#!/usr/bin/env python3
"""Hash-chained revocation log, its head, and the reverse index from revoked subjects to their dependents (task P2,
C07, F07). Revocation lives outside every artifact, so revoking changes no artifact bytes or hashes.

The log is JSON Lines (contracts/schemas/revocation_event.json): a genesis record (seq 0, prev_sha256 all zeros, the
log_id), then events {seq, prev_sha256, subject: {kind, ref and/or sha256}, reason, time, actor}, each binding the
canonical SHA-256 of the record before it. The head (revocation_head.json) {head_version, log_id, count, last_sha256,
as_of, source} is written by the custodian after every append and at least every status period. verify() trusts a log
only with a head that matches it: an empty or unterminated file, a gap, an edited or reordered record, a record removed
from the end (the head counts more), a head for another log, a head older than the allowed status age or dated in the
future, and a head from another status source are all refusals. A refused log is never read as "nothing revoked":
RevocationStatus.ok is false and every lookup method refuses to answer.

In protected use (load(..., protected=True)) the log and the head must also be protected inputs: regular files the
running account neither owns, nor can write, nor can replace (contracts/trusted_input.py). The checks bind the content
to the head and the head to a source; who may write that source (the custodian identity) is the deployment's trust
anchor. A replayed older head that is still within the status age is not detected here: the age bounds that window.

The reverse index (build_index, affected) maps project files and the subjects they name to their dependents:
envelope inputs (by SHA-256 and by resolved ref), data_exposure.record_ref, release manifests (source -> release ->
every file with a released SHA-256), exposure records (release -> record), decision records (recipe -> decision ->
the artifacts it produced), attestations (bundle and recipe -> attestation), frozen bundles (files -> bundle) and
recipes (canonical digest). affected() returns the transitive closure; nothing is written.

Usage:
  revocation.py init LOG --log-id ID --actor NAME [--time T]            create a log with its genesis record
  revocation.py append LOG --kind K (--ref R | --sha256 H) --reason TEXT --actor NAME [--time T]
  revocation.py head LOG --source S [--as-of T]                         print the head for the log as it is now
  revocation.py verify LOG --head FILE --source S [--max-age S] [--now T] [--protected]
  revocation.py affected LOG --head FILE --source S --root DIR [--max-age S] [--now T] [--protected]
init, append and head are custodian operations (they write or describe the custodian's record); run by an agent on
synthetic data they are exercises. Times are YYYY-MM-DDTHH:MM:SSZ.
Exit codes: 0 ok, 1 refused (verify/affected), 2 unreadable input or bad usage. Output: JSON on stdout; findings name a
path and a code, never a revoked subject's content.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.release_manifest import _ts, canonical_sha256  # noqa: E402
from contracts.schema import Report, validate  # noqa: E402
from contracts.trusted_input import Account, read_protected, read_unchecked  # noqa: E402

LOG_FORMAT = "hep-research-revocation-log/1"
HEAD_VERSION = "1.0.0"
ZERO = "0" * 64
MAX_STATUS_AGE_S = 86400  # the stalest head any caller may accept (as contracts.attestation)
SUBJECT_KINDS = ("artifact", "release", "recipe", "source", "attestation")
SKIP_DIRS = frozenset({".git", "__pycache__", "node_modules", ".venv"})


def _now_text() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def encode(rec: dict) -> bytes:
    """One log line: canonical JSON and a newline."""
    return json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"


def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key")
    return dict(pairs)


# --- custodian-side writers (pure: they return records; the custodian writes them) ---------------------------------

def genesis(log_id: str, actor: str, created: str | None = None) -> dict:
    return {"seq": 0, "prev_sha256": ZERO,
            "genesis": {"log_format": LOG_FORMAT, "log_id": log_id, "created": created or _now_text(), "actor": actor}}


def next_event(records: list[dict], subject: dict, reason: str, actor: str, time: str | None = None) -> dict:
    ev = {"seq": len(records), "prev_sha256": canonical_sha256(records[-1]), "subject": subject, "reason": reason,
          "time": time or _now_text(), "actor": actor}
    rep = validate(ev, "revocation_event.json")
    if not rep.ok:
        raise ValueError("; ".join(f"{f.path}: {f.code}" for f in rep.errors))
    return ev


def head_of(records: list[dict], source: str, as_of: str | None = None) -> dict:
    return {"head_version": HEAD_VERSION, "log_id": records[0]["genesis"]["log_id"], "count": len(records),
            "last_sha256": canonical_sha256(records[-1]), "as_of": as_of or _now_text(), "source": source}


# --- verification ----------------------------------------------------------------------------------------------------

class RevocationUnverified(RuntimeError):
    """A lookup on a log that did not verify: there is no answer, in particular not 'nothing revoked'."""


@dataclass
class RevocationStatus:
    ok: bool
    findings: list[dict]
    log_id: str | None = None
    count: int = 0
    as_of: str | None = None
    source: str | None = None
    events: list[dict] = field(default_factory=list)
    log_sha256: str | None = None
    head_sha256: str | None = None

    def _require(self) -> None:
        if not self.ok:
            raise RevocationUnverified("the revocation log did not verify; its status is unknown")

    def revoked(self, kind: str | None = None, ref: str | None = None, sha256: str | None = None) -> dict | None:
        """The first event revoking a subject that matches (kind optional; ref or sha256), or None."""
        self._require()
        for ev in self.events:
            s = ev["subject"]
            if kind is not None and s["kind"] != kind:
                continue
            if (ref is not None and s.get("ref") == ref) or (sha256 is not None and s.get("sha256") == sha256):
                return ev
        return None

    def revoked_digests(self) -> set[str]:
        self._require()
        return {ev["subject"]["sha256"] for ev in self.events if "sha256" in ev["subject"]}

    def status_doc(self, kinds=SUBJECT_KINDS) -> dict:
        """The {as_of, source, revoked: [{ref, time, reason}]} shape that release_manifest.py and attestation.py read,
        for the given subject kinds; every ref and sha256 of a matching subject is listed as a ref."""
        self._require()
        revoked = []
        for ev in self.events:
            s = ev["subject"]
            if s["kind"] in kinds:
                for key in ("ref", "sha256"):
                    if key in s:
                        revoked.append({"ref": s[key], "time": ev["time"], "reason": ev["reason"]})
        return {"as_of": self.as_of, "source": self.source, "revoked": revoked}

    def summary(self) -> dict:
        return {"ok": self.ok, "log_id": self.log_id, "count": self.count, "as_of": self.as_of, "source": self.source,
                "log_sha256": self.log_sha256, "head_sha256": self.head_sha256, "findings": self.findings}


def is_chained_log(data: bytes) -> bool:
    """Whether the bytes start with a genesis record (the hash-chained format), as opposed to legacy JSON Lines."""
    first = data.split(b"\n", 1)[0]
    try:
        rec = json.loads(first.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return False
    return isinstance(rec, dict) and isinstance(rec.get("genesis"), dict)


def verify(log_bytes: bytes | None, head, *, source: str, now: datetime.datetime | None = None,
           max_age_s: int = MAX_STATUS_AGE_S) -> RevocationStatus:
    """Verify a log against its head (both already read). See the module docstring."""
    now = now or datetime.datetime.now(datetime.UTC)
    rep = Report()
    records: list[dict] = []
    if not (isinstance(max_age_s, int) and not isinstance(max_age_s, bool) and 0 < max_age_s <= MAX_STATUS_AGE_S):
        rep.add("error", "$max_age", "revocation.age_too_long", f"the allowed status age must be 1..{MAX_STATUS_AGE_S} s")
    if not (isinstance(source, str) and source):
        rep.add("error", "$source", "revocation.source_unchecked", "no expected status source: the head cannot be bound")
    if log_bytes is None:
        rep.add("error", "$log", "revocation.log_unreadable", "no revocation log")
    elif not log_bytes.strip():
        rep.add("error", "$log", "revocation.empty", "the log is empty: an empty file is not 'nothing revoked'")
    else:
        if not log_bytes.endswith(b"\n"):
            rep.add("error", "$log", "revocation.truncated_line", "the last record is not terminated: the log was cut")
        for n, line in enumerate(log_bytes.split(b"\n")[:-1] if log_bytes.endswith(b"\n") else log_bytes.split(b"\n"), 1):
            where = f"$log:{n}"
            try:
                rec = json.loads(line.decode("utf-8"), object_pairs_hook=_no_duplicates)
            except (UnicodeDecodeError, ValueError):
                rep.add("error", where, "revocation.bad_record", "not one JSON object per line")
                break
            schema = {"$ref": "revocation_event.json#/$defs/genesis"} if n == 1 else "revocation_event.json"
            srep = validate(rec, schema)
            if not srep.ok:
                code = "revocation.bad_genesis" if n == 1 else "revocation.bad_record"
                rep.add("error", where, code, "; ".join(sorted({f.code for f in srep.errors})))
                break
            if n > 1:
                if rec["seq"] != n - 1:
                    rep.add("error", where, "revocation.seq_gap", f"seq {rec['seq']} where {n - 1} was expected")
                    break
                if rec["prev_sha256"] != canonical_sha256(records[-1]):
                    rep.add("error", where, "revocation.chain_broken", "does not bind the record before it")
                    break
                if n > 2 and rec["time"] < records[-1]["time"]:
                    rep.add("error", where, "revocation.time_order", "dated before the record before it")
                    break
            records.append(rec)
    if not isinstance(head, dict) or not validate(head, "revocation_head.json").ok:
        rep.add("error", "$head", "revocation.head_malformed", "no valid head: the log's completeness is unknown")
        head = None
    if head is not None and rep.ok:
        as_of = _ts(head["as_of"])
        if head["source"] != source:
            rep.add("error", "$head.source", "revocation.other_source", "the head is not from the expected status source")
        if as_of is None or as_of > now or (now - as_of).total_seconds() > max_age_s:
            rep.add("error", "$head.as_of", "revocation.stale", f"the head is older than {max_age_s} s or dated in the future")
        if head["log_id"] != records[0]["genesis"]["log_id"]:
            rep.add("error", "$head.log_id", "revocation.head_other_log", "the head belongs to another log")
        elif head["count"] > len(records):
            rep.add("error", "$head.count", "revocation.truncated", "the log holds fewer records than the head counts")
        elif head["count"] < len(records) or head["last_sha256"] != canonical_sha256(records[-1]):
            rep.add("error", "$head", "revocation.head_mismatch", "the head does not describe this log")
        elif len(records) > 1 and records[-1]["time"] > head["as_of"]:
            rep.add("error", "$head.as_of", "revocation.event_after_head", "an event is dated after the head")
    ok = rep.ok
    return RevocationStatus(
        ok=ok, findings=[f.as_dict() for f in rep.findings],
        log_id=records[0]["genesis"]["log_id"] if ok else None, count=len(records) if ok else 0,
        as_of=head["as_of"] if ok and head else None, source=head["source"] if ok and head else None,
        events=records[1:] if ok else [],
        log_sha256=hashlib.sha256(log_bytes).hexdigest() if ok and log_bytes is not None else None,
        head_sha256=canonical_sha256(head) if ok and head else None)


def _read(path, protected: bool, account: Account | None, where: str, rep: list) -> bytes | None:
    chk = read_protected(path, account) if protected else read_unchecked(path)
    for code, msg in chk.refusals:
        rep.append({"severity": "error", "path": where, "code": code, "message": msg})
    return chk.data


def load(log_path, head_path, *, source: str, now: datetime.datetime | None = None, max_age_s: int = MAX_STATUS_AGE_S,
         protected: bool = False, account: Account | None = None) -> RevocationStatus:
    """Read and verify a log and its head from files; protected applies the source checks of trusted_input."""
    refusals: list[dict] = []
    log_bytes = None if log_path is None else _read(log_path, protected, account, "$log", refusals)
    head_bytes = None if head_path is None else _read(head_path, protected, account, "$head", refusals)
    if refusals:
        return RevocationStatus(ok=False, findings=refusals)
    head = None
    if head_bytes is not None:
        try:
            head = json.loads(head_bytes.decode("utf-8"), object_pairs_hook=_no_duplicates)
        except (UnicodeDecodeError, ValueError):
            head = None
    return verify(log_bytes, head, source=source, now=now, max_age_s=max_age_s)


# --- reverse index ---------------------------------------------------------------------------------------------------

def subject_keys(subject: dict) -> set[str]:
    """Index keys a revocation subject starts from."""
    keys = set()
    if subject.get("sha256"):
        keys.add(f"sha256:{subject['sha256']}")
    ref = subject.get("ref")
    if ref:
        kind = subject.get("kind")
        keys.add(f"path:{Path(ref).as_posix()}" if kind in ("artifact", "recipe") else f"{kind}:{ref}")
    return keys


@dataclass
class Index:
    root: str
    files: dict[str, str] = field(default_factory=dict)  # project-relative path -> file SHA-256
    edges: dict[str, set] = field(default_factory=dict)  # key -> keys that depend on it (or are the same thing)

    def link(self, dependency: str, dependent: str) -> None:
        self.edges.setdefault(dependency, set()).add(dependent)

    def same(self, a: str, b: str) -> None:
        self.link(a, b)
        self.link(b, a)

    def as_dict(self) -> dict:
        return {"root": self.root, "files": dict(sorted(self.files.items())),
                "edges": {k: sorted(v) for k, v in sorted(self.edges.items())}}


def _obj(value) -> dict:
    return value if isinstance(value, dict) else {}


def _json_files(root: Path):
    for parent, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not os.path.islink(os.path.join(parent, d)))
        for name in sorted(names):
            p = Path(parent) / name
            if p.suffix.lower() == ".json" and stat.S_ISREG(os.lstat(p).st_mode):
                yield p


def build_index(root) -> Index:
    """Scan every regular JSON file under root (links are not followed) and record what depends on what."""
    from core.partition.bundle import digest_of
    root = Path(root).resolve()
    idx = Index(str(root))
    for p in _json_files(root):
        rel = p.relative_to(root).as_posix()
        data = p.read_bytes()
        node = f"path:{rel}"
        sha = hashlib.sha256(data).hexdigest()
        idx.files[rel] = sha
        idx.same(node, f"sha256:{sha}")
        try:
            doc = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue
        if not isinstance(doc, dict):
            continue
        idx.same(node, f"sha256:{canonical_sha256(doc)}")
        if "artifact_type" in doc and "contract_version" in doc:
            for inp in doc.get("inputs") or []:
                if not isinstance(inp, dict):
                    continue
                if isinstance(inp.get("sha256"), str):
                    idx.link(f"sha256:{inp['sha256']}", node)
                ref = inp.get("ref")
                if isinstance(ref, str) and not inp.get("external"):
                    tgt = (root / ref).resolve() if not Path(ref).is_absolute() else Path(ref).resolve()
                    if tgt == root or root in tgt.parents:
                        idx.link(f"path:{tgt.relative_to(root).as_posix()}", node)
            rec = _obj(doc.get("data_exposure")).get("record_ref")
            if isinstance(rec, str):
                tgt = (p.parent / rec).resolve()
                if root in tgt.parents:
                    idx.link(f"path:{tgt.relative_to(root).as_posix()}", node)
        elif "manifest_version" in doc and isinstance(doc.get("release_id"), str):
            from contracts.release_manifest import manifest_digest
            rid = f"release:{doc['release_id']}"
            idx.same(node, rid)
            idx.same(node, f"sha256:{manifest_digest(doc)}")
            src = _obj(doc.get("source"))
            if isinstance(src.get("sha256"), str):
                idx.link(f"sha256:{src['sha256']}", rid)
            if isinstance(src.get("snapshot_id"), str):
                idx.link(f"source:{src['snapshot_id']}", rid)
            for a in doc.get("artifacts") or []:
                if isinstance(a, dict) and isinstance(a.get("sha256"), str):
                    idx.link(rid, f"sha256:{a['sha256']}")
        elif "attestation_version" in doc and isinstance(doc.get("attestation_id"), str):
            aid = f"attestation:{doc['attestation_id']}"
            idx.same(node, aid)
            lc = _obj(doc.get("lifecycle"))
            if isinstance(lc.get("revocation_ref"), str):
                idx.same(aid, f"attestation:{lc['revocation_ref']}")
            subj = _obj(doc.get("subject"))
            if isinstance(subj.get("bundle_sha256"), str):
                idx.link(f"sha256:{subj['bundle_sha256']}", aid)
            recipe = _obj(_obj(subj.get("scope")).get("recipe"))
            if isinstance(recipe.get("sha256"), str):
                idx.link(f"sha256:{recipe['sha256']}", aid)
        elif "record_version" in doc and "decision_id" in doc:
            if isinstance(doc.get("recipe_sha256"), str):
                idx.link(f"sha256:{doc['recipe_sha256']}", node)
            for a in doc.get("artifacts") or []:
                if isinstance(a, dict) and isinstance(a.get("sha256"), str):
                    idx.link(node, f"sha256:{a['sha256']}")
        elif "record_version" in doc and isinstance(doc.get("entries"), list) and "analysis" in doc:
            for e in doc["entries"]:
                if isinstance(e, dict) and isinstance(e.get("release_id"), str):
                    idx.link(f"release:{e['release_id']}", node)
        elif doc.get("format") == "hep-research-bundle/1":
            try:
                idx.same(node, f"sha256:{digest_of(doc)}")
            except (KeyError, TypeError):
                pass
            for f in doc.get("files") or []:
                if isinstance(f, dict) and isinstance(f.get("sha256"), str):
                    idx.link(f"sha256:{f['sha256']}", node)
    return idx


def affected(index: Index, subject: dict) -> list[str]:
    """Project files that are the subject or depend on it, transitively (sorted project-relative paths)."""
    seen: set[str] = set()
    todo = list(subject_keys(subject))
    while todo:
        k = todo.pop()
        if k in seen:
            continue
        seen.add(k)
        todo.extend(index.edges.get(k, ()))
    return sorted(k[len("path:"):] for k in seen if k.startswith("path:") and k[len("path:"):] in index.files)


def affected_by(index: Index, status: RevocationStatus) -> dict[str, list[int]]:
    """{project path: [seq of every event that reaches it]} for a verified log."""
    status._require()
    out: dict[str, list[int]] = {}
    for ev in status.events:
        for rel in affected(index, ev["subject"]):
            out.setdefault(rel, []).append(ev["seq"])
    return dict(sorted(out.items()))


# --- command line ----------------------------------------------------------------------------------------------------

def _read_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("log", type=Path)
    p.add_argument("--log-id", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--time")
    p = sub.add_parser("append")
    p.add_argument("log", type=Path)
    p.add_argument("--kind", required=True, choices=SUBJECT_KINDS)
    p.add_argument("--ref")
    p.add_argument("--sha256")
    p.add_argument("--reason", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--time")
    p = sub.add_parser("head")
    p.add_argument("log", type=Path)
    p.add_argument("--source", required=True)
    p.add_argument("--as-of", dest="as_of")
    for name in ("verify", "affected"):
        p = sub.add_parser(name)
        p.add_argument("log", type=Path)
        p.add_argument("--head", type=Path, required=True)
        p.add_argument("--source", required=True)
        p.add_argument("--max-age", dest="max_age", type=int, default=MAX_STATUS_AGE_S)
        p.add_argument("--now")
        p.add_argument("--protected", action="store_true",
                       help="the log and head must be files the running account neither owns nor can write or replace")
        if name == "affected":
            p.add_argument("--root", type=Path, required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    for t in ("time", "as_of", "now"):
        if getattr(args, t, None) and _ts(getattr(args, t)) is None:
            print(json.dumps({"status": "unreadable", "error": f"--{t.replace('_', '-')} must be YYYY-MM-DDTHH:MM:SSZ"}))
            return 2
    try:
        if args.cmd == "init":
            if args.log.exists():
                print(json.dumps({"status": "unreadable", "error": f"{args.log} exists: a log is created once"}))
                return 2
            rec = genesis(args.log_id, args.actor, args.time)
            with open(args.log, "xb") as fh:
                fh.write(encode(rec))
            print(json.dumps({"status": "ok", "record": rec}))
            return 0
        if args.cmd == "append":
            if not (args.ref or args.sha256):
                print(json.dumps({"status": "unreadable", "error": "give --ref or --sha256"}))
                return 2
            records = _read_records(args.log)
            subject = {"kind": args.kind, **({"ref": args.ref} if args.ref else {}),
                       **({"sha256": args.sha256} if args.sha256 else {})}
            ev = next_event(records, subject, args.reason, args.actor, args.time)
            with open(args.log, "ab") as fh:
                fh.write(encode(ev))
            print(json.dumps({"status": "ok", "record": ev}))
            return 0
        if args.cmd == "head":
            print(json.dumps(head_of(_read_records(args.log), args.source, args.as_of), indent=1))
            return 0
    except (OSError, ValueError, KeyError, IndexError) as exc:
        print(json.dumps({"status": "unreadable", "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    st = load(args.log, args.head, source=args.source, now=_ts(args.now) if args.now else None,
              max_age_s=args.max_age, protected=args.protected)
    out = {"status": "ok" if st.ok else "refused", **st.summary()}
    if args.cmd == "affected" and st.ok:
        if args.root.is_symlink() or not args.root.is_dir():
            print(json.dumps({"status": "unreadable", "error": f"{args.root}: not a directory (a link is never followed)"}))
            return 2
        out["affected"] = affected_by(build_index(args.root), st)
    print(json.dumps(out, indent=1))
    return 0 if st.ok else 1


if __name__ == "__main__":
    sys.exit(main())
