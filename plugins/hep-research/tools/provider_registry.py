#!/usr/bin/env python3
"""Generate the cr-provider/1 registry that a caller passes to core/provider (--provider-registry FILE).

The registry lists every provider declared in the 'provider' field of the plugin's adapters/*/adapter.json and of the
profile.json of every profile in profiles/registry.json, plus the user-supplied declarations given with
--user-provider (each listed explicitly; their outputs carry the label user-supplied and are never evidence for a
validated result). Each declaration is checked against contracts/schemas/cr_provider.json and the core rules
(core/provider/protocol.py); its entrypoint is resolved inside the declaring folder (regular file, no link, no '..')
and written as an absolute path, so the registry is generated per checkout, written outside the repository and never
committed. The provider version is the declaration's 'version', else the adapter's or profile's version; a
user-supplied declaration must give one.

A declaration with a modulation block (contracts 3.15.0: the provider modulates, the declared exception to "providers
never modulate") is refused unless its conformance result passed (core/provider/protocol.py). The conformance gate
(--conformance PROVIDER_ID) produces that result: at a reference point it asks the provider's entrypoint module, through
its hook isotope_tables(request, point), for its isotopic LIS (the point without its modulation parameter: a run
without modulation) and for its modulated per-isotope output (the point with it), applies the plugin's force-field tool
(skills/hep-measurement/scripts/solar_modulation_force_field.py, the command line of its tool contract, --lis-table)
to the LIS of each isotope at every top-of-atmosphere node whose LIS energy E_k/n + |Z| phi / A lies inside the LIS
table, and compares with the provider's value: passed when every relative deviation is within the tolerance (no looser
than 1e-3). The reference point, observables and tolerance come from the options or from the declaration's existing
conformance block. It prints the conformance block to declare and writes the per-node comparison to --out.

Usage:
  python3 tools/provider_registry.py --write "$CRPROP_OUT/registry.json" [--user-provider DECLARATION.json ...]
  python3 tools/provider_registry.py --check         # check the declarations only; write nothing
  python3 tools/provider_registry.py --conformance usine --out "$CRPROP_OUT/conformance.json"
      [--reference-point '{"phi_2011_2016_gv": 0.7}'] [--observables OBSERVABLES.json] [--tolerance 1e-3]
Exit codes of --conformance: 0 passed, 1 failed (a deviation above the tolerance, or no node compared), 2 unusable
input (unknown provider, no modulation block, no hook, an invalid reference, an unwritable --out).
A user-supplied declaration file holds one declaration (or a list) with a 'version'; its entrypoint is relative to
the file's folder. Output: one JSON object (status written|ok|rejected, providers, problems). Exit 0 ok, 2 an invalid
declaration, a duplicate provider id, a path inside the plugin or an unwritable path.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.schema import validate  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.provider.entrypoint import write_json_atomic  # noqa: E402
from core.constants.physical import nuclear_mass_gev  # noqa: E402
from core.provider.protocol import (  # noqa: E402
    MODULATION_PARAMETER,
    MODULATION_TOLERANCE_MAX,
    PROTOCOL,
    check_declaration,
    check_request,
    declarations_of,
)
from core.provider.registry import REGISTRY_FORMAT, parse_registry  # noqa: E402

DECLARATIONS_SCHEMA = {"$ref": "cr_provider.json#/$defs/declarations"}
FORCE_FIELD_TOOL = "skills/hep-measurement/scripts/solar_modulation_force_field.py"
CONFORMANCE_HOOK = "isotope_tables"


class ConformanceError(ValueError):
    """Input the conformance gate cannot use (exit 2)."""


def declaring_files(root: Path = ROOT) -> list[tuple[Path, dict]]:
    """(manifest path, manifest) of every adapter.json and registered profile.json, in a stable order."""
    out = []
    for path in sorted((root / "adapters").glob("*/adapter.json")):
        out.append((path, json.loads(path.read_text(encoding="utf-8"))))
    reg = root / "profiles" / "registry.json"
    if reg.is_file():
        for item in json.loads(reg.read_text(encoding="utf-8")).get("profiles", []):
            path = root / "profiles" / item["path"] / "profile.json"
            if path.is_file():
                out.append((path, json.loads(path.read_text(encoding="utf-8"))))
    return out


def resolve_entrypoint(folder: Path, relative: str) -> tuple[Path | None, str]:
    """The absolute entrypoint inside `folder`, or (None, problem). Links and paths leaving the folder are refused."""
    target = folder / relative
    if any(os.path.islink(folder.joinpath(*Path(relative).parts[:i])) for i in range(1, len(Path(relative).parts) + 1)):
        return None, f"entrypoint {relative} is or passes through a link"
    try:
        mode = os.lstat(target).st_mode
    except OSError:
        return None, f"entrypoint {relative} does not exist in {folder}"
    if not stat.S_ISREG(mode):
        return None, f"entrypoint {relative} is not a regular file"
    resolved = target.resolve()
    if folder.resolve() not in resolved.parents:
        return None, f"entrypoint {relative} leaves {folder}"
    return resolved, ""


def collect(field, folder: Path, component: str, default_version: str | None, user_supplied: bool,
            where: str) -> tuple[list[dict], list[str]]:
    """Registry items and problems for one 'provider' field."""
    rep = validate(field, DECLARATIONS_SCHEMA, Vocabulary())
    problems = [f"{where}: {f.path} {f.message}" for f in rep.errors]
    items = []
    for decl in declarations_of(field) if not problems else []:
        core_problems = check_declaration(decl)
        problems += [f"{where} {decl.get('id')}: {p}" for p in core_problems]
        if core_problems:
            continue
        version = decl.get("version", default_version)
        if not version:
            problems.append(f"{where} {decl['id']}: a user-supplied declaration gives its version")
            continue
        entry, why = resolve_entrypoint(folder, decl["entrypoint"])
        if entry is None:
            problems.append(f"{where} {decl['id']}: {why}")
            continue
        items.append({"declaration": decl, "version": version, "entrypoint_path": str(entry),
                      "component": component, "user_supplied": user_supplied})
    return items, problems


def build(user_files: list[Path], root: Path = ROOT) -> tuple[dict, list[str]]:
    items: list[dict] = []
    problems: list[str] = []
    for path, manifest in declaring_files(root):
        if "provider" not in manifest:
            continue
        got, bad = collect(manifest["provider"], path.parent, str(manifest.get("id", path.parent.name)),
                           manifest.get("version"), False, str(path.relative_to(root)))
        items += got
        problems += bad
    for path in user_files:
        try:
            field = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{path}: unreadable: {exc}")
            continue
        got, bad = collect(field, Path(path).resolve().parent, f"user-supplied:{Path(path).name}", None, True,
                           str(path))
        items += got
        problems += bad
    ids = [i["declaration"]["id"] for i in items]
    problems += [f"provider id '{pid}' is declared twice" for pid in sorted({x for x in ids if ids.count(x) > 1})]
    doc = {"format": REGISTRY_FORMAT, "providers": items}
    if not problems:
        try:
            parse_registry(doc)
        except ValueError as exc:
            problems.append(str(exc))
    return doc, problems


def find_declaration(provider_id: str, root: Path = ROOT) -> tuple[dict, Path, str]:
    """(declaration, entrypoint path, provider version) of a plugin provider, read without the conformance rule (the
    gate runs before a passing result exists)."""
    for path, manifest in declaring_files(root):
        for decl in declarations_of(manifest.get("provider") or []):
            if isinstance(decl, dict) and decl.get("id") == provider_id:
                entry, why = resolve_entrypoint(path.parent, str(decl.get("entrypoint", "")))
                if entry is None:
                    raise ConformanceError(why)
                return decl, entry, str(decl.get("version") or manifest.get("version") or "")
    raise ConformanceError(f"no provider {provider_id!r} is declared in the plugin's adapters or profiles")


def _load_hook(entrypoint: Path):
    spec = importlib.util.spec_from_file_location(f"provider_entrypoint_{entrypoint.stem}", entrypoint)
    if spec is None or spec.loader is None:
        raise ConformanceError(f"cannot load {entrypoint}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hook = getattr(module, CONFORMANCE_HOOK, None)
    if not callable(hook):
        raise ConformanceError(f"{entrypoint.name} has no {CONFORMANCE_HOOK}(request, point) hook: the conformance "
                               "gate needs the provider's per-isotope tables")
    return hook


def _isotope_problems(tables, label: str) -> list[str]:
    if not isinstance(tables, dict) or not isinstance(tables.get("isotopes"), dict) or not tables["isotopes"]:
        return [f"{label}: the hook returns {{'phi_gv', 'isotopes': {{nuclide: {{charge, mass_number, ekn, flux}}}}}}"]
    problems = []
    for nuc, t in tables["isotopes"].items():
        ok = isinstance(t, dict) and isinstance(t.get("charge"), int) and isinstance(t.get("mass_number"), int) \
            and isinstance(t.get("ekn"), list) and isinstance(t.get("flux"), list) and len(t["ekn"]) == len(t["flux"]) >= 2
        if not ok:
            problems.append(f"{label} {nuc}: charge, mass_number and equal-length ekn and flux lists")
    return problems


def force_field_tool(ekn: float, lis_table: Path, charge: int, mass_number: int, phi_gv: float,
                     python: str = sys.executable) -> float:
    """flux_toa of the plugin's force-field tool (its command line, the tool contract) at one E_k/n."""
    argv = [python, "-I", str(ROOT / FORCE_FIELD_TOOL), "--modulate", "--energy", repr(float(ekn)), "--energy-kind",
            "Ek_per_nucleon", "--mass", repr(nuclear_mass_gev(charge, mass_number)), "--charge", str(charge),
            "--mass-number", str(mass_number), "--phi", repr(float(phi_gv)), "--lis-table", str(lis_table)]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=120,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if proc.returncode != 0:
        raise ConformanceError(f"the force-field tool failed (exit {proc.returncode}): {proc.stdout[-400:]}")
    return float(json.loads(proc.stdout)["flux_toa"])


