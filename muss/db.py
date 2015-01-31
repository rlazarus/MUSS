import hashlib
import pickle
import textwrap

from muss import channels, locks, utils


class Object(object):

    """
    Something in the database.

    Attributes:
        name: The string used to identify the object to players. Non-unique.
        type: 'thing' in this implementation. Subclasses may set to 'player',
            'room', or 'exit'. Other values are prohibited but should be
            treated, by convention, as equivalent to 'thing'.
        location: The Object containing this one. None, if this object isn't
            inside anything (required for rooms).
        owner: The Player who owns this object.
        attr_locks: A dict mapping attribute names to AttributeLock instances.
        locks: An object whose attributes hold miscellaneous locks on this
            object.
    """

    def __init__(self, name, location=None, owner=None):
        """
        Create a brand-new object and add it to the database.

        Args: name, location (default None), owner (defaults to current
        authority) as described in the class docstring
        """
        lock = locks.AttributeLock(locks.SYSTEM, locks.Fail(), locks.Fail())
        super(Object, self).__setattr__("attr_locks", {"attr_locks": lock})

        if owner is not None:
            owner_ = owner
        else:
            if locks.authority() is not None:
                owner_ = locks.authority()
            else:
                raise locks.MissingAuthorityError("Object created with no "
                                                  "owner and no authority.")

        with locks.authority_of(locks.SYSTEM):
            self.uid = None  # This will be assigned when we call store()
            self.type = 'thing'
            self.owner = owner_
            self.name = name
            self.lock_attr("name", set_lock=locks.Owns(self))
            self.lock_attr("owner", set_lock=locks.Owns(self))
            self.locks = Locks()
            self.lock_attr("locks", set_lock=locks.Fail())
            self._location = None

        with locks.authority_of(self.owner):
            self.description = "You see nothing special."
            self.locks.take = locks.Pass()
            self.locks.drop = locks.Pass()
            self.locks.insert = locks.Is(self)
            self.locks.remove = locks.Is(self)
            self.locks.destroy = locks.Owns(self)
            if location:
                self.location = location

    def __repr__(self):
        """
        Developer-facing string representation: ### NAME

        (#__ if the object hasn't been assigned a uid yet)
        """
        if self.uid is not None:
            return "#{} {}".format(self.uid, self.name)
        else:
            return "#__ {}".format(self.name)

    def __str__(self):
        """
        User-facing string representation: its name.
        """
        return self.name

    def __getattribute__(self, attr):
        if attr == "__dict__" and locks.authority() is locks.SYSTEM:
            # This comes up when we're unpickling the db, and attr_locks
            # doesn't exist yet
            return super(Object, self).__getattribute__(attr)

        attr_locks = super(Object, self).__getattribute__("attr_locks")
        if attr in attr_locks:
            if attr_locks[attr].get_lock():
                # Lock passes; grant access
                return super(Object, self).__getattribute__(attr)
            else:
                # Lock fails; deny access
                raise locks.LockFailedError("You don't have permission to get "
                                            "{} from {}.".format(attr, self))
        else:
            # No lock is defined; grant access
            return super(Object, self).__getattribute__(attr)

    def __setattr__(self, attr, value):
        # Does the attribute already exist?
        if attr not in super(Object, self).__getattribute__("__dict__"):
            # No, it's a new one; allow the write and also create a default lock
            super(Object, self).__setattr__(attr, value)
            lock = locks.AttributeLock(set_lock=locks.OwnsAttribute(self, attr))
            with locks.authority_of(locks.SYSTEM):
                self.attr_locks[attr] = lock
        else:
            # Yes, so check the lock
            with locks.authority_of(locks.SYSTEM):
                if attr not in self.attr_locks:
                    # No lock is defined; allow the write
                    return super(Object, self).__setattr__(attr, value)
                else:
                    set_lock = self.attr_locks[attr].set_lock

            if set_lock():
                return super(Object, self).__setattr__(attr, value)
            else:
                # Lock fails; deny the write
                raise locks.LockFailedError("You don't have permission to set "
                                            "{} on {}.".format(attr, self))

    def __delattr__(self, attr):
        try:
            with locks.authority_of(locks.SYSTEM):
                owner_lock = locks.Owns(self.attr_locks[attr])
        except KeyError as e:
            if hasattr(self, attr):
                # Attribute exists, lock doesn't. This is a code error.
                raise e
            else:
                # The attribute doesn't exist.
                raise AttributeError

        if owner_lock():
            super(Object, self).__delattr__(attr)
            with locks.authority_of(locks.SYSTEM):
                del self.attr_locks[attr]
        else:
            raise locks.LockFailedError("You don't have permission to unset {} "
                                        "on {}.".format(attr, self))

    def lock_attr(self, attr, owner=None, get_lock=None, set_lock=None):
        if not hasattr(self, attr):
            raise KeyError("{} has no attribute {}.".format(self, attr))

        with locks.authority_of(locks.SYSTEM):
            lock = self.attr_locks[attr]

        if (locks.authority() is not lock.owner
            and locks.authority() is not locks.SYSTEM):
            raise locks.LockFailedError("You don't own that attribute.")

        if owner is None and get_lock is None and set_lock is None:
            raise TypeError("Specify at least one of owner, get_lock, set_lock")

        if owner is not None:
            lock.owner = owner
        if get_lock is not None:
            lock.get_lock = get_lock
        if set_lock is not None:
            lock.set_lock = set_lock

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if name.startswith("#"):
            raise ValueError("Names can't begin with a #.")

        if hasattr(self, "name"):
            with locks.authority_of(locks.SYSTEM):
                lock = self.attr_locks["name"].set_lock
            if lock():
                with locks.authority_of(locks.SYSTEM):
                    self._name = name
            else:
                raise locks.LockFailedError("You don't have permission to set "
                                            "name on {}.".format(self))
        else:
            lock = locks.OwnsAttribute(self, "name")
            attr_lock = locks.AttributeLock(set_lock=lock)
            with locks.authority_of(locks.SYSTEM):
                self.attr_locks["name"] = attr_lock
            self._name = name

    @name.deleter
    def name(self):
        # When names are heritable, we can talk.
        raise AttributeError("Every Object must have a name attribute.")

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, destination):
        origin = self.location

        if not destination.locks.insert():
            raise locks.LockFailedError("You can't put that in {}."
                                        .format(destination.name))
        if origin and not origin.locks.remove():
            raise locks.LockFailedError("You can't remove that from {}."
                                        .format(origin.name))

        player = locks.authority()
        if destination == player:
            if not self.locks.take():
                raise locks.LockFailedError("You cannot take {}."
                                            .format(self.name))
        elif origin == player:
            if not self.locks.drop():
                raise locks.LockFailedError("You cannot drop {}."
                                            .format(self.name))

        # Locks passed or non-applicable. Proceed with the move.
        with locks.authority_of(locks.SYSTEM):
            self._location = destination

        with locks.authority_of(self):
            # this gets to use self authority because it should always happen,
            # regardless of the reason location is being changed.
            # it does NOT get to use system authority because it's sometimes
            # (always, for players) how position gets initialized, which locks
            # the object out of its own position attribute.
            if destination is not origin:
                # whatever we were doing there, we're not doing it any more
                self.position = None

        # Trigger a "look" command so we see our new surroundings
        from muss.commands.world import Look
        try:
            Look().execute(self, {"obj": destination})
        except AttributeError:
            pass
            # if triggered in a Player's __init__, there's no textwrapper yet
            # but we'll show the surroundings at the end of __init__ anyway

    @location.deleter
    def location(self):
        # Everything has a location. If feel the need to delete it, consider
        # setting it to None instead.
        raise locks.LockFailedError("You don't have permission to unset "
                                    "location on {}.".format(self))

    def neighbors(self):
        """
        Find all objects this object can see.

        Returns:
            A list of (in order) this object's location if any, objects in the
            same place, and contents of this object.
        """
        if self.location:
            result = [self.location]
        else:
            result = []

        if self.location:
            # Add everything in the same place, as well as our contents
            result.extend(find_all(lambda obj: obj.location == self or
                                               obj.location == self.location))
        else:
            # We have no location; add only our contents
            result.extend(find_all(lambda obj: obj.location == self))

        return result

    def send(self, line):
        """
        By default, do nothing.

        Subclasses may override to specify behavior when a line is "heard": the
        Player class sends the line over the network, if connected. Specific
        objects may have specific behavior -- for example, a video-camera
        object might report all lines received to another location.
        """
        pass

    def emit(self, line, exceptions=None):
        """
        Send a line to each of this object's neighbors.

        Args:
            line: The line to send.
            exceptions: An optional set of objects to which the line is not
                sent.
        """
        if exceptions is None:
            exceptions = set()

        for obj in set(self.neighbors()).difference(exceptions):
            obj.send(line)

    def position_string(self):
        """
        If the object has a position, return 'name (position)'.
        Otherwise, just return the name.
        """
        pos_string = self.name
        try:
            if self.position:
                # this isn't redundant with the try;
                # it's to avoid printing position when it's None
                pos_string = "{} ({})".format(self.name, self.position)
        except AttributeError:
            pass
        return pos_string

    def population_string(self):
        """
        List the players inside an object as a string formatted for display. If
        no one's inside the object, return an empty string.
        """

        population = find_all(lambda x: x.type == 'player' and
                                        x.location is self)
        if population:
            names = []
            for player in population:
                if player.connected:
                    names.append(player.position_string())
                else:
                    names.append(player.name + " (disconnected)")
            return "Players: {}".format(utils.comma_and(names))
        else:
            return ""

    def contents_string(self):
        """
        List the object's contents as a string formatted for display. If no
        contents, return an empty string.
        """
        objects = find_all(lambda x: x.type != 'player' and x.type != 'exit'
                                     and x.location is self
                                     and not (hasattr(x, 'equipped')
                                              and x.equipped))
        names = [o.position_string() for o in objects]
        text = utils.comma_and(names)

        if objects:
            return "Contents: {}".format(text)
        else:
            return ""

    def equipment_string(self):
        """
        List the object's equipment as a string formatted for display. If no
        equipment, return an empty string.
        """
        objects = find_all(lambda x: x.type != 'player' and x.type != 'exit'
                                     and x.location is self
                                     and hasattr(x, 'equipped') and x.equipped)
        names = [o.position_string() for o in objects]
        text = utils.comma_and(names)

        if objects:
            return "Equipment: {}".format(text)
        else:
            return ""

    def exits_string(self):
        """
        List the object's exits as a string formatted for display. If no exits,
        return an empty string.

        Exits from an object are pretty unlikely if the object isn't a room,
        but they're not illegal.
        """
        exits = find_all(lambda x: x.type == 'exit' and x.location is self)
        text = utils.comma_and(map(str, exits))
        if exits:
            return "Exits: {}".format(text)
        else:
            return ""

    def destroy(self):
        """
        Destroy this object, if current authority passes its destroy lock.
        """
        if not self.locks.destroy():
            raise locks.LockFailedError("You cannot destroy {}."
                                        .format(self.name, self.owner))
        delete(self)


