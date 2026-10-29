"""propagation_fit.py (cr-propagation C2): multi-dataset propagation fit through a cr-provider/1 provider.

Uses the closed-form provider of theory:cr-secondary-ratio (B/C bin-averaged in ln(E/n), convention crsr:bin_average)
on one SYNTHETIC Asimov dataset made here (8 bins, 5% uncorrelated + 3% fully correlated). Checks: Asimov recovery,
the refusals of C2-5 (missing covariance exit 3, out-of-domain start, bin-integrated data, modulation without isotopic
LIS), the loop limits of C2-6 (restart cap, toy-failure threshold, chain-step cap, posterior withheld below the ESS
limit), families outside the provider domain listed as not expressible, an exact D0/L degeneracy held for the
verdict, and the evaluation budget. The provider runs as a subprocess with a cache shared by the tests of this module
(about 200 provider point evaluations per run). The full end-to-end study is examples/propagation-fit/run.py.

The USINE case (C2U) is checked from the study recorded by usine_family_study.py (fixture
tests/adapters/fixtures/cr_propagation/c2u/usine-family-study.json): BIG and SLIM fitted with the USINE provider to
SYNTHETIC Asimov B/C data from BIG, Asimov recovery with a boundary parameter (C2U-1), the provider's evaluation
records and out-of-domain refusals (C2U-2), toy-calibrated delta chi2 of both families on a response model validated
against the provider (C2U-3), and the bin-semantics guard for USINE's P2 values. These run offline; with
HEP_USINE_LIVE_TEST=1 (and HEP_USINE_BIN, HEP_USINE_DATA) one live test refits SLIM with USINE (about 30 runs) and
compares it with the record. C2U's family calibration was refused (recorded, asserted as such); C2U-3 moved to C2UF-1
(decision A1.12), checked from the study recorded by usine_two_dataset_family_study.py (fixture
tests/adapters/fixtures/cr_propagation/c2uf/usine-two-dataset-family-study.json): B/C and 10Be/9Be from one USINE run
per point, BIG and SLIM fitted with the provider; the recorded polynomial response model was refused (0.452 sigma >
0.05). C2UF-1 is met in the emulator study (usine_emulator_family_study.py, fixture usine-emulator-family-study.json,
decision A1.14; since L1, decision B1.3, K4's retraining with the kernel condition bound 1e10 and V_A_kms declared
enters_squared): a Gaussian-process emulator of USINE validated on 40 held-out USINE runs (largest error 0.0032 sigma),
its error in the covariance, BIG and SLIM fitted with the emulator provider and calibrated with 200 toys each (no
failed toy), BIG surviving. With HEP_USINE_LIVE_TEST=1 live tests rerun the truth point (one USINE run) and compare the emulator with
two fresh USINE runs.
"""
import copy
import json
import math
import os
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
USINE_RECORD = PLUGIN / "tests" / "adapters" / "fixtures" / "cr_propagation" / "c2u" / "usine-family-study.json"
TWO_DATASET_RECORD = (PLUGIN / "tests" / "adapters" / "fixtures" / "cr_propagation" / "c2uf"
                      / "usine-two-dataset-family-study.json")
