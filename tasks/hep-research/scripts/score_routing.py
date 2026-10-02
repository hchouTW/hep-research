#!/usr/bin/env python3
"""Score live routing traces from run_headless.py. Not part of the plugin.

A case passes when the first skill the host invoked is `hep-research:<expected_primary>`. Expected "ask" passes
when the answer asks the user a clarifying question (any skill may have been loaded first).
Other outcomes are reported separately: legacy standalone skill chosen, no skill invoked, another plugin skill.
Loading: for cases whose expected owner is hep-theory or hep-computing, any read of an experiment-profile file
is a loading violation (task 7.15).
usage: score_routing.py routing-live.json [--out score.json]
"""
import json
import sys
from collections import Counter

LEGACY = {"academic-diagrams", "academic-papers", "agile-development", "ams-analysis", "deep-learning", "hep-analysis",
          "task-authoring"}


def classify(tr):
    exp = tr["case"]["expected_primary"]
    inv = [s for s in tr["skills_invoked"] if s]
    first = inv[0] if inv else None
    # a run that hit --max-turns after choosing a skill still shows the routing decision
    if first is None and tr.get("subtype") not in ("success", "error_max_turns"):
        return "run-error", first
    if exp == "ask":
        asks = "?" in (tr.get("result") or "") or "？" in (tr.get("result") or "")
        return ("pass" if asks else "fail"), first
    if first is None:
        return "no-skill", first
    if first == f"hep-research:{exp}":
        return "pass", first
    if first in LEGACY:
        return "legacy-skill", first
    if first.startswith("hep-research:"):
        return "other-hep-research-skill", first
    return "other-skill", first


def main():
    traces = json.load(open(sys.argv[1], encoding="utf-8"))
    rows = []
    for tr in traces:
        outcome, first = classify(tr)
        exp = tr["case"]["expected_primary"]
        exp_reads = [f["path"] for f in tr["files_read_detail"] if f["experiment_profile"]]
        loading_violation = exp in ("hep-theory", "hep-computing") and tr["case"]["kind"] != "ams-computing" and bool(exp_reads)
        rows.append({"id": tr["case"]["id"], "lang": tr["case"]["lang"], "kind": tr["case"]["kind"], "expected": exp,
                     "first_skill": first, "all_skills": tr["skills_invoked"], "outcome": outcome,
                     "files_read": len(tr["files_read"]), "outside_plugin_reads": [f["path"] for f in tr["files_read_detail"] if not f["inside_plugin"]],
                     "experiment_profile_reads": exp_reads, "loading_violation": loading_violation,
                     "cost_usd": tr.get("cost_usd"), "num_turns": tr.get("num_turns")})
    summary = {"cases": len(rows), "outcomes": dict(Counter(r["outcome"] for r in rows)),
               "by_lang": {l: dict(Counter(r["outcome"] for r in rows if r["lang"] == l)) for l in sorted({r["lang"] for r in rows})},
               "loading_violations": [r["id"] for r in rows if r["loading_violation"]],
               "total_cost_usd": round(sum(r["cost_usd"] or 0 for r in rows), 4),
               "model": traces[0].get("model") if traces else None, "host_version": traces[0].get("host_version") if traces else None,
               "plugin_path": traces[0].get("plugin_path") if traces else None}
    out = {"summary": summary, "rows": rows}
    if "--out" in sys.argv:
        open(sys.argv[sys.argv.index("--out") + 1], "w", encoding="utf-8").write(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    for r in rows:
        if r["outcome"] != "pass" or r["loading_violation"]:
            print(r["id"], r["kind"], r["expected"], "->", r["first_skill"], r["outcome"], "LOADVIOL" if r["loading_violation"] else "")


if __name__ == "__main__":
    main()
