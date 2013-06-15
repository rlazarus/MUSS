import mock
from twisted.trial import unittest
from muss import db, handler, locks, parser, utils, equipment


class PlayerMock(db.Player):
    def __init__(self, *args, **kwargs):
        super(PlayerMock, self).__init__(*args, **kwargs)
        self.send = mock.MagicMock()

    def __repr__(self):
        return "Mock({})".format(super(PlayerMock, self).__repr__())

    def response_stack(self, count):
        """
        Unpacks <count> calls to the player.send MagicMock.
        """
        response_calls = self.send.call_args_list
        return [r[0][0] for r in response_calls][-count:]

    def last_response(self):
        """
        Returns only the last line sent to this player from the server.
        """
        return self.send.call_args[0][0]

    def send_line(self, command):
        """
        Send a string to this player's current mode, as if they'd
        typed it in at the console.
        """
        with locks.authority_of(self):
            self.mode.handle(self, command)


class MUSSTestCase(unittest.TestCase):
    """
    A parent test case with common utilities for MUSS tests:
     * setUp() -- creates a database, lobby, and player.
     * new_player(name) -- returns a player object with the name given.
     * setup_objects() -- generates a bunch of objects and, if one doesn't
       already exist, a neighboring player.
     * run_command(command, string) -- parses the string given against the
       command's argument pattern, then executes the command on the result,
       using self.player's authority and perspective.
     * assert_response(string, response) -- asserts that the given command,
       if it were typed into the game by self.player, would produce the
       given response. (See the method definition for more options.)
    """

    def setUp(self):
        with locks.authority_of(locks.SYSTEM):
            self.lobby = db.Room("lobby")
            self.lobby.uid = 0
        self.patch(db, "_objects", {0: self.lobby})
        self.player = self.new_player("Player")

    def new_player(self, name):
        """
        Create a new player with the given name, store it in the database,
        and return it.
        """
        newbie = PlayerMock(name, "password")
        newbie.location = self.lobby
        newbie.enter_mode(handler.NormalMode())
        db.store(newbie)
        return newbie

    def setup_objects(self):
        """
        Generates the following clutter:

        OBJECTS IN THE LOBBY:    abacus, ant, balloon, Bucket, cat, frog,
                                 Fodor's Guide, horse
        IN PLAYER'S INVENTORY:   Anabot doll, ape plushie, apple, cat, cherry,
                                 cheese, horse figurine, monster mask, monocle,
                                 moose, millipede
        IN NEIGHBOR'S INVENTORY: apple
        IN FROG'S INVENTORY:     hat

        All of these are stored in self.objects[name], EXCEPT:
            * the cat in the room is objects["room_cat"]
            * the cat in player's inventory is objects["inv_cat"]
            * the apple in neighbor's inventory is ["neighbor_apple"]

        All are plain db.Objects, EXCEPT:
            * monocle and monster mask are equipment.Equipment
            * Bucket is a db.Container

        The player owns all the objects in its inventory. SYSTEM owns the rest.
        """

        # Won't hurt to do this again if it's already been done.
        self.neighbor = self.new_player("PlayersNeighbor") 

        self.objects = {}
        with locks.authority_of(self.player):
            for inv_object in ["apple", "horse figurine", "ape plushie",
                               "Anabot doll", "cherry", "cheese", "moose",
                               "millipede"]:
                self.objects[inv_object] = db.Object(inv_object, self.player)
            self.objects["monocle"] = equipment.Equipment("monocle",
                                                          self.player)
            self.objects["monster mask"] = equipment.Equipment("monster mask",
                                                               self.player)
        with locks.authority_of(locks.SYSTEM):
            for room_object in ["frog", "ant", "horse", "Fodor's Guide",
                                "abacus", "balloon"]:
                self.objects[room_object] = db.Object(room_object,
                                                  self.player.location)
            self.objects["Bucket"] = db.Container("Bucket",
                                                  self.player.location)
            self.objects["room_cat"] = db.Object("cat", self.player.location)
            self.objects["inv_cat"] = db.Object("cat", self.player)
            self.objects["neighbor_apple"] = db.Object("apple", self.neighbor)
            self.objects["hat"] = db.Object("hat", self.objects["frog"])
        for key in self.objects:
            db.store(self.objects[key])

    def run_command(self, command, string):
        """
        Parse the string against the command's argument pattern, then
        execute the command on behalf of the player.
        """
        args = command.args(self.player).parseString(string)
        with locks.authority_of(self.player):
            command().execute(self.player, args)

    def assert_response(self, command, test_response=None, startswith=None,
                       endswith=None, contains=None):
        """
        Assert that a command sends the appropriate response to the player.
        At least one of test_response, startswith, endswith, and contains
        must be given.
        """
        if not (test_response or startswith or endswith or contains):
            raise ValueError("No assertion type specified.")

        self.player.send_line(command)
        response = self.player.last_response()

        if test_response:
            self.assertEqual(response, test_response)
        if startswith:
            # This instead of using .startswith because it produces more useful
            # errors
            self.assertEqual(response[:len(startswith)], startswith)
        if endswith:
            # ditto
            self.assertEqual(response[-len(endswith):], endswith)
        if contains:
            self.assertTrue(contains in response)
