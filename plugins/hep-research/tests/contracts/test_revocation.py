"""P2: hash-chained revocation log, head, source checks and reverse index (C07, F07). An empty, cut, edited, reordered
or truncated log, a head for another log, from another source, stale or in the future are refused, and a refused log
never answers 'nothing revoked'. The reverse index marks every artifact derived from a revoked subject, transitively,
without changing any bytes. Synthetic values only."""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import revocation as rv  # noqa: E402
from contracts.release_manifest import canonical_sha256  # noqa: E402
from core.protected.trusted_input import Account, file_refusals, read_protected  # noqa: E402

NOW = datetime.datetime(2026, 10, 14, 12, 0, 0, tzinfo=datetime.UTC)
SRC = "custodian:synthetic-revocations"
SHA_A = "a" * 64


def make_log(n_events=2):
    recs = [rv.genesis("log-synthetic", "custodian", "2026-10-14T08:00:00Z")]
    for i in range(n_events):
        recs.append(rv.next_event(recs, {"kind": "artifact", "sha256": f"{i + 1:x}" * 64}, f"synthetic reason {i}",
                                  "custodian", f"2026-10-14T09:0{i}:00Z"))
    return recs


def blob(recs):
    return b"".join(rv.encode(r) for r in recs)


def other_account():
    """An account that is not the file owner and is in none of its groups: the file looks custodian-written."""
    return Account(os.geteuid() + 4242, frozenset())


