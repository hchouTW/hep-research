#!/usr/bin/env python3
"""Naming extractor of hep-computing (semantic naming charter, references/semantic-naming.md): write the naming
inventory of one surface for contracts/naming_check.py.

Surfaces:
  N1  code identifiers of Python files: functions, classes, module and class variables, instance attributes
      (self.x = ...), parameters and local variables. C++ and shell are not read yet (say so when they matter).
  N2  files and directories; a file whose path a JSON manifest in scope lists next to a sha256 is manifest_checksummed.
  N5  argparse flags and environment variables read by Python code; keys of JSON, TOML and INI configuration files
      (YAML too when PyYAML is installed; otherwise each YAML file is listed in skipped_inputs and references stay
      partial). In the plugin itself, configuration files are contract definitions (N16) and are not read here.
  N16 the plugin's contract vocabulary: artifact types, vocabulary terms (contracts/vocab), effect, class and
      composition ids, skill, script and schema names. Only in the plugin; elsewhere it scans zero inputs.
The inventory holds every name of the surface within the scope folders, each with its references found by a search
of every text file in scope (search_coverage says what was searched), its kind and its source (external: names an
outside API or tool fixes, such as __init__, setUp, README.md). With --changed REV (a git revision) each name is
marked added, modified (same name, other content) or unchanged, and names removed since REV are included with
change removed; the inventory is never reduced to the changed names.

Usage: python3 extract_names.py --surface N1|N2|N5|N16 --out INV.json [--root DIR] [--scope DIR ...] [--changed REV]
--root is the project (default: the working directory); --scope folders are relative to it (default: the root). The
output is a working file of <project>/naming/, refused inside the project's artifacts_dir. Prints one JSON object
with a status key. Exit 0 written, 2 bad input (unknown surface, scope outside the root, bad revision, unwritable
output), 3 written but zero inputs scanned (the check reports the surface unsupported). Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import configparser
import datetime as _dt
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True  # a script run from an installed plugin leaves no __pycache__ in it
PLUGIN = Path(__file__).resolve().parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from core.naming.model import new_entity, new_inventory, sha256_text  # noqa: E402
from core.naming.vocab import hook_methods  # noqa: E402
from core.status import add_status_argument  # noqa: E402

VERSION = "1.0.0"
GIT_TIMEOUT_S = 120
EXTRACTOR = {"id": "skills/hep-computing/scripts/extract_names.py", "version": VERSION}
SURFACES = ("N1", "N2", "N5", "N16")
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache",
             ".tox", ".ipynb_checkpoints"}
WORK_DIR = "naming"  # <project>/naming/: the naming working files, never scanned
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".jsonl", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".tex",
                 ".bib", ".c", ".cc", ".cxx", ".cpp", ".h", ".hh", ".hpp", ".C", ".csv", ".tsv", ".rst", ".html",
                 ".xml", ".smk", ".cmake", ".in", ".sty", ".cls"}
TEXT_NAMES = {"Makefile", "Snakefile", "CMakeLists.txt", "Dockerfile"}
MAX_TEXT_BYTES = 2_000_000
CONVENTIONAL_FILES = {"README.md", "LICENSE", "CHANGELOG.md", "Makefile", "CMakeLists.txt", "__init__.py", "__main__.py",
                      "setup.py", "setup.cfg", "pyproject.toml", "requirements.txt", ".gitignore", "SKILL.md",
                      "Snakefile", "conftest.py", "Dockerfile", "plugin.json", "OWNERS.json", "hep-research.project.json"}
SKIP_DECORATORS = re.compile(r"(?:\.setter|\.getter|\.deleter|\.register|^overload|\.overload)$")
WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*")
PATH = re.compile(r"[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]*)+")
FLAG = re.compile(r"(?<![A-Za-z0-9_-])--?[A-Za-z0-9][A-Za-z0-9_-]*")
CONFIG_NAME = re.compile(r"(?i)(config|settings|options)[^/]*\.json$|\.toml$|\.ini$|\.cfg$|\.ya?ml$")
CORE_API_DIRS = ("core", "contracts")
PLUGIN_SCRIPT_DIRS = ("skills", "tools", "contracts", "core", "adapters")


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_plugin(root: Path) -> bool:
    try:
        return json.loads((root / ".claude-plugin" / "plugin.json").read_text())["name"] == "hep-research"
    except (OSError, ValueError, KeyError):
        return False


def walk(root: Path, scopes) -> list[str]:
    """Project-relative posix paths of every file and directory under the scope folders, cache folders excluded."""
    out: list[str] = []
    root = root.resolve()
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


def is_text(rel: str) -> bool:
    p = PurePosixPath(rel)
    return p.suffix in TEXT_SUFFIXES or p.name in TEXT_NAMES


def read_text(root: Path, rel: str) -> str | None:
    p = root / rel
    try:
        if p.stat().st_size > MAX_TEXT_BYTES:
            return None
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


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
                    for cand in {_norm(tok), _norm((here / tok).as_posix())}:
                        if cand is None:
                            continue
                        parts = cand.split("/")
                        for i in range(1, len(parts) + 1):
                            self.hits.setdefault("/".join(parts[:i]), []).append((rel, n))

    def find(self, path: str) -> list[tuple[str, int]]:
        return list(dict.fromkeys(self.hits.get(path, [])))


def _norm(path: str) -> str | None:
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


# ---------------------------------------------------------------------------------------------------------------- N1


class _Decl:
    __slots__ = ("name", "container", "line", "end", "content", "scope", "node", "fn", "decl_type")

    def __init__(self, name, container, line, end, content, scope, node, fn, decl_type):
        self.name, self.container, self.line, self.end, self.content = name, container, line, end, content
        self.scope, self.node, self.fn, self.decl_type = scope, node, fn, decl_type


def _targets(node) -> list[ast.Name]:
    if isinstance(node, ast.Name):
        return [node]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [n for e in node.elts for n in _targets(e)]
    if isinstance(node, ast.Starred):
        return _targets(node.value)
    return []


def _walk_own(fn):
    """The nodes of a function body, without descending into nested functions, classes or lambdas."""
    todo = list(ast.iter_child_nodes(fn))
    while todo:
        node = todo.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            todo.extend(ast.iter_child_nodes(node))


def _decorator_name(d) -> str:
    return ast.unparse(d.func if isinstance(d, ast.Call) else d)


def python_declarations(source: str) -> list[_Decl]:
    """Every declaration of a Python module, in source order. Variables: the first binding per container; def and
    class statements: each one (a second one in the same container is a duplicate), except property accessors,
    overloads and registered implementations."""
    tree = ast.parse(source)
    lines = source.splitlines()
    out: list[_Decl] = []
    seen_vars: set[tuple[str, str]] = set()

    def seg(node) -> str:
        """The whole source lines of a node (hashed for change detection)."""
        lo = getattr(node, "lineno", None)
        return "\n".join(lines[lo - 1:getattr(node, "end_lineno", lo) or lo]) if lo else ast.dump(node)

    def var(name, container, node, scope, fn, stmt):
        if (container, name) in seen_vars:
            return
        seen_vars.add((container, name))
        out.append(_Decl(name, container, node.lineno, getattr(node, "end_lineno", node.lineno) or node.lineno,
                         seg(stmt), scope, node, fn, "variable"))

    def body(stmts, container, scope, fn):
        for st in stmts:
            stmt(st, container, scope, fn)

    def stmt(st, container, scope, fn):
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not any(SKIP_DECORATORS.search(_decorator_name(d)) for d in st.decorator_list):
                out.append(_Decl(st.name, container, st.lineno, st.end_lineno or st.lineno, seg(st), scope, st, fn,
                                 "class" if isinstance(st, ast.ClassDef) else "function"))
                seen_vars.add((container, st.name))
            inner = f"{container}.{st.name}" if container != "<module>" else st.name
            if isinstance(st, ast.ClassDef):
                body(st.body, inner, "class", fn)
            else:
                a = st.args
                for arg in a.posonlyargs + a.args + a.kwonlyargs + [x for x in (a.vararg, a.kwarg) if x]:
                    if arg.arg in ("self", "cls") and scope == "class":
                        continue
                    var(arg.arg, inner, arg, "function", st, arg)
                body(st.body, inner, "function", st)
                for node in _walk_own(st):
                    if isinstance(node, ast.NamedExpr):
                        var(node.target.id, inner, node.target, "function", st, node)
                    elif isinstance(node, ast.comprehension):
                        for n in _targets(node.target):
                            var(n.id, inner, n, "function", st, node)
                if scope == "class":
                    for node in ast.walk(st):
                        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                            tg = node.targets if isinstance(node, ast.Assign) else [node.target]
                            for t in tg:
                                if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                                    var(t.attr, container, t, "class", None, node)
            return
        if isinstance(st, ast.Assign):
            for t in st.targets:
                for n in _targets(t):
                    var(n.id, container, n, scope, fn, st)
        elif isinstance(st, (ast.AnnAssign, ast.AugAssign)):
            for n in _targets(st.target):
                var(n.id, container, n, scope, fn, st)
        elif isinstance(st, (ast.For, ast.AsyncFor)):
            for n in _targets(st.target):
                var(n.id, container, n, scope, fn, st)
            body(st.body + st.orelse, container, scope, fn)
        elif isinstance(st, (ast.With, ast.AsyncWith)):
            for item in st.items:
                if item.optional_vars is not None:
                    for n in _targets(item.optional_vars):
                        var(n.id, container, n, scope, fn, st)
            body(st.body, container, scope, fn)
        elif isinstance(st, ast.Try) or (hasattr(ast, "TryStar") and isinstance(st, ast.TryStar)):
            body(st.body, container, scope, fn)
            for h in st.handlers:
                if h.name:
                    var(h.name, container, h, scope, fn, h)
                body(h.body, container, scope, fn)
            body(st.orelse + st.finalbody, container, scope, fn)
        elif isinstance(st, (ast.If, ast.While)):
            body(st.body + st.orelse, container, scope, fn)
        elif isinstance(st, ast.Match):
            for case in st.cases:
                body(case.body, container, scope, fn)
    body(tree.body, "<module>", "module", None)
    return out


class PyIndex:
    """Per file: name uses (Name nodes), attribute uses, keyword arguments by callee and import bindings resolved to the files
    of the scope. A module-level name of file F is referenced by its uses in F, and in another file G by the import
    that binds it from F, the uses of that binding in G, and attribute uses alias.name where alias is F's module.
    A class member is referenced by its attribute uses in F and in the files that import from F (an instance passed
    around without its module is not followed: a known limit of the search)."""

    def __init__(self):
        self.names: dict[str, dict[str, list[int]]] = {}
        self.attrs: dict[str, dict[str, list[int]]] = {}
        self.keywords: dict[tuple[str, str], list[tuple[str, int]]] = {}  # (callee name, keyword) -> uses
        self._loads: dict[int, dict[str, list[int]]] = {}
        self.imports: dict[str, list[tuple[str, str, str, int]]] = {}  # file -> (local name, target file, name or "", line)
        self.modules: dict[str, set[str]] = {}
        self.importers: dict[str, set[str]] = {}

    def register(self, rel: str):
        parts = list(PurePosixPath(rel).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        for i in range(len(parts)):
            self.modules.setdefault(".".join(parts[i:]), set()).add(rel)

    def resolve(self, rel: str, module: str | None, level: int) -> set[str]:
        if level:
            base = list(PurePosixPath(rel).parent.parts)[:max(len(PurePosixPath(rel).parent.parts) - (level - 1), 0)]
            dotted = ".".join(base + ([module] if module else []))
            hit = self.modules.get(dotted, set())
            return {f for f in hit if f.startswith("/".join(base))} or hit
        return self.modules.get(module or "", set())

    def add(self, rel: str, tree: ast.AST):
        names = self.names.setdefault(rel, {})
        attrs = self.attrs.setdefault(rel, {})
        imps = self.imports.setdefault(rel, [])
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.setdefault(node.id, []).append(node.lineno)
            elif isinstance(node, ast.Attribute):
                attrs.setdefault(node.attr, []).append(node.lineno)
            elif isinstance(node, ast.Call):
                f = node.func
                callee = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                for kw in node.keywords:
                    if callee and kw.arg:
                        self.keywords.setdefault((callee, kw.arg), []).append((rel, getattr(kw, "lineno", node.lineno)))
            elif isinstance(node, ast.Import):
                for a in node.names:
                    local = a.asname or a.name.split(".")[0]
                    for f in self.resolve(rel, a.name if a.asname else a.name.split(".")[0], 0):
                        imps.append((local, f, "", node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    local = a.asname or a.name
                    for f in self.resolve(rel, node.module, node.level):
                        imps.append((local, f, a.name, node.lineno))
                    sub = f"{node.module}.{a.name}" if node.module else a.name
                    for f in self.resolve(rel, sub, node.level):
                        imps.append((local, f, "", node.lineno))

    def finish(self):
        for g, imps in self.imports.items():
            for _local, f, _name, _line in imps:
                if f != g:
                    self.importers.setdefault(f, set()).add(g)


def _kind_and_source(d: _Decl, rel: str, plugin: bool) -> tuple[str, str]:
    hooks, prefixes = hook_methods()
    if d.scope == "function":
        return "local", "project"
    if (d.name.startswith("__") and d.name.endswith("__")) or (d.scope == "class" and (
            d.name in hooks or any(d.name.startswith(p) for p in prefixes))):
        return ("private" if d.name.startswith("_") else "module_public"), "external"
    parts = [p for p in d.container.split(".") if p != "<module>"]
    if d.name.startswith("_") or any(p.startswith("_") and not p.endswith("__") for p in parts):
        return "private", "project"
    if plugin and PurePosixPath(rel).parts[0] in CORE_API_DIRS:
        return "plugin_core_api", "project"
    return "module_public", "project"


def _loads(fn, py: PyIndex) -> dict[str, list[int]]:
    """Name loads inside a function, computed once per function."""
    got = py._loads.get(id(fn))
    if got is None:
        got = {}
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                got.setdefault(node.id, []).append(node.lineno)
        py._loads[id(fn)] = got
    return got


def _local_refs(d: _Decl, rel: str, py: PyIndex) -> list[dict]:
    """Loads of a local inside its function; for a parameter also the keyword arguments of calls to the function in
    other places (a parameter name is part of the function's interface)."""
    fn = d.fn
    lo, hi = fn.lineno, fn.end_lineno or fn.lineno
    refs = [{"from": f"{rel}:{ln}", "kind": "in-scope"} for ln in _loads(fn, py).get(d.name, [])]
    if d.decl_type == "variable" and isinstance(d.node, ast.arg):
        callee = fn.name
        if callee == "__init__" and "." in d.container:
            callee = d.container.split(".")[-2]
        for f, line in py.keywords.get((callee, d.name), []):
            if not (f == rel and lo <= line <= hi):
                refs.append({"from": f"{f}:{line}", "kind": "keyword"})
    return list({r["from"]: r for r in refs}.values())


def _wide_refs(d: _Decl, rel: str, py: PyIndex) -> list[dict]:
    refs: dict[str, dict] = {}

    def add(f, line, kind):
        if not (f == rel and line == d.line):
            refs.setdefault(f"{f}:{line}", {"from": f"{f}:{line}", "kind": kind})
    if d.scope == "module":
        for line in py.names.get(rel, {}).get(d.name, []):
            add(rel, line, "uses")
        for g, imps in py.imports.items():
            if g == rel:
                continue
            for local, f, name, line in imps:
                if f != rel:
                    continue
                if name == d.name:
                    add(g, line, "imports")
                    for ln in py.names.get(g, {}).get(local, []):
                        add(g, ln, "uses")
                elif name == "":
                    for ln in py.attrs.get(g, {}).get(d.name, []):
                        add(g, ln, "attribute")
    else:
        for g in sorted({rel} | py.importers.get(rel, set())):
            for ln in py.attrs.get(g, {}).get(d.name, []):
                add(g, ln, "attribute")
        if d.decl_type != "variable":
            for ln in py.names.get(rel, {}).get(d.name, []):
                add(rel, ln, "uses")
    return list(refs.values())


def _old_source(root: Path, rev: str, rel: str) -> str | None:
    p = subprocess.run(["git", "-C", str(root), "show", f"{rev}:{rel}"], capture_output=True, text=True,
                       timeout=GIT_TIMEOUT_S)
    return p.stdout if p.returncode == 0 else None


def _changed_files(root: Path, rev: str, scopes) -> tuple[set[str], set[str]]:
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


def _keyed(decls) -> dict[tuple, _Decl]:
    out, count = {}, {}
    for d in decls:
        k = (d.container, d.name, d.decl_type == "variable")
        count[k] = count.get(k, 0) + 1
        out[k + (count[k],)] = d
    return out


def extract_n1(root: Path, scopes, changed: str | None = None) -> dict:
    root = Path(root).resolve()
    files = [f for f in walk(root, scopes) if f.endswith(".py") and (root / f).is_file()]
    plugin = is_plugin(root)
    py, parsed, skipped = PyIndex(), {}, []
    for rel in files:
        py.register(rel)
    for rel in files:
        text = read_text(root, rel)
        try:
            tree = ast.parse(text) if text is not None else None
        except SyntaxError as exc:
            tree = None
            skipped.append({"path": rel, "reason": f"syntax error line {exc.lineno}"})
        if tree is None:
            if text is None:
                skipped.append({"path": rel, "reason": "unreadable or larger than 2 MB"})
            continue
        py.add(rel, tree)
        parsed[rel] = text
    py.finish()
    cov = coverage(["N1"], scopes) if not skipped else [f"N1:{f}" for f in parsed]
    touched, deleted = (_changed_files(root, changed, scopes) if changed else (set(), set()))
    entities = []
    for rel, text in parsed.items():
        decls = python_declarations(text)
        old = None
        if changed and rel in touched:
            src = _old_source(root, changed, rel)
            try:
                old = _keyed(python_declarations(src)) if src is not None else {}
            except SyntaxError:
                old = {}
        now = _keyed(decls)
        for key, d in now.items():
            kind, source = _kind_and_source(d, rel, plugin)
            refs = _local_refs(d, rel, py) if d.scope == "function" else _wide_refs(d, rel, py)
            change = "unchanged"
            if old is not None:
                prev = old.get(key)
                change = "added" if prev is None else ("modified" if sha256_text(prev.content) != sha256_text(d.content)
                                                       else "unchanged")
            entities.append(new_entity("N1", kind, d.name, rel, d.container, (d.line, d.end), source=source,
                                       content=d.content, extractor=EXTRACTOR, references=refs, search_coverage=cov,
                                       change=change))
        if old:
            for key, d in old.items():
                if key not in now:
                    entities.append(_removed_n1(d, rel, plugin, py, cov))
    for rel in sorted(deleted):
        if not rel.endswith(".py"):
            continue
        src = _old_source(root, changed, rel)
        try:
            for d in (python_declarations(src) if src else []):
                entities.append(_removed_n1(d, rel, plugin, py, cov))
        except SyntaxError:
            skipped.append({"path": rel, "reason": f"syntax error at {changed}"})
    return new_inventory("N1", scopes, len(parsed), entities, _now(), changed_since=changed,
                         skipped_inputs=skipped or None)


def _removed_n1(d: _Decl, rel: str, plugin: bool, py: PyIndex, cov) -> dict:
    kind, source = _kind_and_source(d, rel, plugin)
    refs = [] if d.scope == "function" else _wide_refs(d, rel, py)
    return new_entity("N1", kind, d.name, rel, d.container, (d.line, d.end), source=source, content=d.content,
                      extractor=EXTRACTOR, references=refs, search_coverage=cov, change="removed")


# ---------------------------------------------------------------------------------------------------------------- N2


def _manifest_paths(root: Path, files) -> set[str]:
    """Paths a JSON manifest in scope lists in an object that also carries a sha256."""
    out: set[str] = set()

    def visit(node):
        if isinstance(node, dict):
            if any("sha256" in str(k).lower() for k in node):
                for v in node.values():
                    if isinstance(v, str) and ("/" in v or "." in v) and len(v) < 512:
                        out.add(v.lstrip("./"))
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)
    for rel in files:
        if rel.endswith(".json"):
            text = read_text(root, rel)
            try:
                visit(json.loads(text)) if text else None
            except ValueError:
                pass
    return out


