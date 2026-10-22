#!/usr/bin/env python3
"""Sci-fix advisories: which releases a scientific correction affects, and which of a project's artifacts they touch.

An advisory (docs/evidence/advisories/SFA-YYYY-NNN.json, format hep-research-scifix-advisory/2, provisional: shadow
mode; the scan still reads /1 for one release) records a defect that a sci-fix corrected, for people holding results made before the fix. It does not repeat
the correctness evidence: it names the entries of docs/evidence/sci-fixes.json. Fields:
  id, summary, severity (S1-S4, the ledger's), ledger (ledger ids),
  affected: [{paths: [plugin-relative files with the defect], ranges: [{type: "SEMVER", events: [{introduced},
             {fixed} | {last_affected}]}], database_specific: {fixed_commit}}]  (OSV semantics: introduced "0" is
             every earlier release; no fixed event means every later release, the fix not released yet),
  impact: {observables: [...], bias, trigger}  (the scientific effect, separate from the version range),
  applies_to: {artifact_types: [...], match: [[condition, ...], ...], match_basis, no_trace, outputs}
             match: OR over groups, AND within a group, of conditions {path, op, value | values, unknown_before}.
             path: envelope keys joined by '.', '[*]' expands a list (extension.tools[*].name). op: exists (present,
             not null and not a missing marker), eq (value), in (values), regex
             (value, re.search on a string). A condition is undecided when the artifact cannot show it: a trace path
             (provenance.code_paths, provenance.code_tags) on an artifact without that field, or a contract_version
             below unknown_before (the field did not exist yet). A group holds when all its conditions hold, fails
             when one fails, else is undecided; the advisory touches the artifact when a group holds, may touch it
             when none holds and one is undecided, or when match is [] (no field can show the affected code ran:
             match_basis says why). no_trace ("possibly-affected") names that verdict. Each group needs a condition
             that discriminates: anything but `exists` on a top-level extension key every artifact of a listed type
             carries. code_paths records only code loaded by the writing process: a script run in another process
             (a core/stats CLI whose output result_artifact.py wraps, a training asset) is never in it.
             outputs {producer: [paths], how_to_recognize}: the affected code writes output that is no artifact;
             listed apart. artifact_types may be [] when outputs is given and no artifact can show the code ran,
  affected[].database_specific: {fixed_commit, introduced_commit, introduced_basis (why the defect starts at a
             release that already held an affected path)},
  remedy, references: [commits].

Subcommands (all read-only):
  check                 every advisory against the ledger, the plugin tree and the release manifests; exit 1 on a
                        problem. Ranges: X.Y.Z versions (introduced may be "0"), no two events at one version, each
                        fixed or last_affected above the introduced before it; a fixed release changes an affected
                        file against the release before it (when both have a manifest); an introduced release that
                        already held an affected path states introduced_basis. applies_to: known artifact types,
                        well-formed conditions that discriminate, match_basis for match [], outputs naming files of
                        the plugin
  affected [--id ID]    the releases each advisory affects, computed from release-manifests/ (in range and holding
                        an affected path); releases in range older than the first manifest are listed apart
  scan PROJECT_DIR      the project's artifacts (artifacts_dir of hep-research.project.json, default
                        ./hep-research-artifacts/) against the advisories: per artifact the release that made it
                        (digest-consistent when versions.plugin_release's digest equals that release's manifest
                        digest, else claimed, else unknown) and the advisories that touch it. Verdict order per
                        advisory: (1) outputs that are no artifact are listed apart (outputs_not_artifacts); (2)
                        artifact type; (3) match (affected, or possibly affected (no trace) when undecided); (4)
                        release in an affected range; (5) that release's manifest holds an affected path of the same
                        block. Shadow mode: a report only, exit 0 whatever it finds; nothing in the project is written.
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
FORMAT = "hep-research-scifix-advisory/2"
FORMAT_V1 = "hep-research-scifix-advisory/1"  # read by scan for one more release, never written
ID = re.compile(r"^SFA-\d{4}-\d{3}$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
SEVERITIES = ("S1", "S2", "S3", "S4")
CONFIG_NAME = "hep-research.project.json"
DEFAULT_ARTIFACTS_DIR = "./hep-research-artifacts/"
OPS = ("exists", "eq", "in", "regex")
SEGMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\[\*\])?$")
TRACE_PATHS = ("provenance.code_paths", "provenance.code_tags")  # contracts 3.5.0 (contracts/trace.py)
NO_TRACE = ("possibly-affected",)


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
    """Format /1: the affected code writes no artifact (every affected block says database_specific.no_artifact)."""
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


def _condition_problems(name: str, cond) -> list[str]:
    if not isinstance(cond, dict):
        return [f"{name}: a match condition is an object"]
    problems, path, op = [], cond.get("path"), cond.get("op")
    if not isinstance(path, str) or not all(SEGMENT.match(seg) for seg in path.split(".")):
        problems.append(f"{name}: condition path {path!r} is keys joined by '.', a key optionally followed by [*]")
    if op not in OPS:
        problems.append(f"{name}: condition op {op!r} is one of {', '.join(OPS)}")
    if op in ("eq", "regex") and "value" not in cond:
        problems.append(f"{name}: condition {op} needs value")
    if op == "regex":
        try:
            re.compile(cond.get("value"))  # type: ignore[arg-type]
        except (re.error, TypeError):
            problems.append(f"{name}: condition regex {cond.get('value')!r} does not compile")
    if op == "in" and not (isinstance(cond.get("values"), list) and cond["values"]):
        problems.append(f"{name}: condition in needs a non-empty values list")
    if set(cond) - {"path", "op", "value", "values", "unknown_before"}:
        problems.append(f"{name}: condition has unknown fields {sorted(set(cond) - {'path', 'op', 'value', 'values', 'unknown_before'})}")
    if "unknown_before" in cond and not VERSION.match(str(cond["unknown_before"])):
        problems.append(f"{name}: unknown_before needs an X.Y.Z contract version")
    return problems


def _applies_problems(name: str, applies: dict, known_types: set[str], root: Path) -> list[str]:
    """Format /2 applies_to: types, match conditions that discriminate, match_basis, no_trace, outputs."""
    problems: list[str] = []
    types, outputs = applies.get("artifact_types"), applies.get("outputs")
    if not isinstance(types, list) or (not types and outputs is None):
        return [f"{name}: applies_to needs artifact_types (or [] with outputs when no artifact can show the code ran)"]
    if "extension_keys" in applies:
        problems.append(f"{name}: extension_keys is format /1: write match conditions")
    for artifact_type in types:
        if artifact_type not in known_types:
            problems.append(f"{name}: artifact type {artifact_type} is not in the contracts' vocabulary")
    if outputs is not None:
        producers = outputs.get("producer") if isinstance(outputs, dict) else None
        if not (isinstance(producers, list) and producers and isinstance(outputs.get("how_to_recognize"), str)
                and outputs["how_to_recognize"]):
            problems.append(f"{name}: outputs needs producer (plugin files) and how_to_recognize")
        for path in producers or []:
            if not (isinstance(path, str) and (root / path).is_file()):
                problems.append(f"{name}: outputs producer {path} is not a file of the plugin")
    if not types:
        return problems
    match = applies.get("match")
    if applies.get("no_trace") not in NO_TRACE:
        problems.append(f"{name}: no_trace is one of {', '.join(NO_TRACE)}")
    if not isinstance(match, list):
        return problems + [f"{name}: applies_to needs match (condition groups; [] when no field can show the code ran)"]
    if not match and not applies.get("match_basis"):
        problems.append(f"{name}: match [] needs match_basis (why no field can show the affected code ran)")
    required = set().union(*(required_extension_keys(t, root) for t in types))
    for group in match:
        if not isinstance(group, list) or not group:
            problems.append(f"{name}: a match group is a non-empty list of conditions")
            continue
        blind = True
        for cond in group:
            problems += _condition_problems(name, cond)
            path = cond.get("path", "") if isinstance(cond, dict) else ""
            if not (isinstance(cond, dict) and cond.get("op") == "exists" and path.count(".") == 1 and
                    path.startswith("extension.") and path.split(".")[1] in required):
                blind = False
        if blind:
            problems.append(f"{name}: a match group cannot show the affected code ran (only exists on extension keys "
                            f"every {', '.join(types)} artifact carries)")
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
        applies = adv.get("applies_to") if isinstance(adv.get("applies_to"), dict) else {}
        problems += _applies_problems(name, applies, known_types, root)
        for block in adv.get("affected") or []:
            if {"no_artifact", "outputs"} & set(block.get("database_specific") or {}):
                problems.append(f"{name}: database_specific no_artifact and outputs are format /1: use "
                                "applies_to.outputs")
        known = extension_properties(applies.get("artifact_types") or [], root)
        for group in applies.get("match") or []:
            for cond in group if isinstance(group, list) else []:
                path = cond.get("path", "") if isinstance(cond, dict) else ""
                top = path.split(".")[1].removesuffix("[*]") if path.startswith("extension.") and "." in path else None
                if top and known is not None and top not in known:
                    problems.append(f"{name}: {path}: {top} is not a top-level property of the extension of "
                                    f"{', '.join(applies.get('artifact_types') or [])}")
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


DIGEST_CONSISTENT = "digest-consistent"  # was "verified" (the artifact's own digest matches; nothing is verified)


def _artifact_release(doc: dict, manifests: dict[str, dict]) -> tuple[str | None, str]:
    """(version, basis): digest-consistent (plugin_release digest equals that release's manifest digest), claimed (a
    version recorded without a matching digest, including unreleased builds), or unknown."""
    versions: dict = doc["versions"] if isinstance(doc.get("versions"), dict) else {}
    rel: dict = versions["plugin_release"] if isinstance(versions.get("plugin_release"), dict) else {}
    release, digest = rel.get("release"), rel.get("digest")
    if isinstance(release, str) and release in manifests and digest == manifests[release]["digest"]:
        return release, DIGEST_CONSISTENT
    plugin = versions.get("plugin")
    if isinstance(plugin, str) and VERSION.match(plugin):
        basis = "claimed (unreleased build)" if release == "unreleased" else "claimed"
        if isinstance(release, str) and release in manifests and digest not in (None, "unknown"):
            basis = "claimed (plugin_release digest differs from the release manifest)"
        return plugin, basis
    return None, "unknown"


def missing_markers(root: Path = ROOT) -> frozenset[str]:
    """The missing-value markers (contracts/vocab/core.json missing_markers: unknown, not-applicable, not-provided)."""
    vocab = load_json(root / "contracts" / "vocab" / "core.json")["vocabularies"]["missing_markers"]
    return frozenset(vocab)


def present(value, markers: frozenset[str]) -> bool:
    """A key's value shows the code wrote something: not absent, null, false, an empty object or list, or a missing
    marker (a zero is present: `0 == False` no longer hides it)."""
    if value is None or value is False or value in ({}, []):
        return False
    return not (isinstance(value, str) and value in markers)


def resolve(doc, path: str) -> list:
    """Every value at a dotted path ('[*]' expands a list); [] when the path is absent."""
    nodes = [doc]
    for segment in path.split("."):
        expand = segment.endswith("[*]")
        key = segment[:-3] if expand else segment
        found: list = []
        for node in nodes:
            if isinstance(node, dict) and key in node:
                if not expand:
                    found.append(node[key])
                elif isinstance(node[key], list):
                    found.extend(node[key])
        nodes = found
    return nodes


def _same(a, b) -> bool:
    return a == b and isinstance(a, bool) == isinstance(b, bool)  # true is not 1


def condition_holds(cond: dict, doc: dict, markers: frozenset[str] = frozenset()) -> bool | None:
    """True, False, or None when the artifact cannot show it (no trace field, or written before the field existed)."""
    values, op = resolve(doc, cond["path"]), cond["op"]
    if op == "exists":  # format /2: only null and a missing marker are absent (false, 0, {} and [] are values)
        ok = any(v is not None and not (isinstance(v, str) and v in markers) for v in values)
    elif op == "eq":
        ok = any(_same(v, cond["value"]) for v in values)
    elif op == "in":
        ok = any(any(_same(v, x) for x in cond["values"]) for v in values)
    else:
        ok = any(isinstance(v, str) and re.search(cond["value"], v) is not None for v in values)
    if ok:
        return True
    prov = doc.get("provenance") if isinstance(doc.get("provenance"), dict) else {}
    trace = next((t for t in TRACE_PATHS if cond["path"].split("[")[0].startswith(t)), None)
    if trace and trace.split(".")[1] not in prov:
        return None
    below = cond.get("unknown_before")
    written = doc.get("contract_version")
    if below and (not isinstance(written, str) or not VERSION.match(written) or
                  version_key(written) < version_key(below)):
        return None
    return False


def match_verdict(applies: dict, doc: dict, markers: frozenset[str] = frozenset()) -> str | None:
    """"affected" when a group holds; "possibly" when none holds and one is undecided, or match is []; else None."""
    groups = applies.get("match") or []
    if not groups:
        return "possibly"
    undecided = False
    for group in groups:
        results = [condition_holds(c, doc, markers) for c in group]
        if all(r is True for r in results):
            return "affected"
        undecided = undecided or not any(r is False for r in results)
    return "possibly" if undecided else None


def _touches(adv: dict, doc: dict, markers: frozenset[str] = frozenset()) -> bool:
    applies = adv.get("applies_to") or {}
    if doc.get("artifact_type") not in (applies.get("artifact_types") or []):
        return False
    keys = applies.get("extension_keys") or []
    ext: dict = doc["extension"] if isinstance(doc.get("extension"), dict) else {}
    return not keys or any(present(ext.get(k), markers) for k in keys)


def _release_affected(adv: dict, version: str, manifests: dict[str, dict]) -> bool:
    """Steps 4 and 5: the release is in a range of a block and, when it has a manifest, holds one of that block's
    paths (a release without a manifest is judged on the range alone)."""
    for block in adv.get("affected") or []:
        if not any(in_range(version, r.get("events") or []) for r in block.get("ranges") or []):
            continue
        if version not in manifests or any(holds(manifests[version]["paths"], p) for p in block.get("paths") or []):
            return True
    return False


def _outputs(adv: dict):
    """What the affected code writes that is no artifact (listed apart), or None."""
    if adv.get("format") == FORMAT_V1:
        return ([(b.get("database_specific") or {}).get("outputs") for b in adv.get("affected") or []]
                if writes_no_artifact(adv) else None)
    return (adv.get("applies_to") or {}).get("outputs")


def _match(adv: dict, doc: dict, markers: frozenset[str]) -> str | None:
    """Steps 2 and 3: None, "affected" or "possibly" (format /1: its type and extension keys)."""
    applies = adv.get("applies_to") or {}
    if doc.get("artifact_type") not in (applies.get("artifact_types") or []):
        return None
    if adv.get("format") == FORMAT_V1:
        return "affected" if not writes_no_artifact(adv) and _touches(adv, doc, markers) else None
    return match_verdict(applies, doc, markers)


def scan(project: Path, advisories: list[dict], manifests: dict[str, dict]) -> dict:
    """Read-only impact report of a project's artifacts against the advisories (shadow mode)."""
    config = project / CONFIG_NAME
    folder = DEFAULT_ARTIFACTS_DIR
    if config.is_file():
        cfg = load_json(config)
        folder = cfg.get("artifacts_dir", DEFAULT_ARTIFACTS_DIR) if isinstance(cfg, dict) else folder
    artifacts_dir = (project / folder).resolve()
    ranges = {adv["id"]: affected_releases(adv, manifests) for adv in advisories}
    markers = missing_markers()
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
            touch = _match(adv, doc, markers)  # steps 2 and 3
            if touch is None:
                continue
            if version is None:
                verdict = "possibly affected (release unknown)"
            elif _release_affected(adv, version, manifests):  # steps 4 and 5
                # the version only moves at a release: a build after release V claims V, with or without the fix
                verdict = ("possibly affected (unreleased build: it may hold the fix)" if "unreleased" in basis
                           else "affected" if touch == "affected" else "possibly affected (no trace)")
            else:
                continue
            finding = {"artifact": str(path.relative_to(artifacts_dir)), "artifact_type": doc["artifact_type"],
                       "release": version, "release_basis": basis, "advisory": adv["id"],
                       "severity": adv["severity"], "verdict": verdict, "remedy": adv.get("remedy")}
            if basis == DIGEST_CONSISTENT:
                finding["release_basis_legacy"] = "verified"  # the former name, kept for one release
            findings.append(finding)
    outputs = [{"advisory": adv["id"], "severity": adv["severity"],
                "releases_affected": ranges[adv["id"]]["releases"], "outputs": _outputs(adv),
                "remedy": adv.get("remedy")} for adv in advisories if _outputs(adv) is not None]  # step 1
    return {"status": "passed", "mode": "shadow", "project": str(project), "artifacts_dir": str(artifacts_dir),
            "artifacts_scanned": scanned, "unreadable": unreadable, "findings": findings,
            "outputs_not_artifacts": outputs,
            "advisories": {a: {"releases_affected": r["releases"]} for a, r in ranges.items()},
            "note": ("shadow mode: a report only, nothing blocks and nothing in the project is written. An artifact "
                     "is listed when its release is in an affected range and holds an affected file, and its type "
                     "and fields show the affected code ran (affected) or cannot show whether it ran (possibly "
                     "affected (no trace): artifacts written before contracts 3.5.0 carry no execution trace, and "
                     "some code runs in another process than the writer). outputs_not_artifacts lists advisories "
                     "whose code writes output that is no artifact: check any such output made with an affected "
                     "release; the scan cannot see it. release_basis 'digest-consistent' was 'verified' "
                     "(release_basis_legacy, kept for one release)")}


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
