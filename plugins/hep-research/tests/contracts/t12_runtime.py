#!/usr/bin/env python3
"""T12 stage 7: A26-A36 at run time and A10 inside a T12 reprocessing (T12-20, T12-21; plan v9.2 Section 13, Section 8.3, R14, R20).

A harness for run-time cases on the backends this repository has, with synthetic fixtures and frozen files read by SHA-256 only. No
quality claim. Every rule and expectation is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 7"). It lives under
tests/ because it imports the contracts and adapters' recipe modules (tools/check_layering.py).

- SCENARIOS: A26-A36 with the plan's text, each `executed` on a named backend or a `gap` with its reason and the T11 families (R14,
  R20). No new backend is built and no scenario is narrowed: a gap keeps P4 execution incomplete.
- E28 (A28): per-channel exposure on the timing counts (adapters/timing-pid, timing_recipe/counts.py).
- E32 (A32): a changed configuration on calo-cluster (adapters/calo-cluster), and E32R (fix round 1, I1): a response built by
  skills/hep-detector/scripts/build_response.py from frozen-configuration products is not paired with another configuration's product
  (a harness-side check on the identity the harness writes into the response's provenance).
- E34 (A34): null modes on the destriper (adapters/destriper).
- A10: a T08 product described by a reconstruction-product/1 sidecar whose retention follows the files retained beside it; a
  recalibration's trace rerun is admitted only when contracts.reconstruction.can_recompute allows `raw` and `conditions_snapshot`. The
  planner is this harness's (plan_step), not the shared runner: run_workflow.py has no retention gate (OPEN_ITEMS).

Operation:
  run --out FILE
      runs E28, E32, E34 and A10's K1-K5 in a scratch folder and writes one JSON record (never over an existing file). Status and exit
      (core/status.py): ok 0, every expectation held (gaps included; P4 execution stays incomplete); failed 1, one did not; rejected 2,
      the output exists or its folder is missing; incomplete 3, a backend could not run or the record could not be written.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.interpreter_guard import child_flags  # noqa: E402
from core.status import exit_code  # noqa: E402

ADAPTERS = ROOT / "adapters"
CALO = ADAPTERS / "calo-cluster" / "assets"
DESTRIPER = ADAPTERS / "destriper" / "assets"
TIMING = ADAPTERS / "timing-pid" / "assets"
for _path in (CALO, CALO / "fixture_tools", DESTRIPER / "fixture_tools", TIMING):
    if str(_path) not in sys.path:
        sys.path.append(str(_path))

T08_CONFIGURATION = CALO / "t08-grid-1.configuration.json"
T08_CONFIGURATION_SHA256 = "5fbbea3b4ca81d962c5ca70fa024ddc82dd6e1d2f06e39b354fda56d26483723"   # Freeze B, T08 configuration
NOISELESS_TOLERANCE = DESTRIPER / "t10-replay-noiseless.tolerance.json"
NOISELESS_TOLERANCE_SHA256 = "12738ebce579ae83057b69d8dca56cd3a626d5c5afe323863a56275de16da698"   # frozen by the user, 2026-11-12
DESTRIPER_SEED = 20260
TIMEOUT = 300
BUILD_RESPONSE = ROOT / "skills" / "hep-detector" / "scripts" / "build_response.py"
OPEN_ITEMS = ["no runner-level retention gate", "build_response.py records no structured product or configuration identity"]
OPEN_ITEM_NOTES = {
    OPEN_ITEMS[0]: "A10's planner is the harness's (plan_step); skills/hep-computing/scripts/run_workflow.py does not consult retention "
                   "before a rerun",
    OPEN_ITEMS[1]: "E32R's pairing check reads the identity the harness writes into --provenance (extension.provenance), so the refusal "
                   "is the harness's, not the response tool's",
}

SCENARIOS = {
    "A26": {"scenario": "Inject signals before filtering to validate signal attenuation, correlations, and lost modes; post-filter closure "
                        "alone is insufficient",
            "run_time": "gap", "backend": None, "families": ["F35", "F38"],
            "reason": "no backend filters a signal: the destriper solves baselines and its method card says 'no filtering or transfer "
                      "function'; T11 F38 records signal injection before filtering as a gap; F35 (HAYSTAC) has binding none"},
    "A27": {"scenario": "Scan overlap / RF-IF / retarding coordinates: retain conditions, dwell, and merge weights for each setting to "
                        "avoid incorrect summation",
            "run_time": "gap", "backend": None, "families": ["F35", "F36"],
            "reason": "no scan-setting backend: F35 (RF/IF map per setting) and F36 (retarding potential) have binding none; RF and "
                      "retarding are T06 contract checks, not run time (t10-closeout.md, W7 row)"},
    "A28": {"scenario": "Different pixel/channel exposures, with readout generating signals: do not use an incorrect single run-level "
                        "exposure",
            "run_time": "executed", "backend": "adapters/timing-pid/assets/timing_recipe/counts.py", "families": ["W6 (T10)"],
            "reason": None},
    "A29": {"scenario": "Different angle bases / periods / axial-vs-vector conventions: transform correctly and retain instrument-response "
                        "dependence",
            "run_time": "gap", "backend": None, "families": ["F37"],
            "reason": "no polarimetry or angle-basis backend: F37 has binding none; the destriper timestream holds pixel and value only, "
                      "no polarization angle"},
    "A30": {"scenario": "First CRES track segment undetected: reconstructed energy and response must reflect this selection effect",
            "run_time": "gap", "backend": None, "families": ["F34"], "reason": "no CRES backend: F34 has binding none"},
    "A31": {"scenario": "Averaged/filtered spectra are not raw counts: do not assume independent Poisson bins; retain the noise model and "
                        "correlations",
            "run_time": "gap", "backend": None, "families": ["F35"],
            "reason": "no backend reads averaged or filtered spectra: F35 (HAYSTAC averaged spectra) has binding none"},
    "A32": {"scenario": "Cuts/cleaning/model/multiplicity change: downstream IRFs cannot be reused without checks",
            "run_time": "executed", "check_side": "harness", "backend": "adapters/calo-cluster/assets/calo_cluster.py",
            "families": ["F15", "F16 (T08)"], "reason": None,
            "guard": "E32: the T08 accounting tool holding the frozen configuration refuses the variant's product; E32R: a response built by "
                     "skills/hep-detector/scripts/build_response.py from frozen-configuration products is refused against the variant's "
                     "product by the harness's pairing check (build_response.py records no structured identity); stage 2's R4 (T12-25) "
                     "showed the response step rerunning on a changed configuration digest, on a synthetic DAG"},
    "A33": {"scenario": "Scintillation exists but is insufficient to measure energy in the specified domain: support only a veto or "
                        "partial quantities, without automatic promotion to a complete measurement",
            "run_time": "gap", "backend": None, "families": ["F10", "F11"],
            "reason": "no backend measures scintillation against an energy domain: F10 has binding none; F11 is bound to simreco "
                      "(adapters/geant4/assets/simreco/simreco.cc: TOF station times and beta on simulated element_sim events), "
                      "adjacent, not a cover: no light-yield, quenching or energy model and no energy-domain or veto-only statement; "
                      "the photon likelihood "
                      "(T09) fits one light model with no veto-only mode; the timing counts (per_event_energy false, A19) are counting, "
                      "not a scintillation veto: adjacent, not a cover"},
    "A34": {"scenario": "Null modes in global maps/fits: state unidentifiable components explicitly; do not fabricate information with "
                        "jitter or naive chunk averages",
            "run_time": "executed", "backend": "adapters/destriper/assets/destriper.py", "families": ["F38 (T10 replay, U7 B2)"],
            "reason": None},
    "A35": {"scenario": "Same frame name but different projection/focal-length definitions: off-axis controls detect the difference; "
                        "metadata names alone cannot yield pass",
            "run_time": "gap", "backend": None, "families": ["F28", "F30"],
            "reason": "no imaging backend: F28 and F30 have binding none"},
    "A36": {"scenario": "Signal injection into real data: retain the injection location / synthetic components and derived labels; do not "
                        "claim a purely observed result",
            "run_time": "gap", "backend": None, "families": ["F35"],
            "reason": "no backend injects into recorded data and none holds real data; the T08 product /3 carries an input label and "
                      "provenance (simulated-unvalidated), a simulation label, not an injection record: adjacent, not a cover"},
}


def p4_gaps() -> list:
    """Every scenario without run-time execution."""
    return sorted(s for s, e in SCENARIOS.items() if e["run_time"] == "gap")


def p4_execution() -> str:
    return "incomplete" if p4_gaps() else "complete"


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def frozen_bytes(path: Path, expected: str) -> bytes:
    """A frozen file, read by SHA-256: refused if its bytes are not the frozen ones."""
    content = path.read_bytes()
    if sha256_hex(content) != expected:
        raise ValueError(f"{path.name} is not the frozen file (SHA-256 {sha256_hex(content)}, expected {expected})")
    return content


def contract_codes(product: dict) -> list:
    """The T06 contract reader's error codes (an empty list: accepted)."""
    from contracts.reconstruction import read_sidecar
    return [finding.code for finding in read_sidecar(product).errors]


