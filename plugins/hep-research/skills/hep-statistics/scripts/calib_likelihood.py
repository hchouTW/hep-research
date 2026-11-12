#!/usr/bin/env python3
"""The joint likelihood (simulator calibration workflow, Part B section 2.1, 5.4; owner of the blocks, link
functions, nu and eta, the V_model principal components, the event-level bootstrap at theta_ref and the pass/fail
summaries of weighted MC; phase 2).

  calib_likelihood.py layout   --contract FILE                  the blocks and the order of beta
  calib_likelihood.py vmodel   --components FILE [--keep-all]   V_model principal components (conditions 1 and 2)
  calib_likelihood.py binomial --moments FILE                   variance-matched n_eff, k_eff and the scope
  calib_likelihood.py bootstrap-size --p P                      B >= max(500, 50 p)
Output: one JSON object; ok (exit 0), rejected (exit 2). The engine needs NumPy and SciPy. Phase 2 (section 17).
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
    from core.calibration import io, likelihood as L, linear
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
    sub.add_parser("layout").add_argument("--contract", required=True)
    v = sub.add_parser("vmodel")
    v.add_argument("--components", required=True, help="JSON {R: matrix, calibration_rows: [...], V_G: matrix}")
    v.add_argument("--keep-all", action="store_true")
    sub.add_parser("binomial").add_argument("--moments", required=True)
    sub.add_parser("bootstrap-size").add_argument("--p", type=int, required=True)
    args = ap.parse_args(argv)

    def go():
        try:
            if args.cmd == "bootstrap-size":
                return {"status": "ok", "B_min": L.bootstrap_size(args.p)}
            if args.cmd == "layout":
                contract, _, _ = io.contract_and_plan(args.contract)
                obs = linear.calibration_observables(contract)
                th = [p["name"] for p in contract.get("parameters", []) if p["role"] == "theta"]
                ph = [p["name"] for p in contract.get("parameters", []) if p["role"] == "phi"
                      and p.get("mode", "profile") == "profile"]
                lay = L.build_layout(obs, th, ph, 0, 0)
                return {"status": "ok", "blocks": [{"name": b.name, "kind": b.kind, "link": b.link,
                                                    "rows": b.index.tolist()} for b in lay.blocks],
                        "beta": lay.sizes}
            if args.cmd == "vmodel":
                c = io.load(args.components)
                R = np.asarray(c["R"], float)
                VG = np.asarray(c["V_G"], float) if c.get("V_G") is not None else None
                rows = np.asarray(c.get("calibration_rows", list(range(R.shape[0]))))
                pc = L.principal_components(R, rows, None if VG is None else np.linalg.inv(VG), keep_all=args.keep_all)
                return io.jsonable({"status": "ok", **pc})
            m = io.load(args.moments)
            n, k = L.binomial_effective(m["W_P"], m["S_P"], m["W_F"], m["S_F"], m.get("V_PF", 0.0))
            out = {"status": "ok", "n_eff": n, "k_eff": k}
            if "T_P" in m:
                out["scope"] = L.binomial_scope(k / n, n, m["S_P"], m["S_F"], m["T_P"], m["T_F"])
            return out
        except L.LikelihoodError as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
