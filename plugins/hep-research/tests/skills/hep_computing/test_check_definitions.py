"""Reconstruction v12 A2: check definitions (scripts/check_definitions.py). Every rule has a positive and a negative
case; the freeze record format and its digest chain have validation tests. All inputs are SYNTHETIC."""
import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-computing" / "scripts" / "check_definitions.py"
sys.path.insert(0, str(SCRIPT.parent))
import check_definitions as CD  # noqa: E402

D1, D2, D3 = "a" * 64, "b" * 64, "c" * 64


def freeze(**over):
    rec = {"step": "reco", "validation_identity": [[D1, D2]], "criteria_version": "v1",
           "confirmation_samples": ["S1", "S2"], "independent_samples": ["S2"], "controls": ["CR"],
           "report_all_confirmations": True,
           "feasibility": {"independent_feasible": True, "reason": "a second resonance is available"},
           "multiple_testing": {"error_type": "false-pass", "combination": "all-pass", "correlations": "global chi2"},
           "cross_round": {"kind": "threshold", "ceiling": 0.025, "option": "allocation"},
           "checks": [{"check_digest": D1, "criterion_digest": D2, "role": "confirmation-independent",
                       "type": "threshold", "rule": {"basis": "physics requirement", "interval": "one-sided",
                                                     "level": 0.975, "systematics": "profiled"}}],
           "power": {"alternative": "true value at the expected performance", "min_pass_favourable": 0.8,
                     "evaluated_on_combined_rule": True},
           "created": "2026-10-29T00:00:00Z"}
    rec.update(over)
    return rec


class Results(unittest.TestCase):
    def test_four_values_with_reason(self):
        self.assertEqual(CD.result("pass", "ok")["result"], "pass")
        for bad in ("passed", "warning", ""):
            with self.subTest(bad=bad):
                self.assertRaises(CD.RuleError, CD.result, bad, "x")
        self.assertRaises(CD.RuleError, CD.result, "fail", " ")

    def test_not_applicable_needs_task_type(self):
        self.assertEqual(CD.result("not-applicable", "no tails in a bounded variable", task_type="T2-numeric")
                         ["task_type"], "T2-numeric")
        self.assertRaises(CD.RuleError, CD.result, "not-applicable", "after the fail")


class Threshold(unittest.TestCase):
    def test_three_regions(self):
        region = (None, 0.05)  # resolution must be below 5 %
        self.assertEqual(CD.threshold_decision((0.03, 0.04), region, power_met=True)["result"], "pass")
        self.assertEqual(CD.threshold_decision((0.06, 0.07), region, power_met=True)["result"], "fail")
        self.assertEqual(CD.threshold_decision((0.04, 0.06), region, power_met=True)["result"], "inconclusive")

    def test_power_not_met_caps_a_pass_but_never_rescues_a_fail(self):
        region = (0.9, None)
        self.assertEqual(CD.threshold_decision((0.92, 0.95), region, power_met=False)["result"], "inconclusive")
        self.assertEqual(CD.threshold_decision((0.80, 0.85), region, power_met=False)["result"], "fail")

    def test_malformed_input_is_refused(self):
        self.assertRaises(CD.RuleError, CD.threshold_decision, (0.2, 0.1), (None, 1.0), power_met=True)
        self.assertRaises(CD.RuleError, CD.threshold_decision, (0.1, 0.2), (None, None), power_met=True)
        self.assertRaises(CD.RuleError, CD.threshold_decision, (0.1, math.nan), (None, 1.0), power_met=True)


