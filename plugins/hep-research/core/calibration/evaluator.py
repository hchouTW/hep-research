"""The evaluator interface of Part B section 7.1 and the registry of evaluators known to the engine.

An experiment's adapter implements five functions:

    evaluate(theta, phi, psi, model, effects_off, seeds)
        -> {pred, V_MC, n_eff[observable], node_diag[node], V_emu, V_learn, grad (optional)}
    resample(node, theta, phi, psi, model, inputs, seeds)          -> direct sampling of that node
    evaluate_from(node, samples, theta, phi, psi, model, seeds)    -> observables from a node output (for P0)
    learned_closure(fold)                                         -> phase 5 (G4-L)
    ask() / tell()                                                -> phase 3 (resimulation and surrogate models)

tiers() and domain() are not the adapter's: candidate methods come from calib_chain, feasibility and the final method
from calib_design (section 7.1). The engine knows the evaluators of this registry by the plan's `evaluator.kind`; the
g4sim evaluator (adapters/geant4, phase 3) is not imported by core (layering)."""
from __future__ import annotations

from typing import Protocol


class EvaluatorUnavailable(LookupError):
    """No evaluator of the plan's kind in this engine version: the caller reports `incomplete` (exit 3)."""


class Evaluator(Protocol):
    observables: list[str]
    parameters: list[str]

    def evaluate(self, theta: dict, phi: dict | None = None, psi: dict | None = None, model: str = "nominal",
                 effects_off=(), seeds: dict | None = None) -> dict: ...

    def resample(self, node: str, theta: dict, phi: dict | None, psi: dict | None, model: str, inputs,
                 seeds: dict) -> object: ...

    def evaluate_from(self, node: str, samples, theta: dict, phi: dict | None, psi: dict | None, model: str,
                      seeds: dict) -> dict: ...


_REGISTERED: dict = {}


def register(kind: str, builder) -> None:
    """Register an adapter's builder (spec, plan) -> evaluator under `kind` (phase 3: the g4sim evaluator of the
    Geant4 adapter, section 7.1, registers itself on import; core never imports it)."""
    _REGISTERED[kind] = builder


def make(plan: dict, contract: dict | None = None):
    """The evaluator the plan names (plan['evaluator'] = {'kind': ..., ...}); phase 1 knows the toy detector, its
    variants and the declared small chains (core/calibration/toy.py)."""
    spec = plan.get("evaluator") or {}
    kind = spec.get("kind")
    from core.calibration import toy                       # the only evaluators in core
    builders = {"toy-detector": toy.toy_detector, "toy-detector-subgraph": toy.toy_detector_subgraph,
                "toy-detector-bimodal": toy.toy_detector_bimodal, "chain": toy.chain_from_spec, **_REGISTERED}
    if kind not in builders:
        raise EvaluatorUnavailable(f"no evaluator of kind {kind!r} in this engine version (phase 1 has "
                                   f"{sorted(builders)}; the g4sim evaluator registers itself when the Geant4 adapter's evaluator is imported)")
    return builders[kind](spec, plan)
