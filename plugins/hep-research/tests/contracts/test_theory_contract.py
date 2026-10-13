"""theory-spec and prediction semantics (hep-theory audit 2026-10-13, THY-WP2 and WP4.3).

The audit found that contracts/validate.py checked only experiment fields, auto-Gaussian uncertainties and the payload
of a theory-spec or prediction: none of the hep-theory invariants (conventions block, order of a perturbative
argument, limit of an asymptotic one, checks behind a strong status, a validity domain, a linked theory spec, an
envelope prescription, a truncation method) was checked. Contracts 2.6.0 add optional fields for them; the rules are
native from 2.6.0, and an older artifact keeps its outcome unless --strict. All fixtures SYNTHETIC."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import validate as v  # noqa: E402

ART = ROOT / "contracts" / "fixtures" / "artifacts"
THEORY_1_0 = json.loads((ART / "valid" / "theory_spec.json").read_text())
PREDICTION_1_0 = json.loads((ART / "valid" / "prediction.json").read_text())


def codes(rep, level="error"):
    return {f.code for f in rep.findings if f.severity == level}


class SchemaFieldTests(unittest.TestCase):
    """THY-WP2.1: optional fields only; their types are checked, their absence is not."""

    def test_new_theory_spec_fields_are_accepted(self):
        doc = copy.deepcopy(THEORY_1_0)
        doc["extension"].update(limit="m_e / sqrt(s) -> 0", neglected=["Z exchange"], computational_run_ref="run.json",
                                degenerate_directions=["D0/L"])
        doc["extension"]["model"]["family"] = "synthetic-family"
        doc["extension"]["checks_run"] = [{"name": "units", "result": "pass", "tolerance": 1e-12},
                                          {"name": "limit", "result": "pass", "tolerance": "exact"}]
        doc["extension"]["references_read"] = [{"citation": "synthetic", "location": "eq. 1", "date_read": "2026-10-13"}]
        rep = v.validate_artifact(doc)
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertFalse(codes(rep))

    def test_new_field_types_are_checked(self):
        for field, value in (("limit", 3), ("neglected", "Z exchange"), ("computational_run_ref", {}),
                             ("degenerate_directions", "D0/L")):
            with self.subTest(field=field):
                doc = copy.deepcopy(THEORY_1_0)
                doc["extension"][field] = value
                self.assertIn("schema.type", codes(v.validate_artifact(doc)))
        doc = copy.deepcopy(THEORY_1_0)
        doc["extension"]["checks_run"] = [{"name": "units", "result": "pass", "tolerance": [1]}]
        self.assertFalse(v.validate_artifact(doc).ok)

    def test_new_prediction_and_uncertainty_fields(self):
        doc = copy.deepcopy(PREDICTION_1_0)
        doc["extension"]["derivation_status"] = "perturbative-argument"
        doc["extension"]["uncertainties"][0].update(prescription="7-point", values=[0.9, 1.1])
        doc["extension"]["uncertainties"].append({"name": "mho", "kind": "truncation", "correlation": "unknown",
                                                  "method": "last-term"})
        rep = v.validate_artifact(doc)
        self.assertTrue(rep.ok, rep.as_dict())
        doc["extension"]["derivation_status"] = "proved"
        self.assertIn("vocab.unknown_term", codes(v.validate_artifact(doc)))


if __name__ == "__main__":
    unittest.main()
