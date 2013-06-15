from muss import db, handler, locks, parser, utils, equipment
from muss.test import test_tools


class CommandTestCase(test_tools.MUSSTestCase):
    def setUp(self):
        super(CommandTestCase, self).setUp()
        self.setup_objects()

    def test_usage(self):
        self.assert_response("usage poke", "poke <player>")
        self.assert_response("usage usage", "usage <command>")
        self.assert_response("usage quit", "quit")
        self.assert_response("usage ;", ";<action>")

    def test_inventory(self):
        inv = [i for i in self.objects.values() if i.location == self.player]
        inv_names = sorted([i.name for i in inv])
        inv_string = ", ".join(inv_names)
        self.assert_response("inventory",
                            "You are carrying: {}.".format(inv_string))
        for item in inv:
            db.delete(item)
        self.assert_response("inventory", "You are not carrying anything.")

    def test_take_success(self):
        from muss.commands.world import Take
        self.run_command(Take, "balloon")
        self.assertEqual(self.objects["balloon"].location, self.player)
        self.run_command(Take, "cat")
        self.assertEqual(self.objects["room_cat"].location, self.player)
        self.assert_response("take frog", "You take frog.")
        self.assertEqual(self.neighbor.send.call_args[0][0],
                         "Player takes frog.")

    def test_take_failure(self):
        from muss.commands.world import Take
        self.assertRaises(parser.NotFoundError,
                          Take.args(self.player).parseString, "rutabega")
        self.assertRaises(parser.AmbiguityError,
                          Take.args(self.player).parseString, "f")

    def test_drop_success(self):
        self.assert_response("drop apple", "You drop apple.")
        self.assertEqual(self.neighbor.send.call_args[0][0],
                         "Player drops apple.")
        self.assertEqual(self.objects["apple"].location, self.player.location)

    def test_drop_failure(self):
        self.assert_response("drop hat", "I don't know of an object in "
                                         "Player's inventory called \"hat\"")
        self.assert_response("drop ch",
                             "Which one do you mean? (cheese, cherry)")

    def test_view_equipment(self):
        self.objects["monocle"].equipped = True
        self.assert_response("equip", "Player is wearing monocle.")

    def test_stealing(self):
        self.objects["monocle"].location = self.neighbor
        self.assert_response("take monocle from playersneighbor",
                             "You can't remove that from PlayersNeighbor.")

    def test_stealing_askingforit(self):
        self.neighbor.locks.remove = locks.Pass()
        self.objects["monocle"].location = self.neighbor
        self.assertEqual(self.objects["monocle"].location, self.neighbor)
        self.assert_response("take monocle from playersneighbor",
                             "You take monocle from PlayersNeighbor.")
        self.assertEqual(self.objects["monocle"].location, self.player)

    def test_stealing_equipment(self):
        self.objects["monocle"].location = self.neighbor
        self.objects["monocle"].equipped = True
        self.assert_response("take monocle from playersneighbor",
                             "You can't, it's equipped.")
        self.objects["monocle"].lock_attr("equipped", set_lock = locks.Pass())
        self.assert_response("take monocle from playersneighbor",
                             "You can't remove that from PlayersNeighbor.")

    def test_stealing_equipment_askingforit(self):
        self.neighbor.locks.remove = locks.Pass()
        self.objects["monocle"].location = self.neighbor
        self.objects["monocle"].equipped = True
        self.assert_response("take monocle from playersneighbor",
                             "You can't, it's equipped.")
        self.objects["monocle"].lock_attr("equipped", set_lock = locks.Pass())
        self.assert_response("take monocle from playersneighbor",
                             "You take monocle from PlayersNeighbor.")

    def test_drop_equip(self):
        self.objects["monocle"].equipped = True
        self.assert_response("drop monocle", "You unequip and drop monocle.")
        self.objects["monocle"].location = self.player
        self.assert_response("wear monocle", "You equip monocle.")
        self.objects["monster mask"].equipped = True
        self.assert_response("drop m",
                             "Which one do you mean? (millipede, moose)")
        # i.e. prefer the ones which aren't equipped
        self.assert_response("drop mo", "You drop moose.")
        self.assert_response("drop mo",
                             "Which one do you mean? (monocle, monster mask)")

    def test_equip(self):
        self.assertEqual(self.objects["monocle"].equipped, False)
        self.assert_response("wear monocle", "You equip monocle.")
        self.assertEqual(self.objects["monocle"].equipped, True)
        self.assert_response("wear monocle", "That is already equipped!")
        self.assertEqual(self.player.equipment_string(),
                         "Player is wearing monocle.")

    def test_equip_nonequippable(self):
        self.assert_response("wear cat", "That is not equipment!")

    def test_unequip(self):
        self.assert_response("wear monocle", "You equip monocle.")
        self.assertEqual(self.objects["monocle"].equipped, True)
        self.assert_response("remove monocle", "You unequip monocle.")
        self.assertEqual(self.objects["monocle"].equipped, False)
        self.assert_response("remove monocle", "That isn't equipped!")
        self.assertEqual(self.player.equipment_string(), "")

    def test_autounequip(self):
        self.objects["monocle"].equipped = True
        self.objects["monocle"].location = self.lobby
        self.assertEqual(self.objects["monocle"].equipped, False)

    def test_give_fail(self):
        self.assertEqual(self.objects["monocle"].location, self.player)
        self.assert_response("give monocle to playersneighbor",
                             "You can't put that in PlayersNeighbor.")
        self.assertEqual(self.objects["monocle"].location, self.player)

    def test_give_succeed(self):
        self.neighbor.locks.insert = locks.Pass()
        self.assertEqual(self.objects["monocle"].location, self.player)
        self.assert_response("give monocle to playersneighbor",
                             "You give monocle to PlayersNeighbor.")
        self.assertEqual(self.objects["monocle"].location, self.neighbor)

    def test_put_fail_drop(self):
        self.objects["cherry"].locks.drop = locks.Fail()
        self.assert_response("put cherry in bucket", "You cannot drop cherry.")

    def test_put_fail_insert(self):
        self.objects["Bucket"].locks.insert = locks.Fail()
        self.assert_response("put cherry in bucket",
                             "You can't put that in Bucket.")

    def test_put_succeed(self):
        self.assert_response("give bucket cherry", "You put cherry in Bucket.")
        self.assertEqual(self.objects["cherry"].location,
                         self.objects["Bucket"])
        self.assert_response("put moose in bucket", "You put moose in Bucket.")
        self.assertEqual(self.objects["moose"].location, self.objects["Bucket"])

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
        self.assertIdentical(exit.location, self.player.location)
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

    def test_help(self):
        from muss.handler import all_commands
        from muss.commands.help import Help

        for command in all_commands():
            names = [] + command().names + command().nospace_names
            send_count = len(command().usages) + 4

            for name in names:
                try:
                    self.run_command(Help, name)
                except parser.AmbiguityError:
                    # It's not a failure of the help system
                    # if command names are ambiguous.
                    continue
                help_sends = self.player.response_stack(send_count)
                usage_list = ["\t" + u for u in command().usages]

                self.assertEqual(help_sends[0][:len(name)], name.upper())
                self.assertEqual(help_sends[1], "Usage:")
                self.assertEqual(help_sends[2:-2], usage_list)
                self.assertEqual(help_sends[-2], "")
                self.assertEqual(help_sends[-1], command.help_text)

    def test_sudo(self):
        self.neighbor.send_line("create muss.db.Object x")
        self.neighbor.send_line("set x.sudotest=5")
        self.neighbor.send_line("drop x")
        self.assert_response("set x.sudotest=6",
                             "You don't have permission to set sudotest on x.")
        self.assert_response("sudo set x.sudotest=6",
                             "Set x's sudotest attribute to 6")

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
