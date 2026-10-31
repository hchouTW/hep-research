#!/usr/bin/env python3
"""Control-layer helper: task contract, fact log, derivation, admission, receipts, human decisions, publish and the
completion report (reconstruction v12 stages C1 and C2; DEC-02, library + CLI, approved by the maintainer on
2026-10-30, who also decided that the control layer ships). Standard library only.

Status: implements Control §1-§6 of the reconstruction v12.2 spec copy and agrees with its reference model on the
tested fact sequences (92 scenarios, 44 mutations, random sequences). The control rules did NOT pass the S0 spec
review (obligation N1 violated in all eight rounds); the round-7 defects are fixed in v12.2, and round 8 left three
open defects, listed in every report. The derivation is a mechanical consequence of unreviewed rules, not a reviewed or
validated result, and the helper gives no autonomous reconstruction capability. Every report carries that
limitation.

Task record (DEC-01/08/09, approved 2026-10-30): one append-only JSON-lines file, by default
<project>/hep-research-artifacts/<task>/task-log/task-log.jsonl, separate from every run's work folder. Each line
carries seq, batch, kind, writer, fields, the SHA-256 of the previous line, the operation id and the request digest;
every load verifies the chain and replays the facts. Agents never edit the file: every fact goes through a command
below, with compare-and-set on --expect-head (the head printed by the previous command or by `status`) and, when
given, --expect-digest (the last line's SHA-256). --op ID makes a write idempotent: repeating it with the same request
returns the first result. The chain detects an edit of any line except the last; keep the head_digest a command
prints outside the record and pass it to --expect-digest or `verify --anchor-digest` to cover that line too.
Writers (Control §2): the agent writes contract, freeze and exposure; C (this helper) writes session, intent,
admission_rejected, reuse, cancel_request and publish; the adapter writes start, receipt and check_result (from
run_workflow.py receipts) and reconcile; only a human writes decision. Order for every attempt: `admit`, then
`start` (right before the run begins), then run the step, then `receipt` (or `receipt --lost`).
Commands:
  init     --task-log FILE [--mode M1|M2|M3]                         create the record (session fact)
  contract --task-log FILE --file CONTRACT.json --expect-head N [--dry-run]
  freeze   --task-log FILE --file FREEZE.json --expect-head N        {"step", "samples", "required", "independent"?, "plan"?}
  exposure --task-log FILE --sample S [--activity A] --expect-head N
  admit    --task-log FILE --attempt ID (--step STEP | --check C --criterion K --target DIGEST | --reuse-source DIGEST
           --step STEP) --cost X [--read SAMPLE ...] --declaration DECL.json --qualification QUAL.json --expect-head N
  receipt  --task-log FILE --receipt R.receipt.json --work DIR [--usage none|wall_s|cpu_s] --expect-head N
  receipt  --task-log FILE --not-started --attempt ID --runner-output OUT.json --expect-head N
  decide   --task-log FILE --action KIND [--ref SEQ] [--digest D] [--step S] [--old-identity I] [--new-identity I]
           [--sample S] [--attempt A] [--basis TEXT] --confirm-human --expect-head N        (humans only)
  publish  --task-log FILE --deliverable ID --expect-head N
  status   --task-log FILE        derive at the current head (resumption view)
  report   --task-log FILE [--format json|markdown] [--out FILE]      completion report (Core §7.4)
  verify   --task-log FILE [--anchor-digest SHA256 [--anchor-seq N]]   verify the chain, replay every fact
 C2 (resumption and recovery; the same rules, still not through S0):
  resume   --task-log FILE        resumption summary for a new session: what not to resubmit, what to do next
  receipt  --task-log FILE --lost --attempt ID [--reason TEXT] --expect-head N   a run that left no receipt: unknown
  reconcile --task-log FILE --receipt R.receipt.json --work DIR --expect-head N  outcome of an unknown/abandoned attempt
  start    --task-log FILE --attempt ID --expect-head N        execution began: record it BEFORE running the step
  cancel   --task-log FILE --attempt ID [--never-started] --expect-head N   C's cancel request (stopping is B's)
  lock     acquire|release|status --task-log FILE [--owner NAME] [--lease-token TOKEN] [--lease-s SECONDS]
           lease lock (Control §5.5): acquire prints a token once; renew (acquire) and release need it
  recover  --task-log FILE        remove a torn, never acknowledged last line (kept aside, recorded)
After a restart: run `resume`; settle every admitted, running or unknown attempt first (take its receipt, record it
lost, reconcile it from a receipt that proves its outcome, or have a human abandon it) -- never resubmit it; then
acquire the lease (a new acquisition, takeover or not, is refused while any attempt is unsettled or a lease is live).
A live lease refuses every write without its token (--lease-token) except a human decision; under M2/M3 every such
write needs the token of a live lease. The owner name is only a label. The lease never replaces compare-and-set.
Contract JSON (closed format, Control §1.1): {"steps": {NAME: {"program", "environment", "external": [],
"upstream": [], "checked": false, "required_checks": [[CHECK_SHA256, CRITERION_SHA256]], "na_allowed": [],
"check_inputs": [[CHECK_SHA256, STEP]], "family": null, "round": null, "rerun_allowed": false, "pin": null}},
"deliverables": {ID: {"step", "target": "T2"|"T3E"|"T3C", "required": true, "confirmation_required": true,
"independent_confirmation_required": false}}, "families": {NAME: {"final_round", "convergence_check",
"mode_check"}}, "samples": {NAME: ROLE}, "budget": null|NUMBER}; program and environment are required in a step, the
other step and deliverable fields default as shown; unknown fields are refused.
Admission compares the executor's declared capabilities (executor_capabilities.py declare/qualify) with the
record's execution mode (CAP-01): M2 needs G1, G2 and G5 (G5 is qualified with this helper's record as the persistent
state, stage C2), M3 also G3 and G4, which are unsupported, so M3 is refused. A run_workflow.py
receipt is bound to the admitted attempt by its attempt id: run the step with --receipt-dir DIR and --attempt-prefix
P so that P + the workflow step id equals the admitted attempt id. An unconfirmed termination becomes a receipt with
termination unknown. --usage auto (default) reports no usage under M1, so the budget holds only against declared
costs, and wall_s under M2/M3, where receipts must carry usage; with wall_s or cpu_s the declared costs and the
budget are in that unit.
Human decisions: `decide` is a guard, not an enforcement. It refuses when the shell carries an agent marker
(CLAUDECODE, CLAUDE_CODE_ENTRYPOINT, AI_AGENT) and requires --confirm-human. An agent must never run it, nor unset
those variables to get past it; the record cannot prove that a human wrote a decision.
Output: one JSON object with "status". Exit codes: 0 ok; 1 refused (admission rejected -- the rejection is written
--, deliverable not met, decision guard) or rerun-required (stale head: re-read, re-derive, retry); 2 rejected (bad
input, a fact that does not validate, a corrupt record, a missing file).
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PLUGIN))
from core.status import exit_code  # noqa: E402
from control_layer_support import completion  # noqa: E402
from control_layer_support import derivation as dv  # noqa: E402
from control_layer_support import lease as leases  # noqa: E402
from control_layer_support.task_record import (CorruptRecord, OperationConflict, TaskRecord,  # noqa: E402
                                               decode_contract, decode_fields, encode_fields)

AGENT_MARKERS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "AI_AGENT")
USAGE_FIELDS = ("auto", "none", "wall_s", "cpu_s")


def _read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _fact_json(fact) -> dict:
    return {"seq": fact.seq, "kind": fact.kind, "writer": fact.writer, "fields": encode_fields(fact.kind, fact.fields)}


def _written(outcome, **extra) -> dict:
    out = {"status": "refused" if outcome.refusal else "ok", "head": outcome.head, "head_digest": outcome.head_digest,
           "written": [_fact_json(f) for f in outcome.facts], **extra}
    if outcome.replayed:
        out["replayed"] = True
    if outcome.refusal:
        out["reason"] = outcome.refusal
    return out


def _transact(args, operation, request: dict, **extra) -> dict:
    record = TaskRecord(args.task_log)

    def guard(log):
        leases.check_write(Path(args.task_log), getattr(args, "lease_token", None), log.mode(),
                           args.command == "decide")
    outcome = record.transact(operation, args.expect_head, args.expect_digest, args.op,
                              {"command": args.command, **request}, guard=guard)
    return _written(outcome, **extra)


# ---------------------------------------------------------------- agent facts

def cmd_contract(args) -> dict:
    spec = decode_contract(_read_json(args.file))
    if args.dry_run:
        loaded = TaskRecord(args.task_log).read()
        log = loaded.log
        log.append("contract", "agent", log.head, spec=spec)
        return {"status": "ok", "dry_run": True, "would_be": dv.contract_status(log, log.facts[-1]),
                "head": loaded.log.head - 1}
    state = {}

    def operation(log):
        fact = log.append("contract", "agent", log.head, spec=spec)
        state["status"] = dv.contract_status(log, fact)
    out = _transact(args, operation, {"spec": encode_fields("contract", {"spec": spec})})
    if "status" in state:
        out["contract_status"] = state["status"]
    return out


def cmd_freeze(args) -> dict:
    raw = _read_json(args.file)
    fields = decode_fields("freeze", raw)
    return _transact(args, lambda log: log.append("freeze", "agent", log.head, **fields), {"freeze": raw})


def cmd_exposure(args) -> dict:
    fields = {"sample": args.sample, **({"attempt": args.activity} if args.activity else {})}
    return _transact(args, lambda log: log.append("exposure", "agent", log.head, **fields), fields)


# ---------------------------------------------------------------- C: admission and publish

def capability_check(declaration: Path, qualification: Path):
    """CAP-01: the executor's declared, qualified capabilities against the guarantees the mode requires."""
    import executor_capabilities as caps  # noqa: PLC0415  (sibling script)
    decl, qual = _read_json(declaration), _read_json(qualification)

    def check(mode):
        verdict = caps.admit(decl, qual, list(caps.MODE_REQUIRES[mode]))
        if verdict["status"] == "ok":
            return None
        return f"mode {mode} needs {', '.join(caps.MODE_REQUIRES[mode])}; " + "; ".join(
            f"{g}: {why}" for g, why in sorted(verdict["refused"].items()))
    return check