def _last_json(text: str) -> dict:
    for line in reversed(text.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {}


# ================================================================ E28: per-channel exposure (timing counts)

def counts_channels() -> list:
    """Stage plan E28: two channels with different read intervals and dead times."""
    return [
        {"channel": "ch-a", "threshold": {"value": 3.0, "unit": "mV"}, "response_ref": "response.ch-a",
         "intervals": [{"interval_id": "a1", "start_s": 0.0, "end_s": 10.0, "dead_s": 1.0, "read": True},
                       {"interval_id": "a2", "start_s": 10.0, "end_s": 20.0, "dead_s": 1.0, "read": True}],
         "pulses": [{"time_s": 1.0, "amplitude": 5.0}, {"time_s": 2.0, "amplitude": 1.0}, {"time_s": 12.0, "amplitude": 7.0}]},
        {"channel": "ch-b", "threshold": {"value": 3.0, "unit": "mV"}, "response_ref": "response.ch-b",
         "intervals": [{"interval_id": "b1", "start_s": 0.0, "end_s": 10.0, "dead_s": 0.5, "read": True},
                       {"interval_id": "b2", "start_s": 10.0, "end_s": 20.0, "dead_s": 0.0, "read": False}],
         "pulses": [{"time_s": 3.0, "amplitude": 4.0}]},
    ]


def counts_product(channels: list) -> tuple:
    from timing_recipe import counts
    return counts.build(channels, "product.t12s7.counts")


def counts_negative(product: dict, name: str) -> dict:
    """A copy of the count product with one stage plan negative (N28a-c)."""
    bad = copy.deepcopy(product)
    block = bad["counts"]
    span = block["run_time"]["value"]
    if name == "absent-as-zero":
        for interval in block["intervals"]:
            if interval["presence"] == "absent":
                interval["count"] = 0
        return bad
    for rate in block["rates"]:
        if name == "run-time-denominator":
            rate["denominator"] = {"source": "run-time", "value": span, "unit": "s"}
        elif name in ("run-span-as-exposure", "single-run-level-exposure"):
            rate["denominator"] = {"source": "valid-exposure", "value": span, "unit": "s"}
        else:
            raise KeyError(name)
    if name == "single-run-level-exposure":
        for channel in block["channels"]:
            channel["valid_exposure"] = {"value": span, "unit": "s"}
    return bad


def exposure_defects(channels: list, product: dict) -> list:
    """Channels whose stated valid exposure is not the sum over their read intervals of (end - start - dead), from the native input."""
    recomputed = {c["channel"]: math.fsum(i["end_s"] - i["start_s"] - i["dead_s"] for i in c["intervals"] if i["read"]) for c in channels}
    stated = {c["channel"]: c["valid_exposure"]["value"] for c in product["counts"]["channels"]}
    return sorted(name for name in recomputed if stated.get(name) != recomputed[name])


def unread_pulse_refusal() -> str | None:
    """N28d: a pulse inside a channel's unread interval; the recipe's refusal text, or None when it was accepted."""
    from timing_recipe.timing_payload import InputError
    channels = counts_channels()
    channels[1]["pulses"].append({"time_s": 15.0, "amplitude": 6.0})
    try:
        counts_product(channels)
    except InputError as error:
        return str(error)
    return None


def case_a28() -> dict:
    channels = counts_channels()
    product, readings = counts_product(channels)
    block = product["counts"]
    intervals = {i["interval_id"]: i for i in block["intervals"]}
    exposures = {c["channel"]: c["valid_exposure"]["value"] for c in block["channels"]}
    single = counts_negative(product, "single-run-level-exposure")
    items = {
        "accepted": contract_codes(product) == [],
        "exposures": exposures == {"ch-a": 18.0, "ch-b": 9.5},
        "run_time": block["run_time"]["value"] == 20.0,
        "counts": [intervals[k].get("count") for k in ("a1", "a2", "b1")] == [1, 1, 1],
        "unread_interval_absent": intervals["b2"]["presence"] == "absent" and "count" not in intervals["b2"],
        "rates_on_own_exposure": all(r["denominator"]["source"] == "valid-exposure" and r["denominator"]["value"] == exposures[r["channel"]]
                                     for r in block["rates"]),
        "N28a": sorted(set(contract_codes(counts_negative(product, "run-time-denominator")))) == ["reconstruction.counts.run_time_denominator"],
        "N28b": sorted(set(contract_codes(counts_negative(product, "run-span-as-exposure")))) == ["reconstruction.counts.exposure_mismatch"],
        "N28c": exposure_defects(channels, single) == ["ch-a", "ch-b"],
        "N28d": "lies in an interval that was not read" in (unread_pulse_refusal() or ""),
        "N28e": sorted(set(contract_codes(counts_negative(product, "absent-as-zero")))) == ["reconstruction.counts.absent_filled"],
        "recomputed_exposure_agrees": exposure_defects(channels, product) == [],
    }
    return {"items": items, "readings": {"valid_exposure_s": exposures, "rates": readings, "N28c_t06_codes": contract_codes(single)}}


# ================================================================ E32 and A10: the calo-cluster workspace

GRID, WIDTH = 40, 1.0
EVENTS = [[(2000.0, 12.3, 20.1)], [(2000.0, 18.4, 20.2), (1500.0, 21.9, 20.6)]]   # as tests/adapters/test_calo_scenarios.py
OTHER_EVENTS = [[(1800.0, 10.4, 9.7)], [(900.0, 30.2, 28.8)]]
RESPONSE_EVENTS = [[(600.0, 20.3, 19.8)], [(1400.0, 19.6, 20.4)], [(2200.0, 20.5, 20.5)], [(3000.0, 19.4, 19.6)]]   # fix round 1, E32R
RESPONSE_EDGES = ["0", "1000", "2000", "3000", "4000"]


def _phi(u: float) -> float:
    return 0.5 * (1.0 + math.erf(u / math.sqrt(2.0)))


def _axis(i: int, centre: float) -> float:
    return _phi((i + 1 - centre) / WIDTH) - _phi((i - centre) / WIDTH)


def _image(showers):
    import numpy
    return numpy.array([[sum(e * _axis(ix, x) * _axis(iy, y) for e, x, y in showers) for iy in range(GRID)] for ix in range(GRID)])


def product_header(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.loads(handle.readline())


def object_count(path: Path) -> int:
    from calo_recipe import product
    return sum(len(event["objects"]) for event in product.read_product(path).events)


class CaloSpace:
    """Hand-made readouts and payloads (stage plan E32), and the calo-cluster command lines on them."""

    def __init__(self, folder: Path, events=None):
        from calo_recipe import cell_input
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.cells = self._write("cells.cells", self._cells_bytes(events or EVENTS))
        ped = cell_input.payload_bytes("pedestal", "subtract", 0.0, GRID * GRID, "adc", "nominal", "hand-made T12 stage 7 constant")
        self.pedestal = self._write("pedestal.json", ped)
        self.gain = self._write("gain.json", cell_input.payload_bytes(
            "gain", "multiply", 1.0, GRID * GRID, "MeV/adc", "nominal", "hand-made T12 stage 7 constant", derived_against=[sha256_hex(ped)]))
        self.gain_new = self._write("gain-new.json", cell_input.payload_bytes(
            "gain", "multiply", 1.1, GRID * GRID, "MeV/adc", "measured", "hand-made T12 stage 7 recalibration (synthetic)",
            derived_against=[sha256_hex(ped)]))

    def _write(self, name: str, content: bytes) -> Path:
        path = self.folder / name
        path.write_bytes(content)
        return path

    @staticmethod
    def _cells_bytes(events) -> bytes:
        import numpy
        from calo_recipe import cell_input
        raw = numpy.stack([_image(showers) for showers in events])
        return cell_input.cells_bytes(raw, numpy.ones(raw.shape, bool), numpy.zeros(raw.shape, bool))

    def other_cells(self) -> Path:
        return self._write("other.cells", self._cells_bytes(OTHER_EVENTS))

    def variant_configuration(self, **changes) -> Path:
        """A whole configuration file: the frozen one's with the named constants changed and its source saying so (a copy)."""
        document = json.loads(frozen_bytes(T08_CONFIGURATION, T08_CONFIGURATION_SHA256))
        document.update(changes)
        document["source"] = "T12 stage 7 variant: " + ", ".join(f"{k} {v}" for k, v in sorted(changes.items()))
        name = "variant-" + "-".join(f"{k}-{v}" for k, v in sorted(changes.items())) + ".configuration.json"
        return self._write(name, (json.dumps(document, indent=1) + "\n").encode("utf-8"))

    def reconstruct(self, name: str, configuration: Path | None = None, gain: Path | None = None, cells: Path | None = None,
                    pedestal: Path | None = None, target: Path | None = None, product_id: str | None = None) -> tuple:
        out = Path(target) if target is not None else self.folder / f"{name}.product.jsonl"
        argv = [sys.executable, "-I", "-B", str(CALO / "calo_cluster.py"), "reconstruct", "--cells", str(cells or self.cells),
                "--pedestal-payload", str(pedestal or self.pedestal), "--gain-payload", str(gain or self.gain), "--product", str(out),
                "--product-id", product_id or name]
        if configuration is not None:
            argv += ["--configuration", str(configuration)]
        done = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT)
        if done.returncode not in (0, 1, 2):
            raise RuntimeError(f"calo_cluster.py could not run (exit {done.returncode}): {done.stderr[-400:]}")
        return done.returncode, out

    def accounting(self, product_path: Path, configuration: Path | None = None) -> tuple:
        argv = [sys.executable, "-I", "-B", str(CALO / "fixture_tools" / "t08_scenarios.py"), "accounting", "--cells", str(self.cells),
                "--pedestal-payload", str(self.pedestal), "--gain-payload", str(self.gain), "--product", str(product_path),
                "--label", "t12s7"]
        if configuration is not None:
            argv += ["--configuration", str(configuration)]
        done = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT)
        if done.returncode not in (0, 1, 2):
            raise RuntimeError(f"t08_scenarios.py could not run (exit {done.returncode}): {done.stderr[-400:]}")
        refused = [line for line in done.stdout.splitlines() if line.startswith("REFUSED ")]
        return done.returncode, {"stdout": done.stdout, "reason": refused[0] if refused else ""}

    def reprocess(self, product_path: Path, retained: dict, new_gain: Path, target: Path) -> dict:
        """A recalibration of a T08 product under new_gain; its step trace-rerun needs `raw` (stage plan, A10)."""
        sidecar = t08_sidecar(product_path, retained)
        decision = plan_step(sidecar, "trace-rerun", ["raw", "conditions_snapshot"])
        header = product_header(product_path)
        if decision["can_recompute"]:
            if header["configuration"]["sha256"] != T08_CONFIGURATION_SHA256 or not retained.get("pedestal"):
                raise RuntimeError("the rerun needs the product's own configuration and its pedestal payload")
            code, out = self.reconstruct("rerun", gain=new_gain, cells=retained["input"], pedestal=retained["pedestal"], target=target,
                                         product_id=header["product_id"])
            decision.update(outcome="ran" if code == 0 else f"rerun failed (exit {code})", product=str(out))
        else:
            decision["usable"] = usable_parameters(product_path)
        return decision


