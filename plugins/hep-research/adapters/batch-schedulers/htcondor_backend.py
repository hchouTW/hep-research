"""HTCondor backend: one cluster per submission, chunk IDs as queue item data, job-event-log polling.

prepare  renders assets/htcondor-chunks.sub.template: `queue chunk_id, attempt_id from items.txt`, so each process
         gets its chunk and attempt IDs directly; request_cpus / request_memory / request_disk / request_gpus,
         universe, container image, requirements, site attributes ("+Name = value", for example a site's run-time
         flavour) and file-transfer mode only from the configuration; a job event log; no max_retries, no
         exit-handling overrides. A configured schedd (a name, or the caller's _condor_SCHEDD_HOST) is written to
         schedd.txt next to the job file, and every condor_submit, condor_q, condor_history and condor_rm of that
         submission passes it as -name, so a campaign stays on its schedd when the site mapping changes later. Shared file system: the runner writes into the campaign's
         outputs/. File transfer: the runner writes into the job's scratch directory and transfer_output_remaps puts
         <attempt>.json and <attempt>.meta.json into outputs/<chunk>/ (the staging area collection reads).
submit   condor_submit [-name S] -terse job.sub   (prints "<cluster>.<first proc> - <cluster>.<last proc>"), run in
         the submission folder, which the relative items.txt needs; a dry run's copy is checked the same way, in
         dry-run/<id>/: condor_submit -dry-run - job.sub. Two failure texts are refusals (no cluster exists, the
         attempts become not-submitted): the credential step ("Failed to process job credential requests ... BAILING
         OUT") and a rejected transaction ("Failed to commit job submission into the queue"); any other failure is
         ambiguous until a person reconciles.
poll     the job event log first (it outlives the queue): submit 000, execute 001, executable error 002, evicted
         004, terminated 005 (return value or signal), shadow exception 007, aborted 009, held 012 (reason, Code,
         Subcode), released 013. A job the log still shows as queued or running is checked against condor_q and
         condor_history (-json); absent from both, it is 'lost'. Without a readable log, condor_q / condor_history
         JobStatus is used (1 idle, 2 running, 3 removing, 4 completed, 5 held, 6 transferring output, 7 suspended).
         A held job is reported with its reason and code and never released here.
cancel   condor_rm <cluster>.<proc>
Paths containing whitespace are refused (htcondor.path_whitespace): submit-description values are not quoted.
Every command, macro and code is listed with its documentation source in
skills/hep-computing/references/batch-scheduling.md (tool facts table).
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.partition.campaign import CampaignError  # noqa: E402
from core.partition.executors import Executor, PollError, SubmitAmbiguous, SubmitRefused, _blank  # noqa: E402

# condor_submit texts that end the call before a cluster exists (observed on HTCondor 24.12.16, CERN, 2026-10-10):
# the credential step failed (retry later), or the schedd rejected the transaction (fix the submit file).
REFUSED_BEFORE_QUEUE = (("Failed to process job credential requests", "htcondor.submit.credential"),
                        ("BAILING OUT", "htcondor.submit.credential"),
                        ("Failed to commit job submission into the queue", "htcondor.submit.rejected"))


def _classad(v) -> str:
    """A configured site attribute as ClassAd text: booleans unquoted, integers bare, strings double-quoted."""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v) if isinstance(v, int) else f'"{v}"'

TEMPLATE = Path(__file__).resolve().parent / "assets" / "htcondor-chunks.sub.template"
HEADER = re.compile(r"^(\d{3}) \((\d+)\.(-?\d+)\.(\d+)\) (\S+ \S+) ?(.*)$")  # proc -1: a cluster-level event (035, 036)
NORMAL = re.compile(r"Normal termination \(return value (\d+)\)")
ABNORMAL = re.compile(r"Abnormal termination \(signal (\d+)\)")
HOLD_CODE = re.compile(r"Code (\d+) Subcode (\d+)")
MEMORY = re.compile(r"^\s*Memory \(MB\)\s*:\s*(\d+)")
KNOWN_EVENTS = {f"{i:03d}" for i in range(0, 45)}
JOB_STATUS = {1: "queued", 2: "running", 3: "cancelled", 5: "held", 6: "running", 7: "unknown"}
ATTRS = "ClusterId,ProcId,JobStatus,HoldReason,HoldReasonCode,HoldReasonSubCode,ExitCode,ExitBySignal,ExitSignal,NumJobStarts"


def _time(text: str):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%y %H:%M:%S", "%m/%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_event_log(text: str) -> dict:
    """{(cluster, proc): observation} from a job event log; raises PollError on a malformed event header."""
    procs: dict = {}
    blocks = text.split("\n...\n")
    if not text.endswith("...\n"):
        blocks = blocks[:-1]  # the last event is still being written
    for block in blocks:
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        m = HEADER.match(lines[0])
        if not m or m.group(1) not in KNOWN_EVENTS:
            raise PollError("htcondor.eventlog.unparsable", f"unexpected event header {lines[0][:200]!r}")
        code, key, when, detail = m.group(1), (int(m.group(2)), int(m.group(3))), _time(m.group(5)), lines[1:]
        if key[1] < 0:  # "Cluster submitted" / "Cluster removed" (HTCondor 24.12): no process, nothing to observe
            continue
        o = procs.setdefault(key,{"state": "queued", "starts": 0, "native": [], "exit_code": None, "signal": None,
                                   "hold_reason": None, "hold_code": None, "host": None, "t_exec": None, "elapsed": None, "mem": None})
        o["native"].append(code)
        if code == "001":
            o.update(state="running", t_exec=when)
            o["starts"] += 1
            h = re.search(r"host: (\S+)", m.group(6))
            o["host"] = h.group(1) if h else None
        elif code in ("004", "007", "013"):
            o.update(state="queued", hold_reason=None, hold_code=None)
        elif code == "009":
            o["state"] = "cancelled"
        elif code == "012":
            hc = next((HOLD_CODE.search(l) for l in detail if HOLD_CODE.search(l)), None)
            o.update(state="held", hold_reason=detail[0].strip() if detail else None,
                     hold_code=f"{hc.group(1)}.{hc.group(2)}" if hc else None)
        elif code == "005":
            body = "\n".join(detail)
            n, a = NORMAL.search(body), ABNORMAL.search(body)
            if n:
                o.update(state="done" if int(n.group(1)) == 0 else "failed", exit_code=int(n.group(1)))
            elif a:
                o.update(state="failed", signal=int(a.group(1)))
            else:
                raise PollError("htcondor.eventlog.unparsable", f"terminated event without return value or signal: {body[:200]!r}")
            if when and o["t_exec"]:
                o["elapsed"] = (when - o["t_exec"]).total_seconds()
            mem = next((MEMORY.match(l) for l in detail if MEMORY.match(l)), None)
            o["mem"] = float(mem.group(1)) if mem else None
        elif code == "010":
            o["state"] = "unknown"  # suspended: the plugin has no rule for it, a person decides
        elif code == "011":
            o["state"] = "running"
    return procs


class HTCondorExecutor(Executor):
    name = "htcondor"

    def __init__(self, config: dict, env: dict | None = None):
        super().__init__(env, config)
        self.config = config
        want = config.get("htcondor", {}).get("schedd")
        caller = os.environ if env is None else env  # read before the allow-list: the name, never the variable, is kept
        self.schedd = caller.get("_condor_SCHEDD_HOST") if want == "caller" else want
        self._schedd_unresolved = want == "caller" and not self.schedd

    @staticmethod
    def _name(schedd: str | None) -> list[str]:
        return ["-name", schedd] if schedd else []

    def _schedd_of(self, rec: dict) -> str | None:
        """The schedd recorded with the record's submission; a campaign stays bound to it after a mapping change."""
        try:
            return (Path(rec["submission_dir"]) / "schedd.txt").read_text(encoding="utf-8").strip() or None
        except OSError:
            return self.schedd

    def prepare(self, ctx: dict) -> dict:
        cfg, res, site = self.config, self.config.get("resources", {}), self.config.get("htcondor", {})
        if self._schedd_unresolved:
            raise CampaignError("htcondor.schedd.unresolved", "htcondor.schedd is 'caller' but _condor_SCHEDD_HOST is not set in the caller's environment")
        sub, cdir, outputs = Path(ctx["submission_dir"]), Path(ctx["campaign_dir"]), Path(ctx["outputs_dir"])
        for p in (cdir, sub, outputs):
            if re.search(r"\s", str(p)):
                raise CampaignError("htcondor.path_whitespace", f"{p} contains whitespace; use a campaign_dir without spaces")
        transfer = site["file_transfer"] == "transfer"
        executable, args = str(ctx["runner"]), []
        if cfg.get("worker_python"):
            executable, args = cfg["worker_python"], [str(ctx["runner"]) if not transfer else Path(ctx["runner"]).name]
        if transfer:
            args += ["--spec", "spec.json", "--chunk", "$(chunk_id)", "--attempt", "$(attempt_id)", "--out-dir", "."]
            inputs = [str(ctx["spec"])] + list(site.get("transfer_input_files", []))
            if cfg.get("worker_python"):
                inputs.append(str(ctx["runner"]))
            remap = "; ".join(f"$(attempt_id){s} = {outputs}/$(chunk_id)/$(attempt_id){s}" for s in (".json", ".meta.json"))
            transfer_lines = (f"when_to_transfer_output = ON_EXIT\ntransfer_input_files = {', '.join(inputs)}\n"
                              f'transfer_output_remaps = "{remap}"\n')
        else:
            args += ["--spec", str(ctx["spec"]), "--chunk", "$(chunk_id)", "--attempt", "$(attempt_id)", "--out-root", str(outputs)]
            transfer_lines = ""
        res_lines = "".join(f"{k} = {v}\n" for k, v in (
            ("request_cpus", res.get("cpus")), ("request_memory", f"{res['memory_mb']}MB" if "memory_mb" in res else None),
            ("request_disk", f"{res['disk_mb']}MB" if "disk_mb" in res else None),
            ("request_gpus", res.get("gpus") or None)) if v is not None)
        site_lines = "".join(f"+{k} = {_classad(v)}\n" for k, v in (site.get("site_attributes") or {}).items())
        values = {
            "submission_id": ctx["submission_id"], "universe": site["universe"], "tag": ctx.get("tag") or ctx["submission_id"],
            "container_line": f"container_image = {site['container_image']}\n" if site.get("container_image") else "",
            "executable": executable,
            "transfer_executable": "true" if transfer and not cfg.get("worker_python") else "false",
            "arguments": " ".join(args), "event_log": str(sub / "events.log"), "log_dir": str(sub / "logs"),
            "should_transfer_files": "YES" if transfer else "NO", "transfer_lines": transfer_lines, "resource_lines": res_lines,
            "site_lines": site_lines,
            "requirements_line": f"requirements = {site['requirements']}\n" if site.get("requirements") else "",
            "throttle_line": f"max_materialize = {cfg['throttle']}\n" if cfg.get("throttle") else "",
            # relative: condor_submit runs in the submission folder, and the dry-run copy can be checked in its own
            "items": "items.txt"}
        text = TEMPLATE.read_text(encoding="utf-8")
        for k, v in values.items():
            text = text.replace("{{" + k + "}}", str(v))
        items = "".join(f"{r['chunk_id']} {r['attempt_id']}\n" for r in ctx["rows"])
        files = {"job.sub": text, "items.txt": items, "map.json": json.dumps(ctx["rows"], indent=1) + "\n"}
        if self.schedd:  # recorded with the submission: every later query of these jobs goes to the same schedd
            files["schedd.txt"] = self.schedd + "\n"
        return {"backend": self.name, "submission_id": ctx["submission_id"], "submission_dir": str(sub), "files": files,
                "submit_argv": ["condor_submit", *self._name(self.schedd), "-terse", str(sub / "job.sub")], "rows": ctx["rows"]}

    def submit(self, plan: dict) -> list[dict]:
        p = self.run_submit(plan["submit_argv"], cwd=plan["submission_dir"])
        m = re.match(r"^(\d+)\.(\d+) - (\d+)\.(\d+)\s*$", (p.stdout.strip().splitlines() or [""])[-1])
        if p.returncode != 0:
            text = ((p.stderr or "") + (p.stdout or "")).strip()
            for marker, code in REFUSED_BEFORE_QUEUE:  # texts the client prints before any cluster exists
                if marker in text:
                    raise SubmitRefused(code, f"exit {p.returncode}: {text[-500:]}")
        if p.returncode != 0 or not m:  # condor_submit ran: the schedd may still have queued the cluster
            raise SubmitAmbiguous("htcondor.submit.failed", f"exit {p.returncode}: {(p.stderr or p.stdout).strip()[-500:]}")
        cluster, first = int(m.group(1)), int(m.group(2))
        return [{"attempt_id": r["attempt_id"], "job_id": f"{cluster}.{first + r['index']}"} for r in plan["rows"]]

    def _ads(self, tool: str, clusters: list[str], schedd: str | None = None, match: int | None = None) -> dict:
        # condor_history reads the schedd's whole history file, newest first; -match N stops after the N ads wanted
        p = self.run_poll([tool, *self._name(schedd), *clusters, *(["-match", str(match)] if match else []), "-json", "-attributes", ATTRS])
        if p.returncode != 0:
            raise PollError(f"htcondor.{tool}.failed", f"exit {p.returncode}: {p.stderr.strip()[-300:]}")
        text = p.stdout.strip()
        try:
            ads = json.loads(text) if text else []
        except ValueError as exc:
            raise PollError(f"htcondor.{tool}.unparsable", f"{exc}: {text[:200]!r}") from None
        if not isinstance(ads, list):
            raise PollError(f"htcondor.{tool}.unparsable", "expected a JSON list of job ads")
        return {f"{a.get('ClusterId')}.{a.get('ProcId')}": a for a in ads}

    @staticmethod
    def _from_ad(ad: dict, evidence: str) -> dict:
        st = ad.get("JobStatus")
        if st == 4:
            if ad.get("ExitBySignal"):
                state, code, sig = "failed", None, ad.get("ExitSignal")
            else:
                code, sig = ad.get("ExitCode"), None
                state = "done" if code == 0 else "failed"
        else:
            state, code, sig = JOB_STATUS.get(st, "unknown"), None, None
        hold = f"{ad.get('HoldReasonCode')}.{ad.get('HoldReasonSubCode', 0)}" if st == 5 and ad.get("HoldReasonCode") is not None else None
        return _blank(state=state, native_state=f"JobStatus {st}", exit_code=code, signal=sig,
                      hold_reason=ad.get("HoldReason") if st == 5 else None, hold_code=hold,
                      restarts=max(int(ad.get("NumJobStarts") or 0) - 1, 0), evidence=evidence)

    def poll(self, records: list[dict]) -> dict:
        out, unresolved = {}, []
        for rec in records:
            log = Path(rec["submission_dir"]) / "events.log"
            try:
                procs = parse_event_log(log.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                unresolved.append(rec)
                continue
            cluster, proc = (int(x) for x in rec["job_id"].split("."))
            o = procs.get((cluster, proc))
            if o is None:
                unresolved.append(rec)
                continue
            out[rec["attempt_id"]] = _blank(
                state=o["state"], native_state="event " + o["native"][-1], exit_code=o["exit_code"], signal=o["signal"],
                hold_reason=o["hold_reason"], hold_code=o["hold_code"], host=o["host"], elapsed_s=o["elapsed"],
                max_rss_mb=o["mem"], restarts=max(o["starts"] - 1, 0), evidence="job event log")
            if o["state"] in ("queued", "running"):
                unresolved.append(rec)  # confirm the job still exists
        by_schedd: dict = {}
        for rec in unresolved:
            by_schedd.setdefault(self._schedd_of(rec), []).append(rec)
        for schedd, recs in by_schedd.items():
            clusters = sorted({r["job_id"].split(".")[0] for r in recs})
            queue = self._ads("condor_q", clusters, schedd)
            missing = [r for r in recs if r["job_id"] not in queue]
            history = self._ads("condor_history", clusters, schedd, match=len(missing)) if missing else {}
            for rec in recs:
                ad = queue.get(rec["job_id"]) or history.get(rec["job_id"])
                if rec["attempt_id"] in out and ad is not None:
                    continue  # the event log already describes it and the job exists
                if ad is not None:
                    out[rec["attempt_id"]] = self._from_ad(ad, "condor_q" if rec["job_id"] in queue else "condor_history")
                else:
                    prev = out.get(rec["attempt_id"], {})
                    out[rec["attempt_id"]] = _blank(state="lost", native_state=prev.get("native_state"),
                                                    evidence="in neither the queue nor the history")
        return out

    def find(self, tag: str, since: str | None = None) -> list[dict]:
        """Read-only: jobs in the queue or the history whose HepResearchTag is the submission tag (reconciliation)."""
        if not re.match(r"^[A-Za-z0-9_.-]+$", tag):
            raise PollError("htcondor.bad_tag", f"refusing to build a constraint from {tag!r}")
        out, seen = [], set()
        for tool in ("condor_q", "condor_history"):
            p = self.run_poll([tool, *self._name(self.schedd), "-constraint", f'HepResearchTag == "{tag}"', "-json", "-attributes", ATTRS])
            if p.returncode != 0:
                raise PollError(f"htcondor.{tool}.failed", f"exit {p.returncode}: {p.stderr.strip()[-300:]}")
            try:
                ads = json.loads(p.stdout.strip() or "[]")
            except ValueError as exc:
                raise PollError(f"htcondor.{tool}.unparsable", str(exc)) from None
            for ad in ads if isinstance(ads, list) else []:
                jid = f"{ad.get('ClusterId')}.{ad.get('ProcId')}"
                if jid not in seen:
                    seen.add(jid)
                    out.append({"job_id": jid, "state": self._from_ad(ad, tool)["state"]})
        return out

    def cancel(self, records: list[dict]) -> list[dict]:
        out = []
        for r in records:
            argv = ["condor_rm", *self._name(self._schedd_of(r)), r["job_id"]]
            try:
                out.append({"argv": argv, "exit": self.run_poll(argv).returncode})
            except PollError as exc:  # a hung or missing client: recorded, the other jobs are still cancelled
                out.append({"argv": argv, "exit": None, "error": exc.signature})
        return out

    def version(self) -> str:
        try:
            p = self.run_poll(["condor_version"])
        except PollError as exc:
            return f"unknown ({exc.signature})"
        return p.stdout.strip().splitlines()[0] if p.returncode == 0 and p.stdout.strip() else f"unknown (condor_version exit {p.returncode})"
