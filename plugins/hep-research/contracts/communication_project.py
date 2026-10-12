#!/usr/bin/env python3
"""Project-level resolution of a communication record: compose the dependency checker, the evidence ledgers and the
declared documents inside an explicit project root, and normalize outcomes for the communication CLIs.

Usage: python3 contracts/communication_project.py RECORD.json --root PROJECT_ROOT
Exit codes: 0 everything resolved, 1 resolution or dependency errors, 3 unresolved only, 2 unreadable input or bad usage.
Output: the context as JSON on stdout.

What it does, with no network access and no file outside the root ever opened:
  - validates the record (contracts/validate.py; the capability selects the legacy or traceability schema);
  - resolves every input through contracts/dependencies.py (existence, identity, hashes, statuses, cycles, root
    boundary) and exposes each input's actual statuses next to the declared ones;
  - loads the declared evidence ledgers (project-relative sources/claims files, their hashes when declared) and the
    ledgers of the project's bound profiles for entries marked `bound: true`; it never scans profiles for a namespace;
  - resolves every cited source id against the loaded ledger of its namespace, reporting an unknown id and an
    unavailable ledger as two different findings;
  - resolves every declared document's path and digest (the content is inspected by the skill's manuscript check).
A legacy record (no communication:traceability-v1) is reported as limited traceability, never as fully traced.
Schema validity, dependency consistency, scientific support and output readiness remain separate statements; this
module makes none of the last two. contracts/communication.py (pure) never imports this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.communication import format_of  # noqa: E402
from contracts.dependencies import SCHEME, validate_dependencies  # noqa: E402
from contracts.schema import Report  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import NAMESPACED, Vocabulary  # noqa: E402
from core.evidence.ledger import check_ledger  # noqa: E402

CONFIG_NAME = "hep-research.project.json"
ALL_CHECKS = ("schema", "dependencies", "ledgers", "documents")
NOTE = ("resolution only: a resolved record says nothing about the physical validity of any artifact or the scientific "
        "support of any claim; those are assessed by a reader and recorded, not established here")


def findings_of(rep: Report) -> list[dict]:
    return [f.as_dict() for f in rep.findings]


def resolve_outcome(findings: list[dict], *, input_error: bool = False, blocked: bool = False) -> tuple[str, int]:
    """The CLI outcome in the plan's precedence: invocation/primary-input failure -> input-error/2; a confirmed error ->
    fail/1; an unresolved required check (or a check blocked by the environment) -> incomplete/3; else pass/0.
    Warnings alone pass. Never derived from Report.ok alone, which is true with unresolved findings present."""
    if input_error:
        return "input-error", 2
    sev = {f.get("severity") for f in findings}
    if "error" in sev:
        return "fail", 1
    if "unresolved" in sev or blocked:
        return "incomplete", 3
    return "pass", 0


def normalize_dependency_report(dep: dict) -> list[dict]:
    """The dependency checker's findings, plus an unresolved finding when its consistency flag is false without one:
    a failed upstream input leaves status 'ok' but dependency_consistency_ok false, which must not read as complete."""
    out = [dict(f) for f in dep.get("findings", []) or []]
    if not dep.get("dependency_consistency_ok", True) and not any(f.get("severity") in ("error", "unresolved") for f in out):
        out.append({"severity": "unresolved", "path": "$.inputs", "code": "dependency.failed_upstream",
                    "message": "an input chain carries 'failed': the record is not consistent for use even though every "
                               "reference resolves"})
    return out


def output_aliases_input(out_path, input_paths) -> bool:
    """True when the output path names one of the inputs (same path, '..' spelling or a symlink alias): a report must
    never overwrite the evidence it audits."""
    out = Path(out_path)
    try:
        out_res = out.resolve()
    except (OSError, RuntimeError):
        out_res = Path(os.path.abspath(out))
    for p in input_paths:
        p = Path(p)
        try:
            if out_res == p.resolve():
                return True
            if out.exists() and p.exists() and os.path.samefile(out, p):
                return True
        except (OSError, RuntimeError):
            continue
    return False


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


class _Resolver:
    def __init__(self, root: Path):
        self.root = root
        self.findings: list[dict] = []

    def add(self, severity, where, code, message):
        self.findings.append({"severity": severity, "path": where, "code": code, "message": message})

    def resolve(self, ref: str, where: str) -> Path | None:
        raw = Path(ref)
        cand = raw if raw.is_absolute() else self.root / raw
        res = cand.resolve()  # follows symlinks, so a link pointing out of the root is refused as well
        if not _inside(res, self.root):
            self.add("error", where, "resolution.outside_root", f"{ref!r} resolves outside the project root; it is not read")
            return None
        return res

    def read_json(self, path: Path, where: str, code: str):
        try:
            raw = path.read_bytes()
        except OSError as exc:
            self.add("error", where, code, f"cannot read {_rel(path, self.root)}: {exc}")
            return None, None
        try:
            return raw, json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            self.add("error", where, code, f"{_rel(path, self.root)} is not JSON: {exc}")
            return raw, None


def _load_project(root: Path, r: _Resolver):
    cfg = root / CONFIG_NAME
    if not cfg.is_file():
        return None
    from contracts.project import load_project
    try:
        proj = load_project(root)
    except (OSError, ValueError) as exc:
        r.add("warning", "$project", "resolution.project_config_unreadable", f"{CONFIG_NAME} cannot be read ({exc}); no profile is bound")
        return None
    for f in proj.report.errors:
        r.add("warning", "$project", "resolution.project_config_invalid", f"{f.code}: {f.message}")
    return proj


def _inputs(doc: dict, r: _Resolver) -> dict:
    out: dict[str, dict] = {}
    for inp in doc.get("inputs", []) or []:
        if not isinstance(inp, dict) or not isinstance(inp.get("ref"), str):
            continue
        ref = inp["ref"]
        entry = {"ref": ref, "declared_sha256": inp.get("sha256"), "declared_status": list(inp.get("status", []) or []),
                 "resolved": False, "path": None, "sha256": None, "status": None, "artifact_type": None, "artifact_id": None,
                 "match": None, "external": bool(inp.get("external")) or bool(SCHEME.match(ref) and not Path(ref).is_absolute())}
        out[ref] = entry
        if entry["external"]:
            continue
        raw = Path(ref)
        cand = (raw if raw.is_absolute() else r.root / raw).resolve()
        if not _inside(cand, r.root) or not cand.is_file():
            continue  # the dependency checker already reported outside_root or missing
        try:
            data = cand.read_bytes()
        except OSError:
            continue
        entry.update(resolved=True, path=_rel(cand, r.root), sha256=hashlib.sha256(data).hexdigest())
        entry["match"] = (entry["sha256"] == entry["declared_sha256"]) if entry["declared_sha256"] else None
        try:
            sdoc = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue
        if isinstance(sdoc, dict):
            entry.update(status=list(sdoc.get("status", []) or []), artifact_type=sdoc.get("artifact_type"), artifact_id=sdoc.get("artifact_id"))
    return out


def _ledger_file(r: _Resolver, ref: str, declared_sha, where: str, entry: dict):
    """One ledger file: (records or None). Updates entry['sha256_checked'] (True/False/None)."""
    path = r.resolve(ref, where)
    if path is None:
        return None
    if not path.is_file():
        r.add("unresolved", where, "resolution.ledger_missing",
              f"ledger file {ref!r} does not exist in the project: its sources cannot be resolved (unavailable, not wrong)")
        return None
    raw, data = r.read_json(path, where, "resolution.ledger_unreadable")
    if raw is None:
        return None
    digest = hashlib.sha256(raw).hexdigest()
    if declared_sha is None:
        r.add("unresolved", where, "resolution.ledger_no_hash", f"{ref!r} has no declared sha256: a substituted ledger cannot be detected")
        if entry["sha256_checked"] is not False:
            entry["sha256_checked"] = None
    elif declared_sha != digest:
        r.add("error", where, "resolution.ledger_hash_mismatch", f"{ref!r} has sha256 {digest}, the record declares {declared_sha}")
        entry["sha256_checked"] = False
    elif entry["sha256_checked"] is None and entry.get("_hash_seen") is None:
        entry["sha256_checked"] = True
    entry["_hash_seen"] = True
    if data is None:
        return None
    if not isinstance(data, list):
        r.add("error", where, "resolution.ledger_unreadable", f"{ref!r} is not a JSON array of records")
        return None
    return data


def _ledgers(ext: dict, proj, r: _Resolver) -> dict:
    out: dict[str, dict] = {}
    bound = {}
    for p in (proj.profiles if proj is not None else []):
        if p.get("evidence_namespace") and p.get("_dir"):
            bound[p["evidence_namespace"]] = p
    for k, led in enumerate(ext.get("evidence_ledgers", []) or []):
        if not isinstance(led, dict):
            continue
        ns, where = str(led.get("namespace")), f"$.extension.evidence_ledgers[{k}]"
        entry: dict = {"namespace": ns, "bound": bool(led.get("bound")), "sources_ref": led.get("sources_ref"), "claims_ref": led.get("claims_ref"),
                 "loaded": False, "sources": {}, "claims": {}, "report": None, "sha256_checked": None}
        out[ns] = entry
        sources = claims = None
        if entry["bound"]:
            prof = bound.get(ns)
            if prof is None:
                r.add("error", where, "resolution.ledger_not_bound",
                      f"ledger '{ns}' is marked bound but no profile bound in {CONFIG_NAME} has that evidence namespace; profiles are never scanned")
                continue
            pdir = Path(prof["_dir"]) / str((prof.get("resources") or {}).get("evidence") or "evidence")
            entry["sources_ref"], entry["claims_ref"] = str(pdir / "sources.json"), str(pdir / "claims.json")
            try:
                sources = json.loads((pdir / "sources.json").read_text(encoding="utf-8"))
                claims = json.loads((pdir / "claims.json").read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                r.add("error", where, "resolution.ledger_unreadable", f"bound profile ledger for '{ns}' cannot be read: {exc}")
                continue
        else:
            sources = _ledger_file(r, str(led.get("sources_ref")), led.get("sources_sha256"), where, entry)
            claims = _ledger_file(r, str(led.get("claims_ref")), led.get("claims_sha256"), where, entry)
        entry.pop("_hash_seen", None)
        if sources is None or claims is None:
            continue
        report = check_ledger(sources, claims, namespace=ns)
        entry["report"] = report
        if report.get("errors"):
            codes = sorted({e["code"] for e in report["errors"]})
            r.add("error", where, "resolution.ledger_invalid", f"ledger '{ns}' fails its own check: {', '.join(codes)}")
        entry["sources"] = {s["id"]: s for s in sources if isinstance(s, dict) and isinstance(s.get("id"), str)}
        entry["claims"] = {c["id"]: c for c in claims if isinstance(c, dict) and isinstance(c.get("id"), str)}
        entry["loaded"] = True
    return out


def _sources(ext: dict, ledgers: dict, r: _Resolver) -> dict:
    ids: dict[str, str] = {}
    for i, c in enumerate(ext.get("claims", []) or []):
        for j, e in enumerate((c.get("evidence", []) or []) if isinstance(c, dict) else []):
            if isinstance(e, dict) and e.get("target_kind") == "source" and isinstance(e.get("target"), str):
                ids.setdefault(e["target"], f"$.extension.claims[{i}].evidence[{j}].target")
    for k, ev in enumerate(ext.get("sources_read", []) or []):
        if isinstance(ev, dict) and isinstance(ev.get("id"), str):
            ids.setdefault(ev["id"], f"$.extension.sources_read[{k}].id")
    out: dict[str, dict] = {}
    for sid, where in ids.items():
        m = NAMESPACED.match(sid)
        ns = m.group(1) if m else None
        entry = {"namespace": ns, "resolved": False, "record": None, "reason": None}
        out[sid] = entry
        led = ledgers.get(ns)
        if led is None:
            entry["reason"] = "namespace not declared"  # the schema-level check already reports it
        elif not led["loaded"]:
            entry["reason"] = "ledger unavailable"
            r.add("unresolved", where, "resolution.source_unavailable", f"'{sid}' cannot be resolved: the ledger of '{ns}' was not loaded")
        elif sid in led["sources"]:
            entry.update(resolved=True, record=led["sources"][sid])
        else:
            entry["reason"] = "unknown id"
            r.add("error", where, "resolution.unknown_source", f"'{sid}' is not in the ledger of '{ns}'")
    return out


def _documents(ext: dict, r: _Resolver) -> dict:
    out: dict[str, dict] = {}
    inspected = {o.get("document_id") for o in ext.get("occurrences", []) or [] if isinstance(o, dict) and o.get("state") == "inspected"}
    for k, d in enumerate(ext.get("documents", []) or []):
        if not isinstance(d, dict):
            continue
        where = f"$.extension.documents[{k}]"
        entry = {"path": d.get("path"), "format": d.get("format"), "resolved": False, "resolved_path": None,
                 "sha256": None, "declared_sha256": d.get("sha256")}
        out[str(d.get("id"))] = entry
        path = r.resolve(str(d.get("path")), where)
        if path is None:
            continue
        if not path.is_file():
            r.add("unresolved", where, "resolution.document_missing", f"document {d.get('path')!r} does not exist in the project")
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            r.add("error", where, "resolution.document_unreadable", f"cannot read {d.get('path')!r}: {exc}")
            continue
        entry.update(resolved=True, resolved_path=_rel(path, r.root), sha256=hashlib.sha256(data).hexdigest())
        if entry["declared_sha256"] and entry["declared_sha256"] != entry["sha256"]:
            r.add("unresolved" if d.get("id") in inspected else "warning", where, "resolution.document_changed",
                  f"document {d.get('path')!r} has sha256 {entry['sha256']}, the record declares {entry['declared_sha256']}: "
                  "its occurrences must be re-inspected")
    return out


def resolve_context(artifact_path, project_root, *, vocab: Vocabulary | None = None, project=None) -> dict:
    """Normalized artifacts, ledgers, sources and documents of a communication record plus structured resolution
    findings; see the module docstring. `project` (a contracts.project.Project) overrides the config found in the root."""
    root = Path(project_root).resolve()
    path = Path(artifact_path)
    path = (path if path.is_absolute() else Path.cwd() / path).resolve()
    r = _Resolver(root)
    ctx: dict = {"project_root": str(root), "artifact_path": None, "artifact_sha256": None, "artifact": None, "format": None, "traceability": "none",
                 "profiles": [], "schema": None, "dependencies": None, "inputs": {}, "ledgers": {}, "sources": {}, "documents": {},
                 "findings": r.findings, "checks_run": [], "checks_not_run": [], "note": NOTE}

    def not_run(*names, reason):
        for n in names:
            ctx["checks_not_run"].append({"check": n, "reason": reason})
    if not root.is_dir():
        r.add("error", "$", "resolution.bad_root", f"project root {project_root} is not a directory")
        not_run(*ALL_CHECKS, reason="no project root")
        return ctx
    if not _inside(path, root):
        r.add("error", "$", "resolution.outside_root", f"{artifact_path} lies outside the project root; it is not read")
        not_run(*ALL_CHECKS, reason="artifact outside the project root")
        return ctx
    ctx["artifact_path"] = _rel(path, root)
    raw, doc = r.read_json(path, "$", "resolution.unreadable") if path.is_file() else (None, None)
    if raw is None:
        if not path.is_file():
            r.add("error", "$", "resolution.unreadable", f"{artifact_path} does not exist")
        not_run(*ALL_CHECKS, reason="the record cannot be read")
        return ctx
    ctx["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
    if not isinstance(doc, dict):
        if doc is not None:
            r.add("error", "$", "resolution.unreadable", f"{artifact_path} is not a JSON object")
        not_run(*ALL_CHECKS, reason="the record cannot be read")
        return ctx
    ctx["artifact"] = doc
    proj = project if project is not None else _load_project(root, r)
    if proj is not None:
        ctx["profiles"] = [p.get("id") for p in proj.profiles]
        if vocab is None:
            vocab = Vocabulary.with_profiles(proj.profiles)
            for prob in vocab.problems:
                r.add("error", "$project", "resolution.profile_vocab", prob)
    vocab = vocab or Vocabulary()
    ctx["schema"] = validate_artifact(doc, vocab).as_dict()
    ctx["checks_run"].append("schema")
    fmt = format_of(doc)
    ctx["format"] = fmt
    ctx["traceability"] = "declared" if fmt == "traceability" else "limited"
    if fmt == "legacy":
        r.add("unresolved", "$.required_capabilities", "resolution.limited_traceability",
              "legacy communication record: claims carry no evidence edges, occurrences or assessments, so only the "
              "envelope inputs can be resolved; it is not fully traced")
    ctx["dependencies"] = validate_dependencies(path, root, vocab=vocab)
    ctx["checks_run"].append("dependencies")
    ctx["inputs"] = _inputs(doc, r)
    raw_ext = doc.get("extension")
    ext: dict = raw_ext if isinstance(raw_ext, dict) else {}
    if fmt != "traceability":
        not_run("ledgers", "documents", reason="legacy format declares no ledgers or documents")
        return ctx
    if ext.get("evidence_ledgers") or (ext.get("scope") or {}).get("sources"):
        ctx["ledgers"] = _ledgers(ext, proj, r)
        ctx["sources"] = _sources(ext, ctx["ledgers"], r)
        ctx["checks_run"].append("ledgers")
    else:
        ctx["sources"] = _sources(ext, {}, r)
        not_run("ledgers", reason="no evidence ledger declared and sources not in scope")
    if ext.get("documents"):
        ctx["documents"] = _documents(ext, r)
        ctx["checks_run"].append("documents")
    else:
        not_run("documents", reason="no document declared")
    return ctx


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("artifact", type=Path)
    ap.add_argument("--root", type=Path, required=True, help="project root: no file outside it is read")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    ctx = resolve_context(args.artifact, args.root)
    print(json.dumps(ctx, indent=1, default=str))
    if any(f["code"] in ("resolution.bad_root", "resolution.unreadable") for f in ctx["findings"]):
        return 2
    findings = list(ctx["findings"]) + (ctx["schema"]["findings"] if ctx["schema"] else []) + \
        (normalize_dependency_report(ctx["dependencies"]) if ctx["dependencies"] else [])
    return resolve_outcome(findings)[1]


if __name__ == "__main__":
    sys.exit(main())
