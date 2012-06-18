from pyparsing import ParseException, Optional, OneOrMore, SkipTo, LineEnd, Token, Literal, Word, printables, alphas

from muss.utils import UserError, find_one
from muss.db import Object, Player, find_all

# Exceptions

class MatchError(UserError):
    def __init__(self, token="thing", test_string=""):
        self.token = token
        self.test_string = test_string

class AmbiguityError(MatchError):
    def __init__(self, token="one", test_string="", matches=[]):
        super(AmbiguityError, self).__init__(token, test_string)
        self.matches = matches

    def __str__(self):
        if self.matches and self.matches[0][0] != self.matches[1][0]:
            # i.e. we have some and they differ
            verbose = "Which {} do you mean?".format(self.token)
            match_names = sorted([t[0] for t in self.matches])
            verbose += " ({})".format(", ".join(match_names))
        else:
            verbose = 'I don\'t know which {} called "{}" you mean.'.format(self.token, self.test_string)
        return verbose


class NotFoundError(MatchError):
    def __str__(self):
        verbose = "I don't know of a {} ".format(self.token)
        if self.test_string:
            verbose += 'called "{}."'.format(self.test_string)
        else:
            verbose += "by that name."
        return verbose


# Tokens

Article = Literal("a") | Literal("an") | Literal("the")
Article.name = "article"

ObjectName = Optional(Article).suppress() + OneOrMore(Word(alphas))
ObjectName.name = "object name"

class ObjectIn(Token):
    def __init__(self, location, returnAll=False):
        super(ObjectIn, self).__init__()
        self.location = location
        self.returnAll = returnAll
        if isinstance(location, Object):
            if isinstance(location, Player):
                where = "{}'s inventory".format(location.name)
            else:
                where = location.name
            self.name = "object in {}".format(where)
        else:
            raise TypeError("Invalid location: " + str(location))

    def parseImpl(self, instring, loc, doActions=True):
        loc, name = ObjectName.parseImpl(instring, loc, doActions)
        test_name = name.lower()
        objects = find_all(lambda p: p.location == self.location)
        try:
            if returnAll:
                matches = find_by_name(test_name, objects, attributes=["name"])
                return ((loc, matches),)
            else:
                matched_object = find_one(test_name, objects, attributes=["name"])
                return loc, matched_object
        except MatchError as e:
            e.token = self.name
            e.test_string = name
            raise e


class NearbyObject(Token):
    def __init__(self, player, priority=None):
        super(NearbyObject, self).__init__()
        self.name = "nearby object"
        self.player = player
        if priority in [None, "room", "inventory"]:
            self.priority = priority
        else:
            raise KeyError("Unknown priority ({}), expected 'room' or 'inventory'".format(priority))

    def parseImpl(self, instring, loc, doActions=True):
        grammar = Optional("my")("my") + ObjectName("object")
        loc, parse_results = ObjectName.parseImpl(instring, loc, doActions)
        results_dict = dict(parse_results)
        if results_dict.get("my"):
            inventory_only = True
        else:
            inventory_only = False
        object_name = results_dict["object"]
        test_name = object_name.lower()

        inv = {}
        room = {}
        inv["perfect"], inv["partial"] = ObjectIn(self.player, returnAll=True).parseString(test_name, parseAll=True)
        room["perfect"], room["partial"] = ObjectIn(self.player.location, returnAll=True).parseString(test_name, parseAll=True)

        matches = []
        if inventory_only:
            if inv["perfect"]:
                matches = inv["perfect"]
            else:
                matches = inv["partial"]
        else:
            if self.priority:
                precedence = {}
                precedence["inventory"] = [inv["perfect"], room["perfect"], inv["partial"], room["partial"]]
                precedence["room"] = [room["perfect"], inv["perfect"], room["partial"], inv["partial"]]
                for match_list in precedence[self.priority]:
                    if match_list:
                        matches = match_list
                        break
            else:
                matches = inv["perfect"] + room["perfect"]
                if not matches:
                    matches = inv["partial"] + room["partial"]

        if len(matches) == 1:
            name, match = matches[0]
            return loc, match
        elif matches:
            raise AmbiguityError(self.name, object_name, matches)
        else:
            raise NotFoundError(self.name, object_name)


class CommandName(Word):
    def __init__(self, fullOnly=False):
        super(CommandName, self).__init__(printables)
        self.fullOnly = fullOnly
        self.name = "command name"

    def parseImpl(self, instring, loc, doActions=True):
        loc, text = super(CommandName, self).parseImpl(instring, loc, doActions)
        test_name = text.lower()
        try:
            if self.fullOnly:
                attributes = ["names"]
            else:
                attributes = ["names", "nospace_names"]
            from muss.commands import all_commands
            name, command = find_one(test_name, all_commands(), attributes=attributes)
            # this is a dict because pyparsing messes up tuples and lists as token return values.
            # I'm not sure why. if you figure it out, send them a patch, will you?
            return loc, ((name, command),)
        except MatchError as exc:
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
        self.name = "player name"

    def parseImpl(self, instring, loc, doActions=True):
        from muss.utils import find_one
        match = ""
        try:
            loc, match = super(PlayerName, self).parseImpl(instring, loc, doActions)
            match = match.lower()
            players = find_all(lambda p: p.type == 'player')
            name, player = find_one(match, players, attributes=["name"])
            return loc, player
        except MatchError as e:
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