EMULATOR_RECORD = TWO_DATASET_RECORD.parent / "usine-emulator-family-study.json"
LIVE = os.environ.get("HEP_USINE_LIVE_TEST") == "1"
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

    def test_provider_side_modulation_needs_the_declared_modulation_block(self):
        """F1, K2 (contracts 3.15.0): a period is accepted when the provider's declaration carries a modulation block
        listing phi_<period>_gv (phi in the domain alone is refused by the registry); the phi must then be fitted or
        fixed, and each dataset's requests carry only its own period's phi."""
        import propagation_fit as pf
        reg = json.loads(self.registry.read_text())
        decl = next(i["declaration"] for i in reg["providers"] if i["declaration"]["id"] == PROVIDER)
        decl["domain"]["phi_p1_gv"] = {"min": 0.0, "max": 2.0}
        cfg = self.config()
        cfg["datasets"][0]["period"] = "p1"
        with self.assertRaises(pf.FitInputError) as ctx:   # phi in the domain without a modulation block
            pf.run(cfg, self.work, reg, cache_dir=self.cache)
        self.assertIn("modulation block", str(ctx.exception))
        decl["modulation"] = {"model": "force-field", "implementation": "SYNTHETIC force field per isotope",
                              "parameters": ["phi_p1_gv"],
                              "conformance": {"reference_point": {"delta": 0.5, "phi_p1_gv": 0.5},
                                              "observables": [{"id": "B/C", "axis": "ekn", "unit": "GeV/n",
                                                               "bins": [[1.0, 10.0]]}],
                                              "tolerance": 1e-3,
                                              "result": {"status": "passed", "max_relative_deviation": 1e-5,
                                                         "nodes_compared": 10, "isotopes": ["11B", "12C"],
                                                         "tool": "SYNTHETIC"}}}
        with self.assertRaises(pf.FitInputError) as ctx:   # phi neither fitted nor fixed
            pf.run(cfg, self.work, reg, cache_dir=self.cache)
        self.assertIn("phi_p1_gv", str(ctx.exception))
        cfg["fixed"]["phi_p1_gv"] = 0.5
        with self.assertRaises(pf.FitRefused) as ctx:   # passes the period check; the closed form refuses the phi
            pf.run(cfg, self.work, reg, cache_dir=self.cache)
        self.assertNotEqual(ctx.exception.reason, "modulation-needs-isotopic-lis")

        class Ds:
            def __init__(self, name, period):
                self.name, self.period = name, period
        toa = ({"observable": {"level": "top-of-atmosphere"}},)
        lis = ({"observable": {"level": "crsr:local-interstellar"}},)
        pf._refuse_double_modulation([Ds("a", "p1"), Ds("c", None)], {"a": toa, "c": lis}, True, PROVIDER)
        for dsets, first, modulates in (([Ds("c", None)], {"c": toa}, True), ([Ds("a", "p1")], {"a": toa}, False)):
            with self.assertRaises(pf.FitRefused) as ctx:   # a modulated value the fit did not ask for
                pf._refuse_double_modulation(dsets, first, modulates, PROVIDER)
            self.assertEqual(ctx.exception.reason, "double-modulation")
        ev = pf.Evaluator(None, PROVIDER, "0.1.0", [Ds("a", "p1"), Ds("b", "p2"), Ds("c", None)], {}, 10)
        pt = {"delta": 0.5, "phi_p1_gv": 0.4, "phi_p2_gv": 0.6}
        self.assertEqual(ev.group_point(pt, [ev.datasets[0]]), {"delta": 0.5, "phi_p1_gv": 0.4})
        self.assertEqual(ev.group_point(pt, [ev.datasets[1]]), {"delta": 0.5, "phi_p2_gv": 0.6})
        self.assertEqual(ev.group_point(pt, [ev.datasets[2]]), {"delta": 0.5})
        self.assertEqual(ev.group_point(pt, ev.datasets), pt)   # per-point: every period of the group kept

    def test_parameter_priors(self):
        """F1: parameters.<name>.prior adds ((p - mean)/sigma)^2; a tight prior holds the parameter at its mean, a
        wide one leaves the Asimov recovery; it counts in the dof; response-model studies refuse it."""
        tight = self.config()
        tight["parameters"]["delta"]["prior"] = {"mean": 0.45, "sigma": 1e-4}
        fit = self.fit(tight)["fits"][0]
        p = {q["name"]: q for q in fit["parameters"]}
        self.assertAlmostEqual(p["delta"]["best_fit"], 0.45, delta=2e-4)
        self.assertGreater(fit["chi2"], fit["chi2_parameter_priors"])
        self.assertLess(abs(p["delta"]["prior"]["pull"]), 2.0)
        self.assertLess(p["delta"]["sigma_coordinate"], 2e-4)   # the prior enters the Fisher matrix
        wide = self.config()
        wide["parameters"]["delta"]["prior"] = {"mean": 0.5, "sigma": 10.0}
        base = self.fit(self.config())["fits"][0]
        fit = self.fit(wide)["fits"][0]
        self.assertEqual(fit["dof"], base["dof"] + 1)
        self.assertAlmostEqual({q["name"]: q for q in fit["parameters"]}["delta"]["best_fit"], 0.5, delta=1e-3)
        bad = self.config()
        bad["parameters"]["delta"]["prior"] = {"mean": 0.5, "sigma": 0.0}
        self.assertEqual(self.cli(bad)[0], 2)
        toys = self.config(toys={"n": 10, "seed": 1, "test": ["delta"]})
        toys["parameters"]["delta"]["prior"] = {"mean": 0.5, "sigma": 0.1}
        code, out = self.cli(toys)
        self.assertEqual((code, out["reason"]), (1, "parameter-priors-not-supported"))

    def test_polish_steps_before_the_verdict(self):
        """F1: optimizer.polish_steps takes Newton steps with the verdict's central differences before judging; the
        polished fit still recovers the Asimov truth and records the steps."""
        cfg = self.config(optimizer={"max_iterations": 100, "max_restarts": 0, "seed": 0, "polish_steps": 1})
        cfg["parameters"]["D0_cm2_s"]["step"] = 0.01
        cfg["parameters"]["delta"]["step"] = 0.002
        fit = self.fit(cfg)["fits"][0]
        self.assertEqual(fit["status"], "converged")
        self.assertEqual(fit["attempts"][0]["polish_steps"], 1)
        for q in fit["parameters"]:
            truth = math.log(TRUTH[q["name"]]) if q["scale"] == "log" else TRUTH[q["name"]]
            self.assertLessEqual(abs(q["best_fit_coordinate"] - truth) / q["sigma_coordinate"], 0.1, q)
        bad = self.config(optimizer={"polish_steps": 9})
        self.assertEqual(self.cli(bad)[0], 2)

    # ---------------------------------------------------------------- K1: noise-aware convergence (opt-in)
    def test_noise_free_fit_is_unchanged_without_optimizer_noise(self):
        """K1-1: without optimizer.noise nothing is added and the threshold is fit_diagnostics' 1e-5; a noise-free
        provider with a measured noise floor keeps that threshold (0.5 x its tiny floor is below 1e-5) and its
        verdict and numbers."""
        import propagation_fit as pf
        from core.stats.fit_diagnostics import EDM_TOL
        self.assertEqual(pf.EDM_TOL_BASE, EDM_TOL)
        self.assertNotIn("noise", pf._opt_cfg({}))
        plain = self.fit(self.config())["fits"][0]
        self.assertNotIn("noise", plain)
        self.assertNotIn("edm_threshold", plain["convergence"])
        measured = self.fit(self.config(optimizer={"noise": {"mode": "measure"}}))["fits"][0]
        noise = measured["noise"]
        self.assertEqual((noise["mode"], noise["evaluations"], noise["dof"]), ("measure", 8, 4))
        self.assertLess(noise["sigma_m2lnl"], 2e-5)
        self.assertEqual(measured["convergence"]["edm_threshold"], EDM_TOL)
        self.assertEqual(measured["status"], plain["status"])
        for a, b in zip(plain["parameters"], measured["parameters"]):
            self.assertLessEqual(abs(a["best_fit_coordinate"] - b["best_fit_coordinate"]),
                                 1e-9 * max(1.0, abs(a["best_fit_coordinate"])))
        self.assertLessEqual(abs(plain["chi2"] - measured["chi2"]), 1e-9 * max(1.0, plain["chi2"]))

    def test_declared_noise_sets_the_threshold_and_is_validated(self):
        fit = self.fit(self.config(optimizer={"noise": {"mode": "declared", "sigma_m2lnl": 0.004}}))["fits"][0]
        self.assertEqual(fit["noise"]["mode"], "declared")
        self.assertLessEqual(abs(fit["convergence"]["edm_threshold"] - 0.002), 1e-12)
        self.assertEqual(fit["status"], "converged")
        self.assertEqual(len(fit["noise"]["steps"]), 2)
        for bad in ({"mode": "declared", "sigma_m2lnl": 0.0}, {"mode": "guess"}, {"mode": "measure", "k": 1}):
            self.assertEqual(self.cli(self.config(optimizer={"noise": bad}))[0], 2, bad)

    def test_rejected_polish_judges_the_returned_point(self):
        """K1 polish fix: a polished point with a higher -ln L than the optimizer's is discarded, and the verdict
        is then on the point actually returned (judged again without polish)."""
        from unittest import mock

        import propagation_fit as pf
        real = pf._verdict
        calls = []

        def worse(nll, x, bounds, held, steps=None, polish=0, **kw):
            out = real(nll, x, bounds, held, steps, polish, **kw)
            calls.append(polish)
            if polish:   # pretend the Newton step went uphill by a quarter of the box
                out["x"] = [v + 0.25 * (b - a) for v, (a, b) in zip(x, bounds)]
                out["status"], out["reasons"] = "failed", ["gradient_not_small"]
            return out
        cfg = self.config(optimizer={"max_iterations": 100, "max_restarts": 0, "seed": 0, "polish_steps": 1})
        plain = self.fit(self.config(optimizer={"max_iterations": 100, "max_restarts": 0, "seed": 0}))["fits"][0]
        with mock.patch.object(pf, "_verdict", worse):
            fit = self.fit(cfg)["fits"][0]
        self.assertEqual(calls, [1, 0])
        self.assertIn("rejected", fit["convergence"]["polish"])
        self.assertEqual(fit["status"], "converged")
        self.assertEqual(fit["convergence"]["edm"], plain["convergence"]["edm"])
        self.assertEqual(fit["best_fit_coordinates"], plain["best_fit_coordinates"])

    def test_unconverged_fit_reports_not_converged(self):
        """K1: an unconverged fit without restarts has reason not-converged (not restart-cap), and the CLI with --out
        reports it and writes no statistical-result instead of exiting with artifact-invalid."""
        cfg = self.config(optimizer={"max_iterations": 1, "max_restarts": 0})
        with tempfile.TemporaryDirectory() as out:
            code, doc = self.cli(cfg, "--out", out)
            self.assertEqual((code, doc["status"], doc["reason"]), (1, "failed", "not-converged"))
            self.assertEqual(doc["fits"][0]["reason"], "not-converged")
            self.assertFalse((Path(out) / "statistical-result.json").exists())
            self.assertTrue((Path(out) / "result.json").is_file())
            self.assertIn("no fit converged: statistical-result.json is not written", doc["warnings"])

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

    def test_polynomial_response_model(self):
        cfg = self.config(response_model={"kind": "polynomial", "degree": 3, "design_points": 24,
                                          "validation_points": 4},
                          toys={"family": "diffusion", "n": 20, "seed": 4, "truth": {"D0_cm2_s": 3e28, "delta": 0.5},
                                "test": ["delta"]})
        res = self.fit(cfg)
        toys = res["toys"]
        self.assertEqual(toys["status"], "ok", toys.get("detail"))
        rm = toys["response_model"]
        self.assertEqual((rm["kind"], rm["degree"], rm["terms"]), ("total-degree polynomial", 3, 10))
        self.assertTrue(rm["validation"]["passed"])
        self.assertEqual(len(toys["rows"]), 20)            # per-toy rows are kept
        cfg["response_model"]["design_points"] = 10        # fewer than twice the 10 terms
        code, out = self.cli(cfg)
        self.assertEqual(code, 2)
        self.assertIn("design_points", out["error"])

    def test_statistical_result_records_the_toy_seed(self):
        import propagation_fit as pf
        from contracts.validate import validate_artifact
        res = self.fit(self.config(toys={"family": "diffusion", "n": 20, "seed": 9,
                                         "truth": {"D0_cm2_s": 3e28, "delta": 0.5}, "test": ["delta"]}))
        sr = pf.statistical_result_artifact(res, res["status_label"])
        self.assertEqual(sr["extension"]["coverage"]["seed"], 9)
        self.assertEqual(sr["extension"]["seeds"]["coverage_toys"], 9)
        rep = validate_artifact(sr)
        self.assertTrue(rep.ok)
        self.assertNotIn("stats.seed_missing", json.dumps(rep.as_dict()))

    def test_multipliers_stay_in_their_bounds(self):
        import numpy as np

        import propagation_fit as pf
        # a design whose unbounded solution is negative is solved within NU_BOUNDS
        model = object.__new__(pf.Model)
        model.n_nu, model.nuisances = 1, [{"prior_sigma": None, "aux": 1.0}]
        model.datasets = [type("D", (), {"name": "d", "y": np.array([-1.0, -2.0]), "chol": np.eye(2)})()]
        model.assign = np.array([[1.0]])
        r, nu = model.profiled({"d": np.array([[1.0, 2.0]])})
        self.assertAlmostEqual(float(nu[0]), pf.NU_BOUNDS[0])

    def test_difference_jacobian_uses_the_stated_steps(self):
        import numpy as np

        import propagation_fit as pf
        calls = []

        def fun(t):
            calls.append(np.array(t))
            return np.array([t[0] ** 2, 3 * t[1]])
        jac = pf._difference_jacobian(fun, [0.5, None], [0, 0], [1.0, 10])
        J = jac(np.array([0.8, 2.0]))
        self.assertAlmostEqual(calls[1][0], 0.3)            # backward step at the upper bound
        self.assertAlmostEqual(J[0, 0], (0.64 - 0.09) / 0.5)
        self.assertAlmostEqual(J[1, 1], 3.0, places=6)
        self.assertEqual(pf._difference_jacobian(fun, None, [0], [1]), "2-point")

    def test_per_center_response_models_for_the_family_calibration(self):
        fams = [{"name": "diffusion", "free": ["D0_cm2_s", "delta"], "fixed": {"L_kpc": 4.0}},
                {"name": "stiff", "free": ["D0_cm2_s"], "fixed": {"L_kpc": 4.0, "delta": 0.45}}]
        cfg = self.config(families=fams, response_model={"kind": "polynomial", "degree": 3, "design_points": 24,
                                                         "validation_points": 4, "layout": "per-center"},
                          family_toys={"n": 20, "seed": 5, "alpha": 0.05})
        res = self.fit(cfg)
        cal = res["family_calibration"]
        self.assertEqual(cal["status"], "ok", cal.get("detail"))
        rm = cal["response_model"]
        self.assertEqual((rm["layout"], len(rm["sub_models"])), ("per-center", 2))
        self.assertEqual([m["center_of"] for m in rm["sub_models"]], ["diffusion", "stiff"])
        self.assertTrue(rm["validation"]["passed"])
        self.assertEqual(rm["validation"]["max_error_over_sigma"],
                         max(m["validation"]["max_error_over_sigma"] for m in rm["sub_models"]))
        pairs = {(a["null"], a["family"]): a["sub_model"] for a in rm["assignment"]}
        self.assertEqual(len(pairs), 4)
        self.assertEqual((pairs[("diffusion", "diffusion")], pairs[("stiff", "stiff")]), (0, 1))
        self.assertEqual({e["family"] for e in cal["families"]}, {"diffusion", "stiff"})
        self.assertTrue(all(len(e["rows"]) == 20 for e in cal["families"]))
        cfg["response_model"]["layout"] = "nested"
        self.assertEqual(self.cli(cfg)[0], 2)
        cfg["response_model"]["layout"] = "joint"            # one box: every best fit +- k x the largest sigma
        cal = self.fit(cfg)["family_calibration"]
        self.assertEqual(cal["status"], "ok", cal.get("detail"))
        self.assertEqual((cal["response_model"]["layout"], len(cal["response_model"]["box_passes"])), ("joint", 1))
        self.assertTrue(cal["response_model"]["validation"]["passed"])

    def test_provider_kind_evaluates_the_provider_in_the_toys(self):
        fams = [{"name": "diffusion", "free": ["D0_cm2_s", "delta"], "fixed": {"L_kpc": 4.0}},
                {"name": "stiff", "free": ["D0_cm2_s"], "fixed": {"L_kpc": 4.0, "delta": 0.45}}]
        cfg = self.config(families=fams, response_model={"kind": "provider", "layout": "joint",
                                                         "half_width_sigma": 4},
                          family_toys={"n": 20, "seed": 6, "alpha": 0.05})
        res = self.fit(cfg, max_evaluations=100000)
        cal = res["family_calibration"]
        self.assertEqual(cal["status"], "ok", cal.get("detail"))
        rm = cal["response_model"]
        self.assertEqual((rm["kind"], rm["provider_evaluations"]), ("provider (no response model)", 0))
        self.assertEqual(rm["validation"]["max_error_over_sigma"], 0.0)
        self.assertTrue(all(len(e["rows"]) == 20 for e in cal["families"]))
        self.assertGreater(res["provider_evaluations"]["points_sent"], 100)   # the toys called the provider

    def test_per_point_requests_send_one_request_for_every_dataset(self):
        import numpy as np

        import propagation_fit as pf

        class Runner:
            def __init__(self):
                self.stats, self.requests = {"points_sent": 0}, []

            def evaluate(self, req):
                self.requests.append(req)
                self.stats["points_sent"] += len(req["points"])
                preds = [{"values": {"edges": [o["bins"][0][0]] + [b for _, b in o["bins"]],
                                     "values": [float(k + 1) for k in range(len(o["bins"]))]}}
                         for o in req["observables"]]
                return {"status": "ok", "results": [{"status": "ok", "labels": ["synthetic"], "predictions": preds,
                                                     "evaluation": {"input_hash": "h", "numerical_tolerance": 0.0}}]}

        def ds(name, obs, edges):
            d = object.__new__(pf.Dataset)
            d.name, d.observable, d.axis, d.unit, d.edges = name, obs, "ekn", "GeV/n", edges
            d.y = np.ones(len(edges) - 1)
            return d
        sets = [ds("bc", "B/C", [1.0, 2.0, 4.0]), ds("be", "10Be/9Be", [0.1, 1.0])]
        runner = Runner()
        ev = pf.Evaluator(runner, "p", "1", sets, {}, 10, decomposable=False, per_point=True)
        out = ev.components({"delta": 0.5})
        self.assertEqual(len(runner.requests), 1)
        self.assertEqual([o["id"] for o in runner.requests[0]["observables"]], ["B/C", "10Be/9Be"])
        self.assertEqual(out["bc"].tolist(), [[1.0, 2.0]])
        self.assertEqual(out["be"].tolist(), [[1.0]])
        self.assertEqual(ev.records[0]["datasets"], ["bc", "be"])
        self.assertEqual(ev.points_sent, 1)
        with self.assertRaises(pf.FitInputError):      # equal ids would make the predictions ambiguous
            pf._per_point_requests({"provider_requests": "per-point"}, [sets[0], ds("bc2", "B/C", [1.0, 2.0])],
                                   False)
        with self.assertRaises(pf.FitInputError):
            pf._per_point_requests({"provider_requests": "per-point"}, sets, True)
        self.assertFalse(pf._per_point_requests({}, sets, False))