def _file_digest(path: Path) -> str:
    if path.is_dir():
        return sha256_text("\n".join(sorted(c.name for c in path.iterdir())))
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def extract_n2(root: Path, scopes, changed: str | None = None) -> dict:
    root = Path(root).resolve()
    paths = walk(root, scopes)
    files = [p for p in paths if (root / p).is_file()]
    index, mentions = TextIndex(root, files), PathIndex(root, files)
    manifest = _manifest_paths(root, paths)
    cov = coverage(["N2", "N14"], scopes)
    touched, deleted = (_changed_files(root, changed, scopes) if changed else (set(), set()))
    entities = []
    for rel in paths:
        p = PurePosixPath(rel)
        name = p.name
        parent = p.parent.as_posix()
        is_dir = (root / rel).is_dir()
        hits = mentions.find(rel) + ([] if is_dir else index.find(name))
        if p.suffix and not is_dir:
            hits += [h for h in index.find(p.stem) if h[0].endswith(".tex")]
        refs = [{"from": f"{f}:{n}", "kind": "mentions"} for f, n in dict.fromkeys(hits) if f != rel]
        kind = "manifest_checksummed" if rel in manifest else "output"
        change = "unchanged"
        if changed:
            change = "added" if rel in touched and _old_source(root, changed, rel) is None and (root / rel).is_file() \
                else ("modified" if rel in touched else "unchanged")
        content = _file_digest(root / rel)
        ent = new_entity("N2", kind, name, rel, parent, (0, 0), source="external" if name in CONVENTIONAL_FILES else "project",
                         extractor=EXTRACTOR, references=refs, search_coverage=cov, change=change)
        ent["content_sha256"] = content
        entities.append(ent)
    for rel in sorted(deleted):
        p = PurePosixPath(rel)
        refs = [{"from": f"{f}:{n}", "kind": "mentions"} for f, n in index.find(p.name)]
        entities.append(new_entity("N2", "output", p.name, rel, p.parent.as_posix(), (0, 0), extractor=EXTRACTOR,
                                   references=refs, search_coverage=cov, change="removed", content=rel))
    return new_inventory("N2", scopes, len(paths), entities, _now(), changed_since=changed)


