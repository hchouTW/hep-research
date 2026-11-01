"""run, inspect and check --probe of the detector-simulation shared layer (TASK.md 9.6, 10.2-10.5, 11).

A module of detsim.py (docs/dev/detector-simulation/TASK.md). One flock lock per run_id held by this controller, a
unique staging folder per attempt (.pending/<run_id>.<nonce>/), one non-overwriting rename. The OS releases the lock
when its holder dies, so there is no liveness polling and no recover command. A success is unique per run_id
(runs/<run_id>/); failures are kept under failed/<run_id>-<UTC ms>-<nonce>/ and may accumulate.

run (TASK.md 10.2), stopping at the first failing step:
   1 file system on the allowlist (unsupported-fs, rejected)       8 leftovers moved to .pending/orphans/, reported
   2 --plan-digest (digest-mismatch, refused)                         (never signalled)
   3 rebuild comparison (plan-stale, refused)                       9 snapshot: inputs copied (or linked) into input/
   4 required guarantees vs the profile (refused)                      and hash-checked (input-changed, refused)
   5 runs/<run_id>/ exists: reused (or run-id-collision)           10 launch the backend (detsim_runner)
   6 flock the lock file; from here every exit passes step 13      11 collect (backend) and observables
   7 runs/<run_id>/ again under the lock                           12 commit: run record, fsync, no-replace rename
  13 release: write state finished and the terminal status into the lock record, fsync, unlock
Nothing in this module signals a process: the runner signals only its own unreaped child's group.

inspect never writes, signals or kills anything: --view state (committed, in-progress, stale, failures, reported
orphans with whether a process with that pid exists now, checked with ps), --view summary (results and observables
of runs/), --attempt ID (a failed attempt's completeness evidence).
"""
from __future__ import annotations

import sys

if __spec__ is None:  # run as a file (tests/skills/test_cli_robustness.py): a module of detsim.py, not a command
    if sys.argv[1:] in ([], ["--help"], ["-h"]):
        print((__doc__ or "detsim module").splitlines()[0] + "\nA module of detsim.py, not a command: "
              "python3 detsim.py --help")
        sys.exit(0)
    print('{"status": "rejected", "error_code": "usage", "message": "a module of detsim.py, not a command"}')
    sys.exit(2)

import csv  # noqa: E402
import datetime  # noqa: E402
import fcntl  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import platform  # noqa: E402
import shutil  # noqa: E402
import signal  # noqa: E402
import socket  # noqa: E402
import stat  # noqa: E402
import subprocess  # noqa: E402
import uuid  # noqa: E402
from pathlib import Path  # noqa: E402

from contracts import CONTRACTS_VERSION  # noqa: E402

import detsim_canonical as canonical  # noqa: E402
import detsim_plan as plan_layer  # noqa: E402
import detsim_platform as platform_calls  # noqa: E402
import detsim_profile as profiles  # noqa: E402
import detsim_runner as runner  # noqa: E402
import detsim_schemas as schemas  # noqa: E402
from detsim_plan import DetsimError  # noqa: E402

ADAPTER_VERSION = "0.2.0"
PLUGIN = Path(__file__).resolve().parents[3]
RECORD_NAME = "run.computational-run.json"
OBSERVABLE_COLUMNS = ("quantity", "unit", "value", "uncertainty_type", "uncertainty", "point_kind", "point",
                      "detector", "component", "labels", "source_sha256")
FS_ADVICE = "artifacts must lie on a local file system of the allowlist (TASK.md 6.2); NFS, CIFS, FUSE are refused"
HOOKS: dict = {}  # test hooks: "before_snapshot", "before_commit", "before_rename", "after_rename" (callables)


# ---------------------------------------------------------------- layout

def store_root(workspace: Path) -> Path:
    return plan_layer.artifacts_root(workspace) / plan_layer.ADAPTER_FOLDER


def _utc_ms() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")[:-3] + "Z"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")


# ---------------------------------------------------------------- step 1: file system

