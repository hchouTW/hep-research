#!/usr/bin/env python3
"""Wiring lint (architecture step 1): is every page and script of a skill wired into the hand-kept lists?

Rules (each finding has a stable key; tools/wiring_known_gaps.json lists the gaps that existed when a rule came in):
  R1 page reachable: every page under skills/<s>/references/ is one step from the SKILL.md Resources table or from the
     entry reference's routing part (tools/reference_inventory.py routing_part()), or two steps through a hub page
     registered in the known-gaps file (a hub must itself be one step away). Markdown links and back-ticked file names
     both count. A pointer page (title ending in "(moved)", under 1 KB) is exempt, but must be recorded with the release
     that removes it; from that release on it is a finding.
  R2 CLI dictionary (tests/skills/test_cli_robustness.py): every NO_INPUT_FILE value is a string reason, and a script
     that reads a file named by one of its arguments is not in NO_INPUT_FILE. That a script is in exactly one of the
     two dictionaries is the test's own check.
  R3 README counts: the number word that opens a README folder row (e.g. "| `references/` | twenty-one references")
     equals the number of files its pattern in the known-gaps file matches.
  R4 CHANGELOG (only with --since REV): every page or script added since REV is named under "## Unreleased" in
     CHANGELOG.md, and a capability id new in docs/capability-map.json since REV comes with an added row in
     docs/capability-matrix.md.

Usage: python3 tools/check_wiring.py [--since REV] [--known-gaps FILE] [--skill NAME] [--root PLUGIN_ROOT]
Output: one JSON object (status, findings, known_gaps_applied, known_gaps_stale). Exit 0 when every finding is a
known gap (the report mode), 1 when a finding is not in the known-gaps file (a new gap), 2 on unusable input. The
known-gaps file only shrinks: delete an entry once its gap is fixed (a stale entry is reported, never an error).
Standard library only; writes nothing. Parsers are the existing ones: the Resources table of
tests/skills/test_routing_tables.py, the entry references and routing part of tools/reference_inventory.py, the link
and back-tick patterns of tests/skills/test_reference_links.py and the dictionaries of test_cli_robustness.py.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.skills.test_cli_robustness import MISSING_FILE_ARGS, NO_INPUT_FILE  # noqa: E402
from tests.skills.test_reference_links import FENCE, LINK, NAMED, NAMED_PATH  # noqa: E402
from tests.skills.test_routing_tables import table  # noqa: E402
from tools.reference_inventory import entry_references, routing_part  # noqa: E402

KNOWN_GAPS = ROOT / "tools" / "wiring_known_gaps.json"
POINTER_MAX_BYTES = 1024
SCRIPT_GLOBS = ("skills/*/scripts/*.py", "skills/*/scripts/*.sh")
# R2: calls that read a file, and words that mark an argument as a file name in its name, dest, metavar or help
READ_CALLS = {"read_text", "read_bytes", "loadtxt", "genfromtxt", "read_csv", "read_parquet", "reader", "DictReader"}
LOAD_MODULES = {"json", "np", "numpy", "pickle", "torch", "yaml"}
FILE_WORD = re.compile(r"\b(file|files|path|table|json|csv|yaml|plan|input|manifest|spec|config|series)\b", re.I)
OUTPUT_NAME = re.compile(r"out|output|write|dir$|work")
UNITS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
         "seventeen eighteen nineteen").split()
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}


def number_word(text: str) -> int | None:
    """The English number (0-99) that opens text: 'forty-nine references' -> 49; None if it opens with none."""
    m = re.match(r"\s*([a-z]+)(?:-([a-z]+))?\b", text.lower())
    if not m:
        return None
    head, tail = m.groups()
    if head in TENS:
        return TENS[head] + (UNITS.index(tail) if tail in UNITS[1:10] else 0)
    return UNITS.index(head) if head in UNITS and not tail else None


def version_tuple(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def finding(rule: str, key: str, detail: str, **extra) -> dict:
    return {"rule": rule, "key": key, "detail": detail, **extra}


# ---------------------------------------------------------------- R1


def targets(text: str, base: Path, skill_dir: Path) -> set[Path]:
    """Reference pages of this skill that text links (Markdown link) or names in back-ticks; base = the text's folder."""
    pages = {p.name: p for p in (skill_dir / "references").rglob("*.md")}
    out = set()
    plain = re.sub(r"`[^`\n]*`", "", FENCE.sub("", text))
    for target in LINK.findall(plain):
        if not re.match(r"^[a-z]+:", target):
            out.add((base / target.partition("#")[0]).resolve())
    for name in NAMED.findall(text):
        if name in pages:
            out.add(pages[name].resolve())
    for rel in NAMED_PATH.findall(text) + re.findall(r"`(references/[\w./-]+\.md)`", text):
        for start in (base, skill_dir):
            if (start / rel).is_file():
                out.add((start / rel).resolve())
    refs = (skill_dir / "references").resolve()
    return {p for p in out if p.suffix == ".md" and refs in p.parents and p.is_file()}


