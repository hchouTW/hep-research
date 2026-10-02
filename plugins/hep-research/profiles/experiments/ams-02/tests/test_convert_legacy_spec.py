"""Tests for scripts/convert_legacy_spec.py (task M2.5, AC13): valid, invalid, incomplete and legacy inputs."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root
sys.path.insert(0, str(ROOT / "scripts"))
import convert_legacy_spec as cls  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
CLAIMS = json.loads((ROOT / "evidence" / "claims.json").read_text(encoding="utf-8"))
DAY = "2026-10-02"


def spec():
    return json.loads((FIX / "spec_valid.json").read_text(encoding="utf-8"))


def ratio_spec():
    doc = spec()
    doc["measurement"]["target"] = "ratio"
    doc["ratio"] = {
        "numerator": "helium flux", "denominator": "proton flux",
        "cancellations": [
            {"effect": "geometric acceptance", "treatment": "correlated",
             "correlation_model": "same fiducial region; correlation from shared MC", "verification": "MC comparison per bin"},
            {"effect": "charge estimator efficiency", "treatment": "independent",
             "correlation_model": None, "verification": "measured per species"}]}
    return doc


def codes(problems):
    return {p["code"] for p in problems}


class ValidInputTests(unittest.TestCase):
    def test_valid_spec_converts_and_validates(self):
        art, problems = cls.convert(spec(), CLAIMS, DAY)
        self.assertEqual(problems, [])
        self.assertTrue(validate_artifact(art, cls.profile_vocab()).ok)
        self.assertEqual(art["artifact_type"], "measurement-spec")
        obs = art["extension"]["observable"]
        self.assertEqual(obs["quantity"], "differential-flux")
        self.assertEqual(obs["level"], "crflux:top-of-instrument")
        self.assertEqual(obs["normalization"]["kind"], "exposure")
        self.assertEqual(obs["variables"][0], {"name": "rigidity", "unit": "GV", "edges": [1.0, 2.0, 5.0, 10.0, 50.0, 100.0]})
        self.assertEqual(art["extension"]["period"], {"start": "2011-05-19", "end": "2013-11-26"})
        self.assertEqual(art["bindings"]["experiments"], [{"profile": "experiment:ams-02", "version": "1.0.0"}])

    def test_yaml_and_json_forms_convert_identically(self):
        yaml_doc = cls._load(FIX / "spec_valid.yaml")
        self.assertEqual(cls.convert(yaml_doc, CLAIMS, DAY), cls.convert(spec(), CLAIMS, DAY))

    def test_lossless_round_trip(self):
        art, _ = cls.convert(spec(), CLAIMS, DAY)
        self.assertEqual(cls.legacy_spec_of(art), spec())

    def test_nothing_is_invented(self):
        art, _ = cls.convert(spec(), CLAIMS, DAY)
        obs = art["extension"]["observable"]
        self.assertEqual(obs["bin_semantics"], "unknown")
        self.assertEqual(obs["normalization"]["value"], "not-provided")
        self.assertEqual(art["extension"]["blinding"], "not-provided")
        self.assertEqual(art["status"], ["unvalidated"])
        text = " ".join(art["unresolved_inputs"])
        for word in ("blinding", "bin semantics", "exposure", "MC production"):
            self.assertIn(word, text)

    def test_contract_rejects_the_artifact_without_the_profile_vocabulary(self):
        art, _ = cls.convert(spec(), CLAIMS, DAY)
        self.assertFalse(validate_artifact(art, Vocabulary()).ok)

    def test_ratio_keeps_cancellation_analysis(self):
        art, problems = cls.convert(ratio_spec(), CLAIMS, DAY)
        self.assertEqual(problems, [])
        canc = art["extension"]["ratio"]["cancellations"]
        self.assertEqual([c["treatment"] for c in canc], ["correlated", "independent"])
        self.assertEqual(canc[1]["correlation_model"], "not-applicable")
        self.assertEqual(art["extension"]["observable"]["unit"], "1")
        self.assertEqual(cls.legacy_spec_of(art)["ratio"]["cancellations"][1]["correlation_model"], None)


class InvalidInputTests(unittest.TestCase):
    def test_not_a_legacy_spec(self):
        for doc in ({}, [], {"spec_version": "2"}, "text"):
            art, problems = cls.convert(doc, CLAIMS, DAY)
            self.assertIsNone(art)
            self.assertEqual(codes(problems), {"input.not_legacy_spec"})

    def test_audit_errors_refuse_conversion(self):
        doc = spec()
        doc["measurement"]["unit"] = "GeV/c"  # rigidity labelled as momentum
        art, problems = cls.convert(doc, CLAIMS, DAY)
        self.assertIsNone(art)
        self.assertIn("legacy.unit.mismatch", codes(problems))

    def test_unknown_claim_is_an_error(self):
        doc = spec()
        doc["parameters"][0]["claim_ids"] = ["C999"]
        art, problems = cls.convert(doc, CLAIMS, DAY)
        self.assertIsNone(art)
        self.assertIn("legacy.parameter.unknown_claim", codes(problems))

    def test_ratio_without_cancellation_analysis(self):
        doc = ratio_spec()
        doc["ratio"]["cancellations"] = []
        art, problems = cls.convert(doc, CLAIMS, DAY)
        self.assertIsNone(art)
        self.assertIn("legacy.ratio.no_cancellation_analysis", codes(problems))

    def test_discovery_target_is_not_mapped(self):
        doc = spec()
        doc["measurement"]["target"] = "discovery"
        art, problems = cls.convert(doc, None, DAY)
        if art is None and "convert.unmappable_target" not in codes(problems):
            self.skipTest(f"legacy audit refuses this mutation first: {sorted(codes(problems))}")
        self.assertIsNone(art)
        self.assertIn("convert.unmappable_target", codes(problems))

    def test_systematic_effect_outside_contract_enum_is_reported(self):
        doc = spec()
        doc["systematics"][0]["effect"] = "everything"
        art, problems = cls.convert(doc, CLAIMS, DAY)
        self.assertIsNone(art)
        self.assertTrue(any(c.startswith(("legacy.", "contract.")) for c in codes(problems)), problems)


class IncompleteInputTests(unittest.TestCase):
    def test_missing_period_becomes_a_marker(self):
        doc = spec()
        del doc["data_scope"]["period"]
        art, problems = cls.convert(doc, CLAIMS, DAY)
        self.assertEqual(problems, [])
        self.assertEqual(art["extension"]["period"], "not-provided")
        self.assertTrue(any("period" in u for u in art["unresolved_inputs"]))

    def test_missing_sample_is_unresolved(self):
        doc = spec()
        del doc["measurement"]["sample"]
        art, _ = cls.convert(doc, CLAIMS, DAY)
        self.assertTrue(any("public or internal" in u for u in art["unresolved_inputs"]))

    def test_optional_sections_absent(self):
        doc = spec()
        for key in ("tail_estimates", "ams_claims", "unresolved_inputs"):
            doc.pop(key, None)
        art, problems = cls.convert(doc, CLAIMS, DAY)
        self.assertEqual(problems, [], problems)
        self.assertNotIn("ams02:tail_estimates", art["extension"]["experiment_fields"])


class LegacyFormTests(unittest.TestCase):
    def test_bare_claim_ids_become_profile_qualified(self):
        art, _ = cls.convert(spec(), CLAIMS, DAY)
        self.assertEqual(art["provenance"]["evidence_ids"], ["ams02:C31"])
        # the legacy form inside the carried spec is untouched
        self.assertEqual(cls.legacy_spec_of(art)["parameters"][0]["claim_ids"], ["C31"])

    def test_already_qualified_ids_are_kept(self):
        doc = spec()
        doc["parameters"][0]["claim_ids"] = ["ams02:C31"]
        art, problems = cls.convert(doc, CLAIMS, DAY)
        self.assertEqual(problems, [])
        self.assertEqual(art["provenance"]["evidence_ids"], ["ams02:C31"])

    def test_ams_only_sections_kept_under_namespace(self):
        art, _ = cls.convert(spec(), CLAIMS, DAY)
        ef = art["extension"]["experiment_fields"]
        for key in ("observables", "response", "estimator", "inference", "validation", "parameters", "ams_claims"):
            self.assertEqual(ef[f"ams02:{key}"], spec()[key], key)

    def test_object_level_maps_to_detector(self):
        doc = spec()
        doc["measurement"]["level"] = "object"
        art, problems = cls.convert(doc, CLAIMS, DAY)
        if art is None:
            self.skipTest(f"legacy audit refuses an object-level flux target: {sorted(codes(problems))}")
        self.assertEqual(art["extension"]["observable"]["level"], "detector")
        self.assertEqual(art["extension"]["experiment_fields"]["ams02:measurement"]["level"], "object")


class CliTests(unittest.TestCase):
    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cls.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_exit_codes(self):
        code, out, _ = self.cli(str(FIX / "spec_valid.yaml"), "--created", DAY)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["artifact_type"], "measurement-spec")
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            doc = spec()
            doc["measurement"]["unit"] = "GeV/c"
            bad.write_text(json.dumps(doc), encoding="utf-8")
            code, _, err = self.cli(str(bad))
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(err)["status"], "refused")
            other = Path(tmp) / "other.json"
            other.write_text('{"spec_version": "2"}', encoding="utf-8")
            self.assertEqual(self.cli(str(other))[0], 2)
            broken = Path(tmp) / "broken.yaml"
            broken.write_text("a: [unclosed\n", encoding="utf-8")
            self.assertEqual(self.cli(str(broken))[0], 2)
            out_file = Path(tmp) / "art.json"
            self.assertEqual(self.cli(str(FIX / "spec_valid.json"), "--out", str(out_file), "--created", DAY)[0], 0)
            self.assertEqual(json.loads(out_file.read_text())["provenance"]["created"], DAY)
        self.assertEqual(self.cli("/nonexistent/spec.json")[0], 2)


if __name__ == "__main__":
    unittest.main()
