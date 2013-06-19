from muss import locks
from muss.test import common_tools


class GiveTestCase(common_tools.MUSSTestCase):
    def setUp(self):
        super(GiveTestCase, self).setUp()
        self.setup_objects()

    def test_give_fail(self):
        self.assertEqual(self.objects["monocle"].location, self.player)
        self.assert_response("give monocle to playersneighbor",
                             "You can't put that in PlayersNeighbor.")
        self.assertEqual(self.objects["monocle"].location, self.player)

    def test_give_fail_reflexive(self):
        self.assert_response("give monocle to player",
                             "You already have monocle.")

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
