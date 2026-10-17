"""tracker_resolution.py (D14): exact least-squares momentum resolution for given layer positions against the
Gluckstern approximation, the PDG multiple-scattering term, the MDR, the impact-parameter form and a requirement scan.
Oracles: exact over Gluckstern variance ratios 0.900, 0.967 and 0.998 at N = 4, 10 and 50; the exact N = 3 coefficient
8 sqrt(3/2); the Gluckstern term equals toy_spectrometer.py's intrinsic slope for the same layers (D7); the PDG
scattering term over the Highland form equals 0.016 / 0.0136 (the stated conversion). Inputs are SYNTHETIC."""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills" / "hep-detector" / "scripts"
SCRIPT = SCRIPTS / "tracker_resolution.py"
TOY_CONFIG = PLUGIN / "skills" / "hep-detector" / "assets" / "toy-spectrometer.fictional.json"


def run(script, *args):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout), p.stderr


def equal(n, length=1.0):
    return [length * i / (n - 1) for i in range(n)]


BASE = ["--point-resolution-um", "10", "--field-tesla", "1.0", "--x-over-x0", "0.05", "--charge", "1", "--beta", "1"]


class ExactVersusGluckstern(unittest.TestCase):
    def test_variance_ratios(self):
        for n, ratio in ((4, 0.900), (10, 0.967), (50, 0.998)):
            with self.subTest(N=n):
                code, out, err = run(SCRIPT, "momentum", "--positions-m", *equal(n), *BASE, "--pt", "10")
                self.assertEqual(code, 0, err)
                # the card quotes three decimals; the exact N = 10 ratio is 0.96648 (it rounds to 0.966, the card says 0.967)
                self.assertAlmostEqual(out["intrinsic"]["exact_over_gluckstern_variance"], ratio, delta=1e-3)
                if n == 4:
                    self.assertAlmostEqual(out["intrinsic"]["exact_over_gluckstern_variance"], 0.9, delta=1e-12)

    def test_three_point_coefficient(self):
        code, out, _ = run(SCRIPT, "momentum", "--positions-m", 0, 0.5, 1.0, *BASE, "--pt", "10")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["intrinsic"]["exact_coefficient"], 8 * math.sqrt(1.5), delta=1e-9)
        self.assertAlmostEqual(out["intrinsic"]["gluckstern_coefficient"], math.sqrt(720 / 7), delta=1e-9)

    def test_resolution_scales_with_pt_and_mdr(self):
        code, out, _ = run(SCRIPT, "momentum", "--positions-m", *equal(10), *BASE, "--pt", "10", "100")
        self.assertEqual(code, 0)
        r10, r100 = (row["intrinsic_relative"] for row in out["points"])
        self.assertAlmostEqual(r100 / r10, 10.0, delta=1e-9)
        mdr = out["mdr_intrinsic_gev"]
        self.assertAlmostEqual(mdr * out["intrinsic"]["sigma_curvature_per_m"] / (0.299792458 * 1.0), 1.0, delta=1e-12)
        ms = out["points"][0]["scattering_relative"]
        self.assertAlmostEqual(ms, 0.016 * math.sqrt(0.05) / (0.299792458 * 1.0 * 1.0), delta=1e-12)
        self.assertAlmostEqual(out["points"][0]["total_relative"], math.hypot(ms, r10), delta=1e-12)


class AgreementWithToySpectrometer(unittest.TestCase):
    def test_gluckstern_term_and_scattering_conversion(self):
        cfg = json.loads(TOY_CONFIG.read_text(encoding="utf-8"))
        code, toy, err = run(SCRIPTS / "toy_spectrometer.py", "resolution", TOY_CONFIG, "--species", "p",
                             "--rigidity", "10")
        self.assertEqual(code, 0, err)
        era = toy["eras"][0] if "eras" in toy else toy["model"]
        measuring = [layer for layer in cfg["layers"] if layer["measuring"]]
        z = [layer["z_m"] for layer in measuring]
        x0 = sum(layer["grammage_g_cm2"] / layer["radiation_length_g_cm2"] for layer in cfg["layers"])
        code, out, err = run(SCRIPT, "momentum", "--positions-m", *z, "--point-resolution-um", "10",
                             "--field-tesla", cfg["field"]["field_tesla"], "--lever-arm-m", cfg["field"]["lever_arm_m"],
                             "--x-over-x0", x0, "--charge", "1", "--beta", "1", "--pt", "10")
        self.assertEqual(code, 0, err)
        self.assertAlmostEqual(out["intrinsic"]["gluckstern_slope_per_gev"] / era["a_per_gv"], 1.0, delta=1e-12)
        self.assertAlmostEqual(out["points"][0]["scattering_relative"] / era["b"], 0.016 / 0.0136, delta=1e-12)


class ImpactAndScan(unittest.TestCase):
    def test_impact_form(self):
        code, out, _ = run(SCRIPT, "impact", "--a-um", "10", "--b-um-gev", "30", "--p-gev", "1", "2",
                           "--theta-deg", "90")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["points"][0]["sigma_d0_um"], math.hypot(10, 30), delta=1e-9)
        self.assertAlmostEqual(out["points"][1]["sigma_d0_um"], math.hypot(10, 15), delta=1e-9)

    def test_scan_meets_requirement_and_is_monotonic(self):
        code, out, _ = run(SCRIPT, "scan", "--n-layers", "4", "8", "--lever-arm-m", "0.5", "1.0", "1.5",
                           "--point-resolution-um", "10", "--field-tesla", "0.5", "--x-over-x0-per-layer", "0.01",
                           "--charge", "1", "--beta", "1", "--pt", "100", "--max-relative-resolution", "0.1")
        self.assertEqual(code, 0)
        for row in out["grid"]:
            self.assertEqual(row["meets"], row["total_relative"] <= 0.1)
        by = {(r["n_layers"], r["lever_arm_m"]): r["total_relative"] for r in out["grid"]}
        self.assertLess(by[(8, 1.5)], by[(8, 1.0)])
        self.assertLess(by[(8, 1.0)], by[(4, 1.0)])
        self.assertIn("minimal_lever_arm_m", out)


class Contract(unittest.TestCase):
    def test_missing_inputs_refused(self):
        for args in (("momentum", "--positions-m", "0", "0.5", "1", "--field-tesla", "1", "--pt", "1"),
                     ("momentum", "--positions-m", "0", "1", *BASE, "--pt", "1"),
                     ("impact", "--a-um", "10", "--p-gev", "1", "--theta-deg", "90")):
            with self.subTest(args=args):
                code, out, _ = run(SCRIPT, *args)
                self.assertEqual(code, 2)
                self.assertEqual(out["status"], "rejected")

    def test_status_and_defaults(self):
        code, out, _ = run(SCRIPT, "momentum", "--positions-m", *equal(5), *BASE, "--pt", "10")
        self.assertEqual((out["status"], out["status_label"]), ("ok", "unvalidated"))
        self.assertIn("status", out["defaults_used"])
        self.assertIn("inputs", out)


if __name__ == "__main__":
    unittest.main()
