"""Read-only recipe instance views (v6.3 C2): one recipe template, many instances.

build_view combines a recipe template with one context instance. Per step it keeps the operator and the order of the
template, takes the effects the operator applies from the semantics table, and gives each effect its correction key
(target_scope, variation_id, calibration_digest, stage) with a source pointer per field. The instance fills only what
the template leaves unspecified and the reader lists as fillable: target_scope and variation_id from the instance,
calibration_digest from a calibration item the instance binds (by that item's digest). A literal in the template that
disagrees is never overridden (instance.override_rejected); operators, step order and calibration content are never
replaced. The view records the adapter that read the template; the recipe file itself is never upgraded."""
from __future__ import annotations

from contracts.analysis_checks.scope import canonical_scope
from contracts.release_manifest import canonical_sha256

FILLABLE = ("target_scope", "variation_id")
KEY_FIELDS = ("target_scope", "variation_id", "calibration_digest", "stage")
ADAPTERS = {"1.0.0": "recipe-1.0.0-view", "1.1.0": "recipe-1.1.0-view"}


def _same(a, b, axes) -> bool:
    if axes:
        ca, cb = canonical_scope(a, axes), canonical_scope(b, axes)
        if ca is not None and cb is not None:
            return ca == cb
    return a == b


def build_view(recipe: dict, recipe_item: str, table: dict, instance: dict, pointer: str, digests: dict,
               axes: dict | None = None) -> dict:
    ops = {o["operator_id"]: o for o in table.get("operators", [])}
    findings: list[dict] = []
    fill = {"target_scope": instance.get("scope"), "variation_id": instance.get("variation")}
    cals = instance.get("calibrations") or {}
    steps = []
    for i, step in enumerate(recipe.get("steps", [])):
        op = ops.get(step.get("operator"))
        if op is None:
            findings.append({"code": "instance.unknown_operator", "where": f"recipe:/steps/{i}/operator",
                             "message": f"operator {step.get('operator')!r} is not in table {table.get('table_id')!r}"})
        literal_keys = step.get("effect_keys") or {}
        effects = {}
        for effect in (op or {}).get("applies", []):
            lit = literal_keys.get(effect) or {}
            key = {}
            for f in KEY_FIELDS:
                src = f"recipe:/steps/{i}/effect_keys/{effect}/{f}"
                if f in lit:
                    key[f] = {"value": lit[f], "source": src}
                    if f in FILLABLE and fill[f] is not None and not _same(lit[f], fill[f], axes or {}):
                        findings.append({"code": "instance.override_rejected", "where": src,
                                         "message": f"the template says {f}={lit[f]!r}; the instance's {fill[f]!r} "
                                                    "cannot override it"})
                elif f in FILLABLE and fill[f] is not None:
                    key[f] = {"value": fill[f], "source": f"context:{pointer}/{'scope' if f == 'target_scope' else 'variation'}"}
                elif f == "calibration_digest" and effect in cals:
                    item = cals[effect]
                    key[f] = {"value": digests.get(item), "source": f"context:{pointer}/calibrations/{effect}"}
                    if item not in digests:
                        findings.append({"code": "instance.unknown_calibration", "where": key[f]["source"],
                                         "message": f"calibration item {item!r} is not in the bundle"})
                else:
                    key[f] = {"value": None, "source": None}
            effects[effect] = key
        steps.append({"step_id": step.get("step_id"), "index": i, "operator": step.get("operator"), "effects": effects})
    view = {"instance_id": instance.get("instance_id"), "recipe": recipe_item,
            "adapter": ADAPTERS.get(str(recipe.get("recipe_version")), "unsupported"), "steps": steps,
            "not_applied": sorted(str(n.get("effect_id")) for n in recipe.get("not_applied", []) if isinstance(n, dict)),
            "findings": findings}
    if view["adapter"] == "unsupported":
        findings.append({"code": "instance.unsupported_recipe_version", "where": "recipe:/recipe_version",
                         "message": f"no reader for recipe_version {recipe.get('recipe_version')!r}"})
    view["view_digest"] = canonical_sha256({k: v for k, v in view.items() if k != "findings"})
    return view