def modulation_conformance(provider_id: str, reference_point: dict | None = None, observables: list | None = None,
                           tolerance: float | None = None, root: Path = ROOT, hook=None) -> dict:
    """The conformance gate of a provider's declared modulation; {"conformance": <block to declare>, "nodes": [...],
    "lis_substitutes", "toa_substitutes"}. hook replaces the entrypoint's isotope_tables (tests)."""
    decl, entrypoint, version = find_declaration(provider_id, root)
    block = decl.get("modulation")
    if not isinstance(block, dict) or not isinstance(block.get("parameters"), list):
        raise ConformanceError(f"provider {provider_id} declares no modulation block with its parameters")
    if block.get("model") != "force-field":
        raise ConformanceError("the conformance gate checks the force-field model only")
    previous = block.get("conformance") if isinstance(block.get("conformance"), dict) else {}
    point = reference_point if reference_point is not None else previous.get("reference_point")
    observables = observables if observables is not None else previous.get("observables")
    tolerance = tolerance if tolerance is not None else previous.get("tolerance", MODULATION_TOLERANCE_MAX)
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) \
            or not 0 < tolerance <= MODULATION_TOLERANCE_MAX:
        raise ConformanceError(f"the tolerance is relative, in (0, {MODULATION_TOLERANCE_MAX:g}]")
    if not isinstance(point, dict):
        raise ConformanceError("give --reference-point (or a declared conformance.reference_point)")
    phis = [n for n in block["parameters"] if point.get(n)]
    if len(phis) != 1 or not MODULATION_PARAMETER.match(phis[0]):
        raise ConformanceError(f"the reference point sets exactly one modulation parameter of {block['parameters']}")
    request = {"protocol": PROTOCOL, "provider": provider_id, "provider_version": version, "points": [point],
               "observables": observables, "want": ["lis"], "transport": None}
    problems = check_request(request)
    if problems:
        raise ConformanceError("reference request: " + "; ".join(problems))
    hook = hook or _load_hook(entrypoint)
    phi = float(point[phis[0]])
    lis_point = {k: v for k, v in point.items() if k not in block["parameters"]}
    lis = hook(dict(request, points=[lis_point]), lis_point)
    toa = hook(request, point)
    problems = _isotope_problems(lis, "LIS") + _isotope_problems(toa, "modulated")
    if not problems and (lis.get("phi_gv") or not math.isclose(float(toa.get("phi_gv") or 0.0), phi, rel_tol=1e-12)):
        problems.append(f"the LIS run must be unmodulated and the modulated run at phi = {phi:g} GV "
                        f"(got {lis.get('phi_gv')!r} and {toa.get('phi_gv')!r})")
    if not problems and set(lis["isotopes"]) != set(toa["isotopes"]):
        problems.append(f"the LIS and modulated runs give different isotopes: {sorted(lis['isotopes'])} and "
                        f"{sorted(toa['isotopes'])}")
    if problems:
        raise ConformanceError("; ".join(problems))
    nodes = []
    with tempfile.TemporaryDirectory(prefix="modulation-conformance-") as scratch:
        for nuc in sorted(toa["isotopes"]):
            z, a = toa["isotopes"][nuc]["charge"], toa["isotopes"][nuc]["mass_number"]
            table = Path(scratch) / f"{nuc}.json"
            pts = [[float(x), float(y)] for x, y in zip(lis["isotopes"][nuc]["ekn"], lis["isotopes"][nuc]["flux"])]
            table.write_text(json.dumps({"variable": "Ek_per_nucleon", "points": pts}), encoding="utf-8")
            lo, hi = min(p[0] for p in pts), max(p[0] for p in pts)
            for ekn, flux in zip(toa["isotopes"][nuc]["ekn"], toa["isotopes"][nuc]["flux"]):
                ekn_lis = float(ekn) + abs(z) * phi / a
                if not (lo <= ekn_lis <= hi and float(ekn) >= lo and float(flux) > 0):
                    continue   # the LIS table does not cover this node: not compared (no extrapolation)
                tool = force_field_tool(float(ekn), table, z, a, phi)
                nodes.append({"isotope": nuc, "ekn_gev": float(ekn), "provider": float(flux), "tool": tool,
                              "relative_deviation": abs(tool / float(flux) - 1.0)})
    compared = sorted({n["isotope"] for n in nodes})
    worst = max((n["relative_deviation"] for n in nodes), default=math.inf)
    passed = bool(nodes) and set(compared) == set(toa["isotopes"]) and worst <= tolerance
    conformance = {"reference_point": dict(point), "observables": observables, "tolerance": float(tolerance),
                   "result": {"status": "passed" if passed else "failed",
                              "max_relative_deviation": worst if nodes else None,
                              "nodes_compared": len(nodes), "isotopes": compared, "tool": FORCE_FIELD_TOOL}}
    return {"provider": provider_id, "provider_version": version, "implementation": block.get("implementation"),
            "conformance": conformance, "nodes": nodes, "lis_substitutes": lis.get("substitutes", []),
            "toa_substitutes": toa.get("substitutes", [])}


