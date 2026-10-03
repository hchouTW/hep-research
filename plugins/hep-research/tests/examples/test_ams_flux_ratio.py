"""Path A (journey J1) regression tests: synthetic flux and correlated ratio with the AMS-02 profile.

Covers reproducibility, Asimov closure, toy closure with the default 400 seeded toys, the correlated ratio against an
independent propagation (T10), time-dependent exposure averaging (T11), contract validity and synthetic labeling.
All inputs are synthetic; passing says the chain is internally consistent, nothing about a real detector.
"""
import contextlib
import hashlib
import io
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "ams-flux-ratio" / "run.py"

try:
    import numpy as np  # noqa: F401
    import matplotlib  # noqa: F401
    HAVE_DEPS = True
except ImportError:  # the D5 environment provides both
    HAVE_DEPS = False


def run(mod, *argv):
    with contextlib.redirect_stdout(io.StringIO()):
        return mod.main(list(argv))


def load():
    spec = importlib.util.spec_from_file_location("ams_flux_ratio_run", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ams_flux_ratio_run"] = mod
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(HAVE_DEPS, "numpy and matplotlib are required (D5 environment)")
class PathATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.world = cls.m.build_world()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "a"
        cls.code = run(cls.m, "--out", str(cls.out))
        cls.results = json.loads((cls.out / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_run_passes_its_predeclared_criteria(self):
        self.assertEqual(self.code, 0, self.results["pass"])
        self.assertTrue(all(self.results["pass"].values()))

    def test_reproducible_with_the_same_seed(self):
        other = Path(self.tmp.name) / "b"
        run(self.m, "--out", str(other))
        digest = [hashlib.sha256((d / "results.json").read_bytes()).hexdigest() for d in (self.out, other)]
        self.assertEqual(digest[0], digest[1])

    def test_different_seed_changes_the_pseudo_data(self):
        other = Path(self.tmp.name) / "c"
        run(self.m, "--seed", "7", "--out", str(other))
        self.assertNotEqual(json.loads((other / "results.json").read_text())["observed_counts"], self.results["observed_counts"])

    def test_asimov_closure_is_exact(self):
        _, dev = self.m.asimov_closure(self.world)
        self.assertLess(max(dev.values()), 1e-9, dev)
        self.assertEqual({k.split("/")[1] for k in dev}, {*self.m.PERIODS, "average"})

    def test_T10_ratio_uncertainty_matches_independent_propagation(self):
        for p, ref in self.results["ratio_reference_T10"].items():
            self.assertLess(ref["max_rel_difference"], 1e-9, p)
            # the shared trigger term cancels, so treating it as independent overstates the sigma in every bin
            self.assertTrue(all(f > 1.0 for f in ref["overestimate_factor_if_independent"]), p)

    def test_T10_trigger_term_cancels_in_the_ratio(self):
        res = self.m.run_analysis(self.m.simulate(None, self.world, asimov=True), self.world)
        p = next(iter(self.m.PERIODS))
        with_trig = self.m.ratio_block(res[("helium", p)], res[("proton", p)])[1]
        for sp in ("helium", "proton"):
            res[(sp, p)]["trigger"] = res[(sp, p)]["trigger"] * 0
        np.testing.assert_allclose(self.m.ratio_block(res[("helium", p)], res[("proton", p)])[1], with_trig)

    def test_T11_period_average_uses_per_period_exposure(self):
        m, w = self.m, self.world
        for s in m.SPECIES:
            expo = sum(w[s][p]["exposure"] for p in m.PERIODS)
            truth = sum(w[s][p]["exposure"] * w[s][p]["truth_flux"] for p in m.PERIODS) / expo
            np.testing.assert_allclose(w[s]["average_truth"], truth)
            # the plain mean of the period fluxes differs where the periods differ, so the weighting matters
            plain = sum(w[s][p]["truth_flux"] for p in m.PERIODS) / len(m.PERIODS)
            self.assertGreater(np.max(np.abs(plain[m.REPORTED] / truth[m.REPORTED] - 1)), 1e-3)
            err = self.results["time_average_T11"][s]["equal_split_exposure_rel_error"]
            self.assertGreater(max(abs(v) for v in err), 0.01, "equal livetime split must visibly mis-state low-rigidity exposure")

    def test_cutoff_selection_follows_documented_factor(self):
        m = self.m
        self.assertEqual(m.CUTOFF_FACTOR, 1.2)
        for per in m.PERIODS.values():
            f = m.cutoff_fraction(per)
            self.assertTrue(np.all(np.diff(f) >= 0) and f[-1] == 1.0)

    def test_toy_pulls_within_criteria(self):
        crit = self.results["criteria"]
        for k, v in self.results["toy_closure"].items():
            self.assertTrue(all(abs(x) < crit["toy_mean_pull_abs"] for x in v["mean_per_bin"]), k)
            lo, hi = crit["toy_pull_width"]
            self.assertTrue(all(lo < x < hi for x in v["width_per_bin"]), k)

    def test_artifacts_valid_and_labeled_synthetic(self):
        self.assertTrue(all(c["ok"] for c in self.results["contract_validation"].values()), self.results["contract_validation"])
        files = sorted((self.out / "artifacts").glob("*.json"))
        self.assertEqual(len(files), 6)
        for f in files:
            doc = json.loads(f.read_text())
            self.assertIn("synthetic", doc["status"], f.name)
            self.assertTrue(doc["artifact_id"].startswith("synthetic-"), f.name)
        spec = json.loads((self.out / "artifacts" / "measurement_spec.json").read_text())
        params = spec["extension"]["experiment_fields"]["ams02:parameters"]
        self.assertEqual({p["provenance"] for p in params}, {"documented", "proposal"})
        self.assertIn("ams02:C31", spec["provenance"]["evidence_ids"])

    def test_outputs_carry_synthetic_label(self):
        self.assertTrue(self.results["label"].startswith("SYNTHETIC"))
        self.assertIn("(SYNTHETIC)", (self.out / "report.md").read_text().splitlines()[0])
        for png in ("flux_per_period.png", "ratio_per_period.png"):
            self.assertTrue((self.out / png).stat().st_size > 1000)


if __name__ == "__main__":
    unittest.main()
