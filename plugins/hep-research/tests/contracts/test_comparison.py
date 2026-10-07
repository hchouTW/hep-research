"""Comparison gate, composition, combination and model-set tests (T03-T09, AC14, AC15).

All fixtures are SYNTHETIC and use neutral namespaces ('alpha', 'beta') unless a test is about a profile namespace."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-statistics" / "scripts"))
from contracts.comparison.combination import plan_combination  # noqa: E402
from contracts.comparison.composition import compose  # noqa: E402
from contracts.comparison.gate import gate  # noqa: E402
from contracts.comparison.model_set import envelope, model_set  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

try:
    import numpy as np
    HAVE_NP = True
except ImportError:
    HAVE_NP = False

EDGES = [-1.0, -0.5, 0.0, 0.5, 1.0]


def obs(**kw):
    o = {"quantity": "differential-cross-section", "variables": [{"name": "x", "unit": "1", "edges": list(EDGES)}],
         "phase_space": {"definition": "synthetic", "fiducial": False}, "level": "parton", "frame": "rest",
         "normalization": {"kind": "integrated-luminosity", "value": "not-applicable"}, "bin_semantics": "bin-averaged",
         "unit": "pb", "conventions": {"energy_variable": "sqrt_s"}}
    o.update(kw)
    return o


def pred(**kw):
    return {"observable": obs(**kw), "parameter_point": {"sqrt_s_gev": 5.0}, "status": [], "uncertainties": [],
            "allowed_transformations": None}


def meas(**kw):
    return {"observable": obs(**kw), "status": ["synthetic"], "uncertainties": [], "covariance": "present", "corrections": []}


COND = {"sqrt_s_gev": 5.0}
FOLD = [{"kind": "bin-integrate", "owner": "hep-theory"},
        {"kind": "multiply-by-normalization", "owner": "hep-statistics", "normalization_kind": "integrated-luminosity",
         "value": 10.0, "unit_in": "pb", "unit_out": "1"},
        {"kind": "forward-fold", "owner": "hep-statistics", "truth_edges": EDGES, "reco_edges": EDGES, "truth_level": "parton",
         "includes": ["migration", "efficiency"], "justification": "synthetic"}]
DET = dict(quantity="event-count", unit="1", level="detector", bin_semantics="bin-integrated")


class GateTests(unittest.TestCase):
    def fields(self, res):
        return [m["field"] for m in res["mismatches"]]

    def test_identical_observables_comparable(self):
        self.assertTrue(gate(pred(), meas(), [], [], COND)["comparable"])

    def test_forward_fold_chain_comparable_and_recorded(self):
        r = gate(pred(), meas(**DET), FOLD, [], COND)
        self.assertTrue(r["comparable"], r["mismatches"])
        self.assertEqual([t["kind"] for t in r["transformations"]], ["bin-integrate", "multiply-by-normalization", "forward-fold"])
        self.assertEqual(r["final_prediction_state"]["corrections"], ["normalization", "migration", "efficiency"])

    def test_every_mismatch_has_reason_and_resolution(self):
        r = gate(pred(unit="nb", frame="lab"), meas(), [], [], {})
        self.assertFalse(r["comparable"])
        self.assertTrue(all(m["reason"] and m["resolve"] for m in r["mismatches"]))

    def test_T08_wrong_level_units_binning_rejected(self):
        self.assertIn("level", self.fields(gate(pred(level="particle-fiducial"), meas(), [], [], COND)))
        self.assertIn("unit", self.fields(gate(pred(unit="nb"), meas(), [], [], COND)))
        coarse = pred(variables=[{"name": "x", "unit": "1", "edges": [-1.0, 0.0, 1.0]}])
        self.assertIn("binning", self.fields(gate(coarse, meas(), [], [], COND)))

    def test_T08_documented_conversions_accepted(self):
        conv = [{"kind": "unit-conversion", "owner": "hep-theory", "from": "nb", "to": "pb", "factor": 1000.0, "justification": "1 nb = 1000 pb"}]
        self.assertTrue(gate(pred(unit="nb"), meas(), conv, [], COND)["comparable"])
        fine = pred(variables=[{"name": "x", "unit": "1", "edges": [-1.0, -0.75, -0.5, 0.0, 0.25, 0.5, 1.0]}])
        rb = [{"kind": "bin-integrate", "owner": "hep-theory"}, {"kind": "rebin", "owner": "hep-theory", "edges": EDGES}]
        self.assertTrue(gate(fine, meas(bin_semantics="bin-integrated", quantity="cross-section"), rb, [], COND)["comparable"])

    def test_rebin_of_averages_needs_integration_first(self):
        fine = pred(variables=[{"name": "x", "unit": "1", "edges": [-1.0, -0.75, -0.5, 0.0, 0.25, 0.5, 1.0]}])
        r = gate(fine, meas(), [{"kind": "rebin", "owner": "hep-theory", "edges": EDGES}], [], COND)
        self.assertIn("transformations[0]", self.fields(r))

    def test_point_vs_bin_needs_mapping(self):
        p = pred(bin_semantics="point")
        self.assertIn("bin_semantics", self.fields(gate(p, meas(), [], [], COND)))
        r = gate(p, meas(bin_semantics="bin-integrated", quantity="cross-section"), [{"kind": "bin-integrate", "owner": "hep-theory"}], [], COND)
        self.assertIn("transformations[0]", self.fields(r))
        ok = gate(p, meas(bin_semantics="bin-integrated", quantity="cross-section"),
                  [{"kind": "bin-integrate", "owner": "hep-theory", "method": "analytic integral of the expression"}], [], COND)
        self.assertTrue(ok["comparable"])

    def test_fiducial_vs_inclusive_and_unfolded_vs_raw(self):
        self.assertIn("phase_space.fiducial", self.fields(gate(pred(), meas(phase_space={"definition": "cut", "fiducial": True}), [], [], COND)))
        r = gate(pred(level="unfolded"), meas(level="detector"), [], [], COND)
        self.assertTrue(any("not equivalent" in m["reason"] for m in r["mismatches"]))

    def test_T07_double_counted_efficiency_caught(self):
        t = copy.deepcopy(FOLD)
        t.insert(2, {"kind": "apply-correction", "owner": "hep-statistics", "effect": "efficiency", "justification": "test"})
        r = gate(pred(), meas(**DET), t, [], COND)
        self.assertFalse(r["comparable"])
        self.assertTrue(any("efficiency" in m["reason"] for m in r["mismatches"]))

    def test_T07_folding_a_detector_level_prediction_rejected(self):
        r = gate(pred(level="detector"), meas(**DET), FOLD, [], COND)
        self.assertFalse(r["comparable"])

    def test_correction_on_both_sides_rejected(self):
        m = meas(level="particle-fiducial")
        m["corrections"] = ["efficiency"]
        t = [{"kind": "level-identification", "owner": "hep-theory", "from": "parton", "to": "particle-fiducial", "justification": "test"},
             {"kind": "apply-correction", "owner": "hep-theory", "effect": "efficiency", "justification": "test"}]
        self.assertIn("corrections", self.fields(gate(pred(), m, t, [], COND)))

    def test_parameter_point_and_validity_range(self):
        self.assertIn("parameter_point.sqrt_s_gev", self.fields(gate(pred(), meas(), [], [], {"sqrt_s_gev": 6.0})))
        self.assertIn("parameter_point.sqrt_s_gev", self.fields(gate(pred(), meas(), [], [], {})))
        p = pred(validity_range={"x": [-0.5, 0.5]})
        self.assertIn("validity_range", self.fields(gate(p, meas(), [], [], COND)))

    def test_producer_restrictions_respected(self):
        p = pred()
        p["allowed_transformations"] = ["bin-integrate"]
        r = gate(p, meas(**DET), FOLD, [], COND)
        self.assertIn("transformations[1]", self.fields(r))

    def test_unjustified_level_identification_rejected(self):
        t = [{"kind": "level-identification", "owner": "hep-theory", "from": "parton", "to": "particle-fiducial"}]
        self.assertFalse(gate(pred(), meas(level="particle-fiducial"), t, [], COND)["comparable"])

    def test_T09_missing_covariance_and_envelope_stay_as_they_are(self):
        p = pred()
        p["uncertainties"] = [{"name": "scale", "kind": "scale-envelope", "correlation": "unknown"}]
        m = meas()
        m["covariance"] = "absent"
        r = gate(p, m, [], [], COND)
        self.assertTrue(r["comparable"])
        self.assertTrue(any(n["field"] == "covariance" for n in r["notes"]))
        self.assertEqual(r["measurement_covariance"], "absent")
        self.assertFalse(r["uncertainty_objects"]["prediction"][0]["gaussian_allowed"])
        self.assertFalse(r["uncertainty_objects"]["prediction"][0]["quantified"])

    def test_statuses_carried(self):
        self.assertEqual(gate(pred(), meas(), [], [], COND)["carried_statuses"], ["synthetic"])

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            pa, ma = Path(tmp) / "p.json", Path(tmp) / "m.json"
            pa.write_text(json.dumps({"artifact_type": "prediction", "status": [], "extension": {"observable": obs(), "parameter_point": {}}}))
            ma.write_text(json.dumps({"artifact_type": "dataset-record", "status": ["synthetic"],
                                      "extension": {"observable": obs(unit="nb"), "covariance": {"status": "present"}}}))
            run = lambda *a: subprocess.run([sys.executable, str(PLUGIN / "contracts" / "comparison" / "gate.py"), *a], capture_output=True, text=True)  # noqa: E731
            self.assertEqual(run(str(pa), str(ma)).returncode, 1)
            ma.write_text(json.dumps({"artifact_type": "dataset-record", "status": ["synthetic"],
                                      "extension": {"observable": obs(), "covariance": {"status": "present"}}}))
            self.assertEqual(run(str(pa), str(ma)).returncode, 0)
            self.assertEqual(run(str(pa), "/nonexistent.json").returncode, 2)


def profile(pid, ns, deps=()):
    return {"id": pid, "kind": "experiment", "version": "1.0.0", "vocabulary_namespaces": [ns], "depends_on": list(deps)}


class GateDefinitionAuditT01(unittest.TestCase):
    """Audit T01: the gate compares the physical definition (process, species, phase space) and every axis.

    Regression tests: each variant below was reported comparable before the fix."""

    def same(self, **kw):
        p, m = pred(**copy.deepcopy(kw)), meas(**copy.deepcopy(kw))
        p["parameter_point"] = {}
        return p, m

    def fields(self, res):
        return [x["field"] for x in res["mismatches"]]

    def test_identical_definitions_still_comparable(self):
        p, m = self.same(process="synthetic e+ e- -> mu+ mu-", species=[{"name": "muon"}],
                         phase_space={"definition": "synthetic fiducial region", "fiducial": True})
        self.assertTrue(gate(p, m, [], [], {})["comparable"])

    def test_a_process_change_not_comparable(self):
        p, m = self.same(process="synthetic e+ e- -> mu+ mu-")
        m["observable"]["process"] = "synthetic e+ e- -> tau+ tau-"
        r = gate(p, m, [], [], {})
        self.assertFalse(r["comparable"])
        self.assertIn("process", self.fields(r))
        self.assertEqual(r["status"], "unresolved")
        self.assertTrue(all(x["resolve"] for x in r["mismatches"]))

    def test_process_on_one_side_only_unresolved(self):
        p, m = self.same(process="synthetic e+ e- -> mu+ mu-")
        del m["observable"]["process"]
        self.assertIn("process", self.fields(gate(p, m, [], [], {})))

    def test_b_species_change_not_comparable(self):
        p, m = self.same(species=[{"name": "muon"}])
        m["observable"]["species"] = [{"name": "tau"}]
        r = gate(p, m, [], [], {})
        self.assertFalse(r["comparable"])
        self.assertIn("species", self.fields(r))

    def test_c_phase_space_change_not_comparable(self):
        p, m = self.same(phase_space={"definition": "synthetic fiducial region", "fiducial": True})
        m["observable"]["phase_space"] = {"definition": "|cos theta| < 0.5 and pT > 20 GeV", "fiducial": True}
        r = gate(p, m, [], [], {})
        self.assertFalse(r["comparable"])
        self.assertIn("phase_space", self.fields(r))

    def test_structured_phase_space_cuts_compared(self):
        cuts = [{"variable": "pT", "unit": "GeV", "low": 20.0, "high": None}]
        p, m = self.same(phase_space={"definition": "a", "fiducial": True, "cuts": cuts})
        m["observable"]["phase_space"] = {"definition": "b", "fiducial": True, "cuts": copy.deepcopy(cuts)}
        self.assertTrue(gate(p, m, [], [], {})["comparable"], "equal structured cuts decide, whatever the free text")
        m["observable"]["phase_space"]["cuts"][0]["low"] = 25.0
        r = gate(p, m, [], [], {})
        self.assertIn("phase_space.cuts", self.fields(r))
        self.assertEqual(r["status"], "not-comparable")

    def test_named_mapping_with_justification_resolves(self):
        p, m = self.same(process="e+e- -> mu+mu- (one photon)")
        m["observable"]["process"] = "e+e- -> mu+mu- (generator)"
        bare = [{"field": "process", "action": "equivalent"}]
        self.assertFalse(gate(p, m, [], bare, {})["comparable"], "a mapping without a justification is not evidence")
        mapped = [{"field": "process", "action": "equivalent", "justification": "same final state; the generator has no Z"}]
        r = gate(p, m, [], mapped, {})
        self.assertTrue(r["comparable"], r["mismatches"])
        self.assertEqual(r["definition_mappings_applied"], mapped)

    def test_d_second_axis_compared(self):
        two = [{"name": "x", "unit": "1", "edges": list(EDGES)}, {"name": "sqrt_s", "unit": "GeV", "edges": [80.0, 90.0, 100.0]}]
        p, m = self.same(variables=copy.deepcopy(two))
        self.assertTrue(gate(p, m, [], [], {})["comparable"])
        m["observable"]["variables"][1] = {"name": "pT", "unit": "TeV", "edges": [0.0, 1.0, 5.0]}
        r = gate(p, m, [], [], {})
        self.assertFalse(r["comparable"])
        self.assertTrue({"variables[1].name", "variables[1].unit", "variables[1].binning"} <= set(self.fields(r)), self.fields(r))

    def test_axis_transformations_on_multi_dimensional_rejected(self):
        two = [{"name": "x", "unit": "1", "edges": list(EDGES)}, {"name": "y", "unit": "1", "edges": [0.0, 1.0, 2.0]}]
        p, m = self.same(variables=copy.deepcopy(two), bin_semantics="bin-integrated", quantity="cross-section")
        m["observable"]["variables"][0]["edges"] = [-1.0, 0.0, 1.0]
        r = gate(p, m, [{"kind": "rebin", "owner": "hep-theory", "edges": [-1.0, 0.0, 1.0]}], [], {})
        self.assertFalse(r["comparable"])
        self.assertIn("multi-dimensional", r["mismatches"][0]["reason"])

    def test_fiducial_restriction_needs_matching_measurement_definition(self):
        cuts = [{"variable": "x", "unit": "1", "low": -0.5, "high": 0.5}]
        p = pred()
        p["parameter_point"] = {}
        m = meas(phase_space={"definition": "|x| < 0.5", "fiducial": True, "cuts": cuts},
                 variables=[{"name": "x", "unit": "1", "edges": [-0.5, 0.0, 0.5]}])
        t = [{"kind": "fiducial-restriction", "owner": "hep-theory", "variable": "x", "range": [-0.5, 0.5]}]
        r = gate(p, m, t, [], {})
        self.assertTrue(r["comparable"], r["mismatches"])
        m["observable"]["phase_space"] = {"definition": "|x| < 0.5", "fiducial": True}
        r = gate(p, m, t, [], {})
        self.assertEqual(r["status"], "unresolved")
        self.assertIn("phase_space", self.fields(r))


class ComposeTests(unittest.TestCase):
    def test_disjoint_namespaces_ok(self):
        r = compose([profile("experiment:a", "alpha"), profile("experiment:b", "beta")], ids=["alpha:D1", "beta:D2"])
        self.assertTrue(r["ok"], r)

    def test_namespace_collision_and_missing_dependency(self):
        r = compose([profile("experiment:a", "alpha"), profile("experiment:b", "alpha", ["experiment:c"])])
        codes = {e["code"] for e in r["errors"]}
        self.assertEqual(codes, {"compose.namespace_collision", "compose.missing_dependency"})

    def test_T06_same_local_name_distinct(self):
        r = compose([profile("experiment:ams-02", "ams02"), profile("experiment:b", "beta")], ids=["ams02:C01", "beta:C01"])
        self.assertTrue(r["ok"])
        self.assertTrue(any(n["code"] == "compose.same_local_name" for n in r["notes"]))

    def test_T06_correlation_needs_explicit_support(self):
        ps = [profile("experiment:ams-02", "ams02"), profile("experiment:b", "beta")]
        self.assertFalse(compose(ps, [{"between": ["ams02:C01", "beta:C01"]}])["ok"])
        ok = compose(ps, [{"between": ["ams02:C01", "beta:C01"], "assumption": {"justification": "synthetic test", "scope": "this test"}}])
        self.assertTrue(ok["ok"])

    def test_unqualified_and_unknown_namespace(self):
        r = compose([profile("experiment:a", "alpha")], ids=["C01", "gamma:C01"])
        self.assertEqual({e["code"] for e in r["errors"]}, {"compose.unqualified_id", "compose.unknown_namespace"})


def ds(i, aux=(), cov="present", **kw):
    return {"id": i, "observable": obs(**kw), "covariance": cov, "auxiliary": list(aux), "uncertainties": []}


ASSUME = {"justification": "synthetic test assumption", "scope": "this test only"}


class CombinationTests(unittest.TestCase):
    def codes(self, r):
        return {p["code"] for p in r["problems"]}

    def test_independence_is_never_assumed(self):
        r = plan_combination([ds("alpha:A"), ds("beta:B")])
        self.assertFalse(r["combinable"])
        self.assertEqual(r["treatment"], "comparison-only")
        self.assertIn("combine.cross_block_undeclared", self.codes(r))

    def test_declared_independence_with_scope_allowed(self):
        r = plan_combination([ds("alpha:A"), ds("beta:B")], [{"between": ["alpha:A", "beta:B"], "independent": True, "assumption": ASSUME}])
        self.assertTrue(r["combinable"], r["problems"])

    def test_T05_overlapping_auxiliary_requires_joint_treatment(self):
        dsets = [ds("alpha:A", ["alpha:lumi-calibration"]), ds("beta:B", ["alpha:lumi-calibration"])]
        r = plan_combination(dsets, [{"between": ["alpha:A", "beta:B"], "independent": True, "assumption": ASSUME}])
        self.assertIn("combine.overlap_undeclared", self.codes(r))
        self.assertIn("combine.independence_contradicted", self.codes(r))
        r = plan_combination(dsets, [{"between": ["alpha:A", "beta:B"], "source": "alpha:lumi-calibration", "assumption": ASSUME}])
        self.assertTrue(r["combinable"], r["problems"])

    def test_T09_missing_covariance_blocks_combination(self):
        r = plan_combination([ds("alpha:A", cov="absent"), ds("beta:B")],
                             [{"between": ["alpha:A", "beta:B"], "independent": True, "assumption": ASSUME}])
        self.assertIn("combine.covariance_missing", self.codes(r))

    def test_envelope_not_gaussianized(self):
        a = ds("alpha:A")
        a["uncertainties"] = [{"name": "scale", "kind": "scale-envelope", "correlation": "unknown"}]
        r = plan_combination([a, ds("beta:B")], [{"between": ["alpha:A", "beta:B"], "independent": True, "assumption": ASSUME}])
        self.assertIn("combine.non_gaussian_component", self.codes(r))

    def test_different_observables_refused(self):
        r = plan_combination([ds("alpha:A"), ds("beta:B", unit="nb")], [{"between": ["alpha:A", "beta:B"], "independent": True, "assumption": ASSUME}])
        self.assertIn("combine.not_same_observable", self.codes(r))

    def test_unsupported_correlation_refused(self):
        r = plan_combination([ds("alpha:A"), ds("beta:B")], [{"between": ["alpha:A", "beta:B"], "source": "x"}])
        self.assertIn("combine.correlation_unsupported", self.codes(r))


@unittest.skipUnless(HAVE_NP, "numpy required")
class GlsTests(unittest.TestCase):
    """T04: two illustrative datasets, same observable, declared shared covariance."""

    def doc(self, ya, yb, cov):
        n = len(ya)
        return {"datasets": [dict(ds("alpha:A", ["alpha:norm"], variables=[{"name": "x", "unit": "1", "edges": EDGES[:n + 1]}]), values=ya),
                             dict(ds("beta:B", ["alpha:norm"], variables=[{"name": "x", "unit": "1", "edges": EDGES[:n + 1]}]), values=yb)],
                "correlations": [{"between": ["alpha:A", "beta:B"], "source": "alpha:norm", "assumption": ASSUME}],
                "joint_covariance": cov}

    def test_one_bin_matches_textbook_blue(self):
        import combine_measurements as cm
        s1, s2, rho, y1, y2 = 1.0, 2.0, 0.3, 10.0, 12.0
        cov = [[s1 ** 2, rho * s1 * s2], [rho * s1 * s2, s2 ** 2]]
        r = cm.combine(self.doc([y1], [y2], cov))
        self.assertEqual(r["status"], "combined", r)
        w1 = (s2 ** 2 - rho * s1 * s2) / (s1 ** 2 + s2 ** 2 - 2 * rho * s1 * s2)
        var = (s1 ** 2 * s2 ** 2 * (1 - rho ** 2)) / (s1 ** 2 + s2 ** 2 - 2 * rho * s1 * s2)
        self.assertAlmostEqual(r["values"][0], w1 * y1 + (1 - w1) * y2, places=12)
        self.assertAlmostEqual(r["covariance"][0][0], var, places=12)

    def test_multibin_shared_normalization_matches_whitened_least_squares(self):
        import combine_measurements as cm
        ya, yb = np.array([100.0, 80.0, 60.0]), np.array([104.0, 79.0, 63.0])
        stat = np.diag(np.concatenate([ya, yb]))
        y = np.concatenate([ya, yb])
        norm = 0.02 ** 2 * np.outer(y, y)  # one shared normalization: fully correlated across both datasets
        cov = stat + norm
        r = cm.combine(self.doc(ya.tolist(), yb.tolist(), cov.tolist()))
        self.assertEqual(r["status"], "combined", r)
        L = np.linalg.cholesky(cov)
        h = np.vstack([np.eye(3), np.eye(3)])
        ref, *_ = np.linalg.lstsq(np.linalg.solve(L, h), np.linalg.solve(L, y), rcond=None)
        np.testing.assert_allclose(r["values"], ref, rtol=1e-12)

    def test_refused_without_declared_overlap(self):
        import combine_measurements as cm
        d = self.doc([1.0], [1.0], [[1.0, 0.0], [0.0, 1.0]])
        d["correlations"] = []
        self.assertEqual(cm.combine(d)["status"], "refused")

    def test_non_positive_definite_refused(self):
        import combine_measurements as cm
        self.assertEqual(cm.combine(self.doc([1.0], [1.0], [[1.0, 2.0], [2.0, 1.0]]))["status"], "refused")


def prediction_doc(aid, spec, values, status=("synthetic",)):
    return {"artifact_id": aid, "artifact_type": "prediction", "status": list(status), "bindings": {"experiments": [], "theory": []},
            "extension": {"observable": obs(), "theory_spec_ref": spec, "parameter_point": {"sqrt_s_gev": 5.0},
                          "representation": "numerical", "values": {"edges": EDGES, "values": values, "unit": "pb"},
                          "uncertainties": [], "allowed_transformations": []}}


class ModelSetTests(unittest.TestCase):
    """T03: no experiment; two competing models keep distinct assumptions."""

    def setUp(self):
        self.a = prediction_doc("model-a", "specs/a.json", [1.0, 2.0, 2.0, 1.0])
        self.b = prediction_doc("model-b", "specs/b.json", [1.2, 1.8, 2.2, 0.9])

    def test_alternatives_kept_distinct_without_experiment(self):
        ms = model_set([self.a, self.b])
        self.assertTrue(ms["ok"], ms["problems"])
        self.assertEqual([a["theory_spec_ref"] for a in ms["alternatives"]], ["specs/a.json", "specs/b.json"])
        self.assertTrue(all(a["experiment_bindings"] == [] for a in ms["alternatives"]))

    def test_shared_spec_rejected(self):
        b = copy.deepcopy(self.b)
        b["extension"]["theory_spec_ref"] = "specs/a.json"
        self.assertFalse(model_set([self.a, b])["ok"])

    def test_envelope_needs_prescription_and_is_not_gaussian(self):
        ms = model_set([self.a, self.b])
        vals = {"model-a": self.a["extension"]["values"]["values"], "model-b": self.b["extension"]["values"]["values"]}
        self.assertFalse(envelope(ms, vals)["ok"])
        env = envelope(ms, vals, {"kind": "min-max", "owner": "hep-theory", "justification": "synthetic test"})
        self.assertTrue(env["ok"])
        self.assertFalse(env["uncertainty"]["gaussian"])
        self.assertEqual(env["uncertainty"]["lower"], [1.0, 1.8, 2.0, 0.9])

    def test_validator_rejects_gaussianized_model_alternative(self):
        doc = {"contract_version": "1.0.0", "artifact_id": "x", "artifact_type": "prediction", "objective": "synthetic",
               "provenance": {"producer_skill": "hep-theory", "created": "2026-10-02"}, "status": ["synthetic"],
               "bindings": {"experiments": [], "theory": []}, "versions": {"plugin": "0.1.0", "contracts": "1.0.0", "profiles": {}},
               "inputs": [], "outputs": [], "unresolved_inputs": [],
               "extension": {"observable": obs(), "parameter_point": {}, "representation": "numerical", "allowed_transformations": [],
                             "uncertainties": [{"name": "models", "kind": "model-alternative", "correlation": "unknown", "gaussian": True}]}}
        r = validate_artifact(doc)
        self.assertIn("uncertainty.auto_gaussian", {f.code for f in r.errors})


if __name__ == "__main__":
    unittest.main()
