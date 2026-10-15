"""theory:cr-secondary-ratio scripts without their packages: a JSON failed status and a documented exit code, no
traceback; --help still works."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def run_without(modules, script, *args):
    """Run a script as __main__ in a fresh interpreter where importing each of `modules` raises ImportError."""
    block = "; ".join(f"sys.modules[{m!r}] = None" for m in modules)
    path = str(SCRIPTS / script)
    code = (f"import runpy, sys; {block}; "
            f"sys.argv = [{path!r}, *{list(args)!r}]; runpy.run_path(sys.argv[0], run_name='__main__')")
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)


class MissingDependencyTests(unittest.TestCase):
    def test_derive_without_sympy_reports_failed(self):
        proc = run_without(["sympy"], "derive.py")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["status"], "failed")
        self.assertIn("sympy", out["error"])

    def test_derive_help_without_sympy(self):
        proc = run_without(["sympy"], "derive.py", "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Usage", proc.stdout)

    def test_predict_without_scipy_exits_3(self):
        proc = run_without(["scipy"], "predict.py")
        self.assertEqual(proc.returncode, 3, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
