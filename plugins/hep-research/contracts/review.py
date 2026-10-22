#!/usr/bin/env python3
"""Independent review contract (docs/dev/independent-review-spec.md, P1): the seven review schemas, their Python rules,
the shared state-transition table and the overall check. Pure: nothing here writes a file; the process driver
(skills/hep-authoring/scripts/review.py) and `check` both use these functions, so the state logic exists once.

Schemas (contracts/schemas/): review_config, review_units, review_manifest, review_record, review_event, review_head,
review_observation, and (contracts 3.4.0) review_filter_record, the record of the optional filtering pass. The built-in
validator has no oneOf, if/then, maxItems or maximum, so ranges, conditional fields, the loose direction of thresholds
(weak_config) and every rule that needs more than one field are functions below.

Event log: review_log.jsonl, one canonical JSON record per line {seq, prev_sha256, event, time, data}, each binding the
canonical SHA-256 (contracts.revocation.canonical_sha256) of the record before it; review_head.json {head_version,
review_id, count, last_sha256}. A log is trusted only with a head that matches it.

State (spec section 6): fold() reads the event list; snapshot() turns it into slot, arbitration-item and finding
states; decide() applies the decision table of section 6.5 to a snapshot and returns one action. decide reads only
what the events say: sidecar files and the clock enter through observed events.

Usage:
  review.py check REVIEW_DIR [--project ROOT]        overall check (section 7.4); read-only
  review.py check --record-only RECORD [--role reviewer|arbiter|filter] [--max-units-per-claim N]
                                                     schema and context-free rules of one review record
                                                     (--role filter: a filter record, filter_record.json)
Output: JSON with a "status" key. Exit 0 ok (warnings may be listed), 1 fail, 2 unreadable input, 3 incomplete
(not_closed, finding_open).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.revocation import canonical_sha256, encode  # noqa: E402,F401  (encode: the log line format)
from contracts.schema import validate  # noqa: E402

REVIEW_VERSION = "1.0.0"
ZERO = "0" * 64
FIXED_LENSES = ("facts", "design", "sources", "bypass")
LOOSE_LENSES = frozenset({"design", "bypass"})  # any evidence; every other lens needs external evidence
EXTERNAL_BASES = frozenset({"locator", "third-party", "tool-output", "exhaustive", "person"})
INDEPENDENT_BASES = frozenset({"third-party", "exhaustive", "person"})  # a locator only with an independent source_kind
INDEPENDENT_SOURCE_KINDS = frozenset({"paper", "equation", "table", "page"})
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

# name: (default, low, high, loose direction). Spec section 5.1; "higher" means a higher value is looser.
CONFIG_RULES = {
    "max_rounds": (3, 1, 5, "higher"),
    "max_attempts_per_slot": (2, 1, 3, "higher"),
    "attempt_timeout_minutes": (40, 20, 120, None),
    "deep_sample": (15, 5, 50, "lower"),
    "max_units_per_claim": (3, 1, 5, "higher"),
    "na_max_ratio": (0.3, 0, 0.5, "higher"),
    "unresolved_max_ratio": (0.3, 0, 0.5, "higher"),
    "refutation_duplicate_max": (0.2, 0, 0.3, "higher"),
    "refutation_min_attempts_for_ratio": (5, 3, 10, "higher"),
    "canaries_per_slot": (2, 1, 3, "lower"),
}

# reason codes (spec section 7)
COMMON_CODES = ("schema_invalid", "packet_mismatch", "dispatch_mismatch", "prior_conversation", "read_outside_packet",
                "file_hash_mismatch", "output_mismatch", "instructions_changed")
REVIEWER_CODES = COMMON_CODES + ("same_identity", "finding_shape", "claim_shape", "deep_missing", "skim_missing",
                                 "basis_missing", "self_citation", "refutation_weak", "verdict_without_finding",
                                 "unresolved_dominant", "canary_missed", "carry_forward_missing")
ARBITER_CODES = COMMON_CODES + ("arbiter_identity", "resolves_incomplete", "resolution_type", "resolution_basis")
# the filter slot of the optional filtering pass (contracts 3.4.0, spec 6.9 and 7.5): it writes no evidence, so
# output_mismatch never applies
FILTER_CODES = tuple(c for c in COMMON_CODES if c != "output_mismatch") + ("same_identity", "decisions_incomplete",
                                                                           "duplicate_target")
FILTER_DECISIONS = ("keep", "drop")
FILTER_MAX_ATTEMPTS = 2     # at most; fewer when max_attempts_per_slot is lower
SIDECAR = "review_record.json"
FILTER_SIDECAR = "filter_record.json"
REPAIR_CODES = ("config_changed", "config_out_of_range", "canary_in_deliverable", "isolation_precondition",
                "isolation_not_yet_effective", "shared_dir_contamination", "change_without_edit")
CHECK_CODES = {"log_broken": "fail", "not_closed": "incomplete", "changed_after_close": "fail",
               "artifacts_changed": "fail", "finding_open": "incomplete", "uphold_not_honored": "fail",
               "adopted_unverified": "warning", "no_model_diversity": "warning", "canary_shortfall": "warning",
               "no_control": "warning", "weak_config": "warning", "superseded_reviews": "listing",
               "late_records": "listing"}
ROLE_REQUIRED = {"reviewer": ("skim", "claims", "verdicts", "findings"), "arbiter": ("resolves",)}
ALLOWED_CONCLUSIONS = {"decline": ("uphold-finding", "accept-decline", "unresolved"),
                       "conflict": ("uphold-first", "uphold-second", "unresolved")}
HUMAN_DECISIONS = {"finding": ("close", "reopen"), "item-decline": ("uphold-finding", "accept-decline"),
                   "item-conflict": ("uphold-first", "uphold-second"), "slot": ("accept-missing",),
                   "verdict": ("uphold", "supersede"), "round-limit": ("extend", "accept")}

# key fields of each event's data (spec section 5.4)
EVENT_FIELDS = {
    "round_started": ("review_id", "round", "document", "source_sha256", "units_sha256", "config", "config_sha256",
                      "slots", "author", "carry_forward", "removed_findings"),
    "observed": ("time", "document_sha256", "sidecars", "repair", "warnings"),
    "dispatched": ("round", "slot_id", "attempt", "packet_sha256", "nonce", "instructions_sha256", "deadline",
                   "canary_commitment", "seed_commitment", "started", "canaries", "canaries_expected",
                   "instruction_files_sha256"),
    "returned": ("round", "slot_id", "attempt"),
    "accepted": ("round", "slot_id", "attempt", "review_sha256", "recomputed", "metrics"),
    "rejected": ("round", "slot_id", "attempt", "review_sha256", "codes"),
    "withdrawn": ("round", "slot_id", "attempt", "reason"),
    "late": ("round", "slot_id", "attempt", "sha256"),
    "disposed": ("finding", "disposition", "reason", "verification", "edited_units", "finding_units", "round", "by"),
    "change_confirmed": ("finding", "round", "slot_id"),
    "change_rejected": ("finding", "round", "slot_id"),
    "arbitration_needed": ("round", "item_id", "type", "slot_id", "model", "first", "second", "finding", "lenses"),
    "arbitration_resolved": ("round", "item_id", "conclusion", "record_sha256"),
    "escalated": ("items", "reason"),
    "human_resolved": ("item", "by", "decision", "reason"),
    "change_reverted": ("finding",),
    "reported": ("report_sha256",),
    "closed": ("report_sha256", "document_sha256"),
    "superseded": ("by", "reason"),
    "filter_needed": ("round", "slot_id", "model", "findings"),
}
TERMINAL = ("closed", "superseded")


# --- small helpers ---------------------------------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str | None:
    try:
        return sha256_bytes(Path(path).read_bytes())
    except OSError:
        return None


def parse_time(text) -> datetime.datetime | None:
    try:
        return datetime.datetime.strptime(str(text), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC)
    except ValueError:
        return None


def format_time(t: datetime.datetime) -> str:
    return t.astimezone(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def unit_pos(uid) -> int | None:
    m = re.fullmatch(r"U(\d{4,})", str(uid))
    return int(m.group(1)) if m else None


def contiguous(units) -> bool:
    """1 or more distinct unit ids forming one run of consecutive positions."""
    pos = [unit_pos(u) for u in units]
    if not pos or None in pos or len(set(pos)) != len(pos):
        return False
    ints = [p for p in pos if p is not None]
    return max(ints) - min(ints) == len(ints) - 1


def is_numeric_key(key: str) -> bool:
    return bool(re.fullmatch(r"[0-9][0-9.\-]*[0-9]|[0-9]", key))


def key_in(text: str, key: str) -> bool:
    """A key diff occurs in text: a numeric key on its digits, not directly preceded or followed by another digit (so
    '3' matches '3 倍' and '3x'); an identifier key on identifier boundaries."""
    if not key or not isinstance(text, str):
        return False
    if is_numeric_key(key):
        return re.search(r"(?<![0-9])" + re.escape(key) + r"(?![0-9])", text) is not None
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(key) + r"(?![A-Za-z0-9_])", text) is not None


# --- configuration (section 5.1) -------------------------------------------------------------------------------------

def effective_config(cfg: dict) -> dict:
    out: dict[str, Any] = {k: v[0] for k, v in CONFIG_RULES.items()}
    out["extra_lenses"] = []
    out["lens_models"] = {}
    out["filter"] = None
    out.update({k: v for k, v in (cfg or {}).items()})
    return out


def config_problems(cfg) -> list[str]:
    """Schema errors and out-of-range values (each one is config_out_of_range)."""
    if not isinstance(cfg, dict):
        return ["config is not a JSON object"]
    out = [f"{f.path}: {f.message}" for f in validate(cfg, "review_config.json").errors]
    for name, (_, low, high, _) in CONFIG_RULES.items():
        v = cfg.get(name)
        if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        if not low <= v <= high:
            out.append(f"{name}: {v} outside the allowed range {low}-{high}")
    models: list = cfg["models"] if isinstance(cfg.get("models"), list) else []
    lm = cfg.get("lens_models")
    if isinstance(lm, dict):
        for lens, model in sorted(lm.items()):
            if not re.fullmatch(r"[a-z][a-z0-9-]*", lens):
                out.append(f"lens_models: {lens!r} is not a lens name")
            if isinstance(model, str) and model not in models:
                out.append(f"lens_models.{lens}: {model} is not in models")
    return out


def weak_config(cfg) -> list[str]:
    """Quality thresholds set looser than their default (spec 5.1: 0.49 for unresolved_max_ratio is weak)."""
    eff = effective_config(cfg)
    out = []
    for name, (default, _, _, loose) in CONFIG_RULES.items():
        v = eff.get(name)
        if loose and isinstance(v, (int, float)) and not isinstance(v, bool):
            if (loose == "higher" and v > default) or (loose == "lower" and v < default):
                out.append(name)
    return out


def refutation_threshold(cfg: dict, n_deep: int) -> int:
    """Effective refutation_min_attempts: min(configured value, deep units), minimum 3."""
    return max(3, min(int(effective_config(cfg)["refutation_min_attempts_for_ratio"]), n_deep))


def lens_strict(lens: str) -> bool:
    return lens not in LOOSE_LENSES


# --- review record rules (section 5.3, the context-free part of 7.1 and 7.2) ---------------------------------------

def _p(code, message):
    return (code, message)


def record_rules(record, role: str | None = None, max_units: int = 3) -> list[tuple[str, str]]:
    """Problems of one review record that need no packet: the schema, role-required fields and the rules that read
    only the record. Used by check --record-only, by the generator's example validation and by receipt."""
    if not isinstance(record, dict):
        return [_p("schema_invalid", "the record is not a JSON object")]
    errs = validate(record, "review_record.json").errors
    if errs:
        return [_p("schema_invalid", f"{e.path}: {e.message}") for e in errs[:20]]
    out = []
    rrole = record["role"]
    if role and rrole != role:
        out.append(_p("schema_invalid", f"$.role: {rrole} where this slot needs {role}"))
    for key in ROLE_REQUIRED[rrole]:
        if key not in record:
            out.append(_p("schema_invalid", f"$.{key}: required for role {rrole}"))
    for key in ("skim", "claims", "verdicts", "findings", "carry_forward"):
        if rrole == "arbiter" and record.get(key):
            out.append(_p("schema_invalid", f"$.{key}: an arbiter record carries no {key}"))
    if rrole == "reviewer" and record.get("resolves"):
        out.append(_p("schema_invalid", "$.resolves: only an arbiter record carries resolves"))
    if any(not str(record.get(k, "")).strip() for k in ("limitations",)):
        out.append(_p("schema_invalid", "$.limitations: must not be blank"))
    ev = {}
    for e in record.get("evidence", []):
        if e["id"] in ev:
            out.append(_p("schema_invalid", f"evidence id {e['id']} repeated"))
        ev[e["id"]] = e
        if e["basis"] == "locator":
            if "lines" not in e and "section" not in e:
                out.append(_p("schema_invalid", f"evidence {e['id']}: a locator needs lines or section"))
            if re.match(r"^[a-z][a-z0-9+.-]*://", e["ref"]) and "copy" not in e:
                out.append(_p("schema_invalid", f"evidence {e['id']}: a URL locator needs copy (the fetched copy in work/)"))
    claims = {}
    for c in record.get("claims", []):
        if c["id"] in claims:
            out.append(_p("claim_shape", f"claim id {c['id']} repeated"))
        claims[c["id"]] = c
        if len(c["units"]) > max_units or not contiguous(c["units"]):
            out.append(_p("claim_shape", f"claim {c['id']}: needs 1-{max_units} contiguous units"))
    findings = {}
    for f in record.get("findings", []):
        if f["id"] in findings:
            out.append(_p("schema_invalid", f"finding id {f['id']} repeated"))
        findings[f["id"]] = f
        if len(f["units"]) > max_units or not contiguous(f["units"]):
            out.append(_p("finding_shape", f"finding {f['id']}: needs 1-{max_units} contiguous units"))
    counts = {cid: 0 for cid in claims}
    for v in record.get("verdicts", []):
        if v["claim_id"] not in claims:
            out.append(_p("claim_shape", f"verdict for unknown claim {v['claim_id']}"))
            continue
        counts[v["claim_id"]] += 1
        if not v["rationale"].strip():
            out.append(_p("schema_invalid", f"verdict {v['claim_id']}: rationale must not be blank"))
        missing = [x for x in v["evidence_ids"] if x not in ev] + [x for x in v["finding_ids"] if x not in findings]
        if missing:
            out.append(_p("schema_invalid", f"verdict {v['claim_id']}: unknown ids {missing}"))
        own = set(claims[v["claim_id"]]["units"])
        own_pos = {unit_pos(u) for u in own}
        for x in v["evidence_ids"]:
            e = ev.get(x)
            if e and e["basis"] == "internal":
                near = [u for u in e["units"] if any(abs((unit_pos(u) or -99) - (p or -99)) <= 2 for p in own_pos if p)]
                if near:
                    out.append(_p("self_citation", f"verdict {v['claim_id']}: internal evidence {x} cites {near}, "
                                                   "the claim's own or adjacent units"))
        if any(a["target"].strip() in own for a in v["refutation_attempts"]):
            out.append(_p("self_citation", f"verdict {v['claim_id']}: a refutation attempt targets the claim's own unit"))
        if v["verdict"] == "supported" and (not v["refutation_attempts"]
                                            or any(not a["target"].strip() for a in v["refutation_attempts"])):
            out.append(_p("refutation_weak", f"verdict {v['claim_id']}: supported without a refutation attempt with a target"))
        if v["verdict"] in ("partially-supported", "unsupported") and not v["finding_ids"]:
            out.append(_p("verdict_without_finding", f"verdict {v['claim_id']}: {v['verdict']} without a finding"))
    for cid, n in counts.items():
        if n != 1:
            out.append(_p("claim_shape", f"claim {cid}: {n} verdicts (exactly one needed)"))
    for s in record.get("skim", []):
        if s["mark"] == "issue" and s.get("finding_id") not in findings:
            out.append(_p("skim_missing", f"skim {s['unit']}: an issue without a matching finding"))
    for c in record.get("carry_forward", []):
        if c["status"] == "confirmed" and not c.get("evidence_ids"):
            out.append(_p("carry_forward_missing", f"carry_forward {c['ref']}: confirmed without evidence"))
        elif any(x not in ev for x in c.get("evidence_ids", [])):
            out.append(_p("schema_invalid", f"carry_forward {c['ref']}: unknown evidence ids"))
    seen = set()
    for r in record.get("resolves", []):
        if r["item_id"] in seen:
            out.append(_p("resolves_incomplete", f"item {r['item_id']}: more than one conclusion"))
        seen.add(r["item_id"])
        if any(x not in ev for x in r["evidence_ids"]):
            out.append(_p("schema_invalid", f"resolve {r['item_id']}: unknown evidence ids"))
    return out


