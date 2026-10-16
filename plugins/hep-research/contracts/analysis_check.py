#!/usr/bin/env python3
"""Opt-in cross-artifact analysis check (v6.3): freeze a chain analysis into a v2 bundle, verify it, evaluate its
obligation inventory and write a report sidecar; old entry points are unchanged and never call this module.

freeze(root, analysis, items, context): reads each item under the project root, completes the context with the
generated obligation inventory, records the semantic lock, writes both (write-once) and returns the bundle
(hep-research-analysis-bundle/2, contracts/schemas/analysis_bundle_v2.json). Lifecycle (C14): inventory and lock are
built before the bundle and never name its digest; the bundle is the completion state.

verify(bundle, root): re-digests every item (canonical JSON and bytes for .json, bytes otherwise) and the bundle.

load_subject(bundle_path, root): the check view (items, context, lock, tables, coverage contracts, catalog, suite) and
input diagnostics, each of kind input-invalid (schema, references, digests, a frozen file missing) or
dependency-missing (a definition the check needs is not available).

Usage: python3 contracts/analysis_check.py freeze --root DIR --analysis NAME --items ITEMS.json --context CONTEXT.json --out FILE
       python3 contracts/analysis_check.py check BUNDLE --root DIR [--out REPORT] [--previous REPORT]
       python3 contracts/analysis_check.py summary REPORT [--cursor N] [--max-bytes N]
Exit codes of check: 0 inputs valid and the suite complete and consistent; 1 a violation, or invalid schema,
references or digests of an input already read; 2 usage error or an unreadable top-level input; 3 otherwise
incomplete or a required dependency missing (precedence 2 > 1 > 3 > 0). freeze: 0 written, 1 refused, 2 bad usage.
A report is a diagnostic: it authorizes nothing (HC-05), and it is never written into the bundle it examines.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.analysis_bundle import BundleRefused, _no_duplicates, _read, item_digest  # noqa: E402
from contracts.analysis_checks import obligations as obl  # noqa: E402
from contracts.analysis_checks.context import check_context  # noqa: E402
from contracts.analysis_checks.lock import build_lock  # noqa: E402
from contracts.effect_catalog import load_catalog  # noqa: E402
from contracts.release_manifest import canonical_sha256  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.protected.identity import plugin_release  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FORMAT2 = "hep-research-analysis-bundle/2"
ROLES2 = ("measurement-spec", "recipe", "semantics-table", "calibration", "tool-contract", "environment-lock", "review",
          "response", "dataset-record", "context", "semantic-lock", "coverage-contract")
MODE_ROLES = {"chain": {"exactly_one": ("measurement-spec", "environment-lock", "context", "semantic-lock"),
                       "at_least_one": ("recipe",)}}
SUITE_DIR = ROOT / "contracts" / "rules" / "suites"
COVERAGE_DIR = ROOT / "contracts" / "semantics" / "coverage"
REGISTRY = ROOT / "contracts" / "rules" / "registry.json"
CONTEXT_REF, LOCK_REF = "check-context.json", "semantic-lock.json"
CHECKER_FILES = ("contracts/analysis_check.py", "contracts/analysis_checks/__init__.py",
                 "contracts/analysis_checks/scope.py", "contracts/analysis_checks/instances.py",
                 "contracts/analysis_checks/context.py", "contracts/analysis_checks/obligations.py",
                 "contracts/analysis_checks/lock.py", "contracts/analysis_checks/rules.py",
                 "contracts/analysis_checks/outcomes.py", "contracts/analysis_checks/readers.py",
                 "contracts/effect_catalog.py", "contracts/recipe_semantics.py")


class UsageError(ValueError):
    """A top-level input named on the command line cannot be read (exit 2)."""


def _file_sha(rel: str) -> str | None:
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def generator_code_digest() -> str | None:
    return _file_sha("contracts/analysis_checks/obligations.py")


def checker_identity() -> dict:
    files = {f: _file_sha(f) for f in CHECKER_FILES}
    return {"files": files, "digest": canonical_sha256(files)}


def registry_digest() -> str | None:
    try:
        return canonical_sha256(json.loads(REGISTRY.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None


def load_suite(suite_id: str, version: str) -> dict:
    return json.loads((SUITE_DIR / f"{suite_id}-{version}.json").read_text(encoding="utf-8"))


def _plugin_coverage() -> dict:
    out = {}
    for p in sorted(COVERAGE_DIR.glob("*.coverage.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        out[doc.get("table_id")] = {"doc": doc, "source": "plugin"}
    return out


def _view(items: dict, context: dict) -> tuple[dict, list[dict]]:
    """Assemble a check view from {id: {role, ref, doc, ...}} and a context; diagnostics for definitions."""
    diags: list[dict] = []
    tables = {}
    for it in items.values():
        if it["role"] == "semantics-table" and isinstance(it.get("doc"), dict):
            tables[it["doc"].get("table_id")] = it["doc"]
    plugin = _plugin_coverage()
    coverage = {}
    for tid in tables:
        bundled = [it for it in items.values() if it["role"] == "coverage-contract" and isinstance(it.get("doc"), dict)
                   and it["doc"].get("table_id") == tid]
        if bundled and tid in plugin and canonical_sha256(bundled[0]["doc"]) != canonical_sha256(plugin[tid]["doc"]):
            diags.append({"kind": "input-invalid", "code": "definition.conflict",
                          "message": f"two different coverage contracts define table '{tid}'"})
        if bundled:
            coverage[tid] = {"doc": bundled[0]["doc"], "source": "bundle"}
        elif tid in plugin:
            coverage[tid] = plugin[tid]
        else:
            diags.append({"kind": "dependency-missing", "code": "definition.coverage_missing",
                          "message": f"no operator coverage contract for table '{tid}'"})
    view = {"items": items, "context": context, "tables": tables, "coverage": coverage, "catalog": load_catalog()}
    return view, diags


def draft_view(root, items: list, context: dict, files: dict | None = None) -> dict:
    """A check view before freezing, from in-memory documents (files: ref -> content) or the files under root."""
    out = {}
    for it in items:
        doc = (files or {}).get(it["ref"])
        if doc is None and str(it["ref"]).endswith(".json"):
            doc = json.loads(_read(Path(root).resolve(), it["ref"]).decode("utf-8"))
        out[it["id"]] = {"role": it["role"], "ref": it["ref"], "doc": doc if isinstance(doc, (dict, list)) else None}
    return _view(out, context)[0]


def _item(root: Path, it: dict) -> dict:
    sha, kind = item_digest(root, it["ref"])
    rec = {"role": it["role"], "id": it["id"], "ref": it["ref"], "sha256": sha, "digest_kind": kind}
    if kind == "canonical-json":
        rec["bytes_sha256"] = hashlib.sha256(_read(root, it["ref"])).hexdigest()
    return rec


def _write_once(path: Path, doc: dict) -> None:
    data = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("utf-8")
    if path.exists() and path.read_bytes() != data:
        raise BundleRefused("bundle.exists", f"{path.name} exists with other content: freeze never overwrites")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def freeze(root, analysis: str, items: list, context: dict, mode: str = "chain") -> dict:
    root = Path(root).resolve()
    if not isinstance(items, list) or not items:
        raise BundleRefused("bundle.no_items", "a bundle needs its items")
    ids, refs = [it.get("id") for it in items], [it.get("ref") for it in items]
    for it in items:
        if not (isinstance(it, dict) and it.get("role") in ROLES2 and it.get("role") not in ("context", "semantic-lock")
                and isinstance(it.get("id"), str) and isinstance(it.get("ref"), str)):
            raise BundleRefused("bundle.bad_item", f"{it!r}: a role from {list(ROLES2)} (context and lock are generated), an id, a ref")
    if len(set(ids)) != len(ids) or {"check-context", "semantic-lock"} & set(ids):
        raise BundleRefused("bundle.duplicate_id", "item ids are unique (and 'check-context', 'semantic-lock' are reserved)")
    if len(set(refs)) != len(refs) or {CONTEXT_REF, LOCK_REF} & set(refs):
        raise BundleRefused("bundle.duplicate_ref", "a ref is listed once (and the context and lock refs are reserved)")
    _roles_ok([it["role"] for it in items] + ["context", "semantic-lock"], mode)
    rep = validate(context, "check_context.json")
    if not rep.ok:
        raise BundleRefused("bundle.context_schema", "; ".join(f"{f.path}: {f.code}" for f in rep.errors))
    view = draft_view(root, items, context)
    roles = {it["id"]: it["role"] for it in items}
    bad = [f for f in check_context(context, roles) if f["code"] in ("context.duplicate_id", "context.unknown_reference")]
    if bad:
        raise BundleRefused("bundle.context_references", "; ".join(f"{f['where']}: {f['message']}" for f in bad))
    suite = load_suite(context["suite"]["id"], context["suite"]["version"])
    full = dict(context, obligations=obl.generate(suite, view))
    view["context"] = full
    lock = build_lock(suite, generator_code_digest() or "", view, registry_digest())
    _write_once(root / CONTEXT_REF, full)
    _write_once(root / LOCK_REF, lock)
    recs = [_item(root, it) for it in items + [{"role": "context", "id": "check-context", "ref": CONTEXT_REF},
                                               {"role": "semantic-lock", "id": "semantic-lock", "ref": LOCK_REF}]]
    _roles_ok([r["role"] for r in recs], mode)
    doc = {"bundle_version": "2.0.0", "format": FORMAT2, "mode": mode, "analysis": analysis,
           "items": sorted(recs, key=lambda x: (ROLES2.index(x["role"]), x["id"])), "plugin_release": dict(plugin_release())}
    doc["bundle_digest"] = canonical_sha256(doc)
    rep = validate(doc, "analysis_bundle_v2.json")
    if not rep.ok:
        raise BundleRefused("bundle.schema", "; ".join(f"{f.path}: {f.code}" for f in rep.errors))
    return doc


def _roles_ok(roles: list, mode: str) -> None:
    need = MODE_ROLES.get(mode)
    if need is None:
        raise BundleRefused("bundle.mode", f"mode {mode!r} is not supported")
    for r in need["exactly_one"]:
        if roles.count(r) != 1:
            raise BundleRefused("bundle.roles", f"{mode} mode needs exactly one {r} item")
    for r in need["at_least_one"]:
        if r not in roles:
            raise BundleRefused("bundle.roles", f"{mode} mode needs at least one {r} item")


def verify(bundle, root) -> dict:
    rep = validate(bundle, "analysis_bundle_v2.json")
    if not rep.ok:
        return {"status": "invalid", "differences": [{"ref": f.path, "change": f.code} for f in rep.errors],
                "bundle_digest": bundle.get("bundle_digest") if isinstance(bundle, dict) else None}
    root = Path(root).resolve()
    diffs = []
    for it in bundle["items"]:
        try:
            now = _item(root, it)
        except BundleRefused as exc:
            diffs.append({"ref": it["ref"], "change": exc.code})
            continue
        for k in ("sha256", "bytes_sha256"):
            if now.get(k) != it.get(k):
                diffs.append({"ref": it["ref"], "change": f"digest:{k}"})
    if canonical_sha256({k: v for k, v in bundle.items() if k != "bundle_digest"}) != bundle["bundle_digest"]:
        diffs.append({"ref": "$", "change": "bundle_digest"})
    try:
        _roles_ok([it["role"] for it in bundle["items"]], bundle["mode"])
    except BundleRefused as exc:
        diffs.append({"ref": "$.items", "change": exc.code})
    return {"status": "different" if diffs else "identical", "differences": diffs, "bundle_digest": bundle["bundle_digest"]}


def load_subject(bundle_path, root) -> tuple[dict, list[dict]]:
    """The check view of a frozen bundle and its input diagnostics. UsageError when the bundle itself is unreadable."""
    root = Path(root).resolve()
    try:
        bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)
    except (OSError, UnicodeError, ValueError) as exc:
        raise UsageError(f"cannot read the bundle {bundle_path}: {exc}") from None
    if not isinstance(bundle, dict):
        raise UsageError(f"{bundle_path} is not a JSON object")
    diags: list[dict] = []
    ver = verify(bundle, root)
    for d in ver["differences"]:
        diags.append({"kind": "input-invalid", "code": f"bundle.{d['change']}".replace("bundle.bundle.", "bundle."),
                      "message": f"{d['ref']}: {d['change']}"})
    items = {}
    for it in bundle.get("items", []) if isinstance(bundle.get("items"), list) else []:
        if not isinstance(it, dict) or "id" not in it:
            continue
        rec = dict(it, doc=None)
        if str(it.get("ref", "")).endswith(".json"):
            try:
                rec["doc"] = json.loads(_read(root, it["ref"]).decode("utf-8"))
            except (BundleRefused, UnicodeError, ValueError):
                pass  # reported by verify as a missing or changed frozen file
        items[it["id"]] = rec
    ctx_items = [i for i in items.values() if i.get("role") == "context"]
    lock_items = [i for i in items.values() if i.get("role") == "semantic-lock"]
    context = ctx_items[0]["doc"] if ctx_items and isinstance(ctx_items[0]["doc"], dict) else {}
    lock = lock_items[0]["doc"] if lock_items and isinstance(lock_items[0]["doc"], dict) else {}
    for name, doc in (("check_context.json", context), ("semantic_lock.json", lock)):
        rep = validate(doc, name)
        for f in rep.errors:
            diags.append({"kind": "input-invalid", "code": f"{name.split('.')[0]}.{f.code}", "message": f"{f.path}: {f.message}"})
    view, more = _view(items, context)
    diags += more
    view.update(bundle=bundle, lock=lock, bundle_verified=ver["status"])
    roles = {k: v.get("role") for k, v in items.items()}
    view["context_findings"] = check_context(context, roles) if context else []
    for f in view["context_findings"]:
        if f["code"] in ("context.duplicate_id", "context.unknown_reference"):
            diags.append({"kind": "input-invalid", "code": f["code"], "message": f"{f['where']}: {f['message']}"})
    suite = (context.get("suite") or {}) if isinstance(context, dict) else {}
    try:
        view["suite"] = load_suite(str(suite.get("id")), str(suite.get("version")))
    except (OSError, ValueError):
        view["suite"] = None
        diags.append({"kind": "dependency-missing", "code": "definition.suite_missing",
                      "message": f"suite {suite.get('id')!r} version {suite.get('version')!r} is not installed"})
    return view, diags


def current_lock(view: dict) -> dict:
    return build_lock(view.get("suite") or {}, generator_code_digest() or "", view, registry_digest())


def check_inventory(view: dict) -> list[dict]:
    frozen = (view.get("context") or {}).get("obligations") or {}
    if view.get("suite") is None:
        return []
    return obl.check_inventory(frozen, obl.generate(view["suite"], view))
