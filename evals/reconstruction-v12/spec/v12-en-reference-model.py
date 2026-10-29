"""
hep-research reconstruction spec v12: reference model of the control layer (the Control part)

This is an executable description of the spec, not plugin code, and it does not mean that any runtime has passed acceptance.

The v11 design (replacing the v10.x enumeration of “protected aspects”):
- **Closed contract format**: a contract has only fixed fields; if a field is unknown or its type or range does not conform, the helper refuses the contract.
- **Tightening only**: a new contract that is “at least as strict” in every field (strictness order, §contract_at_least_as_strict) takes effect automatically;
  otherwise the whole contract is pending human approval (decision approve_contract) and has no effect at all until approved. There is no partial application.
- **Target tier and achieved tier are separate**: the contract states a target tier for each deliverable; the achieved tier is derived from facts. There is no downgrade mechanism —
  not reaching the target means partial completion.
- **Human decisions**: approve a contract, approve an identity continuation (replacing v10's impact-upper-bound exemption), assign producer ownership, unblind, abandon.
- **Identity and reuse are computed and checked by C**: callers cannot supply the computational identity; a reuse source must be a usable artifact of the same step with the same identity.
- Deliverables, iteration families and final rounds are all in the contract format; the final round must be a checked artifact and carry the convergence and free-mode checks declared by its family.

v11.1 (the 32 findings of S0 v11): the upstream set is part of the strictness order; fail is bound to the computational identity; accepted and publish are bound to deliverables;
the budget is charged by actual usage; field types are validated; an approval takes effect at the position of the approval fact, and later contracts are not re-evaluated retroactively; reuse does not change the binding order;
the first contract in M2/M3 is pending human confirmation; a family has only a fixed final round, with no maximum number of rounds.

v12 (the N1 findings of S0 v11.1): when same-identity reruns are not allowed, there is no rerun before the check either; append first fully validates every fact
(including exposure) before writing the whole batch, and the derivation cache is always cleared; the freeze condition constrains only results on confirmation samples.

v12.1 (spec copy; the S0 v12 round-1 findings): a step added by a later contract may not carry the values reserved for the first
contract or a human (confirmation not required, same-identity reruns, allowed not-applicable) and may not join an existing family
(S0v12-N1-F1); a checked step's earlier computed artifact must have a counted result for every required check before another
computation of that step is admitted, and publish records how many artifacts the dependency chain produced (S0v12-N1-F2); an attempt
id is unique across intents and admission rejections (S0v12-N1-F3); a family round may hold several steps (a partitioned round),
the final round has exactly one checked step, in-family upstreams come only from the same or the previous round, and every round
after the first consumes the previous one (S0v12-N4-F2, F4); the family's check names are check digests (S0v12-N4-F5).
v12.1, round 2: attempts of a step on the chain that ended without a usable artifact (failed, cancelled, unknown, abandoned,
or computed but unattested) are counted as failed draws in the report and in publish (S0r2-N1-F1); every field of B and
human facts is validated (S0r2-N1-F3); a step may require method-independent confirmation, and the freeze names which of
its confirmation samples are method-independent (S0r2-N5-F1); only the final step of a family is checked, and every step
of round r > 1 consumes round r-1 directly or through steps of its own round (S0r2-N4-F1, F2).
v12.1, round 3 (not re-reviewed; N1 did not pass S0): a sample counts as method-independent only when a freeze that
precedes its first exposure lists it so (S0r3-N1-F1); the report and publish also carry the task-wide history of
fail/inconclusive results and failed draws on steps off the deliverable's chain (S0r3-N1-F2).
v12.1, round 4 (user-approved fixes; N1 did not pass the fourth S0 round): a contract that changes a step's content so that
an earlier attempt's identity becomes current again (a revert) changes the binding among artifacts already seen, and like a
pin needs human approval; report and publish carry every confirmation-sample result on the chain (S0r4-N1-F1). The
confirmation fields belong to the deliverable, and a deliverable that becomes T3C by a later contract takes the reserved
values (confirmation and method-independent confirmation required) unless a human approves (S0r4-N1-F2). A check's
declared further inputs are named in the contract, resolved by C at admission and part of the check attempt's identity; an
input that is an upstream of the target must be the version the target consumed (S0r4-N1-F3). Only exposures written by C
are attributed to a check attempt (S0r4-N1-F4); the task-wide history counts the artifacts of every step (S0r4-N1-F5).
v12.1, round 5 (user-approved fixes; N1 did not pass the fifth S0 round): a revert is also recognised by its digest — an
artifact whose representative producer has another identity than its first producer in the step (an output already seen,
reproduced by a changed computation) is not bound without a human pin (S0r5-N1-F1). A check input that is not an upstream
of the target's step resolves only to that step's bound version, and the result counts only while it is still the bound
version; upstreams and check inputs together form an acyclic graph (S0r5-N1-F2). Admission keys the side effect of a
check attempt on check x criterion x target (S0r5-N1-F3).
v12.1, after the sixth S0 round (user decision: adopt one rule and start C1 with N1 not passed): the revert rule and
the reproduced rule are replaced by one binding rule — an artifact of a step is **overtaken** when an output first seen
in that step after it (any attempt of the step name, any contract, whatever its end state or attestation) is no longer
usable and current; an overtaken artifact binds only through a pin (human approval). This covers reverts, reproduced
digests, unattested peeks and removed-and-re-added steps (S0r6-N1-F1, F2). A step added by a later contract has no
pin (S0r6-N1-F2).

Run: python3 -I hep-research-reconstruction-v12-en-reference-model.py
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, replace
from typing import Any

DERIVATION_VERSION = "v12.1"


def h(*parts: Any) -> str:
    return hashlib.sha256(repr(parts).encode()).hexdigest()[:12]


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
TIER_RANK = {t: i for i, t in enumerate(TIERS)}
ROLES = {"exploration", "training", "control", "confirmation", "blinded"}
SPECIAL_STEPS = ("__check__",)
MODES = ("M1", "M2", "M3")
FREEZE_KEYS = {"step", "samples", "required"}


class NoContract(Exception):
    """No effective contract (none written yet, or the first contract in M2/M3 is still pending human confirmation)."""


@dataclass(frozen=True)
class Fact:
    seq: int
    kind: str
    writer: str
    data: tuple

    def get(self, k, default=None):
        return dict(self.data).get(k, default)


class StaleWrite(Exception):
    pass


class Admission(Exception):
    pass


class Rejected(Exception):
    """The fact's format or writer does not conform; the helper refuses to append it."""


class Log:
    def __init__(self):
        self.facts: list[Fact] = []
        self._memo: dict = {}
        self._by_kind: dict = {}
        self._by_attempt: dict = {}
        self._by_output: dict = {}
        self._by_target: dict = {}
        self._by_sample: dict = {}
        self._by_identity: dict = {}
        self._by_step_out: dict = {}
        self._by_check_target: dict = {}
        self._intent: dict = {}

    @property
    def head(self) -> int:
        return len(self.facts)

    def _validate(self, kind, writer, data, pending):
        if kind not in WRITERS:
            raise Rejected(f"unknown fact kind {kind}")
        for key in ("attempt", "sample", "target", "source", "step", "identity", "check", "criteria",
                    "check_attempt", "digest"):
            if key in data and data[key] is not None and not isinstance(data[key], str):
                raise Rejected(f"{key} must be a string")
        if "outputs" in data and not _strs(data["outputs"] if data["outputs"] is not None else ()):
            raise Rejected("outputs must be a tuple of digests")
        if kind == "exposure" and (not isinstance(data.get("sample"), str) or set(data) - {"sample", "attempt"}):
            raise Rejected("an exposure names one sample (and optionally the attempt or activity)")
        if writer not in WRITERS[kind]:
            raise Rejected(f"{writer} may not write {kind}")
        if kind in ("receipt", "reconcile") and data.get("end") not in END_VALUES:
            raise Rejected(f"end value {data.get('end')!r} not allowed")
        if kind == "check_result" and data.get("result") not in RESULT_VALUES:
            raise Rejected(f"result value {data.get('result')!r} not allowed")
        if kind == "decision" and data.get("action") not in DECISIONS:
            raise Rejected(f"decision {data.get('action')!r} not allowed")
        if kind == "intent" and attempt_id_taken(self, data["attempt"], pending):
            raise Rejected("attempt id must be unique")
        if kind == "session":
            if self.head != 0 or pending or data.get("mode") not in MODES or set(data) != {"mode"}:
                raise Rejected("a session fact is the first fact and names a mode M1/M2/M3")
        if kind == "contract":
            validate_contract(self, data.get("spec"))
        if kind in ("receipt", "reconcile") and data.get("usage") is not None and not _nonneg(data.get("usage")):
            raise Rejected("usage must be a finite number >= 0")
        why = fact_field_problem(kind, data)             # v12.1 round 2 (S0r2-N1-F3)
        if why:
            raise Rejected(why)
        if kind == "freeze":
            if set(data) - {"plan", "independent"} != FREEZE_KEYS or not isinstance(data.get("plan", ""), str):
                raise Rejected(f"freeze must have exactly the fields {sorted(FREEZE_KEYS)} (and optionally a plan "
                               f"digest: the frozen document with multiple-testing, cross-round and feasibility parts)")
            if not has_contract(self):
                raise Rejected("freeze before an effective contract")
            if not isinstance(data["step"], str) or data["step"] not in contract(self)["steps"]:
                raise Rejected("freeze names an unknown step")
            if not (isinstance(data["samples"], tuple) and all(isinstance(x, str) for x in data["samples"])):
                raise Rejected("freeze samples must be a tuple of sample names")
            if not _pairs(data["required"]):
                raise Rejected("freeze required must be a frozenset of (check, criteria) pairs")
            for smp in data["samples"]:
                if sample_role(self, smp) != "confirmation":
                    raise Rejected(f"freeze lists {smp}, which is not a confirmation sample")
            ind = data.get("independent", ())
            if not (isinstance(ind, tuple) and all(isinstance(x, str) for x in ind) and set(ind) <= set(data["samples"])):
                raise Rejected("freeze independent must be a tuple of its own samples (the method-independent ones)")

    def append_batch(self, items, expect_head: int | None = None) -> list[Fact]:
        """Append several facts with one compare-and-set; if any one does not conform, none of the batch is written."""
        if expect_head is not None and expect_head != self.head:
            raise StaleWrite(f"expected head {expect_head}, actual {self.head}")
        try:                                            # first fully validate every item; if any one does not conform, none of the batch is written
            for i, (kind, writer, data) in enumerate(items):
                self._validate(kind, writer, data, items[:i])
        finally:
            self._memo.clear()
        out = [Fact(self.head + i, kind, writer, tuple(sorted(data.items(), key=lambda kv: kv[0])))
               for i, (kind, writer, data) in enumerate(items)]
        for f in out:
            self.facts.append(f)
            self._index(f)
        self._memo.clear()
        return out

    def _index(self, f: Fact):
        self._by_kind.setdefault(f.kind, []).append(f)
        a = f.get("attempt")
        if a is not None:
            self._by_attempt.setdefault(a, []).append(f)
        if f.kind == "intent":
            self._intent[a] = f
            self._by_identity.setdefault(f.get("identity"), []).append(f)
            if f.get("step") == "__check__":
                self._by_check_target.setdefault(dict(f.get("inputs") or ()).get("target"), []).append(f)
        if f.kind in ("receipt", "reconcile", "reuse"):
            outs = (f.get("source"),) if f.kind == "reuse" else (f.get("outputs") or ())
            for d in outs:
                self._by_output.setdefault(d, []).append(f)
            it = self._intent.get(a)
            if it is not None:
                self._by_step_out.setdefault(it.get("step"), []).append(f)
        if f.kind == "check_result":
            self._by_target.setdefault(f.get("target"), []).append(f)
        if f.kind in ("exposure", "check_result") and f.get("sample") is not None:
            self._by_sample.setdefault(f.get("sample"), []).append(f)

    def mode(self) -> str:
        s = self._by_kind.get("session")
        return s[0].get("mode") if s else "M1"

    def append(self, kind: str, writer: str, expect_head: int | None = None, **data) -> Fact:
        return self.append_batch([(kind, writer, data)], expect_head)[0]

    def of(self, kind: str):
        return self._by_kind.get(kind, [])

    def of_attempt(self, attempt):
        return self._by_attempt.get(attempt, [])

    def results_for(self, target):
        return self._by_target.get(target, [])

    def of_sample(self, sample):
        return self._by_sample.get(sample, [])


def memo(fn):
    """Memoization within one log head: facts are only appended, never changed, so results do not change while head is unchanged."""
    def wrapper(log, *args):
        key = (fn.__name__, args)
        if key not in log._memo:
            log._memo[key] = fn(log, *args)
        return log._memo[key]
    wrapper.__name__ = fn.__name__
    wrapper.__wrapped__ = fn
    return wrapper


def fact_field_problem(kind, data) -> str | None:
    """v12.1 round 2 (S0r2-N1-F3): the fields of B, adapter and human facts have fixed types and values."""
    s = lambda k: isinstance(data.get(k), str)  # noqa: E731
    if kind in ("receipt", "reconcile"):
        if data.get("termination") not in ("confirmed", "unknown") or not s("attempt"):
            return "a receipt or reconcile names its attempt and a termination of confirmed or unknown"
    if kind in ("start", "cancel_request") and not s("attempt"):
        return f"{kind} names its attempt"
    if kind == "check_result" and not all(s(k) for k in ("target", "check", "criteria", "check_attempt")):
        return "a check result names its target, check, criteria and check attempt"
    if kind == "decision":
        need = {"approve_contract": (), "accept_identity": ("digest", "step", "old_identity", "new_identity"),
                "assign_producer": ("digest", "step"), "unblind": ("sample",), "abandon": ("attempt",)}
        a = data.get("action")
        if a in need and not all(s(k) for k in need[a]):
            return f"decision {a} needs {list(need[a])}"
        if a == "approve_contract" and (not isinstance(data.get("ref"), int) or isinstance(data.get("ref"), bool)):
            return "approve_contract names the sequence number of the contract it approves"
    return None


def attempt_id_taken(log, attempt, pending) -> bool:
    """v12.1 (S0v12-N1-F3): an attempt id is unique across intents and admission rejections."""
    return bool(log._by_attempt.get(attempt)) or any(
        k in ("intent", "admission_rejected") and d.get("attempt") == attempt for k, _, d in pending)


# ================================================================ closed contract format

@dataclass(frozen=True)
class StepSpec:
    program: str
    env: str = "env0"
    upstream: tuple = ()
    external: tuple = ()
    checked: bool = False
    required: frozenset = frozenset()          # required (check, criteria)
    na_allowed: frozenset = frozenset()
    check_inputs: frozenset = frozenset()       # r4 (S0r4-N1-F3): (check digest, step) — further inputs a required check reads
    family: str | None = None
    round: int | None = None
    allow_rerun: bool = False
    pin: str | None = None


@dataclass(frozen=True)
class Deliverable:
    step: str
    target: str                                 # T2 / T3E / T3C
    required: bool = True
    confirmation_required: bool = True          # r4 (S0r4-N1-F2): in effect when the target is T3C; a deliverable field
    independent_confirmation: bool = False      # v12.1 r2: a pass on a method-independent confirmation sample is also required


@dataclass(frozen=True)
class Family:
    final_round: int                            # the fixed final round; rounds must be exactly 1..final_round
    convergence_check: str                      # check digest of the convergence check among the final step's required checks
    mode_check: str                             # check digest of the free (unconstrained) mode check among the final step's required checks


CONTRACT_KEYS = {"steps", "deliverables", "families", "samples", "budget"}


