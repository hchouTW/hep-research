"""Status and completion report derived from the fact log (Core §6.4, §7.4; Control §4.5-4.6; FLOW-01, TIER-01).
Nothing here is stored: every value is derived from the facts at one head. Standard library only."""
from __future__ import annotations

from . import derivation as dv

LIMITATIONS = (
    "The control rules this helper applies (Control §1-§6 of the reconstruction v12.1 spec copy) did NOT pass the S0 "
    "spec review: obligation N1 was violated in six recorded review rounds, and the last change (the single "
    "'overtaken' binding rule) was not reviewed at all. The helper implements the spec copy's Control part and "
    "agrees with its reference model on the tested fact sequences; that is not a review or a validation of the "
    "rules, and the derivation below is a mechanical consequence of unreviewed rules, not an established result. "
    "It gives no autonomous reconstruction capability.",
    "Reads are not observable with the local runner: attested artifacts are 'attested (declared inputs)' (DEC-10); "
    "undeclared reads cannot be detected.",
    "Receipts and run records are files in the workspace: the adapter checks their digests and consistency but cannot "
    "authenticate them.",
    "Human decisions are entered through a guard (refused in an agent's shell, explicit confirmation flag), not an "
    "authentication: the record cannot prove that a human wrote them.",
    "Conditions resolution evidence (G6) is unsupported: conditions were not re-resolved or compared against a "
    "snapshot before publish or the completion check.",
    "M2/M3 are not available (G5 persistent state and the C2 resumption stage are missing); the helper refuses "
    "admission under them.",
    "Defaults pending maintainer approval: DEC-01/DEC-08/DEC-09 (task record location and format), DEC-02 (library "
    "and CLI helper), DEC-12 (first contract), DEC-13 (no shared store with hep-review), DEC-14 (no delegation of "
    "human decisions).",
)


def _steps_seen(log) -> list[str]:
    names = list(dv.contract(log)["steps"]) if dv.has_contract(log) else []
    names += [name for name in log._by_step_out if name not in names and name not in dv.SPECIAL_STEPS]
    return names


def _attested_kind(log, digest) -> str:
    """attested (declared inputs): has a producer; unattested: computed, but usage or reads exceeded the declaration
    (or no usage under M2/M3); otherwise the output came from no computed attempt with an intent written by C."""
    if dv.producers(log, digest):
        return "attested (declared inputs)"
    if any(dv.intent_of(log, f.get("attempt")) is not None and dv.exec_status(log, f.get("attempt")) == "computed"
           for f in dv.output_facts(log, digest)):
        return "unattested"
    return "no producer (failed, cancelled, abandoned, or without an intent written by C)"


def artifacts(log) -> dict:
    found = {}
    for name in _steps_seen(log):
        rows = []
        for digest in dv.candidates_raw(log, name):
            rows.append({"digest": digest, "label": dv.label(log, digest) if dv.has_contract(log) else "no contract",
                         "kind": _attested_kind(log, digest),
                         "in_contract": dv.has_contract(log) and name in dv.contract(log)["steps"]})
        found[name] = {"bound": dv.bound(log, name) if dv.has_contract(log) and name in dv.contract(log)["steps"]
                       else None, "artifacts": rows}
    return found


def deliverables(log) -> dict:
    if not dv.has_contract(log):
        return {}
    rows = {}
    for did, dl in dv.contract(log)["deliverables"].items():
        row = dv.report_status(log, did)
        artifact = row["artifact"]
        seen = [{"digest": d, "label": dv.label(log, d)} for d in dv.candidates_raw(log, dl.step)]
        if row["met"]:
            state, reason = "done", "the achieved tier reaches the target"
        elif artifact is not None:
            state, reason = "partial", f"achieved {row['achieved'] or 'none'} is below the target {dl.target}"
        elif seen:
            state, reason = "blocked", "no artifact of the step binds: " + ", ".join(
                f"{x['digest']} {x['label']}" for x in seen)
        else:
            state, reason = "not started", "the step has no artifact yet"
        rows[did] = {"step": dl.step, "target": dl.target, "achieved": row["achieved"], "met": row["met"],
                     "required": dl.required, "state": state, "reason": reason, "artifact": artifact,
                     "artifact_label": dv.label(log, artifact) if artifact is not None else None,
                     "confirmation_required": dl.confirmation_required,
                     "independent_confirmation_required": dl.independent_confirmation,
                     "prior_failures": [list(x) for x in row["prior_failures"]],
                     "failed_draws": [list(x) for x in row["failed_draws"]],
                     "confirmation_results": [list(x) for x in row["confirmation_results"]],
                     "chain_artifacts": sum(len(dv.step_artifacts(log, n)) for n in dv.chain_steps(log, dl.step)),
                     "published": [{"seq": p.seq, "digest": p.get("digest"), "achieved": p.get("achieved"),
                                    "head": p.get("head"), "derivation": p.get("derivation")}
                                   for p in log.of("publish") if p.get("deliverable") == did]}
    return rows


