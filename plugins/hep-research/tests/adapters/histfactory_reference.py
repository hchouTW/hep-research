"""Reference HistFactory likelihood written without pyhf, used to cross-check the pyhf adapter workspaces in
adapters/pyhf-combine/assets/ (SYNTHETIC). Modifiers follow the pyhf 0.7 default definitions:

- normsys, interpolation code 4: exponential (hi**a, lo**-a) for |a| >= 1, inside a sixth-order polynomial matching
  value, slope and curvature at a = +-1;
- histosys, code 4p: linear for |a| >= 1, inside a + polynomial with the same value and derivatives at a = +-1;
- staterror: Gaussian constraint on a per-bin factor, relative width unc/nominal;
- shapesys: Poisson constraint on a per-bin factor, tau = (nominal/unc)**2;
- main measurement: Poisson with lgamma normalization; Gaussian constraints fully normalized.

The CLs limit uses the q~_mu test statistic, the asymptotic formulae and background-only Asimov data (nuisance
parameters from the mu = 0 fit to the observed data)."""
import math

import numpy as np
from scipy.optimize import brentq, minimize
from scipy.special import gammaln
from scipy.stats import norm

HALF_LOG_2PI = 0.5 * math.log(2 * math.pi)


def normsys_code4(hi, lo, a):
    """Multiplicative normsys factor at nuisance value a."""
    if abs(a) >= 1:
        return hi ** a if a >= 0 else lo ** (-a)
    lh, ll = math.log(hi), math.log(lo)
    rows, rhs = [], []
    for x, f, f1, f2 in ((1, hi, hi * lh, hi * lh * lh), (-1, lo, -lo * ll, lo * ll * ll)):
        rows += [[x ** i for i in range(1, 7)],
                 [i * x ** (i - 1) for i in range(1, 7)],
                 [i * (i - 1) * x ** (i - 2) if i > 1 else 0 for i in range(1, 7)]]
        rhs += [f - 1, f1, f2]
    coef = np.linalg.solve(np.array(rows, float), np.array(rhs))
    return 1 + sum(c * a ** (i + 1) for i, c in enumerate(coef))


def histosys_code4p(nom, hi, lo, a):
    """Additive histosys shift of the nominal histogram at nuisance value a."""
    nom, hi, lo = (np.asarray(x, float) for x in (nom, hi, lo))
    up, dn = hi - nom, nom - lo
    if abs(a) >= 1:
        return nom + (a * up if a >= 0 else a * dn)
    s, d = 0.5 * (up + dn), 0.0625 * (up - dn)
    return nom + a * (s + a * d * (15 + a * a * (3 * a * a - 10)))


def cls_from_q(q, qa):
    """Asymptotic CLs for q~_mu given its observed and Asimov values."""
    sq, sqa = math.sqrt(q), math.sqrt(qa)
    t = sq if sq <= sqa else (q + qa) / (2 * sqa)
    return (1 - norm.cdf(t)) / (1 - norm.cdf(t - sqa))


