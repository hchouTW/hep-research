"""S07: skills/hep-statistics/scripts/bayes_diagnostics.py. Convergence diagnostics on seeded synthetic chains
(configurations fixed before running), prior-sensitivity reweighting, and the demonstration
Metropolis sampler against the exact flat-prior bound of counting_reference.py (n = 0, b = 0: -ln 0.05)."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "bayes_diagnostics.py"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-analysis" / "scripts"))

try:
    import numpy as np
    import bayes_diagnostics as bd
    HAVE_NP = True
except ImportError:
    HAVE_NP = False

from contracts.validate import validate_artifact  # noqa: E402


def run(*args):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


def ar1(rng, rho, chains, n):
    e = rng.normal(size=(chains, n))
    z = np.empty((chains, n))
    z[:, 0] = e[:, 0] / math.sqrt(1 - rho ** 2)       # stationary start
    for t in range(1, n):
        z[:, t] = rho * z[:, t - 1] + e[:, t]
    return z


@unittest.skipUnless(HAVE_NP, "numpy not installed: Bayesian diagnostics unverified")
class Diagnostics(unittest.TestCase):
    def test_independent_chains_converge(self):
        x = np.random.default_rng(1).normal(size=(4, 1000))
        r = bd.diagnose({"x": x}, (0.5,), 1.01, 100)
        self.assertLess(r["parameters"]["x"]["rhat"], 1.01)
        self.assertEqual(r["status"], "converged")

    def test_offset_chains_flagged(self):
        x = np.random.default_rng(2).normal(size=(4, 1000))
        x[2:] += 1.0                                    # two chains at 0, two at 1 sigma
        r = bd.diagnose({"x": x}, (0.5,), 1.01, 100)
        self.assertGreater(r["parameters"]["x"]["rhat"], 1.1)
        self.assertEqual(r["status"], "not-converged")

    def test_ar1_bulk_ess(self):
        rho, chains, n = 0.9, 4, 5000
        z = ar1(np.random.default_rng(3), rho, chains, n)
        ess = bd.diagnose_param(z)["ess_bulk"]
        target = chains * n * (1 - rho) / (1 + rho)
        self.assertLess(abs(ess / target - 1), 0.15, (ess, target))

    def test_too_few_chains_or_draws_incomplete(self):
        rng = np.random.default_rng(4)
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "c.json"
            f.write_text(json.dumps({"x": rng.normal(size=(1, 1000)).tolist()}))
            code, out = run("diagnose", "--input", str(f))
            self.assertEqual((code, out["status"]), (3, "incomplete"))
            np.save(Path(tmp) / "c.npy", rng.normal(size=(4, 20)))
            code, out = run("diagnose", "--input", str(Path(tmp) / "c.npy"))
            self.assertEqual((code, out["status"]), (3, "incomplete"))

    def test_quantile_mcse_reported(self):
        x = np.random.default_rng(5).normal(size=(4, 2000))
        q = bd.diagnose_param(x, (0.05, 0.95))["quantiles"]
        for p in ("0.05", "0.95"):
            self.assertGreater(q[p]["mcse"], 0)
            self.assertLess(q[p]["mcse"], 0.1)


@unittest.skipUnless(HAVE_NP, "numpy not installed: prior reweighting unverified")
class Reweighting(unittest.TestCase):
    def test_reweight_to_a_close_prior(self):
        # posterior of a normal mean with a wide normal prior; reweight to a slightly narrower prior: the exact
        # conjugate answer is known
        rng = np.random.default_rng(6)
        draws = rng.normal(1.0, 0.2, 20000)            # posterior under N(0, 100^2) is ~ N(1, 0.2^2)
        doc = {"param": "mu", "draws": draws.tolist(), "quantiles": [0.5],
               "old_prior": {"form": "normal", "mean": 0, "sd": 100}, "new_prior": {"form": "normal", "mean": 0, "sd": 1}}
        res, code = bd.reweight(doc)
        self.assertEqual(code, 0)
        exact = (1 / 0.2 ** 2) / (1 / 0.2 ** 2 + 1)     # N(1, 0.2^2) likelihood with a N(0, 1) prior: 25/26
        self.assertAlmostEqual(res["quantiles"]["0.5"]["new"], exact, delta=0.01)
        self.assertGreater(res["weight_ess_fraction"], 0.9)

    def test_low_weight_ess_requires_rerun(self):
        draws = np.random.default_rng(7).normal(1.0, 0.2, 5000)
        doc = {"param": "mu", "draws": draws.tolist(),
               "old_prior": {"form": "normal", "mean": 0, "sd": 100}, "new_prior": {"form": "normal", "mean": 2.0, "sd": 0.02}}
        res, code = bd.reweight(doc)
        self.assertEqual((code, res["status"]), (1, "rerun-required"))
        self.assertIn("rerun", res["reason"])

    def test_wider_support_requires_rerun(self):
        draws = np.random.default_rng(8).uniform(0, 5, 2000)
        doc = {"param": "s", "draws": draws.tolist(),
               "old_prior": {"form": "uniform", "low": 0, "high": 5}, "new_prior": {"form": "uniform", "low": 0, "high": 10}}
        res, code = bd.reweight(doc)
        self.assertEqual(code, 1)
        self.assertIn("support", res["reason"])


@unittest.skipUnless(HAVE_NP, "numpy not installed: demonstration sampler unverified")
class DemoSampler(unittest.TestCase):
    def test_upper_bound_matches_counting_reference(self):
        from counting_reference import bayesian_upper  # skills/hep-analysis/scripts
        exact = bayesian_upper(0, 0.0, 0.95)
        self.assertAlmostEqual(exact, -math.log(0.05), places=5)
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "result.json"
            code, out = run("demo-sampler", "--n", "0", "--b", "0", "--chains", "4", "--draws", "20000",
                            "--seed", "11", "--artifact", str(art))
            self.assertEqual(code, 0, out)
            ub = out["upper_bound"]
            self.assertLess(abs(ub["value"] - exact), 3 * ub["mcse"], (ub, exact))
            self.assertIn("DEMONSTRATION", out["label"])
            doc = json.loads(art.read_text())
            rep = validate_artifact(doc)
            self.assertTrue(rep.ok, [f.as_dict() for f in rep.findings])
            self.assertEqual(doc["extension"]["paradigm"], "bayesian")
            # the same artifact claiming convergence with a large R-hat is refused (S11)
            doc["extension"]["convergence"]["rhat"] = {"s": 1.2}
            self.assertIn("stats.convergence_mismatch", {f.code for f in validate_artifact(doc).errors})


if __name__ == "__main__":
    unittest.main()
