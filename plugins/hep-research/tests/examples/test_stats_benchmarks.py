"""examples/stats-benchmarks: hep-statistics audit benchmarks (SYNTHETIC). coverage-grid (T14): exact coverage of the
known-background belts, toy coverage of the asymptotic profile limit with the predeclared gate, a toy calibration
against an exact value and a negative control the gate must reject. The fast tier runs 2,000 toys; the slow tier
reproduces the committed 20,000-toy output."""
import contextlib
import importlib.util
import io
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
BENCH = PLUGIN / "examples" / "stats-benchmarks"
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"
NETWORK = os.environ.get("HEP_NETWORK_TESTS") == "1"


def load(name):
    spec = importlib.util.spec_from_file_location(f"bench_{name.replace('-', '_')}", BENCH / name / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def close(a, b, path=""):
    if isinstance(a, dict):
        if set(a) != set(b):
            return [f"{path}: keys differ"]
        return [m for k in a for m in close(a[k], b[k], f"{path}/{k}")]
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: lengths differ"]
        return [m for i, (x, y) in enumerate(zip(a, b)) for m in close(x, y, f"{path}/{i}")]
    if isinstance(a, float) or isinstance(b, float):
        return [] if math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12) else [f"{path}: {a} != {b}"]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def run(mod, *args):
    td = tempfile.TemporaryDirectory()
    with contextlib.redirect_stdout(io.StringIO()):
        code = mod.main(["--out", td.name, *args])
    res = json.loads((Path(td.name) / "results.json").read_text())
    td.cleanup()
    return code, res


class CoverageGrid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load("coverage-grid")
        cls.committed = json.loads((BENCH / "coverage-grid" / "output" / "results.json").read_text())
        cls.code, cls.res = run(cls.mod, "--toys", "2000")

    def test_smoke_run_passes_its_criteria(self):
        self.assertEqual(self.code, 0)
        s = self.res["summary"]
        self.assertTrue(s["exact_belts_pass"])
        self.assertTrue(s["toy_calibration_agrees"])
        self.assertTrue(s["negative_control_rejected"])
        self.assertEqual(s["asymptotic_points_failing"], [])

    def test_exact_coverage_matches_the_committed_output(self):
        self.assertEqual(close(self.res["exact"], self.committed["exact"]), [])

    def test_committed_full_budget_result(self):
        c = self.committed
        self.assertEqual(c["toys"], 20000)
        self.assertTrue(all(r["gate"]["verdict"] == "pass" for r in c["asymptotic_profile"]))
        self.assertEqual(c["negative_control"]["gate"]["verdict"], "fail")
        for r in c["exact"]:
            self.assertGreaterEqual(r["classical"], 0.95 - 1e-12)
            self.assertGreaterEqual(r["feldman_cousins"], 0.95 - 1e-12)

    @unittest.skipUnless(SLOW, "slow (about 25 s, the 20,000-toy grid): set HEP_SLOW_TESTS=1")
    def test_full_budget_reproduces(self):
        code, res = run(self.mod)
        self.assertEqual(code, 0)
        self.assertEqual(close(res, self.committed), [])


