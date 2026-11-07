"""Finite candidate index and replayable selection (detector reconstruction T15a; plan Sections 5.7-5.9, 5.13, 5.14, 8.7, 16.1; K16, K18).

select_candidate judges every candidate of a finite index on one signature of an inspection: necessary conditions through
judge_candidates (SEL05), then quality evidence through check_recipe_evidence (SEL06), then the fixed objective (SEL07), and
writes a selection-record/1 (SEL08). It runs nothing and starts no backend, and a record holds no command (A52). check_selection_replay
makes the selection again on the inputs a caller holds and names every input that differs (A60).

Rules only. An index or policy not labelled artificial is refused, because K16's gates and objective are the user's. `role` is a
label, not a test of content, so it keeps nothing real out by itself; nothing is claimed about selection on real recipes. What
cannot be read or judged stays open and ends in a restricted delivery, never in a choice. Costs are compared at
RELATIVE_TOLERANCE_CEILING, a constant so that no policy can widen its own limit (Section 5.9 item 5). That value is a stand-in for
these artificial fixtures: "K09/K16 fix metric directions, tolerances, and statistical sufficiency" (Section 5.9 item 3), an open item.

A limit: `target` and `deliverable` of a policy reach the record only. A candidate of another quantity is told apart only by its
own `requires`, so SEL05's "type/quantity" rests on the author of the index.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

from contracts.input_inspector import judge_candidates
from contracts.recipe_semantics import canonical_sha256
from contracts.reconstruction import QUALIFICATION_BLOCKS, RELATIVE_TOLERANCE_CEILING, check_recipe_evidence, recipe_identity, runnable
from contracts.schema import Report
from contracts.sidecar_reader import FORMATS, reader_path

NO_QUALIFIED = "no qualified candidate"  # Section 5.9 item 5; Section 5.14, DS1
NOT_ESTABLISHED = "not established"
NO_CHECK_STATED = "no required check stated by the recipe"
STAGE_REFUSED = "reconstruction.recipe.evidence_stage_insufficient"
WITNESS_STAGE = "artificial-witness"
NECESSARY_BLOCKS = {"unsatisfied": "necessary-unsatisfied", "unknown": "necessary-unknown", "conflicting": "necessary-conflicting"}  # SEL05
# Every reason a candidate can stand out, in the order a record lists them. A52: the backend and the evidence stay two reasons.
BLOCKS = ("necessary-unsatisfied", "necessary-unknown", "necessary-conflicting", "recipe-unavailable", "no-available-backend", "quality-failed", "insufficient-evidence", "cost-unknown", "over-budget")
# SEL08 "obtain information": blocks more information could lift; a failed check or a limit it cannot. The backend follows Section 8.7's
# worked record: "state": "needs-evidence" beside "command": null and "runtime_evidence": null. A52's distinction is in the reasons.
OPEN_BLOCKS = frozenset({"necessary-unknown", "necessary-conflicting", "recipe-unavailable", "no-available-backend", "insufficient-evidence", "cost-unknown"})
BLOCK_REASONS = {"recipe-unavailable": "the recipe of this row was not supplied, is ambiguous, or differs from the one the index binds", "no-available-backend": "no backend is selected, or none has runtime evidence",
                 "quality-failed": "a required quality check failed", "insufficient-evidence": "required quality evidence is insufficient",
                 "cost-unknown": "no cost comparable with the limit", "over-budget": "over the cost cap"}
# Section 8.7: rule and reader hashes. Sources, not version strings, so that a change in a listed module cannot keep an old digest. A
# changed comment invalidates too, the conservative side of Section 9.4. The lists hold the modules that decide or read, not every import.
CONTRACTS_FOLDER = Path(__file__).resolve().parent
RULE_SOURCES = ("candidate_selection.py", "input_inspector.py", "reconstruction.py", "conditions.py", "recipe_semantics.py")
READER_SOURCES = ("sidecar_reader.py", "input_inspector.py", "schema.py", "schemas/reconstruction_common.json") + tuple(f"schemas/{name}" for name in sorted(FORMATS.values()))


def _unique(documents: list, field: str) -> dict:
    """Two documents under one identity cannot be told apart, and neither is used (A46: "without arbitrarily choosing a value")."""
    found: dict = {}
    for document in documents:
        found.setdefault(document[field], []).append(document)
    return {identity: held[0] for identity, held in found.items() if len(held) == 1}


def _uncovered_checks(policy: dict, evidence: dict | None) -> list:
    """Section 8.4 check 6; T06 reading: "required checks match and are constructible". What a contract holds is K16's; what is judged here
    is only whether the evidence covers it, each check by its own passed, constructible row."""
    contract = policy["quality_contract"]
    covered = {item["check_id"] for item in (evidence or {"checks": []})["checks"] if item["state"] == "pass" and item["constructible"]}
    return [] if contract is None else [check for check in contract["required_checks"] if check not in covered]


def _quality(recipe: dict, evidence_by_id: dict, policy: dict) -> tuple:
    """SEL06, as (block or None, this recipe's evidence or None). Evidence of another recipe or version says nothing here, so an
    expert's record is never a policy's (DS3; Section 17.3). A failure is evidence stating `failed`, or a `fail` row on a check the recipe
    or the contract requires: DS1, "Required tail check fails", "Exclude; speed cannot compensate for quality". Missing evidence is
    everything else short of routine use, such as evidence stating `inconclusive` or `unvalidated`, or a required row that is inconclusive,
    skipped, not applicable or absent: DS1, "Required quality evidence still insufficient", "Not in the routine set; may be listed
    separately as a qualification candidate". Section 8.4 check 6 keeps failed, inconclusive and unvalidated as three states. check_recipe_evidence refuses a witness for routine use (Section 12.1), and
    only that refusal is set aside, because Section 5.14 selects on a witness and every policy read here is an artificial one. T15b,
    which widens the role, must gate this on the role."""
    evidence = evidence_by_id.get(recipe["evidence_ref"])
    if evidence is None or evidence["recipe_id"] != recipe["recipe_id"] or evidence["recipe_sha256"] != recipe_identity(recipe):
        return "insufficient-evidence", None
    contract = policy["quality_contract"]
    required = set(recipe["checks"]) | set([] if contract is None else contract["required_checks"])
    if evidence["state"] == "failed" or any(item["state"] == "fail" and item["check_id"] in required for item in evidence["checks"]):
        return "quality-failed", evidence
    codes = [finding.code for finding in check_recipe_evidence(recipe, evidence).errors]
    refused = [code for code in codes if not (code == STAGE_REFUSED and evidence["stage"] == WITNESS_STAGE)]
    # Section 5.14: "pass all necessary conditions and quality checks": no required check is no quality check, not a vacuous pass
    if recipe["status"] != "routine" or refused or not recipe["checks"] or _uncovered_checks(policy, evidence):
        return "insufficient-evidence", evidence
    return None, evidence


def _total_cost(row: dict, policy: dict):
    """Sections 5.10, 5.14: a candidate's cost and the overhead shared by all, in the unit of the limit, or None."""
    objective = policy["objective"]
    if objective is None or row["cost"] is None or row["cost"]["unit"] != objective["cap"]["unit"]:
        return None
    total = row["cost"]["value"] + policy["shared_overhead"]["value"]
    return total if math.isfinite(total) else None


def _within_cap(total, cap) -> bool:
    """DS1: "keep time within" the cap, at the stated tolerance, since a sum of floats can miss an equal limit by rounding."""
    return total <= cap or _same_cost(total, cap)


def _same_cost(first, second) -> bool:
    """Section 5.9 item 4, "differences uncertain"; the tolerance is the module's stand-in, open for K16 (Section 5.9 item 3)."""
    return math.isclose(first, second, rel_tol=RELATIVE_TOLERANCE_CEILING, abs_tol=0)


def _indexed_recipe(row: dict, index: dict, recipes: dict) -> dict | None:
    """SEL04: only the recipe this row binds, of a method the index lists, is a candidate."""
    recipe = recipes.get(row["recipe_id"])
    method = next((item for item in index["methods"] if item["card_ref"] == row["method_ref"]), None)
    if recipe is None or recipe_identity(recipe) != row["recipe_sha256"] or recipe["method"] != {"card_ref": method["card_ref"], "card_sha256": method["card_sha256"]}:
        return None
    return recipe


def _unresolved_members(composition: dict | None, recipes: dict) -> list:
    """DS3: the whole needs its actual router and every expert."""
    if composition is None:
        return []
    return [member or "no router" for member in [composition["router"]] + composition["experts"] if member not in recipes]


def _backend_available(recipe: dict) -> bool:
    """K02: a backend is confirmed only after it has run. Nearest in the plan, Section 5.5: "an available library" does not "establish recipe usability"."""
    return runnable(recipe) and recipe["runtime_evidence"] is not None


def _judged_row(row: dict, judged: dict, index: dict, recipes: dict, evidence_by_id: dict, policy: dict) -> dict:
    """One candidate against everything at once, so a record shows all it lacks and not only the first thing (A52)."""
    blocks = set() if judged["eligible"] else {NECESSARY_BLOCKS[judged["state"]]}
    recipe = _indexed_recipe(row, index, recipes)
    evidence, uncovered = None, []
    if recipe is None:
        blocks.add("recipe-unavailable")
    else:
        if not _backend_available(recipe):
            blocks.add("no-available-backend")
        block, evidence = _quality(recipe, evidence_by_id, policy)
        blocks |= {block} - {None}
        uncovered = _uncovered_checks(policy, evidence) if block == "insufficient-evidence" else []
        uncovered += [NO_CHECK_STATED] if block == "insufficient-evidence" and not recipe["checks"] else []  # Section 5.6 item 5
    missing = _unresolved_members(row["composition"], recipes)
    if missing:
        blocks.add("insufficient-evidence")
    total = _total_cost(row, policy)
    if policy["objective"] is not None:  # Section 5.9 item 5: a limit is not lowered, and an unknown cost is not within it
        if total is None:
            blocks.add("cost-unknown")
        elif not _within_cap(total, policy["objective"]["cap"]["value"]):
            blocks.add("over-budget")
    listed = [block for block in BLOCKS if block in blocks]
    # SEL06, Section 5.10: a binding that can run and lacks only what a pilot finds out is listed for limited qualification (DS1, c_unknown)
    may_qualify = "insufficient-evidence" in blocks and blocks <= QUALIFICATION_BLOCKS and recipe is not None and runnable(recipe)
    standing = "routine-eligible" if not listed else "qualification-candidate" if may_qualify else "excluded"
    return {"recipe": row["recipe_id"], "standing": standing, "blocks": listed, "branch": judged["branch"], "open": judged["open"] + missing + uncovered,
            "cost": total, "evidence_stage": None if evidence is None else evidence["stage"], "runtime_evidence": None if recipe is None else recipe["runtime_evidence"], "rationale": row["rationale"],
            "evidence_id": None if evidence is None else evidence["evidence_id"], "condition": judged}


def _restriction(reasons: list, rows: list, options: list) -> dict:
    """A52, Section 5.6 item 5: what stands in the way, what stays open, and what can still be offered."""
    return {"reasons": reasons, "open": sorted({key for row in rows for key in row["open"]}), "options": options}


def _no_choice(rows: list) -> tuple:
    """Section 5.9 item 5, SEL08. Nothing is lowered to reach a choice, and a baseline is not qualified by being declared."""
    reasons = [block for block in BLOCKS if any(block in row["blocks"] for row in rows)]
    state = "needs-evidence" if any(set(row["blocks"]) <= OPEN_BLOCKS for row in rows) else "abstained"
    return state, None, f"{NO_QUALIFIED}: {', '.join(reasons)}", _restriction(reasons, rows, [])


def _baseline_or_options(shortlist: list, rows: list, policy: dict, problem: str) -> tuple:
    """Section 5.9 item 4: "If evidence is insufficient or differences uncertain, use a predeclared conservative baseline/tie-break and call it
    a 'qualified default choice,' not a proven best." So any eligible baseline, in the tie or not; otherwise the options, without a choice."""
    names = [row["recipe"] for row in shortlist]
    if policy["baseline"] in [row["recipe"] for row in rows if row["standing"] == "routine-eligible"]:
        return "qualified-default", policy["baseline"], f"qualified default choice, the predeclared baseline, not a proven best: {problem}", None
    return "abstained", None, f"no choice made: {problem}", _restriction([problem], rows, names)


def _decision(rows: list, policy: dict) -> tuple:
    """SEL07, SEL08, as (state, chosen recipe, reason, restriction). Section 5.9: speed never compensates, and best is only best here."""
    eligible = [row for row in rows if row["standing"] == "routine-eligible"]
    if not eligible:
        return _no_choice(rows)
    if policy["objective"] is None or policy["quality_contract"] is None:  # Section 5.9 item 3; DS1: no objective, no claim
        return _baseline_or_options(eligible, rows, policy, "objective-not-fixed")
    if len({row["evidence_stage"] for row in eligible}) > 1:  # Section 5.9 item 2: evidence must align in measured stage
        return _baseline_or_options(eligible, rows, policy, "evidence-not-comparable")
    lowest = min(row["cost"] for row in eligible)
    tied = [row for row in eligible if _same_cost(row["cost"], lowest)]
    if len(tied) > 1:  # Section 5.9 item 4: differences uncertain
        return _baseline_or_options(tied, rows, policy, "tied-within-tolerance")
    return "selected", tied[0]["recipe"], "minimum cost among the routine-eligible candidates of this index, under this objective; no global-best claim", None


def _expert_support(index: dict, recipes: dict, evidence_by_id: dict, policy: dict) -> list:
    """DS3: the claim stops at the experts that hold quality evidence of their own. Each is held to the policy's contract, the only statement of
    required quality here, so a contract an expert cannot meet leaves it unsupported: the cautious side, open for K16."""
    experts = sorted({expert for row in index["candidates"] if row["composition"] is not None for expert in row["composition"]["experts"]})
    return [expert for expert in experts if expert in recipes and _quality(recipes[expert], evidence_by_id, policy)[0] is None]


def _candidate_record(row: dict) -> dict:
    """Section 8.7: a candidate with its reasons. What excludes it is written out, and nothing is said of a candidate that stands."""
    reasons = [row["condition"]["reason"]] if not row["condition"]["eligible"] else []
    reasons += [BLOCK_REASONS[block] for block in row["blocks"] if block in BLOCK_REASONS]
    return {"recipe": row["recipe"], "hard_predicates": row["condition"]["state"], "quality_evidence": row["evidence_id"], "exclusion_or_probe_reason": "; ".join(reasons) or None}


def _policy_summary(policy: dict) -> dict:
    objective = policy["objective"]
    budgets = None if objective is None else f"cost cap {objective['cap']['value']} {objective['cap']['unit']}; shared overhead {policy['shared_overhead']['value']}"
    return {"version": policy["version"], "granularity": policy["granularity"], "target": policy["target"], "quality_contract": None if policy["quality_contract"] is None else policy["quality_contract"]["contract_id"],
            "objective": None if objective is None else objective["kind"], "budgets": budgets}


def _trial(probe: dict) -> dict:
    """A60, K17: feature costs, one row per probe, failures included. They are recorded, and kept apart from candidate costs (Section 5.10)."""
    cost = probe["cost"]
    return {"trial_id": probe["run"], "cost": f"bytes_read={cost['bytes_read']}; seconds={cost['seconds']}; memory_bytes={cost['memory_bytes']}", "outcome": probe["outcome"]}


def _signature_summary(signature: dict) -> dict:
    """Section 5.13: signature facts with their scopes, and what stayed unknown or in conflict."""
    facts = [{"key": fact["key"], "value": fact["value"], "scope": fact["scope"], "reference": fact["source"]["reference"]} for fact in signature["facts"]]
    return {"facts": facts, "unknown": signature["unknown"], "conflicts": signature["conflicts"]}


def _source_sha256(names: tuple) -> str:
    digest = hashlib.sha256()
    for name in names:
        digest.update(name.encode("utf-8") + b"\0" + (CONTRACTS_FOLDER / name).read_bytes())
    return digest.hexdigest()


def _sorted_digests(documents: list) -> list:
    return sorted(canonical_sha256(document) for document in documents)


def _digests(signature: dict, inspection: dict, index: dict, policy: dict, recipes: list, evidence: list) -> dict:
    """Section 8.7: input, reader, conditions, rule and evidence hashes; A60: policy and candidate set too. The whole inspection is
    the input, feature costs included, so a second inspection is a new input. Whole recipes, since recipe_identity leaves out what
    evidence changes, and that changes a selection."""
    bound = [{"recipe": recipe["recipe_id"], "conditions": recipe["profile_binding"]["conditions"]} for recipe in recipes]
    used = [fact for fact in signature["facts"] if fact["key"].startswith("conditions")]
    return {"input_sha256": canonical_sha256(inspection), "reader_sha256": _source_sha256(READER_SOURCES), "rule_sha256": _source_sha256(RULE_SOURCES),
            "conditions_sha256": canonical_sha256({"bound": _sorted_digests(bound), "used": _sorted_digests(used)}), "evidence_sha256": canonical_sha256(_sorted_digests(evidence)),
            "policy_sha256": canonical_sha256(policy), "candidate_set_sha256": canonical_sha256({"index": index, "recipes": _sorted_digests(recipes)})}


def _public_judgment(row: dict) -> dict:
    return {field: row[field] for field in ("recipe", "standing", "blocks", "branch", "open", "cost", "evidence_stage", "runtime_evidence", "rationale")}


def _bare_record(reason: str, signature_id) -> dict:
    """Fail closed: a valid record that chooses nothing and, with no formal block, cannot be replayed. `dataset` is a filler: the
    schema has no null for granularity, and nothing was selected at any unit."""
    return {"schema": "selection-record/1", "record_id": "selection.refused", "request": {"target": NOT_ESTABLISHED, "deliverable": NOT_ESTABLISHED},
            "signature_ref": signature_id if isinstance(signature_id, str) and signature_id else NOT_ESTABLISHED,
            "policy": {"version": None, "granularity": "dataset", "target": None, "quality_contract": None, "objective": None, "budgets": None}, "candidates": [],
            "decision": {"state": "abstained", "chosen_recipe": None, "reason": reason, "decision_record_ref": None}, "trials": [], "sample_roles": [], "dependencies": [], "required_extensions": []}


def _refused_record(report, arguments: dict) -> dict:
    return _bare_record(f"{NO_QUALIFIED}: inputs refused: {', '.join(sorted({finding.code for finding in report.errors}))}", arguments.get("signature_id"))


@reader_path("inspection", "index", "policy", "recipes", "evidence", refused=_refused_record)
def select_candidate(signature_id: str, inspection: dict, index: dict, policy: dict, recipes: list, evidence: list) -> dict:
    """A selection-record/1 for one signature of an inspection, from a candidate index, a policy, recipes and their evidence. The
    order of `recipes` and `evidence` does not matter. The order of the index is an input: it changes the record's rows, never the decision."""
    signatures = [item for item in inspection["signatures"] if item["signature_id"] == signature_id]
    if len(signatures) != 1 or not isinstance(recipes, list) or not isinstance(evidence, list):
        return _bare_record(f"{NO_QUALIFIED}: this signature or these lists cannot be read from the inputs", signature_id)
    try:
        hashes = _digests(signatures[0], inspection, index, policy, recipes, evidence)
    except OSError as error:  # a record that cannot name its rules cannot be replayed, so it chooses nothing
        return _bare_record(f"{NO_QUALIFIED}: rule sources unreadable: {type(error).__name__}", signature_id)
    by_recipe, by_evidence = _unique(recipes, "recipe_id"), _unique(evidence, "evidence_id")
    conditions = judge_candidates(signatures[0], [{"candidate": row["recipe_id"], "requires": row["requires"]} for row in index["candidates"]])
    rows = [_judged_row(row, judged, index, by_recipe, by_evidence, policy) for row, judged in zip(index["candidates"], conditions)]
    state, chosen, reason, restriction = _decision(rows, policy)
    formal = {"hashes": hashes, "values_role": policy["role"], "candidate_set": {"index_id": index["index_id"], "version": index["version"]}, "signature": _signature_summary(signatures[0]),
              "inspection": {"state": inspection["state"], "stop_reason": inspection["stop_reason"], "products_unread": inspection["products_unread"]},
              "judgments": [_public_judgment(row) for row in rows], "baseline": policy["baseline"], "sample_groups": policy["sample_groups"],
              "qualification_candidates": [row["recipe"] for row in rows if row["standing"] == "qualification-candidate"], "restricted_delivery": restriction,
              "claims": {"expert_support": _expert_support(index, by_recipe, by_evidence, policy), "policy_confirmed": False, "global_best": False},
              "post_selection_evidence": None, "learned_ranker": None}
    return {"schema": "selection-record/1", "record_id": f"selection.{canonical_sha256([signature_id, hashes])[:16]}", "request": {"target": policy["target"], "deliverable": policy["deliverable"]}, "signature_ref": signature_id,
            "policy": _policy_summary(policy), "candidates": [_candidate_record(row) for row in rows],
            "decision": {"state": state, "chosen_recipe": chosen, "reason": reason, "decision_record_ref": None}, "trials": [_trial(probe) for probe in inspection["probes"]],
            "sample_roles": policy["sample_roles"], "dependencies": [f"{name}:{value}" for name, value in sorted(hashes.items())], "formal": formal, "required_extensions": []}


@reader_path("record", "inspection", "index", "policy", "recipes", "evidence")
def check_selection_replay(record: dict, inspection: dict, index: dict, policy: dict, recipes: list, evidence: list) -> Report:
    """A60, SEL10: the selection again, on the inputs a caller holds now. Each hash that differs is named, and the old decision stands
    for nothing then, even if the same recipe wins. No finding means these inputs give this very record, and nothing more: what the
    inputs say may still be out of date, so a clean replay is no evidence of quality."""
    report = Report()
    current = select_candidate(record["signature_ref"], inspection, index, policy, recipes, evidence) if "formal" in record else {}
    if "formal" not in current:
        report.add("error", "$.formal", "reconstruction.selection.not_replayable", "no formal record on one side of this replay: nothing can be compared")
        return report
    changed = [name for name, value in sorted(current["formal"]["hashes"].items()) if value != record["formal"]["hashes"][name]]
    for name in changed:
        report.add("error", "$.formal.hashes", "reconstruction.selection.dependency_changed", f"{name}: this input is not the one the record was made from, so the old decision proves nothing about it")
    if current["decision"] != record["decision"]:
        report.add("error", "$.decision", "reconstruction.selection.decision_changed", f"these inputs give {current['decision']['state']} {current['decision']['chosen_recipe']}")
    if not changed and current != record:
        report.add("error", "$", "reconstruction.selection.record_altered", "the same inputs give another record: this one was changed after it was written")
    return report