def _noisy_quadratic(sigma_f, curvature, center, seed):
    """-ln L = (t - c)^T A (t - c) / 2 plus deterministic noise of standard deviation sigma_f, uncorrelated between
    distinct points (a hash of the point, like the rounding of a deterministic provider's printed tables)."""
    import hashlib
    from statistics import NormalDist

    import numpy as np
    A, c = np.asarray(curvature, dtype=float), np.asarray(center, dtype=float)

    def f(t):
        key = repr((seed,) + tuple(float(v) for v in t)).encode()
        u = (int(hashlib.sha256(key).hexdigest()[:13], 16) + 0.5) / 16 ** 13
        d = np.asarray(t, dtype=float) - c
        return 0.5 * float(d @ A @ d) + sigma_f * NormalDist().inv_cdf(u)
    return f


@unittest.skipUnless(HAVE, "needs numpy and scipy")
class NoiseAwareConvergence(unittest.TestCase):
    """K1-1 on a synthetic noisy objective with known noise (VALIDATION.md CRPROP-K1): the stencil measures the noise,
    the noise-sized steps keep the noise part of EDM below sigma_f / 16 on average, and the verdict flips correctly
    (a true minimum converges under the rule and fails fit_diagnostics' 1e-5; a point 20 sigma_f in EDM away fails)."""
    SIGMA_F = 5e-4   # noise of -ln L; sigma of -2 ln L = 1e-3
    A = [[4.0, 1.2, 0.0, 0.3], [1.2, 1.0, 0.2, 0.0], [0.0, 0.2, 2.0, 0.5], [0.3, 0.0, 0.5, 0.5]]
    CENTER = [1.0, -0.5, 0.2, 3.0]
    BOUNDS = [(-10.0, 10.0)] * 4

    def setUp(self):
        import numpy as np

        import propagation_fit as pf
        self.np, self.pf = np, pf
        self.F = np.asarray(self.A)

    def test_stencil_measures_the_known_noise(self):
        np, pf = self.np, self.pf
        ratios = []
        for seed in range(30):
            f = _noisy_quadratic(self.SIGMA_F, self.A, self.CENTER, seed)
            rec = pf._noise_floor(f, self.CENTER, self.F, set(), self.BOUNDS, {"mode": "measure", "max_evaluations": 40})
            self.assertEqual((rec["evaluations"], rec["dof"]), (16, 8))
            ratios.append((rec["sigma_m2lnl"] / (2 * self.SIGMA_F)) ** 2)
        # 240 degrees of freedom in all: the mean variance ratio has a relative standard error of 9%
        self.assertLess(abs(float(np.mean(ratios)) - 1.0), 0.3)
        small = pf._noise_floor(_noisy_quadratic(self.SIGMA_F, self.A, self.CENTER, 0), self.CENTER, self.F, set(),
                                self.BOUNDS, {"mode": "measure", "max_evaluations": 9})
        self.assertEqual((small["evaluations"], len(small["coordinates"])), (8, 2))
        held = pf._noise_floor(_noisy_quadratic(self.SIGMA_F, self.A, self.CENTER, 0), self.CENTER, self.F,
                               {0, 1, 2, 3}, self.BOUNDS, {"mode": "measure", "max_evaluations": 40})
        self.assertIsNone(held["sigma_m2lnl"])   # nothing measurable: the fit keeps the 1e-5 threshold

    def test_steps_follow_the_noise_and_the_curvature(self):
        np, pf = self.np, self.pf
        s = 2 * self.SIGMA_F
        st = pf._noise_steps(s, self.F, self.CENTER, self.BOUNDS, set(), None)
        V = float(np.sum(np.diag(self.F) * np.diag(np.linalg.inv(self.F))))
        a = min(max(2 * math.sqrt(self.SIGMA_F * V), 0.1), 1.0)
        self.assertLessEqual(abs(st["step_factor"] - a), 1e-12 * a)
        for h, fii in zip(st["steps"], np.diag(self.F)):
            self.assertLessEqual(abs(h - a / math.sqrt(fii)), 5e-3 * h)   # 3 significant digits
        self.assertEqual(pf._noise_steps(1e-12, self.F, self.CENTER, self.BOUNDS, set(), None)["step_factor"], 0.1)
        self.assertEqual(pf._noise_steps(10.0, self.F, self.CENTER, self.BOUNDS, set(), None)["step_factor"], 1.0)
        near = [(-10.0, 1.001), (-10.0, 10.0), (-10.0, 10.0), (-10.0, 10.0)]   # half the room to a bound at most
        self.assertLessEqual(pf._noise_steps(s, self.F, self.CENTER, near, set(), None)["steps"][0], 0.0005 + 1e-12)

    def _judge(self, f, t, noise_aware):
        pf = self.pf
        if noise_aware:
            st = pf._noise_steps(2 * self.SIGMA_F, self.F, t, self.BOUNDS, set(), None)["steps"]
            return pf._verdict(f, t, self.BOUNDS, set(), st, edm_tol=max(pf.EDM_TOL_BASE, pf.NOISE_EDM_FACTOR
                                                                          * 2 * self.SIGMA_F), grid=True)
        small = [1e-3 / math.sqrt(x) for x in self.np.diag(self.F)]   # steps that ignore the noise
        return pf._verdict(f, t, self.BOUNDS, set(), small)

    def test_verdict_flips_with_the_rule(self):
        np = self.np
        edm_noise = []
        for seed in range(20):
            f = _noisy_quadratic(self.SIGMA_F, self.A, self.CENTER, seed)
            ruled = self._judge(f, self.CENTER, True)
            self.assertEqual(ruled["status"], "converged", (seed, ruled))
            self.assertLessEqual(abs(ruled["edm_threshold"] - self.SIGMA_F), 1e-12)
            edm_noise.append(ruled["edm"])
            plain = self._judge(f, self.CENTER, False)
            self.assertEqual(plain["status"], "failed")
            self.assertNotIn("edm_threshold", plain)
        # the step rule: mean noise part of EDM <= sigma_f / 16 (allowance 1.5 for 20 samples)
        self.assertLess(float(np.mean(edm_noise)), 1.5 * self.SIGMA_F / 16)
        # a point whose true EDM is 20 sigma_f fails under the rule, with its EDM measured to about 30%
        d = np.linalg.solve(self.F, np.ones(4))
        d *= math.sqrt(2 * 20 * self.SIGMA_F / float(d @ self.F @ d))
        off = (np.asarray(self.CENTER) + d).tolist()
        for seed in range(5):
            v = self._judge(_noisy_quadratic(self.SIGMA_F, self.A, self.CENTER, seed), off, True)
            self.assertEqual(v["status"], "failed")
            self.assertIn("gradient_not_small", v["reasons"])
            self.assertLess(abs(v["edm"] / (20 * self.SIGMA_F) - 1.0), 0.3)


