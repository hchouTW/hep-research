"""D1: propagate_scale_distortion.py, propagating a calibration residual (scale, inverse offset, resolution, plugin).

Oracles:
- scale x_m = (1+s) x on a power law dN/dx ~ x^-gamma: every bin shifts by (1+s)^(gamma-1) - 1 ~ (gamma-1) s;
- inverse offset 1/x_m = 1/x + q delta: the bin yields equal the integral of x^-gamma (1 - q x delta)^(gamma-2) to
  better than 1e-6 (independent numerical integral); first order (2-gamma) q x delta;
- opposite-sign ratio: the ratio shift is (1+s_n)/(1+s_d) - 1 exactly, the difference of the signed shifts to first
  order, and its magnitude is the sum of the two magnitudes;
- resolution: for a Gaussian relative resolution sigma, the folding factor is 1 + (gamma-1)(gamma-2) sigma^2/2 + O(sigma^4);
- events and response agree in the small-resolution limit (events drawn from the same power law);
- no default delta or s; a missing charge sign is refused; |q x delta| > 0.3 warns, >= 1 is refused.
"""
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "skills" / "hep-detector" / "scripts" / "propagate_scale_distortion.py"
CSV_CHECK = ROOT / "skills" / "hep-measurement" / "scripts" / "check_systematic_variations.py"
sys.path.insert(0, str(ROOT))
from contracts.schema import validate  # noqa: E402

EDGES = [2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0]
GAMMA_P, GAMMA_N = 2.8, 2.6


def run(*args, timeout=300):
    return subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True,
                          timeout=timeout)


def run_json(*args, timeout=300):
    res = run(*args, timeout=timeout)
    try:
        return res.returncode, json.loads(res.stdout), res
    except json.JSONDecodeError:
        raise AssertionError(res.stdout + res.stderr) from None


def power_integral(lo, hi, gamma):
    e = 1.0 - gamma
    return (hi ** e - lo ** e) / e


