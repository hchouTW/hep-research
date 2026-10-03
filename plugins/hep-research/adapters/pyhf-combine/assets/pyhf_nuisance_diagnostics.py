#!/usr/bin/env python3
"""Post-fit nuisance-parameter diagnostics for a pyhf workspace: pulls and constraints, pre- and post-fit impacts
on the parameter of interest, a ranking, a grouped uncertainty breakdown and the large nuisance correlations.

Purpose: the executable form of the "post-fit nuisance diagnostics" section of
${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/references/nuisance-modeling.md. It is a diagnostic around pyhf, not a
fitting framework: the likelihood, the fits and the interpolation codes are pyhf's (Model defaults unless the
workspace says otherwise). Needs pyhf (tested with 0.7.6, numpy backend, scipy optimizer).

Conventions (each echoed in the output):
  pull         (theta_hat - theta_0) / sigma_prefit, with theta_0 the auxiliary datum (nominal) and sigma_prefit the
               constraint width: 1 for normsys/histosys, the staterror width, and 1/sqrt(tau) for Poisson-constrained
               (shapesys) factors, which is a Gaussian approximation and flagged as such.
  constraint   sigma_postfit / sigma_prefit, sigma_postfit from the inverse numerical Hessian of -ln L at the best fit.
  impact       the POI shift when one nuisance component is fixed at theta_hat +- sigma_prefit (pre-fit impact) or
               theta_hat +- sigma_postfit (post-fit impact) and every other free parameter is refitted. Signs kept.
  ranking      by max(|post-fit up|, |post-fit down|).
  breakdown    for each declared group, sigma_group = sqrt(sigma_total^2 - sigma_frozen^2), with the group fixed at its
               best-fit values and the POI uncertainty recomputed from the Hessian of the refitted model; a sequential
               decomposition in the given and in the reversed order; and the closure of the quadrature sum against
               the total. Decompositions depend on method and order: report them as such.
  correlations nuisance pairs with |rho| above --corr-threshold (default 0.5 [Proposal]); |rho| > 0.95 is a warning
               (near-degenerate directions).
Unconstrained parameters (normfactor, shapefactor, lumi with no aux) have no pre-fit width: no pull and no pre-fit
impact, but a post-fit impact. A refit that fails is listed with status "failed", never dropped.

Usage: python3 pyhf_nuisance_diagnostics.py WORKSPACE.json [--measurement NAME] [--groups GROUPS.json]
                                          [--corr-threshold 0.5] [--json OUT.json]
  GROUPS.json: {"group name": ["parameter name", ...], ...} (names as in the pyhf parameter order; a multi-bin
  modifier name stands for all its components).
Output: JSON (stdout, or --json) and a text table (stdout with --json). No random numbers are used; the output
records "seed": null and the pyhf version.
Exit codes: 0 ok; 1 the nominal fit failed or a requested refit failed; 2 rejected input or pyhf not installed.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

try:
    import numpy as np
    import pyhf
except ImportError:  # pragma: no cover - exercised by the test that hides pyhf
    np = pyhf = None

TOLERANCE = 1e-10


def _components(model):
    """One row per scalar parameter: name, owner set, index, kind, theta_0, sigma_prefit, gaussian flag."""
    rows = []
    for name in model.config.par_order:
        ps = model.config.param_set(name)
        sl = model.config.par_slice(name)
        n = ps.n_parameters
        for k, idx in enumerate(range(sl.start, sl.stop)):
            label = name if n == 1 else f"{name}[{k}]"
            row = {"name": label, "set": name, "index": idx, "constrained": bool(ps.constrained),
                   "theta_0": None, "sigma_prefit": None, "gaussian": None}
            if ps.constrained:
                aux = list(ps.auxdata)
                if getattr(ps, "pdf_type", None) == "poisson":
                    tau = float(ps.factors[k])
                    row.update(theta_0=aux[k] / tau, sigma_prefit=1 / math.sqrt(tau), gaussian=False)
                else:
                    sig = ps.sigmas[k] if getattr(ps, "sigmas", None) is not None else 1.0
                    row.update(theta_0=float(aux[k]), sigma_prefit=float(sig), gaussian=True)
            rows.append(row)
    return rows


def _fit(data, model, fixed=None, init=None):
    fixed_params = list(model.config.suggested_fixed())
    init_pars = list(model.config.suggested_init() if init is None else init)
    for idx, value in (fixed or {}).items():
        fixed_params[idx] = True
        init_pars[idx] = value
    pars, twice_nll = pyhf.infer.mle.fit(data, model, init_pars=init_pars, fixed_params=fixed_params,
                                         return_fitted_val=True)
    return np.asarray(pars, float), float(twice_nll) / 2.0


def _hessian(data, model, p, free):
    """Central-difference Hessian of -ln L in the free parameters."""
    def nll(q):
        return -float(model.logpdf(q, data)[0])
    lo_b = [b[0] for b in model.config.suggested_bounds()]
    hi_b = [b[1] for b in model.config.suggested_bounds()]
    h = [max(1e-4, 1e-4 * abs(p[i])) for i in free]
    n = len(free)
    H = np.zeros((n, n))
    for a in range(n):
        for b in range(a, n):
            i, j = free[a], free[b]
            val = 0.0
            for si, sj, w in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)):
                q = np.array(p, float)
                q[i] += si * h[a]
                q[j] += sj * h[b]
                val += w * nll(q)
            H[a, b] = H[b, a] = val / (4 * h[a] * h[b])
    at_bound = [model.config.par_names[i] if hasattr(model.config, "par_names") else i
                for i in free if p[i] - h[free.index(i)] < lo_b[i] or p[i] + h[free.index(i)] > hi_b[i]]
    return H, at_bound


def _covariance(data, model, p, fixed_idx=()):
    free = [i for i, f in enumerate(model.config.suggested_fixed()) if not f and i not in set(fixed_idx)]
    H, at_bound = _hessian(data, model, p, free)
    eig = np.linalg.eigvalsh(H)
    if eig.min() <= 0:
        return None, free, at_bound, float(eig.min())
    cov = np.linalg.inv(H)
    return cov, free, at_bound, float(eig.min())


def diagnostics(spec, measurement=None, groups=None, corr_threshold=0.5):
    pyhf.set_backend("numpy", pyhf.optimize.scipy_optimizer(tolerance=TOLERANCE))
    ws = pyhf.Workspace(spec)
    model = ws.model(measurement_name=measurement) if measurement else ws.model()
    data = ws.data(model)
    poi = model.config.poi_index
    poi_name = model.config.poi_name
    comps = _components(model)
    out = {"tool": "pyhf_nuisance_diagnostics", "pyhf_version": pyhf.__version__, "seed": None,
           "poi": poi_name, "conventions": {
               "pull": "(theta_hat - theta_0) / sigma_prefit",
               "constraint": "sigma_postfit / sigma_prefit (inverse numerical Hessian)",
               "impact": "POI shift with the nuisance fixed at theta_hat +- sigma and all other free parameters refitted",
               "breakdown": "sqrt(sigma_total^2 - sigma_frozen^2), group fixed at best fit, Hessian of the refit",
               "corr_threshold": corr_threshold},
           "status": "ok", "failures": [], "warnings": []}
    try:
        p_hat, nll_hat = _fit(data, model)
    except Exception as exc:  # pyhf raises FailedMinimization
        out.update(status="failed", failures=[{"fit": "nominal", "error": str(exc)}])
        return out, 1
    cov, free, at_bound, min_eig = _covariance(data, model, p_hat)
    if cov is None:
        out.update(status="failed", failures=[{"fit": "nominal Hessian", "error": f"not positive definite (min eigenvalue {min_eig:.3g})"}])
        return out, 1
    if at_bound:
        out["warnings"].append(f"parameters within one Hessian step of a bound: {at_bound}; errors there are unreliable")
    sig_post = {i: math.sqrt(cov[k, k]) for k, i in enumerate(free)}
    sigma_total = sig_post[poi]
    out["best_fit"] = {"poi_hat": float(p_hat[poi]), "poi_sigma_hessian": sigma_total, "nll": nll_hat}

    rows = []
    for c in comps:
        i = c["index"]
        if i == poi or i not in sig_post:
            continue
        r = {"name": c["name"], "theta_hat": float(p_hat[i]), "sigma_postfit": sig_post[i], "constrained": c["constrained"]}
        if c["constrained"]:
            r["pull"] = (p_hat[i] - c["theta_0"]) / c["sigma_prefit"]
            r["constraint"] = sig_post[i] / c["sigma_prefit"]
            r["sigma_prefit"] = c["sigma_prefit"]
            if not c["gaussian"]:
                r["note"] = "Poisson constraint: the Gaussian pull scale is an approximation"
        else:
            r["note"] = "unconstrained: no pre-fit width, no pull, no pre-fit impact"
        impacts = {}
        kinds = [("postfit", sig_post[i])] + ([("prefit", c["sigma_prefit"])] if c["constrained"] else [])
        for kind, s in kinds:
            for sign, label in ((1, "up"), (-1, "down")):
                try:
                    p_fix, _ = _fit(data, model, fixed={i: float(p_hat[i] + sign * s)}, init=p_hat)
                    impacts[f"{kind}_{label}"] = float(p_fix[poi] - p_hat[poi])
                except Exception as exc:
                    impacts[f"{kind}_{label}"] = None
                    out["failures"].append({"fit": f"{c['name']} {kind} {label}", "status": "failed", "error": str(exc)})
        r["impacts"] = impacts
        rows.append(r)
    ranked = sorted(rows, key=lambda r: -max(abs(r["impacts"].get("postfit_up") or 0),
                                               abs(r["impacts"].get("postfit_down") or 0)))
    out["nuisances"] = ranked
    out["ranking"] = [r["name"] for r in ranked]

    # correlations among nuisance components
    idx_name = {c["index"]: c["name"] for c in comps}
    pairs = []
    for a in range(len(free)):
        for b in range(a + 1, len(free)):
            i, j = free[a], free[b]
            if poi in (i, j):
                continue
            rho = cov[a, b] / math.sqrt(cov[a, a] * cov[b, b])
            if abs(rho) > corr_threshold:
                pairs.append({"pair": [idx_name[i], idx_name[j]], "rho": float(rho)})
                if abs(rho) > 0.95:
                    out["warnings"].append(f"near-degenerate nuisances {idx_name[i]} and {idx_name[j]} (rho = {rho:.3f})")
    out["correlations"] = sorted(pairs, key=lambda x: -abs(x["rho"]))
    out["poi_correlations"] = sorted(({"name": idx_name[i], "rho": float(cov[free.index(poi), k] / math.sqrt(cov[k, k] * cov[free.index(poi), free.index(poi)]))}
                                      for k, i in enumerate(free) if i != poi), key=lambda x: -abs(x["rho"]))

    if groups:
        out["breakdown"] = _breakdown(data, model, p_hat, comps, groups, sigma_total, out)
    if out["failures"]:
        out["status"] = "failed"
        return out, 1
    return out, 0


def _expand(model, comps, names):
    idx = []
    for n in names:
        hit = [c["index"] for c in comps if c["set"] == n or c["name"] == n]
        if not hit:
            raise ValueError(f"unknown parameter in groups: {n}")
        idx += hit
    return idx


def _sigma_frozen(data, model, p_hat, idx, out, label):
    poi = model.config.poi_index
    try:
        p, _ = _fit(data, model, fixed={i: float(p_hat[i]) for i in idx}, init=p_hat)
    except Exception as exc:
        out["failures"].append({"fit": f"breakdown {label}", "status": "failed", "error": str(exc)})
        return None
    cov, free, _, min_eig = _covariance(data, model, p, idx)
    if cov is None:
        out["failures"].append({"fit": f"breakdown {label} Hessian", "status": "failed", "error": f"min eigenvalue {min_eig:.3g}"})
        return None
    return math.sqrt(cov[free.index(poi), free.index(poi)])


def _breakdown(data, model, p_hat, comps, groups, sigma_total, out):
    nuis = [c["index"] for c in comps if c["index"] != model.config.poi_index and not model.config.suggested_fixed()[c["index"]]]
    res = {"sigma_total": sigma_total, "freeze_one": {}, "sequential": {}}
    for g, names in groups.items():
        s = _sigma_frozen(data, model, p_hat, _expand(model, comps, names), out, g)
        res["freeze_one"][g] = None if s is None else math.sqrt(max(sigma_total ** 2 - s ** 2, 0.0))
    s_stat = _sigma_frozen(data, model, p_hat, nuis, out, "all nuisances")
    res["sigma_stat_all_frozen"] = s_stat
    for order_name, order in (("given", list(groups)), ("reversed", list(groups)[::-1])):
        frozen, prev, seq = [], sigma_total, {}
        for g in order:
            frozen += _expand(model, comps, groups[g])
            s = _sigma_frozen(data, model, p_hat, frozen, out, f"sequential {g}")
            seq[g] = None if s is None or prev is None else math.sqrt(max(prev ** 2 - s ** 2, 0.0))
            prev = s
        res["sequential"][order_name] = seq
    vals = [v for v in res["freeze_one"].values() if v is not None]
    if s_stat is not None and len(vals) == len(groups):
        quad = math.sqrt(sum(v * v for v in vals) + s_stat ** 2)
        res["closure"] = {"quadrature_sum_with_stat": quad, "ratio_to_total": quad / sigma_total,
                          "note": "freeze-one groups plus the all-frozen statistical part in quadrature; a ratio away "
                                  "from 1 means the groups are correlated and the decomposition is not unique"}
    return res


def table(out):
    lines = [f"POI {out['poi']} = {out['best_fit']['poi_hat']:.5g} +- {out['best_fit']['poi_sigma_hessian']:.3g} "
             f"(pyhf {out['pyhf_version']}, status {out['status']})",
             f"{'nuisance':32s} {'pull':>8s} {'constr':>7s} {'pre+':>9s} {'pre-':>9s} {'post+':>9s} {'post-':>9s}"]

    def f(x):
        return f"{x:9.4f}" if isinstance(x, float) else f"{'-':>9s}"
    for r in out["nuisances"]:
        im = r["impacts"]
        lines.append(f"{r['name'][:32]:32s} {f(r.get('pull'))[1:]:>8s} {f(r.get('constraint'))[2:]:>7s} "
                     f"{f(im.get('prefit_up'))} {f(im.get('prefit_down'))} {f(im.get('postfit_up'))} {f(im.get('postfit_down'))}")
    for w in out["warnings"]:
        lines.append(f"warning: {w}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("workspace")
    parser.add_argument("--measurement")
    parser.add_argument("--groups")
    parser.add_argument("--corr-threshold", type=float, default=0.5)
    parser.add_argument("--json", dest="json_out")
    args = parser.parse_args(argv)
    if pyhf is None:
        print(json.dumps({"status": "failed", "error": "pyhf not installed: these diagnostics need pyhf (tested 0.7.6)"}))
        return 2
    try:
        with open(args.workspace, encoding="utf-8") as fh:
            spec = json.load(fh)
        groups = None
        if args.groups:
            with open(args.groups, encoding="utf-8") as fh:
                groups = json.load(fh)
            if not isinstance(groups, dict) or not all(isinstance(v, list) and v for v in groups.values()):
                raise ValueError("groups must map a name to a non-empty list of parameter names")
        if not 0 < args.corr_threshold < 1:
            raise ValueError("--corr-threshold must be in (0, 1)")
        out, code = diagnostics(spec, args.measurement, groups, args.corr_threshold)
    except (OSError, ValueError, KeyError, pyhf.exceptions.InvalidSpecification) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    text = json.dumps(out, indent=1)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        if "best_fit" in out:
            print(table(out))
    else:
        print(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
