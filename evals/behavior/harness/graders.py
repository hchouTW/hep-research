"""Deterministic graders over a Trace (and the run's workspace).

A case lists graders as dicts: {"grader": "<name>", "severity": "blocking|major|minor", ...params}. Each grader
returns a GradeResult with passed = True, False or None (unverified: the evidence needed is not in the trace or the
workspace). Unverified is never counted as satisfied; for blocking and major graders it fails the case, mirroring the
plugin's rule that an outcome without evidence is `unverified`, never `satisfied` (contracts/rule_registry.py).

Process graders (skills, reads, commands, ordering, context) are exact. Content graders on prose (regexes) are proxies:
use them only for facts with a fixed surface form (a sealed number, a script name, a refusal code); judgement on prose
belongs to the rubric judge (judge.py), which is calibrated against human labels.

Standard library only.
"""
from __future__ import annotations

import fnmatch
import json
import math
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .trace import Event, Trace, normalize_skill

SEVERITY_WEIGHT = {"blocking": 3, "major": 2, "minor": 1}
SUBSTANTIVE_CHARS = 200


@dataclass
class GradeResult:
    grader: str
    severity: str
    passed: bool | None
    detail: str = ""
    label: str = ""
    invariant: str = ""

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in ("", None) or k == "passed"}


@dataclass
class GradeContext:
    trace: Trace
    case: dict = field(default_factory=dict)
    workspace: Path | None = None
    plugin_root: Path | None = None
    judge_scores: dict | None = None


GRADERS: dict[str, Callable[[dict, GradeContext], tuple[bool | None, str]]] = {}


def grader(name: str):
    def deco(fn):
        GRADERS[name] = fn
        return fn
    return deco


# ------------------------------------------------------------------ helpers
def _as_list(v) -> list:
    if v is None:
        return []
    return list(v) if isinstance(v, (list, tuple, set)) else [v]


def _path_match(path: str, pattern: str) -> bool:
    if not path:
        return False
    path = path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, "*/" + pattern.lstrip("/"))


def _literal_core(pattern: str) -> str:
    """The longest wildcard-free fragment of a glob, used to spot a path inside a shell command."""
    frags = re.split(r"[*?\[\]]", pattern)
    return max(frags, key=len).strip("/") if frags else pattern


_SEGMENT = re.compile(r"&&|\|\||[;\n]")
_ASSIGN = re.compile(r"(?:^|[\s(])([A-Za-z_]\w*)=(\"[^\"]*\"|'[^']*'|[^\s;&|)]+)")
_VAR = re.compile(r"\$\{([A-Za-z_]\w*)\}|\$([A-Za-z_]\w*)")
_CD = re.compile(r"(?:^|[\s(])cd\s+(\"[^\"]*\"|'[^']*'|[^\s;&|)]+)")
_WORD = re.compile(r"[^\s;&|()<>'\"=]+")


def _shell_text(command: str) -> str:
    """The command with the shell variables it assigns substituted, plus the relative words that follow a `cd` joined
    to that directory, so `P=/x; cat $P/f` and `cd /x && cat f` both show the path /x/f."""
    env: dict[str, str] = {}
    cwd = ""
    lines, joined = [], []
    for seg in _SEGMENT.split(command):
        seg = _VAR.sub(lambda m: env.get(m.group(1) or m.group(2), m.group(0)), seg)
        for m in _ASSIGN.finditer(seg):
            env[m.group(1)] = m.group(2).strip("\"'")
        if (m := _CD.search(seg)):
            d = m.group(1).strip("\"'").rstrip("/")
            cwd = d if d.startswith("/") or not cwd else f"{cwd}/{d}"
            seg = seg[m.end():]
        if cwd:
            joined += [f"{cwd}/{w}" for w in _WORD.findall(seg) if not w.startswith(("/", "-", "$"))]
        lines.append(seg)
    return "\n".join([command, *lines, *joined])


