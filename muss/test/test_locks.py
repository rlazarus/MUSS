from twisted.trial import unittest

import muss.db
import muss.locks

class LockTestCase(unittest.TestCase):
    def setUp(self):
        self.patch(muss.db, "_objects", {0: muss.db._objects[0]})
        
        self.player = muss.db.Player("Player", "password")
        muss.db.store(self.player)

        self.player2 = muss.db.Player("PlayerTwo", "password")
        muss.db.store(self.player2)

    def test_contextmanager(self):
        self.assertIs(muss.locks._authority, None)
        with muss.locks.authority_of(self.player):
            self.assertIs(muss.locks._authority, self.player)
        self.assertIs(muss.locks._authority, None)

    def test_contextmanager_nested(self):
        self.assertIs(muss.locks._authority, None)
        with muss.locks.authority_of(self.player):
            self.assertIs(muss.locks._authority, self.player)
            with muss.locks.authority_of(self.player2):
                self.assertIs(muss.locks._authority, self.player2)
            self.assertIs(muss.locks._authority, self.player)
        self.assertIs(muss.locks._authority, None)

    def test_get_authority(self):
        self.assertIs(muss.locks.authority(), None)
        with muss.locks.authority_of(self.player):
            self.assertIs(muss.locks.authority(), self.player)
        self.assertIs(muss.locks.authority(), None)

    def test_pass(self):
        lock = muss.locks.Pass()
        self.assertTrue(lock(self.player))
        self.assertTrue(lock(self.player2))

    def test_fail(self):
        lock = muss.locks.Fail()
        self.assertFalse(lock(self.player))
        self.assertFalse(lock(self.player2))

    def test_not(self):
        self.assertFalse(muss.locks.Not(muss.locks.Pass())(self.player))
        self.assertTrue(muss.locks.Not(muss.locks.Fail())(self.player))

    def test_and(self):
        true = muss.locks.Pass()
        false = muss.locks.Fail()

        self.assertTrue(muss.locks.And(true)(self.player))
        self.assertFalse(muss.locks.And(false)(self.player))

        self.assertTrue(muss.locks.And(true, true)(self.player))
        self.assertFalse(muss.locks.And(true, false)(self.player))
        self.assertFalse(muss.locks.And(false, true)(self.player))
        self.assertFalse(muss.locks.And(false, false)(self.player))

        self.assertTrue(muss.locks.And(true, true, true)(self.player))
        self.assertFalse(muss.locks.And(true, true, false)(self.player))

    def test_or(self):
        true = muss.locks.Pass()
        false = muss.locks.Fail()

        self.assertTrue(muss.locks.Or(true)(self.player))
        self.assertFalse(muss.locks.Or(false)(self.player))

        self.assertTrue(muss.locks.Or(true, true)(self.player))
        self.assertTrue(muss.locks.Or(true, false)(self.player))
        self.assertTrue(muss.locks.Or(false, true)(self.player))
        self.assertFalse(muss.locks.Or(false, false)(self.player))

        self.assertTrue(muss.locks.Or(false, false, true)(self.player))
        self.assertFalse(muss.locks.Or(false, false, false)(self.player))

    def test_is(self):
        lock = muss.locks.Is(self.player)
        self.assertTrue(lock(self.player))
        self.assertFalse(lock(self.player2))

    def test_has(self):
        key = muss.db.Object("a key")
        key.location = self.player
        muss.db.store(key)

        lock = muss.locks.Has(key)
        self.assertTrue(lock(self.player))
        self.assertFalse(lock(self.player2))
