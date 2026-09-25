import os
import tempfile
import unittest

from plugin.refs import Reference, all_references, parse_address, reference_at, resolve_path


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


class TestSingleQuotedAttributes(unittest.TestCase):
    """XML permits either quote style; DITA files in the wild use both."""

    def test_finds_single_quoted_href(self):
        text = "<xref href='tasks/installing.dita#install/step-3'/>"
        ref = reference_at(text, text.index("tasks"))
        self.assertIsNotNone(ref)
        self.assertEqual(ref.path, "tasks/installing.dita")
        self.assertEqual(ref.element_id, "step-3")

    def test_single_quoted_scope_external_still_declines(self):
        text = "<xref href='https://example.com' scope='external'/>"
        self.assertIsNone(reference_at(text, text.index("https")))

    def test_mixed_quote_styles_in_one_element(self):
        text = '<topicref href=\'a.dita\' copy-to="b.dita"/>'
        self.assertEqual(reference_at(text, text.index("a.dita")).path, "a.dita")
        self.assertEqual(reference_at(text, text.index("b.dita")).path, "b.dita")

    def test_double_quote_inside_single_quoted_value_is_kept(self):
        text = "<xref href='say\"what.dita'/>"
        self.assertEqual(reference_at(text, text.index("say")).path, 'say"what.dita')


class TestAllReferences(unittest.TestCase):
    """Every resolvable address in a buffer, for underlining clickable regions."""

    def test_finds_each_reference_with_its_span(self):
        text = '<topicref href="a.dita"/>\n<p conref="b.dita#t/e"/>'
        found = all_references(text)
        self.assertEqual(len(found), 2)
        (s1, e1, r1), (s2, e2, r2) = found
        self.assertEqual(text[s1:e1], "a.dita")
        self.assertEqual(r1.attribute, "href")
        self.assertEqual(text[s2:e2], "b.dita#t/e")
        self.assertEqual(r2.attribute, "conref")

    def test_spans_cover_only_the_value_not_the_quotes(self):
        text = '<xref href="a.dita"/>'
        start, end, _ = all_references(text)[0]
        self.assertEqual(text[start - 1], '"')
        self.assertEqual(text[end], '"')

    def test_skips_external_and_non_resolvable(self):
        text = (
            '<xref href="https://example.com" scope="external"/>'
            '<xref href="p.html" format="html"/>'
            '<topicref keyref="k"/>'
            '<xref href="ok.dita"/>'
        )
        found = all_references(text)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][2].path, "ok.dita")

    def test_single_quoted_values_are_found(self):
        text = "<xref href='a.dita'/>"
        self.assertEqual(len(all_references(text)), 1)

    def test_several_addresses_in_one_element(self):
        text = '<topicref href="a.dita" copy-to="b.dita"/>'
        self.assertEqual([text[s:e] for s, e, _ in all_references(text)],
                         ["a.dita", "b.dita"])

    def test_empty_buffer(self):
        self.assertEqual(all_references(""), [])

    def test_buffer_with_no_references(self):
        self.assertEqual(all_references("<p>Just text.</p>"), [])
