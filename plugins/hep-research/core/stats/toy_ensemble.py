#!/usr/bin/env python3
"""Toy ensembles with an explicit generation policy, reproducible partitions and complete failure accounting.

A toy study is defined by what it generates from, not only by its seed. EnsembleSpec makes the choice explicit
(no default) among:

  conditional-fluctuated-aux  nuisances at their conditional best fit on the observed data at the tested parameter;
                              auxiliary measurements redrawn around them (the profile construction used by the LHC
                              experiments; Cowan et al. 2011);
  conditional-fixed-aux       nuisances at the conditional best fit; auxiliary measurements fixed at their observed
                              values;
  unconditional-prior         nuisances drawn from their constraint terms read as priors (a prior-predictive,
                              hybrid ensemble; its coverage is an average over the prior, not at a true nuisance);
  plug-in                     nuisances fixed at a supplied point (for example the true point of a coverage study).

Results of different ensembles are labeled with the ensemble and are never pooled: a coverage claim made with one
does not carry over to another.

Seeds: toy i of a study with seed S uses toy_seed(S, i), a SHA-256 derivation of (S, i); the task that runs it
(task_id of n_tasks, contiguous disjoint index ranges from partition()) does not change its data, so a partitioned
run merges to exactly the single-task run, and merge() refuses duplicate or missing indices.

Every generated toy has exactly one outcome: ok, fit_failed, invalid_data, empty_data, timeout or error (counts
always sum to the toys generated). coverage() reports, for a predeclared failure policy, the coverage counting
failures as not covering (C/N), as covering ((C+F)/N) and among successes only (C/(N-F)), each with its exact
binomial interval; the headline follows the policy, so dropping failures can never improve it. There is no retry: a
failed toy stays failed (automatic retries are disabled; the maximum attempt count is 0).
Standard library only.
"""
from __future__ import annotations

import hashlib
import math
import random
import time
from collections import Counter
from dataclasses import dataclass, field

from core.stats.tail_estimation import clopper_pearson

ENSEMBLES = ("conditional-fluctuated-aux", "conditional-fixed-aux", "unconditional-prior", "plug-in")
OUTCOMES = ("ok", "fit_failed", "invalid_data", "empty_data", "timeout", "error")
FAILURE_POLICIES = ("count-as-noncovering", "count-as-covering", "report-bounds")


class EnsembleError(ValueError):
    """Raised for an invalid ensemble specification, an inconsistent merge or pooling across ensembles."""


class ToyFailure(Exception):
    """Raised by a generator or evaluator to classify a toy: outcome is one of OUTCOMES other than ok."""

    def __init__(self, outcome: str, message: str = "") -> None:
        if outcome not in OUTCOMES or outcome == "ok":
            raise EnsembleError(f"unknown failure outcome {outcome!r}")
        super().__init__(message or outcome)
        self.outcome = outcome


def toy_seed(seed: int, index: int) -> int:
    """63-bit seed of toy `index` in a study with seed `seed` (independent of how the study is partitioned)."""
    return int.from_bytes(hashlib.sha256(f"hep-research-toy:{seed}:{index}".encode()).digest()[:8], "big") >> 1


def partition(n_toys: int, n_tasks: int) -> list[tuple[int, int]]:
    """Contiguous, disjoint [start, stop) index ranges covering range(n_toys), one per task (sizes differ by <= 1)."""
    if isinstance(n_toys, bool) or not isinstance(n_toys, int) or n_toys < 1:
        raise EnsembleError("n_toys must be a positive integer")
    if isinstance(n_tasks, bool) or not isinstance(n_tasks, int) or not 1 <= n_tasks <= n_toys:
        raise EnsembleError("n_tasks must be an integer in [1, n_toys]")
    q, r = divmod(n_toys, n_tasks)
    out, start = [], 0
    for t in range(n_tasks):
        stop = start + q + (1 if t < r else 0)
        out.append((start, stop))
        start = stop
    return out


@dataclass
class EnsembleSpec:
    kind: str
    seed: int
    n_toys: int
    task_id: int = 0
    n_tasks: int = 1
    failure_policy: str = "count-as-noncovering"
    timeout_s: float | None = None            # a toy that takes longer is classified timeout (not interrupted)
    max_attempts: int = 0                      # retries are disabled; any other value is refused
    notes: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in ENSEMBLES:
            raise EnsembleError(f"ensemble kind must be one of {ENSEMBLES} (no default), got {self.kind!r}")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise EnsembleError("seed must be an integer")
        if self.failure_policy not in FAILURE_POLICIES:
            raise EnsembleError(f"failure_policy must be one of {FAILURE_POLICIES}")
        if self.max_attempts != 0:
            raise EnsembleError("automatic retries are not configured: max_attempts must be 0")
        parts = partition(self.n_toys, self.n_tasks)
        if not 0 <= self.task_id < self.n_tasks:
            raise EnsembleError("task_id must lie in [0, n_tasks)")
        self.indices = range(*parts[self.task_id])

    def record(self) -> dict:
        return {"kind": self.kind, "seed": self.seed, "n_toys": self.n_toys, "task_id": self.task_id,
                "n_tasks": self.n_tasks, "indices": [self.indices.start, self.indices.stop],
                "seed_derivation": "sha256('hep-research-toy:<seed>:<index>')[:8] >> 1",
                "failure_policy": self.failure_policy, "timeout_s": self.timeout_s, "max_attempts": self.max_attempts}


