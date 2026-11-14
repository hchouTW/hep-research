#!/usr/bin/env python3
"""Scoring side of T09, D3 stage 4: two helpers a job uses to read its own tools' output (re-review nits N-A and N-B of
d3-stage3-rereview.md). Standard library only; it reads text, never a product or a truth file.

classify CODE FILE (N-A): the outcome of one run of a tool that ends with a RESULT line (t09_truth_start.py,
t09_topology_readings.py), from its exit code and its stdout together. The last line must be `RESULT {json}` whose status is a
run status of core/status.py and whose exit_code is both the run's exit code and exit_code(status); then (0, ok) is `passed`,
(1, failed) `gate-failed`, (2, rejected) `rejected`, (2, error) `error`. Anything else is `crash`: no RESULT line (a bare
traceback exits 1 too, so the code alone cannot tell it from a failed gate), a RESULT line that is not the last, a code that
does not match its status, a signal. Prints the class; exits 0 whatever the class (the class is the answer), 2 on bad usage.

count-exact --spec SPEC LOG... (N-B): every line of the logs that starts with "PASS EQUAL " must match exactly one kind's
pattern in full (re.fullmatch: anchored at both ends), and every kind must count exactly its expected number. SPEC is JSON
{kind: {"pattern": regex, "expected": n}}. Prints per kind `COUNT kind n of expected`, each line no pattern matches as
`UNMATCHED line`, then the RESULT line; exit 0 (ok) when every count is exact and no line is unmatched, 1 (failed) otherwise,
2 (rejected) for a spec or log it cannot read. Exit codes are core/status.py's.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from core.status import RUN_STATUSES, exit_code  # noqa: E402

CLASSES = {("ok", 0): "passed", ("failed", 1): "gate-failed", ("rejected", 2): "rejected", ("error", 2): "error"}
PREFIX = "PASS EQUAL "


def classify(code: int, text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or not lines[-1].startswith("RESULT "):
        return "crash"
    try:
        doc = json.loads(lines[-1][len("RESULT "):])
    except ValueError:
        return "crash"
    if not isinstance(doc, dict):
        return "crash"
    status, stated = doc.get("status"), doc.get("exit_code")
    if status not in RUN_STATUSES or isinstance(stated, bool) or stated != code or RUN_STATUSES[status] != code:
        return "crash"
    return CLASSES.get((status, code), "crash")


def count_exact(lines, spec: dict):
    """(counts per kind, unmatched PASS EQUAL lines, ok)."""
    compiled = {kind: re.compile(entry["pattern"]) for kind, entry in spec.items()}
    counts = {kind: 0 for kind in spec}
    unmatched = []
    for line in lines:
        if not line.startswith(PREFIX):
            continue
        kinds = [kind for kind, rx in compiled.items() if rx.fullmatch(line)]
        if len(kinds) != 1:
            unmatched.append(line)
            continue
        counts[kinds[0]] += 1
    ok = not unmatched and all(counts[kind] == spec[kind]["expected"] for kind in spec)
    return counts, unmatched, ok


def _result(operation: str, status: str, reason: str) -> int:
    code = exit_code(status)
    print("RESULT " + json.dumps({"operation": operation, "status": status, "exit_code": code, "reason": reason}, sort_keys=True))
    return code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    c = sub.add_parser("classify", help="a run's outcome from its exit code and its stdout file")
    c.add_argument("code", type=int)
    c.add_argument("stdout")
    k = sub.add_parser("count-exact", help="PASS EQUAL lines counted by exact full-line patterns")
    k.add_argument("--spec", required=True)
    k.add_argument("logs", nargs="+")
    args = ap.parse_args(argv)
    if args.operation == "classify":
        try:
            text = Path(args.stdout).read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        print(classify(args.code, text))
        return 0
    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        if not (isinstance(spec, dict) and spec and all(isinstance(e, dict) and set(e) == {"pattern", "expected"}
                                                        and isinstance(e["pattern"], str) and isinstance(e["expected"], int)
                                                        for e in spec.values())):
            raise ValueError("spec must map each kind to exactly pattern (text) and expected (count)")
        lines = [line for path in args.logs for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines()]
        counts, unmatched, ok = count_exact(lines, spec)
    except (OSError, ValueError, re.error) as exc:
        return _result("count-exact", "rejected", str(exc))
    for kind, n in counts.items():
        print(f"COUNT {kind} {n} of {spec[kind]['expected']}")
    for line in unmatched:
        print(f"UNMATCHED {line}")
    return _result("count-exact", "ok" if ok else "failed", "" if ok else "a PASS EQUAL count is not exact or a line matches no pattern")


if __name__ == "__main__":
    sys.exit(main())
