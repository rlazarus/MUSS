import pyparsing as pyp

from muss import db, utils


class MatchError(pyp.ParseException, utils.UserError):
    def __init__(self, pstr="", loc=0, msg=None, elem=None, token=None):
        super(MatchError, self).__init__(pstr, loc, msg, elem)
        if token:
            self.token = token
        elif self.parserElement:
            self.token = str(self.parserElement)
        else:
            self.token = "thing"


class AmbiguityError(MatchError):
    def __init__(self, pstr="", loc=0, msg=None, elem=None, matches=[],
                 token=None):
        super(AmbiguityError, self).__init__(pstr, loc, msg, elem, token)
        if self.token == "thing":
            self.token = "one"
        self.matches = matches
        if matches and not self.loc:
            shortest = min(matches, key=len)
            for i, letter in enumerate(shortest):
                for match in matches:
                    if match[i] is not letter:
                        break
            self.loc = i

    def verbose(self):
        if self.matches:
            if isinstance(self.matches[0], tuple):
                matches_different = self.matches[0][0] != self.matches[1][0]
            else:
                matches_different = self.matches[0] != self.matches[1]
            if matches_different:
                verbose = "Which {} do you mean?".format(self.token)
                match_names = sorted([t[0] for t in self.matches])
                verbose += " ({})".format(", ".join(match_names))
            elif self.pstr:
                verbose = ('I don\'t know which {} called "{}" you mean.'
                           .format(self.token, self.pstr))
        if not self.matches or (not matches_different and not self.pstr):
            verbose = "I don't know which {} you mean.".format(self.token)
        return verbose


class NotFoundError(MatchError):
    def verbose(self):
        verbose = "I don't know of {} {} ".format(utils.article(self.token),
                                                  self.token)
        if self.pstr:
            verbose += 'called "{}"'.format(self.pstr)
        else:
            verbose += "by that name."
        return verbose


class NoSuchUidError(NotFoundError):
    def verbose(self):
        return "There is no object {}.".format(self.pstr)


Article = (pyp.CaselessKeyword("an") | pyp.CaselessKeyword("a") |
           pyp.CaselessKeyword("the"))
Article.setName("article")
# This will match "THE" but return "the."
# Not sure if that's the right behavior, but that's what it does.


Text = pyp.Regex(r".+")
Text.setName("text")
# Cheerfully adapted from restOfLine, substituting + for *.


ObjectName = (Article.suppress() + pyp.OneOrMore(pyp.Word(pyp.printables)) |
              pyp.OneOrMore(pyp.Word(pyp.printables)))
# Doing it this way instead of Optional() so an object called "the" will match.
ObjectName.setName("object name")

# Yes, pyparsing defines these, but not with QuotedString for some reason and
# we want that because it can unquote the strings for us automatically.
SingleQuoted = pyp.QuotedString(quoteChar="'", escChar="\\")
DoubleQuoted = pyp.QuotedString(quoteChar='"', escChar="\\")
TripleQuoted = pyp.QuotedString(quoteChar='"""', multiline=True)
PythonQuoted = TripleQuoted | DoubleQuoted | SingleQuoted


class EmptyLine(pyp.Token):
    def __init__(self):
        super(EmptyLine, self).__init__()
        self.name = "empty line"

    def parseImpl(self, instring, loc, doActions=True):
        if instring:
            raise pyp.ParseException(instring, loc, self.errmsg, self)
        return loc, ""


class NonEmptyLine(pyp.Token):
    def __init__(self):
        super(NonEmptyLine, self).__init__()
        self.name = "non-empty line"

    def parseImpl(self, instring, loc, doActions=True):
        if not instring:
            raise pyp.ParseException(instring, loc, self.errmsg, self)
        return loc, instring


