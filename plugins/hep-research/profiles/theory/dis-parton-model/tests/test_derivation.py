"""theory:dis-parton-model derivation tests: the SymPy checks, negative tests of the Altarelli-Martinelli identity,
and the toy closed form against quadrature (SYNTHETIC inputs)."""
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

HAVE_ALL = all(find_spec(m) for m in ("sympy", "numpy", "scipy"))
if HAVE_ALL:
    import sympy as sp

    import derive


@unittest.skipUnless(HAVE_ALL, "sympy, numpy and scipy are required (requirements-core.txt)")
class DerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = derive.derive()

    def test_all_checks_pass(self):
        self.assertEqual(self.out["status"], "perturbative-argument")
        self.assertIn("O(alpha_s^1)", self.out["order"])
        self.assertTrue(all(self.out["checks"].values()), self.out["checks"])

    def test_versions_recorded(self):
        self.assertEqual(self.out["environment"]["sympy"], sp.__version__)
        self.assertTrue(self.out["environment"]["python"])

    def test_wrong_colour_factor_breaks_identity(self):
        self.assertTrue(derive.altarelli_martinelli_integrand()[0])
        self.assertFalse(derive.altarelli_martinelli_integrand(cf=sp.Integer(3))[0])

    def test_missing_charge_average_on_gluon_breaks_identity(self):
        self.assertFalse(derive.altarelli_martinelli_integrand(gluon_has_e2=False)[0])

    def test_charge_average(self):
        avg = derive.flavour_algebra()["e2_average"]
        self.assertEqual(avg["4"], "5/18")
        self.assertEqual(avg["3"], "2/9")

    def test_closed_form_matches_quadrature_and_converges(self):
        rows = self.out["results"]["toy_closed_form_vs_quadrature"]
        self.assertEqual(len(rows), 6)
        for r in rows:
            self.assertLess(r["relative_difference"], 1e-10)
        gl = self.out["results"]["toy_gauss_legendre_relative_error"]["by_x"]
        for errs in gl.values():
            self.assertLess(errs[-1], 1e-10)
            self.assertGreater(errs[0], errs[-1])

    def test_stored_derivation_checks_current(self):
        stored = json.loads((ROOT / "derivations" / "derivation.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["checks"], self.out["checks"])
        self.assertEqual(stored["results"]["integrand_sympy"], self.out["results"]["integrand_sympy"])


if __name__ == "__main__":
    unittest.main()
