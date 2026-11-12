"""A `fit.py` Problem over a section 7.1 evaluator (phase 3): the g4sim-backed problems (the synthetic ZDC fixture of
section 15.2 through the g4sim evaluator, which registers itself from the Geant4 adapter) and the analytic stand-ins of
`cherenkov_standin.py`, without the toy detector's chain model.

- Prediction: the evaluator's prediction at theta (its methods, common random numbers: one batch of events at every
  theta), in the contract's link space, plus a toy's perturbation.
- Errors at theta_ref: V_data^unc = per-event covariance / exposure of each sample (the construction of
  `linear.design`), V_MC from the evaluator; V_G = V_data + V_MC. No bootstrap, nu or eta here.
- Pseudo-data: from a truth MC's events by the D6 rule of A12 (`closure.resample_truth`, at the data's sampling model),
  summarized with the evaluator's estimators; or, for analytic stand-ins without events, a Gaussian draw with V_data at
  the truth (labelled `gaussian-summary`).
"""
from __future__ import annotations

import math

import numpy as np

from . import closure
from . import likelihood as L
from . import linear, toy


class EvaluatorProblem:
    """theta from the contract (physical bounds, sampling bounds as the prior), the contract's Gaussian calibration
    observables and exposure; `seeds` select the evaluator's batch; `degeneracy_modes` feed the P3/G5 hints."""

    def __init__(self, evaluator, contract: dict, plan: dict | None = None, seeds: dict | None = None,
                 degeneracy_modes=(), fd_fraction: float | None = None):
        self.evaluator = evaluator
        self.contract = contract
        self.plan = dict(plan or {})
        self.seeds = seeds
        self.obs = linear.calibration_observables(contract)
        self.names = [o["name"] for o in self.obs]
        self.links = [o["link"] for o in self.obs]
        pars = [p for p in contract.get("parameters", []) if p.get("role") == "theta"]
        self.theta_names = [p["name"] for p in pars]
        self._prior = [tuple(map(float, p["sampling_bounds"])) for p in pars]
        self._bounds = [tuple(map(float, p.get("physical_bounds", p["sampling_bounds"]))) for p in pars]
        self.exposure = dict(contract.get("exposure") or {})
        self.layout = L.build_layout([{"name": n, "block": "gaussian", "link": k} for n, k in zip(self.names,
                                     self.links)], self.theta_names, [], 0, 0)
        frac = fd_fraction if fd_fraction is not None else float((self.plan.get("design") or {}).get("fd_fraction",
                                                                                                   0.05))
        self._fd_fraction = frac
        self.fd_steps = np.array([frac * (hi - lo) for lo, hi in self._prior])
        self.pert = np.zeros(len(self.names))
        self.sigma_noise = 0.0
        self.edm_tol = float((self.plan.get("numerics") or {}).get("tolerance", 0.1))   # D79, as problems.py
        self.observed: L.Observations | None = None
        self.truth = None
        self.has_bootstrap = False
        self.V_depends_on_theta = True
        self.degeneracy_modes = list(degeneracy_modes)
        self._cache: dict = {}

    # -- model
    def _evaluate(self, tp) -> dict:
        theta = {n: float(v) for n, v in zip(self.theta_names, np.asarray(tp, float))}
        key = tuple(round(v, 14) for v in theta.values())
        if key not in self._cache:
            if len(self._cache) > 2048:
                self._cache.clear()
            self._cache[key] = self.evaluator.evaluate(theta, names=self.names, seeds=self.seeds)
        return self._cache[key]

    def _to_link(self, pred) -> np.ndarray:
        return np.array([L.link(np.array([v]), k)[0] for v, k in zip(pred, self.links)])

    def h(self, tp) -> np.ndarray:
        return self._to_link(self._evaluate(tp)["pred"]) + self.pert

    def V_parts(self, tp) -> tuple[np.ndarray, np.ndarray]:
        """(V_data^unc, V_MC) in link space at theta."""
        r = self._evaluate(tp)
        runs = r["runs"]
        n_data = np.array([linear._exposure(self.exposure, o, runs[k]) for k, o in enumerate(self.obs)], float)
        samples = np.array([o.get("sample") or runs[k] for k, o in enumerate(self.obs)], dtype=object)
        same = np.equal.outer(samples, samples) & np.equal.outer(np.array(runs, dtype=object),
                                                                 np.array(runs, dtype=object))
        g = linear.to_link_delta(np.asarray(r["pred"], float), self.links)
        Vd = np.asarray(r["s2"], float) / np.sqrt(np.outer(n_data, n_data)) * same * np.outer(g, g)
        Vm = np.asarray(r["V_MC"], float) * np.outer(g, g)
        return Vd, Vm

    def reference(self, tp, beta, frozen=None, **_kw) -> L.Reference:
        Vd, Vm = self.V_parts(tp)
        n = len(self.names)
        return L.Reference(V_G=Vd + Vm, V_std=Vd, U=np.zeros((n, 0)), S=np.zeros((n, 0)), constraints=[]).finalize()

    def bounds(self):
        return list(self._bounds)

    def prior_box(self):
        return list(self._prior)

    def sigma_prior(self):
        return [(hi - lo) / math.sqrt(12.0) for lo, hi in self._prior]

    def beta(self, theta: dict) -> np.ndarray:
        return np.array([float(theta[n]) for n in self.theta_names])

    # -- pseudo-data and toys
    def with_data(self, observed: L.Observations):
        p = EvaluatorProblem(self.evaluator, self.contract, self.plan, self.seeds, self.degeneracy_modes,
                             self._fd_fraction)
        p.observed, p.truth = observed, self.truth
        return p

    def simulate(self, beta_truth, rng, phis=None, nominal: bool = True) -> L.Observations:
        """Gaussian-summary pseudo-data (`gaussian-summary`): N(h(truth), V_data(truth)); for evaluators without
        events (analytic stand-ins). Event-level pseudo-data from a truth MC: `pseudo_data`."""
        tp = np.asarray(beta_truth, float)[:len(self.theta_names)]
        Vd, _ = self.V_parts(tp)
        return L.Observations(y_gauss=rng.multivariate_normal(self.h(tp) - self.pert, Vd))

    def replica_pert(self, rng, tp=None) -> np.ndarray:
        """No replicas of the MC here: the evaluators of this module carry V_MC from their own events (zero for the
        analytic stand-ins); the replica-difference toys of section 6.6 need two batches (not provided)."""
        return np.zeros(len(self.names))

    def pseudo_data(self, truth_events: dict, sampling: dict, rng) -> L.Observations:
        """One pseudo-data set from a truth MC (D6 as approved in A12): events drawn with replacement with probability
        proportional to w at the size of the data's sampling model, summarized with the evaluator's estimators.
        truth_events: {run, values: {observable: per-event array}, weights?: per-event array}."""
        values = truth_events["values"]
        n = len(next(iter(values.values())))
        w = truth_events.get("weights")
        idx = closure.resample_truth(np.ones(n) if w is None else w, closure.pseudo_data_size(sampling, rng), rng)
        run = truth_events.get("run", "truth")
        by = {o["name"]: o for o in self.obs}
        obs = [toy.Observable(nm, run, (lambda ev, nm=nm: ev["values"][nm]), _functional(by[nm], truth_events, nm),
                              (lambda ev, nm=nm: np.isfinite(ev["values"][nm]))) for nm in self.names]
        holder = type("M", (), {"observables": obs})()
        picked = {run: {"values": {nm: np.asarray(values[nm], float)[idx] for nm in self.names}}}
        o = toy.observe(holder, picked, {run: np.ones(idx.size)}, self.names)
        return L.Observations(y_gauss=self._to_link(o["pred"]))


def _functional(obs: dict, truth_events: dict, name: str) -> str:
    """The estimator of an observable: the truth sample's declaration (the evaluator's), else the contract's."""
    f = (truth_events.get("functionals") or {}).get(name)
    return f or {"location": "mean", "width": "std"}.get(obs.get("functional", "location"), "mean")
