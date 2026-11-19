"""CHK-AT-08-01 (S1): charge_confusion_rate.py template mode must return the Barlow-Beeston maximum of the likelihood,
not a point where its minimizer stopped, also at 5e5 and 1e6 events per bin.

SYNTHETIC inputs: the discriminant shapes of test_charge_confusion_rate.py (RIGHT, WRONG; MC generated count twice
the template sum), data and templates drawn with fixed seeds at injected rates c = 1e-2 and 5e-2.

Oracles (neither imports charge_confusion_rate.py or core/stats/template_fit.py):
- profile scan (basis locator, pdg_2025_statistics): the joint likelihood of the data and the MC template counts with
  one nuisance per bin and template, L(theta, nu) = P(x | theta, nu) P(y | nu) (PDG sec. 40.2.6.1, eq. 40.40), each
  factor Poisson; the nuisances are profiled (eq. 40.41) per bin by exact cyclic coordinate descent (each 1-D
  minimum is the positive root of a quadratic; the per-bin function is convex), the total yield by golden-section
  search, and the rate on the stated grid RATE_GRID, refined by golden-section search. The maximum of L defines the
  MLE (sec. 40.2.2, eq. 40.9); the 68.27% interval is where 2 Delta ln L = 1 (eq. 40.78 and Table 40.1, M = 1).
- third-party (scipy): the same joint likelihood with scipy.stats.poisson.logpmf, maximized over all yields and
  nuisances (log parameters) by scipy.optimize.minimize (L-BFGS-B) from three interior starts; the deepest is kept.
- general result: at the MLE no other point has a larger likelihood, so the tool's reported yields, put into the
  oracle likelihood, must be within TOL["dnll"] of the oracle maximum.
Property: the rate is invariant under a common permutation of the discriminant bins (the likelihood is a sum over
bins). Negative control: the pre-fix start sequence (naive fit, then one Barlow-Beeston fit, as the tool did before
the fix) is emulated with core.stats.template_fit and must be rejected by the oracle.

Tolerances (fixed before the first run): TOL["rate_sigma"] = 0.1 of the oracle's 68% half-width sigma, for the rate
and both interval ends. The tool's Nelder-Mead stops at a ln L spread of about 1e-10 (1 + |ln L|) ~ 1e-3 at
|ln L| ~ 1e7, which moves a profile minimum by up to sqrt(2 x 1e-3) = 0.045 sigma; 0.1 sigma is twice that. The
pre-fix tool is off by 8 sigma or more at 1e6 events. TOL["dnll"] = 0.05 in 2 Delta ln L: 25 times the 2e-3 that
the Nelder-Mead tolerance allows, and far below the 2 Delta ln L = 1 of one standard deviation; the oracle's own
error (coordinate descent to 1e-13 relative, golden-section to 1e-9 of its bracket) is below 1e-6.
"""
import importlib.util
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
CASES = [(5e5, 1e-2, 0), (5e5, 5e-2, 1), (1e6, 1e-2, 0), (1e6, 5e-2, 0)]   # (events per bin, injected rate, seed)
TOL = {"rate_sigma": 0.1, "dnll": 0.05}
RATE_GRID = [10.0 ** (-5 + t / 8.0) for t in range(41)]   # 1e-5 to 1 in eighth decades, the scan's stated domain
GOLD = (math.sqrt(5.0) - 1.0) / 2.0


def poisson(rng, mu):
    if mu > 50:
        return max(0, int(round(rng.gauss(mu, math.sqrt(mu)))))
    k, p, l_ = 0, 1.0, math.exp(-mu)
    while True:
        p *= rng.random()
        if p <= l_:
            return k
        k += 1


def toy_bin(n_total, rate, seed):
    rng = random.Random(seed * 1000 + int(rate * 1e4) + int(n_total))
    sr, sw = sum(RIGHT), sum(WRONG)
    mu = [n_total * ((1 - rate) * r / sr + rate * w / sw) for r, w in zip(RIGHT, WRONG)]
    return {"data": [poisson(rng, m) for m in mu],
            "templates": {"right": [poisson(rng, r) for r in RIGHT], "wrong": [poisson(rng, w) for w in WRONG]},
            "mc_events": {"right": 2 * sr, "wrong": 2 * sw}}