def basis_class(e: dict) -> str:
    """independent | external (not independent) | internal: how the report counts an evidence item."""
    b = e.get("basis")
    if b in INDEPENDENT_BASES or (b == "locator" and e.get("source_kind") in INDEPENDENT_SOURCE_KINDS):
        return "independent"
    return "external" if b in EXTERNAL_BASES else "internal"


# --- receipt (sections 7.1, 7.2, A3, A5) -----------------------------------------------------------------------------

def _finding_text_ok(f: dict, unit_text: dict) -> bool:
    if not all(u in unit_text for u in f["units"]):
        return False
    ordered = sorted(f["units"], key=lambda u: unit_pos(u) or 0)
    return norm_ws(f["value"]) in norm_ws(" ".join(unit_text[u] for u in ordered))


def finding_ok(f: dict, unit_text: dict, max_units: int) -> bool:
    """finding_shape for one finding: 1..max contiguous units of this slot, value an excerpt of their text."""
    return len(f["units"]) <= max_units and contiguous(f["units"]) and _finding_text_ok(f, unit_text)


def canary_hits(record: dict, canaries: list, unit_text: dict, max_units: int) -> dict:
    """{canary unit: [finding ids that hit it]}; a hit passes finding_shape, cites the unit and its value carries the
    new value's key diff (A5)."""
    out: dict[str, list] = {c["unit"]: [] for c in canaries}
    for f in record.get("findings", []):
        if not finding_ok(f, unit_text, max_units):
            continue
        for c in canaries:
            if c["unit"] in f["units"] and key_in(f["value"], c["new_key"]):
                out[c["unit"]].append(f["id"])
    return out


