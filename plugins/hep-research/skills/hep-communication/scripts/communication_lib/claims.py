"""audit_claims: recorded assessments, source read coverage, advisory wording scans, number and unit consistency,
reporting completeness, a traceable claim matrix and draft-ready facts (plan T5).

Deterministic code checks the record's consistency, never scientific truth: a support verdict is the assessor's
recorded judgment. Wording scans are advisory (warnings) and skip quoted language, negations and statements about
another paper's claim. Exact source values stay separate from display strings; a comparison uses the occurrence's
declared rounding and never invents a tolerance or a unit conversion. Needed calculations are routed to the producing
skill as handoffs with the specific unresolved input.
"""
from __future__ import annotations

import json
import re
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from communication_lib import numbers as N
from communication_lib import report as R
from communication_lib.reporting import check_reporting
from contracts.communication import evidence_fingerprint, format_of
from contracts.communication_project import normalize_dependency_report
from contracts.evidence import STRENGTH

NOTE = ("assessment recorded by its assessor and checked for consistency with the record; whether the evidence supports "
        "the wording is the reader's judgment, not established by this audit; wording findings are advisory")
PROMOTED = {"synthetic", "asimov", "preliminary", "unvalidated", "failed", "user-supplied"}
# English, Traditional Chinese (RC-A10) and Simplified Chinese (F-12): each CJK character that differs between the two
# scripts is a character class, so mixed forms match too. CJK alternatives carry no \\b: CJK characters are word
# characters.
_DATA = r"(?:[资資]料|[数數][据據])"
MEASURED_RE = re.compile(r"\b(we measure|measured|observed|observation of|in data|the data show|data show)\b"
                         r"|[测測]量到|量[测測]到|[测測]得|[观觀][测測]到|[观觀]察到|在" + _DATA + r"中|" + _DATA + r"[显顯]示", re.I)
DISCOVERY_RE = re.compile(r"\b(observation of|evidence for|discover(?:y|ed)?|establish(?:es|ed)?)\b"
                          r"|[发發][现現]|[证證][实實]|[确確]立|[观觀][测測]到.{0,6}[讯訊信][号號]", re.I)
UNIVERSAL_RE = re.compile(r"\b(for all|all energies|all masses|universal(?:ly)?|always|in general|any (?:energy|mass|regime))\b"
                          r"|[对對]所有|所有能量|所有[质質]量|普遍|[总總]是|一般而言|任何能[区區]", re.I)
NEGATION_RE = re.compile(r"\b(no evidence|not|neither|nor|fails? to|without|rule[sd]? out|disfavou?r)\b"
                         r"|[没沒]有|[并並]未|[并並]非|未能|[无無]法|排除|不支持|不是", re.I)
ATTRIBUTION_RE = re.compile(r"\b(Ref\.|refs?\.|reported (?:by|in)|claims? that|according to|argue[sd]? that|et al\.)\b"
                            r"|根[据據]|[据據].{0,10}[报報][导導道]|文[献獻]\s*\[|等人", re.I)
QUOTE_RE = re.compile(r"[\"“「『][^\"”」』]*[\"”」』]")


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?;])\s+|(?<=[。！？；])", text) if s.strip()]


def _scan_sentences(text: str):
    """Sentences that may carry the author's own assertion: quotes removed, negated or attributed sentences skipped."""
    for s in _sentences(text):
        bare = QUOTE_RE.sub("", s)
        if NEGATION_RE.search(bare) or ATTRIBUTION_RE.search(bare):
            continue
        yield bare


def _locate(doc, locator: str):
    node = doc
    for part in locator.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return None, False
    return node, True


MODES = {"half-up": ROUND_HALF_UP, "half-even": ROUND_HALF_EVEN}


def _pdg_decimals(unc: Decimal) -> int:
    """Decimal places the PDG rule keeps for an uncertainty (Review of Particle Physics, Introduction 5.3, read
    2026-10-17): the three highest digits 100-354 keep two significant digits, 355-949 one, 950-999 round up to 1000
    and keep two."""
    if unc <= 0:
        raise ValueError("the PDG rule needs a positive uncertainty")
    adj = unc.adjusted()  # exponent of the leading digit
    top = int(abs(unc).scaleb(2 - adj).to_integral_value(rounding=ROUND_DOWN))  # the three highest digits, 100-999
    if top <= 354:
        return 1 - adj
    return -adj  # 355-949: one significant digit; 950-999: rounds up to 1000, two significant digits


