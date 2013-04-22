import code
import sys
import StringIO

import pyparsing

from muss import handler, locks, parser, utils


class Python(parser.Command):
    name = "python"
    help_text = "Enter an interactive Python session."

    def execute(self, player, args):
        if locks.authority() is not locks.SYSTEM:
            # When user code is implemented, this will create an untrusted REPL under the player's authority.
            raise utils.UserError("Not yet implemented: for now, sudo is required.")

        player.send("***********")
        player.send("* WARNING *")
        player.send("***********")
        player.send("")
        player.send("You are working interactively with the actual Python process running the game. Careless actions here can really permanently foul up important things.")
        player.send("")

        def check_password(line):
            if player.hash(line) == player.password:
                with locks.authority_of(SYSTEM):
                    player.enter_mode(PythonMode(player))
            else:
                player.send("Incorrect.")

        player.enter_mode(handler.PromptMode(player, "To proceed, enter your password:", check_password))


class PythonMode(handler.Mode):
    blank_line = False

    def __init__(self, player):
        if locks.authority() is not locks.SYSTEM:
            raise locks.LockFailedError("PythonMode requires system authority.")

        self.console = code.InteractiveConsole()
        player.send(">>>")

    def handle(self, player, line):
        if line == ".":
            player.send("Exiting python.")
            player.exit_mode()
            return

        with locks.authority_of(locks.SYSTEM):
            try:
                sys.stdout = sys.stderr = StringIO.StringIO()
                if self.console.push(line):
                    player.send("...")
                else:
                    player.send(sys.stdout.getvalue())
                    player.send(">>>")
            finally:
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__


class Sudo(parser.Command):
    name = "sudo"
    usage = "sudo <command>"
    help_text = "Execute any other command with SYSTEM privileges. Only accessible if the debug flag is set on your player object."

    @classmethod
    def args(cls, player):
        return pyparsing.restOfLine("line")

    def execute(self, player, args):
        if getattr(player, "debug"):
            line = args["line"]
            with locks.authority_of(locks.SYSTEM):
                player.mode.handle(player, line)
        else:
            player.send("You're not set for debugging!")
