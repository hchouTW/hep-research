"""The toy detector of Part B section 15.1 and the small chains the tests declare: a pure-Python (NumPy, SciPy) chain
simulator over a stage graph, with the evaluator interface of section 7.1.

Every node kernel draws from its own stored uniform streams (inverse-CDF sampling), so a re-evaluation with the same
seed uses common random numbers (section 6.6) and a resample with a new seed is independent. Density kernels give the
log density used by reweighting (section 3.6, 6.1); deterministic kernels are rerun from stored inputs; black-box
kernels are only resimulated. Everything here is `synthetic`: values from this module serve tests and design studies
only, never validation data (section 10.2)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import special, stats

from core.calibration import reweight

STATUS = ["synthetic"]


# ------------------------------------------------------------------ kernels
class Kernel:
    """A node kernel. kind: density | deterministic | black-box. `params` are the parameter names it reads;
    `density_params` those that act entirely through its density (section 6.1 item 3); `n_u` its uniform streams per
    event; `filtered` marks generation-time filtering (zero suppression: missing support, section 6.1)."""
    kind = "density"
    outputs: tuple = ()
    params: tuple = ()
    density_params: tuple = ()
    n_u = 1
    filtered = False

    def sample(self, par: dict, p: dict, u: np.ndarray, run: "Run") -> dict:
        raise NotImplementedError

    def logpdf(self, out: dict, par: dict, p: dict, run: "Run") -> np.ndarray:
        raise NotImplementedError(f"{type(self).__name__} has no density")

    def support(self, par: dict, p: dict, run: "Run") -> dict | None:
        """{output: (lo, hi)} per event, or None when unbounded / not restricted by the parameters."""
        return None


def _norm(u):
    return special.ndtri(np.clip(u, 1e-300, 1 - 1e-16))


def _poisson_ppf(u, mu):
    return stats.poisson.ppf(u, np.maximum(mu, 1e-300)).astype(float)


class Normal(Kernel):
    """x ~ N(loc, scale^2), loc = p[loc] (+ parent value), scale = p[scale] (x |loc| when relative)."""

    def __init__(self, out="x", loc=None, scale="sigma", parent=None, relative=False, const_loc=0.0):
        self.out, self.loc, self.scale, self.parent, self.relative, self.const_loc = out, loc, scale, parent, \
            relative, const_loc
        self.outputs = (out,)
        self.params = tuple(x for x in (loc, scale) if x)
        self.density_params = self.params

    def _loc_scale(self, par, p, n):
        loc = np.full(n, self.const_loc) + (p[self.loc] if self.loc else 0.0)
        if self.parent:
            loc = loc + par[self.parent]
        scale = p[self.scale] * (np.abs(loc) if self.relative else 1.0)
        return loc, scale

    def sample(self, par, p, u, run):
        loc, scale = self._loc_scale(par, p, u.shape[1])
        return {self.out: loc + scale * _norm(u[0])}

    def logpdf(self, out, par, p, run):
        loc, scale = self._loc_scale(par, p, len(out[self.out]))
        return stats.norm.logpdf(out[self.out], loc, scale)


class Uniform(Kernel):
    """x ~ U(p[lo], p[lo] + width): the U(theta, theta + 1) of the section 15.3.1 support test."""

    def __init__(self, out="x", lo="theta", width=1.0):
        self.out, self.lo, self.width = out, lo, width
        self.outputs, self.params, self.density_params = (out,), (lo,), (lo,)

    def sample(self, par, p, u, run):
        return {self.out: p[self.lo] + self.width * u[0]}

    def logpdf(self, out, par, p, run):
        x = out[self.out]
        inside = (x >= p[self.lo]) & (x <= p[self.lo] + self.width)
        return np.where(inside, -math.log(self.width), -np.inf)

    def support(self, par, p, run):
        n = run.n
        return {self.out: (np.full(n, p[self.lo]), np.full(n, p[self.lo] + self.width))}


class Poisson(Kernel):
    """n ~ Poisson(rate x parent) sampled, optionally with excess variance (Fano factor > 1: a negative binomial with
    the same mean, the "implementation includes ENF" of section 15.3.1). The density used for reweighting is the
    registered one (plan kernels[node].registration.density: poisson | negative-binomial)."""

    def __init__(self, out="n", rate="rate", parent=None, fano=1.0, registered="poisson"):
        self.out, self.rate, self.parent, self.fano, self.registered = out, rate, parent, fano, registered
        self.outputs, self.params, self.density_params = (out,), (rate,), (rate,)

    def _mu(self, par, p, n):
        base = par[self.parent] if self.parent else np.ones(n)
        return p[self.rate] * base

    def sample(self, par, p, u, run):
        mu = self._mu(par, p, u.shape[1])
        if self.fano > 1.0:                                   # negative binomial, mean mu, variance fano * mu
            prob = 1.0 / self.fano
            r = mu * prob / (1.0 - prob)
            return {self.out: stats.nbinom.ppf(u[0], np.maximum(r, 1e-300), prob).astype(float)}
        return {self.out: _poisson_ppf(u[0], mu)}

    def logpdf(self, out, par, p, run):
        mu = self._mu(par, p, len(out[self.out]))
        if self.registered == "negative-binomial" and self.fano > 1.0:
            prob = 1.0 / self.fano
            return stats.nbinom.logpmf(out[self.out], mu * prob / (1.0 - prob), prob)
        return stats.poisson.logpmf(out[self.out], mu)


class Binomial(Kernel):
    def __init__(self, out="k", n_parent="n", prob="eff"):
        self.out, self.n_parent, self.prob = out, n_parent, prob
        self.outputs, self.params, self.density_params = (out,), (prob,), (prob,)

    def sample(self, par, p, u, run):
        return {self.out: stats.binom.ppf(u[0], par[self.n_parent], p[self.prob]).astype(float)}

    def logpdf(self, out, par, p, run):
        return stats.binom.logpmf(out[self.out], par[self.n_parent], p[self.prob])


class GammaSum(Kernel):
    """Charge of N photoelectrons with gain G and excess noise factor F: Q | N ~ Gamma(N/(F-1), G(F-1)) (each
    photoelectron's gain has mean G and variance G^2 (F-1)); Q = 0 when N = 0."""

    def __init__(self, out="q", n_parent="n_pe", gain="gain", enf="enf"):
        self.out, self.n_parent, self.gain, self.enf = out, n_parent, gain, enf
        self.outputs, self.params, self.density_params = (out,), (gain, enf), (gain, enf)

    def _shape_scale(self, par, p):
        f = p[self.enf] - 1.0
        return par[self.n_parent] / f, p[self.gain] * f

    def sample(self, par, p, u, run):
        a, s = self._shape_scale(par, p)
        q = np.zeros_like(a)
        pos = a > 0
        q[pos] = stats.gamma.ppf(u[0][pos], a[pos]) * s
        return {self.out: q}

    def logpdf(self, out, par, p, run):
        a, s = self._shape_scale(par, p)
        q = out[self.out]
        lp = np.zeros_like(q)
        pos = a > 0
        lp[pos] = stats.gamma.logpdf(q[pos], a[pos], scale=s)
        lp[~pos] = np.where(q[~pos] == 0.0, 0.0, -np.inf)
        return lp


class Electronics(Kernel):
    """Two readout channels of the same charge, adc = q + N(0, noise^2), zero-suppressed below `threshold` (recorded
    as NaN: missing support for reweighting, section 6.1). The threshold changes the support and is not a density
    parameter; the noise width is, where no event is suppressed."""
    filtered = True
    n_u = 2

    def __init__(self, q_parent="q", noise="noise_width", threshold="threshold"):
        self.q_parent, self.noise, self.threshold = q_parent, noise, threshold
        self.outputs = ("adc_a", "adc_b")
        self.params, self.density_params = (noise, threshold), (noise,)

    def sample(self, par, p, u, run):
        q = par[self.q_parent]
        out = {}
        for k, name in enumerate(self.outputs):
            adc = q + p[self.noise] * _norm(u[k])
            out[name] = np.where(adc >= p[self.threshold], adc, np.nan)
        return out

    def logpdf(self, out, par, p, run):
        q = par[self.q_parent]
        lp = np.zeros(len(q))
        for name in self.outputs:
            lp = lp + stats.norm.logpdf(out[name], q, p[self.noise])   # NaN for a suppressed event
        return lp

    def support(self, par, p, run):
        n = len(par[self.q_parent])
        return {name: (np.full(n, p[self.threshold]), np.full(n, np.inf)) for name in self.outputs}


class Deposition(Kernel):
    """Black box (resimulation only): deposited energy E s_f exp(-t/lambda) (1 + sigma_d z), t the material thickness."""
    kind = "black-box"

    def __init__(self, e_parent="e", thickness="material_thickness", s_f=0.9, lam=10.0, sigma_d=0.02):
        self.e_parent, self.thickness, self.s_f, self.lam, self.sigma_d = e_parent, thickness, s_f, lam, sigma_d
        self.outputs, self.params = ("d",), (thickness,)

    def sample(self, par, p, u, run):
        e = par[self.e_parent]
        return {"d": np.maximum(e * self.s_f * math.exp(-p[self.thickness] / self.lam)
                                * (1.0 + self.sigma_d * _norm(u[0])), 0.0)}


class Steps(Kernel):
    """A multi-step process (step-level reweighting, section 3.6): n_steps steps, each keeping a fraction
    f ~ Beta(kappa x, kappa (1 - x)), x = p[keep]; per-step data stored. Output the remaining energy."""
    n_u = 0

    def __init__(self, keep="keep", n_steps=8, kappa=200.0, e0=1.0):
        self.keep, self.n_steps, self.kappa, self.e0 = keep, n_steps, kappa, e0
        self.n_u = n_steps
        self.outputs = ("remaining",) + tuple(f"step{i}" for i in range(n_steps))
        self.params, self.density_params = (keep,), (keep,)

    def sample(self, par, p, u, run):
        a, b = self.kappa * p[self.keep], self.kappa * (1 - p[self.keep])
        fr = stats.beta.ppf(u, a, b)
        out = {f"step{i}": fr[i] for i in range(self.n_steps)}
        out["remaining"] = self.e0 * np.prod(fr, axis=0)
        return out

    def step_logpdf(self, out, p):
        a, b = self.kappa * p[self.keep], self.kappa * (1 - p[self.keep])
        return np.stack([stats.beta.logpdf(out[f"step{i}"], a, b) for i in range(self.n_steps)])

    def logpdf(self, out, par, p, run):
        return self.step_logpdf(out, p).sum(axis=0)


class Fixed(Kernel):
    """A reference injection or a known input: fixed outputs, no parameter (section 3.4)."""
    kind = "deterministic"
    n_u = 0

    def __init__(self, **values):
        self.values = values
        self.outputs = tuple(values)

    def sample(self, par, p, u, run):
        return {k: np.full(run.n, float(v)) for k, v in self.values.items()}


class Function(Kernel):
    """A deterministic kernel y = fn(parents, p)."""
    kind = "deterministic"
    n_u = 0

    def __init__(self, outputs, fn, params=()):
        self.outputs, self.fn, self.params = tuple(outputs), fn, tuple(params)

    def sample(self, par, p, u, run):
        return self.fn(par, p)


# ------------------------------------------------------------------ model
@dataclass
class Run:
    id: str
    n: int
    kernels: dict                    # node -> Kernel (nodes absent from the run are not listed)
    parents: dict                    # node -> list of parent nodes within the run


@dataclass
class Observable:
    name: str
    run: str
    var: object                      # fn(events) -> values, events = {node: {output: array}}
    functional: str = "mean"         # mean | std | fraction
    mask: object = None              # fn(events) -> bool array: the events entering the observable (D41)
    tail: bool = False               # a tail-type functional (A7: P5/G4 decisions refused)


@dataclass
class Model:
    order: list                      # node ids, topological
    runs: dict                       # run id -> Run
    observables: list
    nominal: dict                    # parameter and constant values
    param_nodes: dict = field(default_factory=dict)   # parameter -> nodes it acts on
    status: list = field(default_factory=lambda: list(STATUS))


def descendants(run: Run, node: str) -> set:
    out, frontier = {node}, [node]
    while frontier:
        n = frontier.pop()
        for c, ps in run.parents.items():
            if n in ps and c not in out:
                out.add(c)
                frontier.append(c)
    return out


def _streams(seed: int, run_index: int, node_index: int, n_u: int, n: int) -> np.ndarray:
    rng = np.random.default_rng(np.random.SeedSequence([int(seed), run_index, node_index]))
    return rng.random((n_u, n)) if n_u else np.zeros((0, n))


def _parent_values(run: Run, events: dict, node: str) -> dict:
    out = {}
    for pn in run.parents.get(node, []):
        out.update(events[pn])
    return out


# ------------------------------------------------------------------ functionals
def functional(values: np.ndarray, w: np.ndarray, kind: str):
    """(estimate, per-event influence psi) of a weighted functional over the events given."""
    W = w.sum()
    if W <= 0 or len(values) == 0:
        return float("nan"), np.zeros_like(values)
    m = float((w * values).sum() / W)
    if kind in ("mean", "fraction"):
        return m, values - m
    if kind == "std":
        var = float((w * (values - m) ** 2).sum() / W)
        s = math.sqrt(max(var, 0.0))
        return s, ((values - m) ** 2 - var) / (2.0 * s if s > 0 else 1.0)
    raise ValueError(f"unknown functional {kind!r}")


def observe(model: Model, run_events: dict, run_weights: dict, names=None) -> dict:
    """Predictions, V_MC (joint, from per-event influence values with the weights), n_eff per observable over the
    events entering it (D41), and the per-run scaled per-event covariance used for the design-stage data errors."""
    if names is None:
        obs = list(model.observables)
    else:
        by_name = {o.name: o for o in model.observables}
        obs = [by_name[n] for n in names if n in by_name]
    k = len(obs)
    pred = np.zeros(k)
    n_eff = np.zeros(k)
    infl = {}                                                  # run -> (N_run, k) influence matrix
    s2 = np.zeros((k, k))
    per_event_var = np.zeros(k)
    weight_sum = {}
    samples = []
    for j, o in enumerate(obs):
        ev = run_events[o.run]
        w_all = run_weights[o.run]
        x = np.asarray(o.var(ev), dtype=float)
        if o.functional == "fraction":
            x = x.astype(float)
        m = np.ones(len(w_all), bool) if o.mask is None else np.asarray(o.mask(ev), bool)
        m &= np.isfinite(x)
        w = np.where(m, w_all, 0.0)
        W = w.sum()
        est, psi = functional(x[m], w[m], o.functional)
        pred[j] = est
        n_eff[j] = W ** 2 / max((w[m] ** 2).sum(), 1e-300)
        col = np.zeros(len(w_all))
        col[m] = w[m] * psi / W
        infl.setdefault(o.run, {})[j] = (col, W)
        weight_sum[o.run] = w_all.sum()
        per_event_var[j] = float((w[m] * psi ** 2).sum() / W)
        samples.append((x[m], w[m], o.functional))
    V = np.zeros((k, k))
    for run, cols in infl.items():
        js = sorted(cols)
        M = np.stack([cols[j][0] for j in js], axis=1)          # c_ik = w_i psi_ik / W_k
        w_all = run_weights[run]
        V[np.ix_(js, js)] = M.T @ M                            # V_MC = sum_i c_ik c_il
        # per-event covariance under the target, scaled so that V_data = s2 / N_data (section 6.7, design stage):
        # Cov(m_k, m_l) at exposure N = W_tot sum_i w_i psi_ik psi_il / (W_k W_l N) = W_tot sum_i c_ik c_il / w_i / N
        pos = w_all > 0
        inv_w = np.zeros_like(w_all)
        inv_w[pos] = 1.0 / w_all[pos]
        s2[np.ix_(js, js)] = weight_sum[run] * (M.T * inv_w) @ M
    return {"names": [o.name for o in obs], "pred": pred, "V_MC": V, "n_eff": n_eff, "s2": s2,
            "per_event_var": per_event_var, "influence": infl, "runs": [o.run for o in obs], "samples": samples}


# ------------------------------------------------------------------ evaluator
class ChainEvaluator:
    """The section 7.1 interface on a Model and a plan: nominal events generated at the plan's generation point with its
    proposal (mixture components on S_q), the plan's method per parameter, common random numbers per seed."""

    def __init__(self, model: Model, plan: dict):
        self.model = model
        spec = plan.get("evaluator", {})
        self.n_scale = float(spec.get("events_scale", 1.0))
        self.seeds = dict(plan.get("seeds") or {})
        self.seeds.setdefault("nominal", 20261110)
        self.methods = dict(plan.get("methods") or {})
        self.registration = {n: (k.get("registration") or {}) for n, k in (plan.get("kernels") or {}).items()}
        for node, reg in self.registration.items():
            for run in model.runs.values():
                kern = run.kernels.get(node)
                if isinstance(kern, Poisson) and reg.get("density"):
                    kern.registered = reg["density"]
        self.proposal = plan.get("proposal") or {}
        self.parameters = list(model.param_nodes)
        self.observables = [o.name for o in model.observables]
        self._nominal = None

    # ---- generation
    def default_method(self, par: str) -> str:
        if par in self.methods:
            return self.methods[par]
        kinds = {self._kernel_kind(n) for n in self.model.param_nodes.get(par, ())}
        if kinds == {"deterministic"}:
            return "rerun"
        if "black-box" in kinds:
            return "resimulation"
        return "analytic-reweighting"

    def _kernel_kind(self, node):
        for r in self.model.runs.values():
            if node in r.kernels:
                return r.kernels[node].kind
        return "deterministic"

    def _components(self):
        comps = self.proposal.get("components") or []
        nodes = list(self.proposal.get("nodes") or [])
        if not comps:
            return nodes, [{"theta": {}, "fraction": 1.0}]
        total = sum(float(c.get("fraction", 1.0)) for c in comps)
        return nodes, [dict(c, fraction=float(c.get("fraction", 1.0)) / total) for c in comps]

    def generate(self, seed: int, params: dict | None = None) -> dict:
        """Events of every run at the generation point; nodes of S_q drawn per mixture component (c_j = n_j / N)."""
        params = {**self.model.nominal, **(params or {})}
        sq, comps = self._components()
        sample = {}
        for ri, (rid, run) in enumerate(self.model.runs.items()):
            n = run.n
            sizes = _sizes(n, [c["fraction"] for c in comps])
            comp_index = np.repeat(np.arange(len(comps)), sizes)
            events, u = {}, {}
            for ni, node in enumerate(self.model.order):
                kern = run.kernels.get(node)
                if kern is None:
                    continue
                u[node] = _streams(seed, ri, ni, kern.n_u, n)
                events[node] = self._sample_node(run, node, kern, events, params, u[node], comp_index, comps, sq)
            sample[rid] = {"events": events, "u": u, "comp": comp_index}
        return {"runs": sample, "params": params, "seed": seed, "sq": sq, "comps": comps}

    def _sample_node(self, run, node, kern, events, params, u, comp_index, comps, sq):
        par = _parent_values(run, events, node)
        if node not in sq or len(comps) == 1 and not comps[0]["theta"]:
            return kern.sample(par, {**params, **(comps[0]["theta"] if node in sq else {})}, u, run)
        out = {k: np.empty(run.n) for k in kern.outputs}
        for j, c in enumerate(comps):
            sel = comp_index == j
            if not sel.any():
                continue
            sub_par = {k: v[sel] for k, v in par.items()}
            sub_run = Run(run.id, int(sel.sum()), run.kernels, run.parents)
            o = kern.sample(sub_par, {**params, **c["theta"]}, u[:, sel], sub_run)
            for k in out:
                out[k][sel] = o[k]
        return out

    @property
    def nominal(self):
        if self._nominal is None:
            self._nominal = self.generate(self.seeds["nominal"])
        return self._nominal

    # ---- the weight formula of section 3.6
    def weights(self, theta_target: dict, sample: dict | None = None, nodes=None, regenerated=()) -> dict:
        """w_i per run: numerator prod_{s in S_theta u S_q} K_s(x; theta'), denominator
        [sum_j c_j prod_{s in S_q} q_js] prod_{s in S_theta \\ S_q} K_s(x; theta_gen); nodes regenerated at theta' are
        drawn from the target and leave the formula (`regenerated`: a set, or {run: set} since a node may be
        regenerated in one run and not in another). `nodes` = S_theta (density nodes whose parameters change)."""
        sample = sample or self.nominal
        target = {**self.model.nominal, **theta_target}
        gen = sample["params"]
        comps = sample["comps"]
        base_nodes = nodes if nodes is not None else self.reweighted_nodes(target)
        out = {}
        for rid, run in self.model.runs.items():
            reg = regenerated.get(rid, set()) if isinstance(regenerated, dict) else set(regenerated)
            sq = [s for s in sample["sq"] if s not in reg]
            s_theta = [s for s in base_nodes if s not in reg]
            ev = sample["runs"][rid]["events"]
            n = run.n
            num = np.zeros(n)
            for s in sorted(set(s_theta) | set(sq)):
                kern = run.kernels.get(s)
                if kern is None or kern.kind != "density":
                    continue
                num += kern.logpdf(ev[s], _parent_values(run, ev, s), target, run)
            sq_run = [s for s in sq if run.kernels.get(s) is not None and run.kernels[s].kind == "density"]
            comp_terms = []
            for c in comps if sq_run else []:
                lp = np.zeros(n)
                for s in sq_run:
                    lp += run.kernels[s].logpdf(ev[s], _parent_values(run, ev, s), {**gen, **c["theta"]}, run)
                comp_terms.append(lp)
            outside = np.zeros(n)
            for s in s_theta:
                kern = run.kernels.get(s)
                if s in sq_run or kern is None or kern.kind != "density":
                    continue
                outside += kern.logpdf(ev[s], _parent_values(run, ev, s), gen, run)
            with np.errstate(invalid="ignore"):
                lw = reweight.log_weights(num, comp_terms, [c["fraction"] for c in comps], outside)
            miss = np.isnan(lw)
            if miss.any():                                     # a suppressed or unrecorded output: missing support
                out.setdefault("_missing_support", []).append(rid)
                lw = np.where(miss, -np.inf, lw)
            out[rid] = np.exp(lw)
        return out

    def reweighted_nodes(self, target: dict) -> list:
        nodes = set()
        for par, ns in self.model.param_nodes.items():
            if self.default_method(par) in ("analytic-reweighting", "step-level-reweighting") \
                    and not _same(target.get(par), self.nominal["params"].get(par)):
                nodes |= set(ns)
        return sorted(nodes)

    # ---- section 7.1 interface
    def evaluate(self, theta: dict, phi: dict | None = None, psi: dict | None = None, model: str = "nominal",
                 effects_off=(), seeds: dict | None = None, names=None) -> dict:
        """Prediction at theta with the plan's methods, outside to inside (section 6.5): resimulation from the most
        upstream resimulated node (common random numbers with the nominal events), rerun of deterministic kernels,
        reweighting of the remaining density nodes."""
        if model != "nominal":
            raise ValueError("alternative models of the toy detector are phase 2")
        target = {**self.model.nominal, **(phi or {}), **(psi or {}), **(theta or {})}
        nom = self.nominal
        changed = [p for p in self.model.param_nodes if not _same(target.get(p), nom["params"].get(p))]
        resim = [p for p in changed if self.default_method(p) in ("resimulation", "surrogate-model")]
        rw_nodes = sorted({n for p in changed if self.default_method(p) in ("analytic-reweighting",
                                                                             "step-level-reweighting")
                           for n in self.model.param_nodes[p]})
        run_events, regenerated_all = {}, {}
        for ri, (rid, run) in enumerate(self.model.runs.items()):
            ev = dict(nom["runs"][rid]["events"])
            start = [n for n in self.model.order if n in run.kernels
                     and set(run.kernels[n].params) & set(resim)]
            regen = set()
            for s0 in start:
                regen |= descendants(run, s0)
            for node in self.model.order:                      # one pass, outside to inside (section 6.5)
                kern = run.kernels.get(node)
                if kern is None:
                    continue
                if node in regen or kern.kind == "deterministic":   # resimulation (CRN) or rerun
                    ev[node] = kern.sample(_parent_values(run, ev, node), target, nom["runs"][rid]["u"][node], run)
            run_events[rid] = ev
            regenerated_all[rid] = regen
        sample = {"runs": {rid: {"events": run_events[rid]} for rid in run_events}, "params": nom["params"],
                  "sq": nom["sq"], "comps": nom["comps"]}
        w = self.weights(target, sample, nodes=rw_nodes, regenerated=regenerated_all)
        missing = w.pop("_missing_support", [])
        out = observe(self.model, run_events, w, names)
        out["node_diag"] = {n: _node_diag(w) for n in rw_nodes}
        out.update({"V_emu": None, "V_learn": None, "missing_support_runs": missing, "theta": target,
                    "methods": {p: self.default_method(p) for p in changed}})
        return out

    def resample(self, node: str, theta: dict, phi: dict | None, psi: dict | None, model: str, inputs,
                 seeds: dict) -> dict:
        """Direct sampling of `node` at theta from the given parent outputs (inputs: {run: events of the parents},
        None for the stored nominal ones), with new random numbers (seeds['resample'])."""
        target = {**self.model.nominal, **(phi or {}), **(psi or {}), **(theta or {})}
        out = {}
        for ri, (rid, run) in enumerate(self.model.runs.items()):
            kern = run.kernels.get(node)
            if kern is None:
                continue
            ev = inputs[rid] if inputs is not None else self.nominal["runs"][rid]["events"]
            u = _streams(seeds["resample"], ri, self.model.order.index(node) + 1000, kern.n_u, run.n)
            out[rid] = kern.sample(_parent_values(run, ev, node), target, u, run)
        return out

    def evaluate_from(self, node: str, samples: dict, theta: dict, phi: dict | None, psi: dict | None, model: str,
                      seeds: dict, names=None) -> dict:
        """Observables from the given output of `node` (per run), propagating downstream at theta with new random
        numbers (seeds['resample']); upstream events and their weights are the nominal ones (section 7.1, for P0)."""
        target = {**self.model.nominal, **(phi or {}), **(psi or {}), **(theta or {})}
        nom = self.nominal
        run_events = {}
        for ri, (rid, run) in enumerate(self.model.runs.items()):
            ev = dict(nom["runs"][rid]["events"])
            down = descendants(run, node) - {node} if node in run.kernels else set()
            for node2 in self.model.order:
                k2 = run.kernels.get(node2)
                if k2 is None:
                    continue
                if node2 == node:
                    ev[node2] = samples[rid]
                elif node2 in down:                            # downstream at theta with new random numbers
                    u = _streams(seeds["resample"], ri, self.model.order.index(node2) + 2000, k2.n_u, run.n)
                    ev[node2] = k2.sample(_parent_values(run, ev, node2), target, u, run)
                elif k2.kind == "deterministic":
                    ev[node2] = k2.sample(_parent_values(run, ev, node2), target, nom["runs"][rid]["u"][node2], run)
            run_events[rid] = ev
        regen = {rid: (descendants(run, node) if node in run.kernels else set()) for rid, run in self.model.runs.items()}
        upstream = self.reweighted_nodes(target)
        sample = {"runs": {rid: {"events": run_events[rid]} for rid in run_events}, "params": nom["params"],
                  "sq": nom["sq"], "comps": nom["comps"]}
        w = self.weights(target, sample, nodes=upstream, regenerated=regen)
        missing = w.pop("_missing_support", [])
        out = observe(self.model, run_events, w, names)
        out["missing_support_runs"] = missing
        return out

    def rerun(self, nodes, theta: dict, seed: int, names=None, params=None) -> dict:
        """resample + evaluate_from from the stored inputs of `nodes` (one node or several, e.g. one per branch): the
        reference prediction of P0 and of the reweighting-versus-rerun agreement (sections 8.2 note 1, 15.2). For one
        node it equals evaluate_from(node, resample(node, ...)) with the same seed. With `params`, each run starts at
        the most upstream of the given nodes whose kernel there reads one of the params (an injected reference
        replaces a node's kernel in some runs). Runs whose regenerated part
        starts at a generator node have new events: `independent_runs` (no pairing with the nominal events)."""
        nodes = [nodes] if isinstance(nodes, str) else list(nodes)
        target = {**self.model.nominal, **(theta or {})}
        nom = self.nominal
        run_events, independent, regen_all = {}, [], {}
        for ri, (rid, run) in enumerate(self.model.runs.items()):
            ev = dict(nom["runs"][rid]["events"])
            touched = [n for n in nodes if n in run.kernels
                       and (params is None or set(run.kernels[n].params) & set(params))]
            starts = [n for n in touched if not any(n in descendants(run, m) - {m} for m in touched)]
            regen = set()
            for n0 in starts:
                regen |= descendants(run, n0)
            for node in self.model.order:
                kern = run.kernels.get(node)
                if kern is None:
                    continue
                if node in regen:
                    offset = 1000 if node in starts else 2000
                    u = _streams(seed, ri, self.model.order.index(node) + offset, kern.n_u, run.n)
                    ev[node] = kern.sample(_parent_values(run, ev, node), target, u, run)
                elif kern.kind == "deterministic":
                    ev[node] = kern.sample(_parent_values(run, ev, node), target, nom["runs"][rid]["u"][node], run)
            if any(not run.parents.get(n) and run.kernels[n].kind != "deterministic" for n in starts):
                independent.append(rid)
            run_events[rid] = ev
            regen_all[rid] = regen
        upstream = self.reweighted_nodes(target)
        sample = {"runs": {rid: {"events": run_events[rid]} for rid in run_events}, "params": nom["params"],
                  "sq": nom["sq"], "comps": nom["comps"]}
        w = self.weights(target, sample, nodes=upstream, regenerated=regen_all)
        missing = w.pop("_missing_support", [])
        out = observe(self.model, run_events, w, names)
        out.update({"missing_support_runs": missing, "independent_runs": independent})
        return out

    def support_findings(self, par: str, points: list[dict], ignorable=()) -> list[dict]:
        """Section 6.1 for one parameter evaluated by reweighting: it acts entirely through the density of each of
        its nodes; no event of the nominal sample is filtered or zero-suppressed there (unless the plan records the
        filtering as ignorable); the proposal's support (the union over its mixture components) contains the target
        support at every point given (prior vertices and Sobol points)."""
        out, seen = [], set()
        nom = self.nominal
        sq, comps = nom["sq"], nom["comps"]

        def add(code, node, rid, msg):
            if (code, node) not in seen:
                seen.add((code, node))
                out.append({"code": code, "parameter": par, "node": node, "run": rid, "message": msg})
        for node in self.model.param_nodes.get(par, []):
            for rid, run in self.model.runs.items():
                kern = run.kernels.get(node)
                if kern is None or par not in kern.params:      # absent, or replaced by an injected reference
                    continue
                if kern.kind != "density" or par not in kern.density_params:
                    add("support.not_density_parameter", node, rid, f"{par} does not act entirely through the density "
                        f"of {node} (section 6.1 item 3)")
                    continue
                ev = nom["runs"][rid]["events"]
                if kern.filtered and node not in ignorable and any(np.isnan(ev[node][o]).any() for o in kern.outputs):
                    add("support.filtered", node, rid, f"events zero-suppressed or filtered at {node} in run {rid}: "
                        "missing support (section 6.1)")
                par_vals = _parent_values(run, ev, node)
                thetas = [c["theta"] for c in comps] if node in sq else [{}]
                gen = [kern.support(par_vals, {**nom["params"], **t}, run) for t in thetas]
                if gen[0] is None:
                    continue
                for pt in points:
                    tgt = kern.support(par_vals, {**nom["params"], **pt}, run)
                    for var, (lo, hi) in tgt.items():
                        if not _covered(lo, hi, [g[var] for g in gen]).all():
                            add("support.missing", node, rid, f"the proposal's support at {node} does not contain "
                                f"the target support at {pt} (supp q must contain the union over the prior)")
                            break
        return out

    def learned_closure(self, fold):
        raise NotImplementedError("learned density ratios are phase 5")

    def ask(self):
        raise NotImplementedError("ask/tell is phase 3")

    def tell(self, *args):
        raise NotImplementedError("ask/tell is phase 3")


def _covered(lo, hi, intervals) -> np.ndarray:
    """Per event: is [lo, hi] inside the union of the intervals [lo_j, hi_j]?"""
    L = np.stack([np.broadcast_to(i[0], np.shape(lo)) for i in intervals])
    H = np.stack([np.broadcast_to(i[1], np.shape(lo)) for i in intervals])
    order = np.argsort(L, axis=0)
    L, H = np.take_along_axis(L, order, 0), np.take_along_axis(H, order, 0)
    cur = np.array(lo, dtype=float)
    for j in range(L.shape[0]):
        reach = L[j] <= cur + 1e-12
        cur = np.where(reach, np.maximum(cur, H[j]), cur)
    return cur >= np.asarray(hi) - 1e-12


def _same(a, b):
    return a == b or (a is not None and b is not None and abs(float(a) - float(b)) <= 1e-15 * max(1.0, abs(b)))


def _sizes(n, fractions):
    raw = np.array(fractions) * n
    sizes = np.floor(raw).astype(int)
    sizes[: n - sizes.sum()] += 1
    return sizes


def _node_diag(w: dict) -> dict:
    allw = np.concatenate([v for v in w.values()]) if w else np.zeros(0)
    if allw.size == 0 or allw.sum() <= 0:
        return {"n_eff": 0.0, "pareto_k": None, "max_weight_fraction": None}
    return {"n_eff": float(allw.sum() ** 2 / (allw ** 2).sum()), "pareto_k": None,
            "max_weight_fraction": float(allw.max() / allw.sum())}


# ------------------------------------------------------------------ the toy detector (section 15.1)
TOY_NOMINAL = {
    "light_yield": 100.0, "pde": 0.25, "gain": 10.0, "enf": 1.2, "noise_width": 2.0, "threshold": 5.0,
    "material_thickness": 1.0, "relative_gain_b": 1.0, "momentum_scale": 1.0, "sum_term_a": 1.0, "sum_term_b": 0.5,
    "layer_b_offset": 0.0,
}
TOY_PARAM_NODES = {
    "light_yield": ["photon_generation"], "pde": ["pde"], "gain": ["gain"], "enf": ["gain"],
    "noise_width": ["electronics"], "threshold": ["electronics"], "material_thickness": ["deposition"],
    "relative_gain_b": ["module_b"], "momentum_scale": ["momentum_measurement"],
    "sum_term_a": ["momentum_measurement"], "sum_term_b": ["layer_b"], "layer_b_offset": ["layer_b"],
}
S_F, LAMBDA = 0.9, 10.0
C_CAL = TOY_NOMINAL["gain"] * TOY_NOMINAL["pde"] * TOY_NOMINAL["light_yield"] * S_F \
    * math.exp(-TOY_NOMINAL["material_thickness"] / LAMBDA)
BEAM_ENERGIES = (1.0, 2.0, 3.0, 4.0)
LIGHT_SOURCE_PHOTONS = 400
KAPPA_P = 0.01


class Momentum(Kernel):
    """Momentum measurement: p_meas ~ N(s p, (kappa a s p)^2); position at layer b before its intrinsic resolution,
    xb ~ N(x0, (5 a / p)^2) (multiple scattering); z3 ~ N(0, 1), passed to layer b (its intrinsic resolution)."""
    n_u = 3
    outputs = ("p_meas", "xb_true", "z3", "x0")
    params = ("momentum_scale", "sum_term_a")
    density_params = params

    def _parts(self, par, p):
        mom = par["p"]
        s, a = p["momentum_scale"], p["sum_term_a"]
        return s * mom, KAPPA_P * a * s * mom, par["x0"], 5.0 * a / mom

    def sample(self, par, p, u, run):
        mu_p, sd_p, mu_x, sd_x = self._parts(par, p)
        return {"p_meas": mu_p + sd_p * _norm(u[0]), "xb_true": mu_x + sd_x * _norm(u[1]), "z3": _norm(u[2]),
                "x0": par["x0"]}                               # the track position at layer a, passed through

    def logpdf(self, out, par, p, run):
        mu_p, sd_p, mu_x, sd_x = self._parts(par, p)
        return (stats.norm.logpdf(out["p_meas"], mu_p, sd_p) + stats.norm.logpdf(out["xb_true"], mu_x, sd_x)
                + stats.norm.logpdf(out["z3"]))


class TrackInput(Kernel):
    n_u = 2
    outputs = ("p", "x0")

    def __init__(self, p_ref):
        self.p_ref = p_ref

    def sample(self, par, p, u, run):
        return {"p": self.p_ref * (1 + 0.005 * _norm(u[0])), "x0": 10.0 * _norm(u[1])}

    def logpdf(self, out, par, p, run):
        return stats.norm.logpdf(out["p"], self.p_ref, 0.005 * self.p_ref) + stats.norm.logpdf(out["x0"], 0, 10.0)


def _calo(beam=None, light=None, spe=False, fano=1.0):
    k = {}
    if beam is not None:
        k["input"] = Normal("e", None, "beam_spread", relative=True, const_loc=beam)
        k["deposition"] = Deposition("e")
        k["photon_generation"] = Poisson("n_ph", "light_yield", parent="d", fano=fano)
    if light is not None:
        k["photon_generation"] = Fixed(n_ph=light)               # light source: known photon count on photon -> PDE
    if not spe:
        k["pde"] = Binomial("n_pe", "n_ph", "pde")
    else:
        k["pde"] = Fixed(n_pe=1)                                  # single photoelectron on PDE -> gain
    k["gain"] = GammaSum("q", "n_pe", "gain", "enf")
    k["electronics"] = Electronics("q")
    k["module_a"] = Function(("e_a", "hit_a"), lambda par, p: {
        "e_a": np.nan_to_num(par["adc_a"] / C_CAL, nan=0.0), "hit_a": np.isfinite(par["adc_a"])})
    k["module_b"] = Function(("e_b", "hit_b"), lambda par, p: {
        "e_b": np.nan_to_num(p["relative_gain_b"] * par["adc_b"] / C_CAL, nan=0.0), "hit_b": np.isfinite(par["adc_b"])},
        params=("relative_gain_b",))
    k["energy_ratio"] = Function(("ratio",), lambda par, p: {
        "ratio": np.where(par["hit_a"] & par["hit_b"], par["e_b"] / np.where(par["e_a"] > 0, par["e_a"], 1.0),
                          np.nan)})
    return k


def _track(p_ref):
    return {
        "track_input": TrackInput(p_ref),
        "momentum_measurement": Momentum(),
        "momentum": Function(("p_rec",), lambda par, p: {"p_rec": par["p_meas"]}),
        "layer_a": Function(("xa",), lambda par, p: {"xa": par["x0"]}),
        "layer_b": Function(("xb",), lambda par, p: {"xb": par["xb_true"] + p["layer_b_offset"]
                                                      + p["sum_term_b"] * par["z3"]},
                            params=("layer_b_offset", "sum_term_b")),
        "position_difference": Function(("dx",), lambda par, p: {"dx": par["xb"] - par["xa"]}),
    }


TOY_PARENTS = {
    "deposition": ["input"], "photon_generation": ["deposition"], "pde": ["photon_generation"], "gain": ["pde"],
    "electronics": ["gain"], "module_a": ["electronics"], "module_b": ["electronics"],
    "energy_ratio": ["module_a", "module_b"], "momentum_measurement": ["track_input"],
    "momentum": ["momentum_measurement"], "layer_a": ["momentum_measurement"], "layer_b": ["momentum_measurement"],
    "position_difference": ["layer_a", "layer_b"], "e_over_p": ["momentum", "module_a"],
}
TOY_ORDER = ["input", "deposition", "photon_generation", "pde", "gain", "electronics", "module_a", "module_b",
             "energy_ratio", "track_input", "momentum_measurement", "layer_a", "layer_b", "position_difference",
             "momentum", "e_over_p"]


def _run(rid, n, kernels):
    parents = {node: [p for p in TOY_PARENTS.get(node, []) if p in kernels] for node in kernels}
    return Run(rid, n, kernels, parents)


def _obs(name, run, node, var, functional="mean", mask=None):
    return Observable(name, run, lambda ev, node=node, var=var: ev[node][var], functional, mask)


def build_toy(n_events=40_000, variant="full", fano=1.0, runs_subset=None) -> Model:
    """The toy detector (section 15.1). variant full: calorimeter and track branches with the merge node E/p;
    subgraph: the calorimeter branch only, no merge node."""
    runs, obs = {}, []
    hit = (lambda ev: ev["module_a"]["hit_a"])
    for e in BEAM_ENERGIES:
        rid = f"beam{int(e)}"
        runs[rid] = _run(rid, n_events, _calo(beam=e, fano=fano))
        obs += [_obs(f"{rid}_e_mean", rid, "module_a", "e_a", mask=hit),
                _obs(f"{rid}_e_width", rid, "module_a", "e_a", "std", mask=hit),
                _obs(f"{rid}_ratio_mean", rid, "energy_ratio", "ratio")]
    runs["light"] = _run("light", n_events, _calo(light=LIGHT_SOURCE_PHOTONS))
    obs += [_obs("light_e_mean", "light", "module_a", "e_a", mask=hit),
            _obs("light_e_width", "light", "module_a", "e_a", "std", mask=hit)]
    runs["spe"] = _run("spe", n_events, _calo(spe=True))
    obs += [_obs("spe_e_mean", "spe", "module_a", "e_a", mask=hit),
            _obs("spe_e_width", "spe", "module_a", "e_a", "std", mask=hit),
            Observable("spe_efficiency", "spe", lambda ev: ev["module_a"]["hit_a"].astype(float), "fraction")]
    if variant == "full":
        for p_ref in (5.0, 2.0):
            rid = f"track{int(p_ref)}"
            runs[rid] = _run(rid, n_events, _track(p_ref))
            obs += [_obs(f"{rid}_p_mean", rid, "momentum", "p_rec"),
                    _obs(f"{rid}_p_width", rid, "momentum", "p_rec", "std"),
                    _obs(f"{rid}_dx_mean", rid, "position_difference", "dx"),
                    _obs(f"{rid}_dx_width", rid, "position_difference", "dx", "std")]
        k = {**_calo(beam=4.0, fano=fano), **_track(4.0)}
        k["e_over_p"] = Function(("eop",), lambda par, p: {
            "eop": np.where(par["hit_a"], par["e_a"] / par["p_rec"], np.nan)})
        runs["eop"] = _run("eop", n_events, k)
        obs.append(_obs("eop_mean", "eop", "e_over_p", "eop"))
    if runs_subset is not None:
        runs = {r: v for r, v in runs.items() if r in runs_subset}
        obs = [o for o in obs if o.run in runs]
    nominal = dict(TOY_NOMINAL, beam_spread=0.01)
    param_nodes = {p: ns for p, ns in TOY_PARAM_NODES.items()
                   if any(n in r.kernels for r in runs.values() for n in ns)}
    return Model(TOY_ORDER, runs, obs, nominal, param_nodes)


def toy_detector(spec: dict, plan: dict) -> ChainEvaluator:
    model = build_toy(int(spec.get("events", 40_000)), "full", float(spec.get("photon_fano", 1.0)),
                      spec.get("runs"))
    return ChainEvaluator(model, plan)


def toy_detector_subgraph(spec: dict, plan: dict) -> ChainEvaluator:
    return ChainEvaluator(build_toy(int(spec.get("events", 40_000)), "subgraph", float(spec.get("photon_fano", 1.0)),
                                    spec.get("runs")), plan)


# ------------------------------------------------------------------ bimodal variant
def toy_detector_bimodal(spec: dict, plan: dict) -> ChainEvaluator:
    """The overlapping modules read out as a sum, S = a f + b (1 - f) + eps, f ~ Beta(alpha, beta), eps ~ N(0, s^2):
    a symmetric Beta gives two exactly degenerate mirror basins (section 15.1; used by G1 in phase 2)."""
    alpha, beta = float(spec.get("alpha", 2.0)), float(spec.get("beta", 2.0))
    s = float(spec.get("s", 0.05))
    n = int(spec.get("events", 40_000))

    class Mix(Kernel):
        kind = "black-box"
        n_u = 2
        outputs = ("S",)
        params = density_params = ("a", "b")

        def sample(self, par, p, u, run):
            f = stats.beta.ppf(u[0], alpha, beta)
            return {"S": p["a"] * f + p["b"] * (1 - f) + s * _norm(u[1])}

    run = Run("sum", n, {"modules": Mix()}, {"modules": []})
    obs = [Observable("sum_mean", "sum", lambda ev: ev["modules"]["S"], "mean"),
           Observable("sum_width", "sum", lambda ev: ev["modules"]["S"], "std"),
           Observable("sum_m3", "sum", lambda ev: (ev["modules"]["S"] - ev["modules"]["S"].mean()) ** 3, "mean")]
    return ChainEvaluator(Model(["modules"], {"sum": run}, obs, {"a": 1.0, "b": 0.6}, {"a": ["modules"],
                                                                                         "b": ["modules"]}), plan)


# ------------------------------------------------------------------ small declared chains (tests, single gates)
CATALOG = {"normal": Normal, "uniform": Uniform, "poisson": Poisson, "binomial": Binomial, "gamma-sum": GammaSum,
           "steps": Steps}


def chain_from_spec(spec: dict, plan: dict) -> ChainEvaluator:
    """A chain declared in the plan: spec = {nodes: [{id, kernel, args, parents}], runs: [{id, n}], observables:
    [{name, run, node, var, functional}], nominal: {...}, param_nodes: {...}}. Used by the negative tests of the
    single gates (section 15.3, "single-gate isolation mode")."""
    spec = spec.get("spec", spec)
    order = [n["id"] for n in spec["nodes"]]
    runs = {}
    for r in spec.get("runs", [{"id": "run", "n": 20_000}]):
        kernels = {n["id"]: CATALOG[n["kernel"]](**n.get("args", {})) for n in spec["nodes"]}
        parents = {n["id"]: list(n.get("parents", [])) for n in spec["nodes"]}
        runs[r["id"]] = Run(r["id"], int(r["n"]), kernels, parents)
    obs = [Observable(o["name"], o["run"], (lambda ev, o=o: ev[o["node"]][o["var"]]), o.get("functional", "mean"),
                      tail=bool(o.get("tail", False))) for o in spec["observables"]]
    return ChainEvaluator(Model(order, runs, obs, dict(spec["nominal"]), dict(spec["param_nodes"])), plan)
