"""Fixture for tests/tools/test_run_required_backends.py (not a test module: run_all_checks collects test_*.py only):
two tests that skip while the backend json is importable, one because it 'needs json', one meant for its absence."""
import unittest


class Fixture(unittest.TestCase):
    def test_needs_the_backend(self):
        self.skipTest("json not installed")

    def test_meant_for_the_backend_absence(self):
        self.skipTest("only meaningful when json is not installed")
