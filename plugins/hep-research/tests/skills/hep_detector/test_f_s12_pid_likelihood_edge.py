"""CHK-AT-06-02 (S1): multisample_pid.py charge --method likelihood returned the first or last point of --z-range when
the likelihood maximum lies outside it, so events of a charge above the range were reported at ZMAX (sigma68 0) with
no warning. An estimate on the edge of the scan is not a maximum of L (PDG Statistics, sec. 40.2.2: the estimators
are the "values that give the maximum of L"); it is now counted and left out.

Evidence, all inputs SYNTHETIC (identity response signal = Z^2, per-layer Moyal densities at R(Z^2) with relative
width 0.1, --z-range 0.5 3.5):
- independent implementation (third-party): per event, the continuous maximum-likelihood Z from
  scipy.optimize.minimize_scalar over scipy.stats.moyal.logpdf (scipy's own density and optimizer), bracketed by a
  400-point log-spaced scan of [0.05, 12], a range wide enough to hold every maximum; events of true Z = 5 have their maximum above 3.5 and must be counted at the edge,
  events of true Z = 2 must be kept with the scipy median;
- exhaustive: over the stated finite domain of 200 events whose 4 layers all read s = 0.1, 0.2, ..., 20.0, each case
  is expected at the edge exactly when its continuous maximum lies outside [0.5, 3.5] (both edges occur);
- invariant: events used + events at the edge = events read; toys at the edge are counted the same way;
- negative control emulating the pre-fix behaviour: clipping the maximum into the range (what returning the edge
  point does) puts every Z = 5 event more than 1 away from its maximum-likelihood value.

Tolerances (fixed before the first run, never widened): the tool scans a grid; for a unimodal likelihood the grid
maximum is one of the two grid points around the continuous maximum, so a kept estimate lies within one scan step
(0.002) of it; 0.0021 adds the optimizer's precision (xatol 1e-6). Exhaustive cases whose maximum lies within 0.004
(two scan steps) of an edge are excluded as ambiguous and counted, and the domain is stated in the test. The oracles do
not import the module under test.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy import optimize, stats

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "skills" / "hep-detector" / "scripts" / "multisample_pid.py"

REL = 0.1
ZMIN, ZMAX = 0.5, 3.5
STEP_TOL = 0.0021
AMBIGUOUS = 0.004
EDGE_WARNING = re.compile(r"^(\d+) events had their likelihood maximum at the edge of --z-range")
TOY_EDGE_WARNING = re.compile(r"^(\d+) of (\d+) toy events had their likelihood maximum at the edge of --z-range")


def run_json(*args, timeout=600):
    res = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True,
                         timeout=timeout)
    try:
        return res.returncode, json.loads(res.stdout)
    except json.JSONDecodeError:
        raise AssertionError(res.stdout + res.stderr) from None


def scipy_mle(signals):
    """Continuous maximum-likelihood |Z| with scipy's Moyal density located at Z^2 (identity response)."""
    def nll(z):
        mu = z * z
        return -float(np.sum(stats.moyal.logpdf(signals, loc=mu, scale=REL * mu)))
    zs = np.geomspace(0.05, 12.0, 400)  # bracket the global maximum first: far from it the density underflows
    i = int(np.argmin([nll(z) for z in zs]))
    res = optimize.minimize_scalar(nll, bounds=(zs[max(i - 1, 0)], zs[min(i + 1, len(zs) - 1)]), method="bounded",
                                   options={"xatol": 1e-6})
    return float(res.x)