class _SquaredStub:
    """A SYNTHETIC 15-bin prediction 1 + a E + b exp(-3E) + 0.004 v^2 exp(-2.7E) (v enters only through v^2, nearly
    degenerate with b, as V_A with the other transport parameters), a response model refusing v above refuse_above,
    and the model interface SurrogateFit uses. Linear in (a, b, v^2), so the bounded minimum is exact (lsq_linear)."""

    E = None
    SIGMA = 0.01

    def __init__(self, squared, refuse_above=None):
        import numpy as np
        _SquaredStub.E = np.linspace(0.0, 1.0, 15)
        self.names, self.lo, self.hi = ["a", "b", "v"], np.array([0.0, 0.0, 0.0]), np.array([2.0, 1.0, 10.0])
        self.refuse_above, self.n_nu = refuse_above, 0
        self.params = {"a": {"step": 1e-3}, "b": {"step": 1e-3}, "v": {"step": 0.03, "enters_squared": squared}}

    @classmethod
    def pred(cls, a, b, v):
        import numpy as np
        return 1.0 + a * cls.E + b * np.exp(-3 * cls.E) + 0.004 * v * v * np.exp(-2.7 * cls.E)

    def components(self, t):
        import propagation_fit as pf
        if self.refuse_above is not None and t[2] > self.refuse_above:
            raise pf.FitRefused("out-of-domain", f"v = {t[2]}")
        return {"d": self.pred(*t)[None, :]}

    def chol_with_error(self):
        import numpy as np
        return {"d": np.eye(len(self.E)) * self.SIGMA}

    def steps(self, names):
        return [self.params[n]["step"] for n in names]

    def residual_at(self, comps, nu, ys, aux, chol):
        import numpy as np
        return np.linalg.solve(chol["d"], ys["d"] - comps["d"].sum(axis=0))

    def fit(self, toy, truth_v=0.0):
        import numpy as np
        import propagation_fit as pf
        rng = np.random.default_rng(toy)
        y = self.pred(0.7, 0.3, truth_v) + self.SIGMA * rng.normal(size=len(self.E))
        sf = pf.SurrogateFit(self, self, self.names, ["linear"] * 3, {},
                             (self.names, [(0.0, 2.0), (0.0, 1.0), (0.0, 10.0)]))
        out = sf.fit({"d": y}, [], np.array([0.7, 0.1, 6.0]), {"max_restarts": 5, "max_iterations": 100,
                                                                "seed": toy})
        return out, sf.last_square, y


