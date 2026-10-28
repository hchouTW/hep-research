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

Usage:
  python3 tools/provider_registry.py --write "$CRPROP_OUT/registry.json" [--user-provider DECLARATION.json ...]
  python3 tools/provider_registry.py --check         # check the declarations only; write nothing
A user-supplied declaration file holds one declaration (or a list) with a 'version'; its entrypoint is relative to
the file's folder. Output: one JSON object (status written|ok|rejected, providers, problems). Exit 0 ok, 2 an invalid
declaration, a duplicate provider id, a path inside the plugin or an unwritable path.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.schema import validate  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.provider.entrypoint import write_json_atomic  # noqa: E402
from core.provider.protocol import check_declaration, declarations_of  # noqa: E402
from core.provider.registry import REGISTRY_FORMAT, parse_registry  # noqa: E402

DECLARATIONS_SCHEMA = {"$ref": "cr_provider.json#/$defs/declarations"}


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     epilog="Exit 0 ok, 2 invalid declarations or an unusable path.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", type=Path, metavar="PATH", help="registry file to write (outside the plugin)")
    mode.add_argument("--check", action="store_true", help="check the declarations; write nothing")
    parser.add_argument("--user-provider", type=Path, action="append", default=[], metavar="DECLARATION",
                        help="a user-supplied declaration file (repeatable)")
    args = parser.parse_args(argv)
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