def cmd_admit(args) -> dict:
    is_check = args.check is not None or args.criterion is not None or args.target is not None
    if is_check and not (args.check and args.criterion and args.target):
        raise ValueError("a check attempt names --check, --criterion and --target")
    step = args.step or ("__check__" if is_check else None)
    if step is None:
        raise ValueError("name --step (or --check/--criterion/--target for a check attempt)")
    capability = capability_check(args.declaration, args.qualification)
    request = {"attempt": args.attempt, "step": step, "cost": repr(args.cost), "reads": args.read,
               "check": [args.check, args.criterion, args.target] if is_check else None,
               "reuse_source": args.reuse_source,
               "capabilities": [hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                for p in (args.declaration, args.qualification)]}

    def operation(log):
        dv.admit(log, log.head, args.attempt, step, cost=args.cost, reads=tuple(args.read),
                 check=(args.check, args.criterion, args.target) if is_check else None,
                 reuse_source=args.reuse_source, capability=capability)
    return _transact(args, operation, request)


def cmd_publish(args) -> dict:
    return _transact(args, lambda log: dv.publish(log, log.head, args.deliverable), {"deliverable": args.deliverable})


# ---------------------------------------------------------------- adapter: run_workflow.py receipts -> facts

def receipt_facts(receipt: dict, receipt_sha: str, work: Path, usage_field: str, intent, mode: str = "M1",
                  kind: str = "receipt") -> list:
    """Facts for one run_workflow.py receipt (B2): a receipt (end status; termination confirmed, or unknown when the
    runner says unconfirmed; the artifact digest as the output whenever termination is confirmed and the run wrote an
    output, also when the step failed: an output once seen stays seen, Control §4.2 overtaken),
    and, for a check run whose result bound to the run, one check_result per sample used (or one without a sample).
    Raises ValueError when the receipt and its run record do not agree."""
    for key in ("attempt", "end_status", "termination", "artifact_digest", "environment_ref"):
        if key not in receipt:
            raise ValueError(f"the receipt has no {key}")
    end = receipt["end_status"]
    if end not in dv.END_VALUES:
        raise ValueError(f"unknown end status {end!r}")
    termination = {"confirmed": "confirmed", "unconfirmed": "unknown"}.get(receipt["termination"])
    if termination is None:
        raise ValueError(f"unknown termination {receipt['termination']!r}")
    ref = receipt["environment_ref"]
    run_record_path = work / ref["run_record"]
    run_record_bytes = run_record_path.read_bytes()
    if hashlib.sha256(run_record_bytes).hexdigest() != ref.get("sha256"):
        raise ValueError("the run record's SHA-256 differs from the one the receipt cites")
    run_record = json.loads(run_record_bytes.decode("utf-8"))
    outputs = (receipt["artifact_digest"],) if termination == "confirmed" and receipt.get("outputs") else ()
    usage = None
    if usage_field == "auto":
        usage_field = "wall_s" if mode in ("M2", "M3") else "none"
    if usage_field != "none":
        usage = (receipt.get("usage") or {}).get(usage_field)
        if usage is None:
            raise ValueError(f"the receipt reports no usage {usage_field}")
    observed = receipt.get("observed_inputs") or {}
    record = {"receipt_sha256": receipt_sha, "run_record": ref["run_record"], "run_record_sha256": ref["sha256"],
              "runner_attempt": receipt["attempt"], "runner_step": receipt.get("step"),
              "artifact_digest": receipt["artifact_digest"], "outputs": receipt.get("outputs", []),
              "reads_observable": bool(observed.get("observable")), "usage": receipt.get("usage"),
              "termination": receipt["termination"], "started": receipt.get("started"), "ended": receipt.get("ended")}
    facts = [(kind, "adapter", {"attempt": intent.get("attempt"), "end": end, "termination": termination,
                                     "outputs": outputs, "usage": usage, "observed_exceeds_declared": False,
                                     "record": record})]
    bind = receipt.get("check_result")
    declared = (run_record.get("extension") or {}).get("check")
    if bind is not None:
        if not isinstance(declared, dict):
            raise ValueError("the receipt carries a check result but its run record declares no check")
        if bind.get("bound"):
            samples = list(bind.get("samples") or []) or [None]
            for sample in samples:
                facts.append(("check_result", "adapter", {
                    "target": declared["target_artifact_digest"], "check": declared["check_digest"],
                    "criteria": declared["criterion_digest"], "result": bind.get("result"),
                    "reason": bind.get("reason"), "check_attempt": intent.get("attempt"), "sample": sample,
                    "record": {"receipt_sha256": receipt_sha, "run_record_sha256": ref["sha256"],
                               "role": declared.get("role"), "type": declared.get("type")}}))
    return facts


