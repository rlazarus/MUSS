from muss import db, locks
from muss.db import Player, Object, store, delete
from muss.handler import NormalMode

from twisted.trial import unittest
from mock import MagicMock

class CommandTestCase(unittest.TestCase):

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

    def assert_command(self, command, test_response=None, startswith=None, endswith=None, contains=None):
        """
        Test that a command sends the appropriate response to the player and, optionally, to a neighbor.
        """
        if not (test_response or startswith or endswith or contains):
            raise ValueError("No assertion type specified.")

        self.player.mode.handle(self.player, command)
        response = self.player.send.call_args[0][0]

        if test_response:
            self.assertEqual(response, test_response)
        if startswith:
            self.assertEqual(response[:len(startswith)], startswith)
            # this instead of using .startswith because it produces more useful errors
        if endswith:
            self.assertEqual(response[-len(endswith):], endswith)
            # see previous comment
        if contains:
            self.assertTrue(contains in response)

    def test_usage(self):
        self.assert_command("usage poke", "\tpoke <player>")
        self.assert_command("usage usage", "\tusage <command>")
        self.assert_command("usage quit", "\tquit")
        self.assert_command("usage ;", "\t;<action>")

    def test_inventory(self):
        inv = [i for i in self.objects.values() if i.location == self.player]
        inv_names = sorted([i.name for i in inv])
        inv_string = ", ".join(inv_names)
        self.assert_command("inventory", "You are carrying: {}.".format(inv_string))
        for item in inv:
            delete(item)
        self.assert_command("inventory", "You are not carrying anything.")

    def test_help(self):
        from muss.commands import all_commands

        for command in all_commands():
            names = command().names
            if not names:
                continue
            name = names[0]
            send_count = 4 # the command name(s), "Usage:", a blank line, and the help text
            send_count += len(command().usages)

            self.player.mode.handle(self.player, "help {}".format(name))
            all_sends = [i[0][0] for i in self.player.send.call_args_list]
            help_sends = all_sends[-send_count:]

            self.assertEqual(help_sends[0][:len(name)], name.upper())
            self.assertEqual(help_sends[1], "Usage:")
            self.assertEqual(help_sends[2:-2], ["\t" + u for u in command().usages])
            self.assertEqual(help_sends[-2], "")
            self.assertEqual(help_sends[-1], command.help_text)
