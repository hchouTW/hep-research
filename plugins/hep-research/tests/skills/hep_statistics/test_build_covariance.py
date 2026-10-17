"""S3: build_covariance.py, a covariance proposal from declared correlation models. Oracles: every kernel is positive
semi-definite; `full` equals the outer product; the time-series recipe of test_time_series_covariance.py is reproduced
(none + full relative + exp-time) and passes core/stats/validate_covariance.py; an invalid user correlation is
refused; the ell scan reports chi2 values that match a direct computation. Inputs are SYNTHETIC."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "build_covariance.py"
VALIDATOR = PLUGIN / "core" / "stats" / "validate_covariance.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import numpy as np
    HAVE_NP = True
except ImportError:  # pragma: no cover
    HAVE_NP = False


def run(*args, doc=None):
    with tempfile.TemporaryDirectory() as d:
        argv = [str(a) for a in args]
        if doc is not None:
            p = Path(d) / "in.json"
            p.write_text(json.dumps(doc), encoding="utf-8")
            argv = [a.replace("@IN", str(p)).replace("@DIR", d) for a in argv]
        cp = subprocess.run([sys.executable, "-B", str(SCRIPT), *argv], capture_output=True, text=True, timeout=600)
        extra = {}
        out_path = Path(d) / "cov.json"
        if out_path.exists():
            extra["file"] = json.loads(out_path.read_text(encoding="utf-8"))
    out = json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else {"raw": cp.stdout, "err": cp.stderr}
    return cp.returncode, out, extra


def series(n=12):
    t = [float(i) for i in range(n)]
    x = [10 ** (0.1 * i) for i in range(n)]
    v = [100.0 * (1.0 + 0.2 * math.sin(2 * math.pi * ti / 11.0)) for ti in t]
    return t, x, v


@unittest.skipUnless(HAVE_NP, "numpy needed")
class Kernels(unittest.TestCase):
    def doc(self, sources, **kw):
        t, x, v = series()
        return dict({"x": x, "times": t, "values": v, "sources": sources}, **kw)

    def test_every_kernel_is_psd_and_labeled_proposal(self):
        n = 12
        corr = np.eye(n) * 0.5 + 0.5
        sources = [{"name": "stat", "model": "none", "relative": 0.01},
                   {"name": "norm", "model": "full", "relative": 0.05},
                   {"name": "scale", "model": "length", "relative": 0.02, "length": 0.4},
                   {"name": "pivot", "model": "antisymmetric", "relative": 0.01, "pivot": 3.0},
                   {"name": "ar", "model": "ar1", "sigma": 1.0, "rho": 0.6},
                   {"name": "drift", "model": "exp-time", "relative": 0.02, "tau": 3.0},
                   {"name": "user", "model": "matrix", "sigma": 0.5, "correlation": corr.tolist()}]
        code, out, _ = run("build", "--input", "@IN", doc=self.doc(sources))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["label"], "[Proposal]")
        self.assertEqual(out["status_label"], "unvalidated")
        for name, block in out["blocks"].items():
            with self.subTest(source=name):
                b = np.array(block)
                self.assertTrue(np.allclose(b, b.T))
                self.assertGreaterEqual(np.linalg.eigvalsh(b).min(), -1e-9 * max(1.0, np.abs(b).max()))
                self.assertTrue(out["checks"][name]["psd"])
        total = np.array(out["total"])
        self.assertTrue(np.allclose(total, sum(np.array(b) for b in out["blocks"].values())))

    def test_full_equals_outer_product_and_none_is_diagonal(self):
        _, _, v = series()
        code, out, _ = run("build", "--input", "@IN", doc=self.doc([{"name": "norm", "model": "full", "relative": 0.05},
                                                                   {"name": "stat", "model": "none", "sigma": 2.0}]))
        self.assertEqual(code, 0, out)
        a = 0.05 * np.array(v)
        self.assertTrue(np.allclose(np.array(out["blocks"]["norm"]), np.outer(a, a), rtol=1e-12, atol=0))
        self.assertTrue(np.allclose(np.array(out["blocks"]["stat"]), 4.0 * np.eye(12)))

    def test_length_ar1_antisymmetric_shapes(self):
        t, x, v = series()
        code, out, _ = run("build", "--input", "@IN", doc=self.doc([
            {"name": "len", "model": "length", "sigma": 1.0, "length": 0.5},
            {"name": "ar", "model": "ar1", "sigma": 1.0, "rho": 0.6},
            {"name": "anti", "model": "antisymmetric", "sigma": 1.0, "pivot": 3.0}]))
        self.assertEqual(code, 0, out)
        lx = np.log(x)
        self.assertTrue(np.allclose(out["blocks"]["len"], np.exp(-np.abs(np.subtract.outer(lx, lx)) / 0.5)))
        i = np.arange(12)
        ar = np.array(out["blocks"]["ar"])
        self.assertTrue(np.allclose(ar, 0.6 ** np.abs(np.subtract.outer(i, i))))
        inv = np.linalg.inv(ar)  # AR(1): the inverse is tridiagonal
        self.assertLess(np.abs(np.triu(inv, 2)).max(), 1e-9)
        s = np.where(np.array(x) < 3.0, 1.0, -1.0)
        self.assertTrue(np.allclose(out["blocks"]["anti"], np.outer(s, s)))

    def test_time_series_recipe_is_reproduced_and_validates(self):
        from test_time_series_covariance import build_time_covariance, synthetic_series
        t, flux, stat = synthetic_series()
        blocks, total = build_time_covariance(flux, stat, [0.03], [(0.02, 4.0)], t)
        doc = {"times": t.tolist(), "values": flux.tolist(), "sources": [
            {"name": "stat", "model": "none", "sigma": stat.tolist()},
            {"name": "tind", "model": "full", "relative": 0.03},
            {"name": "tdep", "model": "exp-time", "relative": 0.02, "tau": 4.0}]}
        code, out, extra = run("build", "--input", "@IN", "--out", "@DIR/cov.json", doc=doc)
        self.assertEqual(code, 0, out)
        self.assertTrue(np.allclose(np.array(out["total"]), total, rtol=1e-12, atol=1e-12))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "cov.json"
            p.write_text(json.dumps(extra["file"]), encoding="utf-8")
            cp = subprocess.run([sys.executable, "-B", str(VALIDATOR), str(p)], capture_output=True, text=True,
                                timeout=300)
        self.assertEqual(cp.returncode, 0, cp.stdout[-800:])

    def test_invalid_correlation_is_refused(self):
        n = 12
        corr = np.eye(n) + 0.7 * (np.eye(n, k=1) + np.eye(n, k=-1))  # nearest neighbour 0.7: not PSD
        code, out, _ = run("build", "--input", "@IN", doc=self.doc([{"name": "nn", "model": "matrix", "sigma": 1.0,
                                                                     "correlation": corr.tolist()}]))
        self.assertEqual(code, 1, out)
        self.assertEqual(out["status"], "failed")
        self.assertFalse(out["checks"]["nn"]["psd"])

    def test_scan_over_length(self):
        t, x, v = series()
        res = [0.5 * ((-1) ** i) for i in range(12)]
        doc = self.doc([{"name": "stat", "model": "none", "sigma": 1.0},
                        {"name": "scale", "model": "length", "sigma": 1.0, "length": 0.4}], residuals=res)
        code, out, _ = run("scan", "--input", "@IN", "--source", "scale", "--lengths", "0.1,0.5,2", doc=doc)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["label"], "[Proposal]")
        self.assertEqual([r["length"] for r in out["scan"]], [0.1, 0.5, 2.0])
        lx = np.log(x)
        for row in out["scan"]:
            c = np.eye(12) + np.exp(-np.abs(np.subtract.outer(lx, lx)) / row["length"])
            r = np.array(res)
            self.assertAlmostEqual(row["chi2"], float(r @ np.linalg.solve(c, r)), delta=1e-9)

    def test_bad_input_exits_2(self):
        for doc in ({"values": [1.0], "sources": [{"name": "a", "model": "nope", "sigma": 1.0}]},
                    {"values": [1.0, 2.0], "sources": [{"name": "a", "model": "length", "sigma": 1.0, "length": 1.0}]},
                    {"values": [1.0, 2.0], "sources": [{"name": "a", "model": "full"}]},
                    {"values": [1.0, 2.0], "sources": []}):
            with self.subTest(doc=doc):
                code, out, _ = run("build", "--input", "@IN", doc=doc)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
