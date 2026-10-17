"""The invariant registry: every rule the skills state, where it is enforced, and what tests it.

Sources of rules
  skills/*/SKILL.md            bullets under "## Invariants"
  contracts/stanzas/context-resolution.md   numbered steps (shared by all seven skills)
  cross-layer rules            defined only in evals/invariants.json (selection, handoff, blinding input side)

Each registry entry (evals/invariants.json):
  id, skill, source, match        match = a prefix of the rule text; ties the entry to the bullet
  severity                       blocking | major
  plane                          where it is enforced today: knowledge (prose only) | mechanism (a script or
                                 validator the agent can run) | authority (outside the agent's control)
  target_plane                   where it should be enforced (the gap is the work list)
  enforced_by                    scripts or validators that check it (paths in the plugin)
  deterministic_tests            test modules that exercise those mechanisms
  depends_on_skill_loaded        true when nothing checks it unless the agent loaded the skill

`coverage` cross-checks the registry against the plugin text and the behavioral cases and prints the gaps:
  unregistered     a rule in the text with no entry (a new bullet must be registered)
  stale            an entry whose text no longer exists
  untested         no behavioral case and no deterministic test
  blocking_prose   severity blocking, plane knowledge
  load_dependent   severity blocking and depends_on_skill_loaded
  plane_gap        plane below target_plane
  missing_paths    enforced_by / deterministic_tests paths that do not exist in the plugin
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .cases import EVALS, REPO, _walk_specs, all_expects

PLANE_RANK = {"knowledge": 0, "mechanism": 1, "authority": 2}


def extract_rules(plugin_root: Path) -> list[dict]:
    out = []
    for f in sorted((plugin_root / "skills").glob("*/SKILL.md")):
        inside = False
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                inside = line.strip() == "## Invariants"
                continue
            if inside and line.startswith("- "):
                out.append({"skill": f.parent.name, "source": f"skills/{f.parent.name}/SKILL.md", "text": line[2:].strip()})
    stanza = plugin_root / "contracts" / "stanzas" / "context-resolution.md"
    if stanza.exists():
        for line in stanza.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\d+\.\s+(.*)", line)
            if m:
                out.append({"skill": "*", "source": "contracts/stanzas/context-resolution.md", "text": m.group(1).strip()})
    return out


def load_registry(path: Path | None = None) -> dict:
    doc = json.loads((path or EVALS / "invariants.json").read_text(encoding="utf-8"))
    return {e["id"]: e for e in doc["invariants"]}


def coverage(plugin_root: Path, registry: dict, cases: list[dict]) -> dict:
    rules = extract_rules(plugin_root)
    by_source = [e for e in registry.values() if e.get("match")]
    unregistered = []
    matched_ids = set()
    for r in rules:
        hits = [e for e in by_source if e["source"] == r["source"] and r["text"].startswith(e["match"])]
        if not hits:
            unregistered.append(f"{r['source']}: {r['text'][:90]}")
        matched_ids |= {e["id"] for e in hits}
    stale = sorted(e["id"] for e in by_source if e["id"] not in matched_ids)

    cases_for: dict[str, list[str]] = {k: [] for k in registry}
    for c in cases:
        for s in _walk_specs(all_expects(c)):
            inv = s.get("invariant")
            if inv in cases_for and c["id"] not in cases_for[inv]:
                cases_for[inv].append(c["id"])

    rows, missing = [], []
    for k, e in sorted(registry.items()):
        for p in e.get("enforced_by", []) + e.get("deterministic_tests", []):
            if not (plugin_root / p.split("::")[0]).exists() and not (REPO / p.split("::")[0]).exists():
                missing.append(f"{k}: {p}")
        rows.append({"id": k, "skill": e.get("skill"), "severity": e["severity"], "plane": e["plane"],
                     "target_plane": e.get("target_plane", e["plane"]), "behavioral_cases": len(cases_for[k]),
                     "deterministic_tests": len(e.get("deterministic_tests", [])),
                     "depends_on_skill_loaded": e.get("depends_on_skill_loaded", True)})
    return {
        "rules_in_text": len(rules), "registered": len(registry),
        "unregistered": unregistered, "stale": stale, "missing_paths": missing,
        "untested": [r["id"] for r in rows if r["behavioral_cases"] == 0 and r["deterministic_tests"] == 0],
        "no_behavioral_case": [r["id"] for r in rows if r["behavioral_cases"] == 0],
        "blocking_prose": [r["id"] for r in rows if r["severity"] == "blocking" and r["plane"] == "knowledge"],
        "load_dependent": [r["id"] for r in rows if r["severity"] == "blocking" and r["depends_on_skill_loaded"]],
        "plane_gap": [r["id"] for r in rows if PLANE_RANK[r["plane"]] < PLANE_RANK[r["target_plane"]]],
        "rows": rows, "cases_for": cases_for,
    }


def coverage_markdown(cov: dict) -> str:
    L = ["# Invariant coverage", "",
         f"{cov['rules_in_text']} rules in the plugin text, {cov['registered']} registry entries.", ""]
    for key, title in (("unregistered", "Rules in the text with no registry entry"),
                       ("stale", "Registry entries whose rule text is gone"),
                       ("missing_paths", "Named mechanisms or tests that do not exist"),
                       ("untested", "No behavioral case and no deterministic test"),
                       ("blocking_prose", "Blocking rules enforced only by prose"),
                       ("load_dependent", "Blocking rules that nothing checks unless the skill is loaded"),
                       ("plane_gap", "Enforced below the target plane")):
        L.append(f"**{title}** ({len(cov[key])}): " + (", ".join(cov[key]) if cov[key] else "none"))
        L.append("")
    L += ["| id | severity | plane → target | behavioral cases | deterministic tests | needs skill loaded |",
          "|---|---|---|---|---|---|"]
    for r in cov["rows"]:
        arrow = r["plane"] if r["plane"] == r["target_plane"] else f"{r['plane']} → **{r['target_plane']}**"
        L.append(f"| {r['id']} | {r['severity']} | {arrow} | {r['behavioral_cases']} | {r['deterministic_tests']} | "
                 f"{'yes' if r['depends_on_skill_loaded'] else 'no'} |")
    return "\n".join(L) + "\n"
