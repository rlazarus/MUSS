import pyparsing as pyp

from muss import parser
from muss.test.parser import parser_tools


class OneOfTestCase(parser_tools.ParserTestCase):
    def test_easy(self):
        result = object()
        token = parser.OneOf("test", {"foo": result, "bar": object()})
        self.assert_parse(token, "foo", result)

    def test_partial(self):
        result = object()
        token = parser.OneOf("test", {"foo": result, "bar": object()},
                             exact=False)
        self.assert_parse(token, "f", result)

    def test_partial_ambiguous(self):
        token = parser.OneOf("test", {"bar": object(), "baz": object()},
                             exact=False)
        self.assertRaises(parser.AmbiguityError, token.parseString, "b",
                          parseAll=True)

    def test_prefer_full(self):
        result = object()
        token = parser.OneOf("test", {"foo": result, "foobar": object()},
                             exact=False)
        self.assert_parse(token, "foo", result)

    def test_partial_but_exact(self):
        token = parser.OneOf("test", {"foo": object(), "bar": object()},
                             exact=True)
        self.assertRaises(parser.NotFoundError, token.parseString, "f",
                          parseAll=True)

    def test_notfound(self):
        self.assertRaises(parser.NotFoundError,
                          parser.OneOf("test", {"foo": object()}).parseString,
                          "bar", parseAll=True)

    def test_pattern(self):
        result = object()
        token = parser.OneOf("test",
                             {"1": object(), "12": result, "12x": object()},
                             pattern=pyp.Word(pyp.nums))
        self.assertEqual(token.parseString("12x", parseAll=False)[0], result)
