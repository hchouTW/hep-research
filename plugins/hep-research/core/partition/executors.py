"""Executor interface for running manifest chunks, and the local (synchronous) executor.

An executor turns a submission context into a plan, submits it, polls it and cancels it:

  prepare(ctx) -> plan                pure: renders files and the submit command, touches nothing
  submit(plan) -> [{attempt_id, job_id}]   the only call that starts work; the campaign calls it only when the user
                                       passed an explicit submit flag (everything else is a dry run)
  poll(records) -> {attempt_id: observation}   one round of queries; raises PollError on unusable output
  cancel(records) -> [argv, ...]      the cancel commands it ran; the campaign calls it only with explicit approval
  version() -> str                    the tool version as the tool reports it, or 'unknown (...)'

ctx: {"campaign_dir", "submission_id", "submission_dir", "rows": [{"index", "chunk_id", "attempt_id"}], "config",
"spec", "runner", "outputs_dir"}. plan: {"backend", "submission_id", "files": {name: text}, "submit_argv": [...],
"rows"}. An observation: {"state" (a normalized state), "native_state", "exit_code", "signal", "hold_reason",
"hold_code", "host", "elapsed_s", "max_rss_mb", "restarts", "evidence"}; missing facts are None, never guessed.
Standard library only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


class PollError(Exception):
    """A poll whose output could not be used. signature groups repeated errors; text is kept for the report."""

    def __init__(self, signature: str, text: str):
        super().__init__(f"{signature}: {text}")
        self.signature, self.text = signature, text


class SubmitError(PollError):
    """A submit command that failed or printed no job ID; the campaign records no attempt for it."""


class Executor:
    name = "abstract"

    def __init__(self, env: dict | None = None):
        self.env = env

    def run(self, argv, cwd=None) -> subprocess.CompletedProcess:
        """Run one tool command; the environment (PATH) decides which tool, so tests can put fakes first."""
        return subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True, env=self.env)

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
                code = subprocess.run(argv, stdout=out, stderr=err, env=self.env).returncode
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
