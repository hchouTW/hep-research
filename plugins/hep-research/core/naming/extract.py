"""Shared machinery of the naming extractors (spec §6.1, §9 step 1): one extractor per owner skill,
skills/<owner>/scripts/extract_names.py, each a table of surface readers run through main() here.

walk() lists the files and folders of the scope folders (cache folders, hidden folders and <project>/naming/ left
out); TextIndex and PathIndex find the text mentions of a name and of a path in every text file in scope; coverage()
writes the search_coverage strings; the git helpers mark names added, modified or removed against a revision
(mark_changes compares the names a reader finds now with those it finds in the old content of the same files);
artifacts() yields the JSON artifacts in scope (read only: an extractor never writes into artifacts_dir, I9). main()
is the common command line: --surface, --out, --root, --scope, --changed (the script adds --status); exit 0 written, 2 bad input,
3 written with zero inputs scanned. core imports only core; standard library only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

from core.naming.model import new_entity, sha256_text

GIT_TIMEOUT_S = 120
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache",
             ".tox", ".ipynb_checkpoints"}
WORK_DIR = "naming"  # <project>/naming/: the naming working files, never scanned
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".jsonl", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".tex",
                 ".bib", ".c", ".cc", ".cxx", ".cpp", ".h", ".hh", ".hpp", ".C", ".csv", ".tsv", ".rst", ".html",
                 ".xml", ".smk", ".cmake", ".in", ".sty", ".cls", ".dat", ".sub", ".jdl", ".slurm", ".mac"}
TEXT_NAMES = {"Makefile", "Snakefile", "CMakeLists.txt", "Dockerfile"}
MAX_TEXT_BYTES = 2_000_000
WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*")
PATH = re.compile(r"[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]*)+")


def now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_plugin(root: Path) -> bool:
    try:
        return json.loads((root / ".claude-plugin" / "plugin.json").read_text())["name"] == "hep-research"
    except (OSError, ValueError, KeyError):
        return False


def walk(root: Path, scopes) -> list[str]:
    """Project-relative posix paths of every file and directory under the scope folders, cache folders excluded."""
    out: list[str] = []
    root = Path(root).resolve()
    for s in scopes:
        base = (root / s).resolve()
        stack = [base]
        while stack:
            d = stack.pop()
            try:
                children = sorted(d.iterdir())
            except OSError:
                continue
            for c in children:
                if c.is_symlink():
                    continue
                if c.is_dir():
                    if c.name in SKIP_DIRS or c.name.startswith(".") or (c.name == WORK_DIR and c.parent == root):
                        continue
                    out.append(c.relative_to(root).as_posix())
                    stack.append(c)
                elif c.is_file():
                    out.append(c.relative_to(root).as_posix())
    return sorted(dict.fromkeys(out))


def files_of(root: Path, scopes) -> list[str]:
    root = Path(root).resolve()
    return [p for p in walk(root, scopes) if (root / p).is_file()]


def is_text(rel: str) -> bool:
    p = PurePosixPath(rel)
    return p.suffix in TEXT_SUFFIXES or p.name in TEXT_NAMES


def read_text(root: Path, rel: str) -> str | None:
    p = Path(root) / rel
    try:
        if p.stat().st_size > MAX_TEXT_BYTES:
            return None
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def line_of(text: str, needle: str) -> int:
    for n, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return n
    return 1


class TextIndex:
    """token -> [(file, line)] over every text file in scope, for one token pattern."""

    def __init__(self, root: Path, files, pattern=WORD):
        self.hits: dict[str, list[tuple[str, int]]] = {}
        self.files = 0
        for rel in files:
            if not is_text(rel):
                continue
            text = read_text(root, rel)
            if text is None:
                continue
            self.files += 1
            for n, line in enumerate(text.splitlines(), 1):
                for m in pattern.finditer(line):
                    tok = m.group(0).rstrip(".-")
                    self.hits.setdefault(tok, []).append((rel, n))

    def find(self, token: str, exclude=()) -> list[tuple[str, int]]:
        ex = set(exclude)
        return [h for h in dict.fromkeys(self.hits.get(token, [])) if h not in ex]

    def refs(self, token: str, at=None, kind: str = "mentions") -> list[dict]:
        """References {from: file:line, kind} of a token, the declaration itself (at = (file, line)) left out."""
        return [{"from": f"{f}:{n}", "kind": kind} for f, n in self.find(token) if (f, n) != at]


class PathIndex:
    """Path-like mentions (a/b/c.txt) resolved against the project root and against the mentioning file's folder:
    resolved path or any of its parent folders -> [(file, line)]. A folder is referenced by mentions of a path inside
    it; a file by mentions that resolve to it (bare file names are matched separately, by TextIndex)."""

    def __init__(self, root: Path, files):
        self.hits: dict[str, list[tuple[str, int]]] = {}
        for rel in files:
            if not is_text(rel):
                continue
            text = read_text(root, rel)
            if text is None:
                continue
            here = PurePosixPath(rel).parent
            for n, line in enumerate(text.splitlines(), 1):
                for m in PATH.finditer(line):
                    tok = m.group(0).rstrip(".-/")
                    for cand in {norm_path(tok), norm_path((here / tok).as_posix())}:
                        if cand is None:
                            continue
                        parts = cand.split("/")
                        for i in range(1, len(parts) + 1):
                            self.hits.setdefault("/".join(parts[:i]), []).append((rel, n))

    def find(self, path: str) -> list[tuple[str, int]]:
        return list(dict.fromkeys(self.hits.get(path, [])))


def norm_path(path: str) -> str | None:
    """A relative posix path with . and .. resolved; None when it climbs above its start."""
    out: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not out:
                return None
            out.pop()
        else:
            out.append(part)
    return "/".join(out) or None


def coverage(surfaces, scopes) -> list[str]:
    return [f"{s}:{('' if sc in ('.', '') else sc.rstrip('/') + '/')}**" for s in surfaces for sc in scopes]


def file_digest(path: Path) -> str:
    if path.is_dir():
        return sha256_text("\n".join(sorted(c.name for c in path.iterdir())))
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------------------ git


def old_bytes(root: Path, rev: str, rel: str) -> bytes | None:
    p = subprocess.run(["git", "-C", str(root), "show", f"{rev}:{rel}"], capture_output=True, timeout=GIT_TIMEOUT_S)
    return p.stdout if p.returncode == 0 else None


def old_source(root: Path, rev: str, rel: str) -> str | None:
    raw = old_bytes(root, rev, rel)
    if raw is None:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def changed_files(root: Path, rev: str, scopes) -> tuple[set[str], set[str]]:
    """(changed or added files, deleted files) since rev, project-relative."""
    p = subprocess.run(["git", "-C", str(root), "diff", "--name-status", "--relative", rev, "--", *scopes],
                       capture_output=True, text=True, timeout=GIT_TIMEOUT_S)
    if p.returncode:
        raise ValueError(f"git diff against {rev!r} failed: {p.stderr.strip()[:200]}")
    changed, deleted = set(), set()
    for line in p.stdout.splitlines():
        parts = line.split("\t")
        if parts[0].startswith("D"):
            deleted.add(parts[1])
        elif parts[0].startswith("R"):
            deleted.add(parts[1])
            changed.add(parts[2])
        else:
            changed.add(parts[-1])
    untracked = subprocess.run(["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "--", *scopes],
                               capture_output=True, text=True, timeout=GIT_TIMEOUT_S).stdout.split()
    return changed | set(untracked), deleted


def mark_changed_by_file(root: Path, rev: str, scopes, entities) -> None:
    """Names in files changed since rev: added when absent from the old file's text, else modified."""
    touched, _ = changed_files(root, rev, scopes)
    for e in entities:
        rel = e["scope"]["file"]
        if rel in touched:
            old = old_source(root, rev, rel)
            e["change"] = "added" if old is None or e["name"] not in old else "modified"


