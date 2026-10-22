"""Fixture for tests/tools/test_run_required_backends.py --from-ledger (not a test module: run_all_checks collects
test_*.py only): one node per outcome class; the absent modules are named so that no environment has them."""
import unittest


class Fixture(unittest.TestCase):
    def test_holds(self):
        self.assertEqual(sum(range(5)), 10)

    def test_needs_an_absent_core_dependency(self):
        import hep_fixture_absent_core  # noqa: F401

    def test_needs_an_absent_backend(self):
        self.skipTest("hep_fixture_absent_backend not installed")

    def test_does_not_hold(self):
        self.assertEqual(sum(range(5)), 11)

    def test_skips_for_the_slow_tier(self):
        self.skipTest("slow tier: set HEP_SLOW_TESTS=1")

    def test_imports_an_undeclared_module(self):
        import hep_fixture_undeclared  # noqa: F401