class ChainTests(unittest.TestCase):
    def setUp(self):
        self.recs = make_log()
        self.head = rv.head_of(self.recs, SRC, "2026-10-14T11:00:00Z")

    def check(self, data, head=None, **kw):
        return rv.verify(data, self.head if head is None else head, source=kw.pop("source", SRC), now=NOW, **kw)

    def codes(self, st):
        return {f["code"] for f in st.findings}

    def test_valid_log_passes_and_answers(self):
        st = self.check(blob(self.recs))
        self.assertTrue(st.ok, st.findings)
        self.assertEqual(st.count, 3)
        self.assertIsNotNone(st.revoked(sha256="1" * 64))
        self.assertIsNone(st.revoked(sha256=SHA_A))
        self.assertEqual(st.revoked_digests(), {"1" * 64, "2" * 64})

    def test_genesis_only_log_is_valid_and_means_nothing_revoked(self):
        recs = make_log(0)
        st = rv.verify(blob(recs), rv.head_of(recs, SRC, "2026-10-14T11:00:00Z"), source=SRC, now=NOW)
        self.assertTrue(st.ok, st.findings)
        self.assertEqual(st.revoked_digests(), set())

    def test_empty_and_missing(self):
        self.assertIn("revocation.empty", self.codes(self.check(b"")))
        self.assertIn("revocation.empty", self.codes(self.check(b"\n\n")))
        self.assertIn("revocation.log_unreadable", self.codes(self.check(None)))

    def test_refused_log_never_answers(self):
        st = self.check(b"")
        self.assertFalse(st.ok)
        for call in (lambda: st.revoked(sha256=SHA_A), st.revoked_digests, st.status_doc):
            with self.assertRaises(rv.RevocationUnverified):
                call()

    def test_truncated_by_records(self):
        st = self.check(blob(self.recs[:2]))
        self.assertIn("revocation.truncated", self.codes(st))
        self.assertFalse(st.ok)

    def test_cut_mid_line(self):
        data = blob(self.recs)
        self.assertIn("revocation.truncated_line", self.codes(self.check(data[:-1])))
        self.assertFalse(self.check(data[:-20]).ok)

    def test_edited_record_breaks_chain(self):
        recs = [dict(r) for r in self.recs]
        recs[1] = dict(recs[1], reason="edited")
        self.assertIn("revocation.chain_broken", self.codes(self.check(blob(recs))))

    def test_edited_last_record_mismatches_head(self):
        recs = [dict(r) for r in self.recs]
        recs[-1] = dict(recs[-1], reason="edited")
        self.assertIn("revocation.head_mismatch", self.codes(self.check(blob(recs))))

    def test_removed_middle_record(self):
        self.assertIn("revocation.seq_gap", self.codes(self.check(blob([self.recs[0], self.recs[2]]))))

    def test_reordered(self):
        self.assertFalse(self.check(blob([self.recs[0], self.recs[2], self.recs[1]])).ok)

    def test_appended_after_head(self):
        recs = self.recs + [rv.next_event(self.recs, {"kind": "release", "ref": "rel-x"}, "late", "c", "2026-10-14T10:00:00Z")]
        self.assertIn("revocation.head_mismatch", self.codes(self.check(blob(recs))))

    def test_replaced_by_other_log(self):
        other = [rv.genesis("log-other", "custodian", "2026-10-14T08:00:00Z")]
        self.assertIn("revocation.head_other_log", self.codes(self.check(blob(other))))

    def test_bad_lines(self):
        data = blob(self.recs)
        self.assertIn("revocation.bad_record", self.codes(self.check(data.replace(b'"seq":1', b'"seq":1,"seq":1', 1))))
        self.assertIn("revocation.bad_record", self.codes(self.check(data + b"not json\n")))
        self.assertIn("revocation.bad_genesis", self.codes(self.check(blob(self.recs[1:]))))
        legacy = json.dumps({"subject_sha256": SHA_A, "reason": "x"}).encode() + b"\n"
        self.assertFalse(rv.is_chained_log(legacy))
        self.assertTrue(rv.is_chained_log(data))
        self.assertIn("revocation.bad_genesis", self.codes(self.check(legacy)))

    def test_time_order_and_event_after_head(self):
        recs = make_log(0)
        recs.append(rv.next_event(recs, {"kind": "artifact", "sha256": SHA_A}, "r", "c", "2026-10-14T09:00:00Z"))
        recs.append(rv.next_event(recs, {"kind": "artifact", "sha256": "b" * 64}, "r", "c", "2026-10-14T08:30:00Z"))
        self.assertIn("revocation.time_order", self.codes(rv.verify(blob(recs), rv.head_of(recs, SRC, "2026-10-14T11:00:00Z"),
                                                                     source=SRC, now=NOW)))
        head = rv.head_of(self.recs, SRC, "2026-10-14T09:00:30Z")
        self.assertIn("revocation.event_after_head", self.codes(self.check(blob(self.recs), head)))

    def test_head_problems(self):
        data = blob(self.recs)
        self.assertIn("revocation.other_source", self.codes(self.check(data, source="somewhere-else")))
        stale = dict(self.head, as_of="2026-10-12T11:00:00Z")
        self.assertIn("revocation.stale", self.codes(self.check(data, stale)))
        future = dict(self.head, as_of="2026-10-15T11:00:00Z")
        self.assertIn("revocation.stale", self.codes(self.check(data, future)))
        self.assertIn("revocation.stale", self.codes(self.check(data, max_age_s=600)))
        self.assertIn("revocation.age_too_long", self.codes(self.check(data, max_age_s=10 ** 6)))
        self.assertIn("revocation.head_malformed", self.codes(self.check(data, {"count": 3})))
        self.assertIn("revocation.head_malformed", self.codes(rv.verify(data, None, source=SRC, now=NOW)))
        self.assertIn("revocation.source_unchecked", self.codes(self.check(data, source="")))

    def test_status_doc_filters_kinds(self):
        recs = make_log(0)
        recs.append(rv.next_event(recs, {"kind": "release", "ref": "rel-1"}, "r", "c", "2026-10-14T09:00:00Z"))
        recs.append(rv.next_event(recs, {"kind": "attestation", "ref": "att-1"}, "r", "c", "2026-10-14T09:01:00Z"))
        st = rv.verify(blob(recs), rv.head_of(recs, SRC, "2026-10-14T11:00:00Z"), source=SRC, now=NOW)
        self.assertEqual([r["ref"] for r in st.status_doc(("release",))["revoked"]], ["rel-1"])
        self.assertEqual(st.status_doc(("release",))["source"], SRC)
        self.assertIsNone(st.revoked(kind="release", ref="att-1"))

    def test_writer_refuses_bad_subject(self):
        with self.assertRaises(ValueError):
            rv.next_event(self.recs, {"kind": "artifact"}, "r", "c")
        with self.assertRaises(ValueError):
            rv.next_event(self.recs, {"kind": "planet", "ref": "x"}, "r", "c")


