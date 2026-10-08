#!/usr/bin/env python3
"""Two-tier profile registry and profile validator.

Usage: python3 contracts/registry.py [--registry PATH] [--local PROFILE_DIR ...]
Exit 0 valid, 1 errors, 2 unreadable registry. Output: JSON report.

Checks: registry schema; duplicate IDs; registry/profile.json agreement; core and contracts
compatibility; required resources present; folder template; paths that escape the package
(including via symlinks); dependency existence and cycles; namespaced vocabulary extensions;
capability claims backed by existing tests. Metadata is read; module content is not.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.schema import Report, validate  # noqa: E402
from contracts.semver import satisfies, valid_spec  # noqa: E402
from contracts.vocab import Vocabulary, declared_namespaces  # noqa: E402
from core import CORE_VERSION  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES: dict[Any, dict[str, list[str]]] = {
    "experiment": {"required": ["profile.json", "index.md", "conventions.json", "modules", "datasets", "evidence", "benchmarks", "tests"],
                   "optional": ["scripts", "README.md"]},
    "theory-domain": {"required": ["profile.json", "index.md", "conventions.json", "models", "derivations", "predictions", "benchmarks", "evidence", "tests"],
                      "optional": ["scripts", "README.md"]},
}
REGISTRY_BUDGET, INDEX_BUDGET = 2048, 4096
DEMONSTRATED = {"demonstrated-on-synthetic-data", "tested-in-declared-environment"}


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def check_profile_dir(pdir: Path, boundary: Path, rep: Report, where: str, expect: dict | None = None) -> dict | None:
    """Validate one profile folder. `boundary` is the directory nothing may escape."""
    if not _inside(pdir, boundary):
        rep.add("error", where, "profile.path_escapes", f"profile path {pdir} escapes {boundary}")
        return None
    pj = pdir / "profile.json"
    if not pj.is_file():
        rep.add("error", where, "profile.missing_resource", f"missing {pj}")
        return None
    try:
        prof = json.loads(pj.read_text(encoding="utf-8"))
    except ValueError as exc:
        rep.add("error", where, "profile.unreadable", f"{pj}: {exc}")
        return None
    if not isinstance(prof, dict):
        rep.add("error", where, "profile.unreadable", f"{pj}: expected a JSON object")
        return None
    pid = prof.get("id", "?")
    where = f"{where}<{pid}>"
    sub = validate(prof, "profile.json", Vocabulary())
    for f in sub.findings:
        rep.add(f.severity, f"{where}{f.path[1:]}", f.code, f.message)
    if expect:
        for k in ("id", "kind", "version"):
            if k in expect and prof.get(k) != expect[k]:
                rep.add("error", where, "registry.mismatch", f"registry {k}={expect[k]!r} but profile.json has {prof.get(k)!r}")
    comp = prof.get("compatible", {})
    for key, have in (("core", CORE_VERSION), ("contracts", CONTRACTS_VERSION)):
        spec = comp.get(key)
        if spec is None:
            continue
        if not valid_spec(spec):
            rep.add("error", f"{where}.compatible.{key}", "profile.bad_version_range", f"cannot parse {spec!r}")
        elif not satisfies(have, spec):
            rep.add("error", f"{where}.compatible.{key}", "profile.incompatible_version",
                    f"requires {key} {spec}, installed {key} is {have}; dependent work must not proceed")
    for name, rel in (prof.get("resources") or {}).items():
        target = pdir / rel
        if not _inside(target, pdir):
            rep.add("error", f"{where}.resources.{name}", "profile.path_escapes", f"resource '{rel}' escapes the profile folder")
        elif not target.exists():
            rep.add("error", f"{where}.resources.{name}", "profile.missing_resource", f"resource '{rel}' does not exist")
    tmpl = TEMPLATES.get(prof.get("kind"))
    if tmpl:
        present = {p.name for p in pdir.iterdir() if not p.name.startswith(".") and p.name != "__pycache__"}
        for need in tmpl["required"]:
            if need not in present:
                rep.add("error", where, "profile.template_violation", f"{prof['kind']} template requires '{need}'")
        for extra in sorted(present - set(tmpl["required"]) - set(tmpl["optional"])):
            rep.add("error", where, "profile.template_violation", f"'{extra}' is not part of the {prof['kind']} template")
        for p in pdir.rglob("*"):
            if p.is_symlink() and not _inside(p, pdir):
                rep.add("error", where, "profile.path_escapes", f"symlink {p.relative_to(pdir)} points outside the profile")
    idx = pdir / (prof.get("resources") or {}).get("index", "index.md")
    if idx.is_file() and idx.stat().st_size > INDEX_BUDGET:
        rep.add("warning", where, "budget.index", f"index.md is {idx.stat().st_size} B > {INDEX_BUDGET} B budget")
    for prob in _vocab_problems(prof):
        rep.add("error", f"{where}.vocabulary_extensions", "profile.vocab_namespace", prob)
    for i, cap in enumerate(prof.get("capabilities", [])):
        if cap.get("status") in DEMONSTRATED:
            tests = cap.get("tests") or []
            if not tests:
                rep.add("error", f"{where}.capabilities[{i}]", "profile.unbacked_capability",
                        f"capability '{cap.get('name')}' claims '{cap['status']}' without tests")
            for t in tests:
                # A test outside the profile folder may only be one of the plugin's own tests.
                if not (_inside(pdir / t, pdir) or _inside(pdir / t, PLUGIN_ROOT / "tests")):
                    rep.add("error", f"{where}.capabilities[{i}]", "profile.path_escapes", f"test '{t}' escapes the profile folder and the plugin tests")
                elif not (pdir / t).exists():
                    rep.add("error", f"{where}.capabilities[{i}]", "profile.unbacked_capability", f"test '{t}' does not exist")
    prof["_dir"] = str(pdir)
    return prof


def _vocab_problems(prof: dict) -> list[str]:
    v, out = Vocabulary(), []
    for name, terms in (prof.get("vocabulary_extensions") or {}).items():
        out += v.extend(name, terms, declared_namespaces(prof))
    return out


def find_cycles(profiles: dict[str, dict]) -> list[list[str]]:
    cycles, state = [], {}

    def visit(n, stack):
        state[n] = 1
        for d in profiles.get(n, {}).get("depends_on", []):
            if d not in profiles:
                continue
            if state.get(d) == 1:
                cycles.append(stack[stack.index(d):] + [d])
            elif d not in state:
                visit(d, stack + [d])
        state[n] = 2

    for n in sorted(profiles):
        if n not in state:
            visit(n, [n])
    return cycles


def validate_registry(registry_path: Path | None = None, local_dirs=(), package_root: Path | None = None) -> tuple[Report, dict]:
    """Validate the registry plus optional local profile folders. Returns (report, {id: profile})."""
    registry_path = Path(registry_path or PLUGIN_ROOT / "profiles" / "registry.json")
    package_root = Path(package_root or registry_path.parent.parent)
    rep = Report()
    loaded: dict[str, Any] = {}
    reg = json.loads(registry_path.read_text(encoding="utf-8"))
    validate(reg, "registry.json", None, rep, "registry")
    if registry_path.stat().st_size > REGISTRY_BUDGET:
        rep.add("warning", "registry", "budget.registry", f"registry is {registry_path.stat().st_size} B > {REGISTRY_BUDGET} B budget")
    entries = [(e, registry_path.parent / e.get("path", ""), package_root, f"registry[{i}]")
               for i, e in enumerate(reg.get("profiles", []) if isinstance(reg, dict) else [])]
    unique = list(dict.fromkeys(Path(d).resolve() for d in local_dirs))  # one folder given twice is one profile
    entries += [(None, d, d, f"local[{i}]") for i, d in enumerate(unique)]
    for expect, pdir, boundary, where in entries:
        prof = check_profile_dir(pdir, boundary, rep, where, expect)
        if prof is None or not isinstance(prof.get("id"), str):
            continue    # a missing or malformed id is already a schema finding
        if prof["id"] in loaded:
            rep.add("error", where, "registry.duplicate_id", f"duplicate profile id '{prof['id']}' (also at {loaded[prof['id']]['_dir']})")
            continue
        loaded[prof["id"]] = prof
    for pid, prof in sorted(loaded.items()):
        for dep in prof.get("depends_on", []):
            if dep not in loaded:
                rep.add("error", pid, "profile.missing_dependency", f"depends on '{dep}', which is not registered")
    for cyc in find_cycles(loaded):
        rep.add("error", cyc[0], "profile.dependency_cycle", "dependency cycle: " + " -> ".join(cyc))
    return rep, loaded


def option_values(args: list[str], flag: str) -> list[str]:
    """Every value given after `flag`; ValueError when the flag ends the command line (a usage error, exit 2)."""
    if args and args[-1] == flag:
        raise ValueError(f"{flag} needs a value")
    return [args[i + 1] for i, a in enumerate(args) if a == flag]


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        reg = next((Path(v) for v in option_values(args, "--registry")), None)
        rep, loaded = validate_registry(reg, option_values(args, "--local"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    print(json.dumps({**rep.as_dict(), "profiles": sorted(loaded)}, indent=1))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
