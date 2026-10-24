"""drell_yan_lo.py (Th15): LO Drell-Yan cross section and kinematics against hand calculations and four-vectors.

Tolerances fixed before comparing: relative 1e-12 for identities and hand values; 1e-6 relative for the Simpson
integral over y (400 intervals) against its closed form.
"""
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-theory/scripts/drell_yan_lo.py"
spec = importlib.util.spec_from_file_location("drell_yan_lo", SCRIPT)
dy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dy)
ALPHA = 0.0072973525643
GEV2_PB = 0.38937937217185936e9
FL = ("d", "u", "s", "c", "b", "dbar", "ubar", "sbar", "cbar", "bbar")


def toy(x, scale=1.0):
    """x f for a toy beam: valence-like quarks, a sea."""
    return {"d": 0.3 * x ** 0.6 * (1 - x) ** 4 * scale, "u": 0.6 * x ** 0.6 * (1 - x) ** 3 * scale,
            "s": 0.05 * (1 - x) ** 7, "c": 0.02 * (1 - x) ** 8, "b": 0.0,
            "dbar": 0.12 * (1 - x) ** 7, "ubar": 0.10 * (1 - x) ** 7, "sbar": 0.05 * (1 - x) ** 7,
            "cbar": 0.02 * (1 - x) ** 8, "bbar": 0.0}


def run(*args, partons=None):
    with tempfile.TemporaryDirectory() as tmp:
        extra = []
        if partons is not None:
            p = Path(tmp) / "p.json"
            p.write_text(json.dumps(partons))
            extra = ["--partons", str(p)]
        r = subprocess.run([sys.executable, str(SCRIPT), *args, *extra], capture_output=True, text=True, timeout=60)
    return r.returncode, json.loads(r.stdout)


def close(a, b, tol=1e-12):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def point_partons(m, y, s, beam1=toy, beam2=toy):
    x1, x2 = m / math.sqrt(s) * math.exp(y), m / math.sqrt(s) * math.exp(-y)
    return {"representation": "xf", "x1": x1, "x2": x2, "beam1": beam1(x1), "beam2": beam2(x2)}


