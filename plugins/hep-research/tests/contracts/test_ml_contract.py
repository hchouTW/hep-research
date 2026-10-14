"""ml-artifact content semantics (physics-ml review 2026-10-13, part D).

The review found that contracts/validate.py checked only that ml-artifact fields exist: it passed a blank grouping key,
an empty model_hash, empty labels or features, a training domain keyed on variables that are not features or with
inverted ranges, and had no place for the split-overlap result, the domain-shift check or the seeds; a calibration was
optional and unchecked. Contracts 2.5.0 report these natively; a 2.4.0 artifact keeps its outcome and gets them with
--strict. All fixtures SYNTHETIC."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts import validate as v  # noqa: E402

ART = ROOT / "contracts" / "fixtures" / "artifacts"
CURRENT = json.loads((ART / "valid" / "ml_artifact_v25.json").read_text())
LEGACY_1_0 = json.loads((ART / "valid" / "ml_artifact.json").read_text())


def codes(rep, level="error"):
    return {f.code for f in rep.findings if f.severity == level}


def splits(**kw):
    def f(e):
        e["splits"].update(kw)
    return f


# name -> (mutation of the extension, level, code)
MUTATIONS = {
    "blank_grouping_key": (splits(grouping_key=" \t"), "error", "ml.no_grouping"),
    "empty_model_hash": (lambda e: e.update(model_hash=""), "error", "ml.model_hash_missing"),
    "blank_model_hash": (lambda e: e.update(model_hash="   "), "error", "ml.model_hash_missing"),
    "empty_labels": (lambda e: e.update(labels=[]), "error", "ml.labels_missing"),
    "empty_features": (lambda e: e.update(features=[], training_domain={}), "error", "ml.features_missing"),
    "domain_unknown_feature": (lambda e: e["training_domain"].update(pt=[0.0, 1.0]), "error",
                               "ml.training_domain_unknown_feature"),
    "domain_inverted": (lambda e: e["training_domain"].update(x=[1.0, 0.0]), "error", "ml.training_domain_range"),
    "domain_empty_range": (lambda e: e["training_domain"].update(x=[0.5, 0.5]), "error", "ml.training_domain_range"),
    "domain_not_a_pair": (lambda e: e["training_domain"].update(x=[0.0]), "error", "ml.training_domain_range"),
    "overlap_failed": (splits(overlap_check={"tool": "check_split_integrity.py", "result": "fail"}), "error", "ml.split_overlap"),
    "test_groups_shared": (splits(test_groups_disjoint=False), "error", "ml.split_overlap"),
    "overlap_not_run": (splits(overlap_check={"tool": "check_split_integrity.py", "result": "not-run"}), "unresolved",
                        "ml.split_overlap_not_run"),
    "overlap_unrecorded": (lambda e: e["splits"].pop("overlap_check"), "warning", "ml.split_overlap_unchecked"),
    "probability_uncalibrated": (lambda e: e.pop("calibration"), "error", "ml.calibration_missing"),
    "density_ratio_uncalibrated": (lambda e: (e.pop("calibration"), e.update(output_semantics="density-ratio")), "error",
                                   "ml.calibration_missing"),
    "inference_uncalibrated": (lambda e: (e.pop("calibration"), e.pop("output_semantics"), e.update(task="inference")),
                               "error", "ml.calibration_missing"),
    "calibration_on_fit_sample": (lambda e: e["calibration"]["validation"].update(sample="val"), "error",
                                  "ml.calibration_on_fit_sample"),
    "calibration_incomplete": (lambda e: e["calibration"].pop("fit_sample"), "error", "ml.calibration_incomplete"),
    "calibration_no_after": (lambda e: e["calibration"]["validation"].pop("after"), "error", "ml.calibration_incomplete"),
    "negative_weights_dropped": (lambda e: e["weights"].update(negative_weight_treatment="dropped"), "warning",
                                 "ml.negative_weights_dropped"),
    "no_seeds": (lambda e: e["environment"].pop("seeds"), "warning", "ml.seeds_missing"),
    "no_environment": (lambda e: e.pop("environment"), "warning", "ml.seeds_missing"),
    "no_domain_shift": (lambda e: e.pop("domain_shift"), "unresolved", "ml.domain_shift_missing"),
    "domain_shift_not_checked": (lambda e: e["domain_shift"].update(status="not-checked"), "unresolved",
                                 "ml.domain_shift_missing"),
    "domain_shift_failed": (lambda e: e["domain_shift"].update(status="failed"), "unresolved", "ml.domain_shift_failed"),
}


def mutated(name, version=None):
    doc = copy.deepcopy(CURRENT)
    if version:
        doc["contract_version"] = version
        doc["versions"]["contracts"] = version
    MUTATIONS[name][0](doc["extension"])
    return doc


class MlSemanticsTests(unittest.TestCase):
    def test_current_fixture_is_clean(self):
        self.assertEqual(CURRENT["contract_version"], CONTRACTS_VERSION)
        rep = v.validate_artifact(copy.deepcopy(CURRENT))
        self.assertEqual(rep.findings, [], rep.as_dict())

    def test_each_mutation_is_reported_natively_at_its_level(self):
        for name, (_, level, code) in MUTATIONS.items():
            with self.subTest(name):
                rep = v.validate_artifact(mutated(name))
                self.assertIn(code, codes(rep, level), rep.as_dict())
                self.assertEqual(rep.ok, level != "error")

    def test_2_4_artifact_keeps_its_outcome_and_strict_reports(self):
        for name, (_, level, code) in MUTATIONS.items():
            with self.subTest(name):
                doc = mutated(name, version="2.4.0")
                rep = v.validate_artifact(doc)
                self.assertNotIn(code, codes(rep, level))
                self.assertTrue(rep.ok, rep.as_dict())
                self.assertIn(code, codes(v.validate_artifact(doc, strict=True), level))

    def test_legacy_1_0_fixture_unchanged_and_strict(self):
        rep = v.validate_artifact(copy.deepcopy(LEGACY_1_0))
        self.assertTrue(rep.ok)
        self.assertFalse({f.code for f in rep.findings} - {"ml.no_downstream_validation"})
        strict = v.validate_artifact(copy.deepcopy(LEGACY_1_0), strict=True)
        self.assertTrue(strict.ok, strict.as_dict())
        self.assertIn("ml.split_overlap_unchecked", codes(strict, "warning"))
        self.assertIn("ml.seeds_missing", codes(strict, "warning"))

    def test_existing_rules_kept(self):
        doc = copy.deepcopy(CURRENT)
        doc["extension"]["splits"]["grouping_key"] = ""
        self.assertIn("ml.no_grouping", codes(v.validate_artifact(doc)))
        doc = copy.deepcopy(CURRENT)
        doc["extension"]["downstream_validation"] = [{"metric": "AUC"}]
        self.assertIn("ml.auc_only", codes(v.validate_artifact(doc)))
        doc = copy.deepcopy(CURRENT)
        doc["extension"]["downstream_validation"] = []
        self.assertIn("ml.no_downstream_validation", codes(v.validate_artifact(doc), "unresolved"))
        self.assertNotIn("ml.domain_shift_missing", codes(v.validate_artifact(doc), "unresolved"))
        doc = copy.deepcopy(CURRENT)
        doc["extension"].update(task="surrogate", training_domain={})
        self.assertIn("ml.no_training_domain", codes(v.validate_artifact(doc)))

    def test_weights_string_and_object_forms(self):
        doc = copy.deepcopy(CURRENT)
        doc["extension"]["weights"] = "generator weights"
        self.assertIn("ml.weights_unstructured", codes(v.validate_artifact(doc)))  # free text: error from 2.8.0
        legacy = copy.deepcopy(doc)
        legacy["contract_version"] = legacy["versions"]["contracts"] = "2.7.0"
        self.assertTrue(v.validate_artifact(legacy).ok)  # a 2.7 artifact keeps its outcome
        doc["extension"]["weights"] = {"source": "generator", "negative_weight_treatment": "clipped", "used_in": ["loss"]}
        self.assertIn("schema.any_of", codes(v.validate_artifact(doc)))
        doc["extension"]["weights"] = {"source": "generator", "negative_weight_treatment": "signed", "used_in": ["fit"]}
        self.assertIn("schema.any_of", codes(v.validate_artifact(doc)))

    def test_new_field_enums(self):
        for path, value in ((("output_semantics",), "logit"), (("splits", "overlap_check", "result"), "passed"),
                            (("domain_shift", "status"), "ok")):
            with self.subTest(path):
                doc = copy.deepcopy(CURRENT)
                tgt = doc["extension"]
                for k in path[:-1]:
                    tgt = tgt[k]
                tgt[path[-1]] = value
                self.assertIn("schema.enum", codes(v.validate_artifact(doc)))

    def test_features_as_objects(self):
        doc = copy.deepcopy(CURRENT)
        doc["extension"]["features"] = [{"name": "x", "unit": "GeV"}, {"name": "y", "unit": "1"}]
        self.assertTrue(v.validate_artifact(doc).ok)

    def test_cli_strict_flag(self):
        import io
        import tempfile
        from contextlib import redirect_stdout
        doc = mutated("domain_inverted", version="2.4.0")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ml.json"
            path.write_text(json.dumps(doc))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(v.main([str(path)]), 0)
                self.assertEqual(v.main([str(path), "--strict"]), 1)



ML_V28_RULES = {  # every ml-artifact code contracts 2.8.0 added (physics-ml audit, PML), plus the statistical-result link
    "ml.calibration_after_not_numeric", "ml.calibration_not_improving", "ml.calibration_on_training_sample",
    "ml.device_free_text", "ml.domain_shift_on_training_sample", "ml.domain_shift_outcome_missing",
    "ml.domain_shift_status_missing", "ml.domain_shift_uncorrected", "ml.downstream_incomplete", "ml.downstream_ml_only",
    "ml.downstream_passed_contradicts", "ml.downstream_unstructured", "ml.duplicate_features",
    "ml.extrapolation_policy_action", "ml.framework_version_missing", "ml.grouping_row_level", "ml.handoff_unknown",
    "ml.label_is_feature", "ml.misspelled_key", "ml.model_hash_malformed", "ml.multiclass_calibration_scope",
    "ml.negative_weights_abs", "ml.output_semantics_missing", "ml.output_semantics_task_mismatch",
    "ml.precision_free_text", "ml.preprocessing_not_on_train", "ml.single_label", "ml.split_check_unverified",
    "ml.status_unsupported", "ml.task_validation_incomplete", "ml.task_validation_missing", "ml.threshold_from_test",
    "ml.training_domain_missing", "ml.training_domain_partial", "ml.training_domain_unbounded",
    "ml.two_sample_power_missing", "ml.units_unknown_feature", "ml.weights_contradiction", "ml.weights_not_split",
    "ml.weights_unstructured", "ml.weights_used_in_empty", "ml.weights_used_in_inconsistent",
    "stats.observable_source_unlinked",
}
LEVEL = {"invalid": "error", "unresolved": "unresolved", "warning": "warning"}


def v28_cases():
    cases = json.loads((ART / "cases.json").read_text())
    valid = [n for n in cases["valid"] if n.startswith(("ml_v28_", "statres_v28_"))]
    neg = {g: {n: c for n, c in cases[g].items() if n.startswith(("ml_v28_", "statres_v28_"))} for g in LEVEL}
    return valid, neg


class MlV28FixtureTests(unittest.TestCase):
    """CHECK-0.10.0 G-6: committed fixtures (tests/contracts/make_fixtures.py, ml_v28_* and statres_v28_*) for every
    ml-artifact rule of contracts 2.8.0; before, the rules were exercised only in memory by the mutation probe."""

    def test_every_2_8_rule_has_a_committed_fixture(self):
        _, neg = v28_cases()
        covered = set().union(*(set(c) for g in neg.values() for c in g.values()))
        self.assertEqual(ML_V28_RULES - covered, set())

    def test_fixtures_report_their_codes_at_their_level(self):
        valid, neg = v28_cases()
        self.assertGreaterEqual(len(valid), 4)
        for name in valid:
            with self.subTest(name):
                rep = v.validate_artifact(json.loads((ART / "valid" / name).read_text()))
                self.assertEqual(rep.findings, [], rep.as_dict())
        for group, cases in neg.items():
            for name, expected in cases.items():
                with self.subTest(name):
                    rep = v.validate_artifact(json.loads((ART / group / name).read_text()))
                    self.assertEqual(rep.ok, group != "invalid", rep.as_dict())
                    self.assertLessEqual(set(expected), codes(rep, LEVEL[group]), rep.as_dict())

    def test_negatives_restamped_2_7_report_under_strict(self):
        _, neg = v28_cases()
        for group, cases in neg.items():
            for name, expected in cases.items():
                if name == "ml_v28_weights_not_split.json":
                    continue  # native only by design: a 2.7.0 artifact had no training/evaluation weights split
                with self.subTest(name):
                    doc = json.loads((ART / group / name).read_text())
                    doc["contract_version"] = doc["versions"]["contracts"] = "2.7.0"
                    found = {f.code for f in v.validate_artifact(doc, strict=True).findings}
                    self.assertLessEqual(set(expected), found)


if __name__ == "__main__":
    unittest.main()
