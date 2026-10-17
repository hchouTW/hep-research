"""mix_period_responses.py (D5): era responses mixed per truth bin with weights w_tj = A_tj T_tj, or stacked for a
joint fit. Oracles: folding the mixed response with the summed weights equals the sum of the per-period folds to 1e-12;
the stacked matrix recovers a synthetic truth; mismatched axes or conventions, a zero total weight and negative
weights are refused; the weight source's checksum is recorded. Responses come from build_response.py on SYNTHETIC
events."""
import csv
import hashlib
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills" / "hep-detector" / "scripts"
MIX = SCRIPTS / "mix_period_responses.py"
BUILD = SCRIPTS / "build_response.py"
TRUTH = ["0", "10", "20", "30"]
RECO = ["0", "5", "10", "15", "20", "25", "30"]


def run(script, *args):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout
    return p.returncode, out, p.stderr


def make_response(d: Path, name: str, sigma: float, seed: int, eff: float, reco=RECO, normalization="conditional_on_generated"):
    rng = random.Random(seed)
    ev = d / f"{name}.csv"
    with open(ev, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["truth", "reco", "selected"])
        for _ in range(6000):
            t = rng.uniform(0, 30)
            sel = rng.random() < eff
            w.writerow([t, t + rng.gauss(0, sigma) if sel else "", int(sel)])
    out = d / f"{name}.json"
    code, rep, err = run(BUILD, "build", ev, "--truth-col", "truth", "--reco-col", "reco", "--unweighted",
                         "--selected-col", "selected", "--truth-edges", *TRUTH, "--reco-edges", *reco, "--variable", "x",
                         "--unit", "GeV", "--normalization", normalization, "--acceptance", "outside_matrix",
                         "--residual", "difference", "--intended-use", "unfolding", "--artifact-id", f"resp-{name}",
                         "--objective", "SYNTHETIC era response", "--created", "2026-10-17", "--out", out)
    assert code == 0, (err, rep)
    return out


def matvec(m, v):
    return [sum(m[i][j] * v[j] for j in range(len(v))) for i in range(len(m))]


