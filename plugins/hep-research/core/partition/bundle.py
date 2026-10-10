"""Execution-bundle freezing for a campaign (AGENTIC-R5 T4.2, F06, X05, X14): what will run, by content.

freeze() writes <campaign>/bundles/<bundle_digest>.json (write-once) listing, with full SHA-256, size and mode:

  campaign      manifest.json, spec.json (command template, container image, worker timeout), runner.py
  worker        every regular file under the worker root the command uses (symlinks and other non-regular files
                are refused, caches skipped)
  interpreter   the command's first token when it is an absolute path outside the worker root: the file it resolves
                to (virtual environments use links) is hashed, and verify() checks the path still resolves there
  shebang       the interpreter a bundled worker's '#!' line names (one absolute path, no arguments), in either form
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

Command grammar (closed): '<absolute interpreter> <absolute bundled worker script> [words]', or a bundled executable
worker first. Each further word is a flag (-x, --name), --name=<value>, or a value: exactly one placeholder ({start},
{stop}, {seed}, {out}, {id}), a number, a plain ASCII word without '/', '.', '~', '$' or braces, or an absolute path
to a bundled worker file; paths carry no braces (the runner formats every word). Every named path is recorded with its
target and re-resolved by verify(), so repointing a link is a change. A bundled worker's '#!' line must name one
absolute interpreter with no arguments, and that interpreter is hashed too. Interpreters may not be launchers (env,
nice, nohup, xargs, timeout, sudo, ...; judged by the resolved name) or '#!' scripts themselves. So no -m, -c or PATH
lookup; what the bundled worker does with a plain word is reviewed code, and enforcing approved bytes at run time is
the trusted submitter's job.
Standard library only.
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

from core.partition import engine

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
FLAG = re.compile(r"^--?[A-Za-z][A-Za-z0-9_-]*$")
PLACEHOLDER_WORD = re.compile(r"^\{(start|stop|seed|out|id)\}$")
BARE = re.compile(r"^[A-Za-z0-9_+:-]+$")  # no '/', '.', '~', '$', '{', '\\' or non-ASCII: never a path


# programs that run their arguments as another program: as an interpreter they would run what the bundle does not name
LAUNCHERS = frozenset({"env", "xargs", "nice", "nohup", "time", "timeout", "sudo", "doas", "su", "stdbuf", "chroot",
                       "setsid", "ionice", "taskset", "numactl", "exec", "command", "busybox", "flock", "watch", "unshare"})


def _shebang(path: Path) -> str | None:
    """The interpreter a '#!' line names, read as the kernel reads it, or None without one. Only a single absolute path
    in plain ASCII is accepted: arguments (a second program, -m, -c), other whitespace or control bytes are refused."""
    try:
        with open(path, "rb") as fh:
            head = fh.readline(4096)
    except OSError:
        return None
    if not head.startswith(b"#!"):
        return None
    line = head[2:].rstrip(b"\n").strip(b" \t")
    if not line or any(b < 0x21 and b not in (0x20, 0x09) or b > 0x7e for b in line) or not head.endswith(b"\n"):
        raise BundleError("bundle.bad_shebang", f"{path}: the '#!' line must be one absolute path in plain ASCII")
    if b" " in line or b"\t" in line:
        raise BundleError("bundle.bad_shebang", f"{path}: '#!' arguments are not bundled; name one interpreter only")
    return line.decode("ascii")


def _launcher(path: str) -> bool:
    return os.path.basename(os.path.realpath(path)) in LAUNCHERS or os.path.basename(path) in LAUNCHERS


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
    body = {k: doc.get(k) for k in ("format", "campaign_uid", "manifest_hash", "container_image", "data_exposure", "roots",
                                    "files", "named")}
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
    if image is not None and not IMAGE_PINNED.fullmatch(str(image)):
        raise BundleError("bundle.image_unpinned", f"container image {image!r} is not pinned by digest (name@sha256:<64 hex>)")
    files = [_entry("campaign", cdir, n) for n in CAMPAIGN_FILES]
    roots = {"campaign": str(cdir)}
    wroot = None
    if worker_root is not None:
        wroot = Path(worker_root)
        if wroot.is_symlink() or not wroot.is_dir():
            raise BundleError("bundle.bad_worker_root", f"{worker_root}: not a directory (a link is never followed)")
        wroot = wroot.resolve()
        if _inside(str(cdir), wroot):
            raise BundleError("bundle.bad_worker_root", f"{wroot} contains the campaign directory, whose state changes as it "
                              "runs: keep the worker code in its own folder")
        roots["worker"] = str(wroot)
        files += [_entry("worker", wroot, rel) for rel in _tree(wroot)]
    try:
        engine.check_template(spec["cmd"])  # spec.json may have changed since init checked it
        tokens = shlex.split(spec["cmd"])
    except ValueError as exc:
        raise BundleError("bundle.bad_command", str(exc)) from None
    if len(tokens) < 2:
        raise BundleError("bundle.bad_command", "the command is '<absolute interpreter> <absolute worker script> [arguments]'")
    named = []

    def worker_path(word: str, tok: str) -> None:
        """An absolute path to a bundled worker file; recorded with its target and re-resolved by verify(). No braces:
        the runner formats every word, so a path with a field would run another path than the one checked."""
        if "{" in word or "}" in word:
            raise BundleError("bundle.bad_word", f"{tok}: a path may not contain braces (it is formatted before it runs)")
        if wroot is None or not word.startswith("/") or not _inside(os.path.realpath(word), wroot):
            raise BundleError("bundle.path_outside", f"{tok}: the command may name only bundled worker files by absolute "
                              "path (give --worker-root for the worker code)")
        if os.path.islink(word):
            raise BundleError("bundle.path_outside", f"{tok}: a link to a worker file; name the bundled file itself")
        rel = Path(os.path.realpath(word)).relative_to(wroot).as_posix()
        if not any(f["role"] == "worker" and f["path"] == rel for f in files):
            raise BundleError("bundle.path_outside", f"{tok}: named by the command but not a bundled worker file")
        named.append({"word": word, "path": rel})

    def interpreter(path: str, role: str, via: str) -> None:
        """Hash an interpreter outside the worker root: an absolute, brace-free path to a program that is neither a
        launcher (env, nice, ...; also through a link) nor a '#!' script itself (no chains)."""
        if not path.startswith("/") or "{" in path or "}" in path:
            raise BundleError("bundle.relative_path", f"{path} ({via}): the interpreter must be an absolute path without "
                              "braces, so the bundle can hash what runs")
        if _launcher(path):
            raise BundleError("bundle.launcher", f"{path} ({via}): a launcher runs another program the bundle does not name")
        real = Path(os.path.realpath(path))
        if _shebang(real) is not None:
            raise BundleError("bundle.bad_shebang", f"{path} ({via}): an interpreter that is itself a '#!' script is not bundled")
        roots[role] = str(real.parent)
        files.append(dict(_entry(role, real.parent, real.name), named_as=path))

    def script_shebang(word: str) -> None:
        """A bundled worker's own '#!' interpreter is hashed whether or not the first word uses it."""
        nxt = _shebang(Path(os.path.realpath(word)))
        if nxt is not None:
            interpreter(nxt, "shebang", f"'#!' line of {word}")

    interp = tokens[0]
    if wroot is not None and interp.startswith("/") and _inside(os.path.realpath(interp), wroot):
        worker_path(interp, interp)  # a bundled executable worker runs directly through its '#!' interpreter
        script_shebang(interp)
        rest = tokens[1:]
    else:
        interpreter(interp, "interpreter", "first word")
        worker_path(tokens[1], tokens[1])  # the interpreter runs a bundled script: no -m, -c or PATH lookup
        script_shebang(tokens[1])
        rest = tokens[2:]
    for tok in rest:
        if NUMBER.fullmatch(tok):
            continue
        flag, eq, value = tok.partition("=") if tok.startswith("-") else ("", "", tok)
        if flag and not FLAG.fullmatch(flag):
            raise BundleError("bundle.bad_word", f"{tok}: flags are -x or --name with letters, digits, '_' and '-'")
        if flag and not eq:
            continue  # a plain flag
        if PLACEHOLDER_WORD.fullmatch(value) or NUMBER.fullmatch(value) or BARE.fullmatch(value):
            continue
        if value.startswith("/"):
            worker_path(value, tok)
            continue
        raise BundleError("bundle.bad_word", f"{tok}: a command word is a flag, one placeholder, a number, a plain word "
                          "(ASCII letters, digits, '_', '+', ':', '-') or an absolute path to a bundled worker file")
    if env_lock is not None:
        p = Path(env_lock)
        roots["environment"] = str(p.parent.resolve())
        files.append(_entry("environment", p.parent.resolve(), p.name))
    doc = {"format": FORMAT, "campaign_uid": state.get("campaign_uid"), "manifest_hash": state["manifest_hash"],
           "container_image": image, "data_exposure": check_exposure(data_exposure), "roots": roots, "files": files,
           "named": named}
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
    for n in doc.get("named", []):  # a word that resolved into the worker root must still resolve to the same file
        if os.path.realpath(n["word"]) != str(Path(doc["roots"].get("worker", "")) / n["path"]):
            diffs.append({"role": "worker", "path": n["word"], "change": "resolves elsewhere"})
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
        # the same files under another request (a changed configuration): never overwritten; the new request gets its
        # own write-once file under the same digest, and load() tells them apart by the configuration hash
        out = out.with_name(f"{doc['bundle_digest']}-{request_id(doc['approval_request'])}.json")
        if out.exists():
            old = json.loads(out.read_text(encoding="utf-8"))
            if old.get("approval_request") == doc["approval_request"]:
                return dict(old, path=str(out), reused=True)
            raise BundleError("bundle.request_differs", f"{out.name} was frozen with another approval request")
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


