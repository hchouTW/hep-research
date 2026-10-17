"""D3: charge_confusion_rate.py. Oracles: a template fit recovers an injected wrong-sign rate; over 200 toys at
injected rates 1e-3 to 1e-1 the 68% interval covers within +-0.05 (slow tier); `control` with integer weights equals
binomial counting with Clopper-Pearson intervals; `gaussian-core` is a lower-bound reference labelled "not an
estimate" and outputs no estimate; the output carries sign rates for species_response.py. Inputs are SYNTHETIC."""
import csv
import importlib.util
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "charge_confusion_rate.py"
sys.path.insert(0, str(PLUGIN))
from core.stats.tail_estimation import clopper_pearson  # noqa: E402

RIGHT = [400, 1200, 2400, 1200, 400, 40, 4, 1]   # SYNTHETIC discriminant shapes (MC counts)
WRONG = [1, 4, 40, 400, 1200, 2400, 1200, 400]


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


def load_module():
    spec = importlib.util.spec_from_file_location("charge_confusion_rate", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def poisson(rng, mu):
    if mu > 50:
        return max(0, int(round(rng.gauss(mu, math.sqrt(mu)))))
    k, p, l_ = 0, 1.0, math.exp(-mu)
    while True:
        p *= rng.random()
        if p <= l_:
            return k
        k += 1


def toy_bin(rng, n_total, rate):
    sr, sw = sum(RIGHT), sum(WRONG)
    mu = [n_total * ((1 - rate) * r / sr + rate * w / sw) for r, w in zip(RIGHT, WRONG)]
    # the MC templates are redrawn too: the Barlow-Beeston interval includes the template statistics (as bb-toys). The
    # generated MC count is fixed (twice the expected template content: a 50% acceptance), so the template sums
    # fluctuate as they do in a real MC sample
    return {"data": [poisson(rng, m) for m in mu],
            "templates": {"right": [poisson(rng, r) for r in RIGHT], "wrong": [poisson(rng, w) for w in WRONG]},
            "mc_events": {"right": 2 * sr, "wrong": 2 * sw}}


class TemplateMode(unittest.TestCase):
    def test_injected_rate_recovered(self):
        rng = random.Random(3)
        doc = {"edges": [1, 10, 100], "true_sign": "negative",
               "bins": [toy_bin(rng, 20000, 0.01), toy_bin(rng, 20000, 0.05)]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            code, out = run("template", "--input", p)
        self.assertEqual(code, 0, out)
        for row, true in zip(out["bins"], (0.01, 0.05)):
            self.assertLess(abs(row["rate"] - true), 4 * row["rate_error"])
        self.assertEqual(out["sign_rates"]["rates"][0]["true"], "negative")
        self.assertEqual(out["sign_rates"]["rates"][0]["reco"], "positive")
        self.assertEqual(len(out["sign_rates"]["rates"][0]["rate"]), 2)

    @unittest.skipUnless(os.environ.get("HEP_SLOW_TESTS") == "1", "slow: set HEP_SLOW_TESTS=1")
    def test_slow_coverage_200_toys(self):
        mod = load_module()
        for rate in (1e-3, 1e-2, 1e-1):
            rng = random.Random(int(rate * 1e4) + 7)
            covered = no_error = 0
            for _ in range(200):
                row = mod.template_rate(toy_bin(rng, 50000, rate), {"right": "right", "wrong": "wrong"})
                if row["interval_68"] is None:  # no interval: reported failed; it covers nothing
                    no_error += 1
                    continue
                covered += row["interval_68"][0] <= rate <= row["interval_68"][1]
            with self.subTest(rate=rate):
                self.assertLess(abs(covered / 200 - 0.683), 0.05, (covered, no_error))


class ControlMode(unittest.TestCase):
    def test_integer_weights_equal_binomial_counting(self):
        rng = random.Random(5)
        with tempfile.TemporaryDirectory() as d:
            ev, dup = Path(d) / "w.csv", Path(d) / "dup.csv"
            rows = [(rng.uniform(1, 100), "negative", "positive" if rng.random() < 0.03 else "negative",
                     rng.randint(1, 3)) for _ in range(600)]
            with ev.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["rig", "truth", "reco", "w"])
                w.writerows(rows)
            with dup.open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["rig", "truth", "reco"])
                for r in rows:
                    for _ in range(r[3]):
                        w.writerow(r[:3])
            common = ["--edges", "1", "10", "100", "--bin-column", "rig", "--true-sign-column", "truth",
                      "--reco-sign-column", "reco"]
            code, a = run("control", "--data", ev, "--weight-column", "w", *common)
            code2, b = run("control", "--data", dup, *common)
        self.assertEqual((code, code2), (0, 0), (a, b))
        for ra, rb in zip(a["bins"], b["bins"]):
            self.assertEqual((ra["n"], ra["k"]), (rb["n"], rb["k"]))
            self.assertEqual(ra["interval_68"], rb["interval_68"])
            lo, hi = clopper_pearson(int(rb["k"]), int(rb["n"]), 0.6826894921370859)
            self.assertAlmostEqual(rb["interval_68"][0], lo, places=12)
            self.assertAlmostEqual(rb["interval_68"][1], hi, places=12)

    def test_non_integer_weights_refused(self):
        with tempfile.TemporaryDirectory() as d:
            ev = Path(d) / "w.csv"
            ev.write_text("rig,truth,reco,w\n5,negative,negative,0.5\n", encoding="utf-8")
            code, out = run("control", "--data", ev, "--weight-column", "w", "--edges", "1", "10", "--bin-column",
                            "rig", "--true-sign-column", "truth", "--reco-sign-column", "reco")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")


class GaussianCore(unittest.TestCase):
    def test_lower_bound_not_an_estimate(self):
        code, out = run("gaussian-core", "--edges", "10", "100", "1000", "--sigma-inv-r", "0.002", "0.002")
        self.assertEqual(code, 0, out)
        self.assertIn("not an estimate", out["label_kind"])
        self.assertIsNone(out["estimate"])
        b = out["bins"][1]
        # at the lower edge R = 100 GV, 1/R = 0.01 and sigma = 0.002: Phi(-5)
        self.assertAlmostEqual(b["lower_bound_at_low_edge"], 0.5 * math.erfc(5 / math.sqrt(2)), places=15)
        self.assertNotIn("sign_rates", out)


if __name__ == "__main__":
    unittest.main()
