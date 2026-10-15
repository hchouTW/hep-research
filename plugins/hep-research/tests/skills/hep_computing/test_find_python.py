"""find_python.py (SYMPY S01/S02): candidate order, rejection reasons, no scanning, exit codes and JSON status."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
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
        fake_python(self.dir, "python3", json.dumps({"version": [3, 13, 0], "executable": "x", "modules": {},
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
        self.assertIn("3.9.6 < 3.13", reasons["HEP_RESEARCH_PYTHON"])
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


def fake_version(folder: Path, name: str, version: list[int], missing=()) -> Path:
    """A fake interpreter of the given version that has `json` (and lacks `missing`)."""
    return fake_python(folder, name, json.dumps({"version": version, "executable": name, "modules": {"json": "x"},
                                                 "missing": list(missing)}))


def load_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("find_python", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(os.name == "posix", "fake interpreters are shell scripts")
class PythonFloorTests(unittest.TestCase):
    """Python 3.13 is the supported minimum: 3.11 and 3.12 are rejected with their reason from every candidate source,
    an eligible 3.13 is selected in the documented order, all-old candidates fail, and a lower --min-python cannot
    lower the floor (a stricter one is kept)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_minimum_is_313(self):
        self.assertEqual(load_module().MIN_PYTHON, "3.13")
        proc, out = run("--require", "json", path_dir=self.dir)
        self.assertEqual(out["min_python"], "3.13")

    def test_311_and_312_rejected_from_every_source(self):
        p311 = fake_version(self.dir, "py311", [3, 11, 9])
        p312 = fake_version(self.dir, "py312", [3, 12, 7])
        path_dir = self.dir / "bin"
        path_dir.mkdir()
        fake_version(path_dir, "python3", [3, 12, 3])
        proc, out = run("--require", "json", "--python", str(p311), env_extra={"HEP_RESEARCH_PYTHON": str(p312)},
                        path_dir=path_dir)
        reasons = {c["source"]: c["reason"] for c in out["candidates"]}
        self.assertEqual(reasons["--python"], "Python 3.11.9 < 3.13")
        self.assertEqual(reasons["HEP_RESEARCH_PYTHON"], "Python 3.12.7 < 3.13")
        self.assertEqual(out["source"], "caller", "the 3.13 caller is the first eligible candidate")
        self.assertNotIn("PATH", reasons, "PATH is not probed once a candidate is accepted")

    def test_313_accepted_in_documented_order_after_an_old_candidate(self):
        old = fake_version(self.dir, "py312", [3, 12, 7])
        new = fake_version(self.dir, "py313", [3, 13, 1])
        proc, out = run("--require", "json", "--python", str(old), env_extra={"HEP_RESEARCH_PYTHON": str(new)},
                        path_dir=self.dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((out["source"], out["python_version"]), ("HEP_RESEARCH_PYTHON", "3.13.1"))
        self.assertEqual(out["candidates"][0]["reason"], "Python 3.12.7 < 3.13")

    def test_path_candidate_accepted_when_everything_before_it_is_old(self):
        mod = load_module()
        p311 = fake_version(self.dir, "py311", [3, 11, 9])
        p313 = fake_version(self.dir, "python3", [3, 13, 0])
        with unittest.mock.patch.object(mod, "candidates",
                                        lambda explicit: [("--python", str(p311)), ("caller", str(p311)), ("PATH", str(p313))]):
            out = mod.find(["json"], explicit=str(p311))
        self.assertEqual((out["status"], out["source"]), ("found", "PATH"))

    def test_all_old_candidates_fail_with_the_minimum_in_the_hint(self):
        mod = load_module()
        p311 = fake_version(self.dir, "py311", [3, 11, 9])
        p312 = fake_version(self.dir, "py312", [3, 12, 7])
        with unittest.mock.patch.object(mod, "candidates",
                                        lambda explicit: [("--python", str(p311)), (mod.ENV_VAR, str(p312)),
                                                          ("caller", str(p311)), ("PATH", str(p312))]):
            out = mod.find(["json"], explicit=str(p311))
        self.assertEqual(out["status"], "failed")
        self.assertIsNone(out["python"])
        self.assertEqual([c["reason"] for c in out["candidates"]],
                         ["Python 3.11.9 < 3.13", "Python 3.12.7 < 3.13", "duplicate of --python", "duplicate of HEP_RESEARCH_PYTHON"])
        self.assertIn("Python >= 3.13", out["hint"])

    def test_missing_package_still_reported_on_an_accepted_version(self):
        p313 = fake_version(self.dir, "py313", [3, 13, 1], missing=[NOT_INSTALLED])
        proc, out = run("--require", NOT_INSTALLED, "--python", str(p313), path_dir=self.dir)
        self.assertEqual(out["candidates"][0]["reason"], f"{NOT_INSTALLED} missing")

    def test_lower_minimum_is_bad_usage(self):
        proc, out = run("--require", "json", "--min-python", "3.12", path_dir=self.dir)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("3.13", proc.stderr)
        self.assertIsNone(out)
        with self.assertRaises(ValueError):
            load_module().find(["json"], min_python="3.12")

    def test_stricter_minimum_is_kept(self):
        p314 = fake_version(self.dir, "py314", [3, 14, 0])
        proc, out = run("--require", "json", "--min-python", "3.14", "--python", str(p314), path_dir=self.dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((out["min_python"], out["python_version"]), ("3.14", "3.14.0"))
        proc, out = run("--require", "json", "--min-python", "3.14", path_dir=self.dir)
        if sys.version_info[:2] < (3, 14):
            self.assertEqual(out["candidates"][0]["reason"], f"Python {'.'.join(map(str, sys.version_info[:3]))} < 3.14")


if __name__ == "__main__":
    unittest.main()
