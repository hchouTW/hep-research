"""S4: covariance_fit.py per-dataset scale nuisance, Phi_obs(x) = Phi_model(x / (1 + s)) / (1 + s) with a Gaussian
constraint on s. Oracles: an injected scale offset of one dataset is recovered in a joint fit with a reference
dataset; without a declaration the joint mode equals separate plain fits, and the plain fit path is unchanged.
Inputs are SYNTHETIC (a smoothly broken power law)."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "covariance_fit.py"

try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    HAVE = True
except ImportError:  # pragma: no cover
    HAVE = False

THETA = [math.log(100.0), 2.7, 2.3, math.log(20.0)]  # ln A, gamma1, gamma2, ln x_b
SMOOTH = 0.1


def bpl(x, theta=THETA, s=SMOOTH):
    ln_a, g1, g2, lxb = theta
    u = math.log(x) - lxb
    h = s * math.log((1 + math.exp(u / s)) / 2)
    return math.exp(ln_a - g1 * (u - h) - g2 * h)


def dataset(name, xs, shift=0.0, rel=0.01, scale=None):
    y = [bpl(x / (1 + shift)) / (1 + shift) for x in xs]
    d = {"name": name, "x": xs, "y": y, "cov": [[(rel * y[i]) ** 2 if i == j else 0.0 for j in range(len(xs))]
                                               for i in range(len(xs))]}
    if scale:
        d["scale_nuisance"] = scale
    return d


def run(doc):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "in.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        cp = subprocess.run([sys.executable, "-B", str(SCRIPT), "fit", "--input", str(p)], capture_output=True,
                            text=True, timeout=600)
    return cp.returncode, json.loads(cp.stdout)


XS = [2.0 * 1.35 ** i for i in range(16)]  # 2 .. ~180, across the break
BASE = {"model": "smoothly-broken-power-law", "model_options": {"smoothness": SMOOTH},
        "start": [math.log(90.0), 2.6, 2.2, math.log(18.0)]}


@unittest.skipUnless(HAVE, "NumPy and SciPy needed")
class ScaleNuisance(unittest.TestCase):
    def test_injected_scale_is_recovered(self):
        doc = dict(BASE, datasets=[dataset("reference", XS),
                                   dataset("shifted", XS[1:-1], shift=0.03, scale={"sigma": 0.05, "kind": "energy"})])
        code, out = run(doc)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["status"], "ok")
        (sn,) = out["scale_nuisances"]
        self.assertEqual((sn["dataset"], sn["kind"], sn["sigma"]), ("shifted", "energy", 0.05))
        self.assertAlmostEqual(sn["s"], 0.03, delta=3e-4)
        self.assertGreater(sn["error"], 0)
        for a, b in zip(out["theta"], THETA):
            self.assertAlmostEqual(a, b, delta=2e-3)
        # noiseless data: the data chi2 vanishes; the total adds the constraint (s / sigma)^2 = 0.36
        self.assertLess(out["chi2"] - out["constraint_chi2"], 1e-3)
        self.assertAlmostEqual(out["constraint_chi2"], (0.03 / 0.05) ** 2, delta=0.01)

    def test_ignoring_the_offset_fits_badly(self):
        doc = dict(BASE, datasets=[dataset("reference", XS), dataset("shifted", XS[1:-1], shift=0.03)])
        code, out = run(doc)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["scale_nuisances"], [])
        self.assertGreater(out["chi2"], 50.0)

    def test_without_declaration_the_joint_mode_equals_the_plain_fit(self):
        d = dataset("only", XS)
        code_j, joint = run(dict(BASE, datasets=[d]))
        code_p, plain = run(dict(BASE, y=d["y"], cov=d["cov"], x=d["x"]))
        self.assertEqual((code_j, code_p), (0, 0), (joint, plain))
        for a, b in zip(joint["theta"], plain["theta"]):
            self.assertAlmostEqual(a, b, delta=1e-6)
        self.assertAlmostEqual(joint["chi2"], plain["chi2"], delta=1e-8)
        self.assertNotIn("scale_nuisances", plain)

    def test_bad_declarations_are_refused(self):
        for scale in ({"sigma": 0.05}, {"sigma": -1.0, "kind": "energy"}, {"kind": "energy"},
                      {"sigma": 0.05, "kind": "energy", "extra": 1}):
            with self.subTest(scale=scale):
                code, out = run(dict(BASE, datasets=[dataset("a", XS), dataset("b", XS, scale=scale)]))
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")
        code, out = run(dict(BASE, datasets=[dataset("a", XS)], multiplicative={"relative_cov": [[0.01]], "mode": "data"}))
        self.assertEqual(code, 2, out)


if __name__ == "__main__":
    unittest.main()
