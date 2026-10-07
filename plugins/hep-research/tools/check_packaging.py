#!/usr/bin/env python3
"""Packaging scan: nothing private, project-specific, cached or transcript-like ships in the plugin.

Scans the files a package would contain (git-tracked files when run in a checkout, else every file except caches):
- no symlinks, caches (__pycache__, *.pyc, .pytest_cache, .DS_Store) or editor/OS debris
- no model transcripts or session logs (*.jsonl, files named *transcript*), no grading rubrics or eval answer keys
- no project data: no hep-research-artifacts/ folder; project configs only as test fixtures
- no private paths (home directories, mounted project folders, temp session folders) or credentials
- no e-mail addresses other than the commit trailer address; no file over 2 MiB
- no restricted-site or personal-machine facts (EOS, AFS or AMS CVMFS paths, lxplus node names, home folders, local
  hostnames), no AMS Offline software identifiers, and no trace of the plugin's pre-release development repository
- no site facts in shipped batch-scheduler configs (JSON under adapters/ or examples/ with a slurm or htcondor
  backend or section): partition, account, QoS, constraint, gres, requirements and container image must be
  placeholders ("<...>") or start with "synthetic"; campaign_dir must not be an absolute path
- the README's stated package size ("about N files, X MB uncompressed") within 10% of the measured file count and
  byte total, so the figure an uploader relies on does not drift
Usage: python3 tools/check_packaging.py [--root PLUGIN_ROOT]   Exit 0 clean, 1 findings. Output: JSON.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_KEYS = ("partition", "account", "qos", "constraint", "gres", "requirements", "container_image")
MAX_BYTES = 2 * 1024 * 1024
CACHE = re.compile(r"(^|/)(__pycache__|\.pytest_cache|\.hypothesis)(/|$)|\.pyc$|(^|/)\.DS_Store$")
TRANSCRIPT = re.compile(r"\.jsonl$|transcript", re.I)
RUBRIC = re.compile(r"rubric|answer[-_]?key|grading|prompts_eval|routing_eval", re.I)
PRIVATE = re.compile(r"/home/[a-z_][a-z0-9_-]*/|/Users/[A-Za-z0-9_.-]+/|C:\\\\Users\\\\|/mnt/project-files|/tmp/claude|\.claude/projects/")
SECRET = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|(api[_-]?key|token|password)\s*[:=]\s*['\"][^'\"\s]{8,}", re.I)
RESTRICTED = re.compile(r"/eos/|/afs/|/cvmfs/ams|lxplus\d+|/Users/|-Users-|/tmp/[a-z]{3,}[a-z0-9]*/|hitronhub|[A-Za-z0-9-]+\.local\b"
                        r"|AMSChain|AMSEventR|AMSDataDir|\bvdev\b|ISS\.B\d+")
LEGACY = re.compile(r"agentic[-_]ai[-_]skills|3e995a4|\.legacy/|legacy_id|\bported from|migrated (from|routing)"
                    r"|legacy [`a-z-]+ (skill|ledger|spec|tests?|sample|scripts?|repo|checkout)|migration[- ]map|ams-analysis|fetch_legacy", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = {"noreply@anthropic.com"}
PLACEHOLDER_LOCAL = {"author", "name", "user", "you", "your.name", "first.last", "someone"}  # template placeholders
TEXT = {".py", ".md", ".json", ".csv", ".txt", ".yaml", ".yml", ".sh", ".C", ".cpp", ".h", ".hpp", ".toml", ".cfg", ".tex", ".bib"}


def files() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."], cwd=ROOT, capture_output=True, text=True, check=True, timeout=120).stdout
        tracked = [ROOT / f for f in out.split("\0") if f and ((ROOT / f).exists() or (ROOT / f).is_symlink())]  # not deleted in the worktree
        if tracked:
            return tracked
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p for p in ROOT.rglob("*") if (p.is_file() or p.is_symlink()) and not CACHE.search(p.relative_to(ROOT).as_posix())]


def batch_site_facts(obj) -> list[str]:
    """Site keys in a batch config that hold neither a placeholder nor a synthetic value."""
    if not isinstance(obj, dict) or not (obj.get("backend") in ("slurm", "htcondor") or "slurm" in obj or "htcondor" in obj):
        return []
    bad = []
    for scope in (obj, obj.get("slurm"), obj.get("htcondor")):
        if not isinstance(scope, dict):
            continue
        for k in SITE_KEYS:
            v = scope.get(k)
            if isinstance(v, str) and not (v.startswith("<") and v.endswith(">")) and not v.lower().startswith("synthetic"):
                bad.append(f"{k}={v}")
        cd = scope.get("campaign_dir")
        if isinstance(cd, str) and cd.startswith(("/", "~")):
            bad.append(f"campaign_dir={cd}")  # an absolute path names someone's file system
    return bad


SIZE_RE = re.compile(r"\(about\s+([\d,]+)\s+files,\s+([\d.]+)\s+MB\s+uncompressed\)")
SIZE_MARGIN = 0.10


def size_drift(fl: list[Path]) -> list[str]:
    """Problems with the README's size statement: missing, or more than SIZE_MARGIN off the measured package."""
    readme = ROOT / "README.md"
    m = SIZE_RE.search(readme.read_text(encoding="utf-8")) if readme.is_file() else None
    if not m:
        return ["README.md has no '(about N files, X MB uncompressed)' statement"]
    n_said, mb_said = int(m.group(1).replace(",", "")), float(m.group(2))
    real = [p for p in fl if p.is_file()]
    n, mb = len(real), sum(p.stat().st_size for p in real) / 1e6
    out = []
    if abs(n - n_said) > SIZE_MARGIN * n:
        out.append(f"README says about {n_said} files, the package has {n}")
    if abs(mb - mb_said) > SIZE_MARGIN * mb:
        out.append(f"README says {mb_said} MB, the package has {mb:.1f} MB")
    return out


def main(argv=None) -> int:
    global ROOT
    args = list(sys.argv[1:] if argv is None else argv)
    if "--root" in args:
        ROOT = Path(args[args.index("--root") + 1]).resolve()
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
            for rule, rx in (("private-path", PRIVATE), ("credential", SECRET), ("restricted-site-fact", RESTRICTED), ("legacy-repo-trace", LEGACY)):
                m = rx.search(text)
                if m and rel != "tools/check_packaging.py":  # the patterns themselves live here
                    add(rel, rule, m.group(0)[:60])
            if p.suffix == ".json" and rel.startswith(("adapters/", "examples/")):
                try:
                    bad = batch_site_facts(json.loads(text))
                except ValueError:
                    bad = []
                if bad:
                    add(rel, "batch-site-fact", ", ".join(bad)[:120])
            for m in EMAIL.finditer(text):
                local = m.group(0).split("@")[0].lower()
                if m.group(0) not in EMAIL_OK and local not in PLACEHOLDER_LOCAL and not m.group(0).endswith((".example", "@example.com", "@example.org")):
                    add(rel, "email", m.group(0))
                    break
    for problem in size_drift(fl):
        add("README.md", "size-statement-drift", problem)
    rep = {"files_scanned": len(fl), "findings": findings, "ok": not findings}
    print(json.dumps(rep, indent=1))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
