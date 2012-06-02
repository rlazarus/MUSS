from pyparsing import SkipTo, StringEnd, Word, alphas

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
    args = Word(alphas)("channel") + SkipTo(StringEnd())("text")

    def execute(self, player, args):
        # (search channels, make sure ours exists and we're in it)
        if args['text']:
            # (send the text to the channel)
            pass
        else:
            # (if we're in a channel mode, switch back to normal mode)
            # (if we're not, enter one)
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


class Slash(Command):
    nospace_name = "/"
    args = Word(alphas)("command") + SkipTo(StringEnd())("arguments")

    def execute(self, player, args):
        # (act like normal mode)
        pass