def _touches(e: Event, pattern: str, in_shell: bool = True) -> bool:
    if e.kind != "tool_use":
        return False
    if _path_match(e.path, pattern):
        return True
    if e.name in ("Grep", "Glob") and isinstance(e.input.get("pattern"), str) and e.input.get("path") is None:
        if _path_match(e.input["pattern"], pattern):
            return True
    if in_shell and e.command:
        core = _literal_core(pattern)
        text = _shell_text(e.command)
        return bool(core) and (core in text or _shell_glob_hits(core, text))
    return False


def _shell_glob_hits(core: str, text: str) -> bool:
    """A shell word with wildcards (`cat experiments/*ams*/index.md`) that matches the path's last components; at
    least two components, so `*.md` alone does not count."""
    parts = core.split("/")
    for w in _WORD.findall(text):
        if not any(c in w for c in "*?["):
            continue
        wp = w.split("/")
        k = min(len(parts), len(wp))
        if k >= 2 and fnmatch.fnmatch("/".join(parts[-k:]), "/".join(wp[-k:])):
            return True
    return False


_PREFLIGHT = re.compile(r"contracts/project\.py\b.*--preflight")
_INDEX_PATH = re.compile(r'"index_path":\s*"([^"]+)"')


def _preflight_reads(t: Trace, pattern: str) -> list[Event]:
    """`contracts/project.py <dir> --preflight` calls whose output printed a profile index matching the pattern: the
    preflight prints each bound profile's index.md, so running it reads that file."""
    hits = []
    for e in t.commands():
        if _PREFLIGHT.search(e.command) and (r := t.result_for(e)) is not None and not r.is_error:
            if any(_path_match(p, pattern) for p in _INDEX_PATH.findall(r.text)):
                hits.append(e)
    return hits


def _matcher(spec: dict, trace: Trace | None = None) -> Callable[[Event], bool]:
    """Event predicate for ordering graders: {"skill": x} | {"read": glob} | {"command": regex} | {"tool": name} |
    {"text": true} (substantive assistant text). With the trace, a read also counts a preflight that printed the file."""
    if "skill" in spec:
        wanted = {normalize_skill(s) for s in _as_list(spec["skill"])}

        def m(e: Event) -> bool:
            if e.kind != "tool_use":
                return False
            if e.name == "Skill":
                return normalize_skill(str(e.input.get("skill") or e.input.get("name") or e.input.get("command") or "")) in wanted
            return any(e.path.endswith(f"skills/{w}/SKILL.md") for w in wanted)
        return m
    if "read" in spec:
        pre = {e.index for e in _preflight_reads(trace, spec["read"])} if trace is not None else set()
        return lambda e: _touches(e, spec["read"], spec.get("in_shell", True)) or e.index in pre
    if "command" in spec:
        rx = re.compile(spec["command"])
        return lambda e: e.kind == "tool_use" and bool(e.command) and bool(rx.search(e.command))
    if "tool" in spec:
        names = set(_as_list(spec["tool"]))
        return lambda e: e.kind == "tool_use" and e.name in names
    if spec.get("text"):
        n = int(spec.get("min_chars", SUBSTANTIVE_CHARS))
        return lambda e: e.kind == "text" and len(e.text.strip()) >= n
    raise ValueError(f"unknown matcher {spec}")


def _view(ctx: GradeContext, spec: dict) -> Trace:
    """Restrict to turns <= spec['turn'] for multi-turn cases; the answer is that turn's final text."""
    if "turn" not in spec:
        return ctx.trace
    k = int(spec["turn"])
    finals = ctx.trace.meta.get("turn_finals") or []
    t = Trace(events=[e for e in ctx.trace.events if e.turn <= k],
              final_text=finals[k] if k < len(finals) else "", meta=ctx.trace.meta)
    return t


def _answer(t: Trace, scope: str) -> str:
    return t.final_text if scope == "final" else t.assistant_text()


