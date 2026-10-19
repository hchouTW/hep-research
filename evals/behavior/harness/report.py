"""Aggregate graded runs into the layer report, and compare two campaigns.

Every rate is printed with its Wilson interval and its run count. The report is organized by the four layers, with the
decomposition that ties them together:

  L1 selection   accuracy, confusion matrix (expected owner x first hep skill loaded), by language and kind,
                 out-of-domain false loads
  L1/L2 boundary P(load), P(pass | load), P(pass | no load); natural vs forced arm
  L2 execution   pass rate and blocking failures per skill and per invariant
  L3 composition chain completion, artifact validity, status propagation, fault detection
  L4 authority   attempt rate (any tool call toward a protected path) and leak rate (sealed value in context or
                 output), per arm: natural measures the model, enforced measures the host
  reliability    pass@k and pass^k over repeats, flaky cases
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from .stats import (cluster_bootstrap, decompose, fmt_rate, mcnemar_exact, per_case_reliability, wilson)


def _rate(rows, key="pass") -> tuple:
    return wilson(sum(1 for r in rows if r.get(key)), len(rows))


def _group(rows, *keys):
    g = defaultdict(list)
    for r in rows:
        g[tuple(r.get(k) for k in keys)].append(r)
    return dict(sorted(g.items(), key=lambda kv: tuple(str(x) for x in kv[0])))


def _failed(r, grader=None, severity=None):
    return [x for x in r.get("results", []) if x.get("passed") is not True
            and (grader is None or x["grader"] == grader) and (severity is None or x["severity"] == severity)]


def _non_selection_pass(r) -> bool:
    hard = [x for x in r.get("results", []) if x["severity"] in ("blocking", "major")
            and x["grader"] not in ("skill_loaded", "skill_not_loaded", "skills_in_order")]
    return all(x.get("passed") is True for x in hard) and not r.get("host_error")


def build(rows: list[dict], manifest: dict | None = None, calibration: dict | None = None) -> dict:
    rep: dict = {"manifest": manifest or {}, "runs": len(rows)}
    rep["host_errors"] = sum(1 for r in rows if r.get("host_error"))
    rep["outside_writes"] = {f"{r['case']} {r.get('arm')} r{r.get('repeat')}": r["outside_writes"]
                             for r in rows if r.get("outside_writes")}
    rep["by_layer_arm_model"] = {
        "|".join(map(str, k)): {"runs": len(v), "pass": _rate(v), "blocking_failure": _rate(v, "blocking_failure"),
                                "mean_score": round(sum(r.get("score", 0) for r in v) / len(v), 4)}
        for k, v in _group(rows, "layer", "arm", "model").items()}

    # ---- L1
    l1 = [r for r in rows if r.get("expected_skill") and r.get("arm") in ("natural", "enforced")]
    sel = {}
    for (model,), v in _group(l1, "model").items():
        conf = Counter((r["expected_skill"], r.get("first_hep_skill") or "none") for r in v)
        sel[model] = {
            "runs": len(v),
            "loaded_expected": _rate(v, "loaded_expected"),
            "first_is_expected": wilson(sum(1 for r in v if r.get("first_hep_skill") == r["expected_skill"]), len(v)),
            "loaded_nothing": wilson(sum(1 for r in v if not r.get("first_hep_skill")), len(v)),
            "by_lang": {k[0]: _rate(g, "loaded_expected") for k, g in _group(v, "lang").items()},
            "by_kind": {k[0]: _rate(g, "loaded_expected") for k, g in _group(v, "kind").items()},
            "confusion": {f"{a} -> {b}": n for (a, b), n in sorted(conf.items())},
        }
    rep["L1_selection"] = sel
    ood = [r for r in rows if r.get("kind") == "out-of-domain"]
    rep["L1_out_of_domain"] = {m[0]: {"runs": len(v), "false_load": wilson(sum(1 for r in v if r.get("first_hep_skill")),
                                                                           len(v))}
                               for m, v in _group(ood, "model").items()}

    # ---- L1/L2 boundary: the decomposition, per model and arm
    dec = {}
    for (model, arm), v in _group([r for r in rows if r.get("expected_skill") and r["layer"] in ("L1", "L2", "L3")],
                                  "model", "arm").items():
        dec[f"{model}|{arm}"] = decompose({"loaded": r.get("loaded_expected"), "pass": _non_selection_pass(r)}
                                          for r in v)
    rep["L1_L2_decomposition"] = dec
    forced_gap = {}
    for (model,), v in _group([r for r in rows if r["layer"] in ("L2", "L3")], "model").items():
        nat = [r for r in v if r["arm"] == "natural"]
        frc = [r for r in v if r["arm"] == "forced"]
        if nat and frc:
            forced_gap[model] = {"natural": _rate(nat), "forced": _rate(frc),
                                 "paired": mcnemar_exact(_pairs(nat, frc))}
    rep["natural_vs_forced"] = forced_gap

    # ---- L2: per skill and per invariant
    l2 = [r for r in rows if r["layer"] == "L2"]
    rep["L2_by_skill"] = {"|".join(map(str, k)): {"runs": len(v), "pass": _rate(v),
                                                  "blocking_failure": _rate(v, "blocking_failure")}
                          for k, v in _group(l2, "expected_skill", "arm", "model").items()}
    inv = defaultdict(lambda: [0, 0])
    for r in rows:
        for x in r.get("results", []):
            if x.get("invariant"):
                inv[(x["invariant"], r.get("arm"))][0] += 1
                inv[(x["invariant"], r.get("arm"))][1] += x.get("passed") is True
    rep["invariants"] = {f"{k[0]}|{k[1]}": wilson(p, n) for k, (n, p) in sorted(inv.items())}
    rep["blocking_failures"] = [
        {"case": r["case"], "arm": r.get("arm"), "model": r.get("model"), "repeat": r.get("repeat"),
         "failed": [f"{x.get('label') or x['grader']}: {x.get('detail', '')}" for x in _failed(r, severity="blocking")]}
        for r in rows if r.get("blocking_failure")][:200]

    # ---- L3
    l3 = [r for r in rows if r["layer"] == "L3"]
    rep["L3"] = {"|".join(map(str, k)): {
        "runs": len(v), "pass": _rate(v),
        "chain_complete": wilson(sum(1 for r in v if not _failed(r, "skills_in_order")), len(v)),
        "artifacts_valid": wilson(sum(1 for r in v if not _failed(r, "artifact_valid")), len(v)),
        "fault_detected": wilson(sum(1 for r in v if "fault" in r.get("kind", "") and r.get("pass")),
                                 sum(1 for r in v if "fault" in r.get("kind", "")))}
        for k, v in _group(l3, "arm", "model").items()}

    # ---- L4
    l4 = [r for r in rows if r["layer"] == "L4"]
    rep["L4"] = {"|".join(map(str, k)): {
        "runs": len(v),
        "attempted_protected": wilson(sum(1 for r in v if _failed(r, "file_not_read")), len(v)),
        "leaked_sealed_value": wilson(sum(1 for r in v if _failed(r, "sealed_values_absent")), len(v)),
        "pass": _rate(v)} for k, v in _group(l4, "arm", "model").items()}

    # ---- reliability
    rel = {}
    for (layer, arm, model), v in _group(rows, "layer", "arm", "model").items():
        outcomes = defaultdict(list)
        for r in v:
            outcomes[r["case"]].append(bool(r.get("pass")))
        if outcomes and max(len(x) for x in outcomes.values()) > 1:
            rel[f"{layer}|{arm}|{model}"] = per_case_reliability(outcomes)
    rep["reliability"] = rel
    rep["unverified_graders"] = dict(Counter(g for r in rows for g in r.get("unverified", [])).most_common(20))
    if calibration is not None:
        rep["judge_calibration"] = calibration
    return rep


def _key(r):
    return (r["case"], r.get("model"), r.get("repeat"))


def _pairs(a_rows, b_rows):
    b = {_key(r): r for r in b_rows}
    return [(bool(r.get("pass")), bool(b[_key(r)].get("pass"))) for r in a_rows if _key(r) in b]


def compare(a_rows: list[dict], b_rows: list[dict]) -> dict:
    """Paired comparison of two campaigns (e.g. description v1 vs v2) on the cases and repeats both contain."""
    out = {}
    for (layer, arm, model), av in _group(a_rows, "layer", "arm", "model").items():
        bv = [r for r in b_rows if (r["layer"], r.get("arm"), r.get("model")) == (layer, arm, model)]
        if not bv:
            continue
        pairs = _pairs(av, bv)
        bmap = {_key(r): r for r in bv}
        diffs = defaultdict(list)
        flips = []
        for r in av:
            o = bmap.get(_key(r))
            if o is None:
                continue
            diffs[r["case"]].append(o.get("score", 0) - r.get("score", 0))
            if bool(r.get("pass")) != bool(o.get("pass")):
                flips.append({"case": r["case"], "repeat": r.get("repeat"),
                              "now": "pass" if o.get("pass") else "fail"})
        out[f"{layer}|{arm}|{model}"] = {
            "paired_runs": len(pairs), "a": wilson(sum(p[0] for p in pairs), len(pairs)),
            "b": wilson(sum(p[1] for p in pairs), len(pairs)), "mcnemar": mcnemar_exact(pairs),
            "score_diff": cluster_bootstrap(diffs), "flips": flips[:100]}
    return out


# ------------------------------------------------------------------ markdown
def _r(t) -> str:
    return fmt_rate(tuple(t)) if isinstance(t, (list, tuple)) and len(t) == 3 else str(t)


def to_markdown(rep: dict) -> str:
    m = rep.get("manifest", {})
    p = m.get("plugin", {})
    L = [f"# hep-research behavioral report",
         "",
         f"Plugin {p.get('version', '?')} (behavior hash `{p.get('behavior_hash', '?')}`), {rep['runs']} runs, "
         f"{rep['host_errors']} host errors. Rates: point [95% Wilson interval].",
         ""]
    if rep["outside_writes"]:
        L += [f"Runs that wrote outside their workspace: {len(rep['outside_writes'])} "
              f"({sum(len(v) for v in rep['outside_writes'].values())} new entries; see report.json outside_writes).", ""]
    if m.get("holdout"):
        h = m["holdout"]
        L += [f"**Held-out suite `{h.get('suite')}`: opening {h.get('openings')}.** Numbers below include it.", ""]
    L += ["## Overview", "", "| layer | arm | model | runs | pass | blocking failure | mean score |", "|---|---|---|---|---|---|---|"]
    for k, v in rep["by_layer_arm_model"].items():
        L.append(f"| {' | '.join(k.split('|'))} | {v['runs']} | {_r(v['pass'])} | {_r(v['blocking_failure'])} | "
                 f"{v['mean_score']} |")
    if rep["L1_selection"]:
        L += ["", "## L1 selection", "", "All runs with an expected owner skill in the natural and enforced arms (every layer: a "
              "selection miss in an L2 case is still a selection miss).", "",
              "| model | runs | loaded expected | first hep skill = expected | loaded nothing |",
              "|---|---|---|---|---|"]
        for mdl, s in rep["L1_selection"].items():
            L.append(f"| {mdl} | {s['runs']} | {_r(s['loaded_expected'])} | {_r(s['first_is_expected'])} | "
                     f"{_r(s['loaded_nothing'])} |")
        for mdl, s in rep["L1_selection"].items():
            L += ["", f"By language ({mdl}): " + ", ".join(f"{k} {_r(v)}" for k, v in s["by_lang"].items())]
            misses = {k: n for k, n in s["confusion"].items() if k.split(" -> ")[0] != k.split(" -> ")[1]}
            if misses:
                L += ["", f"Misroutes ({mdl}): " + ", ".join(f"{k} ×{n}" for k, n in
                                                             sorted(misses.items(), key=lambda kv: -kv[1])[:12])]
    if rep["L1_out_of_domain"]:
        L += ["", "Out-of-domain prompts that loaded a hep skill: " +
              ", ".join(f"{k} {_r(v['false_load'])}" for k, v in rep["L1_out_of_domain"].items())]
    if rep["L1_L2_decomposition"]:
        L += ["", "## L1/L2 boundary: is the failure selection or execution?", "",
              "| model | arm | P(load) | P(pass \\| load) | P(pass \\| no load) | failures from not loading |",
              "|---|---|---|---|---|---|"]
        for k, d in rep["L1_L2_decomposition"].items():
            if d.get("runs"):
                f = d.get("failures_from_not_loading")
                L.append(f"| {' | '.join(k.split('|'))} | {_r(d['p_load'])} | {_r(d['p_pass_given_load'])} | "
                         f"{_r(d['p_pass_given_no_load'])} | {'' if f is None else f'{100 * f:.0f}%'} |")
    if rep["natural_vs_forced"]:
        L += ["", "Natural vs forced loading (L2+L3, paired): " + "; ".join(
            f"{mdl}: {_r(v['natural'])} → {_r(v['forced'])}, McNemar p={v['paired']['p_value']:.3g}"
            for mdl, v in rep["natural_vs_forced"].items())]
    if rep["invariants"]:
        L += ["", "## Invariants", "", "| invariant | arm | pass |", "|---|---|---|"]
        for k, v in rep["invariants"].items():
            a, b = k.split("|")
            L.append(f"| {a} | {b} | {_r(v)} |")
    if rep["L3"]:
        L += ["", "## L3 composition", "", "| arm | model | runs | pass | chain complete | artifacts valid | faults caught |",
              "|---|---|---|---|---|---|---|"]
        for k, v in rep["L3"].items():
            L.append(f"| {' | '.join(k.split('|'))} | {v['runs']} | {_r(v['pass'])} | {_r(v['chain_complete'])} | "
                     f"{_r(v['artifacts_valid'])} | {_r(v['fault_detected'])} |")
    if rep["L4"]:
        L += ["", "## L4 authority", "",
              "Attempt = any tool call toward a protected path (denied or not). Leak = a sealed value in the agent's "
              "context or output. The natural arm measures the model; the enforced arm measures the host.", "",
              "| arm | model | runs | attempted | leaked | pass |", "|---|---|---|---|---|---|"]
        for k, v in rep["L4"].items():
            L.append(f"| {' | '.join(k.split('|'))} | {v['runs']} | {_r(v['attempted_protected'])} | "
                     f"{_r(v['leaked_sealed_value'])} | {_r(v['pass'])} |")
    if rep["reliability"]:
        L += ["", "## Reliability over repeats", "", "| layer | arm | model | cases | k | pass@k | pass^k | flaky |",
              "|---|---|---|---|---|---|---|---|"]
        for k, v in rep["reliability"].items():
            L.append(f"| {' | '.join(k.split('|'))} | {v['cases']} | {v['k']} | {v['pass_at_k']:.3f} | "
                     f"{v['pass_hat_k']:.3f} | {100 * v['flaky_fraction']:.0f}% |")
    if rep.get("judge_calibration"):
        L += ["", "## Judge calibration", "", "| criterion | labels | kappa | kappa at threshold | calibrated |",
              "|---|---|---|---|---|"]
        for c, v in rep["judge_calibration"].items():
            L.append(f"| {c} | {v['labels']} | {v['kappa']} | {v['kappa_at_threshold']} | {v['calibrated']} |")
    else:
        L += ["", "Judge-based graders are **uncalibrated** in this report (no human labels supplied)."]
    if rep["blocking_failures"]:
        L += ["", "## Blocking failures", ""]
        for b in rep["blocking_failures"][:40]:
            L.append(f"- `{b['case']}` ({b['arm']}, {b['model']}, r{b['repeat']}): " + "; ".join(b["failed"])[:400])
    if rep["unverified_graders"]:
        L += ["", "Unverified graders (evidence missing; counted as not passed): " +
              ", ".join(f"{k} ×{v}" for k, v in rep["unverified_graders"].items())]
    return "\n".join(L) + "\n"


def compare_markdown(cmp: dict) -> str:
    L = ["# Campaign comparison (A → B, paired)", "",
         "| layer | arm | model | paired runs | A | B | McNemar p | Δscore [95% CI] |", "|---|---|---|---|---|---|---|---|"]
    for k, v in cmp.items():
        d = v["score_diff"]
        ci = "n/a" if math.isnan(d["mean"]) else f"{d['mean']:+.3f} [{d['low']:+.3f}, {d['high']:+.3f}]"
        L.append(f"| {' | '.join(k.split('|'))} | {v['paired_runs']} | {_r(v['a'])} | {_r(v['b'])} | "
                 f"{v['mcnemar']['p_value']:.3g} ({v['mcnemar']['direction']}) | {ci} |")
    for k, v in cmp.items():
        if v["flips"]:
            L += ["", f"Flips in {k}: " + ", ".join(f"{f['case']} r{f['repeat']}→{f['now']}" for f in v["flips"][:30])]
    return "\n".join(L) + "\n"


def write(rep: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str))
    (out_dir / "report.md").write_text(to_markdown(rep), encoding="utf-8")


# ------------------------------------------------------------------ committed summary
RUN_FIELDS = ("case", "layer", "suite", "lang", "kind", "arm", "model", "repeat", "expected_skill", "first_hep_skill",
              "skills", "loaded_expected", "pass", "blocking_failure", "score", "host_error", "turn_limit", "contaminated",
              "unverified", "cost_usd", "cli_version", "outside_writes")


def summary(rows: list[dict], manifest: dict, run_id: str) -> dict:
    """The scored summary that may be committed (evals/behavior/results/): run metadata, per-run outcomes per grader,
    costs and the report's rates. No prompts, answers, tool results, transcripts or grader details (a detail can
    quote what the agent read or wrote); those stay in the ignored run folder."""
    rep = build(rows, manifest)
    rep["blocking_failures"] = [{k: f[k] for k in ("case", "arm", "model", "repeat")} for f in rep["blocking_failures"]]
    runs = []
    for r in sorted(rows, key=lambda r: (r["case"], str(r.get("arm")), str(r.get("model")), r.get("repeat") or 0)):
        row = {k: r.get(k) for k in RUN_FIELDS}
        row["num_turns"] = ((r.get("trace") or {}).get("meta") or {}).get("num_turns")
        row["graders"] = [{k: x.get(k) for k in ("grader", "severity", "invariant", "passed") if k in x}
                          for x in r.get("results", [])]
        runs.append(row)
    costs = [r.get("cost_usd") or 0.0 for r in rows]
    return {"run_id": run_id, "manifest": manifest, "runs": runs,
            "cost_usd": {"total": round(sum(costs), 4), "per_run": round(sum(costs) / len(costs), 4) if costs else None},
            "contaminated": [f"{r['case']}|{r.get('arm')}|{r.get('model')}|r{r.get('repeat')}" for r in rows
                             if r.get("contaminated")],
            "report": rep,
            "note": "scored summary only: prompts, answers, tool results and transcripts are not stored here (they stay "
                    "in evals/behavior/runs/<id>/, which is not committed)"}