def _nonneg(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0


def _finite_budget(b):
    return b is None or _nonneg(b)


def _strs(t):
    return isinstance(t, tuple) and all(isinstance(x, str) for x in t)


def _pairs(fs):
    return isinstance(fs, frozenset) and all(isinstance(p, tuple) and len(p) == 2 and _strs(p) for p in fs)


def _opt(x, typ):
    return x is None or (isinstance(x, typ) and not isinstance(x, bool))


def _types_ok(s: StepSpec) -> bool:
    return (isinstance(s.program, str) and isinstance(s.env, str) and _strs(s.upstream) and _strs(s.external)
            and len(set(s.upstream)) == len(s.upstream)
            and all(isinstance(getattr(s, k), bool) for k in ("checked", "allow_rerun"))
            and _pairs(s.required) and _pairs(s.na_allowed) and _pairs(s.check_inputs)
            and _opt(s.family, str) and _opt(s.round, int) and _opt(s.pin, str))


def family_chain_problem(steps, fam, f) -> str | None:
    """In-family upstreams come only from the same or the previous round, and every round after the first consumes the previous one."""
    members = {n: s for n, s in steps.items() if s.family == fam}
    for n, s in members.items():
        if any(steps[u].family == fam and steps[u].round not in (s.round, s.round - 1) for u in s.upstream):
            return f"{n} may consume only steps of its own or the previous round"
    for n, s in members.items():                   # r2 (S0r2-N4-F1): each step of round r > 1 reaches round r - 1
        if s.round > 1 and not _reaches_previous(steps, fam, n, set()):
            return f"{n} does not consume round {s.round - 1}, directly or through steps of its round"
    for n, s in members.items():                   # r2 (S0r2-N4-F2): only the final step is checked
        if s.checked and s.round != f.final_round:
            return f"{n}: only the family's final step is checked"
    return None


def _reaches_previous(steps, fam, n, seen) -> bool:
    s = steps[n]
    for u in s.upstream:
        us = steps[u]
        if us.family != fam:
            continue
        if us.round == s.round - 1:
            return True
        if us.round == s.round and u not in seen and _reaches_previous(steps, fam, u, seen | {n}):
            return True
    return False


def validate_contract(log: Log, spec: dict):
    """Format validation: closed fields, types, ranges, and cross-field consistency."""
    if not isinstance(spec, dict) or set(spec) != CONTRACT_KEYS:
        raise Rejected(f"contract must have exactly the fields {sorted(CONTRACT_KEYS)}")
    steps, dels, fams, smp = spec["steps"], spec["deliverables"], spec["families"], spec["samples"]
    if not all(isinstance(x, dict) and all(isinstance(k, str) for k in x) for x in (steps, dels, fams, smp)):
        raise Rejected("steps, deliverables, families and samples are maps keyed by name")
    if any(k.startswith("__") for k in steps):
        raise Rejected("step names starting with __ are reserved")
    if not all(isinstance(s, StepSpec) and _types_ok(s) for s in steps.values()):
        raise Rejected("every step must be a StepSpec with fields of the declared types")
    if not all(isinstance(d, Deliverable) and isinstance(d.step, str) and all(
            isinstance(getattr(d, k), bool) for k in ("required", "confirmation_required", "independent_confirmation"))
               for d in dels.values()):
        raise Rejected("every deliverable must be a Deliverable with fields of the declared types")
    if not all(isinstance(f, Family) and isinstance(f.final_round, int) and not isinstance(f.final_round, bool)
               and isinstance(f.convergence_check, str) and isinstance(f.mode_check, str)
               and f.convergence_check != f.mode_check for f in fams.values()):
        raise Rejected("every family must be a Family with fields of the declared types")
    if not _finite_budget(spec["budget"]):
        raise Rejected("budget must be null or a finite number >= 0")
    if any(r not in ROLES for r in smp.values()):
        raise Rejected("unknown sample role")
    for name, s in steps.items():
        for u in s.upstream:
            if u not in steps:
                raise Rejected(f"{name}: unknown upstream {u}")
        if s.checked and not s.required:
            raise Rejected(f"{name}: a checked step needs at least one required check")
        if not s.na_allowed <= s.required:
            raise Rejected(f"{name}: not-applicable may only be allowed for required checks")
        for c, u in s.check_inputs:                 # r4 (S0r4-N1-F3)
            if c not in {k for k, _ in s.required} or u not in steps or u == name:
                raise Rejected(f"{name}: a check input names a required check of this step and another step")
        if (s.family is None) != (s.round is None):
            raise Rejected(f"{name}: family and round go together")
        if s.family is not None and (s.family not in fams or not isinstance(s.round, int) or s.round < 1):
            raise Rejected(f"{name}: unknown family or bad round")
    for fam, f in fams.items():
        members = {n: s for n, s in steps.items() if s.family == fam}
        rounds = sorted({s.round for s in members.values()})
        if f.final_round < 1 or rounds != list(range(1, f.final_round + 1)):
            raise Rejected(f"family {fam}: rounds must be exactly 1..final_round, each with at least one step")
        finals = [n for n, s in members.items() if s.round == f.final_round and s.checked]
        if len(finals) != 1:
            raise Rejected(f"family {fam}: the final round must have exactly one checked step")
        why = family_chain_problem(steps, fam, f)  # v12.1: rounds are chained (S0v12-N4-F4)
        if why:
            raise Rejected(f"family {fam}: {why}")
        last = steps[finals[0]]
        names = {c for c, _ in last.required}
        if not last.checked or not {f.convergence_check, f.mode_check} <= names:
            raise Rejected(f"family {fam}: the final round must be checked and require the convergence "
                           f"and unconstrained-mode checks")
        if any(c in (f.convergence_check, f.mode_check) for c, _ in last.na_allowed):
            raise Rejected(f"family {fam}: the convergence and mode checks cannot be not-applicable")
    for did, d in dels.items():
        if d.step not in steps or d.target not in TIERS:
            raise Rejected(f"deliverable {did}: unknown step or tier")
        if not steps[d.step].checked:
            raise Rejected(f"deliverable {did}: its step must be checked")
        s = steps[d.step]
        if s.family is not None and s.round != fams[s.family].final_round:
            raise Rejected(f"deliverable {did}: an iteration deliverable must be the final round")
    seen, stack = set(), set()

    def visit(n):
        if n in stack:
            raise Rejected(f"cycle at {n}")
        if n in seen:
            return
        stack.add(n)
        for u in steps[n].upstream + tuple(sorted(x for _, x in steps[n].check_inputs)):   # r5 (S0r5-N1-F2)
            visit(u)
        stack.discard(n)
        seen.add(n)

    for n in steps:
        visit(n)
    for name, s in steps.items():
        if s.pin is not None and s.pin not in candidates_raw(log, name):
            raise Rejected(f"{name}: pin {s.pin} is not an output of this step")


def step_at_least_as_strict(o: StepSpec, n: StepSpec) -> bool:
    """Whether n is at least as strict as o. Program, environment and external dependencies are content fields: they may change, but changing them invalidates the artifacts.
    The upstream set is a strictness field (v11.1): upstreams may only be added, not removed or replaced — removing an upstream would move its check results out of the deliverable's dependency chain."""
    return (set(n.upstream) >= set(o.upstream)
            and (n.checked or not o.checked)
            and n.required >= o.required
            and n.na_allowed <= o.na_allowed
            and n.check_inputs == o.check_inputs
            and (n.family, n.round) == (o.family, o.round)
            and (not n.allow_rerun or o.allow_rerun)
            and n.pin == o.pin)


def contract_at_least_as_strict(old: dict, new: dict) -> bool:
    """Strictness order: holds only if every field is at least as strict; adding steps, deliverables, samples or families does not lower the requirements."""
    for name, os_ in old["steps"].items():
        ns = new["steps"].get(name)
        if ns is None or not step_at_least_as_strict(os_, ns):
            return False
    for name, ns in new["steps"].items():          # v12.1 (S0v12-N1-F1): an added step takes no value reserved for the
        if name in old["steps"]:                   # first contract or a human, and does not join an existing family
            continue
        if ns.allow_rerun or ns.na_allowed or ns.family in old["families"] or ns.pin is not None:   # r6: no pin
            return False
    for did, od in old["deliverables"].items():
        nd = new["deliverables"].get(did)
        if nd is None or nd.step != od.step or TIER_RANK[nd.target] < TIER_RANK[od.target] \
                or (od.required and not nd.required) \
                or (od.confirmation_required and not nd.confirmation_required) \
                or (od.independent_confirmation and not nd.independent_confirmation):
            return False
    for did, nd in new["deliverables"].items():    # r4 (S0r4-N1-F2): a deliverable that becomes T3C later takes the
        od = old["deliverables"].get(did)          # reserved values; "no" comes only from the first contract or a human
        if nd.target == "T3C" and (od is None or od.target != "T3C") \
                and not (nd.confirmation_required and nd.independent_confirmation):
            return False
    for fam, of in old["families"].items():
        if new["families"].get(fam) != of:
            return False
    for smp, role in old["samples"].items():
        if new["samples"].get(smp) != role:
            return False
    ob, nb = old["budget"], new["budget"]
    if ob is not None and (nb is None or nb > ob):
        return False
    return True


def _identity(step, s: StepSpec, inputs: dict) -> str:
    return h(step, s.program, s.env, s.external, tuple(sorted(inputs.items())))


@memo
def _contracts(log: Log):
    """Walk once through the contracts and approve_contract decisions in fact order. Returns (effective contract spec or None, status of each contract).

    - The first contract in M1 takes effect directly; the first contract in M2/M3 is pending human confirmation (DEC-12).
    - Each later one: at least as strict → takes effect; otherwise pending_approval, recording which effective contract it was proposed against.
    - approve_contract takes effect at its own position, and only if the approved contract is still pending and the effective contract is still the one it was proposed against;
      otherwise the approval has no effect (stale). Later contracts are not re-evaluated retroactively because of the approval.
    - When a contract takes effect, all contracts still pending lapse (lapsed) and must be proposed again before they can be approved."""
    eff, eff_seq = None, None
    status, against = {}, {}
    events = sorted(log.of("contract") + [d for d in log.of("decision") if d.get("action") == "approve_contract"],
                    key=lambda f: f.seq)
    by_seq = {f.seq: f for f in log.of("contract")}

    def activate(seq):
        nonlocal eff, eff_seq
        for k, v in status.items():
            if v == "effective":
                status[k] = "superseded"
            elif v == "pending_approval":
                status[k] = "lapsed"
        eff, eff_seq = by_seq[seq].get("spec"), seq
        status[seq] = "effective"

    for f in events:
        if f.kind == "contract":
            new = f.get("spec")
            if (eff is None and log.mode() == "M1" and not status) or \
                    (eff is not None and contract_at_least_as_strict(eff, new)):
                activate(f.seq)
            else:
                status[f.seq], against[f.seq] = "pending_approval", eff_seq
        else:
            ref = f.get("ref")
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
    """For the completion report: whether each contract is effective, superseded, pending_approval or lapsed."""
    return _contracts(log)[1][contract_fact.seq]


def spec_of(log, step) -> StepSpec:
    return contract(log)["steps"][step]


def sample_role(log, sample) -> str | None:
    if not has_contract(log):
        return None
    return contract(log)["samples"].get(sample)


# ================================================================ execution state

TERMINAL = {"success": "computed", "failure": "failed", "timeout": "failed", "cancelled": "cancelled"}


@memo
def _exec(log: Log, attempt: str):
    """(state, terminal fact). Only one terminal fact per attempt is in effect."""
    st, term, reconciled = "planned", None, False
    for f in log.of_attempt(attempt):
        k = f.kind
        if k == "admission_rejected" and st == "planned":
            st = "rejected"
        elif k == "intent" and st == "planned":
            st = "admitted"
        elif k == "reuse" and st == "admitted":
            st, term = "reused", f
        elif k == "start" and st == "admitted":
            st = "running"
        elif k == "cancel_request":
            st = {"admitted": "cancelled", "running": "cancelling"}.get(st, st)
        elif k == "receipt" and st in ("admitted", "running", "cancelling"):
            if f.get("termination") == "confirmed":
                st, term = TERMINAL[f.get("end")], f
            else:
                st = "unknown"
        elif k == "reconcile" and f.get("termination") == "confirmed":
            if st == "unknown":
                st, term = TERMINAL[f.get("end")], f
            elif st == "abandoned":
                reconciled = True
        elif k == "decision" and f.get("action") == "abandon" and st == "unknown":
            st = "abandoned"
    if st == "abandoned" and reconciled:
        return "abandoned_reconciled", None
    return st, term


def exec_status(log, attempt) -> str:
    return _exec(log, attempt)[0]


def terminal_fact(log, attempt):
    return _exec(log, attempt)[1]


def intent_of(log, attempt):
    return log._intent.get(attempt)


def reported_usage(log, attempt):
    us = [r.get("usage") for r in log.of_attempt(attempt) if r.kind in ("receipt", "reconcile")
          and r.get("usage") is not None]
    return max(us) if us else None


def charge(log, it) -> float:
    """Budget accounting (v11.1): the larger of the declared cost and the usage reported by B."""
    u = reported_usage(log, it.get("attempt"))
    return max(it.get("cost", 0.0), u if u is not None else 0.0)


@memo
def in_flight(log: Log) -> float:
    return sum(charge(log, f) for f in log.of("intent")
               if exec_status(log, f.get("attempt")) in
               ("admitted", "running", "cancelling", "unknown", "abandoned"))


@memo
def used(log: Log) -> float:
    return sum(charge(log, f) for f in log.of("intent")
               if exec_status(log, f.get("attempt")) in
               ("computed", "failed", "cancelled", "abandoned_reconciled", "reused"))


# ================================================================ artifacts and producers

def output_facts(log: Log, digest: str):
    return [f for f in log._by_output.get(digest, []) if terminal_fact(log, f.get("attempt")) is f]


@memo
def candidates_raw(log: Log, step: str):
    seen = {}
    for f in log._by_step_out.get(step, []):
        if terminal_fact(log, f.get("attempt")) is not f:
            continue
        outs = (f.get("source"),) if f.kind == "reuse" else (f.get("outputs") or ())
        for d in outs:
            seen.setdefault(d, f.seq)
    return sorted(seen, key=seen.get)


def attested(log, attempt) -> bool:
    """The reads or usage observed by B do not exceed what was declared. Usage above the declared cost (v11.1) also counts as exceeding: an artifact whose cost was under-reported is not usable."""
    if any(r.get("observed_exceeds_declared") for r in log.of_attempt(attempt) if r.kind in ("receipt", "reconcile")):
        return False
    it = intent_of(log, attempt)
    u = reported_usage(log, attempt)
    if u is None and log.mode() != "M1" and terminal_fact(log, attempt) is not None \
            and terminal_fact(log, attempt).kind != "reuse":
        return False                                    # M2/M3: B must report usage
    return not (it is not None and u is not None and u > it.get("cost", 0.0))


@memo
def producers(log: Log, digest: str):
    out = []
    for f in output_facts(log, digest):
        it = intent_of(log, f.get("attempt"))
        if it is None or it.get("step") in SPECIAL_STEPS:
            continue
        if exec_status(log, it.get("attempt")) in ("computed", "reused") and attested(log, it.get("attempt")):
            out.append((f.seq, it))
    return out


@memo
def claiming_steps(log: Log, digest: str) -> tuple:
    steps = contract(log)["steps"]
    return tuple(sorted({it.get("step") for _, it in producers(log, digest) if it.get("step") in steps}))


@memo
def owner_step(log: Log, digest: str):
    cs = claiming_steps(log, digest)
    if len(cs) == 1:
        return cs[0]
    for d in reversed(log.of("decision")):
        if d.get("action") == "assign_producer" and d.get("digest") == digest and d.get("step") in cs:
            return d.get("step")
    return None


def producer_conflict(log, digest) -> bool:
    return len(claiming_steps(log, digest)) > 1 and owner_step(log, digest) is None


def inputs_of(it) -> dict:
    return dict(it.get("inputs") or ())


def expected_identity(log: Log, step: str, inputs: dict) -> str:
    return _identity(step, spec_of(log, step), inputs)


def identity_accepted(log, digest, step, old_id, new_id) -> bool:
    """Human-approved identity continuation (replacing v10's impact-upper-bound exemption): valid only for this artifact and this pair of identities."""
    return any(d.get("action") == "accept_identity" and d.get("digest") == digest and d.get("step") == step
               and d.get("old_identity") == old_id and d.get("new_identity") == new_id
               for d in log.of("decision"))


@memo
def best_producer(log: Log, digest: str):
    """Usable producer of the owning step: those whose identity is current (or continued by approval) take priority; among them the earliest is taken (v11.1: reuse does not change the binding order).
    If none is current, the latest is taken. Returns (seq, intent)."""
    step = owner_step(log, digest)
    if step is None:
        return None
    best = None
    for seq, it in producers(log, digest):
        if it.get("step") != step:
            continue
        exp = expected_identity(log, step, inputs_of(it))
        cur = it.get("identity") == exp
        ok_id = cur or identity_accepted(log, digest, step, it.get("identity"), exp)
        rank = (ok_id, -seq if ok_id else seq)
        if best is None or rank > best[0]:
            best = (rank, seq, it)
    return None if best is None else best[1:]


def usable(log, digest) -> bool:
    return best_producer(log, digest) is not None


def step_of(log, digest):
    bp = best_producer(log, digest)
    return None if bp is None else bp[1].get("step")


def bind_seq(log, digest) -> int:
    bp = best_producer(log, digest)
    return -1 if bp is None else bp[0]


@memo
def self_current(log: Log, digest: str) -> bool:
    bp = best_producer(log, digest)
    if bp is None:
        return False
    _, it = bp
    step = it.get("step")
    exp = expected_identity(log, step, inputs_of(it))
    return it.get("identity") == exp or identity_accepted(log, digest, step, it.get("identity"), exp)


@memo
def overtaken(log: Log, digest: str) -> bool:
    """r6 (S0r6-N1-F1, F2): an output first seen in the step after this artifact — by any attempt of the step name, under
    any contract, whatever its end state or attestation — is no longer usable and current. Binding this artifact again
    would be a choice among outputs already seen, so it binds only through a pin (human approval)."""
    step = step_of(log, digest)
    order = candidates_raw(log, step)
    if digest not in order:
        return False
    return any(not (usable(log, e) and current(log, e)) for e in order[order.index(digest) + 1:])


@memo
def bound(log: Log, step: str):
    s = spec_of(log, step)
    if s.pin is not None:
        return s.pin if ok(log, s.pin) else None
    best = None
    for d in candidates_raw(log, step):
        if step_of(log, d) == step and ok(log, d) and not overtaken(log, d):
            if best is None or bind_seq(log, d) > bind_seq(log, best):
                best = d
    return best


def intermediate_round(log, step) -> bool:
    """A family member other than the final round's checked step (v12.1: a round may hold several steps)."""
    s = spec_of(log, step)
    return s.family is not None and not (s.round == contract(log)["families"][s.family].final_round and s.checked)


@memo
def upstream_state(log: Log, digest: str) -> str:
    """ok / stale / waiting."""
    _, it = best_producer(log, digest)
    me = spec_of(log, it.get("step"))
    ins = inputs_of(it)
    if set(me.upstream) != set(ins):
        return "stale"
    state = "ok"
    for u in me.upstream:
        d = ins[u]
        if d is None or not usable(log, d) or not current(log, d):
            return "stale"
        if step_of(log, d) != u:
            return "stale"
        us = spec_of(log, u)
        if intermediate_round(log, u) and us.family != me.family:
            return "stale"
        b = bound(log, u)
        if b == d:
            continue
        if us.pin is not None:
            if us.pin != d:
                return "stale"
            state = "waiting"
            continue
        if b is not None and bind_seq(log, b) > bind_seq(log, d):
            return "stale"
        state = "waiting"
    return state


def current(log, digest) -> bool:
    return self_current(log, digest) and upstream_state(log, digest) != "stale"


# ================================================================ checks, freeze and achieved tier

def check_identity(chk, crit, target, extra=None):
    """r4 (S0r4-N1-F3): the declared further inputs, resolved by C, are part of the check attempt's identity."""
    return h("check", chk, crit, target) if not extra else h("check", chk, crit, target, tuple(sorted(extra.items())))


def declared_check_inputs(log, target, chk) -> tuple:
    st = step_of(log, target)
    return tuple(sorted(u for c, u in spec_of(log, st).check_inputs if c == chk)) if st is not None else ()


def check_inputs_for(log, target, chk):
    """At admission C resolves each declared input: an upstream of the target's step to the version the target consumed,
    any other step to its bound version (r5, S0r5-N1-F2: never a held or unbound one). None if one cannot be resolved."""
    consumed = inputs_of(best_producer(log, target)[1])
    out = {}
    for u in declared_check_inputs(log, target, chk):
        d = consumed[u] if u in consumed else bound(log, u)
        if d is None:
            return None
        out["input:" + u] = d
    return out


def check_attempt_of(it, target, chk, crit) -> bool:
    ins = inputs_of(it)
    extra = {k: v for k, v in ins.items() if k != "target"}
    return ins.get("target") == target and it.get("identity") == check_identity(chk, crit, target, extra)


def check_inputs_hold(log, it, target, chk) -> bool:
    """The attempt read exactly the declared inputs of the effective contract; an upstream input is the consumed version,
    any other input is still the bound version of its step (r5, S0r5-N1-F2)."""
    extra = {k: v for k, v in inputs_of(it).items() if k != "target"}
    if set(extra) != {"input:" + u for u in declared_check_inputs(log, target, chk)}:
        return False
    consumed = inputs_of(best_producer(log, target)[1])
    return all(extra[k] == (consumed[k[6:]] if k[6:] in consumed else bound(log, k[6:])) for k in extra)


def valid_check_attempt(log, r, target, chk, crit) -> bool:
    a = r.get("check_attempt")
    it = intent_of(log, a)
    return (it is not None and exec_status(log, a) == "computed" and attested(log, a)
            and check_attempt_of(it, target, chk, crit) and check_inputs_hold(log, it, target, chk))


def result_sample(log, r):
    smp = r.get("sample")
    it = intent_of(log, r.get("check_attempt"))
    return smp if smp is not None and it is not None and smp in (it.get("reads") or ()) else None


def pending_check_attempts(log, target, chk, crit) -> bool:
    for it in log._by_check_target.get(target, []):
        if check_attempt_of(it, target, chk, crit) and exec_status(log, it.get("attempt")) in ("admitted", "running", "cancelling", "unknown", "abandoned"):
            return True
    return False


@memo
def same_identity_outputs(log: Log, step: str, identity: str) -> tuple:
    """Outputs of all attempts of the same step with the same computational identity (copies from reruns)."""
    out = []
    for it in log._by_identity.get(identity, []):
        if it.get("step") != step:
            continue
        tf = terminal_fact(log, it.get("attempt"))
        if tf is None:
            continue
        for d in ((tf.get("source"),) if tf.kind == "reuse" else (tf.get("outputs") or ())):
            if d not in out:
                out.append(d)
    return tuple(out)


def identity_failures(log, step, identity, pairs):
    """v11.1: fail and inconclusive are bound to the computational identity — a required-check failure on any copy with the same identity counts."""
    return [r for d in same_identity_outputs(log, step, identity) for r in log.results_for(d)
            if (r.get("check"), r.get("criteria")) in pairs and r.get("result") in ("fail", "inconclusive")]


@memo
def checks_state(log: Log, digest: str) -> str:
    """ok / missing / held. fail and inconclusive count whatever the check attempt's state, and are bound to the computational identity (v11.1)."""
    _, it = best_producer(log, digest)
    s = spec_of(log, it.get("step"))
    if not s.checked:
        return "ok"
    if identity_failures(log, it.get("step"), it.get("identity"), s.required):
        return "held"
    missing = False
    for chk, crit in s.required:
        rs = [r for r in log.results_for(digest) if (r.get("check"), r.get("criteria")) == (chk, crit)]
        if any(r.get("result") in ("fail", "inconclusive") for r in rs):
            return "held"
        if any(r.get("result") == "not-applicable" and (chk, crit) not in s.na_allowed for r in rs):
            return "held"
        good = [r for r in rs if valid_check_attempt(log, r, digest, chk, crit) and (
            r.get("result") == "pass" or
            (r.get("result") == "not-applicable" and (chk, crit) in s.na_allowed))]
        if not good or pending_check_attempts(log, digest, chk, crit):
            missing = True
    return "missing" if missing else "ok"


@memo
def freeze_ok(log: Log, digest: str, conf_req: bool = True, indep_req: bool = False) -> bool:
    """Freeze and confirmation conditions for T3-C; the two flags are the deliverable's (r4, S0r4-N1-F2)."""
    _, it = best_producer(log, digest)
    step = it.get("step")
    s = spec_of(log, step)
    fz = [f for f in log.of("freeze") if f.get("step") == step and f.get("required") == s.required]
    if not fz:
        return False
    first = min(f.seq for f in fz)
    results = [r for r in log.results_for(digest) if (r.get("check"), r.get("criteria")) in s.required]
    if any(r.seq < first for r in results):
        return False
    mine = {r.get("check_attempt") for r in results}        # this artifact's required-check attempts
    conf_ok = indep_ok = False
    for r in results:
        smp = result_sample(log, r)
        if smp is None or sample_role(log, smp) != "confirmation":
            continue                                    # only results on confirmation samples are constrained by the freeze condition (v12)
        holding = [f.seq for f in fz if smp in f.get("samples")]
        if not holding:
            return False
        for e in log.of_sample(smp):
            if e.kind != "exposure" or e.seq >= r.seq:
                continue
            if e.seq < min(holding) or e.writer != "C" or e.get("attempt") not in mine:   # r4 (S0r4-N1-F4)
                return False
        for r2 in log.of_sample(smp):
            if r2.kind == "check_result" and r2.seq < r.seq and r2.get("target") != digest \
                    and result_sample(log, r2) == smp:
                return False
        if r.get("result") == "pass" and valid_check_attempt(log, r, digest, r.get("check"), r.get("criteria")):
            conf_ok = True
            if independent_sample(log, step, s.required, smp):
                indep_ok = True
    if indep_req and not independent_ok(log, digest, indep_ok):
        return False
    return conf_ok or not conf_req


def independent_sample(log, step, required, smp) -> bool:
    """r3 (S0r3-N1-F1): only a freeze that precedes the sample's first exposure can label it method-independent."""
    first = min((e.seq for e in log.of_sample(smp) if e.kind == "exposure"), default=None)
    return any(smp in (f.get("independent") or ()) and smp in f.get("samples") and (first is None or f.seq < first)
               for f in log.of("freeze") if f.get("step") == step and f.get("required") == required)


def independent_ok(log, digest, found) -> bool:
    """v12.1 r2 (S0r2-N5-F1): a valid pass on a sample the freeze lists as method-independent."""
    return found


@memo
def ok(log: Log, digest: str) -> bool:
    if not usable(log, digest):
        return False
    return current(log, digest) and upstream_state(log, digest) == "ok" and checks_state(log, digest) == "ok"


def achieved_tier(log, digest, conf_req: bool = True, indep_req: bool = False) -> str | None:
    """Achieved tier derived from facts: T2 needs ok; T3E has the same mechanical conditions as T2 (the difference is in how the report labels it); T3C additionally needs freeze and confirmation."""
    if not ok(log, digest) or not spec_of(log, step_of(log, digest)).checked:
        return None
    return "T3C" if freeze_ok(log, digest, conf_req, indep_req) else "T3E"


def chain_steps(log, step) -> list:
    """The deliverable step and all of its upstreams in the effective contract."""
    steps, out, todo = contract(log)["steps"], [], [step]
    while todo:
        n = todo.pop()
        if n not in out:
            out.append(n)
            todo.extend(steps[n].upstream)
    return out


def prior_failures(log, step) -> list:
    """For the report (v11.1): every fail or inconclusive any artifact on this dependency chain has had, whether or not its identity has since changed."""
    out = []
    for n in chain_steps(log, step):
        for d in candidates_raw(log, n):
            for r in log.results_for(d):
                if r.get("result") in ("fail", "inconclusive"):
                    out.append((n, d, r.get("check"), r.get("criteria"), r.get("result")))
    return out


def failed_draws(log, step) -> list:
    """v12.1 r2 (S0r2-N1-F1): computation attempts of the chain that ended without a usable artifact — failed,
    cancelled, unknown, abandoned, or computed but unattested — so that turning a disliked draw into an execution failure
    stays visible in the report and in publish."""
    out = []
    for n in chain_steps(log, step):
        for it in log.of("intent"):
            if it.get("step") != n:
                continue
            a = it.get("attempt")
            st = exec_status(log, a)
            if st in ("failed", "cancelled", "unknown", "abandoned", "abandoned_reconciled") or \
                    (st == "computed" and not attested(log, a)):
                out.append((n, a, st))
    return out


def confirmation_results(log, step) -> list:
    """r4 (S0r4-N1-F1): every result on a confirmation sample of any artifact of the chain, so that confirming several
    draws on different samples and keeping one stays visible."""
    return [(n, d, r.get("check"), result_sample(log, r), r.get("result")) for n in chain_steps(log, step)
            for d in candidates_raw(log, n) for r in log.results_for(d)
            if result_sample(log, r) is not None and sample_role(log, result_sample(log, r)) == "confirmation"]


def task_history(log) -> dict:
    """r3 (S0r3-N1-F2): fail/inconclusive results and failed draws on every step of the effective contract, so a selection
    made on a step off the deliverable's chain stays visible."""
    steps = contract(log)["steps"]
    fails = [(n, d, r.get("check"), r.get("result")) for n in steps for d in candidates_raw(log, n)
             for r in log.results_for(d) if r.get("result") in ("fail", "inconclusive")]
    draws = [x for n in steps for x in failed_draws_of_step(log, n)]
    arts = {n: len(step_artifacts(log, n)) for n in steps}  # r4 (S0r4-N1-F5): unchecked side-step variants are counted too
    return {"failures": fails, "failed_draws": draws, "artifacts": arts}


def failed_draws_of_step(log, n) -> list:
    out = []
    for it in log.of("intent"):
        if it.get("step") != n:
            continue
        a = it.get("attempt")
        st = exec_status(log, a)
        if st in ("failed", "cancelled", "unknown", "abandoned", "abandoned_reconciled") or \
                (st == "computed" and not attested(log, a)):
            out.append((n, a, st))
    return out


def deliverable_status(log, did) -> dict:
    d = contract(log)["deliverables"][did]
    a = bound(log, d.step)
    got = achieved_tier(log, a, d.confirmation_required, d.independent_confirmation) if a is not None else None
    if got == "T3E" and d.target == "T2":
        got = "T2"
    met = got is not None and TIER_RANK[got] >= TIER_RANK[d.target]
    return {"artifact": a, "target": d.target, "achieved": got, "met": met, "required": d.required}


def report_status(log, did) -> dict:
    """One row of the completion report: deliverable_status plus the historical failures on the dependency chain."""
    step = contract(log)["deliverables"][did].step
    return {**deliverable_status(log, did), "prior_failures": prior_failures(log, step),
            "failed_draws": failed_draws(log, step), "confirmation_results": confirmation_results(log, step),
            "task_history": task_history(log)}


def accepted(log, digest) -> bool:
    """The artifact is the bound version of at least one deliverable, and every deliverable bound to it meets its target tier (v11.1:
    a lower-target deliverable on the same step cannot vouch for a higher-target deliverable)."""
    mine = [did for did, d in contract(log)["deliverables"].items() if bound(log, d.step) == digest]
    return bool(mine) and all(deliverable_status(log, did)["met"] for did in mine)


def historical_failures(log, digest):
    st = step_of(log, digest)
    req = spec_of(log, st).required if st is not None else frozenset()
    return [(r.get("check"), r.get("criteria"), r.get("result")) for r in log.results_for(digest)
            if r.get("result") in ("fail", "inconclusive") and (r.get("check"), r.get("criteria")) not in req]


def label(log, digest) -> str:
    if producer_conflict(log, digest):
        return "producer_conflict"
    if not producers(log, digest) or not usable(log, digest):
        return "not_usable"
    step = step_of(log, digest)
    s = spec_of(log, step)
    if not current(log, digest):
        return "invalidated"
    if intermediate_round(log, step):
        later = [n for n, x in contract(log)["steps"].items()
                 if x.family == s.family and x.round > s.round and any(usable(log, d) for d in candidates_raw(log, n))]
        return "superseded_by_iteration" if later else "iteration_internal"
    if upstream_state(log, digest) == "waiting":
        return "blocked_upstream"
    cs = checks_state(log, digest)
    if cs == "held":
        return "held"
    if cs == "missing":
        return "unchecked"
    if bound(log, step) != digest:
        return "overtaken" if overtaken(log, digest) and spec_of(log, step).pin != digest else "superseded"
    return "ok"


# ================================================================ admission, check, publish

def provisional_input(log, step):
    b = bound(log, step)
    if b is not None:
        return b
    best = None
    for d in candidates_raw(log, step):
        if step_of(log, d) == step and current(log, d):
            if best is None or bind_seq(log, d) > bind_seq(log, best):
                best = d
    return best


def same_identity_ran(log, step, identity) -> bool:
    """v12: the same step with the same identity already has an attempt that is in flight, or that succeeded and is attested (whether or not it has been checked)."""
    for f in log._by_identity.get(identity, []):
        if f.get("step") != step:
            continue
        st = exec_status(log, f.get("attempt"))
        if st in ("admitted", "running", "cancelling", "unknown", "abandoned") or \
                (st in ("computed", "reused") and attested(log, f.get("attempt"))):
            return True
    return False


def counted_result(log, digest, chk, crit) -> bool:
    """A result of any value from a valid check attempt of this check x criteria x target."""
    return any((r.get("check"), r.get("criteria")) == (chk, crit) and valid_check_attempt(log, r, digest, chk, crit)
               for r in log.results_for(digest))


def step_artifacts(log, step) -> list:
    """Every artifact a computed, attested attempt of this step produced (any identity, current or not)."""
    return [d for d in candidates_raw(log, step) if any(it.get("step") == step for _, it in producers(log, d))]


def unchecked_artifacts(log, step) -> list:
    """v12.1 (S0v12-N1-F2): artifacts of a checked step that lack a counted result for some required check."""
    s = spec_of(log, step)
    if not s.checked:
        return []
    return [d for d in step_artifacts(log, step) if not all(counted_result(log, d, c, k) for c, k in s.required)]


def same_side_effect(f, step, check) -> bool:
    """r5 (S0r5-N1-F3): check attempts have the same side effect when they check the same check x criterion x target,
    whatever check inputs were resolved (Control §3)."""
    return f.get("step") == step and check_attempt_of(f, check[2], check[0], check[1])


def admit(log: Log, expect_head: int, attempt: str, step: str, cost: float = 1.0, reads: tuple = (),
          check: tuple | None = None, reuse_source: str | None = None) -> Fact:
    """C computes the identity; the caller may specify only the step, reads, cost and (for a check attempt) the (check, criteria, target) to check."""
    if expect_head != log.head:
        raise StaleWrite("re-read and re-derive before admission")

    def reject(reason):
        log.append("admission_rejected", "C", attempt=attempt, step=step, reason=reason)
        raise Admission(reason)

    if not has_contract(log):
        reject("no effective contract")
    c = contract(log)
    if not _nonneg(cost):
        reject("cost must be a finite number >= 0")
    if c["budget"] is not None and used(log) + in_flight(log) + cost > c["budget"]:
        reject("budget: used + in-flight + request exceeds limit")
    for smp in reads:
        role = sample_role(log, smp)
        if role == "confirmation":
            if step != "__check__":
                reject(f"confirmation sample {smp} may be read only by a check attempt")
            if not any(smp in f.get("samples") for f in log.of("freeze")):
                reject(f"confirmation sample {smp} read before freeze")
        if role == "blinded" and not any(d.get("action") == "unblind" and d.get("sample") == smp
                                         for d in log.of("decision")):
            reject(f"blinded sample {smp} read without unblinding decision")
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
        if step not in c["steps"] or check is not None:
            reject("unknown step")
        s = c["steps"][step]
        inputs = {u: provisional_input(log, u) for u in s.upstream}
        if any(v is None for v in inputs.values()):
            reject("missing upstream")
        identity = expected_identity(log, step, inputs)
        if reuse_source is not None:
            bp = best_producer(log, reuse_source)
            if bp is None or bp[1].get("step") != step or bp[1].get("identity") != identity \
                    or not current(log, reuse_source):
                reject("reuse source is not a usable, current output of this step with this identity")
        else:
            if identity_failures(log, step, identity, s.required):
                reject("this computation identity already failed a required check; change the computation")
            if not s.allow_rerun and same_identity_ran(log, step, identity):
                reject("same identity already ran or is running and reruns are not allowed; use reuse")
            if unchecked_artifacts(log, step):
                reject("an earlier artifact of this checked step has no counted result for every required check; "
                       "check it before computing another")
    for f in log.of("intent"):
        same = same_side_effect(f, step, check) if step in SPECIAL_STEPS else (f.get("step") == step)
        if same and exec_status(log, f.get("attempt")) == "unknown":
            reject("same side effect has an unknown attempt; reconcile or abandon first")
    items = [("intent", "C", dict(attempt=attempt, step=step, identity=identity,
                                  inputs=tuple(sorted(inputs.items())), cost=cost, reads=tuple(reads)))]
    items += [("exposure", "C", dict(sample=smp, attempt=attempt)) for smp in reads]
    if reuse_source is not None:
        items.append(("reuse", "C", dict(attempt=attempt, source=reuse_source)))
    return log.append_batch(items, expect_head)[0]


def publish(log: Log, expect_head: int, did: str) -> Fact:
    """Publish a deliverable (v11.1): record the deliverable id, the bound artifact, and the target and achieved tiers."""
    if expect_head != log.head:
        raise StaleWrite("re-derive before publish")
    if not has_contract(log) or did not in contract(log)["deliverables"]:
        raise Admission("unknown deliverable")
    st = deliverable_status(log, did)
    if not st["met"]:
        raise Admission("deliverable not met at this head")
    step = contract(log)["deliverables"][did].step
    pf = prior_failures(log, step)
    draws = sum(len(step_artifacts(log, n)) for n in chain_steps(log, step))
    return log.append("publish", "C", expect_head, deliverable=did, digest=st["artifact"], target=st["target"],
                      achieved=st["achieved"], prior_failures=len(pf), chain_artifacts=draws,
                      failed_draws=len(failed_draws(log, step)),
                      confirmation_results=len(confirmation_results(log, step)),
                      task_failures=len(task_history(log)["failures"]),
                      task_artifacts=sum(task_history(log)["artifacts"].values()), head=expect_head,
                      derivation=DERIVATION_VERSION)


# ================================================================ scenario test helpers

C1 = frozenset({("chkA", "crit1")})


def spec(steps, deliverables=None, families=None, samples=None, budget=None):
    return {"steps": steps, "deliverables": deliverables if deliverables is not None else {},
            "families": families or {}, "samples": samples or {}, "budget": budget}


def base_steps(**reco_kw):
    kw = {"program": "pReco", "upstream": ("raw",), "checked": True, "required": C1, **reco_kw}
    return {"raw": StepSpec(program="pRaw"), "reco": StepSpec(**kw)}


def new_log(steps, target="T2", samples=None, budget=None, deliverables=None, families=None, mode=None) -> Log:
    log = Log()
    if mode is not None:
        log.append("session", "C", mode=mode)
    dels = deliverables if deliverables is not None else {"D": Deliverable("reco", target)}
    log.append("contract", "agent", spec=spec(steps, dels, families, samples, budget))
    return log


def recontract(log: Log, samples=None, budget="keep", deliverables=None, families=None, **changes) -> Fact:
    c = contract(log)
    steps = dict(c["steps"])
    steps.update(changes)
    return log.append("contract", "agent", spec=spec(
        steps, deliverables if deliverables is not None else dict(c["deliverables"]),
        families if families is not None else dict(c["families"]),
        samples if samples is not None else dict(c["samples"]),
        c["budget"] if budget == "keep" else budget))


def approve(log, cf):
    log.append("decision", "human", action="approve_contract", ref=cf.seq)


def run(log: Log, attempt: str, step: str, out: str, end="success", termination="confirmed", reads=(),
        **extra) -> str:
    admit(log, log.head, attempt, step, reads=reads)
    log.append("start", "B", attempt=attempt)
    log.append("receipt", "B", attempt=attempt, end=end, termination=termination,
               outputs=(out,) if termination == "confirmed" else (), **extra)
    return out


def check(log: Log, target: str, chk: str, crit: str, result: str, attempt: str, sample=None,
          end="success", termination="confirmed"):
    admit(log, log.head, attempt, "__check__", cost=0.0, reads=(sample,) if sample else (),
          check=(chk, crit, target))
    log.append("receipt", "B", attempt=attempt, end=end, termination=termination, outputs=())
    log.append("check_result", "B", target=target, check=chk, criteria=crit, result=result,
               check_attempt=attempt, sample=sample)


def expect(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__}")


def reco_spec(**kw):
    base = dict(program="pReco", upstream=("raw",), checked=True, required=C1)
    base.update(kw)
    return StepSpec(**base)


def t3c_steps(**kw):
    return base_steps(**kw)


# ================================================================ basic paths and states (v10 scenarios reused, changed to v11 semantics)

def t01_happy_path():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    assert accepted(log, "X1") and label(log, "X1") == "ok"
    assert deliverable_status(log, "D") == {"artifact": "X1", "target": "T2", "achieved": "T2", "met": True,
                                            "required": True}


def t02_unknown_termination_blocks_until_reconcile():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1")
    run(log, "a2", "reco", "X1", termination="unknown")
    assert exec_status(log, "a2") == "unknown" and not usable(log, "X1")
    expect(Admission, admit, log, log.head, "a3", "reco")
    log.append("reconcile", "B", attempt="a2", end="success", termination="confirmed", outputs=("X1",))
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    assert accepted(log, "X1")


def t03_timeout_confirmed_is_failed():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1", end="timeout")
    assert exec_status(log, "a1") == "failed"


def t04_check_fix_needs_human_approval_and_no_recompute():
    steps = base_steps()
    steps["raw"] = StepSpec(program="pRaw", checked=True, required=frozenset({("chkR", "k1")}))
    log = new_log(steps)
    run(log, "a1", "raw", "R1")
    check(log, "R1", "chkR", "k1", "fail", "c0")
    run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    assert label(log, "R1") == "held" and label(log, "X1") == "blocked_upstream"
    n = len([f for f in log.of("intent") if f.get("step") not in SPECIAL_STEPS])
    cf = recontract(log, raw=StepSpec(program="pRaw", checked=True, required=frozenset({("chkR2", "k1")})))
    assert contract_status(log, cf) == "pending_approval"
    check(log, "R1", "chkR2", "k1", "pass", "c2")
    assert label(log, "R1") == "held"                       # not approved: still judged by the original check
    approve(log, cf)
    assert ok(log, "R1") and accepted(log, "X1")
    assert len([f for f in log.of("intent") if f.get("step") not in SPECIAL_STEPS]) == n
    assert ("chkR", "k1", "fail") in historical_failures(log, "R1")


def t05_program_change_invalidates_downstream():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    recontract(log, raw=StepSpec(program="pRaw_v2"))
    assert label(log, "R1") == "invalidated" and label(log, "X1") == "invalidated"


def t06_external_condition_change_invalidates():
    log = new_log(base_steps(external=("cond_v1",)))
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    assert accepted(log, "X1")
    recontract(log, reco=reco_spec(external=("cond_v2",)))
    assert label(log, "X1") == "invalidated"


def t07_no_cherry_picking():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "fail", "c1")
    check(log, "X1", "chkA", "crit1", "pass", "c2")
    assert label(log, "X1") == "held"


