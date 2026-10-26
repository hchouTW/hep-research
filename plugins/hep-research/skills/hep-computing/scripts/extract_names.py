#!/usr/bin/env python3
"""Naming extractor of hep-computing (semantic naming charter, references/semantic-naming.md): write the naming
inventory of one surface for contracts/naming_check.py.

Surfaces:
  N1  code identifiers of Python files: functions, classes, module and class variables, instance attributes
      (self.x = ...), parameters and local variables. C++ and shell are not read yet (say so when they matter).
  N2  files and directories; a file whose path a JSON manifest in scope lists next to a sha256 is manifest_checksummed.
  N3  objects inside ROOT files (every folder); a histogram named ...Up or ...Down is a shape_histogram. Read with
      uproot, else PyROOT; without either each ROOT file is listed in skipped_inputs (zero inputs: unsupported).
      References: text mentions in every text file in scope (code, datacards, LaTeX), so the search covers N10, N14.
  N4  branches and columns: TTree branches of ROOT files (as N3), Parquet columns (with pyarrow), and columns code
      defines (RDataFrame Define, Redefine, Alias in Python and C++); TTree branches and RNTuple fields alike.
      --external PATH marks official ntuples.
  N5  argparse flags and environment variables read by Python code; keys of JSON, TOML and INI configuration files
      (YAML too when PyYAML is installed; otherwise each YAML file is listed in skipped_inputs and references stay
      partial). In the plugin itself, configuration files are contract definitions (N16) and are not read here.
  N16 the plugin's contract vocabulary: artifact types, vocabulary terms (contracts/vocab), effect, class and
      composition ids, skill, script and schema names. Only in the plugin; elsewhere it scans zero inputs.
  N6  batch jobs, workflow rules and chunks: Snakemake rules and log patterns, Slurm job names and output patterns,
      HTCondor batch names and log, output and error patterns, run_workflow.py step ids, partition chunk ids.
The inventory holds every name of the surface within the scope folders, each with its references found by a search
of every text file in scope (search_coverage says what was searched), its kind and its source (external: names an
outside API or tool fixes, such as __init__, setUp, README.md). With --changed REV (a git revision) each name is
marked added, modified (same name, other content) or unchanged, and names removed since REV are included with
change removed; the inventory is never reduced to the changed names.

Usage: python3 extract_names.py --surface N1|N2|N3|N4|N5|N6|N16 --out INV.json [--root DIR] [--scope DIR ...]
       [--changed REV] [--external PATH ...]
--root is the project (default: the working directory); --scope folders are relative to it (default: the root). The
output is a working file of <project>/naming/, refused inside the project's artifacts_dir. Prints one JSON object
with a status key. Exit codes: 0 written, 2 bad input (unknown surface, scope outside the root, bad revision, unwritable
output), 3 written but zero inputs scanned (the check reports the surface unsupported). Standard library only; N3
and N4 read ROOT files with uproot or PyROOT and Parquet with pyarrow when installed.
"""
from __future__ import annotations

import ast
import configparser
import json
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True  # a script run from an installed plugin leaves no __pycache__ in it
PLUGIN = Path(__file__).resolve().parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from core.naming.extract import (GIT_TIMEOUT_S, PathIndex, TextIndex, changed_files, coverage,  # noqa: E402,F401
                                 file_digest, is_plugin, line_of, main as run_cli, mark_changed_by_file,
                                 old_source, read_text, walk)
from core.naming.extract import Builder  # noqa: E402
from core.naming.extract import now as _now  # noqa: E402
from core.naming.model import new_entity, new_inventory, sha256_text  # noqa: E402
from core.naming.vocab import hook_methods  # noqa: E402
from core.status import add_status_argument  # noqa: E402

VERSION = "1.1.0"
EXTRACTOR = {"id": "skills/hep-computing/scripts/extract_names.py", "version": VERSION}
CONVENTIONAL_FILES = {"README.md", "LICENSE", "CHANGELOG.md", "Makefile", "CMakeLists.txt", "__init__.py", "__main__.py",
                      "setup.py", "setup.cfg", "pyproject.toml", "requirements.txt", ".gitignore", "SKILL.md",
                      "Snakefile", "conftest.py", "Dockerfile", "plugin.json", "OWNERS.json", "hep-research.project.json"}
