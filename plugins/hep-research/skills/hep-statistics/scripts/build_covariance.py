#!/usr/bin/env python3
"""A covariance proposal from declared correlation models, one block per uncertainty source, and a scan of a
correlation length (S3).

Purpose: when a source's correlation between bins is not published, its structure is a modelling choice. This tool
builds the matrix from the choice the user states, checks it, and shows how much a fit depends on it; it never
invents a correlation. Every output is labeled [Proposal].

Method: block_k = D_k R_k D_k with D_k = diag(sigma_k) (absolute, or "relative" x values) and R_k from the model:
  none           R = I (uncorrelated)
  full           R = 1 (fully correlated; the block is the outer product a a^T)
  length         R_ij = exp(-|ln x_i - ln x_j| / length) (correlation decreasing with the log distance; x > 0)
  antisymmetric  R_ij = s_i s_j, s = +1 below the pivot and -1 at or above it (a tilt about a pivot)
  ar1            R_ij = rho^|i - j| (equally spaced bins; |rho| < 1)
  exp-time       R_ij = exp(-|t_i - t_j| / tau) (tau > 0; the time-bin recipe of time-series-inference.md)
  matrix         R given by the user (a correlation matrix, unit diagonal)
The total is the sum of the blocks. Each block and the total are checked for symmetry and positive
semi-definiteness (smallest eigenvalue >= -1e-10 x the largest |entry|); a block that is not PSD is reported and the
run fails (exit 1): nothing is repaired or clipped.
scan: the same build with one source's length (length or exp-time tau, or ar1 rho) set to each value of --lengths;
with "residuals" in the input, chi2 = r^T C^-1 r is reported per value, so the dependence on the assumption is seen.

Assumptions and validity: Gaussian uncertainties; the models are proposals, not measurements of a correlation; the
length or rho comes from the user's argument (detector granularity, run length), and the scan shows its effect.

Input JSON: {"values": [...] (central values, length n; needed for "relative"), "x": [...] (bin centres, x > 0, for
length and antisymmetric), "times": [...] (for exp-time), "sources": [{"name", "model", "sigma": number or [n] |
"relative": number or [n], "length" | "pivot" | "rho" | "tau" | "correlation": [[n x n]]}, ...],
"residuals": [...] (optional, for scan), "units": "..." (optional)}
Output JSON: "status" (ok, failed, rejected, missing-dependency), "status_label", "inputs", "defaults_used", "label"
([Proposal]), "blocks" {name: matrix}, "total", "checks" {name: {min_eigenvalue, psd}}, "total_check"; scan: "scan"
[{length, chi2, min_eigenvalue, logdet}]. --out writes {"labels", "matrix", "kind": "absolute", "units", "blocks"}
for core/stats/validate_covariance.py.
Exit codes: 0 ok; 1 a block or the total is not positive semi-definite; 2 bad input; 3 NumPy missing.
Run: python3 <plugin root>/skills/hep-statistics/scripts/build_covariance.py build --input sources.json [--out cov.json]
     python3 <plugin root>/skills/hep-statistics/scripts/build_covariance.py scan --input sources.json --source NAME
         --lengths 0.1,0.3,1,3
Requires NumPy (not needed for --help).
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

LABEL = "[Proposal]"
MODELS = ("none", "full", "length", "antisymmetric", "ar1", "exp-time", "matrix")
PARAM = {"length": "length", "exp-time": "tau", "ar1": "rho", "antisymmetric": "pivot", "matrix": "correlation"}
NOTE = ("a proposal: the correlation models are stated assumptions, not measured correlations; show the scan or an "
        "alternative model before relying on a fit that uses them")


class InputError(ValueError):
    """A refused input (exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _vector(np, v, n, name):
    a = np.asarray(v, dtype=float)
    if a.ndim == 0:
        a = np.full(n, float(a))
    if a.shape != (n,) or not np.all(np.isfinite(a)):
        raise InputError(f"{name} must be a finite number or a list of {n} numbers")
    return a


def _scale(np, src, values, n):
    if ("sigma" in src) == ("relative" in src):
        raise InputError(f"source {src.get('name')!r}: give exactly one of sigma (absolute) or relative")
    if "sigma" in src:
        s = _vector(np, src["sigma"], n, f"{src['name']}.sigma")
    else:
        if values is None:
            raise InputError(f"source {src['name']!r}: relative needs values")
        s = _vector(np, src["relative"], n, f"{src['name']}.relative") * values
    if np.any(s < 0):
        raise InputError(f"source {src['name']!r}: uncertainties must be >= 0")
    return s


def _need(np, doc, key, n, src):
    if doc.get(key) is None:
        raise InputError(f"source {src['name']!r} (model {src['model']}) needs {key!r}")
    return _vector(np, doc[key], n, key)


def correlation(np, src, doc, n):
    model = src["model"]
    if model == "none":
        return np.eye(n)
    if model == "full":
        return np.ones((n, n))
    p = src.get(PARAM[model])
    if p is None:
        raise InputError(f"source {src['name']!r} (model {model}) needs {PARAM[model]!r}")
    if model == "matrix":
        r = np.asarray(p, dtype=float)
        if r.shape != (n, n) or not np.all(np.isfinite(r)):
            raise InputError(f"source {src['name']!r}: correlation must be a finite {n} x {n} matrix")
        if not np.allclose(np.diag(r), 1.0) or not np.allclose(r, r.T) or np.any(np.abs(r) > 1 + 1e-12):
            raise InputError(f"source {src['name']!r}: correlation must be symmetric, unit-diagonal, |r| <= 1")
        return r
    p = float(p)
    if not math.isfinite(p):
        raise InputError(f"source {src['name']!r}: {PARAM[model]} must be finite")
    if model == "length":
        x = _need(np, doc, "x", n, src)
        if np.any(x <= 0) or p <= 0:
            raise InputError(f"source {src['name']!r}: length needs x > 0 and length > 0")
        lx = np.log(x)
        return np.exp(-np.abs(np.subtract.outer(lx, lx)) / p)
    if model == "antisymmetric":
        x = _need(np, doc, "x", n, src)
        s = np.where(x < p, 1.0, -1.0)
        return np.outer(s, s)
    if model == "ar1":
        if not -1.0 < p < 1.0:
            raise InputError(f"source {src['name']!r}: rho must lie in (-1, 1)")
        i = np.arange(n)
        return p ** np.abs(np.subtract.outer(i, i))
    t = _need(np, doc, "times", n, src)  # exp-time
    if p <= 0:
        raise InputError(f"source {src['name']!r}: tau must be > 0")
    return np.exp(-np.abs(np.subtract.outer(t, t)) / p)


def _check(np, m):
    scale = max(1.0, float(np.abs(m).max())) if m.size else 1.0
    ev = float(np.linalg.eigvalsh(0.5 * (m + m.T)).min()) if m.size else 0.0
    return {"min_eigenvalue": ev, "symmetric": bool(np.allclose(m, m.T, rtol=0, atol=1e-12 * scale)),
            "psd": bool(ev >= -1e-10 * scale and np.allclose(m, m.T, rtol=0, atol=1e-12 * scale))}


def build(doc: dict, override: dict | None = None) -> dict:
    import numpy as np
    sources = doc.get("sources")
    if not isinstance(sources, list) or not sources:
        raise InputError("give at least one source")
    values = doc.get("values")
    if values is not None:
        values = _vector(np, values, len(values), "values")
    n = len(values) if values is not None else None
    for key in ("x", "times"):
        if n is None and doc.get(key) is not None:
            n = len(doc[key])
    if n is None:
        first = sources[0]
        n = len(first.get("sigma")) if isinstance(first.get("sigma"), list) else None
    if not n:
        raise InputError("cannot tell the number of bins: give values, x or times")
    blocks, checks, names = {}, {}, []
    for src in sources:
        if not isinstance(src, dict) or not src.get("name") or src.get("model") not in MODELS:
            raise InputError(f"every source needs a name and a model in {list(MODELS)}")
        if src["name"] in names:
            raise InputError(f"duplicate source name {src['name']!r}")
        names.append(src["name"])
        if override and src["name"] == override["name"]:
            src = dict(src, **{PARAM[src["model"]]: override["value"]})
        s = _scale(np, src, values, n)
        b = np.outer(s, s) * correlation(np, src, doc, n)
        blocks[src["name"]] = b
        checks[src["name"]] = _check(np, b)
    total = sum(blocks.values())
    return {"n": n, "names": names, "blocks": blocks, "checks": checks, "total": total, "total_check": _check(np, total)}


def _ok(res) -> bool:
    return all(c["psd"] for c in res["checks"].values()) and res["total_check"]["psd"]


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build the blocks and the total")
    b.add_argument("--input", required=True, help="JSON with values, x or times, and sources")
    b.add_argument("--out", help="write {labels, matrix, kind, units, blocks} for validate_covariance.py")
    s = sub.add_parser("scan", help="scan one source's length (length, tau or rho)")
    s.add_argument("--input", required=True)
    s.add_argument("--source", required=True, help="name of a length, exp-time or ar1 source")
    s.add_argument("--lengths", required=True, help="comma-separated values to scan")
    for p in (b, s):
        add_status_argument(p)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    defaults = [k for k in ("status",) if f"--{k}" not in given]
    status, body = "ok", {}
    try:
        try:
            import numpy as np
        except ImportError:
            status, body = "missing-dependency", {"error": "NumPy is required: pip install numpy"}
        else:
            doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise InputError("the input must be a JSON object")
            if args.command == "build":
                res = build(doc)
                body = {"label": LABEL, "blocks": {k: v.tolist() for k, v in res["blocks"].items()},
                        "total": res["total"].tolist(), "checks": res["checks"], "total_check": res["total_check"],
                        "note": NOTE}
                if not _ok(res):
                    status = "failed"
                    body["reason"] = "a block or the total is not positive semi-definite; nothing was repaired"
                elif args.out:
                    Path(args.out).write_text(json.dumps({
                        "labels": [f"bin{i}" for i in range(res["n"])], "matrix": res["total"].tolist(),
                        "kind": "absolute", "units": doc.get("units", "value^2"),
                        "blocks": {k: v.tolist() for k, v in res["blocks"].items()}, "label": LABEL}, indent=1) + "\n",
                        encoding="utf-8")
            else:
                src = next((x for x in doc.get("sources") or [] if isinstance(x, dict) and x.get("name") == args.source),
                           None)
                if src is None or src.get("model") not in ("length", "exp-time", "ar1"):
                    raise InputError("--source must name a length, exp-time or ar1 source")
                try:
                    grid = [float(v) for v in args.lengths.split(",") if v.strip()]
                except ValueError as exc:
                    raise InputError("--lengths must be comma-separated numbers") from exc
                if not grid or not all(math.isfinite(v) for v in grid):
                    raise InputError("--lengths must be finite numbers")
                r = doc.get("residuals")
                rows = []
                for v in grid:
                    res = build(doc, {"name": args.source, "value": v})
                    row = {"length": v, "parameter": PARAM[src["model"]], "min_eigenvalue": res["total_check"]["min_eigenvalue"],
                           "psd": _ok(res)}
                    sign, logdet = np.linalg.slogdet(res["total"])
                    row["logdet"] = float(logdet) if sign > 0 else None
                    if r is not None:
                        rv = _vector(np, r, res["n"], "residuals")
                        row["chi2"] = float(rv @ np.linalg.solve(res["total"], rv)) if sign > 0 else None
                    rows.append(row)
                body = {"label": LABEL, "source": args.source, "scan": rows, "note": NOTE}
                if not all(row["psd"] for row in rows):
                    status, body["reason"] = "failed", "the total is not positive semi-definite at some scanned value"
    except OSError as exc:
        status, body = "rejected", {"error": f"cannot read {args.input}: {exc}"}
    except (InputError, ValueError, TypeError, KeyError) as exc:
        status, body = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **body}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
