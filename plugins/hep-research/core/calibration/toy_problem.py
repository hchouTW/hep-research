"""The toy detector of section 15.1 as a fit problem of the engine (phase 2): the `fit.py` Problem over the phase-1
`ChainEvaluator`, labeled `synthetic`, used by the gates of phase 2 "on the toy detector" (section 17).

- Prediction: the evaluator's prediction at (theta, phi) with the plan's methods and common random numbers, in link
  space, plus the link-space columns of eta (data systematics) and, when the problem is a downstream segment, the
  shifts that `map_params` returns.
- Data errors: the event-level parametric bootstrap of section 2.1 at theta_ref, B >= max(500, 50 p) sets of the data's
  size generated from the model at theta_ref (never resampled from the observed events), regenerated with the same
  uniforms at every theta_ref update (common random numbers), frozen where section 7.3 says so.
- V_MC from the evaluator's per-event influence values; V_G = V-hat + V_MC.
- Toy data: one data-size event sample generated at the truth, summarized with the same estimators; constraint centres
  sampled around the true nuisances; replicas: two independent nominal-MC samples (new seeds) at the generation point.
"""
from __future__ import annotations

import math

import numpy as np

from . import likelihood as L
from . import toy
from .toy import ChainEvaluator, observe

LINK_BY_FUNCTIONAL = {"mean": "log", "std": "log", "fraction": "logit"}


def _seed_int(seed):
    if isinstance(seed, (tuple, list)):
        return int(np.random.SeedSequence([int(s) for s in seed]).generate_state(1)[0])
    return int(seed)


def per_set_summaries(model, events: dict, names: list, n_sets: int) -> np.ndarray:
    """The summary statistics of n_sets equal consecutive sets of each run's events (the bootstrap sets), the same
    estimators as `observe` with unit weights: (n_sets x len(names))."""
    by = {o.name: o for o in model.observables}
    out = np.zeros((n_sets, len(names)))
    for j, nm in enumerate(names):
        o = by[nm]
        ev = events[o.run]
        x = np.asarray(o.var(ev), float)
        m = np.ones(x.size, bool) if o.mask is None else np.asarray(o.mask(ev), bool)
        m &= np.isfinite(x)
        N = x.size // n_sets
        X, M = x[:N * n_sets].reshape(n_sets, N), m[:N * n_sets].reshape(n_sets, N)
        cnt = M.sum(1)
        mean = np.where(cnt > 0, (X * M).sum(1) / np.maximum(cnt, 1), np.nan)
        if o.functional in ("mean", "fraction"):
            out[:, j] = mean
        else:
            var = ((X - mean[:, None]) ** 2 * M).sum(1) / np.maximum(cnt, 1)
            out[:, j] = np.sqrt(var)
    return out