def run(spec: EnsembleSpec, generate, evaluate) -> dict:
    """Run this task's toys. generate(rng, index) returns toy data; evaluate(data, index) returns a value. Either may
    raise ToyFailure(outcome); any other exception is outcome error. Returns the spec record, outcome counts that sum
    to the toys generated, and one row (index, outcome, value) per toy."""
    rows = []
    for i in spec.indices:
        rng = random.Random(toy_seed(spec.seed, i))
        t0 = time.perf_counter()
        try:
            value = evaluate(generate(rng, i), i)
            outcome = "ok"
        except ToyFailure as exc:
            value, outcome = None, exc.outcome
        except Exception:  # noqa: BLE001  (recorded as an outcome, never hidden)
            value, outcome = None, "error"
        if outcome == "ok" and spec.timeout_s is not None and time.perf_counter() - t0 > spec.timeout_s:
            value, outcome = None, "timeout"
        rows.append((i, outcome, value))
    counts = Counter(o for _, o, _ in rows)
    outcomes = {o: counts.get(o, 0) for o in OUTCOMES}
    out = {"ensemble": spec.record(), "generated": len(rows), "outcomes": outcomes, "rows": rows}
    if sum(outcomes.values()) != len(rows):
        raise EnsembleError("outcome counts do not sum to the toys generated")
    return out


def merge(parts: list[dict]) -> dict:
    """Merge task results of one study: same ensemble kind, seed and n_toys; every index exactly once."""
    if not parts:
        raise EnsembleError("nothing to merge")
    keys = {(p["ensemble"]["kind"], p["ensemble"]["seed"], p["ensemble"]["n_toys"], p["ensemble"]["failure_policy"],
             p["ensemble"]["timeout_s"]) for p in parts}
    if len(keys) != 1:
        raise EnsembleError(f"cannot merge different studies or ensembles: {sorted(keys)}")
    rows = sorted((r for p in parts for r in p["rows"]), key=lambda r: r[0])
    idx = [r[0] for r in rows]
    n = parts[0]["ensemble"]["n_toys"]
    if len(set(idx)) != len(idx):
        raise EnsembleError("duplicate toy indices across tasks")
    if idx != list(range(n)):
        missing = sorted(set(range(n)) - set(idx))
        raise EnsembleError(f"missing toy indices: {missing[:10]}{' ...' if len(missing) > 10 else ''}")
    counts = Counter(o for _, o, _ in rows)
    ens = dict(parts[0]["ensemble"], task_id=None, n_tasks=len(parts), indices=[0, n])
    return {"ensemble": ens, "generated": n, "outcomes": {o: counts.get(o, 0) for o in OUTCOMES}, "rows": rows}


def coverage(result: dict, covered, nominal: float, interval_cl: float = 0.95) -> dict:
    """Coverage of a procedure from an ensemble result; covered(value) says whether one successful toy covered.

    Returns C (covered successes), F (failed toys, every outcome other than ok), N (generated), the three
    coverages C/N, (C+F)/N and C/(N-F) with exact intervals at interval_cl, and the headline chosen by the
    ensemble's failure policy: count-as-noncovering -> C/N; count-as-covering -> (C+F)/N; report-bounds -> the
    interval [C/N, (C+F)/N] with no single value. The ensemble kind travels with the result."""
    n = result["generated"]
    ok_values = [v for _, o, v in result["rows"] if o == "ok"]
    c = sum(1 for v in ok_values if covered(v))
    f = n - len(ok_values)
    policy = result["ensemble"]["failure_policy"]

    def est(k, m):
        return {"value": k / m, "k": k, "n": m, "interval": list(clopper_pearson(k, m, interval_cl))} if m else None
    out = {"ensemble": result["ensemble"]["kind"], "nominal": nominal, "generated": n, "covered": c, "failed": f,
           "outcomes": result["outcomes"], "failure_policy": policy, "interval_cl": interval_cl,
           "failures_as_noncovering": est(c, n), "failures_as_covering": est(c + f, n),
           "conditional_on_success": est(c, n - f),
           "standard_error_at_nominal": math.sqrt(nominal * (1 - nominal) / n)}
    if policy == "count-as-noncovering":
        out["headline"] = out["failures_as_noncovering"]
    elif policy == "count-as-covering":
        out["headline"] = out["failures_as_covering"]
    else:
        out["headline"] = {"bounds": [c / n, (c + f) / n]}
    return out


def coverage_gate(cov: dict, max_deficit: float = 0.01, n_tests: int = 1, gate_cl: float = 0.95) -> dict:
    """Undercoverage gate (audit T14), fixed before any result is seen: the procedure passes at this point when the
    one-sided lower confidence bound on the headline coverage (failures counted as not covering unless the policy
    says otherwise) is at least nominal - max_deficit. The bound uses confidence 1 - (1 - gate_cl) / n_tests
    (Bonferroni over the points of a grid). Overcoverage is not a failure. With report-bounds the lower bound of C/N
    is used."""
    from core.stats.tail_estimation import one_sided_lower, one_sided_upper
    h = cov["failures_as_covering"] if cov["failure_policy"] == "count-as-covering" else cov["failures_as_noncovering"]
    level = 1.0 - (1.0 - gate_cl) / n_tests
    lb, ub = one_sided_lower(h["k"], h["n"], level), one_sided_upper(h["k"], h["n"], level)
    threshold = cov["nominal"] - max_deficit
    verdict = "pass" if lb >= threshold else ("fail" if ub < threshold else "insufficient-precision")
    return {"pass": verdict == "pass", "verdict": verdict, "lower_bound": lb, "upper_bound": ub, "threshold": threshold,
            "bound_cl": level, "n_tests": n_tests, "max_deficit": max_deficit,
            "rule": ("pass: one-sided lower confidence bound on coverage >= nominal - max_deficit; fail: the upper bound "
                     "is below it; otherwise insufficient-precision (more toys needed, not a failure of the method); "
                     "Bonferroni over the grid")}
