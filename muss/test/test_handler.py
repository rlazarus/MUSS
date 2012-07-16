from muss import db, locks
from muss.db import Player, Object, store
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
        self.player.enter_mode(NormalMode())
        store(self.player)

        self.neighbor = Player("PlayersNeighbor", "password")
        self.neighbor.send = MagicMock()
        self.neighbor.location = db._objects[0]
        self.neighbor.enter_mode(NormalMode())
        store(self.neighbor)

    def populate_objects(self):
        self.objects = {}
        for room_object in ["frog", "ant", "horse", "Fodor's Guide", "abacus", "balloon"]:
            self.objects[room_object] = Object(room_object, self.player.location)
        for inv_object in ["apple", "horse figurine", "ape plushie", "Anabot doll", "cherry", "cheese"]:
            self.objects[inv_object] = Object(inv_object, self.player)
        self.objects["room_cat"] = Object("cat", self.player.location)
        self.objects["inv_cat"] = Object("cat", self.player)
        for key in self.objects:
            store(self.objects[key])

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

    def test_require_full(self):
        self.player.mode.handle(self.player, "des #2")
        self.assert_command("des #2", 'I don\'t know of a command called "des." (If you mean "destroy," you\'ll need to use the whole command name.)')
