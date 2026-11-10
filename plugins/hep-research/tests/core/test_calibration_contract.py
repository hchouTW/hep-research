"""core/calibration/contract (simulator calibration phase 0): calib_contract check, Part B section 5.2 in phase-0 scope.

One negative test per named case of section 15.3.2 (contract rules) and the contract-side cases of sections 15.3.3 and
15.3.13; D5 (sub-shape after exclusion, approval A6), D38 and clause 9 items 1, 5, 6, 9, 11. Each case changes one
thing in the valid toy-detector contract of calibration_fixtures and expects its finding code."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_fixtures as F  # noqa: E402
from core.calibration import contract as cc  # noqa: E402


def codes(c, rel=None, **kw):
    return {f["code"] for f in cc.check(c, rel if rel is not None else F.releases(), **kw)["findings"]}


def shape(name, role, K=3, **kw):
    bins = [f"b{i}" for i in range(K)]
    o = F.observable(name, role, estimator="binned-fractions", range="simplex", link="alr", functional="shape",
                     vector={"K": K, "bins": bins, "reference_category": bins[-1], "data_side": "count"},
                     shape_class="free-omega", N_decl={"value": 50, "basis": "exposure times an external rate"})
    o.pop("value_conventions")
    o.update(kw)
    return o


class Baseline(unittest.TestCase):
    def test_valid_contract_accepted(self):
        r = cc.check(F.contract(), F.releases())
        self.assertEqual((r["status"], r["findings"]), ("accepted", []))
        self.assertTrue(any("phase 2" in d for d in r["deferred"]))      # model-quantity rules listed, not skipped
        self.assertEqual(len(cc.lock_hash(F.contract())), 64)


class ContractRules_15_3_2(unittest.TestCase):
    def assertRejected(self, c, code, rel=None, **kw):
        got = codes(c, rel, **kw)
        self.assertIn(code, got, got)

    def test_contains_data_values(self):
        c = F.contract()
        c["observables"][0]["observed_value"] = 1.234
        self.assertRejected(c, "contract.data_values")

    def test_roles_overlap(self):
        c = F.contract()
        c["observables"].append(F.observable("energy_mean", "validation", "val_sample"))
        self.assertRejected(c, "observables.role_overlap")

    def test_dependency_cycle(self):
        c = F.contract()
        self.assertRejected(c, "upstream.cycle", series_graph={"toy-holdout": ["other"], "other": ["toy-holdout"]})
        self.assertNotIn("upstream.cycle", codes(c, series_graph={"toy-holdout": ["other"], "other": []}))

    def test_stage_graph_cycle(self):
        c = F.contract()
        c["stage_graph"]["edges"].append({"from": "gain", "to": "photon_generation"})
        self.assertRejected(c, "graph.cycle")

    def test_simulation_bins_by_true_value(self):
        c = F.contract()
        c["observables"][0]["binning"] = {"variable_level": "true"}
        self.assertRejected(c, "observables.true_binning")

    def test_model_enumerated_and_absorbed(self):
        c = F.contract()
        c["models"]["absorbed"] = [{"id": "nominal"}]
        self.assertRejected(c, "models.enumerated_and_absorbed")

    def test_inferred_form_without_holdout(self):
        c = F.contract()
        c["model_discrepancy"]["form"] = "inferred"
        self.assertNotIn("model_discrepancy.inferred_mode", codes(c))
        c["validation"]["mode"] = "cross-validation"
        self.assertRejected(c, "model_discrepancy.inferred_mode")

    def test_kernel_not_positive_definite(self):
        c = F.contract()
        c["model_discrepancy"]["kernel"] = {"type": "matrix", "matrix": [[1.0, 2.0], [2.0, 1.0]]}
        self.assertRejected(c, "model_discrepancy.kernel_not_pd")
        c["model_discrepancy"]["kernel"] = {"type": "matrix", "matrix": [[1.0, 0.5], [0.5, 1.0]]}
        self.assertNotIn("model_discrepancy.kernel_not_pd", codes(c))
        c["model_discrepancy"]["kernel"] = {"type": "cosine"}
        self.assertRejected(c, "model_discrepancy.kernel_not_pd")

    def test_block_rule(self):
        c = F.contract()
        c["observables"][1]["block"] = "binomial"           # shares cal_sample with energy_mean
        self.assertRejected(c, "observables.block_rule")

    def test_injection_without_node_split(self):
        c = F.contract()
        c["references"][1]["edge"] = {"inside": "photon_generation"}
        self.assertRejected(c, "reference.injection_not_split")
        c = F.contract()
        c["references"][1]["edge"] = {"from": "input", "to": "pde"}       # not an edge of the graph
        self.assertRejected(c, "reference.injection_not_split")

    def test_link_range_mismatch(self):
        c = F.contract()
        c["observables"][0].update(range="unit-interval", link="log")    # log for a tail probability
        self.assertRejected(c, "observables.link_range")
        c = F.contract()
        c["observables"][0].update(range="signed", link="log")           # log for a signed quantity
        self.assertRejected(c, "observables.link_range")

    def test_shape_bins_as_scalars_or_k_minus_1(self):
        c = F.contract()
        c["observables"].append(F.observable("frac_b0", "calibration", "cal_sample", range="unit-interval",
                                             link="logit", bin_of="spectrum"))
        self.assertRejected(c, "observables.shape_bin_as_scalar")
        c = F.contract()
        s = shape("spectrum", "calibration", sample=None)
        s["vector"]["bins"] = s["vector"]["bins"][:-1]                   # only K-1 bins
        c["observables"].append(s)
        self.assertRejected(c, "observables.shape_bins")
        c = F.contract()
        c["observables"].append(shape("spectrum", "calibration", link="logit"))
        self.assertRejected(c, "observables.shape_logit")

    def test_merging_rule(self):
        """n_min at the evaluation points is phase 2; phase 0 requires the merging rule, never by observed counts."""
        c = F.contract()
        s = shape("spectrum", "calibration", sample="cal_sample")
        s["vector"]["data_side"] = "gaussian-summary"
        c["observables"].append(s)
        self.assertRejected(c, "observables.merging_rule")
        s["vector"]["merging_rule"] = {"defined_by": "observed-counts"}
        self.assertRejected(c, "observables.merging_observed")
        s["vector"]["merging_rule"] = {"defined_by": "design-expectation", "n_min": 20}
        self.assertNotIn("observables.merging_rule", codes(c))

    def test_conversion_relation_missing(self):
        c = F.contract()
        del c["references"][1]["conversion"]
        self.assertRejected(c, "references.conversion_missing")
        c = F.contract()
        c["references"][1]["conversion"]["parameters"] = ["led_alpha"]   # not listed as phi
        self.assertRejected(c, "references.conversion_phi")

    def test_redundant_measurement_without_comparison_node(self):
        c = F.contract()
        c["references"][3]["edge"] = {"out_of": "module_a"}
        c["references"][3]["observation"] = "module_a"
        self.assertRejected(c, "reference.redundant_without_comparison")
        c = F.contract()
        c["stage_graph"]["edges"].append({"from": "gain", "to": "energy_ratio"})   # three upstreams
        self.assertRejected(c, "graph.comparison_upstream")

    def test_upstream_usage_and_role(self):
        c = F.contract()
        c["upstream"] = [{"result_sha256": F.h("up"), "usages": []}]
        self.assertRejected(c, "upstream.usage")
        c["upstream"] = [{"result_sha256": F.h("up"), "usages": ["envelope", "nuisance-posterior"], "role": "variation"}]
        self.assertRejected(c, "upstream.role_mismatch")
        c["upstream"] = [{"result_sha256": "0.97", "usages": ["xi"]}]
        self.assertRejected(c, "upstream.not_hash")


class OtherClauses(unittest.TestCase):
    def test_parameters(self):
        c = F.contract()
        del c["parameters"][0]["sampling_bounds"]
        self.assertIn("parameters.bounds", codes(c))
        c = F.contract()
        phi = next(p for p in c["parameters"] if p["role"] == "phi")
        del phi["source"]
        self.assertIn("parameters.phi_source", codes(c))
        c = F.contract()
        c["parameters"].append({"name": "temperature", "role": "psi", "nodes": ["gain"],
                                "uncertainty": "non-negligible"})
        self.assertIn("parameters.psi_uncertainty", codes(c))

    def test_physics_list_confirmation(self):
        c = F.contract()
        c["models"]["enumerated"] = [{"id": "a", "physics_list": "PL_A"}, {"id": "b", "physics_list": "PL_B"}]
        self.assertIn("models.physics_list_unconfirmed", codes(c))
        c["models"]["physics_list_confirmations"] = [{"physics_lists": ["PL_A", "PL_B"], "record": "note-1"}]
        self.assertNotIn("models.physics_list_unconfirmed", codes(c))

    def test_g4sim_source(self):
        c = F.contract()
        c["simulator"], c["source"] = "g4sim", {"density": "external"}
        self.assertIn("source.external", codes(c))
        c["source"] = {"density": "analytic"}
        self.assertNotIn("source.external", codes(c))

    def test_estimators_and_conventions(self):
        c = F.contract()
        c["estimators"]["uses_truth"] = True
        self.assertIn("estimators.truth", codes(c))
        c = F.contract()
        del c["observables"][0]["value_conventions"]["zero_denominator"]
        self.assertIn("observables.value_conventions", codes(c))

    def test_d5_subshape_after_exclusion(self):
        """A6 (D5): the sub-shape left after excluding a bin of a free-omega count shape is a new free-omega shape,
        with its own N_decl and recorded basis, N_decl >= 10; a missing declaration rejects."""
        c = F.contract()
        sub = shape("spectrum_sub", "validation", K=2, sample=None, redeclared_from={"shape": "spectrum",
                                                                                  "excluded_bins": ["b2"]})
        c["observables"].append(sub)
        c["validation"]["unused"].append({"observable": "spectrum.b2", "reason": "rank condition (c)",
                                          "clause": "section 9.2"})
        rel = F.releases()
        rel[F.VAL]["observables"] += [{"name": "spectrum_sub"}, {"name": "spectrum.b2"}]
        self.assertNotIn("observables.n_decl_basis", codes(c, rel))
        del sub["N_decl"]
        self.assertIn("observables.n_decl_basis", codes(c, rel))
        sub["N_decl"] = {"value": 9, "basis": "exposure times an external rate"}
        self.assertIn("observables.n_decl_small", codes(c, rel))

    def test_d38_subshape_k1(self):
        c = F.contract()
        c["observables"].append(shape("spectrum_sub", "calibration", K=1, sample=None, shape_class="conditioned",
                                      redeclared_from={"shape": "spectrum", "excluded_bins": ["b1", "b2"]}))
        self.assertIn("observables.subshape_k1", codes(c))

    def test_absolute_normalization(self):
        c = F.contract()
        c["event_samples"][1] = {"id": "val_sample", "normalization": "absolute"}      # field missing means no
        self.assertIn("samples.sim_absolute_normalization", codes(c))
        c["event_samples"][1]["sim_absolute_normalization"] = {"value": "yes", "basis": "cross section x lumi"}
        self.assertNotIn("samples.sim_absolute_normalization", codes(c))

    def test_n_decl_s(self):
        c = F.contract()
        del c["event_samples"][0]["components"][0]["basis"]
        self.assertIn("samples.n_decl_s", codes(c))
        c = F.contract()
        c["event_samples"][0]["components"][0]["N_decl"] = 999                  # observed basis: 1000 in the release
        self.assertIn("samples.n_decl_s_unequal", codes(c))

    def test_exact_relation_in_validation_sample(self):
        c = F.contract()
        c["observables"].append(F.observable("ratio_width", "validation", "val_sample", functional="core-width"))
        c["validation"]["exact_relations"] = [{"sample": "val_sample", "observables": ["ratio_mean", "ratio_width"]}]
        rel = F.releases()
        rel[F.VAL]["observables"].append({"name": "ratio_width"})
        self.assertIn("validation.exact_relation_all_used", codes(c, rel))

    def test_validation_declarations(self):
        c = F.contract()
        del c["validation"]["N_d"]
        self.assertIn("validation.N_d_missing", codes(c))
        c = F.contract()
        c["validation"]["N_dc"] = [{"n": {"energy_mean": 1.0}, "construction": "sum by definition"}]   # no c
        self.assertIn("validation.N_dc_item", codes(c))
        c = F.contract()
        c["validation"]["unused"] = []
        self.assertIn("validation.unused_mismatch", codes(c))
        c = F.contract()
        c["validation"]["alternatives"] = []
        self.assertIn("validation.no_alternative", codes(c))
        c["validation"]["mode"] = "none"
        self.assertNotIn("validation.no_alternative", codes(c))

    def test_15_3_1_p7_parameter_shift_alternative(self):
        c = F.contract()
        c["validation"]["alternatives"] = [{"kind": "parameter-shift", "description": "nu_k = 2"}]
        self.assertIn("validation.alternative_shift", codes(c))

    def test_untestable(self):
        rel = F.releases()
        rel[F.VAL]["declarations"]["has_value"]["ratio_mean"] = False
        self.assertIn("validation.untestable_used", codes(F.contract(), rel))
        c = F.contract()
        c["validation"]["unused"][0]["reason"] = "untestable"           # 'spare' is declared to have a value
        self.assertIn("validation.untestable_has_value", codes(c))

    def test_non_gaussian_block_before_phase_2(self):
        c = F.contract()
        c["observables"][2]["block"] = "poisson"
        self.assertIn("validation.block_unsupported", codes(c))


class DataReleaseAndSharing(unittest.TestCase):
    def test_15_3_3_observed_only_statistical(self):
        rel = F.releases()
        rel[F.CAL]["declarations"]["uncertainty_sources"]["energy_mean"]["statistical"] = "observed"
        self.assertIn("validation.observed_only", codes(F.contract(), rel))

    def test_15_3_13_holdout_shares_events(self):
        rel = F.releases()
        rel[F.VAL]["lineage"]["raw_units"] = [f"evt-{i:04d}" for i in range(700, 1500)]   # overlap 300
        self.assertIn("validation.holdout_shares_units", codes(F.contract(), rel))
        c = F.contract()
        c["validation"]["mode"] = "cross-validation"
        c["validation"]["unused"] = []
        self.assertNotIn("validation.holdout_shares_units", codes(c, rel))

    def test_15_3_13_mixed_sample(self):
        """A validation summary statistic sharing events with calibration observables, taken from a sample with
        events only in the validation release, is rejected (mixed sample)."""
        rel = F.releases()
        rel[F.CAL]["samples"]["cal_sample"]["raw_units"] = [f"evt-{i:04d}" for i in range(500, 1300)]
        self.assertIn("samples.not_contained", codes(F.contract(), rel))


if __name__ == "__main__":
    unittest.main()
