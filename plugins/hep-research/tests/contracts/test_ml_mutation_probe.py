"""ml-artifact mutation probe (physics-ml audit, source brief Appendix B; PML).

Each row applies one physically or procedurally wrong change to a valid ml-artifact and states the least severe level
the validator must report natively at contract 2.8.0. Before the audit (0.9.0) 47 of 54 such artifacts passed with no
finding. FIX is the current valid fixture (contracts/fixtures/artifacts/valid/ml_artifact_v25.json), EX the J9
example's ml_artifact.json. Rows are numbered as in the source brief; where the brief's grouping left a row's mutation
open, the docstring of the mutation says what is probed. A row listed in BY_DESIGN may stay silent, with the reason.

The silent count is printed by test_report_silent_count (run with -v). Older artifacts (2.7.0) keep their default
outcome and get the same findings under --strict (test_legacy_*).
"""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import validate as v  # noqa: E402

FIX = json.loads((ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "ml_artifact_v25.json").read_text())
EX = json.loads((ROOT / "examples" / "ml-classifier-to-inference" / "output" / "artifacts" / "ml_artifact.json")
                .read_text())
RANK = {"warning": 1, "unresolved": 2, "error": 3}


def _set(path, value):
    def f(e):
        tgt = e
        for k in path[:-1]:
            tgt = tgt[k]
        tgt[path[-1]] = value
    return f


def _pop(path):
    def f(e):
        tgt = e
        for k in path[:-1]:
            tgt = tgt[k]
        tgt.pop(path[-1], None)
    return f


def _both(*fs):
    def f(e):
        for g in fs:
            g(e)
    return f


def _status(*labels):
    def f(doc):
        doc["status"] = list(labels)
    return f


def _dv(items):
    return _set(("downstream_validation",), items)


PASSED_COVERAGE = {"metric": "coverage", "quantity_affected": "mu 68% interval", "value": 0.40,
                   "criterion": ">= 0.68", "passed": True, "ref": "results.json#toys"}

