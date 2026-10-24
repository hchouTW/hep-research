#!/usr/bin/env python3
"""Reference inventory: every file under skills/*/references/ with its owner, size, citations,
last change and textual overlap with other references.

For each reference: owner skill, bytes and lines, which plugin files cite it (a Markdown link to it or its file name
in backticks or plain text; its own file, docs/, CHANGELOG.md and VALIDATION.md excluded), whether its owner's SKILL.md links it, and the last commit that
touched it (from git; in a shallow clone that is the oldest commit available, said so in the output). Overlap is the
Jaccard index and the containment (shared / smaller) of word 8-shingles between two references (lowercased,
punctuation removed); pairs at or above --threshold or containment 0.15 are listed, and references with similar names are grouped. Overlap is a hypothesis to read, not proof of
duplication. One owner per topic (upgrade plan X2): a listed pair whose two references belong to different skills is
an error in both modes (status fail, exit 1); keep the topic in its owner's reference and link to it from the other.
Pairs inside one skill stay listed only.

Usage: python3 tools/reference_inventory.py [--json docs/reference-inventory.json] [--md docs/reference-inventory.md]
       [--threshold 0.08] [--check] [--root PLUGIN_ROOT]
--check regenerates in memory and exits 1 if the committed files differ in anything except the git columns
(so a new or removed reference, or a changed citation, is caught). Standard library only.
Soft budget (upgrade plan B-05): both modes print "warnings" for the routing part of an entry reference above
ROUTING_SOFT_BYTES (4 KB) and for any reference above REFERENCE_SOFT_BYTES (24 KB); warnings never change the exit
code. The entry reference of a skill is the first reference linked in its SKILL.md "## Resources" section; its
routing part is the text before the first level-2 heading plus every level-2 section whose heading names routing, an
index, contents, when to read the file or choosing a tool.
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHINGLE = 8
CONTAINMENT = 0.15  # also list a pair when this share of the smaller file's shingles is in the other
RECORDS = {"CHANGELOG.md", "VALIDATION.md"}
MAINTENANCE_LISTS = {"tools/wiring_known_gaps.json"}  # lists pages to check them, does not cite them
MAX_GROUP = 4       # a name token shared by more files than this is a topic word, not a family
ROUTING_SOFT_BYTES = 4096
REFERENCE_SOFT_BYTES = 24576
ROUTING_HEADING = re.compile(r"routing|routes|index|contents|when to read|choosing a tool", re.I)
NAME_STOP = {"and", "guide", "the", "of", "for", "in", "to", "a", "md", "reference", "principles"}


def refs(root: Path) -> list[Path]:
    return sorted(root.glob("skills/*/references/**/*.md"))


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def shingles(text: str) -> set:
    w = words(text)
    return {" ".join(w[i:i + SHINGLE]) for i in range(max(len(w) - SHINGLE + 1, 0))}


def corpus(root: Path) -> dict[str, str]:
    out = {}
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        # docs/ (the inventory itself, maintenance maps), the change records, the release manifests (which list
        # every file) and the wiring lint's known gaps are not citations
        if (p.is_file() and p.suffix in (".md", ".json", ".py") and "__pycache__" not in p.parts
                and rel.parts[0] not in ("docs", "release-manifests")
                and rel.as_posix() not in RECORDS | MAINTENANCE_LISTS):
            try:
                out[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                pass
    return out


def git_last(root: Path, rel: str) -> str:
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%h %ad", "--date=short", "--", rel], cwd=root,
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or "untracked"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def shallow(root: Path) -> bool:
    try:
        r = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=root, capture_output=True, text=True, timeout=120)
        return r.stdout.strip() == "true"
    except OSError:
        return False


def name_key(stem: str) -> frozenset:
    """Name tokens without filler words, with a plural s removed (diagrams -> diagram)."""
    toks = (t[:-1] if len(t) > 4 and t.endswith("s") and not t.endswith("ss") else t for t in re.split(r"[-_]", stem.lower()))
    return frozenset(t for t in toks if t not in NAME_STOP and not t.isdigit())


def build(root: Path, threshold: float, with_git: bool = True) -> dict:
    files = refs(root)
    texts = corpus(root)
    rows, sh = [], {}
    for p in files:
        rel = p.relative_to(root).as_posix()
        skill = p.relative_to(root).parts[1]
        text = p.read_text(encoding="utf-8")
        sh[rel] = shingles(text)
        name = p.name
        cited = sorted(f for f, t in texts.items() if f != rel and name in t)
        skill_md = (root / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        row = {"path": rel, "owner": skill, "bytes": p.stat().st_size, "lines": text.count("\n") + 1,
               "linked_from_skill_md": f"references/{p.relative_to(root / 'skills' / skill / 'references').as_posix()}" in skill_md,
               "cited_by": cited, "cited_by_other_skills": sorted({f.split("/")[1] for f in cited
                                                                  if f.startswith("skills/") and f.split("/")[1] != skill})}
        if with_git:
            row["last_commit"] = git_last(root, rel)
        rows.append(row)
    pairs = []
    for a, b in itertools.combinations(sh, 2):
        if not sh[a] or not sh[b]:
            continue
        common = len(sh[a] & sh[b])
        j = common / len(sh[a] | sh[b])
        c = common / min(len(sh[a]), len(sh[b]))
        if j >= threshold or c >= CONTAINMENT:
            pairs.append({"a": a, "b": b, "jaccard": round(j, 3), "containment": round(c, 3), "shared_shingles": common})
    pairs.sort(key=lambda x: (-x["containment"], -x["jaccard"]))
    groups = {}
    for p in files:
        for q in files:
            shared = name_key(p.stem) & name_key(q.stem)
            if p < q and shared and p.parent.parent == q.parent.parent:
                for k in shared:  # one group per shared token, kept below when it stays small (a real family)
                    groups.setdefault(k, set()).update({p.relative_to(root).as_posix(), q.relative_to(root).as_posix()})
    by_skill = {}
    for r in rows:
        s = by_skill.setdefault(r["owner"], {"references": 0, "bytes": 0, "uncited": 0})
        s["references"] += 1
        s["bytes"] += r["bytes"]
        s["uncited"] += not r["cited_by"]
    out = {"generated_by": "tools/reference_inventory.py", "shingle_words": SHINGLE, "threshold": threshold,
           "by_skill": by_skill, "references": rows, "overlap_pairs": pairs,
           "name_groups": {k: sorted(v) for k, v in sorted(groups.items()) if 2 <= len(v) <= MAX_GROUP}}
    if with_git:
        out["git_note"] = ("shallow clone: last_commit is the oldest commit available for files unchanged since then, "
                           "not their last meaningful change") if shallow(root) else "full history"
    return out


def cross_skill_overlaps(inv: dict) -> list[dict]:
    """Overlapping pairs whose references belong to different skills (X2: one owner per topic)."""
    return [p for p in inv["overlap_pairs"] if p["a"].split("/")[1] != p["b"].split("/")[1]]


def overlap_problems(inv: dict) -> list[str]:
    return [f"one owner per topic: {p['a']} and {p['b']} overlap (Jaccard {p['jaccard']}, containment "
            f"{p['containment']}); keep the text in the owner's reference and link to it" for p in cross_skill_overlaps(inv)]


def entry_references(root: Path) -> list[str]:
    """The first reference each SKILL.md's '## Resources' section links (plugin-relative paths)."""
    out = []
    for skill in sorted(root.glob("skills/*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        resources = text.split("## Resources", 1)[1] if "## Resources" in text else ""
        m = re.search(r"\((references/[^)#\s]+\.md)", resources)
        if m:
            out.append((skill.parent / m.group(1)).relative_to(root).as_posix())
    return out


def routing_part(text: str) -> str:
    """Preamble plus the level-2 sections whose heading is about routing (see the module docstring)."""
    parts = re.split(r"(?m)^(?=## )", text)
    keep = [parts[0]] + [p for p in parts[1:] if ROUTING_HEADING.search(p.splitlines()[0])]
    return "".join(keep)


def soft_budget(root: Path) -> list[str]:
    """Warnings for the reference soft budget (B-05); never a failure."""
    warns = []
    for rel in entry_references(root):
        size = len(routing_part((root / rel).read_text(encoding="utf-8")).encode())
        if size > ROUTING_SOFT_BYTES:
            warns.append(f"{rel}: routing part {size} B > {ROUTING_SOFT_BYTES} B (entry reference)")
    for p in refs(root):
        size = p.stat().st_size
        if size > REFERENCE_SOFT_BYTES:
            warns.append(f"{p.relative_to(root).as_posix()}: {size} B > {REFERENCE_SOFT_BYTES} B (24 KB)")
    return warns


def markdown(inv: dict) -> str:
    lines = ["# Reference inventory", "",
             "Generated by `tools/reference_inventory.py`; do not edit by hand. Consolidation "
             "proposals are in [reference-consolidation.md](reference-consolidation.md).", "",
             f"Overlap: Jaccard index of {inv['shingle_words']}-word shingles, pairs >= {inv['threshold']}. "
             + inv.get("git_note", ""), "", "## By skill", "", "| Skill | References | KB | Cited nowhere |", "|---|---|---|---|"]
    for s, v in sorted(inv["by_skill"].items()):
        lines.append(f"| {s} | {v['references']} | {v['bytes'] / 1000:.0f} | {v['uncited']} |")
    lines += ["", "## Overlapping pairs", "", f"Listed when Jaccard >= {inv['threshold']} or containment (shared / smaller "
              f"file) >= {CONTAINMENT}.", "", "| A | B | Jaccard | Containment | Shared shingles |", "|---|---|---|---|---|"]
    for p in inv["overlap_pairs"]:
        lines.append(f"| `{p['a']}` | `{p['b']}` | {p['jaccard']} | {p['containment']} | {p['shared_shingles']} |")
    if not inv["overlap_pairs"]:
        lines.append("| none | | | |")
    lines += ["", f"## Similar names (same skill, a shared name token in at most {MAX_GROUP} files)", ""]
    for k, v in inv["name_groups"].items():
        lines.append(f"- **{k}**: " + ", ".join(f"`{Path(x).name}`" for x in v))
    lines += ["", "## References", "", "| Reference | Owner | KB | In SKILL.md | Cited by (files) | Other skills citing | Last commit |",
              "|---|---|---|---|---|---|---|"]
    for r in inv["references"]:
        name = r["path"].split("/references/", 1)[1]
        lines.append(f"| `{name}` | {r['owner']} | {r['bytes'] / 1000:.1f} | {'yes' if r['linked_from_skill_md'] else 'no'} | "
                     f"{len(r['cited_by'])} | {', '.join(r['cited_by_other_skills']) or '-'} | {r.get('last_commit', '-')} |")
    return "\n".join(lines) + "\n"


def strip_git(doc: dict) -> dict:
    d = json.loads(json.dumps(doc))
    d.pop("git_note", None)
    for r in d["references"]:
        r.pop("last_commit", None)
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", type=Path, default=ROOT / "docs" / "reference-inventory.json")
    ap.add_argument("--md", type=Path, default=ROOT / "docs" / "reference-inventory.md")
    ap.add_argument("--threshold", type=float, default=0.08)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", type=Path, default=ROOT, help="plugin root (default: this checkout)")
    opts = ap.parse_args(argv)
    root = opts.root.resolve()
    if opts.check:
        if not opts.json.is_file():
            print(json.dumps({"status": "fail", "problems": [f"{opts.json.name} missing"]}))
            return 1
        committed = json.loads(opts.json.read_text(encoding="utf-8"))
        fresh = build(root, committed.get("threshold", opts.threshold), with_git=False)
        same = strip_git(committed) == strip_git(fresh)
        problems = ([] if same else ["the committed inventory is stale: rerun tools/reference_inventory.py"]) + overlap_problems(fresh)
        print(json.dumps({"status": "fail" if problems else "pass", "references": len(fresh["references"]),
                          "problems": problems, "warnings": soft_budget(root)}))
        return 1 if problems else 0
    inv = build(root, opts.threshold)
    opts.json.write_text(json.dumps(inv, indent=1) + "\n", encoding="utf-8")
    opts.md.write_text(markdown(inv), encoding="utf-8")
    problems = overlap_problems(inv)
    print(json.dumps({"status": "fail" if problems else "ok", "references": len(inv["references"]),
                      "overlap_pairs": len(inv["overlap_pairs"]), "problems": problems, "warnings": soft_budget(root)}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
