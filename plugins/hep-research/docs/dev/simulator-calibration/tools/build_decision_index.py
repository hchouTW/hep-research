#!/usr/bin/env python3
"""Build the decision-status index of Part B from its own markers (Appendix D entries and tagged §19 items).
Usage: python3 -I tools/build_decision_index.py   (run from the package root)
Writes simcal-decision-index.json and simcal-decision-index.md.

Status comes only from the markers in the text: "**Accepted by the author (2026-11-09…).**", "**Merged into Dn; accepted by the
author (2026-11-09).**" or a tag ending "accepted by the author 2026-11-09" -> accepted; "**Decided by the author (2026-11-10).**" or
a tag ending "decided by the author 2026-11-10" -> decided; otherwise open. D31 is reported as front matter line 38 states it.

Kind of an open item follows front matter line 38: every open item is the author's, except the parts marked "Settled by
computation" (implemented as written until the author confirms) or "Settled by plugin source" (no decision), and except D19,
D25 and the open §14.1 items of §19 (the body's reading is implemented until the author confirms). A computation item whose text
reserves a part for the author ("Open for the author", "(2) for the author") needs the author for that part.

Blocks: the earliest §17 phase in the item's triage tag, with the overrides listed in OVERRIDE (placement rule of the author's
decision-sheet.md: a rule sits at the phase whose deliverable codes it)."""
import json, re
from collections import Counter, defaultdict
SPEC = "simulator-calibration-v7.37.4-clean-en.md"
L = open(SPEC, encoding="utf-8").read().split("\n")
def first(prefix): return next(i for i, l in enumerate(L) if l.startswith(prefix))
sD, s19, sA, sE = first("## Appendix D"), first("## 19."), first("## Appendix A"), first("## Appendix E")
TAG = re.compile(r"\[(?:triage|not triaged)[^\[\]]*\]")

# §19 triage row names, matched by content to the descriptions in decision-sheet.md (Inferred; triage.md itself is not available).
NAMES19 = {"The default source table for the correlation kernels": "§19-1", "Thresholds of shift": "§19-2", "the effect of the discarded part on the size of T_v": "§19-3",
           "The default list of alternative hypotheses": "§19-4", "The G8 cost for resimulation-level parameters": "§19-5", "Cross-event effects": "§19-6",
           "The simulation calibration results for the thresholds of §8.7": "§19-7", "Non-local or multimodal degeneracy": "§19-8", "How C++ density kernels are registered": "§19-9",
           "Whether reproducible numerical exceptions": "§19-14.1a", "Whether the \"budget revision\"": "§19-14.1b", "an exact recomputation with the same": "§19-14.1c",
           "Whether the execution environment": "§19-14.1d", "A member before the stop point": "§19-14.1e", "When the G5 renewal of cross-validation toys stops": "§19-14.1f",
           "the current text, as a documented": "§19-11", "Observables whose rounding is not negligible": "§19-12", "the threshold 0.15 is a design value": "§19-13",
           "The cost of the toy replica-difference construction": "§19-14", "The interpolation variance V_emu": "§19-15", "Generator tuning and the external source": "§19-g1",
           "scan (g4sim; settled by plugin source)": "§19-g2", "k_B and the E^L/E^S split": "§19-g3", "The stage hand-off format": "§19-g4a",
           "On the efficiency-map path, ε_c includ": "§19-g4b", "Decided by the author (2026-11-10). (The g4sim side": "§19-g4c", "Derived fields of the model identity": "§19-g5",
           "Enforcement for production use": "§19-g6", "Conditions for keeping old results": "§19-g7", "Posterior update of ξ": "§19-g8",
           "the confirmation with a real Geant4 mapping run": "§19-g9"}
