"""Files of one review: locations, deterministic JSON writing, the private directory and the event log, appended only
under an exclusive file lock (fcntl on POSIX, msvcrt on Windows; spec section 2)."""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

from core import hostcaps
from contracts.review import encode, event_problems, make_event, make_head, parse_log, parse_time, verify_log

ASSETS = Path(__file__).resolve().parents[2] / "assets"


class ReviewError(Exception):
    """A refused command: bad input or a state in which the command may not run (exit 2)."""


def dumps(obj) -> str:
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(obj), encoding="utf-8")


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_asset(name: str) -> dict:
    return read_json(ASSETS / name)


def default_private_root() -> Path:
    """$XDG_STATE_HOME/hep-research/reviews, else ~/.local/state/..., on Windows %LOCALAPPDATA%\\hep-research\\reviews."""
    return hostcaps.state_dir("reviews")


@contextlib.contextmanager
def locked(path: Path):
    """An exclusive lock on path (created if needed) for the duration of the block."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as fh:
        if os.name == "nt":  # pragma: no cover - Windows
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


class Review:
    """A review directory <project>/reviews/<id> and its private directory <private_root>/<id>."""

    def __init__(self, project: Path, review_id: str, private_root: Path):
        self.project = Path(project).resolve()
        self.id = review_id
        self.dir = self.project / "reviews" / review_id
        self.private = Path(private_root).resolve() / review_id
        self.log = self.dir / "review_log.jsonl"
        self.head = self.dir / "review_head.json"
        self.lock = self.dir / "review_log.lock"

    def attempt_dir(self, r: int, sid: str, k: int) -> Path:
        return self.dir / f"round-{r}" / sid / f"attempt-{k}"

    def private_attempt(self, r: int, sid: str, k: int) -> Path:
        return self.private / f"round-{r}" / sid / f"attempt-{k}"

    def units_path(self, r: int) -> Path:
        return self.dir / "units" / f"round-{r}.json"

    def events(self) -> list:
        if not self.log.exists():
            return []
        return parse_log(self.log.read_bytes())

    def verified(self) -> tuple[list, list[str]]:
        try:
            events = self.events()
            head = read_json(self.head)
        except (OSError, ValueError) as exc:
            return [], [str(exc)]
        return events, verify_log(events, head)

    def append(self, event: str, time: str, data: dict) -> dict:
        """Append one event and rewrite the head, under the log lock; refuses a log that does not verify."""
        with locked(self.lock):
            events = self.events()
            if events:
                problems = verify_log(events, read_json(self.head))
                if problems:
                    raise ReviewError(f"the event log does not verify: {problems[0]}")
            rec = make_event(events[-1] if events else None, event, time, data)
            probs = event_problems(rec)
            if probs:
                raise ReviewError(f"refused to write a malformed {event} event: {probs[0]}")
            if events and parse_time(time) < parse_time(events[-1]["time"]):
                raise ReviewError(f"--now {time} is earlier than the last event ({events[-1]['time']})")
            with open(self.log, "ab") as fh:
                fh.write(encode(rec))
            tmp = self.head.with_suffix(".json.tmp")
            tmp.write_text(dumps(make_head(self.id, events + [rec])), encoding="utf-8")
            os.replace(tmp, self.head)
            return rec

    # private files
    def slots(self) -> dict:
        p = self.private / "slots.json"
        return read_json(p) if p.exists() else {}

    def save_slots(self, slots: dict) -> None:
        write_json(self.private / "slots.json", slots)

    def seeds(self) -> dict:
        return read_json(self.private / "sample_seed")

    def save_seeds(self, seeds: dict) -> None:
        write_json(self.private / "sample_seed", seeds)


def find_reviews(project: Path) -> list[str]:
    root = Path(project) / "reviews"
    return sorted(p.name for p in root.iterdir() if (p / "review_log.jsonl").is_file()) if root.is_dir() else []
