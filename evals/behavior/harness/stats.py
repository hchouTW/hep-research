"""Statistics for behavioral evaluations. Standard library only.

An eval score is a measurement with an uncertainty. These functions give the intervals and tests the reports use:

  wilson            binomial proportion interval (all pass rates)
  pass_hat_k        P(all k repeats of a case pass), averaged over cases: reliability, not ability
  pass_at_k         P(at least one of k passes): ability ceiling
  mcnemar_exact     paired comparison of two variants on the same cases (discordant pairs only)
  cluster_bootstrap CI for a mean difference resampling cases (repeats within a case are correlated)
  cohen_kappa       judge-vs-human agreement (calibration)
  n_for_paired      cases needed to detect a change at given power (rough planning number)
  decompose         P(pass) = P(load) * P(pass | load) + P(no load) * P(pass | no load)
"""
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from statistics import NormalDist
from typing import Hashable, Iterable, Sequence

_N = NormalDist()


def wilson(k: int, n: int, cl: float = 0.95) -> tuple[float, float, float]:
    """(point, low, high). n = 0 gives (nan, 0, 1)."""
    if n == 0:
        return float("nan"), 0.0, 1.0
    z = _N.inv_cdf(0.5 + cl / 2)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def _comb(n: int, k: int) -> int:
    return math.comb(n, k) if 0 <= k <= n else 0


def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased estimate of P(at least one pass in k draws) from c passes in n repeats."""
    if n - c < k:
        return 1.0
    return 1.0 - _comb(n - c, k) / _comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """Unbiased estimate of P(all k draws pass) from c passes in n repeats."""
    if c < k:
        return 0.0
    return _comb(c, k) / _comb(n, k)


def per_case_reliability(outcomes: dict[Hashable, Sequence[bool]], k: int | None = None) -> dict:
    """outcomes: case -> list of pass/fail over repeats. k defaults to the smallest repeat count."""
    if not outcomes:
        return {"cases": 0}
    k = k or min(len(v) for v in outcomes.values())
    at = [pass_at_k(len(v), sum(v), k) for v in outcomes.values()]
    hat = [pass_hat_k(len(v), sum(v), k) for v in outcomes.values()]
    flaky = [c for c, v in outcomes.items() if 0 < sum(v) < len(v)]
    return {"cases": len(outcomes), "k": k, "pass_at_k": sum(at) / len(at), "pass_hat_k": sum(hat) / len(hat),
            "flaky_cases": sorted(map(str, flaky)), "flaky_fraction": len(flaky) / len(outcomes)}


def mcnemar_exact(pairs: Iterable[tuple[bool, bool]]) -> dict:
    """Two-sided exact McNemar test. pairs: (variant A passed, variant B passed) for the same case and repeat."""
    b = c = same = 0
    for a, bb in pairs:
        if a and not bb:
            b += 1
        elif bb and not a:
            c += 1
        else:
            same += 1
    n = b + c
    if n == 0:
        p = 1.0
    else:
        tail = sum(_comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
        p = min(1.0, 2 * tail)
    return {"a_only": b, "b_only": c, "concordant": same, "p_value": p,
            "direction": "B better" if c > b else ("A better" if b > c else "no change")}


def cluster_bootstrap(diffs_by_case: dict[Hashable, Sequence[float]], n_boot: int = 4000, cl: float = 0.95,
                      seed: int = 20261017) -> dict:
    """CI of the mean per-case difference (B - A), resampling cases with replacement."""
    rng = random.Random(seed)
    means = [sum(v) / len(v) for v in diffs_by_case.values() if v]
    if not means:
        return {"mean": float("nan"), "low": float("nan"), "high": float("nan"), "cases": 0}
    m = sum(means) / len(means)
    boots = []
    for _ in range(n_boot):
        s = [means[rng.randrange(len(means))] for _ in means]
        boots.append(sum(s) / len(s))
    boots.sort()
    lo = boots[int((1 - cl) / 2 * n_boot)]
    hi = boots[min(n_boot - 1, int((1 + cl) / 2 * n_boot))]
    return {"mean": m, "low": lo, "high": hi, "cases": len(means)}


def cohen_kappa(a: Sequence[Hashable], b: Sequence[Hashable]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("need two equal-length, non-empty label lists")
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def n_for_paired(p_discordant: float, effect: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Cases for a paired McNemar test to detect a pass-rate change `effect` when a fraction p_discordant of cases
    flips either way (Connor 1987 approximation). Planning number only."""
    za = _N.inv_cdf(1 - alpha / 2)
    zb = _N.inv_cdf(power)
    if effect <= 0 or p_discordant <= effect:
        raise ValueError("need 0 < effect < p_discordant")
    n = (za * math.sqrt(p_discordant) + zb * math.sqrt(p_discordant - effect ** 2)) ** 2 / effect ** 2
    return math.ceil(n)


def n_for_interval(p: float, half_width: float, cl: float = 0.95) -> int:
    """Independent runs for a normal-approximation interval of the given half width around p."""
    z = _N.inv_cdf(0.5 + cl / 2)
    return math.ceil(z * z * p * (1 - p) / half_width ** 2)


def decompose(rows: Iterable[dict]) -> dict:
    """rows: {"loaded": bool, "pass": bool}. The multiplicative view of the layers: how much of the failure rate is
    explained by not loading the skill at all."""
    cnt = defaultdict(lambda: [0, 0])
    for r in rows:
        cnt[bool(r["loaded"])][0] += 1
        cnt[bool(r["loaded"])][1] += bool(r["pass"])
    n = cnt[True][0] + cnt[False][0]
    if n == 0:
        return {"runs": 0}
    out = {"runs": n}
    out["p_load"] = wilson(cnt[True][0], n)
    out["p_pass_given_load"] = wilson(cnt[True][1], cnt[True][0])
    out["p_pass_given_no_load"] = wilson(cnt[False][1], cnt[False][0])
    out["p_pass"] = wilson(cnt[True][1] + cnt[False][1], n)
    pl, ppl = out["p_load"][0], out["p_pass_given_load"][0]
    if not math.isnan(ppl):
        out["p_pass_if_always_loaded"] = ppl
        out["failures_from_not_loading"] = (cnt[False][0] - cnt[False][1]) / max(1, n - cnt[True][1] - cnt[False][1])
    return out


def fmt_rate(t: tuple[float, float, float]) -> str:
    p, lo, hi = t
    if math.isnan(p):
        return "n/a"
    return f"{100 * p:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"
