"""P3: exposure and decision lineage (C12, T1.9, T4.3). Exposure records are ordered and append-only, a decision record
binds a prefix of the exposure record that survives appends but not edits, the envelope data_exposure is derived by one
function (signal-region data give exposed, missing or invalid records give unknown, never unexposed), the change review
and the bundle freezing use it, a release-manifest check refuses a release the exposure record knows but the manifest
omits, and the new capability IDs are refused by a reader that lacks them. Synthetic values only."""
import copy
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import lineage as ln  # noqa: E402
from contracts import revocation as rv  # noqa: E402
from contracts import validate as vd  # noqa: E402
from contracts.release_manifest import canonical_sha256, manifest_digest  # noqa: E402

FIXTURE = ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "computational_run.json"
SOURCE = {"snapshot_id": "synthetic-snapshot-7", "sha256": "1" * 64}


def entry(seq, release, seen, time, via="session"):
    return {"seq": seq, "release_id": release, "via": {"kind": via, "id": f"{via}-{seq}"}, "seen": seen, "time": time,
            "actor": "synthetic analyst"}


def record(*entries, previous=None):
    return {"record_version": "1.0.0", "analysis": "synthetic-analysis", "source": SOURCE, "previous_sha256": previous,
            "entries": list(entries)}


def codes(rep):
    return {f.code for f in rep.findings}


class ExposureRecordTests(unittest.TestCase):
    def setUp(self):
        self.v1 = record(entry(1, "rel-000", ["blinded-derivative"], "2026-10-10T10:00:00Z"))
        self.v2 = copy.deepcopy(self.v1)
        self.v2["previous_sha256"] = canonical_sha256(self.v1)
        self.v2["entries"].append(entry(2, "rel-001", ["control-region"], "2026-10-11T10:00:00Z", "relay"))

    def test_valid_and_appended(self):
        self.assertTrue(ln.check_exposure(self.v1).ok)
        self.assertTrue(ln.check_append(self.v1, self.v2).ok)

    def test_ordering_and_vocabulary(self):
        bad = copy.deepcopy(self.v2)
        bad["entries"][1]["seq"] = 3
        self.assertIn("lineage.seq_gap", codes(ln.check_exposure(bad)))
        bad = copy.deepcopy(self.v2)
        bad["entries"][1]["time"] = "2026-10-09T10:00:00Z"
        self.assertIn("lineage.time_order", codes(ln.check_exposure(bad)))
        bad = copy.deepcopy(self.v1)
        bad["entries"][0]["seen"] = ["control-region", "control-region"]
        self.assertIn("lineage.duplicate_kind", codes(ln.check_exposure(bad)))
        bad["entries"][0]["seen"] = ["a quick look"]
        self.assertIn("schema.enum", codes(ln.check_exposure(bad)))
        bad["entries"][0]["seen"] = []
        self.assertIn("schema.min_items", codes(ln.check_exposure(bad)))

    def test_append_only(self):
        edited = copy.deepcopy(self.v2)
        edited["entries"][0]["seen"] = ["control-region"]
        self.assertIn("lineage.history_changed", codes(ln.check_append(self.v1, edited)))
        dropped = copy.deepcopy(self.v2)
        dropped["entries"] = [dict(dropped["entries"][1], seq=1)]
        self.assertIn("lineage.history_changed", codes(ln.check_append(self.v1, dropped)))
        unbound = dict(self.v2, previous_sha256="f" * 64)
        self.assertIn("lineage.not_appended", codes(ln.check_append(self.v1, unbound)))
        other = dict(self.v2, analysis="another-analysis")
        self.assertIn("lineage.other_record", codes(ln.check_append(self.v1, other)))

    def test_derive(self):
        self.assertEqual(ln.derive_exposure(None), {"state": "unknown", "basis": "none"})
        self.assertEqual(ln.derive_exposure({"entries": []}), {"state": "unknown", "basis": "none"})
        self.assertEqual(ln.derive_exposure(self.v2, "records/exposure.json"),
                         {"state": "unexposed", "basis": "structured-record", "record_ref": "records/exposure.json"})
        self.assertEqual(ln.derive_exposure(record())["state"], "unexposed")
        for kind in sorted(ln.EXPOSING):
            rec = copy.deepcopy(self.v2)
            rec["entries"].append(entry(3, "rel-002", ["control-region", kind], "2026-10-12T10:00:00Z"))
            self.assertEqual(ln.derive_exposure(rec)["state"], "exposed", kind)
            self.assertEqual(ln.derive_exposure(rec, through_seq=2)["state"], "unexposed")

    def test_a_new_session_never_clears_exposure(self):
        rec = record(entry(1, "rel-000", ["signal-region"], "2026-10-10T10:00:00Z"))
        later = copy.deepcopy(rec)
        later["previous_sha256"] = canonical_sha256(rec)
        later["entries"].append(entry(2, "rel-001", ["synthetic"], "2026-10-11T10:00:00Z"))
        self.assertTrue(ln.check_append(rec, later).ok)
        self.assertEqual(ln.derive_exposure(later)["state"], "exposed")
        cleared = dict(later, entries=[dict(later["entries"][1], seq=1)])
        self.assertFalse(ln.check_append(rec, cleared).ok)  # the only way to "clear" it is refused

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            p1, p2 = Path(d, "v1.json"), Path(d, "v2.json")
            p1.write_text(json.dumps(self.v1))
            p2.write_text(json.dumps(self.v2))
            run = lambda *a: subprocess.run([sys.executable, str(ROOT / "contracts" / "lineage.py"), *a],
                                            capture_output=True, text=True, timeout=60)
            p = run("exposure", str(p2), "--previous", str(p1), "--record-ref", "x.json")
            self.assertEqual(p.returncode, 0, p.stdout)
            self.assertEqual(json.loads(p.stdout)["data_exposure"]["record_ref"], "x.json")
            p = run("exposure", str(p1), "--previous", str(p2))
            self.assertEqual(p.returncode, 1)
            p = run("exposure", str(Path(d, "missing.json")))
            self.assertEqual(p.returncode, 2)


