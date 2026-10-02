"""Contract, registry, project-config, vocabulary, evidence and conventions-gate tests (M1).

Covers T01, T02, T25, T26 and the AC06/AC07/AC13/AC31 parts that exist in M1.
All fixtures are synthetic structural stand-ins.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.compat.conventions import compare_conventions  # noqa: E402
from contracts.evidence import validate_ledger  # noqa: E402
from contracts.project import load_project, resolve_context  # noqa: E402
from contracts.registry import validate_registry  # noqa: E402
from contracts.semver import satisfies  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

FIX = ROOT / "contracts" / "fixtures"
ART = FIX / "artifacts"
REG = FIX / "registry"
PROJ = FIX / "projects"


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def codes(report):
    return {f.code for f in report.errors}


class ArtifactFixtureTests(unittest.TestCase):
    cases = load(ART / "cases.json")

    def test_every_valid_fixture_passes_without_findings(self):
        for name in self.cases["valid"]:
            with self.subTest(name=name):
                rep = validate_artifact(load(ART / "valid" / name))
                self.assertTrue(rep.ok, [f.as_dict() for f in rep.findings])

    def test_every_invalid_fixture_fails_with_expected_code(self):
        for name, expected in self.cases["invalid"].items():
            with self.subTest(name=name):
                rep = validate_artifact(load(ART / "invalid" / name))
                self.assertFalse(rep.ok)
                self.assertTrue(set(expected) <= codes(rep), (expected, codes(rep)))

    def test_each_extension_has_valid_and_invalid_fixture(self):
        types_valid = {load(ART / "valid" / n)["artifact_type"] for n in self.cases["valid"]}
        types_invalid = {load(ART / "invalid" / n).get("artifact_type") for n in self.cases["invalid"]}
        from contracts.validate import EXTENSION_SCHEMAS
        self.assertEqual(set(EXTENSION_SCHEMAS), types_valid)
        missing = set(EXTENSION_SCHEMAS) - types_invalid - {"comparison-spec", "communication"}
        self.assertEqual(missing, set(), "extensions without a negative fixture")

    def test_fixtures_are_labeled_synthetic(self):
        for p in ART.rglob("*.json"):
            if p.name == "cases.json":
                continue
            self.assertIn("SYNTHETIC", load(p)["objective"], p.name)


class DataKindStatusTests(unittest.TestCase):
    """AC22: synthetic, Asimov and observed stay distinct labels."""

    def test_observed_cannot_be_combined_with_synthetic_or_asimov(self):
        base = load(ART / "valid" / "dataset_record.json")
        for other in ("synthetic", "asimov"):
            with self.subTest(other=other):
                doc = copy.deepcopy(base)
                doc["status"] = ["observed", other]
                self.assertIn("status.conflict", codes(validate_artifact(doc)))

    def test_synthetic_and_asimov_labels_validate_alone(self):
        base = load(ART / "valid" / "dataset_record.json")
        for st in (["synthetic"], ["asimov", "synthetic"]):
            with self.subTest(status=st):
                doc = copy.deepcopy(base)
                doc["status"] = st
                self.assertNotIn("status.conflict", codes(validate_artifact(doc)))


class NonColliderNormalizationTests(unittest.TestCase):
    """T26: exposure, protons-on-target, target-exposure validate with no luminosity field."""

    def test_non_collider_kinds_validate_without_luminosity(self):
        for name in ("measurement_exposure.json", "measurement_protons_on_target.json", "measurement_target_exposure.json"):
            with self.subTest(name=name):
                doc = load(ART / "valid" / name)
                self.assertNotIn("luminosity", json.dumps(doc).replace("integrated-luminosity", ""))
                self.assertTrue(validate_artifact(doc).ok)

    def test_core_vocabulary_has_no_collider_only_default(self):
        v = Vocabulary()
        self.assertTrue({"exposure", "protons-on-target", "target-exposure", "live-time", "shape-only"} <= v.core("normalization_kinds"))


class VocabularyExtensionTests(unittest.TestCase):
    def test_namespaced_level_valid_only_with_profile_extension(self):
        doc = load(ART / "valid" / "measurement_exposure.json")
        doc["extension"]["observable"]["level"] = "fxa:instrument"
        self.assertIn("vocab.unknown_term", codes(validate_artifact(doc)))
        _, loaded = validate_registry(REG / "valid" / "profiles" / "registry.json")
        vocab = Vocabulary.with_profiles(loaded.values())
        self.assertTrue(validate_artifact(doc, vocab).ok)

    def test_extension_requires_own_namespace(self):
        problems = Vocabulary().extend("levels", ["instrument", "other:x", "mine:y"], ["mine"])
        self.assertEqual(len(problems), 2)

    def test_conventions_alias(self):
        v = Vocabulary()
        self.assertEqual(v.extend("conventions", ["ams02:energy_variable"], "ams02"), [])
        self.assertTrue(v.has("convention_keys", "ams02:energy_variable"))


class RegistryTests(unittest.TestCase):
    """T01/T02 and AC06: each negative package fails with a precise, named error."""
    cases = load(REG / "cases.json")

    def test_registry_packages(self):
        for name, expected in self.cases.items():
            with self.subTest(name=name):
                rep, _ = validate_registry(REG / name / "profiles" / "registry.json")
                if not expected:
                    self.assertTrue(rep.ok, [f.as_dict() for f in rep.findings])
                else:
                    self.assertTrue(set(expected) <= codes(rep), (expected, codes(rep)))

    def test_errors_name_the_offender(self):
        rep, _ = validate_registry(REG / "cycle" / "profiles" / "registry.json")
        msg = " ".join(f.message for f in rep.errors)
        self.assertIn("theory:fixture-th-a", msg)
        self.assertIn("theory:fixture-th-b", msg)
        rep, _ = validate_registry(REG / "escaping_path" / "profiles" / "registry.json")
        self.assertTrue(any("outside.md" in f.message for f in rep.errors))

    def test_deterministic(self):
        a, _ = validate_registry(REG / "template_violation" / "profiles" / "registry.json")
        b, _ = validate_registry(REG / "template_violation" / "profiles" / "registry.json")
        self.assertEqual(a.as_dict(), b.as_dict())

    def test_shipped_registry_valid_and_within_budget(self):
        rep, _ = validate_registry()
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.findings])
        self.assertLessEqual((ROOT / "profiles" / "registry.json").stat().st_size, 2048)

    def test_symlink_escape_detected(self):
        with tempfile.TemporaryDirectory() as td:
            pkg = Path(td) / "pkg"
            shutil.copytree(REG / "valid", pkg)
            outside = Path(td) / "secret"
            outside.mkdir()
            (pkg / "profiles" / "experiments" / "a" / "modules" / "link").symlink_to(outside)
            rep, _ = validate_registry(pkg / "profiles" / "registry.json")
            self.assertIn("profile.path_escapes", codes(rep))


class ProjectConfigTests(unittest.TestCase):
    """AC07: 0/1/many experiments x 0/1/many theory contexts, a local profile, conflict diagnostics."""
    meta = load(PROJ / "cases.json")
    registry = (PROJ / meta["registry"]).resolve()

    def _load(self, name, td):
        dst = Path(td) / name
        shutil.copytree(PROJ / name, dst)
        return load_project(dst, self.registry)

    def test_cases(self):
        with tempfile.TemporaryDirectory() as td:
            for name, exp in self.meta["cases"].items():
                with self.subTest(name=name):
                    p = self._load(name, td)
                    self.assertTrue(set(exp["errors"]) <= codes(p.report), (exp, codes(p.report)))
                    if not exp["errors"]:
                        self.assertTrue(p.report.ok, [f.as_dict() for f in p.report.findings])
                        self.assertEqual(len(p.profiles), exp["profiles"])

    def test_matrix_is_complete(self):
        names = set(self.meta["cases"])
        for e in ("0", "1", "many"):
            for t in ("0", "1", "many"):
                self.assertIn(f"exp{e}_th{t}", names)
        self.assertIn("local_profile", names)

    def test_local_profile_inside_plugin_rejected(self):
        p = load_project(PROJ / "local_profile", self.registry)
        self.assertIn("project.local_in_plugin", codes(p.report))
        self.assertIn("project.writes_into_plugin", codes(p.report))

    def test_resolution_order(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._load("exp1_th0", td)
            r = resolve_context({"theory": ["theory:fixture-th-a"]}, p, needs_profile=True)
            self.assertEqual((r["decision"], r["source"]), ("use", "request"))
            r = resolve_context({}, p, needs_profile=True)
            self.assertEqual((r["source"], r["experiments"]), ("project-config", ["experiment:fixture-exp-a"]))
            empty = self._load("exp0_th0", td)
            self.assertEqual(resolve_context({}, empty, needs_profile=True)["decision"], "ask")
            self.assertEqual(resolve_context({}, None, needs_profile=False)["decision"], "none")


class ConventionsGateTests(unittest.TestCase):
    """T25: unknown or namespaced convention keys are not comparable unless mapped."""

    def test_equal_core_conventions_comparable(self):
        r = compare_conventions({"energy_variable": "sqrt_s"}, {"energy_variable": "sqrt_s"})
        self.assertTrue(r["comparable"])

    def test_namespaced_key_on_one_side_blocks(self):
        r = compare_conventions({"ams02:energy_variable": "rigidity"}, {"energy_variable": "rigidity"})
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "ams02:energy_variable")

    def test_unknown_key_blocks_until_mapped(self):
        a, b = {"my_scheme": "x"}, {}
        self.assertFalse(compare_conventions(a, b)["comparable"])
        m = [{"key": "my_scheme", "action": "irrelevant", "justification": "fixture: does not enter this observable"}]
        r = compare_conventions(a, b, m)
        self.assertTrue(r["comparable"])
        self.assertEqual(r["mappings_applied"], m)

    def test_mapping_without_justification_ignored(self):
        r = compare_conventions({"x:k": 1}, {"x:k": 2}, [{"key": "x:k", "action": "equivalent"}])
        self.assertFalse(r["comparable"])

    def test_differing_values_block(self):
        r = compare_conventions({"metric_signature": "+---"}, {"metric_signature": "-+++"})
        self.assertFalse(r["comparable"])

    def test_core_key_one_side_is_note_not_block(self):
        r = compare_conventions({"metric_signature": "+---"}, {})
        self.assertTrue(r["comparable"])
        self.assertEqual(len(r["notes"]), 1)


class EvidenceSchemaTests(unittest.TestCase):
    def _src(self, sid="fx:S01", level="full-text"):
        return {"id": sid, "title": "synthetic", "authors": "fixture", "tier": 1, "verification_level": level,
                "verification_date": "2026-10-01", "formal_status": "published", "supersedes": [], "superseded_by": []}

    def _claim(self, cid="fx:C01", strength="full-text", sources=("fx:S01",)):
        return {"id": cid, "claim": "synthetic", "evidence_status": "public-fact", "source_ids": list(sources), "location": "p1",
                "scope": {"text": "fixture"}, "verification_strength": strength, "numeric_quotation_allowed": False,
                "last_reviewed": "2026-10-01"}

    def test_valid_ledger(self):
        self.assertTrue(validate_ledger([self._src()], [self._claim()], "fx").ok)

    def test_namespace_enforced(self):
        rep = validate_ledger([self._src("S01")], [], "fx")
        self.assertFalse(rep.ok)
        rep = validate_ledger([self._src("other:S01")], [], "fx")
        self.assertIn("evidence.namespace", codes(rep))

    def test_over_strong_claim(self):
        rep = validate_ledger([self._src(level="metadata-only")], [self._claim()], "fx")
        self.assertIn("evidence.over_strong", codes(rep))

    def test_same_local_id_two_namespaces_distinct(self):
        self.assertTrue(validate_ledger([self._src("fx:S01")], [], "fx").ok)
        self.assertTrue(validate_ledger([self._src("fy:S01")], [], "fy").ok)

    def test_three_dates_are_separate_fields(self):
        """Section 12: publication date, data-taking period and verification date are distinct fields."""
        props = load(ROOT / "contracts" / "schemas" / "evidence_source.json")["properties"]
        for key in ("publication_date", "data_taking_period", "verification_date"):
            self.assertIn(key, props)
        self.assertIn("verification_date", load(ROOT / "contracts" / "schemas" / "evidence_source.json")["required"])

    def test_unknown_verification_date_allowed_but_not_zero(self):
        s = self._src()
        s["verification_date"] = "unknown"
        self.assertTrue(validate_ledger([s], [], "fx").ok)
        s["verification_date"] = 0
        self.assertFalse(validate_ledger([s], [], "fx").ok)


class SemverTests(unittest.TestCase):
    def test_ranges(self):
        self.assertTrue(satisfies("1.0.0", ">=1.0,<2.0"))
        self.assertFalse(satisfies("2.0.0", ">=1.0,<2.0"))
        self.assertTrue(satisfies("0.1.0", ">=0.1,<1.0"))


class TheoryIndependenceTests(unittest.TestCase):
    """7.17 item 5: theory artifacts validate with all experiment fields absent."""

    def test_theory_spec_has_no_experiment_fields(self):
        doc = load(ART / "valid" / "theory_spec.json")
        self.assertTrue(validate_artifact(doc).ok)
        text = json.dumps(doc["extension"])
        for word in ("blinding", "selections", "detector", "luminosity", "response"):
            self.assertNotIn(word, text)

    def test_dataset_record_without_detector_modules(self):
        """7.17 item 6: a published-shape dataset record needs no detector fields."""
        doc = load(ART / "valid" / "dataset_record.json")
        self.assertTrue(validate_artifact(doc).ok)
        self.assertNotIn("response", doc["extension"])
        pub = copy.deepcopy(doc)
        pub["extension"].update(status="published", source_evidence_ids=["fxa:S01"], dataset_id="fxa:hepdata-shaped-1")
        pub["status"] = ["unvalidated"]
        self.assertTrue(validate_artifact(pub).ok)


    def test_metadata_only_record_with_unknown_bin_semantics(self):
        """M2: a record read at abstract level may not know its bin semantics; it validates
        with an unresolved finding instead of forcing an invented term."""
        doc = load(ART / "valid" / "dataset_record.json")
        doc["extension"]["observable"]["bin_semantics"] = "unknown"
        doc["extension"].pop("data", None)
        rep = validate_artifact(doc)
        self.assertTrue(rep.ok, [f.message for f in rep.errors])
        self.assertIn("observable.bin_semantics_missing", {f.code for f in rep.findings if f.severity == "unresolved"})
        doc["extension"]["observable"]["bin_semantics"] = "bin-ish"
        self.assertIn("schema.any_of", codes(validate_artifact(doc)))


if __name__ == "__main__":
    unittest.main()
