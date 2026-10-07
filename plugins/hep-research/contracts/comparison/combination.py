"""Combination planning (AC15): may several measurements of one observable be combined, and how?

plan_combination(datasets, correlations=(), profiles=()) -> {"combinable", "treatment", "problems", "notes", "cross_blocks"}
  datasets: [{"id": "<ns>:<local>", "observable": {...}, "covariance": "present"|"absent"|"partial",
              "auxiliary": ["<ns>:<aux id>", ...], "uncertainties": [{"name", "kind", "correlation"}, ...]}]
  correlations: [{"between": [dataset_a, dataset_b], "source": "<aux id or effect>", "evidence_ids": [...]}
                 or {..., "assumption": {"justification", "scope"}}]; an explicit independence statement is
                 {"between": [a, b], "independent": true, "assumption": {...}} and also needs a justification.

Rules: observables must pass the comparison gate pairwise with no transformation; a missing or partial covariance
stays missing (no diagonal is assumed); a shared auxiliary measurement needs a declared correlation, otherwise the
only treatments are a joint fit with that measurement modeled once, or a comparison without combination (likelihoods
are never multiplied silently); every cross-dataset block needs evidence or a scoped assumption, including
independence; non-Gaussian uncertainty objects (scale envelopes, model alternatives, truncation) never enter a
Gaussian covariance.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

from contracts.comparison.composition import compose
from contracts.comparison.gate import NON_GAUSSIAN, gate


def _supported(c: dict) -> bool:
    a = c.get("assumption") or {}
    return bool(c.get("evidence_ids")) or bool(a.get("justification") and a.get("scope"))


def plan_combination(datasets, correlations=(), profiles=()) -> dict:
    problems, notes, blocks = [], [], {}
    if len(datasets) < 2:
        problems.append({"code": "combine.too_few", "message": "a combination needs at least two datasets"})
    ids = [d["id"] for d in datasets]
    comp = compose(list(profiles), [], ids + [a for d in datasets for a in d.get("auxiliary", [])]) if profiles else None
    if comp:
        problems += [{"code": e["code"], "message": e["message"]} for e in comp["errors"]]
        notes += comp["notes"]

    for a, b in combinations(datasets, 2):
        g = gate({"observable": a["observable"], "parameter_point": {}, "allowed_transformations": None, "status": []},
                 {"observable": b["observable"], "status": [], "corrections": []}, [], [], {})
        for m in g["mismatches"]:
            problems.append({"code": "combine.not_same_observable", "message": f"{a['id']} vs {b['id']}: {m['field']}: {m['reason']}"})

    for d in datasets:
        if d.get("covariance") in ("absent", "partial", None):
            problems.append({"code": "combine.covariance_missing",
                             "message": f"{d['id']}: covariance is {d.get('covariance') or 'not stated'}; it stays missing and no diagonal "
                                        "is assumed. Obtain the covariance, or compare without combining"})
        for u in d.get("uncertainties", []):
            if u.get("kind") in NON_GAUSSIAN:
                problems.append({"code": "combine.non_gaussian_component",
                                 "message": f"{d['id']}: '{u.get('name')}' is a {u['kind']}; it is not put into a Gaussian covariance "
                                            "without a hep-theory prescription"})

    declared: dict[tuple[Any, ...], list[Any]] = {}
    for c in correlations:
        pair = tuple(sorted(c.get("between", [])))
        if len(pair) != 2 or any(p not in ids for p in pair):
            problems.append({"code": "combine.correlation_unknown_dataset", "message": f"correlation {c.get('between')} names an unknown dataset"})
            continue
        if not _supported(c):
            problems.append({"code": "combine.correlation_unsupported",
                             "message": f"{list(pair)}: {'independence' if c.get('independent') else 'correlation'} needs evidence ids "
                                        "or an assumption with justification and scope"})
            continue
        declared.setdefault(pair, []).append(c)

    for a, b in combinations(datasets, 2):
        pair = tuple(sorted((a["id"], b["id"])))
        shared = sorted(set(a.get("auxiliary", [])) & set(b.get("auxiliary", [])))
        decl = declared.get(pair, [])
        covered = {c.get("source") for c in decl if not c.get("independent")}
        for aux in shared:
            if aux not in covered:
                problems.append({"code": "combine.overlap_undeclared",
                                 "message": f"{a['id']} and {b['id']} both use {aux}; declare the correlation it induces (joint treatment), "
                                            "or compare them separately. Their likelihoods are never multiplied as if independent"})
        if any(c.get("independent") for c in decl) and shared:
            problems.append({"code": "combine.independence_contradicted",
                             "message": f"{list(pair)} declared independent but share {shared}"})
        if decl:
            blocks[" x ".join(pair)] = [{k: v for k, v in c.items() if k != "between"} for c in decl]
        else:
            problems.append({"code": "combine.cross_block_undeclared",
                             "message": f"no statement about the correlation of {a['id']} and {b['id']}; independence is not assumed"})
    ok = not problems
    return {"combinable": ok, "treatment": "joint-gls" if ok else "comparison-only", "problems": problems, "notes": notes,
            "cross_blocks": blocks}