# ------------------------------------------------------------------ oracle 1: profile scan of the joint likelihood
def bin_nll(d, a, p):
    """min over A >= 0 of nu - d ln nu + sum_j (A_j - a_j ln A_j), nu = sum_j p_j A_j (PDG eq. 40.40 for one bin,
    constants dropped), by exact cyclic coordinate descent."""
    k = len(a)
    A = [float(max(x, 0.5)) for x in a]
    for _ in range(20000):
        change = 0.0
        for j in range(k):
            s = sum(p[t] * A[t] for t in range(k) if t != j)
            pj, aj = p[j], a[j]
            qa, qb, qc = (1 + pj) * pj, (1 + pj) * s - d * pj - aj * pj, -aj * s
            if pj == 0:   # the template does not enter nu: A_j - a_j ln A_j alone, minimum at a_j
                a_next = float(aj)
            elif aj > 0:
                disc = math.sqrt(qb * qb - 4 * qa * qc)
                a_next = (-qb + disc) / (2 * qa) if qb <= 0 else (-2 * qc) / (qb + disc)
            else:
                a_next = max(0.0, -qb / qa)
            change = max(change, abs(a_next - A[j]) / (1.0 + A[j]))
            A[j] = a_next
        if change < 1e-13:
            break
    nu = sum(pj * Aj for pj, Aj in zip(p, A))
    return nu - (d * math.log(nu) if d > 0 else 0.0) + sum(Aj - (aj * math.log(Aj) if aj > 0 else 0.0)
                                                         for Aj, aj in zip(A, a))


def nll(doc, yields):
    names = ["right", "wrong"]
    mc = [doc["mc_events"][n] for n in names]
    return sum(bin_nll(d, [doc["templates"][n][i] for n in names], [yields[n] / mc[j] for j, n in enumerate(names)])
               for i, d in enumerate(doc["data"]))


def golden(f, lo, hi, iterations):
    c, d = hi - GOLD * (hi - lo), lo + GOLD * (hi - lo)
    fc, fd = f(c), f(d)
    for _ in range(iterations):
        if fc < fd:
            hi, d, fd = d, c, fc
            c = hi - GOLD * (hi - lo)
            fc = f(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + GOLD * (hi - lo)
            fd = f(d)
    x = 0.5 * (lo + hi)
    return x, f(x)


def profile(doc, r):
    """-ln L profiled at rate r (PDG eq. 40.41): the total yield N by golden-section search."""
    scale = sum(doc["data"]) * 0.5 * sum(doc["mc_events"][n] / sum(doc["templates"][n]) for n in ("right", "wrong"))

    def g(ln_n):
        n = math.exp(ln_n)
        return nll(doc, {"right": n * (1 - r), "wrong": n * r})
    return golden(g, math.log(0.5 * scale), math.log(2.0 * scale), 50)[1]


def oracle_scan(doc):
    """(r_hat, -ln L at r_hat, lo, hi) of the profile likelihood in r."""
    vals = [profile(doc, r) for r in RATE_GRID]
    b = min(range(len(RATE_GRID)), key=lambda t: vals[t])
    r_hat, best = golden(lambda r: profile(doc, r), RATE_GRID[max(b - 1, 0)], RATE_GRID[min(b + 1, len(RATE_GRID) - 1)], 40)

    def excess(r):
        return 2.0 * (profile(doc, r) - best) - 1.0

    def bisect(a, b):  # excess(a) < 0 <= excess(b), either order
        for _ in range(40):
            c = 0.5 * (a + b)
            if excess(c) < 0:
                a = c
            else:
                b = c
        return 0.5 * (a + b)
    lo = 0.0 if excess(0.0) < 0 else bisect(r_hat, 0.0)
    hi = bisect(r_hat, min(1.0, 3.0 * r_hat))
    return r_hat, best, lo, hi


# ---------------------------------------------------------------------------------- oracle 2: scipy, all nuisances
def scipy_rate(doc):
    names = ["right", "wrong"]
    d = np.array(doc["data"], float)
    a = np.array([doc["templates"][n] for n in names], float)
    mc = np.array([doc["mc_events"][n] for n in names], float)
    k, nb = a.shape

    def f(x):
        y, nuis = np.exp(x[:k]), np.exp(x[k:]).reshape(k, nb)
        part = (y / mc)[:, None] * nuis
        nu = part.sum(0)
        val = -(stats.poisson.logpmf(d, nu).sum() + stats.poisson.logpmf(a, nuis).sum())
        w = 1.0 - d / nu
        return val, np.concatenate([(part * w[None, :]).sum(1), (part * w[None, :] + nuis - a).ravel()])
    best = None
    for c0 in (0.5, 0.2, 0.05):
        y0 = d.sum() * mc / a.sum(1) * np.array([1 - c0, c0])
        x0 = np.concatenate([np.log(y0), np.log(np.maximum(a, 0.5)).ravel()])
        res = optimize.minimize(f, x0, jac=True, method="L-BFGS-B", bounds=[(None, None)] * k + [(-40, None)] * (k * nb),
                                options={"maxiter": 100000, "maxfun": 100000, "ftol": 1e-16, "gtol": 1e-9, "maxcor": 50})
        if best is None or res.fun < best.fun:
            best = res
    y = np.exp(best.x[:k])
    return float(y[1] / y.sum())


def run_tool(docs):
    doc = {"edges": [float(e) for e in range(1, len(docs) + 2)], "true_sign": "negative", "bins": docs}
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "t.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        p = subprocess.run([sys.executable, "-B", str(SCRIPT), "template", "--input", str(path)], capture_output=True,
                           text=True, timeout=1200)
    return p.returncode, json.loads(p.stdout)