class Locks(object):
    """
    This is only used as a namespace: it's instantiated once for each object,
    to hold references to locks.
    """
    def __getattribute__(self, attr):
        """
        If the lock is defined, return it. If it's not defined, return a
        failing lock. This might be inconvenient behavior in some situations,
        but it beats having to handle an AttributeError every time we check a
        lock.
        """
        try:
            return super(Locks, self).__getattribute__(attr)
        except AttributeError:
            return locks.Fail()

    def __getstate__(self):
        """
        Return self.__dict__ for pickling. Need to do this explicitly, because
        of our custom shenanigans in __getattribute__.

        (The pickle module looks up __getstate__ first, and if it doesn't exist
        we get too clever and return a Fail() instead of raising AttributeError
        like we're supposed to.)
        """
        return self.__dict__

    def __setstate__(self, state):
        """
        Restore self.__dict__ to the given state. See documentation for
        __getstate__.
        """
        if locks.authority() is locks.SYSTEM:
            self.__dict__ = state

    def __repr__(self):
        return "Locks({})".format(self.__dict__)


class Container(Object):
    """
    An otherwise-default Object whose insert and remove locks are Pass().
    """
    def __init__(self, name, location=None, owner=None):
        super(Container, self).__init__(name, location, owner)
        self.locks.insert = locks.Pass()
        self.locks.remove = locks.Pass()