def iteration_steps():
    return {
        "al1": StepSpec(program="pAl", family="align", round=1),
        "al2": StepSpec(program="pAl", upstream=("al1",), family="align", round=2),
        "al3": StepSpec(program="pAl", upstream=("al2",), family="align", round=3, checked=True,
                        required=frozenset({("converged", "c"), ("weak_mode", "w")})),
        "reco": StepSpec(program="pReco", upstream=("al3",), checked=True, required=C1),
    }


ALIGN = {"align": Family(final_round=3, convergence_check="converged", mode_check="weak_mode")}


def t08_iteration_labels_and_nonconvergence():
    log = new_log(iteration_steps(), families=ALIGN)
    run(log, "i1", "al1", "A1")
    assert label(log, "A1") == "iteration_internal"
    run(log, "i2", "al2", "A2"); run(log, "i3", "al3", "A3")
    assert label(log, "A1") == "superseded_by_iteration"
    check(log, "A3", "converged", "c", "pass", "k1"); check(log, "A3", "weak_mode", "w", "pass", "k2")
    run(log, "r1", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "k3")
    assert ok(log, "A3") and accepted(log, "X1")
    log2 = new_log(iteration_steps(), families=ALIGN)
    for a, s, o in [("i1", "al1", "A1"), ("i2", "al2", "A2"), ("i3", "al3", "A3")]:
        run(log2, a, s, o)
    check(log2, "A3", "converged", "c", "fail", "k1")
    run(log2, "r1", "reco", "X1")
    check(log2, "X1", "chkA", "crit1", "pass", "k3")
    assert label(log2, "A3") == "held" and label(log2, "X1") == "blocked_upstream"


