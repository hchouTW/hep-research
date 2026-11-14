"""Contribution decomposition of Part B section 10.5 (calib_contrib.py; phase 4).

A quantity Q of one observable at a parameter point (theta-hat) is split into one term per effect. Each effect is
declared in the contract (`effects`: [{name, removal: {parameter: value after removal}}]) and removed through the
evaluator's `effects_off` (section 7.1). Q(S) is the evaluation with the effects of S present and all others removed;
the total is Q(all present) - Q(none present). The term of effect i is its Shapley value, the mean over orderings of
Q(prefix + i) - Q(prefix); on every ordering these differences sum to the total (telescoping), so the terms sum to the
total by construction.

- n <= 10 effects: all 2^n subsets are evaluated and the terms are exact Shapley sums;
- n > 10: orderings are sampled (uniform permutations, a fixed seed); each term is the mean over the sampled
  orderings and its sampling error (and the sampling covariance between terms) is reported;
- every subset actually evaluated must pass the ESS threshold of G4 (N_eff,k >= N_req,k, section 6.7, the
  implementation of calib_reweight: design.g4_inputs_from and reweight.g4); events not recorded at a reweighted node
  (missing support) fail it too. If any one fails, no decomposition is output: status `failed`, finding `contrib.ess`
  and the failing subsets;
- the covariances between the terms come from an event bootstrap: one multinomial resampling of each run's events,
  shared by every subset (common random numbers pair the events), applied at first order through the evaluator's
  per-event influence values (section 7.1 `influence`); an evaluator without them leaves the item `incomplete`;
- the object of the decomposition (`variance`: Q = value^2; `resolution`: Q = value) is a required input and is
  stated in the output.

Forced joint fits (A21, section 19-g8): the decomposition evaluates the simulator at fixed parameter points and
combines no propagation packages, so the conflict rules of section 10.4 never force a joint fit here; the output says
so (`forced_joint_fits`: [])."""
from __future__ import annotations

import math

import numpy as np

from core.calibration import design, evaluator as E, linear, reweight

EXHAUSTIVE_MAX = 10                      # section 10.5: all 2^n subsets when n <= 10
OBJECTS = ("variance", "resolution")
BOOTSTRAP_DEFAULT = 500
PERMUTATIONS_DEFAULT = 200
SEED_DEFAULT = 20261113


class ContribError(ValueError):
    """Bad input (exit 2) or, with status incomplete, an evaluator that cannot remove effects (exit 3)."""

    def __init__(self, code: str, message: str, status: str = "rejected"):
        super().__init__(message)
        self.code, self.status = code, status


def declared_effects(contract: dict, select=None) -> dict:
    """{effect: {parameter: value after removal}} from the contract's `effects` (section 7.1, 10.5), optionally
    restricted to `select` (names). Every effect names contract parameters with numeric values."""
    decl = contract.get("effects") or []
    params = {p.get("name") for p in contract.get("parameters", [])}
    out: dict = {}
    for e in decl:
        name, removal = e.get("name"), e.get("removal")
        if not name or not isinstance(removal, dict) or not removal:
            raise ContribError("contrib.declaration", f"effect {name!r}: a name and its value after removal "
                               "({parameter: value}) are required (section 10.5)")
        if name in out:
            raise ContribError("contrib.declaration", f"effect {name!r} is declared twice")
        unknown = sorted(set(removal) - params)
        if unknown:
            raise ContribError("contrib.declaration", f"effect {name!r} removes {unknown}, not contract parameters")
        out[name] = dict(removal)
    if select is not None:
        missing = sorted(set(select) - set(out))
        if missing:
            raise ContribError("contrib.declaration", f"effects {missing} are not declared in the contract")
        out = {k: out[k] for k in select}
    if not out:
        raise ContribError("contrib.declaration", "no effects declared (contract `effects`)")
    try:
        E.removal_values(out)                                # conflicting values after removal are rejected
    except ValueError as exc:
        raise ContribError("contrib.declaration", str(exc)) from None
    return out


