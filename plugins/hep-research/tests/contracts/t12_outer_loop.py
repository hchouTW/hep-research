#!/usr/bin/env python3
"""T12 stage 1: the synthetic two-round outer loop of plan R37 (CAI-T12-1, CAI-T12-2; R36, Section 9.7, G06).

A harness for interface tests, with synthetic fixtures only. It derives no constant from data (R31): the "derivation" below is a
placeholder update on generated ADC values, and the convergence and unconstrained-mode checks are placeholders with no quality meaning.
They never satisfy A37. Every rule, tolerance and expectation is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 1").

It uses the existing interfaces only: the R32 sidecars and contracts/conditions.py (payload identity, check_used, reuse_decision), and
the control layer's derivation for the loop (families, the final round's checks, the labels iteration_internal and
superseded_by_iteration, publish). The control rules are not qualified (G07, mode M1); agreement shows that the interface behaves as
those rules say, nothing more. It lives under tests/ because it imports both the contracts and a skill's scripts (tools/check_layering.py).

The loop (family t12-synthetic-gain, final round 2):
  nominal-gain -> reco-r1 -> derive-r1 -> reco-r2 -> derive-r2 (final step: convergence and unconstrained-mode checks) -> reco-final
nominal-gain and reco-final are outside the loop; reco-final runs only when the final step is ok, and is checked by the record check.

Operation:
  run --variant converging|non-converging [--plant wrong-round|reuse-across-payloads|outside-consumes-round-1|skip-final-checks] --out FILE
      writes the t12-outer-loop/1 record. Status and exit (core/status.py): ok 0, every expectation of the variant holds (for
      non-converging, the hold is the expected result); failed 1, one does not (a planted defect is detected); rejected 2, bad input
      (unknown variant or plant, an output that exists: a record is never overwritten, a missing output folder); incomplete 3, the
      harness could not run or the record could not be written.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-computing" / "scripts"))
from contracts.conditions import check_used, reuse_decision  # noqa: E402
from contracts.recipe_semantics import canonical_sha256  # noqa: E402
from core.status import exit_code  # noqa: E402
from control_layer_support import derivation as dv  # noqa: E402
from control_layer_support import task_record  # noqa: E402
from tests.contracts.reconstruction_fixtures import calibration_payload, product as product_document, used_payload  # noqa: E402

SCHEMA = "t12-outer-loop/1"
CHANNELS = 8
HITS = 4
E_REF = 1.0                                   # the synthetic reference energy (arbitrary unit)
SPREAD = {"converging": 0.02, "non-converging": 0.20}
TAU = 0.01                                    # the placeholder convergence criterion
FINAL_ROUND = 2
FAMILY = "t12-synthetic-gain"
TAG = "t12_synthetic_gain"
CONSTRAINT = "constraint.synthetic-reference-energy"
MODE = "mode.global-gain-scale"
PLANTS = ("wrong-round", "reuse-across-payloads", "outside-consumes-round-1", "skip-final-checks", "mode-unconstrained")
ALL_STEPS = ("nominal-gain", "reco-r1", "derive-r1", "reco-r2", "derive-r2", "reco-final")
RECO_STEPS = ("reco-r1", "reco-r2", "reco-final")
PAYLOAD_STEPS = ("nominal-gain", "derive-r1", "derive-r2")
ROUNDS = {"nominal-gain": None, "derive-r1": 1, "derive-r2": 2}
DELIVERABLES = {"final-gain": "derive-r2", "final-product": "reco-final"}
LABELS = {"nominal-gain": "ok", "reco-r1": "superseded_by_iteration", "derive-r1": "superseded_by_iteration",
          "reco-r2": "iteration_internal", "derive-r2": "ok", "reco-final": "ok"}
CLAIMS = {"label": "synthetic", "quality": "none", "a37": "not satisfied by this fixture",
          "control_rules": "not qualified (G07, mode M1)"}
NOT_MET = "deliverable not met"


# ================================================================ the two placeholder checks and the record check (fixed by digest)

def convergence_check(final_gains, previous_gains, tau):
    metric = max(abs(round_gain / previous_gain - 1.0) for round_gain, previous_gain in zip(final_gains, previous_gains, strict=True))
    return ("pass" if metric <= tau else "fail"), metric


def unconstrained_mode_check(payload):
    held = (payload["unconstrained_modes"] == [MODE] and payload["constraints_used"] == [CONSTRAINT]
            and not set(payload["independent_validation"]) & set(payload["constraints_used"]))
    return "pass" if held else "fail"


def record_check(product, final_payload, final_round):
    codes = [finding.code for finding in check_used(product, [final_payload]).errors]
    rounds = [entry["round"] for entry in product["conditions_used"]]
    return ("pass" if not codes and rounds == [final_round] else "fail"), codes


CRITERIA = {"convergence": {"tau": TAU}, "mode": {"unconstrained_modes": [MODE], "constraints_used": [CONSTRAINT]},
            "record": {"round": FINAL_ROUND}}
CHECKS = {"convergence": convergence_check, "mode": unconstrained_mode_check, "record": record_check}


def check_digests() -> dict:
    """(check digest, criterion digest): the SHA-256 of the check function's source and of its criterion."""
    return {name: (canonical_sha256({"source": inspect.getsource(function)}), canonical_sha256(CRITERIA[name]))
            for name, function in CHECKS.items()}


