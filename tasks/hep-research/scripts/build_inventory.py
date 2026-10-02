#!/usr/bin/env python3
"""M0 step 6: build integration-inventory.json and the first-draft migration-map.csv.

Dev tooling (outside the distributable plugin). Reads the legacy skills from a read-only
checkout of agentic-ai-skills ($LEGACY_REPO, default .legacy/agentic-ai-skills; see LEGACY_SOURCE.md)
and writes into this repository. Rules are a [Proposal] first draft;
M1 refines per-section ownership. Usage: python3 build_inventory.py [--commit HASH]
"""
import csv, hashlib, json, re, subprocess, sys
from pathlib import Path

import os
HERE = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
REPO = Path(os.environ.get("LEGACY_REPO", HERE / ".legacy" / "agentic-ai-skills"))
SKILLS = ["ams-analysis", "hep-analysis", "deep-learning", "academic-papers",
          "academic-diagrams", "agile-development", "task-authoring"]
DOCS = HERE / "plugins/hep-research/docs"
COMMIT = sys.argv[sys.argv.index("--commit") + 1] if "--commit" in sys.argv else \
    subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()

def ftype(p):
    parts = p.split("/")
    sub = parts[1] if len(parts) > 2 else ""
    name = parts[-1]
    if sub == "tests" and len(parts) > 3 and parts[2] == "grading": return "grading-rubric"
    if sub == "evals": return "eval-grader" if "graders" in parts else "eval-prompt"
    if name == "SKILL.md": return "entry-point"
    if name in {"README.md", "VALIDATION.md", "TODO.md", "REVIEWER_PACKET.md"}: return "skill-doc"
    if sub == "agents": return "host-metadata"
    if sub == "tests": return "test-fixture" if "fixtures" in parts else "test"
    return {"references": "reference", "scripts": "script", "data": "data", "assets": "asset",
            "templates": "template", "examples": "example"}.get(sub, "other")

