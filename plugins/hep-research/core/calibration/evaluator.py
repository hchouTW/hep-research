"""The evaluator interface of Part B section 7.1 and the registry of evaluators known to the engine.

An experiment's adapter implements five functions:

    evaluate(theta, phi, psi, model, effects_off, seeds)
        -> {pred, V_MC, n_eff[observable], node_diag[node], V_emu, V_learn, grad (optional)}
    resample(node, theta, phi, psi, model, inputs, seeds)          -> direct sampling of that node
    evaluate_from(node, samples, theta, phi, psi, model, seeds)    -> observables from a node output (for P0)
    learned_closure(fold)                                         -> phase 5 (G4-L)
    ask(requests) / tell(run_ids)                                 -> the asynchronous interface (below)

ask/tell (resimulation and surrogate models, phase 3): the engine keeps the state file (calibration-ask-tell/1,
core/calibration/emulator.py: new_state, ask, tell, drive), one entry per evaluation with its `run_id`, parameter
point and seeds. `ask(requests)` submits [{run_id, theta, seeds, names}] and returns the run_ids accepted; `tell(
run_ids)` returns {run_id: result} for those done (each once; pending ones are absent), a result being what
`evaluate` returns ({names, pred, V_MC}, optionally the per-event contributions `influence` for sigma_Delta of P6).

tiers() and domain() are not the adapter's: candidate methods come from calib_chain, feasibility and the final method
from calib_design (section 7.1). The engine knows the evaluators of this registry by the plan's `evaluator.kind`; the
g4sim evaluator (adapters/geant4, phase 3) is not imported by core (layering).

effects_off (section 10.5, phase 4): {effect: {parameter: value after removal}}, the values the contract's `effects`
declare (`removal_values` merges them); evaluating with it is evaluating at those parameter values, with the plan's
methods. An evaluator that cannot remove effects raises (calib_contrib reports `incomplete`)."""
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

    def ask(self, requests: list) -> list: ...

    def tell(self, run_ids=None) -> dict: ...


def removal_values(effects_off) -> dict:
    """The parameter values of `effects_off` ({effect: {parameter: value}}, section 10.5) merged into one point; a
    bare list of effect names (no declared values) or two effects removing one parameter to different values is a
    ValueError."""
    if not effects_off:
        return {}
    if not isinstance(effects_off, dict) or not all(isinstance(v, dict) for v in effects_off.values()):
        raise ValueError("effects_off is {effect: {parameter: value after removal}} (section 10.5): every effect "
                         "carries its declared value after removal")
    out: dict = {}
    for name, removal in effects_off.items():
        for par, value in removal.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"effect {name!r}: the value after removal of {par!r} is not a number")
            if par in out and out[par] != float(value):
                raise ValueError(f"parameter {par!r} is removed to different values by two effects")
            out[par] = float(value)
    return out


_REGISTERED: dict = {}


def register(kind: str, builder) -> None:
    """Register an adapter's builder (spec, plan) -> evaluator under `kind` (phase 3: the g4sim evaluator of the
    Geant4 adapter, section 7.1, registers itself on import; core never imports it)."""
    _REGISTERED[kind] = builder


def make(plan: dict, contract: dict | None = None):
    """The evaluator the plan names (plan['evaluator'] = {'kind': ..., ...}); phase 1 knows the toy detector, its
    variants and the declared small chains (core/calibration/toy.py). With plan['evaluator']['surrogate'] (a trained
    surrogate's record, emulator.Surrogate.record) the surrogate-model parameters are evaluated with it (phase 3)."""
    spec = plan.get("evaluator") or {}
    kind = spec.get("kind")
    from core.calibration import toy                       # the only evaluators in core
    builders = {"toy-detector": toy.toy_detector, "toy-detector-subgraph": toy.toy_detector_subgraph,
                "toy-detector-bimodal": toy.toy_detector_bimodal, "chain": toy.chain_from_spec, **_REGISTERED}
    if kind not in builders:
        raise EvaluatorUnavailable(f"no evaluator of kind {kind!r} in this engine version (phase 1 has "
                                   f"{sorted(builders)}; the g4sim evaluator registers itself when the Geant4 adapter's evaluator is imported)")
    if kind in _REGISTERED and contract is not None:     # adapters read the contract's locked bindings
        spec = dict(spec, contract=contract)
    ev = builders[kind](spec, plan)
    if spec.get("surrogate"):                            # a trained surrogate (calib_emulator.py train --out)
        if not hasattr(ev, "attach_surrogate"):
            raise EvaluatorUnavailable(f"the evaluator of kind {kind!r} cannot carry a surrogate model")
        from core.calibration import emulator
        ev.attach_surrogate(emulator.Surrogate.from_record(spec["surrogate"]))
    return ev
