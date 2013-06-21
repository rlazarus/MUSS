# Commands for building out the game world and managing objects.

import importlib
import pyparsing as pyp

from muss import db, locks, parser, utils, handler

class Create(parser.Command):
    name = "create"
    usage = "create <module>.<type> <name>"
    help_text = "Create a new item in your inventory, which you own."

    @classmethod
    def args(cls, player):
        return pyp.Word(pyp.alphas + ".")("type") + parser.Text("name")

    def execute(self, player, args):
        type_name = args["type"]
        object_name = args["name"]
        mod_name, class_name = type_name.rsplit(".", 1)
        try:
            module = importlib.import_module(mod_name)
            object_class = getattr(module, class_name)
        except ImportError:
            raise utils.UserError("I don't know of this module: "
                                  "{}".format(mod_name))
        except AttributeError:
            raise utils.UserError("{} doesn't have this class: "
                                  "{}".format(mod_name, class_name))
        new_item = object_class(object_name, owner=player, location=player)
        db.store(new_item)
        player.send("Created item #{}, {}.".format(new_item.uid, new_item.name))


class Destroy(parser.Command):
    name = "destroy"
    usage = "destroy <uid>"
    help_text = ("Destroy an item, given its UID. This command cannot be "
                 "abbreviated; you must use the full name, to be sure you "
                 "really mean it.")
    require_full = True

    @classmethod
    def args(cls, player):
        return parser.ObjectUid()("target")

    def execute(self, player, args):
        target = args["target"]
        target_uid = target.uid
        target_name = target.name
        target.destroy()
        player.send("You destroy #{} ({}).".format(target_uid, target_name))
        player.emit("{} destroys {}.".format(player.name, target_name),
                    exceptions=[player])


class Dig(parser.Command):
    name = "dig"
    usage = ["dig", "dig <room name>"]
    help_text = "Follow a series of prompts to create a room."

    @classmethod
    def args(cls, player):
        return pyp.OneOrMore(pyp.Word(pyp.alphas))("name") | parser.EmptyLine()

    def execute(self, player, args):
        prompts = ["Enter the room's name:",
                   "Enter the name of the exit into the room, or . for none:",
                   "Enter the name of the exit back, or . for none:"]
        inputs = [None for i in prompts]
        self.phase = 0

        def handle_input(line):
            inputs[self.phase] = line
            self.phase += 1

            if self.phase < len(prompts):
                d = handler.prompt(player, prompts[self.phase])
                d.addCallback(handle_input)
                return
            else:
                finish(*inputs)

        def finish(room_name, to_exit_name, from_exit_name):
            room = db.Room(room_name)
            db.store(room)
            if to_exit_name != ".":
                exit_to = db.Exit(to_exit_name, player.location, room)
                db.store(exit_to)
            if from_exit_name != ".":
                exit_from = db.Exit(from_exit_name, room, player.location)
                db.store(exit_from)
            player.send("Done.")

        if "name" in args:
            name = " ".join(args["name"])
            handle_input(name)
        else:
            d = handler.prompt(player, prompts[0])
            d.addCallback(handle_input)


class Open(parser.Command):
    name = "open"
    usage = "open <name> to <uid>"
    help_text = ("Create an exit from your current location to the given "
                 "destination.")

    @classmethod
    def args(cls, player):
        return (pyp.OneOrMore(pyp.Word(pyp.alphas))("name") +
                parser.ObjectUid()("destination"))

    def execute(self, player, args):
        name_words = args["name"]
        destination = args["destination"]
        to = name_words.pop()
        name = " ".join(name_words)
        if to != "to":
            # this is me compensating for pyparsing's failings
            raise pyp.ParseException(name, len(name)-len(to),  None, None)
        exit = db.Exit(name, player.location, destination)
        db.store(exit)
        player.send("Opened {} to {}.".format(exit, destination))


