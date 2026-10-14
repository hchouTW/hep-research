"""P4.2: a release prepared from each blinding mode passes contracts/release_manifest.py with every custodian option
(code digest, destination sets, release history by analysis and exposure record, sealed-value scan) once the
custodian's approval binds it; the preparation refuses a sealed file inside the release, a non-empty release directory,
an unknown code identity and key-like parameters. Synthetic data only."""
from __future__ import annotations

import copy
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import release_manifest as rm  # noqa: E402
from contracts import release_prepare as rp  # noqa: E402
from core.blinding import transforms as tf  # noqa: E402

NOW = datetime.datetime(2026, 10, 14, 12, 0, 0, tzinfo=datetime.UTC)
CODE = "2" * 64
SERVICE = {"service": "synthetic-model-service", "tenant": "synthetic-tenant", "region": "synthetic-region",
           "model_families": ["family-a"], "data_handling": "synthetic terms"}
DEST = {"services": [SERVICE], "tools": ["Read"], "network": [], "recipients": ["synthetic analyst"],
        "logging": {"transcripts": "local only", "telemetry": "off"}}
SOURCE = {"snapshot_id": "synthetic-snapshot-7", "sha256": "1" * 64}
META = {"release_id": "synthetic-release-002", "source": SOURCE,
        "review": {"reviewer": "synthetic reviewer", "date": "2026-10-13", "scope": "synthetic release"},
        "approval_ref": "approval-002", "purposes": ["exploration"], "destinations": DEST,
        "validity": {"effective": "2026-10-14T00:00:00Z", "expires": "2026-10-20T00:00:00Z", "revocation_ref": "rev-002",
                     "status_source": "synthetic-custodian", "max_status_age_s": 3600},
        "composition_review": {"reviewer": "synthetic reviewer", "date": "2026-10-13",
                               "conclusion": "the earlier release masks the same region"}}
LEDGER = [{"release_id": "synthetic-release-001", "manifest_sha256": "3" * 64, "analysis": "synthetic-analysis",
           "source_sha256": SOURCE["sha256"]}]
EXPOSURE = {"record_version": "1.0.0", "analysis": "synthetic-analysis", "source": SOURCE, "previous_sha256": None,
            "entries": [{"seq": 1, "release_id": "synthetic-release-001", "via": {"kind": "session", "id": "s-1"},
                         "seen": ["blinded-derivative"], "time": "2026-10-12T10:00:00Z", "actor": "synthetic analyst"}]}
REGION = {"variable": "m", "low": 20, "high": 30}
RELEASES = {
    "binned-mask": lambda: tf.binned_mask([0, 10, 20, 30, 40, 50], [12.0, 30.0, 47.0, 25.0, 9.0], REGION),
    "event-removal": lambda: tf.event_removal([{"m": m, "evt": i} for i, m in enumerate([3.5, 12.25, 21.0, 26.5, 33.75, 48.5])],
                                              "m", REGION, drop_fields=["evt"]),
    "common-offset": lambda: tf.common_offset([1.25, 2.5, 7.75, 11.125], 3.7316),
    "common-scale": lambda: tf.common_scale([0.137, 0.522, 0.9013, 0.311], 1.8125),
}


class ReleasePrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def prepared(self, mode):
        out, sealed = self.d / mode / "release", self.d / mode / "custodian" / "sealed.json"
        m = rp.prepare(RELEASES[mode](), META, out, sealed, ledger=LEDGER, analysis="synthetic-analysis",
                       exposure_record=EXPOSURE, code_digest=CODE)
        return m, out, json.loads(sealed.read_text())

    def full_check(self, m, out, sealed):
        approval = {"approval_id": "approval-002", "manifest_sha256": rm.manifest_digest(m), "approver": "custodian-a",
                    "authority": "data-release", "purposes": ["exploration"], "destinations_sha256": rm.canonical_sha256(DEST),
                    "valid_from": "2026-10-01T00:00:00Z", "valid_until": "2026-10-31T00:00:00Z"}
        effective = {"services": [{"service": "synthetic-model-service", "tenant": "synthetic-tenant",
                                   "region": "synthetic-region", "model_family": "family-a"}],
                     "tools": ["Read"], "network": [], "recipients": ["synthetic analyst"], "logging": DEST["logging"]}
        return rm.check(m, out, approval, {"custodian-a": ["data-release"]}, LEDGER,
                        {"as_of": "2026-10-14T11:30:00Z", "source": "synthetic-custodian", "revoked": []}, effective, NOW,
                        code_digest=CODE, destination_sets={"s1": DEST}, analysis="synthetic-analysis", sealed=sealed,
                        exposure_record=EXPOSURE)

    def test_every_mode_passes_the_full_check(self):
        for mode in tf.MODES:
            with self.subTest(mode=mode):
                m, out, sealed = self.prepared(mode)
                self.assertEqual(sorted(p.name for p in out.iterdir()), ["released.json"])
                self.assertEqual(m["related_releases"], ["synthetic-release-001"])
                self.assertTrue(sealed["sealed"])
                rep = self.full_check(m, out, sealed)
                self.assertEqual(rep["status"], "pass", rep["findings"])

    def test_a_sealed_value_in_the_release_fails_the_check(self):
        m, out, sealed = self.prepared("common-offset")
        doc = json.loads((out / "released.json").read_text())
        doc["values"].append(sealed["sealed"][0])  # an original value leaks into the release
        (out / "released.json").write_text(json.dumps(doc))
        body = (out / "released.json").read_bytes()
        import hashlib
        m["artifacts"][0].update(sha256=hashlib.sha256(body).hexdigest(), size=len(body))
        codes = {f["code"] for f in self.full_check(m, out, sealed)["findings"]}
        self.assertIn("release.sealed_value_present", codes)

    def test_refusals(self):
        rel = RELEASES["common-scale"]()
        with self.assertRaises(rp.PrepareRefused) as cm:
            rp.prepare(rel, META, self.d / "r", self.d / "r" / "sealed.json", code_digest=CODE)
        self.assertEqual(cm.exception.code, "prepare.sealed_in_release")
        (self.d / "full").mkdir()
        (self.d / "full" / "x").write_text("x")
        with self.assertRaises(rp.PrepareRefused) as cm:
            rp.prepare(rel, META, self.d / "full", self.d / "s.json", code_digest=CODE)
        self.assertEqual(cm.exception.code, "prepare.out_not_empty")
        with self.assertRaises(rp.PrepareRefused) as cm:
            rp.prepare(rel, META, self.d / "r2", self.d / "s2.json", code_digest="not-hex")
        self.assertEqual(cm.exception.code, "prepare.code_unknown")
        bad = copy.deepcopy(rel)
        bad["parameters"]["scale_used"] = 1.8125
        with self.assertRaises(rp.PrepareRefused) as cm:
            rp.prepare(bad, META, self.d / "r3", self.d / "s3.json", code_digest=CODE)
        self.assertEqual(cm.exception.code, "prepare.keys_present")
        with self.assertRaises(rp.PrepareRefused) as cm:
            rp.prepare(rel, {k: v for k, v in META.items() if k != "validity"}, self.d / "r4", self.d / "s4.json",
                       code_digest=CODE)
        self.assertEqual(cm.exception.code, "prepare.meta_incomplete")

    def test_command_line(self):
        rel_file, meta_file = self.d / "release.json", self.d / "meta.json"
        rel_file.write_text(json.dumps(RELEASES["binned-mask"]()))
        meta_file.write_text(json.dumps(META))
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rp.main(["--release", str(rel_file), "--meta", str(meta_file), "--out", str(self.d / "rel"),
                            "--sealed-out", str(self.d / "cust" / "sealed.json"), "--code-digest", CODE])
        rep = json.loads(out.getvalue())
        self.assertEqual((code, rep["status"]), (0, "prepared"), rep)
        self.assertTrue(Path(rep["manifest"]).is_file())
        self.assertFalse((self.d / "rel" / "sealed.json").exists())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rp.main(["--release", str(rel_file), "--meta", str(meta_file), "--out", str(self.d / "r9"),
                                      "--sealed-out", str(self.d / "s9.json"), "--code-digest", CODE,
                                      "--manifest-out", str(self.d / "r9" / "m.json")]), 1)


if __name__ == "__main__":
    unittest.main()
