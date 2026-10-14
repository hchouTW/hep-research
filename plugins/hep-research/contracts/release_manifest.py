#!/usr/bin/env python3
"""Data release manifest checker (AGENTIC-R5 T1.2, plan basis §7.3): schema plus the semantic checks a schema cannot
express. It is meant to run on the custodian side, from a protected copy of every input; run by an agent it is
advisory only, and passing it never releases data (the trusted release gate does, T1.8).

Usage: python3 contracts/release_manifest.py MANIFEST --root DIR --approval FILE --approvers FILE --ledger FILE
           --revocations FILE --effective FILE [--now YYYY-MM-DDTHH:MM:SSZ]
           [--code-digest HEX] [--destination-sets FILE] [--analysis NAME [--exposure-record FILE]] [--sealed FILE]
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
  --revocation-log, --revocation-head  instead of --revocations: the hash-chained revocation log and its head
               (contracts/revocation.py), verified against validity.status_source and validity.max_status_age_s; its
               release events are the status (a log that does not verify: release.status_unverified)
  --effective  the effective destinations of the session: {"services": [{"service", "tenant", "region",
               "model_family", "model"}], "tools", "network", "recipients", "logging": {"transcripts", "telemetry"}};
               every key must be present (an absent list is not "none used") and every entry allowed by the manifest
Always checked, from the manifest alone: no transform parameter name may look like key material (KEY_LIKE: key,
secret, offset, scale, seed, password, token; the schema already requires transform.keys_recorded to be false), and no
destination may contain a wildcard '*'.

Custodian options (each one adds checks; none is needed for a pass, and a custodian should give all of them):
  --code-digest       the code-release digest of the transform code the custodian runs (64 hex); transform.code_sha256
                      must equal it
  --destination-sets  {name: destinations}: the destination sets the custodian holds (one per qualified
                      configuration); the manifest's destinations must equal one of them exactly
  --analysis          the analysis this release belongs to: every ledger entry of the same analysis or of the same
                      source (ledger entries may carry "analysis" and "source_sha256") must be listed in
                      related_releases, and every listed release must be in the ledger (a revoked one is a warning: the
                      composition review must cover it)
  --exposure-record   with --analysis: the analysis's exposure record (contracts/schemas/exposure_record.json) for this
                      release's source; it must be valid and for this analysis and source, and every release it records
                      (other than this one) must be in related_releases and in the ledger, so earlier releases are known
                      from both the ledger and the record
  --sealed            the sealed file of this release (audit_blinded_outputs.py seal: {"sealed": [...], "rtol"}, or
                      nothing_sealable); needs --root. Every artifact is scanned for a sealed value: a JSON object
                      without its declared structure keys (STRUCTURE_KEYS: bin edges, masks, region), other files as
                      core.blinding.scan_file reads them. An artifact that cannot be scanned fails (fail closed)
Output: JSON {"status": "pass"|"fail", "manifest_sha256", "findings", "note"}. Exit 0 pass, 1 fail, 2 unreadable input.
Rejection details are for the custodian; what an agent sees of a refusal is a fixed status (HC-08). A finding never
names a sealed value or a count of matches.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import re
import stat
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.schema import Report, validate  # noqa: E402

RELEASE_AUTHORITY = "data-release"
KEY_LIKE = re.compile(r"key|secret|offset|scale|seed|password|token", re.IGNORECASE)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_SEALED_RTOL = 1e-6  # as audit_blinded_outputs.py
# top-level keys of a JSON artifact that hold declared structure, not data: bin edges collide with low-digit sealed
# values (a difference of 7 counts against an edge at 7.0); masks are booleans; the region is retained by definition
STRUCTURE_KEYS = frozenset({"edges", "blinded_bins", "region", "blinding", "flow", "status"})
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
    elif not all(isinstance(v, list) and all(isinstance(a, str) for a in v) for v in approvers.values()):
        rep.add("error", "approvers", "release.approvers_malformed", "each approver maps to a list of authority strings")
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
    elif not all(isinstance(r, dict) and isinstance(r.get("ref"), str) for r in revoked):
        rep.add("error", "revocations.revoked", "release.status_unknown", "an entry is not {'ref': ..., ...}: status unreadable")
    elif any(isinstance(r, dict) and r.get("ref") in (v["revocation_ref"], m["release_id"]) for r in revoked):
        rep.add("error", "revocations", "release.revoked", "this release is revoked")


def check_ledger(m: dict, ledger, rep: Report) -> None:
    if not isinstance(ledger, list):
        rep.add("error", "ledger", "release.ledger_missing", "no release ledger: release_id reuse cannot be excluded")
        return
    digest = manifest_digest(m)
    if not all(isinstance(e, dict) and isinstance(e.get("release_id"), str) and isinstance(e.get("manifest_sha256"), str)
               for e in ledger):
        rep.add("error", "ledger", "release.ledger_malformed", "an entry is not {'release_id', 'manifest_sha256'}: reuse cannot be excluded")
        return
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


def check_keys(m: dict, rep: Report) -> None:
    """Key material never travels with a release: no parameter name may look like a key (keys_recorded is false by the
    schema)."""
    tr = m["transform"]

    def walk(obj, path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if KEY_LIKE.search(str(k)):
                    rep.add("error", f"{path}.{k}", "release.keys_present", "a transform parameter name looks like key material")
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")
    walk(tr["parameters"], "transform.parameters")


def check_wildcards(m: dict, rep: Report) -> None:
    if "*" in json.dumps(m["destinations"], ensure_ascii=False):
        rep.add("error", "destinations", "release.destination_wildcard", "a destination contains a wildcard")


def check_code_digest(m: dict, code_digest, rep: Report) -> None:
    if not (isinstance(code_digest, str) and HEX64.match(code_digest)):
        rep.add("error", "code_digest", "release.code_digest_malformed", "the expected code digest is not 64 lower-case hex")
    elif m["transform"]["code_sha256"] != code_digest:
        rep.add("error", "transform.code_sha256", "release.transform_code_mismatch",
                "the transform code is not the code release the custodian runs")


def check_destination_sets(m: dict, sets, rep: Report) -> None:
    if not (isinstance(sets, dict) and sets and all(isinstance(v, dict) for v in sets.values())):
        rep.add("error", "destination_sets", "release.destination_sets_malformed", "expected {name: destinations}, not empty")
    elif m["destinations"] not in sets.values():
        rep.add("error", "destinations", "release.destination_set_unknown",
                "the destinations are not exactly one destination set the custodian holds")


def check_history(m: dict, ledger, analysis, revocations, rep: Report) -> None:
    """related_releases must name every earlier release of this analysis or source, and only releases the ledger knows."""
    if not (isinstance(analysis, str) and analysis.strip()):
        rep.add("error", "analysis", "release.analysis_malformed", "the analysis name is empty")
        return
    if not isinstance(ledger, list) or not all(isinstance(e, dict) and isinstance(e.get("release_id"), str) for e in ledger):
        rep.add("error", "ledger", "release.history_unchecked", "no readable ledger: the release history cannot be checked")
        return
    src = m["source"]["sha256"]
    known = {e["release_id"] for e in ledger if e["release_id"] != m["release_id"]}
    expected = {e["release_id"] for e in ledger if e["release_id"] != m["release_id"]
                and (e.get("analysis") == analysis or e.get("source_sha256") == src)}
    listed = set(m["related_releases"])
    if expected - listed:
        rep.add("error", "related_releases", "release.related_incomplete",
                f"earlier releases of this analysis or source not listed: {sorted(expected - listed)}")
    if listed - known:
        rep.add("error", "related_releases", "release.related_unknown",
                f"related releases the ledger does not know: {sorted(listed - known)}")
    revoked = {r.get("ref") for r in (revocations or {}).get("revoked") or [] if isinstance(r, dict)}
    for rid in sorted(listed & revoked):
        rep.add("warning", "related_releases", "release.related_revoked",
                f"related release {rid} is revoked; the composition review must cover it")


def check_exposure_history(m: dict, ledger, analysis, record, rep: Report) -> None:
    """Earlier releases known from the exposure record must be listed and known to the ledger as well."""
    from contracts.lineage import check_exposure
    if not (isinstance(analysis, str) and analysis.strip()):
        rep.add("error", "exposure_record", "release.exposure_without_analysis", "an exposure record needs --analysis")
        return
    if not isinstance(record, dict) or not check_exposure(record).ok:
        rep.add("error", "exposure_record", "release.exposure_invalid", "the exposure record is not a valid exposure record")
        return
    if record["analysis"] != analysis or record["source"] != m["source"]:
        rep.add("error", "exposure_record", "release.exposure_other_record", "the record is for another analysis or source")
        return
    seen = {e["release_id"] for e in record["entries"]} - {m["release_id"]}
    missing = seen - set(m["related_releases"])
    if missing:
        rep.add("error", "related_releases", "release.related_incomplete",
                f"releases in the exposure record not listed: {sorted(missing)}")
    known = {e.get("release_id") for e in ledger if isinstance(e, dict)} if isinstance(ledger, list) else set()
    if seen - known:
        rep.add("error", "exposure_record", "release.exposure_release_unknown",
                f"releases in the exposure record the ledger does not know: {sorted(seen - known)}")


def load_sealed(doc) -> tuple[list[float], float]:
    """The sealed numbers and tolerance of a sealed file (audit_blinded_outputs.py seal); ValueError when malformed,
    since a malformed sealed file would make every scan pass. An empty list only with nothing_sealable."""
    nums = doc.get("sealed") if isinstance(doc, dict) else None
    if isinstance(nums, list) and not nums and doc.get("nothing_sealable") is True:
        pass
    elif not isinstance(nums, list) or not nums or not all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in nums):
        raise ValueError("the sealed file must hold a non-empty list of finite numbers under 'sealed'")
    rtol = doc.get("rtol", 1e-9)
    if isinstance(rtol, bool) or not isinstance(rtol, (int, float)) or not 0 < rtol <= MAX_SEALED_RTOL:
        raise ValueError(f"the sealed file's rtol must be in (0, {MAX_SEALED_RTOL:g}]")
    return [float(x) for x in nums], float(rtol)


def check_sealed(m: dict, root: Path | None, sealed_doc, rep: Report) -> None:
    """Scan every artifact for a sealed value. The messages name the artifact only: no value, token or count."""
    from core.blinding.blinding import scan_file, scan_text
    try:
        sealed, rtol = load_sealed(sealed_doc)
    except ValueError as exc:
        rep.add("error", "sealed", "release.sealed_malformed", str(exc))
        return
    if root is None:
        rep.add("error", "sealed", "release.scan_incomplete", "no release directory given: the artifacts cannot be scanned")
        return
    for a in m["artifacts"]:
        p = root / a["path"]
        where = f"artifacts[{a['path']}]"
        try:
            if os.path.islink(p) or not p.is_file():
                raise ValueError("not a regular file")
            if p.suffix.lower() == ".json":
                doc = json.loads(p.read_text(encoding="utf-8"))
                data = {k: v for k, v in doc.items() if k not in STRUCTURE_KEYS} if isinstance(doc, dict) else doc
                hits = scan_text(json.dumps(data, indent=1), sealed, rtol)
            else:
                hits = scan_file(p, sealed, rtol)
                if hits and hits[0].get("unscanned"):
                    raise ValueError(hits[0]["reason"])
        except (OSError, ValueError) as exc:
            rep.add("error", where, "release.scan_incomplete", f"cannot be scanned (fail closed): {type(exc).__name__}")
            continue
        if hits:
            rep.add("error", where, "release.sealed_value_present", "contains a sealed value")


def status_from_log(revocations, kinds: tuple, rep: Report, where: str, code: str):
    """A contracts.revocation.RevocationStatus as the {as_of, source, revoked} document of the given subject kinds, or
    None (with an error) when it did not verify; any other value is returned unchanged."""
    if revocations is None or isinstance(revocations, dict) or not hasattr(revocations, "status_doc"):
        return revocations
    if not revocations.ok:
        rep.add("error", where, code, "the revocation log did not verify: "
                + ", ".join(sorted({f["code"] for f in revocations.findings})))
        return None
    return revocations.status_doc(kinds)


def check(manifest, root=None, approval=None, approvers=None, ledger=None, revocations=None, effective=None,
          now: datetime.datetime | None = None, *, code_digest=None, destination_sets=None, analysis=None,
          sealed=None, exposure_record=None) -> dict:
    """The keyword-only arguments are the custodian options of the command line (module docstring); None skips them.
    `revocations` is the status document or a verified contracts.revocation.RevocationStatus."""
    now = now or datetime.datetime.now(datetime.UTC)
    rep = validate(manifest, "release_manifest.json")
    revocations = status_from_log(revocations, ("release",), rep, "revocations", "release.status_unverified")
    if rep.ok:
        check_keys(manifest, rep)
        check_wildcards(manifest, rep)
        if code_digest is not None:
            check_code_digest(manifest, code_digest, rep)
        if destination_sets is not None:
            check_destination_sets(manifest, destination_sets, rep)
        if analysis is not None:
            check_history(manifest, ledger, analysis, revocations, rep)
        if exposure_record is not None:
            check_exposure_history(manifest, ledger, analysis, exposure_record, rep)
        if sealed is not None:
            check_sealed(manifest, None if root is None else Path(root), sealed, rep)
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


def log_status(manifest, log, head, now):
    """Load the revocation log against the manifest's own status source and age (malformed manifest: no source)."""
    from contracts.revocation import MAX_STATUS_AGE_S, load
    v = manifest.get("validity") if isinstance(manifest, dict) else None
    v = v if isinstance(v, dict) else {}
    age = v.get("max_status_age_s")
    age = min(age, MAX_STATUS_AGE_S) if isinstance(age, int) and not isinstance(age, bool) and age > 0 else MAX_STATUS_AGE_S
    source = v.get("status_source") if isinstance(v.get("status_source"), str) else ""
    return load(log, head, source=source, now=now, max_age_s=age)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("manifest", type=Path)
    for name in ("approval", "approvers", "ledger", "revocations", "effective"):
        ap.add_argument(f"--{name}", type=Path)
    ap.add_argument("--root", type=Path)
    ap.add_argument("--now")
    ap.add_argument("--code-digest", dest="code_digest")
    ap.add_argument("--destination-sets", dest="destination_sets", type=Path)
    ap.add_argument("--analysis")
    ap.add_argument("--sealed", type=Path)
    ap.add_argument("--exposure-record", dest="exposure_record", type=Path)
    ap.add_argument("--revocation-log", dest="revocation_log", type=Path)
    ap.add_argument("--revocation-head", dest="revocation_head", type=Path)
    args = ap.parse_args(argv)
    if args.revocation_log is not None and args.revocations is not None:
        print(json.dumps({"status": "unreadable", "error": "give --revocations or --revocation-log, not both"}))
        return 2
    try:
        docs = {name: None if getattr(args, name) is None else json.loads(getattr(args, name).read_text(encoding="utf-8"))
                for name in ("manifest", "approval", "approvers", "ledger", "revocations", "effective",
                             "destination_sets", "sealed", "exposure_record")}
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
    revocations = docs["revocations"]
    if args.revocation_log is not None:
        revocations = log_status(docs["manifest"], args.revocation_log, args.revocation_head, now)
    try:
        out = check(docs["manifest"], args.root, docs["approval"], docs["approvers"], docs["ledger"], revocations,
                    docs["effective"], now, code_digest=args.code_digest, destination_sets=docs["destination_sets"],
                    analysis=args.analysis, sealed=docs["sealed"], exposure_record=docs["exposure_record"])
    except (AttributeError, KeyError, TypeError, ValueError) as exc:  # an input of the wrong shape: never a pass
        print(json.dumps({"status": "unreadable", "error": f"malformed input: {type(exc).__name__}: {exc}"}))
        return 2
    print(json.dumps(out, indent=1))
    return 0 if out["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
