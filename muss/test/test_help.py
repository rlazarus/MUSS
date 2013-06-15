from muss import db, handler, locks, parser
from muss.test import common_tools


class CommandTestCase(common_tools.MUSSTestCase):
    def test_usage(self):
        self.assert_response("usage poke", "poke <player>")
        self.assert_response("usage usage", "usage <command>")
        self.assert_response("usage quit", "quit")
        self.assert_response("usage ;", ";<action>")

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
