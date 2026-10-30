"""Control layer C, in memory: fact log, closed contract format, strictness order, effective contract, execution
state, artifact derivation, achieved tier, admission and per-deliverable publish (Control §1-§6 of the reconstruction
v12.2 spec copy; reconstruction v12 stage C1, DEC-02 approved 2026-10-30: library + CLI helper). Standard library
only.

Status: this module implements the spec copy's Control part and is kept structurally close to its executable
reference model (derivation version v12.2), which serves as the oracle: tests run the model's 92 scenarios and 44
mutations against this module and compare both derivations on the same fact sequences. **The control rules did not
pass the S0 spec review** (obligation N1 was violated in all seven recorded rounds; the two round-7 defects are fixed
in v12.2, which has not yet been re-reviewed). Agreeing with the model therefore shows only that this module computes
what the unreviewed rules say; it is not a review or a validation of the rules, and gives no autonomous
reconstruction capability.

Differences from the model, none of which changes a derivation:
- identities are SHA-256 digests of canonical JSON (Control §4) instead of the model's short repr hash;
- admission takes an optional capability check (Control §5.1 item 1, CAP-01), outside the model's scope;
- the in-memory log records which facts were appended together (batch_start), so that a persisted record can be
  replayed batch by batch with the same validation.
Persistence (append-only JSON lines with a digest chain and compare-and-set) is in task_record.py.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

DERIVATION_VERSION = "v12.2"


def canonical_bytes(value: Any) -> bytes:
    """Canonical form of a JSON value (Control §4): sorted keys, separators ',' ':', non-ASCII kept, UTF-8."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest_of(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


# ================================================================ fact log

WRITERS = {
    "session": {"C"},
    "contract": {"agent"},
    "freeze": {"agent"},
    "intent": {"C"},
    "admission_rejected": {"C"},
    "reuse": {"C"},
    "cancel_request": {"C"},
    "exposure": {"C", "B", "agent"},
    "start": {"B", "adapter"},
    "receipt": {"B", "adapter"},
    "reconcile": {"B", "adapter"},
    "check_result": {"B", "adapter"},
    "decision": {"human"},
    "publish": {"C"},
}
DECISIONS = {"approve_contract", "accept_identity", "assign_producer", "unblind", "abandon"}
END_VALUES = {"success", "failure", "timeout", "cancelled"}
RESULT_VALUES = {"pass", "fail", "inconclusive", "not-applicable"}
TIERS = ("T2", "T3E", "T3C")
TIER_RANK = {tier: rank for rank, tier in enumerate(TIERS)}
ROLES = {"exploration", "training", "control", "confirmation", "blinded"}
SPECIAL_STEPS = ("__check__",)
MODES = ("M1", "M2", "M3")
FREEZE_KEYS = {"step", "samples", "required"}


class NoContract(Exception):
    """No effective contract (none written yet, or the first contract under M2/M3 still awaits a human)."""


@dataclass(frozen=True)
class Fact:
    seq: int
    kind: str
    writer: str
    fields: dict

    def get(self, key, default=None):
        return self.fields.get(key, default)


class StaleWrite(Exception):
    """The expected head does not match: re-read, re-derive and retry (compare-and-set, Control §5.5)."""


class Admission(Exception):
    """Admission rejected the attempt (an admission_rejected fact was written), or publish found the deliverable not
    met."""


class Rejected(Exception):
    """A fact's kind, writer, format or field values do not conform; nothing of its batch is written."""


class Log:
    """The append-only fact log in memory, indexed by kind, attempt, output digest, check target, sample, identity and
    step (Control §4.8). Derivation results are cached per log head in _memo and cleared on every append."""

    def __init__(self):
        self.facts: list[Fact] = []
        self.batch_start: list[int] = []
        self._memo: dict = {}
        self._by_kind: dict = {}
        self._by_attempt: dict = {}
        self._by_output: dict = {}
        self._by_target: dict = {}
        self._by_sample: dict = {}
        self._by_identity: dict = {}
        self._by_step_out: dict = {}
        self._by_check_target: dict = {}
        self._by_step_intent: dict = {}
        self._intent: dict = {}

    @property
    def head(self) -> int:
        return len(self.facts)

    def _validate(self, kind, writer, fields, pending):
        if kind not in WRITERS:
            raise Rejected(f"unknown fact kind {kind}")
        for key in ("attempt", "sample", "target", "source", "step", "identity", "check", "criteria",
                    "check_attempt", "digest"):
            if key in fields and fields[key] is not None and not isinstance(fields[key], str):
                raise Rejected(f"{key} must be a string")
        if "outputs" in fields and not _strs(fields["outputs"] if fields["outputs"] is not None else ()):
            raise Rejected("outputs must be a tuple of digests")
        if kind == "exposure" and (not isinstance(fields.get("sample"), str) or set(fields) - {"sample", "attempt"}):
            raise Rejected("an exposure names one sample (and optionally the attempt or activity)")
        if writer not in WRITERS[kind]:
            raise Rejected(f"{writer} may not write {kind}")
        if kind in ("receipt", "reconcile") and fields.get("end") not in END_VALUES:
            raise Rejected(f"end value {fields.get('end')!r} not allowed")
        if kind == "check_result" and fields.get("result") not in RESULT_VALUES:
            raise Rejected(f"result value {fields.get('result')!r} not allowed")
        if kind == "decision" and fields.get("action") not in DECISIONS:
            raise Rejected(f"decision {fields.get('action')!r} not allowed")
        if kind == "intent" and attempt_id_taken(self, fields["attempt"], pending):
            raise Rejected("attempt id must be unique")
        if kind == "session":
            if self.head != 0 or pending or fields.get("mode") not in MODES or set(fields) != {"mode"}:
                raise Rejected("a session fact is the first fact and names a mode M1/M2/M3")
        if kind == "contract":
            validate_contract(self, fields.get("spec"))
        if kind in ("receipt", "reconcile") and fields.get("usage") is not None and not _nonneg(fields.get("usage")):
            raise Rejected("usage must be a finite number >= 0")
        why = fact_field_problem(kind, fields)
        if why:
            raise Rejected(why)
        if kind == "freeze":
            if set(fields) - {"plan", "independent"} != FREEZE_KEYS or not isinstance(fields.get("plan", ""), str):
                raise Rejected(f"freeze must have exactly the fields {sorted(FREEZE_KEYS)} (and optionally a plan "
                               f"digest: the frozen document with multiple-testing, cross-round and feasibility parts)")
            if not has_contract(self):
                raise Rejected("freeze before an effective contract")
            if not isinstance(fields["step"], str) or fields["step"] not in contract(self)["steps"]:
                raise Rejected("freeze names an unknown step")
            if not (isinstance(fields["samples"], tuple) and all(isinstance(x, str) for x in fields["samples"])):
                raise Rejected("freeze samples must be a tuple of sample names")
            if not _pairs(fields["required"]):
                raise Rejected("freeze required must be a frozenset of (check, criteria) pairs")
            for sample in fields["samples"]:
                if sample_role(self, sample) != "confirmation":
                    raise Rejected(f"freeze lists {sample}, which is not a confirmation sample")
            independent = fields.get("independent", ())
            if not (isinstance(independent, tuple) and all(isinstance(x, str) for x in independent)
                    and set(independent) <= set(fields["samples"])):
                raise Rejected("freeze independent must be a tuple of its own samples (the method-independent ones)")

    def append_batch(self, items, expect_head: int | None = None) -> list[Fact]:
        """Append several facts with one compare-and-set; if any one does not conform, none of the batch is written."""
        if expect_head is not None and expect_head != self.head:
            raise StaleWrite(f"expected head {expect_head}, actual {self.head}")
        try:
            for index, (kind, writer, fields) in enumerate(items):
                self._validate(kind, writer, fields, items[:index])
        finally:
            self._memo.clear()
        start = self.head
        written = [Fact(start + index, kind, writer, dict(sorted(fields.items())))
                   for index, (kind, writer, fields) in enumerate(items)]
        for fact in written:
            self.facts.append(fact)
            self.batch_start.append(start)
            self._index(fact)
        self._memo.clear()
        return written

    def _index(self, fact: Fact):
        self._by_kind.setdefault(fact.kind, []).append(fact)
        attempt = fact.get("attempt")
        if attempt is not None:
            self._by_attempt.setdefault(attempt, []).append(fact)
        if fact.kind == "intent":
            self._intent[attempt] = fact
            self._by_identity.setdefault(fact.get("identity"), []).append(fact)
            self._by_step_intent.setdefault(fact.get("step"), []).append(fact)
            if fact.get("step") == "__check__":
                self._by_check_target.setdefault(dict(fact.get("inputs") or ()).get("target"), []).append(fact)
        if fact.kind in ("receipt", "reconcile", "reuse"):
            outs = (fact.get("source"),) if fact.kind == "reuse" else (fact.get("outputs") or ())
            for digest in outs:
                self._by_output.setdefault(digest, []).append(fact)
            intent = self._intent.get(attempt)
            if intent is not None:
                self._by_step_out.setdefault(intent.get("step"), []).append(fact)
        if fact.kind == "check_result":
            self._by_target.setdefault(fact.get("target"), []).append(fact)
        if fact.kind in ("exposure", "check_result") and fact.get("sample") is not None:
            self._by_sample.setdefault(fact.get("sample"), []).append(fact)

    def mode(self) -> str:
        sessions = self._by_kind.get("session")
        return sessions[0].get("mode") if sessions else "M1"

    def append(self, kind: str, writer: str, expect_head: int | None = None, **fields) -> Fact:
        return self.append_batch([(kind, writer, fields)], expect_head)[0]

    def of(self, kind: str):
        return self._by_kind.get(kind, [])

    def of_attempt(self, attempt):
        return self._by_attempt.get(attempt, [])

    def results_for(self, target):
        return self._by_target.get(target, [])

    def of_sample(self, sample):
        return self._by_sample.get(sample, [])


