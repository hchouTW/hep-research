"""CHK-AT-02-01 evidence: tracker_resolution.py momentum keeps each layer position with its own point resolution.

Defect (parent): the positions were sorted but the per-layer resolutions were kept in input order, so for unsorted
positions with unequal resolutions every resolution was attached to a different layer and the curvature error was
that of another layout (a factor 2.2 too small on the layout below).

Oracles (none imports the module under test; no expected value is copied from its output):
- the weighted least-squares curvature error of PDG RPP 2025, 35. Particle Detectors at Accelerators, sec. 35.12,
  eq. (35.69), p. 112 (read 2026-11-17): (delta k_res)^2 = (4/w) V_ss / (V_ss V_s2s2 - V_ss2^2), with
  V_{s^m s^n} = <s^m s^n> - <s^m><s^n>, <s^m> = w^-1 sum(s_i^m / eps_i^2), w = sum(eps_i^-2), transcribed in
  `pdg_curvature_sigma` below and evaluated on the (position, resolution) pairs as given;
- exhaustive: all 24 orders of the same four (position, resolution) pairs give one curvature error (the fit depends
  on the set of pairs only, eq. 35.69 being a sum over points);
- negative control: the pre-fix pairing (positions sorted, resolutions in input order), emulated here with the same
  transcribed formula, differs from the correct value by more than a factor 2, so the oracle discriminates.

Tolerances, fixed before the first run: relative 1e-9 between the tool and the transcribed formula (both evaluate
the same closed form in double precision for O(1) m positions; their roundings differ by about 1e-15, so 1e-9 leaves
six orders of margin while a re-pairing changes the value by more than 10%); relative 1e-12 between orders of the
same pairs (only the summation order changes); the negative control needs a ratio above 2 (the issue measured 2.2).
Inputs are SYNTHETIC.
"""
import itertools
import json
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "tracker_resolution.py"

REL_TOL_ORACLE = 1e-9
REL_TOL_ORDER = 1e-12
MIN_PRE_FIX_RATIO = 2.0

# (position m, point resolution um): two coarse layers and two fine layers, given out of order
PAIRS = ((0.3, 100.0), (0.6, 100.0), (0.0, 2.0), (0.9, 2.0))
FIXED = ["--field-tesla", "1.0", "--x-over-x0", "0.01", "--charge", "1", "--beta", "1", "--pt", "10"]


def pdg_curvature_sigma(positions, sigmas):
    """PDG RPP 2025 eq. (35.69), transcribed: sigma of k = 1/R from points s_i with errors eps_i."""
    w = sum(1.0 / e ** 2 for e in sigmas)

    def mean(m):
        return sum(s ** m / e ** 2 for s, e in zip(positions, sigmas)) / w

    v_ss = mean(2) - mean(1) ** 2
    v_ss2 = mean(3) - mean(1) * mean(2)
    v_s2s2 = mean(4) - mean(2) ** 2
    return (4.0 / w * v_ss / (v_ss * v_s2s2 - v_ss2 ** 2)) ** 0.5


def run_momentum(pairs):
    positions = [str(p) for p, _ in pairs]
    resolutions = [str(s) for _, s in pairs]
    proc = subprocess.run([sys.executable, "-B", str(SCRIPT), "momentum", "--positions-m", *positions,
                           "--point-resolution-um", *resolutions, *FIXED],
                          capture_output=True, text=True, timeout=600)
    return proc.returncode, json.loads(proc.stdout), proc.stderr


class PairsKeptTogether(unittest.TestCase):
    def test_unsorted_unequal_layout_matches_the_pdg_fit_of_the_given_pairs(self):
        code, out, err = run_momentum(PAIRS)
        self.assertEqual(code, 0, err)
        expected = pdg_curvature_sigma([p for p, _ in PAIRS], [s * 1e-6 for _, s in PAIRS])
        got = out["intrinsic"]["sigma_curvature_per_m"]
        self.assertLessEqual(abs(got / expected - 1.0), REL_TOL_ORACLE, (got, expected))

    def test_every_order_of_the_pairs_gives_the_same_curvature_error(self):
        values = []
        for order in itertools.permutations(PAIRS):
            code, out, err = run_momentum(order)
            self.assertEqual(code, 0, err)
            values.append(out["intrinsic"]["sigma_curvature_per_m"])
        self.assertEqual(len(values), 24)
        for v in values:
            self.assertLessEqual(abs(v / values[0] - 1.0), REL_TOL_ORDER, values)

    def test_negative_control_the_pre_fix_pairing_is_a_different_layout(self):
        correct = pdg_curvature_sigma([p for p, _ in PAIRS], [s * 1e-6 for _, s in PAIRS])
        pre_fix = pdg_curvature_sigma(sorted(p for p, _ in PAIRS), [s * 1e-6 for _, s in PAIRS])
        self.assertGreater(correct / pre_fix, MIN_PRE_FIX_RATIO, (correct, pre_fix))


if __name__ == "__main__":
    unittest.main()
