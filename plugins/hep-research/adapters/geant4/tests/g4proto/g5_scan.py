#!/usr/bin/env python3
"""Evidence for G5 (g4sim plan, Section 1): new C++ against every file of the Geant4 examples tree, with lines normalized
(comments and whitespace removed, trivial lines skipped), counting runs of K consecutive lines the two share.

This is evidence for the reviewer, never the confirmation, which a person gives in a VALIDATION entry. A positive control scans a
reformatted copy of one example file, and it must be found, or a count of zero means nothing.

Usage: g5_scan.py --examples DIR FILE... [--length K]   Prints JSON with a status key.
Exit 0 no shared run and the control found, 1 shared runs, or the control not found, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SUFFIXES = (".cc", ".hh", ".icc")
_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_TRIVIAL = re.compile(r"^(?:[{}();,]*|#(?:include|ifndef|define|endif|pragma).*|namespace\w*|public:|private:|protected:|else|return;|break;)$")


def normalized(text: str) -> list[str]:
    """Code lines with comments and all whitespace removed, trivial lines skipped."""
    lines = []
    for line in _COMMENT.sub("", text).splitlines():
        line = re.sub(r"\s+", "", line.split("//", 1)[0])
        if not _TRIVIAL.match(line):
            lines.append(line)
    return lines


def windows(lines: list[str], length: int) -> set[tuple]:
    return {tuple(lines[at:at + length]) for at in range(len(lines) - length + 1)}


def example_windows(root: Path, length: int) -> tuple[set, int]:
    found: set = set()
    files = 0
    for path in sorted(root.rglob("*")):
        if path.suffix in SUFFIXES and path.is_file():
            found |= windows(normalized(path.read_text(encoding="utf-8", errors="replace")), length)
            files += 1
    return found, files


def reformatted(text: str) -> str:
    """The control: the same code with its whitespace changed and its comments gone."""
    return "\n".join("    " + " ".join(line.split()) for line in _COMMENT.sub("", text).splitlines() if not line.strip().startswith("//"))


def control_file(root: Path) -> Path | None:
    candidates = sorted(path for path in root.rglob("*.cc") if path.is_file())
    return max(candidates[:200], key=lambda path: path.stat().st_size, default=None)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--length", type=int, default=3)
    parser.add_argument("files", type=Path, nargs="+")
    args = parser.parse_args(argv)
    try:
        known, count = example_windows(args.examples, args.length)
        shared = {str(path): sorted(windows(normalized(path.read_text(encoding="utf-8")), args.length) & known) for path in args.files}
    except OSError as err:
        print(json.dumps({"status": "error", "message": str(err)}))
        return 2
    if count == 0:
        print(json.dumps({"status": "error", "message": "no example file found"}))
        return 2
    sample = control_file(args.examples)
    control = len(windows(normalized(reformatted(sample.read_text(encoding="utf-8", errors="replace"))), args.length) & known)
    total = sum(len(item) for item in shared.values())
    clean = total == 0 and control > 0
    print(json.dumps({"status": "ok" if clean else "failed", "length": args.length, "example_files": count, "scanned": len(args.files),
                      "shared_runs": total, "by_file": {path: len(item) for path, item in shared.items()},
                      "first_shared": next(([list(run) for run in item[:2]] for item in shared.values() if item), []),
                      "control": str(sample), "control_shared_runs": control}, indent=1))
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
