"""Shared scientific vocabulary: core terms plus namespaced profile extensions."""
from __future__ import annotations

import json
import re
from pathlib import Path

CORE_FILE = Path(__file__).resolve().parent / "vocab" / "core.json"
NAMESPACED = re.compile(r"^([a-z][a-z0-9-]*):([A-Za-z0-9_.+-]+)$")
ALIASES = {"conventions": "convention_keys"}


class Vocabulary:
    def __init__(self) -> None:
        data = json.loads(CORE_FILE.read_text(encoding="utf-8"))
        self._core = {k: set(v) for k, v in data["vocabularies"].items()}
        self._ext: dict[str, set[str]] = {k: set() for k in self._core}
        self.problems: list[str] = []    # extension problems collected by with_profiles

    def core(self, name: str) -> set[str]:
        return set(self._core[name])

    def names(self) -> list[str]:
        return sorted(self._core)

    def extend(self, name: str, terms, namespaces) -> list[str]:
        """Register profile terms. Returns problems (empty on success).

        Terms must be '<ns>:<x>' with <ns> one of the profile's declared namespaces."""
        problems = []
        namespaces = {namespaces} if isinstance(namespaces, str) else set(namespaces)
        name = ALIASES.get(name, name)
        if name not in self._core:
            return [f"unknown vocabulary '{name}' (core vocabularies: {self.names()})"]
        for term in terms:
            m = NAMESPACED.match(term)
            if not m or m.group(1) not in namespaces:
                problems.append(f"extension term '{term}' must be namespaced with one of {sorted(namespaces)}")
            else:
                self._ext[name].add(term)
        return problems

    def has(self, name: str, term: str) -> bool:
        return term in self._core.get(name, ()) or term in self._ext.get(name, ())

    @classmethod
    def with_profiles(cls, profiles) -> "Vocabulary":
        """Build a vocabulary extended by loaded profile.json dicts (see contracts.registry).

        Rejected extensions are listed in the returned vocabulary's `problems`."""
        v = cls()
        for p in profiles:
            ns = declared_namespaces(p)
            for name, terms in (p.get("vocabulary_extensions") or {}).items():
                v.problems += [f"{p.get('id', '?')}: {x}" for x in v.extend(name, terms, ns)]
        return v


def declared_namespaces(profile: dict) -> list[str]:
    """Namespaces a profile may use: vocabulary_namespaces, else [evidence_namespace]."""
    return list(profile.get("vocabulary_namespaces") or [profile.get("evidence_namespace")])