# name -> (base, target "ext" or "doc", mutation, minimum level, work package)
ROWS = {
    "M01": ("FIX", "ext", _both(_set(("calibration", "fit_sample"), "./Val "), _set(("calibration", "validation", "sample"), "val")),
            "error", "0.1"),
    "M02": ("FIX", "ext", _set(("calibration", "sample_check"), {"fit_sha256": "1" * 64, "eval_sha256": "1" * 64}), "error", "0.1"),
    "M03": ("FIX", "ext", _set(("calibration", "sample_check"), {"disjoint": False}), "error", "0.1"),
    "M04": ("FIX", "ext", _set(("calibration", "fit_sample"), "train"), "error", "1.4"),
    "M05": ("FIX", "ext", _set(("calibration", "validation", "after"), "good"), "error", "1.4"),
    "M06": ("FIX", "ext", _set(("splits", "grouping_key"), "row"), "unresolved", "1.3"),
    "M07": ("FIX", "ext", _set(("splits", "overlap_check"), {"tool": "manual", "result": "pass"}), "unresolved", "1.3"),
    "M08": ("FIX", "ext", _dv([{"metric": "validated", "result": "pass"}]), "error", "1.1"),
    "M09": ("FIX", "ext", _dv(["ROC AUC = 0.93"]), "error", "1.1"),
    "M10": ("FIX", "ext", _dv(["weighted AUC", "accuracy"]), "error", "1.1"),
    "M11": ("FIX", "ext", _dv([{"metric": "accuracy", "quantity_affected": "classifier", "value": 0.91,
                                "criterion": ">= 0.9", "passed": True, "ref": "x"}]), "error", "1.1"),
    "M48": ("FIX", "ext", _dv([PASSED_COVERAGE]), "error", "1.1"),
    "M13": ("FIX", "ext", _both(_pop(("output_semantics",)), _pop(("calibration",))), "unresolved", "1.2"),
    "M15": ("FIX", "doc", _status("observed"), "error", "1.3"),
    "M47": ("EX", "doc", _status("unvalidated"), "error", "1.3"),
    "M18": ("FIX", "ext", _set(("training_domain", "x"), [-1e308, 1e308]), "unresolved", "1.3"),
    "M19": ("FIX", "ext", _pop(("training_domain", "y")), "unresolved", "1.3"),
    "M20": ("FIX", "ext", _set(("training_domain",), {}), "unresolved", "1.3"),
    "M21": ("FIX", "ext", _set(("weights", "used_in"), ["metrics"]), "error", "1.4"),
    "M22": ("FIX", "ext", _set(("weights", "training"), {"negative_weight_treatment": "abs", "class_balancing": "none"}),
            "error", "1.4"),
    "M23": ("FIX", "ext", _set(("weights", "used_in"), []), "error", "1.4"),
    "M24": ("FIX", "ext", _set(("weights",), "unweighted"), "error", "1.4"),
    "M25": ("FIX", "ext", _set(("domain_shift", "control_sample"), "training sample"), "unresolved", "0.6"),
    "M26": ("FIX", "ext", _set(("domain_shift", "outcome"), "uncorrected"), "unresolved", "0.6"),
    "M27": ("FIX", "ext", _pop(("domain_shift", "outcome")), "unresolved", "0.6"),
    "M49": ("FIX", "ext", _pop(("domain_shift", "status")), "unresolved", "0.6"),
    "M28": ("FIX", "ext", _set(("model_hash",), "sha256:placeholder"), "error", "1.3"),
    "M29": ("FIX", "ext", _set(("model_hash",), "TODO"), "error", "1.3"),
    "M30": ("FIX", "ext", _set(("model_hash",), "sha256:" + "a" * 63), "error", "1.3"),
    "M32": ("FIX", "ext", _both(_pop(("environment", "torch_version")), _pop(("environment", "framework"))), "warning", "1.3"),
    "M33": ("FIX", "ext", _both(_set(("environment", "precision"), "high"), _set(("environment", "device"), "my laptop")),
            "warning", "1.3"),
    "M35": ("FIX", "ext", _both(_set(("task",), "surrogate"), _set(("output_semantics",), "regression-value"),
                                _pop(("calibration",))), "error", "1.3"),
    "M36": ("FIX", "ext", _both(_set(("task",), "generation"), _set(("output_semantics",), "generated-sample"),
                                _pop(("calibration",))), "error", "1.3"),
    "M37": ("FIX", "ext", _both(_set(("task",), "inference"), _set(("output_semantics",), "density-ratio")), "error", "1.3"),
    "M38": ("FIX", "ext", _both(_set(("task",), "regression"), _set(("output_semantics",), "regression-value"),
                                _pop(("calibration",))), "error", "1.3"),
    "M39": ("FIX", "ext", _set(("task",), "regression"), "error", "1.3"),
    "M40": ("FIX", "ext", _set(("task",), "generation"), "error", "1.3"),
    "M41": ("FIX", "ext", _both(_set(("output_semantics",), "regression-value"), _pop(("calibration",))), "error", "1.3"),
    "M42": ("FIX", "ext", _set(("labels",), ["sig"]), "error", "1.3"),
    "M43": ("FIX", "ext", _set(("features",), ["x", "y", "x"]), "error", "1.3"),
    "M44": ("FIX", "ext", _set(("preprocessing",), [{"step": "standardize", "features": ["x", "y"], "fit_on": "test"}]),
            "error", "1.3"),
    "M45": ("FIX", "ext", _set(("preprocessing",), [{"step": "standardize", "features": ["x", "y"], "fit_on": "all"}]),
            "error", "1.3"),
    "M46": ("FIX", "ext", _set(("labels",), ["sig", "x"]), "error", "1.3"),
    "M50": ("EX", "ext", _set(("calibration", "validation", "after"), 0.2), "unresolved", "1.4"),
    "M51": ("EX", "ext", _set(("metrics", "test", "working_point", "threshold_from"), "test"), "error", "1.3"),
    "M52": ("EX", "ext", _set(("weights", "used_in"), ["loss", "metrics", "calibration", "templates", "calibration"]),
            "error", "1.4"),
    "M53": ("EX", "ext", _set(("units",), {"m_ll": "GeV", "acop": "rad", "pt_miss": "GeV", "cos_theta": "1", "mass": "GeV"}),
            "error", "1.3"),
    "M54": ("EX", "ext", _set(("splits", "test_groups_disjoint"), False), "error", "0.0"),
    "M55": ("FIX", "ext", lambda e: e.update(output_semantic=e.pop("output_semantics")), "error", "1.2"),
    "M56": ("FIX", "ext", lambda e: e.update(calibraton=e.pop("calibration")), "error", "1.2"),
    "M57": ("FIX", "ext", lambda e: e.update(domain_shfit=e.pop("domain_shift")), "error", "1.2"),
    "M59": ("FIX", "ext", _both(_set(("labels",), ["a", "b", "c"]), _set(("calibration", "validation", "metric"), "brier (a vs rest)")),
            "error", "1.3"),
    "M60": ("FIX", "ext", _both(_set(("task",), "inference"), _set(("output_semantics",), "density-ratio"),
                                _set(("sbi_validation",), {"coverage": {"method": "expected coverage", "result": 0.68},
                                                           "handoff": "hep-statistic"})), "error", "1.3"),
}
# Valid rows: the mutation is legitimate and must not be refused.
VALID_ROWS = {
    "M58": ("FIX", "ext", _both(_set(("task",), "inference"), _set(("output_semantics",), "density-ratio"),
                                _set(("parameters",), ["theta"]), _set(("training_domain",), {"x": [0.0, 1.0], "y": [-1.0, 1.0],
                                                                                              "theta": [0.0, 2.0]}),
                                _set(("sbi_validation",), {"coverage": {"method": "expected coverage (TARP)", "result": 0.68},
                                                           "handoff": "hep-statistics"})), "1.3"),
}
BY_DESIGN: dict = {}
DONE = {"0.0", "0.1", "0.6"}  # work packages whose rows are enforced; extended as each package lands