OVERRIDE = {"§19-2": ("phase 2", "tag: blocks no phase; coded by G9/P8 in phase 2 (placement rule of decision-sheet.md)"),
            "§19-3": ("phase 2", "tag: blocks no phase; coded with G6 in phase 2 (placement rule of decision-sheet.md)"),
            "§19-13": ("phase 2", "tag: blocks no phase; a phase-2 deliverable per §17 (placement rule of decision-sheet.md)"),
            "D73": ("phase 2", "tag: blocks no phase; its open part is the §15.3.5 negative control, a phase-2 test"),
            "D85": ("phase 3", "tag: blocks no phase (phase-3 calibration; provisional-thresholds)")}

def classify(text):
    tag = " ".join(TAG.findall(text))
    if (re.search(r"\*\*Accepted by the author \(2026-11-09[^)]*\)\.\*\*", text) or re.search(r"\*\*Merged into D\d+; accepted by the author \(2026-11-09\)\.\*\*", text)
            or "accepted by the author 2026-11-09" in tag):
        st = "accepted 2026-11-09"
    elif "**Decided by the author (2026-11-10).**" in text or "decided by the author 2026-11-10" in tag:
        st = "decided 2026-11-10"
    else:
        st = "open"
    blocks = re.search(r"blocks (no phase|phases? [0-9][0-9–, or-]*)", tag)
    cls = re.match(r"\[(?:triage: )?([^;\]]+)", tag)
    return st, (cls.group(1).strip() if cls else ""), (blocks.group(1).strip() if blocks else ""), tag

p141 = next(i for i in range(s19, sA) if L[i].startswith("- ") and "Six points in the §14.1 execution binding" in L[i])
e141 = next(i for i in range(p141 + 1, sA) if L[i].startswith("- ") or L[i].startswith("#"))
def kind(r, text):
    if r["status"] != "open": return ""
    t = r["triage"]
    if r.get("item") in ("D19", "D25") or (r.get("name", "").startswith("§19-14.1") and t.startswith("accept?")):
        return "implement the body's reading (line 38); author confirms"
    if t.startswith("plugin fact"): return "settled by plugin source"
    if t.startswith("compute"):
        if re.search(r"Open for the author|\(\d\) for the author", text): return "needs the author (open part); the rest is implemented as written"
        return "computation: implemented as written; author confirms"
    if t.startswith("defer"): return "needs the author before the phase it is deferred to"
    return "needs the author"

D = []
for i in range(sD, sE):
    m = re.match(r"^\| (D\d+) \| ([^|]*) \|", L[i])
    if m:
        st, cls, bl, tag = classify(L[i])
        r = {"item": m.group(1), "line": i + 1, "where": m.group(2).strip(), "status": st, "triage": cls, "blocks": bl, "note": ""}
        if r["item"] == "D31" and st == "open":
            r["status"], r["note"] = "no open part", "front matter, line 38: its response-layer requirement is a plugin-source rule accepted on 2026-11-09"
        r["kind"] = kind(r, L[i])
        if r["item"] in OVERRIDE and r["status"] == "open":
            r["blocks"], r["note"] = OVERRIDE[r["item"]][0], (r["note"] + "; " if r["note"] else "") + OVERRIDE[r["item"]][1]
        pr = re.search(r"Proposed resolution[^:]*:\s*(.+?)(?:\[triage|\[not triaged|\|\s*$)", L[i])
        r["proposal"] = re.sub(r"\s+", " ", pr.group(1)).strip()[:300] if pr else ""
        D.append(r)
S19 = []
for i in range(s19, sA):
    if L[i].lstrip().startswith("- ") and TAG.search(L[i]):
        st, cls, bl, tag = classify(L[i])
        text = re.sub(r"\*\*|`", "", L[i].strip()[2:])
        name = next((v for k, v in NAMES19.items() if k.replace("`", "") in text), "")
        r = {"line": i + 1, "name": name, "start": re.sub(r"\s+", " ", text)[:110], "status": st, "triage": cls, "blocks": bl, "note": ""}
        r["kind"] = kind(r, L[i])
        if p141 < i < e141 and r["kind"] == "needs the author": r["kind"] = "implement the body's reading (line 38); author confirms"
        if name in OVERRIDE and st == "open":
            r["blocks"], r["note"] = OVERRIDE[name]
        S19.append(r)
