from pyparsing import SkipTo, StringEnd, Word, alphas, Optional

from handler import Command

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
