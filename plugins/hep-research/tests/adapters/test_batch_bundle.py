"""T4.2 through the batch CLI with the fake Slurm scheduler: freeze, verify-bundle, and submit --bundle refusing a
campaign whose worker code changed after freezing."""
import shlex
import sys
import unittest

from tests.adapters.batch_harness import WORKER, Harness


class BundleCliTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness("slurm", items=4, chunk=2)
        self.wdir = self.h.dir / "worker-code"
        self.wdir.mkdir()
        (self.wdir / "worker.py").write_text(WORKER)
        self.h.cmd = (f"{shlex.quote(sys.executable)} {self.wdir / 'worker.py'} --start {{start}} --stop {{stop}} "
                      "--seed {seed} --out {out} --id {id}")
        self.assertEqual(self.h.plan()[0], 0)

    def tearDown(self):
        self.h.cleanup()

    def test_freeze_verify_and_bound_submission(self):
        code, out = self.h.cli("freeze", "--worker-root", str(self.wdir), "--scope", "synthetic CLI test",
                               "--exposure", '{"state": "unknown", "basis": "none"}')
        self.assertEqual(code, 0, out)
        digest = out["bundle_digest"]
        self.assertRegex(out["approval_request"]["config_hash"], "^[0-9a-f]{64}$")
        code, out = self.h.cli("verify-bundle", "--bundle", digest)
        self.assertEqual((code, out["status"]), (0, "identical"))
        code, out = self.h.cli("submit", "--submit", "--pilot", "--bundle", digest)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.h.state()["submissions"][-1]["bundle_digest"], digest)
        (self.wdir / "worker.py").write_text(WORKER + "# changed after freezing\n")
        code, out = self.h.cli("verify-bundle", "--bundle", digest)
        self.assertEqual((code, out["status"]), (1, "different"))
        code, out = self.h.cli("submit", "--submit", "--bundle", digest)
        self.assertEqual((code, out["code"]), (2, "bundle.changed"))

    def test_freeze_refuses_code_outside_the_bundle(self):
        code, out = self.h.cli("freeze")
        self.assertEqual((code, out["code"]), (2, "bundle.path_outside"))


if __name__ == "__main__":
    unittest.main()
