# Commands for communicating with other players.

import pyparsing as pyp

from muss import channels, db, handler, parser, utils, locks


class Chat(parser.Command):
    name = "chat"
    nospace_name = "."
    usage = [".", "chat <channel>", "chat <channel> <text>"]
    help_text = "Chat on a specific channel, or enter/leave channel modes."

    @classmethod
    def args(cls, player):
        return pyp.Optional(
            parser.OneOf(channels.all())("channel").setName("channel") +
            pyp.Optional(parser.Text("text")))

    def execute(self, player, args):
        if 'channel' in args:
            channel = args['channel']

            if 'text' in args:
                if args['text'].startswith(Emote.nospace_name):
                    channel.pose(player, args['text'][1:])
                elif args['text'].startswith(SpacelessEmote.nospace_name):
                    channel.semipose(player, args['text'][1:])
                else:
                    channel.say(player, args['text'])
            else:
                player.enter_mode(ChatMode(channel))
                player.send("You are now chatting to {}. To get back to Normal "
                            "Mode, type: .".format(channel))
        elif (isinstance(player.mode, SayMode) or
              isinstance(player.mode, ChatMode)):
            player.exit_mode()
            player.send("You are now in Normal Mode.")
        else:
            raise utils.UserError("You're already in Normal Mode.")


class Emote(parser.Command):
    name = ["emote"]
    nospace_name = ":"
    usage = ["emote <action>", ":<action>"]
    help_text = "Perform an action visible to the people in your location."

    @classmethod
    def args(cls, player):
        return parser.Text("text")

    def execute(self, player, args):
        player.emit("{} {}".format(player, args['text']))


class Say(parser.Command):
    name = "say"
    nospace_name = ["'", '"']
    usage = ["say <statement>", "'<statement>", '"<statement>']
    help_text = "Say something to the people in your location."

    @classmethod
    def args(cls, player):
        return pyp.restOfLine("text")

    def execute(self, player, args):
        if args['text']:
            if isinstance(player.mode, SayMode):
                prefix = "* "
            else:
                prefix = ""
            player.send('{}You say, "{}"'.format(prefix, args['text']))
            player.emit('{} says, "{}"'.format(player, args['text']),
                        exceptions=[player])
        else:
            player.enter_mode(SayMode())
            player.send("You are now in Say Mode. To get back to Normal Mode, "
                        "type: .")


class SayMode(handler.Mode):

    """
    Mode entered when a player uses the say command with no arguments.
    """

    def handle(self, player, line):
        """
        Check for escapes and emotes, then pass through to say.
        """

        if line.startswith("/"):
            handler.NormalMode().handle(player, line[1:])
            return

        for command in [Emote, SpacelessEmote, Chat]:
            for name in command().nospace_names:
                if line.startswith(name):
                    arguments = line.split(name, 1)[1]
                    args = command.args(player).parseString(arguments).asDict()

                    command().execute(player, args)
                    return

        args = Say.args(player).parseString(line).asDict()
        Say().execute(player, args)


class ChatMode(handler.Mode):

    """
    Mode for chatting on a particular channel.
    """

    def __init__(self, channel):
        self.channel = channel

    def handle(self, player, line):
        if line.startswith('/'):
            handler.NormalMode().handle(player, line[1:])
            return

        for name in Chat().nospace_names:
            if line.startswith(name):
                arguments = line.split(name, 1)[1]
                args = Chat.args(player).parseString(arguments).asDict()
                Chat().execute(player, args)
                return

        if line.startswith(Emote.nospace_name):
            self.channel.pose(player, line[1:])
        elif line.startswith(SpacelessEmote.nospace_name):
            self.channel.semipose(player, line[1:])
        else:
            self.channel.say(player, line)


class SpacelessEmote(parser.Command):
    nospace_name = ";"
    usage = ";<action>"
    help_text = ("Perform an action visible to the people in your location, "
                 "without a space after your name. e.g.:\n"
                 "\n"
                 ";'s pet cat follows along behind    =>  Fizz's pet cat "
                 "follows along behind")

    @classmethod
    def args(cls, player):
        return pyp.restOfLine("text")

    def execute(self, player, args):
        player.emit("{}{}".format(player, args['text']))


class Tell(parser.Command):
    name = "tell"
    usage = "tell <player> <message>"
    help_text = ("Send a private message to another player. Player names may "
                 "be abbreviated.")

    @classmethod
    def args(cls, player):
        return parser.PlayerName()("target") + parser.Text("message")

    def execute(self, player, args):
        target = args['target']
        message = args['message']
        if target.connected:
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
            with locks.authority_of(locks.SYSTEM):
                player.last_told = target
        else:
            player.send("{} is not connected.".format(target))


class Retell(parser.Command):
    name = "retell"
    usage = "retell <message>"
    help_text = ("Send another private message to the same player you sent the "
                 "last one to.")

    @classmethod
    def args(cls, player):
        return parser.Text("message")

    def execute(self, player, args):
        if player.last_told:
            args["target"] = player.last_told
            Tell().execute(player, args)
        else:
            player.send("You haven't sent a tell to anyone yet.")


class Pose(parser.Command):
    name = "pose"
    usage = ["pose", "pose <new position>"]
    help_text = ("Set the position that will be displayed to other people when "
                 "they look at you or around the room you're in. (Call it with "
                 "no position string to clear your current position.) e.g.:\n"
                 "\n"
                 "pose sitting on the floor    =>  "
                 "Fizz is sitting on the floor\n"
                 "pose pacing back and forth   =>  "
                 "Fizz is pacing back and forth")

    @classmethod
    def args(cls, player):
        return pyp.restOfLine("text")

    def execute(self, player, args):
        position = args["text"].strip()
        if position:
            player.position = position
            player.emit("{} is now {}.".format(player, position))
            # no player/others split to avoid things like this:
            # "You are now standing on their head."
        else:
            if player.position:
                oldposition = player.position
                player.position = None
                player.emit("{} is no longer {}.".format(player, oldposition))
            else:
                player.send("You're not currently posing.")


class Who(parser.Command):
    name = "who"
    help_text = "List the connected players."

    def execute(self, player, args):
        players = db.find_all(lambda x: isinstance(x, db.Player) and
                                        x.connected)
        player.send("{number} {playersare} connected: {players}.".format(
            number=len(players),
            playersare="player is" if len(players) == 1 else "players are",
            players=utils.comma_and(map(str, list(players)))))
