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
import sys
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
