"""S8: tail_extrapolation.py fits a control-region tail with model families, extrapolates it into the signal region
with the statistical interval and the envelope between models, validates on a pseudo signal region cut from the control
region, warns beyond the declared extrapolation distance and hands over to core/stats. Oracles: in toys with a known
exponential tail the envelope interval covers the true signal-region expectation at least at the declared rate; the
right model passes validation at about 1 - alpha and a wrong model is rejected with the power predicted from its Asimov
fit. The envelope is never turned into a Gaussian without a declared prescription. Inputs are SYNTHETIC."""
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "tail_extrapolation.py"
sys.path.insert(0, str(SCRIPT.parent))
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"
try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False

EDGES = [float(x) for x in range(100, 205, 5)]  # x from 100 to 200 in 5-unit bins
CR, VR, SR = [100.0, 160.0], [145.0, 160.0], [160.0, 200.0]


def exp_counts(norm, lam, rng):
    """Poisson counts of N lam exp(-lam (x - 100)) integrated per bin."""
    out = []
    for a, b in zip(EDGES[:-1], EDGES[1:]):
        mu = norm * (math.exp(-lam * (a - 100)) - math.exp(-lam * (b - 100)))
        out.append(poisson(rng, mu))
    return out


def pow_counts(norm, gamma, rng):
    out = []
    for a, b in zip(EDGES[:-1], EDGES[1:]):
        mu = norm * 100.0 / (gamma - 1) * ((a / 100) ** (1 - gamma) - (b / 100) ** (1 - gamma))
        out.append(poisson(rng, mu))
    return out


def poisson(rng, mu):
    if mu > 50:
        return max(0, int(round(rng.gauss(mu, math.sqrt(mu)))))
    k, p, L = 0, 1.0, math.exp(-mu)
    while True:
        p *= rng.random()
        if p < L:
            return k
        k += 1


def true_exp_sr(norm, lam):
    return norm * (math.exp(-lam * (SR[0] - 100)) - math.exp(-lam * (SR[1] - 100)))


def doc(counts, models=("exponential", "power-law"), **kw):
    d = {"variable": "SYNTHETIC mass", "edges": EDGES, "counts": counts, "control_region": CR, "signal_region": SR,
         "validation_region": VR, "models": list(models), "nominal": models[0], "max_extrapolation": 60.0,
         "validation_alpha": 0.05, "cl": 0.6827}
    d.update(kw)
    return d


def run(d, *args):
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "in.json"
        p.write_text(json.dumps(d), encoding="utf-8")
        cp = subprocess.run([sys.executable, "-B", str(SCRIPT), "--input", str(p), *map(str, args)],
                            capture_output=True, text=True, timeout=600)
    return cp.returncode, (json.loads(cp.stdout) if cp.stdout.strip().startswith("{") else None), cp.stderr


