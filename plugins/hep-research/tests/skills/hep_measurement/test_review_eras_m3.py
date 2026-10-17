"""M3: multi-era design. A measurement-spec may declare eras (detector configuration, calibration, software or
operating changes) with `eras: [{id, start, end, kind, source}]`; review_measurement_spec.py then checks them:
era.bin_straddles_boundary (error: a period or time bin crosses an era boundary), era.correction_missing (warning: a
correction not determined per era nor declared shared), era.correlation_undeclared (warning: a systematic without its
correlation across eras) and era.version_mismatch (warning: eras processed with different versions without a declared
software or calibration change). Specs without eras get the same review as before. All specs are SYNTHETIC."""
import copy
import glob
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-measurement" / "scripts"))
from contracts.validate import validate_artifact  # noqa: E402
import review_measurement_spec as rms  # noqa: E402

SCRIPT = ROOT / "skills" / "hep-measurement" / "scripts" / "review_measurement_spec.py"
SPEC = ROOT / "skills" / "hep-measurement" / "assets" / "worked-spec.cosmic-ray.synthetic.json"


def two_era_spec():
    doc = json.loads(SPEC.read_text(encoding="utf-8"))
    ext = doc["extension"]
    effects = [c["effect_id"] for c in ext["corrections"]]
    ext["period"] = [{"start": "2026-01-01", "end": "2026-06-01"}, {"start": "2026-06-01", "end": "2027-01-01"}]
    ext["eras"] = [
        {"id": "era-1", "start": "2026-01-01", "end": "2026-06-01", "kind": "configuration",
         "source": "SYNTHETIC: run log", "corrections": list(effects), "versions": {"reconstruction": "v1"}},
        {"id": "era-2", "start": "2026-06-01", "end": "2027-01-01", "kind": "configuration",
         "source": "SYNTHETIC: run log, a layer added", "corrections": list(effects), "versions": {"reconstruction": "v1"}},
    ]
    for s in ext["systematics"]:
        s["era_correlation"] = "uncorrelated"
    return doc


def codes(review):
    return {d["code"] for d in review["defects"]} | {w["code"] for w in review["warnings"]}


class ErasField(unittest.TestCase):
    def test_spec_with_eras_validates_without_unknown_keys(self):
        rep = validate_artifact(two_era_spec())
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertFalse([f for f in rep.as_dict()["findings"] if "unknown_key" in f["code"]], rep.as_dict())

    def test_unknown_era_kind_and_missing_fields_are_refused(self):
        doc = two_era_spec()
        doc["extension"]["eras"][0]["kind"] = "vibes"
        self.assertFalse(validate_artifact(doc).ok)
        doc = two_era_spec()
        del doc["extension"]["eras"][1]["source"]
        self.assertFalse(validate_artifact(doc).ok)
        doc = two_era_spec()
        doc["extension"]["systematics"][0]["era_correlation"] = "sometimes"
        self.assertFalse(validate_artifact(doc).ok)


