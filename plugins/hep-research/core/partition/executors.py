"""Executor interface for running manifest chunks, and the local (synchronous) executor.

An executor turns a submission context into a plan, submits it, polls it and cancels it:

  prepare(ctx) -> plan                pure: renders files and the submit command, touches nothing
  submit(plan) -> [{attempt_id, job_id}]   the only call that starts work; the campaign calls it only when the user
                                       passed an explicit submit flag (everything else is a dry run). It raises
                                       SubmitRefused when the scheduler was certainly not reached, SubmitAmbiguous
                                       when it may have accepted the jobs (timeout, exit 0 without a job ID, a non-zero
                                       exit after the call)
  find(tag, since) -> [{job_id, ...}]  read-only: jobs the scheduler knows under a submission tag (reconciliation)
  poll(records) -> {attempt_id: observation}   one round of queries; raises PollError on unusable output
  cancel(records) -> [argv, ...]      the cancel commands it ran; the campaign calls it only with explicit approval
  version() -> str                    the tool version as the tool reports it, or 'unknown (...)'

ctx: {"campaign_dir", "submission_id", "submission_dir", "rows": [{"index", "chunk_id", "attempt_id"}], "config",
"spec", "runner", "outputs_dir"}. plan: {"backend", "submission_id", "files": {name: text}, "submit_argv": [...],
"rows"}. An observation: {"state" (a normalized state), "native_state", "exit_code", "signal", "hold_reason",
"hold_code", "host", "elapsed_s", "max_rss_mb", "restarts", "evidence"}; missing facts are None, never guessed.
Every tool call has a timeout (scheduler_timeout_s, default 120 s) and runs with an allow-listed environment
(ENV_ALLOW plus the configured env_passthrough names), so tokens and agent sockets in the caller's environment do not
reach scheduler clients or local workers. Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


class PollError(Exception):
    """A poll whose output could not be used. signature groups repeated errors; text is kept for the report."""

    def __init__(self, signature: str, text: str):
        super().__init__(f"{signature}: {text}")
        self.signature, self.text = signature, text


class SubmitError(PollError):
    """A submit that did not yield job IDs. Use a subclass: the campaign treats the two very differently."""


class SubmitRefused(SubmitError):
    """Definitely not submitted: the scheduler client could not even be started. The attempts become not-submitted."""


class SubmitAmbiguous(SubmitError):
    """The scheduler may have accepted the jobs (timeout, exit 0 without a job ID, a non-zero exit after the call). The
    submission stays unconfirmed until a person reconciles it; it is never recorded as not submitted."""


DEFAULT_TIMEOUT_S = 120
ENV_ALLOW = ("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR", "SLURM_CONF", "CONDOR_CONFIG")


ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}$")
SECRET_LIKE = re.compile(r"TOKEN|SECRET|PASSW|PROXY|KEY|CRED|COOKIE|SSH_AUTH|KRB5|AUTH", re.I)


def passthrough_problems(names) -> list[str]:
    """Why these passthrough names are refused: not variable names, or credential-like (credentials never reach
    scheduler clients, jobs or local workers)."""
    if not isinstance(names, (list, tuple)):
        return ["must be a list of environment variable names"]
    out = []
    for x in names:
        if not isinstance(x, str) or not ENV_NAME.match(x):
            out.append(f"{x!r} is not an environment variable name")
        elif SECRET_LIKE.search(x):
            out.append(f"{x!r} looks like a credential; credentials never reach scheduler clients or jobs")
    return out


def allowed_env(env: dict | None = None, passthrough=()) -> dict:
    """The allow-listed subset of env (default os.environ): ENV_ALLOW plus the passthrough names, which must pass
    passthrough_problems (ValueError otherwise)."""
    problems = passthrough_problems(list(passthrough or ()))
    if problems:
        raise ValueError("env passthrough refused: " + "; ".join(problems))
    src = os.environ if env is None else env
    keep = set(ENV_ALLOW) | set(passthrough or ())
    return {k: v for k, v in src.items() if k in keep}


class Executor:
    name = "abstract"

    def __init__(self, env: dict | None = None, config: dict | None = None):
        cfg = config or {}
        self.env = allowed_env(env, cfg.get("env_passthrough", ()))
        self.timeout = cfg.get("scheduler_timeout_s", DEFAULT_TIMEOUT_S)
        self.worker_timeout = cfg.get("worker_timeout_s")

    def run(self, argv, cwd=None) -> subprocess.CompletedProcess:
        """Run one tool command with the timeout and the allow-listed environment (PATH decides which tool, so tests
        can put fakes first). Raises subprocess.TimeoutExpired or OSError; callers classify them."""
        return subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True, env=self.env,
                              timeout=self.timeout)

    def run_submit(self, argv, cwd=None) -> subprocess.CompletedProcess:
        """run() for the one call that may start jobs: a client that cannot start is SubmitRefused; a timeout is
        SubmitAmbiguous (the scheduler may have accepted the jobs before the client hung)."""
        try:
            return self.run(argv, cwd)
        except subprocess.TimeoutExpired:
            raise SubmitAmbiguous(f"{self.name}.submit.timeout", f"no answer within {self.timeout} s") from None
        except OSError as exc:
            raise SubmitRefused(f"{self.name}.submit.not_started", f"{argv[0]}: {exc}") from None

    def run_poll(self, argv, cwd=None) -> subprocess.CompletedProcess:
        """run() for observation and cancel calls: a timeout or a client that cannot start is a PollError."""
        try:
            return self.run(argv, cwd)
        except subprocess.TimeoutExpired:
            raise PollError(f"{self.name}.timeout", f"{argv[0]}: no answer within {self.timeout} s") from None
        except OSError as exc:
            raise PollError(f"{self.name}.not_started", f"{argv[0]}: {exc}") from None

    def find(self, tag: str, since: str | None = None) -> list[dict]:
        return []

    def prepare(self, ctx: dict) -> dict:
        raise NotImplementedError

    def submit(self, plan: dict) -> list[dict]:
        raise NotImplementedError

    def poll(self, records: list[dict]) -> dict:
        raise NotImplementedError

    def cancel(self, records: list[dict]) -> list[list[str]]:
        raise NotImplementedError

    def version(self) -> str:
        return "unknown (not queried)"


def _blank(**kw) -> dict:
    base = {"state": "unknown", "native_state": None, "exit_code": None, "signal": None, "hold_reason": None,
            "hold_code": None, "host": None, "elapsed_s": None, "max_rss_mb": None, "restarts": 0, "evidence": None}
    base.update(kw)
    return base


class LocalExecutor(Executor):
    """Runs every chunk of a submission synchronously, in order, through the same worker-side runner as a batch job."""

    name = "local"

    def prepare(self, ctx: dict) -> dict:
        argv = [[sys.executable, str(ctx["runner"]), "--spec", str(ctx["spec"]), "--out-dir",
                 str(Path(ctx["outputs_dir"]) / r["chunk_id"]), "--chunk", r["chunk_id"], "--attempt", r["attempt_id"]]
                for r in ctx["rows"]]
        return {"backend": self.name, "submission_id": ctx["submission_id"], "submission_dir": str(ctx["submission_dir"]),
                "files": {"commands.json": json.dumps(argv, indent=1) + "\n"}, "submit_argv": ["(in-process)"],
                "rows": ctx["rows"], "argv": argv}

    def submit(self, plan: dict) -> list[dict]:
        sub = Path(plan["submission_dir"])
        done = {}
        for row, argv in zip(plan["rows"], plan["argv"]):
            with open(sub / f"{row['attempt_id']}.stdout.log", "w") as out, open(sub / f"{row['attempt_id']}.stderr.log", "w") as err:
                try:  # the same timeout and environment rules as a batch job (X16)
                    code = subprocess.run(argv, stdout=out, stderr=err, env=self.env, timeout=self.worker_timeout).returncode
                except subprocess.TimeoutExpired:
                    code = 124
            done[row["attempt_id"]] = code
        (sub / "local-results.json").write_text(json.dumps(done, sort_keys=True) + "\n")
        return [{"attempt_id": r["attempt_id"], "job_id": f"local-{plan['submission_id']}-{r['index']}"} for r in plan["rows"]]

    def poll(self, records: list[dict]) -> dict:
        out = {}
        for rec in records:
            f = Path(rec["submission_dir"]) / "local-results.json"
            codes = json.loads(f.read_text()) if f.exists() else {}
            code = codes.get(rec["attempt_id"])
            if code is None:
                out[rec["attempt_id"]] = _blank(state="lost", evidence="local results missing")
            else:
                out[rec["attempt_id"]] = _blank(state="done" if code == 0 else "failed", native_state=f"exit {code}",
                                                exit_code=code, host=os.uname().nodename, evidence="local process exit code")
        return out

    def cancel(self, records: list[dict]) -> list[list[str]]:
        return []  # local submissions finish inside submit(); nothing is left to cancel

    def version(self) -> str:
        return f"python {sys.version.split()[0]}"
