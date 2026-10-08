"""B10: every workflow command in references/batch-scheduling.md runs against the fake scheduler, in order."""
import re
import shlex
import unittest

from tests.adapters.batch_harness import ROOT, Harness

REF = ROOT / "skills" / "hep-computing" / "references" / "batch-scheduling.md"
EXPECTED_EXIT = {"check-config": 0, "plan": 0, "freeze": 0, "submit": 0, "status": 1, "watch": 1, "resubmit": 0, "reset": 0, "merge": 0, "report": 0}


def workflow_commands():
    text = REF.read_text()
    block = text.split("## The workflow", 1)[1].split("```", 2)[1]
    joined = re.sub(r"\\\n\s*", " ", block)
    return [shlex.split(l.split("#")[0])[2:] for l in joined.splitlines() if l.startswith("python3 batch_campaign.py")]


class ReferenceWorkflowTests(unittest.TestCase):
    def test_documented_workflow_runs_on_the_fake_scheduler(self):
        cmds = workflow_commands()
        self.assertEqual([c[0] for c in cmds], ["check-config", "plan", "freeze", "submit", "submit", "status", "submit", "watch",
                                                 "resubmit", "reset", "merge", "report"])
        h = Harness("slurm", extra={"monitor": {"poll_interval_s": 60, "max_polls": 2}})
        self.addCleanup(h.cleanup)
        seen_status = False
        for c in cmds:
            args = [a for a in c]
            i = args.index("--config")
            del args[i:i + 2]
            if args[0] == "plan":  # same flags, smaller job so the fake scheduler stays fast; the worker in its own folder
                (h.dir / "worker").mkdir()
                (h.dir / "worker" / "toy.py").write_text((h.dir / "worker.py").read_text())
                cmd = h.cmd.replace(str(h.dir / "worker.py"), str(h.dir / "worker" / "toy.py"))
                args = ["plan", "--job", "toys", "--items", "10", "--chunk-size", "1", "--seed", "42", "--cmd", cmd]
            if args[0] == "freeze":
                args[args.index("--worker-root") + 1] = str(h.dir / "worker")
            if args[0] == "reset":
                args[args.index("--chunks") + 1] = "c0004"
            if args[0] == "report":
                args[args.index("--out") + 1] = str(h.dir / "artifacts" / "toys-run.json")
            code, rep = h.cli(*args, sleep=lambda s: None)
            expected = EXPECTED_EXIT[args[0]]
            if args[0] == "status":
                expected, seen_status = (1, True)  # after the pilot, nine chunks are still planned
            if args[0] == "watch":
                expected = 0  # everything finished at submit time on the fake scheduler
            with self.subTest(command=" ".join(args[:3])):
                self.assertEqual(code, expected, rep)
        self.assertTrue(seen_status)
        self.assertEqual(sum(1 for c in h.calls() if c["tool"] == "sbatch" and "--version" not in c["argv"]), 2)  # resubmit was a dry run


if __name__ == "__main__":
    unittest.main()