class DrellYanLO(unittest.TestCase):
    def test_hand_value(self):
        m, y, rs = 6.0, 0.3, 38.8
        p = point_partons(m, y, rs * rs)
        code, out = run("xsec", "--sqrt-s", str(rs), "--rapidity-frame", "cm", "--M", str(m), "--y", str(y),
                        "--alpha", str(ALPHA), "--alpha-label", "alpha(0)", "--bosons", "gamma", partons=p)
        self.assertEqual(code, 0, out)
        o = out["outputs"]
        x1, x2 = p["x1"], p["x2"]
        b1, b2 = p["beam1"], p["beam2"]
        e2 = {"u": 4 / 9, "d": 1 / 9, "s": 1 / 9, "c": 4 / 9, "b": 1 / 9}
        lum = sum(e2[q] * (b1[q] / x1 * b2[q + "bar"] / x2 + b1[q + "bar"] / x1 * b2[q] / x2) for q in e2)
        hand = 8 * math.pi * ALPHA ** 2 / (9 * m * rs * rs) * lum
        self.assertTrue(close(o["d2sigma_dM_dy_GeV3"], hand))
        self.assertTrue(close(o["d2sigma_dM_dy_pb_per_GeV"], hand * GEV2_PB))
        self.assertTrue(close(o["x1"] * o["x2"], o["tau"]))
        self.assertTrue(close(o["tau"], m * m / (rs * rs)))

    def test_normalization_against_pdg_numeric_constant(self):
        # review M5: independent of the code's 8 pi alpha^2 / 9: PDG Eq. (51.3) sigma(e+e- -> mu mu) = 86.8 nb / s;
        # q qbar -> l+ l- carries e_q^2 / N_c; dsigma/dM dy = 2M sigma_hat(M^2) / s * f1 f2 (alpha(0) assumed in 86.8)
        m, y, rs = 6.0, 0.3, 38.8
        p = point_partons(m, y, rs * rs)
        _, out = run("xsec", "--sqrt-s", str(rs), "--rapidity-frame", "cm", "--M", str(m), "--y", str(y),
                     "--alpha", str(ALPHA), "--alpha-label", "alpha(0)", "--bosons", "gamma", partons=p)
        x1, x2, b1, b2 = p["x1"], p["x2"], p["beam1"], p["beam2"]
        e2 = {"u": 4 / 9, "d": 1 / 9, "s": 1 / 9, "c": 4 / 9, "b": 1 / 9}
        ff = sum(e2[q] * (b1[q] * b2[q + "bar"] + b1[q + "bar"] * b2[q]) for q in e2) / (x1 * x2)
        sigma_hat_nb = 86.8 / (3 * m * m)
        hand_pb = 2 * m * sigma_hat_nb * 1e3 / (rs * rs) * ff
        self.assertAlmostEqual(out["outputs"]["d2sigma_dM_dy_pb_per_GeV"] / hand_pb, 1.0, delta=2e-3)  # 86.8 is rounded

    def test_jacobians_and_xf_against_four_vectors(self):
        s = 400.0 ** 2
        rs = math.sqrt(s)
        for m, y in ((10.0, 0.0), (8.0, 1.1), (30.0, -0.7)):
            k = dy.kinematics(m, y, s)
            # massless hadrons along +-z in the c.m. frame; the pair is x1 P1 + x2 P2
            e = (k["x1"] + k["x2"]) * rs / 2
            pz = (k["x1"] - k["x2"]) * rs / 2
            self.assertTrue(close(e * e - pz * pz, m * m))
            self.assertTrue(close(0.5 * math.log((e + pz) / (e - pz)), y))
            self.assertTrue(close(k["xF"]["2pL/sqrts"], 2 * pz / rs))
            self.assertTrue(close(k["xF"]["x1-x2"], k["x1"] - k["x2"]))
            plmax = (s - m * m) / (2 * rs)
            self.assertTrue(close(k["xF"]["pL/pLmax"], pz / plmax))
            h = 1e-6  # d x_F / dy by central difference
            for d in dy.XF_DEFS:
                num = (dy.kinematics(m, y + h, s)["xF"][d] - dy.kinematics(m, y - h, s)["xF"][d]) / (2 * h)
                self.assertTrue(close(k["dxF_dy"][d], num, 1e-8), d)

    def test_convert_round_trips(self):
        base = ["convert", "--sqrt-s", "38.8", "--rapidity-frame", "cm"]
        _, a = run(*base, "--M", "5", "--y", "0.4")
        for d in dy.XF_DEFS:
            _, b = run(*base, "--M", "5", "--xF", repr(a["outputs"]["xF"][d]), "--xF-definition", d)
            self.assertTrue(close(b["outputs"]["y_cm"], 0.4, 1e-10), d)
        _, c = run(*base, "--x1", repr(a["outputs"]["x1"]), "--x2", repr(a["outputs"]["x2"]))
        self.assertTrue(close(c["outputs"]["M"], 5.0, 1e-10))
        _, t = run(*base, "--tau", repr(a["outputs"]["tau"]), "--y", "0.4")
        self.assertTrue(close(t["outputs"]["x1"], a["outputs"]["x1"], 1e-10))

    def test_lab_rapidity_shift_fixed_target(self):
        e1, m1 = 120.0, 0.938
        base = ["convert", "--E1", str(e1), "--m1", str(m1), "--E2", str(m1), "--m2", str(m1), "--rapidity-frame", "lab"]
        p1 = math.sqrt(e1 * e1 - m1 * m1)
        shift = 0.5 * math.log((e1 + m1 + p1) / (e1 + m1 - p1))
        s = 2 * m1 * m1 + 2 * e1 * m1
        _, out = run(*base, "--M", "5", "--y", repr(shift))
        o = out["outputs"]
        self.assertTrue(close(o["y_shift"], shift))
        self.assertTrue(close(o["y_cm"], 0.0, 1e-10))
        self.assertTrue(close(o["s"], s))
        self.assertTrue(close(o["x1"], o["x2"], 1e-10))

    def test_identical_beams_symmetric_in_y(self):
        rs = 38.8
        vals = []
        for y in (0.35, -0.35):
            _, out = run("xsec", "--sqrt-s", str(rs), "--rapidity-frame", "cm", "--M", "6", "--y", str(y),
                         "--alpha", str(ALPHA), "--alpha-label", "a", "--bosons", "gamma",
                         partons=point_partons(6.0, y, rs * rs))
            vals.append(out["outputs"]["d2sigma_dM_dy_GeV3"])
        self.assertTrue(close(vals[0], vals[1]))

    def test_lo_scaling(self):
        tau, y = 0.02, 0.2
        vals = []
        for rs in (20.0, 60.0):
            m = math.sqrt(tau) * rs
            _, out = run("xsec", "--sqrt-s", str(rs), "--rapidity-frame", "cm", "--M", repr(m), "--y", str(y),
                         "--alpha", str(ALPHA), "--alpha-label", "a", "--bosons", "gamma",
                         partons=point_partons(m, y, rs * rs))
            vals.append(out["outputs"]["M3_dsigma_dM_dy_GeV0"])
        self.assertTrue(close(vals[0], vals[1], 1e-10))

    def test_y_integral_closed_form(self):
        # toy number densities f(x) = x^-a for every quark of beam 1 and antiquark of beam 2, only u-type, e^2 = 4/9:
        # sum = (4/9) f1(x1) f2(x2) = (4/9) tau^-a: int dy over |y| < -ln(sqrt(tau)) = (4/9) tau^-a (-ln tau)
        a_pow, s, m = 0.4, 1000.0, 5.0
        tau = m * m / s

        def b1(x):
            return {f: (x ** (1 - a_pow) if f == "u" else 0.0) for f in FL}

        def b2(x):
            return {f: (x ** (1 - a_pow) if f == "ubar" else 0.0) for f in FL}
        n, ymax = 400, -0.5 * math.log(tau)
        h = 2 * ymax / n
        tot = 0.0
        for i in range(n + 1):
            y = -ymax + i * h
            y = max(min(y, ymax * (1 - 1e-15)), -ymax * (1 - 1e-15))
            k = dy.kinematics(m, y, s)
            lum = (4 / 9) * (b1(k["x1"])["u"] / k["x1"]) * (b2(k["x2"])["ubar"] / k["x2"])
            w = 1 if i in (0, n) else (4 if i % 2 else 2)
            tot += w * 8 * math.pi * ALPHA ** 2 / (9 * m * s) * lum
        tot *= h / 3
        closed = 8 * math.pi * ALPHA ** 2 / (9 * m * s) * (4 / 9) * tau ** -a_pow * (-math.log(tau))
        self.assertTrue(close(tot, closed, 1e-6))

    def test_pd_over_pp_follows_dbar_over_ubar(self):
        # LO, large x_1: sigma(pd) / (2 sigma(pp)) grows with dbar/ubar of the target (per-nucleon deuteron = (p+n)/2)
        rs, m, y = 15.0, 5.0, 0.8
        ratios = []
        for r in (0.8, 1.0, 1.4):
            def target_p(x, r=r):
                v = toy(x)
                v["dbar"] = r * v["ubar"]
                return v

            def target_d(x, r=r):
                p = target_p(x)
                n = dict(p, u=p["d"], d=p["u"], ubar=p["dbar"], dbar=p["ubar"])
                return {f: 0.5 * (p[f] + n[f]) for f in FL}
            outs = []
            for tgt in (target_p, target_d):
                _, out = run("xsec", "--sqrt-s", str(rs), "--rapidity-frame", "cm", "--M", str(m), "--y", str(y),
                             "--alpha", str(ALPHA), "--alpha-label", "a", "--bosons", "gamma",
                             partons=point_partons(m, y, rs * rs, toy, tgt))
                outs.append(out["outputs"]["d2sigma_dM_dy_GeV3"])
            ratios.append(outs[1] / outs[0])  # per-nucleon pd / pp = sigma(pd) / (2 sigma(pp))
        self.assertLess(ratios[0], ratios[1])
        self.assertLess(ratios[1], ratios[2])

    def test_refusals_and_rejections(self):
        rs, m, y = 38.8, 6.0, 0.3
        p = point_partons(m, y, rs * rs)
        base = ["xsec", "--sqrt-s", str(rs), "--rapidity-frame", "cm", "--M", str(m), "--y", str(y),
                "--alpha", str(ALPHA), "--alpha-label", "a"]
        code, out = run(*base, "--bosons", "gammaZ", partons=p)
        self.assertEqual((code, out["status"]), (1, "refused"))
        code, out = run(*base, "--bosons", "gamma", "--resonance-window", "5.5:6.5", partons=p)
        self.assertEqual((code, out["status"]), (1, "refused"))
        code, _ = run(*base, "--bosons", "gamma", "--resonance-window", "5.5:6.5", "--allow-in-window", partons=p)
        self.assertEqual(code, 0)
        code, out = run(*base, "--bosons", "gamma", partons=point_partons(m, 0.31, rs * rs))
        self.assertEqual((code, out["status"]), (2, "rejected"))  # parton file evaluated at another point
        code, _ = run("convert", "--sqrt-s", "10", "--rapidity-frame", "cm", "--M", "11", "--y", "0")
        self.assertEqual(code, 2)  # M^2 >= s
        code, _ = run("convert", "--sqrt-s", "10", "--rapidity-frame", "cm", "--M", "5", "--xF", "0.2")
        self.assertEqual(code, 2)  # no x_F definition
        code, _ = run("convert", "--sqrt-s", "10", "--rapidity-frame", "cm", "--M", "5", "--y", "2")
        self.assertEqual(code, 2)  # x_1 > 1
        code, _ = run("convert", "--sqrt-s", "10", "--M", "5", "--y", "0")
        self.assertEqual(code, 2)  # undeclared rapidity frame
        code, _ = run("convert", "--sqrt-s", "38.8", "--rapidity-frame", "lab", "--M", "5", "--y", "0")
        self.assertEqual(code, 2)  # lab frame without beam four-momenta
        # review M4
        code, _ = run("convert", "--sqrt-s", "38.8", "--rapidity-frame", "cm", "--M", "5", "--y", "1", "--x1", "0.2",
                      "--x2", "0.1")
        self.assertEqual(code, 2)  # two point specifications
        code, out = run("convert", "--E1", "100", "--m1", "0", "--E2", "0", "--m2", "0", "--rapidity-frame", "lab",
                        "--M", "5", "--y", "0")
        self.assertEqual((code, out["status"]), (2, "rejected"))  # no c.m. frame
        code, _ = run(*base, "--bosons", "gamma", "--resonance-window", "6.5:5.5", partons=p)
        self.assertEqual(code, 2)  # LO > HI


if __name__ == "__main__":
    unittest.main()