def pdg_round(value, uncertainty) -> tuple[str, str]:
    """(value, uncertainty) as the PDG rule displays them; the value keeps the uncertainty's precision (half up)."""
    v, u = Decimal(str(value)), Decimal(str(uncertainty))
    q = Decimal(1).scaleb(-_pdg_decimals(u))
    return str(v.quantize(q, rounding=ROUND_HALF_UP)), str(u.quantize(q, rounding=ROUND_HALF_UP))


def pdg_round_asymmetric(value, plus, minus) -> tuple[str, str, str]:
    """PDG rule for asymmetric errors: when they differ by less than 10% of their average, the average is the
    displayed symmetric error; otherwise the narrower one sets the rounding of both."""
    v, up, dn = Decimal(str(value)), Decimal(str(plus)), Decimal(str(minus))
    avg = (up + dn) / 2
    if abs(up - dn) < Decimal("0.1") * avg:
        val, unc = pdg_round(v, avg)
        return val, unc, unc
    q = Decimal(1).scaleb(-_pdg_decimals(min(up, dn)))
    return (str(v.quantize(q, rounding=ROUND_HALF_UP)), str(up.quantize(q, rounding=ROUND_HALF_UP)),
            str(dn.quantize(q, rounding=ROUND_HALF_UP)))


def parse_rounding(rounding: str) -> tuple[str, int, str]:
    """(kind, n, mode) of a rule 'decimals:n' or 'significant:n' with an optional ':half-up' (default) or ':half-even',
    or 'pdg' (the PDG rule, which needs the uncertainty); ValueError when malformed."""
    if str(rounding) == "pdg":
        return "pdg", 0, "half-up"
    parts = str(rounding).split(":")
    if len(parts) not in (2, 3) or parts[0] not in ("decimals", "significant"):
        raise ValueError(f"unknown rounding rule {rounding!r}: use decimals:n or significant:n[:half-up|half-even]")
    try:
        n = int(parts[1])
    except ValueError:
        raise ValueError(f"rounding rule {rounding!r}: {parts[1]!r} is not an integer") from None
    mode = parts[2] if len(parts) == 3 else "half-up"
    if mode not in MODES:
        raise ValueError(f"rounding rule {rounding!r}: mode must be half-up or half-even")
    if (parts[0] == "significant" and n < 1) or (parts[0] == "decimals" and n < 0) or n > 20:
        raise ValueError(f"rounding rule {rounding!r}: {parts[0]} must be between {1 if parts[0] == 'significant' else 0} and 20")
    return parts[0], n, mode


def _round(value: str, rounding: str | None, uncertainty=None):
    """The display form of an exact value under a declared rounding rule (round half up unless the rule says
    ':half-even'), or None when the rule is missing or malformed, the value is not a finite number, or the rule is
    'pdg' and no uncertainty is given."""
    d = N.to_decimal(value)
    if d is None or rounding is None:
        return None
    try:
        kind, n, mode = parse_rounding(rounding)
        if kind == "pdg":
            u = N.to_decimal(uncertainty) if uncertainty is not None else None
            return None if u is None else pdg_round(d, u)[0]
        if kind == "decimals":
            return str(d.quantize(Decimal(1).scaleb(-n), rounding=MODES[mode]))
        if d == 0:
            return "0"
        return str(d.quantize(Decimal(1).scaleb(d.adjusted() - n + 1), rounding=MODES[mode]))
    except (ValueError, InvalidOperation):
        return None


def _rounds_somehow(source: Decimal, shown: Decimal) -> bool:
    """With no declared rule: the display equals the source rounded (half up or half even) to the display's own last
    digit, so 1.1 is a rounding of 1.09 and 1.02 is not."""
    try:
        q = Decimal(1).scaleb(shown.as_tuple().exponent)
        return any(source.quantize(q, rounding=m) == shown for m in MODES.values())
    except InvalidOperation:
        return False


