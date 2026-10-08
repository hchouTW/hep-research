"""Slurm backend: one job array per submission, accounting-based polling, no scheduler-side requeue.

prepare  renders assets/slurm-array.sbatch.template: --array=0-(n-1)[%throttle], --no-requeue, resources and site
         keys only from the configuration; the job runs the campaign's runner with the array index, which the
         runner maps to a chunk through the submission map (map.json) written with the script.
submit   sbatch --parsable --output=<logs>/%A_%a.stdout.log --error=<logs>/%A_%a.stderr.log job.sbatch
poll     sacct --jobs=<ids> --duplicates --parsable2 --noheader --format=JobID,State,ExitCode,Elapsed,MaxRSS,NodeList
         (ExitCode is "exit:signal"; MaxRSS is taken from the job steps). If sacct fails, squeue plus the runner's
         meta files are used and the evidence is marked 'queue+outputs'; a task in neither is 'lost'.
cancel   scancel <job>_<index>
Every option, field and state code here is listed with its documentation source in
skills/hep-computing/references/batch-scheduling.md (tool facts table).
"""
from __future__ import annotations

import datetime
import json
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.partition.executors import Executor, PollError, SubmitAmbiguous, _blank  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent / "assets" / "slurm-array.sbatch.template"
SACCT_FIELDS = "JobID,State,ExitCode,Elapsed,MaxRSS,NodeList"
STATES = {  # native State (first word; "CANCELLED by 123" -> CANCELLED) -> normalized
    "PENDING": "queued", "CONFIGURING": "queued", "REQUEUED": "queued", "REQUEUE_FED": "queued",
    "RUNNING": "running", "COMPLETING": "running", "STAGE_OUT": "running", "RESIZING": "running",
    "COMPLETED": "done", "FAILED": "failed", "TIMEOUT": "timeout", "OUT_OF_MEMORY": "out-of-memory",
    "CANCELLED": "cancelled", "NODE_FAIL": "node-failure", "BOOT_FAIL": "node-failure", "PREEMPTED": "preempted-or-evicted",
    "REQUEUE_HOLD": "held", "SPECIAL_EXIT": "held", "RESV_DEL_HOLD": "held",
    "SIGNALING": "running",
    # suspended or stopped: as for HTCondor's suspend event, the plugin has no rule for it, a person decides
    "SUSPENDED": "unknown", "STOPPED": "unknown",
    # DEADLINE: ended by a --deadline the adapter never sets; REVOKED: a federation sibling removed
    "DEADLINE": "failed", "REVOKED": "cancelled",
}
TASK = re.compile(r"^(\d+)_(\d+)$")
PENDING_RANGE = re.compile(r"^(\d+)_\[(.+)\]$")


def native(state: str) -> str:
    return (state or "").split()[0].rstrip("+") if state else ""


def mapped(state: str) -> str:
    return STATES.get(native(state), "unknown")


def parse_exit(text: str) -> tuple[int | None, int | None]:
    m = re.fullmatch(r"(\d+):(\d+)", text or "")
    if not m:
        raise ValueError(f"ExitCode {text!r} is not exit:signal")
    code, sig = int(m.group(1)), int(m.group(2))
    return code, (sig or None)


def parse_elapsed(text: str) -> float | None:
    m = re.fullmatch(r"(?:(\d+)-)?(?:(\d+):)?(\d+):(\d+)(?:\.\d+)?", text or "")
    if not m:
        return None
    d, h, mi, s = (int(g) if g else 0 for g in m.groups())
    return float(((d * 24 + h) * 60 + mi) * 60 + s)


def parse_rss_mb(text: str) -> float | None:
    m = re.fullmatch(r"([\d.]+)([KMGT]?)", (text or "").strip())
    if not m:
        return None
    return float(m.group(1)) * {"": 1 / 2**20, "K": 1 / 1024, "M": 1, "G": 1024, "T": 1024**2}[m.group(2)]


def expand_range(spec: str) -> list[int]:
    out = []
    for part in spec.split("%")[0].split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


