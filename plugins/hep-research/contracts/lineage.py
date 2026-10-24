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
compares its file SHA-256 with artifacts[].sha256 (except an entry of a 1.1.0 measurement-acceptance record bound by
binding "parameters", whose parameter_digest contracts/design.py compares, DEC-06): a different hash is lineage.artifact_mismatch, a ref that is not a
readable file lineage.artifact_missing or lineage.artifact_unreadable, all errors (as a missing exposure record is).
Without base_dir (an in-memory record with no location) artifacts are not opened.

Decision record 1.1.0 (contracts 3.11.0, detector system design DEC-03..DEC-16): the six design categories
(DESIGN_CATEGORIES) need at least one artifact; only they may carry dispositions[] or the seen marker
{"state": "not-applicable"}, and a 1.0.0 record uses none of the 1.1.0 additions (lineage.needs_1_1_0). A record with the
marker needs no exposure record, but its input closure is checked (check_not_applicable, DEC-15): the closure of each
artifacts[].ref from contracts/dependencies.py (validate_dependencies 'checked') is opened and the marker is refused
(lineage.not_applicable_refused) when it holds a dataset-record with extension.status published or preliminary, an
artifact whose status includes observed, an external input, or a protected input (a path under the enclosing project
configuration's agent_policy protected_paths or protected_inputs); without base_dir the closure cannot be read and the
marker is refused (lineage.closure_unchecked).

derive_exposure(record) is the only mapping to the envelope data_exposure: no record, an unreadable or invalid record
is {"state": "unknown", "basis": "none"} (never unexposed); a valid record is {"state": "exposed"} when any entry up to
the given seq names an exposing kind (EXPOSING), otherwise "unexposed", with basis structured-record and the record_ref.
Exposure only grows: entries are never removed, so a new session or a new record version never clears it. In
protected mode load_exposure() reads the record only as a protected input (custodian-written).

Usage: python3 contracts/lineage.py exposure RECORD [--previous FILE] [--record-ref REF] [--through N]
       python3 contracts/lineage.py decision DECISION [--exposure RECORD] [--artifacts-root DIR]
       (--exposure is required unless the record's seen is the 1.1.0 not-applicable marker)
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
DESIGN_CATEGORIES = frozenset({"design-scope", "requirements-baseline", "architecture-selection", "design-baseline",
                               "requirement-change", "measurement-acceptance"})
NOT_APPLICABLE = {"state": "not-applicable"}
PROJECT_CONFIG = "hep-research.project.json"
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
        if actual != art["sha256"] and art.get("binding") != "parameters":  # DEC-06: digest checked by design.py
            rep.add("error", f"{where}.sha256", "lineage.artifact_mismatch",
                    f"{art['ref']}: file SHA-256 {actual} differs from the record")


def _protected_paths(base_dir: Path) -> list[Path]:
    """Protected paths of the project configuration enclosing base_dir (agent_policy protected_paths and
    protected_inputs), resolved against the configuration's folder."""
    for d in [base_dir, *base_dir.parents][:6]:
        cfg = d / PROJECT_CONFIG
        if cfg.is_file():
            try:
                doc = json.loads(cfg.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                return []
            pol = doc.get("agent_policy") if isinstance(doc, dict) else None
            if not isinstance(pol, dict):
                return []
            raw = list(pol.get("protected_paths") or []) + [v for v in (pol.get("protected_inputs") or {}).values()
                                                             if isinstance(v, str)]
            return [(d / r).resolve() for r in raw if isinstance(r, str)]
    return []


def check_not_applicable(dec: dict, base_dir: Path | None, rep: Report) -> None:
    """DEC-15: the not-applicable marker is refused when the input closure of artifacts[] holds experimental,
    observed, external or protected data (see the module docstring)."""
    if base_dir is None:
        rep.add("error", "$.seen", "lineage.closure_unchecked",
                "the not-applicable marker needs the artifacts' folder: an unread closure cannot be ruled out")
        return
    from contracts.dependencies import validate_dependencies  # lazy: dependencies imports the validator stack
    base = Path(base_dir).resolve()
    protected = _protected_paths(base)
    for i, art in enumerate(dec["artifacts"]):
        where = f"$.artifacts[{i}]"
        path = (base / art["ref"]).resolve()
        if not path.is_file():
            continue  # check_artifacts already reports it
        deps = validate_dependencies(path, base)
        if deps.get("protected") and deps["status"] == "error" and not deps["checked"]:
            rep.add("error", where, "lineage.not_applicable_refused",
                    "protected use refused reading the closure: it cannot be ruled out")
            continue
        closure = [path] + [(base / c).resolve() for c in deps["checked"]]
        for f in deps["findings"]:
            if f["code"] == "dependency.external_unresolved":
                rep.add("error", where, "lineage.not_applicable_refused", f"external input in the closure: {f['path']}")
            elif f["code"] == "dependency.outside_root":
                rep.add("error", where, "lineage.not_applicable_refused", f"input outside the folder: {f['path']}")
        for src in closure:
            if any(src == p or p in src.parents for p in protected):
                rep.add("error", where, "lineage.not_applicable_refused", f"protected input {src}")
                continue
            try:
                doc = json.loads(src.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                rep.add("error", where, "lineage.not_applicable_refused", f"unreadable input {src}")
                continue
            if not isinstance(doc, dict):
                continue
            ext: dict = doc["extension"] if isinstance(doc.get("extension"), dict) else {}
            if doc.get("artifact_type") == "dataset-record" and ext.get("status") in ("published", "preliminary"):
                rep.add("error", where, "lineage.not_applicable_refused",
                        f"{src.name} is experimental data (dataset-record status {ext.get('status')})")
            if "observed" in (doc.get("status") or []):
                rep.add("error", where, "lineage.not_applicable_refused", f"{src.name} carries 'observed'")


def check_version_use(dec: dict, rep: Report) -> None:
    """1.1.0 additions only in 1.1.0 records and only for design categories (DEC-04, DEC-11, DEC-13, DEC-14)."""
    design = dec["category"] in DESIGN_CATEGORIES
    marker = dec["seen"] == NOT_APPLICABLE
    if dec["record_version"] == "1.0.0" and (design or marker or "dispositions" in dec):
        rep.add("error", "$.record_version", "lineage.needs_1_1_0",
                "design categories, the not-applicable marker and dispositions need record_version 1.1.0")
    if not design and marker:
        rep.add("error", "$.seen", "lineage.not_applicable_not_design", "only design records may mark seen not-applicable")
    if not design and "dispositions" in dec:
        rep.add("error", "$.dispositions", "lineage.dispositions_not_design", "only design records carry dispositions")
    bound = [a for a in dec["artifacts"] if "binding" in a or "parameter_digest" in a]
    if bound and (dec["category"] != "measurement-acceptance" or dec["record_version"] != "1.1.0"
                  or any(a.get("binding") != "parameters" or "parameter_digest" not in a for a in bound)):
        rep.add("error", "$.artifacts", "lineage.binding_not_allowed",
                "only a 1.1.0 measurement-acceptance record binds candidates by binding 'parameters' with a parameter_digest")
    if design and not dec["artifacts"]:
        rep.add("error", "$.artifacts", "lineage.design_no_artifacts", "a design record lists at least one artifact")


def check_decision(dec, exposure=None, base_dir: Path | None = None) -> Report:
    rep = validate(dec, "decision_record.json")
    if not rep.ok:
        return rep
    check_version_use(dec, rep)
    if base_dir is not None:
        check_artifacts(dec, base_dir, rep)
    if dec["seen"] == NOT_APPLICABLE:  # DEC-14..DEC-16: no exposure applies; the closure is checked instead
        if rep.ok:
            check_not_applicable(dec, base_dir, rep)
        return rep
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
    if exposure is None or not isinstance(dec.get("seen"), dict) or "through_seq" not in dec["seen"] \
            or not check_decision(dec, exposure).ok:
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
    p.add_argument("--exposure", type=Path,
                   help="the exposure record; required unless seen is the not-applicable marker (1.1.0)")
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
        if other is None and not (isinstance(first, dict) and first.get("seen") == NOT_APPLICABLE):
            print(json.dumps({"status": "unreadable", "error": "--exposure is required unless seen is not-applicable"}))
            return 2
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
