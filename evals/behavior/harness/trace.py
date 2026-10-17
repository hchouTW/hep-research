"""Normalized view of one agent run, parsed from a host transcript.

The behavioral suites grade what the agent *did* (which skills it loaded, which files it read, which commands it ran,
what entered its context, what it answered), not only what it wrote. This module turns a Claude Code
`--output-format stream-json` transcript (one JSON object per line) into a `Trace`. The parser is tolerant: unknown
event types are kept in `raw` and ignored, so a host update degrades a grader to `unverified` instead of crashing.

Skill loads are recognized two ways, because hosts differ (docs/architecture.md, host fact 7):
  * a `Skill` tool call (input key `skill`, `name` or `command`), namespaced or not;
  * a `Read` of `skills/<name>/SKILL.md` inside the plugin.
Both are normalized to the bare skill name (`hep-statistics`); companion skills keep their plugin prefix
(`ams02-research:profile`).

Standard library only.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

HEP_PREFIX = "hep-research:"
_SKILL_MD = re.compile(r"(?:^|/)skills/([A-Za-z0-9_.-]+)/SKILL\.md$")
_READ_TOOLS = {"Read", "NotebookRead"}
_SEARCH_TOOLS = {"Grep", "Glob", "LS"}
_SHELL_TOOLS = {"Bash", "mcp__remote-devices__device_bash"}


def normalize_skill(name: str) -> str:
    name = (name or "").strip().lstrip("/")
    if name.startswith(HEP_PREFIX):
        return name[len(HEP_PREFIX):]
    return name


@dataclass
class Event:
    """One step of the run, in order. kind: text | tool_use | tool_result."""
    index: int
    kind: str
    turn: int = 0
    name: str = ""                      # tool name for tool_use / tool_result
    input: dict = field(default_factory=dict)
    text: str = ""                      # assistant text, or tool result content
    tool_use_id: str = ""
    is_error: bool = False

    @property
    def path(self) -> str:
        for key in ("file_path", "path", "notebook_path"):
            v = self.input.get(key)
            if isinstance(v, str) and v:
                return PurePosixPath(v.replace("\\", "/")).as_posix()
        return ""

    @property
    def command(self) -> str:
        v = self.input.get("command")
        return v if isinstance(v, str) else ""


@dataclass
class Trace:
    events: list[Event] = field(default_factory=list)
    final_text: str = ""
    meta: dict = field(default_factory=dict)
    raw_unknown: int = 0

    # ---------------------------------------------------------------- derived views
    def tool_uses(self, names: Iterable[str] | None = None) -> list[Event]:
        wanted = set(names) if names else None
        return [e for e in self.events if e.kind == "tool_use" and (wanted is None or e.name in wanted)]

    def result_for(self, use: Event) -> Event | None:
        for e in self.events:
            if e.kind == "tool_result" and e.tool_use_id and e.tool_use_id == use.tool_use_id:
                return e
        return None

    def skill_loads(self) -> list[tuple[int, str]]:
        """(event index, normalized skill) in load order; a skill loaded twice appears once (first load)."""
        seen: dict[str, int] = {}
        for e in self.events:
            if e.kind != "tool_use":
                continue
            name = ""
            if e.name == "Skill":
                name = normalize_skill(str(e.input.get("skill") or e.input.get("name") or e.input.get("command") or ""))
            elif e.name in _READ_TOOLS:
                m = _SKILL_MD.search(e.path)
                if m:
                    name = m.group(1)
            if name and name not in seen:
                seen[name] = e.index
        return sorted(((i, n) for n, i in seen.items()), key=lambda t: t[0])

    @property
    def skills(self) -> list[str]:
        return [n for _, n in self.skill_loads()]

    def hep_skills(self) -> list[str]:
        return [s for s in self.skills if s.startswith("hep-")]

    def reads(self) -> list[Event]:
        return self.tool_uses(_READ_TOOLS | _SEARCH_TOOLS)

    def commands(self) -> list[Event]:
        return self.tool_uses(_SHELL_TOOLS)

    def context_text(self) -> str:
        """Everything that entered the model's context from tools: the leakage channel for sealed values."""
        return "\n".join(e.text for e in self.events if e.kind == "tool_result")

    def assistant_text(self) -> str:
        parts = [e.text for e in self.events if e.kind == "text"]
        if self.final_text and (not parts or parts[-1].strip() != self.final_text.strip()):
            parts.append(self.final_text)
        return "\n".join(parts)

    def first_index(self, predicate) -> int | None:
        for e in self.events:
            if predicate(e):
                return e.index
        return None

    @property
    def answer_index(self) -> int:
        return len(self.events)

    def summary(self) -> dict:
        return {
            "skills": self.skills,
            "reads": [e.path for e in self.reads()][:40],
            "commands": [e.command[:200] for e in self.commands()][:40],
            "denied": sum(1 for e in self.events if e.kind == "tool_result" and e.is_error and "hook" in e.text.lower()),
            "final_chars": len(self.final_text),
            "meta": {k: self.meta.get(k) for k in ("model", "num_turns", "total_cost_usd", "duration_ms", "is_error")},
        }