def cmd_receipt(args) -> dict:
    if args.lost:
        if not args.attempt:
            raise ValueError("--lost needs --attempt")
        attempt = args.attempt
        facts = [("receipt", "adapter", {"attempt": attempt, "end": "failure", "termination": "unknown",
                                         "outputs": (), "observed_exceeds_declared": False,
                                         "record": {"lost": True, "reason": args.reason or "no receipt or run record "
                                                    "of this attempt was found; its outcome is unknown"}})]
        request = {"lost": attempt, "reason": args.reason}
    elif args.not_started:
        if not (args.attempt and args.runner_output):
            raise ValueError("--not-started needs --attempt and --runner-output")
        runner_bytes = Path(args.runner_output).read_bytes()
        runner = json.loads(runner_bytes.decode("utf-8"))
        if runner.get("status") != "rejected" or runner.get("steps"):
            raise ValueError("a not-started receipt needs the runner's own refusal (status rejected, no step run)")
        attempt = args.attempt
        facts = [("receipt", "adapter", {"attempt": attempt, "end": "failure", "termination": "confirmed",
                                         "outputs": (), "observed_exceeds_declared": False,
                                         "record": {"not_started": True, "runner_output_sha256":
                                                    hashlib.sha256(runner_bytes).hexdigest(),
                                                    "runner_error": runner.get("error")}})]
        request = {"not_started": attempt, "runner_output": facts[0][2]["record"]["runner_output_sha256"]}
    else:
        if not (args.receipt and args.work):
            raise ValueError("a receipt needs --receipt and --work (the run's work folder)")
        receipt_bytes = Path(args.receipt).read_bytes()
        receipt = json.loads(receipt_bytes.decode("utf-8"))
        attempt = receipt.get("attempt")
        facts = None
        request = {"receipt": hashlib.sha256(receipt_bytes).hexdigest(), "usage": args.usage}
    state = {}

    def operation(log):
        intent = dv.intent_of(log, attempt)
        if intent is None:
            raise dv.Rejected(f"attempt {attempt!r} has no intent written by C: admit it first (an output without "
                              f"an intent is not usable)")
        if dv.terminal_fact(log, attempt) is not None or dv.exec_status(log, attempt) not in (
                "admitted", "running", "cancelling"):
            raise dv.Rejected(f"attempt {attempt!r} is {dv.exec_status(log, attempt)}: a receipt is taken only for "
                              f"an admitted or running attempt")
        items = facts if facts is not None else receipt_facts(receipt, request["receipt"], Path(args.work),
                                                              args.usage, intent, log.mode())
        consumed = dict(intent.get("inputs") or ())
        extra = {k: v for k, v in consumed.items() if k != "target"}
        for kind, _, fields in items:
            if kind == "check_result":
                state["identity_matches"] = intent.get("step") == "__check__" and intent.get(
                    "identity") == dv.check_identity(fields["check"], fields["criteria"], fields["target"], extra)
        log.append_batch(items, log.head)
    out = _transact(args, operation, request)
    if "identity_matches" in state and not state["identity_matches"]:
        out["warning"] = ("the run's declared check, criterion or target differs from the admitted check attempt (or "
                          "the attempt was not admitted as a check): a pass does not count; a fail or inconclusive "
                          "still holds its target")
    return out


