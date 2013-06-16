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

    def test_set_string(self):
        from muss.commands.building import Set

        self.run_command(Set, "player.test='single quotes'")
        self.assertEqual(self.player.test, "single quotes")

        self.run_command(Set, "player.test='escaped \\' single'")
        self.assertEqual(self.player.test, "escaped ' single")

        self.run_command(Set, 'player.test="double quotes"')
        self.assertEqual(self.player.test, "double quotes")

        self.run_command(Set, 'player.test="escaped \\" double"')
        self.assertEqual(self.player.test, 'escaped " double')

        self.run_command(Set, 'player.test="""triple \' " quotes"""')
        self.assertEqual(self.player.test, 'triple \' " quotes')

    def test_set_numeric(self):
        from muss.commands.building import Set
        self.run_command(Set, 'player.test=1337')
        self.assertEqual(self.player.test, 1337)

    def test_set_uid(self):
        from muss.commands.building import Set

        self.run_command(Set, "player.test=#0")
        self.assertIs(self.player.test, self.lobby)

        self.assertRaises(utils.UserError, self.run_command, Set,
                          "player.test=#-1")

        self.assertRaises(utils.UserError, self.run_command, Set,
                          "player.test=#99999")

    def test_set_keywords(self):
        from muss.commands.building import Set

        self.run_command(Set, "player.test=True")
        self.assertIs(self.player.test, True)

        self.run_command(Set, "player.test=False")
        self.assertIs(self.player.test, False)

        self.run_command(Set, "player.test=None")
        self.assertIs(self.player.test, None)

    def test_set_reachable(self):
        from muss.commands.building import Set

        with locks.authority_of(locks.SYSTEM):
            self.objects["frog"].owner = self.player
            # so that the player will have permission to do this:
        self.run_command(Set, "frog.owner=playersneighbor")
        self.assertEqual(self.objects["frog"].owner, self.neighbor)

        self.run_command(Set, "playersneighbor.pet=frog")
        self.assertEqual(self.neighbor.pet, self.objects["frog"])

    def test_set_spaces(self):
        from muss.commands.building import Set

        self.run_command(Set, "player . test = 'extra spaces'")
        self.assertEqual(self.player.test, "extra spaces")

        self.run_command(Set, "player . test = 5")
        self.assertEqual(self.player.test, 5)

        self.run_command(Set, "player . test = None")
        self.assertEqual(self.player.test, None)

        self.run_command(Set, "player . test = frog")
        self.assertEqual(self.player.test, self.objects["frog"])

    def test_set_failure(self):
        self.assert_response("set asdf.name='foo'",
                             "I don't know what object you mean by 'asdf'")
        self.assert_response("set player.5='foo'",
                             "'5' is not a valid attribute name.")
        self.assert_response("set player.test=foo",
                             "'foo' is not a valid attribute value.")

    def test_set_name(self):
        self.assert_response("set player.name='Foo'",
                             "You don't have permission to set name on Player.")
        self.assert_response("set apple.name='pear'",
                             "Set apple's name attribute to pear")
        self.assert_response("set cherry.name='#25'",
                             "Names can't begin with a #.")

    def test_unset_success(self):
        self.player.send_line("set player.test = 1")
        self.assert_response("unset player.test",
                             "Unset test attribute on Player.")

    def test_unset_failure(self):
        self.assert_response("unset player.foobar",
                             "Player doesn't have an attribute 'foobar'")
        self.assert_response("unset foobar.name",
                             "I don't know what object you mean by 'foobar'")
        self.assert_response("unset player.name",
                             "You don't have permission to unset name on "
                             "Player.")

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
