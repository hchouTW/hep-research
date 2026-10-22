"""observe (spec sections 6.1, 7.3 and A7): everything outside the event log that decide needs, recorded as one
observed event. With an observation input (--observation FILE) the host facts come from that file instead of the
machine, so a run is byte-for-byte reproducible:
  {"host": {"name", "precondition", "session_start", "settings_mtime", "settings"}, "instruction_files": {path: sha},
   "shared_dirs": [dir, ...], "git_head": "..."}   (every key optional; missing keys are read from the machine)
"""
from __future__ import annotations

import datetime
import glob
import json
import os
import subprocess
from pathlib import Path

from contracts.review import (canonical_sha256, config_problems, effective_config, fold, format_time, parse_time,
                              sha256_file, sidecar_name)
from review_lib import units as U
from review_lib.store import load_asset, read_json

HOST = "claude-code"
SCAN_LIMIT = 2000           # files per shared directory
SCAN_BYTES = 1 << 20        # larger files are not read for review material


def _expand(p: str, project: Path) -> Path:
    """A review-hosts.json path with its placeholders filled in for this machine and project."""
    slug = str(project).replace("/", "-")
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join("~", ".claude")
    p = (p.replace("<project>", str(project)).replace("<project-slug>", slug)
         .replace("<uid>", str(getattr(os, "getuid", lambda: 0)()))
         .replace("<tmp>", str(Path("/tmp").resolve())).replace("<claude-config>", config))
    return Path(os.path.expanduser(p))


def _settings(host: dict, project: Path) -> list[tuple[Path, dict]]:
    out = []
    for p in host["settings_files"] + host["managed_settings"]:
        path = _expand(p, project)
        try:
            out.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    return out


def session_start(env=None, run=subprocess.run) -> str | None:
    """Start time (UTC) of the Claude Code host process named by CLAUDE_PID, from `ps -o lstart=`; None when the variable
    is unset or ps fails. Observed on the macOS CLI on 2026-10-21; not documented by the host (review-hosts.json)."""
    env = os.environ if env is None else env
    pid = str(env.get("CLAUDE_PID") or "")
    if not pid.isdigit():
        return None
    try:
        res = run(["ps", "-o", "lstart=", "-p", pid], capture_output=True, text=True, timeout=10,
                  env=dict(os.environ, LC_ALL="C", LANG="C"))
    except (OSError, subprocess.SubprocessError):
        return None
    text = " ".join(res.stdout.split())
    if res.returncode != 0 or not text:
        return None
    try:
        local = datetime.datetime.strptime(text, "%a %b %d %H:%M:%S %Y")
    except ValueError:
        return None
    return format_time(local.astimezone(datetime.UTC))


def host_facts(project: Path, given: dict | None) -> dict:
    """Isolation precondition (A7), settings that affect loading or isolation, and their modification time."""
    given = given or {}
    if "host" in given:
        h = dict({"name": HOST, "precondition": "none", "session_start": None, "settings_mtime": None, "settings": {}},
                 **given["host"])
        return h
    host = load_asset("review-hosts.json")["hosts"][HOST]
    files = _settings(host, project)
    env_files = [p for p, s in files if str((s.get("env") or {}).get("CLAUDE_CODE_FORK_SUBAGENT")) == "0"]
    deny = any("Agent(fork)" in ((s.get("permissions") or {}).get("deny") or []) for _, s in files)
    if env_files or os.environ.get("CLAUDE_CODE_FORK_SUBAGENT") == "0":
        pre = "fork-disabled-env"
    elif deny:
        pre = "fork-denied"
    else:
        pre = "none"
    mtime = None
    if env_files:
        t = max(p.stat().st_mtime for p in env_files)
        mtime = format_time(datetime.datetime.fromtimestamp(int(t), datetime.UTC))
    keep = set(host["loading_settings"]) | {"permissions", "env"}
    settings = {}
    for p, s in files:
        sub = {k: s[k] for k in sorted(s) if k in keep}
        if "env" in sub:
            sub["env"] = {k: v for k, v in sub["env"].items() if k.startswith("CLAUDE_CODE_")}
        if "permissions" in sub:
            sub["permissions"] = {"deny": [x for x in (sub["permissions"].get("deny") or []) if x.startswith("Agent(")]}
        settings[str(p)] = sub
    return {"name": HOST, "precondition": pre, "session_start": session_start(), "settings_mtime": mtime, "settings": settings}


