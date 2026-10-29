"""The persistent task record of the control layer: one append-only JSON-lines file with a digest chain and
compare-and-set appends, and the JSON codec of facts and contracts (reconstruction v12 C1; DEC-01, DEC-08, DEC-09
defaults, pending maintainer approval: `hep-research-artifacts/<task>/task-log/task-log.jsonl`, the path given on the
command line; DEC-13: ideas reused from the hep-review store -- operation-id idempotency, head continuity -- but no
shared store). Standard library only.

Line format (every line is the canonical JSON of Control §4: sorted keys, separators ',' ':', non-ASCII kept):
  {"seq": N, "batch": FIRST_SEQ_OF_ITS_APPEND, "kind": KIND, "writer": C|B|adapter|agent|human, "fields": {...},
   "prev": SHA-256 of the previous line's bytes (null for line 0), "op": OPERATION_ID|null,
   "request": SHA-256 of the request|null, "time": UTC ISO-8601}
Every load verifies the whole chain (sequence numbers, previous-line digests, canonical bytes, closed field sets)
and replays every append batch through the derivation's validation, so a record edited by hand is refused -- except
an edit of the last line, which no later line commits to: that one is caught only against a digest kept outside
the record (the expected digest of the next append, or an anchor given to `verify`). An
append holds an exclusive lock on <file>.lock (POSIX flock; the lock only serializes writers), re-reads and verifies
the record, refuses unless the caller's expected head (and, when given, the expected last-line digest) still holds
(compare-and-set, Control §5.5), validates the whole batch before writing anything, and writes the batch with one
O_APPEND write followed by fsync. A crash in the middle of that write leaves a torn last line, which the next load
reports; recovery belongs to C2.
"""
from __future__ import annotations

import contextlib
import datetime
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .derivation import (Admission, Deliverable, Family, Log, Rejected, StaleWrite, StepSpec, canonical_bytes,
                         digest_of)

try:
    import fcntl as posix_lock
except ImportError:  # pragma: no cover - non-POSIX: compare-and-set still holds, writers are not serialized
    posix_lock = None

LINE_KEYS = {"seq", "batch", "kind", "writer", "fields", "prev", "op", "request", "time"}

# ---------------------------------------------------------------- field codec


class Codec:
    """Field kinds of the JSON form; decode() is strict (wrong JSON types and duplicates are refused)."""
    TEXT, INTEGER, NUMBER, FLAG, TEXTS, PAIRS, INPUTS, CONTRACT, RECORD = (
        "text", "integer", "number", "flag", "texts", "pairs", "inputs", "contract", "record")


FIELD_KINDS = {
    "session": {"mode": Codec.TEXT},
    "contract": {"spec": Codec.CONTRACT},
    "freeze": {"step": Codec.TEXT, "samples": Codec.TEXTS, "required": Codec.PAIRS, "plan": Codec.TEXT,
               "independent": Codec.TEXTS},
    "intent": {"attempt": Codec.TEXT, "step": Codec.TEXT, "identity": Codec.TEXT, "inputs": Codec.INPUTS,
               "cost": Codec.NUMBER, "reads": Codec.TEXTS},
    "admission_rejected": {"attempt": Codec.TEXT, "step": Codec.TEXT, "reason": Codec.TEXT},
    "reuse": {"attempt": Codec.TEXT, "source": Codec.TEXT},
    "cancel_request": {"attempt": Codec.TEXT},
    "exposure": {"sample": Codec.TEXT, "attempt": Codec.TEXT},
    "start": {"attempt": Codec.TEXT},
    "receipt": {"attempt": Codec.TEXT, "end": Codec.TEXT, "termination": Codec.TEXT, "outputs": Codec.TEXTS,
                "usage": Codec.NUMBER, "observed_exceeds_declared": Codec.FLAG, "record": Codec.RECORD},
    "reconcile": {"attempt": Codec.TEXT, "end": Codec.TEXT, "termination": Codec.TEXT, "outputs": Codec.TEXTS,
                  "usage": Codec.NUMBER, "observed_exceeds_declared": Codec.FLAG, "record": Codec.RECORD},
    "check_result": {"target": Codec.TEXT, "check": Codec.TEXT, "criteria": Codec.TEXT, "result": Codec.TEXT,
                     "check_attempt": Codec.TEXT, "reason": Codec.TEXT, "sample": Codec.TEXT,
                     "record": Codec.RECORD},
    "decision": {"action": Codec.TEXT, "ref": Codec.INTEGER, "digest": Codec.TEXT, "step": Codec.TEXT,
                 "old_identity": Codec.TEXT, "new_identity": Codec.TEXT, "sample": Codec.TEXT,
                 "attempt": Codec.TEXT, "basis": Codec.TEXT},
    "publish": {"deliverable": Codec.TEXT, "digest": Codec.TEXT, "target": Codec.TEXT, "achieved": Codec.TEXT,
                "prior_failures": Codec.INTEGER, "chain_artifacts": Codec.INTEGER, "failed_draws": Codec.INTEGER,
                "confirmation_results": Codec.INTEGER, "task_failures": Codec.INTEGER,
                "task_artifacts": Codec.INTEGER, "head": Codec.INTEGER, "derivation": Codec.TEXT},
}

