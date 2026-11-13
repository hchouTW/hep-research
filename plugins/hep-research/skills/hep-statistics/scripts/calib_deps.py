#!/usr/bin/env python3
"""Dependencies between calibration results (simulator calibration workflow, Part B sections 5.2 clause 5, 10.2,
10.3, 10.4; owner of hash references, cycle checks, roles derived from usage and version ids).

  calib_deps.py roles   --contract FILE     upstream[] of a contract: hash citations, usages, derived roles
  calib_deps.py cycles  --graph FILE        {result or series: [upstreams]}: a cycle is rejected (section 10.3)
  calib_deps.py version --payload FILE      update_digest and version id of a shared-nuisance version (section 10.4)
  calib_deps.py finalize --result FILE --payload FILE --out FILE
                                            write the version id into a result, then its result hash (acyclic)
Output: one JSON object; status ok (exit 0), failed (exit 1: findings or a cycle), rejected (exit 2: unreadable
input), written (exit 0) for finalize. Standard library only. Phase 0 (section 17); the section 10.4 conflict
rules (`packages`) phase 2; invalidation (section 10.3, approval A21) phase 4.
  calib_deps.py packages --input FILE      {packages, upstreams, common_sources?}: the section 10.4 decision
                                            (package split, version conflict, source overlap, common source,
                                            theta/nu split, a version of xi); failed (exit 1) with
                                            findings; forced_joint_fits lists each joint fit the conflict
                                            rules force (A21, section 19-g8: xi has no versions)
  calib_deps.py invalidate --input FILE    {results, changes: [{old, new}], marked?}: downstreams of a revised or
                                            downgraded upstream need a redo, a same-kappa re-judgment does not
                                            (section 10.3); failed (exit 1) when any result needs a redo
  calib_deps.py identity --input FILE      {result, current, record?, basis?}: a changed masked identity item
                                            (section 5.1) needs a redo unless a T2 record registered before the new
                                            build passes (TOST at 0.1 sigma_tot^design, alpha 0.05, provisional;
                                            A21 19-g7): carried-over (exit 0, flag identity-carried-over), redo
                                            (exit 1), unchanged (exit 0)
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

from core.calibration import deps, io


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("roles").add_argument("--contract", required=True)
    sub.add_parser("cycles").add_argument("--graph", required=True)
    sub.add_parser("version").add_argument("--payload", required=True)
    sub.add_parser("packages").add_argument("--input", required=True)
    sub.add_parser("invalidate").add_argument("--input", required=True)
    sub.add_parser("identity").add_argument("--input", required=True)
    f = sub.add_parser("finalize")
    for a in ("--result", "--payload", "--out"):
        f.add_argument(a, required=True)
    args = ap.parse_args(argv)

    def go():
        try:
            if args.cmd == "roles":
                c = io.load(args.contract)
                ups = c.get("upstream", []) if isinstance(c, dict) else None
                findings = deps.check_upstream_entries(ups)
                roles = {e.get("result_sha256"): deps.derive_role(e["usages"]) for e in ups or []
                         if isinstance(e, dict) and e.get("usages") and set(e["usages"]) <= deps.USAGES}
                return {"status": "failed" if findings else "ok", "roles": roles, "findings": findings}
            if args.cmd == "cycles":
                g = io.load(args.graph)
                if not isinstance(g, dict) or not all(isinstance(v, list) for v in g.values()):
                    raise io.InputError("the graph maps each result to the list of its upstreams")
                cyc = deps.find_cycle(g)
                return {"status": "failed" if cyc else "ok", "cycle": cyc}
            if args.cmd == "packages":
                x = io.load(args.input)
                if not isinstance(x, dict) or not isinstance(x.get("packages"), list):
                    raise io.InputError("--input: {packages: [...], upstreams: {...}, common_sources?: {...}}")
                cs = {k: set(v) for k, v in (x.get("common_sources") or {}).items()}
                findings = deps.check_packages(x["packages"], x.get("upstreams") or {}, cs or None)
                return {"status": "failed" if findings else "ok", "findings": findings,
                        "forced_joint_fits": deps.forced_joint_fits(x["packages"], findings)}
            if args.cmd == "invalidate":
                x = io.load(args.input)
                if not isinstance(x, dict) or not isinstance(x.get("results"), list) \
                        or not isinstance(x.get("changes"), list) or not isinstance(x.get("marked", []), list):
                    raise io.InputError("--input: {results: [...], changes: [{old, new}], marked?: [hashes]}")
                r = deps.invalidate(x["results"], x["changes"], x.get("marked", []))
                return dict(r, status="failed" if r["redo"] else "ok")
            if args.cmd == "identity":
                x = io.load(args.input)
                if not isinstance(x, dict) or "result" not in x or "current" not in x \
                        or not isinstance(x.get("basis", {}), dict):
                    raise io.InputError("--input: {result, current: [{model, identity}], record?, basis?}")
                return deps.identity_decision(x["result"], x["current"], x.get("record"), x.get("basis"))
            payload = io.load(args.payload)
            if args.cmd == "version":
                return {"status": "ok", "update_digest": deps.update_digest(payload),
                        "version_id": deps.version_id(payload)}
            r = deps.finalize_result(io.load(args.result), payload)
            io.write_json(args.out, r)
            return {"status": "written", "out": args.out, "version_id": r["version_id"],
                    "result_sha256": r["result_sha256"]}
        except deps.DependencyError as exc:
            raise io.InputError(f"{exc.code}: {exc}") from None
        except (AttributeError, KeyError, TypeError) as exc:
            raise io.InputError(f"unexpected input structure: {exc}") from None
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
