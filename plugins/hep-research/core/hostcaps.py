"""Host capability probes: what the operating system offers, asked in one place instead of scattered platform tests.

Probes (cached, each returns bool):
- posix_ids()       os.geteuid, os.getegid and os.getgroups exist (account identity; protected mode needs it);
- process_groups()  a POSIX host with os.killpg and os.setsid (a runner can start and stop a whole process group);
- proc_fs()         /proc/self/stat is a file (a runner can observe every process a step left behind: guarantee G2
                    of the hep-computing executor capabilities; macOS and Windows have no /proc);
- wsl()             Linux under Windows Subsystem for Linux.

require(*caps) raises UnsupportedPlatform when a capability is missing. Its report() is the JSON a script prints
before exiting with core.status.exit_code("missing-dependency") (3); callers with their own JSON shape (the protected
guard, tools with a fixed output schema) format it themselves:
    {"status": "missing-dependency", "reason": "unsupported-platform", "missing": [...], "platform": sys.platform}
plus "hint": "use WSL2" on Windows.

state_dir(*parts) is the per-user state folder: %LOCALAPPDATA%\\hep-research\\... on Windows, otherwise
$XDG_STATE_HOME/hep-research/... or ~/.local/state/hep-research/... (unchanged on Linux and macOS).

Standard library only. Tests patch the probes (tests/_platform.py needs() skips a test on a host without them).
"""
from __future__ import annotations

import functools
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path


@functools.cache
def posix_ids() -> bool:
    return all(hasattr(os, name) for name in ("geteuid", "getegid", "getgroups"))


@functools.cache
def process_groups() -> bool:
    return os.name == "posix" and hasattr(os, "killpg") and hasattr(os, "setsid")


@functools.cache
def proc_fs() -> bool:
    return os.path.isfile("/proc/self/stat")


@functools.cache
def wsl() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    try:
        with open("/proc/sys/kernel/osrelease", encoding="utf-8") as fh:
            release = fh.read().lower()
    except OSError:
        return False
    return "microsoft" in release or "wsl" in release


PROBES: dict[str, Callable[[], bool]] = {
    "posix_ids": posix_ids, "process_groups": process_groups, "proc_fs": proc_fs, "wsl": wsl,
}


def has(cap: str) -> bool:
    """Whether the host has capability cap (a key of PROBES); an unknown name is a programming error."""
    if cap not in PROBES:
        raise KeyError(f"unknown host capability {cap!r}; known: {sorted(PROBES)}")
    return bool(PROBES[cap]())


def on_windows() -> bool:
    """Native Windows (not WSL); a function so tests can patch it without changing os.name for pathlib."""
    return os.name == "nt"


class UnsupportedPlatform(RuntimeError):
    """A needed host capability is missing; report() is the missing-dependency JSON."""

    def __init__(self, missing: list[str]):
        self.missing = list(missing)
        super().__init__(f"this platform ({sys.platform}) lacks: {', '.join(self.missing)}")

    def report(self) -> dict:
        out: dict = {"status": "missing-dependency", "reason": "unsupported-platform", "missing": self.missing,
                     "platform": sys.platform}
        if on_windows():
            out["hint"] = "use WSL2"
        return out


def require(*caps: str) -> None:
    """Raise UnsupportedPlatform naming every capability in caps the host lacks; return when it has them all."""
    missing = [cap for cap in caps if not has(cap)]
    if missing:
        raise UnsupportedPlatform(missing)


def state_dir(*parts: str, environ: Mapping[str, str] | None = None) -> Path:
    """The per-user state folder for hep-research (module docstring), with parts appended; nothing is created."""
    env = os.environ if environ is None else environ
    if on_windows():
        base = Path(env.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(env.get("XDG_STATE_HOME") or Path(env.get("HOME") or Path.home()) / ".local" / "state")
    return base.joinpath("hep-research", *parts)
