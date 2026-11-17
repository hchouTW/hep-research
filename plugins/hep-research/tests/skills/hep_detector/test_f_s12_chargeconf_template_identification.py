"""CHK-AT-08-03 (S2): charge_confusion_rate.py template mode must not report a rate that the fit does not identify.

With a background template degenerate with the right-sign template, the right-sign yield, and so the rate
r = Y_wrong / (Y_right + Y_wrong), is not identified: the bin must be failed with a warning naming it, and its
sign_rates entries must not carry a rate (the lead's decision for CHK-AT-08-03: not identified means the profile
interval reaches r = 1, or the background template is degenerate with the right-sign template within statistics).

SYNTHETIC inputs (seeded): 2e4 events per bin, injected rate 0.02, the discriminant shapes of
test_charge_confusion_rate.py. Bin 1 has no background (control: identified); bin 2 a background drawn from the
right-sign shape (seed 100); bin 3 a background whose counts equal the right-sign template's; bin 4 a background drawn
from the right-sign shape (seed 101).

Oracles (neither imports charge_confusion_rate.py or core/stats/template_fit.py):
- third-party likelihood (scipy): the joint Poisson likelihood of the data and the MC template counts with one
  nuisance per bin and template (pdg_2025_statistics sec. 40.2.6.1, eq. 40.40), from scipy.stats.poisson.logpmf,
  minimized by scipy.optimize.minimize (L-BFGS-B) from four starts, freely and with the right-sign yield fixed at 0
  (r = 1). Where 2 Delta ln L(r = 1) < 1 the 68.27% profile interval reaches r = 1 (eq. 40.78, Table 40.1, M = 1):
  expected not identified; the control must have 2 Delta ln L(r = 1) > 1.
- third-party homogeneity test (scipy.stats.chi2_contingency, Pearson, no continuity correction) of the right-sign
  and background template counts: p >= 0.01 means the two shapes are compatible within the template statistics, so
  the background is degenerate with the right-sign template: expected not identified.
Expected values come from these oracles. Tolerances: 2 Delta ln L is compared with 1 and p with 0.01, the thresholds of
the rule; the cases are chosen far from them (bins 3 and 4 have 2 Delta ln L(r = 1) below 1e-6, bin 2 p = 0.25, bin 1
2 Delta ln L(r = 1) in the thousands), so the optimizer's precision (below 1e-6 in ln L) cannot change a verdict.
"""
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "charge_confusion_rate.py"

try:
    import numpy as np
    from scipy import optimize, stats
    HAVE_SCIPY = True
except ImportError:  # pragma: no cover - scipy is a core requirement
    HAVE_SCIPY = False

RIGHT = [400, 1200, 2400, 1200, 400, 40, 4, 1]   # SYNTHETIC discriminant shapes (MC counts)
WRONG = [1, 4, 40, 400, 1200, 2400, 1200, 400]
P_DEGENERATE = 0.01


def poisson(rng, mu):
    if mu > 50:
        return max(0, int(round(rng.gauss(mu, math.sqrt(mu)))))
    k, p, l_ = 0, 1.0, math.exp(-mu)
    while True:
        p *= rng.random()
        if p <= l_:
            return k
        k += 1


def toy(seed, background):
    """background: None, 'drawn' (from the right-sign shape) or 'identical' (the right-sign template's counts)."""
    rng = random.Random(seed)
    sr, sw = sum(RIGHT), sum(WRONG)
    mu = [20000 * (0.98 * r / sr + 0.02 * w / sw) for r, w in zip(RIGHT, WRONG)]
    b = {"data": [poisson(rng, v) for v in mu],
         "templates": {"right": [poisson(rng, r) for r in RIGHT], "wrong": [poisson(rng, w) for w in WRONG]},
         "mc_events": {"right": 2 * sr, "wrong": 2 * sw}}
    if background == "drawn":
        b["templates"]["background"] = [poisson(rng, r) for r in RIGHT]
    elif background == "identical":
        b["templates"]["background"] = list(b["templates"]["right"])
    if background:
        b["mc_events"]["background"] = 2 * sr
    return b


