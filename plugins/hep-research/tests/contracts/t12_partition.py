#!/usr/bin/env python3
"""T12 stage 3: partitioning, recovery and boundaries (T12-10 to T12-12; plan v9.2 Sections 10.2 items 3-7 and 10.5; A11, A12).

A harness for interface tests on recorded T07 refit, T08 and T09 products read by SHA-256, and on the existing runner. No quality claim.
Every rule and expectation is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 3"). It lives under tests/ because it
imports the E6 evaluation layout (tests/adapters/t04_evaluation_layout.py, recorded beside Freeze B; imported, never edited) and a skill's
runner (tools/check_layering.py: tests import anything).

- read_product, merge_by_key: object keys of a product (M1) and the merge of range products against a single pass (M2, T12-10).
- cut_ranges, with_header, without_event_objects: range products cut from a recorded single pass in its own form (unit tests).
- collect_ranges: a bin's ranges and attempts, through the layout's attempt rules, the record's product SHA-256 and the product's own
  completeness (T12-10, T12-11); accounts per stable scope, check_accounts and exposure (T12-12).
- run_steps, partial_then: run_workflow.py, unchanged, on a timed-out, killed, resubmitted or failing step (K5-K8).

Operation:
  recorded --evidence DIR
      DIR holds the folders d4-e6a-7591439 and d4-e6b-7591993 (block-1 range runs). Every file of RECORDED must have its pinned SHA-256;
      then R1 (T07 finding ranges by event index), R2 (T08 and T09 range products merged by key) and R3 (T07 refit ranges complete and
      disjoint by key; collected complete; missing without the middle range). Status and exit (core/status.py): ok 0; failed 1, a
      comparison differs; rejected 2, a file missing or not its pinned SHA-256; incomplete 3, a crash.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import sys
from collections import Counter, namedtuple
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.status import exit_code  # noqa: E402
from tests.adapters import t04_evaluation_layout as layout  # noqa: E402

EXAMPLES = {
    "t07-refit": ("examples/reconstruction-tracking/recorded/refit.product",
                  "a02d04b0b9d522eec9d6923fe79b406ab95477906eb3e3af23eac3231875495b"),
    "t08": ("examples/reconstruction-calorimetry/recorded/events.product",
            "1107dcec6509d236f13954439d650384f389bab0a32096df6bb82f76fd729cc8"),
    "t09-multistart": ("examples/reconstruction-photon-likelihood/recorded/main.multistart.product",
                       "9d44ae712dc4b758cc9cbd4311c17fd1e31568cccd6377250c65aeaa60eee6b1"),
    "t09-topology": ("examples/reconstruction-photon-likelihood/recorded/main.topology.product",
                     "b42cb36ace58a8a31c24fb8b8af0d0502d188dd8fad91e8598ee5b2ef1133150"),
}
KIND_OF = {"t07-refit": "t07-refit", "t08": "jsonl", "t09-multistart": "jsonl", "t09-topology": "jsonl"}
KINDS = ("t07-refit", "jsonl")
T07_SECTIONS = ("track", "state", "parameters", "track_output", "residual", "measurement_output", "residual_covariance")
RANGE_IDENTITY = {"t07-refit": ("product_id", "data_product", "data_sha256", "hit_sets_sha256"),
                  "jsonl": ("product_id", "input", "events", "h1_product")}
NON_FINAL = ("RUNNING", "PENDING", "REQUEUED", "RESIZING", "SUSPENDED", "COMPLETING", "UNKNOWN")
CATEGORIES = ("success", "excluded", "failure", "unconfirmed")
Identity = namedtuple("Identity", "workflow fixture_id block stratum")


class PartitionError(ValueError):
    """A product, a plan or an account the harness refuses; the reason names it."""


class RecordedCrash(RuntimeError):
    """The job's comparison could not run on files whose pinned hash matched: incomplete (exit 3), never rejected (fix round 1, m6)."""


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def frozen_bytes(path: Path, expected: str) -> bytes:
    """The bytes of a recorded file, only if its SHA-256 is the pinned one."""
    try:
        content = Path(path).read_bytes()
    except OSError as error:
        raise PartitionError(f"{path}: cannot be read: {error.strerror}") from None
    if sha256_hex(content) != expected:
        raise PartitionError(f"{path}: SHA-256 {sha256_hex(content)} is not the pinned {expected}")
    return content


def read_example(name: str) -> bytes:
    relative, expected = EXAMPLES[name]
    return frozen_bytes(ROOT / relative, expected)


# ================================================================ M1: object keys

@dataclass(frozen=True)
class Product:
    kind: str
    header: dict
    objects: dict          # key -> value; a T07 key carries its occurrence, so a repeated line is another key (an extra one)
    end: object
    first: int
    count: object          # events of the range (None for a T07 refit product read without a range)
    events: frozenset      # events that hold at least one object


def event_of(key) -> int:
    """The event of an object key: ("event", g) or (section, "event-<g>-...", n)."""
    if key[0] == "event":
        return key[1]
    token = key[1]
    if not token.startswith("event-"):
        raise PartitionError(f"object key {key} names no event")
    return int(token.split("-")[1])


def _read_t07(content: bytes, first: int, count) -> Product:
    text = content.decode("utf-8")
    lines = text.split("\n")
    if lines[-1] != "" or len(lines) < 3 or not lines[-2].startswith("end "):
        raise PartitionError("truncated: the T07 product does not end with its end line")
    header, objects, seen = {}, {}, Counter()
    counts = Counter()
    for line in lines[:-2]:
        tokens = line.split(" ")
        if tokens[0] in T07_SECTIONS:
            if len(tokens) < 2:
                raise PartitionError(f"a {tokens[0]} line without an object token")
            occurrence = seen[(tokens[0], tokens[1])]
            seen[(tokens[0], tokens[1])] += 1
            key = (tokens[0], tokens[1], occurrence)
            objects[key] = line
            counts[tokens[0]] += 1
        elif objects:
            raise PartitionError(f"a header line after the first object line: {line[:60]!r}")
        else:
            name, _, value = line.partition(" ")
            if name in header:
                raise PartitionError(f"header line {name} twice")
            header[name] = value
    try:
        end = tuple(int(n) for n in lines[-2].split(" ")[1:])
    except ValueError:
        raise PartitionError(f"truncated: the end line {lines[-2][:60]!r} is not counts") from None
    if end != tuple(counts[s] for s in T07_SECTIONS):
        raise PartitionError(f"truncated: the end line counts {end}, the product holds {tuple(counts[s] for s in T07_SECTIONS)}")
    events = frozenset(event_of(k) for k in objects)
    if count is not None:
        outside = sorted(e for e in events if not first <= e < first + count)
        if outside:
            raise PartitionError(f"objects of events {outside[:5]} lie outside the range {first}-{first + count - 1}")
    return Product("t07-refit", header, objects, end, first, count, events)


