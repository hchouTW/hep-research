#!/usr/bin/env python3
"""Build, run and summarize ONE CRDB (LPSC) REST query for cross-checking a published AMS number.

CRDB (https://lpsc.in2p3.fr/crdb/) is a Tier 6 secondary compilation: values are
transcriptions of publications. This helper never makes a CRDB value an AMS result: every
row it prints is labelled `secondary`, every saved export gets a sidecar `.meta.json`
with the request, the retrieval time (UTC), the CRDB export date from the file header,
a SHA-256, and the CRDB version only if YOU pass it (the export header names the CRDB
papers, not a release number, so the version is recorded as null otherwise).
See modules/cosmic-ray-databases.md and ledger claims C125-C130.

Defaults follow the cross-check procedure of that reference: native axis (`--energy-type`
is required, no default), `combo_level=0` and `energy_convert_level=0` (no query-time
combinations or conversions) and `exp_dates=AMS`. `time_series` is sent only when you
ask for it: CRDB excludes time series (for example per-Bartels-rotation fluxes) by
default (C128). Parameter names and ranges are those of C128 and may change.

Rules: one request per `fetch` run, identifying User-Agent, no credentials, https only,
a size cap, one retry of a transient error (HTTP 5xx or a network failure) and none of a
refusal (401, 403, 429): a block is reported, never worked around.

Usage (from the skill directory; every command has --help):
  python3 profiles/experiments/ams-02/scripts/crdb_query.py url --num H --energy-type R [--den ...] [--exp-dates AMS ...]
  python3 profiles/experiments/ams-02/scripts/crdb_query.py fetch --num H --energy-type R --out DIR/name.csv [--crdb-version V4.2]
  python3 profiles/experiments/ams-02/scripts/crdb_query.py summarize DIR/name.csv [--rows]
Exit codes: 0 ok; 1 request refused or failed, or an export with no data rows; 2 usage error or
unreadable file. Standard library only. Importable: `build_params`, `build_url`, `Fetcher`,
`parse_export`, `summarize` (the HTTP layer is injectable for tests).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

BASE_URL = "https://lpsc.in2p3.fr/crdb/rest.php"
USER_AGENT = "ams-analysis-crdb-query/1 (single query; no credentials; honors blocks)"
ENERGY_TYPES = ("EKN", "EK", "R", "ETOT", "ETOTN")
FORMATS = ("csv", "csv-asimport", "usine", "galprop")
MODULATIONS = ("USO05", "USO17", "GHE17")
TIME_SERIES = ("no", "only", "all")
BLOCKED_STATUS = {401, 403, 429}
DEFAULT_MAX_MB = 20
LABEL = "secondary: CRDB transcription, check against the primary paper"


class UsageError(ValueError):
    pass


def _level(name: str, v) -> int:
    if v not in (0, 1, 2):
        raise UsageError(f"{name} must be 0, 1 or 2, got {v!r}")
    return int(v)


def build_params(num: str, energy_type: str, den: str = "", exp_dates: str | None = "AMS",
                 combo_level: int = 0, energy_convert_level: int = 0, energy_start=None, energy_stop=None,
                 time_start: str | None = None, time_stop: str | None = None, time_series: str | None = None,
                 fmt: str | None = None, modulation: str | None = None, flux_rescaling=None) -> dict:
    """Return the query parameters as an ordered dict of strings; raise UsageError on a bad value."""
    if not num or not num.strip():
        raise UsageError("num (numerator, for example H, 1H-BAR, e-, O-group) is required")
    if energy_type not in ENERGY_TYPES:
        raise UsageError(f"energy_type must be one of {', '.join(ENERGY_TYPES)}, got {energy_type!r}")
    p = {"num": num.strip(), "den": (den or "").strip(), "energy_type": energy_type}
    if exp_dates:
        p["exp_dates"] = exp_dates
    p["combo_level"] = str(_level("combo_level", combo_level))
    p["energy_convert_level"] = str(_level("energy_convert_level", energy_convert_level))
    for name, v in (("energy_start", energy_start), ("energy_stop", energy_stop), ("flux_rescaling", flux_rescaling)):
        if v is not None:
            try:
                float(v)
            except (TypeError, ValueError):
                raise UsageError(f"{name} must be a number, got {v!r}") from None
            p[name] = str(v)
    for name, v in (("time_start", time_start), ("time_stop", time_stop)):
        if v is not None:
            if not re.fullmatch(r"\d{4}(/\d{2})?", v):
                raise UsageError(f"{name} must be YYYY or YYYY/MM, got {v!r}")
            p[name] = v
    if time_series is not None:
        if time_series not in TIME_SERIES:
            raise UsageError(f"time_series must be one of {', '.join(TIME_SERIES)}, got {time_series!r}")
        p["time_series"] = time_series
    if fmt is not None:
        if fmt not in FORMATS:
            raise UsageError(f"format must be one of {', '.join(FORMATS)}, got {fmt!r}")
        p["format"] = fmt
    if modulation is not None:
        if modulation not in MODULATIONS:
            raise UsageError(f"modulation must be one of {', '.join(MODULATIONS)}, got {modulation!r}")
        p["modulation"] = modulation
    return p


def build_url(params: dict) -> str:
    # urlencode percent-encodes '+' as %2B, which CRDB needs for a positron (e+); ':' and '(' are kept readable.
    return BASE_URL + "?" + urllib.parse.urlencode(params, safe=":()/", quote_via=urllib.parse.quote)


# ---------------------------------------------------------------- HTTP
@dataclass
class Response:
    status: int
    content_type: str
    data: bytes
    url: str


class Http:
    """Plain urllib GET with a size cap, an identifying User-Agent and no credentials."""

    def __init__(self, timeout: float = 90.0):
        self.timeout = timeout

    def get(self, url: str, max_bytes: int) -> Response:
        if not url.startswith("https://"):
            raise UsageError(f"refusing non-https url {url}")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv,text/plain,*/*"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return Response(r.status, r.headers.get("Content-Type", ""), r.read(max_bytes + 1), r.geturl())
        except urllib.error.HTTPError as e:
            return Response(e.code, e.headers.get("Content-Type", "") if e.headers else "", b"", url)
        except (urllib.error.URLError, TimeoutError, OSError):
            return Response(0, "", b"", url)


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Fetcher:
    def __init__(self, http=None, max_mb: int = DEFAULT_MAX_MB, retries: int = 1, retry_wait: float = 10.0,
                 sleep=time.sleep, clock=now_utc):
        self.http, self.max_bytes = http or Http(), max_mb * (1 << 20)
        self.retries, self.retry_wait, self.sleep, self.clock = retries, retry_wait, sleep, clock

    def fetch(self, url: str) -> tuple[str, str, Response | None]:
        """Return (outcome, detail, response); outcome is ok | blocked | too-large | http-error | not-an-export."""
        resp = None
        for attempt in range(self.retries + 1):
            resp = self.http.get(url, self.max_bytes)
            if resp.status in BLOCKED_STATUS:
                return "blocked", f"HTTP {resp.status} (not retried, not bypassed)", resp
            transient = resp.status == 0 or resp.status >= 500
            if transient and attempt < self.retries:
                self.sleep(self.retry_wait)
                continue
            break
        if resp.status == 0 or resp.status >= 400:
            return "http-error", f"HTTP {resp.status}", resp
        if len(resp.data) > self.max_bytes:
            return "too-large", f"more than {self.max_bytes // (1 << 20)} MB", resp
        head = resp.data[:200].decode("utf-8", "replace")
        if not head.startswith("# Data export from CRDB"):
            return "not-an-export", f"content-type {resp.content_type or '?'}, no CRDB export header", resp
        return "ok", "", resp


# ---------------------------------------------------------------- parsing
COL_RE = re.compile(r"^#\s*Col\.(\d+)\s*-\s*(.+?)\s*$")


def parse_export(text: str) -> dict:
    """Parse a CRDB csv export: header comments, the column names they declare, and the data rows."""
    comments, cols = [], {}
    body = []
    for line in text.splitlines():
        if line.startswith("#"):
            comments.append(line)
            m = COL_RE.match(line)
            if m:
                cols[int(m.group(1))] = m.group(2)
        elif line.strip():
            body.append(line)
    names = [cols[i] for i in sorted(cols)]
    export_date = next((c.split(":", 1)[1].strip() for c in comments if c.startswith("# Date:")), None)
    rows = []
    for rec in csv.reader(io.StringIO("\n".join(body))):
        if names and len(rec) != len(names):
            raise ValueError(f"row with {len(rec)} fields but the header declares {len(names)} columns")
        rows.append(dict(zip(names, rec)) if names else {"fields": rec})
    return {"comments": comments, "columns": names, "export_date": export_date, "rows": rows}


def summarize(parsed: dict, include_rows: bool = False) -> dict:
    groups: dict = {}
    for r in parsed["rows"]:
        k = (r.get("SUBEXP-NAME"), r.get("SUBEXP-DATES"), r.get("DATA-QTY"), r.get("DATA-EAXIS"), r.get("PUBLI-DATAORIGIN"))
        groups[k] = groups.get(k, 0) + 1
    out = {
        "label": LABEL,
        "export_date": parsed["export_date"],
        "columns": parsed["columns"],
        "n_rows": len(parsed["rows"]),
        "sub_experiments": [
            {"subexp_name": k[0], "data_taking_dates": k[1], "quantity": k[2], "energy_axis": k[3],
             "data_origin": k[4], "n_rows": n} for k, n in groups.items()],
        "notes": [
            "Several sub-experiments can describe the same AMS data (different periods, analyses or time resolution): do not merge or average them.",
            "A systematic error of 0 means 'not separately quoted' for old data, not an AMS statement.",
            "Match each sub-experiment to its AMS paper through its name and data-taking dates, then compare with the ledger claim.",
        ],
    }
    if include_rows:
        out["rows"] = [dict(r, secondary=True) for r in parsed["rows"]]
    return out


def sidecar(url: str, final_url: str, resp: Response, parsed: dict, crdb_version: str | None, retrieved: str) -> dict:
    return {
        "label": LABEL,
        "requested_url": url,
        "final_url": final_url,
        "retrieved_utc": retrieved,
        "http_status": resp.status,
        "bytes": len(resp.data),
        "sha256": hashlib.sha256(resp.data).hexdigest(),
        "crdb_export_date": parsed["export_date"],
        "crdb_version": crdb_version,
        "crdb_version_note": None if crdb_version else "not recorded: the export header names the CRDB papers, not a release; pass --crdb-version",
        "n_rows": len(parsed["rows"]),
    }


# ---------------------------------------------------------------- commands
def _params_from(args) -> dict:
    return build_params(args.num, args.energy_type, den=args.den, exp_dates=args.exp_dates or None,
                        combo_level=args.combo_level, energy_convert_level=args.energy_convert_level,
                        energy_start=args.energy_start, energy_stop=args.energy_stop,
                        time_start=args.time_start, time_stop=args.time_stop, time_series=args.time_series,
                        fmt=args.format, modulation=args.modulation, flux_rescaling=args.flux_rescaling)


def cmd_url(args) -> int:
    print(build_url(_params_from(args)))
    return 0


def cmd_fetch(args, http=None) -> int:
    url = build_url(_params_from(args))
    out = Path(args.out)
    if out.exists() and not args.overwrite:
        print(f"{out} exists; use --overwrite", file=sys.stderr)
        return 2
    f = Fetcher(http=http, max_mb=args.max_mb, retries=args.retries, retry_wait=args.retry_wait)
    retrieved = f.clock()
    outcome, detail, resp = f.fetch(url)
    if outcome != "ok":
        print(json.dumps({"status": outcome, "detail": detail, "requested_url": url}, indent=2))
        return 1
    text = resp.data.decode("utf-8", "replace")
    try:
        parsed = parse_export(text)
    except ValueError as e:
        print(json.dumps({"status": "unparsable", "detail": str(e), "requested_url": url}, indent=2))
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(resp.data)
    meta = sidecar(url, resp.url, resp, parsed, args.crdb_version, retrieved)
    out.with_name(out.name + ".meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"status": "ok", "file": str(out), **{k: meta[k] for k in ("retrieved_utc", "crdb_export_date", "crdb_version", "n_rows", "sha256")},
                      "label": LABEL}, indent=2))
    return 0 if parsed["rows"] else 1


def cmd_summarize(args) -> int:
    p = Path(args.file)
    try:
        parsed = parse_export(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as e:
        print(f"cannot read {p}: {e}", file=sys.stderr)
        return 2
    s = summarize(parsed, include_rows=args.rows)
    meta = p.with_name(p.name + ".meta.json")
    if meta.exists():
        try:
            s["sidecar"] = json.loads(meta.read_text())
        except (OSError, ValueError):
            s["sidecar"] = "unreadable"
    print(json.dumps(s, indent=2))
    return 0 if parsed["rows"] else 1


def add_query_args(sp):
    sp.add_argument("--num", required=True, help="numerator, e.g. H, 1H-BAR, e-, e+, O-group")
    sp.add_argument("--den", default="", help="denominator (empty for a flux)")
    sp.add_argument("--energy-type", required=True, choices=ENERGY_TYPES, help="native axis of the quantity; no default on purpose")
    sp.add_argument("--exp-dates", default="AMS", help="sub-experiment filter (default AMS; pass '' for no filter), e.g. 'AMS' or 'PAMELA(2006:2008)'")
    sp.add_argument("--combo-level", type=int, default=0, help="0 native only (default), 1 within 5%% in energy, 2 within 20%%")
    sp.add_argument("--energy-convert-level", type=int, default=0, help="0 queried axis only (default), 1 exact conversions, 2 approximate (avoid)")
    sp.add_argument("--energy-start"); sp.add_argument("--energy-stop")
    sp.add_argument("--time-start", help="YYYY or YYYY/MM"); sp.add_argument("--time-stop", help="YYYY or YYYY/MM")
    sp.add_argument("--time-series", choices=TIME_SERIES, help="CRDB default is no (time series excluded)")
    sp.add_argument("--format", choices=FORMATS, help="CRDB default is csv-asimport; summarize needs a csv export with a column header")
    sp.add_argument("--modulation", choices=MODULATIONS)
    sp.add_argument("--flux-rescaling")


def main(argv=None, http=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("url", help="print the REST URL (offline)")
    add_query_args(u)
    fch = sub.add_parser("fetch", help="run ONE query and save the export plus a sidecar .meta.json")
    add_query_args(fch)
    fch.add_argument("--out", required=True, help="output file, e.g. cache/ams_p_R.csv")
    fch.add_argument("--crdb-version", help="the CRDB release you read on the website (recorded as given)")
    fch.add_argument("--max-mb", type=int, default=DEFAULT_MAX_MB)
    fch.add_argument("--retries", type=int, default=1, help="retries of a transient error (5xx, network); a block is never retried")
    fch.add_argument("--retry-wait", type=float, default=10.0)
    fch.add_argument("--overwrite", action="store_true")
    sm = sub.add_parser("summarize", help="list sub-experiments, periods and row counts of a saved export")
    sm.add_argument("file")
    sm.add_argument("--rows", action="store_true", help="include every row, each labelled secondary")
    try:
        args = ap.parse_args(argv)
        if args.cmd == "url":
            return cmd_url(args)
        if args.cmd == "fetch":
            return cmd_fetch(args, http=http)
        return cmd_summarize(args)
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