class SourceTests(unittest.TestCase):
    """DP-4: in protected use the log and head must be files the running account neither owns nor can write or replace.
    Ownership by another identity cannot be created in a test without privileges, so the 'custodian' case is modeled by
    evaluating the same files for another account."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "cust"
        self.dir.mkdir()
        self.recs = make_log()
        self.log = self.dir / "revocations.jsonl"
        self.head = self.dir / "head.json"
        self.log.write_bytes(blob(self.recs))
        self.head.write_text(json.dumps(rv.head_of(self.recs, SRC, "2026-10-14T11:00:00Z")))
        for p in (self.log, self.head):
            os.chmod(p, 0o644)
        os.chmod(self.dir, 0o755)

    def tearDown(self):
        os.chmod(self.dir, 0o755)
        self.tmp.cleanup()

    def load(self, account=None, protected=True, log=None, head=None):
        return rv.load(log or self.log, head or self.head, source=SRC, now=NOW, protected=protected, account=account)

    def codes(self, st):
        return {f["code"] for f in st.findings}

    def test_custodian_owned_files_pass_for_another_account(self):
        st = self.load(other_account())
        self.assertTrue(st.ok, st.findings)

    def test_own_files_refused_in_protected_mode(self):
        st = self.load()
        self.assertFalse(st.ok)
        self.assertIn("source.replaceable", self.codes(st))  # the account owns the directory as well
        # every directory above a temporary file is the account's own, so the file checks are exercised directly
        codes = {c for c, _ in file_refusals(os.stat(self.log), Account.current(), "log")}
        self.assertEqual(codes, {"source.owned_by_account", "source.writable_by_account"})
        self.assertTrue(self.load(protected=False).ok)

    def test_group_writable_refused(self):
        acct = Account(os.geteuid() + 4242, frozenset({os.stat(self.log).st_gid}))
        os.chmod(self.log, 0o664)
        self.assertIn("source.writable_by_account", self.codes(self.load(acct)))

    def test_replaceable_directory_refused(self):
        acct = Account(os.geteuid() + 4242, frozenset({os.stat(self.dir).st_gid}))
        os.chmod(self.dir, 0o775)
        self.assertIn("source.replaceable", self.codes(self.load(acct)))

    def test_sticky_directory_is_not_replaceable_by_others(self):
        acct = Account(os.geteuid() + 4242, frozenset({os.stat(self.dir).st_gid}))
        os.chmod(self.dir, 0o1777)
        self.assertTrue(self.load(acct).ok)

    def test_hard_link_refused(self):
        os.link(self.log, self.dir / "extra-link")
        self.assertIn("source.hard_linked", self.codes(self.load(other_account())))

    def test_symlink_in_trusted_directory_is_followed_and_checked(self):
        link = self.dir / "log-link"
        link.symlink_to(self.log.name)
        self.assertTrue(self.load(other_account(), log=link).ok)
        os.chmod(self.log, 0o666)
        self.assertIn("source.writable_by_account", self.codes(self.load(other_account(), log=link)))

    def test_missing_and_not_regular(self):
        self.assertIn("source.missing", self.codes(self.load(other_account(), log=self.dir / "nope")))
        self.assertIn("source.not_regular", self.codes(self.load(other_account(), log=self.dir)))
        fifo = self.dir / "fifo"
        os.mkfifo(fifo)
        self.assertIn("source.not_regular", self.codes(self.load(other_account(), log=fifo)))

    def test_read_protected_returns_checked_bytes(self):
        chk = read_protected(self.log, other_account())
        self.assertTrue(chk.ok)
        self.assertEqual(chk.data, self.log.read_bytes())
        self.assertEqual(chk.sha256, hashlib.sha256(self.log.read_bytes()).hexdigest())


def envelope(aid, inputs=(), exposure_ref=None):
    doc = {"contract_version": "2.6.0", "artifact_id": aid, "artifact_type": "computational-run", "objective": "synthetic",
           "inputs": list(inputs), "status": ["synthetic"]}
    if exposure_ref:
        doc["data_exposure"] = {"state": "exposed", "basis": "structured-record", "record_ref": exposure_ref}
    return doc


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, doc):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, indent=1))
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def snapshot(self):
        return {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_recipe_revocation_marks_derivatives_transitively(self):
        recipe = json.loads((ROOT / "contracts" / "semantics" / "recipes" / "flux_from_counts.json").read_text())
        rsha = self.write("recipes/flux.json", recipe)
        a = self.write("art/a.json", envelope("a", [{"ref": "recipes/flux.json", "sha256": rsha}]))
        b = self.write("art/b.json", envelope("b", [{"ref": "art/a.json", "sha256": a}]))
        self.write("art/c.json", envelope("c", [{"ref": "art/b.json", "sha256": b}]))
        self.write("art/unrelated.json", envelope("u"))
        before = self.snapshot()
        idx = rv.build_index(self.root)
        got = rv.affected(idx, {"kind": "recipe", "sha256": canonical_sha256(recipe)})
        self.assertEqual(got, ["art/a.json", "art/b.json", "art/c.json", "recipes/flux.json"])
        self.assertEqual(rv.affected(idx, {"kind": "recipe", "sha256": rsha}), got)
        self.assertEqual(rv.affected(idx, {"kind": "artifact", "ref": "art/b.json"}), ["art/b.json", "art/c.json"])
        self.assertEqual(self.snapshot(), before, "building the index changed bytes")

    def test_ref_without_hash_still_links(self):
        self.write("art/a.json", envelope("a"))
        self.write("art/b.json", envelope("b", [{"ref": "art/a.json"}]))
        idx = rv.build_index(self.root)
        self.assertEqual(rv.affected(idx, {"kind": "artifact", "ref": "art/a.json"}), ["art/a.json", "art/b.json"])

    def test_release_and_source_propagate(self):
        rel_file = self.root / "release" / "counts.json"
        rel_file.parent.mkdir()
        rel_file.write_text('{"counts": [1, 2]}')
        csha = hashlib.sha256(rel_file.read_bytes()).hexdigest()
        self.write("release/manifest.json", {"manifest_version": "1.0.0", "release_id": "rel-1",
                                             "source": {"snapshot_id": "snap-1", "sha256": "5" * 64},
                                             "artifacts": [{"path": "counts.json", "sha256": csha, "size": 1, "format": "json"}]})
        self.write("art/fit.json", envelope("fit", [{"ref": "release/counts.json", "sha256": csha}]))
        idx = rv.build_index(self.root)
        want = ["art/fit.json", "release/counts.json", "release/manifest.json"]
        self.assertEqual(rv.affected(idx, {"kind": "release", "ref": "rel-1"}), want)
        self.assertEqual(rv.affected(idx, {"kind": "source", "ref": "snap-1"}), want)
        self.assertEqual(rv.affected(idx, {"kind": "source", "sha256": "5" * 64}), want)

    def test_exposure_record_ref_and_attestation(self):
        self.write("records/exposure.json", {"record": "synthetic"})
        self.write("art/a.json", envelope("a", exposure_ref="../records/exposure.json"))
        self.write("att.json", {"attestation_version": "1.0.0", "attestation_id": "att-1",
                                "subject": {"bundle_sha256": "6" * 64, "scope": {"recipe": {"sha256": "7" * 64}}},
                                "lifecycle": {"revocation_ref": "rev-att-1"}})
        idx = rv.build_index(self.root)
        self.assertEqual(rv.affected(idx, {"kind": "artifact", "ref": "records/exposure.json"}),
                         ["art/a.json", "records/exposure.json"])
        self.assertEqual(rv.affected(idx, {"kind": "recipe", "sha256": "7" * 64}), ["att.json"])
        self.assertEqual(rv.affected(idx, {"kind": "attestation", "ref": "rev-att-1"}), ["att.json"])

    def test_links_and_outside_refs_are_not_followed(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        Path(outside.name, "x.json").write_text(json.dumps(envelope("x")))
        (self.root / "linked").symlink_to(outside.name)
        self.write("art/a.json", envelope("a", [{"ref": "../../escape.json"}]))
        idx = rv.build_index(self.root)
        self.assertEqual(sorted(idx.files), ["art/a.json"])

    def test_affected_by_log(self):
        a = self.write("art/a.json", envelope("a"))
        self.write("art/b.json", envelope("b", [{"ref": "art/a.json", "sha256": a}]))
        recs = make_log(0)
        recs.append(rv.next_event(recs, {"kind": "artifact", "sha256": a}, "synthetic", "c", "2026-10-14T09:00:00Z"))
        st = rv.verify(blob(recs), rv.head_of(recs, SRC, "2026-10-14T11:00:00Z"), source=SRC, now=NOW)
        self.assertEqual(rv.affected_by(rv.build_index(self.root), st), {"art/a.json": [1], "art/b.json": [1]})


class DependencyTests(unittest.TestCase):
    """P2.3: dependencies.py reads the verified log; the legacy format is a warning, refused in protected mode."""

    def setUp(self):
        from tests.contracts.test_r5_contracts import run_doc
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.up = self.root / "up.json"
        self.up.write_text(json.dumps(run_doc(artifact_id="up")), encoding="utf-8")
        self.up_sha = hashlib.sha256(self.up.read_bytes()).hexdigest()
        self.down = self.root / "down.json"
        self.down.write_text(json.dumps(run_doc(artifact_id="down", inputs=[
            {"ref": "up.json", "sha256": self.up_sha, "status": ["synthetic", "unvalidated"]}])), encoding="utf-8")
        self.cust = self.root / "custodian"
        self.cust.mkdir()
        self.log, self.head = self.cust / "log.jsonl", self.cust / "head.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write_log(self, subjects):
        recs = make_log(0)
        for i, s in enumerate(subjects):
            recs.append(rv.next_event(recs, s, "synthetic", "custodian", f"2026-10-14T09:0{i}:00Z"))
        self.log.write_bytes(blob(recs))
        self.head.write_text(json.dumps(rv.head_of(recs, SRC, "2026-10-14T11:00:00Z")))
        return recs

    def deps(self, **kw):
        from contracts.dependencies import validate_dependencies
        kw.setdefault("revocation_head", self.head)
        kw.setdefault("revocation_source", SRC)
        return validate_dependencies(self.down, self.root, revocations=kw.pop("revocations", self.log), now=NOW, **kw)

    def codes(self, rep):
        return {f["code"] for f in rep["findings"]}

    def test_revoked_upstream_from_chained_log(self):
        self.write_log([{"kind": "artifact", "sha256": self.up_sha}])
        rep = self.deps()
        self.assertIn("dependency.revoked", self.codes(rep))
        self.assertFalse(rep["dependency_consistency_ok"])

    def test_valid_log_without_matching_event_is_consistent(self):
        self.write_log([{"kind": "artifact", "sha256": SHA_A}])
        rep = self.deps()
        self.assertTrue(rep["dependency_consistency_ok"], rep["findings"])

    def test_unverified_log_fails_closed(self):
        recs = self.write_log([{"kind": "artifact", "sha256": SHA_A}])
        self.log.write_bytes(blob(recs[:1]))  # truncated: the head counts two records
        rep = self.deps()
        self.assertIn("dependency.revocations_unverified", self.codes(rep))
        self.assertFalse(rep["dependency_consistency_ok"])
        self.write_log([])
        self.assertIn("dependency.revocations_unverified", self.codes(self.deps(revocation_source=None)))
        self.assertIn("dependency.revocations_unverified", self.codes(self.deps(revocation_head=None)))

    def test_empty_file_is_an_error(self):
        self.log.write_bytes(b"")
        rep = self.deps()
        self.assertIn("dependency.revocations_unreadable", self.codes(rep))
        self.assertFalse(rep["dependency_consistency_ok"])

    def test_legacy_format_warns_outside_protected_mode(self):
        self.log.write_text(json.dumps({"subject_sha256": self.up_sha, "reason": "synthetic"}) + "\n")
        rep = self.deps()
        self.assertIn("dependency.revocations_legacy", self.codes(rep))
        self.assertIn("dependency.revoked", self.codes(rep))

    def test_protected_flag_without_a_protected_project_is_refused(self):
        self.write_log([])
        rep = self.deps(protected=True)
        self.assertIn("protected.policy_missing", self.codes(rep))
        self.assertEqual((rep["status"], rep["checked"]), ("error", []))

    def test_inside_protected_mode(self):
        """With the protected inputs established: the authoritative log applies, a legacy --revocations is refused,
        and an extra chained log must itself be a protected input."""
        from tests.contracts.test_r5_contracts import run_doc
        from tests.protected_fixture import ProtectedProject
        from contracts.dependencies import validate_dependencies
        pp = ProtectedProject(self.root / "prot").start()
        self.addCleanup(pp.stop)
        up = pp.artifact("up.json", run_doc(artifact_id="up"))
        up_sha = hashlib.sha256(up.read_bytes()).hexdigest()
        down = pp.artifact("down.json", run_doc(artifact_id="down", inputs=[
            {"ref": "up.json", "sha256": up_sha, "status": ["synthetic", "unvalidated"]}]))
        rep = validate_dependencies(down, pp.project)
        self.assertTrue(rep["protected"])
        self.assertTrue(rep["dependency_consistency_ok"], rep["findings"])
        pp.revoke("artifact", sha256=up_sha)
        self.assertIn("dependency.revoked", self.codes(validate_dependencies(down, pp.project)))
        legacy = pp.project / "legacy.jsonl"
        legacy.write_text(json.dumps({"subject_sha256": up_sha, "reason": "synthetic"}) + "\n")
        self.assertIn("dependency.revocations_legacy", self.codes(validate_dependencies(down, pp.project, revocations=legacy)))
        extra = pp.project / "extra.jsonl"
        extra.write_bytes(blob(make_log(0)))
        head = pp.project / "extra-head.json"
        head.write_text(json.dumps(rv.head_of(make_log(0), SRC, "2026-10-14T11:00:00Z")))
        rep = validate_dependencies(down, pp.project, revocations=extra, revocation_head=head, revocation_source=SRC)
        self.assertIn("dependency.revocations_unverified", self.codes(rep))  # a file in the project is replaceable

class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        p = subprocess.run([sys.executable, str(ROOT / "contracts" / "revocation.py"), *args], capture_output=True,
                           text=True, timeout=60)
        return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)

    def test_init_append_head_verify_affected(self):
        with tempfile.TemporaryDirectory() as d:
            log, head = Path(d, "log.jsonl"), Path(d, "head.json")
            self.assertEqual(self.run_cli("init", str(log), "--log-id", "l", "--actor", "c", "--time", "2026-10-14T08:00:00Z")[0], 0)
            self.assertEqual(self.run_cli("init", str(log), "--log-id", "l", "--actor", "c")[0], 2)
            code, out = self.run_cli("append", str(log), "--kind", "artifact", "--sha256", SHA_A, "--reason", "r",
                                     "--actor", "c", "--time", "2026-10-14T09:00:00Z")
            self.assertEqual(code, 0, out)
            self.assertEqual(self.run_cli("append", str(log), "--kind", "artifact", "--reason", "r", "--actor", "c")[0], 2)
            code, out = self.run_cli("head", str(log), "--source", SRC, "--as-of", "2026-10-14T11:00:00Z")
            head.write_text(json.dumps(out))
            code, out = self.run_cli("verify", str(log), "--head", str(head), "--source", SRC, "--now", "2026-10-14T12:00:00Z")
            self.assertEqual((code, out["status"], out["count"]), (0, "ok", 2))
            code, out = self.run_cli("verify", str(log), "--head", str(head), "--source", SRC, "--now",
                                     "2026-10-14T12:00:00Z", "--protected")
            self.assertEqual((code, out["status"]), (1, "refused"))
            self.assertTrue({"source.owned_by_account", "source.replaceable"} & {f["code"] for f in out["findings"]})
            proj = Path(d, "proj")
            proj.mkdir()
            code, out = self.run_cli("affected", str(log), "--head", str(head), "--source", SRC, "--now",
                                     "2026-10-14T12:00:00Z", "--root", str(proj))
            self.assertEqual((code, out["affected"]), (0, {}))
            log.write_bytes(b"")
            self.assertEqual(self.run_cli("verify", str(log), "--head", str(head), "--source", SRC)[0], 1)


class StatusSourceTests(unittest.TestCase):
    """P2.4: release manifests and attestations take the verified log as their one status source, end to end."""

    def log_status(self, subjects, source, as_of, now):
        recs = make_log(0)
        for i, s in enumerate(subjects):
            recs.append(rv.next_event(recs, s, "synthetic", "custodian", f"2026-10-08T0{i}:00:00Z"))
        return recs, rv.verify(blob(recs), rv.head_of(recs, source, as_of), source=source, now=now, max_age_s=3600)

    def setUp(self):
        from tests.contracts.test_release_manifest import ReleaseManifestTests
        self.rm_case = ReleaseManifestTests("test_valid_release_passes_only_with_every_input")
        self.rm_case.setUp()
        self.addCleanup(self.rm_case.tearDown)

    def test_release_manifest(self):
        from contracts import release_manifest as rm
        from tests.contracts.test_release_manifest import NOW as RNOW
        case = self.rm_case
        _, st = self.log_status([], "synthetic-custodian", "2026-10-08T11:30:00Z", RNOW)
        self.assertEqual(case.run_check(revocations=st)["status"], "pass")
        _, st = self.log_status([{"kind": "release", "ref": "rev-001"}], "synthetic-custodian", "2026-10-08T11:30:00Z", RNOW)
        self.assertIn("release.revoked", {f["code"] for f in case.run_check(revocations=st)["findings"]})
        _, st = self.log_status([{"kind": "attestation", "ref": "rev-001"}], "synthetic-custodian", "2026-10-08T11:30:00Z", RNOW)
        self.assertEqual(case.run_check(revocations=st)["status"], "pass")  # another kind's subject does not revoke it
        bad = rv.verify(b"", None, source="synthetic-custodian", now=RNOW)
        out = case.run_check(revocations=bad)
        self.assertIn("release.status_unverified", {f["code"] for f in out["findings"]})
        self.assertEqual(out["status"], "fail")
        # command line: the log is verified against the manifest's own status source and age
        d = Path(case.tmp.name)
        recs, _ = self.log_status([{"kind": "release", "ref": "synthetic-release-001"}], "synthetic-custodian",
                                  "2026-10-08T11:30:00Z", RNOW)
        (d / "log.jsonl").write_bytes(blob(recs))
        (d / "head.json").write_text(json.dumps(rv.head_of(recs, "synthetic-custodian", "2026-10-08T11:30:00Z")))
        files = {}
        for name in ("approval", "approvers", "ledger", "effective"):
            files[name] = d / f"{name}.json"
            files[name].write_text(json.dumps(case.approval if name == "approval" else case.inputs[name]))
        (d / "m.json").write_text(json.dumps(case.m))
        argv = [sys.executable, str(ROOT / "contracts" / "release_manifest.py"), str(d / "m.json"), "--root", str(case.root),
                "--now", "2026-10-08T12:00:00Z", "--revocation-log", str(d / "log.jsonl"), "--revocation-head",
                str(d / "head.json")] + [x for n, f in files.items() for x in (f"--{n}", str(f))]
        p = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("release.revoked", {f["code"] for f in json.loads(p.stdout)["findings"]})
        p = subprocess.run(argv + ["--revocations", str(files["ledger"])], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 2)

    def test_attestation(self):
        from tests.contracts.test_attestation import NOW as ANOW, AttestationTests, axes
        case = AttestationTests("test_all_axes_in_good_state")
        case.setUp()
        self.addCleanup(case.tearDown)
        _, st = self.log_status([], "synthetic-gate", "2026-10-09T11:30:00Z", ANOW)
        self.assertEqual(axes(case.run_eval(revocations=st))["lifecycle"], "active")
        _, st = self.log_status([{"kind": "attestation", "ref": "rev-att-001"}], "synthetic-gate", "2026-10-09T11:30:00Z", ANOW)
        self.assertEqual(axes(case.run_eval(revocations=st))["lifecycle"], "revoked")
        _, st = self.log_status([{"kind": "release", "ref": "att-001"}], "synthetic-gate", "2026-10-09T11:30:00Z", ANOW)
        self.assertEqual(axes(case.run_eval(revocations=st))["lifecycle"], "active")
        out = case.run_eval(revocations=rv.verify(b"", None, source="synthetic-gate", now=ANOW))
        self.assertEqual(axes(out)["lifecycle"], "unknown")
        self.assertIn("attestation.status_unverified", {f["code"] for f in out["findings"]})


if __name__ == "__main__":
    unittest.main()
