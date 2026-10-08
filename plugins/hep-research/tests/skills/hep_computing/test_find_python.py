"""find_python.py (SYMPY S01/S02): candidate order, rejection reasons, no scanning, exit codes and JSON status."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-computing" / "scripts" / "find_python.py"
NOT_INSTALLED = "surely_not_installed_pkg_hep"


def fake_python(folder: Path, name: str, stdout: str) -> Path:
    """An executable that ignores its arguments and prints `stdout`, standing in for a Python interpreter."""
    path = folder / name
    path.write_text(f"#!/bin/sh\necho '{stdout}'\n", encoding="utf-8")  # builtin only: PATH may be a bare folder
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def run(*args, env_extra=None, path_dir=None):
    env = {k: v for k, v in os.environ.items() if k != "HEP_RESEARCH_PYTHON"}
    if path_dir is not None:
        env["PATH"] = str(path_dir)
    env.update(env_extra or {})
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=300)
    return proc, json.loads(proc.stdout) if proc.stdout.strip() else None


@unittest.skipUnless(os.name == "posix", "fake interpreters are shell scripts")
class FindPythonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_caller_accepted_with_versions(self):
        proc, out = run("--require", "json", path_dir=self.dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(out["status"], "found")
        self.assertEqual(out["source"], "caller")
        self.assertEqual(out["python_version"], ".".join(map(str, sys.version_info[:3])))
        self.assertIn("json", out["modules"])

    def test_environment_variable_wins_over_caller(self):
        proc, out = run("--require", "json", env_extra={"HEP_RESEARCH_PYTHON": sys.executable}, path_dir=self.dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(out["source"], "HEP_RESEARCH_PYTHON")
        self.assertEqual([c["source"] for c in out["candidates"]], ["HEP_RESEARCH_PYTHON"])

    def test_flag_wins_over_environment_variable(self):
        proc, out = run("--require", "json", "--python", sys.executable,
                        env_extra={"HEP_RESEARCH_PYTHON": "/nonexistent/python"}, path_dir=self.dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(out["source"], "--python")

    def test_missing_module_rejects_every_candidate(self):
        fake_python(self.dir, "python3", json.dumps({"version": [3, 12, 0], "executable": "x", "modules": {},
                                                     "missing": [NOT_INSTALLED]}))
        proc, out = run("--require", NOT_INSTALLED, path_dir=self.dir)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(out["status"], "failed")
        self.assertIsNone(out["python"])
        # only the documented candidates are tried: no conda or venv scanning
        self.assertEqual([c["source"] for c in out["candidates"]], ["caller", "PATH"])
        for c in out["candidates"]:
            self.assertFalse(c["accepted"])
            self.assertIn(f"{NOT_INSTALLED} missing", c["reason"])
        self.assertIn("HEP_RESEARCH_PYTHON", out["hint"])

    def test_unusable_candidates_fall_through(self):
        old = fake_python(self.dir, "old-python", json.dumps({"version": [3, 9, 6], "executable": "x", "modules": {"json": "x"},
                                                              "missing": []}))
        garbage = fake_python(self.dir, "garbage-python", "not json")
        proc, out = run("--require", "json", "--python", "/nonexistent/python",
                        env_extra={"HEP_RESEARCH_PYTHON": str(old)}, path_dir=self.dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(out["source"], "caller")
        reasons = {c["source"]: c["reason"] for c in out["candidates"] if not c["accepted"]}
        self.assertIn("not an executable file", reasons["--python"])
        self.assertIn("3.9.6 < 3.11", reasons["HEP_RESEARCH_PYTHON"])
        proc, out = run("--require", "json", "--python", str(garbage), path_dir=self.dir)
        self.assertIn("probe failed", out["candidates"][0]["reason"])

    def test_same_interpreter_probed_once(self):
        proc, out = run("--require", NOT_INSTALLED, "--python", sys.executable,
                        env_extra={"HEP_RESEARCH_PYTHON": sys.executable}, path_dir=self.dir)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual([c["reason"] for c in out["candidates"][1:]], ["duplicate of --python", "duplicate of --python"])

    def test_help(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("HEP_RESEARCH_PYTHON", proc.stdout)


if __name__ == "__main__":
    unittest.main()
