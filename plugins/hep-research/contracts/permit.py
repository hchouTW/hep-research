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
       python3 contracts/permit.py check-report ATTESTATION --bundle B --root DIR --policy P --revocations R
           [--permit PERMIT] [--evidence-root DIR] [--required-roles ROLE ...] [--purpose PURPOSE] [--now ISO]

check-report (v6.3 D10, advisory): an analysis-check report counts only among an accepted, bound review's evidence,
about the permit's bundle, internally consistent, from the suites and checker the custodian's purpose policy names,
complete and without violation (codes permit.report_*). It never reports a use as allowed.
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


REPORT_SCHEMA = "check_report.json"


def report_check(att: dict, bundle: dict, root, evidence_root, policy: dict, purpose: str = FORMAL_PURPOSE, *,
                 permit: dict | None = None, now: datetime.datetime | None = None, revocations=None,
                 roles: list | None = None) -> list[dict]:
    """Advisory check of an analysis-check report for formal use (v6.3 D10, C15). The report counts only as evidence
    of an accepted, bound attestation review (found among the review's evidence by the report's own schema); it must
    be about the permit's analysis bundle, internally consistent (a hand-edited pass fails), from the suites and the
    checker the custodian's purpose policy names, complete and without a violation. Declaration-based outcomes count
    because the accepted review lists the report. With pre-execution reports only (no result binding yet), the policy
    must say it accepts them. Returns refusals; it never reports a use as allowed (the custodian's gate decides)."""
    from contracts.analysis_checks.outcomes import formal_view, summarize
    from contracts.attestation import evaluate
    now = now or datetime.datetime.now(datetime.UTC)
    root, evidence_root = Path(root), Path(evidence_root)
    refusals: list[dict] = []
    digest = bundle.get("bundle_digest") if isinstance(bundle, dict) else None
    if permit is not None and (permit.get("subject") or {}).get("analysis_bundle_sha256") != digest:
        refusals.append(_r("permit.report_wrong_subject", "$permit.subject.analysis_bundle_sha256",
                           "the permit binds another analysis bundle than the one checked"))
    scope = ((att.get("subject") or {}).get("scope") or {}) if isinstance(att, dict) else {}
    recipe_sha = (scope.get("recipe") or {}).get("sha256")
    recipe = None
    for it in (bundle or {}).get("items", []):
        if it.get("role") == "recipe" and it.get("sha256") == recipe_sha:
            try:
                recipe = json.loads((root / it["ref"]).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                recipe = None
    use = dict({k: v for k, v in scope.items() if k != "purposes"}, purposes=[purpose]) if scope else None
    out = evaluate(att, bundle=bundle, recipe=recipe, evidence_root=evidence_root, revocations=revocations,
                   roles=roles, use=use, now=now)
    axes = {k: v["state"] for k, v in (out.get("axes") or {}).items()}
    if not out.get("evaluated") or axes.get("review") != "accepted-as-recorded" or axes.get("lifecycle") != "active":
        return refusals + [_r("permit.report_unreviewed", "$attestation.review",
                              f"no accepted, bound and active review (review {axes.get('review')}, lifecycle "
                              f"{axes.get('lifecycle')}): a report alone never counts")]
    reports = []
    for r in att["review"]["reviews"]:
        if r.get("conclusion") != "accepted" or r.get("bundle_sha256") != att["subject"]["bundle_sha256"]:
            continue
        for e in r.get("evidence", []):
            try:
                doc = json.loads((evidence_root / e["ref"]).read_text(encoding="utf-8"))
            except (OSError, ValueError, KeyError):
                continue
            if validate(doc, REPORT_SCHEMA).ok:
                reports.append((e["ref"], doc))
    if not reports:
        return refusals + [_r("permit.report_missing", "$attestation.review.evidence",
                              "the accepted review lists no analysis-check report as evidence")]
    rules = (policy.get("purposes") or {}).get(purpose) if isinstance(policy, dict) else None
    if not isinstance(rules, dict):
        return refusals + [_r("permit.report_policy_missing", "$policy.purposes",
                              f"the purpose policy says nothing about {purpose!r}")]
    for ref, rep_doc in reports:
        where = f"$evidence:{ref}"
        if rep_doc.get("subject_digest") != digest:
            refusals.append(_r("permit.report_wrong_subject", where, "the report is about another bundle"))
        s = summarize(rep_doc["obligations"], rep_doc["input_validity"] == "valid")
        consistent = (canonical_sha256(rep_doc["assessment"]) == rep_doc["assessment_id"]
                      and rep_doc["assessment"].get("subject") == rep_doc.get("subject_digest")
                      and {k: s[k] for k in ("coverage", "consistency", "counts")}
                      == {k: rep_doc[k] for k in ("coverage", "consistency", "counts")}
                      and formal_view(rep_doc["obligations"], rep_doc["input_validity"] == "valid") == rep_doc["formal_use_view"])
        if not consistent:
            refusals.append(_r("permit.report_inconsistent", where,
                               "the report's summary or assessment does not follow from its obligations (edited?)"))
            continue
        have = rep_doc["assessment"].get("suites") or [rep_doc["assessment"].get("suite")]
        missing = [x for x in rules.get("suites", []) if x not in have]
        if missing:
            refusals.append(_r("permit.report_wrong_suite", where, f"the policy needs suites {missing}"))
        if rules.get("checker_digests") is not None and rep_doc["assessment"].get("checker") not in rules["checker_digests"]:
            refusals.append(_r("permit.report_stale_assessment", where, "the report's checker is not one the policy accepts"))
        if rep_doc["input_validity"] != "valid" or rep_doc["coverage"]["value"] != "complete":
            refusals.append(_r("permit.report_incomplete", where, "the report is not complete on valid inputs"))
        elif rep_doc["consistency"] != "consistent":
            refusals.append(_r("permit.report_violation", where, "the report establishes a violation"))
        binding = rep_doc.get("result_binding")
        if isinstance(binding, dict) and permit is not None:  # post-execution part (V60, m2c-design.md)
            subject = permit.get("subject") or {}
            unlisted = [r.get("sha256") for r in binding.get("results", []) if r.get("sha256") not in (subject.get("artifacts") or [])]
            if unlisted:
                refusals.append(_r("permit.report_result_unlisted", where,
                                   f"{len(unlisted)} result file(s) the report's binding cites are not in the permit's artifacts"))
            eb = subject.get("execution_bundle_sha256")
            if eb and any(x != eb for x in binding.get("execution_bundles", [])):
                refusals.append(_r("permit.report_execution_bundle_mismatch", where,
                                   "the result binding's execution bundle is not the permit's"))
        if "not checked" in str(rep_doc.get("execution_evidence_level")) and not rules.get("accept_pre_execution_only"):
            refusals.append(_r("permit.report_pre_execution_only", where,
                               "a pre-execution report: run lineage was not checked, and the policy does not accept that"))
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
    q = sub.add_parser("check-report", help="advisory: an analysis-check report among an accepted review's evidence")
    q.add_argument("attestation", type=Path)
    q.add_argument("--bundle", type=Path, required=True)
    q.add_argument("--root", type=Path, required=True)
    q.add_argument("--evidence-root", type=Path)
    q.add_argument("--policy", type=Path, required=True, help="the custodian's purpose policy (JSON)")
    q.add_argument("--permit", type=Path)
    q.add_argument("--revocations", type=Path, required=True)
    q.add_argument("--required-roles", action="append", default=[])
    q.add_argument("--purpose", default=FORMAL_PURPOSE)
    q.add_argument("--now", default=None, help="ISO time (default: now)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.cmd == "check-report":
        try:
            load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))  # noqa: E731
            now = _ts(args.now) if args.now else None
            if args.now and now is None:
                raise ValueError("--now is an ISO time")
            refusals = report_check(load(args.attestation), load(args.bundle), args.root, args.evidence_root or args.root,
                                    load(args.policy), args.purpose, permit=load(args.permit) if args.permit else None,
                                    now=now, revocations=load(args.revocations), roles=args.required_roles or None)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            print(json.dumps({"status": "usage", "error": str(exc)}))
            return 2
        print(json.dumps({"status": "refused" if refusals else "checked", "refusals": refusals, "formal_use_allowed": False,
                          "note": "advisory: the report's bindings were checked; the custodian's gate decides and enforces"},
                         indent=1))
        return 3 if refusals else 0
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