class MixPeriodResponses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.d = Path(cls.tmp.name)
        cls.r1 = make_response(cls.d, "era1", 3.0, 1, 0.8)
        cls.r2 = make_response(cls.d, "era2", 1.5, 2, 0.9)  # an added layer: better resolution, higher efficiency
        cls.weights = cls.d / "weights.json"
        cls.weights.write_text(json.dumps({"source": "SYNTHETIC acceptance x collection time",
                                           "periods": {"era1": {"acceptance": [0.30, 0.32, 0.33],
                                                                "collection_time": [1000.0, 1200.0, 1300.0]},
                                                       "era2": {"acceptance": 0.40,
                                                                "collection_time": [500.0, 450.0, 400.0]}}}))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def mix(self, *extra, weights=None, periods=None):
        out = self.d / "mixed.json"
        periods = periods or [f"era1={self.r1}", f"era2={self.r2}"]
        args = ["mix"] + sum((["--period", p] for p in periods), []) + [
            "--weights", weights or self.weights, "--artifact-id", "mixed", "--objective", "SYNTHETIC mixed response",
            "--created", "2026-10-17", "--out", out, *extra]
        code, rep, err = run(MIX, *args)
        return code, rep, err, out

    def test_fold_of_the_mix_equals_the_sum_of_period_folds(self):
        code, rep, err, out = self.mix()
        self.assertEqual(code, 0, err + json.dumps(rep)[:1500])
        self.assertEqual(rep["status"], "ok")
        mixed = json.loads(out.read_text())["extension"]
        e1 = json.loads(self.r1.read_text())["extension"]
        e2 = json.loads(self.r2.read_text())["extension"]
        w1 = [0.30 * 1000.0, 0.32 * 1200.0, 0.33 * 1300.0]
        w2 = [0.40 * 500.0, 0.40 * 450.0, 0.40 * 400.0]
        phi = [5.0, 2.5, 1.0]
        per_period = [a + b for a, b in zip(matvec(e1["matrix"], [w * f for w, f in zip(w1, phi)]),
                                            matvec(e2["matrix"], [w * f for w, f in zip(w2, phi)]))]
        mixed_fold = matvec(mixed["matrix"], [(a + b) * f for a, b, f in zip(w1, w2, phi)])
        for x, y in zip(mixed_fold, per_period):
            self.assertAlmostEqual(x, y, delta=1e-12 * max(1.0, abs(y)))
        for name in ("underflow", "overflow"):
            got = sum(m * (a + b) * f for m, a, b, f in zip(mixed[name], w1, w2, phi))
            want = sum((m1 * a + m2 * b) * f for m1, m2, a, b, f in zip(e1[name], e2[name], w1, w2, phi))
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertEqual(rep["weights_sha256"], hashlib.sha256(self.weights.read_bytes()).hexdigest())
        self.assertEqual(mixed["mixing"]["weights"], {"era1": w1, "era2": w2})
        self.assertEqual(rep["validation"]["contracts_validate"], "ok")
        v = subprocess.run([sys.executable, "-B", str(PLUGIN / "contracts" / "response_adapter.py"), str(out),
                            "--validate"], capture_output=True, text=True, timeout=600)
        self.assertEqual(v.returncode, 0, v.stdout[-1500:])

    def test_stack_recovers_the_synthetic_truth(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("numpy not installed (used by the test only)")
        out = self.d / "stack.json"
        code, rep, err = run(MIX, "stack", "--period", f"era1={self.r1}", "--period", f"era2={self.r2}", "--weights",
                             self.weights, "--out", out)
        self.assertEqual(code, 0, err)
        st = json.loads(out.read_text())
        S = np.array(st["matrix"])
        self.assertEqual(S.shape, (2 * 6, 3))
        self.assertEqual([b["era"] for b in st["row_blocks"]], ["era1", "era2"])
        phi = np.array([5.0, 2.5, 1.0])
        mu = S @ phi
        est, *_ = np.linalg.lstsq(S, mu, rcond=None)
        np.testing.assert_allclose(est, phi, rtol=1e-10)
        e1 = json.loads(self.r1.read_text())["extension"]
        w1 = [0.30 * 1000.0, 0.32 * 1200.0, 0.33 * 1300.0]
        np.testing.assert_allclose(S[:6], np.array(e1["matrix"]) * np.array(w1), rtol=1e-15)

    def test_refusals(self):
        other = make_response(self.d, "other", 2.0, 3, 0.8, reco=["0", "10", "20", "30"])
        code, rep, _, _ = self.mix(periods=[f"era1={self.r1}", f"era2={other}"])
        self.assertEqual((code, rep["status"]), (2, "rejected"))
        self.assertIn("reco", rep["error"])
        sel = make_response(self.d, "sel", 2.0, 4, 0.8, normalization="conditional_on_selected")
        code, rep, _, _ = self.mix(periods=[f"era1={self.r1}", f"era2={sel}"])
        self.assertEqual((code, rep["status"]), (2, "rejected"))
        zero = self.d / "zero.json"
        zero.write_text(json.dumps({"periods": {"era1": {"weight": [0, 1, 1]}, "era2": {"weight": [0, 1, 1]}}}))
        code, rep, _, _ = self.mix(weights=zero)
        self.assertEqual((code, rep["status"]), (2, "rejected"))
        neg = self.d / "neg.json"
        neg.write_text(json.dumps({"periods": {"era1": {"weight": [-1, 1, 1]}, "era2": {"weight": [2, 1, 1]}}}))
        code, rep, _, _ = self.mix(weights=neg)
        self.assertEqual((code, rep["status"]), (2, "rejected"))
        missing = self.d / "missing.json"
        missing.write_text(json.dumps({"periods": {"era1": {"weight": [1, 1, 1]}}}))
        code, rep, _, _ = self.mix(weights=missing)
        self.assertEqual((code, rep["status"]), (2, "rejected"))
        code, rep, _, _ = self.mix(periods=[f"era1={self.d / 'nope.json'}"])
        self.assertEqual((code, rep["status"]), (2, "rejected"))

    def test_mixed_mc_stat_is_the_effective_count(self):
        code, rep, err, out = self.mix()
        self.assertEqual(code, 0, err)
        ext = json.loads(out.read_text())["extension"]
        e1 = json.loads(self.r1.read_text())["extension"]
        e2 = json.loads(self.r2.read_text())["extension"]
        n1, n2 = e1["mc_stat"]["events_per_truth_bin"], e2["mc_stat"]["events_per_truth_bin"]
        w1 = [0.30 * 1000.0, 0.32 * 1200.0, 0.33 * 1300.0]
        w2 = [0.40 * 500.0, 0.40 * 450.0, 0.40 * 400.0]
        for j in range(3):
            f1, f2 = w1[j] / (w1[j] + w2[j]), w2[j] / (w1[j] + w2[j])
            self.assertAlmostEqual(ext["mc_stat"]["events_per_truth_bin"][j], 1.0 / (f1 * f1 / n1[j] + f2 * f2 / n2[j]),
                                   delta=1e-9)
        self.assertEqual(ext["mc_stat"]["kind"], "effective_counts")


if __name__ == "__main__":
    unittest.main()
