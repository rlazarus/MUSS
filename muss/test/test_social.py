from muss import db
from muss.db import Player, store
from muss.handler import NormalMode

from twisted.trial import unittest
from mock import MagicMock


class SocialTestCase(unittest.TestCase):

    def setUp(self):
        self.patch(db, "_objects", {0: db._objects[0]})
        
        self.player = Player("Player", "password")
        self.player.send = MagicMock()
        self.player.location = db._objects[0]
        self.player.mode = NormalMode()
        store(self.player)
        
        self.neighbor = Player("Neighbor", "password")
        self.neighbor.send = MagicMock()
        self.neighbor.location = db._objects[0]
        self.neighbor.mode = NormalMode()
        store(self.neighbor)
        
    def assert_command(self, command, response, neighbor=None):
        """
        Test that a command sends the appropriate response to the player and, optionally, to a neighbor.
        """
        self.player.mode.handle(self.player, command)
        self.player.send.assert_called_with(response)
        if neighbor is not None:
            self.neighbor.send.assert_called_with(neighbor)

    def test_say_apostrophe(self):
        self.assert_command("'hello world", 'You say, "hello world"', 'Player says, "hello world"')
        self.assert_command("' hello world", 'You say, "hello world"', 'Player says, "hello world"')
    
    def test_say_quote(self):
        self.assert_command('"hello world', 'You say, "hello world"', 'Player says, "hello world"')
        self.assert_command('" hello world', 'You say, "hello world"', 'Player says, "hello world"')
    
    def test_say_fullname(self):
        self.assert_command("say hello world", 'You say, "hello world"', 'Player says, "hello world"')
        
    def test_emote_colon(self):
        self.assert_command(":greets the world", "Player greets the world", "Player greets the world")
        
    def test_emote_fullname(self):
        for name in ["emote", "EMOTE", "em", "eM", "pose"]:
            self.assert_command("{} greets the world".format(name), "Player greets the world", "Player greets the world")
            
    def test_saymode(self):
        self.assert_command("say", "You are now in Say Mode. To get back to Normal Mode, type: .") 
        self.assert_command("not a real command", '* You say, "not a real command"', 'Player says, "not a real command"')
        self.assert_command(":waves", "Player waves", "Player waves")
        self.assert_command("em waves", '* You say, "em waves"', 'Player says, "em waves"')
        self.assert_command("foobar", '* You say, "foobar"', 'Player says, "foobar"')
        self.assert_command("/foobar", "You triggered FooOne.") 
        self.assert_command(".", "You are now in Normal Mode.") 
        self.assert_command("foobar", "You triggered FooOne.")
