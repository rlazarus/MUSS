from muss import channels, locks
from muss.test import common_tools

class SocialTestCase(common_tools.MUSSTestCase):
    def setUp(self):
        super(SocialTestCase, self).setUp()
        self.neighbor = self.new_player("Neighbor")
        self.otherneighbor = self.new_player("OtherNeighbor")
        self.notconnected = self.new_player("NotConnected")
        with locks.authority_of(locks.SYSTEM):
            self.notconnected.mode_stack = []

    def test_say_apostrophe(self):
        self.assert_response("'hello world",
                             'You say, "hello world"',
                             'Player says, "hello world"')
        self.assert_response("' hello world",
                             'You say, " hello world"',
                             'Player says, " hello world"')

    def test_say_quote(self):
        self.assert_response('"hello world',
                             'You say, "hello world"',
                             'Player says, "hello world"')
        self.assert_response('" hello world',
                             'You say, " hello world"',
                             'Player says, " hello world"')

    def test_say_fullname(self):
        self.assert_response("say hello world",
                             'You say, "hello world"',
                             'Player says, "hello world"')

    def test_emote_colon(self):
        self.assert_response(":greets the world",
                             "Player greets the world",
                             "Player greets the world")

    def test_emote_fullname(self):
        for name in ["emote", "EMOTE", "em", "eM"]:
            self.assert_response("{} greets the world".format(name),
                                 "Player greets the world",
                                 "Player greets the world")

    def test_saymode(self):
        self.assert_response("say",
                             "You are now in Say Mode. To get back to Normal "
                             "Mode, type: .")
        self.assert_response("not a real command",
                             '* You say, "not a real command"',
                             'Player says, "not a real command"')
        self.assert_response(":waves", "Player waves", "Player waves")
        self.assert_response("em waves", '* You say, "em waves"',
                             'Player says, "em waves"')
        self.assert_response("foobar", '* You say, "foobar"',
                             'Player says, "foobar"')
        self.assert_response("/foobar arg", "You triggered FooOne.")
        self.assert_response(".", "You are now in Normal Mode.")
        self.assert_response("foobar arg", "You triggered FooOne.")

    def test_tell_success(self):
        self.assert_response("tell neighbor hi", "You tell Neighbor: hi",
                             "Player tells you: hi")
        self.assert_response("tell ne hi", "You tell Neighbor: hi",
                             "Player tells you: hi")
 
        self.assert_response("tell ne :waves", "To Neighbor: Player waves",
                             "Tell: Player waves")
        self.assert_response("tell ne ;'s fingers wiggle",
                             "To Neighbor: Player's fingers wiggle",
                             "Tell: Player's fingers wiggle")
        self.assert_response("tell player hi", "You tell Player: hi")
 
    def test_tell_failure(self):
        self.assert_response("tell hi",
                             "I don't know of a player called \"hi\"")
        self.assert_response("tell no hi", "NotConnected is not connected.")
        self.assert_response("tell n hi",
                             "Which player do you mean? (Neighbor, "
                             "NotConnected)")
        self.assert_response("tell ne", "(Try \"help tell\" for more help.)")

    def test_retell_success(self):
        self.assert_response("tell ne hi", "You tell Neighbor: hi")
        self.assert_response("retell hi again", "You tell Neighbor: hi again")
        self.assert_response("tell o hi", "You tell OtherNeighbor: hi")
        self.assert_response("retell hi again",
                             "You tell OtherNeighbor: hi again")

    def test_retell_failure(self):
        self.assert_response("retell to nowhere",
                             "You haven't sent a tell to anyone yet.")
        self.assert_response("tell o hi", "You tell OtherNeighbor: hi")
        with locks.authority_of(locks.SYSTEM):
            self.otherneighbor.mode_stack = []
        self.assert_response("retell to nowhere",
                             "OtherNeighbor is not connected.")
 
    def test_pose(self):
        self.assertIs(self.player.position, None)
        self.assert_response("pose leaning against the wall",
                             "Player is now leaning against the wall.")
        self.assertEqual(self.player.position, "leaning against the wall")
        self.assert_response("pose standing on their head",
                             "Player is now standing on their head.")
        self.assertEqual(self.player.position, "standing on their head")
        self.assert_response("pose",
                            "Player is no longer standing on their head.")
        self.assertEqual(self.player.position, None)
        self.assert_response("pose", "You're not currently posing.")
        self.assert_response("pose foo", "Player is now foo.")
        with locks.authority_of(locks.SYSTEM):
            self.player.location = self.neighbor
            # look, I just needed a location
        self.assertIs(self.player.position, None)