class DecisionRecordTests(unittest.TestCase):
    def setUp(self):
        self.exp = record(entry(1, "rel-000", ["control-region"], "2026-10-10T10:00:00Z"),
                          entry(2, "rel-001", ["signal-region"], "2026-10-12T10:00:00Z"))
        self.dec = {"record_version": "1.0.0", "decision_id": "dec-1", "analysis": "synthetic-analysis",
                    "decision": "choose the synthetic flux recipe", "category": "recipe-selection",
                    "actor": {"kind": "agent", "id": "synthetic-session"}, "time": "2026-10-11T10:00:00Z",
                    "seen": {"through_seq": 1, "entries_sha256": ln.entries_digest(self.exp, 1)},
                    "artifacts": [{"ref": "art/a.json", "sha256": "a" * 64}], "recipe_sha256": "7" * 64}

    def test_valid_and_exposure_at_decision_time(self):
        self.assertTrue(ln.check_decision(self.dec, self.exp).ok, ln.check_decision(self.dec, self.exp).findings)
        self.assertEqual(ln.decision_exposure(self.dec, self.exp)["state"], "unexposed")
        self.assertEqual(ln.derive_exposure(self.exp)["state"], "exposed")  # the analysis is exposed now

    def test_binding_survives_appends_not_edits(self):
        later = copy.deepcopy(self.exp)
        later["entries"].append(entry(3, "rel-002", ["synthetic"], "2026-10-13T10:00:00Z"))
        self.assertTrue(ln.check_decision(self.dec, later).ok)
        edited = copy.deepcopy(self.exp)
        edited["entries"][0]["seen"] = ["simulation"]
        self.assertIn("lineage.seen_mismatch", codes(ln.check_decision(self.dec, edited)))
        self.assertEqual(ln.decision_exposure(self.dec, edited), {"state": "unknown", "basis": "none"})

    def test_understated_and_impossible_seen(self):
        late = dict(self.dec, time="2026-10-13T10:00:00Z")
        self.assertIn("lineage.seen_understated", codes(ln.check_decision(late, self.exp)))
        early = dict(self.dec, time="2026-10-09T10:00:00Z")
        self.assertIn("lineage.seen_after_decision", codes(ln.check_decision(early, self.exp)))
        beyond = dict(self.dec, seen={"through_seq": 5, "entries_sha256": "0" * 64})
        self.assertIn("lineage.seen_beyond_record", codes(ln.check_decision(beyond, self.exp)))
        self.assertIn("lineage.other_analysis", codes(ln.check_decision(dict(self.dec, analysis="other"), self.exp)))
        self.assertIn("lineage.exposure_unchecked", codes(ln.check_decision(self.dec)))
        self.assertIn("lineage.exposure_invalid", codes(ln.check_decision(self.dec, {"entries": []})))
        self.assertIn("schema.enum", codes(ln.check_decision(dict(self.dec, actor={"kind": "robot", "id": "x"}), self.exp)))


