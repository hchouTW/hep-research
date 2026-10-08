"""Execution-bundle freezing for a campaign (AGENTIC-R5 T4.2, F06, X05, X14): what will run, by content.

freeze() writes <campaign>/bundles/<bundle_digest>.json (write-once) listing, with full SHA-256, size and mode:

  campaign      manifest.json, spec.json (command template, container image, worker timeout), runner.py
  worker        every regular file under the worker root the command uses (symlinks and other non-regular files
                are refused, caches skipped)
  interpreter   the command's first token when it is an absolute path outside the worker root: the file it resolves
                to (virtual environments use links) is hashed, and verify() checks the path still resolves there
  environment   an environment lock file, when given (pip freeze, conda lock, container build record, ...)

plus the container image, which must be pinned by digest (name@sha256:<64 hex>; a tag can move, X14), the campaign's
manifest hash and uid, and the data exposure known at freezing time (the AGENTIC-R5 T4.4 states; default
{"state": "unknown", "basis": "none"}). Every other absolute path in the command is refused: the command may refer only
to bundle content. The bundle digest is the SHA-256 of the canonical JSON (sorted keys, no whitespace) of everything
except the approval request and the creation time, so a change of code, defaults, environment, image or recorded
exposure gives a different digest.

The file also carries an approval request (bundle_digest, config_hash, limits, scope) for a human decision through the
trusted gate (T4.1). Nothing here approves anything, and the files stay agent-writable: verify() detects changes,
check_campaign() refuses a bundle frozen for another campaign, and execution from approved bytes is the trusted
submitter's job (T3.5).

Command words: the first must be an absolute interpreter path; any word that may name a file (it contains '/', starts
with '~', or has a dot and is not a number, also after '--opt=') must be an absolute path to a bundled worker file. Bare
words, numbers, flags and the runner's placeholders pass. Standard library only.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shlex
import stat
from pathlib import Path

FORMAT = "hep-research-execution-bundle/1"
IMAGE_PINNED = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")
EXPOSURE_STATES = ("unexposed", "exposed", "unknown", "incomplete")
EXPOSURE_BASES = ("structured-record", "legacy-text", "none")
CACHE_DIRS = {".git", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".ipynb_checkpoints"}
CAMPAIGN_FILES = ("manifest.json", "spec.json", "runner.py")


class BundleError(ValueError):
    """Refusal with a named code."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _entry(role: str, root: Path, rel: str) -> dict:
    path = root / rel
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise BundleError("bundle.missing_file", f"{role}:{rel}: {exc.strerror}") from None
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise BundleError("bundle.not_regular", f"{role}:{rel}: only regular files are bundled (a link is never followed)")
    return {"role": role, "path": rel, "sha256": _sha(path), "size": st.st_size,
            "mode": "100755" if st.st_mode & 0o111 else "100644"}


def _tree(root: Path) -> list[str]:
    out = []
    for parent, dirs, names in os.walk(root, followlinks=False):
        for d in list(dirs):
            if (Path(parent) / d).is_symlink():
                raise BundleError("bundle.not_regular", f"worker:{(Path(parent) / d).relative_to(root).as_posix()}: "
                                  "a symbolic link to a directory is never followed")
        dirs[:] = sorted(d for d in dirs if d not in CACHE_DIRS)
        out += [(Path(parent) / n).relative_to(root).as_posix() for n in names]  # a .pyc outside __pycache__ is code
    return sorted(out, key=lambda p: p.encode("utf-8"))


def _inside(path: str, root: Path) -> bool:
    try:
        Path(os.path.normpath(path)).relative_to(root)
        return True
    except ValueError:
        return False


NUMBER = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")


def _path_like(value: str) -> bool:
    """A command word that may name a file: it contains '/', starts with '~', or has a dot and is not a number.
    Placeholders ({out}, ...) and flags are filled or read by the runner and the worker, not looked up here."""
    if not value or value.startswith("{") or (value.startswith("-") and "=" not in value and "/" not in value):
        return False
    return "/" in value or value.startswith("~") or ("." in value and not NUMBER.match(value))


