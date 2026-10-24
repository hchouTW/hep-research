"""Geant4 program A1.15, slow tier (HEP_SLOW_TESTS=1; run and recorded in the release gate): toys of the study-layer
statistics in core/stats.

- Gate toys: the operating characteristics of the convergence gate (core.stats.decisions.equivalence) against the
  table of program spec A1.8 (printed there, computed by gate_operating_characteristics.py with numpy and scipy, 2e6
  toys per cell), 1e4 toys per cell, to +-3 sigma_MC. Model as stated in the table header: "se = target" columns draw
  diff ~ N(d, se) with se_diff = target = tol/4 estimated on nu = 30 (TOST part only); "two-stage" columns draw both
  points per A1.9 (K = K_trial = 16, f = F_0.90(15, 15)) and apply the full gate including the target condition.
- Coverage toys: nominal 90 % t intervals of batch means (core.stats.batch_means) for each class of J14 estimator
  (mean, proportion, quantile, mode), |coverage - 0.90| <= 0.02 + 3 sigma_MC, through core.stats.toy_ensemble's run,
  coverage and coverage_gate.
- MPV bias toys: the A1.7 design point of J14 (B = 30000, 2 keV bins, K = 16): 95 % upper bound of the relative bias
  <= tol/10 = 0.002, with Moyal toys of width 1.5 xi (checked against the recorded Geant4 histogram; VALIDATION).
- Detection-limit toys: an injection at the claimed limit DL = tol + |rel| + t_0.977(nu) se_rel is caught (the
  control's verdict is fail) with probability >= 0.977 - 3 sigma_MC (A1.10).
Standard library only (the oracles are the printed table and general results, not a reimplementation)."""
import math
import os
import random
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from core.stats import batch_means as M, decisions as D, toy_ensemble as TE  # noqa: E402
from core.stats.distributions import f_ppf, t_ppf  # noqa: E402

SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"
TOYS = 10_000
# program spec A1.8, operating characteristics (true difference in units of tol)
TABLE = {0.0: {"pass_tost": 0.976, "pass_two_stage": 0.809, "pass_two_stage_met": 0.999, "fail1": 0.000,
               "fail30": 0.000, "fail30_two_stage": 0.000},
         0.5: {"pass_tost": 0.621, "pass_two_stage": 0.696, "pass_two_stage_met": 0.860, "fail1": 0.000,
               "fail30": 0.000, "fail30_two_stage": 0.000},
         1.0: {"pass_tost": 0.050, "pass_two_stage": 0.044, "pass_two_stage_met": 0.054, "fail1": 0.050,
               "fail30": 0.002, "fail30_two_stage": 0.002},
         2.0: {"pass_tost": 0.000, "pass_two_stage": 0.000, "pass_two_stage_met": 0.000, "fail1": 0.988,
               "fail30": 0.780, "fail30_two_stage": 0.952}}


def chi2_over_nu(rng, nu):
    return rng.gammavariate(nu / 2.0, 2.0) / nu


def within(test, got, want, n, what):
    sigma = math.sqrt(max(want * (1 - want), 1.0 / n) / n)
    test.assertLessEqual(abs(got - want), 3 * sigma + 0.0005, f"{what}: toys {got:.4f}, table {want:.3f} (n={n})")


@unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
class GateToys(unittest.TestCase):
    def test_se_equal_to_the_target(self):
        rng = random.Random(81)
        tol, se, nu = 1.0, 0.25, 30
        for d, row in TABLE.items():
            p = f1 = f30 = 0
            for _ in range(TOYS):
                diff = rng.gauss(d, se)
                s = se * math.sqrt(chi2_over_nu(rng, nu))
                p += abs(diff) + t_ppf(0.95, nu) * s <= tol  # TOST part only (no target condition)
                f1 += D.equivalence(diff, s, nu, tol, m=1)["verdict"] == "fail"
                f30 += D.equivalence(diff, s, nu, tol, m=30)["verdict"] == "fail"
            within(self, p / TOYS, row["pass_tost"], TOYS, f"pass d={d}")
            within(self, f1 / TOYS, row["fail1"], TOYS, f"fail m=1 d={d}")
            within(self, f30 / TOYS, row["fail30"], TOYS, f"fail m=30 d={d}")

    def test_two_stage_design(self):
        rng = random.Random(82)
        tol, kd = 1.0, 15
        tgt, f = tol / (4 * math.sqrt(2)), f_ppf(0.90, kd, kd)

        def point():
            true = tgt / math.sqrt(f * chi2_over_nu(rng, kd))
            return true, true * math.sqrt(chi2_over_nu(rng, kd))
        for d, row in TABLE.items():
            both = given = met_n = f30 = 0
            for _ in range(TOYS):
                (ta, ea), (tb, eb) = point(), point()
                diff = rng.gauss(d, math.hypot(ta, tb))
                se = math.hypot(ea, eb)
                nu = D.welch_dof(ea, kd, eb, kd)
                met = ea <= tgt and eb <= tgt
                r = D.equivalence(diff, se, nu, tol, m=30, targets_met=met)
                both += r["verdict"] == "pass"
                met_n += met
                given += met and abs(diff) + t_ppf(0.95, nu) * se <= tol
                f30 += r["verdict"] == "fail"
            within(self, both / TOYS, row["pass_two_stage"], TOYS, f"two-stage pass d={d}")
            within(self, given / met_n, row["pass_two_stage_met"], met_n, f"two-stage pass|met d={d}")
            within(self, f30 / TOYS, row["fail30_two_stage"], TOYS, f"two-stage fail m=30 d={d}")


def _moyal(rng, mode, xi):
    z = rng.gauss(0.0, 1.0)
    return mode - xi * math.log(z * z)


@unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
class CoverageToys(unittest.TestCase):
    """Nominal 90 % batch-means t intervals, K = 16 blocks of B events, per estimator class."""
    K, B, N_TOYS = 16, 400, 2000

    def check(self, name, truth, block_estimate, seed):
        def generate(rng, index):
            return [block_estimate(rng) for _ in range(self.K)]

        def evaluate(blocks, index):
            r = M.batch_mean(blocks)
            h = M.t_halfwidth(r["se"], r["dof"], 0.90)
            return {"lo": r["value"] - h, "hi": r["value"] + h}
        spec = TE.EnsembleSpec(kind="plug-in", seed=seed, n_toys=self.N_TOYS)
        res = TE.run(spec, generate, evaluate)
        cov = TE.coverage(res, lambda o: o["lo"] <= truth <= o["hi"], 0.90)
        sigma = math.sqrt(0.9 * 0.1 / self.N_TOYS)
        got = cov["headline"]["value"]
        self.assertLessEqual(abs(got - 0.90), 0.02 + 3 * sigma, f"{name}: coverage {got:.4f}")
        gate = TE.coverage_gate(cov, max_deficit=0.02 + 3 * sigma)
        self.assertNotEqual(gate["verdict"], "fail", f"{name}: {gate}")

    def test_mean(self):
        self.check("mean", 1.0, lambda rng: sum(rng.expovariate(1.0) for _ in range(self.B)) / self.B, 11)

    def test_proportion(self):
        self.check("proportion", 0.1, lambda rng: sum(rng.random() < 0.1 for _ in range(self.B)) / self.B, 12)

    def test_quantile(self):
        def med(rng):
            xs = [rng.expovariate(1.0) for _ in range(self.B)]
            hist = [0] * 100
            for x in xs:
                if x < 5.0:
                    hist[int(x / 0.05)] += 1
            return M.hist_quantile(hist, 0.0, 0.05, 0.5, overflow=sum(x >= 5.0 for x in xs))["value"]
        self.check("quantile", math.log(2), med, 13)

    def test_mode(self):
        def mode(rng):
            hist = [0] * 120
            for _ in range(self.B * 5):
                x = rng.gauss(3.0, 1.0)
                if 0.0 <= x < 6.0:
                    hist[int(x / 0.05)] += 1
            return M.block_mode(hist, 0.0, 0.05)["value"]
        self.check("mode", 3.0, mode, 14)


@unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
class MpvBiasToys(unittest.TestCase):
    def test_j14_design_point(self):
        """J14's MPV design minimum B = 75000 events per block, 2 keV bins, K = 16, Moyal(mode 0.085 MeV, 1.5 xi with
        xi = 5.35 keV): 95 % upper bound of the relative bias of the mean of block modes <= 0.002 (tol/10 for
        mpv_deposit_MeV, tol 0.02), 4000 toys. Each block histogram is drawn as an exact multinomial of the bin
        probabilities (the Moyal CDF erfc(exp(-l/2)/sqrt(2))), which has the distribution of binning B events. The
        earlier design B >= 30000 (realised 34158) had a bias of about +0.0017, too close to the bound: 200- and
        1000-toy runs gave upper bounds of 0.0018 to 0.00209 (VALIDATION GEANT4-CORRECTNESS)."""
        import numpy as np
        mode, xi, w, b, k, toys, lo, hi = 0.085, 1.5 * 0.00535, 0.002, 75000, 16, 4000, 0.05, 0.13
        edges = [lo + i * w for i in range(round((hi - lo) / w) + 1)]
        cdf = [math.erfc(math.exp(-((x - mode) / xi) / 2) / math.sqrt(2)) for x in edges]
        p = [cdf[i + 1] - cdf[i] for i in range(len(edges) - 1)]
        p.append(1.0 - sum(p))
        rng = np.random.default_rng(91)
        est = [M.mpv([list(h[:-1]) for h in rng.multinomial(b, p, size=k)], lo, w)["value"] for _ in range(toys)]
        mean = sum(est) / toys
        sd = math.sqrt(sum((e - mean) ** 2 for e in est) / (toys - 1))
        ub = (mean - mode) / mode + 1.645 * sd / math.sqrt(toys) / mode
        self.assertLessEqual(ub, 0.002, f"95 % upper bound of the relative bias {ub:.5f}")


@unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
class DetectionLimitToys(unittest.TestCase):
    def test_an_injection_at_the_limit_is_caught(self):
        """A benchmark with reference accuracy 0.03, k = 3, relative se 0.004 per run on K = 16 blocks; the nominal
        deviates by rel ~ N(0, se); the control is injected at the DL claimed from the nominal and its control
        partner's se (both estimated, nu = 15 each); caught = the control's own verdict fails (|rel_c| > tol_c)."""
        rng = random.Random(97)
        acc, k_sigma, se, nu = 0.03, 3.0, 0.004, 15
        caught = 0
        for _ in range(TOYS):
            rel_n = rng.gauss(0.0, se)
            se_n, se_c = (se * math.sqrt(chi2_over_nu(rng, nu)) for _ in range(2))
            tol_n = acc + k_sigma * se_n
            dl = D.detection_limit(tol_n, rel_n, math.hypot(se_n, se_c), D.welch_dof(se_n, nu, se_c, nu))["value"]
            rel_c = rng.gauss(dl, se)
            caught += abs(rel_c) > acc + k_sigma * se_c
        p = caught / TOYS
        self.assertGreaterEqual(p, 0.977 - 3 * math.sqrt(0.977 * 0.023 / TOYS), f"power {p:.4f}")


if __name__ == "__main__":
    unittest.main()
