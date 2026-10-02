#!/usr/bin/env python3
"""Mark experiment-specific passages in moved Markdown as example blocks (M2 layering follow-up to the move commit).

For each hard-coded-experiment-name finding of tools/check_layering.py in a Markdown file, wraps the smallest
enclosing Markdown block in <!-- example: ... --> ... <!-- /example -->: the whole fenced code block, the whole
table, or the paragraph / list item (contiguous non-blank lines). Worked example task files under
skills/*/examples/ are wrapped whole, since they are examples by purpose. Text is unchanged;
only comment lines are inserted. Python findings are not handled here (they are reworded by hand).

Usage: python3 tasks/hep-research/scripts/mark_example_blocks.py [--dry-run]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3] / "plugins" / "hep-research"
OPEN = "<!-- example: experiment-specific illustration -->"
CLOSE = "<!-- /example -->"
WHOLE = re.compile(r"^skills/[^/]+/examples/[^/]+-task\.md$")


def findings():
    p = subprocess.run([sys.executable, "tools/check_layering.py"], cwd=PLUGIN, capture_output=True, text=True)
    out = {}
    for v in json.loads(p.stdout)["violations"]:
        if v["rule"] == "hard-coded-experiment-name" and v["file"].endswith(".md"):
            out.setdefault(v["file"], set()).add(v["line"])
    return out


def fences(lines):
    spans, start = [], None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith(("```", "~~~")):
            if start is None:
                start = i
            else:
                spans.append((start, i))
                start = None
    return spans


def block(lines, i, fence_spans):
    for a, b in fence_spans:
        if a <= i <= b:
            return a, b
    is_table = lines[i].lstrip().startswith("|")
    a = i
    while a > 0 and lines[a - 1].strip() and (lines[a - 1].lstrip().startswith("|") == is_table or not is_table):
        if not is_table and re.match(r"\s*([-*+]|\d+\.)\s", lines[a]) and not lines[a].startswith((" ", "\t")):
            break  # a top-level list item starts here
        if lines[a - 1].lstrip().startswith("#"):
            break
        a -= 1
    b = i
    while b + 1 < len(lines) and lines[b + 1].strip() and (lines[b + 1].lstrip().startswith("|") == is_table or not is_table):
        if not is_table and re.match(r"([-*+]|\d+\.)\s", lines[b + 1]):
            break
        if lines[b + 1].lstrip().startswith("#"):
            break
        b += 1
    return a, b


def mark(rel, line_nos):
    path = PLUGIN / rel
    lines = path.read_text(encoding="utf-8").split("\n")
    if WHOLE.match(rel):
        start = 0
        end = len(lines) - 1
        while end > start and not lines[end].strip():
            end -= 1
        spans = [(start, end)]
    else:
        fs = fences(lines)
        spans = sorted(block(lines, n - 1, fs) for n in line_nos)
        merged = []
        for a, b in spans:
            if merged and a <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
            else:
                merged.append((a, b))
        spans = merged
    for a, b in reversed(spans):
        lines.insert(b + 1, CLOSE)
        lines.insert(a, OPEN)
    return "\n".join(lines), len(spans)


def main(argv):
    total = 0
    for rel, nos in sorted(findings().items()):
        text, n = mark(rel, nos)
        total += n
        print(f"{rel}: {n} block(s)")
        if "--dry-run" not in argv:
            (PLUGIN / rel).write_text(text, encoding="utf-8")
    print(f"total blocks: {total}")


if __name__ == "__main__":
    main(sys.argv[1:])
