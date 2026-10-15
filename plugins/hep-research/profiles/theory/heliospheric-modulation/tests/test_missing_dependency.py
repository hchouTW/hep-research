"""theory:heliospheric-modulation derive.py without SymPy: a JSON failed status and exit 2, no traceback; --help
still works. predict.py and make_artifacts.py need only the standard library."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def run_without(modules, script, *args):
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

    def test_artifacts_need_no_third_party_package(self):
        proc = run_without(["sympy", "numpy", "scipy"], "make_artifacts.py", "--check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