def usable_parameters(product_path: Path) -> dict:
    """The higher-level parameters a product keeps without its readout: objects, with the gain payload they were made with."""
    from calo_recipe import product
    read = product.read_product(product_path)
    keys = ("energy", "sigma_energy", "x", "y", "sigma_x", "sigma_y")
    objects = [dict({"event": event["event"], "object": item["object"]}, **{k: item[k] for k in keys})
               for event in read.events for item in event["objects"]]
    return {"gain_payload": read.header["chain"][1]["payload_id"], "recalibrated": False, "objects": objects}


WAVEFORM_LOSS = "pulse-shape or timing recalibration (no samples in calo-cells/1)"
RAW_REFUSAL = "refused: the readout is not retained, so a trace rerun is infeasible"
SNAPSHOT_REFUSAL = "refused: the conditions snapshot is not retained, so the chain cannot be rerun as it was"


def _retained_file(path, expected: str) -> bool:
    return path is not None and Path(path).is_file() and sha256_hex(Path(path).read_bytes()) == expected


def t08_sidecar(product_path: Path, retained: dict) -> dict:
    """reconstruction-product/1 describing a T08 product, with retention from its header and the files retained beside it."""
    from calo_recipe import product
    header = product.read_product(product_path).header
    chain = header["chain"]
    raw = "reproducible" if _retained_file(retained.get("input"), header["input"]["sha256"]) else "removed"
    snapshot = "reproducible" if (_retained_file(retained.get("pedestal"), chain[0]["payload_id"])
                                  and _retained_file(retained.get("gain"), chain[1]["payload_id"])) else "removed"
    used = [{"slot": step["step"], "tag": f"t08-chain-{step['step']}", "payload_id": step["payload_id"], "origin": step["origin"],
             "round": step["round"]} for step in chain]
    return {"schema": "reconstruction-product/1", "product_id": header["product_id"], "revision": 1, "collection": "calo-clusters",
            "native": {"type": "calo-cluster::Product", "schema_ref": header["format"]}, "presence": "present",
            "role": "reconstruction-input", "conditions_used": used, "required_extensions": [],
            "retention": {"raw": raw, "waveform": "removed", "truth": "not-applicable", "candidates": "kept", "conditions_snapshot": snapshot,
                          "lost_recalibrations": [header["retention"]["lost_recalibrations"], WAVEFORM_LOSS]}}


