"""Execution trace for artifact provenance (contracts 3.5.0; sci-fix improvement plan A1, maintainer decision
2026-10-22).

provenance() returns the two optional envelope fields a producer adds to `provenance` when it writes an artifact:
  code_paths  the plugin's .py files the writing process had loaded (a snapshot of sys.modules, plugin-relative POSIX
              paths, sorted, without duplicates; the test suite under tests/ is left out). Loaded is not executed: a
              module imported for one helper is listed whole, so the field narrows which advisories can apply; it
              never proves that a defect touched a result.
  code_tags   the tags that advisory-named shared functions set with tag() since the previous envelope (sorted). Tags
              are per envelope: provenance() returns and clears them, so two artifacts written by one process never
              share tags.
A script run as a subprocess is recorded by its own envelope, not by its parent's.

The implementation lives in core so that shared core functions can call tag() (core never imports contracts);
contracts.trace is the public import path for envelope writers and re-exports every name.
"""
from __future__ import annotations

import re
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_tags: set[str] = set()
_lock = threading.Lock()


def tag(name: str) -> None:
    """Record that an advisory-named shared function ran (lower-case words joined by '-')."""
    if not TAG.match(name):
        raise ValueError(f"code tag {name!r} must match {TAG.pattern}")
    with _lock:
        _tags.add(name)


def code_paths(root: Path = ROOT) -> list[str]:
    """The plugin .py files among the loaded modules (the running script included)."""
    base, found = root.resolve(), set()
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if not isinstance(path, str) or not path.endswith(".py"):
            continue
        try:
            rel = Path(path).resolve().relative_to(base)
        except (OSError, ValueError):
            continue
        if "__pycache__" not in rel.parts and rel.parts[0] != "tests":
            found.add(rel.as_posix())
    return sorted(found, key=lambda p: p.encode("utf-8"))


def provenance(root: Path = ROOT) -> dict:
    """{"code_paths", "code_tags"} for the envelope being written; clears the tags."""
    with _lock:
        tags = sorted(_tags)
        _tags.clear()
    return {"code_paths": code_paths(root), "code_tags": tags}
