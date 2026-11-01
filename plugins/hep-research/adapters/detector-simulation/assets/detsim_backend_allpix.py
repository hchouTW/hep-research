"""Allpix Squared backend of detsim (capability allpix.pixel-charge 1, task card AP-BOOT).

A module of detsim.py (docs/dev/detector-simulation/TASK.md 8.2, 12.2; card-AP-BOOT.md); --backend allpix-squared.
It reruns the official Allpix Squared example examples/example.conf (with example_detector.conf and
example_electric_field.init, all three unchanged and hash-pinned) with only the allowed command-line overrides
`-o number_of_events=10 -o multithreading=false -o random_seed=N`, and reads the ROOTObjectWriter file
ATTEMPT_ROOT/output/data.root.

Interface (detsim_plan.py docstring): NAME; capabilities(); code_files(capability); check(task, capability,
input_manifest) (pure: roles, pinned input hashes = check 1 at plan time, sibling layout the configuration needs);
build_spec(...) (pure: argv ENV_ROOT/allpix/bin/allpix -c INPUT_ROOT/<config> -o ..., the recorded environment
variables, expected output, timeout); collect(attempt_dir, spec) and observables(attempt_dir, spec) (the ROOT
extractor); probe(env_root) (impure, check --probe only: content-based identity and the variables).

Extractor: the trees are read through ROOT's streamer information without loading libAllpixObjects (ROOT emulates
the classes; TTree::Draw evaluates member names such as detector1.charge_ and detector1.pixel_.index_.fCoordinates.fX),
so collect needs only the ROOT Python bindings of the controller's interpreter, never the environment root. Only data
members are read (pixel index, charge_, signal_, the Event tree's seed); object references (TRef wrappers), the
stored configuration (except as recorded run configuration) and the file hash are never compared. The expected tree
set is the module chain of the configuration minus the ROOTObjectWriter include / exclude lists. collect writes one
deterministic summary, ATTEMPT_ROOT/extract/pixel_summary.json (per event: seed, per detector the PixelCharge and
PixelHit data members per pixel), and checks: config-fidelity (check 1), event-count, expected-trees, members,
hits-per-detector (check 3), plausibility-band (check 3b). compare_summaries(a, b) is check 2 (reproducibility).

ROOT is imported only inside the functions that need it (R-07 (i)); standard library, core, contracts and sibling
modules otherwise. This file never launches the simulator and never decides a run's terminal state.
"""
from __future__ import annotations

import sys

if __spec__ is None:  # run as a file (tests/skills/test_cli_robustness.py): a module of detsim.py, not a command
    if sys.argv[1:] in ([], ["--help"], ["-h"]):
        print((__doc__ or "detsim module").splitlines()[0] + "\nA module of detsim.py, not a command: "
              "python3 detsim.py --help")
        sys.exit(0)
    print('{"status": "rejected", "error_code": "usage", "message": "a module of detsim.py, not a command"}')
    sys.exit(2)

import copy  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import signal  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
from fractions import Fraction  # noqa: E402
from pathlib import Path  # noqa: E402

import detsim_canonical as canonical  # noqa: E402
import detsim_platform as platform_calls  # noqa: E402

NAME = "allpix-squared"
CAPABILITY_ID = "allpix.pixel-charge"
ASSETS_DIR = Path(__file__).resolve().parent
DESCRIPTOR_FILE = ASSETS_DIR / "allpix" / "allpix.pixel-charge.json"
PLUGIN = ASSETS_DIR.parents[2]
GEANT4_BUILD = PLUGIN / "adapters" / "geant4" / "assets" / "geant4_build.py"
ROLES = ("config", "detector", "field")
SUMMARY_FILE = "ATTEMPT_ROOT/extract/pixel_summary.json"
SUMMARY_FORMAT = "allpix-pixel-summary/1"
FIXED_OVERRIDES = ("number_of_events", "multithreading")
ALLOWED_OVERRIDES = ("number_of_events", "multithreading", "random_seed", "output_directory")
DRAW_ESTIMATE = 1000000  # rows TTree::Draw keeps per call (one event per call)
PROBE_TIMEOUT_S = 300
SYSTEM_PATH = "/usr/bin:/bin"  # for the shell scripts geant4-config and root-config during probe only


def _descriptor() -> dict:
    return json.loads(DESCRIPTOR_FILE.read_text(encoding="utf-8"))


def _error(status: str, code: str, message: str, location: str | None = None, **details):
    import detsim_plan  # sibling module (the shared layer); imported lazily to keep this module light
    return detsim_plan.DetsimError(status, code, message, location, **details)


# ---------------------------------------------------------------- interface: descriptor, checks, spec

def capabilities() -> dict:
    return {CAPABILITY_ID: _descriptor()}


def code_files(capability: dict) -> list:
    return [("detsim_backend_allpix.py", Path(__file__)), ("allpix/allpix.pixel-charge.json", DESCRIPTOR_FILE)]