def exact_correction(f: dict, old_key: str) -> bool:
    return any(key_in(f.get(k, ""), old_key) for k in ("correction", "description", "fix"))


def receipt_codes(record, ctx: dict) -> list[tuple[str, str]]:
    """Every receipt problem of a record, given the facts the driver gathered (ctx):
    kind (lens|shadow|arbiter), lens, slot_id, dispatched {packet_sha256, nonce, instructions_sha256}, author,
    limits {max_units_per_claim, na_max_ratio, unresolved_max_ratio, refutation_duplicate_max,
    refutation_min_attempts_effective}, unit_text {id: text in this slot's version}, skim_units, deep_units,
    canaries [{unit, new_key}], carry_refs, items {item_id: {type, lenses}}, parties [identities],
    files {path string: {exists, sha256, forbidden, in_work}}, instructions_changed (bool).
    A schema problem stops the other rules; every other code is reported independently."""
    kind = ctx["kind"]
    role = "arbiter" if kind == "arbiter" else "reviewer"
    lim = ctx["limits"]
    max_units = int(lim["max_units_per_claim"])
    base = record_rules(record, role, max_units)
    if any(c == "schema_invalid" for c, _ in base):
        return [p for p in base if p[0] == "schema_invalid"]
    out = list(base)
    d = ctx["dispatched"]
    if record["packet_sha256"] != d["packet_sha256"]:
        out.append(_p("packet_mismatch", "packet_sha256 differs from the dispatched packet"))
    if record["dispatch_nonce"] != d["nonce"] or record["instructions_sha256"] != d["instructions_sha256"] \
            or record["reviewer"]["slot_id"] != ctx["slot_id"]:
        out.append(_p("dispatch_mismatch", "nonce, instructions_sha256 or slot_id differs from the dispatch"))
    if record["isolation"]["saw_prior_conversation"]:
        out.append(_p("prior_conversation", "the reviewer saw a prior conversation"))
    ident = record["reviewer"]["identity"].strip()
    if kind == "arbiter":
        if ident == ctx.get("author") or ident in ctx.get("parties", ()):
            out.append(_p("arbiter_identity", "the arbiter is the author or a reviewer under arbitration"))
    elif ident == ctx.get("author"):
        out.append(_p("same_identity", "the reviewer's identity is the author's"))
    files = ctx.get("files", {})
    bad_read = [f"{p['path']} ({files[p['path']]['forbidden']})" for p in record["paths_read"]
                if (files.get(p["path"]) or {}).get("forbidden")]
    if bad_read:
        out.append(_p("read_outside_packet", f"forbidden paths read: {bad_read}"))
    hashed = [(p["path"], p["sha256"]) for p in record["paths_read"]]
    for e in record["evidence"]:
        if e["basis"] == "locator":
            if "copy" in e:
                hashed.append((e["copy"], e["sha256"]))
            elif (files.get(e["ref"]) or {}).get("local"):
                hashed.append((e["ref"], e["sha256"]))
    wrong = [p for p, h in hashed if (files.get(p) or {}).get("sha256") != h]
    if wrong:
        out.append(_p("file_hash_mismatch", f"whole-file sha256 differs or file missing: {sorted(set(wrong))}"))
    outs = []
    for e in record["evidence"]:
        for o in e.get("output_files", []):
            outs.append((o["path"], o["sha256"]))
        if e["basis"] == "exhaustive":
            outs.append((e["script"], e["script_sha256"]))
    bad_out = [p for p, h in outs if not (files.get(p) or {}).get("in_work") or (files.get(p) or {}).get("sha256") != h]
    if bad_out:
        out.append(_p("output_mismatch", f"output or script files missing, outside work/ or changed: {sorted(set(bad_out))}"))
    if ctx.get("instructions_changed"):
        out.append(_p("instructions_changed", "instruction files or settings changed during the attempt"))
    ev = {e["id"]: e for e in record["evidence"]}
    if kind == "arbiter":
        items = ctx.get("items", {})
        got = {r["item_id"]: r for r in record["resolves"]}
        if set(got) != set(items):
            out.append(_p("resolves_incomplete", f"resolves cover {sorted(got)}, items are {sorted(items)}"))
        for iid, r in got.items():
            it = items.get(iid)
            if not it:
                continue
            if r["conclusion"] not in ALLOWED_CONCLUSIONS[it["type"]]:
                out.append(_p("resolution_type", f"item {iid}: {r['conclusion']} is not allowed for a {it['type']}"))
            elif r["conclusion"] != "unresolved":
                strict = any(lens_strict(x) for x in it.get("lenses", ["facts"]))
                bases = [ev[x]["basis"] for x in r["evidence_ids"] if x in ev]
                if not bases or (strict and not any(b in EXTERNAL_BASES for b in bases)):
                    out.append(_p("resolution_basis", f"item {iid}: the conclusion lacks the evidence its lens needs"))
        return _dedupe(out)
    unit_text = ctx["unit_text"]
    claims = {c["id"]: c for c in record["claims"]}
    if any(u not in unit_text for c in claims.values() for u in c["units"]):
        out.append(_p("claim_shape", "a claim cites a unit that is not in units.json"))
    for f in record["findings"]:
        if len(f["units"]) <= max_units and contiguous(f["units"]) and not _finding_text_ok(f, unit_text):
            out.append(_p("finding_shape", f"finding {f['id']}: value is not an excerpt of its units in this packet"))
    deep = list(ctx["deep_units"])
    covered = {u for c in claims.values() for u in c["units"]}
    miss = [u for u in deep if u not in covered]
    if miss:
        out.append(_p("deep_missing", f"deep units without a claim: {miss}"))
    marks = {s["unit"]: s["mark"] for s in record["skim"]}
    skim = list(ctx["skim_units"])
    unmarked = [u for u in skim if u not in marks]
    na = sum(1 for u in skim if marks.get(u) == "n/a")
    if unmarked:
        out.append(_p("skim_missing", f"skim units without a mark: {unmarked[:10]}"))
    elif skim and na / len(skim) > float(lim["na_max_ratio"]):
        out.append(_p("skim_missing", f"n/a share {na}/{len(skim)} above na_max_ratio"))
    strict = lens_strict(ctx["lens"])
    deep_set = set(deep)
    verdicts = [v for v in record["verdicts"] if v["claim_id"] in claims]
    for v in verdicts:
        if v["verdict"] == "unresolved" or not set(claims[v["claim_id"]]["units"]) & deep_set:
            continue
        bases = [ev[x]["basis"] for x in v["evidence_ids"] if x in ev]
        if not bases or (strict and not any(b in EXTERNAL_BASES for b in bases)):
            out.append(_p("basis_missing", f"verdict {v['claim_id']}: no {'external ' if strict else ''}evidence"))
    attempts = [(a["method"].strip(), a["target"].strip()) for v in verdicts
                if set(claims[v["claim_id"]]["units"]) & deep_set for a in v["refutation_attempts"]]
    if attempts and len(attempts) >= int(lim["refutation_min_attempts_effective"]):
        counts: dict[tuple, int] = {}
        for a in attempts:
            counts[a] = counts.get(a, 0) + 1
        dup = sum(1 for a in attempts if counts[a] > 1)
        if dup / len(attempts) > float(lim["refutation_duplicate_max"]):
            out.append(_p("refutation_weak", f"{dup} of {len(attempts)} refutation attempts repeat a (method, target)"))
    if deep:
        by_unit: dict[str, list] = {u: [] for u in deep}
        for v in verdicts:
            for u in claims[v["claim_id"]]["units"]:
                if u in by_unit:
                    by_unit[u].append(v["verdict"])
        unres = sum(1 for u, vs in by_unit.items() if vs and all(x == "unresolved" for x in vs))
        if unres / len(deep) > float(lim["unresolved_max_ratio"]):
            out.append(_p("unresolved_dominant", f"{unres} of {len(deep)} deep units only unresolved"))
    if kind == "lens" and ctx.get("canaries"):
        hits = canary_hits(record, ctx["canaries"], unit_text, max_units)
        missed = [u for u, fs in hits.items() if not fs]
        if missed:
            out.append(_p("canary_missed", f"{len(missed)} control unit(s) without a hit"))
    refs = list(ctx.get("carry_refs", []))
    marked = {c["ref"] for c in record.get("carry_forward", [])}
    if [r for r in refs if r not in marked]:
        out.append(_p("carry_forward_missing", f"carry_forward items unmarked: {[r for r in refs if r not in marked]}"))
    return _dedupe(out)


