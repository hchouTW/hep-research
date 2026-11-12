#!/usr/bin/env python3
"""Propagation (simulator calibration workflow, Part B section 10.4; owner of the export of the principal components
of the joint posterior and of the shared-nuisance versions; phase 2).

  calib_propagate.py export  --input FILE    {theta_hat, zeta_hat, Sigma, i_theta, i_zeta, Sigma_boot?, w?, G_s?,
                                              zeta_keys?}: G_xi, G_zeta (one joint regression), Sigma_zeta, G_s
  calib_propagate.py version --payload FILE  update_digest and version id (acyclic)
Phase 3 (efficiency-map bases, section 6.7, D28, 15.3a; the engine in core/calibration/map_basis.py):
  calib_propagate.py map-basis --maps FILE --replicas R [--jacobian FILE] [--predictions FILE]
                     the native basis of a fixed map set ({component: map}) from g4sim's replicas 1..R, its
                     registration key; U = J B_map (--jacobian, linear in eps only) or U = M V (--predictions at the
                     R replicas, R x n_obs)
  calib_propagate.py joint-pattern --input FILE   {bins, detections, maps, logical_run_seed, first_event, N_map,
                     component, R?}: the pattern table and its hash, the scan key, the table against the maps, the
                     analytic covariance and, with R, the joint-pattern replicas and their registration key
  calib_propagate.py map-cross --input FILE   {a, b} two studies on one basis: U_a U_b^T (a per-study PCA joined by
                     index is rejected)
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
    from core.calibration import io, deps, map_basis as MB, propagate as P
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
    mb = sub.add_parser("map-basis")
    mb.add_argument("--maps", required=True)
    mb.add_argument("--replicas", type=int, required=True)
    mb.add_argument("--jacobian")
    mb.add_argument("--predictions")
    sub.add_parser("joint-pattern").add_argument("--input", required=True)
    sub.add_parser("map-cross").add_argument("--input", required=True)
    args = ap.parse_args(argv)

    def go():
        try:
            if args.cmd in ("map-basis", "joint-pattern", "map-cross"):
                return map_command(args)
            if args.cmd == "version":
                return {"status": "ok", **P.version(io.load(args.payload))}
            x = io.load_object(args.input, ("theta_hat", "zeta_hat", "Sigma", "i_theta", "i_zeta"))
            pkg = P.export(np.asarray(x["theta_hat"], float), np.asarray(x["zeta_hat"], float),
                           np.asarray(x["Sigma"], float), x["i_theta"], x["i_zeta"],
                           None if x.get("Sigma_boot") is None else np.asarray(x["Sigma_boot"], float),
                           float(x.get("w", 1.0)), None if x.get("G_s") is None else np.asarray(x["G_s"], float),
                           x.get("zeta_keys"))
            return io.jsonable({"status": "ok", **pkg, "variance": P.variance(pkg)})
        except (deps.DependencyError, MB.BasisError) as exc:
            return {"status": "rejected", "code": exc.code, "error": str(exc)}
    return io.run(go)


def _maps(path):
    from pathlib import Path
    x = io.load_object(path)
    base = Path(path).resolve().parent
    return {int(k): io.load_object(str(base / v)) if isinstance(v, str) else v for k, v in x.items()}


def map_command(args) -> dict:
    try:
        if args.cmd == "map-basis":
            b = MB.native_basis(_maps(args.maps), args.replicas)
            out = {"status": "ok", "key": b["key"], "coordinates": b["coordinates"], "eps0": b["eps0"],
                   "B_map": b["B_map"], "rank": b["B_map"].shape[1], "replicas": b["replicas"]}
            if args.jacobian:
                out["U"] = MB.u_linear(np.asarray(io.load(args.jacobian), float), b)
                out["construction"] = "linear"
            if args.predictions:
                out["U"] = MB.u_digitized(np.asarray(io.load(args.predictions), float), b)
                out["construction"] = "digitized"
            return io.jsonable(out)
        x = io.load_object(args.input)
        if args.cmd == "map-cross":
            st = []
            for k in ("a", "b"):
                r = dict(x[k])
                r["U"] = np.asarray(r["U"], float)
                if "Q_m" in r:
                    r["Q_m"] = np.asarray(r["Q_m"], float)
                st.append(r)
            return io.jsonable({"status": "ok", **MB.cross_covariance(*st)})
        maps = x["maps"]
        chans = [m["channels"] for m in maps]
        table = MB.pattern_table({int(e): int(b) for e, b in x["bins"].items()},
                                 [{int(e): c for e, c in d.items()} for d in x["detections"]], chans)
        from core.simulation import efficiency_map
        key = MB.scan_key([efficiency_map.map_sha256(m) for m in maps], x["logical_run_seed"], x.get("first_event", 0),
                          x["N_map"])
        f = MB.pattern_findings(table, maps)
        out = {"status": "failed" if f else "ok", "findings": f, "pattern_table": table,
               "pattern_table_sha256": MB.pattern_sha256(table), "scan_key": key,
               "analytic_covariance": MB.analytic_covariance(table, chans)}
        if x.get("R") is not None and not f:
            comp = int(x.get("component", 1))
            out["replicas"] = MB.joint_replicas(table, chans, key, comp, int(x["R"]))
            out["registration_key"] = MB.joint_registration_key(key, comp, table, chans, int(x["R"]))
        return io.jsonable(out)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        if isinstance(exc, (MB.BasisError, io.InputError)):
            raise
        raise io.InputError(f"malformed input: {exc!r}") from None


if __name__ == "__main__":
    sys.exit(main())