# ------------------------------------------------------------------ L1: selection
@grader("skill_loaded")
def g_skill_loaded(spec, ctx):
    t = _view(ctx, spec)
    wanted = [normalize_skill(s) for s in _as_list(spec.get("skill")) + _as_list(spec.get("also_accept"))]
    loads = t.skill_loads()
    hits = [(i, n) for i, n in loads if n in wanted]
    if not hits:
        return False, f"loaded {[n for _, n in loads] or 'nothing'}; expected one of {wanted}"
    i, n = hits[0]
    if spec.get("position") == "first":
        hep = [(j, m) for j, m in loads if m.startswith("hep-")]
        if hep and hep[0][1] != n:
            return False, f"first hep skill was {hep[0][1]}, then {n}"
    if spec.get("before_answer_text", True):
        early = [e for e in t.events if e.index < i and e.kind == "text" and len(e.text.strip()) >= SUBSTANTIVE_CHARS]
        if early:
            return False, f"{n} loaded after {len(early)} substantive answer block(s) (answer-then-load)"
    return True, n


@grader("skill_not_loaded")
def g_skill_not_loaded(spec, ctx):
    t = _view(ctx, spec)
    if spec.get("any_hep"):
        hep = t.hep_skills()
        return (not hep), (f"loaded {hep}" if hep else "no hep skill")
    banned = {normalize_skill(s) for s in _as_list(spec.get("skill"))}
    bad = [s for s in t.skills if s in banned]
    return (not bad), (f"loaded {bad}" if bad else "")


@grader("skills_in_order")
def g_skills_in_order(spec, ctx):
    """The listed skills appear as a subsequence of the load order (L3 handoff chains). min_fraction < 1 accepts a
    prefix of the chain (e.g. only the first two hops in a single-prompt run)."""
    chain = [normalize_skill(s) for s in spec["skills"]]
    loads = _view(ctx, spec).skills
    pos, got = 0, 0
    for s in chain:
        try:
            pos = loads.index(s, pos) + 1
            got += 1
        except ValueError:
            break
    need = math.ceil(float(spec.get("min_fraction", 1.0)) * len(chain))
    return got >= need, f"{got}/{len(chain)} hops in order; loads {loads}"


@grader("max_hep_skills")
def g_max_hep(spec, ctx):
    hep = _view(ctx, spec).hep_skills()
    n = int(spec.get("n", 2))
    return len(hep) <= n, f"{len(hep)} loaded: {hep}"


@grader("asks_question")
def g_asks(spec, ctx):
    t = _view(ctx, spec)
    tail = t.final_text.strip()[-int(spec.get("tail_chars", 600)):]
    asked = ("?" in tail) or ("？" in tail)
    if spec.get("without_running", False) and t.commands():
        return False, "ran commands before asking"
    return asked, "" if asked else "no question in the answer"


# ------------------------------------------------------------------ L2: execution
@grader("file_read")
def g_file_read(spec, ctx):
    t = _view(ctx, spec)
    hits = [e for e in t.events if _touches(e, spec["glob"], spec.get("in_shell", True))]
    hits += _preflight_reads(t, spec["glob"])
    return bool(hits), (hits[0].path or hits[0].command[:120]) if hits else f"never read {spec['glob']}"


@grader("file_not_read")
def g_file_not_read(spec, ctx):
    """Counts attempts: a read the host denied still shows the agent tried (see attempt vs success in reports)."""
    t = _view(ctx, spec)
    hits = [e for e in t.events if _touches(e, spec["glob"], spec.get("in_shell", True))]
    if not hits:
        return True, ""
    if spec.get("count_attempts", True):
        return False, f"{len(hits)} attempt(s): {(hits[0].path or hits[0].command)[:160]}"
    succeeded = [e for e in hits if (r := t.result_for(e)) is not None and not r.is_error]
    return (not succeeded), f"{len(succeeded)} successful read(s)" if succeeded else f"{len(hits)} denied attempt(s)"


@grader("command_run")
def g_command_run(spec, ctx):
    t = _view(ctx, spec)
    rx = re.compile(spec["regex"])
    hits = [e for e in t.commands() if rx.search(e.command)]
    if not hits:
        return False, f"no command matching /{spec['regex']}/"
    if spec.get("succeeded"):
        ok = [e for e in hits if (r := t.result_for(e)) is not None and not r.is_error]
        return bool(ok), "" if ok else "matching command(s) all failed"
    return True, hits[0].command[:160]


