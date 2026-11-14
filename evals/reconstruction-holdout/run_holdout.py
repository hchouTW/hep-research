#!/usr/bin/env python3
"""Harness of the detector-reconstruction AI evaluation (plan v9.2 T13, K11, R22): runs the system under test (SUT) on
a holdout tasks file and writes the run records (schema t13-run/1) that the frozen scorer score_holdout.py reads.
Specification: plugins/hep-research/docs/dev/detector-reconstruction/t13-harness-spec.md, sections 1-3 and 8.

What it does (spec section 3):
  3.1 snapshot   copies the tracked plugin files of plugin_commit, minus docs/dev/, from the repository's object store
                 (git ls-tree + cat-file, never the live tree) into <run root>/plugin-snapshot/hep-research, checks the
                 copy's file list and hashes against the commit, records the file-list hash, makes the copy read-only
                 and re-checks it before every session.
  3.2 isolation  every session: a fresh CLAUDE_CONFIG_DIR under the run root (only the login file copied in), a fresh
                 CLAUDE_CODE_TMPDIR = TMPDIR (mode 0700) beside its stream, --setting-sources project,local,
                 --strict-mcp-config, --plugin-dir <snapshot>, a minimal environment (an allowlist, the settings'
                 pass_env and BASH_DEFAULT_TIMEOUT_MS / BASH_MAX_TIMEOUT_MS from the settings), cwd = a fresh rep
                 directory holding only that task's inputs, hash-checked. A run root inside
                 a git clone, or with a CLAUDE.md (or CLAUDE.local.md) in it or above it, is refused. The session must
                 report exactly this plugin, the recorded CLI version and model, or the evaluation stops.
  3.3 prompt     the task prompt, the input file names, then the frozen reporting suffix (verbatim from the spec) with
                 <subjects> filled.
  3.4 order      R repetitions (3 for the evaluation of record); a seeded shuffle per repetition round, recorded in
                 plan.json before the first session; a task never runs twice in a row.
  3.5 observe    from the CLI's stream-json, never from the SUT's report: commands and exit codes, reads, skills,
                 tokens, cost, turns, tool calls, clarifications; from the file system: every file written under the rep
                 directory with its SHA-256 (after the session's whole process group is killed); from the harness: wall
                 time and the end status. A command's exit code is 0 only from a non-error result; an error result
                 gives the last "Exit code N" in its text (else -1); a non-error result with a returnCodeInterpretation
                 gives 1; a command started or moved into the background (run_in_background, backgroundTaskId, or the
                 CLI's own "moved to the background" form; ids never re-pointed) gets the code of its completion record
                 (task notification: the last "exit code N" at the end of its summary; system task event; BashOutput
                 poll, its stdout/stderr ignored), accepted only with a terminal status and 0 only with "completed",
                 never from a subagent's user event; else -1 (completion not observed).
                 A turn or budget limit is a SUT failure: status completed with no valid report.
  3.6 report     the last fenced t13-report block of the final answer, kept raw beside the normalised copy.
  3.7 record     <run root>/runs/<task_id>/rep-<k>/run.json.
  3.8 stop/flag  stops the whole evaluation (STOP.json, exit 1): a tool read or search outside the allowed read roots
                 (rep directory, snapshot, the settings' roots, the session's own config and temporary directories) or
                 of a path the harness cannot resolve; a searching command aimed at or covering the home directory,
                 the repository, the run root, a protected root or ~/.claude, or run from a directory the harness cannot
                 follow; a reference (absolute, or relative after following cd) to the repository, a protected root,
                 ~/.claude, ~/.claude.json or a path inside the home directory; an absolute reference into the run root
                 outside the allowed roots; an event or init record the guard cannot judge (kind guard-error). Words
                 are read with quotes normalised, and a raw-text pass over the whole command (quotes, $'...', ${HOME}
                 forms, here-documents and -c code included) stops on any literal path into those areas; payloads of
                 bash/sh/zsh -c, eval, $(...), backticks, here-strings and shell here-documents are checked as commands;
                 a glob is judged by whether any expansion could fall in a stopping area. Round 5: a path-form word
                 of any command but echo/printf (a message after -m/--message/-e excepted) is a path argument, and so
                 are prefix assignments and the directory after -C/--git-dir/--work-tree/--directory (judged as
                 DIR/*); //x, file:// URLs, /proc/<pid>/root|cwd, brace expansions (at most 256, else a glob) and
                 decoded $'...' text are judged as the paths they name. cd/pushd is followed after
                 shell keywords and prefix commands; a cd to a target with $, a backtick, ~name, an option, or a
                 subshell makes the directory unknown. Flagged for the custodian (FLAGS.jsonl and the run record), never a stop: other
                 references outside the allowed roots (relative ones into the run root included), references from an
                 unknown directory, unresolvable path text, network commands, tool writes outside the rep directory.
                 The command check is a heuristic.
  3.9 rerun      a repetition that did not run for a harness cause before its session began (the CLI could not start,
                 a stream with no event at all, a harness error before any event) is rerun once, after the planned
                 sessions, and the rerun is recorded. A harness error after any event, a SUT crash or a timeout is
                 never rerun; the session's process group is killed whatever ends the attempt.
                 The snapshot is checked again after the last session.

Usage:
  run_holdout.py run --run-root DIR --tasks STAGING/tasks.json --inputs STAGING/inputs --sut t13-sut.json
                     --settings t13-settings.json --repo CLONE [--claude-bin claude] [--seed N] [--repetitions 3]
                     [--login-from LOGGED_IN_CONFIG_DIR] [--dry-run]
  run_holdout.py run --resume DIR [--custodian-category A|B] (same other arguments)
Inputs are found at <inputs>/<task_id>/<name>, else <inputs>/<name>. The tasks file and the inputs lie in a
custody-side staging folder outside the run root (protected like the repository); each task's inputs are copied into its
rep directory just before its session and their unchanged copies removed right after. A stop writes STOP.json and a
task-free STOP-SUMMARY.txt; a SUT-caused stop records the repetition completed with no report (a fail). --resume
continues the recorded plan after the custodian's decision (spec section 9). Round 7: each launch is recorded
(launch.json) and a resume first kills a CLI an interrupted harness left running; an interrupted repetition's inputs are
removed, its partial stream scanned (a hit is a stop for the custodian), otherwise it is rerun once; a repetition is rerun
at most once (RERUN.json claimed before the rerun session); a B decision is recorded beside the repetition. --dry-run validates everything and prints the plan without calling any CLI or writing anything.
Exit codes: 0 every planned session ran; 1 the evaluation stopped (contamination or an isolation failure; see
STOP.json); 2 rejected input or setup (nothing ran); 3 incomplete (a repetition stays not-run after its one rerun).
Standard library only.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import fnmatch
import hashlib
import json
import os
import posixpath
import queue
import random
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.dont_write_bytecode = True

EXIT_OK, EXIT_STOPPED, EXIT_BAD_INPUT, EXIT_INCOMPLETE = 0, 1, 2, 3

PLUGIN_NAME = "hep-research"
PLUGIN_PATH = "plugins/hep-research"
EXCLUDED_PREFIX = PLUGIN_PATH + "/docs/dev/"
TASKS_SCHEMA = "t13-holdout-tasks/1"
SUT_SCHEMA = "t13-sut/1"
SETTINGS_SCHEMA = "t13-settings/1"
RUN_SCHEMA = "t13-run/1"
PLAN_SCHEMA = "t13-plan/1"
SUT_KEYS = ("model", "plugin_version", "plugin_commit", "harness_sha256", "settings_sha256")
ISOLATION_FLAGS = ["--setting-sources", "project,local", "--strict-mcp-config"]
LOGIN_FILES = (".credentials.json",)
AUTH_ENV = ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")
# the only variables of the runner's environment a session sees (m5), besides the settings' pass_env; the harness sets
# CLAUDE_CONFIG_DIR, CLAUDE_CODE_TMPDIR, TMPDIR, PWD and the BASH_* timeouts itself
ENV_ALLOWLIST = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE", "TERM", "TZ",
                 *AUTH_ENV)
# effort_args is an allowlist (m1): empty, or exactly ["--effort", <the settings' effort>]
EFFORT_FLAG = "--effort"
SETTINGS_KEYS = {"schema", "cli", "effort", "effort_args", "max_turns", "wall_time_s", "session_budget_usd",
                 "allowed_tools", "disallowed_tools", "isolation_flags", "allowed_read_roots", "protected_roots",
                 "bash_timeouts_ms", "pass_env", "environment", "sandbox"}
# round 8, part B: every SUT session runs inside bubblewrap from an empty root; these system folders are bound read-only
SANDBOX_SYSTEM = ("/usr", "/lib", "/lib64", "/bin", "/sbin", "/etc")
SANDBOX_KEYS = {"enabled", "bwrap", "ro_binds"}
# never visible inside the sandbox (re-review 6, 3): hidden by an empty tmpfs where a system bind covers them
MASKED_ROOTS = ("/run/munge", "/var/run/munge", "/etc/slurm")
REQUIRED_SETTINGS = SETTINGS_KEYS - {"session_budget_usd", "disallowed_tools", "effort"}
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TASK_KEYS = {"task_id", "prompt", "inputs", "report_fields"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")
HEX_RE = re.compile(r"^[0-9a-f]{64}$")
READ_TOOLS = {"Read": ("file_path",), "NotebookRead": ("notebook_path", "file_path")}
SEARCH_TOOLS = {"Grep": ("path",), "Glob": ("path",), "LS": ("path",)}
WRITE_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}

# The frozen reporting suffix, verbatim from the spec (section 3, "Frozen reporting suffix"); a test pins it.
REPORTING_SUFFIX = """When you have finished, end your answer with one fenced code block whose info string is t13-report, containing a JSON
object {"outcome": ..., "claims": [...]}. outcome is one of: executed (you ran the method to completion and delivered
its results), partial (a restricted or partial delivery, including a run that failed), answered (a conceptual answer
without running anything), asked (you need information from me first), refused (you decline, saying why). Each claim
is {"kind": ..., "subject": ..., "value": ..., "unit": ..., "evidence": [...]}. Three kinds are positive only:
executed (a run that completed), passed (a check or gate that passed), capability (something can be done here). Report
every negative finding (something could not run, a run or a check failed, something is unavailable) as kind statement
(a short finding) or value (a number or category), never as executed, passed or capability. Use these subjects:
<subjects>
evidence lists what supports the claim: "cmd:<the exact command you ran>", "file:<path relative to the working
directory of a file you wrote>" or "read:<path of a file you read>". Report only what you did and saw in this session."""


class HarnessError(Exception):
    """Input or setup the harness refuses: exit 2, nothing runs."""


def need(cond, msg: str) -> None:
    if not cond:
        raise HarnessError(msg)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_text_safe(path, text: str) -> None:
    """Write a file without ever following a symlink (re-review 6, 1): the folder is opened with O_NOFOLLOW, the data
    goes to a fresh name created with O_CREAT|O_EXCL|O_NOFOLLOW, and a rename relative to the folder's descriptor
    replaces the target entry itself (a planted symlink is replaced, never written through)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        tmp = f".{path.name}.{os.getpid()}.{os.urandom(6).hex()}.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=dfd)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.rename(tmp, path.name, src_dir_fd=dfd, dst_dir_fd=dfd)
        except BaseException:
            try:
                os.unlink(tmp, dir_fd=dfd)
            except OSError:
                pass
            raise
    finally:
        os.close(dfd)


def append_line_safe(path, line: str) -> None:
    """Append by rewriting: the current content (read with O_NOFOLLOW) plus the line goes to a fresh name renamed onto
    the target, so neither a symlink nor a hard link to another file is ever written through (re-review 7)."""
    path = Path(path)
    old = ""
    dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dfd)
            with os.fdopen(fd, encoding="utf-8") as fh:
                old = fh.read()
        except FileNotFoundError:
            pass
    finally:
        os.close(dfd)
    write_text_safe(path, old + line)


def write_json(path: Path, doc) -> None:
    write_text_safe(path, json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def sha256_nofollow(path) -> str:
    """SHA-256 of a regular file opened with O_NOFOLLOW (a SUT file is never read through a symlink)."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    h = hashlib.sha256()
    with os.fdopen(fd, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path, what: str):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarnessError(f"{what}: cannot read {path}: {exc.__class__.__name__}") from None


# ------------------------------------------------------------------------------------------------ inputs
def load_sut(path: Path) -> dict:
    doc = load_json(path, "sut")
    need(isinstance(doc, dict) and doc.get("schema") == SUT_SCHEMA, f"sut: schema is not {SUT_SCHEMA}")
    for k in SUT_KEYS:
        need(isinstance(doc.get(k), str) and doc[k].strip(), f"sut: {k} must be a non-empty string")
    for k in ("harness_sha256", "settings_sha256"):
        need(HEX_RE.match(doc[k]) is not None, f"sut: {k} must be 64 lowercase hex digits")
    return {k: doc[k] for k in SUT_KEYS}


def load_settings(path: Path) -> dict:
    s = load_json(path, "settings")
    need(isinstance(s, dict) and s.get("schema") == SETTINGS_SCHEMA, f"settings: schema is not {SETTINGS_SCHEMA}")
    unknown = sorted(set(s) - SETTINGS_KEYS)
    need(not unknown, f"settings: keys the harness does not honour: {', '.join(unknown)}")
    missing = sorted(REQUIRED_SETTINGS - set(s))
    need(not missing, f"settings: missing keys: {', '.join(missing)}")
    cli = s.get("cli")
    need(isinstance(cli, dict) and isinstance(cli.get("name"), str) and isinstance(cli.get("version"), str)
         and cli["version"].strip(), "settings: cli needs name and version")
    need(s.get("isolation_flags") == ISOLATION_FLAGS,
         f"settings: isolation_flags must be the harness's isolation flags {ISOLATION_FLAGS}")
    need(isinstance(s.get("max_turns"), int) and not isinstance(s["max_turns"], bool) and s["max_turns"] >= 1,
         "settings: max_turns must be a positive integer")
    need(isinstance(s.get("wall_time_s"), (int, float)) and not isinstance(s["wall_time_s"], bool)
         and s["wall_time_s"] > 0, "settings: wall_time_s must be a positive number")
    b = s.get("session_budget_usd")
    need(b is None or (isinstance(b, (int, float)) and not isinstance(b, bool) and b > 0),
         "settings: session_budget_usd must be null or a positive number")
    for key in ("allowed_tools", "disallowed_tools"):
        v = s.get(key, [])
        need(isinstance(v, list) and all(isinstance(t, str) and t.strip() and not t.startswith("-") for t in v),
             f"settings: {key} must be a list of tool names")
    need(s.get("allowed_tools"), "settings: allowed_tools must not be empty")
    for key in ("allowed_read_roots", "protected_roots"):
        v = s.get(key, [])
        need(isinstance(v, list) and all(isinstance(p, str) and p.startswith("/") for p in v),
             f"settings: {key} must be a list of absolute paths")
    need(s.get("effort") is None or isinstance(s.get("effort"), str), "settings: effort must be a string or null")
    ea = s.get("effort_args")
    need(ea == [] or (s.get("effort") and ea == [EFFORT_FLAG, s["effort"]]),
         f"settings: effort_args must be [] or [\"{EFFORT_FLAG}\", <effort>] with the settings' effort")
    bt = s.get("bash_timeouts_ms")
    need(isinstance(bt, dict) and set(bt) == {"default", "max"}
         and all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in bt.values())
         and bt["default"] <= bt["max"],
         "settings: bash_timeouts_ms needs positive integers default <= max (BASH_DEFAULT_TIMEOUT_MS, "
         "BASH_MAX_TIMEOUT_MS)")
    sb = s.get("sandbox")
    need(isinstance(sb, dict) and set(sb) == SANDBOX_KEYS and isinstance(sb.get("enabled"), bool)
         and isinstance(sb.get("bwrap"), str) and sb["bwrap"].startswith("/") and isinstance(sb.get("ro_binds"), list)
         and all(isinstance(x, str) and x.startswith("/") for x in sb["ro_binds"]),
         "settings: sandbox needs enabled (true for every holdout run), bwrap (an absolute path) and ro_binds (absolute "
         "paths, all read-only: the CLI's real path and launcher, node if needed)")
    pe = s.get("pass_env")
    need(isinstance(pe, list) and all(isinstance(v, str) and ENV_NAME_RE.match(v)
                                      and not v.startswith(("CLAUDE", "SLURM_", "MUNGE_")) for v in pe),
         "settings: pass_env must be a list of variable names (none starting with CLAUDE, SLURM_ or MUNGE_)")
    need(isinstance(s.get("environment"), dict), "settings: environment must be an object (host class, Python, backends)")
    return s


def safe_name(name) -> bool:
    if not isinstance(name, str) or not name.strip() or name.startswith("/") or "\\" in name or "\0" in name:
        return False
    parts = name.split("/")
    return all(p not in ("", ".", "..") for p in parts)


