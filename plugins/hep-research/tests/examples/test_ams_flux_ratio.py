"""Path A (journey J1) regression tests: synthetic flux and correlated ratio with the AMS-02 profile.

Covers reproducibility, Asimov closure, toy closure with the default 400 seeded toys, the correlated ratio against an
independent propagation (T10), time-dependent exposure averaging (T11), contract validity and synthetic labeling, the
charge-sideband background with its closure and the blinded helium bin absent from every output (P4-2, sentinel audit).
All inputs are synthetic; passing says the chain is internally consistent, nothing about a real detector.
"""
import contextlib
import hashlib
import io
import importlib.util
import json
import math
import subprocess
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

    def test_matches_committed_output(self):
        """Deterministic values to rel 1e-9 / abs 1e-12. The toy-closure summary only to Monte Carlo precision (3
        standard errors of a unit-width pull mean and width): on another platform a last-digit difference in a
        Poisson or binomial rate can change how many uniforms one draw consumes, and every later toy then differs."""
        committed = json.loads((SCRIPT.parent / "output" / "results.json").read_text())
        n = committed["toys"]
        tol = {"mean_per_bin": 3 / math.sqrt(n), "width_per_bin": 3 / math.sqrt(2 * (n - 1))}

        def same(a, b, path="$"):
            if isinstance(a, float) or isinstance(b, float):
                self.assertTrue(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12), f"{path}: {a} != {b}")
            elif isinstance(a, dict) and isinstance(b, dict):
                self.assertEqual(sorted(a), sorted(b), path)
                for k in a:
                    same(a[k], b[k], f"{path}.{k}")
            elif isinstance(a, list) and isinstance(b, list):
                self.assertEqual(len(a), len(b), path)
                for i, (x, y) in enumerate(zip(a, b)):
                    same(x, y, f"{path}[{i}]")
            else:
                self.assertEqual(a, b, path)

        run_toys, ref_toys = self.results["toy_closure"], committed["toy_closure"]
        same({k: v for k, v in self.results.items() if k != "toy_closure"}, {k: v for k, v in committed.items() if k != "toy_closure"})
        self.assertEqual(sorted(run_toys), sorted(ref_toys))
        for key in ref_toys:
            for stat, t in tol.items():
                for i, (x, y) in enumerate(zip(run_toys[key][stat], ref_toys[key][stat], strict=True)):
                    self.assertLessEqual(abs(x - y), t, f"toy_closure.{key}.{stat}[{i}]: {x} vs {y}")

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
        self.assertEqual(len(files), 8)  # spec, four responses (species x period), ratio result, two datasets
        for f in files:
            doc = json.loads(f.read_text())
            self.assertIn("synthetic", doc["status"], f.name)
            self.assertTrue(doc["artifact_id"].startswith("synthetic-"), f.name)
        spec = json.loads((self.out / "artifacts" / "measurement_spec.json").read_text())
        params = spec["extension"]["experiment_fields"]["ams02:parameters"]
        self.assertEqual({p["provenance"] for p in params}, {"documented", "proposal"})
        self.assertIn("ams02:C31", spec["provenance"]["evidence_ids"])

    def test_background_charge_sideband_estimate_and_closure(self):
        m, b = self.m, self.results["background"]
        # exponential tail above 1.3 with slope 0.2: window [1.7, 2.5) over sideband [1.3, 1.6)
        tail = lambda lo, hi: math.exp(-(lo - 1.3) / 0.2) - math.exp(-(hi - 1.3) / 0.2)  # noqa: E731
        self.assertAlmostEqual(b["transfer_factor_window"], tail(1.7, 2.5) / tail(1.3, 1.6), places=12)
        self.assertAlmostEqual(b["transfer_factor_validation_band"], tail(1.6, 1.7) / tail(1.3, 1.6), places=12)
        self.assertLess(b["asimov_closure_max_rel_dev"], 1e-12)
        for p in m.PERIODS:
            for est, cr, blinded in zip(b["estimate_window"][p], b["sideband_counts"][p], m.BLINDED):
                if blinded:
                    self.assertIsNone(est)
                else:
                    self.assertAlmostEqual(est, b["transfer_factor_window"] * cr, places=9)
            v = b["validation_closure"][p]
            self.assertLess(abs(v["total_pull"]), 3.0, p)
            self.assertGreater(v["p_value"], 1e-3, p)
            # the background is a visible part of the helium window, not a no-op subtraction
            he = [x for x in self.results["observed_counts"][f"helium/{p}"] if x is not None]
            self.assertGreater(sum(x for x in b["estimate_window"][p] if x is not None) / sum(he), 0.02, p)
        spec = json.loads((self.out / "artifacts" / "measurement_spec.json").read_text())["extension"]
        self.assertEqual(len(spec["backgrounds"]), 1)
        self.assertNotIn("no_backgrounds_reason", spec)
        self.assertIn("1.3 <= Q < 1.6", spec["backgrounds"][0]["control_region"])
        self.assertIn("validation band", spec["backgrounds"][0]["closure"])
        self.assertIn("background_transfer_factor", [s["name"] for s in spec["systematics"]])

    def test_subtraction_is_unbiased_on_the_expectation(self):
        """Asimov input with the background: helium and ratio return the truth exactly; without the subtraction they
        would be biased by the leak fraction."""
        m, w = self.m, self.world
        sim = m.simulate(None, w, asimov=True)
        res = m.run_analysis(sim, w)
        for p in m.PERIODS:
            np.testing.assert_allclose(res[("helium", p)]["flux"][m.REPORTED], w["helium"][p]["truth_flux"][m.REPORTED], rtol=1e-9)
        sim["sideband"] = {p: 0 * v for p, v in sim["sideband"].items()}
        biased = m.run_analysis(sim, w)
        p = next(iter(m.PERIODS))
        self.assertGreater(np.max(biased[("helium", p)]["flux"][m.PUBLISHED] / w["helium"][p]["truth_flux"][m.PUBLISHED] - 1), 0.02)

    def test_blinded_bin_is_absent_from_the_outputs(self):
        m, r = self.m, self.results
        blinded = [j for j, b in enumerate(m.BLINDED) if b]
        self.assertEqual(blinded, [9])  # 60-100 GV
        self.assertEqual(r["blinding"]["blinded_bins"], blinded)
        self.assertFalse(r["blinding"]["unblinded"])
        j = blinded[0]
        for p in m.PERIODS:
            self.assertIsNone(r["observed_counts"][f"helium/{p}"][j])
            self.assertIsNotNone(r["observed_counts"][f"proton/{p}"][j])  # proton counts stay open
            for vals, cov in ((r["flux"][f"helium/{p}"]["values"], r["flux"][f"helium/{p}"]["covariance"]["total"]),
                              (r["ratio"][p]["values"], r["ratio"][p]["covariance"])):
                self.assertIsNone(vals[j])
                self.assertTrue(all(x is None for x in cov[j]) and all(row[j] is None for row in cov))
            released = json.loads((self.out / r["blinding"]["released_helium_histograms"][p]).read_text())
            self.assertEqual(released["status"], "synthetic")
            self.assertIsNone(released["values"][j])
            self.assertIsNone(released["ratio_to_reference"][j])
            ds = json.loads((self.out / "artifacts" / f"dataset_{p}.json").read_text())["extension"]["data"]
            self.assertEqual(ds["edges"][-1], 60.0)
            self.assertEqual(len(ds["values"]), len(ds["edges"]) - 1)
        self.assertIsNone(r["time_average_T11"]["helium"]["average_flux"][j - m.REPORTED.start])
        spec = json.loads((self.out / "artifacts" / "measurement_spec.json").read_text())
        bl = spec["extension"]["blinding"]
        self.assertTrue(bl["blinded"])
        self.assertEqual(bl["mask"]["intervals"], [{"variable": "rigidity", "low": 60.0, "high": 100.0}])
        self.assertIsNone(bl["unblinding_record_ref"])
        self.assertNotIn("observed", spec["status"])
        self.assertEqual(r["blinding"]["figure_check"]["status"], "pass")

    def test_blinding_audit_with_synthetic_sentinel(self):
        """Rerun with synthetic sentinels in place of the blinded helium counts: every output is byte-identical to the
        normal run (no published number depends on them), and audit_blinded_outputs.py, sealing each period's sentinel
        histogram as the custodian would, finds none of the sealed numbers. A planted sentinel is found (positive
        control). Sentinels avoid the false hits that short integer counts give."""
        m = self.m
        sentinels = dict(zip(m.PERIODS, (987654.321, 876543.219)))
        real = m.pseudo_data

        def planted(seed, world):
            sim = real(seed, world)
            for p, v in sentinels.items():
                sim["counts"][("helium", p)][m.BLINDED] = v
            return sim
        sent_out = Path(self.tmp.name) / "sentinel"
        m.pseudo_data = planted
        try:
            self.assertEqual(run(m, "--out", str(sent_out)), 0)
        finally:
            m.pseudo_data = real
        files = sorted(p.relative_to(self.out) for p in self.out.rglob("*") if p.is_file())
        self.assertEqual(files, sorted(p.relative_to(sent_out) for p in sent_out.rglob("*") if p.is_file()))
        for f in files:
            self.assertEqual((self.out / f).read_bytes(), (sent_out / f).read_bytes(), str(f))

        audit = PLUGIN / "skills" / "hep-computing" / "scripts" / "audit_blinded_outputs.py"
        sim = planted(self.results["seed"], self.world)
        exempt = []
        for png in ("flux_per_period.png", "ratio_per_period.png"):
            exempt += ["--exempt", f"{sent_out / png}=checked with core.blinding.check_figure in run.py"]
        with tempfile.TemporaryDirectory() as private:
            d = Path(private)
            for p in m.PERIODS:
                w = self.world["helium"][p]
                refs = [w["expected_reco"] + w["leak"]["window"], m.TF_SR * sim["sideband"][p]]
                (d / f"{p}.json").write_text(json.dumps({"edges": m.EDGES.tolist(), "values": sim["counts"][("helium", p)].tolist()}))
                args = []
                for i, ref in enumerate(refs):
                    (d / f"{p}-ref{i}.json").write_text(json.dumps({"edges": m.EDGES.tolist(), "values": ref.tolist()}))
                    args += ["--reference", str(d / f"{p}-ref{i}.json")]
                seal = subprocess.run([sys.executable, str(audit), "seal", "--hist", str(d / f"{p}.json"), "--low", "60", "--high", "100",
                                       *args, "--out", str(d / f"{p}-sealed.json")], capture_output=True, text=True, timeout=120)
                self.assertEqual(seal.returncode, 0, seal.stderr)
                scan = subprocess.run([sys.executable, str(audit), "scan", "--sealed", str(d / f"{p}-sealed.json"), str(sent_out), *exempt],
                                      capture_output=True, text=True, timeout=120)
                self.assertEqual(scan.returncode, 0, scan.stdout)
                self.assertEqual(json.loads(scan.stdout)["status"], "pass")
            leak = d / "leak"
            leak.mkdir()
            (leak / "log.txt").write_text(f"helium 60-100 GV: {sentinels[next(iter(m.PERIODS))]}\n")
            bad = subprocess.run([sys.executable, str(audit), "scan", "--sealed", str(d / f"{next(iter(m.PERIODS))}-sealed.json"), str(leak)],
                                 capture_output=True, text=True, timeout=120)
            self.assertEqual(bad.returncode, 1, bad.stdout)

    def test_documented_profile_validation_command_works(self):
        """P4-3: the report names the command; with a project config outside the plugin it exits 0."""
        report = (self.out / "report.md").read_text()
        self.assertIn("--profiles-from", report)
        with tempfile.TemporaryDirectory() as proj:
            cfg = Path(proj) / "hep-research.project.json"
            profile = json.loads((PLUGIN / "profiles" / "experiments" / "ams-02" / "profile.json").read_text())
            cfg.write_text(json.dumps({"schema_version": "1.0.0", "plugin_version": ">=0.6,<1.0",
                                       "experiments": [{"profile": "experiment:ams-02", "version": profile["version"]}],
                                       "theory": []}))
            spec = self.out / "artifacts" / "measurement_spec.json"
            plain = subprocess.run([sys.executable, str(PLUGIN / "contracts" / "validate.py"), str(spec)],
                                   capture_output=True, text=True, timeout=120)
            bound = subprocess.run([sys.executable, str(PLUGIN / "contracts" / "validate.py"), str(spec),
                                    "--profiles-from", str(cfg)], capture_output=True, text=True, timeout=120)
            self.assertEqual(plain.returncode, 1)
            self.assertIn("--profiles-from", plain.stdout)
            self.assertEqual(bound.returncode, 0, bound.stdout)

    def test_outputs_carry_synthetic_label(self):
        self.assertTrue(self.results["label"].startswith("SYNTHETIC"))
        self.assertIn("(SYNTHETIC)", (self.out / "report.md").read_text().splitlines()[0])
        for png in ("flux_per_period.png", "ratio_per_period.png"):
            self.assertTrue((self.out / png).stat().st_size > 1000)


if __name__ == "__main__":
    unittest.main()