def _dedupe(problems):
    seen, out = set(), []
    for p in problems:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def record_metrics(record: dict, ctx: dict) -> dict:
    """Quality metrics written into the accepted event and the report (A8)."""
    if record.get("role") == "arbiter":
        return {"resolves": {r["item_id"]: r["conclusion"] for r in record.get("resolves", [])},
                "bases": _basis_counts(record)}
    claims = {c["id"]: c for c in record.get("claims", [])}
    deep = set(ctx.get("deep_units", []))
    skim: dict[str, int] = {}
    for s in record.get("skim", []):
        skim[s["mark"]] = skim.get(s["mark"], 0) + 1
    dv: dict[str, int] = {}
    for v in record.get("verdicts", []):
        if set(claims.get(v["claim_id"], {}).get("units", [])) & deep:
            dv[v["verdict"]] = dv.get(v["verdict"], 0) + 1
    n = sum(dv.values())
    m = {"skim": dict(sorted(skim.items())), "deep_verdicts": dict(sorted(dv.items())),
         "partially_supported_share": round(dv.get("partially-supported", 0) / n, 4) if n else 0.0,
         "bases": _basis_counts(record)}
    cans = ctx.get("canaries") or []
    if cans:
        max_units = int(ctx["limits"]["max_units_per_claim"])
        hits = canary_hits(record, cans, ctx["unit_text"], max_units)
        fmap = {f["id"]: f for f in record.get("findings", [])}
        rows = []
        for c in cans:
            fs = hits.get(c["unit"], [])
            rows.append({"place": "deep" if c["unit"] in deep else "skim", "hit": bool(fs),
                         "exact": any(exact_correction(fmap[x], c.get("old_key", "")) for x in fs)})
        m["canaries"] = rows
    return m


# --- filter records (contracts 3.4.0; spec sections 5.5, 6.9 and 7.5) -------------------------------------------------

def filter_record_rules(record) -> list[tuple[str, str]]:
    """Problems of one filter record that need no packet: the schema, blank reasons, a finding decided twice, and
    duplicate_of (only on a drop, naming another finding this record keeps). Used by check --record-only --role
    filter, by the generator's example validation and by receipt."""
    if not isinstance(record, dict):
        return [_p("schema_invalid", "the record is not a JSON object")]
    errs = validate(record, "review_filter_record.json").errors
    if errs:
        return [_p("schema_invalid", f"{e.path}: {e.message}") for e in errs[:20]]
    out = []
    if not record["limitations"].strip():
        out.append(_p("schema_invalid", "$.limitations: must not be blank"))
    by_id: dict[str, list] = {}
    for d in record["decisions"]:
        if not d["reason"].strip():
            out.append(_p("schema_invalid", f"decision {d['finding_id']}: reason must not be blank"))
        by_id.setdefault(d["finding_id"], []).append(d["decision"])
    for fid, ds in by_id.items():
        if len(ds) > 1:
            out.append(_p("decisions_incomplete", f"finding {fid}: {len(ds)} decisions (exactly one needed)"))
    kept = {fid for fid, ds in by_id.items() if set(ds) == {"keep"}}
    for d in record["decisions"]:
        if "duplicate_of" not in d:
            continue
        if d["decision"] != "drop":
            out.append(_p("duplicate_target", f"decision {d['finding_id']}: duplicate_of is only for a drop"))
        elif d["duplicate_of"] == d["finding_id"] or d["duplicate_of"] not in kept:
            out.append(_p("duplicate_target", f"decision {d['finding_id']}: duplicate_of {d['duplicate_of']} is not "
                                              "another finding this record keeps"))
    return out


def filter_receipt_codes(record, ctx: dict) -> list[tuple[str, str]]:
    """Every receipt problem of a filter record (spec 7.5), given the facts the driver gathered (ctx): slot_id,
    dispatched {packet_sha256, nonce, instructions_sha256}, author, finding_ids (the ids in the packet's findings.json),
    files {path string: {exists, sha256, forbidden, in_work}}, instructions_changed (bool). A schema problem stops the
    other rules."""
    base = filter_record_rules(record)
    if any(c == "schema_invalid" for c, _ in base):
        return [p for p in base if p[0] == "schema_invalid"]
    out = list(base)
    d = ctx["dispatched"]
    if record["packet_sha256"] != d["packet_sha256"]:
        out.append(_p("packet_mismatch", "packet_sha256 differs from the dispatched packet"))
    if record["dispatch_nonce"] != d["nonce"] or record["instructions_sha256"] != d["instructions_sha256"] \
            or record["reviewer"]["slot_id"] != ctx["slot_id"]:
        out.append(_p("dispatch_mismatch", "nonce, instructions_sha256 or slot_id differs from the dispatch"))
    if record["isolation"]["saw_prior_conversation"]:
        out.append(_p("prior_conversation", "the filter agent saw a prior conversation"))
    if record["reviewer"]["identity"].strip() == ctx.get("author"):
        out.append(_p("same_identity", "the filter agent's identity is the author's"))
    files = ctx.get("files", {})
    bad_read = [f"{p['path']} ({files[p['path']]['forbidden']})" for p in record["paths_read"]
                if (files.get(p["path"]) or {}).get("forbidden")]
    if bad_read:
        out.append(_p("read_outside_packet", f"forbidden paths read: {bad_read}"))
    wrong = [p["path"] for p in record["paths_read"] if (files.get(p["path"]) or {}).get("sha256") != p["sha256"]]
    if wrong:
        out.append(_p("file_hash_mismatch", f"whole-file sha256 differs or file missing: {sorted(set(wrong))}"))
    if ctx.get("instructions_changed"):
        out.append(_p("instructions_changed", "instruction files or settings changed during the attempt"))
    ids = set(ctx["finding_ids"])
    got = {x["finding_id"] for x in record["decisions"]}
    if ids - got:
        out.append(_p("decisions_incomplete", f"findings without a decision: {sorted(ids - got)}"))
    if got - ids:
        out.append(_p("decisions_incomplete", f"decisions for ids not in findings.json: {sorted(got - ids)}"))
    return _dedupe(out)


