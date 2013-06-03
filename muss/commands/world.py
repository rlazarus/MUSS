# Basic interactions in the world.

from muss import db, parser


class Equip(parser.Command):
    name = ["equip", "wear", "don"]
    usage = ["equip <item>", "wear <item>", "don <item>"]
    help_text = "Equip an item that you are carrying."

    @classmethod
    def args(cls, player):
        return parser.ObjectIn(player)("item")

    def execute(self, player, args):
        item = args["item"]
        item.equip()
        player.send("You equip {}.".format(item.name))
        player.emit("{} equips {}.".format(player.name, item.name),
                    exceptions=[player])


class Unequip(parser.Command):
    name = ["unequip", "remove", "doff"]
    usage = ["unequip <item>", "remove <item>", "doff <item>"]
    help_text = "Remove an item you have equipped."

    @classmethod
    def args(cls, player):
        return parser.ObjectIn(player)("item")

    def execute(self, player, args):
        item = args["item"]
        item.unequip()
        player.send("You unequip {}.".format(item.name))
        player.emit("{} unequips {}.".format(player.name, item.name),
                    exceptions=[player])


class Drop(parser.Command):
    name = "drop"
    usage = ["drop <item>"]
    help_text = "Drop an item from your inventory into your location."

    @classmethod
    def args(cls, player):
        return parser.ObjectIn(player, returnAll=True)("items")

    def execute(self, player, args):
        perfect, partial = args[0]
        # Why does this work and args["items"] doesn't?
        # I don't know, but it does. I blame pyparsing.
        if perfect:
            item_list = perfect
        else:
            item_list = partial
        equipped = [x for x in item_list if hasattr(x, "equipped")
                                            and x.equipped]
        unequipped = [x for x in item_list if x not in equipped]
        if len(unequipped) == 1:
            item = unequipped[0]
        elif not unequipped and len(equipped) == 1:
            item = equipped[0]
        elif unequipped:
            raise parser.AmbiguityError("", 0, "", None,
                                        [(x.name, x) for x in unequipped])
        elif equipped:
            raise parser.AmbiguityError("", 0, "", None,
                                        [(x.name, x) for x in equipped])
        else:
            raise parser.NotFoundError("", 0, "", None)

        if hasattr(item, "equipped") and x.equipped:
            player.send("You unequip and drop {}.".format(item.name))
            player.emit("{} unequips and drops {}.".format(player.name,
                        item.name), exceptions=[player])
            item.unequip()
        else:
            player.send("You drop {}.".format(item.name))
            player.emit("{} drops {}.".format(player.name, item.name),
                        exceptions=[player])
        item.location = player.location


class Go(parser.Command):
    name = "go"
    help_text = "Travel through an exit."

    @classmethod
    def args(cls, player):
        return parser.ReachableOrUid(player)("exit")

    def execute(self, player, args):
        try:
            args["exit"].go(player)
        except AttributeError:
            # it has no go() so it isn't an exit
            player.send("You can't go through {}.".format(args["exit"]))


class Inventory(parser.Command):
    name = "inventory"
    help_text = "Shows you what you're carrying."

    def execute(self, player, args):
        inv = db.find_all(lambda i: i.location == player)
        if inv:
            inv_names = sorted([i.name for i in inv])
            inv_string = ", ".join(inv_names)
            player.send("You are carrying: {}.".format(inv_string))
        else:
            player.send("You are not carrying anything.")


class Look(parser.Command):
    name = ["look", "l"]
    usage = "look [object]"
    help_text = ("Show an object's description. If it has contents or exits, "
                 "list them. If it's an exit, show its destination.\n"
                 "You can specify an object either by naming something near "
                 "you or giving its UID. If no object is specified, you will "
                 "look at your current location.")

    @classmethod
    def args(cls, player):
        return parser.ReachableOrUid(player)("obj") | parser.EmptyLine()

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

        equipment = obj.equipment_string()
        if equipment:
            player.send(equipment)

        exits = obj.exits_string()
        if exits:
            player.send(exits)

        if obj.type == 'exit':
            player.send("Destination: {}".format(obj.destination))


class Take(parser.Command):
    name = ["take", "get"]
    usage = ["take <item>", "get <item>"]
    help_text = "Pick up an item in your location."

    @classmethod
    def args(cls, player):
        return parser.ObjectIn(player.location)("item")

    def execute(self, player, args):
        item = args["item"]
        item.location = player
        player.send("You take {}.".format(item.name))
        player.emit("{} takes {}.".format(player.name, item.name),
                    exceptions=[player])
