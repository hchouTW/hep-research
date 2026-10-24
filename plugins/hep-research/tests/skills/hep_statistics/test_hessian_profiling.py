"""hessian_profiling.py (S12): linear Hessian profiling against the exact weighted least-squares solution.

Toy: predictions linear in the eigenvector coordinates z, y(z) = y0 + D z, with the set's prior chi2_0 + sum z_k^2 /
Delta chi^2 ... in the w = z/t parametrization the profiled minimum is the exact solution of the stacked least-squares
problem [C^-1/2 D; t I] w = [C^-1/2 (y - y0); 0]. Tolerances fixed before comparing: 1e-10 relative.
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
SCRIPT = ROOT / "skills/hep-statistics/scripts/hessian_profiling.py"


def run(doc):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "in.json"
        p.write_text(json.dumps(doc))
        r = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True, timeout=120)
    return r.returncode, json.loads(r.stdout)


def toy(tol=4.0):
    rng = np.random.default_rng(5)
    n, K = 6, 3
    y0 = rng.uniform(1, 2, n)
    D = rng.normal(0, 0.1, (n, K))
    members = [y0]
    for k in range(K):
        members += [y0 + D[:, k], y0 - D[:, k]]
    obs_d = rng.normal(0, 0.05, K)
    obs = [1.0] + [v for k in range(K) for v in (1.0 + obs_d[k], 1.0 - obs_d[k])]
    data = y0 + D @ np.array([0.8, -0.5, 0.2])
    cov = np.diag(rng.uniform(0.01, 0.02, n) ** 2)
    return {"set": "toy", "error_type": "hessian", "tolerance_delta_chi2": tol, "members": np.array(members).tolist(),
            "data": data.tolist(), "covariance": cov.tolist(), "observables": {"O": obs}}, y0, D, data, cov, obs_d


class Profiling(unittest.TestCase):
    def test_equals_exact_weighted_least_squares(self):
        doc, y0, D, data, cov, obs_d = toy()
        code, out = run(doc)
        self.assertEqual(code, 0, out)
        t = math.sqrt(4.0)
        L = np.linalg.cholesky(np.linalg.inv(cov))
        A = np.vstack([L.T @ D, t * np.eye(D.shape[1])])
        b = np.concatenate([L.T @ (data - y0), np.zeros(D.shape[1])])
        w_exact = np.linalg.lstsq(A, b, rcond=None)[0]
        for got, exp in zip(out["outputs"]["w_min"], w_exact):
            self.assertAlmostEqual(got, exp, delta=1e-10)
        o = out["outputs"]["observables"]["O"]
        self.assertAlmostEqual(o["central_after"], 1.0 + obs_d @ w_exact, delta=1e-10)
        B = D.T @ np.linalg.inv(cov) @ D + t * t * np.eye(3)
        self.assertAlmostEqual(o["uncertainty_after"], t * math.sqrt(obs_d @ np.linalg.inv(B) @ obs_d), delta=1e-12)
        self.assertLess(o["uncertainty_after"], o["symmetric_uncertainty_before"])
        self.assertAlmostEqual(out["outputs"]["linearity_max_relative_asymmetry"], 0.0, delta=1e-9)

    def test_no_constraint_keeps_the_set(self):
        doc, *_ = toy()
        doc["covariance"] = (np.array(doc["covariance"]) * 1e12).tolist()  # data carry no information
        _, out = run(doc)
        o = out["outputs"]["observables"]["O"]
        self.assertAlmostEqual(o["uncertainty_after"] / o["symmetric_uncertainty_before"], 1.0, delta=1e-6)
        self.assertAlmostEqual(o["central_after"], 1.0, delta=1e-6)

    def test_dynamic_tolerance_skips_the_fixed_tolerance_verdict(self):
        # review: with a dynamic tolerance the single-Delta chi^2 interpretation is lost (Paukkunen and Zurita, p. 4)
        doc, *_ = toy()
        doc["dynamic_tolerance"] = [[1.0, 1.0], [5.0, 5.0], [3.0, 3.0]]
        doc["covariance"] = (np.array(doc["covariance"]) * 1e10).tolist()  # no information
        code, out = run(doc)
        self.assertEqual(code, 0, out)
        o = out["outputs"]
        self.assertIsNone(o["observables"]["O"]["uncertainty_after"])
        self.assertIn("dynamic", o["consistency"])

    def test_refusals(self):
        doc, *_ = toy()
        code, out = run(dict(doc, error_type="replicas"))
        self.assertEqual((code, out["status"]), (1, "refused"))
        code, out = run(dict(doc, members=doc["members"][:-1]))  # 1 + 5 members: odd count after the central one
        self.assertEqual((code, out["status"]), (1, "refused"))
        code, _ = run(dict(doc, members=doc["members"]))  # 1 + 6: valid (LHAPDF counts the central member)
        self.assertEqual(code, 0)
        bad = np.array(doc["covariance"])
        bad[0, 1] = bad[1, 0] = 10.0
        code, out = run(dict(doc, covariance=bad.tolist()))
        self.assertEqual((code, out["status"]), (1, "refused"))


if __name__ == "__main__":
    unittest.main()
