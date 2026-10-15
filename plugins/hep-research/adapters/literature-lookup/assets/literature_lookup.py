#!/usr/bin/env python3
"""Look up one literature identifier in INSPIRE-HEP, ADS and arXiv and print a metadata record per source.

Purpose: an optional, executable form of the hep-communication lookup recipes
(`skills/hep-communication/references/literature-lookup-recipes.md`). It answers "does this identifier resolve,
to what, and is the cited arXiv version the latest", with the source URL and the UTC retrieval time, so an answer can
name its source instead of quoting memory. No skill requires it: without it (or without network) a citation stays
`not-verified`.

What it does:
- parses the identifier: `arxiv:1007.1727v1` (also old style `arxiv:hep-ph/0511063`, or bare), `doi:10.x/y` (or bare
  `10.x/y`), `inspire:860907` (INSPIRE record id), `bibcode:2003AJ....125..525J` (ADS only);
- queries each requested source that can resolve that identifier kind (default: all of them), one request each:
  INSPIRE-HEP REST API (`https://inspirehep.net/api/literature`), arXiv export API
  (`https://export.arxiv.org/api/query`, the unversioned id, so the reply carries the latest version) and the ADS
  search API (`https://api.adsabs.harvard.edu/v1/search/query`);
- ADS needs a personal token, read from the environment variable ADS_API_TOKEN (or ADS_TOKEN). It is sent only in
  the Authorization header of the ADS request and is never printed, recorded or written to a file. Without a token
  no ADS request is made and the ADS result is `not-verified`;
- per source it reports `status` (found, not-found, ambiguous, rate-limited, error, not-verified, unsupported),
  `read_level` (`metadata-only` when found, else `not-verified`), `source_url`, `retrieved_at` (UTC), the HTTP status
  and the metadata (title, authors, DOI, arXiv id and latest version, INSPIRE record id and texkeys, ADS bibcode,
  journal reference); for an arXiv id with a version it compares the requested version with the latest one;
- an HTTP 429 is reported as `rate-limited` with the server's Retry-After, never retried silently; requests to one
  host are spaced (arXiv 3 s, INSPIRE 0.4 s) and carry a User-Agent naming this plugin;
- `--replay DIR` answers from recorded responses (JSON files with url, http_status, headers, body, recorded_at)
  instead of the network; `retrieved_at` is then the recording time and `transport` says `replay`. `--record DIR`
  writes each live response in that format (response headers only, never the request headers).

A metadata record shows that a paper exists and where; it does not show what the paper says (read level
`metadata-only`).

Usage: literature_lookup.py IDENTIFIER [--source inspire|arxiv|ads] (repeatable; default all applicable)
                            [--replay DIR | --record DIR] [--timeout S] [--format json|text]
Exit codes (precedence 2 > 1 > 3 > 0): 0 found in at least one source with no open item; 1 not found anywhere it
was looked up; 2 invalid invocation or identifier; 3 incomplete: a version mismatch, or no source could answer
(rate limit, network error, no ADS token, ambiguous result, no recorded response). Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ADAPTER_VERSION = "0.1.0"
RECORD_VERSION = "1.0.0"
USER_AGENT = (f"hep-research-literature-lookup/{ADAPTER_VERSION} "
              "(hep-research plugin; https://github.com/hchouTW/hep-research)")
TOKEN_ENV = ("ADS_API_TOKEN", "ADS_TOKEN")
MAX_BYTES = 4 * 1024 * 1024
MIN_INTERVAL_S = {"export.arxiv.org": 3.0, "inspirehep.net": 0.4, "api.adsabs.harvard.edu": 0.2}
SOURCES = ("inspire", "arxiv", "ads")
SUPPORTS = {"inspire": {"arxiv", "doi", "inspire"}, "arxiv": {"arxiv"}, "ads": {"arxiv", "doi", "bibcode"}}
INSPIRE_FIELDS = "titles,authors.full_name,dois,arxiv_eprints,texkeys,control_number,publication_info,collaborations"
ADS_FIELDS = "bibcode,title,author,doi,identifier,pub,year,pubdate"
KEEP_HEADERS = ("content-type", "retry-after", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset")
MAX_AUTHORS = 10
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom",
        "os": "http://a9.com/-/spec/opensearch/1.1/"}
NEW_ARXIV = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")
OLD_ARXIV = re.compile(r"^([a-z][a-z.-]*(?:\.[A-Z]{2})?/\d{7})(v\d+)?$")
DOI = re.compile(r"^10\.\d{4,9}/\S+$")
BIBCODE = re.compile(r"^\d{4}[A-Za-z&.]{1,5}[A-Za-z0-9.&]{4}[A-Za-z0-9.]{4}[A-Z.]\d{3}[0-9]?[A-Z.]?$")


class InvalidIdentifier(ValueError):
    pass


def parse_identifier(text: str) -> dict:
    """Return {"input", "kind", "value", "version"}; raise InvalidIdentifier for anything else."""
    raw = text.strip()
    prefix, sep, rest = raw.partition(":")
    kind = prefix.lower() if sep and prefix.lower() in ("arxiv", "doi", "inspire", "bibcode") else None
    body = rest.strip() if kind else raw
    if kind in (None, "arxiv"):
        for pat in (NEW_ARXIV, OLD_ARXIV):
            m = pat.match(body)
            if m:
                return {"input": raw, "kind": "arxiv", "value": m.group(1), "version": m.group(2)}
        if kind == "arxiv":
            raise InvalidIdentifier(f"{raw!r} is not an arXiv identifier (e.g. arxiv:1007.1727v1)")
    if kind in (None, "doi"):
        if body.lower().startswith("https://doi.org/"):
            body = body[16:]
        if DOI.match(body):
            return {"input": raw, "kind": "doi", "value": body, "version": None}
        if kind == "doi":
            raise InvalidIdentifier(f"{raw!r} is not a DOI (e.g. doi:10.1140/epjc/s10052-011-1554-0)")
    if kind == "inspire":
        if body.isdigit():
            return {"input": raw, "kind": "inspire", "value": body, "version": None}
        raise InvalidIdentifier(f"{raw!r} is not an INSPIRE record id (e.g. inspire:860907)")
    if kind == "bibcode":
        if BIBCODE.match(body):
            return {"input": raw, "kind": "bibcode", "value": body, "version": None}
        raise InvalidIdentifier(f"{raw!r} is not an ADS bibcode (19 characters)")
    raise InvalidIdentifier(f"{raw!r}: use arxiv:ID[vN], doi:DOI, inspire:RECID or bibcode:BIBCODE")


def request_url(source: str, ident: dict) -> str:
    kind, value = ident["kind"], ident["value"]
    if source == "inspire":
        if kind == "inspire":
            return f"https://inspirehep.net/api/literature/{value}?fields={INSPIRE_FIELDS}"
        q = f"{kind}:{value}"
        return ("https://inspirehep.net/api/literature?" +
                urllib.parse.urlencode({"q": q, "size": "2", "fields": INSPIRE_FIELDS}))
    if source == "arxiv":
        return "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"id_list": value, "max_results": "1"})
    if source == "ads":
        q = f'{kind}:"{value}"'
        return ("https://api.adsabs.harvard.edu/v1/search/query?" +
                urllib.parse.urlencode({"q": q, "fl": ADS_FIELDS, "rows": "2"}))
    raise ValueError(source)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class LiveTransport:
    """urllib with per-host spacing; optionally writes each response to a record directory."""

    name = "live"

    def __init__(self, timeout: float = 20.0, record_dir: Path | None = None):
        self.timeout = timeout
        self.record_dir = record_dir
        self._last: dict[str, float] = {}

    def fetch(self, url: str, headers: dict, source: str) -> dict:
        host = urllib.parse.urlsplit(url).hostname or ""
        wait = MIN_INTERVAL_S.get(host, 0.0) - (time.monotonic() - self._last.get(host, -1e9))
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
        recorded_at = utc_now()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 (fixed https endpoints)
                status, hdrs, body = resp.status, resp.headers, resp.read(MAX_BYTES)
        except urllib.error.HTTPError as exc:
            status, hdrs = exc.code, exc.headers
            try:
                body = exc.read(MAX_BYTES)
            except OSError:
                body = b""
        finally:
            self._last[host] = time.monotonic()
        ex = {"source": source, "url": url, "recorded_at": recorded_at, "http_status": status,
              "headers": {k: hdrs.get(k) for k in KEEP_HEADERS if hdrs is not None and hdrs.get(k) is not None},
              "body": body.decode("utf-8", errors="replace")}
        if self.record_dir is not None:
            self.record_dir.mkdir(parents=True, exist_ok=True)
            name = f"{source}-{hashlib.sha256(url.encode()).hexdigest()[:12]}.json"
            (self.record_dir / name).write_text(json.dumps(ex, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return ex


class ReplayTransport:
    """Answers from recorded exchanges (one JSON object per file, keyed by its url)."""

    name = "replay"

    def __init__(self, *paths: Path):
        self.exchanges: dict[str, dict] = {}
        files = [f for p in map(Path, paths) for f in (sorted(p.glob("*.json")) if p.is_dir() else [p])]
        if not files or not all(f.is_file() for f in files):
            raise FileNotFoundError(f"no recorded responses (*.json) in {', '.join(map(str, paths))}")
        for f in files:
            ex = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(ex, dict) and isinstance(ex.get("url"), str):
                self.exchanges[ex["url"]] = ex

    def fetch(self, url: str, headers: dict, source: str) -> dict | None:
        return self.exchanges.get(url)


def _authors(names: list[str]) -> dict:
    return {"authors": names[:MAX_AUTHORS], "author_count": len(names)}


def parse_inspire(body: str, ident: dict) -> tuple[str, dict, list[str]]:
    doc = json.loads(body)
    if "hits" in doc:
        hits = doc["hits"].get("hits", [])
        total = doc["hits"].get("total", len(hits))
        if total == 0 or not hits:
            return "not-found", {}, []
        if total > 1:
            ids = [h.get("metadata", {}).get("control_number") for h in hits]
            return "ambiguous", {"candidates_inspire_recid": ids}, [f"{total} INSPIRE records match {ident['input']}"]
        md = hits[0].get("metadata", {})
    else:
        md = doc.get("metadata", {})
        if not md:
            return "not-found", {}, []
    eprints = md.get("arxiv_eprints") or []
    pub = next((p for p in md.get("publication_info") or [] if p.get("material") != "erratum"), {})
    journal = " ".join(str(pub[k]) for k in ("journal_title", "journal_volume", "artid", "year") if pub.get(k))
    out = {"title": (md.get("titles") or [{}])[0].get("title"),
           **_authors([a.get("full_name") for a in md.get("authors") or [] if a.get("full_name")]),
           "collaborations": [c.get("value") for c in md.get("collaborations") or [] if c.get("value")],
           "doi": [d.get("value") for d in md.get("dois") or [] if d.get("value")],
           "arxiv_id": eprints[0].get("value") if eprints else None,
           "inspire_recid": md.get("control_number"),
           "texkeys": md.get("texkeys") or [],
           "journal_ref": journal or None}
    notes = []
    if not eprints:
        notes.append("the INSPIRE record lists no arXiv e-print")
    if ident["kind"] == "arxiv" and ident["version"]:
        notes.append("INSPIRE does not record arXiv versions; use the arXiv result for the version check")
    return "found", out, notes


def parse_arxiv(body: str, ident: dict) -> tuple[str, dict, list[str]]:
    root = ET.fromstring(body)
    entries = root.findall("a:entry", ATOM)
    if not entries:
        return "not-found", {}, []
    e = entries[0]
    eid = (e.findtext("a:id", "", ATOM) or "").strip()
    if "/api/errors" in eid:
        msg = (e.findtext("a:summary", "", ATOM) or "").strip()
        return ("not-found" if "does not exist" in msg.lower() else "error"), {}, [f"arXiv API error: {msg}"]
    m = re.search(r"abs/(.+?)(v\d+)?$", eid)
    if not m:
        return "error", {}, [f"unexpected arXiv entry id {eid!r}"]
    base, latest = m.group(1), m.group(2)
    if base != ident["value"]:
        return "error", {}, [f"arXiv returned {base}, not {ident['value']}"]
    out = {"title": " ".join((e.findtext("a:title", "", ATOM) or "").split()),
           **_authors([(a.findtext("a:name", "", ATOM) or "").strip() for a in e.findall("a:author", ATOM)]),
           "arxiv_id": base, "latest_version": latest,
           "published": e.findtext("a:published", None, ATOM), "updated": e.findtext("a:updated", None, ATOM),
           "doi": [d for d in [e.findtext("arxiv:doi", None, ATOM)] if d],
           "journal_ref": e.findtext("arxiv:journal_ref", None, ATOM),
           "primary_category": (e.find("arxiv:primary_category", ATOM).get("term")
                                if e.find("arxiv:primary_category", ATOM) is not None else None)}
    return "found", out, []


def parse_ads(body: str, ident: dict) -> tuple[str, dict, list[str]]:
    docs = json.loads(body).get("response", {}).get("docs", [])
    if not docs:
        return "not-found", {}, []
    if len(docs) > 1:
        return "ambiguous", {"candidates_bibcode": [d.get("bibcode") for d in docs]}, \
            [f"{len(docs)} ADS records match {ident['input']}"]
    d = docs[0]
    out = {"title": (d.get("title") or [None])[0], **_authors(d.get("author") or []), "bibcode": d.get("bibcode"),
           "doi": d.get("doi") or [], "journal_ref": d.get("pub"), "year": d.get("year")}
    return "found", out, []


PARSERS = {"inspire": parse_inspire, "arxiv": parse_arxiv, "ads": parse_ads}


def version_check(ident: dict, meta: dict) -> dict | None:
    if ident["kind"] != "arxiv" or not meta.get("latest_version"):
        return None
    latest, req = meta["latest_version"], ident["version"]
    if req is None:
        return {"requested": None, "latest": latest, "match": None,
                "note": "no version requested: the identifier resolves to the latest version"}
    vc = {"requested": req, "latest": latest, "match": req == latest}
    if int(req[1:]) > int(latest[1:]):
        vc["note"] = f"requested {req} does not exist; the latest is {latest}"
    elif req != latest:
        vc["note"] = f"cites {req}; arXiv now has {latest}: check what changed before citing"
    return vc


def ads_token() -> str | None:
    for name in TOKEN_ENV:
        val = os.environ.get(name, "").strip()
        if val:
            return val
    return None


def lookup_source(source: str, ident: dict, transport) -> dict:
    res = {"source": source, "status": "error", "read_level": "not-verified", "source_url": None,
           "retrieved_at": None, "transport": transport.name, "http_status": None, "metadata": {}, "notes": []}
    if ident["kind"] not in SUPPORTS[source]:
        res.update(status="unsupported", notes=[f"{source} cannot resolve a {ident['kind']} identifier"])
        return res
    url = request_url(source, ident)
    res["source_url"] = url
    headers = {}
    if source == "ads":
        token = ads_token() if transport.name == "live" else "replay"
        if not token:
            res.update(status="not-verified",
                       notes=[f"no ADS token in {' or '.join(TOKEN_ENV)}: no ADS request made"])
            return res
        if transport.name == "live":
            headers["Authorization"] = f"Bearer {token}"
    try:
        ex = transport.fetch(url, headers, source)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        res["notes"].append(f"request failed: {type(exc).__name__}: {reason}")
        res["retrieved_at"] = utc_now()
        return res
    if ex is None:
        res["notes"].append("no recorded response for this URL")
        return res
    res["retrieved_at"] = ex.get("recorded_at")
    res["http_status"] = code = ex.get("http_status")
    if ex.get("synthetic"):
        res["notes"].append("replayed from a constructed response, not a recorded one: " + ex.get("note", ""))
    if code == 429:
        ra = (ex.get("headers") or {}).get("retry-after")
        res.update(status="rate-limited", retry_after=ra)
        res["notes"].append(f"HTTP 429 from {source}; wait {ra or 'a few'} s before retrying (not retried)")
        return res
    if code == 404:
        res["status"] = "not-found"
        return res
    if code in (401, 403) and source == "ads":
        res["status"] = "not-verified"
        res["notes"].append(f"ADS refused the token (HTTP {code}); the token is not shown")
        return res
    if code != 200:
        res["notes"].append(f"HTTP {code} from {source}")
        return res
    try:
        status, meta, notes = PARSERS[source](ex.get("body", ""), ident)
    except (ValueError, ET.ParseError, AttributeError, TypeError, KeyError, IndexError) as exc:
        res["notes"].append(f"unreadable {source} response: {type(exc).__name__}: {exc}")
        return res
    res.update(status=status, metadata=meta)
    res["notes"].extend(notes)
    if status == "found":
        res["read_level"] = "metadata-only"
        vc = version_check(ident, meta)
        if vc:
            res["version_check"] = vc
    return res


def lookup(identifier: str, sources=None, transport=None) -> dict:
    """Look an identifier up; returns the record (see the module docstring). Raises InvalidIdentifier."""
    ident = parse_identifier(identifier)
    transport = transport or LiveTransport()
    wanted = list(sources) if sources else [s for s in SOURCES if ident["kind"] in SUPPORTS[s]]
    results = [lookup_source(s, ident, transport) for s in wanted]
    statuses = [r["status"] for r in results]
    mismatch = any(r.get("version_check", {}).get("match") is False for r in results)
    if "found" in statuses:
        outcome, code = ("incomplete", 3) if mismatch else ("pass", 0)
    elif "not-found" in statuses:
        outcome, code = "fail", 1
    else:
        outcome, code = "incomplete", 3
    return {"tool": "literature_lookup", "adapter_version": ADAPTER_VERSION, "record_version": RECORD_VERSION,
            "identifier": ident, "outcome": outcome, "exit_code": code, "version_mismatch": mismatch,
            "results": results}


def as_text(rec: dict) -> str:
    lines = [f"{rec['identifier']['input']}: {rec['outcome']}"]
    for r in rec["results"]:
        md = r["metadata"]
        lines.append(f"- {r['source']}: {r['status']} ({r['read_level']}) {r['source_url'] or ''} "
                     f"retrieved {r['retrieved_at'] or '-'} [{r['transport']}]")
        if md.get("title"):
            lines.append(f"  title: {md['title']}")
        vc = r.get("version_check")
        if vc:
            lines.append(f"  version: requested {vc['requested']}, latest {vc['latest']}")
        lines.extend(f"  note: {n}" for n in r["notes"])
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="literature_lookup.py", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("identifier")
    ap.add_argument("--source", action="append", choices=SOURCES, help="repeatable; default: every applicable one")
    io = ap.add_mutually_exclusive_group()
    io.add_argument("--replay", type=Path, help="answer from recorded responses in this directory (no network)")
    io.add_argument("--record", type=Path, help="write each live response to this directory")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--format", choices=("json", "text"), default="json")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        transport = ReplayTransport(args.replay) if args.replay else LiveTransport(args.timeout, args.record)
        rec = lookup(args.identifier, args.source, transport)
    except InvalidIdentifier as exc:
        print(json.dumps({"tool": "literature_lookup", "outcome": "input-error", "exit_code": 2, "error": str(exc)}))
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(json.dumps({"tool": "literature_lookup", "outcome": "input-error", "exit_code": 2,
                          "error": f"{type(exc).__name__}: {exc}"}))
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(rec, indent=1, ensure_ascii=False) if args.format == "json" else as_text(rec))
    return rec["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
