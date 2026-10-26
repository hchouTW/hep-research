"""Vocabulary resolution chain of the semantic naming engine (spec §7.5).

A token resolves in the first layer that knows it:
  1. glossary: the project glossary (preferred terms, aliases, abbreviations and identifiers, every word of each);
  2. profile: the namespace vocabulary of the bound profile (experiment-specific abbreviations live only there);
  3. default: core/naming/data (HEP abbreviations and units, symbols, framework names, programming abbreviations,
     short English words);
  4. english: a general English word, approximated by its shape: three or more letters with a vowel. A one- or
     two-letter token or a token without a vowel must resolve in layers 1-3.
Digits always resolve. The forbidden table is not in the chain: a glossary never makes a generic name acceptable.
When a higher layer holds a word a lower layer also holds, the shadowing is recorded (Vocabulary.shadowed).
Standard library only; the glossary is loaded by core.terminology.glossary.load_glossary.
"""
from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
LAYERS = ("glossary", "profile", "default", "english")
WORD_SHAPE = re.compile(r"^[a-z]{3,}$")
VOWELS = set("aeiouy")


@cache
def _data_file(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def forbidden_table() -> dict:
    return _data_file("forbidden.json")


def default_words() -> frozenset[str]:
    abbr, sym, fw = _data_file("hep-abbreviations.json"), _data_file("symbols.json"), _data_file("framework-names.json")
    words = abbr["abbreviations"] + abbr["units"] + sym["symbols"] + fw["programming"] + fw["short_words"]
    return frozenset(w.lower() for w in words) | frozenset(w.lower() for w in fw["frameworks"])


def framework_names() -> frozenset[str]:
    return frozenset(_data_file("framework-names.json")["frameworks"])


def hook_methods() -> tuple[frozenset[str], tuple[str, ...]]:
    fw = _data_file("framework-names.json")
    return frozenset(fw["hook_methods"]), tuple(fw["hook_prefixes"])


def data_versions() -> dict:
    return {f.name: _data_file(f.name).get("vocabulary_version", _data_file(f.name).get("forbidden_version"))
            for f in sorted(DATA_DIR.glob("*.json"))}


def _words(text: str) -> set[str]:
    return {w.lower() for w in re.split(r"[\s_\-./]+", str(text)) if w}


def glossary_words(glossary: dict | None) -> set[str]:
    if not glossary:
        return set()
    out: set[str] = set()
    for e in glossary.get("entries", []):
        for term in (e.get("preferred") or {}).values():
            out |= _words(term)
        for terms in (e.get("aliases") or {}).values():
            for term in terms or []:
                out |= _words(term)
        for a in e.get("abbreviations") or []:
            out |= _words(a)
        for ident in e.get("identifiers") or []:
            out.add(str(ident).lower())
            out |= _words(ident)
    return out


def glossary_identifiers(glossary: dict | None) -> set[str]:
    """Single-token spellings a glossary declares (protected words of the tokenizer)."""
    out: set[str] = set()
    for e in (glossary or {}).get("entries", []):
        for ident in e.get("identifiers") or []:
            out.add(str(ident))
        for a in e.get("abbreviations") or []:
            if re.fullmatch(r"[A-Za-z0-9]+", str(a)):
                out.add(str(a).lower())
    return out


class Vocabulary:
    def __init__(self, glossary: dict | None = None, profile_terms=()):
        self.glossary = glossary
        self.layers = {"glossary": glossary_words(glossary), "profile": {str(t).lower() for t in profile_terms},
                       "default": set(default_words())}
        self.glossary_protected = glossary_identifiers(glossary)
        self._protected: dict[tuple, tuple[str, ...]] = {}
        self.shadowed = sorted(f"{w}: {hi} shadows {lo}" for i, hi in enumerate(LAYERS[:3]) for lo in LAYERS[i + 1:3]
                               for w in self.layers[hi] & self.layers[lo])

    def resolve(self, token: str) -> str | None:
        """The layer that resolves the token, or None."""
        t = token.lower()
        if t.isdigit():
            return "default"
        for layer in ("glossary", "profile", "default"):
            if t in self.layers[layer]:
                return layer
        if WORD_SHAPE.match(t) and set(t) & VOWELS:
            return "english"
        return None

    def protected(self, fixed_names=(), include_glossary: bool = True) -> tuple[str, ...]:
        """Protected words of the tokenizer: framework names, HEP abbreviations and units of two or more letters (chi2,
        p4, GeV), profile terms, the surface's fixed names and, unless include_glossary is false (the forbidden
        judgement), the glossary's identifiers and abbreviations; longest first, cached per argument."""
        key = (tuple(sorted(fixed_names)), include_glossary)
        if key in self._protected:
            return self._protected[key]
        abbr = _data_file("hep-abbreviations.json")["abbreviations"]
        out = set(framework_names()) | set(fixed_names)
        out |= {a for a in abbr + _data_file("hep-abbreviations.json")["units"] if len(a) >= 2}
        out |= {t for t in self.layers["profile"] if len(t) >= 2}
        if include_glossary:
            out |= self.glossary_protected
        self._protected[key] = tuple(sorted(out, key=len, reverse=True))
        return self._protected[key]