def t09_freeze_must_precede_confirmation():
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation"})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    expect(Admission, check, log, "X1", "chkA", "crit1", "pass", "c1", sample="S")
    log.append("freeze", "agent", step="reco", samples=("S",), required=C1)
    check(log, "X1", "chkA", "crit1", "pass", "c2", sample="S")
    assert accepted(log, "X1") and deliverable_status(log, "D")["achieved"] == "T3C"


def t10_cas_and_budget_with_in_flight():
    log = new_log(base_steps(), budget=2.0)
    head = log.head
    admit(log, head, "a1", "raw")
    expect(StaleWrite, admit, log, head, "a2", "raw")
    log.append("receipt", "B", attempt="a1", end="success", termination="unknown", outputs=())
    expect(Admission, admit, log, log.head, "b1", "reco")
    log.append("decision", "human", action="abandon", attempt="a1")
    assert in_flight(log) == 1.0 and exec_status(log, "a1") == "abandoned"


def t11_unattested_not_usable():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1", observed_exceeds_declared=True)
    assert not usable(log, "R1") and label(log, "R1") == "not_usable"


def t12_unchecked_intermediate_is_cheap():
    steps = {"s1": StepSpec(program="p1"), "s2": StepSpec(program="p2", upstream=("s1",)),
             "s3": StepSpec(program="p3", upstream=("s2",)),
             "out": StepSpec(program="p4", upstream=("s3",), checked=True, required=C1)}
    log = new_log(steps, deliverables={"D": Deliverable("out", "T2")})
    for i, s in enumerate(["s1", "s2", "s3"]):
        run(log, f"a{i}", s, f"I{i}")
    run(log, "a9", "out", "Y")
    check(log, "Y", "chkA", "crit1", "pass", "c1")
    assert accepted(log, "Y") and len(log.of("check_result")) == 1


def t13_superseded_and_pin_needs_approval():
    log = new_log(base_steps(allow_rerun=True))
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    run(log, "a3", "reco", "X2")
    check(log, "X2", "chkA", "crit1", "pass", "c2")
    assert label(log, "X1") == "superseded" and accepted(log, "X2")
    cf = recontract(log, reco=reco_spec(pin="X1", allow_rerun=True))
    assert bound(log, "reco") == "X2"                       # changing the pin is not tightening: pending approval
    approve(log, cf)
    assert bound(log, "reco") == "X1" and accepted(log, "X1")


def t14_same_identity_rerun_is_reuse_unless_allowed():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1")
    expect(Admission, admit, log, log.head, "a2", "raw")
    admit(log, log.head, "r1", "raw", cost=0.0, reuse_source="R1")
    assert exec_status(log, "r1") == "reused"
    log2 = new_log({**base_steps(), "raw": StepSpec(program="pRaw", allow_rerun=True)})
    run(log2, "a1", "raw", "R1"); run(log2, "a2", "reco", "X1")
    check(log2, "X1", "chkA", "crit1", "pass", "c1")
    run(log2, "a3", "raw", "R2")
    assert bound(log2, "raw") == "R2" and label(log2, "X1") == "invalidated"


def t16_lowering_without_approval_is_ignored():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "fail", "c1")
    recontract(log, reco=reco_spec(required=frozenset({("chkA", "loose")})))
    check(log, "X1", "chkA", "loose", "pass", "c2")
    assert label(log, "X1") == "held"
    log = new_log(base_steps(required=frozenset({("A", "a"), ("B", "b")})))
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "A", "a", "fail", "c1"); check(log, "X1", "B", "b", "pass", "c2")
    recontract(log, reco=reco_spec(required=frozenset({("B", "b")})))
    assert label(log, "X1") == "held"
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation"})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    recontract(log, deliverables={"D": Deliverable("reco", "T2")})
    st = deliverable_status(log, "D")
    assert st["target"] == "T3C" and not st["met"] and st["achieved"] == "T3E"


def t17_human_approved_change_takes_effect():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "fail", "c1")
    cf = recontract(log, reco=reco_spec(required=frozenset({("chkA", "crit2")})))
    check(log, "X1", "chkA", "crit2", "pass", "c2")
    assert not accepted(log, "X1")
    expect(Rejected, log.append, "decision", "agent", action="approve_contract", ref=cf.seq)
    approve(log, cf)
    assert accepted(log, "X1") and historical_failures(log, "X1") == [("chkA", "crit1", "fail")]


def t18_asymmetric_check_attempt_states():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "fail", "c1", end="failure")
    check(log, "X1", "chkA", "crit1", "pass", "c2")
    assert label(log, "X1") == "held"
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "fail", "c1", termination="unknown")
    assert label(log, "X1") == "held"
    expect(Admission, check, log, "X1", "chkA", "crit1", "pass", "c2")
    log.append("decision", "human", action="abandon", attempt="c1")
    assert label(log, "X1") == "held"
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    admit(log, log.head, "c1", "__check__", cost=0.0, check=("chkA", "crit1", "X1"))
    check(log, "X1", "chkA", "crit1", "pass", "c2")
    assert not accepted(log, "X1")


def t19_result_whitelist_and_na():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    for bad in ("FAIL", "error", "", "Fail"):
        expect(Rejected, log.append, "check_result", "B", target="X1", check="chkA", criteria="crit1",
               result=bad, check_attempt="c1")
    check(log, "X1", "chkA", "crit1", "not-applicable", "c1")
    assert label(log, "X1") == "held"
    log = new_log(base_steps(na_allowed=C1))
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "not-applicable", "c1")
    assert accepted(log, "X1")


def t20_pin_must_be_ok_and_exist():
    steps = base_steps()
    steps["raw"] = StepSpec(program="pRaw", checked=True, required=frozenset({("chkR", "k")}))
    log = new_log(steps)
    run(log, "a1", "raw", "R1")
    check(log, "R1", "chkR", "k", "fail", "c0")
    cf = recontract(log, raw=StepSpec(program="pRaw", checked=True, required=frozenset({("chkR", "k")}), pin="R1"))
    approve(log, cf)
    run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    assert not accepted(log, "X1") and label(log, "X1") == "blocked_upstream"
    expect(Rejected, recontract, log, raw=StepSpec(program="pRaw", pin="ZZZ"))


def t21_freeze_per_sample_and_single_use():
    log = new_log(t3c_steps(), target="T3C", samples={"S1": "confirmation", "S2": "confirmation"})
    log.append("freeze", "agent", step="reco", samples=("S1",), required=C1)
    log.append("exposure", "agent", sample="S2")
    log.append("freeze", "agent", step="reco", samples=("S1", "S2"), required=C1)
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1", sample="S2")
    assert not accepted(log, "X1")
    log = new_log(t3c_steps(allow_rerun=True), target="T3C", samples={"S": "confirmation", "T": "confirmation"})
    log.append("freeze", "agent", step="reco", samples=("S", "T"), required=C1)
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "fail", "c1", sample="S")
    recontract(log, reco=reco_spec(program="pReco_fix", allow_rerun=True))
    run(log, "a3", "reco", "X2")
    check(log, "X2", "chkA", "crit1", "pass", "c2", sample="S")
    assert not accepted(log, "X2")
    check(log, "X2", "chkA", "crit1", "pass", "c3", sample="T")
    assert not accepted(log, "X2")
    log3 = new_log(t3c_steps(allow_rerun=True), target="T3C", samples={"S": "confirmation", "T": "confirmation"})
    log3.append("freeze", "agent", step="reco", samples=("S", "T"), required=C1)
    run(log3, "a1", "raw", "R1"); run(log3, "a2", "reco", "X1")
    check(log3, "X1", "chkA", "crit1", "fail", "c1", sample="S")
    expect(Admission, run, log3, "a3", "reco", "X2")          # v11.1: no rerun after a same-identity failure
    recontract(log3, reco=reco_spec(program="pReco_fix", allow_rerun=True))
    run(log3, "a4", "reco", "X2")
    check(log3, "X2", "chkA", "crit1", "pass", "c3", sample="T")
    assert accepted(log3, "X2")
    assert ("reco", "X1", "chkA", "crit1", "fail") in report_status(log3, "D")["prior_failures"]


def t22_identity_continuation_is_a_human_decision():
    # replaces v10's impact-upper-bound exemption: only a human can approve, and only for the named artifact and the named pair of identities
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    old_id = intent_of(log, "a2").get("identity")
    recontract(log, reco=reco_spec(program="pReco_v2"))
    assert label(log, "X1") == "invalidated"
    new_id = expected_identity(log, "reco", {"raw": "R1"})
    expect(Rejected, log.append, "decision", "agent", action="accept_identity", digest="X1", step="reco",
           old_identity=old_id, new_identity=new_id)
    log.append("decision", "human", action="accept_identity", digest="X1", step="reco",
               old_identity=old_id, new_identity=new_id)
    assert accepted(log, "X1")
    recontract(log, reco=reco_spec(program="pReco_v3"))
    assert label(log, "X1") == "invalidated"