def apply(name, rows=ROWS):
    base, target, mutate = rows[name][:3]
    doc = copy.deepcopy(FIX if base == "FIX" else EX)
    mutate(doc if target == "doc" else doc["extension"])
    return doc


def worst(rep):
    return max((RANK[f.severity] for f in rep.findings if f.severity in RANK), default=0)


class MutationProbe(unittest.TestCase):
    def test_bases_are_clean(self):
        for name, doc in (("FIX", FIX), ("EX", EX)):
            with self.subTest(name):
                rep = v.validate_artifact(copy.deepcopy(doc))
                self.assertEqual([f for f in rep.findings if f.severity in ("error", "unresolved")], [], rep.as_dict())

    def test_rows_reach_their_level_natively(self):
        for name, row in ROWS.items():
            if row[4] not in DONE or name in BY_DESIGN:
                continue
            with self.subTest(name):
                rep = v.validate_artifact(apply(name))
                self.assertGreaterEqual(worst(rep), RANK[row[3]], (name, rep.as_dict()))

    def test_valid_rows_stay_valid(self):
        for name, row in VALID_ROWS.items():
            if row[3] not in DONE:
                continue
            with self.subTest(name):
                rep = v.validate_artifact(apply(name, VALID_ROWS))
                self.assertTrue(rep.ok, rep.as_dict())

    def test_legacy_artifacts_keep_their_outcome_and_strict_reports(self):
        for name, row in ROWS.items():
            if row[4] not in DONE or name in BY_DESIGN or row[4] == "0.0":
                continue
            with self.subTest(name):
                doc = apply(name)
                doc["contract_version"] = doc["versions"]["contracts"] = "2.7.0"
                base = copy.deepcopy(FIX if row[0] == "FIX" else EX)
                base["contract_version"] = base["versions"]["contracts"] = "2.7.0"
                self.assertGreaterEqual(worst(v.validate_artifact(doc, strict=True)), RANK["warning"], name)

    def test_report_silent_count(self):
        silent = sorted(name for name in ROWS if worst(v.validate_artifact(apply(name))) == 0)
        print(f"\nml-artifact mutation probe: {len(silent)} of {len(ROWS)} rows silent: {silent}")
        allowed = {n for n, r in ROWS.items() if r[4] not in DONE} | set(BY_DESIGN)
        self.assertLessEqual(set(silent), allowed)


if __name__ == "__main__":
    unittest.main()
