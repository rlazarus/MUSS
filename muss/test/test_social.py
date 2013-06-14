from muss import db, handler, locks

import mock
from twisted.trial import unittest


class SocialTestCase(unittest.TestCase):

    def setUp(self):
        self.patch(db, "_objects", {0: db._objects[0]})
        self.patch(locks, "_authority", locks.SYSTEM)

        self.player = db.Player("Player", "password")
        with locks.authority_of(self.player):
            self.player.send = mock.MagicMock()
            self.player.enter_mode(handler.NormalMode())
        db.store(self.player)

        self.neighbor = db.Player("Neighbor", "password")
        with locks.authority_of(self.neighbor):
            self.neighbor.send = mock.MagicMock()
            self.neighbor.enter_mode(handler.NormalMode())
        db.store(self.neighbor)

        self.otherneighbor = db.Player("OtherNeighbor", "password")
        with locks.authority_of(self.otherneighbor):
            self.otherneighbor.send = mock.MagicMock()
            self.otherneighbor.enter_mode(handler.NormalMode())
        db.store(self.otherneighbor)

        self.notconnected = db.Player("NotConnected", "password")
        with locks.authority_of(self.notconnected):
            self.notconnected.send = mock.MagicMock()
            # Not entering mode -> empty mode_stack -> .connected() returns
            # False
        db.store(self.notconnected)

    def assert_command(self, command, response, neighbor=None):
        """
        Test that a command sends the appropriate response to the player and,
        optionally, to a neighbor.
        """
        with locks.authority_of(self.player):
            # so as to see permissions errors if they happen
            self.player.mode.handle(self.player, command)
        self.player.send.assert_called_with(response)
        if neighbor is not None:
            self.neighbor.send.assert_called_with(neighbor)

    def test_say_apostrophe(self):
        self.assert_command("'hello world",
                            'You say, "hello world"',
                            'Player says, "hello world"')
        self.assert_command("' hello world",
                            'You say, " hello world"',
                            'Player says, " hello world"')

    def test_say_quote(self):
        self.assert_command('"hello world',
                            'You say, "hello world"',
                            'Player says, "hello world"')
        self.assert_command('" hello world',
                            'You say, " hello world"',
                            'Player says, " hello world"')

    def test_say_fullname(self):
        self.assert_command("say hello world",
                            'You say, "hello world"',
                            'Player says, "hello world"')

    def test_emote_colon(self):
        self.assert_command(":greets the world",
                            "Player greets the world",
                            "Player greets the world")

    def test_emote_fullname(self):
        for name in ["emote", "EMOTE", "em", "eM"]:
            self.assert_command("{} greets the world".format(name),
                                "Player greets the world",
                                "Player greets the world")

    def test_saymode(self):
        self.assert_command("say",
                            "You are now in Say Mode. To get back to Normal "
                            "Mode, type: .")
        self.assert_command("not a real command",
                            '* You say, "not a real command"',
                            'Player says, "not a real command"')
        self.assert_command(":waves", "Player waves", "Player waves")
        self.assert_command("em waves", '* You say, "em waves"',
                            'Player says, "em waves"')
        self.assert_command("foobar", '* You say, "foobar"',
                            'Player says, "foobar"')
        self.assert_command("/foobar arg", "You triggered FooOne.")
        self.assert_command(".", "You are now in Normal Mode.")
        self.assert_command("foobar arg", "You triggered FooOne.")

    def test_tell_success(self):
        self.assert_command("tell neighbor hi", "You tell Neighbor: hi",
                            "Player tells you: hi")
        self.assert_command("tell ne hi", "You tell Neighbor: hi",
                            "Player tells you: hi")

        self.assert_command("tell ne :waves", "To Neighbor: Player waves",
                            "Tell: Player waves")
        self.assert_command("tell ne ;'s fingers wiggle",
                            "To Neighbor: Player's fingers wiggle",
                            "Tell: Player's fingers wiggle")
        self.assert_command("tell player hi", "You tell Player: hi")

    def test_tell_failure(self):
        self.assert_command("tell hi", "I don't know of a player called \"hi\"")
        self.assert_command("tell no hi", "NotConnected is not connected.")
        self.assert_command("tell n hi",
                            "Which player do you mean? (Neighbor, "
                            "NotConnected)")
        self.assert_command("tell ne", "(Try \"help tell\" for more help.)")

    def test_retell_success(self):
        self.assert_command("tell ne hi", "You tell Neighbor: hi")
        self.assert_command("retell hi again", "You tell Neighbor: hi again")
        self.assert_command("tell o hi", "You tell OtherNeighbor: hi")
        self.assert_command("retell hi again",
                            "You tell OtherNeighbor: hi again")

    def test_retell_failure(self):
        self.assert_command("retell to nowhere",
                            "You haven't sent a tell to anyone yet.")
        self.assert_command("tell o hi", "You tell OtherNeighbor: hi")
        with locks.authority_of(locks.SYSTEM):
            self.otherneighbor.mode_stack = []
        self.assert_command("retell to nowhere",
                            "OtherNeighbor is not connected.")

    def test_pose(self):
        self.assertIs(self.player.position, None)
        self.assert_command("pose leaning against the wall",
                            "Player is now leaning against the wall.")
        self.assertEqual(self.player.position, "leaning against the wall")
        self.assert_command("pose standing on their head",
                            "Player is now standing on their head.")
        self.assertEqual(self.player.position, "standing on their head")
        self.assert_command("pose",
                            "Player is no longer standing on their head.")
        self.assertEqual(self.player.position, None)
        self.assert_command("pose", "You're not currently posing.")
        self.assert_command("pose foo", "Player is now foo.")
        with locks.authority_of(locks.SYSTEM):
            self.player.location = self.neighbor
            # look, I just needed a location
        self.assertIs(self.player.position, None)
