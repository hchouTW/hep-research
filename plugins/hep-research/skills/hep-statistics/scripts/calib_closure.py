#!/usr/bin/env python3
"""G8, the closure test (simulator calibration workflow, Part B section 8.4; owner of G8; phase 2).

  calib_closure.py nc --d D --level standard|full        N_bias, N_cov and N_c (the section 8.4 table)
  calib_closure.py decide --results FILE                  the Holm decision from the pseudo-data results
  calib_closure.py not-executed --reason TEXT             no decision: closure-not-tested
The results file: {level, names, sigma_design, interior: {errors, cover68, cover95, nontruth_basin, X,
interval_toys}, boundary: {...}}. Output: one JSON object; passed (exit 0), failed (exit 1, remedy plan; contract
when the pseudo-data fall in a non-truth basin, D57), incomplete (exit 3). Phase 2 (section 17).
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
import json
import sys

try:
    MISSING = None
    import numpy as np
    from core.calibration import io, closure
except ImportError as _exc:                   # the engine needs NumPy and SciPy: a JSON message, exit 2
    MISSING = str(_exc)


def _missing(argv):
    a = argv if argv is not None else sys.argv[1:]
    if MISSING and "-h" not in a and "--help" not in a:
        print(json.dumps({"status": "rejected", "error": f"needs NumPy and SciPy ({MISSING})"}))
        return True
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    if _missing(argv):
        return 2
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("nc")
    n.add_argument("--d", type=int, required=True)
    n.add_argument("--level", choices=("standard", "full"), required=True)
    sub.add_parser("decide").add_argument("--results", required=True)
    sub.add_parser("not-executed").add_argument("--reason", required=True)
    args = ap.parse_args(argv)

    def go():
        if args.cmd == "nc":
            return {"status": "ok", **closure.n_c(args.d, args.level)}
        if args.cmd == "not-executed":
            return {"status": "ok", **closure.not_executed(args.reason)}
        r = io.load(args.results)
        pts = {}
        for k in ("interior", "boundary"):
            x = r[k]
            pts[k] = {"errors": np.asarray(x["errors"], float), "cover68": np.asarray(x["cover68"], bool),
                      "cover95": np.asarray(x.get("cover95", x["cover68"]), bool),
                      "nontruth_basin": np.asarray(x.get("nontruth_basin", [False]), bool), "X": int(x.get("X", 0)),
                      "interval_toys": x.get("interval_toys", {"X": 0, "n": 0})}
        return io.jsonable(closure.g8(r["level"], r["names"], r["sigma_design"], pts["interior"], pts["boundary"]))
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
