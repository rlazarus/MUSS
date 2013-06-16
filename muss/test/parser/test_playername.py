import pyparsing as pyp
from muss import parser
from muss.test import common_tools


class PlayerNameTestCase(common_tools.MUSSTestCase):
    def setUp(self):
        super(PlayerNameTestCase, self).setUp()
        self.setup_objects()

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

    def test_playername(self):
        for test_name in ["Player", "player", "PLAYER"]:
            self.assert_parse(parser.PlayerName(), test_name, self.player)
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