def filter_metrics(record: dict) -> dict:
    ds = record.get("decisions", [])
    return {"kept": sum(1 for d in ds if d["decision"] == "keep"), "dropped": sum(1 for d in ds if d["decision"] == "drop"),
            "duplicates": sum(1 for d in ds if d.get("duplicate_of"))}


def sidecar_name(st: dict, r: int, sid: str) -> str:
    """The record file of an attempt folder: filter_record.json for the filter slot, else review_record.json."""
    return FILTER_SIDECAR if (r, sid) in st.get("filter_slots", {}) else SIDECAR


def filter_pool(st: dict) -> list[str]:
    """The findings the filtering pass judges: every accepted round-1 finding except the control findings closed as
    auto-canary (they quote mutated text the filter's copy of the document does not contain)."""
    return sorted(g for g, f in st["findings"].items()
                  if f["round"] == 1 and not any(x["disposition"] == "auto-canary" for x in f["disposals"]))


def filter_needed(st: dict) -> bool:
    """Spec 6.9: round 1, the configuration names a filter model, no filter slot yet, and at least one finding."""
    rd = st["rounds"].get(st["round"], {})
    return bool(effective_config(rd.get("config", {})).get("filter")) and st["round"] == 1 and st.get("filter") is None \
        and bool(filter_pool(st))


def _basis_counts(record):
    out = {"independent": 0, "external": 0, "internal": 0, "tool-output": 0}
    for e in record.get("evidence", []):
        out[basis_class(e)] += 1
        if e.get("basis") == "tool-output":
            out["tool-output"] += 1
    return out


# --- event log (sections 3, 5.4) -------------------------------------------------------------------------------------

def make_event(prev: dict | None, event: str, time: str, data: dict) -> dict:
    return {"seq": 0 if prev is None else prev["seq"] + 1,
            "prev_sha256": ZERO if prev is None else canonical_sha256(prev),
            "event": event, "time": time, "data": data}


def make_head(review_id: str, events: list) -> dict:
    return {"head_version": REVIEW_VERSION, "review_id": review_id, "count": len(events),
            "last_sha256": canonical_sha256(events[-1])}


def parse_log(data: bytes) -> list:
    """Records of a log file; a ValueError for an empty file, an unterminated line or a line that is not JSON."""
    if not data:
        raise ValueError("empty log")
    if not data.endswith(b"\n"):
        raise ValueError("unterminated last line")
    return [json.loads(line) for line in data.decode("utf-8").split("\n")[:-1]]


def event_problems(rec) -> list[str]:
    errs = validate(rec, "review_event.json").errors
    if errs:
        return [f"{e.path}: {e.message}" for e in errs]
    out = [f"data.{k}: missing" for k in EVENT_FIELDS[rec["event"]] if k not in rec["data"]]
    if rec["event"] == "observed" and not out:
        out += [f"data{e.path[1:]}: {e.message}" for e in validate(rec["data"], "review_observation.json").errors]
    return out


def verify_log(records: list, head) -> list[str]:
    """Problems of the hash chain, the event fields, the head and the transitions (empty: trusted)."""
    out = []
    prev = None
    for i, rec in enumerate(records):
        probs = event_problems(rec) if isinstance(rec, dict) else ["not an object"]
        if probs:
            out.append(f"line {i + 1}: {probs[0]}")
            break
        if rec["seq"] != i or rec["prev_sha256"] != (ZERO if prev is None else canonical_sha256(prev)):
            out.append(f"line {i + 1}: chain broken (seq or prev_sha256)")
            break
        t_now = parse_time(rec["time"])
        t_prev: datetime.datetime | None = parse_time(prev["time"]) if prev is not None else None
        if t_now and t_prev and t_now < t_prev:
            out.append(f"line {i + 1}: time goes backwards")
            break
        prev = rec
    if not records:
        out.append("no events")
    if not out:
        if validate(head, "review_head.json").errors:
            out.append("head does not match review_head.json")
        elif head["count"] != len(records) or head["last_sha256"] != canonical_sha256(records[-1]) \
                or head["review_id"] != records[0]["data"].get("review_id"):
            out.append("head does not match the log (count, last_sha256 or review_id)")
        else:
            out += transition_problems(records)
    return out


def transition_problems(records: list) -> list[str]:
    """Event order rules: round_started first; attempts numbered from 1 within the configured maximum; an outcome only
    for a dispatched attempt and at most one; late only after withdrawn; no event after a terminal one."""
    out: list[str] = []
    if records[0]["event"] != "round_started":
        return ["the first event is not round_started"]
    max_att = None
    rounds: set = set()
    slots: set = set()
    atts: dict[tuple, dict] = {}
    items: set = set()
    findings: set = set()
    filter_slots: set = set()
    for rec in records:
        e, d, s = rec["event"], rec["data"], rec["seq"]
        if out:
            break
        if e in TERMINAL and rec is not records[-1]:
            out.append(f"seq {s}: events after {e}")
        if e == "round_started":
            rounds.add(d["round"])
            max_att = int(effective_config(d["config"])["max_attempts_per_slot"])
            slots |= {(d["round"], x["slot_id"]) for x in d["slots"]}
        elif e == "arbitration_needed":
            slots.add((d["round"], d["slot_id"]))
            items.add(d["item_id"])
        elif e == "filter_needed":
            if filter_slots:
                out.append(f"seq {s}: a second filter_needed")
            slots.add((d["round"], d["slot_id"]))
            filter_slots.add((d["round"], d["slot_id"]))
        elif e == "dispatched":
            key = (d["round"], d["slot_id"])
            if key not in slots:
                out.append(f"seq {s}: dispatched for unknown slot {key}")
            prev = atts.get(key, {})
            limit = min(FILTER_MAX_ATTEMPTS, max_att or 0) if key in filter_slots else max_att
            if d["attempt"] != len(prev) + 1 or d["attempt"] > limit or (prev and prev[max(prev)] is None):
                out.append(f"seq {s}: attempt {d['attempt']} out of order for {key}")
            atts.setdefault(key, {})[d["attempt"]] = None
        elif e in ("returned", "accepted", "rejected", "withdrawn", "late"):
            st = atts.get((d["round"], d["slot_id"]), {})
            if d["attempt"] not in st:
                out.append(f"seq {s}: {e} for an attempt never dispatched")
            elif e == "late":
                if st[d["attempt"]] != "withdrawn":
                    out.append(f"seq {s}: late for an attempt that was not withdrawn")
            elif e != "returned":
                if st[d["attempt"]] is not None:
                    out.append(f"seq {s}: second outcome for one attempt")
                st[d["attempt"]] = e
                if e == "accepted":
                    for f in d.get("findings", []):
                        findings.add(f"{d['round']}/{d['slot_id']}/{f['id']}")
        elif e in ("disposed", "change_confirmed", "change_rejected", "change_reverted"):
            if d["finding"] not in findings:
                out.append(f"seq {s}: {e} for unknown finding {d['finding']}")
        elif e == "arbitration_resolved" and d["item_id"] not in items:
            out.append(f"seq {s}: resolution of unknown item {d['item_id']}")
    return out


# --- state (sections 6.2-6.4) ----------------------------------------------------------------------------------------

