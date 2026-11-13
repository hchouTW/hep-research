"""The phase-3 gate and G8 drivers (tests/core/calibration_phase3_gates.py; wave 3, WP-H): the task table, the
`--local` code path, and the merge's decision logic on synthetic task records, each failing configuration reported as
failed (negative) next to a passing control. Everything is `synthetic`."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import calibration_phase3_gates as H  # noqa: E402

from core.calibration import closure as C  # noqa: E402


def _rows(n, sd, bias=0.0, seed=0, start=0, nonconv=()):
    """Synthetic fits: errors N(bias sigma, sigma^2) with sigma_tot = sigma_design."""
    rng = np.random.default_rng(seed)
    out = []
    for s in range(start, start + n):
        if s in nonconv:
            out.append({"s": s, "converged": False})
            continue
        e = (bias + rng.standard_normal(len(sd))) * sd
        out.append({"s": s, "converged": True, "error": e.tolist(), "sigma_tot": list(sd)})
    return out


class TaskTable(unittest.TestCase):
    def test_families_and_determinism(self):
        fam = H.family_counts()
        self.assertEqual(fam["units"], len(H.UNIT_ITEMS))
        self.assertEqual(fam["g8_3m"], 2 * H.M3["per_point"] // H.M3["chunk"])
        self.assertEqual(fam["g8_3m_spot"], 1)
        for name, cfg in H.TOY_CONFIGS.items():
            self.assertEqual(fam[f"toy_g8|{name}"], cfg["reps"] * 2 * H.TOY_PER_POINT // H.toy_chunk(cfg))
        first = [i for i, (f, kw) in enumerate(H.TASKS) if f == "toy_g8" and H.TOY_CONFIGS[kw["config"]].get("second")]
        mm = [i for i, (f, _) in enumerate(H.TASKS) if f == "toy_g8_mm"]
        self.assertEqual((mm[0], mm[-1]), (24124, 25163))      # the registered p3-toy-g8 indices stay where they were
        self.assertGreater(min(first), mm[-1])
        self.assertEqual(H.toy_truth_batches(H.TOY_CONFIGS["cal6b"]), 200)
        self.assertEqual(H.toy_truth_batches(H.TOY_CONFIGS["cal6"]), H.TOY_TRUTH_BATCHES)
        json.dumps(H.TASKS)                                   # every task's arguments are plain JSON
        self.assertEqual(H.cal_seed(1, 7), H.cal_seed(1, 7))
        self.assertNotEqual(H.cal_seed(1, 7), H.cal_seed(6, 7))
        self.assertGreaterEqual(H.M3["per_point"], C.n_c(3, "full")["N_c"])
        self.assertGreaterEqual(H.TOY_PER_POINT, C.n_c(2, "full")["N_c"])

    def test_list_cli(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(H.main(["--list"]), 0)
        self.assertEqual(json.loads(buf.getvalue())["tasks"], len(H.TASKS))


class UnitItems(unittest.TestCase):
    def test_negative_caught_and_geant4_skip(self):
        out = {H.EMULATOR_TESTS + "P6Arrays.test_delta_m_fails_on_a_large_difference": {"outcome": "passed"},
               H.EMULATOR_TESTS + "P6Arrays.test_bonferroni_z": {"outcome": "passed"}}
        r = H.judge_units("p6_negatives", out, names=list(out))
        self.assertTrue(r["passed"])
        self.assertEqual(r["negatives_caught"], [H.EMULATOR_TESTS + "P6Arrays.test_delta_m_fails_on_a_large_difference"])
        out[H.PROBLEM_TESTS + "ResponseParametersP0.test_with_geant4"] = {"outcome": "skipped",
                                                                "reason": "requires Geant4: products (Slurm)"}
        r = H.judge_units("g4sim_zdc_positive", {k: v for k, v in out.items() if k.startswith(H.PROBLEM_TESTS)},
                          names=[H.PROBLEM_TESTS + "ResponseParametersP0"])
        self.assertTrue(r["passed"])
        self.assertEqual(r["requires_geant4"], [H.PROBLEM_TESTS + "ResponseParametersP0.test_with_geant4"])

    def test_failures_and_other_skips_fail_the_item(self):
        two = [H.EMULATOR_TESTS + "P6Arrays.test_bonferroni_z", H.EMULATOR_TESTS + "P6Toy.test_too_few_design_points"]
        good = {t: {"outcome": "passed"} for t in two}
        self.assertTrue(H.judge_units("p6_negatives", good, names=two)["passed"])               # control
        bad = {**good, two[1]: {"outcome": "failed", "detail": "x"}}
        self.assertFalse(H.judge_units("p6_negatives", bad, names=two)["passed"])
        skip = {**good, two[1]: {"outcome": "skipped", "reason": "no time"}}
        self.assertFalse(H.judge_units("p6_negatives", skip, names=two)["passed"])
        self.assertFalse(H.judge_units("p6_negatives", {two[0]: {"outcome": "passed"}}, names=two)["passed"])
        self.assertFalse(H.judge_units("p6_negatives", good)["passed"])          # the full item: tests not run

    def test_runner_records_outcomes(self):
        out = H.run_tests([H.EMULATOR_TESTS + "P6Arrays.test_bonferroni_z", "test_calibration_emulator.NoSuchClass"])
        self.assertEqual(out[H.EMULATOR_TESTS + "P6Arrays.test_bonferroni_z"]["outcome"], "passed")
        self.assertEqual(out["test_calibration_emulator.NoSuchClass"]["outcome"], "error")


class ThreeMethodJudge(unittest.TestCase):
    sigma = [0.03, 1e-4, 0.1]

    def blocks(self, bias=0.0, sd=None):
        sd = np.asarray(sd or self.sigma)
        n = H.M3["per_point"]
        return [{"point": pt, "rows": _rows(n, sd, bias if pt == "interior" else 0.0, seed=k, nonconv=(3,)),
                 "sigma_design": sd.tolist(), "theta": [0, 0, 0]} for k, pt in enumerate(("interior", "boundary"))]

    def test_unbiased_passes_and_the_spot_check_does_not_decide(self):
        spot = {"spot_check": {"status": "not-decided"}}
        r = H.g8_3m_judge(self.blocks(), spot)
        self.assertEqual((r["status"], r["spot_check_status"]), ("passed", "not-decided"))
        self.assertEqual(r["g8"]["full"]["N_c"], 518)
        self.assertIn("spot check", r["not_judged"])

    def test_biased_fails(self):
        r = H.g8_3m_judge(self.blocks(bias=0.5), None)
        self.assertEqual(r["status"], "failed")
        self.assertIn("bias", {f["test"] for f in r["g8"]["full"]["fails"]})

    def test_inconsistent_design_or_too_few_fits(self):
        b = self.blocks()
        b[1]["sigma_design"] = [0.031, 1e-4, 0.1]
        self.assertEqual(H.g8_3m_judge(b, None)["status"], "failed")
        b = self.blocks()
        b[0]["rows"] = b[0]["rows"][:100]
        self.assertEqual(H.g8_3m_judge(b, None)["status"], "incomplete")


class ToyG8Judge(unittest.TestCase):
    sigma = np.array([0.0008, 0.02])
    REPS = 20

    def decisions(self, name, bias=0.0, reps=REPS):
        out = []
        for r in range(reps):
            bl = [{"point": pt, "rows": _rows(H.TOY_PER_POINT, self.sigma, bias if pt == "interior" else 0.0,
                                              seed=1000 * r + k), "sigma_design": self.sigma.tolist()}
                  for k, pt in enumerate(("interior", "boundary"))]
            out.append(H.toy_g8_replicate(name, r, bl, self.sigma))
        return out

    def test_correct_configuration_passes_with_power_and_injection(self):
        r = H.toy_g8_judge("cal1", self.decisions("cal1"), reps=self.REPS)
        self.assertEqual(r["status"], "passed", r)
        self.assertEqual(set(r["power"].values()), {self.REPS})
        self.assertTrue(r["calibration_10_passed"])
        self.assertTrue(0.0 < r["calibration_10"]["inject|independent|0.01|full"]["injected_fraction"] < 0.02)

    def test_biased_configuration_is_reported_failed(self):
        r = H.toy_g8_judge("cal6", self.decisions("cal6", bias=0.5), reps=self.REPS)
        self.assertEqual(r["false_alarms_full"], self.REPS)
        self.assertFalse(r["passed"])
        self.assertIn(r["status"], ("failed", "exposure-condition-not-met"))
        r = H.toy_g8_judge("cal6", self.decisions("cal6", bias=0.06), reps=self.REPS)   # the bias condition
        self.assertEqual(r["status"], "exposure-condition-not-met")

    def test_missing_replicates_and_reported_configurations(self):
        r = H.toy_g8_judge("cal6", self.decisions("cal6", reps=5), reps=self.REPS)
        self.assertEqual(r["status"], "incomplete")
        r = H.toy_g8_judge("cal12_vmc2_r10", self.decisions("cal12_vmc2_r10", reps=5), reps=5)
        self.assertEqual((r["status"], r["passed"]), ("reported", None))


class OtherJudges(unittest.TestCase):
    def test_calorimeter_and_phi(self):
        good = {"p3": "passed", "converged": True, "g1": "passed", "pull": [0.3, -1.2]}
        self.assertTrue(H.calo_fit_judge([dict(good, r=i) for i in range(3)], reps=3)["passed"])
        self.assertFalse(H.calo_fit_judge([dict(good, r=0), dict(good, r=1, g1="failed")], reps=2)["passed"])
        self.assertFalse(H.calo_fit_judge([dict(good, r=0, pull=[4.5, 0.0])], reps=1)["passed"])
        self.assertFalse(H.calo_fit_judge([dict(good, r=0)], reps=2)["passed"])                 # a missing repetition
        cases = [{"case": "small", "ok": True}, {"case": "large", "ok": True}]
        self.assertTrue(H.phi_resim_judge(cases)["passed"])
        self.assertFalse(H.phi_resim_judge(cases[:1])["passed"])
        self.assertFalse(H.phi_resim_judge([cases[0], {"case": "large", "ok": False}])["passed"])

    def test_decide_all_reports_missing_records(self):
        tasks = [("units", {"item": "p6_negatives"}), ("zdc_fit", {"r0": 0, "reps": 1})]
        recs = {1: {"result": [{"r": 0, "p3": "passed", "converged": True, "g1": "passed", "pull": [0.0, 0.0]}]}}
        items = H.decide_all(recs, tasks)
        self.assertEqual(items["units|p6_negatives"]["status"], "missing")
        self.assertTrue(items["zdc_fit"]["passed"])


class Local(unittest.TestCase):
    def test_local_code_path(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "local.json"
            self.assertEqual(H.main(["--local", "--out", str(out)]), 0)
            rec = json.loads(out.read_text())
        self.assertEqual(rec["label"], "smoke (not evidence)")
        res = rec["results"]
        self.assertTrue(res["units"]["passed"])
        self.assertEqual(res["g8_3m_spot"], "not-decided")
        self.assertEqual(len(res["toy_g8_rows"]), 2)
        self.assertEqual({b["point"] for b in res["g8_3m_rows"]}, {"interior", "boundary"})


if __name__ == "__main__":
    unittest.main()