# ================================================================ the fixture contract

def contract_spec(plant=None) -> dict:
    digests = check_digests()
    step = dv.StepSpec
    outside_upstream = ("derive-r1",) if plant == "outside-consumes-round-1" else ("derive-r2",)
    steps = {
        "nominal-gain": step(program="t12.nominal-gain/1"),
        "reco-r1": step(program="t12.reconstruct/1", upstream=("nominal-gain",), family=FAMILY, round=1),
        "derive-r1": step(program="t12.derive-gain/1", upstream=("reco-r1",), family=FAMILY, round=1),
        "reco-r2": step(program="t12.reconstruct/1", upstream=("derive-r1",), family=FAMILY, round=2),
        "derive-r2": step(program="t12.derive-gain/1", upstream=("reco-r2", "derive-r1"), family=FAMILY, round=2, checked=True,
                          required=frozenset({digests["convergence"], digests["mode"]}),
                          check_inputs=frozenset({(digests["convergence"][0], "derive-r1")})),
        "reco-final": step(program="t12.reconstruct/1", upstream=outside_upstream, checked=True,
                           required=frozenset({digests["record"]}), check_inputs=frozenset({(digests["record"][0], "derive-r2")})),
    }
    return {"steps": steps,
            "deliverables": {did: dv.Deliverable(step=name, target="T2") for did, name in DELIVERABLES.items()},
            "families": {FAMILY: dv.Family(final_round=FINAL_ROUND, convergence_check=digests["convergence"][0],
                                           mode_check=digests["mode"][0])},
            "samples": {}, "budget": None}


# ================================================================ the synthetic recipe and derivation

def generated_gains(variant) -> list:
    spread = SPREAD[variant]
    return [1.0 + spread * (c - 3.5) / 3.5 for c in range(CHANNELS)]


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def native_bytes(kind: str, rows) -> bytes:
    """The native content a sidecar points to by digest: one line per channel, numbers by repr (exact round trip)."""
    return (f"t12-{kind}/1\n" + "".join(f"{c} {' '.join(repr(v) for v in row)}\n" for c, row in enumerate(rows))).encode()


