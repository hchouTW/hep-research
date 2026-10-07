#!/usr/bin/env python3
"""Measure loading budgets: SKILL.md lines/bytes, description length, registry and
profile index sizes, and (when the Claude Code CLI is available) the host's always-on token estimate.

Usage: python3 tools/measure_entrypoints.py [--no-cli]
Exit 0 within budget or documented exception, 1 otherwise. Output: JSON.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUDGET = {"skill_bytes": 8192, "skill_lines_max": 180, "description_chars": 1024, "registry_bytes": 2048, "index_bytes": 4096}
EXCEPTIONS = ROOT / "tools" / "budget_exceptions.json"


def cli_always_on() -> dict:
    exe = shutil.which("claude")
    if not exe:
        return {"status": "skip", "reason": "claude CLI not found"}
    try:
        out = subprocess.run([exe, "--plugin-dir", str(ROOT), "plugin", "details", "hep-research"],
                             capture_output=True, text=True, timeout=60, cwd=str(ROOT.parent)).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "skip", "reason": str(exc)}
    m = re.search(r"Always-on:\s*~?([\d,]+)\s*tok", out)
    per = {k: int(v.replace(",", "").replace(".", "")) for k, v in re.findall(r"^\s{2}([a-z-]+)\s+~([\d,.]+)\s", out, re.M)}
    if not m:
        return {"status": "skip", "reason": "could not parse `claude plugin details` output"}
    return {"status": "measured", "always_on_tokens": int(m.group(1).replace(",", "")), "per_skill_always_on": per,
            "source": "claude --plugin-dir <root> plugin details hep-research (host estimate)"}


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    exceptions = json.loads(EXCEPTIONS.read_text()) if EXCEPTIONS.is_file() else {}
    rows, over = [], []
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        m = re.search(r'^description:\s*"?(.*?)"?\s*$', text, re.M)
        desc = m.group(1) if m else ""
        row = {"skill": skill.parent.name, "lines": text.count("\n"), "bytes": len(text.encode()), "description_chars": len(desc)}
        rows.append(row)
        for key, limit in (("bytes", BUDGET["skill_bytes"]), ("lines", BUDGET["skill_lines_max"]), ("description_chars", BUDGET["description_chars"])):
            if row[key] > limit and f"{row['skill']}:{key}" not in exceptions:
                over.append(f"{row['skill']} {key}={row[key]} > {limit}")
    reg = ROOT / "profiles" / "registry.json"
    reg_bytes = reg.stat().st_size
    if reg_bytes > BUDGET["registry_bytes"]:
        over.append(f"registry {reg_bytes} B > {BUDGET['registry_bytes']}")
    indexes = {}
    for e in json.loads(reg.read_text())["profiles"]:
        idx = reg.parent / e["path"] / "index.md"
        if idx.is_file():
            indexes[e["id"]] = idx.stat().st_size
            if indexes[e["id"]] > BUDGET["index_bytes"] and f"{e['id']}:index" not in exceptions:
                over.append(f"{e['id']} index.md {indexes[e['id']]} B > {BUDGET['index_bytes']}")
    result = {
        "ok": not over, "budget": BUDGET, "skills": rows,
        "totals": {"skill_bytes": sum(r["bytes"] for r in rows), "description_chars": sum(r["description_chars"] for r in rows)},
        "registry_bytes": reg_bytes, "profile_index_bytes": indexes, "over_budget": over,
        "exceptions": exceptions, "host_estimate": {"status": "skip", "reason": "--no-cli"} if "--no-cli" in args else cli_always_on(),
        "note": "Line counts are informative: SKILL.md paragraphs are unwrapped, so bytes are the binding budget.",
    }
    print(json.dumps(result, indent=1))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