def plan_step(sidecar: dict, step: str, levels) -> dict:
    """Admit a reprocessing step only when every level it needs can still be reached (contracts.reconstruction.can_recompute). This
    planner is the harness's: the shared runner has no retention gate (OPEN_ITEMS)."""
    from contracts.reconstruction import can_recompute
    single = isinstance(levels, str)
    needed = [levels] if single else list(levels)
    states = {level: sidecar.get("retention", {}).get(level) for level in needed}
    missing = [level for level in needed if not can_recompute(sidecar, level)]
    if not missing:
        outcome = "admitted"
    elif missing[0] == "raw":
        outcome = RAW_REFUSAL
    elif missing[0] == "conditions_snapshot":
        outcome = SNAPSHOT_REFUSAL
    else:
        outcome = f"refused: {missing[0]} is {states[missing[0]]}, so this recomputation is infeasible"
    return {"step": step, "requires": levels if single else needed, "retention": states[needed[0]] if single else states,
            "can_recompute": not missing, "outcome": outcome}


def case_a32(folder: Path) -> dict:
    space = CaloSpace(folder)
    frozen_before = sha256_hex(T08_CONFIGURATION.read_bytes())
    code_f, frozen = space.reconstruct("frozen")
    variant_file = space.variant_configuration(cell_threshold_mev=1.2)
    code_v, variant = space.reconstruct("variant", configuration=variant_file)
    sha_f, sha_v = (product_header(p)["configuration"]["sha256"] for p in (frozen, variant))
    refused, out_refused = space.accounting(variant)
    own, _ = space.accounting(variant, configuration=variant_file)
    frozen_own, _ = space.accounting(frozen)
    response = response_case(Path(folder) / "response")
    items = {
        "products_written": (code_f, code_v) == (0, 0),
        "frozen_names_frozen_configuration": sha_f == T08_CONFIGURATION_SHA256,
        "variant_names_its_configuration": sha_v == sha256_hex(variant_file.read_bytes()),
        "identities_differ": sha_f != sha_v,
        "frozen_consumer_refuses_variant": refused == 2 and f"made with configuration {sha_v}, not the one given ({sha_f})" in out_refused["reason"],
        "variant_consumer_accepts_variant": own == 0,
        "frozen_consumer_accepts_frozen": frozen_own == 0,
        "frozen_file_unchanged": frozen_before == sha256_hex(T08_CONFIGURATION.read_bytes()) == T08_CONFIGURATION_SHA256,
    }
    items.update(response["items"])
    return {"items": items, "readings": dict({"configurations": {"frozen": sha_f, "variant": sha_v}, "refusal": out_refused["reason"]},
                                             **response["readings"])}


