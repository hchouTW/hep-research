#!/usr/bin/env python3
"""Flag surrogate-model queries that leave the training domain (extrapolation).

Purpose: a surrogate (an ML model standing in for a simulation or a calculation) is only validated where it was
trained. Its output looks equally confident everywhere, so extrapolation has to be detected from the inputs.

What it does: for each query point, reports (1) features outside the per-feature training range (box check) and
(2) the distance to the nearest training point, in units scaled by each feature's training range, compared with the
typical nearest-neighbour spacing inside the training set. A query is 'outside' when it fails the box check, and
'sparse' when it is inside the box but farther than --factor times the 95th percentile of training spacings
(holes and corners of the box are not covered by the training data).

Input JSON: {"features": ["a", "b"], "training": [[...], ...], "queries": [[...], ...]}
  or "training_domain": {"a": [lo, hi], ...} instead of "training" (box check only; spacing is then not checked).
Output: JSON report. Exit codes: 0 every query inside, 1 any query outside or sparse, 2 bad input.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/check_surrogate_domain.py domain.json [--factor 3]
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def _ranges(features, training):
    return {f: [min(p[i] for p in training), max(p[i] for p in training)] for i, f in enumerate(features)}


def _dist(a, b, scale):
    return math.sqrt(sum(((x - y) / s) ** 2 for x, y, s in zip(a, b, scale)))


def check(payload: dict, factor: float = 3.0) -> dict:
    feats = payload["features"]
    training = payload.get("training")
    box = payload.get("training_domain") or (_ranges(feats, training) if training else None)
    if not box:
        raise ValueError("need 'training' points or a 'training_domain'")
    scale = [max(box[f][1] - box[f][0], 1e-300) for f in feats]
    threshold = None
    if training and len(training) > 1:
        nn = sorted(min(_dist(p, q, scale) for j, q in enumerate(training) if j != i) for i, p in enumerate(training))
        threshold = factor * nn[min(len(nn) - 1, int(0.95 * len(nn)))]
    rows = []
    for k, q in enumerate(payload["queries"]):
        out = [f for i, f in enumerate(feats) if not box[f][0] <= q[i] <= box[f][1]]
        row = {"query": k, "outside_features": out}
        if training:
            d = min(_dist(q, p, scale) for p in training)
            row["nearest_scaled_distance"] = round(d, 6)
            row["sparse"] = bool(not out and threshold is not None and d > threshold)
        row["status"] = "outside" if out else ("sparse" if row.get("sparse") else "inside")
        rows.append(row)
    return {"training_box": box, "spacing_threshold": threshold, "queries": rows,
            "passed": all(r["status"] == "inside" for r in rows),
            "note": "inside the domain is necessary, not sufficient: validate the surrogate on held-out points there"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path")
    ap.add_argument("--factor", type=float, default=3.0)
    args = ap.parse_args(argv)
    try:
        with open(args.path, encoding="utf-8") as fh:
            rep = check(json.load(fh), args.factor)
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    print(json.dumps(rep, indent=1))
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
