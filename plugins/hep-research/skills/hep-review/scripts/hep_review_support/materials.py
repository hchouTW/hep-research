"""Controlled reading, snapshots and drop-file ingestion (hep-review spec v9 sections 9.1-9.4 and 12.4).

Reading is root-bound and component by component: every intermediate component is opened relative to the previous
directory fd with O_DIRECTORY|O_NOFOLLOW, the last with O_NOFOLLOW|O_NONBLOCK and then fstat-ed, so symlinks
(including parent components), FIFOs, sockets and devices are refused and a FIFO never blocks. Known blind spots:
hard links and bind mounts can point in-root paths at out-of-root content; bind mounts are undetectable, hard links
(st_nlink > 1) are recorded as a limitation. These rules do not defend against anyone with full control of the host.
On a platform without dir_fd support the procedure is unavailable and no root-bound claim is made (case N26).
"""
from __future__ import annotations

import errno
import hashlib
import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_MAX_BYTES = 16 * 1024 * 1024
DROP_MAX_BYTES = 256 * 1024
HARD_LINK_LIMITATION = "hard link (st_nlink > 1): the bytes may also be reachable from outside the root"
ROOT_BOUND_LIMITATION = ("root-bound reading: hard links and bind mounts can point in-root paths at out-of-root "
                         "content; bind mounts are undetectable")


