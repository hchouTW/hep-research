"""Platform calls of the detector-simulation shared layer: file-system type, durable writes, no-replace rename.

A module of detsim.py (TASK.md 6.2, 10.2 step 1 and 10.3 under docs/dev/detector-simulation/; decision D-W1-3 and
V-04 of PROGRESS.md). Every call goes through a small recorder hook (CALLS) so tests can confirm the order of fsync,
F_FULLFSYNC and rename calls without strace.

- filesystem_type(path): macOS statfs(2) f_fstypename through ctypes (measured: apfs); Linux the longest mount point
  of /proc/self/mountinfo containing path. LOCAL_FILESYSTEMS lists the allowlist per platform; anything else (NFS,
  CIFS, FUSE, object storage, unknown) is refused by the caller with unsupported-fs.
- fsync_file(path): F_FULLFSYNC on macOS (plain fsync does not reach stable storage there), fsync on Linux.
- fsync_dir(path): directory fsync; best effort (durable_commit is soft on macOS).
- rename_noreplace(src, dst): renamex_np(RENAME_EXCL) on macOS, renameat2(RENAME_NOREPLACE) on Linux, through ctypes;
  raises FileExistsError when dst exists (an empty directory included). When the call is unavailable it returns
  False and the caller falls back to check-then-rename under its lock (commit_noreplace: soft).
- set_parent_death_signal(): Linux PR_SET_PDEATHSIG(SIGKILL) for a preexec_fn, followed by a getppid() check.
"""
from __future__ import annotations

import sys

if __spec__ is None:  # run as a file (tests/skills/test_cli_robustness.py): a module of detsim.py, not a command
    print(__doc__.splitlines()[0] + "\nA module of detsim.py, not a command: python3 detsim.py --help")
    sys.exit(0 if sys.argv[1:] in ([], ["--help"], ["-h"]) else 2)

import ctypes  # noqa: E402
import ctypes.util  # noqa: E402
import errno  # noqa: E402
import fcntl  # noqa: E402
import os  # noqa: E402
from pathlib import Path  # noqa: E402

LOCAL_FILESYSTEMS = {"darwin": frozenset({"apfs", "hfs"}),
                     "linux": frozenset({"ext2", "ext3", "ext4", "xfs", "btrfs", "tmpfs"})}
RENAME_EXCL = 0x00000004       # macOS <stdio.h>
RENAME_NOREPLACE = 1           # Linux <linux/fs.h>
AT_FDCWD = -100
PR_SET_PDEATHSIG = 1
CALLS: list = []  # (operation, path) in call order; tests read and clear it
_LIBC = None


def _libc():
    global _LIBC
    if _LIBC is None:
        _LIBC = ctypes.CDLL(ctypes.util.find_library("c") or None, use_errno=True)
    return _LIBC


def platform_key() -> str:
    return "darwin" if sys.platform == "darwin" else "linux" if sys.platform.startswith("linux") else sys.platform


class _StatfsDarwin(ctypes.Structure):  # struct statfs with 64-bit inodes (<sys/mount.h>)
    _fields_ = [("f_bsize", ctypes.c_uint32), ("f_iosize", ctypes.c_int32), ("f_blocks", ctypes.c_uint64),
                ("f_bfree", ctypes.c_uint64), ("f_bavail", ctypes.c_uint64), ("f_files", ctypes.c_uint64),
                ("f_ffree", ctypes.c_uint64), ("f_fsid", ctypes.c_int32 * 2), ("f_owner", ctypes.c_uint32),
                ("f_type", ctypes.c_uint32), ("f_flags", ctypes.c_uint32), ("f_fssubtype", ctypes.c_uint32),
                ("f_fstypename", ctypes.c_char * 16), ("f_mntonname", ctypes.c_char * 1024),
                ("f_mntfromname", ctypes.c_char * 1024), ("f_flags_ext", ctypes.c_uint32),
                ("f_reserved", ctypes.c_uint32 * 7)]


def _mountinfo_type(path: Path) -> str | None:
    best, best_type = "", None
    try:
        lines = Path("/proc/self/mountinfo").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    target = str(path)
    for line in lines:
        left, _, right = line.partition(" - ")
        fields, tail = left.split(), right.split()
        if len(fields) < 5 or not tail:
            continue
        mount = fields[4].encode("utf-8").decode("unicode_escape")
        if (target == mount or target.startswith(mount.rstrip("/") + "/")) and len(mount) >= len(best):
            best, best_type = mount, tail[0]
    return best_type


def filesystem_type(path) -> str | None:
    """The file-system type name of the existing folder path, or None when it cannot be determined."""
    path = Path(path).resolve()
    if platform_key() == "darwin":
        buf = _StatfsDarwin()
        libc = _libc()
        fn = getattr(libc, "statfs$INODE64", None) or libc.statfs
        fn.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
        if fn(os.fsencode(path), ctypes.byref(buf)) != 0:
            return None
        return buf.f_fstypename.decode("ascii", "replace") or None
    if platform_key() == "linux":
        return _mountinfo_type(path)
    return None


def fsync_file(path) -> str:
    """Flush one file to stable storage; returns the call used ("F_FULLFSYNC" or "fsync")."""
    fd = os.open(path, os.O_RDONLY)
    try:
        if platform_key() == "darwin" and hasattr(fcntl, "F_FULLFSYNC"):
            CALLS.append(("F_FULLFSYNC", str(path)))
            fcntl.fcntl(fd, fcntl.F_FULLFSYNC)
            return "F_FULLFSYNC"
        CALLS.append(("fsync", str(path)))
        os.fsync(fd)
        return "fsync"
    finally:
        os.close(fd)


def fsync_dir(path) -> bool:
    """Directory fsync, best effort; False when the platform refuses it."""
    CALLS.append(("fsync_dir", str(path)))
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return False
    try:
        os.fsync(fd)
        return True
    except OSError:
        return False
    finally:
        os.close(fd)


def rename_noreplace(src, dst) -> bool:
    """Rename src to dst unless dst exists (FileExistsError). False when no no-replace call is available here."""
    CALLS.append(("rename_noreplace", str(dst)))
    libc = _libc()
    if platform_key() == "darwin" and hasattr(libc, "renamex_np"):
        fn = libc.renamex_np
        fn.argtypes, fn.restype = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint], ctypes.c_int
        rc = fn(os.fsencode(src), os.fsencode(dst), RENAME_EXCL)
    elif platform_key() == "linux" and hasattr(libc, "renameat2"):
        fn = libc.renameat2
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        fn.restype = ctypes.c_int
        rc = fn(AT_FDCWD, os.fsencode(src), AT_FDCWD, os.fsencode(dst), RENAME_NOREPLACE)
    else:
        return False
    if rc == 0:
        return True
    err = ctypes.get_errno()
    if err == errno.EEXIST or err == errno.ENOTEMPTY:
        raise FileExistsError(err, os.strerror(err), str(dst))
    if err in (errno.EINVAL, errno.ENOSYS, errno.ENOTSUP):
        return False  # the file system or kernel lacks the flag: caller falls back (commit_noreplace: soft)
    raise OSError(err, os.strerror(err), str(src))


def set_parent_death_signal() -> None:  # pragma: no cover - runs in the child between fork and exec, Linux only
    """preexec_fn on Linux: SIGKILL this child when its parent dies, then exit if the parent is already gone."""
    import signal
    parent = os.getppid()
    _libc().prctl(PR_SET_PDEATHSIG, int(signal.SIGKILL), 0, 0, 0)
    if os.getppid() != parent:
        os._exit(1)