def memo(fn):
    """Cache within one log head: facts are only appended, never changed, so a result holds while the head holds."""
    def wrapper(log, *args):
        key = (fn.__name__, args)
        if key not in log._memo:
            log._memo[key] = fn(log, *args)
        return log._memo[key]
    wrapper.__name__ = fn.__name__
    wrapper.__wrapped__ = fn
    return wrapper


def fact_field_problem(kind, fields) -> str | None:
    """The fields of B, adapter and human facts have fixed types and values (Control §2)."""
    def is_str(key):
        return isinstance(fields.get(key), str)
    if kind in ("receipt", "reconcile"):
        if fields.get("termination") not in ("confirmed", "unknown") or not is_str("attempt"):
            return "a receipt or reconcile names its attempt and a termination of confirmed or unknown"
    if kind in ("start", "cancel_request") and not is_str("attempt"):
        return f"{kind} names its attempt"
    if kind == "check_result" and not all(is_str(key) for key in ("target", "check", "criteria", "check_attempt")):
        return "a check result names its target, check, criteria and check attempt"
    if kind == "decision":
        need = {"approve_contract": (), "accept_identity": ("digest", "step", "old_identity", "new_identity"),
                "assign_producer": ("digest", "step"), "unblind": ("sample",), "abandon": ("attempt",)}
        action = fields.get("action")
        if action in need and not all(is_str(key) for key in need[action]):
            return f"decision {action} needs {list(need[action])}"
        ref = fields.get("ref")
        if action == "approve_contract" and (not isinstance(ref, int) or isinstance(ref, bool)):
            return "approve_contract names the sequence number of the contract it approves"
    return None


def attempt_id_taken(log, attempt, pending) -> bool:
    """An attempt id is unique across intents and admission rejections (Control §2)."""
    return bool(log._by_attempt.get(attempt)) or any(
        kind in ("intent", "admission_rejected") and fields.get("attempt") == attempt for kind, _, fields in pending)


# ================================================================ closed contract format (Control §1.1)

@dataclass(frozen=True)
class StepSpec:
    program: str
    env: str = "env0"
    upstream: tuple = ()
    external: tuple = ()
    checked: bool = False
    required: frozenset = frozenset()          # required (check digest, criterion digest)
    na_allowed: frozenset = frozenset()
    check_inputs: frozenset = frozenset()       # (check digest, step): further inputs a required check reads
    family: str | None = None
    round: int | None = None
    allow_rerun: bool = False
    pin: str | None = None


@dataclass(frozen=True)
class Deliverable:
    step: str
    target: str                                 # T2 / T3E / T3C
    required: bool = True
    confirmation_required: bool = True          # in effect when the target is T3C
    independent_confirmation: bool = False      # a pass on a method-independent confirmation sample is also required


@dataclass(frozen=True)
class Family:
    final_round: int                            # rounds are exactly 1..final_round
    convergence_check: str                      # check digest among the final step's required checks
    mode_check: str                             # check digest of the unconstrained-mode check


CONTRACT_KEYS = {"steps", "deliverables", "families", "samples", "budget"}


