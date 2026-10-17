"""M6: cosmic_ray_flux.py takes the bin-width unit as a free reported string and, beyond the Feldman-Cousins grid,
an asymptotic profile-likelihood interval (`auto` selects it); orbit_averaged_geomagnetic_cutoff.py maps an
inclination above 90 deg to 180 - i and takes --edges. Oracles: asymptotic within 5% of Feldman-Cousins at the grid
edge; i and 180 - i agree; default outputs unchanged. SYNTHETIC inputs."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
S = ROOT / "skills" / "hep-measurement" / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(S))
from cosmic_ray_flux import flux_from_counts  # noqa: E402
import orbit_averaged_geomagnetic_cutoff as orb  # noqa: E402


def run(script, *args):
    p = subprocess.run([sys.executable, "-B", str(S / script), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


class FreeUnit(unittest.TestCase):
    def test_any_unit_string_is_reported_not_converted(self):
        code, out, _ = run("cosmic_ray_flux.py", "--counts", "4", "--exposure", "2e7", "--bin-width", "0.7",
                           "--bin-width-unit", "MV per nucleon")
        self.assertEqual(code, 0)
        self.assertEqual(out["bin_width_unit"], "MV per nucleon")
        ref = flux_from_counts(4, 2e7, 0.7, bin_width_unit="GV")
        self.assertEqual(out["flux"], ref["flux"])

    def test_empty_unit_is_refused(self):
        code, _, err = run("cosmic_ray_flux.py", "--counts", "4", "--exposure", "2e7", "--bin-width", "1",
                           "--bin-width-unit", " ")
        self.assertEqual(code, 2)
        self.assertIn("--bin-width-unit", err)


class Asymptotic(unittest.TestCase):
    def test_close_to_feldman_cousins_at_the_grid_edge(self):
        for n, b in ((200, 100), (250, 50)):  # the largest counts the Feldman-Cousins grid accepts
            fc = flux_from_counts(n, 1.0, 1.0, background=b, method="feldman-cousins")
            asy = flux_from_counts(n, 1.0, 1.0, background=b, method="asymptotic")
            with self.subTest(n=n, b=b):
                self.assertEqual(asy["method_id"], "asymptotic")
                self.assertAlmostEqual(asy["flux_lower"] / fc["flux_lower"], 1.0, delta=0.05)
                self.assertAlmostEqual(asy["flux_upper"] / fc["flux_upper"], 1.0, delta=0.05)

    def test_auto_beyond_the_grid_uses_the_asymptotic_interval(self):
        code, out, _ = run("cosmic_ray_flux.py", "--counts", "4800", "--exposure", "1", "--bin-width", "1",
                           "--background", "100", "--bin-width-unit", "GV")
        self.assertEqual(code, 0)
        self.assertEqual(out["method_id"], "asymptotic")
        self.assertLess(out["flux_lower"], 4700)
        self.assertGreater(out["flux_upper"], 4700)
        code, out, _ = run("cosmic_ray_flux.py", "--counts", "4800", "--exposure", "1", "--bin-width", "1",
                           "--background", "100", "--background-sigma", "10", "--bin-width-unit", "GV")
        self.assertEqual(code, 0)
        self.assertEqual(out["method_id"], "asymptotic")
        self.assertTrue(out["approximate"])

    def test_explicit_feldman_cousins_beyond_the_grid_still_exits_3(self):
        code, _, err = run("cosmic_ray_flux.py", "--counts", "4800", "--exposure", "1", "--bin-width", "1",
                           "--background", "100", "--method", "feldman-cousins", "--bin-width-unit", "GV")
        self.assertEqual(code, 3)
        self.assertIn("asymptotic", err)

    def test_auto_inside_the_grid_is_unchanged(self):
        self.assertEqual(flux_from_counts(40, 1.0, 1.0, background=4)["method_id"], "feldman-cousins")
        self.assertEqual(flux_from_counts(40, 1.0, 1.0)["method_id"], "garwood")


class Orbit(unittest.TestCase):
    def test_retrograde_maps_to_180_minus_i(self):
        a = orb.orbit_cutoff_profile(51.6, 1.06)
        b = orb.orbit_cutoff_profile(180.0 - 51.6, 1.06)
        # 180 - 128.4 is 51.599999999999994 in floating point: agreement to rounding
        for k in ("min_cutoff_gv", "max_cutoff_gv", "time_weighted_mean_cutoff_gv"):
            self.assertAlmostEqual(a[k] / b[k], 1.0, delta=1e-12, msg=k)
        for x, y in zip(a["latitude_range_deg"], b["latitude_range_deg"]):
            self.assertAlmostEqual(x, y, delta=1e-10)
        self.assertEqual(b["inclination_deg"], 180.0 - 51.6)
        self.assertAlmostEqual(b["inclination_effective_deg"], 51.6, delta=1e-12)

    def test_default_exposure_table_edges_unchanged_and_edges_option(self):
        t = orb.tilted_dipole_profile(51.6, 80.7, -72.7, 1.06, days=0.2, step_s=60.0)
        self.assertEqual([r["cutoff_gv"][0] for r in t["exposure_vs_cutoff"]],
                         [0.0, 0.5, 1, 2, 3, 4, 6, 8, 10, 12, 14, 16])
        t2 = orb.tilted_dipole_profile(51.6, 80.7, -72.7, 1.06, days=0.2, step_s=60.0, edges=[0, 5, 10, 20])
        self.assertEqual([r["cutoff_gv"] for r in t2["exposure_vs_cutoff"]], [[0, 5], [5, 10], [10, 20]])
        self.assertAlmostEqual(sum(r["time_fraction"] for r in t2["exposure_vs_cutoff"]), 1.0, delta=1e-12)
        code, out, _ = run("orbit_averaged_geomagnetic_cutoff.py", "--inclination", "128.4", "--radius-re", "1.06",
                           "--edges", "0,5,10,20")
        self.assertEqual(code, 0)
        self.assertEqual([r["cutoff_gv"] for r in out["exposure_vs_cutoff"]], [[0, 5], [5, 10], [10, 20]])

    def test_bad_edges_are_refused(self):
        code, _, _ = run("orbit_averaged_geomagnetic_cutoff.py", "--inclination", "51.6", "--edges", "5,1")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
