"""The hep-review store: location checks and the append-only SQLite commit log (hep-review spec v9 11.1, 11.2, 11.5).

One writer (the coordinator), single host, local disk. Each commit is a metadata object chained by
prev_commit_digest; objects never change bytes; corrections are new objects or a new segment. The chain detects change
only relative to a trusted anchor outside the store (continuity.py). Connections use isolation_level=None with
explicit BEGIN IMMEDIATE / COMMIT / ROLLBACK; blobs are written and verified before any commit references them. No
model, network call or long work runs inside a write transaction.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from contracts import hep_review as H
from contracts.schema import SCHEMA_DIR as SCHEMAS
from contracts.schema import validate as schema_validate
from hep_review_support import submissions as SUB

UNSUPPORTED_FS = {"nfs", "nfs4", "cifs", "smbfs", "smb", "smb2", "smb3", "afpfs", "webdav", "9p", "virtiofs",
                  "osxfuse", "macfuse", "sshfs"}
SYNC_MARKERS = ("Library/Mobile Documents", "Library/CloudStorage", "Dropbox", "OneDrive", "Google Drive",
                "GoogleDrive", "iCloud Drive")
APPROVED_VALIDATORS = (H.LATEST_VALIDATOR,)
HOST_PROFILE = Path(__file__).resolve().parents[2] / "assets" / "host_profile.json"
DB_NAME = "hep-review.sqlite3"
BUSY_TIMEOUT_MS = 5000


class StoreLocationRefused(Exception):
    """The intended store location is unsupported (network, FUSE, VM mount, synced folder or unknown type)."""


class HeadMismatch(Exception):
    """CAS failure: the expected head is not the current head."""


class OperationConflict(Exception):
    """An operation_id was reused with a different payload."""


class AdmissionRefused(Exception):
    """The commit was refused by the admission checks; `codes` lists why."""

    def __init__(self, errors: list[dict]):
        self.errors = errors
        self.codes = [e["code"] for e in errors]
        super().__init__("; ".join(f"{e['code']}: {e['message']}" for e in errors))


class ValidatorNotApproved(Exception):
    """A current report was asked for with a validator version that is not the latest approved one."""


@dataclass
class AppendResult:
    status: str  # committed | replayed
    head: dict


def _err(code: str, message: str) -> dict:
    return {"code": code, "path": "$", "message": message}


def default_store_dir(env: dict | None = None) -> Path:
    """$XDG_STATE_HOME/hep-research/hep-review, else ~/.local/state/hep-research/hep-review (the repository's
    convention for private state; outside the project under review)."""
    env = os.environ if env is None else env
    base = env.get("XDG_STATE_HOME") or str(Path(env.get("HOME", str(Path.home()))) / ".local" / "state")
    return Path(base) / "hep-research" / "hep-review"


def _mounts(platform: str) -> str:
    if platform.startswith("linux"):
        try:
            return Path("/proc/self/mountinfo").read_text()
        except OSError:
            return ""
    try:
        return subprocess.run(["mount"], capture_output=True, text=True, timeout=10, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _parse_mounts(text: str, platform: str) -> list[tuple[str, str]]:
    out = []
    for line in text.splitlines():
        if platform.startswith("linux"):
            parts = line.split()
            if " - " in line and len(parts) > 5:
                fstype = line.split(" - ", 1)[1].split()[0]
                out.append((parts[4].replace("\\040", " "), fstype))
        elif " on " in line and " (" in line:
            rest = line.split(" on ", 1)[1]
            mp, opts = rest.rsplit(" (", 1)
            out.append((mp, opts.split(",")[0].strip(" )")))
    return out


def filesystem_type(path: str | Path, *, mounts_text: str | None = None, platform: str | None = None) -> str | None:
    platform = platform or sys.platform
    text = _mounts(platform) if mounts_text is None else mounts_text
    p = str(path)
    best, fstype = -1, None
    for mp, fs in _parse_mounts(text, platform):
        if (p == mp or p.startswith(mp.rstrip("/") + "/") or mp == "/") and len(mp) > best:
            best, fstype = len(mp), fs
    return fstype


def _resolved(path: str | Path) -> str:
    """The real path of the nearest existing ancestor, plus the rest: a symlink into a synced or network folder is
    judged by where it leads (review M3)."""
    p = Path(path).absolute()
    rest: list[str] = []
    while not p.exists() and p != p.parent:
        rest.insert(0, p.name)
        p = p.parent
    return str(Path(os.path.realpath(p)).joinpath(*rest))


def check_location(path: str | Path, *, mounts_text: str | None = None, platform: str | None = None) -> dict:
    """Filesystem type and sync status of an intended store location (spec 11.1), judged on the resolved path.
    Unknown type -> unsupported."""
    p = _resolved(path)
    fs = filesystem_type(p, mounts_text=mounts_text, platform=platform)
    sync = any(m in p for m in SYNC_MARKERS)
    if fs is None:
        ok, reason = False, "filesystem type could not be determined; ask the user for a local location"
    elif fs in UNSUPPORTED_FS or fs.startswith("fuse"):
        ok, reason = False, f"{fs} is a network, FUSE or VM-mounted filesystem"
    elif sync:
        ok, reason = False, "the path is inside a synced folder"
    else:
        ok, reason = True, f"local {fs}"
    return {"path": p, "fs_type": fs, "sync_folder": sync, "supported": ok, "reason": reason}


def check_current_validator(version: str, approved: tuple[str, ...] = APPROVED_VALIDATORS) -> bool:
    """A current report uses only the latest approved validator (spec 7.3; case N61). The kernel stays pure; this is
    the I/O-side check."""
    if not approved or version != approved[-1]:
        raise ValidatorNotApproved(f"validator {version} is not the latest approved ({approved[-1] if approved else None})")
    return True


TABLE_DEFINITIONS = """
CREATE TABLE IF NOT EXISTS objects(context_id TEXT NOT NULL, segment_id TEXT NOT NULL, kind TEXT NOT NULL,
  logical_id TEXT NOT NULL, digest TEXT NOT NULL, bytes BLOB NOT NULL,
  PRIMARY KEY(context_id, segment_id, kind, logical_id));
