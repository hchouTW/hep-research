"""Receipt (spec sections 7.1, 7.2, A3 without --rerun, A5): gather the facts a review record is judged on (the
dispatch, the packet the reviewer saw, canaries, and every file the record names, hashed again now), then apply the
pure rules of contracts.review.receipt_codes."""
from __future__ import annotations

import datetime
import fnmatch
import json
import re
from pathlib import Path

from contracts.review import parse_time, sha256_file
from review_lib import units as U
from review_lib.store import read_json

PLUGIN = Path(__file__).resolve().parents[4]
IMPLEMENTATION = ("skills/hep-authoring/scripts/review*.py", "skills/hep-authoring/scripts/review_lib/*",
                  "skills/hep-authoring/assets/review-lenses.json", "skills/hep-authoring/assets/review-hosts.json",
                  "contracts/review.py")
URLISH = re.compile(r"^[a-z][a-z0-9+.-]*://")


def artifacts_dir(project: Path) -> Path:
    try:
        cfg = json.loads((project / "hep-research.project.json").read_text(encoding="utf-8"))
        return (project / cfg.get("artifacts_dir", "hep-research-artifacts")).resolve()
    except (OSError, ValueError):
        return (project / "hep-research-artifacts").resolve()


def _within(p: Path, d: Path) -> bool:
    return p == d or d in p.parents


def classify(rv, adir: Path, path_str: str, started, shared: list[Path], doc: Path, probes=()) -> dict:
    """{exists, local, sha256, forbidden (reason or None), in_work} of one path a record names; a relative path is
    relative to the attempt folder, or to the plugin root when it names no file there."""
    if URLISH.match(path_str):
        return {"exists": False, "local": False, "sha256": None, "forbidden": None, "in_work": False}
    p = Path(path_str)
    if not p.is_absolute():  # relative to the attempt folder, else to the plugin root (reviewers cite plugin paths)
        p = adir / p if (adir / p).exists() or not (PLUGIN / p).exists() else PLUGIN / p
    try:
        p = p.resolve()
    except (OSError, RuntimeError):
        return {"exists": False, "local": True, "sha256": None, "forbidden": None, "in_work": False}
    forbidden = None
    if p == doc:
        forbidden = "the original delivered document"
    elif _within(p, rv.private.resolve()):
        forbidden = "the private directory"
    elif p in (rv.log.resolve(), rv.head.resolve()):
        forbidden = "the event log"
    elif _within(p, rv.dir.resolve()) and not _within(p, adir.resolve()):
        forbidden = "another slot's or attempt's folder"
    elif _within(p, artifacts_dir(rv.project)):
        forbidden = "the author's traceability records"
    elif _within(p, PLUGIN):
        rel = p.relative_to(PLUGIN).as_posix()
        if any(fnmatch.fnmatch(rel, pat) for pat in IMPLEMENTATION):
            forbidden = "the mechanism's implementation files"
    if forbidden is None and probes and not _within(p, (adir / "packet").resolve()) and U.is_copy(p, list(probes)):
        forbidden = "a copy or version of the delivered document"
    if forbidden is None and p.exists():
        for d in shared:
            if _within(p, d.resolve()):
                mt = datetime.datetime.fromtimestamp(int(p.stat().st_mtime), datetime.UTC)
                if started and mt < started:
                    forbidden = "a host shared-directory file older than the attempt"
    return {"exists": p.is_file(), "local": True, "sha256": sha256_file(p) if p.is_file() else None,
            "forbidden": forbidden, "in_work": _within(p, (adir / "work").resolve()) and p.is_file()}


def record_paths(record: dict) -> list[str]:
    out = [p.get("path") for p in record.get("paths_read", []) if isinstance(p, dict)]
    for e in record.get("evidence", []):
        if not isinstance(e, dict):
            continue
        out += [e.get("ref"), e.get("copy"), e.get("script")]
        out += [o.get("path") for o in e.get("output_files", []) if isinstance(o, dict)]
    return sorted({p for p in out if isinstance(p, str) and p})


def build_context(rv, *, r: int, sid: str, k: int, slot: dict, dispatched: dict, author: str, shared: list[Path],
                  instructions_changed: bool, parties: list[str], item_lenses: dict, record) -> dict:
    adir = rv.attempt_dir(r, sid, k)
    pdir = adir / "packet"
    scope = read_json(pdir / "scope.json")
    units = read_json(pdir / "units.json")["units"]
    cpath = rv.private_attempt(r, sid, k) / "canary.json"
    canaries = read_json(cpath)["canaries"] if cpath.exists() else []
    started = parse_time(dispatched["started"])
    doc = (rv.project / rv_document(rv)).resolve()
    probes = U.copy_probes(read_json(rv.units_path(r))["units"])
    files = {}
    if isinstance(record, dict):
        for p in record_paths(record):
            files[p] = classify(rv, adir, p, started, shared, doc, probes)
    items = {}
    if slot["role"] == "arbiter":
        for it in read_json(pdir / "items.json")["items"]:
            items[it["item_id"]] = {"type": it["type"], "lenses": item_lenses.get(it["item_id"], ["facts"])}
    return {"kind": slot["role"], "lens": slot.get("lens") or "facts", "slot_id": sid,
            "dispatched": {"packet_sha256": dispatched["packet_sha256"], "nonce": dispatched["nonce"],
                           "instructions_sha256": dispatched["instructions_sha256"]},
            "author": author, "parties": parties,
            "limits": {k2: scope[k2] for k2 in ("max_units_per_claim", "na_max_ratio", "unresolved_max_ratio",
                                                 "refutation_duplicate_max", "refutation_min_attempts_effective")},
            "unit_text": {u["id"]: u["text"] for u in units}, "skim_units": scope["skim_units"],
            "deep_units": scope["deep_units"] + scope["focus_units"],
            "canaries": [{"unit": c["unit"], "new_key": c["new_key"], "old_key": c["old_key"]} for c in canaries],
            "carry_refs": [c["ref"] for c in scope.get("carry_forward", [])], "items": items, "files": files,
            "instructions_changed": instructions_changed}


def rv_document(rv) -> str:
    first = rv.events()[0]
    return first["data"]["document"]
