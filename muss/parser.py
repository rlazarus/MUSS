from pyparsing import ParseException, Optional, SkipTo, LineEnd, Word, printables, alphas


# Exceptions

class AmbiguityError(Exception):
    def __init__(self, token="one", test_string="", matches=[]):
        self.token = token
        self.matches = matches
        self.test_string = test_string

    def verbose(self):
        if self.matches and self.matches[0][0] != self.matches[1][0]:
            # i.e. we have some and they differ
            verbose = "Which {} do you mean?".format(self.token)
            match_names = sorted([t[0] for t in self.matches])
            verbose += " ({})".format(", ".join(match_names))
        else:
            verbose = 'I don\'t know which {} called "{}" you mean.'.format(self.token, self.test_string)
        return verbose


class NotFoundError(Exception):
    def __init__(self, token="thing", test_string=""):
        self.token = token
        self.test_string = test_string

    def verbose(self):
        verbose = "I don't know of a {} ".format(self.token)
        if self.test_string:
            verbose += 'called "{}."'.format(self.test_string)
        else:
            verbose += "by that name."
        return verbose


# Tokens

class CommandName(Word):
    def __init__(self, fullOnly=False):
        super(CommandName, self).__init__(printables)
        self.fullOnly = fullOnly

    def __str__(self):
        return "command name"

    def parseImpl(self, instring, loc, doActions=True):
        loc, text = super(CommandName, self).parseImpl(instring, loc, doActions)
        test_name = text.lower()
        try:
            if self.fullOnly:
                attributes = ["names"]
            else:
                attributes = ["names", "nospace_names"]
            from muss.commands import all_commands
            from muss.utils import find_one
            name, command = find_one(test_name, all_commands(), attributes=attributes)
            # this is a dict because pyparsing messes up tuples and lists as token return values.
            # I'm not sure why. if you figure it out, send them a patch, will you?
            return loc, ((name, command),)
        except (AmbiguityError, NotFoundError) as exc:
            loc -= len(instring.split(None, 1)[0])
            exc.loc = loc
            exc.pstr = instring
            exc.token = "command"
            exc.test_string = test_name
            raise exc


class PlayerName(Word):
    """
    Token to match a full player name, regardless of whether that player is nearby.

    The match is case-insensitive; the returned match is always equal to the player's actual name.
    """
    _allowed_chars = alphas  # This is temporary; when there are rules for legal player names, we'll draw directly from there.

    def __init__(self):
        super(PlayerName, self).__init__(alphas)

    def __str__(self):
        return "player name"

    def parseImpl(self, instring, loc, doActions=True):
        from muss.utils import find_one
        from muss.db import find_all
        match = ""
        try:
            loc, match = super(PlayerName, self).parseImpl(instring, loc, doActions)
            match = match.lower()
            players = find_all(lambda p: p.type == 'player')
            name, player = find_one(match, players, attributes=["name"])
            return loc, player
        except (AmbiguityError, NotFoundError) as e:
            e.token = "player"
            raise e
        except ParseException:
            # not a Word
            raise NotFoundError(token="player", test_string=match)


# Other definitions

class Command(object):

    """
    The superclass for all commands -- local or global, built-in or user-defined.
    """
    args = LineEnd() # By default, expect no arguments

    @property
    def names(self):
        if hasattr(self, "name"):
            if isinstance(self.name, list):
                return self.name
            else:
                return [self.name]
        else:
            return []

    @property
    def nospace_names(self):
        if hasattr(self, "nospace_name"):
            if isinstance(self.nospace_name, list):
                return self.nospace_name
            else:
                return [self.nospace_name]
        else:
            return []

    @property
    def usages(self):
        if hasattr(self, "usage"):
            if isinstance(self.usage, list):
                return self.usage
            else:
                return [self.usage]
        else:
            if hasattr(self.args, "exprs"):
                token_list = self.args.exprs
            else:
                token_list = [self.args]
            printable_tokens = []
            for token in token_list:
                if isinstance(token, LineEnd):
                    continue
                printable_token = str(token).replace(" ", "-")
                if not isinstance(token, Optional):
                    printable_token = "<{}>".format(printable_token)
                printable_tokens.append(printable_token)
            if printable_tokens:
                arg_string = " " + " ".join(printable_tokens)
            else:
                arg_string = ""
            cases = []
            for name in self.names:
                cases.append(name + arg_string)
            for nospace_name in self.nospace_names:
                cases.append(nospace_name + arg_string)
            return sorted(cases)
