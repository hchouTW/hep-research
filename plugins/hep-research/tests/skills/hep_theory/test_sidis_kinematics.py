"""sidis_kinematics.py (Th18): SIDIS invariants and Trento angles against constructed four-vectors.

Tolerances fixed before comparing: 1e-10 absolute for angles and invariants.
"""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-theory/scripts/sidis_kinematics.py"
M = 0.938


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)
    return r.returncode, json.loads(r.stdout)


def fmt(v):
    return ",".join(repr(float(c)) for c in v)


def unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return [c / n for c in v]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def event(phi, theta_l=0.2, e=27.6, ep=17.0, z=0.4, pht=0.6, mh=0.14):
    """Target rest frame: lepton along +z, scattered lepton in the xz plane, hadron at azimuth phi around q."""
    l = [e, 0.0, 0.0, e]
    lp = [ep, ep * math.sin(theta_l), 0.0, ep * math.cos(theta_l)]
    q = [l[i] - lp[i] for i in range(4)]
    qhat = unit(q[1:])
    lperp = [l[1 + i] - sum(l[1 + j] * qhat[j] for j in range(3)) * qhat[i] for i in range(3)]
    e1 = unit(lperp)
    e2 = cross(qhat, e1)
    nu = q[0]
    eh = z * nu  # z = P.P_h / P.q = E_h / nu in the target rest frame
    pl = math.sqrt(eh * eh - mh * mh - pht * pht)
    ph3 = [pl * qhat[i] + pht * (math.cos(phi) * e1[i] + math.sin(phi) * e2[i]) for i in range(3)]
    return l, [M, 0, 0, 0], lp, [eh] + ph3, qhat, e1, e2


def boost_z(v, beta):
    g = 1 / math.sqrt(1 - beta * beta)
    return [g * (v[0] + beta * v[3]), v[1], v[2], g * (v[3] + beta * v[0])]


class SidisKinematics(unittest.TestCase):
    def args(self, l, P, lp, ph, extra=()):
        return ["vectors", "--l", fmt(l), "--P", fmt(P), "--lp", fmt(lp), "--ph", fmt(ph),
                "--azimuth-convention", "trento", *extra]

    def test_invariants_and_phi_h(self):
        for phi in (0.3, 2.0, -1.2, 3.0):
            l, P, lp, ph, *_ = event(phi)
            code, out = run(*self.args(l, P, lp, ph))
            self.assertEqual(code, 0, out)
            o = out["outputs"]
            q = [l[i] - lp[i] for i in range(4)]
            Q2 = -(q[0] ** 2 - q[1] ** 2 - q[2] ** 2 - q[3] ** 2)
            self.assertAlmostEqual(o["Q2_GeV2"], Q2, delta=1e-10)
            self.assertAlmostEqual(o["x"], Q2 / (2 * M * q[0]), delta=1e-10)
            self.assertAlmostEqual(o["y"], q[0] / l[0], delta=1e-10)
            self.assertAlmostEqual(o["z"], 0.4, delta=1e-10)
            self.assertAlmostEqual(o["PhT_GeV"], 0.6, delta=1e-10)
            self.assertAlmostEqual(o["phi_h_rad"], phi, delta=1e-10)
            self.assertAlmostEqual(o["abs_qT_GeV_leading_power"], 0.6 / 0.4, delta=1e-10)
            g2 = 4 * M * M * o["x"] ** 2 / Q2
            y = o["y"]
            self.assertAlmostEqual(o["epsilon"], (1 - y - g2 * y * y / 4) / (1 - y + y * y / 2 + g2 * y * y / 4), delta=1e-12)

    def test_frame_independence_under_boost_along_z(self):
        l, P, lp, ph, *_ = event(0.8)
        _, rest = run(*self.args(l, P, lp, ph))
        b = -0.99  # target moving towards the lepton: a collider-like frame
        _, moving = run(*self.args(*(boost_z(v, b) for v in (l, P, lp, ph))))
        for k in ("x", "y", "Q2_GeV2", "z", "PhT_GeV", "phi_h_rad"):
            self.assertAlmostEqual(rest["outputs"][k], moving["outputs"][k], delta=1e-8, msg=k)

    def test_mirror_reflection_and_spin_flip(self):
        l, P, lp, ph, *_ = event(0.7)
        spin = [0.0, 1.0, 0.0]
        _, a = run(*self.args(l, P, lp, ph, ["--S", fmt(spin)]))
        mirror = [[v[0], v[1], -v[2], v[3]] for v in (l, P, lp, ph)]
        _, b = run(*self.args(*mirror, ["--S", fmt([0.0, -1.0, 0.0])]))
        self.assertAlmostEqual(b["outputs"]["phi_h_rad"], -a["outputs"]["phi_h_rad"], delta=1e-10)
        self.assertAlmostEqual(b["outputs"]["phi_S_rad"], -a["outputs"]["phi_S_rad"], delta=1e-10)
        _, c = run(*self.args(l, P, lp, ph, ["--S", fmt([0.0, -1.0, 0.0])]))
        d = (c["outputs"]["phi_S_rad"] - a["outputs"]["phi_S_rad"]) % (2 * math.pi)
        self.assertAlmostEqual(d, math.pi, delta=1e-10)  # flipping the target spin shifts phi_S by pi

    def test_classification(self):
        base = ["classify", "--Q2", "4", "--z", "0.5", "--tmd-max", "0.25", "--collinear-min", "1.0"]
        for pht, region in (("0.2", "TMD"), ("0.5", "matching"), ("1.2", "collinear")):
            _, out = run(*base, "--PhT", pht)
            self.assertEqual(out["outputs"]["region"], region, pht)

    def test_rejections(self):
        l, P, lp, ph, *_ = event(0.5)
        code, _ = run("vectors", "--l", fmt(l), "--P", fmt(P), "--lp", fmt(lp), "--ph", fmt(ph))
        self.assertEqual(code, 2)  # no azimuth convention
        for extra in (["--Q2", "4", "--z", "1.2", "--PhT", "0.1"], ["--Q2", "4", "--z", "0.5", "--PhT", "-0.1"]):
            code, _ = run("classify", *extra, "--tmd-max", "0.2", "--collinear-min", "1")
            self.assertEqual(code, 2, extra)
        code, _ = run("classify", "--Q2", "4", "--z", "0.5", "--PhT", "0.1", "--tmd-max", "1", "--collinear-min", "0.2")
        self.assertEqual(code, 2)  # thresholds not ordered
        q = [l[i] - lp[i] for i in range(4)]
        along = [0.4 * q[0], *(0.4 * c for c in q[1:])]
        along[0] = math.sqrt(sum(c * c for c in along[1:]) + 0.14 ** 2)
        code, _ = run(*self.args(l, P, lp, along))
        self.assertEqual(code, 2)  # hadron along q: phi_h undefined
        code, _ = run(*self.args(l, P, lp, [1.0, 0.3, 0.2, 3.0]))
        self.assertEqual(code, 2)  # spacelike hadron four-vector
        code, _ = run(*self.args(l, [-M, 0, 0, 0], lp, ph))
        self.assertEqual(code, 2)  # target energy not positive


if __name__ == "__main__":
    unittest.main()
