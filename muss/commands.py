from pyparsing import SkipTo, StringEnd, Word, alphas, Optional

from muss.handler import Command, Mode, NormalMode

class FooOne(Command):
    name = ["foobar", "test"]
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        pass


class FooTwo(Command):
    name = ["foobaz", "test"]
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        pass


class Chat(Command):
    name = "chat"
    nospace_name = "."
    args = Optional(Word(alphas)("channel") + SkipTo(StringEnd())("text"))

    def execute(self, player, args):
        if args['channel']:
            if args['text']:
                # (send the text to the channel)
                pass
            else:
                # (switch to the channel's mode)
                pass
        else:
            # (switch to normal mode)
            pass


class Emote(Command):
    name = ["pose", "emote"]
    nospace_name = ":"
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        player.emit("{} {}".format(player, args['text']))
        # !!! This will have to check channel, when we have channels.


class Say(Command):
    name = "say"
    nospace_name = ["'", '"']
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        if args['text']:
            player.send('You say, "{}"'.format(args['text']))
            player.emit('{} says, "{}"'.format(player, args['text']), exceptions=[player])
        else:
            player.send("I would go into say mode now, but I can't yet.")


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
                    # I should probably check for ambiguity here, but I'm not yet.
                    arguments = line.split(name, 1)[1]
                    args = command.args.ParseString(arguments).asDict()
                    command().execute(player, args)
                    return

        args = Say.args.parseString(line).asDict()
        Say().execute(player, args)