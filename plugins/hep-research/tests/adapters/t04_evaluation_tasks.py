#!/usr/bin/env python3
"""The evaluation's task runner for T07, T08 and T09 on blocks 11 and 12 (D4 stage E6c; d4-e6c-brief.md, item 3). Scoring side; the recipes never
import it. The job scripts under <private>/jobs/evaluation/ start it, one operation per Slurm task, always with layout.SCRIPT_FLAGS; it starts
every recipe and fixture script with the same flags and judges each run by that script's own result line (layout.classify_script_run): a
traceback or a missing result line is a crash (exit 3, CRASHED), never a negative reading (E6a fix round 2).

Sections cited are of t04-values-v4.md (Freeze A). The block is one constant of the job scripts (lib.sh BLOCK), passed as --block and checked
here first (check_block): 11 or 12 only (v4 3.2: evaluation attempts 1 and 2; the attempt and its level follow from the block, core
level_of_block); any other block is refused before anything is read or drawn. Every operation ends with one line
`RESULT <operation> ok|failed|rejected|crashed|incomplete` and exits by core/status.py: 0 ok, 1 a step failed, 2 a rejected input, 3 crashed or
incomplete (a harness task that must be rerun; it draws nothing).

Operations, on the layout of E6a (t04_evaluation_layout.evaluation_plan):
  t08-sample    one T08 sample (v4 4.2; 15), 12,000 events: the whole stratum by the unchanged fixture tool (milestone draws-started first), then
                (milestone fit-started, before the first event enters the recipe: E6a re-review N3) the recipe's reconstruct, check-product and
                A38's accounting; a range record. A sheet stop (check-product exit 1: a cell counted twice) or a failed accounting is kept in
                stop.json with the script's own line, then the task fails (fix round 1, M1).
  t08-checks    the checks rerun at evaluation (the user, 2026-11-12, "Rerun at evaluation": once inside the submission, at the frozen hash, on
                their own v4 3.2 block, 1): main E3 iso, far and near at 3,000 block-1 events, CAI-T08-1 (fixed membership, both gain roles) and
                its planted-fraction control, CAI-T08-2 (re-reconstruction, recorded), and the reference selection; checks.json.
  t09-generate  one T09 sample (15), 12,000 events: the whole stratum, every 500-event range file cut here (E6a M7), the dead control's ranges
                relabelled dead as live-unhit (E1a); generation.json.
  t09-range     one range of 500 events (24 per sample): its files' SHA-256 against generation.json, then fit-started, the multistart fit and
                check-product (exit 1: the probability-sum stop, kept in stop.json), the truth-start comparator (main bins only: the controls'
                were never read, fix round 1, M6), topology and its check (main, two-source), E1a's fit (dead), E1b's (stratum 10).
  t09-fixed-points  v4 9.3's likelihood check and per-channel sum at the 50 fixed points of block 6 (t09_fixed_points.py), deterministic.
  t07-bin, t07-refit, t07-slices, t07-negative-cases, t07-checks, T07 collect, score and summary: E6b's commands (t07_evaluation_scoring),
                each call mapped here to E6b's operation and options (t07_call; E6 merge stage, E6c re-review R2: index to fixture and
                stratum, E6b's names, no option E6b's parser lacks) and run by E6b's t07_interface. T07's collection is one E6b collect per bin
                (attempts classified here), its scoring one score-bin per bin into the common scores folder with a scored.json marker per bin,
                its slices one score-slices per fixture and parameter once every bin of the fixture has its marker, and its summary E6b's,
                reached only when every bin and slice marker and both checks tasks' counted results are there (else SUMMARY INCOMPLETE).
  collect       per workflow, afterany on every task: attempts classified (layout.classify_attempt from sacct and the milestones file), the
                counted one selected (layout.select_attempt), each bin checked with its products (layout.collect_bin); an incomplete bin is
                "missing" with its reason; recorded stops carried. collection.json is written last, with "finished": true.
  score         one bin: a complete bin scored (t08_scoring.score_sample, t09_scoring.score_bin; checks), a missing bin given v4 10's "required
                output missing" records; T09's index 15 is the pool, read from the nine B2-B4 bins' reduced pool.npz files. Its outputs are
                written only when it ends ok, with scored.json naming the collection's SHA-256 (fix round 1, I1).
  summary       per workflow: every bin's records, the checks (with the T08 checks task's and the fixed points' counted attempts) and
                core.workflow_outcome with the workflow's required checks (fix round 1, I2). A harness task that crashed or was refused (a bin
                without scored.json, a collection that did not finish, a fixed-points or checks run without its result, a required check
                absent) is SUMMARY INCOMPLETE, exit 3, with no OUTCOME line: it is rerun (no draw), never read as a fail (fix round 1, I1).
  plan, names   the plan and its resource total (layout.evaluation_plan), for the user's approval (K10); the attempts lines' task names.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.adapters import t04_evaluation_core as core  # noqa: E402
from tests.adapters import t04_evaluation_layout as layout  # noqa: E402
from tests.adapters import t04_bin_scorer as bin_scorer  # noqa: E402

EXIT_OK, EXIT_FAILED, EXIT_REJECTED, EXIT_CRASHED = 0, 1, 2, 3
RESULT_WORDS = {EXIT_OK: "ok", EXIT_FAILED: "failed", EXIT_REJECTED: "rejected", EXIT_CRASHED: "incomplete"}
EVENTS = layout.EVENTS_PER_BIN
T09_RANGE_EVENTS = layout.T09_RANGE_EVENTS
T09_RANGES = layout.split(EVENTS, T09_RANGE_EVENTS)
T08_SAMPLES = layout.T08_LABELS
T09_SAMPLES = layout.T09_LABELS
T09_POOL_INDEX = len(T09_SAMPLES)          # the T09 scoring task of the pooled mirrored and reversed tests (v4 9.4)
T09_E1B_STRATUM = 10
T08_FIXTURE_NAMES = {8001: "main", 8002: "edge", 8003: "dead", 8004: "saturation"}
T09_FIXTURE_NAMES = {9001: "main", 9002: "dead", 9003: "saturation", 9004: "two-source"}
# The checks' block (the user, 2026-11-12: "Rerun at evaluation ... on their own v4 3.2 blocks (1 and 6)"): CAI-T08 on block 1 (its interface
# runs, as job 7554028), the generator check and the fixed points on block 6. Fixed, not a switch.
CHECKS_SOURCE = "rerun-at-evaluation"
CHECKS_BLOCK = 1
CHECKS_EVENTS = 3000
CHECKS_SAMPLES = ((8001, 6, "main-E3-iso"), (8001, 7, "main-E3-far"), (8001, 8, "main-E3-near"))


class TaskError(ValueError):
    """A rejected input of a task (exit 2)."""


class ScriptCrash(RuntimeError):
    """A script ended with a traceback or without its own result line (exit 3)."""


class StepFailed(RuntimeError):
    """A step ended with its own negative result line (exit 1)."""


class Incomplete(RuntimeError):
    """A harness task's output is absent or not finished: the summary is incomplete (exit 3), never a workflow fail."""


class DeadlineReached(Incomplete):
    """A subprocess of the task outlived the task's deadline (layout.subprocess_timeout) and was stopped: incomplete, and the milestone
    stopped-at-deadline is written (integration review M1)."""


def check_block(block) -> int:
    """v4 3.2: blocks 11 and 12 are evaluation attempts 1 and 2; any other block is refused before anything is read or drawn. Returns the
    attempt (core.ATTEMPT_OF_BLOCK)."""
    try:
        block = int(block)
    except (TypeError, ValueError):
        raise TaskError(f"block {block!r} is not a number") from None
    if block not in layout.EVALUATION_BLOCKS:
        raise TaskError(f"block {block} is refused: the evaluation draws and scores blocks 11 and 12 only (v4 3.2)")
    return core.ATTEMPT_OF_BLOCK[block]


def checks_source(value: str = CHECKS_SOURCE) -> str:
    """The user's answer (2026-11-12): the deterministic and CAI checks are rerun at evaluation; the other reading (the Freeze-B run's and the
    latest T07 records) is refused."""
    if value != "rerun-at-evaluation":
        raise TaskError(f"checks source {value!r} is refused: the user's answer is 'rerun-at-evaluation' (2026-11-12)")
    return value


# ---- the T07 interface (E6b's command line: d4-e6b-report.md, "The interface for E6c"; E6 merge stage, E6c re-review R2)

T07_BINS = tuple((fixture_id, stratum) for fixture_id in (7001, 7002) for stratum in range(12))   # t07-bin index: 0-11 clean s, 12-23 noise s - 12
T07_REFIT_PIECES = tuple(layout.split(EVENTS, layout.t07_refit_range()))                       # 3 pieces of 4,000 events (E6a's measured refit)
T07_REFITS = tuple((stratum, piece) for stratum in range(12) for piece in T07_REFIT_PIECES)    # t07-refit index 3 s + p: clean stratum s, piece p
T07_NEGATIVE_FOLDER = ROOT / "tests" / "adapters" / "data" / "t07-negative-cases"
T07_CHECK_TASKS = (("T07 negative cases", "t07-negative-cases", "negative-checks.json"), ("T07 checks", "t07-checks", "deterministic-checks.json"))


def _t07():
    from tests.adapters import t07_evaluation_scoring
    return t07_evaluation_scoring


def t07_slice_tasks() -> tuple:
    """t07-slices index k: (fixture, parameter), 5 per fixture (E6b's one score-slices per fixture and parameter)."""
    return tuple((fixture_id, name) for fixture_id in (7001, 7002) for name in _t07().PARAMETERS)


def _index(index, count: int, what: str) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < count:
        raise TaskError(f"{what} {index!r}: 0 to {count - 1}")
    return index


