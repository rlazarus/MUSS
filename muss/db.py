import muss.locks
from muss.utils import UserError, comma_and

import hashlib
import pickle
from textwrap import TextWrapper

class Object(object):

    """
    Something in the database.

    Attributes:
        name: The string used to identify the object to players. Non-unique.
        type: 'thing' in this implementation. Subclasses may set to 'player', 'room', or 'exit'. Other values are prohibited but should be treated, by convention, as equivalent to 'thing'.
        location: The Object containing this one. None, if this object isn't inside anything (required for rooms).
        owner: The Player who owns this object.
        attr_locks: A dict mapping attribute names to AttributeLock instances.
        locks: A dict containing miscellaneous other locks pertaining to this object.
    """

    description = "You see nothing special." # Unsatisfying default description

    def __init__(self, name, location=None, owner=None):
        """
        Create a brand-new object and add it to the database.

        Args: name, location (default None), owner (defaults to current authority) as described in the class docstring
        """
        super(Object, self).__setattr__("attr_locks", {"attr_locks": muss.locks.AttributeLock(muss.locks.SYSTEM, muss.locks.Fail(), muss.locks.Fail())})

        if owner is not None:
            owner_ = owner
        else:
            owner_ = muss.locks.authority()

        with muss.locks.authority_of(muss.locks.SYSTEM):
            self.uid = None # This will be assigned when we call store()
            self.type = 'thing'
            self.owner = owner_

        with muss.locks.authority_of(self.owner):
            self.name = name
            self.locks = {}
            self.locks["take"] = muss.locks.Pass()
            self.locks["drop"] = muss.locks.Pass()
            self.locks["insert"] = muss.locks.Is(self)
            self.locks["remove"] = muss.locks.Is(self)
            self.locks["destroy"] = muss.locks.Is(self.owner)
            if location:
                self.move_to(location)
            else:
                self.location = None

    def __repr__(self):
        """
        Developer-facing string representation: <Object ###: NAME>
        """
        if self.uid is not None:
            return "<Object #{}: {}>".format(self.uid, self.name)
        else:
            return "<Object (unnumbered): {}>".format(self.name)

    def __str__(self):
        """
        User-facing string representation: its name.
        """
        return self.name

    def __getattribute__(self, attr):
        if attr == "__dict__" and muss.locks.authority() == muss.locks.SYSTEM:
            # This comes up when we're unpickling the db, and attr_locks doesn't exist yet
            return super(Object, self).__getattribute__(attr)

        attr_locks = super(Object, self).__getattribute__("attr_locks")
        if attr_locks.has_key(attr):
            if attr_locks[attr].get_lock():
                # Lock passes; grant access
                return super(Object, self).__getattribute__(attr)
            else:
                # Lock fails; deny access
                raise muss.locks.LockFailedError
        else:
            # No lock is defined; grant access
            return super(Object, self).__getattribute__(attr)

    def __setattr__(self, attr, value):
        # Does the attribute already exist?
        if attr not in super(Object, self).__getattribute__("__dict__"):
            # No, it's a new one; allow the write and also create a default lock
            super(Object, self).__setattr__(attr, value)
            lock = muss.locks.AttributeLock()
            with muss.locks.authority_of(muss.locks.SYSTEM):
                self.attr_locks[attr] = lock
        else:
            # Yes, so check the lock
            with muss.locks.authority_of(muss.locks.SYSTEM):
                if not self.attr_locks.has_key(attr):
                    # No lock is defined; allow the write
                    return super(Object, self).__setattr__(attr, value)
                else:
                    set_lock = self.attr_locks[attr].set_lock

            if set_lock():
                # Lock passes; allow the write
                return super(Object, self).__setattr__(attr, value)
            else:
                # Lock fails; deny the write
                raise muss.locks.LockFailedError

    def neighbors(self):
        """
        Find all objects this object can see.

        Returns:
            A list of (in order) this object's location if any, objects in the same place, and contents of this object.
        """
        if self.location:
            result = [self.location]
        else:
            result = []

        if self.location:
            # Add everything in the same place, as well as our contents
            result.extend(find_all(lambda obj: obj.location == self or obj.location == self.location))
        else:
            # We have no location; add only our contents
            result.extend(find_all(lambda obj: obj.location == self))

        return result

    def send(self, line):
        """
        By default, do nothing.

        Subclasses may override to specify behavior when a line is "heard": the Player class sends the line over the network, if connected. Specific objects may have specific behavior -- for example, a video-camera object might report all lines received to another location.
        """
        pass

    def emit(self, line, exceptions=None):
        """
        Send a line to each of this object's neighbors.

        Args:
            line: The line to send.
            exceptions: An optional set of objects to which the line is not sent.
        """
        if exceptions is None:
            exceptions = set()

        for obj in set(self.neighbors()).difference(exceptions):
            obj.send(line)

    def move_to(self, destination):
        """
        Move this object, checking the appropriate locks.

        Args:
            destination: The object to move this one into.

        Raises:
            UserError: If the object is already in its intended destination.
            LockFailedError: If the current authority lacks one of the four needed permissions (two on the item, one on its current location, and one on its destination).
        """
        if hasattr(self, "location"):
            origin = self.location
        else:
            origin = None

        if origin == destination:
            raise UserError("{} is already there.".format(self.name))

        if not destination.locks["insert"]():
            raise muss.locks.LockFailedError("You can't put that in {}.".format(destination.name))
        if origin and not origin.locks["remove"]():
            raise muss.locks.LockFailedError("You can't remove that from {}.".format(origin.name))

        player = muss.locks.authority()
        if destination == player:
            if not self.locks["take"]():
                raise muss.locks.LockFailedError("You cannot take {}.".format(self.name))
        elif origin == player:
            if not self.locks["drop"]():
                raise muss.locks.LockFailedError("You cannot drop {}.".format(self.name))
        else:
            # Not taking or dropping; use the location attribute lock.
            self.location = destination
            from muss.commands.world import Look
            try:
                Look().execute(self, {"obj": destination})  # Trigger a "look" command so we see our new surroundings
            except AttributeError:
                pass  # if triggered in a Player's __init__, there's no textwrapper yet, but we'll show the surroundings at the end of __init__ anyway
            return

        # We passed our take or drop lock; don't need to pass location attribute lock.
        with muss.locks.authority_of(muss.locks.SYSTEM):
            self.location = destination
        from muss.commands.world import Look
        Look().execute(self, {"obj": destination})

    def contents_string(self):
        """
        List the object's contents as a string formatted for display. If no contents, return an empty string.
        """
        contents = comma_and(map(str, find_all(lambda x: x.type != 'exit' and x.location is self)))
        if contents:
            return "Contents: {}".format(contents)
        else:
            return ""

    def exits_string(self):
        """
        List the object's exits as a string formatted for display. If no exits, return an empty string.

        Exits from an object are pretty unlikely if the object isn't a room, but they're not illegal.
        """
        exits = comma_and(map(str, find_all(lambda x: x.type == 'exit' and x.location is self)))
        if exits:
            return "Exits: {}".format(exits)
        else:
            return ""

    def destroy(self):
        """
        Destroy this object, if current authority passes its destroy lock.
        """
        if not self.locks["destroy"]():
            raise muss.locks.LockFailedError("You cannot destroy {}.".format(self.name, self.owner))
        delete(self)


