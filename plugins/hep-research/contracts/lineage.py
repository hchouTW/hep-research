#!/usr/bin/env python3
"""Exposure and decision lineage (task P3, C12, T1.9, T4.3): checks for the exposure record and the decision record
(contracts/schemas/exposure_record.json, decision_record.json) and the one function that turns an exposure record into
the envelope's data_exposure.

Exposure record: per analysis and source snapshot, the releases that reached a session or a relay, with the kinds of
data seen, written append-only by the custodian. check_exposure() verifies the schema, seq 1..n without gaps and times
that never go backwards; check_append(previous, new) verifies that a new version names the previous version's
canonical SHA-256, keeps its analysis, source and every entry unchanged, and only adds entries after them.

Decision record: one decision, its actor (human or agent), what had been seen (through_seq entries of the exposure
record, bound by the canonical SHA-256 of exactly those entries), the artifacts produced and the recipe chosen.
check_decision(decision, exposure) verifies the binding against the current record (later appends do not break it, an
edited history does) and refuses a decision that predates entries it claims to have seen, or postdates entries it
leaves out ('seen' understated). Given base_dir (the CLI passes the decision record's folder, or --artifacts-root), it
also opens each artifacts[].ref (relative refs resolve against base_dir, absolute ones are used as they are) and
compares its file SHA-256 with artifacts[].sha256: a different hash is lineage.artifact_mismatch, a ref that is not a
readable file lineage.artifact_missing or lineage.artifact_unreadable, all errors (as a missing exposure record is).
Without base_dir (an in-memory record with no location) artifacts are not opened.

derive_exposure(record) is the only mapping to the envelope data_exposure: no record, an unreadable or invalid record
is {"state": "unknown", "basis": "none"} (never unexposed); a valid record is {"state": "exposed"} when any entry up to
the given seq names an exposing kind (EXPOSING), otherwise "unexposed", with basis structured-record and the record_ref.
Exposure only grows: entries are never removed, so a new session or a new record version never clears it. In
protected mode load_exposure() reads the record only as a protected input (custodian-written).

Usage: python3 contracts/lineage.py exposure RECORD [--previous FILE] [--record-ref REF] [--through N]
       python3 contracts/lineage.py decision DECISION --exposure RECORD [--artifacts-root DIR]
Exit codes: 0 valid, 1 invalid, 2 unreadable input. Output: JSON {"status", "findings", ...}; exposure also prints the
derived data_exposure, decision the exposure at decision time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.release_manifest import canonical_sha256  # noqa: E402
from contracts.schema import Report, validate  # noqa: E402

EXPOSING = frozenset({"signal-region", "unblinded-result", "sealed-value"})
UNKNOWN = {"state": "unknown", "basis": "none"}


def check_exposure(rec, rep: Report | None = None) -> Report:
    rep = validate(rec, "exposure_record.json") if rep is None else validate(rec, "exposure_record.json", report=rep)
    if not rep.ok:
        return rep
    prev_time = ""
    for i, e in enumerate(rec["entries"]):
        where = f"$.entries[{i}]"
        if e["seq"] != i + 1:
            rep.add("error", f"{where}.seq", "lineage.seq_gap", f"seq {e['seq']} where {i + 1} was expected")
        if e["time"] < prev_time:
            rep.add("error", f"{where}.time", "lineage.time_order", "dated before the entry before it")
        prev_time = max(prev_time, e["time"])
        if len(set(e["seen"])) != len(e["seen"]):
            rep.add("error", f"{where}.seen", "lineage.duplicate_kind", "a kind of data is listed twice")
    return rep


def check_append(previous, new) -> Report:
    """The new version extends the previous one: same analysis and source, previous entries unchanged, digest bound."""
    rep = Report()
    for name, doc in (("previous", previous), ("new", new)):
        sub = check_exposure(doc)
        for f in sub.findings:
            rep.add(f.severity, f"{name}:{f.path}", f.code, f.message)
    if not rep.ok:
        return rep
    if new["previous_sha256"] != canonical_sha256(previous):
        rep.add("error", "new:$.previous_sha256", "lineage.not_appended", "does not name the previous version's digest")
    if (new["analysis"], new["source"]) != (previous["analysis"], previous["source"]):
        rep.add("error", "new:$", "lineage.other_record", "another analysis or source snapshot")
    n = len(previous["entries"])
    if new["entries"][:n] != previous["entries"]:
        rep.add("error", "new:$.entries", "lineage.history_changed", "an earlier entry was removed or changed")
    return rep


def derive_exposure(rec, record_ref: str | None = None, through_seq: int | None = None) -> dict:
    """The envelope data_exposure for an exposure record (None: no record). See the module docstring."""
    if rec is None or not check_exposure(rec).ok:
        return dict(UNKNOWN)
    entries = rec["entries"] if through_seq is None else rec["entries"][:max(0, through_seq)]
    out = {"state": "exposed" if any(EXPOSING & set(e["seen"]) for e in entries) else "unexposed",
           "basis": "structured-record"}
    if record_ref:
        out["record_ref"] = record_ref
    return out


def load_exposure(path, protected: bool | None = None) -> dict | None:
    """The record at path, or None when it is missing, unreadable or not a JSON object (derive_exposure: unknown). In
    protected mode (the enclosing entry point's context, or protected=True) the record is a protected input written
    by the custodian (core.protected.trusted_input): a record the session's account could have written is refused,
    since it is the one input that can lower exposure."""
    from core.protected.guard import CURRENT
    from core.protected.trusted_input import read_protected
    ctx = CURRENT.get()
    if protected or (protected is None and ctx is not None and ctx.protected):
        chk = read_protected(path)
        if not chk.ok:
            return None
        data = chk.data or b""
    else:
        try:
            data = Path(path).read_bytes()
        except OSError:
            return None
    try:
        doc = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None
    return doc if isinstance(doc, dict) else None


def entries_digest(rec: dict, through_seq: int) -> str:
    return canonical_sha256(rec["entries"][:through_seq])


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_artifacts(dec: dict, base_dir: Path, rep: Report) -> None:
    """Each artifacts[].sha256 against the file's SHA-256 (ref resolved against base_dir unless absolute)."""
    for i, art in enumerate(dec["artifacts"]):
        path = Path(base_dir) / art["ref"]
        where = f"$.artifacts[{i}]"
        if not path.is_file():
            rep.add("error", f"{where}.ref", "lineage.artifact_missing", f"no file at {path}: its SHA-256 is not verified")
            continue
        try:
            actual = file_sha256(path)
        except OSError as exc:
            rep.add("error", f"{where}.ref", "lineage.artifact_unreadable", f"cannot read {path}: {exc}")
            continue
        if actual != art["sha256"]:
            rep.add("error", f"{where}.sha256", "lineage.artifact_mismatch",
                    f"{art['ref']}: file SHA-256 {actual} differs from the record")


def check_decision(dec, exposure=None, base_dir: Path | None = None) -> Report:
    rep = validate(dec, "decision_record.json")
    if not rep.ok:
        return rep
    if base_dir is not None:
        check_artifacts(dec, base_dir, rep)
    if exposure is None:
        rep.add("error", "$.seen", "lineage.exposure_unchecked", "no exposure record: what had been seen is not verified")
        return rep
    erep = check_exposure(exposure)
    if not erep.ok:
        rep.add("error", "$exposure", "lineage.exposure_invalid", ", ".join(sorted({f.code for f in erep.errors})))
        return rep
    if exposure["analysis"] != dec["analysis"]:
        rep.add("error", "$.analysis", "lineage.other_analysis", "the exposure record belongs to another analysis")
        return rep
    n, entries = dec["seen"]["through_seq"], exposure["entries"]
    if n > len(entries):
        rep.add("error", "$.seen.through_seq", "lineage.seen_beyond_record", "more entries than the exposure record holds")
        return rep
    if entries_digest(exposure, n) != dec["seen"]["entries_sha256"]:
        rep.add("error", "$.seen.entries_sha256", "lineage.seen_mismatch", "the seen entries differ from the exposure record")
        return rep
    if n and entries[n - 1]["time"] > dec["time"]:
        rep.add("error", "$.seen", "lineage.seen_after_decision", "an entry counted as seen is dated after the decision")
    later = [e["seq"] for e in entries[n:] if e["time"] < dec["time"]]
    if later:
        rep.add("error", "$.seen", "lineage.seen_understated",
                f"entries {later} are dated before the decision but not counted as seen")
    return rep


def decision_exposure(dec: dict, exposure: dict | None, record_ref: str | None = None) -> dict:
    """What had been seen when the decision was made, as a data_exposure (unknown unless the decision checks)."""
    if exposure is None or not check_decision(dec, exposure).ok:
        return dict(UNKNOWN)
    return derive_exposure(exposure, record_ref, dec["seen"]["through_seq"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("exposure")
    p.add_argument("record", type=Path)
    p.add_argument("--previous", type=Path)
    p.add_argument("--record-ref", dest="record_ref")
    p.add_argument("--through", type=int)
    p = sub.add_parser("decision")
    p.add_argument("decision", type=Path)
    p.add_argument("--exposure", type=Path, required=True)
    p.add_argument("--artifacts-root", dest="artifacts_root", type=Path,
                   help="folder that relative artifacts[].ref resolve against (default: the decision record's folder)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        first = json.loads((args.record if args.cmd == "exposure" else args.decision).read_text(encoding="utf-8"))
        other_path = args.previous if args.cmd == "exposure" else args.exposure
        other = None if other_path is None else json.loads(other_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    base = None
    if args.cmd == "decision":
        base = args.artifacts_root if args.artifacts_root is not None else args.decision.resolve().parent
        if not base.is_dir():
            print(json.dumps({"status": "unreadable", "error": f"--artifacts-root {base} is not a folder"}))
            return 2
    if args.cmd == "exposure":
        rep = check_exposure(first) if other is None else check_append(other, first)
        out = {"data_exposure": derive_exposure(first, args.record_ref, args.through)}
    else:
        rep = check_decision(first, other, base)
        out = {"exposure_at_decision": decision_exposure(first, other)}
    print(json.dumps({"status": "valid" if rep.ok else "invalid", **out,
                      "findings": [f.as_dict() for f in rep.findings]}, indent=1))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
