"""theory:cr-secondary-ratio derivation tests: the SymPy checks pass, the stored record is current, and the
equivalence check is discriminating (a wrong grammage mapping fails)."""
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

    def test_stored_record_is_current(self):
        stored = json.loads((ROOT / "derivations" / "derivation.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["checks"], self.out["checks"])
        self.assertEqual(stored["results"], self.out["results"])

    def test_wrong_grammage_mapping_fails(self):
        t = derive.thin_disc()
        wrong = 2 * t["grammage"]
        slab_wrong = (derive.sig_ps / derive.m) / (1 / wrong + derive.sig_s / derive.m)
        self.assertNotEqual(sp.simplify(t["ratio"] - slab_wrong), 0)

    def test_grammage_depends_on_D_over_L_only(self):
        lam = derive.thin_disc()["grammage"]
        c = sp.symbols("c", positive=True)
        self.assertEqual(sp.simplify(lam.subs({derive.D_s: c * derive.D_s, derive.L: c * derive.L}) - lam), 0)
        self.assertNotEqual(sp.simplify(lam.subs(derive.L, c * derive.L) - lam), 0)


if __name__ == "__main__":
    unittest.main()
