#!/usr/bin/env python3
"""Generator event weights: normalization, negative-weight fraction and effective sample size.

Purpose: give the rules of <plugin root>/skills/hep-theory/references/event-generation.md an executable form.
For weights w_i of a FULL production with cross section sigma: per-event normalization sigma * L * w_i / sum(w)
(never by entry count), negative fraction f = N(w < 0) / N, effective sample size N_eff = (sum w)^2 / sum(w^2).
For unit-magnitude weights +-1 this is N (1 - 2f)^2. The script never drops or absolute-values a weight; it reports
what doing so would do to the normalization, as a warning. For a selection it reports the selected sum of weights,
sum of squared weights, N_eff = (sum w)^2 / sum w^2 and the relative statistical uncertainty sqrt(sum w^2) / |sum w|;
a selected sum <= 0 is refused. It refuses non-finite weights, sigma_pb not finite and > 0, a negative or
non-finite luminosity, and selected indices that are not integers, negative, out of range or repeated.

Input JSON: {"weights": [...], "sigma_pb": float, "luminosity_ipb": float (optional),
             "selected": [indices] (optional, events passing a selection)}
Run: python3 event_weights.py weights.json [--status LABEL]. Output JSON: "status" (run status, core/status.py) and
"status_label" (the inputs' artifact label, default unvalidated). Exit 0 ok, 1 refused input, 2 bad arguments or
unreadable input. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # sibling imports leave no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument  # noqa: E402


def _finite(name: str, x) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError(f"{name} must be a number, got {x!r}")
    v = float(x)
    if not math.isfinite(v):
        raise ValueError(f"{name} is not finite ({v})")
    return v


def summarize(weights: list[float], sigma_pb: float, luminosity_ipb: float | None = None, selected=None) -> dict:
    if not isinstance(weights, list) or not weights:
        raise ValueError("weights must be a non-empty list of numbers")
    weights = [_finite(f"weight {i}", w) for i, w in enumerate(weights)]
    sigma_pb = _finite("sigma_pb", sigma_pb)
    if sigma_pb <= 0:
        raise ValueError(f"sigma_pb must be > 0, got {sigma_pb}")
    if luminosity_ipb is not None:
        luminosity_ipb = _finite("luminosity_ipb", luminosity_ipb)
        if luminosity_ipb < 0:
            raise ValueError(f"luminosity_ipb must be >= 0, got {luminosity_ipb}")
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
        if not isinstance(selected, list):
            raise ValueError("selected must be a list of event indices")
        bad = [i for i in selected if isinstance(i, bool) or not isinstance(i, int)]
        if bad:
            raise ValueError(f"selected indices must be integers, got {bad}")
        out_of_range = [i for i in selected if not 0 <= i < n]
        if out_of_range:
            raise ValueError(f"selected indices out of range 0..{n - 1} (negative indices are not allowed): "
                             f"{out_of_range}")
        if len(set(selected)) != len(selected):
            dups = sorted({i for i in selected if selected.count(i) > 1})
            raise ValueError(f"selected lists an event more than once: {dups}")
        sw = [weights[i] for i in selected]
        sel, sel2 = sum(sw), sum(w * w for w in sw)
        if sel <= 0:
            raise ValueError(f"selected sum of weights {sel} is not positive: no normalizable selected yield "
                             "(refused, not flagged)")
        out.update(selected_n_entries=len(sw), selected_sum_w=sel, selected_sum_w2=sel2,
                   selected_effective_sample_size=sel ** 2 / sel2,
                   selected_relative_stat_uncertainty=math.sqrt(sel2) / abs(sel),
                   selected_fraction_of_sum=sel / total, selected_sigma_pb=sigma_pb * sel / total,
                   selected_non_positive_sum="refused")
        if luminosity_ipb is not None:
            out["selected_expected_events"] = sigma_pb * luminosity_ipb * sel / total
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    add_status_argument(ap)
    opts = ap.parse_args(argv)
    try:
        text = open(opts.input, encoding="utf-8").read()
    except OSError as exc:  # a missing or unreadable input: JSON status, exit 2
        print(json.dumps({"status": "rejected", "error": f"cannot read {opts.input}: {exc}"}))
        return 2
    try:
        doc = json.loads(text)
        if not isinstance(doc, dict):
            raise ValueError("input must be a JSON object")
        out = summarize(doc["weights"], doc["sigma_pb"], doc.get("luminosity_ipb"), doc.get("selected"))
    except (ValueError, KeyError, TypeError) as exc:
        reason = f"missing field {exc}" if isinstance(exc, KeyError) else str(exc)
        print(json.dumps({"status": "failed", "status_label": opts.status, "reason": reason}))
        return 1
    print(json.dumps(dict(out, status="ok", status_label=opts.status), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
