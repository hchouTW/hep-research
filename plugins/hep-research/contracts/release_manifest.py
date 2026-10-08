#!/usr/bin/env python3
"""Data release manifest checker (AGENTIC-R5 T1.2, plan basis §7.3): schema plus the semantic checks a schema cannot
express. It is meant to run on the custodian side, from a protected copy of every input; run by an agent it is
advisory only, and passing it never releases data (the trusted release gate does, T1.8).

Usage: python3 contracts/release_manifest.py MANIFEST --root DIR --approval FILE --approvers FILE --ledger FILE
           --revocations FILE --effective FILE [--now YYYY-MM-DDTHH:MM:SSZ]
Every input is required for a pass: a check that cannot run is a failure (fail closed), never a skip.

  manifest     the release manifest (contracts/schemas/release_manifest.json)
  --root       the release directory: exactly the listed artifacts, regular files with the listed size and SHA-256
  --approval   the protected approval record: {"approval_id", "manifest_sha256", "approver", "authority", "purposes",
               "destinations_sha256", "valid_from", "valid_until"}. It must bind this manifest's digest (canonical JSON
               without approval_ref), cover its purposes, its destinations (digest) and its validity period
  --approvers  {approver: [authorities]}: the approval's authority must be RELEASE_AUTHORITY ('data-release') and
               the approver must hold it. Where the approval record and this list live and who may write them is the
               trust anchor (Q-06); this checker verifies the binding, not the anchor
  --ledger     the custodian's release ledger: [{"release_id", "manifest_sha256"}]; a release_id recorded for other
               content is reuse
  --revocations {"as_of", "source", "revoked": [{"ref", "time", "reason"}]}: from validity.status_source and no older
               than validity.max_status_age_s; the release_id or revocation_ref listed means revoked
  --effective  the effective destinations of the session: {"services": [{"service", "tenant", "region",
               "model_family", "model"}], "tools", "network", "recipients", "logging": {"transcripts", "telemetry"}};
               every key must be present (an absent list is not "none used") and every entry allowed by the manifest
Output: JSON {"status": "pass"|"fail", "manifest_sha256", "findings", "note"}. Exit 0 pass, 1 fail, 2 unreadable input.
Rejection details are for the custodian; what an agent sees of a refusal is a fixed status (HC-08).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.schema import Report, validate  # noqa: E402

RELEASE_AUTHORITY = "data-release"
NOTE = ("advisory unless run by the custodian from protected copies; passing does not release data, and the approval "
        "trust anchor (who may write approval records) is outside this check")


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def manifest_digest(manifest: dict) -> str:
    """What an approval binds: the canonical JSON of the manifest without approval_ref (which names the approval)."""
    return canonical_sha256({k: v for k, v in manifest.items() if k != "approval_ref"})


def _ts(text) -> datetime.datetime | None:
    try:
        t = datetime.datetime.strptime(str(text), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return t.replace(tzinfo=datetime.UTC)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_content(m: dict, root: Path | None, rep: Report) -> None:
    if root is None:
        rep.add("error", "root", "release.content_unchecked", "no release directory given: the bytes are not bound")
        return
    listed = {a["path"]: a for a in m["artifacts"]}
    found = set()
    def unreadable(exc: OSError) -> None:
        rep.add("error", f"root/{exc.filename}", "release.content_unchecked", f"cannot list: {exc.strerror}")

    for parent, dirs, names in os.walk(root, followlinks=False, onerror=unreadable):
        for name in dirs + names:
            p = Path(parent) / name
            rel = p.relative_to(root).as_posix()
            st = os.lstat(p)
            if stat.S_ISLNK(st.st_mode):
                rep.add("error", f"root/{rel}", "release.symlink", "symbolic links are refused in a release")
            elif stat.S_ISREG(st.st_mode):
                found.add(rel)
                if rel not in listed:
                    rep.add("error", f"root/{rel}", "release.unlisted_file", "a file the manifest does not list")
            elif not stat.S_ISDIR(st.st_mode):
                rep.add("error", f"root/{rel}", "release.not_regular", "not a regular file")
    for rel, a in listed.items():
        if rel not in found:
            rep.add("error", f"artifacts[{rel}]", "release.missing_file", "listed but not a regular file in the release")
            continue
        p = root / rel
        if os.lstat(p).st_size != a["size"] or _sha(p) != a["sha256"]:
            rep.add("error", f"artifacts[{rel}]", "release.content_mismatch", "size or SHA-256 differs from the manifest")


def check_approval(m: dict, approval: dict | None, approvers: dict | None, now: datetime.datetime, rep: Report) -> None:
    if approval is None:
        rep.add("error", "approval", "release.approval_missing", "no approval record: a manifest's own hash proves nothing")
        return
    need = ("approval_id", "manifest_sha256", "approver", "authority", "purposes", "destinations_sha256", "valid_from", "valid_until")
    missing = [k for k in need if not approval.get(k)]
    if missing:
        rep.add("error", "approval", "release.approval_incomplete", f"missing {missing}")
        return
    if approval["approval_id"] != m["approval_ref"]:
        rep.add("error", "approval.approval_id", "release.approval_other", "the record is not the one approval_ref names")
    if approval["manifest_sha256"] != manifest_digest(m):
        rep.add("error", "approval.manifest_sha256", "release.approval_unbound", "the approval binds another manifest")
    if not set(m["purposes"]) <= set(approval["purposes"]):
        rep.add("error", "approval.purposes", "release.purpose_unapproved", f"not approved: {sorted(set(m['purposes']) - set(approval['purposes']))}")
    if approval["destinations_sha256"] != canonical_sha256(m["destinations"]):
        rep.add("error", "approval.destinations_sha256", "release.destinations_unapproved", "the approval binds other destinations")
    vf, vu = _ts(approval["valid_from"]), _ts(approval["valid_until"])
    eff, exp = _ts(m["validity"]["effective"]), _ts(m["validity"]["expires"])
    if vf is None or vu is None or eff is None or exp is None:
        rep.add("error", "approval", "release.bad_time", "approval or validity times are not YYYY-MM-DDTHH:MM:SSZ")
    else:
        if not (vf <= eff and exp <= vu):
            rep.add("error", "approval", "release.validity_unapproved", "the manifest's validity period exceeds the approval's")
        if not (vf <= now < vu):
            rep.add("error", "approval", "release.approval_expired", "the approval is not valid now")
    if approval["authority"] != RELEASE_AUTHORITY:
        rep.add("error", "approval.authority", "release.authority_wrong", f"a release needs the {RELEASE_AUTHORITY!r} authority")
    if not isinstance(approvers, dict):
        rep.add("error", "approvers", "release.authority_unchecked", "no approver list: the approver's authority cannot be checked")
    elif RELEASE_AUTHORITY not in (approvers.get(approval["approver"]) or []):
        rep.add("error", "approval.authority", "release.authority_unknown", f"the approver does not hold {RELEASE_AUTHORITY!r}")


def check_validity(m: dict, revocations: dict | None, now: datetime.datetime, rep: Report) -> None:
    v = m["validity"]
    eff, exp = _ts(v["effective"]), _ts(v["expires"])
    if eff is None or exp is None or not (eff <= now < exp):
        rep.add("error", "validity", "release.not_valid_now", "outside the manifest's validity period")
    if revocations is None:
        rep.add("error", "revocations", "release.status_unknown", "no revocation status: validity cannot be established")
        return
    as_of = _ts(revocations.get("as_of"))
    if revocations.get("source") != v["status_source"]:
        rep.add("error", "revocations.source", "release.status_other_source", "not from validity.status_source")
    if as_of is None or as_of > now or (now - as_of).total_seconds() > v["max_status_age_s"]:
        rep.add("error", "revocations.as_of", "release.status_stale", f"older than {v['max_status_age_s']} s or undated")
    revoked = revocations.get("revoked")
    if not isinstance(revoked, list):
        rep.add("error", "revocations.revoked", "release.status_unknown", "the revoked list is missing")
    elif any(isinstance(r, dict) and r.get("ref") in (v["revocation_ref"], m["release_id"]) for r in revoked):
        rep.add("error", "revocations", "release.revoked", "this release is revoked")


def check_ledger(m: dict, ledger, rep: Report) -> None:
    if not isinstance(ledger, list):
        rep.add("error", "ledger", "release.ledger_missing", "no release ledger: release_id reuse cannot be excluded")
        return
    digest = manifest_digest(m)
    for i, e in enumerate(ledger):
        if isinstance(e, dict) and e.get("release_id") == m["release_id"] and e.get("manifest_sha256") != digest:
            rep.add("error", f"ledger[{i}]", "release.id_reused", "this release_id was recorded for other content")


def check_destinations(m: dict, eff: dict | None, rep: Report) -> None:
    if not isinstance(eff, dict):
        rep.add("error", "effective", "release.destinations_unchecked", "no effective configuration to compare")
        return
    allowed = m["destinations"]
    for i, s in enumerate(eff.get("services") or []):
        ok = any(s.get("service") == a["service"] and s.get("tenant") == a["tenant"] and s.get("region") == a["region"]
                 and s.get("model_family") in a["model_families"] and (not a.get("models") or s.get("model") in a["models"])
                 for a in allowed["services"])
        if not ok:
            rep.add("error", f"effective.services[{i}]", "release.destination_mismatch", "a model destination the manifest does not allow")
    if not eff.get("services"):
        rep.add("error", "effective.services", "release.destinations_unchecked", "no model services listed")
    for key in ("tools", "network", "recipients"):
        if not isinstance(eff.get(key), list):
            rep.add("error", f"effective.{key}", "release.destinations_unchecked", "absent: an unlisted kind is not 'none used'")
            continue
        extra = sorted(set(eff[key]) - set(allowed[key]))
        if extra:
            rep.add("error", f"effective.{key}", "release.destination_mismatch", f"not allowed: {extra}")
    if eff.get("logging") != allowed["logging"]:
        rep.add("error", "effective.logging", "release.destination_mismatch", "logging or telemetry differs from the manifest")


def check(manifest, root=None, approval=None, approvers=None, ledger=None, revocations=None, effective=None,
          now: datetime.datetime | None = None) -> dict:
    now = now or datetime.datetime.now(datetime.UTC)
    rep = validate(manifest, "release_manifest.json")
    if rep.ok:
        if manifest["related_releases"] and "composition_review" not in manifest:
            rep.add("error", "composition_review", "release.composition_unreviewed", "related releases need a composition review")
        if len({a["path"] for a in manifest["artifacts"]}) != len(manifest["artifacts"]):
            rep.add("error", "artifacts", "release.duplicate_path", "an artifact path is listed twice")
        check_ledger(manifest, ledger, rep)
        check_content(manifest, None if root is None else Path(root), rep)
        check_approval(manifest, approval, approvers, now, rep)
        check_validity(manifest, revocations, now, rep)
        check_destinations(manifest, effective, rep)
    digest = manifest_digest(manifest) if isinstance(manifest, dict) else None
    return {"status": "pass" if rep.ok else "fail", "manifest_sha256": digest,
            "findings": [f.as_dict() for f in rep.findings], "note": NOTE}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("manifest", type=Path)
    for name in ("approval", "approvers", "ledger", "revocations", "effective"):
        ap.add_argument(f"--{name}", type=Path)
    ap.add_argument("--root", type=Path)
    ap.add_argument("--now")
    args = ap.parse_args(argv)
    try:
        docs = {name: None if getattr(args, name) is None else json.loads(getattr(args, name).read_text(encoding="utf-8"))
                for name in ("manifest", "approval", "approvers", "ledger", "revocations", "effective")}
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    now = _ts(args.now) if args.now else None
    if args.now and now is None:
        print(json.dumps({"status": "unreadable", "error": "--now must be YYYY-MM-DDTHH:MM:SSZ"}))
        return 2
    if args.root is not None and (args.root.is_symlink() or not args.root.is_dir()):
        print(json.dumps({"status": "unreadable", "error": f"{args.root}: not a directory (a link is never followed)"}))
        return 2
    out = check(docs["manifest"], args.root, docs["approval"], docs["approvers"], docs["ledger"], docs["revocations"],
                docs["effective"], now)
    print(json.dumps(out, indent=1))
    return 0 if out["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
