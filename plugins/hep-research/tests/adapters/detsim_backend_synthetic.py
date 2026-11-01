"""A simulator-free backend of the detector-simulation shared layer (TASK.md 8.2), for the adapter's tests only.

It implements the backend interface with fixed outputs and no simulator, so the shared layer (identity, plan,
rebuild comparison; later lock, runner and commit) can be tested on synthetic inputs. It never launches anything:
build_spec only describes a command (ENV_ROOT/bin/synthetic-sim); the execution-layer tests supply cooperative
programs for it. It lives under tests/, never in adapters/*/assets/ (R-07 (i)), and is injected with
detsim.main(argv, backends={"synthetic": module}).

Capability synthetic.echo 1.0.0: parameters seed (integer), threshold (a quantity in e), events (integer 1-1000),
optional point (a quantity in V/cm, refused outside 100-80000 unless allow_outside_validated_range) and
allow_outside_validated_range; one input of role config is required. build_spec renders run.conf from the
parameters and the config input's hash. collect and observables read ATTEMPT_ROOT/raw/values.csv lines
"quantity,value,unit,event" into detsim-completeness/1 and detsim-observables/1 documents.

make_project(root) writes a complete synthetic project (task, config input, environment record) for the tests.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

NAME = "synthetic"
QUANTITY = {"$ref": "detector_task.json#/$defs/quantity"}
POINT_RANGE_V_PER_CM = (100, 80000)
CAPABILITY = {
    "id": "synthetic.echo",
    "version": "1.0.0",
    "backend": NAME,
    "parameters_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["seed", "threshold", "events"],
        "properties": {
            "seed": {"type": "integer", "minimum": 0, "maximum": 4294967295},
            "threshold": QUANTITY,
            "events": {"type": "integer", "minimum": 1, "maximum": 1000},
            "point": QUANTITY,
            "allow_outside_validated_range": {"type": "boolean"},
        },
    },
    "required_guarantees": {"timeout_kill": "hard", "inputs_unmodified": "hard"},
    "limitations": ["synthetic test backend: no simulator, fixed outputs, no physics"],
}
VALUES_FILE = "ATTEMPT_ROOT/raw/values.csv"
CONFIG_FILE = "ATTEMPT_ROOT/config/run.conf"


def capabilities() -> dict:
    return {CAPABILITY["id"]: json.loads(json.dumps(CAPABILITY))}


def code_files(capability: dict) -> list:
    return [("detsim_backend_synthetic.py", Path(__file__))]


def check(task: dict, capability: dict, input_manifest: list) -> list:
    issues = []
    if not any(item["role"] == "config" for item in input_manifest):
        issues.append({"code": "input-role-missing", "kind": "rejected", "location": "$.inputs",
                       "message": "synthetic.echo needs one input of role config"})
    point = task["parameters"].get("point")
    if point is not None and not task["parameters"].get("allow_outside_validated_range", False):
        mantissa, _, exponent = point["value"].partition("e")
        value = float(mantissa) * 10 ** int(exponent or 0) if point["value"] != "0" else 0.0
        low, high = POINT_RANGE_V_PER_CM
        if point["unit"] != "V/cm" or not low <= value <= high:
            issues.append({"code": "out-of-domain", "kind": "refused", "location": "$.parameters.point",
                           "message": f"point outside the validated range {low}-{high} V/cm",
                           "valid_range": {"min": str(low), "max": str(high), "unit": "V/cm"}})
    return issues


def _rendered(path: str, text: str) -> dict:
    raw = text.encode("utf-8")
    return {"path": path, "encoding": "base64", "content": base64.b64encode(raw).decode("ascii"),
            "sha256": hashlib.sha256(raw).hexdigest()}


def build_spec(task: dict, capability: dict, input_manifest: list, environment: dict, profile: dict) -> dict:
    parameters = task["parameters"]
    config = next(item for item in input_manifest if item["role"] == "config")
    lines = [f"seed = {parameters['seed']}", f"threshold = {parameters['threshold']['value']} "
             f"{parameters['threshold']['unit']}", f"events = {parameters['events']}",
             f"config_sha256 = {config['sha256']}"]
    if "point" in parameters:
        lines.append(f"point = {parameters['point']['value']} {parameters['point']['unit']}")
    variables = environment["variables"]
    return {
        "argv": ["ENV_ROOT/bin/synthetic-sim", CONFIG_FILE, "--input", "INPUT_ROOT/" + config["path"],
                 "--out", VALUES_FILE],
        "environment": {name: variables[name] for name in sorted(variables) if name in ("PATH", "SYNTHETIC_DATA")},
        "files": [_rendered(CONFIG_FILE, "\n".join(lines) + "\n")],
        "expected_outputs": [VALUES_FILE],
        "timeout_s": task["budget"]["timeout_s"],
    }


def _local(attempt_dir: Path, logical: str) -> Path:
    return Path(attempt_dir).joinpath(*logical.split("/")[1:])


def collect(attempt_dir: Path, spec: dict) -> dict:
    missing = [p for p in spec["expected_outputs"] if not _local(attempt_dir, p).is_file()]
    evidence = [{"check": "expected-outputs", "result": "fail" if missing else "pass"}]
    if not missing:
        rows = _local(attempt_dir, VALUES_FILE).read_text(encoding="utf-8").splitlines()
        evidence.append({"check": "values-rows", "result": "pass" if rows else "fail",
                         "detail": f"{len(rows)} row(s)"})
    failed = missing or any(e["result"] != "pass" for e in evidence)
    return {"schema": "detsim-completeness/1", "state": "partial" if failed else "complete", "evidence": evidence,
            "missing_outputs": missing}


def observables(attempt_dir: Path, spec: dict) -> dict:
    path = _local(attempt_dir, VALUES_FILE)
    source = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        quantity, value, unit, event = line.split(",")
        rows.append({"quantity": quantity, "unit": unit, "value": value, "uncertainty_type": "none",
                     "point_kind": "event", "point": int(event), "labels": ["synthetic"], "source_sha256": source})
    return {"schema": "detsim-observables/1", "rows": rows}


def probe(env_root: Path) -> dict:
    return {"backend": NAME, "version": "synthetic 1.0.0"}


IDENTITY = {"kind": "synthetic", "backend_version": "1.0.0", "platform": "any"}
VARIABLES = {"PATH": "ENV_ROOT/bin", "SYNTHETIC_DATA": "ENV_ROOT/share/synthetic"}


def task_document(env_identity: str, **parameters) -> dict:
    params = {"seed": 12345, "threshold": {"value": "600", "unit": "e"}, "events": 10}
    params.update(parameters)
    return {"schema": "detector-task/1", "capability_id": "synthetic.echo", "objective": "synthetic shared-layer test",
            "environment_ref": env_identity, "inputs": [{"role": "config", "path": "inputs/run config.conf"}],
            "parameters": params, "budget": {"timeout_s": 60, "max_output_bytes": 1048576}}


def write_env_record(project: Path, identity: dict | None = None, variables: dict | None = None) -> str:
    """Write the environment record into the project's artifacts directory; returns its env_identity."""
    import detsim_plan  # the shared layer (the caller puts adapters/detector-simulation/assets on sys.path)
    record = detsim_plan.env_record(identity or IDENTITY, variables or VARIABLES, facts=probe(Path("/")),
                                    path_record={"note": "synthetic"})
    path = detsim_plan.env_record_path(detsim_plan.artifacts_root(project), record["env_identity"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")
    return record["env_identity"]


def make_project(root: Path, **parameters) -> Path:
    """A synthetic project under root: inputs/run config.conf, task.json and the environment record."""
    project = Path(root)
    (project / "inputs").mkdir(parents=True, exist_ok=True)
    (project / "inputs" / "run config.conf").write_text("synthetic configuration\nmodel = toy\n", encoding="utf-8")
    env_identity = write_env_record(project)
    (project / "task.json").write_text(json.dumps(task_document(env_identity, **parameters), indent=1),
                                       encoding="utf-8")
    return project
