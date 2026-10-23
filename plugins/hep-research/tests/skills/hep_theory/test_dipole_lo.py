"""dipole_lo.py (Th19): Bessel functions, dipole-model limits, positivity, convergence and the alpha cancellation.

Tolerances fixed before comparing: Bessel values 1e-10 relative against the integral representation; small-r and
large-r limits of sigma_hat 1e-6 relative; convergence report below 1e-4 relative at the default settings.
"""
import importlib.util
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-theory/scripts/dipole_lo.py"
spec = importlib.util.spec_from_file_location("dipole_lo", SCRIPT)
dl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dl)
BASE = ["--x", "1e-3", "--Q2", "10", "--flavours", "u:2/3:0.14,d:-1/3:0.14,s:-1/3:0.14", "--model", "gbw",
        "--sigma0-mb", "23.0", "--x0", "3.0e-4", "--lambda", "0.29", "--parameter-source", "toy (test inputs)",
        "--x-variable", "mass-modified", "--fit-x-variable", "mass-modified", "--x-max", "0.01",
        "--alpha", "0.0072973525643", "--alpha-label", "alpha(0)"]


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=300)
    return r.returncode, json.loads(r.stdout)


def with_arg(args, flag, value):
    out = list(args)
    out[out.index(flag) + 1] = value
    return out


class DipoleLO(unittest.TestCase):
    def test_bessel_against_integral_representation(self):
        from scipy.integrate import quad
        from scipy.special import k0, k1
        for nu, fn in ((0, k0), (1, k1)):
            for xv in (0.05, 0.7, 3.0, 12.0):
                rep, _ = quad(lambda t: math.exp(-xv * math.cosh(t) + nu * t) * (1 + math.exp(-2 * nu * t)) / 2, 0, 60, epsabs=0,
                              epsrel=1e-13, limit=200)
                self.assertAlmostEqual(fn(xv) / rep, 1.0, delta=1e-10, msg=(nu, xv))
        # small-argument behaviour used by GBW Eq. 13: K_1(x) ~ 1/x
        self.assertAlmostEqual(k1(1e-6) * 1e-6, 1.0, delta=1e-6)

    def test_sigma_hat_limits(self):
        x, s0, x0, lam = 1e-3, 50.0, 3e-4, 0.29
        qs2 = (x0 / x) ** lam
        r = 1e-4
        self.assertAlmostEqual(dl.gbw_sigma_hat(r, x, s0, x0, lam) / (s0 * r * r * qs2 / 4), 1.0, delta=1e-6)
        self.assertAlmostEqual(dl.gbw_sigma_hat(1e3, x, s0, x0, lam) / s0, 1.0, delta=1e-12)

    def test_run_positivity_and_convergence(self):
        code, out = run(*BASE)
        self.assertEqual(code, 0, out)
        o = out["outputs"]
        self.assertGreater(o["sigma_T_GeV-2"], 0)
        self.assertGreater(o["sigma_L_GeV-2"], 0)
        self.assertLessEqual(o["F_L"], o["F_2"])
        for k in ("rel_change_doubling_nodes", "rel_change_doubling_rmax"):
            self.assertLess(max(o["convergence"][k].values()), 1e-4, k)
        self.assertAlmostEqual(o["sigma_T_mb"] / o["sigma_T_GeV-2"], 0.38937937217185936, delta=1e-12)

    def test_alpha_cancels_in_F2(self):
        _, a = run(*BASE)
        _, b = run(*with_arg(BASE, "--alpha", "0.0078"))
        self.assertAlmostEqual(a["outputs"]["F_2"] / b["outputs"]["F_2"], 1.0, delta=1e-12)
        self.assertAlmostEqual(b["outputs"]["sigma_T_GeV-2"] / a["outputs"]["sigma_T_GeV-2"], 0.0078 / 0.0072973525643,
                               delta=1e-10)

    def test_saturation_and_transparency_in_F2(self):
        # sigma_0 scales sigma linearly; a smaller x (larger Q_s) raises F_2 at fixed Q^2
        _, a = run(*BASE)
        _, b = run(*with_arg(BASE, "--sigma0-mb", "46.0"))
        self.assertAlmostEqual(b["outputs"]["F_2"] / a["outputs"]["F_2"], 2.0, delta=1e-10)
        _, c = run(*with_arg(BASE, "--x", "1e-4"))
        self.assertGreater(c["outputs"]["F_2"], a["outputs"]["F_2"])

    def test_sigma_L_colour_transparency_limit(self):
        # review: pins the normalization. m = 0, Q^2 >> Q_s^2: sigma_hat ~ sigma_0 r^2 Q_s^2 / 4 and int u^3 K_0^2 = 1/3
        # give sigma_L = (6 alpha / 4 pi^2) e^2 sigma_0 Q_s^2 (2 pi / 3) / Q^2 (derived independently of the code)
        args = with_arg(with_arg(with_arg(BASE, "--flavours", "u:2/3:0"), "--Q2", "1e4"), "--x", "1e-3")
        args = [*args, "--r-min", "1e-6"]
        _, out = run(*args)
        alpha, s0 = 0.0072973525643, 23.0 / 0.38937937217185936
        qs2 = (3.0e-4 / 1e-3) ** 0.29
        hand = 6 * alpha / (4 * math.pi ** 2) * (4 / 9) * s0 * qs2 * (2 * math.pi / 3) / 1e4
        self.assertAlmostEqual(out["outputs"]["sigma_L_GeV-2"] / hand, 1.0, delta=2e-3)

    def test_mass_modified_x_is_eq21(self):
        # one massive flavour: mass-modified at x equals Bjorken at x~ = x (Q^2 + 4 m^2)/Q^2 (GBW Eq. 21)
        m, q2, x = 1.4, 10.0, 1e-3
        a_args = with_arg(with_arg(BASE, "--flavours", f"c:2/3:{m}"), "--x", str(x))
        _, a = run(*a_args)
        xt = x * (q2 + 4 * m * m) / q2
        b_args = with_arg(with_arg(with_arg(a_args, "--x", repr(xt)), "--x-variable", "bjorken"), "--fit-x-variable",
                          "bjorken")
        _, b = run(*b_args)
        self.assertAlmostEqual(a["outputs"]["F_2"] / b["outputs"]["F_2"], 1.0, delta=1e-12)

    def test_refusals_and_rejections(self):
        code, out = run(*with_arg(BASE, "--x-variable", "bjorken"))
        self.assertEqual((code, out["status"]), (1, "refused"))  # x variable differs from the fit's
        code, out = run(*with_arg(BASE, "--x", "0.05"))
        self.assertEqual((code, out["status"]), (1, "refused"))  # above the declared x limit
        code, _ = run(*with_arg(BASE, "--model", "iim"))
        self.assertEqual(code, 2)
        code, _ = run(*with_arg(BASE, "--lambda", "-0.2"))
        self.assertEqual(code, 2)
        code, _ = run(*with_arg(BASE, "--flavours", "u:2/3"))
        self.assertEqual(code, 2)
        code, out = run(*with_arg(BASE, "--flavours", "u:2/0:0.14"))
        self.assertEqual((code, out["status"]), (2, "rejected"))  # division by zero in the charge
        code, _ = run(*with_arg(BASE, "--flavours", "u:2/3:0.14,u:2/3:0.14"))
        self.assertEqual(code, 2)  # duplicate flavour


if __name__ == "__main__":
    unittest.main()