def check_filesystem(store: Path) -> str:
    store.mkdir(parents=True, exist_ok=True)
    kind = platform_calls.filesystem_type(store)
    allowed = platform_calls.LOCAL_FILESYSTEMS.get(platform_calls.platform_key(), frozenset())
    if kind not in allowed:
        raise DetsimError("rejected", "unsupported-fs", f"the artifacts folder is on file system {kind!r}; "
                          + FS_ADVICE, str(store), filesystem=kind, allowed=sorted(allowed))
    return kind


# ---------------------------------------------------------------- lock record (steps 6, 13)

class RunLock:
    """The persistent lock file .pending/<run_id>.lock holding this attempt's record (close-on-exec, never inherited
    by the backend). acquire() reads the previous record first, then writes this controller's."""

    def __init__(self, path: Path):
        self.path, self.fd, self.previous, self.record = path, None, None, {}

    def acquire(self, record: dict) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            return False
        self.fd = fd
        raw = b""
        while chunk := os.read(fd, 1 << 16):
            raw += chunk
        self.previous = self._parse(raw)
        self.write(record)
        return True

    @staticmethod
    def _parse(raw: bytes):
        if not raw.strip():
            return None
        try:
            doc = json.loads(raw)
            return doc if isinstance(doc, dict) else {"unreadable": True}
        except ValueError:
            return {"unreadable": True}

    def write(self, record: dict) -> None:
        self.record = dict(record)
        serialized = json.dumps(self.record, indent=1, sort_keys=True).encode("utf-8")
        os.lseek(self.fd, 0, os.SEEK_SET)
        os.ftruncate(self.fd, 0)
        os.write(self.fd, serialized)
        os.fsync(self.fd)

    def update(self, **fields) -> None:
        self.write(dict(self.record, **fields))

    def release(self, **fields) -> None:
        if self.fd is None:
            return
        try:
            self.update(**fields)
        finally:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


def read_lock_state(path: Path) -> dict:
    """inspect's view of a lock file: held (another controller), stale (free, record unfinished) or idle."""
    if not path.is_file():
        return {"lock": "none"}
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            held = True
        else:
            held = False
            fcntl.flock(fd, fcntl.LOCK_UN)
        raw = path.read_bytes()
    finally:
        os.close(fd)
    record = RunLock._parse(raw) or {}
    state = "in-progress" if held else ("stale" if record.get("state") not in (None, "finished") else "idle")
    return {"lock": state, "record": record}