class _Subsets:
    """Q(S) for subsets S (bit masks over the effects, bit set = effect present), cached, with its ESS record and its
    bootstrap replicas (one multinomial draw per run, shared by all subsets)."""

    def __init__(self, ev, contract, theta, observable, quantity, effects, f, B, seed) -> None:
        self.ev, self.contract, self.theta, self.observable, self.quantity = ev, contract, theta, observable, quantity
        self.names = list(effects)
        self.effects = effects
        self.f, self.B = f, B
        self.rng = np.random.default_rng(seed)
        self.draws: dict = {}
        self.cache: dict = {}

    def _counts(self, run, n):
        if run not in self.draws:
            self.draws[run] = self.rng.multinomial(n, np.full(n, 1.0 / n), size=self.B).astype(float) - 1.0
        if self.draws[run].shape[1] != n:
            raise ContribError("contrib.pairing", f"run {run}: the number of events changed between subsets",
                               "incomplete")
        return self.draws[run]

    def _q(self, v):
        return v * v if self.quantity == "variance" else v

    def get(self, mask: int) -> dict:
        if mask in self.cache:
            return self.cache[mask]
        off = {e: self.effects[e] for i, e in enumerate(self.names) if not mask >> i & 1}
        try:
            r = self.ev.evaluate(dict(self.theta), effects_off=off, names=[self.observable])
        except (ValueError, NotImplementedError, LookupError) as exc:
            raise ContribError("contrib.effects_off", f"the evaluator cannot remove {sorted(off)}: {exc}",
                               "incomplete") from None
        if list(r.get("names", [])) != [self.observable]:
            raise ContribError("contrib.observable", f"the evaluator has no observable {self.observable!r}")
        w, n_req, missing = design.g4_inputs_from(r, self.contract, self.f)
        g = reweight.g4(w, n_req)
        row = g["observables"][0]
        ess_ok = row["n_eff"] >= row["n_req"] and not missing
        infl = r.get("influence")
        if not infl:
            raise ContribError("contrib.bootstrap", "the evaluator returns no per-event influence values: the "
                               "bootstrap covariances of section 10.5 cannot be formed", "incomplete")
        value = float(np.asarray(r["pred"], float)[0])
        rep = np.full(self.B, value)
        for run, cols in infl.items():
            if 0 in cols:
                col = np.asarray(cols[0][0], float)
                rep = rep + self._counts(run, col.size) @ col
        rec = {"mask": mask, "present": [e for i, e in enumerate(self.names) if mask >> i & 1],
               "value": value, "q": self._q(value), "q_boot": self._q(rep),
               "n_eff": float(row["n_eff"]), "n_req": float(row["n_req"]), "missing_support_runs": missing,
               "ess_passed": bool(ess_ok)}
        self.cache[mask] = rec
        return rec


def _shapley_weights(n: int) -> np.ndarray:
    return np.array([math.factorial(s) * math.factorial(n - s - 1) / math.factorial(n) for s in range(n)])


def _exhaustive(sub: _Subsets, n: int):
    full = (1 << n) - 1
    for mask in range(full + 1):
        sub.get(mask)
    wts = _shapley_weights(n)
    terms = np.zeros(n)
    boot = np.zeros((n, sub.B))
    for i in range(n):
        for mask in range(full + 1):
            if mask >> i & 1:
                continue
            a, b = sub.cache[mask | 1 << i], sub.cache[mask]
            wt = wts[bin(mask).count("1")]
            terms[i] += wt * (a["q"] - b["q"])
            boot[i] += wt * (a["q_boot"] - b["q_boot"])
    return terms, boot, None


def _sampled(sub: _Subsets, n: int, m: int, seed: int):
    rng = np.random.default_rng(seed)
    contrib = np.zeros((m, n))
    boot = np.zeros((n, sub.B))
    for k in range(m):
        perm = rng.permutation(n)
        mask = 0
        prev = sub.get(mask)
        for i in perm:
            mask |= 1 << int(i)
            cur = sub.get(mask)
            contrib[k, i] = cur["q"] - prev["q"]
            boot[i] += cur["q_boot"] - prev["q_boot"]
            prev = cur
    terms = contrib.mean(axis=0)
    samp_cov = np.cov(contrib, rowvar=False, ddof=1) / m if m > 1 else np.full((n, n), np.nan)
    return terms, boot / m, samp_cov


def permutation_sums(subset_q: dict, names: list, orders) -> list[float]:
    """For each ordering (a sequence of effect names), the sum of the sequential differences Q(prefix + i) - Q(prefix)
    over the subset values {frozenset(present): Q}: equal to the total on every ordering (section 10.5)."""
    out = []
    for order in orders:
        present: set = set()
        s = 0.0
        for e in order:
            before = subset_q[frozenset(present)]
            present.add(e)
            s += subset_q[frozenset(present)] - before
        out.append(s)
    return out