# ---------------------------------------------------------------------------------------------------------------- N5


def _str_arg(call: ast.Call, i: int = 0):
    if len(call.args) > i and isinstance(call.args[i], ast.Constant) and isinstance(call.args[i].value, str):
        return call.args[i].value
    return None


def _env_name(node) -> tuple[str, int] | None:
    """The variable an os.environ / os.getenv read names, with its line."""
    if isinstance(node, ast.Call):
        f = ast.unparse(node.func)
        if f in ("os.getenv", "getenv", "os.environ.get", "environ.get", "os.environ.setdefault", "environ.setdefault"):
            name = _str_arg(node)
            return (name, node.lineno) if name else None
    if isinstance(node, ast.Subscript) and ast.unparse(node.value) in ("os.environ", "environ") \
            and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
        return node.slice.value, node.lineno
    return None


def _config_keys(text: str, suffix: str):
    """(key, container) pairs of a configuration file, duplicates kept; raises ValueError when unreadable."""
    out: list[tuple[str, str]] = []
    if suffix == ".json":
        def hook(pairs):
            return {"__pairs__": pairs}

        def visit(node, path):
            if isinstance(node, dict) and "__pairs__" in node:
                for k, v in node["__pairs__"]:
                    out.append((k, path or "<root>"))
                    visit(v, f"{path}.{k}" if path else k)
            elif isinstance(node, list):
                for v in node:
                    visit(v, path)
        visit(json.loads(text, object_pairs_hook=hook), "")
    elif suffix == ".toml":
        def walk_toml(table, path):
            for k, v in table.items():
                out.append((k, path or "<root>"))
                if isinstance(v, dict):
                    walk_toml(v, f"{path}.{k}" if path else k)
        try:
            walk_toml(tomllib.loads(text), "")
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(str(exc)) from exc
    elif suffix in (".ini", ".cfg"):
        cp = configparser.ConfigParser(strict=False)
        try:
            cp.read_string(text)
        except configparser.Error as exc:
            raise ValueError(str(exc)) from exc
        for sec in cp.sections():
            out.append((sec, "<root>"))
            for k in cp[sec]:
                out.append((k, sec))
    else:
        import yaml  # optional: the caller checks it is installed

        def walk_yaml(node, path):
            if isinstance(node, dict):
                for k, v in node.items():
                    out.append((str(k), path or "<root>"))
                    walk_yaml(v, f"{path}.{k}" if path else str(k))
            elif isinstance(node, list):
                for v in node:
                    walk_yaml(v, path)
        walk_yaml(yaml.safe_load(text), "")
    return out


