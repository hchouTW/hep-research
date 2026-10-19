#!/usr/bin/env python3
"""Check every citation of a draft against literature records and evidence ledgers: never a citation from memory.

Usage: python3 check_citations.py DRAFT [DRAFT ...] [--record LITERATURE.json ...] [--ledger SOURCES.json ...]
                                  [--format json|markdown] [--out REPORT]

DRAFT files are read by extension: `.tex` (\\cite-family keys; % comments skipped), `.bib` (entry keys with their doi,
eprint and INSPIRE fields), `.md` (pandoc `[@key]` citations and bare `arXiv:` or DOI identifiers). A cited key is
resolved to its `.bib` entry when one of the DRAFT files defines it. --record is a hep-citations `literature-record`
artifact (or a bare record written before contracts 2.13.0); --ledger is a profile evidence ledger's `sources.json`.
Each citation is matched on stable identifiers first (DOI, arXiv id without version, INSPIRE record id), then on the
citation key a record stores; titles are never compared. A citation found nowhere is reported `not-verified`
(unresolved): hand it to hep-citations or mark it in the text, never fill it from memory. A citation found only at
read level not-verified, not-opened or metadata-only is a warning (the record shows the paper exists, not what it
says), and so is an arXiv version that differs from the recorded one.

One JSON report (report_version 1.0.0; markdown with --format markdown) on stdout or --out (never an input path).
Exit codes: 0 every citation found; 3 a citation not verified (incomplete); 2 invalid invocation or unreadable input.
Read-only; no lookup is performed (online verification is hep-citations's, through the host's tools).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.dont_write_bytecode = True  # importing plugin packages leaves no __pycache__ (F-10)
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from contracts import audit_report as R  # noqa: E402
from core.evidence.identifiers import identifiers_of, keys_of, normalize_arxiv, normalize_doi  # noqa: E402

TOOL = "check_citations"
CHECKS = ("extract", "match", "read-levels", "versions")
CITE_RE = re.compile(r"\\(?:no)?cite[a-zA-Z]*\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}")
PANDOC_RE = re.compile(r"\[[^\]]*@[^\]]*\]")
PANDOC_KEY_RE = re.compile(r"-?@([\w:.#$%&\-+?<>~/]+)")
ARXIV_TEXT_RE = re.compile(r"\barXiv:\s*((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)", re.I)
DOI_TEXT_RE = re.compile(r"(?:\bdoi:\s*|https?://(?:dx\.)?doi\.org/)(10\.\d{4,9}/[^\s\]\)>,;\"'}]+)", re.I)
BIB_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.S)
BIB_FIELD_RE = re.compile(r"(\w+)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|\"([^\"]*)\"|(\d+))", re.S)
WEAK_LEVELS = ("not-verified", "not-opened", "metadata-only")
NOTE = ("offline check: citations are matched to records and ledgers by identifier, then by stored key; nothing was "
        "looked up, and a match says the citation has a record, not that the cited text supports the claim")


def strip_tex_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def parse_bib(text: str) -> dict:
    """{key: {doi, arxiv, arxiv_version, inspire}} of the entries of a .bib text (string, comment, preamble skipped)."""
    out = {}
    starts = list(BIB_ENTRY_RE.finditer(text))
    for i, m in enumerate(starts):
        if m.group(1).lower() in ("string", "comment", "preamble"):
            continue
        body = text[m.end():starts[i + 1].start() if i + 1 < len(starts) else len(text)]
        fields = {f.group(1).lower(): (f.group(2) or f.group(3) or f.group(4) or "").strip() for f in BIB_FIELD_RE.finditer(body)}
        arx = normalize_arxiv(fields.get("eprint", "")) if fields.get("archiveprefix", "arxiv").lower() == "arxiv" else None
        out[m.group(2)] = {"doi": normalize_doi(fields.get("doi")), "arxiv": arx[0] if arx else None,
                           "arxiv_version": arx[1] if arx else None,
                           "inspire": fields.get("inspire") or None}
    return out


def extract(paths: list[Path]) -> tuple[list[dict], dict]:
    """(citations, bib) from the drafts: one citation per cited key or bare identifier, with every location."""
    texts = {p: p.read_text(encoding="utf-8") for p in paths}
    bib: dict = {}
    for p, t in texts.items():
        if p.suffix.lower() == ".bib":
            bib.update(parse_bib(t))
    found: dict[str, dict] = {}

    def add(kind: str, value: str, where: str, ids: dict | None = None):
        c = found.setdefault(f"{kind}:{value}", {"kind": kind, "value": value, "locations": [], "identifiers": ids or {}})
        if where not in c["locations"]:
            c["locations"].append(where)
    for p, t in texts.items():
        suffix = p.suffix.lower()
        if suffix == ".tex":
            for n, line in enumerate(strip_tex_comments(t).splitlines(), 1):
                for m in CITE_RE.finditer(line):
                    for key in (k.strip() for k in m.group(1).split(",")):
                        if key:
                            add("key", key, f"{p.name}:{n}", bib.get(key))
        elif suffix == ".md":
            for n, line in enumerate(t.splitlines(), 1):
                for block in PANDOC_RE.findall(line):
                    for key in PANDOC_KEY_RE.findall(block):
                        add("key", key.rstrip(".,;"), f"{p.name}:{n}", bib.get(key.rstrip(".,;")))
                for m in ARXIV_TEXT_RE.finditer(line):
                    a = normalize_arxiv(m.group(1))
                    if a:
                        add("arxiv", m.group(1), f"{p.name}:{n}", {"arxiv": a[0], "arxiv_version": a[1]})
                for m in DOI_TEXT_RE.finditer(line):
                    add("doi", m.group(1).rstrip("."), f"{p.name}:{n}", {"doi": normalize_doi(m.group(1).rstrip("."))})
        elif suffix != ".bib":  # a .bib only resolves keys; an uncited entry is check_manuscript.py's finding

            raise ValueError(f"{p}: unsupported draft type {p.suffix!r} (use .tex, .bib or .md)")
    return list(found.values()), bib


def load_sources(records: list[Path], ledgers: list[Path]) -> list[dict]:
    """Every source of the records and ledgers with its origin, read level, date and identifiers."""
    out = []
    for path in records:
        doc = json.loads(path.read_text(encoding="utf-8"))
        rec = doc.get("extension") if isinstance(doc, dict) and doc.get("artifact_type") == "literature-record" else doc
        if not isinstance(rec, dict) or rec.get("record_version") != "1.0.0" or not isinstance(rec.get("sources"), dict):
            raise ValueError(f"{path} is not a literature record (a literature-record artifact or record_version 1.0.0)")
        for sid, s in rec["sources"].items():
            ids = s.get("identifiers") if isinstance(s.get("identifiers"), dict) else {}
            if "dois" in ids or "arxiv_ids" in ids:  # still in ledger form
                ids = identifiers_of(s, top_level_inspire=True)
            out.append({"origin": str(path), "id": sid, "level": s.get("verification_level"),
                        "date": s.get("verification_date"), "key": s.get("citation_key"),
                        "ids": {k: ids.get(k) for k in ("doi", "arxiv", "arxiv_version", "inspire")}})
    for path in ledgers:
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows = doc.get("sources") if isinstance(doc, dict) else doc
        if not isinstance(rows, list):
            raise ValueError(f"{path} is not an evidence ledger (a JSON array of sources, or an object with 'sources')")
        for s in rows:
            if isinstance(s, dict) and isinstance(s.get("id"), str):
                out.append({"origin": str(path), "id": s["id"], "level": s.get("verification_level"),
                            "date": s.get("verification_date") or s.get("access_date"), "key": s.get("citation_key"),
                            "ids": identifiers_of(s, top_level_inspire=True)})
    return out


def match(citation: dict, sources: list[dict]) -> tuple[dict | None, str]:
    ids = {k: v for k, v in (citation.get("identifiers") or {}).items() if v}
    keys = keys_of(ids)
    for s in sources:
        if keys & keys_of(s["ids"]):
            return s, "identifier"
    if citation["kind"] == "key":
        for s in sources:
            if s.get("key") and s["key"] == citation["value"]:
                return s, "citation key"
    return None, ""


def check(drafts: list[Path], records: list[Path], ledgers: list[Path]) -> dict:
    citations, bib = extract(drafts)
    sources = load_sources(records, ledgers)
    findings, rows = [], []
    for c in sorted(citations, key=lambda c: (c["locations"][0], c["value"])):
        where = ", ".join(c["locations"])
        s, how = match(c, sources)
        row = {"citation": c["value"], "kind": c["kind"], "locations": c["locations"],
               "identifiers": {k: v for k, v in (c.get("identifiers") or {}).items() if v}}
        if s is None:
            row["status"] = "not-verified"
            findings.append(R.finding("citation.not_verified", "unresolved", where,
                                      f"{c['value']} is in no literature record or evidence ledger given",
                                      "hand it to hep-citations for a record, or mark it unverified in the text ([CITATION NEEDED]); never fill it from memory",
                                      source=TOOL))
        else:
            row.update(status="found", matched_by=how, source_id=s["id"], origin=s["origin"], read_level=s["level"],
                       verification_date=s["date"])
            if s["level"] in WEAK_LEVELS:
                findings.append(R.finding("citation.read_level_low", "warning", where,
                                          f"{c['value']} is recorded as {s['id']} at read level {s['level']}: it shows the paper exists, not what it says",
                                          "read the cited passage (page or full-text) before it supports a claim", source=TOOL, source_id=s["id"]))
            cv, rv = row["identifiers"].get("arxiv_version"), s["ids"].get("arxiv_version")
            if cv and rv and cv != rv:
                findings.append(R.finding("citation.version_differs", "warning", where,
                                          f"{c['value']} cites arXiv {cv}; the record holds {rv} ({s['id']})",
                                          "cite the version that was read, or reread the cited passage in the recorded version",
                                          source=TOOL, source_id=s["id"]))
        rows.append(row)
    notes = [] if citations else [{"code": "citation.none_found", "message": "the drafts cite nothing this tool recognizes"}]
    counts = {"citations": len(rows), "found": sum(r["status"] == "found" for r in rows),
              "not_verified": sum(r["status"] == "not-verified" for r in rows), "sources_given": len(sources)}
    return R.assemble(TOOL, {"drafts": [str(p) for p in drafts], "records": [str(p) for p in records],
                             "ledgers": [str(p) for p in ledgers], "bib_entries": len(bib)}, findings,
                      checks_run=list(CHECKS),
                      checks_not_run=[{"check": "online-lookup", "reason": "offline; lookups are hep-citations's", "required": False},
                                      {"check": "claim-support", "reason": "a record says a source exists and how far it was read; "
                                       "whether its text supports the claim is a reading task", "required": False}],
                      notes=notes, citations=rows, counts_citations=counts, note=NOTE)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_citations.py", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("drafts", type=Path, nargs="*", help="draft files: .tex, .bib, .md")
    ap.add_argument("--record", type=Path, action="append", default=[], help="literature-record artifact (repeatable)")
    ap.add_argument("--ledger", type=Path, action="append", default=[], help="evidence-ledger sources.json (repeatable)")
    ap.add_argument("--format", choices=("json", "markdown"), default="json")
    ap.add_argument("--out", type=Path, help="write the report here instead of stdout (never an input path)")
    try:
        args = ap.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return 2 if exc.code else 0

    def fail(msg: str) -> int:
        print(json.dumps(R.input_error_report(TOOL, msg, CHECKS), indent=1))
        print(f"error: {msg}", file=sys.stderr)
        return 2
    if not args.drafts:
        return fail("name at least one draft file (.tex, .bib or .md)")
    for p in args.drafts + args.record + args.ledger:
        if not p.is_file():
            return fail(f"{p} is not a readable file")
    try:
        rep = check(args.drafts, args.record, args.ledger)
    except (OSError, UnicodeDecodeError) as exc:
        return fail(f"cannot read an input: {exc}")
    except ValueError as exc:
        return fail(str(exc))
    return R.emit(rep, args.format, args.out, args.drafts + args.record + args.ledger)


if __name__ == "__main__":
    sys.exit(main())
