"""Simulator calibration phase 5: the default-off identity cases over the phase-5-modified default-off branches
(review F3, A33; `calibration_phase5_gates.py` item 4). Not a unit test module.

Each case runs only engine code (`core.calibration`, no test fixtures) of the plugin tree given by --root and prints
its output as JSON. The golden output of a case is captured by running THIS file against a `git archive` of the
phase-5 base (`calibration_phase5_gates.py --capture-base-cases`); at the gate the same file runs against the gate
commit's tree. So a difference is a change of the engine between the base and the gate commit with the extensions
off, never a change of fixtures or of the case code (the harness compares this file's SHA-256 with the capture's).

Cases (each runs a branch the 50 phase-0..4 cases do not reach, review F3):
- holdout_toy_detector: a holdout fit on the toy detector (problems.from_inputs, the calib_validate path),
  validate.holdout_pieces, one validate.holdout_toy (simulate and simulate_val from the weighted nominal MC, i.e.
  ToyProblem._observe_weighted; replica_pert and replica_pert_val; the validation block _val_block).
- toy_replica_paths: ToyProblem.replica_pert / replica_pert_val / simulate_val (both data paths) directly.
- identify_p3_toy: identify.p3 on the toy detector at the prior centre (Asimov).
- evaluator_problem_standin: EvaluatorProblem.reference, a fit and identify.p3 on the analytic Cherenkov stand-in.
- vmodel_columns_components: linear.vmodel_columns with squared-exponential and matrix components, and
  linear.design on the toy detector with those components.
Left out: the inferred-V_model version branch of vmodel_columns (`version=`) and every learned-path branch: their APIs
do not exist at the base (they are phase-5 opt-in features, tested by item 1).

  python -I calibration_phase5_identity_cases.py --root PLUGIN_ROOT --case NAME     (prints the output JSON)
  python -I calibration_phase5_identity_cases.py --list
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

CASES = ("holdout_toy_detector", "toy_replica_paths", "identify_p3_toy", "evaluator_problem_standin",
         "vmodel_columns_components")
CAL = ["beam1_e_mean", "beam2_e_mean", "beam4_e_mean", "light_e_mean", "light_e_width", "spe_e_mean"]
VAL = ["beam2_e_width", "beam4_e_width"]


def plain(x):
    """A JSON value of x (dicts, sequences, NumPy arrays and scalars; non-finite floats as strings); anything else
    is an error, so the output never depends on an object's repr."""
    import numpy as np
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if isinstance(x, np.ndarray):
        return plain(x.tolist())
    if isinstance(x, np.generic):
        x = x.item()
    if isinstance(x, float) and not math.isfinite(x):
        return repr(x)
    if x is None or isinstance(x, (bool, int, float, str)):
        return x
    raise TypeError(f"not a plain value: {type(x).__name__}")


def dump(value) -> str:
    return json.dumps(plain(value), indent=1, sort_keys=True) + "\n"


def toy_contract(with_vmodel: bool = False) -> tuple[dict, dict]:
    """The small toy-detector contract of the fit_toy golden case (2 theta, 4000 MC events), with the validation rows."""
    obs = [{"name": n, "role": "calibration", "block": "gaussian", "link": "log"} for n in CAL] + \
          [{"name": n, "role": "validation", "block": "gaussian", "link": "log"} for n in VAL]
    contract = {"observables": obs, "exposure": {"all": 400},
                "parameters": [{"name": "pde", "role": "theta", "sampling_bounds": [0.2, 0.3],
                                "physical_bounds": [0.01, 0.99]},
                               {"name": "gain", "role": "theta", "sampling_bounds": [8, 12],
                                "physical_bounds": [1, 100]}]}
    if with_vmodel:                       # linear.design reads the exposure per run
        contract["model_discrepancy"] = {"form": "fixed", "components": vmodel_components()}
        contract["exposure"] = {r: 400 for r in ("beam1", "beam2", "beam4", "light", "spe")}
    plan = {"evaluator": {"kind": "toy-detector-subgraph", "events": 4000}}
    return contract, plan


def vmodel_components() -> list:
    return [{"kind": "squared-exponential", "observables": ["beam1_e_mean", "beam2_e_mean", "beam4_e_mean"],
             "f": 0.02, "length": 1.5, "control": {"beam1_e_mean": 1.0, "beam2_e_mean": 2.0, "beam4_e_mean": 4.0}},
            {"kind": "matrix", "observables": ["light_e_mean", "light_e_width"],
             "R": [[4e-4, 1e-4], [1e-4, 9e-4]]}]


