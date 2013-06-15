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

    def test_view_equipment(self):
        with locks.authority_of(locks.SYSTEM):
            self.objects["monocle"].equipped = True
        self.assert_response("equip", "Player is wearing monocle.")

    def test_stealing(self):
        with locks.authority_of(locks.SYSTEM):
            self.objects["monocle"].location = self.neighbor
        self.assert_response("take monocle from playersneighbor",
                             "You can't remove that from PlayersNeighbor.")

    def test_stealing_askingforit(self):
        with locks.authority_of(locks.SYSTEM):
            self.neighbor.locks.remove = locks.Pass()
            self.objects["monocle"].location = self.neighbor
        self.assertEqual(self.objects["monocle"].location, self.neighbor)
        self.assert_response("take monocle from playersneighbor",
                             "You take monocle from PlayersNeighbor.")
        self.assertEqual(self.objects["monocle"].location, self.player)

    def test_stealing_equipment(self):
        with locks.authority_of(locks.SYSTEM):
            self.objects["monocle"].location = self.neighbor
            self.objects["monocle"].equipped = True
            self.assert_response("take monocle from playersneighbor",
                                 "You can't, it's equipped.")
            self.objects["monocle"].lock_attr("equipped",
                                              set_lock = locks.Pass())
            self.assert_response("take monocle from playersneighbor",
                                 "You can't remove that from PlayersNeighbor.")

    def test_stealing_equipment_askingforit(self):
        with locks.authority_of(locks.SYSTEM):
            self.neighbor.locks.remove = locks.Pass()
            self.objects["monocle"].location = self.neighbor
            self.objects["monocle"].equipped = True
            self.assert_response("take monocle from playersneighbor",
                                 "You can't, it's equipped.")
            self.objects["monocle"].lock_attr("equipped",
                                              set_lock = locks.Pass())
            self.assert_response("take monocle from playersneighbor",
                                 "You take monocle from PlayersNeighbor.")

    def test_drop_equip(self):
        with locks.authority_of(locks.SYSTEM):
            self.objects["monocle"].equipped = True
            self.assert_response("drop monocle",
                                 "You unequip and drop monocle.")
            self.objects["monocle"].location = self.player
            self.assert_response("wear monocle", "You equip monocle.")
            self.objects["monster mask"].equipped = True
        self.assert_response("drop m",
                             "Which one do you mean? (millipede, moose)")
        # i.e. prefer the ones which aren't equipped
        self.assert_response("drop mo", "You drop moose.")
        self.assert_response("drop mo",
                             "Which one do you mean? (monocle, monster mask)")

    def test_equip(self):
        self.assertEqual(self.objects["monocle"].equipped, False)
        self.assert_response("wear monocle", "You equip monocle.")
        self.assertEqual(self.objects["monocle"].equipped, True)
        self.assert_response("wear monocle", "That is already equipped!")
        self.assertEqual(self.player.equipment_string(),
                         "Player is wearing monocle.")

    def test_equip_nonequippable(self):
        self.assert_response("wear cat", "That is not equipment!")

    def test_unequip(self):
        self.assert_response("wear monocle", "You equip monocle.")
        self.assertEqual(self.objects["monocle"].equipped, True)
        self.assert_response("remove monocle", "You unequip monocle.")
        self.assertEqual(self.objects["monocle"].equipped, False)
        self.assert_response("remove monocle", "That isn't equipped!")
        self.assertEqual(self.player.equipment_string(), "")

    def test_autounequip(self):
        with locks.authority_of(locks.SYSTEM):
            self.objects["monocle"].equipped = True
            self.objects["monocle"].location = self.lobby
        self.assertEqual(self.objects["monocle"].equipped, False)

    def test_give_fail(self):
        self.assertEqual(self.objects["monocle"].location, self.player)
        self.assert_response("give monocle to playersneighbor",
                             "You can't put that in PlayersNeighbor.")
        self.assertEqual(self.objects["monocle"].location, self.player)

    def test_give_succeed(self):
        self.neighbor.locks.insert = locks.Pass()
        self.assertEqual(self.objects["monocle"].location, self.player)
        self.assert_response("give monocle to playersneighbor",
                             "You give monocle to PlayersNeighbor.")
        self.assertEqual(self.objects["monocle"].location, self.neighbor)

    def test_put_fail_drop(self):
        self.objects["cherry"].locks.drop = locks.Fail()
        self.assert_response("put cherry in bucket", "You cannot drop cherry.")

    def test_put_fail_insert(self):
        self.objects["Bucket"].locks.insert = locks.Fail()
        self.assert_response("put cherry in bucket",
                             "You can't put that in Bucket.")

    def test_put_succeed(self):
        self.assert_response("give bucket cherry", "You put cherry in Bucket.")
        self.assertEqual(self.objects["cherry"].location,
                         self.objects["Bucket"])
        self.assert_response("put moose in bucket", "You put moose in Bucket.")
        self.assertEqual(self.objects["moose"].location, self.objects["Bucket"])
