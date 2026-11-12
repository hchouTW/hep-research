#!/usr/bin/env python3
"""Evidence grade, flags and uses of a calibration result (simulator calibration workflow, Part B section 10.2 and
Appendix C; owner of the grade rules, the "outcome already determined" lookup and variation-upstream eligibility).

  calib_use.py judge  --inputs FILE     grade one result: the Appendix C.1 inputs and its upstreams
  calib_use.py lookup --inputs FILE --undecided mandatory-gate,p7,v
                                        before opening: is the outcome already determined (section 10.2 rule 0)?
FILE holds {"inputs": {C.1 fields, own_flags: [...]}, "upstreams": [{"usages": [...], "effective_grade": ...,
"flags": [...]}]}; field names are those of the reference decision table (Appendix C.1, last column).
Output: one JSON object. judge: status ok (exit 0) with own_grade (null for a pending input), effective_grade, uses,
flags, variation_flags; status incomplete (exit 3) when the result is incomplete (no use, cannot be cited); status
rejected (exit 2) for bad input or an inadmissible variation upstream. lookup: status ok with determined (when true,
the validation data are not opened and V is recorded not-applicable). Standard library only. Phase 0 (section 17).
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

from core.calibration import io, use


def _inputs(path):
    doc = io.load(path)
    if not isinstance(doc, dict) or not isinstance(doc.get("inputs"), dict):
        raise io.InputError('the inputs file holds {"inputs": {...}, "upstreams": [...]}')
    c = dict(doc["inputs"])
    c["own_flags"] = set(c.get("own_flags", []))
    ups = [dict(u, usages=set(u.get("usages", [])), flags=set(u.get("flags", []))) for u in doc.get("upstreams", [])]
    try:
        use.check_inputs(c)
        for u in ups:
            if not {"usages", "effective_grade", "flags"} <= set(u):
                raise ValueError("an upstream has usages, effective_grade and flags")
    except ValueError as exc:
        raise io.InputError(str(exc)) from None
    return c, ups


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    j = sub.add_parser("judge", help="grade one result")
    j.add_argument("--inputs", required=True)
    lk = sub.add_parser("lookup", help="outcome already determined?")
    lk.add_argument("--inputs", required=True)
    lk.add_argument("--undecided", required=True, help="comma list of mandatory-gate, p7, v")
    args = ap.parse_args(argv)

    def go():
        c, ups = _inputs(args.inputs)
        try:
            if args.cmd == "judge":
                r = use.judge(c, ups)
                return {"status": "incomplete" if r["effective_grade"] == use.INCOMPLETE else "ok", **r}
            r = use.outcome_determined(c, ups, [x for x in args.undecided.split(",") if x])
            return {"status": "ok", **r}
        except ValueError as exc:
            raise io.InputError(str(exc)) from None
    return io.run(go)


if __name__ == "__main__":
    sys.exit(main())
