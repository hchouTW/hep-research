#!/usr/bin/env python3
"""Packaging scan (task M5.4): nothing private, project-specific, cached or transcript-like ships in the plugin.

Scans the files a package would contain (git-tracked files when run in a checkout, else every file except caches):
- no symlinks, caches (__pycache__, *.pyc, .pytest_cache, .DS_Store) or editor/OS debris
- no model transcripts or session logs (*.jsonl, files named *transcript*), no grading rubrics or eval answer keys
- no project data: no hep-research-artifacts/ folder; project configs only as test fixtures
- no private paths (home directories, mounted project folders, temp session folders) or credentials
- no e-mail addresses other than the commit trailer address; no file over 2 MiB
Usage: python3 tools/check_packaging.py   Exit 0 clean, 1 findings. Output: JSON.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2 * 1024 * 1024
CACHE = re.compile(r"(^|/)(__pycache__|\.pytest_cache)(/|$)|\.pyc$|(^|/)\.DS_Store$")
TRANSCRIPT = re.compile(r"\.jsonl$|transcript", re.I)
RUBRIC = re.compile(r"rubric|answer[-_]?key|grading|prompts_eval|routing_eval", re.I)
PRIVATE = re.compile(r"/home/[a-z_][a-z0-9_-]*/|/Users/[A-Za-z0-9_.-]+/|C:\\\\Users\\\\|/mnt/project-files|/tmp/claude|\.claude/projects/")
SECRET = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|(api[_-]?key|token|password)\s*[:=]\s*['\"][^'\"\s]{8,}", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = {"noreply@anthropic.com"}
PLACEHOLDER_LOCAL = {"author", "name", "user", "you", "your.name", "first.last", "someone"}  # template placeholders
TEXT = {".py", ".md", ".json", ".csv", ".txt", ".yaml", ".yml", ".sh", ".C", ".toml", ".cfg", ".tex", ".bib"}


def files() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        tracked = [ROOT / f for f in out.split("\0") if f]
        if tracked:
            return tracked
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p for p in ROOT.rglob("*") if (p.is_file() or p.is_symlink()) and not CACHE.search(p.relative_to(ROOT).as_posix())]


def main() -> int:
    findings = []

    def add(path, rule, detail=""):
        findings.append({"file": path, "rule": rule, "detail": detail})

    fl = files()
    for p in fl:
        rel = p.relative_to(ROOT).as_posix()
        fixture = rel.startswith(("tests/", "contracts/fixtures/"))
        if p.is_symlink():
            add(rel, "symlink")
            continue
        if CACHE.search(rel):
            add(rel, "cache")
        if TRANSCRIPT.search(rel):
            add(rel, "transcript-or-log")
        if RUBRIC.search(rel):
            add(rel, "rubric-or-eval-key")
        if "hep-research-artifacts/" in rel:
            add(rel, "project-artifacts")
        if p.name == "hep-research.project.json" and not fixture:
            add(rel, "project-config-outside-fixtures")
        if p.stat().st_size > MAX_BYTES:
            add(rel, "large-file", f"{p.stat().st_size} bytes")
        if p.suffix in TEXT:
            text = p.read_text(encoding="utf-8", errors="replace")
            for rule, rx in (("private-path", PRIVATE), ("credential", SECRET)):
                m = rx.search(text)
                if m and not (rule == "private-path" and rel == "tools/check_packaging.py"):
                    add(rel, rule, m.group(0)[:60])
            for m in EMAIL.finditer(text):
                local = m.group(0).split("@")[0].lower()
                if m.group(0) not in EMAIL_OK and local not in PLACEHOLDER_LOCAL and not m.group(0).endswith((".example", "@example.com", "@example.org")):
                    add(rel, "email", m.group(0))
                    break
    rep = {"files_scanned": len(fl), "findings": findings, "ok": not findings}
    print(json.dumps(rep, indent=1))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
