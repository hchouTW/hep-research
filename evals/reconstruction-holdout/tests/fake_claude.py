#!/usr/bin/env python3
"""A stand-in for `claude -p ... --output-format stream-json --verbose` for the T13 harness tests: no model calls.

It acts out a scripted session in its working directory (the rep directory): it writes the files a scripted command or
Write would write, and emits the stream the real CLI emits (a system/init event, assistant tool_use blocks, user
tool_result blocks with a tool_use_result object, a non-JSON progress line, the final assistant text and a result event
with usage and cost).

Stream shapes. CONFIRMED means seen in a real Claude Code stream or transcript; GUESS means a shape the harness accepts
that must be confirmed at the shakedown with the real CLI (t13 shakedown checklist):
  CONFIRMED  system/init with session_id, model, claude_code_version, plugins, tools; assistant tool_use; user
             tool_result with is_error; result with subtype, num_turns, total_cost_usd, usage, result.
  CONFIRMED  a failed Bash result as text starting "Exit code N" with is_error true.
  CONFIRMED  explicit background start text "Command running in background with ID: <id>"; automatic background text
             "Command ... was moved to the background (ID: <id>) ..."; a later <task-notification> text block with
             <task-id>, <status> and "(exit code N)" in its summary (the shape this harness's own sessions receive).
  GUESS      tool_use_result.backgroundTaskId on a background start; tool_use_result.returnCodeInterpretation on a
             non-error non-zero exit (grep 1); tool_use_result.interrupted.
  GUESS      "Exit code N" trailing after other text (trailing=true here).
  GUESS      a system event {subtype: task_notification, task_id, status, exit_code} as a completion record.
  GUESS      a BashOutput tool result with <status> and <exit_code> tags as a completion record.
  GUESS      CLI temporary files under CLAUDE_CODE_TMPDIR ("{tmp}" here) that the session reads back.
  GUESS      result subtypes error_max_turns and error_max_budget_usd for the turn and budget limits.
  GUESS      a failed background notification summary ending "... failed with exit code N"; a still-running poll
             (<status>running</status>) whose <stdout> holds tag-like text; a system task event with status killed.
  ADVERSARIAL (not CLI shapes; inputs the harness must not trust): foreground output that looks like a background start
             ("output"), a <task-notification> inside a subagent user event ("_event" with parent_tool_use_id), a
             stream with tool use but no init event (mode events_no_init), a plugin entry without a name
             (FAKE_NAMELESS_PLUGIN), a NUL byte in a path.

Environment:
  FAKE_SCRIPT   JSON file {"<prompt substring>": scenario}; the first key found in the prompt selects the scenario.
                A scenario is {"actions": [...], "final": "<text>", "mode": "ok"} or {"attempts": [scenario, ...]}
                (the n-th call for that key acts out attempts[n], the last one repeating).
                action: {"tool": "Bash", "command": str, "exit_code": int, "writes": {rel: text},
                         "background": "explicit" | "auto", "task_field": bool (backgroundTaskId), "bg_id": str,
                         "completion": {"shape": "notification" | "system" | "bashoutput", "exit_code": int | null,
                                        "status": "completed"},
                         "rci": str (returnCodeInterpretation), "trailing": bool, "no_result": bool,
                         "output": str (the text of a foreground result with exit 0),
                         "spawn_late": rel (a left-over process writes it 2 s later),
                         "tamper_snapshot": bool (adds a file to the --plugin-dir copy),
                         "pause_after_use": seconds (sleep between the tool_use and its result),
                         "same_write": bool (the tool_use and its result in one write),
                         "chmod000": rel (make that written file unreadable, mode 000),
                         "symlinks": {name: target} (symlinks planted in the working directory),
                         "error": bool (the tool result says is_error),
                         "sh" / "shbg": str (run that shell command in the working directory, in the foreground or
                                            detached)}
                        Read actions take "pause_after_use" and "same_write" too.
                        {"tool": "Read" | "Grep" | "Glob", "file_path"/"path"/"pattern": str}
                        {"tool": "Write", "file_path": str, "content": str}
                        {"tool": "Skill", "skill": str}   {"tool": "AskUserQuestion"}
                        {"tool": "_event", "event": {...}}  (emitted as it is, no tool use)
                completion also takes "stdout" (the poll's <stdout> text).
                "burst": true writes the whole stream in one write at the end.
                mode: ok | crash (exit 1 after the actions, no result) | hang (sleep after the actions) |
                events_no_init (a tool use without an init event, then exit 1) | no_init (exit 1 with
                nothing on stdout: the CLI never started a session) | error_result (a result event of subtype
                error_max_turns) | error_budget (subtype error_max_budget_usd).
                "{cwd}", "{cfg}", "{tmp}", "{home}" in any string: the working directory, CLAUDE_CONFIG_DIR,
                CLAUDE_CODE_TMPDIR, HOME.
  FAKE_LOG      every call appends one JSON line: argv, cwd, the files in cwd at start, CLAUDE_CONFIG_DIR and its files,
                the CLAUDE* variable names, every variable name, TMPDIR and CLAUDE_CODE_TMPDIR with their modes, the
                BASH_* timeouts, and FAKE_CHECK_FILE's existence.
  FAKE_VERSION  claude_code_version reported (default 9.9.9); FAKE_EXTRA_PLUGINS comma-separated extra plugin names.
  Inside the sandbox (round 8) the test's files are not visible: FAKE_SCRIPT_JSON carries the scenario itself, and when
  FAKE_LOG is unset or not writable the log line is emitted as a {"type": "system", "subtype": "fake_log"} event in the
  stream. FAKE_PROBE lists paths (colon-separated) whose existence the log reports; the log also records HOME.
"""
import json
import os
import subprocess
import sys
import time
import uuid

