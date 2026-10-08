#!/usr/bin/env python3
"""Batch campaigns on Slurm or HTCondor: plan, submit, poll, collect, resubmit, merge, report.

Every command that changes scheduler state is a dry run unless its flag is given: submit and resubmit need --submit,
cancel needs --approve-cancel. Nothing here releases a held job, raises a resource request or resubmits on its own.

  check-config --config C [--example]
  plan     --config C (--manifest M | --job ID --items N --chunk-size K --seed S) --cmd "worker ... {start} {stop} {seed} {out}"
           [--container-image IMAGE]                     writes the manifest and the runner spec into campaign_dir
  submit   --config C [--submit] [--pilot] [--chunks ID ...] [--plan-digest D]   --pilot: one chunk, to size time
           and memory; --plan-digest: the dry run's plan_digest, refuses if the job files changed since the review
  status   --config C                                    exactly one poll, then collection; per-chunk state,
                                                         elapsed time and peak memory where the scheduler reports them
  watch    --config C                                    repeated status within monitor.poll_interval_s (>= 60) and
                                                         monitor.max_polls / monitor.deadline_s; refuses without them
  resubmit --config C [--submit]                         only chunks whose decision allows it (max_attempts, changed
                                                         resources after timeout or out-of-memory)
  reset    --config C --chunks ID ... --reason TEXT      after a person fixed the cause (refused beyond
                                                         limits.max_resets_per_chunk)
  reconcile --config C --submission S                   read-only: the jobs the scheduler lists under the
                                                         submission's tag (after an interrupted or ambiguous submit)
  confirm  --config C --submission S --jobs ATTEMPT=JOB ...   a person records the jobs; every job ID must be one
                                                         reconcile lists (fabricated IDs are refused)
  abandon  --config C --submission S --reason TEXT       a person found none of them; recorded as 'abandoned'
Submission runs outside the agent sandbox: only in a disposable test environment with synthetic data, each submission
approved by the user, until a trusted submitter is qualified. Scheduler clients get an allow-listed environment and a
timeout; a submit whose outcome is unknown stays unconfirmed, never 'not-submitted'.
  cancel   --config C [--chunks ID ...] [--approve-cancel]   also jobs found under the tag of unconfirmed or
                                                         abandoned submissions; records each exit; a request is not
                                                         termination (a later status poll observes that)
A configured 'limits' section stops a submission or reset that would exceed it (core/partition/limits.py).
  merge    --config C                                    requires every chunk exactly once
  report   --config C --out ARTIFACT.json [--label synthetic ...] [--objective TEXT]
           writes a computational-run artifact (status 'failed' unless the merge is complete)
The config file (see batch_config.py) lives in your project; campaign_dir is relative to the config's folder.
Exit codes: 0 done / complete, 1 incomplete, failed or blocked chunks, 2 refused (configuration or usage).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PLUGIN))
import batch_config  # noqa: E402
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from core.partition import campaign as cp  # noqa: E402
from core.partition import engine  # noqa: E402
from core.partition import limits  # noqa: E402
from core.partition.executors import PollError  # noqa: E402


def executor_for(cfg: dict, env=None):
    if cfg["backend"] == "slurm":
        from slurm_backend import SlurmExecutor
        return SlurmExecutor(cfg, env)
    from htcondor_backend import HTCondorExecutor
    return HTCondorExecutor(cfg, env)


def load_config(path: Path, example: bool = False) -> tuple[dict, Path]:
    text = sys.stdin.read() if str(path) in ("-", "/dev/stdin") else path.read_text(encoding="utf-8")
    cfg = json.loads(text)
    errs = batch_config.validate(cfg, example=example)
    if errs:
        raise RefusedConfig(errs)
    base = Path.cwd() if str(path) in ("-", "/dev/stdin") else path.resolve().parent
    return cfg, (base / cfg["campaign_dir"]).resolve() if not example else base


class RefusedConfig(Exception):
    def __init__(self, errors):
        super().__init__("configuration refused")
        self.errors = errors


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_artifact(cdir: Path, cfg: dict, executor, labels: list[str], objective: str) -> dict:
    """computational-run artifact for a campaign; incomplete campaigns carry 'failed' and a non-zero exit status."""
    manifest, state = cp.load(cdir)
    merged = cp.merge(cdir)
    complete = merged["status"] == "complete"
    chunk_hashes = {f"chunks/{p.name}": _sha(p) for p in sorted((cdir / "chunks").glob("*.json"))}
    merged_hash = hashlib.sha256(json.dumps(merged["merged"], sort_keys=True).encode()).hexdigest() if complete else None
    attempts = {cid: [{k: r.get(k) for k in ("attempt_id", "global_attempt_id", "job_id", "origin", "host", "final_state", "native_state",
                                             "exit_code", "signal", "hold_code", "hold_reason", "resource_change",
                                             "cancel_requests", "termination_observed")}
                      for r in row.get("attempt_records", [])] for cid, row in sorted(state["chunks"].items())}
    resources = {r["attempt_id"]: {"elapsed_s": r.get("elapsed_s"), "max_rss_mb": r.get("max_rss_mb")}
                 for row in state["chunks"].values() for r in row.get("attempt_records", [])
                 if r.get("elapsed_s") is not None or r.get("max_rss_mb") is not None}
    status = sorted(set(labels) | ({"unvalidated"} if complete else {"failed", "unvalidated"}))
    return {
        "contract_version": CONTRACTS_VERSION, "artifact_id": f"batch-campaign-{manifest['job_id']}-{manifest['manifest_hash'][:12]}",
        "artifact_type": "computational-run", "objective": objective,
        "versions": {"plugin": json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"], "contracts": CONTRACTS_VERSION,
                     "plugin_release": plugin_release()},
        "provenance": {"producer_skill": "hep-computing", "created": datetime.date.today().isoformat()},
        "inputs": [], "outputs": [], "status": status, "unresolved_inputs": [],
        "extension": {
            "input_manifest": [{"path": "manifest.json", "sha256": _sha(cdir / "manifest.json")},
                               {"path": "spec.json", "sha256": _sha(cdir / "spec.json")}],
            "tools": [{"name": cfg["backend"], "version": executor.version()},
                      {"name": "hep-research core/partition runner", "version": _sha(cdir / "runner.py")}],
            "commands": [" ".join(map(str, s["command"])) for s in state["submissions"]],
            "environment": {"backend": cfg["backend"], "config_sha256": batch_config.config_hash(cfg), "config": cfg,
                            "manifest_hash": manifest["manifest_hash"],  # in full; artifact_id shows 12 digits only
                            "container_image": json.loads((cdir / "spec.json").read_text()).get("container_image"),
                            "execution": {"campaign_status": "complete" if complete else "incomplete", "attempts": attempts,
                                          "duplicates": state["duplicates"], "quarantine": state["quarantine"],
                                          "resets": state["resets"], "merge_problems": merged["problems"],
                                          "campaign_uid": state.get("campaign_uid"), "cancels": state.get("cancels", []),
                                          "resource_risk": state.get("resource_risk", []),
                                          "limits": {"configured": cfg.get("limits"), "usage": limits.usage(state)}}},
            "seeds": {"manifest_seed": manifest["seed"], "chunk_seeds": {c["id"]: c["seed"] for c in manifest["chunks"]}},
            "tolerances": {"merge": "exact: every chunk exactly once, item ranges tile [0, n); results summed key by key"},
            "resources": resources,
            "exit_status": 0 if complete else 1,
            "output_hashes": dict(chunk_hashes, **({"merged": merged_hash} if merged_hash else {})),
        }}


def main(argv=None, env=None, sleep=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check-config", "plan", "submit", "status", "watch", "resubmit", "reset", "reconcile", "confirm", "abandon",
                 "cancel", "merge", "report"):
        s = sub.add_parser(name)
        s.add_argument("--config", type=Path, required=True)
        if name == "check-config":
            s.add_argument("--example", action="store_true", help="accept placeholders (only for the shipped example)")
        if name == "plan":
            s.add_argument("--manifest", type=Path)
            s.add_argument("--job")
            s.add_argument("--items", type=int)
            s.add_argument("--chunk-size", type=int)
            s.add_argument("--seed", type=int)
            s.add_argument("--cmd", dest="template", required=True)
            s.add_argument("--container-image")
        if name in ("submit", "resubmit"):
            s.add_argument("--submit", action="store_true", help="really submit (default: dry run, no scheduler call)")
        if name == "submit":
            s.add_argument("--pilot", action="store_true")
            s.add_argument("--plan-digest", help="the plan_digest of the reviewed dry run: refuse if the job files changed")
        if name in ("submit", "cancel", "reset"):
            s.add_argument("--chunks", nargs="+", required=name == "reset")
        if name in ("reset", "abandon"):
            s.add_argument("--reason", required=True)
        if name in ("reconcile", "confirm", "abandon"):
            s.add_argument("--submission", required=True, help="the unconfirmed submission, for example s003")
        if name == "confirm":
            s.add_argument("--jobs", nargs="+", required=True, metavar="ATTEMPT=JOB",
                           help="every attempt of the submission with the job ID the scheduler shows for it")
        if name == "cancel":
            s.add_argument("--approve-cancel", action="store_true")
        if name == "report":
            s.add_argument("--out", type=Path, required=True)
            s.add_argument("--label", action="append", default=[], help="status label to carry, e.g. synthetic")
            s.add_argument("--objective", default="Batch campaign of a manifest-partitioned job")
    args = ap.parse_args(argv)

    def emit(obj, code):
        print(json.dumps(obj, indent=1, default=str))
        return code

    try:
        cfg, cdir = load_config(args.config, example=getattr(args, "example", False))
        if args.cmd == "check-config":
            return emit({"ok": True, "config_sha256": batch_config.config_hash(cfg)}, 0)
        ex = executor_for(cfg, env)
        if args.cmd == "plan":
            if args.manifest:
                manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            elif None in (args.job, args.items, args.chunk_size, args.seed):
                return emit({"error": "plan needs --manifest or all of --job --items --chunk-size --seed"}, 2)
            else:
                manifest = engine.make_manifest(args.job, args.items, args.chunk_size, args.seed)
            cp.init(cdir, manifest, args.template, args.container_image, cfg.get("worker_timeout_s"))
            return emit({"campaign_dir": str(cdir), "chunks": len(manifest["chunks"]), "manifest_hash": manifest["manifest_hash"]}, 0)
        if args.cmd == "submit":
            rep = cp.submit(cdir, ex, cfg, chunk_ids=args.chunks, approved=args.submit, pilot=args.pilot,
                            expected_plan_digest=args.plan_digest)
            return emit(rep, 0)
        if args.cmd == "status":
            rep = cp.poll(cdir, ex)
            return emit(rep, 0 if rep["complete"] else 1)
        if args.cmd == "watch":
            rep = cp.watch(cdir, ex, cfg, **({"sleep": sleep} if sleep else {}))
            return emit(rep, 0 if rep["complete"] else 1)
        if args.cmd == "resubmit":
            rep = cp.resubmit(cdir, ex, cfg, approved=args.submit)
            return emit(rep, 1 if rep["blocked"] else 0)
        if args.cmd == "reset":
            return emit(cp.reset(cdir, args.chunks, args.reason, cfg), 0)
        if args.cmd == "confirm":
            pairs = dict(item.split("=", 1) for item in args.jobs if "=" in item)
            if len(pairs) != len(args.jobs):
                return emit({"error": "--jobs takes ATTEMPT=JOB pairs"}, 2)
            return emit(cp.confirm_submission(cdir, args.submission, pairs, ex), 0)
        if args.cmd == "reconcile":
            return emit(cp.reconcile(cdir, ex, args.submission), 0)
        if args.cmd == "abandon":
            return emit(cp.abandon_submission(cdir, args.submission, args.reason), 0)
        if args.cmd == "cancel":
            return emit(cp.cancel(cdir, ex, args.chunks, approved=args.approve_cancel), 0)
        if args.cmd == "merge":
            rep = cp.merge(cdir)
            return emit(rep, 0 if rep["status"] == "complete" else 1)
        art = build_artifact(cdir, cfg, ex, args.label, args.objective)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(art, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return emit({"artifact": str(args.out), "status": art["status"], "exit_status": art["extension"]["exit_status"]},
                    art["extension"]["exit_status"])
    except RefusedConfig as exc:
        return emit({"error": "configuration refused", "errors": exc.errors}, 2)
    except cp.CampaignError as exc:
        return emit({"error": str(exc), "code": exc.code}, 2)
    except PollError as exc:
        return emit({"error": exc.text, "code": exc.signature}, 1)
    except (OSError, ValueError, KeyError) as exc:
        return emit({"error": str(exc)}, 2)


if __name__ == "__main__":
    sys.exit(main())
