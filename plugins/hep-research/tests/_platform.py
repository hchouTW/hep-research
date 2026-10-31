"""Skip a test on a host that lacks a capability: @needs("proc_fs"), with skip reason "needs proc_fs" (core/hostcaps.py).

The reason always starts "needs ", so a run's skipped share per platform can be counted (tools/run_all_checks.py --out).

plain_tmpdir() is a parent for temporary folders whose path is ASCII without spaces, for tests whose subject refuses or
quotes such a path by design (HTCondor's htcondor.path_whitespace refusal, Slurm's golden job scripts, a #! line, which
the kernel splits at a space): under a TMPDIR named with a space or other characters (the hostile-paths CI job) they
would test the path instead of their subject. Everything else keeps the hostile TMPDIR.

protected_refusal(code) is the refusal a protected-mode test expects on this host: code on a host with POSIX account
identity, protected.unsupported_platform without it (native Windows refuses every protected use first).
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import hostcaps  # noqa: E402


def needs(*caps: str):
    """unittest.skipUnless for every capability in caps; the reason names the first one the host lacks."""
    missing = [cap for cap in caps if not hostcaps.has(cap)]
    return unittest.skipUnless(not missing, f"needs {missing[0]}" if missing else "")


_PLAIN = re.compile(r"[A-Za-z0-9_./-]+")


def plain_tmpdir() -> str | None:
    """The temporary folder when its path is plain ASCII without spaces (on Windows: always), else /tmp on POSIX;
    a value for tempfile's dir= (None means the default)."""
    default = tempfile.gettempdir()
    if os.name == "nt" or _PLAIN.fullmatch(os.path.realpath(default)):
        return None
    return "/tmp" if os.path.isdir("/tmp") and _PLAIN.fullmatch(os.path.realpath("/tmp")) else None


def protected_refusal(code: str) -> str:
    """code where protected mode is supported, else protected.unsupported_platform (module docstring)."""
    return code if hostcaps.has("posix_ids") else "protected.unsupported_platform"