def _nonneg(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def _finite_budget(budget):
    return budget is None or _nonneg(budget)


def _strs(value):
    return isinstance(value, tuple) and all(isinstance(x, str) for x in value)


def _pairs(value):
    return isinstance(value, frozenset) and all(isinstance(p, tuple) and len(p) == 2 and _strs(p) for p in value)


def _opt(value, typ):
    return value is None or (isinstance(value, typ) and not isinstance(value, bool))


def _types_ok(step: StepSpec) -> bool:
    return (isinstance(step.program, str) and isinstance(step.env, str) and _strs(step.upstream)
            and _strs(step.external) and len(set(step.upstream)) == len(step.upstream)
            and all(isinstance(getattr(step, key), bool) for key in ("checked", "allow_rerun"))
            and _pairs(step.required) and _pairs(step.na_allowed) and _pairs(step.check_inputs)
            and _opt(step.family, str) and _opt(step.round, int) and _opt(step.pin, str))


def family_chain_problem(steps, fam, family) -> str | None:
    """In-family upstreams come only from the same or the previous round, every round after the first consumes the
    previous one, and only the final step is checked."""
    members = {name: step for name, step in steps.items() if step.family == fam}
    for name, step in members.items():
        if any(steps[up].family == fam and steps[up].round not in (step.round, step.round - 1)
               for up in step.upstream):
            return f"{name} may consume only steps of its own or the previous round"
    for name, step in members.items():
        if step.round > 1 and not _reaches_previous(steps, fam, name, set()):
            return f"{name} does not consume round {step.round - 1}, directly or through steps of its round"
    for name, step in members.items():
        if step.checked and step.round != family.final_round:
            return f"{name}: only the family's final step is checked"
    return None


def _reaches_previous(steps, fam, name, seen) -> bool:
    step = steps[name]
    for up in step.upstream:
        up_step = steps[up]
        if up_step.family != fam:
            continue
        if up_step.round == step.round - 1:
            return True
        if up_step.round == step.round and up not in seen and _reaches_previous(steps, fam, up, seen | {name}):
            return True
    return False


def validate_contract(log: Log, spec: dict):
    """Format validation: closed fields, types, ranges and cross-field consistency (Control §1.1)."""
    if not isinstance(spec, dict) or set(spec) != CONTRACT_KEYS:
        raise Rejected(f"contract must have exactly the fields {sorted(CONTRACT_KEYS)}")
    steps, dels, fams, samples = spec["steps"], spec["deliverables"], spec["families"], spec["samples"]
    if not all(isinstance(x, dict) and all(isinstance(k, str) for k in x) for x in (steps, dels, fams, samples)):
        raise Rejected("steps, deliverables, families and samples are maps keyed by name")
    if any(name.startswith("__") for name in steps):
        raise Rejected("step names starting with __ are reserved")
    if not all(isinstance(step, StepSpec) and _types_ok(step) for step in steps.values()):
        raise Rejected("every step must be a StepSpec with fields of the declared types")
    if not all(isinstance(dl, Deliverable) and isinstance(dl.step, str) and all(
            isinstance(getattr(dl, key), bool) for key in ("required", "confirmation_required",
                                                          "independent_confirmation"))
               for dl in dels.values()):
        raise Rejected("every deliverable must be a Deliverable with fields of the declared types")
    if not all(isinstance(fm, Family) and isinstance(fm.final_round, int) and not isinstance(fm.final_round, bool)
               and isinstance(fm.convergence_check, str) and isinstance(fm.mode_check, str)
               and fm.convergence_check != fm.mode_check for fm in fams.values()):
        raise Rejected("every family must be a Family with fields of the declared types")
    if not _finite_budget(spec["budget"]):
        raise Rejected("budget must be null or a finite number >= 0")
    if any(role not in ROLES for role in samples.values()):
        raise Rejected("unknown sample role")
    for name, step in steps.items():
        for up in step.upstream:
            if up not in steps:
                raise Rejected(f"{name}: unknown upstream {up}")
        if step.checked and not step.required:
            raise Rejected(f"{name}: a checked step needs at least one required check")
        if not step.na_allowed <= step.required:
            raise Rejected(f"{name}: not-applicable may only be allowed for required checks")
        for chk, other in step.check_inputs:
            if chk not in {c for c, _ in step.required} or other not in steps or other == name:
                raise Rejected(f"{name}: a check input names a required check of this step and another step")
        if (step.family is None) != (step.round is None):
            raise Rejected(f"{name}: family and round go together")
        if step.family is not None and (step.family not in fams or not isinstance(step.round, int) or step.round < 1):
            raise Rejected(f"{name}: unknown family or bad round")
    for fam, family in fams.items():
        members = {name: step for name, step in steps.items() if step.family == fam}
        rounds = sorted({step.round for step in members.values()})
        if family.final_round < 1 or rounds != list(range(1, family.final_round + 1)):
            raise Rejected(f"family {fam}: rounds must be exactly 1..final_round, each with at least one step")
        finals = [name for name, step in members.items() if step.round == family.final_round and step.checked]
        if len(finals) != 1:
            raise Rejected(f"family {fam}: the final round must have exactly one checked step")
        why = family_chain_problem(steps, fam, family)
        if why:
            raise Rejected(f"family {fam}: {why}")
        last = steps[finals[0]]
        names = {c for c, _ in last.required}
        if not last.checked or not {family.convergence_check, family.mode_check} <= names:
            raise Rejected(f"family {fam}: the final round must be checked and require the convergence "
                           f"and unconstrained-mode checks")
        if any(c in (family.convergence_check, family.mode_check) for c, _ in last.na_allowed):
            raise Rejected(f"family {fam}: the convergence and mode checks cannot be not-applicable")
    for did, dl in dels.items():
        if dl.step not in steps or dl.target not in TIERS:
            raise Rejected(f"deliverable {did}: unknown step or tier")
        if not steps[dl.step].checked:
            raise Rejected(f"deliverable {did}: its step must be checked")
        step = steps[dl.step]
        if step.family is not None and step.round != fams[step.family].final_round:
            raise Rejected(f"deliverable {did}: an iteration deliverable must be the final round")
    seen, stack = set(), set()

    def visit(name):
        if name in stack:
            raise Rejected(f"cycle at {name}")
        if name in seen:
            return
        stack.add(name)
        for up in steps[name].upstream + tuple(sorted(x for _, x in steps[name].check_inputs)):
            visit(up)
        stack.discard(name)
        seen.add(name)

    for name in steps:
        visit(name)
    for name, step in steps.items():
        if step.pin is not None and step.pin not in candidates_raw(log, name):
            raise Rejected(f"{name}: pin {step.pin} is not an output of this step")


def step_at_least_as_strict(current_step: StepSpec, proposed: StepSpec) -> bool:
    """Whether `proposed` is at least as strict as `current_step` (Control §1.2). Program, environment and external
    dependencies are content fields: they may change, but a change invalidates the artifacts. Upstreams may only be
    added: removing one would move its check results out of the deliverable's dependency chain."""
    return (set(proposed.upstream) >= set(current_step.upstream)
            and (proposed.checked or not current_step.checked)
            and proposed.required >= current_step.required
            and proposed.na_allowed <= current_step.na_allowed
            and proposed.check_inputs == current_step.check_inputs
            and (proposed.family, proposed.round) == (current_step.family, current_step.round)
            and (not proposed.allow_rerun or current_step.allow_rerun)
            and proposed.pin == current_step.pin)


def contract_at_least_as_strict(effective: dict, proposed: dict) -> bool:
    """Strictness order (Control §1.2): holds only if every field is at least as strict."""
    for name, step in effective["steps"].items():
        proposed_step = proposed["steps"].get(name)
        if proposed_step is None or not step_at_least_as_strict(step, proposed_step):
            return False
    for name, proposed_step in proposed["steps"].items():   # an added step takes no value reserved for the first
        if name in effective["steps"]:                       # contract or a human, joins no existing family
            continue
        if (proposed_step.allow_rerun or proposed_step.na_allowed or proposed_step.family in effective["families"]
                or proposed_step.pin is not None):
            return False
    for did, current_dl in effective["deliverables"].items():
        proposed_dl = proposed["deliverables"].get(did)
        if proposed_dl is None or proposed_dl.step != current_dl.step \
                or TIER_RANK[proposed_dl.target] < TIER_RANK[current_dl.target] \
                or (current_dl.required and not proposed_dl.required) \
                or (current_dl.confirmation_required and not proposed_dl.confirmation_required) \
                or (current_dl.independent_confirmation and not proposed_dl.independent_confirmation):
            return False
    for did, proposed_dl in proposed["deliverables"].items():   # a deliverable that becomes T3C later takes the
        current_dl = effective["deliverables"].get(did)          # reserved values; "no" only from a human
        if proposed_dl.target == "T3C" and (current_dl is None or current_dl.target != "T3C") \
                and not (proposed_dl.confirmation_required and proposed_dl.independent_confirmation):
            return False
    for fam, family in effective["families"].items():
        if proposed["families"].get(fam) != family:
            return False
    for sample, role in effective["samples"].items():
        if proposed["samples"].get(sample) != role:
            return False
    current_budget, proposed_budget = effective["budget"], proposed["budget"]
    if current_budget is not None and (proposed_budget is None or proposed_budget > current_budget):
        return False
    return True


def _identity(step, spec: StepSpec, inputs: dict) -> str:
    """Computational identity (Control §4.2): owning step, program, environment, external dependencies and the
    actually consumed inputs, as the SHA-256 of their canonical form."""
    return digest_of({"kind": "computation", "step": step, "program": spec.program, "environment": spec.env,
                      "external": list(spec.external), "inputs": dict(sorted(inputs.items()))})


@memo
def _contracts(log: Log):
    """Walk the contracts and approve_contract decisions in fact order (Control §1.3). Returns (effective contract
    spec or None, status of each contract by sequence number)."""
    eff, eff_seq = None, None
    status, against = {}, {}
    events = sorted(log.of("contract") + [d for d in log.of("decision") if d.get("action") == "approve_contract"],
                    key=lambda fact: fact.seq)
    by_seq = {fact.seq: fact for fact in log.of("contract")}

    def activate(seq):
        nonlocal eff, eff_seq
        for key, value in status.items():
            if value == "effective":
                status[key] = "superseded"
            elif value == "pending_approval":
                status[key] = "lapsed"
        eff, eff_seq = by_seq[seq].get("spec"), seq
        status[seq] = "effective"

    for event in events:
        if event.kind == "contract":
            proposed = event.get("spec")
            if (eff is None and log.mode() == "M1" and not status) or \
                    (eff is not None and contract_at_least_as_strict(eff, proposed)):
                activate(event.seq)
            else:
                status[event.seq], against[event.seq] = "pending_approval", eff_seq
        else:
            ref = event.get("ref")
            if status.get(ref) == "pending_approval" and against.get(ref) == eff_seq:
                activate(ref)
    return eff, status


def has_contract(log) -> bool:
    return _contracts(log)[0] is not None


def contract(log: Log) -> dict:
    eff = _contracts(log)[0]
    if eff is None:
        raise NoContract("no effective contract")
    return eff


def contract_status(log, contract_fact) -> str:
    """effective, superseded, pending_approval or lapsed (for the completion report)."""
    return _contracts(log)[1][contract_fact.seq]


def spec_of(log, step) -> StepSpec:
    return contract(log)["steps"][step]


def sample_role(log, sample) -> str | None:
    if not has_contract(log):
        return None
    return contract(log)["samples"].get(sample)


# ================================================================ execution state (Control §3)

TERMINAL = {"success": "computed", "failure": "failed", "timeout": "failed", "cancelled": "cancelled"}


@memo
def _exec(log: Log, attempt: str):
    """(state, terminal fact). Only one terminal fact per attempt is in effect."""
    state, term, reconciled = "planned", None, False
    for fact in log.of_attempt(attempt):
        kind = fact.kind
        if kind == "admission_rejected" and state == "planned":
            state = "rejected"
        elif kind == "intent" and state == "planned":
            state = "admitted"
        elif kind == "reuse" and state == "admitted":
            state, term = "reused", fact
        elif kind == "start" and state == "admitted":
            state = "running"
        elif kind == "cancel_request":
            state = {"admitted": "cancelled", "running": "cancelling"}.get(state, state)
        elif kind == "receipt" and state in ("admitted", "running", "cancelling"):
            if fact.get("termination") == "confirmed":
                state, term = TERMINAL[fact.get("end")], fact
            else:
                state = "unknown"
        elif kind == "reconcile" and fact.get("termination") == "confirmed":
            if state == "unknown":
                state, term = TERMINAL[fact.get("end")], fact
            elif state == "abandoned":
                reconciled = True
        elif kind == "decision" and fact.get("action") == "abandon" and state == "unknown":
            state = "abandoned"
    if state == "abandoned" and reconciled:
        return "abandoned_reconciled", None
    return state, term


def exec_status(log, attempt) -> str:
    return _exec(log, attempt)[0]


def terminal_fact(log, attempt):
    return _exec(log, attempt)[1]


def intent_of(log, attempt):
    return log._intent.get(attempt)


def reported_usage(log, attempt):
    usages = [fact.get("usage") for fact in log.of_attempt(attempt) if fact.kind in ("receipt", "reconcile")
              and fact.get("usage") is not None]
    return max(usages) if usages else None


def charge(log, intent) -> float:
    """Budget accounting (Control §5.1 item 2): the larger of the declared cost and the usage reported by B."""
    usage = reported_usage(log, intent.get("attempt"))
    return max(intent.get("cost", 0.0), usage if usage is not None else 0.0)


@memo
def in_flight(log: Log) -> float:
    return sum(charge(log, fact) for fact in log.of("intent")
               if exec_status(log, fact.get("attempt")) in
               ("admitted", "running", "cancelling", "unknown", "abandoned"))


@memo
def used(log: Log) -> float:
    return sum(charge(log, fact) for fact in log.of("intent")
               if exec_status(log, fact.get("attempt")) in
               ("computed", "failed", "cancelled", "abandoned_reconciled", "reused"))


# ================================================================ artifacts and producers (Control §4.1)

def output_facts(log: Log, digest: str):
    return [fact for fact in log._by_output.get(digest, []) if terminal_fact(log, fact.get("attempt")) is fact]


@memo
def candidates_raw(log: Log, step: str):
    """Every output digest an attempt of this step name produced in its terminal fact, in order of first sight."""
    seen = {}
    for fact in log._by_step_out.get(step, []):
        if terminal_fact(log, fact.get("attempt")) is not fact:
            continue
        outs = (fact.get("source"),) if fact.kind == "reuse" else (fact.get("outputs") or ())
        for digest in outs:
            seen.setdefault(digest, fact.seq)
    return sorted(seen, key=seen.get)


def attested(log, attempt) -> bool:
    """The reads or usage observed by B do not exceed what was declared; under M2/M3 the receipt must carry usage
    (Delivery §2.3)."""
    if any(fact.get("observed_exceeds_declared") for fact in log.of_attempt(attempt)
           if fact.kind in ("receipt", "reconcile")):
        return False
    intent = intent_of(log, attempt)
    usage = reported_usage(log, attempt)
    if usage is None and log.mode() != "M1" and terminal_fact(log, attempt) is not None \
            and terminal_fact(log, attempt).kind != "reuse":
        return False
    return not (intent is not None and usage is not None and usage > intent.get("cost", 0.0))


@memo
def producers(log: Log, digest: str):
    found = []
    for fact in output_facts(log, digest):
        intent = intent_of(log, fact.get("attempt"))
        if intent is None or intent.get("step") in SPECIAL_STEPS:
            continue
        if exec_status(log, intent.get("attempt")) in ("computed", "reused") and attested(log, intent.get("attempt")):
            found.append((fact.seq, intent))
    return found


@memo
def claiming_steps(log: Log, digest: str) -> tuple:
    steps = contract(log)["steps"]
    return tuple(sorted({intent.get("step") for _, intent in producers(log, digest) if intent.get("step") in steps}))


@memo
def owner_step(log: Log, digest: str):
    claims = claiming_steps(log, digest)
    if len(claims) == 1:
        return claims[0]
    for decision in reversed(log.of("decision")):
        if decision.get("action") == "assign_producer" and decision.get("digest") == digest \
                and decision.get("step") in claims:
            return decision.get("step")
    return None


def producer_conflict(log, digest) -> bool:
    return len(claiming_steps(log, digest)) > 1 and owner_step(log, digest) is None


def inputs_of(intent) -> dict:
    return dict(intent.get("inputs") or ())


def expected_identity(log: Log, step: str, inputs: dict) -> str:
    return _identity(step, spec_of(log, step), inputs)


def identity_accepted(log, digest, step, old_id, new_id) -> bool:
    """A human-approved identity continuation: valid only for this artifact and this pair of identities."""
    return any(decision.get("action") == "accept_identity" and decision.get("digest") == digest
               and decision.get("step") == step and decision.get("old_identity") == old_id
               and decision.get("new_identity") == new_id
               for decision in log.of("decision"))


@memo
def best_producer(log: Log, digest: str):
    """The representative producer of the owning step (Control §4.2): among producers whose identity is current (or
    continued by approval), the earliest; when none is, the latest. Returns (seq, intent) or None."""
    step = owner_step(log, digest)
    if step is None:
        return None
    best = None
    for seq, intent in producers(log, digest):
        if intent.get("step") != step:
            continue
        exp = expected_identity(log, step, inputs_of(intent))
        cur = intent.get("identity") == exp
        ok_id = cur or identity_accepted(log, digest, step, intent.get("identity"), exp)
        rank = (ok_id, -seq if ok_id else seq)
        if best is None or rank > best[0]:
            best = (rank, seq, intent)
    return None if best is None else best[1:]


def usable(log, digest) -> bool:
    return best_producer(log, digest) is not None


def step_of(log, digest):
    rep = best_producer(log, digest)
    return None if rep is None else rep[1].get("step")


def bind_seq(log, digest) -> int:
    rep = best_producer(log, digest)
    return -1 if rep is None else rep[0]


@memo
def self_current(log: Log, digest: str) -> bool:
    rep = best_producer(log, digest)
    if rep is None:
        return False
    _, intent = rep
    step = intent.get("step")
    exp = expected_identity(log, step, inputs_of(intent))
    return intent.get("identity") == exp or identity_accepted(log, digest, step, intent.get("identity"), exp)


@memo
def first_seen(log: Log, step: str, digest: str):
    """Sequence number of the first terminal fact of an attempt of the step that output this digest."""
    for fact in log._by_step_out.get(step, []):
        if terminal_fact(log, fact.get("attempt")) is fact and \
                digest in ((fact.get("source"),) if fact.kind == "reuse" else (fact.get("outputs") or ())):
            return fact.seq
    return None


IN_FLIGHT = ("admitted", "running", "cancelling")


@memo
def step_intents(log: Log, step: str) -> tuple:
    """The intents of one step, from the log's index (Control §4.8: no whole-log scan per derivation call)."""
    return tuple(log._by_step_intent.get(step, ()))


@memo
def overtaken(log: Log, digest: str) -> bool:
    """A newer attempt of the step name -- one with a fact after this artifact was first seen, under any contract --
    produced no usable and current output: it failed, was cancelled, is unknown, was abandoned (reconciled or not), or
    its output is unattested, invalidated or otherwise not current, with or without outputs (Control §4.2, v12.2).
    Binding this artifact again would be a choice among draws already made, so it binds only through a pin (human
    approval). Attempts still in flight, reuse attempts and attempts that reproduced this digest do not overtake."""
    step = step_of(log, digest)
    first = first_seen(log, step, digest)
    if first is None:
        return False
    for intent in step_intents(log, step):
        attempt = intent.get("attempt")
        if max(fact.seq for fact in log.of_attempt(attempt)) <= first:
            continue
        state = exec_status(log, attempt)
        if state in IN_FLIGHT or state == "reused":
            continue
        term = terminal_fact(log, attempt)
        outs = tuple(term.get("outputs") or ()) if term is not None and term.kind != "reuse" else ()
        if digest in outs:
            continue
        if state == "computed" and any(usable(log, other) and current(log, other) for other in outs):
            continue
        return True
    return False


@memo
def bound(log: Log, step: str):
    spec = spec_of(log, step)
    if spec.pin is not None:
        return spec.pin if ok(log, spec.pin) else None
    best = None
    for digest in candidates_raw(log, step):
        if step_of(log, digest) == step and ok(log, digest) and not overtaken(log, digest):
            if best is None or bind_seq(log, digest) > bind_seq(log, best):
                best = digest
    return best


def intermediate_round(log, step) -> bool:
    """A family member other than the final round's checked step."""
    spec = spec_of(log, step)
    return spec.family is not None and not (
        spec.round == contract(log)["families"][spec.family].final_round and spec.checked)


@memo
def upstream_state(log: Log, digest: str) -> str:
    """ok / stale / waiting (Control §4.2)."""
    _, intent = best_producer(log, digest)
    mine = spec_of(log, intent.get("step"))
    consumed = inputs_of(intent)
    if set(mine.upstream) != set(consumed):
        return "stale"
    state = "ok"
    for up in mine.upstream:
        used_digest = consumed[up]
        if used_digest is None or not usable(log, used_digest) or not current(log, used_digest):
            return "stale"
        if step_of(log, used_digest) != up:
            return "stale"
        up_spec = spec_of(log, up)
        if intermediate_round(log, up) and up_spec.family != mine.family:
            return "stale"
        up_bound = bound(log, up)
        if up_bound == used_digest:
            continue
        if up_spec.pin is not None:
            if up_spec.pin != used_digest:
                return "stale"
            state = "waiting"
            continue
        if up_bound is not None and bind_seq(log, up_bound) > bind_seq(log, used_digest):
            return "stale"
        state = "waiting"
    return state


def current(log, digest) -> bool:
    return self_current(log, digest) and upstream_state(log, digest) != "stale"


# ================================================================ checks, freeze and achieved tier (Control §4.3-4.5)

def check_identity(chk, crit, target, extra=None):
    """The identity of a check attempt: check x criterion x target x the check inputs resolved by C."""
    return digest_of({"kind": "check", "check": chk, "criterion": crit, "target": target,
                      "inputs": dict(sorted((extra or {}).items()))})


def declared_check_inputs(log, target, chk) -> tuple:
    step = step_of(log, target)
    return tuple(sorted(other for c, other in spec_of(log, step).check_inputs if c == chk)) if step is not None else ()


def check_inputs_for(log, target, chk):
    """At admission C resolves each declared input: an upstream of the target's step to the version the target
    consumed, any other step to its bound version. None if one cannot be resolved."""
    consumed = inputs_of(best_producer(log, target)[1])
    resolved = {}
    for other in declared_check_inputs(log, target, chk):
        digest = consumed[other] if other in consumed else bound(log, other)
        if digest is None:
            return None
        resolved["input:" + other] = digest
    return resolved


def check_attempt_of(intent, target, chk, crit) -> bool:
    consumed = inputs_of(intent)
    extra = {key: value for key, value in consumed.items() if key != "target"}
    return consumed.get("target") == target and intent.get("identity") == check_identity(chk, crit, target, extra)


def check_inputs_hold(log, intent, target, chk) -> bool:
    """The attempt read exactly the declared inputs of the effective contract; an upstream input is the consumed
    version, any other input is still the bound version of its step."""
    extra = {key: value for key, value in inputs_of(intent).items() if key != "target"}
    if set(extra) != {"input:" + other for other in declared_check_inputs(log, target, chk)}:
        return False
    consumed = inputs_of(best_producer(log, target)[1])
    return all(extra[key] == (consumed[key[6:]] if key[6:] in consumed else bound(log, key[6:])) for key in extra)


def valid_check_attempt(log, result, target, chk, crit) -> bool:
    attempt = result.get("check_attempt")
    intent = intent_of(log, attempt)
    return (intent is not None and exec_status(log, attempt) == "computed" and attested(log, attempt)
            and check_attempt_of(intent, target, chk, crit) and check_inputs_hold(log, intent, target, chk))


def result_sample(log, result):
    sample = result.get("sample")
    intent = intent_of(log, result.get("check_attempt"))
    return sample if sample is not None and intent is not None and sample in (intent.get("reads") or ()) else None


def pending_check_attempts(log, target, chk, crit) -> bool:
    for intent in log._by_check_target.get(target, []):
        if check_attempt_of(intent, target, chk, crit) and exec_status(log, intent.get("attempt")) in (
                "admitted", "running", "cancelling", "unknown", "abandoned"):
            return True
    return False


@memo
def same_identity_outputs(log: Log, step: str, identity: str) -> tuple:
    """Outputs of all attempts of the same step with the same computational identity (copies from reruns)."""
    found = []
    for intent in log._by_identity.get(identity, []):
        if intent.get("step") != step:
            continue
        term = terminal_fact(log, intent.get("attempt"))
        if term is None:
            continue
        for digest in ((term.get("source"),) if term.kind == "reuse" else (term.get("outputs") or ())):
            if digest not in found:
                found.append(digest)
    return tuple(found)


def identity_failures(log, step, identity, pairs):
    """A fail or inconclusive of a required check on any copy with the same computational identity."""
    return [result for digest in same_identity_outputs(log, step, identity) for result in log.results_for(digest)
            if (result.get("check"), result.get("criteria")) in pairs
            and result.get("result") in ("fail", "inconclusive")]


@memo
def checks_state(log: Log, digest: str) -> str:
    """ok / missing / held. A fail or inconclusive counts whatever its check attempt's state, and binds to the
    computational identity."""
    _, intent = best_producer(log, digest)
    spec = spec_of(log, intent.get("step"))
    if not spec.checked:
        return "ok"
    if identity_failures(log, intent.get("step"), intent.get("identity"), spec.required):
        return "held"
    missing = False
    for chk, crit in spec.required:
        results = [r for r in log.results_for(digest) if (r.get("check"), r.get("criteria")) == (chk, crit)]
        if any(r.get("result") in ("fail", "inconclusive") for r in results):
            return "held"
        if any(r.get("result") == "not-applicable" and (chk, crit) not in spec.na_allowed for r in results):
            return "held"
        good = [r for r in results if valid_check_attempt(log, r, digest, chk, crit) and (
            r.get("result") == "pass" or
            (r.get("result") == "not-applicable" and (chk, crit) in spec.na_allowed))]
        if not good or pending_check_attempts(log, digest, chk, crit):
            missing = True
    return "missing" if missing else "ok"


@memo
def freeze_ok(log: Log, digest: str, conf_req: bool = True, indep_req: bool = False) -> bool:
    """Freeze and confirmation conditions for T3C (Control §4.4); the two flags are the deliverable's."""
    _, intent = best_producer(log, digest)
    step = intent.get("step")
    spec = spec_of(log, step)
    freezes = [f for f in log.of("freeze") if f.get("step") == step and f.get("required") == spec.required]
    if not freezes:
        return False
    first = min(f.seq for f in freezes)
    results = [r for r in log.results_for(digest) if (r.get("check"), r.get("criteria")) in spec.required]
    if any(r.seq < first for r in results):
        return False
    mine = {r.get("check_attempt") for r in results}
    conf_ok = indep_ok = False
    for result in results:
        sample = result_sample(log, result)
        if sample is None or sample_role(log, sample) != "confirmation":
            continue
        holding = [f.seq for f in freezes if sample in f.get("samples")]
        if not holding:
            return False
        for seen in log.of_sample(sample):
            if seen.kind != "exposure" or seen.seq >= result.seq:
                continue
            if seen.seq < min(holding) or seen.writer != "C" or seen.get("attempt") not in mine:
                return False
        for other in log.of_sample(sample):
            if other.kind == "check_result" and other.seq < result.seq and other.get("target") != digest \
                    and result_sample(log, other) == sample:
                return False
        if result.get("result") == "pass" and valid_check_attempt(log, result, digest, result.get("check"),
                                                                  result.get("criteria")):
            conf_ok = True
            if independent_sample(log, step, spec.required, sample):
                indep_ok = True
    if indep_req and not independent_ok(log, digest, indep_ok):
        return False
    return conf_ok or not conf_req


def independent_sample(log, step, required, sample) -> bool:
    """Only a freeze that precedes the sample's first exposure can label it method-independent."""
    first = min((e.seq for e in log.of_sample(sample) if e.kind == "exposure"), default=None)
    return any(sample in (f.get("independent") or ()) and sample in f.get("samples") and (first is None or f.seq < first)
               for f in log.of("freeze") if f.get("step") == step and f.get("required") == required)


def independent_ok(log, digest, found) -> bool:
    """A valid pass on a sample a freeze lists as method-independent."""
    return found


@memo
def ok(log: Log, digest: str) -> bool:
    if not usable(log, digest):
        return False
    return current(log, digest) and upstream_state(log, digest) == "ok" and checks_state(log, digest) == "ok"


def achieved_tier(log, digest, conf_req: bool = True, indep_req: bool = False) -> str | None:
    """T2 needs ok; T3E has the same mechanical conditions; T3C additionally needs freeze and confirmation."""
    if not ok(log, digest) or not spec_of(log, step_of(log, digest)).checked:
        return None
    return "T3C" if freeze_ok(log, digest, conf_req, indep_req) else "T3E"


def chain_steps(log, step) -> list:
    """The deliverable step and all of its upstreams in the effective contract."""
    steps, found, todo = contract(log)["steps"], [], [step]
    while todo:
        name = todo.pop()
        if name not in found:
            found.append(name)
            todo.extend(steps[name].upstream)
    return found


def prior_failures(log, step) -> list:
    """Every fail or inconclusive any artifact on this dependency chain has had, whatever its identity now."""
    found = []
    for name in chain_steps(log, step):
        for digest in candidates_raw(log, name):
            for result in log.results_for(digest):
                if result.get("result") in ("fail", "inconclusive"):
                    found.append((name, digest, result.get("check"), result.get("criteria"), result.get("result")))
    return found


def failed_draws(log, step) -> list:
    """Computation attempts of the chain that ended without a usable artifact: failed, cancelled, unknown,
    abandoned, or computed but unattested."""
    found = []
    for name in chain_steps(log, step):
        for intent in log.of("intent"):
            if intent.get("step") != name:
                continue
            attempt = intent.get("attempt")
            state = exec_status(log, attempt)
            if state in ("failed", "cancelled", "unknown", "abandoned", "abandoned_reconciled") or \
                    (state == "computed" and not attested(log, attempt)):
                found.append((name, attempt, state))
    return found


def confirmation_results(log, step) -> list:
    """Every result on a confirmation sample of any artifact of the chain, and every check attempt on the chain that
    read a confirmation sample and ended without a result ("no result", v12.2)."""
    done = [(name, digest, r.get("check"), result_sample(log, r), r.get("result")) for name in chain_steps(log, step)
            for digest in candidates_raw(log, name) for r in log.results_for(digest)
            if result_sample(log, r) is not None and sample_role(log, result_sample(log, r)) == "confirmation"]
    aborted = [(name, digest, None, sample, "no result") for name, digest, _, _, reads in failed_check_draws(log, step)
               for sample in reads if sample_role(log, sample) == "confirmation"]
    return done + aborted


def failed_check_draws(log, step) -> list:
    """Check attempts on artifacts of the chain that ended without a check result (failed, cancelled, unknown,
    abandoned, or computed without a result), so retrying a check until it passes stays visible (v12.2)."""
    targets = {digest: name for name in chain_steps(log, step) for digest in candidates_raw(log, name)}
    return aborted_checks(log, targets)


def aborted_checks(log, targets: dict) -> list:
    found = []
    for intent in log.of("intent"):
        if intent.get("step") != "__check__":
            continue
        target = inputs_of(intent).get("target")
        attempt = intent.get("attempt")
        if target not in targets or exec_status(log, attempt) in IN_FLIGHT:
            continue
        if not any(r.get("check_attempt") == attempt for r in log.results_for(target)):
            found.append((targets[target], target, attempt, exec_status(log, attempt),
                          tuple(intent.get("reads") or ())))
    return found


def task_history(log) -> dict:
    """Fail/inconclusive results, failed draws and artifact counts on every step of the effective contract."""
    steps = contract(log)["steps"]
    fails = [(name, digest, r.get("check"), r.get("result")) for name in steps for digest in candidates_raw(log, name)
             for r in log.results_for(digest) if r.get("result") in ("fail", "inconclusive")]
    draws = [x for name in steps for x in failed_draws_of_step(log, name)]
    arts = {name: len(step_artifacts(log, name)) for name in steps}
    checks = aborted_checks(log, {digest: name for name in steps for digest in candidates_raw(log, name)})
    return {"failures": fails, "failed_draws": draws, "artifacts": arts, "failed_check_draws": checks}


def failed_draws_of_step(log, name) -> list:
    found = []
    for intent in log.of("intent"):
        if intent.get("step") != name:
            continue
        attempt = intent.get("attempt")
        state = exec_status(log, attempt)
        if state in ("failed", "cancelled", "unknown", "abandoned", "abandoned_reconciled") or \
                (state == "computed" and not attested(log, attempt)):
            found.append((name, attempt, state))
    return found


def deliverable_status(log, did) -> dict:
    dl = contract(log)["deliverables"][did]
    artifact = bound(log, dl.step)
    got = achieved_tier(log, artifact, dl.confirmation_required, dl.independent_confirmation) \
        if artifact is not None else None
    if got == "T3E" and dl.target == "T2":
        got = "T2"
    met = got is not None and TIER_RANK[got] >= TIER_RANK[dl.target]
    return {"artifact": artifact, "target": dl.target, "achieved": got, "met": met, "required": dl.required}


def report_status(log, did) -> dict:
    """One row of the completion report: deliverable_status plus the histories of the dependency chain."""
    step = contract(log)["deliverables"][did].step
    return {**deliverable_status(log, did), "prior_failures": prior_failures(log, step),
            "failed_draws": failed_draws(log, step), "failed_check_draws": failed_check_draws(log, step),
            "confirmation_results": confirmation_results(log, step),
            "task_history": task_history(log)}


def accepted(log, digest) -> bool:
    """The artifact is bound for at least one deliverable and every deliverable bound to it meets its target."""
    mine = [did for did, dl in contract(log)["deliverables"].items() if bound(log, dl.step) == digest]
    return bool(mine) and all(deliverable_status(log, did)["met"] for did in mine)


def historical_failures(log, digest):
    step = step_of(log, digest)
    req = spec_of(log, step).required if step is not None else frozenset()
    return [(r.get("check"), r.get("criteria"), r.get("result")) for r in log.results_for(digest)
            if r.get("result") in ("fail", "inconclusive") and (r.get("check"), r.get("criteria")) not in req]


def label(log, digest) -> str:
    """Diagnostic label (Control §4.6), the first that holds."""
    if producer_conflict(log, digest):
        return "producer_conflict"
    if not producers(log, digest) or not usable(log, digest):
        return "not_usable"
    step = step_of(log, digest)
    spec = spec_of(log, step)
    if not current(log, digest):
        return "invalidated"
    if intermediate_round(log, step):
        later = [name for name, other in contract(log)["steps"].items()
                 if other.family == spec.family and other.round > spec.round
                 and any(usable(log, d) for d in candidates_raw(log, name))]
        return "superseded_by_iteration" if later else "iteration_internal"
    if upstream_state(log, digest) == "waiting":
        return "blocked_upstream"
    state = checks_state(log, digest)
    if state == "held":
        return "held"
    if state == "missing":
        return "unchecked"
    if bound(log, step) != digest:
        return "overtaken" if overtaken(log, digest) and spec_of(log, step).pin != digest else "superseded"
    return "ok"


# ================================================================ admission, check attempt, reuse, publish (Control §5)

def provisional_input(log, step):
    best_bound = bound(log, step)
    if best_bound is not None:
        return best_bound
    best = None
    for digest in candidates_raw(log, step):
        if step_of(log, digest) == step and current(log, digest):
            if best is None or bind_seq(log, digest) > bind_seq(log, best):
                best = digest
    return best


def same_identity_ran(log, step, identity) -> bool:
    """The same step with the same identity has an attempt in flight, or one that succeeded and is attested
    (whether or not it has been checked)."""
    for fact in log._by_identity.get(identity, []):
        if fact.get("step") != step:
            continue
        state = exec_status(log, fact.get("attempt"))
        if state in ("admitted", "running", "cancelling", "unknown", "abandoned") or \
                (state in ("computed", "reused") and attested(log, fact.get("attempt"))):
            return True
    return False


def counted_result(log, digest, chk, crit) -> bool:
    """A result of any value from a valid check attempt of this check x criterion x target."""
    return any((r.get("check"), r.get("criteria")) == (chk, crit) and valid_check_attempt(log, r, digest, chk, crit)
               for r in log.results_for(digest))


def step_artifacts(log, step) -> list:
    """Every artifact a computed, attested attempt of this step produced (any identity, current or not)."""
    return [d for d in candidates_raw(log, step) if any(intent.get("step") == step for _, intent in producers(log, d))]


def unchecked_artifacts(log, step) -> list:
    """Artifacts of a checked step that lack a counted result for some required check."""
    spec = spec_of(log, step)
    if not spec.checked:
        return []
    return [d for d in step_artifacts(log, step) if not all(counted_result(log, d, c, k) for c, k in spec.required)]


def same_side_effect(fact, step, check) -> bool:
    """Check attempts have the same side effect when they check the same check x criterion x target, whatever check
    inputs were resolved (Control §3)."""
    return fact.get("step") == step and check_attempt_of(fact, check[2], check[0], check[1])


def admit(log: Log, expect_head: int, attempt: str, step: str, cost: float = 1.0, reads: tuple = (),
          check: tuple | None = None, reuse_source: str | None = None, capability=None) -> Fact:
    """Admission (Control §5.1-5.3). C computes the identity, the consumed inputs and the accounts; the caller names
    only the step, the reads, the cost and, for a check attempt, (check, criterion, target). `capability`, when
    given, is called with the execution mode and returns a refusal reason or None (CAP-01; outside the model)."""
    if expect_head != log.head:
        raise StaleWrite("re-read and re-derive before admission")

    def reject(reason):
        log.append("admission_rejected", "C", attempt=attempt, step=step, reason=reason)
        raise Admission(reason)

    if not has_contract(log):
        reject("no effective contract")
    if capability is not None:
        refusal = capability(log.mode())
        if refusal:
            reject(f"capability: {refusal}")
    eff = contract(log)
    if not _nonneg(cost):
        reject("cost must be a finite number >= 0")
    if eff["budget"] is not None and used(log) + in_flight(log) + cost > eff["budget"]:
        reject("budget: used + in-flight + request exceeds limit")
    for sample in reads:
        role = sample_role(log, sample)
        if role == "confirmation":
            if step != "__check__":
                reject(f"confirmation sample {sample} may be read only by a check attempt")
            if not any(sample in f.get("samples") for f in log.of("freeze")):
                reject(f"confirmation sample {sample} read before freeze")
        if role == "blinded" and not any(d.get("action") == "unblind" and d.get("sample") == sample
                                         for d in log.of("decision")):
            reject(f"blinded sample {sample} read without unblinding decision")
    if step == "__check__":
        if check is None or reuse_source is not None:
            reject("a check attempt names (check, criteria, target) and cannot reuse")
        chk, crit, target = check
        if not usable(log, target):
            reject("check target is not a usable artifact")
        extra = check_inputs_for(log, target, chk)
        if extra is None:
            reject("a declared check input has no usable version")
        identity, inputs = check_identity(chk, crit, target, extra), {"target": target, **extra}
    else:
        if step not in eff["steps"] or check is not None:
            reject("unknown step")
        spec = eff["steps"][step]
        inputs = {up: provisional_input(log, up) for up in spec.upstream}
        if any(value is None for value in inputs.values()):
            reject("missing upstream")
        identity = expected_identity(log, step, inputs)
        if reuse_source is not None:
            rep = best_producer(log, reuse_source)
            if rep is None or rep[1].get("step") != step or rep[1].get("identity") != identity \
                    or not current(log, reuse_source):
                reject("reuse source is not a usable, current output of this step with this identity")
        else:
            if identity_failures(log, step, identity, spec.required):
                reject("this computation identity already failed a required check; change the computation")
            if not spec.allow_rerun and same_identity_ran(log, step, identity):
                reject("same identity already ran or is running and reruns are not allowed; use reuse")
            if unchecked_artifacts(log, step):
                reject("an earlier artifact of this checked step has no counted result for every required check; "
                       "check it before computing another")
    for fact in log.of("intent"):
        same = same_side_effect(fact, step, check) if step in SPECIAL_STEPS else (fact.get("step") == step)
        if same and exec_status(log, fact.get("attempt")) == "unknown":
            reject("same side effect has an unknown attempt; reconcile or abandon first")
    items = [("intent", "C", dict(attempt=attempt, step=step, identity=identity,
                                  inputs=tuple(sorted(inputs.items())), cost=cost, reads=tuple(reads)))]
    items += [("exposure", "C", dict(sample=sample, attempt=attempt)) for sample in reads]
    if reuse_source is not None:
        items.append(("reuse", "C", dict(attempt=attempt, source=reuse_source)))
    return log.append_batch(items, expect_head)[0]


def publish(log: Log, expect_head: int, did: str) -> Fact:
    """Publish a deliverable (Control §5.4): the deliverable id, the bound artifact, the target and achieved tiers
    and the counts of the dependency chain and the task, with compare-and-set on the derivation's sequence number."""
    if expect_head != log.head:
        raise StaleWrite("re-derive before publish")
    if not has_contract(log) or did not in contract(log)["deliverables"]:
        raise Admission("unknown deliverable")
    status = deliverable_status(log, did)
    if not status["met"]:
        raise Admission("deliverable not met at this head")
    step = contract(log)["deliverables"][did].step
    failures = prior_failures(log, step)
    draws = sum(len(step_artifacts(log, name)) for name in chain_steps(log, step))
    return log.append("publish", "C", expect_head, deliverable=did, digest=status["artifact"], target=status["target"],
                      achieved=status["achieved"], prior_failures=len(failures), chain_artifacts=draws,
                      failed_draws=len(failed_draws(log, step)),
                      failed_check_draws=len(failed_check_draws(log, step)),
                      confirmation_results=len(confirmation_results(log, step)),
                      task_failures=len(task_history(log)["failures"]),
                      task_artifacts=sum(task_history(log)["artifacts"].values()), head=expect_head,
                      derivation=DERIVATION_VERSION)