CREATE TABLE IF NOT EXISTS commits(context_id TEXT NOT NULL, segment_id TEXT NOT NULL, seq INTEGER NOT NULL,
  digest TEXT NOT NULL UNIQUE, operation_id TEXT NOT NULL, payload_digest TEXT NOT NULL, header BLOB NOT NULL,
  PRIMARY KEY(context_id, segment_id, seq));
CREATE UNIQUE INDEX IF NOT EXISTS commits_operation ON commits(context_id, operation_id);
CREATE TABLE IF NOT EXISTS commit_objects(commit_digest TEXT NOT NULL, position INTEGER NOT NULL, kind TEXT NOT NULL,
  logical_id TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(commit_digest, position));
CREATE TABLE IF NOT EXISTS heads(context_id TEXT PRIMARY KEY, segment_id TEXT NOT NULL, seq INTEGER NOT NULL,
  commit_digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS segments(context_id TEXT NOT NULL, segment_id TEXT NOT NULL, genesis_digest TEXT NOT NULL,
  origin BLOB, PRIMARY KEY(context_id, segment_id));
CREATE TABLE IF NOT EXISTS blobs(digest TEXT PRIMARY KEY, size INTEGER NOT NULL);
"""


def _raw_refs(value):
    stack = [value]
    while stack:
        v = stack.pop()
        if isinstance(v, dict):
            if v.get("profile_id") == H.RAW_PROFILE and isinstance(v.get("digest"), str):
                yield v["digest"]
            stack.extend(v.values())
        elif isinstance(v, list):
            stack.extend(v)


class Store:
    """The commit log of every context in one directory: <dir>/hep-review.sqlite3 and <dir>/blobs/<sha256>."""

    def __init__(self, directory: str | Path, *, location: dict | None = None, host_profile: dict | None = None):
        directory = Path(directory)
        loc = location if location is not None else check_location(directory.parent if not directory.exists()
                                                                    else directory)
        if not loc.get("supported"):
            raise StoreLocationRefused(f"{loc.get('path')}: {loc.get('reason')} (no live backend; no JSON fallback)")
        self.location = loc
        self.host = host_profile if host_profile is not None else json.loads(HOST_PROFILE.read_text("utf-8"))
        self.host_digest = H.metadata_digest(self.host)
        self.dir = directory
        (self.dir / "blobs").mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.dir / DB_NAME, isolation_level=None, timeout=BUSY_TIMEOUT_MS / 1000)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        self.conn.executescript(TABLE_DEFINITIONS)

    def close(self) -> None:
        self.conn.close()

    def settings(self) -> dict:
        sync = self.conn.execute("PRAGMA synchronous").fetchone()[0]
        return {"journal_mode": self.conn.execute("PRAGMA journal_mode").fetchone()[0],
                "synchronous": {0: "off", 1: "normal", 2: "full", 3: "extra"}.get(sync, str(sync)),
                "busy_timeout_ms": BUSY_TIMEOUT_MS, "sqlite_version": sqlite3.sqlite_version,
                "python": sys.version.split()[0], "location": self.location}

    # -- blobs -------------------------------------------------------------------------------------------------------
    def put_blob(self, content: bytes) -> str:
        """Write, sync and verify a blob outside any transaction; an unreferenced blob is an orphan, not committed."""
        digest = hashlib.sha256(content).hexdigest()
        target = self.dir / "blobs" / digest
        if not target.exists():
            temp_path = self.dir / "blobs" / f".{digest}.{os.getpid()}.temp_path"
            with open(temp_path, "wb") as fh:
                fh.write(content)
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(temp_path, 0o444)
            os.replace(temp_path, target)
        if self.blob_status(digest) != "ok":
            raise OSError(f"blob {digest} did not verify after writing")
        self.conn.execute("INSERT OR IGNORE INTO blobs(digest, size) VALUES(?, ?)", (digest, len(content)))
        return digest

    def blob_status(self, digest: str) -> str:
        p = self.dir / "blobs" / digest
        try:
            content = p.read_bytes()
        except OSError:
            return "missing"
        return "ok" if hashlib.sha256(content).hexdigest() == digest else "changed"

    def read_blob(self, digest: str) -> bytes:
        content = (self.dir / "blobs" / digest).read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise OSError(f"blob {digest} changed after it was written")
        return content

    def orphan_blobs(self, context_id: str) -> list[str]:
        used: set[str] = set()
        for (raw,) in self.conn.execute("SELECT bytes FROM objects WHERE context_id=?", (context_id,)):
            used.update(_raw_refs(json.loads(raw)))
        return sorted(d for (d,) in self.conn.execute("SELECT digest FROM blobs") if d not in used)

    # -- heads and commits -------------------------------------------------------------------------------------------
    def head(self, context_id: str) -> dict | None:
        row = self.conn.execute("SELECT segment_id, seq, commit_digest FROM heads WHERE context_id=?",
                                (context_id,)).fetchone()
        return None if row is None else {"segment_id": row[0], "seq": row[1], "commit_digest": row[2]}

    def segments(self, context_id: str) -> list[dict]:
        return [{"segment_id": s, "genesis_digest": g, "origin": json.loads(o) if o else None}
                for s, g, o in self.conn.execute("SELECT segment_id, genesis_digest, origin FROM segments WHERE "
                                                 "context_id=? ORDER BY rowid", (context_id,))]

    def commit_by_digest(self, context_id: str, digest: str) -> dict | None:
        row = self.conn.execute("SELECT segment_id, seq FROM commits WHERE context_id=? AND digest=?",
                                (context_id, digest)).fetchone()
        return None if row is None else {"segment_id": row[0], "seq": row[1]}

    def commit_at(self, context_id: str, segment_id: str, seq: int) -> dict | None:
        row = self.conn.execute("SELECT digest, header FROM commits WHERE context_id=? AND segment_id=? AND seq=?",
                                (context_id, segment_id, seq)).fetchone()
        return None if row is None else {"digest": row[0], "commit": json.loads(row[1])}

    def _segment_objects(self, context_id: str, segment_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT o.bytes FROM commits c JOIN commit_objects co ON co.commit_digest=c.digest JOIN objects o ON "
            "o.context_id=c.context_id AND o.segment_id=c.segment_id AND o.kind=co.kind AND o.logical_id=co.logical_id "
            "WHERE c.context_id=? AND c.segment_id=? ORDER BY c.seq, co.position", (context_id, segment_id)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def _admit(self, context_id: str, segment_id: str, objects: list[dict]) -> list[dict]:
        """Admission checks inside the write transaction (spec 11.2 step 2): object rules, id reuse, blobs present,
        plan ancestry and the downgrade list, assignment bindings. Review records are admitted whenever their
        object rules hold: their disposition (quarantine) is computed by the validator, and the raw original is kept."""
        errs: list[dict] = []
        existing = self._segment_objects(context_id, segment_id)
        seen = {(o["record_kind"], o["id"]): H.metadata_digest(o) for o in existing}
        prior = list(existing)
        carried: set[str] | None = None
        for o in objects:
            for e in H.check_object(o):
                errs.append(e)
            if isinstance(o.get("protocol"), str) and o["protocol"] in H.EXPERIMENTAL_PROTOCOLS:
                # after the freeze (spec 5.3) a 0.x object is only ever carried unchanged into a new segment
                if carried is None:
                    carried = {H.metadata_digest(x) for s in self.segments(context_id)
                               for x in self._segment_objects(context_id, s["segment_id"])}
                if H.metadata_digest(o) not in carried:
                    errs.append(_err("object.experimental_write", f"{o.get('id')}: new objects use {H.PROTOCOL}; "
                                     "hep-review/0 objects are only carried unchanged"))
            kind_name = str(o.get("record_kind", "")).replace("-", "_")
            if (SCHEMAS / f"hep_review_{kind_name}.json").is_file():
                rep = schema_validate(o, f"hep_review_{kind_name}.json")
                errs.extend(_err("schema." + f.code.split(".", 1)[-1], f"{f.path}: {f.message}")
                            for f in rep.errors)
            if o.get("context_id") != context_id:
                errs.append(_err("object.context", f"{o.get('id')} belongs to another context"))
            key = (o.get("record_kind"), o.get("id"))
            if key in seen:
                errs.append(_err("object.id_reused", f"{key} is already committed (ids never change bytes)"))
            for d in _raw_refs(o):
                if self.blob_status(d) != "ok":
                    errs.append(_err("blob.missing", f"{o.get('id')} references blob {d} that is not stored"))
            kind = o.get("record_kind")
            intents = [x for x in prior if x["record_kind"] == "intent"]
            plans = {x["revision"]: x for x in prior if x["record_kind"] == "plan"}
            if kind == "intent" and intents:
                errs.append(_err("intent.revision_unsupported", "intent revisions (authorized change-requests) are "
                                   "T07 work and not implemented"))
            if kind == "plan":
                head_rev = max(plans) if plans else 0
                if o.get("revision") != head_rev + 1 or o.get("parent_revision") != (head_rev or None):
                    errs.append(_err("plan.ancestry", f"plan revision {o.get('revision')} does not follow the head "
                                       f"plan revision {head_rev}"))
                if not intents:
                    errs.append(_err("plan.intent", "no intent is committed"))
                else:
                    errs.extend(H.check_plan(o, plans.get(head_rev), intents[-1]))
            if kind == "assignment":
                p = plans.get(o.get("plan_revision"))
                if p is None or o.get("spec_id") not in {s.get("id") for s in p.get("assignment_specs", [])}:
                    errs.append(_err("assignment.binding", "the assignment names no spec of a committed plan "
                                       "revision"))
                errs.extend(self._assignment_bases(o))
            if kind == "record":
                errs.extend(self._derived(o, prior))
            if kind == "supply" and not any(x.get("record_kind") == "assignment" and x.get("id") == o.get(
                    "assignment_id") for x in prior):
                errs.append(_err("supply.binding", "supplied material names no committed assignment"))
            seen[key] = H.metadata_digest(o)
            prior.append(o)
        return errs

    def _assignment_bases(self, a: dict) -> list[dict]:
        """Condition bases may not exceed what the bound host profile can observe (spec 4.3, 12.2; review B3)."""
        errs = []
        caps = self.host.get("capabilities", {})
        if a.get("host_profile_digest") != self.host_digest:
            errs.append(_err("assignment.host_profile", "the assignment is not bound to this store's host profile"))
        cond = a.get("conditions", {})
        others = cond.get("no-other-evaluations-seen", {})
        if others.get("basis") == "observed" and others.get("satisfied") is True \
                and caps.get("filesystem_isolation", {}).get("value") is not True:
            errs.append(_err("assignment.basis_exceeds_host", "no-other-evaluations-seen cannot be observed without "
                             "observed filesystem isolation; on this host it is advisory"))
        fresh = cond.get("fresh-context", {})
        dispatch = a.get("dispatch") or {}
        if fresh.get("basis") == "observed" and fresh.get("satisfied") is True and not (
                dispatch.get("via") == "agent-tool" and isinstance(dispatch.get("invocation_id"), str)
                and dispatch["invocation_id"] and caps.get("fresh_context_subagents", {}).get("value") is True):
            errs.append(_err("assignment.basis_exceeds_host", "an observed fresh context needs the host's dispatch "
                             "record (agent-tool invocation id)"))
        if cond.get("non-author", {}).get("basis") == "observed":
            errs.append(_err("assignment.basis_exceeds_host", "authorship is declared, never observed by this host"))
        return errs

    def _derived(self, rec: dict, prior: list[dict]) -> list[dict]:
        """A review record must be exactly what its stored raw submission gives (spec 12.4; review B4). Only
        submission records have a raw-derivation path in this version; others are refused until one exists."""
        if rec.get("type") != "submission":
            return [_err("record.type_not_derivable", f"{rec.get('type')} records have no raw-derivation path yet "
                         "(T04); they cannot be committed")]
        asg = next((x for x in prior if x.get("record_kind") == "assignment" and x.get("id") == rec.get(
            "assignment_id")), None)
        ref = rec.get("raw_submission_ref") or {}
        if asg is None or self.blob_status(str(ref.get("digest"))) != "ok":
            return []  # binding and blob errors are reported by their own checks
        try:
            expected = SUB.parse(prior, asg, self.read_blob(ref["digest"]), ref, rec.get("submission_fidelity"),
                                 executor=self.host.get("reviewer_executor", "reviewer"), record_id=rec.get("id"),
                                 declared_digest=rec.get("declared_digest"))
        except (StopIteration, KeyError, TypeError):
            return [_err("record.not_derived_from_raw", "the record's plan or manifest cannot be found")]
        if H.encode(expected) != H.encode(rec):
            return [_err("record.not_derived_from_raw", "the record differs from what its stored raw submission "
                         "gives: it was edited or retyped")]
        return []

    def append(self, context_id: str, objects: list[dict], expected_head: dict | None, operation_id: str, *,
               writer_session_id: str, validator_version: str = H.LATEST_VALIDATOR,
               _after_insert: Callable[[], None] | None = None, _genesis_origin: dict | None = None,
               _segment_id: str | None = None) -> AppendResult:
        """Atomic append with CAS on expected_head and idempotency on operation_id (spec 11.2). expected_head comes from
        the coordinator's out-of-store sequence (continuity.py), never from a fresh read made just to pass the CAS."""
        refs = sorted((H.object_ref(o) for o in objects), key=lambda r: r["digest"])
        payload_digest = H.metadata_digest({"objects": refs, "head_changes": {}})
        c = self.conn
        c.execute("BEGIN IMMEDIATE")
        try:
            row = c.execute("SELECT segment_id, seq, digest, payload_digest FROM commits WHERE context_id=? AND "
                            "operation_id=?", (context_id, operation_id)).fetchone()
            if row is not None:
                c.execute("ROLLBACK")
                if row[3] != payload_digest:
                    raise OperationConflict(f"{operation_id} was committed with another payload")
                return AppendResult("replayed", {"segment_id": row[0], "seq": row[1], "commit_digest": row[2]})
            head = self.head(context_id)
            if _genesis_origin is None and head != expected_head:
                raise HeadMismatch(f"expected head {expected_head}, current {head}")
            if _genesis_origin is not None:
                if head != expected_head:
                    raise HeadMismatch(f"expected head {expected_head}, current {head}")
                segment_id, seq, prev = str(_segment_id), 1, None
            elif head is None:
                segment_id, seq, prev = "seg-1", 1, None
            else:
                segment_id, seq, prev = head["segment_id"], head["seq"] + 1, head["commit_digest"]
            errs = self._admit(context_id, segment_id, objects)
            if errs:
                raise AdmissionRefused(errs)
            header = {"protocol": H.PROTOCOL, "context_id": context_id, "segment_id": segment_id, "seq": seq,
                      "prev_commit_digest": prev, "operation_id": operation_id, "payload_digest": payload_digest,
                      "validator_version": validator_version, "writer_session_id": writer_session_id}
            if _genesis_origin:
                header.update(_genesis_origin)
            digest = H.metadata_digest(header)
            for pos, o in enumerate(objects):
                c.execute("INSERT INTO objects VALUES(?,?,?,?,?,?)", (context_id, segment_id, o["record_kind"],
                                                                     o["id"], H.metadata_digest(o), H.encode(o)))
                c.execute("INSERT INTO commit_objects VALUES(?,?,?,?,?)",
                          (digest, pos, o["record_kind"], o["id"], H.metadata_digest(o)))
            c.execute("INSERT INTO commits VALUES(?,?,?,?,?,?,?)", (context_id, segment_id, seq, digest, operation_id,
                                                                    payload_digest, H.encode(header)))
            if seq == 1:
                c.execute("INSERT INTO segments VALUES(?,?,?,?)", (context_id, segment_id, digest,
                                                                   json.dumps(_genesis_origin) if _genesis_origin
                                                                   else None))
            c.execute("INSERT OR REPLACE INTO heads VALUES(?,?,?,?)", (context_id, segment_id, seq, digest))
            if _after_insert is not None:
                _after_insert()
            c.execute("COMMIT")
        except BaseException:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise
        return AppendResult("committed", {"segment_id": segment_id, "seq": seq, "commit_digest": digest})

    def insert_verbatim(self, context_id: str, segment_id: str, commits: list[dict], origin: dict | None) -> None:
        """Rebuild a context from a verified export: the same commit headers, digests and object bytes, in one
        transaction (used only by export.import_export after verify_export passed)."""
        c = self.conn
        c.execute("BEGIN IMMEDIATE")
        try:
            if self.head(context_id) is not None:
                raise ValueError(f"context {context_id} already exists")
            for x in commits:
                header, digest = x["commit"], x["digest"]
                if H.metadata_digest(header) != digest:
                    raise ValueError(f"commit {header.get('seq')} digest does not match")
                for pos, o in enumerate(x["objects"]):
                    c.execute("INSERT INTO objects VALUES(?,?,?,?,?,?)", (context_id, segment_id, o["record_kind"],
                                                                         o["id"], H.metadata_digest(o), H.encode(o)))
                    c.execute("INSERT INTO commit_objects VALUES(?,?,?,?,?)",
                              (digest, pos, o["record_kind"], o["id"], H.metadata_digest(o)))
                c.execute("INSERT INTO commits VALUES(?,?,?,?,?,?,?)",
                          (context_id, segment_id, header["seq"], digest, header["operation_id"],
                           header["payload_digest"], H.encode(header)))
                if header["seq"] == 1:
                    c.execute("INSERT INTO segments VALUES(?,?,?,?)", (context_id, segment_id, digest,
                                                                       json.dumps(origin) if origin else None))
            last = commits[-1]
            c.execute("INSERT INTO heads VALUES(?,?,?,?)", (context_id, segment_id, last["commit"]["seq"],
                                                            last["digest"]))
            c.execute("COMMIT")
        except BaseException:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise

    def load_bundle(self, context_id: str, as_of_seq: int | None = None, *, segment_id: str | None = None,
                    mode: str = "recorded") -> dict:
        """As-of read (spec 11.5): one short read transaction for the head, the commits with seq <= N and their small
        objects; blobs are then re-checked against their refs outside it. Never writes and never moves the head."""
        c = self.conn
        c.execute("BEGIN")
        try:
            head = self.head(context_id)
            if head is None:
                raise KeyError(f"no context {context_id}")
            seg = segment_id or head["segment_id"]
            top = c.execute("SELECT MAX(seq) FROM commits WHERE context_id=? AND segment_id=?",
                            (context_id, seg)).fetchone()[0]
            n = top if as_of_seq is None else as_of_seq
            if n is None or n < 1 or n > top:
                raise KeyError(f"seq {as_of_seq} is not on segment {seg}")
            rows = c.execute("SELECT digest, header FROM commits WHERE context_id=? AND segment_id=? AND seq<=? "
                             "ORDER BY seq", (context_id, seg, n)).fetchall()
            commits = []
            for digest, header in rows:
                objs = [H.ingest_json(r[0], max_depth=128) for r in c.execute(
                    "SELECT o.bytes FROM commit_objects co JOIN objects o ON o.context_id=? AND o.segment_id=? AND "
                    "o.kind=co.kind AND o.logical_id=co.logical_id WHERE co.commit_digest=? ORDER BY co.position",
                    (context_id, seg, digest))]
                commits.append({"commit": H.ingest_json(header), "digest": digest, "objects": objs})
        finally:
            c.execute("COMMIT")
        checks = {d: self.blob_status(d) for x in commits for o in x["objects"] for d in _raw_refs(o)}
        return {"context_id": context_id, "segment_id": seg, "mode": mode, "commits": commits, "as_of_seq": n,
                "as_of_commit_digest": commits[-1]["digest"], "blob_checks": dict(sorted(checks.items()))}
