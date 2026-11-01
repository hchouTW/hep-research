"""Plan assembly, rebuild comparison and the environment record of the detector-simulation shared layer.

A module of detsim.py (TASK.md 9.1-9.3, 10.1 and 10.2 steps 2-3 under docs/dev/detector-simulation/).

prepare (stateless; never simulates, downloads or writes): parse and check the task (detector-task/1), refuse unknown
fields; find the capability in the trusted backend and validate the parameters with its schema; normalize every
{value, unit} quantity (decimal/1); resolve each input relative to the project root (never the current folder) into
the input manifest (role, relative path, size, SHA-256); read the environment record
artifacts_root/detector-simulation/.env/<environment_ref>.json (no live probing); call the backend's check and
build_spec; assemble the plan with the whole hash scope of TASK.md 9.2 (task, capability id, version and descriptor
hash, hashes of the shared-layer modules, the backend's code files and the four schemas, environment identity and
variables, input manifest, runner profile, ExecutionSpec with rendered file bytes, canonicalization versions); check
it (detsim_schemas.check_plan) and return it with its plan_digest (canonical_sha256).

Rebuild comparison (run step 3): the whole plan is rebuilt from the task recorded in it with the current trusted
code, the current environment record, the current profile and the current input files, and the canonical bytes are
compared. Any difference, or a plan that can no longer be rebuilt, is refused with plan-stale and the mismatched
fields as JSON pointers. This checks equality with the trusted result, not tampering. check_plan_digest compares an
optional --plan-digest with the plan's digest (digest-mismatch).

Environment record (format detsim-env/1, hidden, not an artifact; written by check --probe): {"format",
"env_identity", "identity", "variables", "facts", "path_record"}. env_identity is the canonical_sha256 of identity
(content only: image digest, or view + platform + commit, plus dataset hashes); identity and the allowlisted
variables (with the environment root written ENV_ROOT) enter the plan; facts and the path-bearing path_record do not.

Backend interface (TASK.md 8.2; a module object): NAME; capabilities() -> {capability id: descriptor} with id,
version, backend, parameters_schema, required_guarantees, limitations; code_files(capability) -> [(key, path)] of the
backend module, templates and driver; check(task, capability, input_manifest) -> [issue] where an issue is {code,
message, kind: "refused" | "rejected", location?}; build_spec(task, capability, input_manifest, environment,
profile) -> ExecutionSpec; and collect, observables, probe (used by run and check --probe).

Errors are DetsimError(status, error_code, message, location, **details); status is a core/status.py run status.
"""
from __future__ import annotations

import sys

if __spec__ is None:  # run as a file (tests/skills/test_cli_robustness.py): a module of detsim.py, not a command
    print(__doc__.splitlines()[0] + "\nA module of detsim.py, not a command: python3 detsim.py --help")
    sys.exit(0 if sys.argv[1:] in ([], ["--help"], ["-h"]) else 2)

import copy  # noqa: E402
import hashlib  # noqa: E402
from pathlib import Path  # noqa: E402

from contracts.project import CONFIG_NAME, DEFAULT_ARTIFACTS_DIR  # noqa: E402
from contracts.schema import validate  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

import detsim_canonical as canonical  # noqa: E402
import detsim_schemas as schemas  # noqa: E402

ASSETS_DIR = Path(__file__).resolve().parent
ADAPTER_FOLDER = "detector-simulation"  # artifacts_root/detector-simulation/
ENV_FOLDER = ".env"
ENV_RECORD_FORMAT = "detsim-env/1"
PLAN_SCHEMA = "detector-plan/1"
OUTSIDE_RANGE_PARAMETER = "allow_outside_validated_range"
MAX_DIFF_FIELDS = 100
DESCRIPTOR_KEYS = ("id", "version", "backend", "parameters_schema", "required_guarantees", "limitations")


