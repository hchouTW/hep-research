#!/usr/bin/env python3
"""Mergeable reduction of time-sliced records: deduplicate by a stable key, then sum (C1).

Purpose: per-period (time-slice) records often reach an analysis split over many files, with a slice repeated at a
file boundary or in a resubmitted job. Summing them file by file counts such a slice twice. This tool keys every
record by a stable key (one column or several, e.g. run,slice), keeps one copy of identical duplicates, refuses a key
whose copies disagree, and only then sums the declared numeric columns, optionally per group (e.g. per era). See
<plugin root>/skills/hep-computing/references/analysis-data-pipelines.md, "Time-sliced records and mergeable
reductions".

Method: records are collected with their key, group and values; after deduplication they are sorted by key and summed
in that order, so a single run and a partitioned run give the same floating-point sums. Partitioned use goes through
core/partition: `partial` writes the JSON a local_partition.py worker writes to {out} (a list of records and a list of
sources), local_partition.py merges the chunks with `--rule records=concat --rule sources=concat`, and `finalize`
deduplicates and sums the merged records, recording the merge inputs (chunks merged and expected, the source digests)
so that a later run-lineage result binding can show the merge was complete.

Assumptions: the key identifies a time slice uniquely; identical copies of a slice are the same slice; the summed
columns are additive (counts, live times, sums of weights), never means, medians or rates.

Input: CSV with a header, JSON Lines (one object per line) or a JSON list of objects; numbers in the summed columns.
Usage:
  time_slice_reduction.py reduce FILE [FILE ...] --key COL[,COL] --sum COL[,COL] [--group-by COL] [--out OUT]
  time_slice_reduction.py partial (FILE ... | --file-list LIST --start I --stop J) --key ... --sum ... [--group-by COL]
                          --out OUT                       (a local_partition.py worker: files LIST[I:J])
  time_slice_reduction.py finalize MERGED_OR_PARTIAL [...] --key ... --sum ... [--group-by COL] [--out OUT]
  every subcommand takes --status LABEL (default unvalidated), echoed as status_label.
Output JSON: status (ok, rejected, incomplete), status_label, inputs, defaults_used; reduce and finalize add groups,
totals, n_records_unique, duplicates_removed, sources (path, sha256, rows, settings) and merge_inputs.
Exit codes: 0 ok; 2 bad input (unreadable file, missing key or column, non-numeric value, conflicting duplicates,
partials made with other settings); 3 the partition merge was incomplete. Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402


class InputError(ValueError):
    """Input that cannot be reduced; extra JSON fields go into the report."""

    def __init__(self, message: str, **extra):
        super().__init__(message)
        self.extra = extra


def _columns(text: str, what: str) -> list[str]:
    cols = [c.strip() for c in text.split(",") if c.strip()]
    if not cols:
        raise InputError(f"{what} names no column")
    return cols


def _read_rows(path: Path) -> tuple[list[dict], str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc.strerror or exc}") from None
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    stripped = text.lstrip()
    try:
        if path.suffix == ".csv" or not stripped.startswith(("{", "[")):
            rows = list(csv.DictReader(io.StringIO(text)))
        elif stripped.startswith("["):
            rows = json.loads(text)
        else:
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    except ValueError as exc:
        raise InputError(f"{path}: not CSV, JSON Lines or a JSON list ({exc})") from None
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise InputError(f"{path}: records must be objects")
    return rows, digest


def _number(value, where: str):
    if isinstance(value, bool):
        raise InputError(f"{where}: {value!r} is not a number")
    if isinstance(value, (int, float)):
        out = value
    else:
        text = str(value).strip()
        try:
            out = int(text)
        except ValueError:
            try:
                out = float(text)
            except ValueError:
                raise InputError(f"{where}: {value!r} is not a number") from None
    if isinstance(out, float) and not math.isfinite(out):
        raise InputError(f"{where}: {value!r} is not finite")
    return out


def _settings(args) -> dict:
    return {"key": _columns(args.key, "--key"), "sum": _columns(args.sum, "--sum"), "group_by": args.group_by}


def collect(paths: list[Path], settings: dict) -> tuple[list, list]:
    """(records [[key, group, {col: value}]], sources [{path, sha256, rows, settings}]) without deduplication."""
    records, sources = [], []
    for path in paths:
        rows, digest = _read_rows(path)
        for i, row in enumerate(rows):
            where = f"{path}:{i + 1}"
            key = []
            for col in settings["key"]:
                v = row.get(col)
                if v is None or str(v).strip() == "":
                    raise InputError(f"{where}: key column {col!r} is missing or empty")
                key.append(str(v).strip())
            group = ""
            if settings["group_by"]:
                g = row.get(settings["group_by"])
                if g is None or str(g).strip() == "":
                    raise InputError(f"{where}: group column {settings['group_by']!r} is missing or empty")
                group = str(g).strip()
            values = {}
            for col in settings["sum"]:
                if col not in row:
                    raise InputError(f"{where}: column {col!r} is missing")
                values[col] = _number(row[col], f"{where} {col}")
            records.append([key, group, values])
        sources.append({"path": str(path), "sha256": digest, "rows": len(rows), "settings": settings})
    return records, sources


def reduce_records(records: list, settings: dict) -> dict:
    """Deduplicate by key (identical copies kept once, differing copies refused), then sum in key order."""
    unique: dict[tuple, list] = {}
    duplicates, conflicts = 0, []
    for key, group, values in records:
        k = tuple(key)
        if k in unique:
            if unique[k] == [group, values]:
                duplicates += 1
            else:
                conflicts.append({"key": key, "first": unique[k], "other": [group, values]})
            continue
        unique[k] = [group, values]
    if conflicts:
        raise InputError("records with the same key differ: one time slice cannot have two values", conflicts=conflicts[:20],
                         n_conflicts=len(conflicts))
    groups: dict[str, dict] = {}
    totals = {col: 0 for col in settings["sum"]}
    for k in sorted(unique):
        group, values = unique[k]
        acc = groups.setdefault(group, {col: 0 for col in settings["sum"]})
        for col in settings["sum"]:
            acc[col] += values[col]
            totals[col] += values[col]
    return {"groups": {g: groups[g] for g in sorted(groups)}, "totals": totals, "n_records_unique": len(unique),
            "duplicates_removed": duplicates}


def _sources_digest(sources: list) -> str:
    return hashlib.sha256(json.dumps(sorted(s["sha256"] for s in sources)).encode()).hexdigest()


def _load_merge_inputs(paths: list[Path], settings: dict) -> tuple[list, list, dict]:
    """Records, sources and the merge record from a local_partition.py merge output or from partial files."""
    records, sources = [], []
    if len(paths) == 1:
        try:
            doc = json.loads(paths[0].read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InputError(f"cannot read {paths[0]}: {exc}") from None
        if isinstance(doc, dict) and "merged" in doc and "problems" in doc:  # core/partition merge output
            if doc.get("status") != "complete" or not isinstance(doc.get("merged"), dict):
                raise InputError("the partition merge is incomplete: no reduction from a partial merge",
                                 incomplete=True, problems=doc.get("problems", []))
            merged = doc["merged"]
            meta = {"kind": "core-partition-merge", "complete": True, "chunks_merged": doc.get("chunks_merged"),
                    "chunks_expected": doc.get("chunks_expected"), "merge_rules": doc.get("merge_rules", {}),
                    "merge_file_sha256": hashlib.sha256(paths[0].read_bytes()).hexdigest()}
            return list(merged.get("records", [])), list(merged.get("sources", [])), meta
    for path in paths:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise InputError(f"cannot read {path}: {exc}") from None
        if not isinstance(doc, dict) or not isinstance(doc.get("records"), list) or not isinstance(doc.get("sources"), list):
            raise InputError(f"{path}: not a partial (records and sources) nor a local_partition.py merge output")
        records += doc["records"]
        sources += doc["sources"]
    return records, sources, {"kind": "partials", "complete": True, "partials": len(paths)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("reduce", "partial", "finalize"):
        p = sub.add_parser(name)
        p.add_argument("files", nargs="*", type=Path)
        p.add_argument("--key", required=True, help="stable key column(s), comma-separated")
        p.add_argument("--sum", required=True, help="additive column(s) to sum, comma-separated")
        p.add_argument("--group-by", help="sum per value of this column (e.g. an era)")
        p.add_argument("--out", type=Path, required=name == "partial")
        add_status_argument(p)
        if name == "partial":
            p.add_argument("--file-list", type=Path, help="a text file with one input path per line")
            p.add_argument("--start", type=int)
            p.add_argument("--stop", type=int)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: (str(v) if isinstance(v, Path) else [str(x) for x in v] if isinstance(v, list) else v)
              for k, v in vars(args).items()}
    report: dict = {"status_label": args.status, "inputs": inputs,
                    "defaults_used": [k for k in ("status", "group_by") if f"--{k.replace('_', '-')}" not in given]}
    try:
        settings = _settings(args)
        files = list(args.files)
        if args.command == "partial" and args.file_list:
            if files or args.start is None or args.stop is None:
                raise InputError("--file-list needs --start and --stop and no positional files")
            try:
                listed = [Path(x.strip()) for x in args.file_list.read_text(encoding="utf-8").splitlines() if x.strip()]
            except OSError as exc:
                raise InputError(f"cannot read {args.file_list}: {exc.strerror or exc}") from None
            if not 0 <= args.start < args.stop <= len(listed):
                raise InputError(f"--start/--stop {args.start}:{args.stop} outside the {len(listed)} listed files")
            files = listed[args.start:args.stop]
        if not files:
            raise InputError("no input files")
        if args.command == "partial":
            records, sources = collect(files, settings)
            doc = {"records": records, "sources": sources, "n_rows_read": sum(s["rows"] for s in sources)}
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
            report.update(status="ok", out=str(args.out), n_rows_read=doc["n_rows_read"])
        else:
            if args.command == "reduce":
                records, sources = collect(files, settings)
                merge_inputs = {"kind": "single-run", "complete": True, "partials": 0}
            else:
                records, sources, merge_inputs = _load_merge_inputs(files, settings)
                other = [s["path"] for s in sources if s.get("settings") != settings]
                if other:
                    raise InputError("partials made with other --key/--sum/--group-by settings", sources=other)
            merge_inputs["sources_digest"] = _sources_digest(sources)
            report.update(reduce_records(records, settings))
            report.update(status="ok", sources=sources, merge_inputs=merge_inputs)
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    except InputError as exc:
        status = "incomplete" if exc.extra.pop("incomplete", False) else "rejected"
        report.update(status=status, error=str(exc), **exc.extra)
    except OSError as exc:
        report.update(status="rejected", error=f"cannot write {args.out}: {exc.strerror or exc}")
    print(json.dumps(report, indent=1))
    return exit_code(report["status"])


if __name__ == "__main__":
    sys.exit(main())
