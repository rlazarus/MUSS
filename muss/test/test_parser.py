from muss import db, locks
from muss.db import Player, Object, store
from muss.handler import NormalMode
from muss.parser import MatchError, AmbiguityError, NotFoundError, NoSuchUidError, PlayerName, CommandName, Article, ObjectName, ObjectIn, NearbyObject, ReachableObject, ObjectUid, ReachableOrUid
from muss.utils import find_by_name, find_one

from twisted.trial import unittest
from twisted.python import failure
from mock import MagicMock
from pyparsing import ParseException, Word, alphas, CaselessKeyword

class ParserTestCase(unittest.TestCase):

    def setUp(self):
        self.patch(db, "_objects", {0: db._objects[0]})
        self.patch(locks, "_authority", locks.SYSTEM)
        
        self.player = Player("Player", "password")
        self.player.send = MagicMock()
        self.player.location = db._objects[0]
        self.player.enter_mode(NormalMode())
        store(self.player)

        self.neighbor = Player("PlayersNeighbor", "password")
        self.neighbor.send = MagicMock()
        self.neighbor.location = db._objects[0]
        self.neighbor.enter_mode(NormalMode())
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

    def assert_error_message(self, desired_exception, desired_message, function_call, *args, **kwargs):
        """
        Wrapper for assertRaises which verifies both the exception type and the error message--e.verbose() for any exception extending MatchError, or str(e) for any other exception.
        """
        exception = self.assertRaises(desired_exception, function_call, *args, **kwargs)
        if isinstance(exception, MatchError):
            self.assertEqual(exception.verbose(), desired_message)
        else:
            self.assertEqual(str(exception), desired_message)
        
    def test_commandname_success(self):
        from muss.commands.help import Help
        from muss.commands.social import Chat
        from muss.commands.test import Poke
        for command_tuple in [("poke", Poke), ("help", Help), ("chat", Chat)]:
            name, command = command_tuple
            parse_result = CommandName()("command").parseString(name, parseAll=True).asDict()
            self.assertEqual(parse_result["command"], command_tuple)

    def test_commandname_notfound(self):
        self.assertRaises(NotFoundError, CommandName().parseString, "noncommand", parseAll=True)
        self.assert_command("usage notacommand", 'I don\'t know of a command called "notacommand."')

    def test_commandname_ambiguous(self):
        self.assertRaises(AmbiguityError, CommandName().parseString, "test", parseAll=True)

    def test_commandname_ambiguity(self):
        self.assert_command("usage test", 'I don\'t know which command called "test" you mean.')
        self.assert_command("usage foo", "Which command do you mean? (foobar, foobaz)")

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
        self.assert_command("poke NotAPlayer", 'I don\'t know of a player called "NotAPlayer."')
        
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
        for word in ["a", "an", "the", "A", "AN", "THE"]:
            parse_result = Article.parseString(word, parseAll=True)
            self.assertEqual(parse_result[0], word.lower())

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
        self.assert_error_message(NotFoundError, "I don't know of an object in lobby called \"asdf.\"", ObjectIn(lobby).parseString, "asdf", parseAll=True)

    def test_objectin_badlocation(self):
        self.assert_error_message(TypeError, "Invalid location: foo", ObjectIn, "foo")

    def test_nearbyobject_room(self):
        parse_result = NearbyObject(self.player).parseString("lobby", parseAll=True)
        self.assertEqual(parse_result[0], self.player.location)
        
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
            self.assert_error_message(NotFoundError, "I don't know of an object in your inventory called \"{}.\"".format(item), NearbyObject(self.player).parseString, "my " + item, parseAll=True)

    def test_nearbyobject_nopriority_success(self):
        for item in ["ant", "frog", "apple", "ape plushie"]:
            parse_result = NearbyObject(self.player).parseString(item, parseAll=True)
            self.assertEqual(parse_result[0], self.objects[item])

    def test_nearbyobject_nopriority_ambiguous(self):
        for item in ["a", "cat", "h"]:
            self.assertRaises(AmbiguityError, NearbyObject(self.player).parseString, item, parseAll=True)

    def test_nearbyobject_nopriority_notfound(self):
        self.assert_error_message(NotFoundError, "I don't know of a nearby object called \"asdf.\"", NearbyObject(self.player).parseString, "asdf", parseAll=True)

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
        e = self.assertRaises(AmbiguityError, NearbyObject(self.player, priority="room").parseString, "a", parseAll=True)
        a_names = ["abacus", "ant"]
        a_matches = [self.objects[i] for i in a_names]
        self.assertEqual(sorted(e.matches), sorted(a_matches))

    def test_nearbyobject_priority_notfound(self):
        self.assert_error_message(NotFoundError, "I don't know of a nearby object called \"asdf.\"", NearbyObject(self.player, priority="inventory").parseString, "asdf", parseAll=True)

    def test_nearbyobject_priority_badpriority(self):
        self.assertRaises(KeyError, NearbyObject, self.player, priority="foo")

    def test_nearbyobject_player(self):
        parse_result = NearbyObject(self.player).parseString("PlayersNeighbor")
        self.assertEqual(parse_result[0], self.neighbor)

    def test_combining_object_tokens(self):
        grammar = ObjectIn(self.player) + Word(alphas)
        parse_result = grammar.parseString("apple pie")
        self.assertEqual(list(parse_result), [self.objects["apple"], "pie"])

    def test_reachableobject_nearby_success(self):
        for item in ["apple", "frog"]:
            parse_result = ReachableObject(self.player).parseString(item, parseAll=True)
            self.assertEqual(parse_result[0], self.objects[item])
        parse_result = ReachableObject(self.player).parseString("my ape", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["ape plushie"])
        parse_result = ReachableObject(self.player).parseString("PlayersN", parseAll=True)
        self.assertEqual(parse_result[0], self.neighbor)

    def test_reachableobject_nearby_failure(self):
        self.assert_error_message(NotFoundError, "I don't know of a reachable object called \"asdf.\"", ReachableObject(self.player).parseString, "asdf", parseAll=True)

    def test_reachableobject_preposition_success(self):
        parse_result = ReachableObject(self.player).parseString("cat on Player", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["inv_cat"])
        parse_result = ReachableObject(self.player).parseString("apple in player", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["apple"])

    def test_reachableobject_preposition_failure(self):
        self.assert_error_message(NotFoundError, "I don't know of a reachable object called \"foo between bar.\"", ReachableObject(self.player).parseString, "foo between bar", parseAll=True)

    def test_reachableobject_preposition_player_success(self):
        parse_result = ReachableObject(self.player).parseString("apple in playersneighbor", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["neighbor_apple"])

    def test_reachableobject_preposition_player_failure(self):
        self.assert_error_message(NotFoundError, "I don't know of an object in PlayersNeighbor's inventory called \"asdf.\"", ReachableObject(self.player).parseString, "asdf in playersneighbor", parseAll=True)
        

    def test_reachableobject_combining_success(self):
        grammar = ReachableObject(self.player)("first") + CaselessKeyword("and") + ReachableObject(self.player)("second")
        parse_result = grammar.parseString("apple in player and hat on frog", parseAll=True).asDict()
        self.assertEqual(parse_result["first"], self.objects["apple"])
        self.assertEqual(parse_result["second"], self.objects["hat"])
        parse_result = grammar.parseString("hat on frog and Fodor's", parseAll=True).asDict()
        self.assertEqual(parse_result["first"], self.objects["hat"])
        self.assertEqual(parse_result["second"], self.objects["Fodor's Guide"])

    def test_reachableobject_combining_failure(self):
        grammar = ReachableObject(self.player)("first") + CaselessKeyword("and") + ReachableObject(self.player)("second")
        self.assert_error_message(NotFoundError, "I don't know of an object in frog called \"apple and hat.\"", grammar.parseString, "apple and hat on frog", parseAll=True)

    def test_reachableobject_room_success(self):
        parse_result = ReachableObject(self.player).parseString("cat in room", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["room_cat"])

    def test_reachable_object_room_failure(self):
        self.assert_error_message(NotFoundError, "I don't know of an object in lobby called \"cherry.\"", ReachableObject(self.player).parseString, "cherry in room", parseAll=True)

    def test_reachableobject_owner(self):
        parse_result = ReachableObject(self.player).parseString("PlayersNeighbor's apple", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["neighbor_apple"])

    def test_reachableobject_owner_failure(self):
        self.assert_error_message(NotFoundError, "I don't know of an object in PlayersNeighbor's inventory called \"frog.\"", ReachableObject(self.player).parseString, "PlayersNeighbor's frog", parseAll=True)

    def test_reachableobject_combining_owner(self):
        grammar = ReachableObject(self.player)("first") + CaselessKeyword("and") + ReachableObject(self.player)("second")
        parse_result = grammar.parseString("my apple and PlayersN's apple", parseAll=True)
        self.assertEqual(parse_result["first"], self.objects["apple"])
        self.assertEqual(parse_result["second"], self.objects["neighbor_apple"])
        parse_result = grammar.parseString("PlayersN's apple and frog in room", parseAll=True)
        self.assertEqual(parse_result["first"], self.objects["neighbor_apple"])
        self.assertEqual(parse_result["second"], self.objects["frog"])

    def test_objectuid_success(self):
        grammar = ObjectUid()("obj")
        result = grammar.parseString("#" + str(self.player.uid))
        self.assertEqual(result.obj, self.player)
        result = grammar.parseString("#" + str(self.neighbor.uid))
        self.assertEqual(result.obj, self.neighbor)

    def test_objectuid_bad_uid_failure(self):
        self.assert_error_message(NoSuchUidError, "There is no object #9999.", ObjectUid().parseString, "#9999")

    def test_objectuid_non_numeric_failure(self):
        non_uids = ["asdf", "#asdf", "#12e", "123"]
        for non_uid in non_uids:
            self.assert_command("whatis {}".format(non_uid), "I was expecting an object UID where you put \"{}.\" (Try \"help whatis.\")".format(non_uid))

    def test_multi_word_matching(self):
        perfect, partial = find_by_name("plushie", self.objects.values(), attributes=["name"])
        self.assertEqual(partial[0], ("ape plushie", self.objects["ape plushie"]))
        name, item = find_one("guide", self.objects.values(), attributes=["name"])
        self.assertEqual(name, "Fodor's Guide")
        self.assertEqual(item, self.objects["Fodor's Guide"])

    def test_require_full(self):
        from muss.commands.building import Destroy
        try:
            parse_result = CommandName()("command").parseString("d")
            self.assertNotEqual(parse_result["command"][1], Destroy)
            # ^-- if there's only one other command starting with d
            # v-- if there's more than one
        except AmbiguityError as e:
            self.assertNotIn(Destroy, [b for a, b in e.matches])
        except:
            self.fail()
        # Error message tests for this are in test_handler.py.

    def test_reachableoruid(self):
        uids = {}
        uids["frog"] = self.objects["frog"].uid
        uids["apple"] = self.objects["apple"].uid
        uids["hat"] = self.objects["hat"].uid

        item = ReachableOrUid(self.player).parseString("frog")[0]
        self.assertEqual(item, self.objects["frog"])
        item = ReachableOrUid(self.player).parseString("#{}".format(uids["frog"]))[0]
        self.assertEqual(item, self.objects["frog"])
        
        item = ReachableOrUid(self.player).parseString("apple")[0]
        self.assertEqual(item, self.objects["apple"])
        item = ReachableOrUid(self.player).parseString("#{}".format(uids["apple"]))[0]
        self.assertEqual(item, self.objects["apple"])
        
        item = ReachableOrUid(self.player).parseString("hat on frog")[0]
        self.assertEqual(item, self.objects["hat"])
        item = ReachableOrUid(self.player).parseString("#{}".format(uids["hat"]))[0]
        self.assertEqual(item, self.objects["hat"])
