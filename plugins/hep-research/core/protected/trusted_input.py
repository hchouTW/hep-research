#!/usr/bin/env python3
"""Source checks for protected inputs (DP-4): a revocation log or head, a qualification record or a permit is trusted
only when it is a regular file that the running account neither owns nor can write, and that the account cannot
replace through any directory on its path. Such a file can only have been written by another identity (the custodian).
Nothing here verifies who that identity is; it verifies that the running account is not it.

read_protected(path) walks the path one component at a time without trusting links: each component (a directory, a
link, the file itself) must not be replaceable by the account, that is it must not sit in a directory the account can
write or owns (an owner can make it writable). The mode bits allow one exception, a sticky directory where neither it
nor the entry belongs to the account (a shared temporary directory), but for the running account (Account.current(),
real=True) a directory that os.access reports writable is refused as well, sticky or not: an ACL can grant a deletion
the mode bits do not show. So a protected input never sits below a world-writable directory such as /tmp or the
macOS shared folder (live C07 run of 2026-10-14: a release volume mounted there was refused); the exception only
applies to a modelled account (tests). A link is followed only after its own entry passed that test. The file is opened without following a final link, checked
on the open descriptor (regular, one link, not owned, not writable) and read from that descriptor, so the bytes
returned are the bytes checked.

Codes (refusals; a path, never a value): source.missing, source.not_regular, source.hard_linked, source.owned_by_account,
source.writable_by_account, source.replaceable, source.changed, source.link_loop, source.unreadable.
The account defaults to the running process; tests pass another Account to model a custodian-owned file. Running as
root refuses every input (root can replace anything).
"""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

MAX_LINKS = 40


@dataclass(frozen=True)
class Account:
    uid: int
    gids: frozenset = field(default_factory=frozenset)
    real: bool = False  # the running account: os.access is consulted as well (ACLs, read-only mounts)

    @classmethod
    def current(cls) -> Account:
        return cls(os.geteuid(), frozenset(os.getgroups()) | {os.getegid()}, True)


@dataclass
class SourceCheck:
    ok: bool
    data: bytes | None
    refusals: list[tuple[str, str]]  # (code, message)
    sha256: str | None = None


def _writable(st: os.stat_result, acct: Account) -> bool:
    if st.st_uid == acct.uid:
        return bool(st.st_mode & stat.S_IWUSR)
    if st.st_gid in acct.gids:
        return bool(st.st_mode & stat.S_IWGRP)
    return bool(st.st_mode & stat.S_IWOTH)


def _replaceable(dir_st: os.stat_result, entry_st: os.stat_result, acct: Account) -> bool:
    """Whether the account can rename, delete or create the entry in that directory."""
    if acct.uid == 0 or dir_st.st_uid == acct.uid:  # an owner can make its directory writable at any time
        return True
    if not _writable(dir_st, acct):
        return False
    if dir_st.st_mode & stat.S_ISVTX:
        return dir_st.st_uid == acct.uid or entry_st.st_uid == acct.uid
    return True


