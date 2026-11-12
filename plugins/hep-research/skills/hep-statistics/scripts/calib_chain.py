#!/usr/bin/env python3
"""Stage graph, candidate methods and reference coverage (simulator calibration workflow, Part B sections 3.1, 3.4,
3.6; owner of the DAG and injection-point split, candidate methods and gate P4).

  calib_chain.py check      --contract FILE                 the stage graph and the placement of references
  calib_chain.py candidates --contract FILE --plan FILE     candidate methods per parameter (section 3.6 step 1)
  calib_chain.py p4         --contract FILE                 directed reachability: can each theta be constrained?
FILE is a calibration-contract/1 (or a calibration-fixture/1, whose contract and plan are used). Output: one JSON
object; status ok/passed (exit 0), failed (exit 1: findings, a parameter without candidate, or P4 failed, remedy
level contract), incomplete (exit 3: g4sim node binding, Table 2 of section 11.4 arrives in phase 3), rejected
(exit 2: unreadable input). Standard library only. Phase 0 (section 17).
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

from core.calibration import chain, io


def _contract_and_plan(path, plan_path=None):
    doc = io.load(path)
    if not isinstance(doc, dict):
        raise io.InputError("a contract or fixture is a JSON object")
    contract, plan = (doc["contract"], doc.get("plan")) if doc.get("schema") == "calibration-fixture/1" else (doc, None)
    if plan_path:
        plan = io.load(plan_path)
    if not isinstance(contract.get("stage_graph"), dict):
        raise io.InputError("the contract has no stage_graph")
    return contract, plan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "candidates", "p4"):
        p = sub.add_parser(name)
        p.add_argument("--contract", required=True)
        if name == "candidates":
            p.add_argument("--plan", help="calibration-plan/1 (default: the fixture's plan)")
    args = ap.parse_args(argv)

    def go():
        contract, plan = _contract_and_plan(args.contract, getattr(args, "plan", None))
        findings = chain.check_graph(contract["stage_graph"])
        if not findings:
            findings = chain.check_references(contract["stage_graph"], contract.get("references", []))
        if args.cmd == "check" or findings:
            return {"status": "failed" if findings else "ok", "findings": findings}
        try:
            if args.cmd == "p4":
                return chain.p4(contract)
            if plan is None:
                raise io.InputError("candidates needs --plan (or a fixture with a plan)")
            return chain.candidate_methods(contract, plan)
        except KeyError as exc:
            raise io.InputError(f"a parameter acts on an undeclared node {exc}") from None
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
