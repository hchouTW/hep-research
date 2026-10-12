"""hep-statistics audit T25: Bayesian inference checks (bayes_calibration.py and the Bayesian contract rules).
SYNTHETIC. Posterior quantiles from chains agree with the conjugate Poisson-Gamma and normal-normal posteriors within
4 MCSE; a random-walk sampler on log(lambda) that leaves out the Jacobian fails the check, and the same sampler with
the Jacobian passes; unconverged chains are not-run, not pass. SBC passes for the exact posterior, fails for one too
narrow or too wide, keeps its false-alarm rate near alpha = 0.01, and reports its power (at least 0.9 against a width
factor 0.7) as fixed before the run. Contract: NUTS metadata, divergences and E-BFMI under fit_status converged,
improper priors, SBC reported as coverage."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))

import bayes_calibration as bc  # noqa: E402

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

PG = {"kind": "poisson-gamma", "a": 2.0, "b": 0.5, "n": 7, "T": 3.0}


def metropolis_log_lambda(jacobian, chains=4, draws=4000, seed=3):
    """Random-walk Metropolis on u = log(lambda) for the Poisson-Gamma posterior; the density of u carries the
    Jacobian lambda = exp(u) only when jacobian is True (the bug this check must catch)."""
    rng = np.random.default_rng(seed)
    a, b, n, t = PG["a"], PG["b"], PG["n"], PG["T"]

    def logp(u):
        lam = math.exp(u)
        return (a - 1 + n) * u - (b + t) * lam + (u if jacobian else 0.0)
    out = np.empty((chains, draws))
    for c in range(chains):
        u = math.log((a + n) / (b + t)) + rng.normal(0, 0.5)
        lp = logp(u)
        for i in range(draws + 1000):
            v = u + rng.normal(0, 0.6)
            lv = logp(v)
            if math.log(rng.random()) < lv - lp:
                u, lp = v, lv
            if i >= 1000:
                out[c, i - 1000] = math.exp(u)
    return out


class PosteriorQuantiles(unittest.TestCase):
    def test_exact_draws_pass_both_conjugate_models(self):
        rng = np.random.default_rng(1)
        post = bc.posterior(PG)
        self.assertEqual(bc.check_quantiles(post.rvs(size=(4, 2000), random_state=rng), PG)["status"], "pass")
        nn = {"kind": "normal-normal", "m0": 0.0, "s0": 2.0, "xbar": 1.3, "sigma": 1.0, "N": 10}
        self.assertEqual(bc.check_quantiles(bc.posterior(nn).rvs(size=(4, 2000), random_state=rng), nn)["status"], "pass")

    def test_missing_jacobian_is_detected(self):
        self.assertEqual(bc.check_quantiles(metropolis_log_lambda(True), PG)["status"], "pass")
        bad = bc.check_quantiles(metropolis_log_lambda(False), PG)
        self.assertEqual(bad["status"], "fail")
        self.assertTrue(any(r["status"] == "fail" for r in bad["quantiles"].values()))

    def test_unconverged_chains_are_not_evidence(self):
        rng = np.random.default_rng(2)
        x = bc.posterior(PG).rvs(size=(4, 2000), random_state=rng)
        x[3] += 2.0
        self.assertEqual(bc.check_quantiles(x, PG)["status"], "not-run")

    def test_improper_prior_refused(self):
        with self.assertRaises(ValueError):
            bc.posterior(dict(PG, a=0.0))


class SimulationBasedCalibration(unittest.TestCase):
    def test_exact_posterior_passes_with_stated_power(self):
        r = bc.sbc(seed=1, power_runs=50)
        self.assertEqual(r["status"], "pass")
        self.assertGreaterEqual(r["power_against_width_0.7"], 0.9)
        self.assertIn("not frequentist coverage", r["note"])

    def test_miscalibrated_posteriors_fail(self):
        for wf in (0.7, 1.3):
            self.assertEqual(bc.sbc(seed=2, width_factor=wf, power_runs=0)["status"], "fail", wf)

    def test_false_alarm_rate(self):
        rejections = sum(bc.sbc(seed=100 + k, power_runs=0, reps=400, draws=99, bins=20)["p_value"] < 0.01 for k in range(60))
        self.assertLessEqual(rejections, 4)          # expected 0.6 at alpha = 0.01; P(>= 5) is below 0.1%

    def test_without_power_it_is_inconclusive(self):
        self.assertEqual(bc.sbc(seed=1, power_runs=0)["status"], "inconclusive")


class BayesianContract(unittest.TestCase):
    def result(self, **ext):
        d = json.loads((ROOT / "contracts/fixtures/artifacts/valid/statres_bayesian.json").read_text())
        d["contract_version"] = d["versions"]["contracts"] = CONTRACTS_VERSION
        d["extension"].update(ext)
        return validate_artifact(d)

    def codes(self, rep, sev):
        return {f.code for f in rep.findings if f.severity == sev}

    def test_rules(self):
        meta = {"name": "NUTS", "warmup": 1000, "chains": 4, "draws": 1000, "divergences": 0, "e_bfmi_min": 0.8,
                "max_treedepth_hits": 0}
        self.assertTrue(self.result(sampler=meta).ok)
        self.assertIn("stats.sampler_metadata_missing", self.codes(self.result(sampler={"name": "NUTS"}), "unresolved"))
        self.assertIn("stats.divergences_unreported", self.codes(self.result(sampler=dict(meta, divergences=3)), "error"))
        self.assertIn("stats.low_e_bfmi", self.codes(self.result(sampler=dict(meta, e_bfmi_min=0.2)), "error"))
        ok = self.result(sampler=dict(meta, divergences=3), fit_status="converged-with-warnings")
        self.assertNotIn("stats.divergences_unreported", self.codes(ok, "error"))
        self.assertIn("stats.improper_prior", self.codes(self.result(priors=[{"parameter": "mu", "form": "flat"}]), "unresolved"))
        self.assertNotIn("stats.improper_prior", self.codes(
            self.result(priors=[{"parameter": "mu", "form": "flat", "propriety": "Poisson likelihood with n >= 0 events"}]),
            "unresolved"))
        self.assertIn("stats.paradigm_mislabeled", self.codes(self.result(coverage={"check": "toys"}), "error"))


if __name__ == "__main__":
    unittest.main()
