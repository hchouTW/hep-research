#!/usr/bin/env python3
"""Host-manifest check: the Claude Code and Codex manifests describe the same plugin.

Plugin manifests (always): `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` exist and agree on name,
version and description; the Codex `skills` path exists and holds the same skills as `skills/`.
Marketplaces (only inside the repository; a relocated copy has none): `.claude-plugin/marketplace.json` and
`.agents/plugins/marketplace.json` at the repository root share a marketplace name, list the same set of plugin
names, and each lists this plugin with a local path that resolves to this folder.

Usage: python3 tools/check_host_manifests.py     exit 0 ok, 1 findings; JSON report on stdout
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def load(path: Path, problems: list[str]) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        problems.append(f"{path.name} unreadable: {e}")
        return {}


def local_path(entry: dict) -> str | None:
    src = entry.get("source")
    if isinstance(src, str):
        return src
    if isinstance(src, dict) and src.get("source") == "local":
        return src.get("path")
    return None


def dependency_names(deps) -> tuple[list[str], list[str]]:
    """Plugin names in a host `dependencies` value, and the entries that could not be read.

    Accepted forms (Claude Code): "name", "name@marketplace", {"name": ..., "version": ..., "marketplace": ...}.
    """
    if deps is None:
        return [], []
    if not isinstance(deps, list):
        return [], [f"dependencies is {type(deps).__name__}, not a list"]
    names, bad = [], []
    for d in deps:
        name = d if isinstance(d, str) else d.get("name") if isinstance(d, dict) else None
        if isinstance(name, str) and name.split("@", 1)[0]:
            names.append(name.split("@", 1)[0])
        else:
            bad.append(f"unreadable dependency entry {d!r}")
    return names, bad


def coupling_problems(plugin: str, manifests: dict[str, dict], catalogs: dict[str, dict]) -> list[str]:
    """Host-native dependency edges between `plugin` and the other plugins its catalogs list."""
    problems: list[str] = []
    others = {str(e.get("name")) for c in catalogs.values() for e in c.get("plugins", [])} - {plugin}
    for host, manifest in manifests.items():
        names, bad = dependency_names(manifest.get("dependencies"))
        problems += [f"{host} plugin.json: {b}" for b in bad]
        problems += [f"{host} plugin.json: {plugin} depends on {n}, which the catalog lists; a companion's compatibility "
                     f"belongs to the companion" for n in names if n in others]
    for host, cat in catalogs.items():
        for entry in cat.get("plugins", []):
            name = entry.get("name")
            names, bad = dependency_names(entry.get("dependencies"))
            problems += [f"{host} marketplace entry {name!r}: {b}" for b in bad]
            targets = others if name == plugin else {plugin}
            problems += [f"{host} marketplace entry {name!r} depends on {n}; remove the edge (the companion checks "
                         f"compatibility itself)" for n in names if n in targets]
    return problems


def main() -> int:
    problems: list[str] = []
    claude = load(ROOT / ".claude-plugin" / "plugin.json", problems)
    codex = load(ROOT / ".codex-plugin" / "plugin.json", problems)
    if claude and codex:
        for key in ("name", "version", "description"):
            if claude.get(key) != codex.get(key):
                problems.append(f"{key} differs: claude {claude.get(key)!r} vs codex {codex.get(key)!r}")
        skills_dir = ROOT / str(codex.get("skills", ""))
        if not codex.get("skills") or not skills_dir.is_dir():
            problems.append(f"codex skills path {codex.get('skills')!r} is not a folder")
        else:
            listed = sorted(p.parent.name for p in skills_dir.glob("*/SKILL.md"))
            expected = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))
            if listed != expected:
                problems.append(f"codex skills {listed} != skills/ {expected}")
    manifests = {h: m for h, m in (("claude", claude), ("codex", codex)) if m}
    catalogs: dict[str, dict] = {}
    markets = {"claude": REPO / ".claude-plugin" / "marketplace.json", "codex": REPO / ".agents" / "plugins" / "marketplace.json"}
    checked = all(p.is_file() for p in markets.values())
    if checked:
        names, listed = {}, {}
        for host, path in markets.items():
            m = load(path, problems)
            catalogs[host] = m
            names[host] = m.get("name")
            listed[host] = sorted(str(e.get("name")) for e in m.get("plugins", []))
            entries = [e for e in m.get("plugins", []) if e.get("name") == claude.get("name")]
            if len(entries) != 1:
                problems.append(f"{host} marketplace lists {claude.get('name')!r} {len(entries)} times")
                continue
            rel = local_path(entries[0])
            if not rel or (REPO / rel).resolve() != ROOT:
                problems.append(f"{host} marketplace path {rel!r} does not resolve to {ROOT.relative_to(REPO)}")
        if len(set(names.values())) != 1:
            problems.append(f"marketplace names differ: {names}")
        if len({tuple(v) for v in listed.values()}) != 1:
            problems.append(f"marketplaces list different plugins: {listed}")
    elif any(p.is_file() for p in markets.values()):
        problems.append("only one host's marketplace file exists at the repository root")
    problems += coupling_problems(str(claude.get("name")), manifests, catalogs)
    report = {"ok": not problems, "problems": problems, "version": claude.get("version"),
              "marketplaces": "checked" if checked else "not checked: no repository root (relocated copy)"}
    print(json.dumps(report, indent=1))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