def matched_sample(product_path: Path, events) -> list:
    """E32R's matched sample: per event, truth the shower energy (one shower per event), reco the sum of the event's object energies,
    selected when the event has an object."""
    from calo_recipe import product
    rows = []
    for showers, event in zip(events, product.read_product(product_path).events):
        if len(showers) != 1:
            raise ValueError("a response event holds exactly one shower")
        energies = [item["energy"] for item in event["objects"]]
        rows.append({"truth": float(showers[0][0]), "reco": math.fsum(energies) if energies else "", "selected": int(bool(energies))})
    return rows


def build_response(space: "CaloSpace", product_path: Path, name: str, events, provenance: str | None = None) -> tuple:
    """build_response.py on the matched sample of a product; the provenance names the product and its configuration identity unless
    one is given. Returns (exit, artifact path, printed JSON)."""
    rows = matched_sample(product_path, events)
    sample = space.folder / f"{name}.matched.csv"
    sample.write_text("truth,reco,selected\n" + "".join(f"{r['truth']!r},{r['reco']!r},{r['selected']}\n" for r in rows), encoding="utf-8")
    header = product_header(product_path)
    if provenance is None:
        provenance = (f"T12 stage 7 matched sample from calo-cluster product sha256 {sha256_hex(Path(product_path).read_bytes())} "
                      f"configuration sha256 {header['configuration']['sha256']}")
    artifact = space.folder / f"{name}.response.json"
    # child_flags: -X utf8 on Windows, where the skill script's guard needs UTF-8 mode and -I ignores PYTHONUTF8
    argv = [sys.executable, "-I", *child_flags(), "-B", str(BUILD_RESPONSE), "build", str(sample), "--truth-col", "truth", "--reco-col", "reco",
            "--unweighted", "--selected-col", "selected", "--truth-edges", *RESPONSE_EDGES, "--reco-edges", *RESPONSE_EDGES,
            "--variable", "energy", "--unit", "MeV", "--normalization", "conditional_on_generated", "--acceptance", "inside_matrix",
            "--residual", "ratio", "--intended-use", "forward_folding", "--artifact-id", f"t12s7.response.{name}",
            "--objective", "T12 stage 7 E32R: a response from calo-cluster products (synthetic, no quality claim)",
            "--created", "2026-11-13", "--provenance", provenance, "--out", str(artifact)]
    done = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT)
    if done.returncode not in (0, 1, 2):
        raise RuntimeError(f"build_response.py could not run (exit {done.returncode}): {done.stderr[-400:]}")
    try:
        printed = json.loads(done.stdout)
    except ValueError:
        printed = _last_json(done.stdout)
    return done.returncode, artifact, printed


