#!/usr/bin/env python3
"""A stand-in for `claude -p ... --output-format stream-json`: emits a canned stream so the harness can be tested
without model calls. The FAKE_ROUTES file maps a prompt substring to the skills the fake session loads (in order) and
the final text; FAKE_PLUGINS lists the plugins the init event reports; FAKE_COST is the cost of each call. Every
call's arguments are appended to FAKE_LOG."""
import json
import os
import sys
import uuid

argv = sys.argv[1:]
prompt = argv[argv.index("-p") + 1]
session = argv[argv.index("--resume") + 1] if "--resume" in argv else str(uuid.uuid4())
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(argv) + "\n")
with open(os.environ["FAKE_ROUTES"], encoding="utf-8") as fh:
    routes = json.load(fh)
skills, text = [], "Here is the answer."
for key, (sk, tx) in routes.items():
    if key in prompt:
        skills, text = sk, tx
        break
plugins = [{"name": p, "path": "/x"} for p in os.environ.get("FAKE_PLUGINS", "hep-research").split(",") if p]
print(json.dumps({"type": "system", "subtype": "init", "session_id": session, "model": argv[argv.index("--model") + 1],
                  "claude_code_version": "9.9.9", "plugins": plugins, "tools": ["Skill", "Read"]}))
for s in skills:
    print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": s}}]}}))
    if s.endswith("hep-analysis"):
        print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read",
              "input": {"file_path": "/plug/profiles/experiments/x/index.md"}}]}}))
print("not json: progress line")
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 2,
                  "total_cost_usd": float(os.environ.get("FAKE_COST", "0.05")), "result": text, "session_id": session}))
