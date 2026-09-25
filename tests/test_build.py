import os
import re
import unittest

from plugin.build import RESULT_FILE_REGEX, build_argv, count_problems, resolve_output

# Captured verbatim from DITA-OT 4.3.1 building a map with a missing topicref
# target and a broken xref. Paths shortened; the line shapes are unchanged.
REAL_OUTPUT = [
    "Error: [DOTX008E] The resource 'file:/tmp/p/missing.dita' cannot be loaded. Make sure it exists.",
    "Warning: file:/tmp/p/test.ditamap:6:34: [DOTX023W]: Unable to retrieve navtitle from target: 'x.dita'. ",
    "Error: file:/tmp/p/good.dita:7:39: [DOTX031E]: The 'y.dita' resource is not available. ",
    "File file:/tmp/p/missing.dita not found",
    "BUILD SUCCESSFUL",
]


class TestBuildArgv(unittest.TestCase):
    def test_basic_invocation(self):
        self.assertEqual(
            build_argv("/usr/bin/dita", "/p/m.ditamap", "html5", "/p/out", []),
            ["/usr/bin/dita", "-i", "/p/m.ditamap", "-f", "html5", "-o", "/p/out"],
        )

    def test_extra_args_are_appended(self):
        argv = build_argv("dita", "/p/m.ditamap", "pdf", "/p/out", ["--args.draft=yes"])
        self.assertEqual(argv[-1], "--args.draft=yes")

    def test_transtype_is_used(self):
        self.assertIn("markdown", build_argv("dita", "/p/m.ditamap", "markdown", "/p/out", []))

    def test_extra_args_are_copied_not_aliased(self):
        extra = ["--a"]
        argv = build_argv("dita", "/m.ditamap", "html5", "/out", extra)
        extra.append("--b")
        self.assertNotIn("--b", argv)


class TestResolveOutput(unittest.TestCase):
    def test_relative_output_resolves_against_map_dir(self):
        self.assertEqual(resolve_output("/p/maps/m.ditamap", "out"),
                         os.path.normpath("/p/maps/out"))

    def test_absolute_output_is_kept(self):
        self.assertEqual(resolve_output("/p/maps/m.ditamap", "/tmp/elsewhere"),
                         os.path.normpath("/tmp/elsewhere"))

    def test_empty_output_defaults_to_out(self):
        self.assertEqual(resolve_output("/p/maps/m.ditamap", ""),
                         os.path.normpath("/p/maps/out"))

    def test_nested_relative_output(self):
        self.assertEqual(resolve_output("/p/m.ditamap", "build/html"),
                         os.path.normpath("/p/build/html"))


class TestResultFileRegex(unittest.TestCase):
    def setUp(self):
        self.pattern = re.compile(RESULT_FILE_REGEX)

    def test_matches_positional_error(self):
        match = self.pattern.match(REAL_OUTPUT[2])
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "/tmp/p/good.dita")
        self.assertEqual(match.group(2), "7")
        self.assertEqual(match.group(3), "39")

    def test_matches_positional_warning(self):
        match = self.pattern.match(REAL_OUTPUT[1])
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "/tmp/p/test.ditamap")
        self.assertEqual(match.group(2), "6")

    def test_captures_the_message(self):
        match = self.pattern.match(REAL_OUTPUT[2])
        self.assertIn("resource is not available", match.group(4))

    def test_does_not_match_plain_success_line(self):
        self.assertIsNone(self.pattern.match("BUILD SUCCESSFUL"))

    def test_does_not_match_non_positional_error(self):
        self.assertIsNone(self.pattern.match(REAL_OUTPUT[0]))

    def test_does_not_match_the_file_not_found_line(self):
        self.assertIsNone(self.pattern.match(REAL_OUTPUT[3]))


class TestCountProblems(unittest.TestCase):
    def test_counts_errors_and_warnings(self):
        # Review Focus 4: the non-positional DOTX008E line must be counted too,
        # because DITA-OT exits 0 and the count is the only signal of failure.
        self.assertEqual(count_problems(REAL_OUTPUT), (2, 1))

    def test_empty_output(self):
        self.assertEqual(count_problems([]), (0, 0))

    def test_ignores_the_word_error_mid_sentence(self):
        self.assertEqual(count_problems(["this line mentions an error in passing"]), (0, 0))

    def test_counts_fatal_as_an_error(self):
        self.assertEqual(count_problems(["Fatal: something collapsed"]), (1, 0))

    def test_tolerates_leading_whitespace(self):
        self.assertEqual(count_problems(["   Error: indented"]), (1, 0))
