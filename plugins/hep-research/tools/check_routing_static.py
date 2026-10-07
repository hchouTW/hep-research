#!/usr/bin/env python3
"""Static routing check (AC20): do the seven skill descriptions cover the routing cases?

For each case in tests/routing/cases.json:
- every trigger term appears in the expected skill's "Use when" part of its description;
- a neighboring or negative case names the skill it must not go to ("not"), and that skill's "Not for" part names
  the expected skill, so the description itself routes the request away;
- an underspecified case expects "ask"; a limited-support (out-of-v1) case expects a core owner whose SKILL.md
  carries the "no validated domain profile" notice, and so does every skill in its optional "also_accept" list;
- handoff chains use real skills, end, and contain at most one round trip between two skills.
Coverage: at least one direct, one neighboring and one negative case per skill (direct and negative counted for
the skill the case is about), one case per journey J1-J12, English, Traditional and Simplified Chinese, Japanese and
German, the special categories (AMS-mentioning computing, theory without experiment, recasting, out-of-v1,
underspecified, multi-turn) and the variants (adversarial: a tool is named but the deliverable belongs to another
skill; quick: a short quick question). A multi-turn case lists later turns, each with its own expected skill and
trigger terms, checked the same way.
Also checks that no SKILL.md mentions a dispatch API. This is a static check of descriptions, not a live routing run.

Usage: python3 tools/check_routing_static.py   Exit 0 all pass, 1 otherwise. Output: JSON.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))
CATEGORIES = ["ams-computing", "theory-no-experiment", "recasting", "out-of-v1", "underspecified", "multi-turn"]
LANGS = ("en", "zh-Hant", "zh-Hans", "ja", "de")
VARIANTS = ("adversarial", "quick")  # a tool named for another skill's deliverable; a short quick question
LIMITED = re.compile(r"no validated domain profile|domain without a validated profile", re.I)
DISPATCH = re.compile(r"\b(dispatch|invoke_skill|call_skill|route_to)\s*\(", re.I)


def descriptions() -> dict:
    out = {}
    for s in SKILLS:
        text = (ROOT / "skills" / s / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r'^description:\s*"(.*)"\s*$', text, re.M)
        desc = m.group(1) if m else ""
        use, _, excl = desc.partition("Not for")
        out[s] = {"use": use.lower(), "not_for": excl.lower(), "body": text}
    return out


def chain_ok(chain) -> list[str]:
    errs = [f"unknown skill {c}" for c in chain if c not in SKILLS]
    pairs = [tuple(sorted(p)) for p in zip(chain, chain[1:]) if p[0] != p[1]]
    for p in set(pairs):
        back_and_forth = sum(1 for a, b in zip(chain, chain[1:]) if tuple(sorted((a, b))) == p)
        if back_and_forth > 2:
            errs.append(f"more than one round trip between {p}")
    if len(chain) > 6:
        errs.append("chain longer than six steps")
    return errs


def main() -> int:
    d = descriptions()
    cases = json.loads((ROOT / "tests" / "routing" / "cases.json").read_text(encoding="utf-8"))["cases"]
    results, cov = [], {s: set() for s in SKILLS}
    for c in cases:
        errs = []
        exp = c["expected_primary"]
        if c["kind"] == "underspecified":
            if exp != "ask":
                errs.append("underspecified requests must expect 'ask'")
        elif exp not in SKILLS:
            errs.append(f"unknown expected skill {exp}")
        else:
            for t in c.get("trigger_terms", []):
                if t.lower() not in d[exp]["use"]:
                    errs.append(f"trigger '{t}' not in the {exp} description")
            if c.get("limited_support") and not LIMITED.search(d[exp]["body"]):
                errs.append(f"{exp} SKILL.md lacks the limited-support notice")
            if not c.get("trigger_terms") and not c.get("limited_support"):
                errs.append("no trigger terms to check")
            for o in c.get("also_accept", []):
                if not c.get("limited_support"):
                    errs.append("also_accept is only for limited-support cases")
                elif o not in SKILLS or o == exp:
                    errs.append(f"also_accept names {o!r}, not another core skill")
                elif not LIMITED.search(d[o]["body"]):
                    errs.append(f"{o} SKILL.md lacks the limited-support notice")
        if c["kind"] in ("neighboring", "negative", "ams-computing"):
            ns = c.get("not")
            if ns not in SKILLS:
                errs.append("neighboring/negative case must name the skill it must not go to")
            elif exp not in d[ns]["not_for"]:
                errs.append(f"the {ns} description does not route this to {exp} in its 'Not for' part")
        if c["kind"] == "multi-turn":
            turns = c.get("turns")
            if not isinstance(turns, list) or not turns:
                errs.append("a multi-turn case needs later turns")
            for k, turn in enumerate(turns or [], 2):
                te = turn.get("expected")
                if te not in SKILLS:
                    errs.append(f"turn {k}: unknown expected skill {te}")
                    continue
                if not turn.get("prompt") or not turn.get("trigger_terms"):
                    errs.append(f"turn {k}: needs a prompt and trigger terms")
                for tt in turn.get("trigger_terms", []):
                    if tt.lower() not in d[te]["use"]:
                        errs.append(f"turn {k}: trigger '{tt}' not in the {te} description")
        if c.get("chain"):
            errs += chain_ok(c["chain"])
            if c["chain"][0] != exp:
                errs.append("chain must start at the expected primary skill")
        if c["kind"] == "direct":
            cov[exp].add("direct")
        if c["kind"] in ("neighboring", "negative") and c.get("not") in cov:
            cov[c["not"]].add(c["kind"])
        results.append({"id": c["id"], "ok": not errs, "errors": errs})
    coverage_errors = [f"{s}: missing {sorted({'direct', 'neighboring', 'negative'} - k)}" for s, k in cov.items()
                       if {"direct", "neighboring", "negative"} - k]
    journeys = {c.get("journey") for c in cases}
    coverage_errors += [f"no case for J{i}" for i in range(1, 13) if f"J{i}" not in journeys]
    coverage_errors += [f"no {k} case" for k in CATEGORIES if not any(c["kind"] == k for c in cases)]
    langs = {c["lang"] for c in cases}
    coverage_errors += [f"no {lang} cases" for lang in LANGS if lang not in langs]
    coverage_errors += [f"no {v} case" for v in VARIANTS if not any(c.get("variant") == v for c in cases)]
    dispatch = [s for s in SKILLS if DISPATCH.search(d[s]["body"])]
    rep = {"cases": len(cases), "failed": [r for r in results if not r["ok"]], "coverage_errors": coverage_errors,
           "dispatch_api_mentions": dispatch, "languages": sorted(langs),
           "note": "static check only: descriptions cover the cases; a live routing run needs approval (paid model calls)"}
    rep["ok"] = not rep["failed"] and not coverage_errors and not dispatch
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