def load_tasks(path: Path) -> list:
    doc = load_json(path, "tasks")
    need(isinstance(doc, dict) and doc.get("schema") == TASKS_SCHEMA, f"tasks: schema is not {TASKS_SCHEMA}")
    need(set(doc) <= {"schema", "holdout_id", "tasks"}, "tasks: a top-level key the system under test must not see")
    need(isinstance(doc.get("tasks"), list) and doc["tasks"], "tasks: 'tasks' must be a non-empty list")
    seen, out = set(), []
    for i, t in enumerate(doc["tasks"]):
        where = f"tasks[{i}]"
        need(isinstance(t, dict) and set(t) <= TASK_KEYS, f"{where}: only {sorted(TASK_KEYS)}")
        need(isinstance(t.get("task_id"), str) and ID_RE.match(t["task_id"]), f"{where}: task_id not an identifier")
        need(t["task_id"] not in seen, f"{where}: duplicate task_id")
        seen.add(t["task_id"])
        need(isinstance(t.get("prompt"), str) and t["prompt"].strip(), f"{where}: prompt must be a non-empty string")
        inputs = t.get("inputs", [])
        need(isinstance(inputs, list), f"{where}: inputs must be a list")
        names = set()
        for j, inp in enumerate(inputs):
            need(isinstance(inp, dict) and set(inp) == {"name", "sha256"} and safe_name(inp["name"])
                 and isinstance(inp["sha256"], str) and HEX_RE.match(inp["sha256"]),
                 f"{where}.inputs[{j}]: name (a relative path without '..') and a 64-hex sha256")
            need(inp["name"] not in names and inp["name"] != "run.json", f"{where}.inputs[{j}]: duplicate or reserved name")
            names.add(inp["name"])
        fields = t.get("report_fields")
        need(isinstance(fields, list) and fields, f"{where}: report_fields must be a non-empty list")
        for j, f in enumerate(fields):
            need(isinstance(f, dict) and set(f) <= {"subject", "description"} and isinstance(f.get("subject"), str)
                 and ID_RE.match(f["subject"]) and isinstance(f.get("description"), str) and f["description"].strip(),
                 f"{where}.report_fields[{j}]: subject (identifier) and description")
        out.append({"task_id": t["task_id"], "prompt": t["prompt"], "inputs": list(inputs),
                    "report_fields": list(fields)})
    return out


def input_source(inputs_dir: Path, task_id: str, name: str) -> Path:
    per_task = inputs_dir / task_id / name
    return per_task if per_task.is_file() else inputs_dir / name


def check_inputs(tasks: list, inputs_dir: Path) -> None:
    for t in tasks:
        for inp in t["inputs"]:
            src = input_source(inputs_dir, t["task_id"], inp["name"])
            need(src.is_file() and not src.is_symlink(), f"task {t['task_id']}: input {inp['name']} not found")
            need(sha256_file(src) == inp["sha256"],
                 f"task {t['task_id']}: input {inp['name']}: SHA-256 differs from the tasks file")


# ------------------------------------------------------------------------------------------------ run root
def check_run_root(run_root: Path) -> None:
    need(run_root.is_dir(), f"run root {run_root} is not a directory (create it for the run window)")
    real = Path(os.path.realpath(run_root))
    for top in {run_root, real}:
        for d in (top, *top.parents):
            dot = d / ".git"
            need(not (dot.is_file() or (dot / "HEAD").exists()),
                 f"the run root lies inside a git clone (.git at {d}); it must be outside every repository clone")
            for name in ("CLAUDE.md", "CLAUDE.local.md"):
                need(not (d / name).exists(), f"{name} found at {d}: the run root must have no CLAUDE.md in it or above it")
    for dirpath, _dirs, names in os.walk(run_root):
        for name in ("CLAUDE.md", "CLAUDE.local.md"):
            need(name not in names, f"{name} found in the run root at {dirpath}")
    default_cfg = Path(os.path.expanduser("~/.claude"))
    need(not real.is_relative_to(Path(os.path.realpath(default_cfg))), "the run root lies in the default ~/.claude")


def under(path: Path, root: Path) -> bool:
    p, r = Path(os.path.realpath(path)), Path(os.path.realpath(root))
    return p == r or r in p.parents


# ------------------------------------------------------------------------------------------------ snapshot (3.1)
def git(repo: Path, *args, data: bytes | None = None) -> bytes:
    proc = subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True, check=False)
    need(proc.returncode == 0, f"git {args[0]} failed: {proc.stderr.decode(errors='replace').strip()[:300]}")
    return proc.stdout


def commit_files(repo: Path, commit: str) -> tuple[str, dict]:
    """The full commit id and {path relative to the plugin: (mode, content bytes)} of its tracked plugin files minus
    docs/dev/, read from the object store."""
    full = git(repo, "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}").decode().strip()
    listing = git(repo, "ls-tree", "-r", "-z", "--full-tree", full, "--", PLUGIN_PATH)
    entries = []
    for rec in listing.split(b"\0"):
        if not rec:
            continue
        meta, _, path = rec.partition(b"\t")
        mode, typ, obj = meta.decode().split()
        path = path.decode("utf-8")
        if path.startswith(EXCLUDED_PREFIX):
            continue
        need(typ == "blob", f"snapshot: {path} is a {typ} (submodules are not supported)")
        entries.append((path, mode, obj))
    need(entries, f"snapshot: no tracked files under {PLUGIN_PATH} at {full}")
    out = git(repo, "cat-file", "--batch", data="".join(f"{o}\n" for _p, _m, o in entries).encode())
    files, pos = {}, 0
    for path, mode, obj in entries:
        nl = out.index(b"\n", pos)
        header = out[pos:nl].decode().split()
        need(len(header) == 3 and header[0] == obj and header[1] == "blob", f"snapshot: cannot read {path}")
        size = int(header[2])
        content = out[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1
        files[path[len(PLUGIN_PATH) + 1:]] = (mode, content)
    return full, files


def manifest_of(files: dict) -> tuple[list, str]:
    lines = [f"{sha256_bytes(content)}  {rel}" for rel, (_mode, content) in sorted(files.items())]
    return lines, sha256_bytes(("\n".join(lines) + "\n").encode())


def write_snapshot(dest: Path, files: dict) -> None:
    need(not dest.exists(), f"snapshot directory {dest} already exists")
    for rel, (mode, content) in sorted(files.items()):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == "120000":
            link = content.decode()
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(rel), link))
            need(not link.startswith("/") and not resolved.startswith(".."),
                 f"snapshot: symlink {rel} points outside the plugin")
            os.symlink(link, target)
            continue
        target.write_bytes(content)
        target.chmod(0o555 if mode == "100755" else 0o444)
    for dirpath, dirs, _names in os.walk(dest, topdown=False):
        for d in dirs:
            os.chmod(os.path.join(dirpath, d), 0o555)
    os.chmod(dest, 0o555)


def snapshot_lines(dest: Path) -> list:
    out = []
    for dirpath, _dirs, names in os.walk(dest):
        for n in names:
            p = Path(dirpath) / n
            rel = p.relative_to(dest).as_posix()
            data = os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
            out.append(f"{sha256_bytes(data)}  {rel}")
    return sorted(out, key=lambda line: line.split("  ", 1)[1])


# ------------------------------------------------------------------------------------------------ prompt, order
def build_prompt(task: dict) -> str:
    parts = [task["prompt"]]
    names = [i["name"] for i in task.get("inputs", [])]
    if names:
        parts.append("Input files (in the working directory):\n" + "\n".join(f"- {n}" for n in names))
    subjects = "\n".join(f"- {f['subject']}: {f['description']}" for f in task["report_fields"])
    parts.append(REPORTING_SUFFIX.replace("<subjects>", subjects))
    return "\n\n".join(parts)


def make_order(task_ids: list, repetitions: int, seed: int) -> list:
    """[(task_id, k)]: one seeded shuffle per repetition round, rounds in sequence, never a task twice in a row."""
    need(repetitions >= 1, "--repetitions must be at least 1")
    need(len(set(task_ids)) == len(task_ids), "duplicate task ids")
    need(repetitions == 1 or len(task_ids) >= 2, "interleaving needs at least two tasks")
    rng = random.Random(seed)
    order = []
    for k in range(1, repetitions + 1):
        perm = sorted(task_ids)
        rng.shuffle(perm)
        if order and perm[0] == order[-1][0]:
            perm[0], perm[1] = perm[1], perm[0]
        order += [(t, k) for t in perm]
    return order


# ------------------------------------------------------------------------------------------------ normalisation (3.6)
def normalise_path(text: str, rep_dirs: list) -> str:
    """Relative to the rep directory when the path lies inside it, absolute otherwise (no file-system access)."""
    p = os.path.expanduser(text.strip())
    if not p:
        return text
    if not p.startswith("/"):
        p = posixpath.join(rep_dirs[0], p)
    p = posixpath.normpath(p)
    if p.startswith("//"):
        p = "/" + p.lstrip("/")
    for r in rep_dirs:
        r = posixpath.normpath(r)
        if p == r:
            return "."
        if p.startswith(r.rstrip("/") + "/"):
            return p[len(r.rstrip("/")) + 1:]
    return p


def squash(text: str) -> str:
    return " ".join(str(text).split())


def normalise_report(report, commands: list, rep_dirs: list):
    """A copy of the report with cmd:, file: and read: references in the observed forms. A command reference that
    matches no observed command becomes 'unresolved-cmd:...' so that it can never pass as an observed command id."""
    out = copy.deepcopy(report)
    if not isinstance(out, dict) or not isinstance(out.get("claims"), list):
        return out
    by_text = {}
    for c in commands:
        by_text[squash(c["command"])] = c["id"]  # the last occurrence wins
    for claim in out["claims"]:
        if not isinstance(claim, dict) or not isinstance(claim.get("evidence"), list):
            continue
        refs = []
        for ref in claim["evidence"]:
            if isinstance(ref, str) and ":" in ref:
                kind, _, name = ref.partition(":")
                if kind == "cmd":
                    cid = by_text.get(squash(name))
                    ref = f"cmd:{cid}" if cid else f"unresolved-cmd:{name}"
                elif kind in ("file", "read") and name.strip():
                    ref = f"{kind}:{normalise_path(name, rep_dirs)}"
            refs.append(ref)
        claim["evidence"] = refs
    return out


FENCE_RE = re.compile(r"^[ \t]{0,3}(?P<f>`{3,}|~{3,})[ \t]*t13-report[ \t]*\n(?P<body>.*?)\n[ \t]{0,3}(?P=f)[ \t]*$",
                      re.M | re.S)


def extract_report(text: str):
    """(raw body, parsed object or None) of the last fenced t13-report block; (None, None) when there is none."""
    blocks = list(FENCE_RE.finditer(text or ""))
    if not blocks:
        return None, None
    raw = blocks[-1].group("body")
    try:
        parsed = json.loads(raw)
    except ValueError:
        return raw, None
    return raw, parsed if isinstance(parsed, dict) else None


# ------------------------------------------------------------------------------------------------ contamination (3.8)
_DELIM = r"""\s'"`;|&<>(),"""
# a command name may carry a path or a leading backslash (/usr/bin/find, \find)
_CMD = r"(?:^|[\s;|&(`{!])(?:sudo\s+)?(?:[^\s;|&()`'\"]*/|\\)?"
SEARCH_RE = re.compile(_CMD + r"(?:find|locate|plocate|mlocate|slocate|rg|ag|ack|ack-grep|fd|fdfind"
                       r"|tree|du|[efz]?grep\s+(?:[^|;&]*\s)?(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive"
                       r"|--dereference-recursive|-d\s*recurse)|ls\s+(?:[^|;&]*\s)?-[a-zA-Z]*R)(?=$|[\s;|&)`}])")
LOCATE_RE = re.compile(_CMD + r"(?:locate|plocate|mlocate|slocate)(?=$|[\s;|&)`}])")
# a command that can reach the network (reading 10): flagged for the custodian, never a stop
NETWORK_RE = re.compile(_CMD + r"(?:curl|wget|ssh|scp|sftp|rsync|nc|ncat|netcat|telnet|ftp"
                        r"|git\s+(?:clone|fetch|pull|push|ls-remote)|pip3?\s+(?:install|download)"
                        r"|python3?\s+-m\s+pip\s+(?:install|download)|conda\s+install|npm\s+install)(?=$|[\s;|&)`}])")
BENIGN = ("/dev/null", "/dev/zero", "/dev/stdin", "/dev/stdout", "/dev/stderr", "/dev/tty", "/dev/urandom",
          "/dev/random")
BENIGN_PREFIXES = ("/dev/fd/",)
GLOB_CHARS = "*?["
# words before the command proper; cd/pushd after them is still followed
PREFIX_WORDS = {"{", "(", "!", "if", "then", "elif", "else", "do", "while", "until", "time", "command", "builtin",
                "env", "nice", "nohup", "exec", "sudo", "timeout", "stdbuf", "ionice", "xargs"}
CLOSING_WORDS = {"}", ")", "fi", "done", "esac"}
ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
INTERPRETERS = {"python", "python2", "python3", "perl", "ruby", "node", "Rscript", "julia", "root", "php", "lua"}
# commands whose plain-word arguments name files (judged as paths when the directory is outside the roots)
READ_CMDS = {"cat", "less", "more", "head", "tail", "wc", "grep", "egrep", "fgrep", "zgrep", "rg", "ag", "ack", "find",
             "fd", "ls", "stat", "file", "cp", "mv", "tar", "zip", "unzip", "od", "xxd", "hexdump", "strings", "diff",
             "cmp", "awk", "sed", "sort", "uniq", "cut", "nl", "tac", "readlink", "realpath", "du", "tree", "source",
             ".", "base64", "md5sum", "sha1sum", "sha256sum", "jq", "rsync", "ln", "dd", "iconv", "column", "paste",
             "join", "comm", "split", "gzip", "gunzip", "zcat", "bzcat", "xzcat", "test", "["}
HEREDOC_RE = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
# a literal path in raw text (inside quotes too): absolute, ~ or ~user forms; $HOME forms are expanded before the scan
RAW_PATH_RE = re.compile(r"(?:^|(?<=[^\w.~/$-]))((?:~[A-Za-z_][\w.-]*|~)(?=/|$|[\s;|&<>()`,=:])"
                         r"[^\s;|&<>()`'\"]*|/[^\s;|&<>()`'\"]*)")
# round 5: scheme://... is a URL (not a path), except file:// whose path is a path
URL_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9+.-]*)://([^\s'\"`;|&<>()]*)")
# round 7 (G1): every ${HOME...} form, with any operator (%, #, /x/y, :n, ',', '^', @E, ...), is judged as $HOME
HOME_ANY_RE = re.compile(r"\$\{HOME(?:[^{}]|\{[^{}]*\})*\}|\$HOME\b")
PROC_RE = re.compile(r"^/proc/(?:self|thread-self|\d+|\$\$|\$\{?[A-Za-z_]\w*\}?)(?:/task/(?:\d+|\$\{?\w+\}?))?"
                     r"/(root|cwd)(?=/|$)(.*)$")
SQ_DOLLAR = "\x01"  # a $ inside single quotes: literal, never expanded (round 7)
MESSAGE_OPTS = {"-m", "--message", "-e"}  # the next word is a message or a pattern, not a path (round 5, finding 3)
TEXT_CMDS = {"echo", "printf"}
DIR_OPTS = {"-C", "--directory", "--git-dir", "--work-tree", "--chdir"}  # the next word is a directory read inside
DIR_OPT_EQ_RE = re.compile(r"^(--directory|--git-dir|--work-tree|--chdir)=(.+)$")
CMD_DIR_OPTS = {"cmake": {"-S", "-B"}}  # per-command options whose next word is a directory (round 7, G4)
CD_FOLLOW_OPTS_RE = re.compile(r"^-[PLe@]+$")  # cd -P/-L/-e/-@ DIR follows DIR like plain cd
MAX_BRACE = 256
ANSI_C_RE = re.compile(r"\$'((?:[^'\\]|\\.)*)'")
_ANSI_ESC = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v", "e": "\x1b", "E": "\x1b",
             "\\": "\\", "'": "'", '"': '"', "?": "?"}
MAX_DEPTH = 6


def spellings(path) -> list:
    a = posixpath.normpath(os.path.abspath(str(path)))
    r = os.path.realpath(str(path))
    return sorted({a, r})


def inside(p: str, roots) -> bool:
    return any(p == r or p.startswith(r.rstrip("/") + "/") for r in roots)


class Unresolvable(ValueError):
    """Path text the guard cannot resolve (a NUL byte, an unexpandable form)."""


class _Unknown:
    def __repr__(self):
        return "<unknown directory>"


UNKNOWN = _Unknown()  # the current directory of a command after a cd the guard cannot follow


