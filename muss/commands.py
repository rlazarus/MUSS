import inspect
from pyparsing import SkipTo, StringEnd, Word, Optional, alphas

from muss.handler import Mode, NormalMode
from muss.locks import LockFailedError
from muss.parser import NotFoundError, Command, CommandName, PlayerName, ObjectIn, ReachableObject, ObjectUid
from muss.utils import get_terminal_size, UserError, find_one
from muss.db import find_all, Object, store


class FooOne(Command):
    name = ["foobar", "test"]
    help_text = "A test command (foobar)."

    @classmethod
    def args(cls, player):
        return Word(alphas)

    def execute(self, player, args):
        player.send("You triggered FooOne.")


class FooTwo(Command):
    name = ["foobaz", "test"]
    help_text = "A test command (foobaz)."


    @classmethod
    def args(cls, player):
        return Word(alphas) + Optional(Word(alphas))

    def execute(self, player, args):
        player.send("You triggered FooTwo.")

class FooThree(Command):
    name = ["asdf"]
    help_text = "A test command (asdf)."

    @classmethod
    def args(cls, player):
        return Word(alphas) * 3 + Optional(Word(alphas) + Word(alphas))

    def execute(self, player, args):
        player.send("You triggered asdf.")


class Lorem(Command):
    name = "lorem"
    help_text = "Spams you with a whole bunch of example text."

    def execute(self, player, args):
        player.send("Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Nam liber tempor cum soluta nobis eleifend option congue nihil imperdiet doming id quod mazim placerat facer possim assum. Typi non habent claritatem insitam; est usus legentis in iis qui facit eorum claritatem. Investigationes demonstraverunt lectores legere me lius quod ii legunt saepius. Claritas est etiam processus dynamicus, qui sequitur mutationem consuetudium lectorum. Mirum est notare quam littera gothica, quam nunc putamus parum claram, anteposuerit litterarum formas humanitatis per seacula quarta decima et quinta decima. Eodem modo typi, qui nunc nobis videntur parum clari, fiant sollemnes in futurum.")
            

class WhatIs(Command):
    name = "whatis"
    help_text = "Get the name of an object from its UID."

    @classmethod
    def args(cls, player):
        return ObjectUid()("uid")

    def execute(self, player, args):
        item = args["uid"]
        player.send("Item #{} is {}.".format(item.uid, item.name))


class Size(Command):
    name = "size"
    help_text = "Get terminal size."

    def execute(self, player, args):
        # not useful yet, just a placeholder.
        player.send(repr(get_terminal_size()))


class Inventory(Command):
    name = "inventory"
    help_text = "Shows you what you're carrying."

    def execute(self, player, args):
        inv = find_all(lambda i: i.location == player)
        if inv:
            inv_names = sorted([i.name for i in inv])
            inv_string = ", ".join(inv_names)
            player.send("You are carrying: {}.".format(inv_string))
        else:
            player.send("You are not carrying anything.")


class Take(Command):
    name = ["take", "get"]
    usage = ["take <item>", "get <item>"]
    help_text = "Pick up an item in your location."

    @classmethod
    def args(cls, player):
        return ObjectIn(player.location)("item")

    def execute(self, player, args):
        item = args["item"]
        item.move_to(player)
        player.send("You take {}.".format(item.name))
        player.emit("{} takes {}.".format(player.name, item.name), exceptions=[player])


class Create(Command):
    name = "create"
    usage = "create <name>" # later, optional type; laterer, name also optional
    help_text = "Create an item in your inventory."

    @classmethod
    def args(cls, player):
        return SkipTo(StringEnd())("name")

    def execute(self, player, args):
        name = args["name"]
        if not name:
            raise UserError("A name is required.")
            return
        new_item = Object(name, player)
        store(new_item)
        player.send("Created item #{}, {}.".format(new_item.uid, new_item.name))


