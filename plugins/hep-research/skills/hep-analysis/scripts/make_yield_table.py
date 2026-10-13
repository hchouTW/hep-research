#!/usr/bin/env python3
"""Render a HEP yield CSV (region,sample,yield[,uncertainty]) as Markdown tables with a status line.

Status: --status (required; one of the core artifact_statuses) is printed above the tables, so unlabeled
numbers never reach a note. Yields and uncertainties must be finite numbers (nan and inf are refused). Pipes and
line breaks in region and sample names are escaped so they cannot break the Markdown table. --totals adds a total per
region: yields summed, uncertainties added in quadrature, which assumes independent samples (stated under the table).
Exit codes: 0 written; 2 usage or invalid input (missing file or column, non-numeric, NaN or inf).
Run: python3 <plugin root>/skills/hep-analysis/scripts/make_yield_table.py --input yields.csv --status synthetic
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path


REQUIRED_COLUMNS = {"region", "sample", "yield"}
STATUSES = ("failed", "unvalidated", "preliminary", "synthetic", "asimov", "observed", "user-supplied",
            "validated-in-scope")  # contracts/vocab/core.json artifact_statuses


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="CSV with region,sample,yield[,uncertainty]")
    parser.add_argument("--precision", default=3, type=int, help="Digits after the decimal point")
    parser.add_argument("--status", required=True, choices=STATUSES, help="status label printed with the tables")
    parser.add_argument("--totals", action="store_true",
                        help="add a total row per region (sum; uncertainties in quadrature, independent samples)")
    return parser.parse_args()


def _number(text: str, what: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"{what} must be a finite number, got {text.strip()!r}")
    return value


def md(text: str) -> str:
    """A Markdown table cell: pipes escaped, line breaks turned into spaces."""
    return " ".join(str(text).replace("|", "\\|").split())


def format_yield(row: dict[str, str], precision: int) -> str:
    value = _number(row["yield"], "yield")
    uncertainty = (row.get("uncertainty") or "").strip()
    if uncertainty:
        return f"{value:.{precision}f} +/- {_number(uncertainty, 'uncertainty'):.{precision}f}"
    return f"{value:.{precision}f}"


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Yield CSV does not exist: {args.input}")

    with args.input.open(newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        if reader.fieldnames is None:
            raise ValueError("Yield CSV is missing a header row")
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"Yield CSV is missing required columns: {sorted(missing)}")

        rows_by_region: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in reader:
            rows_by_region[row["region"]].append(row)

    lines = [f"Status: {args.status}", ""]
    for region in sorted(rows_by_region):
        lines += [f"## {md(region)}", "", "| Sample | Yield |", "| --- | ---: |"]
        rows = sorted(rows_by_region[region], key=lambda item: item["sample"])
        for row in rows:
            lines.append(f"| {md(row['sample'])} | {format_yield(row, args.precision)} |")
        if args.totals:
            total = math.fsum(_number(r["yield"], "yield") for r in rows)
            uncs = [(r.get("uncertainty") or "").strip() for r in rows]
            cell = f"{total:.{args.precision}f}"
            if all(uncs):
                err = math.sqrt(math.fsum(_number(u, "uncertainty") ** 2 for u in uncs))
                cell += f" +/- {err:.{args.precision}f}"
            lines.append(f"| **Total** | {cell} |")
            lines += ["", "Total: yields summed; uncertainties added in quadrature (assumes independent samples)."]
        lines.append("")
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print(f"make_yield_table.py: error: {exc}", file=sys.stderr)
        sys.exit(2)
