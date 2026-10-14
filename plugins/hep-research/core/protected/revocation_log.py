"""Hash-chained revocation log and head: writers and the verifier (task P2), standard library only so that the
protected-use guard in core can verify the log; contracts.revocation is the public interface (schemas, reverse index,
command line) and re-exports these names.

The record checks below are the rules of contracts/schemas/revocation_event.json and revocation_head.json written out;
tests/contracts/test_revocation.py checks that both agree on every fixture. See contracts/revocation.py for the format.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
from dataclasses import dataclass, field

from core.protected.trusted_input import Account, read_protected, read_unchecked

LOG_FORMAT = "hep-research-revocation-log/1"
HEAD_VERSION = "1.0.0"
ZERO = "0" * 64
MAX_STATUS_AGE_S = 86400  # the stalest head any caller may accept (as contracts.attestation)
SUBJECT_KINDS = ("artifact", "release", "recipe", "source", "attestation", "qualification")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def parse_ts(text) -> datetime.datetime | None:
    try:
        t = datetime.datetime.strptime(str(text), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return t.replace(tzinfo=datetime.UTC)


def now_text() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def encode(rec: dict) -> bytes:
    """One log line: canonical JSON and a newline."""
    return json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"


def no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key")
    return dict(pairs)


def _text(v) -> bool:
    return isinstance(v, str) and bool(v)


def _int(v, low: int) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= low


def genesis_problem(rec) -> str | None:
    if not isinstance(rec, dict) or set(rec) != {"seq", "prev_sha256", "genesis"}:
        return "not a genesis record {seq, prev_sha256, genesis}"
    g = rec["genesis"]
    if rec["seq"] != 0 or isinstance(rec["seq"], bool) or rec["prev_sha256"] != ZERO:
        return "genesis needs seq 0 and prev_sha256 all zeros"
    if not isinstance(g, dict) or set(g) != {"log_format", "log_id", "created", "actor"} or g["log_format"] != LOG_FORMAT \
            or not _text(g["log_id"]) or not _text(g["actor"]) or not (isinstance(g["created"], str) and TIMESTAMP.match(g["created"])):
        return f"genesis needs {{log_format: {LOG_FORMAT}, log_id, created, actor}}"
    return None


def event_problem(rec) -> str | None:
    if not isinstance(rec, dict) or set(rec) != {"seq", "prev_sha256", "subject", "reason", "time", "actor"}:
        return "not an event {seq, prev_sha256, subject, reason, time, actor}"
    s = rec["subject"]
    if not _int(rec["seq"], 1) or not (isinstance(rec["prev_sha256"], str) and HEX64.match(rec["prev_sha256"])):
        return "seq is an integer >= 1 and prev_sha256 64 lower-case hex"
    if not _text(rec["reason"]) or not _text(rec["actor"]) or not (isinstance(rec["time"], str) and TIMESTAMP.match(rec["time"])):
        return "reason and actor are non-empty, time is YYYY-MM-DDTHH:MM:SSZ"
    if not isinstance(s, dict) or s.get("kind") not in SUBJECT_KINDS or not set(s) <= {"kind", "ref", "sha256"} \
            or not ("ref" in s or "sha256" in s):
        return f"subject is {{kind: one of {list(SUBJECT_KINDS)}, ref and/or sha256}}"
    if ("ref" in s and not _text(s["ref"])) or ("sha256" in s and not (isinstance(s["sha256"], str) and HEX64.match(s["sha256"]))):
        return "subject ref is non-empty, sha256 64 lower-case hex"
    return None


def head_problem(head) -> str | None:
    if not isinstance(head, dict) or set(head) != {"head_version", "log_id", "count", "last_sha256", "as_of", "source"}:
        return "not a head {head_version, log_id, count, last_sha256, as_of, source}"
    if head["head_version"] != HEAD_VERSION or not _text(head["log_id"]) or not _int(head["count"], 1) \
            or not (isinstance(head["last_sha256"], str) and HEX64.match(head["last_sha256"])) \
            or not (isinstance(head["as_of"], str) and TIMESTAMP.match(head["as_of"])) or not _text(head["source"]):
        return "head fields have the wrong type or format"
    return None


# --- custodian-side writers (pure: they return records; the custodian writes them) ---------------------------------

def genesis(log_id: str, actor: str, created: str | None = None) -> dict:
    rec = {"seq": 0, "prev_sha256": ZERO,
           "genesis": {"log_format": LOG_FORMAT, "log_id": log_id, "created": created or now_text(), "actor": actor}}
    problem = genesis_problem(rec)
    if problem:
        raise ValueError(problem)
    return rec


def next_event(records: list[dict], subject: dict, reason: str, actor: str, time: str | None = None) -> dict:
    ev = {"seq": len(records), "prev_sha256": canonical_sha256(records[-1]), "subject": subject, "reason": reason,
          "time": time or now_text(), "actor": actor}
    problem = event_problem(ev)
    if problem:
        raise ValueError(problem)
    return ev


def head_of(records: list[dict], source: str, as_of: str | None = None) -> dict:
    return {"head_version": HEAD_VERSION, "log_id": records[0]["genesis"]["log_id"], "count": len(records),
            "last_sha256": canonical_sha256(records[-1]), "as_of": as_of or now_text(), "source": source}


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
    except (UnicodeDecodeError, ValueError, RecursionError):
        return False
    return isinstance(rec, dict) and isinstance(rec.get("genesis"), dict)


def verify(log_bytes: bytes | None, head, *, source: str, now: datetime.datetime | None = None,
           max_age_s: int = MAX_STATUS_AGE_S) -> RevocationStatus:
    """Verify a log against its head (both already read). See contracts/revocation.py. Never raises on malformed input."""
    try:
        return _verify(log_bytes, head, source=source, now=now, max_age_s=max_age_s)
    except (ValueError, UnicodeError, RecursionError, TypeError, KeyError) as exc:
        return RevocationStatus(ok=False, findings=[{"severity": "error", "path": "$log", "code": "revocation.bad_record",
                                                     "message": f"malformed record: {type(exc).__name__}"}])


def _verify(log_bytes: bytes | None, head, *, source: str, now: datetime.datetime | None = None,
            max_age_s: int = MAX_STATUS_AGE_S) -> RevocationStatus:
    now = now or datetime.datetime.now(datetime.UTC)
    findings: list[dict] = []

    def add(path: str, code: str, message: str) -> None:
        findings.append({"severity": "error", "path": path, "code": code, "message": message})

    records: list[dict] = []
    if not (isinstance(max_age_s, int) and not isinstance(max_age_s, bool) and 0 < max_age_s <= MAX_STATUS_AGE_S):
        add("$max_age", "revocation.age_too_long", f"the allowed status age must be 1..{MAX_STATUS_AGE_S} s")
    if not (isinstance(source, str) and source):
        add("$source", "revocation.source_unchecked", "no expected status source: the head cannot be bound")
    if log_bytes is None:
        add("$log", "revocation.log_unreadable", "no revocation log")
    elif not log_bytes.strip():
        add("$log", "revocation.empty", "the log is empty: an empty file is not 'nothing revoked'")
    else:
        terminated = log_bytes.endswith(b"\n")
        if not terminated:
            add("$log", "revocation.truncated_line", "the last record is not terminated: the log was cut")
        lines = log_bytes.split(b"\n")
        for n, line in enumerate(lines[:-1] if terminated else lines, 1):
            where = f"$log:{n}"
            try:
                rec = json.loads(line.decode("utf-8"), object_pairs_hook=no_duplicates)
            except (UnicodeDecodeError, ValueError, RecursionError):
                add(where, "revocation.bad_record", "not one JSON object per line")
                break
            problem = genesis_problem(rec) if n == 1 else event_problem(rec)
            if problem:
                add(where, "revocation.bad_genesis" if n == 1 else "revocation.bad_record", problem)
                break
            if n > 1:
                if rec["seq"] != n - 1:
                    add(where, "revocation.seq_gap", f"seq {rec['seq']} where {n - 1} was expected")
                    break
                if rec["prev_sha256"] != canonical_sha256(records[-1]):
                    add(where, "revocation.chain_broken", "does not bind the record before it")
                    break
                if n > 2 and rec["time"] < records[-1]["time"]:
                    add(where, "revocation.time_order", "dated before the record before it")
                    break
            records.append(rec)
    if head_problem(head):
        add("$head", "revocation.head_malformed", "no valid head: the log's completeness is unknown")
        head = None
    if head is not None and not findings:
        as_of = parse_ts(head["as_of"])
        if head["source"] != source:
            add("$head.source", "revocation.other_source", "the head is not from the expected status source")
        if as_of is None or as_of > now or (now - as_of).total_seconds() > max_age_s:
            add("$head.as_of", "revocation.stale", f"the head is older than {max_age_s} s or dated in the future")
        if head["log_id"] != records[0]["genesis"]["log_id"]:
            add("$head.log_id", "revocation.head_other_log", "the head belongs to another log")
        elif head["count"] > len(records):
            add("$head.count", "revocation.truncated", "the log holds fewer records than the head counts")
        elif head["count"] < len(records) or head["last_sha256"] != canonical_sha256(records[-1]):
            add("$head", "revocation.head_mismatch", "the head does not describe this log")
        elif len(records) > 1 and records[-1]["time"] > head["as_of"]:
            add("$head.as_of", "revocation.event_after_head", "an event is dated after the head")
    if findings or head is None:
        return RevocationStatus(ok=False, findings=findings)
    assert log_bytes is not None
    return RevocationStatus(ok=True, findings=[], log_id=records[0]["genesis"]["log_id"], count=len(records),
                            as_of=head["as_of"], source=head["source"], events=records[1:],
                            log_sha256=hashlib.sha256(log_bytes).hexdigest(), head_sha256=canonical_sha256(head))


def _read(path, protected: bool, account: Account | None, where: str, out: list) -> bytes | None:
    chk = read_protected(path, account) if protected else read_unchecked(path)
    for code, msg in chk.refusals:
        out.append({"severity": "error", "path": where, "code": code, "message": msg})
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
            head = json.loads(head_bytes.decode("utf-8"), object_pairs_hook=no_duplicates)
        except (UnicodeDecodeError, ValueError, RecursionError):
            head = None
    return verify(log_bytes, head, source=source, now=now, max_age_s=max_age_s)