class Room(Object):
    """
    A location object. Has no location, and various sensible lock defaults.
    """
    def __init__(self, name, owner=None):
        super(Room, self).__init__(name, None, owner)
        self.locks.insert = locks.Pass()
        self.locks.remove = locks.Pass()
        self.locks.take = locks.Fail()
        with locks.authority_of(locks.SYSTEM):
            self.type = "room"


class Player(Object):

    """
    Something in the database that is, specifically, associated with a person.

    Attributes:
        name: Both the name as described on Object and the login name. Unique
            among Players.
        password: Result of calling this class's hash() method with the correct
            password.
        mode: Whatever Mode we're currently in (if connected). Read-only.
        mode_stack: The stack of modes, current mode last (if connected). No
            read except SYSTEM.
    """

    def __init__(self, name, password):
        """
        Create a brand-new player and add it to the database.

        Args:
            name: The player's name.
            password: The player's password, in plaintext, to be discarded
                forever after this method call.
        """
        Object.__init__(self, name, location=get(0), owner=self)
        with locks.authority_of(locks.SYSTEM):
            self.type = 'player'
            self.lock_attr("name", set_lock=locks.Fail())
            self.lock_attr("owner", set_lock=locks.Fail())
            self.password = self.hash(password)
            self.textwrapper = textwrap.TextWrapper()
            # Initialize the mode stack empty, but enter_mode() must be called
            # before any input is handled.
            self.mode_stack = []
            self.lock_attr("mode_stack", set_lock=locks.Owns(self))
            self.last_told = None
        with locks.authority_of(self):
            self.locks.take = locks.Fail()
            self.locks.destroy = locks.Fail()
            # While we're under development, let's assume everybody wants debug
            # information.
            self.debug = True
            # Until there's a command to join a channel, do it automatically.
            channels._channels['Public'].join(self)

    @property
    def mode(self):
        return self.mode_stack[-1]

    @property
    def connected(self):
        return bool(self.mode_stack)

    def enter_mode(self, mode):
        """
        Set the arg as the player's current Mode. It will handle input until
        either enter_mode() is called again, or the new mode is terminated with
        exit_mode().
        """
        self.mode_stack.append(mode)

    def exit_mode(self):
        """
        Pop the current mode off the stack; the one before it will begin
        handling input.

        Raises:
            IndexError: If there is only one mode on the stack, popping it
                would leave future input unhandled, and is not allowed.
        """
        if len(self.mode_stack) == 1:
            raise IndexError("Can't exit the only mode on the stack.")
        elif len(self.mode_stack) == 0:
            raise IndexError("Can't exit with no modes on the stack.")
        self.mode_stack.pop()

    def hash(self, password):
        """
        Generate a hash from this Player's name and the given password. This
        method is called in creating and authenticating players.

        Args:
            password: The password to hash.
        """
        # Hash the username and password together
        m = hashlib.sha512()
        m.update(self.name)
        m.update(password)
        return m.hexdigest()

    def send(self, line):
        """
        If this player is connected, send the line to the client.
        """
        from muss.server import factory
        lines = line.split("\n")
        wrapped = []
        for i in lines:
            if i:
                wrapped.extend(self.textwrapper.wrap(i))
            else:  # TextWrapper strips blank lines, so let's preserve them
                wrapped.append("")

        try:
            for wrapped_line in wrapped:
                factory.allProtocols[self.name].sendLine(wrapped_line)
        except KeyError:
            pass

    def contents_string(self):
        contents = find_all(lambda x: x.location == self
                                      and not (hasattr(x, 'equipped')
                                               and x.equipped))
        text = utils.comma_and(map(str, list(contents)))
        if contents:
            return "{} is carrying {}.".format(self.name, text)
        else:
            return ""

    def equipment_string(self):
        equipment = find_all(lambda x: x.location == self
                                       and hasattr(x, 'equipped')
                                       and x.equipped)
        text = utils.comma_and(map(str, list(equipment)))
        if equipment:
            return "{} is wearing {}.".format(self.name, text)
        else:
            return ""


