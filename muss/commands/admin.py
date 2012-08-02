from code import InteractiveConsole
from pyparsing import SkipTo, StringEnd
import sys
from StringIO import StringIO

from muss.handler import Mode, PromptMode
from muss.locks import LockFailedError, authority, authority_of, SYSTEM
from muss.parser import Command
from muss.utils import UserError


class Python(Command):
    name = "python"
    help_text = "Enter an interactive Python session."

    def execute(self, player, args):
        if authority() is not SYSTEM:
            # When user code is implemented, this will create an untrusted REPL under the player's authority.
            raise UserError("Not yet implemented: for now, sudo is required.")

        player.send("***********")
        player.send("* WARNING *")
        player.send("***********")
        player.send("")
        player.send("You are working interactively with the actual Python process running the game. Careless actions here can really permanently foul up important things.")
        player.send("")

        def check_password(line):
            if player.hash(line) == player.password:
                with authority_of(SYSTEM):
                    player.enter_mode(PythonMode(player))
            else:
                player.send("Incorrect.")

        player.enter_mode(PromptMode(player, "To proceed, enter your password:", check_password))


class PythonMode(Mode):
    blank_line = False

    def __init__(self, player):
        if authority() is not SYSTEM:
            raise LockFailedError("PythonMode requires system authority.")

        self.console = InteractiveConsole()
        player.send(">>>")

    def handle(self, player, line):
        if line == ".":
            player.send("Exiting python.")
            player.exit_mode()
            return

        with authority_of(SYSTEM):
            try:
                sys.stdout = sys.stderr = StringIO()
                if self.console.push(line):
                    player.send("...")
                else:
                    player.send(sys.stdout.getvalue())
                    player.send(">>>")
            finally:
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__


class Sudo(Command):
    name = "sudo"
    usage = "sudo <command>"
    help_text = "Execute any other command with SYSTEM privileges. Only accessible if the debug flag is set on your player object."

    @classmethod
    def args(cls, player):
        return SkipTo(StringEnd())("line")

    def execute(self, player, args):
        if getattr(player, "debug"):
            line = args["line"]
            with authority_of(SYSTEM):
                player.mode.handle(player, line)
        else:
            player.send("You're not set for debugging!")
