#!/usr/bin/env python3
"""hep-research behavioral evaluation: command line.

  validate   load every case (suites, routing table, optional held-out) and check them
  coverage   invariant registry vs plugin text vs cases; prints the enforcement gaps
  plan       print the run matrix, its size and one example command (no model calls)
  run        execute the matrix against the host (paid; needs --yes, --case-budget-usd and --budget-usd)
  regrade    regrade recorded runs with the current graders (no model calls)
  judge      score rubric criteria of recorded runs with a judge model (paid; same three flags)
  report     aggregate a run directory into report.md / report.json
  summarize  write the committable scored summary of a run (no prompts, answers or transcripts)
  compare    paired comparison of two run directories (A -> B)
  holdout    commit | verify | open | leaks for the blinded held-out suite
  power      planning numbers: runs needed for an interval or a paired comparison

Typical loop (from the repository root; the plugin defaults to plugins/hep-research)
  python3 evals/behavior/run.py validate && python3 evals/behavior/run.py coverage
  python3 evals/behavior/run.py plan --layers L1 --models claude-haiku-5-5 --sample 60
  python3 evals/behavior/run.py run --layers L1,L2 --arms natural,forced --models claude-sonnet-5-5 --repeats 3 \
      --case-budget-usd 0.5 --budget-usd 20 --yes
  python3 evals/behavior/run.py report --run evals/behavior/runs/<id>
  python3 evals/behavior/run.py summarize --run evals/behavior/runs/<id> --out evals/behavior/results/<id>.json

Exit codes: 0 ok, 1 findings (invalid cases, coverage gaps with --strict, failed gate, contaminated run), 2 usage.
Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from harness import cases as casemod  # noqa: E402
from harness import holdout, invariants, judge, report, runner, stats  # noqa: E402


def plugin_root(arg: str | None) -> Path:
    for cand in (arg, os.environ.get("HEP_PLUGIN_ROOT"), str(casemod.DEFAULT_PLUGIN)):
        if cand and (Path(cand) / "skills").is_dir() and (Path(cand) / ".claude-plugin").is_dir():
            return Path(cand).resolve()
    print("usage error: plugin root not found: pass --plugin-root or set HEP_PLUGIN_ROOT (the folder with skills/)",
          file=sys.stderr)
    sys.exit(2)


def load_all(args, root: Path) -> list[dict]:
    cs = casemod.load_suite_files(plugin_root=root)
    if not getattr(args, "no_routing", False):
        cs += casemod.import_routing(root)
    if getattr(args, "holdout", None):
        hcases = json.loads(Path(args.holdout).read_text(encoding="utf-8"))["cases"]
        for c in hcases:
            c.setdefault("suite", "holdout")
            c["tags"] = sorted(set(c.get("tags", [])) | {"holdout"})
        cs += hcases
    return cs


DEFAULT_MAX_TURNS = 40
PRESETS = {
    "selection": {"layers": "L1", "arms": "natural", "repeats": 3, "max_turns": 6},   # 6 as in evals/routing
    "boundary": {"layers": "L1,L2,L3", "bound_only": True, "arms": "natural,forced", "repeats": 3},
    "execution": {"layers": "L2", "arms": "natural,forced,baseline", "repeats": 3},
    "composition": {"layers": "L3", "arms": "natural,forced", "repeats": 3},
    "authority": {"layers": "L4", "arms": "natural,enforced", "repeats": 5},
    "release": {"layers": "L1,L2,L3,L4", "arms": "natural,forced,enforced", "repeats": 3},
}


def apply_preset(args):
    """A preset fills the selection and host options the user did not set on the command line."""
    if getattr(args, "preset", None):
        for k, v in PRESETS[args.preset].items():
            if getattr(args, k, None) in (None, False, "natural", 1) and v is not None:
                setattr(args, k, v)
    if hasattr(args, "max_turns") and args.max_turns is None:
        args.max_turns = DEFAULT_MAX_TURNS
    return args


def usage(msg: str) -> int:
    print(f"usage error: {msg}", file=sys.stderr)
    return 2


def _csv(v):
    return [x.strip() for x in v.split(",") if x.strip()] if v else None


def selected(args, root):
    apply_preset(args)
    cs = load_all(args, root)
    return casemod.select(cs, layers=_csv(args.layers), ids=args.ids, suites=_csv(args.suites), tags=_csv(args.tags),
                          langs=_csv(args.langs), sample=args.sample, seed=args.seed,
                          bound_only=getattr(args, "bound_only", False))


def cmd_validate(args):
    root = plugin_root(args.plugin_root)
    cs = load_all(args, root)
    errs = casemod.check_cases(cs, invariants.load_registry())
    by = {}
    for c in cs:
        by.setdefault(c["layer"], 0)
        by[c["layer"]] += 1
    widened = {c["id"]: c["allowed_tools"] for c in cs if c.get("allowed_tools")}
    print(json.dumps({"cases": len(cs), "by_layer": by, "widened_tools": widened, "errors": errs},
                     indent=1, ensure_ascii=False))
    return 1 if errs else 0


def cmd_coverage(args):
    root = plugin_root(args.plugin_root)
    cov = invariants.coverage(root, invariants.load_registry(), load_all(args, root))
    md = invariants.coverage_markdown(cov)
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
        (Path(args.out) / "coverage.md").write_text(md, encoding="utf-8")
        (Path(args.out) / "coverage.json").write_text(json.dumps(cov, indent=1, ensure_ascii=False))
    print(md)
    hard = cov["unregistered"] or cov["stale"] or cov["missing_paths"]
    return 1 if (hard or (args.strict and (cov["untested"] or cov["blocking_prose"]))) else 0


def _opts(args):
    return {"max_turns": args.max_turns, "timeout": args.timeout, "claude_bin": args.claude_bin,
            "allowed_tools": args.allowed_tools, "rerun": getattr(args, "rerun", False),
            "isolation": "config-dir" if args.config_dir else args.isolation, "config_dir": args.config_dir,
            "case_budget_usd": args.case_budget_usd, "budget_usd": getattr(args, "budget_usd", None)}


def _need_budgets(args) -> str | None:
    if args.case_budget_usd is None or args.budget_usd is None:
        return "paid calls need both --case-budget-usd (per run) and --budget-usd (total)"
    if args.case_budget_usd <= 0 or args.budget_usd <= 0:
        return "budgets must be positive"
    return None


def cmd_plan(args):
    root = plugin_root(args.plugin_root)
    apply_preset(args)
    cs = selected(args, root)
    m = runner.plan(cs, _csv(args.arms), _csv(args.models), args.repeats)
    by = {}
    for c, a, mo, _ in m:
        by[(c["layer"], a, mo)] = by.get((c["layer"], a, mo), 0) + 1
    print(json.dumps({"cases": len(cs), "runs": len(m), "by_layer_arm_model": {"|".join(k): v for k, v in by.items()},
                      "estimated_cost_usd": round(len(m) * args.cost_per_run, 2) if args.cost_per_run else None,
                      "plugin": runner.plugin_fingerprint(root)}, indent=1))
    if m:
        c, a, mo, _ = m[0]
        prompt = c["prompt"] if c.get("prompt") else c["turns"][0]["prompt"]
        print("example:", shlex.join(runner.host_command(prompt, mo, a, c, root, _opts(args))), file=sys.stderr)
    return 0


def cmd_run(args):
    root = plugin_root(args.plugin_root)
    if not args.yes:
        return usage("live runs call a paid model: add --yes (use `plan` first to see the size)")
    why = _need_budgets(args)
    if why:
        return usage(why)
    if args.holdout:
        if not (args.holdout_name and args.release):
            return usage("--holdout needs --holdout-name and --release (one opening per release is recorded)")
    apply_preset(args)
    opts = _opts(args)
    cs = selected(args, root)
    matrix = runner.plan(cs, _csv(args.arms), _csv(args.models), args.repeats)
    out = Path(args.out or HERE / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    if args.holdout:
        opts["holdout_record"] = holdout.open_suite(Path(args.holdout), args.holdout_name, args.release, str(out))
    res = runner.run_matrix(matrix, out, root, opts, jobs=args.jobs)
    man = json.loads((out / "manifest.json").read_text())
    rep = report.build(runner.collect(out), man)
    report.write(rep, out)
    contaminated = [r for r in res if r.get("contaminated")]
    print(json.dumps({"status": "contaminated" if contaminated else "done", "runs": len(res),
                      "planned": len(matrix), "stopped": man.get("stopped"), "spent_usd": man.get("spent_usd"),
                      "report": str(out / "report.md")}, indent=1))
    return 1 if contaminated else 0


def cmd_regrade(args):
    root = plugin_root(args.plugin_root)
    idx = {c["id"]: c for c in load_all(args, root)}
    rows = runner.regrade(Path(args.run), idx, root)
    print(f"regraded {len(rows)} runs")
    return 0


def cmd_judge(args):
    root = plugin_root(args.plugin_root)
    if not args.yes:
        return usage("judging calls a paid model: add --yes")
    why = _need_budgets(args)
    if why:
        return usage(why)
    idx = {c["id"]: c for c in load_all(args, root)}
    call = judge.cli_caller(args.judge_model, args.claude_bin, args.case_budget_usd,
                            "config-dir" if args.config_dir else args.isolation, args.config_dir)
    n, stopped = 0, None
    for meta_file in sorted(Path(args.run).glob("*/*/*/r*/meta.json")):
        rdir = meta_file.parent
        case = idx.get(json.loads(meta_file.read_text())["case"])
        if not case or not case.get("rubric") or ((rdir / "judge.json").exists() and not args.rerun):
            continue
        if call.spent >= args.budget_usd:
            stopped = f"budget: {call.spent:.4f} USD spent of {args.budget_usd:g}"
            break
        judge.judge_run(rdir, case, runner.trace_for(rdir), call, args.judge_model)
        runner.grade_run(rdir, case, root)
        n += 1
    print(json.dumps({"judged": n, "spent_usd": round(call.spent, 4), "stopped": stopped}, indent=1))
    return 0


def cmd_report(args):
    run = Path(args.run)
    man = json.loads((run / "manifest.json").read_text()) if (run / "manifest.json").exists() else {}
    cal = judge.calibrate(Path(args.labels), run) if args.labels else None
    rep = report.build(runner.collect(run), man, cal)
    report.write(rep, Path(args.out) if args.out else run)
    print(report.to_markdown(rep))
    if args.gate:
        return gate(rep, json.loads(Path(args.gate).read_text()))
    return 0


def gate(rep: dict, thresholds: dict) -> int:
    """Release gate: thresholds on lower confidence bounds, so a small sample cannot pass by luck.
    {"L1_loaded_expected_low": {"claude-sonnet-5-5": 0.9}, "max_blocking_failures": 0, "L4_enforced_leak_high": 0.0}"""
    fails = []
    for model, lo in thresholds.get("L1_loaded_expected_low", {}).items():
        s = rep["L1_selection"].get(model)
        if s and s["loaded_expected"][1] < lo:
            fails.append(f"L1 {model}: lower bound {s['loaded_expected'][1]:.3f} < {lo}")
    if "max_blocking_failures" in thresholds and len(rep["blocking_failures"]) > thresholds["max_blocking_failures"]:
        fails.append(f"{len(rep['blocking_failures'])} blocking failures > {thresholds['max_blocking_failures']}")
    for k, v in rep["L4"].items():
        if k.startswith("enforced|") and v["leaked_sealed_value"][0] > thresholds.get("L4_enforced_leak_high", 0.0):
            fails.append(f"L4 {k}: sealed value leaked in {v['leaked_sealed_value'][0]:.3f} of runs")
    print(json.dumps({"gate": "fail" if fails else "pass", "findings": fails}, indent=1))
    return 1 if fails else 0


def cmd_summarize(args):
    run = Path(args.run)
    man = json.loads((run / "manifest.json").read_text()) if (run / "manifest.json").exists() else {}
    doc = report.summary(runner.collect(run), man, args.run_id or run.name)
    out = Path(args.out) if args.out else HERE / "results" / f"{args.run_id or run.name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "summary": str(out), "runs": len(doc["runs"]), "cost_usd": doc["cost_usd"],
                      "contaminated": len(doc["contaminated"])}, indent=1))
    return 0


def cmd_compare(args):
    a, b = runner.collect(Path(args.a)), runner.collect(Path(args.b))
    cmp = report.compare(a, b)
    md = report.compare_markdown(cmp)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    print(md)
    return 0


def cmd_holdout(args):
    root = plugin_root(args.plugin_root)
    p = Path(args.file)
    if args.action == "commit":
        print(json.dumps(holdout.commit(p, args.name, args.author), indent=1))
    elif args.action == "verify":
        print(json.dumps(holdout.verify(p, args.name), indent=1))
    elif args.action == "leaks":
        found = holdout.leaks(p, holdout.skill_descriptions(root), args.ngram)
        print(json.dumps({"leaks": found}, indent=1, ensure_ascii=False))
        return 1 if found else 0
    elif args.action == "open":
        print(json.dumps(holdout.open_suite(p, args.name, args.release, "manual"), indent=1))
    return 0


def cmd_power(args):
    out = {"interval": {f"p={p}": {f"±{h}": stats.n_for_interval(p, h) for h in (0.1, 0.05, 0.03)}
                        for p in (0.3, 0.6, 0.9, 0.95)},
           "paired_mcnemar": {f"discordant={d}": {f"effect={e}": stats.n_for_paired(d, e)
                                                  for e in (0.05, 0.1, 0.2) if e < d}
                              for d in (0.1, 0.2, 0.3)}}
    print(json.dumps(out, indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plugin-root")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def sel(p):
        p.add_argument("--layers")
        p.add_argument("--suites")
        p.add_argument("--ids", help="regex on case id")
        p.add_argument("--tags")
        p.add_argument("--langs")
        p.add_argument("--sample", type=int)
        p.add_argument("--seed", type=int, default=20261017)
        p.add_argument("--holdout", help="held-out suite file (kept outside the repository)")
        p.add_argument("--no-routing", action="store_true", help="skip the routing-table import")
        p.add_argument("--bound-only", action="store_true", help="only cases whose project binds a profile")

    def isolation(p):
        p.add_argument("--isolation", choices=runner.ISOLATIONS, default="setting-sources",
                       help="setting-sources: the user's login without user settings, instructions or plugins")
        p.add_argument("--config-dir", help="a separate, logged-in CLAUDE_CONFIG_DIR (implies --isolation config-dir)")
        p.add_argument("--case-budget-usd", type=float, help="per run (or judge call); passed as --max-budget-usd")

    def host(p):
        p.add_argument("--arms", default="natural")
        p.add_argument("--models", default="claude-sonnet-5-5")
        p.add_argument("--repeats", type=int, default=1)
        p.add_argument("--max-turns", type=int, default=None,
                       help=f"default {DEFAULT_MAX_TURNS}; the selection preset uses 6")
        p.add_argument("--timeout", type=int, default=900)
        p.add_argument("--claude-bin", default="claude")
        p.add_argument("--allowed-tools", default=runner.DEFAULT_TOOLS)
        p.add_argument("--preset", choices=sorted(PRESETS), help="campaign preset (layers, arms, repeats)")
        isolation(p)

    p = sub.add_parser("validate"); sel(p); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("coverage"); sel(p); p.add_argument("--out"); p.add_argument("--strict", action="store_true")
    p.set_defaults(fn=cmd_coverage)
    p = sub.add_parser("plan"); sel(p); host(p); p.add_argument("--cost-per-run", type=float, default=0.0)
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("run"); sel(p); host(p)
    p.add_argument("--out"); p.add_argument("--jobs", type=int, default=4); p.add_argument("--yes", action="store_true")
    p.add_argument("--budget-usd", type=float, help="total; no new run starts once it is spent")
    p.add_argument("--rerun", action="store_true"); p.add_argument("--holdout-name"); p.add_argument("--release")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("regrade"); sel(p); p.add_argument("--run", required=True); p.set_defaults(fn=cmd_regrade)
    p = sub.add_parser("judge"); sel(p); p.add_argument("--run", required=True)
    p.add_argument("--judge-model", default="claude-opus-5-5"); p.add_argument("--claude-bin", default="claude")
    p.add_argument("--yes", action="store_true"); p.add_argument("--rerun", action="store_true")
    isolation(p); p.add_argument("--budget-usd", type=float, help="total for this judge pass")
    p.set_defaults(fn=cmd_judge)
    p = sub.add_parser("report"); p.add_argument("--run", required=True); p.add_argument("--out")
    p.add_argument("--labels", help="human labels CSV for judge calibration")
    p.add_argument("--gate", help="thresholds JSON (release gate)"); p.set_defaults(fn=cmd_report)
    p = sub.add_parser("summarize"); p.add_argument("--run", required=True); p.add_argument("--out")
    p.add_argument("--run-id"); p.set_defaults(fn=cmd_summarize)
    p = sub.add_parser("compare"); p.add_argument("--a", required=True); p.add_argument("--b", required=True)
    p.add_argument("--out"); p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("holdout"); p.add_argument("action", choices=["commit", "verify", "open", "leaks"])
    p.add_argument("--file", required=True); p.add_argument("--name", default="holdout-1")
    p.add_argument("--author", default=""); p.add_argument("--release", default="")
    p.add_argument("--ngram", type=int, default=4); p.set_defaults(fn=cmd_holdout)
    p = sub.add_parser("power"); p.set_defaults(fn=cmd_power)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
