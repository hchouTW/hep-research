#!/usr/bin/env python3
"""Bartels rotation numbers and dates, and rotation averages of a daily heliospheric input with a time lag (Th13).

Purpose: put the inputs of a time-dependent solar-modulation model (tilt angle, field magnitude, sunspot number, a
neutron-monitor potential, ...) on the same time bins as a flux published per Bartels rotation, with a stated lag.
See <plugin root>/skills/hep-theory/references/solar-modulation-models.md, "Lining a model up with time-resolved data".
Method: a Bartels rotation is a 27-day interval counted continuously from 1832-02-08 (rotation 1 starts that day; WDC
Kp/Ap format description, ftp.space.dtu.dk/WDC/indices/kp-ap/wdc/wdc_fmt.txt, read 2026-10-20). Rotation n covers the
UT days [1832-02-08 + 27 (n - 1), 1832-02-08 + 27 n). Cross-check: rotation 2426 starts 2011-05-15 (Caltech ACE
Science Center table Bartels2008-2027.pdf, read 2026-10-20; tested).
- rotation: date(s) -> rotation number, day in rotation (1-27), start, end (exclusive).
- dates: rotation number(s) -> start, end (exclusive).
- average: a daily series (CSV with a header; ISO dates) averaged over each rotation window shifted EARLIER by
  --lag-days (the input that drives the flux of rotation n is read over [start - lag, end - lag)), with the number of
  days used and the coverage. A rotation whose coverage is below --min-coverage makes the run "incomplete" (exit 3);
  the threshold has no default. Dates must be YYYY-MM-DD (UT days); repeated dates and timestamps are refused, so
  an hourly or sub-daily series is aggregated to days first. The lag is a model input (for example a fitted one);
  none is built in. A negative lag reads the input after the flux window and is allowed for tests of causality.
Assumptions: days are UT calendar days; an input value is attached to its whole day; the plain mean is used (no
weighting). Moving averages over several rotations, interpolation and gap filling are not done.
Usage: bartels_rotation.py rotation --date 2011-05-15 [...]
       bartels_rotation.py dates --rotation 2426 [2427 ...]   (or --range 2426 2504)
       bartels_rotation.py average --series FILE.csv --date-column date --value-column tilt_deg
         --rotation N [...] | --range N M  --lag-days L --min-coverage F [--status LABEL]
Output JSON: status, status_label, inputs, defaults_used, conventions, rows. Exit codes: 0 ok; 2 bad input;
3 incomplete coverage. Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

EPOCH = dt.date(1832, 2, 8)
LENGTH_DAYS = 27
CONVENTIONS = {
    "definition": "27-day intervals counted continuously from 1832-02-08 (rotation 1 starts that day)",
    "source": "WDC Kp/Ap format description (ftp.space.dtu.dk/WDC/indices/kp-ap/wdc/wdc_fmt.txt), read 2026-10-20",
    "cross_check": "rotation 2426 starts 2011-05-15 (Caltech ACE Science Center Bartels table 2008-2027)",
    "interval": "start inclusive, end exclusive, UT calendar days",
    "lag": "input window of rotation n = [start - lag, end - lag); lag > 0 means the input precedes the flux",
}


class BartelsError(ValueError):
    """An input outside the domain of the calculation."""


def parse_date(text: str) -> dt.date:
    """A calendar date written exactly YYYY-MM-DD; a timestamp is refused, since cutting it to a day can shift it
    across a day boundary in another time zone."""
    t = text.strip()
    if len(t) != 10:
        raise BartelsError(f"not a YYYY-MM-DD date: {text!r} (aggregate timestamps to UT days first)")
    try:
        return dt.date.fromisoformat(t)
    except ValueError as exc:
        raise BartelsError(f"not a YYYY-MM-DD date: {text!r}") from exc


def rotation_of(day: dt.date) -> tuple[int, int]:
    """(rotation number, day in rotation 1..27)."""
    offset = (day - EPOCH).days
    if offset < 0:
        raise BartelsError(f"{day} is before the start of rotation 1 ({EPOCH})")
    return offset // LENGTH_DAYS + 1, offset % LENGTH_DAYS + 1


def bounds(n: int) -> tuple[dt.date, dt.date]:
    """Start (inclusive) and end (exclusive) of rotation n."""
    if n < 1:
        raise BartelsError(f"rotation numbers start at 1, got {n}")
    start = EPOCH + dt.timedelta(days=LENGTH_DAYS * (n - 1))
    return start, start + dt.timedelta(days=LENGTH_DAYS)


def read_series(path: Path, date_col: str, value_col: str) -> dict[dt.date, float]:
    if not path.is_file():
        raise BartelsError(f"no such file: {path}")
    out: dict[dt.date, float] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:  # tolerate a byte-order mark
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or date_col not in reader.fieldnames or value_col not in reader.fieldnames:
            raise BartelsError(f"columns {date_col!r} and {value_col!r} must both be in the header {reader.fieldnames}")
        for i, row in enumerate(reader, start=2):
            day = parse_date(row[date_col])
            if day in out:
                raise BartelsError(f"line {i}: date {day} repeated; give one value per day")
            raw = (row[value_col] or "").strip()
            if raw == "":
                continue  # a missing day; counted as not covered
            try:
                value = float(raw)
            except ValueError as exc:
                raise BartelsError(f"line {i}: value {raw!r} is not a number") from exc
            if not math.isfinite(value):
                raise BartelsError(f"line {i}: value {raw!r} is not finite; leave the cell empty for a missing day")
            out[day] = value
    if not out:
        raise BartelsError("the series has no values")
    return out


def averages(series: dict[dt.date, float], rotations: list[int], lag_days: float) -> list[dict]:
    if lag_days != int(lag_days):
        raise BartelsError("--lag-days must be a whole number of days")
    lag = dt.timedelta(days=int(lag_days))
    rows = []
    for n in rotations:
        start, end = bounds(n)
        w0, w1 = start - lag, end - lag
        vals = [v for d, v in series.items() if w0 <= d < w1]
        rows.append({"rotation": n, "start": start.isoformat(), "end_exclusive": end.isoformat(),
                     "window_start": w0.isoformat(), "window_end_exclusive": w1.isoformat(),
                     "n_days": len(vals), "coverage": len(vals) / LENGTH_DAYS,
                     "mean": (sum(vals) / len(vals)) if vals else None})
    return rows


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _rotation_list(a) -> list[int]:
    if a.range is not None:
        lo, hi = a.range
        if hi < lo:
            raise BartelsError("--range N M needs N <= M")
        return list(range(lo, hi + 1))
    if not a.rotation:
        raise BartelsError("give --rotation N [...] or --range N M")
    return list(a.rotation)


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=JsonArgumentParser)
    p_rot = sub.add_parser("rotation", help="date(s) -> rotation number")
    p_rot.add_argument("--date", nargs="+", required=True)
    for name in ("dates", "average"):
        p = sub.add_parser(name)
        p.add_argument("--rotation", type=int, nargs="+")
        p.add_argument("--range", type=int, nargs=2, metavar=("N", "M"))
        if name == "average":
            p.add_argument("--series", type=Path, required=True)
            p.add_argument("--date-column", required=True)
            p.add_argument("--value-column", required=True)
            p.add_argument("--lag-days", type=float, required=True)
            p.add_argument("--min-coverage", type=float, required=True)
    for p in (p_rot, *sub.choices.values()):
        if not any(x.dest == "status" for x in p._actions):
            add_status_argument(p)
    a = ap.parse_args(argv)
    inputs = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(a).items() if k != "status"}
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    base = {"status_label": a.status, "inputs": inputs,
            "defaults_used": [k for k in ("status",) if f"--{k}" not in given]}
    status = "ok"
    try:
        if a.cmd == "rotation":
            rows = []
            for text in a.date:
                day = parse_date(text)
                n, k = rotation_of(day)
                s, e = bounds(n)
                rows.append({"date": day.isoformat(), "rotation": n, "day_in_rotation": k,
                             "start": s.isoformat(), "end_exclusive": e.isoformat()})
        elif a.cmd == "dates":
            rows = [{"rotation": n, "start": s.isoformat(), "end_exclusive": e.isoformat()}
                    for n in _rotation_list(a) for s, e in [bounds(n)]]
        else:
            if not 0.0 < a.min_coverage <= 1.0:
                raise BartelsError("--min-coverage must be in (0, 1]")
            rows = averages(read_series(a.series, a.date_column, a.value_column), _rotation_list(a), a.lag_days)
            low = [r["rotation"] for r in rows if r["coverage"] < a.min_coverage]
            if low:
                status = "incomplete"
                base["below_min_coverage"] = low
    except BartelsError as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": status, **base, "label": "[General method]", "conventions": CONVENTIONS,
                      "rows": rows}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
