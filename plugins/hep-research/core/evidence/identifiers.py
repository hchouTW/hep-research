"""Stable literature identifiers: normalized DOI, arXiv id (version kept apart) and INSPIRE record id.

One paper, one entry: identifiers decide (DOI, else arXiv id without version, else INSPIRE record id), never citation
keys or titles. Used by hep-citations (the literature-record import) and hep-authoring (the citation check of a
draft), so both read a source's identifiers the same way. Library module; standard library only.
"""
from __future__ import annotations

import re

ARXIV_RE = re.compile(r"^(?:arxiv:)?\s*(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v(\d+))?$", re.I)
DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:", "doi ")


def normalize_doi(doi) -> str | None:
    """Lower-case DOI without resolver prefix, or None."""
    if not isinstance(doi, str) or not doi.strip():
        return None
    d = doi.strip().lower()
    for prefix in DOI_PREFIXES:
        if d.startswith(prefix):
            d = d[len(prefix):]
    return d or None


def normalize_arxiv(aid) -> tuple[str, str | None] | None:
    """(arXiv id without version, 'vN' or None), or None when the text is not an arXiv id."""
    if not isinstance(aid, str):
        return None
    m = ARXIV_RE.match(aid.strip())
    if not m:
        return None
    return m.group(1), (f"v{m.group(2)}" if m.group(2) else None)


def identifiers_of(src: dict, top_level_inspire: bool = False) -> dict:
    """{doi, arxiv, arxiv_version, inspire} of an evidence-ledger source: identifiers.dois and arxiv_ids (or the same
    keys at top level, as profile ledgers write them) and identifiers.inspire_record_id (also at top level when
    top_level_inspire is set; the literature import reads it only from identifiers)."""
    raw = src.get("identifiers")
    ids: dict = raw if isinstance(raw, dict) else {}
    dois = [normalize_doi(x) for x in (ids.get("dois") or src.get("dois") or [])]
    arx = [normalize_arxiv(x) for x in (ids.get("arxiv_ids") or src.get("arxiv_ids") or [])]
    inspire = ids.get("inspire_record_id")
    if inspire in (None, "") and top_level_inspire:
        inspire = src.get("inspire_record_id")
    return {"doi": next((d for d in dois if d), None), "arxiv": next((a[0] for a in arx if a), None),
            "arxiv_version": next((a[1] for a in arx if a and a[1]), None),
            "inspire": str(inspire) if inspire not in (None, "") else None}


def keys_of(ids: dict) -> set:
    """The stable identifier keys (kind, value) a source can be matched on."""
    return {(k, ids[k]) for k in ("doi", "arxiv", "inspire") if ids.get(k)}
