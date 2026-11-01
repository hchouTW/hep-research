#!/usr/bin/env python3
"""Export events from a ROOT TTree (or Parquet) to one Phoenix event JSON per event, using a declared mapping.

Usage: python3 export_events.py INPUT --mapping mapping.json --out DIR [--status LABEL]
                                 [--entries START:STOP | --events RUN_SUBRUN_EVENT,...]
Template: copy into the project and edit the mapping, not this code, for a new flat ntuple.
Selection: --entries takes tree entries START (inclusive) to STOP (exclusive); --events takes the listed events, in
that order (all must exist). The event limit is checked before any coordinate is read. DIR must be empty or new.
Parquet input needs pyarrow (exit 3 without it).

Writes DIR/events/<run>_<subrun>_<event>.json and DIR/export-record.json (inputs with sha256, mapping, per-event
file sha256, object counts, labels). Only the safe Phoenix subset is written:
  points    -> "Hits" collection, type "Point" (one colour per collection; no per-point size or value)
  polylines -> "Hits" collection, type "Line": one item per straight segment between consecutive points (6 numbers)
Never written: "Tracks" (Phoenix recomputes phi/eta/d0 in the browser and redraws them as smooth curves).
Coordinates are converted to mm with the declared unit; non-finite values, missing units and limit overflows are
refused, never silently dropped or truncated.
Prints JSON {"status": ...}; exit 0 ok, 1 refused (limits), 2 bad input, 3 missing dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

UNIT_TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "um": 1e-3}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(status: str, code: int, reason: str) -> int:
    print(json.dumps({"status": status, "reason": reason}))
    return code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--status", default="unvalidated", help="label carried to the outputs (e.g. synthetic)")
    sel = ap.add_mutually_exclusive_group()
    sel.add_argument("--entries", help="START:STOP, tree entries to export (STOP exclusive)")
    sel.add_argument("--events", help="comma-separated run_subrun_event keys to export, in this order")
    a = ap.parse_args(argv)
    try:
        import awkward as ak
        import numpy as np
        import uproot
    except ImportError as exc:
        return fail("missing-dependency", 3, str(exc))
    try:
        m = json.loads(Path(a.mapping).read_text())
    except (OSError, ValueError) as exc:
        return fail("rejected", 2, f"mapping unreadable: {exc}")
    unit = m.get("unit")
    if unit not in UNIT_TO_MM:
        return fail("rejected", 2, f"mapping 'unit' must be one of {sorted(UNIT_TO_MM)}, got {unit!r}")
    k = UNIT_TO_MM[unit]
    limits = m.get("limits", {})
    max_events, max_objects = int(limits.get("max_events", 50)), int(limits.get("max_objects_per_event", 200000))
    ids = m["id"]
    branches = [ids["run"], ids["subrun"], ids["event"]]
    id_branches = list(branches)
    for c in m.get("points", []):
        branches += [c["x"], c["y"], c["z"]]
    for c in m.get("polylines", []):
        branches += [c["x"], c["y"], c["z"], c["group"]]
    inp = Path(a.input)
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        return fail("rejected", 2, f"{out} is not empty; export into a new folder (stale events would stay)")
    start, stop = 0, None
    if a.entries:
        try:
            s, e = a.entries.split(":")
            start, stop = int(s or 0), (int(e) if e else None)
        except ValueError:
            return fail("rejected", 2, "--entries must be START:STOP with integers")
    if inp.suffix == ".parquet":
        try:
            import pyarrow  # noqa: F401  (awkward reads Parquet through it)
        except ImportError as exc:
            return fail("missing-dependency", 3, f"Parquet input needs pyarrow: {exc}")
    try:
        if inp.suffix == ".parquet":
            arr = ak.from_parquet(inp)
            read = lambda b, lo, hi: (arr[tuple(b.split("."))] if "." in b else arr[b])[lo:hi]  # noqa: E731
            total = len(arr)
        else:
            tree = uproot.open(inp)[m["tree"]]
            # read branch by branch: tree.arrays() regroups dotted names ("hit.x") into records
            read = lambda b, lo, hi: tree[b].array(library="ak", entry_start=lo, entry_stop=hi)  # noqa: E731
            total = int(tree.num_entries)
        stop = total if stop is None else min(stop, total)
        if a.events:
            wanted = [k.strip() for k in a.events.split(",") if k.strip()]
            if len(wanted) > max_events:
                return fail("refused", 1, f"{len(wanted)} events exceed max_events={max_events}")
            idcols = {b: read(b, 0, total) for b in set(id_branches)}          # ids only: small
            index = {f"{int(r)}_{int(s)}_{int(e)}": i for i, (r, s, e) in
                     enumerate(zip(*(idcols[ids[x]].tolist() for x in ("run", "subrun", "event"))))}
            absent = [k for k in wanted if k not in index]
            if absent:
                return fail("rejected", 2, f"events not in the input: {', '.join(absent[:10])}")
            rows = [index[k] for k in wanted]
        else:
            if stop - start > max_events:
                return fail("refused", 1, f"{stop - start} entries exceed max_events={max_events}; select with "
                                          "--entries or --events, or raise limits.max_events in the mapping")
            rows = list(range(start, stop))
        lo, hi = (min(rows), max(rows) + 1) if rows else (0, 0)
        window = {b: read(b, lo, hi) for b in set(branches)}               # only the selected range is read
        columns = {b: [window[b][r - lo] for r in rows] for b in window}
    except Exception as exc:  # uproot/awkward raise many types for unreadable input
        return fail("rejected", 2, f"input unreadable with the mapping: {exc}")
    n = len(rows)
    if n == 0:
        return fail("rejected", 2, "no event selected")

    (out / "events").mkdir(parents=True, exist_ok=True)
    record = {"schema": "event-display-export/1", "status_label": a.status, "unit_out": "mm",
              "inputs": [{"path": inp.name, "sha256": sha256_file(inp)},
                         {"path": Path(a.mapping).name, "sha256": sha256_file(Path(a.mapping))}],
              "events": []}
    seen = set()
    for i in range(n):
        run, subrun, event = (str(int(columns[ids[x]][i])) for x in ("run", "subrun", "event"))
        key = f"{run}_{subrun}_{event}"
        if key in seen:
            return fail("rejected", 2, f"duplicate event id {key}")
        seen.add(key)
        hits, count = {}, 0
        for c in m.get("points", []):
            xs, ys, zs = (np.asarray(columns[c[q]][i], dtype=float) * k for q in ("x", "y", "z"))
            pts = np.stack([xs, ys, zs], axis=1)
            if not np.isfinite(pts).all():
                return fail("rejected", 2, f"non-finite coordinate in {c['collection']} of event {key}")
            hits[c["collection"]] = [{"pos": p.tolist(), "type": "Point", "color": c.get("color", "#2b8cbe")}
                                     for p in pts]
            count += len(pts)
        for c in m.get("polylines", []):
            xs, ys, zs = (np.asarray(columns[c[q]][i], dtype=float) * k for q in ("x", "y", "z"))
            grp = np.asarray(columns[c["group"]][i])
            segs = []
            for g in dict.fromkeys(grp.tolist()):           # keep first-seen order of polyline ids
                sel = grp == g
                p = np.stack([xs[sel], ys[sel], zs[sel]], axis=1)
                if not np.isfinite(p).all():
                    return fail("rejected", 2, f"non-finite coordinate in {c['collection']} of event {key}")
                segs += [{"pos": [*p[j].tolist(), *p[j + 1].tolist()], "type": "Line",
                          "color": c.get("color", "#e6550d"), "polyline": int(g)} for j in range(len(p) - 1)]
            hits[c["collection"]] = segs
            count += len(segs)
        if count > max_objects:
            return fail("refused", 1, f"event {key}: {count} objects exceed max_objects_per_event={max_objects}")
        ev = {"run number": run, "event number": event, "subrun": subrun, "Hits": hits}
        path = out / "events" / f"{key}.json"
        path.write_text(json.dumps(ev, separators=(",", ":"), allow_nan=False))
        record["events"].append({"id": {"run": run, "subrun": subrun, "event": event}, "file": f"events/{key}.json",
                                 "sha256": sha256_file(path), "objects": count, "bytes": path.stat().st_size})
    (out / "export-record.json").write_text(json.dumps(record, indent=1))
    print(json.dumps({"status": "ok", "status_label": a.status, "events": n, "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
