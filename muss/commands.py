from pyparsing import SkipTo, StringEnd, Word, alphas, Optional

from muss.handler import Command, Mode, NormalMode

class FooOne(Command):
    name = ["foobar", "test"]
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        player.send("You triggered FooOne.")


class FooTwo(Command):
    name = ["foobaz", "test"]
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        player.send("You triggered FooTwo.")


class Chat(Command):
    name = "chat"
    nospace_name = "."
    args = Optional(Word(alphas)("channel") + SkipTo(StringEnd())("text"))

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

    def execute(self, player, args):
        player.emit("{} {}".format(player, args['text']))
        # !!! This will have to check channel modes when we have them


class Say(Command):
    name = "say"
    nospace_name = ["'", '"']
    args = SkipTo(StringEnd())("text")

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
