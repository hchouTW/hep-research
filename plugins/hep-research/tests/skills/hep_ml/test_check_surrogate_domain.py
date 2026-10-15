"""Tests for skills/hep-ml/scripts/check_surrogate_domain.py.

The script was rewritten after an external review measured two failures of the old per-feature-box + range-scaled
nearest-neighbour method: a 20-D query at Mahalanobis distance ~8.9 from 800 standard-normal training points was
reported 'inside', and an in-distribution point was reported 'outside' because one coordinate left the box. The old
tests here (a 16-point ring with --factor) encoded that method: --factor and "spacing_threshold" are gone, the box is
a diagnostic unless --box-strict, and thresholds are calibrated quantiles, which need enough training points (a
16-point ring is now an input error). They are replaced by the cases below.
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-ml" / "scripts" / "check_surrogate_domain.py"
sys.path.insert(0, str(SCRIPT.parent))
import check_surrogate_domain as csd  # noqa: E402


def names(d):
    return [f"x{i}" for i in range(d)]


def run_main(payload, *extra):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "d.json"
        path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = csd.main([str(path), *extra])
        return code, json.loads(buf.getvalue())


class MeasuredFailureTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(20)
        self.train = self.rng.standard_normal((800, 20))

    def test_20d_far_query_is_outside(self):
        rep = csd.check({"features": names(20), "training": self.train.tolist(), "queries": [[2.0] * 20]})
        q = rep["queries"][0]
        self.assertGreater(q["mahalanobis"], 8.0)
        self.assertEqual(q["status"], "outside")
        self.assertEqual(q["outside_features"], [])  # inside every per-feature range: the old method said 'inside'
        self.assertFalse(rep["passed"])

    def test_in_distribution_false_positive_rate(self):
        draws = self.rng.standard_normal((200, 20))
        rep = csd.check({"features": names(20), "training": self.train.tolist(), "queries": draws.tolist()},
                        quantile=0.99)
        flagged = sum(q["status"] != "inside" for q in rep["queries"])
        self.assertLessEqual(flagged / 200, 0.03)
        self.assertLessEqual(rep["estimated_false_positive_rate"], 0.05)
        self.assertEqual(rep["n_held_out"], 160)

    def test_one_coordinate_outside_the_box_is_not_outside_unless_strict(self):
        query = [0.0] * 20
        query[3] = float(self.train[:, 3].max()) + 0.05  # just past the range in one feature, typical elsewhere
        rep = csd.check({"features": names(20), "training": self.train.tolist(), "queries": [query]})
        self.assertEqual(rep["queries"][0]["outside_features"], ["x3"])
        self.assertEqual(rep["queries"][0]["status"], "inside")
        self.assertTrue(any("diagnostic" in r for r in rep["queries"][0]["reasons"]))
        strict = csd.check({"features": names(20), "training": self.train.tolist(), "queries": [query]},
                           box_strict=True)
        self.assertEqual(strict["queries"][0]["status"], "outside")


class GeometryTests(unittest.TestCase):
    def test_off_the_correlation_ridge_is_outside(self):
        rng = np.random.default_rng(1)
        a = rng.standard_normal(1000)
        train = np.c_[a, a + 0.05 * rng.standard_normal(1000)]
        rep = csd.check({"features": ["a", "b"], "training": train.tolist(), "queries": [[1.0, -1.0], [1.0, 1.0]]})
        off, on = rep["queries"]
        self.assertEqual(off["outside_features"], [])  # inside the per-feature box
        self.assertEqual(off["status"], "outside")
        self.assertEqual(on["status"], "inside")

    def test_exact_linear_constraint_is_checked_through_the_dropped_direction(self):
        rng = np.random.default_rng(2)
        a, b = rng.standard_normal(500), rng.standard_normal(500)
        rep = csd.check({"features": ["a", "b", "sum"], "training": np.c_[a, b, a + b].tolist(),
                         "queries": [[0.5, 0.5, 1.0], [0.5, 0.5, 0.0]]})
        self.assertEqual(rep["dropped_directions"], 1)
        self.assertEqual([q["status"] for q in rep["queries"]], ["inside", "outside"])

    def test_constant_feature_does_not_crash_and_is_reported(self):
        rng = np.random.default_rng(3)
        train = np.c_[rng.standard_normal(200), np.full(200, 3.0), rng.standard_normal(200)]
        code, rep = run_main({"features": ["a", "c", "b"], "training": train.tolist(),
                              "queries": [[0.1, 3.0, -0.2], [0.1, 4.0, -0.2]]})
        self.assertEqual(code, 1)
        self.assertEqual(rep["constant_features"], ["c"])
        self.assertEqual([q["status"] for q in rep["queries"]], ["inside", "outside"])
        self.assertEqual(rep["queries"][1]["constant_feature_mismatch"], ["c"])

    def test_hole_in_the_training_data_is_sparse(self):
        rng = np.random.default_rng(4)
        grid = np.array([[i, j] for i in np.linspace(0, 1, 30) for j in np.linspace(0, 1, 30)
                         if not (0.3 < i < 0.7 and 0.3 < j < 0.7)])
        train = grid + rng.uniform(-0.005, 0.005, grid.shape)
        code, rep = run_main({"features": ["a", "b"], "training": train.tolist(),
                              "queries": [[0.1, 0.1], [0.5, 0.5], [3.0, 0.5]]})
        self.assertEqual(code, 1)
        self.assertEqual([q["status"] for q in rep["queries"]], ["inside", "sparse", "outside"])

    def test_3000_points_are_fast(self):
        rng = np.random.default_rng(5)
        payload = {"features": names(10), "training": rng.standard_normal((3000, 10)).tolist(),
                   "queries": rng.standard_normal((500, 10)).tolist()}
        start = time.perf_counter()
        rep = csd.check(payload)
        self.assertLess(time.perf_counter() - start, 5.0)
        self.assertEqual(rep["n_training"], 3000)

    def test_deterministic_for_a_seed(self):
        rng = np.random.default_rng(6)
        payload = {"features": names(3), "training": rng.standard_normal((300, 3)).tolist(), "queries": [[0, 0, 0]]}
        self.assertEqual(csd.check(payload, seed=4), csd.check(payload, seed=4))


class CliTests(unittest.TestCase):
    def test_box_only_domain(self):
        code, rep = run_main({"features": ["a"], "training_domain": {"a": [0, 1]}, "queries": [[0.5], [2.0]]})
        self.assertEqual(code, 1)
        self.assertEqual(rep["method"], "box-only")
        self.assertEqual([q["status"] for q in rep["queries"]], ["inside", "outside"])
        self.assertIn("box-only", rep["note"])

    def test_all_inside_is_exit_0(self):
        rng = np.random.default_rng(7)
        code, rep = run_main({"features": names(2), "training": rng.standard_normal((200, 2)).tolist(),
                              "queries": [[0.0, 0.1]]})
        self.assertEqual((code, rep["passed"]), (0, True))

    def test_bad_input_is_exit_2_with_a_json_error(self):
        rng = np.random.default_rng(8)
        train = rng.standard_normal((100, 2)).tolist()
        cases = {
            "not json": "{not json",
            "no training": {"features": ["a"], "queries": [[0.1]]},
            "features not a list": {"features": 3, "training": [[1]], "queries": [[1]]},
            "query dimension mismatch": {"features": ["a", "b"], "training": train, "queries": [[0.1]]},
            "query too long": {"features": ["a", "b"], "training": train, "queries": [[0.1, 0.2, 0.3]]},
            "training dimension mismatch": {"features": ["a", "b"], "training": train + [[1.0]], "queries": [[0, 0]]},
            "non-finite": {"features": ["a", "b"], "training": train, "queries": [[0.1, "x"]]},
            "too few points": {"features": ["a", "b"], "training": train[:16], "queries": [[0, 0]]},
        }
        for name, payload in cases.items():
            with self.subTest(name):
                code, rep = run_main(payload)
                self.assertEqual(code, 2)
                self.assertIn("error", rep)

    def test_numerical_failure_is_exit_3_not_1(self):
        rng = np.random.default_rng(9)
        train = (rng.standard_normal((100, 2)) * 1e300).tolist()  # covariance overflows
        code, rep = run_main({"features": ["a", "b"], "training": train, "queries": [[0.0, 0.0]]})
        self.assertEqual(code, 3)
        self.assertIn("numerical", rep["error"])

    def test_missing_file_through_the_command_line(self):
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "/nonexistent/domain.json"], capture_output=True,
                             text=True, timeout=600)
        self.assertEqual(res.returncode, 2)
        self.assertIn("error", json.loads(res.stdout))
        self.assertNotIn("Traceback", res.stderr)


if __name__ == "__main__":
    unittest.main()
