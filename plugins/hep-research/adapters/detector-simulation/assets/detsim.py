#!/usr/bin/env python3
"""detsim: run a pinned detector-simulation capability (Allpix Squared, Garfield++) as a content-addressed plan.

Verbs (docs/dev/detector-simulation/TASK.md 11):
  describe   capabilities, versions, limitations and required guarantees of a backend; without --backend the
             adapter's backends, runner profiles and contracts. Launches nothing.
  check      static and semantic checks of a task and its project: the task against detector-task/1 and the
             capability's parameter schema, quantities (decimal/1), inputs resolved inside the project, the
             environment record, the backend's own checks. --probe (environment capture) comes with the execution
             layer and answers not-run in this version.
  prepare    the pinned plan (detector-plan/1) and its plan_digest; stateless, writes nothing. --digest-only
             [--replicate N] prints only {"status": "ok", "parameter_digest": <run digest>} (the computational-run
             parameter_digest, for run_workflow.py's incremental mode).
  run, inspect  not part of this version (execution layer, work item W3b): they answer not-run and start nothing.

Usage:
  python3 detsim.py [--backend allpix-squared|garfieldpp] describe
  python3 detsim.py --backend NAME check   --workspace PROJECT --task task.json [--allow-outside-validated-range]
  python3 detsim.py --backend NAME prepare --workspace PROJECT --task task.json [--allow-outside-validated-range]
                                            [--digest-only [--replicate N]]
The task path is relative to the project root (--workspace), never to the current folder. Identity: plan_digest =
canonical_sha256 of the plan (canonical/1); run digest = SHA-256("detsim-run/1\\0" + raw plan_digest + uint32
big-endian replicate); run_id = its first 32 hex characters; replicate 0 ... 2^32 - 1, default 0.

Output: one JSON object with "status" and, unless ok, a stable "error_code", the location and diagnostics.
Exit codes (core/status.py): 0 ok; 1 refused (plan-stale, digest-mismatch, out-of-domain, an invalid environment
record, ...); 2 rejected (malformed or unknown-field task, unreadable file, usage error) or error (internal: an
exception inside detsim); 3 missing-dependency (a backend's module or this platform's runner profile), incomplete
(environment-not-validated) or not-run. Imports only the standard library, core, contracts and its sibling modules;
backends import ROOT or uproot only inside the functions that need them.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import importlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings, core and contracts leaves no __pycache__ (F-10)
ASSETS = Path(__file__).resolve().parent
PLUGIN = ASSETS.parents[2]
for _entry in (str(PLUGIN), str(ASSETS)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from core import hostcaps  # noqa: E402
from core.status import exit_code  # noqa: E402

import detsim_canonical as canonical  # noqa: E402
import detsim_plan as plan_layer  # noqa: E402
import detsim_profile as profiles  # noqa: E402
import detsim_schemas as schemas  # noqa: E402
from detsim_plan import DetsimError  # noqa: E402

ADAPTER_ID = "adapter:detector-simulation"
DEFAULT_BACKENDS = {"allpix-squared": "detsim_backend_allpix", "garfieldpp": "detsim_backend_garfield"}
LATER_VERBS = ("run", "inspect")


class UsageError(Exception):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    """Usage errors become the JSON answer {"status": "rejected", "error_code": "usage"} (exit 2)."""

    def error(self, message):
        raise UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="detsim.py", description=__doc__.splitlines()[0],
                                epilog="See the module docstring (python3 -c 'help(...)') or TASK.md 11 for details.")
    parser.add_argument("--backend", help="allpix-squared or garfieldpp")
    verbs = parser.add_subparsers(dest="verb", required=True, metavar="VERB")
    verbs.add_parser("describe", help="capabilities and limitations; launches nothing")
    for name, text in (("check", "static and semantic checks of a task"), ("prepare", "the pinned plan and digest")):
        verb = verbs.add_parser(name, help=text)
        verb.add_argument("--workspace", required=True, help="the project root (task and inputs resolve against it)")
        verb.add_argument("--task", required=True, help="detector-task/1 file, relative to the project root")
        verb.add_argument("--allow-outside-validated-range", action="store_true",
                          help="set the capability's allow_outside_validated_range parameter (in the hash scope)")
        if name == "check":
            verb.add_argument("--probe", action="store_true", help="environment capture (execution layer; not-run)")
        else:
            verb.add_argument("--digest-only", action="store_true", help="print only the run digest")
            verb.add_argument("--replicate", help="0 ... 2^32 - 1 (with --digest-only), default 0")
    for name in LATER_VERBS:  # their arguments are not read in this version
        verbs.add_parser(name, help="execution layer (not in this version): answers not-run")
    return parser


def load_backend(name: str | None, backends: dict):
    """The backend module for --backend name; not-run when the adapter version has no such module."""
    if name is None:
        raise DetsimError("rejected", "usage", "this verb needs --backend", "--backend", known=sorted(backends))
    if name not in backends:
        raise DetsimError("rejected", "usage", f"unknown backend {name!r}", "--backend", known=sorted(backends))
    target = backends[name]
    if not isinstance(target, str):
        return target
    try:
        return importlib.import_module(target)
    except ImportError as err:
        if getattr(err, "name", None) == target:
            raise DetsimError("not-run", "backend-unavailable", f"backend {name} ({target}.py) is not part of this "
                              "adapter version; nothing was started", "--backend") from None
        raise DetsimError("missing-dependency", "missing-dependency", f"backend {name} cannot be loaded: {err}",
                          "--backend", missing=[getattr(err, "name", None) or str(err)]) from None


def project_root(text: str) -> Path:
    path = Path(text)
    if not path.is_dir():
        raise DetsimError("rejected", "workspace-missing", f"--workspace {text!r} is not a folder", "--workspace")
    return path.resolve()


def read_task(workspace: Path, text: str):
    path = Path(text)
    return plan_layer.read_json(path if path.is_absolute() else workspace / path, "task-unreadable", "task")


def host_profile() -> dict:
    return profiles.profile(profiles.host_profile_id())


def describe(args, backends: dict) -> dict:
    try:
        host = profiles.host_profile_id()
    except hostcaps.UnsupportedPlatform:
        host = None
    if args.backend is None:
        available = {name: ("in-process module" if not isinstance(target, str)
                            else "present" if importlib.util.find_spec(target) is not None
                            else "not in this adapter version") for name, target in sorted(backends.items())}
        return {"status": "ok", "adapter": ADAPTER_ID, "backends": available, "host_profile": host,
                "profiles": profiles.PROFILES, "contracts": sorted(schemas.SCHEMA_FILES),
                "canonicalization": [canonical.CANONICAL_VERSION, canonical.DECIMAL_VERSION],
                "verbs_not_in_this_version": list(LATER_VERBS) + ["check --probe"]}
    backend = load_backend(args.backend, backends)
    found = []
    for capability_id, descriptor in sorted(backend.capabilities().items()):
        found.append({"id": capability_id, "version": descriptor.get("version"),
                      "limitations": descriptor.get("limitations", []),
                      "required_guarantees": descriptor.get("required_guarantees", {}),
                      "parameters": sorted(descriptor.get("parameters_schema", {}).get("properties", {}))})
    return {"status": "ok", "backend": args.backend, "capabilities": found, "host_profile": host}


def check(args, backends: dict) -> dict:
    if args.probe:
        return {"status": "not-run", "error_code": "not-implemented", "message": "check --probe (environment "
                "capture) comes with the execution layer; nothing was probed or written", "location": "--probe"}
    workspace = project_root(args.workspace)
    task = read_task(workspace, args.task)
    backend = load_backend(args.backend, backends)
    profile_doc = host_profile()
    task, capability = plan_layer.checked_task(task, backend, args.allow_outside_validated_range)
    manifest = plan_layer.resolve_inputs(task, workspace)
    environment = plan_layer.load_env_record(plan_layer.artifacts_root(workspace), task["environment_ref"])
    plan_layer.raise_backend_issues(backend.check(task, capability, manifest))
    return {"status": "ok", "backend": args.backend, "capability": {"id": capability["id"],
                                                                     "version": capability["version"]},
            "inputs": manifest, "environment": {"env_identity": environment["env_identity"]},
            "profile": profile_doc["id"],
            "guarantee_shortfalls": profiles.shortfalls(capability["required_guarantees"], profile_doc)}


def prepare(args, backends: dict) -> dict:
    if args.replicate is not None and not args.digest_only:
        raise DetsimError("rejected", "usage", "--replicate applies only with --digest-only", "--replicate")
    replicate = canonical.parse_replicate(args.replicate) if args.replicate is not None else 0
    workspace = project_root(args.workspace)
    task = read_task(workspace, args.task)
    backend = load_backend(args.backend, backends)
    plan, plan_digest = plan_layer.assemble_plan(task, workspace, backend, host_profile(),
                                                 allow_outside_validated_range=args.allow_outside_validated_range)
    if args.digest_only:
        return {"status": "ok", "parameter_digest": canonical.run_digest(plan_digest, replicate)}
    return {"status": "ok", "plan_digest": plan_digest, "plan": plan}


def later_verb(args, backends: dict) -> dict:
    return {"status": "not-run", "error_code": "not-implemented", "message": f"{args.verb} comes with the execution "
            "layer (work item W3b) and is not part of this version; nothing was started", "location": args.verb}


VERBS = {"describe": describe, "check": check, "prepare": prepare, "run": later_verb, "inspect": later_verb}


def main(argv=None, backends=None) -> int:
    """Run one verb and print its JSON answer; every exception becomes a JSON answer (error / internal, exit 2)."""
    known = dict(DEFAULT_BACKENDS if backends is None else backends)
    try:
        args, unread = build_parser().parse_known_args(argv)
        if unread and args.verb not in LATER_VERBS:
            raise UsageError(f"unrecognized arguments: {' '.join(unread)}")
        answer = VERBS[args.verb](args, known)
    except UsageError as err:
        answer = {"status": "rejected", "error_code": "usage", "message": str(err)}
    except DetsimError as err:
        answer = err.answer()
    except canonical.CanonicalError as err:
        answer = {"status": "rejected", "error_code": err.code, "message": str(err)}
    except hostcaps.UnsupportedPlatform as err:
        answer = dict(err.report(), error_code="unsupported-platform", message=str(err))
    except Exception as err:  # noqa: BLE001 - every exception is reported as JSON (TASK.md 11.3)
        answer = {"status": "error", "error_code": "internal", "message": f"{type(err).__name__}: {err}"}
    print(json.dumps(answer, indent=1, ensure_ascii=True))
    return exit_code(answer["status"])


if __name__ == "__main__":
    sys.exit(main())
