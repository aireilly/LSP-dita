import os
import tempfile
import unittest

from plugin.topics import find_fragment_offset, offset_to_row, read_topic_info, strip_markup

TWO_TOPICS = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE dita PUBLIC "-//OASIS//DTD DITA Composite//EN" "ditabase.dtd">
<dita>
  <task id="first">
    <title>First task</title>
    <taskbody>
      <steps><step id="step-1"><cmd>Do the first thing.</cmd></step></steps>
    </taskbody>
  </task>
  <task id="second">
    <title>Second task</title>
    <taskbody>
      <steps><step id="step-1"><cmd>Do the second thing.</cmd></step></steps>
    </taskbody>
  </task>
</dita>
'''


class TestFindFragmentOffset(unittest.TestCase):
    def test_topic_only(self):
        offset = find_fragment_offset(TWO_TOPICS, "second", "")
        self.assertIsNotNone(offset)
        self.assertTrue(TWO_TOPICS[offset:].startswith('<task id="second"'))

    def test_duplicate_element_id_resolves_within_addressed_topic(self):
        # Review Focus 1: both topics define step-1; the addressed one must win.
        first = find_fragment_offset(TWO_TOPICS, "first", "step-1")
        second = find_fragment_offset(TWO_TOPICS, "second", "step-1")
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertLess(first, second)
        self.assertIn("Do the second thing", TWO_TOPICS[second:second + 120])
        self.assertIn("Do the first thing", TWO_TOPICS[first:first + 120])

    def test_missing_topic_returns_none(self):
        self.assertIsNone(find_fragment_offset(TWO_TOPICS, "nope", ""))

    def test_missing_element_falls_back_to_topic(self):
        offset = find_fragment_offset(TWO_TOPICS, "first", "nope")
        self.assertIsNotNone(offset)
        self.assertTrue(TWO_TOPICS[offset:].startswith('<task id="first"'))

    def test_empty_topic_id_returns_none(self):
        self.assertIsNone(find_fragment_offset(TWO_TOPICS, "", "step-1"))

    def test_single_quoted_id_attribute(self):
        text = "<concept id='c1'><title>T</title></concept>"
        self.assertIsNotNone(find_fragment_offset(text, "c1", ""))

    def test_id_prefix_does_not_false_match(self):
        text = '<concept id="intro-long"><title>T</title></concept><concept id="intro"/>'
        offset = find_fragment_offset(text, "intro", "")
        self.assertTrue(text[offset:].startswith('<concept id="intro"/>'))


class TestOffsetToRow(unittest.TestCase):
    def test_first_line_is_row_zero(self):
        self.assertEqual(offset_to_row("abc\ndef", 1), 0)

    def test_second_line(self):
        self.assertEqual(offset_to_row("abc\ndef", 5), 1)

    def test_offset_at_newline_stays_on_that_line(self):
        self.assertEqual(offset_to_row("abc\ndef", 3), 0)


class TestStripMarkup(unittest.TestCase):
    def test_removes_nested_tags(self):
        self.assertEqual(strip_markup("Install the <ph>Operator</ph> now."),
                         "Install the Operator now.")

    def test_collapses_whitespace(self):
        self.assertEqual(strip_markup("Line one\n   line two"), "Line one line two")

    def test_decodes_common_entities(self):
        self.assertEqual(strip_markup("a &amp; b &lt;c&gt;"), "a & b <c>")

    def test_unknown_entity_is_left_alone(self):
        # Review Focus 3: an undefined entity must not raise.
        self.assertEqual(strip_markup("hard&nbsp;space"), "hard&nbsp;space")

    def test_empty_fragment(self):
        self.assertEqual(strip_markup(""), "")


class TestReadTopicInfo(unittest.TestCase):
    def _write(self, content):
        fd, path = tempfile.mkstemp(suffix=".dita")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_reads_title_and_shortdesc(self):
        path = self._write(
            '<concept id="c"><title>Installing</title>'
            '<shortdesc>Install the <ph>Operator</ph>.</shortdesc></concept>'
        )
        info = read_topic_info(path)
        self.assertEqual(info.title, "Installing")
        self.assertEqual(info.shortdesc, "Install the Operator.")

    def test_missing_shortdesc_is_empty(self):
        path = self._write('<concept id="c"><title>Only a title</title></concept>')
        info = read_topic_info(path)
        self.assertEqual(info.title, "Only a title")
        self.assertEqual(info.shortdesc, "")

    def test_undefined_entity_does_not_raise(self):
        # Review Focus 3: DITA references external DTDs; ElementTree would raise here.
        path = self._write(
            '<concept id="c"><title>A&nbsp;title</title>'
            '<shortdesc>Text with &nbsp; entity.</shortdesc></concept>'
        )
        info = read_topic_info(path)
        self.assertIn("title", info.title)

    def test_malformed_markup_does_not_raise(self):
        # Review Focus 3: an unclosed tag still yields something readable.
        path = self._write('<concept id="c"><title>Unclosed<shortdesc>Body.</shortdesc>')
        info = read_topic_info(path)
        self.assertIsNotNone(info)
        self.assertEqual(info.shortdesc, "Body.")

    def test_title_spanning_multiple_lines(self):
        path = self._write('<concept id="c"><title>A\n  wrapped\n  title</title></concept>')
        self.assertEqual(read_topic_info(path).title, "A wrapped title")

    def test_map_title_is_read(self):
        path = self._write('<map><title>My map</title><topicref href="a.dita"/></map>')
        self.assertEqual(read_topic_info(path).title, "My map")

    def test_missing_file_returns_none(self):
        self.assertIsNone(read_topic_info("/nonexistent/path/to.dita"))

    def test_reread_after_modification(self):
        path = self._write('<concept id="c"><title>Before</title></concept>')
        self.assertEqual(read_topic_info(path).title, "Before")
        os.utime(path, (0, 0))
        with open(path, "w", encoding="utf-8") as f:
            f.write('<concept id="c"><title>After</title></concept>')
        self.assertEqual(read_topic_info(path).title, "After")
