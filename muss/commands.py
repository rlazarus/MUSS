import inspect
from pyparsing import SkipTo, StringEnd, Word, Optional, alphas

from muss.handler import Mode, NormalMode
from muss.locks import LockFailedError
from muss.parser import NotFoundError, Command, CommandName, PlayerName


class FooOne(Command):
    name = ["foobar", "test"]
    args = Word(alphas)
    help_text = "A test command (foobar)."

    def execute(self, player, args):
        player.send("You triggered FooOne.")


class FooTwo(Command):
    name = ["foobaz", "test"]
    args = Word(alphas) + Optional(Word(alphas))
    help_text = "A test command (foobaz)."

    def execute(self, player, args):
        player.send("You triggered FooTwo.")

class FooThree(Command):
    name = ["asdf"]
    args = Word(alphas) * 3 + Optional(Word(alphas) + Word(alphas))
    help_text = "A test command (asdf)."

    def execute(self, player, args):
        player.send("You triggered asdf.")


class LoremIpsum(Command):
    name = "loremipsum"
    help_text = "Spams you with a whole bunch of example text."

    def execute(self, player, args):
        player.send("Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Nam liber tempor cum soluta nobis eleifend option congue nihil imperdiet doming id quod mazim placerat facer possim assum. Typi non habent claritatem insitam; est usus legentis in iis qui facit eorum claritatem. Investigationes demonstraverunt lectores legere me lius quod ii legunt saepius. Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.")
            

class Size(Command):
    name = "size"
    help_text = "Get terminal size."

    def execute(self, player, args):
        from utils import get_terminal_size
        player.send(repr(get_terminal_size()))


class Chat(Command):
    name = "chat"
    nospace_name = "."
    args = Optional(Word(alphas)("channel") + SkipTo(StringEnd())("text"))
    usage = [".", "chat <channel>", "chat <channel> <text>"]
    help_text = "Chat on a specific channel, or enter/leave channel modes."

    def execute(self, player, args):
        if args.get('channel'):
            # text will always exist, it just might be empty
            if args['text']:
                # (send the text to the channel)
                pass
            else:
                # (switch to the channel's mode)
                pass
        else:
            player.mode = NormalMode()
            player.send("You are now in Normal Mode.")


class Pose(Command):
    name = ["pose", "emote"]
    nospace_name = ":"
    args = SkipTo(StringEnd())("text")
    usage = ["emote <action>", "pose <action>", ":<action>"]
    help_text = "Perform an action visible to the people in your location."

    def execute(self, player, args):
        player.emit("{} {}".format(player, args['text']))
        # !!! This will have to check channel modes when we have them


class Semipose(Command):
    nospace_name = ";"
    args = SkipTo(StringEnd())("text")
    usage = ";<action>"
    help_text = """Perform an action visible to the people in your location, without a space after your name. e.g.:

    ;'s pet cat follows along behind    =>  Fizz's pet cat follows along behind"""

    def execute(self, player, args):
        player.emit("{}{}".format(player, args['text']))
        # !!! This will have to check channel modes when we have them


class Usage(Command):
    name = "usage"
    args = CommandName()("command")
    help_text = "Display just the usage for a command, rather than its full help."

    def execute(self, player, args):
        name, command = args["command"]
        for case in command().usages:
            player.emit("\t" + case)


class Help(Command):
    name = ["help"]
    args = Optional(CommandName()("command"))
    help_text = "See the list of available commands, or get help for a specific command."

    def execute(self, player, args):
        if args.get("command"):
            name, command = args["command"]
            name_list = ""
            other_names = command().names + command().nospace_names
            if len(other_names) > 1:
                other_names = [a for a in other_names if a != name]
                other_names.sort()
                name_list = " ({})".format(", ".join(other_names)).upper()
            player.send("{}{}".format(name.upper(), name_list))
            Usage().execute(player, {"command":{name:command}})
            if hasattr(command, "help_text"):
                player.send("\r\n" + command.help_text)
        else:
            # when we get command storage sorted out, this'll be replaced
            all_names = []
            for command in all_commands():
                all_names.extend(command().names)
                all_names.extend(command().nospace_names)
            all_names = sorted(set(all_names))
            player.emit('Available commands: {}\r\n\r\nUse "help <command>" for more information about a specific command.'.format(", ".join(all_names)))


class Say(Command):
    name = "say"
    nospace_name = ["'", '"']
    args = SkipTo(StringEnd())("text")
    usage = ["say <statement>", "'<statement>", '"<statement>']
    help_text = "Say something to the people in your location."

    def execute(self, player, args):
        if args['text']:
            if isinstance(player.mode, SayMode):
                prefix = "* "
            else:
                prefix = ""
            player.send('{}You say, "{}"'.format(prefix, args['text']))
            player.emit('{} says, "{}"'.format(player, args['text']), exceptions=[player])
        else:
            player.mode = SayMode()
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

        for command in [Pose, Chat]:
            for name in command().nospace_names:
                if line.startswith(name):
                    arguments = line.split(name, 1)[1]
                    args = command.args.parseString(arguments).asDict()
                    command().execute(player, args)
                    return

        args = Say.args.parseString(line).asDict()
        Say().execute(player, args)


class Quit(Command):
    name = "quit"
    help_text = "Quits the game."

    def execute(self, player, args):
        import muss.server
        player.send("Bye!")
        muss.server.factory.allProtocols[player.name].transport.loseConnection()


class Poke(Command):
    name = "poke"
    args = PlayerName()("victim")
    help_text = "Pokes another player, at any location."
    
    def execute(self, player, args):
        victim = args["victim"]
        if player.location == victim.location:
            player.send("You poke {}!".format(victim))
            victim.send("{} pokes you!".format(player))
            player.emit("{} pokes {}!".format(player, victim), exceptions=[player, victim])
        else:
            player.send("From afar, you poke {}!".format(victim))
            victim.send("From afar, {} pokes you!".format(player))
            

class Examine(Command):
    name = "examine"
    help_text = "Show details about an object, including all of its visible attributes."
    # Actually, so far it takes no arguments and examines the player.

    def execute(self, player, args):
        obj = player
        player.send("{} (#{}, {}, owned by {})".format(obj, obj.uid, obj.type, obj.owner))
        suppress = set(["name", "uid", "type", "owner", "attr_locks", "mode", "password", "textwrapper"]) # attrs not to list
        for attr in sorted(player.__dict__):
            if attr not in suppress:
                try:
                    player.send("{}: {}".format(attr, repr(getattr(player, attr))))
                except LockFailedError:
                    player.send("{} (hidden)".format(attr))


def all_commands(asDict=False):
    """
    Return a set of all the command classes defined here.
    """
    commands = []
    byname = {}
    for cls in globals().values():
        if inspect.isclass(cls) and issubclass(cls, Command) and cls is not Command:
            commands.append(cls)
            for name in cls().names + cls().nospace_names:
                if byname.get(name):
                    byname[name].append(cls)
                else:
                    byname[name] = [cls]
    if asDict:
        return byname
    else:
        return set(commands)
