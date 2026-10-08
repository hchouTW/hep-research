"""Code identity of the installed plugin (AGENTIC-R5 T0.2/T0.3, plan basis §6.6).

The release bundle is the git-listed plugin files or, outside git (an installed copy, a `git archive` export), every
regular file except caches. Recorded manifests under `release-manifests/` are never part of a bundle, so a release can
carry its own. For each file: relative POSIX path, full SHA-256, size and mode (100755 when any execute bit is set,
else 100644); symlinks and other non-regular files are refused; files are sorted by the UTF-8 bytes of their path. The
digest is the SHA-256 of the canonical UTF-8 JSON (sorted keys, no whitespace) of {"format", "files"}.

plugin_release() is the one helper producers call for `versions.plugin_release`: {"release": <version>, "digest":
<64 hex>} when the installed tree matches its own recorded manifest `release-manifests/<version>.json`, else
{"release": "unreleased", "digest": "unknown"} (a development tree has no stable identity to record). Identity is
provenance only: it never authorizes a use.
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "hep-research-code-release-manifest/1"
RECORDS = "release-manifests/"  # recorded manifests of published releases; never part of a bundle
CACHE_DIRS = {".git", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
UNKNOWN = {"release": "unreleased", "digest": "unknown"}


class RefusedFile(ValueError):
    pass


def _git_files(root: Path) -> list[str] | None:
    try:
        inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, capture_output=True, text=True,
                                timeout=60)
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return None
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "."],
                             cwd=root, capture_output=True, text=True, check=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    # a tracked file deleted in the work tree is not part of the tree on disk
    return [f for f in out.split("\0") if f and os.path.lexists(root / f)]


def _walk_files(root: Path) -> list[str]:
    found = []
    for parent, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in CACHE_DIRS]
        for name in dirs + names:
            if (Path(parent) / name).is_symlink():
                found.append((Path(parent) / name).relative_to(root).as_posix())
        found += [(Path(parent) / n).relative_to(root).as_posix() for n in names
                  if not n.endswith(".pyc") and not (Path(parent) / n).is_symlink()]
    return found


def bundle_files(root: Path) -> list[str]:
    listed = _git_files(root)
    if listed is None:
        listed = _walk_files(root)
    keep = {f for f in listed if not f.startswith(RECORDS) and "__pycache__/" not in f and not f.endswith(".pyc")}
    return sorted(keep, key=lambda f: f.encode("utf-8"))


def entry(root: Path, rel: str) -> dict:
    path = root / rel
    st = os.lstat(path)
    if stat.S_ISLNK(st.st_mode):
        raise RefusedFile(f"{rel}: symbolic links are not allowed in a release bundle")
    if not stat.S_ISREG(st.st_mode):
        raise RefusedFile(f"{rel}: not a regular file")
    if "\\" in rel or "\n" in rel or rel.startswith("/") or ".." in rel.split("/"):
        raise RefusedFile(f"{rel}: unsupported path")
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return {"path": rel, "sha256": h.hexdigest(), "size": st.st_size,
            "mode": "100755" if st.st_mode & 0o111 else "100644"}


def digest_of(files: list[dict]) -> str:
    body = json.dumps({"format": FORMAT, "files": files}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def generate(root: Path) -> dict:
    files = [entry(root, rel) for rel in bundle_files(root)]
    try:
        version = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        version = None
    return {"format": FORMAT, "plugin": "hep-research", "version": version, "hash_algorithm": "sha256",
            "path_order": "UTF-8 bytes, ascending", "file_count": len(files), "digest": digest_of(files), "files": files}


def verify(root: Path, recorded: dict) -> dict:
    if recorded.get("format") != FORMAT or not isinstance(recorded.get("files"), list):
        raise ValueError(f"not a {FORMAT} manifest")
    if digest_of(recorded["files"]) != recorded.get("digest"):
        raise ValueError("the recorded manifest's digest does not match its own file list")
    now = generate(root)
    old = {f["path"]: f for f in recorded["files"]}
    new = {f["path"]: f for f in now["files"]}
    diffs = [{"path": p, "change": "missing"} for p in sorted(old.keys() - new.keys())]
    diffs += [{"path": p, "change": "added"} for p in sorted(new.keys() - old.keys())]
    diffs += [{"path": p, "change": "content" if old[p]["sha256"] != new[p]["sha256"] else "mode"}
              for p in sorted(old.keys() & new.keys()) if old[p] != new[p]]
    return {"status": "identical" if not diffs else "different", "recorded_digest": recorded["digest"],
            "digest": now["digest"], "differences": diffs}




def plugin_release(root: Path | None = None) -> dict:
    """{"release", "digest"} for versions.plugin_release (see the module docstring)."""
    return dict(_plugin_release(str(Path(root or ROOT).resolve())))


@functools.lru_cache(maxsize=8)
def _plugin_release(root: str) -> tuple:
    r = Path(root)
    try:
        version = json.loads((r / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        recorded = json.loads((r / RECORDS / f"{version}.json").read_text(encoding="utf-8"))
        if verify(r, recorded)["status"] == "identical":
            return tuple({"release": version, "digest": recorded["digest"]}.items())
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return tuple(UNKNOWN.items())
