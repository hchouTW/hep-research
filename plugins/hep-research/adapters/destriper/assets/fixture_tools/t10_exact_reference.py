#!/usr/bin/env python3
"""The fixed reference of T10's destriping replay: the zero-sum constrained least-squares map and baselines of a
destriper-timestream/1, in exact rational arithmetic (docs/dev/detector-reconstruction/t10-replay-stage-plan.md, section 4).

Written independently of the solver (adapters/destriper/assets/destripe_recipe) and sharing no code with it: standard library
only, its own reader, and another method. The solver iterates on the reduced baseline system; this solves the joint system of map
and baselines directly,

    [ A^T A   c ] [ x      ]   [ A^T y ]
    [ c^T     0 ] [ lambda ] = [ 0     ],      A = [P F], x = (m, a), c = (0 on the map, 1 on each baseline),

by Gauss-Jordan elimination on Fractions. Every input float is read as its exact binary value (Fraction(float) is exact). A
singular system (a scan with more than one connected component, or an unobserved pixel) is refused: no values.

Usage: t10_exact_reference.py solve --timestream T --out R. Output t10-exact-reference/1: every value as an exact "p/q" string and
its nearest float, the multiplier lambda, the input's SHA-256 and this file's own. One JSON object on stdout with "status"; exit 0
written, 1 refused (singular), 2 bad input; an existing target is never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from fractions import Fraction

FORMAT = "t10-exact-reference/1"
INPUT_FORMAT = "destriper-timestream/1"


class Singular(ValueError):
    """The constrained system has no unique solution."""


def _read(document: dict):
    if not isinstance(document, dict) or document.get("format") != INPUT_FORMAT:
        raise ValueError(f"not a {INPUT_FORMAT} document")
    pixels, length = document["pixels"], document["baseline_length"]
    pixel, value = document["pixel"], document["value"]
    if len(pixel) != len(value) or len(pixel) % length:
        raise ValueError("pixel and value differ in length, or are not whole baselines")
    for p in pixel:
        if not (isinstance(p, int) and 0 <= p < pixels):
            raise ValueError(f"pixel {p!r} out of range")
    return pixels, length, pixel, [Fraction(v) for v in value]


def _system(pixels: int, length: int, pixel: list, value: list):
    """The KKT matrix and right side, built sample by sample: each sample adds its row (one 1 at its pixel, one at its baseline)."""
    baselines = len(pixel) // length
    size = pixels + baselines + 1
    matrix = [[Fraction(0)] * size for _ in range(size)]
    right = [Fraction(0)] * size
    for t, (p, y) in enumerate(zip(pixel, value)):
        columns = (p, pixels + t // length)
        for i in columns:
            right[i] += y
            for j in columns:
                matrix[i][j] += 1
    for j in range(pixels, pixels + baselines):
        matrix[size - 1][j] = Fraction(1)
        matrix[j][size - 1] = Fraction(1)
    return matrix, right, baselines


def _gauss_jordan(matrix: list, right: list) -> list:
    size = len(matrix)
    rows = [list(row) + [value] for row, value in zip(matrix, right)]
    for column in range(size):
        pivot = next((index for index in range(column, size) if rows[index][column] != 0), None)
        if pivot is None:
            raise Singular(f"the constrained system is singular at column {column}: a null mode is left that the zero-sum constraint does not fix")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        lead = rows[column][column]
        rows[column] = [entry / lead for entry in rows[column]]
        for index in range(size):
            factor = rows[index][column]
            if index != column and factor != 0:
                rows[index] = [entry - factor * other for entry, other in zip(rows[index], rows[column])]
    return [row[size] for row in rows]


def _entry(value: Fraction) -> dict:
    return {"exact": f"{value.numerator}/{value.denominator}", "float": float(value)}


def solve_exact(document: dict) -> dict:
    pixels, length, pixel, value = _read(document)
    matrix, right, baselines = _system(pixels, length, pixel, value)
    solution = _gauss_jordan(matrix, right)
    return {"format": FORMAT, "map": [_entry(v) for v in solution[:pixels]],
            "baselines": [_entry(v) for v in solution[pixels:pixels + baselines]], "multiplier": _entry(solution[-1])["exact"],
            "method": "joint KKT system of map, baselines and the zero-sum multiplier, Gauss-Jordan on Fractions"}


def _own_sha256() -> str:
    with open(__file__, "rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    solve = sub.add_parser("solve")
    solve.add_argument("--timestream", required=True)
    solve.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    try:
        with open(args.timestream, "rb") as stream:
            raw = stream.read()
        document = json.loads(raw.decode("utf-8"))
        result = solve_exact(document)
    except Singular as exc:
        print(json.dumps({"operation": "solve", "status": "refused", "reason": str(exc)}))
        return 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"operation": "solve", "status": "rejected", "reason": str(exc)}))
        return 2
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    result["reference_sha256"] = _own_sha256()
    try:
        with open(args.out, "x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, sort_keys=True) + "\n")
    except OSError as exc:
        print(json.dumps({"operation": "solve", "status": "rejected", "reason": f"{args.out} cannot be written (never overwritten): {exc}"}))
        return 2
    print(json.dumps({"operation": "solve", "status": "written", "out": args.out, "reference_sha256": result["reference_sha256"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
