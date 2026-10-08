#!/usr/bin/env python3
"""Project configuration (hep-research.project.json): validation, local profiles, context resolution.

Usage: python3 contracts/project.py PROJECT_DIR_OR_CONFIG [--registry PATH] [--local DIR ...]
Exit 0 valid, 1 errors, 2 unreadable. Output: JSON with resolved bindings and findings.
--local DIR adds a profile folder supplied at run time (for example by a companion plugin's `<plugin>:profile`
skill) to the config's `local_profile_paths`; it is validated like any local profile.

Resolution order: explicit request -> project config -> ask (when the task needs a
profile and none is determinable) -> proceed with no profile. Never guess an experiment.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.registry import PLUGIN_ROOT, option_values, validate_registry  # noqa: E402
from contracts.schema import Report, validate  # noqa: E402
from contracts.semver import parse, satisfies, valid_spec  # noqa: E402

CONFIG_NAME = "hep-research.project.json"
SCHEMA_VERSION = "1.1.0"  # the project-config schema this reader implements (1.1.0: agent_policy, closed blinding)
DEFAULT_ARTIFACTS_DIR = "./hep-research-artifacts/"


@dataclass
class Project:
    config_path: Path | None
    config: dict
    report: Report
    profiles: list[dict] = field(default_factory=list)   # bound + local profile metadata
    artifacts_dir: Path | None = None


def _plugin_version() -> str:
    return json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]


def load_project(path: Path, registry_path: Path | None = None, extra_local: list[Path] | None = None) -> Project:
    path = Path(path)
    cfg_path = path / CONFIG_NAME if path.is_dir() else path
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    proj_dir = cfg_path.parent
    rep = validate(cfg, "project_config.json", None, Report(), "config")
    if not rep.ok:
        return Project(cfg_path, cfg, rep)
    check_schema_version(cfg, rep)
    check_blinding_block(cfg, rep)
    check_agent_policy(cfg, proj_dir, rep)
    pv = cfg["plugin_version"]
    if not valid_spec(pv):
        rep.add("error", "config.plugin_version", "project.bad_version_range", f"cannot parse {pv!r}")
    elif not satisfies(_plugin_version(), pv):
        rep.add("error", "config.plugin_version", "project.incompatible_plugin", f"project accepts {pv}; installed plugin is {_plugin_version()}")

    local_dirs = []
    for i, rel in enumerate(cfg.get("local_profile_paths", [])):
        d = (proj_dir / rel).resolve()
        if d == PLUGIN_ROOT.resolve() or PLUGIN_ROOT.resolve() in d.parents:
            rep.add("error", f"config.local_profile_paths[{i}]", "project.local_in_plugin", "local profiles live in the project, never inside the plugin")
        local_dirs.append(d)
    for d in extra_local or []:  # companion-plugin profiles, given on the command line, never in the plugin itself
        d = Path(d).resolve()
        if d == PLUGIN_ROOT.resolve() or PLUGIN_ROOT.resolve() in d.parents:
            rep.add("error", "--local", "project.local_in_plugin", "local profiles live in the project, never inside the plugin")
        if d not in local_dirs:
            local_dirs.append(d)
    reg_rep, loaded = validate_registry(registry_path, local_dirs)
    rep.findings.extend(reg_rep.findings)

    profiles = []
    seen: dict[str, Any] = {}
    for axis in ("experiments", "theory"):
        want_kind = "experiment" if axis == "experiments" else "theory-domain"
        for i, b in enumerate(cfg.get(axis, [])):
            where, pid = f"config.{axis}[{i}]", b["profile"]
            if pid in seen and seen[pid] != b["version"]:
                rep.add("error", where, "project.conflicting_pins", f"'{pid}' pinned to {seen[pid]} and {b['version']}; declare one version")
            seen[pid] = b["version"]
            prof = loaded.get(pid)
            if prof is None:
                rep.add("error", where, "project.unknown_profile", f"'{pid}' is neither registered nor a valid local profile")
                continue
            if prof["kind"] != want_kind:
                rep.add("error", where, "project.wrong_axis", f"'{pid}' is a {prof['kind']} profile, bound under '{axis}'")
            if prof["version"] != b["version"]:
                rep.add("error", where, "project.version_pin_mismatch", f"pinned {b['version']}, available {prof['version']}")
            if prof not in profiles:
                profiles.append(prof)
    for o in cfg.get("overrides", []):
        if o.get("variant_of"):
            rep.add("warning", "config.overrides", "project.variant_as_override",
                    f"'{o['target']}' declares variant_of: a scientifically different choice is an explicit variant, not an override")
    art = (proj_dir / cfg.get("artifacts_dir", DEFAULT_ARTIFACTS_DIR)).resolve()
    if art == PLUGIN_ROOT.resolve() or PLUGIN_ROOT.resolve() in art.parents:
        rep.add("error", "config.artifacts_dir", "project.writes_into_plugin", "artifacts_dir must be outside the installed plugin")
    return Project(cfg_path, cfg, rep, profiles, art)


def check_schema_version(cfg: dict, rep: Report) -> None:
    """The config's schema_version must be one this reader implements (same major, not a newer minor: the schema is
    closed, so newer fields would otherwise be refused one by one); agent_policy needs 1.1.0 or later."""
    have, want = parse(cfg["schema_version"]), parse(SCHEMA_VERSION)
    if have[0] != want[0] or have[1] > want[1]:
        rep.add("error", "config.schema_version", "project.unsupported_schema",
                f"schema_version {cfg['schema_version']} is not supported by this reader (schema {SCHEMA_VERSION})")
    elif "agent_policy" in cfg and have < (1, 1, 0):
        rep.add("error", "config.agent_policy", "project.policy_needs_schema",
                "agent_policy needs schema_version 1.1.0 or later")


BLINDING_KEYS = {"blinded", "allowed_outputs", "regions"}


def check_blinding_block(cfg: dict, rep: Report) -> None:
    """From schema 1.1.0 the blinding block is closed (an unknown key would be silently ignored by every reader); with
    agent_policy present the block is required, so a missing block can never read as 'nothing blinded'."""
    block = cfg.get("blinding")
    if block is None:
        if "agent_policy" in cfg:
            rep.add("error", "config.blinding", "project.blinding_missing",
                    "a project with agent_policy must declare its blinding block (an empty list if nothing is blinded)")
        return
    if parse(cfg["schema_version"]) >= (1, 1, 0):
        for key in sorted(set(block) - BLINDING_KEYS):
            rep.add("error", f"config.blinding.{key}", "project.blinding_unknown_key", f"'{key}' is not a blinding field")
    for i, r in enumerate(block.get("regions", [])):
        if not r["low"] < r["high"]:
            rep.add("error", f"config.blinding.regions[{i}]", "project.bad_region", "a blinded region needs low < high")


def _relative_inside(rel: str) -> bool:
    p = Path(rel)
    return not p.is_absolute() and ".." not in p.parts and not rel.startswith("~")


def check_agent_policy(cfg: dict, proj_dir: Path, rep: Report) -> None:
    """Path rules and manifest digests of agent_policy. Advisory: the result never authorizes access; a launcher
    outside the agent's reach compares this copy with authoritative_copy by digest."""
    pol = cfg.get("agent_policy")
    if pol is None:
        return
    for i, rel in enumerate(pol.get("protected_paths", [])):
        if not _relative_inside(rel):
            rep.add("error", f"config.agent_policy.protected_paths[{i}]", "project.policy_bad_path",
                    f"{rel!r}: protected paths are relative to the project, without '..'")
    for i, m in enumerate(pol.get("release_manifests", [])):
        where = f"config.agent_policy.release_manifests[{i}]"
        if not _relative_inside(m["ref"]):
            rep.add("error", where, "project.policy_bad_path", f"{m['ref']!r}: manifest refs are relative, without '..'")
            continue
        path = proj_dir / m["ref"]
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            rep.add("error", where, "project.policy_manifest_missing", f"{m['ref']!r} cannot be read")
            continue
        if digest != m["sha256"]:
            rep.add("error", where, "project.policy_manifest_mismatch", f"{m['ref']!r} has sha256 {digest}, the policy declares {m['sha256']}")


