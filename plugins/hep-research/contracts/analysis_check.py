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

Snapshots are on by default (D11b): freeze stores the pinned definitions in <root>/.hep-research/snapshots/ and
records the bundle in <root>/.hep-research/bundles.json; check reproduces a drifted subject from that store when it
exists. 'snapshots gc' lists (dry run) or deletes (--apply) only snapshots no indexed bundle references.

Removed in 0.28.0 (value gate Shrink, docs/dev/cross-artifact-check/decision-value-gate.md): the model-card and
run-lineage suites, model-only bundles (--mode model), result bindings (--results) and the project blinding block
(--project). A context or bundle that names them is refused with that reason; reproduce such reports with 0.27.x.

Usage: python3 contracts/analysis_check.py freeze --root DIR --analysis NAME --items ITEMS.json --context CONTEXT.json --out FILE
                                            [--snapshots DIR | --no-snapshots]
       python3 contracts/analysis_check.py check BUNDLE --root DIR [--out REPORT] [--previous REPORT] [--snapshots DIR]
                                            [--exceptions FILE]
       python3 contracts/analysis_check.py summary REPORT [--cursor N] [--max-bytes N]
       python3 contracts/analysis_check.py snapshots gc --root DIR [--apply]
Exit codes of check: 0 inputs valid and the suite complete and consistent; 1 a violation, or invalid schema,
references or digests of an input already read; 2 usage error or an unreadable top-level input; 3 otherwise
incomplete, a required dependency missing, or definitions that differ from the semantic lock (precedence
2 > 1 > 3 > 0); the status is 'complete' only with exit 0 (P6). freeze: 0 written, 1 refused, 2 bad usage.
snapshots gc: 0 done, 1 refused (an indexed bundle is unreadable), 2 bad usage.
A report is a diagnostic: it authorizes nothing (HC-05), and it is never written into the bundle it examines.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.analysis_bundle import BundleRefused, _no_duplicates, _read, item_digest  # noqa: E402
from contracts.analysis_checks import obligations as obl  # noqa: E402
from contracts.analysis_checks.context import check_context, input_findings, version_findings  # noqa: E402
from contracts.analysis_checks.lock import build_lock  # noqa: E402
from contracts.effect_catalog import load_catalog  # noqa: E402
from contracts.release_manifest import canonical_sha256  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.protected.identity import plugin_release  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FORMAT2 = "hep-research-analysis-bundle/2"
ROLES2 = ("measurement-spec", "recipe", "semantics-table", "calibration", "tool-contract", "environment-lock", "review",
          "response", "dataset-record", "context", "semantic-lock", "coverage-contract", "validation-record")
MODE_ROLES = {"chain": {"exactly_one": ("measurement-spec", "environment-lock", "context", "semantic-lock"),
                       "at_least_one": ("recipe",)}}
# Removed in 0.28.0 (value gate Shrink, decision-value-gate.md; architecture section 13.4): refused with this reason
REMOVED_SUITES = ("model-card", "run-lineage")
REMOVED = ("removed in hep-research 0.28.0 (cross-artifact check Shrink: model-card, run-lineage, model-only bundles "
           "and result bindings); reproduce it with 0.27.x")
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
# the code the obligation generator runs: the generator itself and the catalog it resolves
GENERATOR_FILES = ("contracts/analysis_checks/obligations.py", "contracts/effect_catalog.py")
STATE_DIR = ".hep-research"


class UsageError(ValueError):
    """A top-level input named on the command line cannot be read (exit 2)."""


def _file_sha(rel: str) -> str | None:
    p = ROOT / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def generator_code_digest() -> str | None:
    files = {f: _file_sha(f) for f in GENERATOR_FILES}
    return canonical_sha256(files) if all(files.values()) else None


def _loaded_plugin_files() -> set[str]:
    """Plugin modules (contracts/, core/) loaded in this process: the code a check actually ran."""
    out = set()
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        try:
            rel = Path(f).resolve().relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if rel.endswith(".py") and rel.split("/", 1)[0] in ("contracts", "core"):
            out.add(rel)
    return out


def checker_identity() -> dict:
    """The digests of the checker's files and of every other plugin module loaded at run time (G10)."""
    files = {f: _file_sha(f) for f in sorted(set(CHECKER_FILES) | _loaded_plugin_files())}
    return {"files": files, "digest": canonical_sha256(files)}