def _key(e: dict, count: dict) -> tuple:
    k = (e["scope"]["file"], e["scope"]["container"], e["entity_kind"], e["name"])
    count[k] = count.get(k, 0) + 1
    return k + (count[k],)


def mark_changes(root: Path, rev: str, scopes, entities: list, read_old) -> list:
    """Mark each entity added, modified (same file, container, kind and name; other content) or unchanged against
    rev, and return the entities removed since rev. read_old(rel, raw_bytes) gives the entities a reader finds in the
    old content of one file (raw_bytes None: the file did not exist); it is called for changed and deleted files."""
    touched, deleted = changed_files(root, rev, scopes)
    by_file: dict[str, list] = {}
    for e in entities:
        by_file.setdefault(e["scope"]["file"], []).append(e)
    removed: list = []
    for rel in sorted(touched | deleted):
        now_ents = by_file.get(rel, [])
        olds = read_old(rel, old_bytes(root, rev, rel)) or []
        count_old: dict = {}
        old_keyed = {_key(o, count_old): o for o in olds}
        count_now: dict = {}
        now_keys = set()
        for e in now_ents:
            k = _key(e, count_now)
            now_keys.add(k)
            prev = old_keyed.get(k)
            e["change"] = "added" if prev is None else (
                "modified" if prev["content_sha256"] != e["content_sha256"] else "unchanged")
        for k, o in old_keyed.items():
            if k not in now_keys:
                o["change"] = "removed"
                removed.append(o)
    return removed