def instruction_files(project: Path, given: dict | None) -> dict:
    """path -> sha256 (or 'absent') of the host instruction files A7 lists; @path imports are followed one level."""
    if given and "instruction_files" in given:
        return dict(sorted(given["instruction_files"].items()))
    spec = load_asset("review-hosts.json")["hosts"][HOST]["instruction_files"]
    paths = [_expand(p, project) for p in spec["user"] + spec["managed"]]
    d = project
    while True:
        paths += [d / n for n in spec["per_directory"]]
        paths += [d / n for n in spec["conditional"]["names"]]
        if d.parent == d:
            break
        d = d.parent
    paths += [project / p for p in spec["project"]]
    out = {}
    for p in paths:
        if p.is_dir():
            for f in sorted(p.rglob("*.md")):
                out[str(f)] = sha256_file(f) or "not-inspectable"
        elif p.exists():
            out[str(p)] = sha256_file(p) or "not-inspectable"
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.startswith("@"):
                        q = _expand(line[1:].strip(), project)
                        q = q if q.is_absolute() else p.parent / q
                        out[str(q)] = sha256_file(q) or "absent"
            except (OSError, UnicodeDecodeError):
                pass
    return dict(sorted(out.items()))


def shared_dirs(project: Path, given: dict | None) -> list[Path]:
    if given and "shared_dirs" in given:
        return [Path(p) for p in given["shared_dirs"]]
    out = []
    for e in load_asset("review-hosts.json")["hosts"][HOST]["shared_dirs"]:
        out += [Path(p) for p in sorted(glob.glob(str(_expand(e["pattern"], project))))]
    return out


def git_head(project: Path, given: dict | None):
    if given and "git_head" in given:
        return given["git_head"]
    try:
        res = subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout.strip() if res.returncode == 0 else None


def attempt_windows(st: dict, events: list, now: str) -> list[tuple]:
    """(start, end) of every attempt: from its dispatch to its outcome (or now while it runs)."""
    ends = {}
    for e in events:
        if e["event"] in ("accepted", "rejected", "withdrawn"):
            d = e["data"]
            ends[(d["round"], d["slot_id"], d["attempt"])] = e["time"]
    out = []
    for (r, sid), atts in st["attempts"].items():
        for k, a in atts.items():
            out.append((parse_time(a["dispatched"]["started"]), parse_time(ends.get((r, sid, k), now))))
    return out


def review_material(rv, st: dict, doc_units: list[dict]) -> list[str]:
    """Strings whose presence in a shared-directory file marks it as this review's: nonces, mutated canary text,
    the packet header and the longest units of the draft."""
    out = [rv.id]
    for atts in st["attempts"].values():
        for a in atts.values():
            out.append(a["dispatched"]["nonce"])
    out += [c["mutated"] for c in all_canaries(rv)]
    out += sorted((u["text"] for u in doc_units if len(u["text"]) > 60), key=len, reverse=True)[:5]
    return out


def all_canaries(rv) -> list[dict]:
    out = []
    for p in sorted(rv.private.glob("round-*/*/attempt-*/canary.json")):
        out += read_json(p).get("canaries", [])
    return out


def scan_shared(dirs: list[Path], windows: list[tuple], material: list[str]) -> dict:
    checked, bad, inside = [], [], []
    for d in dirs:
        if not d.is_dir():
            continue
        checked.append(str(d))
        files = sorted(p for p in d.rglob("*") if p.is_file())[:SCAN_LIMIT]
        for f in files:
            mt = datetime.datetime.fromtimestamp(int(f.stat().st_mtime), datetime.UTC)
            if any(a and b and a <= mt <= b for a, b in windows):
                inside.append(str(f))
                continue
            if f.stat().st_size > SCAN_BYTES:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(m and m in text for m in material):
                bad.append(str(f))
    return {"checked": checked, "contaminated": bad, "in_window": inside}


def sidecars(rv, st: dict) -> dict:
    out = {}
    for (r, sid), atts in sorted(st["attempts"].items()):
        for k in sorted(atts):
            adir = rv.attempt_dir(r, sid, k)
            name = sidecar_name(st, r, sid)
            final, tmp = adir / name, adir / f"{name}.tmp"
            ent = {"exists": final.is_file(), "tmp": tmp.is_file() and not final.is_file()}
            if final.is_file():
                ent["sha256"] = sha256_file(final)
            out[f"{r}/{sid}/{k}"] = ent
    return out


def unedited_changes(st: dict) -> list[str]:
    """Findings whose latest disposal is changed or partially-changed while the edited units then covered none of
    the finding's units (change_without_edit)."""
    out = []
    for g, f in st["findings"].items():
        if f["disposals"] and f["state"] in ("open", "reopened"):
            d = f["disposals"][-1]
            if d["disposition"] in ("changed", "partially-changed") and not set(d["edited_units"]) & set(d["finding_units"]) \
                    and f["state"] != "removed-pending":
                out.append(g)
    return sorted(out)


def changed_removed(rv, st: dict, text: str | None, r: int | None = None) -> tuple[list, list]:
    """Units of round r's table (default: the current round) that are changed or removed in the given text."""
    if text is None:
        return [], []
    r = r or st["round"]
    old = read_json(rv.units_path(r))["units"]
    m = U.map_units(old, U.split_markdown(text))
    return sorted(a for a, _ in m["changed"]), sorted(m["removed"])


