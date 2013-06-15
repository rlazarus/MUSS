import pyparsing as pyp
from twisted.python import failure

from muss import db, parser, utils
from muss.test import common_tools


class ParserTestCase(common_tools.MUSSTestCase):
    def setUp(self):
        super(ParserTestCase, self).setUp()
        self.setup_objects()
        tricky_names = ["me and you", "cup of mead", "here and there",
                        "heretical thoughts"]
        # These are for confounding the me/here keywords.
        for name in tricky_names:
            self.objects[name] = db.Object(name)
            db.store(self.objects[name])

    def assert_parse(self, token, string, result):
        parse_result = token.parseString(string, parseAll=True)
        self.assertEqual(parse_result[0], result)

    def assert_error_message(self, desired_exception, desired_message,
                             function_call, *args, **kwargs):
        """
        Wrapper for assertRaises which verifies both the exception type and the
        error message--e.verbose() for any exception extending MatchError, or
        str(e) for any other exception.
        """
        exception = self.assertRaises(desired_exception, function_call,
                                      *args, **kwargs)
        if isinstance(exception, parser.MatchError):
            self.assertEqual(exception.verbose(), desired_message)
        else:
            self.assertEqual(str(exception), desired_message)

    def test_commandname_success(self):
        from muss.commands.help import Help
        from muss.commands.social import Chat
        from muss.commands.test import Poke
        for command_tuple in [("poke", Poke), ("help", Help), ("chat", Chat)]:
            name, command = command_tuple
            pattern = parser.CommandName()("command")
            parse_result = pattern.parseString(name, parseAll=True)
            self.assertEqual(parse_result["command"], command_tuple)

    def test_commandname_notfound(self):
        self.assertRaises(parser.NotFoundError,
                          parser.CommandName().parseString,
                          "noncommand", parseAll=True)
        self.assert_response("usage notacommand",
                             'I don\'t know of a command called "notacommand"')

    def test_commandname_ambiguous(self):
        self.assertRaises(parser.AmbiguityError,
                          parser.CommandName().parseString,
                          "test", parseAll=True)

    def test_commandname_ambiguity(self):
        self.assert_response("usage test",
                             'I don\'t know which command called "test" you '
                             'mean.')
        self.assert_response("usage foo",
                             "Which command do you mean? (foobar, foobaz)")

    def test_playername(self):
        self.assert_parse(parser.PlayerName(), "Player", self.player)
        self.assert_parse(parser.PlayerName(), "player", self.player)
        self.assert_parse(parser.PlayerName(), "PLAYER", self.player)
        self.assert_parse(parser.PlayerName(), "playersn", self.neighbor)

    def test_playername_failure_not_player(self):
        self.assertRaises(parser.NotFoundError,
                          parser.PlayerName().parseString,
                          "NotAPlayer", parseAll=True)
        self.assert_response("poke NotAPlayer",
                             'I don\'t know of a player called "NotAPlayer"')

    def test_playername_failure_invalid_name(self):
        self.assertRaises(parser.NotFoundError,
                          parser.PlayerName().parseString, "6", parseAll=True)

    def test_playername_ambiguous(self):
        self.assertRaises(parser.AmbiguityError,
                          parser.PlayerName().parseString,
                          "Play", parseAll=True)
        self.assert_response("poke play",
                             "Which player do you mean? (Player, "
                             "PlayersNeighbor)")

    def test_combining_playername(self):
        grammar = parser.PlayerName() + pyp.Word(pyp.alphas)
        parse_result = grammar.parseString("Player foo", parseAll=True)
        self.assertEqual(list(parse_result), [self.player, "foo"])

    def test_article_success(self):
        for word in ["a", "an", "the", "A", "AN", "THE"]:
            parse_result = parser.Article.parseString(word, parseAll=True)
            self.assertEqual(parse_result[0], word.lower())

    def test_article_failure(self):
        self.assertRaises(pyp.ParseException,
                          parser.Article.parseString, "foo", parseAll=True)

    def test_objectname_success(self):
        for name in ["apple", "a", "frog", "big frog", "them", "anniversary"]:
            for phrase in [name, "the " + name, "a " + name, "an " + name]:
                pattern = parser.ObjectName
                parse_result = pattern.parseString(phrase, parseAll=True)
                matched_name = " ".join(parse_result)
                self.assertEqual(matched_name, name)

    def test_objectname_failure(self):
        for name in ["\r\n", "", "\t", ""]:
            self.assertRaises(pyp.ParseException,
                              parser.ObjectName.parseString,
                              name, parseAll=True)

    def test_objectin(self):
        self.assert_parse(parser.ObjectIn(self.lobby), "Player", self.player)
        self.assert_parse(parser.ObjectIn(self.lobby), "Players", self.neighbor)

    def test_objectin_ambiguous(self):
        self.assertRaises(parser.AmbiguityError,
                          parser.ObjectIn(self.lobby).parseString,
                          "Play", parseAll=True)

    def test_objectin_notfound(self):
        self.assert_error_message(parser.NotFoundError, "I don't know of an "
                                  "object in lobby called \"asdf\"",
                                  parser.ObjectIn(self.lobby).parseString,
                                  "asdf", parseAll=True)

    def test_objectin_badlocation(self):
        self.assert_error_message(TypeError, "Invalid location: foo",
                                  parser.ObjectIn, "foo")

    def test_nearbyobject_room(self):
        self.assert_parse(parser.NearbyObject(self.player), "lobby", self.lobby)

    def test_nearbyobject_my_success(self):
        near_player = parser.NearbyObject(self.player)
        for phrase in ["my apple", "my app"]:
            self.assert_parse(near_player, phrase, self.objects["apple"])
        self.assert_parse(near_player, "my horse",
                          self.objects["horse figurine"])
        self.assert_parse(near_player, "my cat", self.objects["inv_cat"])

    def test_nearbyobject_my_ambiguous(self):
        self.assertRaises(parser.AmbiguityError,
                          parser.NearbyObject(self.player).parseString,
                          "my ap", parseAll=True)

    def test_nearbyobject_my_notfound(self):
        for item in ["ant", "frog", "asdf"]:
            pattern = parser.NearbyObject(self.player)
            self.assert_error_message(parser.NotFoundError,
                                      "I don't know of an object in your "
                                      "inventory called \"{}\"".format(item),
                                      pattern.parseString,
                                      "my " + item, parseAll=True)

    def test_nearbyobject_nopriority_success(self):
        for item in ["ant", "frog", "apple", "ape plushie"]:
            self.assert_parse(parser.NearbyObject(self.player), item,
                              self.objects[item])

    def test_nearbyobject_nopriority_ambiguous(self):
        for item in ["a", "cat", "h"]:
            self.assertRaises(parser.AmbiguityError,
                              parser.NearbyObject(self.player).parseString,
                              item, parseAll=True)

    def test_nearbyobject_nopriority_notfound(self):
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of a nearby object called "
                                  "\"asdf\"",
                                  parser.NearbyObject(self.player).parseString,
                                  "asdf", parseAll=True)

    def test_nearbyobject_priority_success(self):
        items = [("an", "ant"), ("horse", "horse"), ("ho", "horse"),
                 ("cher", "cherry"), ("cheese", "cheese")]
        pattern = parser.NearbyObject(self.player, priority="room")

        for name, item in items:
            self.assert_parse(pattern, item, self.objects[item])
        self.assert_parse(pattern, "cat", self.objects["room_cat"])

        pattern = parser.NearbyObject(self.player, priority="inventory")
        self.assert_parse(pattern, "cat", self.objects["inv_cat"])

    def test_nearbyobject_priority_ambiguous(self):
        pattern = parser.NearbyObject(self.player, priority="room")
        self.assertRaises(parser.AmbiguityError,
                          pattern.parseString, "f", parseAll=True)
        self.assertRaises(parser.AmbiguityError, pattern.parseString,
                          "ch", parseAll=True)
        e = self.assertRaises(parser.AmbiguityError, pattern.parseString,
                              "a", parseAll=True)
        a_names = ["abacus", "ant"]
        a_matches = [(i, self.objects[i]) for i in a_names]
        self.assertEqual(sorted(e.matches), sorted(a_matches))

    def test_nearbyobject_priority_notfound(self):
        pattern = parser.NearbyObject(self.player, priority="inventory")
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of a nearby object called "
                                  "\"asdf\"",
                                  pattern.parseString, "asdf", parseAll=True)

    def test_nearbyobject_priority_badpriority(self):
        self.assertRaises(ValueError,
                          parser.NearbyObject, self.player, priority="foo")

    def test_nearbyobject_player(self):
        pattern = parser.NearbyObject(self.player)
        self.assert_parse(pattern, "PlayersNeighbor", self.neighbor)

    def test_nearbyobject_me(self):
        pattern = parser.NearbyObject(self.player)
        self.assert_parse(pattern, "me", self.player)
        me = db.Object("me", self.lobby)
        db.store(me)
        self.assert_parse(pattern, "me", me)

    def test_nearbyobject_here(self):
        pattern = parser.NearbyObject(self.player)
        self.assert_parse(pattern, "here", self.lobby)
        here = db.Object("here", self.lobby)
        db.store(here)
        self.assert_parse(pattern, "here", here)
        # Just because this works doesn't mean you should ever do it.

    def test_combining_object_tokens(self):
        grammar = parser.ObjectIn(self.player) + pyp.Word(pyp.alphas)
        parse_result = grammar.parseString("apple pie")
        self.assertEqual(list(parse_result), [self.objects["apple"], "pie"])

    def test_reachableobject_nearby_success(self):
        pattern = parser.ReachableObject(self.player)
        for item in ["apple", "frog"]:
            self.assert_parse(pattern, item, self.objects[item])
        self.assert_parse(pattern, "my ape", self.objects["ape plushie"])

    def test_reachableobject_nearby_failure(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of a reachable object called "
                                  "\"asdf\"",
                                  pattern.parseString, "asdf", parseAll=True)

    def test_reachableobject_simple_success(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_parse(pattern, "cat on Player", self.objects["inv_cat"])
        self.assert_parse(pattern, "apple in Player", self.objects["apple"])
        self.assert_parse(pattern, "cat in room", self.objects["room_cat"])
        self.assert_parse(pattern, "apple in playersneighbor",
                          self.objects["neighbor_apple"])
        self.assert_parse(pattern, "PlayersNeighbor's apple",
                          self.objects["neighbor_apple"])

    def test_reachableobject_preposition_failure(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of a reachable object called "
                                  "\"foo between bar\"",
                                  pattern.parseString,
                                  "foo between bar", parseAll=True)

    def test_reachableobject_preposition_player_failure(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of an object in "
                                  "PlayersNeighbor's inventory called \"asdf\"",
                                  pattern.parseString,
                                  "asdf in playersneighbor", parseAll=True)

    def test_reachable_object_room_failure(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of an object in lobby called "
                                  "\"cherry\"",
                                  pattern.parseString,
                                  "cherry in room", parseAll=True)

    def test_reachableobject_owner_failure(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of an object in "
                                  "PlayersNeighbor's inventory called \"frog\"",
                                  pattern.parseString,
                                  "PlayersNeighbor's frog", parseAll=True)

    def test_reachableobject_combining_success(self):
        grammar = (parser.ReachableObject(self.player)("first") +
                   pyp.CaselessKeyword("and") +
                   parser.ReachableObject(self.player)("second"))
        parse_result = grammar.parseString("apple in player and hat on frog",
                                           parseAll=True)
        self.assertEqual(parse_result["first"], self.objects["apple"])
        self.assertEqual(parse_result["second"], self.objects["hat"])
        parse_result = grammar.parseString("hat on frog and Fodor's",
                                           parseAll=True)
        self.assertEqual(parse_result["first"], self.objects["hat"])
        self.assertEqual(parse_result["second"], self.objects["Fodor's Guide"])

    def test_reachableobject_combining_failure(self):
        grammar = (parser.ReachableObject(self.player)("first") +
                   pyp.CaselessKeyword("and") +
                   parser.ReachableObject(self.player)("second"))
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of an object in frog called "
                                  "\"apple and hat\"",
                                  grammar.parseString,
                                  "apple and hat on frog", parseAll=True)

    def test_reachableobject_combining_owner(self):
        grammar = (parser.ReachableObject(self.player)("first") +
                   pyp.CaselessKeyword("and") +
                   parser.ReachableObject(self.player)("second"))
        parse_result = grammar.parseString("my apple and PlayersN's apple",
                                           parseAll=True)
        self.assertEqual(parse_result["first"], self.objects["apple"])
        self.assertEqual(parse_result["second"], self.objects["neighbor_apple"])
        parse_result = grammar.parseString("PlayersN's apple and frog in room",
                                           parseAll=True)
        self.assertEqual(parse_result["first"], self.objects["neighbor_apple"])
        self.assertEqual(parse_result["second"], self.objects["frog"])

    def test_objectuid_success(self):
        grammar = parser.ObjectUid()("obj")
        for player in [self.player, self.neighbor]:
            self.assert_parse(grammar, "#"+str(player.uid), player)

    def test_objectuid_bad_uid_failure(self):
        self.assert_error_message(parser.NoSuchUidError,
                                  "There is no object #9999.",
                                  parser.ObjectUid().parseString, "#9999")

    def test_objectuid_non_numeric_failure(self):
        non_uids = ["asdf", "#asdf", "#12e", "123"]
        for non_uid in non_uids:
            self.assert_response("whatis {}".format(non_uid),
                                 "(Try \"help whatis\" for more help.)"
                                 .format(non_uid))

    def test_multi_word_matching(self):
        perfect, partial = utils.find_by_name("plushie", self.objects.values(),
                                              attributes=["name"])
        self.assertEqual(partial[0],
                         ("ape plushie", self.objects["ape plushie"]))
        name, item = utils.find_one("guide", self.objects.values(),
                                    attributes=["name"])
        self.assertEqual(name, "Fodor's Guide")
        self.assertEqual(item, self.objects["Fodor's Guide"])

    def test_require_full(self):
        from muss.commands.building import Destroy
        try:
            parse_result = parser.CommandName()("command").parseString("d")
            self.assertNotEqual(parse_result["command"][1], Destroy)
            # ^-- if there's only one other command starting with d
            # v-- if there's more than one
        except parser.AmbiguityError as e:
            self.assertNotIn(Destroy, [b for a, b in e.matches])
        except:
            self.fail()
        # Error message tests for this are in test_handler.py.

    def test_reachableoruid(self):
        pattern = parser.ReachableOrUid(self.player)
        for name in ["frog", "apple"]:
            obj = self.objects[name]
            self.assert_parse(pattern, name, obj)
            self.assert_parse(pattern, "#"+str(obj.uid), obj)
        obj = self.objects["hat"]
        self.assert_parse(pattern, "hat on frog", obj)
        self.assert_parse(pattern, "#"+str(obj.uid), obj)