def config_hash(cfg: dict) -> str:
    """SHA-256 of the configuration as sorted JSON: the key an approval request and a submission share."""
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


def request_id(request: dict) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:12]


def load(campaign_dir, digest: str, config_hash: str | None = None) -> dict:
    """The bundle document frozen for digest; with several requests under one digest (see freeze), the one whose
    approval request names config_hash. Refused: bundle.ambiguous (several, no hash given), bundle.request_differs
    (none frozen with this configuration), bundle.unreadable."""
    if not re.fullmatch(r"[0-9a-f]{64}", digest or ""):
        raise BundleError("bundle.bad_digest", f"{digest!r} is not a full SHA-256")
    folder = Path(campaign_dir) / "bundles"
    paths = sorted(folder.glob(f"{digest}.json")) + sorted(folder.glob(f"{digest}-*.json"))
    if not paths:
        raise BundleError("bundle.unreadable", f"{digest}.json: no bundle frozen with this digest")
    docs = []
    for path in paths:
        try:
            docs.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            raise BundleError("bundle.unreadable", f"{path.name}: {exc}") from None
    if config_hash is None:
        if len(docs) == 1:
            return docs[0]
        raise BundleError("bundle.ambiguous", f"{len(docs)} approval requests were frozen for {digest[:12]}; load with the configuration")
    for doc in docs:
        if (doc.get("approval_request") or {}).get("config_hash") == config_hash:
            return doc
    if len(docs) == 1 and (docs[0].get("approval_request") or {}).get("config_hash") is None:
        return docs[0]  # frozen without a configuration hash (core-only use): bound to no configuration
    raise BundleError("bundle.request_differs", f"no bundle with digest {digest[:12]} was frozen with this configuration "
                      f"(hash {config_hash[:12]}); freeze it, and have the new request approved")