def t07_call(operation: str, *, block: int, **a) -> tuple:
    """One T07 call of this runner as E6b's (operation, keywords) for t07_evaluation_scoring.t07_interface: the index mapped to fixture and
    stratum (or refit piece, or slice task), E6b's own option names, and nothing E6b's parser does not define (its summary has no --out). Test:
    each call parses through E6b's build_parser."""
    if operation == "bin":
        fixture_id, stratum = T07_BINS[_index(a["index"], len(T07_BINS), "T07 bin")]
        return "bin", dict(block=block, fixture_id=fixture_id, stratum=stratum, first=0, count=EVENTS, build=a["build"], out=a["out"])
    if operation == "refit":
        stratum, piece = T07_REFITS[_index(a["index"], len(T07_REFITS), "T07 refit")]
        return "refit", dict(block=block, stratum=stratum, first=piece.first, count=piece.count, bin_dir=a["bin_dir"], build=a["build"], out=a["out"])
    if operation == "slices":
        fixture_id, name = t07_slice_tasks()[_index(a["index"], len(t07_slice_tasks()), "T07 slices task")]
        return "pool", dict(block=block, fixture_id=fixture_id, events=EVENTS, bins=a["scores"], out=a["scores"], parameters=name)
    if operation == "negative-cases":
        return "negative-cases", dict(block=block, build=a["build"], folder=T07_NEGATIVE_FOLDER, out=a["out"])
    if operation == "checks":
        return "checks", dict(block=block, build=a["build"], out=a["out"], workers=a.get("workers", 1))
    if operation == "collect":
        fixture_id, stratum = T07_BINS[_index(a["index"], len(T07_BINS), "T07 bin")]
        return "collect", dict(block=block, fixture_id=fixture_id, stratum=stratum, count=EVENTS, refit_range=layout.t07_refit_range(),
                               attempts=a["attempts"], out=a["out"])
    if operation == "score":
        fixture_id, stratum = T07_BINS[_index(a["index"], len(T07_BINS), "T07 bin")]
        if fixture_id == 7002 and not a.get("rate_record"):
            raise TaskError("a T07 noise bin needs the Freeze-B r_dev record (F2, v4 8.3): give --rate-record")
        return "score", dict(block=block, fixture_id=fixture_id, stratum=stratum, events=EVENTS, collection=a["collection"], out=a["scores"],
                             rate_record=a.get("rate_record") if fixture_id == 7002 else None)
    if operation == "summary":
        return "summary", dict(block=block, scores=a["scores"], checks=a["checks"])
    raise TaskError(f"no T07 call {operation}")


def t07_run(operation: str, **a) -> int:
    """E6b's command for one call (t07_call), in this process; it prints its own result line (RESULT t07-scoring ...); returns its exit code."""
    e6b_operation, keywords = t07_call(operation, **a)
    return _t07().t07_interface(e6b_operation, **keywords)


def _needs(value, what: str):
    if not value:
        raise TaskError(f"{what} is not given")
    return value


def _workers() -> int:
    return len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else 1


def _classified(rows, state_of) -> list:
    """[[verdict, folder]] of a task's attempts (layout.classify_attempt from sacct and each folder's milestones), as E6b's collect reads them."""
    found = []
    for job, folder in rows:
        state, code, elapsed = state_of(job)
        marks = Milestones(folder)
        found.append([layout.classify_attempt(state, code, elapsed, marks.names() if marks.path.exists() else None)[0], str(folder)])
    return found


def _sha_or_none(path) -> str | None:
    return sha256_file(path) if Path(path).is_file() else None


def t07_bin(block: int, index: int, out: Path, build) -> int:
    check_block(block)
    return t07_run("bin", block=block, index=index, build=_needs(build, "the T07 build (--t07-build)"), out=out)


def t07_refit(block: int, index: int, out: Path, build, attempts_file, *, state_of=None) -> int:
    """One refit piece of a clean bin, on the data file of its bin task's counted attempt (attempts.tsv, "T07 bin s")."""
    check_block(block)
    state_of = state_of or sacct_state
    build = _needs(build, "the T07 build (--t07-build)")
    stratum, _ = T07_REFITS[_index(index, len(T07_REFITS), "T07 refit")]
    rows = read_attempts(Path(_needs(attempts_file, "the attempts file (--attempts)"))).get(f"T07 bin {stratum}", [])
    bin_dir = counted_folder(rows, block, state_of)
    return t07_run("refit", block=block, index=index, bin_dir=bin_dir, build=build, out=out)


def t07_negative_cases(block: int, out: Path, build) -> int:
    check_block(block)
    return t07_run("negative-cases", block=block, build=_needs(build, "the T07 build (--t07-build)"), out=out)


def t07_checks(block: int, out: Path, build) -> int:
    check_block(block)
    return t07_run("checks", block=block, build=_needs(build, "the T07 build (--t07-build)"), out=out, workers=_workers())


def t07_collect(block: int, attempts_file: Path, out: Path, *, state_of=None) -> int:
    """T07's collection: per bin E6b's collect (the bin and, for a clean bin, its three refit pieces; attempts classified here), then
    collection.json, written last with "finished": true. A bin collect that is refused or fails leaves no collection.json (incomplete)."""
    check_block(block)
    state_of = state_of or sacct_state
    attempts = read_attempts(attempts_file)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "collection.json").exists():   # E6 merge review M7: a rerun that stops early leaves no earlier collection.json behind
        (out / "collection.json").unlink()
    bins = {}
    pieces = len(T07_REFIT_PIECES)   # E6 merge review M6: refit index pieces x s + p (submit.sh numbers them the same way, from the names)
    for index, (fixture_id, stratum) in enumerate(T07_BINS):
        label = f"T07 bin {index}"
        tried = {"bin": _classified(attempts.get(label, []), state_of), "refit": {}}
        if fixture_id == 7001:
            for p, piece in enumerate(T07_REFIT_PIECES):
                tried["refit"][str(piece.first)] = _classified(attempts.get(f"T07 refit {pieces * stratum + p}", []), state_of)
        attempts_path, document_path = out / f"t07-bin-{index}.attempts.json", out / f"t07-bin-{index}.json"
        attempts_path.write_text(json.dumps(tried, sort_keys=True) + "\n", encoding="utf-8")
        code = t07_run("collect", block=block, index=index, attempts=attempts_path, out=document_path)
        if code != EXIT_OK:
            return code
        document = json.loads(document_path.read_text(encoding="utf-8"))
        bins[label] = {"status": document["status"], "reason": document["reason"], "collection": str(document_path), "sha256": sha256_file(document_path)}
        print(f"COLLECT T07 block {block} {label} (fixture {fixture_id} stratum {stratum}): {document['status']}"
              + (f" ({document['reason']})" if document["reason"] else "") + (f"; refit {document['refit']['status']}" if "refit" in document else ""))
    (out / "collection.json").write_text(json.dumps({"workflow": "T07", "block": block, "bins": bins, "finished": True}, sort_keys=True, indent=1) + "\n",
                                         encoding="utf-8")
    return EXIT_OK


def t07_score(block: int, index: int, collection: Path, out: Path, rate_record) -> int:
    """One T07 bin: E6b's score-bin on its collection, into the common scores folder (Path(out).parent, which E6b's slices and summary read),
    then the bin's scored.json in out, written last (the summary's marker, E6c fix round 1, I1)."""
    check_block(block)
    bins = _collection(collection, "T07", block)
    label = f"T07 bin {_index(index, len(T07_BINS), 'T07 bin')}"
    entry = bins[label]
    if sha256_file(entry["collection"]) != entry["sha256"]:
        raise TaskError(f"{label}: its collection changed after the collection (SHA-256)")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    marker = out / "scored.json"
    if marker.exists():
        marker.unlink()
    scores = out.parent
    fixture_id, stratum = T07_BINS[index]
    scoring = _t07()
    records, slices = scores / scoring.records_name(fixture_id, block, stratum), scores / scoring.slices_name(fixture_id, block, stratum)
    for path in (records, slices):   # only this run's files may stand beside its marker
        if path.exists():
            path.unlink()
    code = t07_run("score", block=block, index=index, collection=entry["collection"], scores=scores, rate_record=rate_record)
    if code == EXIT_REJECTED and records.is_file() and slices.is_file():
        # E6 merge review M3 (the coordinator's ruling): E6b refused the bin's files and wrote v4 10's "required output missing" records. A
        # refused marker: the summary stays incomplete naming the bin and the refusal, for the coordinator; never a pass, never silently a fail.
        found = scoring.read_records(records)
        marker.write_text(json.dumps({"bin": label, "refused": True, "reason": found[0].reason if found else "no record",
                                      "collection_sha256": sha256_file(collection), "bin_collection_sha256": entry["sha256"],
                                      "records_sha256": _sha_or_none(records), "slices_sha256": _sha_or_none(slices)}, sort_keys=True) + "\n",
                          encoding="utf-8")
        return code
    if code != EXIT_OK:
        return code
    marker.write_text(json.dumps({"bin": label, "collection_sha256": sha256_file(collection), "bin_collection_sha256": entry["sha256"],
                                  "records_sha256": _sha_or_none(scores / scoring.records_name(fixture_id, block, stratum)),
                                  "slices_sha256": _sha_or_none(scores / scoring.slices_name(fixture_id, block, stratum))}, sort_keys=True) + "\n",
                      encoding="utf-8")
    return EXIT_OK


