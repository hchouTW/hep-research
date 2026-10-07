#!/usr/bin/env python3
"""PDF uncertainty of one observable from its values on every member of a PDF set, by the set's own error type.

Purpose: apply the combination formula that matches the set (the most common PDF-uncertainty error is using the
Hessian formula on replicas or the reverse). Formulas (see <plugin root>/skills/hep-theory/references/pdfs-and-lhapdf.md):
  symmhessian  members 0, 1..N: delta = sqrt(sum_k (X_k - X_0)^2)                      (symmetric eigenvectors)
  hessian      members 0, (1,2), (3,4) ... pairs (+, -) along each eigenvector:
               delta+ = sqrt(sum_k max(X_2k-1 - X_0, X_2k - X_0, 0)^2), delta- likewise with min (asymmetric)
  replicas     members 0 (average), 1..N replicas: central = mean, delta = sample standard deviation, and the
               central 68% interval of the replicas
The error type and the confidence level of the set come from the set's metadata (LHAPDF `ErrorType`, `ErrorConfLevel`);
the script refuses a member count that does not fit the declared type. A Hessian set quoted at 90% CL is not
rescaled silently: pass --rescale-to-68 to divide by 1.645 (Gaussian assumption, stated in the output).

Input JSON: {"error_type": "symmhessian" | "hessian" | "replicas", "conf_level_percent": 68 | 90,
             "members": [X_0, X_1, ...]}
Run: python3 pdf_uncertainty.py input.json [--rescale-to-68]. Exit 0 ok, 1 refused input, 2 bad arguments.
Standard library only. This combines member values; it does not evaluate PDFs (that needs LHAPDF).
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys


def combine(error_type: str, members: list[float], conf_level_percent: float = 68.0, rescale_to_68: bool = False) -> dict:
    if len(members) < 3:
        raise ValueError("need the central member and at least two error members")
    x0, rest = members[0], members[1:]
    if error_type == "symmhessian":
        up = down = math.sqrt(sum((x - x0) ** 2 for x in rest))
        central = x0
    elif error_type == "hessian":
        if len(rest) % 2:
            raise ValueError(f"asymmetric Hessian set needs pairs of error members, got {len(rest)}")
        pairs = list(zip(rest[0::2], rest[1::2]))
        up = math.sqrt(sum(max(a - x0, b - x0, 0.0) ** 2 for a, b in pairs))
        down = math.sqrt(sum(max(x0 - a, x0 - b, 0.0) ** 2 for a, b in pairs))
        central = x0
    elif error_type == "replicas":
        if len(rest) < 20:
            raise ValueError(f"{len(rest)} replicas are too few for a standard deviation or a 68% interval")
        central = statistics.fmean(rest)
        up = down = statistics.stdev(rest)
        ordered = sorted(rest)
        lo_i, hi_i = int(round(0.16 * (len(ordered) - 1))), int(round(0.84 * (len(ordered) - 1)))
        interval = [ordered[lo_i], ordered[hi_i]]
    else:
        raise ValueError(f"unknown error_type {error_type!r}")
    out = {"error_type": error_type, "n_error_members": len(rest), "central": central,
           "delta_up": up, "delta_down": down, "conf_level_percent": conf_level_percent}
    if error_type == "replicas":
        out["replica_68_interval"] = interval
        out["member_0_vs_replica_mean"] = x0 - central
    if rescale_to_68 and conf_level_percent != 68.0:
        if abs(conf_level_percent - 90.0) > 1e-9:
            raise ValueError("only 90% to 68% rescaling is supported")
        out.update(delta_up=up / 1.645, delta_down=down / 1.645, conf_level_percent=68.0,
                   rescaling="divided by 1.645 (assumes a Gaussian; a prescription, not a property of the set)")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", help="JSON file with error_type, conf_level_percent and members")
    ap.add_argument("--rescale-to-68", action="store_true")
    opts = ap.parse_args(argv)
    doc = json.loads(open(opts.input, encoding="utf-8").read())
    try:
        out = combine(doc["error_type"], [float(x) for x in doc["members"]], float(doc.get("conf_level_percent", 68)),
                      opts.rescale_to_68)
    except (ValueError, KeyError) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}))
        return 1
    print(json.dumps(dict(out, status="ok"), indent=1))
    return 0


if __name__ == "__main__":
    import sys as _sys
    try:
        sys.exit(main())
    except OSError as _exc:  # a missing or unreadable input: one line, no traceback
        print(f"pdf_uncertainty.py: error: {_exc}", file=_sys.stderr)
        raise SystemExit(2)