# contract JSON names (Control §1.1); a step needs program and environment, every other field has the default shown
STEP_FIELDS = {"program": "program", "environment": "env", "external": "external", "upstream": "upstream",
               "checked": "checked", "required_checks": "required", "na_allowed": "na_allowed",
               "check_inputs": "check_inputs", "family": "family", "round": "round", "rerun_allowed": "allow_rerun",
               "pin": "pin"}
STEP_REQUIRED = ("program", "environment")
DELIVERABLE_FIELDS = {"step": "step", "target": "target", "required": "required",
                      "confirmation_required": "confirmation_required",
                      "independent_confirmation_required": "independent_confirmation"}
DELIVERABLE_REQUIRED = ("step", "target")
FAMILY_FIELDS = {"final_round": "final_round", "convergence_check": "convergence_check", "mode_check": "mode_check"}


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _decode_texts(value, where):
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise Rejected(f"{where} must be a list of strings")
    return tuple(value)


def _decode_pairs(value, where):
    if not isinstance(value, list) or not all(isinstance(p, list) and len(p) == 2 and all(isinstance(x, str) for x in p)
                                              for p in value):
        raise Rejected(f"{where} must be a list of [string, string] pairs")
    pairs = frozenset(tuple(p) for p in value)
    if len(pairs) != len(value):
        raise Rejected(f"{where} lists a pair twice")
    return pairs


def _encode_pairs(value):
    return sorted([list(p) for p in value])


def _decode_scalar(value, kind, where):
    if value is None:
        return None
    if kind == Codec.TEXT and not isinstance(value, str):
        raise Rejected(f"{where} must be a string")
    if kind == Codec.INTEGER and (not isinstance(value, int) or isinstance(value, bool)):
        raise Rejected(f"{where} must be an integer")
    if kind == Codec.NUMBER and not _is_number(value):
        raise Rejected(f"{where} must be a number")
    if kind == Codec.FLAG and not isinstance(value, bool):
        raise Rejected(f"{where} must be true or false")
    return value


def _decode_named(value, names, required, where):
    if not isinstance(value, dict):
        raise Rejected(f"{where} must be an object")
    unknown = sorted(set(value) - set(names))
    if unknown:
        raise Rejected(f"{where}: unknown field(s) {unknown} (closed format, Control §1.1)")
    missing = [key for key in required if key not in value]
    if missing:
        raise Rejected(f"{where}: missing field(s) {missing}")
    return value


def decode_step(value, where) -> StepSpec:
    value = _decode_named(value, STEP_FIELDS, STEP_REQUIRED, where)
    kw = {}
    for key, attr in STEP_FIELDS.items():
        if key not in value:
            continue
        item, at = value[key], f"{where}.{key}"
        if key in ("program", "environment"):
            if not isinstance(item, str):
                raise Rejected(f"{at} must be a string")
        elif key in ("external", "upstream"):
            item = _decode_texts(item, at)
        elif key in ("checked", "rerun_allowed"):
            if not isinstance(item, bool):
                raise Rejected(f"{at} must be true or false")
        elif key in ("required_checks", "na_allowed", "check_inputs"):
            item = _decode_pairs(item, at)
        elif key in ("family", "pin"):
            if item is not None and not isinstance(item, str):
                raise Rejected(f"{at} must be a string or null")
        elif key == "round":
            if item is not None and (not isinstance(item, int) or isinstance(item, bool)):
                raise Rejected(f"{at} must be a positive integer or null")
        kw[attr] = item
    return StepSpec(**kw)


