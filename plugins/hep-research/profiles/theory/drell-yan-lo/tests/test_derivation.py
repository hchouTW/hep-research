"""theory:drell-yan-lo derivation tests: every SymPy check passes, versions are recorded, and the checks catch a
wrong Eq. 5, a non-coplanar quark axis and a wrong Eq. 9 coefficient (negative tests)."""
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
        self.assertTrue(all(self.out["checks"].values()), self.out["checks"])
        self.assertEqual(self.out["status"]["lo_cross_section"], "analytic-derivation")
        self.assertEqual(self.out["status"]["lam_tung_and_eq10"], "perturbative-argument")

    def test_channel_mixture_is_a_cross_section_weighted_A_average(self):
        for k in ("mixture:A_terms_integrate_to_zero", "mixture:unpolarized_term_integrates_to_16pi_over_3",
                  "mixture:sigma_weighted_sum_equals_A_average", "mixture:lambda_form_with_3_plus_lambda_weights"):
            self.assertTrue(self.out["checks"][k], k)
        self.assertEqual(self.out["status"]["channel_mixture"], "analytic-derivation")

    def test_versions_recorded(self):
        self.assertEqual(self.out["environment"]["sympy"], sp.__version__)

    def test_wrong_sign_in_eq5_is_caught(self):
        bad = derive.eq5() - 2 * (derive.a * sp.cos(derive.th1)) * sp.cos(derive.th)  # flips the A4 term
        self.assertTrue(derive._normal_form(derive.eq2_with_eq4() - derive.eq5()).is_zero)
        self.assertFalse(derive._normal_form(derive.eq2_with_eq4() - bad).is_zero)

    def test_non_coplanar_axis_violates_lam_tung(self):
        a6 = derive.eq6()
        A0, A2 = derive.A[0], derive.A[2]
        lt = 1 - (2 - 3 * A0) / (2 + A0) - 2 * (2 * A2) / (2 + A0)
        val = lt.subs({A0: a6[0], A2: a6[2]}).subs({derive.th1: sp.pi / 4, derive.ph1: sp.pi / 6})
        self.assertGreater(float(val), 0.0)

    def test_wrong_qg_coefficient_does_not_reproduce_eq10(self):
        r = derive.r
        a0 = 4 * r ** 2 / (1 + 4 * r ** 2)
        lam = sp.simplify((2 - 3 * a0) / (2 + a0))
        self.assertNotEqual(sp.simplify(lam - derive.PENG_EQ10["qg"][0]), 0)

    def test_cross_section_form(self):
        lo = self.out["results"]["lo"]
        self.assertEqual(lo["sigma_hat_qqbar_to_ll"], "4*pi*alpha**2*e_q**2/(9*s_hat)")
        self.assertIn("8*pi*alpha**2", lo["d2sigma_dM_dy"])

    def test_stored_derivation_current(self):
        stored = json.loads((ROOT / "derivations" / "derivation.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["checks"], self.out["checks"])
        self.assertEqual(stored["results"], self.out["results"])


if __name__ == "__main__":
    unittest.main()
