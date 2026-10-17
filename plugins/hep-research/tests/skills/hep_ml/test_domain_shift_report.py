"""ML4: domain_shift_report.py. Oracles: for identical distributions the classifier AUC is within its statistical range
around 0.5 and the per-feature p-values are uniform (slow tier for the uniformity scan); an injected shift is found and
attributed to the right feature; the domain_shift block is accepted by write_ml_artifact.py's schema; the per-period
breakdown isolates the shifted period. All inputs are SYNTHETIC."""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-ml" / "scripts" / "domain_shift_report.py"
sys.path.insert(0, str(ROOT))
try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


def write(path, cols):
    names = list(cols)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(names)
        for row in zip(*(cols[n] for n in names)):
            w.writerow([f"{v:.10g}" if isinstance(v, float) else v for v in row])


def sample(rng, n, shift=0.0, period=None):
    x = rng.normal(0, 1, n)
    y = rng.normal(0, 1, n) + shift
    z = rng.exponential(1.0, n)
    cols = {"x": x.tolist(), "y": y.tolist(), "z": z.tolist(), "run": [int(i // 50) for i in range(n)]}
    if period is not None:
        cols["period"] = period
    return cols


@unittest.skipIf(np is None, "numpy is not installed")
class DomainShiftReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def files(self, shift=0.0, seed=1, n=2000, periods=False):
        rng = np.random.default_rng(seed)
        ref, tgt = self.d / "ref.csv", self.d / "tgt.csv"
        write(ref, sample(rng, n))
        if periods:
            a = sample(rng, n // 2, 0.0, ["p1"] * (n // 2))
            b = sample(rng, n // 2, shift, ["p2"] * (n // 2))
            write(tgt, {k: a[k] + b[k] for k in a})
        else:
            write(tgt, sample(rng, n, shift))
        return ref, tgt

    def args(self, ref, tgt, *extra):
        return ("--reference", ref, "--target", tgt, "--features", "x,y,z", "--group-column", "run",
                "--control-sample", "SYNTHETIC control region", "--seed", "3", *extra)

    def test_identical_distributions_show_no_shift(self):
        ref, tgt = self.files(0.0)
        code, out, err = run(*self.args(ref, tgt))
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "ok")
        self.assertFalse(out["shift_detected"])
        c = out["classifier_test"]
        self.assertLess(abs(c["auc"] - 0.5), 3 * c["auc_sigma_null"])
        self.assertEqual(out["status_label"], "unvalidated")

    def test_injected_shift_is_found_and_attributed(self):
        ref, tgt = self.files(0.25)
        code, out, err = run(*self.args(ref, tgt))
        self.assertEqual(code, 1, err)
        self.assertTrue(out["shift_detected"])
        self.assertEqual(out["drivers"][0], "y")
        self.assertNotIn("x", out["drivers"])
        self.assertGreater(out["classifier_test"]["z"], 3)
        y = out["features"]["y"]
        self.assertLess(y["ks"]["p"], 1e-3)
        self.assertAlmostEqual(y["wasserstein"], 0.25, delta=0.08)

    def test_domain_shift_block_is_accepted_by_the_ml_artifact_schema(self):
        ref, tgt = self.files(0.25)
        block = self.d / "ds.json"
        code, out, err = run(*self.args(ref, tgt, "--domain-shift-out", block))
        self.assertEqual(code, 1, err)
        ds = json.loads(block.read_text())["domain_shift"]
        self.assertEqual(ds["control_sample"], "SYNTHETIC control region")
        self.assertEqual(ds["status"], "checked")
        self.assertNotIn("outcome", ds)  # what was done about the shift is the analyst's declaration
        schema = json.loads((ROOT / "contracts" / "schemas" / "ext_ml_artifact.json").read_text())["properties"]["domain_shift"]
        for key in schema["required"]:
            self.assertIn(key, ds)
        code, out, err = run(*self.args(ref, tgt, "--domain-shift-out", block, "--outcome", "uncorrected"))
        self.assertEqual(code, 2)  # uncorrected needs --nuisance
        code, out, err = run(*self.args(ref, tgt, "--domain-shift-out", block, "--outcome", "bounded-by-nuisance",
                                        "--nuisance", "ml_shift"))
        self.assertEqual(code, 1, err)
        self.assertEqual(json.loads(block.read_text())["domain_shift"]["nuisance"], "ml_shift")

    def test_per_period_breakdown(self):
        ref, tgt = self.files(0.4, periods=True)
        code, out, err = run(*self.args(ref, tgt, "--period-column", "period"))
        self.assertEqual(code, 1, err)
        per = out["periods"]
        self.assertLess(per["p2"]["y"]["ks_p"], 1e-3)
        self.assertGreater(per["p1"]["y"]["ks_p"], 1e-3)

    def test_bad_input(self):
        ref, tgt = self.files(0.0)
        for args in (self.args(ref, tgt, "--folds", "1"), ("--reference", ref, "--target", tgt, "--features", "nope",
                                                            "--control-sample", "c")):
            with self.subTest(args=args):
                code, out, _ = run(*args)
                self.assertEqual(code, 2)
                self.assertEqual(out["status"], "rejected")

    @unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
    def test_slow_p_values_uniform_under_the_null(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import domain_shift_report as dsr
        rng = np.random.default_rng(11)
        ps = []
        for _ in range(400):
            a, b = rng.normal(0, 1, 500), rng.normal(0, 1, 500)
            ps.append(dsr.ks_test(a, np.ones(500), b, np.ones(500))["p"])
        ps = np.sort(ps)
        d = np.max(np.abs(ps - (np.arange(1, 401) - 0.5) / 400))
        self.assertLess(d, 1.36 / np.sqrt(400) + 0.02)


if __name__ == "__main__":
    unittest.main()
