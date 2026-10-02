#!/usr/bin/env python3
"""Maintain a manifest of AMS Collaboration papers and fetch them into a LOCAL cache.

Purpose: let a maintainer read the primary papers behind the evidence ledger without
committing PDFs (licenses are per paper and the files are large). The manifest
`evidence/papers_manifest.json` holds metadata only: DOI, INSPIRE record, journal
reference, ledger source IDs, and an ordered list of candidate PDF URLs. PDFs, opt-in APS Supplemental Material files and extracted text go to a cache directory OUTSIDE the repository
(`$AMS_PAPERS_CACHE`, else `~/.cache/ams-analysis/papers`) with a SHA-256 index.

Rules this script follows: it identifies itself, waits between requests, retries a transient error (HTTP 5xx, 406, network failure) once after a pause, never sends
credentials, and never works around a bot-verification page, a login or an HTTP
401/403/429: such a paper is recorded as `blocked` and left for a human to download
and register with `adopt`. A cached arXiv or repository copy is labeled as such (the
index records `version`: `publisher`, `arxiv` or `repository`); reading a preprint is
not reading the published paper, and the ledger's verification level must say which
was read. A cached file raises no claim by itself: claims still need `evidence/claims.json`
entries read at their stated level (see modules/source-policy.md).

Usage (from the skill directory; every command has --help):
  python3 profiles/experiments/ams-02/scripts/fetch_papers.py check-manifest             # offline: schema and ledger cross-check
  python3 profiles/experiments/ams-02/scripts/fetch_papers.py refresh-manifest           # network: rebuild the manifest (INSPIRE-HEP, OpenAlex)
  python3 profiles/experiments/ams-02/scripts/fetch_papers.py status [--cache DIR]       # what is cached, blocked or missing
  python3 profiles/experiments/ams-02/scripts/fetch_papers.py fetch --keys KEY [KEY ...] | --all [--supplements] [--dry-run]
  python3 profiles/experiments/ams-02/scripts/fetch_papers.py adopt FILE_OR_DIR ...      # register PDFs you downloaded yourself
  python3 profiles/experiments/ams-02/scripts/fetch_papers.py verify                     # re-hash the cache against its index
  python3 profiles/experiments/ams-02/scripts/fetch_papers.py extract [--keys KEY ...]   # pdftotext -layout next to the PDFs (needs pdftotext)
Exit codes: 0 ok; 1 completed with blocked or failed items, or a failed check/verify;
2 usage error, unreadable manifest/cache, or network refused for the whole refresh.
Standard library only (pdftotext is an optional external tool used only by `extract`).
Importable: `check_manifest`, `build_entry`, `Fetcher`, `Cache` (the HTTP layer is injectable for tests).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
MANIFEST = ROOT / "evidence" / "papers_manifest.json"
SOURCES = ROOT / "evidence" / "sources.json"
USER_AGENT = "ams-analysis-paper-fetch/1 (maintainer cache; no credentials; honors blocks)"
INSPIRE_QUERY = "collaboration:AMS and document_type:article"
SUPP_EXT = ("pdf", "zip", "txt", "csv", "dat", "xlsx")
MAX_SUPP_FILES = 20  # per paper, a guard against a runaway listing
KEY_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
BOT_MARKERS = ("just a moment", "making sure you", "human verification", "cf-chl", "captcha", "awswaf",
               "access denied", "enable javascript", "are you a robot", "not a bot")
BLOCKED_STATUS = {401, 403, 429}
RETRY_STATUS = {0, 406, 500, 502, 503, 504}  # transient only; a block (BLOCKED_STATUS) or a 404 is never retried
REQUIRED = ("key", "doi", "inspire_id", "title", "journal_ref", "date", "generation", "publisher",
            "source_ids", "pdf_candidates")
CANDIDATE_KINDS = {"publisher": "publisher", "arxiv": "arxiv", "repository": "repository"}


# ---------------------------------------------------------------- manifest
def doi_key(doi: str | None, inspire_id) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", doi) if doi else f"inspire-{inspire_id}"


def publisher_of(doi: str | None) -> str:
    if not doi:
        return "unknown"
    return {"10.1103": "aps", "10.1016": "elsevier", "10.1088": "iop", "10.1109": "ieee",
            "10.3103": "springer"}.get(doi.split("/")[0], "other")


AMS02_BEFORE_2011 = {"10.1109/TNS.2005.862781"}  # AMS-02 hardware paper, titled like the AMS-01 era ones


def generation_of(date: str, title: str, doi: str | None = None) -> str:
    """Heuristic tag (AMS-01 flew in 1998; AMS-02 on the ISS since 2011); a maintainer may edit the manifest."""
    year = int(date[:4]) if date[:4].isdigit() else 0
    if "AMS-01" in title and "AMS-02" not in title:
        return "ams-01-or-earlier"
    if year >= 2011 or "AMS-02" in title or (doi or "") in AMS02_BEFORE_2011:
        return "ams-02"
    return "ams-01-or-earlier"


def journal_ref(pi: dict) -> str:
    if not pi.get("journal_title"):
        return ""
    where = pi.get("artid") or pi.get("page_start") or ""
    return f"{pi['journal_title']} {pi.get('journal_volume', '')} ({pi.get('year', '')}) {where}".replace("  ", " ").strip()


def build_entry(hit: dict, openalex: dict | None, ledger_by_doi: dict) -> dict:
    """One manifest row from an INSPIRE literature hit and an optional OpenAlex work."""
    m = hit["metadata"]
    doi = (m.get("dois") or [{}])[0].get("value")
    pi = (m.get("publication_info") or [{}])[0]
    date = str(m.get("earliest_date", ""))
    title = m["titles"][0]["title"]
    candidates: list[dict] = []
    if doi and doi.startswith("10.1103/") and pi.get("journal_title") == "Phys.Rev.Lett.":
        candidates.append({"url": f"https://journals.aps.org/prl/pdf/{doi}", "kind": "publisher"})
    seen = {c["url"] for c in candidates}
    for loc in (openalex or {}).get("locations", []) or []:
        url = re.sub(r"^http://", "https://", loc.get("pdf_url") or "")
        if url.startswith("https://") and url not in seen:
            host = urllib.parse.urlparse(url).hostname or ""
            kind = "publisher" if host.endswith("aps.org") else ("arxiv" if host.endswith("arxiv.org") else "repository")
            candidates.append({"url": url, "kind": kind})
            seen.add(url)
    for ax in m.get("arxiv_eprints") or []:
        url = f"https://arxiv.org/pdf/{ax['value']}"
        if url not in seen:
            candidates.append({"url": url, "kind": "arxiv"})
            seen.add(url)
    oa = (openalex or {}).get("open_access") or {}
    supp = [f"https://journals.aps.org/prl/supplemental/{doi}"] if candidates and candidates[0]["url"].startswith(
        "https://journals.aps.org/prl/pdf/") else []
    return {
        "key": doi_key(doi, m.get("control_number")),
        "doi": doi,
        "inspire_id": m.get("control_number"),
        "title": re.sub(r"\s+", " ", title).strip(),
        "journal_ref": journal_ref(pi),
        "date": date,
        "generation": generation_of(date, title, doi),
        "publisher": publisher_of(doi),
        "oa_status": oa.get("oa_status"),
        "source_ids": sorted(ledger_by_doi.get((doi or "").lower(), [])),
        "arxiv": [a["value"] for a in m.get("arxiv_eprints") or []],
        "pdf_candidates": candidates,
        "supplement_pages": supp,
    }


def ledger_dois(sources_path: Path = SOURCES) -> dict:
    data = json.loads(sources_path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data["sources"]
    out: dict = {}
    for s in rows:
        for d in s.get("dois") or []:
            out.setdefault(d.lower(), []).append(s["id"])
    return out


def check_manifest(manifest: dict, ledger: dict, source_ids: set | None = None) -> list[str]:
    """Return a list of problems (empty means the manifest is consistent with its schema and the ledger)."""
    problems: list[str] = []
    papers = manifest.get("papers")
    if not isinstance(papers, list) or not papers:
        return ["manifest has no 'papers' list"]
    keys, dois = set(), set()
    for p in papers:
        k = p.get("key", "?")
        for f in REQUIRED:
            if f not in p:
                problems.append(f"{k}: missing field {f}")
        if not KEY_RE.match(str(p.get("key", ""))):
            problems.append(f"{k}: key is not a safe file name")
        if k in keys:
            problems.append(f"{k}: duplicate key")
        keys.add(k)
        d = (p.get("doi") or "").lower()
        if d:
            if d in dois:
                problems.append(f"{k}: duplicate doi {d}")
            dois.add(d)
        for c in p.get("pdf_candidates", []):
            if not str(c.get("url", "")).startswith("https://") or c.get("kind") not in CANDIDATE_KINDS:
                problems.append(f"{k}: bad candidate {c}")
        for u in p.get("supplement_pages", []):
            if not str(u).startswith("https://journals.aps.org/prl/supplemental/"):
                problems.append(f"{k}: bad supplement page {u}")
        want = sorted(ledger.get(d, []))
        if sorted(p.get("source_ids", [])) != want:
            problems.append(f"{k}: source_ids {p.get('source_ids')} differ from the ledger rows with this DOI {want}")
        for sid in p.get("source_ids", []):
            if source_ids is not None and sid not in source_ids:
                problems.append(f"{k}: unknown source id {sid}")
    for d, ids in ledger.items():
        if d.startswith("10.1103/physrevlett.") and d not in dois:
            problems.append(f"ledger {ids} cites AMS-era PRL doi {d} that is not in the manifest (refresh-manifest)")
    return problems


# ---------------------------------------------------------------- HTTP
@dataclass
class Response:
    status: int
    content_type: str
    data: bytes
    url: str


class Http:
    """Plain urllib GET with a size cap, an identifying User-Agent and no credentials."""

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout

    def get(self, url: str, max_bytes: int) -> Response:
        if not url.startswith("https://"):
            raise ValueError(f"refusing non-https url {url}")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = r.read(max_bytes + 1)
                return Response(r.status, r.headers.get("Content-Type", ""), data, r.geturl())
        except urllib.error.HTTPError as e:
            return Response(e.code, e.headers.get("Content-Type", "") if e.headers else "", b"", url)
        except (urllib.error.URLError, TimeoutError, OSError):
            return Response(0, "", b"", url)  # network failure: status 0, reported per item


def classify(resp: Response, max_bytes: int) -> tuple[str, str]:
    """Return (outcome, detail): ok | blocked | too-large | not-a-pdf | http-error."""
    if resp.status in BLOCKED_STATUS:
        return "blocked", f"HTTP {resp.status}"
    if resp.status >= 400 or resp.status == 0:
        return "http-error", f"HTTP {resp.status}"
    if len(resp.data) > max_bytes:
        return "too-large", f"more than {max_bytes // (1 << 20)} MB"
    if resp.data[:5] == b"%PDF-":
        return "ok", ""
    head = resp.data[:6000].decode("utf-8", "replace").lower()
    if any(mk in head for mk in BOT_MARKERS):
        return "blocked", "bot-verification page (not bypassed)"
    return "not-a-pdf", f"content-type {resp.content_type or '?'} is not a PDF"


# ---------------------------------------------------------------- cache
def default_cache() -> Path:
    return Path(os.environ.get("AMS_PAPERS_CACHE") or Path.home() / ".cache" / "ams-analysis" / "papers")


def safe_name(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", Path(urllib.parse.unquote(name)).name).lstrip(".")
    return base[:150] or "file"


class Cache:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.index_path = self.root / "index.json"
        self.index = {"schema": "1", "files": {}, "blocked": {}}
        if self.index_path.exists():
            self.index = json.loads(self.index_path.read_text(encoding="utf-8"))
            self.index.setdefault("files", {})
            self.index.setdefault("blocked", {})

    def save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.index_path)

    def rel(self, kind: str, key: str, name: str) -> str:
        return f"pdf/{key}.pdf" if kind == "article" else f"supp/{key}/{safe_name(name)}"

    def has(self, rel: str) -> bool:
        return rel in self.index["files"] and (self.root / rel).exists()

    def put(self, rel: str, data: bytes, **meta):
        path = (self.root / rel).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError(f"path escapes the cache: {rel}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.index["files"][rel] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                                    "retrieved": dt.date.today().isoformat(), **meta}

    def article(self, key: str) -> dict | None:
        rel = f"pdf/{key}.pdf"
        return {"file": rel, **self.index["files"][rel]} if self.has(rel) else None


class Fetcher:
    def __init__(self, cache: Cache, http=None, delay: float = 1.0, max_mb: int = 400, sleep=time.sleep, log=print,
                 retries: int = 1, retry_wait: float = 5.0):
        self.cache, self.http = cache, http or Http()
        self.delay, self.max_bytes, self.sleep, self.log = delay, max_mb << 20, sleep, log
        self.retries, self.retry_wait = max(0, retries), retry_wait
        self._last = 0.0

    def _once(self, url: str) -> Response:
        wait = self.delay - (time.monotonic() - self._last)
        if self._last and wait > 0:
            self.sleep(wait)
        try:
            return self.http.get(url, self.max_bytes)
        finally:
            self._last = time.monotonic()

    def _get(self, url: str) -> Response:
        """GET with the polite delay; retries only transient errors (RETRY_STATUS), never a block."""
        resp = self._once(url)
        for attempt in range(self.retries):
            if resp.status not in RETRY_STATUS:
                break
            self.log(f"  transient HTTP {resp.status} for {url}; retrying in {self.retry_wait:g} s ({attempt + 1}/{self.retries})")
            self.sleep(self.retry_wait)
            resp = self._once(url)
        return resp

    def fetch_article(self, p: dict, dry_run: bool = False) -> str:
        key = p["key"]
        if self.cache.article(key):
            return "cached"
        if dry_run:
            return "would-fetch"
        outcome = "none"
        for cand in p["pdf_candidates"]:
            resp = self._get(cand["url"])
            outcome, detail = classify(resp, self.max_bytes)
            if outcome == "ok":
                version = {"publisher": "publisher", "arxiv": "arxiv", "repository": "repository"}[cand["kind"]]
                self.cache.put(f"pdf/{key}.pdf", resp.data, url=cand["url"], version=version, kind="article",
                               content_type=resp.content_type)
                self.cache.index["blocked"].pop(key, None)
                return f"fetched ({version})"
            self.log(f"  {key}: {cand['kind']} {cand['url']} -> {outcome} ({detail})")
            self.cache.index["blocked"][key] = {"url": cand["url"], "reason": f"{outcome}: {detail}",
                                                "date": dt.date.today().isoformat()}
        return "blocked" if outcome == "blocked" else ("failed" if p["pdf_candidates"] else "no-candidate")

    def supplement_links(self, page_url: str) -> list[str]:
        """Supplement file links on an APS supplemental-material page (only links under /prl/supplemental/)."""
        resp = self._get(page_url)
        if resp.status >= 400 or resp.status == 0:
            return []
        html = resp.data.decode("utf-8", "replace")
        found = re.findall(r'href="(/prl/supplemental/[^"#?]+\.(?:%s))"' % "|".join(SUPP_EXT), html)
        urls = {urllib.parse.urljoin("https://journals.aps.org", h) for h in found if ".." not in h}
        return sorted(u for u in urls if urllib.parse.urlparse(u).path.startswith("/prl/supplemental/"))[:MAX_SUPP_FILES]

    def fetch_supplements(self, p: dict, dry_run: bool = False) -> list[str]:
        out = []
        for page in p.get("supplement_pages", []):
            if dry_run:
                out.append(f"would-list {page}")
                continue
            for url in self.supplement_links(page):
                name = safe_name(url)
                rel = self.cache.rel("supplement", p["key"], name)
                if self.cache.has(rel):
                    out.append(f"cached {name}")
                    continue
                resp = self._get(url)
                if resp.status in BLOCKED_STATUS or resp.status >= 400 or resp.status == 0:
                    out.append(f"{name}: blocked or error HTTP {resp.status}")
                    continue
                if len(resp.data) > self.max_bytes:
                    out.append(f"{name}: too large")
                    continue
                if name.lower().endswith(".pdf") and resp.data[:5] != b"%PDF-":
                    out.append(f"{name}: not a PDF")
                    continue
                self.cache.put(rel, resp.data, url=url, version="publisher", kind="supplement",
                               content_type=resp.content_type)
                out.append(f"fetched {name}")
        return out


# ---------------------------------------------------------------- commands
def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pick(manifest: dict, keys, all_flag: bool) -> list[dict]:
    papers = manifest["papers"]
    if all_flag:
        return papers
    index = {p["key"]: p for p in papers}
    short = {}
    for p in papers:
        short.setdefault(p["doi"].split("/", 1)[1].lower() if p.get("doi") else p["key"].lower(), p)
    chosen = []
    for k in keys or []:
        hit = index.get(k) or short.get(k.lower()) or index.get(doi_key(k, None))
        if not hit:
            raise KeyError(f"no manifest entry for {k!r}")
        chosen.append(hit)
    return chosen


def cmd_check(args) -> int:
    manifest = load_manifest(args.manifest)
    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    rows = sources if isinstance(sources, list) else sources["sources"]
    problems = check_manifest(manifest, ledger_dois(args.sources), {s["id"] for s in rows})
    print(json.dumps({"status": "pass" if not problems else "fail", "papers": len(manifest["papers"]),
                      "problems": problems}, indent=2))
    return 1 if problems else 0


def cmd_refresh(args, http=None) -> int:
    http = http or Http()
    hits, page = [], 1
    fields = "titles,dois,arxiv_eprints,publication_info,earliest_date,document_type,control_number"
    while True:
        url = "https://inspirehep.net/api/literature?" + urllib.parse.urlencode(
            {"q": INSPIRE_QUERY, "size": 100, "page": page, "sort": "mostrecent", "fields": fields})
        resp = http.get(url, 50 << 20)
        if resp.status != 200:
            print(json.dumps({"verdict": "unreadable", "error": f"INSPIRE HTTP {resp.status}"}))
            return 2
        data = json.loads(resp.data)
        hits += data["hits"]["hits"]
        if len(hits) >= data["hits"]["total"] or not data["hits"]["hits"]:
            break
        page += 1
        time.sleep(args.delay)
    ledger = ledger_dois(args.sources)
    papers = []
    for h in hits:
        doi = (h["metadata"].get("dois") or [{}])[0].get("value")
        oa = None
        if doi:
            time.sleep(args.delay)
            r = http.get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/")
                         + "?select=open_access,locations", 5 << 20)
            if r.status == 200:
                oa = json.loads(r.data)
        papers.append(build_entry(h, oa, ledger))
    papers.sort(key=lambda p: (p["date"], p["key"]))
    manifest = {"schema": "1", "generated": dt.date.today().isoformat(),
                "source": f"INSPIRE-HEP literature API, q='{INSPIRE_QUERY}'; open-access locations from OpenAlex",
                "note": "Metadata only. 'generation' is a heuristic. 'pdf_candidates' are tried in order; a "
                        "publisher PDF is preferred, arXiv and repository copies are labeled as such when cached. "
                        "No PDFs are stored in this repository.",
                "papers": papers}
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    problems = check_manifest(manifest, ledger)
    print(json.dumps({"status": "wrote", "papers": len(papers), "problems": problems}, indent=2))
    return 1 if problems else 0


def cmd_status(args) -> int:
    manifest, cache = load_manifest(args.manifest), Cache(args.cache)
    rows = []
    for p in manifest["papers"]:
        art = cache.article(p["key"])
        supp = [r for r in cache.index["files"] if r.startswith(f"supp/{p['key']}/")]
        state = f"cached ({art['version']})" if art else ("blocked" if p["key"] in cache.index["blocked"] else "missing")
        rows.append({"key": p["key"], "ref": p["journal_ref"], "status": state, "supplements": len(supp),
                     "sources": p["source_ids"]})
    counts: dict = {}
    for r in rows:
        counts[r["status"].split(" ")[0]] = counts.get(r["status"].split(" ")[0], 0) + 1
    print(json.dumps({"cache": str(args.cache), "counts": counts, "papers": rows}, indent=2))
    return 0


def cmd_fetch(args, http=None) -> int:
    if not args.all and not args.keys:
        print(json.dumps({"verdict": "unreadable", "error": "give --keys or --all"}))
        return 2
    manifest = load_manifest(args.manifest)
    try:
        chosen = pick(manifest, args.keys, args.all)
    except KeyError as exc:
        print(json.dumps({"verdict": "unreadable", "error": str(exc)}))
        return 2
    cache = Cache(args.cache)
    f = Fetcher(cache, http=http, delay=args.delay, max_mb=args.max_mb, log=lambda s: print(s, file=sys.stderr),
                retries=args.retries, retry_wait=args.retry_wait)
    results, bad = [], 0
    for p in chosen:
        res = f.fetch_article(p, args.dry_run)
        entry = {"key": p["key"], "article": res}
        if args.supplements and p.get("supplement_pages"):
            entry["supplements"] = f.fetch_supplements(p, args.dry_run)
        if res in ("blocked", "failed", "no-candidate"):
            bad += 1
        results.append(entry)
        if not args.dry_run:
            cache.save()
    print(json.dumps({"cache": str(args.cache), "results": results, "not_fetched": bad,
                      "hint": "blocked papers: download in a browser, then `adopt` the file" if bad else ""}, indent=2))
    return 1 if bad else 0


def cmd_adopt(args) -> int:
    manifest, cache = load_manifest(args.manifest), Cache(args.cache)
    files: list[Path] = []
    for item in args.paths:
        pth = Path(item).expanduser()
        files += sorted(pth.glob("*.pdf")) if pth.is_dir() else [pth]
    by_name = {}
    for p in manifest["papers"]:
        if p.get("doi"):
            by_name[p["doi"].split("/", 1)[1].lower()] = p
        by_name[p["key"].lower()] = p
    adopted, skipped = [], []
    for f in files:
        stem = re.sub(r" \(\d+\)$", "", f.stem).lower()
        p = by_name.get(stem)
        if p is None or not f.is_file():
            skipped.append(f"{f.name}: no manifest entry matches the file name (expected e.g. PhysRevLett.110.141102.pdf)")
            continue
        data = f.read_bytes()
        if data[:5] != b"%PDF-":
            skipped.append(f"{f.name}: not a PDF")
            continue
        if cache.article(p["key"]) and not args.force:
            skipped.append(f"{f.name}: {p['key']} already cached (use --force to replace)")
            continue
        cache.put(f"pdf/{p['key']}.pdf", data, url=f"adopted:{f.name}", version=args.version, kind="article",
                  content_type="application/pdf")
        cache.index["blocked"].pop(p["key"], None)
        adopted.append(p["key"])
    cache.save()
    print(json.dumps({"adopted": adopted, "skipped": skipped}, indent=2))
    return 1 if skipped and not adopted else 0


def cmd_verify(args) -> int:
    cache = Cache(args.cache)
    bad = []
    for rel, meta in cache.index["files"].items():
        path = cache.root / rel
        if not path.exists():
            bad.append(f"{rel}: missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != meta["sha256"]:
            bad.append(f"{rel}: hash differs from the index")
    print(json.dumps({"checked": len(cache.index["files"]), "problems": bad}, indent=2))
    return 1 if bad else 0


def cmd_extract(args) -> int:
    exe = shutil.which("pdftotext")
    if not exe:
        print(json.dumps({"verdict": "unreadable", "error": "pdftotext is not installed (poppler); extract is optional"}))
        return 2
    cache = Cache(args.cache)
    want = {p["key"] for p in pick(load_manifest(args.manifest), args.keys, not args.keys)}
    done = []
    for rel in sorted(cache.index["files"]):
        if not rel.endswith(".pdf"):
            continue
        key = rel.split("/")[1].removesuffix(".pdf")
        if key not in want:
            continue
        out = cache.root / "txt" / (rel[:-4].replace("/", "__") + ".txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        if subprocess.run([exe, "-layout", str(cache.root / rel), str(out)], capture_output=True).returncode == 0:
            done.append(str(out.relative_to(cache.root)))
    print(json.dumps({"extracted": len(done), "files": done}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--sources", type=Path, default=SOURCES, help="ledger sources used for the cross-check")
    ap.add_argument("--cache", type=Path, default=None, help="cache directory (default $AMS_PAPERS_CACHE or ~/.cache/ams-analysis/papers)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-manifest", help="offline schema and ledger cross-check")
    r = sub.add_parser("refresh-manifest", help="rebuild the manifest from INSPIRE-HEP and OpenAlex (network)")
    r.add_argument("--delay", type=float, default=0.5)
    sub.add_parser("status", help="show cache state per paper")
    f = sub.add_parser("fetch", help="download papers into the cache")
    f.add_argument("--keys", nargs="*", help="manifest keys or DOI tails such as PhysRevLett.110.141102")
    f.add_argument("--all", action="store_true")
    f.add_argument("--supplements", action="store_true",
                   help="also fetch APS Supplemental Material files (off by default; the files can be large)")
    f.add_argument("--dry-run", action="store_true")
    f.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    f.add_argument("--max-mb", type=int, default=400, help="per-file size cap")
    f.add_argument("--retries", type=int, default=1, help="retries for transient errors (5xx, 406, network); 0 disables; blocks are never retried")
    f.add_argument("--retry-wait", type=float, default=5.0, help="seconds to wait before a retry")
    a = sub.add_parser("adopt", help="register PDFs you downloaded yourself (matched by file name)")
    a.add_argument("paths", nargs="+")
    a.add_argument("--force", action="store_true")
    a.add_argument("--version", default="publisher", choices=["publisher", "arxiv", "repository"])
    sub.add_parser("verify", help="re-hash cached files against the index")
    e = sub.add_parser("extract", help="pdftotext -layout for cached PDFs")
    e.add_argument("--keys", nargs="*")
    return ap


def main(argv: list[str] | None = None, http=None) -> int:
    args = build_parser().parse_args(argv)
    args.cache = args.cache or default_cache()
    try:
        if args.cmd == "check-manifest":
            return cmd_check(args)
        if args.cmd == "refresh-manifest":
            return cmd_refresh(args, http)
        if args.cmd == "status":
            return cmd_status(args)
        if args.cmd == "fetch":
            return cmd_fetch(args, http)
        if args.cmd == "adopt":
            return cmd_adopt(args)
        if args.cmd == "verify":
            return cmd_verify(args)
        return cmd_extract(args)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"verdict": "unreadable", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
