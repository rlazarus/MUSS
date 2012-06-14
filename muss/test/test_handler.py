from muss import db
from muss.db import Player, store
from muss.commands import NormalMode, PlayerName

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
        
    def test_fake(self):
        self.assert_command("not a real command", "I don't know what you mean by \"not.\"")

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