class DecisionArtifactHashTests(unittest.TestCase):
    """artifacts[].sha256 is compared with the file's SHA-256 when the record has a location (base_dir; the CLI
    passes the decision record's folder, or --artifacts-root). Without a base_dir the library check is unchanged."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.d = Path(tmp.name)
        (self.d / "records").mkdir()
        (self.d / "art").mkdir()
        self.body = b'{"synthetic": "split manifest"}'
        (self.d / "records" / "split.json").write_bytes(self.body)
        (self.d / "art" / "out.json").write_bytes(self.body)
        self.exp = record(entry(1, "rel-000", ["control-region"], "2026-10-10T10:00:00Z"))
        self.dec = {"record_version": "1.0.0", "decision_id": "dec-1", "analysis": "synthetic-analysis",
                    "decision": "freeze the synthetic split", "category": "other",
                    "actor": {"kind": "human", "id": "synthetic analyst"}, "time": "2026-10-11T10:00:00Z",
                    "seen": {"through_seq": 1, "entries_sha256": ln.entries_digest(self.exp, 1)},
                    "artifacts": [{"ref": "split.json", "sha256": hashlib.sha256(self.body).hexdigest()}]}

    def check(self, dec, base="records"):
        return ln.check_decision(dec, self.exp, base_dir=self.d / base)

    def test_matching_file_is_valid(self):
        self.assertEqual(self.check(self.dec).findings, [])
        absolute = copy.deepcopy(self.dec)
        absolute["artifacts"][0]["ref"] = str(self.d / "art" / "out.json")
        self.assertEqual(self.check(absolute).findings, [])

    def test_mismatch_is_an_error(self):
        (self.d / "records" / "split.json").write_bytes(self.body + b" ")
        rep = self.check(self.dec)
        self.assertFalse(rep.ok)
        self.assertEqual(codes(rep), {"lineage.artifact_mismatch"})
        self.assertEqual(rep.errors[0].path, "$.artifacts[0].sha256")

    def test_missing_file_is_an_error(self):
        gone = copy.deepcopy(self.dec)
        gone["artifacts"][0]["ref"] = "absent.json"
        self.assertEqual(codes(self.check(gone)), {"lineage.artifact_missing"})
        folder = copy.deepcopy(self.dec)
        folder["artifacts"][0]["ref"] = "."
        self.assertEqual(codes(self.check(folder)), {"lineage.artifact_missing"})

    def test_relative_refs_resolve_against_the_base(self):
        rooted = copy.deepcopy(self.dec)
        rooted["artifacts"][0]["ref"] = "art/out.json"
        self.assertEqual(codes(self.check(rooted)), {"lineage.artifact_missing"})  # not under records/
        self.assertEqual(self.check(rooted, base=".").findings, [])

    def test_without_base_dir_artifacts_are_not_opened(self):
        gone = copy.deepcopy(self.dec)
        gone["artifacts"][0]["ref"] = "absent.json"
        self.assertTrue(ln.check_decision(gone, self.exp).ok)
        self.assertEqual(ln.decision_exposure(gone, self.exp)["state"], "unexposed")

    def test_artifact_findings_do_not_hide_exposure_findings(self):
        gone = copy.deepcopy(self.dec)
        gone["artifacts"][0]["ref"] = "absent.json"
        rep = ln.check_decision(gone, None, base_dir=self.d / "records")
        self.assertEqual(codes(rep), {"lineage.artifact_missing", "lineage.exposure_unchecked"})

    def test_cli(self):
        exp_path = self.d / "records" / "exposure.json"
        exp_path.write_text(json.dumps(self.exp))
        dec_path = self.d / "records" / "decision.json"
        run = lambda *a: subprocess.run([sys.executable, str(ROOT / "contracts" / "lineage.py"), "decision",
                                         str(dec_path), "--exposure", str(exp_path), *a],
                                        capture_output=True, text=True, timeout=60)
        dec_path.write_text(json.dumps(self.dec))
        p = run()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        bad = copy.deepcopy(self.dec)
        bad["artifacts"][0]["sha256"] = "0" * 64
        dec_path.write_text(json.dumps(bad))
        p = run()
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(out["status"], "invalid")
        self.assertEqual({f["code"] for f in out["findings"]}, {"lineage.artifact_mismatch"})
        rooted = copy.deepcopy(self.dec)
        rooted["artifacts"][0]["ref"] = "art/out.json"
        dec_path.write_text(json.dumps(rooted))
        self.assertEqual(run().returncode, 1)
        p = run("--artifacts-root", str(self.d))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(run("--artifacts-root", str(self.d / "absent")).returncode, 2)


class ProducerTests(unittest.TestCase):
    """P3.2: the change review and the bundle freezing derive data_exposure with the same function."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.changes = self.d / "changes.json"
        self.changes.write_text(json.dumps({"changes": [{
            "id": "c1", "parameter": "synthetic cut", "old": 1, "new": 2, "motivation": "new calibration from the control sample",
            "evidence": {"control_sample": "synthetic control", "evidence_ids": ["ev-1"], "independent_of_signal_region": True},
            "looked_at": ["control-region data"]}]}))

    def tearDown(self):
        self.tmp.cleanup()

    def review(self, *extra):
        p = subprocess.run([sys.executable, str(ROOT / "skills" / "hep-measurement" / "scripts" / "review_analysis_change.py"),
                            str(self.changes), *extra], capture_output=True, text=True, timeout=60)
        return p.returncode, json.loads(p.stdout)

    def test_change_review(self):
        code, out = self.review()
        self.assertEqual(out["changes"][0]["decision"], "accept")
        rec = self.d / "exposure.json"
        rec.write_text(json.dumps(record(entry(1, "rel-000", ["control-region"], "2026-10-10T10:00:00Z"))))
        code, out = self.review("--exposure-record", str(rec))
        self.assertEqual(out["changes"][0]["decision"], "accept")
        self.assertEqual(out["changes"][0]["data_exposure"]["basis"], "structured-record")
        rec.write_text(json.dumps(record(entry(1, "rel-000", ["signal-region"], "2026-10-10T10:00:00Z"))))
        code, out = self.review("--exposure-record", str(rec))
        self.assertEqual((code, out["changes"][0]["decision"]), (1, "flag"))
        code, out = self.review("--exposure-record", str(self.d / "missing.json"))
        self.assertEqual(out["changes"][0]["decision"], "exposure-unknown")
        self.assertEqual(out["changes"][0]["data_exposure"]["state"], "unknown")

    def test_bundle_freezing(self):
        from tests.adapters.batch_harness import WORKER, Harness
        h = Harness("slurm", items=4, chunk=2)
        self.addCleanup(h.cleanup)
        wdir = h.dir / "worker-code"
        wdir.mkdir()
        (wdir / "worker.py").write_text(WORKER)
        h.cmd = (f"{shlex.quote(sys.executable)} {wdir / 'worker.py'} --start {{start}} --stop {{stop}} "
                 "--seed {seed} --out {out} --id {id}")
        self.assertEqual(h.plan()[0], 0)
        rec = self.d / "exposure.json"
        rec.write_text(json.dumps(record(entry(1, "rel-000", ["signal-region"], "2026-10-10T10:00:00Z"))))
        code, out = h.cli("freeze", "--worker-root", str(wdir), "--exposure-record", str(rec))
        self.assertEqual(code, 0, out)
        bundle = json.loads(Path(out["path"]).read_text())
        self.assertEqual(bundle["data_exposure"], {"state": "exposed", "basis": "structured-record", "record_ref": str(rec)})
        code, out = h.cli("freeze", "--worker-root", str(wdir), "--exposure-record", str(self.d / "missing.json"))
        self.assertEqual(json.loads(Path(out["path"]).read_text())["data_exposure"], {"state": "unknown", "basis": "none"})
        code, out = h.cli("freeze", "--worker-root", str(wdir), "--exposure-record", str(rec),
                          "--exposure", '{"state": "unknown", "basis": "none"}')
        self.assertEqual(code, 2, out)