argv = sys.argv[1:]
prompt = argv[argv.index("-p") + 1]
cwd = os.getcwd()
cfg = os.environ.get("CLAUDE_CONFIG_DIR")
tmp = os.environ.get("CLAUDE_CODE_TMPDIR")


def files_under(top):
    out = []
    for dirpath, _dirs, names in os.walk(top):
        for n in names:
            out.append(os.path.relpath(os.path.join(dirpath, n), top))
    return sorted(out)


def runroot_files():
    """Every file under the run root (two levels above runs/<task>/rep-k) outside this rep directory, by name."""
    top = os.path.dirname(os.path.dirname(os.path.dirname(cwd)))
    out = []
    for dirpath, dirs, names in os.walk(top):
        if os.path.abspath(dirpath).startswith(os.path.abspath(cwd)):
            continue
        out += [os.path.relpath(os.path.join(dirpath, n), top) for n in names]
    return sorted(out)


def mode_of(p):
    return oct(os.stat(p).st_mode & 0o777) if p and os.path.isdir(p) else None


check = os.environ.get("FAKE_CHECK_FILE")
LOG_RECORD = None


def write_log(rec):
    global LOG_RECORD
    try:
        with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except (KeyError, OSError):
        LOG_RECORD = rec  # emitted into the stream after the init event


if True:
    write_log({"pid": os.getpid(), "argv": argv, "cwd": cwd, "home": os.environ.get("HOME"),
                         "probe": {p: os.path.exists(p) for p in os.environ.get("FAKE_PROBE", "").split(":") if p}, "cwd_files": files_under(cwd), "config_dir": cfg,
                         "config_files": files_under(cfg) if cfg and os.path.isdir(cfg) else None,
                         "env_claude": sorted(k for k in os.environ if k.startswith("CLAUDE")),
                         "env_keys": sorted(os.environ),
                         "tmpdir": os.environ.get("TMPDIR"), "tmpdir_mode": mode_of(os.environ.get("TMPDIR")),
                         "code_tmpdir": tmp, "code_tmpdir_mode": mode_of(tmp),
                         "bash_timeouts": [os.environ.get("BASH_DEFAULT_TIMEOUT_MS"),
                                           os.environ.get("BASH_MAX_TIMEOUT_MS")],
                         "check_file_exists": bool(check) and os.path.exists(check),
                         "runroot_files": runroot_files()})

if os.environ.get("FAKE_SCRIPT_JSON"):
    script = json.loads(os.environ["FAKE_SCRIPT_JSON"])
else:
    with open(os.environ["FAKE_SCRIPT"], encoding="utf-8") as fh:
        script = json.load(fh)
key, scen = None, {"actions": [], "final": "No scenario."}
for k, v in script.items():
    if k in prompt:
        key, scen = k, v
        break
if "attempts" in scen:
    counts_path = os.environ["FAKE_LOG"] + ".counts.json"
    counts = json.load(open(counts_path)) if os.path.exists(counts_path) else {}
    n = counts.get(key, 0)
    counts[key] = n + 1
    with open(counts_path, "w") as fh:
        json.dump(counts, fh)
    scen = scen["attempts"][min(n, len(scen["attempts"]) - 1)]


