"""CHK-AT-08-02 (S2): the status and warnings of charge_confusion_rate.py template mode follow one rule per bin.

Rule (the lead's decision for CHK-AT-08-02, the convention of core/stats/template_fit._overall): a bin whose fit
outcome is not-converged or infeasible makes the status failed (exit 1); a bin whose outcome is
converged-at-boundary or covariance-warning leaves the status ok (exit 0) and adds a warning naming the bin; a
converged bin adds nothing. The old test on rate_error being None could never fire (rate_error is the half-width of the
profile interval), so a covariance-warning bin was reported ok with no warning.

Oracle (basis exhaustive): the rule is enumerated over its whole finite domain, the five fit outcomes of
core/stats/template_fit.py in the second of two bins (the first converged), with the per-bin fit replaced by a
fixed row of that outcome, so only the status logic is under test. Expected values come from the rule above, not from
the tool. A real fit is checked too: SYNTHETIC data with no wrong-sign events (seeded) put the wrong-sign yield at the
boundary, and that bin must be warned. No tolerances: statuses, exit codes and warnings are compared exactly.
"""
import contextlib
import importlib.util
import io
import json
import math
import random
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "charge_confusion_rate.py"
RIGHT = [400, 1200, 2400, 1200, 400, 40, 4, 1]   # SYNTHETIC discriminant shapes (MC counts)
WRONG = [1, 4, 40, 400, 1200, 2400, 1200, 400]
OUTCOMES = ("converged", "converged-at-boundary", "covariance-warning", "not-converged", "infeasible")
# the rule: outcome -> (status, exit code, warned)
RULE = {"converged": ("ok", 0, False), "converged-at-boundary": ("ok", 0, True), "covariance-warning": ("ok", 0, True),
        "not-converged": ("failed", 1, True), "infeasible": ("failed", 1, True)}


def load_module():
    spec = importlib.util.spec_from_file_location("charge_confusion_rate_status", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def poisson(rng, mu):
    if mu > 50:
        return max(0, int(round(rng.gauss(mu, math.sqrt(mu)))))
    k, p, l_ = 0, 1.0, math.exp(-mu)
    while True:
        p *= rng.random()
        if p <= l_:
            return k
        k += 1


def run_main(mod, doc):
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "t.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = mod.main(["template", "--input", str(path)])
    return code, json.loads(buf.getvalue())


class TemplateStatusRule(unittest.TestCase):
    def test_exhaustive_outcome_rule(self):
        mod = load_module()
        doc = {"edges": [1.0, 2.0, 3.0], "true_sign": "negative",
               "bins": [{"data": [1, 1], "templates": {"right": [1, 0], "wrong": [0, 1]}}] * 2}
        for outcome in OUTCOMES:
            calls = []

            def fake(bin_doc, names, outcome=outcome, calls=calls):
                calls.append(1)
                return {"rate": 0.02, "rate_error_hessian": None, "interval_68": [0.01, 0.03], "rate_error": 0.01,
                        "interval_method": "fixed row (test)", "yields": {"right": 98.0, "wrong": 2.0},
                        "fit_outcome": "converged" if len(calls) == 1 else outcome}
            mod.template_rate = fake
            code, out = run_main(mod, doc)
            status, exit_code, warned = RULE[outcome]
            with self.subTest(outcome=outcome):
                self.assertEqual((out["status"], code), (status, exit_code), out)
                named = [w for w in out["warnings"] if "bin 2" in w]
                self.assertEqual(bool(named), warned, out["warnings"])
                self.assertFalse([w for w in out["warnings"] if "bin 1" in w], out["warnings"])

    def test_real_boundary_fit_is_warned(self):
        rng = random.Random(1)
        sr, sw = sum(RIGHT), sum(WRONG)
        b = {"data": [poisson(rng, 20000 * r / sr) for r in RIGHT],
             "templates": {"right": [poisson(rng, r) for r in RIGHT], "wrong": [poisson(rng, w) for w in WRONG]},
             "mc_events": {"right": 2 * sr, "wrong": 2 * sw}}
        code, out = run_main(load_module(), {"edges": [1.0, 2.0], "true_sign": "positive", "bins": [b]})
        outcome = out["bins"][0]["fit_outcome"]
        self.assertIn(outcome, OUTCOMES)
        status, exit_code, warned = RULE[outcome]
        self.assertNotEqual(outcome, "converged", out["bins"][0])   # no wrong-sign events: the yield is at 0
        self.assertEqual((out["status"], code), (status, exit_code), out)
        self.assertEqual(any("bin 1" in w for w in out["warnings"]), warned, out["warnings"])


if __name__ == "__main__":
    unittest.main()
