"""The four detector-simulation contracts, validated by schema and by the code checks the schemas cannot express.

A module of detsim.py (TASK.md 9.5 under docs/dev/detector-simulation/): detector-task/1 (contracts/schemas/
detector_task.json), detector-plan/1 (detector_plan.json), detsim-completeness/1 (detsim_completeness.json) and
detsim-observables/1 (detsim_observables.json, decision D-W1-2). Each check_* function returns findings
{severity, path, code, message}; an empty list of errors means valid.

The repository validator (contracts/schema.py) implements a keyword subset and applies "pattern" with re.search, so
"^...$" still accepts a trailing newline. The code checks here apply every pattern again with re.fullmatch and add
what no supported keyword can say: '.' and '..' path segments, unique input paths and file paths, environment
variable names, base64 decoding and file hashes, the hash-scope rules of detsim_canonical.check_hash_scope (no float
anywhere in a task or plan), the completeness state rules and the observables uncertainty rules.
"""
from __future__ import annotations

import sys

if __spec__ is None:  # run as a file (tests/skills/test_cli_robustness.py): a module of detsim.py, not a command
    print(__doc__.splitlines()[0] + "\nA module of detsim.py, not a command: python3 detsim.py --help")
    sys.exit(0 if sys.argv[1:] in ([], ["--help"], ["-h"]) else 2)

import base64  # noqa: E402
import binascii  # noqa: E402
import hashlib  # noqa: E402
import re  # noqa: E402

from contracts.schema import SCHEMA_DIR, load_schema, validate  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

import detsim_canonical as canonical  # noqa: E402

SCHEMA_FILES = {
    "detector-task/1": "detector_task.json",
    "detector-plan/1": "detector_plan.json",
    "detsim-completeness/1": "detsim_completeness.json",
    "detsim-observables/1": "detsim_observables.json",
}
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*", re.ASCII)
LOGICAL_ROOTS = ("ENV_ROOT", "INPUT_ROOT", "ATTEMPT_ROOT")
_ROOT_TOKEN = re.compile(r"(?:^|[=:,;\s])(/|~)")


def _finding(path: str, code: str, message: str) -> dict:
    return {"severity": "error", "path": path, "code": code, "message": message}


def schema_findings(value, schema_name: str) -> list[dict]:
    return [f.as_dict() for f in validate(value, schema_name, Vocabulary()).errors]


def _defs(schema_file: str) -> dict:
    return load_schema(schema_file).get("$defs", {})


def _full(pattern_owner: dict) -> re.Pattern:
    return re.compile(pattern_owner["pattern"], re.ASCII)


def _fullmatch_findings(value, pattern_owner: dict, path: str) -> list[dict]:
    if isinstance(value, str) and _full(pattern_owner).fullmatch(value) is None:
        return [_finding(path, "pattern.fullmatch", f"{value[:80]!r} does not match {pattern_owner['pattern']} as a "
                                                    "whole (re.fullmatch)")]
    return []


def _scope_findings(value, prefix: str) -> list[dict]:
    return [_finding(prefix + i["path"][1:], f"hash_scope.{i['code']}", i["message"])
            for i in canonical.check_hash_scope(value)]


def _path_segment_findings(path_text, where: str) -> list[dict]:
    if isinstance(path_text, str) and any(seg in (".", "..") for seg in path_text.split("/")):
        return [_finding(where, "path.dot_segment", f"{path_text!r}: no '.' or '..' segments")]
    return []