def observe(rv, now: str, given: dict | None, private_root: Path) -> tuple[dict, list[dict]]:
    """(observed data, late events to write first)."""
    events = rv.events()
    st = fold(events)
    rd = st["rounds"][st["round"]]
    doc = rv.project / st["document"]
    try:
        text = read_doc(doc)
        doc_sha = sha256_file(doc)
    except (OSError, UnicodeDecodeError):
        text, doc_sha = None, None
    cfg_path = rv.project / config_rel(st)
    cfg_sha = sha256_file(cfg_path)
    try:
        cfg = read_json(cfg_path)
        probs = config_problems(cfg) + private_dir_problems(cfg, rv.project, private_root, given)
    except (OSError, ValueError):
        probs = ["review-config.json is missing or not JSON"]
    host = host_facts(rv.project, given)
    instr = instruction_files(rv.project, given)
    doc_units = U.split_markdown(text) if text else []
    shared = scan_shared(shared_dirs(rv.project, given), attempt_windows(st, events, now),
                         review_material(rv, st, doc_units))
    cans = all_canaries(rv)
    leak = bool(text) and any(c["mutated"] in text for c in cans)
    changed, removed = changed_removed(rv, st, text)
    side = sidecars(rv, st)
    repair, warnings = [], []
    if cfg_sha != rd["config_sha256"]:
        repair.append("config_changed")
    if probs:
        repair.append("config_out_of_range")
    if leak:
        repair.append("canary_in_deliverable")
    if host["precondition"] == "none":
        repair.append("isolation_precondition")
    elif host["precondition"] == "fork-denied":
        warnings.append("isolation: Agent(fork) is denied, but the docs do not say when the rule takes effect; "
                        "the R0 self-check is the fallback")
    if host["precondition"] == "fork-disabled-env":
        ss, mt = parse_time(host.get("session_start")), parse_time(host.get("settings_mtime"))
        if ss is None:
            warnings.append("cannot confirm whether the isolation setting has taken effect (no session start time)")
        elif mt and mt > ss:
            repair.append("isolation_not_yet_effective")
    if shared["contaminated"]:
        repair.append("shared_dir_contamination")
    if unedited_changes(st):
        repair.append("change_without_edit")
    late = []
    late_have = {(d["round"], d["slot_id"], d["attempt"]) for d in st["late"]}
    for key, ent in side.items():
        r, sid, k = key.split("/")
        a = st["attempts"][(int(r), sid)][int(k)]
        if ent["exists"] and a["outcome"] == "withdrawn" and (int(r), sid, int(k)) not in late_have:
            late.append({"round": int(r), "slot_id": sid, "attempt": int(k), "sha256": ent["sha256"]})
    data = {"time": now, "document_sha256": doc_sha, "config_sha256": cfg_sha, "config_problems": probs, "host": host,
            "instruction_files": instr, "shared_dirs": shared, "canary_in_deliverable": leak,
            "changed_units": changed, "removed_units": removed, "git_head": git_head(rv.project, given),
            "sidecars": side, "repair": sorted(set(repair)), "warnings": warnings}
    return data, late


SHARED_CONFIG = "reviews/review-config.json"


def config_rel(st: dict) -> str:
    """The configuration file of the review's current round, relative to the project: the shared
    reviews/review-config.json, or the review's own file when it was started with --own-config (round_started
    config_file)."""
    rd = st["rounds"].get(st["round"], {})
    return rd.get("config_file") or SHARED_CONFIG


def uses_shared_config(rv) -> bool:
    """Whether a review reads the shared configuration file (every review not started with --own-config)."""
    st = fold(rv.events())
    return config_rel(st) == SHARED_CONFIG


def read_doc(path: Path) -> str:
    """The document's text exactly as stored (no newline translation), so text and byte hashes agree."""
    return Path(path).read_bytes().decode("utf-8")


def private_dir_problems(cfg: dict, project: Path, private_root: Path, given: dict | None) -> list[str]:
    """private_dir must be outside the project tree and the host's shared directories (spec 5.1)."""
    p = Path(private_root).resolve()
    bad = []
    if p == project or project in p.parents:
        bad.append("private_dir: inside the project tree")
    for d in shared_dirs(project, given):
        d = d.resolve()
        if p == d or d in p.parents:
            bad.append(f"private_dir: inside the host shared directory {d}")
    return bad


def instruction_hash(obs: dict) -> str:
    """What dispatched and receipt compare (A7 timing): the instruction files and the loading and isolation settings."""
    return canonical_sha256({"files": obs["instruction_files"], "settings": obs["host"].get("settings", {}),
                             "precondition": obs["host"]["precondition"]})


def deadline(now: str, cfg: dict) -> str:
    t = parse_time(now) + datetime.timedelta(minutes=int(effective_config(cfg)["attempt_timeout_minutes"]))
    return format_time(t)
