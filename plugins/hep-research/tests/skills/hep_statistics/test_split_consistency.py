"""split_consistency.py (S1): consistency of a measurement made on split samples (eras, halves, detectors).

For two splits d = x1 - x2 and Cov(d) = C1 + C2 - C12 - C21 (C12 the declared shared block), chi2 = d^T Cov(d)^-1 d
with n degrees of freedom; for K splits a generalized chi2 against a common value (GLS, (K - 1) n degrees of freedom)
and the pairwise tests with a Sidak or toy correction. Oracles: the two-split chi2 by hand; K = 2 generalized equals
the pairwise chi2; the subtraction of a shared block; the power for an injected offset against the noncentral chi2;
uniform p-values under the null (KS, slow tier: HEP_SLOW_TESTS=1). Inputs are SYNTHETIC."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "split_consistency.py"
sys.path.insert(0, str(SCRIPT.parent))
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"
NO_NUMPY = ("import runpy, sys; sys.modules['numpy'] = None; sys.argv = [sys.argv[1]] + sys.argv[2:]; "
            "runpy.run_path(sys.argv[0], run_name='__main__')")

try:
    import numpy as np
    from scipy import stats
except ImportError:  # pragma: no cover
    np = None


def run(doc, *args):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "in.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "--input", str(p), *args], capture_output=True,
                           text=True, timeout=600)
    return r.returncode, (json.loads(r.stdout) if r.stdout.strip().startswith("{") else {"raw": r.stdout + r.stderr})


C1 = [[0.04, 0.01, 0.0], [0.01, 0.09, 0.02], [0.0, 0.02, 0.16]]
C2 = [[0.05, 0.0, 0.0], [0.0, 0.08, 0.01], [0.0, 0.01, 0.10]]
SHARED = [[0.02, 0.0, 0.0], [0.0, 0.03, 0.0], [0.0, 0.0, 0.04]]


@unittest.skipIf(np is None, "NumPy and SciPy needed")
class TwoSplits(unittest.TestCase):
    def test_chi2_by_hand_without_shared_blocks(self):
        x1, x2 = [1.0, 2.0, 3.0], [1.3, 1.6, 3.5]
        code, out = run({"splits": [{"id": "a", "values": x1, "covariance": C1},
                                    {"id": "b", "values": x2, "covariance": C2}]})
        self.assertEqual(code, 0, out)
        d = np.subtract(x1, x2)
        chi2 = float(d @ np.linalg.solve(np.add(C1, C2), d))
        self.assertAlmostEqual(out["overall"]["chi2"], chi2, delta=1e-10)
        self.assertEqual(out["overall"]["ndf"], 3)
        self.assertAlmostEqual(out["overall"]["p_asymptotic"], float(stats.chi2.sf(chi2, 3)), delta=1e-12)
        self.assertIn("shared systematic uncertainties not subtracted", " ".join(out["warnings"]))
        self.assertEqual(out["status"], "ok")
        self.assertIsNone(out["verdict"])  # no --alpha: p-values only

    def test_shared_block_is_subtracted(self):
        x1, x2 = [1.0, 2.0, 3.0], [1.3, 1.6, 3.5]
        code, out = run({"splits": [{"id": "a", "values": x1, "covariance": C1},
                                    {"id": "b", "values": x2, "covariance": C2}],
                         "cross_covariance": [{"a": "a", "b": "b", "block": SHARED}]})
        self.assertEqual(code, 0, out)
        d = np.subtract(x1, x2)
        cov = np.add(C1, C2) - np.array(SHARED) - np.array(SHARED).T
        self.assertAlmostEqual(out["overall"]["chi2"], float(d @ np.linalg.solve(cov, d)), delta=1e-10)
        self.assertFalse([w for w in out["warnings"] if "not subtracted" in w])

    def test_verdict_and_exit_code_with_alpha(self):
        far = {"splits": [{"id": "a", "values": [1.0, 2.0, 3.0], "covariance": C1},
                          {"id": "b", "values": [2.0, 3.0, 4.0], "covariance": C2}]}
        code, out = run(far, "--alpha", "0.01")
        self.assertEqual((code, out["status"], out["verdict"]), (1, "fail", "inconsistent"))
        near = {"splits": [{"id": "a", "values": [1.0, 2.0, 3.0], "covariance": C1},
                           {"id": "b", "values": [1.01, 2.0, 3.0], "covariance": C2}]}
        code, out = run(near, "--alpha", "0.01")
        self.assertEqual((code, out["verdict"]), (0, "consistent"))

    def test_toy_p_value_agrees_with_asymptotic_for_gaussian_input(self):
        x1, x2 = [1.0, 2.0, 3.0], [1.3, 1.6, 3.5]
        code, out = run({"splits": [{"id": "a", "values": x1, "covariance": C1},
                                    {"id": "b", "values": x2, "covariance": C2}]}, "--toys", "20000", "--seed", "3")
        self.assertEqual(code, 0, out)
        p, pt = out["overall"]["p_asymptotic"], out["overall"]["p_toys"]
        self.assertAlmostEqual(pt, p, delta=4 * math.sqrt(p * (1 - p) / 20000) + 1e-4)
        self.assertEqual(out["overall"]["toys"], 20000)

    def test_power_for_an_injected_offset_matches_the_noncentral_chi2(self):
        import split_consistency as sc
        rng = np.random.default_rng(11)
        cov = np.add(C1, C2)
        delta = np.array([0.3, -0.2, 0.4])
        lam = float(delta @ np.linalg.solve(cov, delta))
        alpha = 0.05
        expected = float(stats.ncx2.sf(stats.chi2.isf(alpha, 3), 3, lam))
        n, hits = 4000, 0
        l1, l2 = np.linalg.cholesky(C1), np.linalg.cholesky(C2)
        for _ in range(n):
            x1 = l1 @ rng.standard_normal(3)
            x2 = l2 @ rng.standard_normal(3) - delta
            res = sc.analyse([{"id": "a", "values": x1.tolist(), "covariance": C1},
                              {"id": "b", "values": x2.tolist(), "covariance": C2}], [])
            hits += res["overall"]["p_asymptotic"] < alpha
        self.assertAlmostEqual(hits / n, expected, delta=4 * math.sqrt(expected * (1 - expected) / n))

    @unittest.skipUnless(SLOW, "slow (KS test of 20,000 null p-values): set HEP_SLOW_TESTS=1")
    def test_p_values_are_uniform_under_the_null(self):
        import split_consistency as sc
        rng = np.random.default_rng(5)
        shared = np.array(SHARED)
        joint = np.block([[np.array(C1), shared], [shared.T, np.array(C2)]])
        lj = np.linalg.cholesky(joint)
        ps = []
        for _ in range(20000):
            z = lj @ rng.standard_normal(6)
            res = sc.analyse([{"id": "a", "values": z[:3].tolist(), "covariance": C1},
                              {"id": "b", "values": z[3:].tolist(), "covariance": C2}],
                             [{"a": "a", "b": "b", "block": SHARED}])
            ps.append(res["overall"]["p_asymptotic"])
        self.assertGreater(stats.kstest(ps, "uniform").pvalue, 0.01)


@unittest.skipIf(np is None, "NumPy and SciPy needed")
class ManySplits(unittest.TestCase):
    def test_k2_generalized_equals_pairwise(self):
        doc = {"splits": [{"id": "a", "values": [1.0, 2.0, 3.0], "covariance": C1},
                          {"id": "b", "values": [1.3, 1.6, 3.5], "covariance": C2}],
               "cross_covariance": [{"a": "a", "b": "b", "block": SHARED}]}
        code, out = run(doc)
        self.assertEqual(code, 0, out)
        self.assertAlmostEqual(out["overall"]["chi2"], out["pairs"][0]["chi2"], delta=1e-9)

    def test_three_splits_generalized_chi2_and_sidak(self):
        x = [[1.0, 2.0, 3.0], [1.3, 1.6, 3.5], [0.8, 2.2, 2.7]]
        covs = [C1, C2, C1]
        doc = {"splits": [{"id": f"s{i}", "values": x[i], "covariance": covs[i]} for i in range(3)]}
        code, out = run(doc)
        self.assertEqual(code, 0, out)
        v = np.zeros((9, 9))
        for i in range(3):
            v[3 * i:3 * i + 3, 3 * i:3 * i + 3] = covs[i]
        h = np.vstack([np.eye(3)] * 3)
        y = np.concatenate([np.array(r) for r in x])
        vi = np.linalg.inv(v)
        mu = np.linalg.solve(h.T @ vi @ h, h.T @ vi @ y)
        r = y - h @ mu
        self.assertAlmostEqual(out["overall"]["chi2"], float(r @ vi @ r), delta=1e-9)
        self.assertEqual(out["overall"]["ndf"], 6)
        self.assertEqual(len(out["pairs"]), 3)
        pmin = min(p["p_asymptotic"] for p in out["pairs"])
        self.assertAlmostEqual(out["pairwise_global"]["p_sidak"], 1 - (1 - pmin) ** 3, delta=1e-12)

    def test_refusals(self):
        bad = [
            {"splits": [{"id": "a", "values": [1.0], "covariance": [[0.1]]}]},
            {"splits": [{"id": "a", "values": [1.0, 2.0], "covariance": [[0.1, 0], [0, 0.1]]},
                        {"id": "b", "values": [1.0], "covariance": [[0.1]]}]},
            {"splits": [{"id": "a", "values": [1.0], "covariance": [[0.1]]},
                        {"id": "a", "values": [1.0], "covariance": [[0.1]]}]},
            {"splits": [{"id": "a", "values": [1.0], "covariance": [[0.1]]},
                        {"id": "b", "values": [1.0], "covariance": [[0.1]]}],
             "cross_covariance": [{"a": "a", "b": "b", "block": [[0.2]]}]},  # Cov(d) not positive definite
            {"splits": [{"id": "a", "values": [1.0], "covariance": [[-0.1]]},
                        {"id": "b", "values": [1.0], "covariance": [[0.1]]}]},
        ]
        for doc in bad:
            with self.subTest(doc=doc):
                code, out = run(doc)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")

    def test_help_without_numpy(self):
        r = subprocess.run([sys.executable, "-c", NO_NUMPY, str(SCRIPT), "--help"], capture_output=True, text=True,
                           timeout=600)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--alpha", r.stdout)


if __name__ == "__main__":
    unittest.main()
