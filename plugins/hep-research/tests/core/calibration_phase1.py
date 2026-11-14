"""Shared builders for the phase-1 tests of the simulator calibration workflow: small declared chains (contract, plan)
for the single-gate negative tests of section 15.3 ("single-gate isolation mode"), and the toy detector's design
fixture. Everything here is `synthetic`."""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESIGN_FIXTURE = ROOT / "core" / "calibration" / "data" / "toy_detector_design.json"


def toy_design() -> dict:
    return json.loads(DESIGN_FIXTURE.read_text())


def chain_case(nodes: list[dict], observables: list[dict], nominal: dict, params: dict, exposure: dict,
               methods: dict | None = None, proposal: dict | None = None, n: int = 20_000, runs=None,
               seed: int = 7, design: dict | None = None) -> tuple[dict, dict]:
    """A contract and a plan for a declared chain.

    nodes: [{id, kernel (toy.CATALOG name), args, parents, kind (density|deterministic|black-box)}]
    observables: [{name, node, var, functional (mean|std|fraction), sample, link, class, run}]
    params: {name: {"nodes": [...], "bounds": [lo, hi]}}"""
    runs = runs or [{"id": "run", "n": n}]
    graph_nodes = [{"id": nd["id"], "kind": "stage", "kernel": nd.get("kind", "density"), "stage": str(i),
                    "mechanisms": ["yield"], "samplable": True} for i, nd in enumerate(nodes)]
    edges = [{"from": p, "to": nd["id"]} for nd in nodes for p in nd.get("parents", [])]
    contract = {
        "schema": "calibration-contract/1", "series": "chain-test", "simulator": "toy-chain",
        "stage_graph": {"nodes": graph_nodes, "edges": edges},
        "parameters": [{"name": k, "role": "theta", "nodes": v["nodes"], "sampling_bounds": list(v["bounds"]),
                        "physical_bounds": [v["bounds"][0] - 10, v["bounds"][1] + 10]} for k, v in params.items()],
        "references": [],
        "observables": [{"name": o["name"], "role": "calibration", "functional": o.get("class", "location"),
                         "link": o.get("link", "identity"), "block": "gaussian", "estimator": "shared",
                         "binning": {"kind": "none"}, "sample": o.get("sample", o.get("run", "run"))}
                        for o in observables],
        "exposure": dict(exposure), "validation": {"mode": "none", "N_dc": [], "N_d": [], "unused": []},
    }
    spec = {"nodes": [{"id": nd["id"], "kernel": nd["kernel"], "args": nd.get("args", {}),
                       "parents": nd.get("parents", [])} for nd in nodes],
            "runs": runs,
            "observables": [{"name": o["name"], "run": o.get("run", "run"), "node": o["node"], "var": o["var"],
                             "functional": o.get("functional", "mean"), "tail": o.get("class") == "tail"}
                            for o in observables],
            "nominal": dict(nominal), "param_nodes": {k: v["nodes"] for k, v in params.items()}}
    plan = {"schema": "calibration-plan/1",
            "kernels": {nd["id"]: {"stored": {"inputs": True, "outputs": True, "steps": nd["kernel"] == "steps"},
                                   "support_declared": True} for nd in nodes},
            "evaluator": {"kind": "chain", "spec": spec}, "seeds": {"nominal": seed, "resample": seed + 1},
            "methods": dict(methods or {}), "design": design or {"fd_fraction": 0.05, "n_scan": 32, "scan_seed": 3}}
    if proposal:
        plan["proposal"] = copy.deepcopy(proposal)
    return contract, plan


def gaussian_chain(bounds=(-2.0, 2.0), proposal=None, n_data=200, n=20_000):
    """x ~ N(mu, sigma), mu the parameter, the observables mean and width of x (P5 cases a and b)."""
    return chain_case(
        [{"id": "x", "kernel": "normal", "args": {"out": "x", "loc": "mu", "scale": "sigma"}}],
        [{"name": "x_mean", "node": "x", "var": "x"}, {"name": "x_width", "node": "x", "var": "x",
                                                       "functional": "std", "link": "log", "class": "core-width"}],
        {"mu": 0.0, "sigma": 1.0}, {"mu": {"nodes": ["x"], "bounds": list(bounds)}}, {"run": n_data},
        methods={"mu": "analytic-reweighting"}, proposal=proposal, n=n)


def uniform_chain(proposal=None):
    """x ~ U(theta, theta + 1) (section 15.3.1, P0 missing support), generated at theta_0 = 0, prior [0, 0.5]."""
    return chain_case(
        [{"id": "x", "kernel": "uniform", "args": {"out": "x", "lo": "theta", "width": 1.0}}],
        [{"name": "x_mean", "node": "x", "var": "x"}, {"name": "x_width", "node": "x", "var": "x",
                                                       "functional": "std", "link": "log", "class": "core-width"}],
        {"theta": 0.0}, {"theta": {"nodes": ["x"], "bounds": [0.0, 0.5]}}, {"run": 500},
        methods={"theta": "analytic-reweighting"}, proposal=proposal)


def poisson_chain(mu=1000.0, rel=0.1, n_data=1000):
    """n ~ Poisson(rate), rate = mu nominal, prior mu (1 +- rel): section 3.6 / 15.3.1 (Poisson at mu = 1000)."""
    return chain_case(
        [{"id": "n", "kernel": "poisson", "args": {"out": "n", "rate": "rate"}}],
        [{"name": "n_mean", "node": "n", "var": "n", "link": "log"},
         {"name": "n_width", "node": "n", "var": "n", "functional": "std", "link": "log", "class": "core-width"}],
        {"rate": mu}, {"rate": {"nodes": ["n"], "bounds": [mu * (1 - rel), mu * (1 + rel)]}}, {"run": n_data},
        methods={"rate": "analytic-reweighting"})