def _read_jsonl(content: bytes, first: int, count) -> Product:
    text = content.decode("utf-8")
    lines = text.split("\n")
    if lines[-1] != "" or len(lines) < 3:
        raise PartitionError("truncated: a JSON Lines product has a header, its events and an end line, and ends with a newline")
    try:
        header = json.loads(lines[0])
        end = json.loads(lines[-2])
        docs = [json.loads(line) for line in lines[1:-2]]
    except ValueError as error:
        raise PartitionError(f"the product is not JSON Lines: {error}") from None
    if not isinstance(end, dict) or "end" not in end or end.get("events") != len(docs):
        raise PartitionError(f"truncated: the end line {lines[-2][:80]!r} does not count the {len(docs)} event lines")
    if [d.get("event") if isinstance(d, dict) else None for d in docs] != list(range(len(docs))):
        raise PartitionError("the event lines are not numbered 0, 1, ... in order")
    if count is not None and len(docs) != count:
        raise PartitionError(f"the product holds {len(docs)} events, the range {first}-{first + count - 1} has {count}: objects outside it")
    objects = {}
    for i, doc in enumerate(docs):
        objects[("event", first + i)] = {**doc, "event": first + i}
    return Product("jsonl", header, objects, end, first, len(docs), frozenset(first + i for i in range(len(docs))))


def read_product(content: bytes, kind: str, first: int = 0, count=None) -> Product:
    """A product's object keys (M1). count, when given, is the range's: an object outside it, or (JSON Lines) another number of events, is
    refused. A truncated product (end line missing or not counting what the product holds) is refused."""
    if kind not in KINDS:
        raise PartitionError(f"product kind {kind} is not one of {KINDS}")
    try:
        return _read_t07(content, first, count) if kind == "t07-refit" else _read_jsonl(content, first, count)
    except UnicodeDecodeError:
        raise PartitionError("the product is not UTF-8 text") from None


# ================================================================ M2: the merge by key (T12-10)

def merge_by_key(single: Product, parts) -> dict:
    """The merged range products against the single pass: omitted, duplicated, differing, extra (keys) and header (field names, as text).
    Exact equality; every list empty when the merge equals the single pass."""
    parts = list(parts)
    seen = Counter()
    merged = {}
    for part in parts:
        if part.kind != single.kind:
            raise PartitionError(f"a {part.kind} range against a {single.kind} single pass")
        for key, value in part.objects.items():
            seen[key] += 1
            merged.setdefault(key, value)
    duplicated = sorted((k for k, n in seen.items() if n > 1), key=repr)
    omitted = sorted((k for k in single.objects if k not in merged), key=repr)
    extra = sorted((k for k in merged if k not in single.objects), key=repr)
    differing = sorted((k for k in merged if k in single.objects and seen[k] == 1 and merged[k] != single.objects[k]), key=repr)
    allowed = set(RANGE_IDENTITY[single.kind])
    header = []
    for index, part in enumerate(parts):
        names = (set(single.header) | set(part.header)) - allowed
        for name in sorted(names):
            if single.header.get(name, "<absent>") != part.header.get(name, "<absent>"):
                header.append(f"range {index} (from {part.first}): header field {name} differs from the single pass")
    return {"omitted": omitted, "duplicated": duplicated, "differing": differing, "extra": extra, "header": header}


def merge_equal(report: dict) -> bool:
    return all(not report[k] for k in ("omitted", "duplicated", "differing", "extra", "header"))


# ================================================================ range products cut from a recorded single pass (unit tests)

def _t07_text(header_lines, object_lines) -> bytes:
    counts = Counter(line.split(" ", 1)[0] for line in object_lines)
    end = "end " + " ".join(str(counts[s]) for s in T07_SECTIONS)
    return ("\n".join(list(header_lines) + list(object_lines) + [end]) + "\n").encode("utf-8")


def _t07_split(content: bytes):
    lines = content.decode("utf-8").split("\n")[:-2]
    head = [line for line in lines if line.split(" ", 1)[0] not in T07_SECTIONS]
    body = [line for line in lines if line.split(" ", 1)[0] in T07_SECTIONS]
    return head, body


def cut_ranges(content: bytes, kind: str, spans) -> list:
    """[(first, range product bytes)]: each span's objects of the single pass, in the product's own form; the range identity changes
    (product_id gets "-r<first>"; JSON Lines: events), the end line counts what the range holds; T07 refit keys stay global (as E6b's)."""
    read_product(content, kind)
    out = []
    for span in spans:
        if kind == "t07-refit":
            head, body = _t07_split(content)
            head = [f"product_id {line.split(' ', 1)[1]}-r{span.first}" if line.startswith("product_id ") else line for line in head]
            keep = [line for line in body if span.first <= event_of((None, line.split(" ")[1])) < span.end]
            out.append((span.first, _t07_text(head, keep)))
        else:
            lines = content.decode("utf-8").split("\n")
            header, end = json.loads(lines[0]), json.loads(lines[-2])
            docs = [json.loads(line) for line in lines[1:-2]]
            if span.end > len(docs):
                raise PartitionError(f"range {span.first}-{span.end - 1} is outside the product's {len(docs)} events")
            header = {**header, "product_id": f"{header.get('product_id')}-r{span.first}", "events": span.count}
            body = [json.dumps({**doc, "event": i}) for i, doc in enumerate(docs[span.first:span.end])]
            out.append((span.first, ("\n".join([json.dumps(header)] + body + [json.dumps({**end, "events": span.count})]) + "\n").encode()))
    return out


