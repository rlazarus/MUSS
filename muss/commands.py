import inspect
from pyparsing import SkipTo, StringEnd, Word, Optional, alphas

from muss.handler import Mode, NormalMode
from muss.locks import LockFailedError
from muss.parser import NotFoundError, Command, CommandName, PlayerName, ObjectIn, ReachableObject, ObjectUid
from muss.utils import get_terminal_size, UserError, find_one
from muss.db import find_all, Object, store


def all_commands(asDict=False):
    """
    Return a set of all the command classes defined here.
    """
    commands = []
    byname = {}
    for cls in globals().values():
        if inspect.isclass(cls) and issubclass(cls, Command) and cls is not Command:
            commands.append(cls)
            for name in cls().names + cls().nospace_names:
                if byname.get(name):
                    byname[name].append(cls)
                else:
                    byname[name] = [cls]
    if asDict:
        return byname
    else:
        return set(commands)
