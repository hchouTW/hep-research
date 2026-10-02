#!/usr/bin/env python3
"""M2: per-file placement plan for the legacy skill content that goes into the seven core skills.

Writes tasks/hep-research/m2/redistribution/plan.csv (source_path, destination, disposition, note)
from docs/migration-map.csv plus the M2 per-script decisions below. `destination` is relative to
plugins/hep-research/. Workers moving files and rewriting links use this one table.
"""
import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEG = Path(os.environ.get("LEGACY_REPO", ROOT / ".legacy/agentic-ai-skills"))
MAP = ROOT / "plugins/hep-research/docs/migration-map.csv"
OUT = ROOT / "tasks/hep-research/m2/redistribution/plan.csv"

LEGACY_TO_SKILL = {"academic-papers": "research-communication", "academic-diagrams": "research-communication",
                   "agile-development": "hep-computing", "task-authoring": "hep-computing",
                   "deep-learning": "physics-ml", "hep-analysis": "hep-analysis"}
HEP_SCRIPTS = {  # M2 per-script owners (sibling imports stay inside one skill)
    "hep-analysis": ["check_systematic_variations", "make_yield_table", "counting_reference", "cosmic_ray_flux",
                     "geomagnetic_cutoff", "orbit_averaged_geomagnetic_cutoff", "particle_ratio_with_uncertainty",
                     "solar_modulation_force_field", "cr_spectrum_powerlaw_fit"],
    "detector-response": ["calorimeter_resolution", "cherenkov_angle", "pid_separation_power", "multiple_scattering",
                          "tag_and_probe_efficiency", "pileup_reweight", "xmax_gaisser_hillas"],
    "hep-statistics": ["li_ma_significance"],
    "hep-computing": ["audit_histograms", "summarize_histogram_statistics", "compare_root_histograms", "inspect_root_file",
                      "roofit_workspace_summary", "check_root_cpp_env", "new_root_cpp_project", "make_synthetic_nanoaod"],
}
SCRIPT_OWNER = {s: k for k, v in HEP_SCRIPTS.items() for s in v}
ADAPTER = {"adapter:root/uproot": "adapters/root-uproot/assets", "adapter:pyhf/combine": "adapters/pyhf-combine/assets"}


def plan_row(r):
    src, dest, disp = r["source_path"], r["destination"], r["disposition"]
    parts = src.split("/")
    top, kind, rest = parts[0], parts[1] if len(parts) > 1 else "", "/".join(parts[2:])
    if top in ("ams-analysis", "README.md") or disp in ("retain-outside", "retire"):
        return None  # handled already (AMS) or not shipped (recorded in the migration map)
    base = parts[-1]
    if top == "docs":
        name = "detector-principles-bibliography.md" if base == "references.md" else base
        return ("skills/detector-response/references/" + name, "move", "detector principles merged into detector-response references")
    skill = LEGACY_TO_SKILL[top]
    if kind == "SKILL.md":
        return (f"skills/{skill}/references/{top}-guide.md", "move+path-edit",
                "legacy SKILL.md body as a guide; frontmatter dropped, links rewritten")
    if kind == "references":
        owner = dest.split("/")[1] if dest.startswith("skills/") else skill
        return (f"skills/{owner}/references/{base}", "move+path-edit", "")
    if kind == "scripts":
        stem = base.rsplit(".", 1)[0]
        if stem == "validate_skill_bundle" and top != "task-authoring":
            return ("-", "retire", "legacy bundle validator; superseded by `claude plugin validate --strict`, tools/check_layering.py and tools/measure_entrypoints.py")
        if top == "hep-analysis":
            return (f"skills/{SCRIPT_OWNER[stem]}/scripts/{base}", "move+path-edit", "M2 per-script owner")
        return (f"skills/{skill}/scripts/{base}", "move+path-edit",
                "library of lint_task.py" if stem == "validate_skill_bundle" else "")
    if kind == "assets" and top == "hep-analysis":
        impl = r["implementation_owner"]
        if impl in ADAPTER:
            return (f"{ADAPTER[impl]}/{base}", "move", "adapter asset; adapter status proposed until tested (AC23)")
        if dest.startswith("profiles/"):
            return ("-", "deferred", "goes to profiles/experiments/synthetic-collider and examples/ in M3")
        return (f"skills/hep-analysis/templates/{base}", "move+path-edit", "")
    if kind in ("assets", "templates", "examples"):
        return (f"skills/{skill}/{kind}/{rest}", "move+path-edit", "")
    if kind == "tests":
        return ("(worker decides)", "port|retire|retain-outside", "see brief: unit tests port to tests/skills/<skill_underscore>/")
    return ("(unplanned)", "?", "")


def main():
    rows = list(csv.DictReader(open(MAP)))
    out, seen = [], {}
    for r in rows:
        p = plan_row(r)
        if p is None:
            continue
        if p[0] not in ("-", "(worker decides)") and p[0] in seen:
            raise SystemExit(f"collision: {r['source_path']} and {seen[p[0]]} -> {p[0]}")
        seen[p[0]] = r["source_path"]
        out.append({"source_path": r["source_path"], "destination": p[0], "disposition": p[1], "note": p[2]})
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["source_path", "destination", "disposition", "note"])
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} rows -> {OUT}")


if __name__ == "__main__":
    main()
