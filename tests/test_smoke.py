import unittest


class TestPackageImportable(unittest.TestCase):
    def test_plugin_is_a_regular_package(self):
        # __file__ is set only for a regular package with __init__.py.
        # A PEP 420 namespace package would import but leave __file__ as None.
        import plugin
        self.assertIsNotNone(plugin.__file__)