def _t07_bin_marker(scores: Path, index: int, tag: str | None, block: int) -> dict:
    fixture_id, stratum = T07_BINS[index]
    scoring = _t07()
    marker = Path(scores) / f"bin-{index}" / "scored.json"
    if not marker.exists():
        raise Incomplete(f"the scoring of T07 bin {index} left no scored.json: it crashed or was refused; rerun it (no draw)")
    doc = json.loads(marker.read_text(encoding="utf-8"))
    if doc.get("refused"):
        raise Incomplete(f"T07 bin {index} was refused at scoring ({doc.get('reason')}): the coordinator's, not a rerun; never a pass or a fail "
                         "(E6 merge review M3)")
    if (tag is not None and doc.get("collection_sha256") != tag) or doc.get("records_sha256") is None \
            or _sha_or_none(Path(scores) / scoring.records_name(fixture_id, block, stratum)) != doc.get("records_sha256") \
            or _sha_or_none(Path(scores) / scoring.slices_name(fixture_id, block, stratum)) != doc.get("slices_sha256"):
        raise Incomplete(f"the scoring of T07 bin {index} is not of this collection, or its files changed; rerun it (no draw)")
    return doc


def t07_slices(block: int, index: int, scores, out: Path) -> int:
    """One fixture's slices of one parameter (E6b's score-slices), once the scoring of each of the fixture's 12 bins left its marker; then
    scores/slices-<index>/scored.json, written last."""
    check_block(block)
    fixture_id, name = t07_slice_tasks()[_index(index, len(t07_slice_tasks()), "T07 slices task")]
    scores = Path(_needs(scores, "the T07 scores folder (--scores)"))
    members, member_slices = {}, {}
    for stratum in range(12):
        bin_index = T07_BINS.index((fixture_id, stratum))
        doc = _t07_bin_marker(scores, bin_index, None, block)
        members[bin_index], member_slices[bin_index] = doc["records_sha256"], doc["slices_sha256"]
    Path(out).mkdir(parents=True, exist_ok=True)
    marker = scores / f"slices-{index}" / "scored.json"
    if marker.exists():
        marker.unlink()
    code = t07_run("slices", block=block, index=index, scores=scores)
    if code != EXIT_OK:
        return code
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"slices": index, "fixture_id": fixture_id, "parameter": name, "bins": members, "bin_slices": member_slices,
                                  "records_sha256": _sha_or_none(scores / _t07().slice_records_name(fixture_id, block, (name,)))}, sort_keys=True) + "\n",
                      encoding="utf-8")
    return EXIT_OK


def t07_summary(block: int, scores: Path, collection: Path, out: Path, *, attempts_file: Path | None = None, state_of=None) -> int:
    """E6b's summary (section 10, the core's workflow_outcome with T07's required checks), reached only when the collection finished, every bin
    and slice task left its marker against it, and both checks tasks' counted attempts ended ok or failed with their checks file; else SUMMARY
    INCOMPLETE, exit 3, no outcome (E6c fix round 1, I1)."""
    check_block(block)
    state_of = state_of or sacct_state
    scores = Path(scores)
    try:
        _collection(collection, "T07", block)
        tag = sha256_file(collection)
        attempts = read_attempts(attempts_file) if attempts_file is not None and Path(attempts_file).exists() else {}
        bin_markers = {index: _t07_bin_marker(scores, index, tag, block) for index in range(len(T07_BINS))}
        for index, (fixture_id, name) in enumerate(t07_slice_tasks()):
            marker = scores / f"slices-{index}" / "scored.json"
            if not marker.exists():
                raise Incomplete(f"the slices task {index} left no scored.json: it crashed or was refused; rerun it (no draw)")
            doc = json.loads(marker.read_text(encoding="utf-8"))
            if _sha_or_none(scores / _t07().slice_records_name(fixture_id, block, (name,))) != doc.get("records_sha256") or doc.get("records_sha256") is None:
                raise Incomplete(f"the slices task {index}'s records changed after it ended; rerun it (no draw)")
            for stratum in range(12):   # E6 merge review M1: the slices read the member bins' current .slices.npz files
                bin_index = T07_BINS.index((fixture_id, stratum))
                if (doc.get("bin_slices") or {}).get(str(bin_index)) != bin_markers[bin_index].get("slices_sha256"):
                    raise Incomplete(f"the slices task {index} read another .slices.npz of T07 bin {bin_index} than its current scoring; rerun the "
                                     "slices (no draw)")
        files = []
        for name, operation, file in T07_CHECK_TASKS:
            folder = counted_single(attempts, name, block, state_of)
            task_result(folder, operation)
            if not (folder / file).exists():
                raise Incomplete(f"{name} in {folder} left no {file}; rerun it")
            files.append(str(folder / file))
    except Incomplete as error:
        print(f"SUMMARY INCOMPLETE T07 block {block}: {error}")
        return EXIT_CRASHED
    Path(out).mkdir(parents=True, exist_ok=True)
    return t07_run("summary", block=block, scores=scores, checks=",".join(files))


# ---- running scripts

@dataclasses.dataclass(frozen=True)
class Paths:
    """Where the scripts are: the three adapters' assets (the plugin's own by default) and the frozen generators and references (given at run time)."""
    calo: Path = ROOT / "adapters" / "calo-cluster" / "assets"
    light: Path = ROOT / "adapters" / "photon-likelihood" / "assets"
    t08_generator: Path | None = None
    t09_generator: Path | None = None
    reference_log: Path | None = None          # job 7479146's calc-t08-reference.log (t08_readings checks its SHA-256)
    reference_script: Path | None = None       # round5/calc-t08-reference.py (t08_scenarios.py reference-selection checks its SHA-256)


def result_pattern(script: Path, sub: str) -> str:
    name = script.name
    for key in (f"{name} {sub}", name):
        if key in layout.RESULT_LINES:
            return layout.RESULT_LINES[key]
    raise TaskError(f"{name} {sub}: no result line is known for this script; it may not run unchecked")


def run_script(script: Path, arguments, log: Path, *, ok=(0,)) -> tuple:
    """Start a Python script with layout.SCRIPT_FLAGS and judge it by its own result line: (exit code, result line, seconds). A crash raises
    ScriptCrash; a negative exit outside `ok` raises StepFailed."""
    arguments = [str(a) for a in arguments]
    pattern = result_pattern(Path(script), arguments[0] if arguments else "")
    started = time.monotonic()
    limit = layout.subprocess_timeout()
    try:
        done = subprocess.run([sys.executable, *layout.SCRIPT_FLAGS, str(script), *arguments], capture_output=True, text=True, timeout=limit)
    except subprocess.TimeoutExpired as expired:   # the task's deadline (layout.start_task): incomplete, never failed, nothing marked done
        partial = "".join(x.decode(errors="replace") if isinstance(x, bytes) else x for x in (expired.stdout or "", expired.stderr or ""))
        Path(log).write_text(partial + f"\nTIMED OUT after {limit:.0f} s (the task's deadline)\n", encoding="utf-8")
        raise DeadlineReached(f"{Path(script).name} {arguments[:1]} timed out after {limit:.0f} s (the task's deadline); log {log}") from None
    seconds = time.monotonic() - started
    text = done.stdout + done.stderr
    Path(log).write_text(text, encoding="utf-8")
    state, line = layout.classify_script_run(done.returncode, text, pattern)
    if state == "crashed":
        raise ScriptCrash(f"{Path(script).name} {arguments[:1]} crashed ({line}); log {log}")
    if state == "incomplete":   # E6 merge review (nit): exit 3 with its own line is incomplete (core/status.py), never a failed step
        raise ScriptCrash(f"{Path(script).name} {arguments[:1]} ended incomplete, exit 3 ({line}); log {log}")
    if done.returncode not in ok:
        raise StepFailed(f"{Path(script).name} {arguments[:1]} ended {state}, exit {done.returncode}: {line}")
    return done.returncode, line, seconds


def stop_or_fail(out: Path, check: str, code: int, line: str, *, stop: bool) -> None:
    """Fix round 1, M1: a recipe's negative result is kept in stop.json (the check, its own line, whether it is a sheet stop), then the task fails."""
    (Path(out) / "stop.json").write_text(json.dumps({"check": check, "line": line, "exit": code, "stop": stop}, sort_keys=True) + "\n", encoding="utf-8")
    raise StepFailed(f"{check}: {line}")


class Milestones:
    """The milestones file of one task attempt (the only file the collection reads before classifying it, as the Freeze-B run's lib.sh)."""

    def __init__(self, out: Path):
        self.path = Path(out) / "milestones.txt"

    def mark(self, name: str) -> None:
        if name not in self.names():
            with open(self.path, "a", encoding="utf-8") as stream:
                stream.write(f"{name} {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")

    def names(self) -> list:
        if not self.path.exists():
            return []
        return [line.split(" ", 1)[0] for line in self.path.read_text(encoding="utf-8").splitlines() if line]


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_record(out: Path, kind: str, record: layout.RangeRecord) -> None:
    folder = Path(out) / "records"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{kind}.json").write_text(record.to_json() + "\n", encoding="utf-8")


def attempt_name() -> str:
    job = os.environ.get("SLURM_ARRAY_JOB_ID") or os.environ.get("SLURM_JOB_ID") or "unset"
    task = os.environ.get("SLURM_ARRAY_TASK_ID")
    return f"{job}_{task}" if task is not None else job


# ---- T08

