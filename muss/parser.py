from pyparsing import ParseException, Combine, Optional, Suppress, OneOrMore, SkipTo, LineEnd, Token, CaselessKeyword, Word, printables, alphas

from muss.utils import UserError, find_one, find_by_name, article
from muss.db import Object, Player, find_all

# Exceptions

class MatchError(ParseException, UserError):
    def __init__(self, pstr="", loc=0, msg=None, elem=None, token="thing", test_string=""):
        super(MatchError, self).__init__(pstr, loc, msg, elem)
        self.token = token
        self.test_string = test_string

class AmbiguityError(MatchError):
    def __init__(self, pstr="", loc=0, msg=None, elem=None, token="one", test_string="", matches=[]):
        super(AmbiguityError, self).__init__(pstr, loc, msg, elem, token, test_string)
        self.matches = matches

    def verbose(self):
        if self.matches and self.matches[0][0] != self.matches[1][0]:
            # i.e. we have some and they differ
            verbose = "Which {} do you mean?".format(self.token)
            match_names = sorted([t[0] for t in self.matches])
            verbose += " ({})".format(", ".join(match_names))
        else:
            verbose = 'I don\'t know which {} called "{}" you mean.'.format(self.token, self.test_string)
        return verbose


class NotFoundError(MatchError):
    def verbose(self):
        verbose = "I don't know of {} {} ".format(article(self.token), self.token)
        if self.test_string:
            verbose += 'called "{}."'.format(self.test_string)
        else:
            verbose += "by that name."
        return verbose


# Tokens

Article = CaselessKeyword("an") | CaselessKeyword("a") | CaselessKeyword("the")
Article.name = "article"

ObjectName = Article.suppress() + OneOrMore(Word(printables)) | OneOrMore(Word(printables))
# doing it this way instead of Optional() so an object called "the" will match.
ObjectName.name = "object name"

class ObjectIn(Token):
    def __init__(self, location, returnAll=False):
        super(ObjectIn, self).__init__()
        if isinstance(location, Object):
            self.location = location
        else:
            raise(TypeError("Invalid location: {}".format(location)))
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
        objects = find_all(lambda p: p.location == self.location)
        test_string = instring
        while test_string:
            try:
                test_loc, parse_result = ObjectName.parseImpl(test_string, loc, doActions)
                name = " ".join(parse_result)
            except ParseException as e:
                break
            test_name = name.lower()
            all_matches = find_by_name(test_name, objects, attributes=["name"])
            if all_matches[0] or all_matches[1]:
                loc = test_loc
                # this instead of "if all_matches" because all_matches will always have two elements
                # even if they're empty
                if self.returnAll:
                    return loc, all_matches
                else:
                    # to improve later: just check the length of all_matches
                    # and raise our own exceptions instead of farming to find_one
                    matched_object = find_one(test_name, objects, attributes=["name"])
                    return loc, matched_object
            if len(test_string.split()) == 1:
                # we just tested the first word alone
                break
            test_string = test_string.split(None, 1)[0]
        raise(NotFoundError(token=self.name, test_string=instring))


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
        loc, parse_results = ObjectName.parseImpl(instring, loc, doActions)
        if parse_results[0] == "my":
            parse_results.pop(0)
            inventory_only = True
        else:
            inventory_only = False
        object_name = " ".join(parse_results)
        test_name = object_name.lower()

        room_matches = None
        inv_matches = None
        room = {"perfect":[], "partial":[]}
        inv = {"perfect":[], "partial":[]}
        try:
            room_loc, room_matches = ObjectIn(self.player.location, returnAll=True).parseImpl(test_name, 0, doActions=doActions)
            room["perfect"], room["partial"] = room_matches
        except NotFoundError as e:
            pass
        try:
            inv_loc, inv_matches = ObjectIn(self.player, returnAll=True).parseImpl(test_name, 0, doActions=doActions)
            inv["perfect"], inv["partial"] = inv_matches
        except NotFoundError as e:
            pass

        matches = []
        if inventory_only:
            if inv["perfect"]:
                matches = inv["perfect"]
            else:
                matches = inv["partial"]
        else:
            if self.priority:
                precedence = {}
                precedence["inventory"] = [inv["perfect"], inv["partial"], room["perfect"], room["partial"]]
                precedence["room"] = [room["perfect"], room["partial"], inv["perfect"], inv["partial"]]
                for match_list in precedence[self.priority]:
                    if match_list:
                        matches = match_list
                        break
            else:
                matches = inv["perfect"] + room["perfect"]
                if not matches:
                    matches = inv["partial"] + room["partial"]

        if len(matches) == 1:
            loc += len(matches[0])
            return loc, matches[0]
        elif matches:
            raise AmbiguityError(token=self.name, test_string=object_name, matches=matches)
        else:
            if inventory_only:
                token = "object in your inventory"
            else:
                token = self.name
            raise NotFoundError(token=token, test_string=object_name)

class ReachableObject(NearbyObject):
        def parseImpl(self, instring, loc, doActions=True):
            Preposition = CaselessKeyword("in") | CaselessKeyword("on") | CaselessKeyword("inside") | CaselessKeyword("from")
            grammar = NearbyObject(self.player, priority=self.priority)("object") | ObjectName("object") + Preposition("preposition") + NearbyObject(self.player)("container")
            # then CaselessKeyword("room") as an alternate container
            # then Combine(NearbyObject(self.player) + "'s inv".suppress() + Optional("entory").suppress())
            # when you have this working, instantiate nearbyobject(self.player) once and reuse it
            try:
                loc, match = grammar.parseImpl(instring, loc, doActions)
                if match[0]:
                    return loc, match
                else:
                    raise NotFoundError(test_string=instring)
            except MatchError as e:
                e.token = "reachable object"
                # ^ make this more specific if we can?
                print "loc was {}".format(e.loc)
                raise e


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
            raise NotFoundError(token="player", test_string=instring)


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