class Exit(Object):
    """
    A link from one Object (usually a room) to another, allowing players to
    move around.

    Attributes:
        location: This exit's source.
        destination: Where this exit drops you.
    """

    def __init__(self, name, source, destination, owner=None, lock=None):
        super(Exit, self).__init__(name, source, owner)
        with locks.authority_of(locks.SYSTEM):
            self.type = 'exit'

        self.destination = destination
        if lock is None:
            self.locks.go = locks.Pass()
        else:
            self.locks.go = lock

        self.depart_message = "{player} leaves through {exit}."
        self.arrive_message = "{player} arrives."

    def go(self, player):
        if not self.locks.go(player):
            raise locks.LockFailedError("You can't go through {}.".format(self))

        player.location = self.destination

        params = {"player": player.name,
                  "exit": self.name,
                  "source": self.location.name,
                  "destination": self.destination.name}

        try:
            self.location.emit(self.depart_message.format(**params))
        except AttributeError:
            pass

        try:
            self.destination.emit(self.arrive_message.format(**params),
                                  exceptions=[player])
        except AttributeError:
            pass

        try:
            player.send(self.go_message.format(**params))
        except AttributeError:
            pass


def backup():
    """
    Dump the contents of the database to a backup file "muss.db", overwriting
    any existing one.
    """
    with open("muss.db", 'wb') as f:
        pickle.dump(_nextUid, f)
        pickle.dump(_objects, f)


