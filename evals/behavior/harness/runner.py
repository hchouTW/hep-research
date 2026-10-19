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

Host: Claude Code headless (`claude -p --output-format stream-json --verbose`). The command is built by
host_command and can be replaced for another host whose transcript trace.py can parse.

Isolation (the same two modes as evals/routing/run_routing_eval.py; recorded in the manifest):
  setting-sources  the user's login with --setting-sources project,local: user settings, user instructions and
                   user-enabled plugins do not load; the workspace's own .claude/settings.json (the enforced arm's
                   hook) still does
  config-dir       CLAUDE_CONFIG_DIR points at a separate, logged-in configuration
Every command adds --strict-mcp-config. A run whose session reports a plugin other than hep-research (or reports
hep-research in the baseline arm) is contaminated: it fails, and the campaign stops. Plugins built into the CLI
("path": "builtin") are recorded, not counted.

Live runs call a paid model. `plan` prints the matrix and the run count; `run` needs --yes and both budgets:
--case-budget-usd (passed to the host as --max-budget-usd) and --budget-usd (no new run starts once the total spent
reaches it). A rerun into the same --out reuses every graded run; their earlier cost does not count against
--budget-usd, so the budget covers only the runs still missing.
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import cases as casemod
from . import fixtures
from .graders import GradeContext, grade_case
from .trace import Trace, load_trace, merge_turns

EVALS = Path(__file__).resolve().parents[1]
HOOK = EVALS / "hooks" / "protect_paths.py"
ARMS = ("natural", "forced", "baseline", "enforced")
DEFAULT_TOOLS = "Bash,Read,Write,Edit,Glob,Grep,Skill"
WEB_TOOLS = ("WebFetch", "WebSearch")   # denied unless a case lists them in allowed_tools
PLUGIN_NAME = "hep-research"
ISOLATIONS = ("setting-sources", "config-dir")

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


def allowed_tools(case: dict, opts: dict) -> list[str]:
    tools = [t for t in (opts.get("allowed_tools") or DEFAULT_TOOLS).split(",") if t]
    return tools + [t for t in case.get("allowed_tools", []) if t not in tools]


def host_command(prompt: str, model: str, arm: str, case: dict, plugin_root: Path, opts: dict,
                 resume: str | None = None) -> list[str]:
    tools = allowed_tools(case, opts)
    budget = opts.get("case_budget_usd")
    cmd = [opts.get("claude_bin", "claude"), "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--model", model, "--allowedTools", ",".join(tools), "--max-turns", str(opts.get("max_turns") or 40),
           "--max-budget-usd", f"{budget:g}" if budget is not None else "<case-budget-usd>", "--strict-mcp-config"]
    denied = [t for t in WEB_TOOLS if t not in tools]
    if denied:
        cmd += ["--disallowedTools", ",".join(denied)]
    if opts.get("isolation", "setting-sources") == "setting-sources":
        cmd += ["--setting-sources", "project,local"]
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


def session_dir(ws: Path, opts: dict) -> Path:
    """The folder the Claude CLI keeps for a working directory (sessions, auto memory)."""
    root = Path(opts["config_dir"]) if opts.get("config_dir") else \
        Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return root / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(ws.resolve()))


def _builtin(p) -> bool:
    return isinstance(p, dict) and (p.get("path") == "builtin" or str(p.get("source", "")).endswith("@builtin"))


def contamination(tr: Trace, arm: str | None) -> str | None:
    """Why a run is not a measurement of this plugin alone, or None."""
    names = sorted({p.get("name") if isinstance(p, dict) else str(p) for p in tr.meta.get("plugins") or []
                    if not _builtin(p)})
    extra = [n for n in names if n != PLUGIN_NAME]
    if extra:
        return f"other plugins loaded: {', '.join(extra)}"
    if arm == "baseline" and PLUGIN_NAME in names:
        return "hep-research loaded in the baseline arm"
    return None


def outside_roots(plugin_root: Path) -> list[Path]:
    """Folders whose new top-level entries count as writes outside the workspace: the home folder, ~/hep-work,
    ~/.venvs and the repository holding the plugin (where earlier runs left scratch folders and virtual environments)."""
    home = Path.home()
    roots = [home, home / "hep-work", home / ".venvs"]
    repo = plugin_root.resolve().parents[1]
    if (repo / ".git").exists():
        roots.append(repo)
    return [r for r in roots if r.is_dir()]