class DetsimError(Exception):
    """A refusal or failure with a stable error_code; answer() is the JSON detsim prints."""

    def __init__(self, status: str, error_code: str, message: str, location: str | None = None, **details):
        super().__init__(message)
        self.status, self.error_code, self.message, self.location, self.details = (status, error_code, message,
                                                                                   location, details)

    def answer(self) -> dict:
        out = {"status": self.status, "error_code": self.error_code, "message": self.message}
        if self.location is not None:
            out["location"] = self.location
        out.update(self.details)
        return out


def sha256_file(path: Path) -> tuple[int, str]:
    """(size in bytes, SHA-256 hex) of a file, read in 1 MiB blocks."""
    h, size = hashlib.sha256(), 0
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
            size += len(block)
    return size, h.hexdigest()


def read_json(path: Path, error_code: str, what: str):
    """Strict JSON (no duplicate keys, no NaN) from a file; rejected with error_code when unreadable or malformed."""
    try:
        raw = Path(path).read_bytes()
    except OSError as err:
        raise DetsimError("rejected", error_code, f"cannot read the {what}: {err.strerror or err}", str(path)) from None
    try:
        return canonical.load_json_strict(raw)
    except canonical.CanonicalError as err:
        raise DetsimError("rejected", error_code, f"the {what} is not strict JSON ({err.code}): {err}", str(path),
                          reason=err.code) from None


def artifacts_root(workspace: Path) -> Path:
    """The project's artifacts directory: artifacts_dir of hep-research.project.json, else the repository default."""
    workspace = Path(workspace)
    config = workspace / CONFIG_NAME
    artifacts_dir = DEFAULT_ARTIFACTS_DIR
    if config.is_file():
        doc = read_json(config, "project-config-invalid", "project configuration")
        if isinstance(doc, dict) and isinstance(doc.get("artifacts_dir"), str):
            artifacts_dir = doc["artifacts_dir"]
    return (workspace / artifacts_dir).resolve()


def env_record_path(artifacts: Path, env_identity: str) -> Path:
    return Path(artifacts) / ADAPTER_FOLDER / ENV_FOLDER / f"{env_identity}.json"


def env_record(identity: dict, variables: dict, facts: dict | None = None, path_record: dict | None = None) -> dict:
    """A detsim-env/1 record; env_identity is computed from identity (content only)."""
    return {"format": ENV_RECORD_FORMAT, "env_identity": canonical.digest(identity), "identity": identity,
            "variables": variables, "facts": facts or {}, "path_record": path_record or {}}


def load_env_record(artifacts: Path, env_identity: str) -> dict:
    """The in-scope part {env_identity, identity, variables} of a validated environment record."""
    path = env_record_path(artifacts, env_identity)
    if not path.is_file():
        raise DetsimError("incomplete", "environment-not-validated",
                          f"no environment record {env_identity}: validate the environment with check --probe first",
                          "$.environment_ref", record=str(path))
    try:
        doc = canonical.load_json_strict(path.read_bytes())
    except (OSError, canonical.CanonicalError) as err:
        raise DetsimError("refused", "environment-record-invalid", f"the environment record is unreadable: {err}",
                          "$.environment_ref", record=str(path)) from None
    problems = []
    if not isinstance(doc, dict) or doc.get("format") != ENV_RECORD_FORMAT:
        problems.append(f"format is not {ENV_RECORD_FORMAT}")
    else:
        identity, variables = doc.get("identity"), doc.get("variables")
        if not isinstance(identity, dict) or not isinstance(variables, dict):
            problems.append("identity and variables are objects")
        else:
            problems += [f"{i['path']}: {i['code']}" for i in canonical.check_hash_scope({"identity": identity,
                                                                                         "variables": variables})]
            problems += [f"variable {n!r}" for n, v in variables.items()
                         if schemas.ENV_NAME.fullmatch(n) is None or not isinstance(v, str)]
            if not problems and canonical.digest(identity) != env_identity:
                problems.append("the canonical_sha256 of identity is not the record's name")
            if doc.get("env_identity") != env_identity:
                problems.append("env_identity is not the record's name")
    if problems:
        raise DetsimError("refused", "environment-record-invalid", f"environment record {env_identity}: "
                          + "; ".join(problems[:5]), "$.environment_ref", record=str(path))
    return {"env_identity": env_identity, "identity": doc["identity"], "variables": doc["variables"]}