def t08_sample(block: int, index: int, out: Path, paths: Paths) -> int:
    check_block(block)
    if not 0 <= index < len(T08_SAMPLES):
        raise TaskError(f"T08 sample {index}: 0 to {len(T08_SAMPLES) - 1}")
    fixture_id, stratum, label = T08_SAMPLES[index]
    if paths.t08_generator is None:
        raise TaskError("the T08 generator is not given")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    marks = Milestones(out)
    tools = paths.calo / "fixture_tools"
    marks.mark("draws-started")
    run_script(tools / "t08_fixture_files.py", ["--generator", paths.t08_generator, "--fixture", T08_FIXTURE_NAMES[fixture_id], "--block", block,
                                                "--stratum", stratum, "--count", EVENTS, "--out-dir", out, "--stem", label], out / "generate.log")
    marks.mark("fit-started")
    product = out / f"{label}.product.jsonl"
    run_script(paths.calo / "calo_cluster.py", ["reconstruct", "--cells", out / f"{label}.cells", "--pedestal-payload", out / f"{label}.pedestal.json",
                                                "--gain-payload", out / f"{label}.gain.json", "--product", product, "--product-id",
                                                f"evaluation-b{block}-{label}"], out / "reconstruct.log", ok=(0, 1))
    code, line, _ = run_script(paths.calo / "calo_cluster.py", ["check-product", "--product", product], out / "check-product.log", ok=(0, 1))
    if code == 1:
        stop_or_fail(out, f"double-count {label}", code, line, stop=True)
    code, line, _ = run_script(tools / "t08_scenarios.py", ["accounting", "--cells", out / f"{label}.cells", "--pedestal-payload", out / f"{label}.pedestal.json",
                                                            "--gain-payload", out / f"{label}.gain.json", "--product", product, "--label", label],
                               out / "accounting.log", ok=(0, 1))
    if code == 1:
        stop_or_fail(out, f"A38 selection and accounting {label}", code, line, stop=False)
    cells_sha = sha256_file(out / f"{label}.cells")
    write_record(out, "product", layout.RangeRecord("T08", fixture_id, block, stratum, 0, EVENTS, tuple(range(EVENTS)), sha256_file(product),
                                                    cells_sha, cells_sha, attempt_name()))
    return EXIT_OK


def t08_checks(block: int, out: Path, paths: Paths) -> int:
    """CAI-T08-1 and -2 and the reference selection, rerun at evaluation on block 1 (CHECKS_BLOCK), as the Freeze-B run's t08.sh did on its samples.
    checks.json holds one core.CheckResult per name of t08_scoring.CHECK_TASK_NAMES."""
    check_block(block)
    checks_source()
    if paths.t08_generator is None or paths.reference_script is None:
        raise TaskError("the T08 generator and the frozen reference script are both needed")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    marks = Milestones(out)
    tools = paths.calo / "fixture_tools"
    cai = tools / "t08_cai.py"
    reco = paths.calo / "calo_cluster.py"
    cai1, cai2 = [], []
    marks.mark("draws-started")
    for fixture_id, stratum, label in CHECKS_SAMPLES:
        d = out / label
        d.mkdir(exist_ok=True)
        run_script(tools / "t08_fixture_files.py", ["--generator", paths.t08_generator, "--fixture", "main", "--block", CHECKS_BLOCK, "--stratum", stratum,
                                                    "--count", CHECKS_EVENTS, "--out-dir", d, "--stem", label], d / "generate.log")
        marks.mark("fit-started")
        run_script(cai, ["payloads", "--cells", d / f"{label}.cells", "--pedestal-payload", d / f"{label}.pedestal.json", "--gain-payload",
                         d / f"{label}.gain.json", "--out-dir", d, "--stem", label], d / "payloads.log")
        for role in ("multiply", "divide"):
            nominal, derived = d / f"{label}.nominal-{role}.product.jsonl", d / f"{label}.derived-{role}.product.jsonl"
            gain_nominal, gain_derived = d / f"{label}.nominal-{role}.gain.json", d / f"{label}.derived-{role}.gain.json"
            run_script(reco, ["reconstruct", "--cells", d / f"{label}.cells", "--pedestal-payload", d / f"{label}.pedestal.json", "--gain-payload",
                              gain_nominal, "--product", nominal, "--product-id", f"evaluation-b{block}-checks-{label}-nominal-{role}"], d / f"nominal-{role}.log")
            ok_nominal = run_script(reco, ["check-product", "--product", nominal], d / f"check-nominal-{role}.log", ok=(0, 1))[0] == 0
            code, line, _ = run_script(cai, ["fixed-membership", "--product", nominal, "--old-gain", gain_nominal, "--new-gain", gain_derived, "--out",
                                             d / f"cai1-{role}.jsonl", "--label", f"{label}-{role}"], d / f"cai1-{role}.log", ok=(0, 1))
            control, cline, _ = run_script(cai, ["fixed-membership", "--product", nominal, "--old-gain", gain_nominal, "--new-gain", gain_derived, "--out",
                                                 d / f"cai1-control-{role}.jsonl", "--label", f"{label}-{role}-control", "--plant-fraction-defect"],
                                           d / f"cai1-control-{role}.log", ok=(0, 1))
            cai1.append(ok_nominal and code == 0 and "RESULT PASS" in line and control == 1 and "RESULT FAIL" in cline)
            run_script(reco, ["reconstruct", "--cells", d / f"{label}.cells", "--pedestal-payload", d / f"{label}.pedestal.json", "--gain-payload",
                              gain_derived, "--product", derived, "--product-id", f"evaluation-b{block}-checks-{label}-derived-{role}"],
                       d / f"derived-{role}.log", ok=(0, 1))
            ok_derived = run_script(reco, ["check-product", "--product", derived], d / f"check-derived-{role}.log", ok=(0, 1))[0] == 0
            code, line, _ = run_script(cai, ["rereco", "--nominal", nominal, "--changed", derived, "--old-gain", gain_nominal, "--new-gain", gain_derived,
                                             "--out", d / f"cai2-{role}.jsonl", "--label", f"{label}-{role}"], d / f"cai2-{role}.log", ok=(0, 1))
            cai2.append(ok_derived and code == 0)
    code, line, _ = run_script(tools / "t08_scenarios.py", ["reference-selection", "--script", paths.reference_script], out / "reference-selection.log", ok=(0, 1))
    from tests.adapters import t08_scoring
    names = t08_scoring.CHECK_TASK_NAMES
    found = [core.CheckResult(names[0], "cai", "pass" if len(cai1) == 6 and all(cai1) else "fail"),
             core.CheckResult(names[1], "cai", "pass" if len(cai2) == 6 and all(cai2) else "fail"),
             core.CheckResult(names[2], "deterministic", "pass" if code == 0 and "PASS" in line else "fail")]
    (out / "checks.json").write_text(json.dumps([dataclasses.asdict(c) for c in found], sort_keys=True) + "\n", encoding="utf-8")
    for c in found:
        print(f"CHECK {c.kind} {c.name}: {c.result}")
    return EXIT_OK


# ---- T09

def t09_range_files(out: Path, first: int) -> dict:
    stem = Path(out) / "ranges" / f"r{first}"
    return {"readout": Path(f"{stem}.readout"), "truth": Path(f"{stem}.truth.npz"), "unhit": Path(f"{stem}.unhit.readout"),
            "unhit_record": Path(f"{stem}.unhit.relabel.json")}


def t09_generate(block: int, index: int, out: Path, paths: Paths) -> int:
    check_block(block)
    if not 0 <= index < len(T09_SAMPLES):
        raise TaskError(f"T09 sample {index}: 0 to {len(T09_SAMPLES) - 1}")
    fixture_id, stratum, label = T09_SAMPLES[index]
    if paths.t09_generator is None:
        raise TaskError("the T09 generator is not given")
    out = Path(out)
    (out / "ranges").mkdir(parents=True, exist_ok=True)
    marks = Milestones(out)
    tools = paths.light / "fixture_tools"
    marks.mark("draws-started")
    run_script(tools / "t09_fixture_files.py", ["--generator", paths.t09_generator, "--fixture", T09_FIXTURE_NAMES[fixture_id], "--block", block,
                                                "--stratum", stratum, "--count", EVENTS, "--out-dir", out, "--stem", label], out / "generate.log")
    full = (out / f"{label}.readout").read_bytes()
    stratum_sha = layout.sha256_bytes(full)
    ranges = []
    for span in T09_RANGES:
        files = t09_range_files(out, span.first)
        piece = layout.t09_readout_range(full, span.first, span.count)
        files["readout"].write_bytes(piece)
        entry = {"first": span.first, "count": span.count, "readout_sha256": layout.sha256_bytes(piece)}
        layout.t09_truth_range(out / f"{label}.truth.npz", span.first, span.count, entry["readout_sha256"], files["truth"])   # one- or two-source
        entry["truth_sha256"] = sha256_file(files["truth"])
        if fixture_id == 9002:
            run_script(tools / "t09_negative_checks.py", ["relabel-dead", "--readout", files["readout"], "--out", files["unhit"], "--record",
                                                          files["unhit_record"]], out / f"relabel-r{span.first}.log")
            entry["unhit_sha256"] = sha256_file(files["unhit"])
        ranges.append(entry)
    document = {"workflow": "T09", "fixture_id": fixture_id, "block": block, "stratum": stratum, "label": label, "stratum_sha256": stratum_sha,
                "truth_sha256": sha256_file(out / f"{label}.truth.npz"), "ranges": ranges, "attempt": attempt_name()}
    (out / "generation.json").write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    return EXIT_OK


