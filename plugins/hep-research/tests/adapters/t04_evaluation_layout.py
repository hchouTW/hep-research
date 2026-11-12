"""The evaluation's parallel layout for T07-T09 on blocks 11 and 12 (D4 stage E6a; d4-e6a-brief.md, item 2). Scoring side; no job here.

Sections cited are of t04-values-v4.md (Freeze A). The evaluation runs as arrays of short tasks, one per (fixture, stratum, event range) for the
recipe runs, and scores a bin only when every one of its ranges is present (section 5.1: the bootstrap is over all events of a bin, 12,000).

The condition, every range draws exactly the events a single full draw would, holds for each workflow as follows (choice (b) of the brief for
T08 and T09):
- T07: the frozen generator takes --first-event (native/t07_fixture_generator.cpp; each event's state is the four integers hashed, section 3.2),
  so a range is its own draw; its data and truth bodies are the full draw's, byte for byte (compare_t07_bodies), and the finder's record and
  product equal the full run's once ordinals are renumbered (compare_t07_records, compare_t07_products). The layout keeps one T07 range per
  bin, so this equality is a reading (classify_t07_ranges: nondeterminism, position dependence or a renumbering defect; fix round 1, I6).
- T08 and T09: the fixture tools t08_fixture_files.py and t09_fixture_files.py take --count from event 0 only, and they are in the Freeze-B
  run's manifest and the adapters' job-of-record pins, so they are not changed (choice (a) would renew both and change two adapters after the
  run). One generation task per stratum writes the whole stratum with the unchanged tool; the harness cuts range files from it
  (t08_cells_range, t09_readout_range, t09_truth_range) with the recipes' own format writers, and the recipe tasks fit the ranges. A range
  file's events are the stratum file's, byte for byte, and a range file of the whole stratum is the stratum file itself. The merged range
  products equal the full product line for line once each event line's index is renumbered (compare_jsonl_ranges). No recipe file changes.
The completeness check (check_ranges, check_bin) refuses a gap, an overlap, a duplicate and a missing range, and requires every event index
0 to N - 1 once; it reads the products themselves (their SHA-256 against the task's record, their event lines and end line against its count)
and the expected bin's identity, so a truncated or wrong product is refused, never scored as a shorter bin (fix round 1, I7). "Top-up: never"
(section 3.4): a missing range is a failed task, not a smaller bin. Fix round 1, I3: the collection runs with afterany on every task of its
workflow, so it runs whatever failed; it classifies every task's attempts as the Freeze-B run's collection step does (classify_attempt, from
sacct and the milestones file only), selects the counted one (select_attempt), checks each bin (collect_bin), and writes section 10's "required
output missing" records for an incomplete bin (missing_bin_records); the scoring of a bin runs on a complete bin only. Fix round 1, I4: a task
that fits or scores events it did not draw writes the milestone fit-started, read as draws-started; on blocks 11 and 12 only an attempt that drew
and fitted nothing (NO-DRAW, NEVER-RAN) may precede the counted one, since U-B12's repeat covers block 2 only (O6, settled). Fix round 2: every
task and collection starts a Python script with SCRIPT_FLAGS (never -I for a script with sibling imports) and requires that script's own result
line (RESULT_LINES, classify_script_run): a traceback or a missing result line is a crash, never read as a negative result.
The cost is a closed form (Plan): CPU-hours (allocated CPUs x elapsed) from recorded per-event costs and per-task start-up, the task count, the
memory request per task (T07 2 x 7,900 MB as the Freeze-B run, fix round 1, I5), every task pinned to U-W7's CPU class, and the wall of the
longest chain if the queue runs everything at once.
"""
from __future__ import annotations

import collections
import hashlib
import json
import math
import struct
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
for _folder in ("adapters/acts-tracking/assets/fixture_tools", "adapters/calo-cluster/assets", "adapters/photon-likelihood/assets"):
    if str(ROOT / _folder) not in sys.path:
        sys.path.insert(0, str(ROOT / _folder))

EVENTS_PER_BIN = 12000                 # section 5.1, "Generation": stratified, 12,000 events per bin
EVALUATION_BLOCKS = (11, 12)           # section 3.2
FREEZE_B_BLOCKS = (2, 3, 4, 5)         # section 3.2; U-B12 (decisions.md) allows a repeat on block 2
INFRASTRUCTURE = ("NODE_FAIL", "BOOT_FAIL", "PREEMPTED")   # as the Freeze-B run's collection step (fbrun_tools.py)
RESOURCE = ("TIMEOUT", "OUT_OF_MEMORY")
NOTHING_DRAWN = ("NO-DRAW", "NEVER-RAN")
REPEATS_ON_FREEZE_B = ("REPEATABLE", "REPEATABLE-WITH-NEW-REQUEST")


class LayoutError(ValueError):
    """A range set, a bin, an attempt list or a range file the layout refuses; the reason names it."""


# ---- Ranges and the completeness check.

@dataclass(frozen=True, order=True)
class EventRange:
    first: int
    count: int

    @property
    def end(self) -> int:
        return self.first + self.count


def split(total: int, size: int) -> list:
    """Consecutive ranges of `size` events from event 0; the last may be shorter."""
    if total < 1 or size < 1:
        raise LayoutError(f"a split needs a positive total and size: {total}, {size}")
    return [EventRange(first, min(size, total - first)) for first in range(0, total, size)]


def check_ranges(found, total: int) -> None:
    """Every event index 0 to total - 1 in exactly one range. Refuses, by name, a duplicate, an overlap, a gap, a missing range and a range
    outside the bin; returns None when complete."""
    items = list(found)
    if any(r.count < 1 or r.first < 0 for r in items):
        raise LayoutError("a range is empty or starts before event 0")
    if any(r.end > total for r in items):
        raise LayoutError(f"a range holds events outside the bin (0 to {total - 1})")
    counted = collections.Counter(items)
    doubled = sorted(r for r, n in counted.items() if n > 1)
    if doubled:
        raise LayoutError(f"duplicate range {doubled[0].first}-{doubled[0].end - 1}")
    ordered = sorted(items)
    for before, after in zip(ordered, ordered[1:]):
        if after.first < before.end:
            raise LayoutError(f"overlap of {before.first}-{before.end - 1} and {after.first}-{after.end - 1}")
        if after.first > before.end:
            raise LayoutError(f"gap: events {before.end}-{after.first - 1} are in no range")
    if not ordered or ordered[0].first != 0 or ordered[-1].end != total:
        start = ordered[0].first if ordered else total
        end = ordered[-1].end if ordered else total
        raise LayoutError(f"missing range: events 0-{start - 1} or {end}-{total - 1} are in no range (top-up never: a failed task)")


