"""Interpreter guard for skill scripts: stop an unsupported Python before any work, or switch to a safe one once.

Skill scripts are started as `python3 <script>`, so nothing enforces requires-python (pyproject.toml) at run time; on
macOS `python3` may be the Xcode command-line tools' 3.9. Every skill script (tools/skill_scripts.json) calls guard()
from a fixed block before its other imports (tools/insert_interpreter_guard.py, tests/tools/test_python_compat.py).

guard():
1. On a Python older than MIN_PYTHON:
   - when HEP_RESEARCH_GUARD_REEXEC is set (any value) the switch already happened once and did not help: one stderr
     line and exit 2 (one switch, never a loop);
   - when HEP_RESEARCH_PYTHON is an absolute path to an existing executable file, `--protected` is not among the
     arguments, the account is not root, and neither the target nor its folder is writable by the running account:
     set the marker and replace the process with that interpreter on the same arguments (os.execv; the path is made
     absolute, never resolved, so a virtual environment's interpreter keeps its environment). No PATH lookup and no
     relative value: an interpreter that runs code outside the agent sandbox must live outside agent-writable paths
     (README "Setup requirements");
   - otherwise one stderr line naming HEP_RESEARCH_PYTHON and find_python.py, and exit 2.
2. On Windows without UTF-8 mode (PYTHONUTF8=1): one stderr line and exit 2 (text I/O would use the ANSI code page).
3. Remove the marker from the environment, so programs this script starts get their own single switch.
Nothing is ever printed on stdout.

child_flags() is the interpreter options a parent passes to a child Python that runs a hep-research script: ["-X",
"utf8"] on Windows, where rule 2 needs UTF-8 mode and isolated mode (-I) ignores PYTHONUTF8; [] elsewhere.

This file is standard library only, imports nothing from the plugin and must parse and run on Python 3.9
(tests/tools/test_python_compat.py FILES). Remove the guard when the default `python3` on supported macOS releases is
at least MIN_PYTHON (docs/architecture.md section 6).
"""
from __future__ import annotations

import os
import sys

MIN_PYTHON = (3, 13)  # pyproject.toml requires-python; tests/core/test_interpreter_guard.py keeps the two equal
TARGET_VARIABLE = "HEP_RESEARCH_PYTHON"
MARKER_VARIABLE = "HEP_RESEARCH_GUARD_REEXEC"
EXIT_BAD_INPUT = 2  # core/status.py EXIT_BAD_INPUT (not imported: this file runs before the plugin is importable)


def _running() -> str:
    return f"{sys.version_info[0]}.{sys.version_info[1]}"


def _need() -> str:
    return f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}"


def _stop(message: str) -> None:
    print(f"hep-research: {message}", file=sys.stderr)
    sys.stderr.flush()
    raise SystemExit(EXIT_BAD_INPUT)


def _is_root() -> bool:
    geteuid = getattr(os, "geteuid", None)
    return geteuid is not None and geteuid() == 0


def switch_target(environ=None, argv=None) -> str | None:
    """The interpreter to switch to, or None when no safe one is named (see the module docstring for the rules)."""
    environ = os.environ if environ is None else environ
    argv = sys.argv if argv is None else argv
    value = environ.get(TARGET_VARIABLE, "")
    if not value or not os.path.isabs(value):
        return None
    if "--protected" in argv[1:] or _is_root():
        return None
    target = os.path.abspath(value)
    if not os.path.isfile(target) or not os.access(target, os.X_OK):
        return None
    if os.access(target, os.W_OK) or os.access(os.path.dirname(target), os.W_OK):
        return None
    return target


def child_flags() -> list:
    """["-X", "utf8"] on Windows, else [] (module docstring): put it right after sys.executable."""
    return ["-X", "utf8"] if os.name == "nt" else []


def guard() -> None:
    """Return when this interpreter may run the calling script; otherwise switch once or exit 2 (module docstring)."""
    if tuple(sys.version_info[:2]) < MIN_PYTHON:  # noqa: UP036  (the check runs on old interpreters)
        if MARKER_VARIABLE in os.environ:
            _stop(f"Python {_need()} or newer is required (running {_running()}); "
                  f"{TARGET_VARIABLE} did not provide one.")
        target = switch_target()
        if target is not None:
            os.environ[MARKER_VARIABLE] = "1"
            sys.stdout.flush()
            sys.stderr.flush()
            os.execv(target, [target, *sys.argv])
        _stop(f"Python {_need()} or newer is required (running {_running()}). Set {TARGET_VARIABLE} to the absolute "
              f"path of a Python {_need()}+ interpreter outside writable folders; find_python.py in the hep-computing "
              f"skill's scripts folder can find one.")
    if os.name == "nt" and sys.flags.utf8_mode == 0:
        _stop("set PYTHONUTF8=1 (UTF-8 mode) to run hep-research scripts on Windows.")
    os.environ.pop(MARKER_VARIABLE, None)