def _line_of(text: str, needle: str) -> int:
    for n, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return n
    return 1


def extract_n5(root: Path, scopes, changed: str | None = None) -> dict:
    root = Path(root).resolve()
    paths = [p for p in walk(root, scopes) if (root / p).is_file()]
    plugin = is_plugin(root)
    words, flags = TextIndex(root, paths), TextIndex(root, paths, FLAG)
    try:
        import yaml  # noqa: F401
        have_yaml = True
    except ImportError:
        have_yaml = False
    entities, skipped, scanned = [], [], 0
    decls: list[tuple] = []  # (kind, name, file, container, line, content)
    env_first: dict[str, tuple] = {}
    for rel in paths:
        text = None
        if rel.endswith(".py"):
            text = read_text(root, rel)
            try:
                tree = ast.parse(text) if text is not None else None
            except SyntaxError:
                tree = None
            if tree is None:
                skipped.append({"path": rel, "reason": "unreadable or not valid Python"})
                continue
            scanned += 1
            flag_kind = "plugin_cli_flag" if plugin and PurePosixPath(rel).parts[0] in PLUGIN_SCRIPT_DIRS else "project_cli_flag"
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
                    receiver = ast.unparse(node.func.value)
                    for a in node.args:
                        if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("-"):
                            decls.append((flag_kind, a.value, rel, receiver, node.lineno, ast.unparse(node)))
                env = _env_name(node)
                if env and env[0] not in env_first:
                    env_first[env[0]] = ("env_var", env[0], rel, "<environment>", env[1], env[0])
        elif not plugin and CONFIG_NAME.search(rel):
            suffix = PurePosixPath(rel).suffix.lower()
            if suffix in (".yaml", ".yml") and not have_yaml:
                skipped.append({"path": rel, "reason": "YAML needs PyYAML (pip install pyyaml), which is not installed"})
                continue
            text = read_text(root, rel)
            try:
                keys = _config_keys(text, suffix) if text is not None else None
            except Exception as exc:  # any parser error: the file is listed as skipped, never silently dropped
                keys = None
                skipped.append({"path": rel, "reason": f"cannot parse: {str(exc)[:120]}"})
                continue
            if keys is None:
                skipped.append({"path": rel, "reason": "unreadable or larger than 2 MB"})
                continue
            scanned += 1
            for k, container in keys:
                decls.append(("project_config_key", k, rel, container, _line_of(text, k), f"{container}:{k}"))
    decls += list(env_first.values())
    cov = coverage(["N5", "N1"], scopes) if not skipped else [f"N5:{p}" for p in paths]
    for kind, name, rel, container, line, content in decls:
        index = flags if name.startswith("-") else words
        hits = [h for h in index.find(name) if h != (rel, line)]
        refs = [{"from": f"{f}:{n}", "kind": "mentions"} for f, n in hits]
        entities.append(new_entity("N5", kind, name, rel, container, (line, line), content=content,
                                   extractor=EXTRACTOR, references=refs, search_coverage=cov))
    if changed:
        _mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N5", scopes, scanned, entities, _now(), changed_since=changed, skipped_inputs=skipped or None)


