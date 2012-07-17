# Commands for building out the game world and managing objects.

from pyparsing import SkipTo, StringEnd

from muss.db import Object, store
from muss.locks import LockFailedError
from muss.parser import Command, ObjectUid, ReachableObject
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
