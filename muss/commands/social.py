# Commands for communicating with other players.

from pyparsing import Optional, SkipTo, StringEnd, Word, alphas

from muss.handler import Mode, NormalMode
from muss.parser import Command


class Chat(Command):
    name = "chat"
    nospace_name = "."
    usage = [".", "chat <channel>", "chat <channel> <text>"]
    help_text = "Chat on a specific channel, or enter/leave channel modes."

    @classmethod
    def args(cls, player):
        return Optional(Word(alphas)("channel") + SkipTo(StringEnd())("text"))

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


