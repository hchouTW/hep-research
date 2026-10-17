#!/usr/bin/env python3
"""Radioactive decay chains: amounts and activities over time, Bateman or matrix exponential (Th12).

Purpose: populations N_i(t) and activities A_i = lambda_i N_i of a decay chain from initial amounts and an optional
constant production, with every half-life traced to its source. See
<plugin root>/skills/hep-theory/references/nuclear-physics-essentials.md.

Method:
- lambda = ln 2 / T_1/2; a stable member has lambda = 0;
- linear chain without production and with distinct decay constants: the Bateman solution
  N_n(t) = sum_i N_i(0) (prod_{j=i}^{n-1} lambda_j) sum_{k=i}^{n} e^{-lambda_k t} / prod_{m=i, m!=k}^{n} (lambda_m - lambda_k);
- branches, production, or decay constants closer than a relative 1e-6: the matrix exponential of the augmented
  system dN/dt = M N + S (M_ii = -lambda_i, M_dp = f_pd lambda_p), which is exact for any graph of decays;
- half-lives from core/constants (NUBASE2020, ground states; year units with 1 y = 365.2422 d), with source and
  edition, unless given with --half-life NAME=VALUE:UNIT (s, m, h, d, y) or NAME=stable;
- the chain order is the decay order; each member decays to the next with fraction 1 unless --branch P:D:F sends a
  fraction F of P to D, the rest of P going to the next member.
Equilibrium labels per consecutive pair: secular (parent half-life above 100 times the daughter's), transient (longer
parent), none (shorter parent).
Assumptions and validity: ground-state decays; no neutron capture or other reactions; constant production into
declared members; decays leaving the listed chain are not followed.
Usage: decay_chain.py --chain N1 N2 ... --initial N=AMOUNT [...] --times T [T ...] --time-unit {s,d,y}
         [--production N=RATE_PER_S ...] [--half-life N=VALUE:UNIT|stable ...] [--branch P:D:F ...]
         [--method auto|bateman|matrix] [--status LABEL]
Output JSON: status, status_label, inputs, defaults_used, half_lives {name: seconds, source, edition}, method,
results [{time, amounts, activities_bq, activity_ratios}], equilibrium, warnings, label [General method].
Exit codes: 0 ok; 2 bad input; 3 NumPy or SciPy missing (needed for the matrix exponential).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core import constants  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LN2 = math.log(2.0)
LABEL = "[General method]"
UNIT_S = {"s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0, "y": 365.2422 * 86400.0}
NEAR = 1e-6


class ChainError(ValueError):
    """An input that does not define a decay chain."""


def bateman(lam: list[float], n0: list[float], t: float) -> list[float]:
    """Amounts of a linear chain at time t (distinct decay constants)."""
    out = []
    for n in range(len(lam)):
        total = 0.0
        for i in range(n + 1):
            if n0[i] == 0.0:
                continue
            pre = n0[i] * math.prod(lam[i:n])
            s = 0.0
            for k in range(i, n + 1):
                den = math.prod(lam[m] - lam[k] for m in range(i, n + 1) if m != k)
                s += math.exp(-lam[k] * t) / den
            total += pre * s
        out.append(total)
    return out


def matrix_solution(lam: list[float], edges: list[tuple[int, int, float]], n0: list[float], prod: list[float],
                    t: float) -> list[float]:
    import numpy as np
    from scipy.linalg import expm

    n = len(lam)
    M = np.zeros((n + 1, n + 1))
    for i, l in enumerate(lam):
        M[i, i] = -l
    for p, d, f in edges:
        M[d, p] += f * lam[p]
    M[:n, n] = prod
    v = expm(M * t) @ np.array(list(n0) + [1.0])
    return [float(x) for x in v[:n]]


def _linear(edges, n):
    return sorted(edges) == [(i, i + 1, 1.0) for i in range(n - 1)]


def solve(lam, edges, n0, prod, times, method="auto") -> dict:
    n = len(lam)
    near = any(abs(lam[i] - lam[j]) <= NEAR * max(lam[i], lam[j]) for i in range(n) for j in range(i) if lam[i] or lam[j])
    can_bateman = _linear(edges, n) and not any(prod) and not near
    if method == "bateman" and not can_bateman:
        raise ChainError("Bateman needs a linear chain without production and with distinct decay constants")
    use = "bateman" if (method == "bateman" or (method == "auto" and can_bateman)) else "matrix-exponential"
    amounts = [bateman(lam, n0, t) if use == "bateman" else matrix_solution(lam, edges, n0, prod, t) for t in times]
    return {"method": use, "amounts": amounts}


def _pairs(text: list[str] | None, what: str) -> dict[str, str]:
    out = {}
    for item in text or []:
        if "=" not in item:
            raise ChainError(f"{what}: expected NAME=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def half_life_s(name: str, given: dict) -> dict:
    if name in given:
        v = given[name]
        if v == "stable":
            return {"seconds": None, "stable": True, "source": "user", "edition": "user"}
        try:
            val, unit = v.split(":")
            sec = float(val) * UNIT_S[unit]
        except (ValueError, KeyError) as exc:
            raise ChainError(f"--half-life {name}={v}: expected VALUE:UNIT with a unit in {sorted(UNIT_S)}") from exc
        if not math.isfinite(sec) or sec <= 0:
            raise ChainError(f"half-life of {name} must be > 0")
        return {"seconds": sec, "stable": False, "source": "user", "edition": "user"}
    try:
        q = constants.half_life(name)
    except constants.ConstantsError as exc:
        raise ChainError(f"{exc}; or give --half-life {name}=VALUE:UNIT") from exc
    if q is None:
        return {"seconds": None, "stable": True, "source": "NUBASE2020 (stable)", "edition": "AME2020 + NUBASE2020"}
    s = constants.half_life_seconds(name)
    return {"seconds": s["value"], "uncertainty_s": s["uncertainty"], "stable": False, "nubase": f"{q.value} {q.unit}",
            "source": q.source, "edition": q.edition, "note": s["note"]}


def equilibrium(tp: float | None, td: float | None) -> str:
    if tp is None:
        return "none (stable parent)"
    if td is None:
        return "none (stable daughter: it accumulates)"
    if tp > 100 * td:
        return "secular (parent half-life above 100 times the daughter's): activity ratio tends to 1"
    if tp > td:
        return "transient: activity ratio tends to T_p / (T_p - T_d)"
    return "none (the parent is shorter-lived)"


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chain", nargs="+", required=True, help="members in decay order (nuclide names or labels)")
    ap.add_argument("--initial", nargs="+", required=True, help="NAME=ATOMS (members not named start at 0)")
    ap.add_argument("--times", type=float, nargs="+", required=True)
    ap.add_argument("--time-unit", choices=sorted(UNIT_S), required=True)
    ap.add_argument("--production", nargs="+", help="NAME=ATOMS_PER_S, constant")
    ap.add_argument("--half-life", nargs="+", help="NAME=VALUE:UNIT or NAME=stable (overrides core/constants)")
    ap.add_argument("--branch", nargs="+", help="P:D:F, a fraction F of P decays to D")
    ap.add_argument("--method", choices=("auto", "bateman", "matrix"), default="auto")
    add_status_argument(ap)
    a = ap.parse_args(argv)
    given_flags = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    defaults = [k for k in ("method", "status") if f"--{k}" not in given_flags]
    base = {"status_label": a.status, "inputs": inputs, "defaults_used": defaults}
    try:
        names = a.chain
        if len(set(names)) != len(names):
            raise ChainError("a member appears twice in --chain")
        idx = {n: i for i, n in enumerate(names)}
        hl = {n: half_life_s(n, _pairs(a.half_life, "--half-life")) for n in names}
        lam = [0.0 if hl[n]["stable"] else LN2 / hl[n]["seconds"] for n in names]
        n0 = [0.0] * len(names)
        for k, v in _pairs(a.initial, "--initial").items():
            if k not in idx:
                raise ChainError(f"--initial names {k!r}, not in --chain")
            n0[idx[k]] = float(v)
        prod = [0.0] * len(names)
        for k, v in _pairs(a.production, "--production").items():
            if k not in idx:
                raise ChainError(f"--production names {k!r}, not in --chain")
            prod[idx[k]] = float(v)
        if any(not math.isfinite(x) or x < 0 for x in n0 + prod):
            raise ChainError("amounts and production rates must be finite and >= 0")
        branches: dict[int, list[tuple[int, float]]] = {}
        for b in a.branch or []:
            try:
                p, d, f = b.split(":")
                f = float(f)
            except ValueError as exc:
                raise ChainError(f"--branch {b!r}: expected P:D:F") from exc
            if p not in idx or d not in idx or not 0 < f <= 1:
                raise ChainError(f"--branch {b!r}: P and D must be in --chain and 0 < F <= 1")
            branches.setdefault(idx[p], []).append((idx[d], f))
        edges = []
        for i in range(len(names)):
            explicit = branches.get(i, [])
            rest = 1.0 - sum(f for _, f in explicit)
            if rest < -1e-12:
                raise ChainError(f"the branches of {names[i]} add up to more than 1")
            edges += [(i, d, f) for d, f in explicit]
            if i + 1 < len(names) and rest > 1e-12 and all(d != i + 1 for d, _ in explicit):
                edges.append((i, i + 1, rest))
        scale = UNIT_S[a.time_unit]
        if any(not math.isfinite(t) or t < 0 for t in a.times):
            raise ChainError("times must be finite and >= 0")
        r = solve(lam, edges, n0, prod, [t * scale for t in a.times], method=a.method)
    except ChainError as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    except ImportError:
        print(json.dumps({"status": "missing-dependency", **base, "error": "NumPy and SciPy are needed for the matrix "
                          "exponential", "install": "pip install numpy scipy"}, indent=1))
        return exit_code("missing-dependency")
    results = []
    for t, amounts in zip(a.times, r["amounts"]):
        act = {n: lam[i] * amounts[i] for i, n in enumerate(names)}
        ratios = {f"{names[i + 1]}/{names[i]}": (act[names[i + 1]] / act[names[i]] if act[names[i]] else None)
                  for i in range(len(names) - 1)}
        results.append({"time": t, "time_unit": a.time_unit, "amounts": dict(zip(names, amounts)),
                        "activities_bq": act, "activity_ratios": ratios})
    eq = {f"{names[i + 1]}/{names[i]}": equilibrium(hl[names[i]]["seconds"], hl[names[i + 1]]["seconds"])
          for i in range(len(names) - 1)}
    warnings = []
    for i, n in enumerate(names):
        out_frac = sum(f for p, _, f in edges if p == i)
        if lam[i] and out_frac < 1 - 1e-12 and i + 1 < len(names):
            warnings.append(f"{n}: a fraction {1 - out_frac:.3g} of its decays leaves the listed chain")
    print(json.dumps({"status": "ok", **base, "label": LABEL, "half_lives": hl, "method": r["method"],
                      "edges": [{"from": names[p], "to": names[d], "fraction": f} for p, d, f in edges],
                      "results": results, "equilibrium": eq, "warnings": warnings}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
