"""Time budgets for the covariance and response validators (T17; slow tier, HEP_SLOW_TESTS=1).

Recorded on the reference Mac (Apple Silicon, Python 3.13, NumPy 2.5): validate_covariance at n = 120 took 1.6 s with
the pure-Python Jacobi rotations (6.9 s in the review's Linux container) and 0.011 s with numpy.linalg.eigh. The
budgets leave room for slower machines; a failure means a change made the validators asymptotically slower."""
import os
import random
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats.validate_covariance import validate_covariance  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402

SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"
try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False


def covariance_doc(n, seed=1):
    rng = random.Random(seed)
    a = [[rng.gauss(0, 1) for _ in range(n)] for _ in range(n)]
    c = [[sum(a[i][k] * a[j][k] for k in range(n)) + (n if i == j else 0) for j in range(n)] for i in range(n)]
    return {"kind": "absolute", "units": "x^2", "labels": [f"b{i}" for i in range(n)], "matrix": c}


def timed(fn, *args):
    start = time.perf_counter()
    out = fn(*args)
    return out, time.perf_counter() - start


@unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
class ValidatorBudgets(unittest.TestCase):
    @unittest.skipUnless(HAVE_NUMPY, "NumPy not installed: only the pure-Python budget applies")
    def test_numpy_path(self):
        for n, budget in ((120, 0.5), (400, 5.0)):
            out, seconds = timed(validate_covariance, covariance_doc(n))
            self.assertEqual(out["metrics"]["total"]["eigen_solver"], "numpy.linalg.eigh")
            self.assertLess(seconds, budget, f"n = {n}: {seconds:.3f} s, budget {budget} s")

    def test_pure_python_path(self):
        os.environ["HEP_STATS_PURE_PYTHON"] = "1"
        try:
            out, seconds = timed(validate_covariance, covariance_doc(60))
        finally:
            del os.environ["HEP_STATS_PURE_PYTHON"]
        self.assertEqual(out["metrics"]["total"]["eigen_solver"], "jacobi")
        self.assertLess(seconds, 5.0, f"n = 60 by rotations: {seconds:.3f} s, budget 5 s")

    def test_response_validator(self):
        import copy
        import json
        n = 80
        doc = copy.deepcopy(json.loads((ROOT / "tests" / "core" / "fixtures" / "response_valid.json").read_text()))
        edges = [float(k + 1) for k in range(n + 1)]
        doc["metadata"]["truth_axis"]["edges"] = doc["metadata"]["reco_axis"]["edges"] = edges
        doc["matrix"] = [[0.6 if i == j else 0.1 if abs(i - j) == 1 else 0.0 for j in range(n)] for i in range(n)]
        for key in list(doc):
            if key not in ("metadata", "matrix"):
                doc.pop(key)
        out, seconds = timed(validate_response, doc)
        self.assertIn("numerical_rank", out["metrics"], out["errors"])  # the eigenvalue step ran
        self.assertLess(seconds, 5.0, f"response n = {n}: {seconds:.3f} s, budget 5 s")


if __name__ == "__main__":
    unittest.main()
