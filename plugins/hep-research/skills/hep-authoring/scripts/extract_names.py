#!/usr/bin/env python3
"""Naming extractor of hep-authoring (semantic naming charter, hep-computing references/semantic-naming.md): write the
naming inventory of one surface for contracts/naming_check.py.

Surfaces:
  N14 LaTeX names of every .tex file in scope: labels (\\label), macros (\\newcommand, \\renewcommand,
      \\DeclareMathOperator, \\def), label references (\\ref, \\eqref, \\cref, \\Cref, \\autoref, \\pageref; each
      targets its label, so a reference to a label no file declares is caught), figure files (\\includegraphics)
      and table files (\\input, \\include) as written, each targeting the N2 file it resolves to (relative to the
      .tex file, then the root; a missing extension is tried as .pdf, .png, .eps, .jpg, .tex). Label references
      come from the label-reference entities; macro references are its uses (\\name).
  N15 BibTeX keys of every .bib file in scope; meaning.concept_id is the record's DOI (doi:...) or arXiv id
      (arxiv:...), so one record under two keys is a duplicate. References: the \\cite-family commands of the .tex
      files (\\cite, \\citep, \\citet, \\nocite, \\parencite, \\textcite, ...).
Comments (% to the end of a line) are left out.

Usage: python3 extract_names.py --surface N14|N15 --out INV.json [--root DIR] [--scope DIR ...] [--changed REV]
--root is the project (default: the working directory); --scope folders are relative to it. The output is a working
file of <project>/naming/, refused inside artifacts_dir. Prints one JSON object with a status key. Exit codes: 0 written,
2 bad input, 3 written but zero inputs scanned (the check reports the surface unsupported). Standard library only.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True  # a script run from an installed plugin leaves no __pycache__ in it
PLUGIN = Path(__file__).resolve().parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from core.naming.extract import Builder, coverage, files_of, mark_changed_by_file, norm_path, now, read_text  # noqa: E402
from core.naming.extract import main as run_cli  # noqa: E402
from core.naming.model import new_inventory  # noqa: E402
from core.status import add_status_argument  # noqa: E402

VERSION = "1.0.0"
EXTRACTOR = {"id": "skills/hep-authoring/scripts/extract_names.py", "version": VERSION}
COMMENT = re.compile(r"(?<!\\)%.*$")
LABEL = re.compile(r"\\label\{([^}]+)\}")
REF = re.compile(r"\\(?:ref|eqref|cref|Cref|autoref|pageref|vref|nameref)\*?\{([^}]+)\}")
MACRO = re.compile(r"\\(?:newcommand|renewcommand|providecommand|DeclareMathOperator)\*?\s*\{?\\([A-Za-z@]+)\}?|"
                   r"\\def\s*\\([A-Za-z@]+)")
GRAPHICS = re.compile(r"\\includegraphics\*?(?:\[[^\]]*\])?\{([^}]+)\}")
INPUT = re.compile(r"\\(?:input|include|subfile)\{([^}]+)\}")
CITE = re.compile(r"\\(?:[A-Za-z]*cite[A-Za-z]*|nocite)\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}")
BIB_ENTRY = re.compile(r"^\s*@([A-Za-z]+)\s*[{(]\s*([^,\s]+)\s*,", re.M)
BIB_FIELD = re.compile(r"\b(doi|eprint)\s*=\s*[{\"]([^}\"]+)[}\"]", re.I)
TRY_SUFFIXES = ("", ".pdf", ".png", ".eps", ".jpg", ".jpeg", ".tex")


def _lines(text: str) -> list[str]:
    return [COMMENT.sub("", ln) for ln in text.splitlines()]


def _resolve(root: Path, tex: str, written: str, files: set[str]) -> str | None:
    for base in (PurePosixPath(tex).parent.as_posix(), ""):
        for suf in TRY_SUFFIXES:
            cand = norm_path(f"{base}/{written}{suf}" if base else f"{written}{suf}")
            if cand and cand in files:
                return cand
    return None


def extract_n14(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    root = Path(root).resolve()
    paths = files_of(root, scopes)
    every = set(paths)
    tex = [p for p in paths if p.endswith(".tex")]
    b = Builder("N14", EXTRACTOR)
    texts = {rel: _lines(read_text(root, rel) or "") for rel in tex}
    macro_uses: dict[str, list[dict]] = {}
    for rel, lines in texts.items():
        for n, ln in enumerate(lines, 1):
            for m in re.finditer(r"\\([A-Za-z@]+)", ln):
                macro_uses.setdefault(m.group(1), []).append({"from": f"{rel}:{n}", "kind": "uses"})
    for rel, lines in texts.items():
        for n, ln in enumerate(lines, 1):
            for m in LABEL.finditer(ln):
                b.add("label", m.group(1).strip(), rel, rel, n, ln.strip(), refs=[])
            for m in REF.finditer(ln):
                for key in m.group(1).split(","):
                    key = key.strip()
                    b.add("label_reference", key, rel, rel, n, ln.strip(), refs=[],
                          targets=[{"surface": "N14", "name": key, "kind": "label", "entity_kind": "label"}])
            for m in MACRO.finditer(ln):
                name = m.group(1) or m.group(2)
                refs = [r for r in macro_uses.get(name, []) if r["from"] != f"{rel}:{n}"]
                b.add("macro", name, rel, rel, n, ln.strip(), refs=refs)
            for pat, kind in ((GRAPHICS, "figure_file"), (INPUT, "table_file")):
                for m in pat.finditer(ln):
                    written = m.group(1).strip()
                    hit = _resolve(root, rel, written, every)
                    t = {"surface": "N2", "name": PurePosixPath(hit or written).name, "kind": "includes"}
                    if hit:
                        t["file"] = hit
                    b.add(kind, written, rel, rel, n, ln.strip(), refs=[], targets=[t])
    entities = b.build(None, coverage(["N14"], scopes))
    if changed:
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N14", scopes, len(tex), entities, now(), changed_since=changed)


def extract_n15(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    root = Path(root).resolve()
    paths = files_of(root, scopes)
    cites: dict[str, list[dict]] = {}
    for rel in (p for p in paths if p.endswith(".tex")):
        for n, ln in enumerate(_lines(read_text(root, rel) or ""), 1):
            for m in CITE.finditer(ln):
                for key in m.group(1).split(","):
                    cites.setdefault(key.strip(), []).append({"from": f"{rel}:{n}", "kind": "cites"})
    b = Builder("N15", EXTRACTOR)
    bibs = [p for p in paths if p.endswith(".bib")]
    for rel in bibs:
        text = read_text(root, rel) or ""
        starts = [(m.start(), m) for m in BIB_ENTRY.finditer(text)]
        for i, (pos, m) in enumerate(starts):
            if m.group(1).lower() in ("comment", "string", "preamble"):
                continue
            body = text[pos:starts[i + 1][0] if i + 1 < len(starts) else len(text)]
            fields = {k.lower(): v.strip() for k, v in BIB_FIELD.findall(body)}
            concept = (f"doi:{fields['doi'].lower()}" if "doi" in fields else
                       f"arxiv:{fields['eprint'].lower()}" if "eprint" in fields else None)
            line = text.count("\n", 0, pos) + 1
            b.add("bib_key", m.group(2), rel, rel, line, body.strip(), refs=list(cites.get(m.group(2), [])),
                  meaning={"concept_id": concept}, end=line + body.count("\n"))
    entities = b.build(None, coverage(["N15"], scopes))
    if changed:
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N15", scopes, len(bibs), entities, now(), changed_since=changed)


EXTRACT = {"N14": extract_n14, "N15": extract_n15}


def _options(ap) -> None:
    add_status_argument(ap)


def main(argv=None) -> int:
    return run_cli(argv, doc=__doc__, readers={**EXTRACT, "__options__": _options}, extractor=EXTRACTOR)


if __name__ == "__main__":
    sys.exit(main())
