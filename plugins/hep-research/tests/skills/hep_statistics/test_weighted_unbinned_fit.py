"""S08 verified walkthrough for the sWeights section of skills/hep-statistics/references/likelihood-fitting.md.

SYNTHETIC toy study (seeded): a Gaussian mass peak (mean 0.5, width 0.05) on a flat background in m in [0, 1];
signal decay time exponential with tau_s = 1, background exponential with tau_b = 3; Poisson yields 1000 signal and
2000 background. Per toy: an extended maximum-likelihood fit of the yields in m (shapes known), sWeights
(Pivk & Le Diberder 2005), and the weighted unbinned fit of tau_s, whose estimate is sum(w t)/sum(w). Uncertainties:
  (a) naive: inverse weighted Hessian, sigma = tau_hat / sqrt(sum w);
  (s) "sandwich" with the weights treated as known: H^-1 (sum w^2 g^2) H^-1;
  (b) asymptotically correct: the stacked estimating equations of the yields, the inverse yield covariance and tau,
      A^-1 B A^-T with B from the per-event contributions (Poisson process), which carries the sWeights' own
      uncertainty (Langenbruch 2022).
Only (b) is asserted (pull width in [0.9, 1.1] over 300 toys, work order [Proposal]); (a) and (s) are reported as
measured. A variant in which the background decay time depends on m breaks the factorization sPlot assumes and
biases tau_s; the bias is reported. The test checks that the reference quotes exactly the numbers it computes."""
import math
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
REF = PLUGIN / "skills" / "hep-statistics" / "references" / "likelihood-fitting.md"

try:
    import numpy as np
    HAVE_NP = True
except ImportError:
    HAVE_NP = False

MU, SIG, TAU_S, TAU_B, NS, NB, TOYS, SEED = 0.5, 0.05, 1.0, 3.0, 1000, 2000, 300, 20261003


def f_sig(m):
    norm = 0.5 * (math.erf((1 - MU) / (SIG * math.sqrt(2))) - math.erf((0 - MU) / (SIG * math.sqrt(2))))
    return np.exp(-0.5 * ((m - MU) / SIG) ** 2) / (SIG * math.sqrt(2 * math.pi) * norm)


def generate(rng, dependent=False):
    ns, nb = rng.poisson(NS), rng.poisson(NB)
    ms = rng.normal(MU, SIG, 3 * ns)
    ms = ms[(ms >= 0) & (ms <= 1)][:ns]
    mb = rng.uniform(0, 1, nb)
    ts = rng.exponential(TAU_S, ms.size)
    tau_b = 1.0 + 4.0 * np.abs(mb - 0.5) if dependent else np.full(nb, TAU_B)   # variant: tau_b depends on m
    tb = rng.exponential(tau_b)
    return np.concatenate([ms, mb]), np.concatenate([ts, tb])


def fit_yields(F):
    """Extended ML of the yields for per-event densities F (n, 2); Newton from the event count."""
    y = np.array([F.shape[0] / 3, 2 * F.shape[0] / 3])
    for _ in range(100):
        D = F @ y
        g = (F / D[:, None]).sum(axis=0) - 1.0
        H = -(F[:, :, None] * F[:, None, :] / (D ** 2)[:, None, None]).sum(axis=0)
        step = np.linalg.solve(H, -g)
        y = y + step
        if np.max(np.abs(step)) < 1e-10:
            break
    return y


def estimating(theta, F, t):
    """Per-event contributions u_i (n, 6) and deterministic part K (6,) of U(theta) = sum u_i - K.
    theta = (N_s, N_b, W_ss, W_sb, W_bb, tau)."""
    ns, nb, wss, wsb, wbb, tau = theta
    D = F @ np.array([ns, nb])
    winv = np.linalg.inv(np.array([[wss, wsb], [wsb, wbb]]))
    w = (winv[0, 0] * F[:, 0] + winv[0, 1] * F[:, 1]) / D
    u = np.column_stack([F[:, 0] / D, F[:, 1] / D, F[:, 0] ** 2 / D ** 2, F[:, 0] * F[:, 1] / D ** 2,
                         F[:, 1] ** 2 / D ** 2, w * (t / tau ** 2 - 1 / tau)])
    K = np.array([1.0, 1.0, wss, wsb, wbb, 0.0])
    return u, K