def encode_step(step: StepSpec) -> dict:
    return {"program": step.program, "environment": step.env, "external": list(step.external),
            "upstream": list(step.upstream), "checked": step.checked, "required_checks": _encode_pairs(step.required),
            "na_allowed": _encode_pairs(step.na_allowed), "check_inputs": _encode_pairs(step.check_inputs),
            "family": step.family, "round": step.round, "rerun_allowed": step.allow_rerun, "pin": step.pin}


def decode_deliverable(value, where) -> Deliverable:
    value = _decode_named(value, DELIVERABLE_FIELDS, DELIVERABLE_REQUIRED, where)
    for key in ("step", "target"):
        if not isinstance(value[key], str):
            raise Rejected(f"{where}.{key} must be a string")
    for key in ("required", "confirmation_required", "independent_confirmation_required"):
        if key in value and not isinstance(value[key], bool):
            raise Rejected(f"{where}.{key} must be true or false")
    return Deliverable(**{attr: value[key] for key, attr in DELIVERABLE_FIELDS.items() if key in value})


def encode_deliverable(dl: Deliverable) -> dict:
    return {"step": dl.step, "target": dl.target, "required": dl.required,
            "confirmation_required": dl.confirmation_required,
            "independent_confirmation_required": dl.independent_confirmation}


def decode_family(value, where) -> Family:
    value = _decode_named(value, FAMILY_FIELDS, tuple(FAMILY_FIELDS), where)
    if not isinstance(value["final_round"], int) or isinstance(value["final_round"], bool):
        raise Rejected(f"{where}.final_round must be an integer")
    for key in ("convergence_check", "mode_check"):
        if not isinstance(value[key], str):
            raise Rejected(f"{where}.{key} must be a string (a check digest)")
    return Family(**value)


def decode_contract(value) -> dict:
    """The closed contract format of Control §1.1 in JSON; exactly the five fields."""
    value = _decode_named(value, ("steps", "deliverables", "families", "samples", "budget"),
                          ("steps", "deliverables", "families", "samples", "budget"), "contract")
    for key in ("steps", "deliverables", "families", "samples"):
        if not isinstance(value[key], dict):
            raise Rejected(f"contract.{key} must be an object keyed by name")
    budget = value["budget"]
    if budget is not None and not _is_number(budget):
        raise Rejected("contract.budget must be null or a number")
    for sample, role in value["samples"].items():
        if not isinstance(role, str):
            raise Rejected(f"contract.samples.{sample} must be a role string")
    return {"steps": {name: decode_step(step, f"contract.steps.{name}") for name, step in value["steps"].items()},
            "deliverables": {did: decode_deliverable(dl, f"contract.deliverables.{did}")
                             for did, dl in value["deliverables"].items()},
            "families": {fam: decode_family(fm, f"contract.families.{fam}") for fam, fm in value["families"].items()},
            "samples": dict(value["samples"]), "budget": budget}


def encode_contract(spec: dict) -> dict:
    return {"steps": {name: encode_step(step) for name, step in spec["steps"].items()},
            "deliverables": {did: encode_deliverable(dl) for did, dl in spec["deliverables"].items()},
            "families": {fam: {"final_round": fm.final_round, "convergence_check": fm.convergence_check,
                               "mode_check": fm.mode_check} for fam, fm in spec["families"].items()},
            "samples": dict(spec["samples"]), "budget": spec["budget"]}


def decode_fields(kind: str, value) -> dict:
    """JSON fields of a fact -> the typed fields the derivation uses. Unknown fields are refused."""
    if kind not in FIELD_KINDS:
        raise Rejected(f"unknown fact kind {kind}")
    if not isinstance(value, dict):
        raise Rejected(f"{kind}: fields must be an object")
    kinds = FIELD_KINDS[kind]
    unknown = sorted(set(value) - set(kinds))
    if unknown:
        raise Rejected(f"{kind}: unknown field(s) {unknown}")
    typed = {}
    for key, item in value.items():
        codec, where = kinds[key], f"{kind}.{key}"
        if codec == Codec.TEXTS:
            typed[key] = None if item is None else _decode_texts(item, where)
        elif codec == Codec.PAIRS:
            typed[key] = _decode_pairs(item, where)
        elif codec == Codec.INPUTS:
            if not isinstance(item, dict) or not all(isinstance(x, str) for x in item.values()):
                raise Rejected(f"{where} must be an object of step -> artifact digest")
            typed[key] = tuple(sorted(item.items()))
        elif codec == Codec.CONTRACT:
            typed[key] = decode_contract(item)
        elif codec == Codec.RECORD:
            if not isinstance(item, dict):
                raise Rejected(f"{where} must be an object")
            typed[key] = item
        else:
            typed[key] = _decode_scalar(item, codec, where)
    return typed


