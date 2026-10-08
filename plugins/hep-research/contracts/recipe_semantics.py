#!/usr/bin/env python3
"""Operator semantics for bounded recipes (AGENTIC-R5 T4.6, F04, P05): check a recipe (contracts/schemas/recipe.json)
against the operator-semantics table it is bound to (contracts/schemas/operator_semantics.json).

Usage: python3 contracts/recipe_semantics.py RECIPE [RECIPE ...] [--table FILE ...] [--upstream ARTIFACT ...]
  RECIPE       recipe files; each names its table by table_id and canonical-JSON SHA-256
  --table      operator-semantics tables; none given means every file in contracts/semantics/tables/
  --upstream   contract artifacts the recipe's input comes from: every effect they record as applied
               (extension.observable.included_corrections, extension.corrections[].effect_id) joins the input's
               applied_effects; a name the table does not define is an error (a repeat cannot be excluded), as is an
               artifact with no such record, or an input effect no upstream artifact records. Without --upstream the
               input's applied_effects are the recipe's own claim (warning semantics.input_effects_unverified)

Checks: the table is consistent (unique ids; every kind and effect an operator or estimand uses is declared); the
recipe's digest matches the table; every step's operator is in the table; quantity kinds chain from the input kind
through every step to the estimand kind (units follow the kinds); each step's required effects are already applied
and none of its forbidden ones are (ordering); no effect is applied twice, counting upstream artifacts (a repeated
correction across steps, P05); the result carries every effect the table requires for the estimand; every other effect of the table is applied or
listed in not_applied with a reason; a step's tool, if named, has a passing tool contract whose operation lists the
operator (contracts/tool_contracts/).
Output: JSON {"status": "pass"|"fail", "recipes": [{"recipe_id", "status", "applied_effects", "findings"}], "note"}.
Exit 0 pass, 1 fail, 2 unreadable input. Passing shows the recipe is consistent with the table; the table's physics and
the recipe's use still need scientific review by scope (HC-12, C15).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.schema import Report, validate  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PLUGIN_ROOT / "contracts" / "semantics" / "tables"
CONTRACT_DIR = PLUGIN_ROOT / "contracts" / "tool_contracts"
NOTE = "consistency with the operator-semantics table only; the table and each use need scientific review by scope (HC-12)"


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def check_table(table) -> Report:
    rep = validate(table, "operator_semantics.json")
    if not rep.ok:
        return rep
    kinds = [q["kind"] for q in table["quantities"]]
    effects = [e["effect_id"] for e in table["effects"]]
    ops = [o["operator_id"] for o in table["operators"]]
    for name, ids in (("quantities", kinds), ("effects", effects), ("operators", ops),
                      ("estimands", [e["kind"] for e in table["estimands"]])):
        for dup in sorted({x for x in ids if ids.count(x) > 1}):
            rep.add("error", name, "semantics.duplicate_id", f"'{dup}' is declared twice")
    for o in table["operators"]:
        where = f"operators.{o['operator_id']}"
        for k in (o["input_kind"], o["output_kind"]):
            if k not in kinds:
                rep.add("error", where, "semantics.undeclared_kind", f"kind '{k}' is not a declared quantity")
        for field in ("applies", "requires", "forbids_after"):
            for e in o[field]:
                if e not in effects:
                    rep.add("error", f"{where}.{field}", "semantics.undeclared_effect", f"effect '{e}' is not declared")
        if set(o["applies"]) & set(o["requires"]):
            rep.add("error", where, "semantics.self_contradiction", "an operator cannot require an effect it applies")
    for e in table["estimands"]:
        if e["kind"] not in kinds:
            rep.add("error", f"estimands.{e['kind']}", "semantics.undeclared_kind", "the estimand kind is not a declared quantity")
        for x in e["required_effects"]:
            if x not in effects:
                rep.add("error", f"estimands.{e['kind']}", "semantics.undeclared_effect", f"effect '{x}' is not declared")
    return rep


def upstream_effects(artifact) -> list[str] | None:
    """Effects an upstream contract artifact records as applied; None when it has no such record at all."""
    ext = artifact.get("extension") if isinstance(artifact, dict) else None
    if not isinstance(ext, dict):
        return None
    out, recorded = [], False
    obs = ext.get("observable")
    if isinstance(obs, dict) and isinstance(obs.get("included_corrections"), list):
        recorded = True
        out += [str(x) for x in obs["included_corrections"]]
    if isinstance(ext.get("corrections"), list):
        recorded = True
        # an entry of the wrong shape is kept as text: it maps to a table effect or fails as unmapped, never vanishes
        out += [str(c.get("effect_id") if isinstance(c, dict) else c) for c in ext["corrections"]]
    return out if recorded else None


def _tool_ops(contracts) -> dict[str, list[str]]:
    """Operators per <tool>:<operation>, from contracts that pass their own check (without running the tool)."""
    from contracts.tool_contract import check as check_contract
    ops = {}
    for c in contracts:
        if isinstance(c, dict) and check_contract(c, help_check=False)["status"] == "pass":
            for o in c["operations"]:
                if isinstance(o, dict):
                    ops[f"{c.get('tool_id')}:{o.get('operation_id')}"] = list(o.get("operators") or [])
    return ops


def check_recipe(recipe, tables: dict[str, dict], upstream: list | None = None, contracts: list | None = None) -> dict:
    """tables: table_id -> table. upstream: upstream artifacts. contracts: tool contracts (for steps naming a tool)."""
    rep = validate(recipe, "recipe.json")
    applied: list[str] = []
    if rep.ok:
        table = tables.get(recipe["semantics"]["table_id"])
        if table is None:
            rep.add("error", "semantics.table_id", "semantics.table_missing", "no such operator-semantics table")
        elif not check_table(table).ok:
            rep.add("error", "semantics.table_id", "semantics.table_invalid", "the operator-semantics table does not pass its own check")
        elif canonical_sha256(table) != recipe["semantics"]["sha256"]:
            rep.add("error", "semantics.sha256", "semantics.table_changed", "the table differs from the one the recipe is bound to")
        else:
            applied = _walk(recipe, table, upstream or [], contracts, rep)
    rid = recipe.get("recipe_id") if isinstance(recipe, dict) else None
    return {"recipe_id": rid, "status": "pass" if rep.ok else "fail", "applied_effects": applied,
            "findings": [f.as_dict() for f in rep.findings]}


def _walk(recipe: dict, table: dict, upstream: list, contracts: list | None, rep: Report) -> list[str]:
    effects = {e["effect_id"] for e in table["effects"]}
    ops = {o["operator_id"]: o for o in table["operators"]}
    tool_ops = _tool_ops(contracts if contracts is not None else _load_dir(CONTRACT_DIR))
    applied: list[str] = []

    def apply(effect: str, where: str) -> None:
        if effect in applied:
            rep.add("error", where, "semantics.repeated_correction", f"'{effect}' is already applied")
        else:
            applied.append(effect)

    for e in recipe["input"]["applied_effects"]:
        if e not in effects:
            rep.add("error", "input.applied_effects", "semantics.undeclared_effect", f"effect '{e}' is not in the table")
        apply(e, "input.applied_effects")
    recorded: set[str] = set()
    for i, art in enumerate(upstream):
        found = upstream_effects(art)
        if found is None:
            rep.add("error", f"upstream[{i}]", "semantics.upstream_unrecorded",
                    "the artifact records no applied effects: a repeated correction cannot be excluded")
            continue
        recorded |= set(found)
        for e in found:
            if e not in effects:
                rep.add("error", f"upstream[{i}]", "semantics.upstream_unmapped",
                        f"upstream effect '{e}' is not in the table: a repeated correction cannot be excluded")
            elif e not in applied:
                applied.append(e)
            # an upstream effect also listed in the recipe's input is the same application, not a repeat
    claimed = recipe["input"]["applied_effects"]
    if claimed and not upstream:
        rep.add("warning", "input.applied_effects", "semantics.input_effects_unverified",
                "no upstream artifact given: the effects claimed as already applied are not corroborated")
    elif upstream:
        for e in sorted(set(claimed) - recorded):
            rep.add("error", "input.applied_effects", "semantics.input_effects_uncorroborated",
                    f"'{e}' is claimed as applied upstream but no upstream artifact records it")
    kind = recipe["input"]["kind"]
    ids = [s["step_id"] for s in recipe["steps"]]
    for dup in sorted({x for x in ids if ids.count(x) > 1}):
        rep.add("error", "steps", "semantics.duplicate_id", f"step '{dup}' is declared twice")
    for s in recipe["steps"]:
        where = f"steps.{s['step_id']}"
        op = ops.get(s["operator"])
        if op is None:
            rep.add("error", where, "semantics.unknown_operator", f"'{s['operator']}' is not in the table")
            kind = None
            continue
        if kind is not None and op["input_kind"] != kind:
            rep.add("error", where, "semantics.kind_mismatch", f"'{s['operator']}' takes {op['input_kind']}, the previous step gives {kind}")
        for e in op["requires"]:
            if e not in applied:
                rep.add("error", where, "semantics.order", f"'{s['operator']}' needs '{e}' applied first")
        for e in op["forbids_after"]:
            if e in applied:
                rep.add("error", where, "semantics.order", f"'{s['operator']}' is defined only before '{e}'")
        for e in op["applies"]:
            apply(e, where)
        if "tool" in s and s["operator"] not in tool_ops.get(s["tool"], []):
            rep.add("error", where, "semantics.tool_uncontracted",
                    f"no tool contract {s['tool']} lists the operator '{s['operator']}'")
        kind = op["output_kind"]
    if kind is not None and kind != recipe["estimand_kind"]:
        rep.add("error", "estimand_kind", "semantics.kind_mismatch", f"the recipe ends in {kind}, not {recipe['estimand_kind']}")
    skipped = [n["effect_id"] for n in recipe["not_applied"]]
    for e in sorted({x for x in skipped if skipped.count(x) > 1} | (set(skipped) - effects)):
        rep.add("error", "not_applied", "semantics.not_applied_invalid", f"'{e}' is listed twice or not in the table")
    for e in sorted(set(skipped) & set(applied)):
        rep.add("error", "not_applied", "semantics.not_applied_invalid", f"'{e}' is listed as not applied but is applied")
    for e in sorted(effects - set(applied) - set(skipped)):
        rep.add("error", "not_applied", "semantics.omission_undeclared", f"'{e}' is neither applied nor declared not applied")
    est = next((e for e in table["estimands"] if e["kind"] == recipe["estimand_kind"]), None)
    if est is None:
        rep.add("error", "estimand_kind", "semantics.unknown_estimand", "the table defines no such estimand")
    else:
        for e in est["required_effects"]:
            if e not in applied:
                rep.add("error", "estimand_kind", "semantics.incomplete", f"the result lacks '{e}'")
    return applied


def _load_dir(path: Path) -> list:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(path.glob("*.json"))]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("recipes", nargs="+", type=Path)
    ap.add_argument("--table", action="append", type=Path, default=[])
    ap.add_argument("--upstream", action="append", type=Path, default=[])
    args = ap.parse_args(argv)
    try:
        recipes = [json.loads(p.read_text(encoding="utf-8")) for p in args.recipes]
        table_docs = ([json.loads(p.read_text(encoding="utf-8")) for p in args.table] if args.table
                      else _load_dir(TABLE_DIR))
        upstream = [json.loads(p.read_text(encoding="utf-8")) for p in args.upstream]
        contracts = _load_dir(CONTRACT_DIR)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    tables, rows = {}, []
    for k, t in enumerate(table_docs):
        tid = t.get("table_id") if isinstance(t, dict) else None
        if not isinstance(tid, str) or tid in tables:
            print(json.dumps({"status": "unreadable", "error": f"table {k}: no table_id, or one given twice"}))
            return 2
        tables[tid] = t
    for r in recipes:
        rows.append(check_recipe(r, tables, upstream, contracts))
    ok = all(r["status"] == "pass" for r in rows)
    print(json.dumps({"status": "pass" if ok else "fail", "recipes": rows, "note": NOTE}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
