from muss import locks, utils
from muss.test import common_tools


class SetTestCase(common_tools.MUSSTestCase):
    def setUp(self):
        super(SetTestCase, self).setUp()
        self.setup_objects()

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