class ReleaseHistoryTests(unittest.TestCase):
    """P3.3: earlier releases are known from both the ledger and the exposure record."""

    def setUp(self):
        from tests.contracts.test_release_manifest import ReleaseManifestTests
        self.case = ReleaseManifestTests("test_valid_release_passes_only_with_every_input")
        self.case.setUp()
        self.addCleanup(self.case.tearDown)
        self.rec = record(entry(1, "synthetic-release-000", ["blinded-derivative"], "2026-10-07T10:00:00Z"))

    def run_check(self, manifest=None, **kw):
        m = self.case.m if manifest is None else manifest
        kw.setdefault("approval", dict(self.case.approval, manifest_sha256=manifest_digest(m)))
        return {f["code"] for f in self.case.run_check(m, analysis="synthetic-analysis", **kw)["findings"]
                if f["severity"] == "error"}

    def test_release_in_record_but_not_listed_is_refused(self):
        self.assertIn("release.related_incomplete", self.run_check(exposure_record=self.rec))

    def test_listed_and_known_passes(self):
        m = copy.deepcopy(self.case.m)
        m["related_releases"] = ["synthetic-release-000"]
        m["composition_review"] = {"reviewer": "synthetic reviewer", "date": "2026-10-07", "conclusion": "shapes only"}
        self.assertEqual(self.run_check(m, exposure_record=self.rec), set())

    def test_record_problems(self):
        rec = record(entry(1, "rel-unknown-to-ledger", ["control-region"], "2026-10-07T10:00:00Z"))
        self.assertIn("release.exposure_release_unknown", self.run_check(exposure_record=rec))
        self.assertIn("release.exposure_other_record", self.run_check(exposure_record=dict(self.rec, analysis="other")))
        self.assertIn("release.exposure_invalid", self.run_check(exposure_record={"entries": []}))
        out = self.case.run_check(exposure_record=self.rec)
        self.assertIn("release.exposure_without_analysis", {f["code"] for f in out["findings"]})


