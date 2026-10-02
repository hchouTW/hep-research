#!/usr/bin/env python3
"""M2: copy the legacy AMS reference files into the ams-02 profile modules.

Content is copied verbatim except for path rewrites (scripts, ledger data,
source index) and, for tests-and-examples.md, removal of the grading
material (scoring rules, test suite, results record), which may not ship.
Reads $LEGACY_REPO (default .legacy/agentic-ai-skills).
"""
import csv
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEG = Path(os.environ.get("LEGACY_REPO", ROOT / ".legacy/agentic-ai-skills"))
L = LEG / "ams-analysis/references"
H = LEG / "hep-analysis/references"
M = ROOT / "plugins/hep-research/profiles/experiments/ams-02/modules"
R = "${CLAUDE_PLUGIN_ROOT}"
PROF = f"{R}/profiles/experiments/ams-02"
SK = f"{R}/skills/hep-analysis/scripts"
SCRIPT = {
    "ams_kinematics": f"{R}/core/kinematics/relativistic.py",
    "validate_response": f"{R}/core/stats/validate_response.py",
    "validate_covariance": f"{R}/core/stats/validate_covariance.py",
    "poisson_diagnostics": f"{R}/core/stats/poisson_diagnostics.py",
    "unfolding_diagnostics": f"{R}/core/stats/unfolding_diagnostics.py",
    "template_fit": f"{R}/core/stats/template_fit.py",
    "statistical_toys": f"{R}/core/stats/statistical_toys.py",
    "likelihood_limits": f"{R}/core/stats/likelihood_limits.py",
    "validate_evidence_ledger": f"{R}/core/evidence/ledger.py",
    "render_source_index": f"{R}/core/evidence/render_index.py",
    "yaml_subset": f"{R}/contracts/legacy/yaml_subset.py",
    "audit_analysis_spec": f"{PROF}/scripts/audit_analysis_spec.py",
    "crdb_query": f"{PROF}/scripts/crdb_query.py",
    "fetch_papers": f"{PROF}/scripts/fetch_papers.py",
}
for s in ("cosmic_ray_flux", "geomagnetic_cutoff", "orbit_averaged_geomagnetic_cutoff",
          "particle_ratio_with_uncertainty", "solar_modulation_force_field"):
    SCRIPT[s] = f"{SK}/{s}.py"


# legacy reference name -> module path inside modules/ (task M2.2: species, subsystems, methods, periods, evidence)
LAYOUT = {
    "charged-cosmic-rays": "species/charged-cosmic-rays.md",
    "antimatter-and-leptons": "species/antimatter-and-leptons.md",
    "nuclei-and-isotopes": "species/nuclei-and-isotopes.md",
    "detector-and-observables": "subsystems/detector-and-observables.md",
    "case-study-from-hep-analysis": "subsystems/instrument-overview.md",
    "reconstruction-and-data-quality": "methods/reconstruction-and-data-quality.md",
    "efficiency-acceptance-backgrounds": "methods/efficiency-acceptance-backgrounds.md",
    "calibration-mc-systematics": "methods/calibration-mc-systematics.md",
    "inference-and-unfolding": "methods/inference-and-unfolding.md",
    "statistical-diagnostics": "methods/statistical-diagnostics.md",
    "analysis-artifacts": "methods/analysis-artifacts.md",
    "worked-examples": "methods/worked-examples.md",
    "time-dependent-analysis": "periods/time-dependent-analysis.md",
    "source-policy": "sources/source-policy.md",
    "cosmic-ray-databases": "sources/cosmic-ray-databases.md",
    "working-rules": "working-rules.md",
}


def relink(t: str, here: str) -> str:
    """Rewrite links of a text written as if it sat flat in modules/ for its real location `here`."""
    depth = here.count("/")  # extra directory levels below modules/
    up = "../" * depth

    def mod(m):
        name = m.group(1)
        if name not in LAYOUT:
            return m.group(0)
        return f"]({up}{LAYOUT[name]}"
    t = re.sub(r"\]\(([\w-]+)\.md", mod, t)
    t = t.replace("](../evidence/", f"]({up}../evidence/").replace("](../index.md", f"]({up}../index.md")
    t = t.replace("](../../../../skills/", f"]({up}../../../../skills/")
    return t


