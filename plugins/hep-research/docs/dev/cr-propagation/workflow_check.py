#!/usr/bin/env python3
"""Machine checks of the cr-propagation r4 workflow (orchestrator and verifier use; not a plugin tool).

Subcommands. The checker and workflow.json are trusted only from the integration branch: a verifier runs the
integration copy with --plugin-root pointing at the plugin root of the branch under test (default: this file's root).
  dag                     WF-1: workflow.json dependencies and capabilities defined, DAG acyclic, waves ordered.
  acceptance              WF-2 / ALL-2: acceptance.json still holds every entry frozen at P0, unchanged
                          (only new entries may be added); its frozen sha256 is the one in VALIDATION.md.
  diff --work-package ID --base REV ALL-5: every path changed since REV is in the WP's `files` or `common_files`,
                          and no orchestrator-only file changed (WF-5).
  gaps --base REV         ALL-4: tools/naming_known_gaps.json has no gap or waiver that REV lacks.

Prints one JSON object with a `status` key. Exit 0 ok, 1 check failed, 2 bad input. Standard library only.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_DIR = Path(__file__).resolve().parent
BRANCH_DOCS = "docs/dev/cr-propagation"
PLUGIN_PREFIX = "plugins/hep-research/"
TERMINAL_STATES = {"merged", "skipped", "blocked"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(PLUGIN_ROOT), *args], check=True, capture_output=True, text=True).stdout


def check_dag(workflow: dict) -> list[str]:
    problems = []
    packages = {wp["id"]: wp for wp in workflow["work_packages"]}
    if len(packages) != len(workflow["work_packages"]):
        problems.append("duplicate work-package id")
    capabilities = set(workflow["capabilities"])
    for wp in packages.values():
        for dep in wp.get("deps", []) + wp.get("soft_deps", []) + wp.get("merge_after", []) + wp.get("merge_before", []):
            if dep not in packages:
                problems.append(f"{wp['id']}: unknown work package {dep}")
            elif dep in wp.get("deps", []) and packages[dep]["wave"] > wp["wave"]:
                problems.append(f"{wp['id']}: dependency {dep} is in a later wave")
        for capability in wp.get("requires", []):
            if capability not in capabilities:
                problems.append(f"{wp['id']}: undefined capability {capability}")
    visiting, done = set(), set()

    def visit(node: str, path: list[str]) -> None:
        if node in done or node not in packages:
            return
        if node in visiting:
            problems.append("cycle: " + " -> ".join(path + [node]))
            return
        visiting.add(node)
        for dep in packages[node].get("deps", []) + packages[node].get("soft_deps", []):
            visit(dep, path + [node])
        visiting.discard(node)
        done.add(node)

    for node in packages:
        visit(node, [])
    return problems


def frozen_acceptance_text() -> str:
    """acceptance.json as committed by P0 (the first commit that added it)."""
    relative = "docs/dev/cr-propagation/acceptance.json"
    first = git("log", "--diff-filter=A", "--format=%H", "--", relative).split()
    if not first:
        raise ValueError("acceptance.json has no commit yet")
    return git("show", f"{first[-1]}:./{relative}")


def check_acceptance() -> tuple[list[str], dict]:
    problems = []
    frozen_text = frozen_acceptance_text()
    frozen_sha = hashlib.sha256(frozen_text.encode("utf-8")).hexdigest()
    validation = (PLUGIN_ROOT / "VALIDATION.md").read_text(encoding="utf-8")
    section = re.search(r"^## CRPROP-ACCEPTANCE.*?(?=^## |\Z)", validation, re.MULTILINE | re.DOTALL)
    if not section or frozen_sha not in section.group(0):
        problems.append(f"frozen sha256 {frozen_sha} not recorded in the CRPROP-ACCEPTANCE section of VALIDATION.md")
    frozen = {entry["id"]: entry for entry in json.loads(frozen_text)["entries"]}
    current = {entry["id"]: entry for entry in load_json(PLUGIN_ROOT / BRANCH_DOCS / "acceptance.json")["entries"]}
    for entry_id, entry in frozen.items():
        if entry_id not in current:
            problems.append(f"{entry_id}: deleted")
        elif current[entry_id] != entry:
            problems.append(f"{entry_id}: changed (only new, stricter entries may be added before H1)")
    return problems, {"frozen_sha256": frozen_sha, "frozen_entries": len(frozen), "added_entries": sorted(set(current) - set(frozen))}


def check_diff(workflow: dict, wp_id: str, base: str) -> tuple[list[str], list[str]]:
    packages = {wp["id"]: wp for wp in workflow["work_packages"]}
    if wp_id not in packages:
        raise ValueError(f"unknown work package {wp_id}")
    allowed = packages[wp_id].get("files", []) + workflow.get("common_files", [])
    orchestrator_only = set(workflow["shared_files"]["orchestrator_only"])
    changed = [line[len(PLUGIN_PREFIX):] if line.startswith(PLUGIN_PREFIX) else "../" + line
               for line in git("diff", "--name-only", f"{base}...HEAD").splitlines() if line]
    problems = []
    for path in changed:
        if path in orchestrator_only and packages[wp_id].get("role") != "orchestrator":
            problems.append(f"{path}: orchestrator-only file changed")
        elif not any(fnmatch.fnmatch(path, pattern) or path.startswith(pattern.rstrip("*")) and pattern.endswith("/**")
                     for pattern in allowed):
            problems.append(f"{path}: outside the WP's files")
    return problems, changed


def check_gaps(base: str) -> list[str]:
    before = json.loads(git("show", f"{base}:./tools/naming_known_gaps.json"))
    after = load_json(PLUGIN_ROOT / "tools/naming_known_gaps.json")

    def entries(document) -> set[str]:
        gaps = document.get("gaps", {})
        waivers = document.get("waivers", [])
        return ({"gap " + json.dumps(item, sort_keys=True) for item in (gaps.items() if isinstance(gaps, dict) else gaps)}
                | {"waiver " + json.dumps(item, sort_keys=True) for item in waivers})

    grown = entries(after) - entries(before)
    return [f"new known-gap entry: {item}" for item in sorted(grown)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("check", choices=["dag", "acceptance", "diff", "gaps"])
    parser.add_argument("--work-package", help="work-package id (diff)")
    parser.add_argument("--base", help="git revision the work package branched from (diff, gaps)")
    parser.add_argument("--plugin-root", type=Path, help="plugin root of the branch under test (default: this file's)")
    args = parser.parse_args()
    global PLUGIN_ROOT
    if args.plugin_root:
        PLUGIN_ROOT = args.plugin_root.resolve()
    try:
        workflow = load_json(WORKFLOW_DIR / "workflow.json")
        details: dict = {}
        if args.check == "dag":
            problems = check_dag(workflow)
            details = {"work_packages": len(workflow["work_packages"]), "capabilities": len(workflow["capabilities"])}
        elif args.check == "acceptance":
            problems, details = check_acceptance()
        elif args.check == "diff":
            if not (args.work_package and args.base):
                raise ValueError("diff needs --work-package and --base")
            problems, changed = check_diff(workflow, args.work_package, args.base)
            details = {"changed": changed}
        else:
            if not args.base:
                raise ValueError("gaps needs --base")
            problems = check_gaps(args.base)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "error", "check": args.check, "error": str(exc)}))
        return 2
    print(json.dumps({"status": "fail" if problems else "ok", "check": args.check, "problems": problems, **details}, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