def restore():
    """
    Read the contents of backup file "muss.db" and populate the database with
    them.
    """
    with open("muss.db", 'rb') as f:
        global _nextUid
        global _objects
        _nextUid = pickle.load(f)
        _objects = pickle.load(f)


def store(obj):
    """
    Save an object to the database, either creating or updating it as
    appropriate.

    If the object's uid is None, it is assumed to be new. If it has a uid, it's
    assumed to be an existing object being updated. If creating a new object,
    do not assign it a uid: this method will assign it one.

    Args:
        obj: The object (an instance of Object or subclass) to update the DB
            with.

    Raises:
        IndexError: If the object carries a uid that doesn't already exist,
            possibly because the object was deleted.
    """
    if not isinstance(obj, Object):
        raise TypeError

    if obj.uid is not None:
        # It already has a UID, so it's already in the database somewhere
        if obj.uid in _objects:
            # Update the DB
            _objects[obj.uid] = obj
        else:
            # Uh oh -- the object we were passed doesn't exist, judging by its
            # UID.
            raise IndexError("There is no object #{}".format(obj.uid))
    else:
        global _nextUid
        # No UID -- this is a new object
        with locks.authority_of(locks.SYSTEM):
            obj.uid = _nextUid
        _nextUid += 1
        _objects[obj.uid] = obj


def delete(obj):
    """
    Delete an object from the database.

    After successfully calling delete(), the object is gone. If you're still
    holding an old reference to it, get rid of it. Calls to store() will fail,
    and other parts of the object's interface are no longer guaranteed: it no
    longer represents anything still in the DB.

    Args:
        obj: The object to delete.

    Raises:
        IndexError: If there's no such object to be deleted.
    """
    del _objects[obj.uid]


def find_all(condition=(lambda x: True)):
    """
    Return a set of all objects in the database matching the given condition.

    Args:
        condition: Any function that takes an object and returns True or False.
    """
    return set(obj for obj in _objects.values() if condition(obj))


def find(condition=(lambda x: True)):
    """
    Return the single object in the database matching the given condition.

    Args:
        condition: Any function that takes an object and returns True or False.

    Raises:
        KeyError: If there are zero, or plural, objects matching the condition.
    """
    results = find_all(condition)
    if not results:
        raise KeyError("Nothing in the database matching {} (expected exactly "
                       "1)".format(condition))
    if len(results) > 1:
        raise KeyError("{} objects in the database matching {} (expected "
                       "exactly 1)".format(len(results), condition))
    return results.pop()


def get(uid):
    """
    Return the single object in the database with the given UID. More efficient
    than the equivalent find() call.

    Raises:
        KeyError: If no object has that number.
    """

    return _objects[uid]


def player_by_name(name, case_sensitive=False):
    """
    Search through the database for a particular player name.

    Args:
        name: The name of the player to find.

    Raises:
        KeyError: Sorry, buddy, there's nobody here by that name.
    """

    if case_sensitive:
        return find(lambda obj: obj.type == 'player' and obj.name == name)
    else:
        return find(lambda obj: obj.type == 'player' and
                                obj.name.lower() == name.lower())


def player_name_taken(name):
    """
    Determine whether there exists a player with a particular name. Returns
    False if player_by_name(name) would raise KeyError.
    """
    try:
        player_by_name(name)
        return True
    except KeyError:
        return False


with locks.authority_of(locks.SYSTEM):
    try:
        restore()
    except IOError as e:
        if e.errno == 2:
            # These ought to be calls to twisted.python.log.msg, but logging
            # hasn't started yet when this module is loaded.
            print("WARNING: Database file muss.db not found. If MUSS is "
                  "starting for the first time, this is normal.")
        else:
            print("ERROR: Unable to load database file muss.db. The database "
                  "will be populated as if MUSS is starting for the first "
                  "time.")
        _nextUid = 0
        _objects = {}
        lobby = Room("lobby")
        store(lobby)
