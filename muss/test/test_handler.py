from muss import db
from muss.db import Player, store
from muss.commands import NormalMode, PlayerName, CommandName

from twisted.trial import unittest
from mock import MagicMock
from pyparsing import ParseException

class HandlerTestCase(unittest.TestCase):

    def setUp(self):
        self.patch(db, "_objects", {0: db._objects[0]})
        
        self.player = Player("Player", "password")
        self.player.send = MagicMock()
        self.player.location = db._objects[0]
        self.player.mode = NormalMode()
        store(self.player)

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
        self.assert_command("not a real command", "I don't know what you mean by \"not.\"")
        
    def test_ambiguous_partial_no_arg_match(self):
        self.assert_command("foo", "I don't know which one you mean: foobar, foobaz?")

    def test_ambiguous_partial_one_arg_match(self):
        self.assert_command("foo two args", "You triggered FooTwo.")

    def test_ambiguous_partial_multi_arg_match(self):
        self.assert_command("foo onearg", "I don't know which one you mean: foobar, foobaz?")
        
    def test_ambiguous_full_no_arg_match(self):
        self.assert_command("test", "I don't know which \"test\" you mean!")

    def test_ambiguous_full_one_arg_match(self):
        self.assert_command("test two args", "You triggered FooTwo.")

    def test_ambiguous_full_multi_arg_match(self):
        self.assert_command("test onearg", "I don't know which \"test\" you mean!")

    def test_unambiguous_no_args(self):
        self.assert_command("foobar", 'That command has required arguments. (Try "help foobar.")')

    def test_unambiguous_not_enough_args(self):
        self.assert_command("asdf one two", 'I was expecting a W:(abcd...) at the end of that. (Try "help asdf.")')

    def test_unambiguous_extra_args(self):
        self.assert_command("quit stuff", 'I was expecting an end of line where you put "stuff." (Try "help quit.")')
        self.assert_command("foobar two args", 'I was expecting an end of text where you put "args." (Try "help foobar.")')

    def test_unambiguous_bad_args(self):
        self.assert_command("poke stuff", 'I was expecting a player name where you put "stuff." (Try "help poke.")')

    # Tests for the PlayerName parse element.
    def test_playername_success(self):
        parse_result = PlayerName().parseString("Player", parseAll=True)
        self.assertEqual(parse_result[0], "Player")
        
    def test_playername_case_insensitive(self):
        parse_result = PlayerName().parseString("player", parseAll=True)
        self.assertEqual(parse_result[0], "Player")
        parse_result = PlayerName().parseString("PLAYER", parseAll=True)
        self.assertEqual(parse_result[0], "Player")
        
    def test_playername_failure_not_player(self):
        self.assertRaises(ParseException, PlayerName().parseString, "NotAPlayer", parseAll=True)
        
    def test_playername_failure_invalid_name(self):
        self.assertRaises(ParseException, PlayerName().parseString, "6", parseAll=True)

    # CommandName and Usage
    def test_commandname_success(self):
        for name in ["poke", "help", "chat"]:
            parse_result = CommandName().parseString(name, parseAll=True)
            self.assertEqual(parse_result[0], name)

    def test_commandname_failure(self):
        self.assertRaises(ParseException, CommandName().parseString, "noncommand", parseAll=True)

    def test_single_usage(self):
        self.assert_command("usage poke", "\tpoke <player-name>")
        self.assert_command("usage usage", "\tusage <command-name>")
        self.assert_command("usage foobaz", "\tfoobaz <W:(abcd...)> [W:(abcd...)]")
        self.assert_command("usage ;", "\t;<action>")
