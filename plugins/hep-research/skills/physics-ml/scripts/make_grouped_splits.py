#!/usr/bin/env python3
"""Build train/validation/test (or k-fold) assignments from a grouping key, never from rows.

Purpose: rows that share an event, run, luminosity block, detector period, simulation seed or generator parameter
point are correlated; splitting them across train and test measures memorization. This builds the split from the
grouping key so every group lands in exactly one split, and writes a manifest that
<plugin root>/skills/physics-ml/scripts/check_split_integrity.py checks directly.

What it does: reads a table of rows, groups them by --group-column, and assigns whole groups:
  --mode random-groups  shuffles the groups with --seed (deterministic for a seed) and fills train, val, test in that
                        order until each reaches its fraction of the rows (a group goes to the split its row-midpoint
                        falls in, so achieved fractions are approximate and are reported);
  --mode temporal       orders groups by the earliest --time-column value in each group (ties by group key) and gives
                        the earliest to train, then val, then test; the manifest carries "timestamps" and
                        "temporal_order" so the chronology is checked too;
  --folds K             (random-groups only) K grouped folds instead: shuffled groups are placed largest first into
                        the fold with the fewest rows; fold i is evaluated by the model trained on the other folds.
Group and ID values are compared the way check_split_integrity.py compares them (same function): surrounding whitespace
stripped, a number with a zero fraction written as an integer (1, 1.0 and "1" are one group), case folded
(--case-sensitive keeps case); booleans, lists and objects are refused. Time values must be numbers or ISO-8601
dates (datetime.fromisoformat: 2024-01-10, not 2024-1-10, which would sort as text). With --label-column the summary
gives class counts per split, and a split without events of a class is refused unless --allow-empty-class. A null group (missing, empty, NaN, or nan/null/none/na) is refused unless
--null-group-policy says what to do: own-group (each such row is its own group) or drop (left out of the manifest).

Input: a CSV file (header row), a JSON-lines file (.jsonl/.ndjson, one object per line), or a JSON file holding a list
  of objects (or {"rows": [...]}); --format overrides the extension. Every row needs a unique --id-column value.
Output: the split manifest (JSON) written to --out, in the format check_split_integrity.py reads: one ID list per
  split ("train"/"val"/"test", or "fold0".."foldK-1"), "groups" (ID -> normalized group), and, with --time-column,
  "timestamps" (plus "temporal_order" in temporal mode). A summary (mode, seed, requested and achieved fractions,
  groups and rows per split, null-group handling) is printed to stdout as strict JSON.
Exit codes: 0 manifest written, 2 bad input (unreadable table, missing column, duplicate ID, null groups without a
  policy, a time value that is not a number or ISO-8601 date, a boolean/list/object key, too few groups for the
  requested splits, a split without a class, bad fractions).
Usage notes / assumptions: standard library only; PyTorch is not required. The split is only as good as the key:
  choose the coarsest key that carries correlation (see <plugin root>/skills/physics-ml/references/ml-analysis.md).
Run: python3 <plugin root>/skills/physics-ml/scripts/make_grouped_splits.py rows.csv --id-column event --group-column run --out splits.json --seed 1
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_split_integrity import canonical_key, parse_timestamp  # noqa: E402  (one normalization for both tools)

SPLITS = ("train", "val", "test")
NULL_MARKERS = {"", "nan", "null", "none", "na"}


class InputError(ValueError):
    """Bad input: exit 2."""


def normalize_key(value, case_sensitive=False):
    try:
        return canonical_key(value, case_sensitive)
    except ValueError as exc:
        raise InputError(str(exc)) from None


def is_null(value):
    if value is None:
        return True
    if isinstance(value, float) and value != value:
        return True
    return isinstance(value, str) and value.strip().casefold() in NULL_MARKERS


def read_rows(path, fmt=None):
    """List of dict rows from CSV, JSON lines, or a JSON list (or {"rows": [...]})."""
    path = Path(path)
    fmt = fmt or {".csv": "csv", ".jsonl": "jsonl", ".ndjson": "jsonl"}.get(path.suffix.lower(), "json")
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            if fmt == "csv":
                rows = list(csv.DictReader(handle))
            elif fmt == "jsonl":
                rows = [json.loads(line) for line in handle if line.strip()]
            else:
                rows = json.load(handle)
                if isinstance(rows, dict):
                    rows = rows.get("rows")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, csv.Error) as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise InputError("the table must be a list of objects (rows)")
    if not rows:
        raise InputError("the table has no rows")
    return rows


def _time_value(value, row_id):
    """(sort key, value written to the manifest) for a time cell; refuses anything but numbers and ISO-8601 dates."""
    if is_null(value):
        raise InputError(f"row {row_id!r} has no time value")
    try:
        kind, key = parse_timestamp(value, row_id)
    except ValueError as exc:
        raise InputError(f"row {row_id!r}: {exc}") from None
    if kind == "number":
        shown = int(key) if isinstance(key, float) and key.is_integer() and isinstance(value, str) and \
            "." not in value and "e" not in value.lower() else key
        return key, shown
    return key, str(value).strip()


def collect_groups(rows, id_col, group_col, time_col=None, null_policy=None, case_sensitive=False):
    """Map group -> list of IDs (in input order), plus timestamps and null-group bookkeeping."""
    groups, group_of, times, shown = {}, {}, {}, {}
    null_rows, dropped = [], []
    for index, row in enumerate(rows):
        if id_col not in row:
            raise InputError(f"row {index} has no column {id_col!r}")
        if group_col not in row:
            raise InputError(f"row {index} has no column {group_col!r}")
        if is_null(row[id_col]):
            raise InputError(f"row {index} has an empty ID")
        rid = normalize_key(row[id_col], case_sensitive)
        if rid in group_of or rid in dropped:
            raise InputError(f"duplicate ID {rid!r} (after stripping whitespace"
                             f"{'' if case_sensitive else ' and folding case'})")
        raw_group = row[group_col]
        if is_null(raw_group):
            null_rows.append(rid)
            if null_policy == "drop":
                dropped.append(rid)
                continue
            if null_policy != "own-group":
                continue  # refused below, after counting all of them
            group = f"<null>:{rid}"
        else:
            group = normalize_key(raw_group, case_sensitive)
        if time_col is not None:
            if time_col not in row:
                raise InputError(f"row {index} has no column {time_col!r}")
            times[rid], shown[rid] = _time_value(row[time_col], rid)
        group_of[rid] = group
        groups.setdefault(group, []).append(rid)
    if null_rows and null_policy is None:
        raise InputError(f"{len(null_rows)} row(s) have a null or empty group (e.g. {null_rows[:3]}); "
                         "pass --null-group-policy own-group or drop")
    kinds = {isinstance(t, (int, float)) for t in times.values()}
    if len(kinds) > 1:
        raise InputError("time values mix numbers and dates; they cannot be ordered")
    return groups, group_of, times, {"null_group_rows": len(null_rows), "policy": null_policy,
                                     "dropped_rows": len(dropped), "shown_times": shown}


def _fill(ordered, groups, fractions):
    """Assign groups, in order, to the split whose cumulative row interval contains the group's row midpoint."""
    total = sum(len(groups[g]) for g in ordered)
    bounds, acc = [], 0.0
    for frac in fractions:
        acc += frac
        bounds.append(acc * total)
    assignment = {name: [] for name in SPLITS}
    cumulative = 0
    for group in ordered:
        size = len(groups[group])
        mid = cumulative + size / 2.0
        index = next((i for i, b in enumerate(bounds) if mid < b), len(bounds) - 1)
        while fractions[index] == 0:  # never land in a split the user switched off
            index -= 1
        assignment[SPLITS[index]].append(group)
        cumulative += size
    return {name: gs for name, gs in assignment.items() if fractions[SPLITS.index(name)] > 0}


