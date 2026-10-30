"""Status and completion report derived from the fact log (Core §6.4, §7.4; Control §4.5-4.6; FLOW-01, TIER-01).
Nothing here is stored: every value is derived from the facts at one head. Standard library only."""
from __future__ import annotations

from . import derivation as dv

LIMITATIONS = (
    "The control rules this helper applies (Control §1-§6 of the reconstruction v12.2 spec copy) did NOT pass the S0 "
    "spec review: obligation N1 was violated in all seven recorded review rounds. The two defects of round 7 (newer "
    "unresolved attempts not overtaking an older output; check attempts without a result counted nowhere) are fixed "
    "in v12.2, which has not yet been re-reviewed (round 8 pending). The helper implements the spec copy's Control "
    "part and agrees with its reference model on the tested fact sequences; that is not a review or a validation of "
    "the rules, and the derivation below is a mechanical consequence of unreviewed rules, not an established result. "
    "It gives no autonomous reconstruction capability.",
    "Reads are not observable with the local runner: attested artifacts are 'attested (declared inputs)' (DEC-10); "
    "undeclared reads cannot be detected.",
    "Receipts and run records are files in the workspace: the adapter checks their digests and consistency but cannot "
    "authenticate them.",
    "Human decisions are entered through a guard (refused in an agent's shell, explicit confirmation flag), not an "
    "authentication: the record cannot prove that a human wrote them.",
    "Conditions resolution evidence (G6) is unsupported: conditions were not re-resolved or compared against a "
    "snapshot before publish or the completion check.",
    "M3 is not available (G3 submission reconciliation and G4 metering are unsupported) and is refused. M2 is "
    "admitted only with a G5 qualification of this helper's task record (restart recovery, stale lock takeover): "
    "that qualifies persistence, not the rules.",
    "Maintainer decisions of 2026-10-30: the control layer ships; DEC-02 (library and CLI helper), DEC-01/DEC-08/"
    "DEC-09 (task record location and format), DEC-12 (first contract), DEC-13 (no shared store with hep-review) and "
    "DEC-14 (no delegation of human decisions) are approved. Shipping is not a review of the rules (above).",
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
                     "failed_check_draws": [list(x) for x in row["failed_check_draws"]],
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
    history = dv.task_history(log) if eff else {"failures": [], "failed_draws": [], "artifacts": {},
                                                "failed_check_draws": []}
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
            "failed_draws": [list(x) for x in history["failed_draws"]], "artifacts": history["artifacts"],
            "failed_check_draws": [list(x) for x in history["failed_check_draws"]]},
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
                   f"failed draws, {len(row['failed_check_draws'])} check attempts without a result, "
                   f"{row['chain_artifacts']} artifacts and {len(row['confirmation_results'])} "
                   f"confirmation-sample results on the dependency chain")
    hist = rep["3_scientific_evidence"]["task_history"]
    out.append(f"- task-wide: {len(hist['failures'])} fail/inconclusive, {len(hist['failed_draws'])} failed draws, "
               f"{len(hist['failed_check_draws'])} check attempts without a result, "
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


# ---------------------------------------------------------------- resumption summary (C2; Core §6.4)

RESUME_RULES = (
    "Never resubmit an attempt that is admitted, running, cancelling, unknown or abandoned: its outcome is not known "
    "to this session. Take its receipt if the run left one; if the run left none, record it lost (`receipt --lost`, "
    "termination unknown); reconcile an unknown or abandoned attempt only from a receipt that proves its outcome "
    "(`reconcile`), or ask a human to abandon it (`decide --action abandon`, in the human's terminal).",
    "Reconcile first, then take over an expired lease (`lock acquire`); a live lease of another owner is not taken "
    "over.",
    "When this summary and the actual state disagree (a run record exists that the record does not show, a process "
    "still runs), the actual state wins: record it through the commands above, and note the difference.",
)


def _dry_admit(log, step: str):
    """Would C admit a computation of `step` now? (capability is checked only at the real admission)"""
    import copy  # noqa: PLC0415
    trial = copy.deepcopy(log)
    try:
        dv.admit(trial, trial.head, "__resume_probe__", step, cost=0.0)
        return None
    except dv.Admission as exc:
        return str(exc)
    except dv.Rejected as exc:
        return f"rejected: {exc}"


def next_actions(log) -> list[dict]:
    """What may be done next, derived from the facts (in this order: settle attempts, human items, then work)."""
    actions = []
    for row in attempts(log):
        state = row["state"]
        if state in ("unknown", "abandoned"):
            actions.append({"do": "reconcile from a receipt that proves the outcome, or ask a human to abandon",
                            "attempt": row["attempt"], "state": state} if state == "unknown" else
                           {"do": "nothing to resubmit; reconcile if its outcome is later proven", "attempt":
                            row["attempt"], "state": state})
        elif state in ("admitted", "running", "cancelling"):
            actions.append({"do": "take the run's receipt (`receipt`), or record it lost (`receipt --lost`); never "
                                  "rerun it", "attempt": row["attempt"], "state": state})
    for item in pending_for_humans(log):
        if item["kind"] != "abandon or reconcile":
            actions.append({"do": f"ask a human: {item['kind']}", **{k: v for k, v in item.items() if k != "kind"}})
    if not dv.has_contract(log):
        actions.append({"do": "write the first contract" if not log.of("contract") else
                        "wait for the human approval of the first contract (M2/M3) or write a new contract"})
        return actions
    eff = dv.contract(log)
    for did, dl in eff["deliverables"].items():
        status = dv.deliverable_status(log, did)
        if status["met"]:
            if not any(p.get("deliverable") == did for p in log.of("publish")):
                actions.append({"do": "publish", "deliverable": did})
            continue
        for name in reversed(dv.chain_steps(log, dl.step)):
            if dv.bound(log, name) is not None:
                continue
            spec = eff["steps"][name]
            usable = [d for d in dv.candidates_raw(log, name) if dv.step_of(log, d) == name and dv.current(log, d)]
            if usable:
                latest = usable[-1]
                lab = dv.label(log, latest)
                missing = sorted(list(p) for p in spec.required if not dv.counted_result(log, latest, *p))
                if lab == "unchecked" and missing:
                    actions.append({"do": "admit the missing checks", "deliverable": did, "step": name,
                                    "target": latest, "checks": missing})
                else:
                    actions.append({"do": f"resolve {lab}", "deliverable": did, "step": name, "artifact": latest,
                                    "admission": _dry_admit(log, name) or "a new computation would be admitted"})
            else:
                actions.append({"do": "compute", "deliverable": did, "step": name,
                                "admission": _dry_admit(log, name) or "would be admitted"})
            break
        else:
            artifact = status["artifact"]
            if artifact is not None and dl.target == "T3C" and status["achieved"] != "T3C":
                actions.append({"do": "freeze, then confirm on an unexposed confirmation sample", "deliverable": did,
                                "artifact": artifact})
    return actions


def resume(log, task_log: str, head_digest: str | None, lease: dict, history: list[dict]) -> dict:
    """The resumption summary (Core §6.4): enough for a new session without the chat history. Facts only."""
    eff = dv.has_contract(log)
    rows = attempts(log)
    by_state: dict = {}
    for row in rows:
        by_state.setdefault(row["state"], []).append(row["attempt"])
    eff_seq = next((c["seq"] for c in contracts(log) if c["status"] == "effective"), None)
    from .task_record import encode_contract  # noqa: PLC0415
    return {
        "task_log": task_log, "head": log.head, "head_digest": head_digest, "mode": log.mode(),
        "derivation": dv.DERIVATION_VERSION,
        "limitation": LIMITATIONS[0],
        "contract": {"effective_seq": eff_seq, "effective": encode_contract(dv.contract(log)) if eff else None,
                     "states": contracts(log)},
        "deliverables": status(log)["deliverables"],
        "attempts_by_state": {k: sorted(v) for k, v in sorted(by_state.items())},
        "do_not_resubmit": sorted(a for s in ("admitted", "running", "cancelling", "unknown", "abandoned")
                                  for a in by_state.get(s, [])),
        "pending_for_humans": pending_for_humans(log),
        "freezes": [{"seq": f.seq, "step": f.get("step"), "samples": list(f.get("samples")),
                     "independent": list(f.get("independent") or ())} for f in log.of("freeze")],
        "samples": exposures(log),
        "accounts": status(log)["accounts"],
        "lease": {k: lease.get(k) for k in ("held", "owner", "expires", "pid", "host")},
        "lease_events": len(history),
        "rules": list(RESUME_RULES),
        "next_actions": next_actions(log),
    }
