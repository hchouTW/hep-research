#!/usr/bin/env python3
"""Usage example for experiment:eic: select the profile through a project config and load resources selectively.

Builds a temporary project directory holding hep-research.project.json that pins experiment:eic, validates it with
contracts/project.py, then walks the profile's routing scenarios (benchmarks/routing-scenarios.json): for each
request it asks resolve_context for the decision and, only when experiment:eic is selected, opens the one module
the index names. Every file opened under profiles/ is recorded; the run fails if any file of another profile is
read. Also shows that a wrong version pin is rejected. Standard library only; no model call; nothing about the EIC
or ePIC is asserted here, only how the profile is selected and read.

Usage (from the plugin root): python3 examples/eic-profile-routing/run.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
PROFILE_DIR = PLUGIN / "profiles" / "experiments" / "eic"
OPENED: set[str] = set()


def _audit(event, args):
    if event == "open" and isinstance(args[0], (str, Path)):
        try:
            rel = Path(args[0]).resolve().relative_to(PLUGIN)
        except ValueError:
            return
        if rel.parts and rel.parts[0] == "profiles" and ".pyc" not in rel.name:  # bytecode-cache reads and writes are not profile reads
            OPENED.add(rel.as_posix())


sys.addaudithook(_audit)
sys.path.insert(0, str(PLUGIN))
from contracts.project import load_project, resolve_context  # noqa: E402

PROFILE = json.loads((PROFILE_DIR / "profile.json").read_text(encoding="utf-8"))
PLUGIN_VERSION = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def project_config(version: str) -> dict:
    return {"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0",
            "experiments": [{"profile": PROFILE["id"], "version": version}], "theory": []}


def write_project(tmp: Path, version: str) -> Path:
    d = tmp / f"project-{version}"
    d.mkdir()
    (d / "hep-research.project.json").write_text(json.dumps(project_config(version), indent=1) + "\n", encoding="utf-8")
    return d


def index_files(index_text: str, keyword: str) -> list[str]:
    for line in index_text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 2 and keyword and keyword.lower() in cells[0].lower():
            return re.findall(r"`([a-z0-9_./-]+\.(?:md|json))`", cells[1])
    return []


def run_scenarios() -> list[dict]:
    scenarios = json.loads((PROFILE_DIR / "benchmarks" / "routing-scenarios.json").read_text(encoding="utf-8"))["scenarios"]
    index_text = (PROFILE_DIR / "index.md").read_text(encoding="utf-8")
    out = []
    for s in scenarios:
        before = set(OPENED)
        # scenarios run without a project config on purpose: a pinned project would turn the generic DIS request
        # into 'use' through contracts/project.py semantics, which is not what the profile's routing table is
        # about; the project-config path is demonstrated separately in main()
        ctx = resolve_context({"experiments": s["explicit_profiles"], "theory": []}, None, s["needs_profile"])
        read = []
        if PROFILE["id"] in ctx["experiments"]:
            for rel in index_files(index_text, s["index_row_keyword"]):
                (PROFILE_DIR / rel).read_text(encoding="utf-8")   # selective load: only the named module
                read.append(rel)
        newly = sorted(p for p in OPENED - before if not p.endswith("index.md") and not p.endswith("routing-scenarios.json"))
        ok = ctx["decision"] == s["expected_decision"] and read == s["expected_eic_files"] and all(
            p.startswith("profiles/experiments/eic/") for p in newly)
        out.append({"id": s["id"], "request": s["request"], "decision": ctx["decision"], "source": ctx["source"],
                    "files_read": read, "expected_files": s["expected_eic_files"], "pass": ok})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eic-example-") as tmp:
        good = load_project(write_project(Path(tmp), PROFILE["version"]))
        bad = load_project(write_project(Path(tmp), "9.9.9"))
    wrong_pin_rejected = (not bad.report.ok) and any(f.code == "project.version_pin_mismatch" for f in bad.report.findings)
    scenarios = run_scenarios() if good.report.ok else []
    ctx = resolve_context({"experiments": [], "theory": []}, good, True)
    project_config_selection = {"decision": ctx["decision"], "source": ctx["source"], "experiments": ctx["experiments"]}
    project_selects = ctx["decision"] == "use" and ctx["source"] == "project-config" and ctx["experiments"] == ["experiment:eic"]
    files = sorted(OPENED)
    # load_project validates the whole registry, so every registered profile.json is read as metadata; that is not a load
    foreign = [p for p in files if not (p.startswith("profiles/experiments/eic/") or p == "profiles/registry.json" or p.endswith("/profile.json"))]
    passed = good.report.ok and wrong_pin_rejected and bool(scenarios) and all(s["pass"] for s in scenarios) and project_selects and not foreign
    results = {"plugin_version": PLUGIN_VERSION, "profile": {"id": PROFILE["id"], "version": PROFILE["version"]},
               "project_config": {k: project_config(PROFILE["version"])[k] for k in ("experiments", "theory")},
               "project_valid": good.report.ok, "bound_profiles": [p["id"] for p in good.profiles],
               "wrong_pin_rejected": wrong_pin_rejected, "project_config_selection": project_config_selection,
               "scenarios": scenarios, "profile_files_read": files,
               "foreign_profile_files_read": foreign, "pass": passed,
               "caveat": "Shows profile selection and selective loading only; asserts nothing about the EIC or ePIC."}
    (a.out / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    lines = ["# experiment:eic usage example", "", f"Profile {PROFILE['id']} {PROFILE['version']} selected through hep-research.project.json; wrong pin rejected: {wrong_pin_rejected}.", "",
             "| Scenario | Decision | Files read |", "|---|---|---|"]
    lines += [f"| {s['id']} | {s['decision']} | {', '.join(s['files_read']) or 'none'} |" for s in scenarios]
    lines += ["", f"Project config alone (request names no profile): decision {ctx['decision']}, source {ctx['source']}, experiments {', '.join(ctx['experiments'])}."]
    lines += ["", f"Profile files opened during the run: {', '.join(files)}.", "", results["caveat"]]
    (a.out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"pass": passed, "scenarios": [(s["id"], s["pass"]) for s in scenarios], "foreign": foreign}))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
