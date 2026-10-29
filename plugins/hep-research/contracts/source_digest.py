"""Function-level source digests of rule implementations (P3, G18): a rule's digest covers its own code and every
plugin function, class and constant it reaches by name, so a change to a shared helper changes the digest of each
rule that uses it. contracts/naming_registry.py compares the digest of each naming predicate with the one its registry
records: a predicate whose code changed without a new version fails the registry check. (Moved from
contracts/analysis_checks/ when the cross-artifact check was retired.)

The digest is formatting-insensitive: comments, blank lines, line breaks inside brackets and docstrings are dropped,
the remaining tokens are kept in order (indentation as INDENT/DEDENT markers). Constants are digested by their
repr (sets sorted). Standard library only."""
from __future__ import annotations

import ast
import hashlib
import inspect
import io
import json
import textwrap
import tokenize
import types

PREFIXES = ("contracts.", "core.")


def _docstring_lines(tree: ast.AST) -> set[int]:
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                out |= set(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return out


def normalized(source: str) -> str:
    source = textwrap.dedent(source)
    doc = _docstring_lines(ast.parse(source))
    toks = []
    for t in tokenize.generate_tokens(io.StringIO(source).readline):
        structural = t.type in (tokenize.INDENT, tokenize.DEDENT)
        if t.type in (tokenize.COMMENT, tokenize.NL, tokenize.ENDMARKER) or (t.start[0] in doc and not structural):
            continue
        toks.append(tokenize.tok_name[t.type] if t.type in (tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE) else t.string)
    return " ".join(toks)


def _ours(target) -> bool:
    return str(getattr(target, "__module__", "") or "").startswith(PREFIXES)


def _constant(value) -> str | None:
    if isinstance(value, (set, frozenset)):
        return repr(sorted(value, key=repr))
    if isinstance(value, (str, int, float, bool, tuple, list, dict, type(None))):
        return repr(value)
    return None


def _referenced(fn_or_cls) -> list[tuple[str, object]]:
    """(name, object) pairs the code reaches by name: plugin functions and classes, module attributes of plugin
    modules, and constants of the defining module."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn_or_cls)))
    module = inspect.getmodule(fn_or_cls)
    if module is None:
        return []
    scope = vars(module)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in scope:
            out.append((f"{module.__name__}.{node.id}", scope[node.id]))
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            mod = scope.get(node.value.id)
            if isinstance(mod, types.ModuleType) and mod.__name__.startswith(PREFIXES) and hasattr(mod, node.attr):
                out.append((f"{mod.__name__}.{node.attr}", getattr(mod, node.attr)))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(PREFIXES[0][:-1]):
            import importlib
            mod = importlib.import_module(node.module)
            out += [(f"{mod.__name__}.{a.name}", getattr(mod, a.name)) for a in node.names if hasattr(mod, a.name)]
    return out


def closure(fn) -> dict[str, str]:
    """{qualified name: normalized source or constant repr} for fn and everything it reaches in the plugin."""
    seen: dict[str, str] = {}
    todo = [(f"{fn.__module__}.{fn.__qualname__}", fn)]
    while todo:
        name, target = todo.pop()
        if name in seen:
            continue
        if inspect.isfunction(target) or inspect.isclass(target):
            own = f"{target.__module__}.{target.__qualname__}"  # keyed where it is defined, not by the importing name
            if not _ours(target) or own in seen:
                continue
            seen[own] = normalized(inspect.getsource(target))
            todo += _referenced(target)
        elif not isinstance(target, types.ModuleType):
            const = _constant(target)
            if const is not None and name.startswith(PREFIXES):
                seen[name] = const
    return seen


def source_digest(fn) -> str:
    return hashlib.sha256(json.dumps(closure(fn), sort_keys=True).encode("utf-8")).hexdigest()