def encode_fields(kind: str, fields: dict) -> dict:
    """Typed fields -> JSON. Refuses fields outside the kind's closed set (Rejected)."""
    kinds = FIELD_KINDS.get(kind)
    if kinds is None:
        raise Rejected(f"unknown fact kind {kind}")
    unknown = sorted(set(fields) - set(kinds))
    if unknown:
        raise Rejected(f"{kind}: field(s) {unknown} have no JSON form")
    encoded = {}
    for key, item in fields.items():
        codec = kinds[key]
        if item is None:
            encoded[key] = None
        elif codec == Codec.TEXTS:
            encoded[key] = list(item)
        elif codec == Codec.PAIRS:
            encoded[key] = _encode_pairs(item)
        elif codec == Codec.INPUTS:
            encoded[key] = dict(item)
        elif codec == Codec.CONTRACT:
            encoded[key] = encode_contract(item)
        else:
            encoded[key] = item
    return encoded


# ---------------------------------------------------------------- the record file

class CorruptRecord(Exception):
    """The record does not verify: a broken chain, a non-canonical or torn line, or a fact that does not validate."""


class OperationConflict(Exception):
    """An operation id was used before with another request."""


@dataclass
class Loaded:
    log: Log
    lines: list = field(default_factory=list)       # parsed line objects
    raw: list = field(default_factory=list)         # the bytes of each line (without the newline)

    @property
    def head_digest(self) -> str | None:
        return hashlib.sha256(self.raw[-1]).hexdigest() if self.raw else None


def _no_constants(token):
    raise ValueError(f"{token} is not a JSON number")


def parse_line(raw: bytes, index: int) -> dict:
    try:
        line = json.loads(raw.decode("utf-8"), parse_constant=_no_constants)
    except (UnicodeDecodeError, ValueError) as exc:
        raise CorruptRecord(f"line {index}: not JSON ({exc})") from None
    if not isinstance(line, dict) or set(line) != LINE_KEYS:
        raise CorruptRecord(f"line {index}: a line has exactly the keys {sorted(LINE_KEYS)}")
    if canonical_bytes(line) != raw:
        raise CorruptRecord(f"line {index}: not in canonical form (edited or reformatted)")
    return line


def load_bytes(content: bytes) -> Loaded:
    """Verify a whole record and replay it into a Log."""
    if content and not content.endswith(b"\n"):
        raise CorruptRecord("the last line is torn (no newline at the end of the record)")
    raws = content.split(b"\n")[:-1] if content else []
    loaded = Loaded(Log())
    prev = None
    group: list = []
    for index, raw in enumerate(raws):
        line = parse_line(raw, index)
        if line["seq"] != index:
            raise CorruptRecord(f"line {index}: sequence number {line['seq']!r}, expected {index}")
        if line["prev"] != prev:
            raise CorruptRecord(f"line {index}: previous-line digest does not match (chain broken)")
        for key in ("op", "request"):
            if line[key] is not None and not isinstance(line[key], str):
                raise CorruptRecord(f"line {index}: {key} must be a string or null")
        if not isinstance(line["time"], str) or not isinstance(line["writer"], str):
            raise CorruptRecord(f"line {index}: time and writer are strings")
        try:
            typed = decode_fields(line["kind"], line["fields"])
            if canonical_bytes(encode_fields(line["kind"], typed)) != canonical_bytes(line["fields"]):
                raise Rejected("fields are not in canonical form")
        except Rejected as exc:
            raise CorruptRecord(f"line {index}: {exc}") from None
        if group and line["batch"] != group[0][0]["batch"]:
            _replay(loaded.log, group)
            group = []
        if not group and line["batch"] != index:
            raise CorruptRecord(f"line {index}: batch {line['batch']!r} does not start here")
        group.append((line, typed))
        loaded.lines.append(line)
        loaded.raw.append(raw)
        prev = hashlib.sha256(raw).hexdigest()
    if group:
        _replay(loaded.log, group)
    return loaded


def _replay(log: Log, group):
    try:
        log.append_batch([(line["kind"], line["writer"], typed) for line, typed in group], group[0][0]["batch"])
    except (Rejected, StaleWrite) as exc:
        raise CorruptRecord(f"lines {group[0][0]['seq']}..{group[-1][0]['seq']}: the batch does not validate: "
                            f"{exc}") from None