def with_header(content: bytes, kind: str, name: str, value) -> bytes:
    """The product with one header field set to value."""
    if kind == "t07-refit":
        head, body = _t07_split(content)
        if not any(line.split(" ", 1)[0] == name for line in head):
            raise PartitionError(f"no header line {name}")
        head = [f"{name} {value}" if line.split(" ", 1)[0] == name else line for line in head]
        return _t07_text(head, body)
    lines = content.decode("utf-8").split("\n")
    lines[0] = json.dumps({**json.loads(lines[0]), name: value})
    return "\n".join(lines).encode("utf-8")


def without_event_objects(content: bytes, event: int) -> bytes:
    """A T07 refit product without any object of one event (an empty collection), its end line recounted."""
    head, body = _t07_split(content)
    return _t07_text(head, [line for line in body if event_of((None, line.split(" ")[1])) != event])


# ================================================================ the range collection (T12-10, T12-11) and accounts (T12-12)

@dataclass(frozen=True)
class Attempt:
    """One Slurm attempt of a range task: sacct's state, exit code and elapsed time, the milestones file (None if none), the RangeRecord
    it left (None if none), the product file found under the range's name (its bytes, a Path for a large file read in a stream, or None
    if none), and the termination."""
    state: str
    exit_code: int
    elapsed: str
    milestones: object
    record: object
    product: object
    termination: str = "confirmed"
    attempt: str = field(kw_only=True)   # the Slurm attempt (job and task ID); the counted attempt's record must name it (fix round 1, I1)


@dataclass(frozen=True)
class Collection:
    status: str            # complete or missing
    outcomes: dict         # EventRange -> (category, reason)
    missing: list          # [(EventRange, reason)] of the failed and unconfirmed ranges
    records: list          # Freeze A section 10's words for each of them
    accounts: dict


def make_record(identity, span, content: bytes, attempt: str = "a1", stratum_sha256: str = "0" * 64) -> "layout.RangeRecord":
    """The RangeRecord a completed range task leaves (as the layout's), naming its product by SHA-256."""
    return layout.RangeRecord(identity.workflow, identity.fixture_id, identity.block, identity.stratum, span.first, span.count,
                              tuple(range(span.first, span.end)), sha256_hex(content), stratum_sha256, "0" * 64, attempt)


def scope(identity, event: int) -> str:
    """The stable scope of a source event."""
    return f"{identity.workflow}/{identity.fixture_id}/b{identity.block}/s{identity.stratum}/e{event}"


def _range_outcome(identity, kind: str, span, tried) -> tuple:
    """(category, reason, events of the range without objects that cannot be claimed read: T07 refit only, fix round 1, I2)."""
    if not tried:
        return "failure", f"missing range: {span.first}-{span.end - 1} has no attempt", frozenset()
    open_ends = [a for a in tried if a.state.split()[0] in NON_FINAL or a.termination != "confirmed"]
    if open_ends:   # fix round 1, m2: any attempt, not only the last, whose end is not confirmed may still write
        a = open_ends[0]
        return "unconfirmed", (f"attempt {a.attempt} is {a.state.split()[0]}, termination {a.termination}: its end is not confirmed; "
                               "check before resubmitting (section 10.2 item 7)"), frozenset()
    verdicts = [layout.classify_attempt(a.state, a.exit_code, a.elapsed, a.milestones)[0] for a in tried]
    try:
        index = layout.select_attempt(verdicts, block=identity.block)
    except layout.LayoutError as error:
        return "failure", str(error), frozenset()
    counted = tried[index]
    record = counted.record
    if record is None:
        return "failure", (f"missing range: the counted attempt of {span.first}-{span.end - 1} left no record (a file a killed attempt "
                           "left is never counted)"), frozenset()
    if record.attempt != counted.attempt:   # fix round 1, I1
        return "failure", (f"the record of {span.first}-{span.end - 1} names attempt {record.attempt}, not the counted attempt "
                           f"{counted.attempt}: an earlier attempt's record is never counted"), frozenset()
    if (record.workflow, record.fixture_id, record.block, record.stratum) != tuple(identity):
        return "failure", f"the record of {span.first}-{span.end - 1} is of another bin", frozenset()
    if (record.first, record.count) != (span.first, span.count) or tuple(record.events) != tuple(range(span.first, span.end)):
        return "failure", f"missing range: the counted attempt's record is not of the range {span.first}-{span.end - 1}", frozenset()
    if counted.product is None:
        return "failure", f"missing range: the product of {span.first}-{span.end - 1} is absent", frozenset()
    large = isinstance(counted.product, Path)   # a large file, read in a stream (the job's refit ranges)
    if (_streamed_sha256(counted.product) if large else sha256_hex(counted.product)) != record.product_sha256:
        return "failure", (f"the product of {span.first}-{span.end - 1} is not the one its record names (SHA-256): a partial file or an "
                           "earlier attempt's file, never reused"), frozenset()
    try:
        if large and kind == "t07-refit":
            _, events, _, complete = _t07_keys(counted.product)
            if not complete:
                raise PartitionError("truncated: the end line does not count the product's lines")
            if any(not span.first <= e < span.end for e in events):
                raise PartitionError(f"objects outside the range {span.first}-{span.end - 1}")
        else:
            events = read_product(counted.product.read_bytes() if large else counted.product, kind, first=span.first,
                                  count=span.count).events
    except PartitionError as error:
        return "failure", f"the product of {span.first}-{span.end - 1} is refused: {error}", frozenset()
    if kind == "t07-refit":   # fix round 1, I2: no events-read declaration in the format; an event without objects is not claimed read
        return "success", "", frozenset(range(span.first, span.end)) - frozenset(events)
    return "success", "", frozenset()


