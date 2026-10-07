#!/usr/bin/env python3
"""Host-neutrality check: skill text reaches plugin files through `<plugin root>/...`, never a host variable.

`<plugin root>` is defined in the shared context stanza of every SKILL.md (the folder two levels above it). Claude
Code and Codex both tell the model where a SKILL.md lives; only Claude Code expands `${CLAUDE_PLUGIN_ROOT}`.

Checks, over the git-listed plugin files (the tree outside git):
- no `${CLAUDE_PLUGIN_ROOT}` outside ALLOWED, which names each kept file and why;
- every `<plugin root>/<path>` reference names a file or folder that exists, outside ALLOWED_MISSING.

Usage: python3 tools/check_host_neutral.py     exit 0 ok, 1 findings; JSON report on stdout
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST_VAR = "${CLAUDE_PLUGIN_ROOT}"
ALLOWED = {
    "docs/architecture.md": "design record: describes how Claude Code resolves the variable",
    "docs/architecture-review.md": "design record: review of the host facts",
    "tools/check_host_neutral.py": "this check names the variable it looks for",
}
# files that name a <plugin root> path on purpose without it existing
ALLOWED_MISSING = {"tests/tools/test_check_layering.py": "planted fixture path for the layering check"}
REF = re.compile(r"<plugin root>/([\w./-]*[\w/])")
TEXT = {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".txt", ".toml", ".cfg", ".csv", ".C", ".cpp", ".h"}


def files() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."], cwd=ROOT,
                             capture_output=True, text=True, check=True, timeout=120).stdout
        listed = [f for f in out.split("\0") if f]
        if listed:
            return listed
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts]


def main() -> int:
    findings = []
    for rel in files():
        path = ROOT / rel
        if path.suffix not in TEXT or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if HOST_VAR in line and rel not in ALLOWED:
                findings.append({"file": rel, "line": n, "rule": "host-variable", "detail": HOST_VAR})
            for ref in REF.findall(line):
                if not (ROOT / ref.rstrip("/")).exists() and rel not in ALLOWED_MISSING:
                    findings.append({"file": rel, "line": n, "rule": "missing-path", "detail": f"<plugin root>/{ref}"})
    report = {"ok": not findings, "findings": findings, "allowed": ALLOWED, "allowed_missing": ALLOWED_MISSING}
    print(json.dumps(report, indent=1))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
