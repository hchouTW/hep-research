"""Tests for skills/hep-computing/scripts/local_partition.py: CLI plan/run/status/reset/merge with a command worker."""
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "skills" / "hep-computing" / "scripts"
sys.path.insert(0, str(ROOT))
import local_partition as lp  # noqa: E402

WORKER = """
import json, sys, os
a = dict(zip(sys.argv[1::2], sys.argv[2::2]))
if os.path.exists(a["--fail-flag"]) and a["--id"] == "c0001":
    sys.stderr.write("disk full (synthetic)"); sys.exit(3)
start, stop = int(a["--start"]), int(a["--stop"])
json.dump({"n": stop - start, "sum": sum(range(start, stop))}, open(a["--out"], "w"))
"""


class LocalPartitionCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name) / "work dir"
        self.d.mkdir()
        (self.d / "worker.py").write_text(WORKER)
        self.flag = self.d / "fail.flag"
        self.flag.write_text("x")
        q = shlex.quote
        self.cmd = f"{q(sys.executable)} {q(str(self.d / 'worker.py'))} --start {{start}} --stop {{stop}} --out {{out}} --id {{id}} --fail-flag {q(str(self.flag))}"

    def cli(self, *a):
        p = subprocess.run([sys.executable, str(ROOT / "local_partition.py"), *a], capture_output=True, text=True, timeout=600)
        return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)

    def test_full_cycle(self):
        man, st = self.d / "manifest.json", self.d / "state"
        self.assertEqual(self.cli("plan", "--job", "t", "--items", "10", "--chunk-size", "4", "--seed", "1", "--out", str(man))[0], 0)
        code, out = self.cli("run", "--manifest", str(man), "--state", str(st), "--cmd", self.cmd)
        self.assertEqual(code, 1)
        self.assertEqual(out["not_done"], ["c0001"])
        self.assertEqual(out["max_attempts"], 1)
        self.assertEqual(self.cli("merge", "--manifest", str(man), "--state", str(st))[0], 1)
        cfg = self.d / "cfg.json"
        cfg.write_text(json.dumps({"max_attempts": 5}))
        code, out = self.cli("run", "--manifest", str(man), "--state", str(st), "--cmd", self.cmd, "--config", str(cfg))
        self.assertEqual(out["chunks"]["c0001"]["status"], "stopped-repeated-failure")
        self.assertEqual(out["chunks"]["c0001"]["attempts"], 2)
        self.assertEqual(sorted(out["skipped_done"]), ["c0000", "c0002"])
        self.flag.unlink()
        self.assertEqual(self.cli("reset", "--manifest", str(man), "--state", str(st), "--chunks", "c0001", "--reason", "freed disk")[0], 0)
        self.assertEqual(self.cli("run", "--manifest", str(man), "--state", str(st), "--cmd", self.cmd)[0], 0)
        code, out = self.cli("merge", "--manifest", str(man), "--state", str(st))
        self.assertEqual(code, 0)
        self.assertEqual(out["merged"], {"n": 10, "sum": 45})

    def test_state_from_another_manifest_refused(self):
        st = self.d / "state"
        lp.run(lp.make_manifest("a", 4, 2, 1), st, lambda c: {"n": 1})
        with self.assertRaises(ValueError):
            lp.run(lp.make_manifest("b", 4, 2, 1), st, lambda c: {"n": 1})

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            lp.make_manifest("x", 0, 1, 1)
        with self.assertRaises(ValueError):
            lp.run(lp.make_manifest("x", 2, 1, 1), self.d / "s", lambda c: 1, {"max_attempts": 0})
        self.assertEqual(self.cli("status", "--manifest", "/nonexistent", "--state", str(self.d))[0], 2)

    def raw_cli(self, *a):
        return subprocess.run([sys.executable, str(ROOT / "local_partition.py"), *a], capture_output=True, text=True, timeout=600)

    def test_bad_manifest_refused_by_every_subcommand_without_touching_state(self):
        """CMP-03: status, merge and reset validated nothing; reset wrote state.json and then crashed."""
        man, st = self.d / "manifest.json", self.d / "state"
        self.assertEqual(self.cli("plan", "--job", "t", "--items", "4", "--chunk-size", "2", "--seed", "1", "--out", str(man))[0], 0)
        self.assertEqual(self.cli("run", "--manifest", str(man), "--state", str(st), "--cmd", self.cmd)[0], 1)
        before = (st / "state.json").read_bytes()
        good = json.loads(man.read_text())
        bad_list = self.d / "list.json"
        bad_list.write_text(json.dumps(good["chunks"]))
        no_chunks = self.d / "nochunks.json"
        no_chunks.write_text(json.dumps({k: v for k, v in good.items() if k != "chunks"}))
        for bad in (bad_list, no_chunks):
            for sub in (["status"], ["merge"], ["reset", "--chunks", "c0001", "--reason", "x"]):
                p = self.raw_cli(sub[0], "--manifest", str(bad), "--state", str(st), *sub[1:])
                self.assertEqual(p.returncode, 2, (bad.name, sub, p.stdout, p.stderr))
                self.assertNotIn("Traceback", p.stderr)
                doc = json.loads(p.stdout)
                self.assertIsInstance(doc.get("error"), str)
                self.assertNotEqual(doc["error"], "'chunks'")
                self.assertEqual((st / "state.json").read_bytes(), before)

    def test_reset_refuses_a_state_of_another_manifest(self):
        man, other, st = self.d / "m.json", self.d / "o.json", self.d / "state"
        self.cli("plan", "--job", "t", "--items", "4", "--chunk-size", "2", "--seed", "1", "--out", str(man))
        self.cli("plan", "--job", "u", "--items", "4", "--chunk-size", "2", "--seed", "1", "--out", str(other))
        self.cli("run", "--manifest", str(man), "--state", str(st), "--cmd", self.cmd)
        before = (st / "state.json").read_bytes()
        code, out = self.cli("reset", "--manifest", str(other), "--state", str(st), "--chunks", "c0001", "--reason", "x")
        self.assertEqual(code, 2)
        self.assertIn("different manifest", out["error"])
        self.assertEqual((st / "state.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
