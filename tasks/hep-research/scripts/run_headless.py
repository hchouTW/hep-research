#!/usr/bin/env python3
"""G5 helper: run Claude Code headless (`claude -p --output-format stream-json`) and reduce each run to a trace.

Not part of the plugin. It must be run with CLAUDE_CONFIG_DIR pointing at an isolated config that has the plugin
installed; it never touches ~/.claude. Each run is a paid model call.

  run_headless.py invoke --prompt TEXT --cwd DIR --out trace.json [--max-turns N]
  run_headless.py routing --cases cases.json --cwd BASE_DIR (one fresh subdirectory per case) --out routing.json [--jobs 6] [--max-turns 4] [--ids a,b]

A trace records: host version, model, plugin path the host loaded, skills invoked (Skill tool), files read (with
whether each is inside the plugin and whether it is an experiment-profile file), permission denials, cost, result.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TOOLS = ["Read", "Glob", "Grep", "Skill"]
# host-session variables of the container this was run from; removed so the run sees only the isolated config
# (no inherited memory stores, extra directories, synced plugins or coordinator tools)
STRIP = ["CLAUDE_CODE_SESSION_ID", "CLAUDE_COWORK_MEMORY_PATH_OVERRIDE", "CLAUDE_MEMORY_STORES", "CLAUDE_ADDITIONAL_DIRECTORIES",
         "CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD", "CLAUDE_CODE_PROJECTS_SESSION", "CLAUDE_CODE_SYNC_SKILLS",
         "CLAUDE_CODE_SYNC_PLUGINS", "CLAUDE_CODE_SKILL_PROPOSALS", "CLAUDE_CODE_COORDINATOR_EXTRA_TOOLS",
         "CLAUDE_CODE_TERMINAL_MCP_TOOLS", "CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_AFTER_LAST_COMPACT",
         "CLAUDE_CODE_ARTIFACT_ASSETS", "DOCUMENTS_MCP_SCRATCH_ROOT"]
DENY = ["Bash", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Agent"]


def run(prompt: str, cwd: str, max_turns: int) -> dict:
    if "CLAUDE_CONFIG_DIR" not in os.environ or os.path.expanduser("~/.claude") == os.environ["CLAUDE_CONFIG_DIR"]:
        raise SystemExit("set CLAUDE_CONFIG_DIR to an isolated config directory")
    env = dict(os.environ)
    for k in STRIP:
        env.pop(k, None)
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--max-turns", str(max_turns),
           "--allowedTools", *TOOLS, "--disallowedTools", *DENY]
    proc = subprocess.run(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900)
    tr = {"prompt": prompt, "exit_code": proc.returncode, "skills_invoked": [], "files_read": [], "globs": [],
          "plugin_path": None, "model": None, "result": None, "cost_usd": None, "permission_denials": [],
          "stderr_tail": proc.stderr[-500:]}
    for line in proc.stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            tr["model"] = d.get("model")
            tr["host_version"] = d.get("claude_code_version")
            tr["memory_paths"] = d.get("memory_paths")
            tr["mcp_tools"] = [t for t in d.get("tools", []) if t.startswith("mcp")]
            for p in d.get("plugins", []):
                if p.get("name") == "hep-research":
                    tr["plugin_path"] = p.get("path")
        elif d.get("type") == "assistant":
            for c in d["message"].get("content", []):
                if c.get("type") != "tool_use":
                    continue
                if c["name"] == "Skill":
                    tr["skills_invoked"].append(c["input"].get("skill") or c["input"].get("command"))
                elif c["name"] == "Read":
                    tr["files_read"].append(c["input"].get("file_path"))
                elif c["name"] in ("Glob", "Grep"):
                    tr["globs"].append(c["input"])
        elif d.get("type") == "result":
            tr.update(result=d.get("result"), cost_usd=d.get("total_cost_usd"), subtype=d.get("subtype"),
                      num_turns=d.get("num_turns"), permission_denials=d.get("permission_denials", []))
    root = tr["plugin_path"] or "\0"
    tr["files_read_detail"] = [{"path": f, "inside_plugin": bool(f and f.startswith(root)),
                                "experiment_profile": bool(f and "/profiles/experiments/" in f)} for f in tr["files_read"]]
    return tr


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("invoke")
    a.add_argument("--prompt", required=True)
    b = sub.add_parser("routing")
    b.add_argument("--cases", type=Path, required=True)
    b.add_argument("--jobs", type=int, default=6)
    b.add_argument("--ids")
    for p in (a, b):
        p.add_argument("--cwd", required=True)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--max-turns", type=int, default=4)
    args = ap.parse_args(argv)
    if args.cmd == "invoke":
        tr = run(args.prompt, args.cwd, args.max_turns)
        args.out.write_text(json.dumps(tr, indent=1, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({k: tr[k] for k in ("plugin_path", "skills_invoked", "files_read", "cost_usd")}, indent=1))
        return 0
    doc = json.loads(args.cases.read_text(encoding="utf-8"))
    cases = doc["cases"] if isinstance(doc, dict) else doc
    if args.ids:
        keep = set(args.ids.split(","))
        cases = [c for c in cases if c["id"] in keep]
    def one(c):
        # a fresh project directory per case, holding the case's synthetic input files (if any)
        d = Path(args.cwd) / c["id"]
        d.mkdir(parents=True, exist_ok=False)
        for name, text in c.get("inputs", {}).items():
            (d / name).parent.mkdir(parents=True, exist_ok=True)
            (d / name).write_text(text, encoding="utf-8")
        return dict(run(c["prompt"], str(d), args.max_turns), case=c)
    with ThreadPoolExecutor(args.jobs) as ex:
        traces = list(ex.map(one, cases))
    args.out.write_text(json.dumps(traces, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(traces)} runs written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
