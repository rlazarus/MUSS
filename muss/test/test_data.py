from twisted.trial import unittest

from muss import db

class DataTestCase(unittest.TestCase):
    def setUp(self):
        # Use a dummy database to test with
        self.patch(db, '_objects', {})

    def tearDown(self):
        pass

    def test_create(self):
        expected_uid = db._nextUid
        obj = db.Object("foo")
        self.assertEqual(obj.uid, None)
        db.store(obj)
        self.assertEqual(obj.uid, expected_uid)
        self.assertEqual(db._nextUid, expected_uid + 1)

    def test_retrieve_one(self):
        obj_created = db.Object("foo")
        db.store(obj_created)
        obj_found = db.find(lambda x: x.uid == obj_created.uid)
        self.assertEqual(obj_created, obj_found)
        self.assertTrue(obj_created is obj_found)
        self.assertEqual(obj_found.name, "foo")
        self.assertEqual(obj_found.type, "thing")

        found = db.find_all(lambda x: x.uid == obj_created.uid)
        self.assertEqual(len(found), 1)
        self.assertEqual(obj_created, found.pop())

    def test_retrieve_many(self):
        foo = db.Object("foo")
        bar = db.Object("bar")
        baz = db.Object("baz")

        db.store(foo)
        db.store(bar)
        db.store(baz)

        def starts_with_ba(obj):
            return obj.name.startswith("ba")

        self.assertRaises(KeyError, db.find, starts_with_ba)
        found = db.find_all(starts_with_ba)

        self.assertNotIn(foo, found)
        self.assertIn(bar, found)
        self.assertIn(baz, found)
        self.assertEqual(len(found), 2)

    def test_retrieve_none(self):
        foo = db.Object("foo")

        self.assertRaises(KeyError, db.find, lambda obj: obj.name == "bar")
        found = db.find_all(lambda obj: obj.name == "bar")
        self.assertEqual(len(found), 0)

    def test_update(self):
        obj = db.Object("foo")
        db.store(obj)
        obj.name = "bar"
        db.store(obj)

        obj = db.find(lambda x: x.uid == obj.uid)
        self.assertEqual(obj.name, "bar")
        self.assertEqual(obj.type, "thing")

    def test_delete(self):
        obj = db.Object("foo")
        db.store(obj)
        db.delete(obj)
        self.assertRaises(IndexError, db.store, obj)

    def test_neighbors(self):
        container = db.Object("container")
        foo = db.Object("foo", location=container)
        neighbor = db.Object("neighbor", location=container)
        containee = db.Object("containee", location=foo)
        distant = db.Object("distant")
        inside_neighbor = db.Object("inside neighbor", location=neighbor)
        inside_containee = db.Object("inside containee", location=containee)
        db.store(container)
        db.store(foo)
        db.store(neighbor)
        db.store(containee)
        db.store(distant)
        db.store(inside_neighbor)
        db.store(inside_containee)

        neighbors = foo.neighbors()
        self.assertIn(container, neighbors)
        self.assertIn(foo, neighbors)
        self.assertIn(neighbor, neighbors)
        self.assertIn(containee, neighbors)
        self.assertNotIn(distant, neighbors)
        self.assertNotIn(inside_neighbor, neighbors)
        self.assertNotIn(inside_containee, neighbors)
        self.assertEqual(len(neighbors), 4)