CONFIGURATION_IN_PROVENANCE = re.compile(r"configuration sha256 ([0-9a-f]{64})")


def response_pairing(artifact_path: Path, product_path: Path) -> dict:
    """The harness's pairing check: a response is used with a product only when the configuration identity its provenance names is the
    product's own; a response that names none, or more than one (carried minor, stage 7 re-review), is unbound and refused."""
    artifact = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
    found = CONFIGURATION_IN_PROVENANCE.findall(str(artifact.get("extension", {}).get("provenance", "")))
    product_configuration = product_header(product_path)["configuration"]["sha256"]
    if len(found) != 1:
        reason = ("unbound: the response names no configuration identity" if not found else
                  f"unbound: the response names {len(found)} configuration identities, not exactly one")
        return {"accepted": False, "reason": reason, "response_configuration": None, "product_configuration": product_configuration}
    accepted = found[0] == product_configuration
    reason = "" if accepted else (f"the response was built from products of configuration {found[0]}; this product was made with "
                                  f"configuration {product_configuration}: refused")
    return {"accepted": accepted, "reason": reason, "response_configuration": found[0], "product_configuration": product_configuration}


def response_case(folder: Path) -> dict:
    """E32R (fix round 1, I1): items R1-R4 and the variant's response as a reading."""
    space = CaloSpace(folder, events=RESPONSE_EVENTS)
    code_f, frozen = space.reconstruct("frozen")
    variant_file = space.variant_configuration(cell_threshold_mev=1.2)
    code_v, variant = space.reconstruct("variant", configuration=variant_file)
    if (code_f, code_v) != (0, 0):
        raise RuntimeError(f"the response products could not be made (exits {code_f}, {code_v})")
    code_r, artifact, printed = build_response(space, frozen, "frozen", RESPONSE_EVENTS)
    same = response_pairing(artifact, frozen) if artifact.is_file() else {"accepted": False}
    other = response_pairing(artifact, variant) if artifact.is_file() else {"accepted": True, "reason": ""}
    _, unbound_artifact, _ = build_response(space, frozen, "unbound", RESPONSE_EVENTS, provenance="a matched sample")
    unbound = response_pairing(unbound_artifact, frozen) if unbound_artifact.is_file() else {"accepted": True, "reason": ""}
    code_v_r, variant_artifact, _ = build_response(space, variant, "variant", RESPONSE_EVENTS)
    matrices = [json.loads(a.read_text(encoding="utf-8"))["extension"]["matrix"] if a.is_file() else None for a in (artifact, variant_artifact)]
    sha_f, sha_v = T08_CONFIGURATION_SHA256, sha256_hex(variant_file.read_bytes())
    items = {
        "R1": code_r == 0 and artifact.is_file() and printed.get("validation", {}).get("contracts_validate") == "ok",
        "R2": same["accepted"] is True,
        "R3": other["accepted"] is False and sha_f in other["reason"] and sha_v in other["reason"],
        "R4": unbound["accepted"] is False and "unbound" in unbound["reason"],
    }
    readings = {"response_matrix_frozen": matrices[0], "response_matrix_variant": matrices[1], "variant_response_exit": code_v_r,
                "variant_matrix_differs": matrices[0] != matrices[1], "matched_sample_frozen": matched_sample(frozen, RESPONSE_EVENTS),
                "matched_sample_variant": matched_sample(variant, RESPONSE_EVENTS)}
    return {"items": items, "readings": readings}