def ansi_c(body: str) -> str:
    """Decode the escapes of a $'...' body (\\xHH, \\NNN octal, \\uHHHH, \\UHHHHHHHH, \\n, ...)."""
    def one(m):
        e = m.group(1)
        try:
            if e[0] == "x":
                return chr(int(e[1:], 16))
            if e[0] in "uU":
                return chr(int(e[1:], 16))
            if e[0] in "01234567":
                return chr(int(e, 8) & 0xFF)
        except (ValueError, OverflowError):
            return ""
        return _ANSI_ESC.get(e, "\\" + e)
    return re.sub(r"\\(x[0-9a-fA-F]{1,2}|u[0-9a-fA-F]{1,4}|U[0-9a-fA-F]{1,8}|[0-7]{1,3}|.)", one, body)


def decode_ansi(text: str) -> str:
    """$'...' replaced by its decoded text in single quotes (quotes inside dropped); $"..." by "..." (round 7, G2); a $
    inside single quotes marked literal."""
    text = ANSI_C_RE.sub(lambda m: "'" + ansi_c(m.group(1)).replace("'", "") + "'", text)
    return protect_single_quotes(text.replace('$"', '"'))


def protect_single_quotes(text: str) -> str:
    """Mark every literal $ as such: inside single quotes, or escaped by a backslash ('${HOME}' and \\$HOME are not
    $HOME), by bash's rules (shell_scan)."""
    out = list(text)
    for i, c, quote, escaped in shell_scan(text):
        if c == "$" and (quote == "'" or escaped):
            out[i] = SQ_DOLLAR
    return "".join(out)


def url_paths(text: str) -> str:
    """URLs removed, file:// URLs replaced by their path (file:///x, file://localhost/x, file://~/x)."""
    def one(m):
        scheme, rest = m.group(1).lower(), m.group(2)
        if scheme != "file":
            return " "
        if rest.startswith("localhost/"):
            rest = rest[len("localhost"):]
        elif not rest.startswith(("/", "~")):
            rest = "/" + rest.split("/", 1)[1] if "/" in rest else "/"
        return "=" + rest
    return URL_RE.sub(one, text)