def payload_sidecar(gains: list, rnd, previous_id=None, producer_identity=None, modes=(MODE,)) -> dict:
    """A round payload names the previous round's payload in derived_against.upstream_payloads and derived_from, and its producing
    step's computational identity as producer.step_id (fix round 1, I5)."""
    fields = {"tag": TAG, "parametrization": {"name": "t12-per-channel-gain", "version": "1"},
              "content_sha256": sha256_hex(native_bytes("gain", [[g] for g in gains]))}
    if rnd is None:
        fields.update(producer={"kind": "external", "source": "synthetic nominal: unit gain"}, origin="nominal")
    else:
        fields.update(producer={"kind": "step", "step_id": producer_identity}, origin="measured", loop={"family": FAMILY, "round": rnd},
                      constraints_used=[CONSTRAINT], unconstrained_modes=list(modes),
                      derived_against={"upstream_payloads": [previous_id]}, derived_from=previous_id)
    return calibration_payload(**fields)


class Loop:
    """One run of the fixture contract on a fresh in-memory fact log."""

    def __init__(self, variant: str, plant=None):
        self.variant, self.plant = variant, plant
        self.spec = contract_spec(plant)
        self.log = dv.Log()
        self.log.append("session", "C", mode="M1")
        self.log.append("contract", "agent", spec=self.spec)
        self.adc = [[g * E_REF] * HITS for g in generated_gains(variant)]
        self.store = {}            # artifact digest -> {"doc", "values", "step"}
        self.outputs, self.consumed, self.computed, self.identity, self.order = {}, {}, {}, {}, []
        self.attempts = {}
        self.cache, self.checks, self.published, self.refused = [], {}, {}, {}
        self.admission_refused = None

    # ---------------------------------------------------------------- control-layer plumbing
    def attempt(self, name: str) -> str:
        self.attempts[name] = self.attempts.get(name, 0) + 1
        return f"{name}:{self.attempts[name]}"

    def payload_by_id(self, payload_id: str):
        for entry in self.store.values():
            if entry["doc"].get("schema") == "conditions-payload/1" and entry["doc"]["payload_id"] == payload_id:
                return entry
        raise KeyError(payload_id)

    def run_step(self, step: str) -> str:
        """A reconstruction step first asks the cache; a hit is acted on only through dv.admit(reuse_source=...), and a refused
        reuse falls back to a computation (fix round 1, I2)."""
        if step in RECO_STEPS:
            upstream = self.spec["steps"][step].upstream[0]
            current = dv.provisional_input(self.log, upstream)
            for decision in self.cache_lookup(step, self.store[current]["doc"]):
                attempt = self.attempt(step)
                try:
                    intent = dv.admit(self.log, self.log.head, attempt, step, cost=0.0, reuse_source=decision["source"])
                except dv.Admission as refusal:
                    decision["acted"] = str(refusal)
                    continue
                decision["acted"] = "reused"
                self.outputs[step], self.consumed[step] = decision["source"], dict(intent.get("inputs"))
                self.identity[step] = intent.get("identity")
                return decision["source"]
        attempt = self.attempt(step)
        intent = dv.admit(self.log, self.log.head, attempt, step, cost=0.0)
        consumed = dict(intent.get("inputs"))
        doc, values = self.produce(step, consumed, intent.get("identity"))
        digest = dv.digest_of(doc)
        self.store.setdefault(digest, {"doc": doc, "values": values, "step": step})
        self.log.append("receipt", "adapter", attempt=attempt, end="success", termination="confirmed", outputs=(digest,))
        self.outputs[step], self.consumed[step], self.identity[step] = digest, consumed, intent.get("identity")
        self.computed[step] = self.computed.get(step, 0) + 1
        self.order.append(step)
        return digest

    def run_check(self, name: str, target: str):
        chk, crit = check_digests()[name]
        attempt = self.attempt(f"check-{name}")
        intent = dv.admit(self.log, self.log.head, attempt, "__check__", cost=0.0, check=(chk, crit, target))
        inputs = dict(intent.get("inputs"))
        entry = self.store[target]
        if name == "convergence":
            result, metric = convergence_check(entry["values"], self.store[inputs["input:derive-r1"]]["values"], TAU)
            outcome = {"result": result, "metric": metric}
        elif name == "mode":
            outcome = {"result": unconstrained_mode_check(entry["doc"])}
        else:
            result, codes = record_check(entry["doc"], self.store[inputs["input:derive-r2"]]["doc"], FINAL_ROUND)
            outcome = {"result": result, "errors": codes}
        self.log.append_batch([
            ("receipt", "adapter", dict(attempt=attempt, end="success", termination="confirmed", outputs=())),
            ("check_result", "adapter", dict(target=target, check=chk, criteria=crit, check_attempt=attempt,
                                             result=outcome["result"]))])
        return outcome

    # ---------------------------------------------------------------- the synthetic steps
    def produce(self, step: str, consumed: dict, identity: str):
        if step == "nominal-gain":
            gains = [1.0] * CHANNELS
            return payload_sidecar(gains, None), gains
        if step.startswith("reco-"):
            payload = self.store[consumed[self.spec["steps"][step].upstream[0]]]
            energies = [[adc / g for adc in row] for row, g in zip(self.adc, payload["values"], strict=True)]
            means = [sum(row) / len(row) for row in energies]
            record = used_payload(payload["doc"])
            if self.plant == "wrong-round" and step == "reco-r2":
                record["round"] = 2
            doc = product_document(product_id=f"product.t12.{step}", conditions_used=[record],
                                   native={"type": "synthetic::T12ChannelEnergies",
                                           "location": "sha256:" + sha256_hex(native_bytes("energy", energies))})
            return doc, means
        product = self.store[consumed[self.spec["steps"][step].upstream[0]]]
        applied = self.payload_by_id(product["doc"]["conditions_used"][0]["payload_id"])
        gains = [g + (mean - E_REF) * g / 2.0 for g, mean in zip(applied["values"], product["values"], strict=True)]
        modes = () if self.plant == "mode-unconstrained" and step == "derive-r2" else (MODE,)
        return payload_sidecar(gains, ROUNDS[step], applied["doc"]["payload_id"], identity, modes), gains

    def cache_lookup(self, step: str, payload: dict) -> list:
        """Section 9.8: ask reuse_decision of every cached product of the same recipe (every reconstruction step runs t12.reconstruct/1 on
        the same hits), with the payload resolved afresh. Every decision is recorded; the hits are returned, in order, for the caller to
        act on through admission. Plant reuse-across-payloads keys the lookup on the tag instead of the identity (the defect P2)."""
        hits = []
        for other in RECO_STEPS:
            if other not in self.outputs:
                continue
            cached = self.store[self.outputs[other]]["doc"]
            if self.plant == "reuse-across-payloads":
                same = all(record["tag"] == payload["tag"] for record in cached["conditions_used"])
                decision = {"reuse": same, "changed": [] if same else ["gain"]}
            else:
                decision = reuse_decision(cached, {"gain": payload})
            entry = {"for": step, "cached": other, "reuse": decision["reuse"], "changed": decision["changed"], "acted": None,
                     "source": self.outputs[other]}
            self.cache.append(entry)
            if entry["reuse"]:
                hits.append(entry)
        return hits

    # ---------------------------------------------------------------- the run
    def loop_and_release(self) -> None:
        for step in ("nominal-gain", "reco-r1", "derive-r1", "reco-r2"):
            self.run_step(step)
        final_artifact = self.run_step("derive-r2")
        if self.plant != "skip-final-checks":
            self.checks["convergence"] = self.run_check("convergence", final_artifact)
            self.checks["mode"] = self.run_check("mode", final_artifact)
        if dv.label(self.log, final_artifact) == "ok" or self.plant == "skip-final-checks":
            outside = self.run_step("reco-final")
            if self.plant != "skip-final-checks":
                self.checks["record"] = self.run_check("record", outside)

    def execute(self) -> dict:
        try:
            self.loop_and_release()
        except dv.Admission as refusal:  # the control layer refused a step: the loop stops there, and the record says so
            self.admission_refused = str(refusal)
        for did in DELIVERABLES:
            try:
                fact = dv.publish(self.log, self.log.head, did)
                self.published[did] = fact.get("digest")
            except dv.Admission as refusal:
                self.refused[did] = str(refusal)
        return self.record()

    def probes(self) -> dict:
        """Probes on copies of the log, so the record's own history is untouched."""
        found = {}
        if "reco-final" in self.outputs:
            clone = copy.deepcopy(self)
            before = len(clone.cache)
            try:
                clone.run_step("reco-final")
                outcome = None
            except dv.Admission as refusal:
                outcome = str(refusal)
            own = [d for d in clone.cache[before:] if d["cached"] == "reco-final"]
            reused = [f for f in clone.log.of("reuse")]
            found["reuse_control"] = {"decision": own[0] if own else {"reuse": False, "acted": None},
                                      "source": reused[-1].get("source") if reused else None,
                                      "state": dv.exec_status(clone.log, reused[-1].get("attempt")) if reused else (outcome or "not reused")}
        clone = copy.deepcopy(self)
        try:
            dv.admit(clone.log, clone.log.head, clone.attempt("reco-r2"), "reco-r2", cost=0.0, reuse_source=self.outputs["reco-r1"])
            found["reuse_across_steps"] = "admitted"
        except dv.Admission as refusal:
            found["reuse_across_steps"] = str(refusal)
        final_artifact = self.outputs.get("derive-r2")
        if final_artifact is not None and dv.label(self.log, final_artifact) == "held":
            clone = copy.deepcopy(self)
            chk, crit = check_digests()["convergence"]
            attempt = clone.attempt("check-convergence")
            dv.admit(clone.log, clone.log.head, attempt, "__check__", cost=0.0, check=(chk, crit, final_artifact))
            clone.log.append_batch([
                ("receipt", "adapter", dict(attempt=attempt, end="success", termination="confirmed", outputs=())),
                ("check_result", "adapter", dict(target=final_artifact, check=chk, criteria=crit, check_attempt=attempt, result="pass"))])
            found["rewrite_probe"] = {"label": dv.label(clone.log, final_artifact)}
            clone = copy.deepcopy(self)
            outside = clone.run_step("reco-final")
            try:
                dv.publish(clone.log, clone.log.head, "final-product")
                refusal = "published"
            except dv.Admission as error:
                refusal = str(error)
            found["forced_outside"] = {"label": dv.label(clone.log, outside), "publish": refusal}
        return found

    def record(self) -> dict:
        steps = {step: {"artifact": digest, "label": dv.label(self.log, digest), "consumed": self.consumed[step],
                        "computed": self.computed.get(step, 0), "identity": self.identity[step]}
                 for step, digest in self.outputs.items()}
        payloads = {}
        for step in PAYLOAD_STEPS:
            if step in self.outputs:
                entry = self.store[self.outputs[step]]
                payloads[step] = {"payload_id": entry["doc"]["payload_id"], "tag": entry["doc"]["tag"],
                                  "round": entry["doc"].get("loop", {}).get("round"), "gains": entry["values"],
                                  "document": entry["doc"]}
        products = {}
        for step in RECO_STEPS:
            if step in self.outputs:
                entry = self.store[self.outputs[step]]
                consumed_payload = self.store[self.consumed[step][self.spec["steps"][step].upstream[0]]]["doc"]
                products[step] = {"conditions_used": entry["doc"]["conditions_used"], "channel_means": entry["values"],
                                  "check_used_errors": [f.code for f in check_used(entry["doc"], [consumed_payload]).errors]}
        failures = [[name, digest, check, result] for name, digest, check, _, result in dv.prior_failures(self.log, "derive-r2")]
        return {"schema": SCHEMA, "variant": self.variant, "plant": self.plant, "claims": dict(CLAIMS),
                "contract_sha256": dv.digest_of(task_record.encode_contract(self.spec)), "derivation": dv.DERIVATION_VERSION,
                "facts": self.log.head, "order": self.order, "steps": steps, "payloads": payloads, "products": products, "cache": self.cache,
                "checks": self.checks, "published": self.published, "publish_refused": self.refused,
                "admission_refused": self.admission_refused,
                "history": {"prior_failures": failures}, **self.probes()}