def t09_range(block: int, index: int, range_index: int, generation: Path, out: Path, paths: Paths) -> int:
    check_block(block)
    if not 0 <= index < len(T09_SAMPLES) or not 0 <= range_index < len(T09_RANGES):
        raise TaskError(f"T09 sample {index} range {range_index}: samples 0 to {len(T09_SAMPLES) - 1}, ranges 0 to {len(T09_RANGES) - 1}")
    fixture_id, stratum, label = T09_SAMPLES[index]
    span = T09_RANGES[range_index]
    generation = Path(generation)
    document = json.loads((generation / "generation.json").read_text(encoding="utf-8"))
    if (document["fixture_id"], document["block"], document["stratum"]) != (fixture_id, block, stratum):
        raise TaskError(f"generation.json is fixture {document['fixture_id']} block {document['block']} stratum {document['stratum']}, not this task's")
    entry = document["ranges"][range_index]
    files = t09_range_files(generation, span.first)
    if (entry["first"], entry["count"]) != (span.first, span.count) or sha256_file(files["readout"]) != entry["readout_sha256"] \
            or sha256_file(files["truth"]) != entry["truth_sha256"]:
        raise TaskError(f"the range files of {span.first}-{span.end - 1} are not generation.json's (SHA-256)")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    marks = Milestones(out)
    like = paths.light / "photon_likelihood.py"
    tools = paths.light / "fixture_tools"
    name = f"evaluation-b{block}-{label}-r{span.first}"
    record = (lambda kind, product, input_sha: write_record(out, kind, layout.RangeRecord(
        "T09", fixture_id, block, stratum, span.first, span.count, tuple(range(span.first, span.end)), sha256_file(product),
        document["stratum_sha256"], input_sha, attempt_name())))

    def checked(product, log, extra=()):
        code, line, _ = run_script(like, ["check-product", "--product", product, *extra], out / log, ok=(0, 1))
        if code == 1:
            stop_or_fail(out, f"probability sum {label}", code, line, stop=True)
    marks.mark("fit-started")      # E6a re-review N3: before the first event of the range enters a recipe
    multistart = out / "multistart.product.jsonl"
    run_script(like, ["fit", "--readout", files["readout"], "--product", multistart, "--product-id", f"{name}-multistart", "--likelihood", "charge-time",
                      "--starts", "multistart"], out / "fit-multistart.log")
    checked(multistart, "check-multistart.log")
    record("multistart", multistart, entry["readout_sha256"])
    if fixture_id == 9001:
        truth_start = out / "truth-start.jsonl"
        run_script(tools / "t09_truth_start.py", ["fit", "--readout", files["readout"], "--truth", files["truth"], "--out", truth_start], out / "truth-start.log")
        record("truth-start", truth_start, entry["readout_sha256"])
    if fixture_id in (9001, 9004):
        topo = out / "topology.product.jsonl"
        run_script(like, ["topology", "--readout", files["readout"], "--h1-product", multistart, "--product", topo, "--product-id", f"{name}-topology"],
                   out / "topology.log")
        checked(topo, "check-topology.log")
        record("topology", topo, entry["readout_sha256"])
    if fixture_id == 9002:
        if sha256_file(files["unhit"]) != entry["unhit_sha256"]:
            raise TaskError("the relabelled range readout is not generation.json's")
        unhit = out / "unhit.multistart.product.jsonl"
        run_script(like, ["fit", "--readout", files["unhit"], "--product", unhit, "--product-id", f"{name}-unhit-multistart", "--likelihood",
                          "charge-time", "--starts", "multistart"], out / "fit-unhit.log")
        checked(unhit, "check-unhit.log")
        record("unhit", unhit, entry["unhit_sha256"])
    if fixture_id == 9001 and stratum == T09_E1B_STRATUM:
        config = paths.light / "t09-sphere-1-single-photon.configuration.json"
        single = out / "single-photon.product.jsonl"
        run_script(like, ["fit", "--readout", files["readout"], "--product", single, "--product-id", f"{name}-single-photon", "--configuration", config,
                          "--likelihood", "charge-time", "--starts", "multistart"], out / "fit-single-photon.log")
        checked(single, "check-single-photon.log", ("--configuration", config))
        code, _, _ = run_script(like, ["check-product", "--product", single], out / "check-single-photon-main.log", ok=(2,))
        if code != 2:
            raise StepFailed("the main reader did not refuse the single-photon product")
        record("single-photon", single, entry["readout_sha256"])
    return EXIT_OK


def t09_fixed_points(block: int, out: Path, paths: Paths) -> int:
    """v4 9.3 at the 50 fixed points of block 6 (deterministic; block 6's declared role, v4 3.2). Run once per attempt."""
    check_block(block)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if paths.t09_generator is None:
        raise TaskError("the T09 generator is not given")
    run_script(paths.light / "fixture_tools" / "t09_fixed_points.py", ["--generator", paths.t09_generator], out / "fixed-points.log", ok=(0, 1))
    return EXIT_OK


# ---- the collection

def t09_kinds(fixture_id: int, stratum: int) -> tuple:
    kinds = ["multistart"]
    if fixture_id == 9001:
        kinds.append("truth-start")
    if fixture_id in (9001, 9004):
        kinds.append("topology")
    if fixture_id == 9002:
        kinds.append("unhit")
    if fixture_id == 9001 and stratum == T09_E1B_STRATUM:
        kinds.append("single-photon")
    return tuple(kinds)


def product_name(kind: str) -> str:
    return {"multistart": "multistart.product.jsonl", "truth-start": "truth-start.jsonl", "topology": "topology.product.jsonl",
            "unhit": "unhit.multistart.product.jsonl", "single-photon": "single-photon.product.jsonl"}[kind]


def planned_bins(workflow: str) -> list:
    """(identity key, label, ranges, kinds) of every bin of a workflow."""
    if workflow == "T08":
        return [((8, f, s), label, [layout.EventRange(0, EVENTS)], ("product",)) for f, s, label in T08_SAMPLES]
    if workflow == "T09":
        return [((9, f, s), label, list(T09_RANGES), t09_kinds(f, s)) for f, s, label in T09_SAMPLES]
    raise TaskError(f"workflow {workflow}: the T07 bins are E6b's (t07_interface)")


def task_name(workflow: str, label: str, span: layout.EventRange) -> str:
    return f"{workflow} {label} {span.first}-{span.end - 1}"


SINGLE_TASKS = {"T09 fixed points": "t09-fixed-points", "T08 checks": "t08-checks"}


def read_attempts(path: Path) -> dict:
    """The submission's attempts file (submit.sh and any resubmission append to it): one line per attempt, "task name<TAB>job ID<TAB>folder",
    in submission order."""
    found = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            raise TaskError(f"an attempts line has three fields: {line!r}")
        found.setdefault(parts[0], []).append((parts[1], Path(parts[2])))
    return found


SACCT_TIMEOUT_SECONDS = 30   # one sacct query answers in about a second; the slurmdbd being slow is the case this bounds
SACCT_ATTEMPTS = 3           # then no answer: the collection or summary is incomplete (rerun, no draw), never a state guessed
SACCT_PAUSE_SECONDS = 10


def sacct_state(job: str, *, timeout: float = SACCT_TIMEOUT_SECONDS, attempts: int = SACCT_ATTEMPTS, pause: float = SACCT_PAUSE_SECONDS) -> tuple:
    """(state, exit code, elapsed) of one job or array task, from sacct: each query bounded by a short timeout (and the task's deadline), at
    most `attempts` queries; with no answer, Incomplete."""
    why = "no query made"
    for attempt in range(attempts):
        left = layout.subprocess_timeout()
        if left <= layout.MINIMUM_TIMEOUT_SECONDS:   # review M2: past the task's deadline, no query and no pause
            raise Incomplete(f"sacct not asked for {job}: the task's deadline has passed ({why}); rerun the task (no draw)")
        try:
            done = subprocess.run(["sacct", "-j", job, "-n", "-P", "-X", "-o", "JobID,State,ExitCode,Elapsed"], capture_output=True, text=True,
                                  timeout=min(timeout, left))
        except subprocess.TimeoutExpired:
            why = f"no answer in {min(timeout, left):.0f} s"
        else:   # review C1: an error answer or no row for the job is no answer, never a state
            rows = [line.split("|") for line in done.stdout.splitlines()]
            found = [fields for fields in rows if len(fields) == 4 and fields[0] == job]
            if done.returncode != 0 or done.stderr.strip():
                why = f"exit {done.returncode}: {done.stderr.strip()[:200]}"
            elif not found:
                why = "no row for the job"
            else:
                fields = found[0]
                return fields[1], int(fields[2].split(":")[0]), fields[3]
        if attempt + 1 < attempts:
            time.sleep(max(0.0, min(pause, layout.subprocess_timeout() - layout.MINIMUM_TIMEOUT_SECONDS)))
    raise Incomplete(f"sacct did not answer for {job} in {attempts} attempts (last: {why}); rerun the task (no draw), never a state guessed")


def counted_folder(rows, block: int, state_of, *, check_task: bool = False, notes: list | None = None) -> Path:
    """The folder of a task's counted attempt (layout.select_attempt over its attempts, classified from sacct and the milestones file);
    check_task: a named check task's rule (layout.select_attempt; the user, 2026-11-13); notes: each attempt that rule let precede the counted
    one, as (index, job, verdict), and the counted one's (index, job)."""
    verdicts = []
    for job, folder in rows:
        state, code, elapsed = state_of(job)
        marks = Milestones(folder)
        verdicts.append(layout.classify_attempt(state, code, elapsed, marks.names() if marks.path.exists() else None)[0])
    if not rows:
        raise layout.LayoutError("the task has no attempt")
    index = layout.select_attempt(verdicts, block=block, check_task=check_task)
    if notes is not None:
        notes += [(i, rows[i][0], v) for i, v in enumerate(verdicts[:index]) if v in layout.CHECK_TASK_REPEATS] + [(index, rows[index][0], None)]
    return Path(rows[index][1])


def _stops(rows) -> list:
    found = []
    for _, folder in rows:
        path = Path(folder) / "stop.json"
        if path.exists():
            found.append(json.loads(path.read_text(encoding="utf-8")))
    return found


