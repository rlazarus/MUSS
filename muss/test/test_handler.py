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
        
    def test_ambiguous_partial(self):
        self.assert_command("foo", "I don't know which one you meant: foobar, foobaz?")
        
    def test_ambiguous_full(self):
        self.assert_command("test", "I don't know which \"test\" you meant!")
        
    def test_fake(self):
        self.assert_command("not a real command", "I don't understand that.")

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