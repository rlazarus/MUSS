from muss import db, parser
from muss.test import common_tools
from muss.test.parser import parser_tools


class NearbyObjectTestCase(parser_tools.ParserTestCase):
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
        me = common_tools.sudo(lambda:db.Object("me", self.lobby))
        db.store(me)
        self.assert_parse(pattern, "me", me)

    def test_nearbyobject_here(self):
        pattern = parser.NearbyObject(self.player)
        self.assert_parse(pattern, "here", self.lobby)
        here = common_tools.sudo(lambda:db.Object("here", self.lobby))
        db.store(here)
        self.assert_parse(pattern, "here", here)
        # Just because this works doesn't mean you should ever do it.