def _same_number(a: str, b: str) -> bool:
    try:
        return Decimal(str(a)) == Decimal(str(b))
    except InvalidOperation:
        return str(a).strip() == str(b).strip()


def _covered(locator: str, event: dict) -> bool:
    """A read event covers an edge locator when its level is full-text, or a recorded locator equals the edge locator
    or is its whole leading part up to a non-alphanumeric boundary ('abstract' covers 'abstract, sentence 2'; 'Table 1'
    does not cover 'Table 12')."""
    level = event.get("level")
    if STRENGTH.get(level, 0) >= 3:
        return True
    if STRENGTH.get(level, 0) < 2:
        return False
    loc = re.sub(r"\s+", " ", locator.strip().lower())
    recorded = [re.sub(r"\s+", " ", str(x).strip().lower()) for x in event.get("locators", []) or []]
    if level == "abstract+metadata" and not recorded:
        recorded = ["abstract"]
    return any(r and re.match(r"^" + re.escape(r) + r"(?![a-z0-9])", loc) for r in recorded)


MEASURED_TYPES = {"measurement", "search", "limit"}


def _planned_only(context: dict, sid: str) -> list[str]:
    """IDs of the planned ledger claims citing a source when every ledger claim citing it is planned; else []."""
    ns = sid.split(":", 1)[0] if ":" in sid else None
    led = (context.get("ledgers") or {}).get(ns) or {}
    citing = [(cid, c) for cid, c in (led.get("claims") or {}).items() if sid in (c.get("source_ids") or [])]
    if citing and all(c.get("kind") == "planned" for _, c in citing):
        return sorted(cid for cid, _ in citing)
    return []


