"""eft_truncation.py: duplicate cross terms, empty conventions, rescaling check, non-finite input (THY-WP1.2).

Every input is a constructed test input, not an EFT fit."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "hep-theory" / "scripts" / "eft_truncation.py"
_spec = importlib.util.spec_from_file_location("eft_truncation", SCRIPT)
eft = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eft)

VALID = {"basis": "Warsaw (test input)", "normalization": "C_i / Lambda^2", "input_scheme": "{m_W, m_Z, G_F} (test)",
         "lambda_tev": 1.0, "operators": ["a", "b"], "x_sm": 1.0, "linear": {"a": 0.1, "b": 0.2},
         "quadratic": {"a*a": 0.01, "a*b": 0.05}, "cross_term_convention": "B_ab multiplies C_a C_b once",
         "points": [{"a": 1, "b": 1}]}
# the audit's reproduction inputs (copied, not imported)
DUP = {"basis": "Warsaw", "normalization": "C_i / Lambda^2", "input_scheme": "mW", "lambda_tev": 1.0,
       "operators": ["a", "b"], "x_sm": 1.0, "linear": {"a": 0.1, "b": 0.2},
       "quadratic": {"a*b": 0.05, "b*a": 0.05, "a*a": 0.01}, "points": [{"a": 1, "b": 1}]}
EMPTY = {"basis": "", "normalization": "C_i / Lambda^2", "input_scheme": "mW", "lambda_tev": 0, "operators": [],
         "x_sm": 1.0, "linear": {}, "points": []}
BADKEY = {"basis": "Warsaw", "normalization": "n", "input_scheme": "mW", "lambda_tev": 1.0, "operators": ["a"],
          "x_sm": 1.0, "linear": {"a": 0.1}, "quadratic": {"a*a*a": 0.1}, "points": [{"a": 1}]}
LAM0 = {"basis": "Warsaw", "normalization": "n", "input_scheme": "mW", "lambda_tev": 0, "operators": ["a"],
        "x_sm": 1.0, "linear": {"a": 0.1}, "points": [{"a": 1}]}
NAN_POINT = '{"basis":"W","normalization":"n","input_scheme":"mW","lambda_tev":1,"operators":["a"],"x_sm":1,' \
            '"linear":{"a":0.1},"points":[{"a":NaN}]}'


def cli(doc):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "in.json"
        p.write_text(doc if isinstance(doc, str) else json.dumps(doc))
        return subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True, timeout=600)


class RefusalTests(unittest.TestCase):
    def assert_refused(self, doc, *needles):
        r = cli(doc)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["status"], "failed")
        for n in needles:
            self.assertIn(n, out["reason"])
        return out

    def test_duplicate_cross_term_spellings_are_refused(self):
        self.assert_refused(DUP, "duplicate", "a*b", "b*a")

    def test_empty_conventions_and_zero_lambda_are_refused(self):
        self.assert_refused(EMPTY)
        self.assert_refused(LAM0, "lambda_tev")
        for field, value in (("basis", " "), ("normalization", ""), ("input_scheme", ""), ("operators", []),
                             ("lambda_tev", -1.0), ("lambda_tev", "inf")):
            with self.subTest(field=field, value=value):
                self.assert_refused(dict(VALID, **{field: value}), field)

    def test_key_that_is_not_a_pair_is_named(self):
        self.assert_refused(BADKEY, "a*a*a")

    def test_non_finite_point_and_coefficients_are_refused(self):
        self.assert_refused(NAN_POINT)
        self.assert_refused(json.dumps(dict(VALID, linear={"a": float("inf"), "b": 0.2})))  # "Infinity"
        self.assert_refused(json.dumps(dict(VALID, quadratic={"a*a": float("nan"), "a*b": 0.05})))
        self.assert_refused(dict(VALID, x_sm="1"), "x_sm")

    def test_off_diagonal_key_needs_a_cross_term_convention(self):
        self.assert_refused({k: v for k, v in VALID.items() if k != "cross_term_convention"}, "cross_term_convention")

    def test_malformed_inputs_give_json_not_a_traceback(self):
        for doc in ([1], dict(VALID, points=[1]), dict(VALID, linear=[1]), dict(VALID, quadratic={"a*b": None}),
                    dict(VALID, operators=["a", "a"]), dict(VALID, quadratic_flag_fraction=-0.1)):
            with self.subTest(doc=doc):
                self.assert_refused(doc)


class OutputTests(unittest.TestCase):
    def test_valid_input_reports_rescaling_check_and_flag_fraction_source(self):
        r = eft.evaluate(VALID)
        self.assertEqual(r["rescaling_check"], "pass")
        self.assertEqual(r["points"][0]["rescaling_check"], "pass")
        self.assertEqual(r["quadratic_flag_fraction"], {"value": 0.3, "source": "default"})
        self.assertIn("no implicit factor 2", r["cross_terms"])
        r = eft.evaluate(dict(VALID, quadratic_flag_fraction=0.5))
        self.assertEqual(r["quadratic_flag_fraction"], {"value": 0.5, "source": "input"})

    def test_off_diagonal_term_enters_once(self):
        r = eft.evaluate(VALID)
        self.assertAlmostEqual(r["points"][0]["quadratic_term"], 0.01 + 0.05, places=12)

    def test_reordered_spelling_is_canonicalized(self):
        a = eft.evaluate(VALID)["points"][0]["quadratic_term"]
        b = eft.evaluate(dict(VALID, quadratic={"a*a": 0.01, "b*a": 0.05}))["points"][0]["quadratic_term"]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