def _mark_changed_by_file(root: Path, rev: str, scopes, entities) -> None:
    """Names in files changed since rev: added when absent from the old file's text, else modified."""
    touched, _ = _changed_files(root, rev, scopes)
    for e in entities:
        rel = e["scope"]["file"]
        if rel in touched:
            old = _old_source(root, rev, rel)
            e["change"] = "added" if old is None or e["name"] not in old else "modified"


# --------------------------------------------------------------------------------------------------------------- N16


def extract_n16(root: Path, scopes, changed: str | None = None) -> dict:
    root = Path(root).resolve()
    if not is_plugin(root):
        return new_inventory("N16", scopes, 0, [], _now(), changed_since=changed)
    paths = [p for p in walk(root, scopes) if (root / p).is_file()]
    index = TextIndex(root, paths)
    decls: list[tuple] = []  # (kind, name, file, container, line)
    scanned = 0

    def text_of(rel):
        return read_text(root, rel) or ""
    env = "contracts/schemas/envelope.json"
    if (root / env).is_file():
        scanned += 1
        for t in json.loads(text_of(env))["properties"]["artifact_type"]["enum"]:
            decls.append(("contract_term", t, env, "artifact_type", _line_of(text_of(env), f'"{t}"')))
    for vf in sorted((root / "contracts" / "vocab").glob("*.json")):
        rel = vf.relative_to(root).as_posix()
        doc, text = json.loads(text_of(rel)), text_of(rel)
        scanned += 1
        for vname, terms in (doc.get("vocabularies") or {}).items():
            decls.append(("contract_term", vname, rel, "vocabularies", _line_of(text, f'"{vname}"')))
            for t in terms:
                decls.append(("contract_term", t, rel, vname, _line_of(text, f'"{t}"')))
        for key, field in (("classes", "class_id"), ("effects", "effect_id"), ("compositions", "composition_id")):
            for item in doc.get(key, []) or []:
                if isinstance(item, dict) and item.get(field):
                    decls.append(("contract_term", item[field], rel, key, _line_of(text, f'"{item[field]}"')))
    for sk in sorted((root / "skills").glob("*/SKILL.md")):
        scanned += 1
        decls.append(("skill_name", sk.parent.name, sk.relative_to(root).as_posix(), "skills", 1))
        for sc in sorted((sk.parent / "scripts").glob("*")):
            if sc.is_file() and sc.suffix in (".py", ".sh", ".C"):
                decls.append(("script_name", sc.name, sc.relative_to(root).as_posix(), f"skills/{sk.parent.name}/scripts", 1))
    for sch in sorted((root / "contracts" / "schemas").glob("*.json")):
        decls.append(("schema_name", sch.name, sch.relative_to(root).as_posix(), "contracts/schemas", 1))
    cov = coverage(["N16"], scopes)
    entities = []
    for kind, name, rel, container, line in decls:
        refs = [{"from": f"{f}:{n}", "kind": "mentions"} for f, n in index.find(name) if (f, n) != (rel, line)]
        entities.append(new_entity("N16", kind, name, rel, container, (line, line), content=f"{container}:{name}",
                                   extractor=EXTRACTOR, references=refs, search_coverage=cov))
    if changed:
        _mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N16", scopes, scanned, entities, _now(), changed_since=changed)


