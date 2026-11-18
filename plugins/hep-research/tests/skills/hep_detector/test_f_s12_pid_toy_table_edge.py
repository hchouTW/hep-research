"""CHK-AT-06-01 (S1): multisample_pid.py charge --toys left out toy events with a sample outside the response table
without saying so, so the predicted core width came from the surviving (narrower) toys only.

Evidence, all inputs SYNTHETIC (identity response signal = Z^2, toy Z = 2, relative Moyal width 0.12, 4 layers,
truncated mean dropping the highest 25%):
- analytic (third-party): the fraction of toy events left out equals 1 - (F(hi) - F(lo))^L, with F the Moyal CDF of
  scipy.stats.moyal (scipy's own definition) at the table ends lo = 0 and hi = 5.5, L = 4 independent layers;
- independent implementation (third-party): the same fraction from toys drawn with scipy.stats.moyal.rvs (scipy's own
  sampler, not the tool's inverse-CDF formula);
- invariant: used + left out = requested, used = the summary's n; a table that covers the tail leaves none out;
- negative control emulating the pre-fix behaviour: the width of the kept toys only is biased low against the width
  of all toys (the silent loss changes the number the tool reports).

Tolerances (fixed before the first run, never widened): the left-out fraction is a binomial count of N = 20000 toys,
so the tool's fraction is compared with the CDF value within 5 binomial standard deviations sqrt(p (1 - p) / N)
(about 0.018 at p = 0.52), and with the scipy-sampled fraction within 5 standard deviations of the difference of two
independent binomial fractions (sqrt(2) times that). The negative control asks for a bias of more than 15% at
200000 scipy toys, where the bias is about 22% (a scipy-only computation before the test was written) and the
statistical error of sigma68 is below 1%.
The oracles do not import the module under test.
"""
import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "skills" / "hep-detector" / "scripts" / "multisample_pid.py"

N_TOYS = 20000
TOY_Z = 2.0
REL = 0.12
N_LAYERS = 4
TABLE_HI = 5.5  # the response table ends at signal 5.5, inside the per-layer tail at Z = 2 (loc 4, scale 0.48)
N_SIGMA = 5.0
BIAS_MIN = 0.15
TOY_WARNING = re.compile(r"^(\d+) of (\d+) toy events had a sample outside the response table")


def run_json(*args, timeout=600):
    res = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True,
                         timeout=timeout)
    try:
        return res.returncode, json.loads(res.stdout)
    except json.JSONDecodeError:
        raise AssertionError(res.stdout + res.stderr) from None


def sigma68(values):
    lo, hi = np.quantile(values, [(1 - 0.6827) / 2, (1 + 0.6827) / 2])
    return (hi - lo) / 2


class ToyTableEdge(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.TemporaryDirectory()
        self.d = Path(self.workdir.name)
        self.layers = [f"s{i}" for i in range(N_LAYERS)]
        with open(self.d / "ev.csv", "w", encoding="utf-8") as fh:
            fh.write("z," + ",".join(self.layers) + "\n")
            fh.write("\n".join("2," + ",".join(["4.0"] * N_LAYERS) for _ in range(5)) + "\n")

    def tearDown(self):
        self.workdir.cleanup()

    def run_toys(self, table_hi):
        resp = self.d / "response.json"
        resp.write_text(json.dumps({"z2": [0.0, table_hi], "signal": [0.0, table_hi]}), encoding="utf-8")
        code, out = run_json("charge", self.d / "ev.csv", "--layers", ",".join(self.layers), "--response", resp,
                             "--method", "truncated-mean", "--truncate-high", "0.25", "--no-path-correction",
                             "--toys", N_TOYS, "--toy-z", TOY_Z, "--toy-moyal-rel-width", REL, "--seed", 7)
        self.assertEqual(code, 0, out)
        return out

    def left_out(self, out):
        hits = [m for m in map(TOY_WARNING.match, out["warnings"]) if m]
        self.assertEqual(len(hits), 1, f"no warning counts the toy events left out: {out['warnings']}")
        k, n = int(hits[0].group(1)), int(hits[0].group(2))
        self.assertEqual(n, N_TOYS)
        return k

    def test_left_out_fraction_matches_the_moyal_cdf(self):
        out = self.run_toys(TABLE_HI)
        k = self.left_out(out)
        mu = TOY_Z ** 2
        dist = stats.moyal(loc=mu, scale=REL * mu)
        p_in = dist.cdf(TABLE_HI) - dist.cdf(0.0)
        p_out = 1.0 - p_in ** N_LAYERS
        sd = math.sqrt(p_out * (1 - p_out) / N_TOYS)
        self.assertAlmostEqual(k / N_TOYS, p_out, delta=N_SIGMA * sd)

    def test_left_out_fraction_matches_scipy_sampling(self):
        out = self.run_toys(TABLE_HI)
        k = self.left_out(out)
        mu = TOY_Z ** 2
        sig = stats.moyal.rvs(loc=mu, scale=REL * mu, size=(N_TOYS, N_LAYERS), random_state=np.random.default_rng(1))
        p_ref = float(np.mean(np.any((sig < 0.0) | (sig > TABLE_HI), axis=1)))
        sd = math.sqrt(2 * p_ref * (1 - p_ref) / N_TOYS)
        self.assertAlmostEqual(k / N_TOYS, p_ref, delta=N_SIGMA * sd)

    def test_counts_add_up_and_a_wide_table_leaves_none_out(self):
        out = self.run_toys(TABLE_HI)
        toy = out["toy_prediction"]
        k = self.left_out(out)
        self.assertEqual(toy["toys_requested"], N_TOYS)
        self.assertEqual(toy["toys_used"], toy["n"])
        self.assertEqual(toy["toys_used"] + k, N_TOYS)
        self.assertTrue(any("biased low" in w for w in out["warnings"] if TOY_WARNING.match(w)))
        wide = self.run_toys(100.0)
        self.assertEqual(wide["toy_prediction"]["toys_used"], N_TOYS)
        self.assertFalse([w for w in wide["warnings"] if "toy" in w], wide["warnings"])

    def test_negative_control_kept_toys_only_are_too_narrow(self):
        """Pre-fix behaviour, emulated: the width from the toys inside the table only, against all toys."""
        mu = TOY_Z ** 2
        sig = stats.moyal.rvs(loc=mu, scale=REL * mu, size=(200000, N_LAYERS), random_state=np.random.default_rng(2))
        per = np.sqrt(np.clip(sig, 0.0, None))  # identity response: per-layer |Z| = sqrt(signal)
        tmean = np.sort(per, axis=1)[:, :N_LAYERS - 1].mean(axis=1)  # drop the highest of 4 (floor(0.25 x 4) = 1)
        kept = np.all((sig >= 0.0) & (sig <= TABLE_HI), axis=1)
        self.assertGreater(kept.mean(), 0.3)
        self.assertLess(sigma68(tmean[kept]), (1 - BIAS_MIN) * sigma68(tmean))


if __name__ == "__main__":
    unittest.main()
