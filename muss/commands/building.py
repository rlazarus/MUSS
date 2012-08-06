# Commands for building out the game world and managing objects.

from pyparsing import OneOrMore, Optional, SkipTo, StringEnd, Suppress, Word, alphas, alphanums, Regex, ParseException

from muss.db import Exit, Object, Room, store
from muss.locks import LockFailedError
from muss.parser import Command, ObjectUid, PythonQuoted, MatchError, ReachableOrUid
from muss.utils import UserError
from muss.handler import Mode, PromptMode

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


class Dig(Command):
    name = "dig"
    help_text = "Follow a series of prompts to create a room."

    @classmethod
    def args(cls, player):
        return Optional(OneOrMore(Word(alphas)("name")))

    def execute(self, player, args):
        def handle_input(line):
            if self.phase == 1:
                self.room_name = line
                player.enter_mode(PromptMode(player, "Enter the name of the exit into the room, or . for none:", handle_input))
                self.phase += 1
            elif self.phase == 2:
                self.to_exit_name = line
                player.enter_mode(PromptMode(player, "Enter the name of the exit back, or . for none:", handle_input))
                self.phase += 1
            elif self.phase == 3:
                self.from_exit_name = line

                # We don't create any objects until now, so that we can cancel without touching the DB
                room = Room(self.room_name)
                store(room)
                if self.to_exit_name != ".":
                    exit_to = Exit(self.to_exit_name, player.location, room)
                    store(exit_to)
                if self.from_exit_name != ".":
                    exit_from = Exit(self.from_exit_name, room, player.location)
                    store(exit_from)
                player.send("Done.")

        if "name" in args:
            self.room_name = args["name"]
            self.phase = 2
            player.enter_mode(PromptMode(player, "Enter the name of the exit into the room, or . for none:", handle_input))
        else:
            self.phase = 1
            player.enter_mode(PromptMode(player, "Enter the room's name:", handle_input))


class Open(Command):
    name = "open"
    usage = "open <name> to <uid>"
    help_text = "Create an exit from your current location to the given destination."

    @classmethod
    def args(cls, player):
        return Word(alphas)("name") + Suppress("to") + ObjectUid()("destination")

    def execute(self, player, args):
        exit = Exit(args["name"], player.location, args["destination"])
        store(exit)
        player.send("Opened {} to {}.".format(exit, args["destination"]))


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
        obj_grammar = ReachableOrUid(player)
        attr_grammar = Word(alphas + "_", alphanums + "_")

        try:
            obj = obj_grammar.parseString(args["obj"], parseAll=True)[0]
        except ParseException:
            raise UserError("I don't know what object you mean by '{}.'".format(args["obj"].strip()))
        try:
            attr = attr_grammar.parseString(args["attr"], parseAll=True)[0]
        except ParseException:
            raise UserError("'{}' is not a valid attribute name.".format(args["attr"].strip()))
        if args["value"].isdigit():
            value = int(args["value"])
        else:
            try:
                value = PythonQuoted.parseString(args["value"], parseAll=True)[0]
            except ParseException:
                raise UserError("'{}' is not a valid attribute value.".format(args["value"].strip()))

        name = obj.name # in case it changes, so we can report the old one
        setattr(obj, attr, value)
        store(obj)
        player.send("Set {}'s {} attribute to {}.".format(name, attr, value))


class Unset(Command):
    name = "unset"
    usage = "unset <object>.<attribute>"
    help_text = "Completely remove an attribute from an object. You must be the owner of the attribute."

    @classmethod
    def args(cls, player):
        # See comments on Set.args
        return Regex("^(?P<obj>.*)\.(?P<attr>.*)$")

    def execute(self, player, args):
        obj_grammar = ReachableOrUid(player)
        try:
            obj = obj_grammar.parseString(args["obj"], parseAll=True)[0]
        except ParseException:
            raise UserError("I don't know what object you mean by '{}.'".format(args["obj"].strip()))

        attr = args["attr"].strip()
        try:
            delattr(obj, attr)
            player.send("Unset {} attribute on {}.".format(attr, obj))
        except AttributeError as e:
            raise UserError("{} doesn't have an attribute '{}.'".format(obj, attr))
        

class Examine(Command):
    name = "examine"
    help_text = "Show details about an object, including all of its visible attributes."

    @classmethod
    def args(cls, player):
        return ReachableOrUid(player)("obj")

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