def collect(workflow: str, block: int, attempts_file: Path, out: Path, *, state_of=sacct_state) -> int:
    check_block(block)
    if (Path(out) / "collection.json").exists():   # integration review M4: a rerun that stops early leaves no earlier collection.json, as T07's
        (Path(out) / "collection.json").unlink()
    attempts = read_attempts(attempts_file)
    bins = {}
    for key, label, spans, kinds in planned_bins(workflow):
        expected = core.BinIdentity(workflow, key[1], block, key[2])
        bin_status = {"status": "complete", "reason": "", "kinds": {}, "stops": []}
        for span in spans:
            bin_status["stops"] += _stops(attempts.get(task_name(workflow, label, span), []))
        generation = None
        if workflow == "T09":
            try:
                generation = counted_folder(attempts.get(f"T09 generate {label}", []), block, state_of)
                document = json.loads((generation / "generation.json").read_text(encoding="utf-8"))
                if (document["fixture_id"], document["block"], document["stratum"]) != (key[1], block, key[2]):
                    raise layout.LayoutError("generation.json is another sample's")
            except (layout.LayoutError, OSError, ValueError, KeyError) as error:
                bins[label] = {"status": "missing", "reason": f"generation: {error}", "kinds": {}, "stops": bin_status["stops"]}
                print(f"COLLECT {workflow} block {block} {label}: missing (generation: {error})")
                continue
            bin_status["generation"] = str(generation)
        for kind in kinds:
            tried, products = {}, {}
            for span in spans:
                rows = []
                for job, folder in attempts.get(task_name(workflow, label, span), []):
                    state, code, elapsed = state_of(job)
                    marks = Milestones(folder)
                    verdict, _ = layout.classify_attempt(state, code, elapsed, marks.names() if marks.path.exists() else None)
                    record_path = folder / "records" / f"{kind}.json"
                    record = layout.RangeRecord.from_json(record_path.read_text(encoding="utf-8")) if record_path.exists() else None
                    rows.append((verdict, record))
                    if record is not None:
                        product = folder / (f"{label}.product.jsonl" if workflow == "T08" else product_name(kind))
                        products[span.first] = (product, record)
                tried[span] = rows
            readable = {first: path.read_bytes() for first, (path, _) in products.items() if path.exists()}
            found = layout.collect_bin(expected, spans, tried, readable, kind="jsonl")
            readable = None
            if found.status == "complete" and generation is not None and {r.stratum_sha256 for r in found.records} != {document["stratum_sha256"]}:
                found = layout.BinCollection("missing", "the ranges were not cut from the counted generation's stratum file", ())
            if found.status != "complete":
                bin_status = {"status": "missing", "reason": f"{kind}: {found.reason}", "kinds": {}, "stops": bin_status["stops"]}
                break
            bin_status["kinds"][kind] = [{"first": r.first, "count": r.count, "product": str(products[r.first][0]), "sha256": r.product_sha256}
                                         for r in found.records]
        bins[label] = bin_status
        print(f"COLLECT {workflow} block {block} {label}: {bin_status['status']}" + (f" ({bin_status['reason']})" if bin_status["reason"] else ""))
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "collection.json").write_text(json.dumps({"workflow": workflow, "block": block, "bins": bins, "finished": True}, sort_keys=True,
                                                          indent=1) + "\n", encoding="utf-8")
    return EXIT_OK


# ---- scoring

def _collection(path: Path, workflow: str, block: int) -> dict:
    """The bins of a finished collection; a collection that did not finish is incomplete (it crashed: rerun it)."""
    path = Path(path)
    if not path.exists():
        raise Incomplete(f"the {workflow} collection left no collection.json: it crashed or was refused; rerun it (no draw)")
    document = json.loads(path.read_text(encoding="utf-8"))
    if (document.get("workflow"), document.get("block")) != (workflow, block):
        raise TaskError(f"the collection is {document.get('workflow')} block {document.get('block')}, not {workflow} block {block}")
    if document.get("finished") is not True:
        raise Incomplete(f"the {workflow} collection did not finish; rerun it (no draw)")
    return document["bins"]


def _verified(entries) -> list:
    """The products of a complete bin, each read again against the SHA-256 the collection checked."""
    out = []
    for entry in sorted(entries, key=lambda e: e["first"]):
        if sha256_file(entry["product"]) != entry["sha256"]:
            raise TaskError(f"{entry['product']} changed after the collection (SHA-256)")
        out.append(Path(entry["product"]))
    return out


def write_scores(out: Path, records, checks, lines, *, collection_sha256: str, label: str, extra=None) -> None:
    """The scoring task's outputs, then scored.json (the marker the summary needs; fix round 1, I1), written last."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    marker = out / "scored.json"
    if marker.exists():
        marker.unlink()
    (out / "records.json").write_text(json.dumps([bin_scorer.record_document(r) for r in records], sort_keys=True) + "\n", encoding="utf-8")
    (out / "checks.json").write_text(json.dumps([dataclasses.asdict(c) for c in checks], sort_keys=True) + "\n", encoding="utf-8")
    if extra is not None:
        import numpy
        numpy.savez(out / "pool.npz", **extra)
    for record in records:
        print(bin_scorer.record_line(record))
    for check in checks:
        print(f"CHECK {check.kind} {check.name}: {check.result}" + (" (stop)" if check.stop else ""))
    for line in lines:
        print(line)
    pool = out / "pool.npz"
    if extra is None and pool.exists():
        pool.unlink()
    marker.write_text(json.dumps({"bin": label, "collection_sha256": collection_sha256, "records": len(records), "checks": len(checks),
                                  "records_sha256": sha256_file(out / "records.json"), "checks_sha256": sha256_file(out / "checks.json"),
                                  "pool_sha256": sha256_file(pool) if extra is not None else None},   # fix round 2, R5
                                 sort_keys=True) + "\n", encoding="utf-8")


def score(workflow: str, block: int, index: int, collection: Path, out: Path, paths: Paths, *, rate_record=None) -> int:
    check_block(block)
    if workflow == "T07":
        return t07_score(block, index, collection, out, rate_record)
    bins = _collection(collection, workflow, block)
    tag = sha256_file(collection)
    if workflow == "T08":
        return score_t08(block, index, bins, out, paths, tag)
    return score_t09(block, index, bins, out, paths, tag, Path(out).parent)


def score_t08(block: int, index: int, bins: dict, out: Path, paths: Paths, tag: str) -> int:
    from tests.adapters import t08_scoring
    from calo_recipe import product as calo_product
    import t08_fixture_files
    if not 0 <= index < len(T08_SAMPLES):
        raise TaskError(f"T08 bin {index}: 0 to {len(T08_SAMPLES) - 1}")
    fixture_id, stratum, label = T08_SAMPLES[index]
    identity = core.BinIdentity("T08", fixture_id, block, stratum)
    entry = bins[label]
    if entry["status"] != "complete":
        write_scores(out, t08_scoring.missing_records(identity, entry["reason"]), [], [f"MISSING {identity.label}: {entry['reason']}"],
                     collection_sha256=tag, label=label)
        return EXIT_OK
    if paths.reference_log is None:
        raise TaskError("job 7479146's reference log is not given")
    log = Path(paths.reference_log).read_bytes()
    if hashlib.sha256(log).hexdigest() != t08_scoring.readings.REFERENCE_LOG_SHA256:
        raise TaskError("the reference log is not job 7479146's")
    reference = t08_scoring.readings.parse_reference(log.decode("utf-8"))
    product_paths = _verified(entry["kinds"]["product"])
    products = [calo_product.read_product(p) for p in product_paths]
    events, header = t08_scoring.merged_events(products)
    products = None
    folder = product_paths[0].parent
    truth_header, truth = t08_fixture_files.read_truth(folder / f"{label}.truth.npz")
    if truth_header["cells_sha256"] != header["input"]["sha256"]:
        raise TaskError("the truth file belongs to other cells than the product's")
    cells_content = (folder / f"{label}.cells").read_bytes()
    saturated = None
    if fixture_id == 8004:
        from calo_recipe import cell_input
        saturated = cell_input.read_cells(cells_content).saturated
    result = t08_scoring.score_sample(identity, events, truth_header, truth, reference, saturated=saturated, products_header=header)
    checks = t08_scoring.sample_checks(result)
    accounting = (folder / "accounting.log").read_text(encoding="utf-8")
    checks.append(core.CheckResult(f"A38 selection and accounting {result.kind.name}", "deterministic",
                                   "pass" if "selection-and-accounting PASS" in accounting else "fail"))
    if index == 0:
        checks += t08_scoring.negative_checks(cells_content, product_paths[0].read_text(encoding="utf-8"))
    write_scores(out, result.records, checks, result.lines, collection_sha256=tag, label=label)
    return EXIT_OK


def _t09_slim(kind_entries, reader) -> list:
    """The bin's event documents, slimmed per range as read (t09_scoring.slim), so one range product is held at a time (review I3)."""
    from tests.adapters import t09_scoring
    out = []
    for path in _verified(kind_entries):
        out.append([t09_scoring.slim(doc) for doc in reader(path).events])
    return t09_scoring.merged_docs(out)


