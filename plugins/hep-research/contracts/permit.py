#!/usr/bin/env python3
"""Formal-use and S3-execution permits (task P5.1, C15) and the recipe-use review before formal use (P5.3).

A permit (contracts/schemas/permit.json) is issued by the custodian's gate and read here only as a protected input
(core.protected.trusted_input: a regular file the running account neither owns, nor can write, nor can replace). It
binds the analysis-level bundle (contracts/analysis_bundle.py) and the digests of the artifacts the use may read, one
purpose, an actor, a budget of uses, a validity window and a nonce. verify() refuses, with codes and never values:

  permit.missing / source.*      no permit, or not a protected input
  permit.malformed               not a permit (schema)
  permit.wrong_scope             issued for another scope (s3-execution vs formal-use)
  permit.not_yet_valid / permit.expired
  permit.revoked                 the verified revocation log revokes it (subject kind 'permit', by id or digest)
  permit.ledger_missing          no nonce ledger among the protected inputs, or it is not a protected input
  permit.replayed                the custodian's nonce ledger already records budget.uses uses of its nonce
  permit.wrong_use               another purpose than the entry point's
  permit.bundle_changed          the analysis bundle at analysis_bundle_ref is missing, has another digest, or no longer
                                 verifies against the project (a changed spec, recipe, calibration or plugin release)
  permit.wrong_subject           an input (a file, or a file under an input directory) whose byte or canonical digest
                                 the permit does not list; no input file at all; for s3-execution, another execution
                                 bundle than the one bound
  permit.review_missing          formal-use permit without a review block
  permit.attestation_mismatch    the attestation file differs from the bound digest, or is about another bundle
  permit.review_not_accepted     the review axis is not accepted-as-recorded for the required roles, or the bundle
                                 holds a recipe that is not the attested one
  permit.review_out_of_scope     the use's purpose is not one the review covers (P5.3)
  permit.attestation_inactive    the lifecycle axis is not active (revoked, expired, superseded, unknown, ...)
  permit.attestation_unsupported a capability the attestation requires is not implemented by this reader

The plugin never records a use and never reports a use as allowed: the custodian's gate appends to the nonce ledger
when the use takes place. checker(path) returns the formal_check that core.protected.guard.guard() takes.

Usage: python3 contracts/permit.py verify PERMIT --project DIR [--scope formal-use|s3-execution]
           [--purpose PURPOSE] [INPUT ...]

check-report was the advisory check of a cross-artifact analysis-check report; it was retired with the check
(docs/dev/cross-artifact-check/decision-retire.md) and now refuses with permit.check_report_retired (exit 2).
Exit 0 when nothing is refused, 3 when the permit is refused, 2 bad usage. Output: JSON.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.release_manifest import _ts, canonical_sha256  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.protected.guard import Context, establish  # noqa: E402
from core.protected.trusted_input import Account, read_protected, read_unchecked  # noqa: E402

FORMAL_PURPOSE = "formal-analysis"


def _r(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def input_digests(path) -> set[str]:
    """The byte digest of a file and, for JSON, its canonical digest (either may be listed in a permit)."""
    data = Path(path).read_bytes()  # OSError, or ValueError for an unusable path: the caller refuses
    out = {hashlib.sha256(data).hexdigest()}
    try:
        out.add(canonical_sha256(json.loads(data.decode("utf-8"))))
    except (UnicodeError, ValueError, RecursionError):
        pass
    return out


def _ledger_uses(ctx: Context, nonce: str, account) -> tuple[int | None, list[dict]]:
    inputs = (ctx.policy or {}).get("protected_inputs") or {}
    path = inputs.get("nonce_ledger")
    if not isinstance(path, str) or not path:
        return None, [_r("permit.ledger_missing", "$policy.protected_inputs.nonce_ledger",
                         "formal use needs the custodian's nonce ledger among the protected inputs")]
    chk = read_protected(path, account)
    if not chk.ok:
        return None, [_r("permit.ledger_missing", "$nonce_ledger", m) for _, m in chk.refusals]
    uses = 0
    for n, line in enumerate((chk.data or b"").decode("utf-8", "replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except (ValueError, RecursionError):
            return None, [_r("permit.ledger_missing", f"$nonce_ledger:{n}", "not one JSON object per line")]
        if isinstance(rec, dict) and rec.get("nonce") == nonce:
            uses += 1
    return uses, []


def _review(permit: dict, bundle: dict, root: Path, ctx: Context, purpose: str, now) -> list[dict]:
    """P5.3: the bound attestation must accept the recipe and cover this use."""
    from contracts.attestation import evaluate
    rv = permit.get("review")
    if not isinstance(rv, dict):
        return [_r("permit.review_missing", "$permit.review", "a formal-use permit binds the attestation the gate checked")]
    ref = Path(rv["attestation_ref"])
    chk = read_unchecked(ref if ref.is_absolute() else root / ref)  # bound by its digest: where it is stored does not matter
    att = None
    if chk.ok:
        try:
            att = json.loads((chk.data or b"").decode("utf-8"))
        except (UnicodeError, ValueError, RecursionError):
            att = None
    if not isinstance(att, dict) or canonical_sha256(att) != rv["attestation_sha256"]:
        return [_r("permit.attestation_mismatch", "$permit.review.attestation_ref", "missing or not the bound attestation")]
    scope = (att.get("subject") or {}).get("scope") if isinstance(att.get("subject"), dict) else None
    recipe_sha = ((scope or {}).get("recipe") or {}).get("sha256") if isinstance(scope, dict) else None
    recipe = None
    for it in bundle["items"]:
        if it["role"] == "recipe" and it["sha256"] == recipe_sha:
            try:
                recipe = json.loads((root / it["ref"]).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                recipe = None
    other = sorted(it["ref"] for it in bundle["items"] if it["role"] == "recipe" and it["sha256"] != recipe_sha)
    if other:
        return [_r("permit.review_not_accepted", "$attestation.subject.scope.recipe",
                   f"bundle recipes {other} are not the attested recipe: each recipe that can run needs its review")]
    use = dict({k: v for k, v in scope.items() if k != "purposes"}, purposes=[purpose]) if isinstance(scope, dict) else None
    status = ctx.revocations
    out = evaluate(att, bundle=bundle, recipe=recipe, evidence_root=root, revocations=status,
                   roles=rv["required_roles"], use=use, now=now)
    if not out["evaluated"] or out["axes"] is None:
        return [_r("permit.attestation_mismatch", "$permit.review", "the attestation is malformed, about another bundle "
                   "or about a recipe that is not in the bundle")]
    axes = {k: v["state"] for k, v in out["axes"].items()}
    refusals = []
    if axes["capability"] != "supported":
        refusals.append(_r("permit.attestation_unsupported", "$attestation.capability", "a required capability is unknown"))
    if axes["review"] == "out-of-scope":
        refusals.append(_r("permit.review_out_of_scope", "$attestation.review", f"the review does not cover {purpose!r}"))
    elif axes["review"] != "accepted-as-recorded":
        refusals.append(_r("permit.review_not_accepted", "$attestation.review", f"review axis {axes['review']}"))
    if axes["lifecycle"] != "active":
        refusals.append(_r("permit.attestation_inactive", "$attestation.lifecycle", f"lifecycle axis {axes['lifecycle']}"))
    return refusals


def _files(paths) -> tuple[list[Path], list[dict]]:
    """The regular files a use reads: files as given, directories expanded (links inside refused)."""
    files, refusals = [], []
    for p in paths:
        try:
            path = Path(p)
            if path.is_dir():
                for q in sorted(path.rglob("*")):
                    if q.is_symlink():
                        refusals.append(_r("permit.wrong_subject", str(q), "a link inside an input directory is refused"))
                    elif q.is_file():
                        files.append(q)
            else:
                files.append(path)
        except (OSError, ValueError):
            refusals.append(_r("permit.wrong_subject", str(p), "this input cannot be read"))
    return files, refusals


def verify(permit_path, ctx: Context, *, scope: str = "formal-use", purpose: str = FORMAL_PURPOSE, inputs=(),
           project_root=None, now: datetime.datetime | None = None, account: Account | None = None,
           execution_bundle_sha256: str | None = None) -> list[dict]:
    """The refusals of a permit for one use (empty when nothing is refused). See the module docstring. For scope
    s3-execution the frozen execution bundle about to run must be given and equal the permit's."""
    from contracts.analysis_bundle import verify as verify_bundle
    now = now or datetime.datetime.now(datetime.UTC)
    if permit_path is None:
        return [_r("permit.missing", "$permit", "formal use needs a permit (--permit)")]
    chk = read_protected(permit_path, account)
    if not chk.ok:
        return [_r(code, "$permit", m) for code, m in chk.refusals]
    try:
        permit = json.loads((chk.data or b"").decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        permit = None
    rep = validate(permit, "permit.json")
    if not rep.ok or not isinstance(permit, dict):
        return [_r("permit.malformed", "$permit", ", ".join(sorted({f.code for f in rep.errors})) or "not JSON")]
    refusals: list[dict] = []
    if permit["scope"] != scope:
        refusals.append(_r("permit.wrong_scope", "$permit.scope", f"issued for {permit['scope']}, not {scope}"))
    nb, ex = _ts(permit["not_before"]), _ts(permit["expires"])
    if nb is None or now < nb:
        refusals.append(_r("permit.not_yet_valid", "$permit.not_before", "not valid yet"))
    if ex is None or now >= ex:
        refusals.append(_r("permit.expired", "$permit.expires", "expired"))
    revs = ctx.revocations
    if revs is not None and any(revs.revoked(kind="permit", ref=permit["permit_id"], sha256=d)
                                for d in (chk.sha256, canonical_sha256(permit))):
        refusals.append(_r("permit.revoked", "$permit", "the permit is revoked"))
    uses, problems = _ledger_uses(ctx, permit["nonce"], account)
    refusals += problems
    if uses is not None and uses >= permit["budget"]["uses"]:
        refusals.append(_r("permit.replayed", "$permit.nonce", f"its {permit['budget']['uses']} use(s) are recorded"))
    if permit["use"]["purpose"] != purpose:
        refusals.append(_r("permit.wrong_use", "$permit.use.purpose", f"issued for {permit['use']['purpose']!r}"))
    root = Path(project_root) if project_root else (Path(ctx.config).parent if ctx.config else Path.cwd())
    bundle = None
    try:
        bundle = json.loads((root / permit["subject"]["analysis_bundle_ref"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        bundle = None
    try:
        bundle_ok = isinstance(bundle, dict) and bundle.get("bundle_digest") == permit["subject"]["analysis_bundle_sha256"] \
            and verify_bundle(bundle, root, check_plugin=True)["status"] == "identical"
    except (OSError, ValueError, TypeError, KeyError):
        bundle_ok = False
    if not bundle_ok:
        refusals.append(_r("permit.bundle_changed", "$permit.subject",
                           "the analysis bundle is missing, another one, or no longer matches the project"))
        bundle = None
    allowed = set(permit["subject"]["artifacts"])
    files, problems = _files(inputs)
    refusals += problems
    if not files:
        refusals.append(_r("permit.wrong_subject", "$inputs", "no input file to compare with the permit's subject"))
    for f in files:
        try:
            if not (input_digests(f) & allowed):
                refusals.append(_r("permit.wrong_subject", str(f), "this input is not covered by the permit"))
        except (OSError, ValueError):
            refusals.append(_r("permit.wrong_subject", str(f), "this input cannot be read"))
    if scope == "s3-execution":
        bound = permit["subject"].get("execution_bundle_sha256")
        if not bound or bound != execution_bundle_sha256:
            refusals.append(_r("permit.wrong_subject", "$permit.subject.execution_bundle_sha256",
                               "an S3 execution permit binds the frozen execution bundle that runs"))
    if scope == "formal-use" and bundle is not None:
        refusals += _review(permit, bundle, root, ctx, purpose, now)
    return refusals


def checker(permit_path, purpose: str = FORMAL_PURPOSE, scope: str = "formal-use", execution_bundle_sha256=None):
    """The formal_check for core.protected.guard.guard(): (ctx, paths) -> refusals."""
    def check(ctx, paths):
        return verify(permit_path, ctx, scope=scope, purpose=purpose, inputs=paths,
                      execution_bundle_sha256=execution_bundle_sha256)
    return check


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("verify")
    p.add_argument("permit", type=Path)
    p.add_argument("inputs", nargs="*")
    p.add_argument("--project", type=Path, required=True)
    p.add_argument("--scope", choices=("formal-use", "s3-execution"), default="formal-use")
    p.add_argument("--purpose", default=FORMAL_PURPOSE)
    q = sub.add_parser("check-report", help="retired with the cross-artifact check; refused with the reason")
    q.add_argument("rest", nargs=argparse.REMAINDER)
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.cmd == "check-report":
        print(json.dumps({"status": "refused", "refusals": [_r(
            "permit.check_report_retired", "$cmd",
            "the cross-artifact analysis check and its reports were retired "
            "(docs/dev/cross-artifact-check/decision-retire.md); read old reports with the last release that has the check")],
            "formal_use_allowed": False}, indent=1))
        return 2
    ctx = establish(args.inputs, project=args.project)
    refusals = list(ctx.refusals) if ctx.protected else [_r("permit.not_protected", "$project",
                                                            "the project does not run in protected mode")]
    if not refusals:
        refusals = verify(args.permit, ctx, scope=args.scope, purpose=args.purpose, inputs=args.inputs,
                          project_root=args.project)
    print(json.dumps({"status": "refused" if refusals else "checked", "refusals": refusals, "formal_use_allowed": False,
                      "note": "advisory: the permit's bindings and source were checked; the custodian decides and "
                              "records the use"}, indent=1))
    return 3 if refusals else 0


if __name__ == "__main__":
    sys.exit(main())
