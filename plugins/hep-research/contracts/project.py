#!/usr/bin/env python3
"""Project configuration (hep-research.project.json): validation, local profiles, context resolution.

Usage: python3 contracts/project.py PROJECT_DIR_OR_CONFIG [--registry PATH]
Exit 0 valid, 1 errors, 2 unreadable. Output: JSON with resolved bindings and findings.

Resolution order (task 7.8): explicit request -> project config -> ask (when the task needs a
profile and none is determinable) -> proceed with no profile. Never guess an experiment.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.registry import PLUGIN_ROOT, validate_registry  # noqa: E402
from contracts.schema import Report, validate  # noqa: E402
from contracts.semver import satisfies, valid_spec  # noqa: E402

CONFIG_NAME = "hep-research.project.json"
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


def load_project(path: Path, registry_path: Path | None = None) -> Project:
    path = Path(path)
    cfg_path = path / CONFIG_NAME if path.is_dir() else path
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    proj_dir = cfg_path.parent
    rep = validate(cfg, "project_config.json", None, Report(), "config")
    if not rep.ok:
        return Project(cfg_path, cfg, rep)
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
    reg_rep, loaded = validate_registry(registry_path, local_dirs)
    rep.findings.extend(reg_rep.findings)

    profiles, seen = [], {}
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
    reg = Path(args[args.index("--registry") + 1]) if "--registry" in args else None
    try:
        p = load_project(Path(args[0]), reg)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    out = {**p.report.as_dict(), "profiles": [x["id"] for x in p.profiles], "artifacts_dir": str(p.artifacts_dir)}
    print(json.dumps(out, indent=1))
    return 0 if p.report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
