import mock
from twisted.trial import unittest

from muss import server


class NetworkTestCase(unittest.TestCase):
    def setUp(self):
        self.proto = server.LineTelnetProtocol()
        self.proto.lineReceived = mock.MagicMock()

    def test_complete(self):
        self.proto.dataReceived("one\r\n")
        self.proto.lineReceived.assert_called_once_with("one")

    def test_incomplete(self):
        self.proto.dataReceived("on")
        self.assertEqual(self.proto.lineReceived.call_count, 0)
        self.proto.dataReceived("e\r\n")
        self.proto.lineReceived.assert_called_once_with("one")

    def test_double(self):
        self.proto.dataReceived("one\r\ntwo\r\n")
        calls = [mock.call("one"), mock.call("two")]
        self.proto.lineReceived.assert_has_calls(calls)
        self.assertEqual(self.proto.lineReceived.call_count, 2)

    def test_double_incomplete(self):
        self.proto.dataReceived("one\r\ntw")
        self.proto.lineReceived.assert_called_once_with("one")
        self.proto.dataReceived("o\r\n")
        calls = [mock.call("one"), mock.call("two")]
        self.proto.lineReceived.assert_has_calls(calls)
        self.assertEqual(self.proto.lineReceived.call_count, 2)

    def test_stagger(self):
        self.proto.dataReceived("on")
        self.assertEqual(self.proto.lineReceived.call_count, 0)
        self.proto.dataReceived("e\r\ntw")
        self.proto.lineReceived.assert_called_once_with("one")
        self.proto.dataReceived("o\r\nthr")
        calls = [mock.call("one"), mock.call("two")]
        self.proto.lineReceived.assert_has_calls(calls)
        self.assertEqual(self.proto.lineReceived.call_count, 2)
