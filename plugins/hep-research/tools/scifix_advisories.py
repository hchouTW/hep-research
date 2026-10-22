#!/usr/bin/env python3
"""Sci-fix advisories: which releases a scientific correction affects, and which of a project's artifacts they touch.

An advisory (docs/evidence/advisories/SFA-YYYY-NNN.json, format hep-research-scifix-advisory/1, provisional: shadow
mode) records a defect that a sci-fix corrected, for people holding results made before the fix. It does not repeat
the correctness evidence: it names the entries of docs/evidence/sci-fixes.json. Fields:
  id, summary, severity (S1-S4, the ledger's), ledger (ledger ids),
  affected: [{paths: [plugin-relative files with the defect], ranges: [{type: "SEMVER", events: [{introduced},
             {fixed} | {last_affected}]}], database_specific: {fixed_commit}}]  (OSV semantics: introduced "0" is
             every earlier release; no fixed event means every later release, the fix not released yet),
  impact: {observables: [...], bias, trigger}  (the scientific effect, separate from the version range),
  applies_to: {artifact_types: [...], extension_keys: [...]}  (an artifact is touched when its type is listed and,
             if keys are given, its extension has one of them: the affected code ran for it),
  affected[].database_specific: {fixed_commit, introduced_commit, introduced_basis (why the defect starts at a
             release that already held an affected path), no_artifact (true: the affected code writes no artifact,
             so no artifact can show it ran), outputs (with no_artifact: the producer and how to recognise its
             output)},
  remedy, references: [commits].

Subcommands (all read-only):
  check                 every advisory against the ledger, the plugin tree and the release manifests; exit 1 on a
                        problem. Ranges: X.Y.Z versions (introduced may be "0"), no two events at one version, each
                        fixed or last_affected above the introduced before it; a fixed release changes an affected
                        file against the release before it (when both have a manifest); an introduced release that
                        already held an affected path states introduced_basis. applies_to: known artifact types, and
                        extension keys that discriminate (no key required by any listed type's extension schema, and
                        at least one key), unless the advisory writes no artifact (no_artifact) or is one of the
                        NONDISCRIMINATING_ALLOWED advisories awaiting migration
  affected [--id ID]    the releases each advisory affects, computed from release-manifests/ (in range and holding
                        an affected path); releases in range older than the first manifest are listed apart
  scan PROJECT_DIR      the project's artifacts (artifacts_dir of hep-research.project.json, default
                        ./hep-research-artifacts/) against the advisories: per artifact the release that made it
                        (verified when versions.plugin_release's digest equals that release's manifest digest,
                        else claimed, else unknown) and the advisories that touch it. Shadow mode: a report only,
                        exit 0 whatever it finds; nothing in the project is written.
Output: JSON on stdout with "status" (passed, failed, rejected; core/status.py). Exit codes: 0 ok (scan: always,
shadow mode), 1 check found problems, 2 bad input.
Usage: python3 <plugin root>/tools/scifix_advisories.py scan /path/to/project
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADVISORIES = ROOT / "docs" / "evidence" / "advisories"
LEDGER = ROOT / "docs" / "evidence" / "sci-fixes.json"
MANIFESTS = ROOT / "release-manifests"
FORMAT = "hep-research-scifix-advisory/1"
ID = re.compile(r"^SFA-\d{4}-\d{3}$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
SEVERITIES = ("S1", "S2", "S3", "S4")
CONFIG_NAME = "hep-research.project.json"
DEFAULT_ARTIFACTS_DIR = "./hep-research-artifacts/"
# Advisories whose extension keys cannot show that the affected code ran (a key every artifact of a listed type
# carries, or no key). Frozen: sci-fix improvement plan PR-5 migrates them to discriminating matches and empties this
# set; a new advisory is never added to it.
NONDISCRIMINATING_ALLOWED = frozenset({
    "SFA-2026-001", "SFA-2026-002", "SFA-2026-004", "SFA-2026-006", "SFA-2026-010", "SFA-2026-020", "SFA-2026-023",
    "SFA-2026-025", "SFA-2026-030", "SFA-2026-031", "SFA-2026-033"})


def version_key(text: str) -> tuple[int, ...]:
    return (0, 0, 0) if text == "0" else tuple(int(p) for p in text.split("."))


def in_range(version: str, events: list[dict]) -> bool:
    """OSV SEMVER range: from an introduced event up to (not including) the next fixed event, or through a
    last_affected event; with no closing event every later version is affected."""
    key, affected = version_key(version), False
    for event in sorted(events, key=lambda e: version_key(next(iter(e.values())))):
        (kind, at), = event.items()
        if kind == "introduced" and key >= version_key(at):
            affected = True
        elif kind == "fixed" and key >= version_key(at):
            affected = False
        elif kind == "last_affected" and key > version_key(at):
            affected = False
    return affected


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_advisories(folder: Path = ADVISORIES) -> list[dict]:
    return [load_json(p) | {"_file": p.name} for p in sorted(folder.glob("SFA-*.json"))]


def load_manifests(folder: Path = MANIFESTS) -> dict[str, dict]:
    out = {}
    for p in folder.glob("*.json"):
        doc = load_json(p)
        out[doc["version"]] = {"digest": doc["digest"], "paths": {f["path"] for f in doc["files"]},
                               "sha256": {f["path"]: f["sha256"] for f in doc["files"]}}
    return dict(sorted(out.items(), key=lambda kv: version_key(kv[0])))


def artifact_types(root: Path = ROOT) -> set[str]:
    """The artifact type vocabulary: the enum of artifact_type in the envelope schema."""
    return set(load_json(root / "contracts" / "schemas" / "envelope.json")["properties"]["artifact_type"]["enum"])


def required_extension_keys(artifact_type: str, root: Path = ROOT) -> set[str]:
    """Extension properties every valid artifact of the type carries: `required` of ext_<type>.json and its variants
    (the validator applies the base schema to every contract version)."""
    stem, folder, found = f"ext_{artifact_type.replace('-', '_')}", root / "contracts" / "schemas", set()
    for schema in [folder / f"{stem}.json", *sorted(folder.glob(f"{stem}_*.json"))]:
        if schema.is_file():
            found |= set(load_json(schema).get("required") or [])
    return found


def writes_no_artifact(adv: dict) -> bool:
    """The affected code writes no artifact (every affected block says database_specific.no_artifact)."""
    blocks = adv.get("affected") or []
    return bool(blocks) and all((b.get("database_specific") or {}).get("no_artifact") is True for b in blocks)


def extension_properties(artifact_types: list[str], root: Path = ROOT) -> set[str] | None:
    """Top-level extension properties of the listed artifact types: the union over contracts/schemas/ext_<type>.json
    and its variants ext_<type>_*.json (contract versions, capabilities); None when no listed type has an extension
    schema, so the keys cannot be checked."""
    found, any_schema = set(), False
    for artifact_type in artifact_types:
        stem = f"ext_{artifact_type.replace('-', '_')}"
        folder = root / "contracts" / "schemas"
        for schema in [folder / f"{stem}.json", *sorted(folder.glob(f"{stem}_*.json"))]:
            if schema.is_file():
                any_schema = True
                found |= set((load_json(schema).get("properties") or {}).keys())
    return found if any_schema else None


def _range_problems(name: str, events: list[dict]) -> list[str]:
    """Event order and versions within one SEMVER range (the caller has checked the event kinds)."""
    problems, versions, introduced = [], set(), None
    for event in events:
        (kind, at), = event.items()
        if not isinstance(at, str) or not (VERSION.match(at) or (kind == "introduced" and at == "0")):
            problems.append(f"{name}: event {event} needs an X.Y.Z version")
            continue
        if at in versions:
            problems.append(f"{name}: two events at version {at} in one range")
        versions.add(at)
        if kind == "introduced":
            introduced = at
        elif introduced is None or version_key(at) <= version_key(introduced):
            problems.append(f"{name}: {kind} {at} is not above the introduced version before it ({introduced})")
            introduced = None
        else:
            introduced = None
    return problems


def _manifest_path(manifest: dict, path: str) -> str | None:
    """The path under which a release holds the file (see holds()), or None."""
    if path in manifest["paths"]:
        return path
    parts = path.split("/", 2)
    if len(parts) < 3 or parts[0] != "skills":
        return None
    found = [p for p in manifest["paths"] if p.startswith("skills/") and p.split("/", 2)[2:] == parts[2:]]
    return found[0] if len(found) == 1 else None


def _previous(manifests: dict[str, dict], version: str) -> str | None:
    earlier = [v for v in manifests if version_key(v) < version_key(version)]
    return max(earlier, key=version_key) if earlier else None


def _release_problems(name: str, block: dict, events: list[dict], manifests: dict[str, dict]) -> list[str]:
    """A fixed release changes an affected file; an introduced release that already held one says why."""
    problems, paths = [], block.get("paths") or []
    for event in events:
        (kind, at), = event.items()
        before = _previous(manifests, at) if at in manifests else None
        if before is None:
            continue
        now, then = manifests[at], manifests[before]
        if kind == "fixed" and "sha256" in now and "sha256" in then:
            pairs = [(_manifest_path(now, p), _manifest_path(then, p)) for p in paths]
            pairs = [(a, b) for a, b in pairs if a and b]
            if pairs and all(now["sha256"][a] == then["sha256"][b] for a, b in pairs):
                problems.append(f"{name}: fixed {at} changes no affected path against {before}")
        if kind == "introduced" and any(_manifest_path(then, p) for p in paths) and \
                not (block.get("database_specific") or {}).get("introduced_basis"):
            problems.append(f"{name}: introduced {at}, but {before} already holds an affected path: "
                            "database_specific.introduced_basis says why the defect starts there")
    return problems


def check(advisories: list[dict], ledger: dict, manifests: dict[str, dict], root: Path = ROOT) -> list[str]:
    """Problems in the advisories: format, ids, ledger references and severities, version ranges, paths, artifact
    types and whether the extension keys discriminate."""
    problems, seen = [], set()
    entries = {f["id"]: f for f in ledger["fixes"]}
    known_types = artifact_types(root)
    for adv in advisories:
        name = adv.get("id", adv["_file"])
        if adv.get("format") != FORMAT:
            problems.append(f"{name}: format must be {FORMAT}")
        if not ID.match(str(adv.get("id"))) or adv["_file"] != f"{adv.get('id')}.json":
            problems.append(f"{name}: id must be SFA-YYYY-NNN and match the file name")
        if adv.get("id") in seen:
            problems.append(f"{name}: duplicate id")
        seen.add(adv.get("id"))
        if adv.get("severity") not in SEVERITIES:
            problems.append(f"{name}: severity must be one of {SEVERITIES}")
        refs = adv.get("ledger") or []
        if not refs:
            problems.append(f"{name}: names no ledger entry (the correctness evidence)")
        for ref in refs:
            if ref not in entries:
                problems.append(f"{name}: ledger entry {ref} not in {LEDGER.name}")
            elif entries[ref]["severity"] != adv.get("severity"):
                problems.append(f"{name}: severity {adv.get('severity')} differs from {ref}'s "
                                f"{entries[ref]['severity']}")
        impact = adv.get("impact") or {}
        if not (impact.get("observables") and impact.get("bias") and impact.get("trigger")):
            problems.append(f"{name}: impact needs observables, bias and trigger")
        applies = adv.get("applies_to") or {}
        if not applies.get("artifact_types"):
            problems.append(f"{name}: applies_to needs artifact_types")
        for artifact_type in applies.get("artifact_types") or []:
            if artifact_type not in known_types:
                problems.append(f"{name}: artifact type {artifact_type} is not in the contracts' vocabulary")
        blocks = adv.get("affected") or []
        marked = [b for b in blocks if (b.get("database_specific") or {}).get("no_artifact") is not None]
        if marked and not writes_no_artifact(adv):
            problems.append(f"{name}: database_specific.no_artifact must be true in every affected block or none")
        if writes_no_artifact(adv):
            if not all(isinstance(b["database_specific"].get("outputs"), str) and b["database_specific"]["outputs"]
                       for b in blocks):
                problems.append(f"{name}: no_artifact needs database_specific.outputs (producer and how to "
                                "recognise its output)")
        else:
            keys = applies.get("extension_keys") or []
            required = {t: required_extension_keys(t, root) & set(keys) for t in applies.get("artifact_types") or []}
            blind = not keys or any(required.values())
            if blind and adv.get("id") not in NONDISCRIMINATING_ALLOWED:
                why = "no extension key" if not keys else "; ".join(
                    f"{', '.join(sorted(k))} required for {t}" for t, k in required.items() if k)
                problems.append(f"{name}: extension keys cannot show the affected code ran ({why}): name a key only "
                                "the affected code writes, or mark no_artifact when it writes no artifact")
            if not blind and adv.get("id") in NONDISCRIMINATING_ALLOWED:
                problems.append(f"{name}: discriminates now: remove it from NONDISCRIMINATING_ALLOWED")
        known = extension_properties(applies.get("artifact_types") or [], root)
        for key in applies.get("extension_keys") or []:
            if known is not None and key not in known:
                problems.append(f"{name}: extension key {key} is not a top-level property of the extension of "
                                f"{', '.join(applies.get('artifact_types') or [])} (the scan reads top-level keys)")
        for block in adv.get("affected") or [{}]:
            paths, ranges = block.get("paths") or [], block.get("ranges") or []
            if not paths or not ranges:
                problems.append(f"{name}: each affected block needs paths and ranges")
            for path in paths:
                if not (root / path).is_file():
                    problems.append(f"{name}: affected path {path} is not a file of the plugin")
            well_formed = True
            for rng in ranges:
                events = rng.get("events") or []
                if rng.get("type") != "SEMVER" or not events or not isinstance(events[0], dict) or \
                        "introduced" not in events[0]:
                    problems.append(f"{name}: a range is SEMVER and starts with an introduced event")
                    well_formed = False
                    continue
                bad = [e for e in events if not isinstance(e, dict) or len(e) != 1 or
                       next(iter(e)) not in ("introduced", "fixed", "last_affected")]
                for event in bad:
                    problems.append(f"{name}: event {event} is not introduced, fixed or last_affected")
                found = [] if bad else _range_problems(name, events)
                problems += found
                if bad or found:
                    well_formed = False
                    continue
                problems += _release_problems(name, block, events, manifests)
                closed = [e for e in events if "fixed" in e or "last_affected" in e]
                if not closed and not (block.get("database_specific") or {}).get("fixed_commit"):
                    problems.append(f"{name}: an open range (fix not released) names database_specific.fixed_commit")
            if paths and ranges and well_formed and not affected_releases(adv, manifests)["releases"] and \
                    not affected_releases(adv, manifests)["before_first_manifest"]:
                problems.append(f"{name}: no release is affected (range or paths wrong)")
    return problems


def holds(manifest_paths: set[str], path: str) -> bool:
    """Whether a release holds the file: at its path, or, for a file under skills/<skill>/, at the same path below
    another skill folder when exactly one file there has it (the skill folders were renamed in 0.11.0 and 0.16.0)."""
    if path in manifest_paths:
        return True
    parts = path.split("/", 2)
    if len(parts) < 3 or parts[0] != "skills":
        return False
    return sum(1 for p in manifest_paths if p.startswith("skills/") and p.split("/", 2)[2:] == parts[2:]) == 1


def affected_releases(adv: dict, manifests: dict[str, dict]) -> dict:
    """Releases with a manifest that are in an affected range and hold one of its paths; whether releases older than
    the first manifest are in range too (they cannot be checked against a manifest)."""
    releases, before = set(), False
    first = next(iter(manifests), None)
    for block in adv.get("affected") or []:
        paths = block.get("paths") or []
        for rng in block.get("ranges") or []:
            events = rng.get("events") or []
            for version, man in manifests.items():
                if in_range(version, events) and any(holds(man["paths"], path) for path in paths):
                    releases.add(version)
            intro = [next(iter(e.values())) for e in events if "introduced" in e]
            if first and intro and version_key(min(intro, key=version_key)) < version_key(first):
                before = True
    return {"releases": sorted(releases, key=version_key), "before_first_manifest": before,
            "first_manifest": first}


def _artifact_release(doc: dict, manifests: dict[str, dict]) -> tuple[str | None, str]:
    """(version, basis): verified (plugin_release digest equals that release's manifest digest), claimed (a version
    recorded without a matching digest, including unreleased builds), or unknown."""
    versions: dict = doc["versions"] if isinstance(doc.get("versions"), dict) else {}
    rel: dict = versions["plugin_release"] if isinstance(versions.get("plugin_release"), dict) else {}
    release, digest = rel.get("release"), rel.get("digest")
    if isinstance(release, str) and release in manifests and digest == manifests[release]["digest"]:
        return release, "verified"
    plugin = versions.get("plugin")
    if isinstance(plugin, str) and VERSION.match(plugin):
        basis = "claimed (unreleased build)" if release == "unreleased" else "claimed"
        if isinstance(release, str) and release in manifests and digest not in (None, "unknown"):
            basis = "claimed (plugin_release digest differs from the release manifest)"
        return plugin, basis
    return None, "unknown"


def _touches(adv: dict, doc: dict) -> bool:
    applies = adv.get("applies_to") or {}
    if doc.get("artifact_type") not in (applies.get("artifact_types") or []):
        return False
    keys = applies.get("extension_keys") or []
    ext: dict = doc["extension"] if isinstance(doc.get("extension"), dict) else {}
    return not keys or any(ext.get(k) not in (None, False, {}, []) for k in keys)


def scan(project: Path, advisories: list[dict], manifests: dict[str, dict]) -> dict:
    """Read-only impact report of a project's artifacts against the advisories (shadow mode)."""
    config = project / CONFIG_NAME
    folder = DEFAULT_ARTIFACTS_DIR
    if config.is_file():
        cfg = load_json(config)
        folder = cfg.get("artifacts_dir", DEFAULT_ARTIFACTS_DIR) if isinstance(cfg, dict) else folder
    artifacts_dir = (project / folder).resolve()
    ranges = {adv["id"]: affected_releases(adv, manifests) for adv in advisories}
    findings, unreadable, scanned = [], [], 0
    for path in sorted(artifacts_dir.rglob("*.json")) if artifacts_dir.is_dir() else []:
        try:
            doc = load_json(path)
        except (OSError, ValueError):
            unreadable.append(str(path.relative_to(artifacts_dir)))
            continue
        if not isinstance(doc, dict) or "artifact_type" not in doc or "versions" not in doc:
            continue  # not an artifact envelope (a sidecar, a table)
        scanned += 1
        version, basis = _artifact_release(doc, manifests)
        for adv in advisories:
            if not _touches(adv, doc):
                continue
            if version is None:
                verdict = "possibly affected (release unknown)"
            elif any(in_range(version, r.get("events") or []) for b in adv.get("affected") or []
                     for r in b.get("ranges") or []):
                # the version only moves at a release: a build after release V claims V, with or without the fix
                verdict = ("possibly affected (unreleased build: it may hold the fix)" if "unreleased" in basis
                           else "affected")
            else:
                continue
            findings.append({"artifact": str(path.relative_to(artifacts_dir)), "artifact_type": doc["artifact_type"],
                             "release": version, "release_basis": basis, "advisory": adv["id"],
                             "severity": adv["severity"], "verdict": verdict, "remedy": adv.get("remedy")})
    return {"status": "passed", "mode": "shadow", "project": str(project), "artifacts_dir": str(artifacts_dir),
            "artifacts_scanned": scanned, "unreadable": unreadable, "findings": findings,
            "advisories": {a: {"releases_affected": r["releases"]} for a, r in ranges.items()},
            "note": ("shadow mode: a report only, nothing blocks and nothing in the project is written. An artifact "
                     "is listed when its type and extension show the affected code ran for it and its release is in "
                     "an affected range; results made without an artifact are not seen")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    aff = sub.add_parser("affected")
    aff.add_argument("--id")
    sc = sub.add_parser("scan")
    sc.add_argument("project")
    args = ap.parse_args(argv)
    out: dict
    try:
        advisories, manifests = load_advisories(), load_manifests()
        if args.cmd == "check":
            problems = check(advisories, load_json(LEDGER), manifests)
            out = {"status": "failed" if problems else "passed", "advisories": len(advisories), "problems": problems}
            code = 1 if problems else 0
        elif args.cmd == "affected":
            chosen = [a for a in advisories if args.id in (None, a["id"])]
            if args.id and not chosen:
                raise ValueError(f"no advisory {args.id}")
            out = {"status": "passed", "affected": {a["id"]: affected_releases(a, manifests) for a in chosen}}
            code = 0
        else:
            project = Path(args.project)
            if not project.is_dir():
                raise ValueError(f"{project} is not a folder")
            out, code = scan(project, advisories, manifests), 0
    except (OSError, ValueError, KeyError) as exc:
        out, code = {"status": "rejected", "error": str(exc)}, 2
    print(json.dumps(out, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
