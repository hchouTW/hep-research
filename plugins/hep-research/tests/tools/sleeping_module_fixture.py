"""Fixture for tests/tools/test_run_all_checks.py: a test module that never finishes in time (not discovered: the
file name does not start with test_)."""
import time
import unittest


class Sleeps(unittest.TestCase):
    def test_sleeps(self):
        time.sleep(60)
