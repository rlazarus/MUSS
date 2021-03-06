import pyparsing as pyp

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

    def test_create_badtype(self):
        self.assert_response("create foo ar",
                             startswith="Object type should be of the form")
        self.assert_response("create foo.bar baz",
                             startswith="I don't know of this module")
        self.assert_response("create muss.db.foo bar",
                             startswith="muss.db doesn't have this class")
        self.assert_response("create muss.db.Room foo",
                             'Use "dig", not "create", to make new rooms.')
        self.assert_response("create muss.db.Exit foo",
                             'Use "open", not "create", to make new exits.')

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

    def test_open_multi(self):
        with locks.authority_of(self.player):
            destination = db.Room("destination")
        db.store(destination)
        self.assert_response("open glowing portal "
                             "to #{}".format(destination.uid),
                             "Opened glowing portal to destination.")
        exit = db.get(destination.uid + 1)
        self.assertTrue(isinstance(exit, db.Exit))
        self.assertIdentical(exit.location, self.lobby)
        self.assertIdentical(exit.destination, destination)

    def test_open_multi_fail(self):
        from muss.commands.building import Open
        self.assertRaises(pyp.ParseException, self.run_command, Open,
                          "glowing portal #0")

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

    def test_destroy_emit_elsewhere(self):
        with locks.authority_of(self.player):
            new_room = db.Room("a room")
        db.store(new_room)
        self.player.send_line("destroy #{}".format(new_room.uid))
        self.assertNotEqual(self.neighbor.last_response(),
                            "Player destroys a room.")

    def test_ghosts(self):
        self.assert_response("destroy #{}".format(self.player.uid),
                             "You cannot destroy Player.")

    def test_dig(self):
        uid = db._nextUid
        self.assert_response("dig", "Enter the room's name (. to cancel):")
        self.assert_response("Room", "Enter the name of the exit into the "
                                     "room, if any (. to cancel):")
        self.assert_response("east", "Enter the name of the exit back, if any "
                                     "(. to cancel):")
        self.assert_response("west", "Dug room #{}, Room.".format(uid))
        room = db.get(uid)
        self.assertEqual(room.type, "room")
        self.assertEqual(room.name, "Room")

    def test_dig_oneline(self):
        uid = db._nextUid
        self.assert_response("dig Another Room", "Enter the name of the exit "
                                                 "into the room, if any "
                                                 "(. to cancel):")
        self.assert_response("west", "Enter the name of the exit back, if "
                                     "any (. to cancel):")
        self.assert_response("east", "Dug room #{}, Another Room.".format(uid))
        room = db.get(uid)
        self.assertEqual(room.type, "room")
        self.assertEqual(room.name, "Another Room")

    def test_dig_commas(self):
        uid = db._nextUid
        self.assert_response("dig Room, With, Commas",
                             "Enter the name of the exit "
                             "into the room, if any (. to cancel):")
        self.assert_response("east", "Enter the name of the exit back, if "
                                     "any (. to cancel):")
        self.assert_response("west", "Dug room #{}, Room, With, "
                                     "Commas.".format(uid))
        room = db.get(uid)
        self.assertEqual(room.name, "Room, With, Commas")

    def test_dig_cancel(self):
        uid = db._nextUid
        self.assert_response("dig", "Enter the room's name (. to cancel):")
        self.assert_response(".", "Canceled.")
        self.assertRaises(KeyError, db.get, uid)

        self.assert_response("dig", "Enter the room's name (. to cancel):")
        self.assert_response("Room", "Enter the name of the exit into the "
                                     "room, if any (. to cancel):")
        self.assert_response(".", "Canceled.")
        self.assertRaises(KeyError, db.get, uid)

        self.assert_response("dig", "Enter the room's name (. to cancel):")
        self.assert_response("Room", "Enter the name of the exit into the "
                                     "room, if any (. to cancel):")
        self.assert_response("east", "Enter the name of the exit back, if "
                                     "any (. to cancel):")
        self.assert_response(".", "Canceled.")
        self.assertRaises(KeyError, db.get, uid)

    def test_dig_noexits(self):
        uid = db._nextUid
        self.assert_response("dig Room", "Enter the name of the exit into the "
                                         "room, if any (. to cancel):")
        self.assert_response("", "Enter the name of the exit back, if "
                                     "any (. to cancel):")
        self.assert_response("", "Dug room #{}, Room.".format(uid))
        room = db.get(uid)
        self.assertEqual(room.type, "room")
        self.assertEqual(room.name, "Room")
        exits = db.find_all(lambda x: x.type == "exit" and 
                                      (x.location is room or
                                       x.destination is room))
        self.assertEqual(exits, set())
