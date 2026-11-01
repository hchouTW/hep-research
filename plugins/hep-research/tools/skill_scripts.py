#!/usr/bin/env python3
"""Generate tools/skill_scripts.json: every Python script a skill's text tells the agent to run (a "skill script").

A skill's text is its SKILL.md and every Markdown file under its references/. A script reference is any token ending
in `.py`, in each form the skills use:
  1. a full path (`<plugin root>/skills/hep-detector/scripts/tracker_resolution.py`) or a plugin-root-relative path (`contracts/x.py`);
  2. a path relative to the referencing file (Markdown links such as `../scripts/x.py`);
  3. a path relative to the skill folder (`scripts/x.py`, `assets/x.py`), or to skills/ (`hep-computing/scripts/x.py`);
     after the shorthands (4), a path relative to an adapter folder (`assets/geant4_build.py` in text about the
     geant4 adapter), when exactly one adapter has it;
  4. a folder shorthand the skill's SKILL.md defines as "`sc/` = `<plugin root>/skills/hep-statistics/scripts/`";
  5. a bare file name, looked up in this order, stopping at the first place that has it: the skill's own scripts/ and
     assets/ (recursively), then adapters/*/assets/, then contracts/, then core/ (recursively).
The forms are tried in that order; the first that names an existing file wins. A name that resolves to no file, or
whose first matching place holds more than one file of that name (`review.py` is both
skills/hep-review/scripts/review.py and contracts/review.py), goes into "unresolved" with its first source line, so
it is visible rather than guessed.

A resolved file is a skill script when it has an `if __name__ == "__main__":` block and is not excluded (EXCLUDED
below, each with its reason). Each script is stored with its depth N below the plugin root (the guard block computes
the plugin root as Path(__file__).resolve().parents[N]) and the skills whose text names it.

Usage: python3 tools/skill_scripts.py [--check] [--root PLUGIN_ROOT]
Writes tools/skill_scripts.json; --check writes nothing and exits 1 when the file differs from a fresh generation
(tests/tools/test_skill_scripts.py runs the same comparison). Exit 0 ok, 1 drift (--check), 2 bad usage.
Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("tools") / "skill_scripts.json"
FORMAT = "hep-research-skill-scripts/1"
TOKEN = re.compile(r"[^\s`'\"()\[\]|,;*]*\.py\b")
SHORTHAND = re.compile(r"`([A-Za-z0-9_-]+/)`\s*=\s*`<plugin root>/([^`]+?)/?`")
MAIN_BLOCK = re.compile(r"^if __name__ == [\"']__main__[\"']\s*:", re.M)
SKIP_DIRS = {"__pycache__", "tests", "examples", "output"}

# The interpreter guard block every listed script carries, first after the module docstring and any `from __future__`
# import (tools/insert_interpreter_guard.py inserts it; tests/tools/test_python_compat.py checks it). {N} is the
# script's depth below the plugin root.
GUARD_BLOCK = """\
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[{N}])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()
"""


def guard_block(depth: int) -> str:
    return GUARD_BLOCK.replace("{N}", str(depth))


def guard_insertion_line(source: str) -> int:
    """The 0-based line index where the guard block belongs: after the module docstring and every leading
    `from __future__` import (comments and blank lines before them stay where they are)."""
    tree = ast.parse(source)
    after = 0
    body = list(tree.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        after = body.pop(0).end_lineno or 0
    while body and isinstance(body[0], ast.ImportFrom) and body[0].module == "__future__":
        after = body.pop(0).end_lineno or after
    if after == 0:  # no docstring and no __future__ import: keep a shebang and leading comments first
        lines = source.splitlines()
        while after < len(lines) and (not lines[after].strip() or lines[after].lstrip().startswith("#")):
            after += 1
    return after


def guard_problems(source: str, depth: int) -> list[str]:
    """Why source does not carry the guard block for depth in the right place (empty when it does)."""
    block = guard_block(depth).splitlines()
    lines = source.splitlines()
    try:
        start = guard_insertion_line(source)
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [f"does not parse: {exc}"]
    found = [i for i, line in enumerate(lines) if line == block[0]]
    if not found:
        return ["no interpreter guard block"]
    at = found[0]
    problems = []
    if len(found) > 1:
        problems.append("more than one interpreter guard block")
    if lines[at:at + len(block)] != block:
        got = next((ln for ln in lines[at:at + len(block)] if "parents[" in ln), "")
        problems.append(f"the guard block differs from tools/skill_scripts.py GUARD_BLOCK (depth {depth}; {got.strip()})")
    first_stmt = [n for n in tree.body if n.lineno - 1 >= start]
    late_future = any(isinstance(n, ast.ImportFrom) and n.module == "__future__" and n.lineno - 1 > at
                      for n in tree.body)
    if late_future or not first_stmt or first_stmt[0].lineno - 1 != at:
        problems.append(f"the guard block is not the first statement after the docstring and __future__ imports "
                        f"(found at line {at + 1}, expected the first statement after line {start})")
    return problems


EXCLUDED_TREES = {  # plugin-root-relative prefixes never listed, with the reason
    "tests/": "tests run under the test runner, not as skill scripts",
    "examples/": "examples are worked inputs and outputs, regenerated per release (docs/maintenance.md)",
    "profiles/": "profile scripts are reached from profile text, outside this list (task Open Questions: default no)",
    "skills/hep-computing/assets/event-display/":
        "self-contained templates users copy into their own projects, where core cannot be imported",
}
EXCLUDED = {  # plugin-root-relative path -> reason
    "skills/hep-computing/scripts/find_python.py":
        "runs on an old python3 to find a qualifying interpreter; must not stop it (tests/tools/test_python_compat.py)",
    "skills/hep-ml/assets/ddp_train_skeleton.py":
        "self-contained template users copy into their own projects, where core cannot be imported",
    "adapters/root-uproot/assets/root_to_parquet.py":
        "self-contained adapter template users copy into their own projects, where core cannot be imported",
    "adapters/root-uproot/assets/pyroot_roofit_signal_background.py":
        "self-contained adapter template users copy into their own projects, where core cannot be imported",
    "adapters/pyhf-combine/assets/pyhf_nuisance_diagnostics.py":
        "self-contained adapter template users copy into their own projects, where core cannot be imported",
}


def _rel(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _files_named(folder: Path, name: str) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob(name)
                  if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(folder).parts[:-1]))


def skill_texts(skill_dir: Path) -> list[Path]:
    texts = [skill_dir / "SKILL.md"]
    refs = skill_dir / "references"
    if refs.is_dir():
        texts += sorted(refs.rglob("*.md"))
    return [t for t in texts if t.is_file()]


def shorthands(skill_md: Path) -> dict[str, str]:
    if not skill_md.is_file():
        return {}
    return {m.group(1): m.group(2).rstrip("/") + "/" for m in SHORTHAND.finditer(skill_md.read_text(encoding="utf-8"))}


def resolve(token: str, text: Path, skill_dir: Path, short: dict[str, str], root: Path) -> list[Path]:
    """Candidate files for token: one file when it resolves, several when ambiguous, none when it names nothing."""
    name = token
    for prefix in ("<plugin_root>/", "root>/", "./"):  # root>/: `<plugin root>` wrapped
        if name.startswith(prefix):
            name = name[len(prefix):]
    if "<" in name or ">" in name or "{" in name or "$" in name:
        return []
    if "/" in name:
        for base in (root, text.parent, skill_dir, root / "skills"):
            p = base / name
            if p.is_file():
                return [p]
        head, _, tail = name.partition("/")
        if f"{head}/" in short:
            p = root / short[f"{head}/"] / tail
            return [p] if p.is_file() else []
        return sorted(p for p in (root / "adapters").glob(f"*/{name}") if p.is_file())
    for places in ([skill_dir / "scripts", skill_dir / "assets"], sorted((root / "adapters").glob("*/assets")),
                   [root / "contracts"], [root / "core"]):
        found = [f for place in places for f in _files_named(place, name)]
        if found:
            return found
    return []


def excluded_reason(rel: str) -> str | None:
    for prefix, reason in EXCLUDED_TREES.items():
        if rel.startswith(prefix):
            return reason
    return EXCLUDED.get(rel)


def generate(root: Path = ROOT) -> dict:
    scripts: dict[str, set[str]] = {}
    unresolved: dict[str, dict] = {}
    not_scripts: set[str] = set()
    for skill_dir in sorted(p for p in (root / "skills").iterdir() if (p / "SKILL.md").is_file()):
        short = shorthands(skill_dir / "SKILL.md")
        for text in skill_texts(skill_dir):
            source = text.relative_to(root).as_posix()
            for lineno, line in enumerate(text.read_text(encoding="utf-8").splitlines(), 1):
                for token in TOKEN.findall(line.replace("<plugin root>/", "<plugin_root>/")):
                    if token.endswith("/.py") or token == ".py":
                        continue
                    found = resolve(token, text, skill_dir, short, root)
                    rels = sorted({r for r in (_rel(f, root) for f in found) if r is not None})
                    if len(rels) != 1:
                        key = f"{skill_dir.name}|{token}"
                        unresolved.setdefault(key, {"skill": skill_dir.name, "name": token,
                                                    "source": f"{source}:{lineno}", "matches": rels})
                        continue
                    rel = rels[0]
                    if excluded_reason(rel) is not None:
                        continue
                    if not MAIN_BLOCK.search((root / rel).read_text(encoding="utf-8")):
                        not_scripts.add(rel)
                        continue
                    scripts.setdefault(rel, set()).add(skill_dir.name)
    return {
        "format": FORMAT,
        "generated_by": "tools/skill_scripts.py",
        "note": "generated; do not edit. Each script carries the interpreter guard block (tools/insert_interpreter_guard.py)",
        "scripts": [{"path": rel, "depth": len(Path(rel).parts) - 1, "skills": sorted(skills)}
                    for rel, skills in sorted(scripts.items())],
        "excluded": [{"path": rel, "reason": reason} for rel, reason in sorted(EXCLUDED.items())]
                    + [{"path": prefix, "reason": reason} for prefix, reason in sorted(EXCLUDED_TREES.items())],
        "unresolved": [unresolved[k] for k in sorted(unresolved)],
        "counts": {"scripts": len(scripts), "unresolved": len(unresolved), "named_without_main": len(not_scripts)},
    }


def render(doc: dict) -> str:
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--check", action="store_true", help="exit 1 when tools/skill_scripts.json is out of date")
    ap.add_argument("--root", type=Path, default=ROOT, help="plugin root (default: this file's plugin)")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    text = render(generate(root))
    out = root / OUT
    if args.check:
        current = out.read_text(encoding="utf-8") if out.is_file() else ""
        ok = current == text
        print(json.dumps({"status": "ok" if ok else "failed", "file": OUT.as_posix(),
                          "message": "up to date" if ok else "out of date: run python3 tools/skill_scripts.py"}))
        return 0 if ok else 1
    out.write_text(text, encoding="utf-8")
    doc = json.loads(text)
    print(json.dumps({"status": "written", "file": OUT.as_posix(), "counts": doc["counts"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
