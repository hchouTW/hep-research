#!/usr/bin/env python3
"""Packaging scan: nothing private, project-specific, cached or transcript-like ships in the plugin.

Scans the files a package would contain (git-tracked files when run in a checkout, else every file except caches); the
content rules below apply to every text file (a known text suffix, or no NUL byte in the first 8 KiB):
- no symlinks, caches (__pycache__, *.pyc, .pytest_cache, .DS_Store) or editor/OS debris, including AppleDouble
  files (a `._<name>` file starting with the AppleDouble magic 00 05 16 07, written by macOS on non-HFS volumes and
  by archivers); a regular file whose name merely starts with `._` is not debris
- no model transcripts or session logs (*.jsonl, files named *transcript*), no grading rubrics or eval answer keys
- no archives (.tar.gz, .zip, ...): they are build or tool outputs, such as the submission.tar.gz hepdata_lib writes
- no project data: no hep-research-artifacts/ folder; project configs only as test fixtures
- no private paths (home directories, mounted project folders, temp session folders) or credentials
- no e-mail addresses other than the commit trailer address and addresses at reserved placeholder domains
  (example.com/.org/.net, *.example, *.invalid, *.test, *.localhost; RFC 2606, RFC 6761); no file over 2 MiB
- no restricted-site or personal-machine facts (EOS, AFS or AMS CVMFS paths, lxplus node names, home folders, local
  hostnames), no AMS Offline software identifiers, and no trace of the plugin's pre-release development repository
- no site facts in shipped batch-scheduler configs (JSON under adapters/ or examples/; any object at any depth with a
  slurm or htcondor backend or section, and everything below it; keys compared case-insensitively): partition,
  account, QoS, constraint, gres, requirements and container image must be placeholders ("<...>") or start with
  "synthetic"; campaign_dir must not be an absolute path
- the README's stated package size ("about N files, X MB uncompressed") within 10% of the file count and byte total
  of the upload zip it describes, `git archive --format=zip HEAD:plugins/hep-research`: the scanned files minus every
  path that git archive leaves out because it or one of its folders is marked export-ignore in a .gitattributes inside
  the plugin (git archive of a subtree reads only the attributes in that tree; tests/ and docs/dev/ are left out,
  maintainer decision 2026-11-14); and that zip inside the documented upload limits, 5,000 entries (files plus the
  folder entries git archive writes, the stricter reading of "5,000 files") and 200 MB (10^6 bytes per MB) uncompressed
- every runtime reference from a shipped file into tests/ or docs/dev/ resolves inside that zip: the tests a profile
  capability cites, plugin-root path constants and "tests/..." path strings in Python files, and relative Markdown links
  (maintainer tools that run the test suite, MAINTAINER_TOOLS, and code below a folder named tests are not checked)
Usage: python3 tools/check_packaging.py [--root PLUGIN_ROOT]   Exit 0 clean, 1 findings. Output: JSON.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_KEYS = ("partition", "account", "qos", "constraint", "gres", "requirements", "container_image")
MAX_BYTES = 2 * 1024 * 1024
CACHE = re.compile(r"(^|/)(__pycache__|\.pytest_cache|\.hypothesis)(/|$)|\.pyc$|(^|/)\.DS_Store$")
TRANSCRIPT = re.compile(r"\.jsonl$|transcript", re.I)
ARCHIVE = re.compile(r"\.(tar|tgz|tar\.gz|tar\.bz2|tar\.xz|zip|7z|rar)$", re.I)  # build or tool outputs, never shipped
RUBRIC = re.compile(r"rubric|answer[-_]?key|grading|prompts_eval|routing_eval", re.I)
PRIVATE = re.compile(r"/home/[a-z_][a-z0-9_-]*/|/Users/[A-Za-z0-9_.-]+/|C:\\\\Users\\\\|/mnt/project-files|/tmp/claude|\.claude/projects/")
SECRET = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|(api[_-]?key|token|password)\s*[:=]\s*['\"][^'\"\s]{8,}", re.I)
# A local hostname (mymac.local); a name followed by .md or .json is a file, such as the Claude Code files CLAUDE.local.md
# and settings.local.json that the independent review host notes must name (maintainer decision, 2026-10-21).
RESTRICTED = re.compile(r"/eos/|/afs/|/cvmfs/ams|lxplus\d+|/Users/|-Users-|/tmp/[a-z]{3,}[a-z0-9]*/|hitronhub|[A-Za-z0-9-]+\.local\b(?!\.(?:md|json))"
                        r"|AMSChain|AMSEventR|AMSDataDir|\bvdev\b|ISS\.B\d+")
LEGACY = re.compile(r"agentic[-_]ai[-_]skills|3e995a4|\.legacy/|legacy_id|\bported from|migrated (from|routing)"
                    r"|legacy [`a-z-]+ (skill|ledger|spec|tests?|sample|scripts?|repo|checkout)|migration[- ]map|ams-analysis|fetch_legacy", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_OK = {"noreply@anthropic.com", "license@geant4.org"}  # the second is in the Geant4 Software License, reproduced verbatim in adapters/geant4/assets/GEANT4-LICENSE.txt
# Placeholder addresses are exempt only at a reserved domain (RFC 2606 / RFC 6761): example.com/.org/.net and their
# subdomains, and the .example, .invalid, .test and .localhost top-level domains. A placeholder local part (author@,
# user@) at any other domain is reported, because author@<real domain> is someone's address.
RESERVED_DOMAIN = re.compile(r"(^|\.)(example\.(com|org|net)|example|invalid|test|localhost)$", re.I)
TEXT = {".py", ".md", ".json", ".csv", ".txt", ".yaml", ".yml", ".sh", ".C", ".cpp", ".cc", ".h", ".hpp", ".toml", ".cfg", ".ini",
        ".tex", ".bib", ".dat", ".tcl", ".ma5", ".info", ".template", ".sub", ".sbatch", ".lock"}  # fast path only


def is_text(p: Path) -> bool:
    """A file is scanned as text when its suffix is a known text format or its first 8 KiB hold no NUL byte, so a
    .hh header, a .patch, a Snakefile or a suffix-less shim is scanned too."""
    if p.suffix in TEXT:
        return True
    with p.open("rb") as fh:
        return b"\0" not in fh.read(8192)


APPLEDOUBLE_MAGIC = b"\x00\x05\x16\x07"


def is_appledouble(p: Path) -> bool:
    """An AppleDouble resource-fork file: named ._<name> and starting with the AppleDouble magic number."""
    if not p.name.startswith("._") or p.is_symlink() or not p.is_file():
        return False
    try:
        with p.open("rb") as fh:
            return fh.read(4) == APPLEDOUBLE_MAGIC
    except OSError:
        return False


def files() -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."], cwd=ROOT, capture_output=True, text=True, check=True, timeout=120).stdout
        tracked = [ROOT / f for f in out.split("\0") if f and ((ROOT / f).exists() or (ROOT / f).is_symlink())]  # not deleted in the worktree
        if tracked:
            return tracked
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p for p in ROOT.rglob("*") if (p.is_file() or p.is_symlink()) and not CACHE.search(p.relative_to(ROOT).as_posix())]


def batch_site_facts(obj, inside: bool = False) -> list[str]:
    """Site keys in a batch config that hold neither a placeholder nor a synthetic value. The JSON is walked
    recursively; a dict with a slurm or htcondor backend or section opens a batch scope that covers everything below
    it. Keys and the backend value are compared case-insensitively."""
    bad: list[str] = []
    if isinstance(obj, list):
        for item in obj:
            bad += batch_site_facts(item, inside)
        return bad
    if not isinstance(obj, dict):
        return bad
    keys = {str(k).lower(): v for k, v in obj.items()}
    backend = keys.get("backend")
    inside = inside or (isinstance(backend, str) and backend.lower() in ("slurm", "htcondor")) \
        or "slurm" in keys or "htcondor" in keys
    if inside:
        for k, v in obj.items():
            if str(k).lower() in SITE_KEYS and isinstance(v, str) and not (v.startswith("<") and v.endswith(">")) \
                    and not v.lower().startswith("synthetic"):
                bad.append(f"{k}={v}")
            if str(k).lower() == "campaign_dir" and isinstance(v, str) and v.startswith(("/", "~")):
                bad.append(f"{k}={v}")  # an absolute path names someone's file system
    for v in obj.values():
        bad += batch_site_facts(v, inside)
    return bad


SIZE_RE = re.compile(r"\(about\s+([\d,]+)\s+files,\s+([\d.]+)\s+MB\s+uncompressed\)")
SIZE_MARGIN = 0.10
MAX_UPLOAD_ENTRIES = 5000          # documented upload limit "5,000 files", read as zip entries (files and folders)
MAX_UPLOAD_BYTES = 200 * 10**6     # documented upload limit "200 MB", uncompressed


def _attribute_rules(fl: list[Path]) -> list[tuple[str, str, bool, bool]]:
    """export-ignore lines of every .gitattributes among the scanned files, outermost file first:
    (folder of the file, pattern without its slashes, directory-only, set). A line that unsets the attribute
    (-export-ignore or !export-ignore) is kept with set=False, so a later line can override an earlier one."""
    rules = []
    for ga in sorted((p for p in fl if p.name == ".gitattributes" and p.is_file()),
                     key=lambda p: len(p.relative_to(ROOT).parts)):
        base = ga.parent.relative_to(ROOT).as_posix()
        base = "" if base == "." else base
        for line in ga.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if not parts or parts[0].startswith("#"):
                continue
            pattern, attrs = parts[0], parts[1:]
            state = None
            for a in attrs:
                if a == "export-ignore":
                    state = True
                elif a in ("-export-ignore", "!export-ignore"):
                    state = False
            if state is None:
                continue
            dir_only = pattern.endswith("/")
            rules.append((base, pattern.rstrip("/"), dir_only, state))
    return rules


def _rule_matches(rule: tuple[str, str, bool, bool], path: str, is_dir: bool) -> bool:
    """gitattributes matching of one rule against a path relative to the plugin root: a pattern holding a slash is
    anchored to the folder of its .gitattributes, one without matches the last path component at any depth."""
    base, pattern, dir_only, _ = rule
    if dir_only and not is_dir:
        return False
    if base:
        if not path.startswith(base + "/"):
            return False
        path = path[len(base) + 1:]
    if "/" in pattern:
        return fnmatch.fnmatchcase(path, pattern.lstrip("/"))
    return fnmatch.fnmatchcase(path.rsplit("/", 1)[-1], pattern)


def upload_files(fl: list[Path]) -> list[Path]:
    """The files the upload zip holds: the scanned regular files minus those that git archive leaves out because the
    file or one of its folders is marked export-ignore (the last matching line wins; a deeper .gitattributes comes
    later). Read from the .gitattributes files themselves, so it works the same outside a git checkout."""
    rules = _attribute_rules(fl)

    def ignored(path: str, is_dir: bool) -> bool:
        state = False
        for rule in rules:
            if _rule_matches(rule, path, is_dir):
                state = rule[3]
        return state

    out = []
    for p in fl:
        if not p.is_file() or p.is_symlink():
            continue
        parts = p.relative_to(ROOT).parts
        folders = ["/".join(parts[:k]) for k in range(1, len(parts))]
        if not any(ignored(d, True) for d in folders) and not ignored("/".join(parts), False):
            out.append(p)
    return out


def zip_entries(files_kept: list[Path]) -> int:
    """Entries of the zip git archive writes for these files: one per file and one per folder holding any of them."""
    folders = {parent for p in files_kept for parent in p.relative_to(ROOT).parents if parent != Path(".")}
    return len(files_kept) + len(folders)


# Files that may lose their tests in the upload zip: maintainer tools that run or list the test suite. Test and gate code
# (any file below a folder named tests) is not checked either; everything else that ships is.
MAINTAINER_TOOLS = {"tools/run_all_checks.py", "tools/check_routing_static.py", "tools/check_ams_optional.py",
                    "tools/ci_plan.py", "tools/check_host_neutral.py"}
LEFT_OUT_PREFIXES = ("tests", "docs/dev")   # the trees export-ignore may thin out; a reference into them must resolve
PATH_VAR = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(Path\(__file__\)\.resolve\(\)|[A-Z_][A-Z0-9_]*)((?:\.parent\b|\.parents\[\d+\])*)\s*(?:#.*)?$", re.M)
PATH_JOIN = re.compile(r"\b([A-Z_][A-Z0-9_]*)((?:\s*/\s*(?:\"[^\"\n]+\"|'[^'\n]+'))+)")
PATH_LITERAL = re.compile(r"[\"']((?:tests|docs/dev)/[\w./*-]+)[\"']")
MD_LINK = re.compile(r"\]\(([^)\s]+)\)")


def _checked(rel: str) -> bool:
    return rel not in MAINTAINER_TOOLS and "tests" not in rel.split("/")[:-1]


def _under_left_out(rel: str) -> bool:
    return any(rel == p or rel.startswith(p + "/") for p in LEFT_OUT_PREFIXES)


def _relative(path: str) -> str | None:
    """A path (absolute, or normalised against ROOT) relative to the plugin root, or None outside it."""
    full = os.path.normpath(path)
    root = os.path.normpath(str(ROOT))
    if full == root:
        return ""
    return full[len(root) + 1:].replace(os.sep, "/") if full.startswith(root + os.sep) else None


def _python_targets(p: Path, text: str) -> list[tuple[str, str]]:
    """Plugin-relative paths a Python file builds: NAME / "a" / "b" where NAME is Path(__file__).resolve() moved up by
    .parent / .parents[k] (directly or through another such name), and whole string literals "tests/..." (read
    against the plugin root, as glob patterns are)."""
    bases: dict[str, str] = {}
    for m in PATH_VAR.finditer(text):
        name, start, steps = m.groups()
        base = str(p) if start.startswith("Path(") else bases.get(start)
        if base is None:
            continue
        for step in re.findall(r"\.parent\b|\.parents\[(\d+)\]", steps):
            base = os.path.dirname(base) if step == "" else os.path.normpath(os.path.join(base, *[".."] * (int(step) + 1)))
        bases[name] = base
    out = []
    for m in PATH_JOIN.finditer(text):
        if m.group(1) in bases:
            parts = re.findall(r"\"([^\"\n]+)\"|'([^'\n]+)'", m.group(2))
            rel = _relative(os.path.join(bases[m.group(1)], *[a or b for a, b in parts]))
            if rel is not None:
                out.append((rel, f"{m.group(1)} / ..."))
    out += [(m.group(1).rstrip("/"), "a path string") for m in PATH_LITERAL.finditer(text)]
    return out


def unresolved_references(fl: list[Path], kept: list[Path]) -> list[tuple[str, str]]:
    """Runtime references from shipped files into tests/ or docs/dev/ that do not resolve inside the upload zip:
    the tests a profile capability cites (contracts/registry.py requires them), plugin-root path constants and path
    strings in Python files, and relative Markdown links. A folder or glob resolves when a kept file lies below or
    matches it. Only targets the scanned tree holds are judged: the finding is a reference export-ignore broke.
    Returns (referring file, detail)."""
    kept_rels = {p.relative_to(ROOT).as_posix() for p in kept}
    all_rels = {p.relative_to(ROOT).as_posix() for p in fl if p.is_file()}

    def present(rel: str, among: set[str]) -> bool:
        if rel in among or any(k.startswith(rel + "/") for k in among):
            return True
        return any(ch in rel for ch in "*?[") and any(fnmatch.fnmatchcase(k, rel) or fnmatch.fnmatchcase(k, rel + "/*")
                                                       for k in among)

    def resolved(rel: str) -> bool:
        # a target the package never held (a broken link, prose that looks like one) is not this check's finding
        return present(rel, kept_rels) or not present(rel, all_rels)
    found = []
    for p in kept:
        rel = p.relative_to(ROOT).as_posix()
        if not _checked(rel):
            continue
        targets: list[tuple[str, str]] = []
        if p.name == "profile.json" and rel.startswith("profiles/"):
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                doc = {}
            for cap in doc.get("capabilities") or [] if isinstance(doc, dict) else []:
                for t in (cap.get("tests") or []) if isinstance(cap, dict) else []:
                    target = _relative(os.path.join(str(p.parent), str(t)))
                    if target is not None:
                        targets.append((target, f"a test of capability '{cap.get('name')}'"))
        elif p.suffix == ".py":
            targets = _python_targets(p, p.read_text(encoding="utf-8", errors="replace"))
        elif p.suffix == ".md":
            for m in MD_LINK.finditer(p.read_text(encoding="utf-8", errors="replace")):
                link = m.group(1).split("#", 1)[0]
                if not link or ":" in link or link.startswith("<"):
                    continue
                target = _relative(os.path.join(str(p.parent), link))
                if target is not None:
                    targets.append((target, "a Markdown link"))
        for target, how in targets:
            if _under_left_out(target) and not resolved(target):
                found.append((rel, f"{target} ({how}) is not in the upload zip"))
    return found


def size_drift(fl: list[Path]) -> list[str]:
    """Problems with the upload zip and the README's statement of its size: the statement missing or more than
    SIZE_MARGIN off the measured zip, or the zip over the documented upload limits."""
    readme = ROOT / "README.md"
    m = SIZE_RE.search(readme.read_text(encoding="utf-8")) if readme.is_file() else None
    kept = upload_files(fl)
    n, nbytes = len(kept), sum(p.stat().st_size for p in kept)
    mb = nbytes / 1e6
    out = []
    if not m:
        out.append("README.md has no '(about N files, X MB uncompressed)' statement")
    else:
        n_said, mb_said = int(m.group(1).replace(",", "")), float(m.group(2))
        if abs(n - n_said) > SIZE_MARGIN * n:
            out.append(f"README says about {n_said} files, the upload zip has {n}")
        if abs(mb - mb_said) > SIZE_MARGIN * mb:
            out.append(f"README says {mb_said} MB, the upload zip has {mb:.1f} MB")
    entries = zip_entries(kept)
    if entries > MAX_UPLOAD_ENTRIES:
        out.append(f"the upload zip has {entries} entries ({n} files and their folders), over the documented limit "
                   f"of 5,000 files ({MAX_UPLOAD_ENTRIES} entries)")
    if nbytes > MAX_UPLOAD_BYTES:
        out.append(f"the upload zip holds {mb:.1f} MB uncompressed, over the documented limit of 200 MB")
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
        if is_appledouble(p):
            add(rel, "appledouble")
        if TRANSCRIPT.search(rel):
            add(rel, "transcript-or-log")
        if ARCHIVE.search(rel):
            add(rel, "archive")
        if RUBRIC.search(rel):
            add(rel, "rubric-or-eval-key")
        if "hep-research-artifacts/" in rel:
            add(rel, "project-artifacts")
        if p.name == "hep-research.project.json" and not fixture:
            add(rel, "project-config-outside-fixtures")
        if p.stat().st_size > MAX_BYTES:
            add(rel, "large-file", f"{p.stat().st_size} bytes")
        if is_text(p):
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
                domain = m.group(0).rsplit("@", 1)[1]
                if m.group(0) not in EMAIL_OK and not RESERVED_DOMAIN.search(domain):
                    add(rel, "email", m.group(0))
                    break
    for problem in size_drift(fl):
        add("README.md", "size-statement-drift", problem)
    for path, problem in unresolved_references(fl, upload_files(fl)):
        add(path, "shipped-reference-unresolved", problem)
    rep = {"files_scanned": len(fl), "findings": findings, "ok": not findings}
    print(json.dumps(rep, indent=1))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
