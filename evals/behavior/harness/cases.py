"""Load, import and check behavioral cases.

Sources
  evals/cases/*.json            suites written for the behavioral layer ({"suite", "layer", "cases": [...]})
  tests/routing/cases.json      the plugin's routing table: imported on the fly as L1 cases, so the table generated
                                by tests/routing/make_cases.py stays the one source of truth for selection
  --holdout FILE                a blinded held-out suite kept outside the repository (holdout.py)

Case schema (checked by check_cases):
  id            unique, [a-z0-9-]+
  layer         L1 | L2 | L3 | L4
  prompt        str, or turns: [{"prompt": str, "expect": [grader, ...]}, ...] for multi-turn cases
  expect        [grader spec, ...]  (graders.py); each may carry "invariant": "<id>" (invariants.json)
  fixtures      {"relative/path": str | {"json": obj} | {"from_plugin": "path/in/plugin"}}
  project       hep-research.project.json content (schema_version and plugin_version filled in when missing)
  protected     [glob, ...]  paths the `enforced` arm's hook denies (L4)
  arms          arms this case is meaningful in (default: all requested)
  force_skill   skill the `forced` arm injects (default: the first skill_loaded grader's skill)
  allowed_tools [tool, ...]  tools added to the default set for this case (e.g. WebFetch); `validate` lists them
  rubric        [{"criterion", "description", "levels": {"0": str, "1": str, "2": str}}]  judge.py
  lang, kind, tags, note, source
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .graders import GRADERS

EVALS = Path(__file__).resolve().parents[1]
REPO = EVALS.parents[1]
DEFAULT_PLUGIN = REPO / "plugins" / "hep-research"
ID_RX = re.compile(r"^[a-z0-9][a-z0-9.-]*$")
LAYERS = ("L1", "L2", "L3", "L4")


def plugin_root_default() -> Path:
    return DEFAULT_PLUGIN


def _set_path(obj, dotted: str, op: str, value=None):
    parts = dotted.split(".")
    for p in parts[:-1]:
        obj = obj[int(p)] if isinstance(obj, list) else obj[p]
    last = parts[-1]
    if op == "delete":
        if isinstance(obj, list):
            obj.pop(int(last))
        else:
            obj.pop(last)
    elif op == "set":
        if isinstance(obj, list):
            obj[int(last)] = value
        else:
            obj[last] = value
    elif op == "append":
        obj[last].append(value)
    else:
        raise ValueError(f"unknown mutation op {op}")


def expand_faults(doc: dict, plugin_root: Path | None) -> list[dict]:
    """L3 fault injection: one clean case plus one case per mutation of an upstream artifact. Each mutated case
    expects the downstream agent to notice (validate the input and stop or report); the clean case expects it to
    proceed. Mutations are declarative ({"op": "delete"|"set"|"append", "path": "a.b.0", "value": ...})."""
    import copy
    fm = doc.get("fault_matrix")
    if not fm or plugin_root is None:
        return []
    src = plugin_root / fm["artifact_from_plugin"]
    if not src.exists():
        return []
    base_art = json.loads(src.read_text(encoding="utf-8"))
    out = []
    for name, m in fm["mutations"].items():
        art = copy.deepcopy(base_art)
        for step in m.get("ops", []):
            _set_path(art, step["path"], step["op"], step.get("value"))
        c = copy.deepcopy(fm["base_case"])
        c["id"] = f"{fm['id_prefix']}-{name}"
        c["kind"] = "fault-clean" if name == "clean" else "fault"
        c.setdefault("fixtures", {})[fm["artifact_as"]] = {"json": art}
        c["expect"] = c.get("expect", []) + m["expect"]
        c["note"] = m.get("note", "")
        c["tags"] = sorted(set(c.get("tags", [])) | {"fault-injection", f"caught-by-validator:{m.get('validator_catches')}"})
        out.append(c)
    return out


def load_suite_files(case_dir: Path | None = None, plugin_root: Path | None = None) -> list[dict]:
    case_dir = case_dir or EVALS / "cases"
    out = []
    for f in sorted(case_dir.glob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        defaults = doc.get("defaults") or {}
        for c in doc["cases"] + expand_faults(doc, plugin_root):
            for key in ("fixtures", "project"):
                if key in defaults:
                    c[key] = {**defaults[key], **(c.get(key) or {})}
            for key in ("protected", "arms"):
                if key in defaults and key not in c:
                    c[key] = list(defaults[key])
            if "expect" in defaults and c.get("prompt"):
                c["expect"] = list(defaults["expect"]) + list(c.get("expect", []))
            c.setdefault("layer", doc.get("layer"))
            c.setdefault("suite", doc.get("suite", f.stem))
            c.setdefault("source", f"cases/{f.name}")
            out.append(c)
    return out


# ------------------------------------------------------------------ routing table import
def _routing_expect(skill: str, rc: dict) -> list[dict]:
    if skill == "ask":
        return [{"grader": "asks_question", "severity": "major", "label": "asks before acting"}]
    return [{"grader": "skill_loaded", "skill": skill, "also_accept": rc.get("also_accept", []), "severity": "major",
             "label": "selects the owner skill", "invariant": "L1-SELECT"}]


def import_routing(plugin_root: Path) -> list[dict]:
    """tests/routing/cases.json -> L1 cases. Profile bindings become the L1/L2 boundary checks: a bound profile must
    be read (blocking), and a theory or computing case must read no experiment profile (AC04, AC12)."""
    src = plugin_root / "tests" / "routing" / "cases.json"
    if not src.exists():
        return []
    profiles = {p["id"]: p for p in json.loads((plugin_root / "profiles" / "registry.json").read_text())["profiles"]}
    version = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text())["version"]
    out = []
    for rc in json.loads(src.read_text(encoding="utf-8"))["cases"]:
        expect = _routing_expect(rc["expected_primary"], rc)
        if rc.get("not"):
            expect.append({"grader": "skill_not_loaded", "skill": rc["not"], "severity": "minor",
                           "label": "does not load the neighbouring skill"})
        if rc.get("chain") and rc.get("kind") == "journey":
            expect.append({"grader": "skills_in_order", "skills": rc["chain"], "min_fraction": 0.5, "severity": "minor",
                           "label": "follows the documented handoff chain"})
        case = {"id": f"rt-{rc['id'].lower()}", "layer": "L1", "suite": "routing-table", "lang": rc["lang"],
                "kind": rc["kind"], "prompt": rc["prompt"], "expect": expect,
                "fixtures": dict(rc.get("inputs") or {}), "source": f"tests/routing/cases.json#{rc['id']}",
                "tags": [t for t in (rc.get("set"), rc.get("variant"), rc.get("journey")) if t]}
        bound = [p for p in rc.get("profiles") or [] if p in profiles]
        if bound:
            exps = [{"profile": p, "version": profiles[p]["version"]} for p in bound if p.startswith("experiment:")]
            ths = [{"profile": p, "version": profiles[p]["version"]} for p in bound if p.startswith("theory:")]
            case["project"] = {"schema_version": "1.2.0", "plugin_version": version,
                               **({"experiments": exps} if exps else {}), **({"theory": ths} if ths else {})}
            for p in bound:
                case["expect"].append({"grader": "file_read", "glob": f"profiles/{profiles[p]['path']}/index.md",
                                       "severity": "blocking", "label": f"reads the bound profile {p}",
                                       "invariant": "CTX-READ-BOUND-PROFILE"})
                case["expect"].append({"grader": "ordered", "first": {"read": f"profiles/{profiles[p]['path']}/*"},
                                       "then": {"text": True}, "severity": "major",
                                       "label": "reads the profile before answering",
                                       "invariant": "CTX-READ-BOUND-PROFILE"})
        if rc.get("kind") == "theory-no-experiment" or (rc["expected_primary"] in ("hep-theory", "hep-computing")
                                                         and not bound):
            case["expect"].append({"grader": "file_not_read", "glob": "profiles/experiments/*", "severity": "major",
                                   "label": "reads no experiment profile", "invariant": "CTX-NO-UNRELATED-PROFILE"})
        if rc.get("limited_support"):
            case["rubric"] = [{"criterion": "limited_support",
                               "description": "States that the request is outside what the plugin validates and what "
                                              "it can still do, instead of answering as if supported.",
                               "levels": {"0": "answers as if fully supported", "1": "hedges vaguely",
                                          "2": "names the limit and the general discipline it applies"}}]
            case["expect"].append({"grader": "judge", "criterion": "limited_support", "severity": "minor",
                                   "invariant": "CTX-LIMITED-SUPPORT"})
        if rc.get("turns"):
            first = {"prompt": rc["prompt"], "expect": case.pop("expect")}
            case.pop("prompt")
            case["turns"] = [first] + [{"prompt": t["prompt"], "expect": _routing_expect(t["expected"], t)}
                                       for t in rc["turns"]]
        out.append(case)
    return out


# ------------------------------------------------------------------ selection
def select(cases: list[dict], layers=None, ids=None, suites=None, tags=None, langs=None, sample=None, seed=20261017,
           bound_only=False):
    import random
    out = cases
    if layers:
        out = [c for c in out if c["layer"] in layers]
    if suites:
        out = [c for c in out if c.get("suite") in suites]
    if ids:
        rx = re.compile(ids)
        out = [c for c in out if rx.search(c["id"])]
    if tags:
        out = [c for c in out if set(tags) & set(c.get("tags", []))]
    if langs:
        out = [c for c in out if c.get("lang", "en") in langs]
    if bound_only:
        out = [c for c in out if binds_profile(c)]
    if sample and sample < len(out):
        # stratified by (layer, first expected skill) so a small smoke run still touches every owner
        rng = random.Random(seed)
        strata: dict = {}
        for c in out:
            strata.setdefault((c["layer"], first_expected_skill(c) or "-"), []).append(c)
        picked, per = [], max(1, sample // max(1, len(strata)))
        for key in sorted(strata):
            group = strata[key][:]
            rng.shuffle(group)
            picked += group[:per]
        rng.shuffle(picked)
        out = sorted(picked[:sample], key=lambda c: c["id"])
    return out


def binds_profile(case: dict) -> bool:
    proj = case.get("project") or {}
    return bool(proj.get("experiments") or proj.get("theory"))


def first_expected_skill(case: dict) -> str | None:
    specs = list(case.get("expect", []))
    for t in case.get("turns") or []:
        specs += t.get("expect", [])
    for s in specs:
        if s.get("grader") == "skill_loaded":
            sk = s.get("skill")
            return sk[0] if isinstance(sk, list) else sk
    return None


def all_expects(case: dict) -> list[dict]:
    specs = list(case.get("expect", []))
    for t in case.get("turns") or []:
        specs += t.get("expect", [])
    return specs


# ------------------------------------------------------------------ checks
def _walk_specs(specs):
    for s in specs:
        yield s
        if s.get("grader") in ("any_of", "all_of"):
            yield from _walk_specs(s.get("graders", []))
        if s.get("grader") == "not":
            yield from _walk_specs([s["grader_spec"]])


def check_cases(cases: list[dict], invariants: dict | None = None) -> list[str]:
    errs = []
    seen = set()
    for c in cases:
        cid = c.get("id", "?")
        if not ID_RX.match(cid):
            errs.append(f"{cid}: bad id")
        if cid in seen:
            errs.append(f"{cid}: duplicate id")
        seen.add(cid)
        if c.get("layer") not in LAYERS:
            errs.append(f"{cid}: layer must be one of {LAYERS}")
        if bool(c.get("prompt")) == bool(c.get("turns")):
            errs.append(f"{cid}: exactly one of prompt / turns")
        specs = all_expects(c)
        if not specs:
            errs.append(f"{cid}: no expectations")
        for s in _walk_specs(specs):
            if s.get("grader") not in GRADERS:
                errs.append(f"{cid}: unknown grader {s.get('grader')}")
            if s.get("severity", "major") not in ("blocking", "major", "minor"):
                errs.append(f"{cid}: bad severity {s.get('severity')}")
            if invariants is not None and s.get("invariant") and s["invariant"] not in invariants:
                errs.append(f"{cid}: invariant {s['invariant']} not in invariants.json")
            if s.get("grader") == "judge":
                crits = {r["criterion"] for r in c.get("rubric", [])}
                if s.get("criterion") not in crits:
                    errs.append(f"{cid}: judge criterion {s.get('criterion')} has no rubric entry")
        for p in (c.get("fixtures") or {}):
            if p.startswith("/") or ".." in Path(p).parts:
                errs.append(f"{cid}: fixture path {p} escapes the workspace")
        at = c.get("allowed_tools")
        if at is not None and not (isinstance(at, list) and all(isinstance(t, str) and t for t in at)):
            errs.append(f"{cid}: allowed_tools must be a list of tool names")
        if c.get("layer") == "L4" and not c.get("protected"):
            errs.append(f"{cid}: L4 case without protected paths")
    return errs


def ngram_leaks(prompt: str, text: str, n: int = 4) -> list[str]:
    """n-word sequences of `prompt` copied from `text` (a description). A held-out prompt that quotes the description
    measures string matching, not selection."""
    words = re.findall(r"[\w/+-]+", prompt.lower())
    hay = " ".join(re.findall(r"[\w/+-]+", text.lower()))
    return sorted({" ".join(words[i:i + n]) for i in range(len(words) - n + 1)
                   if " ".join(words[i:i + n]) in hay})
