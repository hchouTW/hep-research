"""D13 (gates G3, G4): the profile kind `reference` and the sourced detector atlas profile.

- the evidence ledger accepts an extra `atlas` block on a claim (the work order's "Inferred" note, tested first);
- profile.json and registry.json accept kind `reference` with an id `reference:<name>`; the reference template
  requires profile.json, index.md, conventions.json, evidence and tests;
- the plugin registry, with the atlas, validates and stays within its 3,072-byte budget;
- a user atlas packaged as a project-local reference profile has custody `unknown` (contracts/custody.py).
Standard library only."""
import json
import shutil
from datetime import date
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.registry import REGISTRY_BUDGET, TEMPLATES, check_profile_dir, load_registry  # noqa: E402
from contracts.schema import Report, validate  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.evidence.ledger import check_ledger  # noqa: E402

ATLAS = ROOT / "profiles" / "reference" / "detector-atlas"
SOURCE = {"id": "x:S01", "title": "SYNTHETIC detector paper", "authors": "nobody", "year": 2026, "tier": 1,
          "verification_level": "full-text", "verification_date": "2026-10-17", "supersedes": [], "superseded_by": []}
CLAIM = {"id": "x:C01", "claim": "SYNTHETIC: the field is 1 T", "claim_types": ["performance_number"],
         "support_kind": "primary", "source_ids": ["x:S01"], "location": "section 1",
         "scope": {"text": "synthetic", "species": [], "range": None, "data_period": None, "analysis": None},
         "limitations": None, "verification_strength": "full-text", "numeric_quotation_allowed": True,
         "last_reviewed": "2026-10-17", "evidence_status": "public-fact",
         "atlas": {"experiment": "SYNTHETIC", "subsystem": "magnet", "quantity": "field", "value": "1",
                   "unit": "T", "kind": "design", "valid_for": "as built", "conditions": None}}


class LedgerAcceptsAtlasBlock(unittest.TestCase):
    def test_extra_atlas_field_is_not_an_error(self):
        res = check_ledger([SOURCE], [CLAIM], date(2026, 10, 17), 365)
        errors = res["errors"]
        self.assertEqual(errors, [], errors)


class ReferenceKind(unittest.TestCase):
    def test_schema_accepts_reference_profiles(self):
        prof = json.loads((ATLAS / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual((prof["id"], prof["kind"]), ("reference:detector-atlas", "reference"))
        rep = validate(prof, "profile.json", Vocabulary())
        self.assertEqual([f for f in rep.findings if f.severity == "error"], [])

    def test_template(self):
        self.assertEqual(set(TEMPLATES["reference"]["required"]),
                         {"profile.json", "index.md", "conventions.json", "evidence", "tests"})
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "detector-atlas"
            shutil.copytree(ATLAS, copy)
            shutil.rmtree(copy / "evidence")
            rep = Report()
            check_profile_dir(copy, Path(d), rep, "local")
            self.assertIn("profile.template_violation", {f.code for f in rep.findings})

    def test_plugin_registry_with_the_atlas(self):
        reg = load_registry()
        errors = [f for f in reg.report.findings if f.severity == "error"]
        self.assertEqual(errors, [], [f.message for f in errors])
        self.assertIn("reference:detector-atlas", reg.every_profile)
        self.assertLessEqual((ROOT / "profiles" / "registry.json").stat().st_size, REGISTRY_BUDGET)


class Custody(unittest.TestCase):
    def test_user_atlas_as_local_profile_is_custody_unknown(self):
        from contracts.custody import inventory
        with tempfile.TemporaryDirectory() as d:
            proj = Path(d) / "project"
            local = proj / "local-atlas"
            shutil.copytree(ATLAS, local)
            pj = json.loads((local / "profile.json").read_text(encoding="utf-8"))
            pj["id"], pj["evidence_namespace"] = "reference:my-atlas", "my-atlas"
            (local / "profile.json").write_text(json.dumps(pj), encoding="utf-8")
            for name in ("sources.json", "claims.json"):
                p = local / "evidence" / name
                p.write_text(p.read_text(encoding="utf-8").replace('"detector-atlas:', '"my-atlas:'), encoding="utf-8")
            (proj / "hep-research.project.json").write_text(json.dumps(
                {"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0", "experiments": [], "theory": [],
                 "local_profile_paths": ["local-atlas"]}), encoding="utf-8")
            rows = {r["profile"]: r for r in inventory(proj)["profiles"]}
        self.assertEqual(rows["reference:my-atlas"]["custody"], "unknown")
        self.assertEqual(rows["reference:detector-atlas"]["custody"], "public")


if __name__ == "__main__":
    unittest.main()
