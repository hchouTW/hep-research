"""B09: a batch campaign writes a computational-run artifact; incomplete campaigns are labeled failed."""
import json
import unittest

from contracts.validate import validate_artifact
from tests.adapters.batch_harness import Harness


class ProvenanceTests(unittest.TestCase):
    def campaign(self, backend, faults=None, **extra):
        h = Harness(backend, items=4, chunk=2, extra=extra or None)
        self.addCleanup(h.cleanup)
        h.plan()
        h.set_faults(faults or {})
        h.cli("submit", "--submit")
        h.cli("status")
        out = h.dir / "artifacts" / "run.json"
        code, rep = h.cli("report", "--out", str(out), "--label", "synthetic")
        return h, code, json.loads(out.read_text())

    def test_complete_campaign_artifact_validates(self):
        for backend, version in (("slurm", "slurm 0.0.0-shim"), ("htcondor", "$CondorVersion: 0.0.0-shim (fake scheduler for tests) $")):
            with self.subTest(backend=backend):
                h, code, art = self.campaign(backend)
                self.assertEqual(code, 0)
                rep = validate_artifact(art)
                self.assertTrue(rep.ok, rep.as_dict())
                ext = art["extension"]
                self.assertEqual(art["status"], ["synthetic", "unvalidated"])
                self.assertEqual(ext["tools"][0], {"name": backend, "version": version})
                self.assertEqual(ext["exit_status"], 0)
                self.assertIn("merged", ext["output_hashes"])
                self.assertEqual(sorted(k for k in ext["output_hashes"] if k.startswith("chunks/")), ["chunks/c0000.json", "chunks/c0001.json"])
                self.assertTrue(ext["commands"][0].startswith("sbatch --parsable" if backend == "slurm" else "condor_submit -terse"))
                self.assertEqual(set(ext["seeds"]["chunk_seeds"]), {"c0000", "c0001"})
                self.assertEqual(ext["environment"]["execution"]["campaign_status"], "complete")
                self.assertEqual(len(ext["environment"]["config_sha256"]), 64)
                self.assertTrue(ext["resources"])  # elapsed time / peak memory per attempt where reported
                self.assertEqual({i["path"] for i in ext["input_manifest"]}, {"manifest.json", "spec.json"})

    def test_stopped_chunk_gives_a_failed_artifact(self):
        h, code, art = self.campaign("slurm", faults={"c0001": [{"kind": "exit", "code": 2}]})
        self.assertEqual(code, 1)
        self.assertIn("failed", art["status"])
        self.assertNotIn("observed", art["status"])
        self.assertEqual(art["extension"]["exit_status"], 1)
        self.assertEqual(art["extension"]["environment"]["execution"]["campaign_status"], "incomplete")
        self.assertNotIn("merged", art["extension"]["output_hashes"])
        self.assertTrue(validate_artifact(art).ok)
        art["status"] = [s for s in art["status"] if s != "failed"]
        codes = [f.code for f in validate_artifact(art).errors]
        self.assertIn("status.failed_unlabeled", codes)


if __name__ == "__main__":
    unittest.main()
