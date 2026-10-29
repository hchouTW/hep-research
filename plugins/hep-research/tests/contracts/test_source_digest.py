"""contracts/source_digest.py: function-level source digests (P3, G18). The digest ignores formatting but not code,
and reaches the plugin helpers a function uses, so a helper change changes the digest of every function that uses it.
contracts/naming_registry.py records these digests for the naming predicates. (Kept from the cross-artifact check's
Phase 0 tests when the check was retired.)"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class SourceDigest(unittest.TestCase):
    def test_source_digest_ignores_formatting_but_not_code(self):
        from contracts.source_digest import normalized
        a = "def f(x):\n    '''doc'''\n    return (x +\n            1)  # one\n"
        b = "def f(x):\n    return (x + 1)\n"
        c = "def f(x):\n    return (x + 2)\n"
        self.assertEqual(normalized(a), normalized(b))
        self.assertNotEqual(normalized(b), normalized(c))

    def test_a_helper_change_reaches_the_functions_that_use_it(self):
        from contracts import rule_registry, source_digest
        names = source_digest.closure(rule_registry.check)
        self.assertIn("contracts.rule_registry.check", names)
        self.assertIn("contracts.rule_registry._check_sources", names)
        self.assertIn("contracts.rule_registry._test_exists", names)

    def test_naming_predicates_keep_their_recorded_digests(self):
        from contracts import naming_registry
        digests = naming_registry.predicate_digests()
        self.assertTrue(digests)
        self.assertTrue(all(len(v) == 64 for v in digests.values()))


if __name__ == "__main__":
    unittest.main()
