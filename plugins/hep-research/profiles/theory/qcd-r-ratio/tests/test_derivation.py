"""theory:qcd-r-ratio derivation tests: the SymPy result, its checks, and a negative test of the mu-independence check."""
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

HAVE_SYMPY = find_spec("sympy") is not None
if HAVE_SYMPY:
    import sympy as sp

    import derive


@unittest.skipUnless(HAVE_SYMPY, "sympy is required (requirements-core.txt)")
class DerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = derive.scale_dependent_coefficients()

    def test_all_checks_pass(self):
        out = derive.derive()
        self.assertEqual(out["status"], "perturbative-argument")
        self.assertTrue(all(out["checks"].values()), out["checks"])

    def test_closed_forms_in_predict_match_sympy(self):
        for nf, eta, lg in ((5, 1 / 33, 0.0), (5, 1 / 33, 1.386), (4, 0.25, -1.386), (3, 0.0, 0.7)):
            sym = [float(x.subs({derive.nf: nf, derive.eta: sp.nsimplify(eta), derive.L: sp.nsimplify(lg)})) for x in self.d]
            num = predict.d_coefficients(nf, eta, lg)
            for k, (s, n) in enumerate(zip(sym, num)):
                self.assertAlmostEqual(s, n, delta=1e-9 * max(1.0, abs(s)), msg=f"d_{k + 1} at nf={nf}, L={lg}")

    def test_wrong_beta0_sign_is_caught(self):
        b0, b1, b2 = derive.betas()
        self.assertTrue(derive.mu_independent(self.d, (b0, b1, b2)))
        self.assertFalse(derive.mu_independent(self.d, (-b0, b1, b2)))

    def test_wrong_coefficient_breaks_the_reference_check(self):
        c = derive.coefficients(5, sp.Rational(1, 33))
        self.assertLess(abs(float(c[1]) - 1.4097), 5e-4)
        self.assertGreater(abs(float(c[1] * 4) - 1.4097), 1.0)  # an alpha_s/(4 pi) expansion would differ by 4^n


if __name__ == "__main__":
    unittest.main()