EXTRACT = {"N1": extract_n1, "N2": extract_n2, "N5": extract_n5, "N16": extract_n16}


def artifacts_dir(root: Path) -> Path | None:
    cfg = root / "hep-research.project.json"
    try:
        rel = json.loads(cfg.read_text(encoding="utf-8")).get("artifacts_dir", "./hep-research-artifacts/")
    except (OSError, ValueError):
        return None
    return (root / rel).resolve()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--surface", required=True, help="N1, N2, N5 or N16")
    ap.add_argument("--out", type=Path, required=True, help="inventory file to write (never inside artifacts_dir)")
    ap.add_argument("--root", type=Path, default=Path("."), help="project root (default: the working directory)")
    ap.add_argument("--scope", action="append", help="folder relative to the root to scan (repeatable; default the root)")
    ap.add_argument("--changed", metavar="REV", help="git revision to mark added, modified and removed names against")
    add_status_argument(ap)
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    def reject(msg: str) -> int:
        print(json.dumps({"status": "rejected", "error": msg}))
        return 2
    if args.surface not in EXTRACT:
        return reject(f"--surface {args.surface}: this extractor reads {', '.join(SURFACES)}; another surface's owner "
                      "provides its extractor (contracts/naming_check.py surfaces)")
    root = args.root.resolve()
    if not root.is_dir():
        return reject(f"--root {args.root} is not a directory")
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
        inv = EXTRACT[args.surface](root, scopes, args.changed)
    except ValueError as exc:
        return reject(str(exc))
    except subprocess.TimeoutExpired:
        return reject(f"git did not answer within {GIT_TIMEOUT_S} s while comparing against {args.changed}")
    try:
        out.write_text(json.dumps(inv, indent=1) + "\n", encoding="utf-8")
    except OSError as exc:
        return reject(f"cannot write {args.out}: {exc}")
    status = "written" if inv["inputs_scanned"] else "incomplete"
    print(json.dumps({"status": status, "status_label": args.status, "out": str(args.out), "surface": args.surface, "entities": len(inv["entities"]),
                      "inputs_scanned": inv["inputs_scanned"], "skipped_inputs": len(inv.get("skipped_inputs", [])),
                      **({"note": "zero inputs scanned: the check reports this surface unsupported"} if not inv["inputs_scanned"] else {})},
                     indent=1))
    return 0 if inv["inputs_scanned"] else 3


if __name__ == "__main__":
    sys.exit(main())