class OneOf(pyp.Token):
    """
    General token for matching one of a discrete set of things.

    Attributes:
        name: A user-facing name for the token, like "object in the room".
        options: A dict mapping input strings to output objects. If the input
            matches one of the keys unambiguously, the return will be the
            associated value.
        pattern: What to look for in the input string. Defaults to
            Word(printables).
        exact: If True, disallow prefix matching -- e.g. "ex" in {"example": 0}.
            Defaults to False.
    """
    def __init__(self, name, options, pattern=None, exact=False):
        super(OneOf, self).__init__()
        self.name = name
        self.options = options
        if pattern is None:
            pattern = pyp.Word(pyp.printables)
        self.pattern = pattern
        self.exact = exact

    def parseImpl(self, instring, loc, doActions=True):
        try:
            loc, parse_result = self.pattern.parseImpl(instring, loc, doActions)
        except pyp.ParseException:
            raise NotFoundError(instring, loc, self.errmsg, self)
        text = parse_result.lower()

        # Find exact matches first:
        matches = filter(
            lambda (key, _): key.lower() == text,
            self.options.items())
        if len(matches) == 1:
            return loc, matches[0][1]
        elif len(matches) > 1:
            raise AmbiguityError(instring, loc, self.errmsg, self, matches)

        # No exact matches. Find partial matches:
        if self.exact:
            raise NotFoundError(instring, loc, self.errmsg, self)
        matches = filter(
            lambda (key, _): key.lower().startswith(parse_result.lower()),
            self.options.items())
        if not matches:
            raise NotFoundError(instring, loc, self.errmsg, self)
        if len(matches) == 1:
            return loc, matches[0][1]
        if len(matches) > 1:
            raise AmbiguityError(instring, loc, self.errmsg, self, matches)


class ObjectIn(pyp.Token):
    """
    Matches an object in the given location.

    Args:
        location: An Object to search in.
        returnAll: If True, return the best set of matches instead of raising
            AmbiguityError.
    """
    def __init__(self, location, returnAll=False):
        super(ObjectIn, self).__init__()
        if isinstance(location, db.Object):
            self.location = location
        else:
            raise(TypeError("Invalid location: {}".format(location)))
        self.returnAll = returnAll
        if isinstance(location, db.Object):
            if isinstance(location, db.Player):
                where = "{}'s inventory".format(location.name)
            else:
                where = location.name
            self.name = "object in {}".format(where)
        else:
            raise TypeError("Invalid location: " + str(location))

    def parseImpl(self, instring, loc, doActions=True):
        objects = db.find_all(lambda p: p.location == self.location)
        test_string = instring
        while test_string:
            try:
                test_loc, parse_result = ObjectName.parseImpl(test_string, loc,
                                                              doActions)
                name = " ".join(parse_result)
            except pyp.ParseException as e:
                break
            test_name = name.lower()
            all_matches = utils.find_by_name(test_name, objects)
            # This instead of "if all_matches" because all_matches will always
            # have two elements even if they're empty.
            if all_matches[0] or all_matches[1]:
                perfect = [i[1] for i in all_matches[0]]
                partial = [i[1] for i in all_matches[1]]
                loc = test_loc
                if self.returnAll:
                    return loc, (perfect, partial)
                else:
                    if len(perfect) == 1:
                        return loc, perfect[0]
                    elif len(perfect):
                        raise(AmbiguityError(instring, loc, self.errmsg, self,
                                             all_matches[0]))
                    elif len(partial) == 1 and not len(perfect):
                        return loc, partial[0]
                    else:
                        # Multiple partial matches
                        raise(AmbiguityError(instring, loc, self.errmsg, self,
                                             all_matches[1]))
            if len(test_string.split()) == 1:
                # We just tested the first word alone.
                break
            test_string = test_string.rsplit(None, 1)[0]
        raise(NotFoundError(instring, loc, self.errmsg, self))


