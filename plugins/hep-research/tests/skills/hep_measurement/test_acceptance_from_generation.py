"""acceptance_from_generation.py (M2): acceptance A(x) = G_gen N_sel(x) / N_gen(x) from generation records.
Oracles: G = pi A for a one-sided flat detector in an isotropic flux (cosine-law generation, everything selected);
the two-coaxial-disc geometric factor (Sullivan) against a straight-line Monte Carlo, and its two limits; a missing
generated count exits 3; a target spectrum taken from the measurement itself warns of circularity. SYNTHETIC inputs."""
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-measurement" / "scripts" / "acceptance_from_generation.py"
sys.path.insert(0, str(SCRIPT.parent))
EDGES = [1.0, 2.0, 4.0, 8.0, 16.0]


def power_law_sample(rng, index, lo, hi):
    a = 1.0 - index
    u = rng.random()
    return (lo ** a + u * (hi ** a - lo ** a)) ** (1.0 / a)


def cosine_direction(rng):
    """Downward unit vector with the cosine law (isotropic flux through a plane)."""
    cos_t = math.sqrt(rng.random())
    sin_t = math.sqrt(1.0 - cos_t * cos_t)
    phi = 2.0 * math.pi * rng.random()
    return sin_t * math.cos(phi), sin_t * math.sin(phi), -cos_t


def config(area=None, n_generated=None, **extra):
    gen = {"surface": "plane", "area_m2": area, "angular": "cosine",
           "spectrum": {"kind": "power-law", "index": 2.0, "x_min": 1.0, "x_max": 16.0}}
    if n_generated is not None:
        gen["n_generated"] = n_generated
    cfg = {"generation": gen, "x": {"variable": "rigidity", "unit": "GV", "edges": EDGES}}
    cfg.update(extra)
    return cfg


def run(cfg, xs, *extra):
    with tempfile.TemporaryDirectory() as d:
        c, e = Path(d) / "cfg.json", Path(d) / "sel.csv"
        c.write_text(json.dumps(cfg), encoding="utf-8")
        e.write_text("x\n" + "".join(f"{x!r}\n" for x in xs), encoding="utf-8")
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "--config", str(c), "--events", str(e), *extra],
                           capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout), p.stderr


class FlatDetector(unittest.TestCase):
    def test_everything_selected_gives_pi_times_area(self):
        rng = random.Random(1)
        n, area = 40000, 0.25
        xs = [power_law_sample(rng, 2.0, 1.0, 16.0) for _ in range(n)]
        code, out, err = run(config(area, n), xs, "--status", "synthetic")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "synthetic")
        self.assertAlmostEqual(out["generation_factor_m2_sr"], math.pi * area, delta=1e-12)
        for b in out["bins"]:
            with self.subTest(bin=b["edges"]):
                self.assertLessEqual(b["acceptance_lower"], math.pi * area * 1.0000001)
                self.assertGreaterEqual(b["acceptance_upper"] * 1.03, math.pi * area)  # 68% CP band, small slack
                self.assertAlmostEqual(b["acceptance"] / (math.pi * area), 1.0, delta=0.05)


class TwoDiscs(unittest.TestCase):
    def test_sullivan_limits(self):
        import acceptance_from_generation as afg
        r = 0.3
        self.assertAlmostEqual(afg.sullivan_two_disc(r, r, 0.0), math.pi ** 2 * r * r, delta=1e-12)
        g = afg.sullivan_two_disc(0.1, 0.2, 100.0)
        self.assertAlmostEqual(g / (math.pi ** 2 * 0.1 ** 2 * 0.2 ** 2 / 100.0 ** 2), 1.0, delta=1e-5)

    def test_monte_carlo_matches_sullivan(self):
        import acceptance_from_generation as afg
        rng = random.Random(7)
        r1, r2, sep = 0.2, 0.15, 0.3
        n = 200000
        sel = []
        for _ in range(n):
            rad, ang = r1 * math.sqrt(rng.random()), 2.0 * math.pi * rng.random()
            x0, y0 = rad * math.cos(ang), rad * math.sin(ang)
            dx, dy, dz = cosine_direction(rng)
            t = sep / -dz
            if (x0 + t * dx) ** 2 + (y0 + t * dy) ** 2 <= r2 * r2:
                sel.append(power_law_sample(rng, 2.0, 1.0, 16.0))
            else:
                rng.random()  # keep the stream aligned
        # every generated event has a rigidity; the selection is independent of it
        code, out, err = run(config(math.pi * r1 * r1, n), sel)
        self.assertEqual(code, 0, err)
        g = afg.sullivan_two_disc(r1, r2, sep)
        for b in out["bins"]:
            with self.subTest(bin=b["edges"]):
                sigma = (b["acceptance_upper"] - b["acceptance_lower"]) / 2.0
                self.assertLess(abs(b["acceptance"] - g), 3.5 * sigma, (b["acceptance"], g, sigma))


class Refusals(unittest.TestCase):
    def test_missing_generated_count_exits_3(self):
        code, out, _ = run(config(1.0, None), [2.0, 3.0])
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "incomplete")
        self.assertIn("n_generated", out["error"])

    def test_bad_input_exits_2(self):
        code, out, _ = run(config(-1.0, 100), [2.0])
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")

    def test_target_from_the_measurement_warns_circularity(self):
        target = {"kind": "power-law", "index": 2.7, "x_min": 1.0, "x_max": 16.0, "from_measurement": True, "source": "this measurement's flux"}
        code, out, _ = run(config(1.0, 1000, target_spectrum=target), [2.0] * 50 + [5.0] * 20)
        self.assertEqual(code, 0)
        self.assertTrue(any("circular" in w for w in out["warnings"]), out["warnings"])
        self.assertEqual(out["target_spectrum"]["index"], 2.7)


if __name__ == "__main__":
    unittest.main()
