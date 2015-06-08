import pyparsing as pyp

from muss import parser, utils
from muss.test.parser import parser_tools


class ParserMiscTestCase(parser_tools.ParserTestCase):
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

    def test_combining_object_tokens(self):
        grammar = parser.ObjectIn(self.player) + pyp.Word(pyp.alphas)
        parse_result = grammar.parseString("apple pie")
        self.assertEqual(list(parse_result), [self.objects["apple"], "pie"])

    def test_combining_object_tokens_partial(self):
        grammar = parser.ObjectIn(self.player) + pyp.Word(pyp.alphas)
        parse_result = grammar.parseString("app pie")
        self.assertEqual(list(parse_result), [self.objects["apple"], "pie"])

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