def run(variant: str, plant=None) -> dict:
    if variant not in SPREAD or (plant is not None and plant not in PLANTS):
        raise ValueError(f"unknown variant {variant!r} or plant {plant!r}")
    return Loop(variant, plant).execute()


# ================================================================ the assessment (t12-stage-plan.md, L1-L8 and H1-H5)

def _products_hold(rec, expected) -> bool:
    for product, (payload_step, rnd) in expected.items():
        used = rec["products"][product]["conditions_used"]
        if len(used) != 1 or (used[0]["slot"], used[0]["payload_id"], used[0]["round"]) != \
                ("gain", rec["payloads"][payload_step]["payload_id"], rnd) or rec["products"][product]["check_used_errors"]:
            return False
    return True


def _payloads_differ(rec) -> bool:
    ids = [rec["payloads"][s]["payload_id"] for s in PAYLOAD_STEPS]
    return len(set(ids)) == 3 and {rec["payloads"][s]["tag"] for s in PAYLOAD_STEPS} == {TAG} and \
        [rec["payloads"][s]["round"] for s in PAYLOAD_STEPS] == [None, 1, 2]


def _cache_refuses(rec, pairs) -> bool:
    decisions = {(d["for"], d["cached"]): d for d in rec["cache"]}
    return len(decisions) == len(rec["cache"]) and set(decisions) == pairs and all(
        not d["reuse"] and d["changed"] == ["gain"] and d["acted"] is None for d in decisions.values())