def decompose(ev, contract: dict, theta: dict, observable: str, quantity: str | None, select=None, *,
              f: float = design.F_DEFAULT, bootstrap: int = BOOTSTRAP_DEFAULT, bootstrap_seed: int = SEED_DEFAULT,
              permutations: int = PERMUTATIONS_DEFAULT, permutation_seed: int = SEED_DEFAULT,
              exhaustive_max: int = EXHAUSTIVE_MAX) -> dict:
    """The section 10.5 decomposition of `observable` at `theta` over the declared effects (or `select`).
    quantity: `variance` or `resolution` (required). Returns status ok with the terms, or failed (`contrib.ess`) with the
    failing subsets and no terms. Raises ContribError for bad input or an evaluator that cannot remove effects."""
    if quantity not in OBJECTS:
        raise ContribError("contrib.object", "state whether the object of the decomposition is the variance or the "
                           "resolution itself (section 10.5): object = variance | resolution")
    if bootstrap < 2:
        raise ContribError("contrib.bootstrap", "at least two bootstrap replicas")
    if not any(o.get("name") == observable for o in contract.get("observables", [])):
        raise ContribError("contrib.observable", f"observable {observable!r} is not declared in the contract")
    effects = declared_effects(contract, select)
    names = list(effects)
    n = len(names)
    sub = _Subsets(ev, contract, theta, observable, quantity, effects, f, int(bootstrap), bootstrap_seed)
    try:
        if n <= exhaustive_max:
            method = "exhaustive"
            terms, boot, samp_cov = _exhaustive(sub, n)
        else:
            if permutations < 2:
                raise ContribError("contrib.permutations", "at least two sampled orderings")
            method = "permutation-sampling"
            terms, boot, samp_cov = _sampled(sub, n, int(permutations), permutation_seed)
    except linear.DesignError as exc:
        raise ContribError("contrib.exposure", str(exc)) from None
    subsets = [{k: rec[k] for k in ("present", "value", "q", "n_eff", "n_req", "missing_support_runs",
                                    "ess_passed")} for _, rec in sorted(sub.cache.items())]
    base = {"object": quantity, "observable": observable, "effects": effects, "method": method,
            "n_effects": n, "n_subsets_evaluated": len(subsets), "f": f,
            "forced_joint_fits": [], "forced_joint_fits_note": "none: the decomposition evaluates the simulator at "
            "fixed parameter points and combines no propagation packages (section 10.4, A21 section 19-g8)"}
    bad = [s for s in subsets if not s["ess_passed"]]
    if bad:                                                  # no values either: they would rebuild the terms
        ess = [{k: v for k, v in s.items() if k not in ("value", "q")} for s in subsets]
        return {"status": "failed", "finding": "contrib.ess", **base, "decomposition": None,
                "failing_subsets": [s for s in ess if not s["ess_passed"]], "subsets": ess,
                "reason": f"{len(bad)} evaluated subset(s) below the ESS threshold of G4 (N_eff < N_req or missing "
                          "support): no decomposition is output (section 10.5)"}
    full, none = sub.cache[(1 << n) - 1], sub.cache[0]
    total = full["q"] - none["q"]
    cov = np.cov(boot, ddof=1) if n > 1 else np.array([[float(np.var(boot[0], ddof=1))]])
    out = {"status": "ok", **base, "total": total, "q_all_present": full["q"], "q_all_removed": none["q"],
           "terms": dict(zip(names, terms.tolist())), "sum_of_terms": float(terms.sum()),
           "efficiency_residual": float(terms.sum() - total),
           "covariance": {"order": names, "matrix": np.atleast_2d(cov).tolist(), "method": "event bootstrap, "
                          f"B = {int(bootstrap)}, first order through the per-event influence values"},
           "total_sd": float(np.std(full["q_boot"] - none["q_boot"], ddof=1)), "subsets": subsets}
    if samp_cov is not None:
        out["sampling_error"] = dict(zip(names, np.sqrt(np.clip(np.diag(samp_cov), 0, None)).tolist()))
        out["sampling_covariance"] = {"order": names, "matrix": samp_cov.tolist(),
                                      "orderings": int(permutations), "seed": permutation_seed}
    return out