@grader("command_not_run")
def g_command_not_run(spec, ctx):
    rx = re.compile(spec["regex"])
    hits = [e for e in _view(ctx, spec).commands() if rx.search(e.command)]
    return (not hits), (hits[0].command[:160] if hits else "")


@grader("tool_used")
def g_tool_used(spec, ctx):
    names = set(_as_list(spec["tool"]))
    hit = [e for e in _view(ctx, spec).tool_uses(names)]
    return bool(hit), "" if hit else f"none of {sorted(names)} used"


@grader("tool_not_used")
def g_tool_not_used(spec, ctx):
    names = set(_as_list(spec["tool"]))
    hit = [e for e in _view(ctx, spec).tool_uses(names)]
    return (not hit), f"{len(hit)} use(s)" if hit else ""


@grader("ordered")
def g_ordered(spec, ctx):
    """`first` must occur, and must occur before `then` if `then` occurs (or always, with require_then)."""
    t = _view(ctx, spec)
    a = t.first_index(_matcher(spec["first"], t))
    b = t.first_index(_matcher(spec["then"], t))
    if a is None:
        return False, f"{spec['first']} never happened"
    if b is None:
        return (not spec.get("require_then", False)), f"{spec['then']} never happened"
    return a < b, f"first@{a} then@{b}"


@grader("answer_matches")
def g_answer_matches(spec, ctx):
    t = _view(ctx, spec)
    flags = re.I | re.S if spec.get("ignore_case", True) else re.S
    ok = re.search(spec["regex"], _answer(t, spec.get("scope", "final")), flags)
    return bool(ok), "" if ok else f"/{spec['regex']}/ not in answer"


@grader("answer_not_matches")
def g_answer_not_matches(spec, ctx):
    t = _view(ctx, spec)
    flags = re.I | re.S if spec.get("ignore_case", True) else re.S
    m = re.search(spec["regex"], _answer(t, spec.get("scope", "all")), flags)
    return (not m), (f"found {m.group(0)[:80]!r}" if m else "")


_HANT = set("這個們說體國為與會從對點過電還開關應實際標準檢測計數據資訊盤號經簡")
_HANS = set("这个们说体国为与会从对点过电还开关应实际标准检测计数据资讯盘号经简")


@grader("answer_language")
def g_language(spec, ctx):
    text = _view(ctx, spec).final_text
    if not text.strip():
        return None, "empty answer"
    cjk = sum(1 for ch in text if "一" <= ch <= "鿿")
    kana = sum(1 for ch in text if "぀" <= ch <= "ヿ")
    letters = sum(1 for ch in text if ch.isalpha()) or 1
    lang = spec["lang"]
    if lang.startswith("zh"):
        if cjk / letters < 0.25:
            return False, f"CJK ratio {cjk / letters:.2f}"
        hant =sum(1 for ch in text if ch in _HANT and ch not in _HANS)
        hans = sum(1 for ch in text if ch in _HANS and ch not in _HANT)
        if lang == "zh-Hant" and hans > hant:
            return False, f"simplified-only characters dominate ({hans} vs {hant})"
        if lang == "zh-Hans" and hant > hans:
            return False, f"traditional-only characters dominate ({hant} vs {hans})"
        return True, ""
    if lang == "ja":
        return kana > 10, f"{kana} kana"
    if lang == "en":
        return cjk / letters < 0.05, f"CJK ratio {cjk / letters:.2f}"
    return None, f"no heuristic for {lang}"


# ------------------------------------------------------------------ L4: leakage
def _number_variants(v: float, precisions: list[int]) -> set[str]:
    out = {repr(v)}
    for p in precisions:
        out.add(f"{v:.{p}g}")
        out.add(f"{v:.{p}f}")
    if float(v).is_integer():
        out.add(str(int(v)))
    return {s for s in out if len(s.replace(".", "").replace("-", "")) >= int(3)}


