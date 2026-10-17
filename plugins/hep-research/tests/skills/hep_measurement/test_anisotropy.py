"""anisotropy.py (M9): directional exposure in right ascension from data-taking periods, the first harmonic
(Rayleigh), the dipole projection, the amplitude upper limit from the Rice distribution, and spurious-modulation
checks at the solar, sidereal and anti-sidereal frequencies. Oracles: isotropic toys follow the Rayleigh law; an
injected dipole is recovered; exposure weighting removes an exposure-made modulation; full sidereal days give a flat
exposure; an anti-sidereal modulation fails the check; the upper limit covers. SYNTHETIC inputs only."""
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-measurement" / "scripts" / "anisotropy.py"
sys.path.insert(0, str(SCRIPT.parent))
SIDEREAL_S = 86164.0905
SOLAR_S = 86400.0
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"


def import_mod():
    import anisotropy
    return anisotropy


def sample_ra(rng, amp, phase_deg):
    """Right ascension (deg) from 1 + amp cos(alpha - phase), by rejection."""
    while True:
        a = 360.0 * rng.random()
        if rng.random() * (1.0 + amp) <= 1.0 + amp * math.cos(math.radians(a - phase_deg)):
            return a


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


def write_events(d, rows, cols=("ra_deg",)):
    p = Path(d) / "events.csv"
    p.write_text(",".join(cols) + "\n" + "".join(",".join(repr(v) for v in r) + "\n" for r in rows), encoding="utf-8")
    return p


class Harmonic(unittest.TestCase):
    def test_isotropic_toys_follow_rayleigh(self):
        an = import_mod()
        rng = random.Random(11)
        n, toys = 400, 400
        ps, rs = [], []
        for _ in range(toys):
            h = an.first_harmonic([360.0 * rng.random() for _ in range(n)])
            ps.append(h["rayleigh_probability"])
            rs.append(h["amplitude"])
        frac = sum(p < 0.1 for p in ps) / toys
        self.assertLess(abs(frac - 0.1), 3.5 * math.sqrt(0.1 * 0.9 / toys))
        self.assertAlmostEqual(sum(rs) / toys / math.sqrt(math.pi / n), 1.0, delta=0.06)

    @unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
    def test_rayleigh_probability_uniform_ks(self):
        an = import_mod()
        rng = random.Random(5)
        ps = sorted(an.first_harmonic([360.0 * rng.random() for _ in range(500)])["rayleigh_probability"]
                    for _ in range(3000))
        d = max(max(abs((i + 1) / len(ps) - p), abs(i / len(ps) - p)) for i, p in enumerate(ps))
        self.assertLess(d, 1.36 / math.sqrt(len(ps)))  # KS at 5%

    def test_injected_dipole_is_recovered(self):
        an = import_mod()
        rng = random.Random(3)
        n = 20000
        h = an.first_harmonic([sample_ra(rng, 0.1, 60.0) for _ in range(n)])
        sigma = math.sqrt(2.0 / n)
        self.assertLess(abs(h["amplitude"] - 0.1), 3.5 * sigma)  # for 1 + a cos(alpha - phi), E[r] = a
        self.assertLess(abs(h["phase_deg"] - 60.0), 8.0)

    def test_dipole_projection_uses_the_declination(self):
        an = import_mod()
        rng = random.Random(9)
        ras = [sample_ra(rng, 0.2, 100.0) for _ in range(20000)]
        h = an.first_harmonic(ras, decs=[30.0] * len(ras))
        self.assertAlmostEqual(h["d_perp"], h["amplitude"] / math.cos(math.radians(30.0)), delta=1e-12)