def _folds(ordered, groups, k):
    by_size = sorted(ordered, key=lambda g: -len(groups[g]))  # stable: the seeded shuffle breaks ties
    folds = [[] for _ in range(k)]
    rows = [0] * k
    for group in by_size:
        target = min(range(k), key=lambda i: (rows[i], i))
        folds[target].append(group)
        rows[target] += len(groups[group])
    return {f"fold{i}": gs for i, gs in enumerate(folds)}


def make_splits(rows, id_col, group_col, time_col=None, fractions=(0.6, 0.2, 0.2), seed=0, mode="random-groups",
                folds=None, null_policy=None, case_sensitive=False, label_col=None, allow_empty_class=False):
    """Return (manifest, summary); raises InputError on bad input."""
    if mode not in ("random-groups", "temporal"):
        raise InputError(f"unknown mode {mode!r}")
    if mode == "temporal" and time_col is None:
        raise InputError("--mode temporal needs --time-column")
    if folds is not None:
        if mode != "random-groups":
            raise InputError("--folds works with --mode random-groups only")
        if folds < 2:
            raise InputError("--folds must be at least 2")
    else:
        if len(fractions) != 3 or any((not math.isfinite(f)) or f < 0 for f in fractions):
            raise InputError("fractions must be three finite non-negative numbers (train val test)")
        if abs(sum(fractions) - 1.0) > 1e-6:
            raise InputError(f"fractions must sum to 1 (got {sum(fractions):.6g})")
        if sum(f > 0 for f in fractions) < 2 or fractions[0] == 0:
            raise InputError("need a positive train fraction and at least one other positive fraction")

    groups, group_of, times, nulls = collect_groups(rows, id_col, group_col, time_col, null_policy, case_sensitive)
    shown_times = nulls.pop("shown_times")
    if not groups:
        raise InputError("no rows left after applying the null-group policy")
    keys = sorted(groups)
    if mode == "temporal":
        first = {g: min(times[i] for i in groups[g]) for g in keys}
        ordered = sorted(keys, key=lambda g: (first[g], g))
    else:
        ordered = list(keys)
        random.Random(seed).shuffle(ordered)

    if folds is not None:
        assignment = _folds(ordered, groups, folds)
    else:
        assignment = _fill(ordered, groups, list(fractions))
    needed = len(assignment)
    if len(groups) < needed:
        raise InputError(f"{len(groups)} group(s) cannot fill {needed} splits; use fewer splits or a finer key")
    empty = [name for name, gs in assignment.items() if not gs]
    if empty:
        raise InputError(f"split(s) {empty} received no group: the groups are too few or too unequal in size for "
                         "these fractions; adjust --fractions or use a finer grouping key")

    manifest = {name: [rid for g in gs for rid in groups[g]] for name, gs in assignment.items()}
    manifest["groups"] = dict(sorted(group_of.items()))
    if times:
        manifest["timestamps"] = dict(sorted(shown_times.items()))
    if mode == "temporal":
        manifest["temporal_order"] = list(assignment)

    total = sum(len(ids) for ids in groups.values())
    per_split = {name: {"groups": len(gs), "rows": len(manifest[name]),
                        "fraction": len(manifest[name]) / total} for name, gs in assignment.items()}
    empty_class = []
    if label_col is not None:
        label_of = {}
        for index, row in enumerate(rows):
            if label_col not in row:
                raise InputError(f"row {index} has no column {label_col!r}")
            label_of[normalize_key(row[id_col], case_sensitive)] = normalize_key(row[label_col], True)
        classes = sorted({label_of[rid] for ids in groups.values() for rid in ids})
        for name in assignment:
            counts = {c: 0 for c in classes}
            for rid in manifest[name]:
                counts[label_of[rid]] += 1
            per_split[name]["class_counts"] = counts
            empty_class += [f"{name}:{c}" for c, n in counts.items() if n == 0]
        if empty_class and not allow_empty_class:
            raise InputError(f"split(s) without events of a class: {empty_class}; a classifier cannot be trained or "
                             "evaluated on such a split. Use a finer grouping key or other fractions, or pass "
                             "--allow-empty-class to accept it")
    overlapping_time = []
    if mode == "temporal":
        names = list(assignment)
        for earlier, later in zip(names, names[1:]):
            latest = max(times[i] for i in manifest[earlier])
            earliest = min(times[i] for i in manifest[later])
            if latest > earliest:
                overlapping_time.append(f"{earlier}|{later}")
    summary = {
        "mode": mode, "seed": seed if mode == "random-groups" else None,
        "folds": folds, "requested_fractions": None if folds else dict(zip(SPLITS, fractions)),
        "id_column": id_col, "group_column": group_col, "time_column": time_col,
        "case_sensitive": case_sensitive,
        "input_rows": len(rows), "rows_assigned": total, "groups": len(groups),
        "null_groups": nulls, "splits": per_split,
        "time_ranges_overlap": overlapping_time,
        "label_column": label_col, "empty_classes": empty_class,
        "note": ("groups span overlapping time ranges, so check_split_integrity.py will report a temporal violation"
                 if overlapping_time else "check the manifest with check_split_integrity.py --strict"),
    }
    return manifest, summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("table", help="CSV, JSON-lines, or JSON list of rows")
    ap.add_argument("--id-column", required=True)
    ap.add_argument("--group-column", required=True, help="run, event, period, seed, parameter point, ...")
    ap.add_argument("--time-column", help="time or period order (required by --mode temporal): numbers or ISO-8601 "
                    "dates (2024-01-10); anything else is refused")
    ap.add_argument("--label-column", help="class label: report class counts per split and refuse a split that has "
                    "no events of a class")
    ap.add_argument("--allow-empty-class", action="store_true", help="accept a split without events of a class")
    ap.add_argument("--mode", choices=("random-groups", "temporal"), default="random-groups")
    ap.add_argument("--fractions", type=float, nargs=3, default=(0.6, 0.2, 0.2), metavar=("TRAIN", "VAL", "TEST"))
    ap.add_argument("--folds", type=int, help="K grouped folds instead of train/val/test")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--null-group-policy", choices=("own-group", "drop"),
                    help="what to do with rows whose group is null or empty (default: refuse)")
    ap.add_argument("--case-sensitive", action="store_true", help="keep case when comparing IDs and groups")
    ap.add_argument("--format", choices=("csv", "jsonl", "json"), help="override the format from the extension")
    ap.add_argument("--out", required=True, help="where to write the split manifest (JSON)")
    args = ap.parse_args(argv)
    try:
        rows = read_rows(args.table, args.format)
        manifest, summary = make_splits(rows, args.id_column, args.group_column, args.time_column,
                                        tuple(args.fractions), args.seed, args.mode, args.folds,
                                        args.null_group_policy, args.case_sensitive, args.label_column,
                                        args.allow_empty_class)
        text = json.dumps(manifest, indent=1, allow_nan=False)
        summary["manifest"] = str(args.out)
        try:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            raise InputError(f"cannot write {args.out}: {exc}") from exc
    except InputError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    print(json.dumps(summary, indent=1, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
