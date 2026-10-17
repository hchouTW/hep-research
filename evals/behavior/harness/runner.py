"""Run behavioral cases against a live agent host, or regrade recorded runs.

One run = one (case, arm, model, repeat). Each run gets a fresh project directory (the workspace) holding the case's
fixtures and project config, so runs cannot see each other's files. The transcript (stream-json), the workspace and a
meta record are kept under the run directory; grading reads only those, so a run can be regraded later with new
graders without paying for the model again (`regrade`).

Arms (the ablations that separate the layers):
  natural    plugin installed, nothing else: what users get
  forced     plugin installed, and the system prompt tells the agent to load the case's owner skill first:
             the ceiling with L1 solved; natural vs forced isolates selection from execution
  baseline   no plugin: what the skills add at all
  enforced   natural, plus the PreToolUse protection hook (hooks/protect_paths.py): L4 with host enforcement

Host: Claude Code headless (`claude -p --output-format stream-json --verbose`). The command template is in
HOST_COMMAND and can be replaced for another host whose transcript trace.py can parse.

Live runs call a paid model. `plan` prints the matrix and the run count; `run` needs --yes.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import cases as casemod
from . import fixtures
from .graders import GradeContext, grade_case
from .trace import Trace, load_trace, merge_turns

EVALS = Path(__file__).resolve().parents[1]
HOOK = EVALS / "hooks" / "protect_paths.py"
ARMS = ("natural", "forced", "baseline", "enforced")
DEFAULT_TOOLS = "Bash,Read,Write,Edit,Glob,Grep,Skill,WebFetch,WebSearch"

FORCE_TEMPLATE = ("Before you answer or run anything, load the skill hep-research:{skill} with the Skill tool and "
                  "follow its context-resolution steps.")


def plugin_fingerprint(plugin_root: Path) -> dict:
    """Version plus a hash of everything that steers behaviour: skill texts, descriptions, registry, profiles' index."""
    h = hashlib.sha256()
    files = sorted(list((plugin_root / "skills").glob("*/SKILL.md")) +
                   list((plugin_root / "skills").glob("*/references/*.md")) +
                   [plugin_root / "profiles" / "registry.json"] +
                   list((plugin_root / "profiles").glob("*/*/index.md")) +
                   list((plugin_root / "contracts" / "stanzas").glob("*.md")))
    for f in files:
        if f.exists():
            h.update(f.relative_to(plugin_root).as_posix().encode())
            h.update(f.read_bytes())
    version = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text())["version"]
    return {"version": version, "behavior_hash": h.hexdigest()[:16], "files": len(files)}


def write_workspace(case: dict, ws: Path, plugin_root: Path, arm: str) -> None:
    ws.mkdir(parents=True, exist_ok=True)
    for rel, content in (case.get("fixtures") or {}).items():
        dest = ws / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, dict) and "json" in content:
            dest.write_text(json.dumps(content["json"], indent=1, ensure_ascii=False), encoding="utf-8")
        elif isinstance(content, dict) and "from_plugin" in content:
            shutil.copyfile(plugin_root / content["from_plugin"], dest)
        elif isinstance(content, dict) and "generate" in content:
            dest.write_text(fixtures.generate(content), encoding="utf-8")
        else:
            dest.write_text(str(content), encoding="utf-8")
    if case.get("project"):
        cfg = dict(case["project"])
        cfg.setdefault("schema_version", "1.2.0")
        cfg.setdefault("plugin_version", plugin_fingerprint(plugin_root)["version"])
        (ws / "hep-research.project.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    claude_dir = ws / ".claude"
    claude_dir.mkdir(exist_ok=True)
    settings: dict = {}
    if arm == "enforced":
        (claude_dir / "protected-paths.json").write_text(json.dumps(
            {"globs": case.get("protected", []), "deny_writes": [".claude/**"]}, indent=1))
        settings["hooks"] = {"PreToolUse": [{"matcher": "*", "hooks": [
            {"type": "command", "command": f"{sys.executable} {HOOK}"}]}]}
    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=1))


def host_command(prompt: str, model: str, arm: str, case: dict, plugin_root: Path, opts: dict,
                 resume: str | None = None) -> list[str]:
    cmd = [opts.get("claude_bin", "claude"), "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--model", model, "--allowedTools", opts.get("allowed_tools", DEFAULT_TOOLS),
           "--max-turns", str(opts.get("max_turns", 40))]
    if arm != "baseline":
        cmd += ["--plugin-dir", str(plugin_root)]
    if arm == "forced":
        skill = case.get("force_skill") or casemod.first_expected_skill(case)
        if skill:
            cmd += ["--append-system-prompt", FORCE_TEMPLATE.format(skill=skill)]
    if resume:
        cmd += ["--resume", resume]
    elif not case.get("turns"):
        cmd += ["--no-session-persistence"]
    return cmd