def _gid(r, sid, local):
    return f"{r}/{sid}/{local}"


def fold(events: list) -> dict:
    """The review state the events describe."""
    st: dict[str, Any] = {"review_id": None, "document": None, "rounds": {}, "round": 0, "attempts": {}, "arb_slots": {},
          "observed": None, "findings": {}, "verdicts": {}, "items": {}, "escalations": [], "human": {},
          "terminal": None, "author": None, "extra_rounds": 0, "accept_round_limit": False, "resolved_slots": set(),
          "late": [], "reported": [], "human_seq": {}, "filter_slots": {}, "filter": None}
    F, V = st["findings"], st["verdicts"]
    for ev in events:
        e, d = ev["event"], ev["data"]
        if e == "round_started":
            r = d["round"]
            st["round"] = r
            st["review_id"], st["document"], st["author"] = d["review_id"], d["document"], d["author"]
            st["rounds"][r] = d
            for g in d.get("removed_findings", []):
                if g in F:
                    F[g]["state"] = "removed-pending"
            for items in d.get("carry_forward", {}).values():
                for c in items:
                    if c["kind"] == "finding" and c["target"] in F:
                        F[c["target"]]["units_now"] = c["units"]
        elif e == "observed":
            st["observed"] = d
        elif e == "dispatched":
            st["attempts"].setdefault((d["round"], d["slot_id"]), {})[d["attempt"]] = {
                "dispatched": d, "returned": False, "outcome": None, "data": None}
        elif e in ("returned", "accepted", "rejected", "withdrawn"):
            a = st["attempts"].get((d["round"], d["slot_id"]), {}).get(d["attempt"])
            if a is None:
                continue
            if e == "returned":
                a["returned"] = True
                continue
            a["outcome"], a["data"] = e, d
            if e == "accepted" and (d["round"], d["slot_id"]) in st["filter_slots"]:
                if st["filter"] is not None:
                    st["filter"]["decisions"] = d.get("decisions")
            elif e == "accepted" and (d["round"], d["slot_id"]) not in st["arb_slots"]:
                r, sid = d["round"], d["slot_id"]
                for f in d.get("findings", []):
                    F[_gid(r, sid, f["id"])] = {"round": r, "slot": sid, "severity": f["severity"], "units": f["units"],
                                                "state": "open", "upheld": False, "changed_round": None,
                                                "disposals": []}
                for v in d.get("verdicts", []):
                    V[_gid(r, sid, v["claim_id"])] = {"round": r, "slot": sid, "units": v["units"],
                                                      "verdict": v["verdict"], "eligible": v.get("eligible", True),
                                                      "findings": [_gid(r, sid, x) for x in v.get("finding_ids", [])],
                                                      "won": 0, "lost": 0, "superseded": False}
        elif e == "late":
            st["late"].append(d)
        elif e == "disposed":
            f = F.get(d["finding"])
            if f is None:
                continue
            f["disposals"].append(d)
            how = d["disposition"]
            if f["state"] == "removed-pending":
                f["state"] = "closed"
            elif how in ("changed", "partially-changed"):
                if set(d["edited_units"]) & set(d["finding_units"]):
                    f["state"], f["changed_round"] = "changed", d["round"]
            elif how == "unresolved":
                f["state"] = "unresolved"
            elif how == "declined":
                f["state"] = "declined-pending" if f["severity"] == "high" else "closed"
            elif how == "auto-canary":
                f["state"] = "closed"
        elif e == "change_confirmed":
            if d["finding"] in F:
                F[d["finding"]]["state"] = "change-confirmed"
        elif e in ("change_rejected", "change_reverted"):
            if d["finding"] in F:
                F[d["finding"]]["state"] = "reopened"
        elif e == "filter_needed":
            st["filter_slots"][(d["round"], d["slot_id"])] = d["model"]
            st["filter"] = dict(d, decisions=None)
        elif e == "arbitration_needed":
            st["items"][d["item_id"]] = dict(d, state="dispatched", conclusion=None)
            st["arb_slots"][(d["round"], d["slot_id"])] = d["item_id"]
        elif e == "arbitration_resolved":
            it = st["items"].get(d["item_id"])
            if it is not None:
                _apply_conclusion(st, it, d["conclusion"])
        elif e == "escalated":
            st["escalations"].append({"seq": ev["seq"], "items": list(d["items"]), "reported": False})
        elif e == "reported":
            st["reported"].append(ev["seq"])
            if st["escalations"]:
                st["escalations"][-1]["reported"] = True
        elif e == "human_resolved":
            _apply_human(st, d, ev["seq"])
        elif e in TERMINAL:
            st["terminal"] = e
    return st


def _apply_conclusion(st, it, conclusion):
    F, V = st["findings"], st["verdicts"]
    it["conclusion"] = conclusion
    if conclusion == "unresolved":
        it["state"] = "unresolved"
        return
    it["state"] = "resolved"
    if it["type"] == "decline":
        f = F.get(it["finding"])
        if f is not None:
            if conclusion == "uphold-finding":
                f["state"], f["upheld"] = "reopened", True
            else:
                f["state"] = "closed"
        return
    win, lose = (it["first"], it["second"]) if conclusion == "uphold-first" else (it["second"], it["first"])
    if win in V:
        V[win]["won"] += 1
    if lose in V:
        V[lose]["lost"] += 1
        V[lose]["superseded"] = True
        for g in V[lose]["findings"]:
            if g in F:
                F[g]["state"] = "closed"
                F[g]["closed_by"] = "superseded-by-arbitration"


def _apply_human(st, d, seq: int = 0):
    ref, dec = d["item"], d["decision"]
    st["human"][ref] = dec
    st["human_seq"][ref] = seq
    kind, _, key = ref.partition(":")
    if kind == "finding" and key in st["findings"]:
        st["findings"][key]["state"] = "closed" if dec == "close" else "reopened"
    elif kind == "item" and key in st["items"]:
        _apply_conclusion(st, st["items"][key], dec)
    elif kind == "slot":
        st["resolved_slots"].add(key)
    elif kind == "verdict" and key in st["verdicts"]:
        v = st["verdicts"][key]
        v["superseded"] = dec == "supersede"
        if v["superseded"]:
            for g in v["findings"]:
                if g in st["findings"]:
                    st["findings"][g]["state"] = "closed"
    elif ref == "round-limit":
        if dec == "extend":
            st["extra_rounds"] += 1
        else:
            st["accept_round_limit"] = True


def slot_state(st: dict, r: int, sid: str) -> dict:
    """Section 6.2: the state of a slot's latest attempt."""
    cfg = effective_config(st["rounds"][r]["config"]) if r in st["rounds"] else effective_config({})
    max_att = int(cfg["max_attempts_per_slot"])
    if (r, sid) in st.get("filter_slots", {}):
        max_att = min(FILTER_MAX_ATTEMPTS, max_att)
    atts = st["attempts"].get((r, sid), {})
    if not atts:
        return {"state": "none", "attempt": 0, "deadline": None}
    k = max(atts)
    a = atts[k]
    out = {"attempt": k, "deadline": a["dispatched"]["deadline"]}
    if a["outcome"] in ("rejected", "withdrawn"):
        return dict(out, state="exhausted" if k >= max_att else a["outcome"])
    if a["outcome"] == "accepted":
        return dict(out, state="accepted")
    obs = st["observed"] or {}
    side = obs.get("sidecars", {}).get(f"{r}/{sid}/{k}", {})
    if side.get("exists") and not side.get("tmp"):
        return dict(out, state="submitted")
    if a["returned"]:
        return dict(out, state="returned-empty")
    t, dl = parse_time(obs.get("time")), parse_time(a["dispatched"]["deadline"])
    if t and dl and t > dl:
        return dict(out, state="overdue")
    return dict(out, state="dispatched")


