"""theory:heliospheric-modulation closed-form benchmark: the hep-measurement force-field script (run as a process)
against the power-law closed forms on synthetic points; the profile never imports or copies the script."""
import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

CFG = predict.load_config(predict.DEFAULT_CONFIG)


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = predict.benchmark(CFG)

    def test_all_checks_pass(self):
        self.assertTrue(all(self.out["checks"].values()), self.out["checks"])
        self.assertEqual(self.out["status"], "synthetic")

    def test_every_point_within_tolerance(self):
        self.assertEqual(self.out["n_points"], 2 * 3 * 3 * 5)
        for row in self.out["points"]:
            with self.subTest(**{k: row[k] for k in ("species", "kind", "x", "phi_gv")}):
                self.assertLessEqual(row["relative_difference"], CFG["relative_tolerance"])
        self.assertEqual(CFG["relative_tolerance"], 1e-10)  # the declared tolerance; not tuned to the result

    def test_stored_benchmark_output_is_current(self):
        stored = json.loads((ROOT / "predictions" / "power-law-benchmark.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["checks"], self.out["checks"])
        self.assertEqual(len(stored["points"]), len(self.out["points"]))
        for s, o in zip(stored["points"], self.out["points"]):
            self.assertEqual((s["species"], s["kind"], s["x"], s["phi_gv"]), (o["species"], o["kind"], o["x"], o["phi_gv"]))
            self.assertAlmostEqual(s["closed_form"], o["closed_form"], delta=1e-12 * o["closed_form"])

    def test_closed_form_detects_a_wrong_shift(self):
        # (|Z|/A) phi used in total kinetic energy (a per-nucleon/total mix-up) moves the He flux far outside tolerance
        right = predict.closed_form("Ek_total", 2.0, 3.7273794, 2, 0.5, 1e4, 2.7)
        wrong = predict.closed_form("Ek_total", 2.0, 3.7273794, 2, 0.5 / 4, 1e4, 2.7)
        self.assertGreater(abs(wrong - right) / right, 0.1)

    def test_breakdown_flag(self):
        self.assertTrue(predict.below_breakdown("Ek_per_nucleon", 0.2, 3.7273794, 2, 4))
        self.assertFalse(predict.below_breakdown("Ek_per_nucleon", 0.4, 3.7273794, 2, 4))
        self.assertTrue(predict.below_breakdown("rigidity", 0.5, 0.938272, 1, 1))
        self.assertIsNone(predict.below_breakdown("Ek_total", 1.0, 11.17, 6, 12))

    def test_point_cli_and_bad_input(self):
        script = ROOT / "scripts" / "predict.py"
        ok = subprocess.run([sys.executable, str(script), "--point", "--kind", "rigidity", "--x", "2", "--mass",
                             "0.938272", "--charge", "1", "--phi", "0.6", "--norm", "1e4", "--index", "2.7"],
                            capture_output=True, text=True, timeout=120)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertLess(json.loads(ok.stdout)["relative_difference"], 1e-10)
        bad = subprocess.run([sys.executable, str(script), "--point", "--x", "2"], capture_output=True, text=True,
                             timeout=120)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(json.loads(bad.stdout)["status"], "failed")

    def test_missing_script_is_exit_3(self):
        saved = predict.FORCE_FIELD
        try:
            predict.FORCE_FIELD = ROOT / "no-such-script.py"
            with self.assertRaises(predict.ScriptError):
                predict.run_force_field("modulate", "Ek_total", 1.0, 0.938272, 1, 0.5, norm=1.0, index=2.7)
        finally:
            predict.FORCE_FIELD = saved

    def test_profile_does_not_import_or_copy_the_force_field(self):
        for py in (ROOT / "scripts").glob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                mods = ([a.name for a in node.names] if isinstance(node, ast.Import)
                        else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                for mod in mods:
                    self.assertFalse(mod.startswith(("skills", "solar_modulation")), f"{py.name} imports {mod}")
            self.assertNotIn("def flux_jacobian", py.read_text(encoding="utf-8"))
        self.assertTrue(predict.FORCE_FIELD.is_file())


if __name__ == "__main__":
    unittest.main()
