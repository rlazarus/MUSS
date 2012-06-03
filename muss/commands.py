from pyparsing import SkipTo, StringEnd

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


class Emote(Command):
    name = ["pose", "emote"]
    nospace_name = ":"
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        player.emit("{} {}".format(player, args['text']))


class Say(Command):
    name = "say"
    nospace_name = ["'", '"']
    args = SkipTo(StringEnd())("text")

    def execute(self, player, args):
        player.send('You say, "{}"'.format(args['text']))
        player.emit('{} says, "{}"'.format(player, args['text']), exceptions=[player])


class Quit(Command):
    name = "quit"

    def execute(self, player, args):
        import muss.server
        player.send("Bye!")
        muss.server.factory.allProtocols[player.name].transport.loseConnection()