def toy_problem():
    """problems.from_inputs on the toy contract with values generated at (0.25, 10) (fresh events, seed 3), as
    calib_fit.py / calib_validate.py build it; returns (problem, validation values in link space)."""
    import numpy as np

    from core.calibration import problems
    from core.calibration import toy_problem as TP
    contract, plan = toy_contract()
    probe = problems.from_inputs(contract, plan, None, None)
    truth = np.array([0.25, 10.0])
    y = np.exp(probe.simulate(truth, np.random.default_rng(3), nominal=False).y_gauss)
    yv = probe.simulate_val(truth, np.random.default_rng(4), nominal=False)
    p = problems.from_inputs(contract, plan, dict(zip(CAL, y.tolist())), None)
    p.sigma_noise = TP.estimate_sigma_noise(p, p.initial_beta())
    return p, yv


def ref_summary(ref) -> dict:
    return {"V_G": ref.V_G, "V_std": ref.V_std, "ln_det": getattr(ref, "ln_det", None),
            "has_V_learn": hasattr(ref, "V_learn")}


def case_holdout_toy_detector() -> dict:
    import numpy as np

    from core.calibration import fit as F
    from core.calibration import validate as V
    p, yv = toy_problem()
    f = F.find_extremum(p, 20261201, p.initial_beta())
    pc = V.holdout_pieces(p, f, yv)
    Cp, k = V.c_r_plus(pc["C_r"], pc["s"], pc["constraints"])
    ok, r, ft = V.holdout_toy(p, f, f.beta, np.random.default_rng([20261202, 0]), seed=(20261202, 0))
    return {"fit": f.record(), "beta": f.beta, "pieces": pc, "T_v": V.t_v(pc["r"], Cp), "k": k,
            "val_block": p.val, "toy": {"converged": ok, "r": r, "fit": ft.record()}}


def case_toy_replica_paths() -> dict:
    import numpy as np
    p, _ = toy_problem()
    b = p.initial_beta()
    rng = np.random.default_rng(20261203)
    return {"replica_pert": p.replica_pert(rng), "replica_pert_val": p.replica_pert_val(rng),
            "simulate_val_nominal": p.simulate_val(b, rng), "simulate_val_fresh": p.simulate_val(b, rng, nominal=False),
            "simulate_nominal": p.simulate(b, rng).y_gauss, "reference": ref_summary(p.reference(b, b))}


def case_identify_p3_toy() -> dict:
    from core.calibration import identify
    p, _ = toy_problem()
    b = p.initial_beta()
    return {"p3": identify.p3(p, b), "p3_ref": identify.p3(p, b, p.reference(b, b))}


def case_evaluator_problem_standin() -> dict:
    import numpy as np

    from core.calibration import cherenkov_standin as C
    from core.calibration import evaluator_problem as EP
    from core.calibration import fit as F
    from core.calibration import identify
    from core.calibration import likelihood as L
    samples = [{"name": "R_p100", "beta": C.beta_of(100.0)}, {"name": "R_p2.4", "beta": C.beta_of(2.4)}]
    centre = {"height_mm": 470.0, "index_scale": 1.0}
    p = EP.EvaluatorProblem(C.CherenkovStandIn(samples), C.contract(samples), degeneracy_modes=[C.MODE])
    tc = p.beta(centre)
    ref = p.reference(tc, tc)
    p.observed = L.Observations(y_gauss=p.h(tc))
    lk = L.Likelihood(p.layout, p.observed, ref)
    b0 = lk.initial_beta(centre)
    p3 = identify.p3(p, b0)
    q = EP.EvaluatorProblem(C.CherenkovStandIn(samples), C.contract(samples), degeneracy_modes=[C.MODE])
    q.observed = q.simulate(q.beta({"height_mm": 472.0, "index_scale": 1.0005}), np.random.default_rng(20261204))
    f = F.find_extremum(q, 20261205, q.beta(centre))
    return {"reference": ref_summary(ref), "p3": p3, "fit": f.record(), "beta": f.beta,
            "observed": q.observed.y_gauss}


def case_vmodel_columns_components() -> dict:
    from core.calibration import evaluator, linear
    names = CAL
    contract, plan = toy_contract(with_vmodel=True)
    U = linear.vmodel_columns(contract, names)
    U_none = linear.vmodel_columns({"model_discrepancy": {"form": "fixed", "components": []}}, names)
    ev = evaluator.make(plan, contract)
    d = linear.design(ev, contract, plan)
    keep = ("names", "theta", "theta_ref", "mu", "J", "V_data", "V_MC", "n_nu", "A_theta", "sigma_tot", "Sigma_MC",
            "Sigma_data", "lambda_max")
    return {"U": U, "U_shape": list(U.shape), "U_none_shape": list(U_none.shape), "design": {k: d[k] for k in keep}}


def run(name: str) -> dict:
    if name not in CASES:
        raise KeyError(name)
    import warnings
    warnings.filterwarnings("ignore", message="The balance properties of Sobol")
    return globals()["case_" + name]()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", help="the plugin root whose core.calibration runs the case")
    ap.add_argument("--case", choices=CASES)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        print(json.dumps(list(CASES)))
        return 0
    if not (a.root and a.case):
        ap.error("--root and --case")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(a.root).resolve()))
    sys.stdout.write(dump(run(a.case)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
