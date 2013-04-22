from twisted.trial import unittest

from muss import db, handler


class ModeTestCase(unittest.TestCase):
    def setUp(self):
        self.player = db.Player("name", "password")

    def test_initial(self):
        self.assertEqual(len(self.player.mode_stack), 0)
        try:
            mode = self.player.mode
            self.fail(mode)
        except IndexError:
            pass

    def test_enter(self):
        mode = handler.Mode()
        self.player.enter_mode(mode)
        self.assertEqual(len(self.player.mode_stack), 1)
        self.assertEqual(self.player.mode_stack[0], mode)
        self.assertEqual(self.player.mode, mode)

    def test_exit(self):
        mode0 = handler.Mode()
        mode1 = handler.Mode()
        self.player.enter_mode(mode0)
        self.assertEqual(self.player.mode, mode0)
        self.player.enter_mode(mode1)
        self.assertEqual(self.player.mode, mode1)
        self.player.exit_mode()
        self.assertEqual(self.player.mode, mode0)

    def test_exit_empty(self):
        self.assertRaises(IndexError, self.player.exit_mode)

    def test_exit_only_one(self):
        self.player.enter_mode(handler.Mode())
        self.assertRaises(IndexError, self.player.exit_mode)