def registry_digest() -> str | None:
    try:
        return canonical_sha256(json.loads(REGISTRY.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None


def load_suite(suite_id: str, version: str) -> dict:
    return json.loads((SUITE_DIR / f"{suite_id}-{version}.json").read_text(encoding="utf-8"))


def context_suites(context: dict) -> list[dict]:
    """The suites a context selects: its primary suite, then any further ones, each once."""
    out = []
    for s in [context.get("suite") or {}] + list(context.get("suites") or []):
        key = {"id": s.get("id"), "version": s.get("version")}
        if key not in out:
            out.append(key)
    return out


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


JSON_ROLES = ("measurement-spec", "recipe", "semantics-table", "response", "dataset-record", "context", "semantic-lock",
              "coverage-contract", "validation-record")
SHAPES = {"recipe": "recipe.json", "semantics-table": "operator_semantics.json", "coverage-contract": "operator_coverage.json",
          "validation-record": "validation_record.json"}


def _is_json(ref) -> bool:
    return str(ref).lower().endswith(".json")


def shape_diagnostics(items: dict, context_version="1.0.0") -> list[dict]:
    """Input-invalid diagnostics for item documents the rules read, checked against their schemas; a document that
    fails is set to None so no rule or generator reads it (the check reports the input, never a traceback). Only the
    input checks the context version enables run (P3)."""
    from contracts.analysis_checks.context import input_check_enabled
    on = lambda name: input_check_enabled(context_version, name)  # noqa: E731
    diags = []
    for iid, it in sorted(items.items()):
        role, doc = it.get("role"), it.get("doc")
        if role in JSON_ROLES and _is_json(it.get("ref")) and doc is None:
            continue  # unreadable: verify reports the frozen file
        if role in JSON_ROLES and not isinstance(doc, dict) and on("item.not_an_object"):
            diags.append({"kind": "input-invalid", "code": "item.not_an_object", "message": f"{iid}: a {role} is a JSON object"})
            it["doc"] = None
        elif role in SHAPES and on("item.schema"):
            res = validate(doc, SHAPES[role])
            if not res.ok:
                diags.append({"kind": "input-invalid", "code": f"item.schema:{role}",
                              "message": f"{iid}: " + "; ".join(f"{f.path}: {f.code}" for f in res.errors[:5])})
                it["doc"] = None
        elif role == "calibration" and isinstance(doc, dict) and on("calibration.shape") and _is_factor_table(doc):
            problems = factor_table_shape(doc)
            if problems:
                diags.append({"kind": "input-invalid", "code": "calibration.shape", "message": f"{iid}: " + "; ".join(problems[:5])})
                it["doc"] = None
        elif role == "measurement-spec" and isinstance(doc, dict):
            corr = (doc.get("extension") or {}).get("corrections") if isinstance(doc.get("extension"), dict) else None
            if not on("spec.bad_corrections"):
                pass
            elif corr is not None and not (isinstance(corr, list) and all(isinstance(c, dict) for c in corr)):
                diags.append({"kind": "input-invalid", "code": "spec.bad_corrections", "message": f"{iid}: corrections are objects"})
                it["doc"] = None
                continue
            ids = [c.get("effect_id") for c in corr or []] if on("spec.duplicate_effect_id") and isinstance(corr, list) else []
            for d in sorted({str(x) for x in ids if ids.count(x) > 1}):
                diags.append({"kind": "input-invalid", "code": "spec.duplicate_effect_id",
                              "message": f"{iid}: effect_id {d!r} names two corrections"})
    if on("coverage.duplicate_contract"):
        by_table: dict = {}
        for iid, it in sorted(items.items()):
            if it.get("role") == "coverage-contract" and isinstance(it.get("doc"), dict):
                by_table.setdefault(str(it["doc"].get("table_id")), []).append((iid, canonical_sha256(it["doc"])))
        for tid, docs in sorted(by_table.items()):
            if len({sha for _, sha in docs}) > 1:
                diags.append({"kind": "input-invalid", "code": "coverage.duplicate_contract",
                              "message": f"table {tid!r} has {len(docs)} different bundle coverage contracts: "
                                         f"{[i for i, _ in docs]} (no first-wins)"})
                for iid, _ in docs:
                    items[iid]["doc"] = None
    return diags


def _is_factor_table(doc: dict) -> bool:
    return "factor_table_version" in doc or "factors" in doc


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def factor_table_shape(doc: dict) -> list[str]:
    """Shape of a factor-table calibration (check-context 1.1.0, G16): factors maps an effect to exactly one of
    values (a non-empty list of finite numbers), scalar (a finite number) or by_scope (scope -> such a list); an
    optional tolerance is {"relative": a finite number >= 0} (r-comp.factor_values 1.1.0 does not use it); optional
    significant_digits is an integer 1..17 (DR-6)."""
    out = []
    if doc.get("factor_table_version") != "1.0.0":
        out.append("factor_table_version is '1.0.0'")
    factors = doc.get("factors")
    if not isinstance(factors, dict) or not factors:
        return out + ["factors is a non-empty object"]
    finite_list = lambda v: isinstance(v, list) and bool(v) and all(_finite(x) for x in v)  # noqa: E731
    for name, entry in sorted(factors.items()):
        forms = [k for k in ("values", "scalar", "by_scope") if isinstance(entry, dict) and k in entry]
        if len(forms) != 1:
            out.append(f"factors.{name}: exactly one of values, scalar, by_scope")
        elif forms[0] == "values" and not finite_list(entry["values"]):
            out.append(f"factors.{name}.values: a non-empty list of finite numbers")
        elif forms[0] == "scalar" and not _finite(entry["scalar"]):
            out.append(f"factors.{name}.scalar: a finite number")
        elif forms[0] == "by_scope" and not (isinstance(entry["by_scope"], dict) and entry["by_scope"]
                                              and all(finite_list(v) for v in entry["by_scope"].values())):
            out.append(f"factors.{name}.by_scope: scope -> a non-empty list of finite numbers")
    if "tolerance" in doc:
        tol = doc["tolerance"]
        rel = tol.get("relative") if isinstance(tol, dict) else None
        if not (isinstance(tol, dict) and set(tol) == {"relative"} and isinstance(rel, (int, float)) and _finite(rel)
                and rel >= 0):
            out.append("tolerance is {\"relative\": a finite number >= 0}")
    if "significant_digits" in doc:
        d = doc["significant_digits"]
        if not (isinstance(d, int) and not isinstance(d, bool) and 1 <= d <= 17):
            out.append("significant_digits is an integer from 1 to 17")
    return out


def draft_view(root, items: list, context: dict, files: dict | None = None) -> dict:
    """A check view before freezing, from in-memory documents (files: ref -> content) or the files under root."""
    out = {}
    for it in items:
        doc = (files or {}).get(it["ref"])
        if doc is None and _is_json(it["ref"]):
            doc = json.loads(_read(Path(root).resolve(), it["ref"]).decode("utf-8"))
        out[it["id"]] = {"role": it["role"], "ref": it["ref"], "doc": doc if isinstance(doc, (dict, list)) else None}
    return _view(out, context)[0]


def _item(root: Path, it: dict) -> dict:
    sha, kind = item_digest(root, it["ref"])
    rec = {"role": it["role"], "id": it["id"], "ref": it["ref"], "sha256": sha, "digest_kind": kind}
    if kind == "canonical-json":
        rec["bytes_sha256"] = hashlib.sha256(_read(root, it["ref"])).hexdigest()
    return rec


def _serialized(doc: dict) -> bytes:
    return (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("utf-8")


def _generated_item(role: str, iid: str, ref: str, doc: dict) -> dict:
    return {"role": role, "id": iid, "ref": ref, "sha256": canonical_sha256(doc), "digest_kind": "canonical-json",
            "bytes_sha256": hashlib.sha256(_serialized(doc)).hexdigest()}


def _check_once(path: Path, doc: dict) -> None:
    if path.exists() and path.read_bytes() != _serialized(doc):
        raise BundleRefused("bundle.exists", f"{path.name} exists with other content: freeze never overwrites")


def _write_once(path: Path, doc: dict) -> None:
    _check_once(path, doc)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(_serialized(doc))
    tmp.replace(path)


class SnapshotInvalid(ValueError):
    """A stored snapshot whose content does not match its digest (rewritten)."""


def save_snapshots(entries: dict, store) -> None:
    """Write {digest: document} content-addressed into the store, write-once; an existing file must hold that digest."""
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    for digest, doc in sorted(entries.items()):
        path = store / f"{digest}.json"
        if path.exists():
            if canonical_sha256(json.loads(path.read_text(encoding="utf-8"))) != digest:
                raise BundleRefused("snapshot.digest", f"{path.name} holds other content than its digest")
            continue
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)


def snapshot_lookup(store):
    def lookup(digest: str):
        path = Path(store) / f"{digest}.json"
        if not path.is_file():
            return None
        doc = json.loads(path.read_text(encoding="utf-8"))
        if canonical_sha256(doc) != digest:
            raise SnapshotInvalid(f"snapshot {digest[:12]} does not match its digest")
        return doc
    return lookup


def default_snapshot_store(root) -> Path:
    return Path(root).resolve() / STATE_DIR / "snapshots"


def record_bundle(root, bundle_path, bundle: dict) -> None:
    """Add a frozen bundle to <root>/.hep-research/bundles.json, the index 'snapshots gc' keeps alive."""
    root = Path(root).resolve()
    index_path = root / STATE_DIR / "bundles.json"
    index: dict = {"index_version": "1.0.0", "bundles": []}
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    try:
        ref = Path(bundle_path).resolve().relative_to(root).as_posix()
    except ValueError:
        ref = str(Path(bundle_path).resolve())
    entry = {"path": ref, "bundle_digest": bundle.get("bundle_digest")}
    if entry not in index["bundles"]:
        index["bundles"].append(entry)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = index_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    tmp.replace(index_path)


def snapshots_gc(root, apply: bool = False) -> dict:
    """Snapshots no indexed bundle references: listed (dry run) or deleted (apply). An indexed bundle that cannot be
    read, or whose semantic lock cannot be read, refuses the whole run: nothing is deleted on a guess."""
    root = Path(root).resolve()
    store = default_snapshot_store(root)
    index_path = root / STATE_DIR / "bundles.json"
    keep: set[str] = set()
    try:
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else {"bundles": []}
        for entry in index["bundles"]:
            p = Path(entry["path"])
            bundle = json.loads((p if p.is_absolute() else root / p).read_text(encoding="utf-8"))
            lock_item = next(it for it in bundle["items"] if it["role"] == "semantic-lock")
            lock = json.loads(_read(root, lock_item["ref"]).decode("utf-8"))
            keep |= {d["digest"] for d in lock.get("definitions", []) if d.get("digest")}
            keep |= {m["closure_digest"] for m in lock.get("member_sets", []) if m.get("closure_digest")}
    except (OSError, ValueError, KeyError, TypeError, StopIteration, BundleRefused) as exc:
        return {"status": "refused", "error": f"an indexed bundle cannot be read: {exc}", "deleted": [], "unreferenced": []}
    stored = sorted(p.stem for p in store.glob("*.json")) if store.is_dir() else []
    unreferenced = [d for d in stored if d not in keep]
    if apply:
        for d in unreferenced:
            (store / f"{d}.json").unlink()
    return {"status": "deleted" if apply else "dry-run", "kept": len(stored) - len(unreferenced),
            "unreferenced": unreferenced, "deleted": unreferenced if apply else []}


def _registry_doc():
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


DEFAULT = "default"


def freeze(root, analysis: str, items: list, context: dict, mode: str = "chain", snapshots=DEFAULT) -> dict:
    """snapshots: a store folder, DEFAULT (<root>/.hep-research/snapshots/) or None (no snapshots)."""
    root = Path(root).resolve()
    if snapshots == DEFAULT:
        snapshots = default_snapshot_store(root)
    if not isinstance(items, list) or not items:
        raise BundleRefused("bundle.no_items", "a bundle needs its items")
    if mode != "chain" or any(isinstance(it, dict) and it.get("role") == "model-card" for it in items):
        raise BundleRefused("bundle.removed", f"model-only bundles and model-card items were {REMOVED}")
    if isinstance(context, dict):
        gone = sorted({str(x.get("id")) for x in context_suites(context) if isinstance(x, dict) and x.get("id") in REMOVED_SUITES})
        if gone:
            raise BundleRefused("bundle.removed", f"suites {gone} were {REMOVED}")
    for it in items:
        if not (isinstance(it, dict) and it.get("role") in ROLES2 and it.get("role") not in ("context", "semantic-lock")
                and isinstance(it.get("id"), str) and isinstance(it.get("ref"), str)):
            raise BundleRefused("bundle.bad_item", f"{it!r}: a role from {list(ROLES2)} (context and lock are generated), an id, a ref")
        if it["role"] in JSON_ROLES and not _is_json(it["ref"]):
            raise BundleRefused("bundle.bad_item", f"{it['id']}: a {it['role']} item is a .json file")
    ids, refs = [it["id"] for it in items], [it["ref"] for it in items]
    if not isinstance(context, dict):
        raise BundleRefused("bundle.context_schema", "the context is a JSON object")
    if len(set(ids)) != len(ids) or {"check-context", "semantic-lock"} & set(ids):
        raise BundleRefused("bundle.duplicate_id", "item ids are unique (and 'check-context', 'semantic-lock' are reserved)")
    if len(set(refs)) != len(refs) or {CONTEXT_REF, LOCK_REF} & set(refs):
        raise BundleRefused("bundle.duplicate_ref", "a ref is listed once (and the context and lock refs are reserved)")
    _roles_ok([it["role"] for it in items] + ["context", "semantic-lock"], mode)
    rep = validate(context, "check_context.json")
    if not rep.ok:
        raise BundleRefused("bundle.context_schema", "; ".join(f"{f.path}: {f.code}" for f in rep.errors))
    pairing = version_findings(context)
    if pairing:
        raise BundleRefused("bundle.context_version", "; ".join(f"{f['where']}: {f['message']}" for f in pairing))
    bad_input = input_findings(context)
    if bad_input:
        raise BundleRefused("bundle.context_input", "; ".join(f"{f['where']}: {f['message']}" for f in bad_input))
    try:
        view = draft_view(root, items, context)
    except (UnicodeError, ValueError) as exc:
        raise BundleRefused("bundle.bad_json", f"an item is not readable JSON: {exc}") from None
    shapes = shape_diagnostics(view["items"], context.get("context_version"))
    if shapes:
        raise BundleRefused("bundle.item_schema", "; ".join(d["message"] for d in shapes))
    roles = {it["id"]: it["role"] for it in items}
    bad = [f for f in check_context(context, roles) if f["code"] in ("context.duplicate_id", "context.unknown_reference")]
    if bad:
        raise BundleRefused("bundle.context_references", "; ".join(f"{f['where']}: {f['message']}" for f in bad))
    try:
        suites = [load_suite(s["id"], s["version"]) for s in context_suites(context)]
    except (OSError, ValueError) as exc:
        raise BundleRefused("bundle.suite_missing", f"a selected suite is not installed: {exc}") from None
    for s in suites:
        if s.get("mode", "chain") != mode:
            raise BundleRefused("bundle.suite_mode", f"suite {s.get('suite_id')!r} checks {s.get('mode')} bundles, not {mode}")
        if not obl.generator_supported(s):
            raise BundleRefused("bundle.generator_unsupported", f"suite {s.get('suite_id')!r} names generator "
                                f"{s.get('generator')!r}, which this checker does not implement")
    full = dict(context, obligations=obl.generate_all(suites, view))
    view["context"] = full
    view["suites"] = suites
    lock = build_lock(suites[0], generator_code_digest() or "", view, registry_digest())
    recs = [_item(root, it) for it in items] + [_generated_item("context", "check-context", CONTEXT_REF, full),
                                                _generated_item("semantic-lock", "semantic-lock", LOCK_REF, lock)]
    doc = {"bundle_version": "2.0.0", "format": FORMAT2, "mode": mode, "analysis": analysis,
           "items": sorted(recs, key=lambda x: (ROLES2.index(x["role"]), x["id"])), "plugin_release": dict(plugin_release())}
    doc["bundle_digest"] = canonical_sha256(doc)
    rep = validate(doc, "analysis_bundle_v2.json")
    if not rep.ok:
        raise BundleRefused("bundle.schema", "; ".join(f"{f.path}: {f.code}" for f in rep.errors))
    _check_once(root / CONTEXT_REF, full)  # every check passes before anything is written
    _check_once(root / LOCK_REF, lock)
    _write_once(root / CONTEXT_REF, full)
    _write_once(root / LOCK_REF, lock)
    if snapshots is not None:  # D11b: the pinned definitions, content-addressed, for historical reproduction
        from contracts.analysis_checks.lock import snapshot_entries
        save_snapshots(snapshot_entries(view, lock, _registry_doc()), snapshots)
    return doc


def _roles_ok(roles: list, mode: str) -> None:
    need = MODE_ROLES.get(mode)
    if mode == "model":
        raise BundleRefused("bundle.removed", f"mode 'model' was {REMOVED}")
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
        if isinstance(it.get("ref"), str) and _is_json(it["ref"]):
            try:
                rec["doc"] = json.loads(_read(root, it["ref"]).decode("utf-8"))
            except (BundleRefused, UnicodeError, ValueError):
                pass  # reported by verify as a missing or changed frozen file
        items[it["id"]] = rec
    ctx_doc: dict = next((i["doc"] for i in items.values() if i.get("role") == "context" and isinstance(i.get("doc"), dict)), {})
    diags += shape_diagnostics(items, ctx_doc.get("context_version"))
    ctx_items = [i for i in items.values() if i.get("role") == "context"]
    lock_items = [i for i in items.values() if i.get("role") == "semantic-lock"]
    context = ctx_items[0]["doc"] if ctx_items and isinstance(ctx_items[0]["doc"], dict) else {}
    lock = lock_items[0]["doc"] if lock_items and isinstance(lock_items[0]["doc"], dict) else {}
    for name, doc in (("check_context.json", context), ("semantic_lock.json", lock)):
        rep = validate(doc, name)
        for f in rep.errors:
            diags.append({"kind": "input-invalid", "code": f"{name.split('.')[0]}.{f.code}", "message": f"{f.path}: {f.message}"})
    diags += [{"kind": "input-invalid", "code": f["code"], "message": f"{f['where']}: {f['message']}"}
              for f in version_findings(context) + input_findings(context)]
    view, more = _view(items, context)
    diags += more
    view.update(bundle=bundle, lock=lock, bundle_verified=ver["status"], root=str(root))
    roles = {k: v.get("role") for k, v in items.items()}
    view["context_findings"] = check_context(context, roles) if context else []
    for f in view["context_findings"]:
        if f["code"] in ("context.duplicate_id", "context.unknown_reference"):
            diags.append({"kind": "input-invalid", "code": f["code"], "message": f"{f['where']}: {f['message']}"})
    view["suite"], view["suites"] = None, []
    for k, s in enumerate(context_suites(context) if isinstance(context, dict) else []):
        if s.get("id") in REMOVED_SUITES:
            diags.append({"kind": "dependency-missing", "code": "definition.suite_removed",
                          "message": f"suite {s.get('id')!r} was {REMOVED}"})
            continue
        try:
            loaded = load_suite(str(s.get("id")), str(s.get("version")))
        except (OSError, ValueError):
            diags.append({"kind": "dependency-missing", "code": "definition.suite_missing",
                          "message": f"suite {s.get('id')!r} version {s.get('version')!r} is not installed"})
            continue
        if not obl.generator_supported(loaded):
            diags.append({"kind": "dependency-missing", "code": "definition.generator_unsupported",
                          "message": f"suite {s.get('id')!r} names generator {loaded.get('generator')!r}, which this "
                                     "checker does not implement: its inventory is not regenerated"})
        view["suites"].append(loaded)
        if k == 0:
            view["suite"] = loaded
    return view, diags


def current_lock(view: dict) -> dict:
    return build_lock(view.get("suite") or {}, generator_code_digest() or "", view, registry_digest())


def check_inventory(view: dict) -> list[dict]:
    frozen = (view.get("context") or {}).get("obligations") or {}
    if view.get("suite") is None or len(view.get("suites") or []) != len(context_suites(view.get("context") or {})):
        return []
    if not all(obl.generator_supported(s) for s in view["suites"]):
        return []  # generator guard: reported as dependency-missing by load_subject
    return obl.check_inventory(frozen, obl.generate_all(view["suites"], view))


# --- evaluation and report (D05c) ---------------------------------------------------------------------------------
REPORT_VERSION = "1.0.0"
SUMMARY_BYTES = 8192  # the agent summary's page cap: a product default sharing D02's paging (not a measurement)


def legacy_findings(view: dict, vocab=None) -> list[dict]:
    """Old entry points' findings on the bundle's own artifacts, kept apart (C10): L1 on the spec, L2 per recipe."""
    from contracts.analysis_checks.outcomes import map_legacy
    from contracts.recipe_semantics import check_recipe
    from contracts.validate import validate_artifact
    from contracts.vocab import Vocabulary
    out = []
    spec_id = (view.get("context") or {}).get("spec")
    spec = (view["items"].get(spec_id) or {}).get("doc")
    if isinstance(spec, dict):
        for f in validate_artifact(spec, vocab or Vocabulary(), strict=True).findings:
            if f.severity in ("error", "warning"):
                out.append({"entry": "contracts/validate.py", "item": spec_id, **f.as_dict(), "maps_to": map_legacy(f.as_dict())})
    for iid, it in sorted(view["items"].items()):
        if it.get("role") == "recipe" and isinstance(it.get("doc"), dict):
            res = check_recipe(it["doc"], view.get("tables", {}), [], None)
            for f in res["findings"]:
                out.append({"entry": "contracts/recipe_semantics.py", "item": iid, **f, "maps_to": map_legacy(f)})
    return out


def evaluate(view: dict, diags: list[dict], previous: dict | None = None, vocab=None, settings: dict | None = None,
             rules: dict | None = None, snapshots=None, exceptions: list | None = None, now: str | None = None) -> dict:
    """A pre-execution assessment: result bindings (run-lineage) were removed in 0.28.0."""
    from contracts.analysis_checks.lock import compare, rebuild
    from contracts.analysis_checks.outcomes import formal_view, summarize
    from contracts.analysis_checks.rules import evaluate as run_rules

    lock_diff = compare(view.get("lock") or {}, current_lock(view)) if view.get("suite") else []
    installed_diff, source = list(lock_diff), "installed"
    missing: list[str] = []
    if lock_diff and snapshots is not None:  # D11b: reproduce the old subject from its snapshot, never from the latest
        try:
            defs, missing = rebuild(view.get("lock") or {}, snapshot_lookup(snapshots))
        except SnapshotInvalid as exc:
            defs, missing = None, []
            diags = list(diags) + [{"kind": "input-invalid", "code": "snapshot.digest", "message": str(exc)}]
        if defs is not None and not missing:
            view = dict(view, coverage=defs["coverage"], catalog=defs["catalog"], suites=defs["suites"],
                        suite=defs["suites"][0] if defs["suites"] else None)
            locked_registry = next((d["digest"] for d in (view.get("lock") or {}).get("definitions", [])
                                    if d["kind"] == "rule-registry"), None)
            lock_diff = compare(view.get("lock") or {}, build_lock(view.get("suite") or {}, generator_code_digest() or "",
                                                                   view, locked_registry))
            source = "snapshot" if not lock_diff else "installed"
    # with drifted definitions a regenerated inventory may differ for that reason alone: drift, not invalid input
    diags = list(diags) + [dict(d, kind="dependency-missing", code=d["code"] + "_under_drift") if lock_diff else
                           dict(d, kind="input-invalid") for d in check_inventory(view)]
    input_valid = not any(d["kind"] == "input-invalid" for d in diags)
    obligations = ((view.get("context") or {}).get("obligations") or {}).get("items", [])
    if input_valid:
        outcomes = run_rules(view, obligations, rules)
    else:
        outcomes = [{"obligation_id": o["obligation_id"], "rule_id": o["rule_id"], "state": "unverified",
                     "reason": "check.input_invalid", "message": "the inputs cannot be established", "evidence": [],
                     "declaration_based": False, "declarations": []} for o in obligations]
    if lock_diff and input_valid:
        outcomes = [o if o["rule_id"] == "r-inv.root" else
                    dict(o, state="unverified", reason="check.semantics_unreproducible", declaration_based=False,
                         message="the definitions differ from the semantic lock; this subject's semantics cannot be "
                                 "reproduced from the current definitions (snapshots: D11b)")
                    for o in outcomes]
    summary = summarize(outcomes, input_valid)
    bundle = view.get("bundle") or {}
    suite = view.get("suite") or {}
    rules_used = [{"rule_id": r["rule_id"], "version": r["version"]} for s in view.get("suites") or [suite] for r in s.get("rules", [])]
    checker = checker_identity()
    settings = dict(settings or {})
    inv = (view.get("context") or {}).get("obligations") or {}
    lock = view.get("lock") or {}
    assessment = {"subject": bundle.get("bundle_digest"), "suite": {"id": suite.get("suite_id"), "version": suite.get("version")},
                  "suites": [{"id": s.get("suite_id"), "version": s.get("version")} for s in view.get("suites") or []],
                  "rules": rules_used, "registry": registry_digest(), "checker": checker["digest"],
                  "readers": lock.get("readers"), "settings": settings, "plugin_release": dict(plugin_release())}
    decl_ids = {d for o in outcomes for d in o.get("declarations", [])}
    # P6: a missing dependency or definitions that differ from the lock never leave the status complete (exit 3)
    blocked = bool(lock_diff) or any(d["kind"] == "dependency-missing" for d in diags)
    report = {
        "report_version": REPORT_VERSION, "kind": "analysis-check-report",
        "status": ("invalid" if not input_valid else "inconsistent" if summary["consistency"] == "inconsistent"
                   else "complete" if summary["coverage"]["value"] == "complete" and summary["consistency"] == "consistent"
                   and not blocked else "incomplete"),
        "subject_digest": bundle.get("bundle_digest"), "assessment_id": canonical_sha256(assessment),
        "assessment": assessment, "inventory_digest": inv.get("digest"), "suite": assessment["suite"],
        "checker": checker, "input_validity": "valid" if input_valid else "invalid",
        "input_diagnostics": diags, "lock_differences": lock_diff,
        "coverage": summary["coverage"], "consistency": summary["consistency"], "counts": summary["counts"],
        "formal_use_view": formal_view(outcomes, input_valid),
        "obligations": outcomes,
        "declarations": [{"declaration_id": d.get("declaration_id"), "type": d.get("type"), "asserted_by": d.get("asserted_by")}
                         for d in (view.get("context") or {}).get("declarations", []) if d.get("declaration_id") in decl_ids],
        "context_findings": view.get("context_findings", []),
        "legacy_findings": legacy_findings(view, vocab) if view.get("items") else [],
        "execution_evidence_level": "not checked: run lineage was removed in 0.28.0 (pre-execution report)",
        "phase": "pre-execution",
        "validation_status": sorted(set(((view.get("items", {}).get((view.get("context") or {}).get("spec")) or {})
                                          .get("doc") or {}).get("status") or [])),
        "scope_delta": scope_delta(previous, bundle.get("bundle_digest"), obligations) if previous else None,
        "semantics_source": source, "installed_differences": installed_diff if source == "snapshot" else [],
        "snapshot_missing": sorted(set(missing)),
        "checker_changed": ((view.get("lock") or {}).get("generator") or {}).get("code_digest") != generator_code_digest(),
        "exceptions": judge_exceptions(exceptions or [], outcomes, now),
        "note": "software consistency of declared contracts only, not physical validity; a diagnostic that authorizes "
                "nothing (HC-05); declaration-based outcomes count for formal use only through an accepted review",
    }
    return report


L2_REPEAT_ERRORS = {"semantics.repeated_correction"}
L2_REPEAT_CONSERVATIVE = {"semantics.repeat_undetermined", "semantics.repeat_distinct_instance"}


def difference_review(view: dict, report: dict) -> dict:
    """Legacy versus new, item by item (D09): every legacy finding and every new violation gets a class; anything the
    rules below do not explain is 'unclassified', and a shadow rollout needs zero of those.

    Classes: artifact-local (an L1 finding of validate.py; the new suite does not repeat artifact-local rules),
    recipe-local (an L2 finding other than repetition: it stays with recipe_semantics.py), agrees (an L2 repetition
    finding and the new repetition outcome on the same recipe's instances say the same: violated with violated,
    undetermined with unverified), new-decides (an undetermined L2 repetition that the new suite decides as violated
    from data flow), new-only (a new violation with no legacy error on the items it rests on: a cross-artifact
    finding)."""
    insts_of: dict[str, set] = {}
    for i in (view.get("context") or {}).get("recipe_instances", []):
        insts_of.setdefault(i.get("recipe"), set()).add(i.get("instance_id"))
    rep_state: dict[str, set] = {}
    for o in report.get("obligations", []):
        if o["rule_id"] == "r-rep.repetition":
            for e in o.get("evidence", []):
                if "instance" in e:
                    rep_state.setdefault(e["instance"], set()).add(o["state"])
    rows = []
    for f in report.get("legacy_findings", []):
        code, cls = f.get("code"), "unclassified"
        if f.get("entry") == "contracts/validate.py":
            cls = "artifact-local"
        elif f.get("entry") == "contracts/recipe_semantics.py":
            states = set().union(*(rep_state.get(i, set()) for i in insts_of.get(f.get("item"), ())))
            if code in L2_REPEAT_ERRORS:
                cls = "agrees" if "violated" in states else "unclassified"
            elif code in L2_REPEAT_CONSERVATIVE:
                cls = ("agrees" if "unverified" in states else "new-decides" if "violated" in states else "unclassified")
            else:
                cls = "recipe-local"
        rows.append({"side": "legacy", "entry": f.get("entry"), "item": f.get("item"), "code": code, "class": cls})
    legacy_items = {f.get("item") for f in report.get("legacy_findings", []) if f.get("entry") == "contracts/recipe_semantics.py"
                    and f.get("code") in L2_REPEAT_ERRORS | L2_REPEAT_CONSERVATIVE}
    for o in report.get("obligations", []):
        if o["state"] != "violated":
            continue
        recipes = {r for r, insts in insts_of.items() for e in o.get("evidence", []) if e.get("instance") in insts}
        cls = "agrees" if o["rule_id"] == "r-rep.repetition" and recipes & legacy_items else "new-only"
        rows.append({"side": "new", "obligation_id": o["obligation_id"], "code": o["reason"], "class": cls})
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    return {"rows": rows, "counts": counts, "unclassified": counts.get("unclassified", 0)}


def judge_exceptions(exceptions: list, outcomes: list[dict], now: str | None = None) -> list[dict]:
    """Scoped exceptions (C10): a separate adjudication that never changes a state, a severity, coverage or
    consistency, and never authorizes use. Each binds an obligation, its finding, a rationale, a person who decided
    and an expiry; a rule the registry marks non-waivable (roots and inventory) is rejected, so is an agent."""
    import datetime
    try:
        reg = {r["rule_id"]: r for r in json.loads(REGISTRY.read_text(encoding="utf-8"))["rules"]}
    except (OSError, ValueError, KeyError):
        reg = {}
    today = now or datetime.date.today().isoformat()
    by_id = {o["obligation_id"]: o for o in outcomes}
    out = []
    for e in exceptions:
        e = dict(e) if isinstance(e, dict) else {"obligation_id": None}
        o = by_id.get(e.get("obligation_id"))
        reason = None
        if o is None:
            reason = "exception.unknown_obligation"
        elif not (reg.get(o["rule_id"]) or {}).get("waivable", False):
            reason = "exception.not_waivable"
        elif e.get("finding") != o.get("reason"):
            reason = "exception.finding_mismatch"
        elif not (isinstance(e.get("decided_by"), dict) and e["decided_by"].get("kind") == "person" and e["decided_by"].get("id")):
            reason = "exception.not_a_person"
        elif not e.get("rationale"):
            reason = "exception.no_rationale"
        elif not isinstance(e.get("expires"), str) or e["expires"] <= today:
            reason = "exception.expired"
        out.append(dict(e, status="rejected" if reason else "accepted", **({"reason": reason} if reason else {}),
                        note="an exception keeps the finding and its state; it never completes a suite or authorizes use"))
    return out


def scope_delta(previous: dict, subject: str | None, obligations: list[dict]) -> dict:
    from contracts.analysis_checks.obligations import diff
    old = [{"obligation_id": o["obligation_id"]} for o in previous.get("obligations", []) if isinstance(o, dict)]
    d = diff(old, obligations)
    return {"previous_assessment": previous.get("assessment_id"), "previous_subject": previous.get("subject_digest"),
            "new_subject": previous.get("subject_digest") != subject, "added": d["added"], "removed": d["removed"],
            "inherits": False, "note": "a new assessment never inherits completeness, acceptance or authorization"}


def exit_code(report: dict) -> int:
    """1 for a violation or invalid inputs, 3 for an incomplete check, a missing dependency or definitions that differ
    from the semantic lock, 0 when complete and consistent (2, a usage error, is decided before a report exists)."""
    if report["input_validity"] == "invalid" or report["consistency"] == "inconsistent":
        return 1
    if (any(d["kind"] == "dependency-missing" for d in report["input_diagnostics"]) or report["lock_differences"]
            or report["coverage"]["value"] != "complete"):
        return 3
    return 0


NEXT_STEPS = {
    "check.applicability_unbound": "bind the correction to instances: a spec target_scope or an instance_mapping declaration",
    "check.response_use_unbound": "add a response_used_by binding (unfolding step or prediction-side folding)",
    "check.coverage_undefined": "list the class members the operator covers in its coverage contract (reviewed)",
    "check.ambiguous_application": "give the correction an application_id (a recipe step_id)",
    "check.scope_relation_unknown": "use parseable axis:value scopes or declare the partition for the same source",
    "check.keys_incomplete": "give target_scope, variation and calibration for both applications",
    "check.root_incomplete": "bind the root's binning pointer and a scope equal to its output instance",
    "check.semantics_unreproducible": "re-freeze against the current definitions (a new subject) or restore them",
    "check.rule_not_run": "use a checker that implements this rule",
    "check.input_invalid": "fix the input diagnostics first",
}


def summary_page(report: dict, cursor: int = 0, max_bytes: int = SUMMARY_BYTES) -> dict:
    """A bounded agent summary (D17): violated and unverified obligations, missing bindings and next steps, paged
    under a byte cap; digests, codes and IDs only, never result values or controlled strings."""
    rows = [{"obligation_id": o["obligation_id"], "state": o["state"], "reason": o["reason"],
             "next": NEXT_STEPS.get(o["reason"])}
            for o in report.get("obligations", []) if o["state"] in ("violated", "unverified", "unsupported")]
    rows.sort(key=lambda r: ({"violated": 0, "unverified": 1, "unsupported": 2}[r["state"]], r["obligation_id"]))
    head = {"status": report.get("status"), "assessment_id": report.get("assessment_id"),
            "subject_digest": report.get("subject_digest"), "input_validity": report.get("input_validity"),
            "coverage": report.get("coverage"), "consistency": report.get("consistency"),
            "missing_bindings": sorted({r["reason"] for r in rows if r["reason"] in NEXT_STEPS and r["state"] == "unverified"}),
            "total_rows": len(rows), "offset": cursor}
    page: list[dict] = []
    for r in rows[cursor:]:
        trial = dict(head, rows=page + [r], next_cursor=cursor + len(page) + 1)
        if len(json.dumps(trial, indent=1).encode()) > max_bytes and page:
            break
        page.append(r)
    nxt = cursor + len(page)
    return dict(head, rows=page, next_cursor=nxt if nxt < len(rows) else None,
                limits={"max_bytes": max_bytes, "note": "a product default sharing the evidence query's paging, not a measurement"})


def _vocab(project):
    if project is None:
        return None
    from contracts.project import load_project
    from contracts.vocab import Vocabulary
    proj = load_project(Path(project))
    if not proj.report.ok:
        raise UsageError("invalid project config: " + "; ".join(f.code for f in proj.report.errors))
    return Vocabulary.with_profiles(proj.profiles)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--root", type=Path, required=True)
    f.add_argument("--analysis", required=True)
    f.add_argument("--items", type=Path, required=True)
    f.add_argument("--context", type=Path, required=True)
    f.add_argument("--out", type=Path, required=True)
    f.add_argument("--snapshots", type=Path, help="store the pinned definitions content-addressed here (D11b; default "
                   "<root>/.hep-research/snapshots)")
    f.add_argument("--no-snapshots", action="store_true", help="store no snapshots")
    f.add_argument("--mode", default="chain", help=argparse.SUPPRESS)  # 'model' was removed in 0.28.0: refused with the reason
    c = sub.add_parser("check")
    c.add_argument("bundle", type=Path)
    c.add_argument("--root", type=Path, required=True)
    c.add_argument("--out", type=Path)
    c.add_argument("--previous", type=Path)
    c.add_argument("--profiles-from", type=Path, help="project config whose profiles extend the vocabulary of the legacy L1 run")
    c.add_argument("--snapshots", type=Path, help="snapshot store: reproduce a subject whose definitions changed since "
                   "freezing (default <root>/.hep-research/snapshots when it exists)")
    c.add_argument("--exceptions", type=Path, help="scoped exceptions (JSON list): judged and listed, never change a state")
    c.add_argument("--results", type=Path, help=argparse.SUPPRESS)  # removed in 0.28.0: refused with the reason
    c.add_argument("--project", type=Path, help=argparse.SUPPRESS)  # removed in 0.28.0: refused with the reason
    s = sub.add_parser("summary")
    s.add_argument("report", type=Path)
    s.add_argument("--cursor", type=int, default=0)
    s.add_argument("--max-bytes", type=int, default=SUMMARY_BYTES)
    g = sub.add_parser("snapshots")
    g.add_argument("action", choices=["gc"])
    g.add_argument("--root", type=Path, required=True)
    g.add_argument("--apply", action="store_true", help="delete (default: dry run, list only)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        if args.cmd == "freeze":
            items = json.loads(args.items.read_text(encoding="utf-8"))
            context = json.loads(args.context.read_text(encoding="utf-8"))
            if args.out.exists():
                raise UsageError(f"{args.out} exists: a bundle is written once")
            if args.out.resolve() in {(args.root / r).resolve() for r in (CONTEXT_REF, LOCK_REF)}:
                raise UsageError(f"{args.out} is where freeze writes the context or lock")
            if not args.out.parent.is_dir():
                raise UsageError(f"{args.out.parent} is not a directory")
            if args.no_snapshots and args.snapshots is not None:
                raise UsageError("--snapshots and --no-snapshots exclude each other")
            store = None if args.no_snapshots else (args.snapshots or DEFAULT)
            try:
                doc = freeze(args.root, args.analysis, items, context, mode=args.mode, snapshots=store)
            except BundleRefused as exc:
                print(json.dumps({"status": "refused", "code": exc.code, "error": str(exc)}, indent=1))
                return 1
            args.out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
            record_bundle(args.root, args.out, doc)
            print(json.dumps({"status": "frozen", "bundle_digest": doc["bundle_digest"], "out": str(args.out)}, indent=1))
            return 0
        if args.cmd == "snapshots":
            if not args.root.is_dir():
                raise UsageError(f"{args.root} is not a directory")
            res = snapshots_gc(args.root, apply=args.apply)
            print(json.dumps(res, indent=1))
            return 1 if res["status"] == "refused" else 0
        if args.cmd == "summary":
            report = json.loads(args.report.read_text(encoding="utf-8"))
            if not (isinstance(report, dict) and isinstance(report.get("obligations"), list)):
                raise UsageError(f"{args.report} is not an analysis-check report")
            if args.cursor < 0 or args.max_bytes < 1024:
                raise UsageError("--cursor is >= 0 and --max-bytes >= 1024")
            print(json.dumps(summary_page(report, args.cursor, args.max_bytes), indent=1))
            return 0
        previous = json.loads(args.previous.read_text(encoding="utf-8")) if args.previous else None
        if previous is not None and not (isinstance(previous, dict) and isinstance(previous.get("obligations"), list)):
            raise UsageError(f"{args.previous} is not an analysis-check report")
        vocab = _vocab(args.profiles_from)
        exceptions = json.loads(args.exceptions.read_text(encoding="utf-8")) if args.exceptions else None
        if exceptions is not None and not isinstance(exceptions, list):
            raise UsageError(f"{args.exceptions} is not a JSON list of exceptions")
        if args.results is not None or args.project is not None:
            raise UsageError(f"--results and --project (result bindings, run lineage) were {REMOVED}")
        view, diags = load_subject(args.bundle, args.root)
        if args.out is not None:
            refs = {(Path(args.root).resolve() / it.get("ref", "")).resolve() for it in view["bundle"].get("items", [])
                    if isinstance(it, dict)}
            if args.out.resolve() in refs or args.out.resolve() == Path(args.bundle).resolve():
                raise UsageError("a report is never written into the bundle it examines")
            if args.out.exists():
                raise UsageError(f"{args.out} exists: reports are never overwritten")
            if not args.out.parent.is_dir():
                raise UsageError(f"{args.out.parent} is not a directory")
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "usage", "error": str(exc)}, indent=1))
        return 2
    store = args.snapshots
    if store is None and default_snapshot_store(args.root).is_dir():
        store = default_snapshot_store(args.root)
    report = evaluate(view, diags, previous, vocab, snapshots=store, exceptions=exceptions)
    if args.out is not None:
        args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