def needed_items(st: dict) -> list[dict]:
    """Section 6.6: arbitration items whose conditions hold but have no arbitration_needed yet, in a fixed order."""
    r = st["round"]
    have = set()
    for it in st["items"].values():
        have.add(("decline", it["finding"]) if it["type"] == "decline" else ("conflict", it["first"], it["second"]))
    out = []
    vs = sorted((g, v) for g, v in st["verdicts"].items() if v["round"] == r and v["eligible"] and not v["superseded"])
    for (g1, v1), (g2, v2) in itertools.combinations(vs, 2):
        if {v1["verdict"], v2["verdict"]} == {"supported", "unsupported"} and set(v1["units"]) & set(v2["units"]):
            first, second = sorted([g1, g2], key=lambda g: (g.split("/")[1], g.split("/", 2)[2]))
            if ("conflict", first, second) not in have:
                out.append({"type": "conflict", "first": first, "second": second, "finding": None})
    for g, f in sorted(st["findings"].items()):
        if f["state"] == "declined-pending" and ("decline", g) not in have:
            out.append({"type": "decline", "first": None, "second": None, "finding": g})
    return out


def double_outcome_verdicts(st: dict) -> list[str]:
    return sorted(g for g, v in st["verdicts"].items() if v["won"] and v["lost"] and f"verdict:{g}" not in st["human"])


def snapshot(st: dict, log_ok: bool = True) -> dict:
    """The abstract state decide() reads: slot, item and finding states, and the escalation, repair and document
    facts (sections 6.2-6.5)."""
    r = st["round"]
    rd = st["rounds"].get(r, {})
    cfg = effective_config(rd.get("config", {}))
    slots = {}
    for s in rd.get("slots", []):
        slots[s["slot_id"]] = dict(slot_state(st, r, s["slot_id"]), kind="review",
                                   resolved=f"slot:{r}/{s['slot_id']}" in st["human"])
    for (rr, sid) in st["arb_slots"]:
        if rr == r:
            slots[sid] = dict(slot_state(st, r, sid), kind="arbiter", resolved=False)
    for (rr, sid) in st.get("filter_slots", {}):
        if rr == r:
            slots[sid] = dict(slot_state(st, r, sid), kind="filter", resolved=False)
    items = {}
    for iid, it in st["items"].items():
        state = it["state"]
        sl = slots.get(it["slot_id"]) if it["round"] == r else None
        if state == "dispatched" and sl and sl["state"] == "exhausted":
            state = "unresolved"
        if state == "unresolved" and f"item:{iid}" in st["human"]:
            state = "resolved"
        items[iid] = state
    esc = None
    if st["escalations"]:
        last = st["escalations"][-1]
        pending = [x for x in last["items"] if st["human_seq"].get(x, -1) < last["seq"]]  # resolved after this escalation
        if pending:
            esc = {"pending": pending, "reported": last["reported"]}
    obs = st["observed"] or {}
    return {"log_ok": log_ok, "terminal": st["terminal"], "escalation": esc, "repair": list(obs.get("repair", [])),
            "slots": slots, "items": items, "needed": needed_items(st),
            "findings": {g: f["state"] for g, f in st["findings"].items()},
            "double_verdicts": double_outcome_verdicts(st),
            "doc_differs": bool(obs) and obs.get("document_sha256") != rd.get("source_sha256"),
            "round": r, "round_limit": int(cfg["max_rounds"]) + st["extra_rounds"],
            "accept_round_limit": st["accept_round_limit"], "filter_needed": filter_needed(st)}


# --- decide (section 6.5) --------------------------------------------------------------------------------------------

DISPOSE_STATES = ("open", "reopened", "removed-pending")


def escalation_items(snap: dict) -> list[str]:
    """What an escalate action hands to a human, from the rule that asked for it (rows 9, 11, 13)."""
    review = {k: v for k, v in snap["slots"].items() if v["kind"] == "review"}
    ex = [f"slot:{snap['round']}/{k}" for k, v in sorted(review.items()) if v["state"] == "exhausted" and not v["resolved"]]
    if ex:
        return ex
    out = [f"item:{k}" for k, v in sorted(snap["items"].items()) if v == "unresolved"]
    out += [f"finding:{g}" for g, s in sorted(snap["findings"].items()) if s == "unresolved"]
    out += [f"verdict:{g}" for g in snap["double_verdicts"]]
    return out or ["round-limit"]


def decide(snap: dict) -> dict:
    """The next action: the first row of the decision table whose condition holds (exactly one, in priority order)."""
    if not snap["log_ok"]:
        return {"row": 1, "action": "stop", "reason": "error: the event log or head fails verification"}
    if snap["terminal"]:
        return {"row": 2, "action": "stop", "reason": f"the review is {snap['terminal']}"}
    if snap["escalation"]:
        if not snap["escalation"]["reported"]:
            return {"row": 2, "action": "report", "reason": "escalated; produce the report for the human"}
        return {"row": 2, "action": "stop", "reason": "waiting for a human: resolve " + ", ".join(snap["escalation"]["pending"])}
    if snap["repair"]:
        return {"row": 3, "action": "repair", "codes": sorted(snap["repair"])}
    slots = snap["slots"]

    def having(*states):
        return sorted((k for k, v in slots.items() if v["state"] in states), key=_slot_order)

    if having("submitted"):
        return {"row": 4, "action": "receive", "slots": having("submitted")}
    if having("returned-empty"):
        return {"row": 5, "action": "withdraw", "reason": "host-failure", "slots": having("returned-empty")}
    if having("overdue"):
        return {"row": 6, "action": "withdraw", "reason": "timeout", "slots": having("overdue")}
    if having("none", "rejected", "withdrawn"):
        return {"row": 7, "action": "dispatch", "slots": having("none", "rejected", "withdrawn")}
    if having("dispatched"):
        dl = sorted(v["deadline"] for v in slots.values() if v["state"] == "dispatched")
        return {"row": 8, "action": "await", "deadline": dl[0], "slots": having("dispatched")}
    if snap.get("filter_needed"):  # row 8a (contracts 3.4.0): only with a filter in the configuration
        return {"row": "8a", "action": "filter"}
    review = {k: v for k, v in slots.items() if v["kind"] == "review"}
    if any(v["state"] == "exhausted" and not v["resolved"] for v in review.values()):
        return {"row": 9, "action": "escalate", "items": escalation_items(snap)}
    if all(v["state"] == "accepted" or v["resolved"] for v in review.values()) and snap["needed"]:
        return {"row": 10, "action": "arbitrate", "items": snap["needed"]}
    if any(v == "unresolved" for v in snap["items"].values()) or "unresolved" in snap["findings"].values() \
            or snap["double_verdicts"]:
        return {"row": 11, "action": "escalate", "items": escalation_items(snap)}
    disp = sorted(g for g, s in snap["findings"].items() if s in DISPOSE_STATES)
    if disp:
        return {"row": 12, "action": "dispose", "findings": disp}
    if snap["doc_differs"] and not snap["accept_round_limit"]:
        if snap["round"] < snap["round_limit"]:
            return {"row": 13, "action": "rereview"}
        return {"row": 13, "action": "escalate", "items": ["round-limit"]}
    return {"row": 14, "action": "close"}


def _slot_order(sid: str):
    m = re.fullmatch(r"S(\d+)", sid)
    return (0, int(m.group(1)), sid) if m else (1, 0, sid)


def carry_forward_plan(st: dict, mapping: dict, slot_roles: dict, new_lens_slot: dict) -> tuple[dict, list]:
    """A4: per new lens slot, the carry_forward items: that lens's non-canary verdicts of the previous round and every
    finding of that lens (main or shadow slot) in state changed, renumbered through the mapping; plus the changed
    findings whose units were all removed, which go to dispose instead (A4.3). slot_roles maps each round (as a string)
    to its slots {slot_id: {role, lens}} (slot ids are reassigned every round); new_lens_slot maps a lens to its main
    slot in the new round."""
    r = st["round"]
    old_to_new = {a: b for a, b in mapping.get("unchanged", []) + mapping.get("changed", [])}
    plan: dict[str, list] = {sid: [] for sid in sorted(new_lens_slot.values())}
    removed: list[str] = []
    n = 0
    for g, v in sorted(st["verdicts"].items()):
        info = slot_roles.get(str(v["round"]), {}).get(v["slot"], {})
        if v["round"] != r or info.get("role") != "lens" or not v["eligible"] or v["superseded"]:
            continue
        units = [old_to_new[u] for u in v["units"] if u in old_to_new]
        if units and info["lens"] in new_lens_slot:
            n += 1
            plan[new_lens_slot[info["lens"]]].append({"ref": f"CF{n}", "kind": "verdict", "target": g, "units": units})
    for g, f in sorted(st["findings"].items()):
        if f["state"] != "changed":
            continue
        units = [old_to_new[u] for u in f.get("units_now") or f["units"] if u in old_to_new]
        tgt = new_lens_slot.get(slot_roles.get(str(f["round"]), {}).get(f["slot"], {}).get("lens") or f.get("lens"))
        if not units or tgt is None:
            removed.append(g)
            continue
        n += 1
        plan[tgt].append({"ref": f"CF{n}", "kind": "finding", "target": g, "units": units})
    return plan, removed


