import unittest

from plugin.lemminx import DITA_FILTER, DITA_FILTER_PATTERN, needs_dita_filter, with_dita_filter


class TestDitaFilterShape(unittest.TestCase):
    """A pattern alone relaxes nothing.

    LSP-lemminx's own defaults pair every pattern with the relaxations it
    wants, for example {"pattern": "**.exsd", "noGrammar": "ignore",
    "schema": {"enabled": "never"}}. An entry carrying only a pattern is
    matched and then changes no behaviour.
    """

    def test_covers_every_dita_extension(self):
        for ext in (".dita", ".ditamap", ".ditaval"):
            self.assertIn(ext, DITA_FILTER_PATTERN)

    def test_turns_validation_off_outright(self):
        # The decisive switch. "schema based validation" is ambiguous about
        # whether a DTD counts, and DITA validates against a DTD.
        self.assertIs(DITA_FILTER["enabled"], False)

    def test_silences_the_missing_grammar_hint(self):
        self.assertEqual(DITA_FILTER["noGrammar"], "ignore")

    def test_turns_grammar_validation_off(self):
        self.assertEqual(DITA_FILTER["schema"], {"enabled": "never"})

    def test_carries_the_pattern(self):
        self.assertEqual(DITA_FILTER["pattern"], DITA_FILTER_PATTERN)


class TestWithDitaFilter(unittest.TestCase):
    def test_adds_filter_to_empty_list(self):
        self.assertEqual(with_dita_filter([]), [DITA_FILTER])

    def test_preserves_existing_filters(self):
        result = with_dita_filter([{"pattern": "**.exsd"}])
        self.assertEqual(result[0], {"pattern": "**.exsd"})
        self.assertEqual(result[-1], DITA_FILTER)

    def test_upgrades_a_pattern_only_entry(self):
        # An earlier version of this package wrote the bare pattern, which
        # matched DITA files and then relaxed nothing.
        result = with_dita_filter([{"pattern": DITA_FILTER_PATTERN}])
        self.assertEqual(result, [DITA_FILTER])

    def test_upgrade_keeps_other_entries_in_place(self):
        result = with_dita_filter([
            {"pattern": "**.exsd"},
            {"pattern": DITA_FILTER_PATTERN},
        ])
        self.assertEqual(result, [{"pattern": "**.exsd"}, DITA_FILTER])

    def test_is_idempotent(self):
        once = with_dita_filter([])
        self.assertEqual(with_dita_filter(once), once)

    def test_does_not_mutate_the_input(self):
        existing = [{"pattern": "**.exsd"}]
        with_dita_filter(existing)
        self.assertEqual(existing, [{"pattern": "**.exsd"}])

    def test_handles_a_non_list_value(self):
        self.assertEqual(with_dita_filter(None), [DITA_FILTER])

    def test_ignores_malformed_entries(self):
        result = with_dita_filter(["junk", {"pattern": "**.exsd"}])
        self.assertIn(DITA_FILTER, result)
        self.assertIn("junk", result)


class TestNeedsDitaFilter(unittest.TestCase):
    def test_true_when_absent(self):
        self.assertTrue(needs_dita_filter([{"pattern": "**.exsd"}]))

    def test_true_for_a_pattern_only_entry(self):
        self.assertTrue(needs_dita_filter([{"pattern": DITA_FILTER_PATTERN}]))

    def test_false_when_fully_present(self):
        self.assertFalse(needs_dita_filter([DITA_FILTER]))

    def test_true_for_empty(self):
        self.assertTrue(needs_dita_filter([]))

    def test_true_for_none(self):
        self.assertTrue(needs_dita_filter(None))