def t23_upstream_list_change_is_stale():
    log = new_log({**base_steps(), "calib": StepSpec(program="pCal")})
    run(log, "a1", "raw", "R1"); run(log, "k1", "calib", "K1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    recontract(log, reco=reco_spec(upstream=("raw", "calib")))
    assert label(log, "X1") == "invalidated"


def t24_multi_producer_same_digest():
    log = new_log({**base_steps(), "raw": StepSpec(program="pRaw", allow_rerun=True)})
    admit(log, log.head, "a1", "raw")
    log.append("receipt", "B", attempt="a1", end="success", termination="unknown", outputs=())
    log.append("decision", "human", action="abandon", attempt="a1")
    run(log, "a2", "raw", "R1")
    assert usable(log, "R1") and label(log, "R1") == "ok"
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    recontract(log, raw=StepSpec(program="pRaw_refactor"))
    assert label(log, "X1") == "invalidated"
    run(log, "a3", "raw", "R1")
    # r6: a refactor reproducing the step's only output is no choice among outputs, so it binds (cf. t88, t91)
    assert label(log, "R1") == "ok" and accepted(log, "X1")


def t25_abandoned_reconcile_moves_to_used():
    log = new_log(base_steps(), budget=2.0)
    admit(log, log.head, "a1", "raw")
    log.append("receipt", "B", attempt="a1", end="success", termination="unknown", outputs=())
    log.append("decision", "human", action="abandon", attempt="a1")
    log.append("reconcile", "B", attempt="a1", end="success", termination="unknown", outputs=())
    assert in_flight(log) == 1.0
    log.append("reconcile", "B", attempt="a1", end="success", termination="confirmed", outputs=("R0",))
    assert in_flight(log) == 0.0 and used(log) == 1.0
    admit(log, log.head, "b1", "raw")
    expect(Admission, admit, log, log.head, "b2", "raw")


def t26_check_provenance():
    log = new_log({**base_steps(), "other": StepSpec(program="pO")})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1"); run(log, "o1", "other", "O1")
    log.append("check_result", "B", target="X1", check="chkA", criteria="crit1", result="pass", check_attempt="o1")
    assert not accepted(log, "X1")
    expect(Rejected, log.append, "check_result", "agent", target="X1", check="chkA", criteria="crit1",
           result="pass", check_attempt="o1")


def t27_adapter_receipt_needs_a_c_admitted_intent():
    log = new_log(base_steps())
    log.append("receipt", "adapter", attempt="ext1", end="success", termination="confirmed", outputs=("R9",))
    assert label(log, "R9") == "not_usable"
    expect(Rejected, log.append, "intent", "adapter", attempt="ext2", step="raw", identity="x", inputs=(), cost=0.0)
    admit(log, log.head, "ext3", "raw", cost=0.0)
    log.append("receipt", "adapter", attempt="ext3", end="success", termination="confirmed", outputs=("R10",))
    assert label(log, "R10") == "ok"


def _chain(depth):
    steps, prev = {}, None
    for i in range(depth):
        steps[f"s{i}"] = StepSpec(program=f"p{i}", upstream=(prev,) if prev else (), checked=True,
                                 required=C1, allow_rerun=True)
        prev = f"s{i}"
    log = new_log(steps, deliverables={"D": Deliverable(f"s{depth-1}", "T2")})
    for i in range(depth):
        for j in range(3):
            d = run(log, f"a{i}_{j}", f"s{i}", f"D{i}_{j}")
            check(log, d, "chkA", "crit1", "pass", f"c{i}_{j}")   # v12.1: every copy is checked before the next
    return log


def t28_scale_linear():
    import time
    times = {}
    for depth in (30, 120):
        log = _chain(depth)
        best = None
        for _ in range(3):
            log._memo.clear()
            t0 = time.perf_counter()
            lb = label(log, f"D{depth-1}_2")
            dt = time.perf_counter() - t0
            best = dt if best is None else min(best, dt)
        assert lb == "ok"
        times[depth] = best
    assert times[120] < 5.0, "derivation too slow"
    assert times[120] / max(times[30], 1e-6) < 9.0, f"derivation not linear: {times}"


def t29_binding_by_fact_order():
    log = new_log({**base_steps(), "raw": StepSpec(program="pRaw", allow_rerun=True)})
    admit(log, log.head, "a1", "raw")
    log.append("receipt", "B", attempt="a1", end="success", termination="unknown", outputs=())
    log.append("reconcile", "B", attempt="a1", end="success", termination="confirmed", outputs=("R_old",))
    run(log, "a2", "raw", "R_new")
    assert bound(log, "raw") == "R_new"


def t30_three_layer_staleness():
    steps = {"raw": StepSpec(program="pRaw"), "mid": StepSpec(program="pMid", upstream=("raw",)),
             "reco": StepSpec(program="pReco", upstream=("mid",), checked=True, required=C1)}
    log = new_log(steps)
    run(log, "a1", "raw", "R1"); run(log, "a2", "mid", "M1"); run(log, "a3", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    recontract(log, raw=StepSpec(program="pRaw2"))
    assert label(log, "M1") == "invalidated" and label(log, "X1") == "invalidated"


def t31_exec_whitelist_and_ids():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1", end="failure")
    log.append("reconcile", "B", attempt="a1", end="success", termination="confirmed", outputs=("R1",))
    assert exec_status(log, "a1") == "failed"
    expect(Rejected, log.append, "receipt", "B", attempt="a1", end="oom_killed", termination="confirmed")
    expect(Rejected, log.append, "intent", "C", attempt="a1", step="raw", identity="x", inputs=(), cost=0)


def t32_admission_rules():
    expect(Rejected, new_log, {"a": StepSpec(program="p", upstream=("b",)), "b": StepSpec(program="q", upstream=("a",))},
           deliverables={})
    log = new_log(base_steps(), samples={"SR": "blinded"})
    expect(Admission, admit, log, log.head, "x", "reco")
    assert exec_status(log, "x") == "rejected"
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    expect(Admission, check, log, "X1", "chkA", "crit1", "pass", "c1", sample="SR")
    log.append("decision", "human", action="unblind", sample="SR")
    check(log, "X1", "chkA", "crit1", "pass", "c2", sample="SR")
    assert any(e.get("sample") == "SR" for e in log.of("exposure"))


def t33_publish_cas_and_version():
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    h0 = log.head
    p = publish(log, h0, "D")
    assert p.get("derivation") == DERIVATION_VERSION and (p.get("deliverable"), p.get("digest")) == ("D", "X1")
    expect(StaleWrite, publish, log, h0, "D")


def t34_waiting_not_stale_when_newer_pending():
    steps = base_steps()
    steps["raw"] = StepSpec(program="pRaw", checked=True, required=frozenset({("chkR", "k")}), allow_rerun=True)
    log = new_log(steps)
    run(log, "a1", "raw", "R1"); check(log, "R1", "chkR", "k", "pass", "c0"); run(log, "a2", "raw", "R2")
    # v12.1: R1 is checked before R2 is computed; a tightening (one more required check) leaves raw with no bound version
    recontract(log, raw=replace(steps["raw"], required=frozenset({("chkR", "k"), ("chkR2", "k")})))
    run(log, "a3", "reco", "X2")
    assert inputs_of(intent_of(log, "a3")) == {"raw": "R2"}
    check(log, "X2", "chkA", "crit1", "pass", "c1")
    check(log, "R1", "chkR2", "k", "pass", "c0b")
    assert bound(log, "raw") == "R1" and label(log, "X2") == "blocked_upstream"
    check(log, "R2", "chkR", "k", "pass", "c2"); check(log, "R2", "chkR2", "k", "pass", "c2b")
    assert bound(log, "raw") == "R2" and accepted(log, "X2")


def t35_writer_restrictions():
    log = new_log(base_steps())
    for kind, writer in [("receipt", "agent"), ("check_result", "agent"), ("decision", "agent"),
                         ("contract", "B"), ("publish", "agent"), ("intent", "agent"), ("intent", "adapter")]:
        expect(Rejected, log.append, kind, writer, attempt="z", end="success", termination="confirmed",
               result="pass", spec={}, action="abandon", step="raw", identity="i", inputs=(), cost=0)
    expect(Rejected, log.append, "decision", "human", action="downgrade")


def t36_random_invariants():
    import random
    rnd = random.Random(20261029)
    labels = {"iteration_internal", "superseded_by_iteration", "not_usable", "invalidated", "producer_conflict",
              "blocked_upstream", "held", "unchecked", "superseded", "overtaken", "ok"}
    for trial in range(250):
        tgt = rnd.choice(["T2", "T3C"])
        steps = base_steps(allow_rerun=True, na_allowed=C1 if rnd.random() < .3 else frozenset())
        steps["raw"] = StepSpec(program="pRaw", checked=rnd.random() < .5, required=frozenset({("chkR", "k")}),
                                allow_rerun=True)
        log = new_log(steps, target=tgt, samples={"S": "confirmation", "T": "confirmation"})
        first_required = steps["reco"].required
        n = 0
        for _ in range(rnd.randint(4, 14)):
            n += 1
            a = rnd.random()
            try:
                if a < .3:
                    run(log, f"a{n}", rnd.choice(["raw", "reco"]), f"D{n}",
                        end=rnd.choice(["success", "success", "failure", "timeout"]),
                        termination=rnd.choice(["confirmed", "confirmed", "unknown"]))
                elif a < .6:
                    outs = candidates_raw(log, "raw") + candidates_raw(log, "reco")
                    if outs:
                        tg = rnd.choice(outs)
                        st = step_of(log, tg) or "reco"
                        pair = ("chkR", "k") if st == "raw" else ("chkA", "crit1")
                        check(log, tg, *pair, rnd.choice(["pass", "pass", "fail", "inconclusive", "not-applicable"]),
                              f"c{n}", sample=rnd.choice([None, "S", "T"]),
                              termination=rnd.choice(["confirmed", "confirmed", "unknown"]))
                elif a < .7:
                    log.append("freeze", "agent", step="reco", samples=tuple(rnd.sample(["S", "T"], rnd.randint(1, 2))),
                               required=spec_of(log, "reco").required)
                elif a < .8:
                    cf = recontract(log, reco=replace(spec_of(log, "reco"),
                                                      required=rnd.choice([C1, frozenset({("chkA", "x")}),
                                                                           C1 | {("chkA", "x")}])),
                                    deliverables={"D": Deliverable("reco", rnd.choice(["T2", "T3C"]))})
                    if rnd.random() < .2:
                        approve(log, cf)
                elif a < .9:
                    outs = candidates_raw(log, "reco")
                    if outs:
                        admit(log, log.head, f"r{n}", "reco", cost=0.0, reuse_source=rnd.choice(outs + ["NOPE"]))
                else:
                    for f in log.of("intent"):
                        if exec_status(log, f.get("attempt")) == "unknown":
                            if rnd.random() < .5:
                                log.append("decision", "human", action="abandon", attempt=f.get("attempt"))
                            else:
                                log.append("reconcile", "B", attempt=f.get("attempt"), end="success",
                                           termination="confirmed", outputs=(f"D{n}r",))
                            break
            except (Admission, Rejected):
                pass
        approvals = bool(log.of("decision")) and any(d.get("action") == "approve_contract" for d in log.of("decision"))
        if not approvals:
            assert spec_of(log, "reco").required >= first_required      # without approval, requirements only grow, never shrink
        for d in candidates_raw(log, "raw") + candidates_raw(log, "reco"):
            assert label(log, d) in labels, label(log, d)
            if accepted(log, d):
                s = spec_of(log, step_of(log, d))
                for pair in s.required:
                    rs = [r for r in log.results_for(d) if (r.get("check"), r.get("criteria")) == pair]
                    assert rs and not any(r.get("result") in ("fail", "inconclusive") for r in rs)
                    assert any(valid_check_attempt(log, r, d, *pair) for r in rs)
                _, it = best_producer(log, d)
                for u, ud in inputs_of(it).items():
                    assert ud == bound(log, u) and ok(log, ud)
                dd = contract(log)["deliverables"]["D"]
                if dd.target == "T3C":
                    assert freeze_ok(log, d, dd.confirmation_required, dd.independent_confirmation)
        snap = {x: label(log, x) for x in candidates_raw(log, "reco")}
        log._memo.clear()
        assert snap == {x: label(log, x) for x in candidates_raw(log, "reco")}


def t37_schema_is_closed_and_checked_steps_need_checks():
    expect(Rejected, new_log, base_steps(required=frozenset()))
    log = new_log(base_steps())
    good = contract(log)
    for bad in ({**good, "alternatives": {}}, {k: v for k, v in good.items() if k != "budget"},
                {**good, "budget": float("nan")}, {**good, "budget": float("inf")}, {**good, "budget": -1},
                {**good, "samples": {"S": "holdout-ish"}}, {**good, "deliverables": {"D": Deliverable("nope", "T2")}},
                {**good, "deliverables": {"D": Deliverable("reco", "T4")}}):
        expect(Rejected, log.append, "contract", "agent", spec=bad)


# ================================================================ counterexamples from S0 and the S0 rerun (excluded by design in v11)

def t38_check_replacement_cannot_be_self_authorized():
    # S0 O1 F1: citing any computed attempt cannot authorize a replacement
    log = new_log(base_steps(required=frozenset({("A", "a"), ("B", "b")})))
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "A", "a", "fail", "c1"); check(log, "X1", "B", "b", "pass", "c2")
    cf = recontract(log, reco=reco_spec(required=frozenset({("B", "b")})))
    assert contract_status(log, cf) == "pending_approval" and label(log, "X1") == "held"


def t39_unknown_contract_fields_are_rejected():
    # S0 O1 F2: there is no “alternative check” field; any new field is rejected
    log = new_log(base_steps())
    expect(Rejected, log.append, "contract", "agent", spec={**contract(log), "alternatives": {"reco": {("T", "t")}}})


def t40_new_step_cannot_take_over_an_artifact():
    # S0 O1 F3
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "fail", "c1")
    recontract(log, reco2=StepSpec(program="pReco", upstream=("raw",), checked=True, required=frozenset({("T", "t")})))
    run(log, "a3", "reco2", "X1")
    assert label(log, "X1") == "producer_conflict" and not accepted(log, "X1")
    expect(Admission, check, log, "X1", "T", "t", "pass", "c2")     # an artifact in conflict cannot be checked
    log.append("decision", "human", action="assign_producer", digest="X1", step="reco")
    assert step_of(log, "X1") == "reco" and label(log, "X1") == "held"


def t41_identity_continuation_cannot_be_obtained_by_cosmetic_changes():
    # S0 O1 F4, S0 rerun N1 F3, FX1 F1: there is no agent-writable exemption; redefining criteria is therefore moot
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "inconclusive", "c1")
    for prog in ("pReco_v2", "pReco_v2b", "pReco_v2c"):
        recontract(log, reco=reco_spec(program=prog))
        assert label(log, "X1") == "invalidated"
    old_id = intent_of(log, "a2").get("identity")
    log.append("decision", "human", action="accept_identity", digest="X1", step="reco", old_identity=old_id,
               new_identity=expected_identity(log, "reco", {"raw": "R1"}))
    check(log, "X1", "chkA", "crit1", "pass", "c2")
    assert label(log, "X1") == "held"                       # the earlier inconclusive still counts


def t42_freeze_role_and_exposure():
    # S0 O1 F5
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation", "TR": "training"})
    expect(Rejected, log.append, "freeze", "agent", step="reco", samples=("TR",), required=C1)
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation"})
    run(log, "a1", "raw", "R1")
    log.append("freeze", "agent", step="reco", samples=("S",), required=C1)
    recontract(log, tune=StepSpec(program="pTune", upstream=("raw",)))
    expect(Admission, admit, log, log.head, "t1", "tune", reads=("S",))
    log.append("exposure", "agent", sample="S")
    run(log, "a2", "reco", "X2")
    check(log, "X2", "chkA", "crit1", "pass", "c2", sample="S")
    assert deliverable_status(log, "D")["achieved"] == "T3E" and not accepted(log, "X2")


def t43_sample_roles_change_only_with_approval():
    # S0 O1 F6, O2 F2
    log = new_log(base_steps(), samples={"SR": "blinded"})
    recontract(log, samples={"SR": "control"})
    assert sample_role(log, "SR") == "blinded"
    expect(Admission, admit, log, log.head, "b1", "raw", reads=("SR",))
    cf = recontract(log, samples={"SR": "control"})
    approve(log, cf)
    assert sample_role(log, "SR") == "control"


def t44_no_downgrade_path_target_stays():
    # S0 O1 F7, S0 rerun N1 F2, N2 F3, FX1 F2: there is no downgrade mechanism; a looser contract written early stays pending approval forever
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation"})
    dormant = recontract(log, deliverables={"D": Deliverable("reco", "T3C", confirmation_required=False)})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    log.append("freeze", "agent", step="reco", samples=("S",), required=C1)
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    assert contract_status(log, dormant) == "pending_approval"
    st = deliverable_status(log, "D")
    assert st["target"] == "T3C" and st["achieved"] == "T3E" and not st["met"]
    # declaring already in the first contract that confirmation is not required is allowed only when the claim type needs no
    # independent confirmation (Methods §2.1; not when confirmation is judged infeasible at freeze, which leaves the field yes), and the report shows it
    log = new_log(t3c_steps(), deliverables={"D": Deliverable("reco", "T3C", confirmation_required=False)})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    log.append("freeze", "agent", step="reco", samples=(), required=C1)
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    assert deliverable_status(log, "D")["met"] and not contract(log)["deliverables"]["D"].confirmation_required


def t45_reuse_source_is_checked():
    # S0 O1 F8 (reuse needs an intent), S0 rerun N1 F1 (reuse source)
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    log.append("reuse", "C", attempt="r0", source="X1")
    assert exec_status(log, "r0") == "planned"
    expect(Admission, admit, log, log.head, "r1", "reco", cost=0.0, reuse_source="NEVER")
    expect(Admission, admit, log, log.head, "r2", "reco", cost=0.0, reuse_source="R1")      # a different step
    recontract(log, reco=reco_spec(program="pReco_v2"))
    expect(Admission, admit, log, log.head, "r3", "reco", cost=0.0, reuse_source="X1")      # different identity
    log2 = new_log(base_steps())
    run(log2, "a1", "raw", "R1", observed_exceeds_declared=True)
    expect(Admission, admit, log2, log2.head, "r4", "raw", cost=0.0, reuse_source="R1")    # not usable


def t46_single_terminal_fact_and_check_provenance():
    # S0 O1 F9
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1")
    log.append("reconcile", "B", attempt="a1", end="success", termination="confirmed", outputs=("Xf",))
    log.append("receipt", "B", attempt="a1", end="success", termination="confirmed", outputs=("Xg",))
    assert not usable(log, "Xf") and not usable(log, "Xg")
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    admit(log, log.head, "c1", "__check__", cost=0.0, check=("chkA", "crit1", "X1"))
    log.append("receipt", "B", attempt="c1", end="success", termination="confirmed", outputs=(),
               observed_exceeds_declared=True)
    log.append("check_result", "B", target="X1", check="chkA", criteria="crit1", result="pass", check_attempt="c1")
    assert label(log, "X1") == "unchecked"
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation"})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    log.append("freeze", "agent", step="reco", samples=("S",), required=C1)
    admit(log, log.head, "c1", "__check__", cost=0.0, check=("chkA", "crit1", "X1"))
    log.append("receipt", "B", attempt="c1", end="success", termination="confirmed", outputs=())
    log.append("check_result", "B", target="X1", check="chkA", criteria="crit1", result="pass",
               check_attempt="c1", sample="S")
    assert deliverable_status(log, "D")["achieved"] == "T3E"


def t47_budget_raise_and_invalid_values():
    # S0 O2 F7, FX1 F3
    log = new_log(base_steps(), budget=1.0)
    run(log, "a1", "raw", "R1")
    for b in (10.0, None):
        recontract(log, budget=b)
        assert contract(log)["budget"] == 1.0
    expect(Rejected, recontract, log, budget=float("nan"))
    expect(Admission, admit, log, log.head, "a2", "reco")
    expect(Admission, admit, log, log.head, "a3", "reco", cost=float("nan"))
    cf = recontract(log, budget=10.0)
    approve(log, cf)
    admit(log, log.head, "a4", "reco")


def t48_intermediate_round_not_consumed_outside_family():
    steps = iteration_steps()
    steps["side"] = StepSpec(program="pSide", upstream=("al2",))
    log = new_log(steps, families=ALIGN)
    run(log, "i1", "al1", "A1"); run(log, "i2", "al2", "A2"); run(log, "s1", "side", "SD")
    assert label(log, "SD") == "invalidated" and not ok(log, "SD")


def t49_invalidated_before_iteration_labels():
    log = new_log(iteration_steps(), families=ALIGN)
    run(log, "i1", "al1", "A1"); run(log, "i2", "al2", "A2")
    recontract(log, al1=StepSpec(program="pAl_v2", family="align", round=1))
    assert label(log, "A1") == "invalidated" and label(log, "A2") == "invalidated"