def capability_of(backend, capability_id: str) -> dict:
    """The trusted descriptor of capability_id in backend; rejected unknown-capability when it has none."""
    descriptors = backend.capabilities()
    if capability_id not in descriptors:
        raise DetsimError("rejected", "unknown-capability", f"backend {backend.NAME} has no capability "
                          f"{capability_id!r}", "$.capability_id", known=sorted(descriptors))
    descriptor = descriptors[capability_id]
    problems = [k for k in DESCRIPTOR_KEYS if k not in descriptor]
    if descriptor.get("id") != capability_id or descriptor.get("backend") != backend.NAME:
        problems.append("id or backend")
    problems += [i["path"] + " " + i["code"] for i in canonical.check_hash_scope(descriptor)]
    if problems:
        raise DetsimError("error", "capability-descriptor-invalid", f"descriptor {capability_id}: {problems[:5]}")
    return descriptor


def _quantities_normalized(value, path: str):
    if isinstance(value, dict):
        if set(value) == {"value", "unit"} and isinstance(value["value"], str):
            try:
                return {"value": canonical.normalize_decimal(value["value"]), "unit": value["unit"]}
            except canonical.CanonicalError as err:
                raise DetsimError("rejected", "decimal-invalid", str(err), path + ".value") from None
        return {k: _quantities_normalized(v, f"{path}.{k}") for k, v in value.items()}
    if isinstance(value, list):
        return [_quantities_normalized(v, f"{path}[{i}]") for i, v in enumerate(value)]
    return value


def checked_task(task, backend, allow_outside_validated_range: bool = False) -> tuple[dict, dict]:
    """(normalized task, capability descriptor) after every static check of the task; DetsimError otherwise."""
    findings = schemas.check_task(task)
    if findings:
        raise DetsimError("rejected", "task-invalid", f"{len(findings)} finding(s) in the task, first: "
                          f"{findings[0]['message']}", findings[0]["path"], findings=findings[:50])
    capability = capability_of(backend, task["capability_id"])
    task = copy.deepcopy(task)
    if allow_outside_validated_range:
        if OUTSIDE_RANGE_PARAMETER not in capability["parameters_schema"].get("properties", {}):
            raise DetsimError("rejected", "option-not-applicable", f"capability {capability['id']} has no "
                              f"{OUTSIDE_RANGE_PARAMETER} parameter", "--allow-outside-validated-range")
        task["parameters"][OUTSIDE_RANGE_PARAMETER] = True
    task["parameters"] = _quantities_normalized(task["parameters"], "$.parameters")
    errors = validate(task["parameters"], capability["parameters_schema"], Vocabulary()).errors
    if errors:
        found = [dict(f.as_dict(), path="$.parameters" + f.path[1:]) for f in errors]
        raise DetsimError("rejected", "parameters-invalid", f"{len(found)} finding(s) in the parameters of "
                          f"{capability['id']}, first: {found[0]['message']}", found[0]["path"], findings=found[:50])
    return task, capability


def resolve_inputs(task: dict, workspace: Path) -> list[dict]:
    """The input manifest: each input resolved inside the project root, with size and SHA-256."""
    root = Path(workspace).resolve()
    manifest = []
    for i, item in enumerate(task["inputs"]):
        where = f"$.inputs[{i}].path"
        try:
            real = root.joinpath(*item["path"].split("/")).resolve(strict=True)
        except (OSError, RuntimeError):
            raise DetsimError("rejected", "input-missing", f"input {item['path']!r} does not exist in the project",
                              where) from None
        if real != root and root not in real.parents:
            raise DetsimError("rejected", "input-outside-project", f"input {item['path']!r} resolves outside the "
                              "project root", where)
        if not real.is_file():
            raise DetsimError("rejected", "input-not-a-file", f"input {item['path']!r} is not a regular file", where)
        size, sha = sha256_file(real)
        manifest.append({"role": item["role"], "path": item["path"], "size": size, "sha256": sha})
    return manifest