def case_a10(folder: Path) -> dict:
    from contracts.reconstruction import can_recompute, read_sidecar
    folder = Path(folder)
    space = CaloSpace(folder)
    code, p0 = space.reconstruct("p0")
    if code != 0:
        raise RuntimeError(f"the T08 product could not be made (exit {code})")
    p0_bytes = p0.read_bytes()
    full = {"input": space.cells, "pedestal": space.pedestal, "gain": space.gain}
    k1 = space.reprocess(p0, full, space.gain_new, folder / "k1.product.jsonl")
    k1_bytes = space.reprocess(p0, full, space.gain, folder / "k1-again.product.jsonl")
    target = folder / "k2.product.jsonl"
    k2 = space.reprocess(p0, dict(full, input=None), space.gain_new, target)
    other_target = folder / "k3.product.jsonl"
    k3 = space.reprocess(p0, dict(full, input=space.other_cells()), space.gain_new, other_target)
    k4 = plan_step(t08_sidecar(p0, full), "pulse-shape-refit", "waveform")
    k6_target = folder / "k6.product.jsonl"
    k6 = space.reprocess(p0, dict(full, pedestal=None), space.gain_new, k6_target)
    reduced = t08_sidecar(p0, dict(full, input=None))
    unstated = copy.deepcopy(reduced)
    del unstated["retention"]["lost_recalibrations"]
    usable = k2.get("usable", {})
    items = {
        "K1": (k1["can_recompute"] and k1["outcome"] == "ran"
               and product_header(folder / "k1.product.jsonl")["chain"][1]["payload_id"] == sha256_hex(space.gain_new.read_bytes())
               and p0.read_bytes() == p0_bytes),
        "K1-bytes": k1_bytes["outcome"] == "ran" and (folder / "k1-again.product.jsonl").read_bytes() == p0_bytes,
        "K2": (not k2["can_recompute"] and k2["outcome"] == RAW_REFUSAL and not target.exists() and p0.read_bytes() == p0_bytes
               and not can_recompute(reduced, "raw")),
        "K2-usable": (usable.get("gain_payload") == sha256_hex(space.gain.read_bytes()) and usable.get("recalibrated") is False
                      and len(usable.get("objects", [])) == object_count(p0) > 0),
        "K3": not k3["can_recompute"] and k3["retention"]["raw"] == "removed" and not other_target.exists(),
        "K6": (not k6["can_recompute"] and k6["outcome"] == SNAPSHOT_REFUSAL
               and k6["retention"] == {"raw": "reproducible", "conditions_snapshot": "removed"} and not k6_target.exists()),
        "K4": not k4["can_recompute"] and k4["outcome"].startswith("refused"),
        "K5": (read_sidecar(reduced).errors == [] and read_sidecar(t08_sidecar(p0, full)).errors == []
               and "reconstruction.retention.loss_unstated" in [f.code for f in read_sidecar(unstated).errors]),
    }
    readings = {"decisions": {"K1": {k: v for k, v in k1.items() if k != "product"}, "K2": {k: v for k, v in k2.items() if k != "usable"},
                              "K3": {k: v for k, v in k3.items() if k != "usable"}, "K4": k4,
                              "K6": {k: v for k, v in k6.items() if k != "usable"}},
                "objects_usable": len(usable.get("objects", [])), "retention_reduced": reduced["retention"]}
    return {"items": items, "readings": readings}


# ================================================================ E34: null modes (destriper)

def noiseless_tolerance() -> dict:
    return json.loads(frozen_bytes(NOISELESS_TOLERANCE, NOISELESS_TOLERANCE_SHA256))


def destripe(folder: Path, variant: str, constraint: str) -> dict:
    """Write the fixture's timestream (seed DESTRIPER_SEED), run destriper.py solve and, when written, check-product."""
    import t10_fixture
    work = Path(folder) / f"{variant}-{constraint}"
    timestream, truth = t10_fixture.write(variant, DESTRIPER_SEED, work)
    target = work / "product.json"
    argv = [sys.executable, "-I", "-B", str(DESTRIPER / "destriper.py"), "solve", "--timestream", str(timestream), "--product", str(target),
            "--product-id", f"product.t12s7.{variant}.{constraint}", "--constraint", constraint, "--stopping", "1e-13"]
    solved = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT)
    if solved.returncode not in (0, 1):
        raise RuntimeError(f"destriper.py solve could not run (exit {solved.returncode}): {solved.stdout[-300:]} {solved.stderr[-300:]}")
    run = {"solve_exit": solved.returncode, "solve": _last_json(solved.stdout), "check_exit": None, "check": None, "product": None,
           "truth": json.loads(truth.read_text(encoding="utf-8"))}
    if target.is_file():
        checked = subprocess.run([sys.executable, "-I", "-B", str(DESTRIPER / "destriper.py"), "check-product", "--product", str(target)],
                                 capture_output=True, text=True, timeout=TIMEOUT)
        run.update(check_exit=checked.returncode, check=_last_json(checked.stdout), product=json.loads(target.read_text(encoding="utf-8")))
    return run


def scan_negative(embedded: dict, name: str) -> dict:
    import t10_fixture
    return t10_fixture.negative_variant(embedded, name)


def _norm(values) -> float:
    return math.sqrt(math.fsum(v * v for v in values))


def a34_runs(folder: Path) -> tuple:
    """E34's three solver runs: noiseless with the zero-sum constraint, noiseless without one, disconnected. Each check-product runs
    the T06 reader on the scan block, which is slow (tens of seconds), so the runs are made once and shared."""
    return (destripe(folder, "noiseless", "zero-sum"), destripe(folder, "noiseless", "none"),
            destripe(folder, "disconnected", "zero-sum"))


