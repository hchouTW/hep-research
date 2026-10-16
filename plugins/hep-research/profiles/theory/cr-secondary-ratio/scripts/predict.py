#!/usr/bin/env python3
"""Predictions of theory:cr-secondary-ratio: a stable secondary-to-primary ratio (B/C) in two propagation models.

Models (derivation in ../derivations/derivation-record.md, checked by derive.py):

* weighted-slab (leaky box): exponential path-length distribution with mean grammage lambda_esc(R);
  ratio = sum_j (sigma_{j->s}/m_H) r_j / (1/lambda_esc(R_s) + sigma_s/m_H), r_j the observed parent ratio N_j/N_ref.
* diffusion-1d (thin disc of half-thickness h and hydrogen density n_H, halo |z| < L with N(+-L) = 0, no convection,
  no reacceleration, no energy losses or decay): at the mid-plane
  ratio = sum_j sigma_{j->s} r_j / (sigma_s + D(R_s) / (h n_H v L)), D(R) = D0 beta (R/R0)^delta. This is the
  weighted slab with lambda_esc = n_H m_H h v L / D, so the ratio depends on D0 and L only through D0/L.

Two numerical cross-checks of the closed forms (the profile benchmark, no external program): the slab ODEs integrated
and averaged over the path-length distribution (slab_ratio_numerical), and the 1D equation with a disc of finite
thickness solved exactly (halo_finite_disc_exact) and by finite differences (halo_finite_disc_fd), which tend to the
thin-disc closed form as h/L -> 0.

Calling it for an arbitrary parameter point (for grids): evaluate(config, overrides) returns the ratio at the
config's energies for the parameters in config["transport"] (or config["leaky_box"]) updated by `overrides`, e.g.
evaluate(cfg, {"D0_cm2_s": 2e28, "L_kpc": 6.0}); grid(cfg, {"D0_cm2_s": [...], "L_kpc": [...]}) evaluates the
Cartesian product (row-major, last axis fastest); bin_averaged(cfg, edges, overrides) gives the ratio averaged in
ln(E/n) over bins, the form stored in the prediction artifact. Every input set in this profile is ILLUSTRATIVE (synthetic
cross sections and transport values); a prediction from them is not a statement about the Galaxy.

Usage:
  python3 predict.py [--config ../benchmarks/bc-benchmark.json] [--set D0_cm2_s=2e28 --set L_kpc=6] [--out P.json]
  python3 predict.py --grid D0_cm2_s=1e28,2e28,4e28 --grid L_kpc=2,4,8 [--out GRID.json]
  python3 predict.py --benchmark      # closed forms against the numerical solutions; exit 1 if a check fails
Exit codes: 0 ok, 1 a check failed, 2 bad input (JSON "error" on stdout), 3 a required package (numpy/scipy) missing.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent
PLUGIN_ROOT = PROFILE.parents[2]
sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(PLUGIN_ROOT))
from core.kinematics.relativistic import Species, beta, convert, to_momentum  # noqa: E402

DEFAULT_CONFIG = PROFILE / "benchmarks" / "bc-benchmark.json"

# Constants (crsr:C05): speed of light (exact), parsec = 648000/pi au (IAU 2012 au), CODATA 2018
# atomic mass unit and proton mass; 1 mb = 1e-27 cm^2.
C_CM_S = 2.99792458e10
KPC_CM = 3.0856775814913673e21
M_U_GEV = 0.93149410242
M_H_G = 1.67262192369e-24  # target mass: proton mass (electron and binding neglected)
MB_CM2 = 1e-27

TRANSPORT_KEYS = ("D0_cm2_s", "L_kpc", "h_kpc", "n_H_cm3", "delta", "R0_GV")
LEAKY_BOX_KEYS = ("lambda0_g_cm2", "delta", "R0_GV")


class InputError(ValueError):
    """A config, override or cross-section set that cannot be used."""


# ---------------------------------------------------------------- inputs

def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_cross_sections(cfg: dict, which: str | None = None) -> dict:
    """The cross-section set named by `which` (a path relative to the profile) or the config's nominal set."""
    xs = load_json(PROFILE / (which or cfg["cross_section_set"]))
    for key in ("production_mb", "inelastic_mb"):
        if not isinstance(xs.get(key), dict):
            raise InputError(f"cross-section set lacks '{key}'")
    return xs