def _rounds_linked(rec) -> bool:
    """I5: each round payload names the previous one and its producing step's identity."""
    for step, previous in (("derive-r1", "nominal-gain"), ("derive-r2", "derive-r1")):
        document, previous_id = rec["payloads"][step]["document"], rec["payloads"][previous]["payload_id"]
        if document["derived_against"] != {"upstream_payloads": [previous_id]} or document["derived_from"] != previous_id \
                or document["producer"] != {"kind": "step", "step_id": rec["steps"][step]["identity"]}:
            return False
    return True


def _labels(rec, names) -> bool:
    return all(rec["steps"][s]["label"] == LABELS[s] for s in names)


def _failure_recorded(rec) -> bool:
    conv = check_digests()["convergence"][0]
    return ["derive-r2", rec["steps"]["derive-r2"]["artifact"], conv, "fail"] in rec["history"]["prior_failures"]


def assess(rec) -> list:
    """The expectation IDs that do not hold. A missing field fails its expectation."""
    if rec.get("variant") == "converging":
        rules = {
            "L1": lambda: set(rec["steps"]) == set(ALL_STEPS) and all(v["computed"] == 1 for v in rec["steps"].values())
            and rec["order"] == list(ALL_STEPS) and _payloads_differ(rec) and _rounds_linked(rec),
            "L2": lambda: _products_hold(rec, {"reco-r1": ("nominal-gain", None), "reco-r2": ("derive-r1", 1),
                                               "reco-final": ("derive-r2", 2)}),
            "L3": lambda: _cache_refuses(rec, {("reco-r2", "reco-r1"), ("reco-final", "reco-r1"), ("reco-final", "reco-r2")})
            and rec["reuse_control"]["decision"]["reuse"] and rec["reuse_control"]["decision"]["acted"] == "reused"
            and rec["reuse_control"]["state"] == "reused"
            and rec["reuse_control"]["source"] == rec["steps"]["reco-final"]["artifact"]
            and "reuse source is not a usable, current output" in rec["reuse_across_steps"],
            "L4": lambda: rec["steps"]["reco-final"]["consumed"] == {"derive-r2": rec["steps"]["derive-r2"]["artifact"]},
            "L5": lambda: set(rec["steps"]) == set(LABELS) and _labels(rec, LABELS),
            "L6": lambda: {k: v["result"] for k, v in rec["checks"].items()} == {"convergence": "pass", "mode": "pass", "record": "pass"},
            "L7": lambda: rec["published"] == {did: rec["steps"][step]["artifact"] for did, step in DELIVERABLES.items()}
            and rec["publish_refused"] == {},
            "L8": lambda: rec["claims"] == CLAIMS,
        }
    elif rec.get("variant") == "non-converging":
        rules = {
            "H1": lambda: rec["checks"]["convergence"]["result"] == "fail" and rec["checks"]["convergence"]["metric"] > TAU
            and rec["checks"]["mode"]["result"] == "pass" and "record" not in rec["checks"]
            and set(rec["steps"]) == set(ALL_STEPS) - {"reco-final"} and all(v["computed"] == 1 for v in rec["steps"].values())
            and rec["order"] == list(ALL_STEPS[:-1]) and _payloads_differ(rec) and _rounds_linked(rec) and _products_hold(rec, {"reco-r1": ("nominal-gain", None), "reco-r2": ("derive-r1", 1)})
            and _cache_refuses(rec, {("reco-r2", "reco-r1")}) and rec["claims"] == CLAIMS,
            "H2": lambda: rec["steps"]["derive-r2"]["label"] == "held" and "reco-final" not in rec["products"]
            and rec["published"] == {} and sorted(rec["publish_refused"]) == sorted(DELIVERABLES)
            and all(NOT_MET in reason for reason in rec["publish_refused"].values()),
            "H3": lambda: _labels(rec, ("reco-r1", "derive-r1", "reco-r2")),
            "H4": lambda: _failure_recorded(rec) and rec["rewrite_probe"]["label"] == "held",
            "H5": lambda: rec["forced_outside"]["label"] == "blocked_upstream" and NOT_MET in rec["forced_outside"]["publish"],
        }
    else:
        return ["variant"]
    failed = []
    for rule_id, rule in rules.items():
        try:
            held = bool(rule())
        except (KeyError, TypeError, IndexError, AttributeError):
            held = False
        if not held:
            failed.append(rule_id)
    return failed