def rw(t: str) -> str:
    t = re.sub(r"(?<![\w/$])scripts/(\w+)\.py", lambda m: SCRIPT[m.group(1)], t)
    t = re.sub(r"(?<![\w/])data/(sources|claims|papers_manifest)\.json", rf"{PROF}/evidence/\1.json", t)
    t = re.sub(r"(?<![\w/])tests/fixtures/(spec_valid\.(?:json|yaml))", rf"{PROF}/tests/fixtures/\1", t)
    t = re.sub(r"\((?:references/)?source-index\.md", "(../evidence/index.md", t)
    t = re.sub(r"`references/source-index\.md`", "`evidence/index.md`", t)
    t = re.sub(r"\(references/([\w-]+\.md)", r"(\1", t)
    t = t.replace("tests-and-examples.md", "worked-examples.md")
    t = re.sub(r"\[([^\]]*)\]\(\.\./VALIDATION\.md[^)]*\)",
               r"\1 (legacy ams-analysis VALIDATION.md at agentic-ai-skills@3e995a4)", t)
    return t


def worked_examples(t: str) -> str:
    lines = t.split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("## Scoring and evaluation rules"))
    # everything from the scoring rules on is evaluation material (rubric, test
    # suite, results, and the test-suite failure modes/questions): excluded.
    t = "\n".join(lines[:start]).rstrip() + "\n"
    t = t.replace("# Worked Examples, Behavioral Tests, and Results", "# Worked Examples")
    t = t.replace(", to run or extend the regression suite, or to record test results.", ".")
    t = re.sub(r"2\. \[Scoring and evaluation rules\][^\n]*\n3\. \[Test suite\][^\n]*\n"
               r"4\. \[Results record\][^\n]*\n5\.[^\n]*\n", "", t)
    return t


def hep_ref_destinations() -> dict:
    """hep-analysis reference file -> skill owning it after M2 (from docs/migration-map.csv)."""
    out = {}
    with open(ROOT / "plugins/hep-research/docs/migration-map.csv") as fh:
        for row in csv.DictReader(fh):
            src = row["source_path"]
            if src.startswith("hep-analysis/references/") and row["destination"].startswith("skills/"):
                out[src.rsplit("/", 1)[1]] = row["destination"].split("/")[1]
    return out


def case_study(t: str) -> str:
    dest = hep_ref_destinations()
    t = re.sub(r"\]\((\d\d-[\w-]+\.md)",
               lambda m: f"](../../../../skills/{dest[m.group(1)]}/references/{m.group(1)}", t)
    t = t.replace("use the `ams-analysis` skill if it is installed alongside this one**: it holds",
                  "use the rest of this profile ([index](../index.md))**: it holds")
    t = t.replace("is a `ams-analysis` / primary-paper\nquestion", "is a profile-evidence / primary-paper\nquestion")
    return t


def working_rules(t: str) -> str:
    """Legacy ams-analysis SKILL.md body -> modules/working-rules.md (the AMS-specific rules the
    seven core skills apply when this profile is active). Frontmatter goes to profile.json scope."""
    t = t.split("---\n", 2)[2].lstrip()
    t = t.replace("# AMS-02 Detector and Physics Analysis", "# AMS-02 Working Rules\n\n"
                  "## When to read this file\n\n"
                  "Read first whenever this profile is active: it holds the AMS-specific invariants, labels, "
                  "source rule and module routing. Migrated from the legacy `ams-analysis` skill; the general "
                  "workflow it describes is owned by the core skills, and this file adds the AMS constraints.", 1)
    t = t.replace("Guide realistic AMS-02", "This profile guides realistic AMS-02")
    t = t.replace("This skill does not replace", "This profile does not replace")
    t = t.replace("For generic ROOT/statistics/detector questions with no AMS tie, do not use this skill; use `hep-analysis` "
                  "(whose reference 38 is a brief AMS overview that this skill supersedes for depth).",
                  "For generic ROOT/statistics/detector questions with no AMS tie, do not load this profile; the core "
                  "skills answer them.")
    t = t.replace("this skill's index was last verified", "this profile's evidence index was last verified")
    t = t.replace("Run from the skill directory with `python3`", "Run with `python3` (paths below are absolute)")
    t = t.replace("| Maintainer regression only (contains grading rubrics; not needed to answer users) | - | `tests-and-examples` |",
                  "| See the intended behavior on representative requests | - | `worked-examples` |")
    t = t.replace("| [tests-and-examples](references/tests-and-examples.md) | Worked examples, behavioral tests, rubrics, results |",
                  "| [worked-examples](worked-examples.md) | Worked examples of the intended behavior |")
    t = t.replace("| [source-index](references/source-index.md) |", "| [evidence index](../evidence/index.md) |")
    t = t.replace("## Reference index", "## Module index")
    t = re.sub(r"\]\(references/([\w-]+\.md)\)", r"](\1)", t)
    t = t.replace("(generated from `data/*.json`)", "(generated from `evidence/*.json`)")
    t = t.replace("`scripts/validate_evidence_ledger.py`, `scripts/render_source_index.py`: check `data/sources.json` and "
                  "`data/claims.json` and keep `source-index` in sync.",
                  "`scripts/validate_evidence_ledger.py` (with `--namespace ams02`), `scripts/render_source_index.py`: check "
                  "`data/sources.json` and `data/claims.json` and keep the evidence index in sync.")
    t = re.sub(r"`source-index`", "the evidence index", t)
    names = "|".join(sorted((k for k in LAYOUT if k != "working-rules"), key=len, reverse=True))
    t = re.sub(rf"`({names})`", lambda m: f"[{m.group(1)}]({m.group(1)}.md)", t)
    return t