class ReadRefused(Exception):
    """A path was refused; `code` says why (read.*, capture.*, snapshot.*)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


class ControlledReadUnavailable(Exception):
    """The platform lacks dir_fd opening or the needed flags: controlled_read=unavailable (spec 9.1)."""


@dataclass
class ReadResult:
    content: bytes
    sha256: str
    size: int
    mtime_ns: int
    ctime_ns: int
    nlink: int
    limitations: list[str] = field(default_factory=list)


def platform_capabilities() -> dict:
    return {"supports_dir_fd_open": os.open in os.supports_dir_fd, "O_NOFOLLOW": hasattr(os, "O_NOFOLLOW"),
            "O_DIRECTORY": hasattr(os, "O_DIRECTORY"), "O_NONBLOCK": hasattr(os, "O_NONBLOCK")}


def controlled_read_available(caps: dict | None = None) -> bool:
    caps = platform_capabilities() if caps is None else caps
    return all(caps.get(k) for k in ("supports_dir_fd_open", "O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK"))


def _components(rel: str) -> list[str]:
    if not isinstance(rel, str) or not rel or rel.startswith("/") or "\\" in rel or "\x00" in rel:
        raise ReadRefused("read.bad_component", f"{rel!r} is not a relative path")
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ReadRefused("read.bad_component", f"{rel!r} has an empty, '.' or '..' component")
    return parts


def _refusal(e: OSError, rel: str) -> ReadRefused:
    if e.errno in (errno.ELOOP, errno.EMLINK) or (e.errno == errno.ENOTDIR):
        return ReadRefused("read.symlink", f"{rel}: a component is a symlink or not a directory")
    if e.errno == errno.ENOENT:
        return ReadRefused("read.missing", f"{rel}: no such file")
    if e.errno in (errno.EACCES, errno.EPERM):
        return ReadRefused("read.denied", f"{rel}: permission denied")
    return ReadRefused("read.os_error", f"{rel}: {e.strerror}")


def read_controlled(root: Path | str, rel: str, *, max_bytes: int = DEFAULT_MAX_BYTES, caps: dict | None = None,
                    _hook: Callable[[], None] | None = None) -> ReadResult:
    """Read one regular file under root without following any symlink (spec 9.2)."""
    if not controlled_read_available(caps):
        raise ControlledReadUnavailable("os.open with dir_fd and O_NOFOLLOW/O_DIRECTORY/O_NONBLOCK is required")
    parts = _components(rel)
    try:  # the root's last component is not followed either (review m5: a drops folder replaced by a symlink)
        dfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as e:
        raise _refusal(e, str(root)) from None
    try:
        for p in parts[:-1]:
            try:
                nfd = os.open(p, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dfd)
            except OSError as e:
                raise _refusal(e, rel) from None
            os.close(dfd)
            dfd = nfd
        try:
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
        except OSError as e:
            raise _refusal(e, rel) from None
    finally:
        os.close(dfd)
    try:
        before = os.fstat(fd)
        if stat.S_ISLNK(before.st_mode):
            raise ReadRefused("read.symlink", f"{rel} is a symlink")
        if not stat.S_ISREG(before.st_mode):
            raise ReadRefused("read.not_regular", f"{rel} is not a regular file")
        if before.st_size > max_bytes:
            raise ReadRefused("read.too_large", f"{rel}: {before.st_size} bytes > limit {max_bytes}")
        if _hook is not None:
            _hook()
        chunks, total = [], 0
        while chunk := os.read(fd, 65536):
            total += len(chunk)
            if total > max_bytes:
                raise ReadRefused("read.too_large", f"{rel}: grew past the limit {max_bytes} while reading")
            chunks.append(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    content = b"".join(chunks)
    if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns,
                                                                     after.st_ctime_ns) or len(content) != after.st_size:
        raise ReadRefused("capture.unstable", f"{rel} changed while it was read")
    lim = [HARD_LINK_LIMITATION] if after.st_nlink > 1 else []
    return ReadResult(content, hashlib.sha256(content).hexdigest(), len(content), after.st_mtime_ns, after.st_ctime_ns,
                      after.st_nlink, lim)


def _store_blob(snapdir: Path, content: bytes, digest: str) -> None:
    snapdir.mkdir(parents=True, exist_ok=True)
    target = snapdir / digest
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ReadRefused("snapshot.digest_mismatch", f"existing snapshot {digest} does not match its name")
        return
    temp_path = snapdir / f".{digest}.temp_path-{os.getpid()}"
    with open(temp_path, "wb") as fh:
        fh.write(content)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temp_path, target)


def raw_ref(logical_id: str, digest: str) -> dict:
    return {"logical_id": logical_id, "algorithm": "sha256", "hash_scope": "raw", "profile_id": "raw-bytes/1",
            "digest": digest}


def snapshot(root: Path | str, rels: list[str], snapdir: Path | str, *, max_bytes: int = DEFAULT_MAX_BYTES,
             max_attempts: int = 2, require_coherent_version: bool = False,
             _between_reads: Callable[[Path], None] | None = None) -> dict:
    """Copy each file from the same opened stream into store-owned snapshot bytes named by their SHA-256 and describe
    them for a manifest. Refused or unstable paths become coverage gaps, never silent omissions (spec 9.3, 9.4)."""
    root, snapdir = Path(root), Path(snapdir)
    materials, gaps = [], []
    for rel in rels:
        result = None
        for attempt in range(max_attempts):
            hook = (lambda r=rel: _between_reads(root / r)) if _between_reads is not None and attempt == 0 else None
            try:
                result = read_controlled(root, rel, max_bytes=max_bytes, _hook=hook)
                break
            except ReadRefused as e:
                if e.code != "capture.unstable" or attempt == max_attempts - 1:
                    gaps.append({"path": rel, "code": e.code, "message": str(e)})
                    break
        if result is None:
            continue
        _store_blob(snapdir, result.content, result.sha256)
        materials.append({"material_id": rel, "raw_ref": raw_ref(rel, result.sha256), "view_version": "raw/1",
                          "authors": [], "authors_basis": "unknown", "source_category": "file",
                          "capture": {"size": result.size, "mtime_ns": str(result.mtime_ns),
                                      "ctime_ns": str(result.ctime_ns), "nlink": result.nlink},  # decimal strings: ns
                          # times exceed the metadata integer range (spec 10.2)
                          "limitations": [ROOT_BOUND_LIMITATION] + result.limitations})
    if require_coherent_version:
        gaps.append({"path": "*", "code": "capture.no_coherent_version",
                     "message": "one consistent version was required, but file-by-file copies only show a captured "
                                "working copy and its capture window"})
    return {"materials": materials, "coverage_gaps": gaps,
            "capture": {"method": "working-copy-file-by-file", "coherent_version": False}}


def read_snapshot(snapdir: Path | str, digest: str) -> bytes:
    """Reviewers and readers read only snapshots; the bytes are re-checked against their name."""
    content = read_controlled(snapdir, digest).content
    if hashlib.sha256(content).hexdigest() != digest:
        raise ReadRefused("snapshot.digest_mismatch", f"snapshot {digest} was changed")
    return content


def ingest_submission(drop_root: Path | str, rel: str, declared_digest: str | None = None, *,
                      max_bytes: int = DROP_MAX_BYTES) -> dict:
    """Read a reviewer's drop file by bytes with the section 9.2 procedure; never retyped (spec 12.4). The fidelity is
    digest-bound when a declared SHA-256 matches, mismatch when it does not (both copies kept), else file-transfer.
    This shows the stored bytes are the submitted bytes, not that nobody else read or wrote the drop file. A reviewer
    that reports `unavailable` (or nothing) has declared no digest."""
    r = read_controlled(drop_root, rel, max_bytes=max_bytes)
    said = None if declared_digest is None else re.sub(r"(?i)^\s*sha-?256\s*:", "", declared_digest).strip().lower()
    if said in (None, "", "unavailable"):
        declared_digest = None
    if declared_digest is None:
        fidelity = "file-transfer"
    elif said == r.sha256:
        fidelity = "digest-bound"
    else:
        fidelity = "mismatch"
    return {"raw": r.content, "raw_ref": raw_ref(f"submission:{rel}", r.sha256), "submission_fidelity": fidelity,
            "declared_digest": declared_digest, "limitations": r.limitations}


def transcribed_submission(text: str) -> dict:
    """The coordinator retyped the submission: affected obligations are at most R1 (spec 12.4, case N31)."""
    content = text.encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    return {"raw": content, "raw_ref": raw_ref("submission:transcribed", digest), "submission_fidelity": "transcribed",
            "declared_digest": None, "limitations": ["transcribed by the coordinator: may truncate or alter"]}
