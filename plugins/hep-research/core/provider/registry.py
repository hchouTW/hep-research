"""The provider registry the caller passes in (--provider-registry FILE). core/provider never searches for providers:
only an entrypoint listed here runs.

The file is generated (tools/provider_registry.py --write FILE) from the 'provider' fields of the plugin's adapter.json
and profile.json files, plus user-supplied declarations given explicitly; it holds absolute paths, so it is written
outside the repository and never committed. Format:
  {"format": "cr-provider-registry/1",
   "providers": [{"declaration": {<the provider declaration>}, "version": "<provider version>",
                  "entrypoint_path": "<absolute path of the entrypoint>", "component": "<declaring adapter or profile>",
                  "user_supplied": false}, ...]}
A user-supplied provider's outputs carry the label user-supplied (never evidence for a validated result).
"""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from core.provider.protocol import check_declaration

REGISTRY_FORMAT = "cr-provider-registry/1"


class RegistryError(ValueError):
    """A registry file that cannot be used."""


@dataclass(frozen=True)
class RegistryEntry:
    provider_id: str
    version: str
    entrypoint: Path
    declaration: dict
    component: str
    user_supplied: bool


def parse_registry(doc) -> dict[str, RegistryEntry]:
    """Entries by provider id from a registry document; RegistryError names every problem."""
    if not isinstance(doc, dict) or doc.get("format") != REGISTRY_FORMAT or not isinstance(doc.get("providers"), list):
        raise RegistryError(f"a provider registry is {{'format': '{REGISTRY_FORMAT}', 'providers': [...]}}")
    entries: dict[str, RegistryEntry] = {}
    problems: list[str] = []
    for k, item in enumerate(doc["providers"]):
        where = f"providers[{k}]"
        if not isinstance(item, dict) or set(item) != {"declaration", "version", "entrypoint_path", "component",
                                                       "user_supplied"}:
            problems.append(f"{where}: exactly declaration, version, entrypoint_path, component and user_supplied")
            continue
        problems += [f"{where}.declaration: {p}" for p in check_declaration(item["declaration"])]
        if not isinstance(item["version"], str) or not item["version"]:
            problems.append(f"{where}.version: a non-empty string")
        if not isinstance(item["user_supplied"], bool) or not isinstance(item["component"], str):
            problems.append(f"{where}: user_supplied is a boolean and component a string")
        path = Path(str(item["entrypoint_path"]))
        if not path.is_absolute():
            problems.append(f"{where}.entrypoint_path: an absolute path")
        else:
            try:
                mode = os.lstat(path).st_mode
            except OSError:
                mode = None
            if mode is None or not stat.S_ISREG(mode):
                problems.append(f"{where}.entrypoint_path: not a regular file (links refused): {path}")
        if problems:
            continue
        pid = item["declaration"]["id"]
        if pid in entries:
            problems.append(f"{where}: provider id '{pid}' is listed twice")
            continue
        entries[pid] = RegistryEntry(pid, item["version"], path, item["declaration"], item["component"],
                                     item["user_supplied"])
    if problems:
        raise RegistryError("; ".join(problems))
    return entries


def load_registry(path) -> dict[str, RegistryEntry]:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryError(f"cannot read the provider registry {path}: {exc}") from None
    return parse_registry(doc)
