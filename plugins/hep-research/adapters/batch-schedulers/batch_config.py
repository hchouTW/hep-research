"""Campaign configuration for the batch-scheduler adapter: site facts come from the user, never from defaults.

One JSON file per campaign, kept in the user's project (never in the plugin):

  backend         "slurm" | "htcondor"                                              required
  campaign_dir    directory for state, job files, logs and outputs                   required
  resources       {"cpus", "memory_mb", "disk_mb", "gpus", "time_limit"}            required object; time_limit
                  ("[D-]HH:MM:SS") required for slurm; other keys optional (omitted means the site default applies)
  slurm           {"partition" (required), "account", "qos", "constraint", "gres"}  required for slurm
  htcondor        {"universe" ("vanilla" | "container", required), "container_image" (required for container),
                   "file_transfer" ("shared-filesystem" | "transfer", required), "requirements",
                   "transfer_input_files"}                                          required for htcondor
  throttle        positive integer: most array tasks / jobs running at once         optional
  max_attempts    positive integer; absent means no resubmission                    optional
  monitor         {"poll_interval_s" (>= 60), "max_polls", "deadline_s"}            optional; watch needs it
  worker_python   absolute path of the interpreter the job uses to start the runner  optional (default python3
                  on the job's PATH, which --export=NONE / getenv = false keep minimal)
  job_name        ignored for the scheduler job name, which is the submission tag  optional
  scheduler_timeout_s  seconds before a scheduler client call is abandoned (default 120)  optional
  worker_timeout_s     seconds before the runner stops the worker command (default none)  optional
  env_passthrough list of environment variable names passed to scheduler clients besides the allow-list
                  (core.partition.executors.ENV_ALLOW); never credentials                optional

Unknown keys are errors, not ignored. A value written as a placeholder ("<...>") is accepted only when validating
the shipped example with example=True. Strings are rendered into job files, so they must be single-line without
template braces, and names (partition, account, qos, job_name, universe, gres) use a strict character set (X01).
worker_python and transfer_input_files must be absolute paths without '..' (X13). Refusals carry a named code:
config.missing_key, config.unknown_key, config.bad_value, config.placeholder. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.partition.executors import passthrough_problems  # noqa: E402

PLACEHOLDER = re.compile(r"^<[^<>]+>$")
TIME = re.compile(r"^(\d+-)?\d{1,2}:\d{2}:\d{2}$")
TOP = {"backend", "campaign_dir", "resources", "slurm", "htcondor", "throttle", "max_attempts", "monitor", "worker_python", "job_name",
       "scheduler_timeout_s", "worker_timeout_s", "env_passthrough"}
NAME = re.compile(r"^[A-Za-z0-9_.:+@-]{1,128}$")  # partition, account, qos, job name, gres
UNSAFE = re.compile(r"[\x00-\x1f\x7f]|\{\{|\}\}")  # control characters (a newline adds a job-file line) or template braces
CONSTRAINT = re.compile(r"^[A-Za-z0-9_.:+@&|!()\[\]*,-]{1,256}$")  # no whitespace: one #SBATCH line holds one option
RESOURCES = {"cpus", "memory_mb", "disk_mb", "gpus", "time_limit"}
SLURM = {"partition", "account", "qos", "constraint", "gres"}
HTCONDOR = {"universe", "container_image", "file_transfer", "requirements", "transfer_input_files"}
MONITOR = {"poll_interval_s", "max_polls", "deadline_s"}
# keys that name a site resource; checked by tools/check_packaging.py in shipped configs
SITE_KEYS = ("partition", "account", "qos", "constraint", "gres", "requirements", "container_image", "campaign_dir")


def is_placeholder(v) -> bool:
    return isinstance(v, str) and bool(PLACEHOLDER.match(v))


def validate(cfg, example: bool = False) -> list[dict]:
    errs: list[dict] = []

    def add(code, key, msg):
        errs.append({"code": code, "key": key, "message": msg})

    def check_keys(obj, allowed, where):
        for k in sorted(set(obj) - allowed):
            add("config.unknown_key", f"{where}{k}", "unknown key (not ignored)")

    def placeholder(v, key) -> bool:
        if is_placeholder(v):
            if not example:
                add("config.placeholder", key, f"placeholder {v!r}: replace it with your site's value")
            return True
        return False

    def pos_int(obj, k, where, minimum=1):
        if k not in obj or placeholder(obj[k], where + k):
            return
        v = obj[k]
        if isinstance(v, bool) or not isinstance(v, int) or v < minimum:
            add("config.bad_value", where + k, f"must be an integer >= {minimum}, got {v!r}")

    def text(obj, k, where, pattern=None):
        if k not in obj or placeholder(obj[k], where + k):
            return
        v = obj[k]
        if not isinstance(v, str) or not v.strip():
            add("config.bad_value", where + k, "must be a non-empty string")
        elif UNSAFE.search(v):
            add("config.bad_value", where + k, "must be one line without control characters or '{{' '}}' (it is rendered into a job file)")
        elif pattern is not None and not pattern.match(v):
            add("config.bad_value", where + k, f"must match {pattern.pattern}")

    def abs_path(v, key):
        if not isinstance(v, str) or not v.startswith("/") or ".." in v.split("/") or UNSAFE.search(v) or "," in v:
            add("config.bad_value", key, "must be an absolute path without '..', commas or control characters")

    if not isinstance(cfg, dict):
        return [{"code": "config.bad_value", "key": "", "message": "the configuration must be a JSON object"}]
    check_keys(cfg, TOP, "")
    for k in ("backend", "campaign_dir", "resources"):
        if k not in cfg:
            add("config.missing_key", k, "required")
    backend = cfg.get("backend")
    if "backend" in cfg and not placeholder(backend, "backend") and backend not in ("slurm", "htcondor"):
        add("config.bad_value", "backend", "must be 'slurm' or 'htcondor'")
    text(cfg, "campaign_dir", "")
    res = cfg.get("resources", {})
    if not isinstance(res, dict):
        add("config.bad_value", "resources", "must be an object")
        res = {}
    check_keys(res, RESOURCES, "resources.")
    for k in ("cpus", "memory_mb", "disk_mb"):
        pos_int(res, k, "resources.")
    pos_int(res, "gpus", "resources.", minimum=0)
    if "time_limit" in res and not placeholder(res["time_limit"], "resources.time_limit") and not (isinstance(res["time_limit"], str) and TIME.match(res["time_limit"])):
        add("config.bad_value", "resources.time_limit", "must be [D-]HH:MM:SS")
    for k in ("throttle", "max_attempts"):
        pos_int(cfg, k, "")
    text(cfg, "job_name", "", NAME)
    if "worker_python" in cfg and not placeholder(cfg["worker_python"], "worker_python"):
        abs_path(cfg["worker_python"], "worker_python")
    pos_int(cfg, "scheduler_timeout_s", "")
    pos_int(cfg, "worker_timeout_s", "")
    if "env_passthrough" in cfg:
        for prob in passthrough_problems(cfg["env_passthrough"]):
            add("config.bad_value", "env_passthrough", prob)
    mon = cfg.get("monitor", {})
    if not isinstance(mon, dict):
        add("config.bad_value", "monitor", "must be an object")
        mon = {}
    check_keys(mon, MONITOR, "monitor.")
    pos_int(mon, "poll_interval_s", "monitor.", minimum=60)
    pos_int(mon, "max_polls", "monitor.")
    pos_int(mon, "deadline_s", "monitor.")
    for other in ("slurm", "htcondor"):
        if other in cfg and backend in ("slurm", "htcondor") and other != backend:
            add("config.unknown_key", other, f"section for another backend ({backend} selected)")
    if backend == "slurm":
        s = cfg.get("slurm")
        if not isinstance(s, dict):
            add("config.missing_key", "slurm", "required for backend slurm")
            s = {}
        check_keys(s, SLURM, "slurm.")
        if "partition" not in s:
            add("config.missing_key", "slurm.partition", "required: the site's partition name")
        for k in SLURM:
            text(s, k, "slurm.", CONSTRAINT if k == "constraint" else NAME)
        if "time_limit" not in res:
            add("config.missing_key", "resources.time_limit", "required for slurm: the walltime, sized from a pilot")
    if backend == "htcondor":
        h = cfg.get("htcondor")
        if not isinstance(h, dict):
            add("config.missing_key", "htcondor", "required for backend htcondor")
            h = {}
        check_keys(h, HTCONDOR, "htcondor.")
        for k, allowed in (("universe", ("vanilla", "container")), ("file_transfer", ("shared-filesystem", "transfer"))):
            if k not in h:
                add("config.missing_key", f"htcondor.{k}", f"required: one of {list(allowed)}")
            elif not placeholder(h[k], f"htcondor.{k}") and h[k] not in allowed:
                add("config.bad_value", f"htcondor.{k}", f"must be one of {list(allowed)}")
        if h.get("universe") == "container" and "container_image" not in h:
            add("config.missing_key", "htcondor.container_image", "required for the container universe")
        for k in ("container_image", "requirements"):
            text(h, k, "htcondor.")
        tif = h.get("transfer_input_files", [])
        if not isinstance(tif, list) or not all(isinstance(x, str) and x for x in tif):
            add("config.bad_value", "htcondor.transfer_input_files", "must be a list of paths")
        else:
            for i, x in enumerate(tif):
                if not is_placeholder(x):
                    abs_path(x, f"htcondor.transfer_input_files[{i}]")
        if "time_limit" in res:
            add("config.unknown_key", "resources.time_limit", "not used by the htcondor backend; enforce walltime with your site's policy")
    return errs


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()