def collect_ranges(identity, kind: str, total: int, planned, attempts, exclusions=None) -> Collection:
    """A bin's planned ranges and their attempts (stage plan, "Range collection", steps 1-5), then its accounts. A plan that does not cover
    events 0 to total - 1 once, or an exclusion without a reason or of an event outside the bin, is refused (PartitionError)."""
    planned = list(planned)
    try:
        layout.check_ranges(planned, total)
    except layout.LayoutError as error:
        raise PartitionError(f"the plan is refused: {error}") from None
    exclusions = dict(exclusions or {})
    bad = [e for e, why in exclusions.items() if not isinstance(why, str) or not why.strip() or not 0 <= e < total]
    if bad:
        raise PartitionError(f"exclusions {sorted(bad)} have no reason or lie outside the bin")
    found = {span: _range_outcome(identity, kind, span, list(attempts.get(span, ()))) for span in planned}
    outcomes = {span: (category, reason) for span, (category, reason, _) in found.items()}
    accounts = {"success": [], "excluded": {}, "failure": [], "unconfirmed": []}
    for span in sorted(planned):
        category, _, unread = found[span]
        for event in range(span.first, span.end):
            if category == "success" and event in unread:
                accounts["unconfirmed"].append(event)
            elif category == "success" and event in exclusions:
                accounts["excluded"][event] = exclusions[event]
            else:
                accounts[category].append(event)
    accounts["unconfirmed"].sort()
    missing = [(span, outcomes[span][1]) for span in sorted(planned) if outcomes[span][0] != "success"]
    missing += [(span, f"T07 refit format gap: events {sorted(found[span][2])[:5]} hold no object, and the product declares no events "
                       "read, so an empty collection cannot be told from events not read (unconfirmed)")
                for span in sorted(planned) if outcomes[span][0] == "success" and found[span][2]]
    missing.sort(key=lambda item: item[0])
    records = [f"required output missing: {scope(identity, span.first)} to e{span.end - 1}: {reason}" for span, reason in missing]
    return Collection("complete" if not missing else "missing", outcomes, missing, records, accounts)


def check_accounts(accounts: dict, total: int) -> list:
    """Defects of a bin's accounts: an event in two categories, an event of the bin in none, an event outside it, an exclusion without a
    reason. Empty when every source event 0 to total - 1 is in exactly one category."""
    defects = []
    where = {}
    for category in CATEGORIES:
        events = accounts.get(category, {} if category == "excluded" else [])
        if category == "excluded":
            for event, why in events.items():
                if not isinstance(why, str) or not why.strip():
                    defects.append(f"event {event}: excluded without a reason")
        for event in events:
            where.setdefault(event, []).append(category)
    for event, categories in sorted(where.items()):
        if len(categories) > 1:
            defects.append(f"event {event}: in two categories or more ({', '.join(categories)})")
        if not 0 <= event < total:
            defects.append(f"event {event}: outside the bin (0 to {total - 1})")
    for event in range(total):
        if event not in where:
            defects.append(f"event {event}: in no category")
    return defects


DENOMINATOR_USE = {
    "success": "numerator and denominator",
    "excluded": "denominator only: a selection or boundary loss lowers the exposure (section 10.2 item 6)",
    "failure": "denominator only: a failed range lowers the exposure; it is never topped up",
    "unconfirmed": "denominator only, and reported: it is checked before any resubmission (section 10.2 item 7)",
    "original_gaps": "neither: never-recorded events are not source events; their observable scope is listed apart (section 10.2 item 4)",
}


def exposure(accounts: dict, total: int, gaps=()) -> dict:
    """Counts per category and the exposure success / total: excluded, failed and unconfirmed events lower it; original gaps (never
    recorded) are listed apart with their observable scope and are not source events. Fix round 1, m1: the accounts must pass
    check_accounts, and each gap needs a reason and a span (first, count) in the stream's own numbering that overlaps no other gap."""
    defects = check_accounts(accounts, total)
    if defects:
        raise PartitionError(f"the accounts are inconsistent: {defects[:3]}")
    spans = []
    for gap in gaps:
        if not isinstance(gap, dict) or not str(gap.get("reason", "")).strip() or not isinstance(gap.get("first"), int) \
                or not isinstance(gap.get("count"), int) or gap["count"] < 1:
            raise PartitionError(f"a gap needs a reason and a span (first, count >= 1): {gap}")
        spans.append((gap["first"], gap["first"] + gap["count"], gap.get("scope")))
    spans.sort()
    for (a0, a1, sa), (b0, b1, sb) in zip(spans, spans[1:]):
        if b0 < a1:
            raise PartitionError(f"gaps {sa} and {sb} overlap")
    counts = {c: len(accounts.get(c, ())) for c in CATEGORIES}
    return {"source_events": total, **counts, "exposure": counts["success"] / total if total else None, "original_gaps": list(gaps),
            "denominator": dict(DENOMINATOR_USE)}


# ================================================================ K5-K8: the runner, unchanged

RANGE_SCRIPT = r'''import os, signal, sys, time
mode = sys.argv[1]
out = "range.out"
if mode == "fail":
    count = int(open("invocations.txt").read()) if os.path.exists("invocations.txt") else 0
    open("invocations.txt", "w").write(f"{count + 1}\n")
    sys.exit(1)
if mode == "keep" and os.path.exists(out):
    sys.exit(0)   # a resubmission that reuses the file it finds
if mode == "rewrite" or mode == "keep":
    open(out, "w").write("complete\n")
    sys.exit(0)
with open(out, "w") as stream:
    stream.write("partial\n")
    stream.flush()
if mode == "kill":
    os.kill(os.getpid(), signal.SIGKILL)
time.sleep(60)
'''


def partial_then(mode: str) -> list:
    """Two steps: `range` (steps/range.py MODE writes range.out: sleep and kill write part of it first; keep exits 0 on a file it finds;
    rewrite writes it; fail counts its invocations and exits 1) and `merge`, which needs it."""
    if mode not in ("sleep", "kill", "keep", "rewrite", "fail"):
        raise PartitionError(f"unknown mode {mode}")
    return [{"id": "range", "argv": ["{python}", "steps/range.py", mode], "inputs": ["steps/range.py"], "outputs": ["range.out"]},
            {"id": "merge", "needs": ["range"], "argv": ["{python}", "-c", "open('merged.out', 'w').write(open('range.out').read())"],
             "inputs": ["range.out"], "outputs": ["merged.out"]}]


