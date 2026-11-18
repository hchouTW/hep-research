"""CHK-AT-04-04 (S3): calorimeter_resolution.py --evaluate no longer evaluates zero or omitted terms silently.

In --evaluate mode --stochastic, --noise and --constant all default to 0. Before the fix, --evaluate --energy 10 alone
exited 0 with relative_resolution 0 and no warning, and --evaluate --stochastic 0.1 gave a stochastic-only resolution
with no high-energy floor, the extrapolation that calorimetry-ecal-hcal.md calls the most common analysis error. PDG
RPP 2025, Particle detectors at accelerators, sec. 35.10.1.1, p. 92: the resolution at high energies is limited by the
constant term; the noise term (sigma_N = B) is not energy-dependent, so its relative part dominates at low energy.

Expected behaviour (from the fixed docstring, not from the script's output):
- all three terms zero: invalid input, exit 2, a JSON object with error_kind invalid-input;
- a zero noise or constant term: exit 0 with one warning per zero term, naming it;
- three nonzero terms (the negative control, and the form of every committed example output): no "warnings" key, so
  those outputs are unchanged.

Tolerances: none. Exit codes, keys and warning counts are compared exactly.

Run from the plugin root: python3 -m unittest tests.skills.hep_detector.test_f_s3_1_calorimeter_zero_terms -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-detector" / "scripts" / "calorimeter_resolution.py"


def run(*args):
    proc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--evaluate", *args], capture_output=True, text=True,
                          timeout=120)
    return proc.returncode, json.loads(proc.stdout)


def zero_term_warnings(payload, name):
    return [w for w in payload.get("warnings", []) if w.startswith(f"{name} term 0")]


class ZeroTerms(unittest.TestCase):
    def test_all_terms_zero_is_refused(self):
        code, payload = run("--energy", "10")
        self.assertEqual(code, 2)
        self.assertEqual(payload["error_kind"], "invalid-input")

    def test_zero_constant_and_noise_are_warned(self):
        code, payload = run("--stochastic", "0.1", "--energy", "10")
        self.assertEqual(code, 0)
        self.assertEqual(len(zero_term_warnings(payload, "constant")), 1)
        self.assertEqual(len(zero_term_warnings(payload, "noise")), 1)
        code, payload = run("--stochastic", "0.1", "--noise", "0.2", "--energy", "10")
        self.assertEqual(code, 0)
        self.assertEqual(len(zero_term_warnings(payload, "constant")), 1)
        self.assertEqual(zero_term_warnings(payload, "noise"), [])

    def test_negative_control_three_terms_have_no_warnings_key(self):
        code, payload = run("--stochastic", "0.03", "--noise", "0.12", "--constant", "0.003", "--energy", "50")
        self.assertEqual(code, 0)
        self.assertNotIn("warnings", payload)


if __name__ == "__main__":
    unittest.main()
