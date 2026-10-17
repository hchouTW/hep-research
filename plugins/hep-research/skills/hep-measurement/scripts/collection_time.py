#!/usr/bin/env python3
"""Collection time per era, time bin and bin of the variable, from declared data-taking periods (M1).

Purpose: the normalization of a time-dependent flux. For each period that passes the declared quality cuts, its live
time (duration x live fraction) is added to every bin of the variable that lies above the period's cutoff threshold
(cutoff x safety factor). The result, the collection time T (seconds) per era, time bin and variable bin, times the
acceptance, is the exposure of the composition exposure_acceptance_livetime_transmission (contracts/vocab/effects.json:
acceptance x livetime x cutoff_transmission). See <plugin root>/skills/hep-measurement/references/correction-chain.md,
"Time-dependent measurements".

Naming: this tool says "collection time" (seconds of live time above cutoff). The contracts' exposure_record is the
blinding record of data exposure, a different thing.

Method: a bin [x_lo, x_hi) receives a period's live time when x_lo >= safety_factor x cutoff (the whole bin above the
threshold; a bin straddling the threshold receives nothing). Periods are keyed by the declared key column; identical
copies (a period split across files) are counted once, copies that differ are refused. Sums run over periods sorted by
(start, key), so `accumulate --emit-partial` on separate inputs followed by `merge` gives the same numbers as a single
`accumulate` over all inputs.

Configuration (JSON; every key is required, there are no defaults and no expressions):
  {"key": COLUMN, "start_column": COLUMN, "duration_column": COLUMN, "live_fraction_column": COLUMN,
   "quality_cuts": [{"name": TEXT, "column": COLUMN, "op": "==|!=|<|<=|>|>=|in", "value": X}],   (may be [])
   "transmission": {"cutoff_column": COLUMN, "safety_factors": [F, ...]},
   "x": {"variable": TEXT, "unit": TEXT, "edges": [...]}, "time_edges": [...],
   "eras": [{"id": TEXT, "start": T, "end": T}]}
Input: period tables as CSV with a header, JSON Lines or a JSON list; start and duration in seconds (time_edges and
eras in the same clock).
Refused (exit 2): a missing or empty key or column, a non-numeric value, a live fraction outside [0, 1], a
non-positive duration, overlapping periods with different keys, a period crossing an era or time-bin boundary, two
copies of a period that differ, a partial made with another configuration. A period outside every era or time bin is
removed and counted in the diagnostics.

Usage:
  collection_time.py accumulate --config CONFIG.json PERIODS [PERIODS ...] [--emit-partial PARTIAL.json] [--out OUT]
  collection_time.py merge --config CONFIG.json PARTIAL [PARTIAL ...] [--out OUT]
  both take --status LABEL (default unvalidated), echoed as status_label.
Output JSON: status (ok, rejected), status_label, inputs, defaults_used, collection_time_s {era: {safety factor:
[[T per x bin] per time bin]}}, livetime_s {era: [per time bin]} (after quality cuts, before transmission), x,
time_edges, eras, diagnostics (periods read, unique, duplicates removed, removed per condition, kept),
normalization (composition and effect IDs), naming. With --emit-partial: the partial file and its digest.
Exit codes: 0 ok; 2 bad input or refused periods. Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

REQUIRED = ("key", "start_column", "duration_column", "live_fraction_column", "quality_cuts", "transmission", "x",
            "time_edges", "eras")
OPS = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
       ">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "in": lambda a, b: a in b}
COMPOSITION = "exposure_acceptance_livetime_transmission"
PARTIAL_KIND = "collection-time-partial"


class InputError(ValueError):
    def __init__(self, message: str, **extra):
        super().__init__(message)
        self.extra = extra


def _num(value, where: str) -> float:
    if isinstance(value, bool):
        raise InputError(f"{where}: {value!r} is not a number")
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise InputError(f"{where}: {value!r} is not a number") from None
    if not math.isfinite(out):
        raise InputError(f"{where}: {value!r} is not finite")
    return out


def _edges(values, where: str) -> list[float]:
    if not isinstance(values, list) or len(values) < 2:
        raise InputError(f"{where} needs at least two edges")
    out = [_num(v, where) for v in values]
    if any(b <= a for a, b in zip(out, out[1:])):
        raise InputError(f"{where} must increase strictly")
    return out


def load_config(path: Path) -> tuple[dict, str]:
    try:
        raw = path.read_bytes()
        cfg = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read the configuration {path}: {exc}") from None
    if not isinstance(cfg, dict):
        raise InputError("the configuration must be a JSON object")
    missing = [k for k in REQUIRED if k not in cfg]
    if missing:
        raise InputError(f"the configuration lacks {missing}; there are no defaults")
    for k in ("key", "start_column", "duration_column", "live_fraction_column"):
        if not isinstance(cfg[k], str) or not cfg[k].strip():
            raise InputError(f"{k} must name a column")
    if not isinstance(cfg["quality_cuts"], list):
        raise InputError("quality_cuts must be a list (possibly empty)")
    names = []
    for i, cut in enumerate(cfg["quality_cuts"]):
        if not isinstance(cut, dict) or set(cut) != {"name", "column", "op", "value"}:
            raise InputError(f"quality_cuts[{i}] must have exactly name, column, op and value")
        if cut["op"] not in OPS:
            raise InputError(f"quality_cuts[{i}].op {cut['op']!r} is not one of {sorted(OPS)}; expressions are not evaluated")
        if cut["op"] == "in" and not isinstance(cut["value"], list):
            raise InputError(f"quality_cuts[{i}]: 'in' needs a list")
        names.append(cut["name"])
    if len(set(names)) != len(names):
        raise InputError("quality cut names must be unique")
    tr = cfg["transmission"]
    if not isinstance(tr, dict) or set(tr) != {"cutoff_column", "safety_factors"}:
        raise InputError("transmission must have exactly cutoff_column and safety_factors")
    if not isinstance(tr["safety_factors"], list) or not tr["safety_factors"]:
        raise InputError("transmission.safety_factors must be a non-empty list")
    sfs = [_num(f, "transmission.safety_factors") for f in tr["safety_factors"]]
    if any(f <= 0 for f in sfs) or len(set(sfs)) != len(sfs):
        raise InputError("safety factors must be positive and distinct")
    x = cfg["x"]
    if not isinstance(x, dict) or not {"variable", "unit", "edges"} <= set(x):
        raise InputError("x needs variable, unit and edges")
    _edges(x["edges"], "x.edges")
    _edges(cfg["time_edges"], "time_edges")
    if not isinstance(cfg["eras"], list) or not cfg["eras"]:
        raise InputError("eras must be a non-empty list of {id, start, end}")
    eras = []
    for i, e in enumerate(cfg["eras"]):
        if not isinstance(e, dict) or not {"id", "start", "end"} <= set(e) or not str(e["id"]).strip():
            raise InputError(f"eras[{i}] needs id, start and end")
        a, b = _num(e["start"], f"eras[{i}].start"), _num(e["end"], f"eras[{i}].end")
        if b <= a:
            raise InputError(f"eras[{i}]: end must be after start")
        eras.append((a, b, str(e["id"])))
    eras.sort()
    if any(eras[k + 1][0] < eras[k][1] for k in range(len(eras) - 1)) or len({e[2] for e in eras}) != len(eras):
        raise InputError("eras overlap or repeat an id")
    canonical = json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    return cfg, hashlib.sha256(canonical.encode()).hexdigest()


def _rows(path: Path) -> tuple[list[dict], str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc.strerror or exc}") from None
    text = raw.decode("utf-8", errors="replace")
    s = text.lstrip()
    try:
        if path.suffix == ".csv" or not s.startswith(("{", "[")):
            rows = list(csv.DictReader(io.StringIO(text)))
        elif s.startswith("["):
            rows = json.loads(text)
        else:
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    except ValueError as exc:
        raise InputError(f"{path}: not CSV, JSON Lines or a JSON list ({exc})") from None
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise InputError(f"{path}: records must be objects")
    return rows, hashlib.sha256(raw).hexdigest()


def _cut_value(raw, target):
    """Compare numbers as numbers and text as text: a CSV '0' equals a configured 0."""
    if isinstance(target, list):
        return _cut_value(raw, target[0]) if target else raw
    if isinstance(target, (int, float)) and not isinstance(target, bool):
        return _num(raw, "quality column")
    return raw if not isinstance(raw, str) else raw.strip()


def read_periods(paths: list[Path], cfg: dict) -> tuple[list[dict], list[dict]]:
    """Normalized period records (no deduplication) and the sources they came from."""
    cols = [cfg["key"], cfg["start_column"], cfg["duration_column"], cfg["live_fraction_column"],
            cfg["transmission"]["cutoff_column"]] + [c["column"] for c in cfg["quality_cuts"]]
    periods, sources = [], []
    for path in paths:
        rows, digest = _rows(path)
        for i, row in enumerate(rows):
            where = f"{path}:{i + 1}"
            for c in cols:
                if c not in row or row[c] is None or str(row[c]).strip() == "":
                    raise InputError(f"{where}: column {c!r} is missing or empty")
            start = _num(row[cfg["start_column"]], f"{where} start")
            duration = _num(row[cfg["duration_column"]], f"{where} duration")
            live = _num(row[cfg["live_fraction_column"]], f"{where} live fraction")
            if duration <= 0:
                raise InputError(f"{where}: duration must be > 0")
            if not 0.0 <= live <= 1.0:
                raise InputError(f"{where}: live fraction {live} outside [0, 1]")
            quality = {}
            for cut in cfg["quality_cuts"]:
                quality[cut["name"]] = _cut_value(row[cut["column"]], cut["value"])
            periods.append({"key": str(row[cfg["key"]]).strip(), "start": start, "duration": duration, "live": live,
                            "cutoff": _num(row[cfg["transmission"]["cutoff_column"]], f"{where} cutoff"),
                            "quality": quality})
        sources.append({"path": str(path), "sha256": digest, "rows": len(rows)})
    return periods, sources


def accumulate(periods: list[dict], cfg: dict) -> dict:
    unique: dict[str, dict] = {}
    duplicates, conflicts = 0, []
    for p in periods:
        if p["key"] in unique:
            if unique[p["key"]] == p:
                duplicates += 1
            else:
                conflicts.append(p["key"])
            continue
        unique[p["key"]] = p
    if conflicts:
        raise InputError("copies of a period differ: one period cannot have two values", conflicting_keys=sorted(set(conflicts)))
    ordered = sorted(unique.values(), key=lambda p: (p["start"], p["key"]))
    overlaps = [[a["key"], b["key"]] for a, b in zip(ordered, ordered[1:]) if b["start"] < a["start"] + a["duration"]]
    if overlaps:
        raise InputError("periods overlap in time", overlaps=overlaps[:20], n_overlaps=len(overlaps))
    edges = [float(v) for v in cfg["x"]["edges"]]
    tedges = [float(v) for v in cfg["time_edges"]]
    eras = sorted(((float(e["start"]), float(e["end"]), str(e["id"])) for e in cfg["eras"]))
    sfs = [float(f) for f in cfg["transmission"]["safety_factors"]]
    sf_keys = [repr(f) for f in sfs]
    nx, nt = len(edges) - 1, len(tedges) - 1
    ct = {e[2]: {k: [[0.0] * nx for _ in range(nt)] for k in sf_keys} for e in eras}
    lt = {e[2]: [0.0] * nt for e in eras}
    removed = {c["name"]: 0 for c in cfg["quality_cuts"]}
    removed.update({"outside_eras": 0, "outside_time_bins": 0})
    crossing = []
    kept = 0
    for p in ordered:
        failed = next((c["name"] for c in cfg["quality_cuts"] if not OPS[c["op"]](p["quality"][c["name"]], c["value"])), None)
        if failed:
            removed[failed] += 1
            continue
        a, b = p["start"], p["start"] + p["duration"]
        era = next((e for e in eras if e[0] <= a < e[1]), None)
        if era is None:
            removed["outside_eras"] += 1
            continue
        if b > era[1]:
            crossing.append({"key": p["key"], "boundary": "era", "at": era[1]})
            continue
        tb = next((k for k in range(nt) if tedges[k] <= a < tedges[k + 1]), None)
        if tb is None:
            removed["outside_time_bins"] += 1
            continue
        if b > tedges[tb + 1]:
            crossing.append({"key": p["key"], "boundary": "time bin", "at": tedges[tb + 1]})
            continue
        live = p["duration"] * p["live"]
        lt[era[2]][tb] += live
        for f, k in zip(sfs, sf_keys):
            threshold = f * p["cutoff"]
            row = ct[era[2]][k][tb]
            for j in range(nx):
                if edges[j] >= threshold:
                    row[j] += live
        kept += 1
    if crossing:
        raise InputError("periods cross an era or time-bin boundary; split them at the boundary first",
                         crossing=crossing[:20], n_crossing=len(crossing))
    return {"collection_time_s": ct, "livetime_s": lt,
            "diagnostics": {"periods_read": len(periods), "periods_unique": len(unique), "duplicates_removed": duplicates,
                            "removed": {k: v for k, v in removed.items() if v or k in {c["name"] for c in cfg["quality_cuts"]}},
                            "periods_kept": kept}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("accumulate", help="collection time from period tables")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("periods", nargs="+", type=Path)
    p.add_argument("--emit-partial", type=Path, help="write the deduplicated periods for a later merge")
    p.add_argument("--out", type=Path)
    add_status_argument(p)
    p = sub.add_parser("merge", help="collection time from partials made with the same configuration")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("partials", nargs="+", type=Path)
    p.add_argument("--out", type=Path)
    add_status_argument(p)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: (str(v) if isinstance(v, Path) else [str(x) for x in v] if isinstance(v, list) else v)
              for k, v in vars(args).items()}
    report: dict = {"status_label": args.status, "inputs": inputs,
                    "defaults_used": [] if "--status" in given else ["status"]}
    try:
        cfg, cfg_sha = load_config(args.config)
        if args.command == "accumulate":
            periods, sources = read_periods(args.periods, cfg)
        else:
            periods, sources = [], []
            for path in args.partials:
                try:
                    doc = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise InputError(f"cannot read {path}: {exc}") from None
                if not isinstance(doc, dict) or doc.get("kind") != PARTIAL_KIND:
                    raise InputError(f"{path} is not a collection-time partial")
                if doc.get("config_sha256") != cfg_sha:
                    raise InputError(f"{path} was made with another configuration", partial=str(path))
                periods += doc["periods"]
                sources += doc["sources"]
        if args.command == "accumulate" and args.emit_partial:
            accumulate(periods, cfg)  # refuse here what a merge would refuse later
            doc = {"kind": PARTIAL_KIND, "config_sha256": cfg_sha, "periods": periods, "sources": sources}
            text = json.dumps(doc, indent=1) + "\n"
            args.emit_partial.parent.mkdir(parents=True, exist_ok=True)
            args.emit_partial.write_text(text, encoding="utf-8")
            report.update(status="ok", partial=str(args.emit_partial),
                          partial_sha256=hashlib.sha256(text.encode()).hexdigest(), periods_read=len(periods))
        else:
            report.update(accumulate(periods, cfg))
            report.update(status="ok", x=cfg["x"], time_edges=cfg["time_edges"], eras=cfg["eras"],
                          safety_factors=[float(f) for f in cfg["transmission"]["safety_factors"]],
                          config_sha256=cfg_sha, sources=sources,
                          normalization={"composition": COMPOSITION, "effects_applied": ["livetime", "cutoff_transmission"],
                                         "rule": "a bin receives a period's live time when its lower edge >= safety factor x cutoff",
                                         "note": "multiply by the acceptance for the exposure; efficiencies are separate factors"},
                          naming="collection time (seconds of live time above the cutoff threshold); the contracts' "
                                 "exposure_record is the blinding record of data exposure, not this quantity")
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    except InputError as exc:
        report.update(status="rejected", error=str(exc), **exc.extra)
    except OSError as exc:
        report.update(status="rejected", error=f"cannot write the output: {exc.strerror or exc}")
    print(json.dumps(report, indent=1))
    if report["status"] != "ok":
        print(f"collection_time.py: error: {report.get('error')}", file=sys.stderr)
    return exit_code(report["status"])


if __name__ == "__main__":
    sys.exit(main())
