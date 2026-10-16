#!/usr/bin/env python3
"""Query a source and claim ledger (evidence/sources.json, evidence/claims.json) in bounded, pageable rows.

Purpose: let an agent read only the evidence rows a task needs, with each row traceable to its ledger record, instead
of loading a whole ledger. The ledger is first checked with core/evidence/ledger.py (same read path, same
verification strengths); a ledger with errors is refused, never partly served.

Rows: one per (claim, cited source) pair, in a stable order (claim id, then source id). Each row carries the claim id
and text, the source id and title, the claim's scope, the source's verification_date (access_date when that is the
only date recorded, as in ledger.py), the source's verification_level, the claim's verification_strength, the
claim's location in the source, and the record position in each ledger file. Fields are copied, never rewritten.

Paging: a page holds at most --page-size rows (default 20) and its JSON output at most --max-bytes bytes (default
16384). These defaults are product defaults, not measurements. Every page reports the total match count, the ledger's
index digest, and a cursor for the next page bound to that digest and to the query; a cursor used after the ledger
changed, or with another query, is refused (query.stale_cursor, query.cursor_mismatch: run the query again). A row
that alone exceeds --max-bytes is not cut: the page carries an overflow marker with the exact command that fetches
it, and the cursor moves past it.

Usage (from the plugin root):
  python3 core/evidence/query.py --sources P --claims P [--claim ID] [--source ID] [--match TEXT]
                                 [--min-strength LEVEL] [--namespace NS] [--page-size N] [--max-bytes N]
                                 [--cursor C] [--today YYYY-MM-DD]
Exit codes: 0 rows served (possibly none); 1 the ledger has errors; 2 unreadable files, bad arguments, or a stale or
mismatched cursor. Output: JSON with a status key. Standard library only. Importable: query_ledger(...).
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

if __package__ in (None, ""):  # run as a script: put the plugin root on sys.path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.evidence.ledger import STRENGTH, _parse_day, _read_date, check_ledger  # noqa: E402
from core.protected.guard import guard, protected_main  # noqa: E402

FORMAT = "hep-research-evidence-query/1"
PAGE_SIZE, MAX_BYTES = 20, 16384  # product defaults, not measurements
PAGE_SIZE_MAX, MAX_BYTES_MIN = 200, 1024
ERRORS_SHOWN = 10


class QueryRefused(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dumps(obj) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False)


def index_digest(sources_bytes: bytes, claims_bytes: bytes) -> str:
    """Digest of the ledger snapshot a cursor is bound to: the bytes of both files and the row format."""
    return _sha(json.dumps({"format": FORMAT, "sources": _sha(sources_bytes), "claims": _sha(claims_bytes)},
                           sort_keys=True).encode())


def _query_digest(query: dict) -> str:
    return _sha(json.dumps(query, sort_keys=True).encode())


def encode_cursor(index: str, query: dict, offset: int) -> str:
    raw = json.dumps({"v": 1, "index": index, "query": _query_digest(query), "offset": offset}, sort_keys=True)
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str, index: str, query: dict) -> int:
    try:
        doc = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        offset = doc["offset"]
        if doc.get("v") != 1 or not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError
    except (binascii.Error, UnicodeError, ValueError, KeyError, TypeError):
        raise QueryRefused("query.bad_cursor", "the cursor cannot be read: run the query again without --cursor") from None
    if doc.get("index") != index:
        raise QueryRefused("query.stale_cursor", "the ledger changed since this cursor was issued: run the query again "
                                                 "without --cursor")
    if doc.get("query") != _query_digest(query):
        raise QueryRefused("query.cursor_mismatch", "the cursor belongs to another query: run this query without --cursor")
    return offset


def rows_of(sources: list, claims: list, files: dict) -> list[dict]:
    """Every (claim, cited source) row of a checked ledger, in the stable order."""
    src = {s["id"]: (j, s) for j, s in enumerate(sources) if isinstance(s, dict) and isinstance(s.get("id"), str)}
    rows = []
    for i, c in enumerate(claims):
        for sid in c.get("source_ids") or []:
            j, s = src[sid]
            date_field = "verification_date" if "verification_date" in s else ("access_date" if "access_date" in s else None)
            rows.append({"claim_id": c["id"], "claim": c.get("claim"), "source_id": sid, "source_title": s.get("title"),
                         "scope": c.get("scope"), "verification_date": _read_date(s), "verification_date_field": date_field,
                         "verification_level": s.get("verification_level"),
                         "verification_strength": c.get("verification_strength"), "location": c.get("location"),
                         "record": {"claims_file": files["claims"], "claim_index": i,
                                    "sources_file": files["sources"], "source_index": j}})
    rows.sort(key=lambda r: (r["claim_id"], r["source_id"], r["record"]["claim_index"], r["record"]["source_index"]))
    return rows


def _matches(row: dict, query: dict) -> bool:
    if query["claim"] is not None and row["claim_id"] != query["claim"]:
        return False
    if query["source"] is not None and row["source_id"] != query["source"]:
        return False
    if query["min_strength"] is not None and STRENGTH.get(row["verification_strength"], 0) < STRENGTH[query["min_strength"]]:
        return False
    if query["match"] is not None:
        scope = row["scope"] if isinstance(row["scope"], dict) else {}
        text = f"{row['claim'] or ''}\n{scope.get('text') or ''}".casefold()
        if query["match"].casefold() not in text:
            return False
    return True


def _fetch_argv(files: dict, query: dict, cursor: str, max_bytes: int) -> list[str]:
    argv = ["python3", "core/evidence/query.py", "--sources", files["sources"], "--claims", files["claims"]]
    for flag, key in (("--claim", "claim"), ("--source", "source"), ("--match", "match"),
                      ("--min-strength", "min_strength"), ("--namespace", "namespace")):
        if query[key] is not None:
            argv += [flag, query[key]]
    return argv + ["--page-size", "1", "--max-bytes", str(max_bytes), "--cursor", cursor]


def query_ledger(sources_bytes: bytes, claims_bytes: bytes, files: dict, *, claim=None, source=None, match=None,
                 min_strength=None, namespace=None, page_size: int = PAGE_SIZE, max_bytes: int = MAX_BYTES,
                 cursor: str | None = None, today: date | None = None) -> dict:
    """One page of rows. files: {"sources", "claims"} as shown in rows and fetch commands. Raises QueryRefused for bad
    arguments or cursors and ValueError for unreadable JSON; a ledger with errors gives status ledger_invalid."""
    guard("core.evidence.query.query_ledger")
    if not 1 <= page_size <= PAGE_SIZE_MAX:
        raise QueryRefused("query.bad_page_size", f"--page-size must be 1-{PAGE_SIZE_MAX}")
    if max_bytes < MAX_BYTES_MIN:
        raise QueryRefused("query.bad_max_bytes", f"--max-bytes must be at least {MAX_BYTES_MIN}")
    if min_strength is not None and min_strength not in STRENGTH:
        raise QueryRefused("query.bad_strength", f"--min-strength must be one of {sorted(STRENGTH)}")
    sources, claims = json.loads(sources_bytes.decode("utf-8")), json.loads(claims_bytes.decode("utf-8"))
    index = index_digest(sources_bytes, claims_bytes)
    report = check_ledger(sources, claims, today, namespace=namespace)
    if report["status"] == "fail":
        return {"status": "ledger_invalid", "index_digest": index, "error_count": len(report["errors"]),
                "errors": report["errors"][:ERRORS_SHOWN],
                "note": "the ledger has errors (core/evidence/ledger.py): no rows are served from it"}
    query = {"claim": claim, "source": source, "match": match, "min_strength": min_strength, "namespace": namespace}
    offset = decode_cursor(cursor, index, query) if cursor else 0
    hits = [r for r in rows_of(sources, claims, files) if _matches(r, query)]
    if offset > len(hits):
        raise QueryRefused("query.bad_cursor", "the cursor points past the last match: run the query again")
    limits = {"page_size": page_size, "max_bytes": max_bytes,
              "note": "page size and byte cap are product defaults or caller choices, not measurements"}

    def page(rows: list, nxt: int, overflow) -> dict:
        return {"status": "ok", "format": FORMAT, "index_digest": index, "query": query, "total_matches": len(hits),
                "offset": offset, "returned": len(rows), "rows": rows,
                "next_cursor": encode_cursor(index, query, nxt) if nxt < len(hits) else None,
                "overflow": overflow, "limits": limits}

    rows: list[dict] = []
    while offset + len(rows) < len(hits) and len(rows) < page_size:
        trial = page(rows + [hits[offset + len(rows)]], offset + len(rows) + 1, None)
        if len(_dumps(trial).encode()) > max_bytes:
            break
        rows.append(hits[offset + len(rows)])
    if rows or offset >= len(hits):
        return page(rows, offset + len(rows), None)
    # the row at offset alone exceeds the cap: never cut it, say how to fetch it, move past it
    alone = len(_dumps(page([hits[offset]], offset + 1, None)).encode())
    here = encode_cursor(index, query, offset)
    need = alone + 1024  # room for the fetch page's own cursor and limits
    overflow = {"row_offset": offset, "claim_id": hits[offset]["claim_id"], "source_id": hits[offset]["source_id"],
                "bytes": alone, "fetch": _fetch_argv(files, query, here, need)}
    return page([], offset + 1, overflow)


@protected_main("core.evidence.query")
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("--sources", type=Path, required=True, help="evidence/sources.json of a profile or a docs ledger")
    parser.add_argument("--claims", type=Path, required=True, help="evidence/claims.json")
    parser.add_argument("--claim", default=None, help="only this claim id")
    parser.add_argument("--source", default=None, help="only rows citing this source id")
    parser.add_argument("--match", default=None, help="case-insensitive text in the claim or its scope.text")
    parser.add_argument("--min-strength", default=None, help=f"only claims at least this strong: {sorted(STRENGTH)}")
    parser.add_argument("--namespace", default=None, help="require IDs of the form <namespace>:S01 / <namespace>:C01")
    parser.add_argument("--page-size", type=int, default=PAGE_SIZE,
                        help=f"rows per page, 1-{PAGE_SIZE_MAX} (default {PAGE_SIZE}: a product default, not a measurement)")
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES,
                        help=f"cap on the JSON output of one page, at least {MAX_BYTES_MIN} (default {MAX_BYTES}: a product "
                             "default, not a measurement)")
    parser.add_argument("--cursor", default=None, help="next_cursor of the previous page")
    parser.add_argument("--today", default=None, help="YYYY-MM-DD for the ledger check (default: system date)")
    args = parser.parse_args(argv)
    today = _parse_day(args.today) if args.today else date.today()
    if today is None:
        print(_dumps({"status": "unreadable", "error": "--today must be YYYY-MM-DD"}))
        return 2
    try:
        sb, cb = args.sources.read_bytes(), args.claims.read_bytes()
        out = query_ledger(sb, cb, {"sources": str(args.sources), "claims": str(args.claims)}, claim=args.claim,
                           source=args.source, match=args.match, min_strength=args.min_strength,
                           namespace=args.namespace, page_size=args.page_size, max_bytes=args.max_bytes,
                           cursor=args.cursor, today=today)
    except QueryRefused as exc:
        print(_dumps({"status": "refused", "code": exc.code, "error": str(exc)}))
        return 2
    except (OSError, ValueError) as exc:
        print(_dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    print(_dumps(out))
    return 0 if out["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