def _species(entry: dict) -> Species:
    return Species(Z=int(entry["Z"]), A=int(entry["A"]), mass=int(entry["A"]) * M_U_GEV)


def kinematics(e_n: float, entry: dict) -> tuple[float, float]:
    """(rigidity in GV, beta) of a nucleus of the given A, Z at kinetic energy per nucleon e_n (GeV/n).

    Mass convention: A times the atomic mass unit (binding energy neglected), so beta at fixed E/n is the same for
    every species. The conversion is core/kinematics/relativistic.py; no second converter here."""
    sp = _species(entry)
    rig = convert(e_n, "kinetic_energy_per_nucleon", "rigidity", sp)
    return rig, beta(to_momentum(e_n, "kinetic_energy_per_nucleon", sp), sp.need_mass())


def _sigma(xs: dict, table: str, key: str) -> float:
    try:
        val = float(xs[table][key])
    except KeyError as exc:
        raise InputError(f"cross-section set has no {table} entry {key!r}") from exc
    if not val >= 0:
        raise InputError(f"{table} {key!r} must be >= 0, got {val}")
    return val * MB_CM2


def _positive(params: dict, key: str) -> float:
    try:
        val = float(params[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise InputError(f"parameter {key!r} missing or not a number") from exc
    if not (val > 0 and math.isfinite(val)):
        raise InputError(f"parameter {key!r} must be finite and > 0, got {val}")
    return val


def _production(cfg: dict, xs: dict) -> list[tuple[dict, float, float]]:
    """(parent entry, sigma_{j->s} in cm^2, observed ratio r_j = N_j / N_ref) for each parent."""
    sec = cfg["secondary"]["name"]
    return [(p, _sigma(xs, "production_mb", f"{p['name']}->{sec}"), float(p["observed_ratio_to_reference"]))
            for p in cfg["parents"]]


# ---------------------------------------------------------------- closed forms

def diffusion_coefficient(params: dict, rig: float, b: float) -> float:
    """D(R) = D0 beta (R/R0)^delta in cm^2/s."""
    return _positive(params, "D0_cm2_s") * b * (rig / _positive(params, "R0_GV")) ** float(params["delta"])


def grammage_1d(params: dict, rig: float, b: float) -> float:
    """Escape grammage of the thin-disc 1D model, lambda_esc = n_H m_H h v L / D(R), in g/cm^2."""
    h = _positive(params, "h_kpc") * KPC_CM
    big_l = _positive(params, "L_kpc") * KPC_CM
    return _positive(params, "n_H_cm3") * M_H_G * h * b * C_CM_S * big_l / diffusion_coefficient(params, rig, b)


def grammage_leaky_box(params: dict, rig: float) -> float:
    """lambda_esc(R) = lambda0 (R/R0)^-delta in g/cm^2 (the weighted-slab model's own parametrization)."""
    return _positive(params, "lambda0_g_cm2") * (rig / _positive(params, "R0_GV")) ** (-float(params["delta"]))


def slab_ratio(lambda_esc: float, cfg: dict, xs: dict) -> float:
    """Closed-form weighted-slab (exponential path-length distribution) ratio N_s / N_ref at one energy."""
    sig_s = _sigma(xs, "inelastic_mb", cfg["secondary"]["name"])
    num = sum(s_js / M_H_G * r for _, s_js, r in _production(cfg, xs))
    return num / (1.0 / lambda_esc + sig_s / M_H_G)


def thin_disc_ratio(params: dict, rig: float, b: float, cfg: dict, xs: dict) -> float:
    """Closed-form 1D thin-disc ratio at the mid-plane, written without the grammage."""
    sig_s = _sigma(xs, "inelastic_mb", cfg["secondary"]["name"])
    h = _positive(params, "h_kpc") * KPC_CM
    big_l = _positive(params, "L_kpc") * KPC_CM
    escape = diffusion_coefficient(params, rig, b) / (h * _positive(params, "n_H_cm3") * b * C_CM_S * big_l)
    return sum(s_js * r for _, s_js, r in _production(cfg, xs)) / (sig_s + escape)


# ---------------------------------------------------------------- numerical cross-checks

def slab_ratio_numerical(lambda_esc: float, cfg: dict, xs: dict, rtol: float = 1e-10) -> float:
    """Integrate dN_j/dx = -N_j/lambda_j, dN_s/dx = sum_j (sigma_js/m_H) N_j - N_s/lambda_s from N_s(0) = 0 and
    average over G(x) = exp(-x/lambda_esc)/lambda_esc (quadrature to 60 lambda_esc). Parents start at the observed
    ratios divided by their own slab survival factor, so their averages equal r_j."""
    from scipy.integrate import quad, solve_ivp
    prod = _production(cfg, xs)
    inv_par = [_sigma(xs, "inelastic_mb", p["name"]) / M_H_G for p, _, _ in prod]
    inv_s = _sigma(xs, "inelastic_mb", cfg["secondary"]["name"]) / M_H_G
    k_js = [s / M_H_G for _, s, _ in prod]
    n0 = [r * (1.0 / lambda_esc + ip) * lambda_esc for (_, _, r), ip in zip(prod, inv_par)]

    def rhs(_x, y):
        par, s = y[:-1], y[-1]
        return [*(-ip * n for ip, n in zip(inv_par, par)), sum(k * n for k, n in zip(k_js, par)) - inv_s * s]

    x_max = 60.0 * lambda_esc
    sol = solve_ivp(rhs, (0.0, x_max), [*n0, 0.0], dense_output=True, rtol=rtol, atol=1e-14, method="DOP853")
    weight = lambda x, i: math.exp(-x / lambda_esc) / lambda_esc * float(sol.sol(x)[i])  # noqa: E731
    avg = [quad(weight, 0.0, x_max, args=(i,), epsabs=0.0, epsrel=1e-11, limit=400)[0] for i in range(len(n0) + 1)]
    ref = [p["name"] for p, _, _ in prod].index(cfg["reference_primary"])
    return avg[-1] / avg[ref]


def _disc_inputs(params: dict, e_n: float, cfg: dict, xs: dict) -> dict:
    """Rates for the finite-thickness disc: Gamma_i = n_H v sigma_i (1/s), D_i (cm^2/s), sources q_j = r_j."""
    prod = _production(cfg, xs)
    n_h = _positive(params, "n_H_cm3")
    out = {"h": _positive(params, "h_kpc") * KPC_CM, "L": _positive(params, "L_kpc") * KPC_CM, "parents": []}
    if out["h"] >= out["L"]:
        raise InputError("the disc half-thickness h must be smaller than the halo half-height L")
    for p, s_js, r in prod:
        rig, b = kinematics(e_n, p)
        out["parents"].append({"name": p["name"], "q": r, "D": diffusion_coefficient(params, rig, b),
                               "G": n_h * b * C_CM_S * _sigma(xs, "inelastic_mb", p["name"]),
                               "G_js": n_h * b * C_CM_S * s_js})
    rig, b = kinematics(e_n, cfg["secondary"])
    out["sec"] = {"D": diffusion_coefficient(params, rig, b),
                  "G": n_h * b * C_CM_S * _sigma(xs, "inelastic_mb", cfg["secondary"]["name"])}
    out["ref"] = [p["name"] for p in cfg["parents"]].index(cfg["reference_primary"])
    return out


def halo_finite_disc_exact(params: dict, e_n: float, cfg: dict, xs: dict) -> dict:
    """Exact mid-plane densities of the 1D model with gas and sources uniform in |z| < h (no convection).

    Parent j: N_j = a_j + A_j cosh(k_j z) in the disc, B_j (L - z) outside; a_j = q_j/Gamma_j, k_j^2 = Gamma_j/D_j,
    A_j = -a_j / Delta_j, Delta_i = cosh(k_i h) + (L - h) k_i sinh(k_i h). Secondary: particular part
    c + sum_j E_j cosh(k_j z) with c = sum_j Gamma_js a_j / Gamma_s, E_j = Gamma_js A_j / (Gamma_s - D_s k_j^2), plus
    F cosh(k_s z), F = -(c + sum_j E_j Delta_j) / Delta_s from continuity of N and dN/dz at z = h."""
    d = _disc_inputs(params, e_n, cfg, xs)
    h, big_l = d["h"], d["L"]

    def delta_(k):
        return math.cosh(k * h) + (big_l - h) * k * math.sinh(k * h)

    sec = d["sec"]
    k_s = math.sqrt(sec["G"] / sec["D"])
    n_par, c, e_sum0, e_delta = [], 0.0, 0.0, 0.0
    for p in d["parents"]:
        k = math.sqrt(p["G"] / p["D"])
        a = p["q"] / p["G"]
        big_a = -a / delta_(k)
        n_par.append(a + big_a)
        denom = sec["G"] - sec["D"] * k * k
        if abs(denom) < 1e-9 * sec["G"]:
            raise InputError(f"Gamma_s/D_s equals Gamma_j/D_j for parent {p['name']}: degenerate particular solution")
        e_j = p["G_js"] * big_a / denom
        c += p["G_js"] * a / sec["G"]
        e_sum0 += e_j
        e_delta += e_j * delta_(k)
    f = -(c + e_delta) / delta_(k_s)
    n_s = c + e_sum0 + f
    return {"parents": n_par, "secondary": n_s, "ratio": n_s / n_par[d["ref"]],
            "parent_ratios": [n / n_par[d["ref"]] for n in n_par]}


def halo_finite_disc_fd(params: dict, e_n: float, cfg: dict, xs: dict, n_disc: int = 2000,
                        n_halo: int = 4000) -> dict:
    """Finite-volume solution of the same finite-disc problem on z in [0, L] (dN/dz = 0 at 0, N = 0 at L), with a
    node at z = h; second order in the cell sizes. A check of halo_finite_disc_exact, not a production solver."""
    import numpy as np
    from scipy.linalg import solve_banded
    d = _disc_inputs(params, e_n, cfg, xs)
    h, big_l = d["h"], d["L"]
    z = np.concatenate([np.linspace(0.0, h, n_disc + 1), np.linspace(h, big_l, n_halo + 1)[1:]])
    dz = np.diff(z)
    n = len(z) - 1  # unknowns at nodes 0..n-1; node n is the boundary (N = 0)
    left = np.concatenate([[0.0], dz[:-1]])[:n]
    right = dz[:n]
    vol = 0.5 * (left + right)
    vol[0] = 0.5 * right[0]
    in_disc = 0.5 * np.where(z[:n] < h, left + right, 0.0)  # disc length inside each control volume
    in_disc[0] = 0.5 * right[0]
    in_disc[n_disc] = 0.5 * left[n_disc]  # the node at z = h: only its lower half lies in the disc
    frac = in_disc / vol

    def solve(diff, gamma, source):
        ab = np.zeros((3, n))
        up = diff / right
        lo = np.where(np.arange(n) > 0, diff / np.where(left > 0, left, 1.0), 0.0)
        ab[1] = -(up + lo) / vol - gamma * frac
        ab[0, 1:] = (up / vol)[:-1]
        ab[2, :-1] = (lo / vol)[1:]
        return solve_banded((1, 1), ab, -source * frac)

    pars = [solve(p["D"], p["G"], p["q"] * np.ones(n)) for p in d["parents"]]
    sec_src = sum(p["G_js"] * npar for p, npar in zip(d["parents"], pars))
    n_s = solve(d["sec"]["D"], d["sec"]["G"], sec_src)
    n_par = [float(x[0]) for x in pars]
    return {"parents": n_par, "secondary": float(n_s[0]), "ratio": float(n_s[0]) / n_par[d["ref"]],
            "parent_ratios": [x / n_par[d["ref"]] for x in n_par], "cells": int(n)}


# ---------------------------------------------------------------- evaluation at a parameter point

def model_parameters(cfg: dict, overrides: dict | None = None) -> dict:
    """The parameter point: the config's block for its model, updated by `overrides` (unknown keys refused)."""
    model = cfg["model"]
    keys, block = (TRANSPORT_KEYS, "transport") if model == "diffusion-1d" else (LEAKY_BOX_KEYS, "leaky_box")
    if model not in ("diffusion-1d", "weighted-slab"):
        raise InputError(f"model must be 'diffusion-1d' or 'weighted-slab', got {model!r}")
    params = dict(cfg[block])
    for key, val in (overrides or {}).items():
        if key not in keys:
            raise InputError(f"unknown parameter {key!r} for model {model}; allowed: {list(keys)}")
        params[key] = float(val)
    return params


def evaluate(cfg: dict, overrides: dict | None = None, xs_set: str | None = None) -> dict:
    """Ratio at cfg["energies_gev_per_n"] for one parameter point; also the escape grammage at each energy."""
    params = model_parameters(cfg, overrides)
    xs = load_cross_sections(cfg, xs_set)
    ratio, gram = [], []
    for e_n in cfg["energies_gev_per_n"]:
        if not e_n > 0:
            raise InputError(f"energies must be > 0 GeV/n, got {e_n}")
        rig, b = kinematics(e_n, cfg["secondary"])
        lam = grammage_1d(params, rig, b) if cfg["model"] == "diffusion-1d" else grammage_leaky_box(params, rig)
        gram.append(lam)
        ratio.append(thin_disc_ratio(params, rig, b, cfg, xs) if cfg["model"] == "diffusion-1d"
                     else slab_ratio(lam, cfg, xs))
    point = dict(params)
    if cfg["model"] == "diffusion-1d":
        point["D0_over_L_cm2_s_per_kpc"] = params["D0_cm2_s"] / params["L_kpc"]
    return {"model": cfg["model"], "parameter_point": point, "cross_section_set": xs_set or cfg["cross_section_set"],
            "energies_gev_per_n": list(cfg["energies_gev_per_n"]), "ratio": ratio, "grammage_g_cm2": gram}


def bin_averaged(cfg: dict, edges: list[float], overrides: dict | None = None, xs_set: str | None = None,
                 n_nodes: int = 8) -> list[float]:
    """Ratio averaged uniformly in ln(E/n) over each bin (Gauss-Legendre, n_nodes per bin).

    This is a theory-side bin average of the ratio itself, not the ratio of bin-averaged fluxes (that needs the primary
    spectra and is excluded); the profile's conventions record the definition (crsr:bin_average)."""
    import numpy as np
    if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])) or edges[0] <= 0:
        raise InputError("bin edges must be positive and strictly increasing")
    x, w = np.polynomial.legendre.leggauss(n_nodes)
    nodes, weights = [], []
    for lo, hi in zip(edges, edges[1:]):
        a, b = math.log(lo), math.log(hi)
        nodes += [math.exp(0.5 * (b - a) * t + 0.5 * (a + b)) for t in x]
        weights.append([0.5 * wi for wi in w])
    vals = evaluate(dict(cfg, energies_gev_per_n=nodes), overrides, xs_set)["ratio"]
    return [float(sum(wi * vals[i * n_nodes + j] for j, wi in enumerate(wb))) for i, wb in enumerate(weights)]