def check_exposure(rec) -> dict:
    if rec is None:
        return {"state": "unknown", "basis": "none"}
    if (not isinstance(rec, dict) or rec.get("state") not in EXPOSURE_STATES or rec.get("basis") not in EXPOSURE_BASES
            or set(rec) - {"state", "basis", "record_ref"}):
        raise BundleError("bundle.bad_exposure", f"data_exposure must be {{'state': one of {list(EXPOSURE_STATES)}, "
                          f"'basis': one of {list(EXPOSURE_BASES)}, optional 'record_ref'}}")
    if rec["state"] == "unexposed" and rec["basis"] != "structured-record":
        raise BundleError("bundle.bad_exposure", "'unexposed' needs basis 'structured-record'")
    return dict(rec)


def digest_of(doc: dict) -> str:
    body = {k: doc[k] for k in ("format", "campaign_uid", "manifest_hash", "container_image", "data_exposure", "roots", "files")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def build(campaign_dir, worker_root=None, env_lock=None, data_exposure=None) -> dict:
    """The bundle document for the campaign as it is on disk now (no approval request, no file written)."""
    cdir = Path(campaign_dir).resolve()
    spec = json.loads((cdir / "spec.json").read_text(encoding="utf-8"))
    state = json.loads((cdir / "state.json").read_text(encoding="utf-8"))
    image = spec.get("container_image")
    if not state.get("campaign_uid"):
        raise BundleError("bundle.no_uid", "the campaign has no campaign_uid yet (created before tags): run a submit dry "
                          "run once, then freeze")
    if image is not None and not IMAGE_PINNED.match(str(image)):
        raise BundleError("bundle.image_unpinned", f"container image {image!r} is not pinned by digest (name@sha256:<64 hex>)")
    files = [_entry("campaign", cdir, n) for n in CAMPAIGN_FILES]
    roots = {"campaign": str(cdir)}
    wroot = None
    if worker_root is not None:
        wroot = Path(worker_root)
        if wroot.is_symlink() or not wroot.is_dir():
            raise BundleError("bundle.bad_worker_root", f"{worker_root}: not a directory (a link is never followed)")
        wroot = wroot.resolve()
        roots["worker"] = str(wroot)
        files += [_entry("worker", wroot, rel) for rel in _tree(wroot)]
    try:
        tokens = shlex.split(spec["cmd"])
    except ValueError as exc:
        raise BundleError("bundle.bad_command", str(exc)) from None
    for i, tok in enumerate(tokens):
        value = tok.split("=", 1)[1] if tok.startswith("-") and "=" in tok else tok  # --opt=/path names a path too
        if i == 0 and not value.startswith("/"):
            raise BundleError("bundle.relative_path", f"{tok}: the interpreter must be an absolute path, so the bundle can hash it")
        if not _path_like(value):
            continue
        if not value.startswith("/"):
            raise BundleError("bundle.relative_path", f"{tok}: a relative path resolves wherever the job starts; give an "
                              "absolute path inside the worker root")
        if wroot is not None and _inside(os.path.realpath(value), wroot):  # resolved, as wroot is (/var -> /private/var)
            rel = Path(os.path.realpath(value)).relative_to(wroot).as_posix()
            if not any(f["role"] == "worker" and f["path"] == rel for f in files):
                raise BundleError("bundle.path_outside", f"{tok}: named by the command but not a bundled worker file")
        elif i == 0:
            real = Path(os.path.realpath(value))
            roots["interpreter"] = str(real.parent)
            files.append(dict(_entry("interpreter", real.parent, real.name), named_as=value))
        else:
            raise BundleError("bundle.path_outside", f"{tok}: the command may refer only to paths inside the bundle "
                              "(give --worker-root for the worker code)")
    if env_lock is not None:
        p = Path(env_lock)
        roots["environment"] = str(p.parent.resolve())
        files.append(_entry("environment", p.parent.resolve(), p.name))
    doc = {"format": FORMAT, "campaign_uid": state.get("campaign_uid"), "manifest_hash": state["manifest_hash"],
           "container_image": image, "data_exposure": check_exposure(data_exposure), "roots": roots, "files": files}
    doc["bundle_digest"] = digest_of(doc)
    return doc


def verify(doc: dict) -> dict:
    """Re-hash every bundled file from its recorded root: {'status': 'identical'|'different', 'differences'}.
    A document whose digest does not match its own content is 'different' at once."""
    if doc.get("format") != FORMAT:
        raise BundleError("bundle.bad_format", f"not a {FORMAT} document")
    if digest_of(doc) != doc.get("bundle_digest"):
        return {"status": "different", "bundle_digest": doc.get("bundle_digest"),
                "differences": [{"change": "document", "message": "the bundle digest does not match the document"}]}
    diffs = []
    for f in doc["files"]:
        root = Path(doc["roots"][f["role"]])
        try:
            now = _entry(f["role"], root, f["path"])
        except BundleError as exc:
            diffs.append({"role": f["role"], "path": f["path"], "change": exc.code})
            continue
        if "named_as" in f:
            if os.path.realpath(f["named_as"]) != str(root / f["path"]):
                diffs.append({"role": f["role"], "path": f["named_as"], "change": "resolves elsewhere"})
            now["named_as"] = f["named_as"]
        if now != f:
            diffs.append({"role": f["role"], "path": f["path"], "change": "content" if now["sha256"] != f["sha256"] else "mode"})
    if "worker" in doc["roots"]:
        wroot = Path(doc["roots"]["worker"])
        listed = {f["path"] for f in doc["files"] if f["role"] == "worker"}
        try:
            added = sorted(set(_tree(wroot)) - listed)
        except (BundleError, OSError) as exc:
            added, diffs = [], diffs + [{"role": "worker", "path": ".", "change": str(exc)}]
        diffs += [{"role": "worker", "path": p, "change": "added"} for p in added]
    return {"status": "identical" if not diffs else "different", "bundle_digest": doc["bundle_digest"], "differences": diffs}


def freeze(campaign_dir, worker_root=None, env_lock=None, data_exposure=None, config: dict | None = None,
           scope: str | None = None, config_hash: str | None = None) -> dict:
    """Write <campaign>/bundles/<digest>.json once (an identical re-freeze returns the existing one)."""
    doc = build(campaign_dir, worker_root, env_lock, data_exposure)
    cfg = config or {}
    doc["approval_request"] = {"bundle_digest": doc["bundle_digest"], "config_hash": config_hash, "limits": cfg.get("limits"),
                               "max_attempts": cfg.get("max_attempts"), "scope": scope,
                               "note": "a request, not an approval: a human decides through the trusted gate"}
    doc["created"] = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = Path(campaign_dir) / "bundles" / f"{doc['bundle_digest']}.json"
    out.parent.mkdir(exist_ok=True)
    if out.exists():
        old = json.loads(out.read_text(encoding="utf-8"))
        if old.get("approval_request") == doc["approval_request"]:
            return dict(old, path=str(out), reused=True)
        raise BundleError("bundle.request_differs", f"{out.name} was frozen with another approval request; "
                          "freeze the changed configuration as a new bundle")
    tmp = out.with_name(f".tmp-{out.name}")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.link(tmp, out)  # write-once
    tmp.unlink()
    return dict(doc, path=str(out), reused=False)


def check_campaign(doc: dict, campaign_dir) -> list[str]:
    """Why this bundle does not belong to this campaign (root, uid, manifest hash); empty when it does."""
    cdir = Path(campaign_dir).resolve()
    state = json.loads((cdir / "state.json").read_text(encoding="utf-8"))
    out = []
    if doc.get("roots", {}).get("campaign") != str(cdir):
        out.append(f"frozen for campaign directory {doc.get('roots', {}).get('campaign')}, not {cdir}")
    if doc.get("campaign_uid") != state.get("campaign_uid"):
        out.append("another campaign_uid")
    if doc.get("manifest_hash") != state.get("manifest_hash"):
        out.append("another manifest")
    return out


def load(campaign_dir, digest: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", digest or ""):
        raise BundleError("bundle.bad_digest", f"{digest!r} is not a full SHA-256")
    path = Path(campaign_dir) / "bundles" / f"{digest}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError("bundle.unreadable", f"{path.name}: {exc}") from None
