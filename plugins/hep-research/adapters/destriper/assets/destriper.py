#!/usr/bin/env python3
"""reco.scan.destriper/1, T10's destriping replay solver: a development binding in Python, not a native backend (decisions.md,
"The user's answer to U7"; the native scan or global solver stays a recorded gap, as U12 A). Synthetic inputs only; no quality
claim.

Operations (contracts/tool_contracts/destriper.json):
  solve          destriper-timestream/1 -> destriper-product/1: conjugate gradient on the reduced baseline system with the zero-sum
                 baseline constraint, then the map by binning; the embedded reconstruction-product/1 holds the
                 reconstruction:scan-v1 global block. --constraint zero-sum (default) states the constraint and reports every map
                 value and baseline; --constraint none states none, names every parameter unidentifiable and reports only the
                 combinations the data determine (map and baseline differences, one map-plus-baseline sum). A scan with an
                 unobserved pixel or more than one connected component is refused: one constraint cannot fix two null modes.
                 A product is never overwritten.
  check-product  read a product back, refusing a malformed or incomplete one, one whose method card differs, or one whose
                 top-level map and baselines are not the embedded reported values, and run
                 contracts.reconstruction.read_sidecar on the embedded product.

Output: one JSON object on stdout with "status". Exit 0 ok or written; 1 refused (the map is not determined), not-converged (the
iteration budget ran out; no product), or failed (check-product: the contract refuses the embedded product); 2 rejected input,
no product written; 3 a missing dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
CARD = HERE / "destriper.method-card.json"
EXIT_FAILED, EXIT_INVALID, EXIT_MISSING = 1, 2, 3


def report(operation: str, status: str, reason: str, code: int, **fields) -> int:
    print(json.dumps({"operation": operation, "status": status, "reason": reason, "exit_code": code, **fields}, sort_keys=True))
    return code


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    solve = sub.add_parser("solve", help="destripe one timestream")
    solve.add_argument("--timestream", required=True, help="destriper-timestream/1, role reconstruction-input")
    solve.add_argument("--product", required=True, help="destriper-product/1 to write; never an existing file; not written on a refusal")
    solve.add_argument("--product-id", required=True, help="the product's identity")
    solve.add_argument("--constraint", choices=("zero-sum", "none"), default="zero-sum", help="the stated constraint on the offset mode")
    solve.add_argument("--stopping", type=float, help="relative residual at which the iteration stops (default 1e-10, recorded)")
    solve.add_argument("--max-iterations", type=int, help="iteration budget (default 10 per baseline, recorded)")
    check = sub.add_parser("check-product", help="read a product back and run the contract on its embedded product")
    check.add_argument("--product", required=True, help="destriper-product/1 to read")
    return ap


def solve(args) -> int:
    from destripe_recipe import DEFAULT_STOPPING, product, solver, timestream
    started = time.perf_counter()
    source, target = Path(args.timestream), Path(args.product)
    if not source.is_file():
        return report("solve", "rejected", f"no such input file: {source}", EXIT_INVALID)
    if target.exists():
        return report("solve", "rejected", f"a product is never overwritten: {target} exists", EXIT_INVALID)
    stopping = DEFAULT_STOPPING if args.stopping is None else args.stopping
    if not 0 < stopping < 1 or (args.max_iterations is not None and args.max_iterations < 1):
        return report("solve", "rejected", "the stopping value is in (0, 1) and the budget at least 1", EXIT_INVALID)
    raw = source.read_bytes()
    try:
        stream = timestream.read(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, timestream.Refusal):
            return report("solve", "refused", str(exc), EXIT_FAILED, components=exc.components)
        return report("solve", "rejected", str(exc), EXIT_INVALID)
    try:
        solution = solver.solve(stream, stopping=stopping, max_iterations=args.max_iterations)
    except solver.NotConverged as exc:
        return report("solve", "not-converged", str(exc), EXIT_FAILED, iterations=exc.iterations, relative_residual=exc.relative_residual)
    built = product.build(stream, solution, constraint=args.constraint, product_id=args.product_id,
                          input_sha256=hashlib.sha256(raw).hexdigest(), card_path=CARD)
    partial = target.with_name(target.name + ".partial")
    try:
        partial.write_text(product.dumps(built), encoding="utf-8")
        os.replace(partial, target)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        return report("solve", "rejected", f"product cannot be written: {exc.strerror}", EXIT_INVALID)
    return report("solve", "written", "", 0, product=str(target), constraint=args.constraint, stopping=stopping,
                  iterations=solution.iterations, relative_residual=solution.relative_residual,
                  input_sha256=built["input"]["sha256"], seconds=round(time.perf_counter() - started, 3))


def check_product(args) -> int:
    from destripe_recipe import product
    path = Path(args.product)
    if not path.is_file():
        return report("check-product", "rejected", f"no such input file: {path}", EXIT_INVALID)
    try:
        document = product.read(json.loads(path.read_text(encoding="utf-8")), HERE)
    except (UnicodeDecodeError, ValueError, TypeError, KeyError, AttributeError) as exc:  # a malformed product is rejected, never a traceback
        return report("check-product", "rejected", str(exc), EXIT_INVALID)
    if str(PLUGIN) not in sys.path:
        sys.path.insert(0, str(PLUGIN))
    from contracts.reconstruction import read_sidecar
    started = time.perf_counter()
    result = read_sidecar(document["reconstruction_product"])
    fields = {"errors": sorted({finding.code for finding in result.errors}), "constraint": document["solver"]["constraint"],
              "contract_seconds": round(time.perf_counter() - started, 3)}
    if not result.ok:
        return report("check-product", "failed", "contracts.reconstruction refuses the embedded product", EXIT_FAILED, **fields)
    return report("check-product", "ok", "", 0, **fields)


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    try:
        import numpy  # noqa: F401
    except ImportError as exc:
        return report(args.operation, "missing-dependency", f"{exc.name} is not installed", EXIT_MISSING)
    return solve(args) if args.operation == "solve" else check_product(args)


if __name__ == "__main__":
    sys.exit(main())
