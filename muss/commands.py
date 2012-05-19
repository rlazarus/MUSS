from pyparsing import SkipTo, StringEnd

from handler import Command

class Say(Command):
    ### there's no syntax yet for names with no following space
    name = ["say", "'", '"']
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        player.send('You say, "{}"'.format(args['text']))
        player.emit('{} says, "{}"'.format(player, args['text']), exceptions=[player])
