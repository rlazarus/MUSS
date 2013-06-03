from muss import db, locks, utils


class EquipmentError(utils.UserError):
    pass


class Equipment(db.Object):
    def __init__(self, name, location=None, owner=None):
        super(Equipment, self).__init__(name, location, owner)
        self.equipped = False
        self.locks.equip = locks.Has(self)
        self.locks.unequip = locks.Has(self)

    def equip(self):
        if not self.locks.equip():
            raise EquipmentError("You cannot equip {}".format(self.name))
        if self.equipped:
            raise EquipmentError("That is already equipped!")
        self.equipped = True

    def unequip(self):
        if not self.locks.unequip():
            # This is Equipment instead of LockFailed so you can tell what's
            # wrong when you try to steal something.
            raise EquipmentError("You cannot unequip {}".format(self.name))
        if not self.equipped:
            raise EquipmentError("That isn't equipped!")
        self.equipped = False

    @db.Object.location.setter
    def location(self, destination):
        if destination is not self.location and hasattr(self, "equipped") and self.equipped:
            self.unequip()
        db.Object.location.__set__(self, destination)
