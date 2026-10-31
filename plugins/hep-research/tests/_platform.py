"""Skip a test on a host that lacks a capability: @needs("proc_fs"), with skip reason "needs proc_fs" (core/hostcaps.py).

The reason always starts "needs ", so a run's skipped share per platform can be counted (tools/run_all_checks.py --out).
"""
from __future__ import annotations

import sys
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
