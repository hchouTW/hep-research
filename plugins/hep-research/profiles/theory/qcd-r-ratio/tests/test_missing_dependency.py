"""theory:qcd-r-ratio derive.py without SymPy: a JSON failed status and exit 2, no traceback; --help still works."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "derive.py"


def run_without_sympy(*args):
    """Run derive.py as __main__ in a fresh interpreter where 'import sympy' raises ModuleNotFoundError."""
    code = ("import runpy, sys; sys.modules['sympy'] = None; "
            f"sys.argv = [{str(SCRIPT)!r}, *{list(args)!r}]; runpy.run_path(sys.argv[0], run_name='__main__')")
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)


class MissingSympyTests(unittest.TestCase):
    def test_run_reports_failed_status(self):
        proc = run_without_sympy()
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["status"], "failed")
        self.assertIn("sympy", out["error"])
        self.assertIn("find_python.py", out["hint"])

    def test_help_works(self):
        proc = run_without_sympy("--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Usage", proc.stdout)


if __name__ == "__main__":
    unittest.main()
