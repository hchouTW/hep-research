#!/usr/bin/env python3
"""Insert the interpreter guard block into every skill script listed in tools/skill_scripts.json.

The block (tools/skill_scripts.py GUARD_BLOCK, with the script's depth N) goes after the module docstring and any
`from __future__` import, before every other import; a shebang and leading comments stay first. Existing sys.path
lines are left alone. Idempotent: a script whose block is already correct is not touched, and a block with a wrong
depth or body is replaced in place by the current one, so a second run changes nothing. On a merge conflict in a
listed script, resolve the code and rerun this script instead of editing the block by hand.

Usage: python3 tools/insert_interpreter_guard.py [--check] [--root PLUGIN_ROOT]
--check writes nothing and exits 1 when a listed script lacks a correct block. Exit 0 ok, 1 (--check) out of date,
2 bad usage or an unreadable list. Prints JSON with a status key. Standard library only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tool(root: Path):
    spec = importlib.util.spec_from_file_location("skill_scripts", root / "tools" / "skill_scripts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def with_guard(source: str, depth: int, tool) -> str:
    """source with exactly one current guard block in its place."""
    block = tool.guard_block(depth).splitlines(keepends=True)
    lines = source.splitlines(keepends=True)
    first = block[0].rstrip("\n")
    for i, line in enumerate(lines):  # drop an existing block (any depth or body) and one blank line after it
        if line.rstrip("\n") == first:
            end = i + 1
            while end < len(lines) and (lines[end].startswith("    ") or lines[end].strip() == ""):
                if lines[end].strip() == "":
                    end += 1
                    break
                end += 1
            del lines[i:end]
            break
    at = tool.guard_insertion_line("".join(lines))
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    rest = lines[at:]
    inserted = block + (["\n"] if rest and rest[0].strip() else [])
    return "".join(lines[:at] + inserted + rest)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--check", action="store_true", help="exit 1 when a listed script lacks a correct guard block")
    ap.add_argument("--root", type=Path, default=ROOT, help="plugin root (default: this file's plugin)")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    tool = _tool(root)
    try:
        scripts = json.loads((root / "tools" / "skill_scripts.json").read_text(encoding="utf-8"))["scripts"]
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "rejected", "message": f"cannot read tools/skill_scripts.json: {exc}"}))
        return 2
    changed, problems = [], []
    for entry in scripts:
        path = root / entry["path"]
        source = path.read_text(encoding="utf-8")
        if not tool.guard_problems(source, entry["depth"]):
            continue
        if args.check:
            problems.append(entry["path"])
            continue
        updated = with_guard(source, entry["depth"], tool)
        left = tool.guard_problems(updated, entry["depth"])
        if left:
            problems.append(f"{entry['path']}: {'; '.join(left)}")
            continue
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(updated)
        changed.append(entry["path"])
    status = "failed" if problems else ("ok" if args.check or not changed else "written")
    print(json.dumps({"status": status, "scripts": len(scripts), "changed": len(changed), "problems": problems},
                     indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
