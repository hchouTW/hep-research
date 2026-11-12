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
    if isinstance(seed, (tuple, list)):           # nested seed tuples are flattened through their own integers
        return int(np.random.SeedSequence([_seed_int(s) for s in seed]).generate_state(1)[0])
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
        else:                                # the estimator of toy.functional with unit weights (unbiased width)
            var = ((X - mean[:, None]) ** 2 * M).sum(1) / np.maximum(cnt - 1, 1)
            out[:, j] = np.sqrt(var) / np.array([toy.c4(float(c)) for c in cnt])
    return out


class ToyProblem:
    """theta: {name: {"bounds": (lo, hi), "prior": (lo, hi)}}; phi_P: {name: (centre, sigma)} (profile mode, acting
    through the evaluator, or `linkshift` names that `map_params` turns into link shifts); eta: [{relative:
    {observable: r}}]; exposure: data events per run; mc_events: nominal MC events per run."""

    def __init__(self, build, names: list, theta: dict, exposure: int, mc_events: int, mc_seed=20261120,
                 phi_P: dict | None = None, eta: list | None = None, links: dict | None = None, B: int | None = None,
                 boot_seed=20261121, generation: dict | None = None, map_params=None, plan: dict | None = None,
                 shift: dict | None = None, thickness_by_yield: bool = False, val_names: list | None = None,
                 val_build=None, val_mc_seed=20261123, val_exposure: int | None = None, counts: dict | None = None,
                 boot_exposure: int | None = None, shift_response: dict | None = None):
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
        # the response of a shift-mode parameter to its unit-normal phi: centre + sigma g(phi), g(phi) = phi + k2 phi^2
        # + k3 phi^3 ({name: (k2, k3)}; linear when absent): the nonlinear phi responses of section 8.7 note 5
        self.shift_response = {n: tuple(map(float, v)) for n, v in (shift_response or {}).items()}
        unknown = set(self.shift_response) - set(self.shift_spec)
        if unknown:
            raise ValueError(f"shift_response names no shift-mode parameter: {sorted(unknown)}")
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
        # count observables (section 2.1 block rules): a histogram of a model observable's per-event variable over
        # the events passing its mask; "absolute" Poisson counts (optionally BB-lite) or a free-omega "shape"
        self.count_spec = {n: dict(c) for n, c in (counts or {}).items()}
        for n, c in self.count_spec.items():
            if c["source"] not in by:
                raise ValueError(f"count observable {n}: unknown source {c['source']!r}")
            c["edges"] = np.asarray(c["edges"], float)
            c["run"] = by[c["source"]].run
        obs = [{"name": n, "block": "gaussian", "link": self.links[n]} for n in self.names]
        obs += [{"name": n, "block": "poisson", "bins": len(c["edges"]) - 1, "free_omega": c.get("kind") == "shape",
                 "bb": bool(c.get("bb", False))} for n, c in self.count_spec.items()]
        self.layout = L.build_layout(obs, list(self.theta_spec), list(self.phi_spec), 0, len(self.eta_spec))
        self._count_blocks = {b.name: b for b in self.layout.blocks if b.kind == "poisson"}
        self.poisson_total = any(c.get("kind", "absolute") == "absolute" for c in self.count_spec.values())
        runs = {by[n].run for n in self.names}
        p_max = max([sum(1 for n in self.names if by[n].run == r) for r in runs] or [1])
        self.B = max(int(B or 0), L.bootstrap_size(p_max))
        self.boot_exposure = int(boot_exposure or exposure)  # != exposure only in a negative control (omega = 1)
        self.generation = dict(generation or {})
        self.observed = None
        self.truth = None
        self.pert = np.zeros(len(self.names))
        self.sigma_noise = 0.0
        self.edm_tol = 0.1
        self.has_bootstrap = True
        self.V_depends_on_theta = True
        # actual data with absolute counts: the event total is Poisson(exposure) (a generous fixed-size sample is cut)
        self._data_model = build(self.exposure if not self.poisson_total else
                                 int(self.exposure + 8 * math.sqrt(self.exposure) + 20))
        self._boot_model = build(self.boot_exposure * self.B)
        self._cache = {}
        # validation observables (holdout, section 9.2): a separate event sample of the same detector (its own nominal
        # MC and its own data), so that validation data share no events with the calibration data
        self.val_names = list(val_names or [])
        self.val_exposure = int(val_exposure or exposure)
        self.val_mc_seed = val_mc_seed
        self.pert_val = np.zeros(len(self.val_names))
        self._val_cache = {}
        self._val_point = None
        if self.val_names:
            vb = val_build or build
            self._val_build = vb
            self._val_model = vb(self.mc_events)
            vby = {o.name: o for o in self._val_model.observables}
            self.val_links = {n: (links or {}).get(n, LINK_BY_FUNCTIONAL[vby[n].functional]) for n in self.val_names}
            self.val_ev = ChainEvaluator(self._val_model, {**self.plan, "seeds": {"nominal": _seed_int(val_mc_seed)}})
            self._val_data_model = vb(self.val_exposure)
            vruns = {vby[n].run for n in self.val_names}
            self.B_val = max(self.B, L.bootstrap_size(max(sum(1 for n in self.val_names if vby[n].run == r)
                                                          for r in vruns)))
            self._val_boot_model = vb(self.val_exposure * self.B_val)

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
        g = (self._to_link(self._predict(params)["pred"]) + shift + self.pert) if self.names else np.zeros(0)
        return np.r_[g, self._count_link(params)] if self.count_spec else g

    # -- count observables
    def _weighted_events(self, params: dict, ev=None, model=None):
        """The nominal MC events of each run and their weights to `params` (reweighting or regeneration with common
        random numbers, as the evaluator's methods decide)."""
        ev, model = ev or self.ev, model or self.model
        target = {**model.nominal, **self._equivalent(params)}
        nom = ev.nominal
        run_events, regen = ev._prepared(target, nom)
        sample = {"runs": {rid: {"events": run_events[rid], "fractions": nom["runs"][rid].get("fractions")}
                           for rid in run_events}, "params": nom["params"], "sq": nom["sq"], "comps": nom["comps"]}
        w = ev.weights(target, sample, nodes=ev.reweighted_nodes(target, nom), regenerated=regen)
        w.pop("_missing_support", None)
        return run_events, w

    def _hist(self, model, events: dict, name: str, weights=None):
        c = self.count_spec[name]
        o = {x.name: x for x in model.observables}[c["source"]]
        ev = events[c["run"]]
        x = np.asarray(o.var(ev), float)
        m = np.ones(x.size, bool) if o.mask is None else np.asarray(o.mask(ev), bool)
        m &= np.isfinite(x)
        w = np.ones(x.size) if weights is None else np.asarray(weights, float)
        sw, _ = np.histogram(x[m], c["edges"], weights=w[m])
        sw2, _ = np.histogram(x[m], c["edges"], weights=w[m] ** 2)
        return sw, sw2

    def counts_pred(self, params: dict) -> dict:
        """Per count observable: the expected counts at the data's exposure (absolute) or the model shape (any
        normalization), with sum w and sum w^2 of the nominal MC per bin (BB-lite tau)."""
        key = ("counts",) + tuple(sorted((k, round(float(v), 14)) for k, v in self._equivalent(params).items()))
        if key not in self._cache:
            run_events, w = self._weighted_events(params)
            out = {}
            for n, c in self.count_spec.items():
                sw, sw2 = self._hist(self.model, run_events, n, w[c["run"]])
                scale = self.exposure / self.model.runs[c["run"]].n
                out[n] = {"mu": sw * scale, "sumw": sw, "sumw2": sw2}
            self._cache[key] = out
        return self._cache[key]

    def _count_link(self, params: dict) -> np.ndarray:
        pr = self.counts_pred(params)
        rows = []
        for n, b in self._count_blocks.items():
            mu = np.maximum(pr[n]["mu"], 1e-300)
            rows.append(b.L @ np.log(mu) if b.free_omega else np.log(mu))
        return np.concatenate(rows)

    def _n_gauss(self):
        return len(self.names)

    def _shift_params(self, phis):
        out = {}
        for (n, (c, s)), v in zip(self.shift_spec.items(), np.atleast_1d(phis)):
            v = float(v)
            k2, k3 = self.shift_response.get(n, (0.0, 0.0))
            out[n] = c + s * (v + k2 * v * v + k3 * v ** 3)
        return out

    def h_shift(self, tp, phis):
        """The predictor with the shift-mode phi at centre + sigma phi_s (unit-normal coordinates, section 5.5)."""
        params, shift = self.params_of(tp)
        params = {**params, **self._shift_params(phis)}
        g = self._to_link(self._predict(params)["pred"]) + shift + self.pert
        return np.r_[g, self._count_link(params)] if self.count_spec else g

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
        if not self.names:
            return np.zeros((0, 0))
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
        if not self.names:                                # a fit of count observables only (e.g. BB-lite)
            pr = self.counts_pred(params)
            tau = {n: L.bb_tau(pr[n]["sumw"], pr[n]["sumw2"]) for n, c in self.count_spec.items() if c.get("bb")}
            nl = self.layout.n_link
            ref = L.Reference(V_G=np.zeros((0, 0)), V_std=np.zeros((0, 0)), U=np.zeros((nl, 0)),
                              S=np.zeros((nl, len(self.eta_spec))), tau=tau)
            ref.V_MC = np.zeros((0, 0))
            return ref.finalize()
        r = self._predict(params)
        mu = r["pred"]
        D = self._dlink(mu)
        V_mc = r["V_MC"] * np.outer(D, D)
        if frozen is not None:
            Vd = frozen.V_std
        else:
            Vd = self.bootstrap_vhat(params, self.boot_seed if bootstrap_seed is None else bootstrap_seed)
        S = self.eta_columns(mu)
        nl = self.layout.n_link
        if nl > S.shape[0]:                               # count rows: no eta columns (link-space shifts of scalars)
            S = np.vstack([S, np.zeros((nl - S.shape[0], S.shape[1]))])
        U = np.zeros((nl, 0))
        tau = {}
        if self.count_spec:
            pr = self.counts_pred(params)
            tau = {n: L.bb_tau(pr[n]["sumw"], pr[n]["sumw2"]) for n, c in self.count_spec.items() if c.get("bb")}
        ref = L.Reference(V_G=Vd + V_mc, V_std=Vd, U=U, S=S, tau=tau)
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
        return self._observe_weighted(self.ev, self.model, params, rng, self.names, self.exposure, self._to_link)

    def simulate(self, beta_truth, rng, phis=None, nominal: bool = True) -> L.Observations:
        """Toy data at the truth. nominal=True (toys under the null hypothesis, section 6.6): drawn from the nominal MC
        weighted to the truth; nominal=False (actual data, G8 pseudo-data with an analytic truth): a fresh event sample
        generated at the truth."""
        lay = self.layout
        sl = lay.slices()
        n0 = len(lay.theta) + len(lay.phi_P)
        params, shift = self.params_of(beta_truth[:n0])
        if phis is not None and self.shift_spec:          # the true shift-mode phi (section 6.6 item 1)
            params = {**params, **self._shift_params(phis)}
        counts = {}
        if self.count_spec:
            y, counts = self._observe_with_counts(params, rng, nominal)
        else:
            y = self.observe_nominal(params, rng) if nominal else self.observe_at(params, int(rng.integers(2 ** 62)))
        eta = beta_truth[sl["eta"]]
        if lay.n_eta:
            y = y + self.eta_columns(self._predict(params)["pred"]) @ eta
        y = y + shift
        phi0 = None
        if lay.phi_P:                            # constraint centres sampled around the true phi (section 6.6)
            sig = np.array([s for _, s in self.phi_spec.values()])
            phi0 = rng.normal(beta_truth[sl["phi_P"]], sig)
        return L.Observations(y_gauss=y, counts=counts, phi0=phi0, phi_cov=self.phi_cov(),
                      eta0=rng.normal(eta, 1.0) if lay.n_eta else None)

    def _observe_with_counts(self, params: dict, rng, nominal: bool):
        """Gaussian summaries and count observables of the same data events: runs hosting an absolute count observable
        have a Poisson(exposure) event total (an absolute count is Poisson), the others the fixed exposure."""
        by = {o.name: o for o in self.model.observables}
        runs = sorted({by[n].run for n in self.names} | {c["run"] for c in self.count_spec.values()})
        absolute = {c["run"] for c in self.count_spec.values() if c.get("kind", "absolute") == "absolute"}
        sizes = {r: (int(rng.poisson(self.exposure)) if r in absolute else self.exposure) for r in runs}
        picked = {}
        if nominal:
            run_events, w = self._weighted_events(params)
            for rid in runs:
                ww = np.asarray(w[rid], float)
                idx = rng.choice(ww.size, size=sizes[rid], replace=True, p=ww / ww.sum())
                picked[rid] = {nd: {k: np.asarray(v)[idx] for k, v in outs.items()} for nd, outs in run_events[rid].items()}
        else:
            ev = ChainEvaluator(self._data_model, {"seeds": {"nominal": 1}})
            gen = ev.generate(int(rng.integers(2 ** 62)), params={**self.model.nominal, **params})
            for rid in runs:
                evs = gen["runs"][rid]["events"]
                if sizes[rid] > self._data_model.runs[rid].n:
                    raise ValueError("the Poisson event total exceeds the generated data sample")
                picked[rid] = {nd: {k: np.asarray(v)[:sizes[rid]] for k, v in outs.items()} for nd, outs in evs.items()}
        y = np.zeros(0)
        if self.names:
            o = observe(self.model, picked, {r: np.ones(sizes[r]) for r in picked}, self.names)
            y = self._to_link(o["pred"])
        counts = {n: self._hist(self.model, picked, n)[0] for n in self.count_spec}
        return y, counts

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

    # -- validation observables (holdout and its toys, section 9.2)
    def _val_link(self, pred, names=None):
        names = names or self.val_names
        return np.array([L.link(np.array([v]), self.val_links[n])[0] for v, n in zip(pred, names)])

    def _val_dlink(self, pred):
        return np.array([L.dlink(np.array([v]), self.val_links[n])[0] for v, n in zip(pred, self.val_names)])

    def _val_predict(self, params: dict, ev=None) -> dict:
        params = self._equivalent(params)
        ev = ev or self.val_ev
        key = (id(ev), tuple(sorted((k, round(float(v), 14)) for k, v in params.items())))
        if key not in self._val_cache:
            if len(self._val_cache) > 4096:
                self._val_cache.clear()
            self._val_cache[key] = ev.evaluate(params, names=self.val_names)
        return self._val_cache[key]

    def h_val(self, tp, phis=None):
        """The validation predictor (link space) at theta, phi_P: the validation nominal MC plus its toy perturbation."""
        params, _ = self.params_of(tp)
        if phis is not None and self.shift_spec:
            params = {**params, **self._shift_params(phis)}
        return self._val_link(self._val_predict(params)["pred"]) + self.pert_val

    def _val_eta(self, mu) -> np.ndarray:
        cols = []
        for sj in self.eta_spec:
            col = np.zeros(len(self.val_names))
            for k, n in enumerate(self.val_names):
                r = float(sj.get("relative", {}).get(n, 0.0))
                if r:
                    col[k] = r if self.val_links[n] == "log" else r * mu[k] * self._val_dlink(np.array([mu[k]]))[0]
            cols.append(col)
        return np.stack(cols, axis=1) if cols else np.zeros((len(self.val_names), 0))

    def val_columns(self):
        """(U_v, S_v): the validation rows' nu columns (none: phi_P act through the evaluator) and eta columns."""
        params, _ = self.params_of(self._val_tp())
        return np.zeros((len(self.val_names), 0)), self._val_eta(self._val_predict(params)["pred"])

    def _val_tp(self):
        if self._val_point is not None:
            return self._val_point
        return np.r_[[0.5 * sum(v["prior"]) for v in self.theta_spec.values()], [c for c, _ in self.phi_spec.values()]]

    def set_val_point(self, tp):
        """The point at which the validation V_data and V_MC are evaluated (the nominal fit's theta-hat)."""
        self._val_point = np.asarray(tp, float).copy()
        self.__dict__.pop("_val_block", None)

    @property
    def val(self) -> dict:
        """Validation V_data (the event-level bootstrap of the validation sample at the validation point, per run),
        V_MC (link space) and constraints (none declared on the toy detector)."""
        if "_val_block" not in self.__dict__:
            params, _ = self.params_of(self._val_tp())
            r = self._val_predict(params)
            D = self._val_dlink(r["pred"])
            ev = ChainEvaluator(self._val_boot_model, {"seeds": {"nominal": 1}})
            gen = ev.generate(_seed_int((self.boot_seed, 7)), params={**self.model.nominal, **self._equivalent(params)})
            sets = per_set_summaries(self._val_boot_model, {k: v["events"] for k, v in gen["runs"].items()},
                                     self.val_names, self.B_val)
            Z = np.stack([L.link(sets[:, k], self.val_links[n]) for k, n in enumerate(self.val_names)], axis=1)
            vby = {o.name: o for o in self._val_model.observables}
            runs = [vby[n].run for n in self.val_names]
            Vd = np.zeros((len(runs), len(runs)))
            for rr in dict.fromkeys(runs):
                idx = [k for k, x in enumerate(runs) if x == rr]
                Vd[np.ix_(idx, idx)] = L.bootstrap_covariance(Z[:, idx])
            self.__dict__["_val_block"] = {"V_data": Vd, "V_MC": r["V_MC"] * np.outer(D, D), "constraints": []}
        return self.__dict__["_val_block"]

    def simulate_val(self, beta_truth, rng, phis=None, nominal: bool = True) -> np.ndarray:
        """Validation data at the truth: nominal=True draws from the validation nominal MC weighted to the truth (the
        toys' true value, section 6.6); nominal=False generates a fresh validation event sample (actual data)."""
        n0 = len(self.layout.theta) + len(self.layout.phi_P)
        params, _ = self.params_of(beta_truth[:n0])
        if phis is not None and self.shift_spec:
            params = {**params, **self._shift_params(phis)}
        if nominal:
            y = self._observe_weighted(self.val_ev, self._val_model, params, rng, self.val_names, self.val_exposure,
                                       self._val_link)
        else:
            ev = ChainEvaluator(self._val_data_model, {"seeds": {"nominal": 1}})
            gen = ev.generate(int(rng.integers(2 ** 62)), params={**self.model.nominal, **self._equivalent(params)})
            w = {k: np.ones(self._val_data_model.runs[k].n) for k in gen["runs"]}
            o = observe(self._val_data_model, {k: v["events"] for k, v in gen["runs"].items()}, w, self.val_names)
            y = self._val_link(o["pred"])
        lay = self.layout
        if lay.n_eta:
            eta = beta_truth[lay.slices()["eta"]]
            y = y + self._val_eta(self._val_predict(params)["pred"]) @ eta
        return y

    def replica_pert_val(self, rng) -> np.ndarray:
        """(m_a - m_b) / sqrt(2) of two independent validation nominal-MC samples at the generation point."""
        gen = {**self.model.nominal, **self.generation}
        sa, sb = int(rng.integers(2 ** 62)), int(rng.integers(2 ** 62))
        ma = self._val_link(self.val_ev.evaluate(gen, names=self.val_names, seeds={"nominal": sa})["pred"])
        mb = self._val_link(self.val_ev.evaluate(gen, names=self.val_names, seeds={"nominal": sb})["pred"])
        self.val_ev._other.pop(sa, None)
        self.val_ev._other.pop(sb, None)
        return (ma - mb) / math.sqrt(2.0)

    def _observe_weighted(self, ev, model, params, rng, names, exposure, to_link):
        target = {**model.nominal, **self._equivalent(params)}
        nom = ev.nominal
        run_events, regen = ev._prepared(target, nom)
        sample = {"runs": {rid: {"events": run_events[rid], "fractions": nom["runs"][rid].get("fractions")}
                           for rid in run_events}, "params": nom["params"], "sq": nom["sq"], "comps": nom["comps"]}
        w = ev.weights(target, sample, nodes=ev.reweighted_nodes(target, nom), regenerated=regen)
        w.pop("_missing_support", None)
        by = {o.name: o for o in model.observables}
        picked = {}
        for rid in sorted({by[n].run for n in names}):          # a fixed order of the draws (determinism)
            ww = np.asarray(w[rid], float)
            idx = rng.choice(ww.size, size=exposure, replace=True, p=ww / ww.sum())
            picked[rid] = {node: {k: np.asarray(v)[idx] for k, v in outs.items()} for node, outs in run_events[rid].items()}
        o = observe(model, picked, {r: np.ones(exposure) for r in picked}, names)
        return to_link(o["pred"])

    # -- cross-validation (section 9.3)
    def subset(self, rows):
        """The problem on the calibration rows `rows` (a training fold): the same detector, MC and bootstrap, the
        layout and data restricted to those rows."""
        rows = [int(r) for r in rows]
        p = ToyProblem.__new__(ToyProblem)
        p.__dict__.update(self.__dict__)
        p.names = [self.names[r] for r in rows]
        p.links = {n: self.links[n] for n in p.names}
        p.eta_spec = [{"relative": {n: v for n, v in sj.get("relative", {}).items() if n in p.names}}
                      for sj in self.eta_spec]
        obs = [{"name": n, "block": "gaussian", "link": p.links[n]} for n in p.names]
        p.layout = L.build_layout(obs, list(self.theta_spec), list(self.phi_spec), 0, len(self.eta_spec))
        p.pert = (np.asarray(self.pert)[rows] if np.ndim(self.pert) else self.pert)
        if self.observed is not None:
            p.observed = L.Observations(y_gauss=np.asarray(self.observed.y_gauss)[rows], phi0=self.observed.phi0,
                            phi_cov=self.observed.phi_cov, eta0=self.observed.eta0)
        p._cache = {}
        p._parent_rows = rows
        return p

    @property
    def d(self):
        return len(self.layout.theta)

    def with_data(self, observed: L.Observations, mc_seed=None):
        p = ToyProblem.__new__(ToyProblem)
        p.__dict__.update(self.__dict__)
        p.observed = observed
        p.pert = np.zeros(len(self.names))
        p.pert_val = np.zeros(len(self.val_names))
        if mc_seed is not None and mc_seed != self.mc_seed:
            p.mc_seed = mc_seed
            p.ev = ChainEvaluator(self.model, {**self.plan, "seeds": {"nominal": _seed_int(mc_seed)}})
            p._cache = {}
        return p

    def asimov(self, beta: np.ndarray) -> L.Observations:
        """Asimov data at beta (the prediction itself), for the design-stage gates."""
        lay = self.layout
        n0 = len(lay.theta) + len(lay.phi_P)
        params, shift = self.params_of(beta[:n0])
        y = (self._to_link(self._predict(params)["pred"]) + shift) if self.names else np.zeros(0)
        cen = np.array([c for c, _ in self.phi_spec.values()]) if self.phi_spec else None
        counts = {n: v["mu"] for n, v in self.counts_pred(params).items()} if self.count_spec else {}
        return L.Observations(y_gauss=y, counts=counts, phi0=cen, phi_cov=self.phi_cov(),
                      eta0=np.zeros(lay.n_eta) if lay.n_eta else None)

    def initial_beta(self, theta0: dict | None = None) -> np.ndarray:
        lay = self.layout
        b = np.zeros(lay.n_beta)
        sl = lay.slices()
        for i, (n, v) in enumerate(self.theta_spec.items()):
            b[i] = (theta0 or {}).get(n, 0.5 * sum(v["prior"]))
        if lay.phi_P:
            b[sl["phi_P"]] = [c for c, _ in self.phi_spec.values()]
        if lay.omega:                                     # free totals: the observed (or expected) total
            for i, n in enumerate(lay.omega):
                tot = float(np.sum(self.observed.counts[n])) if self.observed is not None and n in self.observed.counts else \
                    float(self.exposure)
                b[sl["omega"].start + i] = max(tot, 1.0)
        if lay.gamma:
            b[sl["gamma"]] = 1.0
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
        q = problem.with_data(problem.observed, mc_seed=(_seed_int(seed), k))
        vals.append(L.Likelihood(lay, problem.observed, ref).deviance(beta, q.h(beta[:n0])))
    return float(np.std(vals, ddof=1))
