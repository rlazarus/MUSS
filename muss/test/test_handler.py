from muss import db, handler, locks, parser
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
        with locks.authority_of(locks.SYSTEM):
            self.foyer = db.Room("foyer")
            db.store(self.foyer)
            self.exit = db.Exit("exit", self.lobby, self.foyer)
        db.store(self.exit)
        self.assertEqual(self.player.location, self.lobby)
        self.player.send_line("exit")
        self.assertEqual(self.player.location, self.foyer)

    def test_exit_permissions(self):
        with locks.authority_of(locks.SYSTEM):
            self.foyer = db.Room("foyer")
            self.exit = db.Exit("exit", self.lobby, self.foyer)
            self.exit.locks.go = locks.Fail()
        db.store(self.foyer)
        db.store(self.exit)
        self.assert_response("exit", "You can't go through exit.")


    def test_ambiguous_exit(self):
        with locks.authority_of(locks.SYSTEM):
            self.foyer = db.Room("foyer")
            self.exit_ju = db.Exit("jump", self.lobby, self.foyer)
            self.exit_jo = db.Exit("joust", self.lobby, self.foyer)
        for obj in self.foyer, self.exit_ju, self.exit_jo:
            db.store(obj)
        self.assert_response("j", "Which exit do you mean? (joust, jump)")

    def test_many_exits_and_commands(self):
        with locks.authority_of(locks.SYSTEM):
            self.exit_s1 = db.Exit("s1", self.lobby, self.lobby)
            self.exit_s2 = db.Exit("s2", self.lobby, self.lobby)
        db.store(self.exit_s1)
        db.store(self.exit_s2)
        self.assert_response("s", startswith="Which command do you mean")

    def test_many_exits_one_command(self):
        with locks.authority_of(locks.SYSTEM):
            self.exit_h1 = db.Exit("h1", self.lobby, self.lobby)
            self.exit_h2 = db.Exit("h2", self.lobby, self.lobby)
        db.store(self.exit_h1)
        db.store(self.exit_h2)
        self.assert_response("h", startswith="Available commands:")

    def test_many_exits_one_nospace(self):
        with locks.authority_of(locks.SYSTEM):
            self.exit_zzza = db.Exit("zzza", self.lobby, self.lobby)
            self.exit_zzzb = db.Exit("zzzb", self.lobby, self.lobby)
        db.store(self.exit_zzza)
        db.store(self.exit_zzzb)
        self.assert_response("zzz foo", "Spaaaaaaaaaaaaaace. (foo).")

    def test_re(self):
        self.assert_response("re", startswith="Which command do you mean")
