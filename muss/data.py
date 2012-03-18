import hashlib

class Object(object):

    """
    Something in the database.

    Attributes:
        name: The string used to identify the object to players. Non-unique.
    """

    def __init__(self, name):
        """
        Create a brand-new object and add it to the database.

        Args:
            name: The object's name.
            type: 'thing' in this implementation. Subclasses may set to 'player', 'room', or 'exit'.
        """
        self.name = name
        self.type = 'thing'
        _database.append(self)


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


# In an extremely temporary measure, this *is* the database. It will eventually be replaced by something sane.
_database = [] 


def player_by_name(name):
    """
    Search through the database for a particular player name.

    Args:
        name: The name of the player to find.

    Raises:
        KeyError: Sorry, buddy, there's nobody here by that name.
    """
    for obj in _database:
        if obj.type == 'player' and obj.name == name:
            return obj

    # Still here?
    raise KeyError("No player named {}".format(name))


def player_name_taken(name):
    """Determine whether there exists a player with a particular name. Returns False if player_by_name(name) would raise KeyError."""
    for obj in _database:
        if obj.type == 'player' and obj.name == name:
            return True

    return False
