"""T1.2: data release manifest schema and its semantic checker. A valid synthetic release passes only with every input
present; missing fields, forged or unbound approvals, content mismatches, destination mismatches, reused IDs, stale or
revoked status all fail. The custodian options (code digest, destination sets, release history, sealed-value scan) and
the always-on key and wildcard rules are covered by CustodianOptionTests. Synthetic data and sentinels only."""
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
        self.assertIn("release.approvers_malformed", codes(self.run_check(approvers={"custodian-a": "data-release-readonly"})))
        self.assertIn("release.status_unknown", codes(self.run_check(
            revocations=dict(self.inputs["revocations"], revoked=["synthetic-release-001"]))))
        self.assertIn("release.ledger_malformed", codes(self.run_check(ledger=[["synthetic-release-001", "5" * 64]])))
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
        files["effective"].write_text(json.dumps({"services": ["not-an-object"], "tools": [], "network": [], "recipients": [],
                                                  "logging": {}}))
        p = run(argv)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertNotIn("Traceback", p.stderr)
        files["approval"].write_text("{not json")
        self.assertEqual(run(argv).returncode, 2)


class CustodianOptionTests(unittest.TestCase):
    """Checks moved from the deployment's custodian into the plugin: each one fails closed, and none is needed for a
    pass when its option is not given (backward compatible)."""
    setUp, tearDown, run_check = ReleaseManifestTests.setUp, ReleaseManifestTests.tearDown, ReleaseManifestTests.run_check

    def resign(self, m):
        """A manifest edit invalidates the approval binding; re-bind it so only the rule under test can fail."""
        return dict(self.approval, manifest_sha256=rm.manifest_digest(m), destinations_sha256=rm.canonical_sha256(m["destinations"]))

    def write_histogram(self, doc, name="hists/masked.json"):
        body = json.dumps(doc).encode()
        (self.root / name).write_bytes(body)
        m = copy.deepcopy(self.m)
        m["artifacts"].append({"path": name, "sha256": hashlib.sha256(body).hexdigest(), "size": len(body), "format": "json"})
        return m

    def test_keys_never_travel(self):
        m = copy.deepcopy(self.m)
        m["transform"]["keys_recorded"] = True
        self.assertIn("schema.const", codes(self.run_check(m, approval=self.resign(m))))
        for name in ("offset", "blinding_key", "Scale_factor", "seed"):
            with self.subTest(parameter=name):
                m = copy.deepcopy(self.m)
                m["transform"]["parameters"] = {"region": {"low": 1, "high": 2}, "nested": [{name: 3}]}
                self.assertIn("release.keys_present", codes(self.run_check(m, approval=self.resign(m))))

    def test_wildcard_destination(self):
        m = copy.deepcopy(self.m)
        m["destinations"]["network"] = ["*.example.org"]
        self.assertIn("release.destination_wildcard", codes(self.run_check(m, approval=self.resign(m))))

    def test_code_digest(self):
        self.assertEqual(self.run_check(code_digest="2" * 64)["status"], "pass")
        self.assertIn("release.transform_code_mismatch", codes(self.run_check(code_digest="9" * 64)))
        self.assertIn("release.code_digest_malformed", codes(self.run_check(code_digest="2" * 63)))

    def test_destination_sets(self):
        held = {"s1": copy.deepcopy(self.m["destinations"])}
        self.assertEqual(self.run_check(destination_sets=held)["status"], "pass")
        other = copy.deepcopy(held)
        other["s1"]["tools"] = ["Read", "Bash"]  # a superset is not the same set
        self.assertIn("release.destination_set_unknown", codes(self.run_check(destination_sets=other)))
        for bad in ({}, [], {"s1": "not-an-object"}):
            self.assertIn("release.destination_sets_malformed", codes(self.run_check(destination_sets=bad)))

    def test_history(self):
        ledger = [{"release_id": "synthetic-release-000", "manifest_sha256": "3" * 64, "analysis": "bc-twin"},
                  {"release_id": "other-analysis-000", "manifest_sha256": "4" * 64, "analysis": "elsewhere",
                   "source_sha256": "8" * 64}]
        self.assertEqual(self.run_check(ledger=ledger, analysis="elsewhere-2")["status"], "pass")
        self.assertIn("release.related_incomplete", codes(self.run_check(ledger=ledger, analysis="bc-twin")))
        same_source = [dict(ledger[1], source_sha256="1" * 64)]
        self.assertIn("release.related_incomplete", codes(self.run_check(ledger=same_source, analysis="bc-twin")))
        m = copy.deepcopy(self.m)
        m["related_releases"] = ["synthetic-release-000"]
        m["composition_review"] = {"reviewer": "synthetic reviewer", "date": "2026-10-07", "conclusion": "no combination"}
        self.assertEqual(self.run_check(m, approval=self.resign(m), ledger=ledger, analysis="bc-twin")["status"], "pass")
        m["related_releases"] = ["synthetic-release-000", "never-published"]
        self.assertIn("release.related_unknown", codes(self.run_check(m, approval=self.resign(m), ledger=ledger, analysis="bc-twin")))
        m["related_releases"] = ["synthetic-release-000"]
        rev = dict(self.inputs["revocations"], revoked=[{"ref": "synthetic-release-000", "time": "2026-10-08T10:00:00Z", "reason": "x"}])
        out = self.run_check(m, approval=self.resign(m), ledger=ledger, analysis="bc-twin", revocations=rev)
        self.assertEqual(out["status"], "pass", out)
        self.assertIn("release.related_revoked", {f["code"] for f in out["findings"] if f["severity"] == "warning"})
        self.assertIn("release.history_unchecked", codes(self.run_check(ledger=None, analysis="bc-twin")))
        self.assertIn("release.analysis_malformed", codes(self.run_check(analysis=" ")))

    def test_sealed_scan(self):
        sealed = {"sealed": [1234.5678, 17.25], "rtol": 1e-9}
        clean = {"edges": [0, 7, 17.25, 30], "values": [5, None, 9], "blinded_bins": [False, True, False],
                 "region": {"low": 7, "high": 17.25}}
        m = self.write_histogram(clean)
        out = self.run_check(m, approval=self.resign(m), sealed=sealed)
        self.assertEqual(out["status"], "pass", out)  # 17.25 as an edge and a region bound is structure, not data
        leak = dict(clean, values=[5, 1234.5678, 9])
        m = self.write_histogram(leak)
        out = self.run_check(m, approval=self.resign(m), sealed=sealed)
        self.assertIn("release.sealed_value_present", codes(out))
        msg = json.dumps(out["findings"])
        self.assertNotIn("1234", msg)  # no sealed value, token or count in a finding
        ratio_leak = dict(clean, ratio_to_reference=[1.0, 17.25, 1.1])
        m = self.write_histogram(ratio_leak)
        self.assertIn("release.sealed_value_present", codes(self.run_check(m, approval=self.resign(m), sealed=sealed)))

    def test_sealed_scan_fails_closed(self):
        sealed = {"sealed": [1234.5678], "rtol": 1e-9}
        self.assertIn("release.scan_incomplete", codes(self.run_check(sealed=sealed, root=None)))
        for bad in ({"sealed": []}, {"sealed": ["x"]}, {"sealed": [1.0], "rtol": 1e-3}, {"sealed": [1.0], "rtol": True}, []):
            with self.subTest(sealed=bad):
                self.assertIn("release.sealed_malformed", codes(self.run_check(sealed=bad)))
        self.assertEqual(self.run_check(sealed={"sealed": [], "nothing_sealable": True})["status"], "pass")
        body = b"\x89PNG\r\n\x1a\n binary"
        (self.root / "hists" / "plot.png").write_bytes(body)
        m = copy.deepcopy(self.m)
        m["artifacts"].append({"path": "hists/plot.png", "sha256": hashlib.sha256(body).hexdigest(), "size": len(body), "format": "png"})
        self.assertIn("release.scan_incomplete", codes(self.run_check(m, approval=self.resign(m), sealed=sealed)))
        (self.root / "hists" / "broken.json").write_bytes(b"{not json")
        m = copy.deepcopy(self.m)
        m["artifacts"].append({"path": "hists/broken.json", "sha256": hashlib.sha256(b"{not json").hexdigest(), "size": 9, "format": "json"})
        self.assertIn("release.scan_incomplete", codes(self.run_check(m, approval=self.resign(m), sealed=sealed)))

    def test_cli_custodian_options(self):
        d = Path(self.tmp.name)
        names = ("approval", "approvers", "ledger", "revocations", "effective")
        files = {"manifest": d / "manifest.json"}
        files["manifest"].write_text(json.dumps(self.m))
        for n in names:
            files[n] = d / f"{n}.json"
            files[n].write_text(json.dumps(self.approval if n == "approval" else self.inputs[n]))
        (d / "sets.json").write_text(json.dumps({"s1": self.m["destinations"]}))
        (d / "sealed.json").write_text(json.dumps({"sealed": [1234.5678], "rtol": 1e-9}))
        argv = [sys.executable, str(ROOT / "contracts" / "release_manifest.py"), str(files["manifest"]), "--root", str(self.root),
                "--now", "2026-10-08T12:00:00Z", "--code-digest", "2" * 64, "--destination-sets", str(d / "sets.json"),
                "--analysis", "bc-twin", "--sealed", str(d / "sealed.json")] + [x for n in names for x in (f"--{n}", str(files[n]))]
        p = subprocess.run(argv, capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        p = subprocess.run([a if a != "2" * 64 else "9" * 64 for a in argv], capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 1)
        self.assertIn("release.transform_code_mismatch", p.stdout)
        (d / "sealed.json").write_text("{not json")
        self.assertEqual(subprocess.run(argv, capture_output=True, text=True, timeout=600).returncode, 2)


if __name__ == "__main__":
    unittest.main()
