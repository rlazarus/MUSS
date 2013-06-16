from muss.test import common_tools


class AdminTestCase(common_tools.MUSSTestCase):
    def test_sudo(self):
        self.neighbor.send_line("create muss.db.Object x")
        self.neighbor.send_line("set x.sudotest=5")
        self.neighbor.send_line("drop x")
        self.assert_response("set x.sudotest=6",
                             "You don't have permission to set sudotest on x.")
        self.assert_response("sudo set x.sudotest=6",
                             "Set x's sudotest attribute to 6")