def _process_exists(pid) -> bool | None:
    """Whether a process with this pid exists now (ps; never a signal). Shown, never acted on."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        out = subprocess.run(["ps", "-p", str(pid), "-o", "pid="], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() == str(pid)


# ---------------------------------------------------------------- step 8: leftovers

def move_leftovers(pending: Path, run_id: str, previous) -> list[dict]:
    """Move every .pending/<run_id>.<nonce>/ folder to .pending/orphans/; report the previous unfinished record."""
    reported = []
    if previous is not None and previous.get("state") != "finished":
        if previous.get("unreadable"):
            reported.append({"previous_attempt": "unknown (unreadable lock record)"})
        else:
            reported.append({k: previous.get(k) for k in ("nonce", "host", "controller_pid", "pid", "pgid",
                                                           "started", "state")})
    orphans = pending / "orphans"
    for folder in sorted(pending.glob(f"{run_id}.*")):
        if not folder.is_dir():
            continue
        nonce = folder.name[len(run_id) + 1:]
        orphans.mkdir(parents=True, exist_ok=True)
        target = orphans / f"{run_id}-{nonce}"
        os.rename(folder, target)
        reported.append({"moved": f".pending/orphans/{target.name}", "nonce": nonce})
    return reported


# ---------------------------------------------------------------- step 9: snapshot

def _readonly(path: Path) -> None:
    os.chmod(path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def snapshot_inputs(plan: dict, workspace: Path, attempt: Path) -> dict:
    """Copy (or link) each input into attempt/input/ and check its hash against the plan; returns isolation facts."""
    threshold = plan["profile"]["policy"]["input_copy_threshold_bytes"]
    facts = {"input_isolation": "hard", "linked": [], "in_place": []}
    root = Path(workspace).resolve()
    for item in plan["inputs"]:
        source = root.joinpath(*item["path"].split("/"))
        target = attempt / "input" / Path(*item["path"].split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        size = source.stat().st_size
        if size <= threshold:
            shutil.copyfile(source, target)
        else:
            try:
                os.link(source, target)
                facts["linked"].append(item["path"])
            except OSError:
                facts["in_place"].append(item["path"])
                target = source
            facts["input_isolation"] = "soft"
        actual = plan_layer.sha256_file(target)[1]
        if actual != item["sha256"]:
            raise DetsimError("refused", "input-changed", f"input {item['path']!r} differs from the plan "
                              "(hash); run prepare again", "$.inputs", path=item["path"], expected=item["sha256"],
                              actual=actual)
        if target != source:
            _readonly(target)
    return facts


def write_rendered_files(spec: dict, attempt: Path) -> None:
    import base64
    for item in spec.get("files", []):
        target = attempt.joinpath(*item["path"].split("/")[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(item["content"]))


def input_hashes_after(plan: dict, workspace: Path, attempt: Path, facts: dict) -> list[str]:
    changed = []
    for item in plan["inputs"]:
        where = (Path(workspace).resolve().joinpath(*item["path"].split("/")) if item["path"] in facts["in_place"]
                 else attempt / "input" / Path(*item["path"].split("/")))
        if not where.is_file() or plan_layer.sha256_file(where)[1] != item["sha256"]:
            changed.append(item["path"])
    return changed


# ---------------------------------------------------------------- step 12: records and commit

def _relative_files(folder: Path) -> list[str]:
    out = []
    for base, _dirs, names in os.walk(folder):
        for name in names:
            out.append(Path(base, name).relative_to(folder).as_posix())
    return sorted(out)


def observables_csv(doc: dict) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(OBSERVABLE_COLUMNS)
    for row in doc.get("rows", []):
        writer.writerow([";".join(row[c]) if c == "labels" else row.get(c, "") for c in OBSERVABLE_COLUMNS])
    return buffer.getvalue()


def _seeds(plan: dict) -> dict:
    found = {k: v for k, v in plan["task"]["parameters"].items() if k in ("seed", "random_seed")}
    return found or {"none": "no random number generator: the capability is deterministic; no seed is invented"}


def run_record(plan: dict, plan_digest: str, replicate: int, ok: bool, facts: dict, folder_rel: str,
               output_hashes: dict, sidecars: list) -> dict:
    from contracts import trace
    from contracts.identity import plugin_release
    plugin_version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    run_digest = canonical.run_digest(plan_digest, replicate)
    labels = ["unvalidated"] if ok else ["failed", "unvalidated"]
    for label in plan["task"].get("labels", []):
        labels.insert(0, label)
    spec = plan["execution"]
    return {
        "contract_version": CONTRACTS_VERSION, "artifact_id": f"detsim-{run_digest[:32]}" + ("" if ok else
                                                                                          f"-{facts['nonce']}"),
        "artifact_type": "computational-run",
        "objective": f"detsim {plan['capability']['id']} {plan['capability']['version']} on backend "
                     f"{plan['capability']['backend']}: {plan['task']['objective']} (a completed run is verification "
                     "at most, never physical validity)",
        "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": plugin_version, "contracts": CONTRACTS_VERSION, "profiles": {},
                     "plugin_release": plugin_release()},
        "provenance": {"producer_skill": "hep-detector", **trace.provenance(),
                       "created": datetime.date.today().isoformat(), "evidence_ids": []},
        "inputs": [], "outputs": [], "status": list(dict.fromkeys(labels)), "unresolved_inputs": [],
        "extension": {
            "input_manifest": [{"path": "input/" + i["path"], "sha256": i["sha256"], "role": i["role"],
                                "size": i["size"]} for i in plan["inputs"]],
            "tools": [{"name": plan["capability"]["backend"], "version": plan["capability"]["version"],
                       "capability": plan["capability"]["id"]},
                      {"name": "detsim (adapters/detector-simulation)", "version": ADAPTER_VERSION}],
            "commands": [" ".join(spec["argv"])], "argv": list(spec["argv"]),
            "environment": {"env_identity": plan["environment"]["env_identity"],
                            "variables": sorted(spec.get("environment", {}))},
            "seeds": _seeds(plan), "tolerances": {}, "exit_status": 0 if ok else 1,
            "output_hashes": output_hashes, "parameter_digest": run_digest,
            "sidecars": sidecars,
            "detsim": {"plan_digest": plan_digest, "run_id": canonical.run_id(plan_digest, replicate),
                       "replicate": replicate, "profile": plan["profile"]["id"],
                       "declared_guarantees": plan["profile"]["guarantees"],
                       "achieved_guarantees": facts.get("achieved", {}), "folder": folder_rel,
                       "native_exit_code": facts.get("native_exit_code"), "signal": facts.get("signal"),
                       "end": facts.get("end"), "error_code": facts.get("error_code"),
                       "duration_s": facts.get("duration_s"), "peak_rss_kib": facts.get("peak_rss_kib"),
                       "nonce": facts["nonce"], "host": socket.gethostname(), "python": platform.python_version(),
                       "orphans_reported": facts.get("orphans_reported", []),
                       "input_isolation": facts.get("input_isolation"),
                       "workflow_attempt": os.environ.get(runner.WORKFLOW_TOKEN)}},
    }


def _fsync_tree(folder: Path) -> None:
    for name in _relative_files(folder):
        platform_calls.fsync_file(folder / name)
    dirs = sorted({p for p in folder.rglob("*") if p.is_dir()}, key=lambda p: len(p.parts), reverse=True)
    for d in dirs:
        platform_calls.fsync_dir(d)
    platform_calls.fsync_dir(folder)


def finish_folder(attempt: Path, store: Path, plan: dict, plan_digest: str, replicate: int, ok: bool, facts: dict,
                  completeness: dict, observables_doc: dict | None, final_rel: str) -> None:
    """Write completeness, observables, manifests and the run record into the attempt folder (committed_folder paths)."""
    (attempt / "plan.canonical.json").write_bytes(canonical.canonical_bytes(plan))
    (attempt / "completeness.json").write_text(json.dumps(completeness, indent=1, sort_keys=True), encoding="utf-8")
    if observables_doc is not None:
        (attempt / "observables.csv").write_text(observables_csv(observables_doc), encoding="utf-8")
    manifests = attempt / "manifests"
    manifests.mkdir(exist_ok=True)
    (manifests / "inputs.json").write_text(json.dumps(plan["inputs"], indent=1, sort_keys=True), encoding="utf-8")
    files = [f for f in _relative_files(attempt) if f != RECORD_NAME and f != "manifests/outputs.json"]
    output_hashes = {f: plan_layer.sha256_file(attempt / f)[1] for f in files if not f.startswith("input/")}
    (manifests / "outputs.json").write_text(json.dumps(output_hashes, indent=1, sort_keys=True), encoding="utf-8")
    output_hashes["manifests/outputs.json"] = plan_layer.sha256_file(manifests / "outputs.json")[1]
    sidecars = sorted(f"{final_rel}/{f}" for f in list(output_hashes) if f.endswith(".json"))
    sidecars += sorted(f"{final_rel}/{f}" for f in files if f.startswith("input/") and f.endswith(".json"))
    record = run_record(plan, plan_digest, replicate, ok, facts, final_rel, output_hashes, sidecars)
    (attempt / RECORD_NAME).write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")


def commit(attempt: Path, target: Path, profile_doc: dict, success: bool = True) -> str:
    """Steps 12.2-12.6: fsync, then a no-replace rename; returns the commit_noreplace level achieved.
    FileExistsError when the target exists (commit-conflict)."""
    _fsync_tree(attempt)
    target.parent.mkdir(parents=True, exist_ok=True)
    if success and "before_rename" in HOOKS:
        HOOKS["before_rename"](attempt, target)
    if platform_calls.rename_noreplace(attempt, target):
        level = "hard"
    else:  # no no-replace call here: check then rename under the lock (only detsim controllers are in the model)
        if target.exists():
            raise FileExistsError(str(target))
        os.rename(attempt, target)
        level = "soft"
    platform_calls.fsync_dir(attempt.parent)
    platform_calls.fsync_dir(target.parent)
    return min(level, profile_doc["guarantees"].get("commit_noreplace", "unsupported"), key=profiles.LEVELS.index)


# ---------------------------------------------------------------- run

class _MaskSignals:
    """Commit: SIGINT and SIGTERM are recorded and do not change the terminal state (TASK.md 10.3)."""

    def __init__(self):
        self.received, self._old = [], {}

    def __enter__(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                self._old[sig] = signal.signal(sig, lambda s, f: self.received.append(signal.Signals(s).name))
            except ValueError:
                pass
        return self

    def __exit__(self, *exc):
        for sig, old in self._old.items():
            signal.signal(sig, old)
        return False


def _achieved(profile_doc: dict, facts: dict) -> dict:
    achieved = dict(profile_doc["guarantees"])
    if facts.get("input_isolation") == "soft":
        achieved["inputs_isolated"] = "soft"
    return achieved


def run(plan: dict, workspace: Path, backend, profile_doc: dict, replicate: int, expected_digest: str | None,
        assets_dir: Path | None = None) -> dict:
    """detsim run (TASK.md 10.2). Returns the JSON answer; raises DetsimError for refusals before the lock."""
    from core import hostcaps
    store = store_root(workspace)
    check_filesystem(store)                                                     # step 1
    plan_digest = plan_layer.check_plan_digest(plan, expected_digest)           # step 2
    plan_layer.rebuild_comparison(plan, workspace, backend, profile_doc, assets_dir)  # step 3
    short = profiles.shortfalls(plan["capability"]["required_guarantees"], profile_doc)  # step 4
    if short:
        raise DetsimError("refused", "guarantee-insufficient", "the runner profile does not meet the capability's "
                          "required guarantees; refused, never downgraded", "$.capability.required_guarantees",
                          shortfalls=short)
    hostcaps.require("process_groups")  # step 10's precondition, checked before the lock (missing-dependency)
    run_id = canonical.run_id(plan_digest, replicate)
    committed_folder = store / "runs" / run_id
    reused = _reuse(committed_folder, plan_digest, run_id)                                 # step 5
    if reused:
        return reused
    pending = store / ".pending"
    nonce = uuid.uuid4().hex[:16]
    lock = RunLock(pending / f"{run_id}.lock")
    record = {"host": socket.gethostname(), "controller_pid": os.getpid(), "nonce": nonce, "started": _now(),
              "budget_timeout_s": plan["execution"]["timeout_s"], "state": "preparing", "run_id": run_id}
    if not lock.acquire(record):                                                # step 6
        held = read_lock_state(pending / f"{run_id}.lock").get("record", {})
        raise DetsimError("incomplete", "in-progress", "another detsim controller holds this run's lock",
                          run_id=run_id, holder={k: held.get(k) for k in ("host", "controller_pid", "started",
                                                                           "budget_timeout_s")})
    terminal = {"status": "error", "error_code": "internal"}
    try:
        answer = _locked_run(plan, plan_digest, replicate, run_id, nonce, workspace, store, pending, committed_folder, backend,
                             profile_doc, lock)
        terminal = {"status": answer["status"], "error_code": answer.get("error_code"),
                    "reused": answer.get("reused", False)}
        return answer
    finally:                                                                    # step 13
        lock.release(state="finished", finished=_now(), terminal=terminal)


def _reuse(committed_folder: Path, plan_digest: str, run_id: str) -> dict | None:
    canonical_plan = committed_folder / "plan.canonical.json"
    if not committed_folder.exists():
        return None
    try:
        existing = canonical.digest(canonical.load_json_strict(canonical_plan.read_bytes()))
    except (OSError, canonical.CanonicalError):
        existing = None
    if existing != plan_digest:
        raise DetsimError("refused", "run-id-collision", "runs/<run_id>/ exists with another plan; nothing is "
                          "overwritten", str(committed_folder), run_id=run_id)
    return {"status": "ok", "reused": True, "run_id": run_id, "folder": f"runs/{run_id}"}


def _locked_run(plan, plan_digest, replicate, run_id, nonce, workspace, store, pending, committed_folder, backend, profile_doc,
                lock) -> dict:
    reused = _reuse(committed_folder, plan_digest, run_id)                                 # step 7
    if reused:
        return reused
    orphans = move_leftovers(pending, run_id, lock.previous)                    # step 8
    attempt = pending / f"{run_id}.{nonce}"
    attempt.mkdir(parents=True)
    facts = {"nonce": nonce, "orphans_reported": orphans}
    spec = plan["execution"]
    if "before_snapshot" in HOOKS:
        HOOKS["before_snapshot"](attempt)
    try:
        facts.update(snapshot_inputs(plan, workspace, attempt))                 # step 9
    except DetsimError:
        shutil.rmtree(attempt, ignore_errors=True)
        raise
    except OSError as err:
        facts.update(end="snapshot-failed", error_code="snapshot-io")
        return _fail(plan, plan_digest, replicate, attempt, store, run_id, facts, profile_doc,
                     {"schema": "detsim-completeness/1", "state": "invalid", "missing_outputs": [],
                      "evidence": [{"check": "snapshot", "result": "fail", "detail": str(err)}]})
    write_rendered_files(spec, attempt)
    env_root = _env_root(workspace, plan)
    roots = {"ENV_ROOT": env_root, "INPUT_ROOT": attempt / "input", "ATTEMPT_ROOT": attempt}
    lock.update(state="running")
    launched = runner.launch(spec, roots, plan["task"]["budget"]["max_output_bytes"], profile_doc["id"],
                             on_start=lambda pid, pgid: lock.update(state="running", pid=pid, pgid=pgid))  # step 10
    facts.update({k: launched[k] for k in ("native_exit_code", "signal", "end", "duration_s", "peak_rss_kib",
                                           "launch_error", "terminated_by_controller", "interruptions")})
    changed = input_hashes_after(plan, workspace, attempt, facts)
    facts["achieved"] = _achieved(profile_doc, facts)
    if changed:
        facts["achieved"]["inputs_unmodified"] = "unsupported"
    if launched["end"] == "launch-failed":
        facts["error_code"] = "missing-dependency"
    elif launched["end"] == "cancelled":
        facts["error_code"] = "cancelled"
    elif launched["end"] in ("timeout", "output-exceeded", "signalled"):
        facts["error_code"] = launched["end"]
    elif changed:
        facts["error_code"] = "input-modified"
    completeness = backend.collect(attempt, spec)                               # step 11
    completeness = dict(completeness, run_id=run_id, native_exit_code=launched["native_exit_code"])
    if launched["native_exit_code"] not in (0, None) and not facts.get("error_code"):
        facts["error_code"] = "backend-failed"
    if facts.get("error_code") or completeness.get("state") != "complete":
        facts.setdefault("error_code", None)
        facts["error_code"] = facts["error_code"] or f"collect-{completeness.get('state')}"
        return _fail(plan, plan_digest, replicate, attempt, store, run_id, facts, profile_doc, completeness)
    observables_doc = dict(backend.observables(attempt, spec), run_id=run_id)
    problems = schemas.check_completeness(completeness) + schemas.check_observables(observables_doc)
    if problems:
        facts["error_code"] = "output-contract"
        facts["contract_findings"] = problems[:20]
        return _fail(plan, plan_digest, replicate, attempt, store, run_id, facts, profile_doc, completeness)
    final_rel = f"detector-simulation/runs/{run_id}"
    with _MaskSignals() as masked:                                              # step 12
        finish_folder(attempt, store, plan, plan_digest, replicate, True, facts, completeness, observables_doc,
                      final_rel)
        if "before_commit" in HOOKS:
            HOOKS["before_commit"](attempt)
        try:
            level = commit(attempt, committed_folder, profile_doc)
        except FileExistsError:
            facts["error_code"] = "commit-conflict"
            return _fail(plan, plan_digest, replicate, attempt, store, run_id, facts, profile_doc, completeness)
        if "after_rename" in HOOKS:
            HOOKS["after_rename"](committed_folder)
    answer = {"status": "ok", "reused": False, "run_id": run_id, "folder": f"runs/{run_id}",
              "plan_digest": plan_digest, "replicate": replicate, "commit_noreplace": level,
              "achieved_guarantees": facts["achieved"], "signals_during_commit": masked.received,
              "observables": len(observables_doc.get("rows", []))}
    if orphans:
        answer["orphans_reported"] = orphans
    return answer


def _env_root(workspace: Path, plan: dict) -> Path:
    path = plan_layer.env_record_path(plan_layer.artifacts_root(workspace), plan["environment"]["env_identity"])
    doc = canonical.load_json_strict(path.read_bytes())
    root = (doc.get("path_record") or {}).get("env_root")
    if not isinstance(root, str) or not Path(root).is_dir():
        raise DetsimError("refused", "environment-root-missing", "the environment record names no existing "
                          "environment root (path_record.env_root); validate the environment with check --probe",
                          "$.environment_ref", record=str(path))
    return Path(root)


def _fail(plan, plan_digest, replicate, attempt, store, run_id, facts, profile_doc, completeness) -> dict:
    """Commit the attempt to failed/<run_id>-<UTC ms>-<nonce>/ with the failed label (TASK.md 10.3 step 5)."""
    name = f"{run_id}-{_utc_ms()}-{facts['nonce']}"
    final_rel = f"detector-simulation/failed/{name}"
    facts.setdefault("achieved", _achieved(profile_doc, facts))
    with _MaskSignals():
        finish_folder(attempt, store, plan, plan_digest, replicate, False, facts, completeness, None, final_rel)
        target = store / "failed" / name
        try:
            commit(attempt, target, profile_doc, success=False)
        except FileExistsError:  # a unique nonce makes this practically impossible; keep the attempt, say so
            raise DetsimError("error", "internal", "the failed/ folder name already exists; the attempt stays in "
                              ".pending/", str(target), reason="failed-folder-exists") from None
    return {"status": "failed", "error_code": facts.get("error_code") or "failed", "run_id": run_id,
            "folder": f"failed/{name}", "native_exit_code": facts.get("native_exit_code"),
            "signal": facts.get("signal"), "end": facts.get("end"), "completeness": completeness.get("state"),
            "orphans_reported": facts.get("orphans_reported", [])}


# ---------------------------------------------------------------- inspect

def inspect(workspace: Path, run_id: str | None, view: str, attempt_id: str | None) -> dict:
    store = store_root(workspace)
    if attempt_id is not None:
        folder = store / "failed" / attempt_id
        if not (folder / "completeness.json").is_file() or "/" in attempt_id or attempt_id.startswith("."):
            raise DetsimError("rejected", "attempt-unknown", f"no failed attempt {attempt_id!r}", "--attempt")
        return {"status": "ok", "attempt": attempt_id,
                "completeness": json.loads((folder / "completeness.json").read_text(encoding="utf-8"))}
    if view == "summary":
        runs = []
        for folder in sorted((store / "runs").glob("*")) if (store / "runs").is_dir() else []:
            if run_id and folder.name != run_id:
                continue
            record_path = folder / RECORD_NAME
            if not record_path.is_file():
                continue
            ext = json.loads(record_path.read_text(encoding="utf-8"))["extension"]
            rows = list(csv.DictReader(io.StringIO((folder / "observables.csv").read_text(encoding="utf-8"))))
            runs.append({"run_id": folder.name, "plan_digest": ext["detsim"]["plan_digest"],
                         "replicate": ext["detsim"]["replicate"], "observables": rows})
        return {"status": "ok", "view": "summary", "runs": runs}
    if run_id is None:
        raise DetsimError("rejected", "usage", "--view state needs --run", "--run")
    lock_state = read_lock_state(store / ".pending" / f"{run_id}.lock")
    record = lock_state.get("record", {})
    failures = sorted(p.name for p in (store / "failed").glob(f"{run_id}-*")) if (store / "failed").is_dir() else []
    committed = (store / "runs" / run_id / RECORD_NAME).is_file()
    state = "committed" if committed else lock_state["lock"] if lock_state["lock"] in ("in-progress", "stale") \
        else ("failed-only" if failures else "none")
    orphans = []
    for entry in record.get("orphans_seen", []) + ([record] if lock_state["lock"] == "stale" else []):
        orphans.append({k: entry.get(k) for k in ("pid", "pgid", "started", "nonce")}
                       | {"process_with_that_pid_exists_now": _process_exists(entry.get("pid"))})
    answer = {"status": "ok", "view": "state", "run_id": run_id, "state": state, "failures": len(failures),
              "failed_attempts": failures, "orphans": orphans,
              "orphan_folders": sorted(p.name for p in (store / ".pending" / "orphans").glob(f"{run_id}-*"))
              if (store / ".pending" / "orphans").is_dir() else []}
    if state == "in-progress":
        answer["holder"] = {k: record.get(k) for k in ("host", "controller_pid", "started", "budget_timeout_s")}
    return answer


# ---------------------------------------------------------------- check --probe

def probe(workspace: Path, backend, env_root: Path) -> dict:
    """Capture and validate a backend environment; write artifacts_root/detector-simulation/.env/<id>.json."""
    env_root = Path(env_root).resolve()
    if not env_root.is_dir():
        raise DetsimError("rejected", "env-root-missing", f"--env-root {str(env_root)!r} is not a folder", "--env-root")
    facts = backend.probe(env_root)  # may raise DetsimError (missing-dependency) before anything is written
    identity, variables = facts["identity"], facts["variables"]
    problems = canonical.check_hash_scope({"identity": identity, "variables": variables})
    problems += [dict(f, path=f["path"]) for f in schemas.host_path_findings(
        (f"variables.{n}", v) for n, v in sorted(variables.items()))]
    problems += [{"path": f"variables.{n}", "code": "variable-name"} for n, v in variables.items()
                 if schemas.ENV_NAME.fullmatch(n) is None or not isinstance(v, str)]
    if problems:  # validate before writing: prepare would refuse such a record (environment-record-invalid)
        raise DetsimError("refused", "environment-invalid", "the captured environment cannot be recorded: "
                          + "; ".join(f"{i['path']}: {i['code']}" for i in problems[:5]), "--env-root",
                          problems=problems[:20])
    manifest = _environment_manifest(env_root, variables)
    record = plan_layer.env_record(identity, variables, facts=facts.get("facts", {}),
                                   path_record={"env_root": str(env_root), "environment_manifest": manifest})
    path = plan_layer.env_record_path(plan_layer.artifacts_root(workspace), record["env_identity"])
    path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = path.with_suffix(".json.tmp")
    partial_path.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(partial_path, path)
    return {"status": "ok", "env_identity": record["env_identity"], "record": f".env/{path.name}",
            "identity": identity, "variables": sorted(variables)}


def _environment_manifest(env_root: Path, variables: dict) -> dict:
    """skills/hep-computing/scripts/environment_manifest.py record, run as a subprocess with the captured
    environment (adapters may not import skills); the path-bearing record, outside the hash scope."""
    script = PLUGIN / "skills" / "hep-computing" / "scripts" / "environment_manifest.py"
    env = {name: runner.bind(value, {"ENV_ROOT": env_root, "INPUT_ROOT": env_root, "ATTEMPT_ROOT": env_root})
           for name, value in variables.items()}
    env.setdefault("PATH", os.environ.get("PATH", ""))
    env["PATH"] = env["PATH"] + os.pathsep + os.path.dirname(sys.executable)
    try:
        out = subprocess.run([sys.executable, "-I", str(script), "record", "--packages", "pip"],
                             capture_output=True, text=True, env=env, timeout=120)
        return json.loads(out.stdout) if out.stdout.strip().startswith("{") else {"status": "error",
                                                                                   "stderr": out.stderr[-400:]}
    except (OSError, subprocess.SubprocessError, ValueError) as err:
        return {"status": "error", "message": str(err)}
