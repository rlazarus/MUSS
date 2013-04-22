# Player-to-server connections.

from muss import parser


class Quit(parser.Command):
    name = "quit"
    help_text = "Quits the game."

    def execute(self, player, args):
        import muss.server
        player.send("Bye!")
        muss.server.factory.allProtocols[player.name].transport.loseConnection()


class Size(parser.Command):
    name = "size"
    help_text = "Get terminal size."

    def execute(self, player, args):
        # not useful yet, just a placeholder.
        player.send(repr(get_terminal_size()))
