# Commands for communicating with other players.

from pyparsing import ParseException, Token, Optional, SkipTo, StringEnd, Word, alphas

from muss.db import Player, find_all
from muss.handler import Mode, NormalMode
from muss.parser import Command, EmptyLine, ConnectedPlayer, PlayerName
from muss.utils import comma_and


class Chat(Command):
    name = "chat"
    nospace_name = "."
    usage = [".", "chat <channel>", "chat <channel> <text>"]
    help_text = "Chat on a specific channel, or enter/leave channel modes."

    @classmethod
    def args(cls, player):
        return EmptyLine() | (Word(alphas)("channel") + SkipTo(StringEnd())("text"))

    def execute(self, player, args):
        if args.get('channel'):
            # text will always exist, it just might be empty
            if args['text']:
                # (send the text to the channel)
                pass
            else:
                # (switch to the channel's mode)
                pass
        elif isinstance(player.mode, SayMode):
            player.exit_mode()
            player.send("You are now in Normal Mode.")


class Pose(Command):
    name = ["pose", "emote"]
    nospace_name = ":"
    usage = ["emote <action>", "pose <action>", ":<action>"]
    help_text = "Perform an action visible to the people in your location."

    @classmethod
    def args(cls, player):
        return SkipTo(StringEnd())("text")

    def execute(self, player, args):
        player.emit("{} {}".format(player, args['text']))


class Say(Command):
    name = "say"
    nospace_name = ["'", '"']
    usage = ["say <statement>", "'<statement>", '"<statement>']
    help_text = "Say something to the people in your location."

    @classmethod
    def args(cls, player):
        return SkipTo(StringEnd())("text")

    def execute(self, player, args):
        if args['text']:
            if isinstance(player.mode, SayMode):
                prefix = "* "
            else:
                prefix = ""
            player.send('{}You say, "{}"'.format(prefix, args['text']))
            player.emit('{} says, "{}"'.format(player, args['text']), exceptions=[player])
        else:
            player.enter_mode(SayMode())
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

        for command in [Pose, Semipose, Chat]:
            for name in command().nospace_names:
                if line.startswith(name):
                    arguments = line.split(name, 1)[1]
                    args = command.args(player).parseString(arguments).asDict()

                    command().execute(player, args)
                    return

        args = Say.args(player).parseString(line).asDict()
        Say().execute(player, args)


class Semipose(Command):
    nospace_name = ";"
    usage = ";<action>"
    help_text = """Perform an action visible to the people in your location, without a space after your name. e.g.:

    ;'s pet cat follows along behind    =>  Fizz's pet cat follows along behind"""

    @classmethod
    def args(cls, player):
        return SkipTo(StringEnd())("text")

    def execute(self, player, args):
        player.emit("{}{}".format(player, args['text']))


class Tell(Command):
    name = "tell"
    usage = "tell <player> <message>"
    help_text = "Send a private message to another player. Player names may be abbreviated."

    @classmethod
    def args(cls, player):
        return PlayerName()("target") + SkipTo(StringEnd())("message")

    def execute(self, player, args):
        target = args['target']
        message = args['message']
        if target.connected:
            if message:
                firstchar = message[0]
                if firstchar in [":", ";"]:
                    message = message[1:]
                    if firstchar is ":":
                        message = " " + message
                    target.send("Tell: {}{}".format(player, message))
                    player.send("To {}: {}{}".format(target, player, message))
                else:
                    target.send("{} tells you: {}".format(player, message))
                    player.send("You tell {}: {}".format(target, message))
            else:
                # This is a hack to force handler to do the error reporting,
                # since we don't have a parse token for "non-empty string."
                # Besides, we'll want this block for tell mode, later.
                raise ParseException("-", 0, "", Token().setName("message"))
        else:
            player.send("{} is not connected.".format(target))


class Who(Command):
    name = "who"
    help_text = "List the connected players."

    def execute(self, player, args):
        players = find_all(lambda x: isinstance(x, Player) and x.connected)
        player.send("{number} {playersare} connected: {players}.".format(
            number=len(players),
            playersare="player is" if len(players) == 1 else "players are",
            players=comma_and(map(str, list(players)))
        ))
