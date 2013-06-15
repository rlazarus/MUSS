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

    def test_playername_success(self):
        parse_result = parser.PlayerName().parseString("Player", parseAll=True)
        self.assertEqual(parse_result[0], self.player)

    def test_playername_case_insensitive(self):
        parse_result = parser.PlayerName().parseString("player", parseAll=True)
        self.assertEqual(parse_result[0], self.player)
        parse_result = parser.PlayerName().parseString("PLAYER", parseAll=True)
        self.assertEqual(parse_result[0], self.player)

    def test_playername_failure_not_player(self):
        self.assertRaises(parser.NotFoundError,
                          parser.PlayerName().parseString,
                          "NotAPlayer", parseAll=True)
        self.assert_response("poke NotAPlayer",
                             'I don\'t know of a player called "NotAPlayer"')

    def test_playername_failure_invalid_name(self):
        self.assertRaises(parser.NotFoundError,
                          parser.PlayerName().parseString, "6", parseAll=True)

    def test_playername_partial(self):
        parse_result = parser.PlayerName().parseString("Players", parseAll=True)
        self.assertEqual(parse_result[0], self.neighbor)

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

    def test_objectin_whole(self):
        lobby = db._objects[0]
        name = "Player"
        parse_result = parser.ObjectIn(lobby).parseString(name, parseAll=True)
        self.assertEqual(parse_result[0], self.player)

    def test_objectin_partial(self):
        lobby = db._objects[0]
        name = "Players"
        parse_result = parser.ObjectIn(lobby).parseString(name, parseAll=True)
        self.assertEqual(parse_result[0], self.neighbor)

    def test_objectin_ambiguous(self):
        lobby = db._objects[0]
        name = "Play"
        self.assertRaises(parser.AmbiguityError,
                          parser.ObjectIn(lobby).parseString,
                          name, parseAll=True)

    def test_objectin_notfound(self):
        lobby = db._objects[0]
        name = "asdf"
        self.assert_error_message(parser.NotFoundError, "I don't know of an "
                                  "object in lobby called \"asdf\"",
                                  parser.ObjectIn(lobby).parseString,
                                  "asdf", parseAll=True)

    def test_objectin_badlocation(self):
        self.assert_error_message(TypeError, "Invalid location: foo",
                                  parser.ObjectIn, "foo")

    def test_nearbyobject_room(self):
        pattern = parser.NearbyObject(self.player)
        parse_result = pattern.parseString("lobby", parseAll=True)
        self.assertEqual(parse_result[0], self.player.location)

    def test_nearbyobject_my_success(self):
        for phrase in ["my apple", "my app"]:
            pattern = parser.NearbyObject(self.player)
            parse_result = pattern.parseString(phrase, parseAll=True)
            self.assertEqual(parse_result[0], self.objects["apple"])

        pattern = parser.NearbyObject(self.player)
        parse_result = pattern.parseString("my horse", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["horse figurine"])

        pattern = parser.NearbyObject(self.player)
        parse_result = pattern.parseString("my cat", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["inv_cat"])

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
            pattern = parser.NearbyObject(self.player)
            parse_result = pattern.parseString(item, parseAll=True)
            self.assertEqual(parse_result[0], self.objects[item])

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
            parse_result = pattern.parseString(name, parseAll=True)
            self.assertEqual(parse_result[0], self.objects[item])

        parse_result = pattern.parseString("cat", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["room_cat"])

        pattern = parser.NearbyObject(self.player, priority="inventory")
        parse_result = pattern.parseString("horse", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["horse figurine"])

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
        parse_result = pattern.parseString("PlayersNeighbor")
        self.assertEqual(parse_result[0], self.neighbor)

    def test_nearbyobject_me(self):
        pattern = parser.NearbyObject(self.player)
        parse_result = pattern.parseString("me")
        self.assertEqual(parse_result[0], self.player)

    def test_nearbyobject_objectme(self):
        pattern = parser.NearbyObject(self.player)
        me = db.Object("me", self.player.location)
        db.store(me)
        parse_result = pattern.parseString("me")
        self.assertEqual(parse_result[0], me)

    def test_nearbyobject_here(self):
        pattern = parser.NearbyObject(self.player)
        parse_result = pattern.parseString("here")
        self.assertEqual(parse_result[0], self.player.location)

    def test_nearbyobject_objecthere(self):
        pattern = parser.NearbyObject(self.player)
        here = db.Object("here", self.player.location)
        db.store(here)
        parse_result = pattern.parseString("here")
        self.assertEqual(parse_result[0], here)

    def test_combining_object_tokens(self):
        grammar = parser.ObjectIn(self.player) + pyp.Word(pyp.alphas)
        parse_result = grammar.parseString("apple pie")
        self.assertEqual(list(parse_result), [self.objects["apple"], "pie"])

    def test_reachableobject_nearby_success(self):
        pattern = parser.ReachableObject(self.player)
        for item in ["apple", "frog"]:
            parse_result = pattern.parseString(item, parseAll=True)
            self.assertEqual(parse_result[0], self.objects[item])

        parse_result = pattern.parseString("my ape", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["ape plushie"])

        parse_result = pattern.parseString("PlayersN", parseAll=True)
        self.assertEqual(parse_result[0], self.neighbor)

    def test_reachableobject_nearby_failure(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of a reachable object called "
                                  "\"asdf\"",
                                  pattern.parseString, "asdf", parseAll=True)

    def test_reachableobject_preposition_success(self):
        pattern = parser.ReachableObject(self.player)
        parse_result = pattern.parseString("cat on Player", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["inv_cat"])

        parse_result = pattern.parseString("apple in player", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["apple"])

    def test_reachableobject_preposition_failure(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of a reachable object called "
                                  "\"foo between bar\"",
                                  pattern.parseString,
                                  "foo between bar", parseAll=True)

    def test_reachableobject_preposition_player_success(self):
        pattern = parser.ReachableObject(self.player)
        parse_result = pattern.parseString("apple in playersneighbor",
                                           parseAll=True)
        self.assertEqual(parse_result[0], self.objects["neighbor_apple"])

    def test_reachableobject_preposition_player_failure(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of an object in "
                                  "PlayersNeighbor's inventory called \"asdf\"",
                                  pattern.parseString,
                                  "asdf in playersneighbor", parseAll=True)

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

    def test_reachableobject_room_success(self):
        pattern = parser.ReachableObject(self.player)
        parse_result = pattern.parseString("cat in room", parseAll=True)
        self.assertEqual(parse_result[0], self.objects["room_cat"])

    def test_reachable_object_room_failure(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of an object in lobby called "
                                  "\"cherry\"",
                                  pattern.parseString,
                                  "cherry in room", parseAll=True)

    def test_reachableobject_owner(self):
        pattern = parser.ReachableObject(self.player)
        parse_result = pattern.parseString("PlayersNeighbor's apple",
                                           parseAll=True)
        self.assertEqual(parse_result[0], self.objects["neighbor_apple"])

    def test_reachableobject_owner_failure(self):
        pattern = parser.ReachableObject(self.player)
        self.assert_error_message(parser.NotFoundError,
                                  "I don't know of an object in "
                                  "PlayersNeighbor's inventory called \"frog\"",
                                  pattern.parseString,
                                  "PlayersNeighbor's frog", parseAll=True)

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
        result = grammar.parseString("#" + str(self.player.uid))
        self.assertEqual(result.obj, self.player)
        result = grammar.parseString("#" + str(self.neighbor.uid))
        self.assertEqual(result.obj, self.neighbor)

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
        uids = {}
        uids["frog"] = self.objects["frog"].uid
        uids["apple"] = self.objects["apple"].uid
        uids["hat"] = self.objects["hat"].uid

        pattern = parser.ReachableOrUid(self.player)

        item = pattern.parseString("frog")[0]
        self.assertEqual(item, self.objects["frog"])
        item = pattern.parseString("#{}".format(uids["frog"]))[0]
        self.assertEqual(item, self.objects["frog"])

        item = pattern.parseString("apple")[0]
        self.assertEqual(item, self.objects["apple"])
        item = pattern.parseString("#{}".format(uids["apple"]))[0]
        self.assertEqual(item, self.objects["apple"])

        item = pattern.parseString("hat on frog")[0]
        self.assertEqual(item, self.objects["hat"])
        item = pattern.parseString("#{}".format(uids["hat"]))[0]
        self.assertEqual(item, self.objects["hat"])
