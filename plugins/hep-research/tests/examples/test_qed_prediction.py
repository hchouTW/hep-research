"""Path C (journey J4) regression tests: standalone theory with theory:qed-benchmark and zero experiment resources."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "qed-prediction" / "run.py"

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    import sympy  # noqa: F401
    import matplotlib  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


@unittest.skipUnless(HAVE_DEPS, "numpy, scipy, sympy and matplotlib are required (D5 environment)")
class PathCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name)
        # a fresh interpreter, so the record of opened files covers the whole run
        cls.proc = subprocess.run([sys.executable, str(SCRIPT), "--out", str(cls.out)], capture_output=True, text=True, timeout=1200)
        cls.r = json.loads((cls.out / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_passes(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stdout + self.proc.stderr)
        self.assertTrue(all(self.r["pass"].values()))

    def test_zero_experiment_resources(self):
        self.assertTrue(self.r["profile_files_read"])
        self.assertTrue(all(p.startswith("profiles/theory/qed-benchmark/") for p in self.r["profile_files_read"]), self.r["profile_files_read"])
        for name in ("theory_spec", "prediction"):
            doc = json.loads((self.out / "artifacts" / f"{name}.json").read_text())
            self.assertEqual(doc["bindings"]["experiments"], [])
        spec = json.loads((self.out / "artifacts" / "theory_spec.json").read_text())["extension"]
        for field in ("blinding", "detector", "luminosity", "data"):
            self.assertNotIn(field, spec)
            self.assertIn(field, " ".join(spec["inapplicable"]))

    def test_status_and_reference(self):
        spec = json.loads((self.out / "artifacts" / "theory_spec.json").read_text())["extension"]
        self.assertEqual(spec["derivation_status"], "analytic-derivation")
        self.assertIn("51.2", spec["references_read"][0]["location"])
        self.assertTrue(any("formal proof" in c for c in spec["checks_not_run"]))
        self.assertTrue(all(c["result"] == "pass" for c in spec["checks_run"]))

    def test_prediction_units_and_uncertainties(self):
        pred = json.loads((self.out / "artifacts" / "prediction.json").read_text())["extension"]
        self.assertEqual(pred["values"]["unit"], "pb")
        kinds = {u["kind"] for u in pred["values"]["uncertainties"]} | {u["kind"] for u in pred["uncertainties"]}
        self.assertEqual(kinds, {"parametric", "numerical", "truncation"})
        self.assertFalse(any(u.get("gaussian") for u in pred["uncertainties"]))
        self.assertAlmostEqual(self.r["prediction"]["sigma_total_pb"], 868.0, places=9)


    def test_files_read_does_not_depend_on_the_bytecode_cache(self):
        """An import opens the .py source on a cold cache and the cached .pyc on a warm one; the record of files read
        must be the same either way (FULLTEST-E3 L04)."""
        cold, warm = cold_and_warm(SCRIPT, "profile_files_read")
        self.assertEqual(cold, warm)
        self.assertIn("profiles/theory/qed-benchmark/scripts/derive.py", cold)

    @unittest.skipUnless((SCRIPT.parent / "output" / "results.json").is_file(), "no committed output in this copy")
    def test_files_read_match_the_committed_output(self):
        committed = json.loads((SCRIPT.parent / "output" / "results.json").read_text())["profile_files_read"]
        self.assertEqual(self.r["profile_files_read"], committed)


class MissingSympyTests(unittest.TestCase):
    """Without SymPy, run.py explains itself (JSON failed status, exit 2, no traceback) and --help still works."""

    def run_without_sympy(self, *args):
        code = ("import runpy, sys; sys.modules['sympy'] = None; "
                f"sys.argv = [{str(SCRIPT)!r}, *{list(args)!r}]; runpy.run_path(sys.argv[0], run_name='__main__')")
        return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300)

    def test_run_reports_failed_status(self):
        proc = self.run_without_sympy("--out", tempfile.gettempdir())
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["status"], "failed")
        self.assertIn("sympy", out["missing"])

    def test_help_works(self):
        proc = self.run_without_sympy("--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Usage", proc.stdout)


def cold_and_warm(script, key):
    """Run `script` twice against a fresh bytecode cache: cold (sources compiled), then warm (cached .pyc read). The
    cache sits inside the plugin's profiles/ folder, where a cold in-tree cache writes its temporary .pyc.<id> files
    (E4); outside the plugin those writes were invisible to the record."""
    got = []
    with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory(dir=PLUGIN / "profiles", prefix=".pyc-test-") as cache:
        env = dict(os.environ, PYTHONPYCACHEPREFIX=cache)
        for run in ("cold", "warm"):
            p = subprocess.run([sys.executable, str(script), "--out", str(Path(td) / run)], capture_output=True, text=True, env=env, timeout=1200)
            if p.returncode:
                raise AssertionError(p.stdout[-1000:] + p.stderr[-2000:])
            got.append(json.loads((Path(td) / run / "results.json").read_text())[key])
    return got


if __name__ == "__main__":
    unittest.main()
