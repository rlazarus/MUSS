from pyparsing import ParseException, Combine, Optional, Suppress, OneOrMore, SkipTo, LineEnd, StringEnd, Token, CaselessKeyword, Word, printables, alphas

from muss.utils import UserError, find_one, find_by_name, article
from muss.db import Object, Player, find_all


class MatchError(ParseException, UserError):
    def __init__(self, pstr="", loc=0, msg=None, elem=None, token="thing", test_string=""):
        if not msg and hasattr(elem, "errmsg"):
            self.msg = elem.errmsg
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


Article = CaselessKeyword("an") | CaselessKeyword("a") | CaselessKeyword("the")
Article.setName("article")


ObjectName = Article.suppress() + OneOrMore(Word(printables)) | OneOrMore(Word(printables))
# doing it this way instead of Optional() so an object called "the" will match.
ObjectName.setName("object name")


class ObjectIn(Token):
    """
    Matches an object in the given location.

    Args: location (to search in), returnAll (boolean, return the best set of matches instead of raising an AmbiguityError if set).
    """
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
            self.setName("object in {}".format(where))
        else:
            raise TypeError("Invalid location: " + str(location))

    def parseImpl(self, instring, loc, doActions=True):
        objects = find_all(lambda p: p.location == self.location)
        test_string = instring
        while test_string:
            # can probably replace this with a for loop
            # negative-indexing in from the end of the list
            try:
                test_loc, parse_result = ObjectName.parseImpl(test_string, loc, doActions)
                name = " ".join(parse_result)
            except ParseException as e:
                break
            test_name = name.lower()
            all_matches = find_by_name(test_name, objects)
            if all_matches[0] or all_matches[1]:
                # this instead of "if all_matches" because all_matches will always have two elements
                # even if they're empty
                loc = test_loc
                if self.returnAll:
                    perfect = [i[1] for i in all_matches[0]]
                    partial = [i[1] for i in all_matches[1]]
                    return loc, (perfect, partial)
                else:
                    # to improve later: just check the length of all_matches
                    # and raise our own exceptions instead of farming to find_one
                    matched_object = find_one(test_name, objects)
                    return loc, matched_object[1]
            if len(test_string.split()) == 1:
                # we just tested the first word alone
                break
            test_string = test_string.rsplit(None, 1)[0]
        raise(NotFoundError(loc=loc, elem=self, token=self.name, test_string=instring))


class NearbyObject(Token):
    """
    Matches an object in the player's inventory or the player's location. Accepts "my" keyword to specify inventory.

    Args: player (to search near); priority ("room," "inventory," or default None; will favor matches in that location)
    """
    def __init__(self, player, priority=None):
        super(NearbyObject, self).__init__()
        self.setName("nearby object")
        self.player = player
        if priority in [None, "room", "inventory"]:
            self.priority = priority
        else:
            raise KeyError("Unknown priority ({}), expected 'room' or 'inventory'".format(priority))

    def parseImpl(self, instring, loc, doActions=True):
        if instring[loc:].startswith("my "):
            loc += 3
            inventory_only = True
        else:
            inventory_only = False
        object_name = instring[loc:].strip()
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
            match = matches[0]
            if match.location is self.player:
                loc += inv_loc
            else:
                loc += room_loc
            return loc, match
        elif matches:
            raise AmbiguityError(loc=loc, elem=self, token=self.name, test_string=object_name, matches=matches)
        else:
            if inventory_only:
                token = "object in your inventory"
            else:
                token = self.name
            raise NotFoundError(loc=loc, elem=self, token=token, test_string=object_name)

class ReachableObject(NearbyObject):
    """
    Matches an object the player can reach, meaning it's either in the player's inventory, in the room, or inside another object in the same room (including another player's inventory). Syntax accepted:
        
        <object>            # checks inventory and room only
        <object> in room    # checks player's location
        <object> in <container>
        * <object> in <container>'s inv[entory]
        * <container>'s <object>

    * (planned, not done yet)

    Args: player (to search near); priority ("room," "inventory," or default None; will favor matches in that location)
    """
    def __init__(self, player, priority=None):
        super(ReachableObject, self).__init__(player, priority)
        self.setName("reachable object")

    def parseImpl(self, instring, loc, doActions=True):
        Preposition = CaselessKeyword("in") | CaselessKeyword("on") | CaselessKeyword("inside") | CaselessKeyword("from")
        Container = NearbyObject(self.player) | CaselessKeyword("room")
        preposition_grammar = SkipTo(Preposition + Container, include=True)
        possessive_grammar = SkipTo("'s ")("owner")
        nearby_grammar = NearbyObject(self.player, priority=self.priority)

        matched_preposition_grammar = False
        matched_possessive_grammar = False
        # SkipTo will want to eat the whole expression unless we split these up
        # (plus it gives us a chance to do a secondary postprocessing check)
        try:
            new_loc, parse_result = possessive_grammar.parseImpl(instring, loc, doActions)
            owner_name = " ".join(parse_result)
            owner = NearbyObject(self.player).parseString(owner_name, parseAll=True)[0]
            matched_possessive_grammar = True
            loc = new_loc + 3 # clearing "'s "
            object_name = instring[loc:]
        except ParseException:
            try:
                new_loc, parse_result = preposition_grammar.parseImpl(instring, loc, doActions)
                matched_preposition_grammar = True
                loc = new_loc
            except ParseException:
                try:
                    loc, parse_result = nearby_grammar.parseImpl(instring, loc, doActions)
                except MatchError as e:
                    raise e
        if matched_preposition_grammar:
            match_tokens = parse_result[0]
            container = match_tokens.pop()
            if container == "room":
                container = self.player.location
            preposition = match_tokens.pop()
            object_name = " ".join(match_tokens)
            try:
                match = ObjectIn(container).parseString(object_name, parseAll=True)
            except MatchError as e:
                e.test_string = object_name
                e.token = "object in {}".format(container.name)
                if container.type == "player":
                    e.token += "'s inventory"
                raise e
        elif matched_possessive_grammar:
            try:
                object_loc, match = ObjectIn(owner).parseImpl(object_name, 0, doActions)
                loc += object_loc
            except MatchError as e:
                e.test_string = object_name
                e.token = "object in {}'s inventory".format(owner)
                raise e
        else:
            match = parse_result
        return loc, match


class CommandName(Word):
    """
    Matches a valid command name and returns a (name, object) tuple.

    Args: fullOnly (boolean, ignores nospace names if set).
    """
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
            name, player = find_one(match, players)
            return loc, player
        except MatchError as e:
            e.token = "player"
            raise e
        except ParseException:
            # not a Word
            raise NotFoundError(loc=loc, elem=self, token="player", test_string=instring)


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