def grid(cfg: dict, axes: dict[str, list[float]], xs_set: str | None = None) -> dict:
    """evaluate() on the Cartesian product of `axes` (row-major, last axis fastest)."""
    import itertools
    names = list(axes)
    points = [evaluate(cfg, dict(zip(names, combo)), xs_set) for combo in itertools.product(*axes.values())]
    return {"model": cfg["model"], "axes": {k: list(map(float, v)) for k, v in axes.items()}, "order": "row-major",
            "energies_gev_per_n": list(cfg["energies_gev_per_n"]),
            "cross_section_set": xs_set or cfg["cross_section_set"],
            "points": [{"parameter_point": p["parameter_point"], "ratio": p["ratio"]} for p in points],
            "illustrative": True}


# ---------------------------------------------------------------- benchmark

def benchmark(cfg: dict) -> dict:
    """Closed forms against the numerical solutions at the config's energies (tolerances stated per check)."""
    params = model_parameters(dict(cfg, model="diffusion-1d"))
    xs = load_cross_sections(cfg)
    rows, checks = [], {}
    slab_dev, map_dev, fd_dev = 0.0, 0.0, 0.0
    for e_n in cfg["energies_gev_per_n"]:
        rig, b = kinematics(e_n, cfg["secondary"])
        lam = grammage_1d(params, rig, b)
        closed = slab_ratio(lam, cfg, xs)
        numeric = slab_ratio_numerical(lam, cfg, xs)
        thin = thin_disc_ratio(params, rig, b, cfg, xs)
        exact = halo_finite_disc_exact(params, e_n, cfg, xs)
        fd = halo_finite_disc_fd(params, e_n, cfg, xs)
        slab_dev = max(slab_dev, abs(numeric / closed - 1))
        map_dev = max(map_dev, abs(thin / closed - 1))
        fd_dev = max(fd_dev, abs(fd["ratio"] / exact["ratio"] - 1))
        rows.append({"e_n_gev": e_n, "grammage_g_cm2": lam, "slab_closed": closed, "slab_numerical": numeric,
                     "thin_disc_closed": thin, "finite_disc_exact": exact["ratio"], "finite_disc_fd": fd["ratio"]})
    checks["slab_ode_average_equals_closed_form_1e-7"] = slab_dev < 1e-7
    checks["thin_disc_equals_slab_with_mapped_grammage_1e-12"] = map_dev < 1e-12
    checks["finite_difference_equals_finite_disc_exact_1e-6"] = fd_dev < 1e-6
    # the thin-disc limit: the finite-disc exact ratio tends to the closed form as h/L -> 0
    e_mid = cfg["energies_gev_per_n"][len(cfg["energies_gev_per_n"]) // 2]
    rig, b = kinematics(e_mid, cfg["secondary"])
    limit = []
    for h_kpc in (0.4, 0.1, 0.025, 0.00625, 0.0015625):
        p = dict(params, h_kpc=h_kpc, n_H_cm3=params["n_H_cm3"] * params["h_kpc"] / h_kpc)  # fixed surface density
        ex = halo_finite_disc_exact(p, e_mid, cfg, xs)
        cfg_r = dict(cfg, parents=[dict(q, observed_ratio_to_reference=r)
                                   for q, r in zip(cfg["parents"], ex["parent_ratios"])])
        limit.append({"h_kpc": h_kpc, "rel_diff": abs(ex["ratio"] / thin_disc_ratio(p, rig, b, cfg_r, xs) - 1)})
    diffs = [x["rel_diff"] for x in limit]
    checks["finite_disc_tends_to_thin_disc_monotonically"] = all(b2 < a2 for a2, b2 in zip(diffs, diffs[1:]))
    checks["finite_disc_within_1e-3_of_thin_disc_at_smallest_h"] = diffs[-1] < 1e-3
    # the degeneracy: D0 and L scaled together leave the thin-disc ratio unchanged
    base = evaluate(dict(cfg, model="diffusion-1d"))["ratio"]
    scaled = evaluate(dict(cfg, model="diffusion-1d"), {"D0_cm2_s": params["D0_cm2_s"] * 2.5,
                                                       "L_kpc": params["L_kpc"] * 2.5})["ratio"]
    checks["ratio_invariant_under_D0_and_L_scaled_together_1e-12"] = max(
        abs(s / r - 1) for s, r in zip(scaled, base)) < 1e-12
    return {"rows": rows, "thin_disc_limit": limit, "max_rel_dev": {"slab_numerical_vs_closed": slab_dev,
            "thin_disc_vs_slab_mapped": map_dev, "fd_vs_finite_exact": fd_dev}, "checks": checks,
            "illustrative": True}


# ---------------------------------------------------------------- CLI

def _parse_assign(items: list[str], many: bool) -> dict:
    out = {}
    for item in items or []:
        key, sep, val = item.partition("=")
        if not sep:
            raise InputError(f"expected KEY=VALUE, got {item!r}")
        out[key.strip()] = [float(v) for v in val.split(",")] if many else float(val)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override one model parameter")
    ap.add_argument("--grid", action="append", default=[], metavar="KEY=V1,V2,...", help="grid axis (repeatable)")
    ap.add_argument("--xs", help="cross-section set (path relative to the profile) instead of the config's nominal")
    ap.add_argument("--benchmark", action="store_true", help="run the closed-form vs numerical benchmark")
    ap.add_argument("--out", type=Path)
    opts = ap.parse_args(argv)
    try:
        import numpy  # noqa: F401
        import scipy  # noqa: F401
    except ImportError as exc:
        print(json.dumps({"status": "failed", "error": f"missing required package: {exc.name}",
                          "hint": "use a Python with numpy and scipy (requirements-core.txt)"}))
        return 3
    try:
        cfg = load_json(opts.config)
        if opts.benchmark:
            out = benchmark(cfg)
        elif opts.grid:
            out = grid(cfg, _parse_assign(opts.grid, many=True), opts.xs)
        else:
            out = evaluate(cfg, _parse_assign(opts.set, many=False), opts.xs)
    except (InputError, KeyError, ValueError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 2
    text = json.dumps(out, indent=1) + "\n"
    if opts.out:
        opts.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if all(out.get("checks", {}).values()) else 1


if __name__ == "__main__":
    sys.exit(main())
