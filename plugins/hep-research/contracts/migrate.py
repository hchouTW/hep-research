#!/usr/bin/env python3
"""Migration dispatcher (v6.3 D11b, C14): convert items of a frozen v2 bundle and rebuild it leaf to root into a new
folder, never touching the original.

migrate(src_root, bundle, dst_root, plan): the source bundle must verify identical. Every non-generated item is
copied to dst_root at its own ref; each planned item is converted (leaf) by a listed lossless converter; then the
check context is regenerated (references are item IDs, so they stay consistent), the semantic lock recorded and the
bundle frozen again (root). Only when the new bundle verifies identical and loads without input diagnostics is
MIGRATION-COMPLETE.json written, with the lineage of every conversion. On any failure the result is 'refused' with its
diagnostics, no completion marker is written, and the original files are unchanged. A conversion that needs missing
physics or scope information is not a converter: it goes to manual completion; changing the mathematical model is a
new analysis.

Converters: recipe-1.0.0-to-1.1.0 (1.1.0 only adds optional correction keys: lossless); context-1.0.0-to-1.1.0
(item check-context, V90): the check context in format 1.1.0. A root or ratio root with required: false is a deferral,
which 1.1.0 records only as an exception (DR-2), so such a context is refused and goes to manual completion;
required: true is dropped; each suite moves to the newest installed version at or above 1.1.0 (a pre-release while
R2 is in development: an older pre-release names rule versions the checker no longer runs). The suites chosen are part
of the lineage.

Usage: python3 contracts/migrate.py SRC_ROOT BUNDLE DST_ROOT --convert ITEM=CONVERTER [--convert ...]
Exit 0 complete, 1 refused, 2 bad usage. Output: JSON with a status key.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import analysis_check as ac  # noqa: E402
from contracts.analysis_bundle import BundleRefused  # noqa: E402
from contracts.schema import validate  # noqa: E402

MARKER = "MIGRATION-COMPLETE.json"


def recipe_1_0_to_1_1(doc: dict) -> dict:
    if doc.get("recipe_version") != "1.0.0":
        raise ValueError("recipe-1.0.0-to-1.1.0 reads a 1.0.0 recipe")
    return dict(copy.deepcopy(doc), recipe_version="1.1.0")


def _latest_1_1_suite(suite_id: str) -> str:
    from contracts.analysis_checks.context import FIRST_1_1_SUITE
    from contracts.semver import precedence
    found = []
    for p in ac.SUITE_DIR.glob(f"{suite_id}-*.json"):
        try:
            if precedence(p.stem[len(suite_id) + 1:]) >= precedence(FIRST_1_1_SUITE):
                found.append(p.stem[len(suite_id) + 1:])
        except ValueError:
            continue
    if not found:
        raise ValueError(f"no installed suite {suite_id} at or above 1.1.0")
    return max(found, key=precedence)  # the newest: an older pre-release names rule versions this checker no longer runs


def context_1_0_to_1_1(doc: dict) -> dict:
    if doc.get("context_version") != "1.0.0":
        raise ValueError("context-1.0.0-to-1.1.0 reads a 1.0.0 check context")
    out = copy.deepcopy(doc)
    for key in ("roots", "ratio_roots"):
        for r in out.get(key) or []:
            if r.get("required") is False:
                raise ValueError(f"{key} {r.get('root_id')!r} is deferred (required: false); check-context 1.1.0 records a "
                                 "deferral only as an exception (DR-2): complete this conversion by hand")
            r.pop("required", None)
    out["context_version"] = "1.1.0"
    out["suite"] = dict(out["suite"], version=_latest_1_1_suite(out["suite"]["id"]))
    if "suites" in out:
        out["suites"] = [dict(s, version=_latest_1_1_suite(s["id"])) for s in out["suites"]]
    return out


CONVERTERS = {"recipe-1.0.0-to-1.1.0": recipe_1_0_to_1_1, "context-1.0.0-to-1.1.0": context_1_0_to_1_1}
CONTEXT_CONVERTERS = ("context-1.0.0-to-1.1.0",)
SCHEMAS = {"recipe": "recipe.json"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _legacy_errors(doc: dict, tables: dict) -> set:
    from contracts.recipe_semantics import check_recipe
    return {f["code"] for f in check_recipe(doc, tables, [], None)["findings"] if f["severity"] == "error"}


def migrate(src_root, bundle_path, dst_root, plan: list, converters: dict | None = None) -> dict:
    convs = dict(CONVERTERS, **(converters or {}))
    src, dst = Path(src_root).resolve(), Path(dst_root).resolve()
    diags: list[dict] = []

    def refused(code: str, message: str) -> dict:
        diags.append({"code": code, "message": message})
        return {"status": "refused", "diagnostics": diags, "marker": None, "bundle": None}
    try:
        bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return refused("migrate.unreadable", str(exc))
    if ac.verify(bundle, src)["status"] != "identical":
        return refused("migrate.source_changed", "the source bundle does not verify identical")
    if dst.exists() and any(dst.iterdir()):
        return refused("migrate.destination_not_empty", f"{dst} exists and is not empty")
    items = {it["id"]: it for it in bundle["items"]}
    for step in plan:
        if step.get("item") not in items or step.get("converter") not in convs:
            return refused("migrate.bad_plan", f"{step!r}: an item of the bundle and a listed converter")
        if (items[step["item"]]["role"] == "context") != (step["converter"] in CONTEXT_CONVERTERS):
            return refused("migrate.bad_plan", f"{step!r}: a context converter converts the check context, and only it")
    generated = ("context", "semantic-lock")
    keep = [{"role": it["role"], "id": it["id"], "ref": it["ref"]} for it in bundle["items"] if it["role"] not in generated]
    context = json.loads((src / next(it["ref"] for it in bundle["items"] if it["role"] == "context")).read_text(encoding="utf-8"))
    context.pop("obligations", None)
    dst.mkdir(parents=True, exist_ok=True)
    for it in keep:
        target = dst / it["ref"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src / it["ref"], target)
    tables = {}
    for it in keep:
        if it["role"] == "semantics-table":
            doc = json.loads((dst / it["ref"]).read_text(encoding="utf-8"))
            tables[doc.get("table_id")] = doc
    lineage = []
    for step in plan:
        it = items[step["item"]]
        if it["role"] == "context":
            try:
                converted = convs[step["converter"]](context)
            except (ValueError, KeyError, TypeError) as exc:
                return refused("migrate.converter_failed", f"{step['item']}: {exc}")
            lineage.append({"item": step["item"], "converter": step["converter"],
                            "from_sha256": ac.canonical_sha256(context), "to_sha256": ac.canonical_sha256(converted),
                            "suites": ac.context_suites(converted)})
            context = converted
            continue
        path = dst / it["ref"]
        before = json.loads(path.read_text(encoding="utf-8"))
        try:
            after = convs[step["converter"]](before)
        except (ValueError, KeyError, TypeError) as exc:
            return refused("migrate.converter_failed", f"{step['item']}: {exc}")
        schema = SCHEMAS.get(it["role"])
        if schema and not validate(after, schema).ok:
            return refused("migrate.converted_invalid", f"{step['item']}: the converted document fails {schema}")
        if it["role"] == "recipe" and _legacy_errors(after, tables) - _legacy_errors(before, tables):
            return refused("migrate.converted_invalid", f"{step['item']}: the conversion adds recipe-semantics errors")
        path.write_text(json.dumps(after, indent=1) + "\n", encoding="utf-8")
        lineage.append({"item": step["item"], "converter": step["converter"], "from_sha256": it.get("bytes_sha256") or it["sha256"],
                        "to_sha256": _sha(path)})
    try:
        new = ac.freeze(dst, bundle["analysis"], keep, context, bundle.get("mode", "chain"))
    except BundleRefused as exc:
        return refused("migrate.freeze_refused", str(exc))
    out = dst / "bundle.json"
    out.write_text(json.dumps(new, indent=1) + "\n", encoding="utf-8")
    if ac.verify(new, dst)["status"] != "identical":
        return refused("migrate.verify_failed", "the migrated bundle does not verify")
    _, more = ac.load_subject(out, dst)
    bad = [d for d in more if d["kind"] == "input-invalid"]
    if bad:
        return refused("migrate.load_failed", "; ".join(d["code"] for d in bad))
    marker = {"migration_version": "1.0.0", "from_bundle": bundle["bundle_digest"], "to_bundle": new["bundle_digest"],
              "conversions": lineage, "completed": True,
              "note": "a migrated analysis is a new subject: no assessment, acceptance or permit carries over"}
    (dst / MARKER).write_text(json.dumps(marker, indent=1) + "\n", encoding="utf-8")
    return {"status": "complete", "diagnostics": diags, "marker": str(dst / MARKER), "bundle": str(out)}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("src_root", type=Path)
    ap.add_argument("bundle", type=Path)
    ap.add_argument("dst_root", type=Path)
    ap.add_argument("--convert", action="append", default=[], help="ITEM=CONVERTER")
    try:
        args = ap.parse_args(argv)
        plan = [dict(zip(("item", "converter"), c.split("=", 1))) for c in args.convert]
        if not plan or any(len(p) != 2 for p in plan):
            raise ValueError("give at least one --convert ITEM=CONVERTER")
    except SystemExit as exc:
        return 2 if exc.code else 0
    except ValueError as exc:
        print(json.dumps({"status": "usage", "error": str(exc)}))
        return 2
    res = migrate(args.src_root, args.bundle, args.dst_root, plan)
    print(json.dumps(res, indent=1))
    return 0 if res["status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
