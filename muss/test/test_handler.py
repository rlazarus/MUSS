from muss import db, handler, locks
from muss.test import common_tools


class HandlerTestCase(common_tools.MUSSTestCase):
    def test_fake(self):
        self.assert_response("not a real command",
                             'I don\'t know of a command called "not"')

    def test_ambiguous_partial_no_arg_match(self):
        self.assert_response("foo",
                             "Which command do you mean? (foobar, foobaz)")

    def test_ambiguous_partial_one_arg_match(self):
        self.assert_response("foo two args", "You triggered FooTwo.")
 
    def test_ambiguous_partial_multi_arg_match(self):
        self.assert_response("foo onearg",
                             "Which command do you mean? (foobar, foobaz)")

    def test_ambiguous_full_no_arg_match(self):
        self.assert_response("test",
                             'I don\'t know which command called "test" you '
                             'mean.')

    def test_ambiguous_full_one_arg_match(self):
        self.assert_response("test two args", "You triggered FooTwo.")

    def test_ambiguous_full_multi_arg_match(self):
        self.assert_response("test onearg",
                             'I don\'t know which command called "test" you '
                             'mean.')

    def test_unambiguous_no_args(self):
        self.assert_response("foobar", '(Try "help foobar" for more help.)')

    def test_unambiguous_not_enough_args(self):
        self.assert_response("asdf one two", '(Try "help asdf" for more help.)')

    def test_unambiguous_extra_args(self):
        self.assert_response("quit stuff", '(Try "help quit" for more help.)')
        self.assert_response("foobar two args",
                             '(Try "help foobar" for more help.)')

    def test_unambiguous_bad_args(self):
        self.assert_response("poke stuff",
                             'I don\'t know of a player called "stuff"')

    def test_require_full(self):
        self.player.send_line("des #2")
        self.assert_response("des #2",
                             'I don\'t know of a command called "des" (If you '
                             'mean "destroy," you\'ll need to use the whole '
                             'command name.)')

    def test_prompt(self):
        self.assert_response("ptest", "Enter text")
        self.assertIsInstance(self.player.mode, handler.LineCaptureMode)
        self.assert_response("stuff and things", "stuff and things")


    def test_exit_invocation(self):
        self.foyer = db.Room("foyer")
        db.store(self.foyer)
        self.exit = db.Exit("exit", self.lobby, self.foyer)
        db.store(self.exit)
        self.assertEqual(self.player.location, self.lobby)
        self.player.send_line("exit")
        self.assertEqual(self.player.location, self.foyer)
