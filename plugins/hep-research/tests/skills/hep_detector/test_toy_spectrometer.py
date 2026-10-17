"""D7: toy_spectrometer.py, a fast synthetic magnetic-spectrometer simulation.

Oracles:
- sigma(1/R) agrees with multiple_scattering.py in both limits (scattering-dominated at low rigidity, intrinsic at
  high rigidity), for the same layers, field and lever arm;
- the same seed gives byte-identical event and period tables; another seed does not;
- the generated 1/R pulls have unit width, the truncated-mean charge sits at the true charge;
- an era that adds a layer and lengthens the lever arm has a smaller intrinsic term a;
- 1e6 events in seconds (HEP_SLOW_TESTS=1).
"""
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills" / "hep-detector" / "scripts"
TOY = SCRIPTS / "toy_spectrometer.py"
MS = SCRIPTS / "multiple_scattering.py"
CONFIG = ROOT / "skills" / "hep-detector" / "assets" / "toy-spectrometer.fictional.json"


def run(script, *args, timeout=300):
    res = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True,
                         timeout=timeout)
    return res


def run_json(script, *args, timeout=300):
    res = run(script, *args, timeout=timeout)
    return res.returncode, json.loads(res.stdout), res


def stack_for_multiple_scattering(config, era_layers=None, lever_arm=None):
    """The multiple_scattering.py stack that describes the same tracker as the toy configuration."""
    layers = era_layers if era_layers is not None else config["layers"]
    measuring = [x for x in layers if x.get("measuring")]
    resolution = {x["resolution_um"] for x in measuring}
    assert len(resolution) == 1, "the oracle needs equal point resolutions (Gluckstern)"
    return {
        "field_tesla": config["field"]["field_tesla"],
        "lever_arm_m": lever_arm or config["field"]["lever_arm_m"],
        "point_resolution_um": resolution.pop(),
        "layers": [{"x_over_x0": x["grammage_g_cm2"] / x["radiation_length_g_cm2"], "measuring": bool(x.get("measuring"))}
                   for x in layers],
    }


class ToySpectrometerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def generate(self, folder, seed, config=CONFIG):
        events, periods = Path(folder) / f"events-{seed}.csv", Path(folder) / f"periods-{seed}.csv"
        code, out, res = run_json(TOY, "generate", config, "--seed", seed, "--events-out", events,
                                  "--periods-out", periods)
        self.assertEqual(code, 0, res.stdout + res.stderr)
        return out, events, periods

    def test_help(self):
        res = run(TOY, "--help")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("generate", res.stdout)
        self.assertIn("resolution", res.stdout)

    def test_resolution_matches_multiple_scattering_in_both_limits(self):
        p = next(s for s in self.config["species"] if s["name"] == "p")
        with tempfile.TemporaryDirectory() as tmp:
            stack = Path(tmp) / "stack.json"
            stack.write_text(json.dumps(stack_for_multiple_scattering(self.config)), encoding="utf-8")
            for rigidity, dominant in ((0.5, "scattering"), (1e5, "intrinsic")):
                with self.subTest(rigidity=rigidity):
                    code, toy, res = run_json(TOY, "resolution", CONFIG, "--species", "p", "--rigidity", rigidity)
                    self.assertEqual(code, 0, res.stdout + res.stderr)
                    row = toy["points"][0]
                    code, ms, res = run_json(MS, stack, "--rigidity", rigidity, "--mass", p["mass_gev"],
                                             "--charge", p["Z"])
                    self.assertEqual(code, 0, res.stdout + res.stderr)
                    self.assertEqual(ms["dominant_term"], dominant)
                    # sigma(1/R) = (sigma(R)/R) / R
                    self.assertAlmostEqual(row["sigma_inv_rigidity_per_gv"] * rigidity,
                                           ms["total_relative_resolution"], delta=1e-9 * ms["total_relative_resolution"])
                    self.assertAlmostEqual(row["beta"], ms["beta"], delta=1e-12)
            era = toy["eras"][0]
            self.assertAlmostEqual(era["a_per_gv"], ms["intrinsic_term"] / 1e5, delta=1e-12 * era["a_per_gv"])

    def test_added_layer_era_improves_the_intrinsic_term(self):
        code, toy, res = run_json(TOY, "resolution", CONFIG, "--species", "p", "--rigidity", 100)
        self.assertEqual(code, 0, res.stdout + res.stderr)
        eras = {e["name"]: e for e in toy["eras"]}
        self.assertLess(eras["era-2-added-layer"]["a_per_gv"], eras["era-1"]["a_per_gv"])
        self.assertEqual(eras["era-2-added-layer"]["measuring_layers"], 9)

    def test_same_seed_same_bytes(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            out1, e1, p1 = self.generate(a, 7)
            out2, e2, p2 = self.generate(b, 7)
            self.assertEqual(e1.read_bytes(), e2.read_bytes())
            self.assertEqual(p1.read_bytes(), p2.read_bytes())
            self.assertEqual(out1["outputs"]["events_sha256"], hashlib.sha256(e1.read_bytes()).hexdigest())
            out3, e3, _ = self.generate(a, 8)
            self.assertNotEqual(e1.read_bytes(), e3.read_bytes())
            for out in (out1, out3):
                self.assertEqual(out["status"], "ok")
                self.assertEqual(out["status_label"], "synthetic")
                self.assertIn("seed", out["inputs"])
            self.assertEqual(out1["inputs"]["seed"], 7)

    def test_tables_are_labeled_and_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, events, periods = self.generate(tmp, 11)
            with open(events, encoding="utf-8") as handle:
                comment = handle.readline()
                rows = list(csv.DictReader(handle))
            self.assertIn("synthetic", comment)
            self.assertIn("seed=11", comment)
            with open(periods, encoding="utf-8") as handle:
                self.assertIn("synthetic", handle.readline())
                prows = list(csv.DictReader(handle))
            self.assertEqual(len(prows), self.config["periods"]["count"])
            self.assertEqual(sum(int(r["n_events"]) for r in prows), len(rows))
            self.assertEqual(out["n_events"], len(rows))
            self.assertEqual({r["era"] for r in prows}, {"era-1", "era-2-added-layer"})
            self.assertEqual([r["era"] for r in prows[5:7]], ["era-1", "era-2-added-layer"])
            pulls, zres = [], {1: [], 2: []}
            for r in rows:
                inv_true = 1.0 / float(r["rigidity_true_gv"])
                pulls.append((float(r["inv_rigidity_meas_per_gv"]) - inv_true) / float(r["sigma_inv_rigidity_per_gv"]))
                zres[int(r["z_true"])].append(float(r["z_meas"]))
            n = len(pulls)
            mean = sum(pulls) / n
            sd = math.sqrt(sum((x - mean) ** 2 for x in pulls) / (n - 1))
            self.assertLess(abs(mean), 5 / math.sqrt(n))
            self.assertLess(abs(sd - 1.0), 5 / math.sqrt(2 * n))
            for z, values in zres.items():
                median = sorted(values)[len(values) // 2]
                self.assertLess(abs(median - z), 0.05 * z, z)

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.json"
            code, out, _ = run_json(TOY, "generate", missing, "--seed", 1, "--events-out", Path(tmp) / "e.csv",
                                    "--periods-out", Path(tmp) / "p.csv")
            self.assertEqual(code, 2)
            self.assertEqual(out["status"], "rejected")
            bad = json.loads(CONFIG.read_text(encoding="utf-8"))
            bad["species"][0]["fraction"] = 0.5
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            code, out, _ = run_json(TOY, "generate", path, "--seed", 1, "--events-out", Path(tmp) / "e.csv",
                                    "--periods-out", Path(tmp) / "p.csv")
            self.assertEqual(code, 2)
            self.assertIn("fraction", out["error"])
            nomass = json.loads(CONFIG.read_text(encoding="utf-8"))
            del nomass["species"][1]["mass_gev"]
            path.write_text(json.dumps(nomass), encoding="utf-8")
            code, out, _ = run_json(TOY, "resolution", path, "--species", "He4", "--rigidity", 10)
            self.assertEqual(code, 2)
            self.assertIn("mass_gev", out["error"])
            # the seed is required: no hidden default
            res = run(TOY, "generate", CONFIG, "--events-out", Path(tmp) / "e.csv", "--periods-out", Path(tmp) / "p.csv")
            self.assertEqual(res.returncode, 2)
            self.assertEqual(json.loads(res.stdout)["status"], "rejected")
            self.assertFalse((Path(tmp) / "e.csv").exists())

    @unittest.skipUnless(os.environ.get("HEP_SLOW_TESTS") == "1", "set HEP_SLOW_TESTS=1 for the 1e6-event timing")
    def test_a_million_events_in_seconds(self):
        big = json.loads(CONFIG.read_text(encoding="utf-8"))
        big["periods"]["rate_hz"] = 1e6 / (big["periods"]["count"] * big["periods"]["duration_s"]
                                           * big["periods"]["live_fraction"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "big.json"
            path.write_text(json.dumps(big), encoding="utf-8")
            start = time.perf_counter()
            out, _, _ = self.generate(tmp, 3, config=path)
            elapsed = time.perf_counter() - start
            self.assertGreater(out["n_events"], 990000)
            self.assertLess(elapsed, 30.0)


if __name__ == "__main__":
    unittest.main()
