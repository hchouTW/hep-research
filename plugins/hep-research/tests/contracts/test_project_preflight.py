"""contracts/project.py --preflight: the bound profiles' index.md, printed for the agent to read before it answers
(registry rule CTX-READ-BOUND-PROFILE, evals/behavior/invariants.json)."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.project import main as project_main  # noqa: E402

FIXTURES = ROOT / "contracts" / "fixtures"
INDEX = ROOT / "profiles" / "experiments" / "synthetic-collider" / "index.md"  # present without the AMS profile


def profile_version() -> str:
    reg = json.loads((ROOT / "profiles" / "registry.json").read_text())
    return next(p["version"] for p in reg["profiles"] if p["id"] == "experiment:synthetic-collider")


def run(*args) -> tuple[int, dict]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = project_main([str(a) for a in args])
    return rc, json.loads(buf.getvalue())


class Preflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, cfg: dict) -> Path:
        (self.d / "hep-research.project.json").write_text(json.dumps(cfg), encoding="utf-8")
        return self.d

    def bound(self, version=None) -> Path:
        return self.write({"schema_version": "1.2.0", "plugin_version": ">=0.1",
                           "experiments": [{"profile": "experiment:synthetic-collider", "version": version or profile_version()}]})

    def test_prints_the_bound_profile_index(self):
        rc, out = run(self.bound(), "--preflight")
        self.assertEqual(rc, 0)
        [entry] = out["preflight"]
        raw = INDEX.read_bytes()
        self.assertEqual(entry["id"], "experiment:synthetic-collider")
        self.assertEqual(entry["status"], "ok")
        self.assertEqual(entry["index_path"], "profiles/experiments/synthetic-collider/index.md")
        self.assertEqual(entry["index_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(entry["index_text"], raw.decode("utf-8"))

    def test_flag_position_does_not_matter_and_output_is_unchanged_without_it(self):
        d = self.bound()
        self.assertEqual(run("--preflight", d)[1]["preflight"], run(d, "--preflight")[1]["preflight"])
        rc, out = run(d)
        self.assertEqual(rc, 0)
        self.assertNotIn("preflight", out)

    def test_no_binding_prints_an_empty_list(self):
        rc, out = run(self.write({"schema_version": "1.2.0", "plugin_version": ">=0.1"}), "--preflight")
        self.assertEqual((rc, out["preflight"]), (0, []))

    def test_invalid_config_prints_nothing_and_exits_1(self):
        rc, out = run(self.bound(version="0.0.1"), "--preflight")
        self.assertEqual(rc, 1)
        self.assertEqual(out["preflight"], [])

    def test_unreadable_path_exits_2(self):
        rc, out = run(self.d / "missing", "--preflight")
        self.assertEqual(rc, 2)
        self.assertFalse(out["ok"])

    def test_local_profile_is_not_printed(self):
        reg = FIXTURES / "registry" / "valid" / "profiles" / "registry.json"
        proj = self.d / "local_profile"
        shutil.copytree(FIXTURES / "projects" / "local_profile", proj)   # local profiles may not live in the plugin
        rc, out = run(proj, "--registry", reg, "--preflight")
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["preflight"], [{"id": "experiment:fixture-local", "status": "not-in-plugin"}])


if __name__ == "__main__":
    unittest.main()