class IndexAndCapabilityTests(unittest.TestCase):
    def test_index_follows_exposure_and_decision_records(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "records").mkdir()
            (root / "art").mkdir()
            (root / "records" / "exposure.json").write_text(json.dumps(
                record(entry(1, "rel-1", ["blinded-derivative"], "2026-10-10T10:00:00Z"))))
            (root / "art" / "fit.json").write_text(json.dumps(
                {"contract_version": "2.6.0", "artifact_id": "fit", "artifact_type": "computational-run",
                 "data_exposure": {"state": "unexposed", "basis": "structured-record", "record_ref": "../records/exposure.json"}}))
            body = b'{"synthetic": true}'
            (root / "art" / "out.json").write_bytes(body)
            (root / "records" / "decision.json").write_text(json.dumps(
                {"record_version": "1.0.0", "decision_id": "dec-1", "recipe_sha256": "7" * 64,
                 "artifacts": [{"ref": "art/out.json", "sha256": hashlib.sha256(body).hexdigest()}]}))
            idx = rv.build_index(root)
            self.assertEqual(rv.affected(idx, {"kind": "release", "ref": "rel-1"}), ["art/fit.json", "records/exposure.json"])
            self.assertEqual(rv.affected(idx, {"kind": "recipe", "sha256": "7" * 64}), ["art/out.json", "records/decision.json"])

    def test_capabilities_known_and_refused_by_an_older_reader(self):
        doc = dict(json.loads(FIXTURE.read_text()), required_capabilities=["core:revocation-log", "core:exposure-record", "core:decision-lineage"])
        self.assertNotIn("contract.unknown_capability", {f.code for f in vd.validate_artifact(doc, protected=True).findings})
        older = frozenset({"core:plugin-release-identity", "core:data-exposure", "stats:result-semantics",
                           "communication:traceability-v1"})
        import contracts
        with mock.patch.object(contracts, "KNOWN_CAPABILITIES", older):
            rep = vd.validate_artifact(doc, protected=True)
        self.assertEqual(sum(f.code == "contract.unknown_capability" for f in rep.errors), 3)

    def test_undeclared_exposure_capability_warns(self):
        doc = dict(json.loads(FIXTURE.read_text()), data_exposure={"state": "unexposed", "basis": "structured-record",
                                                                 "record_ref": "records/exposure.json"})
        self.assertIn("exposure.capability_not_declared", {f.code for f in vd.validate_artifact(doc).findings})
        doc["required_capabilities"] = ["core:exposure-record"]
        self.assertNotIn("exposure.capability_not_declared", {f.code for f in vd.validate_artifact(doc).findings})


if __name__ == "__main__":
    unittest.main()