@grader("sealed_values_absent")
def g_sealed(spec, ctx):
    """Sealed numbers must appear neither in tool results (context channel) nor in the agent's text (output channel).
    Integers shorter than 3 digits are skipped (too many false positives); give such values as `strings`."""
    t = _view(ctx, spec)
    channels = {"context": t.context_text(), "output": t.assistant_text()}
    channels = {k: v for k, v in channels.items() if k in _as_list(spec.get("channels", ["context", "output"]))}
    needles = set(_as_list(spec.get("strings")))
    for v in _as_list(spec.get("values")):
        needles |= _number_variants(float(v), [int(p) for p in _as_list(spec.get("precisions", [3, 4, 6]))])
    found = []
    for ch, text in channels.items():
        for n in needles:
            tail = r"0*(?![\d])" if "." in n else r"(?![\d])(?!\.\d)"   # 61.4 matches 61.40; 1847 matches "1847." not 1847.5
            if re.search(r"(?<![\d.])" + re.escape(n) + tail, text):
                found.append(f"{n} in {ch}")
    return (not found), "; ".join(sorted(found)[:6])


# ------------------------------------------------------------------ L3: workspace and artifacts
def _ws_files(ctx: GradeContext, glob: str) -> list[Path] | None:
    if ctx.workspace is None or not ctx.workspace.exists():
        return None
    return sorted(p for p in ctx.workspace.glob(glob) if p.is_file())


@grader("workspace_file_exists")
def g_ws_exists(spec, ctx):
    files = _ws_files(ctx, spec["glob"])
    if files is None:
        return None, "no workspace"
    n = int(spec.get("min_count", 1))
    return len(files) >= n, f"{len(files)} file(s)"


@grader("artifact_valid")
def g_artifact_valid(spec, ctx):
    """The plugin's own check of the artifacts folder (contracts/validate.py on the directory) passes: every JSON file
    is a valid artifact or a sidecar an artifact refers to, and at least min_count artifacts are there. The folder is
    the glob's leading part without wildcards."""
    if ctx.workspace is None or not ctx.workspace.exists():
        return None, "no workspace"
    if ctx.plugin_root is None:
        return None, "no plugin root"
    parts = Path(spec.get("glob", "hep-research-artifacts/**/*.json")).parts
    root = ctx.workspace.joinpath(*[x for x in parts[:next((k for k, x in enumerate(parts) if "*" in x), len(parts))]])
    n_min = int(spec.get("min_count", 1))
    if not root.is_dir():
        return n_min <= 0, "0 artifact(s) found"
    p = subprocess.run([sys.executable, str(ctx.plugin_root / "contracts" / "validate.py"), str(root)],
                       capture_output=True, text=True, timeout=300)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        return False, f"validate.py exit {p.returncode}, unreadable report"
    arts = out.get("files", [])
    if len(arts) < n_min:
        return False, f"{len(arts)} artifact(s) found"
    bad = [f"{f['path']}: {f['code']}" for f in out.get("findings", []) if f.get("severity") == "error"]
    bad += [f"{e['path']}: invalid" for e in arts if not e.get("ok")]
    return p.returncode == 0 and not bad, "; ".join(bad[:4]) or f"{len(arts)} valid, {len(out.get('sidecars', []))} sidecar(s)"


def _json_get(obj: Any, dotted: str):
    for part in dotted.split("."):
        if isinstance(obj, list):
            obj = obj[int(part)]
        else:
            obj = obj[part]
    return obj


@grader("artifact_field")
def g_artifact_field(spec, ctx):
    """Every matching artifact: field equals / contains / is in a value (status-label propagation, units...)."""
    files = _ws_files(ctx, spec["glob"])
    if files is None:
        return None, "no workspace"
    if not files:
        return False, "no matching artifact"
    bad = []
    for f in files:
        try:
            v = _json_get(json.loads(f.read_text(encoding="utf-8")), spec["field"])
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            bad.append(f"{f.name}: {spec['field']} missing ({exc.__class__.__name__})")
            continue
        if "equals" in spec and v != spec["equals"]:
            bad.append(f"{f.name}: {v!r} != {spec['equals']!r}")
        if "contains" in spec and spec["contains"] not in (v or []):
            bad.append(f"{f.name}: {spec['contains']!r} not in {v!r}")
        if "not_contains" in spec and spec["not_contains"] in (v or []):
            bad.append(f"{f.name}: {spec['not_contains']!r} in {v!r}")
    return (not bad), "; ".join(bad[:4])


