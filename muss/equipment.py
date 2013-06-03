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
            raise locks.LockFailedError("You cannot equip {}".format(self.name))
        if self.equipped:
            raise EquipmentError("That is already equipped!")
        self.equipped = True

    def unequip(self):
        if not self.locks.unequip():
            raise locks.LockFailedError("You cannot unequip {}".format(self.name))
        if not self.equipped:
            raise EquipmentError("That isn't equipped!")
        self.equipped = False

    @db.Object.location.setter
    def location(self, destination):
        origin = self.location
        db.Object.location.__set__(self, destination)
        if self.location is not origin:
            # We moved, presumably we're no longer equipped
            self.equipped = False
