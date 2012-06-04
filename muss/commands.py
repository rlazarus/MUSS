import inspect
from pyparsing import SkipTo, StringEnd, Word, alphas, Optional

from muss.handler import Command, Mode, NormalMode

class FooOne(Command):
    name = ["foobar", "test"]
    helptext = "A test command."

    def execute(self, player, args):
        player.send("You triggered FooOne.")


class FooTwo(Command):
    name = ["foobaz", "test"]
    helptext = "A test command."

    def execute(self, player, args):
        player.send("You triggered FooTwo.")


class Chat(Command):
    name = "chat"
    nospace_name = "."
    args = Optional(Word(alphas)("channel") + SkipTo(StringEnd())("text"))
    helptext = "Chat on a specific channel, or enter/leave channel modes."

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
    helptext = "Perform an action visible to the people in your location."
    examples = [(":waves", "Fizz waves")]

    def execute(self, player, args):
        player.emit("{} {}".format(player, args['text']))
        # !!! This will have to check channel modes when we have them


class Help(Command):
    name = ["help"]
    # args = Optional(Word(alphas)("command"))
    usage = ["help", "help <command>"]
    helptext = "See the list of available commands, or get help for a specific command (not yet supported)."

    def execute(self, player, args):
        if args.get("command"):
            # find command by name, generate help
            pass
        else:
            import muss.commands
            commands = [cls for (name, cls) in inspect.getmembers(muss.commands) if inspect.isclass(cls) and issubclass(cls, Command) and cls is not Command]
            # when we get command storage sorted out, this'll be replaced
            all_names = []
            for command in commands:
                # this ridiculous hack will depart with issue #19
                if isinstance(command.name, list):
                    all_names.extend(command.name)
                else:
                    all_names.append(command.name)
                if isinstance(command.nospace_name, list):
                    all_names.extend(command.nospace_name)
                else:
                    all_names.append(command.nospace_name)
            all_names = sorted(set(all_names)) # alphabetize, remove dupes
            player.emit('Available commands: {}\r\n\r\nUse "help <command>" for more information about a specific command.'.format(", ".join(all_names)))


class Say(Command):
    name = "say"
    nospace_name = ["'", '"']
    args = SkipTo(StringEnd())("text")
    usage = ["say <text>", "'<statement>", '"<statement>']
    helptext = "Say something to the people in your location."
    examples = [("'Hello!", 'Fizz says, "Hello!"')]

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
            for name in command.nospace_name:
                if line.startswith(name):
                    arguments = line.split(name, 1)[1]
                    args = command.args.parseString(arguments).asDict()
                    command().execute(player, args)
                    return

        args = Say.args.parseString(line).asDict()
        Say().execute(player, args)


class Quit(Command):
    name = "quit"
    helptext = "Quits the game."

    def execute(self, player, args):
        import muss.server
        player.send("Bye!")
        muss.server.factory.allProtocols[player.name].transport.loseConnection()
