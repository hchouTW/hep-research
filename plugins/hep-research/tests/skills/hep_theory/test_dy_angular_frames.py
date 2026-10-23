"""drell_yan_lo.py frames, lam-tung, coefficients (Th15): the CS <-> HX rotation against four-vector geometry and a
direct numerical rotation of the angular distribution.

Tolerances fixed before comparing: 1e-10 for the rotation angle and invariants; 1e-9 for the least-squares refit of
the rotated distribution on a 60 x 120 grid (the rotated distribution lies exactly in the fitted span).
"""
import importlib.util
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-theory/scripts/drell_yan_lo.py"
spec = importlib.util.spec_from_file_location("drell_yan_lo", SCRIPT)
dy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dy)


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)
    return r.returncode, json.loads(r.stdout)


def boost_to_rest(v, q):
    """Boost four-vector v into the rest frame of q (E, px, py, pz)."""
    m = math.sqrt(q[0] ** 2 - q[1] ** 2 - q[2] ** 2 - q[3] ** 2)
    b = np.array(q[1:]) / q[0]
    g = q[0] / m
    bp = float(np.dot(b, v[1:]))
    b2 = float(np.dot(b, b))
    e = g * (v[0] - bp)
    p = np.array(v[1:]) + ((g - 1) * bp / b2 - g * v[0]) * b
    return e, p


def axes(m, qt, y, rs=13000.0):
    """z_HX, z_CS, y axis in the dilepton rest frame (Faccioli et al. 2010, Eqs. 25, 27; beam 1 along +z)."""
    mt = math.sqrt(m * m + qt * qt)
    q = (mt * math.cosh(y), qt, 0.0, mt * math.sinh(y))
    p1 = (rs / 2, 0.0, 0.0, rs / 2)
    p2 = (rs / 2, 0.0, 0.0, -rs / 2)
    e1, v1 = boost_to_rest(p1, q)
    e2, v2 = boost_to_rest(p2, q)
    zhx = -(v1 + v2) / np.linalg.norm(v1 + v2)
    zcs = e2 * v1 - e1 * v2
    zcs /= np.linalg.norm(zcs)
    yax = np.cross(v1, v2)
    yax /= np.linalg.norm(yax)
    return zhx, zcs, yax


