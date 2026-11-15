"""Skip a test on a host that lacks a capability: @needs("proc_fs"), with skip reason "needs proc_fs" (core/hostcaps.py).

The reason always starts "needs ", so a run's skipped share per platform can be counted (tools/run_all_checks.py --out).

plain_tmpdir() is a parent for temporary folders whose path is ASCII without spaces, for tests whose subject refuses or
quotes such a path by design (HTCondor's htcondor.path_whitespace refusal, Slurm's golden job scripts, a #! line, which
the kernel splits at a space): under a TMPDIR named with a space or other characters (the hostile-paths CI job) they
would test the path instead of their subject. Everything else keeps the hostile TMPDIR.

protected_refusal(code) is the refusal a protected-mode test expects on this host: code on a host with POSIX account
identity, protected.unsupported_platform without it (native Windows refuses every protected use first).

recording_erfc() is true when the C library's erfc (Python's math.erfc) rounds like the hosts that recorded byte pins of
values built on it: glibc 2.34 on NSTCCore (EL9) and glibc 2.39 on GitHub's ubuntu-24.04. Their erfc is not correctly
rounded; the glibc of ubuntu-26.04 (GitHub's ubuntu-latest from October 2026) is, and so differs in the last bit of some
values. The probe is the input on which the design-space example's committed charge confusion differs (main's full CI
runs from PR #405 on). NumPy's CPU dispatch and the BLAS core type do not enter these pins (main full-run fix round).
"""
from __future__ import annotations

import math
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


# erfc(0x1.8ad12d913e8abp+1): the recording hosts' value, one ulp below the correctly rounded 0x1.b0243cd499416p-17.
_ERFC_PROBE = (float.fromhex("0x1.8ad12d913e8abp+1"), float.fromhex("0x1.b0243cd499415p-17"))
RECORDING_ERFC_REASON = ("needs the recording hosts' erfc (glibc 2.34 / 2.39, not correctly rounded): this C library rounds "
                         "math.erfc otherwise (e.g. ubuntu-26.04), and the pinned bytes are those of its last bits")


def recording_erfc() -> bool:
    """math.erfc rounds the probe like the recording hosts (module docstring)."""
    x, want = _ERFC_PROBE
    return math.erfc(x) == want
