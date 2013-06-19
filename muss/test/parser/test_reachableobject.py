import pyparsing as pyp

from muss import db, parser
from muss.test.parser import parser_tools


class ReachableObjectTestCase(parser_tools.ParserTestCase):
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