# ================================================================ command line

def _emit(status: str, **fields) -> int:
    print(json.dumps({"status": status, **fields}, sort_keys=True))
    return exit_code(status)


def write_record(path: Path, content: bytes) -> None:
    with open(path, "xb") as handle:
        handle.write(content)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="operation", required=True)
    run_parser = sub.add_parser("run", help="run one variant of the fixture loop and write its record")
    run_parser.add_argument("--variant", required=True)
    run_parser.add_argument("--plant")
    run_parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.variant not in SPREAD or (args.plant is not None and args.plant not in PLANTS):
        return _emit("rejected", reason=f"unknown variant {args.variant!r} or plant {args.plant!r}")
    if args.out.exists() or not args.out.parent.is_dir():
        return _emit("rejected", reason=f"{args.out} exists or its folder does not: a record is never overwritten")
    try:
        rec = run(args.variant, args.plant)
    except Exception as error:  # noqa: BLE001 - any crash is "incomplete", never a negative reading
        return _emit("incomplete", reason=f"{type(error).__name__}: {error}")
    failed = assess(rec)
    rec["assessment"] = {"failed": failed}
    content = (json.dumps(rec, sort_keys=True, indent=1) + "\n").encode()
    try:
        write_record(args.out, content)
    except OSError as error:  # the record was not written: incomplete, never a negative reading
        return _emit("incomplete", reason=f"the record could not be written: {type(error).__name__}: {error}")
    return _emit("ok" if not failed else "failed", variant=args.variant, plant=args.plant, failed=failed, out=str(args.out),
                 sha256=sha256_hex(content))


if __name__ == "__main__":
    sys.exit(main())
