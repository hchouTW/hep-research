#!/usr/bin/env python3
"""Rename the analysis-check programme's code-name identifiers ("v6.3" / "v63") to descriptive names (WP-R, DR-15;
docs/dev/cross-artifact-check/cross-artifact-check-architecture.en.md section 8.3).

Mapping: docs/dev/v6.3/ -> docs/dev/cross-artifact-check/ (a forwarding README.md stays at the old path), the
test_v63_* modules -> test_analysis_check_* / test_evidence_query, the helpers v63_cases and v63_runs ->
analysis_check_cases and analysis_check_runs.

Safety rules (normative, section 8.3):
  R-1 only whole identifiers of the mapping are replaced, never next to a letter, digit or underscore; a bare v63 or
      v6.3 is never replaced (test_v63_submission_bundle_digests names validation case V63)
  R-2 never modified: release manifests, CHANGELOG.md, VALIDATION.md, docs/dev/**/decision-*.md, the content of the
      moved records, contracts/vocab/effects.json, contracts/semantics/**, contracts/rules/suites/**, contracts/schemas/**
  R-3 records are moved with git mv, content unchanged; the forwarding README.md keeps docs/dev/v6.3/<file> working
  R-4 test IDs in contracts/rules/registry.json are rewritten together (ship with the other registry changes)
  R-5 idempotent: a second run changes nothing
  R-6 --verify: no leftover old identifiers, every registry test ID resolves, the stub exists, the derived-file checks
      pass
  R-7 after rewriting, the derived files whose --check fails are regenerated (reference inventory, stanzas,
      capability map)

Usage: python3 tools/rename_analysis_check_ids.py ROOT                       dry run: list moves and rewrites
       python3 tools/rename_analysis_check_ids.py ROOT --apply --date DATE [--also FILE ...]
       python3 tools/rename_analysis_check_ids.py ROOT --verify [--also FILE ...]
ROOT is the plugin root inside a git work tree. --also names further files outside ROOT (for example the repository
README) rewritten by the same rules. Output: JSON with a status key. Exit 0 ok, 1 verify findings or a failed step,
2 bad usage. Standard library only.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

OLD_DIR, NEW_DIR = "docs/dev/v6.3", "docs/dev/cross-artifact-check"
TEST_MODULES = {
    "test_v63_baseline_gaps": "test_analysis_check_baseline_gaps",
    "test_v63_d03a": "test_analysis_check_profile_loading",
    "test_v63_d04": "test_analysis_check_effect_catalog",
    "test_v63_d05a": "test_analysis_check_identity_and_instances",
    "test_v63_d05b": "test_analysis_check_bundle_and_context",
    "test_v63_d05c": "test_analysis_check_report",
    "test_v63_d05d": "test_analysis_check_run_lineage",
    "test_v63_d06": "test_analysis_check_chain_rules",
    "test_v63_d07": "test_analysis_check_ratio_rules",
    "test_v63_d07_model": "test_analysis_check_model_rules",
    "test_v63_d09": "test_analysis_check_shadow_and_refusal",
    "test_v63_d10": "test_analysis_check_report_permit",
    "test_v63_d11a": "test_analysis_check_coverage_reader",
    "test_v63_d11b": "test_analysis_check_snapshots",
    "test_v63_d12b": "test_analysis_check_custody",
    "test_v63_d17": "test_analysis_check_review_integration",
    "test_v63_refusal_blockers": "test_analysis_check_refusal_blockers",
    "test_v63_review_fixes": "test_analysis_check_review_fixes",
    "test_v63_rule_registry": "test_analysis_check_rule_registry",
}
HELPERS = {"v63_cases": "analysis_check_cases", "v63_runs": "analysis_check_runs"}
CORE = {"test_v63_evidence_query": "test_evidence_query"}
IDENTIFIERS = {**TEST_MODULES, **HELPERS, **CORE}
MOVES = ([(f"tests/contracts/{o}.py", f"tests/contracts/{n}.py") for o, n in {**TEST_MODULES, **HELPERS}.items()]
         + [(f"tests/core/{o}.py", f"tests/core/{n}.py") for o, n in CORE.items()])
PROTECTED = ("release-manifests/*", "CHANGELOG.md", "VALIDATION.md", "docs/dev/*/decision-*.md", f"{OLD_DIR}/*",
             f"{NEW_DIR}/*", "contracts/vocab/effects.json", "contracts/semantics/*", "contracts/rules/suites/*",
             "contracts/schemas/*", "tools/rename_analysis_check_ids.py")
DERIVED = (("tools/reference_inventory.py", ["--check"], []), ("tools/build_stanzas.py", ["--check"], []),
           ("tools/capability_map.py", ["--check"], ["--write"]))
STUB = """# Moved: docs/dev/cross-artifact-check/