def one_toy(rng, dependent=False):
    m, t = generate(rng, dependent)
    F = np.column_stack([f_sig(m), np.ones_like(m)])
    y = fit_yields(F)
    D = F @ y
    W = (F[:, :, None] * F[:, None, :] / (D ** 2)[:, None, None]).sum(axis=0)   # inverse yield covariance
    V = np.linalg.inv(W)
    w = (V[0, 0] * F[:, 0] + V[0, 1] * F[:, 1]) / D                              # sWeights
    tau = float(np.sum(w * t) / np.sum(w))
    sig_a = tau / math.sqrt(w.sum())
    g = t / tau ** 2 - 1 / tau
    h = w.sum() / tau ** 2
    sig_s = math.sqrt(np.sum(w ** 2 * g ** 2)) / h
    theta = np.array([y[0], y[1], W[0, 0], W[0, 1], W[1, 1], tau])
    u, K = estimating(theta, F, t)
    B = u.T @ u
    A = np.empty((6, 6))
    for j in range(6):
        step = 1e-6 * max(1.0, abs(theta[j]))
        tp, tm = theta.copy(), theta.copy()
        tp[j] += step
        tm[j] -= step
        up, kp = estimating(tp, F, t)
        um, km = estimating(tm, F, t)
        A[:, j] = ((up.sum(axis=0) - kp) - (um.sum(axis=0) - km)) / (2 * step)
    Ai = np.linalg.inv(A)
    sig_b = math.sqrt((Ai @ B @ Ai.T)[5, 5])
    return tau, sig_a, sig_s, sig_b


def study(dependent=False, toys=TOYS, seed=SEED):
    rng = np.random.default_rng(seed + (1 if dependent else 0))
    r = np.array([one_toy(rng, dependent) for _ in range(toys)])
    tau = r[:, 0]
    out = {"tau_mean": tau.mean(), "tau_sd": tau.std(ddof=1)}
    for k, name in ((1, "a"), (2, "s"), (3, "b")):
        pulls = (tau - TAU_S) / r[:, k]
        out[f"pull_mean_{name}"], out[f"pull_width_{name}"] = pulls.mean(), pulls.std(ddof=1)
    return out


def fmt(x):
    return f"{x:.3f}"


@unittest.skipUnless(HAVE_NP, "numpy not installed: sWeights walkthrough unverified")
class SWeightsWalkthrough(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ok = study()
        cls.dep = study(dependent=True)
        print("\nsWeights study:", {k: round(v, 4) for k, v in cls.ok.items()},
              "\nfactorization broken:", {k: round(v, 4) for k, v in cls.dep.items()})

    def test_asymptotically_correct_pull_width(self):
        self.assertTrue(0.9 <= self.ok["pull_width_b"] <= 1.1, self.ok)

    def test_reference_quotes_the_computed_numbers(self):
        text = " ".join(REF.read_text(encoding="utf-8").split())
        for key in ("pull_width_a", "pull_width_s", "pull_width_b", "tau_mean"):
            self.assertIn(fmt(self.ok[key]), text, key)
        self.assertIn(fmt(self.dep["tau_mean"]), text)
        self.assertIn(fmt(self.dep["pull_mean_b"]), text)

    def test_broken_factorization_biases_the_fit(self):
        # the bias is reported, and it is large compared with the toy-mean uncertainty
        se = self.dep["tau_sd"] / math.sqrt(TOYS)
        self.assertGreater(abs(self.dep["tau_mean"] - TAU_S), 5 * se, self.dep)


if __name__ == "__main__":
    unittest.main()