def _git(root: Path, *args) -> str | None:
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=GIT_TIMEOUT_S)
    return p.stdout.strip() if p.returncode == 0 else None


def change_base(root: Path, rev: str) -> dict:
    """What --changed compares against. "auto" is the merge base of HEAD and the main branch (origin/HEAD, main,
    master, origin/main, origin/master, the first that exists). For an explicit revision, hidden_commits counts the
    commits of this branch (after the merge base) that the revision already contains: their names would look
    unchanged, so the check reports every name instead."""
    main = next((b for b in ("origin/HEAD", "main", "master", "origin/main", "origin/master")
                 if _git(root, "rev-parse", "--verify", "--quiet", f"{b}^{{commit}}")), None)
    base = _git(root, "merge-base", "HEAD", main) if main else None
    if rev == "auto":
        if base is None:
            head = _git(root, "rev-parse", "HEAD")
            if head is None:
                raise ValueError("--changed auto needs a git repository with at least one commit")
            return {"rev": "auto", "sha": head, "merge_base": None, "hidden_commits": 0,
                    "note": "no main branch found: compared against HEAD, so only uncommitted changes are marked"}
        return {"rev": "auto", "sha": base, "merge_base": base, "hidden_commits": 0}
    sha = _git(root, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    if sha is None:
        raise ValueError(f"--changed {rev}: not a git revision of {root}")
    hidden = 0
    if base and _git(root, "merge-base", "--is-ancestor", base, sha) is not None:
        hidden = int(_git(root, "rev-list", "--count", f"{base}..{sha}") or 0)
    return {"rev": rev, "sha": sha, "merge_base": base, "hidden_commits": hidden}


def enclosing_project(root: Path) -> Path | None:
    """A folder above root that is a project (hep-research.project.json or a git checkout), unless root lies inside
    the hep-research plugin itself: an inventory of a subfolder never stands for the whole project."""
    root = Path(root).resolve()
    if (root / "hep-research.project.json").is_file() or (root / ".git").exists():
        return None
    for up in root.parents:
        if is_plugin(up):
            return None
        if (up / "hep-research.project.json").is_file() or (up / ".git").exists():
            return up
    return None


# ------------------------------------------------------------------------------------------------------ artifacts


def artifacts_dir(root: Path) -> Path | None:
    cfg = Path(root) / "hep-research.project.json"
    try:
        rel = json.loads(cfg.read_text(encoding="utf-8")).get("artifacts_dir", "./hep-research-artifacts/")
    except (OSError, ValueError):
        return None
    return (Path(root) / rel).resolve()


def load_json(root: Path, rel: str):
    text = read_text(root, rel)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def artifacts(root: Path, files, types) -> list[tuple[str, dict, str]]:
    """(file, artifact, text) for every JSON file in scope whose artifact_type is one of types."""
    out = []
    for rel in files:
        if not rel.endswith(".json"):
            continue
        text = read_text(root, rel)
        if text is None or '"artifact_type"' not in text:
            continue
        try:
            doc = json.loads(text)
        except ValueError:
            continue
        if isinstance(doc, dict) and doc.get("artifact_type") in types:
            out.append((rel, doc, text))
    return out


def artifact_status(doc: dict) -> str | None:
    s = doc.get("status")
    return s if isinstance(s, str) else None


# ------------------------------------------------------------------------------------------------------- entities


class Builder:
    """Collects the declarations of one surface and turns them into entities with references and coverage.

    add(kind, name, file, container, line, content, ...) records one declaration; build(index, cov) resolves the
    references of each through the TextIndex (the declaration line itself left out) unless refs are given."""

    def __init__(self, surface: str, extractor: dict):
        self.surface, self.extractor = surface, extractor
        self.items: list[dict] = []

    def add(self, kind: str, name, file: str, container: str, line: int, content: str = "", *, source="project",
            refs=None, meaning=None, targets=None, end: int | None = None):
        if not isinstance(name, str) or not name:
            return
        self.items.append({"kind": kind, "name": name, "file": file, "container": container, "line": max(int(line), 0),
                           "end": end, "content": content or f"{container}:{name}", "source": source, "refs": refs,
                           "meaning": meaning, "targets": targets})

    def build(self, index: TextIndex | None, cov, ref_kind: str = "mentions") -> list[dict]:
        out = []
        for it in self.items:
            refs = it["refs"]
            if refs is None:
                refs = index.refs(it["name"], (it["file"], it["line"]), ref_kind) if index is not None else []
            e = new_entity(self.surface, it["kind"], it["name"], it["file"], it["container"],
                           (it["line"], it["end"] if it["end"] is not None else it["line"]), source=it["source"],
                           content=it["content"], extractor=self.extractor, references=refs, search_coverage=cov,
                           meaning=it["meaning"])
            if it["targets"]:
                e["targets"] = list(it["targets"])
            out.append(e)
        return out


# ------------------------------------------------------------------------------------------------------------ CLI


def main(argv, *, doc: str, readers: dict, extractor: dict) -> int:
    """The common command line of every extract_names.py. readers maps a surface to f(root, scopes, changed, args)
    returning an inventory; readers["__options__"](parser) adds the script's own options, --status included."""
    import sys
    ap = argparse.ArgumentParser(description=doc.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=doc.split("\n\n", 1)[1] if "\n\n" in doc else None)
    surfaces = [s for s in readers if not s.startswith("__")]
    ap.add_argument("--surface", required=True, help=", ".join(surfaces))
    ap.add_argument("--out", type=Path, required=True, help="inventory file to write (never inside artifacts_dir)")
    ap.add_argument("--root", type=Path, default=Path("."), help="project root (default: the working directory)")
    ap.add_argument("--scope", action="append", help="folder relative to the root to scan (repeatable; default the root)")
    ap.add_argument("--changed", metavar="REV", nargs="?", const="auto",
                    help="git revision to mark added, modified and removed names against (alone or auto: the merge "
                         "base of HEAD and the main branch)")
    readers["__options__"](ap)  # the script's own options, --status (core.status.add_status_argument) among them
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    def reject(msg: str) -> int:
        print(json.dumps({"status": "rejected", "error": msg}))
        return 2
    if args.surface not in surfaces:
        return reject(f"--surface {args.surface}: this extractor reads {', '.join(surfaces)}; another surface's owner "
                      "provides its extractor (contracts/naming_check.py surfaces)")
    root = args.root.resolve()
    if not root.is_dir():
        return reject(f"--root {args.root} is not a directory")
    above = enclosing_project(root)
    if above is not None:
        return reject(f"--root {args.root} lies inside the project {above}: give the project root as --root and narrow "
                      "with --scope (references are then searched in the whole project, or reported partial)")
    scopes = []
    for s in args.scope or ["."]:
        p = (root / s).resolve()
        if p != root and root not in p.parents:
            return reject(f"--scope {s} lies outside the root")
        if not p.is_dir():
            return reject(f"--scope {s} is not a directory")
        scopes.append(p.relative_to(root).as_posix() if p != root else ".")
    art = artifacts_dir(root)
    out = args.out.resolve()
    if art is not None and (out == art or art in out.parents):
        return reject(f"--out {args.out} is inside artifacts_dir: naming working files stay out of it; use <project>/naming/")
    if not out.parent.is_dir():
        return reject(f"--out directory {args.out.parent} does not exist")
    try:
        base = change_base(root, args.changed) if args.changed else None
        inv = readers[args.surface](root, scopes, base["sha"] if base else None, args)
        if base:
            inv["changed_since"] = base["rev"] if base["rev"] != "auto" else base["sha"]
            inv["change_base"] = base
    except ValueError as exc:
        return reject(str(exc))
    except subprocess.TimeoutExpired:
        return reject(f"git did not answer within {GIT_TIMEOUT_S} s while comparing against {args.changed}")
    try:
        out.write_text(json.dumps(inv, indent=1) + "\n", encoding="utf-8")
    except OSError as exc:
        return reject(f"cannot write {args.out}: {exc}")
    status = "written" if inv["inputs_scanned"] else "incomplete"
    note = {"note": "zero inputs scanned: the check reports this surface unsupported"} if not inv["inputs_scanned"] else {}
    print(json.dumps({"status": status, "status_label": args.status, "out": str(args.out), "surface": args.surface,
                      "entities": len(inv["entities"]), "inputs_scanned": inv["inputs_scanned"],
                      "skipped_inputs": len(inv.get("skipped_inputs", [])), **note}, indent=1))
    sys.stdout.flush()
    return 0 if inv["inputs_scanned"] else 3
