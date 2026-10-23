"""tmd_gaussian.py (Th18): Gaussian-ansatz SIDIS and Drell-Yan shapes and the Sivers sign change.

Tolerances fixed before comparing: 1e-12 relative for identities; 1e-6 relative for the numerical d^2 P_hT integral.
"""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-theory/scripts/tmd_gaussian.py"
FL = ("d", "u", "s", "c", "b", "dbar", "ubar", "sbar", "cbar", "bbar")
F1 = {"d": 1.1, "u": 2.0, "s": 0.3, "c": 0.1, "b": 0.0, "dbar": 0.4, "ubar": 0.35, "sbar": 0.3, "cbar": 0.1, "bbar": 0.0}
D1 = {"d": 0.2, "u": 0.6, "s": 0.15, "c": 0.0, "b": 0.0, "dbar": 0.6, "ubar": 0.2, "sbar": 0.15, "cbar": 0.0,
      "bbar": 0.0}


def run(*args, partons=None):
    with tempfile.TemporaryDirectory() as tmp:
        extra = []
        if partons is not None:
            p = Path(tmp) / "p.json"
            p.write_text(json.dumps(partons))
            extra = ["--partons", str(p)]
        r = subprocess.run([sys.executable, str(SCRIPT), *args, *extra], capture_output=True, text=True, timeout=60)
    return r.returncode, json.loads(r.stdout)


class TMDGaussian(unittest.TestCase):
    def test_sidis_integral_gives_collinear(self):
        x, z, k2, p2 = 0.1, 0.4, 0.57, 0.12
        n, pmax = 4000, 6.0
        pts = [pmax * (i + 0.5) / n for i in range(n)]
        code, out = run("sidis", "--x", str(x), "--z", str(z), "--kperp2", str(k2), "--pperp2", str(p2),
                        "--PhT", *map(repr, pts), partons={"f1": F1, "D1": D1})
        self.assertEqual(code, 0, out)
        o = out["outputs"]
        hand = x * sum(({"u": 4, "c": 4}.get(f.replace("bar", ""), 1) / 9) * F1[f] * D1[f] for f in FL)
        self.assertAlmostEqual(o["collinear_F_UU_T"], hand, delta=1e-12 * hand)
        self.assertAlmostEqual(o["PT2_width_GeV2"], p2 + z * z * k2, delta=1e-14)
        integral = sum(2 * math.pi * r["PhT_GeV"] * r["F_UU_T"] for r in o["rows"]) * (pmax / n)
        self.assertAlmostEqual(integral / hand, 1.0, delta=1e-6)

    def test_against_direct_eq41_convolution(self):
        # independent: Bacchetta et al. Eq. 4.1 with D(z, k_T^2) normalized as D_1(z) = z^2 int d^2k_T D(z, k_T^2)
        # (their Eq. 3.41), k_T the quark momentum relative to the hadron; Gaussian widths <p_T^2> (distribution) and
        # <k_T^2> = <p_perp^2>/z^2; brute-force 2D quadrature of the delta-function-reduced integral at one P_hT
        import numpy as np
        x, z, k2, p2, pht = 0.1, 0.4, 0.57, 0.12, 0.45
        kt2w = p2 / z ** 2
        coll = x * sum(({"u": 4, "c": 4}.get(f.replace("bar", ""), 1) / 9) * F1[f] * D1[f] for f in FL)
        g = np.linspace(-6, 6, 1201)
        h = g[1] - g[0]
        px, py = np.meshgrid(g, g, indexing="ij")
        # delta(p_T - k_T - P/z): k_T = p_T - P/z
        kx, ky = px - pht / z, py
        fp = np.exp(-(px ** 2 + py ** 2) / k2) / (np.pi * k2)
        dk = np.exp(-(kx ** 2 + ky ** 2) / kt2w) / (np.pi * kt2w) / z ** 2
        direct = coll * float((fp * dk).sum() * h * h)
        _, out = run("sidis", "--x", str(x), "--z", str(z), "--kperp2", str(k2), "--pperp2", str(p2), "--PhT", str(pht),
                     partons={"f1": F1, "D1": D1})
        self.assertAlmostEqual(out["outputs"]["rows"][0]["F_UU_T"] / direct, 1.0, delta=1e-6)

    def test_dy_shape_normalized_and_widths_add(self):
        n, qmax = 4000, 8.0
        qs = [qmax * (i + 0.5) / n for i in range(n)]
        _, out = run("dy", "--k1perp2", "0.5", "--k2perp2", "0.7", "--qT", *map(repr, qs))
        o = out["outputs"]
        self.assertAlmostEqual(o["qT2_width_GeV2"], 1.2, delta=1e-14)
        integral = sum(2 * math.pi * r["qT_GeV"] * r["shape_per_GeV2"] for r in o["rows"]) * (qmax / n)
        self.assertAlmostEqual(integral, 1.0, delta=1e-6)
        mean_q2 = sum(2 * math.pi * r["qT_GeV"] ** 3 * r["shape_per_GeV2"] for r in o["rows"]) * (qmax / n)
        self.assertAlmostEqual(mean_q2, 1.2, delta=1e-5)  # <q_T^2> of the 2D Gaussian equals its width parameter

    def test_sivers_sign_change(self):
        _, out = run("sivers", "--sidis-value", "0.03", "--notation", "f1T_perp")
        self.assertEqual(out["outputs"]["drell_yan_value"], -0.03)
        self.assertIn("Eq. 14", out["outputs"]["rule"])

    def test_rejections(self):
        code, _ = run("sidis", "--x", "0.1", "--z", "1.2", "--kperp2", "0.5", "--pperp2", "0.1", "--PhT", "0.5",
                      partons={"f1": F1, "D1": D1})
        self.assertEqual(code, 2)
        code, _ = run("sidis", "--x", "0.1", "--z", "0.4", "--kperp2", "-0.5", "--pperp2", "0.1", "--PhT", "0.5",
                      partons={"f1": F1, "D1": D1})
        self.assertEqual(code, 2)
        code, _ = run("sidis", "--x", "0.1", "--z", "0.4", "--kperp2", "0.5", "--pperp2", "0.1", "--PhT", "-0.5",
                      partons={"f1": F1, "D1": D1})
        self.assertEqual(code, 2)
        code, _ = run("sidis", "--x", "0.1", "--z", "0.4", "--kperp2", "0.5", "--pperp2", "0.1", "--PhT", "0.5",
                      partons={"f1": {k: v for k, v in F1.items() if k != "u"}, "D1": D1})
        self.assertEqual(code, 2)
        code, _ = run("sivers", "--sidis-value", "0.03")
        self.assertEqual(code, 2)  # notation required


if __name__ == "__main__":
    unittest.main()
