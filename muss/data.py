import hashlib

class Database(object):

    """
    The singleton database, keeping track of every in-game object. This implementation hangs onto everything in RAM, but we'll eventually offload it into some flavor of SQL database.
    """

    _instance = None
    def __new__(cls):
        if not cls._instance:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._nextUid = 0
            cls._instance._objects = {}

            lobby = Object("Lobby")
            cls._instance.store(lobby)
        return cls._instance

    def __init__(self):
        """
        Do nothing. Because of the way the singleton pattern is implemented, this method may be called repeatedly on the same object. It should not be implemented nor overridden.
        """
        pass

    def store(self, obj):
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
            if self._objects.has_key(obj.uid):
                # Update the DB
                self._objects[obj.uid] = obj
            else:
                # Uh oh -- the object we were passed doesn't exist, judging by its UID
                raise IndexError("There is no object #{}".format(obj.uid))
        else:
            # No UID -- this is a new object
            obj.uid = self._nextUid
            self._nextUid += 1
            self._objects[obj.uid] = obj

    def delete(self, obj):
        """
        Delete an object from the database.

        After successfully calling delete(), the object is gone. If you're still holding an old reference to it, get rid of it. Calls to store() will fail, and other parts of the object's interface are no longer guaranteed: it no longer represents anything still in the DB.

        Args:
            uid: The uid of the object to delete.

        Raises:
            IndexError: If there's no such object to be deleted.
        """
        del self._objects[obj.uid]

    def find_all(self, condition=(lambda x:True)):
        """
        Return a set of all objects in the database matching the given condition.

        Args:
            condition: Any function that takes an object and returns True or False.
        """
        return set(obj for obj in self._objects.values() if condition(obj))

    def find(self, condition=(lambda x:True)):
        """
        Return the single object in the database matching the given condition.

        Args:
            condition: Any function that takes an object and returns True or False.

        Raises:
            KeyError: If there are zero, or plural, objects matching the condition.
        """
        results = self.find_all(condition)
        if not results:
            raise KeyError("Nothing in the database matching {} (expected exactly 1)".format(condition))
        if len(results) > 1:
            raise KeyError("{} objects in the database matching {} (expected exactly 1)".format(len(results), condition))
        return results.pop()


class Object(object):

    """
    Something in the database.

    Attributes:
        name: The string used to identify the object to players. Non-unique.
        type: 'thing' in this implementation. Subclasses may set to 'player', 'room', or 'exit'. Other values are prohibited but should be treated, by convention, as equivalent to 'thing'.
        location: The Object containing this one. None, if this object isn't inside anything (required for rooms).
    """

    def __init__(self, name, location=None):
        """
        Create a brand-new object and add it to the database.

        Args: name, location (default None) as described in the class docstring
        """
        self.uid = None # This will be assigned when we call store() on the Database
        self.name = name
        self.location = location
        self.type = 'thing'

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

        db = Database()

        if self.location:
            # Add everything in the same place, as well as our contents
            result.extend(db.find_all(lambda obj: obj.location == self or obj.location == self.location))
        else:
            # We have no location; add only our contents
            result.extend(db.find_all(lambda obj: obj.location == self))

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

class Player(Object):

    """
    Something in the database that is, specifically, associated with a person.

    Attributes:
        name: Both the name as described on Object and the login name. Unique among Players.
        password: Result of calling this class's hash() method with the correct password.
    """

    def __init__(self, name, password):
        """
        Create a brand-new player and add it to the database.

        Args:
            name: The player's name.
            password: The player's password, in plaintext, to be discarded forever after this method call.
        """
        Object.__init__(self, name)
        self.type = 'player'
        self.password = self.hash(password)
        self.location = Database().find(lambda obj: obj.uid == 0)

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
        from server import factory
        try:
            factory.allProtocols[self.name].sendLine(line)
        except KeyError:
            pass

def player_by_name(name):
    """
    Search through the database for a particular player name.

    Args:
        name: The name of the player to find.

    Raises:
        KeyError: Sorry, buddy, there's nobody here by that name.
    """

    return Database().find(lambda obj: obj.type == 'player' and obj.name == name)


def player_name_taken(name):
    """Determine whether there exists a player with a particular name. Returns False if player_by_name(name) would raise KeyError."""
    try:
        player_by_name(name)
        return True
    except KeyError:
        return False
