#!/usr/bin/env python3
"""T12 stage 2: reprocessing scenarios for conditions, invalidation and identity (T12-05 to T12-09, T12-24 to T12-27; plan v9.2
Sections 9.3, 9.4, 9.8, 9.9; A04, A14, A32, A40, A42).

A harness for interface tests, with synthetic DAGs and frozen recorded files read only. No quality claim. Every rule and expectation is
fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 2"). It lives under tests/ because it imports the contracts, a skill's
scripts and an adapter's recipe module (tools/check_layering.py).

- Workspace: a work folder with a DAG (calibrate -> cluster -> response -> report, plus pedestal-monitor; optionally a legacy step with
  an undeclared executable), run by skills/hep-computing/scripts/run_workflow.py, and the changes R1-R5 apply to it. Every step script is
  written here; `bin/cluster-tool` is an executable stand-in for a native binary, declared as a native input.
- configuration_change: what a changed configuration key means for revalidation (R6).
- quality_reuse_probe: the control layer's view of a reused artifact under a stricter criterion (R7).
- bind_chunk, check_chunk_binding: one payload per key of a chunk (R8).
- scope_check: source and output scope of the running process (R9).

Operation:
  scope-check --snapshot DIR --live DIR [--live DIR ...] [--evidence-path PATH ...] [--import MODULE ...]
      imports the named modules, then checks this process: every sys.path entry, every loaded module's file, the working folder and each
      evidence path must lie outside every live root, and this file must lie inside the snapshot. Status and exit (core/status.py): ok 0;
      rejected 2, with the offending paths; incomplete 3.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import importlib.util
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.status import exit_code  # noqa: E402

RUNNER = ROOT / "skills" / "hep-computing" / "scripts" / "run_workflow.py"
T08_CONFIGURATION = ROOT / "adapters" / "calo-cluster" / "assets" / "t08-grid-1.configuration.json"
T09_BUDGET = ROOT / "adapters" / "photon-likelihood" / "assets" / "t09-multistart-1.budget.json"
T08_CONFIGURATION_SHA256 = "5fbbea3b4ca81d962c5ca70fa024ddc82dd6e1d2f06e39b354fda56d26483723"   # Freeze B, T08 configuration
T09_BUDGET_SHA256 = "70220b7ddf1679d01d4a9c5397d1fdf124c6f0bd8ed4dca562d9c18e04180307"   # t09-multistart-1 budget
TAG = "t12_stage2_gain"
# The runner runs in this process with a pinned known release digest, as tests/skills/hep_computing/test_workflow_b1.py does: in a
# development tree the digest is unknown and INC-03 then never skips, which would hide every skip and every rerun decision.
PINNED_RELEASE = {"release": "t12-stage2-harness", "digest": "e" * 64, "source": "pinned by the T12 stage 2 harness"}
STEPS = ("calibrate", "pedestal-monitor", "cluster", "response", "report")

PHYSICS = "physics: response revalidation required"
LIMIT = "candidate or resource limit: response revalidation to be judged"
IDENTITY = "identity"
METADATA = "metadata"
CATEGORIES = {
    "calo-cluster-configuration": {"format": IDENTITY, "recipe": IDENTITY, "source": METADATA, "grid": PHYSICS,
                                   "shower_width_cells": PHYSICS, "cell_quantum_mev": PHYSICS, "noise_sigma_mev": PHYSICS,
                                   "cell_threshold_mev": PHYSICS, "seed_threshold_mev": PHYSICS, "sharing_iterations": PHYSICS,
                                   "peaks_kept": PHYSICS},
    "light-likelihood-multistart": {"format": IDENTITY, "starts": LIMIT, "tie_tolerance": LIMIT},
}


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def frozen_bytes(path: Path, expected: str) -> bytes:
    """A frozen file, read by SHA-256: refused if its bytes are not the Freeze B ones."""
    content = path.read_bytes()
    if sha256_hex(content) != expected:
        raise ValueError(f"{path.name} is not the frozen file (SHA-256 {sha256_hex(content)}, expected {expected})")
    return content


# ================================================================ R6: configuration changes

def configuration_change(old: dict, changed: dict) -> dict:
    """{changed key: category} for two documents of one configuration family. An unknown key is a KeyError: a key with no category
    cannot be judged, so it is refused rather than guessed."""
    family = str(old.get("format", "")).rsplit("/", 1)[0]
    table = CATEGORIES[family]
    unknown = sorted((set(old) | set(changed)) - set(table))
    if unknown:
        raise KeyError(f"keys without a category in {family}: {unknown}")
    return {key: table[key] for key in sorted(set(old) | set(changed)) if old.get(key) != changed.get(key)}


# ================================================================ R8: one payload per key of a chunk

def _holding(key, payloads) -> list:
    """The payloads whose IOV holds the key, each read on its own coordinates (fix round 1, M6)."""
    from contracts.conditions import iov_holds
    return [p for p in payloads
            if {pred["coordinate"] for pred in p["iov"]["predicates"]} == {COORDINATE} and iov_holds(p, {COORDINATE: key})]


COORDINATE = "position-key"   # the chunk's key axis: a payload valid on another coordinate holds no key of it


def bind_chunk(keys, payloads) -> list:
    """Bind each key to the one payload whose IOV holds it; consecutive keys with one payload form one part (Section 9.3)."""
    parts = []
    for key in keys:
        holding = _holding(key, payloads)
        if len(holding) != 1:
            raise ValueError(f"no payload holds key {key}" if not holding else f"{len(holding)} payloads hold key {key}")
        pid = holding[0]["payload_id"]
        if parts and parts[-1]["payload_id"] == pid and parts[-1]["keys"][1] == key - 1:
            parts[-1]["keys"][1] = key
        else:
            parts.append({"keys": [key, key], "payload_id": pid})
    return parts


def check_chunk_binding(binding, payloads, keys) -> dict:
    """A binding of a chunk's keys: keys whose payload's IOV does not hold them (the first event's payload applied to a whole
    chunk), keys of the chunk no part covers, and keys two parts cover (fix round 1, M6)."""
    by_id = {p["payload_id"]: p for p in payloads}
    wrong, seen, twice = [], {}, []
    for part in binding:
        first, last = part["keys"]
        for key in range(first, last + 1):
            if key in seen:
                twice.append(key)
            seen[key] = True
            if by_id.get(part["payload_id"]) not in _holding(key, payloads):
                wrong.append(key)
    return {"wrong_payload": sorted(set(wrong)), "uncovered": [k for k in keys if k not in seen], "overlapping": sorted(set(twice))}


# ================================================================ R7: quality reuse in the control layer

def quality_reuse_probe() -> dict:
    """A product with a pass under criterion A and an older fail under criterion F; a stricter contract adds criterion B. The labels
    after each event, and the historical failures (the derivation of the control layer, as stage 1)."""
    sys.path.insert(0, str(ROOT / "skills" / "hep-computing" / "scripts"))
    from control_layer_support import derivation as dv
    check, crit_a, crit_b, crit_f = "c" * 64, "a" * 64, "b" * 64, "f" * 64

    def contract(required):
        return {"steps": {"product": dv.StepSpec(program="t12.product/1", checked=True, required=frozenset(required))},
                "deliverables": {}, "families": {}, "samples": {}, "budget": None}

    log = dv.Log()
    log.append("session", "C", mode="M1")
    log.append("contract", "agent", spec=contract({(check, crit_a)}))
    dv.admit(log, log.head, "product:1", "product", cost=0.0)
    digest = "d" * 64
    log.append("receipt", "adapter", attempt="product:1", end="success", termination="confirmed", outputs=(digest,))

    def run_check(attempt, crit, result):
        dv.admit(log, log.head, attempt, "__check__", cost=0.0, check=(check, crit, digest))
        log.append_batch([("receipt", "adapter", dict(attempt=attempt, end="success", termination="confirmed", outputs=())),
                          ("check_result", "adapter", dict(target=digest, check=check, criteria=crit, check_attempt=attempt,
                                                           result=result))])

    run_check("check:f", crit_f, "fail")      # an older check under another criterion: not required, so historical
    run_check("check:a", crit_a, "pass")
    found = {"label_before": dv.label(log, digest)}
    log.append("contract", "agent", spec=contract({(check, crit_a), (check, crit_b)}))   # stricter: effective at once (M1)
    found["label_after_new_criterion"] = dv.label(log, digest)
    dv.admit(log, log.head, "product:reuse", "product", cost=0.0, reuse_source=digest)
    found["label_after_reuse"] = dv.label(log, digest)
    run_check("check:b", crit_b, "pass")
    found["label_after_new_check"] = dv.label(log, digest)
    found["historical_failures"] = [list(f) for f in dv.historical_failures(log, digest)]
    found.update(old_check=check, old_criterion=crit_f)
    return found


# ================================================================ R1-R5: the reprocessing workspace

CALIBRATE = """import json, sys
sidecar, values, raw, out, product = sys.argv[1:6]
side = json.load(open(sidecar)); gains = json.load(open(values))["gains"]; adc = json.load(open(raw))["adc"]
json.dump({"energies": [a / g for a, g in zip(adc, gains)]}, open(out, "w"), sort_keys=True)
used = [{"slot": "gain", "tag": side["tag"], "payload_id": side["payload_id"], "origin": side["origin"], "round": None}]
json.dump({"schema": "reconstruction-product/1", "product_id": "product.t12s2.calibrated", "revision": 1, "collection": "measurements",
           "native": {"type": "synthetic::T12CalibratedCells"}, "presence": "present", "role": "reconstruction-input",
           "conditions_used": used, "required_extensions": []}, open(product, "w"), sort_keys=True)
