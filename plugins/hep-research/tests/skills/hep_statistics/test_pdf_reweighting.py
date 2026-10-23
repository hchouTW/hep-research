"""pdf_reweighting.py (S12): Bayesian reweighting of replicas against hand calculations and a synthetic truth.

Tolerances fixed before comparing: 1e-12 relative for weights and N_eff; the reweighted mean must move toward the
truth and its spread must shrink on the synthetic set.
"""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-statistics/scripts/pdf_reweighting.py"


def run(doc, *args):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "in.json"
        p.write_text(json.dumps(doc))
        r = subprocess.run([sys.executable, str(SCRIPT), str(p), *args], capture_output=True, text=True, timeout=120)
    return r.returncode, json.loads(r.stdout)


def synthetic(n_rep=400, seed=3):
    """Replicas of a one-parameter 'PDF' a_k ~ N(1.0, 0.2); predictions t_i = a x_i; data from a_true = 1.15."""
    rng = np.random.default_rng(seed)
    a = 1.0 + 0.2 * rng.standard_normal(n_rep)
    x = np.array([1.0, 2.0, 3.0])
    sig = np.array([0.15, 0.25, 0.35])
    data = 1.15 * x + sig * rng.standard_normal(3) * 0.0  # exact truth (no noise) so the direction is unambiguous
    return {"set": "toy", "kind": "replicas", "origin": "native-replicas", "predictions": (a[:, None] * x).tolist(),
            "data": data.tolist(), "covariance": np.diag(sig ** 2).tolist(), "observables": {"a": a.tolist()}}, a


class Reweighting(unittest.TestCase):
    def test_hand_weights_and_neff(self):
        doc = {"set": "toy", "kind": "replicas", "origin": "native-replicas",
               "predictions": [[1.0, 2.0], [1.2, 1.9], [0.7, 2.4]], "data": [1.1, 2.1],
               "covariance": [[0.04, 0.0], [0.0, 0.09]]}
        for form in ("nnpdf", "giele-keller"):
            code, out = run(doc, "--weights", form, "--min-replicas", "2")
            self.assertEqual(code, 0, out)
            o = out["outputs"]
            d = np.array(doc["data"])
            t = np.array(doc["predictions"])
            chi2 = np.sum((d - t) ** 2 / np.array([0.04, 0.09]), axis=1)
            w = np.exp(-chi2 / 2) * (chi2 ** 0.5 if form == "nnpdf" else 1.0)  # (chi2)^((n-1)/2), n = 2
            w = w * 3 / w.sum()
            for got, exp in zip(o["weights"], w):
                self.assertAlmostEqual(got / exp, 1.0, delta=1e-12)
            neff = math.exp(sum(wk * math.log(3 / wk) for wk in w) / 3)
            self.assertAlmostEqual(o["N_eff"] / neff, 1.0, delta=1e-12)
            self.assertAlmostEqual(o["kish_ess"], w.sum() ** 2 / np.sum(w ** 2), delta=1e-12)

    def test_one_point_zero_chi2_is_finite(self):
        doc = {"set": "t", "kind": "replicas", "origin": "native-replicas", "predictions": [[1.0], [1.5], [0.5]],
               "data": [1.0], "covariance": [[0.04]]}
        code, out = run(doc, "--weights", "nnpdf", "--min-replicas", "2")
        self.assertEqual(code, 0, out)
        self.assertTrue(all(math.isfinite(v) for v in out["outputs"]["weights"]))

    def test_moves_toward_truth(self):
        doc, a = synthetic()
        code, out = run(doc, "--weights", "nnpdf", "--min-replicas", "100", "--min-neff", "50", "--unweight", "100")
        self.assertEqual(code, 0, out)
        o = out["outputs"]["observables"]["a"]
        self.assertLess(abs(o["reweighted"]["mean"] - 1.15), abs(o["prior"]["mean"] - 1.15))
        self.assertLess(o["reweighted"]["std"], o["prior"]["std"])
        self.assertEqual(len(out["outputs"]["unweighted_indices"]), 100)
        self.assertIn("alternative_method", out["outputs"])

    def test_low_neff_warns(self):
        doc, _ = synthetic(n_rep=200)
        doc["covariance"] = (np.array(doc["covariance"]) * 1e-4).tolist()  # very precise data: weights collapse
        code, out = run(doc, "--weights", "nnpdf", "--min-replicas", "100", "--min-neff", "50")
        self.assertEqual(code, 0)
        self.assertTrue(out["outputs"]["warnings"])

    def test_refusals_and_rejections(self):
        doc, _ = synthetic(n_rep=50)
        code, out = run(dict(doc, kind="hessian"), "--weights", "nnpdf", "--min-replicas", "10")
        self.assertEqual((code, out["status"]), (1, "refused"))
        code, out = run(dict(doc, origin="hessian-generated"), "--weights", "nnpdf", "--min-replicas", "10")
        self.assertEqual((code, out["status"]), (1, "refused"))
        code, out = run(dict(doc, origin="hessian-generated"), "--weights", "nnpdf", "--min-replicas", "10",
                        "--allow-hessian-replicas")
        self.assertEqual((code, out["status"]), (1, "refused"))  # review: only GK weights with chi2/Delta chi^2
        code, out = run(dict(doc, origin="hessian-generated"), "--weights", "giele-keller", "--min-replicas", "10",
                        "--allow-hessian-replicas")
        self.assertEqual(code, 2)  # the set's tolerance is required for the rescaling
        code, out = run(dict(doc, origin="hessian-generated", tolerance_delta_chi2=4.0), "--weights", "giele-keller",
                        "--min-replicas", "10", "--allow-hessian-replicas")
        self.assertEqual(code, 0, out)
        chi2 = np.array(out["outputs"]["chi2"])
        w = np.exp(-chi2 / 8.0)
        w = w * len(w) / w.sum()
        self.assertAlmostEqual(out["outputs"]["weights"][0] / w[0], 1.0, delta=1e-12)  # Paukkunen-Zurita Eq. 5.2
        code, out = run(doc, "--weights", "nnpdf", "--min-replicas", "100")
        self.assertEqual((code, out["status"]), (1, "refused"))  # fewer replicas than the user's minimum
        bad = dict(doc, covariance=[[1.0, 2.0, 0.0], [2.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        code, out = run(bad, "--weights", "nnpdf", "--min-replicas", "10")
        self.assertEqual((code, out["status"]), (1, "refused"))  # not positive definite
        code, _ = run(dict(doc, data=[1.0]), "--weights", "nnpdf", "--min-replicas", "10")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