class DiscreteProfile(unittest.TestCase):
    """T27 (EXPERIMENTAL): the committed discrete-profiling study (skills/hep-statistics/scripts/discrete_profile.py):
    four true backgrounds (three in the candidate family, one outside), mu = 0 and 1, the envelope rebuilt in every
    toy, a single fixed form as the baseline; criteria fixed in the script before the study."""

    @classmethod
    def setUpClass(cls):
        import sys as _s
        _s.path.insert(0, str(PLUGIN / "skills" / "hep-statistics" / "scripts"))
        import discrete_profile
        cls.dp = discrete_profile
        cls.res = json.loads((BENCH / "discrete-profile" / "output" / "results.json").read_text())

    def test_study_design_and_criteria(self):
        r = self.res
        self.assertEqual(r["criteria"], self.dp.CRITERIA)
        truths = {row["truth"] for row in r["rows"]}
        self.assertEqual(truths, set(self.dp.TRUTHS))
        self.assertIn("outside_family", truths)
        self.assertEqual({row["mu_true"] for row in r["rows"]}, {0.0, 1.0})
        varied = False
        for row in r["rows"]:
            self.assertEqual(row["toys"], 300)
            self.assertEqual(sum(row["forms_chosen"].values()) + row["failed"], 300)
            varied |= row["procedure"] == "envelope" and len(row["forms_chosen"]) > 1
        self.assertTrue(varied)                                          # the selection is redone per toy

    def test_one_toy_envelope_is_at_least_as_wide_as_one_form(self):
        import numpy as _np
        n = _np.random.default_rng(1).poisson(self.dp.TRUTHS["outside_family"]())
        _, _, lo_e, hi_e = self.dp.interval(n)
        _, _, lo_1, hi_1 = self.dp.interval(n, ["exp1"])
        self.assertLessEqual(lo_e, lo_1 + 1e-3)
        self.assertGreaterEqual(hi_e, hi_1 - 1e-3)

    def test_envelope_coverage_established_at_1500_toys(self):
        # preregistered follow-up (1,500 toys per envelope row, seed 20261013, criteria unchanged): the 300-toy study
        # could not decide coverage; with 1,500 every envelope row passes bias and coverage
        r = json.loads((BENCH / "discrete-profile" / "output" / "results-envelope-1500.json").read_text())
        self.assertEqual(r["criteria"], self.dp.CRITERIA)
        self.assertEqual(r["procedures"], ["envelope"])
        self.assertEqual(len(r["rows"]), 8)
        for row in r["rows"]:
            self.assertEqual(row["toys"], 1500)
            self.assertTrue(row["bias_ok"], row)
            self.assertEqual(row["coverage_verdict"], "pass", row)

    @unittest.skipUnless(SLOW, "slow (the 300-toy study: about 10 minutes on 8 cores, an hour on one): set HEP_SLOW_TESTS=1")
    def test_study_reproduces(self):
        # the rows run in parallel (seeds depend on the row only). The fits are Nelder-Mead/BFGS, whose last digits
        # differ between platforms and can flip a toy that sits on an interval edge, so the comparison is per row:
        # coverage within 2 percentage points (6 of 300 toys), mean mu-hat within 0.01, bias within 0.05 of the
        # spread, failures within 2, and every verdict identical. On the platform that wrote the output the numbers
        # agree exactly.
        new = self.dp.study(300, self.res["seed"], workers=max(1, min(8, os.cpu_count() or 1)))
        self.assertEqual(len(new["rows"]), len(self.res["rows"]))
        for a, b in zip(new["rows"], self.res["rows"]):
            key = (b["truth"], b["mu_true"], b["procedure"])
            self.assertEqual((a["truth"], a["mu_true"], a["procedure"]), key)
            self.assertLessEqual(abs(a["coverage_68"] - b["coverage_68"]), 0.02, key)
            self.assertLessEqual(abs(a["mean_mu_hat"] - b["mean_mu_hat"]), 0.01, key)
            self.assertLessEqual(abs(a["bias_over_spread"] - b["bias_over_spread"]), 0.05, key)
            self.assertLessEqual(abs(a["failed"] - b["failed"]), 2, key)
            self.assertEqual((a["bias_ok"], a["coverage_verdict"]), (b["bias_ok"], b["coverage_verdict"]), key)


class PublishedLikelihood(unittest.TestCase):
    """T17: the committed reproduction of ATLAS-SUSY-2018-31 SRB (OBSERVED public likelihood). The asymptotic
    construction was preregistered as primary and reproduces every value; the toy construction is reported with its
    own verdict (it does not reproduce the observed and -1 sigma limits); the fit without the control region fails."""

    @classmethod
    def setUpClass(cls):
        out = BENCH / "published-likelihood-sbottom" / "output"
        cls.res = json.loads((out / "results.json").read_text())
        cls.val = json.loads((out / "artifact_validation.json").read_text())
        cls.mod = load("published-likelihood-sbottom")

    def test_committed_verdicts(self):
        v = self.res["verdict"]
        self.assertTrue(v["asymptotic_reproduces"])
        self.assertTrue(v["negative_control_fails"])
        self.assertFalse(v["toy_based_reproduces"])
        self.assertEqual(self.res["pallet_sha256"], self.mod.SHA256)
        self.assertEqual(self.res["preregistration"], self.mod.PREREGISTRATION)
        a = self.res["asymptotic"]["values"]
        self.assertEqual(len(a["S95_exp"]), 5)
        self.assertEqual(len(a["cls_scan"]["S"]), 31)                     # a full scan, not CLs at one point
        t = self.res["toy_based"]["values"]
        self.assertEqual(t["toys_per_point"], 5000)
        lo, hi = t["S95_obs_mc_range_95"]
        self.assertGreater(lo, 4.9 + 0.05)                                 # the toy limit is not the published one

    def test_artifacts_validate_and_the_gate_is_not_passed(self):
        self.assertTrue(self.val["computational_run"]["ok"])
        self.assertTrue(self.val["statistical_result"]["ok"])
        self.assertEqual(self.val["publication_gate"]["status"], "unresolved")

    @unittest.skipUnless(NETWORK and SLOW, "network and slow (downloads the HEPData pallet): set HEP_NETWORK_TESTS=1 and HEP_SLOW_TESTS=1")
    def test_asymptotic_reproduction_reruns(self):
        import tempfile as _t
        with _t.TemporaryDirectory() as td:
            with contextlib.redirect_stdout(io.StringIO()):
                code = self.mod.main(["--download", td, "--toys", "0", "--out", td])
            self.assertEqual(code, 0)
            new = json.loads((Path(td) / "results.json").read_text())
        for k, row in self.res["asymptotic"]["comparison"].items():
            self.assertEqual(new["asymptotic"]["comparison"][k]["status"], row["status"], k)
            self.assertAlmostEqual(new["asymptotic"]["comparison"][k]["reproduced"], row["reproduced"],
                                   delta=1e-3 * abs(row["reproduced"]), msg=k)   # optimizer and platform differences


if __name__ == "__main__":
    unittest.main()
