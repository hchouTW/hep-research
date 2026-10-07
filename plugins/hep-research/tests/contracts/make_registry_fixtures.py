#!/usr/bin/env python3
"""Regenerate registry and project-config fixtures under contracts/fixtures/{registry,projects}/.
Fixture profiles are structural stand-ins named 'fixture-*'; they carry no physics content.

Usage: python3 tests/contracts/make_registry_fixtures.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "contracts" / "fixtures" / "registry"
PROJ = ROOT / "contracts" / "fixtures" / "projects"
EXP_DIRS = ["modules", "datasets", "evidence", "benchmarks", "tests"]
TH_DIRS = ["models", "derivations", "predictions", "benchmarks", "evidence", "tests"]


def profile(pid, kind, ns, **kw):
    p = {"id": pid, "kind": kind, "version": "1.0.0", "scope": "structural fixture", "exclusions": [],
         "compatible": {"core": ">=1.0,<2.0", "contracts": ">=2.0,<3.0"}, "related_skills": ["hep-analysis"],
         "resources": {"index": "index.md", "conventions": "conventions.json"},
         "vocabulary_extensions": {}, "adapters": {"required": [], "optional": []}, "depends_on": [],
         "evidence_namespace": ns, "maintainer": "fixture", "capabilities": [
             {"name": "structure-only", "status": "proposed", "scope": "fixture"}]}
    p.update(kw)
    return p


def write_profile(base: Path, rel: str, prof: dict, skip=(), extra=()):
    d = base / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "profile.json").write_text(json.dumps(prof, indent=1) + "\n")
    if "index.md" not in skip:
        (d / "index.md").write_text(f"# {prof['id']} (fixture)\n")
    if "conventions.json" not in skip:
        (d / "conventions.json").write_text("{}\n")
    for sub in (EXP_DIRS if prof["kind"] == "experiment" else TH_DIRS):
        if sub not in skip:
            (d / sub).mkdir(exist_ok=True)
            (d / sub / ".keep").write_text("")
    for e in extra:
        (d / e).mkdir(exist_ok=True)
        (d / e / ".keep").write_text("")


def package(name: str, profiles: list[tuple[str, dict, dict]], registry_override=None):
    """profiles: (relative path under profiles/, profile.json dict, write_profile kwargs)."""
    base = REG / name
    (base / "profiles").mkdir(parents=True, exist_ok=True)
    entries = []
    for rel, prof, kw in profiles:
        write_profile(base / "profiles", rel, prof, **kw)
        entries.append({"id": prof["id"], "kind": prof["kind"], "version": prof["version"], "scope": "fixture", "path": rel})
    reg = {"registry_version": "1.0.0", "profiles": registry_override(entries) if registry_override else entries}
    (base / "profiles" / "registry.json").write_text(json.dumps(reg, indent=1) + "\n")


def main() -> None:
    for d in (REG, PROJ):
        shutil.rmtree(d, ignore_errors=True)
    exp_a = profile("experiment:fixture-exp-a", "experiment", "fxa", vocabulary_extensions={"levels": ["fxa:instrument"], "normalization_kinds": ["fxa:per-orbit"]})
    exp_b = profile("experiment:fixture-exp-b", "experiment", "fxb")
    th_a = profile("theory:fixture-th-a", "theory-domain", "fta", related_skills=["hep-theory"])
    th_b = profile("theory:fixture-th-b", "theory-domain", "ftb", related_skills=["hep-theory"])
    ok = [("experiments/a", exp_a, {}), ("experiments/b", exp_b, {}), ("theory/a", th_a, {}), ("theory/b", th_b, {})]
    package("valid", ok)
    cases = {"valid": []}
    package("duplicate_id", [("experiments/a", exp_a, {}), ("experiments/a2", dict(exp_a), {})]); cases["duplicate_id"] = ["registry.duplicate_id"]
    package("incompatible_version", [("experiments/a", {**exp_a, "compatible": {"core": ">=2.0,<3.0", "contracts": ">=2.0,<3.0"}}, {})]); cases["incompatible_version"] = ["profile.incompatible_version"]
    package("missing_resource", [("experiments/a", exp_a, {"skip": ["conventions.json"]})]); cases["missing_resource"] = ["profile.missing_resource"]
    package("template_violation", [("theory/a", th_a, {"skip": ["derivations"], "extra": ["notes"]})]); cases["template_violation"] = ["profile.template_violation"]
    package("escaping_path", [("experiments/a", {**exp_a, "resources": {"index": "../../../../outside.md", "conventions": "conventions.json"}}, {})],
            registry_override=lambda e: e + [{"id": "experiment:fixture-out", "kind": "experiment", "version": "1.0.0", "scope": "x", "path": "../../.."}])
    cases["escaping_path"] = ["profile.path_escapes"]
    package("cycle", [("theory/a", {**th_a, "depends_on": ["theory:fixture-th-b"]}, {}), ("theory/b", {**th_b, "depends_on": ["theory:fixture-th-a"]}, {})]); cases["cycle"] = ["profile.dependency_cycle"]
    package("missing_dependency", [("theory/a", {**th_a, "depends_on": ["theory:fixture-absent"]}, {})]); cases["missing_dependency"] = ["profile.missing_dependency"]
    package("unbacked_capability", [("experiments/a", {**exp_a, "capabilities": [{"name": "x", "status": "demonstrated-on-synthetic-data", "scope": "x"}]}, {})]); cases["unbacked_capability"] = ["profile.unbacked_capability"]
    package("bad_vocab_namespace", [("experiments/a", {**exp_a, "vocabulary_extensions": {"levels": ["instrument", "other:level"]}}, {})]); cases["bad_vocab_namespace"] = ["profile.vocab_namespace"]
    package("registry_mismatch", [("experiments/a", exp_a, {})], registry_override=lambda e: [{**e[0], "version": "1.1.0"}]); cases["registry_mismatch"] = ["registry.mismatch"]
    (REG / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")

    # Project configs: 0/1/many experiments x 0/1/many theory, plus a local profile kept in the project.
    sets = {"0": [], "1": ["a"], "many": ["a", "b"]}
    pcases = {}
    for ne, exps in sets.items():
        for nt, ths in sets.items():
            name = f"exp{ne}_th{nt}"
            cfg = {"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0",
                   "experiments": [{"profile": f"experiment:fixture-exp-{x}", "version": "1.0.0"} for x in exps],
                   "theory": [{"profile": f"theory:fixture-th-{x}", "version": "1.0.0"} for x in ths]}
            (PROJ / name).mkdir(parents=True, exist_ok=True)
            (PROJ / name / "hep-research.project.json").write_text(json.dumps(cfg, indent=1) + "\n")
            pcases[name] = {"errors": [], "profiles": len(exps) + len(ths)}
    loc = PROJ / "local_profile"
    write_profile(loc / "local-profiles", "exp-local", profile("experiment:fixture-local", "experiment", "local-fx"))
    (loc / "hep-research.project.json").write_text(json.dumps({
        "schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0",
        "experiments": [{"profile": "experiment:fixture-local", "version": "1.0.0"}],
        "local_profile_paths": ["local-profiles/exp-local"],
        "overrides": [{"target": "fxa:placeholder", "value": 1, "provenance": "fixture: user-supplied note"}]}, indent=1) + "\n")
    pcases["local_profile"] = {"errors": [], "profiles": 1}
    bad = {
        "unknown_profile": ({"experiments": [{"profile": "experiment:fixture-nope", "version": "1.0.0"}]}, ["project.unknown_profile"]),
        "version_pin_mismatch": ({"experiments": [{"profile": "experiment:fixture-exp-a", "version": "0.9.0"}]}, ["project.version_pin_mismatch"]),
        "conflicting_pins": ({"experiments": [{"profile": "experiment:fixture-exp-a", "version": "1.0.0"}, {"profile": "experiment:fixture-exp-a", "version": "1.1.0"}]}, ["project.conflicting_pins"]),
        "wrong_axis": ({"theory": [{"profile": "experiment:fixture-exp-a", "version": "1.0.0"}]}, ["project.wrong_axis"]),
        "override_without_provenance": ({"overrides": [{"target": "x", "value": 1}]}, ["schema.required"]),
        "incompatible_plugin": ({"plugin_version": ">=2.0"}, ["project.incompatible_plugin"]),
    }
    for name, (patch, codes) in bad.items():
        cfg = {"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0", **patch}
        (PROJ / name).mkdir(parents=True, exist_ok=True)
        (PROJ / name / "hep-research.project.json").write_text(json.dumps(cfg, indent=1) + "\n")
        pcases[name] = {"errors": codes}
    (PROJ / "cases.json").write_text(json.dumps({"registry": "../registry/valid/profiles/registry.json", "cases": pcases}, indent=1) + "\n")
    print(f"{len(cases)} registry packages, {len(pcases)} project configs")


if __name__ == "__main__":
    main()