class Set(parser.Command):
    name = "set"
    usage = "set <object>.<attribute> = <value>"
    help_text = ('Change an attribute on an object, assuming you have the '
                 'appropriate permissions. The object can be referred to by '
                 'name or UID; values can be positive integers, quoted '
                 'strings, True, False, None, or the name of an item you can '
                 'reach. Examples:\n'
                 '\n'
                 'set ball.color="blue"\n'
                 'set my backpack.capacity=50\n'
                 'set #56.name="Fred"')

    @classmethod
    def args(cls, player):
        # re is much better at this than pyparsing is ...
        return pyp.Regex("^(?P<obj>.*)\.(?P<attr>.*)=(?P<value>.*)$")

    def execute(self, player, args):
        # ... but the tradeoff is we have to do the validity checking down here.
        obj_grammar = parser.ReachableOrUid(player)
        attr_grammar = pyp.Word(pyp.alphas + "_", pyp.alphanums + "_")

        try:
            obj = obj_grammar.parseString(args["obj"], parseAll=True)[0]
        except pyp.ParseException:
            name = args["obj"].strip()
            raise utils.UserError("I don't know what object you mean by '{}'"
                                  .format(name))

        try:
            attr = attr_grammar.parseString(args["attr"], parseAll=True)[0]
        except pyp.ParseException:
            name = args["attr"].strip()
            raise utils.UserError("'{}' is not a valid attribute name."
                                  .format(name))

        value_string = args["value"].strip()
        if value_string.isdigit():
            value = int(args["value"])
        elif value_string == "True":
            value = True
        elif value_string == "False":
            value = False
        elif value_string == "None":
            value = None
        else:
            try:
                pattern = parser.PythonQuoted
                value = pattern.parseString(args["value"], parseAll=True)[0]
                value = value.decode("string-escape")
            except pyp.ParseException:
                try:
                    pattern = parser.ReachableOrUid(player)
                    value = pattern.parseString(args["value"], parseAll=True)[0]
                except pyp.ParseException:
                    # okay, I give up
                    raise utils.UserError("'{}' is not a valid attribute value."
                                          .format(args["value"].strip()))

        name = obj.name  # In case it changes, so we can report the old one
        try:
            setattr(obj, attr, value)
        except ValueError as e:
            raise utils.UserError(str(e))
        db.store(obj)
        player.send("Set {}'s {} attribute to {}".format(name, attr, value))


class Unset(parser.Command):
    name = "unset"
    usage = "unset <object>.<attribute>"
    help_text = ("Completely remove an attribute from an object. You must be "
                 "the owner of the attribute.")

    @classmethod
    def args(cls, player):
        # See comments on Set.args
        return pyp.Regex("^(?P<obj>.*)\.(?P<attr>.*)$")

    def execute(self, player, args):
        obj_grammar = parser.ReachableOrUid(player)
        try:
            obj = obj_grammar.parseString(args["obj"], parseAll=True)[0]
        except pyp.ParseException:
            raise utils.UserError("I don't know what object you mean by '{}'"
                                  .format(args["obj"].strip()))

        attr = args["attr"].strip()
        try:
            delattr(obj, attr)
            player.send("Unset {} attribute on {}.".format(attr, obj))
        except AttributeError as e:
            raise utils.UserError("{} doesn't have an attribute '{}'"
                                  .format(obj, attr))


class Examine(parser.Command):
    name = "examine"
    usage = ["examine <name>", "examine <uid>"]
    help_text = ("Show details about an object, including all of its visible "
                 "attributes.")

    @classmethod
    def args(cls, player):
        return parser.ReachableOrUid(player)("obj")

    def execute(self, player, args):
        obj = args["obj"]
        player.send("{} (#{}, {}, owned by {})".format(obj, obj.uid, obj.type,
                                                       obj.owner))
        suppress = set(["name", "uid", "type", "owner", "attr_locks", "mode",
                        "password", "textwrapper"])  # attrs not to list
        for attr in sorted(obj.__dict__):
            if attr not in suppress:
                try:
                    player.send("{}: {}".format(attr, repr(getattr(obj, attr))))
                except locks.LockFailedError:
                    player.send("{} (hidden)".format(attr))


class WhatIs(parser.Command):
    name = "whatis"
    usage = "whatis <uid>"
    help_text = "Get the name of an object from its UID."

    @classmethod
    def args(cls, player):
        return parser.ObjectUid()("uid")

    def execute(self, player, args):
        item = args["uid"]
        player.send("Item #{} is {}.".format(item.uid, item.name))