def run_one(case: dict, arm: str, model: str, repeat: int, run_dir: Path, plugin_root: Path, opts: dict) -> dict:
    rdir = run_dir / case["id"] / arm / model.replace("/", "_") / f"r{repeat}"
    if (rdir / "grade.json").exists() and not opts.get("rerun"):
        return json.loads((rdir / "grade.json").read_text())
    if rdir.exists():
        shutil.rmtree(rdir)
    ws = rdir / "workspace"
    write_workspace(case, ws, plugin_root, arm)
    prompts = [t["prompt"] for t in case["turns"]] if case.get("turns") else [case["prompt"]]
    meta = {"case": case["id"], "layer": case["layer"], "arm": arm, "model": model, "repeat": repeat,
            "started": dt.datetime.now(dt.timezone.utc).isoformat(), "turns": []}
    session = None
    traces = []
    for t_no, prompt in enumerate(prompts):
        cmd = host_command(prompt, model, arm, case, plugin_root, opts, resume=session)
        t0 = time.time()
        try:
            p = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=opts.get("timeout", 900),
                               env={**os.environ, "HEP_EVAL_RUN": "1"})
            out, err, code = p.stdout, p.stderr, p.returncode
        except subprocess.TimeoutExpired as exc:
            out, err, code = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""), \
                "timeout", -9
        (rdir / f"transcript.t{t_no}.jsonl").write_text(out, encoding="utf-8")
        tr = load_trace(rdir / f"transcript.t{t_no}.jsonl")
        traces.append(tr)
        session = tr.meta.get("session_id") or session
        meta["turns"].append({"returncode": code, "seconds": round(time.time() - t0, 1), "stderr_tail": err[-2000:],
                              "argv": [a if a != prompt else "<prompt>" for a in cmd]})
        if code != 0:
            break
    meta["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (rdir / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    return grade_run(rdir, case, plugin_root)


def trace_for(rdir: Path) -> Trace:
    parts = sorted(rdir.glob("transcript.t*.jsonl"), key=lambda p: int(p.name.split(".t")[1].split(".")[0]))
    traces = [load_trace(p) for p in parts]
    return merge_turns(traces) if len(traces) > 1 else (traces[0] if traces else Trace())


def grade_run(rdir: Path, case: dict, plugin_root: Path) -> dict:
    meta = json.loads((rdir / "meta.json").read_text()) if (rdir / "meta.json").exists() else {}
    tr = trace_for(rdir)
    judge = json.loads((rdir / "judge.json").read_text()).get("scores") if (rdir / "judge.json").exists() else None
    ctx = GradeContext(trace=tr, case=case, workspace=rdir / "workspace", plugin_root=plugin_root, judge_scores=judge)
    verdict = grade_case(case, ctx)
    host_failed = any(t.get("returncode") not in (0, None) for t in meta.get("turns", []))
    expected = casemod.first_expected_skill(case)
    hep = tr.hep_skills()
    out = {"case": case["id"], "layer": case["layer"], "suite": case.get("suite"), "lang": case.get("lang", "en"),
           "kind": case.get("kind", ""), "arm": meta.get("arm"), "model": meta.get("model"),
           "repeat": meta.get("repeat"), "expected_skill": expected,
           "first_hep_skill": hep[0] if hep else None, "skills": tr.skills,
           "loaded_expected": bool(expected and expected in tr.skills),
           "host_error": host_failed, "trace": tr.summary(), **verdict}
    if host_failed:
        out["pass"] = False
        out.setdefault("unverified", []).append("host")
    (rdir / "grade.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


# ------------------------------------------------------------------ matrix
def plan(cases: list[dict], arms: list[str], models: list[str], repeats: int) -> list[tuple]:
    out = []
    for c in cases:
        for arm in arms:
            if c.get("arms") and arm not in c["arms"]:
                continue
            if arm == "enforced" and not c.get("protected"):
                continue
            if arm == "forced" and not (c.get("force_skill") or casemod.first_expected_skill(c)):
                continue
            if arm == "forced" and c["layer"] == "L1" and not casemod.binds_profile(c):
                continue    # forcing the load makes pure selection trivial; it is informative only for profile reads
            for m in models:
                for r in range(repeats):
                    out.append((c, arm, m, r))
    return out


def run_matrix(matrix: list[tuple], run_dir: Path, plugin_root: Path, opts: dict, jobs: int = 4) -> list[dict]:
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"created": dt.datetime.now(dt.timezone.utc).isoformat(), "plugin": plugin_fingerprint(plugin_root),
                "opts": {k: v for k, v in opts.items() if k != "claude_bin"}, "runs": len(matrix),
                "holdout": opts.get("holdout_record")}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    results = []
    with cf.ThreadPoolExecutor(max_workers=jobs) as pool:
        futs = {pool.submit(run_one, c, a, m, r, run_dir, plugin_root, opts): (c["id"], a, m, r) for c, a, m, r in matrix}
        for i, f in enumerate(cf.as_completed(futs), 1):
            key = futs[f]
            try:
                res = f.result()
            except Exception as exc:  # keep the campaign going; the failure is recorded as a host error
                res = {"case": key[0], "arm": key[1], "model": key[2], "repeat": key[3], "pass": False,
                       "host_error": True, "error": f"{exc.__class__.__name__}: {exc}"}
            results.append(res)
            mark = "PASS" if res.get("pass") else ("HOST" if res.get("host_error") else "fail")
            print(f"[{i}/{len(matrix)}] {mark} {key[0]} {key[1]} {key[2]} r{key[3]}", file=sys.stderr)
    return results


def regrade(run_dir: Path, case_index: dict, plugin_root: Path) -> list[dict]:
    """Regrade every recorded run with the current graders and case definitions (no model calls)."""
    out = []
    for meta_file in sorted(run_dir.glob("*/*/*/r*/meta.json")):
        rdir = meta_file.parent
        meta = json.loads(meta_file.read_text())
        case = case_index.get(meta["case"])
        if case is None:
            print(f"skip {meta['case']}: no longer defined", file=sys.stderr)
            continue
        out.append(grade_run(rdir, case, plugin_root))
    return out


def collect(run_dir: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(run_dir.glob("*/*/*/r*/grade.json"))]
