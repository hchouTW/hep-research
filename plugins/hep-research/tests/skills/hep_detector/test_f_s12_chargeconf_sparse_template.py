"""CHK-AT-08-01 (S1), follow-up: with a sparse wrong-sign MC template, charge_confusion_rate.py template mode must
return the maximum of the likelihood as r -> 0+, not the value at exactly r = 0.

At a yield of exactly 0 the Barlow-Beeston log-likelihood the tool uses drops that template's MC-count terms, so
ln L at r = 0 is not the limit r -> 0+. With a wrong-sign template of 1-2 MC counts per bin the dropped terms make r = 0
look several units of ln L better than any r > 0, and a profile evaluated at exactly r = 0 returns rate 0 with a
68% interval of width ~1e-12, labelled ok.

SYNTHETIC inputs (the fix verifier's case): four bins, each with about 5000 right-sign events plus 3, 6, 10 and 20
wrong-sign events, right-sign MC template [400, 1200, 2400, 1200, 400, 40, 4, 1] and the sparse wrong-sign MC
template [0, 0, 1, 1, 2, 1, 1, 0], MC generated counts 11290 and 12.

Oracles (neither imports charge_confusion_rate.py or core/stats/template_fit.py):
- profile scan (basis locator, pdg_2025_statistics): the joint likelihood of the data and the MC template counts with
  one nuisance per bin and template, L(theta, nu) = P(x | theta, nu) P(y | nu) (PDG sec. 40.2.6.1, eq. 40.40), each
  factor Poisson and kept whole at every yield (a template with yield 0 still has its MC-count factor, so the
  likelihood is continuous at r = 0); the nuisances are profiled (eq. 40.41) per bin by exact cyclic coordinate
  descent, the total yield by golden-section search, the rate on RATE_GRID (0, then 1e-6 to 1 in eighth decades),
  refined by golden-section search. The maximum of L defines the MLE (sec. 40.2.2, eq. 40.9); the 68.27% interval is
  where 2 Delta ln L = 1 (eq. 40.78 and Table 40.1, M = 1), its lower end 0 when 2 Delta ln L(0) < 1.
- third-party (scipy): the same joint likelihood with scipy.stats.poisson.logpmf, maximized over all yields and
  nuisances (log parameters, bounded below so a yield may approach 0) by scipy.optimize.minimize (L-BFGS-B) from five
  starts with rates 0.2 to 2e-5; the deepest is kept.
- general result: at the MLE no other point has a larger likelihood, so the tool's reported yields, put into the
  oracle likelihood, must be within TOL["dnll"] of the oracle maximum.
Negative control: the profile at exactly r = 0 from core.stats.template_fit._ll_bb (the pre-fix evaluation, with the
total yield profiled by golden-section search) is emulated; it must pick r = 0 as the maximum, and its interval
upper end must be rejected by the oracle.

Tolerances (fixed before the first run): TOL["rate_sigma"] = 0.1 of the oracle's 68% half-width sigma, for the rate
and both interval ends. At |ln L| ~ 6.5e4 the tool's Nelder-Mead stops at a ln L spread of about 1e-10 (1 + |ln L|)
~ 7e-6, which moves a profile minimum by sqrt(2 x 7e-6) ~ 0.004 sigma; 0.1 sigma is 25 times that. The pre-fix tool
returns rate 0 and an upper end of ~5e-13 against oracle upper ends of 5e-3 to 1.2e-2, about 2 sigma off.
TOL["dnll"] = 0.05 in 2 Delta ln L: far above the tool's 1.4e-5 and far below the 2 Delta ln L = 1 of one standard
deviation; the oracle's own error (coordinate descent to 1e-13 relative, golden section to 1e-9 of its bracket) is
below 1e-6.
"""
import importlib.util
import json
import math
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

RIGHT = [400, 1200, 2400, 1200, 400, 40, 4, 1]   # SYNTHETIC MC templates
WRONG = [0, 0, 1, 1, 2, 1, 1, 0]
MC_EVENTS = {"right": 11290, "wrong": 12}
OBSERVED_COUNTS = [[354, 1063, 2126, 1063, 355, 36, 4, 1],   # about 5000 right-sign plus 3, 6, 10, 20 wrong-sign events
        [354, 1063, 2127, 1064, 356, 36, 5, 1],
        [354, 1063, 2127, 1065, 358, 37, 5, 1],
        [354, 1063, 2129, 1066, 361, 39, 7, 1]]
TOL = {"rate_sigma": 0.1, "dnll": 0.05}
RATE_GRID = [0.0] + [10.0 ** (-6 + t / 8.0) for t in range(49)]
GOLD = (math.sqrt(5.0) - 1.0) / 2.0
NAMES = ("right", "wrong")


def bins():
    return [{"data": list(d), "templates": {"right": list(RIGHT), "wrong": list(WRONG)}, "mc_events": dict(MC_EVENTS)}
            for d in OBSERVED_COUNTS]