def t50_final_round_is_checked_and_fixed():
    # S0 rerun N4 F2, F3
    steps = iteration_steps()
    steps["al3"] = StepSpec(program="pAl", upstream=("al2",), family="align", round=3)
    expect(Rejected, new_log, steps, families=ALIGN)
    log = new_log(iteration_steps(), families=ALIGN)
    for a, s, o in [("i1", "al1", "A1"), ("i2", "al2", "A2"), ("i3", "al3", "A3")]:
        run(log, a, s, o)
    check(log, "A3", "converged", "c", "fail", "k1")
    steps2 = {k: v for k, v in iteration_steps().items() if k != "al3"}
    steps2["al2"] = StepSpec(program="pAl", upstream=("al1",), family="align", round=2, checked=True,
                             required=frozenset({("converged", "c"), ("weak_mode", "w")}))
    steps2["reco"] = StepSpec(program="pReco", upstream=("al2",), checked=True, required=C1)
    c = contract(log)
    cf = log.append("contract", "agent", spec={**c, "steps": steps2, "families": {
        "align": Family(final_round=2, convergence_check="converged", mode_check="weak_mode")}})
    assert contract_status(log, cf) == "pending_approval"
    assert contract(log)["families"]["align"].final_round == 3
    al4 = StepSpec(program="pAl", upstream=("al3",), family="align", round=4, checked=True,
                   required=frozenset({("converged", "c"), ("weak_mode", "w")}))
    cf4 = recontract(log, al4=al4, al3=StepSpec(program="pAl", upstream=("al2",), family="align", round=3),
                     families={"align": Family(final_round=4, convergence_check="converged", mode_check="weak_mode")})
    assert contract_status(log, cf4) == "pending_approval"   # adding a round also needs human approval


def t51_deliverables_cannot_be_remapped_or_replaced():
    # S0 rerun N1 F5
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "fail", "c1")
    recontract(log, reco_lax=StepSpec(program="pLax", upstream=("raw",), checked=True, required=frozenset({("T", "t")})),
               deliverables={"D": Deliverable("reco_lax", "T2")})
    assert contract(log)["deliverables"]["D"].step == "reco"
    recontract(log, reco_lax=StepSpec(program="pLax", upstream=("raw",), checked=True, required=frozenset({("T", "t")})),
               deliverables={"D": Deliverable("reco", "T2"), "D_extra": Deliverable("reco_lax", "T2")})
    run(log, "a3", "reco_lax", "XL")
    check(log, "XL", "T", "t", "pass", "c2")
    assert deliverable_status(log, "D_extra")["met"] and not deliverable_status(log, "D")["met"]


def t52_identity_is_computed_by_c():
    # S0 rerun N1 F4
    import inspect
    assert "identity" not in inspect.signature(admit).parameters
    log = new_log(base_steps())
    expect(Admission, admit, log, log.head, "c0", "__check__", cost=0.0, check=("chkA", "crit1", "NOPE"))
    expect(Admission, admit, log, log.head, "c1", "raw", check=("chkA", "crit1", "R1"))


def t53_two_required_checks_on_one_confirmation_sample():
    # recommended obligation from S0 rerun N1: two required checks on the same artifact may share a confirmation sample
    req = frozenset({("A", "a"), ("B", "b")})
    log = new_log(t3c_steps(required=req), target="T3C", samples={"S": "confirmation"})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    log.append("freeze", "agent", step="reco", samples=("S",), required=req)
    check(log, "X1", "A", "a", "pass", "c1", sample="S")
    check(log, "X1", "B", "b", "pass", "c2", sample="S")
    assert accepted(log, "X1") and deliverable_status(log, "D")["achieved"] == "T3C"


def t54_family_needs_round():
    # recommended obligation from S0 rerun N1: a family without a round must not crash the derivation
    steps = base_steps()
    steps["raw"] = StepSpec(program="pRaw", family="align")
    expect(Rejected, new_log, steps, families=ALIGN)


def t55_contract_is_all_or_nothing():
    log = new_log(base_steps(), budget=5.0)
    cf = recontract(log, reco=reco_spec(required=C1 | {("extra", "e")}), budget=10.0)
    assert contract_status(log, cf) == "pending_approval"
    assert spec_of(log, "reco").required == C1                # the tightened part does not take effect on its own either
    cf2 = recontract(log, reco=reco_spec(required=C1 | {("extra", "e")}), budget=3.0)
    assert contract_status(log, cf2) == "effective" and contract_status(log, cf) == "lapsed"
    approve(log, cf)                                          # a stale approval has no effect
    assert contract(log)["budget"] == 3.0


def t56_target_and_achieved_are_reported_separately():
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation"})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    st = deliverable_status(log, "D")
    assert (st["target"], st["achieved"], st["met"]) == ("T3C", "T3E", False)
    expect(Admission, publish, log, log.head, "D")


def t57_allow_rerun_cannot_be_switched_on_silently():
    # prevent cherry-picking results by rerunning non-deterministic steps
    log = new_log(base_steps())
    cf = recontract(log, reco=reco_spec(allow_rerun=True))
    assert contract_status(log, cf) == "pending_approval" and not spec_of(log, "reco").allow_rerun


# ================================================================ counterexamples from S0 v11 (fixed in v11.1)

def t58_upstream_cannot_be_dropped_silently():
    # S0v11-N1-F1
    steps = base_steps()
    steps["raw"] = StepSpec(program="pRaw", checked=True, required=frozenset({("chkR", "k")}))
    log = new_log(steps)
    run(log, "a1", "raw", "R1")
    check(log, "R1", "chkR", "k", "fail", "c0")
    cf = recontract(log, reco=reco_spec(upstream=()))
    assert contract_status(log, cf) == "pending_approval" and spec_of(log, "reco").upstream == ("raw",)
    recontract(log, raw2=StepSpec(program="pRaw2"))
    cf2 = recontract(log, reco=reco_spec(upstream=("raw2",)))
    assert contract_status(log, cf2) == "pending_approval"
    cf3 = recontract(log, reco=reco_spec(upstream=("raw", "raw2")))   # only adding an upstream: at least as strict
    assert contract_status(log, cf3) == "effective"


def t59_rounds_unique_and_order_independent():
    # S0v11-N1-F2, S0v11-N4-F2
    twin = StepSpec(program="pTwin", upstream=("al2",), family="align", round=3, checked=True,
                    required=frozenset({("converged", "c"), ("weak_mode", "w")}))
    member = StepSpec(program="pChunk", upstream=("al2",), family="align", round=3)
    for order in ("twin_first", "twin_last"):
        st = iteration_steps()
        st = ({"twin": twin, **st} if order == "twin_first" else {**st, "twin": twin})
        expect(Rejected, new_log, st, families=ALIGN)          # two checked steps in the final round
        st = iteration_steps()
        st = ({"member": member, **st} if order == "twin_first" else {**st, "member": member})
        log = new_log(st, families=ALIGN)                      # v12.1: an unchecked member makes a partitioned round
        assert not intermediate_round(log, "al3") and intermediate_round(log, "member")
    st = iteration_steps()
    st["al4"] = StepSpec(program="pAl", upstream=("al3",), family="align", round=4)
    expect(Rejected, new_log, st, families=ALIGN)              # no rounds beyond the final round
    st = iteration_steps()
    del st["al2"]
    st["al3"] = replace(st["al3"], upstream=("al1",))
    expect(Rejected, new_log, st, families=ALIGN)              # rounds must be consecutive


def t60_fail_binds_to_identity_not_digest():
    # S0v11-N1-F3
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "fail", "c1")
    expect(Admission, run, log, "a3", "reco", "X2")           # same-identity rerun is rejected
    log = new_log(base_steps(allow_rerun=True))
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    run(log, "a3", "reco", "X2")                              # v12.1: X1 is checked before X2 is computed
    check(log, "X2", "chkA", "crit1", "fail", "c2")
    assert label(log, "X1") == "held" and not deliverable_status(log, "D")["met"]


def t61_lower_tier_deliverable_cannot_stand_in():
    # S0v11-N1-F4
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation"})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    cf = recontract(log, deliverables={"D": Deliverable("reco", "T3C"), "D2": Deliverable("reco", "T2", required=False)})
    assert contract_status(log, cf) == "effective"
    assert deliverable_status(log, "D2")["met"] and not accepted(log, "X1")
    expect(Admission, publish, log, log.head, "D")
    p = publish(log, log.head, "D2")
    assert (p.get("deliverable"), p.get("target"), p.get("achieved"), p.get("prior_failures")) == ("D2", "T2", "T2", 0)


def t62_budget_counts_reported_usage():
    # S0v11-N1-F5
    log = new_log(base_steps(), budget=2.0)
    admit(log, log.head, "a1", "raw", cost=0.0)
    log.append("start", "B", attempt="a1")
    log.append("receipt", "B", attempt="a1", end="success", termination="confirmed", outputs=("R1",), usage=5.0)
    assert used(log) == 5.0 and not usable(log, "R1")
    expect(Admission, admit, log, log.head, "a2", "raw", cost=0.0)
    expect(Rejected, log.append, "receipt", "B", attempt="a1", end="success", termination="confirmed",
           outputs=(), usage=float("nan"))


def t63_freeze_format_is_validated():
    # S0v11-N1-F6
    log = Log()
    expect(Rejected, log.append, "freeze", "agent", step="reco", samples=("S",), required=C1)
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation"})
    for bad in (dict(step="reco"), dict(step="reco", samples="S", required=C1),
                dict(step="reco", samples=("S",), required={("chkA", "crit1")}),
                dict(step="reco", samples=("S",), required=C1, note="x")):
        expect(Rejected, log.append, "freeze", "agent", **bad)
    log.append("freeze", "agent", step="reco", samples=("S",), required=C1)
    log.append("freeze", "agent", step="reco", samples=("S",), required=C1, plan="sha256:freeze-doc")
    expect(Rejected, log.append, "freeze", "agent", step="reco", samples=("S",), required=C1, plan=7)


def t64_approval_applies_at_its_position():
    # S0v11-N1-F7
    log = new_log(base_steps())
    cf1 = recontract(log, reco=reco_spec(required=frozenset({("chkA", "loose")})))     # pending
    cf2 = recontract(log, reco=reco_spec(required=frozenset({("chkA", "loose"), ("chkZ", "z")})))  # also pending (against c0)
    approve(log, cf1)
    assert contract_status(log, cf1) == "effective" and contract_status(log, cf2) == "lapsed"
    assert spec_of(log, "reco").required == frozenset({("chkA", "loose")})
    log = new_log(base_steps())
    cf1 = recontract(log, reco=reco_spec(required=frozenset({("chkA", "loose")})))     # pending
    cf2 = recontract(log, reco=reco_spec(required=C1 | {("chkZ", "z")}))               # tightening: takes effect
    approve(log, cf1)                                                                   # already lapsed: no fallback to it
    assert contract_status(log, cf2) == "effective" and ("chkZ", "z") in spec_of(log, "reco").required


def t65_field_types_are_validated():
    # S0v11-N1-F8
    for bad in (reco_spec(allow_rerun="no"), reco_spec(checked=1), reco_spec(required={("chkA", "crit1")}),
                reco_spec(upstream=["raw"]), reco_spec(round=True, family=None), reco_spec(pin=3)):
        expect(Rejected, new_log, {**base_steps(), "reco": bad})
    expect(Rejected, new_log, base_steps(), deliverables={"D": Deliverable("reco", "T2", required="no")})
    expect(Rejected, new_log, {**base_steps(), "__x": StepSpec(program="p")})


def t66_reuse_does_not_rebind():
    # S0v11-N1-F9
    log = new_log(base_steps(allow_rerun=True))
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1"); check(log, "X1", "chkA", "crit1", "pass", "c1")
    run(log, "a3", "reco", "X2"); check(log, "X2", "chkA", "crit1", "pass", "c2")
    assert bound(log, "reco") == "X2"
    admit(log, log.head, "r1", "reco", cost=0.0, reuse_source="X1")
    assert exec_status(log, "r1") == "reused" and bound(log, "reco") == "X2"


def t67_first_contract_waits_for_human_in_m2():
    # S0v11-N2-F8, N5-F9 (DEC-12)
    log = new_log(base_steps(), mode="M2")
    cf = log.of("contract")[0]
    assert contract_status(log, cf) == "pending_approval" and not has_contract(log)
    expect(Admission, admit, log, log.head, "a1", "raw")
    expect(Rejected, log.append, "session", "C", mode="M1")                  # session can only be the first fact
    expect(Rejected, log.append, "session", "agent", mode="M1")
    approve(log, cf)
    run(log, "a1b", "raw", "R1")                                            # v12.1: the rejected id a1 is not reused
    assert has_contract(log) and contract_status(log, cf) == "effective"
    assert not usable(log, "R1")                                            # M2: receipt without usage → not attested
    run(log, "a2", "raw", "R2", usage=0.5)
    assert usable(log, "R2")
    log = new_log(base_steps(), mode="M3")
    c0 = log.of("contract")[0]
    c1 = log.append("contract", "agent", spec=spec(base_steps(), {"D": Deliverable("reco", "T2")}))
    assert not has_contract(log)                                            # the second one does not take effect automatically either
    approve(log, c1)
    assert contract_status(log, c0) == "lapsed"


def t68_family_needs_convergence_and_mode_checks():
    # S0v11-N4-F1
    st = iteration_steps()
    st["al3"] = replace(st["al3"], required=frozenset({("converged", "c")}))
    expect(Rejected, new_log, st, families=ALIGN)
    st = iteration_steps()
    st["al3"] = replace(st["al3"], na_allowed=frozenset({("weak_mode", "w")}))
    expect(Rejected, new_log, st, families=ALIGN)
    expect(Rejected, new_log, iteration_steps(),
           families={"align": Family(final_round=3, convergence_check="converged", mode_check="converged")})


# ================================================================ counterexamples from S0 v11.1 (fixed in v12)

def t69_no_rerun_before_check_without_allow_rerun():
    # S0v11.1-N1-F1: when same-identity reruns are not allowed, another copy cannot be run to pick from, even before the first copy is checked
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    expect(Admission, run, log, "a3", "reco", "X2")
    expect(Admission, run, log, "a4", "raw", "R2")
    log2 = new_log(base_steps())
    run(log2, "a1", "raw", "R1")
    admit(log2, log2.head, "b1", "reco")
    expect(Admission, admit, log2, log2.head, "b2", "reco")          # not allowed either while one is already in flight
    log3 = new_log(base_steps())
    run(log3, "a1", "raw", "R1"); run(log3, "a2", "reco", "X1", end="failure")
    run(log3, "a3", "reco", "X1")                                    # a retry after an execution failure is allowed


def t70_append_is_validated_and_atomic():
    # S0v11.1-N1-F2: a malformed exposure means none of the batch is written, and no derivation cache is left behind
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1")
    assert deliverable_status(log, "D")["met"]
    stricter = {**contract(log), "steps": {**contract(log)["steps"], "reco": reco_spec(required=C1 | {("Z", "z")})}}
    head = log.head
    for bad in ([("contract", "agent", {"spec": stricter}), ("exposure", "agent", {"sample": ["S"]})],
                [("contract", "agent", {"spec": stricter}), ("exposure", "agent", {"sample": "S", "x": 1})],
                [("contract", "agent", {"spec": stricter}), ("exposure", "agent", {"sample": "S", "attempt": 3})]):
        expect(Rejected, log.append_batch, bad, head)
        assert log.head == head and deliverable_status(log, "D")["met"]
    log.append_batch([("contract", "agent", {"spec": stricter}), ("exposure", "agent", {"sample": "S"})], head)
    assert not deliverable_status(log, "D")["met"]
    expect(Admission, publish, log, log.head, "D")


def t71_control_sample_checks_do_not_block_t3c():
    # S0v11.1-N1-F3: the freeze condition constrains only results on confirmation samples
    req = frozenset({("closure", "c"), ("conf", "k")})
    log = new_log(t3c_steps(required=req), target="T3C", samples={"S": "confirmation", "CR": "control"})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    log.append("freeze", "agent", step="reco", samples=("S",), required=req)
    check(log, "X1", "closure", "c", "pass", "c1", sample="CR")
    check(log, "X1", "conf", "k", "pass", "c2", sample="S")
    assert deliverable_status(log, "D")["achieved"] == "T3C"


# ================================================================ counterexamples from S0 v12 (fixed in the v12.1 spec copy)

def t72_added_step_cannot_take_reserved_values():
    # S0v12-N1-F1: values reserved for the first contract or a human cannot come in through a step added later, even after M2 confirmation
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation"}, mode="M2")
    approve(log, log.of("contract")[0])
    run(log, "a1", "raw", "R1")
    dels = {"D": Deliverable("reco", "T3C"), "D2": Deliverable("reco2", "T3C", independent_confirmation=True)}
    for loose in (dict(allow_rerun=True), dict(na_allowed=C1)):
        cf = recontract(log, deliverables=dels, reco2=reco_spec(program="pReco2", **loose))
        assert contract_status(log, cf) == "pending_approval", loose
        assert "reco2" not in contract(log)["steps"]
    cf = recontract(log, deliverables={**dels, "D2": Deliverable("reco2", "T3C", confirmation_required=False,
                                                                 independent_confirmation=True)},
                    reco2=reco_spec(program="pReco2"))
    assert contract_status(log, cf) == "pending_approval"                   # r4: the field is on the deliverable now
    cf = recontract(log, deliverables=dels, reco2=reco_spec(program="pReco2"))
    assert contract_status(log, cf) == "effective"                          # a plain added step is a tightening
    log = new_log(t3c_steps(), target="T3C", samples={"S": "confirmation"})  # M1 log for the execution part
    run(log, "a1", "raw", "R1")
    recontract(log, deliverables={**dels, "D2": Deliverable("reco2", "T3C", confirmation_required=False)},
               reco2=reco_spec(program="pReco2"))
    assert "reco2" not in contract(log)["steps"]
    recontract(log, deliverables=dels, reco2=reco_spec(program="pReco2"))
    run(log, "a2", "reco2", "Y1"); check(log, "Y1", "chkA", "crit1", "pass", "c1")
    assert deliverable_status(log, "D2")["achieved"] == "T3E"                # no confirmation, no T3C
    expect(Admission, publish, log, log.head, "D2")
    log = new_log(iteration_steps(), families=ALIGN)                        # an added step cannot join an existing family
    cf = recontract(log, extra=StepSpec(program="pX", upstream=("al1",), family="align", round=2))
    assert contract_status(log, cf) == "pending_approval"