def run_steps(work: Path, steps, timeout_s=None, incremental: bool = False, step_extra=None) -> tuple:
    """Run the steps with run_workflow.py in this process (the stage 2 harness's loader, with its pinned release digest, so --incremental
    can skip). Returns (exit code, the runner's JSON, {step id: run record})."""
    from tests.contracts import t12_reprocessing
    work = Path(work)
    (work / "steps").mkdir(parents=True, exist_ok=True)
    (work / "steps" / "range.py").write_text(RANGE_SCRIPT, encoding="utf-8")
    steps = [dict(s) for s in steps]
    if timeout_s is not None:
        steps[0]["timeout_s"] = timeout_s
    steps[0].update(step_extra or {})
    path = work / "workflow.json"
    path.write_text(json.dumps({"workflow": "t12-stage3", "steps": steps}, indent=1), encoding="utf-8")
    argv = [str(path), "--work", str(work), "--created", "2026-11-13", "--status", "synthetic"] + (["--incremental"] if incremental else [])
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = t12_reprocessing.runner().main(argv)
    records = {}
    for record in (work / "runs").glob("*.computational-run.json"):
        records[record.name.split(".computational-run.json")[0]] = json.loads(record.read_text(encoding="utf-8"))
    ran = {s["id"] for s in json.loads(buffer.getvalue()).get("steps", [])}
    return code, json.loads(buffer.getvalue()), {k: v for k, v in records.items() if k in ran}


# ================================================================ the job of record: block-1 range runs (R1-R3)