# ------------------------------------------------------------------ oracle 1: profile scan of the joint likelihood
def bin_nll(d, a, p):
    """min over A >= 0 of nu - d ln nu + sum_j (A_j - a_j ln A_j), nu = sum_j p_j A_j (PDG eq. 40.40 for one bin,
    constants dropped; the MC factor of every template is kept, also at p_j = 0), by exact cyclic coordinate descent."""
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
    mc = [doc["mc_events"][n] for n in NAMES]
    return sum(bin_nll(d, [doc["templates"][n][i] for n in NAMES], [yields[n] / mc[j] for j, n in enumerate(NAMES)])
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


def n_bracket(doc):
    scale = sum(doc["data"]) * 0.5 * sum(doc["mc_events"][n] / sum(doc["templates"][n]) for n in NAMES)
    return math.log(0.5 * scale), math.log(2.0 * scale)


def profile(doc, r):
    """-ln L profiled at rate r (PDG eq. 40.41): the total yield N by golden-section search."""
    return golden(lambda ln_n: nll(doc, {"right": math.exp(ln_n) * (1 - r), "wrong": math.exp(ln_n) * r}),
                  *n_bracket(doc), 50)[1]


def oracle_scan(doc):
    """(r_hat, -ln L at r_hat, lo, hi) of the profile likelihood in r."""
    vals = [profile(doc, r) for r in RATE_GRID]
    b = min(range(len(RATE_GRID)), key=lambda t: vals[t])
    r_hat, best = golden(lambda r: profile(doc, r), RATE_GRID[max(b - 1, 0)], RATE_GRID[min(b + 1, len(RATE_GRID) - 1)],
                         40)
    if vals[b] < best:
        r_hat, best = RATE_GRID[b], vals[b]

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
    up = next(r for r in RATE_GRID if r > r_hat and excess(r) >= 0)
    return r_hat, best, lo, bisect(r_hat, up)


# ---------------------------------------------------------------------------------- oracle 2: scipy, all nuisances
def scipy_rate(doc):
    d = np.array(doc["data"], float)
    a = np.array([doc["templates"][n] for n in NAMES], float)
    mc = np.array([doc["mc_events"][n] for n in NAMES], float)
    k, nb = a.shape

    def f(x):
        y, nuis = np.exp(x[:k]), np.exp(x[k:]).reshape(k, nb)
        nu = ((y / mc)[:, None] * nuis).sum(0)
        return -(stats.poisson.logpmf(d, nu).sum() + stats.poisson.logpmf(a, nuis).sum())
    best = None
    for c0 in (0.2, 0.02, 2e-3, 2e-4, 2e-5):
        y0 = d.sum() * mc / a.sum(1) * np.array([1 - c0, c0])
        x0 = np.concatenate([np.log(y0), np.log(np.maximum(a, 0.5)).ravel()])
        res = optimize.minimize(f, x0, method="L-BFGS-B", bounds=[(-30, None)] * k + [(-40, None)] * (k * nb),
                                options={"maxiter": 200000, "maxfun": 200000, "ftol": 1e-15, "gtol": 1e-10})
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


class SparseTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = bins()
        cls.code, cls.out = run_tool(cls.docs)
        cls.oracle = [oracle_scan(doc) for doc in cls.docs]

    def sigma(self, k):
        return 0.5 * (self.oracle[k][3] - self.oracle[k][2])

    def test_rate_and_interval_match_profile_scan(self):
        self.assertEqual((self.code, self.out["status"]), (0, "ok"), self.out.get("warnings"))
        for k in range(len(OBSERVED_COUNTS)):
            r_hat, _, lo, hi = self.oracle[k]
            row, tol = self.out["bins"][k], TOL["rate_sigma"] * self.sigma(k)
            with self.subTest(bin=k):
                self.assertLessEqual(abs(row["rate"] - r_hat), tol, (row["rate"], r_hat))
                self.assertLessEqual(abs(row["interval_68"][0] - lo), tol, (row["interval_68"], lo, hi))
                self.assertLessEqual(abs(row["interval_68"][1] - hi), tol, (row["interval_68"], lo, hi))

    @unittest.skipUnless(HAVE_SCIPY, "scipy not installed")
    def test_rate_matches_scipy_explicit_nuisance_fit(self):
        for k in range(len(OBSERVED_COUNTS)):
            with self.subTest(bin=k):
                expected = scipy_rate(self.docs[k])
                self.assertLessEqual(abs(self.out["bins"][k]["rate"] - expected), TOL["rate_sigma"] * self.sigma(k),
                                     (self.out["bins"][k]["rate"], expected))

    def test_reported_yields_are_the_maximum(self):
        for k in range(len(OBSERVED_COUNTS)):
            with self.subTest(bin=k):
                gap = 2.0 * (nll(self.docs[k], self.out["bins"][k]["yields"]) - self.oracle[k][1])
                self.assertLessEqual(gap, TOL["dnll"], gap)

    def test_negative_control_profile_at_exactly_zero_is_rejected(self):
        """The pre-fix evaluation (the profile from core.stats.template_fit._ll_bb on a rate grid that starts at
        exactly 0) picks r = 0, and its interval upper end (the first grid rate where 2 Delta ln L >= 1 from there)
        is rejected by the oracle."""
        sys.path.insert(0, str(PLUGIN))
        spec = importlib.util.spec_from_file_location("template_fit_sparse_negative_control",
                                                      PLUGIN / "core" / "stats" / "template_fit.py")
        tf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tf)
        k = 3   # the largest wrong-sign signal: oracle rate ~4e-3
        _, observed, m, mc = tf._load(self.docs[k])

        def pre_profile(r):
            return golden(lambda ln_n: -tf._ll_bb(observed, m, mc, [math.exp(ln_n) * (1 - r), math.exp(ln_n) * r]),
                          *n_bracket(self.docs[k]), 50)[1]
        vals = [pre_profile(r) for r in RATE_GRID]
        self.assertEqual(min(range(len(RATE_GRID)), key=lambda t: vals[t]), 0)
        hi_pre = next(r for r, v in zip(RATE_GRID, vals) if 2.0 * (v - vals[0]) >= 1.0)
        self.assertGreater(abs(hi_pre - self.oracle[k][3]), TOL["rate_sigma"] * self.sigma(k), (hi_pre, self.oracle[k]))
        self.assertGreater(self.oracle[k][0], TOL["rate_sigma"] * self.sigma(k), self.oracle[k])


if __name__ == "__main__":
    unittest.main()
