from twisted.trial import unittest
from twisted.test import proto_helpers

from muss import server, data


class LoginTestCase(unittest.TestCase):
    def assert_response(self, received, equal=None, startswith=None, endswith=None):
        """
        Send a line to the server, and assert that its response will match what we expect. Provide exactly one of the last three (keyword) args.

        Args:
            received: The line the server should simulate receiving.
            equal: Assert that the response is exactly equal to this string. (Uses assertEqual)
            startswith: Assert that the response starts with this string. (Uses assertTrue and .startswith)
            endswith: Assert that the response ends with this string. (Uses assertTrue and .endswith)
        """
        if not (equal or startswith or endswith):
            raise ValueError("No assertion")

        self.proto.dataReceived(received)
        response = self.tr.value()
        self.tr.clear()

        if equal:
            self.assertEqual(response, equal)
        elif startswith:
            self.assertTrue(response.startswith(startswith))
        elif endswith:
            self.assertTrue(response.endswith(endswith))

    def new_connection(self):
        self.proto = self.factory.buildProtocol(("127.0.0.1", 0))
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)

    def setUp(self):
        self.factory = server.WorldFactory()
        self.new_connection()

        # Monkey-patch the internal database to make these tests mutually independent.
        # Include only #0, the lobby. We'll do this differently when we have an actual database.
        self.patch(data.Database(), "_objects", {0: data.Database()._objects[0]})

    def test_greet(self):
        msg = self.tr.value()
        self.assertTrue(msg.startswith("Hello!\r\n"), msg)
        self.assertEqual(len(msg.split("\r\n")), 5, msg)

    def test_quit(self):
        self.tr.clear() # Clear out the greeting
        self.assert_response("quit\r\n", "Bye!\r\n")

    def test_create_typo(self):
        self.tr.clear() # Clear out the greeting
        self.assert_response("new\r\n", "Welcome! What username would you like?\r\n")
        self.assert_response("name\r\n", endswith="password.\r\n")
        self.assert_response("pass\r\n", endswith="again.\r\n")
        self.assert_response("wrongpass\r\n", startswith="Passwords don't match")

    def test_create_successful(self):
        self.tr.clear() # Clear out the greeting
        self.assert_response("new\r\n", "Welcome! What username would you like?\r\n")
        self.assert_response("name\r\n", endswith="password.\r\n")
        self.assert_response("pass\r\n", endswith="again.\r\n")
        self.assert_response("pass\r\n", "Hello, name!\r\n")
        self.assert_response("hello world\r\n", "<name> hello world\r\n")

    def test_login_bad_username(self):
        # Create an account
        self.proto.dataReceived("new\r\nname\r\npass\r\npass\r\n")
        self.new_connection()
        self.tr.clear()

        self.assert_response("wrongname pass\r\n", "Invalid login.\r\n")

    def test_login_bad_password(self):
        # Create an account
        self.proto.dataReceived("new\r\nname\r\npass\r\npass\r\n")
        self.new_connection()
        self.tr.clear()

        self.assert_response("name wrongpass\r\n", "Invalid login.\r\n")

    def test_login_success(self):
        # Create an account
        self.proto.dataReceived("new\r\nname\r\npass\r\npass\r\n")
        self.new_connection()
        self.tr.clear()

        self.assert_response("name pass\r\n", "Hello, name!\r\n")
        self.assert_response("hello world\r\n", "<name> hello world\r\n")