E6A, E6B = "d4-e6a-7591439", "d4-e6b-7591993"
T07_RUNS = ("full", "full-again", "r0", "r50", "r120")
RECORDED = {
    f"{E6A}/range-t07-clean/clean-b1-s2-full-again.product": "253bcfadada66e77e521ce7b8f4b37eed95b368b2ed144d69d4c890db12c1c68",
    f"{E6A}/range-t07-clean/clean-b1-s2-full-again.record": "ea99f1557a0595ef4892db1c60ae814383308c8ef58039a7c4c308b946f578b0",
    f"{E6A}/range-t07-clean/clean-b1-s2-full-again.t07data": "e88a53b8c6699afd7de74bd58b8709acc8ef10a88f53f3484e96570871060d42",
    f"{E6A}/range-t07-clean/clean-b1-s2-full-again.t07truth": "9912702898d1cb8e4e327b3d586b996e019e13ec96282b265ae3c0a4035389ab",
    f"{E6A}/range-t07-clean/clean-b1-s2-full.product": "1dd3b426d984f45111e24769a244943f059e592d5484343039ee9dbb0824c868",
    f"{E6A}/range-t07-clean/clean-b1-s2-full.record": "23065f7b02b81e7d39626d3dced3cf41d90c79df1f10a36c10d25200d3535b8c",
    f"{E6A}/range-t07-clean/clean-b1-s2-full.t07data": "e88a53b8c6699afd7de74bd58b8709acc8ef10a88f53f3484e96570871060d42",
    f"{E6A}/range-t07-clean/clean-b1-s2-full.t07truth": "9912702898d1cb8e4e327b3d586b996e019e13ec96282b265ae3c0a4035389ab",
    f"{E6A}/range-t07-clean/clean-b1-s2-r0.product": "b5a2abf84b45ad60fb348e5a4a5aa2d5bbc2f075f97e1e08c784d75ce86e9b6f",
    f"{E6A}/range-t07-clean/clean-b1-s2-r0.record": "e1a50367fcfb1fb8e5e8dc4f7df1137c7ebe43ed5a8fac383a6c45ccdafac54c",
    f"{E6A}/range-t07-clean/clean-b1-s2-r0.t07data": "d5328cc52802809780f85b420a9d29980e81e5e05e542c34443ca2acdf515b03",
    f"{E6A}/range-t07-clean/clean-b1-s2-r0.t07truth": "281e379abf244e38fb831a0af20f1934e6592f0faebeee4b6364810c9cbe49a6",
    f"{E6A}/range-t07-clean/clean-b1-s2-r120.product": "bf7a7f9c9e92772b8913b0cc0ea3508880e95cc8af302cda2fbd97021315b218",
    f"{E6A}/range-t07-clean/clean-b1-s2-r120.record": "47782edaf1ae46e63f053b4736cc01f662fd3134ddaaa570ba167bc10e62a4cb",
    f"{E6A}/range-t07-clean/clean-b1-s2-r120.t07data": "aeb2bcb22fd8001c99054fb11fd57c5a4607bdced9d1d489216114286a79cc64",
    f"{E6A}/range-t07-clean/clean-b1-s2-r120.t07truth": "579e95c1006de3853e274609f81da0043b63ae620eac0c91ee16b9c7bbb50156",
    f"{E6A}/range-t07-clean/clean-b1-s2-r50.product": "d2207ddeacb73f553d1031ff94297224f3e1c56433de289827085669a585d944",
    f"{E6A}/range-t07-clean/clean-b1-s2-r50.record": "c3cc722632201183bbd02635967eb3d132df57fe094eca616138ecbcdf48d593",
    f"{E6A}/range-t07-clean/clean-b1-s2-r50.t07data": "ede49bd401d866120ff9513992e3c8d8932082aefd0e71e4f39b027870eb12a9",
    f"{E6A}/range-t07-clean/clean-b1-s2-r50.t07truth": "270b98cd67840dd0f636fc9ac6c24a41e84c53f5f5bcdf2f37d5dc937df024ca",
    f"{E6A}/range-t07-noise/noise-b1-s2-full-again.product": "ae480db31b99b85a475385fddf13f7a6fe2c5e76f1b6dc56c6893436e00abd1f",
    f"{E6A}/range-t07-noise/noise-b1-s2-full-again.record": "e163168841d07a7bfe309e0186d180ad1657d7db41beadbcbac5c4244e30c6c0",
    f"{E6A}/range-t07-noise/noise-b1-s2-full-again.t07data": "2f45f6367ffd0348815f63e29dbc68b07036feffc930c19e4a97a9208a4f18ae",
    f"{E6A}/range-t07-noise/noise-b1-s2-full-again.t07truth": "f36e154fe964a48a7ff1176fd004eee4fa4097c55e8cda41eed3b7b7a8d6ffd6",
    f"{E6A}/range-t07-noise/noise-b1-s2-full.product": "5fb15af74eaaab8ccc4fc07f405cf73d8160b1b6925d0b1d548862788acda0fc",
    f"{E6A}/range-t07-noise/noise-b1-s2-full.record": "f06f2c18a59a6b2ebf93e11999184603e4fa13da4bfd0916997fc8fdc45a8352",
    f"{E6A}/range-t07-noise/noise-b1-s2-full.t07data": "2f45f6367ffd0348815f63e29dbc68b07036feffc930c19e4a97a9208a4f18ae",
    f"{E6A}/range-t07-noise/noise-b1-s2-full.t07truth": "f36e154fe964a48a7ff1176fd004eee4fa4097c55e8cda41eed3b7b7a8d6ffd6",
    f"{E6A}/range-t07-noise/noise-b1-s2-r0.product": "46f30e44075835d1c06c855f555c597f1f3da129d3f07c82fb60cbcd6ca2aaa0",
    f"{E6A}/range-t07-noise/noise-b1-s2-r0.record": "a2bdb2cfdba1db1fe2d4ed57bd71e3c809b3afadd797e4bebfa5b2722ac2aaed",
    f"{E6A}/range-t07-noise/noise-b1-s2-r0.t07data": "06f23a69315d81d4f93aedf0b20344232c6107b50f7241f3b1a8353c0e8d0497",
    f"{E6A}/range-t07-noise/noise-b1-s2-r0.t07truth": "f46edbfba08104af44fce99a4d070dccdf2df14a87576e02013951ff2a8e7c1b",
    f"{E6A}/range-t07-noise/noise-b1-s2-r120.product": "99021a3d908cfb0abec8902267307db605783155f22fd79f96aed527077af932",
    f"{E6A}/range-t07-noise/noise-b1-s2-r120.record": "e23668f8c52915f468bbb91837b297bca11a7d0f47662e88db347bedb97abb47",
    f"{E6A}/range-t07-noise/noise-b1-s2-r120.t07data": "f615811d9dd462b66707decbdeb1f9092ceab4f29a8a5576f0395e4a2712d1b1",
    f"{E6A}/range-t07-noise/noise-b1-s2-r120.t07truth": "bfe399a9ca73fd480a2ac0776324afaef87df1aa4a8b7bd95f5e2bd5ac8428e6",
    f"{E6A}/range-t07-noise/noise-b1-s2-r50.product": "8a93ae3ed9ff8c50dda5ffad92b3589eb54c5a3318f0c46c60c29d29e6adcc28",
    f"{E6A}/range-t07-noise/noise-b1-s2-r50.record": "f0022aa884a85c64c77905cb517a61a36fcfaf6eb8570b5802434ae2b811b7a1",
    f"{E6A}/range-t07-noise/noise-b1-s2-r50.t07data": "a00eaa3fcd614f1b75a0054a4eab63ea6a9a28062decf7eb36410e421082318f",
    f"{E6A}/range-t07-noise/noise-b1-s2-r50.t07truth": "85d7fe1bf015319e12240df98ce463b2d4b7ac7ce4383cd9333f6c85b31591f1",
    f"{E6A}/range-t08-main/full.product.jsonl": "d92bd5b1fc1b6579706b6870e19e855e421c6fa6700a4d6f3362a0d28aa6b078",
    f"{E6A}/range-t08-main/r0.product.jsonl": "17cae5c2ccbcd9efada13980db679341edf713512bc9789eebd8ef57c75095f2",
    f"{E6A}/range-t08-main/r200.product.jsonl": "0e1cd0f1a5a8644b7a7ec70bed90a2b34ab3bde13103d447e742ca8970bb9aeb",
    f"{E6A}/range-t08-main/r450.product.jsonl": "5828980b26e4cbe10b79a81c00bc6778aa14b3d20ecb7f7561c1ec32ed8940b2",
    f"{E6A}/range-t08-dead/full.product.jsonl": "5af4a4f22f58b6af510846fa8062cac7cba0e788c2daedbe97846225f0ae98ad",
    f"{E6A}/range-t08-dead/r0.product.jsonl": "2eaab4184f736f2b22be46f6cdc73663e5d565d548dc598c70a0d15189f6f225",
    f"{E6A}/range-t08-dead/r100.product.jsonl": "20f681b43e02c83689d7aaca2acdd592c32d1488749712874502ffaac70770bd",
    f"{E6A}/range-t09-main/full.multistart.product.jsonl": "50a1f3510da6e1925b0bef9b289cba448e86ec8b9e39314ae61aa2c5ac8ed98d",
    f"{E6A}/range-t09-main/full.topology.product.jsonl": "d5dfcf80bc050e4c5871577a90ff44b3cc981b48fad048ae49df4c933b62e0e5",
    f"{E6A}/range-t09-main/r0.multistart.product.jsonl": "72d8a0846c023d02b21b761774cd7853c2a992f5252b9d78ccb571a6f3264894",
    f"{E6A}/range-t09-main/r0.topology.product.jsonl": "41cce57fc89cc0ea76ced45cb13ee3f102b650845b6316b5e1944f9a4d543227",
    f"{E6A}/range-t09-main/r13.multistart.product.jsonl": "5bcb191e097881f771aa99e70bc9e86c22b89dc0f053ca00cd09f87af1c7bfd5",
    f"{E6A}/range-t09-main/r13.topology.product.jsonl": "6c62c7fc8f8bcef0c84611ee3f7828add7cee8025995f292b5d97b9098f83a66",
    f"{E6A}/range-t09-main/r31.multistart.product.jsonl": "480e22683d3a6d61b07b66a4b04c9e70e57934b7b0658bd5a1d7ad397f9c2876",
    f"{E6A}/range-t09-main/r31.topology.product.jsonl": "361970a249a3de24e30c5bb2603caf534a080ec1ec55288df37f521daa931d00",
    f"{E6B}/t07/clean-s4/refit-clean-b1-s4-0.product": "8256602249690260e165aa348dd388de27e3281d9b77e54be892f0b0097e6aa9",
    f"{E6B}/t07/clean-s4/refit-clean-b1-s4-1000.product": "8662dcc603ec44070dbfd80de82eefdcca860ea2f74eb13626ba452d52afb2dc",
    f"{E6B}/t07/clean-s4/refit-clean-b1-s4-2000.product": "489296a10f619b8a4c706b6097cd89f1f1cb19d1c85881a8683e8824df32b52e",
    f"{E6B}/t07/clean-s4/refit-collection.json": "762d60098ce4d41c852661a513b3295b44101f73ec123f0b47f80cbfbe691547",
}
# R2: (label, folder, full product, [(first, range product)]), the E6a ranges (e6a.sh, range-t08-*, range-t09-main).
JSONL_RUNS = (
    ("T08 main s4", "range-t08-main", "full.product.jsonl", [(0, "r0.product.jsonl"), (200, "r200.product.jsonl"), (450, "r450.product.jsonl")]),
    ("T08 dead s0", "range-t08-dead", "full.product.jsonl", [(0, "r0.product.jsonl"), (100, "r100.product.jsonl")]),
    ("T09 main s9 multistart", "range-t09-main", "full.multistart.product.jsonl",
     [(0, "r0.multistart.product.jsonl"), (13, "r13.multistart.product.jsonl"), (31, "r31.multistart.product.jsonl")]),
    ("T09 main s9 topology", "range-t09-main", "full.topology.product.jsonl",
     [(0, "r0.topology.product.jsonl"), (13, "r13.topology.product.jsonl"), (31, "r31.topology.product.jsonl")]),
)
REFIT_FIRSTS = (0, 1000, 2000)
REFIT_EVENTS = 3000


