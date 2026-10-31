#!/usr/bin/env python3
"""
build_lit_matrix.py -- turn a CSV of paper reading notes into a formatted
markdown comparison table for a literature review or related-work section.

Reads a CSV with an arbitrary header row (column names are flexible -- e.g.
key,year,method,dataset,result,notes) and writes a GitHub-flavored markdown
table with the same columns, optionally sorted by one of them.

Read-only with respect to the input; only ever writes the single output file
(or stdout). Standard library only (csv module).

--require-provenance (Com4): the CSV must have an `identifier` column (arXiv:YYMM.NNNNN, doi:10.x/..., inspire:NNN or
isbn:...) and a `read_level` column holding one of the plugin's verification levels (not-verified, not-opened,
metadata-only, abstract+metadata, page, full-text; contracts/vocab/core.json); every row that lacks either is listed on
stderr and the run exits 1, so a matrix never presents a paper nobody opened as if it had been read.

Exit codes: 0 written; 1 a row without a valid identifier or read level (--require-provenance); 2 bad input.

Usage:
    python3 build_lit_matrix.py notes.csv --require-provenance
    python3 build_lit_matrix.py notes.csv
    python3 build_lit_matrix.py notes.csv --sort-by year
    python3 build_lit_matrix.py notes.csv --sort-by year --descending -o lit_matrix.md
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
import csv
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from contracts.communication_project import output_aliases_input  # noqa: E402


def read_rows(csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    # utf-8-sig drops the byte-order mark Excel writes, which would otherwise
    # become part of the first column name.
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("no header row (empty file?)")
        fieldnames = list(reader.fieldnames)
        rows = []
        for lineno, row in enumerate(reader, start=2):
            extra = row.pop(None, None)  # cells beyond the header
            if extra:
                print(f"warning: {csv_path}: row {lineno} has {len(extra)} cell(s) more than the "
                      f"header; they are dropped", file=sys.stderr)
            # A short row gives None for the missing cells.
            rows.append({k: ("" if v is None else v) for k, v in row.items()})
    if len(fieldnames) == 1 and any(d in fieldnames[0] for d in ";\t"):
        print(f"warning: {csv_path} parsed as a single column '{fieldnames[0]}'; the file looks "
              f"semicolon- or tab-separated, but this script expects commas", file=sys.stderr)
    return fieldnames, rows


PLUGIN = Path(__file__).resolve().parents[3]
IDENTIFIER = re.compile(r"^(arxiv:(\d{4}\.\d{4,5}(v\d+)?|[a-z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?)|doi:10\.\d{4,9}/\S+"
                        r"|inspire:\d+|isbn:[\d-]{10,17}X?)$", re.I)


def read_levels() -> list[str]:
    vocab = json.loads((PLUGIN / "contracts" / "vocab" / "core.json").read_text(encoding="utf-8"))
    return list(vocab["vocabularies"]["verification_levels"])


def provenance_problems(fieldnames: list[str], rows: list[dict[str, str]]) -> list[str]:
    """One line per row whose identifier or read level is missing or not recognized."""
    levels = read_levels()
    key = fieldnames[0]
    out = []
    for row in rows:
        problems = []
        ident = row.get("identifier", "").strip()
        if not IDENTIFIER.match(ident):
            problems.append(f"identifier {ident!r} is not arXiv:..., doi:..., inspire:... or isbn:...")
        level = row.get("read_level", "").strip()
        if level not in levels:
            problems.append(f"read_level {level!r} is not one of {levels}")
        if problems:
            out.append(f"row {row.get(key, '?')}: " + "; ".join(problems))
    return out


def sort_rows(rows: list[dict[str, str]], sort_by: str | None, descending: bool) -> list[dict[str, str]]:
    if not sort_by:
        return rows

    def sort_key(row: dict[str, str]):
        value = row.get(sort_by, "")
        # Sort numerically when possible (e.g. a "year" column), else as text.
        try:
            return (0, float(value))
        except (TypeError, ValueError):
            return (1, value)

    return sorted(rows, key=sort_key, reverse=descending)


def escape_cell(value: str) -> str:
    # Markdown table cells can't contain a literal, unescaped pipe or newline.
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()


def to_markdown_table(fieldnames: list[str], rows: list[dict[str, str]]) -> str:
    header = "| " + " | ".join(escape_cell(name) for name in fieldnames) + " |"
    separator = "| " + " | ".join("---" for _ in fieldnames) + " |"
    body_lines = [
        "| " + " | ".join(escape_cell(row.get(col, "")) for col in fieldnames) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body_lines])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", type=Path, help="Input CSV of reading notes, one row per paper")
    parser.add_argument("--sort-by", default=None, help="Column name to sort by (e.g. 'year')")
    parser.add_argument("--descending", action="store_true", help="Sort descending instead of ascending")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Write markdown to this file instead of stdout")
    parser.add_argument("--require-provenance", action="store_true",
                        help="require identifier and read_level columns with valid values in every row (exit 1 if not)")
    args = parser.parse_args(argv)

    if not args.csv_path.is_file():
        print(f"error: {args.csv_path} is not a file", file=sys.stderr)
        return 2
    if args.output is not None and output_aliases_input(args.output, [args.csv_path]):
        print(f"error: --output {args.output} names the input CSV; the input is never overwritten", file=sys.stderr)
        return 2

    try:
        fieldnames, rows = read_rows(args.csv_path)
    except ValueError as exc:  # includes UnicodeDecodeError
        hint = " (save the CSV as UTF-8)" if isinstance(exc, UnicodeDecodeError) else ""
        print(f"error: {args.csv_path}: {exc}{hint}", file=sys.stderr)
        return 2

    if args.sort_by and args.sort_by not in fieldnames:
        print(f"error: --sort-by '{args.sort_by}' is not a column in {args.csv_path} "
              f"(columns: {', '.join(fieldnames)})", file=sys.stderr)
        return 2

    if args.require_provenance:
        missing = [c for c in ("identifier", "read_level") if c not in fieldnames]
        if missing:
            print(f"error: --require-provenance needs the column(s) {', '.join(missing)} in {args.csv_path}",
                  file=sys.stderr)
            return 2
        problems = provenance_problems(fieldnames, rows)
        if problems:
            for line in problems:
                print(f"error: {line}", file=sys.stderr)
            return 1

    rows = sort_rows(rows, args.sort_by, args.descending)
    table = to_markdown_table(fieldnames, rows)

    if args.output:
        args.output.write_text(table + "\n", encoding="utf-8")
        print(f"Wrote {len(rows)} row(s) to {args.output}")
    else:
        print(table)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