class NearbyObject(pyp.Token):
    """
    Matches an object in the player's inventory or the player's location.
    Accepts "my" keyword to specify inventory.

    Args:
        player: A Player to search near.
        priority: If "room" or "inventory", the search will favor matches there.
            If None, perfect matches in either set are preferred over partial
            matches in either.
    """
    def __init__(self, player, priority=None):
        super(NearbyObject, self).__init__()
        self.name = "nearby object"
        self.player = player
        if priority in [None, "room", "inventory"]:
            self.priority = priority
        else:
            raise ValueError("Unknown priority ({}), expected 'room' or "
                             "'inventory'".format(priority))

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
        room = {"perfect": [], "partial": []}
        inv = {"perfect": [], "partial": []}
        try:
            token = ObjectIn(self.player.location, returnAll=True)
            room_loc, room_matches = token.parseImpl(test_name, 0,
                                                     doActions=doActions)
            room["perfect"], room["partial"] = room_matches
        except NotFoundError as e:
            pass
        room_name = self.player.location.name.lower()
        if test_name == room_name:
            room["perfect"].append(self.player.location)
            room_loc = loc + len(test_name)
        elif room_name.startswith(test_name) or (" " + test_name) in room_name:
            room["partial"].append(self.player.location)
            room_loc = loc + len(test_name)
        try:
            token = ObjectIn(self.player, returnAll=True)
            inv_loc, inv_matches = token.parseImpl(test_name, 0,
                                                   doActions=doActions)
            inv["perfect"], inv["partial"] = inv_matches
        except NotFoundError as e:
            pass

        matches = []
        any_perfect = False
        if inventory_only:
            if inv["perfect"]:
                matches = inv["perfect"]
                any_perfect = True
            else:
                matches = inv["partial"]
        else:
            if self.priority:
                if self.priority == "inventory":
                    first_list = inv
                    second_list = room
                else:
                    first_list = room
                    second_list = inv
                if first_list["perfect"]:
                    matches = first_list["perfect"]
                    any_perfect = True
                elif first_list["partial"]:
                    matches = first_list["partial"]
                elif second_list["perfect"]:
                    matches = second_list["perfect"]
                    any_perfect = True
                else:
                    matches = second_list["partial"]
            else:
                matches = inv["perfect"] + room["perfect"]
                if matches:
                    any_perfect = True
                else:
                    matches = inv["partial"] + room["partial"]

        if not any_perfect:
            if test_name == "me":
                return loc+2, [self.player]
            if test_name == "here":
                return loc+4, [self.player.location]

        if len(matches) == 1:
            match = matches[0]
            if match.location is self.player:
                loc += inv_loc
            else:
                loc += room_loc
            return loc, match
        elif matches:
            raise AmbiguityError(object_name, loc, self.errmsg, self,
                                 [(m.name, m) for m in matches])
        else:
            if inventory_only:
                token = "object in your inventory"
            else:
                token = None
            raise NotFoundError(object_name, loc, self.errmsg, self, token)


class ReachableObject(NearbyObject):
    """
    Matches an object the player can reach, meaning it's either in the player's
    inventory, in the room, or inside another object in the same room
    (including another player's inventory). Syntax accepted:

        <object>            # checks inventory and room only
        <object> in room    # checks player's location
        <object> in <container>
        <container>'s <object>

    Args:
        player: A Player to search near.
        priority: If "room" or "inventory", the search will favor matches there.
            If None, perfect matches in either set are preferred over partial
            matches in either.
    """
    def __init__(self, player, priority=None):
        super(ReachableObject, self).__init__(player, priority)
        self.name = "reachable object"

    def parseImpl(self, instring, loc, doActions=True):
        Preposition = (pyp.CaselessKeyword("in") | pyp.CaselessKeyword("on") |
                       pyp.CaselessKeyword("inside") |
                       pyp.CaselessKeyword("from"))
        Container = NearbyObject(self.player) | pyp.CaselessKeyword("room")
        preposition_grammar = pyp.SkipTo(Preposition + Container, include=True)
        possessive_grammar = pyp.SkipTo("'s ")("owner")
        nearby_grammar = NearbyObject(self.player, priority=self.priority)

        matched_preposition_grammar = False
        matched_possessive_grammar = False
        # SkipTo will want to eat the whole expression unless we split these up
        # (plus it gives us a chance to do a secondary postprocessing check)
        try:
            new_loc, parse_result = possessive_grammar.parseImpl(instring, loc,
                                                                 doActions)
            owner_name = " ".join(parse_result)
            token = NearbyObject(self.player)
            owner = token.parseString(owner_name, parseAll=True)[0]
            matched_possessive_grammar = True
            loc = new_loc + 3  # clearing "'s "
            object_name = instring[loc:]
        except pyp.ParseException:
            try:
                new_loc, parse_result = preposition_grammar.parseImpl(
                    instring, loc, doActions)
                matched_preposition_grammar = True
                loc = new_loc
            except pyp.ParseException:
                try:
                    loc, parse_result = nearby_grammar.parseImpl(instring, loc,
                                                                 doActions)
                except MatchError as e:
                    if hasattr(e, "matches"):
                        e.__init__(instring, e.loc, self.errmsg, self,
                                   e.matches)
                    else:
                        e.__init__(instring, e.loc, self.errmsg, self)
                    raise e
        if matched_preposition_grammar:
            match_tokens = parse_result[0]
            container = match_tokens.pop()
            if container == "room":
                container = self.player.location
            preposition = match_tokens.pop()
            object_name = " ".join(match_tokens)
            try:
                token = ObjectIn(container)
                match = token.parseString(object_name, parseAll=True)
            except MatchError as e:
                e.pstr = object_name
                e.token = "object in {}".format(container.name)
                if container.type == "player":
                    e.token += "'s inventory"
                raise e
        elif matched_possessive_grammar:
            try:
                token = ObjectIn(owner)
                object_loc, match = token.parseImpl(object_name, 0, doActions)
                loc += object_loc
            except MatchError as e:
                e.pstr = object_name
                e.token = "object in {}'s inventory".format(owner)
                raise e
        else:
            match = parse_result
        return loc, match


