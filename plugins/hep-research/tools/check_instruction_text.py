#!/usr/bin/env python3
"""Instruction-text conformance (HC-18, U12): shipped texts the agent follows must not direct it against a hard
constraint of the agentic plan (AGENTIC-R5 §13.4, MUST items M01-M25).

Each rule is a phrase that, where it occurs, tells the agent to unblind in the session, to hold unblinded data or real
sealed values, to treat an agent-run check as enforcement or authorization, or to bring private material onto an
unqualified host. The check reads the git-listed plugin files the agent can be pointed at: skills, profiles, adapters,
core, contracts, docs and README.md. CHANGELOG.md (history), tests and tools are not instructions and are skipped.

Usage: python3 tools/check_instruction_text.py     exit 0 ok, 1 findings; JSON report on stdout
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ("skills/", "profiles/", "adapters/", "core/", "contracts/", "docs/", "README.md", "VALIDATION.md")
SKIP = ("CHANGELOG.md",)
TEXT = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".def", ".sh"}
# (id, regex, why)
RULES = [
    ("M01", r"until unblinding is authorized by the user", "implies in-session unblinding (HC-04)"),
    ("M02", r"Unblind only when the user has authorized", "in-session unblinding (HC-04)"),
    ("M08", r"enforcement side of blinding", "an agent-run check called enforcement (HC-05)"),
    ("M08", r"--out /private/sealed\.json", "a sealed file written to an agent-readable path (HC-01)"),
    ("M09", r"this module only enforces", "an agent-run check called enforcement (HC-05)"),
    ("M10", r"(?<!not )\bblinding enforcement\b", "an agent-run check called enforcement (HC-05)"),
    ("M11", r"scan them with `scripts/audit_blinded_outputs\.py scan` before sharing", "agent scan with real sealed values gates sharing (HC-06)"),
    ("M14", r"private calibration constants from my local profile", "private data invited onto an unqualified host (HC-13)"),
    ("M17", r"unless the user supplies them", "internal material invited into the session (HC-13)"),
    ("M18", r"Upload the files a request needs", "unrestricted upload to an unqualified host (HC-13)"),
    ("M25", r"unblinding_authorization", "an agent-fillable field that reads as authorization (HC-04, HC-05)"),
]
# required text: (id, file, phrase)
REQUIRED = [
    ("M16", "contracts/stanzas/context-resolution.md", "agent_policy"),
    ("M13", "skills/hep-computing/SKILL.md", "Submission is unsandboxed execution"),
    ("M12", "skills/hep-computing/references/batch-scheduling.md", "Submission is unsandboxed execution"),
]


def files() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."], cwd=ROOT,
                             capture_output=True, text=True, check=True, timeout=120).stdout
        listed = [f for f in out.split("\0") if f]
    except (OSError, subprocess.SubprocessError):
        listed = []
    if not listed:  # a relocated copy outside git
        listed = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    return sorted(f for f in listed if f.startswith(SCOPE) and f not in SKIP and Path(f).suffix in TEXT
                  and "/tests/" not in f and not f.startswith("tests/"))


def check() -> dict:
    findings = []
    compiled = [(i, re.compile(rx, re.I), why) for i, rx, why in RULES]
    for rel in files():
        try:
            text = (ROOT / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for i, rx, why in compiled:
            for m in rx.finditer(text):
                findings.append({"rule": i, "file": rel, "line": text.count("\n", 0, m.start()) + 1, "why": why})
    for i, rel, phrase in REQUIRED:
        path = ROOT / rel
        if not path.exists() or phrase not in path.read_text(encoding="utf-8"):
            findings.append({"rule": i, "file": rel, "line": None, "why": f"required text missing: {phrase!r}"})
    return {"status": "fail" if findings else "pass", "rules": len(RULES) + len(REQUIRED), "findings": findings}


def main() -> int:
    rep = check()
    print(json.dumps(rep, indent=1))
    return 1 if rep["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
