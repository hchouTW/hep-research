#!/usr/bin/env python3
"""Export an already-computed result to chart payloads plus a sidecar, without re-analysing anything.

Usage:
  python3 export_histogram.py --root FILE --object NAME --integration jsroot [plotly ...] --out DIR [--errors auto|disabled]
  python3 export_histogram.py --json RESULT.json --integration plotly [jsroot ...] --out DIR [--errors auto|disabled]
  python3 export_histogram.py --json TABLE.json --integration echarts --out DIR
  python3 export_histogram.py --self-test
  python3 export_histogram.py --verify-payload P.json --sidecar S.json [--root FILE --object NAME | --json FILE]

Inputs: a 1D ROOT histogram (TH1C/S/I/F/D, read with uproot from its stored members), a "binned-1d" result JSON
(edges, contents, sumw2 or null, "weighted": true/false, underflow, overflow, units), or a "table" JSON
(categories, series). The project computed these; this script only serialises them.
Outputs in DIR: <name>.sidecar.json (the source values exactly as read, for checking) and <name>.<integration>.json.
Rules (see references/event-display-facts.md):
  - display numbers (bin centres, widths, error bars) come only from the named functions below;
  - without stored Sumw2, sqrt(|content|) error bars are drawn only for a result known to be unweighted counts:
    a TH1 whose statistics show unit-weight fills (fTsumw == fTsumw2 > 0), or a binned-1d JSON with
    "weighted": false. Anything else without Sumw2 (weighted, or filled by SetBinContent, or a binned-1d JSON
    that does not say) is refused unless --errors disabled (then no error bars are drawn);
  - members that change meaning (fBinStatErrOpt, fNormFactor, fFunctions, fMaximum/fMinimum, axis range,
    fOption, unflushed fBuffer, text bin labels) are refused at their non-default values;
  - Plotly/ECharts have no place for under/overflow: the payload carries them as a note the panel must show.
Prints JSON {"status": ...}; exit 0 ok, 1 refused, 2 bad input, 3 missing dependency.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ACCEPTED_TH1 = ("TH1C", "TH1S", "TH1I", "TH1F", "TH1D")


class Refused(Exception):
    """The input is readable but cannot be shown without changing its meaning (exit 1)."""


class Rejected(Exception):
    """The input is unusable or outside what this template supports (exit 2)."""


def finite_numbers(what: str, values) -> list[float]:
    """Every value must be a real, finite number (not a bool, a string or null)."""
    if not isinstance(values, list):
        raise Rejected(f"{what} must be a list of numbers")
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise Rejected(f"{what}: {v!r} is not a finite number")
    return [float(v) for v in values]


def th1_unweighted(src: dict) -> bool:
    """True only when the stored statistics show unit-weight fills: fTsumw == fTsumw2 > 0. A TH1 filled with
    SetBinContent has fTsumw == fTsumw2 == 0, and its errors are not known (the content may be a ratio or a rate)."""
    return src["tsumw"] > 0 and src["tsumw"] == src["tsumw2"]


# ---- the only places display numbers are derived (checked by check_bundle.py and its self-test) ----
def bin_centres(edges: list[float]) -> list[float]:
    return [edges[i] + (edges[i + 1] - edges[i]) / 2.0 for i in range(len(edges) - 1)]


def bin_widths(edges: list[float]) -> list[float]:
    return [edges[i + 1] - edges[i] for i in range(len(edges) - 1)]


def error_bars(contents: list[float], sumw2: list[float] | None, weighted: bool) -> list[float] | None:
    """sqrt(sumw2) when stored; sqrt(|content|) only for unweighted fills without Sumw2 (ROOT's own convention)."""
    if sumw2 is not None:
        if any(v < 0 for v in sumw2):
            raise Rejected("negative sumw2")
        return [math.sqrt(v) for v in sumw2]
    if weighted:
        return None
    return [math.sqrt(abs(c)) for c in contents]


# ---- readers ----
def read_root_th1(path: Path, name: str) -> dict:
    import numpy as np
    import uproot
    h = uproot.open(path)[name]
    cls = h.classname
    if cls not in ACCEPTED_TH1:
        raise Rejected(f"{name} is {cls}; this template accepts {', '.join(ACCEPTED_TH1)} only")
    ax = h.member("fXaxis")
    checks = {
        "fBinStatErrOpt": h.member("fBinStatErrOpt") != 0,
        "fNormFactor": h.member("fNormFactor") != 0.0,
        "fFunctions": len(h.member("fFunctions")) > 0,
        "fMaximum/fMinimum": h.member("fMaximum") != -1111.0 or h.member("fMinimum") != -1111.0,
        "axis range (fFirst/fLast)": ax.member("fFirst") != 0 or ax.member("fLast") != 0,
        "fOption": str(h.member("fOption")) != "",
        "unflushed fBuffer": h.member("fBufferSize") > 0 and len(h.member("fBuffer") or []) > 0
                             and h.member("fBuffer")[0] != 0,
        "text bin labels": ax.member("fLabels") is not None and len(ax.member("fLabels")) > 0,
    }
    bad = [k for k, v in checks.items() if v]
    if bad:
        raise Rejected(f"{name}: non-default {', '.join(bad)} change what is shown; not supported by this template")
    contents = [float(v) for v in h.values(flow=True)]
    if not all(math.isfinite(v) for v in contents):
        raise Rejected(f"{name}: non-finite bin content")
    sw2 = h.member("fSumw2")
    sumw2 = [float(v) for v in sw2] if sw2 is not None and len(sw2) else None
    xbins = [float(v) for v in ax.member("fXbins")]
    nb, xmin, xmax = int(ax.member("fNbins")), float(ax.member("fXmin")), float(ax.member("fXmax"))
    edges = xbins if xbins else [float(e) for e in np.linspace(xmin, xmax, nb + 1)]
    return {"kind": "th1", "class": cls, "name": str(h.member("fName")), "title": str(h.member("fTitle")),
            "x_title": str(ax.member("fTitle")), "nbins": nb, "xmin": xmin, "xmax": xmax, "xbins": xbins,
            "edges": edges, "contents_with_flow": contents, "sumw2_with_flow": sumw2,
            "entries": float(h.member("fEntries")), "tsumw": float(h.member("fTsumw")),
            "tsumw2": float(h.member("fTsumw2")), "tsumwx": float(h.member("fTsumwx")),
            "tsumwx2": float(h.member("fTsumwx2")), "dtype": str(h.values().dtype)}


def read_json(path: Path) -> dict:
    return validate_json(json.loads(path.read_text()))


def validate_json(d: dict) -> dict:
    if not isinstance(d, dict):
        raise Rejected("JSON input must be an object")
    if d.get("kind") == "binned-1d":
        e, c = finite_numbers("edges", d.get("edges")), finite_numbers("contents", d.get("contents"))
        if len(e) != len(c) + 1 or any(b <= a for a, b in zip(e, e[1:])):
            raise Rejected("edges must strictly increase and have len(contents)+1 entries")
        if d.get("sumw2") is not None and len(finite_numbers("sumw2", d["sumw2"])) != len(c):
            raise Rejected("sumw2 must match contents")
        for k in ("underflow", "overflow"):
            if k in d:
                finite_numbers(k, [d[k]])
        if "weighted" in d and not isinstance(d["weighted"], bool):
            raise Rejected("'weighted' must be true or false")
        return d
    if d.get("kind") == "table":
        n = len(d["categories"])
        if not isinstance(d.get("series"), list) or not d["series"]:
            raise Rejected("a table needs a non-empty 'series' list")
        for s in d["series"]:
            if len(finite_numbers(f"series {s.get('name')!r} values", s.get("values"))) != n:
                raise Rejected("every series needs one value per category")
        return d
    raise Rejected("JSON input kind must be 'binned-1d' or 'table'")


# ---- payload builders (serialisation only) ----
def as_binned(src: dict) -> dict:
    """Common view of a TH1 or a binned-1d result: in-range contents, sumw2, flow, labels."""
    if src["kind"] == "th1":
        c, s = src["contents_with_flow"], src["sumw2_with_flow"]
        weighted = not th1_unweighted(src)
        x_title = src["x_title"]
        return {"name": src["name"], "title": src["title"].split(";")[0], "x_title": x_title,
                "y_title": src["title"].split(";")[2] if src["title"].count(";") >= 2 else "",
                "edges": src["edges"], "contents": c[1:-1], "sumw2": s[1:-1] if s else None,
                "underflow": c[0], "overflow": c[-1], "weighted": weighted}
    unit = f" [{src['x_unit']}]" if src.get("x_unit") else ""
    return {"name": src["name"], "title": src.get("title", src["name"]), "x_title": src.get("x_label", "") + unit,
            "y_title": src.get("y_label", ""), "edges": src["edges"], "contents": src["contents"],
            "sumw2": src.get("sumw2"), "underflow": src.get("underflow", 0.0), "overflow": src.get("overflow", 0.0),
            # unknown counts as weighted: without sumw2, errors are drawn only when the result says "weighted": false
            "weighted": src.get("weighted", True)}


def plotly_payload(b: dict, errors_mode: str) -> dict:
    err = None if errors_mode == "disabled" else error_bars(b["contents"], b["sumw2"], b["weighted"])
    if err is None and errors_mode != "disabled":
        raise Refused("no Sumw2 and not known to be unweighted counts: errors unknown; store sumw2 upstream, "
                      "mark a binned-1d result \"weighted\": false if it is unit-weight counts, or rerun with "
                      "--errors disabled to show contents without error bars")
    trace = {"type": "bar", "x": bin_centres(b["edges"]), "y": b["contents"], "width": bin_widths(b["edges"]),
             "name": b["title"]}
    if err is not None:
        trace["error_y"] = {"type": "data", "array": err, "visible": True}
    return {"integration": "plotly", "data": [trace],
            "layout": {"title": {"text": b["title"]}, "xaxis": {"title": {"text": b["x_title"]}},
                       "yaxis": {"title": {"text": b["y_title"]}}, "bargap": 0, "showlegend": False},
            "flow": {"underflow": b["underflow"], "overflow": b["overflow"]}, "errors": errors_mode}


def jsroot_payload(src: dict, errors_mode: str) -> dict:
    """Members to copy into a JSROOT TH1D created in the browser; no number is computed here or there."""
    if src["kind"] == "th1":
        if not th1_unweighted(src) and src["sumw2_with_flow"] is None and errors_mode != "disabled":
            raise Refused("TH1 without Sumw2 whose statistics do not show unit-weight fills (weighted, or filled "
                          "by SetBinContent): JSROOT would draw sqrt(|content|); store Sumw2 upstream or rerun "
                          "with --errors disabled")
        # ROOT's "title;x title;y title" convention is not parsed by JSROOT when members are copied: split it here
        parts = src["title"].split(";")
        m = {"fName": src["name"], "fTitle": parts[0], "fEntries": src["entries"], "fTsumw": src["tsumw"],
             "fTsumw2": src["tsumw2"], "fTsumwx": src["tsumwx"], "fTsumwx2": src["tsumwx2"],
             "fArray": src["contents_with_flow"], "fSumw2": src["sumw2_with_flow"] or [],
             "fXaxis": {"fNbins": src["nbins"], "fXmin": src["xmin"], "fXmax": src["xmax"], "fXbins": src["xbins"],
                        "fTitle": src["x_title"] or (parts[1] if len(parts) > 1 else "")},
             "fYaxis": {"fTitle": parts[2] if len(parts) > 2 else ""}}
    else:
        b = as_binned(src)
        if b["weighted"] and b["sumw2"] is None and errors_mode != "disabled":
            raise Refused("result without sumw2 and not marked \"weighted\": false; rerun with --errors disabled")
        e = b["edges"]
        m = {"fName": b["name"], "fTitle": b["title"], "fEntries": None, "fTsumw": None, "fTsumw2": None,
             "fTsumwx": None, "fTsumwx2": None, "fArray": [b["underflow"], *b["contents"], b["overflow"]],
             "fSumw2": [0.0, *b["sumw2"], 0.0] if b["sumw2"] is not None else [],
             "fXaxis": {"fNbins": len(e) - 1, "fXmin": e[0], "fXmax": e[-1], "fXbins": list(e),
                        "fTitle": b["x_title"]}, "fYaxis": {"fTitle": b["y_title"]}}
    opt = "hist nostat" if errors_mode == "disabled" else "e1 nostat"
    return {"integration": "jsroot", "typename": "TH1D", "members": m, "draw_option": opt, "errors": errors_mode}


def echarts_payload(src: dict) -> dict:
    if src.get("kind") != "table":
        raise Rejected("the echarts template takes a 'table' result (categories x series)")
    units = {s.get("unit", "") for s in src["series"]}
    return {"integration": "echarts", "option": {
        "title": {"text": src.get("title", src["name"])}, "tooltip": {"trigger": "axis"}, "legend": {"bottom": 0},
        "xAxis": {"type": "category", "data": src["categories"]},
        "yAxis": {"type": "value", "name": units.pop() if len(units) == 1 else ""},
        "series": [{"type": "bar", "name": s["name"], "data": s["values"]} for s in src["series"]]}}


def verify(payload_path: Path, sidecar_path: Path, root: str | None, object_name: str | None, js: str | None) -> int:
    """Oracle: (1) sidecar equals a fresh read of the source; (2) payload equals the derivations applied to the
    sidecar, bit for bit. Exit 0 equal, 1 different."""
    side = json.loads(sidecar_path.read_text())["values"]
    pay = json.loads(payload_path.read_text())
    problems = []
    if root or js:
        fresh = read_root_th1(Path(root), object_name) if root else read_json(Path(js))
        if fresh != side:
            problems.append("sidecar differs from a fresh read of the source")
    integ = pay.get("integration")
    if integ == "plotly":
        expect = plotly_payload(as_binned(side), pay.get("errors", "auto"))
    elif integ == "jsroot":
        expect = jsroot_payload(side, pay.get("errors", "auto"))
    elif integ == "echarts":
        expect = echarts_payload(side)
    else:
        problems.append(f"unknown integration {integ!r}")
        expect = None
    if expect is not None and json.loads(json.dumps(expect)) != pay:
        problems.append(f"{integ} payload differs from the derivations applied to the sidecar")
    print(json.dumps({"status": "failed" if problems else "ok", "payload": payload_path.name, "problems": problems}))
    return 1 if problems else 0


def self_test() -> int:
    """Known-answer tests: expected values are written by hand, not produced by the functions under test."""
    e = [0.0, 5.0, 10.0, 20.0, 40.0, 80.0]
    assert bin_centres(e) == [2.5, 7.5, 15.0, 30.0, 60.0]
    assert bin_widths(e) == [5.0, 5.0, 10.0, 20.0, 40.0]
    assert error_bars([4.0, 9.0], [16.0, 0.25], True) == [4.0, 0.5]
    assert error_bars([4.0, -9.0], None, False) == [2.0, 3.0]
    assert error_bars([4.0], None, True) is None
    try:
        error_bars([1.0], [-1.0], False)
        raise AssertionError("negative sumw2 accepted")
    except Rejected:
        pass
    weighted_no_sumw2 = {"name": "w", "title": "w", "x_title": "", "y_title": "", "edges": [0.0, 1.0],
                         "contents": [2.5], "sumw2": None, "underflow": 0.0, "overflow": 0.0, "weighted": True}
    try:
        plotly_payload(weighted_no_sumw2, "auto")
        raise AssertionError("weighted histogram without sumw2 was not refused")
    except Refused:
        pass
    assert "error_y" not in plotly_payload(weighted_no_sumw2, "disabled")["data"][0]
    # a binned-1d result that does not say it is unweighted gets no invented sqrt errors
    unstated = {"kind": "binned-1d", "name": "xs", "edges": [0.0, 1.0, 2.0], "contents": [0.04, 0.01], "sumw2": None}
    for build in (lambda s: plotly_payload(as_binned(s), "auto"), lambda s: jsroot_payload(s, "auto")):
        try:
            build(unstated)
            raise AssertionError("binned-1d without sumw2 and without 'weighted' was not refused")
        except Refused:
            pass
    counts = dict(unstated, contents=[4.0, 9.0], weighted=False)
    assert plotly_payload(as_binned(counts), "auto")["data"][0]["error_y"]["array"] == [2.0, 3.0]
    # a TH1 filled by SetBinContent (fTsumw == fTsumw2 == 0, no Sumw2) is refused; unit-weight fills are not
    th1 = {"kind": "th1", "name": "h", "title": "h", "x_title": "", "edges": [0.0, 1.0], "contents_with_flow":
           [0.0, 4.0, 0.0], "sumw2_with_flow": None, "entries": 4.0, "tsumw": 0.0, "tsumw2": 0.0, "tsumwx": 0.0,
           "tsumwx2": 0.0, "nbins": 1, "xmin": 0.0, "xmax": 1.0, "xbins": []}
    try:
        jsroot_payload(th1, "auto")
        raise AssertionError("SetBinContent-filled TH1 without Sumw2 was not refused")
    except Refused:
        pass
    assert jsroot_payload(dict(th1, tsumw=4.0, tsumw2=4.0), "auto")["draw_option"] == "e1 nostat"
    for bad in ({"kind": "table", "name": "t", "categories": ["a"], "series": [{"name": "s", "values": [float("nan")]}]},
                {"kind": "binned-1d", "name": "b", "edges": [0.0, 1.0], "contents": ["1"]},
                {"kind": "binned-1d", "name": "b", "edges": [0.0, 1.0], "contents": [1.0], "underflow": float("nan")}):
        try:
            validate_json(bad)
            raise AssertionError(f"invalid input accepted: {bad}")
        except Rejected:
            pass
    print(json.dumps({"status": "ok", "self_test": "derivations and refusals"}))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src_g = ap.add_mutually_exclusive_group()
    src_g.add_argument("--root")
    src_g.add_argument("--json")
    ap.add_argument("--object")
    ap.add_argument("--integration", nargs="+", choices=["jsroot", "plotly", "echarts"])
    ap.add_argument("--out")
    ap.add_argument("--errors", choices=["auto", "disabled"], default="auto")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--verify-payload", help="check this payload against --sidecar (and the source if given)")
    ap.add_argument("--sidecar")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    if a.verify_payload:
        if not a.sidecar:
            print(json.dumps({"status": "rejected", "reason": "--verify-payload needs --sidecar"}))
            return 2
        try:
            return verify(Path(a.verify_payload), Path(a.sidecar), a.root, a.object, a.json)
        except (Refused, Rejected, KeyError, TypeError, ValueError, OSError) as exc:
            print(json.dumps({"status": "failed", "reason": str(exc)}))
            return 1
    if not (a.root or a.json) or not a.integration or not a.out or (a.root and not a.object):
        print(json.dumps({"status": "rejected", "reason": "need --root FILE --object NAME or --json FILE, "
                                                          "--integration and --out"}))
        return 2
    try:
        if a.root:
            try:
                import uproot  # noqa: F401
            except ImportError as exc:
                print(json.dumps({"status": "missing-dependency", "reason": str(exc)}))
                return 3
            src = read_root_th1(Path(a.root), a.object)
            source = {"file": Path(a.root).name, "object": a.object}
        else:
            src = read_json(Path(a.json))
            source = {"file": Path(a.json).name}
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        name = src.get("name") or a.object
        payloads = {}
        for integ in a.integration:
            if integ == "plotly":
                if src["kind"] == "table":
                    raise Rejected("the plotly template takes a histogram, not a table")
                payloads[integ] = plotly_payload(as_binned(src), a.errors)
            elif integ == "jsroot":
                if src["kind"] == "table":
                    raise Rejected("the jsroot template takes a histogram, not a table")
                payloads[integ] = jsroot_payload(src, a.errors)
            else:
                payloads[integ] = echarts_payload(src)
    except Refused as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}))
        return 1
    except (Rejected, KeyError, TypeError, ValueError, OSError) as exc:
        print(json.dumps({"status": "rejected", "reason": f"{type(exc).__name__}: {exc}"}))
        return 2
    sidecar = {"schema": "event-display-sidecar/1", "source": source, "values": src}
    (out / f"{name}.sidecar.json").write_text(json.dumps(sidecar, indent=1, allow_nan=False))
    for integ, p in payloads.items():
        (out / f"{name}.{integ}.json").write_text(json.dumps(p, separators=(",", ":"), allow_nan=False))
    print(json.dumps({"status": "ok", "name": name, "written": [f"{name}.sidecar.json"] +
                      [f"{name}.{i}.json" for i in payloads]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
