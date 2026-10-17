"""dm_direct_rate.py (Th5): standard-halo velocity integral, Helm form factor, spin-independent recoil rate, J and D
factors and indirect-detection flux prefactors. Oracles: the closed-form velocity integral without an escape speed
and its v_E -> 0 limit; the truncated-Maxwellian normalization (eta at v_min = 0); eta = 0 above v_esc + v_E;
F(0) = 1 and the first zero of the Helm form factor; rate scalings; the uniform-sphere J factor of the PDG Dark Matter
review, Eq. (27.22); the self-conjugate / Dirac factor 1/2 vs 1/4. Inputs are SYNTHETIC; no halo value is built in."""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "dm_direct_rate.py"
sys.path.insert(0, str(SCRIPT.parent))

V0, VESC, VE = 238.0, 544.0, 250.0  # km/s, SYNTHETIC inputs (the script has no defaults)


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


def eta_no_escape(vmin, v0, ve):
    return (math.erf((vmin + ve) / v0) - math.erf((vmin - ve) / v0)) / (2 * ve)


class VelocityIntegral(unittest.TestCase):
    def setUp(self):
        import dm_direct_rate as m
        self.m = m

    def test_closed_form_without_escape_speed(self):
        for vmin in (0.0, 100.0, 300.0, 600.0):
            with self.subTest(vmin=vmin):
                self.assertAlmostEqual(self.m.eta_shm(vmin, V0, 1e5, VE) / eta_no_escape(vmin, V0, VE), 1.0,
                                       delta=1e-7)

    def test_earth_at_rest_limit(self):
        for vmin in (50.0, 200.0):
            with self.subTest(vmin=vmin):
                limit = 2.0 / (math.sqrt(math.pi) * V0) * math.exp(-(vmin / V0) ** 2)
                self.assertAlmostEqual(self.m.eta_shm(vmin, V0, 1e5, 1e-3) / limit, 1.0, delta=1e-5)

    def test_truncated_normalization(self):
        z = VESC / V0
        norm = math.pi ** 1.5 * V0 ** 3 * (math.erf(z) - 2 * z / math.sqrt(math.pi) * math.exp(-z * z))
        mean_inverse_speed = 2 * math.pi * V0 ** 2 * (1 - math.exp(-z * z)) / norm
        self.assertAlmostEqual(self.m.eta_shm(0.0, V0, VESC, 1e-3) / mean_inverse_speed, 1.0, delta=1e-5)

    def test_zero_above_the_kinematic_end_and_decreasing(self):
        self.assertEqual(self.m.eta_shm(VESC + VE + 1.0, V0, VESC, VE), 0.0)
        values = [self.m.eta_shm(v, V0, VESC, VE) for v in range(0, 800, 50)]
        self.assertTrue(all(a >= b for a, b in zip(values, values[1:])))


class HelmFormFactor(unittest.TestCase):
    def setUp(self):
        import dm_direct_rate as m
        self.m = m

    def test_unity_at_zero_and_first_zero(self):
        self.assertAlmostEqual(self.m.helm_f2(0.0, 131), 1.0, delta=1e-12)
        r1 = self.m.helm_radius_fm(131)
        self.assertLess(self.m.helm_f2(4.493409457909064 / r1, 131), 1e-20)

    def test_lewin_smith_radius(self):
        c = 1.23 * 131 ** (1 / 3) - 0.60
        self.assertAlmostEqual(self.m.helm_radius_fm(131), math.sqrt(c * c + 7 / 3 * math.pi ** 2 * 0.52 ** 2 - 5 * 0.81),
                               delta=1e-12)


