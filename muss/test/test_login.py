from twisted.test import proto_helpers

from muss import server, db
from muss.test import common_tools


class LoginTestCase(common_tools.MUSSTestCase):
    def assert_response(self, received, equal=None, startswith=None,
                        endswith=None):
        """
        Send a line to the server, and assert that its response will match what
        we expect. Provide exactly one of the last three (keyword) args.

        Args:
            received: The line the server should simulate receiving.
            equal: Assert that the response is exactly equal to this string.
                (Uses assertEqual)
            startswith: Assert that the response starts with this string. (Uses
                assertTrue and .startswith)
            endswith: Assert that the response ends with this string. (Uses
                assertTrue and .endswith)
        """
        if equal is None and startswith is None and endswith is None:
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
        super(LoginTestCase, self).setUp()
        self.factory = server.WorldFactory()
        self.new_connection()

    def test_greet(self):
        msg = self.tr.value()
        self.assertTrue(msg.startswith("Hello!\r\n"), msg)
        self.assertEqual(len(msg.split("\r\n")), 5, msg)

    def test_quit(self):
        self.tr.clear()  # Clear out the greeting
        self.assert_response("quit\r\n", "Bye!\r\n")

    def test_create_typo(self):
        self.tr.clear()  # Clear out the greeting
        self.assert_response("new\r\n",
                             "Welcome! What username would you like?\r\n")
        self.assert_response("name\r\n", endswith="password.\r\n")
        self.assert_response("pass\r\n", endswith="again.\r\n")
        self.assert_response("wrongpass\r\n",
                             startswith="Passwords don't match")

    def test_create_successful(self):
        self.tr.clear()  # Clear out the greeting
        self.assert_response("new\r\n",
                             "Welcome! What username would you like?\r\n")
        self.assert_response("name\r\n", endswith="password.\r\n")
        self.assert_response("pass\r\n", endswith="again.\r\n")
        self.assert_response("pass\r\n", startswith="Hello, name!\r\n")
        self.assert_response("say hello world\r\n",
                             startswith='You say, "hello world"\r\n')

    def test_create_cancel(self):
        self.tr.clear()  # Clear out the greeting
        self.assert_response("new\r\n",
                             "Welcome! What username would you like?\r\n")
        self.proto.dataReceived("cancel\r\n")
        self.test_greet()

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

        self.assert_response("name pass\r\n", startswith="Hello, name!\r\n\r\n")

    def test_login_case_insensitivity(self):
        self.proto.dataReceived("new\r\nNAME\r\npass\r\npass\r\n")
        self.new_connection()
        self.tr.clear()

        self.assert_response("name pass\r\n", startswith="Hello, NAME!\r\n\r\n")

    def test_connected_attr(self):
        self.proto.dataReceived("new\r\nname\r\npass\r\npass\r\n")
        self.proto.connectionLost(reason=None)
        self.new_connection()
        self.tr.clear()

        player = db.find(lambda x: x.name == "name")

        self.assertTrue(not player.connected)
        self.assert_response("name pass\r\n", startswith="Hello, name!\r\n\r\n")
        self.assertTrue(player.connected)

        self.proto.dataReceived("quit\r\n")
        self.assertTrue(player.connected)