class ToyProblem:
    """theta: {name: {"bounds": (lo, hi), "prior": (lo, hi)}}; phi_P: {name: (centre, sigma)} (profile mode, acting
    through the evaluator, or `linkshift` names that `map_params` turns into link shifts); eta: [{relative:
    {observable: r}}]; exposure: data events per run; mc_events: nominal MC events per run."""

    def __init__(self, build, names: list, theta: dict, exposure: int, mc_events: int, mc_seed=20261120,
                 phi_P: dict | None = None, eta: list | None = None, links: dict | None = None, B: int | None = None,
                 boot_seed=20261121, generation: dict | None = None, map_params=None, plan: dict | None = None,
                 shift: dict | None = None, thickness_by_yield: bool = False):
        self.build = build
        self.names = list(names)
        self.theta_spec = dict(theta)
        self.phi_spec = dict(phi_P or {})
        self.eta_spec = list(eta or [])
        self.exposure, self.mc_events = int(exposure), int(mc_events)
        self.mc_seed, self.boot_seed = mc_seed, boot_seed
        self.plan = dict(plan or {})
        self.map_params = map_params
        self.shift_spec = dict(shift or {})              # shift-mode phi: {name: (centre, sigma)}
        self.shift_names = list(self.shift_spec)
        # the material thickness evaluated as its equivalent light-yield factor: the deposition only rescales d by
        # exp(-(t - t0)/lambda) (event by event with the same uniforms), so the photon count depends on (LY, t) only
        # through LY exp(-(t - t0)/lambda); this is the section 3.6 rerun of the deterministic deposition with the
        # photon-generation density reweighted, smooth in t, where resimulation with common random numbers is a
        # staircase on discrete counts (toy detector only; data are still generated with the resimulated thickness)
        self.thickness_by_yield = bool(thickness_by_yield)
        self.model = build(self.mc_events)
        self.ev = ChainEvaluator(self.model, {**self.plan, "seeds": {"nominal": _seed_int(mc_seed)}})
        by = {o.name: o for o in self.model.observables}
        self.links = {n: (links or {}).get(n, LINK_BY_FUNCTIONAL[by[n].functional]) for n in self.names}
        obs = [{"name": n, "block": "gaussian", "link": self.links[n]} for n in self.names]
        self.layout = L.build_layout(obs, list(self.theta_spec), list(self.phi_spec), 0, len(self.eta_spec))
        runs = {by[n].run for n in self.names}
        p_max = max(sum(1 for n in self.names if by[n].run == r) for r in runs)
        self.B = max(int(B or 0), L.bootstrap_size(p_max))
        self.generation = dict(generation or {})
        self.data = None
        self.truth = None
        self.pert = np.zeros(len(self.names))
        self.sigma_noise = 0.0
        self.edm_tol = 0.1
        self.has_bootstrap = True
        self.V_depends_on_theta = True
        self._data_model = build(self.exposure)
        self._boot_model = build(self.exposure * self.B)
        self._cache = {}

    # -- parameters
    def params_of(self, tp) -> tuple[dict, np.ndarray]:
        tp = np.asarray(tp, float)
        names = list(self.theta_spec) + list(self.phi_spec)
        d = dict(zip(names, tp))
        d.update({n: c for n, (c, _) in self.shift_spec.items()})      # shift-mode phi fixed at nominal
        if self.map_params is not None:
            return self.map_params(d)
        return d, np.zeros(len(self.names))

    def bounds(self):
        return [tuple(v["bounds"]) for v in self.theta_spec.values()]

    def prior_box(self):
        return [tuple(v["prior"]) for v in self.theta_spec.values()]

    def sigma_prior(self):
        return [(b - a) / math.sqrt(12.0) for a, b in self.prior_box()]

    @property
    def fd_steps(self):
        st = [1e-3 * (b - a) for a, b in self.prior_box()]
        k = 0.01 if self.thickness_by_yield else 0.2      # resimulated phi: steps above the CRN jitter
        st += [k * float(s) for _, s in self.phi_spec.values()]
        return np.asarray(st, float)

    # -- model
    def _equivalent(self, params: dict) -> dict:
        if not self.thickness_by_yield or "material_thickness" not in params:
            return params
        p = dict(params)
        t0 = toy.TOY_NOMINAL["material_thickness"]
        ly = p.get("light_yield", toy.TOY_NOMINAL["light_yield"])
        p["light_yield"] = ly * math.exp(-(p["material_thickness"] - t0) / toy.LAMBDA)
        p["material_thickness"] = t0
        return p

    def _predict(self, params: dict, seeds=None) -> dict:
        params = self._equivalent(params)
        key = (tuple(sorted((k, round(float(v), 14)) for k, v in params.items())), None if seeds is None else
               tuple(sorted(seeds.items())))
        if key not in self._cache:
            if len(self._cache) > 4096:
                self._cache.clear()
            self._cache[key] = self.ev.evaluate(params, names=self.names, seeds=seeds)
        return self._cache[key]

    def _to_link(self, pred):
        return np.array([L.link(np.array([v]), self.links[n])[0] for v, n in zip(pred, self.names)])

    def _dlink(self, pred):
        return np.array([L.dlink(np.array([v]), self.links[n])[0] for v, n in zip(pred, self.names)])

    def h(self, tp):
        params, shift = self.params_of(tp)
        return self._to_link(self._predict(params)["pred"]) + shift + self.pert

    def _shift_params(self, phis):
        return {n: c + s * float(v) for (n, (c, s)), v in zip(self.shift_spec.items(), np.atleast_1d(phis))}

    def h_shift(self, tp, phis):
        """The predictor with the shift-mode phi at centre + sigma phi_s (unit-normal coordinates, section 5.5)."""
        params, shift = self.params_of(tp)
        params = {**params, **self._shift_params(phis)}
        return self._to_link(self._predict(params)["pred"]) + shift + self.pert

    def eta_columns(self, mu) -> np.ndarray:
        cols = []
        for sj in self.eta_spec:
            col = np.zeros(len(self.names))
            for k, n in enumerate(self.names):
                r = float(sj.get("relative", {}).get(n, 0.0))
                if r:                    # a relative shift r of mu_k in link space: r on a log link, r mu_k g'(mu_k)
                    col[k] = r if self.links[n] == "log" else r * mu[k] * self._dlink(np.array([mu[k]]))[0]
            cols.append(col)
        return np.stack(cols, axis=1) if cols else np.zeros((len(self.names), 0))

    def bootstrap_vhat(self, params: dict, seed) -> np.ndarray:
        """The bootstrap covariance of the link-space summary statistics at theta_ref (same uniforms for a given
        seed at every theta_ref: common random numbers)."""
        ev = ChainEvaluator(self._boot_model, {"seeds": {"nominal": 1}})
        gen = ev.generate(_seed_int(seed), params={**self.model.nominal, **self._equivalent(params)})
        sets = per_set_summaries(self._boot_model, {r: v["events"] for r, v in gen["runs"].items()}, self.names,
                                 self.B)
        Z = np.stack([L.link(sets[:, k], self.links[n]) for k, n in enumerate(self.names)], axis=1)
        by = {o.name: o for o in self.model.observables}
        runs = [by[n].run for n in self.names]
        V = np.zeros((len(self.names), len(self.names)))
        for r in dict.fromkeys(runs):               # one event sample per run: p and B per sample (D34)
            idx = [k for k, x in enumerate(runs) if x == r]
            V[np.ix_(idx, idx)] = L.bootstrap_covariance(Z[:, idx])
        return V

    def reference(self, tp, beta, frozen=None, bootstrap_frozen=False, bootstrap_seed=None):
        params, _ = self.params_of(tp)
        r = self._predict(params)
        mu = r["pred"]
        D = self._dlink(mu)
        V_mc = r["V_MC"] * np.outer(D, D)
        if frozen is not None:
            Vd = frozen.V_std
        else:
            Vd = self.bootstrap_vhat(params, self.boot_seed if bootstrap_seed is None else bootstrap_seed)
        S = self.eta_columns(mu)
        U = np.zeros((len(self.names), 0))
        ref = L.Reference(V_G=Vd + V_mc, V_std=Vd, U=U, S=S)
        ref.V_MC = V_mc
        return ref.finalize()

    @property
    def V_MC_link(self):
        params, _ = self.params_of(np.r_[[0.5 * (a + b) for a, b in self.prior_box()],
                                         [c for c, _ in self.phi_spec.values()]])
        r = self._predict(params)
        D = self._dlink(r["pred"])
        return r["V_MC"] * np.outer(D, D)

    # -- data and toys
    def observe_at(self, params: dict, seed) -> np.ndarray:
        """Summary statistics (link space) of one data-size event sample generated at `params`."""
        ev = ChainEvaluator(self._data_model, {"seeds": {"nominal": 1}})
        gen = ev.generate(_seed_int(seed), params={**self.model.nominal, **params})
        w = {r: np.ones(self._data_model.runs[r].n) for r in gen["runs"]}
        o = observe(self._data_model, {r: v["events"] for r, v in gen["runs"].items()}, w, self.names)
        return self._to_link(o["pred"])

    def observe_nominal(self, params: dict, rng) -> np.ndarray:
        """Summary statistics (link space) of one data-size event set drawn with replacement from the nominal MC sample
        weighted to `params`: its expectation is the nominal MC prediction at that point (section 6.6: a toy's true
        value is m_nom(truth) = mu* + e_nom) and its noise is the data's event-level noise."""
        ev = self.ev
        target = {**self.model.nominal, **self._equivalent(params)}
        nom = ev.nominal
        run_events, regen = ev._prepared(target, nom)
        sample = {"runs": {rid: {"events": run_events[rid], "fractions": nom["runs"][rid].get("fractions")}
                           for rid in run_events}, "params": nom["params"], "sq": nom["sq"], "comps": nom["comps"]}
        w = ev.weights(target, sample, nodes=ev.reweighted_nodes(target, nom), regenerated=regen)
        w.pop("_missing_support", None)
        by = {o.name: o for o in self.model.observables}
        runs = {by[n].run for n in self.names}
        picked = {}
        for rid in runs:
            ww = np.asarray(w[rid], float)
            idx = rng.choice(ww.size, size=self.exposure, replace=True, p=ww / ww.sum())
            picked[rid] = {node: {k: np.asarray(v)[idx] for k, v in outs.items()} for node, outs in run_events[rid].items()}
        o = observe(self.model, picked, {r: np.ones(self.exposure) for r in picked}, self.names)
        return self._to_link(o["pred"])

    def simulate(self, beta_truth, rng, phis=None, nominal: bool = True) -> L.Data:
        """Toy data at the truth. nominal=True (toys under the null hypothesis, section 6.6): drawn from the nominal MC
        weighted to the truth; nominal=False (actual data, G8 pseudo-data with an analytic truth): a fresh event sample
        generated at the truth."""
        lay = self.layout
        sl = lay.slices()
        n0 = len(lay.theta) + len(lay.phi_P)
        params, shift = self.params_of(beta_truth[:n0])
        y = self.observe_nominal(params, rng) if nominal else self.observe_at(params, int(rng.integers(2 ** 62)))
        eta = beta_truth[sl["eta"]]
        if lay.n_eta:
            y = y + self.eta_columns(self._predict(params)["pred"]) @ eta
        y = y + shift
        phi0 = None
        if lay.phi_P:                            # constraint centres sampled around the true phi (section 6.6)
            sig = np.array([s for _, s in self.phi_spec.values()])
            phi0 = rng.normal(beta_truth[sl["phi_P"]], sig)
        return L.Data(y_gauss=y, phi0=phi0, phi_cov=self.phi_cov(),
                      eta0=rng.normal(eta, 1.0) if lay.n_eta else None)

    def phi_cov(self):
        if not self.phi_spec:
            return None
        return np.diag([float(s) ** 2 for _, s in self.phi_spec.values()])

    def replica_pert(self, rng, tp=None) -> np.ndarray:
        """(m_a - m_b) / sqrt(2) of two independent nominal-MC samples at the generation point (section 6.6)."""
        gen = {**self.model.nominal, **self.generation}
        sa, sb = int(rng.integers(2 ** 62)), int(rng.integers(2 ** 62))
        ma = self._to_link(self.ev.evaluate(gen, names=self.names, seeds={"nominal": sa})["pred"])
        mb = self._to_link(self.ev.evaluate(gen, names=self.names, seeds={"nominal": sb})["pred"])
        self.ev._other.pop(sa, None)
        self.ev._other.pop(sb, None)
        return (ma - mb) / math.sqrt(2.0)

    def with_data(self, data: L.Data, mc_seed=None):
        p = ToyProblem.__new__(ToyProblem)
        p.__dict__.update(self.__dict__)
        p.data = data
        p.pert = np.zeros(len(self.names))
        if mc_seed is not None and mc_seed != self.mc_seed:
            p.mc_seed = mc_seed
            p.ev = ChainEvaluator(self.model, {**self.plan, "seeds": {"nominal": _seed_int(mc_seed)}})
            p._cache = {}
        return p

    def asimov(self, beta: np.ndarray) -> L.Data:
        """Asimov data at beta (the prediction itself), for the design-stage gates."""
        lay = self.layout
        n0 = len(lay.theta) + len(lay.phi_P)
        params, shift = self.params_of(beta[:n0])
        y = self._to_link(self._predict(params)["pred"]) + shift
        cen = np.array([c for c, _ in self.phi_spec.values()]) if self.phi_spec else None
        return L.Data(y_gauss=y, phi0=cen, phi_cov=self.phi_cov(),
                      eta0=np.zeros(lay.n_eta) if lay.n_eta else None)

    def initial_beta(self, theta0: dict | None = None) -> np.ndarray:
        lay = self.layout
        b = np.zeros(lay.n_beta)
        sl = lay.slices()
        for i, (n, v) in enumerate(self.theta_spec.items()):
            b[i] = (theta0 or {}).get(n, 0.5 * sum(v["prior"]))
        if lay.phi_P:
            b[sl["phi_P"]] = [c for c, _ in self.phi_spec.values()]
        return b


def estimate_sigma_noise(problem: ToyProblem, beta: np.ndarray, K: int = 5, seed=20261122) -> float:
    """sigma_noise (section 8.1): the standard deviation of the objective recomputed at beta with K >= 5 sets of MC
    seeds (independent nominal MC samples, the reference quantities kept), used in the G1 EDM threshold and the
    section 7.4 tolerances."""
    if K < 5:
        raise ValueError("sigma_noise needs K >= 5 seed sets")
    lay = problem.layout
    n0 = len(lay.theta) + len(lay.phi_P)
    ref = problem.reference(beta[:n0], beta)
    vals = []
    for k in range(K):
        q = problem.with_data(problem.data, mc_seed=(_seed_int(seed), k))
        vals.append(L.Likelihood(lay, problem.data, ref).deviance(beta, q.h(beta[:n0])))
    return float(np.std(vals, ddof=1))
