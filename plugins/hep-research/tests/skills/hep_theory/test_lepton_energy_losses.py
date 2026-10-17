"""lepton_energy_losses.py (Th2): synchrotron and inverse-Compton energy losses of relativistic electrons, the loss
time tau = E / b and the diffusion distance sqrt(4 D tau). Oracles: the Thomson-limit loss rate and loss time computed
here from the formulas (constants typed in, CODATA 2022); the Klein-Nishina function of Moderski et al. 2005 (Eqs. 3,
A10, A12) tends to 1 in the Thomson limit and to (9 / 2b^2)(ln b - 11/6) in the KN limit; unit checks. Inputs are
SYNTHETIC."""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "lepton_energy_losses.py"
sys.path.insert(0, str(SCRIPT.parent))

SIGMA_T = 6.6524587051e-29  # m^2, CODATA 2022
C = 299792458.0  # m/s
ME_GEV = 0.51099895069e-3  # GeV
EV_J = 1.602176634e-19
GEV_J = 1e9 * EV_J


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=600)
    out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout
    return p.returncode, out


def thomson_rate_gev_s(e_gev, u_ev_cm3):
    gamma = e_gev / ME_GEV
    u_j_m3 = u_ev_cm3 * 1e6 * EV_J
    return 4.0 / 3.0 * SIGMA_T * C * (gamma * gamma - 1.0) * u_j_m3 / GEV_J


class LeptonLossesCli(unittest.TestCase):
    def test_thomson_rate_and_loss_time(self):
        code, out = run("--energy-gev", "1000", "--b-microgauss", "3", "--field", "0.26:thomson", "--kn", "thomson")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["status"], "ok")
        row = out["rows"][0]
        b_ic = thomson_rate_gev_s(1000.0, 0.26)
        self.assertAlmostEqual(row["b_ic_gev_s"][0] / b_ic, 1.0, delta=1e-9)
        # synchrotron: U_B = B^2 / 8 pi (Gaussian), B = 3 microgauss
        u_b_ev_cm3 = (3e-6) ** 2 / (8 * math.pi) / (EV_J * 1e7)  # erg/cm^3 -> eV/cm^3
        self.assertAlmostEqual(row["u_b_ev_cm3"] / u_b_ev_cm3, 1.0, delta=1e-12)
        self.assertAlmostEqual(row["b_sync_gev_s"] / thomson_rate_gev_s(1000.0, u_b_ev_cm3), 1.0, delta=1e-9)
        self.assertAlmostEqual(row["tau_s"], 1000.0 / (row["b_sync_gev_s"] + b_ic), delta=1e-6 * row["tau_s"])
        self.assertIn("status", out["defaults_used"])

    def test_loss_time_scales_as_one_over_energy_in_the_thomson_limit(self):
        code, out = run("--energy-gev", "10", "100", "--b-microgauss", "1", "--field", "1:thomson", "--kn", "thomson")
        self.assertEqual(code, 0, out)
        t10, t100 = (r["tau_s"] for r in out["rows"])
        g10, g100 = 10 / ME_GEV, 100 / ME_GEV
        self.assertAlmostEqual(t10 / t100, 10 * (g100 ** 2 - 1) / (100 * (g10 ** 2 - 1)), delta=1e-9)

    def test_diffusion_distance_and_units(self):
        code, out = run("--energy-gev", "100", "--b-microgauss", "3", "--field", "1:thomson", "--kn", "thomson",
                        "--diffusion-cm2-s", "1e29")
        self.assertEqual(code, 0, out)
        row = out["rows"][0]
        self.assertAlmostEqual(row["distance_cm"], math.sqrt(4e29 * row["tau_s"]), delta=1e-9 * row["distance_cm"])
        self.assertAlmostEqual(row["tau_yr"], row["tau_s"] / (365.25 * 86400.0), delta=1e-9 * row["tau_yr"])
        pc_cm = 648000 / math.pi * 149597870700.0 * 100.0
        self.assertAlmostEqual(row["distance_kpc"], row["distance_cm"] / (1e3 * pc_cm), delta=1e-9 * row["distance_kpc"])

    def test_klein_nishina_reduces_the_ic_rate(self):
        code, thom = run("--energy-gev", "1000", "--b-microgauss", "1", "--field", "1:5000", "--kn", "thomson")
        code2, kn = run("--energy-gev", "1000", "--b-microgauss", "1", "--field", "1:5000", "--kn", "exact")
        self.assertEqual((code, code2), (0, 0))
        self.assertLess(kn["rows"][0]["b_ic_gev_s"][0], thom["rows"][0]["b_ic_gev_s"][0])
        b = kn["rows"][0]["b_tilde"][0]
        kt_ev = 1.380649e-23 * 5000 / EV_J
        self.assertAlmostEqual(b, 4 * (1000 / ME_GEV) * 2.8 * kt_ev / (ME_GEV * 1e9), delta=1e-9 * b)

    def test_bad_input(self):
        for args in (("--energy-gev", "1", "--b-microgauss", "-1", "--field", "1:thomson", "--kn", "thomson"),
                     ("--energy-gev", "0.0001", "--b-microgauss", "1", "--field", "1:thomson", "--kn", "thomson"),
                     ("--energy-gev", "1", "--b-microgauss", "1", "--field", "1:thomson", "--kn", "exact"),
                     ("--energy-gev", "1", "--b-microgauss", "1", "--field", "abc", "--kn", "thomson")):
            with self.subTest(args=args):
                code, out = run(*args)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")


class KleinNishinaFunction(unittest.TestCase):
    def setUp(self):
        import lepton_energy_losses as m
        self.m = m

    def test_thomson_limit(self):
        self.assertAlmostEqual(self.m.f_kn_exact(1e-2), 1.0, delta=0.05)
        self.assertAlmostEqual(self.m.f_kn_exact(1e-3), 1.0, delta=0.006)
        self.assertAlmostEqual(self.m.f_kn_approx(1e-6), 1.0, delta=2e-6)

    def test_kn_limit(self):
        for b in (1e5, 1e7):
            asym = 9.0 / (2.0 * b * b) * (math.log(b) - 11.0 / 6.0)
            with self.subTest(b=b):
                self.assertAlmostEqual(self.m.f_kn_exact(b) / asym, 1.0, delta=1e-3)

    def test_approximation_against_exact(self):
        # Moderski et al. 2005, Eq. (3) against Eqs. (A10, A12): measured here (the paper gives no accuracy figure);
        # the script's docstring states these bounds, so --kn approx is not used beyond them without saying so
        for b, tol in ((1e-3, 2e-4), (0.1, 0.01), (1.0, 0.03)):
            with self.subTest(b=b):
                self.assertAlmostEqual(self.m.f_kn_approx(b) / self.m.f_kn_exact(b), 1.0, delta=tol)
        for b in (10.0, 100.0, 1e3):
            with self.subTest(b=b):
                self.assertTrue(0.7 < self.m.f_kn_approx(b) / self.m.f_kn_exact(b) < 1.45)

    def test_dilogarithm(self):
        self.assertAlmostEqual(self.m.li2_neg(1.0), -math.pi ** 2 / 12, delta=1e-12)
        self.assertAlmostEqual(self.m.li2_neg(0.5), -0.4484142069236462, delta=1e-12)
        # inversion identity, with Li2(-0.1) from its power series
        series = sum((-0.1) ** k / k ** 2 for k in range(1, 40))
        self.assertAlmostEqual(self.m.li2_neg(10.0), -math.pi ** 2 / 6 - 0.5 * math.log(10.0) ** 2 - series, delta=1e-10)


if __name__ == "__main__":
    unittest.main()
