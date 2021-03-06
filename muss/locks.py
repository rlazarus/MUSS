import contextlib

from muss import utils


_authority = None


def authority():
    """
    Who is the current authority?
    """
    return _authority


@contextlib.contextmanager
def authority_of(player):
    """
    Context manager to declare the current authority. Use like this:

    locked_action(x)  # Raises MissingAuthorityError, unless some other
                      # authority was already declared.

    with authority_of(alice):
        locked_action(x)  # Allowed, if Alice passes the lock.
        locked_action(y)  # Raises LockFailedError, if Alice fails the lock.

    Args:
        player: The player to be passed to all locks inside the "with"
            statement.
    """
    global _authority

    old_authority, _authority = _authority, player
    try:
        yield
    finally:
        _authority = old_authority


# If this is the current authority, no locks are checked; everything is
# permitted.
SYSTEM = object()


class AttributeLock(object):
    """
    Manages the ownership of, and locks on, an attribute of an Object. Doesn't
    keep track of which attribute is locked; that's handled by the attr_locks
    dict on the Object.

    Anyone can see that the attribute exists, whether or not they pass the
    get_lock. (Otherwise they'd be able to find out by attempting to create
    it.)

    Only the owner of an attribute may delete it -- except that the owner of the
    Object can obviously delete the Object, disappearing the attribute along
    with it.

    Perhaps confusingly, an AttributeLock is not a Lock; rather, it holds Locks.

    Attributes: (whoa)
        owner: the owner of the attribute (defaults to the authority when the
            AttributeLock is created)
        get_lock: the Lock which must be passed to read the attribute (defaults
            to Pass())
        set_lock: the Lock which must be passed to write to the attribute
            (defaults to Is(owner), but you may want to set it explicitly to an
            OwnsAttribute lock on the attribute, in case ownership changes)
    """
    def __init__(self, owner=None, get_lock=None, set_lock=None):
        if owner is not None:
            self.owner = owner
        else:
            self.owner = authority()

        if get_lock is not None:
            self.get_lock = get_lock
        else:
            self.get_lock = Pass()

        if set_lock is not None:
            self.set_lock = set_lock
        else:
            self.set_lock = Is(owner)


class Lock(object):
    """
    Superclass of all lock types: rules for determining whether a particular
    action is available to a particular player.
    """

    def __call__(self, player=None):
        """
        Returns True if the given player passes this lock, False otherwise.
        Defaults to checking against the current authority.
        """
        if player is None:
            if authority() is None:
                raise MissingAuthorityError
            else:
                player = authority()

        if player is SYSTEM:
            return True
        else:
            with authority_of(SYSTEM):
                return self.check(player)

    def check(self, player):
        raise NotImplementedError


class Is(Lock):
    """
    Passes only for the given player.
    """

    def __init__(self, trustee):
        self.trustee = trustee

    def check(self, player):
        return (self.trustee is player)

    def __repr__(self):
        return "Is({!r})".format(self.trustee)


class In(Lock):
    """
    Passes for members of the given collection. The collection is stored by
    reference and may be mutable; membership is checked at evaluation time, not
    creation time.
    """

    def __init__(self, trustees):
        self.trustees = trustees

    def check(self, player):
        return (player in self.trustees)

    def __repr__(self):
        return "In({!r})".format(self.trustees)


class Has(Lock):
    """
    Passes iff the player is holding the given object.
    """

    def __init__(self, key):
        self.key = key

    def check(self, player):
        return (self.key.location is player)

    def __repr__(self):
        return "Has({!r})".format(self.key)


class Owns(Lock):
    """
    Passes iff the player is the owner of the given object.
    """

    def __init__(self, prop):
        self.prop = prop

    def check(self, player):
        return (self.prop.owner is player)

    def __repr__(self):
        return "Owns({!r})".format(self.prop)


class OwnsAttribute(Lock):
    """
    Passes iff the player is the owner of the given attribute.
    """

    def __init__(self, obj, attr):
        self.obj = obj
        self.attr = attr

    def check(self, player):
        try:
            return self.obj.attr_locks[self.attr].owner is player
        except KeyError:
            # If the attr doesn't exist, the lock fails.
            return False

    def __repr__(self):
        return "OwnsAttribute({!r}, {}".format(self.obj, self.attr)


class And(Lock):
    """
    Passes iff all of the given locks pass.
    """

    def __init__(self, *locks):
        self.locks = locks

    def check(self, player):
        for lock in self.locks:
            if not lock(player):
                return False
        else:
            return True

    def __repr__(self):
        return " & ".join("({!r})".format(lock) if isinstance(lock, Or)
                          else repr(lock) for lock in self.locks)

class Or(Lock):
    """
    Passes iff any of the given locks passes.
    """

    def __init__(self, *locks):
        self.locks = locks

    def check(self, player):
        for lock in self.locks:
            if lock(player):
                return True
        else:
            return False

    def __repr__(self):
        return " | ".join("({!r})".format(lock) if isinstance(lock, And)
                          else repr(lock) for lock in self.locks)


class Not(Lock):
    """
    Passes iff the given lock fails.
    """

    def __init__(self, lock):
        self.lock = lock

    def check(self, player):
        return not self.lock(player)

    def __repr__(self):
        return "Not({!r})".format(self.lock)


class Pass(Lock):
    """
    Always passes.
    """

    def __call__(self, player=None):
        # Override default behavior; doesn't matter what the authority is, or
        # even if there is authority, just pass.
        return True

    def __repr__(self):
        return "Pass()"


class Fail(Lock):
    """
    Always fails, except for SYSTEM (in which case the lock should not be
    checked).
    """

    def check(self, player):
        return False

    def __repr__(self):
        return "Fail()"


class LockFailedError(utils.UserError):
    pass


class MissingAuthorityError(Exception):
    pass