def sub(x):
    if isinstance(x, str):
        return (x.replace("{cwd}", cwd).replace("{cfg}", cfg or "").replace("{tmp}", tmp or "")
                .replace("{home}", os.path.expanduser("~")))
    if isinstance(x, list):
        return [sub(v) for v in x]
    if isinstance(x, dict):
        return {k: sub(v) for k, v in x.items()}
    return x


scen = sub(scen)
mode = scen.get("mode", "ok")
REAL_STDOUT = sys.stdout
if scen.get("burst"):  # the whole stream in one write at the end (it is all in the pipe when the harness reads it)
    import io
    sys.stdout = io.StringIO()
if mode == "no_init":
    print("Error: could not reach the service", file=sys.stderr)
    sys.exit(1)
if mode == "events_no_init":
    print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "toolu_x", "name": "Bash",
                                                                   "input": {"command": "true"}}]}}), flush=True)
    sys.exit(1)

session = str(uuid.uuid4())


def emit(ev):
    ev.setdefault("session_id", session)
    print(json.dumps(ev), flush=True)


plugin_dir = argv[argv.index("--plugin-dir") + 1] if "--plugin-dir" in argv else None
plugins = [{"name": "hep-research", "path": plugin_dir}] if plugin_dir else []
plugins += [{"name": p, "path": "/elsewhere/" + p} for p in os.environ.get("FAKE_EXTRA_PLUGINS", "").split(",") if p]
if os.environ.get("FAKE_NAMELESS_PLUGIN"):
    plugins.append({"path": "/elsewhere/nameless"})
plugins.append({"name": "cc-plugin-telemetry", "path": "builtin", "source": "cc-plugin-telemetry@builtin"})
emit({"type": "system", "subtype": "init", "cwd": cwd, "model": argv[argv.index("--model") + 1],
      "claude_code_version": os.environ.get("FAKE_VERSION", "9.9.9"), "plugins": plugins,
      "tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"], "mcp_servers": [],
      "permissionMode": "default", "apiKeySource": "none"})
print("not json: progress line", flush=True)
if LOG_RECORD is not None:
    emit({"type": "system", "subtype": "fake_log", "log": LOG_RECORD})

usage = {"input_tokens": 120, "output_tokens": 30, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
counter = [0]


HELD = []  # a tool_use line held back to be written together with its result (same_write)


def tool_use(name, inp, hold=False):
    counter[0] += 1
    tid = f"toolu_fake_{counter[0]:03d}"
    ev = {"type": "assistant", "parent_tool_use_id": None, "session_id": session,
          "message": {"id": f"msg_{counter[0]}", "role": "assistant", "model": "fake",
                      "content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}], "usage": usage}}
    if hold:
        HELD.append(json.dumps(ev))
    else:
        emit(ev)
    return tid


def tool_result(tid, text, is_error=False, extra=None):
    ev = {"type": "user", "parent_tool_use_id": None, "session_id": session,
          "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": text,
                                                    "is_error": is_error}]}}
    if extra is not None:
        ev["tool_use_result"] = extra
    if HELD:
        print(HELD.pop() + "\n" + json.dumps(ev), flush=True)  # one write: the result is in the pipe with its call
    else:
        emit(ev)


def completion(bg_id, comp, command):
    shape, code, status = comp.get("shape"), comp.get("exit_code"), comp.get("status", "completed")
    if shape == "notification":
        if code is None:
            tail = ""
        elif status == "completed":
            tail = f" (exit code {code})"
        else:
            tail = f" with exit code {code}"
        text = (f"<task-notification>\n<task-id>{bg_id}</task-id>\n<status>{status}</status>\n<summary>Background "
                f"command \"{command}\" {status}{tail}</summary>\n</task-notification>")
        emit({"type": "user", "parent_tool_use_id": None,
              "message": {"role": "user", "content": [{"type": "text", "text": text}]}})
    elif shape == "system":
        emit({"type": "system", "subtype": "task_notification", "task_id": bg_id, "status": status, "exit_code": code})
    elif shape == "bashoutput":
        tid = tool_use("BashOutput", {"bash_id": bg_id})
        tags = f"<status>{status}</status>\n" + (f"<exit_code>{code}</exit_code>\n" if code is not None else "")
        tool_result(tid, tags + f"<stdout>{comp.get('stdout', 'done')}</stdout>")


SCRIPT_KEYS = ("chmod000", "symlinks", "error", "tool", "exit_code", "writes", "no_result", "background", "task_field", "completion", "rci", "trailing",
               "spawn_late", "sh", "shbg", "tamper_snapshot", "output", "bg_id", "pause_after_use",
               "same_write")
