"""Path B (journey J3) regression tests: SYNTHETIC corrected angular distribution with the illustrative
experiment:synthetic-collider profile. Reproducibility, Asimov and toy closure, independent expected values,
contract validity, synthetic labels, that no other profile (AMS, theory) is loaded, the sideband background estimate and
its closure (P4-2), and that the blinded signal-region bin is absent from every output (sentinel audit)."""
import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "collider-angular" / "run.py"

try:
    import numpy as np
    import matplotlib  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


def load():
    spec = importlib.util.spec_from_file_location("collider_angular_run", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["collider_angular_run"] = mod
    spec.loader.exec_module(mod)
    return mod


def run(mod, *argv):
    with contextlib.redirect_stdout(io.StringIO()):
        return mod.main(list(argv))


@unittest.skipUnless(HAVE_DEPS, "numpy and matplotlib are required (D5 environment)")
class PathBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "a"
        cls.code = run(cls.m, "--out", str(cls.out))
        cls.r = json.loads((cls.out / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_passes_predeclared_criteria(self):
        self.assertEqual(self.code, 0, self.r["pass"])

    def test_reproducible(self):
        other = Path(self.tmp.name) / "b"
        run(self.m, "--out", str(other))
        h = [hashlib.sha256((d / "results.json").read_bytes()).hexdigest() for d in (self.out, other)]
        self.assertEqual(h[0], h[1])

    def test_expected_values_are_independent_of_the_chain(self):
        # analytic: f = 1 + c^2, norm 8/3; bin [0, 0.18): sigma * (0.18 + 0.18^3/3) / (8/3) / 0.18
        e = self.m.expected_dsigma(870.0, 1.0, 0.0)
        j = list(self.m.TE).index(0.0)
        self.assertAlmostEqual(e[j], 870.0 * (0.18 + 0.18 ** 3 / 3) / (8 / 3) / 0.18, places=9)
        # integrating the expected values over [-1, 1] returns the generator cross section
        self.assertAlmostEqual(float(np.sum(e * self.m.WIDTH)), 870.0, places=9)

    def test_asimov_closure_exact(self):
        self.assertLess(max(self.r["asimov_closure"].values()), 1e-9)

    def test_measurement_consistent_with_expected(self):
        f = self.r["fiducial_cross_section_pb"]
        self.assertLess(abs(f["value"] - f["expected"]), 4 * (f["stat"] ** 2 + f["background"] ** 2 + f["lumi"] ** 2) ** 0.5)
        self.assertGreater(self.r["chi2_vs_expected"]["p_value"], 1e-3)

    def test_background_sideband_estimate_and_closure(self):
        b = self.r["background"]
        # Beta(2, 2) x_vis: f(SR = [0.9, 1]) = 1 - (3 x 0.81 - 2 x 0.729) = 0.028, f(CR = [0.5, 0.8)) = 0.896 - 0.5 = 0.396
        self.assertAlmostEqual(b["transfer_factor_signal_region"], 0.028 / 0.396, places=12)
        self.assertAlmostEqual(b["transfer_factor_validation_band"], (0.972 - 0.896) / 0.396, places=12)
        self.assertLess(b["asimov_closure_max_rel_dev"], 1e-12)
        for est, cr, blinded in zip(b["estimate_signal_region"], b["control_region_counts"], self.m.BLINDED):
            if blinded:
                self.assertIsNone(est)
            else:
                self.assertAlmostEqual(est, b["transfer_factor_signal_region"] * cr, places=9)
        v = b["validation_closure"]
        self.assertLess(abs(v["total_pull"]), 3.0)
        self.assertGreater(v["p_value"], 1e-3)
        self.assertTrue(self.r["pass"]["background_validation_closure"] and self.r["pass"]["background_asimov_closure"])
        # the background is a visible fraction of the signal region (not a no-op subtraction)
        sr = sum(x for x in self.r["reco_counts"] if x is not None)
        self.assertGreater(sum(x for x in b["estimate_signal_region"] if x is not None) / sr, 0.01)
        spec = json.loads((self.out / "artifacts" / "measurement_spec.json").read_text())["extension"]
        self.assertEqual(len(spec["backgrounds"]), 1)
        self.assertNotIn("no_backgrounds_reason", spec)
        bkg = spec["backgrounds"][0]
        self.assertIn("x_vis", bkg["control_region"])
        self.assertIn("validation band", bkg["closure"])
        self.assertIn("background_transfer_factor", [s["name"] for s in spec["systematics"]])

    def test_subtraction_is_unbiased_on_the_expectation(self):
        """Asimov input with background: the subtracted, unfolded result returns the generator values exactly."""
        g = self.m.CFG["generator"]
        m = self.m.detector.response(self.m.CFG, g["shape_a"], g["shape_b"])["matrix"]
        mu = m @ (self.m.LUMI * self.m.expected_dsigma(g["sigma_pb"], g["shape_a"], g["shape_b"]) * self.m.WIDTH)
        b = self.m.expected_background()
        res = self.m.analyse(self.m.blind_counts(mu + b["sr"]), b["cr"], m, self.m.LUMI, self.m.TF_SR, mu)
        e = self.m.expected_dsigma(g["sigma_pb"], g["shape_a"], g["shape_b"])
        np.testing.assert_allclose(res["dsigma"][self.m.REP], e[self.m.REP], rtol=1e-9)
        # without the subtraction the same input would be biased by the background fraction
        res0 = self.m.analyse(self.m.blind_counts(mu + b["sr"]), 0 * b["cr"], m, self.m.LUMI, self.m.TF_SR, mu)
        self.assertGreater(np.max(res0["dsigma"][self.m.REP] / e[self.m.REP] - 1), 0.01)

    def test_blinded_bins_are_absent_from_the_outputs(self):
        blinded = [j for j, b in enumerate(self.m.BLINDED) if b]
        self.assertEqual(blinded, [11])
        self.assertEqual(self.r["blinding"]["blinded_reco_bins"], blinded)
        self.assertFalse(self.r["blinding"]["unblinded"])
        for j in blinded:
            self.assertIsNone(self.r["reco_counts"][j])
            self.assertIsNone(self.r["dsigma"]["values"][j])
            for block in self.r["dsigma"]["covariance"].values():
                self.assertTrue(all(x is None for x in block[j]))
                self.assertTrue(all(row[j] is None for row in block))
        released = json.loads((self.out / self.r["blinding"]["released_signal_region_histogram"]).read_text())
        self.assertEqual(released["status"], "synthetic")
        self.assertEqual([j for j, b in enumerate(released["blinded_bins"]) if b], blinded)
        self.assertTrue(all(released["values"][j] is None and released["ratio_to_reference"][j] is None for j in blinded))
        spec = json.loads((self.out / "artifacts" / "measurement_spec.json").read_text())
        bl = spec["extension"]["blinding"]
        self.assertTrue(bl["blinded"])
        self.assertEqual(bl["mask"]["intervals"], [{"variable": "cos_theta", "low": 0.9, "high": 1.0}])
        self.assertIsNone(bl["unblinding_record_ref"])
        self.assertNotIn("observed", spec["status"])
        self.assertEqual(self.r["blinding"]["figure_check"]["status"], "pass")

    def test_published_values_do_not_depend_on_the_blinded_count(self):
        g = self.m.CFG["generator"]
        m = self.m.detector.response(self.m.CFG, g["shape_a"], g["shape_b"])["matrix"]
        d = self.m.pseudo_data(self.r["seed"])
        mu = m @ (self.m.LUMI * self.m.expected_dsigma(g["sigma_pb"], g["shape_a"], g["shape_b"]) * self.m.WIDTH)
        bumped = d["sr"].copy()
        bumped[self.m.BLINDED] += 500.0
        a = self.m.analyse(self.m.blind_counts(d["sr"]), d["cr"], m, self.m.LUMI, self.m.TF_SR, mu)
        b = self.m.analyse(self.m.blind_counts(bumped), d["cr"], m, self.m.LUMI, self.m.TF_SR, mu)
        np.testing.assert_array_equal(a["dsigma"], b["dsigma"])
        np.testing.assert_array_equal(a["total"], b["total"])

    def test_blinding_audit_with_synthetic_sentinel(self):
        """Seal the blinded signal-region count (acting as custodian, synthetic data only) and scan every output; a planted
        copy of a sealed number must be found (positive control)."""
        audit = PLUGIN / "skills" / "hep-computing" / "scripts" / "audit_blinded_outputs.py"
        d = self.m.pseudo_data(self.r["seed"])
        g = self.m.CFG["generator"]
        m = self.m.detector.response(self.m.CFG, g["shape_a"], g["shape_b"])["matrix"]
        mu = m @ (self.m.LUMI * self.m.expected_dsigma(g["sigma_pb"], g["shape_a"], g["shape_b"]) * self.m.WIDTH)
        refs = [mu + self.m.expected_background()["sr"], self.m.TF_SR * d["cr"]]
        with tempfile.TemporaryDirectory() as private:
            p = Path(private)
            (p / "hist.json").write_text(json.dumps({"edges": self.m.RE.tolist(), "values": d["sr"].tolist()}))
            ref_args = []
            for i, r in enumerate(refs):
                (p / f"ref{i}.json").write_text(json.dumps({"edges": self.m.RE.tolist(), "values": r.tolist()}))
                ref_args += ["--reference", str(p / f"ref{i}.json")]
            seal = subprocess.run([sys.executable, str(audit), "seal", "--hist", str(p / "hist.json"), "--low", "0.9", "--high", "1.0",
                                   *ref_args, "--out", str(p / "sealed.json")], capture_output=True, text=True, timeout=120)
            self.assertEqual(seal.returncode, 0, seal.stderr)
            exempt = ["--exempt", f"{self.out / 'dsigma_dcos.png'}=checked with core.blinding.check_figure in run.py"]
            scan = subprocess.run([sys.executable, str(audit), "scan", "--sealed", str(p / "sealed.json"), str(self.out), *exempt],
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(scan.returncode, 0, scan.stdout)
            self.assertEqual(json.loads(scan.stdout)["status"], "pass")
            # positive control: the blinded count planted in a copy of the outputs is found
            leak = Path(private) / "leak"
            leak.mkdir()
            (leak / "log.txt").write_text(f"bin 11 count {d['sr'][11]:.1f}\n")
            bad = subprocess.run([sys.executable, str(audit), "scan", "--sealed", str(p / "sealed.json"), str(leak)],
                                 capture_output=True, text=True, timeout=120)
            self.assertEqual(bad.returncode, 1, bad.stdout)

    def test_luminosity_normalization_and_artifacts(self):
        spec = json.loads((self.out / "artifacts" / "measurement_spec.json").read_text())
        norm = spec["extension"]["observable"]["normalization"]
        self.assertEqual((norm["kind"], norm["value"], norm["unit"]), ("integrated-luminosity", 20.0, "pb^-1"))
        self.assertTrue(all(c["ok"] for c in self.r["contract_validation"].values()))
        for f in (self.out / "artifacts").glob("*.json"):
            doc = json.loads(f.read_text())
            self.assertIn("synthetic", doc["status"])
            self.assertEqual([b["profile"] for b in doc["bindings"]["experiments"]], ["experiment:synthetic-collider"])
            self.assertEqual(doc["bindings"]["theory"], [])

    def test_only_the_illustrative_profile_is_loaded(self):
        self.assertEqual(self.r["profiles_loaded"], ["experiment:synthetic-collider"])
        text = SCRIPT.read_text()
        for forbidden in ("ams-02", "ams02", "profiles/theory", "qed"):
            self.assertNotIn(forbidden, text.lower())

    def test_labels(self):
        self.assertIn("SYNTHETIC", self.r["label"])
        self.assertIn("ILLUSTRATIVE", (self.out / "report.md").read_text().splitlines()[0])


if __name__ == "__main__":
    unittest.main()