class Destroy(Command):
    name = "destroy"
    usage = "destroy <uid>"
    help_text = "Destroy an item, given its UID. This command cannot be abbreviated; you must use the full name, to be sure you really mean it."
    require_full = True

    @classmethod
    def args(cls, player):
        return ObjectUid()("target")

    def execute(self, player, args):
        target = args["target"]
        target_uid = target.uid
        target_name = target.name
        target.destroy()
        player.send("You destroy #{} ({}).".format(target_uid, target_name))
        player.emit("{} destroys {}.".format(player.name, target_name), exceptions=[player])


class Drop(Command):
    name = "drop"
    usage = ["drop <item>"]
    help_text = "Drop an item from your inventory into your location."

    @classmethod
    def args(cls, player):
        return ObjectIn(player)("item")

    def execute(self, player, args):
        item = args["item"]
        item.move_to(player.location)
        player.send("You drop {}.".format(item.name))
        player.emit("{} drops {}.".format(player.name, item.name), exceptions=[player])


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
        else:
            player.mode = NormalMode()
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


class Usage(Command):
    name = "usage"
    help_text = "Display just the usage for a command, rather than its full help."

    @classmethod
    def args(cls, player):
        return CommandName()("command")

    def execute(self, player, args):
        name, command = args["command"]
        for case in command().usages:
            player.send("\t" + case)


class Help(Command):
    name = ["help"]
    help_text = "See the list of available commands, or get help for a specific command."

    @classmethod
    def args(cls, player):
        return SkipTo(StringEnd())("command")

    def execute(self, player, args):
        if args["command"]:
            name, command = find_one(args["command"], all_commands(), attributes=["names", "nospace_names"])
            name_list = ""
            other_names = command().names + command().nospace_names
            if len(other_names) > 1:
                other_names = [a for a in other_names if a != name]
                other_names.sort()
                name_list = " ({})".format(", ".join(other_names))
            player.send("{}{}".format(name, name_list).upper())
            player.send("Usage:")
            Usage().execute(player, {"command":(name,command)})
            if hasattr(command, "help_text"):
                player.send("")
                player.send(command.help_text)
        else:
            # when we get command storage sorted out, this'll be replaced
            all_names = []
            for command in all_commands():
                all_names.extend(command().names)
                all_names.extend(command().nospace_names)
            all_names = sorted(set(all_names))
            player.send("Available commands: {}".format(", ".join(all_names)))
            player.send('Use "help <command>" for more information about a specific command.')


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

        for command in [Pose, Semipose, Chat]:
            for name in command().nospace_names:
                if line.startswith(name):
                    arguments = line.split(name, 1)[1]
                    args = command.args(player).parseString(arguments).asDict()

                    command().execute(player, args)
                    return

        args = Say.args(player).parseString(line).asDict()
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
    help_text = "Pokes another player, at any location."

    @classmethod
    def args(cls, player):
        return PlayerName()("victim")

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

    @classmethod
    def args(cls, player):
        return ReachableObject(player)("obj") | ObjectUid()("obj")

    def execute(self, player, args):
        obj = args["obj"]
        player.send("{} (#{}, {}, owned by {})".format(obj, obj.uid, obj.type, obj.owner))
        suppress = set(["name", "uid", "type", "owner", "attr_locks", "mode", "password", "textwrapper"]) # attrs not to list
        for attr in sorted(player.__dict__):
            if attr not in suppress:
                try:
                    player.send("{}: {}".format(attr, repr(getattr(player, attr))))
                except LockFailedError:
                    player.send("{} (hidden)".format(attr))


class Look(Command):
    name = "look"
    help_text = "Show an object's description. If it has contents or exits, list them. If it's an exit, show its destination."

    @classmethod
    def args(cls, player):
        return Optional(ReachableObject(player)("obj") | ObjectUid()("obj"))

    def execute(self, player, args):
        try:
            obj = args["obj"]
        except KeyError:
            # If invoked without argument, look at our surroundings instead
            obj = player.location

        player.send(obj.name)
        player.send(obj.description)
        contents = obj.contents_string()
        if contents:
            player.send(contents)


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