def brace_expand(word: str) -> list:
    """Bash brace expansion ({a,b}, {n..m}, {a..e}) of a word, at most MAX_BRACE results; beyond that, every brace
    group becomes '*' (a glob that may reach any area). ${...} is never expanded."""
    def first_group(w, start=0):
        i = start
        while True:
            i = w.find("{", i)
            if i < 0:
                return None
            if i > 0 and w[i - 1] == "$":
                i += 1
                continue
            depth, j, parts, last = 0, i, [], i + 1
            while j < len(w):
                if w[j] == "{":
                    depth += 1
                elif w[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                elif w[j] == "," and depth == 1:
                    parts.append(w[last:j])
                    last = j + 1
                j += 1
            if j >= len(w):
                return None
            parts.append(w[last:j])
            if len(parts) >= 2:
                return i, j + 1, parts
            m = re.fullmatch(r"(-?\d+)\.\.(-?\d+)(?:\.\.(-?\d+))?|([A-Za-z])\.\.([A-Za-z])", parts[0])
            if m and m.group(1) is not None:
                a, b = int(m.group(1)), int(m.group(2))
                step = abs(int(m.group(3) or 1)) or 1
                if abs(b - a) // step + 1 > MAX_BRACE:
                    return i, j + 1, None
                rng = range(a, b + (1 if b >= a else -1), step if b >= a else -step)
                return i, j + 1, [str(x) for x in rng]
            if m:
                a, b = ord(m.group(4)), ord(m.group(5))
                return i, j + 1, [chr(x) for x in range(a, b + (1 if b >= a else -1), 1 if b >= a else -1)]
            i += 1

    out, done = [word], []
    while out:
        w = out.pop()
        g = first_group(w)
        if g is None:
            done.append(w)
        elif g[2] is None:
            return [re.sub(r"(?<!\$)\{[^{}]*\}", "*", w)]
        else:
            out += [w[:g[0]] + alt + w[g[1]:] for alt in g[2]]
        if len(out) + len(done) > MAX_BRACE:
            star = word
            while re.search(r"(?<!\$)\{[^{}]*\}", star):
                star = re.sub(r"(?<!\$)\{[^{}]*\}", "*", star)
            return [star]
    return done


def shell_tokens(seg: str) -> list:
    """Words of one command segment with quotes normalised ("$HOME"/.claude.json -> $HOME/.claude.json), $'...'
    decoded and comments dropped."""
    seg = strip_comment(decode_ansi(seg))
    try:
        return shlex.split(seg, posix=True)
    except ValueError:
        return re.sub(r"[\"']", "", seg).split()


def strip_comment(seg: str) -> str:
    """Cut a comment: an unquoted, unescaped # at the start of a word (a # inside a word, as in ${HOME#x}, or after an
    escaped blank, is not one), by bash's rules (shell_scan)."""
    prev_blank = True
    for i, c, quote, escaped in shell_scan(seg):
        if c == "#" and quote is None and not escaped and prev_blank:
            return seg[:i]
        prev_blank = quote is None and not escaped and c in " \t\n"
    return seg


def pieces(token: str) -> list:
    """The token and its parts around = < > , : (assignments, redirections, path lists); URLs dropped, file:// URLs
    replaced by their path."""
    token = url_paths(token)
    out = [token] if not token.startswith("=") else []
    out += [p for p in re.split(r"[=<>,:]", token) if p and p != token]
    return out


def path_form(text: str) -> str | None:
    """'abs' for /x, ~, ~/x, ~user..., $HOME..., ${HOME...}; 'rel' for anything containing '..'; else None."""
    if text.startswith(("/", "~")) or re.match(r"\$\{?HOME(?:\}|\b|[:/])", text):
        return "abs"
    if ".." in text:
        return "rel"
    return None


def shell_scan(text: str):
    """Yield (index, char, quote, escaped) with bash's quoting rules: outside quotes a backslash escapes the next
    character; inside double quotes it escapes only $ ` " \\ and newline; inside single quotes nothing is special but the
    closing quote. quote is the context the character is read in (None, "'" or '"'); escaped marks a character a
    backslash made literal (round 8, re-review 5: one tracker for quotes, comments and segments)."""
    quote, i, n = None, 0, len(text)
    while i < n:
        c = text[i]
        if quote == "$'":  # ANSI-C quoting: a backslash escapes the next character, ' closes
            if c == "\\" and i + 1 < n:
                yield i, c, "'", False
                yield i + 1, text[i + 1], "'", True
                i += 2
                continue
            yield i, c, "'", False
            if c == "'":
                quote = None
        elif quote == "'":
            yield i, c, quote, False
            if c == "'":
                quote = None
        elif quote == '"':
            if c == "\\" and i + 1 < n and text[i + 1] in '$`"\\\n':
                yield i, c, quote, False
                yield i + 1, text[i + 1], quote, True
                i += 2
                continue
            yield i, c, quote, False
            if c == '"':
                quote = None
        else:
            if c == "\\" and i + 1 < n:
                yield i, c, None, False
                yield i + 1, text[i + 1], None, True
                i += 2
                continue
            yield i, c, None, False
            if c == "$" and text[i + 1:i + 2] == "'":
                yield i + 1, "'", None, False
                quote = "$'"
                i += 2
                continue
            if c in "'\"":
                quote = c
        i += 1


def split_segments(text: str) -> list:
    """Split a command on ; & | && || and newlines outside quotes, $(...) and backticks."""
    out, cur, depth, tick, skip = [], [], 0, False, False
    for i, c, quote, escaped in shell_scan(text):
        if skip:
            skip = False
            cur.append(c)
            continue
        if quote is not None or escaped or c == "\\":
            cur.append(c)
            continue
        if c == "`":
            tick = not tick
        elif c == "$" and text[i + 1:i + 2] == "(":
            depth += 1
            cur.append("$")
            skip = True  # the ( that follows is copied as is
            continue
        elif c == ")" and depth:
            depth -= 1
        elif c in ";&|\n" and not depth and not tick:
            out.append("".join(cur))
            cur = []
            continue
        cur.append(c)
    out.append("".join(cur))
    return out


def cmd_name(word: str) -> str:
    return posixpath.basename(word.lstrip("\\"))


def substitutions(text: str) -> list:
    """Payloads of $(...) (balanced) and `...` in a command text."""
    out, i = [], 0
    while True:
        i = text.find("$(", i)
        if i < 0:
            break
        depth, j = 1, i + 2
        while j < len(text) and depth:
            depth += {"(": 1, ")": -1}.get(text[j], 0)
            j += 1
        out.append(text[i + 2:j - 1] if depth == 0 else text[i + 2:])
        i += 2
    out += re.findall(r"`([^`]*)`", text)
    return [p for p in out if p.strip()]


def split_heredocs(text: str) -> tuple[str, list]:
    """(the text without heredoc bodies, [(the line that opened the heredoc, its body)])."""
    lines, outer, docs, i = text.split("\n"), [], [], 0
    while i < len(lines):
        line = lines[i]
        outer.append(line)
        i += 1
        for m in HEREDOC_RE.finditer(line):
            strip_tabs, delim, body = m.group(1) == "-", m.group(3), []
            while i < len(lines):
                cand = lines[i].lstrip("\t") if strip_tabs else lines[i]
                i += 1
                if cand.strip() == delim:
                    break
                body.append(lines[i - 1])
            docs.append((line[:m.start()], "\n".join(body)))
    return "\n".join(outer), docs


class Guard:
    """The allowed read roots, the protected areas and the write area of one session.

    Stops (3.8): a tool read or search outside the allowed roots, or of a path the guard cannot resolve; a searching
    command aimed at or covering the home directory, the repository, the run root, a protected root or ~/.claude, or
    run from a directory the guard cannot follow; a reference to the repository, a protected root, ~/.claude,
    ~/.claude.json or a path inside the home directory (absolute, or relative after following cd; for an absolute
    literal also anywhere in the raw text, inside quotes, here-documents and -c code; a glob when any expansion could
    fall there); an absolute reference into the run root outside the allowed roots. Payloads of bash/sh -c, eval,
    $(...), backticks, here-strings and shell here-documents are checked as commands. Flags (recorded for the
    custodian, never a stop; the user's C2 answer): any other reference outside the allowed roots (relative references
    into the run root included), references from a directory the guard cannot follow, unresolvable path text, network
    commands, tool writes outside the rep directory. Stated limits (neither stopped nor flagged): variable indirection,
    symbolic links made at run time, paths built at run time or inside an interpreter, scripts written and then run,
    the directory stack (popd, cd -)."""

    def __init__(self, rep_dir: Path, snapshot: Path, settings: dict, run_root: Path, repo: Path, home: str,
                 own=(), write_ok=(), staging=(), expand_home=None, forbidden=(), sandbox_bound=None):
        self.rep = spellings(rep_dir)
        self.home = home
        # inside the sandbox ~ and $HOME are the session folder (re-review 6, C); the runner's home stays protected
        self.expand_home = expand_home or home
        self.forbidden = list(forbidden)
        # inside the sandbox (re-review 7): every bound path (system, ro binds, masked, own, snapshot) in every spelling
        sb = sandbox_bound or {}
        self.bound_all = list(sb.get("all", []))
        self.masked = list(sb.get("masked", []))
        self.masked_roots = [x for m in MASKED_ROOTS for x in spellings(m)] if sandbox_bound else []
        # own: the session's own configuration and temporary directories (the CLI's transcript and temporary files)
        self.allowed = self.rep + spellings(snapshot) + [s for r in (*settings.get("allowed_read_roots", []), *own)
                                                         for s in spellings(r)]
        self.write_ok = self.rep + [s for r in write_ok for s in spellings(r)]
        # staging: the custody-side folder of the tasks file and the inputs (round 6), protected like the repository
        strict = [repo, *settings.get("protected_roots", []), os.path.join(home, ".claude"),
                  os.path.join(home, ".claude.json"), *staging]
        self.strict = [s for p in strict for s in spellings(p)]
        self.repo_sp = spellings(repo)
        self.claude_sp = spellings(os.path.join(home, ".claude")) + spellings(os.path.join(home, ".claude.json"))
        self.run_root = spellings(run_root)
        self.home_sp = spellings(home)
        self.search_prot = self.strict + self.run_root + self.home_sp

    # ---------------------------------------------------------------- paths
    def expand(self, text: str) -> str:
        t = text.strip()
        if "\0" in t or not t:
            raise Unresolvable(repr(text))
        t = HOME_ANY_RE.sub(lambda m: self.expand_home, t)  # $HOME anywhere in the word (//$HOME/x is a path too)
        if t == "~" or t.startswith("~/"):
            t = self.expand_home + t[1:]
        elif t.startswith("~"):
            e = os.path.expanduser(t)
            if e == t:
                raise Unresolvable(repr(text))
            t = e
        return t

    def resolve(self, text: str, cwd=None) -> list:
        t = self.expand(text)
        if not t.startswith("/"):
            if cwd is UNKNOWN:
                raise Unresolvable(repr(text))
            t = posixpath.join(cwd or self.rep[0], t)
        lex = posixpath.normpath(t)
        if lex.startswith("//"):  # normpath keeps a leading //
            lex = "/" + lex.lstrip("/")
        for _ in range(8):  # /proc/<pid>/root/x is /x; /proc/<pid>/cwd/x is relative to the working directory
            m = PROC_RE.match(lex)
            if not m:
                break
            base = "/" if m.group(1) == "root" else (cwd if isinstance(cwd, str) else self.rep[0])
            lex = posixpath.normpath(base.rstrip("/") + "/" + m.group(2).lstrip("/"))
            if lex.startswith("//"):
                lex = "/" + lex.lstrip("/")
        if any(c in lex for c in GLOB_CHARS):
            return [lex]
        try:
            real = os.path.realpath(lex)
        except (ValueError, OSError):
            raise Unresolvable(repr(text)) from None
        return sorted({lex, real})

    def bind_ancestor(self, p: str) -> bool:
        """Inside the sandbox, a folder that leads to a bound path shows only the skeleton bwrap made for it."""
        return any(b.startswith(p.rstrip("/") + "/") for b in self.bound_all)

    def breach_target(self, p: str) -> bool:
        """A target whose answer without an error would show that the sandbox failed: inside a forbidden root, outside
        every bound path and not an ancestor of one; the munge and Slurm folders unless they are masked."""
        if not inside(p, self.forbidden) or inside(p, self.allowed) or self.bind_ancestor(p):
            return False
        if inside(p, self.masked_roots):
            return not inside(p, self.masked)
        return not inside(p, self.bound_all)

    def read_hit(self, text: str, cwd=None) -> str | None:
        try:
            paths = self.resolve(text, cwd)
        except Unresolvable:
            return f"read of a path the harness cannot resolve: {text!r}"
        for p in paths:
            if not inside(p, self.allowed) and not self.bind_ancestor(p):
                return f"read outside the allowed read roots: {p}"
        return None

    def write_flag(self, text: str) -> str | None:
        try:
            paths = self.resolve(text)
        except Unresolvable:
            return f"tool write to a path the harness cannot resolve: {text!r}"
        for p in paths:
            if not inside(p, self.write_ok):
                return f"tool write outside the rep directory: {p}"
        return None

    @staticmethod
    def _glob_reaches(pattern: str, areas, strict: bool = False, covering: bool = False) -> bool:
        """Whether an expansion of an absolute glob pattern could lie in (strict: strictly inside) one of the areas,
        or (covering) be an ancestor of one."""
        pp = pattern.split("/")
        for a in areas:
            ap = a.split("/")
            n = min(len(pp), len(ap))
            if not all(fnmatch.fnmatchcase(x, p) for p, x in zip(pp[:n], ap[:n])):
                continue
            if len(pp) >= len(ap) + (1 if strict else 0) or (covering and len(pp) < len(ap)):
                return True
        return False

    def _stop_area(self, p: str) -> bool:
        """Repository, protected roots, ~/.claude, ~/.claude.json, or strictly inside the home directory."""
        if any(c in p for c in GLOB_CHARS):
            return self._glob_reaches(p, self.strict) or self._glob_reaches(p, self.home_sp, strict=True)
        return inside(p, self.strict) or (inside(p, self.home_sp) and p not in self.home_sp)

    def _strict_area(self, p: str) -> bool:
        """Repository, protected roots, ~/.claude (anything under it) or ~/.claude.json."""
        if any(c in p for c in GLOB_CHARS):
            return self._glob_reaches(p, self.strict)
        return inside(p, self.strict)

    def _in_home(self, p: str) -> bool:
        if any(c in p for c in GLOB_CHARS):
            return self._glob_reaches(p, self.home_sp)
        return inside(p, self.home_sp)

    def _allowed(self, p: str) -> bool:
        if any(c in p for c in GLOB_CHARS):
            prefix = re.split(r"[*?\[]", p, maxsplit=1)[0]
            return inside(prefix.rsplit("/", 1)[0] or "/", self.allowed) and "/../" not in p
        return inside(p, self.allowed)

    def _judge(self, cand: str, cwd, form: str, search: bool, stops: list, flags: list) -> None:
        if cwd is UNKNOWN and form != "abs":
            (stops if search else flags).append(f"reference from a directory the harness cannot follow: {cand!r}")
            return
        try:
            paths = self.resolve(cand, cwd)
        except Unresolvable:
            (stops if search else flags).append(f"unresolvable reference: {cand!r}")
            return
        for p in paths:
            globbed = any(c in p for c in GLOB_CHARS)
            if self._allowed(p):  # an allowed root wins (e.g. an interpreter prefix inside the home directory)
                continue
            if not search and not globbed and self.bind_ancestor(p):  # a skeleton folder of the sandbox
                continue
            if globbed:
                covers = self._glob_reaches(p, self.search_prot, covering=True)
            else:
                covers = p == "/" or any(q.startswith(p.rstrip("/") + "/") for q in self.search_prot)
            in_prot = (self._glob_reaches(p, self.search_prot) if globbed else inside(p, self.search_prot))
            in_run = self._glob_reaches(p, self.run_root) if globbed else inside(p, self.run_root)
            if search and (covers or in_prot):
                stops.append(f"searching command aimed at {p}")
            elif not globbed and (p in BENIGN or p.startswith(BENIGN_PREFIXES)):
                continue
            elif self._stop_area(p):
                stops.append(f"command refers to protected material at {p}")
            elif in_run:
                if form == "abs":
                    stops.append(f"absolute reference into the run root at {p}")
                else:
                    flags.append(f"relative reference into the run root: {cand} -> {p}")
            else:
                flags.append(f"reference outside the allowed roots: {cand} -> {p}")

    def _judge_text(self, cand: str, cwd, stops: list, flags: list) -> None:
        """Round 4: a literal that is not a path argument (echo text, comments, other words, here-documents that are
        not code) stops only when it names the repository, a protected root, ~/.claude or ~/.claude.json; anything
        else outside the allowed roots (inside $HOME, the run root, elsewhere) is flagged."""
        try:
            paths = self.resolve(cand, cwd)
        except Unresolvable:
            flags.append(f"unresolvable reference: {cand!r}")
            return
        for p in paths:
            if self._allowed(p) or (p in BENIGN or p.startswith(BENIGN_PREFIXES)):
                continue
            if self._strict_area(p):
                stops.append(f"text names protected material at {p}")
            elif self._in_home(p):
                flags.append(f"text names a path inside the home directory: {cand} -> {p}")
            else:
                flags.append(f"text names a path outside the allowed roots: {cand} -> {p}")

    # ---------------------------------------------------------------- raw text
    def _raw_literals(self, text: str) -> list:
        """Absolute and ~ literal paths anywhere in the text, inside quotes too, with $HOME forms expanded."""
        t = protect_single_quotes(ANSI_C_RE.sub(lambda m: "'" + ansi_c(m.group(1)) + "'", text).replace('$"', '"'))
        t = url_paths(t).replace("=", " ")
        t = HOME_ANY_RE.sub(lambda m: self.expand_home, t)
        t = re.sub(r"\\(.)", r"\1", t)
        t = t.replace('"', "").replace("'", "")
        out = []
        for m in RAW_PATH_RE.finditer(t):
            for w in brace_expand(m.group(1)):
                out += [p for p in w.split(",") if p.startswith(("/", "~"))]
        return out

    def _raw_pass(self, text: str, stops: list, flags: list) -> None:
        """C2 and round 4: a literal anywhere in the text, whatever quoting or nesting hides it, stops when it names the
        repository, a protected root, ~/.claude or ~/.claude.json; inside $HOME otherwise it is flagged (a path
        argument of a reading command is judged again, by the stricter rule, in the word pass)."""
        for lit in self._raw_literals(text):
            try:
                paths = self.resolve(lit)
            except Unresolvable:
                continue
            for p in paths:
                if self._allowed(p):
                    continue
                if self._strict_area(p):
                    stops.append(f"literal path to protected material at {p}")
                elif self._in_home(p) and p not in self.home_sp:
                    flags.append(f"literal path inside the home directory: {p}")

    def _text_literals(self, text: str, cwd, stops: list, flags: list) -> None:
        for lit in self._raw_literals(text):
            self._judge_text(lit, cwd, stops, flags)

    def _code_literals(self, code: str, cwd, stops: list, flags: list) -> None:
        """Interpreter code (-c, here-documents): its absolute literal paths are references."""
        for lit in self._raw_literals(code):
            self._judge(lit, cwd, "abs", False, stops, flags)

    # ---------------------------------------------------------------- commands
    def command_check(self, command, cwd=None, depth: int = 0) -> tuple[list, list]:
        """(stop reasons, flag reasons) of one shell command. cd is followed within the command; a cd the harness
        cannot follow makes the directory unknown. Never raises."""
        stops, flags = [], []
        try:
            self._check(str(command), self.rep[0] if cwd is None else cwd, depth, stops, flags)
        except Exception as exc:  # a command the guard cannot parse is flagged, never a crash
            flags.append(f"command the harness could not parse ({exc.__class__.__name__})")
        return sorted(set(stops)), sorted(set(flags))

    def _nested(self, payload: str, cwd, depth: int, stops: list, flags: list) -> None:
        if depth >= MAX_DEPTH:
            flags.append("command nesting too deep to check")
            return
        s, f = self.command_check(payload, cwd, depth + 1)
        stops += s
        flags += f

    def _check(self, command: str, cwd, depth: int, stops: list, flags: list) -> None:
        self._raw_pass(command, stops, flags)
        if LOCATE_RE.search(command):
            stops.append("locate searches the whole file system")
        if NETWORK_RE.search(command):
            flags.append("network command (shell network is not blocked)")
        outer, docs = split_heredocs(command)
        for opener, body in docs:
            toks = shell_tokens(split_segments(opener)[-1]) if opener.strip() else []
            name = cmd_name(self._strip_prefixes(toks)[0]) if self._strip_prefixes(toks) else ""
            if name in SHELLS:
                self._nested(body, cwd, depth, stops, flags)
            elif name in INTERPRETERS or name.startswith("python"):
                self._code_literals(body, cwd, stops, flags)
            else:  # a document (cat > notes.md <<EOF): its words are text, not reads
                self._text_literals(body, cwd, stops, flags)
        for payload in substitutions(outer):
            self._nested(payload, cwd, depth, stops, flags)
        for raw_seg in split_segments(outer):
            seg = raw_seg.strip()
            if not seg:
                continue
            if seg.startswith("("):  # a subshell: its directory is not followed
                cwd = UNKNOWN
            toks = [t for t in shell_tokens(seg.strip("() ")) if t not in ("(", ")")]
            stripped, chdirs = self._prefix_split(toks)
            lead = [t for t in toks[:len(toks) - len(stripped)] if ASSIGN_RE.match(t)]
            toks = stripped
            while toks and toks[0] in CLOSING_WORDS:  # done < file: the redirection still counts
                toks = toks[1:]
            # assignments: before a command their values are its path arguments (GIT_DIR=~/x git ...); alone, text
            for a in lead:
                for w in brace_expand(a.split("=", 1)[1]):
                    for piece in pieces(w):
                        form = path_form(piece)
                        if form is not None and toks:
                            self._judge(piece, cwd, form, False, stops, flags)
                        elif form is not None:
                            self._judge_text(piece, cwd, stops, flags)
            if not toks:
                continue
            for d in chdirs:  # env -C DIR cmd: cmd runs in DIR
                cwd = self._cd([d], cwd, cwd is UNKNOWN or not inside(cwd, self.allowed), stops, flags)
            name = cmd_name(toks[0])
            search = SEARCH_RE.search(" " + seg) is not None
            outside_cwd = cwd is UNKNOWN or not inside(cwd, self.allowed)
            if name in ("cd", "pushd"):
                cwd = self._cd(toks[1:], cwd, outside_cwd, stops, flags)
                continue
            if name == "for":
                continue  # its words are values; literal paths among them were judged by the raw pass
            if name == "eval":
                self._nested(" ".join(toks[1:]), cwd, depth, stops, flags)
            if name in SHELLS:
                for i, t in enumerate(toks[1:-1], 1):
                    if re.fullmatch(r"-[a-zA-Z]*c[a-zA-Z]*", t):
                        self._nested(toks[i + 1], cwd, depth, stops, flags)
                        break
            interp = name in INTERPRETERS or name.startswith("python")
            if interp:
                for i, t in enumerate(toks[1:-1], 1):
                    if re.fullmatch(r"-[a-zA-Z]*[ce]", t):
                        self._code_literals(toks[i + 1], cwd, stops, flags)
                        break
            for i, t in enumerate(toks[:-1]):
                if t == "<<<":
                    self._nested(toks[i + 1], cwd, depth, stops, flags)
            if search and cwd is UNKNOWN:
                stops.append(f"searching command run from a directory the harness cannot follow: {seg!r}")
            if search and cwd is not UNKNOWN:  # a search without a path argument searches the current directory
                self._judge(cwd, cwd, "abs", True, stops, [])
            # round 5, finding 3: a path-form word of ANY command but echo/printf is a path argument (a message or
            # pattern after -m/--message/-e is text); bash/sh script arguments are interpreter scripts
            text_cmd = name in TEXT_CMDS
            for i, tok in enumerate(toks):
                prev = toks[i - 1] if i > 0 else ""
                message = (prev in MESSAGE_OPTS and not (interp and prev == "-e")) or tok.startswith("--message=")
                redirect = bool(re.match(r"\d*[<>]", tok)) or (i > 0 and re.fullmatch(r"\d*(?:[<>]{1,2}|<<<)&?",
                                                                                     prev) is not None)
                path_arg = i == 0 or search or redirect or not (text_cmd or message)
                into = (prev in DIR_OPTS or prev in CMD_DIR_OPTS.get(name, ())) and not text_cmd
                eq = DIR_OPT_EQ_RE.match(tok) if not text_cmd else None
                word = eq.group(2) if eq else tok
                into = into or eq is not None  # git -C ~ log / tar --directory=~ read inside ~: judge DIR/*
                for w in brace_expand(word.rstrip("/") + "/*" if into and word else word):
                    for piece in pieces(w):
                        if piece.startswith("@") and piece[1:2] in ("/", "~", "$", "."):
                            piece = piece[1:]  # @file arguments (curl -d @f, gcc @f): the file is read
                        form = path_form(piece)
                        if form is None and into:
                            form = "rel"
                        if form is not None:
                            if path_arg:
                                self._judge(piece, cwd, form, search, stops, flags)
                            else:  # round 4: echo/printf words and messages are text
                                self._judge_text(piece, cwd, stops, flags)
                            continue
                        if i == 0 or piece != w or w.startswith("-"):
                            continue
                        if search or (outside_cwd and path_arg):
                            if cwd is UNKNOWN and not search:
                                flags.append(f"reference from a directory the harness cannot follow: {w!r}")
                            elif cwd is not UNKNOWN:
                                self._judge(w, cwd, "rel", search, stops, flags)

    @staticmethod
    def _strip_prefixes(toks: list) -> list:
        return Guard._prefix_split(toks)[0]

    @staticmethod
    def _prefix_split(toks: list) -> tuple[list, list]:
        """Drop leading shell keywords, prefix commands with their options, and assignments (cd after them counts);
        also return the directories env -C/--chdir changes to (round 7, G3)."""
        toks, chdirs = list(toks), []
        while toks:
            t = toks[0]
            if cmd_name(t) == "env":
                toks.pop(0)
                while toks and (toks[0].startswith("-") or ASSIGN_RE.match(toks[0])):
                    o = toks.pop(0)
                    if o in ("-C", "--chdir") and toks:
                        chdirs.append(toks.pop(0))
                    elif o.startswith("--chdir="):
                        chdirs.append(o.split("=", 1)[1])
                    elif re.fullmatch(r"-[a-zA-Z0-9]*C", o) and toks:
                        chdirs.append(toks.pop(0))
                    elif o in ("-u", "--unset", "-S", "--split-string") and toks:
                        toks.pop(0)
            elif t in PREFIX_WORDS or cmd_name(t) in PREFIX_WORDS:
                toks.pop(0)
                while toks and (toks[0].startswith("-") or re.fullmatch(r"\d+(?:\.\d+)?[smhd]?", toks[0])):
                    toks.pop(0)
            elif ASSIGN_RE.match(t):
                toks.pop(0)
            else:
                break
        return toks, chdirs

    def _cd(self, args: list, cwd, outside_cwd: bool, stops: list, flags: list):
        opts, rest, ended = [], [], False
        for a in args:
            if not ended and a == "--":
                ended = True
            elif not ended and CD_FOLLOW_OPTS_RE.match(a):
                continue  # -P/-L/-e/-@ change how DIR is followed, not which DIR
            elif not ended and a.startswith("-"):
                opts.append(a)
            else:
                rest.append(a)
        target = rest[0] if rest else "~"
        form = path_form(target)
        tilde_user = target.startswith("~") and not (target == "~" or target.startswith("~/"))
        unknown = bool(opts) or "`" in target or "(" in target or tilde_user or ("$" in target and form != "abs")
        if form == "abs" or (form == "rel" and not unknown) or (outside_cwd and not unknown):
            self._judge(target, cwd, form or "rel", False, stops, flags)
        if unknown or (cwd is UNKNOWN and form != "abs"):
            return UNKNOWN
        try:
            return self.resolve(target, cwd)[0]
        except Unresolvable:
            return UNKNOWN


# ------------------------------------------------------------------------------------------------ observation (3.5)
# Bash result shapes (see tests/fake_claude.py for which are confirmed and which are guesses for the shakedown)
# N2: a background start is read only from tool_use_result.backgroundTaskId, from the result of a run_in_background
# command (EXPLICIT_BG_RE), or from a non-error result whose whole text is the CLI's automatic form (AUTO_BG_RE)
EXPLICIT_BG_RE = re.compile(r"^\s*Command running in background with ID:\s*([A-Za-z0-9_-]+)")
AUTO_BG_RE = re.compile(r"\s*Command\b[^\n<>]*?\bwas moved to the background \(ID:\s*([A-Za-z0-9_-]+)\)\.?"
                        r"(?:\s*Output is being written to:\s*\S+)?\s*")
# C1: a code is accepted only with a terminal status, and 0 only with status completed
TERMINAL = {"completed", "failed", "killed", "error", "errored", "timeout", "timed_out", "cancelled", "canceled",
            "interrupted"}
STREAMS_RE = re.compile(r"<(stdout|stderr)>.*?(?:</\1>|\Z)", re.S)
SUMMARY_CODE_RE = re.compile(r"exit code (-?\d+)\)?\s*\.?\s*\Z", re.I)
EXIT_TEXT_RE = re.compile(r"Exit code (-?\d+)")
OPEN_NOTE, CLOSE_NOTE = "<task-notification>", "</task-notification>"
TAG_RE = {k: re.compile(rf"<{k}>\s*(.*?)\s*</{k}>", re.S)
          for k in ("task-id", "status", "exit_code", "exit-code", "summary")}
OUTPUT_TOOLS = ("BashOutput", "TaskOutput")
BREACH_TOOLS = ("Read", "NotebookRead", "Grep", "Glob", "LS")  # their non-error answers are direct evidence
CLARIFICATION_NOTE = ("clarifications counts AskUserQuestion tool uses; in headless -p mode that tool may be "
                      "unavailable, so a question back usually shows only as the reported outcome 'asked'")


def tool_result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
    return ""


def skill_label(raw: str) -> str:
    return raw.split(":", 1)[1] if raw.startswith(PLUGIN_NAME + ":") else raw


def tag(text: str, name: str):
    m = TAG_RE[name].search(text)
    return m.group(1) if m else None


def single_tag(text: str, name: str):
    """The value of a tag that occurs exactly once (a repeated tag is no record: None)."""
    found = TAG_RE[name].findall(text)
    return found[0] if len(found) == 1 else None


def key(x) -> str:
    return x if isinstance(x, str) else json.dumps(x, sort_keys=True, default=str)


def as_dict(x) -> dict:
    return x if isinstance(x, dict) else {}


def as_list(x) -> list:
    return x if isinstance(x, list) else []


class Observer:
    """Facts from a stream-json session, fed one line at a time."""

    def __init__(self, guard: Guard, rep_dirs: list):
        self.guard, self.rep_dirs = guard, rep_dirs
        self.init = None
        self.result = None
        self.events = 0
        self.commands, self.reads, self.searches, self.tool_writes, self.skills = [], [], [], [], []
        self.tool_calls = self.clarifications = 0
        self.last_text = ""
        self.hits, self.flags = [], []
        self._bash, self._bg, self._output_calls = {}, {}, {}
        self.parse_errors = []
        self.sandboxed = False  # inside the sandbox an out-of-root attempt is a flag, reviewed before scoring
        self._current_use = None
        self._watch = {}  # sandboxed attempts aimed at a forbidden root, by tool use, until their result arrives
        self.breach = None  # such an attempt that came back without an error: the sandbox failed (isolation stop)
        self.trigger_event = None  # the event that caused the first stop
        self.result_after_trigger = False  # a tool result was in the stream after it (its output may have reached the model)

    def feed(self, line: str) -> None:
        line = line.strip()
        if not line.startswith("{"):
            return
        try:
            ev = json.loads(line)
        except ValueError:
            return
        if not isinstance(ev, dict):
            return
        self.events += 1
        typ = ev.get("type")
        if typ == "system" and ev.get("subtype") == "init":
            self.init = ev
        elif typ == "system" and ev.get("task_id") is not None:
            if ev.get("parent_tool_use_id") is not None:  # a subagent's event is no completion record
                return
            code = ev.get("exit_code")
            self._complete(key(ev["task_id"]), str(ev.get("status") or ""),
                           code if isinstance(code, int) and not isinstance(code, bool) else None)
        elif typ == "assistant":
            texts = []
            for block in as_list(as_dict(ev.get("message")).get("content")):
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    self._tool_use(block)
                elif block.get("type") == "text":
                    texts.append(str(block.get("text") or ""))
            if texts and ev.get("parent_tool_use_id") is None:
                self.last_text = "\n".join(texts)
        elif typ == "user":
            extra = ev.get("tool_use_result")
            if self.trigger_event is not None and self.events > self.trigger_event and any(
                    isinstance(b, dict) and b.get("type") == "tool_result"
                    for b in as_list(as_dict(ev.get("message")).get("content"))):
                self.result_after_trigger = True
            # a subagent's user event (parent_tool_use_id set) is never a source of completion records
            main = ev.get("parent_tool_use_id") is None
            content = as_dict(ev.get("message")).get("content")
            if isinstance(content, str) and main:
                self._notifications(content)
            for block in as_list(content):
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    self._tool_result(block, extra, main)
                elif block.get("type") == "text" and main:
                    self._notifications(str(block.get("text") or ""))
        elif typ == "result":
            self.result = ev

    def _hit(self, **kw):
        if self.sandboxed:  # round 8, part B: "Flag, review later" (the sandbox makes the target absent)
            self.flags.append({**kw, "reason": "sandbox (flag, review before scoring): " + str(kw.get("reason", ""))})
            targets = []
            if kw.get("path"):
                try:
                    targets = self.guard.resolve(str(kw["path"]))
                except Unresolvable:
                    targets = []
            targets += [m.group(1) for m in re.finditer(r"(?: at | -> |: )(/\S*)", str(kw.get("reason", "")))]
            # round 11 (the coordinator's ruling): only a tool read or search is watched; its answer is direct
            # evidence. A shell command's exit status says nothing about access (pipes, ||, test, printf, links,
            # here-documents), so a shell reference is a flag only, never a breach
            if kw.get("tool") in BREACH_TOOLS and any(self.guard.breach_target(t) for t in targets):
                self._watch[self._current_use] = kw
            return
        self.hits.append(kw)
        if self.trigger_event is None:
            self.trigger_event = self.events

    def _tool_use(self, block: dict) -> None:
        self.tool_calls += 1
        self._current_use = key(block.get("id"))
        name = str(block.get("name") or "")
        inp = block.get("input") if isinstance(block.get("input"), dict) else {}
        if name == "Bash":
            cmd = str(inp.get("command") or "")
            rec = {"id": f"c{len(self.commands) + 1}", "command": cmd, "exit_code": None,
                   "background": bool(inp.get("run_in_background")), "bg_id": None, "completion": None,
                   "bg_duplicate": None}
            self.commands.append(rec)
            self._bash[key(block.get("id"))] = rec
            stops, flags = self.guard.command_check(cmd)
            for h in stops:
                self._hit(tool="Bash", command=cmd, reason=h)
            for f in flags:
                self.flags.append({"tool": "Bash", "command": cmd, "reason": f})
        elif name in OUTPUT_TOOLS:
            bid = inp.get("bash_id") or inp.get("task_id") or inp.get("shell_id")
            if bid:
                self._output_calls[key(block.get("id"))] = key(bid)
        elif name in READ_TOOLS:
            path = next((str(inp[k]) for k in READ_TOOLS[name] if inp.get(k)), "")
            if path:
                norm = normalise_path(path, self.rep_dirs)
                if norm not in self.reads:
                    self.reads.append(norm)
                h = self.guard.read_hit(path)
                if h:
                    self._hit(tool=name, path=path, reason=h)
        elif name in SEARCH_TOOLS:
            targets = [str(inp[k]) for k in SEARCH_TOOLS[name] if inp.get(k)]
            pat = str(inp.get("pattern") or "")
            base = targets[0] if targets else None
            if name == "Glob" and (pat.startswith(("/", "~", "$HOME", "${HOME}", "..")) or "/../" in pat):
                prefix = re.split(r"[*?\[{]", pat, maxsplit=1)[0] or "/"
                targets.append(prefix if prefix.startswith(("/", "~", "$")) or base is None
                               else posixpath.join(base, prefix))
            self.searches.append({"tool": name, "targets": targets, "pattern": pat})
            for t in targets:
                h = self.guard.read_hit(t)
                if h:
                    self._hit(tool=name, path=t, reason=h)
        elif name in WRITE_TOOLS:
            path = str(inp.get(WRITE_TOOLS[name]) or "")
            if path:
                self.tool_writes.append(normalise_path(path, self.rep_dirs))
                f = self.guard.write_flag(path)
                if f:
                    self.flags.append({"tool": name, "path": path, "reason": f})
        elif name == "Skill":
            raw = str(inp.get("skill") or inp.get("command") or "")
            if raw:
                self.skills.append(skill_label(raw))
        elif name == "AskUserQuestion":
            self.clarifications += 1

    def _tool_result(self, block: dict, extra, main: bool = True) -> None:
        text = tool_result_text(block.get("content"))
        watched = self._watch.pop(key(block.get("tool_use_id")), None)
        if watched is not None and not block.get("is_error") and self.breach is None:
            self.breach = {**watched, "breach": "a forbidden root answered without an error"}
        bid = self._output_calls.get(key(block.get("tool_use_id")))
        if bid is not None:  # a BashOutput-style poll: a completion record when it carries a terminal status
            if main:
                meta = STREAMS_RE.sub("", text)  # the job's own output is never read as a status or a code
                code = single_tag(meta, "exit_code") or single_tag(meta, "exit-code")
                status = single_tag(meta, "status")
                if status and "<" not in status:
                    self._complete(bid, status, int(code) if code and re.fullmatch(r"-?\d{1,9}", code) else None)
            return
        rec = self._bash.get(key(block.get("tool_use_id")))
        if rec is None or rec["exit_code"] is not None or rec["bg_id"] is not None:
            return
        ex = as_dict(extra)
        bg_id = ex.get("backgroundTaskId")
        bg_id = key(bg_id) if bg_id else None
        if not bg_id and rec["background"]:
            m = EXPLICIT_BG_RE.match(text)
            bg_id = m.group(1) if m else None
        if not bg_id and not block.get("is_error"):  # only the CLI's whole automatic form, never other output
            m = AUTO_BG_RE.fullmatch(text)
            bg_id = m.group(1) if m else None
        if bg_id and str(bg_id) in self._bg:  # N2: a background id is never re-pointed
            rec["exit_code"], rec["bg_duplicate"] = -1, str(bg_id)
        elif bg_id:  # started (explicitly or automatically) in the background: the code comes from a completion record
            rec["bg_id"], rec["background"] = str(bg_id), True
            self._bg[str(bg_id)] = rec
        elif rec["background"] or ex.get("interrupted"):
            rec["exit_code"] = -1  # completion not observed
        elif block.get("is_error"):
            codes = EXIT_TEXT_RE.findall(text)
            rec["exit_code"] = int(codes[-1]) if codes else -1
        elif ex.get("returnCodeInterpretation"):
            rec["exit_code"] = 1  # a non-zero exit the CLI does not count as an error (grep 1, diff 1, test)
        else:
            rec["exit_code"] = 0

    def _notifications(self, text: str) -> None:
        """C1: one clean <task-notification> per text block. Nested or repeated notification tags, a summary that
        holds "<", or a repeated tag outside the summary make the block no completion record at all."""
        if OPEN_NOTE not in text:
            return
        if text.count(OPEN_NOTE) != 1 or text.count(CLOSE_NOTE) != 1:
            return
        start, end = text.index(OPEN_NOTE) + len(OPEN_NOTE), text.index(CLOSE_NOTE)
        if end < start:
            return
        body = text[start:end]
        s_open, s_close = body.find("<summary>"), body.rfind("</summary>")
        summary, outside = "", body
        if s_open >= 0 or s_close >= 0:
            if s_open < 0 or s_close < s_open:
                return
            summary = body[s_open + len("<summary>"):s_close]  # up to the LAST </summary>
            if "<" in summary:
                return
            outside = body[:s_open] + body[s_close + len("</summary>"):]
        bid, status = single_tag(outside, "task-id"), single_tag(outside, "status")
        if not bid or status is None or "<" in bid or "<" in status:
            return
        code = single_tag(outside, "exit_code") or single_tag(outside, "exit-code")
        if code is None:  # the last "exit code N", at the very end of the summary
            m = SUMMARY_CODE_RE.search(summary.strip())
            code = m.group(1) if m else None
        self._complete(bid, status, int(code) if code and re.fullmatch(r"-?\d{1,9}", code) else None)

    def _complete(self, bid: str, status: str, code) -> None:
        rec = self._bg.get(key(bid))
        if rec is None or rec["exit_code"] is not None:
            return
        status = str(status or "").strip().lower()
        rec["completion"] = {"status": status, "exit_code": code}
        if code is None or status not in TERMINAL or (code == 0 and status != "completed"):
            return  # stays unobserved (-1)
        rec["exit_code"] = code

    def stop_category(self) -> str:
        """The category of a SUT-caused stop, for the task-free summary (never a path or a command)."""
        if any(h.get("tool") != "Bash" for h in self.hits):
            return "tool read outside roots"
        reasons = [str(h.get("reason", "")) for h in self.hits]
        if any(r.startswith(("searching", "locate")) for r in reasons):
            return "search"
        paths = [m.group(1) for r in reasons for m in re.finditer(r"(?: at | -> )(/\S*)", r)]
        if any(inside(p, self.guard.repo_sp) for p in paths):
            return "repository read"
        if any(inside(p, self.guard.claude_sp) for p in paths):
            return "~/.claude"
        return "protected root"

    def observed_commands(self) -> list:
        out = []
        for c in self.commands:
            row = {"id": c["id"], "exit_code": -1 if c["exit_code"] is None else c["exit_code"], "command": c["command"]}
            if c["bg_id"]:
                row["background"] = {"id": c["bg_id"], "completion": c["completion"]}
            if c["bg_duplicate"]:
                row["background"] = {"id": c["bg_duplicate"], "duplicate_id_ignored": True}
            out.append(row)
        return out

    def final_text(self) -> str:
        if self.result is not None and isinstance(self.result.get("result"), str):
            return self.result["result"]
        return self.last_text


# ------------------------------------------------------------------------------------------------ sessions
class Stop(Exception):
    def __init__(self, kind: str, detail: dict):
        super().__init__(kind)
        self.kind, self.detail = kind, detail


def proc_start_time(pid: int):
    """The start time of a process (/proc/PID/stat field 22, clock ticks since boot), or None."""
    try:
        stat = Path(f"/proc/{int(pid)}/stat").read_text()
        return int(stat[stat.rindex(")") + 2:].split()[19])
    except (OSError, ValueError, IndexError):
        return None


def proc_argv(pid: int):
    try:
        raw = Path(f"/proc/{int(pid)}/cmdline").read_bytes()
    except (OSError, ValueError):
        return None
    return [a.decode(errors="replace") for a in raw.split(b"\0")[:-1]] if raw else []


def proc_pgid(pid: int):
    try:
        stat = Path(f"/proc/{int(pid)}/stat").read_text()
        return int(stat[stat.rindex(")") + 2:].split()[2])
    except (OSError, ValueError, IndexError):
        return None


def group_members(pgid: int) -> list:
    out = []
    for d in Path("/proc").iterdir():
        if d.name.isdigit() and proc_pgid(int(d.name)) == pgid:
            out.append(int(d.name))
    return out


def kill_group(pgid: int, proc=None) -> None:
    """TERM, then KILL, the session's whole process group (the CLI and anything it left behind)."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except (ProcessLookupError, PermissionError):
            return
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if proc is not None:
                proc.poll()
            try:
                os.killpg(pgid, 0)
            except (ProcessLookupError, PermissionError):
                return
            time.sleep(0.05)


class Harness:
    def __init__(self, args, sut, settings, tasks, me):
        self.args, self.sut, self.settings, self.me = args, sut, settings, me
        self.tasks = {t["task_id"]: t for t in tasks}
        self.run_root = Path(os.path.abspath(args.run_root))
        self.snapshot = self.run_root / "plugin-snapshot" / PLUGIN_NAME
        self.runs = self.run_root / "runs"
        self.home = os.path.expanduser("~")
        self.manifest = None
        self.staging = [Path(os.path.abspath(args.tasks)).parent, Path(os.path.abspath(args.inputs))]
        self.sandboxed = bool(settings.get("sandbox", {}).get("enabled")) and not getattr(args, "no_sandbox", False)
        self.session_started = False
        self.fallback_records = []

    def forbidden_roots(self) -> list:
        """Every folder that must be absent inside the sandbox, in every spelling (written and resolved): the repository,
        the staging folders, the run root, the runner's home, /ceph (and /ceph/work's real spelling), the munge and Slurm
        configuration folders and the settings' protected roots (re-review 6, 2-3)."""
        roots = [str(self.args.repo), *map(str, self.staging), str(self.run_root), os.path.expanduser("~"), "/ceph",
                 *MASKED_ROOTS, *self.settings.get("protected_roots", [])]
        if os.path.exists("/ceph/work"):
            roots.append("/ceph/work")
        return sorted({x for r in roots for x in spellings(r)})

    def sandbox_args(self, rep_dir: Path, cfg: Path, tmp_dir: Path) -> tuple[list, dict]:
        """bwrap arguments for one session: an empty root; the system folders, the CLI, the plugin snapshot and the
        interpreter and backend prefixes read-only (canonical paths, checked at start); the munge and Slurm folders
        masked by an empty tmpfs where a system bind covers them; the session folder (cwd and HOME), its config and tmp
        folders read-write; its own /proc and /dev, a new PID namespace, the network shared (the model API). Also what
        is bound: {"system", "ro", "own", "masked"}, each in every spelling."""
        args = ["--unshare-pid", "--die-with-parent", "--proc", "/proc", "--dev", "/dev"]
        system, ro, own, masked = [], [], [], []
        for p in SANDBOX_SYSTEM:
            if os.path.islink(p):
                args += ["--symlink", os.readlink(p), p]
            elif os.path.isdir(p):
                args += ["--ro-bind", p, p]
                system.append(p)
        for p in [*self.settings["sandbox"]["ro_binds"], str(self.snapshot), *self.settings.get("allowed_read_roots", [])]:
            p = posixpath.normpath(p)
            if os.path.exists(p) and p not in system + ro and not inside(p, system + ro):
                args += ["--ro-bind", p, p]
                ro += spellings(p)
        for m in MASKED_ROOTS:
            real = os.path.realpath(m)
            if os.path.lexists(real) and inside(real, system) and real not in masked:
                args += ["--tmpfs", real]
                masked.append(real)
        for p in (rep_dir, cfg, tmp_dir):
            args += ["--bind", str(p), str(p)]
            own += spellings(p)
        return args + ["--chdir", str(rep_dir)], {"system": system, "ro": ro, "own": own, "masked": masked}

    def absent_paths(self, bound: dict) -> list:
        """Paths that must not exist inside the sandbox, at every spelling: each forbidden root itself, or, for one that
        leads to a bound path, its other entries (two levels); the entries of a masked root."""
        allb = bound["system"] + bound["ro"] + bound["own"]
        out = []

        def visit(p: str, depth: int):
            p = posixpath.normpath(p)
            if not os.path.lexists(p) or len(out) >= 600:
                return
            if p in bound["masked"] or inside(p, bound["masked"]):
                if p in bound["masked"]:
                    try:
                        out.extend(os.path.join(p, n) for n in sorted(os.listdir(p))[:100])
                    except OSError:
                        pass
                return
            if inside(p, allb):
                return
            if any(b.startswith(p.rstrip("/") + "/") for b in allb):  # leads to a bound path: look one level down
                if depth < 2:
                    try:
                        for n in sorted(os.listdir(p))[:200]:
                            visit(os.path.join(p, n), depth + 1)
                    except OSError:
                        pass
                return
            out.append(p)
        for r in self.forbidden_roots():
            visit(r, 0)
        return sorted(set(out))

    def sandbox_selftest(self, sb_args: list, bound: dict) -> None:
        """At every session start: no bind exposes a forbidden root, and inside the very sandbox the session will get
        none of the absent paths exists. A sandbox that cannot start, an exposing bind or a visible absent path is an
        isolation stop (no session runs)."""
        forbidden = self.forbidden_roots()
        binds = bound["system"] + bound["ro"]
        covering = []
        for f in forbidden:
            if not os.path.lexists(f):  # nothing there to expose
                continue
            for b in binds:
                if inside(f, [b]) and not (b in bound["system"] and (f in bound["masked"]
                                                                       or os.path.realpath(f) in bound["masked"])):
                    covering.append(f)
        # a bind inside the repository, a staging folder or a protected root, or inside the run root other than the
        # session's own folders and the snapshot, exposes material that must be absent too
        inner = [x for r in (str(self.args.repo), *map(str, self.staging), *self.settings.get("protected_roots", []))
                 for x in spellings(r)]
        own = bound["own"] + spellings(self.snapshot)
        covering += [b for b in binds if inside(b, inner)
                     or (inside(b, spellings(self.run_root)) and not inside(b, own))]
        if covering:  # a bind that is, contains or lies inside a folder that must be absent
            raise Stop("isolation", {"reason": f"sandbox self-test: {len(set(covering))} bound path(s) expose folders "
                                               "that must be absent inside the sandbox", "visible": sorted(set(covering))})
        absent = self.absent_paths(bound)
        script = 'for p in "$@"; do [ -e "$p" ] && echo "VISIBLE:$p"; done; echo SELFTEST-OK'
        try:
            p = subprocess.run([self.settings["sandbox"]["bwrap"], *sb_args, "--", "/bin/sh", "-c", script, "sh",
                                *absent], capture_output=True, text=True, timeout=120, env={"PATH": "/usr/bin:/bin"})
            out = p.stdout
        except (OSError, subprocess.SubprocessError) as exc:
            out = f"bwrap failed: {exc.__class__.__name__}"
        if "SELFTEST-OK" not in out:
            raise Stop("isolation", {"reason": "sandbox self-test: the sandbox did not start", "detail": out[-400:]})
        visible = [x[len("VISIBLE:"):] for x in out.splitlines() if x.startswith("VISIBLE:")]
        if visible:
            raise Stop("isolation", {"reason": f"sandbox self-test: {len(visible)} path(s) that must be absent are "
                                               "visible inside the sandbox", "visible": visible})

    def command(self, prompt: str) -> list:
        s = self.settings
        cmd = [self.args.claude_bin, "-p", prompt, "--model", self.sut["model"], "--output-format", "stream-json",
               "--verbose", "--max-turns", str(s["max_turns"]), *ISOLATION_FLAGS, "--plugin-dir", str(self.snapshot),
               "--allowedTools", *s["allowed_tools"]]
        if s.get("disallowed_tools"):
            cmd += ["--disallowedTools", *s["disallowed_tools"]]
        if s.get("session_budget_usd") is not None:
            cmd += ["--max-budget-usd", f"{s['session_budget_usd']:g}"]
        return cmd + list(s.get("effort_args", []))

    def env(self, config_dir: Path, tmp_dir: Path, rep_dir: Path) -> dict:
        """A minimal environment (m5): the allowlist, the settings' pass_env, and what the harness sets."""
        names = (*ENV_ALLOWLIST, *self.settings["pass_env"])
        env = {k: os.environ[k] for k in names if k in os.environ}
        bt = self.settings["bash_timeouts_ms"]
        env.update({"CLAUDE_CONFIG_DIR": str(config_dir), "CLAUDE_CODE_TMPDIR": str(tmp_dir), "TMPDIR": str(tmp_dir),
                    "PWD": str(rep_dir), "BASH_DEFAULT_TIMEOUT_MS": str(bt["default"]),
                    "BASH_MAX_TIMEOUT_MS": str(bt["max"])})
        return env

    def check_snapshot(self) -> None:
        if snapshot_lines(self.snapshot) != self.manifest:
            raise Stop("isolation", {"reason": "the plugin snapshot changed after it was checked"})

    def isolation_problem(self, init: dict) -> str | None:
        def builtin(p):
            return isinstance(p, dict) and (p.get("path") == "builtin" or str(p.get("source", "")).endswith("@builtin"))
        plugins = [p for p in init.get("plugins") or [] if not builtin(p)]
        names = sorted({str((p.get("name") if isinstance(p, dict) else p) or "<unnamed>") for p in plugins})
        if names != [PLUGIN_NAME]:
            other = [n for n in names if n != PLUGIN_NAME]
            return (f"other plugins loaded: {', '.join(other)}" if other else f"{PLUGIN_NAME} plugin not loaded")
        ours = next(p for p in plugins if str((p.get("name") if isinstance(p, dict) else p) or "") == PLUGIN_NAME)
        if isinstance(ours, dict) and ours.get("path") and not under(Path(ours["path"]), self.snapshot):
            return f"{PLUGIN_NAME} loaded from {ours['path']}, not the snapshot"
        if init.get("claude_code_version") != self.settings["cli"]["version"]:
            return (f"CLI version {init.get('claude_code_version')} differs from the settings record's "
                    f"{self.settings['cli']['version']}")
        if init.get("model") != self.sut["model"]:
            return f"model {init.get('model')} differs from the SUT record's {self.sut['model']}"
        return None

    def collect_files(self, rep_dir: Path, side: Path, inputs: dict) -> tuple[list, bool, list, list]:
        """Every file written under the rep directory with its SHA-256 (unchanged inputs left out). A file or folder the
        harness cannot read is recorded as unreadable, never evidence and never an exception (round 7, S1)."""
        files, sut_run_json, links, unreadable = [], False, [], []

        def walk_error(err):
            try:
                unreadable.append(Path(err.filename).relative_to(rep_dir).as_posix() + "/")
            except (ValueError, TypeError):
                unreadable.append(str(err.filename))
        for dirpath, dirs, names in os.walk(rep_dir, onerror=walk_error):
            dirs.sort()
            for d in list(dirs):  # a symlinked folder is recorded, never entered
                if os.path.islink(os.path.join(dirpath, d)):
                    links.append(Path(dirpath, d).relative_to(rep_dir).as_posix() + "/")
                    dirs.remove(d)
            for n in sorted(names):
                p = Path(dirpath) / n
                rel = p.relative_to(rep_dir).as_posix()
                try:
                    if p.is_symlink() or not p.is_file():
                        links.append(rel)
                        continue
                    if rel == "run.json":  # the record's name: the SUT's own file is kept aside, never as evidence
                        os.replace(p, side / "sut-run.json")
                        sut_run_json = True
                        continue
                    h = sha256_nofollow(p)
                except OSError:
                    unreadable.append(rel)
                    continue
                if inputs.get(rel) != h:
                    files.append({"path": rel, "sha256": h})
        return files, sut_run_json, links, sorted(unreadable)

    @staticmethod
    def unstage_inputs(rep_dir: Path, inputs: dict) -> list:
        """Round 6, re-review 7 (3): unchanged input copies leave the rep directory right after the session. Each name is
        walked component by component from the rep folder's descriptor with O_NOFOLLOW, and the file is hashed and
        unlinked at its folder's descriptor: a symlinked parent is never followed (a changed input is the SUT's output
        and stays)."""
        removed = []
        for name, h in inputs.items():
            parts = name.split("/")
            if not parts or any(p in ("", ".", "..") for p in parts):
                continue
            fds = []
            try:
                fds.append(os.open(rep_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
                for comp in parts[:-1]:
                    fds.append(os.open(comp, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fds[-1]))
                st = os.stat(parts[-1], dir_fd=fds[-1], follow_symlinks=False)
                if not stat.S_ISREG(st.st_mode):
                    continue
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fds[-1])
                digest = hashlib.sha256()
                with os.fdopen(fd, "rb") as fh:
                    for block in iter(lambda: fh.read(1 << 20), b""):
                        digest.update(block)
                if digest.hexdigest() != h:
                    continue
                os.unlink(parts[-1], dir_fd=fds[-1])
                removed.append(name)
                for i in range(len(parts) - 1, 0, -1):  # empty input folders go too, each at its parent's descriptor
                    try:
                        os.rmdir(parts[i - 1], dir_fd=fds[i - 1])
                    except OSError:
                        break
            except OSError:
                continue
            finally:
                for fd in fds:
                    os.close(fd)
        return sorted(removed)

    def write_record(self, tid: str, k: int, attempt: int, record: dict) -> None:
        """run.json in the rep directory; if that fails, beside the session's stream (recorded, never lost)."""
        try:
            write_json(self.runs / tid / f"rep-{k}" / "run.json", record)
        except OSError as exc:
            alt = self.run_root / "sessions" / tid / f"rep-{k}" / f"attempt-{attempt}" / "run.json"
            write_json(alt, record)
            self.fallback_records.append({"task_id": tid, "repetition": k, "attempt": attempt, "path": str(alt),
                                          "error": exc.__class__.__name__})

    def record_flags(self, tid: str, k: int, attempt: int, flags: list) -> None:
        if not flags:
            return
        append_line_safe(self.run_root / "FLAGS.jsonl", "".join(
            json.dumps({"task_id": tid, "repetition": k, "attempt": attempt, **f}, sort_keys=True) + "\n"
            for f in flags))

    def run_attempt(self, tid: str, k: int, attempt: int) -> dict:
        self.session_started = False
        task = self.tasks[tid]
        rep_dir = self.runs / tid / f"rep-{k}"
        side = self.run_root / "sessions" / tid / f"rep-{k}" / f"attempt-{attempt}"
        cfg = self.run_root / "config" / tid / f"rep-{k}" / f"attempt-{attempt}"
        tmp_dir = side / "tmp"
        need(not rep_dir.exists(), f"{rep_dir} exists already")
        rep_dir.mkdir(parents=True)
        side.mkdir(parents=True)
        cfg.mkdir(parents=True)
        tmp_dir.mkdir(mode=0o700)
        os.chmod(tmp_dir, 0o700)
        sb_args = None
        if self.sandboxed:  # the self-test runs before any input enters the run root
            sb_args, bound = self.sandbox_args(rep_dir, cfg, tmp_dir)
            self.sandbox_selftest(sb_args, bound)
        if self.args.login_from:
            for name in LOGIN_FILES:
                src = Path(self.args.login_from) / name
                if src.is_file():
                    shutil.copyfile(src, cfg / name)
                    os.chmod(cfg / name, 0o600)
        inputs = {}
        for inp in task["inputs"]:
            dst = rep_dir / inp["name"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(input_source(Path(self.args.inputs), tid, inp["name"]), dst)
            need(sha256_file(dst) == inp["sha256"], f"task {tid}: input {inp['name']}: SHA-256 differs after the copy")
            inputs[inp["name"]] = inp["sha256"]
        prompt = build_prompt(task)
        (side / "prompt.txt").write_text(prompt, encoding="utf-8")
        rep_dirs = spellings(rep_dir)
        rep_dirs.sort(key=lambda p: p != posixpath.normpath(os.path.abspath(rep_dir)))
        sandbox_bound = None
        sb_ro = []
        if self.sandboxed:  # every bound path is legitimate inside the sandbox; the CLI's binds are read roots too
            sb_ro = list(self.settings["sandbox"]["ro_binds"])
            sandbox_bound = {"all": bound["system"] + bound["ro"] + bound["own"] + bound["masked"]
                             + spellings(self.snapshot), "masked": bound["masked"]}
        guard = Guard(rep_dir, self.snapshot, self.settings, self.run_root, Path(self.args.repo), self.home,
                      own=[cfg, tmp_dir, *sb_ro], write_ok=[tmp_dir], staging=self.staging,
                      expand_home=str(rep_dir) if self.sandboxed else None,
                      forbidden=self.forbidden_roots() if self.sandboxed else (), sandbox_bound=sandbox_bound)
        obs = Observer(guard, rep_dirs)
        obs.sandboxed = self.sandboxed
        record = {"schema": RUN_SCHEMA, "sandbox": self.sandboxed, "slurm_job_id": os.environ.get("SLURM_JOB_ID"), "task_id": tid, "repetition": k, "system_under_test": dict(self.sut),
                  "status": "not-run", "harness_sha256": self.me, "attempt": attempt,
                  "inputs": [{"name": n, "sha256": h} for n, h in sorted(inputs.items())],
                  "prompt_sha256": sha256_bytes(prompt.encode()), "config_dir": str(cfg), "tmp_dir": str(tmp_dir),
                  "stream": str((side / "stream.jsonl").relative_to(self.run_root)), "started": now()}
        stop_reason, timed_out, rc, cause, proc, stream_complete = None, False, None, None, None, False
        t0 = time.monotonic()
        stderr_f = open(side / "stderr.txt", "w", encoding="utf-8")
        try:
            try:
                cmd, env = self.command(prompt), self.env(cfg, tmp_dir, rep_dir)
                if sb_args is not None:
                    cmd = [self.settings["sandbox"]["bwrap"], *sb_args, "--", *cmd]
                    env["HOME"] = str(rep_dir)  # the session folder is HOME inside the sandbox
                proc = subprocess.Popen(cmd, cwd=rep_dir, env=env,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=stderr_f, text=True,
                                        encoding="utf-8", errors="replace", start_new_session=True)
            except OSError as exc:
                cause = f"harness cause: the CLI could not start ({exc.__class__.__name__})"
                proc = None
            if proc is not None:  # S2: recorded at launch, so that a resume can find a CLI an interrupted harness left
                write_json(side / "launch.json", {"pid": proc.pid, "pgid": proc.pid, "started": now(),
                                                  "start_time": proc_start_time(proc.pid),
                                                  "argv": proc_argv(proc.pid), "claude_bin": str(self.args.claude_bin)})
                argv_final = False
                lines: queue.Queue = queue.Queue()

                def reader():
                    for ln in proc.stdout:
                        lines.put(ln)
                    lines.put(None)
                th = threading.Thread(target=reader, daemon=True)
                th.start()
                deadline = t0 + float(self.settings["wall_time_s"])
                with open(side / "stream.jsonl", "w", encoding="utf-8") as raw:
                    while True:
                        left = deadline - time.monotonic()
                        if left <= 0:
                            timed_out = True
                            kill_group(proc.pid, proc)
                            break
                        try:
                            ln = lines.get(timeout=max(min(left, 1.0), 0.05))
                        except queue.Empty:
                            continue
                        if ln is None:
                            break
                        raw.write(ln)
                        if not argv_final:  # the leader's argv once its exec chain is done (interpreter, launcher)
                            argv_final = True
                            try:
                                launch = load_json(side / "launch.json", "launch")
                                write_json(side / "launch.json", {**launch, "argv_running": proc_argv(proc.pid)})
                            except (HarnessError, OSError):
                                pass
                        had_init = obs.init is not None
                        try:
                            obs.feed(ln)
                        except Exception as exc:  # N1: the guard could not judge an event: stop, never guess
                            stop_reason = ("guard-error", f"{exc.__class__.__name__}: {exc}")
                        if obs.events:
                            self.session_started = True
                        if stop_reason:
                            kill_group(proc.pid, proc)
                            break
                        if obs.init is not None and not had_init:
                            try:
                                problem = self.isolation_problem(obs.init)
                            except Exception as exc:  # N1: an init event the harness cannot judge stops too
                                problem = None
                                stop_reason = ("guard-error", f"isolation check: {exc.__class__.__name__}: {exc}")
                            if problem:
                                stop_reason = ("isolation", problem)
                        if obs.hits and stop_reason is None:
                            stop_reason = ("contamination", "a read or search outside the allowed roots")
                        if obs.breach and stop_reason is None:  # re-review 6, C: the sandbox failed
                            stop_reason = ("isolation", "sandbox breach: a forbidden root answered a read or a command "
                                                        "without an error")
                        if stop_reason:
                            kill_group(proc.pid, proc)
                            break
                    th.join(timeout=10)
                    stream_complete = not th.is_alive()
                    while True:  # whatever the CLI wrote before it was stopped
                        try:
                            ln = lines.get_nowait()
                        except queue.Empty:
                            break
                        if ln is None:
                            break
                        raw.write(ln)
                        try:
                            obs.feed(ln)
                        except Exception as exc:  # the session is over: recorded, and the raw stream keeps the line
                            obs.parse_errors.append(f"after the stop: {exc.__class__.__name__}: {exc}")
                try:
                    rc = proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    rc = None  # the finally below kills the group (I3), before the rep directory is walked
        finally:
            stderr_f.close()
            if proc is not None:  # I3, N1: nothing the session started outlives it, whatever happened above
                kill_group(proc.pid, proc)
                rc = proc.poll() if rc is None else rc
                try:
                    launch = load_json(side / "launch.json", "launch")
                    write_json(side / "launch.json", {**launch, "ended": now()})
                except (HarnessError, OSError):
                    pass
        wall = round(time.monotonic() - t0, 3)
        if obs.events:
            self.session_started = True
        if obs.hits and stop_reason is None:
            stop_reason = ("contamination", "a read or search outside the allowed roots")
        res = obs.result or {}
        subtype = str(res.get("subtype") or "")
        limit = "max_turns" in subtype or "budget" in subtype
        rerunnable = False
        if cause:
            status, detail, rerunnable = "not-run", cause, True
        elif stop_reason and stop_reason[0] == "isolation":
            status, detail = "not-run", f"stopped by the harness: isolation failure ({stop_reason[1]})"
        elif timed_out:
            status, detail = "timeout", f"wall time {self.settings['wall_time_s']} s reached"
        elif stop_reason and stop_reason[0] == "contamination":
            # round 6: a SUT-caused stop is the SUT's failure: completed with no valid report (scored fail), never
            # rerun; the evaluation still stops until the custodian decides (spec section 9)
            status = "completed"
            detail = f"SUT-caused stop ({obs.stop_category()}): {stop_reason[1]} (no valid report; scored fail)"
        elif stop_reason:
            status, detail = "crashed", f"stopped by the harness: {stop_reason[0]} ({stop_reason[1]})"
        elif obs.events == 0:
            # I2: rerunnable only when the stream carried no event at all (no init, no tool use, no result)
            status, detail, rerunnable = "not-run", "harness cause: the CLI started no session (no event)", True
            cause = detail
        elif obs.init is None:
            status, detail = "not-run", "the stream carried events but no init event (not rerun: the SUT may have acted)"
        elif limit:
            # reading 8: a turn or budget limit is a SUT failure, scored as fail (no valid report), never rerun
            status, detail = "completed", f"SUT limit reached: result {subtype} (no valid report)"
        elif subtype == "success" and not res.get("is_error") and rc == 0:
            status, detail = "completed", "success"
        else:
            status = "crashed"
            detail = f"result {subtype}" if res else "no result event"
            detail += f", exit code {rc}"
        try:
            files, sut_run_json, links, unreadable = self.collect_files(rep_dir, side, inputs)
        finally:  # S1: the inputs leave the run root whatever happens after the session
            removed = self.unstage_inputs(rep_dir, inputs)
        raw_report, parsed = extract_report(obs.final_text())
        sut_stop = bool(stop_reason and stop_reason[0] == "contamination")
        if limit or sut_stop:
            parsed = None
        if stop_reason and stop_reason[0] == "contamination":
            reached = True if obs.result_after_trigger else (False if stream_complete else "unknown")
        else:
            reached = "unknown"
        commands = obs.observed_commands()
        usage = res.get("usage") if isinstance(res.get("usage"), dict) else None
        record.update({
            "status": status,
            "observed": {"commands": commands, "files": files, "reads": list(obs.reads), "unreadable": unreadable,
                         "skills_loaded": list(obs.skills), "searches": obs.searches,
                         "tool_writes": obs.tool_writes, "ignored_links": links},
            "reported": normalise_report(parsed, commands, rep_dirs) if parsed is not None else None,
            "reported_raw": raw_report,
            "metrics": {"tokens": usage, "cost_usd": res.get("total_cost_usd"), "turns": res.get("num_turns"),
                        "tool_calls": obs.tool_calls, "clarifications": obs.clarifications,
                        "clarifications_note": CLARIFICATION_NOTE, "wall_time_s": wall,
                        "duration_ms": res.get("duration_ms")},
            "end": {"status": status, "detail": detail, "returncode": rc, "harness_cause": cause,
                    "rerunnable": rerunnable, "sut_wrote_run_json": sut_run_json, "parse_errors": obs.parse_errors},
            "contamination": obs.hits,
            "inputs_removed_after_session": removed,
            "stop": ({"kind": stop_reason[0], "category": obs.stop_category() if sut_stop else stop_reason[0],
                      "output_reached_model": reached, "sut_caused": sut_stop} if stop_reason else None),
            "flags": obs.flags,
            "session_id": (obs.init or {}).get("session_id"),
            "cli_version": (obs.init or {}).get("claude_code_version"),
            "model_reported": (obs.init or {}).get("model"),
            "ended": now()})
        if stop_reason:  # S4: STOP.json exists before the repetition record (no window with a stop record alone)
            write_json(self.run_root / "STOP.json", {
                "kind": stop_reason[0], "task_id": tid, "repetition": k, "attempt": attempt, "reason": stop_reason[1],
                "category": obs.stop_category() if sut_stop else stop_reason[0], "output_reached_model": reached,
                "sut_caused": sut_stop, "time": now(), "provisional": True})
        self.write_record(tid, k, attempt, record)
        self.record_flags(tid, k, attempt, obs.flags)
        if stop_reason:
            raise Stop(stop_reason[0], {"task_id": tid, "repetition": k, "attempt": attempt, "reason": stop_reason[1],
                                        "category": obs.stop_category() if sut_stop else stop_reason[0],
                                        "output_reached_model": reached, "sut_caused": sut_stop,
                                        "hits": obs.hits})
        return record

    def attempt_safely(self, tid: str, k: int, attempt: int) -> dict:
        try:
            return self.run_attempt(tid, k, attempt)
        except Stop:
            raise
        except Exception as exc:  # a harness defect or failed setup: not-run; rerunnable only before the session began
            started = self.session_started
            record = {"schema": RUN_SCHEMA, "task_id": tid, "repetition": k, "system_under_test": dict(self.sut),
                      "status": "not-run", "attempt": attempt, "harness_sha256": self.me,
                      "end": {"status": "not-run", "rerunnable": not started,
                              "detail": "harness error after the session started (not rerun: the SUT already ran)"
                              if started else "harness error before the session started",
                              "harness_cause": f"harness cause: internal error {exc.__class__.__name__}: {exc}"}}
            try:
                (self.runs / tid / f"rep-{k}").mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            record["inputs_removed_after_session"] = self.unstage_inputs(self.runs / tid / f"rep-{k}", self.task_inputs(tid))
            self.write_record(tid, k, attempt, record)
            return record

    def task_inputs(self, tid: str) -> dict:
        return {i["name"]: i["sha256"] for i in self.tasks[tid]["inputs"]}

    def rerun_marker(self, tid: str, k: int) -> Path:
        return self.run_root / "reruns" / tid / f"rep-{k}" / "RERUN.json"

    def claim_rerun(self, tid: str, k: int, cause: str, category=None) -> None:
        """S3: one rerun per repetition, claimed before the rerun session starts, refused a second time however the
        first ended."""
        marker = self.rerun_marker(tid, k)
        need(not marker.exists(), f"{tid} rep-{k} was rerun once already (at most one rerun per repetition)")
        write_json(marker, {"cause": cause, "custodian_category": category, "time": now()})

    def move_aside(self, tid: str, k: int, label: str = "attempt-1") -> str:
        src = self.runs / tid / f"rep-{k}"
        dst = self.run_root / "reruns" / tid / f"rep-{k}" / label
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, dst)
        return str(dst.relative_to(self.run_root))

    def next_attempt(self, tid: str, k: int) -> int:
        top = self.run_root / "sessions" / tid / f"rep-{k}"
        nums = [int(p.name.split("-")[1]) for p in top.glob("attempt-*") if p.name.split("-")[1].isdigit()] \
            if top.is_dir() else []
        return max(nums, default=0) + 1

    def stop(self, exc: Stop, sessions: list) -> int:
        doc = {"kind": exc.kind, **exc.detail, "time": now(), "sessions_before": len(sessions),
               "note": ("the evaluation stopped; no further session was started. A contamination is a compromise of "
                        "the holdout, not a rerunnable defect: the user decides whether the holdout is spent."
                        if exc.kind == "contamination" else
                        "the evaluation stopped: the harness's guard could not judge an event (a read or search it "
                        "cannot rule out); no further session was started." if exc.kind == "guard-error" else
                        "the evaluation stopped on an isolation failure; no further session was started.")}
        doc.setdefault("category", exc.kind)
        doc.setdefault("output_reached_model", "unknown")
        doc["custodian"] = ("decide before scoring, from this session's command log and raw stream only: A a false "
                            "positive (resume with --custodian-category A: one rerun), B an attempt whose output never "
                            "reached the model (--custodian-category B: the repetition stays a fail), C out-of-root "
                            "data reached the model (the holdout is spent); spec section 9")
        write_json(self.run_root / "STOP.json", doc)
        word = {True: "yes", False: "no"}.get(doc["output_reached_model"], "unknown")
        # the builders' view: one task-free line, never a path, a command or task text
        write_text_safe(self.run_root / "STOP-SUMMARY.txt",
                        f"stop, category: {doc['category']}, output reached model: {word}\n")
        self.finish(sessions, stopped=doc)
        msg = f"STOPPED {exc.kind}: {exc.detail.get('task_id')} rep-{exc.detail.get('repetition')}: " \
              f"{exc.detail.get('reason')} (see STOP.json)"
        print(msg)
        print(msg, file=sys.stderr)
        return EXIT_STOPPED

    def finish(self, sessions: list, stopped=None) -> None:
        flags = self.run_root / "FLAGS.jsonl"
        n_flags = len(flags.read_text(encoding="utf-8").splitlines()) if flags.exists() else 0
        write_json(self.run_root / "harness-record.json",
                   {"schema": "t13-harness-record/1", "harness_sha256": self.me, "ended": now(),
                    "sessions": sessions, "stopped": stopped, "flags": n_flags,
                    "fallback_records": self.fallback_records})

    def read_record(self, tid: str, k: int) -> dict:
        try:
            return json.loads((self.runs / tid / f"rep-{k}" / "run.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"status": "not-run", "end": {}}

    def run(self, order: list, resume: dict | None = None) -> int:
        """The planned sessions; with resume (spec section 9), finished repetitions are kept untouched, and a stopped
        repetition is rerun once only on the custodian's category A."""
        sessions, self.order, self._resume_doc, started, paused = [], order, None, 0, False
        limit = getattr(self.args, "max_sessions", None)
        try:
            orphans = self.kill_orphans()  # S2: a CLI an interrupted harness left running is stopped first
            if resume is not None:
                self.begin_resume(resume, sessions, orphans)
                started = len(sessions)  # reruns a resume started count toward --max-sessions (re-review 6)
            for tid, k in order:
                rep_dir = self.runs / tid / f"rep-{k}"
                if (rep_dir / "run.json").is_file():
                    continue  # finished before (a resume): kept untouched
                if limit and started >= limit:  # one Slurm job's batch is done; the next job resumes the same plan
                    paused = True
                    break
                started += 1
                if rep_dir.exists():  # left incomplete: its inputs out first, then kept aside (recorded)
                    self.unstage_inputs(rep_dir, self.task_inputs(tid))
                    self.move_aside(tid, k, f"incomplete-{self.next_attempt(tid, k)}")
                self.check_snapshot()
                n = self.next_attempt(tid, k)
                rec = self.attempt_safely(tid, k, n)
                sessions.append({"task_id": tid, "repetition": k, "attempt": n, "status": rec["status"],
                                 "harness_cause": rec["end"].get("harness_cause")})
                print(json.dumps({"task_id": tid, "repetition": k, "status": rec["status"]}), flush=True)
            # 3.9: one recorded rerun of a repetition that did not run for a harness cause before its session began
            for tid, k in ([] if paused else order):
                first = self.read_record(tid, k)
                cause = first.get("end", {}).get("harness_cause")
                if first.get("status") != "not-run" or not cause or not first["end"].get("rerunnable") \
                        or self.rerun_marker(tid, k).exists():
                    continue
                self.claim_rerun(tid, k, cause)
                n = self.next_attempt(tid, k)
                moved = self.move_aside(tid, k, f"attempt-{first.get('attempt', n - 1)}")
                self.check_snapshot()
                rec = self.attempt_safely(tid, k, n)
                rec["rerun"] = {"attempt": n, "first_attempt_cause": cause, "first_attempt_moved_to": moved}
                self.write_record(tid, k, n, rec)
                sessions.append({"task_id": tid, "repetition": k, "attempt": n, "status": rec["status"],
                                 "harness_cause": rec["end"].get("harness_cause"), "rerun_of": cause})
                print(json.dumps({"task_id": tid, "repetition": k, "status": rec["status"], "rerun": True}), flush=True)
            self.check_snapshot()  # m4: the snapshot is unchanged after the last session too
        except Stop as exc:
            self.end_resume(self._resume_doc, sessions, stopped=True)
            return self.stop(exc, sessions)
        self.end_resume(self._resume_doc, sessions, stopped=False)
        self.finish(sessions)
        if paused:
            print(json.dumps({"status": "paused", "sessions_this_run": started, "runs": str(self.runs)}))
            return EXIT_OK
        final = {}
        for t, k in order:
            final[(t, k)] = self.read_record(t, k).get("status", "not-run")
        not_run = sorted(f"{t} rep-{k}" for (t, k), st in final.items() if st == "not-run")
        counts = {}
        for st in final.values():
            counts[st] = counts.get(st, 0) + 1
        flags = self.run_root / "FLAGS.jsonl"
        n_flags = len(flags.read_text(encoding="utf-8").splitlines()) if flags.exists() else 0
        print(json.dumps({"status": "incomplete" if not_run else "done", "statuses": counts, "not_run": not_run,
                          "flags_for_custodian": n_flags, "runs": str(self.runs)}))
        return EXIT_INCOMPLETE if not_run else EXIT_OK

    def kill_orphans(self) -> list:
        """S2 and re-review 5 (3): a launch without an end record may have left a CLI running. Its group is killed only
        when its leader is exactly the recorded one (PID, start time and argv), or when the leader is gone while
        processes of that group remain (the session's own leftovers); never anything else. Each case is recorded."""
        out = []
        for lj in sorted(self.run_root.glob("sessions/*/rep-*/attempt-*/launch.json")):
            try:
                d = json.loads(lj.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if d.get("ended"):
                continue
            try:
                pgid = int(d.get("pgid"))
            except (TypeError, ValueError):
                continue
            entry = {"pgid": pgid, "launch": str(lj.relative_to(self.run_root)), "killed": False}
            leader_start = proc_start_time(pgid)
            argvs = [a for a in (d.get("argv"), d.get("argv_running")) if a]
            if leader_start is not None:  # a process with the leader's PID exists
                if leader_start == d.get("start_time") and proc_argv(pgid) in argvs:
                    kill_group(pgid)
                    entry.update(killed=True, why="the recorded leader (PID, start time and argv match)")
                elif proc_pgid(pgid) == pgid:
                    entry["why"] = "another process leads a group with this PGID (a reused PID): left alone"
                else:
                    members = [m for m in group_members(pgid) if m != pgid]
                    if members:
                        kill_group(pgid)
                        entry.update(killed=True, why="the leader is gone; its group's leftovers were killed")
                    else:
                        entry["why"] = "the PID was reused outside the group and the group is empty"
            else:
                members = group_members(pgid)
                if members:
                    kill_group(pgid)
                    entry.update(killed=True, why="the leader is gone; its group's leftovers were killed",
                                 members=members)
                else:
                    entry["why"] = "nothing of this session is left"
            write_json(lj, {**d, "ended": now(), "orphan_handled": entry})
            out.append(entry)
        return out

    def guard_for(self, tid: str, k: int, attempt: int):
        rep_dir = self.runs / tid / f"rep-{k}"
        side = self.run_root / "sessions" / tid / f"rep-{k}" / f"attempt-{attempt}"
        cfg = self.run_root / "config" / tid / f"rep-{k}" / f"attempt-{attempt}"
        rep_dirs = spellings(rep_dir)
        rep_dirs.sort(key=lambda p: p != posixpath.normpath(os.path.abspath(rep_dir)))
        guard = Guard(rep_dir, self.snapshot, self.settings, self.run_root, Path(self.args.repo), self.home,
                      own=[cfg, side / "tmp"], write_ok=[side / "tmp"], staging=self.staging,
                      expand_home=str(rep_dir) if self.sandboxed else None,
                      forbidden=self.forbidden_roots() if self.sandboxed else ())
        obs = Observer(guard, rep_dirs)
        obs.sandboxed = self.sandboxed
        return obs

    def scan_interrupted(self, tid: str, k: int) -> None:
        """S2: the partial stream of an interrupted repetition is scanned with the guard before any decision; a hit is a
        SUT-caused stop that needs the custodian's category."""
        attempt = self.next_attempt(tid, k) - 1
        stream = self.run_root / "sessions" / tid / f"rep-{k}" / f"attempt-{attempt}" / "stream.jsonl"
        obs = self.guard_for(tid, k, attempt)
        kind = "contamination"
        try:
            for line in stream.read_text(encoding="utf-8", errors="replace").splitlines() if stream.exists() else []:
                obs.feed(line)
        except Exception as exc:  # the guard cannot judge the partial stream: a stop, never a guess
            kind = "guard-error"
            obs.hits.append({"tool": "harness", "reason": f"guard error on the partial stream: {exc.__class__.__name__}"})
        if not obs.hits:
            return
        sut = kind == "contamination"
        category = obs.stop_category() if sut else "guard-error"
        reached = True if obs.result_after_trigger else "unknown"  # the stream was cut: never assume no output
        reason = "a read or search outside the allowed roots, in the partial stream of an interrupted repetition"
        write_json(self.run_root / "STOP.json", {"kind": kind, "task_id": tid, "repetition": k, "attempt": attempt,
                                                 "reason": reason, "category": category,
                                                 "output_reached_model": reached, "sut_caused": sut, "time": now(),
                                                 "provisional": True})
        record = {"schema": RUN_SCHEMA, "task_id": tid, "repetition": k, "system_under_test": dict(self.sut),
                  "status": "completed" if sut else "crashed", "attempt": attempt, "harness_sha256": self.me,
                  "observed": {"commands": obs.observed_commands(), "files": [], "reads": list(obs.reads),
                               "skills_loaded": list(obs.skills)},
                  "reported": None, "reported_raw": None, "contamination": obs.hits, "flags": obs.flags,
                  "stop": {"kind": kind, "category": category, "output_reached_model": reached, "sut_caused": sut},
                  "end": {"status": "completed" if sut else "crashed", "rerunnable": False,
                          "detail": f"SUT-caused stop ({category}) found in the partial stream of an interrupted "
                                    f"repetition (no valid report; scored fail)"}}
        self.write_record(tid, k, attempt, record)
        raise Stop(kind, {"task_id": tid, "repetition": k, "attempt": attempt, "reason": reason, "category": category,
                          "output_reached_model": reached, "sut_caused": sut, "hits": obs.hits})

    def begin_resume(self, resume: dict, sessions: list, orphans: list) -> dict:
        n = 1 + len(list(self.run_root.glob("resume-*.json")))
        doc = {"schema": "t13-resume/1", "resume": n, "started": now(), "harness_sha256": self.me,
               "custodian_category": resume.get("category"), "stopped": None, "sessions": [],
               "orphans_killed": orphans, "interrupted": []}
        self._resume_doc = doc
        write_json(self.run_root / f"resume-{n}.json", doc)  # S3: every resume is recorded, also one that stops
        interrupted = [(t, k) for t, k in self.order
                       if (self.runs / t / f"rep-{k}").exists() and not (self.runs / t / f"rep-{k}" / "run.json").exists()]
        doc["interrupted"] = [list(x) for x in interrupted]
        for t, k in interrupted:  # S2: their inputs leave the run root before anything else runs
            self.unstage_inputs(self.runs / t / f"rep-{k}", self.task_inputs(t))
        for t, k in interrupted:
            self.scan_interrupted(t, k)
        stop = resume.get("stop")
        if stop is not None:
            tid, k = stop.get("task_id"), stop.get("repetition")
            doc["stopped"] = [tid, k] if tid else None
            decision = {"decided_before_scoring": True, "time": now(),
                        "stop": {key: stop.get(key) for key in ("kind", "category", "output_reached_model")}}
            if tid:  # re-review 5 (4): the decision is on disk before STOP.json moves, in a harness-only folder (re-review 6)
                write_json(self.decision_path(tid, k), {"category": resume.get("category"), **decision})
            if resume.get("category") == "A" and tid:  # (5): the rerun is claimed before anything moves
                self.claim_rerun(tid, k, "custodian category A: a false positive stop", category="A")
            self.archive_stop(n)
            if resume.get("category") == "A" and tid:
                old = self.read_record(tid, k).get("attempt", 1)
                moved = self.move_aside(tid, k, f"attempt-{old}-stopped")
                self.check_snapshot()
                n_att = self.next_attempt(tid, k)
                new = self.attempt_safely(tid, k, n_att)
                new["rerun"] = {"attempt": n_att, "custodian_category": "A", "first_attempt_moved_to": moved,
                                "first_attempt_cause": "harness cause: a stop the custodian judged a false positive "
                                                       "(category A, spec section 9)"}
                self.write_record(tid, k, n_att, new)
                sessions.append({"task_id": tid, "repetition": k, "attempt": n_att, "status": new["status"],
                                 "rerun_of": "custodian category A"})
            elif resume.get("category") == "B" and tid and (self.runs / tid / f"rep-{k}" / "run.json").is_file():
                # S4: the B decision is recorded beside the repetition (written above) and in its record
                rec = self.read_record(tid, k)
                end = rec.setdefault("end", {})
                end["custodian_category"] = "B"
                end["detail"] = (str(end.get("detail") or "") + "; custodian category B: a real out-of-root attempt "
                                 "whose output never reached the model; the repetition stays a fail")
                self.write_record(tid, k, rec.get("attempt", 1), rec)
        for t, k in interrupted:  # no guard hit: one recorded rerun as a harness cause
            rep_dir = self.runs / t / f"rep-{k}"
            if (rep_dir / "run.json").exists():
                continue
            cause = "harness cause: the harness was interrupted during this repetition (no guard hit in its partial stream)"
            if self.rerun_marker(t, k).exists():
                self.write_record(t, k, self.next_attempt(t, k) - 1, {
                    "schema": RUN_SCHEMA, "task_id": t, "repetition": k, "system_under_test": dict(self.sut),
                    "status": "not-run", "harness_sha256": self.me,
                    "end": {"status": "not-run", "rerunnable": False, "harness_cause": cause,
                            "detail": "interrupted again after its one rerun"}})
                continue
            self.claim_rerun(t, k, cause)
            moved = self.move_aside(t, k, f"incomplete-{self.next_attempt(t, k) - 1}")
            self.check_snapshot()
            n_att = self.next_attempt(t, k)
            new = self.attempt_safely(t, k, n_att)
            new["rerun"] = {"attempt": n_att, "first_attempt_cause": cause, "first_attempt_moved_to": moved}
            self.write_record(t, k, n_att, new)
            sessions.append({"task_id": t, "repetition": k, "attempt": n_att, "status": new["status"],
                             "rerun_of": "interrupted"})
        write_json(self.run_root / f"resume-{n}.json", doc)
        return doc

    def decision_path(self, tid: str, k: int) -> Path:
        return self.run_root / "decisions" / str(tid) / f"rep-{k}" / "custodian.json"

    def archive_stop(self, n: int) -> None:
        (self.run_root / "stops").mkdir(exist_ok=True)
        os.replace(self.run_root / "STOP.json", self.run_root / "stops" / f"STOP-{n}.json")
        if (self.run_root / "STOP-SUMMARY.txt").exists():
            os.replace(self.run_root / "STOP-SUMMARY.txt", self.run_root / "stops" / f"STOP-SUMMARY-{n}.txt")

    def end_resume(self, doc, sessions: list, stopped: bool) -> None:
        if doc is None:
            return
        doc.update({"ended": now(), "sessions": sessions, "stopped_again": stopped})
        write_json(self.run_root / f"resume-{doc['resume']}.json", doc)


# ------------------------------------------------------------------------------------------------ main
def find_bin(name: str) -> str | None:
    if os.sep in name:
        return name if os.path.isfile(name) and os.access(name, os.X_OK) else None
    return shutil.which(name)


def cmd_run(args) -> int:
    me = sha256_file(Path(__file__))
    sut = load_sut(args.sut)
    need(sut["harness_sha256"] == me, "the SUT record's harness_sha256 differs from this harness's SHA-256 (run the "
                                      "frozen harness, or record a new SUT)")
    need(sha256_file(args.settings) == sut["settings_sha256"],
         "the settings file's SHA-256 differs from the SUT record's settings_sha256")
    settings = load_settings(args.settings)
    sandbox = settings["sandbox"]["enabled"]
    need(not (sandbox and args.no_sandbox), "the settings record requires the sandbox: --no-sandbox is refused (it is "
                                            "for tests only, never for a holdout run)")
    need(sandbox or args.no_sandbox, "the settings record has no sandbox (sandbox.enabled false): such a run needs "
                                     "--no-sandbox, for tests only; a holdout run needs sandbox.enabled true")
    if sandbox:
        bw = settings["sandbox"]["bwrap"]
        need(os.path.isfile(bw) and os.access(bw, os.X_OK), f"sandbox: bwrap not found or not executable at {bw}")
        protected = [x for r in settings.get("protected_roots", []) for x in spellings(r)]
        for p in [*settings["sandbox"]["ro_binds"], *settings.get("allowed_read_roots", [])]:
            real = os.path.realpath(p)
            need(real == posixpath.normpath(p), f"settings: the bind {p} is not canonical (it resolves to {real}); "
                                                f"write the resolved path (re-review 6)")
            need(not os.path.lexists(os.path.join(real, ".git")), f"settings: the bind {p} holds a .git clone")
            need(not any(inside(q, [real]) for q in protected), f"settings: the bind {p} holds a protected root")
    need(args.max_sessions is None or args.max_sessions >= 1, "--max-sessions must be at least 1")
    resume = args.resume is not None
    need(resume or args.run_root is not None, "give --run-root (a new evaluation) or --resume RUN_ROOT")
    need(not (resume and args.run_root is not None and Path(os.path.abspath(args.run_root)) !=
              Path(os.path.abspath(args.resume))), "--run-root and --resume name different run roots")
    run_root = Path(os.path.abspath(args.resume if resume else args.run_root))
    args.run_root = run_root
    check_run_root(run_root)
    # round 6: the tasks file and all inputs stay in a custody-side staging folder outside the run root; only the running
    # task's inputs are inside it, in its rep directory, during its session
    for path, what in ((args.tasks, "tasks file"), (args.inputs, "inputs directory")):
        need(not under(Path(path), run_root), f"the {what} must lie outside the run root (custody-side staging)")
        need(not under(run_root, Path(os.path.abspath(path)).parent if what == "tasks file" else Path(path)),
             f"the run root must not lie inside the staging folder of the {what}")
    need(not under(run_root, Path(args.repo)), "the run root lies inside the repository")
    tasks = load_tasks(Path(args.tasks))
    check_inputs(tasks, Path(args.inputs))
    runs = run_root / "runs"
    if not resume:
        need(not (runs.exists() and any(runs.iterdir())), "the run root already holds runs: a new evaluation needs a "
                                                           "fresh run root (or --resume it)")
        need(not (run_root / "plan.json").exists(), "the run root already holds a plan.json")
    need(find_bin(args.claude_bin) is not None, f"CLI {args.claude_bin} not found or not executable")
    login = bool(args.login_from and any((Path(args.login_from) / n).is_file() for n in LOGIN_FILES)) \
        or any(os.environ.get(v) for v in AUTH_ENV)
    if not args.dry_run:
        need(login, "no login for the fresh configuration directories: give --login-from a logged-in configuration "
                    "directory (its .credentials.json is copied) or set ANTHROPIC_API_KEY")
    commit, files = commit_files(Path(args.repo), sut["plugin_commit"])
    try:
        version = json.loads(files[".claude-plugin/plugin.json"][1]).get("version")
    except (KeyError, ValueError):
        raise HarnessError("snapshot: no readable .claude-plugin/plugin.json at plugin_commit") from None
    need(version == sut["plugin_version"], f"plugin_version {sut['plugin_version']} differs from the commit's {version}")
    lines, list_sha = manifest_of(files)
    if resume:
        return resume_run(args, sut, settings, tasks, me, run_root, lines)
    seed = args.seed if args.seed is not None else int.from_bytes(os.urandom(4), "big")
    order = make_order([t["task_id"] for t in tasks], args.repetitions, seed)
    h = Harness(args, sut, settings, tasks, me)
    snap_info = {"commit": commit, "files": len(lines), "file_list_sha256": list_sha, "excluded": EXCLUDED_PREFIX}
    plan = {"schema": PLAN_SCHEMA, "plan": True, "seed": seed, "repetitions": args.repetitions,
            "order": [list(x) for x in order], "tasks": len(tasks), "tasks_sha256": sha256_file(args.tasks),
            "system_under_test": sut, "settings_sha256": sut["settings_sha256"], "harness_sha256": me,
            "snapshot": snap_info, "command": h.command("<prompt>"), "login": login,
            "sandbox": {"enabled": h.sandboxed, "bwrap": settings["sandbox"]["bwrap"],
                        "ro_binds": settings["sandbox"]["ro_binds"]}}
    if args.dry_run:
        print(json.dumps(plan, sort_keys=True))
        print(json.dumps({"status": "dry-run", "sessions": len(order)}))
        return EXIT_OK
    write_snapshot(h.snapshot, files)
    h.manifest = snapshot_lines(h.snapshot)
    need(h.manifest == lines, "snapshot: the copy's file list or hashes differ from the commit")
    (run_root / "snapshot-manifest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    plan["created"] = now()
    write_json(run_root / "plan.json", plan)  # the seed and the order, before the first session
    (run_root / "plan.sha256").write_text(f"{sha256_file(run_root / 'plan.json')}  plan.json\n", encoding="utf-8")
    return h.run(order)


def resume_run(args, sut, settings, tasks, me, run_root: Path, lines: list) -> int:
    """Round 6: continue a stopped or interrupted evaluation with the same plan (spec section 9)."""
    plan_path, plan_sha = run_root / "plan.json", run_root / "plan.sha256"
    need(plan_path.is_file() and plan_sha.is_file(), "--resume: the run root holds no plan.json and plan.sha256")
    need(plan_sha.read_text(encoding="utf-8").split()[:1] == [sha256_file(plan_path)],
         "--resume: plan.json differs from its recorded SHA-256")
    plan = load_json(plan_path, "plan")
    need(plan.get("harness_sha256") == me, "--resume: the plan was made by another harness")
    need(plan.get("settings_sha256") == sut["settings_sha256"] == sha256_file(args.settings),
         "--resume: the settings differ from the plan's")
    need(plan.get("system_under_test") == sut, "--resume: the SUT record differs from the plan's")
    need(plan.get("tasks_sha256") == sha256_file(args.tasks), "--resume: the tasks file differs from the plan's")
    h = Harness(args, sut, settings, tasks, me)
    need(h.snapshot.is_dir() and snapshot_lines(h.snapshot) == lines,
         "--resume: the plugin snapshot differs from plugin_commit")
    h.manifest = lines
    order = [tuple(x) for x in plan["order"]]
    stop_path = run_root / "STOP.json"
    stop = load_json(stop_path, "STOP.json") if stop_path.exists() else None
    category = args.custodian_category
    need(category is None or stop is not None, "--resume: --custodian-category given but there is no STOP.json (the "
                                               "custodian decides on a stop only)")
    if stop is None:  # S4: a SUT-caused stop record without STOP.json (a crash between the two) is never passed over
        for rec_path in sorted(run_root.glob("runs/*/rep-*/run.json")):
            try:
                rec = json.loads(rec_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            decision = run_root / "decisions" / rec_path.parent.parent.name / rec_path.parent.name / "custodian.json"
            need(not ((rec.get("stop") or {}).get("sut_caused") and not decision.exists()),
                 f"--resume: {rec_path.parent.parent.name} {rec_path.parent.name} holds a SUT-caused stop without "
                 "STOP.json and without the custodian's decision")
    if stop is not None and category == "A" and stop.get("task_id"):
        need(not h.rerun_marker(stop["task_id"], stop.get("repetition", 1)).exists(),
             f"--resume: {stop['task_id']} rep-{stop.get('repetition')} was rerun once already (at most one rerun)")
    if stop is not None:
        need(category is not None, "--resume: a stopped evaluation resumes only with the custodian's category, decided "
                                   "before scoring (--custodian-category A or B; spec section 9)")
        need(category != "C", "--resume: category C means out-of-root data reached the model: the holdout is spent; a "
                              "new holdout comes from a new writer session (spec section 9)")
    if args.dry_run:
        print(json.dumps({"resume": True, "order": plan["order"], "stop": bool(stop), "category": category}))
        return EXIT_OK
    return h.run(order, resume={"stop": stop, "category": category})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="T13 harness (see the module docstring).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--run-root", type=Path)
    r.add_argument("--resume", type=Path, metavar="RUN_ROOT",
                   help="continue the evaluation in RUN_ROOT with its recorded plan (spec section 9)")
    r.add_argument("--custodian-category", "--rerun-stopped", dest="custodian_category", choices=("A", "B", "C"),
                   help="the custodian's decision on the stop, made before scoring: A rerun the stopped repetition "
                        "once, B keep it as a fail, C the holdout is spent (refused)")
    r.add_argument("--tasks", type=Path, required=True)
    r.add_argument("--inputs", type=Path, required=True)
    r.add_argument("--sut", type=Path, required=True, help="t13-sut.json (schema t13-sut/1)")
    r.add_argument("--settings", type=Path, required=True, help="t13-settings.json (schema t13-settings/1)")
    r.add_argument("--repo", type=Path, required=True, help="a clone holding plugin_commit (read through git only)")
    r.add_argument("--claude-bin", default="claude")
    r.add_argument("--seed", type=int)
    r.add_argument("--repetitions", type=int, default=3)
    r.add_argument("--login-from", type=Path, help="a logged-in configuration directory; only its login file is copied")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--no-sandbox", action="store_true",
                   help="tests only: run without bwrap (refused when the settings record says sandbox enabled)")
    r.add_argument("--max-sessions", type=int, help="run at most N new sessions of the plan, then pause (exit 0); a "
                                                     "later --resume continues the same plan (one Slurm job per batch)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_BAD_INPUT if exc.code else EXIT_OK
    try:
        return cmd_run(args)
    except HarnessError as exc:
        print(f"STATUS rejected: {exc}", file=sys.stderr)
        print("STATUS rejected")
        return EXIT_BAD_INPUT


if __name__ == "__main__":
    sys.exit(main())