def _json_arg(text: str, what: str):
    path = Path(text)
    try:
        return json.loads(path.read_text(encoding="utf-8") if path.is_file() else text)
    except (OSError, ValueError) as exc:
        raise ConformanceError(f"{what}: not JSON or a readable JSON file: {exc}") from None


def conformance_main(args) -> int:
    try:
        point = _json_arg(args.reference_point, "--reference-point") if args.reference_point else None
        observables = _json_arg(args.observables, "--observables") if args.observables else None
        report = modulation_conformance(args.conformance, point, observables, args.tolerance)
    except ConformanceError as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}, indent=1))
        return 2
    passed = report["conformance"]["result"]["status"] == "passed"
    if args.out:
        try:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            write_json_atomic(args.out, report)
        except OSError as exc:
            print(json.dumps({"status": "rejected", "error": f"cannot write {args.out}: {exc}"}, indent=1))
            return 2
    print(json.dumps({"status": "passed" if passed else "failed", "provider": report["provider"],
                      "conformance": report["conformance"], "out": str(args.out) if args.out else None}, indent=1))
    return 0 if passed else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     epilog="Exit 0 ok, 2 invalid declarations or an unusable path; --conformance: "
                                            "0 passed, 1 failed, 2 unusable input.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", type=Path, metavar="PATH", help="registry file to write (outside the plugin)")
    mode.add_argument("--check", action="store_true", help="check the declarations; write nothing")
    mode.add_argument("--conformance", metavar="PROVIDER_ID",
                      help="run the conformance gate of the provider's declared modulation")
    parser.add_argument("--user-provider", type=Path, action="append", default=[], metavar="DECLARATION",
                        help="a user-supplied declaration file (repeatable)")
    parser.add_argument("--reference-point", metavar="JSON", help="--conformance: the reference point (JSON or a file)")
    parser.add_argument("--observables", metavar="JSON",
                        help="--conformance: the observable requests whose isotopes are compared (JSON or a file)")
    parser.add_argument("--tolerance", type=float, help="--conformance: relative tolerance, at most 1e-3")
    parser.add_argument("--out", type=Path, help="--conformance: file for the per-node comparison")
    args = parser.parse_args(argv)
    if args.conformance:
        return conformance_main(args)
    doc, problems = build(args.user_provider)
    summary = {"providers": [{"id": i["declaration"]["id"], "version": i["version"], "component": i["component"],
                              "user_supplied": i["user_supplied"]} for i in doc["providers"]]}
    if problems:
        print(json.dumps({"status": "rejected", "problems": problems, **summary}, indent=1))
        return 2
    if args.check:
        print(json.dumps({"status": "ok", **summary}, indent=1))
        return 0
    target = args.write.resolve()
    if target == ROOT.resolve() or ROOT.resolve() in target.parents:
        print(json.dumps({"status": "rejected", "problems": [f"{args.write} is inside the plugin; the registry holds "
                                                              "absolute paths and is never committed"]}, indent=1))
        return 2
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(target, doc)
    except OSError as exc:
        print(json.dumps({"status": "rejected", "problems": [f"cannot write {args.write}: {exc}"]}, indent=1))
        return 2
    print(json.dumps({"status": "written", "path": str(target), **summary}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