@unittest.skipUnless(HAVE, "needs numpy and scipy")
class SquaredParameterRetry(unittest.TestCase):
    """L1-1 (VALIDATION.md CRPROP-L1): a toy fit that fails in a parameter declared enters_squared is retried in
    w = p^2; it then reaches the exact bounded minimum; a fit that converges in p is unchanged; an out-of-domain
    refusal in the first attempt is retried; the declaration is refused off a linear axis starting at 0."""

    TOYS = 20

    def test_fits_failing_in_p_reach_the_exact_minimum_in_the_square(self):
        import numpy as np
        from scipy.optimize import lsq_linear
        E = np.linspace(0.0, 1.0, 15)
        A = np.stack([E, np.exp(-3 * E), 0.004 * np.exp(-2.7 * E)], axis=1) / _SquaredStub.SIGMA
        failed_in_p, retried = 0, 0
        for toy in range(self.TOYS):
            (_, _, ok0, _), sq0, _ = _SquaredStub(False).fit(toy)
            (chi2, z, ok, reason), sq, y = _SquaredStub(True).fit(toy)
            self.assertFalse(sq0)
            failed_in_p += not ok0
            self.assertTrue(ok, (toy, reason))
            self.assertEqual(sq, not ok0, toy)
            retried += sq
            exact = lsq_linear(A, (y - 1.0) / _SquaredStub.SIGMA, bounds=([0, 0, 0], [2, 1, 100]), tol=1e-14)
            self.assertLessEqual(abs(chi2 - 2 * exact.cost), 1e-6 * 2 * exact.cost, toy)
        self.assertGreater(failed_in_p, 0)          # the mechanism of the K4 toys: p fails near the bound
        self.assertEqual(retried, failed_in_p)

    def test_fits_converging_in_p_keep_their_numbers(self):
        same = 0
        for truth_v in (0.0, 6.0):
            for toy in range(self.TOYS):
                plain, _, _ = _SquaredStub(False).fit(toy, truth_v)
                if not plain[2]:
                    continue
                declared, sq, _ = _SquaredStub(True).fit(toy, truth_v)
                self.assertFalse(sq)
                self.assertEqual((plain[0], tuple(plain[1]), plain[3]), (declared[0], tuple(declared[1]), declared[3]))
                same += 1
        self.assertGreater(same, 0)

    def test_an_out_of_domain_first_attempt_is_retried(self):
        rescued = 0
        for toy in range(self.TOYS):
            plain, _, _ = _SquaredStub(False, refuse_above=6.5).fit(toy)
            declared, sq, _ = _SquaredStub(True, refuse_above=6.5).fit(toy)
            if plain[3] == "provider-out-of-domain" and declared[2]:
                self.assertTrue(sq)
                rescued += 1
        self.assertGreater(rescued, 0)

    def test_declaration_needs_a_linear_axis_from_zero(self):
        import propagation_fit as pf
        domain = {"V_A_kms": {"min": 0.0, "max": 105.0}, "D0_cm2_s": {"min": 1e28, "max": 1e29},
                  "V_c_kms": {"min": 1.0, "max": 9.0}}
        ok = pf.Model({"parameters": {"V_A_kms": {"start": 60.0, "enters_squared": True}}}, [], None, domain)
        self.assertTrue(ok.params["V_A_kms"]["enters_squared"])
        for name, spec in (("D0_cm2_s", {"start": 3e28, "scale": "log", "enters_squared": True}),
                           ("V_c_kms", {"start": 2.0, "enters_squared": True}),
                           ("V_A_kms", {"start": 60.0, "enters_squared": "yes"})):
            with self.subTest(name=name), self.assertRaises(pf.FitInputError):
                pf.Model({"parameters": {name: spec}}, [], None, domain)


def _usine_record():
    return json.loads(USINE_RECORD.read_text(encoding="utf-8"))