class ObjectUid(pyp.Token):
    """
    Matches an object uid of the form #42 and returns the appropriate object,
    regardless of whether it's nearby. Raises UserError if no such object
    exists.
    """
    name = "object UID"
    pattern = pyp.Combine(pyp.Suppress("#") + pyp.Word(pyp.printables)("uid"))

    def parseImpl(self, instring, loc, doActions=True):
        try:
            result = self.pattern.parseString(instring[loc:])
            if not result.uid.isdigit():
                raise pyp.ParseException(instring, loc, self.errmsg, self)
            uid = int(result.uid)
            return loc + len(result.uid) + 1, db.get(uid)
        except pyp.ParseException:
            # Nope! Raise ours instead.
            raise pyp.ParseException(instring, loc, self.errmsg, self)
        except KeyError:
            raise NoSuchUidError("#{}".format(result.uid), loc, self.errmsg,
                                 self)


class CommandName(pyp.Word):
    """
    Matches a valid command name and returns a (name, object) tuple.

    Args: fullOnly (boolean, ignores nospace names if set).
    """
    def __init__(self, fullOnly=False):
        super(CommandName, self).__init__(pyp.printables)
        self.fullOnly = fullOnly
        self.name = "command"

    def parseImpl(self, instring, loc, doActions=True):
        loc, text = super(CommandName, self).parseImpl(instring, loc, doActions)
        test_name = text.lower()
        try:
            if self.fullOnly:
                attributes = ["names"]
            else:
                attributes = ["names", "nospace_names"]
            from muss.handler import all_commands
            perfect_matches, partial_matches = utils.find_by_name(
                test_name, all_commands(), attributes=attributes)
            adjusted_perfect = [x[1] for x in perfect_matches]
            adjusted_partial = []
            for match_tuple in partial_matches:
                name, command = match_tuple
                if not command.require_full:
                    adjusted_partial.append(command)
            matches = adjusted_perfect + adjusted_partial
            command_tuple = utils.find_one(test_name, matches,
                                           attributes=attributes)
            return loc, (command_tuple,)
        except MatchError as exc:
            exc.token = "command"
            exc.pstr = test_name
            raise exc


class PlayerName(OneOf):
    def __init__(self):
        super(PlayerName, self).__init__(
            "player",
            {p.name: p for p in db.find_all(lambda p: p.type == 'player')},
            pyp.Word(pyp.alphas))


class ReachableOrUid(pyp.Token):
    """
    Matches either a ReachableObject with the given argument or any object by
    UID.
    """
    def __init__(self, player, priority=None):
        super(ReachableOrUid, self).__init__()
        self.name = "reachable object or UID"
        self.player = player
        self.priority = priority

    def parseImpl(self, instring, loc, doActions=True):
        try:
            loc, parse_result = ObjectUid().parseImpl(instring, loc, doActions)
            return loc, parse_result
        except pyp.ParseException:
            try:
                token = ReachableObject(self.player, self.priority)
                loc, parse_result = token.parseImpl(instring, loc, doActions)
                return loc, parse_result
            except pyp.ParseException as e:
                if hasattr(e, "matches"):
                    e.__init__(instring, e.loc, self.errmsg, self, e.matches)
                else:
                    e.__init__(instring, e.loc, self.errmsg, self)
                raise e


class Command(object):
    """
    The superclass for all commands -- local or global, built-in or
    user-defined.
    """

    # Require the full name of the command to be typed--don't accept partial
    # matches.
    require_full = False

    @classmethod
    def args(cls, player):
        """
        Return the pyp pattern for this command's arguments. This
        implementation rejects any args; subclasses should override if they
        intend to accept any.
        """
        # By default, accept no arguments
        return pyp.LineEnd()

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
            args = self.args(None)
            if hasattr(args, "exprs"):
                token_list = args.exprs
            else:
                token_list = [args]
            printable_tokens = []
            for token in token_list:
                if isinstance(token, pyp.LineEnd):
                    continue
                printable_token = str(token).replace(" ", "-")
                if not isinstance(token, pyp.Optional):
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
