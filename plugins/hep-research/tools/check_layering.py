#!/usr/bin/env python3
"""Enforce the layer directions of task Section 7.4 (AST import scan plus text scan).

Allowed plugin-internal imports:
  core/       -> core (+ stdlib and the mandatory environment only)
  contracts/  -> contracts, core (+ stdlib and the mandatory environment only)
  skills/<s>/scripts -> core, contracts (never another skill)
  profiles/<p> -> core, contracts; another profile only if declared in depends_on
  adapters/<a> -> core, contracts
  examples/, tests/, tools/ -> anything
Text rules:
  - core/ code never references profiles/, adapters/ or skills/ paths.
  - Core skill text and code, core/ and contracts/ (fixtures excluded) contain no hard-coded
    profile IDs, evidence namespaces of registered profiles, or experiment names, except inside
    example blocks (<!-- example ... --> ... <!-- /example --> in Markdown;
    '# example-begin' ... '# example-end' in Python) or a whitelist entry.
  - No core schema requires a collider-only or AMS-only field.
  - Every module or package in core/ has a steward in core/OWNERS.json.

Usage: python3 tools/check_layering.py [--root PLUGIN_ROOT]
Exit 0 clean, 1 violations. Output: JSON with file, line, rule, message per violation.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

MANDATORY = {"numpy", "scipy", "matplotlib", "sympy", "mpmath"}
INTERNAL = {"core", "contracts", "skills", "profiles", "adapters", "tools", "tests", "examples"}
EXPERIMENT_NAMES = r"\b(AMS-?02|AMS|ATLAS|CMS|LHCb|ALICE|Belle(?: II)?|BaBar|IceCube|Fermi-LAT|DAMPE|PAMELA|CALET|Super-?K(?:amiokande)?|DUNE|T2K|NOvA|XENONnT|LZ|KATRIN|Auger|HESS|MAGIC|VERITAS|CTA)\b"
PROFILE_ID = r"\b(experiment|theory):[a-z0-9][a-z0-9-]*\b"
COLLIDER_OR_AMS_FIELDS = {"luminosity", "integrated_luminosity", "pileup", "trigger", "jets", "met", "rigidity",
                          "geomagnetic_cutoff", "abs_Z", "charge_sign", "ams_claims", "sqrt_s"}
MD_EXAMPLE = re.compile(r"<!--\s*example.*?<!--\s*/example\s*-->", re.S)
PY_EXAMPLE = re.compile(r"#\s*example-begin.*?#\s*example-end", re.S)


def component(rel: Path) -> tuple[str, str | None]:
    parts = rel.parts
    top = parts[0]
    if top == "skills" and len(parts) > 1:
        return "skills", parts[1]
    if top == "profiles" and len(parts) > 2:
        return "profiles", "/".join(parts[1:3])
    if top == "adapters" and len(parts) > 1:
        return "adapters", parts[1]
    return top, None


def imported_modules(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield node.lineno, a.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module


def blank_examples(text: str, pattern: re.Pattern) -> str:
    """Replace example blocks by blank lines so line numbers stay correct."""
    return pattern.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def required_fields(schema, out: set):
    if isinstance(schema, dict):
        out.update(schema.get("required", []))
        for v in schema.values():
            required_fields(v, out)
    elif isinstance(schema, list):
        for v in schema:
            required_fields(v, out)
    return out


def check(root: Path) -> list[dict]:
    root = root.resolve()
    v: list[dict] = []
    stdlib = set(sys.stdlib_module_names)
    wl_path = root / "tools" / "layering_whitelist.json"
    whitelist = json.loads(wl_path.read_text()) if wl_path.is_file() else []

    def add(path: Path, line: int, rule: str, msg: str, text: str = "") -> None:
        rel = str(path.relative_to(root))
        for w in whitelist:
            if w["file"] == rel and re.search(w["pattern"], text or msg):
                return
        v.append({"file": rel, "line": line, "rule": rule, "message": msg})

    profiles = {}
    reg = root / "profiles" / "registry.json"
    if reg.is_file():
        for e in json.loads(reg.read_text()).get("profiles", []):
            pj = (reg.parent / e["path"] / "profile.json")
            if pj.is_file():
                p = json.loads(pj.read_text())
                profiles["/".join(Path(e["path"]).parts[:2])] = p
    namespaces = {p.get("evidence_namespace") for p in profiles.values()} - {None}
    for p in profiles.values():
        namespaces.update(p.get("vocabulary_namespaces", []))
    id_to_dir = {p["id"]: d for d, p in profiles.items()}

    # Import scan
    for py in sorted(root.rglob("*.py")):
        rel = py.relative_to(root)
        comp, sub = component(rel)
        if comp in ("tools", "tests", "examples") or "fixtures" in rel.parts:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            add(py, exc.lineno or 0, "parse", f"cannot parse: {exc.msg}")
            continue
        for line, mod in imported_modules(tree):
            top = mod.split(".")[0]
            if comp in ("core", "contracts"):
                allowed = {"core"} | ({"contracts"} if comp == "contracts" else set())
                if top in INTERNAL and top not in allowed:
                    add(py, line, "direction", f"{comp}/ must not import '{mod}'")
                elif top not in INTERNAL and top not in stdlib and top not in MANDATORY:
                    add(py, line, "dependency", f"{comp}/ may use only stdlib and the mandatory environment; imports '{mod}'")
            elif comp == "skills":
                if top in INTERNAL - {"core", "contracts"}:
                    add(py, line, "direction", f"skills/{sub} may import only core and contracts; imports '{mod}'")
            elif comp == "adapters":
                if top in INTERNAL - {"core", "contracts"}:
                    add(py, line, "direction", f"adapters/{sub} may import only core and contracts; imports '{mod}'")
            elif comp == "profiles":
                if top in {"skills", "adapters", "tools", "tests", "examples"}:
                    add(py, line, "direction", f"profiles/{sub} may import only core, contracts and declared profiles; imports '{mod}'")

    # Text scan
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix not in (".py", ".md", ".json"):
            continue
        rel = f.relative_to(root)
        comp, sub = component(rel)
        text = f.read_text(encoding="utf-8", errors="replace")
        if comp == "profiles" and sub:
            own = profiles.get(sub, {})
            deps = {id_to_dir.get(d) for d in own.get("depends_on", [])}
            for m in re.finditer(r"profiles/((?:experiments|theory)/[a-z0-9-]+)", text):
                if m.group(1) != sub and m.group(1) not in deps:
                    add(f, text.count("\n", 0, m.start()) + 1, "direction",
                        f"profiles/{sub} references profiles/{m.group(1)} without declaring it in depends_on", m.group(0))
            continue
        if comp == "core" and f.suffix == ".py":
            for m in re.finditer(r"""["'][^"'\n]*\b(profiles|adapters|skills)/""", text):
                add(f, text.count("\n", 0, m.start()) + 1, "direction", f"core/ references a {m.group(1)}/ path", m.group(0))
        scanned = comp in ("core", "contracts") or (comp == "skills")
        if not scanned or "fixtures" in rel.parts or rel.parts[:2] == ("contracts", "vocab"):
            continue
        body = blank_examples(text, MD_EXAMPLE if f.suffix == ".md" else PY_EXAMPLE)
        patterns = [(EXPERIMENT_NAMES, "experiment-name"), (PROFILE_ID, "profile-id")]
        if namespaces:
            patterns.append((r"\b(" + "|".join(sorted(map(re.escape, namespaces))) + r"):[A-Za-z0-9_]", "namespace"))
        for pat, rule in patterns:
            for m in re.finditer(pat, body):
                line = body.count("\n", 0, m.start()) + 1
                add(f, line, f"hard-coded-{rule}", f"'{m.group(0)}' outside an example block", m.group(0))

    # Schema scan: no collider-only or AMS-only required field
    for s in sorted((root / "contracts" / "schemas").glob("*.json")) if (root / "contracts" / "schemas").is_dir() else []:
        req = required_fields(json.loads(s.read_text()), set())
        for bad in sorted(req & COLLIDER_OR_AMS_FIELDS):
            add(s, 0, "schema-term", f"core schema requires experiment-specific field '{bad}'")

    # Stewards
    owners_file = root / "core" / "OWNERS.json"
    owners = json.loads(owners_file.read_text()).get("modules", {}) if owners_file.is_file() else {}
    if (root / "core").is_dir():
        for item in sorted((root / "core").iterdir()):
            name = item.stem if item.suffix in (".py", ".json") else item.name
            if name in ("__init__", "__pycache__", "OWNERS") or item.name.startswith("."):
                continue
            if name not in owners:
                add(item, 0, "steward", f"core module '{name}' has no steward in core/OWNERS.json")
    return v


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[args.index("--root") + 1]) if "--root" in args else Path(__file__).resolve().parents[1]
    violations = check(root)
    print(json.dumps({"ok": not violations, "violations": violations}, indent=1))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