@unittest.skipUnless(HAVE, "needs numpy and scipy")
class UsineProvider(unittest.TestCase):
    """C2U from the recorded USINE study (offline), plus one live refit gated by HEP_USINE_LIVE_TEST=1."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _usine_record()
        cls.res = cls.doc["result"]
        cls.fits = {f["family"]: f for f in cls.res["fits"]}
        cls.tmp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.tmp.name)
        cls.registry = cls.work / "registry.json"
        proc = subprocess.run([sys.executable, str(PLUGIN / "tools" / "provider_registry.py"), "--write",
                               str(cls.registry)], capture_output=True, text=True, timeout=300)
        assert proc.returncode == 0, proc.stdout + proc.stderr

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def config(self, **extra):
        cfg = copy.deepcopy(self.doc["config"])
        for key in ("family_toys", "intervals"):
            cfg.pop(key, None)
        cfg.update(extra)
        return cfg

    # ---------------------------------------------------------------- C2U-1
    def test_c2u1_asimov_recovery_with_a_boundary_parameter(self):
        truth = self.doc["truth"]
        big = self.fits["BIG"]
        self.assertEqual((big["status"], big["convergence"]["status"]), ("converged", "converged"))
        interior = 0
        for p in big["parameters"]:
            t = math.log(truth[p["name"]]) if p["scale"] == "log" else truth[p["name"]]
            if p["name"] == "V_c_kms":
                continue
            interior += 1
            self.assertFalse(p["at_bound"], p)
            self.assertLessEqual(abs(p["best_fit_coordinate"] - t) / p["sigma_coordinate"], 0.1, p)
        self.assertEqual(interior, 3)
        vc = next(p for p in big["parameters"] if p["name"] == "V_c_kms")
        self.assertEqual(truth["V_c_kms"], 0.0)
        self.assertTrue(vc["at_bound"])
        kkt = [k for k in big["convergence"]["kkt"] if k["index"] == big["free"].index("V_c_kms")]
        self.assertEqual((len(kkt), kkt[0]["bound"], kkt[0]["ok"]), (1, "lower", True))
        interval = next(i for i in big["profile_intervals"] if i["parameter"] == "V_c_kms")
        self.assertEqual((interval["lower"]["kind"], interval["upper"]["kind"]), ("bound", "crossing"))
        sigma_one_sided = interval["upper"]["width_coordinate"]
        self.assertGreater(sigma_one_sided, 0.0)
        self.assertLessEqual(abs(vc["best_fit"] - truth["V_c_kms"]) / sigma_one_sided, 0.1)
        self.assertTrue(self.res["gate"][0]["comparable"])
        self.assertIn("synthetic", self.res["status_label"])

    # ---------------------------------------------------------------- C2U-2
    def test_c2u2_provider_records(self):
        prov = self.res["provider"]
        self.assertEqual((prov["id"], prov["version"], prov["decomposable"]), ("usine", "0.2.0", False))
        self.assertEqual(self.res["channels"], ["total"])
        pe = self.res["provider_evaluations"]
        records = pe["records"]
        self.assertGreater(len(records), 0)
        self.assertEqual(pe["records_with_computational_run"], len(records))
        self.assertTrue(all(r["computational_run_ref"] and r["computational_run_resolved"] for r in records))
        self.assertEqual(len({r["input_hash"] for r in records}), len(records))   # one record per evaluation
        self.assertEqual(pe["computational_runs"]["resolved"], len(records))
        self.assertEqual(pe["computational_runs"]["unresolved_refs"], [])
        tools = pe["computational_runs"]["tools"]
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "USINE")
        self.assertIn("V3.5", tools[0]["version"])
        self.assertIn("fb53006d", tools[0]["version"])
        self.assertLessEqual(self.doc["usine_evaluations"]["fit"], self.doc["config"].get("max_evaluations", 1200))

    def test_c2u2_out_of_domain_is_refused_without_a_run(self):
        import propagation_fit as pf
        cfg = self.config(families=[self.doc["config"]["families"][0]])
        cfg["parameters"]["V_A_kms"]["start"] = 200.0
        with self.assertRaises(pf.FitRefused) as ctx:
            pf.run(cfg, self.work, str(self.registry), cache_dir=self.work / "cache")
        self.assertEqual(ctx.exception.reason, "out-of-domain")
        # a point sent outside the domain is refused by the provider entrypoint before any USINE run
        from core.provider.runner import ProviderRunner
        obs = {"id": "B/C", "axis": "ekn", "unit": "GeV/n", "bins": [[1.0, 2.0]]}
        point = dict(self.doc["truth"], V_A_kms=200.0)
        req = {"protocol": "cr-provider/1", "provider": "usine", "provider_version": "0.2.0",
               "transport": self.doc["config"]["transport"], "points": [point], "observables": [obs],
               "want": ["lis"], "seed": None}
        env = {k: os.environ.pop(k) for k in ("HEP_USINE_BIN", "HEP_USINE_DATA") if k in os.environ}
        try:
            with ProviderRunner(str(self.registry)) as runner:
                resp = runner.evaluate(req)
        finally:
            os.environ.update(env)
        self.assertEqual(resp["results"][0]["status"], "failed")
        self.assertEqual(resp["results"][0]["reason"], "out-of-domain")

    def test_multipliers_need_a_decomposable_provider(self):
        import propagation_fit as pf
        cfg = self.config(nuisances=[{"name": "xs-C-B", "kind": "production-norm", "channel": "C->B",
                                      "prior_sigma": 0.1}])
        with self.assertRaises(pf.FitRefused) as ctx:
            pf.run(cfg, self.work, str(self.registry), cache_dir=self.work / "cache")
        self.assertEqual(ctx.exception.reason, "not-decomposable")

    # ---------------------------------------------------------------- C2U-3 (moved to C2UF-1, decision A1.12)
    def test_c2u3_recorded_refusal_is_asserted_and_moved(self):
        self.assertEqual(self.res["families"]["expressible"], ["BIG", "SLIM"])
        self.assertEqual(self.res["families"]["not_expressible"], [])
        for name in ("BIG", "SLIM"):                      # both fitted with the provider itself
            self.assertEqual(self.fits[name]["status"], "converged")
        # C2U's study recorded the calibration as refused (VALIDATION CRPROP-C2U: the union box spanned the whole V_A
        # domain); the criterion is asserted from the C2UF study in UsineTwoDatasetFamilies, never skipped here
        cal = self.res["family_calibration"]
        self.assertEqual((cal["status"], cal["reason"]), ("failed", "response-model-above-tolerance"))
        self.assertIn("above the tolerance 0.05", cal["detail"])
        self.assertTrue(TWO_DATASET_RECORD.is_file())

    def test_statistical_result_of_the_study_validates(self):
        import propagation_fit as pf
        from contracts.validate import validate_artifact
        sr = pf.statistical_result_artifact(self.res, self.res["status_label"])
        rep = validate_artifact(sr)
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertEqual(sr["extension"]["seeds"]["family_toys"], self.doc["config"]["family_toys"]["seed"])

    # ---------------------------------------------------------------- bin semantics (P2)
    def test_bin_semantics_guard_accepts_p2_and_refuses_mismatches(self):
        import propagation_fit as pf
        from core.provider.registry import load_registry
        entry = load_registry(str(self.registry))["usine"]
        pred = self.doc["truth_prediction"]
        self.assertEqual(pf.binning_meaning(pred["observable"])[0], "ratio of bin integrals (P2)")
        record = self.doc["config"]["datasets"][0]["measurement"]
        keys = list(self.doc["truth"])
        run_keys = self.doc["config"]["run_record_keys"]

        def gate(observable):
            rec = copy.deepcopy(record)
            rec["extension"]["observable"] = observable
            ds = pf.Dataset("d", rec, "B/C", self.work)
            return pf._gate(ds, pred, ["synthetic"], self.doc["config"]["gate_plan"], entry, keys, run_keys)
        self.assertTrue(gate(copy.deepcopy(pred["observable"]))["comparable"])
        p2 = copy.deepcopy(pred["observable"])
        p2["bin_semantics"] = "bin-integrated"
        p2["conventions"].pop("energy_variable")
        self.assertTrue(gate(p2)["comparable"])                      # P2 data declared bin-integrated
        for change in ({"bin_semantics": "point"},
                       {"conventions": dict(pred["observable"]["conventions"],
                                            **{"crsr:bin_average": "ratio averaged uniformly in ln(E/n)"})},
                       {"conventions": {k: v for k, v in pred["observable"]["conventions"].items()
                                        if k != "energy_variable"}}):
            obs = dict(copy.deepcopy(pred["observable"]), **change)
            with self.assertRaises(pf.FitRefused) as ctx:
                gate(obs)
            self.assertEqual(ctx.exception.reason, "bin-semantics-mismatch", change)

    # ---------------------------------------------------------------- live (gated)
    @unittest.skipUnless(LIVE, "live USINE runs: set HEP_USINE_LIVE_TEST=1, HEP_USINE_BIN and HEP_USINE_DATA")
    def test_live_slim_refit_matches_the_record(self):
        import propagation_fit as pf
        runs = self.work / "runs"
        runs.mkdir(exist_ok=True)
        cfg = self.config(families=[f for f in self.doc["config"]["families"] if f["name"] == "SLIM"],
                          computational_runs=str(runs))
        old = os.environ.get("HEP_USINE_RUN_DIR")
        os.environ["HEP_USINE_RUN_DIR"] = str(runs)
        try:
            res = pf.run(cfg, self.work, str(self.registry), cache_dir=self.work / "live-cache", max_evaluations=150)
        finally:
            if old is None:
                os.environ.pop("HEP_USINE_RUN_DIR")
            else:
                os.environ["HEP_USINE_RUN_DIR"] = old
        live = {p["name"]: p["best_fit"] for p in res["fits"][0]["parameters"]}
        rec = {p["name"]: p["best_fit"] for p in self.fits["SLIM"]["parameters"]}
        for name, value in rec.items():
            self.assertLessEqual(abs(live[name] / value - 1.0), 1e-6, name)
        pe = res["provider_evaluations"]
        self.assertEqual(pe["computational_runs"]["resolved"], len(pe["records"]))
        self.assertIn("fb53006d", pe["computational_runs"]["tools"][0]["version"])


if __name__ == "__main__":
    unittest.main()


def _two_dataset_record():
    return json.loads(TWO_DATASET_RECORD.read_text(encoding="utf-8"))


@unittest.skipUnless(HAVE, "needs numpy and scipy")
class UsineTwoDatasetFamilies(unittest.TestCase):
    """The two-dataset USINE study of C2UF dispatch 1 (polynomial response models), asserted as recorded: fits with
    USINE, the response model refused (0.452 sigma). C2UF-1 itself is asserted from the emulator study
    (UsineEmulatorFamilies, decision A1.14). One live check gated by HEP_USINE_LIVE_TEST=1."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _two_dataset_record()
        cls.res = cls.doc["result"]
        cls.fits = {f["family"]: f for f in cls.res["fits"]}
        cls.cal = cls.res["family_calibration"]

    def test_two_datasets_both_families_fitted_with_the_provider(self):
        self.assertEqual(self.res["families"]["expressible"], ["BIG", "SLIM"])
        self.assertEqual(self.res["families"]["not_expressible"], [])
        for name in ("BIG", "SLIM"):
            self.assertEqual(self.fits[name]["status"], "converged")
        truth = self.doc["truth"]
        for p in self.fits["BIG"]["parameters"]:              # Asimov: BIG (the generator) returns the truth
            t = math.log(truth[p["name"]]) if p["scale"] == "log" else truth[p["name"]]
            self.assertLessEqual(abs(p["best_fit_coordinate"] - t) / p["sigma_coordinate"], 0.01, p)
        self.assertLess(self.fits["BIG"]["parameters"][2]["sigma_coordinate"], 10.0)   # 10Be/9Be pins V_A (C2U: 27.8)
        self.assertGreater(self.fits["SLIM"]["chi2"] - self.fits["BIG"]["chi2"], 20.0)
        self.assertEqual([d["observable"] for d in self.res["datasets"]], ["B/C", "10Be/9Be"])
        self.assertTrue(all(g["comparable"] for g in self.res["gate"]))
        self.assertEqual(self.doc["config"]["transport"]["decay"]["enabled"], True)
        self.assertEqual(self.doc["config"]["provider_requests"], "per-point")
        pe = self.res["provider_evaluations"]
        self.assertTrue(pe["records"])
        for r in pe["records"]:                       # one USINE run serves both datasets
            self.assertEqual(r["datasets"], ["bc-asimov", "be-asimov"])
            self.assertTrue(r["computational_run_ref"] and r["computational_run_resolved"])
        self.assertEqual(pe["computational_runs"]["unresolved_refs"], [])
        self.assertEqual([t["name"] for t in pe["computational_runs"]["tools"]], ["USINE"])
        self.assertIn("fb53006d", pe["computational_runs"]["tools"][0]["version"])
        self.assertLessEqual(self.doc["usine_evaluations"]["fit"], 255)
        self.assertIn("synthetic", self.res["status_label"])

    def test_two_datasets_recorded_calibration_refusal(self):
        # the recorded study (VALIDATION CRPROP-C2UF, study 2): the joint degree-4 model was refused, so no toy ran
        declared = self.doc["config"]["response_model"]
        self.assertEqual((declared["layout"], declared["degree"], declared["design_points"],
                          declared["half_width_sigma"], declared["tolerance_sigma"]), ("joint", 4, 150, 3.0, 0.05))
        self.assertEqual((self.cal["status"], self.cal["reason"]), ("failed", "response-model-above-tolerance"))
        self.assertIn("largest error is 0.452 of the data sigma, above the tolerance 0.05", self.cal["detail"])
        self.assertNotIn("families", self.cal)
        self.assertIsNone(self.res["families"]["surviving"])
        self.assertEqual(self.res["status"], "failed")

    def test_two_datasets_statistical_result_validates(self):
        import propagation_fit as pf
        from contracts.validate import validate_artifact
        sr = pf.statistical_result_artifact(self.res, self.res["status_label"])
        rep = validate_artifact(sr)
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertEqual(sr["extension"]["seeds"]["family_toys"], self.doc["config"]["family_toys"]["seed"])

    @unittest.skipUnless(LIVE, "live USINE run: set HEP_USINE_LIVE_TEST=1, HEP_USINE_BIN and HEP_USINE_DATA")
    def test_live_truth_rerun_matches_the_record(self):
        sys.path.insert(0, str(PLUGIN / "tests" / "skills" / "hep_statistics"))
        import usine_two_dataset_family_study as study
        with tempfile.TemporaryDirectory() as scratch_dir:
            work = Path(scratch_dir)
            registry = work / "registry.json"
            proc = subprocess.run([sys.executable, str(PLUGIN / "tools" / "provider_registry.py"), "--write",
                                   str(registry)], capture_output=True, text=True, timeout=300)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            old = os.environ.get("HEP_USINE_RUN_DIR")
            os.environ["HEP_USINE_RUN_DIR"] = str(work / "runs")
            (work / "runs").mkdir()
            try:
                res, gen = study.generate(str(registry), str(work / "cache"))   # one USINE run, fresh cache
            finally:
                if old is None:
                    os.environ.pop("HEP_USINE_RUN_DIR")
                else:
                    os.environ["HEP_USINE_RUN_DIR"] = old
            self.assertEqual(gen["points_sent"], 1)
            for (name, *_), pred in zip(study.DATASETS, res["predictions"]):
                rec = self.doc["truth_predictions"][name]["values"]["values"]
                for a, b in zip(pred["values"]["values"], rec):
                    self.assertLessEqual(abs(a / b - 1.0), 1e-6, name)
            run = json.loads(next((work / "runs").rglob("*.computational-run.json")).read_text())
            self.assertIn("fb53006d", json.dumps(run["extension"]["tools"]))


