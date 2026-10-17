#!/usr/bin/env python3
"""SYNTHETIC events for the example workflow: x exponential, w uniform, from a seeded generator (standard library).
Usage: generate_events.py --seed N --n ROWS --out events.csv"""
import argparse
import random
import sys

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument("--seed", type=int, required=True)
ap.add_argument("--n", type=int, required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
rng = random.Random(a.seed)
with open(a.out, "w", encoding="utf-8", newline="") as fh:
    fh.write("x,w\n")
    for _ in range(a.n):
        fh.write(f"{rng.expovariate(0.3)!r},{rng.uniform(0.5, 1.5)!r}\n")
sys.exit(0)
