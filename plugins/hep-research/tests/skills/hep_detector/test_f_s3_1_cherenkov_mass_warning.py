"""CHK-AT-01-04 (S3): cherenkov_angle.py warns when its first-order relative mass resolution is not reliable.

relative_mass_resolution = gamma^2 dbeta/beta is the first-order propagation of m = p sqrt(1/beta^2 - 1). PDG RPP 2025,
Probability, sec. 39.2.1 (eqs. 39.18-39.19): the linear approximation can break down when the function is
significantly nonlinear within a region comparable to the standard deviation. Near beta = 1 the mass is nonlinear in
beta (and undefined for beta >= 1) once the beta error is not small against 1 - beta. Before the fix the tool printed
dm/m = 2.08 for pions at 10 GeV/c in n = 1.05 with no warning; it warned only for dbeta/beta > 0.1.

Expected behaviour (the threshold 0.1 is the one the script already uses for dbeta/beta): a species whose
gamma^2 dbeta/beta exceeds 0.1 gets one warning naming the species and "relative mass resolution"; a species below
it gets none. Which species exceed 0.1 is decided here from the closed forms (PDG RPP 2025, Particle detectors at
accelerators, eqs. 35.8, 35.11, 35.12: N = L N0 sin^2(theta_c), sigma = sqrt(sigma_photon^2/N + sigma_track^2),
dbeta/beta = tan(theta_c) sigma), not from the tool's output.
Negative control: a case where both species are below 0.1 (pi and K at 2 GeV/c in n = 1.05) has no such warning.

Tolerances: none. The closed-form values are only compared with 0.1 (pi 2.08 and K 0.166 at 10 GeV/c; pi 0.083 and
K 0.0065 at 2 GeV/c), and the warnings are counted exactly.

Run from the plugin root: python3 -m unittest tests.skills.hep_detector.test_f_s3_1_cherenkov_mass_warning -v
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
MASSES = {"pi": 0.13957039, "K": 0.493677}  # GeV, PDG
DETECTOR = ("--radiator-length", "2", "--figure-of-merit", "100", "--single-photon-resolution", "5",
            "--track-resolution", "0.5")


def closed_form_mass_resolution(index, momentum, mass, length_cm=2.0, n0=100.0, sigma_photon=5e-3, sigma_track=5e-4):
    energy = math.hypot(momentum, mass)
    beta, gamma = momentum / energy, energy / mass
    theta = math.acos(1.0 / (index * beta))
    photons = length_cm * n0 * math.sin(theta) ** 2
    sigma = math.sqrt(sigma_photon ** 2 / photons + sigma_track ** 2)
    return gamma ** 2 * math.tan(theta) * sigma


def run(momentum):
    proc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--index", "1.05", "--species", "pi", "K",
                           "--momentum", str(momentum), *DETECTOR], capture_output=True, text=True, timeout=120)
    return proc.returncode, json.loads(proc.stdout)


def mass_warnings(payload, label):
    return [w for w in payload["warnings"] if w.startswith(f"species {label}:") and "relative mass resolution" in w]


class MassResolutionWarning(unittest.TestCase):
    def test_above_threshold_is_warned(self):
        code, payload = run(10)
        self.assertEqual(code, 0)
        for label, name in (("a", "pi"), ("b", "K")):
            with self.subTest(species=name):
                self.assertGreater(closed_form_mass_resolution(1.05, 10.0, MASSES[name]), 0.1)
                self.assertEqual(len(mass_warnings(payload, label)), 1)

    def test_negative_control_below_threshold(self):
        code, payload = run(2)
        self.assertEqual(code, 0)
        for label, name in (("a", "pi"), ("b", "K")):
            with self.subTest(species=name):
                self.assertLess(closed_form_mass_resolution(1.05, 2.0, MASSES[name]), 0.1)
                self.assertEqual(mass_warnings(payload, label), [])


if __name__ == "__main__":
    unittest.main()