def attempts(log) -> list[dict]:
    rows = []
    for intent in log.of("intent"):
        attempt = intent.get("attempt")
        rows.append({"attempt": attempt, "step": intent.get("step"), "state": dv.exec_status(log, attempt),
                     "cost": intent.get("cost"), "usage": dv.reported_usage(log, attempt),
                     "attested": dv.attested(log, attempt), "reads": list(intent.get("reads") or ()),
                     "inputs": dict(intent.get("inputs") or ())})
    for fact in log.of("admission_rejected"):
        rows.append({"attempt": fact.get("attempt"), "step": fact.get("step"), "state": "rejected",
                     "reason": fact.get("reason")})
    return rows


def exposures(log) -> dict:
    samples = dict(dv.contract(log)["samples"]) if dv.has_contract(log) else {}
    names = sorted(set(samples) | {f.get("sample") for f in log.of("exposure")})
    return {sample: {"role": samples.get(sample),
                     "exposures": [{"seq": e.seq, "writer": e.writer, "attempt": e.get("attempt")}
                                   for e in log.of_sample(sample) if e.kind == "exposure"],
                     "freezes": [f.seq for f in log.of("freeze") if sample in (f.get("samples") or ())],
                     "unblinded": any(d.get("action") == "unblind" and d.get("sample") == sample
                                      for d in log.of("decision"))}
            for sample in names}


def contracts(log) -> list[dict]:
    statuses = dv._contracts(log)[1]
    return [{"seq": c.seq, "status": statuses[c.seq]} for c in log.of("contract")]


def pending_for_humans(log) -> list[dict]:
    items = [{"kind": "approve_contract", "ref": row["seq"], "why": "the contract is not at least as strict, or is "
              "the first contract under M2/M3"} for row in contracts(log) if row["status"] == "pending_approval"]
    for row in attempts(log):
        if row["state"] == "unknown":
            items.append({"kind": "abandon or reconcile", "attempt": row["attempt"],
                          "why": "termination unconfirmed: no other attempt with the same side effect is admitted"})
    if dv.has_contract(log):
        for name, info in artifacts(log).items():
            for row in info["artifacts"]:
                if row["label"] == "producer_conflict":
                    items.append({"kind": "assign_producer", "digest": row["digest"],
                                  "why": "producers of different steps made the same digest"})
                elif row["label"] == "overtaken":
                    items.append({"kind": "approve_contract (pin)", "step": name, "digest": row["digest"],
                                  "why": "an output already seen binds again only through a human-approved pin"})
    return items


def status(log) -> dict:
    """The resumption-oriented status (Core §6.4) at the log's head."""
    eff = dv.has_contract(log)
    budget = dv.contract(log)["budget"] if eff else None
    return {"mode": log.mode(), "head": log.head, "effective_contract": eff, "contracts": contracts(log),
            "deliverables": {did: {k: row[k] for k in ("step", "target", "achieved", "met", "required", "state",
                                                       "reason", "artifact", "artifact_label")}
                             for did, row in deliverables(log).items()},
            "steps": artifacts(log), "attempts": attempts(log),
            "accounts": {"budget": budget, "used": dv.used(log), "in_flight": dv.in_flight(log),
                         "usage_reported": any(f.get("usage") is not None for f in log.of("receipt") + log.of("reconcile"))},
            "samples": exposures(log), "pending_for_humans": pending_for_humans(log),
            "derivation": dv.DERIVATION_VERSION}


