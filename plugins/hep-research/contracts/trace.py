"""Execution trace for artifact provenance (contracts 3.5.0): the public import path for envelope writers. The
implementation is core/trace.py (shared core functions call tag(), and core never imports contracts); see its docstring
for code_paths, code_tags and provenance()."""
from core.trace import ROOT, TAG, code_paths, provenance, tag  # noqa: F401
