"""Path D (journey J5) regression tests: QED prediction vs SYNTHETIC reconstructed data, normalization fit.

One run with the default seed and toys; it must rerun byte for byte on the same machine, match the committed output
(floats to rel 1e-9 / abs 1e-12, since another platform's floating point differs in the last digits), pass every
pre-declared criterion, reject each mismatched variant, and keep the synthetic status along the contract trace."""
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "theory-comparison" / "run.py"
COMMITTED = PLUGIN / "examples" / "theory-comparison" / "output" / "results.json"

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    import matplotlib  # noqa: F401
    HAVE_DEPS = True
except ImportError:
    HAVE_DEPS = False


@unittest.skipUnless(HAVE_DEPS, "numpy, scipy and matplotlib are required (D5 environment)")
class PathDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("theory_comparison_run", SCRIPT)
        cls.m = importlib.util.module_from_spec(spec)
        sys.modules["theory_comparison_run"] = cls.m
        spec.loader.exec_module(cls.m)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "d"
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = cls.m.main(["--out", str(cls.out)])
        cls.r = json.loads((cls.out / "results.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_passes_predeclared_criteria(self):
        self.assertEqual(self.code, 0, self.r["pass"])

    def test_rerun_is_byte_identical(self):
        other = Path(self.tmp.name) / "d2"
        with contextlib.redirect_stdout(io.StringIO()):
            self.m.main(["--out", str(other)])
        h = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.out / "results.json", other / "results.json")]
        self.assertEqual(h[0], h[1])

    def test_reproduces_committed_output(self):
        def same(a, b, path="$"):
            if isinstance(a, float) or isinstance(b, float):
                self.assertTrue(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12), f"{path}: {a} != {b}")
            elif isinstance(a, dict) and isinstance(b, dict):
                self.assertEqual(sorted(a), sorted(b), path)
                for k in a:
                    same(a[k], b[k], f"{path}.{k}")
            elif isinstance(a, list) and isinstance(b, list):
                self.assertEqual(len(a), len(b), path)
                for i, (x, y) in enumerate(zip(a, b)):
                    same(x, y, f"{path}[{i}]")
            else:
                self.assertEqual(a, b, path)
        same(self.r, json.loads(COMMITTED.read_text()))

    def test_both_profiles_and_nothing_else(self):
        self.assertEqual(sorted(self.r["profiles_loaded"]), ["experiment:synthetic-collider", "theory:qed-benchmark"])

    def test_injection_closure(self):
        for k, a in self.r["asimov"].items():
            self.assertAlmostEqual(a["mu_hat"], float(k), places=8)
        self.assertIn("0.8", self.r["toy_results"])

    def test_every_variant_rejected_with_its_field(self):
        self.assertGreaterEqual(len(self.r["negative_variants"]), 9)
        for n in self.r["negative_variants"]:
            with self.subTest(n["name"]):
                self.assertTrue(n["rejected"])
                self.assertTrue(n["expected_field_reported"], n["mismatches"])
                self.assertTrue(all(x["resolve"] for x in n["mismatches"]))

    def test_contract_trace_keeps_synthetic_status(self):
        trace = {t["artifact"]: t for t in self.r["contract_trace"]}
        self.assertTrue(all("synthetic" in t["status"] for t in trace.values()))
        fit = trace["synthetic-path-d-mu-fit"]
        self.assertIn("artifacts/comparison_spec.json", fit["inputs"])
        self.assertIn("artifacts/folded_expectation.json", fit["inputs"])
        self.assertIn("../qed-prediction/output/artifacts/prediction.json", trace["synthetic-path-d-folded-expectation"]["inputs"])

    def test_no_new_physics_claim(self):
        text = (self.out / "report.md").read_text().lower()
        self.assertIn("no statement about new physics", text)
        self.assertNotIn("evidence for new physics", text)

    def test_gate_failure_stops_the_fit(self):
        bad = dict(self.m.plan(["migration", "efficiency"]))
        bad["mappings"] = []
        orig = self.m.plan
        try:
            self.m.plan = lambda inc: bad
            with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
                code = self.m.main(["--out", tmp, "--toys", "2"])
                self.assertEqual(code, 1)
                self.assertTrue((Path(tmp) / "gate_failure.json").exists())
                self.assertFalse((Path(tmp) / "results.json").exists())
        finally:
            self.m.plan = orig


@unittest.skipUnless(HAVE_DEPS, "numpy, scipy and matplotlib are required (D5 environment)")
class LowCountTests(unittest.TestCase):
    """AC17: low and zero counts in the Path D likelihood (no Gaussian approximation, empty bins allowed)."""

    def test_zero_and_low_count_bins(self):
        spec = importlib.util.spec_from_file_location("theory_comparison_run_low", SCRIPT)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        a = [0.4, 0.3, 0.2, 0.1, 0.5, 0.5]
        fit = m.Model([0, 1, 0, 0, 2, 0], a, 0.02, 5.8e-4).fit()
        self.assertAlmostEqual(fit["mu_hat"], 3 / 2.0, places=12)
        lo, hi = fit["interval_68"]
        self.assertGreater(lo, 0.0)
        self.assertGreater(hi - fit["mu_hat"], fit["mu_hat"] - lo)  # Poisson asymmetry is kept


if __name__ == "__main__":
    unittest.main()
