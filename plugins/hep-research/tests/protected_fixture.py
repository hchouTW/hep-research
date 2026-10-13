"""A synthetic protected project for tests of protected-use mode (task P1). Synthetic values only.

ProtectedProject(tmp) writes:
  <tmp>/project/hep-research.project.json   agent_policy anchored to the authoritative copy, with protected_inputs
  <tmp>/custodian/policy.json               the authoritative copy (agent_policy without authoritative_copy)
  <tmp>/custodian/revocations.jsonl, head.json, qualification.json
start() patches the running account (files are evaluated for another account, so they read as custodian-written; a
test cannot create files owned by another identity without privileges) and the running plugin's identity (the
qualified one). Corruption helpers produce each failure the bypass suite needs.
"""
from __future__ import annotations

import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path
from unittest import mock

from core.protected import revocation_log as rl
from core.protected.trusted_input import Account

SOURCE = "custodian:synthetic-revocations"
PLUGIN = {"release": "0.0.0", "digest": "d" * 64}


def ts(delta_s: int = 0) -> str:
    return (datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=delta_s)).strftime("%Y-%m-%dT%H:%M:%SZ")


class ProtectedProject:
    def __init__(self, tmp, policy_extra: dict | None = None):
        self.tmp = Path(tmp)
        self.project = self.tmp / "project"
        self.cust = self.tmp / "custodian"
        self.project.mkdir(parents=True, exist_ok=True)
        self.cust.mkdir(parents=True, exist_ok=True)
        self.log, self.head = self.cust / "revocations.jsonl", self.cust / "head.json"
        self.qual, self.policy_file = self.cust / "qualification.json", self.cust / "policy.json"
        self.policy = {"policy_version": "1.0.0", "model_context_allowed": ["public", "synthetic"],
                       "unblinding": "outside-agent-session",
                       "protected_inputs": {"revocation_log": str(self.log), "revocation_head": str(self.head),
                                            "status_source": SOURCE, "max_status_age_s": 3600,
                                            "qualification_record": str(self.qual)}}
        self.policy.update(policy_extra or {})
        self.records = [rl.genesis("synthetic-log", "custodian", ts(-7200))]
        self._patches: list = []
        self.write_all()

    # --- writing -----------------------------------------------------------------------------------------------------
    def _write(self, path: Path, data: bytes) -> None:
        if path.exists():
            os.chmod(path, 0o644)
            path.unlink()
        path.write_bytes(data)
        os.chmod(path, 0o644)

    def write_all(self) -> None:
        body = json.dumps(self.policy, sort_keys=True).encode()
        self._write(self.policy_file, body)
        cfg = {"schema_version": "1.2.0", "plugin_version": ">=0.1",
               "blinding": {"blinded": [], "allowed_outputs": [], "regions": []},
               "agent_policy": dict(self.policy, authoritative_copy={"location": str(self.policy_file),
                                                                     "sha256": hashlib.sha256(body).hexdigest()})}
        (self.project / "hep-research.project.json").write_text(json.dumps(cfg, indent=1))
        self.write_log()
        self.write_qualification()

    def write_log(self, as_of: str | None = None) -> None:
        self._write(self.log, b"".join(rl.encode(r) for r in self.records))
        self._write(self.head, json.dumps(rl.head_of(self.records, SOURCE, as_of or ts(-60))).encode())

    def write_qualification(self, **over) -> None:
        q = {"record_version": "1.0.0", "qualification_id": "qual-synthetic-1", "stage": "S1",
             "host": {"surface": "synthetic-host", "effective_digest": "e" * 64}, "plugin": dict(PLUGIN),
             "policy_sha256": rl.canonical_sha256(self.policy), "valid_from": ts(-86400), "valid_until": ts(86400),
             "issued_by": "synthetic custodian"}
        q.update(over)
        self._write(self.qual, json.dumps(q).encode())

    def anchored(self, cfg: dict) -> dict:
        """cfg with its agent_policy made the authoritative policy: protected_inputs added, the authoritative copy and a
        qualification bound to it written, authoritative_copy set. A config without agent_policy is returned as is."""
        if "agent_policy" not in cfg:
            return cfg
        cfg = json.loads(json.dumps(cfg))
        self.policy = dict(cfg["agent_policy"], protected_inputs=self.policy["protected_inputs"])
        body = json.dumps(self.policy, sort_keys=True).encode()
        self._write(self.policy_file, body)
        self.write_qualification()
        cfg["agent_policy"] = dict(self.policy, authoritative_copy={"location": str(self.policy_file),
                                                                    "sha256": hashlib.sha256(body).hexdigest()})
        return cfg

    def revoke(self, kind: str, ref: str | None = None, sha256: str | None = None) -> None:
        subject = {"kind": kind, **({"ref": ref} if ref else {}), **({"sha256": sha256} if sha256 else {})}
        self.records.append(rl.next_event(self.records, subject, "synthetic revocation", "custodian", ts(-120)))
        self.write_log()

    def artifact(self, rel: str, doc: dict) -> Path:
        p = self.project / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, indent=1))
        return p

    # --- failures for the bypass suite -------------------------------------------------------------------------------
    def fail(self, mode: str) -> None:
        if mode == "missing":
            os.chmod(self.log, 0o644)
            self.log.unlink()
        elif mode == "empty":
            self._write(self.log, b"")
        elif mode == "truncated":
            self.revoke("artifact", sha256="f" * 64)
            self._write(self.log, b"".join(rl.encode(r) for r in self.records[:-1]))
        elif mode == "replaced":
            other = [rl.genesis("another-log", "custodian", ts(-7200))]
            self._write(self.log, b"".join(rl.encode(r) for r in other))
        elif mode == "stale":
            self.write_log(as_of=ts(-7200))
        elif mode == "writable":
            os.chmod(self.log, 0o666)
        elif mode == "no-qualification":
            os.chmod(self.qual, 0o644)
            self.qual.unlink()
        elif mode == "expired-qualification":
            self.write_qualification(valid_until=ts(-60))
        else:
            raise ValueError(mode)

    # --- patches -----------------------------------------------------------------------------------------------------
    def start(self) -> ProtectedProject:
        fake = Account(os.geteuid() + 4242, frozenset())
        self._patches = [mock.patch.object(Account, "current", classmethod(lambda cls: fake)),
                         mock.patch("core.protected.guard.plugin_identity", lambda: dict(PLUGIN))]
        for p in self._patches:
            p.start()
        return self

    def stop(self) -> None:
        for p in reversed(self._patches):
            p.stop()
        self._patches = []

    @contextlib.contextmanager
    def inside(self):
        """The working directory inside the project (for entry points that are given no path)."""
        old = os.getcwd()
        os.chdir(self.project)
        try:
            yield self.project
        finally:
            os.chdir(old)

    def cleanup_modes(self) -> None:
        for p in (self.log, self.head, self.qual, self.policy_file):
            if p.exists():
                os.chmod(p, 0o644)
