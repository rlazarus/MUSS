from twisted.trial import unittest

from muss.db import Player
from muss.handler import Mode

class ModeTestCase(unittest.TestCase):
    def setUp(self):
        self.player = Player("name", "password")

    def test_initial(self):
        self.assertEqual(len(self.player.mode_stack), 0)
        try:
            mode = self.player.mode
            self.fail(mode)
        except IndexError:
            pass

    def test_enter(self):
        mode = Mode()
        self.player.enter_mode(mode)
        self.assertEqual(len(self.player.mode_stack), 1)
        self.assertEqual(self.player.mode_stack[0], mode)
        self.assertEqual(self.player.mode, mode)

    def test_exit(self):
        mode0 = Mode()
        mode1 = Mode()
        self.player.enter_mode(mode0)
        self.assertEqual(self.player.mode, mode0)
        self.player.enter_mode(mode1)
        self.assertEqual(self.player.mode, mode1)
        self.player.exit_mode()
        self.assertEqual(self.player.mode, mode0)

    def test_exit_empty(self):
        self.assertRaises(IndexError, self.player.exit_mode)

    def test_exit_only_one(self):
        self.player.enter_mode(Mode())
        self.assertRaises(IndexError, self.player.exit_mode)