for act in scen.get("actions", []):
    tool = act["tool"]
    if tool == "_event":
        emit(act["event"])
        continue
    inp = {k: v for k, v in act.items() if k not in SCRIPT_KEYS}
    if tool == "AskUserQuestion":
        inp = {"questions": [{"question": "Which one?", "options": []}]}
    if act.get("background") == "explicit":
        inp["run_in_background"] = True
    tid = tool_use(tool, inp, hold=bool(act.get("same_write")))
    if act.get("pause_after_use"):
        time.sleep(float(act["pause_after_use"]))
    result, is_error, extra = "ok", False, None
    for rel, text in (act.get("writes") or {}).items():
        path = os.path.join(cwd, rel)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    for name, target in (act.get("symlinks") or {}).items():  # the SUT plants symlinks where the harness writes
        os.symlink(target, os.path.join(cwd, name))
    if act.get("chmod000"):  # the SUT leaves a file nobody can read
        os.chmod(os.path.join(cwd, act["chmod000"]), 0)
    if act.get("sh"):  # a real shell command run in the session folder (the reviewer's hook, round 10)
        subprocess.run(["/bin/sh", "-c", act["sh"]], cwd=cwd)
    if act.get("shbg"):
        subprocess.Popen(["/bin/sh", "-c", act["shbg"]], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    if act.get("spawn_late"):
        target = os.path.join(cwd, act["spawn_late"])
        subprocess.Popen([sys.executable, "-c", f"import time; time.sleep(2); open({target!r}, 'w').write('late')"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    if act.get("tamper_snapshot") and plugin_dir:
        os.chmod(plugin_dir, 0o755)
        with open(os.path.join(plugin_dir, "planted.md"), "w") as fh:
            fh.write("planted\n")
    if tool == "Write":
        os.makedirs(os.path.dirname(act["file_path"]) or ".", exist_ok=True)
        with open(act["file_path"], "w", encoding="utf-8") as fh:
            fh.write(act.get("content", ""))
        result = f"File created successfully at: {act['file_path']}"
    if act.get("no_result"):
        continue
    if tool == "Bash":
        code = act.get("exit_code", 0)
        bg = act.get("background")
        bg_id = act.get("bg_id") or f"bash_{counter[0]}"
        if bg == "explicit":
            result = f"Command running in background with ID: {bg_id}"
        elif bg == "auto":
            result = (f"Command did not complete within its 120s timeout and was moved to the background (ID: {bg_id})."
                      f" Output is being written to: {tmp}/tasks/{bg_id}.output")
        elif code and act.get("rci"):
            extra = {"stdout": "", "stderr": "", "interrupted": False, "returnCodeInterpretation": act["rci"]}
            result = act["rci"]
        elif code and act.get("trailing"):
            result, is_error = f"warning: something odd\nsomething failed\nExit code {code}", True
        elif code:
            result, is_error = f"Exit code {code}\nsomething failed", True
        else:
            result = act.get("output", "done")
        if bg and act.get("task_field"):
            extra = {"stdout": "", "stderr": "", "interrupted": False, "backgroundTaskId": bg_id}
        tool_result(tid, result, is_error, extra)
        if bg and act.get("completion"):
            completion(bg_id, act["completion"], act["command"])
        continue
    tool_result(tid, result, bool(act.get("error")) or is_error, extra)

if mode == "hang":
    time.sleep(60)
if mode == "crash":
    print("Segmentation fault (fake)", file=sys.stderr)
    sys.exit(1)
final = scen.get("final", "Done.")
emit({"type": "assistant", "parent_tool_use_id": None,
      "message": {"id": "msg_final", "role": "assistant", "model": "fake", "content": [{"type": "text", "text": final}],
                  "usage": usage}})
n_actions = len(scen.get("actions", []))
if mode in ("error_result", "error_budget"):
    emit({"type": "result", "subtype": "error_max_turns" if mode == "error_result" else "error_max_budget_usd",
          "is_error": True, "num_turns": n_actions + 1, "duration_ms": 1500, "total_cost_usd": 0.02, "usage": usage})
    sys.exit(1)
emit({"type": "result", "subtype": "success", "is_error": False, "num_turns": n_actions + 1, "duration_ms": 2345,
      "duration_api_ms": 2000, "total_cost_usd": 0.0123, "result": final,
      "usage": {"input_tokens": 1000, "output_tokens": 200, "cache_read_input_tokens": 300,
                "cache_creation_input_tokens": 40}})
if sys.stdout is not REAL_STDOUT:
    REAL_STDOUT.write(sys.stdout.getvalue())
    REAL_STDOUT.flush()
