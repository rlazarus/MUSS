from twisted.trial import unittest

import muss.db
import muss.locks

class DataTestCase(unittest.TestCase):
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
