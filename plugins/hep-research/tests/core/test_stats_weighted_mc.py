"""hep-statistics audit T20: weighted and signed-weight Monte Carlo templates. SYNTHETIC.

The effective-count Barlow-Beeston likelihood of template_fit.py treats sumw^2/sumw2 as Poisson counts, valid for
positive weights only: a template declared signed, with a negative bin sum (a negative-weight component split into its
own template) or with sumw2 > sumw^2 (which only signed weights produce) is refused. For signed-weight MC the Gaussian
MC-statistics term of shape-limit (mc_stat = sqrt(sumw2), Barlow-Beeston-lite) is validated against the known truth:
background MC with 20% negative weights is drawn event by event, the 68.27% two-sided profile-likelihood interval of mu
covers mu_true at nominal with the term, and undercovers without it (the negative baseline). Criteria fixed before
the run: |coverage - 0.6827| <= 4 standard errors; the baseline below by more than 4 standard errors."""
import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats import template_fit as tf  # noqa: E402
from core.stats._poisson import ppf  # noqa: E402

B = [40.0, 25.0, 15.0, 8.0]
S = [2.0, 4.0, 6.0, 4.0]
F_NEG, W0, TOYS, NOMINAL = 0.2, 0.5, 600, 0.6827


def signed_template(rng):
    """Per bin: Poisson number of MC events, weight -W0 with probability F_NEG else +W0; E[sumw] = B."""
    sumw, sumw2 = [], []
    for b in B:
        lam = b / ((1 - 2 * F_NEG) * W0)
        k = ppf(rng.random(), lam)
        neg = sum(rng.random() < F_NEG for _ in range(k))
        sumw.append((k - 2 * neg) * W0)
        sumw2.append(k * W0 * W0)
    return sumw, sumw2


def covers(rng, with_mc):
    sumw, sumw2 = signed_template(rng)
    if min(sumw) <= 0:
        return None
    n = [ppf(rng.random(), s + b) for s, b in zip(S, B)]
    bins = [{"n": k, "b": w, "s": s} for k, w, s in zip(n, sumw, S)]
    if with_mc:
        for x, w2 in zip(bins, sumw2):
            x["mc_stat"] = math.sqrt(w2)
    m = ll._ShapeModel(*ll._load_shape({"bins": bins}))
    aux = m.aux_obs()
    mu_hat, _, best = m.glob(m.n, aux)
    t = 2.0 * (m.cond(1.0, m.n, aux)[1] - best)
    if m.log.summary()["observed"]["failed"]:
        return "failed"
    return t <= 1.0


class SignedWeightTemplates(unittest.TestCase):
    def test_effective_count_likelihood_refuses_signed_weights(self):
        rng = random.Random(1)
        sumw, sumw2 = signed_template(rng)
        base = {"data": [42, 30, 20, 11], "templates": {"sig": S}}
        for tmpl, why in (({"sumw": sumw, "sumw2": sumw2, "weights": "signed"}, "not supported"),
                          ({"sumw": [-1.0, 2.0, 3.0, 1.0], "sumw2": [1.0, 4.0, 9.0, 1.0]}, "negative sum"),
                          ({"sumw": [10.0, 5.0, 3.0, 2.0], "sumw2": [150.0, 5.0, 3.0, 2.0]}, "exceeds sumw")):
            with self.assertRaisesRegex(tf.ToyError, why):
                tf.wbb_fit(dict(base, templates={"sig": S, "bkg": tmpl}))
        ok = tf.wbb_fit(dict(base, templates={"sig": S, "bkg": {"sumw": B, "sumw2": [b * 0.5 for b in B]}}))
        self.assertIn(ok["status"], ("ok", "failed"))

    def test_gaussian_mc_term_covers_and_ignoring_it_does_not(self):
        se = math.sqrt(NOMINAL * (1 - NOMINAL) / TOYS)
        result = {}
        for with_mc in (True, False):
            rng = random.Random(2026)
            outcomes = [covers(rng, with_mc) for _ in range(TOYS)]
            self.assertNotIn("failed", outcomes)
            usable = [o for o in outcomes if o is not None]
            self.assertGreater(len(usable), 0.99 * TOYS)              # a non-positive bin sum is rare and counted
            result[with_mc] = sum(usable) / len(usable)
        self.assertLess(abs(result[True] - NOMINAL), 4 * se, result)
        self.assertLess(result[False], NOMINAL - 4 * se, result)


if __name__ == "__main__":
    unittest.main()