def _file_hashes(pairs) -> dict:
    out = {}
    for key, path in pairs:
        if key in out:
            raise DetsimError("error", "code-files-invalid", f"code file key {key!r} listed twice")
        out[key] = sha256_file(Path(path))[1]
    return out


def code_hashes(backend, capability: dict, assets_dir: Path | None = None) -> dict:
    """SHA-256 of every shared-layer module (assets/detsim*.py except backends), of the backend's code files and of
    the four contract schemas. assets_dir is for tests that rebuild against a changed copy of the shared layer."""
    assets = Path(assets_dir) if assets_dir is not None else ASSETS_DIR
    shared = [(p.name, p) for p in sorted(assets.glob("detsim*.py")) if not p.name.startswith("detsim_backend_")]
    return {"shared_layer": _file_hashes(shared), "backend": _file_hashes(backend.code_files(capability)),
            "schemas": schemas.schema_file_hashes()}


def raise_backend_issues(issues) -> None:
    if not issues:
        return
    kinds = {i.get("kind") for i in issues}
    status = "rejected" if "rejected" in kinds or not kinds <= {"refused"} else "refused"
    first = issues[0]
    raise DetsimError(status, first.get("code", "backend-check"), first.get("message", ""), first.get("location"),
                      issues=issues[:50])


def plan_profile(profile_doc: dict) -> dict:
    return {k: copy.deepcopy(profile_doc[k]) for k in ("id", "level", "guarantees", "policy")}


def assemble_plan(task, workspace: Path, backend, profile_doc: dict, assets_dir: Path | None = None,
                  allow_outside_validated_range: bool = False) -> tuple[dict, str]:
    """prepare (TASK.md 10.1): (plan, plan_digest). Launches, downloads and writes nothing."""
    task, capability = checked_task(task, backend, allow_outside_validated_range)
    manifest = resolve_inputs(task, workspace)
    environment = load_env_record(artifacts_root(workspace), task["environment_ref"])
    raise_backend_issues(backend.check(task, capability, manifest))
    profile_in_scope = plan_profile(profile_doc)
    spec = backend.build_spec(copy.deepcopy(task), capability, copy.deepcopy(manifest), copy.deepcopy(environment),
                              copy.deepcopy(profile_in_scope))
    plan = {
        "schema": PLAN_SCHEMA,
        "canonicalization": {"json": canonical.CANONICAL_VERSION, "decimal": canonical.DECIMAL_VERSION},
        "task": task,
        "capability": {"id": capability["id"], "version": capability["version"], "backend": backend.NAME,
                       "descriptor_sha256": canonical.digest(capability),
                       "required_guarantees": copy.deepcopy(capability["required_guarantees"])},
        "code": code_hashes(backend, capability, assets_dir),
        "environment": environment,
        "inputs": manifest,
        "profile": profile_in_scope,
        "execution": spec,
    }
    findings = schemas.check_plan(plan)
    if isinstance(spec, dict) and isinstance(spec.get("timeout_s"), int) and spec["timeout_s"] > task["budget"]["timeout_s"]:
        findings.append({"severity": "error", "path": "$.execution.timeout_s", "code": "execution.timeout_over_budget",
                         "message": "the backend's timeout exceeds the task budget"})
    if findings:
        raise DetsimError("error", "plan-invalid", f"the backend produced an invalid plan: {findings[0]['message']}",
                          findings[0]["path"], findings=findings[:50])
    return plan, canonical.digest(plan)


