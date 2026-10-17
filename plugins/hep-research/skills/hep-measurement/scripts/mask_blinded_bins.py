#!/usr/bin/env python3
"""Mask the bins of a histogram that overlap a blinded region before it is plotted, tabulated or shared.

Synthetic data and tests only when the agent runs it: the input is the unmasked histogram, which an agent must never
hold for real data. For real data this is the data custodian's preparation step, run outside the agent session, and
the agent reads only the released, masked output.

Usage: python3 mask_blinded_bins.py --hist hist.json --low 120 --high 130 [--reference mc.json] [--out masked.json]
hist.json / mc.json: {"edges": [...], "values": [...]}, optionally "errors" and/or "variances" (one per bin) and
"underflow"/"overflow" numbers. Writes the masked histogram (blinded bins = null) and, with --reference, the
data/reference ratio with the same bins masked (a ratio reveals its numerator). Error and variance arrays are masked
with the same mask (a masked value never travels with its unmasked error); the underflow (overflow) is masked when the
blinded range reaches below the first (above the last) edge. The script fails closed: values that are not finite
numbers, and errors, variances or reference values whose length differs from the number of bins, exit 2 and write
nothing (these checks are made here, independently of core.blinding).
Bin edges must be finite and strictly increasing; otherwise nothing is written and the exit code is 2.
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 written; 2 usage or invalid input (NaN, inf, malformed file). The blinded region comes from the collaboration's blinding policy, recorded in the project config `blinding` block.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.blinding.blinding import mask_binned, mask_ratio  # noqa: E402
from core.protected.guard import protected_main  # noqa: E402

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope', 'projection')  # contracts/vocab/core.json artifact_statuses


def _reject_constant(token):
    raise ValueError(f'non-finite number {token} in the input')


def _numbers(values, what, n=None):
    """Finite numbers only (bools and strings refused); n: required length."""
    if not isinstance(values, list):
        raise ValueError(f"{what} must be a list of numbers")
    if n is not None and len(values) != n:
        raise ValueError(f"{what} has {len(values)} entries for {n} bins: refusing to align them")
    for i, v in enumerate(values):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"{what}[{i}] must be a number, got {v!r}")
    return [float(v) for v in values]


def _number(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{what} must be a number, got {v!r}")
    return float(v)


@protected_main("mask_blinded_bins")
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hist", type=Path, required=True)
    ap.add_argument("--low", type=float, required=True)
    ap.add_argument("--high", type=float, required=True)
    ap.add_argument("--reference", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--status", choices=STATUSES, default="unvalidated", help="status label, echoed as status")
    args = ap.parse_args(argv)
    if not args.low < args.high:
        ap.error(f"blinded range needs --low < --high (got {args.low} >= {args.high})")
    try:
        h = json.loads(args.hist.read_text(encoding="utf-8"), parse_constant=_reject_constant)
        if not isinstance(h, dict):
            raise ValueError("histogram JSON must be an object {\"edges\": [...], \"values\": [...]}")
        edges = _numbers(h["edges"], "edges")
        values = _numbers(h["values"], "values", len(edges) - 1 if len(edges) > 1 else None)
        out = mask_binned(edges, values, {"low": args.low, "high": args.high})
        mask = out["blinded_bins"]
        for key in ("errors", "variances"):
            if key in h:
                arr = _numbers(h[key], key, len(values))
                out[key] = [None if b else x for x, b in zip(arr, mask)]
        for key, blinded in (("underflow", args.low < edges[0]), ("overflow", args.high > edges[-1])):
            if key in h:
                out[key] = None if blinded else _number(h[key], key)
        if args.reference:
            ref_doc = json.loads(args.reference.read_text(encoding="utf-8"), parse_constant=_reject_constant)
            if not isinstance(ref_doc, dict):
                raise ValueError("reference JSON must be an object with 'values'")
            ref = _numbers(ref_doc["values"], "reference values", len(values))
            out["ratio_to_reference"] = mask_ratio(values, ref, mask)
        for key in ("errors", "variances", "ratio_to_reference"):
            if key in out and any(b and x is not None for x, b in zip(out[key], mask)):
                raise ValueError(f"internal check: {key} would carry a value in a blinded bin")
    except KeyError as exc:
        print(f"error: histogram JSON is missing key {exc} (expected {{\"edges\": [...], \"values\": [...]}})", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps({"status": args.status, **out}, indent=1)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
