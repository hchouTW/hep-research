#!/usr/bin/env python3
"""A weighted histogram filled chunk by chunk from a CSV file, a ROOT tree (uproot.iterate) or Parquet (pyarrow): a
template for out-of-core processing whose result does not depend on the chunking (C5).

Purpose: show the pattern of `<plugin root>/skills/hep-computing/references/columnar-and-large-scale-data.md`: read a
bounded number of rows at a time, reduce each chunk to mergeable sums, and combine the sums. Each bin keeps an exact
running sum (Shewchuk partials, rounded once at the end with math.fsum), so a chunked run equals one pass bit for bit;
a plain floating-point running sum would differ in the last digits and need a declared tolerance instead.

Input: --source csv (standard library; a header row), root (--tree NAME; needs uproot) or parquet (needs pyarrow);
--column X, optional --weight W (default: unit weights, reported in defaults_used), --edges E0 E1 ... (increasing),
--chunk-size N rows per chunk (0 = one pass; default 100000).
Output JSON: status (ok, rejected, missing-dependency), status_label (--status, default unvalidated), inputs,
defaults_used, edges, values and sumw2 (underflow first, overflow last), n_rows, chunks, the source and the method.
Exit codes: 0 ok; 2 bad input (missing file or column, non-numeric value, bad edges); 3 the reader's package missing.
Usage: python3 chunked_histogram.py FILE --source csv --column x [--weight w] --edges 0 1 2 5 10 [--chunk-size 1000]
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import bisect
import csv
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # the import below leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

INSTALL = {"root": "pip install uproot awkward (optional extra root-uproot)", "parquet": "pip install pyarrow"}


class InputError(ValueError):
    pass


class Missing(Exception):
    pass


class ExactSum:
    """Shewchuk's exact summation: the partials represent the sum exactly; value() rounds once."""

    def __init__(self):
        self.partials: list[float] = []

    def add(self, x: float) -> None:
        i = 0
        for y in self.partials:
            if abs(x) < abs(y):
                x, y = y, x
            hi = x + y
            lo = y - (hi - x)
            if lo:
                self.partials[i] = lo
                i += 1
            x = hi
        self.partials[i:] = [x]

    def value(self) -> float:
        return math.fsum(self.partials)


def chunks_csv(path: Path, column: str, weight: str | None, size: int):
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in (column, weight) if c and c not in (reader.fieldnames or [])]
        if missing:
            raise InputError(f"{path}: no column(s) {missing}; header {reader.fieldnames}")
        buf: list[tuple[float, float]] = []
        for i, row in enumerate(reader):
            try:
                buf.append((float(row[column]), float(row[weight]) if weight else 1.0))
            except ValueError as exc:
                raise InputError(f"{path}: row {i + 2} is not numeric ({exc})") from exc
            if size and len(buf) >= size:
                yield buf
                buf = []
        if buf or not size:
            yield buf


def chunks_root(path: Path, tree: str, column: str, weight: str | None, size: int):
    try:
        import uproot
    except ImportError as exc:
        raise Missing(f"uproot is not importable ({exc})") from exc
    names = [column] + ([weight] if weight else [])
    try:
        t = uproot.open(path)[tree]
    except Exception as exc:  # uproot raises many types for an unreadable file or a missing key
        raise InputError(f"{path}: cannot open tree {tree!r} ({exc})") from exc
    missing = [n for n in names if n not in t.keys()]
    if missing:
        raise InputError(f"{path}:{tree}: no branch(es) {missing}")
    step = size if size else t.num_entries or 1
    for arrays in t.iterate(names, step_size=step, library="np"):
        xs = arrays[column].tolist()
        ws = arrays[weight].tolist() if weight else [1.0] * len(xs)
        yield list(zip(map(float, xs), map(float, ws)))


def chunks_parquet(path: Path, column: str, weight: str | None, size: int):
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise Missing(f"pyarrow is not importable ({exc})") from exc
    pf = pq.ParquetFile(path)
    names = [column] + ([weight] if weight else [])
    missing = [n for n in names if n not in pf.schema_arrow.names]
    if missing:
        raise InputError(f"{path}: no column(s) {missing}")
    for batch in pf.iter_batches(batch_size=size or max(pf.metadata.num_rows, 1), columns=names):
        xs = batch.column(column).to_pylist()
        ws = batch.column(weight).to_pylist() if weight else [1.0] * len(xs)
        yield list(zip(map(float, xs), map(float, ws)))


def histogram(chunks, edges: list[float]) -> dict:
    n = len(edges) + 1  # underflow, len(edges) - 1 bins, overflow
    sums = [ExactSum() for _ in range(n)]
    sums2 = [ExactSum() for _ in range(n)]
    rows = nchunks = 0
    for chunk in chunks:
        nchunks += 1
        for x, w in chunk:
            if not (math.isfinite(x) and math.isfinite(w)):
                raise InputError("non-finite value or weight")
            i = bisect.bisect_right(edges, x)  # 0 = underflow, len(edges) = overflow
            sums[i].add(w)
            sums2[i].add(w * w)
            rows += 1
    return {"values": [s.value() for s in sums], "sumw2": [s.value() for s in sums2], "n_rows": rows,
            "chunks": nchunks}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", type=Path)
    ap.add_argument("--source", choices=("csv", "root", "parquet"), required=True)
    ap.add_argument("--tree", help="tree name (--source root)")
    ap.add_argument("--column", required=True)
    ap.add_argument("--weight")
    ap.add_argument("--edges", type=float, nargs="+", required=True)
    ap.add_argument("--chunk-size", type=int, default=100000, help="rows per chunk; 0 reads everything at once")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("weight", "chunk-size", "status") if f"--{k}" not in given]
    base = {"status_label": args.status, "inputs": {k: (str(v) if isinstance(v, Path) else v)
                                                   for k, v in vars(args).items() if k != "status"},
            "defaults_used": defaults}
    try:
        if not args.file.is_file():
            raise InputError(f"{args.file} not found")
        edges = list(args.edges)
        if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])) or not all(map(math.isfinite, edges)):
            raise InputError("--edges must be at least two finite, increasing values")
        if args.chunk_size < 0:
            raise InputError("--chunk-size must be >= 0")
        if args.source == "root" and not args.tree:
            raise InputError("--source root needs --tree")
        reader = {"csv": lambda: chunks_csv(args.file, args.column, args.weight, args.chunk_size),
                  "root": lambda: chunks_root(args.file, args.tree, args.column, args.weight, args.chunk_size),
                  "parquet": lambda: chunks_parquet(args.file, args.column, args.weight, args.chunk_size)}[args.source]
        res = histogram(reader(), edges)
    except Missing as exc:
        print(json.dumps({"status": "missing-dependency", **base, "error": str(exc), "install": INSTALL[args.source]},
                         indent=1))
        return exit_code("missing-dependency")
    except (InputError, OSError) as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": "ok", **base, "edges": edges, **res, "source": args.source,
                      "method": "exact per-bin sums (Shewchuk partials), rounded once; chunking cannot change the result"},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