class Tolerance(unittest.TestCase):
    kw = dict(k=2.0, sigma_stat=0.01, delta_phys=0.005, claimed_total=0.03, check_precision=0.005)

    def test_pass_and_fail(self):
        self.assertEqual(CD.tolerance_decision(0.002, 0.01, **self.kw)["result"], "pass")
        self.assertEqual(CD.tolerance_decision(0.025, 0.01, **self.kw)["result"], "fail")

    def test_nonzero_deviation_becomes_a_systematic(self):
        d = CD.tolerance_decision(0.015, 0.004, **self.kw)  # inside 0.02, but 3.75 sigma from zero
        self.assertEqual((d["result"], d["transferred_systematic"]), ("pass", 0.015))

    def test_tolerance_above_claimed_uncertainty_is_refused(self):
        self.assertRaises(CD.RuleError, CD.tolerance_decision, 0.0, 0.01, **{**self.kw, "claimed_total": 0.01})

    def test_coarse_check_raises_the_non_closure_systematic(self):
        d = CD.tolerance_decision(0.001, 0.05, **{**self.kw, "check_precision": 0.04})
        self.assertEqual((d["result"], d["transferred_systematic"]), ("pass", 0.04))


class MultipleTesting(unittest.TestCase):
    def test_per_bin_levels(self):
        self.assertEqual(CD.per_bin_alpha(0.05, 20, "pass-rejects-noncompliant"), 0.05)
        self.assertAlmostEqual(CD.per_bin_alpha(0.05, 20, "fail-rejects-compatible"), 0.0025)
        self.assertAlmostEqual(CD.per_bin_alpha(0.05, 20, "fail-rejects-compatible", "sidak"), 0.002561, places=6)
        self.assertRaises(CD.RuleError, CD.per_bin_alpha, 0.05, 20, "any")
        self.assertRaises(CD.RuleError, CD.per_bin_alpha, 0.05, 0, "fail-rejects-compatible")

    def test_combination(self):
        self.assertEqual(CD.combine(["pass", "pass"])["result"], "pass")
        self.assertEqual(CD.combine(["pass", "fail", "inconclusive"])["result"], "fail")
        self.assertEqual(CD.combine(["pass", "inconclusive"])["result"], "inconclusive")
        self.assertEqual(CD.combine(["pass", "inconclusive"], inconclusive_as="fail")["result"], "fail")
        self.assertRaises(CD.RuleError, CD.combine, [])

    def test_twenty_compatibility_bins_need_a_correction(self):  # the 64 % example of Methods §2.4
        self.assertAlmostEqual(1 - 0.95 ** 20, 0.6415, places=4)
        self.assertLess(1 - (1 - CD.per_bin_alpha(0.05, 20, "fail-rejects-compatible")) ** 20, 0.05)


class CrossRound(unittest.TestCase):
    def test_threshold_allocation(self):
        ok = CD.rounds_check("threshold", 0.025, [{"alpha": 0.0125, "level": 0.9875},
                                                  {"alpha": 0.0125, "level": 0.9875}], option="allocation")
        self.assertTrue(ok["within_ceiling"])
        self.assertRaises(CD.RuleError, CD.rounds_check, "threshold", 0.025,  # a 97.5 % level does not implement 1.25 %
                          [{"alpha": 0.0125, "level": 0.975}], option="allocation")

    def test_threshold_cap(self):
        fresh = CD.rounds_check("threshold", 0.1, [{"alpha": 0.025, "fresh": True}] * 3, option="cap")
        self.assertAlmostEqual(fresh["overall"], 0.0731, places=4)
        reused = CD.rounds_check("threshold", 0.1, [{"alpha": 0.025, "fresh": True}, {"alpha": 0.025, "fresh": False}],
                                 option="cap")
        self.assertEqual(reused["overall"], 0.05)
        self.assertFalse(CD.rounds_check("threshold", 0.025, [{"alpha": 0.025, "fresh": True}] * 2,
                                         option="cap")["within_ceiling"])

    def test_compatibility_never_splits_alpha_or_widens(self):
        good = CD.rounds_check("compatibility", 0.2, [{"p_unfav": 0.1, "alpha": 0.05, "tolerance": 0.02},
                                                      {"p_unfav": 0.1, "alpha": 0.05, "tolerance": 0.015}])
        self.assertTrue(good["within_ceiling"])
        self.assertRaises(CD.RuleError, CD.rounds_check, "compatibility", 0.2,
                          [{"p_unfav": 0.1, "alpha": 0.05, "tolerance": 0.02},
                           {"p_unfav": 0.1, "alpha": 0.025, "tolerance": 0.02}])
        self.assertRaises(CD.RuleError, CD.rounds_check, "compatibility", 0.2,
                          [{"p_unfav": 0.1, "alpha": 0.05, "tolerance": 0.02},
                           {"p_unfav": 0.1, "alpha": 0.05, "tolerance": 0.03}])
        self.assertFalse(CD.rounds_check("compatibility", 0.2, [{"p_unfav": 0.2, "alpha": 0.05, "tolerance": 0.02}] * 3)
                         ["within_ceiling"])

    def test_rule_of_three(self):
        self.assertAlmostEqual(CD.rule_of_three(1000), 3 / 1000, places=4)
        self.assertRaises(CD.RuleError, CD.rule_of_three, 0)