BINS = [toy(100, None), toy(100, "drawn"), toy(100, "identical"), toy(101, "drawn")]


def scipy_nll(b, right_fixed_zero):
    names = list(b["templates"])
    d = np.array(b["data"], float)
    a = np.array([b["templates"][n] for n in names], float)
    mc = np.array([b["mc_events"][n] for n in names], float)
    k, nb = a.shape
    free = np.array([not (right_fixed_zero and n == "right") for n in names])
    nf = int(free.sum())

    def f(x):
        y = np.zeros(k)
        y[free] = np.exp(x[:nf])
        nuis = np.exp(x[nf:]).reshape(k, nb)
        part = (y / mc)[:, None] * nuis
        nu = part.sum(0)
        val = -(stats.poisson.logpmf(d, nu).sum() + stats.poisson.logpmf(a, nuis).sum())
        w = 1.0 - d / nu
        return val, np.concatenate([(part * w[None, :]).sum(1)[free], (part * w[None, :] + nuis - a).ravel()])
    scale = d.sum() * mc / a.sum(1)
    splits = ([0.9, 0.05, 0.05], [0.5, 0.02, 0.48], [0.05, 0.02, 0.93], [0.3, 0.3, 0.4]) if k == 3 else \
        ([0.98, 0.02], [0.9, 0.1], [0.5, 0.5], [0.2, 0.8])
    best = math.inf
    for split in splits:
        y0 = scale * np.array(split)
        x0 = np.concatenate([np.log(y0[free]), np.log(np.maximum(a, 0.5)).ravel()])
        res = optimize.minimize(f, x0, jac=True, method="L-BFGS-B", bounds=[(-30, None)] * nf + [(-40, None)] * (k * nb),
                                options={"maxiter": 100000, "maxfun": 100000, "ftol": 1e-16, "gtol": 1e-9, "maxcor": 50})
        best = min(best, float(res.fun))
    return best


def homogeneity_p(b):
    table = np.array([b["templates"]["right"], b["templates"]["background"]], float)
    table = table[:, table.sum(0) > 0]
    return float(stats.chi2_contingency(table, correction=False)[1])


@unittest.skipUnless(HAVE_SCIPY, "scipy not installed")
class TemplateIdentification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        doc = {"edges": [1.0, 2.0, 3.0, 4.0, 5.0], "true_sign": "negative", "bins": BINS}
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "t.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            p = subprocess.run([sys.executable, "-B", str(SCRIPT), "template", "--input", str(path)],
                               capture_output=True, text=True, timeout=1200)
        cls.code, cls.out = p.returncode, json.loads(p.stdout)
        cls.reaches_one = [2.0 * (scipy_nll(b, True) - scipy_nll(b, False)) < 1.0 for b in BINS]
        cls.degenerate = [("background" in b["templates"]) and homogeneity_p(b) >= P_DEGENERATE for b in BINS]
        cls.expected = [r or g for r, g in zip(cls.reaches_one, cls.degenerate)]

    def test_oracle_cases(self):
        """The oracles classify the cases as built: only the control is identified."""
        self.assertEqual(self.expected, [False, True, True, True], (self.reaches_one, self.degenerate))

    def test_not_identified_bins_fail_and_are_named(self):
        self.assertEqual((self.code, self.out["status"]), (1, "failed"), self.out["warnings"])
        for k, expected in enumerate(self.expected):
            with self.subTest(bin=k + 1):
                named = [w for w in self.out["warnings"] if f"bin {k + 1}:" in w and "not identified" in w]
                self.assertEqual(bool(named), expected, self.out["warnings"])

    def test_not_identified_rates_are_not_passed_on(self):
        sr = self.out["sign_rates"]["rates"][0]
        for k, expected in enumerate(self.expected):
            with self.subTest(bin=k + 1):
                if expected:
                    self.assertIsNone(sr["rate"][k])
                    self.assertIsNone(sr["rate_error"][k])
                else:
                    self.assertEqual(sr["rate"][k], self.out["bins"][k]["rate"])
                    self.assertLess(abs(sr["rate"][k] - 0.02), 4 * sr["rate_error"][k])


if __name__ == "__main__":
    unittest.main()
