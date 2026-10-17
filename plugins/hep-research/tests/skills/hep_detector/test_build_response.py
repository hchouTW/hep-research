"""build_response.py (D9): a response artifact from matched truth, reco, weight and selection flag. Oracles: Gaussian
smearing of events at one truth value gives the analytic migration probabilities; the column sums (with explicit
under/overflow) equal the selection efficiency; for unweighted events the uncertainty is the multinomial
sqrt(P(1 - P)/N); the artifact passes contracts/validate.py and contracts/response_adapter.py --validate; --fold
equals the matrix product; resolution summaries match the injected width. Events are SYNTHETIC."""
import csv
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "build_response.py"
TRUTH_EDGES = [0.0, 10.0, 20.0, 30.0]
RECO_EDGES = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]


def run(*args, cwd=None):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600, cwd=cwd)
    out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout
    return p.returncode, out, p.stderr


def phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def write_events(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["truth", "reco", "weight", "selected"])
        for r in rows:
            w.writerow(r)


class BuildResponse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)

    def common(self, events, out, *extra, normalization="conditional_on_generated"):
        return ["build", events, "--truth-col", "truth", "--reco-col", "reco", "--selected-col", "selected",
                "--truth-edges", *TRUTH_EDGES, "--reco-edges", *RECO_EDGES, "--variable", "x", "--unit", "GeV",
                "--normalization", normalization, "--acceptance", "outside_matrix", "--residual", "difference",
                "--intended-use", "forward_folding", "--artifact-id", "synthetic-response", "--objective",
                "SYNTHETIC response for a test", "--created", "2026-10-17", "--out", out, *extra]

    def gaussian_events(self, n=200000, sigma=4.0, x0=15.0, eff=0.7, seed=11, weighted=False):
        rng = random.Random(seed)
        rows = []
        for _ in range(n):
            sel = rng.random() < eff
            w = rng.choice((0.5, 1.0, 2.0)) if weighted else 1.0
            reco = x0 + rng.gauss(0.0, sigma) if sel else ""
            rows.append([x0, reco, w, int(sel)])
        return rows

    def test_gaussian_smearing_gives_the_analytic_migration(self):
        ev, out = self.d / "ev.csv", self.d / "resp.json"
        rows = self.gaussian_events()
        write_events(ev, rows)
        code, rep, err = run(*self.common(ev, out, "--unweighted"))
        self.assertEqual(code, 0, err + json.dumps(rep)[:2000])
        self.assertEqual(rep["status"], "ok")
        doc = json.loads(out.read_text())
        ext = doc["extension"]
        self.assertEqual(ext["orientation"], "rows_reco_cols_truth")
        self.assertEqual(ext["inefficiency"], "inside_matrix")
        n_sel = sum(r[3] for r in rows)
        eff = n_sel / len(rows)
        col = [row[1] for row in ext["matrix"]]  # truth bin 1 holds every event (x0 = 15)
        sigma_mc = ext["build_diagnostics"]["mc_uncertainty"]
        for i, (lo, hi) in enumerate(zip(RECO_EDGES, RECO_EDGES[1:])):
            p_exact = eff * (phi((hi - 15.0) / 4.0) - phi((lo - 15.0) / 4.0))
            self.assertAlmostEqual(col[i], p_exact, delta=4 * sigma_mc[i][1] + 1e-12)
        under = eff * phi((0.0 - 15.0) / 4.0)
        self.assertAlmostEqual(ext["underflow"][1], under, delta=5 * math.sqrt(under / len(rows)) + 1e-6)

    def test_column_sums_equal_the_selection_efficiency(self):
        ev, out = self.d / "ev.csv", self.d / "resp.json"
        rng = random.Random(3)
        rows = []
        for _ in range(5000):
            t = rng.uniform(0, 30)
            sel = rng.random() < 0.4 + 0.015 * t
            w = rng.uniform(0.2, 3.0)
            rows.append([t, t + rng.gauss(0, 3.0) if sel else "", w, int(sel)])
        write_events(ev, rows)
        code, rep, err = run(*self.common(ev, out, "--weight-col", "weight"))
        self.assertEqual(code, 0, err)
        ext = json.loads(out.read_text())["extension"]
        for j, (lo, hi) in enumerate(zip(TRUTH_EDGES, TRUTH_EDGES[1:])):
            in_bin = [r for r in rows if lo <= r[0] < hi]
            eff = sum(r[2] for r in in_bin if r[3]) / sum(r[2] for r in in_bin)
            col = sum(row[j] for row in ext["matrix"]) + ext["underflow"][j] + ext["overflow"][j]
            self.assertAlmostEqual(col, eff, delta=1e-12)
            self.assertAlmostEqual(ext["generated_per_truth_bin"][j], sum(r[2] for r in in_bin), delta=1e-9)
            self.assertAlmostEqual(rep["selection_efficiency"][j], eff, delta=1e-12)

    def test_conditional_on_selected_sums_to_one_and_lists_the_efficiency_separately(self):
        ev, out = self.d / "ev.csv", self.d / "resp.json"
        write_events(ev, self.gaussian_events(n=20000))
        code, rep, err = run(*self.common(ev, out, "--unweighted", normalization="conditional_on_selected"))
        self.assertEqual(code, 0, err)
        ext = json.loads(out.read_text())["extension"]
        self.assertEqual(ext["inefficiency"], "outside_matrix")
        self.assertIn("efficiency", ext["applied_separately"])
        s = sum(row[1] for row in ext["matrix"]) + ext["underflow"][1] + ext["overflow"][1]
        self.assertAlmostEqual(s, 1.0, delta=1e-12)

    def test_unweighted_uncertainty_is_multinomial(self):
        ev, out = self.d / "ev.csv", self.d / "resp.json"
        rows = self.gaussian_events(n=3000)
        write_events(ev, rows)
        run(*self.common(ev, out, "--unweighted"))
        ext = json.loads(out.read_text())["extension"]
        n = len(rows)
        for i, row in enumerate(ext["matrix"]):
            p = row[1]
            self.assertAlmostEqual(ext["build_diagnostics"]["mc_uncertainty"][i][1], math.sqrt(p * (1 - p) / n),
                                   delta=1e-12)

    def test_artifact_validates_and_folds(self):
        ev, out = self.d / "ev.csv", self.d / "resp.json"
        write_events(ev, self.gaussian_events(n=20000, weighted=True))
        truth = self.d / "truth.json"
        truth.write_text(json.dumps({"truth": [100.0, 200.0, 50.0]}))
        code, rep, err = run(*self.common(ev, out, "--weight-col", "weight", "--fold", truth))
        self.assertEqual(code, 0, err)
        v = subprocess.run([sys.executable, "-B", str(PLUGIN / "contracts" / "validate.py"), str(out), "--strict"],
                           capture_output=True, text=True, timeout=600)
        self.assertEqual(v.returncode, 0, v.stdout[-2000:])
        a = subprocess.run([sys.executable, "-B", str(PLUGIN / "contracts" / "response_adapter.py"), str(out),
                            "--validate"], capture_output=True, text=True, timeout=600)
        self.assertEqual(a.returncode, 0, a.stdout[-2000:])
        ext = json.loads(out.read_text())["extension"]
        expect = [sum(ext["matrix"][i][j] * t for j, t in enumerate([100.0, 200.0, 50.0])) for i in range(6)]
        for got, want in zip(rep["folded"]["reco"], expect):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertEqual(rep["validation"]["contracts_validate"], "ok")
        self.assertEqual(ext["mc_stat"]["kind"], "sumw2")
        self.assertEqual(len(ext["mc_stat"]["sumw2"]), 6)

    def test_unfolding_response_with_every_truth_bin_filled_validates(self):
        ev, out = self.d / "ev.csv", self.d / "resp.json"
        rng = random.Random(9)
        write_events(ev, [[t, t + rng.gauss(0, 1.0), 1.0, 1] for t in (rng.uniform(0, 30) for _ in range(6000))])
        args = self.common(ev, out, "--unweighted")
        args[args.index("forward_folding")] = "unfolding"
        code, rep, err = run(*args)
        self.assertEqual(code, 0, err + json.dumps(rep.get("validation"))[:1500])
        ext = json.loads(out.read_text())["extension"]
        self.assertEqual(ext["mc_stat"]["kind"], "generated_counts")
        self.assertEqual(sum(ext["mc_stat"]["events_per_truth_bin"]), 6000)

    def test_resolution_summary_matches_the_injected_width(self):
        ev, out = self.d / "ev.csv", self.d / "resp.json"
        write_events(ev, self.gaussian_events(n=50000, sigma=2.0))
        code, rep, err = run(*self.common(ev, out, "--unweighted"))
        self.assertEqual(code, 0, err)
        res = json.loads(out.read_text())["extension"]["build_diagnostics"]["resolution"][1]
        self.assertAlmostEqual(res["sigma68"], 2.0, delta=0.05)
        self.assertAlmostEqual(res["sigma_mad"], 2.0, delta=0.05)
        self.assertAlmostEqual(res["median"], 0.0, delta=0.05)
        self.assertLess(res["tail_fraction"], 0.01)

    def test_same_input_gives_the_same_bytes(self):
        ev = self.d / "ev.csv"
        write_events(ev, self.gaussian_events(n=5000))
        a, b = self.d / "a.json", self.d / "b.json"
        run(*self.common(ev, a, "--unweighted"))
        run(*self.common(ev, b, "--unweighted"))
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_refusals(self):
        ev, out = self.d / "ev.csv", self.d / "resp.json"
        write_events(ev, [[5.0, "", 1.0, 1]])  # selected without a reco value
        code, rep, _ = run(*self.common(ev, out, "--unweighted"))
        self.assertEqual((code, rep["status"]), (2, "rejected"))
        write_events(ev, [[5.0, 6.0, -1.0, 1]])  # negative weight
        code, rep, _ = run(*self.common(ev, out, "--weight-col", "weight"))
        self.assertEqual((code, rep["status"]), (2, "rejected"))
        write_events(ev, [[5.0, 6.0, 1.0, 1]])
        code, rep, _ = run(*[a for a in self.common(ev, out) if a != "--acceptance" and a != "outside_matrix"],
                           "--unweighted")
        self.assertEqual(code, 2)  # --acceptance has no default
        code, rep, _ = run(*self.common(self.d / "missing.csv", out, "--unweighted"))
        self.assertEqual((code, rep["status"]), (2, "rejected"))
        bad_edges = self.common(ev, out, "--unweighted")
        bad_edges[bad_edges.index("--truth-edges") + 2] = -1.0
        code, rep, _ = run(*bad_edges)
        self.assertEqual((code, rep["status"]), (2, "rejected"))
        self.assertFalse(out.exists())

    def test_empty_truth_bin_is_refused_for_unfolding(self):
        ev, out = self.d / "ev.csv", self.d / "resp.json"
        write_events(ev, self.gaussian_events(n=2000))  # every event in truth bin 1
        args = self.common(ev, out, "--unweighted")
        args[args.index("forward_folding")] = "unfolding"
        code, rep, _ = run(*args)
        self.assertEqual((code, rep["status"]), (1, "refused"))
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
