import unittest

from plugin.lemminx import DITA_FILTER_PATTERN, needs_dita_filter, with_dita_filter


class TestWithDitaFilter(unittest.TestCase):
    def test_adds_filter_to_empty_list(self):
        self.assertEqual(with_dita_filter([]), [{"pattern": DITA_FILTER_PATTERN}])

    def test_preserves_existing_filters(self):
        existing = [{"pattern": "**.exsd"}]
        result = with_dita_filter(existing)
        self.assertEqual(result[0], {"pattern": "**.exsd"})
        self.assertEqual(result[-1], {"pattern": DITA_FILTER_PATTERN})

    def test_is_idempotent(self):
        once = with_dita_filter([])
        twice = with_dita_filter(once)
        self.assertEqual(once, twice)

    def test_does_not_mutate_the_input(self):
        existing = [{"pattern": "**.exsd"}]
        with_dita_filter(existing)
        self.assertEqual(existing, [{"pattern": "**.exsd"}])

    def test_handles_a_non_list_value(self):
        self.assertEqual(with_dita_filter(None), [{"pattern": DITA_FILTER_PATTERN}])

    def test_ignores_malformed_entries(self):
        result = with_dita_filter(["junk", {"pattern": "**.exsd"}])
        self.assertIn({"pattern": DITA_FILTER_PATTERN}, result)
        self.assertIn("junk", result)


class TestNeedsDitaFilter(unittest.TestCase):
    def test_true_when_absent(self):
        self.assertTrue(needs_dita_filter([{"pattern": "**.exsd"}]))

    def test_false_when_present(self):
        self.assertFalse(needs_dita_filter([{"pattern": DITA_FILTER_PATTERN}]))

    def test_true_for_empty(self):
        self.assertTrue(needs_dita_filter([]))

    def test_true_for_none(self):
        self.assertTrue(needs_dita_filter(None))


class TestFilterPattern(unittest.TestCase):
    def test_covers_every_dita_extension(self):
        for ext in (".dita", ".ditamap", ".ditaval"):
            self.assertIn(ext, DITA_FILTER_PATTERN)
