"""Batch-adapter regressions from the hep-computing remediation (CMP-22..24), against the fake schedulers.

CMP-22: slurm_backend built --array=0-(n-1) for any n; a cluster's MaxArraySize was never checked.
CMP-23: a job whose allocation row is COMPLETED 0:0 but whose DerivedExitCode is nonzero (a failed srun step) counted
        as done; DerivedExitCode was not even read.
CMP-24: htcondor_backend listed event 002 (error in executable) but left the job queued and fell back to condor_q.
Each test fails on c1d375c. All inputs SYNTHETIC.
"""
import unittest

from tests.adapters.batch_harness import Harness
import slurm_backend as sb  # noqa: E402  (batch_harness put the adapter on sys.path)


class SlurmMaxArraySizeTests(unittest.TestCase):
    """CMP-22."""

    def test_array_beyond_max_array_size_is_refused_before_sbatch(self):
        h = Harness("slurm", items=2000, chunk=1)
        self.addCleanup(h.cleanup)
        h.plan()
        h.set_faults({"_global": {"scontrol": "1001"}})
        code, rep = h.cli("submit", "--submit")
        self.assertNotEqual(code, 0, rep)
        self.assertIn("slurm.array.too_large", str(rep))
        self.assertEqual([c["tool"] for c in h.calls()], ["scontrol"], "no sbatch call after the refusal")
        sub = h.state()["submissions"][0]
        self.assertEqual(sub["status"], "not-submitted")

    def test_array_below_the_limit_and_unreadable_limit_submit(self):
        for mode in ("1001", "unavailable"):
            with self.subTest(scontrol=mode):
                h = Harness("slurm", items=4, chunk=1)
                self.addCleanup(h.cleanup)
                h.plan()
                h.set_faults({"_global": {"scontrol": mode}})
                self.assertEqual(h.cli("submit", "--submit")[0], 0)
                self.assertIn("sbatch", [c["tool"] for c in h.calls()])

    def test_limit_parsing(self):
        self.assertEqual(sb.MAX_ARRAY.search("A = 1\nMaxArraySize            = 20000\n").group(1), "20000")


class SlurmDerivedExitCodeTests(unittest.TestCase):
    """CMP-23."""

    def test_completed_with_nonzero_derived_exit_code_fails(self):
        h = Harness("slurm", items=2, chunk=1)
        self.addCleanup(h.cleanup)
        h.plan()
        h.set_faults({"c0000": [{"kind": "native", "state": "COMPLETED", "exit": "0:0", "derived": "4:0"}]})
        h.cli("submit", "--submit")
        code, rep = h.cli("status")
        c = rep["chunks"]["c0000"]
        self.assertEqual(c["status"], "failed", c)
        self.assertEqual(rep["chunks"]["c0001"]["status"], "done")
        errors = h.state()["chunks"]["c0000"]["errors"]
        self.assertEqual(len(errors), 1)
        self.assertIn("derived-exit", errors[0])
        self.assertIn("exit=4", errors[0])
        self.assertIn("DerivedExitCode", sb.SACCT_FIELDS)


if __name__ == "__main__":
    unittest.main()