class LikelihoodEdge(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.d = Path(self.workdir.name)
        self.resp = self.d / "response.json"
        self.resp.write_text(json.dumps({"z2": [0.0, 400.0], "signal": [0.0, 400.0]}), encoding="utf-8")

    def tearDown(self):
        self.workdir.cleanup()

    def write(self, rows, n_layers):
        layers = [f"s{i}" for i in range(n_layers)]
        with open(self.d / "ev.csv", "w", encoding="utf-8") as fh:
            fh.write("z," + ",".join(layers) + "\n")
            for z, sig in rows:
                fh.write(f"{z}," + ",".join(repr(float(s)) for s in sig) + "\n")
        return layers

    def run_tool(self, layers, *extra):
        return run_json("charge", self.d / "ev.csv", "--layers", ",".join(layers), "--response", self.resp,
                        "--method", "likelihood", "--moyal-rel-width", REL, "--z-range", ZMIN, ZMAX,
                        "--true-z-column", "z", "--no-path-correction", *extra)

    def edge_count(self, out):
        hits = [m for m in map(EDGE_WARNING.match, out["warnings"]) if m]
        self.assertEqual(len(hits), 1, f"no warning counts the events at the edge of --z-range: {out['warnings']}")
        return int(hits[0].group(1))

    def sampled_rows(self):
        rng = np.random.default_rng(5)
        rows = []
        for z in (2, 5):
            mu = z * z
            for sig in stats.moyal.rvs(loc=mu, scale=REL * mu, size=(40, 6), random_state=rng):
                rows.append((z, sig))
        return rows

    def test_maxima_outside_the_range_are_counted_not_returned(self):
        rows = self.sampled_rows()
        mle = [scipy_mle(sig) for _, sig in rows]
        self.assertTrue(all(abs(m - ZMAX) > 0.05 and abs(m - ZMIN) > 0.05 for m in mle))  # no ambiguous case
        expected_edge = sum(1 for m in mle if not ZMIN <= m <= ZMAX)
        self.assertEqual(expected_edge, sum(1 for z, _ in rows if z == 5))
        code, out = self.run_tool(self.write(rows, 6))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.edge_count(out), expected_edge)
        self.assertNotIn("5", out["per_true_z"])
        kept = [m for (z, _), m in zip(rows, mle) if z == 2]
        self.assertAlmostEqual(out["per_true_z"]["2"]["median"], float(np.median(kept)), delta=STEP_TOL)

    def test_exhaustive_constant_signals(self):
        domain = [k / 10 for k in range(1, 201)]  # s = 0.1 .. 20.0 on all 4 layers
        mle = {s: scipy_mle(np.full(4, s)) for s in domain}
        cases = [s for s in domain if min(abs(mle[s] - ZMIN), abs(mle[s] - ZMAX)) > AMBIGUOUS]
        self.assertGreater(len(cases), 190)
        low = [s for s in cases if mle[s] < ZMIN]
        high = [s for s in cases if mle[s] > ZMAX]
        self.assertTrue(low and high)  # both edges are exercised
        code, out = self.run_tool(self.write([(1, [s] * 4) for s in cases], 4))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.edge_count(out), len(low) + len(high))
        self.assertEqual(out["events_used"], len(cases) - len(low) - len(high))

    def test_counts_add_up_for_events_and_toys(self):
        rows = self.sampled_rows()
        code, out = self.run_tool(self.write(rows, 6), "--toys", 300, "--toy-z", 3.4, "--toy-moyal-rel-width", REL,
                                  "--seed", 3)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["events_used"] + out["at_z_range_edge"], len(rows))
        self.assertEqual(out["at_z_range_edge"], self.edge_count(out))
        toy = out["toy_prediction"]
        hits = [m for m in map(TOY_EDGE_WARNING.match, out["warnings"]) if m]
        self.assertEqual(len(hits), 1, out["warnings"])  # toys at Z = 3.4 reach above 3.5
        self.assertEqual(int(hits[0].group(2)), 300)
        self.assertEqual(toy["toys_used"] + int(hits[0].group(1)), 300)
        self.assertLessEqual(toy["median"], ZMAX)
        code, out = self.run_tool(self.write([(z, s) for z, s in rows if z == 5], 6))
        self.assertEqual(code, 2, out)
        self.assertEqual(out["status"], "rejected")
        self.assertIn("edge of --z-range", out["error"])

    def test_negative_control_returning_the_edge_is_far_from_the_maximum(self):
        """Pre-fix behaviour, emulated: the estimate clipped into --z-range."""
        rows = [(z, sig) for z, sig in self.sampled_rows() if z == 5]
        for _, sig in rows:
            m = scipy_mle(sig)
            self.assertGreater(abs(min(max(m, ZMIN), ZMAX) - m), 1.0)


if __name__ == "__main__":
    unittest.main()
