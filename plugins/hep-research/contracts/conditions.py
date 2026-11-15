"""Conditions payloads of the reconstruction contracts (plan R32, K07, Sections 9.3, 9.8, 9.9; D2).

A payload sidecar records what a payload is, what it was derived against and how it may be used; its constants stay in
the native payload, and this plugin derives none (R31). Identities, not tags, decide everything here: payload_identity
hashes the content of the sidecar, so a change under one tag is a new identity. No conditions database or service is
built (Section 3.1). contracts.reconstruction.read_sidecar reads a payload; the other functions judge its use, and each
takes whole documents through contracts.sidecar_reader.
"""
from __future__ import annotations

from contracts.recipe_semantics import canonical_sha256
from contracts.schema import Report
from contracts.sidecar_reader import reader_path

NOT_IDENTITY = ("payload_id", "tag")


def payload_identity(payload: dict) -> str:
    return canonical_sha256({field: value for field, value in payload.items() if field not in NOT_IDENTITY})


def _check_constraints(payload: dict, cited, report: Report, path: str) -> None:
    for constraint in sorted(set(cited) & set(payload["constraints_used"])):
        report.add("error", path, "conditions.constraint_as_validation",
                   f"{constraint} was used to derive this payload, so it cannot be its independent validation (Section 9.6)")


def _check_payload(payload: dict, report: Report, path: str = "$") -> None:
    """R32 rules beyond the schema."""
    if payload["payload_id"] != payload_identity(payload):
        report.add("error", f"{path}.payload_id", "conditions.identity_mismatch", "payload_id is not the identity of this content")
    producer = payload["producer"]
    if not producer.get("step_id" if producer["kind"] == "step" else "source"):
        report.add("error", f"{path}.producer", "conditions.producer_incomplete", "a producer is a step identity, or external with the source named")
    against = payload["derived_against"]
    if payload["kind"] == "alignment-parameters":
        if "alignment" not in payload:
            report.add("error", path, "conditions.alignment_incomplete", "an alignment payload states its degrees of freedom, frame and level")
        if "geometry_id" not in against:
            report.add("error", f"{path}.derived_against", "conditions.derivation_missing", "an alignment payload names the nominal geometry its deltas apply to")
    elif "upstream_payloads" not in against:
        report.add("error", f"{path}.derived_against", "conditions.derivation_missing", "a calibration payload lists the upstream payloads it assumed, in chain order")
    for predicate in payload["iov"]["predicates"]:
        if predicate["start"] > predicate["end"]:
            report.add("error", f"{path}.iov", "conditions.iov_reversed", f"{predicate['coordinate']}: start is after end")
        elif predicate["start"] == predicate["end"] and predicate["closure"] == "half-open":
            report.add("error", f"{path}.iov", "conditions.iov_empty", f"{predicate['coordinate']}: a half-open interval from a point to itself holds nothing")
    _check_constraints(payload, payload["independent_validation"], report, f"{path}.independent_validation")


@reader_path("payload", refused=lambda report, arguments: False)
def iov_holds(payload: dict, point: dict) -> bool:
    """Whether a payload is valid at this point."""
    return _iov_holds(payload["iov"], point)


def _iov_holds(iov: dict, point: dict) -> bool:
    """Every predicate holds at this point. A coordinate the point does not state does not hold: unrelated coordinates are
    never compared (Section 9.3)."""
    for predicate in iov["predicates"]:
        value = point.get(predicate["coordinate"])
        if value is None or value < predicate["start"]:
            return False
        if value > predicate["end"] or (value == predicate["end"] and predicate["closure"] == "half-open"):
            return False
    return True


@reader_path("payloads", refused=lambda report, arguments: None)
def iov_intersection(payloads) -> dict | None:
    """The common validity of the payloads a step depends on: the intersection on each coordinate, all coordinates kept. None
    means no common validity can be stated: the intersection is empty, there is no dependency, or endpoints mix closures on
    one coordinate, which follow source rules (Section 9.3) that this reader does not have."""
    joined: dict = {}
    for payload in payloads:
        for predicate in payload["iov"]["predicates"]:
            found = joined.setdefault(predicate["coordinate"], dict(predicate))
            if found["closure"] != predicate["closure"]:
                raise ValueError(f"{predicate['coordinate']}: mixed closures need the source's rule")
            found["start"], found["end"] = max(found["start"], predicate["start"]), min(found["end"], predicate["end"])
    for predicate in joined.values():
        half_open = predicate["closure"] == "half-open"
        if predicate["start"] > predicate["end"] or (half_open and predicate["start"] == predicate["end"]):
            return None
    return {"predicates": [joined[coordinate] for coordinate in joined]} if joined else None


@reader_path("payload")
def check_binding(payload: dict, context: dict) -> Report:
    """A payload bound into a context: {"origin", "geometry_id" (alignment), "upstream_chain" (calibration)}. A different
    geometry or chain, or nominal in place of measured, is refused, never silently applied (R32; CAI-T06-2, CAI-T06-4)."""
    report = Report()
    if payload["origin"] == "nominal" and context.get("origin") != "nominal":
        report.add("error", "$.origin", "conditions.nominal_as_measured", "a nominal payload is never presented as measured")
    elif payload["origin"] == "measured" and context.get("origin") == "nominal":
        report.add("error", "$.origin", "conditions.measured_as_nominal", "a context declared nominal does not take a measured payload")
    against = payload["derived_against"]
    if payload["kind"] == "alignment-parameters":
        if against.get("geometry_id") != context.get("geometry_id"):
            report.add("error", "$.derived_against.geometry_id", "conditions.geometry_mismatch",
                       f"derived against {against.get('geometry_id')}, bound on {context.get('geometry_id')}")
    elif against.get("upstream_payloads") != context.get("upstream_chain"):
        report.add("error", "$.derived_against.upstream_payloads", "conditions.upstream_chain_mismatch",
                   "the bound upstream chain is not the one this payload assumed, in chain order")
    return report


