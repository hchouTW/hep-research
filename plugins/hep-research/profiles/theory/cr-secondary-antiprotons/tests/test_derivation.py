"""theory:cr-secondary-antiprotons derivation tests: the SymPy checks pass, the stored record is current, and the
checks are discriminating (a wrong upper limit or a wrong Gamma-function ratio fails)."""
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

HAVE_SYMPY = find_spec("sympy") is not None
if HAVE_SYMPY:
    import sympy as sp

    import derive


@unittest.skipUnless(HAVE_SYMPY, "sympy is required (requirements-core.txt)")
class DerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = derive.derive()

    def test_all_checks_pass(self):
        self.assertEqual(self.out["status"], "analytic-derivation")
        self.assertTrue(all(self.out["checks"].values()), self.out["checks"])
        self.assertGreaterEqual(len(self.out["checks"]), 10)

    def test_stored_record_is_current(self):
        stored = json.loads((ROOT / "derivations" / "derivation.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["checks"], self.out["checks"])
        self.assertEqual(stored["results"], self.out["results"])

    def test_wrong_upper_limit_is_detected(self):
        self.assertFalse(derive.direct_vs_beta(2, derive.Tth, 2 * derive.T / derive.Tth))

    def test_wrong_gamma_ratio_is_detected(self):
        g, x = derive.g, derive.x
        lhs = sp.integrate(x ** (g - 1) * (1 - x) ** 2, (x, 0, 1), conds="none")
        self.assertFalse(derive.zero(sp.gammasimp(lhs - sp.gamma(g) * 2 / sp.gamma(g + 2))))


if __name__ == "__main__":
    unittest.main()
