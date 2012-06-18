from muss import db, locks
from muss.db import Player, store
from muss.handler import NormalMode
from muss.parser import AmbiguityError, NotFoundError, PlayerName, CommandName, Article, ObjectName, ObjectIn, NearbyObject

from twisted.trial import unittest
from mock import MagicMock
from pyparsing import ParseException

class HandlerTestCase(unittest.TestCase):

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

    def assert_command(self, command, response):
        """
        Test that a command sends the appropriate response to the player and, optionally, to a neighbor.
        """
        self.player.mode.handle(self.player, command)
        self.player.send.assert_called_with(response)
        
    def test_blankline(self):
        self.player.mode.handle(self.player, "")
        self.assertFalse(self.player.send.called)
        
    def test_fake(self):
        self.assert_command("not a real command", 'I don\'t know of a command called "not."')
        
    def test_ambiguous_partial_no_arg_match(self):
        self.assert_command("foo", "Which command do you mean? (foobar, foobaz)")

    def test_ambiguous_partial_one_arg_match(self):
        self.assert_command("foo two args", "You triggered FooTwo.")

    def test_ambiguous_partial_multi_arg_match(self):
        self.assert_command("foo onearg", "Which command do you mean? (foobar, foobaz)")
        
    def test_ambiguous_full_no_arg_match(self):
        self.assert_command("test", 'I don\'t know which command called "test" you mean.')

    def test_ambiguous_full_one_arg_match(self):
        self.assert_command("test two args", "You triggered FooTwo.")

    def test_ambiguous_full_multi_arg_match(self):
        self.assert_command("test onearg", 'I don\'t know which command called "test" you mean.')

    def test_unambiguous_no_args(self):
        self.assert_command("foobar", 'That command has required arguments. (Try "help foobar.")')

    def test_unambiguous_not_enough_args(self):
        self.assert_command("asdf one two", 'I was expecting a W:(abcd...) at the end of that. (Try "help asdf.")')

    def test_unambiguous_extra_args(self):
        self.assert_command("quit stuff", 'I was expecting a LineEnd where you put "stuff." (Try "help quit.")')
        self.assert_command("foobar two args", 'I was expecting a StringEnd where you put "args." (Try "help foobar.")')

    def test_unambiguous_bad_args(self):
        self.assert_command("poke stuff", 'I don\'t know of a player called "stuff."')

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

    # Tests for the PlayerName parse element.
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

    # Object token tests woo!
    def test_article_success(self):
        for word in ["a", "an", "the"]:
            parse_result = Article.parseString(word, parseAll=True)
            self.assertEqual(parse_result[0], word)

    def test_article_failure(self):
        self.assertRaises(ParseException, Article.parseString, "foo", parseAll=True)


    def test_objectname_success(self):
        for name in ["frog", "big frog", "them", "anniversary"]:
            for phrase in [name, "the " + name, "a " + name, "an " + name]:
                parse_result = ObjectName("thing").parseString(phrase, parseAll=True).asDict()
                reassembled = " ".join(parse_result["thing"])
                self.assertEqual(reassembled, name)

    def test_objectname_failure(self):
        for name in ["555", "", "\t", "the 5"]:
            self.assertRaises(ParseException, ObjectName.parseString, name, parseAll=True)
    
    # this is the wrong place for this but I'm ont sure what the right one is.
    def test_usage(self):
        self.assert_command("usage poke", "\tpoke <player-name>")
        self.assert_command("usage usage", "\tusage <command-name>")
        self.assert_command("usage quit", "\tquit")
        self.assert_command("usage ;", "\t;<action>")
