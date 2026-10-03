#!/usr/bin/env python3
"""SYNTHETIC chunk worker for the batch-partition example: the T21 computation (examples/local-partition/run.py
compute()) for one chunk, written as JSON to --out. Usage: worker.py --start A --stop B --seed S --out FILE --id ID"""
import argparse
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("t21", Path(__file__).resolve().parents[1] / "local-partition" / "run.py")
t21 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t21)

ap = argparse.ArgumentParser()
for a in ("--start", "--stop", "--seed"):
    ap.add_argument(a, type=int, required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--id", required=True)
args = ap.parse_args()
print(f"synthetic chunk {args.id}: items [{args.start}, {args.stop})")
Path(args.out).write_text(json.dumps(t21.compute({"start": args.start, "stop": args.stop, "seed": args.seed})))
