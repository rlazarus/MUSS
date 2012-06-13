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
