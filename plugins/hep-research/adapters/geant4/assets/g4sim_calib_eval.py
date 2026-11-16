#!/usr/bin/env python3
"""Deprecated alias of g4sim_simcal_eval.py (simcal rename, hep-research 0.70.0; removed in 0.72.0).

As a command it prints one notice on stderr, then runs g4sim_simcal_eval.py with the same arguments, so its stdout,
stderr and exit code are those of g4sim_simcal_eval.py. Imported (as 0.69.0 code did to register the g4sim evaluator
kind), it warns once (DeprecationWarning) and is replaced by the g4sim_simcal_eval module itself, so the evaluator is
registered and every name is the same object. See docs/dev/simcal-naming-map.md.
"""
import runpy
import sys
from pathlib import Path

RENAMED_SCRIPT = Path(__file__).resolve().with_name("g4sim_simcal_eval.py")

if __name__ == "__main__":
    print(f"simcal.deprecated_script: {Path(__file__).name} is deprecated, use {RENAMED_SCRIPT.name} (removed in "
          "hep-research 0.72.0)", file=sys.stderr)
    sys.argv[0] = str(RENAMED_SCRIPT)
    runpy.run_path(str(RENAMED_SCRIPT), run_name="__main__")
else:
    import importlib
    import warnings

    warnings.warn(f"{__name__} is deprecated: import {RENAMED_SCRIPT.stem} (removed in hep-research 0.72.0)",
                  DeprecationWarning, stacklevel=2)
    if str(RENAMED_SCRIPT.parent) not in sys.path:
        sys.path.insert(0, str(RENAMED_SCRIPT.parent))
    sys.modules[__name__] = importlib.import_module(RENAMED_SCRIPT.stem)
