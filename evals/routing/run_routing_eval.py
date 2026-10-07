#!/usr/bin/env python3
"""Live routing evaluation of the hep-research plugin through a headless agent CLI.

Runs the routing cases (plugins/hep-research/tests/routing/cases.json) one pass each through `claude -p` (or `codex
exec`), records which plugin skill each run loads first, every skill it loads and the profile files it reads, scores
the run against the case's expected owner, and compares the scores with a committed baseline for the same CLI,
CLI version and model. Paid model calls: run `estimate` first, and use a budget.

Subcommands:
  run       run cases and write the scored summary to results/<run_id>.json (raw streams go to runs/<run_id>/raw/,
            which is not committed). --dry-run prints the commands and calls no model.
  compare   compare a scored summary with a baseline (exit 1 on a regression: a case that passed and now fails).
  baseline  copy a scored summary of a full run to baselines/<cli>-<cli version>-<model>.json.
  estimate  expected cost of a run from the mean cost per turn in an earlier summary (or --per-turn-usd).

Isolation (recorded in the summary):
  config-dir       CLAUDE_CONFIG_DIR (claude) or CODEX_HOME (codex) points at a separate, logged-in configuration, so
                   no user instructions, other plugins or MCP servers load; the plugin under test comes from
                   --plugin-dir. Log in once in a terminal: CLAUDE_CONFIG_DIR=DIR claude auth login.
  setting-sources  (claude only) the user's login with --setting-sources project,local and --strict-mcp-config, so
                   user settings, user-enabled plugins and MCP servers do not load. The run stops if the session
                   reports any plugin besides the one under test.
Scoring: strict = the first plugin skill loaded is the expected owner (or an accepted alternative of a limited-support
case); lenient = the expected owner is loaded at some point; an underspecified case ("ask") passes when the run loads
no plugin skill before asking, judged by a question mark in the final answer (a heuristic, labeled so). A multi-turn
case passes when every turn loads its own expected owner during that turn.

Usage:
  run_routing_eval.py estimate --from results/R.json [--cases FILE] [--ids a,b]
  run_routing_eval.py run --model claude-sonnet-5-5 [--cli claude] [--ids a,b | --sample N --seed S] [--jobs 4]
                          [--max-turns 6] [--case-budget-usd 0.5] [--budget-usd 5] [--isolation setting-sources |
                          --config-dir DIR] [--dry-run]
  run_routing_eval.py compare results/R.json [--baseline baselines/B.json]
  run_routing_eval.py baseline results/R.json
Exit codes: 0 ok; 1 regression (compare) or contaminated run; 2 bad input. Standard library only.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins" / "hep-research"
CASES = PLUGIN / "tests" / "routing" / "cases.json"
PLUGIN_NAME = "hep-research"
SKILLS = sorted(p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md"))
READ_ONLY_TOOLS = ["Skill", "Read", "Glob", "Grep"]
DENIED_TOOLS = ["Bash", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Agent", "Task"]


class EvalError(ValueError):
    """Bad input to the harness."""


# --------------------------------------------------------------------------------------------- cases
def load_cases(path: Path, ids=None, sample=None, seed=0) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    cases = json.loads(raw)["cases"]
    if ids:
        want = [i for i in ids if i]
        known = {c["id"] for c in cases}
        missing = [i for i in want if i not in known]
        if missing:
            raise EvalError(f"unknown case ids: {', '.join(missing)}")
        cases = [c for c in cases if c["id"] in want]
    if sample:
        cases = random.Random(seed).sample(cases, min(sample, len(cases)))
    return cases, hashlib.sha256(raw).hexdigest()


def turns_of(case: dict) -> list[dict]:
    first = {"prompt": case["prompt"], "expected": case["expected_primary"]}
    return [first] + [{"prompt": t["prompt"], "expected": t["expected"]} for t in case.get("turns", [])]


# ------------------------------------------------------------------------------------------- parsing
def skill_name(raw: str) -> tuple[str, bool]:
    """(short name, is a skill of the plugin under test) for a Skill tool input such as 'hep-research:hep-theory'."""
    if ":" in raw:
        plugin, name = raw.split(":", 1)
        return name, plugin == PLUGIN_NAME and name in SKILLS
    return raw, raw in SKILLS


def parse_claude(lines) -> dict:
    """Facts from a `claude -p --output-format stream-json --verbose` stream."""
    out = {"session_id": None, "cli_version": None, "model": None, "plugins": [], "skills": [], "other_skills": [],
           "profile_reads": [], "cost_usd": 0.0, "turns": 0, "is_error": False, "final_text": "", "events": 0}
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        out["events"] += 1
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            out["session_id"] = ev.get("session_id")
            out["cli_version"] = ev.get("claude_code_version")
            out["model"] = ev.get("model")
            # plugins built into the CLI ("path": "builtin", source "...@builtin") are part of the CLI, not user installs
            builtin = lambda p: isinstance(p, dict) and (p.get("path") == "builtin" or str(p.get("source", "")).endswith("@builtin"))
            out["plugins"] = sorted({(p.get("name") if isinstance(p, dict) else str(p)) for p in ev.get("plugins", []) if not builtin(p)})
            out["builtin_plugins"] = sorted({p.get("name") for p in ev.get("plugins", []) if builtin(p)})
        elif ev.get("type") == "assistant":
            for block in (ev.get("message") or {}).get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                inp = block.get("input") or {}
                if block.get("name") == "Skill":
                    name, ours = skill_name(str(inp.get("skill") or inp.get("command") or ""))
                    (out["skills"] if ours else out["other_skills"]).append(name)
                for key in ("file_path", "path", "pattern"):
                    v = str(inp.get(key) or "")
                    if "/profiles/" in v or v.startswith("profiles/"):
                        out["profile_reads"].append(v[v.index("profiles/"):])
        elif ev.get("type") == "result":
            out["cost_usd"] = float(ev.get("total_cost_usd") or 0.0)
            out["turns"] = int(ev.get("num_turns") or 0)
            out["is_error"] = bool(ev.get("is_error")) or ev.get("subtype", "success") != "success"
            out["final_text"] = str(ev.get("result") or "")
            out["session_id"] = ev.get("session_id") or out["session_id"]
    return out


SKILL_READ = re.compile(r"skills/([a-z-]+)/SKILL\.md")


def parse_codex(lines) -> dict:
    """Facts from a `codex exec --json` stream: a skill counts as loaded when its SKILL.md is read by a command."""
    out = {"session_id": None, "cli_version": None, "model": None, "plugins": [], "skills": [], "other_skills": [],
           "profile_reads": [], "cost_usd": 0.0, "turns": 0, "is_error": False, "final_text": "", "events": 0,
           "tokens": 0}
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        out["events"] += 1
        typ = ev.get("type")
        if typ == "thread.started":
            out["session_id"] = ev.get("thread_id")
        elif typ == "item.completed":
            item = ev.get("item") or {}
            if item.get("type") == "command_execution":
                cmd = str(item.get("command") or "")
                for name in SKILL_READ.findall(cmd):
                    if name in SKILLS and name not in out["skills"]:
                        out["skills"].append(name)
                for m in re.findall(r"profiles/[^\s'\"]+", cmd):
                    out["profile_reads"].append(m)
            elif item.get("type") == "agent_message":
                out["final_text"] = str(item.get("text") or "")
        elif typ == "turn.completed":
            out["turns"] += 1
            usage = ev.get("usage") or {}
            out["tokens"] += int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
        elif typ in ("turn.failed", "error"):
            out["is_error"] = True
    return out


# ------------------------------------------------------------------------------------------- scoring
def asks(text: str) -> bool:
    return "?" in text or "？" in text


def score_turn(expected: str, facts: dict, case: dict, prior_skills=()) -> dict:
    skills = [s for s in facts["skills"]]
    first = skills[0] if skills else None
    if facts["is_error"] and not skills:
        outcome = "error"
    elif expected == "ask":
        outcome = "pass" if (not skills and asks(facts["final_text"])) else ("no-question" if not skills else "skill-instead-of-question")
    elif first is None:
        outcome = "no-skill"
    elif first == expected or (case.get("limited_support") and first in case.get("also_accept", [])):
        outcome = "pass"
    elif case.get("not") and first == case["not"]:
        outcome = "excluded-skill"
    else:
        outcome = "wrong-skill"
    lenient = outcome == "pass" or (expected != "ask" and (expected in skills or expected in prior_skills))
    return {"expected": expected, "first_skill": first, "skills": skills, "outcome": outcome, "strict": outcome == "pass",
            "lenient": lenient, "heuristic": expected == "ask"}


def loading_violation(case: dict, reads: list[str]) -> bool:
    """A case that names no profile ("profiles": []) must read none."""
    return case.get("profiles") == [] and bool(reads)


def summarize(rows: list[dict]) -> dict:
    def block(sel):
        n = len(sel)
        return {"cases": n, "strict_pass": sum(r["strict"] for r in sel), "lenient_pass": sum(r["lenient"] for r in sel)}
    out = {"overall": block(rows)}
    for key in ("lang", "kind", "variant", "expected_primary", "set"):
        groups: dict[str, list] = {}
        for r in rows:
            groups.setdefault(str(r.get(key) or "-"), []).append(r)
        out[f"by_{key}"] = {k: block(v) for k, v in sorted(groups.items())}
    out["outcomes"] = {}
    for r in rows:
        out["outcomes"][r["outcome"]] = out["outcomes"].get(r["outcome"], 0) + 1
    out["loading_violations"] = [r["id"] for r in rows if r.get("loading_violation")]
    costs = [r["cost_usd"] for r in rows]
    out["cost_usd"] = {"total": round(sum(costs), 4), "per_case": round(sum(costs) / len(costs), 4) if costs else None,
                       "per_turn": round(sum(costs) / max(sum(r["n_turns"] for r in rows), 1), 4)}
    return out


# ------------------------------------------------------------------------------------------- running
def claude_cmd(cli_path, prompt, args, session=None):
    cmd = [cli_path, "-p", prompt, "--model", args.model, "--output-format", "stream-json", "--verbose",
           "--max-turns", str(args.max_turns), "--max-budget-usd", f"{args.case_budget_usd:g}",
           "--plugin-dir", str(args.plugin_dir), "--strict-mcp-config",
           "--allowedTools", *READ_ONLY_TOOLS, "--disallowedTools", *DENIED_TOOLS]
    if args.isolation == "setting-sources":
        cmd += ["--setting-sources", "project,local"]
    if session:
        cmd += ["--resume", session]
    return cmd


def codex_cmd(cli_path, prompt, args, cwd, session=None):
    if session:
        return [cli_path, "exec", "resume", session, "--json", "-m", args.model, prompt]
    return [cli_path, "exec", "--json", "--skip-git-repo-check", "--sandbox", "read-only", "-m", args.model, "-C", str(cwd), prompt]


def session_dir(args, cwd: Path) -> Path | None:
    """The folder the Claude CLI keeps for a working directory (sessions, auto memory), or None for Codex."""
    if args.cli != "claude":
        return None
    root = Path(args.config_dir) if args.config_dir else Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return root / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(cwd.resolve()))


def run_case(case: dict, args, raw_dir: Path) -> dict:
    env = dict(os.environ)
    if args.config_dir:
        env["CLAUDE_CONFIG_DIR" if args.cli == "claude" else "CODEX_HOME"] = str(args.config_dir)
    parse = parse_claude if args.cli == "claude" else parse_codex
    row = {k: case.get(k) for k in ("id", "lang", "kind", "variant", "set", "expected_primary")}
    turn_rows, facts_all, session, cost, n_turns = [], [], None, 0.0, 0
    with tempfile.TemporaryDirectory(prefix="hep-routing-") as tmp:
        cwd = Path(tmp)
        for name, text in (case.get("inputs") or {}).items():
            (cwd / name).parent.mkdir(parents=True, exist_ok=True)
            (cwd / name).write_text(text, encoding="utf-8")
        prior: list[str] = []
        sdir = session_dir(args, cwd)
        sdir_existed = sdir is not None and sdir.exists()
        for k, turn in enumerate(turns_of(case), 1):
            cmd = (claude_cmd(args.cli_path, turn["prompt"], args, session) if args.cli == "claude"
                   else codex_cmd(args.cli_path, turn["prompt"], args, cwd, session))
            if args.cli == "claude" and len(turns_of(case)) == 1:
                cmd.append("--no-session-persistence")
            suffix = "" if k == 1 else f".turn{k}"
            saved = raw_dir / f"{case['id']}{suffix}.jsonl"
            if args.reuse_raw and saved.is_file() and saved.stat().st_size:
                # resuming a run: score the stream already recorded instead of paying for it again
                facts = parse(saved.read_text(encoding="utf-8").splitlines())
                facts_all.append(facts)
                session = facts["session_id"] or session
                cost += facts["cost_usd"]
                n_turns += facts["turns"]
                turn_rows.append(dict(score_turn(turn["expected"], facts, case, prior), exit_code=0, reused=True))
                prior += facts["skills"]
                continue
            try:
                proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=args.case_timeout, check=False)
                stream, err, code = proc.stdout, proc.stderr, proc.returncode
            except subprocess.TimeoutExpired as exc:
                stream, err, code = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""), "timeout", -1
            saved.write_text(stream, encoding="utf-8")
            if err.strip():
                (raw_dir / f"{case['id']}{suffix}.stderr.txt").write_text(err, encoding="utf-8")
            facts = parse(stream.splitlines())
            if code != 0 and not facts["events"]:
                facts["is_error"] = True
            facts_all.append(facts)
            session = facts["session_id"] or session
            cost += facts["cost_usd"]
            n_turns += facts["turns"]
            turn_rows.append(dict(score_turn(turn["expected"], facts, case, prior), exit_code=code))
            prior += facts["skills"]
        # the CLI keeps a folder per working directory; remove the one this case's throwaway folder created
        if sdir is not None and not sdir_existed and "hep-routing-" in sdir.name and sdir.is_dir():
            shutil.rmtree(sdir, ignore_errors=True)
    first = facts_all[0]
    row.update({"turns": turn_rows, "outcome": "pass" if all(t["strict"] for t in turn_rows) else
                next(t["outcome"] for t in turn_rows if not t["strict"]),
                "strict": all(t["strict"] for t in turn_rows), "lenient": all(t["lenient"] for t in turn_rows),
                "profile_reads": sorted({r for f in facts_all for r in f["profile_reads"]}),
                "other_skills": sorted({s for f in facts_all for s in f["other_skills"]}),
                "plugins_reported": first["plugins"], "builtin_plugins": first.get("builtin_plugins", []),
                "cli_version": first["cli_version"], "model_reported": first["model"],
                "cost_usd": round(cost, 6), "n_turns": n_turns})
    row["loading_violation"] = loading_violation(case, row["profile_reads"])
    return row


def contaminated(row: dict) -> str | None:
    extra = [p for p in row.get("plugins_reported") or [] if p != PLUGIN_NAME]
    if extra:
        return f"other plugins loaded: {', '.join(extra)}"
    return None


def cmd_run(args) -> int:
    cases, case_sha = load_cases(args.cases, args.ids.split(",") if args.ids else None, args.sample, args.seed)
    if not cases:
        raise EvalError("no cases selected")
    if args.cli == "codex" and args.isolation == "setting-sources":
        raise EvalError("codex needs --config-dir (CODEX_HOME with only this plugin installed)")
    args.cli_path = args.cli_path or shutil.which(args.cli) or args.cli
    args.isolation = "config-dir" if args.config_dir else args.isolation
    if args.dry_run:
        for c in cases:
            for t in turns_of(c):
                cmd = claude_cmd(args.cli_path, t["prompt"], args) if args.cli == "claude" else codex_cmd(args.cli_path, t["prompt"], args, "<tmp>")
                print(json.dumps({"case": c["id"], "cmd": cmd}, ensure_ascii=False))
        print(json.dumps({"status": "dry-run", "cases": len(cases), "turns": sum(len(turns_of(c)) for c in cases)}))
        return 0
    run_id = args.run_id or f"{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}-{args.cli}-{args.model}"
    raw_dir = args.out / run_id / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    lock, spent, rows, stop = threading.Lock(), [0.0], [], threading.Event()

    def task(case):
        if stop.is_set():
            return None
        with lock:
            if spent[0] >= args.budget_usd:
                stop.set()
                return None
        try:
            row = run_case(case, args, raw_dir)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:  # one broken case is recorded, not fatal
            row = {k: case.get(k) for k in ("id", "lang", "kind", "variant", "set", "expected_primary")}
            row.update({"turns": [], "outcome": "harness-error", "strict": False, "lenient": False, "profile_reads": [],
                        "other_skills": [], "plugins_reported": [], "builtin_plugins": [], "cli_version": None,
                        "model_reported": None, "cost_usd": 0.0, "n_turns": 0, "loading_violation": False,
                        "harness_error": f"{type(exc).__name__}: {exc}"})
        with lock:
            spent[0] += row["cost_usd"]
            why = contaminated(row)
            if why:
                row["contaminated"] = why
                stop.set()
        print(json.dumps({"case": row["id"], "outcome": row["outcome"], "skills": [t["skills"] for t in row["turns"]],
                          "cost_usd": row["cost_usd"], "spent_usd": round(spent[0], 4)}, ensure_ascii=False), flush=True)
        return row
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for row in pool.map(task, cases):
            if row is not None:
                rows.append(row)
    git = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", str(args.plugin_dir)],
                                capture_output=True, text=True, check=False).stdout.strip())
    versions = sorted({r["cli_version"] for r in rows if r.get("cli_version")})
    meta = {"run_id": run_id, "date": f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%d}", "cli": args.cli,
            "cli_version": versions[0] if len(versions) == 1 else versions, "model": args.model,
            "models_reported": sorted({r["model_reported"] for r in rows if r.get("model_reported")}),
            "isolation": args.isolation, "plugin_commit": git, "plugin_dirty": dirty, "cases_file_sha256": case_sha,
            "selected": len(cases), "completed": len(rows), "full_set": len(cases) == len(json.loads(args.cases.read_text())["cases"]),
            "max_turns": args.max_turns, "case_budget_usd": args.case_budget_usd, "budget_usd": args.budget_usd,
            "stopped_early": len(rows) < len(cases)}
    rows.sort(key=lambda r: r["id"])
    summary = {"meta": meta, "summary": summarize(rows) if rows else {}, "cases": rows,
               "contaminated": [r["id"] for r in rows if r.get("contaminated")],
               "note": ("scored summary only: prompts, answers and transcripts are not stored here (raw streams stay in "
                        f"runs/{run_id}/raw/, not committed)")}
    args.results.mkdir(parents=True, exist_ok=True)
    out = args.results / f"{run_id}.json"
    out.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "contaminated" if summary["contaminated"] else "done", "results": str(out),
                      "overall": summary["summary"].get("overall"), "cost_usd": summary["summary"].get("cost_usd")}))
    return 1 if summary["contaminated"] else 0


# --------------------------------------------------------------------------------------- baselines
def baseline_key(meta: dict) -> str:
    version = meta["cli_version"] if isinstance(meta["cli_version"], str) else "mixed"
    return f"{meta['cli']}-{version}-{meta['model']}"


def cmd_baseline(args) -> int:
    doc = json.loads(args.result.read_text(encoding="utf-8"))
    if not doc["meta"].get("full_set") and not args.allow_partial:
        raise EvalError("a baseline needs a full run of the case set (or --allow-partial)")
    if doc.get("contaminated"):
        raise EvalError("a contaminated run cannot be a baseline")
    args.baselines.mkdir(parents=True, exist_ok=True)
    out = args.baselines / f"{baseline_key(doc['meta'])}.json"
    out.write_text(json.dumps({"meta": doc["meta"], "cases": {r["id"]: {"strict": r["strict"], "lenient": r["lenient"],
                                                                         "outcome": r["outcome"]} for r in doc["cases"]}},
                              indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "written", "baseline": str(out)}))
    return 0


def compare(result: dict, base: dict) -> dict:
    now = {r["id"]: r for r in result["cases"]}
    then = base["cases"]
    common = sorted(set(now) & set(then))
    reg = [i for i in common if then[i]["strict"] and not now[i]["strict"]]
    fix = [i for i in common if not then[i]["strict"] and now[i]["strict"]]
    return {"compared": len(common), "regressions": reg, "fixed": fix, "new_cases": sorted(set(now) - set(then)),
            "not_run": sorted(set(then) - set(now)),
            "same_case_file": result["meta"].get("cases_file_sha256") == base["meta"].get("cases_file_sha256")}


def cmd_compare(args) -> int:
    doc = json.loads(args.result.read_text(encoding="utf-8"))
    path = args.baseline or args.baselines / f"{baseline_key(doc['meta'])}.json"
    if not Path(path).is_file():
        print(json.dumps({"status": "no-baseline", "expected": str(path)}))
        return 0
    rep = compare(doc, json.loads(Path(path).read_text(encoding="utf-8")))
    rep["status"] = "regression" if rep["regressions"] else "ok"
    print(json.dumps(rep, indent=1))
    return 1 if rep["regressions"] else 0


def cmd_estimate(args) -> int:
    cases, _ = load_cases(args.cases, args.ids.split(",") if args.ids else None, args.sample, args.seed)
    turns = sum(len(turns_of(c)) for c in cases)
    if args.per_turn_usd is not None:
        per = args.per_turn_usd
        source = "--per-turn-usd"
    else:
        if not args.from_result:
            raise EvalError("give --from RESULT.json or --per-turn-usd")
        doc = json.loads(args.from_result.read_text(encoding="utf-8"))
        rows = doc["cases"]
        per = sum(r["cost_usd"] for r in rows) / max(sum(len(r["turns"]) for r in rows), 1)
        source = f"{args.from_result.name} ({doc['meta']['model']}, {len(rows)} cases)"
    print(json.dumps({"cases": len(cases), "prompt_turns": turns, "usd_per_prompt_turn": round(per, 4),
                      "estimate_usd": round(per * turns, 2), "source": source}))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--cli", choices=("claude", "codex"), default="claude")
    r.add_argument("--cli-path", help="executable (default: found on PATH)")
    r.add_argument("--model", required=True, help="pinned model id; recorded and part of the baseline key")
    r.add_argument("--cases", type=Path, default=CASES)
    r.add_argument("--ids", help="comma-separated case ids")
    r.add_argument("--sample", type=int, help="a seeded random sample of N cases")
    r.add_argument("--seed", type=int, default=1)
    r.add_argument("--jobs", type=int, default=4)
    r.add_argument("--max-turns", type=int, default=6)
    r.add_argument("--case-budget-usd", type=float, default=0.5)
    r.add_argument("--budget-usd", type=float, default=5.0, help="no new case starts once this much is spent")
    r.add_argument("--case-timeout", type=float, default=600.0)
    r.add_argument("--isolation", choices=("setting-sources", "config-dir"), default="setting-sources")
    r.add_argument("--config-dir", type=Path, help="separate CLI configuration directory (implies config-dir isolation)")
    r.add_argument("--plugin-dir", type=Path, default=PLUGIN)
    r.add_argument("--out", type=Path, default=HERE / "runs")
    r.add_argument("--results", type=Path, default=HERE / "results")
    r.add_argument("--run-id")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--reuse-raw", action="store_true", help="resume a run: score raw streams already in runs/<run_id>/raw/")
    c = sub.add_parser("compare")
    c.add_argument("result", type=Path)
    c.add_argument("--baseline", type=Path)
    c.add_argument("--baselines", type=Path, default=HERE / "baselines")
    b = sub.add_parser("baseline")
    b.add_argument("result", type=Path)
    b.add_argument("--baselines", type=Path, default=HERE / "baselines")
    b.add_argument("--allow-partial", action="store_true")
    e = sub.add_parser("estimate")
    e.add_argument("--from", dest="from_result", type=Path)
    e.add_argument("--per-turn-usd", type=float)
    e.add_argument("--cases", type=Path, default=CASES)
    e.add_argument("--ids")
    e.add_argument("--sample", type=int)
    e.add_argument("--seed", type=int, default=1)
    args = ap.parse_args(argv)
    try:
        return {"run": cmd_run, "compare": cmd_compare, "baseline": cmd_baseline, "estimate": cmd_estimate}[args.command](args)
    except (EvalError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "rejected", "error": f"{type(exc).__name__}: {exc}"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