# --- overall check (section 7.4) -------------------------------------------------------------------------------------

def load_review(review_dir: Path) -> tuple[list, dict | None, list[str]]:
    """(events, head, problems) of a review directory; problems are log_broken reasons."""
    try:
        events = parse_log((review_dir / "review_log.jsonl").read_bytes())
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return [], None, [f"review_log.jsonl: {exc}"]
    try:
        head = json.loads((review_dir / "review_head.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return events, None, [f"review_head.json: {exc}"]
    return events, head, verify_log(events, head)


def check(review_dir, project: Path | None = None) -> dict:
    """Section 7.4 on a review directory; reads files only."""
    review_dir = Path(review_dir).resolve()
    project = Path(project).resolve() if project else review_dir.parents[1]
    events, head, problems = load_review(review_dir)
    codes = []

    def add(code, detail):
        codes.append({"code": code, "result": CHECK_CODES[code], "detail": detail})

    if problems:
        add("log_broken", problems)
        return _check_result(codes, {})
    st = fold(events)
    rd = st["rounds"][st["round"]]
    doc = project / st["document"]
    if st["terminal"] != "closed":
        add("not_closed", f"the review is not closed (round {st['round']})")
    else:
        closed = [e for e in events if e["event"] == "closed"][-1]["data"]
        if sha256_file(doc) != closed["document_sha256"]:
            add("changed_after_close", f"{st['document']} changed after close")
    changed = []
    for r, rnd in st["rounds"].items():
        if sha256_file(review_dir / "units" / f"round-{r}.json") != rnd["units_sha256"]:
            changed.append(f"units/round-{r}.json")
    for (r, sid), atts in st["attempts"].items():
        for k, a in atts.items():
            adir = review_dir / f"round-{r}" / sid / f"attempt-{k}"
            changed += _packet_changes(adir, a["dispatched"]["packet_sha256"])
            name = sidecar_name(st, r, sid)
            if a["outcome"] in ("accepted", "rejected") and sha256_file(adir / name) != a["data"]["review_sha256"]:
                changed.append(f"{adir.relative_to(review_dir)}/{name}")
    if changed:
        add("artifacts_changed", changed)
    open_f = sorted(g for g, f in st["findings"].items() if f["state"] in ("open", "reopened", "declined-pending",
                                                                           "removed-pending"))
    if open_f:
        add("finding_open", open_f)
    upheld = {g for g, f in st["findings"].items() if f["upheld"]}
    bad = sorted({e["data"]["finding"] for e in events if e["event"] == "disposed" and e["data"]["finding"] in upheld
                  and e["data"]["disposition"] == "declined" and _after_uphold(events, e)})
    if bad:
        add("uphold_not_honored", bad)
    unver = sorted(e["data"]["finding"] for e in events if e["event"] == "disposed"
                   and (e["data"].get("verification") or {}).get("adopted_unverified"))
    if unver:
        add("adopted_unverified", unver)
    models = [s["model"] for rnd in st["rounds"].values() for s in rnd["slots"]]
    models += [it["model"] for it in st["items"].values()]
    author_model = (st["author"] or {}).get("model")
    if models and (len(set(models)) == 1 or all(m == author_model for m in models)):
        add("no_model_diversity", sorted(set(models)))
    short, none_ = [], []
    for (r, sid), atts in sorted(st["attempts"].items()):
        d = atts[max(atts)]["dispatched"]
        if d["canaries_expected"]:
            if d["canaries"] == 0:
                none_.append(f"{r}/{sid}")
            elif d["canaries"] < d["canaries_expected"]:
                short.append(f"{r}/{sid}")
    if short:
        add("canary_shortfall", short)
    if none_:
        add("no_control", none_)
    weak = weak_config(rd["config"])
    if weak:
        add("weak_config", weak)
    others = []
    reviews = review_dir.parent
    for other in sorted(p for p in reviews.iterdir() if p.is_dir() and p != review_dir):
        try:
            first = json.loads((other / "review_log.jsonl").read_text(encoding="utf-8").split("\n", 1)[0])
        except (OSError, ValueError):
            continue
        if first.get("data", {}).get("document") == st["document"]:
            others.append(other.name)
    if others:
        add("superseded_reviews", others)
    if st["late"]:
        add("late_records", [f"{d['round']}/{d['slot_id']}/{d['attempt']}" for d in st["late"]])
    return _check_result(codes, {"review_id": st["review_id"], "round": st["round"], "state": st["terminal"] or "open"})


def _after_uphold(events, disposed_ev):
    g = disposed_ev["data"]["finding"]
    ups = [e["seq"] for e in events if e["event"] == "arbitration_resolved" and e["data"]["conclusion"] == "uphold-finding"]
    items = {e["data"]["item_id"]: e["data"].get("finding") for e in events if e["event"] == "arbitration_needed"}
    ups = [e["seq"] for e in events if e["event"] == "arbitration_resolved"
           and e["data"]["conclusion"] == "uphold-finding" and items.get(e["data"]["item_id"]) == g]
    return any(s < disposed_ev["seq"] for s in ups)


def _packet_changes(adir: Path, packet_sha: str) -> list[str]:
    pdir = adir / "packet"
    rel = f"{adir.parent.parent.name}/{adir.parent.name}/{adir.name}/packet"
    if sha256_file(pdir / "manifest.json") != packet_sha:
        return [f"{rel}/manifest.json"]
    try:
        man = json.loads((pdir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [f"{rel}/manifest.json"]
    return [f"{rel}/{f['name']}" for f in man.get("files", []) if sha256_file(pdir / f["name"]) != f["sha256"]]


def _check_result(codes, info) -> dict:
    results = {c["result"] for c in codes}
    status = "fail" if "fail" in results else "incomplete" if "incomplete" in results else "ok"
    return dict(info, status=status, codes=codes)


# --- command line ----------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check", help="overall check of a review directory, or --record-only on one record")
    p.add_argument("target", type=Path, help="the review directory, or with --record-only the record file")
    p.add_argument("--record-only", action="store_true")
    p.add_argument("--role", choices=("reviewer", "arbiter", "filter"))
    p.add_argument("--max-units-per-claim", type=int, default=CONFIG_RULES["max_units_per_claim"][0])
    p.add_argument("--project", type=Path, help="project root (default: two levels above the review directory)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.record_only:
        try:
            record = json.loads(args.target.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            print(json.dumps({"status": "error", "error": f"unreadable record: {exc}"}))
            return 2
        probs = filter_record_rules(record) if args.role == "filter" or (isinstance(record, dict) and record.get(
            "role") == "filter" and not args.role) else record_rules(record, args.role, args.max_units_per_claim)
        print(json.dumps({"status": "fail" if probs else "ok",
                          "problems": [{"code": c, "message": m} for c, m in probs]}, indent=1, ensure_ascii=False))
        return 1 if probs else 0
    if not (args.target / "review_log.jsonl").is_file():
        print(json.dumps({"status": "error", "error": f"no review_log.jsonl in {args.target}"}))
        return 2
    res = check(args.target, args.project)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    return {"ok": 0, "fail": 1, "incomplete": 3}[res["status"]]


if __name__ == "__main__":
    sys.exit(main())
