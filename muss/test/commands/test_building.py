from muss import db, handler, locks, utils, equipment
from muss.test import common_tools


class BuildingTestCase(common_tools.MUSSTestCase):
    def setUp(self):
        super(BuildingTestCase, self).setUp()
        self.setup_objects()

    def test_create_success(self):
        self.assert_response("create muss.db.Object a widget",
                             startswith="Created item #",
                             endswith=", a widget.")
        self.assert_response("inventory", contains="a widget")

    def test_create_failure(self):
        self.assert_response("create", "(Try \"help create\" for more help.)")

    def test_create_types(self):
        self.assert_response("create muss.db.Container box", endswith=", box.")
        box = db.find(lambda x: x.name == "box")
        self.assertIsInstance(box, db.Container)
        self.assertEqual(box.location, self.player)
        self.assert_response("create muss.equipment.Equipment snake",
                             endswith=", snake.")
        snake = db.find(lambda x: x.name == "snake")
        self.assertIsInstance(snake, equipment.Equipment)
        self.assertEqual(snake.location, self.player)

    def test_open(self):
        with locks.authority_of(self.player):
            destination = db.Room("destination")
        db.store(destination)
        self.assert_response("open north to #{}".format(destination.uid),
                             "Opened north to destination.")
        exit = db.get(destination.uid + 1)
        self.assertTrue(isinstance(exit, db.Exit))
        self.assertIdentical(exit.location, self.lobby)
        self.assertIdentical(exit.destination, destination)

    def test_destroy(self):
        apple_uid = self.objects["apple"].uid
        command = "destroy #{}".format(apple_uid)
        response = "You destroy #{} (apple).".format(apple_uid)
        self.assert_response(command, response)
        self.assertEqual(self.neighbor.send.call_args[0][0],
                         "Player destroys apple.")
        self.assertRaises(KeyError, db.get, apple_uid)

        with locks.authority_of(self.objects["frog"]):
            handler.NormalMode().handle(self.objects["frog"], "drop hat")
        self.player.send_line("take hat")
        hat_uid = self.objects["hat"].uid
        self.assert_response("destroy #{}".format(hat_uid),
                             "You cannot destroy hat.")

    def test_ghosts(self):
        self.assert_response("destroy #{}".format(self.player.uid),
                             "You cannot destroy Player.")

    def test_dig(self):
        uid = db._nextUid
        self.assert_response("dig", "Enter the room's name:")
        self.assert_response("Room", "Enter the name of the exit into the "
                                     "room, or . for none:")
        self.assert_response("east", "Enter the name of the exit back, or . "
                                     "for none:")
        self.assert_response("west", "Done.")
        room = db.get(uid)
        self.assertEqual(room.type, "room")
        self.assertEqual(room.name, "Room")

    def test_dig_oneline(self):
        uid = db._nextUid
        self.assert_response("dig Another Room", "Enter the name of the exit "
                                                 "into the room, or . for "
                                                 "none:")
        self.assert_response("west", "Enter the name of the exit back, or . "
                                     "for none:")
        self.assert_response("east", "Done.")
        room = db.get(uid)
        self.assertEqual(room.type, "room")
        self.assertEqual(room.name, "Another Room")