def simpson(f, lo, hi, n=20000):
    h = (hi - lo) / n
    s = f(lo) + f(hi)
    s += 4 * sum(f(lo + (2 * k - 1) * h) for k in range(1, n // 2 + 1))
    s += 2 * sum(f(lo + 2 * k * h) for k in range(1, n // 2))
    return s * h / 3


def model(path, components=None, ratio=True):
    doc = {"variable": "rigidity", "unit": "GV", "edges": EDGES,
           "components": components or [
               {"name": "positive", "charge_sign": 1, "spectrum": {"kind": "power-law", "index": GAMMA_P, "norm": 1.0}},
               {"name": "negative", "charge_sign": -1, "spectrum": {"kind": "power-law", "index": GAMMA_N, "norm": 1e-4}}]}
    if ratio:
        doc["ratio"] = {"numerator": "negative", "denominator": "positive"}
    Path(path).write_text(json.dumps(doc), encoding="utf-8")
    return path


class ResponseOracles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.input = model(self.dir / "model.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_scale_is_the_power_law_factor(self):
        s = 0.01
        code, out, res = run_json("response", self.input, "--mode", "scale", "--scale", s)
        self.assertEqual(code, 0, res.stdout + res.stderr)
        self.assertEqual(out["status"], "ok")
        for name, gamma in (("positive", GAMMA_P), ("negative", GAMMA_N)):
            comp = out["components"][name]
            for up, down in zip(comp["relative_shift_up"], comp["relative_shift_down"]):
                self.assertAlmostEqual(up, (1 + s) ** (gamma - 1) - 1, delta=1e-12)
                self.assertAlmostEqual(down, (1 - s) ** (gamma - 1) - 1, delta=1e-12)
                self.assertAlmostEqual(up, (gamma - 1) * s, delta=(gamma - 1) ** 2 * s * s)

    def test_inverse_offset_matches_the_analytic_density(self):
        delta = 2e-3
        code, out, res = run_json("response", self.input, "--mode", "inverse-offset", "--delta", delta)
        self.assertEqual(code, 0, res.stdout + res.stderr)
        for name, q, gamma, norm in (("positive", 1, GAMMA_P, 1.0), ("negative", -1, GAMMA_N, 1e-4)):
            comp = out["components"][name]
            for i, (lo, hi) in enumerate(zip(EDGES[:-1], EDGES[1:])):
                expected_up = norm * simpson(lambda x: x ** -gamma * (1 - q * x * delta) ** (gamma - 2), lo, hi)
                expected_nom = norm * power_integral(lo, hi, gamma)
                self.assertLess(abs(comp["up"][i] / expected_up - 1), 1e-6, (name, i))
                self.assertLess(abs(comp["nominal"][i] / expected_nom - 1), 1e-12)
                center = math.sqrt(lo * hi)
                self.assertAlmostEqual(comp["relative_shift_up"][i], (2 - gamma) * q * center * delta,
                                       delta=0.15 * abs((2 - gamma) * q * center * delta) + 1e-4)

    def test_opposite_sign_ratio_shifts_subtract_and_magnitudes_add(self):
        code, out, res = run_json("response", self.input, "--mode", "inverse-offset", "--delta", 1e-3)
        self.assertEqual(code, 0, res.stdout + res.stderr)
        num, den, ratio = out["components"]["negative"], out["components"]["positive"], out["ratio"]
        for i in range(len(EDGES) - 1):
            sn, sd = num["relative_shift_up"][i], den["relative_shift_up"][i]
            self.assertLess(sn * sd, 0)  # opposite signs
            self.assertAlmostEqual(ratio["relative_shift_up"][i], (1 + sn) / (1 + sd) - 1, delta=1e-12)
            self.assertAlmostEqual(ratio["signed_shift_difference_up"][i], sn - sd, delta=1e-15)
            self.assertAlmostEqual(ratio["relative_shift_up"][i], sn - sd, delta=4 * max(sn * sn, sd * sd))
            self.assertAlmostEqual(abs(ratio["relative_shift_up"][i]), abs(sn) + abs(sd),
                                   delta=4 * max(sn * sn, sd * sd))
            self.assertAlmostEqual(ratio["up"][i], num["up"][i] / den["up"][i], delta=1e-12 * ratio["up"][i])

    def test_variations_feed_check_systematic_variations_and_covariance_is_rank_one(self):
        code, out, res = run_json("response", self.input, "--mode", "scale", "--scale", 0.02)
        self.assertEqual(code, 0, res.stdout + res.stderr)
        comp = out["components"]["positive"]
        path = self.dir / "variations.json"
        path.write_text(json.dumps(comp["systematic_variations"]), encoding="utf-8")
        check = subprocess.run([sys.executable, "-B", str(CSV_CHECK), "--json", str(path)], capture_output=True,
                               text=True, timeout=300)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        cov = comp["covariance"]
        d = [(u - w) / 2 for u, w in zip(comp["up"], comp["down"])]
        for i, row in enumerate(cov):
            for j, value in enumerate(row):
                self.assertAlmostEqual(value, d[i] * d[j], delta=1e-15 + 1e-12 * abs(d[i] * d[j]))
                self.assertEqual(value, cov[j][i])
        self.assertEqual(out["ratio"]["covariance_kind"], "fully correlated (one parameter), rank 1")

    def test_gaussian_resolution_folding_factor(self):
        sigma, r = 0.02, 0.1
        code, out, res = run_json("response", self.input, "--mode", "resolution", "--core-sigma", sigma,
                                  "--tail-fraction", 0, "--tail-sigma", sigma, "--resolution-shift", r)
        self.assertEqual(code, 0, res.stdout + res.stderr)
        for name, gamma in (("positive", GAMMA_P), ("negative", GAMMA_N)):
            comp = out["components"][name]

            def factor(width):
                return 1 + (gamma - 1) * (gamma - 2) * width ** 2 / 2
            expected = factor(sigma * (1 + r)) / factor(sigma) - 1
            for value in comp["relative_shift_up"]:
                self.assertAlmostEqual(value, expected, delta=1e-7)

    def test_validation_record(self):
        record = self.dir / "record.json"
        code, out, res = run_json("response", self.input, "--mode", "inverse-offset", "--delta", 1e-3,
                                  "--validation-record", record, "--effect", "rigidity_scale")
        self.assertEqual(code, 0, res.stdout + res.stderr)
        doc = json.loads(record.read_text(encoding="utf-8"))
        self.assertTrue(validate(doc, "validation_record.json").ok, doc)
        self.assertEqual(doc["claim"]["relation"], "fully_correlated")
        self.assertEqual([s["root"] for s in doc["subjects"]], ["negative", "positive"])
        self.assertIn("do not cancel", doc["conclusion"])
        # needs --effect, and a ratio (two subjects)
        code, out, _ = run_json("response", self.input, "--mode", "inverse-offset", "--delta", 1e-3,
                                "--validation-record", self.dir / "r2.json")
        self.assertEqual(code, 2)
        self.assertFalse((self.dir / "r2.json").exists())
        single = model(self.dir / "single.json", ratio=False)
        code, out, _ = run_json("response", single, "--mode", "scale", "--scale", 0.01,
                                "--validation-record", self.dir / "r3.json", "--effect", "x")
        self.assertEqual(code, 2)

    def test_refusals_and_warnings(self):
        # no default delta or s
        for mode in ("scale", "inverse-offset", "resolution"):
            code, out, _ = run_json("response", self.input, "--mode", mode)
            self.assertEqual(code, 2, mode)
            self.assertEqual(out["status"], "rejected")
        # missing charge sign
        comps = [{"name": "positive", "spectrum": {"kind": "power-law", "index": 2.7, "norm": 1.0}}]
        code, out, _ = run_json("response", model(self.dir / "nosign.json", comps, ratio=False), "--mode", "scale",
                                "--scale", 0.01)
        self.assertEqual(code, 2)
        self.assertIn("charge_sign", out["error"])
        # |q x delta| > 0.3 warns; >= 1 is refused
        code, out, _ = run_json("response", self.input, "--mode", "inverse-offset", "--delta", 0.01)
        self.assertEqual(code, 0)
        self.assertTrue(any("0.3" in w for w in out["warnings"]))
        code, out, _ = run_json("response", self.input, "--mode", "inverse-offset", "--delta", 0.05)
        self.assertEqual(code, 2)
        # a plugin runs only with --allow-plugin
        plugin = self.dir / "plugin.py"
        plugin.write_text("def distort(x, charge_sign, variation):\n"
                          "    return x * (1.01 if variation == 'up' else 0.99)\n", encoding="utf-8")
        code, out, _ = run_json("response", self.input, "--mode", "plugin", "--plugin", "plugin.py")
        self.assertEqual(code, 2)
        self.assertIn("--allow-plugin", out["error"])
        code, out, res = run_json("response", self.input, "--mode", "plugin", "--plugin", "plugin.py",
                                  "--allow-plugin")
        self.assertEqual(code, 0, res.stdout + res.stderr)
        code, ref, _ = run_json("response", self.input, "--mode", "scale", "--scale", 0.01)
        for a, b in zip(out["components"]["positive"]["up"], ref["components"]["positive"]["up"]):
            self.assertAlmostEqual(a / b, 1, delta=1e-9)
        plugin.write_text("def distort(x, charge_sign, variation):\n    raise RuntimeError('boom')\n",
                          encoding="utf-8")
        code, out, _ = run_json("response", self.input, "--mode", "plugin", "--plugin", "plugin.py",
                                "--allow-plugin")
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "failed")
        self.assertIn("boom", out["error"])

    def test_status_label(self):
        code, out, _ = run_json("response", self.input, "--mode", "scale", "--scale", 0.01)
        self.assertEqual(out["status_label"], "unvalidated")
        self.assertIn("scale", out["inputs"])
        self.assertEqual(out["defaults_used"], [])
        code, out, _ = run_json("response", self.input, "--mode", "scale", "--scale", 0.01, "--status", "synthetic")
        self.assertEqual(out["status_label"], "synthetic")


class EventsAgreeWithResponse(unittest.TestCase):
    def test_small_resolution_limit(self):
        rng = random.Random(20261017)
        lo, hi = 1.0, 200.0
        rows = []
        for sign, gamma, n in ((1, GAMMA_P, 200000), (-1, GAMMA_N, 100000)):
            e = 1 - gamma
            for _ in range(n):
                x = (lo ** e + rng.random() * (hi ** e - lo ** e)) ** (1 / e)
                rows.append(f"{sign * x:.12g}")
        delta = 2e-3
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "events.csv"
            events.write_text("# synthetic test events\nrigidity_meas_gv\n" + "\n".join(rows) + "\n", encoding="utf-8")
            code, ev, res = run_json("events", events, "--column", "rigidity_meas_gv", "--signed", "--edges",
                                     *EDGES, "--mode", "inverse-offset", "--delta", delta,
                                     "--ratio", "negative-over-positive")
            self.assertEqual(code, 0, res.stdout + res.stderr)
            code, rs, res = run_json("response", model(Path(tmp) / "m.json"), "--mode", "inverse-offset", "--delta",
                                     delta)
            self.assertEqual(code, 0, res.stdout + res.stderr)
            for name in ("positive", "negative"):
                e_comp, r_comp = ev["components"][name], rs["components"][name]
                for i in range(len(EDGES) - 1):
                    noise = math.sqrt(e_comp["systematic_variations"]["up_diff_sumw2"][i]) / e_comp["nominal"][i]
                    self.assertLess(abs(e_comp["relative_shift_up"][i] - r_comp["relative_shift_up"][i]),
                                    5 * noise + 1e-4, (name, i))
            self.assertIn("ratio", ev)
            self.assertEqual(ev["inputs"]["events_skipped"], 0)

    def test_events_refuse_a_missing_sign(self):
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "events.csv"
            events.write_text("x\n3.0\n4.0\n", encoding="utf-8")
            code, out, _ = run_json("events", events, "--column", "x", "--edges", *EDGES, "--mode", "scale",
                                    "--scale", 0.01)
            self.assertEqual(code, 2)
            self.assertIn("charge sign", out["error"])
            code, out, _ = run_json("events", events, "--column", "missing", "--signed", "--edges", *EDGES,
                                    "--mode", "scale", "--scale", 0.01)
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
