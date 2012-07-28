# Basic interactions in the world.

from pyparsing import Optional, SkipTo, StringEnd

from muss.db import find_all
from muss.parser import Command, ObjectIn, ObjectUid, ReachableOrUid


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


class Go(Command):
    name = "go"
    help_text = "Travel through an exit."

    @classmethod
    def args(cls, player):
        return Optional(ReachableOrUid(player)("exit"))

    def execute(self, player, args):
        try:
            args["exit"].go(player)
        except AttributeError:
            # it has no go() so it isn't an exit
            player.send("You can't go through {}.".format(exit))


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


class Look(Command):
    name = "look"
    help_text = "Show an object's description. If it has contents or exits, list them. If it's an exit, show its destination."

    @classmethod
    def args(cls, player):
        return Optional(ReachableOrUid(player)("obj"))

    def execute(self, player, args):
        try:
            obj = args["obj"]
        except KeyError:
            # If invoked without argument, look at our surroundings instead
            obj = player.location

        player.send(obj.name)
        player.send(obj.description)

        population = obj.population_string()
        if population:
            player.send(population)

        contents = obj.contents_string()
        if contents:
            player.send(contents)

        exits = obj.exits_string()
        if exits:
            player.send(exits)

        if obj.type == 'exit':
            player.send("Destination: {}".format(obj.destination))


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