class Frames(unittest.TestCase):
    def test_rotation_angle_matches_geometry(self):
        for m, qt, y in ((10.0, 5.0, 0.5), (91.0, 30.0, -1.2), (6.0, 2.0, 2.0), (20.0, 15.0, 0.0)):
            zhx, zcs, yax = axes(m, qt, y)
            geo = math.atan2(float(np.dot(np.cross(zhx, zcs), yax)), float(np.dot(zhx, zcs)))
            d = dy.hx_to_cs_angle(m, qt, y)
            self.assertAlmostEqual(abs(geo), d, delta=1e-10)  # magnitude: Eq. 28 against the boosted axes

    def test_rotation_against_direct_numerical_rotation(self):
        lam, mu, nu = 0.6, 0.15, 0.3
        for d in (0.4, -1.1, 2.5):
            th = np.linspace(0.01, math.pi - 0.01, 60)
            ph = np.linspace(0, 2 * math.pi, 120, endpoint=False)
            T, P = np.meshgrid(th, ph, indexing="ij")
            # direction in the new frame -> old frame: r_old = R_y^-1(d) r_new (Faccioli et al. Eqs. 18-19)
            xn, yn, zn = np.sin(T) * np.cos(P), np.sin(T) * np.sin(P), np.cos(T)
            xo = math.cos(d) * xn + math.sin(d) * zn
            zo = -math.sin(d) * xn + math.cos(d) * zn
            yo = yn
            cto = zo
            sto = np.sqrt(np.clip(1 - zo ** 2, 0, None))
            pho = np.arctan2(yo, xo)
            w = 1 + lam * cto ** 2 + mu * 2 * sto * cto * np.cos(pho) + nu / 2 * sto ** 2 * np.cos(2 * pho)
            basis = np.stack([np.ones_like(T), np.cos(T) ** 2, np.sin(2 * T) * np.cos(P),
                              np.sin(T) ** 2 * np.cos(2 * P)], axis=-1).reshape(-1, 4)
            c, *_ = np.linalg.lstsq(basis, w.reshape(-1), rcond=None)
            fit = {"lambda": c[1] / c[0], "mu": c[2] / c[0], "nu": 2 * c[3] / c[0]}
            got = dy.rotate(lam, mu, nu, d)
            for k in fit:
                self.assertAlmostEqual(got[k], fit[k], delta=1e-9, msg=(d, k))

    def test_invariants_and_round_trip(self):
        args = ["frames", "--M", "10", "--qT", "6", "--y", "0.8", "--lambda", "0.5", "--mu", "0.1", "--nu", "0.4"]
        code, out = run(*args, "--from", "CS", "--to", "HX")
        self.assertEqual(code, 0, out)
        o = out["outputs"]
        for k in ("lambda_tilde", "F", "lam_tung_1_minus_lambda_minus_2nu"):
            if k != "lam_tung_1_minus_lambda_minus_2nu":
                self.assertAlmostEqual(o["invariants_before"][k], o["invariants_after"][k], delta=1e-10)
        new = o["output"]
        _, back = run("frames", "--M", "10", "--qT", "6", "--y", "0.8", "--lambda", repr(new["lambda"]),
                      "--mu", repr(new["mu"]), "--nu", repr(new["nu"]), "--from", "HX", "--to", "CS")
        for k, v in (("lambda", 0.5), ("mu", 0.1), ("nu", 0.4)):
            self.assertAlmostEqual(back["outputs"]["output"][k], v, delta=1e-10)

    def test_lam_tung_is_frame_independent_when_it_holds(self):
        lam, nu = 0.6, 0.2  # 1 - lambda - 2 nu = 0
        for d in (0.3, 1.0, 2.0):
            r = dy.rotate(lam, 0.1, nu, d)
            self.assertAlmostEqual(1 - r["lambda"] - 2 * r["nu"], 0.0, delta=1e-12)
            self.assertAlmostEqual(dy.invariants(r["lambda"], r["mu"], r["nu"])["lambda_tilde"], 1.0, delta=1e-12)

    def test_transverse_at_zero_qt(self):
        code, out = run("frames", "--M", "6", "--qT", "0", "--y", "0.5", "--lambda", "1", "--mu", "0", "--nu", "0",
                        "--from", "CS", "--to", "HX")
        self.assertEqual(code, 0)
        self.assertEqual(out["outputs"]["output"], {"lambda": 1.0, "mu": 0.0, "nu": 0.0})

    def test_positivity_refused(self):
        code, out = run("frames", "--M", "6", "--qT", "1", "--y", "0", "--lambda", "0", "--mu", "0", "--nu", "1.5",
                        "--from", "CS", "--to", "HX")
        self.assertEqual((code, out["status"]), (1, "refused"))
        # review I1: passes the necessary bounds of Eq. 22 but W < 0 somewhere on the sphere (W_min = -0.044)
        code, out = run("frames", "--M", "6", "--qT", "1", "--y", "0", "--lambda", "1", "--mu", "0.3", "--nu", "-2",
                        "--from", "CS", "--to", "HX")
        self.assertEqual((code, out["status"]), (1, "refused"))

    def test_positivity_matches_a_sphere_scan(self):
        rng = np.random.default_rng(7)
        th = np.linspace(0, math.pi, 181)
        ph = np.linspace(0, 2 * math.pi, 361)
        T, P = np.meshgrid(th, ph, indexing="ij")
        for _ in range(300):
            lam, mu, nu = rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-2, 2)
            w = (1 + lam * np.cos(T) ** 2 + mu * np.sin(2 * T) * np.cos(P)
                 + nu / 2 * np.sin(T) ** 2 * np.cos(2 * P))
            wmin = float(w.min())
            if abs(wmin) < 1e-3:
                continue  # too close to the boundary for a grid scan
            eq22 = abs(nu / 2) <= (1 + lam) / 2 and abs(mu) <= (1 - nu / 2) / 2  # Faccioli et al. 2010, Eq. 22
            self.assertEqual(not dy.positivity(lam, mu, nu), wmin > 0 and eq22, (lam, mu, nu, wmin))

    def test_rotation_sign_end_to_end(self):
        # review M5: refit the distribution on the boosted HX and CS axes; the script's HX -> CS result must match
        lam, mu, nu = 0.7, 0.1, 0.2
        for m, qt, y in ((10.0, 5.0, 0.5), (91.0, 30.0, -1.2)):
            zhx, zcs, yax = axes(m, qt, y)
            xhx, xcs = np.cross(yax, zhx), np.cross(yax, zcs)
            th = np.linspace(0.01, math.pi - 0.01, 50)
            ph = np.linspace(0, 2 * math.pi, 100, endpoint=False)
            T, P = np.meshgrid(th, ph, indexing="ij")
            r = (np.sin(T) * np.cos(P))[..., None] * xcs + (np.sin(T) * np.sin(P))[..., None] * yax \
                + np.cos(T)[..., None] * zcs  # directions given in CS coordinates
            ct, sx, sy = r @ zhx, r @ xhx, r @ yax
            st = np.sqrt(np.clip(1 - ct ** 2, 0, None))
            phh = np.arctan2(sy, sx)
            w = 1 + lam * ct ** 2 + mu * 2 * st * ct * np.cos(phh) + nu / 2 * st ** 2 * np.cos(2 * phh)
            basis = np.stack([np.ones_like(T), np.cos(T) ** 2, np.sin(2 * T) * np.cos(P),
                              np.sin(T) ** 2 * np.cos(2 * P)], axis=-1).reshape(-1, 4)
            c, *_ = np.linalg.lstsq(basis, w.reshape(-1), rcond=None)
            _, out = run("frames", "--M", str(m), "--qT", str(qt), "--y", str(y), "--lambda", str(lam), "--mu", str(mu),
                         "--nu", str(nu), "--from", "HX", "--to", "CS")
            o = out["outputs"]["output"]
            self.assertAlmostEqual(o["lambda"], c[1] / c[0], delta=1e-9)
            self.assertAlmostEqual(o["mu"], c[2] / c[0], delta=1e-9)
            self.assertAlmostEqual(o["nu"], 2 * c[3] / c[0], delta=1e-9)

    def test_coefficients_and_lam_tung(self):
        _, out = run("coefficients", "--A0", "0.2", "--A1", "0.05", "--A2", "0.2")
        o = out["outputs"]
        self.assertAlmostEqual(1 - o["lambda"] - 2 * o["nu"], 0.0, delta=1e-12)  # A0 = A2 <=> Lam-Tung
        _, back = run("coefficients", "--lambda", repr(o["lambda"]), "--mu", repr(o["mu"]), "--nu", repr(o["nu"]))
        for k, v in (("A0", 0.2), ("A1", 0.05), ("A2", 0.2)):
            self.assertAlmostEqual(back["outputs"][k], v, delta=1e-12)
        _, lt = run("lam-tung", "--lambda", "0.9", "--nu", "0.1", "--sigma-lambda", "0.03", "--sigma-nu", "0.02",
                    "--rho", "0.5")
        self.assertAlmostEqual(lt["outputs"]["one_minus_lambda_minus_2nu"], -0.1, delta=1e-12)
        self.assertAlmostEqual(lt["outputs"]["sigma"], math.sqrt(0.03 ** 2 + 4 * 0.02 ** 2 + 4 * 0.5 * 0.03 * 0.02),
                               delta=1e-12)


if __name__ == "__main__":
    unittest.main()
