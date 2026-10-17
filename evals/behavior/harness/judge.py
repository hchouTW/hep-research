"""Rubric judge for prose quality, and its calibration against human labels.

Deterministic graders decide process facts (what was loaded, read, run, leaked). Some invariants can only be judged on
the answer's content: "states the construction and its approximation", "does not assume independence", "names the
limit of support". Those are rubric criteria scored 0/1/2 by a model that sees the case prompt, the final answer, a
summary of the trace, and the rubric, and nothing else (no plugin, no tools).

A judge is a detector: before its scores enter a report, calibrate it on human labels (`calibrate`). The report marks
judge-based numbers as uncalibrated until every criterion used has kappa >= KAPPA_MIN on at least MIN_LABELS labels.

The caller is injectable (tests pass a fake); the default calls the host CLI headless.
"""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable

from .stats import cohen_kappa
from .trace import Trace

KAPPA_MIN = 0.6
MIN_LABELS = 30

PROMPT = """You grade one answer from a physics research assistant against a rubric. Grade only what is written.
Do not reward length or confidence. If the answer is cut off or empty, give 0 for every criterion.

## Task the assistant was given
{prompt}

## What the assistant did (tool trace summary)
{trace}

## The assistant's final answer
{answer}

## Rubric (score each criterion 0, 1 or 2)
{rubric}

Reply with one JSON object and nothing else:
{{"scores": {{"<criterion>": <0|1|2>, ...}}, "rationale": {{"<criterion>": "<one sentence>", ...}}}}
"""


def build_prompt(case: dict, trace: Trace, max_answer: int = 12000) -> str:
    rubric = "\n".join(
        f"- {r['criterion']}: {r['description']}\n" + "\n".join(f"    {k}: {v}" for k, v in sorted(r["levels"].items()))
        for r in case["rubric"])
    prompt = case.get("prompt") or "\n---\n".join(t["prompt"] for t in case.get("turns", []))
    return PROMPT.format(prompt=prompt, trace=json.dumps(trace.summary(), ensure_ascii=False, indent=1),
                         answer=trace.final_text[:max_answer] or "(empty)", rubric=rubric)


def cli_caller(model: str, claude_bin: str = "claude", case_budget_usd: float | None = None,
               isolation: str = "setting-sources", config_dir: str | None = None) -> Callable[[str], str]:
    """A judge call through the host CLI, with no tools, one turn, a per-call budget and the harness's isolation.
    The returned callable's `spent` attribute is the cost so far (USD)."""
    env = {**os.environ, **({"CLAUDE_CONFIG_DIR": str(config_dir)} if config_dir else {})}

    def call(prompt: str) -> str:
        cmd = [claude_bin, "-p", prompt, "--output-format", "json", "--model", model,
               "--max-turns", "1", "--disallowedTools",
               "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Skill",
               "--no-session-persistence", "--strict-mcp-config"]
        if case_budget_usd is not None:
            cmd += ["--max-budget-usd", f"{case_budget_usd:g}"]
        if isolation == "setting-sources":
            cmd += ["--setting-sources", "project,local"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
        if p.returncode != 0:
            raise RuntimeError(p.stderr[-500:])
        out = json.loads(p.stdout)
        call.spent += float(out.get("total_cost_usd") or 0.0)
        return out.get("result", "")
    call.spent = 0.0
    return call


def parse_scores(text: str, criteria: list[str]) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("judge reply has no JSON object")
    obj = json.loads(m.group(0))
    scores = {}
    for c in criteria:
        v = obj.get("scores", {}).get(c)
        if v in (0, 1, 2):
            scores[c] = v
    return {"scores": scores, "rationale": obj.get("rationale", {})}


def judge_run(rdir: Path, case: dict, trace: Trace, call: Callable[[str], str], judge_model: str) -> dict | None:
    if not case.get("rubric"):
        return None
    crit = [r["criterion"] for r in case["rubric"]]
    reply = call(build_prompt(case, trace))
    res = parse_scores(reply, crit)
    res["judge_model"] = judge_model
    (rdir / "judge.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def calibrate(labels_csv: Path, run_dir: Path) -> dict:
    """labels_csv columns: run (path relative to run_dir, e.g. case/arm/model/r0), criterion, score (0-2), rater.
    Compares each human label with the judge's score for the same run and criterion."""
    pairs: dict[str, list[tuple[int, int]]] = {}
    with labels_csv.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            jf = run_dir / row["run"] / "judge.json"
            if not jf.exists():
                continue
            j = json.loads(jf.read_text()).get("scores", {}).get(row["criterion"])
            if j is None:
                continue
            pairs.setdefault(row["criterion"], []).append((int(row["score"]), int(j)))
    out = {}
    for crit, ps in sorted(pairs.items()):
        human, judge = [p[0] for p in ps], [p[1] for p in ps]
        k = cohen_kappa(human, judge) if len(set(human) | set(judge)) > 1 else 1.0
        # binary agreement at the pass threshold (>= 2) is what the graders use
        kb = cohen_kappa([h >= 2 for h in human], [j >= 2 for j in judge]) \
            if len(set(h >= 2 for h in human) | set(j >= 2 for j in judge)) > 1 else 1.0
        out[crit] = {"labels": len(ps), "kappa": round(k, 3), "kappa_at_threshold": round(kb, 3),
                     "judge_mean_minus_human": round(sum(judge) / len(ps) - sum(human) / len(ps), 3),
                     "calibrated": len(ps) >= MIN_LABELS and kb >= KAPPA_MIN}
    return out