def evidence_index(t: str) -> str:
    """Legacy source-index.md prose -> evidence/index.md; the tables are regenerated afterwards."""
    t = t.replace("Read before quoting any AMS number", "Read before quoting any AMS number")
    t = t.replace("[source-policy](source-policy.md)", "[source-policy](../modules/sources/source-policy.md)")
    t = t.replace(
        "edit those files, run `python3 scripts/validate_evidence_ledger.py`, then "
        "`python3 scripts/render_source_index.py --write`",
        "edit those files, run `python3 core/evidence/ledger.py --sources S --claims C --namespace ams02`, then "
        "`python3 core/evidence/render_index.py --sources S --claims C --index I --write` (from the plugin root, "
        "with S, C, I the paths of `sources.json`, `claims.json` and this file)")
    t = t.replace("carry their own `access_date` in `data/sources.json`",
                  "carry their own `verification_date` in `sources.json`")
    t = t.replace("Only claims used by this skill.", "Only claims used by this profile.")
    t = re.sub(r"\(edit data/(sources|claims)\.json, then run scripts/render_source_index\.py --write\)",
               r"(edit \1.json, then run core/evidence/render_index.py --write)", t)
    t = t.replace("the skill supplies no counts", "the profile supplies no counts")
    t = t.replace("# Source Index and Claim-to-Source Map",
                  "# AMS-02 Evidence Index and Claim-to-Source Map\n\n"
                  "The generated tables use profile-qualified IDs (`ams02:S04`). The prose here and in the "
                  "profile modules uses the short form: `S04` means `ams02:S04`, `C20` means `ams02:C20`.")
    return rw(t)


def main() -> None:
    if M.exists() and "--force" not in sys.argv:
        # After the move commit, sci-fix commits edit the modules in place; a rerun would erase them.
        raise SystemExit(f"{M} exists: this script records the M2 move and would overwrite later sci-fix commits. "
                         "Use --force only to reproduce the move commit on a clean checkout.")
    n = 0
    if M.exists():
        shutil.rmtree(M)
    texts = {}
    for f in sorted(L.glob("*.md")):
        if f.name == "source-index.md":
            continue  # replaced by the generated evidence/index.md
        t = f.read_text()
        if f.name == "tests-and-examples.md":
            texts["worked-examples"] = worked_examples(t)
        else:
            texts[f.stem] = t
    texts["case-study-from-hep-analysis"] = case_study((H / "38-ams02-case-study.md").read_text())
    texts["working-rules"] = working_rules((LEG / "ams-analysis/SKILL.md").read_text())
    for name, t in texts.items():
        out = M / LAYOUT[name]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(relink(rw(t), LAYOUT[name]))
        n += 1
    ev = M.parent / "evidence/index.md"
    ev.write_text(evidence_index((L / "source-index.md").read_text()))
    # regenerate the tables from the migrated ledger so the index is never stale
    sys.path.insert(0, str(ROOT / "plugins/hep-research"))
    from core.evidence import ledger, render_index
    sources, claims = ledger.load_ledger(ev.parent / "sources.json", ev.parent / "claims.json")
    ev.write_text(render_index.write_index(ev.read_text(), sources, claims))
    print(f"wrote {n} modules to {M}")


if __name__ == "__main__":
    main()
