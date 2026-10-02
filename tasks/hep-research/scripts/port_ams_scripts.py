#!/usr/bin/env python3
"""M2: port the AMS-only scripts and their tests from the legacy ams-analysis skill.

  yaml_subset.py          -> contracts/legacy/yaml_subset.py (generic strict YAML subset)
  audit_analysis_spec.py  -> profiles/experiments/ams-02/scripts/
  fetch_papers.py         -> profiles/experiments/ams-02/scripts/   (networked, opt-in)
  crdb_query.py           -> profiles/experiments/ams-02/scripts/   (networked, opt-in)
Tests go to profiles/experiments/ams-02/tests/ (yaml_subset tests to tests/contracts/).
Only import paths, data paths and namespaced claim-ID lookup change; every other line is
copied. Reads $LEGACY_REPO (default .legacy/agentic-ai-skills).
"""
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEG = Path(os.environ.get("LEGACY_REPO", ROOT / ".legacy/agentic-ai-skills")) / "ams-analysis"
PLUG = ROOT / "plugins/hep-research"
PROF = PLUG / "profiles/experiments/ams-02"

# script-mode bootstrap: profile scripts sit 4 levels below the plugin root
BOOT = '''import sys as _sys
from pathlib import Path as _Path
_PLUGIN_ROOT = _Path(__file__).resolve().parents[4]
if str(_PLUGIN_ROOT) not in _sys.path:  # make core/ and contracts/ importable when run as a script
    _sys.path.insert(0, str(_PLUGIN_ROOT))
'''


def sub1(pattern, repl, text, count=1):
    new, n = re.subn(pattern, repl, text, count=count)
    if n == 0:
        raise SystemExit(f"pattern not found: {pattern!r}")
    return new


def rep1(old, new, text):
    if old not in text:
        raise SystemExit(f"text not found: {old!r}")
    return text.replace(old, new)


def port_yaml():
    t = (LEG / "scripts/yaml_subset.py").read_text()
    (PLUG / "contracts/legacy").mkdir(parents=True, exist_ok=True)
    (PLUG / "contracts/legacy/__init__.py").write_text(
        '"""Readers for legacy input formats (strict YAML subset; experiment-specific converters live in their profiles)."""\n')
    (PLUG / "contracts/legacy/yaml_subset.py").write_text(t)


def port_audit():
    t = (LEG / "scripts/audit_analysis_spec.py").read_text()
    t = rep1("sys.path.insert(0, str(Path(__file__).resolve().parent))\nimport yaml_subset  # noqa: E402  (strict YAML subset, standard library only)\n",
             BOOT + "from contracts.legacy import yaml_subset  # noqa: E402  (strict YAML subset, standard library only)\n", t)
    t = rep1('ROOT = Path(__file__).resolve().parents[1]\n', 'ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder\n', t)
    t = rep1('default=ROOT / "data" / "claims.json"', 'default=ROOT / "evidence" / "claims.json"', t)
    t = rep1('    lookup = {c["id"]: c for c in claims} if isinstance(claims, list) else claims\n',
             '    lookup = {c["id"]: c for c in claims} if isinstance(claims, list) else claims\n'
             '    if lookup is not None:  # a bare legacy ID (C31) is the short form of the namespaced one (ams02:C31)\n'
             '        lookup = {**{k.split(":", 1)[1]: v for k, v in lookup.items() if ":" in k}, **lookup}\n', t)
    t = t.replace("[--claims data/claims.json | --no-claims]", "[--claims evidence/claims.json | --no-claims]")
    t = t.replace("references/analysis-artifacts.md", "modules/analysis-artifacts.md")
    t = t.replace("python3 scripts/audit_analysis_spec.py", "python3 profiles/experiments/ams-02/scripts/audit_analysis_spec.py")
    return t


def port_fetch():
    t = (LEG / "scripts/fetch_papers.py").read_text()
    t = rep1('ROOT = Path(__file__).resolve().parents[1]\nMANIFEST = ROOT / "data" / "papers_manifest.json"\nSOURCES = ROOT / "data" / "sources.json"\n',
             'ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder\nMANIFEST = ROOT / "evidence" / "papers_manifest.json"\nSOURCES = ROOT / "evidence" / "sources.json"\n', t)
    t = t.replace("`data/papers_manifest.json`", "`evidence/papers_manifest.json`")
    t = t.replace("`data/claims.json`", "`evidence/claims.json`")
    t = t.replace("references/source-policy.md", "modules/source-policy.md")
    t = re.sub(r"python3 scripts/fetch_papers\.py", "python3 profiles/experiments/ams-02/scripts/fetch_papers.py", t)
    return t


def port_crdb():
    t = (LEG / "scripts/crdb_query.py").read_text()
    t = t.replace("references/cosmic-ray-databases.md", "modules/cosmic-ray-databases.md")
    t = re.sub(r"python3 scripts/crdb_query\.py", "python3 profiles/experiments/ams-02/scripts/crdb_query.py", t)
    return t


def main():
    port_yaml()
    (PROF / "scripts").mkdir(exist_ok=True)
    for name, fn in (("audit_analysis_spec", port_audit), ("fetch_papers", port_fetch), ("crdb_query", port_crdb)):
        (PROF / f"scripts/{name}.py").write_text(fn())
    fx = PROF / "tests/fixtures"
    fx.mkdir(parents=True, exist_ok=True)
    for f in ("spec_valid.json", "spec_valid.yaml"):
        shutil.copyfile(LEG / f"tests/fixtures/{f}", fx / f)
    print("ported scripts; tests are ported by hand (see tasks/hep-research/m2/equivalence.md)")


if __name__ == "__main__":
    main()
