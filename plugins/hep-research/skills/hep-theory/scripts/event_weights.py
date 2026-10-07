#!/usr/bin/env python3
"""Generator event weights: normalization, negative-weight fraction and effective sample size.

Purpose: give the rules of <plugin root>/skills/hep-theory/references/event-generation.md an executable form.
For weights w_i of a FULL production with cross section sigma: per-event normalization sigma * L * w_i / sum(w)
(never by entry count), negative fraction f = N(w < 0) / N, effective sample size N_eff = (sum w)^2 / sum(w^2).
For unit-magnitude weights +-1 this is N (1 - 2f)^2. The script never drops or absolute-values a weight; it reports
what doing so would do to the normalization, as a warning.

Input JSON: {"weights": [...], "sigma_pb": float, "luminosity_ipb": float (optional),
             "selected": [indices] (optional, events passing a selection)}
Run: python3 event_weights.py weights.json. Exit 0 ok, 1 refused input, 2 bad arguments. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys


def summarize(weights: list[float], sigma_pb: float, luminosity_ipb: float | None = None, selected=None) -> dict:
    if not weights:
        raise ValueError("no weights")
    total = sum(weights)
    if total <= 0:
        raise ValueError("sum of weights is not positive: the production is not normalizable as given")
    n = len(weights)
    f_neg = sum(1 for w in weights if w < 0) / n
    n_eff = total ** 2 / sum(w * w for w in weights)
    out = {"n_entries": n, "sum_of_weights": total, "negative_fraction": f_neg, "effective_sample_size": n_eff,
           "effective_over_entries": n_eff / n,
           "bias_if_abs_weights": sum(abs(w) for w in weights) / total - 1.0,
           "bias_if_negatives_dropped": sum(w for w in weights if w > 0) / total - 1.0}
    if selected is not None:
        sel = sum(weights[i] for i in selected)
        out["selected_fraction_of_sum"] = sel / total
        out["selected_sigma_pb"] = sigma_pb * sel / total
        if luminosity_ipb is not None:
            out["selected_expected_events"] = sigma_pb * luminosity_ipb * sel / total
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    opts = ap.parse_args(argv)
    doc = json.loads(open(opts.input, encoding="utf-8").read())
    try:
        out = summarize([float(w) for w in doc["weights"]], float(doc["sigma_pb"]), doc.get("luminosity_ipb"),
                        doc.get("selected"))
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
        print(f"event_weights.py: error: {_exc}", file=_sys.stderr)
        raise SystemExit(2)