class FreezeRecord(unittest.TestCase):
    def test_valid_record(self):
        self.assertEqual(CD.freeze_problems(freeze()), [])

    def test_invalid_records(self):
        cases = {
            "unknown field": freeze(note="x"),
            "missing field": {k: v for k, v in freeze().items() if k != "power"},
            "independent not a confirmation sample": freeze(independent_samples=["CR"]),
            "no report-all commitment": freeze(report_all_confirmations=False),
            "infeasible without conditions": freeze(feasibility={"independent_feasible": False, "reason": "none"}),
            "bad multiple testing": freeze(multiple_testing={"error_type": "fdr", "combination": "all-pass",
                                                             "correlations": "x"}),
            "bad ceiling": freeze(cross_round={"kind": "threshold", "ceiling": 1.5, "option": "cap"}),
            "power not on combined rule": freeze(power={"alternative": "x", "evaluated_on_combined_rule": False}),
            "checks differ from identity": freeze(validation_identity=[[D1, D3]]),
            "independent role without sample": freeze(independent_samples=[]),
        }
        tol = copy.deepcopy(freeze())
        tol["checks"][0].update(type="performance-estimate", role="closure",
                                rule={"method": "m", "k": 3.0, "sigma_stat": 0.02, "delta_phys": 0.0, "claimed_total": 0.03})
        cases["tolerance above claimed"] = tol
        for name, rec in cases.items():
            with self.subTest(case=name):
                self.assertTrue(CD.freeze_problems(rec), name)

    def test_digest_chain(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "freeze.jsonl"
            CD.append_line(log, freeze())
            CD.append_line(log, freeze(criteria_version="v2"))
            self.assertEqual(CD.verify_chain(log), [])
            self.assertRaises(CD.RuleError, CD.append_line, log, freeze(note="x"))
            self.assertEqual(len(log.read_bytes().splitlines()), 2)  # a refused record is not written
            lines = log.read_bytes().splitlines()
            log.write_bytes(lines[1] + b"\n" + lines[0] + b"\n")  # reordered
            self.assertTrue(CD.verify_chain(log))


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                           timeout=60)
        return p.returncode, json.loads(p.stdout)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            good, bad, rule = Path(d) / "g.json", Path(d) / "b.json", Path(d) / "r.json"
            good.write_text(json.dumps(freeze()))
            bad.write_text(json.dumps(freeze(note="x")))
            rule.write_text(json.dumps({"rule": "threshold", "interval": [0.03, 0.04], "region": [None, 0.05],
                                        "power_met": True}))
            self.assertEqual(self.run_cli("validate-freeze", good)[0], 0)
            self.assertEqual(self.run_cli("validate-freeze", bad)[0], 1)
            code, out = self.run_cli("decide", rule)
            self.assertEqual((code, out["decision"]["result"]), (0, "pass"))
            self.assertEqual(self.run_cli("decide", Path(d) / "missing.json")[0], 2)


if __name__ == "__main__":
    unittest.main()
