"""Project-level resolution of communication records (hep-authoring plan T1, second increment):
contracts/communication_project.py composes the dependency checker, the evidence ledgers and the declared documents
without network access, and normalizes outcomes for the communication CLIs. All records are SYNTHETIC fixtures."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.dependencies import validate_dependencies  # noqa: E402
from contracts.schema import Report  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

try:
    from contracts.communication_project import (findings_of, normalize_dependency_report, output_aliases_input,
                                                 resolve_context, resolve_outcome)
except ImportError:  # the tests below must fail, not error at import, before the module exists
    resolve_context = normalize_dependency_report = resolve_outcome = output_aliases_input = findings_of = None

ART = ROOT / "contracts" / "fixtures" / "artifacts"
RICH = json.loads((ART / "valid" / "communication_traceability.json").read_text(encoding="utf-8"))
LEGACY = json.loads((ART / "valid" / "communication.json").read_text(encoding="utf-8"))
STATRES = json.loads((ART / "valid" / "statres_frequentist.json").read_text(encoding="utf-8"))
PRED = json.loads((ART / "valid" / "prediction.json").read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p: Path, obj) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1) if not isinstance(obj, str) else obj, encoding="utf-8")
    return p


SOURCE = {"id": "lit:S01", "title": "Synthetic fixture paper", "authors": "Fixture et al.", "year": 2026, "tier": 2,
          "verification_level": "abstract+metadata", "verification_date": "2026-10-12", "supersedes": [], "superseded_by": [],
          "verification_limitations": "fixture"}
CLAIM = {"id": "lit:C01", "claim": "fixture claim", "claim_types": ["published_result"], "source_ids": ["lit:S01"],
         "location": "abstract", "scope": {"text": "fixture"}, "verification_strength": "abstract+metadata",
         "numeric_quotation_allowed": True, "last_reviewed": "2026-10-12"}


class ProjectFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        obs = copy.deepcopy(STATRES)
        obs["artifact_id"], obs["status"] = "fixture-synthetic-obs", ["observed"]
        self.obs = write(self.root / "artifacts" / "obs.json", obs)
        syn = copy.deepcopy(PRED)
        syn["artifact_id"] = "fixture-synthetic-syn"
        self.syn = write(self.root / "artifacts" / "syn.json", syn)
        write(self.root / "evidence" / "lit" / "sources.json", [SOURCE])
        write(self.root / "evidence" / "lit" / "claims.json", [CLAIM])
        write(self.root / "paper" / "main.md", "# Fixture\n\nThe ratio is 1.02 +/- 0.05.\n")
        self.doc = copy.deepcopy(RICH)
        self.doc["inputs"][0]["sha256"], self.doc["inputs"][1]["sha256"] = sha(self.obs), sha(self.syn)
        self.doc["inputs"][0]["version"], self.doc["inputs"][1]["version"] = obs["contract_version"], syn["contract_version"]
        for c in self.doc["extension"]["claims"]:
            for e in c["evidence"]:
                c["assessment"]["evidence_fingerprints"][e["id"]] = "sha256:" + self.doc["inputs"][0 if e["target"].endswith("obs.json") else 1]["sha256"]
        ext = self.doc["extension"]
        ext["scope"]["sources"] = True
        ext["evidence_ledgers"] = [{"namespace": "lit", "sources_ref": "evidence/lit/sources.json", "claims_ref": "evidence/lit/claims.json",
                                    "sources_sha256": sha(self.root / "evidence/lit/sources.json"),
                                    "claims_sha256": sha(self.root / "evidence/lit/claims.json")}]
        ext["sources_read"] = [{"id": "lit:S01", "level": "abstract+metadata", "verification_date": "2026-10-12", "locators": ["abstract"]}]
        ext["claims"][0]["evidence"].append({"id": "ev:C1-s", "target_kind": "source", "target": "lit:S01", "locator": "abstract, sentence 2",
                                             "role": "qualifies", "usage": "used-in-claim", "version": "2026-10-12"})
        ext["claims"][0]["assessment"]["evidence_fingerprints"]["ev:C1-s"] = "version:2026-10-12"
        ext["claims"][0]["assessment"]["evidence_ids"].append("ev:C1-s")
        self.path = self.save()

    def save(self):
        return write(self.root / "artifacts" / "comm.json", self.doc)

    def tearDown(self):
        self.tmp.cleanup()

    def ctx(self, path=None):
        self.assertIsNotNone(resolve_context, "contracts.communication_project does not exist")
        return resolve_context(path or self.path, self.root)

    @staticmethod
    def codes(ctx, severity=None):
        return {f["code"] for f in ctx["findings"] if severity is None or f["severity"] == severity}

    @staticmethod
    def dep_codes(ctx):
        return {f["code"] for f in ctx["dependencies"]["findings"]}


class ResolveContextTests(ProjectFixture):
    def test_valid_chain_resolves_everything(self):
        self.assertTrue(validate_artifact(self.doc).ok, [f.as_dict() for f in validate_artifact(self.doc).errors])
        ctx = self.ctx()
        self.assertEqual(ctx["format"], "traceability")
        self.assertEqual(ctx["traceability"], "declared")
        self.assertEqual(ctx["findings"], [])
        self.assertTrue(ctx["schema"]["ok"])
        self.assertEqual(ctx["dependencies"]["status"], "ok")
        self.assertTrue(all(i["resolved"] and i["match"] for i in ctx["inputs"].values()), ctx["inputs"])
        self.assertEqual(ctx["inputs"]["artifacts/obs.json"]["status"], ["observed"])
        self.assertTrue(ctx["ledgers"]["lit"]["loaded"])
        self.assertEqual(ctx["ledgers"]["lit"]["sha256_checked"], True)
        self.assertEqual(ctx["ledgers"]["lit"]["report"]["status"], "pass", ctx["ledgers"]["lit"]["report"])
        self.assertTrue(ctx["sources"]["lit:S01"]["resolved"])
        self.assertEqual(ctx["sources"]["lit:S01"]["record"]["title"], "Synthetic fixture paper")
        self.assertTrue(ctx["documents"]["doc:paper"]["resolved"])
        self.assertEqual(ctx["documents"]["doc:paper"]["sha256"], sha(self.root / "paper/main.md"))
        self.assertEqual(ctx["artifact_sha256"], sha(self.path))
        self.assertIn("dependencies", ctx["checks_run"])
        self.assertIn("ledgers", ctx["checks_run"])

    def test_legacy_record_has_limited_traceability(self):
        legacy = copy.deepcopy(LEGACY)
        legacy["extension"]["claims"][0]["result_ref"] = "artifacts/obs.json"
        p = write(self.root / "artifacts" / "legacy.json", legacy)
        ctx = self.ctx(p)
        self.assertEqual(ctx["format"], "legacy")
        self.assertEqual(ctx["traceability"], "limited")
        self.assertIn("resolution.limited_traceability", self.codes(ctx, "unresolved"))
        self.assertIn("ledgers", [c["check"] for c in ctx["checks_not_run"]])

    def test_missing_input_is_a_dependency_error(self):
        self.syn.unlink()
        ctx = self.ctx()
        self.assertIn("dependency.missing", self.dep_codes(ctx))
        self.assertFalse(ctx["inputs"]["artifacts/syn.json"]["resolved"])
        self.assertEqual(ctx["dependencies"]["status"], "error")

    def test_changed_input_detected_and_exposed(self):
        changed = json.loads(self.obs.read_text())
        changed["objective"] = "SYNTHETIC: same file name, different content"
        write(self.obs, changed)
        ctx = self.ctx()
        self.assertIn("dependency.hash_mismatch", self.dep_codes(ctx))
        inp = ctx["inputs"]["artifacts/obs.json"]
        self.assertTrue(inp["resolved"])
        self.assertFalse(inp["match"])
        self.assertEqual(inp["sha256"], sha(self.obs))
        self.assertNotEqual(inp["sha256"], inp["declared_sha256"])

    def test_cycle_detected(self):
        obs = json.loads(self.obs.read_text())
        obs["inputs"] = [{"ref": "artifacts/comm.json", "status": ["synthetic", "unvalidated"]}]
        obs["status"] = ["observed"]  # deliberately wrong: a cycle through a synthetic consumer
        write(self.obs, obs)
        self.doc["inputs"][0]["sha256"] = sha(self.obs)
        self.save()
        self.assertIn("dependency.cycle", self.dep_codes(self.ctx()))

    def test_out_of_root_references_are_not_opened(self):
        outside = Path(self.tmp.name) / "secret-sources.json"
        write(outside, [SOURCE])
        doc_outside = Path(self.tmp.name) / "secret.md"
        doc_outside.write_text("secret\n")
        (self.root / "paper" / "link.md").symlink_to(doc_outside)
        ext = self.doc["extension"]
        ext["evidence_ledgers"][0]["sources_ref"] = "../secret-sources.json"
        ext["documents"][0]["path"] = "paper/link.md"
        self.save()
        opened, watching = [], []
        sys.addaudithook(lambda ev, args: opened.append(str(args[0])) if watching and ev == "open" and isinstance(args[0], (str, Path)) else None)
        watching.append(1)
        try:
            ctx = self.ctx()
        finally:
            watching.clear()
        self.assertIn("resolution.outside_root", self.codes(ctx, "error"))
        self.assertFalse(ctx["ledgers"]["lit"]["loaded"])
        self.assertFalse(ctx["documents"]["doc:paper"]["resolved"])
        self.assertNotIn(str(outside), opened)
        self.assertNotIn(str(doc_outside), opened)
        self.assertNotIn(str(doc_outside.resolve()), opened)
        self.assertTrue(any(p.endswith("comm.json") for p in opened), "the artifact itself was read")

    def test_unknown_source_and_unavailable_ledger_are_distinct(self):
        self.doc["extension"]["claims"][0]["evidence"][-1]["target"] = "lit:S99"
        self.doc["extension"]["sources_read"][0]["id"] = "lit:S99"
        self.save()
        ctx = self.ctx()
        self.assertIn("resolution.unknown_source", self.codes(ctx, "error"))
        self.assertFalse(ctx["sources"]["lit:S99"]["resolved"])
        (self.root / "evidence" / "lit" / "sources.json").unlink()
        ctx = self.ctx()
        self.assertIn("resolution.ledger_missing", self.codes(ctx, "unresolved"), "unavailable material is unresolved, not an error")
        self.assertIn("resolution.source_unavailable", self.codes(ctx, "unresolved"))
        self.assertNotIn("resolution.unknown_source", self.codes(ctx))

    def test_ledger_hash_mismatch_and_missing_hash(self):
        write(self.root / "evidence" / "lit" / "sources.json", [dict(SOURCE, title="edited after the record was written")])
        ctx = self.ctx()
        self.assertIn("resolution.ledger_hash_mismatch", self.codes(ctx, "error"))
        self.assertEqual(ctx["ledgers"]["lit"]["sha256_checked"], False)
        del self.doc["extension"]["evidence_ledgers"][0]["sources_sha256"]
        self.save()
        ctx = self.ctx()
        self.assertIn("resolution.ledger_no_hash", self.codes(ctx, "unresolved"))
        self.assertIsNone(ctx["ledgers"]["lit"]["sha256_checked"])

    def test_invalid_ledger_reported(self):
        write(self.root / "evidence" / "lit" / "claims.json", [dict(CLAIM, source_ids=["lit:S77"])])
        self.doc["extension"]["evidence_ledgers"][0]["claims_sha256"] = sha(self.root / "evidence/lit/claims.json")
        self.save()
        ctx = self.ctx()
        self.assertIn("resolution.ledger_invalid", self.codes(ctx, "error"))

    def test_document_missing_and_digest(self):
        (self.root / "paper" / "main.md").unlink()
        ctx = self.ctx()
        self.assertIn("resolution.document_missing", self.codes(ctx, "unresolved"))
        write(self.root / "paper" / "main.md", "changed\n")
        self.doc["extension"]["documents"][0]["sha256"] = "0" * 64
        self.save()
        ctx = self.ctx()
        self.assertIn("resolution.document_changed", self.codes(ctx, "warning"))

    def test_schema_only_check_is_independent_of_files(self):
        shutil.rmtree(self.root / "artifacts")
        shutil.rmtree(self.root / "evidence")
        self.assertTrue(validate_artifact(self.doc).ok)

    def test_unreadable_artifact(self):
        p = self.root / "artifacts" / "broken.json"
        p.write_text("{not json")
        ctx = self.ctx(p)
        self.assertIn("resolution.unreadable", self.codes(ctx, "error"))
        self.assertEqual(ctx["traceability"], "none")
        self.assertIn("schema", [c["check"] for c in ctx["checks_not_run"]])
        self.assertTrue(all(c["reason"] for c in ctx["checks_not_run"]))


class BoundProfileTests(ProjectFixture):
    def test_bound_profile_ledger_resolves_its_namespace(self):
        prof = json.loads((ROOT / "profiles" / "experiments" / "eic" / "profile.json").read_text())
        write(self.root / "hep-research.project.json", {"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0",
                                                         "experiments": [{"profile": prof["id"], "version": prof["version"]}], "theory": []})
        ext = self.doc["extension"]
        ext["evidence_ledgers"].append({"namespace": "eic", "bound": True})
        ext["sources_read"].append({"id": "eic:S01", "level": "page", "verification_date": "2026-10-12"})
        ext["claims"][1]["evidence"].append({"id": "ev:C2-e", "target_kind": "source", "target": "eic:S01", "locator": "page body",
                                             "role": "background", "usage": "context-only", "usage_reason": "orientation only"})
        ext["claims"][1]["assessment"]["currency"] = "stale"
        self.save()
        ctx = self.ctx()
        self.assertTrue(ctx["ledgers"]["eic"]["loaded"], ctx["ledgers"].get("eic"))
        self.assertTrue(ctx["ledgers"]["eic"]["bound"])
        self.assertTrue(ctx["sources"]["eic:S01"]["resolved"])
        self.assertNotIn("resolution.unknown_source", self.codes(ctx))
        self.assertNotIn("resolution.ledger_missing", self.codes(ctx))

    def test_unbound_profile_namespace_is_not_scanned(self):
        ext = self.doc["extension"]
        ext["evidence_ledgers"].append({"namespace": "eic", "bound": True})
        self.save()
        ctx = self.ctx()
        self.assertFalse(ctx["ledgers"]["eic"]["loaded"])
        self.assertIn("resolution.ledger_not_bound", self.codes(ctx, "error"))


class DependencyVocabularyTests(unittest.TestCase):
    def test_bound_profile_vocabulary_reaches_the_dependency_checker(self):
        from contracts.project import load_project
        src = ROOT / "contracts" / "fixtures" / "projects" / "local_profile"
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td) / "proj"
            shutil.copytree(src, proj)
            pj = proj / "local-profiles" / "exp-local" / "profile.json"
            prof = json.loads(pj.read_text())
            prof.update(id="experiment:local-vocab-synthetic", vocabulary_namespaces=["locv"],
                        vocabulary_extensions={"levels": ["locv:trigger-level"]})
            pj.write_text(json.dumps(prof))
            cfg = json.loads((proj / "hep-research.project.json").read_text())
            cfg["experiments"] = [{"profile": "experiment:local-vocab-synthetic", "version": "1.0.0"}]
            cfg["overrides"] = []
            (proj / "hep-research.project.json").write_text(json.dumps(cfg))
            p = load_project(proj)
            self.assertTrue(p.report.ok, [f.as_dict() for f in p.report.findings])
            vocab = Vocabulary.with_profiles(p.profiles)
            pred = copy.deepcopy(PRED)
            pred["extension"]["observable"]["level"] = "locv:trigger-level"
            srcp = write(proj / "artifacts" / "pred.json", pred)
            consumer = copy.deepcopy(LEGACY)
            consumer["inputs"] = [{"ref": "artifacts/pred.json", "sha256": sha(srcp), "status": ["synthetic", "unvalidated"]}]
            cpath = write(proj / "artifacts" / "comm.json", consumer)
            without = validate_dependencies(cpath, proj)
            self.assertIn("dependency.source_invalid", {f["code"] for f in without["findings"]})
            with_vocab = validate_dependencies(cpath, proj, vocab=vocab)
            self.assertEqual(with_vocab["status"], "ok", with_vocab["findings"])
            ctx = resolve_context(cpath, proj)  # the project config in the root is picked up without being passed
            self.assertEqual(ctx["dependencies"]["status"], "ok", ctx["dependencies"]["findings"])
            self.assertEqual(ctx["profiles"], ["experiment:local-vocab-synthetic"])


class OutcomeTests(unittest.TestCase):
    def test_unresolved_with_report_ok_is_incomplete(self):
        rep = Report()
        rep.add("unresolved", "$", "x.pending", "needs the source")
        self.assertTrue(rep.ok)
        self.assertEqual(resolve_outcome(findings_of(rep)), ("incomplete", 3))

    def test_error_wins_over_unresolved_and_warning_alone_passes(self):
        rep = Report()
        rep.add("warning", "$", "x.note", "n")
        self.assertEqual(resolve_outcome(findings_of(rep)), ("pass", 0))
        rep.add("unresolved", "$", "x.pending", "p")
        rep.add("error", "$", "x.bad", "b")
        self.assertEqual(resolve_outcome(findings_of(rep)), ("fail", 1))

    def test_input_error_wins(self):
        self.assertEqual(resolve_outcome([{"severity": "error", "path": "$", "code": "x", "message": "m"}], input_error=True), ("input-error", 2))

    def test_blocked_required_check_is_incomplete(self):
        self.assertEqual(resolve_outcome([], blocked=True), ("incomplete", 3))

    def test_failed_upstream_with_status_ok_normalizes_to_incomplete(self):
        dep = {"status": "ok", "dependency_consistency_ok": False, "failed_upstream": True, "findings": []}
        f = normalize_dependency_report(dep)
        self.assertEqual([x["code"] for x in f], ["dependency.failed_upstream"])
        self.assertEqual(f[0]["severity"], "unresolved")
        self.assertEqual(resolve_outcome(f), ("incomplete", 3))
        dep = {"status": "error", "dependency_consistency_ok": False, "failed_upstream": False,
               "findings": [{"severity": "error", "path": "$", "code": "dependency.missing", "message": "m"}]}
        self.assertEqual(resolve_outcome(normalize_dependency_report(dep)), ("fail", 1))


class OutputAliasTests(unittest.TestCase):
    def test_output_path_aliasing_an_input_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            inp = write(d / "record.json", {"a": 1})
            link = d / "alias.json"
            link.symlink_to(inp)
            self.assertTrue(output_aliases_input(inp, [inp]))
            self.assertTrue(output_aliases_input(link, [inp]))
            self.assertTrue(output_aliases_input(d / "sub" / ".." / "record.json", [inp]))
            self.assertFalse(output_aliases_input(d / "report.json", [inp]))
            self.assertFalse(output_aliases_input(d / "missing" / "report.json", [inp]))


if __name__ == "__main__":
    unittest.main()


class ReviewMinors(ProjectFixture):
    def test_changed_document_with_inspected_occurrences_is_unresolved(self):
        write(self.root / "paper" / "main.md", "changed\n")
        self.doc["extension"]["documents"][0]["sha256"] = "0" * 64
        self.doc["extension"]["occurrences"][0]["state"] = "inspected"
        self.save()
        ctx = self.ctx()
        self.assertIn("resolution.document_changed", self.codes(ctx, "unresolved"))
        self.doc["extension"]["occurrences"][0]["state"] = "mapped"
        self.save()
        ctx = self.ctx()
        self.assertIn("resolution.document_changed", self.codes(ctx, "warning"))
        self.assertNotIn("resolution.document_changed", self.codes(ctx, "unresolved"))