def is_pointer(page: Path) -> bool:
    first = page.read_text(encoding="utf-8").lstrip().splitlines()[:1]
    return bool(first) and first[0].startswith("# ") and first[0].rstrip().endswith("(moved)") and \
        page.stat().st_size < POINTER_MAX_BYTES


def check_reachability(root: Path, skill_dir: Path, gaps: dict, version: str) -> list[dict]:
    rel = lambda p: p.relative_to(root.resolve()).as_posix()  # noqa: E731
    skill = skill_dir.name
    entries = [root / e for e in entry_references(root) if Path(e).parts[1] == skill]
    one_step = targets(table(skill_dir), skill_dir, skill_dir)
    for entry in entries:
        one_step |= {entry.resolve()} | targets(routing_part(entry.read_text(encoding="utf-8")), entry.parent, skill_dir)
    reach, out = set(one_step), []
    for hub in gaps.get("hubs", {}).get(skill, []):
        page = (skill_dir / hub).resolve()
        if page not in one_step:
            out.append(finding("R1", f"R1:hub:{skill}/{hub}", "registered hub is not one step from SKILL.md (or missing)"))
            continue
        reach |= targets(page.read_text(encoding="utf-8"), page.parent, skill_dir)
    pages = sorted(p.resolve() for p in (skill_dir / "references").rglob("*.md"))
    # steps over whole pages, for the report only: how far an unreachable page is
    steps, frontier, n = {p: 1 for p in one_step}, set(one_step), 1
    while frontier:
        n += 1
        nxt = set()
        for p in frontier:
            for q in targets(p.read_text(encoding="utf-8"), p.parent, skill_dir):
                if q not in steps:
                    steps[q] = n
                    nxt.add(q)
        frontier = nxt
    pointers = gaps.get("pointers", {})
    for page in pages:
        path = rel(page)
        if is_pointer(page):
            rec = pointers.get(path)
            if not rec or "remove_in" not in rec:
                out.append(finding("R1", f"R1:pointer-unrecorded:{path}", "pointer page without a removal release in the "
                                   "known-gaps file 'pointers'"))
            elif version_tuple(version) >= version_tuple(rec["remove_in"]):
                out.append(finding("R1", f"R1:pointer-expired:{path}", f"pointer page was due for removal in "
                                   f"{rec['remove_in']} (plugin is {version})"))
            continue
        if page not in reach:
            out.append(finding("R1", f"R1:{path}", "not one step from the Resources table or the entry routing part, "
                               "nor linked from a registered hub", skill=skill, steps=steps.get(page)))
    return out


# ---------------------------------------------------------------- R2


def reads_file_argument(script: Path) -> list[str]:
    """Argument names of a script that reads files and has an argument naming one (empty when it reads none)."""
    tree = ast.parse(script.read_text(encoding="utf-8"))
    reads, names = False, []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name == "open":
            mode = next((a.value for a in node.args[1:2] if isinstance(a, ast.Constant)), None)
            mode = next((k.value.value for k in node.keywords if k.arg == "mode" and isinstance(k.value, ast.Constant)), mode)
            reads |= mode is None or ("r" in str(mode) and "+" not in str(mode))
        elif name in READ_CALLS or (name == "load" and isinstance(func, ast.Attribute)
                                    and ast.unparse(func.value) in LOAD_MODULES):
            reads = True
        elif name == "add_argument":
            kw = {k.arg: k.value for k in node.keywords}
            kind = ast.unparse(kw["type"]) if "type" in kw else ""
            flags = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
            if "action" in kw or "choices" in kw or kind in ("int", "float") or any(OUTPUT_NAME.search(f) for f in flags):
                continue
            words = " ".join(flags + [ast.unparse(kw[k]) for k in ("help", "metavar", "dest") if k in kw])
            if FILE_WORD.search(words.replace("-", " ").replace("_", " ")) or kind in ("Path", "pathlib.Path") \
                    or "FileType" in kind:
                names.append(flags[0] if flags else "?")
    return names if reads else []


def check_cli(root: Path, skill: str | None, missing_file_args=MISSING_FILE_ARGS, no_input_file=NO_INPUT_FILE) -> list[dict]:
    out = []
    for script, reason in sorted(no_input_file.items()):
        if skill and not script.startswith(f"skills/{skill}/"):
            continue
        if not isinstance(reason, str):
            out.append(finding("R2", f"R2:reason:{script}", f"NO_INPUT_FILE value is a {type(reason).__name__}, not a "
                               "string reason (an argument list belongs in MISSING_FILE_ARGS)"))
        path = root / script
        if path.suffix == ".py" and path.is_file():
            args = reads_file_argument(path)
            if args:
                out.append(finding("R2", f"R2:reads-file:{script}", f"in NO_INPUT_FILE but reads the file named by "
                                   f"{', '.join(args)}: move it to MISSING_FILE_ARGS"))
    return out


