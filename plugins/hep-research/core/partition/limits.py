"""Campaign resource limits and attempt identity (T3.4): what a campaign has used, counted conservatively.

A campaign configuration may carry a 'limits' section; every key is optional and its value comes from the site and
the person running the campaign (Q-07), never from a default here:

  max_submissions        submissions recorded (an intent counts; a refused client that never started does not)
  max_total_jobs         job attempts recorded, under the same rule
  max_concurrent_jobs    attempts that may still be running: queued, running, held, submitting, and unknown or
                         abandoned attempts until their worst-case walltime has passed (orphan risk)
  max_core_hours         cpus x elapsed time of finished attempts, cpus x walltime limit for every attempt whose end
                         is not observed; with no walltime limit (htcondor) the use is unbounded and the limit refuses
  max_resets_per_chunk   reset() calls per chunk

A limit that would be exceeded stops the new submission (or reset) before anything is written; it never cancels or
changes work already submitted. Without a 'limits' section nothing is limited here (max_attempts still bounds
resubmission), and the usage is still reported. These counts read agent-writable state: they bound mistakes, not a
forged state.json (that needs the trusted submitter, T3.5).

Attempt identity: '<campaign_uid>:<attempt_id>', globally unique because the campaign_uid is random per campaign.
Standard library only.
"""
from __future__ import annotations

import datetime
import re

LIMIT_KEYS = ("max_submissions", "max_total_jobs", "max_concurrent_jobs", "max_core_hours", "max_resets_per_chunk")
WALLTIME = re.compile(r"^(?:(\d+)-)?(\d{1,2}):(\d{2}):(\d{2})$")
# states in which a job may run without the record knowing it (orphan risk)
ORPHAN_RISK = frozenset({"unknown", "abandoned"})


def global_attempt_id(campaign_uid: str | None, attempt_id: str) -> str:
    return f"{campaign_uid or 'unknown-campaign'}:{attempt_id}"


def walltime_s(resources: dict | None) -> int | None:
    """Seconds of a '[D-]HH:MM:SS' time_limit, or None when there is none."""
    m = WALLTIME.match(str((resources or {}).get("time_limit") or ""))
    if not m:
        return None
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def _cpus(resources: dict | None) -> int:
    c = (resources or {}).get("cpus")
    return c if isinstance(c, int) and not isinstance(c, bool) and c > 0 else 1


def _ts(text: str | None) -> datetime.datetime | None:
    try:
        return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None


def problems(limits) -> list[str]:
    """Why a 'limits' section is malformed (also checked by batch_config.validate)."""
    if limits is None:
        return []
    if not isinstance(limits, dict):
        return ["limits must be an object"]
    out = [f"unknown key limits.{k}" for k in sorted(set(limits) - set(LIMIT_KEYS))]
    for k in LIMIT_KEYS:
        if k not in limits:
            continue
        v = limits[k]
        ok = (isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0) if k == "max_core_hours" else \
             (isinstance(v, int) and not isinstance(v, bool) and v >= (0 if k == "max_resets_per_chunk" else 1))
        if not ok:
            out.append(f"limits.{k} must be a {'positive number' if k == 'max_core_hours' else 'non-negative integer' if k == 'max_resets_per_chunk' else 'positive integer'}, got {v!r}")
    return out


def _counted(rec: dict) -> bool:
    """A recorded job attempt: not a scheduler restart (counted with its job) and not a client that never started."""
    return rec.get("origin") != "scheduler-restart" and rec.get("final_state") != "not-submitted"


def _may_still_run(rec: dict, now: datetime.datetime) -> bool:
    fs = rec.get("final_state")
    if fs is None or fs == "held":
        return True
    if fs not in ORPHAN_RISK:
        return False
    wall, start = walltime_s(rec.get("resources")), _ts(rec.get("submit_time"))
    if wall is None or start is None:
        return True  # no bound on when it ends: it counts as running
    return now < start + datetime.timedelta(seconds=wall)


def _core_hours(rec: dict) -> float | None:
    cpus = _cpus(rec.get("resources"))
    fs = rec.get("final_state")
    if fs is None or fs in ORPHAN_RISK or fs == "held" or rec.get("elapsed_s") is None:
        wall = walltime_s(rec.get("resources"))
        return None if wall is None else cpus * wall / 3600
    return cpus * float(rec["elapsed_s"]) / 3600


def usage(state: dict, now: datetime.datetime | None = None) -> dict:
    now = now or datetime.datetime.now(datetime.UTC)
    recs = [r for row in state.get("chunks", {}).values() for r in row.get("attempt_records", [])]
    counted = [r for r in recs if _counted(r)]
    hours = [_core_hours(r) for r in counted]  # a scheduler restart is inside its job's elapsed time or walltime
    resets: dict = {}
    for r in state.get("resets", []):
        resets[r["chunk"]] = resets.get(r["chunk"], 0) + 1
    return {"submissions": sum(1 for s in state.get("submissions", []) if s.get("status") != "not-submitted"),
            "total_jobs": len(counted),
            "concurrent_jobs": sum(1 for r in counted if _may_still_run(r, now)),
            "core_hours": None if any(h is None for h in hours) else round(sum(h for h in hours if h is not None), 6),
            "orphan_risk_jobs": sum(1 for r in counted if r.get("final_state") in ORPHAN_RISK),
            "resets_per_chunk": resets}


def check_submission(state: dict, config: dict, n_jobs: int, now: datetime.datetime | None = None) -> tuple[dict, list[str]]:
    """(usage, violations) for a new submission of n_jobs attempts under config['limits']."""
    lim = config.get("limits") or {}
    use = usage(state, now)
    out = []
    for key, used, add in (("max_submissions", use["submissions"], 1), ("max_total_jobs", use["total_jobs"], n_jobs),
                           ("max_concurrent_jobs", use["concurrent_jobs"], n_jobs)):
        if key in lim and used + add > lim[key]:
            out.append(f"{key}: {used} used + {add} new > {lim[key]}")
    if "max_core_hours" in lim:
        wall = walltime_s(config.get("resources"))
        if use["core_hours"] is None or wall is None:
            out.append("max_core_hours: core-hours are unbounded (an attempt without a walltime limit and an unobserved end, "
                       "or no resources.time_limit for the new jobs), so the limit cannot be shown to hold")
        else:
            new = n_jobs * _cpus(config.get("resources")) * wall / 3600
            if use["core_hours"] + new > lim["max_core_hours"]:
                out.append(f"max_core_hours: {use['core_hours']:.3f} used + {new:.3f} requested > {lim['max_core_hours']}")
    return use, out


def check_reset(state: dict, config: dict | None, chunk_id: str) -> str | None:
    lim = (config or {}).get("limits") or {}
    if "max_resets_per_chunk" not in lim:
        return None
    used = sum(1 for r in state.get("resets", []) if r["chunk"] == chunk_id)
    if used + 1 > lim["max_resets_per_chunk"]:
        return f"max_resets_per_chunk: {chunk_id} has {used} resets; limit {lim['max_resets_per_chunk']}"
    return None
