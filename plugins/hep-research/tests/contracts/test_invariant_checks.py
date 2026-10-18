"""Validator checks behind three SKILL.md invariants (registry evals/behavior/invariants.json):
STAT-02, a frequentist limit names its construction (warning stats.construction_missing); ML-05, weights that enter
the loss record training and evaluation weights separately (warning ml.weights_not_separated); THEO-05, a source
read for a theory spec is cited with its exact location (schema). Synthetic fixtures."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.validate import validate_artifact  # noqa: E402

VALID = ROOT / "contracts" / "fixtures" / "artifacts" / "valid"


def load(name: str) -> dict:
    return json.loads((VALID / name).read_text(encoding="utf-8"))


def codes(doc: dict, severity: str) -> set[str]:
    return {f.code for f in validate_artifact(doc).findings if f.severity == severity}


class ConstructionNamed(unittest.TestCase):
    def test_limit_without_construction_warns(self):
        doc = load("statres_v26.json")
        self.assertNotIn("stats.construction_missing", codes(doc, "warning"))
        del doc["extension"]["construction"]
        self.assertIn("stats.construction_missing", codes(doc, "warning"))
        self.assertNotIn("stats.construction_missing", codes(doc, "error"), "a warning, not an error")

    def test_result_without_a_limit_does_not_warn(self):
        doc = load("statres_frequentist.json")
        doc["extension"].pop("construction", None)
        self.assertNotIn("stats.construction_missing", codes(doc, "warning"))


class WeightsSeparated(unittest.TestCase):
    def test_loss_weights_without_both_blocks_warn(self):
        doc = load("ml_artifact_v25.json")
        self.assertNotIn("ml.weights_not_separated", codes(doc, "warning"))
        for block in ("training", "evaluation"):
            d = copy.deepcopy(doc)
            del d["extension"]["weights"][block]
            self.assertIn("ml.weights_not_separated", codes(d, "warning"), block)

    def test_weights_only_in_metrics_do_not_warn(self):
        doc = load("ml_artifact_v25.json")
        w = doc["extension"]["weights"]
        w["used_in"] = ["metrics"]
        w.pop("training")
        w.pop("class_balancing", None)
        self.assertNotIn("ml.weights_not_separated", codes(doc, "warning"))


class SourcesLocated(unittest.TestCase):
    def test_a_reference_without_its_location_is_an_error(self):
        doc = load("theory_spec_v26.json")
        doc["extension"]["references_read"] = [{"citation": "synthetic", "location": "eq. 1", "date_read": "2026-10-13"}]
        self.assertTrue(validate_artifact(doc).ok)
        del doc["extension"]["references_read"][0]["location"]
        self.assertFalse(validate_artifact(doc).ok)


if __name__ == "__main__":
    unittest.main()
