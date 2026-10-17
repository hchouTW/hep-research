"""M8: isotope_fraction.py. Oracles: the mass resolution from rigidity and velocity, (sigma_m/m)^2 = (sigma_R/R)^2 +
gamma^4 (sigma_beta/beta)^2, grows as gamma^2 when beta -> 1; known isotope fractions are recovered from a synthetic
data histogram; over 400 toys the fraction pulls have width 0.85-1.15 (slow tier); MC-only templates whose tails are
not validated on data give unvalidated; the result carries the template overlap, the shifts for the resolution
nuisances and a composition table spectrum_transform.py reads. Inputs are SYNTHETIC."""
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-measurement" / "scripts" / "isotope_fraction.py"
CONFIG = PLUGIN / "skills" / "hep-measurement" / "assets" / "isotope-fraction.example.json"
TRUE = {"7Be": 0.55, "9Be": 0.30, "10Be": 0.15}
try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout + p.stderr)


def load():
    spec = importlib.util.spec_from_file_location("isotope_fraction", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Resolution(unittest.TestCase):
    def test_gamma_squared_growth(self):
        code, out = run("resolution", "--sigma-r-rel", "0", "--sigma-beta", "0.001", "--beta", "0.9", "0.99", "0.999")
        self.assertEqual(code, 0, out)
        for row in out["points"]:
            g = 1 / math.sqrt(1 - row["beta"] ** 2)
            self.assertAlmostEqual(row["sigma_m_over_m"], g * g * 0.001 / row["beta"], places=12)
        r = [p["sigma_m_over_m"] for p in out["points"]]
        self.assertGreater(r[2] / r[1], 9)  # gamma^2 grows about tenfold from 0.99 to 0.999


@unittest.skipUnless(HAVE_NUMPY, "isotope_fraction.py fit needs numpy")
class Fractions(unittest.TestCase):
    def data_file(self, d, seed, n=6000):
        mod = load()
        cfg = json.loads(CONFIG.read_text())
        truth = mod.build_templates(dict(cfg, mc_events_per_isotope=400000), seed=seed + 1000)
        rng = np.random.default_rng(seed)
        bins = []
        for k in range(len(cfg["rigidity_edges"]) - 1):
            shapes = {iso: np.array(truth["templates"][k][iso]) / truth["generated"][iso] for iso in TRUE}
            mu = sum(n * TRUE[iso] * shapes[iso] / sum(TRUE[i] * shapes[i].sum() for i in TRUE) for iso in TRUE)
            bins.append(rng.poisson(mu).tolist())
        p = Path(d) / "data.json"
        p.write_text(json.dumps({"bins": bins}), encoding="utf-8")
        return p

    def test_known_fractions_recovered(self):
        with tempfile.TemporaryDirectory() as d:
            data = self.data_file(d, 7)
            code, out = run("fit", "--config", CONFIG, "--data", data, "--seed", "3")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["status_label"], "unvalidated")  # MC-only tails
        for row in out["bins"]:
            for iso, f in TRUE.items():
                fr = row["fractions"][iso]
                # fractions are of the isotopes inside the accepted beta range, which favours no isotope much here
                self.assertLess(abs(fr["value"] - f), 4 * fr["error"] + 0.03, (iso, fr))
            self.assertIn("overlap", row)
            self.assertIn("sigma_beta_scale", row["nuisance_shifts"])
        table = out["composition_table"]
        self.assertEqual(table["kind"], "table")
        self.assertEqual(sorted(i["A"] for i in table["isotopes"]), [7, 9, 10])

    @unittest.skipUnless(os.environ.get("HEP_SLOW_TESTS") == "1", "slow: set HEP_SLOW_TESTS=1")
    def test_slow_pull_widths_400_toys(self):
        mod = load()
        cfg = json.loads(CONFIG.read_text())
        pulls = {iso: [] for iso in TRUE}
        with tempfile.TemporaryDirectory() as d:
            for t in range(400):
                data = json.loads(self.data_file(d, 100 + t).read_text())
                res = mod.fit_all(cfg, data, seed=5000 + t, nuisance_shifts=False)
                row = res["bins"][0]
                truth_frac = res["true_reference"] if "true_reference" in res else TRUE
                for iso in TRUE:
                    fr = row["fractions"][iso]
                    pulls[iso].append((fr["value"] - truth_frac[iso]) / fr["error"])
        for iso, v in pulls.items():
            m = sum(v) / len(v)
            w = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
            with self.subTest(iso=iso):
                self.assertTrue(0.85 < w < 1.15, (iso, m, w))
                self.assertLess(abs(m), 0.3, (iso, m))


class Refusals(unittest.TestCase):
    def test_bad_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "c.json"
            cfg = json.loads(CONFIG.read_text())
            cfg["isotopes"] = [{"name": "7Be"}, {"name": "8Xx"}]
            bad.write_text(json.dumps(cfg), encoding="utf-8")
            data = Path(d) / "d.json"
            data.write_text(json.dumps({"bins": [[1] * 15, [1] * 15]}), encoding="utf-8")
            code, out = run("fit", "--config", bad, "--data", data, "--seed", "1")
            self.assertEqual(code, 2, out)
            self.assertEqual(out["status"], "rejected")
            code, out = run("resolution", "--sigma-r-rel", "0.01", "--sigma-beta", "0.001", "--beta", "1.2")
            self.assertEqual(code, 2, out)
            self.assertEqual(out["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