"""
MONITOR = """import json, sys
sidecar, raw, out = sys.argv[1:4]
json.dump({"pedestal_payload": json.load(open(sidecar))["payload_id"], "cells": len(json.load(open(raw))["adc"])}, open(out, "w"),
          sort_keys=True)
"""
CLUSTER = """import hashlib, json, os, sys
calibrated, config, out, version = sys.argv[1:5]
os.makedirs(os.path.dirname(out), exist_ok=True)
energies = json.load(open(calibrated))["energies"]; cfg = json.load(open(config))
kept = [e for e in energies if e >= cfg["cell_threshold_mev"]]
json.dump({"tool": version, "configuration_sha256": hashlib.sha256(open(config, "rb").read()).hexdigest(),
           "seed_threshold_mev": cfg["seed_threshold_mev"], "cluster_energy": sum(kept), "cells": len(kept)}, open(out, "w"), sort_keys=True)
"""
RESPONSE = """import json, sys
clusters, out = sys.argv[1:3]
c = json.load(open(clusters))
json.dump({"configuration_sha256": c["configuration_sha256"], "tool": c["tool"], "pairing": [c["cluster_energy"], c["cells"]]},
          open(out, "w"), sort_keys=True)
"""
REPORT = """import json, sys
response, meta, out = sys.argv[1:4]
r = json.load(open(response)); m = json.load(open(meta))
open(out, "w").write(f"# {m['title']}\\n\\nconfiguration {r['configuration_sha256']}; tool {r['tool']}; pairing {r['pairing']}\\n")
"""
TOOL = """#!/bin/sh
# bin/cluster-tool: an executable stand-in for a native binary (T12 stage 2){comment}
exec "{python}" -B steps/cluster.py "$1" "$2" "$3" "{version}"
"""
LEGACY = "#!/bin/sh\n# an executable the workflow does not declare\nprintf 'legacy\\n' > \"$1\"\n"


class Workspace:
    """A reprocessing work folder. run() returns {step: skipped}."""

    def __init__(self, root: Path, legacy: bool = False):
        self.root, self.legacy = Path(root), legacy
        self.work = self.root / "work"
        self.tool_version, self.tool_comment = "1", ""
        self.configuration = frozen_bytes(T08_CONFIGURATION, T08_CONFIGURATION_SHA256)
        self.write("raw.json", json.dumps({"adc": [10.0, 22.0, 5.0, 40.0]}))
        self.write("conditions/pedestal.json", json.dumps(self.payload("pedestal", [0.0] * 4)))
        self.set_gain([1.0, 1.0, 1.0, 1.0])
        self.write("config/t08.configuration.json", self.configuration)
        self.write("report-meta.json", json.dumps({"title": "T12 reprocessing"}))
        for name, text in (("calibrate", CALIBRATE), ("monitor", MONITOR), ("cluster", CLUSTER), ("response", RESPONSE),
                           ("report", REPORT)):
            self.write(f"steps/{name}.py", text)
        self.write_tool()
        if legacy:
            self.write("bin/legacy-tool", LEGACY, executable=True)

    # ---------------------------------------------------------------- files
    def write(self, name: str, content, executable: bool = False) -> None:
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
        if executable:
            path.chmod(0o755)

    def read_bytes(self, name: str) -> bytes:
        return (self.work / name).read_bytes()

    def read_json(self, name: str):
        return json.loads(self.read_bytes(name))

    def exists(self, name: str) -> bool:
        return (self.work / name).is_file()

    def configuration_sha256(self) -> str:
        return sha256_hex(self.read_bytes("config/t08.configuration.json"))

    def scientific_outputs(self) -> list:
        sha = self.configuration_sha256()
        return ["calibrated.json", "calibrated.product.json", "monitor.json", f"products/{sha}/clusters.json", "response.json"]

    # ---------------------------------------------------------------- conditions
    def payload(self, slot: str, values: list) -> dict:
        from tests.contracts.reconstruction_fixtures import calibration_payload
        content = json.dumps({"slot": slot, "gains": values}, sort_keys=True).encode()
        return calibration_payload(tag=TAG if slot == "gain" else "t12_stage2_pedestal", content_sha256=sha256_hex(content),
                                   producer={"kind": "external", "source": f"synthetic T12 stage 2 {slot}"})

    def set_gain(self, gains: list) -> None:
        content = json.dumps({"slot": "gain", "gains": gains}, sort_keys=True)
        self.write("conditions/gain.values.json", content)
        self.write("conditions/gain.json", json.dumps(self.payload("gain", gains)))

    # ---------------------------------------------------------------- the changes R1-R5
    def change_gain(self, gains: list) -> None:
        self.set_gain(gains)

    def write_tool(self) -> None:
        comment = f"\n{self.tool_comment}" if self.tool_comment else ""
        self.write("bin/cluster-tool", TOOL.format(python=sys.executable, version=self.tool_version, comment=comment), executable=True)

    def rebuild_tool(self, version: str, comment: str = "") -> None:
        self.tool_version, self.tool_comment = version, comment
        self.write_tool()

    def change_configuration(self, **changes) -> None:
        document = json.loads(self.configuration)
        document.update(changes)
        self.write("config/t08.configuration.json", json.dumps(document, indent=1) + "\n")

    def change_title(self, title: str) -> None:
        self.write("report-meta.json", json.dumps({"title": title}))

    # ---------------------------------------------------------------- the workflow
    def workflow(self) -> dict:
        clusters = f"products/{self.configuration_sha256()}/clusters.json"
        py = "{python}"
        steps = [
            {"id": "calibrate", "argv": [py, "steps/calibrate.py", "conditions/gain.json", "conditions/gain.values.json", "raw.json",
                                         "calibrated.json", "calibrated.product.json"],
             "inputs": ["conditions/gain.json", "conditions/gain.values.json", "raw.json"],
             "outputs": ["calibrated.json", "calibrated.product.json"]},
            {"id": "pedestal-monitor", "argv": [py, "steps/monitor.py", "conditions/pedestal.json", "raw.json", "monitor.json"],
             "inputs": ["conditions/pedestal.json", "raw.json"], "outputs": ["monitor.json"]},
            {"id": "cluster", "needs": ["calibrate"],
             "argv": ["bin/cluster-tool", "calibrated.json", "config/t08.configuration.json", clusters],
             "inputs": ["calibrated.json", "config/t08.configuration.json"], "outputs": [clusters],
             "native_inputs": ["bin/cluster-tool", "steps/cluster.py"]},
            {"id": "response", "needs": ["cluster"], "argv": [py, "steps/response.py", clusters, "response.json"],
             "inputs": [clusters], "outputs": ["response.json"]},
            {"id": "report", "needs": ["response"], "argv": [py, "steps/report.py", "response.json", "report-meta.json", "report.md"],
             "inputs": ["response.json", "report-meta.json"], "outputs": ["report.md"]},
        ]
        if self.legacy:
            steps.append({"id": "legacy", "argv": ["bin/legacy-tool", "legacy.txt"], "inputs": [], "outputs": ["legacy.txt"]})
        return {"workflow": "t12-stage2", "steps": steps}

    def run(self, incremental: bool = True) -> dict:
        path = self.root / "workflow.json"
        path.write_text(json.dumps(self.workflow(), indent=1))
        argv = [sys.executable, "-B", str(RUNNER), str(path), "--work", str(self.work), "--created", "2026-11-13", "--status",
                "synthetic"] + (["--incremental"] if incremental else [])
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = runner().main(argv[3:])
        out = json.loads(buffer.getvalue())
        if code != 0 or out.get("status") != "ok":
            raise RuntimeError(f"the workflow did not run (exit {code}): {json.dumps(out)[-800:]}")
        return {s["id"]: bool(s.get("skipped", False)) for s in out["steps"]}


_RUNNER = []


def runner():
    """skills/hep-computing/scripts/run_workflow.py, loaded once, with the pinned release digest."""
    if not _RUNNER:
        spec = importlib.util.spec_from_file_location("run_workflow_t12_stage2", RUNNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.plugin_release = lambda root=None: dict(PINNED_RELEASE)
        _RUNNER.append(module)
    return _RUNNER[0]


# ================================================================ R9: source and output scope

def _inside(path: Path, roots) -> Path | None:
    try:
        real = path.resolve()
    except OSError:
        return None
    for root in roots:
        if real == root or root in real.parents:
            return root
    return None


def _inside_unresolved(path: Path, roots) -> bool:
    """Whether the path as written (symlinks not followed) lies under a live root: an interpreter run through a link in a live tree."""
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def scope_check(snapshot: Path, live, outputs=()) -> dict:
    """Offending paths of this process: sys.path entries, loaded modules' files, the working folder and outputs under a live root, and
    this file outside the snapshot. A Git path proves nothing here: only where files really are (resolved) counts."""
    roots = [Path(r).resolve() for r in live]
    offending = []
    for entry in sys.path:
        if entry and _inside(Path(entry), roots):
            offending.append({"kind": "sys.path", "path": str(Path(entry).resolve())})
    for name, module in sorted(sys.modules.items()):
        file = getattr(module, "__file__", None)
        if file and _inside(Path(file), roots):
            offending.append({"kind": "module", "module": name, "path": str(Path(file).resolve())})
        for location in list(getattr(module, "__path__", None) or []):   # a namespace package has no __file__ (M7)
            if isinstance(location, str) and _inside(Path(location), roots):
                offending.append({"kind": "package search location", "module": name, "path": str(Path(location).resolve())})
    invoked = Path(sys.executable).absolute()
    as_invoked = invoked.parent.resolve() / invoked.name        # the link itself, its folder resolved
    if _inside_unresolved(as_invoked, roots) or _inside(invoked, roots):   # the running interpreter, as invoked and resolved
        offending.append({"kind": "interpreter", "path": str(invoked)})
    if _inside(Path.cwd(), roots):
        offending.append({"kind": "working folder", "path": str(Path.cwd().resolve())})
    for out in outputs:
        if _inside(Path(out), roots):
            offending.append({"kind": "output", "path": str(Path(out).resolve())})
    if _inside(Path(__file__), [Path(snapshot).resolve()]) is None:
        offending.append({"kind": "harness outside the snapshot", "path": str(Path(__file__).resolve())})
    return {"offending": offending}


def _emit(status: str, **fields) -> int:
    print(json.dumps({"status": status, **fields}, sort_keys=True))
    return exit_code(status)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="operation", required=True)
    scope = sub.add_parser("scope-check", help="check this process's source and output scope against live roots")
    scope.add_argument("--snapshot", required=True, type=Path)
    scope.add_argument("--live", required=True, action="append", type=Path)
    scope.add_argument("--evidence-path", dest="evidence_paths", action="append", default=[], type=Path)
    scope.add_argument("--import", dest="imports", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        for name in args.imports:
            importlib.import_module(name)
        found = scope_check(args.snapshot, args.live, args.evidence_paths)
    except Exception as error:  # noqa: BLE001 - a crash is incomplete, never a verdict
        return _emit("incomplete", reason=f"{type(error).__name__}: {error}")
    if found["offending"]:
        return _emit("rejected", offending=found["offending"], live=[str(p) for p in args.live])
    return _emit("ok", snapshot=str(args.snapshot.resolve()), live=[str(p) for p in args.live])


if __name__ == "__main__":
    sys.exit(main())