def _emulator_record():
    return json.loads(EMULATOR_RECORD.read_text(encoding="utf-8"))


@unittest.skipUnless(HAVE, "needs numpy and scipy")
class UsineEmulatorFamilies(unittest.TestCase):
    """C2UF-1 (decision A1.14) from the recorded emulator study (usine_emulator_family_study.py): a Gaussian-process
    emulator of USINE (B/C and 10Be/9Be, decay on) validated on held-out USINE runs at 0.05 sigma, its error in the
    covariance (P10), BIG and SLIM fitted with the emulator provider, toy-calibrated delta chi2 of both, the generator
    surviving. Hard assertions; one live check gated by HEP_USINE_LIVE_TEST=1 (two USINE runs)."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _emulator_record()
        cls.res = cls.doc["result"]
        cls.fits = {f["family"]: f for f in cls.res["fits"]}
        cls.cal = cls.res["family_calibration"]
        cls.val = cls.doc["emulator"]["validation"]

    def test_emulator_validated_against_usine_and_its_error_in_the_covariance(self):
        import hashlib
        self.assertEqual((self.val["passed"], self.val["tolerance"]), (True, 0.05))
        self.assertLessEqual(self.val["max_error_over_sigma"], 0.05)
        self.assertEqual(len(self.val["rows"]), 40)
        self.assertTrue(all(r["status"] == "ok" and r["max_error_over_sigma"] <= 0.05 for r in self.val["rows"]))
        self.assertEqual(sum(1 for r in self.val["rows"] if r["point"]["V_A_kms"] == 0.0), 10)   # the SLIM slice
        model = TWO_DATASET_RECORD.parent / self.doc["emulator"]["model"]
        self.assertEqual(hashlib.sha256(model.read_bytes()).hexdigest(), self.doc["emulator"]["model_sha256"])
        self.assertEqual(self.res["provider"]["id"], "emulator")
        self.assertTrue(self.res["provider"]["version"].endswith("+model." + self.doc["emulator"]["model_sha256"][:12]))
        for ds in self.doc["config"]["datasets"]:      # P10: the largest held-out error per bin, uncorrelated
            comp = [u for u in ds["measurement"]["extension"]["data"]["uncertainties"] if u["name"] == "emulator"]
            self.assertEqual(len(comp), 1)
            self.assertEqual(comp[0]["correlation"], "uncorrelated")
            self.assertEqual(comp[0]["values"], self.val["error_component"][ds["name"]])

    def test_emulator_toy_calibrated_delta_chi2_and_generator_survives(self):
        self.assertEqual(self.res["status"], "ok")
        self.assertEqual(self.res["families"]["expressible"], ["BIG", "SLIM"])
        for name in ("BIG", "SLIM"):
            self.assertEqual(self.fits[name]["status"], "converged")
            usine = self.doc["usine_fits"][name]        # the emulator fit equals the USINE fit of study 2
            self.assertLessEqual(abs(self.fits[name]["chi2"] - usine["chi2"]), 0.05)
        self.assertEqual(self.cal["status"], "ok", self.cal.get("detail"))
        self.assertEqual(self.cal["response_model"]["kind"], "provider (no response model)")
        entries = {e["family"]: e for e in self.cal["families"]}
        self.assertEqual(set(entries), {"BIG", "SLIM"})
        n, alpha = self.doc["config"]["family_toys"]["n"], self.doc["config"]["family_toys"]["alpha"]
        self.assertEqual((n, alpha), (200, 0.05))
        best = min(f["chi2"] for f in self.fits.values())
        for name, e in entries.items():
            self.assertEqual(e["status"], "ok")
            self.assertEqual(e["toys"], n)
            self.assertLessEqual(e["failed"], 0.02 * n)
            self.assertEqual(len(e["rows"]), n)
            self.assertAlmostEqual(e["delta_chi2"], self.fits[name]["chi2"] - best, places=12)
            ok_rows = [r for r in e["rows"] if r["outcome"] == "ok"]
            exceed = sum(1 for r in ok_rows if r["delta_chi2"] >= e["delta_chi2"] - 1e-12)
            self.assertEqual((e["p_toys"]["k"], e["p_toys"]["n"]), (exceed, len(ok_rows)))
        gen = self.doc["generating_family"]
        self.assertEqual((gen, entries[gen]["delta_chi2"]), ("BIG", 0.0))
        self.assertTrue(entries[gen]["surviving"])
        self.assertGreaterEqual(entries[gen]["p_toys"]["estimate"], alpha)
        self.assertIn(gen, self.cal["surviving"])
        self.assertEqual(self.res["families"]["surviving"], self.cal["surviving"])
        self.assertGreater(entries["SLIM"]["delta_chi2"], 20.0)

    def test_l1_portable_model_and_squared_va(self):
        """L1-2 (VALIDATION.md CRPROP-L1): the fixture is the model trained with the kernel condition bound 1e10, its
        k = 4 confirmation over the toy domain passed, V_A_kms is declared enters_squared, and BIG's toy fits that
        failed in V_A went through the V_A^2 retries (recorded per toy as square_retry)."""
        model = json.loads((TWO_DATASET_RECORD.parent / self.doc["emulator"]["model"]).read_text(encoding="utf-8"))
        self.assertEqual(self.doc["emulator"]["max_condition"], 1e10)
        self.assertEqual(model["training"]["max_condition"], 1e10)
        for comp in model["components"]:
            self.assertLessEqual(comp["condition_number"], 1e10 * (1 + 1e-6))
        conf = self.doc["emulator"]["confirmation"]
        self.assertTrue(conf["passed"])
        self.assertLessEqual(conf["max_error_over_sigma"], conf["tolerance"])
        self.assertIs(self.doc["config"]["parameters"]["V_A_kms"]["enters_squared"], True)
        retried = [r for e in self.cal["families"] for r in e["rows"] if r.get("square_retry")]
        self.assertTrue(retried)
        self.assertTrue(all(r["square_retry"] == ["BIG"] for r in retried))

    def test_statistical_result_validates(self):
        import propagation_fit as pf
        from contracts.validate import validate_artifact
        sr = pf.statistical_result_artifact(self.res, self.res["status_label"])
        self.assertTrue(validate_artifact(sr).ok)
        self.assertEqual(sr["extension"]["seeds"]["family_toys"], self.doc["config"]["family_toys"]["seed"])

    @unittest.skipUnless(LIVE, "live USINE runs: set HEP_USINE_LIVE_TEST=1, HEP_USINE_BIN and HEP_USINE_DATA")
    def test_live_emulator_matches_fresh_usine_runs(self):
        sys.path.insert(0, str(PLUGIN / "tests" / "skills" / "hep_statistics"))
        import usine_emulator_family_study as study
        rows = [self.val["rows"][3], self.val["rows"][35]]
        with tempfile.TemporaryDirectory() as scratch_dir:
            work = Path(scratch_dir)
            registry = work / "registry.json"
            proc = subprocess.run([sys.executable, str(PLUGIN / "tools" / "provider_registry.py"), "--write",
                                   str(registry)], capture_output=True, text=True, timeout=300)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            old = os.environ.get("HEP_USINE_RUN_DIR")
            os.environ["HEP_USINE_RUN_DIR"] = str(work)
            try:
                usine, sent = study.usine_values(str(registry), str(work / "cache"), [r["point"] for r in rows])
            finally:
                if old is None:
                    os.environ.pop("HEP_USINE_RUN_DIR")
                else:
                    os.environ["HEP_USINE_RUN_DIR"] = old
            self.assertEqual(sent, 2)
            artifact = TWO_DATASET_RECORD.parent / self.doc["emulator"]["ml_artifact"]
            emu_reg = study.emulator_registry(str(registry), artifact, work / "emulator-registry.json")
            emu = study.emulator_values(emu_reg, artifact, [r["point"] for r in rows])
            nbc = 15
            for u, e in zip(usine, emu):
                self.assertEqual(e["status"], "ok")
                for i, (a, b) in enumerate(zip(e["values"], u)):
                    rel = study.SIGMA_REL["bc-asimov" if i < nbc else "be-asimov"]
                    self.assertLessEqual(abs(a - b) / (rel * b), 0.05, i)