def load_blinding(path: Path) -> dict:
    """The validated blinding block of a project; ValueError when the config is invalid. A project without the block
    and without agent_policy has nothing blinded; with agent_policy the block is required (check_blinding_block)."""
    proj = load_project(path)
    if not proj.report.ok:
        raise ValueError("invalid project config: " + "; ".join(f"{f.code}: {f.message}" for f in proj.report.errors))
    return proj.config.get("blinding") or {"blinded": [], "allowed_outputs": []}


def resolve_context(request: dict, project: Project | None, needs_profile: bool) -> dict:
    """Decide which profiles a task uses. `request` holds only IDs the user stated explicitly:
    {"experiments": [...], "theory": [...]}. Returns {"decision", "source", "experiments", "theory"}."""
    exp, th = list(request.get("experiments", [])), list(request.get("theory", []))
    if exp or th:
        return {"decision": "use", "source": "request", "experiments": exp, "theory": th}
    if project is not None and (project.config.get("experiments") or project.config.get("theory")):
        return {"decision": "use", "source": "project-config",
                "experiments": [b["profile"] for b in project.config.get("experiments", [])],
                "theory": [b["profile"] for b in project.config.get("theory", [])]}
    if needs_profile:
        return {"decision": "ask", "source": "none", "experiments": [], "theory": []}
    return {"decision": "none", "source": "none", "experiments": [], "theory": []}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(__doc__)
        return 2
    try:
        reg = next((Path(v) for v in option_values(args, "--registry")), None)
        extra = [Path(v) for v in option_values(args, "--local")]
        p = load_project(Path(args[0]), reg, extra)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    out = {**p.report.as_dict(), "profiles": [x["id"] for x in p.profiles], "artifacts_dir": str(p.artifacts_dir),
           "note": "advisory check: a valid config, including agent_policy, does not enforce or authorize anything"}
    print(json.dumps(out, indent=1))
    return 0 if p.report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
