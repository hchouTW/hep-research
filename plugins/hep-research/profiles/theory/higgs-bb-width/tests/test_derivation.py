"""theory:higgs-bb-width derivation tests: the SymPy result, its checks, the closed recursion in predict.py, and
negative tests of the mu-independence check."""
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
        cls.out = derive.derive()
        cls.bs, cls.gs = derive.betas(5), derive.gammas(5)
        cls.r = derive.scale_dependent_coefficients(5)

    def test_all_checks_pass(self):
        self.assertEqual(self.out["status"], "perturbative-argument")
        self.assertTrue(all(self.out["checks"].values()), self.out["checks"])

    def test_recursion_in_predict_matches_sympy(self):
        s4 = -825.7
        for lg in (0.0, 1.386, -1.386, 0.37):
            sub = {derive.L: sp.nsimplify(lg), derive.s4: sp.nsimplify(s4), **derive.NUMERIC}
            sym = [float(x.subs(sub)) for x in self.r]
            num = predict.r_values(5, s4, lg)
            for k, (a, b) in enumerate(zip(sym, num)):
                self.assertAlmostEqual(a, b, delta=1e-9 * max(1.0, abs(a)), msg=f"r_{k} at L={lg}")

    def test_wrong_beta0_or_gamma1_is_caught(self):
        self.assertTrue(derive.mu_independent(self.r, self.bs, self.gs))
        self.assertFalse(derive.mu_independent(self.r, [-self.bs[0]] + self.bs[1:], self.gs))
        self.assertFalse(derive.mu_independent(self.r, self.bs, self.gs[:1] + [2 * self.gs[1]] + self.gs[2:]))

    def test_alpha_s_over_4pi_normalization_would_be_caught(self):
        """Reading the hep-ph/9701390 beta_i (alpha_s/(4 pi)) as alpha_s/pi coefficients breaks mu-independence."""
        self.assertFalse(derive.mu_independent(self.r, derive.betas_4pi(5), self.gs))

    def test_numeric_coefficients_in_predict_match_sympy(self):
        for nf in (3, 4, 5):
            sym = [float(sp.sympify(x).subs({derive.nf: nf, derive.s4: 0}).subs(derive.NUMERIC))
                   for x in [1] + derive.s_coefficients(nf_=derive.nf)]
            self.assertEqual(len(sym), 5)
            for a, b in zip(sym[:4], predict.s_coefficients(nf, 0.0)[:4]):
                self.assertAlmostEqual(a, b, delta=1e-10 * max(1.0, abs(a)))
            for a, b in zip(derive.gammas(nf), predict.gammas(nf)):
                self.assertAlmostEqual(float(sp.sympify(a).subs(derive.NUMERIC)), b, delta=1e-9 * max(1.0, abs(b)))
            for a, b in zip(derive.betas(nf), predict.betas(nf)):
                self.assertAlmostEqual(float(sp.sympify(a).subs(derive.NUMERIC)), b, delta=1e-9 * max(1.0, abs(b)))


if __name__ == "__main__":
    unittest.main()
