from twisted.trial import unittest

from muss import db, locks


class LockTestCase(unittest.TestCase):
    def setUp(self):
        with locks.authority_of(locks.SYSTEM):
            self.patch(db, "_objects", {0: db._objects[0]})

            self.player = db.Player("Player", "password")
            db.store(self.player)

            self.player2 = db.Player("PlayerTwo", "password")
            db.store(self.player2)

    def test_contextmanager(self):
        self.assertIs(locks._authority, None)
        with locks.authority_of(self.player):
            self.assertIs(locks._authority, self.player)
        self.assertIs(locks._authority, None)

    def test_contextmanager_nested(self):
        self.assertIs(locks._authority, None)
        with locks.authority_of(self.player):
            self.assertIs(locks._authority, self.player)
            with locks.authority_of(self.player2):
                self.assertIs(locks._authority, self.player2)
            self.assertIs(locks._authority, self.player)
        self.assertIs(locks._authority, None)

    def test_get_authority(self):
        self.assertIs(locks.authority(), None)
        with locks.authority_of(self.player):
            self.assertIs(locks.authority(), self.player)
        self.assertIs(locks.authority(), None)

    def test_pass(self):
        lock = locks.Pass()
        with locks.authority_of(self.player):
            self.assertTrue(lock(self.player))
            self.assertTrue(lock(self.player2))

    def test_fail(self):
        lock = locks.Fail()
        with locks.authority_of(self.player):
            self.assertFalse(lock(self.player))
            self.assertFalse(lock(self.player2))

    def test_not(self):
        with locks.authority_of(self.player):
            self.assertFalse(locks.Not(locks.Pass())(self.player))
            self.assertTrue(locks.Not(locks.Fail())(self.player))

    def test_and(self):
        true = locks.Pass()
        false = locks.Fail()

        with locks.authority_of(self.player):
            self.assertTrue(locks.And(true)(self.player))
            self.assertFalse(locks.And(false)(self.player))

            self.assertTrue(locks.And(true, true)(self.player))
            self.assertFalse(locks.And(true, false)(self.player))
            self.assertFalse(locks.And(false, true)(self.player))
            self.assertFalse(locks.And(false, false)(self.player))

            self.assertTrue(locks.And(true, true, true)(self.player))
            self.assertFalse(locks.And(true, true, false)(self.player))

    def test_or(self):
        true = locks.Pass()
        false = locks.Fail()

        with locks.authority_of(self.player):
            self.assertTrue(locks.Or(true)(self.player))
            self.assertFalse(locks.Or(false)(self.player))

            self.assertTrue(locks.Or(true, true)(self.player))
            self.assertTrue(locks.Or(true, false)(self.player))
            self.assertTrue(locks.Or(false, true)(self.player))
            self.assertFalse(locks.Or(false, false)(self.player))

            self.assertTrue(locks.Or(false, false, true)(self.player))
            self.assertFalse(locks.Or(false, false, false)(self.player))

    def test_is(self):
        lock = locks.Is(self.player)
        with locks.authority_of(self.player):
            self.assertTrue(lock(self.player))
            self.assertFalse(lock(self.player2))

    def test_has(self):
        with locks.authority_of(self.player):
            key = db.Object("a key")
            key.location = self.player
            db.store(key)

            lock = locks.Has(key)
            self.assertTrue(lock(self.player))
            self.assertFalse(lock(self.player2))
