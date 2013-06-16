from muss import parser
from muss.test import common_tools


class CommandNameTestCase(common_tools.MUSSTestCase):
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
