"""F-06: tools report the inputs they used and the defaults they took (inputs, defaults_used); a defaulted detector
parameter, or a defaulted geomagnetic dipole moment, is a warning. Before the fix the defaults were silent."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PID = ROOT / "skills/hep-detector/scripts/pid_separation_power.py"
CHER = ROOT / "skills/hep-detector/scripts/cherenkov_angle.py"
GEO = ROOT / "skills/hep-measurement/scripts/geomagnetic_cutoff.py"


def run(script, *args):
    res = subprocess.run([sys.executable, "-I", str(script), *args], capture_output=True, text=True, timeout=120)
    return res.returncode, (json.loads(res.stdout) if res.stdout.strip().startswith("{") else None), res.stderr


class PidDefaults(unittest.TestCase):
    def test_tof_without_parameters_lists_defaults_used(self):
        code, out, err = run(PID, "--mode", "tof", "--species", "pi", "K")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["defaults_used"], {"path": 1.0, "time_resolution": 60.0, "threshold": 3.0,
                                                "convention": "single", "momentum": 2.0})
        self.assertEqual(out["inputs"]["path"], 1.0)
        self.assertEqual(sum("describes no particular detector" in w for w in out["warnings"]), 2)

    def test_given_parameters_are_not_defaults_and_numbers_are_unchanged(self):
        code, given, _ = run(PID, "--mode", "tof", "--species", "pi", "K", "--momentum", "2", "--path", "1",
                             "--time-resolution", "60", "--threshold", "3", "--convention", "single")
        self.assertEqual(code, 0)
        self.assertEqual(given["defaults_used"], {})
        self.assertEqual(given["warnings"], [])
        _, defaulted, _ = run(PID, "--mode", "tof", "--species", "pi", "K")
        self.assertEqual(given["n_sigma"], defaulted["n_sigma"])

    def test_only_the_mode_parameters_are_reported(self):
        _, out, _ = run(PID, "--mode", "dedx", "--species", "pi", "K", "--momentum", "0.5")
        self.assertIn("material", out["defaults_used"])
        self.assertNotIn("path", out["defaults_used"])
        self.assertNotIn("path", out["inputs"])


class CherenkovDefaults(unittest.TestCase):
    def test_defaulted_detector_parameters_warn(self):
        code, out, err = run(CHER, "--index", "1.05", "--species", "pi", "K")
        self.assertEqual(code, 0, err)
        for name in ("radiator_length", "figure_of_merit", "single_photon_resolution", "track_resolution", "momentum"):
            self.assertIn(name, out["defaults_used"])
        self.assertEqual(sum("describes no particular detector" in w for w in out["warnings"]), 4)
        code, out, _ = run(CHER, "--index", "1.05", "--species", "pi", "K", "--momentum", "10", "--radiator-length",
                           "2", "--figure-of-merit", "100", "--single-photon-resolution", "5", "--track-resolution", "0",
                           "--convention", "single")
        self.assertEqual(out["defaults_used"], {})
        self.assertFalse([w for w in out["warnings"] if "describes no particular detector" in w])


class GeomagneticDefaults(unittest.TestCase):
    def test_defaulted_dipole_is_reported_with_its_epoch(self):
        code, out, err = run(GEO, "--latitude", "30")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["dipole"], {"moment_g_cm3": 8.05e25, "epoch": "1955"})
        self.assertEqual(out["defaults_used"]["dipole_moment_g_cm3"], 8.05e25)
        self.assertTrue(any("dipole moment not given" in w for w in out["warnings"]))

    def test_given_dipole_and_epoch(self):
        code, out, _ = run(GEO, "--latitude", "30", "--dipole-moment", "7.69e25", "--epoch", "2025")
        self.assertEqual(code, 0)
        self.assertEqual(out["dipole"], {"moment_g_cm3": 7.69e25, "epoch": "2025"})
        self.assertNotIn("dipole_moment_g_cm3", out["defaults_used"])
        self.assertEqual(out["warnings"], [])
        _, out, _ = run(GEO, "--latitude", "30", "--dipole-moment", "7.69e25")
        self.assertEqual(out["dipole"]["epoch"], "not stated")
        self.assertTrue(any("without --epoch" in w for w in out["warnings"]))
        code, _, _ = run(GEO, "--latitude", "30", "--epoch", "2025")       # an epoch without its moment
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
