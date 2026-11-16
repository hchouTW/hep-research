#!/usr/bin/env python3
"""Deprecated alias of simcal_chain.py (simcal rename, hep-research 0.70.0; removed in 0.72.0).

Prints one notice on stderr, then runs simcal_chain.py with the same arguments, so its stdout, stderr and exit code are those of
simcal_chain.py. See docs/dev/simcal-naming-map.md.
"""
import runpy
import sys
from pathlib import Path

RENAMED_SCRIPT = Path(__file__).resolve().with_name("simcal_chain.py")

if __name__ == "__main__":
    print(f"simcal.deprecated_script: {Path(__file__).name} is deprecated, use {RENAMED_SCRIPT.name} (removed in hep-research "
          "0.72.0)", file=sys.stderr)
    sys.argv[0] = str(RENAMED_SCRIPT)
    runpy.run_path(str(RENAMED_SCRIPT), run_name="__main__")