class ChannelsTestCase(common_tools.MUSSTestCase):
    def setUp(self):
        super(ChannelsTestCase, self).setUp()
        self.patch(channels, "_channels", {})
        self.channel = channels.Channel("Public")

    def test_init(self):
        self.assertIn(self.channel.name, channels._channels)
        self.assertEquals(self.channel.name, "Public")

    def test_reject_dupe(self):
        self.assertRaises(ValueError, channels.Channel, "Public")

    def test_join(self):
        self.assertNotIn(self.player, self.channel.players)
        self.assertNotIn(self.neighbor, self.channel.players)
        self.channel.join(self.player)
        self.assertIn(self.player, self.channel.players)
        self.assertNotIn(self.neighbor, self.channel.players)
        self.channel.join(self.neighbor)
        self.assertIn(self.player, self.channel.players)
        self.assertIn(self.neighbor, self.channel.players)

    def test_leave(self):
        self.channel.join(self.player)
        self.channel.join(self.neighbor)

        self.assertIn(self.player, self.channel.players)
        self.assertIn(self.neighbor, self.channel.players)
        self.channel.leave(self.player)
        self.assertNotIn(self.player, self.channel.players)
        self.assertIn(self.neighbor, self.channel.players)
        self.channel.leave(self.neighbor)
        self.assertNotIn(self.player, self.channel.players)
        self.assertNotIn(self.neighbor, self.channel.players)

    def test_join_twice(self):
        self.channel.join(self.player)
        self.assertRaises(ValueError, self.channel.join, self.player)

    def test_leave_twice(self):
        self.assertRaises(ValueError, self.channel.leave, self.player)

    def test_send(self):
        self.channel.join(self.player)
        self.channel.join(self.neighbor)
        self.assert_response('. pub testing',
                             '[Public] You say, "testing"',
                             '[Public] Player says, "testing"')

    def test_pose(self):
        self.channel.join(self.player)
        self.channel.join(self.neighbor)
        self.assert_response('. pub :tests',
                             '[Public] Player tests',
                             '[Public] Player tests')

    def test_semipose(self):
        self.channel.join(self.player)
        self.channel.join(self.neighbor)
        self.assert_response(". pub ;'s test passes",
                             "[Public] Player's test passes",
                             "[Public] Player's test passes")

    def test_chatmode(self):
        self.channel.join(self.player)
        self.channel.join(self.neighbor)
        self.assert_response(". pub",
                             "You are now chatting to Public. To get back to "
                             "Normal Mode, type: .")
        self.assert_response("not a real command",
                             '[Public] You say, "not a real command"',
                             '[Public] Player says, "not a real command"')
        self.assert_response(":waves",
                             "[Public] Player waves",
                             "[Public] Player waves")
        self.assert_response("em waves",
                             '[Public] You say, "em waves"',
                             '[Public] Player says, "em waves"')
        self.assert_response("foobar",
                             '[Public] You say, "foobar"',
                             '[Public] Player says, "foobar"')
        self.assert_response("/foobar arg", "You triggered FooOne.")
        self.assert_response(".", "You are now in Normal Mode.")
        self.assert_response("foobar arg", "You triggered FooOne.")
