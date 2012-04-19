from twisted.trial import unittest

from muss import data

class DataTestCase(unittest.TestCase):
    def setUp(self):
        # Use a dummy database to test with
        self.db = data.Database()
        self.patch(self.db, '_objects', {})

    def tearDown(self):
        pass

    def test_create(self):
        self.assertEqual(self.db._nextUid, 0)
        obj = data.Object("foo")
        self.assertEqual(obj.uid, None)
        self.db.store(obj)
        self.assertEqual(obj.uid, 0)
        self.assertEqual(self.db._nextUid, 1)

    def test_retrieve_one(self):
        obj_created = data.Object("foo")
        self.db.store(obj_created)
        obj_found = self.db.find(lambda x: x.uid == obj_created.uid)
        self.assertEqual(obj_created, obj_found)
        self.assertTrue(obj_created is obj_found)
        self.assertEqual(obj_found.name, "foo")
        self.assertEqual(obj_found.type, "thing")

        found = self.db.find_all(lambda x: x.uid == obj_created.uid)
        self.assertEqual(len(found), 1)
        self.assertEqual(obj_created, found.pop())

    def test_retrieve_many(self):
        foo = data.Object("foo")
        bar = data.Object("bar")
        baz = data.Object("baz")

        self.db.store(foo)
        self.db.store(bar)
        self.db.store(baz)

        def starts_with_ba(obj):
            return obj.name.startswith("ba")

        self.assertRaises(KeyError, self.db.find, starts_with_ba)
        found = self.db.find_all(starts_with_ba)

        self.assertNotIn(foo, found)
        self.assertIn(bar, found)
        self.assertIn(baz, found)
        self.assertEqual(len(found), 2)

    def test_retrieve_none(self):
        foo = data.Object("foo")

        self.assertRaises(KeyError, self.db.find, lambda obj: obj.name == "bar")
        found = self.db.find_all(lambda obj: obj.name == "bar")
        self.assertEqual(len(found), 0)

    def test_update(self):
        obj = data.Object("foo")
        self.db.store(obj)
        obj.name = "bar"
        self.db.store(obj)

        obj = self.db.find(lambda x: x.uid == obj.uid)
        self.assertEqual(obj.name, "bar")
        self.assertEqual(obj.type, "thing")

    def test_delete(self):
        obj = data.Object("foo")
        self.db.store(obj)
        self.db.delete(obj)
        self.assertRaises(IndexError, self.db.store, obj)
