import hashlib
import os
import tempfile
import unittest

from plugin.server import needs_install, verify_sha256


class TestNeedsInstall(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_true_when_jar_absent(self):
        self.assertTrue(needs_install(self.dir, "s.jar", "0.1.0"))

    def test_true_when_marker_absent(self):
        open(os.path.join(self.dir, "s.jar"), "w").close()
        self.assertTrue(needs_install(self.dir, "s.jar", "0.1.0"))

    def test_true_when_marker_disagrees(self):
        open(os.path.join(self.dir, "s.jar"), "w").close()
        with open(os.path.join(self.dir, "VERSION"), "w") as f:
            f.write("0.0.9")
        self.assertTrue(needs_install(self.dir, "s.jar", "0.1.0"))

    def test_false_when_jar_and_marker_agree(self):
        open(os.path.join(self.dir, "s.jar"), "w").close()
        with open(os.path.join(self.dir, "VERSION"), "w") as f:
            f.write("0.1.0\n")
        self.assertFalse(needs_install(self.dir, "s.jar", "0.1.0"))


class TestVerifySha256(unittest.TestCase):
    def _file_with(self, payload):
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
        return path

    def test_matching_digest(self):
        path = self._file_with(b"hello")
        self.assertTrue(verify_sha256(path, hashlib.sha256(b"hello").hexdigest()))

    def test_mismatched_digest(self):
        path = self._file_with(b"hello")
        self.assertFalse(verify_sha256(path, "0" * 64))

    def test_case_insensitive(self):
        path = self._file_with(b"hello")
        self.assertTrue(verify_sha256(path, hashlib.sha256(b"hello").hexdigest().upper()))
