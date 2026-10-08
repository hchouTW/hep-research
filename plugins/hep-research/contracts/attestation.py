#!/usr/bin/env python3
"""Attestations with separate capability, review and lifecycle axes (AGENTIC-R5 T4.5, F11): evaluate each axis of an
attestation (contracts/schemas/attestation.json) on its own. Nothing here combines the axes into one verdict, and no
axis state authorizes a use: the trusted gate (T4.1) reads protected copies and decides (HC-05).

Usage: python3 contracts/attestation.py ATTESTATION [--bundle FILE] [--recipe FILE] [--evidence-root DIR]
           [--revocations FILE] [--required-roles FILE] [--use FILE] [--now YYYY-MM-DDTHH:MM:SSZ]
  --bundle         the frozen bundle document (bundles/<digest>.json): its digest must match its content and the subject
  --recipe         the recipe the scope names: its canonical digest must match scope.recipe.sha256
  --evidence-root  directory the reviews' evidence refs are relative to; each file is hashed (links refused)
  --revocations    {"as_of", "source", "revoked": [{"ref", ...}]} from lifecycle.status_source, no older than
                   max_status_age_s; the attestation_id or revocation_ref listed means revoked
  --required-roles ["role", ...]: every role needs an accepted review bound to this bundle, scope and evidence
  --use            the scope of the intended use: it must equal the reviewed scope except purposes, and name one
                   reviewed purpose ({... scope fields ..., "purposes": ["<one purpose>"]})
  --now            evaluate at another time (tests, replay); the trusted gate uses its own clock

Axis states (each reported separately):
  capability  supported | unsupported (a required capability this reader does not implement)
  review      absent | unbound (no review binds this bundle and scope) | rejected (a bound review rejects or requests
              changes) | bindings-unchecked (no --bundle or no --recipe to compare with the subject) |
              evidence-unverified (no --evidence-root, or evidence differs) | roles-unchecked (no --required-roles) |
              roles-incomplete | out-of-scope (--use exceeds the reviewed scope) | accepted-as-recorded (every check
              above passed; the reviewer's identity and the protected record behind record_ref are not verified here)
  lifecycle   unknown (no, stale, foreign or malformed status) | draft | withdrawn | superseded | not-yet-effective |
              expired | revoked | active
Output: JSON {"attestation_id", "evaluated_at", "clock" ("system", or "given" with --now), "subject_sha256",
"scope_sha256", "axes": {...}, "evaluated", "findings", "note"}. Exit 0 when the
attestation was evaluated (whatever its axis states), 1 when it is malformed or its subject does not match the given
bundle or recipe (then "axes" is null: no state is reported for a mismatched subject), 2 for unreadable input.
lifecycle.max_status_age_s above MAX_STATUS_AGE_S is refused: the attestation does not choose its own freshness.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import stat
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import KNOWN_CAPABILITIES  # noqa: E402
from contracts.release_manifest import _sha, _ts, canonical_sha256  # noqa: E402
from contracts.schema import Report, validate  # noqa: E402
from core.partition.bundle import digest_of  # noqa: E402

NOTE = ("each axis is reported on its own and none authorizes a use; the trusted gate decides from protected copies "
        "(HC-05). Software consistency only, not scientific validity (HC-12)")
PURPOSES = ("exploration", "fixed-execution", "validation", "formal-analysis")
MAX_STATUS_AGE_S = 86400  # the stalest revocation status any attestation may accept


def capability_axis(att: dict, rep: Report) -> dict:
    unknown = [c for c in att["capability"]["required_capabilities"] if c not in KNOWN_CAPABILITIES]
    for c in unknown:
        rep.add("warning", "capability.required_capabilities", "attestation.capability_unsupported",
                f"'{c}' is not implemented by this reader")
    return {"state": "unsupported" if unknown else "supported", "unsupported": unknown}


def _evidence_ok(review: dict, root: Path | None, rep: Report, where: str) -> bool:
    if root is None:
        return False
    ok = True
    for e in review["evidence"]:
        p = root / e["ref"]
        parts = Path(e["ref"]).parts
        try:
            linked = any(os.path.islink(root.joinpath(*parts[:i])) for i in range(1, len(parts)))
            st = os.lstat(p)
            same = not linked and stat.S_ISREG(st.st_mode) and _sha(p) == e["sha256"]
        except OSError:
            same = False
        if not same:
            rep.add("warning", f"{where}.evidence", "attestation.evidence_changed",
                    f"'{e['ref']}' is missing, a link, or differs from the reviewed bytes")
            ok = False
    return ok


def review_axis(att: dict, scope_sha: str, evidence_root: Path | None, roles: list | None, use: dict | None,
                bindings_checked: bool, now: datetime.datetime, rep: Report) -> dict:
    reviews = att["review"]["reviews"]
    if not reviews:
        return {"state": "absent", "bound_reviews": 0}
    bundle = att["subject"]["bundle_sha256"]
    bound = []
    for k, r in enumerate(reviews):
        if r["date"] > now.strftime("%Y-%m-%d"):
            rep.add("warning", f"review.reviews[{k}]", "attestation.review_future", "the review is dated after now: not counted")
        elif r["bundle_sha256"] != bundle or r["scope_sha256"] != scope_sha:
            rep.add("warning", f"review.reviews[{k}]", "attestation.review_unbound",
                    "the review binds another bundle or scope: it does not carry over")
        else:
            bound.append((k, r))
    out = {"bound_reviews": len(bound)}
    if not bound:
        return dict(out, state="unbound")
    if any(r["conclusion"] != "accepted" for _, r in bound):
        return dict(out, state="rejected")
    if not bindings_checked:
        rep.add("warning", "review", "attestation.bindings_unchecked",
                "no --bundle or no --recipe: the subject's digests are not compared with anything")
        return dict(out, state="bindings-unchecked")
    verified = [r for k, r in bound if _evidence_ok(r, evidence_root, rep, f"review.reviews[{k}]")]
    if evidence_root is None:
        rep.add("warning", "review", "attestation.evidence_unchecked", "no evidence root: the reviewed evidence is not re-hashed")
    if not verified or len(verified) != len(bound):
        return dict(out, state="evidence-unverified")
    if roles is None:
        state = "roles-unchecked"
    else:
        missing = sorted(set(roles) - {r["role"] for r in verified})
        by_reviewer: dict[str, set] = {}
        for r in verified:
            by_reviewer.setdefault(r["reviewer"], set()).add(r["role"])
        for held in by_reviewer.values():
            if len(held & set(roles)) > 1:
                rep.add("warning", "review", "attestation.roles_one_reviewer",
                        f"one reviewer fills {sorted(held & set(roles))}; whether that is allowed is a Q-06 policy")
        if missing:
            rep.add("warning", "review", "attestation.roles_incomplete", f"no accepted bound review by {missing}")
        state = "roles-incomplete" if missing else "accepted-as-recorded"
    if use is not None and state in ("accepted-as-recorded", "roles-unchecked"):
        scope = att["subject"]["scope"]
        rest = {k: v for k, v in scope.items() if k != "purposes"}
        use_rest = {k: v for k, v in use.items() if k != "purposes"}
        purposes = use.get("purposes")
        if (use_rest != rest or not isinstance(purposes, list) or len(purposes) != 1
                or purposes[0] not in scope["purposes"]):
            rep.add("warning", "use", "attestation.out_of_scope", "the intended use is not the reviewed scope: it needs a new review")
            state = "out-of-scope"
    return dict(out, state=state)


def lifecycle_axis(att: dict, revocations, now: datetime.datetime, rep: Report) -> dict:
    lc = att["lifecycle"]
    eff, exp = _ts(lc["effective"]), _ts(lc["expires"])
    if eff is None or exp is None or exp <= eff:
        rep.add("error", "lifecycle", "attestation.bad_time", "effective must precede expires")
        return {"state": "unknown"}
    if lc["max_status_age_s"] > MAX_STATUS_AGE_S:
        rep.add("error", "lifecycle.max_status_age_s", "attestation.status_age_too_long",
                f"more than {MAX_STATUS_AGE_S} s: the attestation does not choose its own freshness")
    if (lc["state"] == "superseded") != bool(lc.get("superseded_by")):
        rep.add("error", "lifecycle.superseded_by", "attestation.superseded_inconsistent",
                "superseded_by is given exactly when the state is superseded")
    status_known = False
    revoked = False
    if not isinstance(revocations, dict):
        rep.add("warning", "revocations", "attestation.status_unknown", "no revocation status")
    else:
        as_of = _ts(revocations.get("as_of"))
        listed = revocations.get("revoked")
        if revocations.get("source") != lc["status_source"]:
            rep.add("warning", "revocations.source", "attestation.status_other_source", "not from lifecycle.status_source")
        elif as_of is None or as_of > now or (now - as_of).total_seconds() > lc["max_status_age_s"]:
            rep.add("warning", "revocations.as_of", "attestation.status_stale", f"older than {lc['max_status_age_s']} s or undated")
        elif not isinstance(listed, list) or not all(isinstance(r, dict) and isinstance(r.get("ref"), str) for r in listed):
            rep.add("warning", "revocations.revoked", "attestation.status_unknown", "the revoked list is missing or malformed")
        else:
            status_known = True
            revoked = any(r["ref"] in (lc["revocation_ref"], att["attestation_id"]) for r in listed)
    if revoked:
        return {"state": "revoked"}
    if lc["state"] != "active":
        return {"state": lc["state"]}
    if now < eff:
        return {"state": "not-yet-effective"}
    if now >= exp:
        return {"state": "expired"}
    return {"state": "active" if status_known else "unknown"}


def evaluate(att, bundle=None, recipe=None, evidence_root=None, revocations=None, roles=None, use=None,
             now: datetime.datetime | None = None) -> dict:
    clock = "system" if now is None else "given"
    now = now or datetime.datetime.now(datetime.UTC)
    rep = validate(att, "attestation.json")
    axes = None
    scope_sha = subject_sha = None
    if rep.ok:
        scope_sha = canonical_sha256(att["subject"]["scope"])
        subject_sha = canonical_sha256(att["subject"])
        if bundle is not None:
            if not isinstance(bundle, dict) or digest_of(bundle) != bundle.get("bundle_digest"):
                rep.add("error", "bundle", "attestation.bundle_changed", "the bundle document does not match its own digest")
            elif bundle["bundle_digest"] != att["subject"]["bundle_sha256"]:
                rep.add("error", "bundle", "attestation.bundle_other", "the attestation is about another bundle")
        if recipe is not None and canonical_sha256(recipe) != att["subject"]["scope"]["recipe"]["sha256"]:
            rep.add("error", "recipe", "attestation.recipe_changed", "the recipe differs from the one in the scope")
        if roles is not None and not (isinstance(roles, list) and roles and all(isinstance(r, str) and r for r in roles)):
            rep.add("error", "required_roles", "attestation.roles_malformed", "required roles are a non-empty list of role names")
            roles = None
        if use is not None and not isinstance(use, dict):
            rep.add("error", "use", "attestation.use_malformed", "the intended use is a scope object")
            use = None
        root = None if evidence_root is None else Path(evidence_root)
        if root is not None and (root.is_symlink() or not root.is_dir()):
            rep.add("warning", "evidence_root", "attestation.evidence_root_refused", "not a directory (a link is never followed)")
            root = None
        axes = {"capability": capability_axis(att, rep),
                "review": review_axis(att, scope_sha, root, roles, use, bundle is not None and recipe is not None, now, rep),
                "lifecycle": lifecycle_axis(att, revocations, now, rep)}
        if not rep.ok:
            axes = None  # a mismatched subject or malformed attestation gets no axis state
    att_id = att.get("attestation_id") if isinstance(att, dict) else None
    return {"attestation_id": att_id, "evaluated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "clock": clock,
            "subject_sha256": subject_sha, "scope_sha256": scope_sha, "axes": axes,
            "evaluated": rep.ok, "findings": [f.as_dict() for f in rep.findings], "note": NOTE}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("attestation", type=Path)
    for name in ("bundle", "recipe", "revocations", "required_roles", "use"):
        ap.add_argument(f"--{name.replace('_', '-')}", dest=name, type=Path)
    ap.add_argument("--evidence-root", type=Path)
    ap.add_argument("--now")
    args = ap.parse_args(argv)
    try:
        docs = {n: None if getattr(args, n) is None else json.loads(getattr(args, n).read_text(encoding="utf-8"))
                for n in ("attestation", "bundle", "recipe", "revocations", "required_roles", "use")}
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    now = _ts(args.now) if args.now else None
    if args.now and now is None:
        print(json.dumps({"status": "unreadable", "error": "--now must be YYYY-MM-DDTHH:MM:SSZ"}))
        return 2
    if args.evidence_root is not None and (args.evidence_root.is_symlink() or not args.evidence_root.is_dir()):
        print(json.dumps({"status": "unreadable", "error": f"{args.evidence_root}: not a directory (a link is never followed)"}))
        return 2
    use = docs["use"]
    if args.use is not None and use is None:
        use = "null"  # a --use file holding null is malformed, not "no intended use"
    out = evaluate(docs["attestation"], docs["bundle"], docs["recipe"], args.evidence_root, docs["revocations"],
                   docs["required_roles"], use, now)
    print(json.dumps(out, indent=1))
    return 0 if out["evaluated"] else 1


if __name__ == "__main__":
    sys.exit(main())