def t73_check_before_recompute():
    # S0v12-N1-F2: a cosmetic content change gives a new identity, but the earlier artifact must be checked before another draw
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    cf = recontract(log, reco=reco_spec(external=("note-1",)))
    assert contract_status(log, cf) == "effective" and label(log, "X1") == "invalidated"
    expect(Admission, run, log, "a3", "reco", "X2")                         # X1 has no counted result yet
    check(log, "X1", "chkA", "crit1", "fail", "c1")                         # checked (here: failed), so it is on record
    run(log, "a4", "reco", "X2"); check(log, "X2", "chkA", "crit1", "pass", "c2")
    p = publish(log, log.head, "D")
    assert p.get("prior_failures") == 1 and p.get("chain_artifacts") == 3    # R1, X1, X2: both draws of reco are reported
    log = new_log(base_steps())                                             # a check attempt that did not complete does not count
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    recontract(log, reco=reco_spec(external=("note-1",)))
    check(log, "X1", "chkA", "crit1", "pass", "c1", end="failure")
    expect(Admission, run, log, "a3", "reco", "X2")
    log = new_log(base_steps())                                             # an unchecked step may be recomputed freely
    run(log, "a1", "raw", "R1"); recontract(log, raw=StepSpec(program="pRaw", external=("n",)))
    run(log, "a2", "raw", "R2")


def t74_rejected_attempt_id_is_reserved():
    # S0v12-N1-F3: an id that admission rejected cannot be admitted later (its cost would escape the accounts)
    log = new_log(base_steps(), budget=2.0)
    admit(log, log.head, "a0", "raw", cost=1.5)
    expect(Admission, admit, log, log.head, "z", "raw", cost=1.5)            # over budget
    log.append("receipt", "B", attempt="a0", end="failure", termination="confirmed", outputs=())
    expect(Rejected, admit, log, log.head, "z", "raw", cost=0.4)
    assert exec_status(log, "z") == "rejected" and used(log) + in_flight(log) <= 2.0


def partitioned_steps():
    return {
        "raw": StepSpec(program="pRaw"),
        "ck1a": StepSpec(program="pChunk", upstream=("raw",), external=("a",), family="cal", round=1),
        "ck1b": StepSpec(program="pChunk", upstream=("raw",), external=("b",), family="cal", round=1),
        "solve1": StepSpec(program="pSolve", upstream=("ck1a", "ck1b"), family="cal", round=1),
        "ck2a": StepSpec(program="pChunk", upstream=("raw", "solve1"), external=("a",), family="cal", round=2),
        "ck2b": StepSpec(program="pChunk", upstream=("raw", "solve1"), external=("b",), family="cal", round=2),
        "solve2": StepSpec(program="pSolve", upstream=("ck2a", "ck2b"), family="cal", round=2, checked=True,
                           required=frozenset({("conv", "c"), ("mode", "m")})),
        "reco": StepSpec(program="pReco", upstream=("solve2",), checked=True, required=C1),
    }


CAL = {"cal": Family(final_round=2, convergence_check="conv", mode_check="mode")}


def t75_partitioned_round_and_chaining():
    # S0v12-N4-F2, F4: a round may hold several steps (chunks and a global solve); rounds are chained
    log = new_log(partitioned_steps(), families=CAL)
    for a, s, o in [("r", "raw", "R"), ("x1", "ck1a", "K1A"), ("x2", "ck1b", "K1B"), ("s1", "solve1", "S1"),
                    ("x3", "ck2a", "K2A"), ("x4", "ck2b", "K2B"), ("s2", "solve2", "S2")]:
        run(log, a, s, o)
    assert label(log, "K2A") == "iteration_internal" and label(log, "S1") == "superseded_by_iteration"
    check(log, "S2", "conv", "c", "pass", "k1"); check(log, "S2", "mode", "m", "pass", "k2")
    run(log, "r1", "reco", "X1"); check(log, "X1", "chkA", "crit1", "pass", "k3")
    assert accepted(log, "X1")
    st = partitioned_steps()
    st["side"] = StepSpec(program="pSide", upstream=("ck2a",))               # a member of the final round is not a result
    log = new_log(st, families=CAL)
    for a, s, o in [("r", "raw", "R"), ("x1", "ck1a", "K1A"), ("x2", "ck1b", "K1B"), ("s1", "solve1", "S1"),
                    ("x3", "ck2a", "K2A"), ("sd", "side", "SD")]:
        run(log, a, s, o)
    assert label(log, "SD") == "invalidated"
    st = partitioned_steps()
    st["ck2a"] = replace(st["ck2a"], upstream=("raw",))
    st["ck2b"] = replace(st["ck2b"], upstream=("raw",))
    expect(Rejected, new_log, st, families=CAL)                             # round 2 does not consume round 1
    st = iteration_steps()
    st["al3"] = replace(st["al3"], upstream=("al2", "al1"))
    expect(Rejected, new_log, st, families=ALIGN)                           # a round consumes only its own or the previous round


def t76_add_round_after_nonconvergence():
    # S0v12-N4-F3: the human-approved contract that adds a round demotes the old final step; its failure stays in the history
    log = new_log(iteration_steps(), families=ALIGN)
    for a, s, o in [("i1", "al1", "A1"), ("i2", "al2", "A2"), ("i3", "al3", "A3")]:
        run(log, a, s, o)
    check(log, "A3", "converged", "c", "fail", "k1"); check(log, "A3", "weak_mode", "w", "pass", "k2")
    steps = dict(contract(log)["steps"])
    steps["al3"] = StepSpec(program="pAl", upstream=("al2",), family="align", round=3)
    steps["al4"] = StepSpec(program="pAl", upstream=("al3",), family="align", round=4, checked=True,
                            required=frozenset({("converged", "c"), ("weak_mode", "w")}))
    steps["reco"] = StepSpec(program="pReco", upstream=("al4",), checked=True, required=C1)
    cf = log.append("contract", "agent", spec={**contract(log), "steps": steps, "families": {
        "align": Family(final_round=4, convergence_check="converged", mode_check="weak_mode")}})
    assert contract_status(log, cf) == "pending_approval"
    approve(log, cf)
    run(log, "i4", "al4", "A4")
    assert label(log, "A3") == "superseded_by_iteration" and label(log, "A4") == "unchecked"
    check(log, "A4", "converged", "c", "pass", "k3"); check(log, "A4", "weak_mode", "w", "pass", "k4")
    run(log, "r1", "reco", "X1"); check(log, "X1", "chkA", "crit1", "pass", "k5")
    st = report_status(log, "D")
    assert st["met"] and ("al3", "A3", "converged", "c", "fail") in st["prior_failures"]


def t77_family_check_names_change_only_with_approval():
    # S0v12-N4-F5: the family names its checks by check digest; changing them (e.g. after a replaced check) is a family change
    st = iteration_steps()
    st["al3"] = replace(st["al3"], required=st["al3"].required | {("converged2", "c")})
    log = new_log(st, families=ALIGN)
    cf = log.append("contract", "agent", spec={**contract(log), "families": {
        "align": Family(final_round=3, convergence_check="converged2", mode_check="weak_mode")}})
    assert contract_status(log, cf) == "pending_approval"


def t78_failed_draws_are_counted():
    # S0r2-N1-F1: a draw turned into an execution failure, a timeout or an unattested output is still on record
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1")
    for i in range(3):
        run(log, f"f{i}", "reco", f"Z{i}", end="failure")                   # retries after execution failure are allowed
    run(log, "t1", "reco", "Z9", end="timeout")
    admit(log, log.head, "u1", "reco", cost=0.0)
    log.append("receipt", "B", attempt="u1", end="success", termination="confirmed", outputs=("ZU",), usage=0.5)
    assert not usable(log, "ZU")                                            # usage above declared cost: unattested
    run(log, "a2", "reco", "X1"); check(log, "X1", "chkA", "crit1", "pass", "c1")
    st = report_status(log, "D")
    assert st["met"] and len(st["failed_draws"]) == 5
    p = publish(log, log.head, "D")
    assert p.get("failed_draws") == 5 and p.get("prior_failures") == 0


def t79_method_independent_confirmation():
    # S0r2-N5-F1: when the step requires method-independent confirmation, a holdout-only pass does not give T3C
    req = frozenset({("hold", "h"), ("indep", "i")})
    smp = {"H": "confirmation", "I": "confirmation", "CR": "control"}
    log = new_log(t3c_steps(required=req), samples=smp,
                  deliverables={"D": Deliverable("reco", "T3C", independent_confirmation=True)})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    log.append("freeze", "agent", step="reco", samples=("H", "I"), required=req, independent=("I",))
    check(log, "X1", "hold", "h", "pass", "c1", sample="H")
    check(log, "X1", "indep", "i", "pass", "c2", sample="CR")              # method-independent check on a control sample
    assert deliverable_status(log, "D")["achieved"] == "T3E"
    log = new_log(t3c_steps(required=req), samples=smp,
                  deliverables={"D": Deliverable("reco", "T3C", independent_confirmation=True)})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    log.append("freeze", "agent", step="reco", samples=("H", "I"), required=req, independent=("I",))
    check(log, "X1", "hold", "h", "pass", "c1", sample="H")
    check(log, "X1", "indep", "i", "pass", "c2", sample="I")
    assert deliverable_status(log, "D")["achieved"] == "T3C"
    cf = recontract(log, deliverables={"D": Deliverable("reco", "T3C")})
    assert contract_status(log, cf) == "pending_approval"                   # dropping it is a loosening
    expect(Rejected, log.append, "freeze", "agent", step="reco", samples=("H",), required=req, independent=("I",))


def t80_fact_fields_are_validated():
    # S0r2-N1-F3: B, adapter and human facts have fixed fields
    log = new_log(base_steps())
    admit(log, log.head, "a1", "raw")
    for kind, writer, fields in [("receipt", "B", dict(attempt="a1", end="success", termination="bogus", outputs=())),
                               ("check_result", "B", dict(result="pass")),
                               ("decision", "human", dict(action="approve_contract")),
                               ("decision", "human", dict(action="abandon")),
                               ("start", "B", dict())]:
        expect(Rejected, log.append, kind, writer, **fields)


def t81_family_membership_rules():
    # S0r2-N4-F1, F2: every step of round r > 1 consumes round r - 1; only the final step is checked
    st = partitioned_steps()
    st["ck2b"] = replace(st["ck2b"], upstream=("raw",))
    expect(Rejected, new_log, st, families=CAL)                             # a chunk that ignores the previous constants
    st = partitioned_steps()
    st["solve1"] = replace(st["solve1"], checked=True, required=C1)
    expect(Rejected, new_log, st, families=CAL)                             # a checked step before the final round


def t82_independent_label_and_off_chain_history():
    # S0r3-N1-F1: a freeze written after the sample was exposed cannot relabel it as method-independent
    req = frozenset({("hold", "h")})
    log = new_log(t3c_steps(required=req), samples={"H": "confirmation"},
                  deliverables={"D": Deliverable("reco", "T3C", independent_confirmation=True)})
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    log.append("freeze", "agent", step="reco", samples=("H",), required=req)
    check(log, "X1", "hold", "h", "pass", "c1", sample="H")
    assert deliverable_status(log, "D")["achieved"] == "T3E"
    log.append("freeze", "agent", step="reco", samples=("H",), required=req, independent=("H",))
    assert deliverable_status(log, "D")["achieved"] == "T3E"
    expect(Admission, publish, log, log.head, "D")
    # S0r3-N1-F2: failures of the required check on an off-chain shadow step are in the task-wide history and in publish
    log = new_log(base_steps())
    run(log, "a1", "raw", "R1")
    recontract(log, shadow=reco_spec(program="pShadow"))
    for i in range(3):
        recontract(log, shadow=reco_spec(program=f"pShadow{i}"))
        run(log, f"s{i}", "shadow", f"S{i}"); check(log, f"S{i}", "chkA", "crit1", "fail", f"k{i}")
    run(log, "a2", "reco", "X1"); check(log, "X1", "chkA", "crit1", "pass", "c1")
    p = publish(log, log.head, "D")
    assert p.get("prior_failures") == 0 and p.get("task_failures") == 3


# ================================================================ counterexamples from the fourth S0 round (user-approved fixes, r4)

def t83_content_revert_needs_a_human():
    # S0r4-N1-F1: confirm X1 on S1 and X2 on S2, then revert the program to re-bind X1 — that choice needs a human
    smp = {"S1": "confirmation", "S2": "confirmation"}
    log = new_log(t3c_steps(), target="T3C", samples=smp)
    log.append("freeze", "agent", step="reco", samples=("S1", "S2"), required=C1)
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1", sample="S1")
    assert contract_status(log, recontract(log, reco=reco_spec(program="pReco_alt"))) == "effective"
    run(log, "a3", "reco", "X2"); check(log, "X2", "chkA", "crit1", "pass", "c2", sample="S2")
    st = report_status(log, "D")
    assert st["artifact"] == "X2" and len(st["confirmation_results"]) == 2  # both confirmations are on record
    p = publish(log, log.head, "D")
    assert p.get("confirmation_results") == 2 and p.get("chain_artifacts") == 3
    cf = recontract(log, reco=reco_spec(program="pReco"))                   # the revert: r6, X1 is overtaken by X2
    assert label(log, "X1") == "overtaken" and label(log, "X2") == "invalidated" and bound(log, "reco") is None
    expect(Admission, publish, log, log.head, "D")
    approve(log, recontract(log, reco=reco_spec(program="pReco", pin="X1")))  # a human may take X1 back, knowingly
    assert bound(log, "reco") == "X1"
    log = new_log(base_steps())                                             # a revert of an upstream step is caught too
    run(log, "a1", "raw", "R1")
    recontract(log, raw=StepSpec(program="pRaw2")); run(log, "a2", "raw", "R2")
    recontract(log, raw=StepSpec(program="pRaw"))
    assert label(log, "R1") == "overtaken" and bound(log, "raw") is None


def t84_confirmation_fields_belong_to_the_deliverable():
    # S0r4-N1-F2: a deliverable that becomes T3C later takes the reserved values unless a human approves
    log = new_log(t3c_steps(), samples={"S": "confirmation", "CR": "control"}, mode="M2",
                  deliverables={"D": Deliverable("reco", "T2", confirmation_required=False)})
    approve(log, log.of("contract")[0])
    for d2 in (Deliverable("reco", "T3C"), Deliverable("reco", "T3C", confirmation_required=False,
                                                       independent_confirmation=True)):
        cf = recontract(log, deliverables={"D": contract(log)["deliverables"]["D"], "D2": d2})
        assert contract_status(log, cf) == "pending_approval", d2
    cf = recontract(log, deliverables={"D": Deliverable("reco", "T3C", confirmation_required=False)})
    assert contract_status(log, cf) == "pending_approval"                   # raising the target counts as adding T3C
    cf = recontract(log, deliverables={"D": contract(log)["deliverables"]["D"],
                                       "D2": Deliverable("reco", "T3C", independent_confirmation=True)})
    assert contract_status(log, cf) == "effective"
    log.append("freeze", "agent", step="reco", samples=("S",), required=C1)
    for a, s, o in (("a1", "raw", "R1"), ("a2", "reco", "X1")):
        admit(log, log.head, a, s)
        log.append("receipt", "B", attempt=a, end="success", termination="confirmed", outputs=(o,), usage=0.5)
    admit(log, log.head, "c1", "__check__", cost=1.0, reads=("CR",), check=("chkA", "crit1", "X1"))
    log.append("receipt", "B", attempt="c1", end="success", termination="confirmed", outputs=(), usage=0.5)
    log.append("check_result", "B", target="X1", check="chkA", criteria="crit1", result="pass",
               check_attempt="c1", sample="CR")
    assert deliverable_status(log, "D")["met"] and not deliverable_status(log, "D2")["met"]
    assert not accepted(log, "X1")
    expect(Admission, publish, log, log.head, "D2")


def t85_check_inputs_are_resolved_by_c():
    # S0r4-N1-F3: a check's further inputs are declared in the contract, resolved by C and part of its identity
    st = iteration_steps()
    st["al3"] = replace(st["al3"], check_inputs=frozenset({("converged", "al2")}))
    st["ref"] = StepSpec(program="pRef")
    st["reco"] = replace(st["reco"], check_inputs=frozenset({("chkA", "ref")}))
    log = new_log(st, families=ALIGN)
    for a, s, o in (("i1", "al1", "A1"), ("i2", "al2", "A2"), ("i3", "al3", "A3")):
        run(log, a, s, o)
    check(log, "A3", "converged", "c", "pass", "k1"); check(log, "A3", "weak_mode", "w", "pass", "k2")
    it = intent_of(log, "k1")
    assert inputs_of(it) == {"target": "A3", "input:al2": "A2"}             # the version al3 consumed, chosen by C
    assert it.get("identity") == check_identity("converged", "c", "A3", {"input:al2": "A2"}) \
        != check_identity("converged", "c", "A3")
    assert label(log, "A3") == "ok"
    run(log, "r1", "reco", "X1")
    expect(Admission, check, log, "X1", "chkA", "crit1", "pass", "c1")      # ref has no usable version yet
    run(log, "f1", "ref", "F1"); check(log, "X1", "chkA", "crit1", "pass", "c2")
    assert inputs_of(intent_of(log, "c2"))["input:ref"] == "F1" and accepted(log, "X1")
    cf = recontract(log, reco=replace(spec_of(log, "reco"), check_inputs=frozenset()))
    assert contract_status(log, cf) == "pending_approval"                   # the declared inputs change only with a human
    expect(Rejected, new_log, {**st, "reco": replace(st["reco"], check_inputs=frozenset({("chkZ", "ref")}))},
           families=ALIGN)


