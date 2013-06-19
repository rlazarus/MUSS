from muss import db, parser, locks
from muss.test import common_tools


class ParserTestCase(common_tools.MUSSTestCase):
    def setUp(self):
        super(ParserTestCase, self).setUp()
        self.setup_objects()
        tricky_names = ["me you", "cup of mead", "here there",
                        "heretical thoughts"]
        # These are for confounding the me/here keywords.
        for name in tricky_names:
            with locks.authority_of(locks.SYSTEM):
                self.objects[name] = db.Object(name, self.lobby)
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
