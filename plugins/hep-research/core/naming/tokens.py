"""Name tokenizer of the semantic naming engine (charter §5, spec §7.1).

1. Strip prefixes: a namespace (`ns:`), a label prefix (`fig:`, `eq:`, `tab:`, `sec:`), the ROOT conventions (`k`
   before a capital, `h_`), leading dashes of a CLI flag, leading and trailing underscores; with strip_extension, a
   known file extension.
2. Longest match of protected words at token boundaries: a protected word written in lower case matches in any case,
   one with capitals matches exactly; the match keeps the spelling of the name.
3. The rest is split at separators (`_`, `-`, `.`), case boundaries and letter-digit boundaries, and lower-cased.

tokenize("kElectronMassGeV", {"gev"}) == ["electron", "mass", "GeV"]. Standard library only.
"""
from __future__ import annotations

import re
from functools import lru_cache

SEPARATORS = "_-. /"
LABEL_PREFIX = re.compile(r"^(?:fig|eq|tab|sec|ch|app|lst):")
NAMESPACE = re.compile(r"^[a-z][a-z0-9-]*:(?=.)")
ROOT_K = re.compile(r"^k(?=[A-Z])")
FILE_EXTENSIONS = frozenset({
    "root", "pdf", "png", "svg", "eps", "jpg", "jpeg", "json", "jsonl", "txt", "csv", "tsv", "dat", "npz", "npy", "h5",
    "hdf5", "parquet", "pkl", "pt", "onnx", "py", "c", "cc", "cxx", "cpp", "h", "hh", "hpp", "sh", "md", "tex", "bib",
    "toml", "yaml", "yml", "ini", "cfg", "log", "gz", "bz2", "xz", "zip", "tar", "html", "xml", "lhe", "hepmc"})


def strip_prefixes(name: str, strip_extension: bool = False) -> str:
    s = name
    if strip_extension:
        while "." in s.lstrip("."):
            stem, ext = s.rsplit(".", 1)
            if ext.lower() not in FILE_EXTENSIONS or not stem:
                break
            s = stem
    s = LABEL_PREFIX.sub("", s)
    s = NAMESPACE.sub("", s)
    s = s.lstrip("-")
    s = ROOT_K.sub("", s)
    if s.startswith("h_") and len(s) > 2:
        s = s[2:]
    return s.strip("_")


def _boundaries(s: str) -> set[int]:
    """Indices where a token may start or end: the ends, around separators, case and letter-digit changes."""
    out = {0, len(s)}
    for i in range(1, len(s)):
        a, b = s[i - 1], s[i]
        if a in SEPARATORS or b in SEPARATORS:
            out.add(i)
        elif a.islower() and b.isupper():
            out.add(i)
        elif a.isupper() and b.isupper() and i + 1 < len(s) and s[i + 1].islower():
            out.add(i)
        elif a.isalpha() != b.isalpha() and (a.isalnum() and b.isalnum()):
            out.add(i)
    return out


def _split_plain(chunk: str) -> list[str]:
    bounds = sorted(_boundaries(chunk))
    parts = [chunk[a:b] for a, b in zip(bounds, bounds[1:])]
    return [p.lower() for p in parts if p and not all(c in SEPARATORS for c in p)]


def _matches(s: str, i: int, word: str) -> bool:
    piece = s[i:i + len(word)]
    return piece == word if not word.islower() else piece.lower() == word


@lru_cache(maxsize=64)
def _starts(words: tuple) -> dict[str, list[str]]:
    """First character (lower case) -> candidate words, longest first."""
    out: dict[str, list[str]] = {}
    for w in words:
        if w:
            out.setdefault(w[0].lower(), []).append(w)
    return out


def tokenize(name: str, protected=(), strip_extension: bool = False) -> list[str]:
    """protected: any iterable of words, or a tuple already sorted longest first (Vocabulary.protected)."""
    s = strip_prefixes(name, strip_extension)
    words = protected if isinstance(protected, tuple) else tuple(sorted({w for w in protected if w}, key=len, reverse=True))
    bounds = _boundaries(s)
    starts = _starts(words)
    tokens: list[str] = []
    buf, i = "", 0
    while i < len(s):
        hit = None
        if i in bounds:
            hit = next((w for w in starts.get(s[i].lower(), ()) if _matches(s, i, w) and i + len(w) in bounds), None)
        if hit:
            tokens += _split_plain(buf)
            buf = ""
            tokens.append(s[i:i + len(hit)])
            i += len(hit)
            continue
        buf += s[i]
        i += 1
    tokens += _split_plain(buf)
    return tokens


def content_tokens(tokens) -> list[str]:
    """Tokens that carry content: digits alone do not."""
    return [t for t in tokens if not t.isdigit()]