SKIP_DECORATORS = re.compile(r"(?:\.setter|\.getter|\.deleter|\.register|^overload|\.overload)$")
FLAG = re.compile(r"(?<![A-Za-z0-9_-])--?[A-Za-z0-9][A-Za-z0-9_-]*")
CONFIG_NAME = re.compile(r"(?i)(config|settings|options)[^/]*\.json$|\.toml$|\.ini$|\.cfg$|\.ya?ml$")
CORE_API_DIRS = ("core", "contracts")
PLUGIN_SCRIPT_DIRS = ("skills", "tools", "contracts", "core", "adapters")


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


def _keyed(decls) -> dict[tuple, _Decl]:
    out, count = {}, {}
    for d in decls:
        k = (d.container, d.name, d.decl_type == "variable")
        count[k] = count.get(k, 0) + 1
        out[k + (count[k],)] = d
    return out


def extract_n1(root: Path, scopes, changed: str | None = None, args=None) -> dict:
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
    touched, deleted = (changed_files(root, changed, scopes) if changed else (set(), set()))
    entities = []
    for rel, text in parsed.items():
        decls = python_declarations(text)
        old = None
        if changed and rel in touched:
            src = old_source(root, changed, rel)
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
        src = old_source(root, changed, rel)
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


def extract_n2(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    root = Path(root).resolve()
    paths = walk(root, scopes)
    files = [p for p in paths if (root / p).is_file()]
    index, mentions = TextIndex(root, files), PathIndex(root, files)
    manifest = _manifest_paths(root, paths)
    cov = coverage(["N2", "N14"], scopes)
    touched, deleted = (changed_files(root, changed, scopes) if changed else (set(), set()))
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
            change = "added" if rel in touched and old_source(root, changed, rel) is None and (root / rel).is_file() \
                else ("modified" if rel in touched else "unchanged")
        content = file_digest(root / rel)
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


def extract_n5(root: Path, scopes, changed: str | None = None, args=None) -> dict:
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
                decls.append(("project_config_key", k, rel, container, line_of(text, k), f"{container}:{k}"))
    decls += list(env_first.values())
    cov = coverage(["N5", "N1"], scopes) if not skipped else [f"N5:{p}" for p in paths]
    for kind, name, rel, container, line, content in decls:
        index = flags if name.startswith("-") else words
        hits = [h for h in index.find(name) if h != (rel, line)]
        refs = [{"from": f"{f}:{n}", "kind": "mentions"} for f, n in hits]
        entities.append(new_entity("N5", kind, name, rel, container, (line, line), content=content,
                                   extractor=EXTRACTOR, references=refs, search_coverage=cov))
    if changed:
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N5", scopes, scanned, entities, _now(), changed_since=changed, skipped_inputs=skipped or None)


# --------------------------------------------------------------------------------------------------------------- N16


def extract_n16(root: Path, scopes, changed: str | None = None, args=None) -> dict:
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
            decls.append(("contract_term", t, env, "artifact_type", line_of(text_of(env), f'"{t}"')))
    for vf in sorted((root / "contracts" / "vocab").glob("*.json")):
        rel = vf.relative_to(root).as_posix()
        doc, text = json.loads(text_of(rel)), text_of(rel)
        scanned += 1
        for vname, terms in (doc.get("vocabularies") or {}).items():
            decls.append(("contract_term", vname, rel, "vocabularies", line_of(text, f'"{vname}"')))
            for t in terms:
                decls.append(("contract_term", t, rel, vname, line_of(text, f'"{t}"')))
        for key, field in (("classes", "class_id"), ("effects", "effect_id"), ("compositions", "composition_id")):
            for item in doc.get(key, []) or []:
                if isinstance(item, dict) and item.get(field):
                    decls.append(("contract_term", item[field], rel, key, line_of(text, f'"{item[field]}"')))
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
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N16", scopes, scanned, entities, _now(), changed_since=changed)


# ----------------------------------------------------------------------------------------------------- N3 and N4


def root_reader():
    """The ROOT reader in use: uproot first, PyROOT second (F17), None without either."""
    try:
        import uproot  # noqa: F401
        return "uproot"
    except ImportError:
        pass
    try:
        import ROOT  # noqa: F401
        return "pyroot"
    except Exception:  # a broken PyROOT install raises more than ImportError
        return None


def _hist_digest(stored, classname: str) -> str:
    try:
        return sha256_text(classname + ":" + stored.values(flow=True).tobytes().hex())
    except Exception:
        return sha256_text(classname)


def root_objects(path: Path, reader: str) -> list[tuple[str, str, str, list[str]]]:
    """(folder inside the file, object name, class name, content digest, branch or field names of a TTree or RNTuple)
    for every object."""
    out = []
    if reader == "uproot":
        import uproot
        with uproot.open(path) as f:
            for key, cls in f.classnames(recursive=True, cycle=False).items():
                folder, _, name = key.rpartition("/")
                stored = None
                branches: list[str] = []
                if cls.startswith(("TTree", "TNtuple", "ROOT::RNTuple")):
                    stored = f[key]
                    branches = list(stored.keys(recursive=True, full_paths=False) if cls.startswith("T")
                                    else stored.keys())
                    digest = sha256_text(cls + ":" + ",".join(branches) + f":{stored.num_entries}")
                elif cls.startswith(("TH1", "TH2", "TH3", "TProfile")):
                    stored = f[key]
                    digest = _hist_digest(stored, cls)
                else:
                    digest = sha256_text(cls + ":" + key)
                out.append((folder or "/", name, cls, digest, branches))
        return out
    import ROOT
    f = ROOT.TFile.Open(str(path))
    if not f or f.IsZombie():
        raise OSError(f"cannot open {path}")

    def visit(d, folder):
        for k in d.GetListOfKeys():
            cls, name = k.GetClassName(), k.GetName()
            stored = k.ReadObj()
            if stored.InheritsFrom("TDirectory"):
                visit(stored, f"{folder}/{name}".lstrip("/"))
                continue
            branches = [b.GetName() for b in stored.GetListOfBranches()] if stored.InheritsFrom("TTree") else []
            digest = sha256_text(f"{cls}:{name}:" + (",".join(branches) if branches else
                                 (str([stored.GetBinContent(i) for i in range(stored.GetNcells())]) if stored.InheritsFrom("TH1") else "")))
            out.append((folder or "/", name, cls, digest, branches))
    visit(f, "")
    f.Close()
    return out


def _external(rel: str, args) -> bool:
    return any(rel == x or rel.startswith(x.rstrip("/") + "/") for x in (getattr(args, "external", None) or []))


def _root_entities(surface: str, root: Path, rel: str, reader: str, path: Path, args) -> list[tuple]:
    """(kind, name, container, content digest, source) for the N3 objects or the N4 branches of one ROOT file."""
    source = "external" if _external(rel, args) else "project"
    out = []
    for folder, name, cls, digest, branches in root_objects(path, reader):
        if surface == "N3":
            kind = "shape_histogram" if cls.startswith(("TH1", "TH2", "TH3")) and re.search(r".(Up|Down)$", name) else "object"
            out.append((kind, name, folder, digest, source))
        else:
            for b in branches:
                out.append(("project_column", b, f"{folder.rstrip('/')}/{name}".lstrip("/"), sha256_text(f"{name}:{b}"), source))
    return out


DEFINE = re.compile(r"\.(?:Define|Redefine|Alias)\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']")
CODE_SUFFIXES = (".py", ".C", ".cc", ".cxx", ".cpp", ".h", ".hh", ".hpp")


def _extract_root(surface: str, root: Path, scopes, changed, args) -> dict:
    root = Path(root).resolve()
    paths = [p for p in walk(root, scopes) if (root / p).is_file()]
    index = TextIndex(root, paths)
    reader = root_reader()
    skipped, scanned, rows = [], 0, []  # rows: (kind, name, file, container, line, digest, source)
    root_files = [p for p in paths if p.endswith(".root")]

    def read_file(rel: str, path: Path) -> list[tuple]:
        return [(k, n, rel, c, 0, d, src) for k, n, c, d, src in _root_entities(surface, root, rel, reader, path, args)]
    for rel in root_files:
        if reader is None:
            skipped.append({"path": rel, "reason": "no ROOT reader: install uproot (pip install uproot) or PyROOT"})
            continue
        try:
            rows += read_file(rel, root / rel)
            scanned += 1
        except Exception as exc:  # an unreadable file is listed, never silently dropped
            skipped.append({"path": rel, "reason": f"cannot read: {str(exc)[:120]}"})
    if surface == "N4":
        for rel in paths:
            if rel.endswith(CODE_SUFFIXES):
                text = read_text(root, rel)
                if text is None:
                    continue
                scanned += 1
                for n, line in enumerate(text.splitlines(), 1):
                    for m in DEFINE.finditer(line):
                        rows.append(("project_column", m.group(1), rel, "<defined-columns>", n, sha256_text(line.strip()),
                                     "project"))
            elif rel.endswith(".parquet"):
                try:
                    import pyarrow.parquet as pq
                except ImportError:
                    skipped.append({"path": rel, "reason": "Parquet needs pyarrow (pip install pyarrow), which is not installed"})
                    continue
                try:
                    names = pq.read_schema(root / rel).names
                except Exception as exc:
                    skipped.append({"path": rel, "reason": f"cannot read: {str(exc)[:120]}"})
                    continue
                scanned += 1
                src = "external" if _external(rel, args) else "project"
                rows += [("project_column", c, rel, "<schema>", 0, sha256_text(f"{rel}:{c}"), src) for c in names]
    reached = ["N3", "N10", "N14"] if surface == "N3" else ["N4"]
    cov = coverage(reached, scopes) if not skipped else [f"{surface}:{p}" for p in paths if not any(p == x["path"] for x in skipped)]

    def entity(row, change="unchanged"):
        kind, name, rel, container, line, digest, src = row
        refs = [r for r in index.refs(name, (rel, line)) if r["from"] != f"{rel}:{line}"]
        e = new_entity(surface, kind, name, rel, container, (line, line), source=src, extractor=EXTRACTOR, references=refs,
                       search_coverage=cov, change=change)
        e["content_sha256"] = digest
        return e
    entities = [entity(r) for r in rows]
    if changed:
        import tempfile

        def read_old(rel, raw):
            if raw is None or not rel.endswith(".root") or reader is None:
                return []
            with tempfile.TemporaryDirectory() as scratch:
                p = Path(scratch) / "old.root"
                p.write_bytes(raw)
                try:
                    return [entity(r) for r in read_file(rel, p)]
                except Exception:
                    return []
        from core.naming.extract import mark_changes
        if surface == "N4":
            mark_changed_by_file(root, changed, scopes, [e for e in entities if not e["scope"]["file"].endswith(".root")])
            root_ents = [e for e in entities if e["scope"]["file"].endswith(".root")]
        else:
            root_ents = entities
        entities += mark_changes(root, changed, scopes, root_ents, read_old)
    return new_inventory(surface, scopes, scanned, entities, _now(), changed_since=changed, skipped_inputs=skipped or None)


def extract_n3(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    return _extract_root("N3", root, scopes, changed, args)


def extract_n4(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    return _extract_root("N4", root, scopes, changed, args)


# ---------------------------------------------------------------------------------------------------------------- N6

SNAKE_RULE = re.compile(r"^\s*rule\s+([A-Za-z_][A-Za-z0-9_]*)\s*:")
SNAKE_LOG = re.compile(r"^\s*log\s*:\s*[\"']([^\"']+)[\"']")
SBATCH = re.compile(r"^#SBATCH\s+(?:--job-name[= ]|-J\s+)(\S+)")
SBATCH_LOG = re.compile(r"^#SBATCH\s+(?:--output|--error|-o|-e)[= ]\s*(\S+)")
CONDOR = re.compile(r"^\s*(batch_name|JobBatchName|log|output|error)\s*=\s*(\S+)", re.I)
SUBMIT_SUFFIXES = (".sub", ".jdl", ".condor", ".submit")


def extract_n6(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    """Batch and workflow names: Snakemake rules and log patterns, Slurm job names and output patterns, HTCondor
    batch names and log/output/error patterns, workflow-runner step ids (run_workflow.py JSON) and partition chunk ids
    (local_partition.py manifests)."""
    root = Path(root).resolve()
    paths = [p for p in walk(root, scopes) if (root / p).is_file()]
    index = TextIndex(root, paths)
    b = Builder("N6", EXTRACTOR)
    scanned = 0
    for rel in paths:
        name = PurePosixPath(rel).name
        text = None
        if name == "Snakefile" or rel.endswith(".smk"):
            text = read_text(root, rel)
            if text is None:
                continue
            scanned += 1
            rule = "<workflow>"
            for n, line in enumerate(text.splitlines(), 1):
                m = SNAKE_RULE.match(line)
                if m:
                    rule = m.group(1)
                    b.add("job", rule, rel, "<rules>", n, line.strip())
                m = SNAKE_LOG.match(line)
                if m:
                    b.add("log_pattern", m.group(1), rel, rule, n, line.strip(), refs=[])
        elif rel.endswith((".sh", ".slurm", ".sbatch")) or rel.endswith(SUBMIT_SUFFIXES):
            text = read_text(root, rel)
            if text is None or ("#SBATCH" not in text and not rel.endswith(SUBMIT_SUFFIXES)):
                continue
            scanned += 1
            for n, line in enumerate(text.splitlines(), 1):
                for pat, kind in ((SBATCH, "job"), (SBATCH_LOG, "log_pattern")):
                    m = pat.match(line)
                    if m:
                        b.add(kind, m.group(1), rel, "<slurm>", n, line.strip(), refs=None if kind == "job" else [])
                m = CONDOR.match(line) if rel.endswith(SUBMIT_SUFFIXES) else None
                if m:
                    kind = "job" if m.group(1).lower() in ("batch_name", "jobbatchname") else "log_pattern"
                    b.add(kind, m.group(2).strip("\"'"), rel, "<condor>", n, line.strip(), refs=None if kind == "job" else [])
        elif rel.endswith(".json"):
            text = read_text(root, rel)
            if text is None or ('"steps"' not in text and '"chunks"' not in text):
                continue
            try:
                doc = json.loads(text)
            except ValueError:
                continue
            if isinstance(doc, dict) and isinstance(doc.get("steps"), list) and "workflow" in doc:
                scanned += 1
                for st in doc["steps"]:
                    if isinstance(st, dict) and isinstance(st.get("id"), str):
                        b.add("job", st["id"], rel, str(doc.get("workflow")), line_of(text, f'"{st["id"]}"'),
                              json.dumps(st, sort_keys=True))
            elif isinstance(doc, dict) and isinstance(doc.get("chunks"), list):
                scanned += 1
                for ch in doc["chunks"]:
                    cid = ch.get("chunk_id", ch.get("id")) if isinstance(ch, dict) else None
                    if isinstance(cid, (str, int)):
                        b.add("chunk", str(cid), rel, "<chunks>", line_of(text, str(cid)), json.dumps(ch, sort_keys=True),
                              refs=[])
    entities = b.build(index, coverage(["N6"], scopes))
    if changed:
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N6", scopes, scanned, entities, _now(), changed_since=changed)


EXTRACT = {"N1": extract_n1, "N2": extract_n2, "N3": extract_n3, "N4": extract_n4, "N5": extract_n5, "N6": extract_n6,
           "N16": extract_n16}


def _options(ap) -> None:
    ap.add_argument("--external", action="append", metavar="PATH",
                    help="N3/N4: a file or folder (relative to the root) of inputs made outside the project, such as "
                         "official ntuples; its names are source external (C4, never renamed)")
    add_status_argument(ap)


def main(argv=None) -> int:
    return run_cli(argv, doc=__doc__, readers={**EXTRACT, "__options__": _options}, extractor=EXTRACTOR)


if __name__ == "__main__":
    sys.exit(main())