def _parent(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def _sibling(path: str, name: str) -> str:
    folder = _parent(path)
    return f"{folder}/{name}" if folder else name


def check(task: dict, capability: dict, input_manifest: list) -> list:
    """Roles (one config, detector and field input), pinned hashes (check 1 at plan time) and the sibling layout the
    official configuration needs (it names its two external files relative to its own folder)."""
    issues = []
    roles = [item["role"] for item in input_manifest]
    for role in ROLES:
        if roles.count(role) != 1:
            issues.append({"code": "input-role", "kind": "rejected", "location": "$.inputs",
                           "message": f"{capability['id']} needs exactly one input of role {role} (found "
                                      f"{roles.count(role)})"})
    extra = sorted(set(roles) - set(ROLES))
    if extra:
        issues.append({"code": "input-role", "kind": "rejected", "location": "$.inputs",
                       "message": f"unknown input roles {extra}; allowed: {list(ROLES)}"})
    if issues:
        return issues
    pinned = capability["pinned"]["inputs"]
    by_role = {item["role"]: item for item in input_manifest}
    for i, item in enumerate(input_manifest):
        if item["sha256"] != pinned[item["role"]]["sha256"]:
            issues.append({"code": "input-not-pinned", "kind": "refused", "location": f"$.inputs[{i}]",
                           "message": f"input {item['path']!r} (role {item['role']}) is not the pinned official "
                                      f"{pinned[item['role']]['name']} (SHA-256 {item['sha256'][:12]}... instead of "
                                      f"{pinned[item['role']]['sha256'][:12]}...): check 1, configuration fidelity"})
    for role in ("detector", "field"):
        want = _sibling(by_role["config"]["path"], pinned[role]["name"])
        if by_role[role]["path"] != want:
            issues.append({"code": "input-layout", "kind": "rejected", "location": "$.inputs",
                           "message": f"the {role} input must be {want!r}: the official configuration names "
                                      f"{pinned[role]['name']} relative to its own folder"})
    return issues


def library_variable() -> str:
    return "DYLD_LIBRARY_PATH" if platform_calls.platform_key() == "darwin" else "LD_LIBRARY_PATH"


def library_suffix() -> str:
    return ".dylib" if platform_calls.platform_key() == "darwin" else ".so"


def build_spec(task: dict, capability: dict, input_manifest: list, environment: dict, profile: dict) -> dict:
    """The pure ExecutionSpec: the official file unchanged plus the allowed -o overrides; the environment record's
    variables (PATH, the library path, every Geant4 dataset variable of the recorded installation)."""
    identity = environment["identity"]
    pinned = capability["pinned"]
    found = (identity.get("allpix") or {}).get("version_string")
    if identity.get("backend") != NAME or found != pinned["version_string"]:
        raise _error("refused", "environment-version-mismatch", f"the environment record's Allpix Squared is "
                     f"{found!r}, the capability is pinned to {pinned['version_string']!r} (commit "
                     f"{pinned['commit']})", "$.environment_ref")
    variables = environment["variables"]
    dataset_names = [d["envvar"] for d in (identity.get("geant4") or {}).get("datasets", [])]
    needed = ["PATH", library_variable()] + dataset_names
    missing = [n for n in needed if n not in variables]
    if missing or not dataset_names:
        raise _error("refused", "environment-variables-missing", f"the environment record lacks {missing or 'the '
                     'Geant4 dataset list'}; validate the environment again with check --probe", "$.environment_ref")
    config = next(item for item in input_manifest if item["role"] == "config")
    parameters = task["parameters"]
    argv = ["ENV_ROOT/allpix/bin/allpix", "-c", "INPUT_ROOT/" + config["path"],
            "-o", f"number_of_events={parameters['number_of_events']}",
            "-o", "multithreading=" + ("true" if parameters["multithreading"] else "false"),
            "-o", f"random_seed={parameters['random_seed']}"]
    return {"argv": argv, "environment": {name: variables[name] for name in sorted(needed)}, "files": [],
            "expected_outputs": [pinned["output_file"]], "timeout_s": task["budget"]["timeout_s"]}


# ---------------------------------------------------------------- configuration and overrides

def parse_config(text: str) -> list:
    """Allpix configuration as [(section, {key: raw value})] in file order (sections may repeat); '#' comments."""
    sections, current = [], None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current = (line[1:-1].strip(), {})
            sections.append(current)
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise ValueError(f"not a key = value line: {raw!r}")
        if current is None:
            current = ("", {})
            sections.append(current)
        current[1][key.strip()] = value.strip()
    return sections


def _list_value(value: str) -> list:
    return [v.strip().strip('"') for v in value.replace(",", " ").split() if v.strip()]


def expected_trees(sections: list, descriptor: dict) -> tuple[list, list]:
    """(expected object trees, problems): the module chain's output types minus the ROOTObjectWriter include /
    exclude lists (Event is always written). An unknown module is a problem, never guessed."""
    outputs, problems, include, exclude = [], [], None, []
    skip = set(descriptor["non_module_sections"])
    for name, keys in sections:
        if name in skip:
            continue
        if name not in descriptor["module_outputs"]:
            problems.append(f"module {name!r} is not in the capability's module output map")
            continue
        outputs += [t for t in descriptor["module_outputs"][name] if t not in outputs]
        if name == "ROOTObjectWriter":
            include = _list_value(keys["include"]) if "include" in keys else None
            exclude = _list_value(keys.get("exclude", ""))
    if include is not None:
        outputs = [t for t in outputs if t in include]
    outputs = [t for t in outputs if t not in exclude]
    return sorted(outputs), problems


def detectors_of(text: str) -> list:
    return [name for name, _keys in parse_config(text) if name]


def overrides_of(argv: list) -> list:
    """[(key, value)] of every -o in argv."""
    out = []
    for i, item in enumerate(argv):
        if item == "-o" and i + 1 < len(argv):
            key, _sep, value = argv[i + 1].partition("=")
            out.append((key, value))
    return out


def _local(attempt_dir: Path, logical: str) -> Path:
    root, _sep, rest = logical.partition("/")
    base = Path(attempt_dir) / "input" if root == "INPUT_ROOT" else Path(attempt_dir)
    return base.joinpath(*rest.split("/"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def config_fidelity(attempt_dir: Path, spec: dict, descriptor: dict) -> tuple[dict, dict]:
    """Check 1 at run time: the three snapshot inputs carry the pinned hashes and the overrides are only the allowed
    keys with the fixed values. Returns (evidence, {"config": text, "detectors": [names]})."""
    argv = spec["argv"]
    problems, found = [], {}
    pinned = descriptor["pinned"]["inputs"]
    try:
        config_path = _local(attempt_dir, argv[argv.index("-c") + 1])
    except (ValueError, IndexError):
        return {"check": "config-fidelity", "result": "fail", "detail": "no -c configuration in argv"}, found
    paths = {"config": config_path, "detector": config_path.parent / pinned["detector"]["name"],
             "field": config_path.parent / pinned["field"]["name"]}
    for role, path in paths.items():
        if not path.is_file():
            problems.append(f"{role} input {path.name} missing from the snapshot")
        elif _sha256(path) != pinned[role]["sha256"]:
            problems.append(f"{role} input {path.name} is not the pinned file")
    fixed = {"number_of_events": "10", "multithreading": "false"}
    keys = [k for k, _v in overrides_of(argv)]
    for key, value in overrides_of(argv):
        if key not in ALLOWED_OVERRIDES:
            problems.append(f"override {key} is not allowed")
        elif key in fixed and value != fixed[key]:
            problems.append(f"override {key}={value} (pinned {fixed[key]})")
        elif key == "random_seed" and not (value.isdigit() and value == str(int(value))):
            problems.append(f"override random_seed={value!r} is not a decimal integer")
    for key in ("number_of_events", "multithreading", "random_seed"):
        if keys.count(key) != 1:
            problems.append(f"override {key} given {keys.count(key)} times (exactly once required)")
    if not problems:
        found["config"] = paths["config"].read_text(encoding="utf-8")
        found["detectors"] = detectors_of(paths["detector"].read_text(encoding="utf-8"))
    detail = "; ".join(problems) if problems else (
        "the three inputs carry the pinned SHA-256; overrides " + ", ".join(f"{k}={v}" for k, v in overrides_of(argv))
        + " (allowed keys only; random_seed_core not set)")
    return {"check": "config-fidelity", "result": "fail" if problems else "pass", "detail": detail}, found


# ---------------------------------------------------------------- ROOT reading (the only ROOT-dependent part)

class RootUnavailable(Exception):
    """The ROOT Python bindings cannot be imported in this interpreter (missing-dependency)."""


def import_root():
    """import ROOT in batch mode, keeping this process's SIGINT / SIGTERM handlers (ROOT installs its own)."""
    saved = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            saved[sig] = signal.getsignal(sig)
        except (ValueError, OSError):
            pass
    try:
        import ROOT  # noqa: PLC0415 - third-party import only inside the function (R-07 (i))
        ROOT.gROOT.SetBatch(True)
    except Exception as err:  # noqa: BLE001 - ImportError, or a broken installation raising at import
        raise RootUnavailable(f"{type(err).__name__}: {err}") from None
    finally:
        for sig, previous_handler in saved.items():
            try:
                if previous_handler is not None:
                    signal.signal(sig, previous_handler)
            except (ValueError, OSError, TypeError):
                pass
    return ROOT


def read_data_file(path: Path, detectors: list, number_of_events: int) -> dict:
    """The data members of data.root without the Allpix object library (emulated classes)."""
    ROOT = import_root()
    old_level = ROOT.gErrorIgnoreLevel
    ROOT.gErrorIgnoreLevel = ROOT.kError  # "no dictionary for class allpix::..." warnings: emulation is intended
    try:
        handle = ROOT.TFile.Open(str(path), "READ")
        if not handle or handle.IsZombie():
            raise OSError(f"ROOT cannot open {path.name}")
        try:
            return _read_open_file(ROOT, handle, detectors, number_of_events)
        finally:
            handle.Close()
    finally:
        ROOT.gErrorIgnoreLevel = old_level


def _draw_rows(tree, expressions: list, entry: int) -> list:
    """Rows of TTree::Draw(expr1:expr2:...) for one entry (goff); every value as a Python float."""
    tree.SetEstimate(DRAW_ESTIMATE)
    n = tree.Draw(":".join(expressions), "", "goff", 1, entry)
    if n < 0:
        raise ValueError(f"TTree::Draw failed for {expressions} in entry {entry}")
    if n > DRAW_ESTIMATE:
        raise ValueError(f"{n} rows exceed the draw estimate {DRAW_ESTIMATE}")
    columns = [tree.GetVal(i) for i in range(len(expressions))]
    return [[float(col[r]) for col in columns] for r in range(n)]


def _read_open_file(ROOT, handle, detectors: list, number_of_events: int) -> dict:
    trees, branches = {}, {}
    for key in handle.GetListOfKeys():
        if key.GetClassName() == "TTree":
            tree = handle.Get(key.GetName())
            trees[key.GetName()] = int(tree.GetEntries())
            branches[key.GetName()] = sorted(b.GetName() for b in tree.GetListOfBranches())
    members = {}
    for info in handle.GetStreamerInfoList():
        if isinstance(info, ROOT.TStreamerInfo) and info.GetName().startswith("allpix::"):
            members[info.GetName()] = {"class_version": int(info.GetClassVersion()),
                                       "members": [el.GetName() for el in info.GetElements()]}
    configuration = {}
    allpix_config = handle.Get("config/Allpix")
    if allpix_config:
        for key in allpix_config.GetListOfKeys():
            stored = allpix_config.Get(key.GetName())
            configuration[key.GetName()] = str(stored.GetTitle()) if hasattr(stored, "GetTitle") else str(stored)
    events = []
    event_tree = handle.Get("Event") if "Event" in trees else None
    for entry in range(trees.get("Event", 0)):
        event_tree.GetEntry(entry)
        events.append({"entry": entry, "id": int(event_tree.ID), "seed": str(int(event_tree.seed)),
                       "pixel_charge": {}, "pixel_hit": {}})
    for tree_name, kind, value_member in (("PixelCharge", "pixel_charge", "charge_"),
                                          ("PixelHit", "pixel_hit", "signal_")):
        if tree_name not in trees:
            continue
        tree = handle.Get(tree_name)
        for detector in detectors:
            if detector not in branches[tree_name]:
                continue
            expressions = [f"{detector}.pixel_.index_.fCoordinates.fX", f"{detector}.pixel_.index_.fCoordinates.fY",
                           f"{detector}.{value_member}"]
            for entry in range(min(trees[tree_name], len(events))):
                rows = _draw_rows(tree, expressions, entry)
                values = []
                for x, y, value in rows:
                    if kind == "pixel_charge":
                        values.append([int(x), int(y), int(value)])  # charge_ is a long: exact below 2^53
                    else:
                        values.append([int(x), int(y), repr(value)])
                events[entry][kind][detector] = values
    return {"trees": trees, "branches": branches, "classes": members, "configuration": configuration,
            "events": events, "root_version": str(ROOT.gROOT.GetVersion())}


# ---------------------------------------------------------------- evaluation (pure; tested without ROOT)

def median(values: list) -> Fraction:
    ordered = sorted(Fraction(v) for v in values)
    if not ordered:
        raise ValueError("median of no values")
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def _decimal_text(value: Fraction) -> str:
    """The median as decimal/1: exact for an integer or a half-integer (the median of integer sums)."""
    if value.denominator == 1:
        return canonical.normalize_decimal(str(value.numerator))
    if value.denominator == 2:
        return canonical.normalize_decimal(str(value.numerator * 5) + "e-1")
    return canonical.normalize_decimal(repr(float(value)))


def charge_sums(events: list, detector: str) -> list:
    """Per event, the sum over detector's pixels of getAbsoluteCharge() = |charge_| (Allpix stores charge signed)."""
    return [sum(abs(c) for _x, _y, c in event["pixel_charge"].get(detector, [])) for event in events]


def plausibility(sums: list, descriptor: dict) -> dict:
    band = descriptor["checks"]["band_e"]
    low, high = Fraction(band["low"]), Fraction(band["high"])
    if not sums:
        return {"check": "plausibility-band", "result": "fail", "detail": "no events"}
    value = median(sums)
    ok = low <= value <= high
    return {"check": "plausibility-band", "result": "pass" if ok else "fail",
            "detail": f"plausibility, not physics validation: median over {len(sums)} events of the per-event sum of "
                      f"PixelCharge::getAbsoluteCharge() over {descriptor['checks']['band_detector']} pixels = "
                      f"{_decimal_text(value)} e; band [{band['low']}, {band['high']}] e"}


def run_settings(raw: dict, descriptor: dict, number_of_events: int, random_seed: str | None) -> dict:
    """Spot check of what ran, from the configuration the program stored in its file: the program version is the
    pinned one and number_of_events, multithreading and random_seed are the planned values."""
    stored = {k: str(v).strip().strip('"') for k, v in raw.get("configuration", {}).items()}
    want = {"version": descriptor["pinned"]["version_string"], "number_of_events": str(number_of_events),
            "multithreading": "false"}
    if random_seed is not None:
        want["random_seed"] = random_seed
    wrong = [f"{k} = {stored.get(k)!r} (planned {v!r})" for k, v in want.items() if stored.get(k) != v]
    return {"check": "run-settings", "result": "fail" if wrong else "pass",
            "detail": "; ".join(wrong) if wrong else "stored configuration: " + ", ".join(
                f"{k} = {stored[k]}" for k in sorted(want)) + (f", random_seed_core = {stored['random_seed_core']} "
                                                               "(derived by Allpix)" if "random_seed_core" in stored
                                                               else "")}


def evaluate(raw: dict, config_text: str, detectors: list, descriptor: dict, number_of_events: int,
             random_seed: str | None = None) -> list:
    """The evidence of checks 3 and 3b, the run settings, the event count, the expected tree set and the members."""
    evidence = [run_settings(raw, descriptor, number_of_events, random_seed)]
    sections = parse_config(config_text)
    expected, problems = expected_trees(sections, descriptor)
    trees = raw["trees"]
    count_ok = trees.get("Event") == number_of_events and len(raw["events"]) == number_of_events
    evidence.append({"check": "event-count", "result": "pass" if count_ok else "fail",
                     "detail": f"Event tree entries {trees.get('Event')}, expected {number_of_events}"})
    present = sorted(t for t in trees if t != "Event")
    absent = [t for t in expected if t not in trees]
    unexpected = [t for t in present if t not in expected]
    short = [t for t in expected if t in trees and trees[t] != number_of_events]
    required_by_checks = [t for t in ("PixelCharge", "PixelHit") if t in absent]
    tree_problems = problems + [f"unexpected tree {t} (excluded or not produced by the module chain)"
                                for t in unexpected] + [f"tree {t} has {trees[t]} entries" for t in short] + [
        f"tree {t} is missing (checks 3 and 3b need it)" for t in required_by_checks]
    evidence.append({"check": "expected-trees", "result": "fail" if tree_problems else "pass",
                     "detail": "; ".join(tree_problems) if tree_problems else
                     f"expected {expected} (module chain minus the ROOTObjectWriter include / exclude lists) + Event; "
                     f"present {present}" + (f"; no tree for {absent}: no objects of that type in any event "
                                              "(upstream rule; never filled with zeros)" if absent else "")})
    member_problems = []
    for cls, names in sorted(descriptor["members"].items()):
        found = raw.get("classes", {}).get(cls)
        if found is None:
            member_problems.append(f"{cls}: no streamer information")
        else:
            member_problems += [f"{cls}::{n} absent" for n in names if n not in found["members"]]
    evidence.append({"check": "members", "result": "fail" if member_problems else "pass",
                     "detail": "; ".join(member_problems) if member_problems else
                     "data members read through the streamer information: " + ", ".join(
                         f"{c} v{raw['classes'][c]['class_version']}" for c in sorted(descriptor["members"]))})
    missing_hits = []
    for event in raw["events"]:
        for detector in detectors:
            if not event["pixel_hit"].get(detector):
                missing_hits.append(f"event {event['id']} {detector}")
    hits_ok = bool(raw["events"]) and bool(detectors) and not missing_hits and "PixelHit" in trees
    evidence.append({"check": "hits-per-detector", "result": "pass" if hits_ok else "fail",
                     "detail": (f"no PixelHit in: {', '.join(missing_hits[:20])}" if missing_hits else
                                f"every one of {len(raw['events'])} events has at least one PixelHit in each of "
                                f"{detectors}")})
    if "PixelCharge" in trees and raw["events"]:
        evidence.append(plausibility(charge_sums(raw["events"], descriptor["checks"]["band_detector"]), descriptor))
    else:
        evidence.append({"check": "plausibility-band", "result": "fail", "detail": "no PixelCharge data"})
    return evidence


def summary_document(raw: dict, source_sha256: str, detectors: list, expected: list) -> dict:
    """The deterministic per-pixel summary (check 2 compares its events part)."""
    events = []
    for event in raw["events"]:
        events.append({"id": event["id"], "seed": event["seed"],
                       "detectors": {d: {"pixel_charge": event["pixel_charge"].get(d, []),
                                         "pixel_hit": event["pixel_hit"].get(d, [])} for d in detectors}})
    keep = ("number_of_events", "multithreading", "random_seed", "random_seed_core", "version")
    return {"format": SUMMARY_FORMAT, "source": "output/data.root", "source_sha256": source_sha256,
            "columns": {"pixel_charge": ["index_x", "index_y", "charge_e_signed"],
                        "pixel_hit": ["index_x", "index_y", "signal_e"]},
            "detectors": detectors, "expected_trees": expected, "trees": raw["trees"],
            "classes": {c: v["class_version"] for c, v in sorted(raw.get("classes", {}).items())},
            "run_configuration": {k: raw["configuration"][k] for k in keep if k in raw["configuration"]},
            "run_configuration_note": "read from the file's stored configuration; recorded, never compared "
                                      "(random_seed_core is derived by Allpix as random_seed + 1)",
            "extractor_root_version": raw.get("root_version"), "events": events}


def compare_summaries(a: dict, b: dict) -> dict:
    """Check 2: data members per event, detector and pixel, and the per-event seeds; never the configuration,
    references or file hashes. {"identical": bool, "differences": [...] (first 50), "pixels_compared": n}."""
    differences, pixels = [], 0
    ea, eb = a.get("events", []), b.get("events", [])
    if len(ea) != len(eb):
        differences.append(f"event count {len(ea)} vs {len(eb)}")
    for x, y in zip(ea, eb):
        if x["id"] != y["id"] or x["seed"] != y["seed"]:
            differences.append(f"event {x['id']}: id/seed {x['id']}/{x['seed']} vs {y['id']}/{y['seed']}")
        for detector in sorted(set(x["detectors"]) | set(y["detectors"])):
            dx, dy = x["detectors"].get(detector, {}), y["detectors"].get(detector, {})
            for kind in ("pixel_charge", "pixel_hit"):
                px, py = dx.get(kind, []), dy.get(kind, [])
                pixels += max(len(px), len(py))
                if px != py:
                    differences.append(f"event {x['id']} {detector} {kind}: {px[:4]} vs {py[:4]}")
    return {"identical": not differences, "differences": differences[:50], "difference_count": len(differences),
            "pixels_compared": pixels}


# ---------------------------------------------------------------- collect and observables

def collect(attempt_dir: Path, spec: dict) -> dict:
    attempt_dir = Path(attempt_dir)
    descriptor = _descriptor()
    data_file = _local(attempt_dir, spec["expected_outputs"][0])
    missing = [p for p in spec["expected_outputs"] if not _local(attempt_dir, p).is_file()]
    evidence = [{"check": "expected-outputs", "result": "fail" if missing else "pass",
                 "detail": f"missing {missing}" if missing else "output/data.root present"}]
    fidelity, found = config_fidelity(attempt_dir, spec, descriptor)
    evidence.append(fidelity)
    if missing or fidelity["result"] != "pass":
        return _completeness("partial" if missing else "invalid", evidence, missing)
    number_of_events = int(dict(overrides_of(spec["argv"]))["number_of_events"])
    detectors = found["detectors"]
    try:
        raw = read_data_file(data_file, detectors, number_of_events)
    except RootUnavailable as err:
        evidence.append({"check": "dependency", "result": "fail",  # the shared layer maps it to missing-dependency
                         "detail": f"missing-dependency: the ROOT Python bindings are not importable in this "
                                   f"controller ({sys.executable}): {err}"})
        return _completeness("invalid", evidence, [])
    except Exception as err:  # noqa: BLE001 - an unreadable or malformed file is an invalid output, reported
        evidence.append({"check": "root-read", "result": "fail", "detail": f"{type(err).__name__}: {err}"})
        return _completeness("invalid", evidence, [])
    evidence.append({"check": "root-read", "result": "pass",
                     "detail": f"read with ROOT {raw['root_version']} through the streamer information "
                               "(libAllpixObjects not loaded)"})
    checks = evaluate(raw, found["config"], detectors, descriptor, number_of_events,
                      dict(overrides_of(spec["argv"])).get("random_seed"))
    evidence += checks
    expected, _problems = expected_trees(parse_config(found["config"]), descriptor)
    summary = summary_document(raw, _sha256(data_file), detectors, expected)
    target = _local(attempt_dir, SUMMARY_FILE)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    failed = [e for e in checks if e["result"] != "pass"]
    partial = any(e["check"] in ("event-count", "expected-trees") for e in failed)
    state = "complete" if not failed else ("partial" if partial else "invalid")
    return _completeness(state, evidence, [])


def _completeness(state: str, evidence: list, missing: list) -> dict:
    return {"schema": "detsim-completeness/1", "state": state, "evidence": evidence, "missing_outputs": missing}


def _number(value) -> str:
    return canonical.normalize_decimal(str(value))


def observables(attempt_dir: Path, spec: dict) -> dict:
    """detsim-observables/1 rows from the summary collect wrote (checked against data.root's hash): per event and
    detector pixel_charge_abs_sum (e), pixel_charge_count and pixel_hit_count (1); per pixel pixel_charge (signed, e)
    and pixel_hit_signal (e) with component pixel_<x>_<y>; per event event_seed (1). point = the Allpix event ID."""
    attempt_dir = Path(attempt_dir)
    summary = json.loads(_local(attempt_dir, SUMMARY_FILE).read_text(encoding="utf-8"))
    source = _sha256(_local(attempt_dir, spec["expected_outputs"][0]))
    if source != summary["source_sha256"]:
        raise ValueError("data.root changed after collect (its hash differs from the summary's)")
    rows = []

    def row(quantity, unit, value, event, detector=None, component=None):
        out = {"quantity": quantity, "unit": unit, "value": _number(value), "uncertainty_type": "none",
               "point_kind": "event", "point": event, "labels": ["unvalidated"], "source_sha256": source}
        if detector is not None:
            out["detector"] = detector
        if component is not None:
            out["component"] = component
        rows.append(out)

    for event in summary["events"]:
        row("event_seed", "1", event["seed"], event["id"])
        for detector in summary["detectors"]:
            pixels = event["detectors"][detector]
            row("pixel_charge_abs_sum", "e", sum(abs(c) for _x, _y, c in pixels["pixel_charge"]), event["id"], detector)
            row("pixel_charge_count", "1", len(pixels["pixel_charge"]), event["id"], detector)
            row("pixel_hit_count", "1", len(pixels["pixel_hit"]), event["id"], detector)
            for x, y, charge in pixels["pixel_charge"]:
                row("pixel_charge", "e", charge, event["id"], detector, f"pixel_{x}_{y}")
            for x, y, signal_text in pixels["pixel_hit"]:
                row("pixel_hit_signal", "e", signal_text, event["id"], detector, f"pixel_{x}_{y}")
    return {"schema": "detsim-observables/1", "rows": rows}


# ---------------------------------------------------------------- probe (check --probe only)

def _run(argv: list, env: dict, timeout: int = PROBE_TIMEOUT_S) -> subprocess.CompletedProcess:
    return subprocess.run(argv, env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)


def _bound_variables(variables: dict, env_root: Path) -> dict:
    return {name: str(env_root) + value[len("ENV_ROOT"):] if value.startswith("ENV_ROOT/") else value
            for name, value in variables.items()}


def _missing(message: str, missing: list):
    return _error("missing-dependency", "missing-dependency", message, "--env-root", missing=missing)


def _datasets(env_root: Path) -> list:
    """(name, envvar, folder name) of every dataset geant4-config --datasets lists for the linked Geant4."""
    config = env_root / "geant4" / "bin" / "geant4-config"
    out = _run([str(config), "--datasets"], {"PATH": SYSTEM_PATH})
    if out.returncode != 0:
        raise _missing(f"geant4-config --datasets failed: {out.stderr.strip()[-300:]}", ["geant4/bin/geant4-config"])
    found = []
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            found.append((parts[0], parts[1], Path(parts[2]).name))
    if not found:
        raise _missing("geant4-config --datasets lists no dataset", ["Geant4 datasets"])
    return found


def _root_version(env_root: Path) -> str:
    out = _run([str(env_root / "root" / "bin" / "root-config"), "--version"], {"PATH": SYSTEM_PATH})
    if out.returncode != 0 or not out.stdout.strip():
        raise _missing("root-config --version failed", ["root/bin/root-config"])
    return out.stdout.strip()


def _allpix_version(env_root: Path, variables: dict) -> tuple[str, str]:
    env = _bound_variables(variables, env_root)
    out = _run([str(env_root / "allpix" / "bin" / "allpix"), "--version"], env)
    text = (out.stdout or "") + (out.stderr or "")
    first = next((line for line in text.splitlines() if "version" in line), "")
    words = first.split()
    version = words[words.index("version") + 1] if "version" in words[:-1] else ""
    if out.returncode != 0 or not version:
        raise _missing(f"allpix --version failed (exit {out.returncode}): {text.strip()[-300:]}", ["allpix"])
    return version, "\n".join(line.strip() for line in text.replace("\x1b[?25l", "").replace("\x1b[?25h", "")
                              .splitlines() if line.strip())


def _geant4_registration(env_root: Path, variables: dict) -> dict:
    """geant4_build.py register and check (subprocesses, TASK.md 7) on the linked Geant4 with the dataset variables
    of the plan; the record goes to a temporary folder (path-bearing, never part of the identity)."""
    env = _bound_variables({n: v for n, v in variables.items() if n not in ("PATH", library_variable())}, env_root)
    env["PATH"] = SYSTEM_PATH
    with tempfile.TemporaryDirectory(prefix="detsim-allpix-probe-") as scratch:
        record = Path(scratch) / "geant4-register.json"
        reg = _run([sys.executable, "-I", str(GEANT4_BUILD), "register", "--geant4-config",
                    str(env_root / "geant4" / "bin" / "geant4-config"), "--dataset-source", "env",
                    "--no-cmake-probe", "--record", str(record)], env)
        if reg.returncode != 0 or not record.is_file():
            try:
                why = json.loads(reg.stdout).get("refused") or reg.stdout[-400:]
            except ValueError:
                why = (reg.stdout + reg.stderr)[-400:]
            raise _missing(f"geant4_build.py register refused the linked Geant4 (exit {reg.returncode}): {why}",
                           ["Geant4 datasets"])
        chk = _run([sys.executable, "-I", str(GEANT4_BUILD), "check", "--record", str(record)], env)
        if chk.returncode != 0:
            raise _missing(f"geant4_build.py check failed (exit {chk.returncode}): {chk.stdout[-400:]}",
                           ["Geant4 datasets"])
        doc = json.loads(record.read_text(encoding="utf-8"))
    build = doc["extension"]["build"]
    datasets = sorted(({"name": d["name"], "version": d["version"], "envvar": d["envvar"],
                        "content_sha256": d["content_sha256"], "n_files": d["n_files"]} for d in build["datasets"]),
                      key=lambda d: d["envvar"])
    version = json.loads(reg.stdout).get("version") or ""
    return {"datasets": datasets, "version": version, "cxx_standard": build.get("cmake_cxx_standard"),
            "register": "ok", "check": json.loads(chk.stdout).get("status")}


def probe(env_root: Path) -> dict:
    """{identity, variables, facts} of an Allpix Squared environment root holding allpix/, geant4/, root/, deps/ and
    data/<dataset folder> (card AP-BOOT). Content-based identity: the Allpix version string, the SHA-256 of the
    executable, libAllpixCore and libAllpixObjects and of the model file cmsp1.conf, the Geant4 version and its
    datasets' content hashes (geant4_build.py register / check), the ROOT version and the platform; never a path.
    missing-dependency when the ROOT bindings (for the extractor), a program, a library, a dataset folder or a
    dataset variable is missing; refused when the Allpix version is not the pinned one."""
    env_root = Path(env_root)
    descriptor = _descriptor()
    try:
        ROOT = import_root()
        extractor_root = str(ROOT.gROOT.GetVersion())
    except RootUnavailable as err:
        raise _missing(f"the extractor needs the ROOT Python bindings in the controller's interpreter "
                       f"({sys.executable}): {err}", ["ROOT"]) from None
    suffix = library_suffix()
    required = {"allpix": "allpix/bin/allpix", "libAllpixCore": f"allpix/lib/libAllpixCore{suffix}",
                "libAllpixObjects": f"allpix/lib/libAllpixObjects{suffix}", "geant4-config": "geant4/bin/geant4-config",
                "root-config": "root/bin/root-config"}
    models = {Path(m).name: m for m in descriptor["pinned"]["model_files"]}
    absent = [rel for rel in list(required.values()) + list(models.values()) if not (env_root / rel).is_file()]
    if not (env_root / "deps" / "lib").is_dir():
        absent.append("deps/lib")
    if absent:
        raise _missing(f"the environment root lacks {absent}", absent)
    datasets = _datasets(env_root)
    variables = {"PATH": "ENV_ROOT/allpix/bin", library_variable(): "ENV_ROOT/allpix/lib"}
    no_folder = []
    for _name, envvar, folder in datasets:
        path = env_root / "data" / folder
        if not path.is_dir() or not any(path.iterdir()):
            no_folder.append(f"{envvar} (data/{folder})")
        variables[envvar] = f"ENV_ROOT/data/{folder}"
    if no_folder:
        raise _missing(f"Geant4 dataset folders missing or empty under data/: {no_folder}", no_folder)
    version, version_text = _allpix_version(env_root, variables)
    if version != descriptor["pinned"]["version_string"]:
        raise _error("refused", "backend-version-mismatch", f"allpix --version reports {version!r}; the capability "
                     f"is pinned to {descriptor['pinned']['version_string']!r}", "--env-root")
    registration = _geant4_registration(env_root, variables)
    recorded = sorted(d["envvar"] for d in registration["datasets"])
    if recorded != sorted(e for _n, e, _f in datasets):
        raise _missing(f"geant4_build.py recorded datasets {recorded}, geant4-config lists "
                       f"{sorted(e for _n, e, _f in datasets)}", ["Geant4 datasets"])
    identity = {
        "backend": NAME,
        "kind": "source-build view",
        "platform": f"{platform_calls.platform_key()}-{platform.machine()}",
        "allpix": {"version_string": version, "commit_abbrev": version.rsplit("-g", 1)[-1],
                   "sha256": {name: _sha256(env_root / rel) for name, rel in required.items()
                              if name in ("allpix", "libAllpixCore", "libAllpixObjects")},
                   "models_sha256": {name: _sha256(env_root / rel) for name, rel in sorted(models.items())}},
        "geant4": {"version": registration["version"], "cxx_standard": registration["cxx_standard"],
                   "datasets": registration["datasets"]},
        "root": {"version": _root_version(env_root)},
    }
    facts = {"backend": NAME, "allpix_version_text": version_text, "extractor_root_version": extractor_root,
             "controller_python": platform.python_version(), "geant4_register": registration["register"],
             "geant4_check": registration["check"],
             "library_resolution": "Geant4, ROOT and dependency libraries through the executable's LC_RPATH / "
                                   "RUNPATH entries; the library path variable names ENV_ROOT/allpix/lib only"}
    return {"identity": copy.deepcopy(identity), "variables": variables, "facts": facts}
