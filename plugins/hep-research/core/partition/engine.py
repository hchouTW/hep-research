"""Manifest-based partition engine: manifest, write-once chunk outputs, bounded resubmission, complete merge.

Rules this enforces:
- The work is split once into a manifest of chunks (id, item range, seed); the manifest hash ties every output to it.
- A chunk's output is written atomically and only once; resubmission skips finished chunks, so nothing is counted twice.
  Atomic means serialized first, fsynced, renamed; a failed write removes its .tmp-* file. A worker result json cannot
  write (a set, an object) is a failed attempt with signature 'unserializable-result'; the run goes on.
- Retries happen only when the run configuration sets "max_attempts"; with no configuration a failed chunk is not
  retried. max_attempts bounds the attempts of a chunk since its last reset() across every run() call, not per call:
  rerunning the command never buys more attempts ('attempts-exhausted', set by the call that used the last attempt);
  only reset() with a reason does.
- A chunk whose last two attempts failed with the same failure signature is stopped even if attempts remain. The
  signature is the worker exception's 'signature' attribute when it has one, else its type and message with paths,
  long hex strings and numbers masked, so a temporary path or a timestamp in the message does not defeat the stop.
- State (attempts, errors) is kept on disk after any failure, so a later resubmission continues where it stopped.
- run(), reset() and merge() hold an exclusive lock on <state>/.lock (dir_lock); a second process or thread gets
  PartitionError("partition.locked") at once instead of racing it for state.json. status() only reads and takes no
  lock. The same lock (shared per-thread registry) is the campaign lock, so a campaign call may nest engine calls.
- Merging reads each manifest chunk from its canonical file chunks/<id>.json only, and checks that it belongs to this
  manifest and has the manifest's id, range and seed, and that the ranges tile [0, n) with no gap or overlap; a missing
  chunk makes the merge 'incomplete', never a silent partial sum. Any other file claiming a manifest chunk is never
  summed: an identical copy is reported, a different one ('merge.conflicting_duplicate') makes the merge incomplete.
- Merge rules (F-07): the default merge sums numbers key by key. A key may declare its rule (rules={"key": "sum" |
  "min" | "max" | "first" | "concat"}, nested keys as "outer.inner"); first takes the value of the first chunk in item
  order, concat joins lists in item order. An undeclared key whose name marks a non-additive quantity (a name token
  in NON_ADDITIVE_TOKENS: seed, median, mean, quantile, min, max, rate, fraction, and none of ADDITIVE_TOKENS such
  as sum or total, so seed_sum still sums) is refused
  ('merge.undeclared_non_additive'): summing it would be wrong. Undeclared other keys keep summing. A combine function
  replaces all of this.

API: make_manifest(job_id, n_items, chunk_size, seed) -> dict; validate_manifest(manifest); check_template(cmd); run(manifest, state_dir, worker, config=None) -> dict
(synchronous, in-process); status(manifest, state_dir); reset(state_dir, chunk_ids, reason); merge(manifest,
state_dir, combine=None, rules=None); dir_lock(directory, operation, busy). Standard library only.
"""
from __future__ import annotations

import contextlib
import datetime
import hashlib
import json
import math
import os
import re
import shlex
import string
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from threading import local as _thread_state  # the packaging scan reads '.local' as a host name
from typing import Any

from core.protected.guard import guard


