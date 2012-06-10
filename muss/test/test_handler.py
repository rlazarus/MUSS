from muss import db
from muss.db import Player, store
from muss.commands import NormalMode

from twisted.trial import unittest
from mock import MagicMock

class HandlerTestCase(unittest.TestCase):

    def setUp(self):
        self.patch(db, "_objects", {0: db._objects[0]})
        
        self.player = Player("Player", "password")
        self.player.send = MagicMock()
        self.player.location = db._objects[0]
        self.player.mode = NormalMode()
        store(self.player)
        
    def test_blankline(self):
        self.player.mode.handle(self.player, "")
        self.assertFalse(self.player.send.called)
        
    def test_ambiguous_partial(self):
        self.player.mode.handle(self.player, "foo")
        self.player.send.assert_called_with("I don't know which one you meant: foobar, foobaz?")
        
    def test_ambiguous_full(self):
        self.player.mode.handle(self.player, "test")
        self.player.send.assert_called_with("I don't know which \"test\" you meant!")
        
    def test_fake(self):
        self.player.mode.handle(self.player, "not a real command")
        self.player.send.assert_called_with("I don't understand that.")