def _quantity_paths(value, path: str):
    """(path, quantity object) for every {value, unit} object inside value."""
    if isinstance(value, dict):
        if set(value) == {"value", "unit"}:
            yield path, value
            return
        for key, item in value.items():
            yield from _quantity_paths(item, f"{path}.{key}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from _quantity_paths(item, f"{path}[{i}]")


def check_task(task) -> list[dict]:
    """detector-task/1: schema, fullmatch of every pattern, path segments, unique input paths, quantities, hash scope."""
    out = schema_findings(task, "detector_task.json")
    if not isinstance(task, dict):
        return out
    props, defs = load_schema("detector_task.json")["properties"], _defs("detector_task.json")
    out += _fullmatch_findings(task.get("capability_id"), props["capability_id"], "$.capability_id")
    out += _fullmatch_findings(task.get("environment_ref"), defs["sha256"], "$.environment_ref")
    seen = set()
    for i, item in enumerate(task.get("inputs") if isinstance(task.get("inputs"), list) else []):
        if not isinstance(item, dict):
            continue
        out += _fullmatch_findings(item.get("role"), defs["input"]["properties"]["role"], f"$.inputs[{i}].role")
        out += _fullmatch_findings(item.get("path"), defs["relative_path"], f"$.inputs[{i}].path")
        out += _path_segment_findings(item.get("path"), f"$.inputs[{i}].path")
        if item.get("path") in seen:
            out.append(_finding(f"$.inputs[{i}].path", "inputs.duplicate_path", f"{item.get('path')!r} is listed twice"))
        seen.add(item.get("path"))
    for where, quantity in _quantity_paths(task.get("parameters"), "$.parameters"):
        out += _fullmatch_findings(quantity.get("value"), defs["decimal"], where + ".value")
        out += _fullmatch_findings(quantity.get("unit"), defs["unit"], where + ".unit")
        if not isinstance(quantity.get("value"), str):
            out.append(_finding(where + ".value", "quantity.value_not_string", "a quantity's value is a decimal string"))
    out += _scope_findings(task, "$")
    return out


def _execution_findings(spec, policy: dict) -> list[dict]:
    """The ExecutionSpec rules of TASK.md 8.2 beyond the schema: logical roots, names, base64 bytes and hashes."""
    out = []
    if not isinstance(spec, dict):
        return out
    attempt = _defs("detector_plan.json")["attempt_path"]
    argv = spec.get("argv") if isinstance(spec.get("argv"), list) else []
    if argv and not (isinstance(argv[0], str) and argv[0].startswith("ENV_ROOT/")):
        out.append(_finding("$.execution.argv[0]", "execution.executable_root", "the backend executable is "
                                                                                "ENV_ROOT/..., never a host path"))
    strings = [(f"$.execution.argv[{i}]", a) for i, a in enumerate(argv)]
    environment = spec.get("environment") if isinstance(spec.get("environment"), dict) else {}
    for name, item in environment.items():
        if ENV_NAME.fullmatch(name) is None:
            out.append(_finding(f"$.execution.environment.{name}", "execution.variable_name",
                                f"{name!r} is not an environment variable name"))
        strings.append((f"$.execution.environment.{name}", item))
    for where, text in strings:
        if isinstance(text, str) and _ROOT_TOKEN.search(text):
            out.append(_finding(where, "execution.host_path", f"{text[:80]!r} names a host path; use ENV_ROOT, "
                                                              "INPUT_ROOT or ATTEMPT_ROOT"))
    paths = []
    for i, item in enumerate(spec.get("files") if isinstance(spec.get("files"), list) else []):
        if not isinstance(item, dict):
            continue
        where = f"$.execution.files[{i}]"
        out += _fullmatch_findings(item.get("path"), attempt, where + ".path")
        paths.append(item.get("path"))
        try:
            raw = base64.b64decode(item.get("content", ""), validate=True)
        except (binascii.Error, ValueError, TypeError):
            out.append(_finding(where + ".content", "execution.base64", "content is not strict base64"))
            continue
        if base64.b64encode(raw).decode("ascii") != item.get("content"):
            out.append(_finding(where + ".content", "execution.base64", "content is not canonical base64"))
        if len(raw) > policy.get("rendered_file_max_bytes", 1048576):
            out.append(_finding(where, "execution.file_too_large", f"{len(raw)} bytes: a file above "
                                                                   f"{policy.get('rendered_file_max_bytes')} bytes is "
                                                                   "an input, not a rendered file"))
        if hashlib.sha256(raw).hexdigest() != item.get("sha256"):
            out.append(_finding(where + ".sha256", "execution.file_hash", "sha256 is not the hash of the content"))
    for i, item in enumerate(spec.get("expected_outputs") if isinstance(spec.get("expected_outputs"), list) else []):
        out += _fullmatch_findings(item, attempt, f"$.execution.expected_outputs[{i}]")
        paths.append(item)
    duplicates = sorted({p for p in paths if isinstance(p, str) and paths.count(p) > 1})
    if duplicates:
        out.append(_finding("$.execution", "execution.duplicate_path", f"paths named twice: {duplicates}"))
    return out


def check_plan(plan) -> list[dict]:
    """detector-plan/1: schema, the embedded task's checks, quantities normalized, ExecutionSpec rules, hash scope."""
    out = schema_findings(plan, "detector_plan.json")
    if not isinstance(plan, dict):
        return out
    task = plan.get("task")
    out += [dict(f, path="$.task" + f["path"][1:]) for f in check_task(task)
            if not f["code"].startswith(("schema.", "hash_scope."))]  # both are reported for the whole plan
    for where, quantity in _quantity_paths(task.get("parameters") if isinstance(task, dict) else None,
                                           "$.task.parameters"):
        if not canonical.is_normalized_decimal(quantity.get("value")):
            out.append(_finding(where + ".value", "quantity.not_normalized", "a plan carries decimal/1 values"))
    defs = _defs("detector_task.json")
    for i, item in enumerate(plan.get("inputs") if isinstance(plan.get("inputs"), list) else []):
        if isinstance(item, dict):
            out += _fullmatch_findings(item.get("path"), defs["relative_path"], f"$.inputs[{i}].path")
            out += _path_segment_findings(item.get("path"), f"$.inputs[{i}].path")
            out += _fullmatch_findings(item.get("sha256"), defs["sha256"], f"$.inputs[{i}].sha256")
    environment = plan.get("environment") if isinstance(plan.get("environment"), dict) else {}
    out += _fullmatch_findings(environment.get("env_identity"), defs["sha256"], "$.environment.env_identity")
    if isinstance(environment.get("identity"), dict) and not canonical.check_hash_scope(environment["identity"]):
        if canonical.digest(environment["identity"]) != environment.get("env_identity"):
            out.append(_finding("$.environment.env_identity", "environment.identity_hash",
                                "env_identity is not the canonical_sha256 of identity"))
    for name in (environment.get("variables") if isinstance(environment.get("variables"), dict) else {}):
        if ENV_NAME.fullmatch(name) is None:
            out.append(_finding(f"$.environment.variables.{name}", "execution.variable_name",
                                f"{name!r} is not an environment variable name"))
    profile = plan.get("profile") if isinstance(plan.get("profile"), dict) else {}
    policy = profile.get("policy") if isinstance(profile.get("policy"), dict) else {}
    out += _execution_findings(plan.get("execution"), policy)
    out += _scope_findings(plan, "$")
    return out


def check_completeness(doc) -> list[dict]:
    """detsim-completeness/1: schema, fullmatch, unique check names and the state rules."""
    out = schema_findings(doc, "detsim_completeness.json")
    if not isinstance(doc, dict):
        return out
    props = load_schema("detsim_completeness.json")["properties"]
    out += _fullmatch_findings(doc.get("run_id"), props["run_id"], "$.run_id")
    evidence = [e for e in doc.get("evidence", []) if isinstance(e, dict)] if isinstance(doc.get("evidence"), list) else []
    names = [e.get("check") for e in evidence]
    for i, e in enumerate(evidence):
        out += _fullmatch_findings(e.get("check"), props["evidence"]["items"]["properties"]["check"],
                                   f"$.evidence[{i}].check")
    if len(names) != len(set(map(str, names))):
        out.append(_finding("$.evidence", "completeness.duplicate_check", "a check is listed twice"))
    missing = doc.get("missing_outputs") if isinstance(doc.get("missing_outputs"), list) else []
    not_passed = [e.get("check") for e in evidence if e.get("result") != "pass"]
    if doc.get("state") == "complete" and (not_passed or missing):
        out.append(_finding("$.state", "completeness.complete_with_failures",
                            f"complete, but checks {not_passed} did not pass or outputs {missing} are missing"))
    if doc.get("state") in ("partial", "invalid") and not (not_passed or missing):
        out.append(_finding("$.state", "completeness.failure_without_evidence",
                            f"{doc.get('state')} needs a failed or inconclusive check or a missing output"))
    return out


def check_observables(doc) -> list[dict]:
    """detsim-observables/1: schema, fullmatch, the uncertainty rules and unique labels per row."""
    out = schema_findings(doc, "detsim_observables.json")
    if not isinstance(doc, dict):
        return out
    row_props = _defs("detsim_observables.json")["row"]["properties"]
    task_defs = _defs("detector_task.json")
    out += _fullmatch_findings(doc.get("run_id"), load_schema("detsim_observables.json")["properties"]["run_id"],
                               "$.run_id")
    for i, row in enumerate(doc.get("rows") if isinstance(doc.get("rows"), list) else []):
        if not isinstance(row, dict):
            continue
        where = f"$.rows[{i}]"
        for key, owner in (("quantity", row_props["quantity"]), ("unit", task_defs["unit"]),
                           ("value", task_defs["normalized_decimal"]), ("uncertainty", task_defs["normalized_decimal"]),
                           ("detector", row_props["detector"]), ("component", row_props["component"]),
                           ("source_sha256", task_defs["sha256"])):
            out += _fullmatch_findings(row.get(key), owner, f"{where}.{key}")
        kind = row.get("uncertainty_type")
        if kind == "none" and "uncertainty" in row:
            out.append(_finding(where + ".uncertainty", "observables.uncertainty_for_none",
                                "uncertainty_type none carries no uncertainty"))
        if kind != "none" and "uncertainty" not in row:
            out.append(_finding(where + ".uncertainty", "observables.uncertainty_missing",
                                f"uncertainty_type {kind!r} needs an uncertainty"))
        if isinstance(row.get("uncertainty"), str) and row["uncertainty"].startswith("-"):
            out.append(_finding(where + ".uncertainty", "observables.uncertainty_negative", "an uncertainty is >= 0"))
        labels = row.get("labels") if isinstance(row.get("labels"), list) else []
        if len(labels) != len(set(map(str, labels))):
            out.append(_finding(where + ".labels", "observables.duplicate_label", "a label is listed twice"))
    return out


def schema_file_hashes() -> dict:
    """SHA-256 of the four schema files' bytes, keyed by file name (part of every plan's hash scope)."""
    return {name: hashlib.sha256((SCHEMA_DIR / name).read_bytes()).hexdigest() for name in sorted(SCHEMA_FILES.values())}
