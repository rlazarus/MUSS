from muss import locks
from muss.test import common_tools


class EquipmentTestCase(common_tools.MUSSTestCase):
    def setUp(self):
        super(EquipmentTestCase, self).setUp()
        self.setup_objects()

    def test_view_equipment(self):
        with locks.authority_of(locks.SYSTEM):
            self.objects["monocle"].equipped = True
        self.assert_response("equip", "Player is wearing monocle.")

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