# (skill, regex on path relative to skill, def_owner, impl_owner, destination, disposition, rationale)
R = [
 # exclusions first
 (None, r"^tests/grading/", "-", "-", "-", "retain-outside", "grading rubrics/answers are never distributed (2.1)"),
 (None, r"^evals/", "-", "-", "-", "retain-outside", "eval prompts and graders stay in dev repo; routing cases rebuilt in tests/routing (M5)"),
 (None, r"(^|/)TODO\.md$|REVIEWER_PACKET\.md$", "-", "-", "-", "retain-outside", "legacy dev tracking; not plugin content"),
 (None, r"^agents/openai\.yaml$", "-", "-", "-", "retain-outside", "non-Claude host metadata; D1 keeps other hosts out of v1 acceptance"),
 (None, r"^scripts/validate_skill_bundle\.py$", "hep-computing", "hep-computing", "tools/", "adapt", "per-skill bundle validator replaced by plugin validators + run_all_checks"),
 (None, r"^(README|VALIDATION)\.md$", "-", "-", "docs/migration.md", "retain-outside", "legacy snapshot docs; facts re-cited in plugin docs"),
 # ams-analysis
 ("ams-analysis", r"^SKILL\.md$", "hep-analysis", "hep-analysis", "skills/* + profiles/experiments/ams-02/index.md", "adapt", "split: general methods to core owners, AMS specifics to profile (4.1)"),
 ("ams-analysis", r"^data/(sources|claims)\.json$", "profile:ams-02", "core/evidence", "profiles/experiments/ams-02/evidence/", "adapt", "namespaced ams02: IDs with legacy mapping (M2)"),
 ("ams-analysis", r"^data/papers_manifest\.json$", "profile:ams-02", "research-communication", "profiles/experiments/ams-02/evidence/", "adapt", "acquisition metadata; no cached PDFs shipped"),
 ("ams-analysis", r"^references/source-policy\.md$", "research-communication", "core/evidence", "contracts/ + profiles/experiments/ams-02/evidence/", "merge", "shared evidence conventions; Section 12 date fixes"),
 ("ams-analysis", r"^references/source-index\.md$", "profile:ams-02", "core/evidence", "profiles/experiments/ams-02/evidence/", "adapt", "generated index; regenerate"),
 ("ams-analysis", r"^references/analysis-artifacts\.md$", "contracts", "contracts", "contracts/legacy/ + measurement extension", "adapt", "analysis contract -> measurement extension + converter; Section 12 YAML-doc fix"),
 ("ams-analysis", r"^references/(statistical-diagnostics|inference-and-unfolding)\.md$", "hep-statistics", "core/stats", "skills/hep-statistics/references + profile examples", "merge", "general inference to statistics; AMS examples stay in profile"),
 ("ams-analysis", r"^references/(detector-and-observables|reconstruction-and-data-quality|calibration-mc-systematics|efficiency-acceptance-backgrounds)\.md$", "detector-response", "detector-response", "profiles/experiments/ams-02/modules/", "adapt", "AMS subsystem/response modules"),
 ("ams-analysis", r"^references/", "profile:ams-02", "profile:ams-02", "profiles/experiments/ams-02/modules/", "adapt", "AMS physics modules (species, periods, databases)"),
 ("ams-analysis", r"^scripts/ams_kinematics\.py$", "hep-theory", "core/kinematics", "core/kinematics + profiles/experiments/ams-02/scripts", "adapt", "generic kinematics to core; AMS interpretation in profile; constants keep provenance"),
 ("ams-analysis", r"^scripts/(validate_response|validate_covariance)\.py$", "contracts", "core/stats", "core/ + contracts/", "adapt", "shared response/covariance contracts"),
 ("ams-analysis", r"^scripts/(likelihood_limits|template_fit|unfolding_diagnostics|poisson_diagnostics|statistical_toys)\.py$", "hep-statistics", "core/stats", "core/stats/", "reuse", "numerical diagnostics stewarded by hep-statistics; port tests"),
 ("ams-analysis", r"^scripts/(validate_evidence_ledger|render_source_index)\.py$", "research-communication", "core/evidence", "core/evidence/", "adapt", "shared evidence tools"),
 ("ams-analysis", r"^scripts/audit_analysis_spec\.py$", "contracts", "contracts", "contracts/legacy/", "adapt", "wrap under versioned contracts"),
 ("ams-analysis", r"^scripts/yaml_subset\.py$", "contracts", "contracts", "contracts/legacy/", "reuse", "strict YAML subset parser for legacy inputs (D6)"),
 ("ams-analysis", r"^scripts/(fetch_papers|crdb_query)\.py$", "research-communication", "profile:ams-02", "profiles/experiments/ams-02/scripts/", "adapt", "networked tools: opt-in only, never run implicitly (7.14); not in 4.1 map"),
 ("ams-analysis", r"^tests/fixtures/", "contracts", "contracts", "contracts/fixtures/legacy/", "reuse", "valid/invalid legacy fixtures"),
 ("ams-analysis", r"^tests/test_bundle\.py$", "-", "-", "-", "retire", "bundle structure test of legacy layout"),
 ("ams-analysis", r"^tests/", "same-as-code", "same-as-code", "tests/ (ported)", "reuse", "port with migrated code; record seeds/tolerances"),
 # hep-analysis
 ("hep-analysis", r"^SKILL\.md$", "hep-analysis", "hep-analysis", "skills/* (redistributed)", "adapt", "redistribute to core owners; Section 12 T12 fix"),
 ("hep-analysis", r"^references/(0[1-6]|10|12|47)-", "hep-analysis", "hep-analysis", "skills/hep-analysis/references", "adapt", "analysis design, backgrounds, systematics, validation"),
 ("hep-analysis", r"^references/(0[7-9]|37)-", "hep-statistics", "core/stats", "skills/hep-statistics/references", "adapt", "likelihood, inference, tools"),
 ("hep-analysis", r"^references/(1[4-7])-", "hep-computing", "hep-computing", "skills/hep-computing/references", "adapt", "ROOT design, build, debugging, python coding"),
 ("hep-analysis", r"^references/(11|20)-", "physics-ml", "physics-ml", "skills/physics-ml/references", "adapt", "ML in analysis"),
 ("hep-analysis", r"^references/27-", "hep-theory", "hep-computing", "skills/hep-theory/references + adapters/", "adapt", "event generation split per 7.3"),
 ("hep-analysis", r"^references/13-", "research-communication", "research-communication", "skills/research-communication/references", "adapt", "source list"),
 ("hep-analysis", r"^references/38-", "profile:ams-02", "profile:ams-02", "profiles/experiments/ams-02/modules/", "merge", "AMS case study belongs in profile"),
 ("hep-analysis", r"^references/(18|19|2[1-689]|3[0-69]|4[0-689]|50)-", "detector-response", "detector-response", "skills/detector-response/references", "adapt", "detector systems, reconstruction, calibration, astroparticle instruments"),
 ("hep-analysis", r"^assets/end_to_end_sample_analysis\.py$", "hep-analysis", "hep-computing", "profiles/experiments/synthetic-collider + examples/", "adapt", "starting point for synthetic-collider; no named-experiment claim"),
 ("hep-analysis", r"^assets/(pyroot_|cpp_|rdf_|fit_histogram|plot_branch|CMakeLists|uproot_)", "hep-computing", "adapter:root/uproot", "adapters/ (proposed)", "adapt", "optional-tool templates; adapters stay proposed until tested"),
 ("hep-analysis", r"^assets/(pyhf-counting|combine_datacard)", "hep-statistics", "adapter:pyhf/combine", "adapters/ (proposed)", "adapt", "optional statistics-tool templates"),
 ("hep-analysis", r"^assets/", "hep-analysis", "hep-analysis", "skills/hep-analysis/templates", "adapt", "configs/examples"),
 ("hep-analysis", r"^scripts/", "hep-analysis", "hep-computing", "skills/*/scripts or core/ (M2 per-script)", "adapt", "per-script owner decided in M2 inventory"),
 ("hep-analysis", r"^tests/", "same-as-code", "same-as-code", "tests/ (ported)", "reuse", "port with migrated code"),
 # deep-learning
 ("deep-learning", r"^references/scientific-machine-learning\.md$", "hep-theory", "physics-ml", "skills/physics-ml/references", "adapt", "ML/theory/statistics boundaries"),
 ("deep-learning", r"^scripts/check_split_integrity\.py$", "physics-ml", "physics-ml", "skills/physics-ml/scripts", "reuse", "grouped-split checks (T16)"),
 (None, r"^SKILL\.md$", None, None, None, "adapt", "entry point merged into new core skill"),
 ("deep-learning", r"", "physics-ml", "physics-ml", "skills/physics-ml/", "adapt", "PyTorch engineering under physics-ml"),
 # academic-papers
 ("academic-papers", r"^references/mathematical-reasoning-and-proof\.md$", "hep-theory", "hep-theory", "skills/hep-theory/references", "adapt", "canonical theory reasoning contract; Section 12 handoff fix"),
 ("academic-papers", r"^references/numerical-and-computational-methods\.md$", "hep-computing", "hep-computing", "skills/hep-computing/references", "adapt", "numerical reliability"),
 ("academic-papers", r"^references/statistical-inference-for-physics\.md$", "hep-statistics", "hep-statistics", "skills/hep-statistics/references", "merge", "inference belongs to statistics (Section 12)"),
 ("academic-papers", r"", "research-communication", "research-communication", "skills/research-communication/", "adapt", "literature, writing, citations"),
 ("academic-diagrams", r"", "research-communication", "research-communication", "skills/research-communication/ (diagram branch)", "adapt", "diagrams and captions"),
 ("agile-development", r"", "hep-computing", "hep-computing", "skills/hep-computing/references", "adapt", "engineering discipline references"),
 ("task-authoring", r"", "hep-computing", "hep-computing", "skills/hep-computing/references (research-task authoring)", "adapt", "confirm scope in M1"),
]
SKILL_DEFAULT = {"ams-analysis": "hep-analysis", "hep-analysis": "hep-analysis", "deep-learning": "physics-ml",
                 "academic-papers": "research-communication", "academic-diagrams": "research-communication",
                 "agile-development": "hep-computing", "task-authoring": "hep-computing"}