# -------------------------------------------------------------------- parsing
def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for c in content:
            if isinstance(c, dict):
                if c.get("type") == "text":
                    out.append(str(c.get("text", "")))
                elif "content" in c:
                    out.append(_content_text(c["content"]))
            elif isinstance(c, str):
                out.append(c)
        return "\n".join(out)
    if isinstance(content, dict):
        return _content_text(content.get("content") or content.get("text") or "")
    return ""


def parse_stream(lines: Iterable[str], turn: int = 0, start_index: int = 0) -> Trace:
    tr = Trace()
    idx = start_index
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            tr.raw_unknown += 1
            continue
        typ = obj.get("type")
        if typ == "system" and obj.get("subtype") == "init":
            tr.meta.setdefault("model", obj.get("model"))
            tr.meta.setdefault("session_id", obj.get("session_id"))
            tr.meta.setdefault("tools", obj.get("tools"))
            tr.meta.setdefault("skills_available", obj.get("skills") or obj.get("slash_commands"))
            tr.meta.setdefault("plugins", obj.get("plugins"))
            tr.meta.setdefault("cli_version", obj.get("claude_code_version"))
        elif typ == "assistant":
            for c in (obj.get("message") or {}).get("content") or []:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "text" and c.get("text", "").strip():
                    tr.events.append(Event(idx, "text", turn, text=c["text"]))
                    idx += 1
                elif c.get("type") == "tool_use":
                    tr.events.append(Event(idx, "tool_use", turn, name=c.get("name", ""),
                                           input=c.get("input") or {}, tool_use_id=c.get("id", "")))
                    idx += 1
        elif typ == "user":
            content = (obj.get("message") or {}).get("content")
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        use_id = c.get("tool_use_id", "")
                        name = next((e.name for e in tr.events if e.tool_use_id == use_id and e.kind == "tool_use"), "")
                        tr.events.append(Event(idx, "tool_result", turn, name=name, text=_content_text(c.get("content")),
                                               tool_use_id=use_id, is_error=bool(c.get("is_error"))))
                        idx += 1
        elif typ == "result":
            tr.final_text = str(obj.get("result") or "")
            for k in ("total_cost_usd", "num_turns", "duration_ms", "is_error", "subtype", "session_id"):
                if k in obj:
                    tr.meta[k] = obj[k]
        else:
            tr.raw_unknown += 1
    if not tr.final_text:
        texts = [e.text for e in tr.events if e.kind == "text"]
        tr.final_text = texts[-1] if texts else ""
    return tr


def load_trace(path: str | Path) -> Trace:
    p = Path(path)
    return parse_stream(p.read_text(encoding="utf-8").splitlines())


def merge_turns(traces: list[Trace]) -> Trace:
    """Concatenate per-turn traces (multi-turn cases); event indices are renumbered, turn numbers kept."""
    out = Trace()
    for t_no, t in enumerate(traces):
        for e in t.events:
            uid = f"t{t_no}:{e.tool_use_id}" if e.tool_use_id else ""
            out.events.append(Event(0, e.kind, t_no, e.name, e.input, e.text, uid, e.is_error))
        out.raw_unknown += t.raw_unknown
        for k, v in t.meta.items():
            if k == "total_cost_usd":
                out.meta[k] = (out.meta.get(k) or 0) + (v or 0)
            else:
                out.meta.setdefault(k, v)
        out.meta.setdefault("turn_finals", []).append(t.final_text)
    for i, e in enumerate(out.events):
        e.index = i
    out.final_text = traces[-1].final_text if traces else ""
    return out
