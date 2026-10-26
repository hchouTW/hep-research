#!/usr/bin/env python3
"""Naming extractor of hep-statistics (semantic naming charter, hep-computing references/semantic-naming.md): write
the naming inventory of surface N10, the names of a statistical model, for contracts/naming_check.py.

N10 reads:
  - Combine datacards (text files with imax/jmax/kmax or bin, process and rate lines): channels (bin names),
    processes, nuisances (systematic lines: lnN, lnU, shape*, gmN, param, ...), rate parameters (rateParam) and the
    observed data data_obs (fixed by Combine: source external). A shape nuisance's histograms are derived from its
    name through the shapes lines ($PROCESS, $CHANNEL, $SYSTEMATIC): each nuisance carries them as derived targets
    on surface N3 (<process>_<nuisance>Up and Down in the named ROOT file), so a check with the N3 inventory sees a
    missing variation and a rename renames them too; each process carries its nominal templates the same way.
  - pyhf JSON workspaces (channels, observations, measurements, version): channels, samples (processes), modifiers
    (nuisances; a normfactor is a rate parameter, the measurement's POI a poi).
  - statistical-result artifacts: parameters_of_interest and nuisances.
Container: the channel (one-bin datacard: its bin; a combined card: the file stem; pyhf: the channel), so the
near-duplicate rule compares names across channels. References: text mentions in every text file in scope.

Usage: python3 extract_names.py --surface N10 --out INV.json [--root DIR] [--scope DIR ...] [--changed REV]
--root is the project (default: the working directory); --scope folders are relative to it. The output is a working
file of <project>/naming/, refused inside artifacts_dir. Prints one JSON object with a status key. Exit codes: 0 written,
2 bad input, 3 written but zero inputs scanned (the check reports N10 unsupported). Standard library only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True  # a script run from an installed plugin leaves no __pycache__ in it
PLUGIN = Path(__file__).resolve().parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from core.naming.extract import (Builder, TextIndex, artifacts, coverage, files_of, line_of,  # noqa: E402
                                 mark_changed_by_file, norm_path, now, read_text)
from core.naming.extract import main as run_cli  # noqa: E402
from core.naming.model import new_inventory  # noqa: E402
from core.status import add_status_argument  # noqa: E402

VERSION = "1.0.0"
EXTRACTOR = {"id": "skills/hep-statistics/scripts/extract_names.py", "version": VERSION}
CARD_SUFFIXES = (".txt", ".dat", ".card", ".datacard")
CARD_HEAD = re.compile(r"^\s*(imax|jmax|kmax)\b", re.M)
SYST_TYPES = re.compile(r"^(lnN|lnU|gmN|gmM|trG|unif|dFD|dFD2|shape\??|shapeN|shapeN2|shapeU|shape\*|param|"
                        r"flatParam|extArg|discrete|rateParam)$")
DIRECTIVES = {"imax", "jmax", "kmax", "bin", "observation", "process", "rate", "shapes", "group", "nuisance",
              "autoMCStats", "*", "-----", "#"}


def _shape_for(shapes, proc: str, chan: str):
    """The shapes line that applies to (process, channel): exact > process with any channel > any process."""
    best, rank = None, -1
    for p, c, f, h, hs in shapes:
        r = (2 if p == proc else 0 if p == "*" else -9) + (1 if c == chan else 0 if c == "*" else -9)
        if r > rank and r >= 0:
            best, rank = (f, h, hs), r
    return best


def _subst(pattern: str, proc: str, chan: str, syst: str = "") -> str | None:
    if "$MASS" in pattern:
        return None  # a mass point is chosen at run time; the name cannot be derived here
    return pattern.replace("$PROCESS", proc).replace("$CHANNEL", chan).replace("$SYSTEMATIC", syst)


def _root_target(card: str, fname: str, hist: str, kind: str) -> dict | None:
    if not fname or fname == "FAKE" or not hist:
        return None
    rel = norm_path((PurePosixPath(card).parent / fname).as_posix())
    folder, _, name = hist.rpartition("/")
    if not rel or not name:
        return None
    return {"surface": "N3", "name": name, "file": rel, "container": folder or "/", "kind": kind, "derived": True}


def read_datacard(rel: str, text: str, b: Builder) -> bool:
    lines = [ln.split("#", 1)[0].rstrip() for ln in text.splitlines()]
    if not CARD_HEAD.search(text) and not (any(ln.startswith("process") for ln in lines)
                                           and any(ln.startswith("rate") for ln in lines)):
        return False
    shapes, bin_rows, proc_rows, after_rate, systs = [], [], [], False, []
    for n, ln in enumerate(lines, 1):
        parts = ln.split()
        if not parts:
            continue
        head = parts[0]
        if head == "shapes" and len(parts) >= 5:
            shapes.append((parts[1], parts[2], parts[3], parts[4], parts[5] if len(parts) > 5 else ""))
        elif head == "bin":
            bin_rows.append((n, parts[1:]))
        elif head == "process":
            proc_rows.append((n, parts[1:]))
        elif head == "rate":
            after_rate = True
        elif after_rate and head not in DIRECTIVES and not head.startswith("-") and len(parts) >= 2:
            systs.append((n, parts))
    chans = list(dict.fromkeys(bin_rows[0][1])) if bin_rows else []
    columns = bin_rows[-1][1] if len(bin_rows) > 1 else (bin_rows[0][1] if bin_rows else [])
    name_row = next((r for r in proc_rows if not all(re.fullmatch(r"-?\d+", x) for x in r[1])), None)
    procs = name_row[1] if name_row else []
    container = chans[0] if len(chans) == 1 else PurePosixPath(rel).stem
    for c in chans:
        b.add("channel", c, rel, container, bin_rows[0][0], f"channel {c}")
    nominal: dict[str, list] = {}
    for col, p in enumerate(procs):
        chan = columns[col] if col < len(columns) else (chans[0] if chans else "")
        sh = _shape_for(shapes, p, chan)
        if sh:
            t = _root_target(rel, sh[0], _subst(sh[1], p, chan) or "", "template")
            if t:
                nominal.setdefault(p, []).append(t)
    for p in dict.fromkeys(procs):
        b.add("process", p, rel, container, name_row[0], f"process {p}", targets=nominal.get(p))
    if any(s[0] == "data_obs" for s in shapes) or any(ln.startswith("observation") for ln in lines):
        b.add("observed_data", "data_obs", rel, container, line_of(text, "observation"), "data_obs", source="external")
    for n, parts in systs:
        name, typ = parts[0], parts[1]
        if typ == "group" or (len(parts) > 2 and parts[1] == "group"):
            continue
        if not SYST_TYPES.match(typ):
            continue
        kind = "rate_parameter" if typ == "rateParam" else "nuisance"
        targets = []
        if typ.startswith("shape"):
            values = parts[2:]
            for col, v in enumerate(values):
                if v in ("-", "0") or col >= len(procs):
                    continue
                p, chan = procs[col], columns[col] if col < len(columns) else (chans[0] if chans else "")
                sh = _shape_for(shapes, p, chan)
                if not sh or not sh[2]:
                    continue
                base = _subst(sh[2], p, chan, name)
                for suffix in ("Up", "Down"):
                    t = _root_target(rel, sh[0], f"{base}{suffix}" if base else "", "shape-histogram")
                    if t and t not in targets:
                        targets.append(t)
        b.add(kind, name, rel, container, n, " ".join(parts), targets=targets or None)
    return True


def read_pyhf(rel: str, doc: dict, text: str, b: Builder) -> bool:
    if not (isinstance(doc, dict) and isinstance(doc.get("channels"), list) and "measurements" in doc):
        return False
    pois = set()
    for m in doc.get("measurements") or []:
        poi = ((m or {}).get("config") or {}).get("poi")
        if isinstance(poi, str):
            pois.add(poi)
            b.add("poi", poi, rel, f"measurement:{m.get('name', '')}", line_of(text, f'"{poi}"'), f"poi {poi}")
    for ch in doc["channels"]:
        cname = ch.get("name") if isinstance(ch, dict) else None
        if not isinstance(cname, str):
            continue
        b.add("channel", cname, rel, cname, line_of(text, f'"{cname}"'), f"channel {cname}")
        seen = set()
        for smp in ch.get("samples") or []:
            sname = smp.get("name") if isinstance(smp, dict) else None
            if isinstance(sname, str):
                b.add("process", sname, rel, cname, line_of(text, f'"{sname}"'), json.dumps(smp.get("data")))
            for mod in (smp.get("modifiers") or []) if isinstance(smp, dict) else []:
                mname, mtype = (mod or {}).get("name"), (mod or {}).get("type")
                if not isinstance(mname, str) or mname in seen or mname in pois:
                    continue
                seen.add(mname)
                kind = "rate_parameter" if mtype == "normfactor" else "nuisance"
                b.add(kind, mname, rel, cname, line_of(text, f'"{mname}"'), f"{mtype} {mname}")
    return True


def extract_n10(root: Path, scopes, changed: str | None = None, args=None) -> dict:
    root = Path(root).resolve()
    paths = files_of(root, scopes)
    index = TextIndex(root, paths)
    b = Builder("N10", EXTRACTOR)
    scanned = 0
    for rel in paths:
        if rel.endswith(CARD_SUFFIXES):
            text = read_text(root, rel)
            if text is not None and read_datacard(rel, text, b):
                scanned += 1
        elif rel.endswith(".json"):
            text = read_text(root, rel)
            if text is None or ('"channels"' not in text and '"artifact_type"' not in text):
                continue
            try:
                doc = json.loads(text)
            except ValueError:
                continue
            if read_pyhf(rel, doc, text, b):
                scanned += 1
    for rel, doc, text in artifacts(root, [p for p in paths if p.endswith(".json")], ("statistical-result",)):
        scanned += 1
        ext = doc.get("extension") or {}
        cont = f"artifact:{doc.get('artifact_id', rel)}"
        status = doc.get("status") if isinstance(doc.get("status"), str) else None
        for poi in ext.get("parameters_of_interest") or []:
            b.add("poi", poi, rel, cont, line_of(text, f'"{poi}"'), f"poi {poi}", meaning={"status_label": status})
        for nu in ext.get("nuisances") or []:
            name = nu if isinstance(nu, str) else (nu or {}).get("name") if isinstance(nu, dict) else None
            b.add("nuisance", name, rel, cont, line_of(text, f'"{name}"'), json.dumps(nu, sort_keys=True),
                  meaning={"status_label": status})
    entities = b.build(index, coverage(["N10"], scopes))
    if changed:
        mark_changed_by_file(root, changed, scopes, entities)
    return new_inventory("N10", scopes, scanned, entities, now(), changed_since=changed)


EXTRACT = {"N10": extract_n10}


def _options(ap) -> None:
    add_status_argument(ap)


def main(argv=None) -> int:
    return run_cli(argv, doc=__doc__, readers={**EXTRACT, "__options__": _options}, extractor=EXTRACTOR)


if __name__ == "__main__":
    sys.exit(main())