class RateCli(unittest.TestCase):
    BASE = ["rate", "--mass-gev", "100", "--sigma-n-cm2", "1e-45", "--mass-number", "131", "--nucleus-mass-gev", "122",
            "--rho-gev-cm3", "0.3", "--v0-km-s", str(V0), "--vesc-km-s", str(VESC), "--vearth-km-s", str(VE),
            "--er-kev", "5", "10", "20", "40", "--form-factor", "helm"]

    def test_rate_and_scalings(self):
        code, out = run(*self.BASE)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["status"], "ok")
        r = [row["dR_dE_per_kg_day_kev"] for row in out["rows"]]
        self.assertTrue(all(x > 0 for x in r))
        self.assertTrue(all(a > b for a, b in zip(r, r[1:])))
        args2 = [a if a != "1e-45" else "2e-45" for a in self.BASE]
        args2 = [a if a != "0.3" else "0.6" for a in args2]
        code, out2 = run(*args2)
        self.assertAlmostEqual(out2["rows"][0]["dR_dE_per_kg_day_kev"] / r[0], 4.0, delta=1e-9)
        self.assertIn("to-verify", out["conventions"]["reference_rate"])

    def test_no_form_factor_is_point_like(self):
        args = [a if a != "helm" else "none" for a in self.BASE]
        code, out = run(*args)
        self.assertEqual(code, 0, out)
        self.assertTrue(all(row["form_factor_sq"] == 1.0 for row in out["rows"]))

    def test_missing_inputs_are_refused(self):
        args = [a for a in self.BASE if a not in ("--rho-gev-cm3", "0.3")]
        code, out = run(*args)
        self.assertEqual(code, 2)
        code, out = run(*[a if a != "100" else "-1" for a in self.BASE])
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")


class JFactor(unittest.TestCase):
    def setUp(self):
        import dm_direct_rate as m
        self.m = m

    def test_uniform_sphere_matches_pdg_27_22(self):
        rho, r, d = 0.5, 0.1, 10.0  # GeV/cm^3, kpc, kpc
        kpc_cm = 648000 / math.pi * 149597870700.0 * 100.0 * 1e3
        j = self.m.j_factor({"profile": "uniform", "rho": rho, "radius_kpc": r}, d, math.degrees(math.asin(r / d)) * 1.01)
        approx = 4 * math.pi * (r * kpc_cm) ** 3 * rho ** 2 / (3 * (d * kpc_cm) ** 2)
        self.assertAlmostEqual(j["J_gev2_cm5"] / approx, 1.0, delta=1e-3)
        self.assertAlmostEqual(j["D_gev_cm2"] / (approx / rho), 1.0, delta=1e-3)

    def test_nfw_converges(self):
        halo = {"profile": "nfw", "rho_s": 0.3, "r_s_kpc": 20.0, "r_max_kpc": 200.0}
        a = self.m.j_factor(halo, 8.0, 5.0, n=200)["J_gev2_cm5"]
        b = self.m.j_factor(halo, 8.0, 5.0, n=400)["J_gev2_cm5"]
        self.assertAlmostEqual(a / b, 1.0, delta=1e-3)

    def test_flux_prefactor_conventions(self):
        code, maj = run("flux", "--annihilation", "--sigmav-cm3-s", "3e-26", "--mass-gev", "100", "--j-gev2-cm5", "1e19",
                        "--yield", "1", "--particle", "self-conjugate")
        code2, dirac = run("flux", "--annihilation", "--sigmav-cm3-s", "3e-26", "--mass-gev", "100", "--j-gev2-cm5",
                           "1e19", "--yield", "1", "--particle", "dirac")
        self.assertEqual((code, code2), (0, 0))
        self.assertAlmostEqual(maj["flux_cm2_s"] / dirac["flux_cm2_s"], 2.0, delta=1e-12)
        self.assertAlmostEqual(maj["flux_cm2_s"], 0.5 * 3e-26 * 1e19 / (4 * math.pi * 100.0 ** 2), delta=1e-30)
        code, dec = run("flux", "--decay", "--lifetime-s", "1e27", "--mass-gev", "100", "--d-gev-cm2", "1e22",
                        "--yield", "2")
        self.assertEqual(code, 0, dec)
        self.assertAlmostEqual(dec["flux_cm2_s"], 2 * 1e22 / (4 * math.pi * 100.0 * 1e27), delta=1e-20)


if __name__ == "__main__":
    unittest.main()