# ---------------------------------------------------------------- human decisions (guard, not enforcement)

def cmd_decide(args) -> dict:
    markers = [name for name in AGENT_MARKERS if os.environ.get(name)]
    if markers:
        return {"status": "refused", "reason": f"this shell carries an agent marker ({', '.join(markers)}): decisions "
                "are written only by a human, in the human's own terminal (DEC-14). This is a guard, not an "
                "enforcement; an agent must not work around it."}
    if not args.confirm_human:
        return {"status": "refused", "reason": "a decision needs --confirm-human, given by the human who decides"}
    fields = {"action": args.action}
    for key in ("ref", "digest", "step", "old_identity", "new_identity", "sample", "attempt", "basis"):
        value = getattr(args, key)
        if value is not None:
            fields[key] = value
    decode_fields("decision", encode_fields("decision", fields))
    return _transact(args, lambda log: log.append("decision", "human", log.head, **fields), fields)


# ---------------------------------------------------------------- reading

def cmd_status(args) -> dict:
    loaded = TaskRecord(args.task_log).read()
    return {"status": "ok", "head_digest": loaded.head_digest, **completion.status(loaded.log)}


def cmd_report(args) -> dict:
    loaded = TaskRecord(args.task_log).read()
    rep = completion.report(loaded.log, str(args.task_log), loaded.head_digest)
    if args.out:
        text = completion.markdown(rep) if args.format == "markdown" else json.dumps(rep, indent=1, sort_keys=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        return {"status": "ok", "overall": rep["overall"], "head": loaded.log.head, "out": str(args.out)}
    if args.format == "markdown":
        return {"status": "ok", "overall": rep["overall"], "head": loaded.log.head,
                "markdown": completion.markdown(rep)}
    return {"status": "ok", **rep}


def cmd_verify(args) -> dict:
    loaded = TaskRecord(args.task_log).read()
    out = {"status": "ok", "head": loaded.log.head, "head_digest": loaded.head_digest, "mode": loaded.log.mode()}
    if args.anchor_digest is not None:
        anchor_seq = args.anchor_seq if args.anchor_seq is not None else loaded.log.head - 1
        if not 0 <= anchor_seq < loaded.log.head or \
                hashlib.sha256(loaded.raw[anchor_seq]).hexdigest() != args.anchor_digest:
            return {**out, "status": "rejected", "error": f"line {anchor_seq} does not have the anchored digest: "
                    f"the record was changed after the anchor was taken"}
    return out


# ---------------------------------------------------------------- C2: reconcile, cancel, resume, lease, recover

def cmd_reconcile(args) -> dict:
    """Adapter: a receipt that proves the outcome of an unknown or abandoned attempt (Control §3)."""
    receipt_bytes = Path(args.receipt).read_bytes()
    receipt = json.loads(receipt_bytes.decode("utf-8"))
    attempt = receipt.get("attempt")
    if receipt.get("termination") != "confirmed":
        raise ValueError("a reconciliation needs a receipt with termination confirmed; an unconfirmed one changes "
                         "nothing")
    request = {"receipt": hashlib.sha256(receipt_bytes).hexdigest(), "usage": args.usage}

    def operation(log):
        intent = dv.intent_of(log, attempt)
        if intent is None:
            raise dv.Rejected(f"attempt {attempt!r} has no intent written by C")
        state = dv.exec_status(log, attempt)
        if state not in ("unknown", "abandoned"):
            raise dv.Rejected(f"attempt {attempt!r} is {state}: a reconcile takes effect only for unknown or "
                              f"abandoned attempts")
        log.append_batch(receipt_facts(receipt, request["receipt"], Path(args.work), args.usage, intent, log.mode(),
                                       kind="reconcile"), log.head)
    return _transact(args, operation, request)


def cmd_start(args) -> dict:
    """Adapter: execution of an admitted attempt has begun (Control §3 admitted -> running). Record it right before
    the run starts, so that a cancel request can never settle an attempt whose process may be running."""
    def operation(log):
        state = dv.exec_status(log, args.attempt)
        if dv.intent_of(log, args.attempt) is None or state != "admitted":
            raise dv.Rejected(f"attempt {args.attempt!r} is {state}: start is recorded only for an admitted attempt")
        log.append("start", "adapter", log.head, attempt=args.attempt)
    return _transact(args, operation, {"attempt": args.attempt})


def cmd_cancel(args) -> dict:
    """C's cancel request. It records the request; stopping the process is B's (run_workflow.py has no cancel
    operation: stop its process group yourself), and the receipt decides the state. For an attempt with no start
    fact the model settles it as cancelled at once, so the caller must state --never-started: an attempt whose run
    may be in progress is first given its `start`, and then cancelling leaves it open for its receipt."""
    def operation(log):
        state = dv.exec_status(log, args.attempt)
        if dv.intent_of(log, args.attempt) is None or state not in ("admitted", "running"):
            raise dv.Rejected(f"attempt {args.attempt!r} is {state}: only an admitted or running attempt is cancelled")
        if state == "admitted" and not args.never_started:
            raise dv.Rejected(f"attempt {args.attempt!r} has no start fact: cancelling it now settles it as cancelled "
                              f"and refuses its later receipt. If its run began, record `start` first; if it never "
                              f"started, say so with --never-started")
        log.append("cancel_request", "C", log.head, attempt=args.attempt)
    return _transact(args, operation, {"attempt": args.attempt, "never_started": bool(args.never_started)})


def cmd_resume(args) -> dict:
    record = TaskRecord(args.task_log)
    loaded = record.read()
    summary = completion.resume(loaded.log, str(args.task_log), loaded.head_digest,
                                leases.lease_state(Path(args.task_log)), leases.read_history(Path(args.task_log)))
    return {"status": "ok", **summary}


def cmd_lock(args) -> dict:
    record = TaskRecord(args.task_log)
    path = Path(args.task_log)
    if args.action == "status":
        return {"status": "ok", "lease": leases.lease_state(path), "history": leases.read_history(path)}
    with record.locked():
        log = record.read().log
        if args.action == "release":
            return {"status": "ok", **leases.release(path, args.lease_token)}
        if not args.owner and args.lease_token is None:
            raise ValueError("lock acquire needs --owner (a new lease) or --lease-token (a renewal)")
        unsettled = [row["attempt"] for row in completion.attempts(log) if row["state"] in leases.UNSETTLED]
        return {"status": "ok", **leases.acquire(path, args.owner, args.lease_s, unsettled, args.lease_token)}


def cmd_recover(args) -> dict:
    return {"status": "ok", **TaskRecord(args.task_log).recover()}


def cmd_init(args) -> dict:
    outcome = TaskRecord(args.task_log).create(args.mode)
    return _written(outcome)


COMMANDS = {"init": cmd_init, "contract": cmd_contract, "freeze": cmd_freeze, "exposure": cmd_exposure,
            "admit": cmd_admit, "receipt": cmd_receipt, "decide": cmd_decide, "publish": cmd_publish,
            "status": cmd_status, "report": cmd_report, "verify": cmd_verify, "reconcile": cmd_reconcile,
            "cancel": cmd_cancel, "start": cmd_start, "resume": cmd_resume, "lock": cmd_lock, "recover": cmd_recover}
WRITES = ("contract", "freeze", "exposure", "admit", "receipt", "decide", "publish", "reconcile", "cancel", "start")


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    cmds = {name: sub.add_parser(name) for name in COMMANDS}
    for name, cmd in cmds.items():
        cmd.add_argument("--task-log", type=Path, required=True)
        if name in WRITES:
            cmd.add_argument("--expect-head", type=int, required=True, help="the head the caller derived from")
            cmd.add_argument("--expect-digest", help="the SHA-256 of the record's last line (head continuity)")
            cmd.add_argument("--op", help="operation id: a repeated write with the same request is not appended twice")
            if name != "decide":
                cmd.add_argument("--lease-token", help="the token `lock acquire` returned (needed while a lease is "
                                 "live, and always under M2/M3)")
    cmds["init"].add_argument("--mode", choices=dv.MODES, default="M1")
    for name in ("contract", "freeze"):
        cmds[name].add_argument("--file", type=Path, required=True)
    cmds["contract"].add_argument("--dry-run", action="store_true", help="say whether it would take effect; write nothing")
    cmds["exposure"].add_argument("--sample", required=True)
    cmds["exposure"].add_argument("--activity", help="the attempt or activity that looked at the sample (a label)")
    adm = cmds["admit"]
    adm.add_argument("--attempt", required=True)
    adm.add_argument("--step")
    adm.add_argument("--cost", type=float, required=True, help="declared cost (finite, >= 0; budget unit)")
    adm.add_argument("--read", action="append", default=[], help="a sample the attempt reads (repeatable)")
    adm.add_argument("--check", help="check digest (SHA-256 of the check program)")
    adm.add_argument("--criterion", help="criterion digest (SHA-256 of the criteria file)")
    adm.add_argument("--target", help="target artifact digest")
    adm.add_argument("--reuse-source", help="artifact digest to reuse (same step, same identity)")
    adm.add_argument("--declaration", type=Path, required=True, help="executor_capabilities.py declare output")
    adm.add_argument("--qualification", type=Path, required=True, help="executor_capabilities.py qualify output")
    rec = cmds["receipt"]
    rec.add_argument("--receipt", type=Path, help="a run_workflow.py <attempt>.receipt.json")
    rec.add_argument("--work", type=Path, help="the run's work folder (holds runs/<step>.computational-run.json)")
    rec.add_argument("--usage", choices=USAGE_FIELDS, default="auto",
                     help="auto: none under M1, wall_s under M2/M3 (where receipts must carry usage)")
    rec.add_argument("--lost", action="store_true", help="no receipt or run record exists: termination unknown")
    rec.add_argument("--reason", help="with --lost: why the outcome is unknown")
    rec.add_argument("--not-started", action="store_true", help="the runner refused the step before starting it")
    rec.add_argument("--attempt", help="with --not-started: the admitted attempt")
    rec.add_argument("--runner-output", type=Path, help="with --not-started: run_workflow.py's JSON output")
    dec = cmds["decide"]
    dec.add_argument("--action", required=True, choices=sorted(dv.DECISIONS))
    dec.add_argument("--ref", type=int, help="approve_contract: the contract's sequence number")
    dec.add_argument("--digest")
    dec.add_argument("--step")
    dec.add_argument("--old-identity")
    dec.add_argument("--new-identity")
    dec.add_argument("--sample")
    dec.add_argument("--attempt")
    dec.add_argument("--basis", help="what the decision rests on (for the record)")
    dec.add_argument("--confirm-human", action="store_true", help="the human deciding confirms it is a human")
    cmds["publish"].add_argument("--deliverable", required=True)
    cmds["reconcile"].add_argument("--receipt", type=Path, required=True)
    cmds["reconcile"].add_argument("--work", type=Path, required=True)
    cmds["reconcile"].add_argument("--usage", choices=USAGE_FIELDS, default="auto")
    cmds["cancel"].add_argument("--attempt", required=True)
    cmds["cancel"].add_argument("--never-started", action="store_true",
                                help="the attempt has no start fact and its run never began (it is settled at once)")
    cmds["start"].add_argument("--attempt", required=True)
    cmds["lock"].add_argument("action", choices=("acquire", "release", "status"))
    cmds["lock"].add_argument("--owner", help="a label for a new lease")
    cmds["lock"].add_argument("--lease-token", help="the current lease's token (renew, release)")
    cmds["lock"].add_argument("--lease-s", type=float, default=900.0, help="lease length in seconds (default 900)")
    cmds["report"].add_argument("--format", choices=("json", "markdown"), default="json")
    cmds["report"].add_argument("--out", type=Path)
    cmds["verify"].add_argument("--anchor-digest", help="a line digest kept outside the record (head_digest of an "
                                "earlier command): the chain alone cannot detect an edit of its last line")
    cmds["verify"].add_argument("--anchor-seq", type=int, help="the line the anchor digest belongs to (default: last)")
    return ap


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        out = COMMANDS[args.command](args)
    except dv.StaleWrite as exc:
        out = {"status": "rerun-required", "reason": str(exc)}
    except leases.LeaseRefused as exc:
        out = {"status": "refused", "reason": f"lease: {exc}"}
    except (dv.Rejected, CorruptRecord, OperationConflict, FileExistsError) as exc:
        out = {"status": "rejected", "error": f"{type(exc).__name__}: {exc}"}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        out = {"status": "rejected", "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False))
    return exit_code(out["status"])


if __name__ == "__main__":
    sys.exit(main())