class TemplateMaximum(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = [toy_bin(*case) for case in CASES]
        cls.code, cls.out = run_tool(cls.docs)
        cls.oracle = [oracle_scan(doc) for doc in cls.docs]

    def sigma(self, k):
        return 0.5 * (self.oracle[k][3] - self.oracle[k][2])

    def test_rate_and_interval_match_profile_scan(self):
        self.assertEqual((self.code, self.out["status"]), (0, "ok"), self.out.get("warnings"))
        for k, case in enumerate(CASES):
            r_hat, _, lo, hi = self.oracle[k]
            row, tol = self.out["bins"][k], TOL["rate_sigma"] * self.sigma(k)
            with self.subTest(case=case):
                self.assertLessEqual(abs(row["rate"] - r_hat), tol, (row["rate"], r_hat))
                self.assertLessEqual(abs(row["interval_68"][0] - lo), tol, (row["interval_68"], lo, hi))
                self.assertLessEqual(abs(row["interval_68"][1] - hi), tol, (row["interval_68"], lo, hi))

    @unittest.skipUnless(HAVE_SCIPY, "scipy not installed")
    def test_rate_matches_scipy_explicit_nuisance_fit(self):
        for k, case in enumerate(CASES):
            with self.subTest(case=case):
                expected = scipy_rate(self.docs[k])
                self.assertLessEqual(abs(self.out["bins"][k]["rate"] - expected), TOL["rate_sigma"] * self.sigma(k),
                                     (self.out["bins"][k]["rate"], expected))

    def test_reported_yields_are_the_maximum(self):
        for k, case in enumerate(CASES):
            with self.subTest(case=case):
                gap = 2.0 * (nll(self.docs[k], self.out["bins"][k]["yields"]) - self.oracle[k][1])
                self.assertLessEqual(gap, TOL["dnll"], gap)

    def test_property_bin_permutation_invariance(self):
        perm = [5, 2, 7, 0, 3, 6, 1, 4]
        docs = [{"data": [doc["data"][i] for i in perm],
                 "templates": {n: [doc["templates"][n][i] for i in perm] for n in ("right", "wrong")},
                 "mc_events": doc["mc_events"]} for doc in self.docs]
        code, out = run_tool(docs)
        self.assertEqual(code, 0, out.get("warnings"))
        for k, case in enumerate(CASES):
            with self.subTest(case=case):
                self.assertLessEqual(abs(out["bins"][k]["rate"] - self.out["bins"][k]["rate"]),
                                     TOL["rate_sigma"] * self.sigma(k))

    def test_negative_control_pre_fix_start_is_rejected(self):
        """The pre-fix sequence (naive fit from an equal split, then one Barlow-Beeston fit from it) stops below the
        maximum at 1e6 events; the oracle must see that (2 Delta ln L > 1, rate off by more than one sigma)."""
        sys.path.insert(0, str(PLUGIN))
        spec = importlib.util.spec_from_file_location("template_fit_negative_control", PLUGIN / "core" / "stats" / "template_fit.py")
        tf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tf)
        k = CASES.index((1e6, 1e-2, 0))
        tnames, observed, m, mc = tf._load(self.docs[k])
        total = sum(observed)
        y0 = tf._fit_yields_full(observed, m, mc, "naive", [max(total / len(tnames), 1.0)] * len(tnames))[0]
        y = tf._fit_yields_full(observed, m, mc, "bb", [max(v, 1.0) for v in y0])[0]
        pre = dict(zip(tnames, y))
        gap = 2.0 * (nll(self.docs[k], pre) - self.oracle[k][1])
        self.assertGreater(gap, 1.0)
        self.assertGreater(abs(pre["wrong"] / (pre["right"] + pre["wrong"]) - self.oracle[k][0]), self.sigma(k))


if __name__ == "__main__":
    unittest.main()