class PartitionError(ValueError):
    """Refusal with a named code (exit 2 in a CLI)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


_HELD = _thread_state()  # directories this thread holds the lock of, with a depth (calls nest)


@contextlib.contextmanager
def dir_lock(directory, operation: str, busy: Callable[[Path, str], Exception] | None = None) -> Iterator[None]:
    """Exclusive, non-blocking lock on <directory>/.lock for one operation; nested calls in the same thread reuse it.
    busy(directory, holder) builds the exception raised when another process or thread holds it (default
    PartitionError("partition.locked")). The holder text (operation, pid, time) is written into the lock file."""
    ddir = Path(directory).resolve()
    held = getattr(_HELD, "dirs", None)
    if held is None:
        held = _HELD.dirs = {}
    if held.get(ddir):
        held[ddir] += 1
        try:
            yield
        finally:
            held[ddir] -= 1
        return
    ddir.mkdir(parents=True, exist_ok=True)
    fh = open(ddir / ".lock", "a+", encoding="utf-8")
    try:
        try:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:  # Windows
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]  # Windows-only API, absent from non-win32 stubs
    except OSError:
        fh.seek(0)
        holder = fh.read().strip() or "another process"
        fh.close()
        if busy is None:
            raise PartitionError("partition.locked", f"{ddir} is in use ({holder}); wait for it to finish") from None
        raise busy(ddir, holder) from None
    try:
        fh.seek(0)
        fh.truncate()
        now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        fh.write(f"{operation} by pid {os.getpid()} since {now}")
        fh.flush()
        held[ddir] = 1
        yield
    finally:
        held.pop(ddir, None)
        fh.close()  # closing the file releases the lock


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


CHUNK_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")  # chunk IDs name output paths: no separators, dots or spaces
JOB_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
PLACEHOLDERS = ("start", "stop", "seed", "out", "id")


def validate_manifest(manifest) -> dict:
    """The manifest unchanged, or ValueError: a job ID and chunk IDs from a safe charset (a chunk ID builds output
    paths, so '../x' would write outside the campaign), integer ranges that tile [0, n_items) in order, integer seeds,
    and a manifest_hash that matches the content."""
    if not isinstance(manifest, dict):
        raise ValueError("the manifest must be a JSON object")
    body = {k: v for k, v in manifest.items() if k != "manifest_hash"}
    if manifest.get("manifest_hash") != _hash(body):
        raise ValueError("manifest_hash does not match the manifest content")
    if not isinstance(manifest.get("job_id"), str) or not JOB_ID.match(manifest["job_id"]):
        raise ValueError(f"job_id must match {JOB_ID.pattern}")
    n = manifest.get("n_items")
    chunks = manifest.get("chunks")
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0 or not isinstance(chunks, list) or not chunks:
        raise ValueError("the manifest needs a positive integer n_items and a non-empty chunk list")
    seen, pos = set(), 0
    for ch in chunks:
        cid = ch.get("id") if isinstance(ch, dict) else None
        if not isinstance(cid, str) or not CHUNK_ID.match(cid):
            raise ValueError(f"chunk id {cid!r} must match {CHUNK_ID.pattern}")
        if cid in seen:
            raise ValueError(f"duplicate chunk id {cid}")
        seen.add(cid)
        if not all(_is_int(ch.get(k)) for k in ("start", "stop", "seed")):
            raise ValueError(f"chunk {cid}: start, stop and seed must be integers")
        if ch["start"] != pos or ch["stop"] <= ch["start"]:
            raise ValueError(f"chunk {cid}: ranges must tile [0, n_items) in order without gaps or overlaps")
        pos = ch["stop"]
    if pos != n:
        raise ValueError(f"the chunk ranges end at {pos}, not at n_items = {n}")
    return manifest


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def check_template(cmd) -> list[str]:
    """The command template split into arguments, or ValueError. Only the fields {start} {stop} {seed} {out} {id} are
    allowed, with no conversion or format spec; {out} is required; literal braces must be doubled ({{ }}). The
    template is trial-rendered, so a template that passes cannot fail to fill in the runner."""
    if not isinstance(cmd, str) or not cmd.strip():
        raise ValueError("the command template is empty")
    try:
        args = shlex.split(cmd)
    except ValueError as exc:
        raise ValueError(f"the command template cannot be split into arguments: {exc}") from None
    used = set()
    for arg in args:
        try:
            fields = list(string.Formatter().parse(arg))
        except ValueError as exc:
            raise ValueError(f"argument {arg!r}: {exc}; write literal braces as {{{{ and }}}}") from None
        for _, name, spec, conv in fields:
            if name is None:
                continue
            if name not in PLACEHOLDERS or spec or conv:
                raise ValueError(f"argument {arg!r}: only {{start}} {{stop}} {{seed}} {{out}} {{id}} are allowed, without "
                                 "conversions or format specs; write literal braces as {{ and }}")
            used.add(name)
    if "out" not in used:
        raise ValueError("the command template must write its result to {out}")
    sample = {"start": 0, "stop": 1, "seed": 0, "out": "/tmp/out.json", "id": "c0000"}
    return [a.format(**sample) for a in args]


def make_manifest(job_id: str, n_items: int, chunk_size: int, seed: int) -> dict:
    if n_items <= 0 or chunk_size <= 0:
        raise ValueError("n_items and chunk_size must be positive")
    if not isinstance(job_id, str) or not JOB_ID.match(job_id):
        raise ValueError(f"job_id must match {JOB_ID.pattern}")
    chunks = [{"id": f"c{k:04d}", "start": s, "stop": min(s + chunk_size, n_items), "seed": seed * 100003 + k}
              for k, s in enumerate(range(0, n_items, chunk_size))]
    body = {"job_id": job_id, "n_items": n_items, "chunk_size": chunk_size, "seed": seed, "chunks": chunks}
    return dict(body, manifest_hash=_hash(body))


def _write_atomic(path: Path, obj) -> None:
    """Write obj as JSON to path atomically: serialized first (a TypeError leaves nothing behind), written to a
    .tmp-* file in the same folder, flushed and fsynced, then renamed over path. On any failure the .tmp-* file is
    removed and the exception re-raised, so path holds either the old or the new content."""
    text = json.dumps(obj, sort_keys=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _load_state(state_dir: Path) -> dict:
    p = state_dir / "state.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"chunks": {}}


_PATH = re.compile(r"(?:[A-Za-z]:)?[\\/][^\s:'\"]*[\\/][^\s:'\"]*")  # absolute or rooted paths with 2+ segments
_HEX = re.compile(r"\b[0-9a-fA-F]{8,}\b")
_NUM = re.compile(r"\d+(?:\.\d+)?")


class _Unserializable(TypeError):
    """A worker result json cannot write; recorded as a chunk failure with a stable signature."""

    signature = "unserializable-result"


def failure_signature(exc: BaseException) -> str:
    """Signature for the 'two identical failures stop' rule. An exception may carry its own stable 'signature'
    (a string); otherwise its type and message with paths, long hex strings and numbers masked. Masking errs on the
    side of stopping: two failures that differ only in a number count as the same failure."""
    sig = getattr(exc, "signature", None)
    if isinstance(sig, str) and sig:
        return sig
    text = _NUM.sub("<n>", _HEX.sub("<hex>", _PATH.sub("<path>", str(exc))))
    return f"{type(exc).__name__}: {' '.join(text.split())[:300]}"


def _signatures(st: dict) -> list:
    """Failure signatures of a chunk; a state written before signatures existed derives them from its error texts."""
    if "signatures" not in st:
        st["signatures"] = [_NUM.sub("<n>", _HEX.sub("<hex>", _PATH.sub("<path>", e))) for e in st.get("errors", [])]
    return st["signatures"]


def _repeated(st: dict) -> bool:
    sigs = _signatures(st)
    return len(sigs) >= 2 and sigs[-1] == sigs[-2]


def _max_attempts(config: dict | None) -> int:
    value = (config or {}).get("max_attempts", 1)
    if not _is_int(value) or value < 1:
        raise ValueError(f"max_attempts must be an integer of at least 1, got {value!r}")
    return value


def run(manifest: dict, state_dir, worker, config: dict | None = None) -> dict:
    """Run every chunk without an output, each within max_attempts counted since its last reset() over all calls."""
    guard("core.partition.engine.run", paths=[state_dir])
    state_dir = Path(state_dir)
    max_attempts = _max_attempts(config)
    with dir_lock(state_dir, "run"):
        return _run(manifest, state_dir, worker, config, max_attempts)


def _run(manifest: dict, state_dir: Path, worker, config: dict | None, max_attempts: int) -> dict:
    state = _load_state(state_dir)
    if state.get("manifest_hash", manifest["manifest_hash"]) != manifest["manifest_hash"]:
        raise ValueError("state directory belongs to a different manifest")
    state["manifest_hash"] = manifest["manifest_hash"]
    ran, skipped = [], []
    for ch in manifest["chunks"]:
        out = state_dir / "chunks" / f"{ch['id']}.json"
        st = state["chunks"].setdefault(ch["id"], {"attempts": 0, "attempts_since_reset": 0, "errors": [],
                                                   "signatures": [], "status": "pending"})
        # a state written before attempts_since_reset existed: count every attempt (fail closed)
        st.setdefault("attempts_since_reset", st["attempts"])
        _signatures(st)
        if out.exists():
            st["status"] = "done"
            skipped.append(ch["id"])
            continue
        while True:
            if _repeated(st):
                st["status"] = "stopped-repeated-failure"
                break
            if st["attempts_since_reset"] >= max_attempts:
                # nothing left: say why instead of 'failed', also on the call that used the last attempt (Q5)
                st["status"] = "attempts-exhausted"
                break
            st["attempts"] += 1
            st["attempts_since_reset"] += 1
            ran.append(ch["id"])
            try:
                result = worker(ch)
                doc = {"chunk_id": ch["id"], "manifest_hash": manifest["manifest_hash"], "start": ch["start"],
                       "stop": ch["stop"], "seed": ch["seed"], "result": result}
                try:
                    json.dumps(doc)
                except (TypeError, ValueError) as exc:  # e.g. a set: the attempt failed, the run goes on
                    raise _Unserializable(f"worker result is not JSON-serializable: {exc}") from None
            except Exception as exc:  # noqa: BLE001 - every worker failure is recorded, not hidden
                st["errors"].append(f"{type(exc).__name__}: {exc}")
                st["signatures"].append(failure_signature(exc))
                st["status"] = "failed"
                _write_atomic(state_dir / "state.json", state)
                continue
            _write_atomic(out, doc)
            st["status"] = "done"
            break
        _write_atomic(state_dir / "state.json", state)
    summary = status(manifest, state_dir)
    return dict(summary, invocations=ran, skipped_done=skipped, max_attempts=max_attempts,
                retries_configured=bool(config and "max_attempts" in config))


def reset(state_dir, chunk_ids, reason: str, manifest: dict | None = None) -> dict:
    """Clear the error history of chunks after their cause was fixed, so they can run again. Kept in 'resets'.
    With a manifest, a state folder that belongs to another manifest is refused before anything is written."""
    state_dir = Path(state_dir)
    with dir_lock(state_dir, "reset"):
        return _reset(state_dir, chunk_ids, reason, manifest)


def _reset(state_dir: Path, chunk_ids, reason: str, manifest: dict | None) -> dict:
    state = _load_state(state_dir)
    if manifest is not None and state.get("manifest_hash", manifest["manifest_hash"]) != manifest["manifest_hash"]:
        raise ValueError("state directory belongs to a different manifest")
    unknown = [cid for cid in chunk_ids if cid not in state["chunks"]]
    if unknown:
        raise ValueError(f"unknown chunk {unknown[0]}")
    for cid in chunk_ids:
        st = state["chunks"].get(cid)
        if st is None:
            raise ValueError(f"unknown chunk {cid}")
        state.setdefault("resets", []).append({"chunk": cid, "reason": reason, "errors": st["errors"], "attempts": st["attempts"]})
        st.update(errors=[], signatures=[], attempts_since_reset=0, status="pending")
    _write_atomic(state_dir / "state.json", state)
    return state


def status(manifest: dict, state_dir) -> dict:
    state = _load_state(Path(state_dir))
    rows = {c["id"]: state["chunks"].get(c["id"], {"attempts": 0, "errors": [], "status": "pending"}) for c in manifest["chunks"]}
    for cid in rows:
        if (Path(state_dir) / "chunks" / f"{cid}.json").exists():
            rows[cid] = dict(rows[cid], status="done")
    not_done = sorted(c for c, r in rows.items() if r["status"] != "done")
    return {"complete": not not_done, "not_done": not_done, "chunks": rows}


def _sum(a, b):
    if isinstance(a, list):
        if len(a) != len(b):
            raise ValueError("chunk results have different lengths")
        return [_sum(x, y) for x, y in zip(a, b)]
    if isinstance(a, dict):
        if set(a) != set(b):
            raise ValueError("chunk results have different keys")
        return {k: _sum(a[k], b[k]) for k in a}
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError(f"the default merge adds numbers only, got {type(a).__name__} and {type(b).__name__}; "
                         "pass a combine function for other results")
    return a + b


MERGE_RULES = ("sum", "min", "max", "first", "concat")
# name tokens of quantities that do not add across chunks (F-07, proposal of the upgrade plan; open question 11)
NON_ADDITIVE_TOKENS = frozenset({"seed", "median", "mean", "quantile", "min", "max", "rate", "fraction"})
# a name that also says it is a sum (seed_sum, n_rate_bins) is additive by its own declaration
ADDITIVE_TOKENS = frozenset({"sum", "sumw", "sumw2", "total", "count", "counts", "n"})


def _non_additive(name: str) -> bool:
    tokens = {t for t in re.split(r"[^a-z0-9]+", name.lower()) if t}
    return bool(tokens & NON_ADDITIVE_TOKENS) and not tokens & ADDITIVE_TOKENS


def parse_rules(items) -> dict:
    """KEY=RULE strings (a CLI's --rule values) -> {key: rule}; a malformed item or unknown rule is a ValueError."""
    rules = {}
    for item in items or []:
        key, sep, rule = str(item).partition("=")
        if not sep or not key or rule not in MERGE_RULES:
            raise ValueError(f"--rule {item!r}: expected KEY=RULE with RULE one of {', '.join(MERGE_RULES)}")
        rules[key] = rule
    return rules


def _undeclared_non_additive(result, rules: dict, path: str = "") -> list[str]:
    """Dotted paths of dict keys that look non-additive and have no declared rule."""
    out: list[str] = []
    if isinstance(result, dict):
        for k, v in result.items():
            p = f"{path}.{k}" if path else str(k)
            if p in rules:
                continue
            if _non_additive(str(k)):
                out.append(p)
            else:
                out.extend(_undeclared_non_additive(v, rules, p))
    return out


def _numbers(values, what: str):
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
        return values
    if all(isinstance(v, list) for v in values) and len({len(v) for v in values}) == 1:
        return values
    raise ValueError(f"merge rule {what} needs numbers or equal-length lists of numbers")


def _apply_rule(rule: str, values: list, path: str):
    if rule == "first":
        return values[0]
    if rule == "concat":
        if not all(isinstance(v, list) for v in values):
            raise ValueError(f"merge rule concat for {path!r} needs lists")
        return [x for v in values for x in v]
    if rule == "sum":
        return _reduce(values)
    pick = min if rule == "min" else max
    vals = _numbers(values, f"{rule} for {path!r}")
    if isinstance(vals[0], list):
        return [_apply_rule(rule, [v[i] for v in vals], f"{path}[{i}]") for i in range(len(vals[0]))]
    return pick(vals)


def _combine_with_rules(results: list, rules: dict, path: str = ""):
    """Key-by-key merge: a declared rule where there is one, summation elsewhere."""
    if path in rules:
        return _apply_rule(rules[path], results, path)
    first = results[0]
    if isinstance(first, dict):
        if any(not isinstance(r, dict) or set(r) != set(first) for r in results):
            raise ValueError("chunk results have different keys")
        return {k: _combine_with_rules([r[k] for r in results], rules, f"{path}.{k}" if path else str(k)) for k in first}
    return _reduce(results)


def _nonfinite(x, path="result") -> str | None:
    """Path of the first NaN or infinity in a chunk result, else None."""
    if isinstance(x, float) and not math.isfinite(x):
        return path
    if isinstance(x, dict):
        return next((p for k, v in x.items() if (p := _nonfinite(v, f"{path}.{k}"))), None)
    if isinstance(x, list):
        return next((p for i, v in enumerate(x) if (p := _nonfinite(v, f"{path}[{i}]"))), None)
    return None


def merge(manifest: dict, state_dir, combine=None, rules: dict | None = None) -> dict:
    """Merge chunk outputs; combine(list_of_results) defaults to key-by-key summation with the declared rules (F-07)."""
    guard("core.partition.engine.merge", paths=[state_dir])
    with dir_lock(state_dir, "merge"):
        return _merge(manifest, Path(state_dir), combine, rules)


def _merge(manifest: dict, state_dir: Path, combine=None, rules: dict | None = None) -> dict:
    rules = dict(rules or {})
    bad_rules = {k: v for k, v in rules.items() if not isinstance(k, str) or v not in MERGE_RULES}
    if bad_rules and combine is None:
        raise PartitionError("merge.bad_rule", f"merge rules must map key paths to one of {list(MERGE_RULES)}: {bad_rules}")
    default = combine is None
    combine = combine or (lambda rs: _combine_with_rules(rs, rules))
    problems: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    results = []
    wanted = {c["id"]: c for c in manifest["chunks"]}
    cdir = Path(state_dir) / "chunks"
    canonical: dict[str, dict] = {}
    # 1. each manifest chunk comes from its canonical file <id>.json only, the one run() and collect() write
    for cid, c in wanted.items():
        f = cdir / f"{cid}.json"
        if not f.exists():
            continue
        doc, why = _read_chunk(f)
        if why:
            problems.append({"code": "merge.unreadable", "file": f.name, "message": why})
            continue
        if doc["manifest_hash"] != manifest["manifest_hash"]:
            problems.append({"code": "merge.foreign_chunk", "file": f.name, "message": "output belongs to another manifest"})
            continue
        if doc["chunk_id"] != cid:
            problems.append({"code": "merge.id_mismatch", "file": f.name, "message": f"holds chunk {doc['chunk_id']!r}"})
            continue
        if (doc["start"], doc["stop"]) != (c["start"], c["stop"]):
            problems.append({"code": "merge.range_mismatch", "file": f.name})
            continue
        if "seed" in doc and doc["seed"] != c["seed"]:
            problems.append({"code": "merge.seed_mismatch", "file": f.name,
                             "message": f"seed {doc['seed']!r}, manifest {c['seed']!r}"})
            continue
        bad = _nonfinite(doc["result"])
        if bad:
            problems.append({"code": "merge.non_finite", "file": f.name, "message": f"{bad} is not finite"})
            continue
        canonical[cid] = doc
        seen[cid] = f.name
        results.append((c["start"], doc["result"]))
    # 2. every other file is never summed; one that claims a manifest chunk with a different result is a conflict
    for f in sorted(cdir.glob("*.json")) if cdir.is_dir() else []:
        if f.stem in wanted or f.name.startswith("."):  # .tmp-* files of an interrupted write are not outputs
            continue
        doc, why = _read_chunk(f)
        if why:
            problems.append({"code": "merge.unreadable", "file": f.name, "message": why})
            continue
        cid = doc["chunk_id"]
        if doc["manifest_hash"] != manifest["manifest_hash"]:
            problems.append({"code": "merge.foreign_chunk", "file": f.name, "message": "output belongs to another manifest"})
        elif cid not in wanted:
            problems.append({"code": "merge.unknown_chunk", "file": f.name})
        elif cid in canonical and all(doc.get(k) == canonical[cid].get(k) for k in ("start", "stop", "seed", "result")):
            problems.append({"code": "merge.duplicate_chunk", "file": f.name,
                             "message": f"identical copy of {cid}.json; not counted twice"})
        else:
            problems.append({"code": "merge.conflicting_duplicate", "file": f.name,
                             "message": f"claims chunk {cid} but differs from {cid}.json (or {cid}.json is not usable); "
                                        "find out which output is right before merging"})
    missing = sorted(set(wanted) - set(seen))
    if missing:
        problems.append({"code": "merge.missing_chunks", "chunks": missing})
    covered = sorted((wanted[c]["start"], wanted[c]["stop"]) for c in seen)
    pos = 0
    for a, b in covered:
        if a != pos:
            problems.append({"code": "merge.gap_or_overlap", "at": pos})
        pos = b
    if not missing and pos != manifest["n_items"]:
        problems.append({"code": "merge.incomplete_range", "covered_to": pos})
    # stray files (identical duplicates, other manifests, unknown ids, unreadable copies) are excluded and reported;
    # the merge is still complete when every manifest chunk was read from its canonical file and the ranges tile the
    # job. A stray file that claims a manifest chunk with a different result means two outputs disagree: incomplete.
    hard = [p for p in problems if p["code"] in ("merge.missing_chunks", "merge.range_mismatch", "merge.gap_or_overlap",
                                                 "merge.incomplete_range", "merge.non_finite", "merge.id_mismatch",
                                                 "merge.seed_mismatch", "merge.conflicting_duplicate")]
    merged = None
    if results and not hard and default:
        undeclared = sorted({k for _, r in results for k in _undeclared_non_additive(r, rules)})
        if undeclared:
            problems.append({"code": "merge.undeclared_non_additive", "keys": undeclared,
                             "message": "these keys name quantities that do not add across chunks; declare a merge rule "
                                        f"for each ({', '.join(MERGE_RULES)})"})
            hard.append(problems[-1])
    if results and not hard:
        try:
            merged = combine([r for _, r in sorted(results, key=lambda t: t[0])])
        except (TypeError, ValueError) as exc:  # results the combine function cannot add: no merged value
            problems.append({"code": "merge.combine_failed", "message": str(exc)})
            hard.append(problems[-1])
        else:
            bad = _nonfinite(merged, "merged")
            if bad:
                problems.append({"code": "merge.non_finite", "message": f"{bad} is not finite after combining"})
                hard.append(problems[-1])
                merged = None
    out = {"status": "complete" if not hard else "incomplete", "merged": merged, "problems": problems,
           "chunks_merged": len(seen), "chunks_expected": len(wanted)}
    if rules:
        out["merge_rules"] = rules
    return out


_CHUNK_KEYS = ("chunk_id", "manifest_hash", "start", "stop", "result")


def _read_chunk(f: Path) -> tuple[dict, str | None]:
    """(document, None) for a chunk output with the required keys, else ({}, why it cannot be used)."""
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, f"not readable JSON: {type(exc).__name__}"
    if not isinstance(doc, dict):
        return {}, "not a JSON object"
    missing = [k for k in _CHUNK_KEYS if k not in doc]
    if missing:
        return {}, f"missing keys {missing}"
    return doc, None


def _reduce(results):
    out = results[0]
    for r in results[1:]:
        out = _sum(out, r)
    return out
