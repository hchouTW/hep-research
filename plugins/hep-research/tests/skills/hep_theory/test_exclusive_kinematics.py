"""exclusive_kinematics.py (Th20): t_min, xi, the BMK and Trento azimuths and diffractive variables against
four-vector arithmetic.

Tolerances fixed before comparing: 1e-9 relative for invariants and angles.
"""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-theory/scripts/exclusive_kinematics.py"
M = 0.938272


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)
    return r.returncode, json.loads(r.stdout)


def fmt(v):
    return ",".join(repr(float(c)) for c in v)


def dot(a, b):
    return a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3]


def dvcs_event(phi, cos_theta_gamma, e=27.6, xb=0.1, q2=2.5):
    """Target rest frame; BMK axes: z' = -q^, x' along the lepton's transverse momentum; the real photon at polar angle
    theta_gamma to q^ and azimuth phi in the (x', y') plane."""
    nu = q2 / (2 * M * xb)
    ep = e - nu
    # scattered lepton angle from Q^2 = 4 E E' sin^2(theta/2)
    th = 2 * math.asin(math.sqrt(q2 / (4 * e * ep)))
    l = [e, 0.0, 0.0, e]
    lp = [ep, ep * math.sin(th), 0.0, ep * math.cos(th)]
    q = [l[i] - lp[i] for i in range(4)]
    # rotate so that q points along -z with the lepton in the xz plane, x component of l positive
    qv = q[1:]
    qn = math.sqrt(sum(c * c for c in qv))
    zh = [-c / qn for c in qv]
    lt = [l[1 + i] - sum(l[1 + j] * (-zh[j]) for j in range(3)) * (-zh[i]) for i in range(3)]
    ltn = math.sqrt(sum(c * c for c in lt))
    xh = [c / ltn for c in lt]
    yh = [zh[1] * xh[2] - zh[2] * xh[1], zh[2] * xh[0] - zh[0] * xh[2], zh[0] * xh[1] - zh[1] * xh[0]]
    # real photon energy from the recoil mass-shell condition: (P + q - k)^2 = M^2, k^2 = 0
    qhat = [-c for c in zh]
    st = math.sqrt(1 - cos_theta_gamma ** 2)
    kdir = [cos_theta_gamma * qhat[i] + st * (math.cos(phi) * xh[i] + math.sin(phi) * yh[i]) for i in range(3)]
    # M^2 = (P + q - k)^2 = M^2 - Q^2 + 2 M nu - 2 k (M + nu - |q| cos)
    kk = (2 * M * nu - q2) / (2 * (M + nu - qn * cos_theta_gamma))
    k = [kk] + [kk * c for c in kdir]
    return l, [M, 0, 0, 0], lp, k


class ExclusiveKinematics(unittest.TestCase):
    def test_tmin_against_four_vectors(self):
        # the extreme t over photon directions is t_min (photon along q)
        xb, q2 = 0.2, 2.0
        _, out = run("dvcs", "--xB", str(xb), "--Q2", str(q2), "--t", "-1.0", "--M", str(M))
        l, P, lp, k = dvcs_event(0.0, 1.0, xb=xb, q2=q2)
        pp = [P[i] + l[i] - lp[i] - k[i] for i in range(4)]
        t = dot([pp[i] - P[i] for i in range(4)], [pp[i] - P[i] for i in range(4)])
        self.assertAlmostEqual(out["outputs"]["t_min_GeV2"] / t, 1.0, delta=1e-9)
        eps2 = 4 * xb * xb * M * M / q2
        self.assertAlmostEqual(out["outputs"]["epsilon"], math.sqrt(eps2), delta=1e-12)

    def test_xi_forms(self):
        _, out = run("dvcs", "--xB", "0.2", "--Q2", "2", "--t", "-0.3", "--M", str(M))
        o = out["outputs"]
        self.assertAlmostEqual(o["xi_leading_power"], 0.2 / 1.8, delta=1e-14)
        self.assertAlmostEqual(o["xi_BMK_Eq4"], 0.2 * (1 - 0.3 / 4) / (1.8 - 0.2 * 0.3 / 2), delta=1e-14)

    def test_bmk_and_trento_azimuths(self):
        for phi in (0.4, 1.9, -2.5):
            l, P, lp, k = dvcs_event(phi, 0.9)
            code, out = run("angles", "--l", fmt(l), "--P", fmt(P), "--lp", fmt(lp), "--q2", fmt(k),
                            "--azimuth-convention", "both")
            self.assertEqual(code, 0, out)
            o = out["outputs"]
            # the photon was built at azimuth phi in the BMK frame (axis -q^): about q^ (Trento) its azimuth is -phi,
            # and the recoiled nucleon, back to back in the transverse plane, sits at phi + pi in the BMK frame
            self.assertAlmostEqual(math.remainder(o["phi_Trento_rad"] + phi, 2 * math.pi), 0.0, delta=1e-9)
            self.assertAlmostEqual(math.remainder(o["phi_BMK_rad"] - (phi + math.pi), 2 * math.pi), 0.0, delta=1e-9)
            # derived relation: phi_Trento = pi - phi_BMK (mod 2 pi)
            self.assertAlmostEqual(math.remainder(o["phi_Trento_rad"] - (math.pi - o["phi_BMK_rad"]), 2 * math.pi),
                                   0.0, delta=1e-9)
            self.assertLess(o["t_GeV2"], 0)

    def test_diffractive(self):
        _, out = run("diffractive", "--x", "1e-3", "--Q2", "10", "--t", "-0.2", "--MX2", "20", "--M", str(M))
        o = out["outputs"]
        self.assertAlmostEqual(o["beta_times_x_P"], 1e-3, delta=1e-15)
        self.assertAlmostEqual(o["beta"], 10 / (10 + 20 + 0.2), delta=1e-14)

    def test_rejections(self):
        code, _ = run("dvcs", "--xB", "0.2", "--Q2", "2", "--t", "-0.01", "--M", str(M))
        self.assertEqual(code, 2)  # |t| < |t_min|
        code, _ = run("dvcs", "--xB", "0.2", "--Q2", "2", "--t", "0.1", "--M", str(M))
        self.assertEqual(code, 2)
        code, _ = run("diffractive", "--x", "0.5", "--Q2", "10", "--t", "-0.2", "--MX2", "50", "--M", str(M))
        self.assertEqual(code, 2)  # x_P > 1
        l, P, lp, k = dvcs_event(0.3, 0.9)
        code, _ = run("angles", "--l", fmt(l), "--P", fmt(P), "--lp", fmt(lp), "--q2", fmt(k))
        self.assertEqual(code, 2)  # no convention
        bad = [k[0] * 1.3, *k[1:]]  # recoil off its mass shell
        code, _ = run("angles", "--l", fmt(l), "--P", fmt(P), "--lp", fmt(lp), "--q2", fmt(bad), "--azimuth-convention",
                      "both")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
