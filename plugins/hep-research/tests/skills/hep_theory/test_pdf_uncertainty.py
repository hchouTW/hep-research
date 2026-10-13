"""pdf_uncertainty.py: alpha_s members, member count, non-finite input (THY-WP1.1).

Every input is a constructed test input (40 eigenvector members at 1 +- 0.002, then two alpha_s members), not a PDF
set. The expected values are hand values: sqrt(40) * 0.002 = 0.01264911064067353 and (1.03 - 0.97) / 2 = 0.03."""
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "hep-theory" / "scripts" / "pdf_uncertainty.py"
_spec = importlib.util.spec_from_file_location("pdf_uncertainty", SCRIPT)
pdf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pdf)

EIGEN = [1.002, 0.998] * 20  # 40 symmetric eigenvector members
MEMBERS_AS = [1.0] + EIGEN + [0.97, 1.03]  # central, 40 eigenvectors, alpha_s down, alpha_s up


def cli(doc, *flags):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "in.json"
        p.write_text(json.dumps(doc) if not isinstance(doc, str) else doc)
        r = subprocess.run([sys.executable, str(SCRIPT), str(p), *flags], capture_output=True, text=True, timeout=600)
    return r


class AlphasMembersTests(unittest.TestCase):
    def test_symmhessian_as_splits_off_the_last_two_members(self):
        r = pdf.combine("symmhessian+as", MEMBERS_AS)
        self.assertAlmostEqual(r["delta_up"], 0.01264911064067353, delta=1e-12)
        self.assertAlmostEqual(r["delta_down"], 0.01264911064067353, delta=1e-12)
        self.assertEqual(r["n_error_members"], 40)
        self.assertAlmostEqual(r["alphas"]["delta"], 0.03, delta=1e-12)
        self.assertEqual(r["alphas"]["member_values"], {"down": 0.97, "up": 1.03})

    def test_alphas_values_are_reported_when_supplied(self):
        r = pdf.combine("symmhessian+as", MEMBERS_AS, alphas_values=[0.117, 0.119])
        self.assertEqual(r["alphas"]["alphas_values"], {"down": 0.117, "up": 0.119})
        with self.assertRaises(ValueError):
            pdf.combine("symmhessian+as", MEMBERS_AS, alphas_values=[0.119, 0.117])  # not down < up

    def test_hessian_and_replicas_accept_the_as_suffix(self):
        r = pdf.combine("hessian+as", [10.0, 10.4, 9.9, 9.7, 10.1, 9.0, 11.0])
        self.assertAlmostEqual(r["delta_up"], math.sqrt(0.16 + 0.01), places=12)
        self.assertAlmostEqual(r["alphas"]["delta"], 1.0, places=12)
        reps = [5.0 + 0.01 * ((-1) ** k) for k in range(40)]
        r = pdf.combine("replicas+as", [5.0] + reps + [4.0, 6.0])
        self.assertEqual(r["n_error_members"], 40)
        self.assertAlmostEqual(r["alphas"]["delta"], 1.0, places=12)

    def test_without_the_suffix_the_alphas_members_are_not_eigenvectors(self):
        # the defect: the plain formula over 42 members mixes the alpha_s variation into the PDF uncertainty
        r = pdf.combine("symmhessian", MEMBERS_AS)
        self.assertGreater(r["delta_up"], 0.04)
        self.assertNotIn("alphas", r)

    def test_combine_alphas_is_a_labelled_prescription(self):
        r = pdf.combine("symmhessian+as", MEMBERS_AS, combine_alphas="quadrature")
        c = r["pdf_plus_alphas"]
        self.assertEqual(c["prescription"], "quadrature")
        self.assertIn("2203.05506", c["citation"])
        self.assertAlmostEqual(c["delta_up"], math.hypot(0.01264911064067353, 0.03), delta=1e-12)
        with self.assertRaises(ValueError):  # no alpha_s members, nothing to combine
            pdf.combine("symmhessian", [1.0, 1.1, 0.9], combine_alphas="quadrature")
        with self.assertRaises(ValueError):
            pdf.combine("symmhessian+as", MEMBERS_AS, combine_alphas="linear")


class MemberCountTests(unittest.TestCase):
    def test_num_members_mismatch_is_refused(self):
        with self.assertRaises(ValueError) as cm:
            pdf.combine("symmhessian", MEMBERS_AS, num_members=41)
        self.assertIn("43", str(cm.exception))
        r = pdf.combine("symmhessian+as", MEMBERS_AS, num_members=43)
        self.assertEqual(r["num_members_checked"], 43)

    def test_cli_num_members_mismatch_exits_1(self):
        r = cli({"error_type": "symmhessian", "num_members": 41, "members": MEMBERS_AS})
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual(json.loads(r.stdout)["status"], "failed")

    def test_docstring_does_not_claim_a_count_check_for_symmhessian_without_num_members(self):
        self.assertNotIn("refuses a member\ncount that does not fit the declared type", pdf.__doc__)
        self.assertIn("num_members", pdf.__doc__)


class SymmetrizeTests(unittest.TestCase):
    def test_symmetrized_hessian_is_an_alternative_prescription(self):
        r = pdf.combine("hessian", [10.0, 10.4, 9.9, 9.7, 10.1], symmetrize=True)
        s = r["symmetrized"]
        self.assertAlmostEqual(s["delta"], 0.5 * math.sqrt(0.5 ** 2 + 0.4 ** 2), places=12)
        self.assertIn("alternative", s["prescription"])
        with self.assertRaises(ValueError):
            pdf.combine("symmhessian", [1.0, 1.1, 0.9], symmetrize=True)


class NonFiniteInputTests(unittest.TestCase):
    def test_nan_member_is_refused(self):
        with self.assertRaises(ValueError):
            pdf.combine("symmhessian", [1.0, float("nan"), 1.01])
        r = cli('{"error_type":"symmhessian","members":[1.0,NaN,1.01]}')
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["status"], "failed")

    def test_non_finite_conf_level_is_refused(self):
        for cl in (float("nan"), float("inf"), 0.0, 100.0):
            with self.subTest(cl=cl), self.assertRaises(ValueError):
                pdf.combine("symmhessian", [1.0, 1.1, 0.9], conf_level_percent=cl)

    def test_malformed_inputs_give_json_not_a_traceback(self):
        for doc in ({"members": [1, 2, 3]}, {"error_type": "symmhessian", "members": "abc"},
                    {"error_type": "symmhessian", "members": [1, None, 2]}, [1, 2],
                    {"error_type": "symmhessian", "members": [1, 2, 3], "num_members": "x"}):
            with self.subTest(doc=doc):
                r = cli(doc)
                self.assertEqual(r.returncode, 1, r.stderr)
                self.assertNotIn("Traceback", r.stderr)
                self.assertEqual(json.loads(r.stdout)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