def audit_claims(record: dict, context: dict, policy: dict) -> dict:
    ext = record.get("extension") if isinstance(record.get("extension"), dict) else {}
    fmt = format_of(record)
    findings: list[dict] = R.normalize(context["schema"]["findings"], "schema", "fix the record")
    findings += R.normalize(context.get("findings", []), "resolution", "resolve the reference inside the project root")
    if context.get("dependencies"):
        findings += R.normalize(normalize_dependency_report(context["dependencies"]), "dependencies", "fix the input chain")
    notes: list[str] = []
    numbers_blocked = 0
    numbers_ran = 0
    handoffs: list[dict] = []
    matrix: list[dict] = []
    facts: list[dict] = []
    scope = {"format": fmt, "claims": [], "policy": {"version": policy.get("policy_version")}}
    if fmt != "traceability":
        for i, c in enumerate(ext.get("claims", []) or []):
            matrix.append({"id": f"legacy:{i}", "text": c.get("text"), "status": c.get("status"), "verdict": None, "currency": None,
                           "evidence": [{"target": c.get("result_ref")}], "occurrences": [], "findings": []})
        findings.append(R.finding("audit.legacy_record", "unresolved", "$.required_capabilities",
                                  "legacy record: no evidence edges, occurrences or assessments to audit",
                                  "write a traceability record (communication:traceability-v1)", source="claims"))
        return R.assemble("audit_claims", scope, findings, checks_run=["schema"], notes=notes,
                          checks_not_run=[{"check": c, "reason": "legacy record", "required": True} for c in ("assessments", "sources", "wording", "numbers", "reporting")],
                          claim_matrix=matrix, draft_facts=facts, handoffs=handoffs, note=NOTE)
    root = Path(context["project_root"])
    read_events = {r.get("id"): r for r in ext.get("sources_read", []) or [] if isinstance(r, dict)}
    occ_by_claim: dict[str, list] = {}
    for o in ext.get("occurrences", []) or []:
        if isinstance(o, dict):
            occ_by_claim.setdefault(o.get("claim_id"), []).append(o)
    stale_claims = {f["location"].split(".assessment")[0] for f in findings if f["code"] == "communication.assessment_stale"}
    docs_cache: dict[str, dict | None] = {}
    rc = ext.get("reporting_context") if isinstance(ext.get("reporting_context"), dict) else None
    rc_fields = (rc or {}).get("fields") if rc else {}
    limitations = list(ext.get("limitations", []) or [])
    for i, c in enumerate(ext.get("claims", []) or []):
        if not isinstance(c, dict):
            continue
        cid, where = c.get("id"), f"$.extension.claims[{i}]"
        scope["claims"].append(cid)
        row_findings: list[str] = []

        def add(code, severity, location, message, action):
            findings.append(R.finding(code, severity, location, message, action, claim=cid, source="claims"))
            row_findings.append(code)
        a = c.get("assessment") if isinstance(c.get("assessment"), dict) else None
        verdict = a.get("verdict") if a else None
        if a:
            if verdict == "unsupported":
                add("claim.unsupported", "error", f"{where}.assessment", f"recorded verdict unsupported: {a.get('rationale')}",
                    "correct the attribution at the evidence locator (cite the version actually read) or narrow the wording; the record stays until the text is fixed")
            elif verdict == "partially-supported":
                add("claim.partially_supported", "warning", f"{where}.assessment", f"recorded verdict partially supported: {a.get('rationale')}",
                    "narrow the wording to what the inspected evidence supports, or add the missing evidence")
            elif verdict == "unresolved":
                add("claim.assessment_unresolved", "unresolved", f"{where}.assessment", f"assessment unresolved: {a.get('rationale')}",
                    "inspect the evidence and record a verdict with locators")
        if c.get("workflow_state") == "verified" and (a is None or where in stale_claims or verdict != "supported"):
            add("workflow.verified_without_assessment", "error", f"{where}.workflow_state",
                "workflow_state is verified but the claim has no current supported assessment",
                "a checkbox does not close a claim: record a current assessment with checked versions, or set the state back")
        # source read coverage
        for j, e in enumerate(c.get("evidence", []) or []):
            if not isinstance(e, dict) or e.get("target_kind") != "source" or (e.get("usage") or "used-in-claim") != "used-in-claim":
                continue
            ev = read_events.get(e.get("target"))
            if ev is None:
                continue  # the schema check already reports source_not_read
            if not _covered(str(e.get("locator", "")), ev):
                add("source.locator_not_read", "unresolved", f"{where}.evidence[{j}]",
                    f"edge {e.get('id')} cites {e.get('locator')!r} of {e.get('target')}, but the read event covers level "
                    f"{ev.get('level')!r} with locators {ev.get('locators') or []}: the cited passage was not read",
                    "read the cited passage and record a read event covering it, or cite what was read (an abstract value with the abstract locator)")
        # planned claims never support a measured result
        if c.get("claim_type") in MEASURED_TYPES:
            if c.get("kind") == "planned":
                add("claim.planned_as_measured", "error", f"{where}.kind",
                    f"a {c.get('claim_type')} claim is marked planned: a plan is not a measured result",
                    "state the plan in the future tense with 'as of <date>' as a background claim, or record the result once it exists")
            for j, e in enumerate(c.get("evidence", []) or []):
                if not isinstance(e, dict) or e.get("target_kind") != "source" or e.get("role") != "supports" \
                        or (e.get("usage") or "used-in-claim") != "used-in-claim":
                    continue
                plans = _planned_only(context, str(e.get("target")))
                if plans:
                    add("claim.planned_support", "error", f"{where}.evidence[{j}]",
                        f"edge {e.get('id')} supports a {c.get('claim_type')} claim with source {e.get('target')}, whose only "
                        f"ledger claims are planned ({', '.join(plans)}): a plan cannot support a measured result",
                        "cite the source of the measured result, or change the edge role to background and the wording to the future tense")
        # wording (advisory)
        status = set(c.get("status", []) or [])
        text = str(c.get("text", ""))
        for s in _scan_sentences(text):
            if status & PROMOTED and MEASURED_RE.search(s):
                add("wording.status_promotion", "warning", f"{where}.text",
                    f"wording describes a result labeled {sorted(status & PROMOTED)} as measured or observed: {s.strip()!r}",
                    "say what the result is (synthetic, preliminary, ...) in the sentence; status survives writing")
            if DISCOVERY_RE.search(s) and (c.get("claim_type") == "search" or (rc or {}).get("result_type") == "search" or re.search(r"\blocal\b", s, re.I)):
                glob = (rc_fields.get("global_significance") or {}).get("state") == "provided" if rc else False
                if not glob:
                    add("wording.significance_unsupported", "warning", f"{where}.text",
                        f"discovery-level wording without a provided global significance: {s.strip()!r}",
                        "quote the local and global significance with the trials method, or weaken the wording")
                    handoffs.append({"to_skill": "hep-statistics", "claim": cid,
                                     "request": "global significance (look-elsewhere correction) and trials method for the quoted local excess"})
            if UNIVERSAL_RE.search(s) and not UNIVERSAL_RE.search(str((c.get("scope") or {}).get("text", ""))):
                add("wording.generalization", "warning", f"{where}.text",
                    f"wording generalizes beyond the recorded scope {str((c.get('scope') or {}).get('text', ''))!r}: {s.strip()!r}",
                    "restate the tested regime, or widen the scope with its evidence")
        # numbers: exact source values versus display strings
        source_value = None
        evidence_rows = []
        for e in c.get("evidence", []) or []:
            if not isinstance(e, dict):
                continue
            identity = evidence_fingerprint(e, record)
            inp = context["inputs"].get(e.get("target")) if e.get("target_kind") == "artifact" else context["sources"].get(e.get("target"))
            evidence_rows.append({"id": e.get("id"), "target_kind": e.get("target_kind"), "target": e.get("target"), "locator": e.get("locator"),
                                  "role": e.get("role"), "usage": e.get("usage") or "used-in-claim", "identity": identity,
                                  "resolved": bool(inp and inp.get("resolved"))})
            if e.get("target_kind") == "artifact" and e.get("role") == "supports" and source_value is None:
                if not inp or not inp.get("resolved") or inp.get("match") is False:
                    numbers_blocked += 1
                    add("numbers.source_unavailable", "unresolved", f"{where}.evidence[{e.get('id')}]",
                        f"the evidence artifact {e.get('target')!r} is missing, outside the root or does not carry its declared digest: "
                        "the source value cannot be compared with the display values",
                        "restore the artifact with its pinned digest, or re-pin the record after inspecting the new file")
                    continue
                key = e.get("target")
                if key not in docs_cache:
                    try:
                        docs_cache[key] = json.loads((root / inp["path"]).read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        docs_cache[key] = None
                node, ok = _locate(docs_cache[key], str(e.get("locator", ""))) if docs_cache[key] is not None else (None, False)
                if ok:
                    source_value = (node, e)
                else:
                    numbers_blocked += 1
                    add("evidence.locator_not_found", "unresolved", f"{where}.evidence[{e.get('id')}]",
                        f"locator {e.get('locator')!r} does not resolve in {e.get('target')!r}: the source value cannot be read",
                        "fix the locator to the field that holds the value")
        for o in occ_by_claim.get(cid, []):
            ov = o.get("value") if isinstance(o.get("value"), dict) else None
            if ov is not None and o.get("passage") and not N.contains_value(str(o["passage"]), ov.get("value", "")):
                add("occurrence.value_not_in_passage", "error", f"$.extension.occurrences[{o.get('id')}]",
                    f"occurrence {o.get('id')} declares display value {ov.get('value')!r}, which is not a number of its recorded passage",
                    "make the passage and the declared display value agree; no automatic correction")
        fact = {"claim_id": cid, "text": text, "claim_type": c.get("claim_type"), "status": sorted(status), "value": None, "unit": None,
                "uncertainty": {}, "source": None, "limitations": limitations, "unresolved_inputs": list(c.get("unresolved_inputs", []) or [])}
        if source_value is not None:
            numbers_ran += 1
            node, e = source_value
            val = node.get("value") if isinstance(node, dict) else node
            fact.update(value=None if val is None else str(val), unit=str(node.get("unit")) if isinstance(node, dict) and "unit" in node else None,
                        uncertainty={k: str(node[k]) for k in ("stat", "syst") if isinstance(node, dict) and k in node},
                        source={"edge": e.get("id"), "target": e.get("target"), "locator": e.get("locator"), "identity": evidence_fingerprint(e, record)})
            for o in occ_by_claim.get(cid, []):
                ov = o.get("value") if isinstance(o.get("value"), dict) else None
                if ov is None or val is None:
                    continue
                owhere = f"$.extension.occurrences[{o.get('id')}]"
                if fact["unit"] is not None and str(ov.get("unit")) != fact["unit"]:
                    add("occurrence.unit_conversion_unspecified", "unresolved", owhere,
                        f"occurrence {o.get('id')} displays unit {ov.get('unit')!r}, the source value is in {fact['unit']!r}; no conversion is recorded",
                        "record the conversion (factor, justification) or display the source unit")
                    continue
                src_d, shown_d = N.to_decimal(val), N.to_decimal(ov.get("value"))
                if src_d is None or shown_d is None:
                    add("occurrence.value_not_finite", "error", owhere,
                        f"occurrence {o.get('id')} compares display {ov.get('value')!r} with source {val!r}: both must be finite numbers",
                        "record finite numbers; a NaN or an infinity is never a displayable result")
                    continue
                if ov.get("rounding") is None:
                    if src_d == shown_d:
                        continue
                    if _rounds_somehow(src_d, shown_d):
                        add("occurrence.value_unrounded_comparison", "warning", owhere,
                            f"occurrence {o.get('id')} displays {ov.get('value')!r}, a rounding of the source value {val!r}, but no rounding rule is declared",
                            "declare the rounding (decimals:n or significant:n) so the display can be checked")
                    else:
                        add("occurrence.value_mismatch", "error", owhere,
                            f"occurrence {o.get('id')} displays {ov.get('value')!r}, which is no rounding of the source value {val!r}",
                            "update the display value to the authoritative source value")
                    continue
                try:
                    parse_rounding(ov.get("rounding"))
                except ValueError as exc:
                    add("occurrence.rounding_malformed", "error", owhere, f"occurrence {o.get('id')}: {exc}",
                        "write the rule as decimals:n or significant:n, optionally :half-up (default) or :half-even")
                    continue
                unc = None
                if isinstance(node, dict):
                    if "uncertainty" in node:
                        unc = node["uncertainty"]
                    elif "stat" in node or "syst" in node:  # the total, stat and syst in quadrature
                        parts = [N.to_decimal(node[k]) for k in ("stat", "syst") if k in node]
                        unc = None if any(p is None for p in parts) else str(sum(p * p for p in parts).sqrt())
                shown = _round(str(val), ov.get("rounding"), uncertainty=unc)
                if shown is None:
                    add("occurrence.rounding_malformed", "error", owhere,
                        f"occurrence {o.get('id')}: the source value {val!r} cannot be rounded under {ov.get('rounding')!r}",
                        "use a rule the value can be rounded to")
                elif not _same_number(str(ov.get("value")), shown):
                    add("occurrence.value_mismatch", "error", owhere,
                        f"occurrence {o.get('id')} displays {ov.get('value')!r}, the source value {val!r} rounds to {shown!r} under {ov.get('rounding')}",
                        "update the display value to the authoritative source value")
        facts.append(fact)
        matrix.append({"id": cid, "text": text, "claim_type": c.get("claim_type"), "status": sorted(status), "verdict": verdict,
                       "currency": "stale" if where in stale_claims else (a.get("currency") if a else None),
                       "assessor": (a or {}).get("assessor"), "evidence": evidence_rows,
                       "occurrences": [{"id": o.get("id"), "document_id": o.get("document_id"), "locator": o.get("locator"), "state": o.get("state")}
                                       for o in occ_by_claim.get(cid, [])],
                       "unresolved_inputs": list(c.get("unresolved_inputs", []) or []), "findings": row_findings})
        for req in c.get("unresolved_inputs", []) or []:
            handoffs.append({"to_skill": "the producing skill", "claim": cid, "request": req})
    reporting = None
    checks_run = ["schema", "assessments", "sources", "wording"] + (["numbers"] if numbers_ran else [])
    not_run = []
    if numbers_blocked:
        not_run.append({"check": "numbers", "reason": f"the evidence artifact or its locator was unavailable for {numbers_blocked} claim(s)", "required": True})
    if rc is not None:
        reporting = check_reporting(rc, policy)
        findings += reporting["findings"]
        checks_run.append("reporting")
    else:
        kinds = {c.get("claim_type") for c in ext.get("claims", []) or [] if isinstance(c, dict)}
        if kinds & {"measurement", "search", "limit", "theory-prediction", "ml-result"}:
            findings.append(R.finding("reporting.context_missing", "unresolved", "$.extension.reporting_context",
                                      "no reporting context: the result type and its method metadata are not declared",
                                      "add reporting_context (result_type, method, fields) so completeness can be checked", source="reporting"))
        not_run.append({"check": "reporting", "reason": "no reporting_context in the record", "required": False})
    return R.assemble("audit_claims", scope, findings, checks_run=checks_run, checks_not_run=not_run, notes=notes,
                      claim_matrix=matrix, draft_facts=facts, handoffs=handoffs, reporting=reporting, note=NOTE)


# ---------------------------------------------------------------- two versions of one text (Com7, audit_claims.py --compare)

_NUM = re.compile(r"(?<![A-Za-z_\d.])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
_STATUS_WORDS = {
    "synthetic": r"\bsynthetic\b|合成|模[拟擬][数數][据據]",
    "asimov": r"\basimov\b",
    "preliminary": r"\bpreliminary\b|初步",
    "expected": r"\bexpected\b|預期|预期",
    "unvalidated": r"\bunvalidated\b|未[验驗][证證]",
}
# claim-strength levels: 3 observation / discovery, 2 evidence, 1 indication or hint, 0 none
_STRENGTH = ((3, r"\bobservation of\b|\bdiscover(?:y|ed)\b|[观觀][测測]到.{0,6}[讯訊信][号號]|[发發][现現]"),
             (2, r"\bevidence for\b|[证證][据據]"),
             (1, r"\bindication of\b|\bhint of\b|[迹跡]象|暗示"))


def _features(text: str) -> dict:
    nums = sorted(str(Decimal(m.group(0))) for m in _NUM.finditer(text))
    status = sorted(k for k, rx in _STATUS_WORDS.items() if re.search(rx, text, re.I))
    level = max((lvl for lvl, rx in _STRENGTH if re.search(rx, text, re.I)), default=0)
    return {"numbers": nums, "status_words": status, "claim_strength": level}


def compare_versions(a: str, b: str) -> dict:
    """Numbers (with their uncertainties), status words and the strongest claim level of two versions of one text,
    such as an English and a Chinese draft; any difference is reported."""
    fa, fb = _features(a), _features(b)
    diffs = []
    if fa["numbers"] != fb["numbers"]:
        only_a = sorted((set(fa["numbers"]) - set(fb["numbers"])) | {n for n in fa["numbers"] if fa["numbers"].count(n) > fb["numbers"].count(n)})
        only_b = sorted((set(fb["numbers"]) - set(fa["numbers"])) | {n for n in fb["numbers"] if fb["numbers"].count(n) > fa["numbers"].count(n)})
        diffs.append({"check": "numbers", "only_in_a": only_a, "only_in_b": only_b,
                      "message": "the versions do not show the same numbers (values or uncertainties)"})
    if fa["status_words"] != fb["status_words"]:
        diffs.append({"check": "status-words", "a": fa["status_words"], "b": fb["status_words"],
                      "message": "a status word (synthetic, preliminary, expected, ...) is in one version only"})
    if fa["claim_strength"] != fb["claim_strength"]:
        names = {0: "none", 1: "indication", 2: "evidence", 3: "observation"}
        diffs.append({"check": "claim-strength", "a": names[fa["claim_strength"]], "b": names[fb["claim_strength"]],
                      "message": "the claim strength differs (for example evidence for vs observation of)"})
    return {"a": fa, "b": fb, "differences": diffs,
            "note": "deterministic comparison of numbers, status words and the strongest claim level; wording is not judged"}
