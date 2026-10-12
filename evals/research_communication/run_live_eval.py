#!/usr/bin/env python3
"""Live run of the research-communication behavioral cases through a headless `claude -p` session (plan T10).

For each case in cases/cases.json: a fresh temporary folder holding only the case's fixture inputs (copied under the
same relative path the prompt names), one `claude -p` pass with the plugin from --plugin-dir, read-only tools
(Skill, Read, Glob, Grep; Bash, Write, Edit, web and agent tools denied), a pinned --model, --max-turns and a per-case
budget; no new case starts once --budget-usd is spent. The isolation, command shape and stream parsing are the
routing harness's (evals/routing/run_routing_eval.py). The captured outputs are written in the replay scorer's format
(outputs/<run_id>.json: meta with model, CLI version, plugin commit, tool access, coverage; one output per case with the
first plugin skill loaded, the final answer as prose, and judgments.semantic = "unjudged"), then scored with
score_replay.py into results/<run_id>.json. A reviewer records the semantic judgments afterwards; this runner never
judges prose. Paid model calls: use --dry-run first.

Usage: run_live_eval.py --model claude-sonnet-5-5 [--ids a,b] [--max-turns 12] [--case-budget-usd 0.6] [--budget-usd 10]
                        [--isolation setting-sources | --config-dir DIR] [--plugin-dir DIR] [--run-id ID] [--dry-run]
Exit codes: 0 run completed; 1 contaminated or no case completed; 2 bad input.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "evals" / "routing"))
import run_routing_eval as rre  # noqa: E402
import score_replay as sr  # noqa: E402

CASES = HERE / "cases" / "cases.json"


def git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def run_case(case: dict, args, raw_dir: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="hep-rceval-") as tmp:
        cwd = Path(tmp)
        for inp in case.get("inputs") or []:
            src = HERE / inp
            dst = cwd / inp
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        cmd = rre.claude_cmd(args.cli_path, case["prompt"], args) + ["--no-session-persistence"]
        if args.dry_run:
            print(" ".join(cmd[:4]) + " ...", "(cwd with", ", ".join(case.get("inputs") or ["no inputs"]) + ")")
            return {"case_id": case["id"], "dry_run": True}
        env = dict(rre.os.environ)
        if args.config_dir:
            env["CLAUDE_CONFIG_DIR"] = str(args.config_dir)
        sdir = rre.session_dir(args, cwd)
        existed = sdir is not None and sdir.exists()
        try:
            proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=args.case_timeout, check=False)
            stream, err, code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            stream, err, code = (exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")), "timeout", -1
        (raw_dir / f"{case['id']}.jsonl").write_text(stream, encoding="utf-8")
        if err.strip():
            (raw_dir / f"{case['id']}.stderr.txt").write_text(err, encoding="utf-8")
        if sdir is not None and not existed and "hep-rceval-" in sdir.name and sdir.is_dir():
            shutil.rmtree(sdir, ignore_errors=True)
    facts = rre.parse_claude(stream.splitlines())
    skills = facts["skills"]
    return {"case_id": case["id"], "skill_loaded": skills[0] if skills else None, "skills": skills, "other_skills": facts["other_skills"],
            "prose": facts["final_text"], "structured": {}, "unresolved": [], "judgments": {"semantic": "unjudged"},
            "run": {"exit_code": code, "is_error": facts["is_error"], "cost_usd": round(facts["cost_usd"], 6), "turns": facts["turns"],
                    "profile_reads": facts["profile_reads"], "plugins_reported": facts["plugins"], "cli_version": facts["cli_version"],
                    "model_reported": facts["model"]}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--ids")
    ap.add_argument("--cases", type=Path, default=CASES)
    ap.add_argument("--plugin-dir", type=Path, default=rre.PLUGIN)
    ap.add_argument("--cli-path", default=shutil.which("claude") or "claude")
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--case-budget-usd", type=float, default=0.6)
    ap.add_argument("--budget-usd", type=float, default=10.0)
    ap.add_argument("--case-timeout", type=float, default=600.0)
    ap.add_argument("--isolation", choices=("setting-sources", "config-dir"), default="setting-sources")
    ap.add_argument("--config-dir", type=Path)
    ap.add_argument("--run-id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    args.cli = "claude"
    try:
        cases_doc = json.loads(args.cases.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    cases = cases_doc["cases"]
    if args.ids:
        want = set(args.ids.split(","))
        cases = [c for c in cases if c["id"] in want]
    run_id = args.run_id or f"live-{dt.datetime.now(dt.timezone.utc):%Y%m%d-%H%M}-{args.model.split('-')[1]}"
    raw_dir = HERE / "runs" / run_id / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    outputs, spent, stopped = [], 0.0, False
    for case in cases:
        if spent >= args.budget_usd:
            stopped = True
            break
        row = run_case(case, args, raw_dir)
        outputs.append(row)
        if not args.dry_run:
            spent += row["run"]["cost_usd"]
            print(f"{case['id']}: skill={row['skill_loaded']} turns={row['run']['turns']} cost=${row['run']['cost_usd']:.3f} error={row['run']['is_error']}")
            if row["run"]["plugins_reported"] and any(p != rre.PLUGIN_NAME for p in row["run"]["plugins_reported"]):
                print(f"contaminated: plugins {row['run']['plugins_reported']}", file=sys.stderr)
                return 1
    if args.dry_run:
        return 0
    meta = {"run": run_id, "live": True, "date": dt.date.today().isoformat(), "model": args.model,
            "models_reported": sorted({o["run"]["model_reported"] for o in outputs if o["run"]["model_reported"]}),
            "cli": "claude", "cli_version": next((o["run"]["cli_version"] for o in outputs if o["run"]["cli_version"]), None),
            "prompt_version": hashlib.sha256(args.cases.read_bytes()).hexdigest(), "plugin_commit": git("rev-parse", "HEAD"),
            "plugin_dirty": bool(git("status", "--porcelain", "--", "plugins/hep-research")), "isolation": args.isolation,
            "tool_access": list(rre.READ_ONLY_TOOLS), "max_turns": args.max_turns, "case_budget_usd": args.case_budget_usd,
            "budget_usd": args.budget_usd, "stopped_early": stopped, "coverage": f"{len(outputs)} of {len(cases_doc['cases'])} cases",
            "cost_usd": round(spent, 4), "judged_by": None,
            "note": "prose captured as the session's final answer; semantic judgments are unjudged until a reviewer records them"}
    out_path = HERE / "outputs" / f"{run_id}.json"
    out_path.write_text(json.dumps({"meta": meta, "outputs": outputs}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = sr.score_all(cases_doc, {"meta": meta, "outputs": outputs})
    (HERE / "results").mkdir(exist_ok=True)
    res_path = HERE / "results" / f"{run_id}.json"
    res_path.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": run_id, "outputs": str(out_path), "results": str(res_path), "counts": summary["counts"],
                      "critical_failures": [c["case_id"] for c in summary["critical_failures"]], "cost_usd": round(spent, 4)}, indent=1))
    return 0 if outputs else 1


if __name__ == "__main__":
    sys.exit(main())