def recorded_reads() -> set:
    """Every file recorded() reads, relative to the evidence folder (fix round 1, n1: RECORDED must pin exactly these)."""
    reads = {f"{E6A}/range-t07-{fx}/{fx}-b1-s2-{run}.{kind}" for fx in ("clean", "noise") for run in T07_RUNS
             for kind in ("t07data", "t07truth", "record", "product")}
    for _, folder, full, parts in JSONL_RUNS:
        reads |= {f"{E6A}/{folder}/{full}"} | {f"{E6A}/{folder}/{name}" for _, name in parts}
    reads |= {f"{E6B}/t07/clean-s4/refit-clean-b1-s4-{first}.product" for first in REFIT_FIRSTS}
    return reads | {f"{E6B}/t07/clean-s4/refit-collection.json"}


def _streamed_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as stream:
            for block in iter(lambda: stream.read(1 << 22), b""):
                digest.update(block)
    except OSError as error:
        raise PartitionError(f"{path.name}: cannot be read: {error.strerror}") from None
    return digest.hexdigest()


def _t07_keys(path: Path):
    """Streamed keys of a large T07 refit product: (sections' keys set, events set, header, end check). Values are not kept."""
    keys, events, header, counts, seen, end = set(), set(), {}, Counter(), Counter(), None
    try:
        stream = open(path, encoding="utf-8")
    except OSError as error:
        raise PartitionError(f"{path.name}: cannot be read: {error.strerror}") from None
    with stream:
        for line in stream:
            if end is not None:
                raise PartitionError(f"{path.name}: a line after the end line")
            line = line.rstrip("\n")
            tokens = line.split(" ", 2)
            if tokens[0] in T07_SECTIONS:
                if len(tokens) < 2:
                    raise PartitionError(f"{path.name}: a {tokens[0]} line without an object token")
                occurrence = seen[(tokens[0], tokens[1])]
                seen[(tokens[0], tokens[1])] += 1
                keys.add((tokens[0], tokens[1], occurrence))
                events.add(event_of((tokens[0], tokens[1])))
                counts[tokens[0]] += 1
            elif counts and tokens[0] != "end":
                raise PartitionError(f"{path.name}: a header line after the first object line (fix round 1, m5: as read_product)")
            elif tokens[0] == "end":
                try:
                    end = tuple(int(n) for n in line.split(" ")[1:])
                except ValueError:
                    raise PartitionError(f"{path.name}: the end line is not counts") from None
            elif not counts:
                if tokens[0] in header:
                    raise PartitionError(f"{path.name}: header line {tokens[0]} twice")
                header[tokens[0]] = line.partition(" ")[2]
    complete = end == tuple(counts[s] for s in T07_SECTIONS)
    return keys, events, header, complete


def jsonl_ranges(base: Path, full: str, parts) -> tuple:
    """R2: the range products (first, file name) of one JSON Lines run, merged by key against its full product. (ok, single, report)."""
    single = read_product((base / full).read_bytes(), "jsonl")
    ranged = [read_product((base / name).read_bytes(), "jsonl", first=first) for first, name in parts]
    report = merge_by_key(single, ranged)
    return merge_equal(report) and sum(p.count for p in ranged) == single.count, single, report


def refit_ranges(base: Path, names: dict, size: int, total: int, records=None) -> tuple:
    """R3: large T07 refit range products {first: file name} of `size` events each, read in a stream: each complete, no object outside
    its range, no key in two ranges, every event 0 to total - 1 with objects, headers equal but the range identity; with records {first:
    RangeRecord} (fix round 1, m3), each product's data_sha256 is its record's stratum file and its hit_sets_sha256 its record's range
    input. (problems, keys)."""
    seen_keys, covered, headers, problems = Counter(), set(), [], []
    for first, name in sorted(names.items()):
        try:
            keys, events, header, complete = _t07_keys(base / name)
        except PartitionError as error:
            problems.append(f"range {first}: refused: {error}")
            continue
        if records is not None:
            record = records.get(first)
            if record is None:
                problems.append(f"range {first}: no record")
            elif (header.get("data_sha256"), header.get("hit_sets_sha256")) != (record.stratum_sha256, record.input_sha256):
                problems.append(f"range {first}: data_sha256 or hit_sets_sha256 is not its record's stratum file or range input")
        if not complete:
            problems.append(f"range {first}: the end line does not count its lines (truncated)")
        outside = sorted(e for e in events if not first <= e < first + size)
        if outside:
            problems.append(f"range {first}: objects of events {outside[:3]} outside it")
        covered |= events
        seen_keys.update(keys)
        headers.append((first, header))
    doubled = [k for k, n in seen_keys.items() if n > 1]
    if doubled:
        problems.append(f"{len(doubled)} keys in two ranges, first {doubled[:2]}")
    if covered != set(range(total)):
        problems.append(f"events with objects: {len(covered)} of {total} (an empty collection is allowed in general, but every event of "
                        "this clean fixture has tracks)")
    allowed = set(RANGE_IDENTITY["t07-refit"])
    for first, header in headers[1:]:
        differ = sorted(n for n in set(header) | set(headers[0][1]) if n not in allowed and header.get(n) != headers[0][1].get(n))
        if differ:
            problems.append(f"range {first}: header fields {differ} differ from range {headers[0][0]}")
    return problems, len(seen_keys)


