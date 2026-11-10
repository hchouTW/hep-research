#!/usr/bin/env python3
"""The surrogate model of the simulator calibration workflow (Part B sections 6.4, 8.2 note 4; owner of the training
set, P6, the surrogate domain and the ask/tell state file). Phase 1 delivers the interface stub only.

  calib_emulator.py train | p6 | ask | tell [...]
Every command answers status incomplete (exit 3): the surrogate model, its training set (D80), P6 and ask/tell are
delivered in phase 3 (section 17). Standard library only.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import sys

from core.calibration import emulator, io


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("train", "p6", "ask", "tell"):
        sub.add_parser(name).add_argument("rest", nargs="*")
    args = ap.parse_args(argv)
    fn = {"train": emulator.training_set, "p6": emulator.p6, "ask": emulator.ask, "tell": emulator.tell}[args.cmd]
    return io.run(fn)


if __name__ == "__main__":
    sys.exit(main())
