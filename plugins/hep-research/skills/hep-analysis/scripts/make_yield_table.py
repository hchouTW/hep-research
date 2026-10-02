#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


REQUIRED_COLUMNS = {"region", "sample", "yield"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a HEP yield CSV as Markdown tables.")
    parser.add_argument("--input", required=True, type=Path, help="CSV with region,sample,yield[,uncertainty]")
    parser.add_argument("--precision", default=3, type=int, help="Digits after the decimal point")
    return parser.parse_args()


def format_yield(row: dict[str, str], precision: int) -> str:
    value = float(row["yield"])
    uncertainty = row.get("uncertainty", "").strip()
    if uncertainty:
        return f"{value:.{precision}f} +/- {float(uncertainty):.{precision}f}"
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

    for region in sorted(rows_by_region):
        print(f"## {region}")
        print()
        print("| Sample | Yield |")
        print("| --- | ---: |")
        for row in sorted(rows_by_region[region], key=lambda item: item["sample"]):
            print(f"| {row['sample']} | {format_yield(row, args.precision)} |")
        print()


if __name__ == "__main__":
    main()
