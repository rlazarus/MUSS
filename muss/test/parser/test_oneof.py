import pyparsing as pyp

from muss import parser
from muss.test.parser import parser_tools


class OneOfTestCase(parser_tools.ParserTestCase):
    def test_easy(self):
        result = object()
        token = parser.OneOf([("foo", result), ("bar", object())])
        self.assert_parse(token, "foo", result)

    def test_partial(self):
        result = object()
        token = parser.OneOf([("foo", result), ("bar", object())], exact=False)
        self.assert_parse(token, "f", result)

    def test_partial_ambiguous(self):
        token = parser.OneOf([("bar", object()), ("baz", object())],
                             exact=False)
        self.assertRaises(parser.AmbiguityError, token.parseString, "b",
                          parseAll=True)

    def test_full_ambiguous(self):
        token = parser.OneOf([("foo", object()), ("foo", object())],
                             exact=False)
        self.assertRaises(parser.AmbiguityError, token.parseString, "foo",
                          parseAll=True)


    def test_prefer_full(self):
        result = object()
        token = parser.OneOf([("foo", result), ("foobar", object())],
                             exact=False)
        self.assert_parse(token, "foo", result)

    def test_prefer_full_case_insensitive(self):
        result = object()
        token = parser.OneOf([("foo", result), ("foobar", object())],
                             exact=False)
        self.assert_parse(token, "Foo", result)

    def test_partial_but_exact(self):
        token = parser.OneOf([("foo", object()), ("bar", object())], exact=True)
        self.assertRaises(parser.NotFoundError, token.parseString, "f",
                          parseAll=True)

    def test_notfound(self):
        self.assertRaises(parser.NotFoundError,
                          parser.OneOf([("foo", object())]).parseString,
                          "bar", parseAll=True)

    def test_pattern(self):
        result = object()
        token = parser.OneOf(
            [("1", object()), ("12", result), ("12x", object())],
            pattern=pyp.Word(pyp.nums))
        self.assertEqual(token.parseString("12x", parseAll=False)[0], result)

    def test_prefer_disambiguate(self):
        result = {"correct": True}
        wrong = {"correct": False}
        correct = lambda obj: obj["correct"]
        token = parser.OneOf([("foo", result), ("foo", wrong)], prefer=correct)
        self.assert_parse(token, "foo", result)

    def test_prefer_filter(self):
        preferred = {"correct": True}
        also_preferred = {"correct": True}
        wrong = {"correct": False}
        correct = lambda obj: obj["correct"]
        token = parser.OneOf(
            [("foo", preferred), ("foo", also_preferred), ("foo", wrong)],
            prefer=correct)
        try:
            token.parseString("foo")
            self.fail("Expected AmbiguityError")
        except parser.AmbiguityError as e:
            self.assertIn(("foo", preferred), e.matches)
            self.assertIn(("foo", also_preferred), e.matches)
            self.assertNotIn(("foo", wrong), e.matches)

    def test_prefer_unhelpful(self):
        wrong = {"correct": False}
        also_wrong = {"correct": False}
        correct = lambda obj: obj["correct"]
        token = parser.OneOf([("foo", wrong), ("foo", also_wrong)],
                             prefer=correct)
        self.assertRaises(parser.AmbiguityError, token.parseString, "foo")
