import unittest

from plugin.java import parse_java_major


class TestParseJavaMajor(unittest.TestCase):
    def test_modern_temurin(self):
        out = 'openjdk version "17.0.20.1" 2026-08-18\nOpenJDK Runtime Environment Temurin-17.0.20.1+1\n'
        self.assertEqual(parse_java_major(out), 17)

    def test_modern_two_digit(self):
        self.assertEqual(parse_java_major('openjdk version "21.0.2" 2024-01-16\n'), 21)

    def test_legacy_one_dot_eight_scheme(self):
        # Review Focus 5: a JRE reporting the pre-9 scheme must resolve to major 8.
        self.assertEqual(parse_java_major('java version "1.8.0_402"\n'), 8)

    def test_oracle_quoted_single_component(self):
        self.assertEqual(parse_java_major('java version "24"\n'), 24)

    def test_unparseable_returns_none(self):
        self.assertIsNone(parse_java_major("command not found"))

    def test_empty_returns_none(self):
        self.assertIsNone(parse_java_major(""))
