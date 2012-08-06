from twisted.trial import unittest
from mock import MagicMock

from muss import channels, db
from muss.channels import Channel
from muss.db import Room, Player, store
from muss.locks import authority_of, SYSTEM

class CommandTestCase(unittest.TestCase):
    def setUp(self):
        self.patch(channels, "_channels", {})

        with authority_of(SYSTEM):
            lobby = Room("lobby")
            lobby.uid = 0
            self.patch(db, "_objects", {0: lobby})

        self.player = Player("Player", "password")
        self.player.send = MagicMock()
        store(self.player)

        self.other = Player("Other", "password")
        self.other.send = MagicMock()
        store(self.other)

        self.channel = Channel("Public")

    def test_init(self):
        self.assertIn(self.channel.name, channels._channels)
        self.assertEquals(self.channel.name, "Public")

    def test_reject_dupe(self):
        self.assertRaises(ValueError, Channel, "Public")

    def test_join(self):
        self.assertNotIn(self.player, self.channel.players)
        self.assertNotIn(self.other, self.channel.players)
        self.channel.join(self.player)
        self.assertIn(self.player, self.channel.players)
        self.assertNotIn(self.other, self.channel.players)
        self.channel.join(self.other)
        self.assertIn(self.player, self.channel.players)
        self.assertIn(self.other, self.channel.players)

    def test_leave(self):
        self.channel.join(self.player)
        self.channel.join(self.other)

        self.assertIn(self.player, self.channel.players)
        self.assertIn(self.other, self.channel.players)
        self.channel.leave(self.player)
        self.assertNotIn(self.player, self.channel.players)
        self.assertIn(self.other, self.channel.players)
        self.channel.leave(self.other)
        self.assertNotIn(self.player, self.channel.players)
        self.assertNotIn(self.other, self.channel.players)

    def test_join_twice(self):
        self.channel.join(self.player)
        self.assertRaises(ValueError, self.channel.join, self.player)

    def test_leave_twice(self):
        self.assertRaises(ValueError, self.channel.leave, self.player)

    def test_send(self):
        self.channel.join(self.player)
        self.channel.join(self.other)
        self.channel.say(self.player, "testing")
        self.assertEquals(self.player.send.call_args[0][0], '[Public] You say, "testing"')
        self.assertEquals(self.other.send.call_args[0][0], '[Public] Player says, "testing"')
        
        self.channel.pose(self.player, "tests")
        self.assertEquals(self.player.send.call_args[0][0], '[Public] Player tests')
        self.assertEquals(self.other.send.call_args[0][0], '[Public] Player tests')

        self.channel.semipose(self.player, "'s test passes")
        self.assertEquals(self.player.send.call_args[0][0], "[Public] Player's test passes")
        self.assertEquals(self.other.send.call_args[0][0], "[Public] Player's test passes")
