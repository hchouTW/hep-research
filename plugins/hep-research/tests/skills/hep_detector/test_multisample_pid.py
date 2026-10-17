"""D10: multisample_pid.py, combining many samples of one particle (charge from many dE/dx layers, a log-likelihood
ratio from per-layer PDFs).

Oracles:
- charge, truncated mean: on Landau-like (Moyal) per-layer samples the core width (sigma68) of the truncated mean
  matches the script's own toy prediction from the per-layer model within statistics;
- charge, leakage: Gaussian per-layer estimates of Z with width sigma; the mean of n layers has width sigma/sqrt(n),
  so P(reco = Z +- 1 | Z) = 1 - Phi(0.5 sqrt(n) / sigma); the leakage matrix matches it, with Clopper-Pearson
  intervals that contain the counts' fractions;
- charge, response inversion: a saturating response curve is inverted back to the true Z;
- likelihood: with the true per-layer PDFs (equal-variance Gaussians, separation d per layer, n layers) the
  efficiency at a mis-identification rate alpha reaches the Neyman-Pearson bound 1 - Phi(z_{1-alpha} - d sqrt(n));
- without declared layer correlations the output says "independence assumed";
- bad input (non-monotonic response, missing column, truncation outside [0, 1), missing PDFs) is exit 2.
All inputs are SYNTHETIC.
"""
import csv
import json
import math
import random
import statistics
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "skills" / "hep-detector" / "scripts" / "multisample_pid.py"
ND = statistics.NormalDist()


def run_json(*args, timeout=600):
    res = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True,
                         timeout=timeout)
    try:
        return res.returncode, json.loads(res.stdout)
    except json.JSONDecodeError:
        raise AssertionError(res.stdout + res.stderr) from None


def moyal(rng, loc, scale):
    """Moyal (Landau approximation) sample: F(x) = 2 (1 - Phi(exp(-lambda/2))), lambda = (x - loc)/scale."""
    u = rng.uniform(1e-12, 1 - 1e-12)
    t = ND.inv_cdf(1.0 - u / 2.0)
    return loc + scale * (-2.0 * math.log(t))


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


class ChargeMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def response(self, z2, signal):
        p = self.d / "response.json"
        p.write_text(json.dumps({"z2": z2, "signal": signal}), encoding="utf-8")
        return p

    def test_truncated_mean_width_matches_toys(self):
        rng = random.Random(3)
        n_layers, rel = 8, 0.12
        rows = [[1] + [moyal(rng, 1.0, rel) for _ in range(n_layers)] for _ in range(4000)]
        layers = [f"s{i}" for i in range(n_layers)]
        write_csv(self.d / "ev.csv", ["z"] + layers, rows)
        resp = self.response([0.0, 100.0], [0.0, 100.0])  # signal = Z^2
        code, out = run_json("charge", self.d / "ev.csv", "--layers", ",".join(layers), "--response", resp,
                             "--true-z-column", "z", "--method", "truncated-mean", "--truncate-high", "0.25",
                             "--no-path-correction", "--toys", "4000", "--toy-z", "1", "--toy-moyal-rel-width", str(rel),
                             "--seed", "11")
        self.assertEqual(code, 0, out)
        z1 = out["per_true_z"]["1"]
        toy = out["toy_prediction"]["sigma68"]
        self.assertAlmostEqual(z1["sigma68"], toy, delta=0.08 * toy)
        self.assertIn("independence assumed", out["correlations"])
        self.assertLess(z1["sigma68"], rel / 2)  # truncation beats a single layer

    def test_leakage_matrix_matches_the_gaussian_truth(self):
        rng = random.Random(5)
        n_layers, sigma, n = 4, 0.8, 15000
        layers = [f"s{i}" for i in range(n_layers)]
        rows = [[z] + [z + rng.gauss(0.0, sigma) for _ in range(n_layers)] for z in (3, 4, 5, 6, 7) for _ in range(n)]
        write_csv(self.d / "ev.csv", ["z"] + layers, rows)
        zs = [k / 100 for k in range(1201)]  # dense knots, so linear interpolation keeps signal = Z
        resp = self.response([z * z for z in zs], zs)
        code, out = run_json("charge", self.d / "ev.csv", "--layers", ",".join(layers), "--response", resp,
                             "--true-z-column", "z", "--method", "weighted-mean", "--layer-sigma", str(sigma),
                             "--no-path-correction")
        self.assertEqual(code, 0, out)
        p = 1.0 - ND.cdf(0.5 * math.sqrt(n_layers) / sigma)
        leak = out["leakage"]
        for z in (4, 5, 6):  # interior charges, far from the table ends
            row = leak["probabilities"][str(z)]
            for nb in (z - 1, z + 1):
                with self.subTest(z=z, reco=nb):
                    self.assertAlmostEqual(row[str(nb)], p, delta=4 * math.sqrt(p * (1 - p) / n))
                    lo, hi = leak["intervals"][str(z)][str(nb)]
                    self.assertLessEqual(lo, row[str(nb)])
                    self.assertGreaterEqual(hi, row[str(nb)])
        self.assertEqual(leak["interval"], "Clopper-Pearson, central 68.27%")

    def test_saturating_response_is_inverted(self):
        zs = [1, 2, 3, 4, 5, 6]
        resp = self.response([z * z for z in range(0, 9)], [z * z / (1 + 0.02 * z * z) for z in range(0, 9)])
        rows = [[z] + [z * z / (1 + 0.02 * z * z)] * 3 for z in zs]
        write_csv(self.d / "ev.csv", ["z", "a", "b", "c"], rows)
        code, out = run_json("charge", self.d / "ev.csv", "--layers", "a,b,c", "--response", resp,
                             "--true-z-column", "z", "--method", "truncated-mean", "--truncate-high", "0",
                             "--no-path-correction")
        self.assertEqual(code, 0, out)
        for z in zs:
            self.assertAlmostEqual(out["per_true_z"][str(z)]["median"], z, delta=0.02)

    def test_path_length_correction(self):
        resp = self.response([0.0, 100.0], [0.0, 100.0])
        write_csv(self.d / "ev.csv", ["z", "a", "b", "cos"], [[2, 8.0, 8.0, 0.5]])
        code, out = run_json("charge", self.d / "ev.csv", "--layers", "a,b", "--response", resp,
                             "--true-z-column", "z", "--method", "truncated-mean", "--truncate-high", "0",
                             "--path-column", "cos")
        self.assertEqual(code, 0, out)
        self.assertAlmostEqual(out["per_true_z"]["2"]["median"], 2.0, delta=1e-9)  # 8 x 0.5 = 4 = Z^2

    def test_declared_correlation_is_reported(self):
        resp = self.response([0.0, 100.0], [0.0, 10.0])
        write_csv(self.d / "ev.csv", ["z", "a", "b"], [[1, 1.0, 1.1], [1, 0.9, 1.0]])
        code, out = run_json("charge", self.d / "ev.csv", "--layers", "a,b", "--response", resp,
                             "--true-z-column", "z", "--method", "weighted-mean", "--layer-sigma", "0.1",
                             "--correlation", "0.3", "--no-path-correction")
        self.assertEqual(code, 0, out)
        self.assertIn("0.3", out["correlations"])

    def test_bad_input_is_rejected(self):
        good = self.response([0.0, 100.0], [0.0, 100.0])
        bad = self.response([0.0, 50.0, 100.0], [0.0, 60.0, 40.0])
        write_csv(self.d / "ev.csv", ["z", "a", "b"], [[1, 1.0, 1.1]])
        cases = [
            ("--response", bad, "--truncate-high", "0.2", "--no-path-correction"),
            ("--response", good, "--truncate-high", "1.0", "--no-path-correction"),
            ("--response", good, "--truncate-high", "0.2"),  # path correction neither given nor waived
        ]
        for extra in cases:
            with self.subTest(extra=extra):
                code, out = run_json("charge", self.d / "ev.csv", "--layers", "a,b", "--method", "truncated-mean",
                                     *extra)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")
        code, out = run_json("charge", self.d / "ev.csv", "--layers", "a,zz", "--response", good, "--method",
                             "truncated-mean", "--truncate-high", "0.2", "--no-path-correction")
        self.assertEqual(code, 2)


class LikelihoodMode(unittest.TestCase):
    def test_reaches_the_neyman_pearson_bound(self):
        rng = random.Random(9)
        n_layers, d, n = 4, 1.0, 20000
        edges = [-6.0 + 0.05 * k for k in range(281)]
        sig = [ND.cdf(b - d) - ND.cdf(a - d) for a, b in zip(edges[:-1], edges[1:])]
        bkg = [ND.cdf(b) - ND.cdf(a) for a, b in zip(edges[:-1], edges[1:])]
        layers = [f"x{i}" for i in range(n_layers)]
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "pdf.json").write_text(json.dumps({"edges": edges, "signal": sig, "background": bkg}), encoding="utf-8")
            rows = [[1] + [rng.gauss(d, 1) for _ in layers] for _ in range(n)]
            rows += [[0] + [rng.gauss(0, 1) for _ in layers] for _ in range(n)]
            write_csv(t / "ev.csv", ["label"] + layers, rows)
            code, out = run_json("likelihood", t / "ev.csv", "--layers", ",".join(layers), "--pdfs", t / "pdf.json",
                                 "--label-column", "label")
        self.assertEqual(code, 0, out)
        alpha = 0.1
        bound = 1.0 - ND.cdf(ND.inv_cdf(1 - alpha) - d * math.sqrt(n_layers))
        curve = out["curve"]
        eff = max(p["efficiency"] for p in curve if p["misid"] <= alpha)
        self.assertAlmostEqual(eff, bound, delta=0.02)
        self.assertIn("independence assumed", out["correlations"])
        pt = curve[len(curve) // 2]
        self.assertLessEqual(pt["efficiency_interval"][0], pt["efficiency"])
        self.assertGreaterEqual(pt["misid_interval"][1], pt["misid"])

    def test_missing_pdfs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_csv(Path(tmp) / "ev.csv", ["label", "a"], [[1, 0.5]])
            code, out = run_json("likelihood", Path(tmp) / "ev.csv", "--layers", "a", "--pdfs",
                                 Path(tmp) / "none.json", "--label-column", "label")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