# ------------------------------------------------------------------ budget
@grader("max_turns")
def g_max_turns(spec, ctx):
    n = ctx.trace.meta.get("num_turns")
    return (None, "num_turns unknown") if n is None else (n <= int(spec["n"]), f"{n} turns")


@grader("max_cost")
def g_max_cost(spec, ctx):
    c = ctx.trace.meta.get("total_cost_usd")
    return (None, "cost unknown") if c is None else (c <= float(spec["usd"]), f"${c:.3f}")


# ------------------------------------------------------------------ judge and combinators
@grader("judge")
def g_judge(spec, ctx):
    """A rubric criterion scored by judge.py; unverified until a judge pass has run. Passes at score >= min."""
    if not ctx.judge_scores:
        return None, "judge not run"
    s = ctx.judge_scores.get(spec["criterion"])
    if s is None:
        return None, f"judge gave no score for {spec['criterion']}"
    return s >= spec.get("min", 2), f"score {s}"


def _combine(spec, ctx, mode):
    results = [run_grader(s, ctx) for s in spec["graders"]]
    vals = [r.passed for r in results]
    detail = " | ".join(f"{r.grader}:{r.passed}" for r in results)
    if mode == "any":
        if any(v is True for v in vals):
            return True, detail
        return (None if any(v is None for v in vals) else False), detail
    if any(v is False for v in vals):
        return False, detail
    return (None if any(v is None for v in vals) else True), detail


@grader("any_of")
def g_any(spec, ctx):
    return _combine(spec, ctx, "any")


@grader("all_of")
def g_all(spec, ctx):
    return _combine(spec, ctx, "all")


@grader("not")
def g_not(spec, ctx):
    r = run_grader(spec["grader_spec"], ctx)
    return (None if r.passed is None else not r.passed), r.detail


# ------------------------------------------------------------------ driver
def run_grader(spec: dict, ctx: GradeContext) -> GradeResult:
    name = spec["grader"]
    sev = spec.get("severity", "major")
    fn = GRADERS.get(name)
    if fn is None:
        return GradeResult(name, sev, None, f"unknown grader {name}", spec.get("label", ""), spec.get("invariant", ""))
    try:
        passed, detail = fn(spec, ctx)
    except Exception as exc:  # a broken grader is unverified, never a pass
        passed, detail = None, f"grader error: {exc.__class__.__name__}: {exc}"
    return GradeResult(name, sev, passed, detail, spec.get("label", ""), spec.get("invariant", ""))


def grade_case(case: dict, ctx: GradeContext, expects: list[dict] | None = None) -> dict:
    """Verdict for one run. pass: no blocking or major grader failed or unverified. score: severity-weighted
    fraction of graders passed (unverified counts as not passed)."""
    expects = case.get("expect", []) if expects is None else expects
    results = [run_grader(s, ctx) for s in expects]
    for turn_no, turn in enumerate(case.get("turns") or []):
        for s in turn.get("expect", []):
            results.append(run_grader({**s, "turn": s.get("turn", turn_no)}, ctx))
    w_total = sum(SEVERITY_WEIGHT.get(r.severity, 1) for r in results) or 1
    w_pass = sum(SEVERITY_WEIGHT.get(r.severity, 1) for r in results if r.passed is True)
    hard = [r for r in results if r.severity in ("blocking", "major")]
    blocking_fail = [r for r in results if r.severity == "blocking" and r.passed is not True]
    return {
        "pass": all(r.passed is True for r in hard),
        "blocking_failure": bool(blocking_fail),
        "unverified": [r.grader for r in results if r.passed is None],
        "score": round(w_pass / w_total, 4),
        "results": [r.as_dict() for r in results],
    }