def _walk(path: str, acct: Account, refusals: list) -> tuple[Path, os.stat_result] | None:
    """The link-free path and lstat of the final entry, after checking every component on the way; None when refused
    or missing."""
    pending = list(Path(os.path.abspath(path)).parts[1:])
    cur = Path("/")
    links = 0
    try:
        cur_st = os.lstat(cur)
        while pending:
            name = pending.pop(0)
            if name in ("", "."):
                continue
            if name == "..":
                cur = cur.parent
                cur_st = os.lstat(cur)
                continue
            entry = cur / name
            try:
                st = os.lstat(entry)
            except FileNotFoundError:
                refusals.append(("source.missing", f"{path}: does not exist"))
                return None
            if _replaceable(cur_st, st, acct) or (acct.real and os.access(cur, os.W_OK, follow_symlinks=False)):
                refusals.append(("source.replaceable", f"{path}: {entry} lies in a directory the running account can write"))
                return None
            if stat.S_ISLNK(st.st_mode):
                links += 1
                if links > MAX_LINKS:
                    refusals.append(("source.link_loop", f"{path}: too many links"))
                    return None
                target = Path(os.readlink(entry))
                pending = list(target.parts[1:] if target.is_absolute() else target.parts) + pending
                if target.is_absolute():
                    cur = Path("/")
                    cur_st = os.lstat(cur)
                continue
            if pending:
                if not stat.S_ISDIR(st.st_mode):
                    refusals.append(("source.missing", f"{path}: {entry} is not a directory"))
                    return None
                cur, cur_st = entry, st
            else:
                return entry, st
    except OSError as exc:
        refusals.append(("source.unreadable", f"{path}: {exc.strerror}"))
        return None
    refusals.append(("source.not_regular", f"{path}: names a directory"))
    return None


def file_refusals(st: os.stat_result, acct: Account, where: str) -> list[tuple[str, str]]:
    """The checks on the opened file itself: regular, one link, not owned and not writable by the account."""
    out = []
    if not stat.S_ISREG(st.st_mode):
        out.append(("source.not_regular", f"{where}: not a regular file"))
    if st.st_nlink != 1:
        out.append(("source.hard_linked", f"{where}: has {st.st_nlink} links; a protected input has one"))
    if st.st_uid == acct.uid:
        out.append(("source.owned_by_account", f"{where}: owned by the running account"))
    if _writable(st, acct):
        out.append(("source.writable_by_account", f"{where}: the running account can write it"))
    return out


def read_protected(path, account: Account | None = None) -> SourceCheck:
    """The bytes of a protected input and the refusals; ok only without any refusal."""
    import hashlib
    acct = account or Account.current()
    refusals: list[tuple[str, str]] = []
    walked = _walk(str(path), acct, refusals)
    if walked is None:
        return SourceCheck(False, None, refusals)
    real, st = walked
    if not stat.S_ISREG(st.st_mode):
        return SourceCheck(False, None, [("source.not_regular", f"{path}: not a regular file")])
    try:
        fd = os.open(real, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        return SourceCheck(False, None, [("source.unreadable", f"{path}: {exc.strerror}")])
    try:
        fst = os.fstat(fd)
        if (fst.st_dev, fst.st_ino) != (st.st_dev, st.st_ino):
            refusals.append(("source.changed", f"{path}: replaced while it was checked"))
        refusals += file_refusals(fst, acct, str(path))
        if acct.real and os.access(real, os.W_OK, follow_symlinks=False) and not any(
                c == "source.writable_by_account" for c, _ in refusals):
            refusals.append(("source.writable_by_account", f"{path}: the running account can write it"))
        if refusals:
            return SourceCheck(False, None, refusals)
        chunks = []
        while True:
            block = os.read(fd, 1 << 20)
            if not block:
                break
            chunks.append(block)
    except OSError as exc:
        return SourceCheck(False, None, [("source.unreadable", f"{path}: {exc.strerror}")])
    finally:
        os.close(fd)
    data = b"".join(chunks)
    return SourceCheck(True, data, [], hashlib.sha256(data).hexdigest())


def read_unchecked(path) -> SourceCheck:
    """The same result shape without the source checks: for advisory use outside protected mode."""
    import hashlib
    try:
        p = Path(path)
        if not p.exists() and not p.is_symlink():
            return SourceCheck(False, None, [("source.missing", f"{path}: does not exist")])
        if p.is_symlink() or not p.is_file():
            return SourceCheck(False, None, [("source.not_regular", f"{path}: not a regular file")])
        data = p.read_bytes()
    except OSError as exc:
        return SourceCheck(False, None, [("source.unreadable", f"{path}: {exc.strerror}")])
    return SourceCheck(True, data, [], hashlib.sha256(data).hexdigest())
