#!/usr/bin/env python3
"""Small exact-Poisson diagnostics for low-count analysis decisions.

Purpose: give the "use Poisson-exact, not Gaussian/Wilks/S-over-sqrt-B" rule an
executable form: exact upper limits and central intervals on a Poisson mean, the
zero-count bound, and a seeded toy coverage check of the interval. This is not a
statistics framework: it does not do profile likelihood, CLs, or unfolding.

What it does: (1) `upper-limit`: classical one-sided upper limit on a signal mean s
for n observed events and a KNOWN background b, found by solving P(N <= n | s + b) =
1 - CL; when the limit is <= 0 (n small versus b) it says the classical construction is
unphysical there and a Feldman-Cousins or CLs construction with toys is needed.
(2) `interval`: Garwood central interval on a Poisson mean (conservative). (3)
`coverage`: fraction of seeded pseudo-experiments whose interval contains the true mean.
(4) `fc-interval`: Feldman-Cousins unified interval on a signal mean for n observed events
and a KNOWN background, by a deterministic grid scan (no toys); the grid step bounds its
accuracy and discreteness makes the result slightly conservative. The upper end is made non-increasing in b as
Feldman and Cousins did for their tables (`--plain-construction` skips that; the output names the construction). (5) `cls-limit`:
CLs upper limit on a signal mean (observed, plus the median and 1/2-sigma expected limits
under background only). `fc-interval` and `cls-limit` accept `--sigma-b`: a background
uncertainty treated by Cousins-Highland marginalization over a truncated normal prior on b
(deterministic quantile nodes, no toys). That is an approximation (a prior-predictive
average, not a profile likelihood), and it is not a validated coverage statement.
Approximations are stated in the output ("[General method]"); seed, toy count and
configuration are always echoed so a run is reproducible.

Usage (from the skill directory):
  python3 core/stats/poisson_diagnostics.py upper-limit --n 0 --b 0 --cl 0.95
  python3 core/stats/poisson_diagnostics.py interval --n 3 --cl 0.6827
  python3 core/stats/poisson_diagnostics.py fc-interval --n 0 --b 3 --cl 0.90
  python3 core/stats/poisson_diagnostics.py fc-interval --n 3 --b 3 --sigma-b 1 --cl 0.90
  python3 core/stats/poisson_diagnostics.py cls-limit --n 3 --b 3 --sigma-b 0.5 --cl 0.95
  python3 core/stats/poisson_diagnostics.py coverage --mu 2.5 --cl 0.6827 --toys 20000 --seed 1
Exit codes: 0 ok; 2 rejected input. Standard library only.
Importable: poisson_cdf, upper_limit, central_interval, coverage, fc_interval, cls_limit.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

if __package__ in (None, ""):  # run as a script: put the plugin root on sys.path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
import json
import math
import random
import sys
from statistics import NormalDist

LABEL = "[General method]"
MAX_MEAN = 500.0  # inversion sampling and exp(-mu) stay accurate below this


class DiagnosticsError(ValueError):
    """Raised for invalid counts, backgrounds, confidence levels or means."""


def _count(n) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise DiagnosticsError(f"n must be a non-negative integer, got {n!r}")
    return n


def _cl(cl) -> float:
    if isinstance(cl, bool) or not isinstance(cl, (int, float)) or not 0.0 < cl < 1.0:
        raise DiagnosticsError(f"cl must lie strictly between 0 and 1, got {cl!r}")
    return float(cl)


def _mean(mu, name="mean", allow_zero=True) -> float:
    ok = isinstance(mu, (int, float)) and not isinstance(mu, bool) and math.isfinite(mu)
    if not ok or mu < 0 or (mu == 0 and not allow_zero):
        raise DiagnosticsError(f"{name} must be a finite non-negative number, got {mu!r}")
    if mu > MAX_MEAN:
        raise DiagnosticsError(f"{name} {mu} exceeds {MAX_MEAN}; use a Gaussian-validated method there")
    return float(mu)


def poisson_cdf(n: int, mu: float) -> float:
    """P(N <= n) for a Poisson mean mu, by direct summation."""
    n, mu = _count(n), _mean(mu)
    if mu == 0.0:
        return 1.0
    term = total = math.exp(-mu)
    for k in range(1, n + 1):
        term *= mu / k
        total += term
    return min(total, 1.0)


def _solve(f, lo: float, hi: float) -> float:
    """Root of a decreasing f on [lo, hi] by bisection."""
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def upper_limit(n: int, b: float, cl: float = 0.95) -> dict:
    """Classical one-sided upper limit on the signal mean s: P(N <= n | s + b) = 1 - cl."""
    n, b, cl = _count(n), _mean(b, "b"), _cl(cl)
    alpha = 1.0 - cl
    total = _solve(lambda mu: poisson_cdf(n, mu) - alpha, 0.0, MAX_MEAN)  # limit on s + b
    s_ul = total - b
    out = {"label": LABEL, "method": "classical Poisson upper limit, known background", "n_obs": n, "b": b, "cl": cl,
           "upper_limit_on_total_mean": total, "upper_limit_on_signal": s_ul}
    if s_ul <= 0:
        out["upper_limit_on_signal"] = None
        out["warning"] = ("classical limit is <= 0: fewer events than the background expects; the construction is "
                          "unphysical here (a negative or empty limit is not a result). Use Feldman-Cousins or CLs "
                          "with toys and report the expected sensitivity")
    if n == 0 and b == 0:
        out["check_minus_ln_alpha"] = -math.log(alpha)
    return out


def central_interval(n: int, cl: float = 0.6827) -> dict:
    """Garwood central interval on a Poisson mean (conservative: coverage >= cl)."""
    n, cl = _count(n), _cl(cl)
    tail = (1.0 - cl) / 2.0
    lower = 0.0
    if n > 0:  # P(N >= n | mu) increases with mu; find mu with P(N >= n | mu) = tail
        lo, hi = 0.0, MAX_MEAN
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if 1.0 - poisson_cdf(n - 1, mid) < tail:
                lo = mid
            else:
                hi = mid
        lower = 0.5 * (lo + hi)
    upper = _solve(lambda mu: poisson_cdf(n, mu) - tail, 0.0, MAX_MEAN)
    return {"label": LABEL, "method": "Garwood central interval (conservative)", "n_obs": n, "cl": cl,
            "lower": lower, "upper": upper}


def _pmf(n: int, mu: float) -> float:
    if mu == 0.0:
        return 1.0 if n == 0 else 0.0
    return math.exp(n * math.log(mu) - mu - math.lgamma(n + 1))


def _fc_range(s: float, b: float, cl: float) -> tuple[int, int]:
    """Feldman-Cousins acceptance region [n1, n2] for signal mean s and known background b.

    The likelihood ratio P(n | s + b) / P(n | best) is unimodal in n, so the region is contiguous: grow it from the
    mode, always adding the neighbor with the larger ratio (the larger n on a tie), until it holds at least cl.
    """
    mu = s + b
    n_max = int(mu + 10 * math.sqrt(mu + 1.0) + 20)
    p = [math.exp(-mu)] + [0.0] * n_max
    for n in range(1, n_max + 1):
        p[n] = p[n - 1] * mu / n

    def ratio(n: int) -> float:
        best = max(float(n), b)  # best-fit total mean for this n, with s >= 0
        if mu == 0.0 or best == 0.0:
            return math.exp(-mu) if n == 0 else 0.0
        return math.exp(n * math.log(mu / best) - mu + best)

    lo = hi = max(range(n_max + 1), key=ratio)
    total = p[lo]
    while total < cl:
        left = ratio(lo - 1) if lo > 0 else -1.0
        right = ratio(hi + 1) if hi < n_max else -1.0
        if left < 0 and right < 0:
            break
        if right >= left:
            hi += 1
            total += p[hi]
        else:
            lo -= 1
            total += p[lo]
    return lo, hi


def _fc_accepts(n_obs: int, s: float, b: float, cl: float) -> bool:
    """True if n_obs is in the Feldman-Cousins acceptance region for signal mean s."""
    lo, hi = _fc_range(s, b, cl)
    return lo <= n_obs <= hi


def _fc_s_max(n: int) -> float:
    return max(n, 1) + 10.0 * math.sqrt(max(n, 1)) + 10.0


def _fc_upper_plain(n: int, b: float, cl: float, step: float) -> float | None:
    """Top-most accepted signal value on the grid (the upper end of the plain construction)."""
    k, stride = int(_fc_s_max(n) / step), max(1, int(0.25 / step))
    while k - stride > 0 and _fc_range((k - stride) * step, b, cl)[0] > n + 2:  # far above the belt: skip ahead
        k -= stride
    while k >= 0:
        if _fc_accepts(n, k * step, b, cl):
            return k * step
        k -= 1
    return None


FC_MONOTONE_WINDOW = 6.0  # b' searched in [b, b + 6]; covers every published 90%/95% entry with n0 <= 20, b <= 15
FC_MONOTONE_COARSE = 0.05


def _fc_upper_monotone(n: int, b: float, cl: float, step: float) -> tuple[float, float]:
    """Upper end forced non-increasing in b: the supremum of the plain upper end over b' in [b, b + window].

    Feldman and Cousins (1998), Sec. IV.B: "we force the function to be non-increasing, by lengthening selected
    confidence intervals as necessary". Between its jumps the plain upper end falls with b' at a slope no steeper
    than -1, so a coarse scan bounds any jump inside a coarse cell by the cell's right end plus the cell width; only
    cells that could beat the running maximum are rescanned at the signal grid step, and each jump found there is
    located by bisection so the value just after it is not missed. Returns (upper, b_at_maximum).
    """
    best = _fc_upper_plain(n, b, cl, step)
    if best is None:
        raise DiagnosticsError("no signal value in the scan range accepts this n; check inputs")
    arg, width = b, FC_MONOTONE_COARSE
    coarse = [(b, best)]
    for j in range(1, int(round(FC_MONOTONE_WINDOW / width)) + 1):
        coarse.append((b + j * width, _fc_upper_plain(n, b + j * width, cl, step)))
        if coarse[-1][1] is not None and coarse[-1][1] > best:
            best, arg = coarse[-1][1], coarse[-1][0]
    fine = max(1, int(round(width / step)))
    for (b_left, prev), (b_right, v) in zip(coarse, coarse[1:]):
        if v is None or v + width < best:
            continue
        for i in range(1, fine + 1):
            bi = b_right if i == fine else b_left + i * width / fine
            u = v if i == fine else _fc_upper_plain(n, bi, cl, step)
            top, at = u, bi
            if u is not None and prev is not None and u > prev:  # a jump inside this fine cell: bisect to its edge
                left, right = bi - width / fine, bi
                for _ in range(12):
                    mid = 0.5 * (left + right)
                    um = _fc_upper_plain(n, mid, cl, step)
                    if um is not None and um >= top:
                        right, top, at = mid, um, mid
                    else:
                        left = mid
            if top is not None and top > best:
                best, arg = top, at
            prev = u
    if arg > b:  # a new top segment starts narrower than the signal grid: look just before the jump on finer grids
        fine_s = step / 5.0
        for i in range(40):
            bi = arg - i * 0.0005
            if bi <= b:
                break
            for j in range(5, 0, -1):
                if _fc_accepts(n, best + j * fine_s, bi, cl):
                    best = best + j * fine_s
                    break
    return best, arg


def fc_interval(n: int, b: float, cl: float = 0.90, step: float | None = None, sigma_b: float = 0.0,
                nodes: int = 40, monotone: bool = True) -> dict:
    """Feldman-Cousins interval on s >= 0 for n observed events, known background b (grid scan).

    By default the upper end is made non-increasing in b as in Feldman and Cousins (1998), which reproduces their
    published tables; monotone=False gives the plain construction at this b alone (its upper end can dip, for example
    1.08 instead of the published 1.26 at n = 0, b = 2, 90% CL).
    """
    n, b, cl = _count(n), _mean(b, "b"), _cl(cl)
    step = (0.005 if not sigma_b else 0.02) if step is None else step
    if isinstance(step, bool) or not isinstance(step, (int, float)) or not 0 < step <= 0.1:
        raise DiagnosticsError("step must lie in (0, 0.1]")
    if sigma_b:
        iv = _fc_marginal(n, b, sigma_b, cl, step, nodes)
        return {"label": LABEL, "method": ("Feldman-Cousins interval on s >= 0 with the background marginalized "
                                           "over a truncated normal prior (Cousins-Highland), grid scan"),
                "n_obs": n, "b": b, "sigma_b": sigma_b, "cl": cl, "grid_step": step, "lower": iv["lower"],
                "upper": iv["upper"], "lower_is_zero": iv["lower"] == 0.0,
                "construction": "plain (the monotonicity adjustment in b is not applied to the marginalized belt)",
                "note": ("approximation: coverage is not guaranteed for the true background value, only on average "
                         "over the prior, and is not a profile-likelihood result; accuracy is about one grid step; "
                         "compare with sigma_b = 0 and with a larger sigma_b to see the sensitivity")}
    if not isinstance(monotone, bool):
        raise DiagnosticsError("monotone must be true or false")
    top = int(_fc_s_max(n) / step)
    lo = next((k * step for k in range(top + 1) if _fc_accepts(n, k * step, b, cl)), None)
    plain = _fc_upper_plain(n, b, cl, step)
    if lo is None or plain is None:
        raise DiagnosticsError("no signal value in the scan range accepts this n; check inputs")
    out = {"label": LABEL, "method": "Feldman-Cousins interval on s >= 0, known background, grid scan", "n_obs": n,
           "b": b, "cl": cl, "grid_step": step, "lower": lo}
    if monotone:
        hi, b_at = _fc_upper_monotone(n, b, cl, step)
        out.update({"upper": hi, "construction": "monotone-in-b (Feldman-Cousins 1998, Sec. IV.B)",
                    "upper_plain": plain, "upper_lengthened": hi > plain,
                    "monotonicity_search": {"b_range": [b, b + FC_MONOTONE_WINDOW], "coarse_step": FC_MONOTONE_COARSE,
                                            "upper_attained_at_b": b_at}})
    else:
        out.update({"upper": plain, "construction": "plain (no monotonicity adjustment; can differ from the "
                                                    "published tables)"})
    out["lower_is_zero"] = lo == 0.0
    out["note"] = ("accuracy is about one grid step; the construction is slightly conservative for discrete counts, "
                   "and the monotone construction lengthens some upper ends further; the background is treated as "
                   "exactly known, so an uncertain background needs a profile-likelihood or toy construction; a lower "
                   "limit of 0 is the expected unified-interval behavior, not a failure; this is not CLs and gives no "
                   "expected sensitivity")
    return out


def _b_nodes(b: float, sigma_b: float, nodes: int) -> list[float]:
    """Equal-probability quantile nodes of Normal(b, sigma_b) truncated at 0 (deterministic)."""
    if isinstance(sigma_b, bool) or not isinstance(sigma_b, (int, float)) or not math.isfinite(sigma_b) or sigma_b < 0:
        raise DiagnosticsError(f"sigma_b must be a finite non-negative number, got {sigma_b!r}")
    if sigma_b == 0.0:
        return [b]
    if isinstance(nodes, bool) or not isinstance(nodes, int) or not 5 <= nodes <= 400:
        raise DiagnosticsError("nodes must be an integer in [5, 400]")
    dist = NormalDist(b, sigma_b)
    lo = dist.cdf(0.0)
    out = [dist.inv_cdf(lo + (1.0 - lo) * (k + 0.5) / nodes) for k in range(nodes)]
    if max(out) > MAX_MEAN - 50.0:
        raise DiagnosticsError("background prior reaches too high a mean for this script")
    return out


def _marg_cdf(n: int, mu_shift: float, nodes: list[float]) -> float:
    return sum(poisson_cdf(n, mu_shift + bk) for bk in nodes) / len(nodes)


def _marg_pmf(n: int, mu_shift: float, nodes: list[float]) -> float:
    return sum(_pmf(n, mu_shift + bk) for bk in nodes) / len(nodes)


def _fc_marginal(n: int, b: float, sigma_b: float, cl: float, step: float, nodes: int) -> dict:
    bk = _b_nodes(b, sigma_b, nodes)
    s_max = max(n, 1) + 10.0 * math.sqrt(max(n, 1)) + 10.0 + 3.0 * sigma_b
    n_cap = int(s_max + max(bk) + 10 * math.sqrt(s_max + max(bk) + 1.0) + 20)
    best = []  # best marginal probability of each count over s >= 0 (independent of the s being tested)
    for m in range(n_cap + 1):
        grid = [s_max * i / 200.0 for i in range(201)]
        i0 = max(range(201), key=lambda i: _marg_pmf(m, grid[i], bk))
        lo, hi = grid[max(i0 - 1, 0)], grid[min(i0 + 1, 200)]
        for _ in range(40):  # golden-section refinement of a unimodal marginal likelihood
            m1, m2 = lo + (hi - lo) * 0.382, lo + (hi - lo) * 0.618
            if _marg_pmf(m, m1, bk) < _marg_pmf(m, m2, bk):
                lo = m1
            else:
                hi = m2
        best.append(max(_marg_pmf(m, 0.5 * (lo + hi), bk), _marg_pmf(m, grid[i0], bk)))
    accepted = []
    for k in range(int(s_max / step) + 1):
        s = k * step
        ranked = sorted(((_marg_pmf(m, s, bk) / best[m], m) for m in range(n_cap + 1)), reverse=True)
        total = 0.0
        for _, m in ranked:
            total += _marg_pmf(m, s, bk)
            if m == n:
                accepted.append(s)
                break
            if total >= cl:
                break
    if not accepted:
        raise DiagnosticsError("no signal value in the scan range accepts this n; check inputs")
    return {"lower": accepted[0], "upper": accepted[-1]}


def cls_limit(n: int, b: float, cl: float = 0.95, sigma_b: float = 0.0, nodes: int = 40) -> dict:
    """CLs upper limit on s (CLs = CLs+b / CLb): observed, and median and 1/2-sigma expected under b only."""
    n, b, cl = _count(n), _mean(b, "b"), _cl(cl)
    bk = _b_nodes(b, sigma_b, nodes)
    alpha, hi = 1.0 - cl, MAX_MEAN - max(bk)

    def limit(m: int) -> float:
        clb = _marg_cdf(m, 0.0, bk)
        return _solve(lambda s: _marg_cdf(m, s, bk) / clb - alpha, 0.0, hi)

    n_cap = int(b + 5.0 * sigma_b + 10.0 * math.sqrt(b + 1.0) + 20)
    weights = [_marg_pmf(m, 0.0, bk) for m in range(n_cap + 1)]
    cum, expected, targets = 0.0, {}, [("-2sigma", 0.025), ("-1sigma", 0.16), ("median", 0.5),
                                       ("+1sigma", 0.84), ("+2sigma", 0.975)]
    cache = {}
    for m, w in enumerate(weights):
        cum += w
        for name, q in targets:
            if name not in expected and cum >= q:
                cache.setdefault(m, limit(m))
                expected[name] = cache[m]
    return {"label": LABEL, "method": ("CLs upper limit on s, counting experiment" +
                                       ("; background uncertainty by Cousins-Highland marginalization" if sigma_b else
                                        ", known background")),
            "n_obs": n, "b": b, "sigma_b": sigma_b, "cl": cl,
            "observed_upper_limit": limit(n), "expected_under_background_only": expected,
            "note": ("CLs is conservative by construction (it over-covers) and is not a frequentist interval; "
                     "the expected band is the quantile of the limit over background-only counts, not a coverage "
                     "claim; with sigma_b the background is a prior-predictive average, so check the dependence on "
                     "sigma_b and use toys or a profile construction for a final result")}


def _draw(rng: random.Random, mu: float) -> int:
    """Poisson variate by inversion of the CDF (exact for mu <= MAX_MEAN)."""
    u, k = rng.random(), 0
    term = total = math.exp(-mu)
    while u > total and k < 10 * int(mu + 10):
        k += 1
        term *= mu / k
        total += term
    return k


def coverage(mu: float, cl: float, toys: int, seed: int) -> dict:
    """Fraction of seeded pseudo-experiments whose Garwood interval contains the true mean mu."""
    mu, cl = _mean(mu, "mu", allow_zero=False), _cl(cl)
    if isinstance(toys, bool) or not isinstance(toys, int) or toys < 100:
        raise DiagnosticsError("toys must be an integer >= 100")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise DiagnosticsError("seed must be an integer and must be recorded")
    rng, cache, hits = random.Random(seed), {}, 0
    for _ in range(toys):
        n = _draw(rng, mu)
        if n not in cache:
            iv = central_interval(n, cl)
            cache[n] = (iv["lower"], iv["upper"])
        lo, hi = cache[n]
        hits += lo <= mu <= hi
    frac = hits / toys
    return {"label": LABEL, "method": "seeded toy coverage of the Garwood interval", "true_mean": mu, "cl": cl,
            "toys": toys, "seed": seed, "coverage": frac,
            "binomial_error_on_coverage": math.sqrt(max(frac * (1 - frac), 0.0) / toys),
            "note": "coverage at a single true mean; scan mu, coverage oscillates for discrete counts"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    u = sub.add_parser("upper-limit", help="classical upper limit on a signal mean")
    u.add_argument("--n", type=int, required=True)
    u.add_argument("--b", type=float, required=True, help="known background mean (0 if none)")
    u.add_argument("--cl", type=float, default=0.95)
    i = sub.add_parser("interval", help="Garwood central interval on a Poisson mean")
    i.add_argument("--n", type=int, required=True)
    i.add_argument("--cl", type=float, default=0.6827)
    f = sub.add_parser("fc-interval", help="Feldman-Cousins interval, known background")
    f.add_argument("--n", type=int, required=True)
    f.add_argument("--b", type=float, required=True, help="known background mean (0 if none)")
    f.add_argument("--cl", type=float, default=0.90)
    f.add_argument("--step", type=float, default=None, help="signal grid step (default 0.005, or 0.02 with --sigma-b)")
    f.add_argument("--sigma-b", type=float, default=0.0, help="background uncertainty (Cousins-Highland marginalization)")
    f.add_argument("--nodes", type=int, default=40, help="prior quantile nodes used with --sigma-b")
    f.add_argument("--plain-construction", action="store_true",
                   help="skip the monotonicity adjustment in b (the published tables use it)")
    k = sub.add_parser("cls-limit", help="CLs upper limit with expected band")
    k.add_argument("--n", type=int, required=True)
    k.add_argument("--b", type=float, required=True, help="background mean (0 if none)")
    k.add_argument("--cl", type=float, default=0.95)
    k.add_argument("--sigma-b", type=float, default=0.0, help="background uncertainty (Cousins-Highland marginalization)")
    k.add_argument("--nodes", type=int, default=40)
    c = sub.add_parser("coverage", help="seeded toy coverage of the interval")
    c.add_argument("--mu", type=float, required=True)
    c.add_argument("--cl", type=float, default=0.6827)
    c.add_argument("--toys", type=int, default=20000)
    c.add_argument("--seed", type=int, required=True, help="required: every toy study records its seed")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "upper-limit":
            result = upper_limit(args.n, args.b, args.cl)
        elif args.command == "fc-interval":
            result = fc_interval(args.n, args.b, args.cl, args.step, args.sigma_b, args.nodes,
                                 not args.plain_construction)
        elif args.command == "cls-limit":
            result = cls_limit(args.n, args.b, args.cl, args.sigma_b, args.nodes)
        elif args.command == "interval":
            result = central_interval(args.n, args.cl)
        else:
            result = coverage(args.mu, args.cl, args.toys, args.seed)
    except DiagnosticsError as exc:
        print(json.dumps({"label": LABEL, "status": "rejected", "error": str(exc)}, indent=2))
        return 2
    result["status"] = "ok"
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
