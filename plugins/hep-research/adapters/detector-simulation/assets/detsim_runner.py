"""Runner of the detector-simulation shared layer: launch one backend under the G0 runner profile (TASK.md 10.2 step 10).

A module of detsim.py (docs/dev/detector-simulation/TASK.md 6, 8.2, 10.2, 10.5). launch() starts the backend
executable named by the ExecutionSpec directly (never through a shell), with exactly the plan's environment variables
(plus HEP_RUN_WORKFLOW_ATTEMPT when present, outside the hash scope), in a new session and process group, from this
single-threaded controller. On Linux the child sets PR_SET_PDEATHSIG(SIGKILL) and checks getppid() before exec.

The logical roots ENV_ROOT, INPUT_ROOT and ATTEMPT_ROOT in argv and variable values are bound to real folders here
(prefix substitution, not shell expansion). stdout and stderr go to ATTEMPT_ROOT/logs/.

Termination rule (never signal a process this command did not start): the controller sends SIGTERM, then SIGKILL
after a grace period, to its own child's process group, and only while the child has not been reaped (poll() returned
None just before). After the child is reaped the group is never signalled again, so a reused pid can never be hit.
Descendants that outlive the child are reported (descendants_killed soft), never hunted. Causes: timeout (budget),
output above the budget (soft: checked every POLL_S), SIGINT / SIGTERM to the controller (cancelled).
"""
from __future__ import annotations

import sys

if __spec__ is None:  # run as a file (tests/skills/test_cli_robustness.py): a module of detsim.py, not a command
    print(__doc__.splitlines()[0] + "\nA module of detsim.py, not a command: python3 detsim.py --help")
    sys.exit(0 if sys.argv[1:] in ([], ["--help"], ["-h"]) else 2)

import os  # noqa: E402
import resource  # noqa: E402
import signal  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import detsim_platform as platform_calls  # noqa: E402

ROOTS = ("ENV_ROOT", "INPUT_ROOT", "ATTEMPT_ROOT")
WORKFLOW_TOKEN = "HEP_RUN_WORKFLOW_ATTEMPT"
POLL_S = 0.05
GRACE_S = 2.0
KILL = os.killpg  # the only signalling call of this module; tests wrap it to record calls


def bind(text: str, roots: dict) -> str:
    """Replace a leading logical root (ENV_ROOT, INPUT_ROOT, ATTEMPT_ROOT) by its real folder."""
    for name in ROOTS:
        if text == name:
            return str(roots[name])
        if text.startswith(name + "/"):
            return str(Path(roots[name]).joinpath(*text[len(name) + 1:].split("/")))
    return text


def _tree_bytes(folder: Path) -> int:
    total = 0
    for base, _dirs, names in os.walk(folder):
        for name in names:
            try:
                total += os.lstat(os.path.join(base, name)).st_size
            except OSError:
                pass
    return total


class _Interrupts:
    """SIGINT and SIGTERM to the controller are recorded instead of killing it (main thread only)."""

    def __init__(self):
        self.received: list[str] = []
        self._old = {}

    def __enter__(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                self._old[sig] = signal.signal(sig, self._note)
            except ValueError:  # not the main thread: interruptions then stop the controller as usual
                pass
        return self

    def _note(self, signum, _frame):
        self.received.append(signal.Signals(signum).name)

    def __exit__(self, *exc):
        for sig, old in self._old.items():
            signal.signal(sig, old)
        return False


def launch(spec: dict, roots: dict, max_output_bytes: int, profile_id: str, on_start=None) -> dict:
    """Run spec in roots; return the execution facts (never raises for a backend failure).

    roots: {"ENV_ROOT", "INPUT_ROOT", "ATTEMPT_ROOT"} real folders. on_start(pid, pgid) is called right after the
    launch (the lock record's diagnostics). The result: native_exit_code, signal, end (exited, signalled, timeout,
    output-exceeded, cancelled, launch-failed), duration_s, peak_rss_kib, interruptions, terminated_by_controller,
    achieved guarantee facts and the launch error when the executable could not be started."""
    attempt = Path(roots["ATTEMPT_ROOT"])
    logs = attempt / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    argv = [bind(a, roots) for a in spec["argv"]]
    env = {name: bind(value, roots) for name, value in spec.get("environment", {}).items()}
    if WORKFLOW_TOKEN in os.environ:
        env[WORKFLOW_TOKEN] = os.environ[WORKFLOW_TOKEN]
    timeout = float(spec["timeout_s"])
    preexec = platform_calls.set_parent_death_signal if platform_calls.platform_key() == "linux" else None
    facts = {"argv_bound": argv, "end": None, "native_exit_code": None, "signal": None, "duration_s": None,
             "peak_rss_kib": None, "interruptions": [], "terminated_by_controller": None, "pid": None, "pgid": None,
             "launch_error": None}
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    start = time.monotonic()
    with _Interrupts() as interrupts, open(logs / "stdout.txt", "wb") as out, open(logs / "stderr.txt", "wb") as err:
        try:
            proc = subprocess.Popen(argv, cwd=attempt, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                    start_new_session=True, close_fds=True, preexec_fn=preexec)
        except OSError as exc:
            facts.update(end="launch-failed", launch_error=f"{type(exc).__name__}: {exc.strerror or exc}",
                         duration_s=round(time.monotonic() - start, 6))
            return facts
        facts["pid"] = facts["pgid"] = proc.pid  # start_new_session: the child leads its own session and group
        if on_start is not None:
            on_start(proc.pid, proc.pid)
        cause, sent_kill, term_at = None, False, None
        while True:
            code = proc.poll()  # reaps the child once it has exited; afterwards the group is never signalled
            if code is not None:
                break
            now = time.monotonic()
            if cause is None:
                if interrupts.received:
                    cause = "cancelled"
                elif now - start > timeout:
                    cause = "timeout"
                elif _tree_bytes(attempt) > max_output_bytes:
                    cause = "output-exceeded"
                if cause is not None:
                    term_at = now
                    _signal_own_group(proc, signal.SIGTERM)
            elif not sent_kill and now - term_at > GRACE_S:
                sent_kill = True
                _signal_own_group(proc, signal.SIGKILL)
            time.sleep(POLL_S)
    facts["duration_s"] = round(time.monotonic() - start, 6)
    facts["interruptions"] = interrupts.received
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    divisor = 1024 if platform_calls.platform_key() == "darwin" else 1  # bytes on macOS, KiB on Linux
    facts["peak_rss_kib"] = max(usage_after, usage_before) // divisor
    if code < 0:
        facts["signal"] = signal.Signals(-code).name
    else:
        facts["native_exit_code"] = code
    facts["terminated_by_controller"] = cause
    facts["end"] = cause or ("signalled" if code < 0 else "exited")
    return facts


def _signal_own_group(proc: subprocess.Popen, sig) -> None:
    """Signal the child's own process group; only called while proc is unreaped (its pid cannot be reused)."""
    if proc.returncode is not None:
        return
    try:
        KILL(proc.pid, sig)
    except ProcessLookupError:
        pass