The development records of the analysis-check programme (code name "v6.3") moved on {date} to
[`docs/dev/cross-artifact-check/`](../cross-artifact-check/README.md), with their content and file names unchanged
(DR-15, WP-R). A reference written as `docs/dev/v6.3/<file>` names `docs/dev/cross-artifact-check/<file>`.
"""


def _patterns() -> list[tuple[re.Pattern, str]]:
    pats = [(re.compile(rf"(?<![A-Za-z0-9_]){re.escape(OLD_DIR)}(?![A-Za-z0-9_])"), NEW_DIR)]
    for old in sorted(IDENTIFIERS, key=len, reverse=True):
        pats.append((re.compile(rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])"), IDENTIFIERS[old]))
    return pats


PATTERNS = _patterns()


def protected(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, p) for p in PROTECTED)


def rewrite(text: str) -> tuple[str, int]:
    total = 0
    for pat, new in PATTERNS:
        text, n = pat.subn(new, text)
        total += n
    return text, total


def git(root: Path, *args) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True, timeout=120).stdout


def tracked(root: Path) -> list[str]:
    return [p for p in git(root, "ls-files", "-z", ".").split("\0") if p]


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def plan(root: Path, also: list[Path]) -> dict:
    moves = []
    if (root / OLD_DIR).is_dir() and not (root / NEW_DIR).exists():
        moves.append({"from": OLD_DIR, "to": NEW_DIR})
    moves += [{"from": a, "to": b} for a, b in MOVES if (root / a).is_file() and not (root / b).exists()]
    moved = {m["from"]: m["to"] for m in moves}
    rewrites = []
    for rel in tracked(root):
        dest = moved.get(rel, rel)
        if rel.startswith(OLD_DIR + "/") or protected(dest):
            continue
        text = _read_text(root / rel)
        if text is None:
            continue
        _, n = rewrite(text)
        if n:
            rewrites.append({"file": dest, "replacements": n})
    for p in also:
        text = _read_text(p)
        if text is not None and rewrite(text)[1]:
            rewrites.append({"file": str(p), "replacements": rewrite(text)[1]})
    return {"moves": moves, "rewrites": rewrites, "stub_missing": NEW_DIR not in (_read_text(root / OLD_DIR / "README.md") or "")}


def _derived(root: Path, regenerate: bool) -> list[dict]:
    out = []
    for script, check, write in DERIVED:
        res = subprocess.run([sys.executable, script, *check], cwd=root, capture_output=True, text=True, timeout=600)
        row = {"script": script, "check": res.returncode == 0}
        if res.returncode != 0 and regenerate:
            subprocess.run([sys.executable, script, *write], cwd=root, check=True, capture_output=True, text=True, timeout=600)
            row["regenerated"] = True
            row["check"] = subprocess.run([sys.executable, script, *check], cwd=root, capture_output=True,
                                          timeout=600).returncode == 0
        out.append(row)
    return out


def apply(root: Path, date: str, also: list[Path]) -> dict:
    p = plan(root, also)
    for m in p["moves"]:
        (root / m["to"]).parent.mkdir(parents=True, exist_ok=True)
        git(root, "mv", m["from"], m["to"])
    for r in p["rewrites"]:
        path = Path(r["file"]) if Path(r["file"]).is_absolute() else root / r["file"]
        text, _ = rewrite(path.read_text(encoding="utf-8"))
        path.write_text(text, encoding="utf-8")
    stub = root / OLD_DIR / "README.md"
    if (root / NEW_DIR).is_dir() and not stub.is_file():
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(STUB.format(date=date), encoding="utf-8")
        git(root, "add", str(stub.relative_to(root)))
    derived = _derived(root, regenerate=True) if (p["moves"] or p["rewrites"]) else []
    return {"status": "applied", "moves": p["moves"], "rewrites": p["rewrites"], "derived": derived}


def verify(root: Path, also: list[Path]) -> dict:
    sys.path.insert(0, str(root))
    from contracts.rule_registry import _test_exists
    findings = []
    p = plan(root, also)
    if p["moves"]:
        findings.append({"code": "rename.moves_pending", "detail": p["moves"]})
    if p["rewrites"]:
        findings.append({"code": "rename.leftover_identifiers", "detail": p["rewrites"]})
    stub = root / OLD_DIR / "README.md"
    if not stub.is_file() or NEW_DIR not in (_read_text(stub) or ""):
        findings.append({"code": "rename.stub_missing", "detail": str(stub)})
    reg = json.loads((root / "contracts" / "rules" / "registry.json").read_text(encoding="utf-8"))
    ids = sorted({t for c in reg["v_cases"] for part in c["parts"] for t in part["tests"]}
                 | {c for g in reg["impact"] for c in g["checks"] if c.startswith("tests.")})
    unresolved = [t for t in ids if not _test_exists(t, root)]
    if unresolved:
        findings.append({"code": "rename.registry_test_unresolved", "detail": unresolved})
    derived = _derived(root, regenerate=False)
    if not all(d["check"] for d in derived):
        findings.append({"code": "rename.derived_stale", "detail": [d for d in derived if not d["check"]]})
    return {"status": "ok" if not findings else "fail", "registry_test_ids": len(ids), "findings": findings,
            "derived": derived}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("root", type=Path)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    ap.add_argument("--date", help="YYYY-MM-DD for the forwarding stub (with --apply)")
    ap.add_argument("--also", type=Path, nargs="*", default=[], help="further files outside ROOT to rewrite")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if not (root / "contracts" / "rules" / "registry.json").is_file():
        print(json.dumps({"status": "usage", "error": f"{root} is not the plugin root"}))
        return 2
    if args.apply and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date or ""):
        print(json.dumps({"status": "usage", "error": "--apply needs --date YYYY-MM-DD"}))
        return 2
    try:
        if args.apply:
            out = apply(root, args.date, [p.resolve() for p in args.also])
        elif args.verify:
            out = verify(root, [p.resolve() for p in args.also])
        else:
            out = dict(plan(root, [p.resolve() for p in args.also]), status="dry-run")
    except subprocess.TimeoutExpired as exc:
        print(json.dumps({"status": "failed", "error": f"{exc.cmd}: timed out"}))
        return 1
    except subprocess.CalledProcessError as exc:
        print(json.dumps({"status": "failed", "error": f"{exc.cmd}: {exc.stderr}"}))
        return 1
    print(json.dumps(out, indent=1))
    return 1 if out["status"] in ("fail", "failed") else 0


if __name__ == "__main__":
    sys.exit(main())