def outside_writes(roots: list[Path], since: float, text: str) -> list[str]:
    """New top-level entries of roots created at or after `since` that this run names (in its commands or tool
    inputs, so concurrent runs are not blamed for each other's files); hidden entries of the home folder are skipped.
    Paths are written with ~ for the home folder."""
    home = Path.home()
    found = []
    for root in roots:
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        for e in entries:
            if root == home and e.name.startswith("."):
                continue
            try:
                st = e.lstat()
            except OSError:
                continue
            born = getattr(st, "st_birthtime", st.st_ctime)
            rel = e.relative_to(home) if e.is_relative_to(home) else None
            if born >= since and (str(e) in text or (rel is not None and
                                                     (f"~/{rel}" in text or f"$HOME/{rel}" in text))):
                found.append(str(e).replace(str(home), "~", 1))
    return sorted(set(found))


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
    env = {**os.environ, "HEP_EVAL_RUN": "1"}
    if opts.get("config_dir"):
        env["CLAUDE_CONFIG_DIR"] = str(opts["config_dir"])
    sdir = session_dir(ws, opts)
    sdir_existed = sdir.exists()
    started = time.time()
    for t_no, prompt in enumerate(prompts):
        cmd = host_command(prompt, model, arm, case, plugin_root, opts, resume=session)
        t0 = time.time()
        try:
            p = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=opts.get("timeout", 900), env=env)
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
        if code != 0 or contamination(tr, arm):
            break
    # the CLI keeps a folder per working directory; remove the one this run's workspace created
    if not sdir_existed and sdir.name.endswith("-workspace") and sdir.is_dir():
        shutil.rmtree(sdir, ignore_errors=True)
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in rdir.glob("transcript.t*.jsonl"))
    meta["outside_writes"] = outside_writes(outside_roots(plugin_root), started - 1, text)
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
    # Reaching --max-turns is the model's behavior under a declared limit, not a host failure; the graders judge it.
    turn_limit = tr.meta.get("subtype") == "error_max_turns"
    host_failed = not turn_limit and any(t.get("returncode") not in (0, None) for t in meta.get("turns", []))
    expected = casemod.first_expected_skill(case)
    hep = tr.hep_skills()
    out = {"case": case["id"], "layer": case["layer"], "suite": case.get("suite"), "lang": case.get("lang", "en"),
           "kind": case.get("kind", ""), "arm": meta.get("arm"), "model": meta.get("model"),
           "repeat": meta.get("repeat"), "expected_skill": expected,
           "first_hep_skill": hep[0] if hep else None, "skills": tr.skills,
           "loaded_expected": bool(expected and expected in tr.skills),
           "host_error": host_failed, "turn_limit": turn_limit, "cost_usd": tr.meta.get("total_cost_usd") or 0.0,
           "cli_version": tr.meta.get("cli_version"), "contaminated": contamination(tr, meta.get("arm")),
           "outside_writes": meta.get("outside_writes"),
           "trace": tr.summary(), **verdict}
    if host_failed:
        out["pass"] = False
        out.setdefault("unverified", []).append("host")
    if out["contaminated"]:
        out["pass"] = False
        out.setdefault("unverified", []).append("isolation")
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


def _git(plugin_root: Path) -> dict:
    def g(*a):
        return subprocess.run(["git", "-C", str(plugin_root), *a], capture_output=True, text=True, check=False).stdout.strip()
    return {"commit": g("rev-parse", "HEAD") or None, "dirty": bool(g("status", "--porcelain", "--", "."))}


class CampaignLocked(RuntimeError):
    """Another live campaign is writing to the same run directory."""


def _lock(run_dir: Path) -> Path:
    """Take run_dir/.campaign.lock (pid inside), or raise CampaignLocked while the process that holds it is alive.
    Two campaigns in one folder delete and regrade each other's runs (2026-10-19), so the second is refused."""
    lock = run_dir / ".campaign.lock"
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                pid = int(lock.read_text().strip() or 0)
                os.kill(pid, 0)
            except (ValueError, ProcessLookupError, OSError):
                lock.unlink(missing_ok=True)  # stale: its process is gone
                continue
            raise CampaignLocked(f"{run_dir} is in use by campaign pid {pid}; wait for it or pick another --out")
        with os.fdopen(fd, "w") as fh:
            fh.write(str(os.getpid()))
        return lock
    raise CampaignLocked(f"cannot take {lock}")