assert len({r["name"] for r in S19 if r["name"]}) == len(S19), "a §19 item has no or a duplicate triage name"
json.dump({"spec": SPEC, "appendix_D": D, "section_19": S19}, open("simcal-decision-index.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def phase_key(b):
    m = re.search(r"\d", b or ""); return int(m.group()) if m else 9
BLOCKING = ("needs the author",)
out = ["# Decision-status index of Part B", "",
       "Generated by `tools/build_decision_index.py` from the markers of `simulator-calibration-v7.37.4-clean-en.md`; do not edit by hand. "
       "Status is read from the text only: an entry is **accepted** or **decided** when it carries the author's marker, otherwise **open**. "
       "The kind of an open item follows front matter line 38 (see the script's docstring and `simcal-task.md`, Section E7, item 1). "
       "\"Blocks\" is the earliest phase of §17 named in the item's triage tag, except the overrides noted in the tables (the placement rule of the author's `decision-sheet.md`). "
       "§19 names (§19-1 … §19-g9) are the `triage.md` row names, matched by content to `decision-sheet.md` (**Inferred**; `triage.md` is not in the package).", ""]
c = Counter(r["status"] for r in D); c19 = Counter(r["status"] for r in S19)
out += ["## Counts", "", "| Set | Total | accepted 2026-11-09 | decided 2026-11-10 | open | other |", "| --- | --- | --- | --- | --- | --- |",
        f"| Appendix D entries | {len(D)} | {c['accepted 2026-11-09']} | {c['decided 2026-11-10']} | {c['open']} | {len(D)-c['accepted 2026-11-09']-c['decided 2026-11-10']-c['open']} (D31: no open part) |",
        f"| Tagged §19 items | {len(S19)} | {c19['accepted 2026-11-09']} | {c19['decided 2026-11-10']} | {c19['open']} | 0 |", ""]
need = [r for r in D + S19 if r["kind"].startswith(BLOCKING)]
out += [f"Open items whose decision (or an open part of it) is the author's: **{len(need)}**. They stop the phase they block until the author decides (`simcal-task.md`, Section E7, item 1); `simcal-approvals.md` is their packet.", "",
        "## Open items by the phase they block", "",
        "| Blocks | Needs the author: Appendix D | Needs the author: §19 | Implemented as written, author confirms | Settled by plugin source |", "| --- | --- | --- | --- | --- |"]
groups = defaultdict(lambda: ([], [], [], []))
for r in D + S19:
    if r["status"] != "open": continue
    label = r.get("item") or f"{r['name']} ({r['line']})"
    k = r["kind"]
    col = 0 if (k.startswith(BLOCKING) and "item" in r) else 1 if k.startswith(BLOCKING) else 3 if k.startswith("settled") else 2
    groups[r["blocks"] or "not stated"][col].append(label)
for k in sorted(groups, key=lambda b: (phase_key(b), b)):
    out.append("| " + k + " | " + " | ".join(", ".join(x) or "—" for x in groups[k]) + " |")
out += ["", "## Appendix D", "", "| Entry | Line | Where | Status | Kind | Triage class | Blocks | Note |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
for r in D:
    out.append(f"| {r['item']} | {r['line']} | {r['where'].replace('|', '/')} | {r['status']} | {r['kind']} | {r['triage']} | {r['blocks']} | {r['note']} |")
out += ["", "## Tagged items of §19", "", "| Name | Line | Item (start of text) | Status | Kind | Triage class | Blocks | Note |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
for r in S19:
    out.append(f"| {r['name']} | {r['line']} | {r['start'].replace('|', '/')} | {r['status']} | {r['kind']} | {r['triage']} | {r['blocks']} | {r['note']} |")
open("simcal-decision-index.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print(dict(c), dict(c19), "needs the author:", len(need))