@reader_path("payload")
def check_validation_claim(payload: dict, constraint: str) -> Report:
    """CAI-T06-3: may this constraint be cited as the payload's independent validation?"""
    report = Report()
    _check_constraints(payload, [constraint], report, "$")
    return report


@reader_path("product", "payloads")
def check_used(product: dict, payloads) -> Report:
    """A product's conditions_used records against the payloads it names (R32: identity and round of each payload; R36: the
    round it consumed; R32: nominal is never presented as measured). The tag is not compared: identities decide, and a
    re-tagged payload is the same payload. Reading a payload has verified that its stored identity is its content's."""
    report, known = Report(), {payload["payload_id"]: payload for payload in payloads}
    for index, record in enumerate(product["conditions_used"]):
        payload, path = known.get(record["payload_id"]), f"$.conditions_used[{index}]"
        if payload is None:
            report.add("error", f"{path}.payload_id", "conditions.unknown_payload", f"{record['payload_id']} is not among the payloads given")
            continue
        if record["origin"] != payload["origin"]:
            code = "conditions.nominal_as_measured" if payload["origin"] == "nominal" else "conditions.measured_as_nominal"
            report.add("error", f"{path}.origin", code, f"recorded as {record['origin']}; the payload is {payload['origin']}")
        produced = payload["loop"]["round"] if "loop" in payload else None
        if record["round"] != produced:
            report.add("error", f"{path}.round", "conditions.round_mismatch", f"recorded round {record['round']}; the payload's round is {produced}")
    return report


def _refused_reuse(report: Report, arguments: dict) -> dict:
    current = arguments["current"]
    return {"reuse": False, "changed": sorted(current) if isinstance(current, dict) else [],
            "reason": "; ".join(finding.message for finding in report.errors)}


@reader_path("product", "current", refused=_refused_reuse)
def reuse_decision(product: dict, current: dict, unknown_dependencies: bool = False) -> dict:
    """May a cached product be reused now? `current` maps each slot to the payload resolved afresh. Its identity is computed
    here, not read from the stored field (Section 9.8), and tags are never compared (Section 9.9). A slot the product never
    consumed is a new dependency, so it changes the decision too (R36). An unknown dependency disables reuse at this level
    (K07). A slot names one payload: a chain of per-IOV payloads uses one slot each."""
    used = product["conditions_used"]
    changed = [record["slot"] for record in used if record["slot"] not in current
               or payload_identity(current[record["slot"]]) != record["payload_id"]]
    consumed = {record["slot"] for record in used}
    changed += sorted(slot for slot in current if slot not in consumed)
    if unknown_dependencies:
        return {"reuse": False, "changed": changed, "reason": "unknown dependencies: reuse is disabled at this level"}
    return {"reuse": not changed, "changed": changed, "reason": "identities changed" if changed else "every identity is unchanged"}


def _parent_payloads(payload: dict) -> list[str]:
    parents = list(payload["derived_against"].get("upstream_payloads", []))
    return parents + [payload["derived_from"]] if "derived_from" in payload else parents


def _every_payload(report: Report, arguments: dict) -> list | None:
    """Section 9.4: a payload that cannot be read broadens invalidation to every payload given, and unclear state disables
    precise invalidation. None, not a list, when the input holds anything that is not a payload document with an identity,
    such as identities or file paths in place of documents, so a caller cannot take it for "nothing affected"."""
    payloads = arguments["payloads"]
    found = list(payloads.values()) if isinstance(payloads, dict) and "schema" not in payloads else payloads
    if not isinstance(found, (list, tuple)) or not all(isinstance(payload, dict) and isinstance(payload.get("payload_id"), str) for payload in found):
        return None
    return [payload["payload_id"] for payload in found]


@reader_path("payloads", refused=_every_payload)
def affected_payloads(changed, payloads) -> list[str] | None:
    """Identities of the payloads derived, directly or not, from the changed ones (Section 9.9: all derived products follow).
    `changed` is a list of identities; `payloads` is a list, a tuple or a mapping from a slot to a payload. Any other shape, or
    a payload that cannot be read, broadens invalidation (Section 9.4): every payload given is affected, and None when the
    input holds anything that is not a payload document with an identity, a mixed list included. A caller tests `is None`,
    never `not result`. An empty list or mapping gives
    [], none affected: Section 9.4 allows precise invalidation when the dependencies are fully declared, and a declared
    empty set of payloads has nothing derived to invalidate."""
    if not isinstance(changed, (list, tuple, set)):
        raise TypeError("changed is a collection of identities")
    documents = list(payloads.values()) if isinstance(payloads, dict) else payloads
    reached = set(changed)
    found: list[str] = []
    while True:
        step = [payload["payload_id"] for payload in documents
                if payload["payload_id"] not in reached and reached & set(_parent_payloads(payload))]
        if not step:
            return found
        reached.update(step)
        found.extend(step)
