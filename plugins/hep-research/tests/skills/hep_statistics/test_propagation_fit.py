"""propagation_fit.py (cr-propagation C2): multi-dataset propagation fit through a cr-provider/1 provider.

Uses the closed-form provider of theory:cr-secondary-ratio (B/C bin-averaged in ln(E/n), convention crsr:bin_average)
on one SYNTHETIC Asimov dataset made here (8 bins, 5% uncorrelated + 3% fully correlated). Checks: Asimov recovery,
the refusals of C2-5 (missing covariance exit 3, out-of-domain start, bin-integrated data, modulation without isotopic
LIS), the loop limits of C2-6 (restart cap, toy-failure threshold, chain-step cap, posterior withheld below the ESS
limit), families outside the provider domain listed as not expressible, an exact D0/L degeneracy held for the
verdict, and the evaluation budget. The provider runs as a subprocess with a cache shared by the tests of this module
(about 200 provider point evaluations per run). The full end-to-end study is examples/propagation-fit/run.py.
"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "propagation_fit.py"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(SCRIPT.parent))

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    HAVE = True
except ImportError:  # pragma: no cover
    HAVE = False

PROVIDER = "cr-secondary-ratio-closed-form"
TRUTH = {"D0_cm2_s": 3.0e28, "delta": 0.5, "L_kpc": 4.0, "R0_gv": 1.0, "disc_halfwidth_pc": 100.0}


@unittest.skipUnless(HAVE, "needs numpy and scipy")
class PropagationFit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np

        from contracts import CONTRACTS_VERSION
        from core.provider.runner import ProviderRunner
        cls.tmp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.tmp.name)
        cls.registry = cls.work / "registry.json"
        cls.cache = cls.work / "cache"
        proc = subprocess.run([sys.executable, str(PLUGIN / "tools" / "provider_registry.py"), "--write",
                               str(cls.registry)], capture_output=True, text=True, timeout=300)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        edges = [float(f"{v:.12g}") for v in np.logspace(0.5, 2.5, 9)]
        req = {"protocol": "cr-provider/1", "provider": PROVIDER, "provider_version": "0.1.0", "points": [TRUTH],
               "observables": [{"id": "B/C", "axis": "ekn", "unit": "GeV/n",
                                "bins": [[a, b] for a, b in zip(edges, edges[1:])]}], "want": ["lis"], "seed": None}
        with ProviderRunner(str(cls.registry), cache_dir=cls.cache) as runner:
            pred = runner.evaluate(req)["results"][0]["predictions"][0]
        y = pred["values"]["values"]
        cls.record = {
            "contract_version": CONTRACTS_VERSION, "artifact_id": "propfit-test-asimov", "artifact_type": "dataset-record",
            "objective": "SYNTHETIC Asimov B/C points from the closed-form provider at an ILLUSTRATIVE truth point",
            "bindings": {"experiments": [], "theory": [{"profile": "theory:cr-secondary-ratio", "version": "0.1.0"}]},
            "versions": {"plugin": "", "contracts": CONTRACTS_VERSION, "profiles": {}},
            "provenance": {"producer_skill": "hep-statistics", "created": "2026-10-28", "evidence_ids": []},
            "inputs": [], "outputs": [], "status": ["synthetic", "asimov"], "unresolved_inputs": [],
            "extension": {"dataset_id": "synthetic:propfit-test", "source_evidence_ids": [],
                          "observable": copy.deepcopy(pred["observable"]),
                          "data": {"edges": pred["values"]["edges"], "values": y, "unit": "1",
                                   "uncertainties": [
                                       {"name": "statistical", "kind": "statistical", "correlation": "uncorrelated",
                                        "values": [0.05 * v for v in y]},
                                       {"name": "normalization", "kind": "systematic",
                                        "correlation": "fully-correlated", "values": [0.03 * v for v in y]}]},
                          "covariance": {"status": "present"}, "status": "synthetic"}}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def config(self, record=None, **extra):
        cfg = {"provider": {"id": PROVIDER, "version": "0.1.0"},
               "datasets": [{"name": "set-b", "measurement": record or self.record, "observable": "B/C"}],
               "parameters": {"D0_cm2_s": {"start": 2.5e28, "scale": "log"}, "delta": {"start": 0.45},
                              "L_kpc": {"start": 4.0, "scale": "log"}},
               "fixed": {"R0_gv": 1.0, "disc_halfwidth_pc": 100.0},
               "nuisances": [{"name": "xs-C-B", "kind": "production-norm", "channel": "C->B", "prior_sigma": 0.1}],
               "families": [{"name": "diffusion", "free": ["D0_cm2_s", "delta"], "fixed": {"L_kpc": 4.0}}],
               "response_model": {"nodes": 5, "validation_points": 4},
               "gate_plan": {"measurement_conditions": {"cross_section_set": "models/xs-illustrative-A.json"}}}
        cfg.update(extra)
        return cfg

    def cli(self, cfg, *flags):
        path = self.work / "config.json"
        path.write_text(json.dumps(cfg))
        proc = subprocess.run([sys.executable, str(SCRIPT), "fit", "--input", str(path), "--provider-registry",
                               str(self.registry), "--cache-dir", str(self.cache), *flags],
                              capture_output=True, text=True, timeout=900)
        self.assertNotIn("Traceback", proc.stderr, proc.stderr[-2000:])
        return proc.returncode, json.loads(proc.stdout)

    def fit(self, cfg, **kw):
        import propagation_fit as pf
        return pf.run(cfg, self.work, str(self.registry), cache_dir=self.cache, **kw)

    # ---------------------------------------------------------------- C2-1 (small), C2-4 shape
    def test_asimov_recovery_and_labels(self):
        res = self.fit(self.config())
        self.assertEqual(res["status"], "ok")
        fit = res["fits"][0]
        self.assertEqual(fit["convergence"]["status"], "converged")
        for p in fit["parameters"]:
            truth = TRUTH[p["name"]]
            coord = __import__("math").log(truth) if p["scale"] == "log" else truth
            self.assertLessEqual(abs(p["best_fit_coordinate"] - coord) / p["sigma_coordinate"], 0.1, p)
        self.assertLessEqual(abs(fit["nuisances"][0]["value"] - 1.0) / fit["nuisances"][0]["sigma"], 0.1)
        self.assertTrue(res["gate"][0]["comparable"])
        self.assertIn("synthetic", res["status_label"])
        self.assertIn("asimov", res["status_label"])
        self.assertEqual(res["channels"], ["C->B", "O->B"])

    def test_exact_degeneracy_is_held_and_reported_as_object(self):
        cfg = self.config(families=[{"name": "halo", "free": ["D0_cm2_s", "delta", "L_kpc"], "fixed": {}}])
        res = self.fit(cfg)
        fit = res["fits"][0]
        self.assertEqual(fit["status"], "converged")
        self.assertEqual(len(fit["convergence"]["held"]), 1)
        objs = fit["degenerate_directions"]
        self.assertTrue(objs and all(isinstance(o, dict) for o in objs))
        self.assertEqual(objs[0]["combination"], "D0_cm2_s/L_kpc")
        self.assertEqual(objs[0]["evidence"], "fisher-screen")
        self.assertNotIn("valid_range", objs[0])   # a screen sees only the neighbourhood of the best fit
        unconstrained = {p["name"] for p in fit["parameters"] if not p["constrained"]}
        self.assertEqual(unconstrained, {"D0_cm2_s", "L_kpc"})

    def test_families_outside_the_domain_are_listed(self):
        fams = [{"name": "BIG", "free": ["D0_cm2_s", "delta", "L_kpc", "V_A_kms", "V_c_kms", "R_break_gv",
                                         "delta_below", "s"], "fixed": {}},
                {"name": "diffusion", "free": ["D0_cm2_s", "delta"], "fixed": {"L_kpc": 4.0}}]
        res = self.fit(self.config(families=fams))
        self.assertEqual(res["families"]["not_expressible"], ["BIG"])
        reason = res["families_not_expressible"][0]["reason"]
        self.assertIn("V_A_kms", reason)
        self.assertEqual([f["family"] for f in res["fits"]], ["diffusion"])

    # ---------------------------------------------------------------- C2-5
    def test_missing_covariance_exits_3(self):
        rec = copy.deepcopy(self.record)
        rec["extension"]["data"]["uncertainties"] = []
        rec["extension"]["covariance"] = {"status": "not-provided"}
        code, out = self.cli(self.config(record=rec))
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "incomplete")
        self.assertEqual(out["missing"][0]["dataset"], "set-b")

    def test_out_of_domain_start_is_refused(self):
        cfg = self.config()
        cfg["parameters"]["D0_cm2_s"]["start"] = 5e30
        code, out = self.cli(cfg)
        self.assertEqual((code, out["status"], out["reason"]), (1, "failed", "out-of-domain"))

    def test_out_of_domain_truth_is_refused(self):
        cfg = self.config(toys={"family": "diffusion", "n": 20, "seed": 1, "truth": {"delta": 0.95},
                                "test": ["delta"]})
        code, out = self.cli(cfg)
        self.assertEqual((code, out["reason"]), (1, "out-of-domain"))

    def test_bin_integrated_data_are_refused(self):
        rec = copy.deepcopy(self.record)
        rec["extension"]["observable"]["bin_semantics"] = "bin-integrated"
        code, out = self.cli(self.config(record=rec))
        self.assertEqual((code, out["reason"]), (1, "bin-semantics-mismatch"))
        self.assertIn("P2", out["detail"])

    def test_unstated_condition_is_not_gated(self):
        cfg = self.config()
        cfg.pop("gate_plan")
        code, out = self.cli(cfg)
        self.assertEqual((code, out["reason"]), (1, "not-comparable"))
        self.assertIn("cross_section_set", out["detail"])

    def test_missing_binning_convention_is_refused(self):
        rec = copy.deepcopy(self.record)
        rec["extension"]["observable"]["conventions"].pop("crsr:bin_average")
        code, out = self.cli(self.config(record=rec))
        self.assertEqual((code, out["reason"]), (1, "bin-semantics-mismatch"))

    def test_modulation_needs_isotopic_lis(self):
        cfg = self.config()
        cfg["datasets"][0]["period"] = "p1"
        code, out = self.cli(cfg)
        self.assertEqual((code, out["reason"]), (1, "modulation-needs-isotopic-lis"))
        self.assertIn("phi_p1_gv", out["detail"])

    def test_unregistered_provider_and_refused_nuisances(self):
        cfg = self.config(provider={"id": "not-registered", "version": "1"})
        self.assertEqual(self.cli(cfg)[1]["reason"], "unregistered-provider")
        cfg = self.config(nuisances=[{"name": "inel", "kind": "inelastic-norm", "prior_sigma": 0.05}])
        self.assertEqual(self.cli(cfg)[1]["reason"], "nuisance-not-supported")
        cfg = self.config(nuisances=[{"name": "a", "kind": "production-norm", "channel": "O->B", "prior_sigma": 0.1},
                                     {"name": "b", "kind": "parent-abundance", "parent": "O", "prior_sigma": None}])
        code, out = self.cli(cfg)
        self.assertEqual(code, 2)
        self.assertIn("exactly degenerate", out["error"])

    def test_evaluation_budget(self):
        code, out = self.cli(self.config(), "--max-evaluations", "0")
        self.assertEqual((code, out["reason"]), (1, "evaluation-budget"))

    # ---------------------------------------------------------------- C2-6 loop limits
    def test_restart_cap(self):
        res = self.fit(self.config(optimizer={"max_iterations": 1}))
        fit = res["fits"][0]
        self.assertEqual(res["status"], "failed")
        self.assertEqual(fit["reason"], "restart-cap")
        self.assertEqual(fit["restarts"], 5)
        self.assertEqual(len(fit["attempts"]), 6)

    def test_toy_failure_threshold_stops_the_study(self):
        cfg = self.config(toys={"family": "diffusion", "n": 50, "seed": 3, "truth": {"D0_cm2_s": 3e28, "delta": 0.5},
                                "test": ["delta"], "max_iterations": 1})
        res = self.fit(cfg)
        toys = res["toys"]
        self.assertEqual((res["status"], toys["status"], toys["reason"]), ("failed", "failed", "toy-failure-threshold"))
        self.assertEqual(toys["failed"], 2)           # stops at the first count above 2% of 50
        self.assertEqual(toys["generated"], 2)
        self.assertNotIn("coverage_pass", toys)

    def test_chain_step_cap(self):
        code, out = self.cli(self.config(posterior={"family": "diffusion", "steps": 200001}))
        self.assertEqual((code, out["reason"]), (1, "chain-step-cap"))

    def test_short_chains_give_no_interval(self):
        res = self.fit(self.config(posterior={"family": "diffusion", "chains": 2, "steps": 200, "seed": 2}))
        post = res["posterior"]
        self.assertEqual(post["status"], "unvalidated")
        self.assertNotIn("intervals_68", post)
        self.assertLess(post["ess_min_seen"], 400)
        self.assertIn("unvalidated", res["status_label"])


if __name__ == "__main__":
    unittest.main()