def recorded(evidence: Path) -> tuple:
    """R1-R3 on the block-1 range runs. Returns (status, lines)."""
    lines = []
    for relative, expected in RECORDED.items():
        got = _streamed_sha256(evidence / relative)
        if got != expected:
            raise PartitionError(f"{relative}: SHA-256 {got} is not the pinned {expected}")
    lines.append(f"PASS {len(RECORDED)} recorded files have their pinned SHA-256")
    try:   # fix round 1, m6: past the hashes, a refusal of a pinned file is the harness's crash (incomplete), never "rejected"
        failed = _compare_recorded(evidence, lines)
    except PartitionError as error:
        raise RecordedCrash(f"a pinned file was refused after its hash matched: {error}") from None
    return ("failed" if failed else "ok"), lines


def _compare_recorded(evidence: Path, lines: list) -> bool:
    failed = False
    # R1: T07 finding ranges by event index.
    for fixture in ("clean", "noise"):
        folder = evidence / E6A / f"range-t07-{fixture}"
        runs = {run: {kind: (folder / f"{fixture}-b1-s2-{run}.{kind}").read_bytes() for kind in ("t07data", "t07truth", "record", "product")}
                for run in T07_RUNS}
        parts = [(0, runs["r0"]), (50, runs["r50"]), (120, runs["r120"])]
        klass, detail = layout.classify_t07_by_index(runs["full"], runs["full-again"], parts)
        ok = klass == "equal"
        failed |= not ok
        lines.append(f"{'PASS' if ok else 'FAIL'} R1 T07 {fixture} s2 150 events, ranges 0:50 50:70 120:30: {klass} ({detail})")
    # R2: T08 and T09 range products merged by key against the full product.
    for label, folder, full, parts in JSONL_RUNS:
        ok, single, report = jsonl_ranges(evidence / E6A / folder, full, parts)
        failed |= not ok
        lines.append(f"{'PASS' if ok else 'FAIL'} R2 {label}: {single.count} events in {len(parts)} ranges, merged by key: "
                     + ("equal (no omitted, duplicated, differing or extra key; headers equal but the range identity)" if ok else
                        json.dumps({k: [str(x) for x in v[:5]] for k, v in report.items()})))
    # R3: the T07 refit ranges of E6b (no single pass kept): complete, disjoint, every event once, headers equal; collected.
    base = evidence / E6B / "t07" / "clean-s4"
    names = {first: f"refit-clean-b1-s4-{first}.product" for first in REFIT_FIRSTS}
    collection = json.loads((base / "refit-collection.json").read_text(encoding="utf-8"))
    records = {r["first"]: layout.RangeRecord.from_json(json.dumps(r)) for r in collection["records"]}
    problems, keys = refit_ranges(base, names, 1000, REFIT_EVENTS, records)
    ok = not problems
    failed |= not ok
    lines.append(f"{'PASS' if ok else 'FAIL'} R3 T07 refit clean b1 s4: ranges 0, 1000, 2000 complete, disjoint by key, events 0-2999 once, "
                 f"each tied to its record's stratum file and range input, {keys} keys" + ("" if ok else f": {problems}"))
    identity = Identity("T07", 7001, 1, 4)
    spans = [layout.EventRange(first, 1000) for first in REFIT_FIRSTS]
    # The attempt history is synthetic (n3): one completed attempt per range, its id the E6b record's own attempt id (I1).
    attempts = {span: [Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), records[span.first], base / names[span.first],
                               attempt=records[span.first].attempt)] for span in spans}
    whole = collect_ranges(identity, "t07-refit", REFIT_EVENTS, spans, attempts)
    middle = layout.EventRange(1000, 1000)   # the middle range's counted attempt finds range 0's file under its name
    wrong = {**attempts, middle: [Attempt("COMPLETED", 0, "00:01:00", ("draws-started",), records[1000], base / names[0],
                                          attempt=records[1000].attempt)]}
    swapped = collect_ranges(identity, "t07-refit", REFIT_EVENTS, spans, wrong)
    ok = whole.status == "complete" and whole.accounts["success"] == list(range(REFIT_EVENTS)) and swapped.status == "missing" \
        and [s.first for s, _ in swapped.missing] == [1000] and swapped.accounts["failure"] == list(range(1000, 2000))
    failed |= not ok
    lines.append(f"{'PASS' if ok else 'FAIL'} R3 collection (synthetic attempt history, one completed attempt per range with the E6b "
                 f"records' attempt ids): all three ranges {whole.status}; with range 0's file under the middle range's name "
                 f"{swapped.status} ({swapped.missing[0][1][:80] if swapped.missing else 'no reason'}); exposure "
                 f"{exposure(swapped.accounts, REFIT_EVENTS)['exposure']:.4f}")
    return failed


def _emit(status: str, **fields) -> int:
    print(json.dumps({"status": status, **fields}, sort_keys=True))
    return exit_code(status)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="operation", required=True)
    run = sub.add_parser("recorded", help="R1-R3 on the block-1 range runs (job of record)")
    run.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        status, lines = recorded(args.evidence)
    except PartitionError as error:
        return _emit("rejected", reason=str(error))
    except Exception as error:  # noqa: BLE001 - a crash is incomplete, never a verdict
        return _emit("incomplete", reason=f"{type(error).__name__}: {error}")
    for line in lines:
        print(line)
    return _emit(status, checks=len(lines))


if __name__ == "__main__":
    sys.exit(main())
