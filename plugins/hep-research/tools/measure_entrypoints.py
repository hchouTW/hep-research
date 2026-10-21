#!/usr/bin/env python3
"""Measure loading budgets: SKILL.md lines/bytes, description length, registry and
profile index sizes, and (when the Claude Code CLI is available) the host's always-on token estimate.

Budget (upgrade plan B-01): a SKILL.md above skill_bytes_target (12,288 bytes) is a warning, which
tools/budget_exceptions.json may waive ("<skill>:bytes": reason); above skill_bytes_max (16,384 bytes) or above
skill_lines_max (500 lines) it fails, with no exception. A description is at most 1,024 characters (the Agent Skills
specification, https://agentskills.io/specification) and the profile registry at most 3,072 bytes
(contracts/registry.py REGISTRY_BUDGET); a profile index.md above 4,096 bytes fails unless excepted ("<id>:index").
Each skill row also records its quick-question load (plan G13): SKILL.md plus its entry reference, the first reference
its Resources section links, against the 25,600-byte limit of B-03 (tests/skills/test_routing_tables.py fails above
it; here it is a warning), so the two halves of a split skill are measured separately.

Usage: python3 tools/measure_entrypoints.py [--no-cli] [--root PLUGIN_ROOT]
Exit 0 when nothing is over budget (warnings do not change it), 1 otherwise. Output: JSON with over_budget and
warnings.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUICK_LOAD_BYTES = 25600  # SKILL.md plus its entry reference (B-03)
ENTRY_REF = re.compile(r"\((references/[^)#\s]+\.md)")
BLOCK_SCALAR = re.compile(r"[>|][-+]?[1-9]?")


def skill_description(text: str) -> str:
    """The frontmatter description in full: a quoted or plain one-line value, or a folded/literal block ('>-', '|')
    or a plain value continued on indented lines, joined with single spaces (as YAML folds them, near enough)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"description:\s*(.*?)\s*$", line)
        if not m:
            continue
        head, cont = m.group(1), []
        for nxt in lines[i + 1:]:
            if nxt.strip() and not nxt[:1].isspace():
                break
            cont.append(nxt.strip())
        parts = cont if BLOCK_SCALAR.fullmatch(head) else [head, *cont]
        value = " ".join(p for p in parts if p)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value
    return ""


BUDGET = {"skill_bytes_target": 12288, "skill_bytes_max": 16384, "skill_lines_max": 500, "description_chars": 1024, "registry_bytes": 3072, "index_bytes": 4096}


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
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[args.index("--root") + 1]).resolve() if "--root" in args else ROOT
    exceptions_file = root / "tools" / "budget_exceptions.json"
    exceptions = json.loads(exceptions_file.read_text()) if exceptions_file.is_file() else {}
    rows, over, warnings = [], [], []
    for skill in sorted((root / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        desc = skill_description(text)
        row = {"skill": skill.parent.name, "lines": len(text.splitlines()), "bytes": len(text.encode()), "description_chars": len(desc)}
        entry = ENTRY_REF.search(text.split("## Resources", 1)[1]) if "## Resources" in text else None
        if entry and (skill.parent / entry.group(1)).is_file():
            row["entry_reference"] = entry.group(1)
            row["quick_load_bytes"] = row["bytes"] + (skill.parent / entry.group(1)).stat().st_size
            if row["quick_load_bytes"] > QUICK_LOAD_BYTES:
                warnings.append(f"{row['skill']} quick load {row['quick_load_bytes']} B (SKILL.md + {entry.group(1)}) > {QUICK_LOAD_BYTES}")
        rows.append(row)
        # hard limits: never waived
        for key, limit in (("bytes", BUDGET["skill_bytes_max"]), ("lines", BUDGET["skill_lines_max"]),
                           ("description_chars", BUDGET["description_chars"])):
            if row[key] > limit:
                over.append(f"{row['skill']} {key}={row[key]} > {limit}")
        if BUDGET["skill_bytes_target"] < row["bytes"] <= BUDGET["skill_bytes_max"] and f"{row['skill']}:bytes" not in exceptions:
            warnings.append(f"{row['skill']} bytes={row['bytes']} > target {BUDGET['skill_bytes_target']} "
                            "(warning; waive in tools/budget_exceptions.json with a reason)")
    reg = root / "profiles" / "registry.json"
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
        "registry_bytes": reg_bytes, "profile_index_bytes": indexes, "over_budget": over, "warnings": warnings,
        "exceptions": exceptions, "host_estimate": {"status": "skip", "reason": "--no-cli"} if "--no-cli" in args else cli_always_on(),
        "note": "Bytes are the main budget (SKILL.md paragraphs are unwrapped); lines are capped at 500.",
    }
    print(json.dumps(result, indent=1))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
