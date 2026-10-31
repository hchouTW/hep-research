#!/usr/bin/env python3
"""Consistency of one measurement made on split samples (eras, data halves, detector parts, analysis methods) (S1).

Method: for two splits with values x1, x2 and covariances C1, C2, d = x1 - x2 and
    Cov(d) = C1 + C2 - C12 - C21,   chi2 = d^T Cov(d)^-1 d,   ndf = n bins,
where C12 is the declared covariance shared by the two splits (a common calibration, the same simulation): it is
subtracted, since it moves both splits together. For K splits the overall test is a generalized chi2 against a common
value mu (generalized least squares on the stacked values with the joint covariance; ndf = (K - 1) n; for K = 2 it
equals the pairwise chi2). Every pair is also tested, with the smallest pairwise p-value corrected for the
K (K - 1) / 2 pairs by Sidak, 1 - (1 - p_min)^m, and, with --toys, by Gaussian toys of the joint model at the common
value. p-values are asymptotic (chi2 distribution, exact for Gaussian splits); --toys adds toy p-values.

Assumptions and validity: Gaussian splits with known covariances; the shared blocks must be declared, otherwise they
are taken as zero and the output says "shared systematic uncertainties not subtracted" (the test is then
conservative for a positive shared covariance); Cov(d) and the joint covariance must be positive definite. A large
p-value says the splits agree within the stated covariances, not that a common systematic is absent.

Input JSON: {"splits": [{"id": "era-1", "values": [...], "covariance": [[...]]}, ...],
             "cross_covariance": [{"a": "era-1", "b": "era-2", "block": [[...]]}, ...] (optional; block = Cov(x_a, x_b))}
Output JSON: "status" (run status, core/status.py: ok, or fail when --alpha is given and the overall p-value is below
it), "status_label" (--status, default unvalidated), "inputs", "defaults_used", "overall" {chi2, ndf, p_asymptotic,
p_toys, toys, common_value}, "pairs" [{a, b, chi2, ndf, p_asymptotic}], "pairwise_global" {p_min, n_pairs, p_sidak,
p_toys}, "verdict" (consistent, inconsistent, or null without --alpha), "warnings", "method_kind", "label".
Exit codes: 0 ok; 1 inconsistent at --alpha (a negative verdict); 2 bad input (fewer than two splits, mismatched
sizes, duplicate ids, a matrix that is not symmetric positive definite); 3 NumPy or SciPy missing.
Run: python3 <plugin root>/skills/hep-statistics/scripts/split_consistency.py --input splits.json [--alpha 0.01]
     [--toys 10000 --seed 1]
Requires NumPy and SciPy (not needed for --help).
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
NOT_SUBTRACTED = "shared systematic uncertainties not subtracted: no cross_covariance declared for {pairs}"


class InputError(ValueError):
    """A refused input (exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _matrix(np, m, n, name):
    a = np.asarray(m, dtype=float)
    if a.shape != (n, n) or not np.all(np.isfinite(a)):
        raise InputError(f"{name} must be a finite {n} x {n} matrix")
    return a


def _pd(np, a, name):
    if not np.allclose(a, a.T, rtol=0, atol=1e-12 * max(1.0, float(np.abs(a).max()))):
        raise InputError(f"{name} is not symmetric")
    try:
        np.linalg.cholesky(a)
    except np.linalg.LinAlgError as exc:
        raise InputError(f"{name} is not positive definite (check the declared shared blocks)") from exc


def _load(np, splits, cross):
    if not isinstance(splits, list) or len(splits) < 2:
        raise InputError("give at least two splits")
    ids, xs, covs = [], [], []
    for s in splits:
        if not isinstance(s, dict) or not s.get("id"):
            raise InputError("every split needs an id, values and covariance")
        if s["id"] in ids:
            raise InputError(f"duplicate split id {s['id']!r}")
        x = np.asarray(s.get("values"), dtype=float)
        if x.ndim != 1 or x.size == 0 or not np.all(np.isfinite(x)):
            raise InputError(f"split {s['id']}: values must be a non-empty list of finite numbers")
        ids.append(s["id"])
        xs.append(x)
        covs.append(_matrix(np, s.get("covariance"), x.size, f"covariance of {s['id']}"))
    n = xs[0].size
    if any(x.size != n for x in xs):
        raise InputError(f"every split needs the same number of bins; got {[x.size for x in xs]}")
    k = len(xs)
    joint = np.zeros((k * n, k * n))
    for i, c in enumerate(covs):
        _pd(np, c, f"covariance of {ids[i]}")
        joint[i * n:(i + 1) * n, i * n:(i + 1) * n] = c
    declared = set()
    for c in cross or []:
        if not isinstance(c, dict) or c.get("a") not in ids or c.get("b") not in ids or c.get("a") == c.get("b"):
            raise InputError("each cross_covariance entry names two different splits a and b and a block")
        i, j = ids.index(c["a"]), ids.index(c["b"])
        b = np.asarray(c.get("block"), dtype=float)
        if b.shape != (n, n) or not np.all(np.isfinite(b)):
            raise InputError(f"cross block {c['a']}-{c['b']} must be a finite {n} x {n} matrix")
        if frozenset((i, j)) in declared:
            raise InputError(f"cross block {c['a']}-{c['b']} given twice")
        declared.add(frozenset((i, j)))
        joint[i * n:(i + 1) * n, j * n:(j + 1) * n] = b
        joint[j * n:(j + 1) * n, i * n:(i + 1) * n] = b.T
    _pd(np, joint, "the joint covariance of the splits")
    return ids, xs, joint, n, declared


def _chi2_pair(np, xs, joint, n, i, j):
    d = xs[i] - xs[j]
    vi, vj = slice(i * n, (i + 1) * n), slice(j * n, (j + 1) * n)
    cov = joint[vi, vi] + joint[vj, vj] - joint[vi, vj] - joint[vj, vi]
    _pd(np, cov, f"Cov(d) of the pair {i}-{j}")
    return float(d @ np.linalg.solve(cov, d))


def _gls(np, y, joint, n, k):
    h = np.vstack([np.eye(n)] * k)
    vi = np.linalg.inv(joint)
    mu = np.linalg.solve(h.T @ vi @ h, h.T @ vi @ y)
    r = y - h @ mu
    return float(r @ vi @ r), mu


def analyse(splits, cross, toys=0, seed=None):
    """The consistency tests (importable; raises InputError on a refused input)."""
    import numpy as np
    from scipy import stats
    ids, xs, joint, n, declared = _load(np, splits, cross)
    k = len(xs)
    y = np.concatenate(xs)
    chi2, mu = _gls(np, y, joint, n, k)
    ndf = (k - 1) * n
    pairs = []
    for i in range(k):
        for j in range(i + 1, k):
            c = _chi2_pair(np, xs, joint, n, i, j)
            pairs.append({"a": ids[i], "b": ids[j], "chi2": c, "ndf": n, "p_asymptotic": float(stats.chi2.sf(c, n)),
                          "shared_block_declared": frozenset((i, j)) in declared})
    m = len(pairs)
    p_min = min(p["p_asymptotic"] for p in pairs)
    overall = {"chi2": chi2, "ndf": ndf, "p_asymptotic": float(stats.chi2.sf(chi2, ndf)), "p_toys": None, "toys": 0,
               "common_value": mu.tolist()}
    pg = {"p_min": p_min, "n_pairs": m, "p_sidak": 1.0 - (1.0 - p_min) ** m, "p_toys": None}
    if toys:
        rng = np.random.default_rng(seed)
        lj = np.linalg.cholesky(joint)
        mean = np.concatenate([mu] * k)
        n_over, n_pmin = 0, 0
        for _ in range(toys):
            yt = mean + lj @ rng.standard_normal(k * n)
            ct, _ = _gls(np, yt, joint, n, k)
            n_over += ct >= chi2
            if m > 1:
                xt = [yt[i * n:(i + 1) * n] for i in range(k)]
                pt = min(float(stats.chi2.sf(_chi2_pair(np, xt, joint, n, i, j), n))
                         for i in range(k) for j in range(i + 1, k))
                n_pmin += pt <= p_min
        overall["p_toys"], overall["toys"] = (n_over + 1) / (toys + 1), toys
        if m > 1:
            pg["p_toys"] = (n_pmin + 1) / (toys + 1)
        if m == 1:
            pg["p_toys"] = overall["p_toys"]
    warnings = []
    missing = [f"{p['a']}-{p['b']}" for p in pairs if not p["shared_block_declared"]]
    if missing:
        warnings.append(NOT_SUBTRACTED.format(pairs=", ".join(missing)))
    return {"overall": overall, "pairs": pairs, "pairwise_global": pg, "warnings": warnings,
            "method_kind": "asymptotic" + (" and toys" if toys else ""), "label": LABEL}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="JSON with splits and optional cross_covariance")
    ap.add_argument("--alpha", type=float, help="test size for a verdict; without it only p-values are reported")
    ap.add_argument("--toys", type=int, default=0, help="number of Gaussian toys for toy p-values (default 0: none)")
    ap.add_argument("--seed", type=int, help="seed of the toys (required with --toys)")
    ap.add_argument("--out", help="also write the JSON result to this path")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    defaults = [k for k in ("status", "toys", "alpha") if f"--{k}" not in given]
    status, body = "ok", {}
    try:
        if args.alpha is not None and not (0.0 < args.alpha < 1.0 and math.isfinite(args.alpha)):
            raise InputError("--alpha must lie in (0, 1)")
        if args.toys < 0 or (args.toys and args.seed is None):
            raise InputError("--toys must be >= 0 and needs --seed")
        try:
            import numpy  # noqa: F401
            import scipy  # noqa: F401
        except ImportError:
            status, body = "missing-dependency", {"error": "NumPy and SciPy are required: pip install numpy scipy"}
        else:
            doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise InputError("the input must be a JSON object")
            body = analyse(doc.get("splits"), doc.get("cross_covariance"), args.toys, args.seed)
            verdict = None
            if args.alpha is not None:
                verdict = "inconsistent" if body["overall"]["p_asymptotic"] < args.alpha else "consistent"
                status = "fail" if verdict == "inconsistent" else "ok"
            body["verdict"] = verdict
    except OSError as exc:
        status, body = "rejected", {"error": f"cannot read {args.input}: {exc}"}
    except (InputError, ValueError, TypeError) as exc:
        status, body = "rejected", {"error": str(exc)}
    result = {"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults, **body}
    text = json.dumps(result, indent=1)
    if args.out and status in ("ok", "fail"):
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
