"""B12: job logs are outputs for the blinding audit; shipped batch configs hold no site facts; no credentials."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.adapters.batch_harness import ADAPTER, ROOT, Harness

AUDIT = ROOT / "skills" / "hep-computing" / "scripts" / "audit_blinded_outputs.py"


class BlindedLogTests(unittest.TestCase):
    def test_sealed_value_in_job_stdout_is_found(self):
        h = Harness("slurm", items=2, chunk=1, worker_print="1234.5678")
        self.addCleanup(h.cleanup)
        h.plan()
        h.cli("submit", "--submit")
        self.assertEqual(h.cli("status")[0], 0)
        sealed = h.dir / "private" / "sealed.json"
        sealed.parent.mkdir()
        sealed.write_text(json.dumps({"sealed": [1234.5678], "region": {"low": 0, "high": 1}}))
        report = h.dir / "private" / "report.json"
        p = subprocess.run([sys.executable, str(AUDIT), "scan", "--sealed", str(sealed), "--report", str(report),
                            str(h.cdir / "submissions")], capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertNotIn(".stdout.log", p.stdout)  # the agent-visible status names no file (N09)
        self.assertNotIn("1234.5678", p.stdout)
        self.assertIn(".stdout.log", report.read_text())


    def test_job_files_and_scheduler_logs_are_read_as_text(self):
        from core.blinding import blinding as bl
        with tempfile.TemporaryDirectory() as td:
            for name in ("slurm-1_2.out", "slurm-1_2.err", "job.sbatch", "job.sub", "wrap.sh"):
                (Path(td) / name).write_text("value 1234.5678\n")
            rep = bl.scan_paths([td], [1234.5678])
            self.assertEqual(rep["unscanned"], [])
            self.assertEqual(len(rep["leaks"]), 5)


class PackagingTests(unittest.TestCase):
    def test_planted_account_fails_the_packaging_check(self):
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "plugin"
            # copy what the scanner sees in the checkout (git-listed files), not ignored local files such as a venv
            listed = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."], cwd=ROOT,
                                    capture_output=True, text=True, timeout=600).stdout.split("\0")
            if not any(listed):
                shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for rel in filter(None, listed):
                if (ROOT / rel).is_file():
                    (copy / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(ROOT / rel, copy / rel)
            run = lambda: subprocess.run([sys.executable, str(copy / "tools" / "check_packaging.py"), "--root", str(copy)],
                                         capture_output=True, text=True, timeout=600)
            first = run()
            self.assertEqual(first.returncode, 0, first.stdout[-2000:])
            ex = copy / "adapters" / "batch-schedulers" / "assets" / "batch-config.example.json"
            cfg = json.loads(ex.read_text())
            cfg["slurm"]["account"] = "hepgrp42"
            ex.write_text(json.dumps(cfg))
            p = run()
            self.assertEqual(p.returncode, 1)
            findings = json.loads(p.stdout)["findings"]
            self.assertEqual([(f["rule"], f["detail"]) for f in findings], [("batch-site-fact", "account=hepgrp42")])

    def test_adapter_handles_no_credentials(self):
        pattern = re.compile(r"X509_USER_PROXY|BEARER_TOKEN|password|getpass|\.netrc|voms-proxy|kinit", re.I)
        for f in sorted(ADAPTER.rglob("*.py")) + sorted((ROOT / "core" / "partition").rglob("*.py")):
            with self.subTest(file=f.name):
                self.assertIsNone(pattern.search(f.read_text()), f)


if __name__ == "__main__":
    unittest.main()
