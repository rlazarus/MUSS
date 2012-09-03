# Commands relating to the in-game documentation.

from pyparsing import SkipTo, StringEnd

from muss.handler import all_commands
from muss.parser import Optional, Command, CommandName
from muss.utils import find_one


class Help(Command):
    name = ["help"]
    help_text = "See the list of available commands, or get help for a specific command."

    @classmethod
    def args(cls, player):
        return Optional(CommandName()("command"))

    def execute(self, player, args):
        if args.get("command"):
            name, command = args["command"]
            name_list = ""
            other_names = command().names + command().nospace_names
            if len(other_names) > 1:
                other_names = [a for a in other_names if a != name]
                other_names.sort()
                name_list = " ({})".format(", ".join(other_names))
            player.send("{}{}".format(name, name_list).upper())
            player.send("Usage:")
            Usage().execute(player, {"command":(name,command)})
            if hasattr(command, "help_text"):
                player.send("")
                player.send(command.help_text)
        else:
            # when we get command storage sorted out, this'll be replaced
            all_names = []
            for command in all_commands():
                all_names.extend(command().names)
                all_names.extend(command().nospace_names)
            all_names = sorted(set(all_names))
            player.send("Available commands: {}\nUse \"help <command>\" for more information about a specific command.".format(", ".join(all_names)))


class Usage(Command):
    name = "usage"
    help_text = "Display just the usage for a command, rather than its full help."

    @classmethod
    def args(cls, player):
        return CommandName()("command")

    def execute(self, player, args):
        name, command = args["command"]
        for case in command().usages:
            player.send("\t" + case)