@dataclass(frozen=True)
class RangeRecord:
    """What a range task leaves for the collection: its bin, its range, the global event indices its product holds, the product's SHA-256, the
    SHA-256 of the stratum file it was cut from and of its own range input (fix round 1, I7), and the Slurm attempt (job and task ID)."""
    workflow: str
    fixture_id: int
    block: int
    stratum: int
    first: int
    count: int
    events: tuple
    product_sha256: str
    stratum_sha256: str
    input_sha256: str
    attempt: str

    def to_json(self) -> str:
        return json.dumps({**asdict(self), "events": list(self.events)}, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "RangeRecord":
        doc = json.loads(text)
        names = {f for f in cls.__dataclass_fields__}
        if not isinstance(doc, dict) or set(doc) != names:
            raise LayoutError(f"a range record has exactly the keys {sorted(names)}")
        return cls(**{**doc, "events": tuple(doc["events"])})


PRODUCT_KINDS = ("jsonl", "t07-record")


def product_events(content: bytes, kind: str) -> int:
    """The events a product holds, read from the product itself: a JSON Lines product (T08, T09) by its event lines, each numbered 0, 1, ... in
    order, and its end line's count, which must agree; a T07 finding record by its event lines and its end record. A truncated product is
    refused."""
    if kind not in PRODUCT_KINDS:
        raise LayoutError(f"product kind {kind} is not one of {PRODUCT_KINDS}")
    text = content.decode("utf-8")
    if kind == "jsonl":
        _, events, end = _jsonl(text)
        try:
            numbers = [json.loads(line).get("event") for line in events]
            counted = json.loads(end).get("events")
        except ValueError as error:
            raise LayoutError(f"the product is not JSON Lines: {error}") from None
        if numbers != list(range(len(events))) or counted != len(events):
            raise LayoutError(f"the product's event lines ({len(events)}) and its end line ({counted}) disagree, or are out of order")
        return len(events)
    lines = text.split("\n")
    if lines[-1] != "" or not lines[-2].startswith("end "):
        raise LayoutError("the record ends before its end record")
    events = sum(1 for line in lines if line.startswith("event "))
    if int(lines[-2].split(" ")[1]) != events:
        raise LayoutError(f"the record's end record counts {lines[-2].split(' ')[1]} events, the record holds {events}")
    return events


def check_bin(records, expected, total: int = EVENTS_PER_BIN, products=None, kind: str = "jsonl") -> list:
    """The collection's check of one bin before scoring (fix round 1, I7): every record of the expected bin (a BinIdentity: workflow, fixture,
    block, stratum) and of one stratum file; the ranges complete; each record's events exactly its range; and, read from the products themselves
    (products: first event of the range -> the product's bytes), each product's SHA-256 its record's and its event count the range's. A
    truncated or mismatched product is refused, never scored as a shorter bin. Returns 0..total-1."""
    records = list(records)
    key = (expected.workflow, expected.fixture_id, expected.block, expected.stratum)
    bins = {(r.workflow, r.fixture_id, r.block, r.stratum) for r in records}
    if bins and bins != {key}:
        raise LayoutError(f"records of another bin than the expected one bin {key}: {sorted(bins)}")
    if len({r.stratum_sha256 for r in records}) > 1:
        raise LayoutError("the ranges were cut from more than one stratum file")
    check_ranges([EventRange(r.first, r.count) for r in records], total)
    for r in records:
        if tuple(r.events) != tuple(range(r.first, r.first + r.count)):
            raise LayoutError(f"range {r.first}-{r.first + r.count - 1} lists events other than its own")
    if products is None:
        raise LayoutError("the products must be read: the records alone do not show what the products hold")
    for r in records:
        content = products.get(r.first)
        if content is None:
            raise LayoutError(f"missing range: the product of {r.first}-{r.first + r.count - 1} is absent")
        if sha256_bytes(content) != r.product_sha256:
            raise LayoutError(f"the product of {r.first}-{r.first + r.count - 1} is not the one its record names (SHA-256)")
        held = product_events(content, kind)
        if held != r.count:
            raise LayoutError(f"the product of {r.first}-{r.first + r.count - 1} holds {held} events, not {r.count}: refused, never a short bin")
    return [event for r in sorted(records, key=lambda r: r.first) for event in r.events]


@dataclass(frozen=True)
class BinCollection:
    status: str        # "complete" or "missing"
    reason: str
    records: tuple


def collect_bin(expected, ranges, attempts, products, *, kind: str = "jsonl", total: int = EVENTS_PER_BIN) -> BinCollection:
    """One bin at the collection (fix round 1, I3), which runs with afterany on every task of the workflow, so it runs whatever failed:
    attempts maps each planned range to its attempts in order, (verdict of classify_attempt, RangeRecord or None); select_attempt picks the
    counted one (blocks 11 and 12: only attempts that drew or fitted nothing may precede it); check_bin then checks the bin with the products.
    Any refusal makes the bin "missing", with the reason: the scoring step writes section 10's "required output missing" records for it
    (missing_bin_records), and scores only a complete bin."""
    try:
        chosen = []
        for span in ranges:
            tried = list(attempts.get(span, ()))
            if not tried:
                raise LayoutError(f"missing range: {span.first}-{span.end - 1} has no attempt")
            index = select_attempt([verdict for verdict, _ in tried], block=expected.block)
            record = tried[index][1]
            if record is None or (record.first, record.count) != (span.first, span.count):
                raise LayoutError(f"missing range: the counted attempt of {span.first}-{span.end - 1} left no record of its range")
            chosen.append(record)
        check_bin(chosen, expected, total, products, kind)
    except LayoutError as error:
        return BinCollection("missing", str(error), ())
    return BinCollection("complete", "", tuple(chosen))


def missing_bin_records(identity, gates, reason: str) -> list:
    """Section 10's "Required output missing, so the test cannot be computed": an inconclusive record of every gate of an incomplete bin."""
    from tests.adapters import t04_evaluation_core as core
    return [core.missing_output(gate, identity, statistic, f"the bin is incomplete at the collection: {reason}") for gate, statistic in gates]


# ---- Running a script: its own result line, never an exit code alone (fix round 2).

# How a task starts a Python script that imports its siblings: -B (no bytecode), -s (no user site) and -E (no PYTHON* variables), so the run is
# isolated from the environment while the script's own folder stays on sys.path. -I is refused for such a script: in Python 3.11 and later it
# implies -P (safe path), so the folder is dropped and a sibling import fails (job 7590464, t07-memory; the Freeze-B run's rate-check).
SCRIPT_FLAGS = ("-B", "-s", "-E")
# Each script's result line (the line that says how the run ended), for the tasks and collections of the evaluation (E6c).
RESULT_LINES = {
    "t07_fake_rate.py run": r"^RESULT (ok|failed|refused):",
    "t07_fake_rate.py check": r"^(OK|REFUSED|REJECTED) ",
    "t08_fixture_files.py": r'^\{.*"status": "[a-z-]+"',
    "calo_cluster.py": r'^\{.*"status": "[a-z-]+"',
    "t09_fixture_files.py": r'^\{.*"status": "[a-z-]+"',
    "photon_likelihood.py": r'^\{.*"status": "[a-z-]+"',
    "t09_truth_start.py": r"^RESULT \{",
    "fbrun_tools.py classify": r"^CLASSIFY job ",
    "fbrun_tools.py t07-comparator": r"^RESULT comparator (ok|failed):",
}
SCRIPT_STATES = ("ok", "negative", "crashed")


def classify_script_run(exit_code: int, run_text: str, result_pattern: str) -> tuple:
    """How a script's run ended: (state, result line). "crashed" when the run_text holds a traceback, when the script's own result line is absent,
    or when the exit code is outside core/status.py's 0-3 (core/status.py: the run's outcome cannot be classified, incomplete, exit 3); else "ok"
    at exit 0 and "negative" at any other exit with its result line (a refusal or a failed check the script itself reports). A
    ModuleNotFoundError at import is a crash, never a negative reading."""
    import re
    lines = run_text.splitlines()
    found = [line for line in lines if re.search(result_pattern, line)]
    if "Traceback (most recent call last)" in run_text or not found or exit_code not in (0, 1, 2, 3):
        why = "a traceback" if "Traceback (most recent call last)" in run_text else ("no result line" if not found else f"exit {exit_code}")
        return "crashed", why
    return ("ok" if exit_code == 0 else "negative"), found[-1]


# ---- Earlier attempts.

EVENTS_ENTERED = ("draws-started", "fit-started")   # fix round 1, I4: a draw, or evaluation events entering a recipe (a range or scoring task)


def classify_attempt(state: str, exit_code: int, elapsed: str, milestones) -> tuple:
    """As fbrun_tools.py classify, from sacct (state, exit code, elapsed) and the milestones file (None if there is none): (verdict, why).
    One addition (fix round 1, I4): the milestone fit-started, written by a task that fits or scores events it did not draw (a T09 range task,
    a scoring task), counts as draws-started, so such a task's failure is never NO-DRAW once evaluation events entered it."""
    base = state.split()[0]
    if milestones is None and elapsed == "00:00:00" and base in ("CANCELLED", "PENDING"):
        return "NEVER-RAN", f"Slurm state {state} with no elapsed time and no milestones: it never started, nothing drawn"
    marks = set(milestones or ())
    if "first-reading" in marks:
        return "NOT-REPEATABLE", "the milestone first-reading is present: an output was read"
    if base == "COMPLETED" and exit_code == 0:
        return "NO-FAILURE", "completed, exit 0"
    if not marks & set(EVENTS_ENTERED):
        return "NO-DRAW", f"Slurm state {state}, exit {exit_code}, before any draw or fit: no event entered; fix and resubmit, not a repeat"
    if base in INFRASTRUCTURE:
        return "REPEATABLE", f"Slurm state {state}: an infrastructure failure, no output read"
    if base in RESOURCE:
        return "REPEATABLE-WITH-NEW-REQUEST", f"Slurm state {state}: the request was too small, no output read; the new request is the user's (K10)"
    if exit_code == 3:
        return "REPEATABLE", "exit 3: the task could not set itself up, no output read"
    if base == "CANCELLED":
        return "NOT-REPEATABLE", f"Slurm state {state}: a cancellation is the user's to rule on"
    return "NOT-REPEATABLE", f"Slurm state {state}, exit {exit_code}: a step of compute or a check failed, not infrastructure"


def select_attempt(verdicts, *, block: int) -> int:
    """The index of the counted attempt of one task: the last, which must be NO-FAILURE. Earlier attempts must have drawn and fitted nothing
    (NO-DRAW, NEVER-RAN); on a Freeze-B block (U-B12) a REPEATABLE one is accepted too. On blocks 11 and 12 no repeat after a draw or a fit
    started (v4 3.4, "A failure stands"; O6, settled): never looser than block 2."""
    verdicts = list(verdicts)
    if not verdicts or verdicts[-1] != "NO-FAILURE":
        raise LayoutError("missing range: the last attempt of the task did not complete, a failed task (top-up never)")
    allowed = NOTHING_DRAWN + (REPEATS_ON_FREEZE_B if block in FREEZE_B_BLOCKS else ())
    for index, verdict in enumerate(verdicts[:-1]):
        if verdict not in allowed:
            raise LayoutError(f"missing range: attempt {index} is {verdict}; on block {block} only {', '.join(allowed)} may precede the counted attempt")
    return len(verdicts) - 1


# ---- Range files (choice (b)).

def t09_readout_range(content: bytes, first: int, count: int) -> bytes:
    """A light-readout/1 file of events first .. first + count - 1 of a stratum's readout, by the recipe's own writer."""
    from light_recipe import readout
    full = readout.read_bytes(content)
    if count < 1 or first < 0 or first + count > full.events:
        raise LayoutError(f"range {first}+{count} is outside the readout's {full.events} events")
    part = slice(first, first + count)
    return readout.readout_bytes(full.state[part], full.charge[part], full.time[part], full.saturated[part], full.header["threshold"],
                                 full.header["saturation_charge"])


def t09_truth_range(full_path, first: int, count: int, readout_sha256: str, out_path) -> None:
    """The truth of the same events, for the scoring-side truth-start fit: per-event arrays sliced, the header's events and readout_sha256 those
    of the range readout; other arrays (the dead channels) and the key order kept."""
    with numpy.load(full_path, allow_pickle=False) as npz:
        names = list(npz.files)
        arrays = {name: npz[name] for name in names}
    header = json.loads(str(arrays["header"]))
    events = header["events"]
    if count < 1 or first < 0 or first + count > events:
        raise LayoutError(f"range {first}+{count} is outside the truth file's {events} events")
    header.update(events=count, readout_sha256=readout_sha256)
    out = {"header": numpy.array(json.dumps(header, sort_keys=True))}
    for name in names[1:]:
        value = arrays[name]
        out[name] = value[first:first + count] if name != "dead_channels" and value.ndim >= 1 and value.shape[0] == events else value
    with open(out_path, "wb") as stream:
        numpy.savez(stream, **out)


def t08_cells_range(content: bytes, first: int, count: int) -> bytes:
    """A calo-cells/1 file of events first .. first + count - 1 of a stratum's cells, by the recipe's own writer (the payloads are per stratum)."""
    from calo_recipe import cell_input
    full = cell_input.read_cells(content)
    events = full.raw.shape[0]
    if count < 1 or first < 0 or first + count > events or full.header["format"] != cell_input.CELLS_FORMAT:
        raise LayoutError(f"range {first}+{count} is outside the cells file's {events} events, or the file is not {cell_input.CELLS_FORMAT}")
    part = slice(first, first + count)
    return cell_input.cells_bytes(full.raw[part], full.live[part], full.saturated[part], raw_unit=full.header["raw_unit"], readout=full.header["readout"])


# ---- Merged range products equal the full product.

def _jsonl(text: str) -> tuple:
    lines = text.split("\n")
    if lines[-1] != "" or len(lines) < 3:
        raise LayoutError("a JSON Lines product has a header, its events and an end line, and ends with a newline")
    return lines[0], lines[1:-2], lines[-2]


def compare_jsonl_ranges(full_text: str, parts, dumps) -> list:
    """Defects, empty when equal: every line of the full product round-trips through dumps, and each range product's event line i, its
    "event" renumbered to first + i, is the full product's line byte for byte; the ranges cover the full product's events once, in order."""
    defects = []
    _, full_events, _ = _jsonl(full_text)
    for g, line in enumerate(full_events):
        if dumps(json.loads(line)) != line:
            defects.append(f"event {g}: the full product's line does not round-trip; byte equality cannot be read through renumbering")
    covered = []
    for first, text in parts:
        _, events, end = _jsonl(text)
        if json.loads(end).get("events") != len(events):
            defects.append(f"range from {first}: the end line counts {json.loads(end).get('events')} events, the range holds {len(events)}")
        for i, line in enumerate(events):
            g = first + i
            doc = json.loads(line)
            if doc.get("event") != i:
                defects.append(f"range from {first}: line {i} is event {doc.get('event')}, not {i}")
                continue
            doc["event"] = g
            if g >= len(full_events):
                defects.append(f"event {g}: beyond the full product's {len(full_events)} events")
            elif dumps(doc) != full_events[g]:
                defects.append(f"event {g}: the range line differs from the full product's")
            covered.append(g)
    if covered != list(range(len(full_events))):
        defects.append(f"the ranges cover events {covered[:3]}... ({len(covered)}), not 0 to {len(full_events) - 1} once in order")
    return defects


def _t07_body(content: bytes, kind: str) -> tuple:
    if kind == "data":
        import t07_fixture_files as files
        layout = files.DATA_HEADER
    else:
        import t07_truth_files as truth
        layout = truth.TRUTH_HEADER
    header = numpy.frombuffer(content[:layout.itemsize], dtype=layout)[0]
    return int(header["event_count"]), content[layout.itemsize:]


def compare_t07_bodies(full: bytes, parts, kind: str) -> list:
    """T07 data (kind "data") or truth ("truth") files: the range files' bodies, in order, concatenate to the full file's body byte for byte,
    and their event counts add up (the headers differ in count, and the truth header in the data file's SHA-256)."""
    count, body = _t07_body(full, kind)
    pieces, total, expected_first = [], 0, 0
    defects = []
    for first, content in parts:
        if first != expected_first:
            defects.append(f"a {kind} range starts at {first}, expected {expected_first}")
        n, piece = _t07_body(content, kind)
        pieces.append(piece)
        total += n
        expected_first = first + n
    if total != count:
        defects.append(f"{kind}: the ranges hold {total} events, the full file {count}")
    if b"".join(pieces) != body:
        defects.append(f"{kind}: the ranges' bodies are not the full file's body")
    return defects


_T07_RECORD_LINES = ("event", "candidate", "vertexing", "vertex", "vertex-track")


def _renumber_t07(line: str, local: int, offset: int) -> str:
    """A T07 record or product line of local ordinal `local`, as the full run writes it (ordinal local + offset): keys event-<o>- and the
    ordinal field of event, candidate, vertexing, vertex and track lines."""
    tokens = line.split(" ")
    target = local + offset
    tokens = [t.replace(f"event-{local}-", f"event-{target}-") if t.startswith(f"event-{local}-") else t for t in tokens]
    kind = tokens[0]
    position = {"event": 1, "vertexing": 1, "candidate": 2, "vertex": 2, "track": 2}.get(kind)
    if position is not None:
        if tokens[position] != str(local):
            raise LayoutError(f"a {kind} line of event {local} carries ordinal {tokens[position]}")
        tokens[position] = str(target)
    return " ".join(tokens)


def _t07_record_events(text: str) -> list:
    """Per event, its lines (event line, candidates, vertexing, vertices, their tracks), in order; header and end lines left out."""
    events = []
    for line in text.split("\n"):
        kind = line.split(" ", 1)[0]
        if kind == "event":
            events.append([line])
        elif kind in _T07_RECORD_LINES:
            if not events:
                raise LayoutError("a record line before the first event")
            events[-1].append(line)
    return events


def compare_t07_records(full_text: str, parts) -> list:
    """The finding records (acts-tracking-finding-record/1 or /2) of the ranges, renumbered, equal the full run's event blocks line for line."""
    full = _t07_record_events(full_text)
    defects, covered = [], []
    for first, text in parts:
        for local, lines in enumerate(_t07_record_events(text)):
            g = first + local
            try:
                renumbered = [_renumber_t07(line, local, first) for line in lines]
            except LayoutError as error:
                defects.append(f"event {g}: {error}")
                continue
            if g >= len(full) or renumbered != full[g]:
                defects.append(f"event {g}: the range record differs from the full run's")
            covered.append(g)
    if covered != list(range(len(full))):
        defects.append(f"the ranges cover {len(covered)} events of the full record's {len(full)}, or out of order")
    return defects


def _t07_product_sections(text: str) -> dict:
    sections = collections.OrderedDict()
    for line in text.split("\n"):
        kind = line.split(" ", 1)[0]
        if kind in ("track", "state", "parameters", "output", "residual", "measurement", "residual-covariance"):
            sections.setdefault(kind, []).append(line)
    return sections


def _event_of(line: str) -> int:
    key = line.split(" ")[1]
    return int(key.split("-")[1])


def compare_t07_products(full_text: str, parts) -> list:
    """acts-tracking-product/1 of the ranges (every event in the product): per section (track, state, parameters, ...), the renumbered lines of
    the ranges, concatenated in range order, equal the full product's lines of that section."""
    full = _t07_product_sections(full_text)
    merged = collections.OrderedDict((kind, []) for kind in full)
    defects = []
    for first, text in parts:
        for kind, lines in _t07_product_sections(text).items():
            for line in lines:
                try:
                    merged.setdefault(kind, []).append(_renumber_t07(line, _event_of(line), first))
                except (LayoutError, ValueError, IndexError) as error:
                    defects.append(f"{kind} line of the range from {first}: {error}")
    for kind in set(full) | set(merged):
        if full.get(kind, []) != merged.get(kind, []):
            defects.append(f"{kind}: the ranges' lines are not the full product's ({len(merged.get(kind, []))} against {len(full.get(kind, []))})")
    return defects


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _numbering_free(line: str) -> str:
    """A T07 record line with its event numbering blanked (event-<o>- keys and the ordinal fields): what renumbering may change."""
    tokens = [("event-#-" + t.split("-", 2)[2]) if t.startswith("event-") and t.count("-") >= 2 and t.split("-")[1].isdigit() else t
              for t in line.split(" ")]
    position = {"event": 1, "vertexing": 1, "candidate": 2, "vertex": 2, "track": 2}.get(tokens[0])
    if position is not None and len(tokens) > position:
        tokens[position] = "#"
    return " ".join(tokens)


def classify_t07_ranges(full_text: str, again_text: str, parts) -> tuple:
    """Position by position: valid only where the files hold their events in event-index order (hand-made records). The job uses
    classify_t07_by_index (fix round 2): the T07 generator's files do not. Fix round 1, I6: why T07's range records differ from one full run, if they do. (class, detail):
    - "nondeterminism": two full runs of the same events differ;
    - "equal": the ranges, renumbered, equal the full run;
    - "renumbering defect": the differing lines are equal once the numbering is blanked (the harness's renumbering is at fault);
    - "position dependence": they differ in a value (an event's result depends on its place in the file or on other events)."""
    if again_text != full_text:
        first, second = _t07_record_events(full_text), _t07_record_events(again_text)
        differ = [g for g, (x, y) in enumerate(zip(first, second)) if x != y]
        return "nondeterminism", f"two full runs differ in {len(differ) + abs(len(first) - len(second))} events, first {differ[:3]}"
    defects = compare_t07_records(full_text, parts)
    if not defects:
        return "equal", "every range event equals the full run's, renumbered"
    full = _t07_record_events(full_text)
    value_differs = []
    for first, text in parts:
        for local, lines in enumerate(_t07_record_events(text)):
            g = first + local
            if g >= len(full):
                value_differs.append(g)
                continue
            if [_numbering_free(line) for line in lines] != [_numbering_free(line) for line in full[g]]:
                value_differs.append(g)
    if value_differs:
        return "position dependence", f"{len(value_differs)} events differ in a value, first {value_differs[:3]}"
    return "renumbering defect", f"{len(defects)} defects, all in the numbering only"


# ---- T07 ranges, event for event by the truth's event index (fix round 2).
# Job 7590464 showed that the T07 generator writes each file's events in an order of its own (the full run's file is not the ranges' files
# concatenated: event indices 65, 24, 145, ... in the full file, 24, 17, 27, ... in the range from 0): the event's identity is its position in
# its file (A09), and positions are not comparable across files. So T07's ranges are compared event for event through the truth file's
# event_index: the same index must carry the same data hits, the same truth record, and the same finding-record block and product lines once
# the local ordinal is renumbered to the full file's position of that index.

def t07_event_indices(truth_content: bytes) -> list:
    """The truth file's event_index of each position in the file."""
    import io as _io
    import t07_truth_files as truth
    import t07_fixture_files as files
    stream = _io.BytesIO(truth_content)
    header = numpy.frombuffer(stream.read(truth.TRUTH_HEADER.itemsize), dtype=truth.TRUTH_HEADER)[0]
    indices = []
    for _ in range(int(header["event_count"])):
        head = files.take_records(stream, truth.TRUTH_EVENT, 1, "truth")[0]
        indices.append(int(head["event_index"]))
        stream.read(truth.VERTEX.itemsize * int(head["vertex_count"]) + truth.TRACK.itemsize * int(head["track_count"]))
    return indices


def _t07_truth_events(truth_content: bytes) -> list:
    import io as _io
    import t07_truth_files as truth
    import t07_fixture_files as files
    stream = _io.BytesIO(truth_content)
    header = numpy.frombuffer(stream.read(truth.TRUTH_HEADER.itemsize), dtype=truth.TRUTH_HEADER)[0]
    events = []
    for _ in range(int(header["event_count"])):
        head = files.take_records(stream, truth.TRUTH_EVENT, 1, "truth")[0]
        tail = stream.read(truth.VERTEX.itemsize * int(head["vertex_count"]) + truth.TRACK.itemsize * int(head["track_count"]))
        events.append(head.tobytes() + tail)
    return events


def _t07_data_events(data_content: bytes) -> list:
    import io as _io
    import t07_fixture_files as files
    stream = _io.BytesIO(data_content)
    header = numpy.frombuffer(stream.read(files.DATA_HEADER.itemsize), dtype=files.DATA_HEADER)[0]
    events = []
    for _ in range(int(header["event_count"])):
        head = files.take_records(stream, files.DATA_EVENT, 1, "data")[0]
        events.append(head.tobytes() + stream.read(files.HIT.itemsize * int(head["hit_count"])))
    return events


def _renumber_to(line: str, local: int, target: int) -> str:
    return _renumber_t07(line, local, target - local)


def _t07_product_by_event(text: str) -> dict:
    """{(section, event ordinal): [lines]} of a T07 product."""
    found = collections.defaultdict(list)
    for kind, lines in _t07_product_sections(text).items():
        for line in lines:
            found[(kind, _event_of(line))].append(line)
    return found


def compare_t07_by_index(full: dict, parts, renumber=True) -> list:
    """full: {"t07data", "t07truth", "record", "product"} -> bytes of one full run; parts: [(first, the same of a range run)]. Defects, empty when
    every event index of the ranges is the full run's, once each, with equal data hits, truth record, finding-record block and product lines
    (renumbered from the range file's position to the full file's)."""
    defects = []
    full_index = t07_event_indices(full["t07truth"])
    position_of = {g: p for p, g in enumerate(full_index)}
    full_data, full_truth = _t07_data_events(full["t07data"]), _t07_truth_events(full["t07truth"])
    full_record = _t07_record_events(full["record"].decode())
    full_product = _t07_product_by_event(full["product"].decode())
    seen = []
    for first, files_of in parts:
        index = t07_event_indices(files_of["t07truth"])
        if sorted(index) != list(range(first, first + len(index))):
            defects.append(f"the range from {first} holds event indices other than {first}-{first + len(index) - 1}")
        hits, truth = _t07_data_events(files_of["t07data"]), _t07_truth_events(files_of["t07truth"])
        record = _t07_record_events(files_of["record"].decode())
        product = _t07_product_by_event(files_of["product"].decode())
        for q, g in enumerate(index):
            seen.append(g)
            p = position_of.get(g)
            if p is None:
                defects.append(f"event index {g}: not in the full run")
                continue
            if hits[q] != full_data[p]:
                defects.append(f"event index {g}: data hits differ")
            if truth[q] != full_truth[p]:
                defects.append(f"event index {g}: truth record differs")
            change = (lambda line: _renumber_to(line, q, p)) if renumber else (lambda line: line)
            try:
                if [change(line) for line in record[q]] != full_record[p]:
                    defects.append(f"event index {g}: finding-record block differs")
                for kind in ("track", "state", "parameters"):
                    if [change(line) for line in product.get((kind, q), [])] != full_product.get((kind, p), []):
                        defects.append(f"event index {g}: product {kind} lines differ")
            except LayoutError as error:
                defects.append(f"event index {g}: {error}")
    if sorted(seen) != sorted(full_index):
        defects.append(f"the ranges hold {len(seen)} event indices, the full run {len(full_index)}, or not the same ones")
    return defects


def classify_t07_by_index(full: dict, again: dict, parts) -> tuple:
    """As classify_t07_ranges, event for event by index: nondeterminism (two full runs differ in data, truth, record or product events), equal,
    renumbering defect (equal with the numbering blanked), position dependence (a value differs)."""
    a_events = (_t07_data_events(full["t07data"]), _t07_truth_events(full["t07truth"]), _t07_record_events(full["record"].decode()),
                sorted(_t07_product_by_event(full["product"].decode()).items()))
    b_events = (_t07_data_events(again["t07data"]), _t07_truth_events(again["t07truth"]), _t07_record_events(again["record"].decode()),
                sorted(_t07_product_by_event(again["product"].decode()).items()))
    if a_events != b_events:
        return "nondeterminism", "two full runs of the same events differ"
    defects = compare_t07_by_index(full, parts)
    if not defects:
        return "equal", "every event index of the ranges equals the full run's, renumbered to its position"
    if any("data hits" in d or "truth record" in d or "event indices" in d or "not in the full run" in d for d in defects):
        return "draw differs", f"{len(defects)} defects, first: {defects[0]}"
    if all("finding-record" in d or "carries ordinal" in d for d in defects):
        loose = []
        full_index = t07_event_indices(full["t07truth"])
        position_of = {g: p for p, g in enumerate(full_index)}
        full_record = _t07_record_events(full["record"].decode())
        for first, files_of in parts:
            record = _t07_record_events(files_of["record"].decode())
            for q, g in enumerate(t07_event_indices(files_of["t07truth"])):
                if [_numbering_free(line) for line in record[q]] != [_numbering_free(line) for line in full_record[position_of[g]]]:
                    loose.append(g)
        if not loose:
            return "renumbering defect", f"{len(defects)} defects, all in the numbering only"
    return "position dependence", f"{len(defects)} defects, first: {defects[0]}"


# ---- The evaluation plan and its cost (closed form).

CPU_CLASS = "AMD EPYC 9645 96-Core Processor"   # U-W7: the evaluation runs on the Freeze-B run's CPU class; every task is pinned to it
MAX_MEMORY_PER_CPU_MB = 7900                     # the partition's MaxMemPerCPU is 7,967 (t07.sh); the Freeze-B run's T07 request
# Recorded costs, wall seconds per event on the AMD EPYC 9645 hosts (U-W7's class), upper values; each cites its record.
T07_SCORING_FACTOR = 1.35   # freeze-b-proposal.md 8.5: job 7551619 step finding, 594 CPU-s against 444 s of cost lines
T07_NOISE_PER_EVENT = {lvl: (find + gen + comparator) / 3000 * T07_SCORING_FACTOR for lvl, (find, gen, comparator) in   # job 7551619 VERTEX-COST, TRUTH-SEEDED-COST
                       enumerate(((3.2, 0.6, 2.5), (8.5, 1.7, 5.6), (61.4, 5.6, 18.1)))}
T07_REFIT_PER_TRACK = 26.8 / 18000                         # job 7551619 REFIT-COST, o1: 25.9-26.8 s per 18,000 tracks
T07_TRACKS_PER_EVENT = (6, 12, 36)                         # o1 recorded (18,000 per 3,000 events); o2, o3 the proposal 8.5 scaling (965 s per 36,000 events)
T07_CLEAN_FIND_PER_EVENT = {lvl: (find + 1.0) / 3000 * T07_SCORING_FACTOR for lvl, find in enumerate((2.6, 5.1, 16.6))}  # job 7551619 VERTEX-COST
T07_REFIT_PER_EVENT = {lvl: T07_REFIT_PER_TRACK * tracks * T07_SCORING_FACTOR for lvl, tracks in enumerate(T07_TRACKS_PER_EVENT)}
# T07 memory (fix round 1, I5): MaxRSS of the clean refit by events of an o3 bin. The Freeze-B run: 8,012,452 kB for the 3,000-event bins
# (collect-7585958.out, "t07 refit"); the E6a job adds 3,000 and 12,000 block-1 events (t07-memory step) and its numbers go here.
T07_REFIT_PEAK_MEMORY = {3000: 8012452}   # MaxRSS in kB, by events
T07_TASK_CPUS, T07_TASK_MEMORY_MB = 2, MAX_MEMORY_PER_CPU_MB   # as the Freeze-B run (t07.sh: 2 x 7,900 MB, WORKERS=1)
T07_MEMORY_MARGIN = 0.9
T07_REFIT_CANDIDATES = (12000, 6000, 4000, 3000, 2000, 1500, 1000)
T08_PER_EVENT = 331 / 45000                                # the Freeze-B run, job 7585955: 5 min 31 s for 45,000 events, its checks included
# The Freeze-B run, sacct elapsed per 3,000 events (block 2): jobs 7585956 (step 1: multistart, truth-start, readings, check-product; E1a in the
# dead control, E1b in main-B4-r0.4-0.7) and 7585957 (step 2: topology, its check and readings). The commands behind them are in
# collect-7585958.out (fit-multistart 1,767-2,339 s, check-multistart 79-96 s, readings 79-94 s, truth-start 105-123 s, topology 6,323-8,129 s,
# check-topology 169-183 s per 3,000 events): the sums include each task's own start-up, so the per-event values are upper ones.
T09_STEP1_SECONDS = {"main-B1-r0.0-0.4": 2390, "main-B1-r0.4-0.7": 2576, "main-B1-r0.7-0.9": 2975, "main-B2-r0.0-0.4": 2222, "main-B2-r0.4-0.7": 2395,
                     "main-B2-r0.7-0.9": 2844, "main-B3-r0.0-0.4": 2162, "main-B3-r0.4-0.7": 2296, "main-B3-r0.7-0.9": 2721, "main-B4-r0.0-0.4": 2101,
                     "main-B4-r0.4-0.7": 4082, "main-B4-r0.7-0.9": 2656, "dead-B3": 4351, "saturation-B3": 2840, "two-source": 2051}
T09_STEP2_SECONDS = {"main-B1-r0.0-0.4": 7418, "main-B1-r0.4-0.7": 8047, "main-B1-r0.7-0.9": 8322, "main-B2-r0.0-0.4": 7483, "main-B2-r0.4-0.7": 7853,
                     "main-B2-r0.7-0.9": 8121, "main-B3-r0.0-0.4": 7381, "main-B3-r0.4-0.7": 7877, "main-B3-r0.7-0.9": 8178, "main-B4-r0.0-0.4": 6525,
                     "main-B4-r0.4-0.7": 7465, "main-B4-r0.7-0.9": 7905, "two-source": 3308}
T09_GENERATION_PER_EVENT = 1.3 / 3000      # the Freeze-B run's draw-* commands: 0.7-1.3 s per 3,000 events (collect-7585958.out, t09-ms draw-*)
T09_GENERATION_CHECK_SECONDS = 47.4        # the generator check (v4 2.1) each generation task runs first: 25.3-47.4 s (collect, block6-generator-check)
# Start-up per task: manifest and frozen-file checks, interpreter start. An assumption for T08 and T09 range tasks (no record isolates it); the
# E6a job fits the T09 commands' fixed and per-event parts at two sizes (COST-FIT lines) and the T07 steps' walls.
START_UP_SECONDS = {"T07": 60, "T08": 30, "T09": 30}
# Scoring per bin: a budget. T07 from job 7474461's pull table: 600 CPU-s for 2.2e10 object-replicates (both statistics), 2.7e-8 s each; an o3
# clean bin's about 5.7e6 objects over its pull statistics x 1,000 replicates x 1.4 (log n at 432,000 against 12,000 objects): about 215 s,
# so 900 s is the upper budget (E6b replaces it from its job; the E6a pull replay prints its own rate).
SCORING_SECONDS = {"T07": 900, "T08": 120, "T09": 300}
COLLECTION_SECONDS = 300   # per workflow: sacct, every product hashed and read (an assumption)
SUMMARY_SECONDS = 120
T07_BUILD_SECONDS, T07_BUILD_CPUS = 86 + 7 + 60, 6    # job 7584388: configure 7 s, build 86 s on 6 CPUs, and its checks
T09_RANGE_EVENTS = 500
T07_RANGE_EVENTS = 12000
T08_RANGE_EVENTS = 12000


def t07_refit_range(measured=None, *, cpus: int = T07_TASK_CPUS, memory_mb: int = T07_TASK_MEMORY_MB) -> int:
    """The largest refit range (events of one clean bin) whose MaxRSS fits the T07 request with a 10 % margin. MaxRSS at a size is the measured
    value, or the linear interpolation between the two measured sizes around it, or beyond the largest measured size the proportional
    extrapolation from it (memory taken as proportional to events, the conservative reading). If 12,000 fits, the refit is one range per bin;
    else it is split by range and the plan says so."""
    measured = dict(T07_REFIT_PEAK_MEMORY if measured is None else measured)
    budget_kb = cpus * memory_mb * 1024 * T07_MEMORY_MARGIN
    sizes = sorted(measured)

    def estimate(size):
        if size in measured:
            return measured[size]
        below, above = [s for s in sizes if s < size], [s for s in sizes if s > size]
        if below and above:
            a, b = below[-1], above[0]
            return measured[a] + (measured[b] - measured[a]) * (size - a) / (b - a)
        anchor = below[-1] if below else above[0]
        return measured[anchor] * size / anchor
    for size in T07_REFIT_CANDIDATES:
        if estimate(size) <= budget_kb:
            return size
    raise LayoutError("no refit range fits the T07 request: the request is the user's (K10)")


@dataclass(frozen=True)
class Task:
    name: str
    kind: str
    events: int
    per_event_seconds: float
    overhead_seconds: float
    depends: tuple
    cpus: int = 1
    bin: tuple = ()
    span: EventRange | None = None
    memory_mb: int = 6000            # per CPU: the Freeze-B run's 6,000 MB for T08 and T09 (MaxRSS at most 1.15 GB, collect)
    dependency: str = "afterok"      # afterok with --kill-on-invalid-dep=yes, or afterany (the collections and summaries)
    cpu_class: str = CPU_CLASS

    @property
    def wall_seconds(self) -> float:
        return self.events * self.per_event_seconds + self.overhead_seconds


@dataclass
class Plan:
    tasks: list
    notes: tuple = ()
    by_name: dict = field(init=False)

    def __post_init__(self):
        self.by_name = {task.name: task for task in self.tasks}
        if len(self.by_name) != len(self.tasks):
            raise LayoutError("two tasks share a name")

    def cpu_hours(self) -> float:
        """Billing: allocated CPUs x elapsed."""
        return sum(task.wall_seconds * task.cpus for task in self.tasks) / 3600

    def overhead_hours(self) -> float:
        return sum(task.overhead_seconds * task.cpus for task in self.tasks) / 3600

    def longest_chain_seconds(self) -> float:
        done = {}

        def finish(name):
            if name not in self.by_name:
                raise LayoutError(f"a task depends on {name}, which the plan does not hold")
            if name not in done:
                task = self.by_name[name]
                done[name] = task.wall_seconds + max((finish(d) for d in task.depends), default=0.0)
            return done[name]
        return max((finish(t.name) for t in self.tasks), default=0.0)

    def task_counts(self) -> dict:
        return dict(collections.Counter(task.kind for task in self.tasks))

    def ranges_by_bin(self) -> dict:
        found = collections.defaultdict(list)
        for task in self.tasks:
            if task.span is not None and task.kind != "T07 refit":
                found[task.bin].append(task.span)
        return dict(found)


T08_LABELS = [(8001, s, f"main-E{s // 3 + 1}-{('iso', 'far', 'near')[s % 3]}") for s in range(12)] + [(8002, 0, "edge-E3"), (8003, 0, "dead-E3"), (8004, 0, "saturation-E4")]
T09_LABELS = [(9001, s, f"main-B{s // 3 + 1}-{('r0.0-0.4', 'r0.4-0.7', 'r0.7-0.9')[s % 3]}") for s in range(12)] + [(9002, 0, "dead-B3"), (9003, 0, "saturation-B3"), (9004, 0, "two-source")]


def evaluation_plan(*, block: int, t07_range: int = T07_RANGE_EVENTS, t08_range: int = T08_RANGE_EVENTS, t09_range: int = T09_RANGE_EVENTS,
                    refit_measured=None) -> Plan:
    """The evaluation of one attempt (block 11 or 12) as tasks with dependencies, all pinned to U-W7's CPU class:
    - T07: one build; a task per (fixture, stratum, range) with the generator's --first-event (one range per bin), 2 CPUs x 7,900 MB and
      WORKERS=1 as the Freeze-B run; the clean refit by range when 12,000 events do not fit (t07_refit_range), each refit range task after its
      bin task;
    - T08: a task per sample; T09: one generation task per sample (the whole stratum), then a task per range (multistart, truth-start,
      topology where the sample has it), afterok on its generation with --kill-on-invalid-dep=yes;
    - per workflow a collection with afterany on every task of the workflow (fix round 1, I3): attempt selection and check_bin per bin;
      "required output missing" records for an incomplete bin; then per bin a scoring task after the collection (it scores a complete bin only);
      per workflow a summary with afterany on its scoring tasks (it calls workflow_outcome)."""
    if block not in EVALUATION_BLOCKS:
        raise LayoutError(f"block {block} is not an evaluation block (section 3.2: 11 and 12)")
    refit_range = t07_refit_range(refit_measured)
    notes = [f"T07 refit range {refit_range} events" + (" (one per bin)" if refit_range >= EVENTS_PER_BIN else
             f": the clean refit is split by range, 12,000 events do not fit {T07_TASK_CPUS} x {T07_TASK_MEMORY_MB} MB"),
             f"every task pinned to {CPU_CLASS} (U-W7): the all-at-once wall needs as many such CPUs as tasks"]
    tasks = [Task("T07 build", "T07 build", 0, 0.0, T07_BUILD_SECONDS, (), T07_BUILD_CPUS)]
    work = {"T07": ["T07 build"], "T08": [], "T09": []}
    bins = {"T07": [], "T08": [], "T09": []}
    for fixture in (7001, 7002):
        for stratum in range(12):
            level = stratum % 3
            per_event = T07_NOISE_PER_EVENT[level] if fixture == 7002 else T07_CLEAN_FIND_PER_EVENT[level]
            for span in split(EVENTS_PER_BIN, t07_range):
                name = f"T07 {fixture} s{stratum} {span.first}-{span.end - 1}"
                tasks.append(Task(name, "T07 bin", span.count, per_event, START_UP_SECONDS["T07"], ("T07 build",), T07_TASK_CPUS,
                                  (7, fixture, stratum), span, T07_TASK_MEMORY_MB))
                work["T07"].append(name)
                if fixture == 7001:
                    for part in split(span.count, refit_range):
                        piece = EventRange(span.first + part.first, part.count)
                        refit = f"T07 refit {fixture} s{stratum} {piece.first}-{piece.end - 1}"
                        tasks.append(Task(refit, "T07 refit", piece.count, T07_REFIT_PER_EVENT[level], START_UP_SECONDS["T07"], (name,), T07_TASK_CPUS,
                                          (7, fixture, stratum), piece, T07_TASK_MEMORY_MB))
                        work["T07"].append(refit)
            bins["T07"].append(f"{fixture} s{stratum}")
    for fixture, stratum, label in T08_LABELS:
        for span in split(EVENTS_PER_BIN, t08_range):
            name = f"T08 {label} {span.first}-{span.end - 1}"
            tasks.append(Task(name, "T08 sample", span.count, T08_PER_EVENT, START_UP_SECONDS["T08"], (), 1, (8, fixture, stratum), span))
            work["T08"].append(name)
        bins["T08"].append(label)
    for fixture, stratum, label in T09_LABELS:
        generation = f"T09 generate {label}"
        tasks.append(Task(generation, "T09 generation", EVENTS_PER_BIN, T09_GENERATION_PER_EVENT, START_UP_SECONDS["T09"] + T09_GENERATION_CHECK_SECONDS, ()))
        work["T09"].append(generation)
        per_event = (T09_STEP1_SECONDS[label] + T09_STEP2_SECONDS.get(label, 0)) / 3000
        for span in split(EVENTS_PER_BIN, t09_range):
            name = f"T09 {label} {span.first}-{span.end - 1}"
            tasks.append(Task(name, "T09 range", span.count, per_event, START_UP_SECONDS["T09"], (generation,), 1, (9, fixture, stratum), span))
            work["T09"].append(name)
        bins["T09"].append(label)
    for workflow in ("T07", "T08", "T09"):
        collection = f"{workflow} collection"
        tasks.append(Task(collection, f"{workflow} collection", 0, 0.0, COLLECTION_SECONDS, tuple(work[workflow]), dependency="afterany"))
        scores = []
        for label in bins[workflow]:
            tasks.append(Task(f"{workflow} score {label}", f"{workflow} scoring", 0, 0.0, SCORING_SECONDS[workflow], (collection,)))
            scores.append(tasks[-1].name)
        tasks.append(Task(f"{workflow} summary", f"{workflow} summary", 0, 0.0, SUMMARY_SECONDS, tuple(scores), dependency="afterany"))
    return Plan(tasks, tuple(notes))