def score_t09(block: int, index: int, bins: dict, out: Path, paths: Paths, tag: str, scores: Path) -> int:
    from tests.adapters import t09_scoring
    if index == T09_POOL_INDEX:
        return score_t09_pool(block, bins, out, tag, scores)
    from light_recipe import configuration, multistart, product as light_product, single_photon, topology
    import t09_fixture_files
    import t09_topology_readings
    import t09_truth_start
    if not 0 <= index < len(T09_SAMPLES):
        raise TaskError(f"T09 bin {index}: 0 to {T09_POOL_INDEX}")
    fixture_id, stratum, label = T09_SAMPLES[index]
    identity = core.BinIdentity("T09", fixture_id, block, stratum)
    entry = bins[label]
    if entry["status"] != "complete":
        write_scores(out, t09_scoring.missing_records(identity, entry["reason"]), [], [f"MISSING {identity.label}: {entry['reason']}"],
                     collection_sha256=tag, label=label)
        return EXIT_OK
    kinds = entry["kinds"]
    cfg = configuration.load()
    read_ms = (lambda p: light_product.read_product(p, None, cfg, multistart.load()))
    read_topo = (lambda p: light_product.read_product(p, None, cfg, multistart.load(), topology.load()))
    reader = t09_fixture_files.read_truth_two_source if fixture_id == 9004 else t09_fixture_files.read_truth
    generation, (truth_header, truth) = _truth_of(entry, reader)
    carry = []
    if fixture_id in (9001, 9004):
        threes = _verified(kinds["multistart"])
        fours = _verified(kinds["topology"])
        slimmed = []
        for three_path, four_path in zip(threes, fours):
            four = read_topo(four_path)
            carry += t09_topology_readings.carry_defects(four, read_ms(three_path), sha256_file(three_path))
            slimmed.append([t09_scoring.slim(doc) for doc in four.events])
            four = None
        events = t09_scoring.merged_docs(slimmed)
    else:
        events = _t09_slim(kinds["multistart"], read_ms)
    ts_docs = None
    if fixture_id == 9001:
        ts_docs = t09_scoring.merged_docs([t09_truth_start.read_truth_start(p)[1] for p in _verified(kinds["truth-start"])])
    result = t09_scoring.score_bin(identity, events, truth_header, truth, truth_start_docs=ts_docs, readout_sha256=generation["stratum_sha256"],
                                   carry_defects=carry)
    checks = t09_scoring.bin_checks(result)
    lines = list(result.lines)
    if fixture_id == 9002:
        unhit = _t09_slim(kinds["unhit"], read_ms)
        check, more = t09_scoring.negative_check(identity, t09_scoring.E1A_NAME, unhit, truth, t09_scoring.E1A_PARAMETERS)
        checks.append(check)
        lines += more
    if fixture_id == 9001 and stratum == T09_E1B_STRATUM:
        sp = single_photon.load()
        single = _t09_slim(kinds["single-photon"], lambda p: light_product.read_product(p, None, sp, multistart.load()))
        check, more = t09_scoring.negative_check(identity, t09_scoring.E1B_NAME, single, truth, t09_scoring.E1B_PARAMETERS)
        checks.append(check)
        lines += more
    extra = None
    if fixture_id == 9001 and stratum in t09_scoring.POOLED_STRATA:
        extra = t09_scoring.pool_columns(events, truth)
    write_scores(out, result.records, checks, lines, collection_sha256=tag, label=label, extra=extra)
    return EXIT_OK


def score_t09_pool(block: int, bins: dict, out: Path, tag: str, scores: Path) -> int:
    """The pool (v4 9.4): complete only if every member bin is (layout.pool_status); its columns read from the members' pool.npz, each member's
    scoring finished against this collection (scored.json), else incomplete (rerun the member's scoring)."""
    from tests.adapters import t09_scoring
    import numpy
    pool = t09_scoring.pool_identity(block)
    labels = {s: T09_SAMPLES[s][2] for s in pool.members}
    status, reason = layout.pool_status(pool, {s: (bins[labels[s]]["status"], bins[labels[s]]["reason"]) for s in pool.members})
    if status != "complete":
        write_scores(out, t09_scoring.missing_pool(block, reason), [], [f"MISSING {pool.label}: {reason}"], collection_sha256=tag, label=pool.name)
        return EXIT_OK
    columns = {}
    for s in pool.members:
        folder = Path(scores) / f"bin-{s}"
        marker = folder / "scored.json"
        doc = json.loads(marker.read_text(encoding="utf-8")) if marker.exists() else {}
        if doc.get("collection_sha256") != tag or not (folder / "pool.npz").exists() or sha256_file(folder / "pool.npz") != doc.get("pool_sha256"):
            raise Incomplete(f"the scoring of bin {s} did not finish against this collection, or its pool.npz is not its scored.json's; rerun it, "
                             "then the pool (no draw)")
        with numpy.load(folder / "pool.npz") as npz:
            columns[s] = {k: npz[k] for k in npz.files}
    write_scores(out, t09_scoring.score_pool(block, columns), [], [], collection_sha256=tag, label=pool.name)
    return EXIT_OK


def _truth_of(entry: dict, reader) -> tuple:
    """The sample's generation.json and its whole-stratum truth, read from the counted generation folder the collection names."""
    if "generation" not in entry:
        raise TaskError("the collection names no generation folder for the bin")
    folder = Path(entry["generation"])
    generation = json.loads((folder / "generation.json").read_text(encoding="utf-8"))
    truth_path = folder / f"{generation['label']}.truth.npz"
    if sha256_file(truth_path) != generation["truth_sha256"]:
        raise TaskError("the stratum's truth file is not generation.json's")
    return generation, reader(truth_path)


# ---- the summary

def scoring_module(workflow: str):
    if workflow == "T08":
        from tests.adapters import t08_scoring
        return t08_scoring
    from tests.adapters import t09_scoring
    return t09_scoring


REPEATABLE_CHECK_TASKS = ("T08 checks", "T07 checks", "T07 negative cases")   # the user, 2026-11-13: check tasks drawing from blocks 1 and 6 only


def counted_single(attempts: dict, name: str, block: int, state_of) -> Path:
    """The counted attempt's folder of a single task (the fixed points, the T08 checks; fix round 1, M3), or Incomplete. Fix round 2, R4: an
    attempt whose generator check failed (milestone generator-check-failed, NOT-REPEATABLE) goes to the user (v4 18, generator-check rows 2 to
    4); it is never "rerun"."""
    rows = attempts.get(name, [])
    if any("generator-check-failed" in Milestones(folder).names() for _, folder in rows):
        raise Incomplete(f"{name}: the generator check failed (NOT-REPEATABLE): it goes to the user (v4 18, generator-check rows 2 to 4), "
                         "no rerun")
    repeatable = name in REPEATABLE_CHECK_TASKS   # the user, 2026-11-13, "Count it: block 1/6 only"; never a recipe task, never the fixed points
    notes = []
    try:
        folder = counted_folder(rows, block, state_of, check_task=repeatable, notes=notes)
    except layout.LayoutError as error:
        raise Incomplete(f"{name}: {error}; rerun it (block 6 or block 1 only, its declared role)") from None
    counted = notes[-1]
    for index, job, verdict in notes[:-1]:
        print(f"CLASSIFY {name} attempt {index} ({job}): {verdict}, {layout.REPEATED_CHECK_TASK}; counted: attempt {counted[0]} ({counted[1]})")
    return folder


def task_result(folder: Path, operation: str) -> str:
    """The task's own result word (its step log, written by lib.sh's step), or Incomplete."""
    log = Path(folder) / f"{operation}.log"
    words = [line.split()[2] for line in (log.read_text(encoding="utf-8").splitlines() if log.exists() else [])
             if line.startswith(f"RESULT {operation} ") and len(line.split()) > 2]
    if not words or words[-1] not in ("ok", "failed"):
        raise Incomplete(f"{operation} in {folder}: no result line ok or failed ({words[-1] if words else 'none'}); rerun it")
    return words[-1]


def extra_checks(workflow: str, block: int, attempts: dict, state_of) -> list:
    """The checks of the single tasks the summary reads: T09's fixed points (three GATE lines of the counted attempt), T08's checks task."""
    if workflow == "T09":
        from tests.adapters import t09_scoring
        folder = counted_single(attempts, "T09 fixed points", block, state_of)
        task_result(folder, "t09-fixed-points")
        lines = (folder / "fixed-points.log").read_text(encoding="utf-8").splitlines() if (folder / "fixed-points.log").exists() else []
        gates = sum(line.startswith("GATE ") for line in lines)
        if gates != 3:
            raise Incomplete(f"the fixed points in {folder} printed {gates} GATE lines, not 3; rerun them")
        return [t09_scoring.fixed_point_check(lines)]
    folder = counted_single(attempts, "T08 checks", block, state_of)
    task_result(folder, "t08-checks")
    if not (folder / "checks.json").exists():
        raise Incomplete(f"the T08 checks in {folder} left no checks.json; rerun them")
    return [core.CheckResult(**d) for d in json.loads((folder / "checks.json").read_text(encoding="utf-8"))]


def summary(workflow: str, block: int, scores: Path, collection: Path, out: Path, *, attempts_file: Path | None = None, state_of=sacct_state) -> int:
    """core.workflow_outcome over every bin's records and every required check (fix round 1, I1 and I2). Missing records come only from bins the
    collection marked missing (recipe side); a harness task that crashed or was refused is SUMMARY INCOMPLETE, exit 3, with no OUTCOME line."""
    attempt = check_block(block)
    module = scoring_module(workflow)
    try:
        bins = _collection(collection, workflow, block)
        tag = sha256_file(collection)
        attempts = read_attempts(attempts_file) if attempts_file is not None and Path(attempts_file).exists() else {}
        records, checks, lines = [], [], []
        samples = T08_SAMPLES if workflow == "T08" else T09_SAMPLES
        indices = list(range(len(samples))) + ([T09_POOL_INDEX] if workflow == "T09" else [])
        for index in indices:
            folder = Path(scores) / f"bin-{index}"
            marker = folder / "scored.json"
            if not marker.exists():
                raise Incomplete(f"the scoring of bin {index} left no scored.json: it crashed or was refused; rerun it (no draw)")
            doc = json.loads(marker.read_text(encoding="utf-8"))
            if doc.get("collection_sha256") != tag or sha256_file(folder / "records.json") != doc.get("records_sha256") \
                    or sha256_file(folder / "checks.json") != doc.get("checks_sha256"):
                raise Incomplete(f"the scoring of bin {index} is not of this collection, or its files changed; rerun it (no draw)")
            records += [bin_scorer.record_of(d) for d in json.loads((folder / "records.json").read_text(encoding="utf-8"))]
            checks += [core.CheckResult(**d) for d in json.loads((folder / "checks.json").read_text(encoding="utf-8"))]
        for label, entry in bins.items():
            for stop in entry.get("stops", []):
                checks.append(core.CheckResult(f"{stop['check']} (recorded in a range task)", "deterministic", "fail", stop=bool(stop["stop"])))
                lines.append(f"STOP {workflow} {label}: {stop['check']}: {stop['line']}")
            if entry["status"] != "complete":
                lines.append(f"MISSING {workflow} {label}: {entry['reason']} (recipe side: required output missing, v4 10)")
        checks += extra_checks(workflow, block, attempts, state_of)
        count = module.count_tests()
        # An incomplete bin (recipe side) carries no checks of its own: it fails through its inconclusive records; every other check is required.
        required = module.required_checks(missing=[label for label, e in bins.items() if e["status"] != "complete"])
        try:
            outcome = core.workflow_outcome(workflow, records, checks, attempt=attempt, found_obligations=getattr(module, "FOUND_OBLIGATIONS", ()),
                                            required_checks=required)
        except core.CoreError as error:
            raise Incomplete(str(error)) from None
    except Incomplete as error:
        print(f"SUMMARY INCOMPLETE {workflow} block {block}: {error}")
        return EXIT_CRASHED
    for line in lines:
        print(line)
    if len(records) != count["total"]:
        print(f"COUNT {workflow}: {len(records)} records, v4 5.3 fixes {count['total']}")
    print(f"OUTCOME {workflow} block {block} attempt {attempt}: gate result {outcome.workflow_result}, R11 state {outcome.r11_state}")
    for reason in outcome.reasons:
        print(f"REASON {reason}")
    for obligation in outcome.open_obligations:
        print(f"OBLIGATION {obligation.name} (owner {obligation.owner or 'none'}): {obligation.reason}")
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "outcome.json").write_text(json.dumps(dataclasses.asdict(outcome), sort_keys=True, default=str) + "\n", encoding="utf-8")
    return EXIT_OK


