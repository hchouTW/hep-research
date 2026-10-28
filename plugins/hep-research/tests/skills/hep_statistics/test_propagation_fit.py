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
per point, BIG and SLIM fitted with the provider, toy-calibrated delta chi2 of both on per-center response models
validated against the provider, the generator surviving. With HEP_USINE_LIVE_TEST=1 one live test reruns the truth
point (one USINE run) and compares it with the record.
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
    def test_c2u3_recorded_refusal_is_asserted_and_moved_to_c2uf(self):
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
    """C2UF-1 (C2U-3 moved by A1.12) from the recorded two-dataset USINE study, plus one live check gated by
    HEP_USINE_LIVE_TEST=1. Hard assertions: nothing here skips when the calibration is not ok."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _two_dataset_record()
        cls.res = cls.doc["result"]
        cls.fits = {f["family"]: f for f in cls.res["fits"]}
        cls.cal = cls.res["family_calibration"]

    def test_c2uf1_both_families_fitted_with_the_provider_on_two_datasets(self):
        self.assertEqual(self.res["families"]["expressible"], ["BIG", "SLIM"])
        self.assertEqual(self.res["families"]["not_expressible"], [])
        for name in ("BIG", "SLIM"):
            self.assertEqual(self.fits[name]["status"], "converged")
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
        self.assertLessEqual(self.doc["usine_evaluations"]["truth"] + self.doc["usine_evaluations"]["fit"], 600)
        self.assertIn("synthetic", self.res["status_label"])

    def test_c2uf1_validated_response_models_with_their_error_in_the_covariance(self):
        self.assertEqual(self.cal["status"], "ok", self.cal.get("detail"))
        rm = self.cal["response_model"]
        declared = self.doc["config"]["response_model"]
        self.assertEqual((rm["layout"], declared["tolerance_sigma"]), ("per-center", 0.05))
        self.assertEqual([m["center_of"] for m in rm["sub_models"][:2]], ["BIG", "SLIM"])
        for m in rm["sub_models"]:
            self.assertEqual(m["kind"], "total-degree polynomial")
            self.assertEqual(m["validation"]["points"], declared["validation_points"])
            self.assertTrue(m["validation"]["passed"])
            self.assertLessEqual(m["validation"]["max_error_over_sigma"], 0.05)
        self.assertTrue(rm["validation"]["passed"])
        for name, pred in self.doc["truth_predictions"].items():   # P10: a per-bin error for every dataset
            self.assertEqual(len(rm["error_component"][name]), len(pred["values"]["values"]))
        self.assertEqual(len(rm["assignment"]), 4)

    def test_c2uf1_toy_calibrated_delta_chi2_and_the_generator_survives(self):
        entries = {e["family"]: e for e in self.cal["families"]}
        self.assertEqual(set(entries), {"BIG", "SLIM"})
        n = self.doc["config"]["family_toys"]["n"]
        alpha = self.doc["config"]["family_toys"]["alpha"]
        self.assertEqual((n, alpha), (200, 0.05))
        best = min(f["chi2"] for f in self.fits.values())
        for name, e in entries.items():
            self.assertEqual(e["status"], "ok")
            self.assertEqual(e["toys"], n)
            self.assertLessEqual(e["failed"], 0.02 * n)
            self.assertAlmostEqual(e["delta_chi2"], self.fits[name]["chi2"] - best, places=12)
            ok_rows = [r for r in e["rows"] if r["outcome"] == "ok"]
            exceed = sum(1 for r in ok_rows if r["delta_chi2"] >= e["delta_chi2"] - 1e-12)
            self.assertEqual((e["p_toys"]["k"], e["p_toys"]["n"]), (exceed, len(ok_rows)))
            if e["p_toys"]["estimate"] is not None:
                self.assertAlmostEqual(e["p_toys"]["estimate"], exceed / len(ok_rows), places=12)
        gen = self.doc["generating_family"]
        self.assertEqual(gen, "BIG")
        self.assertEqual(entries[gen]["delta_chi2"], 0.0)
        self.assertTrue(entries[gen]["surviving"])
        self.assertGreaterEqual(entries[gen]["p_toys"]["estimate"], alpha)
        self.assertIn(gen, self.cal["surviving"])
        self.assertEqual(self.res["families"]["surviving"], self.cal["surviving"])

    def test_c2uf_statistical_result_validates(self):
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
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
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
