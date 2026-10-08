"""T1.2: data release manifest schema and its semantic checker. A valid synthetic release passes only with every input
present; missing fields, forged or unbound approvals, content mismatches, destination mismatches, reused IDs, stale or
revoked status all fail. Synthetic data only."""
import copy
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
from contracts import release_manifest as rm  # noqa: E402

NOW = datetime.datetime(2026, 10, 8, 12, 0, 0, tzinfo=datetime.UTC)
SERVICE = {"service": "synthetic-model-service", "tenant": "synthetic-tenant", "region": "synthetic-region",
           "model_families": ["family-a"], "data_handling": "synthetic terms"}


def codes(out):
    return sorted({f["code"] for f in out["findings"] if f["severity"] == "error"})


class ReleaseManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "release"
        (self.root / "hists").mkdir(parents=True)
        body = b'{"bins": [1, 2, 3], "blinded": "offset hidden"}'
        (self.root / "hists" / "shape.json").write_bytes(body)
        self.m = {
            "manifest_version": "1.0.0", "release_id": "synthetic-release-001",
            "source": {"snapshot_id": "synthetic-snapshot-7", "sha256": "1" * 64},
            "artifacts": [{"path": "hists/shape.json", "sha256": hashlib.sha256(body).hexdigest(), "size": len(body), "format": "json"}],
            "artifact_rules": {"symlinks": "refused", "unlisted_files": "refused"},
            "transform": {"code_sha256": "2" * 64, "parameters": {"normalize": "shape-only"}, "keys_recorded": False},
            "protected": ["signal-strength"], "retained": ["shapes"],
            "review": {"reviewer": "synthetic reviewer", "date": "2026-10-07", "scope": "shape-only release"},
            "approval_ref": "approval-001", "purposes": ["exploration"],
            "destinations": {"services": [SERVICE], "tools": ["Read"], "network": [], "recipients": ["synthetic analyst"],
                             "logging": {"transcripts": "local only", "telemetry": "off"}},
            "validity": {"effective": "2026-10-08T00:00:00Z", "expires": "2026-10-15T00:00:00Z", "revocation_ref": "rev-001",
                         "status_source": "synthetic-custodian", "max_status_age_s": 3600},
            "related_releases": []}
        self.approval = {"approval_id": "approval-001", "manifest_sha256": rm.manifest_digest(self.m), "approver": "custodian-a",
                         "authority": "data-release", "purposes": ["exploration"],
                         "destinations_sha256": rm.canonical_sha256(self.m["destinations"]),
                         "valid_from": "2026-10-01T00:00:00Z", "valid_until": "2026-10-31T00:00:00Z"}
        self.inputs = {"root": self.root, "approval": self.approval, "approvers": {"custodian-a": ["data-release"]},
                       "ledger": [{"release_id": "synthetic-release-000", "manifest_sha256": "3" * 64}],
                       "revocations": {"as_of": "2026-10-08T11:30:00Z", "source": "synthetic-custodian", "revoked": []},
                       "effective": {"services": [{"service": "synthetic-model-service", "tenant": "synthetic-tenant",
                                                   "region": "synthetic-region", "model_family": "family-a"}],
                                     "tools": ["Read"], "network": [], "recipients": ["synthetic analyst"],
                                     "logging": {"transcripts": "local only", "telemetry": "off"}}}

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, manifest=None, **override):
        kw = dict(self.inputs, **override)
        return rm.check(self.m if manifest is None else manifest, now=NOW, **kw)

    def test_valid_release_passes_only_with_every_input(self):
        out = self.run_check()
        self.assertEqual(out["status"], "pass", out)
        self.assertIn("does not release data", out["note"])
        for name, code in (("root", "release.content_unchecked"), ("approval", "release.approval_missing"),
                           ("ledger", "release.ledger_missing"), ("revocations", "release.status_unknown"),
                           ("effective", "release.destinations_unchecked")):
            with self.subTest(missing=name):
                self.assertIn(code, codes(self.run_check(**{name: None})))
        self.assertIn("release.authority_unchecked", codes(self.run_check(approvers=None)))
        for key in ("tools", "network", "recipients"):
            eff = {k: v for k, v in self.inputs["effective"].items() if k != key}
            self.assertIn("release.destinations_unchecked", codes(self.run_check(effective=eff)), key)

    def test_missing_fields_and_schema_rules(self):
        for key in ("release_id", "artifacts", "approval_ref", "destinations", "validity", "protected"):
            with self.subTest(missing=key):
                m = copy.deepcopy(self.m)
                del m[key]
                self.assertEqual(self.run_check(m)["status"], "fail")
        for path, value in ((("transform", "keys_recorded"), True), (("artifacts", 0, "path"), "../outside.json"),
                            (("artifacts", 0, "path"), "/abs.json"), (("purposes",), ["formal-analysis"]),
                            (("artifact_rules", "symlinks"), "followed"), (("source", "sha256"), "abc")):
            with self.subTest(path=path):
                m = copy.deepcopy(self.m)
                node = m
                for k in path[:-1]:
                    node = node[k]
                node[path[-1]] = value
                self.assertEqual(self.run_check(m)["status"], "fail")
        m = copy.deepcopy(self.m)
        m["unexpected"] = 1
        self.assertEqual(self.run_check(m)["status"], "fail")

    def test_forged_or_unbound_approvals(self):
        changed = copy.deepcopy(self.m)
        changed["retained"] = ["shapes", "normalization"]  # the approval binds the old content
        self.assertIn("release.approval_unbound", codes(self.run_check(changed)))
        for key, value, code in (("approval_id", "approval-999", "release.approval_other"),
                                 ("purposes", ["validation"], "release.purpose_unapproved"),
                                 ("destinations_sha256", "4" * 64, "release.destinations_unapproved"),
                                 ("valid_until", "2026-10-08T06:00:00Z", "release.approval_expired"),
                                 ("authority", "anything", "release.authority_wrong"),
                                 ("approver", "someone-else", "release.authority_unknown"),
                                 ("approver", "", "release.approval_incomplete")):
            with self.subTest(key=key):
                self.assertIn(code, codes(self.run_check(approval=dict(self.approval, **{key: value}))))
        # approval_ref is left out of what the approval binds, so naming the approval is not circular
        self.assertEqual(rm.manifest_digest(dict(self.m, approval_ref="other")), rm.manifest_digest(self.m))

    def test_content_mismatch_links_and_unlisted_files(self):
        (self.root / "hists" / "shape.json").write_bytes(b'{"bins": [1, 2, 4]}')
        self.assertIn("release.content_mismatch", codes(self.run_check()))
        self.tearDown()
        self.setUp()
        (self.root / "extra.json").write_text("{}")
        self.assertIn("release.unlisted_file", codes(self.run_check()))
        self.tearDown()
        self.setUp()
        os.symlink(self.root / "hists" / "shape.json", self.root / "link.json")
        self.assertIn("release.symlink", codes(self.run_check()))
        self.tearDown()
        self.setUp()
        (self.root / "hists" / "shape.json").unlink()
        self.assertIn("release.missing_file", codes(self.run_check()))
        self.tearDown()
        self.setUp()
        hidden = self.root / "hidden"
        hidden.mkdir()
        (hidden / "extra.bin").write_bytes(b"x")
        os.chmod(hidden, 0)
        try:
            if os.access(hidden, os.R_OK):  # running as root: permissions do not hide anything
                self.skipTest("directory permissions are not enforced for this user")
            self.assertIn("release.content_unchecked", codes(self.run_check()))
        finally:
            os.chmod(hidden, 0o755)

    def test_destination_mismatch(self):
        for mutate in (lambda e: e["services"][0].update(region="other-region"),
                       lambda e: e["services"][0].update(model_family="family-b"),
                       lambda e: e["services"].append({"service": "background-summarizer", "tenant": "x", "region": "y",
                                                       "model_family": "family-a"}),
                       lambda e: e["network"].append("example.org"),
                       lambda e: e["tools"].append("WebFetch"),
                       lambda e: e["logging"].update(telemetry="on")):
            eff = copy.deepcopy(self.inputs["effective"])
            mutate(eff)
            self.assertIn("release.destination_mismatch", codes(self.run_check(effective=eff)))
        named = copy.deepcopy(self.m)
        named["destinations"]["services"][0]["models"] = ["family-a-2026-09"]
        appr = dict(self.approval, manifest_sha256=rm.manifest_digest(named),
                    destinations_sha256=rm.canonical_sha256(named["destinations"]))
        self.assertIn("release.destination_mismatch", codes(self.run_check(named, approval=appr)))  # model not reported

    def test_reuse_revocation_staleness_and_composition(self):
        self.assertIn("release.id_reused", codes(self.run_check(ledger=[{"release_id": "synthetic-release-001", "manifest_sha256": "5" * 64}])))
        same = [{"release_id": "synthetic-release-001", "manifest_sha256": rm.manifest_digest(self.m)}]
        self.assertEqual(self.run_check(ledger=same)["status"], "pass")  # re-checking the same release is not reuse
        rev = dict(self.inputs["revocations"], revoked=[{"ref": "rev-001", "time": "2026-10-08T10:00:00Z", "reason": "x"}])
        self.assertIn("release.revoked", codes(self.run_check(revocations=rev)))
        stale = dict(self.inputs["revocations"], as_of="2026-10-08T09:00:00Z")
        self.assertIn("release.status_stale", codes(self.run_check(revocations=stale)))
        other = dict(self.inputs["revocations"], source="somewhere else")
        self.assertIn("release.status_other_source", codes(self.run_check(revocations=other)))
        self.assertIn("release.not_valid_now", codes(rm.check(self.m, now=NOW + datetime.timedelta(days=30), **self.inputs)))
        rel = copy.deepcopy(self.m)
        rel["related_releases"] = ["synthetic-release-000"]
        self.assertIn("release.composition_unreviewed", codes(self.run_check(rel)))

    def test_cli_exit_codes(self):
        d = Path(self.tmp.name)
        files = {}
        for name, doc in (("manifest", self.m), ("approval", self.approval), ("approvers", self.inputs["approvers"]),
                          ("ledger", self.inputs["ledger"]), ("revocations", self.inputs["revocations"]),
                          ("effective", self.inputs["effective"])):
            files[name] = d / f"{name}.json"
            files[name].write_text(json.dumps(doc))
        argv = [sys.executable, str(ROOT / "contracts" / "release_manifest.py"), str(files["manifest"]), "--root", str(self.root),
                "--now", "2026-10-08T12:00:00Z"] + [x for n in ("approval", "approvers", "ledger", "revocations", "effective")
                                                    for x in (f"--{n}", str(files[n]))]
        run = lambda a: subprocess.run(a, capture_output=True, text=True, timeout=600)
        p = run(argv)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["status"], "pass")
        p = run([a for a in argv if a not in ("--effective", str(files["effective"]))])
        self.assertEqual(p.returncode, 1)
        files["approval"].write_text("{not json")
        self.assertEqual(run(argv).returncode, 2)


if __name__ == "__main__":
    unittest.main()
