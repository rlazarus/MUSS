from muss import db, locks, parser
from muss.test import common_tools


class ItemTestCase(common_tools.MUSSTestCase):
    def setUp(self):
        super(ItemTestCase, self).setUp()
        self.setup_objects()

    def test_inventory(self):
        inv = [i for i in self.objects.values() if i.location == self.player]
        inv_names = sorted([i.name for i in inv])
        inv_string = ", ".join(inv_names)
        self.assert_response("inventory",
                            "You are carrying: {}.".format(inv_string))
        for item in inv:
            db.delete(item)
        self.assert_response("inventory", "You are not carrying anything.")

    def test_take_success(self):
        from muss.commands.world import Take
        self.run_command(Take, "balloon")
        self.assertEqual(self.objects["balloon"].location, self.player)
        self.run_command(Take, "cat")
        self.assertEqual(self.objects["room_cat"].location, self.player)
        self.assert_response("take frog", "You take frog.")
        self.assertEqual(self.neighbor.send.call_args[0][0],
                         "Player takes frog.")

    def test_take_failure(self):
        from muss.commands.world import Take
        self.assertRaises(parser.NotFoundError,
                          Take.args(self.player).parseString, "rutabega")
        self.assertRaises(parser.AmbiguityError,
                          Take.args(self.player).parseString, "f")

    def test_drop_success(self):
        self.assert_response("drop apple", "You drop apple.")
        self.assertEqual(self.neighbor.send.call_args[0][0],
                         "Player drops apple.")
        self.assertEqual(self.objects["apple"].location, self.lobby)

    def test_drop_failure(self):
        self.assert_response("drop hat", "I don't know of an object in "
                                         "Player's inventory called \"hat\"")
        self.assert_response("drop ch",
                             "Which one do you mean? (cheese, cherry)")

    def test_stealing(self):
        with locks.authority_of(locks.SYSTEM):
            self.objects["monocle"].location = self.neighbor
        self.assert_response("take monocle from playersneighbor",
                             "You can't remove that from PlayersNeighbor.")

    def test_stealing_askingforit(self):
        with locks.authority_of(locks.SYSTEM):
            bystander = self.new_player("Bystander")
            self.neighbor.locks.remove = locks.Pass()
            self.objects["monocle"].location = self.neighbor
        self.assertEqual(self.objects["monocle"].location, self.neighbor)
        self.assert_response("take monocle from playersneighbor",
                             "You take monocle from PlayersNeighbor.")
        self.assertEqual(self.neighbor.send.call_args[0][0],
                         "Player takes monocle from you.")
        self.assertEqual(bystander.send.call_args[0][0],
                         "Player takes monocle from PlayersNeighbor.")
        self.assertEqual(self.objects["monocle"].location, self.player)
