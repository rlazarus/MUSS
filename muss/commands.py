import inspect
from pyparsing import SkipTo, StringEnd, Word, alphas, Optional

from muss.handler import Command, Mode, NormalMode
from utils import find_by_name

class FooOne(Command):
    name = ["foobar", "test"]
    help_text = "A test command."

    def execute(self, player, args):
        player.send("You triggered FooOne.")


class FooTwo(Command):
    name = ["foobaz", "test"]
    help_text = "A test command."

    def execute(self, player, args):
        player.send("You triggered FooTwo.")


class Chat(Command):
    name = "chat"
    nospace_name = "."
    args = Optional(Word(alphas)("channel") + SkipTo(StringEnd())("text"))
    help_text = "Chat on a specific channel, or enter/leave channel modes."

    def execute(self, player, args):
        # we need to use get() for channel but not text, because
        # text will always exist, it just might be empty
        if args.get('channel'):
            if args['text']:
                # (send the text to the channel)
                pass
            else:
                # (switch to the channel's mode)
                pass
        else:
            player.mode = NormalMode()
            player.send("You are now in Normal Mode.")


class Emote(Command):
    name = ["pose", "emote"]
    nospace_name = ":"
    args = SkipTo(StringEnd())("text")
    usage = ["emote <action>", "pose <action>", ":<action>"]
    help_text = "Perform an action visible to the people in your location."

    def execute(self, player, args):
        player.emit("{} {}".format(player, args['text']))
        # !!! This will have to check channel modes when we have them


class Help(Command):
    name = ["help"]
    args = Optional(Word(alphas)("command"))
    usage = ["help", "help <command>"]
    help_text = "See the list of available commands, or get help for a specific command (not yet supported)."

    def execute(self, player, args):
        commands = [cls for (name, cls) in globals().items() if inspect.isclass(cls) and issubclass(cls, Command) and cls is not Command]
        if args.get("command"):
            perfect_matches, partial_matches = find_by_name(args["command"], commands)
            if len(perfect_matches) == 1 or (len(partial_matches) == 1 and not perfect_matches):
                if perfect_matches:
                    name, command = perfect_matches[0]
                else:
                    name, command = partial_matches[1]
                if hasattr(command, "usage"):
                    usage = ""
                    for usecase in command.usage:
                        usage += "\r\n\t{}".format(usecase)
                else:
                    usage = "\r\n\t" + name.lower()
                name_list = ""
                other_names = command().names
                if len(other_names) > 1:
                    other_names = [a for a in other_names if a != name]
                    other_names.sort()
                    name_list = " ({})".format(", ".join(other_names)).upper()
                fullhelp = "{}{}\r\nUsage: {}".format(name.upper(), name_list, usage)
                if hasattr(command, "help_text"):
                    fullhelp += "\r\n"*2 + command.help_text
                player.send(fullhelp)
            elif perfect_matches:
                player.send('I don\'t know which "{}" you needed help with!'.format(perfect_matches[0][0]))
            elif partial_matches:
                matches = [a[0] for a in partial_matches]
                player.send("Which one did you want help with: {}?".format(", ".join(matches)))
            else:
                player.send('I don\'t have any help for "{}."'.format(args["command"]))
        else:
            # when we get command storage sorted out, this'll be replaced
            all_names = []
            for command in commands:
                all_names.extend(command().names)
                all_names.extend(command().nospace_names)
            all_names = sorted(set(all_names)) # alphabetize, remove dupes
            player.emit('Available commands: {}\r\n\r\nUse "help <command>" for more information about a specific command.'.format(", ".join(all_names)))


class Say(Command):
    name = "say"
    nospace_name = ["'", '"']
    args = SkipTo(StringEnd())("text")
    usage = ["say <text>", "'<statement>", '"<statement>']
    help_text = "Say something to the people in your location."

    def execute(self, player, args):
        if args['text']:
            if isinstance(player.mode, SayMode):
                prefix = "* "
            else:
                prefix = ""
            player.send('{}You say, "{}"'.format(prefix, args['text']))
            player.emit('{} says, "{}"'.format(player, args['text']), exceptions=[player])
        else:
            player.mode = SayMode()
            player.send("You are now in Say Mode. To get back to Normal Mode, type: .")


class SayMode(Mode):

    """
    Mode entered when a player uses the say command with no arguments.
    """

    def handle(self, player, line):
        """
        Check for escapes and emotes, then pass through to say.
        """

        if line.startswith("/"):
            NormalMode().handle(player, line[1:])
            return

        for command in [Emote, Chat]:
            for name in command().nospace_names:
                if line.startswith(name):
                    arguments = line.split(name, 1)[1]
                    args = command.args.parseString(arguments).asDict()
                    command().execute(player, args)
                    return

        args = Say.args.parseString(line).asDict()
        Say().execute(player, args)


class Quit(Command):
    name = "quit"
    help_text = "Quits the game."

    def execute(self, player, args):
        import muss.server
        player.send("Bye!")
        muss.server.factory.allProtocols[player.name].transport.loseConnection()