def load_plan(path: Path) -> dict:
    """A plan file: the plan object, or prepare's answer {"status": "ok", "plan": ...}; rejected when malformed."""
    doc = read_json(path, "plan-unreadable", "plan")
    if isinstance(doc, dict) and "plan" in doc and "schema" not in doc:
        doc = doc["plan"]
    findings = schemas.check_plan(doc)
    if findings:
        raise DetsimError("rejected", "plan-invalid", f"{len(findings)} finding(s) in the plan, first: "
                          f"{findings[0]['message']}", findings[0]["path"], findings=findings[:50])
    return doc


def check_plan_digest(plan: dict, expected: str | None) -> str:
    """The plan's digest; refused digest-mismatch when expected (--plan-digest) is given and differs."""
    actual = canonical.digest(plan)
    if expected is None:
        return actual
    if not isinstance(expected, str) or canonical.SHA256_HEX.fullmatch(expected) is None:
        raise DetsimError("rejected", "digest-format", f"--plan-digest {expected!r} is not 64 lowercase hex "
                          "characters", "--plan-digest")
    if expected != actual:
        raise DetsimError("refused", "digest-mismatch", "the plan's digest is not the --plan-digest given",
                          "--plan-digest", expected=expected, actual=actual)
    return actual


def _pointer(parts) -> str:
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def diff_fields(planned, rebuilt, parts: tuple = ()) -> list[str]:
    """JSON pointers of every place where planned and rebuilt differ (leaves, added or removed keys, list lengths)."""
    if isinstance(planned, dict) and isinstance(rebuilt, dict):
        out = []
        for key in sorted(set(planned) | set(rebuilt)):
            if key not in planned or key not in rebuilt:
                out.append(_pointer(parts + (key,)))
            else:
                out += diff_fields(planned[key], rebuilt[key], parts + (key,))
        return out
    if isinstance(planned, list) and isinstance(rebuilt, list):
        out = [_pointer(parts)] if len(planned) != len(rebuilt) else []
        for i, (a, b) in enumerate(zip(planned, rebuilt)):
            out += diff_fields(a, b, parts + (i,))
        return out
    same = type(planned) is type(rebuilt) and planned == rebuilt
    return [] if same else [_pointer(parts)]


_STALE_FIELD = {"input-": "/inputs", "environment-": "/environment", "unknown-capability": "/capability",
                "capability-": "/capability", "code-": "/code", "task-": "/task", "parameters-": "/task/parameters",
                "decimal-": "/task/parameters", "option-": "/task/parameters"}


def rebuild_comparison(plan: dict, workspace: Path, backend, profile_doc: dict,
                       assets_dir: Path | None = None) -> str:
    """Run step 3: rebuild the whole plan from its task with the current trusted code, environment record, profile
    and inputs and compare the canonical bytes; the plan_digest, or refused plan-stale with the mismatched fields."""
    try:
        rebuilt, rebuilt_digest = assemble_plan(copy.deepcopy(plan["task"]), workspace, backend, profile_doc,
                                                assets_dir)
    except DetsimError as err:
        field = next((v for k, v in _STALE_FIELD.items() if err.error_code.startswith(k)), "")
        raise DetsimError("refused", "plan-stale", f"the plan cannot be rebuilt now ({err.error_code}: {err.message});"
                          " run prepare again", err.location, mismatched_fields=[field], rebuild_error=err.answer())
    if canonical.canonical_bytes(rebuilt) != canonical.canonical_bytes(plan):
        fields = diff_fields(plan, rebuilt)
        raise DetsimError("refused", "plan-stale", f"{len(fields)} field(s) differ from the plan rebuilt with the "
                          "current code, environment record, profile and inputs; run prepare again",
                          mismatched_fields=fields[:MAX_DIFF_FIELDS], mismatched_count=len(fields),
                          plan_digest=canonical.digest(plan), rebuilt_digest=rebuilt_digest)
    return rebuilt_digest
