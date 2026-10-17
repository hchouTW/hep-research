#!/usr/bin/env python3
"""Report step of the example workflow: total weight and rows from the histogram step (standard library).
Usage: report.py histogram.json --out report.json"""
import argparse
import json
import math
import sys

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("histogram")
ap.add_argument("--out", required=True)
a = ap.parse_args()
h = json.load(open(a.histogram, encoding="utf-8"))
if h.get("status") != "ok":
    print(f"histogram step did not succeed: {h.get('status')}", file=sys.stderr)
    sys.exit(1)
out = {"label": "SYNTHETIC", "n_rows": h["n_rows"], "total_weight": math.fsum(h["values"]),
       "in_range_weight": math.fsum(h["values"][1:-1]), "edges": h["edges"]}
with open(a.out, "w", encoding="utf-8") as fh:
    fh.write(json.dumps(out, indent=1, sort_keys=True) + "\n")