def report(log, task_log: str, head_digest: str | None) -> dict:
    """The completion report (Core §7.4), paragraphs 1-7, with the limitations paragraph."""
    eff = dv.has_contract(log)
    rows = deliverables(log)
    required = [row for row in rows.values() if row["required"]]
    unsettled = [row["attempt"] for row in attempts(log)
                 if row["state"] in ("admitted", "running", "cancelling", "unknown")]
    complete = eff and bool(required) and all(row["met"] for row in required) and not unsettled
    steps = artifacts(log)
    unattested = [{"step": name, "digest": row["digest"]} for name, info in steps.items()
                  for row in info["artifacts"] if row["kind"] == "unattested"]
    checks = [{"seq": r.seq, "target": r.get("target"), "check": r.get("check"), "criteria": r.get("criteria"),
               "result": r.get("result"), "reason": r.get("reason"), "check_attempt": r.get("check_attempt"),
               "sample": r.get("sample"), "counted_sample": dv.result_sample(log, r)} for r in log.of("check_result")]
    history = dv.task_history(log) if eff else {"failures": [], "failed_draws": [], "artifacts": {}}
    accounts = status(log)["accounts"]
    limitations = list(LIMITATIONS)
    if accounts["budget"] is not None and not accounts["usage_reported"]:
        limitations.append("No receipt reported usage: the budget was enforced against declared costs only, not "
                           "against actual usage (G4 metering unsupported).")
    return {
        "overall": "complete" if complete else ("partial completion" if eff else "no effective contract"),
        "unsettled_attempts": unsettled,
        "1_deliverables": rows,
        "2_computation": {"steps": steps, "unattested": unattested, "attempts": attempts(log)},
        "3_scientific_evidence": {"check_results": checks, "task_history": {
            "failures": [list(x) for x in history["failures"]],
            "failed_draws": [list(x) for x in history["failed_draws"]], "artifacts": history["artifacts"]},
            "samples": exposures(log),
            "freezes": [{"seq": f.seq, "step": f.get("step"), "samples": list(f.get("samples")),
                         "independent": list(f.get("independent") or ()), "plan": f.get("plan")}
                        for f in log.of("freeze")]},
        "4_contracts_and_decisions": {"contracts": contracts(log), "decisions": [
            {"seq": d.seq, "writer": d.writer, **{k: v for k, v in d.fields.items()}} for d in log.of("decision")],
            "pending_for_humans": pending_for_humans(log)},
        "5_limitations": limitations,
        "6_unconfirmed_risks": {"unknown_or_abandoned": [row for row in attempts(log)
                                                         if row["state"] in ("unknown", "abandoned")],
                                "in_flight": accounts["in_flight"], "budget": accounts["budget"],
                                "used": accounts["used"]},
        "7_reproduction": {"task_log": task_log, "head": log.head, "head_digest": head_digest,
                           "derivation": dv.DERIVATION_VERSION, "mode": log.mode(),
                           "receipts": [f.get("record") for f in log.of("receipt") + log.of("reconcile")
                                        if f.get("record")]},
    }


def markdown(rep: dict) -> str:
    """A readable rendering of report(); the JSON form is the reference."""
    out = [f"# Completion report: {rep['overall']}", "", "## 1. Deliverables", "",
           "| Deliverable | Required | Target | Achieved | State | Reason |", "|---|---|---|---|---|---|"]
    for did, row in rep["1_deliverables"].items():
        out.append(f"| {did} | {'yes' if row['required'] else 'no'} | {row['target']} | {row['achieved'] or 'none'} "
                   f"| {row['state']} | {row['reason']} |")
    out += ["", "## 2. Computation", ""]
    for name, info in rep["2_computation"]["steps"].items():
        arts = ", ".join(f"`{a['digest'][:12]}` {a['label']} ({a['kind']})" for a in info["artifacts"]) or "none"
        out.append(f"- {name}: bound {('`' + info['bound'][:12] + '`') if info['bound'] else 'none'}; {arts}")
    out += ["", "## 3. Scientific evidence", ""]
    for did, row in rep["1_deliverables"].items():
        out.append(f"- {did}: {len(row['prior_failures'])} historical fail/inconclusive, {len(row['failed_draws'])} "
                   f"failed draws, {row['chain_artifacts']} artifacts and {len(row['confirmation_results'])} "
                   f"confirmation-sample results on the dependency chain")
    hist = rep["3_scientific_evidence"]["task_history"]
    out.append(f"- task-wide: {len(hist['failures'])} fail/inconclusive, {len(hist['failed_draws'])} failed draws, "
               f"artifacts per step {hist['artifacts']}")
    for res in rep["3_scientific_evidence"]["check_results"]:
        out.append(f"- check `{res['check'][:12]}` on `{res['target'][:12]}`: {res['result']} ({res['reason'] or ''})")
    out += ["", "## 4. Contracts and decisions", ""]
    out += [f"- contract at seq {c['seq']}: {c['status']}" for c in rep["4_contracts_and_decisions"]["contracts"]]
    out += [f"- decision at seq {d['seq']} by {d['writer']}: {d['action']}"
            for d in rep["4_contracts_and_decisions"]["decisions"]]
    out += [f"- pending for a human: {p}" for p in rep["4_contracts_and_decisions"]["pending_for_humans"]]
    out += ["", "## 5. Scope and limitations", ""] + [f"- {x}" for x in rep["5_limitations"]]
    risks = rep["6_unconfirmed_risks"]
    out += ["", "## 6. Unconfirmed risks", "",
            f"- unknown or abandoned attempts: {[r['attempt'] for r in risks['unknown_or_abandoned']] or 'none'}; "
            f"in flight {risks['in_flight']}, used {risks['used']}, budget {risks['budget']}"]
    repro = rep["7_reproduction"]
    out += ["", "## 7. Reproduction", "",
            f"- task log `{repro['task_log']}` at head {repro['head']} (last line `{repro['head_digest']}`), "
            f"derivation {repro['derivation']}, mode {repro['mode']}", ""]
    return "\n".join(out)