class SlurmExecutor(Executor):
    name = "slurm"

    def __init__(self, config: dict, env: dict | None = None):
        super().__init__(env, config)
        self.config = config

    def prepare(self, ctx: dict) -> dict:
        cfg, res, site = self.config, self.config.get("resources", {}), self.config.get("slurm", {})
        n = len(ctx["rows"])
        array = f"0-{n - 1}" + (f"%{cfg['throttle']}" if cfg.get("throttle") else "")
        lines = [f"#SBATCH --partition={site['partition']}"]
        for key, opt in (("account", "account"), ("qos", "qos"), ("constraint", "constraint"), ("gres", "gres")):
            if key in site:
                lines.append(f"#SBATCH --{opt}={site[key]}")
        lines.append(f"#SBATCH --time={res['time_limit']}")
        if "cpus" in res:
            lines.append(f"#SBATCH --cpus-per-task={res['cpus']}")
        if "memory_mb" in res:
            lines.append(f"#SBATCH --mem={res['memory_mb']}M")
        if res.get("gpus"):
            lines.append(f"#SBATCH --gpus={res['gpus']}")
        if "disk_mb" in res:
            lines.append(f"#SBATCH --tmp={res['disk_mb']}M")
        sub = Path(ctx["submission_dir"])
        q = shlex.quote
        wp = cfg.get("worker_python")
        path_line = f"export PATH={q(str(Path(wp).parent))}:/usr/bin:/bin\n" if wp else ""
        values = {"submission_id": ctx["submission_id"], "job_name": ctx.get("tag") or cfg.get("job_name", "hep-partition"),
                  "array": array, "path_line": path_line,
                  "resource_lines": "\n".join(lines), "worker_python": q(wp or "python3"),
                  "runner": q(str(ctx["runner"])), "spec": q(str(ctx["spec"])), "map": q(str(sub / "map.json")),
                  "outputs": q(str(ctx["outputs_dir"]))}
        text = TEMPLATE.read_text(encoding="utf-8")
        for k, v in values.items():
            text = text.replace("{{" + k + "}}", str(v))
        argv = ["sbatch", "--parsable", f"--output={sub / 'logs'}/%A_%a.stdout.log", f"--error={sub / 'logs'}/%A_%a.stderr.log",
                str(sub / "job.sbatch")]
        return {"backend": self.name, "submission_id": ctx["submission_id"], "submission_dir": str(sub),
                "files": {"job.sbatch": text, "map.json": json.dumps(ctx["rows"], indent=1) + "\n"},
                "submit_argv": argv, "rows": ctx["rows"]}

    def submit(self, plan: dict) -> list[dict]:
        p = self.run_submit(plan["submit_argv"], cwd=plan["submission_dir"])
        first = (p.stdout.strip().splitlines() or [""])[0]
        job = first.split(";")[0]
        if p.returncode != 0 or not job.isdigit():  # sbatch ran: the scheduler may still have queued the array
            raise SubmitAmbiguous("slurm.sbatch.failed", f"exit {p.returncode}: {(p.stderr or p.stdout).strip()[-500:]}")
        return [{"attempt_id": r["attempt_id"], "job_id": f"{job}_{r['index']}"} for r in plan["rows"]]

    def poll(self, records: list[dict]) -> dict:
        jobs = sorted({r["job_id"].split("_")[0] for r in records})
        p = self.run_poll(["sacct", f"--jobs={','.join(jobs)}", "--duplicates", "--parsable2", "--noheader", f"--format={SACCT_FIELDS}"])
        if p.returncode != 0:
            return self._poll_queue(records, f"sacct exit {p.returncode}: {p.stderr.strip()[-300:]}")
        tasks: dict[str, list[dict]] = {}
        steps: dict[str, list[str]] = {}
        for line in p.stdout.splitlines():
            if not line.strip():
                continue
            f = line.split("|")
            if len(f) != 6:
                raise PollError("slurm.sacct.unparsable", f"expected 6 '|' fields: {line[:200]!r}")
            jid, state, exitc, elapsed, rss, nodes = f
            base, _, step = jid.partition(".")
            m, pr = TASK.match(base), PENDING_RANGE.match(base)
            if not (m or pr) or (pr and step):
                raise PollError("slurm.sacct.unparsable", f"unexpected JobID {jid!r}")
            if step:
                steps.setdefault(base, []).append(rss)
                continue
            try:
                code, sig = parse_exit(exitc)
            except ValueError as exc:
                raise PollError("slurm.sacct.unparsable", str(exc)) from None
            ids = [base] if m else [f"{pr.group(1)}_{i}" for i in expand_range(pr.group(2))]
            for t in ids:
                tasks.setdefault(t, []).append({"state": state, "code": code, "sig": sig, "elapsed": elapsed, "nodes": nodes})
        out, missing = {}, []
        for rec in records:
            hist = tasks.get(rec["job_id"])
            if not hist:
                missing.append(rec)
                continue
            last = hist[-1]
            rss = [parse_rss_mb(x) for x in steps.get(rec["job_id"], [])]
            rss = [x for x in rss if x is not None]
            out[rec["attempt_id"]] = _blank(
                state=mapped(last["state"]), native_state=last["state"], exit_code=last["code"], signal=last["sig"],
                host=last["nodes"] or None, elapsed_s=parse_elapsed(last["elapsed"]), max_rss_mb=max(rss) if rss else None,
                restarts=len(hist) - 1, evidence="accounting (sacct)")
        if missing:  # not in accounting (yet): ask the queue, then the runner's records, before calling it lost
            out.update(self._poll_queue(missing, "no accounting record for this array task"))
        return out

    def _poll_queue(self, records: list[dict], why: str) -> dict:
        jobs = sorted({r["job_id"].split("_")[0] for r in records})
        p = self.run_poll(["squeue", f"--jobs={','.join(jobs)}", "--array", "--noheader", "--format=%i|%T"])
        if p.returncode != 0:
            raise PollError("slurm.no_accounting_no_queue", f"{why}; squeue exit {p.returncode}: {p.stderr.strip()[-300:]}")
        queued = {}
        for line in p.stdout.splitlines():
            if not line.strip():
                continue
            f = line.strip().split("|")
            if len(f) != 2 or not TASK.match(f[0]):
                raise PollError("slurm.squeue.unparsable", f"unexpected line {line[:200]!r}")
            queued[f[0]] = f[1]
        out = {}
        for rec in records:
            ev = f"queue+outputs (accounting unavailable: {why})"
            if rec["job_id"] in queued:
                st = queued[rec["job_id"]]
                out[rec["attempt_id"]] = _blank(state=mapped(st), native_state=st, evidence=ev)
                continue
            meta = sorted(Path(rec.get("outputs_dir", "")).glob(f"{rec['attempt_id']}*.meta.json")) if rec.get("outputs_dir") else []
            if meta:
                m = json.loads(meta[-1].read_text(encoding="utf-8"))
                code = m.get("exit_code")
                out[rec["attempt_id"]] = _blank(state="done" if code == 0 else "failed", native_state="not in queue; runner meta file",
                                                exit_code=code, signal=m.get("signal"), host=m.get("host"), evidence=ev)
            else:
                out[rec["attempt_id"]] = _blank(state="lost", native_state="not in queue, no runner record", evidence=ev)
        return out

    def find(self, tag: str, since: str | None = None) -> list[dict]:
        """Read-only: array tasks the accounting lists under the job name tag (reconciliation)."""
        start = "now-7days"
        if since:  # recorded in UTC; sacct reads --starttime in the cluster's local time, so convert, with an hour's margin
            try:
                t = datetime.datetime.fromisoformat(since.replace("Z", "+00:00")) - datetime.timedelta(hours=1)
                start = t.astimezone().strftime("%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass
        p = self.run_poll(["sacct", f"--name={tag}", f"--starttime={start}", "--array", "-X", "--parsable2", "--noheader",
                           "--format=JobID,JobName,State"])
        if p.returncode != 0:
            raise PollError("slurm.sacct.failed", f"exit {p.returncode}: {p.stderr.strip()[-300:]}")
        out = []
        for line in p.stdout.splitlines():
            f = line.strip().split("|")
            if len(f) != 3:
                continue
            jid, name, state = f
            m, pr = TASK.match(jid), PENDING_RANGE.match(jid)
            if name != tag or not (m or pr):
                continue
            ids = [jid] if m else [f"{pr.group(1)}_{i}" for i in expand_range(pr.group(2))]
            out += [{"job_id": t, "state": mapped(state), "native_state": state} for t in ids]
        return out

    def cancel(self, records: list[dict]) -> list[dict]:
        out = []
        for r in records:
            argv = ["scancel", r["job_id"]]
            try:
                out.append({"argv": argv, "exit": self.run_poll(argv).returncode})
            except PollError as exc:  # a hung or missing client: recorded, the other jobs are still cancelled
                out.append({"argv": argv, "exit": None, "error": exc.signature})
        return out

    def version(self) -> str:
        try:
            p = self.run_poll(["sbatch", "--version"])
        except PollError as exc:
            return f"unknown ({exc.signature})"
        return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else f"unknown (sbatch --version exit {p.returncode})"
