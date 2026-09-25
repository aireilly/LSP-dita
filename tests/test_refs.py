import os
import tempfile
import unittest

from plugin.refs import Reference, parse_address, reference_at, resolve_path


class TestParseAddress(unittest.TestCase):
    def test_path_only(self):
        self.assertEqual(parse_address("tasks/installing.dita"), ("tasks/installing.dita", "", ""))

    def test_path_and_topic(self):
        self.assertEqual(parse_address("a.dita#topic-id"), ("a.dita", "topic-id", ""))

    def test_path_topic_and_element(self):
        self.assertEqual(parse_address("a.dita#topic-id/step-3"), ("a.dita", "topic-id", "step-3"))

    def test_same_file_fragment(self):
        self.assertEqual(parse_address("#topic-id/step-3"), ("", "topic-id", "step-3"))

    def test_whitespace_is_stripped(self):
        self.assertEqual(parse_address("  a.dita#t  "), ("a.dita", "t", ""))


class TestReferenceAt(unittest.TestCase):
    def test_finds_href(self):
        text = '<xref href="tasks/installing.dita#install/step-3"/>'
        ref = reference_at(text, text.index("tasks"))
        self.assertIsNotNone(ref)
        self.assertEqual(ref.attribute, "href")
        self.assertEqual(ref.path, "tasks/installing.dita")
        self.assertEqual(ref.topic_id, "install")
        self.assertEqual(ref.element_id, "step-3")

    def test_finds_conref(self):
        text = '<p conref="shared.dita#warnings/reboot"/>'
        ref = reference_at(text, text.index("shared"))
        self.assertEqual(ref.attribute, "conref")
        self.assertEqual(ref.path, "shared.dita")

    def test_finds_conrefend(self):
        text = '<p conref="a.dita#t/one" conrefend="a.dita#t/three"/>'
        ref = reference_at(text, text.index("a.dita#t/three"))
        self.assertEqual(ref.attribute, "conrefend")
        self.assertEqual(ref.element_id, "three")

    def test_finds_copy_to(self):
        text = '<topicref href="a.dita" copy-to="b.dita"/>'
        ref = reference_at(text, text.index("b.dita"))
        self.assertEqual(ref.attribute, "copy-to")

    def test_declines_non_resolvable_attribute(self):
        text = '<topicref keyref="some-key" navtitle="Title"/>'
        self.assertIsNone(reference_at(text, text.index("some-key")))

    def test_declines_scope_external(self):
        text = '<xref href="https://example.com" scope="external"/>'
        self.assertIsNone(reference_at(text, text.index("https")))

    def test_declines_format_html(self):
        text = '<xref href="page.html" format="html"/>'
        self.assertIsNone(reference_at(text, text.index("page.html")))

    def test_declines_uri_scheme(self):
        text = '<xref href="mailto:docs@example.com"/>'
        self.assertIsNone(reference_at(text, text.index("mailto")))

    def test_declines_offset_outside_any_value(self):
        text = '<xref href="a.dita"/>'
        self.assertIsNone(reference_at(text, text.index("<xref")))

    def test_handles_multiline_element(self):
        text = '<topicref\n    href="tasks/a.dita"\n    scope="local"/>'
        ref = reference_at(text, text.index("tasks"))
        self.assertEqual(ref.path, "tasks/a.dita")

    def test_picks_the_value_under_the_offset_not_the_first(self):
        text = '<topicref href="first.dita" copy-to="second.dita"/>'
        ref = reference_at(text, text.index("second.dita"))
        self.assertEqual(ref.path, "second.dita")

    def test_declines_empty_value(self):
        text = '<xref href=""/>'
        self.assertIsNone(reference_at(text, text.index('""') + 1))

    def test_offset_inside_a_later_element_uses_that_element(self):
        text = '<p href="a.dita"/>\n<p conref="b.dita#t"/>'
        ref = reference_at(text, text.index("b.dita"))
        self.assertEqual(ref.path, "b.dita")
        self.assertEqual(ref.attribute, "conref")


class TestResolvePath(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "tasks"), exist_ok=True)
        os.makedirs(os.path.join(self.root, "maps"), exist_ok=True)
        self.current = os.path.join(self.root, "maps", "main.ditamap")

    def test_resolves_relative_to_current_file(self):
        ref = Reference(raw="../tasks/a.dita", path="../tasks/a.dita",
                        topic_id="", element_id="", attribute="href")
        self.assertEqual(resolve_path(ref, self.current),
                         os.path.join(self.root, "tasks", "a.dita"))

    def test_same_file_fragment_resolves_to_current_file(self):
        ref = Reference(raw="#t/e", path="", topic_id="t", element_id="e", attribute="href")
        self.assertEqual(resolve_path(ref, self.current), self.current)

    def test_normalises_backslashes(self):
        # Review Focus 2: an authoring slip using Windows separators still resolves.
        ref = Reference(raw="..\\tasks\\a.dita", path="..\\tasks\\a.dita",
                        topic_id="", element_id="", attribute="href")
        self.assertEqual(resolve_path(ref, self.current),
                         os.path.join(self.root, "tasks", "a.dita"))

    def test_traversal_is_normalised_not_escaped(self):
        # Review Focus 2: `..` collapses via normpath, yielding a clean absolute path.
        ref = Reference(raw="../../x.dita", path="../../x.dita",
                        topic_id="", element_id="", attribute="href")
        resolved = resolve_path(ref, self.current)
        self.assertEqual(resolved, os.path.normpath(os.path.join(self.root, "..", "x.dita")))
        self.assertNotIn("..", resolved)

    def test_returns_none_without_a_current_file(self):
        ref = Reference(raw="a.dita", path="a.dita", topic_id="", element_id="", attribute="href")
        self.assertIsNone(resolve_path(ref, ""))

    def test_percent_encoded_space_is_decoded(self):
        ref = Reference(raw="my%20topic.dita", path="my%20topic.dita",
                        topic_id="", element_id="", attribute="href")
        self.assertEqual(resolve_path(ref, self.current),
                         os.path.join(self.root, "maps", "my topic.dita"))