# ---- the task names (submit.sh writes one attempts.tsv line per submitted task with them)

def task_names() -> list:
    """(kind, sample, range, name): the collection's and summary's names of every recipe and check task, in the submission's array order."""
    out = [("t08-sample", i, 0, task_name("T08", label, layout.EventRange(0, EVENTS))) for i, (_, _, label) in enumerate(T08_SAMPLES)]
    out += [("t09-generate", i, 0, f"T09 generate {label}") for i, (_, _, label) in enumerate(T09_SAMPLES)]
    out += [("t09-range", i, t, task_name("T09", label, span)) for i, (_, _, label) in enumerate(T09_SAMPLES) for t, span in enumerate(T09_RANGES)]
    out += [(kind, 0, 0, name) for name, kind in SINGLE_TASKS.items()]
    out += [("t07-bin", i, 0, f"T07 bin {i}") for i in range(24)] + [("t07-refit", i, 0, f"T07 refit {i}") for i in range(36)]
    out += [("t07-negative-cases", 0, 0, "T07 negative cases"), ("t07-checks", 0, 0, "T07 checks")]
    return out


# ---- the plan

def plan(block: int) -> int:
    check_block(block)
    found = layout.evaluation_plan(block=block)
    per = {}
    for task in found.tasks:
        w = task.kind.split(" ")[0]
        per.setdefault(w, [0, 0.0])
        per[w][0] += 1
        per[w][1] += task.wall_seconds * task.cpus / 3600
    for w, (n, hours) in sorted(per.items()):
        sub = layout.Plan([t for t in found.tasks if t.kind.startswith(w)])
        print(f"PLAN {w}: {n} tasks, {hours:.1f} CPU-hours, longest chain {sub.longest_chain_seconds() / 3600:.2f} h")
    print(f"PLAN tasks {len(found.tasks)} by kind {json.dumps(found.task_counts(), sort_keys=True)}")
    print(f"PLAN total {found.cpu_hours():.1f} CPU-hours (allocated CPUs x elapsed), longest chain {found.longest_chain_seconds() / 3600:.2f} h")
    for note in found.notes:
        print(f"PLAN note: {note}")
    return EXIT_OK


# ---- the command line

OPERATIONS = ("t08-sample", "t08-checks", "t09-generate", "t09-range", "t09-fixed-points", "collect", "score", "summary", "plan", "names", "t07-bin",
              "t07-refit", "t07-slices", "t07-negative-cases", "t07-checks")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    for name in OPERATIONS:
        p = sub.add_parser(name)
        p.add_argument("--block", required=True)
        if name not in ("plan", "names"):
            p.add_argument("--out", required=True)
        if name in ("t08-sample", "t09-generate", "t09-range", "score", "t07-bin", "t07-refit", "t07-slices"):
            p.add_argument("--index", type=int, required=True)
        if name == "t09-range":
            p.add_argument("--range", type=int, required=True)
            p.add_argument("--generation", required=True)
        if name in ("collect", "score", "summary"):
            p.add_argument("--workflow", required=True, choices=("T07", "T08", "T09"))
        if name in ("collect", "summary"):
            p.add_argument("--attempts", required=True)
        if name == "t07-refit":
            p.add_argument("--attempts", help="attempts.tsv: the refit runs on its bin task's counted attempt")
        if name in ("t07-bin", "t07-refit", "t07-negative-cases", "t07-checks"):
            p.add_argument("--t07-build", help="the T07 build folder (t07-build.sh)")
        if name == "t07-slices":
            p.add_argument("--scores", help="the T07 scores folder (score.sh's)")
        if name == "score":
            p.add_argument("--rate-record", help="T07 noise bins: the Freeze-B r_dev record (F2, v4 8.3)")
        if name in ("score", "summary"):
            p.add_argument("--collection", required=True)
        if name == "summary":
            p.add_argument("--scores", required=True)
        p.add_argument("--t08-generator")
        p.add_argument("--t09-generator")
        p.add_argument("--reference-log")
        p.add_argument("--reference-script")
        p.add_argument("--calo-assets", default=str(Paths.calo), help="the calo-cluster assets (default the plugin's; hand-made tests only)")
        p.add_argument("--light-assets", default=str(Paths.light), help="the photon-likelihood assets (default the plugin's; hand-made tests only)")
    args = ap.parse_args(argv)
    paths = Paths(calo=Path(args.calo_assets), light=Path(args.light_assets), t08_generator=args.t08_generator and Path(args.t08_generator),
                  t09_generator=args.t09_generator and Path(args.t09_generator), reference_log=args.reference_log and Path(args.reference_log),
                  reference_script=args.reference_script and Path(args.reference_script))
    op = args.operation
    try:
        check_block(args.block)
        block = int(args.block)
        if op == "t08-sample":
            code = t08_sample(block, args.index, Path(args.out), paths)
        elif op == "t08-checks":
            code = t08_checks(block, Path(args.out), paths)
        elif op == "t09-generate":
            code = t09_generate(block, args.index, Path(args.out), paths)
        elif op == "t09-range":
            code = t09_range(block, args.index, args.range, Path(args.generation), Path(args.out), paths)
        elif op == "t09-fixed-points":
            code = t09_fixed_points(block, Path(args.out), paths)
        elif op == "collect":
            code = collect(args.workflow, block, Path(args.attempts), Path(args.out)) if args.workflow != "T07" else \
                t07_collect(block, Path(args.attempts), Path(args.out))
        elif op == "score":
            code = score(args.workflow, block, args.index, Path(args.collection), Path(args.out), paths, rate_record=args.rate_record)
        elif op == "summary":
            code = summary(args.workflow, block, Path(args.scores), Path(args.collection), Path(args.out), attempts_file=Path(args.attempts)) \
                if args.workflow != "T07" else t07_summary(block, Path(args.scores), Path(args.collection), Path(args.out), attempts_file=Path(args.attempts))
        elif op == "plan":
            code = plan(block)
        elif op == "names":
            for kind, sample, span, name in task_names():
                print(f"NAME\t{kind}\t{sample}\t{span}\t{name}")
            code = EXIT_OK
        elif op == "t07-bin":
            code = t07_bin(block, args.index, Path(args.out), args.t07_build)
        elif op == "t07-refit":
            code = t07_refit(block, args.index, Path(args.out), args.t07_build, args.attempts)
        elif op == "t07-slices":
            code = t07_slices(block, args.index, args.scores, Path(args.out))
        elif op == "t07-negative-cases":
            code = t07_negative_cases(block, Path(args.out), args.t07_build)
        else:
            code = t07_checks(block, Path(args.out), args.t07_build)
    except (TaskError, layout.LayoutError, bin_scorer.ScoringError) as error:
        print(f"REJECTED {op}: {error}")
        print(f"RESULT {op} rejected", flush=True)
        return EXIT_REJECTED
    except StepFailed as error:
        print(f"FAILED {op}: {error}")
        print(f"RESULT {op} failed", flush=True)
        return EXIT_FAILED
    except Incomplete as error:
        if isinstance(error, DeadlineReached) and getattr(args, "out", None):   # review M1: the attempt's own reason at the collection
            Path(args.out).mkdir(parents=True, exist_ok=True)
            Milestones(Path(args.out)).mark(layout.STOPPED_AT_DEADLINE)
        print(f"INCOMPLETE {op}: {error}")
        print(f"RESULT {op} incomplete", flush=True)
        return EXIT_CRASHED
    except ScriptCrash as error:
        print(f"CRASHED {op}: {error}")
        print(f"RESULT {op} crashed", flush=True)
        return EXIT_CRASHED
    except Exception as error:  # noqa: BLE001 - a defect of this tool is a crash, never a negative reading
        import traceback
        traceback.print_exc()
        print(f"RESULT {op} crashed: unexpected {type(error).__name__}", flush=True)
        return EXIT_CRASHED
    print(f"RESULT {op} {RESULT_WORDS[code]}", flush=True)
    return code


def task_main(argv=None) -> int:
    """The command line of an evaluation task (the job scripts start this file): the task's deadline is set from its operation's Slurm limit
    (layout.start_task; integration fix round) before main, so every subprocess of the task is bounded by it. In-process callers (tests, the
    development wrapper) call main and keep their own deadline, or none."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in layout.TASK_LIMIT_SECONDS:
        layout.start_task(argv[0])
    return main(argv)


if __name__ == "__main__":
    sys.exit(task_main())