class Exposure(unittest.TestCase):
    def periods(self, d, rows):
        p = Path(d) / "periods.csv"
        p.write_text("period,start_s,duration_s,live_fraction\n" + "".join(f"{k},{s!r},{t!r},{f!r}\n" for k, s, t, f in rows),
                     encoding="utf-8")
        return p

    def config(self, d, half_width=15.0):
        p = Path(d) / "exp.json"
        p.write_text(json.dumps({"key": "period", "start_column": "start_s", "duration_column": "duration_s",
                                 "live_fraction_column": "live_fraction", "lst_at_t0_deg": 0.0,
                                 "fov_half_width_deg": half_width, "ra_bins": 24}), encoding="utf-8")
        return p

    def test_whole_sidereal_days_give_a_flat_exposure(self):
        with tempfile.TemporaryDirectory() as d:
            per = self.periods(d, [("p1", 0.0, 2 * SIDEREAL_S, 0.9), ("p2", 2 * SIDEREAL_S, SIDEREAL_S, 0.5)])
            code, out, err = run("exposure", "--config", self.config(d), per, "--status", "synthetic")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "ok")
        for v in out["relative_exposure"]:
            self.assertAlmostEqual(v, 1.0, delta=1e-9)
        # with full coverage the mean exposure is the live time times the fraction of the circle in view (30/360)
        live = 0.9 * 2 * SIDEREAL_S + 0.5 * SIDEREAL_S
        self.assertAlmostEqual(sum(out["exposure_s"]) / 24.0 / (live * 30.0 / 360.0), 1.0, delta=1e-12)
        self.assertAlmostEqual(out["live_time_s"], live, delta=1e-6)

    def test_exposure_weighting_removes_an_exposure_made_modulation(self):
        an = import_mod()
        with tempfile.TemporaryDirectory() as d:
            per = self.periods(d, [("p1", 0.0, 0.5 * SIDEREAL_S, 1.0), ("p2", SIDEREAL_S, SIDEREAL_S, 0.2)])
            code, out, err = run("exposure", "--config", self.config(d, 30.0), per)
            self.assertEqual(code, 0, err)
            emap = Path(d) / "map.json"
            emap.write_text(json.dumps(out), encoding="utf-8")
            rel = out["relative_exposure"]
            rng = random.Random(21)
            rows = []
            while len(rows) < 20000:  # isotropic sky seen through the exposure
                a = 360.0 * rng.random()
                if rng.random() * max(rel) <= rel[int(a // 15.0)]:
                    rows.append((a,))
            ev = write_events(d, rows)
            code, raw, _ = run("harmonic", "--events", ev, "--cl", "0.95")
            code2, weighted, _ = run("harmonic", "--events", ev, "--exposure-map", emap, "--cl", "0.95")
        self.assertEqual(code2, 0)
        sigma = math.sqrt(2.0 / 20000)
        self.assertGreater(raw["harmonic"]["amplitude"], 10 * sigma)
        self.assertLess(weighted["harmonic"]["amplitude"], 4 * sigma)
        self.assertTrue(any("uniform exposure" in w for w in raw["warnings"]))
        self.assertIsNotNone(an)


class UpperLimit(unittest.TestCase):
    def test_limit_properties(self):
        an = import_mod()
        n = 2000
        ul = [an.amplitude_upper_limit(r, n, 0.95)["upper_limit"] for r in (0.0, 0.02, 0.04, 0.08)]
        self.assertTrue(all(b >= a for a, b in zip(ul, ul[1:])))
        self.assertGreaterEqual(ul[2], 0.04)
        exp = an.amplitude_upper_limit(None, n, 0.95)["expected_limit"]
        self.assertGreater(exp, 0.0)

    def test_rice_cdf_reduces_to_rayleigh(self):
        an = import_mod()
        n, x = 1000, 0.05
        self.assertAlmostEqual(an.rice_cdf(x, 0.0, n), 1.0 - math.exp(-n * x * x / 4.0), delta=1e-12)

    @unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
    def test_upper_limit_covers(self):
        an = import_mod()
        rng = random.Random(4)
        n, s, toys = 1500, 0.03, 300
        cover = 0
        for _ in range(toys):
            ras = [sample_ra(rng, s, 0.0) for _ in range(n)]
            r = an.first_harmonic(ras)["amplitude"]
            cover += an.amplitude_upper_limit(r, n, 0.9)["upper_limit"] >= s
        self.assertGreaterEqual(cover / toys, 0.9 - 3 * math.sqrt(0.09 / toys))


class SpuriousModulation(unittest.TestCase):
    def test_anti_sidereal_modulation_fails(self):
        rng = random.Random(8)
        f_anti = 2.0 / SOLAR_S - 1.0 / SIDEREAL_S
        rows = []
        while len(rows) < 20000:
            t = 365.25 * SOLAR_S * rng.random()
            if rng.random() * 1.3 <= 1.0 + 0.3 * math.cos(2 * math.pi * f_anti * t):
                rows.append((360.0 * rng.random(), t))
        with tempfile.TemporaryDirectory() as d:
            ev = write_events(d, rows, ("ra_deg", "time_s"))
            code, out, _ = run("harmonic", "--events", ev, "--time-column", "time_s", "--spurious-alpha", "0.01")
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "failed")
        self.assertIn("anti-sidereal", out["checks"]["failed"][0])

    def test_isotropic_in_time_passes_and_reports_frequencies(self):
        rng = random.Random(12)
        rows = [(360.0 * rng.random(), 365.25 * SOLAR_S * rng.random()) for _ in range(5000)]
        with tempfile.TemporaryDirectory() as d:
            ev = write_events(d, rows, ("ra_deg", "time_s"))
            code, out, _ = run("harmonic", "--events", ev, "--time-column", "time_s", "--spurious-alpha", "0.001")
        self.assertEqual(code, 0)
        self.assertEqual(set(out["checks"]["frequencies"]), {"solar", "sidereal", "anti-sidereal"})

    def test_bad_input_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            ev = write_events(d, [(400.0,)])
            code, out, _ = run("harmonic", "--events", ev)
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
