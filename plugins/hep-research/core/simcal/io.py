"""Input and output of the calib_*.py scripts (Part B section 14 conventions): JSON in, one JSON object out with a
`status` key, exit codes 0 normal, 1 negative decision, 2 input error, 3 incomplete; the ledger written atomically
under an exclusive lock (the single writer of section 9.5). Standard library only."""
from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
from typing import Any
from pathlib import Path

from core.canonical import load_json_strict

EXIT = {"ok": 0, "accepted": 0, "passed": 0, "written": 0, "not-applicable": 0, "synthetic": 0,
        "no-testable-direction": 0,                     # a decision: no direction to test (section 9.4)
        "failed": 1, "refused": 1, "insufficient": 1,   # insufficient power is a negative verdict (section 9.4)
        "rejected": 2,
        "incomplete": 3, "not-decided": 3, "pending": 3, "gap": 3}   # gap: G8 without a usable truth sample (D6, A12)  # no decision reached (e.g. G9 after P8 failed, G8 not run)


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



def load_object(path: str, required=()) -> dict:
    """`load` for an input that must be a JSON object with the `required` keys: anything else is bad input (exit 2),
    never a traceback."""
    x = load(path)
    if not isinstance(x, dict):
        raise InputError(f"{path}: expected a JSON object, got {type(x).__name__}")
    missing = [k for k in required if k not in x]
    if missing:
        raise InputError(f"{path}: missing key(s) {', '.join(missing)}")
    return x


def emit(out: dict) -> int:
    print(json.dumps(out, indent=1, sort_keys=False, default=sorted))
    return EXIT.get(str(out.get("status")), 2)


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
    fd, temporary_path = tempfile.mkstemp(dir=p.parent, prefix=f".{p.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        os.replace(temporary_path, p)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary_path)
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


def contract_and_plan(contract_path: str, plan_path: str | None = None) -> tuple[dict, dict | None, dict]:
    """(contract, plan, extras) from a calibration-contract/1 and a calibration-plan/1, or from a calibration-fixture/1
    holding both (extras: its other keys, e.g. the design fixture's synthetic `systematics`)."""
    doc = load(contract_path)
    if not isinstance(doc, dict):
        raise InputError(f"{contract_path}: a contract or fixture is a JSON object")
    if doc.get("schema") == "calibration-fixture/1":
        contract, plan = doc.get("contract"), doc.get("plan")
        extras = {k: v for k, v in doc.items() if k not in ("contract", "plan")}
    else:
        contract, plan, extras = doc, None, {}
    if plan_path:
        plan = load(plan_path)
    if not isinstance(contract, dict):
        raise InputError("no contract")
    return contract, plan, extras


def jsonable(x):
    """NumPy arrays and scalars to plain JSON values (NaN to null, +-inf to the strings "inf", "-inf"); keys starting
    with '_' (internal detail) dropped."""
    import numpy as np
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items() if not str(k).startswith("_")}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        x = x.item()
    if isinstance(x, float) and not np.isfinite(x):        # NaN / Infinity are not JSON (review F15)
        return None if np.isnan(x) else ("inf" if x > 0 else "-inf")
    return x


def systematics(release_path: str | None, extras: dict) -> list | None:
    """The eta columns' source: the `systematic` component of a calibration release (readable; the sealed components
    are never provided, section 2.1): the release file given, else a design fixture's synthetic release."""
    from core.calibration import data_release as data
    r = load(release_path) if release_path else extras.get("release")
    if r is not None:
        try:
            systematic: Any = data.provide(r, "systematic", opened=False, role="calibration")
            return systematic
        except (data.DataError, KeyError, TypeError) as exc:
            raise InputError(f"{release_path or 'the fixture release'}: no readable systematic component ({exc})") \
                from None
    return None
