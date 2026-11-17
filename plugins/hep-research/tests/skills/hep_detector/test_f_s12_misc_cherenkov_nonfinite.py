"""CHK-AT-01-01 (S4): cherenkov_angle.py on an expected photon number that is not finite, or a per-track angular
resolution that underflows to zero.

Defect: with --radiator-length 1e200 --figure-of-merit 1e200, N0 * L = 1e400 overflows to inf, the per-track resolution
5e-3 / sqrt(inf) (+) 0 is 0, and main() divides the angle difference by it: a ZeroDivisionError traceback, exit 1 and an
empty stdout. The script's docstring and its tool contract allow exit 1 only with a JSON object (ok false), and exit 2
only with a JSON object of error_kind invalid-input.

Expected behaviour, fixed here before the fix is written (from the docstring's exit-code paragraph, not from the
script's output):
- an expected photon number that is not finite is invalid input: exit 2, one JSON object on stdout with ok false and
  error_kind invalid-input, the usage on stderr, no traceback;
- finite inputs whose per-track resolution underflows to zero (single-photon resolution 1e-300 mrad with about 1e299
  expected photons: 1e-303 / sqrt(1e299) is below the smallest double) make the computation fail: exit 1, one JSON
  object on stdout with ok false, no traceback.
Negative control: an ordinary case (pi and K at 10 GeV/c in n = 1.05) still exits 0 with a finite n_sigma; it passes on
the parent and on the fix.

Tolerances: none. Every comparison is exact (exit codes, JSON keys and labels); the negative control only checks that
n_sigma is a finite number greater than zero, not its value.

Run from the plugin root: python3 -m unittest tests.skills.hep_detector.test_f_s12_misc_cherenkov_nonfinite -v
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-detector" / "scripts" / "cherenkov_angle.py"
BASE = ("--index", "1.05", "--species", "pi", "K", "--momentum", "10")


def run(*extra):
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *BASE, *extra], capture_output=True, text=True, timeout=120)


class NonFinitePhotonNumber(unittest.TestCase):
    def test_overflowing_photon_number_is_invalid_input(self):
        """The audit's run e2: N0 * L = 1e400 is not a finite expected photon number."""
        p = run("--radiator-length", "1e200", "--figure-of-merit", "1e200")
        self.assertNotIn("Traceback", p.stderr)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        out = json.loads(p.stdout)
        self.assertIs(out["ok"], False)
        self.assertEqual(out["error_kind"], "invalid-input")
        self.assertIn("photon", out["error"])

    def test_resolution_underflowing_to_zero_fails_with_json(self):
        """Finite N of about 1e299 and a 1e-300 mrad single-photon term: the per-track resolution is 0.0."""
        p = run("--radiator-length", "1e150", "--figure-of-merit", "1e150", "--single-photon-resolution", "1e-300",
                "--track-resolution", "0")
        self.assertNotIn("Traceback", p.stderr)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        out = json.loads(p.stdout)
        self.assertIs(out["ok"], False)
        self.assertEqual(out["status"], "failed")

    def test_negative_control_ordinary_case_is_unchanged(self):
        p = run("--radiator-length", "2", "--figure-of-merit", "100", "--single-photon-resolution", "5",
                "--track-resolution", "0")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        out = json.loads(p.stdout)
        self.assertTrue(isinstance(out["n_sigma"], float) and math.isfinite(out["n_sigma"]) and out["n_sigma"] > 0)


if __name__ == "__main__":
    unittest.main()