class ShapeModel:
    """The two-channel workspace pyhf-shape-synthetic.json. Parameters, in this order:
    mu, jes (histosys), bkg_xsec (normsys), three staterror factors (synthetic_sr), two shapesys factors (synthetic_cr)."""
    NAMES = ["mu", "jes", "bkg_xsec", "staterror_synthetic_sr[0]", "staterror_synthetic_sr[1]",
             "staterror_synthetic_sr[2]", "cr_shape[0]", "cr_shape[1]"]
    LO = np.array([0, -5, -5, 1e-3, 1e-3, 1e-3, 1e-3, 1e-3])
    HI = np.array([10, 5, 5, 3, 3, 3, 3, 3])

    def __init__(self, ws):
        ch = {c["name"]: {s["name"]: s for s in c["samples"]} for c in ws["channels"]}
        self.sr, self.cr = ch["synthetic_sr"], ch["synthetic_cr"]
        obs = {o["name"]: o["data"] for o in ws["observations"]}
        self.n = np.array(obs["synthetic_sr"] + obs["synthetic_cr"], float)
        bkg, crb = self.sr["background"], self.cr["background"]
        unc = np.array(self._mod(bkg, "staterror"))
        self.st_sigma = unc / np.array(bkg["data"])
        self.tau = (np.array(crb["data"]) / np.array(self._mod(crb, "shapesys"))) ** 2
        self.aux_obs = {"jes": 0.0, "bkg_xsec": 0.0, "st": np.ones(3), "tau": self.tau.copy()}

    @staticmethod
    def _mod(sample, kind):
        return next((m["data"] for m in sample["modifiers"] if m["type"] == kind), None)

    def _hist(self, sample, a):
        h = self._mod(sample, "histosys")
        return np.array(sample["data"], float) if h is None else histosys_code4p(sample["data"], h["hi_data"], h["lo_data"], a)

    def _norm(self, sample, a):
        m = self._mod(sample, "normsys")
        return 1.0 if m is None else normsys_code4(m["hi"], m["lo"], a)

    def expected(self, p):
        mu, jes, bx = p[0], p[1], p[2]
        s = mu * self._hist(self.sr["signal"], jes)
        b = self._norm(self.sr["background"], bx) * self._hist(self.sr["background"], jes) * np.asarray(p[3:6])
        c = self._norm(self.cr["background"], bx) * self._hist(self.cr["background"], jes) * np.asarray(p[6:8])
        return np.concatenate([s + b, c])

    def nll(self, p, n=None, aux=None):
        n = self.n if n is None else n
        aux = self.aux_obs if aux is None else aux
        lam = self.expected(p)
        if np.any(lam <= 0):
            return 1e30
        v = np.sum(lam - n * np.log(lam) + gammaln(n + 1))
        v += 0.5 * (p[1] - aux["jes"]) ** 2 + 0.5 * (p[2] - aux["bkg_xsec"]) ** 2 + 2 * HALF_LOG_2PI
        v += np.sum(0.5 * ((np.asarray(p[3:6]) - aux["st"]) / self.st_sigma) ** 2 + np.log(self.st_sigma) + HALF_LOG_2PI)
        g = np.asarray(p[6:8]) * self.tau
        v += np.sum(g - aux["tau"] * np.log(g) + gammaln(aux["tau"] + 1))
        return v

    def fit(self, n=None, aux=None, mu=None):
        """Global fit (mu is None) or fit with mu fixed; returns (parameters, nll). Two starting points."""
        free = list(range(8)) if mu is None else list(range(1, 8))
        best = None
        for start in ([1, 0, 0, 1, 1, 1, 1, 1], [0.3, 0.5, -0.5, 1, 1, 1, 1, 1]):
            x0 = np.array(start, float)
            if mu is not None:
                x0[0] = mu

            def f(x, x0=x0):
                q = x0.copy()
                q[free] = x
                return self.nll(q, n, aux)
            r = minimize(f, x0[free], method="L-BFGS-B", bounds=list(zip(self.LO[free], self.HI[free])),
                         options={"ftol": 1e-14, "gtol": 1e-9, "maxiter": 5000})
            q = x0.copy()
            q[free] = r.x
            if best is None or r.fun < best[1]:
                best = (q, r.fun)
        return best

    def asimov(self):
        p0, _ = self.fit(mu=0.0)
        return self.expected(p0), {"jes": p0[1], "bkg_xsec": p0[2], "st": p0[3:6].copy(), "tau": p0[6:8] * self.tau}

    def qtilde(self, mu, n=None, aux=None):
        p_hat, nll_hat = self.fit(n, aux)
        if p_hat[0] > mu:
            return 0.0
        return max(2 * (self.fit(n, aux, mu=mu)[1] - nll_hat), 0.0)

    def cls_limit(self, cl=0.95):
        na, auxa = self.asimov()
        return brentq(lambda mu: cls_from_q(self.qtilde(mu), self.qtilde(mu, na, auxa)) - (1 - cl), 0.5, 8.0, xtol=1e-5)
