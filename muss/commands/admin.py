from pyparsing import SkipTo, StringEnd

from muss.locks import authority_of, SYSTEM
from muss.parser import Command


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
