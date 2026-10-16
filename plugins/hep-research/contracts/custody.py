#!/usr/bin/env python3
"""Custody inventory of the profiles a project sees (v6.3 D12b, V30; companion transition stage 1, C15).

Stage 1 is inventory and report only: no profile field is required, nothing is refused or allowed because of this
report, and the loading rules of contracts/registry.py and contracts/project.py are unchanged. Each profile of the
visible closure gets an origin and a custody status:

- plugin: listed in the plugin's public registry; public by origin (a fact of where it is shipped).
- run-time-local: a folder given at run time with --local, as a companion plugin's <plugin>:profile does; known
  controlled, with its custody metadata missing (unverified, custody.metadata_missing).
- project-local: a folder in the project's local_profile_paths; custody unknown (unverified, custody.unknown).

A missing custody_domain is never read as public, and an unknown status is never downgraded to public, even when the
profile's content looks public. An unknown source is kept apart from a known-controlled one with missing metadata. A
declared custody_domain (no profile schema accepts one yet) would be listed as declared and stay unverified at
stage 1; equal values are never merged into one policy. custody_domain expresses controlled ownership, never
authorization. Rejected profiles keep their rejection codes.

Usage: python3 contracts/custody.py PROJECT_DIR [--local DIR ...]
Exit codes: 0 report written; 2 unreadable project or bad usage. Output: JSON with a status key.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.registry import PLUGIN_ROOT, load_registry  # noqa: E402

STAGE = 1
CONFIG_NAME = "hep-research.project.json"


def _row(pid: str, prof: dict, origin: str, rejected: list[str]) -> dict:
    declared = prof.get("custody_domain")
    if origin == "plugin":
        custody, state, reason = "public", "satisfied", "custody.public_by_origin"
    elif declared is not None:
        custody, state, reason = f"declared:{declared}", "unverified", "custody.stage1_report_only"
    elif origin == "run-time-local":
        custody, state, reason = "controlled-metadata-missing", "unverified", "custody.metadata_missing"
    else:
        custody, state, reason = "unknown", "unverified", "custody.unknown"
    return {"profile": pid, "origin": origin, "custody_domain": declared, "custody": custody, "state": state,
            "reason": reason, "rejected": rejected}


def inventory(project, extra_local=(), registry_path=None) -> dict:
    """The custody rows of every profile the project's closure loads (the public registry, local_profile_paths and
    run-time --local folders); ValueError when the project config cannot be read."""
    project = Path(project)
    cfg_path = project / CONFIG_NAME if project.is_dir() else project
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"cannot read the project config {cfg_path}: {exc}") from None
    if not isinstance(cfg, dict):
        raise ValueError(f"{cfg_path} is not a JSON object")
    project_dirs = [(cfg_path.parent / str(rel)).resolve() for rel in cfg.get("local_profile_paths", []) or []]
    run_time = [Path(d).resolve() for d in extra_local or []]
    res = load_registry(registry_path, project_dirs + [d for d in run_time if d not in project_dirs])
    plugin = Path(registry_path or PLUGIN_ROOT / "profiles" / "registry.json").resolve().parent

    def origin(prof: dict) -> str:
        d = Path(str(prof.get("_dir", ""))).resolve()
        if d in run_time:
            return "run-time-local"
        if d in project_dirs:
            return "project-local"
        return "plugin" if plugin == d or plugin in d.parents else "project-local"
    rows = [_row(pid, prof, origin(prof), res.rejected.get(pid, [])) for pid, prof in sorted(res.every_profile.items())]
    return {"status": "report", "stage": STAGE, "profiles": rows,
            "counts": {k: sum(r["custody"] == k for r in rows) for k in sorted({r["custody"] for r in rows})},
            "note": "stage 1: inventory and report only; custody metadata never authorizes use, a missing value is "
                    "never public, and no loading rule or refusal changes"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("project", type=Path)
    ap.add_argument("--local", dest="run_time_dirs", type=Path, action="append", default=[],
                    help="a profile folder supplied at run time")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        out = inventory(args.project, args.run_time_dirs)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "usage", "error": str(exc)}, indent=1))
        return 2
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
