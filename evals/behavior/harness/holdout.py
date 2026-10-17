"""Blinded held-out suite: the eval-side equivalent of a blinded signal region.

Tuning descriptions or SKILL.md text against the same cases you report is looking at the signal region while choosing
cuts. The development cases (evals/cases, the routing table) are open: tune on them freely. The held-out suite is
written by someone who did not write the descriptions, kept outside the repository, and opened once per release.

  commit   hash the held-out file and record the commitment in evals/holdout.commit.json (the file stays outside)
  verify   check a file against the commitment (a changed file after commit is a different suite)
  open     record an opening (release tag, date, run directory) and allow `run.py run --holdout` to proceed
  leaks    n-gram check: held-out prompts must not quote skill descriptions (that would test string matching)

A suite that has been opened N times has been seen N times. The report prints the opening count next to every held-out
number; after a few openings, retire the suite and write a new one.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

from .cases import EVALS, ngram_leaks

COMMIT_FILE = EVALS / "holdout.commit.json"


def canonical_hash(path: Path) -> str:
    doc = json.loads(path.read_text(encoding="utf-8"))
    canon = json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _load() -> dict:
    return json.loads(COMMIT_FILE.read_text()) if COMMIT_FILE.exists() else {"suites": {}}


def _save(doc: dict) -> None:
    COMMIT_FILE.write_text(json.dumps(doc, indent=1) + "\n")


def commit(path: Path, name: str, author: str) -> dict:
    doc = _load()
    if name in doc["suites"]:
        raise SystemExit(f"suite {name!r} already committed; retire it or use a new name")
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    doc["suites"][name] = {"sha256": canonical_hash(path), "cases": len(cases), "author": author,
                           "committed": dt.date.today().isoformat(), "openings": [], "retired": False}
    _save(doc)
    return doc["suites"][name]


def verify(path: Path, name: str) -> dict:
    doc = _load()
    rec = doc["suites"].get(name)
    if rec is None:
        raise SystemExit(f"no commitment for suite {name!r}")
    h = canonical_hash(path)
    if h != rec["sha256"]:
        raise SystemExit(f"held-out file does not match the commitment ({h[:12]} != {rec['sha256'][:12]}): "
                         "it changed after it was committed")
    if rec.get("retired"):
        raise SystemExit(f"suite {name!r} is retired")
    return rec


def open_suite(path: Path, name: str, release: str, run_dir: str) -> dict:
    rec = verify(path, name)
    doc = _load()
    doc["suites"][name]["openings"].append({"release": release, "date": dt.date.today().isoformat(),
                                            "run_dir": run_dir})
    _save(doc)
    return {**rec, "suite": name, "openings": len(doc["suites"][name]["openings"])}


def leaks(path: Path, descriptions: dict[str, str], n: int = 4) -> list[dict]:
    out = []
    for c in json.loads(path.read_text(encoding="utf-8"))["cases"]:
        prompts = [c["prompt"]] if c.get("prompt") else [t["prompt"] for t in c.get("turns", [])]
        for p in prompts:
            for skill, desc in descriptions.items():
                hits = ngram_leaks(p, desc, n)
                if hits:
                    out.append({"case": c["id"], "skill": skill, "ngrams": hits})
    return out


def skill_descriptions(plugin_root: Path) -> dict[str, str]:
    out = {}
    for f in sorted((plugin_root / "skills").glob("*/SKILL.md")):
        text = f.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("description:"):
                out[f.parent.name] = line.split(":", 1)[1].strip().strip('"')
                break
    return out