def run_matrix(matrix: list[tuple], run_dir: Path, plugin_root: Path, opts: dict, jobs: int = 4) -> list[dict]:
    """Run the matrix. No new run starts once opts["budget_usd"] is spent or a run is contaminated; the stop and
    the number of runs completed are recorded in manifest.json. One campaign at a time per run directory."""
    run_dir.mkdir(parents=True, exist_ok=True)
    held = _lock(run_dir)
    try:
        return _run_matrix(matrix, run_dir, plugin_root, opts, jobs)
    finally:
        held.unlink(missing_ok=True)


def _run_matrix(matrix: list[tuple], run_dir: Path, plugin_root: Path, opts: dict, jobs: int) -> list[dict]:
    manifest = {"created": dt.datetime.now(dt.timezone.utc).isoformat(), "plugin": plugin_fingerprint(plugin_root),
                "plugin_git": _git(plugin_root), "isolation": opts.get("isolation", "setting-sources"),
                "opts": {k: v for k, v in opts.items() if k not in ("claude_bin", "config_dir", "holdout_record")},
                "allowed_tools_default": (opts.get("allowed_tools") or DEFAULT_TOOLS).split(","),
                "runs": len(matrix), "holdout": opts.get("holdout_record")}
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    budget = opts.get("budget_usd")
    lock = threading.Lock()
    state = {"spent": 0.0, "stop": None, "reused": 0}

    def task(c, a, m, r):
        with lock:
            if state["stop"] is None and budget is not None and state["spent"] >= budget:
                state["stop"] = f"budget: {state['spent']:.4f} USD spent of {budget:g}"
            if state["stop"]:
                return None
        # a run graded by an earlier campaign in run_dir is reused; its cost was spent then, not against this budget
        cached = (not opts.get("rerun")
                  and (run_dir / c["id"] / a / m.replace("/", "_") / f"r{r}" / "grade.json").exists())
        res = run_one(c, a, m, r, run_dir, plugin_root, opts)
        with lock:
            if cached:
                state["reused"] += 1
            else:
                state["spent"] += res.get("cost_usd") or 0.0
            if res.get("contaminated") and not state["stop"]:
                state["stop"] = f"contaminated: {c['id']} {a} {m} r{r}: {res['contaminated']}"
        return res

    results = []
    with cf.ThreadPoolExecutor(max_workers=jobs) as pool:
        futs = {pool.submit(task, c, a, m, r): (c["id"], a, m, r) for c, a, m, r in matrix}
        for i, f in enumerate(cf.as_completed(futs), 1):
            key = futs[f]
            try:
                res = f.result()
            except Exception as exc:  # keep the campaign going; the failure is recorded as a host error
                res = {"case": key[0], "arm": key[1], "model": key[2], "repeat": key[3], "pass": False,
                       "host_error": True, "error": f"{exc.__class__.__name__}: {exc}"}
                rdir = run_dir / key[0] / key[1] / key[2].replace("/", "_") / f"r{key[3]}"
                try:  # no grade.json is written, so a rerun into run_dir repeats this run
                    rdir.mkdir(parents=True, exist_ok=True)
                    (rdir / "host_error.txt").write_text(res["error"] + "\n", encoding="utf-8")
                except OSError:
                    pass
            if res is None:
                continue
            results.append(res)
            mark = "PASS" if res.get("pass") else ("HOST" if res.get("host_error") else "fail")
            print(f"[{i}/{len(matrix)}] {mark} {key[0]} {key[1]} {key[2]} r{key[3]}", file=sys.stderr)
    manifest.update({"completed": len(results), "skipped": len(matrix) - len(results), "reused": state["reused"],
                     "spent_usd": round(state["spent"], 4), "stopped": state["stop"],
                     "cli_versions": sorted({r["cli_version"] for r in results if r.get("cli_version")})})
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    if state["stop"]:
        print(f"stopped: {state['stop']} ({len(results)} of {len(matrix)} runs completed)", file=sys.stderr)
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
