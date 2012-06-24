from muss import db, locks
from muss.db import Player, Object, store
from muss.handler import NormalMode
from muss.parser import AmbiguityError, NotFoundError, PlayerName, CommandName, Article, ObjectName, ObjectIn, NearbyObject, ReachableObject

from twisted.trial import unittest
from mock import MagicMock
from pyparsing import ParseException, Word, alphas, CaselessKeyword

class ParserTestCase(unittest.TestCase):

    def setUp(self):
        self.patch(db, "_objects", {0: db._objects[0]})
        self.patch(locks, "_authority", locks.SYSTEM)
        
        self.player = Player("Player", "password")
        self.player.send = MagicMock()
        self.player.location = db._objects[0]
        self.player.mode = NormalMode()
        store(self.player)

        self.neighbor = Player("PlayersNeighbor", "password")
        self.neighbor.send = MagicMock()
        self.neighbor.location = db._objects[0]
        self.neighbor.mode = NormalMode()
        store(self.neighbor)

        self.objects = {}
        for room_object in ["frog", "ant", "horse", "Fodor's Guide", "abacus", "balloon"]:
            self.objects[room_object] = Object(room_object, self.player.location)
        for inv_object in ["apple", "horse figurine", "ape plushie", "Anabot doll", "cherry", "cheese"]:
            self.objects[inv_object] = Object(inv_object, self.player)
        self.objects["room_cat"] = Object("cat", self.player.location)
        self.objects["inv_cat"] = Object("cat", self.player)
        self.objects["neighbor_apple"] = Object("apple", self.neighbor)
        self.objects["hat"] = Object("hat", self.objects["frog"])
        for key in self.objects:
            store(self.objects[key])

    def assert_command(self, command, response):
        """
        Test that a command sends the appropriate response to the player and, optionally, to a neighbor.
        """
        self.player.mode.handle(self.player, command)
        self.player.send.assert_called_with(response)
        
    def test_commandname_success(self):
        from muss.commands import Poke, Help, Chat
        for command_tuple in [("poke", Poke), ("help", Help), ("chat", Chat)]:
            name, command = command_tuple
            parse_result = CommandName()("command").parseString(name, parseAll=True).asDict()
            self.assertEqual(parse_result["command"], command_tuple)

    def test_commandname_notfound(self):
        self.assertRaises(NotFoundError, CommandName().parseString, "noncommand", parseAll=True)

    def test_commandname_ambiguous(self):
        self.assertRaises(AmbiguityError, CommandName().parseString, "test", parseAll=True)

    def test_commandname_ambiguity(self):
        self.assert_command("usage test", 'I don\'t know which command called "test" you mean.')
        self.assert_command("usage foo", "Which command do you mean? (foobar, foobaz)")

    def test_commandname_notfound(self):
        self.assert_command("usage notacommand", 'I don\'t know of a command called "notacommand."')

    def test_playername_success(self):
        parse_result = PlayerName().parseString("Player", parseAll=True)
        self.assertEqual(parse_result[0], self.player)
        
    def test_playername_case_insensitive(self):
        parse_result = PlayerName().parseString("player", parseAll=True)
        self.assertEqual(parse_result[0], self.player)
        parse_result = PlayerName().parseString("PLAYER", parseAll=True)
        self.assertEqual(parse_result[0], self.player)
        
    def test_playername_failure_not_player(self):
        self.assertRaises(NotFoundError, PlayerName().parseString, "NotAPlayer", parseAll=True)
        
    def test_playername_failure_invalid_name(self):
        self.assertRaises(NotFoundError, PlayerName().parseString, "6", parseAll=True)

    def test_playername_partial(self):
        parse_result = PlayerName().parseString("Players", parseAll=True)
        self.assertEqual(parse_result[0], self.neighbor)

    def test_playername_ambiguous(self):
        self.assertRaises(AmbiguityError, PlayerName().parseString, "Play", parseAll=True)
        self.assert_command("poke play", "Which player do you mean? (Player, PlayersNeighbor)")

    def test_combining_playername(self):
        grammar = PlayerName() + Word(alphas)
        parse_result = grammar.parseString("Player foo", parseAll=True)
        self.assertEqual(list(parse_result), [self.player, "foo"])

    def test_article_success(self):
        for word in ["a", "an", "the"]:
            parse_result = Article.parseString(word, parseAll=True)
            self.assertEqual(parse_result[0], word)

    def test_article_failure(self):
        self.assertRaises(ParseException, Article.parseString, "foo", parseAll=True)

    def test_objectname_success(self):
        for name in ["apple", "a", "frog", "big frog", "them", "anniversary"]:
            for phrase in [name, "the " + name, "a " + name, "an " + name]:
                parse_result = ObjectName.parseString(phrase, parseAll=True)
                matched_name = " ".join(parse_result)
                self.assertEqual(matched_name, name)

    def test_objectname_failure(self):
        for name in ["\r\n", "", "\t", ""]:
            self.assertRaises(ParseException, ObjectName.parseString, name, parseAll=True)

    def test_objectin_whole(self):
        lobby = db._objects[0]
        name = "Player"
        parse_result = ObjectIn(lobby).parseString(name, parseAll=True)
        self.assertEqual(parse_result[0], self.player)

    def test_objectin_partial(self):
        lobby = db._objects[0]
        name = "Players"
        parse_result = ObjectIn(lobby).parseString(name, parseAll=True)
        self.assertEqual(parse_result[0], self.neighbor)

    def test_objectin_ambiguous(self):
        lobby = db._objects[0]
        name = "Play"
        self.assertRaises(AmbiguityError, ObjectIn(lobby).parseString, name, parseAll=True)

    def test_objectin_notfound(self):
        lobby = db._objects[0]
        name = "asdf"
        self.assertRaises(NotFoundError, ObjectIn(lobby).parseString, name, parseAll=True)

    def test_objectin_badlocation(self):
        self.assertRaises(TypeError, lambda: ObjectIn("foo"))
        
    def test_nearbyobject_my_success(self):
        for phrase in ["my apple", "my app"]:
            parse_result = NearbyObject(self.player).parseString(phrase, parseAll=True)
            self.assertEqual(parse_result[0], self.objects["apple"])
        parse_result = NearbyObject(self.player).parseString("my horse", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["horse figurine"])
        parse_result = NearbyObject(self.player).parseString("my cat", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["inv_cat"])

    def test_nearbyobject_my_ambiguous(self):
        self.assertRaises(AmbiguityError, NearbyObject(self.player).parseString, "my ap", parseAll=True)

    def test_nearbyobject_my_notfound(self):
        for item in ["ant", "frog", "asdf"]:
            self.assertRaises(NotFoundError, NearbyObject(self.player).parseString, "my " + item, parseAll=True)

    def test_nearbyobject_nopriority_success(self):
        for item in ["ant", "frog", "apple", "ape plushie"]:
            parse_result = NearbyObject(self.player).parseString(item, parseAll=True)
            self.assertEqual(parse_result[0], self.objects[item])

    def test_nearbyobject_nopriority_ambiguous(self):
        for item in ["a", "cat", "h"]:
            self.assertRaises(AmbiguityError, NearbyObject(self.player).parseString, item, parseAll=True)

    def test_nearbyobject_nopriority_ambiguous(self):
        self.assertRaises(NotFoundError, NearbyObject(self.player).parseString, "asdf", parseAll=True)

    def test_nearbyobject_priority_success(self):
        items = [("an", "ant"), ("horse", "horse"), ("h", "horse"), ("cher", "cherry"), ("cheese", "cheese")]
        for name, item in items:
            parse_result = NearbyObject(self.player, priority="room").parseString(name, parseAll=True)
            self.assertEqual(parse_result[0], self.objects[item])
        parse_result = NearbyObject(self.player, priority="room").parseString("cat", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["room_cat"])
        parse_result = NearbyObject(self.player, priority="inventory").parseString("horse", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["horse figurine"])

    def test_nearbyobject_priority_ambiguous(self):
        self.assertRaises(AmbiguityError, NearbyObject(self.player, priority="room").parseString, "f", parseAll=True)
        self.assertRaises(AmbiguityError, NearbyObject(self.player, priority="room").parseString, "ch", parseAll=True)
        try:
            NearbyObject(self.player, priority="room").parseString("a", parseAll=True)
        except AmbiguityError as e:
            a_names = ["abacus", "ant"]
            a_matches = [self.objects[i] for i in a_names]
            self.assertEqual(sorted(e.matches), sorted(a_matches))
        else:
            self.fail()

    def test_nearbyobject_priority_notfound(self):
        self.assertRaises(NotFoundError, NearbyObject(self.player, priority="inventory").parseString, "asdf", parseAll=True)

    def test_nearbyobject_priority_badpriority(self):
        self.assertRaises(KeyError, lambda: NearbyObject(self.player, priority="foo"))

    def test_nearbyobject_player(self):
        parse_result = NearbyObject(self.player).parseString("PlayersNeighbor")
        self.assertEqual(parse_result[0], self.neighbor)

    def test_combining_object_tokens(self):
        grammar = ObjectIn(self.player) + Word(alphas)
        parse_result = grammar.parseString("apple pie")
        self.assertEqual(list(parse_result), [self.objects["apple"], "pie"])

    def test_reachableobject_nearby(self):
        for item in ["apple", "frog"]:
            parse_result = ReachableObject(self.player).parseString(item, parseAll=True)
            self.assertEqual(parse_result[0], self.objects[item])
        parse_result = ReachableObject(self.player).parseString("my ape", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["ape plushie"])
        parse_result = ReachableObject(self.player).parseString("PlayersN", parseAll=True)
        self.assertEqual(parse_result[0], self.neighbor)

    def test_reachableobject_preposition(self):
        parse_result = ReachableObject(self.player).parseString("cat on Player", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["inv_cat"])
        parse_result = ReachableObject(self.player).parseString("apple in player", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["apple"])

    def test_reachableobject_combining(self):
        grammar = ReachableObject(self.player)("first") + CaselessKeyword("and") + ReachableObject(self.player)("second")
        parse_result = grammar.parseString("apple in player and hat on frog", parseAll=True).asDict()
        self.assertEqual(parse_result["first"], self.objects["apple"])
        self.assertEqual(parse_result["second"], self.objects["hat"])
        parse_result = grammar.parseString("hat on frog and Fodor's", parseAll=True).asDict()
        self.assertEqual(parse_result["first"], self.objects["hat"])
        self.assertEqual(parse_result["second"], self.objects["Fodor's Guide"])
        try:
            grammar.parseString("apple and hat on frog", parseAll=True)
            self.fail()
        except NotFoundError as e:
            self.assertEqual(e.test_string, "apple and hat")
            self.assertEqual(e.token, "object in frog")
        else:
            self.fail()

    def test_reachableobject_room_keyword(self):
        parse_result = ReachableObject(self.player).parseString("cat in room", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["room_cat"])

    def test_reachableobject_owner(self):
        parse_result = ReachableObject(self.player).parseString("PlayersNeighbor's apple", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["neighbor_apple"])

    def test_reachableobject_combining_owner(self):
        grammar = ReachableObject(self.player)("first") + CaselessKeyword("and") + ReachableObject(self.player)("second")
        parse_result = grammar.parseString("my apple and PlayersN's apple", parseAll=True)
        self.assertEqual(parse_result["first"], self.objects["apple"])
        self.assertEqual(parse_result["second"], self.objects["neighbor_apple"])
        parse_result = grammar.parseString("PlayersN's apple and frog in room", parseAll=True)
        self.assertEqual(parse_result["first"], self.objects["neighbor_apple"])
        self.assertEqual(parse_result["second"], self.objects["frog"])

    # this is the wrong place for this but I'm not sure what the right one is.
    def test_usage(self):
        self.assert_command("usage poke", "\tpoke <player-name>")
        self.assert_command("usage usage", "\tusage <command-name>")
        self.assert_command("usage quit", "\tquit")
        self.assert_command("usage ;", "\t;<action>")
