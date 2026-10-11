"""Campaign resource limits and attempt identity (T3.4): what a campaign has used, counted conservatively.

A campaign configuration may carry a 'limits' section; every key is optional and its value comes from the site and
the person running the campaign (Q-07), never from a default here:

  max_submissions        submissions recorded (an intent counts; a refused client that never started does not)
  max_total_jobs         job attempts recorded, under the same rule
  max_concurrent_jobs    attempts that may still be running: queued, running, held, submitting, and unknown or
                         abandoned attempts (orphan risk): an unknown one until a poll sees it end, either until a person clears it
                         with evidence from the scheduler (campaign.clear_orphan_risk); a walltime does not bound
                         them, since a lost job may wait in the queue for any time before it starts
  max_core_hours         cpus x elapsed time of finished attempts, cpus x walltime limit for every attempt whose end
                         is not observed; with no walltime limit (htcondor) the use is unbounded and the limit refuses.
                         cpus is what the scheduler allocated when it reports it (alloc_cpus: a site may round a
                         request up, 2x on hyper-threaded GPU nodes), else what was requested times alloc_cpu_factor;
                         new jobs are projected at alloc_cpu_factor too
  alloc_cpu_factor       not a limit: allocated CPUs per requested CPU that the site declares (>= 1, e.g. 2 on
                         hyper-threaded GPU nodes), so max_core_hours holds before any allocation is observed. The
                         factor used is the larger of this and the largest allocated/requested ratio seen so far in
                         the campaign; without either it is 1. It scales new jobs and attempts with no alloc_cpus yet
                         (a queued Slurm task reports none)
  max_resets_per_chunk   reset() calls per chunk

A limit that would be exceeded stops the new submission (or reset) before anything is written; it never cancels or
changes work already submitted. Without a 'limits' section nothing is limited here (max_attempts still bounds
resubmission), and the usage is still reported. These counts read agent-writable state: they bound mistakes, not a
forged state.json (that needs the trusted submitter, T3.5).

Attempt identity: '<campaign_uid>:<attempt_id>', globally unique because the campaign_uid is random per campaign.
Standard library only.
"""
from __future__ import annotations

import re

LIMIT_KEYS = ("max_submissions", "max_total_jobs", "max_concurrent_jobs", "max_core_hours", "max_resets_per_chunk",
              "alloc_cpu_factor")
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
        number = isinstance(v, (int, float)) and not isinstance(v, bool)
        if k == "max_core_hours":
            ok, want = number and v > 0, "positive number"
        elif k == "alloc_cpu_factor":
            ok, want = number and v >= 1, "number >= 1"
        else:
            ok = isinstance(v, int) and not isinstance(v, bool) and v >= (0 if k == "max_resets_per_chunk" else 1)
            want = "non-negative integer" if k == "max_resets_per_chunk" else "positive integer"
        if not ok:
            out.append(f"limits.{k} must be a {want}, got {v!r}")
    return out


def _counted(rec: dict) -> bool:
    """A recorded job attempt: not a scheduler restart (counted with its job) and not a client that never started."""
    return rec.get("origin") != "scheduler-restart" and rec.get("final_state") != "not-submitted"


def _may_still_run(rec: dict) -> bool:
    fs = rec.get("final_state")
    if fs is None or fs == "held":
        return True
    return fs in ORPHAN_RISK and not rec.get("orphan_cleared")


def _alloc_cpus(rec: dict) -> int | None:
    a = rec.get("alloc_cpus")
    return a if isinstance(a, int) and not isinstance(a, bool) and a > 0 else None


def _alloc_cpu_factor(recs: list[dict]) -> float:
    """Largest allocated/requested cpu ratio observed (never below 1): how far requests under-state use here."""
    return max([1.0] + [a / _cpus(r.get("resources")) for r in recs if (a := _alloc_cpus(r))])


def _core_hours(rec: dict, factor: float) -> float | None:
    cpus = _alloc_cpus(rec) or _cpus(rec.get("resources")) * factor
    fs = rec.get("final_state")
    if fs is None or fs in ORPHAN_RISK or fs == "held" or rec.get("elapsed_s") is None:
        wall = walltime_s(rec.get("resources"))
        return None if wall is None else cpus * wall / 3600
    return cpus * float(rec["elapsed_s"]) / 3600


def usage(state: dict, limits: dict | None = None) -> dict:
    """What the campaign has used; limits supplies alloc_cpu_factor, the only key that changes a count."""
    recs = [r for row in state.get("chunks", {}).values() for r in row.get("attempt_records", [])]
    counted = [r for r in recs if _counted(r)]
    observed = _alloc_cpu_factor(counted)
    factor = max(observed, float((limits or {}).get("alloc_cpu_factor") or 1))
    hours = [_core_hours(r, factor) for r in counted]  # a scheduler restart is inside its job's elapsed time or walltime
    resets: dict = {}
    for r in state.get("resets", []):
        resets[r["chunk"]] = resets.get(r["chunk"], 0) + 1
    return {"submissions": sum(1 for s in state.get("submissions", []) if s.get("status") != "not-submitted"),
            "total_jobs": len(counted),
            "concurrent_jobs": sum(1 for r in counted if _may_still_run(r)),
            "core_hours": None if any(h is None for h in hours) else round(sum(h for h in hours if h is not None), 6),
            "alloc_cpu_factor": factor,
            "alloc_cpu_factor_observed": observed,
            "orphan_risk_jobs": sum(1 for r in counted if r.get("final_state") in ORPHAN_RISK),
            "resets_per_chunk": resets}


def check_submission(state: dict, config: dict, n_jobs: int) -> tuple[dict, list[str]]:
    """(usage, violations) for a new submission of n_jobs attempts under config['limits']."""
    lim = config.get("limits") or {}
    use = usage(state, lim)
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
            new = n_jobs * _cpus(config.get("resources")) * wall / 3600 * use["alloc_cpu_factor"]
            if use["core_hours"] + new > lim["max_core_hours"]:
                source = "observed" if use["alloc_cpu_factor_observed"] >= use["alloc_cpu_factor"] else "configured"
                scaled = f" (x{use['alloc_cpu_factor']:g} allocated per requested cpu, {source})" if use["alloc_cpu_factor"] > 1 else ""
                out.append(f"max_core_hours: {use['core_hours']:.3f} used + {new:.3f} requested{scaled} > {lim['max_core_hours']}")
    return use, out


def check_reset(state: dict, config: dict | None, chunk_id: str) -> str | None:
    lim = (config or {}).get("limits") or {}
    if "max_resets_per_chunk" not in lim:
        return None
    used = sum(1 for r in state.get("resets", []) if r["chunk"] == chunk_id)
    if used + 1 > lim["max_resets_per_chunk"]:
        return f"max_resets_per_chunk: {chunk_id} has {used} resets; limit {lim['max_resets_per_chunk']}"
    return None
