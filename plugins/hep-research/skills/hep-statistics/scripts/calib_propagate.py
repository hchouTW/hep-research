#!/usr/bin/env python3
"""Propagation (simulator calibration workflow, Part B section 10.4; owner of the export of the principal components
of the joint posterior and of the shared-nuisance versions; phase 2).

  calib_propagate.py export  --input FILE    {theta_hat, zeta_hat, Sigma, i_theta, i_zeta, Sigma_boot?, w?, G_s?,
                                              zeta_keys?}: G_xi, G_zeta (one joint regression), Sigma_zeta, G_s
  calib_propagate.py version --payload FILE  update_digest and version id (acyclic)
Output: one JSON object; ok (exit 0), rejected (exit 2). The conflict rules over packages are calib_deps.py's. The
engine needs NumPy and SciPy. Phase 2 (section 17).
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
    from core.calibration import io, deps, propagate as P
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
    sub.add_parser("export").add_argument("--input", required=True)
    sub.add_parser("version").add_argument("--payload", required=True)
    args = ap.parse_args(argv)

    def go():
        try:
            if args.cmd == "version":
                return {"status": "ok", **P.version(io.load(args.payload))}
            x = io.load_object(args.input, ("theta_hat", "zeta_hat", "Sigma", "i_theta", "i_zeta"))
            pkg = P.export(np.asarray(x["theta_hat"], float), np.asarray(x["zeta_hat"], float),
                           np.asarray(x["Sigma"], float), x["i_theta"], x["i_zeta"],
                           None if x.get("Sigma_boot") is None else np.asarray(x["Sigma_boot"], float),
                           float(x.get("w", 1.0)), None if x.get("G_s") is None else np.asarray(x["G_s"], float),
                           x.get("zeta_keys"))
            return io.jsonable({"status": "ok", **pkg, "variance": P.variance(pkg)})
        except deps.DependencyError as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