class Container(Object):
    """
    An otherwise-default Object whose insert and remove locks are Pass().
    """
    def __init__(self, name, location=None, owner=None):
        super(Container, self).__init__(name, location, owner)
        self.locks["insert"] = muss.locks.Pass()
        self.locks["remove"] = muss.locks.Pass()


class Room(Object):
    """
    A location object. Has no location, and various sensible lock defaults.
    """
    def __init__(self, name, owner=None):
        super(Room, self).__init__(name, None, owner)
        self.locks["insert"] = muss.locks.Pass()
        self.locks["remove"] = muss.locks.Pass()
        self.locks["take"] = muss.locks.Fail()


class Player(Object):

    """
    Something in the database that is, specifically, associated with a person.

    Attributes:
        name: Both the name as described on Object and the login name. Unique among Players.
        password: Result of calling this class's hash() method with the correct password.
        mode: Whatever Mode we're currently in (if connected). Read-only.
        mode_stack: The stack of modes, current mode last (if connected). No read except SYSTEM.
    """

    def __init__(self, name, password):
        """
        Create a brand-new player and add it to the database.

        Args:
            name: The player's name.
            password: The player's password, in plaintext, to be discarded forever after this method call.
        """
        Object.__init__(self, name, location=find(lambda obj: obj.uid == 0), owner=self)
        with muss.locks.authority_of(muss.locks.SYSTEM):
            self.type = 'player'
            self.password = self.hash(password)
            self.textwrapper = TextWrapper()
        with muss.locks.authority_of(self):
            self.locks["take"] = muss.locks.Fail()
            self.locks["destroy"] = muss.locks.Fail()
            self.debug = True  # While we're under development, let's assume everybody wants debug information
            self.mode_stack = []  # enter_mode() must be called before any input is handled

    @property
    def mode(self):
        return self.mode_stack[-1]

    def enter_mode(self, mode):
        """
        Set the arg as the player's current Mode. It will handle input until either enter_mode() is called again, or the new mode is terminated with exit_mode().
        """
        self.mode_stack.append(mode)

    def exit_mode(self):
        """
        Pop the current mode off the stack; the one before it will begin handling input.

        Raises:
            IndexError: If there is only one mode on the stack, popping it would leave future input unhandled, and is not allowed.
        """
        if len(self.mode_stack) == 1:
            raise IndexError("Can't exit the only mode on the stack.")
        elif len(self.mode_stack) == 0:
            raise IndexError("Can't exit with no modes on the stack.")
        self.mode_stack.pop()


    def hash(self, password):
        """
        Generate a hash from this Player's name and the given password. This method is called in creating and authenticating players.

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
        wrapped = "\r\n".join(self.textwrapper.wrap(line))
        try:
            factory.allProtocols[self.name].sendLine(wrapped)
        except KeyError:
            pass

    def contents_string(self):
        contents = comma_and(map(str, list(find_all(lambda x: x.location == self))))
        if contents:
            return "{} is carrying {}.".format(self.name, contents)
        else:
            return ""


class Exit(Object):
    """
    A link from one Object (usually a room) to another, allowing players to move around.

    Attributes:
        location: This exit's source.
        destination: Where this exit drops you.
    """

    def __init__(self, name, source, destination, owner=None, lock=None):
        super(Exit, self).__init__(name, source, owner)
        with muss.locks.authority_of(muss.locks.SYSTEM):
            self.type = 'exit'
        self.destination = destination
        if lock is None:
            lock = muss.locks.Pass()
        self.locks["go"] = lock

    def go(self, player):
        if self.locks["go"](player):
            player.move_to(self.destination)
        else:
            raise muss.locks.LockFailedError


def backup():
    """
    Dump the contents of the database to a backup file "muss.db", overwriting any existing one.
    """
    with open("muss.db", 'wb') as f:
        pickle.dump(_nextUid, f)
        pickle.dump(_objects, f)


def restore():
    """
    Read the contents of backup file "muss.db" and populate the database with them.
    """
    with open("muss.db", 'rb') as f:
        global _nextUid
        global _objects
        _nextUid = pickle.load(f)
        _objects = pickle.load(f)


def store(obj):
    """
    Save an object to the database, either creating or updating it as appropriate.

    If the object's uid is None, it is assumed to be new. If it has a uid, it's assumed to be an existing object being updated. If creating a new object, do not assign it a uid: this method will assign it one.

    Args:
        obj: The object (an instance of Object or subclass) to update the DB with.

    Raises:
        IndexError: If the object carries a uid that doesn't already exist, possibly because the object was deleted.
    """
    if not isinstance(obj, Object):
        raise TypeError

    if obj.uid:
        # It already has a UID, so it's already in the database somewhere
        if _objects.has_key(obj.uid):
            # Update the DB
            _objects[obj.uid] = obj
        else:
            # Uh oh -- the object we were passed doesn't exist, judging by its UID
            raise IndexError("There is no object #{}".format(obj.uid))
    else:
        global _nextUid
        # No UID -- this is a new object
        with muss.locks.authority_of(muss.locks.SYSTEM):
            obj.uid = _nextUid
        _nextUid += 1
        _objects[obj.uid] = obj


def delete(obj):
    """
    Delete an object from the database.

    After successfully calling delete(), the object is gone. If you're still holding an old reference to it, get rid of it. Calls to store() will fail, and other parts of the object's interface are no longer guaranteed: it no longer represents anything still in the DB.

    Args:
        obj: The object to delete.

    Raises:
        IndexError: If there's no such object to be deleted.
    """
    del _objects[obj.uid]


def find_all(condition=(lambda x:True)):
    """
    Return a set of all objects in the database matching the given condition.

    Args:
        condition: Any function that takes an object and returns True or False.
    """
    return set(obj for obj in _objects.values() if condition(obj))


def find(condition=(lambda x:True)):
    """
    Return the single object in the database matching the given condition.

    Args:
        condition: Any function that takes an object and returns True or False.

    Raises:
        KeyError: If there are zero, or plural, objects matching the condition.
    """
    results = find_all(condition)
    if not results:
        raise KeyError("Nothing in the database matching {} (expected exactly 1)".format(condition))
    if len(results) > 1:
        raise KeyError("{} objects in the database matching {} (expected exactly 1)".format(len(results), condition))
    return results.pop()


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
        return find(lambda obj: obj.type == 'player' and obj.name.lower() == name.lower())


def player_name_taken(name):
    """Determine whether there exists a player with a particular name. Returns False if player_by_name(name) would raise KeyError."""
    try:
        player_by_name(name)
        return True
    except KeyError:
        return False


with muss.locks.authority_of(muss.locks.SYSTEM):
    try:
        restore()
    except IOError as e:
        if e.errno == 2:
            # These ought to be calls to twisted.python.log.msg, but logging hasn't started yet when this module is loaded.
            print("WARNING: Database file muss.db not found. If MUSS is starting for the first time, this is normal.")
        else:
            print("ERROR: Unable to load database file muss.db. The database will be populated as if MUSS is starting for the first time.")
        _nextUid = 0
        _objects = {}
        lobby = Room("lobby")
        store(lobby)
        foyer = Room("foyer")
        store(foyer)
        north = Exit("north", lobby, foyer)
        store(north)
        south = Exit("south", foyer, lobby)
        store(south)