class EraRules(unittest.TestCase):
    def test_clean_two_era_spec_has_no_era_finding(self):
        review = rms.draft(two_era_spec())
        self.assertFalse({c for c in codes(review) if c.startswith("era.")}, review)
        self.assertEqual(review["verdict"], "acceptable-with-open-inputs")

    def test_period_straddling_a_boundary_is_an_error(self):
        doc = two_era_spec()
        doc["extension"]["period"] = [{"start": "2026-03-01", "end": "2026-09-01"}]
        review = rms.draft(doc)
        self.assertIn("era.bin_straddles_boundary", {d["code"] for d in review["defects"]})
        self.assertEqual(review["verdict"], "needs-work")

    def test_time_bin_straddling_a_boundary_is_an_error(self):
        doc = two_era_spec()
        ext = doc["extension"]
        for e, (a, b) in zip(ext["eras"], ((61000.0, 61160.0), (61160.0, 61400.0))):
            e["start"], e["end"] = a, b
        ext["period"] = [{"start": 61000.0, "end": 61400.0}]
        ext["observable"]["variables"].append({"name": "time", "unit": "MJD", "edges": [61000.0, 61100.0, 61200.0,
                                                                                         61400.0]})
        review = rms.draft(doc)
        hits = [d for d in review["defects"] if d["code"] == "era.bin_straddles_boundary"]
        self.assertTrue(hits, review)
        self.assertTrue(any("61100" in d["why"] and "61200" in d["why"] for d in hits), hits)

    def test_correction_missing_in_one_era(self):
        doc = two_era_spec()
        doc["extension"]["eras"][1]["corrections"] = doc["extension"]["eras"][1]["corrections"][1:]
        self.assertIn("era.correction_missing", {w["code"] for w in rms.draft(doc)["warnings"]})
        doc["extension"]["eras"][1]["shared_corrections"] = [doc["extension"]["corrections"][0]["effect_id"]]
        self.assertNotIn("era.correction_missing", {w["code"] for w in rms.draft(doc)["warnings"]})

    def test_correlation_undeclared(self):
        doc = two_era_spec()
        del doc["extension"]["systematics"][0]["era_correlation"]
        self.assertIn("era.correlation_undeclared", {w["code"] for w in rms.draft(doc)["warnings"]})

    def test_version_mismatch(self):
        doc = two_era_spec()
        doc["extension"]["eras"][1]["versions"] = {"reconstruction": "v2"}
        self.assertIn("era.version_mismatch", {w["code"] for w in rms.draft(doc)["warnings"]})
        doc["extension"]["eras"][1]["kind"] = "software"
        self.assertNotIn("era.version_mismatch", {w["code"] for w in rms.draft(doc)["warnings"]})

    def test_one_era_needs_no_cross_era_declarations(self):
        doc = two_era_spec()
        doc["extension"]["eras"] = doc["extension"]["eras"][:1]
        doc["extension"]["eras"][0]["end"] = "2027-01-01"
        for s in doc["extension"]["systematics"]:
            del s["era_correlation"]
        self.assertFalse({c for c in codes(rms.draft(doc)) if c.startswith("era.")})

    def test_cli_exit_code(self):
        doc = two_era_spec()
        doc["extension"]["period"] = [{"start": "2026-03-01", "end": "2026-09-01"}]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "spec.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            r = subprocess.run([sys.executable, "-B", str(SCRIPT), str(p)], capture_output=True, text=True, timeout=600)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(json.loads(r.stdout)["verdict"], "needs-work")


class ExistingSpecsUnchanged(unittest.TestCase):
    def test_reviews_of_specs_without_eras_do_not_change(self):
        paths = sorted(glob.glob(str(ROOT / "contracts/fixtures/artifacts/*/measurement_*.json")))
        paths += [str(p) for p in (ROOT / "skills/hep-measurement/assets").glob("*.json") if "spec" in p.name]
        self.assertGreater(len(paths), 10)
        for path in paths:
            doc = json.loads(Path(path).read_text(encoding="utf-8"))
            if doc.get("artifact_type") != "measurement-spec" or "eras" in doc.get("extension", {}):
                continue
            with self.subTest(spec=Path(path).name):
                with_rules = rms.draft(copy.deepcopy(doc))
                without = rms.draft(copy.deepcopy(doc), era_checks=False)
                self.assertEqual(with_rules, without)


class Documentation(unittest.TestCase):
    def test_analysis_design_section(self):
        text = (ROOT / "skills/hep-measurement/references/analysis-design.md").read_text(encoding="utf-8")
        self.assertIn("## Detector configuration changes (eras)", text)
        for code in ("era.bin_straddles_boundary", "era.correction_missing", "era.correlation_undeclared",
                     "era.version_mismatch"):
            self.assertIn(code, text)


if __name__ == "__main__":
    unittest.main()
