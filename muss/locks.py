from contextlib import contextmanager


_authority = None


def authority():
    """
    Who is the current authority?
    """
    return _authority


@contextmanager
def authority_of(player):
    """
    Context manager to declare the current authority. Use like this:
    
    locked_action(x)  # Raises MissingAuthorityError, unless some other authority was already declared.
    with authority_of(alice):
        locked_action(x)  # Allowed, if Alice passes the lock.
        locked_action(y)  # Raises LockFailedError, if Alice fails the lock.
        
    Args:
        player: The player to be passed to all locks inside the "with" statement.
    """
    global _authority

    old_authority, _authority = _authority, player
    yield
    _authority = old_authority


class Lock(object):
    """
    Superclass of all lock types: rules for determining whether a particular action is available to a particular player.
    """
    
    def __call__(self, player=None):
        """
        Returns True if the given player passes this lock, False otherwise. Defaults to checking against the current authority.
        """
        if authority() is None:
            if self.__class__ is Pass:
                return True
            else:
                raise MissingAuthorityError

        if player is None:
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


class Has(Lock):
    """
    Passes iff the player is holding the given object.
    """

    def __init__(self, key):
        self.key = key

    def check(self, player):
        return (self.key.location is player)


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


class Not(Lock):
    """
    Passes iff the given lock fails.
    """

    def __init__(self, lock):
        self.lock = lock

    def check(self, player):
        return not self.lock(player)


class Pass(Lock):
    """
    Always passes.
    """

    def check(self, player):
        return True


class Fail(Lock):
    """
    Always fails.
    """

    def check(self, player):
        return False


class Error(Exception):
    pass


class LockFailedError(Error):
    pass

class MissingAuthorityError(Error):
    pass
