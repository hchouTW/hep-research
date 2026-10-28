"""hep-review kernel (pure; protocol hep-review/0, schema 0.x, experimental): strict JSON and the metadata encoding.

Specification: docs/dev/hep-review/ (task file and hep-review spec v9). This module is pure: no file, database,
network or clock access, and no import of a skill. Callers pass bytes and already-loaded objects.

Sections:
- strict JSON ingestion (spec 10.2) and the hep-review-metadata/1 encoding (spec 10.3);
- references, legacy native hashes and object rules: creation order, self-reference (spec 6.4, 10.4);
- plan admission: required obligations, decision_required, the downgrade list and obligation_map (spec 6.3, 8.1, 8.2);
- validate(bundle, version): structure, bindings, dependencies and disposition (spec 7.3);
- project(validated, version): the layer-1 projection: closures and carry-over (8.3), finding states (7.2),
  outcomes (7.1), flags and coverage (7.4), facets (7.7), per-obligation tiers and the R2 floor (4.2-4.3),
  claim binding (15.6), summary_eligible (7.5);
- decide_summary (the layer-2 combination rule of 7.5; the attestation inputs come from the I/O layer),
  render_report and check_historical (7.3, 7.6).

Nothing here claims scientific validity: outcomes are projections of committed records under stated conditions.
"""
from __future__ import annotations

import copy
import decimal
import hashlib
import json
import re
from collections.abc import Callable
from typing import Any

PROTOCOL = "hep-review/0"
SCHEMA_VERSION = "0.1.0"
METADATA_PROFILE = "hep-review-metadata/1"
RAW_PROFILE = "raw-bytes/1"

# ---------------------------------------------------------------------------------------------------------------------
# Strict JSON (spec 10.2) and the unique byte encoding (spec 10.3)
# ---------------------------------------------------------------------------------------------------------------------

SAFE_INT = 2 ** 53 - 1
DEFAULT_MAX_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_DEPTH = 64
KEY_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*\Z")  # ASCII schema names (condition names use hyphens)