def t86_agent_exposure_is_not_a_check_attempt():
    # S0r4-N1-F4: an exposure the agent writes is never attributed to a C-admitted check attempt
    req = frozenset({("chkA", "crit1"), ("chkB", "crit2")})
    log = new_log(t3c_steps(required=req), target="T3C", samples={"S": "confirmation"})
    log.append("freeze", "agent", step="reco", samples=("S",), required=req)
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1", sample="S")
    log.append("exposure", "agent", sample="S", attempt="c1")
    check(log, "X1", "chkB", "crit2", "pass", "c2", sample="S")
    assert deliverable_status(log, "D")["achieved"] == "T3E"


def t87_off_chain_artifacts_are_counted():
    # S0r4-N1-F5: unchecked side-step variants are counted in the task-wide history and in publish
    log = new_log(base_steps(), samples={"CR": "control"})
    run(log, "a1", "raw", "R1")
    for i in range(5):
        recontract(log, side=StepSpec(program=f"pVariant{i}", upstream=("raw",)))
        run(log, f"s{i}", "side", f"SV{i}", reads=("CR",))
    run(log, "a2", "reco", "X1"); check(log, "X1", "chkA", "crit1", "pass", "c1", sample="CR")
    assert report_status(log, "D")["task_history"]["artifacts"]["side"] == 5
    p = publish(log, log.head, "D")
    assert p.get("chain_artifacts") == 2 and p.get("task_artifacts") == 7


# ================================================================ counterexamples from the fifth S0 round (user-approved fixes, r5)

def t88_reproduced_digest_needs_a_pin():
    # S0r5-N1-F1: a cosmetic change that reproduces an already-seen digest does not re-bind it without a human
    smp = {"S1": "confirmation", "S2": "confirmation"}
    log = new_log(t3c_steps(), target="T3C", samples=smp)
    log.append("freeze", "agent", step="reco", samples=("S1", "S2"), required=C1)
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1")
    check(log, "X1", "chkA", "crit1", "pass", "c1", sample="S1")
    recontract(log, reco=reco_spec(program="pReco_alt"))
    run(log, "a3", "reco", "X2"); check(log, "X2", "chkA", "crit1", "pass", "c2", sample="S2")
    cf = recontract(log, reco=reco_spec(program="pReco "))                  # cosmetic: a new identity, not a revert
    assert contract_status(log, cf) == "effective" and label(log, "X2") == "invalidated"
    run(log, "a4", "reco", "X1")                                            # reproduces the first, already-seen output
    assert overtaken(log, "X1") and label(log, "X1") == "overtaken" and bound(log, "reco") is None
    assert not deliverable_status(log, "D")["met"]
    expect(Admission, publish, log, log.head, "D")
    cf = recontract(log, reco=reco_spec(program="pReco ", pin="X1"))       # a human may take it, knowingly
    assert contract_status(log, cf) == "pending_approval"
    approve(log, cf)
    assert bound(log, "reco") == "X1" and label(log, "X1") == "ok"
    log = new_log(base_steps())                                             # through an unchecked upstream step
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1"); check(log, "X1", "chkA", "crit1", "pass", "c1")
    recontract(log, raw=StepSpec(program="pRaw2")); run(log, "a3", "raw", "R2")
    run(log, "a4", "reco", "X2"); check(log, "X2", "chkA", "crit1", "pass", "c2")
    recontract(log, raw=StepSpec(program="pRaw "))
    run(log, "a5", "raw", "R1")                                             # reproduces R1
    assert bound(log, "raw") is None and label(log, "X1") == "blocked_upstream" and not accepted(log, "X1")
    log = new_log(base_steps())                                             # a deterministic same-identity copy is not a reproduction
    run(log, "a1", "raw", "R1")
    admit(log, log.head, "r1", "raw", cost=0.0, reuse_source="R1")
    assert not overtaken(log, "R1") and bound(log, "raw") == "R1"


def t89_check_inputs_must_stay_bound():
    # S0r5-N1-F2: a non-upstream check input resolves only to a bound version, and the result counts only while it is bound
    st = base_steps()
    st["ref"] = StepSpec(program="pRef", checked=True, required=frozenset({("refchk", "r")}))
    st["reco"] = replace(st["reco"], check_inputs=frozenset({("chkA", "ref")}))
    log = new_log(st)
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1"); run(log, "f1", "ref", "F1")
    check(log, "F1", "refchk", "r", "fail", "k1")                           # the reference is held
    expect(Admission, check, log, "X1", "chkA", "crit1", "pass", "c1")
    recontract(log, ref=replace(st["ref"], program="pRef2"))
    run(log, "f2", "ref", "F2"); check(log, "F2", "refchk", "r", "pass", "k2")
    check(log, "X1", "chkA", "crit1", "pass", "c2")
    assert inputs_of(intent_of(log, "c2"))["input:ref"] == "F2" and accepted(log, "X1")
    recontract(log, ref=replace(st["ref"], program="pRef3"))                # the reference changes after the check
    run(log, "f3", "ref", "F3"); check(log, "F3", "refchk", "r", "pass", "k3")
    assert label(log, "X1") == "unchecked" and not accepted(log, "X1")      # the result no longer counts
    check(log, "X1", "chkA", "crit1", "pass", "c3")
    assert accepted(log, "X1")
    st2 = dict(st)                                                          # a check input that depends on the target is a cycle
    st2["down"] = StepSpec(program="pDown", upstream=("reco",))
    st2["reco"] = replace(st["reco"], check_inputs=frozenset({("chkA", "down")}))
    expect(Rejected, new_log, st2)


def t90_check_side_effect_is_check_criterion_target():
    # S0r5-N1-F3: while a check attempt of check x criterion x target is unknown, another one is rejected
    st = base_steps()
    st["ref"] = StepSpec(program="pRef")
    st["reco"] = replace(st["reco"], check_inputs=frozenset({("chkA", "ref")}))
    log = new_log(st)
    run(log, "a1", "raw", "R1"); run(log, "a2", "reco", "X1"); run(log, "f1", "ref", "F1")
    check(log, "X1", "chkA", "crit1", "pass", "c1", termination="unknown")
    recontract(log, ref=StepSpec(program="pRef2")); run(log, "f2", "ref", "F2")
    expect(Admission, check, log, "X1", "chkA", "crit1", "pass", "c2")


def t91_overtaken_covers_peeks_and_readded_steps():
    # S0r6-N1-F1: a draw made unattested on purpose and reproduced later is still an output already seen
    smp = {"S1": "confirmation", "S2": "confirmation"}
    log = new_log(t3c_steps(), target="T3C", samples=smp, budget=10.0)
    log.append("freeze", "agent", step="reco", samples=("S1", "S2"), required=C1)
    run(log, "a1", "raw", "R1")
    admit(log, log.head, "a2", "reco", cost=0.0)                            # under-declared cost: unattested peek
    log.append("receipt", "B", attempt="a2", end="success", termination="confirmed", outputs=("X1",), usage=0.5)
    assert not usable(log, "X1")
    recontract(log, reco=reco_spec(program="pReco_alt"))
    run(log, "a3", "reco", "X2"); check(log, "X2", "chkA", "crit1", "pass", "c2", sample="S2")
    recontract(log, reco=reco_spec(program="pReco "))                       # cosmetic
    run(log, "a4", "reco", "X1")                                            # reproduces the peeked output
    check(log, "X1", "chkA", "crit1", "pass", "c1", sample="S1")
    assert label(log, "X1") == "overtaken" and not deliverable_status(log, "D")["met"]
    expect(Admission, publish, log, log.head, "D")
    # S0r6-N1-F2: a step removed with approval and re-added by the agent with an old program, or with a pin
    st = {**base_steps(), "alt": reco_spec(program="pAlt1")}
    dels = {"D": Deliverable("reco", "T2"), "D2": Deliverable("alt", "T2")}
    log = new_log(st, deliverables=dels)
    run(log, "a1", "raw", "R1"); run(log, "b1", "alt", "A1"); check(log, "A1", "chkA", "crit1", "pass", "k1")
    recontract(log, alt=reco_spec(program="pAlt2"))
    run(log, "b2", "alt", "A2"); check(log, "A2", "chkA", "crit1", "pass", "k2")
    steps = {k: v for k, v in contract(log)["steps"].items() if k != "alt"}
    cf = log.append("contract", "agent", spec=spec(steps, {"D": dels["D"]}))
    approve(log, cf)
    cf = log.append("contract", "agent", spec=spec({**steps, "alt": reco_spec(program="pAlt1")}, dels))
    assert contract_status(log, cf) == "effective"
    assert label(log, "A1") == "overtaken" and bound(log, "alt") is None and not deliverable_status(log, "D2")["met"]
    log = new_log(st, deliverables=dels)                                    # re-adding a step name with a pin needs a human
    run(log, "a1", "raw", "R1"); run(log, "b1", "alt", "A1"); check(log, "A1", "chkA", "crit1", "pass", "k1")
    recontract(log, alt=reco_spec(program="pAlt2")); run(log, "b2", "alt", "A2")
    steps = {k: v for k, v in contract(log)["steps"].items() if k != "alt"}
    approve(log, log.append("contract", "agent", spec=spec(steps, {"D": dels["D"]})))
    cf = log.append("contract", "agent", spec=spec({**steps, "alt": reco_spec(program="pAlt1", pin="A1")}, dels))
    assert contract_status(log, cf) == "pending_approval" and "alt" not in contract(log)["steps"]


# ================================================================ mutation tests: every mutation must be caught by some scenario

def _mut_fail_only_from_computed(log, digest):
    _, it = best_producer(log, digest)
    s = spec_of(log, it.get("step"))
    if not s.checked:
        return "ok"
    for chk, crit in s.required:
        rs = [r for r in log.results_for(digest) if (r.get("check"), r.get("criteria")) == (chk, crit)
              and valid_check_attempt(log, r, digest, chk, crit)]
        if any(r.get("result") in ("fail", "inconclusive") for r in rs):
            return "held"
        if not any(r.get("result") in ("pass", "not-applicable") for r in rs):
            return "missing"
    return "ok"


def _mut_newest_producer(log, digest):
    step = owner_step(log, digest)
    if step is None:
        return None
    best = None
    for seq, it in producers(log, digest):
        if it.get("step") != step:
            continue
        exp = expected_identity(log, step, inputs_of(it))
        ok_id = it.get("identity") == exp or identity_accepted(log, digest, step, it.get("identity"), exp)
        if best is None or (ok_id, seq) > best[0]:
            best = ((ok_id, seq), seq, it)
    return None if best is None else best[1:]


MUTATIONS = {
    "fail counts only computed check attempts": ("checks_state", lambda orig: memo(_mut_fail_only_from_computed)),
    "freeze not checked": ("freeze_ok", lambda orig: memo(lambda log, d, *a: True)),
    "upstream ignores current": ("current", lambda orig: (lambda log, d: self_current(log, d))),
    "strictness order not checked": ("contract_at_least_as_strict", lambda orig: (lambda o, n: True)),
    "required checks can be reduced": ("step_at_least_as_strict", lambda orig: (
        lambda o, n: orig(o, replace(n, required=n.required | o.required)))),
    "family final round can change": ("contract_at_least_as_strict", lambda orig: (
        lambda o, n: orig({**o, "families": n["families"]}, n))),
    "sample roles can change": ("contract_at_least_as_strict", lambda orig: (
        lambda o, n: orig({**o, "samples": {}}, n))),
    "budget can be loosened": ("contract_at_least_as_strict", lambda orig: (
        lambda o, n: orig({**o, "budget": None}, n))),
    "deliverables can be repointed": ("contract_at_least_as_strict", lambda orig: (
        lambda o, n: orig({**o, "deliverables": {}}, n))),
    "pin does not require ok": ("bound", lambda orig: memo(lambda log, s: spec_of(log, s).pin or orig.__wrapped__(log, s))),
    "check does not verify identity": ("valid_check_attempt", lambda orig: (
        lambda log, r, t, c, k: exec_status(log, r.get("check_attempt")) == "computed")),
    "multiple steps not treated as a conflict": ("owner_step", lambda orig: memo(lambda log, d: (claiming_steps(log, d) or (None,))[-1])),
    "exposure after freeze not checked": ("result_sample", lambda orig: (lambda log, r: r.get("sample"))),
    "non-final round usable outside the family": ("intermediate_round", lambda orig: (lambda log, step: False)),
    "identity continuation needs no human": ("identity_accepted", lambda orig: (lambda *a: True)),
    "reuse source not checked": ("best_producer", lambda orig: memo(
        lambda log, d: orig.__wrapped__(log, d) or (0, {"step": "reco", "identity": None, "inputs": ()}))),
    "format not validated": ("validate_contract", lambda orig: (lambda log, spec: None)),
    "upstream can be removed": ("step_at_least_as_strict", lambda orig: (lambda o, n: orig(replace(o, upstream=()), n))),
    "fail bound only to the digest": ("identity_failures", lambda orig: (lambda *a: [])),
    "accepted if any one deliverable is met": ("accepted", lambda orig: (lambda log, d: any(
        deliverable_status(log, k)["met"] and deliverable_status(log, k)["artifact"] == d
        for k in contract(log)["deliverables"]))),
    "budget counts only the declared cost": ("charge", lambda orig: (lambda log, it: it.get("cost", 0.0))),
    "usage overrun still attested": ("attested", lambda orig: (lambda log, a: not any(
        r.get("observed_exceeds_declared") for r in log.of_attempt(a) if r.kind in ("receipt", "reconcile")))),
    "same-identity rerun allowed before the check": ("same_identity_ran", lambda orig: (lambda log, st, i: any(
        ok(log, d) for d in candidates_raw(log, st) if best_producer(log, d) and best_producer(log, d)[1].get("identity") == i))),
    "freeze constrains all samples": ("freeze_ok", lambda orig: memo(lambda log, d, *a: orig.__wrapped__(log, d, *a) and not any(
        result_sample(log, r) and sample_role(log, result_sample(log, r)) != "confirmation" for r in log.results_for(d)))),
    "reuse changes the binding": ("best_producer", lambda orig: memo(lambda log, d: _mut_newest_producer(log, d))),
    "added step may take reserved values": ("contract_at_least_as_strict", lambda orig: (
        lambda o, n: orig(o, {**n, "steps": {k: v for k, v in n["steps"].items() if k in o["steps"]}}))),
    "recompute before checking the earlier artifact": ("unchecked_artifacts", lambda orig: (lambda log, step: [])),
    "rejected attempt id reusable": ("attempt_id_taken", lambda orig: (lambda log, a, pending: a in log._intent or any(
        k == "intent" and d.get("attempt") == a for k, _, d in pending))),
    "rounds need not be chained": ("family_chain_problem", lambda orig: (lambda steps, fam, f: None)),
    "failed draws not counted": ("failed_draws", lambda orig: (lambda log, step: [])),
    "method-independent confirmation not checked": ("independent_ok", lambda orig: (lambda log, d, found: True)),
    "fact fields not validated": ("fact_field_problem", lambda orig: (lambda kind, data: None)),
    "independent label from any freeze": ("independent_sample", lambda orig: (lambda log, step, req, smp: any(
        smp in (f.get("independent") or ()) for f in log.of("freeze")))),
    "task-wide history omitted": ("task_history", lambda orig: (lambda log: {"failures": [], "failed_draws": [],
                                                                            "artifacts": {}})),
    "overtaken artifact binds without a human": ("overtaken", lambda orig: memo(lambda log, d: False)),
    "confirmation results not reported": ("confirmation_results", lambda orig: (lambda log, step: [])),
    "added T3C deliverable inherits no": ("contract_at_least_as_strict", lambda orig: (
        lambda o, n: orig(o, {**n, "deliverables": {k: replace(v, confirmation_required=True,
                                                               independent_confirmation=True)
                                                    if k not in o["deliverables"] or o["deliverables"][k].target != "T3C"
                                                    else v for k, v in n["deliverables"].items()}}))),
    "check inputs not resolved by C": ("check_inputs_for", lambda orig: (lambda log, t, c: {})),
    "added step may carry a pin": ("contract_at_least_as_strict", lambda orig: (
        lambda o, n: orig(o, {**n, "steps": {k: (replace(v, pin=None) if k not in o["steps"] else v)
                                             for k, v in n["steps"].items()}}))),
    "check input need not stay bound": ("check_inputs_hold", lambda orig: (lambda log, it, t, c: set(
        k for k in inputs_of(it) if k != "target") == {"input:" + u for u in declared_check_inputs(log, t, c)})),
    "check side effect not recognised across check inputs": ("same_side_effect", lambda orig: (
        lambda f, step, chk: orig(f, step, chk) and set(inputs_of(f)) == {"target"})),
    "agent exposure attributed to a check attempt": ("freeze_ok", lambda orig: memo(
        lambda log, d, *a: orig.__wrapped__(_NoWriterLog(log), d, *a))),
}


class _NoWriterLog:
    """Mutation helper: a view of the log in which every exposure appears to be written by C."""
    def __init__(self, log):
        self._log = log
        self._memo = {}

    def __getattr__(self, k):
        return getattr(self._log, k)

    def of_sample(self, smp):
        return [replace(f, writer="C") if f.kind == "exposure" else f for f in self._log.of_sample(smp)]


def run_tests(tests):
    failed = []
    for t in tests:
        try:
            t()
        except Exception as e:  # noqa: BLE001
            failed.append((t.__name__, f"{type(e).__name__}: {e}"))
    return failed


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("t") and k[1:3].isdigit()]

if __name__ == "__main__":
    fails = run_tests(TESTS)
    for t in TESTS:
        bad = [f for f in fails if f[0] == t.__name__]
        print(("FAIL " + t.__name__ + ": " + bad[0][1]) if bad else ("PASS " + t.__name__))
    print(f"{len(TESTS) - len(fails)}/{len(TESTS)} scenarios passed")
    g = globals()
    survived = []
    for name, (fn, make) in MUTATIONS.items():
        orig = g[fn]
        g[fn] = make(orig)
        killed = bool(run_tests(TESTS))
        g[fn] = orig
        print(("KILLED   " if killed else "SURVIVED ") + name)
        if not killed:
            survived.append(name)
    print(f"{len(MUTATIONS) - len(survived)}/{len(MUTATIONS)} mutations killed")
    raise SystemExit(1 if fails or survived else 0)