def case_a34(folder: Path, runs: tuple | None = None) -> dict:
    tolerance = noiseless_tolerance()
    zero, free, split = runs if runs is not None else a34_runs(folder)
    readings, items = {}, {}
    items["zero_sum_written_and_checked"] = (zero["solve_exit"], zero["check_exit"]) == (0, 0)
    if zero["product"] is not None:
        scan = zero["product"]["reconstruction_product"]["scan"]
        truth = zero["truth"]
        norm = _norm(truth["baselines"])
        readings["baselines_relative"] = _norm([a - b for a, b in zip(zero["product"]["baselines"], truth["baselines"])]) / norm
        readings["map_relative"] = _norm([a - b for a, b in zip(zero["product"]["map"], truth["map"])]) / norm
        items["zero_sum_constraint_named"] = scan["constraint"] is not None and "zero-sum" in scan["constraint"]["statement"]
        items["zero_sum_within_frozen_tolerance"] = (readings["baselines_relative"] <= tolerance["tau_baselines"]
                                                     and readings["map_relative"] <= tolerance["tau_map"])
        embedded = zero["product"]["reconstruction_product"]
        for name, code in (("jitter", "reconstruction.scan.jitter_precision"), ("chunk-average", "reconstruction.scan.chunk_average"),
                           ("unique-without-constraint", "reconstruction.scan.unique_claim")):
            codes = sorted(set(contract_codes(scan_negative(embedded, name))))   # amendment 1: T10's rule, its code among the codes
            readings.setdefault("negative_codes", {})[name] = codes
            items[f"negative_{name}"] = code in codes
    items["none_written_and_checked"] = (free["solve_exit"], free["check_exit"]) == (0, 0)
    if free["product"] is not None:
        scan = free["product"]["reconstruction_product"]["scan"]
        items["none_every_parameter_unidentifiable"] = len(scan["unidentifiable"]) == 48 == len(scan["model"]["parameters"])
        items["none_no_single_parameter_reported"] = not any(sorted(abs(w) for w in item["weights"])[-2:] == [0, 1] for item in scan["reported"])
        items["none_no_constraint_no_uniqueness"] = scan["constraint"] is None and scan["uniqueness_claim"] is False
    items["disconnected_refused"] = (split["solve_exit"] == 1 and split["solve"].get("status") == "refused"
                                     and len(split["solve"].get("components") or []) == 2 and split["product"] is None)
    readings["tolerance"] = {"tau_baselines": tolerance["tau_baselines"], "tau_map": tolerance["tau_map"]}
    return {"items": items, "readings": readings}


# ================================================================ the record

def run_all(folder: Path) -> dict:
    folder = Path(folder)
    cases = {"A28": case_a28(), "A32": case_a32(folder / "a32"), "A34": case_a34(folder / "a34")}
    a10 = case_a10(folder / "a10")
    scenarios = {}
    for name, entry in sorted(SCENARIOS.items()):
        scenarios[name] = dict(entry, **cases.get(name, {}))
    return {"format": "t12-runtime-record/1", "stage": 7, "obligations": ["T12-20", "T12-21"], "scenarios": scenarios, "a10": a10,
            "p4_execution": p4_execution(), "gaps": p4_gaps(), "open_items": list(OPEN_ITEMS), "open_item_notes": dict(OPEN_ITEM_NOTES), "synthetic": True, "quality_claim": None,
            "note": "exit 0 means every expectation held, gaps included; P4 execution stays incomplete while a gap exists"}


def failed_items(record: dict) -> list:
    failed = [f"{s}.{k}" for s, e in sorted(record["scenarios"].items()) for k, v in sorted(e.get("items", {}).items()) if not v]
    failed += [f"A10.{k}" for k, v in sorted(record["a10"]["items"].items()) if not v]
    for name, entry in sorted(record["scenarios"].items()):
        if entry["run_time"] == "executed" and not entry.get("items"):
            failed.append(f"{name}: executed without items")
    return failed


def _emit(status: str, **fields) -> int:
    print(json.dumps({"status": status, **fields}, sort_keys=True))
    return exit_code(status)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="operation", required=True)
    run = sub.add_parser("run", help="run the executed cases and A10, and write the record")
    run.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.out.exists():
        return _emit("rejected", reason=f"{args.out} exists: a record is never overwritten")
    if not args.out.parent.is_dir():
        return _emit("rejected", reason=f"{args.out.parent} is not a folder")
    try:
        with tempfile.TemporaryDirectory(prefix="t12s7-") as scratch:
            record = run_all(Path(scratch))
    except Exception as error:  # noqa: BLE001 - a backend that cannot run is incomplete, never a verdict
        return _emit("incomplete", reason=f"{type(error).__name__}: {error}")
    failed = failed_items(record)
    record["status"] = "failed" if failed else "ok"
    record["failed_items"] = failed
    partial = args.out.with_name(args.out.name + ".partial")
    try:
        partial.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(partial, args.out)
    except OSError as error:
        partial.unlink(missing_ok=True)
        return _emit("incomplete", reason=f"the record cannot be written: {error.strerror}")
    return _emit(record["status"], out=str(args.out), failed_items=failed, p4_execution=record["p4_execution"], gaps=record["gaps"])


if __name__ == "__main__":
    sys.exit(main())
