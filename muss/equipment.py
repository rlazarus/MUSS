from muss import db, locks, utils


class EquipmentError(utils.UserError):
    pass


class Equipment(db.Object):
    def __init__(self, name, location=None, owner=None):
        super(Equipment, self).__init__(name, location, owner)
        self.equipped = False
        self.lock_attr("equipped", set_lock=locks.Has(self))

    def equip(self):
        if self.equipped:
            raise EquipmentError("That is already equipped!")
        self.equipped = True

    def unequip(self):
        if not self.equipped:
            raise EquipmentError("That isn't equipped!")
        try:
            self.equipped = False
        except locks.LockFailedError:
            raise EquipmentError("You can't, it's equipped.")

    @db.Object.location.setter
    def location(self, destination):
        if destination is not self.location and hasattr(self, "equipped") and self.equipped:
            self.unequip()
        db.Object.location.__set__(self, destination)