class IngestError(ValueError):
    """Strict ingestion refused the input; `code` says why (json.*)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class EncodeError(ValueError):
    """A value outside the restricted domain of hep-review-metadata/1."""


def is_int(x: Any) -> bool:
    """An integer that is not a bool (spec 10.2: type checks use type(x) is int)."""
    return type(x) is int


def _max_depth(text: str) -> int:
    """Maximum nesting depth of [ and {, skipping string contents; non-recursive."""
    depth = best = 0
    in_str = esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
            if depth > best:
                best = depth
        elif ch in "]}":
            depth -= 1
    return best


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    seen: set[str] = set()
    for k, _ in pairs:
        if k in seen:
            raise IngestError("json.duplicate_key", f"duplicate key {k!r} (after decoding escapes)")
        seen.add(k)
        if not KEY_NAME.match(k):
            raise IngestError("json.key_name", f"key {k!r} is not an ASCII name")
    return dict(pairs)


def _int(token: str) -> int:
    if token == "-0":
        raise IngestError("json.minus_zero", "the integer -0 is not allowed")
    if len(token.lstrip("-")) > 16:  # longer than 2^53-1 (16 digits); never hand int() a huge token
        raise IngestError("json.int_range", f"integer token of {len(token)} characters is outside +-(2^53-1)")
    value = int(token)
    if not -SAFE_INT <= value <= SAFE_INT:
        raise IngestError("json.int_range", f"integer {token} is outside +-(2^53-1)")
    return value


def _float(token: str):
    raise IngestError("json.float", f"floating-point number {token} is not allowed; use a decimal string")


def _constant(token: str):
    raise IngestError("json.constant", f"{token} is not allowed")


def _check_strings(value: Any) -> None:
    stack = [value]
    while stack:
        v = stack.pop()
        if isinstance(v, str):
            if any(0xD800 <= ord(c) <= 0xDFFF for c in v):
                raise IngestError("json.lone_surrogate", "a string contains a lone surrogate")
        elif isinstance(v, dict):
            stack.extend(v.values())  # keys are ASCII names, checked in _pairs
        elif isinstance(v, list):
            stack.extend(v)


def ingest_json(raw: bytes, *, max_bytes: int = DEFAULT_MAX_BYTES, max_depth: int = DEFAULT_MAX_DEPTH) -> Any:
    """Parse metadata strictly (spec 10.2). Raises IngestError; never returns a value it would have to correct."""
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("ingest_json takes bytes; never decoded text from an unknown source")
    if len(raw) > max_bytes:
        raise IngestError("json.too_large", f"{len(raw)} bytes > limit {max_bytes}")
    try:
        text = bytes(raw).decode("utf-8")  # strict: rejects invalid UTF-8 and encoded surrogates
    except UnicodeDecodeError as e:
        raise IngestError("json.encoding", f"not UTF-8: {e.reason}") from None
    if text.startswith("﻿"):
        raise IngestError("json.bom", "a byte order mark is not allowed")
    if _max_depth(text) > max_depth:
        raise IngestError("json.too_deep", f"nesting deeper than {max_depth}")
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_int, parse_float=_float,
                           parse_constant=_constant)
    except IngestError:
        raise
    except RecursionError:
        raise IngestError("json.too_deep", "nesting too deep") from None
    except json.JSONDecodeError as e:
        raise IngestError("json.syntax", e.msg) from None
    _check_strings(value)
    return value


def _check_domain(value: Any, depth: int = 0) -> None:
    if depth > 256:
        raise EncodeError("value nested too deeply")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if not -SAFE_INT <= value <= SAFE_INT:
            raise EncodeError(f"integer {value} outside +-(2^53-1)")
        return
    if type(value) is str:
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise EncodeError("lone surrogate in a string")
        return
    if type(value) is list:
        for v in value:
            _check_domain(v, depth + 1)
        return
    if type(value) is dict:
        for k, v in value.items():
            if type(k) is not str or not KEY_NAME.match(k):
                raise EncodeError(f"key {k!r} is not an ASCII name")
            _check_domain(v, depth + 1)
        return
    raise EncodeError(f"{type(value).__name__} is outside the metadata value domain")


def encode(value: Any) -> bytes:
    """The unique byte encoding of hep-review-metadata/1 (spec 10.3). Within the restricted domain, json.dumps with
    these settings writes exactly the specified bytes; the gold vectors in contracts/fixtures/hep_review/ are the
    authority, not this implementation."""
    _check_domain(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def metadata_digest(value: Any) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


def raw_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------------------------------------------------

TIERS = ("R0", "R1", "R2", "R3")
OUTCOMES = ("supported", "violated", "undetermined", "not-examined", "not-applicable")
METHOD_OBSERVATIONS = ("completed", "failed", "not-run")
FINDING_STATES = ("candidate", "supported", "disputed", "refuted", "retired-for-current")
BASES = ("observed", "declared", "self-reported", "advisory", "inferred", "unknown")
FLOOR = ("non-author", "fresh-context", "no-other-evaluations-seen")
FLOOR_BASES = {"non-author": {"observed", "declared"}, "fresh-context": {"observed"},
               "no-other-evaluations-seen": {"observed", "advisory"}}
EXTRA_CONDITION_BASES = {"observed", "declared"}
FIDELITIES = ("digest-bound", "file-transfer", "host-transcript", "transcribed", "mismatch")
FIDELITY_R2 = {"digest-bound", "file-transfer", "host-transcript"}
RECORD_TYPES = {"submission": "reviewer", "verification": "verifier", "adjudication": "arbiter", "response": "author"}
DISCHARGE_REFUSED = {"missing-data", "difficulty", "budget"}
# The applicability reasons a discharge may give; anything else (including missing data, difficulty or budget under
# another name) is refused (spec 7.1).
DISCHARGE_REASONS = ("condition-absent", "out-of-scope-by-intent", "superseded-by-other-obligation")
JUDGING_RECORD_TYPES = {"submission", "verification", "adjudication"}
CLAIM_STATES_R3 = {"pilot-checked-scope", "evaluated-scope"}
SCOPE_DONE = "performed-no-known-gaps"
KIND_ORDER = ("intent", "manifest", "plan", "packet", "assignment", "record", "claim-binding")
QUALIFIER = {"R1": "R1 (non-independent recorded review)",
             "R2": "R2 (independent review under the recorded conditions)",
             "R3": "R3 (review within the evaluated scope)"}
NO_DEFECT = "no still-valid defect was observed within the scope of this check"
ADVISORY_SENTENCE = ("The reviewer was instructed not to read other evaluations; this was neither observed nor "
                     "enforced.")
R0_SENTENCE = "R0: unrecorded, non-independent preliminary opinion; no no-defect summary is given at R0."
BUNDLE_KEYS = {"context_id", "segment_id", "mode", "commits", "as_of_seq", "as_of_commit_digest", "blob_checks"}


class BundleError(ValueError):
    """The bundle itself cannot be interpreted (unknown keys, broken chain, colliding ids)."""


class RenderError(ValueError):
    """render_report refuses: hand-filled content, a summary sentence without its tier qualifier, or a layer 1 that
    the bundle does not reproduce."""


def _err(code: str, message: str, path: str = "$") -> dict:
    return {"code": code, "path": path, "message": message}


# ---------------------------------------------------------------------------------------------------------------------
# References, legacy native hashes, object rules (spec 6.4, 10.1, 10.4)
# ---------------------------------------------------------------------------------------------------------------------

REF_FIELDS = ("logical_id", "algorithm", "hash_scope", "profile_id", "digest")

# Versioned adapters for native hashes of existing artifacts: the excluded fields are fixed here, never by a producer.
LEGACY_ADAPTERS = {
    "release-approval/1": {"digest_field": "manifest_sha256", "excluded_fields": ["approval_ref"],
                           "hash_scope": "native-canonical-object"},
    "dependencies-input/1": {"digest_field": "sha256", "excluded_fields": [], "hash_scope": "raw-file-bytes"},
    "verify-run/1": {"digest_field": "sha256", "excluded_fields": [], "hash_scope": "referenced-file-bytes"},
}


def object_ref(committed: dict) -> dict:
    """The metadata content_ref of a committed object; its digest lives here, never inside the object."""
    return {"logical_id": committed["id"], "algorithm": "sha256", "hash_scope": "metadata",
            "profile_id": METADATA_PROFILE, "digest": metadata_digest(committed)}


def same_ref(a: dict, b: dict) -> bool:
    """Two refs are the same only when every field agrees: the same digest string under another profile or scope is
    a different ref (case P04)."""
    return all(a.get(k) == b.get(k) for k in REF_FIELDS)


def legacy_ref(adapter: str, native: dict, *, logical_id: str) -> dict:
    """Wrap a native hash field by field (cases P03, P28); the native value and its profile are kept as they are."""
    if adapter not in LEGACY_ADAPTERS:
        raise ValueError(f"no registered legacy adapter {adapter!r}")
    a = LEGACY_ADAPTERS[adapter]
    return {"logical_id": logical_id, "algorithm": "sha256", "hash_scope": a["hash_scope"],
            "profile_id": f"legacy:{adapter}", "digest": native[a["digest_field"]], "native": copy.deepcopy(native),
            "excluded_fields": list(a["excluded_fields"])}


def _nested_refs(value: Any):
    stack = [value]
    while stack:
        v = stack.pop()
        if isinstance(v, dict):
            if "logical_id" in v and "digest" in v:
                yield v
            stack.extend(v.values())
        elif isinstance(v, list):
            stack.extend(v)


def check_object(committed: dict) -> list[dict]:
    """Version-independent object rules: header, creation order, no self-reference (spec 6.2, 6.4; cases A25, N05)."""
    errs: list[dict] = []
    kind = committed.get("record_kind")
    if kind == "report":
        return [_err("order.report_is_not_a_commit_input", "reports are derived and never committed")]
    if kind not in KIND_ORDER:
        errs.append(_err("object.kind", f"unknown record_kind {kind!r}"))
    for f in ("protocol", "schema_version", "id", "context_id"):
        if not isinstance(committed.get(f), str) or not committed.get(f):
            errs.append(_err("object.header", f"missing header field {f}", f"$.{f}"))
    if committed.get("protocol") not in (None, PROTOCOL):
        errs.append(_err("object.protocol", f"protocol must be {PROTOCOL}", "$.protocol"))
    for key in ("digest", "self_digest", "object_digest", "own_digest"):
        if key in committed:
            errs.append(_err("object.embedded_digest", "an object never carries its own digest", f"$.{key}"))
    for key in ("excluded_fields", "hash_exclude", "digest_excludes"):
        if key in committed:
            errs.append(_err("object.producer_excluded_fields", "producers cannot choose fields to exclude", f"$.{key}"))
    for r in _nested_refs(committed):
        if r.get("logical_id") == committed.get("id") and "native" not in r:
            errs.append(_err("object.self_reference", "an object references its own digest"))
            break
    if kind == "plan":
        for key in ("assignments", "assignment_ids", "assignment_refs"):
            if key in committed:
                errs.append(_err("order.plan_references_assignment", "a plan holds assignment_specs only", f"$.{key}"))
    if kind == "packet":
        for key in ("assignment_id", "assignment_ref", "assignment_ids"):
            if key in committed:
                errs.append(_err("order.packet_references_assignment", "packets do not reference assignments",
                                 f"$.{key}"))
    return errs


def rule_check_object(committed: dict, lookup: dict) -> list[dict]:
    return check_object(committed)


def rule_check_plan(committed: dict, lookup: dict) -> list[dict]:
    """Plan admission re-applied by the current validator: a committed plan it judges non-compliant (a downgrade, a
    missing decision_required) enters the version-inconsistency list when the head plan references it (spec 7.3)."""
    if committed.get("record_kind") != "plan" or lookup.get("intent") is None:
        return []
    parent = lookup.get("plans", {}).get(committed.get("revision", 0) - 1) if is_int(committed.get("revision")) else None
    return [e for e in check_plan(committed, parent, lookup["intent"]) if not e["code"].startswith(("object.",
                                                                                                   "order."))]


# Validator versions: each maps to the object rules it applies. Historical checks use the rule set of their version
# (old versions are kept as repository tags; this table holds the current line).
LATEST_VALIDATOR = "0.1.0"
VALIDATOR_RULES: dict[str, tuple[Callable[[dict, dict], list[dict]], ...]] = {
    "0.1.0": (rule_check_object, rule_check_plan)}


# ---------------------------------------------------------------------------------------------------------------------
# Plan admission: required obligations, decision_required, downgrade list, obligation_map (spec 6.3, 8.1, 8.2)
# ---------------------------------------------------------------------------------------------------------------------

def _dec(s: Any) -> decimal.Decimal | None:
    if not isinstance(s, str) or not re.fullmatch(r"[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?", s):
        return None
    return decimal.Decimal(s)


def _required_conditions(plan: dict) -> set[str]:
    return {c["condition"] for c in plan.get("independence_requirements", [])
            if isinstance(c, dict) and c.get("required") is True}


def _judged(plan: dict, kind: str, oid: str) -> bool:
    return any(j.get("kind") == kind and oid in j.get("obligation_ids", []) for j in plan.get("judgments", []))


def check_plan(plan: dict, parent: dict | None, intent: dict) -> list[dict]:
    """Rejections at adoption of a plan revision (cases A10, A22a, D9, N23, N46, N56, N58, N68)."""
    errs = check_object(plan)
    obs = plan.get("obligations")
    if not isinstance(obs, list):
        return errs + [_err("plan.obligations", "obligations must be a list")]
    ids = [o.get("id") for o in obs]
    if len(set(ids)) != len(ids):
        errs.append(_err("plan.duplicate_obligation", "obligation ids must be unique"))
    if not any(o.get("required") is True for o in obs):
        errs.append(_err("plan.no_required_obligation", "a plan needs at least one required obligation (min of the "
                         "empty set is undefined)"))
    for i, o in enumerate(obs):
        if type(o.get("required")) is not bool:
            errs.append(_err("plan.required_missing", "required must be true or false", f"$.obligations[{i}]"))
        elif o["required"]:
            if type(o.get("decision_required")) is not bool:
                errs.append(_err("plan.decision_required_missing", "a required obligation states decision_required "
                                 "explicitly", f"$.obligations[{i}]"))
        elif "decision_required" in o and o["decision_required"] is not False:
            errs.append(_err("plan.optional_decision_required", "decision_required is fixed to false for an optional "
                             "obligation", f"$.obligations[{i}]"))
        for t in o.get("tolerances", []):
            if _dec(t.get("value")) is None:
                errs.append(_err("plan.tolerance_value", "tolerances are non-negative decimal strings",
                                 f"$.obligations[{i}]"))
    if "target_tier" in plan and plan["target_tier"] != intent.get("target_tier"):
        errs.append(_err("plan.target_tier", "target_tier belongs to the intent; a plan revision cannot change it"))
    if plan.get("intent_id") != intent.get("id"):
        errs.append(_err("plan.intent", "the plan does not belong to this intent"))
    if "change_request" in plan:
        errs.append(_err("plan.change_request_unsupported", "authorized change-requests are handled in T07, which is "
                         "not implemented; downgrades stay rejected"))
    if parent is not None:
        errs.extend(_downgrades(parent, plan))
    return errs


def _field_downgrades(oid: str, o: dict, n: dict, plan: dict, judged_ids: tuple[str, ...], p: str) -> list[dict]:
    """The section 8.1 checks between one old required obligation and one obligation that replaces it (same id or a
    1:1 rename through obligation_map)."""
    errs: list[dict] = []
    if n.get("required") is not True:
        errs.append(_err("downgrade.required_to_optional", f"{oid} required -> optional", p))
    if not set(o.get("required_methods", [])) <= set(n.get("required_methods", [])):
        errs.append(_err("downgrade.method_removed", f"{oid} lost required methods", p))
    if not set(o.get("evidence_requirements", [])) <= set(n.get("evidence_requirements", [])):
        errs.append(_err("downgrade.evidence_removed", f"{oid} lost evidence requirements", p))
    if not set(o.get("independence_requirements", [])) <= set(n.get("independence_requirements", [])):
        errs.append(_err("downgrade.independence_removed", f"{oid} lost independence conditions", p))
    if o.get("decision_required") is True and n.get("decision_required") is not True:
        errs.append(_err("downgrade.decision_required_dropped", f"{oid} decision_required true -> false", p))
    errs.extend(_tolerance_downgrades(oid, o, n, p))
    if _adoption_loosened(o, n):
        errs.append(_err("downgrade.adoption_loosened", f"{oid} adoption_policy loosened", p))
    for field_, code in (("criterion", "downgrade.criterion_changed"),
                         ("assumptions", "downgrade.assumptions_changed")):
        if o.get(field_) != n.get(field_) and not any(_judged(plan, "equivalent_or_stronger", x) for x in judged_ids):
            errs.append(_err(code, f"{oid} {field_} changed without an equivalent-or-stronger judgment", p))
    return errs


def _adoption_loosened(o: dict, n: dict) -> bool:
    oa, na = o.get("adoption_policy", {}), n.get("adoption_policy", {})
    return (any(oa.get(k) is True and na.get(k) is not True for k in ("second_method_required",
                                                                       "verification_required"))
            or not set(oa.get("qualifications", [])) <= set(na.get("qualifications", [])))


def _split_downgrades(oid: str, o: dict, targets: list[dict], p: str) -> list[dict]:
    """A split or merge: the required targets together keep every method, evidence requirement and independence
    condition; each required target keeps decision_required, the tolerances it shares and the adoption policy.
    Whether the new criteria cover the old one needs a scope judgment (a planning gap without it, spec 8.2.3)."""
    errs: list[dict] = []
    req = [t for t in targets if t.get("required") is True]
    for key, code in (("required_methods", "downgrade.method_removed"),
                      ("evidence_requirements", "downgrade.evidence_removed"),
                      ("independence_requirements", "downgrade.independence_removed")):
        if not set(o.get(key, [])) <= {x for t in req for x in t.get(key, [])}:
            errs.append(_err(code, f"{oid}: the split lost {key}", p))
    for t in req:
        if o.get("decision_required") is True and t.get("decision_required") is not True:
            errs.append(_err("downgrade.decision_required_dropped", f"{oid} -> {t['id']} drops decision_required", p))
        if _adoption_loosened(o, t):
            errs.append(_err("downgrade.adoption_loosened", f"{oid} -> {t['id']} loosens adoption_policy", p))
        shared = dict(t, tolerances=[x for x in t.get("tolerances", [])])
        old_shared = dict(o, tolerances=[x for x in o.get("tolerances", [])
                                         if x.get("quantity") in {y.get("quantity") for y in t.get("tolerances", [])}])
        errs.extend(_tolerance_downgrades(f"{oid}->{t['id']}", old_shared, shared, p))
    covered = {x.get("quantity") for t in req for x in t.get("tolerances", [])}
    if any(x.get("quantity") not in covered for x in o.get("tolerances", [])):
        errs.append(_err("downgrade.tolerance_loosened", f"{oid}: the split dropped a tolerance", p))
    return errs


def _downgrades(parent: dict, plan: dict) -> list[dict]:
    errs: list[dict] = []
    if not _required_conditions(parent) <= _required_conditions(plan):
        errs.append(_err("downgrade.independence_removed", "plan-level independence conditions were removed"))
    old = {o["id"]: o for o in parent.get("obligations", [])}
    revised = {o["id"]: o for o in plan.get("obligations", [])}
    omap = {m["old_id"]: m for m in plan.get("obligation_map", []) or []}
    for oid, o in old.items():
        if not o.get("required"):
            continue
        p = f"$.obligations[{oid}]"
        if oid in revised:
            errs.extend(_field_downgrades(oid, o, revised[oid], plan, (oid,), p))
        elif oid in omap:
            targets = omap[oid].get("new_ids") or []
            if not targets:
                errs.append(_err("downgrade.required_retired", f"required {oid} retired via obligation_map", p))
            elif any(t not in revised for t in targets):
                errs.append(_err("plan.map_unknown_target", f"obligation_map of {oid} names unknown obligations", p))
            elif not any(revised[t].get("required") is True for t in targets):
                errs.append(_err("downgrade.mapped_to_optional", f"required {oid} mapped only to optional", p))
            elif len(targets) == 1:
                errs.extend(_field_downgrades(oid, o, revised[targets[0]], plan, (oid, targets[0]), p))
            else:
                errs.extend(_split_downgrades(oid, o, [revised[t] for t in targets], p))
        else:
            errs.append(_err("downgrade.required_removed", f"required {oid} deleted", p))
    return errs


def _tolerance_downgrades(oid: str, o: dict, n: dict, p: str) -> list[dict]:
    newt = {t.get("quantity"): t for t in n.get("tolerances", [])}
    for t in o.get("tolerances", []):
        q = t.get("quantity")
        nt = newt.get(q)
        if nt is None or nt.get("kind") != t.get("kind"):
            return [_err("downgrade.tolerance_loosened", f"{oid} tolerance on {q} removed or re-kinded", p)]
        a, b = _dec(t.get("value")), _dec(nt.get("value"))
        if a is None or b is None or b > a:
            return [_err("downgrade.tolerance_loosened", f"{oid} tolerance on {q} loosened", p)]
    return []


# ---------------------------------------------------------------------------------------------------------------------
# validate(bundle, version): structure, bindings, dependencies, disposition (spec 7.3)
# ---------------------------------------------------------------------------------------------------------------------

def _items(rec: dict):
    for group in ("answers", "findings", "attempts", "evidence", "judgments", "suspected_conflicts", "responses"):
        for it in rec.get(group, []) if isinstance(rec.get(group), list) else []:
            if isinstance(it, dict):
                yield group, it


def _edges(group: str, it: dict) -> list[str]:
    deps = list(it.get("depends_on", []))
    if group == "answers":
        deps += it.get("evidence_ids", []) + it.get("attempt_ids", []) + it.get("finding_ids", [])
    elif group == "findings":
        deps += it.get("evidence_ids", [])
    elif group in ("judgments", "responses"):
        deps += [it[k] for k in ("finding_id", "answer_id") if it.get(k)]
    return [d for d in deps if isinstance(d, str)]


def _check_chain(bundle: dict) -> None:
    prev = None
    for i, c in enumerate(bundle["commits"], 1):
        head = c.get("commit", {})
        if not is_int(head.get("seq")) or head.get("seq") != i or head.get("prev_commit_digest") != prev:
            raise BundleError(f"bundle.chain: commit {i} is out of sequence or not chained")
        if metadata_digest(head) != c.get("digest"):
            raise BundleError(f"bundle.chain: commit {i} digest does not match its content")
        payload = {"objects": sorted((object_ref(o) for o in c.get("objects", [])), key=lambda r: r["digest"]),
                   "head_changes": {}}
        if metadata_digest(payload) != head.get("payload_digest"):
            raise BundleError(f"bundle.chain: commit {i} payload_digest does not match its objects")
        prev = c["digest"]
    if bundle.get("as_of_seq") != len(bundle["commits"]) or bundle.get("as_of_commit_digest") != prev:
        raise BundleError("bundle.as_of: as_of_seq / as_of_commit_digest do not name the last commit")


def validate(bundle: dict, validator_version: str, *, rules: dict | None = None) -> dict:
    """Structural, binding and dependency diagnostics and the disposition of every record and item. Disposition is
    computed here and never stored (spec 7.3). The output is the input of project()."""
    rules = VALIDATOR_RULES if rules is None else rules
    if validator_version not in rules:
        raise ValueError(f"unknown validator version {validator_version!r}")
    if not isinstance(bundle, dict) or set(bundle) - BUNDLE_KEYS:
        raise BundleError(f"bundle.keys: unexpected {sorted(set(bundle) - BUNDLE_KEYS)} (only committed objects "
                          "are projected)")
    if bundle.get("mode") not in ("recorded", "R0"):
        raise BundleError("bundle.mode must be 'recorded' or 'R0'")
    _check_chain(bundle)
    entries: list[tuple[int, dict]] = []
    seen: dict[tuple[str, str], str] = {}
    for c in bundle["commits"]:
        for o in c["objects"]:
            key = (o.get("record_kind"), o.get("id"))
            d = metadata_digest(o)
            if key in seen and seen[key] != d:
                raise BundleError(f"bundle.id_collision: {key} maps to different bytes")
            seen[key] = d
            entries.append((c["commit"]["seq"], o))
    qrec: dict[str, dict] = {}
    qitem: dict[str, dict] = {}
    diagnostics: list[dict] = []
    for _seq, o in entries:
        for e in check_object(o):
            diagnostics.append(dict(e, object=o.get("id")))
        for field_name in ("revision", "plan_revision", "intent_revision"):
            if field_name in o and not is_int(o[field_name]):
                diagnostics.append(_err("object.integer", f"{o.get('id')}: {field_name} must be an integer", f"$.{field_name}")
                                   | {"object": o.get("id")})
    diagnostics.extend(_order_diagnostics(entries))
    if any(not is_int(o.get("revision")) for _, o in entries if o.get("record_kind") == "plan"):
        raise BundleError("bundle.plan_revision: a plan revision is not an integer")
    intents = [o for _, o in entries if o.get("record_kind") == "intent"]
    plans = {o["revision"]: (s, o) for s, o in entries if o.get("record_kind") == "plan"}
    manifests = {o["id"]: o for _, o in entries if o.get("record_kind") == "manifest"}
    assignments = {o["id"]: (s, o) for s, o in entries if o.get("record_kind") == "assignment"}
    input_error = None
    if not intents:
        input_error = {"code": "input.no_intent", "message": "no intent"}
    elif not intents[-1].get("material_scope"):
        input_error = {"code": "input.no_scope", "message": "the intent establishes no material scope"}
    elif not plans:
        input_error = {"code": "input.no_plan", "message": "no adopted plan"}
    else:
        head = plans[max(plans)][1]
        man = manifests.get(head.get("manifest_id"))
        if man is None:
            input_error = {"code": "input.no_manifest", "message": "the head plan's manifest is missing"}
        else:
            have = {m.get("material_id") for m in man.get("materials", [])}
            if not set(intents[-1]["material_scope"]) <= have:
                input_error = {"code": "input.scope_not_captured", "message": "scope materials are not in the manifest"}
    known_items: dict[str, tuple[str, str, dict]] = {}  # item id -> (record id, group, item)
    for seq, o in entries:
        if o.get("record_kind") != "record":
            continue
        rid = str(o.get("id"))
        reason = _record_binding(o, seq, plans, assignments, manifests, known_items, bundle)
        if reason:
            qrec[rid] = reason
            continue
        for group, it in _items(o):
            known_items[str(it["id"])] = (rid, group, it)
    # item-level quarantine: corrupt evidence, invalid discharges, then propagation along dependencies
    authors = _authors(manifests)
    for iid, (rid, group, it) in known_items.items():
        if group == "evidence":
            st = bundle.get("blob_checks", {}).get(it.get("content_ref", {}).get("digest"), "missing")
            if st != "ok":
                qitem[iid] = {"code": f"evidence.blob_{st}", "record_id": rid, "message": f"evidence bytes {st}"}
        if group == "answers" and it.get("verdict") == "not-applicable":
            rec = _record(entries, rid)
            asg = assignments.get(rec.get("assignment_id"), (0, {}))[1]
            dis = it.get("discharge")
            if not isinstance(dis, dict):
                qitem[iid] = {"code": "discharge.missing", "record_id": rid, "message": "not-applicable needs a discharge"}
            elif dis.get("reason_category") not in DISCHARGE_REASONS:
                qitem[iid] = {"code": "discharge.invalid_reason", "record_id": rid,
                              "message": f"not-applicable needs one of {list(DISCHARGE_REASONS)}; never missing data, "
                                         "difficulty or budget"}
            elif asg.get("role") == "author" or rec.get("actor") in authors:
                qitem[iid] = {"code": "discharge.by_author", "record_id": rid,
                              "message": "an author cannot discharge an obligation"}
            elif dis.get("basis") not in ("observed", "declared") or not _qualified(asg) \
                    or rec.get("type") not in ("submission", "verification"):
                qitem[iid] = {"code": "discharge.basis", "record_id": rid,
                              "message": "a discharge needs an observed or declared basis from a qualified reviewer"}
    changed = True
    while changed:
        changed = False
        for iid, (rid, group, it) in known_items.items():
            if iid in qitem:
                continue
            bad = [d for d in _edges(group, it) if d in qitem or (d in known_items and known_items[d][0] in qrec)]
            if bad:
                qitem[iid] = {"code": "dependency.quarantined", "record_id": rid,
                              "message": f"depends on quarantined {sorted(bad)}"}
                changed = True
    if bundle["mode"] == "R0":
        integrity = "not-checked"
    elif qrec or qitem or diagnostics:
        integrity = "partial-invalid"
    else:
        integrity = "valid"
    return {"bundle": bundle, "validator_version": validator_version, "entries": entries,
            "quarantined_records": qrec, "quarantined_items": qitem, "record_integrity": integrity,
            "input_error": input_error, "diagnostics": diagnostics}


def _order_diagnostics(entries: list[tuple[int, dict]]) -> list[dict]:
    """Creation order (spec 6.4): an object may reference only objects committed before it; a plan's manifest and
    intent precede it; a metadata ref names an earlier object."""
    first: dict[str, int] = {}
    digest_seq: dict[str, int] = {}
    for seq, o in entries:
        first.setdefault(str(o.get("id")), seq)
        digest_seq.setdefault(metadata_digest(o), seq)
    out = []
    for seq, o in entries:
        names = []
        if o.get("record_kind") == "plan":
            names = [o.get("manifest_id"), o.get("intent_id")]
        for n in names:
            if n in first and first[n] >= seq:
                out.append(_err("order.forward_reference", f"{o.get('id')} names {n}, committed later") |
                           {"object": o.get("id")})
        for r in _nested_refs(o):
            if r.get("profile_id") == METADATA_PROFILE and r.get("digest") in digest_seq \
                    and digest_seq[r["digest"]] >= seq:
                out.append(_err("order.forward_reference", f"{o.get('id')} references an object committed later") |
                           {"object": o.get("id")})
    return out


def _record(entries, rid):
    return next(o for _, o in entries if o.get("record_kind") == "record" and o.get("id") == rid)


def _authors(manifests: dict) -> set[str]:
    out: set[str] = set()
    for m in manifests.values():
        for mat in m.get("materials", []):
            out.update(mat.get("authors", []))
    return out


def _record_binding(rec, seq, plans, assignments, manifests, known_items, bundle) -> dict | None:
    """None if the record's envelope, bindings and dependencies hold; else the reason to quarantine it whole."""
    def q(code, msg):
        return {"code": code, "message": msg, "raw_submission_ref": rec.get("raw_submission_ref")}
    if rec.get("type") not in RECORD_TYPES or rec.get("submission_fidelity") not in FIDELITIES \
            or not isinstance(rec.get("raw_submission_ref"), dict) or not isinstance(rec.get("actor"), str):
        return q("envelope.invalid", "type, actor, raw_submission_ref or submission_fidelity is invalid")
    if rec["submission_fidelity"] == "mismatch":
        return q("fidelity.mismatch", "the submitted digest does not match the stored bytes")
    asg = assignments.get(rec.get("assignment_id"))
    if asg is None:
        return q("binding.assignment", "unknown assignment")
    if asg[0] >= seq:
        return q("order.forward_reference", "the record references an assignment committed after it")
    a = asg[1]
    if a.get("actor") != rec["actor"]:
        return q("binding.actor", "the record's actor is not the assignment's actor")
    if RECORD_TYPES[rec["type"]] != a.get("role"):
        return q("binding.role", f"a {rec['type']} record needs a {RECORD_TYPES[rec['type']]} assignment")
    rev = rec.get("plan_revision")
    if not is_int(rev) or not is_int(a.get("plan_revision")):
        return q("envelope.invalid", "plan_revision must be an integer (a bool is not an integer)")
    if rev != a.get("plan_revision") or rev not in plans or plans[rev][0] >= seq:
        return q("binding.plan", "the record is not bound to the plan revision of its assignment")
    if plans[rev][0] >= asg[0]:
        return q("order.forward_reference", "the assignment was committed before the plan revision it names")
    plan = plans[rev][1]
    if a.get("spec_id") not in {s.get("id") for s in plan.get("assignment_specs", [])}:
        return q("binding.assignment_spec", "the assignment's spec is not in its plan revision")
    obligations = {o["id"] for o in plan.get("obligations", [])}
    man = manifests.get(plan.get("manifest_id"), {})
    digests = {m.get("material_id"): m.get("raw_ref", {}).get("digest") for m in man.get("materials", [])}
    materials = set(digests)
    local: set[str] = set()
    for _group, it in _items(rec):
        if not isinstance(it.get("id"), str) or it["id"] in local or it["id"] in known_items:
            return q("envelope.duplicate_item", "item ids must be unique in the context")
        local.add(it["id"])
    for group, it in _items(rec):
        if group in ("answers", "findings", "attempts", "evidence") and it.get("obligation_id") not in obligations:
            return q("binding.obligation", f"{it['id']} names an obligation outside its plan revision")
        if group == "attempts" and it.get("observation") not in METHOD_OBSERVATIONS:
            return q("envelope.invalid", f"{it['id']} has an unknown method observation")
        if group == "answers" and it.get("verdict") not in OUTCOMES:
            return q("envelope.invalid", f"{it['id']} has an unknown verdict")
        loc = it.get("locator")
        if isinstance(loc, dict) and loc.get("material_id") not in materials:
            return q("binding.material", f"{it['id']} locates a material outside the manifest")
        if isinstance(loc, dict) and loc.get("digest") != digests.get(loc.get("material_id")):
            return q("binding.locator_digest", f"{it['id']} locates bytes that are not the manifest's snapshot")
        for mid in it.get("cited_materials", []):
            if mid not in materials:
                return q("binding.material", f"{it['id']} cites a material outside the manifest")
        for d in _edges(group, it):
            if d not in local and d not in known_items:
                return q("dependency.unknown", f"{it['id']} depends on unknown {d}")
    return None


# ---------------------------------------------------------------------------------------------------------------------
# Closures (spec 8.3)
# ---------------------------------------------------------------------------------------------------------------------

def environment_component(attempt: dict, observations: list | None) -> dict | None:
    """Item 4 of a closure. A missing tools field is unrecorded (None), never the empty set; `tools: []` needs no
    observation. observations=None means the attempt's own revision; otherwise the executor must be re-observed in
    the new revision, and a different or unobserved executor always differs."""
    if "tools" not in attempt or not isinstance(attempt.get("tools"), list):
        return None
    if attempt["tools"] == []:
        return {"tools": []}
    ex = attempt.get("executor")
    if observations is None:
        return {"executor": ex, "tools": sorted(attempt["tools"]),
                "environment_refs": sorted(attempt.get("environment_refs", []))}
    for o in observations:
        if o.get("executor") == ex:
            return {"executor": ex, "tools": sorted(o.get("tools", [])),
                    "environment_refs": sorted(o.get("environment_refs", []))}
    return {"executor": ex, "unobserved": True}


def _ob_core(o: dict) -> str:
    return metadata_digest({k: o.get(k) for k in ("question", "criterion", "assumptions", "tolerances")})


# ---------------------------------------------------------------------------------------------------------------------
# project(validated, version): the layer-1 projection
# ---------------------------------------------------------------------------------------------------------------------

class _Ctx:
    """Indexes over a validated bundle (internal)."""

    def __init__(self, v: dict):
        self.v = v
        self.b = v["bundle"]
        ent = v["entries"]
        self.intent = [o for _, o in ent if o["record_kind"] == "intent"][-1]
        self.plans = {o["revision"]: o for _, o in ent if o["record_kind"] == "plan"}
        self.H = max(self.plans)
        self.head = self.plans[self.H]
        self.manifests = {o["id"]: o for _, o in ent if o["record_kind"] == "manifest"}
        self.assignments = {o["id"]: o for _, o in ent if o["record_kind"] == "assignment"}
        self.bindings = [o for _, o in ent if o["record_kind"] == "claim-binding"]
        self.records = [(s, o) for s, o in ent if o["record_kind"] == "record"
                        and o["id"] not in v["quarantined_records"]]
        self.items: dict[str, dict] = {}
        self.item_group: dict[str, str] = {}
        self.item_rec: dict[str, dict] = {}
        self.item_seq: dict[str, int] = {}
        for s, r in self.records:
            for g, it in _items(r):
                if it["id"] in v["quarantined_items"]:
                    continue
                self.items[it["id"]] = it
                self.item_group[it["id"]] = g
                self.item_rec[it["id"]] = r
                self.item_seq[it["id"]] = s
        self.gaps: list[dict] = []
        self._resolve_cache: dict[tuple[str, int], tuple[str, ...]] = {}
        self._transition_gaps()

    def obligations(self, rev: int) -> dict:
        return {o["id"]: o for o in self.plans[rev]["obligations"]}

    def manifest(self, rev: int) -> dict:
        return self.manifests.get(self.plans[rev]["manifest_id"], {"materials": []})

    def _transition_gaps(self) -> None:
        revs = sorted(self.plans)
        for prev, cur in zip(revs, revs[1:]):
            old, revised = self.obligations(prev), self.obligations(cur)
            omap = {m["old_id"]: m for m in self.plans[cur].get("obligation_map", []) or []}
            into: dict[str, list[str]] = {}
            for oid in old:
                if oid in revised:
                    into.setdefault(oid, []).append(oid)
                    continue
                if oid not in omap:
                    self.gaps.append({"kind": "unmapped_old_obligation", "obligation_id": oid, "revision": cur})
                    continue
                targets = omap[oid].get("new_ids") or []
                for t in targets:
                    into.setdefault(t, []).append(oid)
                if len(targets) > 1 and not self._scope_judged(cur, oid):
                    self.gaps.append({"kind": "split_without_scope_judgment", "obligation_id": oid, "revision": cur})
            for t, olds in into.items():
                if len(olds) > 1 and not all(self._scope_judged(cur, o) for o in olds):
                    self.gaps.append({"kind": "merge_without_scope_judgment", "obligation_id": t, "revision": cur})

    def _scope_judged(self, rev: int, old_id: str) -> bool:
        return any(j.get("kind") == "scope_coverage" and old_id in j.get("old_ids", [])
                   for j in self.plans[rev].get("judgments", []))

    def resolve(self, oid: str, rev: int) -> tuple[str, ...]:
        """Obligation ids in the head revision that an obligation of revision `rev` maps to (empty: unmapped)."""
        key = (oid, rev)
        if key not in self._resolve_cache:
            cur = {oid}
            for r in range(rev + 1, self.H + 1):
                if r not in self.plans:
                    continue
                revised = self.obligations(r)
                omap = {m["old_id"]: m for m in self.plans[r].get("obligation_map", []) or []}
                nxt: set[str] = set()
                for o in cur:
                    if o in revised:
                        nxt.add(o)
                    elif o in omap:
                        nxt.update(t for t in omap[o].get("new_ids") or [] if t in revised)
                cur = nxt
            self._resolve_cache[key] = tuple(sorted(cur))
        return self._resolve_cache[key]

    def closure(self, iid: str, rev: int, ob: dict, own: bool, seen: frozenset = frozenset()) -> str | None:
        it = self.items.get(iid)
        if it is None or iid in seen:
            return None
        man = self.manifest(rev)
        mats = {m["material_id"]: m for m in man.get("materials", [])}
        located = [it["locator"]["material_id"]] if isinstance(it.get("locator"), dict) else []
        mids = sorted(set(ob.get("targets", [])) | set(it.get("cited_materials", [])) | set(located))
        materials = [[m, mats.get(m, {}).get("raw_ref", {}).get("digest"), mats.get(m, {}).get("view_version")]
                     for m in mids]
        env = None
        if self.item_group[iid] == "attempts":
            env = environment_component(it, None if own else self.plans[rev].get("environment_observations", []))
            if env is None:
                return None
        upstream = []
        for d in sorted(set(_edges(self.item_group[iid], it))):
            if d not in self.items:
                return None
            c = self.closure(d, rev, ob, own, seen | {iid})
            if c is None:
                return None
            upstream.append(c)
        return metadata_digest({"obligation": _ob_core(ob), "materials": materials,
                                "adoption_policy": ob.get("adoption_policy"), "environment": env,
                                "upstream": upstream})

    def placement(self, iid: str) -> tuple[tuple[str, ...], bool]:
        """(head obligation ids the item maps to, whether its closure is identical in the head revision)."""
        it = self.items[iid]
        rec = self.item_rec[iid]
        rev = rec["plan_revision"]
        oid = it.get("obligation_id") or self._finding_obligation(it)
        if oid is None:
            return (), False
        targets = self.resolve(oid, rev)
        if len(targets) != 1:
            return targets, False
        own_ob = self.obligations(rev).get(oid)
        head_ob = self.obligations(self.H)[targets[0]]
        if own_ob is None:
            return targets, False
        own = self.closure(iid, rev, own_ob, True)
        cur = self.closure(iid, self.H, head_ob, rev == self.H)
        return targets, own is not None and own == cur

    def _finding_obligation(self, it: dict) -> str | None:
        f = self.items.get(it.get("finding_id", ""))
        return f.get("obligation_id") if f else None


def _qualified(a: dict, ob: dict | None = None) -> bool:
    """Qualified with an observed or declared basis, holding every qualification the obligation's adoption policy
    names (spec 6.5, 7.2)."""
    q = a.get("qualified", {})
    need = set((ob or {}).get("adoption_policy", {}).get("qualifications", []))
    return (q.get("satisfied") is True and q.get("basis") in ("observed", "declared")
            and need <= set(a.get("qualifications", [])))


def _target_authors(ctx: _Ctx, ob: dict) -> set[str]:
    mats = {m["material_id"]: m for m in ctx.manifest(ctx.H).get("materials", [])}
    return {a for t in ob.get("targets", []) for a in mats.get(t, {}).get("authors", [])}


def _judge_counts(ctx: _Ctx, jrec: dict, ob: dict) -> bool:
    """Only qualified, non-author judges in submission, verification or adjudication records can adopt, refute or
    dispute; an author's disagreement is a response, never a ruling (spec 6.5, 7.2)."""
    return (jrec["type"] in JUDGING_RECORD_TYPES and _qualified(ctx.assignments[jrec["assignment_id"]], ob)
            and jrec["actor"] not in _target_authors(ctx, ob)
            and ctx.assignments[jrec["assignment_id"]].get("role") != "author")


def _finding_states(ctx: _Ctx, conflicted: set[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    judg = [(ctx.item_rec[i], it) for i, it in ctx.items.items() if ctx.item_group[i] == "judgments"]
    resp = [it for i, it in ctx.items.items() if ctx.item_group[i] == "responses"]
    for fid, f in ctx.items.items():
        if ctx.item_group[fid] != "findings":
            continue
        rec = ctx.item_rec[fid]
        asg = ctx.assignments[rec["assignment_id"]]
        ob = ctx.obligations(rec["plan_revision"]).get(f["obligation_id"], {})
        pol = ob.get("adoption_policy", {})
        positive = negative = 0
        verified = second = False
        direct = (not pol.get("verification_required") and not pol.get("second_method_required")
                  and rec["type"] == "submission" and _qualified(asg, ob))
        if direct:
            positive += 1
        adjudications = []
        fixed = False
        for jrec, j in judg:
            if j.get("finding_id") != fid:
                continue
            if not _judge_counts(ctx, jrec, ob):
                continue
            if j.get("kind") == "finding_assessment":
                if j.get("verdict") == "supported":
                    positive += 1
                    verified |= jrec["type"] == "verification"
                    second |= j.get("method") not in (None, f.get("method"))
                elif j.get("verdict") == "refuted":
                    negative += 1
            elif j.get("kind") == "adjudication" and jrec["type"] == "adjudication":
                adjudications.append(j.get("verdict"))
            elif j.get("kind") == "fix_verified" and jrec["type"] == "verification":
                fixed = True
        if fid in conflicted:
            negative += 1
        adopted = direct or ((verified or not pol.get("verification_required"))
                             and (second or not pol.get("second_method_required")) and positive > 0)
        if adjudications:
            state = adjudications[0] if len(set(adjudications)) == 1 else "disputed"
            if state not in ("supported", "refuted"):
                state = "disputed"
        elif positive and negative:
            state = "disputed"
        elif negative:
            state = "refuted"
        elif positive and adopted:
            state = "supported"
        else:
            state = "candidate"
        if state == "supported" and fixed:
            state = "retired-for-current"
        r = next((x for x in resp if x.get("finding_id") == fid), None)
        out[fid] = {"state": state, "response": r.get("response") if r else None,
                    "fix_check": r.get("fix_check") if r else None, "adjudicated": bool(adjudications)}
    return out


def _tier_of(ctx: _Ctx, ob: dict, recs: list[dict], floor_ok: bool) -> tuple[str, list[str], set[str]]:
    """The highest tier whose conditions all hold for this obligation, with the reasons it is not higher."""
    if ctx.b["mode"] == "R0":
        return "R0", ["R0 consultation: no store, record integrity not checked"], set()
    reasons: list[str] = []
    advisory: set[str] = set()
    if not floor_ok:
        reasons.append("independent-review floor not met by the plan's independence conditions")
    if not recs:
        reasons.append("no admitted submission supports this obligation's result")
    target_authors = _target_authors(ctx, ob)
    extra = (_required_conditions(ctx.head) - set(FLOOR)) | set(ob.get("independence_requirements", []))
    for r in recs:
        a = ctx.assignments[r["assignment_id"]]
        cond = a.get("conditions", {})
        for c in FLOOR:
            x = cond.get(c, {})
            if x.get("satisfied") is not True or x.get("basis") not in FLOOR_BASES[c]:
                reasons.append(f"{c} not met with an accepted basis for {a['id']} (basis {x.get('basis')})")
            elif x.get("basis") == "advisory":
                advisory.add(c)
        if r["actor"] in target_authors:
            reasons.append(f"{r['actor']} is an author of this obligation's material (non-author unmet)")
        if a.get("contamination"):
            reasons.append(f"{a['id']} saw other evaluations before submitting (no-other-evaluations-seen unmet)")
        for c in sorted(extra):  # sorted: layer 1 never depends on set iteration order
            x = cond.get(c, {})
            if x.get("satisfied") is not True or x.get("basis") not in EXTRA_CONDITION_BASES:
                reasons.append(f"plan condition {c} not met for {a['id']}")
        fid = r["submission_fidelity"]
        if fid not in FIDELITY_R2 or (fid == "host-transcript" and a.get("host_transcript_writable") is not False):
            reasons.append(f"submission fidelity {fid} is below file-transfer")
    if reasons:
        return "R1", reasons, advisory
    req = ctx.head.get("required_restrictions") or []
    ok, why = _claim_binding_ok(ctx.bindings[-1] if ctx.bindings else None, ctx.head)
    r3 = bool(req) and ok
    for r in recs:
        a = ctx.assignments[r["assignment_id"]]
        enforced = {x.get("id") for x in a.get("restrictions", []) if x.get("status") == "enforced"
                    and x.get("basis") == "observed"}
        if not set(req) <= enforced:
            r3 = False
            why.append(f"required restrictions not observed as enforced for {a['id']}")
    if not req:
        why.append("no required runtime restriction is stated, so R3 is not claimed")
    return ("R3" if r3 else "R2"), ([] if r3 else why), advisory


def _claim_binding_ok(binding: dict | None, plan: dict) -> tuple[bool, list[str]]:
    """Spec 15.6: a committed claim-binding object with the claim bytes and the evaluation chain segment from the
    trusted checkpoint the plan states to the commit holding the claim state, and the plan's capability fingerprint.
    Checked without reading the evaluation log's current state (layer 2 re-checks the current state)."""
    if not binding:
        return False, ["no claim-binding commit"]
    chain = binding.get("chain_segment") or []
    if not chain:
        return False, ["claim binding lacks the evaluation chain segment"]
    prev = None
    for i, c in enumerate(chain):
        if metadata_digest(c.get("commit", {})) != c.get("digest"):
            return False, ["evaluation chain segment: a commit digest does not match"]
        if i and c["commit"].get("prev_commit_digest") != prev:
            return False, ["evaluation chain segment is not chained"]
        prev = c["digest"]
    cp = plan.get("evaluation_checkpoint")  # stated by the coordinator under the user's authority, never the binding
    if not isinstance(cp, dict):
        return False, ["the plan names no trusted evaluation checkpoint"]
    if chain[0]["commit"].get("seq") != cp.get("seq") or chain[0].get("digest") != cp.get("digest"):
        return False, ["evaluation chain segment does not start at the trusted checkpoint"]
    claim = binding.get("claim") or {}
    if metadata_digest(claim) not in chain[-1].get("object_digests", []):
        return False, ["the claim is not in the last commit of the segment"]
    if claim.get("state") not in CLAIM_STATES_R3:
        return False, [f"claim state {claim.get('state')} is below pilot-checked-scope"]
    fp = plan.get("capability_fingerprint")  # this case's fingerprint comes from the case log, never the binding
    if not fp or claim.get("fingerprint") != fp:
        return False, ["claim fingerprint does not match this case's committed fingerprint"]
    return True, []


def project(validated: dict, validator_version: str, *, rules: dict | None = None) -> dict:
    """Layer 1: a pure function of the validated bundle and the validator version; same input, same bytes."""
    rules = VALIDATOR_RULES if rules is None else rules
    if validator_version not in rules:
        raise ValueError(f"unknown validator version {validator_version!r}")
    if validated.get("validator_version") != validator_version:
        raise ValueError("the bundle was validated with another validator version")
    b = validated["bundle"]
    again = validate(b, validator_version, rules=rules)  # disposition is never taken from the caller (spec 7.3)
    if any(again[k] != validated.get(k) for k in ("quarantined_records", "quarantined_items", "record_integrity",
                                                  "input_error", "entries", "diagnostics")):
        raise ValueError("the validated input does not match validate(bundle): disposition cannot be supplied")
    base = {"protocol": PROTOCOL, "schema_version": SCHEMA_VERSION, "kind": "hep-review-layer1",
            "context_id": b["context_id"], "segment_id": b["segment_id"], "as_of_seq": b["as_of_seq"],
            "as_of_commit_digest": b["as_of_commit_digest"], "validator_version": validator_version,
            "record_integrity": validated["record_integrity"]}
    if validated["input_error"]:
        return base | {"input_error": validated["input_error"], "summary_eligible": False, "achieved_tier": None}
    ctx = _Ctx(validated)
    head_obs = ctx.obligations(ctx.H)
    # placement of every admitted item: which head obligation, current or stale
    place = {iid: ctx.placement(iid) for iid in ctx.items}
    cur_answers: dict[str, list[dict]] = {o: [] for o in head_obs}
    for iid, (tg, cur) in place.items():
        if ctx.item_group[iid] != "answers" or not cur:
            continue
        r = ctx.item_rec[iid]
        if r["type"] in JUDGING_RECORD_TYPES and _qualified(ctx.assignments[r["assignment_id"]], head_obs[tg[0]]):
            cur_answers[tg[0]].append(ctx.items[iid])  # an author's response or an unqualified answer never counts
    assessed = {it.get("answer_id") for i, it in ctx.items.items()
                if ctx.item_group[i] == "judgments" and it.get("kind") == "answer_assessment"
                and it.get("verdict") == "supported" and ctx.item_rec[i]["type"] == "verification"
                and it.get("answer_id") in place and place[it["answer_id"]][0]
                and _judge_counts(ctx, ctx.item_rec[i], head_obs[place[it["answer_id"]][0][0]])}
    # mechanical conflicts and judged suspicions
    conflicted: set[str] = set()
    conflict_obs: set[str] = set()
    for oid, ans in cur_answers.items():
        verdicts = {a["verdict"] for a in ans}
        if {"supported", "violated"} <= verdicts:
            conflict_obs.add(oid)
            for a in ans:
                if a["verdict"] == "violated":
                    conflicted.update(a.get("finding_ids", []))
    unjudged: list[dict] = []
    conflict_judgments = {it.get("suspicion_id"): it for i, it in ctx.items.items()
                          if ctx.item_group[i] == "judgments" and it.get("kind") == "conflict"}
    for iid, it in ctx.items.items():
        if ctx.item_group[iid] != "suspected_conflicts":
            continue
        j = conflict_judgments.get(iid)
        if j is None:
            unjudged.append({"suspicion_id": iid, "between": it.get("between", [])})
        elif j.get("substantive") is True:
            for x in it.get("between", []):
                if ctx.item_group.get(x) == "findings":
                    conflicted.add(x)
                elif ctx.item_group.get(x) == "answers" and place.get(x, ((), False))[1]:
                    conflict_obs.add(place[x][0][0])
    states = _finding_states(ctx, conflicted)
    for oid in sorted(conflict_obs):
        violated = [a for a in cur_answers.get(oid, []) if a["verdict"] == "violated"]
        if violated and all(a.get("finding_ids") and all(states.get(f, {}).get("adjudicated")
                                                       for f in a["finding_ids"]) for a in violated):
            conflict_obs.discard(oid)  # every opposing item was ruled on by an adjudication
    findings_out = []
    historical = []
    stale_followups = []
    cur_find: dict[str, list[str]] = {o: [] for o in head_obs}
    for fid, st in sorted(states.items()):
        tg, cur = place[fid]
        f = ctx.items[fid]
        row = {"id": fid, "obligation_id": f["obligation_id"], "mapped_to": list(tg), "state": st["state"],
               "current": cur, "stale": not cur, "response": st["response"], "fix_check": st["fix_check"]}
        findings_out.append(row)
        if cur:
            cur_find[tg[0]].append(fid)
        elif st["state"] in ("supported", "candidate", "disputed"):
            stale_followups.append({"item_id": fid, "kind": "finding", "state": st["state"], "mapped_to": list(tg)})
            if st["state"] == "supported":
                historical.append({"finding_id": fid, "obligation_id": f["obligation_id"],
                                   "commit_seq": ctx.item_seq[fid]})
    for iid, (tg, cur) in sorted(place.items()):
        it = ctx.items[iid]
        if ctx.item_group[iid] == "answers" and not cur and it.get("verdict") in ("violated", "undetermined"):
            stale_followups.append({"item_id": iid, "kind": "answer", "state": it["verdict"], "mapped_to": list(tg)})
    # dependency gaps from quarantine
    dep_gap_obs = sorted(o for o in {_q_obligation(validated, iid) for iid, q in validated["quarantined_items"].items()
                                     if q["code"].startswith(("dependency.", "evidence."))} if o is not None)
    floor_ok = set(FLOOR) <= _required_conditions(ctx.head)
    obligations_out = []
    carried = []
    advisory_all: set[str] = set()
    for oid, ob in head_obs.items():
        answers = cur_answers[oid]
        fstates = [states[f]["state"] for f in cur_find[oid]]
        stale_here = any(oid in s["mapped_to"] for s in stale_followups) or \
            any(oid in tg and not cur for tg, cur in place.values())
        outcome, reasons = _outcome(ctx, ob, answers, fstates, oid in conflict_obs, bool(stale_here), place,
                                    assessed)
        recs = []
        for a in answers:
            r = ctx.item_rec[a["id"]]
            if r not in recs:
                recs.append(r)
        tier, tier_reasons, adv = _tier_of(ctx, ob, recs, floor_ok)
        advisory_all |= adv
        for a in answers:
            if ctx.item_rec[a["id"]]["plan_revision"] < ctx.H:
                carried.append({"obligation_id": oid, "item_id": a["id"], "commit_seq": ctx.item_seq[a["id"]],
                                "note": "carried over: identical closure"})
        obligations_out.append({
            "id": oid, "required": ob["required"] is True, "decision_required": ob.get("decision_required") is True,
            "outcome": outcome, "reasons": reasons, "obligation_tier": tier, "tier_reasons": tier_reasons,
            "discharge": next((a.get("discharge") for a in answers if a["verdict"] == "not-applicable"), None)
            if outcome == "not-applicable" else None,
            "facets": _facets(ctx, ob, answers, outcome, place)})
    gaps = list(ctx.gaps)
    mapped = {r for o in head_obs.values() if o.get("required") is True for r in o.get("origin_requirement_ids", [])}
    for req in ctx.intent.get("minimum_requirements", []):
        if req["id"] not in mapped:
            gaps.append({"kind": "unplanned_requirement", "requirement_id": req["id"]})
    if ctx.head.get("scope_scan") != SCOPE_DONE:
        gaps.append({"kind": "scope", "state": ctx.head.get("scope_scan")})
    inconsistencies = _version_inconsistencies(ctx, place, validator_version, rules)
    required = [o for o in obligations_out if o["required"]]
    defects = any(f["current"] and f["state"] == "supported" for f in findings_out)
    disputed = any(f["current"] and f["state"] == "disputed" for f in findings_out)
    open_reasons: list[dict] = []
    for f in findings_out:
        if f["current"] and f["state"] in ("candidate", "disputed"):
            open_reasons.append({"kind": f"{f['state']}_finding", "item_id": f["id"]})
    open_reasons += [{"kind": "stale_follow_up", "item_id": s["item_id"]} for s in stale_followups]
    open_reasons += [{"kind": "required_" + o["outcome"], "obligation_id": o["id"]} for o in required
                     if o["outcome"] in ("not-examined", "undetermined")]
    open_reasons += [{"kind": "planning_gap", "gap": g["kind"]} for g in gaps]
    open_reasons += [{"kind": "version_inconsistency", "object_id": x["object_id"]} for x in inconsistencies]
    open_reasons += [{"kind": "unjudged_conflict", "suspicion_id": u["suspicion_id"]} for u in unjudged]
    open_reasons += [{"kind": "unverified_conflict", "obligation_id": o} for o in sorted(conflict_obs)]
    open_reasons += [{"kind": "dependency_gap", "obligation_id": o} for o in dep_gap_obs]
    met = (not gaps and all(o["outcome"] != "not-examined" for o in required)
           and all(not (o["decision_required"] and o["outcome"] in ("undetermined", "not-examined")) for o in required))
    open_q = bool(open_reasons)
    tiers = [o["obligation_tier"] for o in required]
    achieved = min(tiers, key=TIERS.index) if tiers else None
    uncovered: dict[str, list[str]] = {"not_examined": [], "undetermined": []}
    for o in obligations_out:
        if o["required"] or o["outcome"] not in ("not-examined", "undetermined") or o["id"] in conflict_obs:
            continue
        if any(f["current"] and f["state"] in ("candidate", "disputed") and o["id"] in f["mapped_to"]
               for f in findings_out):
            continue
        uncovered["not_examined" if o["outcome"] == "not-examined" else "undetermined"].append(o["id"])
    discharged = [o for o in required if o["outcome"] == "not-applicable"]
    coverage = {"total_obligations": len(obligations_out), "total_required": len(required),
                "discharged": len(discharged),
                "methods_not_run_by_discharge": sorted(f"{o['id']}:{m}" for o in discharged
                                                      for m in head_obs[o["id"]].get("required_methods", []))}
    integrity = validated["record_integrity"]
    eligible = (achieved is not None and TIERS.index(achieved) >= 1 and integrity == "valid" and met
                and not defects and not disputed and not open_q)
    quarantined = [{"record_id": rid, "code": q["code"], "raw_submission_ref": q.get("raw_submission_ref")}
                   for rid, q in sorted(validated["quarantined_records"].items())]
    quarantined += [{"item_id": iid, "record_id": q["record_id"], "code": q["code"]}
                    for iid, q in sorted(validated["quarantined_items"].items())]
    return base | {
        "target_tier": ctx.intent.get("target_tier"), "head_plan_revision": ctx.H,
        "obligations": obligations_out, "findings": findings_out,
        "flags": {"has_supported_defects": defects, "has_disputed_findings": disputed,
                  "has_open_questions": open_q, "plan_requirements_met": met},
        "open_reasons": open_reasons, "planning_gaps": gaps, "uncovered_optional": uncovered,
        "unverified_historical_defects": historical, "version_inconsistencies": inconsistencies,
        "quarantined": quarantined, "carried_over": carried, "coverage": coverage,
        "independence_floor_not_met": not floor_ok, "advisory_conditions": sorted(advisory_all),
        "achieved_tier": achieved, "summary_eligible": eligible,
        "cost": {"status": "unavailable"},
        "limitations": ["Outcomes are projections of committed records under the stated conditions, not proofs.",
                        "Closed or mechanically valid does not mean scientifically passed."]}


def _q_obligation(validated: dict, iid: str) -> str | None:
    for _, o in validated["entries"]:
        if o.get("record_kind") != "record":
            continue
        for _, it in _items(o):
            if it.get("id") == iid:
                return it.get("obligation_id")
    return None


def _outcome(ctx: _Ctx, ob: dict, answers: list[dict], fstates: list[str], conflict: bool, stale: bool,
             place: dict, assessed: set) -> tuple[str, list[str]]:
    if conflict or "disputed" in fstates:
        return "undetermined", ["substantive conflict between admitted judgments (not resolved by majority)"]
    if "supported" in fstates:
        return "violated", ["linked to a current supported finding"]
    if "candidate" in fstates:
        return "undetermined", ["a candidate finding awaits adoption under the adoption policy"]
    if not answers:
        return "not-examined", ["previous result stale (closure changed)" if stale else "no admissible answer"]
    verdicts = {a["verdict"] for a in answers}
    if "undetermined" in verdicts:
        missing = sorted({m.get("name", str(m)) if isinstance(m, dict) else str(m)
                          for a in answers for m in a.get("missing_inputs", [])})
        return "undetermined", ["work exists but no conclusion"] + [f"missing input: {m}" for m in missing]
    if "violated" in verdicts:
        return "undetermined", ["violated was asserted without an adopted finding"]
    if "not-examined" in verdicts and len(verdicts) == 1:
        return "not-examined", ["the reviewer did not complete the check"]
    pending = _adoption_pending(ctx, ob, answers, place, assessed)
    if verdicts == {"not-applicable"}:
        if pending:
            return "undetermined", [pending]
        return "not-applicable", ["valid applicability discharge"]
    attempts = [ctx.items[x] for a in answers for x in a.get("attempt_ids", [])
                if x in ctx.items and place.get(x, ((), False))[1]]
    done = {x.get("method") for x in attempts if x.get("observation") == "completed"}
    missing_m = [m for m in ob.get("required_methods", []) if m not in done]
    evidence = [ctx.items[x] for a in answers for x in a.get("evidence_ids", [])
                if x in ctx.items and place.get(x, ((), False))[1]]
    have_e = {e.get("requirement") for e in evidence}
    missing_e = [e for e in ob.get("evidence_requirements", []) if e not in have_e]
    if missing_m or missing_e:
        return "not-examined", [f"required method not completed: {m}" for m in missing_m] + \
            [f"required evidence missing: {e}" for e in missing_e]
    if pending:
        return "undetermined", [pending]
    return "supported", ["evidence supports the criterion under the stated conditions"]


def _adoption_pending(ctx: _Ctx, ob: dict, answers: list[dict], place: dict, assessed: set) -> str | None:
    """The adoption policy applies to positive results too (spec 7.2): a required verification or second method keeps
    the result pending until it is current."""
    pol = ob.get("adoption_policy", {})
    positive = [a for a in answers if a["verdict"] in ("supported", "not-applicable")]
    if pol.get("verification_required") and not any(a["id"] in assessed for a in positive):
        return "a positive result awaits the verification its adoption policy requires"
    if pol.get("second_method_required"):
        methods = {ctx.items[x].get("method") for a in positive for x in a.get("attempt_ids", [])
                   if x in ctx.items and place.get(x, ((), False))[1] and ctx.items[x].get("observation") == "completed"}
        if len(methods) < 2:
            return "a positive result awaits the second method its adoption policy requires"
    return None


def _facets(ctx: _Ctx, ob: dict, answers: list[dict], outcome: str, place: dict) -> dict:
    attempts = [ctx.items[x] for a in answers for x in a.get("attempt_ids", [])
                if x in ctx.items and place.get(x, ((), False))[1] and ctx.items[x].get("observation") == "completed"]
    tol_q = {t.get("quantity") for t in ob.get("tolerances", [])}

    def reproduced(x):
        r = x.get("reproduction") or {}
        return (x.get("method") == "reproduction" and bool(r.get("reference_quantities"))
                and bool(r.get("tolerance_quantities")) and set(r["tolerance_quantities"]) <= tol_q)
    func = [x["id"] for x in attempts if x.get("method") == "functional-check"]
    rep = [x["id"] for x in attempts if reproduced(x)]
    ind = [x["id"] for x in attempts if x.get("independent_method") is True]
    return {"artifact_functional": {"performed": bool(func), "attempts": func},
            "result_reproduced": {"performed": bool(rep), "attempts": rep},
            "independent_method_checked": {"performed": bool(ind), "attempts": ind},
            "domain_assessment": {"outcome": outcome}}


def _version_inconsistencies(ctx: _Ctx, place: dict, version: str, rules: dict) -> list[dict]:
    """Objects referenced by the head plan or by current result closures that the current validator judges
    non-compliant; superseded objects never enter the list (spec 7.3; cases D24, D30)."""
    refs = [ctx.intent, ctx.head, ctx.manifests.get(ctx.head.get("manifest_id"))]
    lookup = {"intent": ctx.intent, "plans": ctx.plans}
    for iid, (_tg, cur) in place.items():
        if cur:
            r = ctx.item_rec[iid]
            if r not in refs:
                refs.append(r)
                refs.append(ctx.assignments[r["assignment_id"]])
    out = []
    seen: set[tuple[str, str]] = set()
    for o in refs:
        if not o or (o["record_kind"], o["id"]) in seen:
            continue
        seen.add((o["record_kind"], o["id"]))
        codes = sorted({e["code"] for rule in rules[version] for e in rule(o, lookup)})
        if codes:
            out.append({"object_id": o["id"], "kind": o["record_kind"], "codes": codes})
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Layer 2 combination rule, rendering, historical check (spec 4.4, 7.5, 7.6)
# ---------------------------------------------------------------------------------------------------------------------

def decide_summary(layer1: dict, attestation: dict) -> dict:
    """Whether the no-defect summary is output (spec 7.5 layer 2). The attestation values (report_mode, validator
    approval, head_continuity, R3 state check) are determined by the I/O layer with their basis; this only combines."""
    cont = attestation.get("head_continuity")
    integrity = layer1.get("record_integrity")
    if cont == "broken":
        integrity = "invalid-continuity-broken"
    disclosure: list[str] = []
    if layer1.get("input_error"):
        return {"output_summary": False, "summary_text": None, "record_integrity": integrity,
                "disclosure": [f"input-error: {layer1['input_error']['message']}; no report is produced"]}
    achieved, target = layer1.get("achieved_tier"), layer1.get("target_tier")
    if achieved and target and TIERS.index(target) > TIERS.index(achieved):
        why = sorted({r for o in layer1["obligations"] if o["required"]
                      and TIERS.index(o["obligation_tier"]) < TIERS.index(target) for r in o["tier_reasons"]})
        disclosure.append(f"target {target}, achieved {achieved}: " + "; ".join(why))
    if layer1.get("independence_floor_not_met"):
        disclosure.append("independent-review floor not met")
    if achieved in ("R2", "R3") and "no-other-evaluations-seen" in layer1.get("advisory_conditions", []):
        disclosure.append(ADVISORY_SENTENCE)
    if cont == "unverified":
        disclosure.append("head continuity unverified: no trusted checkpoint anchors this session; provide the "
                          "last checkpoint (segment, seq, digest) to verify continuity")
    elif cont == "broken":
        disclosure.append("head continuity broken: appending stopped; record integrity is not valid")
    r3_ok = achieved != "R3" or attestation.get("r3_state_matches") is True
    if achieved == "R3" and attestation.get("r3_state_matches") is False:
        disclosure.append("the capability claim changed after binding: rebind before reporting R3")
    out = (layer1.get("summary_eligible") is True and attestation.get("report_mode") == "current"
           and attestation.get("validator_is_latest_approved") is True and cont == "verified"
           and integrity == "valid" and r3_ok)
    text = None
    if out:
        text = f"{QUALIFIER[str(achieved)]}: {NO_DEFECT}."
        unc = layer1.get("uncovered_optional", {})
        if unc.get("not_examined") or unc.get("undetermined"):
            text += (f" Uncovered optional obligations: not-examined {unc['not_examined']}, "
                     f"undetermined {unc['undetermined']}.")
        if "no-other-evaluations-seen" in layer1.get("advisory_conditions", []):
            text += " " + ADVISORY_SENTENCE
    return {"output_summary": out, "summary_text": text, "record_integrity": integrity, "disclosure": disclosure}


PRESENTATION_KEYS = {"title", "summary_sentence", "language"}
SUMMARY_UNIT = "{tier_qualifier}: " + NO_DEFECT
UNQUALIFIED_PASS = re.compile(r"\b(correct|correctly|correctness|passed|pass|passes|verified|proven)\b", re.I)


def render_report(layer1: bytes, attestation: dict, *, bundle: dict, validator_version: str,
                  presentation: dict | None = None, rules: dict | None = None) -> str:
    """Present both layers. Layer 1 must be exactly what the bundle projects to, so nothing can be hand-filled,
    deleted or carried from old obligations; presentation may only set a title, language and the wording of the
    summary sentence, which must keep {tier_qualifier} and the fixed scope phrase (cases P24, N14, N36)."""
    presentation = presentation or {}
    extra = set(presentation) - PRESENTATION_KEYS
    if extra:
        raise RenderError(f"presentation cannot set {sorted(extra)}")
    sentence = presentation.get("summary_sentence", SUMMARY_UNIT + ".")
    if SUMMARY_UNIT not in sentence:
        raise RenderError("a no-defect summary must keep '{tier_qualifier}: " + NO_DEFECT + "' as one sentence")
    for text in (presentation.get("title", ""), sentence.replace(SUMMARY_UNIT, "")):
        if UNQUALIFIED_PASS.search(text):
            raise RenderError(f"unqualified pass wording is not allowed: {text!r}")
    expected = encode(project(validate(bundle, validator_version, rules=rules), validator_version, rules=rules))
    if bytes(layer1) != expected:
        raise RenderError("layer 1 does not match the projection of the bundle")
    p = json.loads(expected)
    s = decide_summary(p, attestation)
    lines = [f"# {presentation.get('title', 'hep-review report')}",
             f"as of seq {p['as_of_seq']} ({p['as_of_commit_digest']}), validator {p['validator_version']}",
             f"layer 1 digest {raw_digest(expected)}"]
    if p.get("input_error"):
        return "\n".join(lines + [f"input-error: {p['input_error']['message']}"]) + "\n"
    lines.append(f"target {p['target_tier']}, achieved {p['achieved_tier']}")
    if p["achieved_tier"] == "R0":
        lines.append(R0_SENTENCE)
    elif s["output_summary"]:
        lines.append(sentence.replace("{tier_qualifier}", QUALIFIER[p["achieved_tier"]])
                     + s["summary_text"][len(QUALIFIER[p["achieved_tier"]]) + len(NO_DEFECT) + 3:])
    lines += [f"disclosure: {d}" for d in s["disclosure"]]
    f = p["flags"]
    lines.append(f"defects={f['has_supported_defects']} disputed={f['has_disputed_findings']} "
                 f"open={f['has_open_questions']} plan_requirements_met={f['plan_requirements_met']} "
                 f"record_integrity={s['record_integrity']}")
    for o in p["obligations"]:
        shown = o["outcome"]
        if shown == "not-applicable":
            shown += " (display: not-run-with-approved-discharge)"
        lines.append(f"- {o['id']} ({'required' if o['required'] else 'optional'}): {shown}; tier "
                     f"{o['obligation_tier']}")
    for x in p["findings"]:
        lines.append(f"- finding {x['id']}: {x['state']}{' (stale)' if x['stale'] else ''}")
    for x in p["unverified_historical_defects"]:
        lines.append(f"- unverified historical defect {x['finding_id']} (commit {x['commit_seq']})")
    for x in p["carried_over"]:
        lines.append(f"- {x['obligation_id']}: carried over: identical closure (commit {x['commit_seq']})")
    for x in p["open_reasons"]:
        lines.append(f"- open: {json.dumps(x, sort_keys=True)}")
    for x in p["quarantined"]:
        lines.append(f"- quarantined: {json.dumps(x, sort_keys=True)}")
    lines.append(f"coverage: {json.dumps(p['coverage'], sort_keys=True)}")
    return "\n".join(lines) + "\n"


def check_historical(old_layer1: bytes, bundle: dict, validator_version: str, *, rules: dict | None = None) -> str:
    """Recompute layer 1 with the old validator version and compare byte for byte; only 'match' or 'mismatch'."""
    recomputed = encode(project(validate(bundle, validator_version, rules=rules), validator_version, rules=rules))
    return "match" if bytes(old_layer1) == recomputed else "mismatch"