@unittest.skipUnless(HAVE, "NumPy and SciPy are needed")
class Basics(unittest.TestCase):
    def test_asimov_exponential_is_recovered_and_handed_over(self):
        norm, lam = 20000.0, 0.05
        counts = [norm * (math.exp(-lam * (a - 100)) - math.exp(-lam * (b - 100))) for a, b in zip(EDGES[:-1], EDGES[1:])]
        code, out, err = run(doc([round(c) for c in counts]))
        self.assertEqual(code, 0, err)
        nom = out["models"]["exponential"]
        self.assertLess(abs(nom["signal_region"]["prediction"] / true_exp_sr(norm, lam) - 1.0), 0.02)
        self.assertTrue(nom["validation"]["passed"])
        env = out["envelope"]
        self.assertLessEqual(env["low"], nom["signal_region"]["prediction"])
        self.assertGreaterEqual(env["high"], nom["signal_region"]["prediction"])
        self.assertIsNone(env["gaussian_sigma"])  # no prescription declared
        self.assertIn("not converted", env["note"])
        h = out["handover"]
        self.assertIn("poisson_diagnostics.py", " ".join(h["commands"]))
        self.assertIn("likelihood_limits.py", " ".join(h["commands"]))
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["status_label"], "unvalidated")

    def test_prescription_and_extrapolation_warning(self):
        rng = random.Random(3)
        counts = exp_counts(20000.0, 0.05, rng)
        code, out, _ = run(doc(counts, envelope_prescription="half-range"))
        self.assertEqual(code, 0)
        env = out["envelope"]
        self.assertAlmostEqual(env["gaussian_sigma"], (env["high"] - env["low"]) / 2, delta=1e-12)
        code, out, _ = run(doc(counts, max_extrapolation=20.0))
        self.assertTrue(any("extrapolation" in w for w in out["warnings"]))

    def test_failed_validation_of_the_nominal_model_is_failed(self):
        rng = random.Random(5)
        counts = pow_counts(20000.0, 6.0, rng)  # a power-law tail, fitted by an exponential
        code, out, _ = run(doc(counts, models=("exponential",), validation_alpha=0.05))
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "failed")
        self.assertFalse(out["models"]["exponential"]["validation"]["passed"])

    def test_bad_inputs(self):
        rng = random.Random(1)
        counts = exp_counts(2000.0, 0.05, rng)
        for bad in (doc(counts, models=["gaussian"]), doc(counts, nominal="power-law", models=["exponential"]),
                    doc(counts, validation_region=[150.0, 170.0]), doc(counts[:-1]),
                    {k: v for k, v in doc(counts).items() if k != "max_extrapolation"},
                    doc(counts, models=["plugin"], plugin="m.py")):
            with self.subTest(keys=sorted(bad)):
                code, out, _ = run(bad)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["status"], "rejected")

    def test_plugin_needs_the_opt_in(self):
        with tempfile.TemporaryDirectory() as t:
            plug = Path(t) / "flat.py"
            plug.write_text("START = [10.0]\n\ndef bin_integral(theta, lo, hi):\n    return theta[0] * (hi - lo)\n",
                            encoding="utf-8")
            rng = random.Random(2)
            d = doc(exp_counts(2000.0, 0.01, rng), models=["plugin"], plugin=str(plug))
            p = Path(t) / "in.json"
            p.write_text(json.dumps(d), encoding="utf-8")
            cp = subprocess.run([sys.executable, "-B", str(SCRIPT), "--input", str(p)], capture_output=True, text=True,
                                timeout=600)
            self.assertEqual(cp.returncode, 2)
            cp = subprocess.run([sys.executable, "-B", str(SCRIPT), "--input", str(p), "--allow-plugin"],
                                capture_output=True, text=True, timeout=600)
            self.assertIn(cp.returncode, (0, 1), cp.stdout + cp.stderr)
            self.assertIn("plugin", json.loads(cp.stdout)["models"])


@unittest.skipUnless(HAVE, "NumPy and SciPy are needed")
class Oracles(unittest.TestCase):
    TOYS = 400 if SLOW else 60

    def test_envelope_covers_at_least_the_declared_rate(self):
        import tail_extrapolation as te
        norm, lam = 4000.0, 0.04
        truth = true_exp_sr(norm, lam)
        rng = random.Random(11)
        cover = 0
        for _ in range(self.TOYS):
            res = te.analyse(doc(exp_counts(norm, lam, rng)))
            iv = res["envelope"]["interval"]  # None when no model passed validation: counted as not covering
            cover += iv is not None and iv[0] <= truth <= iv[1]
        rate = cover / self.TOYS
        floor = 0.6827 - 3 * math.sqrt(0.6827 * 0.3173 / self.TOYS)
        self.assertGreaterEqual(rate, floor, rate)

    def test_validation_size_and_power(self):
        import tail_extrapolation as te
        rng = random.Random(13)
        alpha = 0.05
        right = sum(not te.analyse(doc(exp_counts(4000.0, 0.04, rng), models=("exponential",)))["models"]
                    ["exponential"]["validation"]["passed"] for _ in range(self.TOYS)) / self.TOYS
        self.assertLess(right, alpha + 3 * math.sqrt(alpha * (1 - alpha) / self.TOYS) + 0.02)
        # wrong model: power-law truth, exponential fit; predicted power from the Asimov fit
        asimov = []
        for a, b in zip(EDGES[:-1], EDGES[1:]):
            asimov.append(4000.0 * 100.0 / 5.0 * ((a / 100) ** -5.0 - (b / 100) ** -5.0))
        expected = te.validation_power(doc(asimov, models=("exponential",)), "exponential")
        rejected = sum(not te.analyse(doc(pow_counts(4000.0, 6.0, rng), models=("exponential",)))["models"]
                       ["exponential"]["validation"]["passed"] for _ in range(self.TOYS)) / self.TOYS
        self.assertGreater(expected, 0.3)
        self.assertLess(abs(rejected - expected), 0.15 if not SLOW else 0.08, (rejected, expected))


class HelpWithoutNumpy(unittest.TestCase):
    def test_help(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "numpy.py").write_text("raise ImportError('hidden')\n", encoding="utf-8")
            env = dict(os.environ, PYTHONPATH=d)
            cp = subprocess.run([sys.executable, "-B", str(SCRIPT), "--help"], capture_output=True, text=True,
                                timeout=600, env=env)
        self.assertEqual(cp.returncode, 0)
        self.assertIn("validation_region", cp.stdout)


if __name__ == "__main__":
    unittest.main()
