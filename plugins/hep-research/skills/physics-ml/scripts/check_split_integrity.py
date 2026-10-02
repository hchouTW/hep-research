#!/usr/bin/env python3
"""Check train/validation/test splits for overlap, duplication, and group leakage.

Purpose: catch the failure that metrics cannot show. If the same record, user, patient,
or session appears in more than one split, the test set is measuring memorization - and
nothing about the numbers looks wrong. Group leakage is the most common serious split
error and is invisible in every metric.

What it does: reports exact ID overlap between every pair of splits, duplicate IDs
within a split, group leakage (a group whose members span splits), and temporal
violations (training records timestamped after validation or test records, when the
split is meant to be chronological). Exits nonzero when any check fails, so it can gate
a pipeline.

Usage notes / assumptions: standard library only; PyTorch is not required. Input is a
JSON object mapping split names to ID lists, optionally with "groups" (ID -> group) and
"timestamps" (ID -> comparable number). IDs must be exact - this does not detect
near-duplicates, which need a modality-appropriate similarity check (see
${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/references/data-strategy.md).
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/check_split_integrity.py ${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/assets/dataset_splits.example.json
"""

import argparse
import itertools
import json
import sys

RESERVED_KEYS = {"groups", "timestamps", "temporal_order", "_comment"}


def _split_ids(payload):
    splits = {}
    for name, values in payload.items():
        if name in RESERVED_KEYS:
            continue
        if not isinstance(values, list):
            raise ValueError(f"split {name!r} must be a list of IDs")
        splits[name] = [str(value) for value in values]
    if len(splits) < 2:
        raise ValueError("need at least two splits to check for leakage")
    return splits


def find_duplicates(ids):
    """IDs appearing more than once within one split."""
    seen, duplicates = set(), set()
    for value in ids:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def find_overlaps(splits):
    """Exact ID intersections between every pair of splits."""
    overlaps = {}
    for left, right in itertools.combinations(sorted(splits), 2):
        shared = set(splits[left]) & set(splits[right])
        if shared:
            overlaps[f"{left}|{right}"] = sorted(shared)
    return overlaps


def find_group_leakage(splits, groups):
    """Groups whose members appear in more than one split."""
    if not groups:
        return {}
    placement = {}
    for name, ids in splits.items():
        for value in ids:
            group = groups.get(value)
            if group is None:
                continue
            placement.setdefault(str(group), set()).add(name)
    return {group: sorted(names) for group, names in sorted(placement.items())
            if len(names) > 1}


def find_temporal_violations(splits, timestamps, order):
    """Records in an earlier split timestamped after records in a later split.

    `order` names the intended chronological sequence, e.g. ["train", "val", "test"].
    """
    if not timestamps or not order:
        return {}
    present = [name for name in order if name in splits]
    bounds = {}
    for name in present:
        values = [timestamps[value] for value in splits[name] if value in timestamps]
        if values:
            bounds[name] = (min(values), max(values))

    violations = {}
    for earlier, later in itertools.combinations(present, 2):
        if earlier not in bounds or later not in bounds:
            continue
        if bounds[earlier][1] > bounds[later][0]:
            violations[f"{earlier}|{later}"] = {
                "latest_in_earlier": bounds[earlier][1],
                "earliest_in_later": bounds[later][0],
                "overlapping_ids": sorted(
                    value for value in splits[earlier]
                    if value in timestamps and timestamps[value] > bounds[later][0]),
            }
    return violations


def check(payload):
    """Run every check and return a report with an overall pass/fail."""
    splits = _split_ids(payload)
    groups = payload.get("groups") or {}
    timestamps = payload.get("timestamps") or {}
    order = payload.get("temporal_order") or []
    if not isinstance(groups, dict) or not isinstance(timestamps, dict):
        raise ValueError("'groups' and 'timestamps' must be objects mapping ID -> value")

    duplicates = {name: found for name, ids in splits.items()
                  if (found := find_duplicates(ids))}
    overlaps = find_overlaps(splits)
    group_leakage = find_group_leakage(splits, {str(k): v for k, v in groups.items()})
    temporal = find_temporal_violations(
        splits, {str(k): v for k, v in timestamps.items()}, order)

    return {
        "splits": {name: len(ids) for name, ids in splits.items()},
        "unique_counts": {name: len(set(ids)) for name, ids in splits.items()},
        "duplicates_within_split": duplicates,
        "overlaps_between_splits": overlaps,
        "group_leakage": group_leakage,
        "temporal_violations": temporal,
        "groups_checked": bool(groups),
        "timestamps_checked": bool(timestamps and order),
        "passed": not (duplicates or overlaps or group_leakage or temporal),
    }


def _format(report):
    lines = ["Splits:"]
    for name, count in report["splits"].items():
        unique = report["unique_counts"][name]
        suffix = "" if unique == count else f"  ({unique} unique)"
        lines.append(f"  {name:<10} {count:>8}{suffix}")
    lines.append("")

    def section(title, contents, describe):
        if contents:
            lines.append(f"FAIL  {title}:")
            for key, value in list(contents.items())[:10]:
                lines.append(f"        {describe(key, value)}")
            if len(contents) > 10:
                lines.append(f"        ... and {len(contents) - 10} more")
        else:
            lines.append(f"ok    {title}: none")

    section("duplicate IDs within a split", report["duplicates_within_split"],
            lambda k, v: f"{k}: {len(v)} duplicated ID(s), e.g. {v[:3]}")
    section("ID overlap between splits", report["overlaps_between_splits"],
            lambda k, v: f"{k.replace('|', ' and ')}: {len(v)} shared, e.g. {v[:3]}")
    if report["groups_checked"]:
        section("group leakage across splits", report["group_leakage"],
                lambda k, v: f"group {k!r} appears in {', '.join(v)}")
    else:
        lines.append("skip  group leakage: no 'groups' mapping supplied "
                     "(the most common serious split error goes unchecked)")
    if report["timestamps_checked"]:
        section("temporal ordering", report["temporal_violations"],
                lambda k, v: (f"{k.replace('|', ' before ')}: "
                              f"{len(v['overlapping_ids'])} record(s) after "
                              f"{v['earliest_in_later']}"))
    else:
        lines.append("skip  temporal ordering: no 'timestamps' + 'temporal_order' supplied")

    lines.append("")
    lines.append("PASSED" if report["passed"] else "FAILED - see the checks above")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("splits", help="JSON file mapping split names to ID lists")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        with open(args.splits, encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("splits file must contain a JSON object")
        report = check(payload)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.exit(f"error: {exc}")

    print(json.dumps(report, indent=2) if args.json else _format(report))
    if not report["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
