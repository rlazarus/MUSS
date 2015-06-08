import pyparsing as pyp

from muss import parser
from muss.test.parser import parser_tools


class SomeOfTestCase(parser_tools.ParserTestCase):
    def test_easy(self):
        result = object()
        token = parser.SomeOf("test", [("foo", result), ("bar", object())])
        self.assert_parse(token, "foo", [result])

    def test_partial(self):
        result = object()
        token = parser.SomeOf("test", [("foo", result), ("bar", object())],
                             exact=False)
        self.assert_parse(token, "f", [result])

    def test_partial_ambiguous(self):
        bar_result = object()
        baz_result = object()
        token = parser.SomeOf("test",
                              [("bar", bar_result), ("baz", baz_result)],
                              exact=False)
        self.assert_parse(token, "b", [bar_result, baz_result])

    def test_full_ambiguous(self):
        result1 = object()
        result2 = object()
        token = parser.SomeOf("test", [("foo", result1), ("foo", result2)],
                             exact=False)
        self.assert_parse(token, "foo", [result1, result2])


    def test_prefer_full(self):
        result = object()
        token = parser.SomeOf("test", [("foo", result), ("foobar", object())],
                             exact=False)
        self.assert_parse(token, "foo", [result])

    def test_prefer_full_case_insensitive(self):
        result = object()
        token = parser.SomeOf("test", [("foo", result), ("foobar", object())],
                             exact=False)
        self.assert_parse(token, "Foo", [result])

    def test_partial_but_exact(self):
        token = parser.OneOf("test", [("foo", object()), ("bar", object())],
                             exact=True)
        self.assertRaises(parser.NotFoundError, token.parseString, "f",
                          parseAll=True)

    def test_notfound(self):
        self.assertRaises(parser.NotFoundError,
                          parser.OneOf("test", [("foo", object())]).parseString,
                          "bar", parseAll=True)

    def test_pattern(self):
        result = object()
        token = parser.SomeOf(
            "test",
            [("1", object()), ("12", result), ("12x", object())],
            pattern=pyp.Word(pyp.nums))
        self.assertEqual(token.parseString("12x", parseAll=False)[0], [result])
