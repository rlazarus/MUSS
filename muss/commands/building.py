# Commands for building out the game world and managing objects.

from pyparsing import SkipTo, StringEnd, Word, alphas, alphanums, Regex, ParseException

from muss.db import Object, store
from muss.locks import LockFailedError
from muss.parser import Command, ObjectUid, ReachableObject, PythonQuoted
from muss.utils import UserError


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


class Set(Command):
    name = "set"
    usage = "set <object>.<attribute> = <value>"
    help_text = """Change an attribute on an object, assuming you have the appropriate permissions. The object can be referred to by name or UID; values can be either numeric or quoted strings. Examples:\r
\r
    set ball.color="blue"\r
    set my backpack.capacity=50\r
    set #56.name="Fred" """

    @classmethod
    def args(cls, player):
        # re is much better at this than pyparsing is ...
        return Regex("^(?P<obj>.*)\.(?P<attr>.*)=(?P<value>.*)$")

    def execute(self, player, args):
        # ... but the tradeoff is we have to do the validity checking down here.
        obj_grammar = ObjectUid() | ReachableObject(player)
        attr_grammar = Word(alphas + "_", alphanums + "_")

        obj = obj_grammar.parseString(args["obj"], parseAll=True)[0]
        try:
            attr = attr_grammar.parseString(args["attr"], parseAll=True)[0]
        except ParseException:
            raise UserError("'{}' isn't a valid attribute name.".format(args["attr"]))
        if args["value"].isdigit():
            value = int(args["value"])
        else:
            try:
                value = PythonQuoted.parseString(args["value"], parseAll=True)[0]
            except ParseException:
                raise UserError("'{}' isn't a valid attribute value.".format(args["value"]))

        name = obj.name # in case it changes, so we can report the old one
        setattr(obj, attr, value)
        player.send("Okay, set {}'s '{}' attribute to '{}.'".format(name, attr, value))


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
        for attr in sorted(obj.__dict__):
            if attr not in suppress:
                try:
                    player.send("{}: {}".format(attr, repr(getattr(obj, attr))))
                except LockFailedError:
                    player.send("{} (hidden)".format(attr))


class WhatIs(Command):
    name = "whatis"
    help_text = "Get the name of an object from its UID."

    @classmethod
    def args(cls, player):
        return ObjectUid()("uid")

    def execute(self, player, args):
        item = args["uid"]
        player.send("Item #{} is {}.".format(item.uid, item.name))
