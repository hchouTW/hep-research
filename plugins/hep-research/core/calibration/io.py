"""Input and output of the calib_*.py scripts (Part B section 14 conventions): JSON in, one JSON object out with a
`status` key, exit codes 0 normal, 1 negative decision, 2 input error, 3 incomplete; the ledger written atomically
under an exclusive lock (the single writer of section 9.5). Standard library only."""
from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

from core.canonical import load_json_strict

EXIT = {"ok": 0, "accepted": 0, "passed": 0, "written": 0, "failed": 1, "refused": 1, "rejected": 2,
        "incomplete": 3}


class InputError(ValueError):
    """Input a script cannot use: exit 2, status rejected."""


def load(path: str):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc.strerror or exc}") from None
    try:
        return load_json_strict(text)
    except ValueError as exc:
        raise InputError(f"{path} is not valid JSON: {exc}") from None


def emit(out: dict) -> int:
    print(json.dumps(out, indent=1, sort_keys=False, default=sorted))
    return EXIT.get(out.get("status"), 2)


def run(fn) -> int:
    """Call fn() -> dict and print it; an InputError becomes status rejected (exit 2)."""
    try:
        return emit(fn())
    except InputError as exc:
        return emit({"status": "rejected", "error": str(exc)})


def write_json(path: str, value) -> None:
    """Write to `path` atomically (temporary file in the same folder, then rename); the folder must exist."""
    p = Path(path)
    if not p.parent.is_dir():
        raise InputError(f"output folder {p.parent} does not exist")
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=f".{p.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, p)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


@contextlib.contextmanager
def locked(path: str):
    """An exclusive lock file next to the ledger: a second writer is refused, never interleaved."""
    lock = Path(f"{path}.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise InputError(f"{lock} exists: another calib_data.py is writing this ledger (single writer)") from None
    except OSError as exc:
        raise InputError(f"cannot lock {path}: {exc.strerror or exc}") from None
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        with contextlib.suppress(OSError):
            lock.unlink()


def guard_stdout_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        with contextlib.suppress(Exception):
            sys.stdout.reconfigure(encoding="utf-8")
