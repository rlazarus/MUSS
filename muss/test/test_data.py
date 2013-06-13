import mock
from twisted.trial import unittest

from muss import db, locks


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
        obj_found = db.get(obj_created.uid)
        self.assertEqual(obj_created, obj_found)
        self.assertTrue(obj_created is obj_found)
        self.assertEqual(obj_found.name, "foo")
        self.assertEqual(obj_found.type, "thing")

        found = db.find_all(lambda x: x.uid == obj_created.uid)
        self.assertEqual(len(found), 1)
        self.assertEqual(obj_created, found.pop())

        self.assertEqual(obj_created, db.get(obj_created.uid))

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
        with locks.authority_of(locks.SYSTEM):
            obj = db.Object("foo")
            db.store(obj)
            obj.name = "bar"
            db.store(obj)

        obj = db.get(obj.uid)
        self.assertEqual(obj.name, "bar")
        self.assertEqual(obj.type, "thing")

    def test_delete(self):
        obj = db.Object("foo")
        db.store(obj)
        db.delete(obj)
        self.assertRaises(IndexError, db.store, obj)

    def test_neighbors(self):
        with locks.authority_of(locks.SYSTEM):
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

    def test_move_insert_remove(self):
        hat = db.Object("hat")
        magician = db.Object("magician")
        db.store(hat)
        db.store(magician)
        try:
            with locks.authority_of(magician):
                rabbit = db.Object("rabbit", hat)
        except locks.LockFailedError as e:
            self.assertEqual(str(e), "You can't put that in hat.")
        else:
            self.fail()
        with locks.authority_of(hat):
            hat.locks.insert = locks.Is(magician)
        with locks.authority_of(magician):
            rabbit = db.Object("rabbit", hat)
            db.store(rabbit)
            try:
                rabbit.location = magician
            except locks.LockFailedError as e:
                self.assertEqual(str(e), "You can't remove that from hat.")
            else:
                self.fail()
            with locks.authority_of(hat):
                hat.locks.remove = locks.Is(magician)
            rabbit.location = magician
        self.assertEqual(rabbit.location, magician)
        # Nothin' up my sleeve, folks.

    def test_move_get_drop_container(self):
        magician = db.Object("magician")
        rabbit = db.Object("stubborn rabbit")
        db.store(magician)
        db.store(rabbit)

        with locks.authority_of(rabbit):
            rabbit.locks.take = locks.Fail()
            rabbit.locks.drop = locks.Fail()
            rabbit.locks.insert = locks.Is(magician)

        with locks.authority_of(magician):
            carrot = db.Object("carrot", magician)
            celery = db.Object("celery", magician)
            hat = db.Container("hat", magician)
            db.store(carrot)
            db.store(celery)
            db.store(hat)

            try:
                rabbit.location = magician
            except locks.LockFailedError as e:
                self.assertEqual(str(e), "You cannot take stubborn rabbit.")
            else:
                self.fail()

            carrot.location = rabbit
            with locks.authority_of(rabbit):
                rabbit.locks.take = locks.Is(magician)
            rabbit.location = magician

            try:
                rabbit.location = hat
            except locks.LockFailedError as e:
                self.assertEqual(str(e), "You cannot drop stubborn rabbit.")
            else:
                self.fail()

            celery.location = rabbit
            with locks.authority_of(rabbit):
                rabbit.locks.drop = locks.Is(magician)
            rabbit.location = hat

            rabbit.location = magician
            # Tada! I'll be here all week.

    def test_destroy(self):
        owner = db.Object("owner")
        not_owner = db.Object("not_owner")
        db.store(owner)
        db.store(not_owner)

        with locks.authority_of(owner):
            item = db.Object("item")
        db.store(item)
        item_uid = item.uid

        with locks.authority_of(not_owner):
            self.assertRaises(locks.LockFailedError, item.destroy)

        with locks.authority_of(owner):
            item.destroy()

        matches = db.find_all(lambda x: x.uid == item_uid)
        self.assertEqual(len(matches), 0)
        self.assertRaises(KeyError, db.get, item_uid)

    def test_exit(self):
        owner = db.Object("owner")
        db.store(owner)
        with locks.authority_of(owner):
            source = db.Room("Source")
            dest = db.Room("Dest")
            db.store(source)
            db.store(dest)
            player = db.Object("Player", location=source)
            player.send = mock.MagicMock()
            db.store(player)
            exit = db.Exit("Exit", source, dest)
            exit.go_message = ("You, {player}, go from {source} to "
                               "{destination} via {exit}.")
            db.store(exit)
            sourceBystander = db.Object("source bystander", location=source)
            sourceBystander.send = mock.MagicMock()
            db.store(sourceBystander)
            destBystander = db.Object("dest bystander", location=dest)
            destBystander.send = mock.MagicMock()
            db.store(destBystander)

            self.assertIs(player.location, source)
            exit.go(player)
            self.assertIs(player.location, dest)

            self.assertEqual(sourceBystander.send.call_count, 1)
            self.assertEqual(destBystander.send.call_count, 1)

            sourceBystander.send.assert_called_once_with(
                "Player leaves through Exit.")
            destBystander.send.assert_called_once_with("Player arrives.")
            player.send.assert_called_with("You, Player, go from Source to "
                                           "Dest via Exit.")
