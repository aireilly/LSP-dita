import os
import tempfile
import unittest

from plugin.rootmap import discover_maps, nearest_map, to_uri


def touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").close()


class TestDiscoverMaps(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_finds_maps_recursively(self):
        touch(os.path.join(self.root, "a.ditamap"))
        touch(os.path.join(self.root, "nested", "b.ditamap"))
        self.assertEqual(len(discover_maps([self.root])), 2)

    def test_excludes_build_directories(self):
        touch(os.path.join(self.root, "keep.ditamap"))
        for excluded in ("out", "temp", "build", ".git"):
            touch(os.path.join(self.root, excluded, "skip.ditamap"))
        found = discover_maps([self.root])
        self.assertEqual([os.path.basename(p) for p in found], ["keep.ditamap"])

    def test_respects_the_limit(self):
        for i in range(10):
            touch(os.path.join(self.root, "m{}.ditamap".format(i)))
        self.assertEqual(len(discover_maps([self.root], limit=4)), 4)

    def test_ignores_non_map_files(self):
        touch(os.path.join(self.root, "topic.dita"))
        self.assertEqual(discover_maps([self.root]), [])

    def test_results_are_sorted(self):
        touch(os.path.join(self.root, "z.ditamap"))
        touch(os.path.join(self.root, "a.ditamap"))
        self.assertEqual([os.path.basename(p) for p in discover_maps([self.root])],
                         ["a.ditamap", "z.ditamap"])

    def test_no_folders_yields_nothing(self):
        self.assertEqual(discover_maps([]), [])

    def test_deduplicates_overlapping_folders(self):
        touch(os.path.join(self.root, "nested", "a.ditamap"))
        found = discover_maps([self.root, os.path.join(self.root, "nested")])
        self.assertEqual(len(found), 1)


class TestNearestMap(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_finds_map_in_same_directory(self):
        touch(os.path.join(self.root, "main.ditamap"))
        topic = os.path.join(self.root, "topic.dita")
        touch(topic)
        self.assertEqual(nearest_map(topic), os.path.join(self.root, "main.ditamap"))

    def test_walks_upwards(self):
        touch(os.path.join(self.root, "main.ditamap"))
        topic = os.path.join(self.root, "topics", "deep", "topic.dita")
        touch(topic)
        self.assertEqual(nearest_map(topic), os.path.join(self.root, "main.ditamap"))

    def test_returns_none_when_absent(self):
        topic = os.path.join(self.root, "topic.dita")
        touch(topic)
        self.assertIsNone(nearest_map(topic, stop_at=self.root))

    def test_closest_map_wins_over_higher_one(self):
        touch(os.path.join(self.root, "outer.ditamap"))
        touch(os.path.join(self.root, "sub", "inner.ditamap"))
        topic = os.path.join(self.root, "sub", "topic.dita")
        touch(topic)
        self.assertEqual(nearest_map(topic), os.path.join(self.root, "sub", "inner.ditamap"))

    def test_empty_start_file_returns_none(self):
        self.assertIsNone(nearest_map("", stop_at=self.root))


class TestToUri(unittest.TestCase):
    def test_absolute_path(self):
        self.assertEqual(to_uri("/home/user/a.ditamap"), "file:///home/user/a.ditamap")

    def test_space_is_encoded(self):
        self.assertEqual(to_uri("/home/user/my map.ditamap"),
                         "file:///home/user/my%20map.ditamap")
