"""The fit problem of a contract, a plan and calibration values (phase 2): the factory the phase-2 CLIs use.

Phase 2 knows the toy-detector evaluators of `evaluator.py` (section 17: phases 0-2 use only the toy detector); the
g4sim evaluator is phase 3. Calibration values are provided by `calib_data.py` alone (data_release.Ledger
.provide_values, which records the fit read); this module receives them.
"""
from __future__ import annotations

import numpy as np

from . import likelihood as L
from . import linear
from . import toy
from .toy_problem import ToyProblem


class ProblemError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def model_builder(plan: dict):
    """n -> toy.Model with n events per run, for the plan's evaluator kind."""
    spec = plan.get("evaluator") or {}
    kind = spec.get("kind")
    fano = float(spec.get("photon_fano", 1.0))
    runs = spec.get("runs")
    if kind == "toy-detector":
        return lambda n: toy.build_toy(n, "full", fano, runs)
    if kind == "toy-detector-subgraph":
        return lambda n: toy.build_toy(n, "subgraph", fano, runs)
    raise ProblemError("problem.evaluator", f"phase 2 fits need a toy-detector evaluator (got {kind!r}); the g4sim "
                       "evaluator is phase 3")


def from_inputs(contract: dict, plan: dict, values: dict | None = None, systematics: list | None = None) -> ToyProblem:
    """The ToyProblem of the contract's calibration observables (unused excluded), theta (physical bounds; sampling
    bounds as the prior box), profile-mode phi with constraints, eta from the release's systematic component, the
    exposure (one value for every run in phase 2), the plan's MC size, seeds and B."""
    obs = linear.calibration_observables(contract)
    names = [o["name"] for o in obs]
    links = {o["name"]: o["link"] for o in obs}
    theta, phi, shift = {}, {}, {}
    for p in contract.get("parameters", []):
        if p["role"] == "theta":
            theta[p["name"]] = {"bounds": tuple(p.get("physical_bounds", p["sampling_bounds"])),
                                "prior": tuple(p["sampling_bounds"])}
        elif p["role"] == "phi" and p.get("mode", "profile") == "profile":
            c = p.get("constraint") or {}
            if "sigma" not in c:
                raise ProblemError("problem.phi_constraint", f"profile phi {p['name']} needs a constraint")
            phi[p["name"]] = (float(c.get("center", toy.TOY_NOMINAL.get(p["name"], 0.0))), float(c["sigma"]))
        elif p["role"] == "phi" and p.get("mode") == "shift":
            c = p.get("constraint") or {}
            shift[p["name"]] = (float(c.get("center", toy.TOY_NOMINAL.get(p["name"], 0.0))), float(c["sigma"]))
    exp = set((contract.get("exposure") or {}).values())
    if len(exp) != 1:
        raise ProblemError("problem.exposure", "phase 2's toy problem uses one exposure for every run")
    spec = plan.get("evaluator") or {}
    seeds = plan.get("seeds") or {}
    eta = [{"relative": dict(s.get("relative", {}))} for s in (systematics or [])
           if any(n in s.get("relative", {}) for n in names)]
    unused = {u["observable"] for u in (contract.get("validation") or {}).get("unused", [])}
    vobs = [o for o in contract.get("observables", []) if o.get("role") == "validation" and o["name"] not in unused
            and o.get("block", "gaussian") == "gaussian"]
    links.update({o["name"]: o["link"] for o in vobs if o.get("link")})
    p = ToyProblem(model_builder(plan), names, theta, int(exp.pop()), int(spec.get("events", 40_000)),
                   seeds.get("nominal", 20261120), phi, eta, links, (plan.get("design") or {}).get("bootstrap_B"),
                   seeds.get("bootstrap", 20261121), plan=plan, shift=shift,
                   val_names=[o["name"] for o in vobs], val_mc_seed=seeds.get("validation_nominal", 20261123))
    p.edm_tol = float((plan.get("numerics") or {}).get("tolerance", 0.1))
    if values is not None:
        missing = [n for n in names if n not in values]
        if missing:
            raise ProblemError("problem.values", f"no calibration value for {missing}")
        y = np.array([L.link(np.array([float(values[n])]), links[n])[0] for n in names])
        p.observed = L.Observations(y_gauss=y, phi0=np.array([c for c, _ in phi.values()]) if phi else None,
                        phi_cov=p.phi_cov(), eta0=np.zeros(len(eta)) if eta else None)
    return p