def classify(skill, rel):
    for s, rx, d, i, dest, disp, why in R:
        if s not in (None, skill) or not re.search(rx, rel): continue
        if d is None:
            o = SKILL_DEFAULT[skill]; return o, o, f"skills/{o}/SKILL.md", disp, why
        return d, i, dest, disp, why
    raise SystemExit(f"unclassified: {skill}/{rel}")

files = [p for p in subprocess.check_output(["git", "ls-files"], cwd=REPO, text=True).split("\n") if p]
inv, rows = [], []
for p in files:
    skill = p.split("/")[0] if p.split("/")[0] in SKILLS else None
    data = (REPO / p).read_bytes()
    if skill is None and not p.startswith(("README.md", "docs/", ".gitignore")): continue
    rec = {"path": p, "skill": skill or "(repo-root)", "type": ftype(p) if skill else "repo-doc",
           "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    inv.append(rec)
    if skill:
        d, i, dest, disp, why = classify(skill, p[len(skill) + 1:])
        rows.append([p, COMMIT, "(whole file)", d, i, dest, disp, "", "", why])
    elif p.startswith("docs/detector-principles/"):
        rows.append([p, COMMIT, "(whole file)", "detector-response", "detector-response",
                     "skills/detector-response/references (compare with hep-analysis 21-50)", "merge", "", "",
                     "not in 4.1 map; overlaps hep-analysis detector references 49/50"])
    elif p == "README.md":
        rows.append([p, COMMIT, "(whole file)", "-", "-", "docs/migration.md", "retain-outside", "", "", "baseline/compat docs"])

DOCS.mkdir(parents=True, exist_ok=True)
(DOCS / "integration-inventory.json").write_text(json.dumps(
    {"source_commit": COMMIT, "generated_by": "tasks/hep-research/scripts/build_inventory.py",
     "status": "[Confirmed] file facts; types are rule-derived", "files": inv}, indent=1) + "\n")
with open(DOCS / "migration-map.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow("source_path,source_commit,section_or_symbol,definition_owner,implementation_owner,destination,disposition,dependencies,tests,rationale".split(","))
    w.writerows(rows)
tracked7 = [p for p in files if p.split("/")[0] in SKILLS]
print(json.dumps({"tracked_in_7_skills": len(tracked7), "inventory": len(inv), "map_rows": len(rows),
                  "coverage_7_skills": sum(1 for r in inv if r["skill"] in SKILLS) / len(tracked7)}))
