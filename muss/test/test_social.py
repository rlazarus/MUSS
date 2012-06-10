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

    def test_say_apostrophe(self):
        self.player.mode.handle(self.player, "'hello world")
        self.player.send.assert_called_with('You say, "hello world"')
        self.neighbor.send.assert_called_with('Player says, "hello world"')
        self.player.mode.handle(self.player, "' hello world")
        self.player.send.assert_called_with('You say, "hello world"')
        self.neighbor.send.assert_called_with('Player says, "hello world"')
    
    def test_say_quote(self):
        self.player.mode.handle(self.player, '"hello world')
        self.player.send.assert_called_with('You say, "hello world"')
        self.neighbor.send.assert_called_with('Player says, "hello world"')
        self.player.mode.handle(self.player, '" hello world')
        self.player.send.assert_called_with('You say, "hello world"')
        self.neighbor.send.assert_called_with('Player says, "hello world"')
    
    def test_say_fullname(self):
        self.player.mode.handle(self.player, "say hello world")
        self.player.send.assert_called_with('You say, "hello world"')
        self.neighbor.send.assert_called_with('Player says, "hello world"')
        
    def test_emote_colon(self):
        self.player.mode.handle(self.player, ":greets the world")
        self.player.send.assert_called_with("Player greets the world")
        self.neighbor.send.assert_called_with("Player greets the world")
        
    def test_emote_fullname(self):
        for name in ["emote", "EMOTE", "em", "eM", "pose"]:
            self.player.mode.handle(self.player, "{} greets the world".format(name))
            self.player.send.assert_called_with("Player greets the world")
            self.neighbor.send.assert_called_with("Player greets the world")
            
    def test_saymode(self):
        self.player.mode.handle(self.player, "say")
        self.player.send.assert_called_with("You are now in Say Mode. To get back to Normal Mode, type: .")
        
        self.player.mode.handle(self.player, "not a real command")
        self.player.send.assert_called_with('* You say, "not a real command"')
        self.neighbor.send.assert_called_with('Player says, "not a real command"')
        
        self.player.mode.handle(self.player, ":waves")
        self.player.send.assert_called_with("Player waves")
        self.neighbor.send.assert_called_with("Player waves")
        
        self.player.mode.handle(self.player, "em waves")
        self.player.send.assert_called_with('* You say, "em waves"')
        self.neighbor.send.assert_called_with('Player says, "em waves"')
        
        self.player.mode.handle(self.player, "foobar")
        self.player.send.assert_called_with('* You say, "foobar"')
        self.neighbor.send.assert_called_with('Player says, "foobar"')
        
        self.player.mode.handle(self.player, "/foobar")
        self.player.send.assert_called_with("You triggered FooOne.")
        
        self.player.mode.handle(self.player, ".")
        self.player.send.assert_called_with("You are now in Normal Mode.")
        
        self.player.mode.handle(self.player, "foobar")
        self.player.send.assert_called_with("You triggered FooOne.")