# ---------------------------------------------------------------- R3


def check_readme_counts(root: Path, skill_dir: Path, gaps: dict) -> list[dict]:
    out = []
    readme = skill_dir / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    for row in gaps.get("readme_counts", {}).get(skill_dir.name, []):
        m = re.search(rf"^\| `{re.escape(row['row'])}` \|([^|\n]*)", text, re.M)
        key = f"R3:{skill_dir.name}:{row['row']}"
        said = number_word(m.group(1)) if m else None
        found = sorted({p for g in row["globs"] for p in skill_dir.glob(g) if p.is_file()})
        if said is None:
            out.append(finding("R3", key, f"README row `{row['row']}` does not open with a number word"))
        elif said != len(found):
            out.append(finding("R3", key, f"README says {said} for `{row['row']}`, {len(found)} files match "
                               f"{', '.join(row['globs'])}"))
    return out


# ---------------------------------------------------------------- R4


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise ValueError(r.stderr.strip() or f"git {' '.join(args)} failed")
    return r.stdout


def check_changelog(root: Path, since: str, skill: str | None) -> list[dict]:
    prefix = git(root, "rev-parse", "--show-prefix").strip()
    # added since REV: committed or staged (diff against the working tree), and new files not yet added to git
    added = [p[len(prefix):] for p in git(root, "diff", "--name-only", "--no-renames", "--diff-filter=A", since, "--",
                                          ".").splitlines()]
    added += git(root, "ls-files", "--others", "--exclude-standard", "--", ".").splitlines()
    added = [p for p in added if fnmatch.fnmatch(p, "skills/*/references/*.md")
             or any(fnmatch.fnmatch(p, g) for g in SCRIPT_GLOBS)]
    if skill:
        added = [p for p in added if p.startswith(f"skills/{skill}/")]
    log = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    unreleased = log.split("## Unreleased", 1)[1].split("\n## ", 1)[0] if "## Unreleased" in log else ""
    out = [finding("R4", f"R4:changelog:{p}", "added since --since but not named under '## Unreleased' in CHANGELOG.md")
           for p in added if Path(p).name not in unreleased]
    try:
        before = {c["id"] for c in json.loads(git(root, "show", f"{since}:./docs/capability-map.json"))["capabilities"]}
    except ValueError:
        before = set()
    now = {c["id"] for c in json.loads((root / "docs" / "capability-map.json").read_text(encoding="utf-8"))["capabilities"]}
    rows_added = [line for line in git(root, "diff", since, "--", "docs/capability-matrix.md").splitlines()
                  if line.startswith("+|")]
    if now - before and not rows_added:
        out += [finding("R4", f"R4:matrix:{cid}", "new capability id without an added docs/capability-matrix.md row")
                for cid in sorted(now - before)]
    return out


# ---------------------------------------------------------------- driver


def check(root: Path, gaps: dict, skill: str | None = None, since: str | None = None) -> list[dict]:
    version = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    skills = sorted(p.parent for p in (root / "skills").glob("*/SKILL.md") if not skill or p.parent.name == skill)
    out = []
    for s in skills:
        out += check_reachability(root, s, gaps, version)
        out += check_readme_counts(root, s, gaps)
    out += check_cli(root, skill)
    if since:
        out += check_changelog(root, since, skill)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--since", metavar="REV", help="also run R4 (CHANGELOG) for pages and scripts added since this git rev")
    ap.add_argument("--known-gaps", type=Path, default=KNOWN_GAPS, help="known gaps, hubs, pointers and README count "
                    "patterns (default tools/wiring_known_gaps.json)")
    ap.add_argument("--skill", metavar="NAME", help="check one skill only (R1, R3; R2 and R4 limited to its files)")
    ap.add_argument("--root", type=Path, default=ROOT, help="plugin root (default: this checkout)")
    opts = ap.parse_args(argv)
    root = opts.root.resolve()
    try:
        gaps = json.loads(opts.known_gaps.read_text(encoding="utf-8"))
        if opts.skill and not (root / "skills" / opts.skill / "SKILL.md").is_file():
            raise ValueError(f"no skill {opts.skill}")
        findings = check(root, gaps, opts.skill, opts.since)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    known = set(gaps.get("gaps", []))
    new = [f for f in findings if f["key"] not in known]
    keys = {f["key"] for f in findings}
    scope = (lambda k: f":{opts.skill}" in k or f"skills/{opts.skill}/" in k) if opts.skill else (lambda k: True)
    if opts.since is None:
        scope_stale = lambda k: scope(k) and not k.startswith("R4:")  # noqa: E731
    else:
        scope_stale = scope
    print(json.dumps({"status": "fail" if new else ("known-gaps" if findings else "pass"),
                      "findings": findings, "new_gaps": [f["key"] for f in new],
                      "known_gaps_applied": sorted(keys & known),
                      "known_gaps_stale": sorted(k for k in known - keys if scope_stale(k))}, indent=1))
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