def encode_lines(log: Log, start: int, prev: str | None, op_id: str | None, request: str | None,
                 when: str | None = None) -> list[bytes]:
    """Canonical lines for log.facts[start:], chained to `prev`."""
    when = when or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    lines = []
    for fact in log.facts[start:]:
        line = {"seq": fact.seq, "batch": log.batch_start[fact.seq], "kind": fact.kind, "writer": fact.writer,
                "fields": encode_fields(fact.kind, fact.fields), "prev": prev, "op": op_id, "request": request,
                "time": when}
        raw = canonical_bytes(line)
        lines.append(raw)
        prev = hashlib.sha256(raw).hexdigest()
    return lines


def dump_log(log: Log) -> bytes:
    """The whole in-memory log as record bytes (used by tests and exports)."""
    return b"".join(raw + b"\n" for raw in encode_lines(log, 0, None, None, None, when="1970-01-01T00:00:00+00:00"))


@dataclass
class Outcome:
    facts: list                      # the facts written by this call (or found, when replayed)
    head: int
    head_digest: str | None
    replayed: bool = False
    refusal: str | None = None       # an admission rejection or an unmet publish


class TaskRecord:
    """One task record file (DEC-01/DEC-08/DEC-09 default location hep-research-artifacts/<task>/task-log/
    task-log.jsonl; pending approval). Facts are appended only through transact()."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")

    def read(self) -> Loaded:
        if not self.path.is_file():
            raise FileNotFoundError(f"no task record at {self.path}")
        return load_bytes(self.path.read_bytes())

    @contextlib.contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "a+b") as handle:
            if posix_lock is not None:
                posix_lock.flock(handle.fileno(), posix_lock.LOCK_EX)
            try:
                yield
            finally:
                if posix_lock is not None:
                    posix_lock.flock(handle.fileno(), posix_lock.LOCK_UN)

    def create(self, mode: str) -> Outcome:
        """Create the record with its session fact (written by C, the first line)."""
        with self._locked():
            if self.path.exists():
                raise FileExistsError(f"a task record already exists at {self.path}")
            log = Log()
            log.append("session", "C", 0, mode=mode)
            lines = encode_lines(log, 0, None, None, None)
            self._write(lines)
            return Outcome(list(log.facts), log.head, hashlib.sha256(lines[-1]).hexdigest())

    def transact(self, operation, expect_head: int, expect_digest: str | None = None, op_id: str | None = None,
                 request: dict | None = None) -> Outcome:
        """Run `operation(log)` on the verified record and append what it wrote, all under the lock.
        Idempotency: a repeated op_id with the same request returns the facts written the first time (replayed);
        with another request it is an OperationConflict. Compare-and-set: StaleWrite unless the record's head (and
        last-line digest, when given) equals what the caller derived from."""
        request_digest = digest_of(request) if request is not None else None
        with self._locked():
            loaded = self.read()
            log = loaded.log
            if op_id is not None:
                earlier = [line for line in loaded.lines if line["op"] == op_id]
                if earlier:
                    if earlier[0]["request"] != request_digest:
                        raise OperationConflict(f"operation {op_id} was used with another request")
                    return Outcome([log.facts[line["seq"]] for line in earlier], log.head, loaded.head_digest,
                                   replayed=True)
            if expect_head != log.head:
                raise StaleWrite(f"expected head {expect_head}, actual {log.head}: re-read, re-derive and retry")
            if expect_digest is not None and expect_digest != loaded.head_digest:
                raise StaleWrite("the last line's digest differs from the expected one: re-read and re-derive")
            start = log.head
            refusal = None
            try:
                operation(log)
            except Admission as exc:
                refusal = str(exc)
            lines = encode_lines(log, start, loaded.head_digest, op_id, request_digest)
            if lines:
                self._write(lines)
            head_digest = hashlib.sha256(lines[-1]).hexdigest() if lines else loaded.head_digest
            return Outcome(log.facts[start:], log.head, head_digest, refusal=refusal)

    def _write(self, lines: list[bytes]):
        payload = b"".join(raw + b"\n" for raw in lines)
        handle = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            view = memoryview(payload)
            while view:
                count = os.write(handle, view)
                view = view[count:]
            os.fsync(handle)
        finally:
            os.close(handle)
