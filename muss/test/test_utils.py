from muss.utils import comma_and

from twisted.trial import unittest

class UtilsTestCase(unittest.TestCase):
    def test_comma_and_zero(self):
        self.assertEqual(comma_and([]), "")

    def test_comma_and_one(self):
        self.assertEqual(comma_and(["one"]), "one")

    def test_comma_and_two(self):
        self.assertEqual(comma_and(["one", "two"]), "one and two")

    def test_comma_and_three(self):
        self.assertEqual(comma_and(["one", "two", "three"]), "one, two, and three")

    def test_comma_and_four(self):
        self.assertEqual(comma_and(["one", "two", "three", "four"]), "one, two, three, and four")
