"""tools/optional_selection.py: the modules each optional CI extra needs, from check-run records (SYNTHETIC records).
A module with a test the required runs skip and the extra unlocks must be selected; verify fails when it is not, and a
selective optional run is refused as evidence."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "tools" / "optional_selection.py"


def record(folder: Path, modules, skipped, extra=None, shard="1/1"):
    folder.mkdir(parents=True, exist_ok=True)
    check = {"name": "unittest", "modules": [{"module": m, "status": "pass", "seconds": 1.0} for m in modules],
             "skipped": skipped, "plan": {"extra": extra, "shard": shard, "modules": sorted(modules)}}
    (folder / "check-run-2026-10-21T000000Z.json").write_text(json.dumps({"checks": [check]}))


def run(*args):
    p = subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, timeout=60)
    return p.returncode, json.loads(p.stdout)


class OptionalSelection(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        mods = ["tests.a.test_x", "tests.a.test_y", "tests.b.test_z"]
        skip_x = "test_fit (tests.a.test_x.Fit.test_fit): pyhf not installed"
        skip_slow = "test_slow (tests.b.test_z.Slow.test_slow): slow: set HEP_SLOW_TESTS=1"
        record(self.d / "req1", mods[:2], [skip_x], shard="1/2")
        record(self.d / "req2", mods[2:], [skip_slow], shard="2/2")
        record(self.d / "opt", mods, [skip_slow])  # pyhf unlocks test_fit; the slow test stays skipped
        self.req = [self.d / "req1", self.d / "req2"]

    def tearDown(self):
        self._t.cleanup()

    def test_generate_selects_the_module_with_the_unlocked_test(self):
        out = self.d / "sel.json"
        code, rep = run("generate", "--required", *self.req, "--optional", f"pyhf={self.d / 'opt'}", "--out", out)
        self.assertEqual(code, 0, rep)
        self.assertEqual(json.loads(out.read_text())["extras"], {"pyhf": ["tests.a.test_x"]})
        code, rep = run("verify", "--required", *self.req, "--optional", f"pyhf={self.d / 'opt'}", "--selection", out)
        self.assertEqual((code, rep["status"]), (0, "ok"), rep)

    def test_verify_fails_when_the_module_is_not_listed(self):
        sel = self.d / "sel.json"
        sel.write_text(json.dumps({"extras": {"pyhf": ["tests.a.test_y"]}}))
        code, rep = run("verify", "--required", *self.req, "--optional", f"pyhf={self.d / 'opt'}", "--selection", sel)
        self.assertEqual(code, 1, rep)
        self.assertIn("tests.a.test_x", rep["unlisted"]["pyhf"])

    def test_a_selective_optional_run_is_not_evidence(self):
        record(self.d / "sel-run", ["tests.a.test_x"], [], extra="pyhf")
        code, rep = run("generate", "--required", *self.req, "--optional", f"pyhf={self.d / 'sel-run'}")
        self.assertEqual(code, 2, rep)
        self.assertIn("full run", rep["error"])


if __name__ == "__main__":
    unittest.main()
