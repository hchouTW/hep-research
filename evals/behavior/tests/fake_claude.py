#!/usr/bin/env python3
"""A scripted stand-in for `claude -p --output-format stream-json`, so the whole pipeline (workspace, arms, hook,
transcript, grading, report) is tested without a model.

Behaviour is set by FAKE_POLICY:
  good   loads the skill its keyword table picks (or the one a forced system prompt names), reads a bound profile's
         index, runs a plausible script, and for prompts about protected data tries to read protected/full_spectrum.csv
  lazy   answers immediately with no tool use
FAKE_PLUGINS (JSON list) is reported as the init event's plugins (default: hep-research when --plugin-dir is given),
FAKE_COST as each run's total_cost_usd (default 0), so the contamination and budget stops can be tested.
The protected read goes through the PreToolUse hook exactly when the workspace's .claude/settings.json configures it,
so the natural and enforced arms differ the way they would on the real host.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

KEYWORDS = [("limit|CLs|interval|combine|fit", "hep-statistics"), ("efficien|tag-and-probe|response|migration", "hep-detector"),
            ("correction chain|spec|blinding", "hep-measurement"), ("BDT|classifier|split", "hep-ml"),
            ("cross section|dsigma|decay|envelope", "hep-theory"), ("citation", "hep-literature"), ("abstract|blog", "hep-writing"),
            ("CMake|chunk|script", "hep-computing")]


def emit(obj):
    print(json.dumps(obj), flush=True)


def arg(flag):
    a = sys.argv
    return a[a.index(flag) + 1] if flag in a else None


def main():
    prompt = arg("-p") or ""
    plugin = arg("--plugin-dir")
    forced = arg("--append-system-prompt") or ""
    cwd = Path.cwd()
    policy = os.environ.get("FAKE_POLICY", "good")
    default_plugins = [{"name": "hep-research", "path": plugin}] if plugin else []
    plugins = json.loads(os.environ["FAKE_PLUGINS"]) if os.environ.get("FAKE_PLUGINS") else default_plugins
    emit({"type": "system", "subtype": "init", "model": arg("--model"), "session_id": "fake-session",
          "plugins": plugins, "claude_code_version": "0.0.0-fake"})
    n = 0

    def tool(name, inp, result, is_error=False):
        nonlocal n
        n += 1
        tid = f"toolu_{n}"
        emit({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}})
        emit({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": result,
                                                       "is_error": is_error}]}})

    def hooked(name, inp):
        settings = cwd / ".claude" / "settings.json"
        hooks = json.loads(settings.read_text()).get("hooks") if settings.exists() else None
        if not hooks:
            return True, ""
        cmd = hooks["PreToolUse"][0]["hooks"][0]["command"]
        p = subprocess.run(cmd, shell=True, input=json.dumps({"tool_name": name, "tool_input": inp, "cwd": str(cwd)}),
                           capture_output=True, text=True)
        return p.returncode == 0, p.stderr

    if policy == "good" and plugin:
        m = re.search(r"hep-research:([a-z-]+)", forced)
        skill = m.group(1) if m else next((s for rx, s in KEYWORDS if re.search(rx, prompt, re.I)), None)
        if skill:
            tool("Skill", {"skill": f"hep-research:{skill}"}, f"Loaded {skill}")
        cfg = cwd / "hep-research.project.json"
        if cfg.exists():
            reg = {p["id"]: p["path"] for p in json.loads((Path(plugin) / "profiles" / "registry.json").read_text())["profiles"]}
            c = json.loads(cfg.read_text())
            for e in c.get("experiments", []) + c.get("theory", []):
                if e["profile"] in reg:
                    idx = Path(plugin) / "profiles" / reg[e["profile"]] / "index.md"
                    tool("Read", {"file_path": str(idx)}, idx.read_text()[:400])
        if skill == "hep-statistics":
            tool("Bash", {"command": f"python3 {plugin}/core/stats/poisson_diagnostics.py cls-limit --n 0 --b 0.8"},
                 '{"status": "ok", "upper_limit": 3.0}')
        if re.search(r"protected|peek|signal-region|full spectrum|完整", prompt, re.I):
            target = "protected/full_spectrum.csv"
            ok, why = hooked("Read", {"file_path": target})
            if ok and (cwd / target).exists():
                tool("Read", {"file_path": target}, (cwd / target).read_text())
            else:
                tool("Read", {"file_path": target}, why or "denied", is_error=True)
        answer = ("Using the CLs construction with the background as a nuisance, the limit is computed by the shipped "
                  "tool; zero counts need exact treatment, so no Gaussian approximation is used. This is synthetic.")
    else:
        answer = "The answer is 42."
    emit({"type": "assistant", "message": {"content": [{"type": "text", "text": answer}]}})
    emit({"type": "result", "subtype": "success", "result": answer, "num_turns": n + 1, "total_cost_usd": float(os.environ.get("FAKE_COST", "0")),
          "session_id": "fake-session"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
