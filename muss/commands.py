from pyparsing import SkipTo, StringEnd

from handler import Command

class Emote(Command):
    name = ["pose", "emote"]
    nospace_name = [":"]
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        player.emit("{} {}".format(player, args['text']))


class Say(Command):
    name = ["say"]
    nospace_name = ["'", '"']
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        player.send('You say, "{}"'.format(args['text']))
        player.emit('{} says, "{}"'.format(player, args['text']), exceptions=[player])
