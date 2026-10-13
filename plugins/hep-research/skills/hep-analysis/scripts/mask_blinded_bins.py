#!/usr/bin/env python3
"""Mask the bins of a histogram that overlap a blinded region before it is plotted, tabulated or shared.

Synthetic data and tests only when the agent runs it: the input is the unmasked histogram, which an agent must never
hold for real data. For real data this is the data custodian's preparation step, run outside the agent session, and
the agent reads only the released, masked output.

Usage: python3 mask_blinded_bins.py --hist hist.json --low 120 --high 130 [--reference mc.json] [--out masked.json]
hist.json / mc.json: {"edges": [...], "values": [...]}. Writes the masked histogram (blinded bins = null) and,
with --reference, the data/reference ratio with the same bins masked (a ratio reveals its numerator).
Bin edges must be finite and strictly increasing; otherwise nothing is written and the exit code is 2.
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 written; 2 usage or invalid input (NaN, inf, malformed file). The blinded region comes from the collaboration's blinding policy, recorded in the project config `blinding` block.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.blinding.blinding import mask_binned, mask_ratio  # noqa: E402

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope')  # contracts/vocab/core.json artifact_statuses


def _reject_constant(token):
    raise ValueError(f'non-finite number {token} in the input')


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
        out = mask_binned(h["edges"], h["values"], {"low": args.low, "high": args.high})
        if args.reference:
            ref = json.loads(args.reference.read_text(encoding="utf-8"), parse_constant=_reject_constant)["values"]
            out["ratio_to_reference"] = mask_ratio(h["values"], ref, out["blinded_bins"])
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
