#!/usr/bin/env python3
"""Predictions of theory:cr-secondary-antiprotons: the secondary antiproton source term q(T_pbar) from cosmic-ray
protons and helium on interstellar hydrogen and helium.

Convention (skills/hep-theory/references/cosmic-ray-propagation.md, "Secondary antiprotons: source-term conventions",
after Korsmeier, Donato, Di Mauro, PRD 97 (2018) 103019, Eq. (1)):

  q_ij(T) = 4 pi n_j  int_{T_th}^{oo} dT_i  phi_i(T_i)  dsigma_ij/dT(T_i, T)

i the projectile (p, He; phi_i per kinetic energy per nucleon T_i), j the target (H, He; density n_j), T the
antiproton kinetic energy. Channels pp, pHe, Hep, HeHe (projectile first). The prompt antiproton cross section is
multiplied by the antineutron and hyperon factor of the same reference (Winkler Eq. (5); Korsmeier et al. Eq. (4)):

  dsigma_total = dsigma_pbar,prompt (2 + Delta_IS + 2 Delta_Lambda)  (both included),

which this code books as (1 + Delta_Lambda) for antiprotons plus (1 + Delta_IS + Delta_Lambda) for antineutrons, so
that each can be excluded and the choice is stated; Delta_Lambda = c_Lambda (Lambda-bar / pbar).

Cross sections: TOY parametrizations, ILLUSTRATIVE (no published parametrization is reproduced here):
  dsigma_pp/dT (T_i, T) = (sigma0 / T_i) (1 - T/T_i)^n   for T_i >= T_th and T < T_i, else 0,
  T_th = (k_th - 1) m_p with k_th = 7 (pp threshold E_p >= 7 m_p, di Mauro et al. PRD 90 (2014) 085017, Eq. (1)),
  dsigma_ij/dT = f_ij dsigma_pp/dT at the same energy per nucleon (constant ILLUSTRATIVE rescaling factors f_ij).
Primary fluxes: power laws or sharp broken power laws in T_i (ILLUSTRATIVE).

Two evaluations: numerical quadrature of the source integral (source_term, the general path: it only needs the
flux and dsigma/dT as functions) and the closed form for piecewise power-law fluxes with the toy cross section
(closed_form_channel; incomplete beta functions), used as the profile's internal benchmark (--benchmark).

Usage:
  python3 predict.py [--config ../benchmarks/source-term-benchmark.json] [--xs models/xs-toy-B.json] [--out P.json]
  python3 predict.py --benchmark      # numerical integration against the closed form; exit 1 if a check fails
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
DEFAULT_CONFIG = PROFILE / "benchmarks" / "source-term-benchmark.json"

# Constants (crpb:C06): proton mass, CODATA 2018; 1 mb = 1e-27 cm^2.
M_P_GEV = 0.93827208816
MB_CM2 = 1e-27
CHANNELS = (("pp", "p", "H"), ("pHe", "p", "He"), ("Hep", "He", "H"), ("HeHe", "He", "He"))
SWITCHES = ("included", "excluded")


class InputError(ValueError):
    """A config or cross-section set that cannot be used."""


# ---------------------------------------------------------------- inputs

def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _num(block: dict, key: str, where: str, positive: bool = True, allow_zero: bool = False) -> float:
    try:
        val = float(block[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise InputError(f"{where}: {key!r} missing or not a number") from exc
    ok = math.isfinite(val) and (val > 0 or (allow_zero and val == 0) or not positive)
    if not ok:
        raise InputError(f"{where}: {key!r} must be finite and {'>= 0' if allow_zero else '> 0'}, got {val}")
    return val


def load_cross_sections(cfg: dict, which: str | None = None) -> dict:
    """The cross-section set named by `which` (a path relative to the profile) or the config's nominal set, checked."""
    xs = load_json(PROFILE / (which or cfg["cross_section_set"]))
    pp = xs.get("pp_prompt")
    if not isinstance(pp, dict) or pp.get("form") != "x-scaling-beta":
        raise InputError("cross-section set: pp_prompt.form must be 'x-scaling-beta' (the only toy form here)")
    _num(pp, "sigma0_mb", "pp_prompt")
    _num(pp, "n", "pp_prompt", allow_zero=True)
    if _num(xs, "threshold_total_energy_mp", "cross-section set") <= 1:
        raise InputError("threshold_total_energy_mp must exceed 1 (a total energy above the proton mass)")
    f = xs.get("channel_factors")
    if not isinstance(f, dict) or set(f) != {c for c, _, _ in CHANNELS} or float(f["pp"]) != 1.0:
        raise InputError("channel_factors must give pp (= 1), pHe, Hep and HeHe")
    for c in f:
        _num(f, c, "channel_factors")
    _num(xs.get("antineutron") or {}, "Delta_IS", "antineutron", allow_zero=True)
    hyp = xs.get("hyperon") or {}
    _num(hyp, "Lambdabar_over_pbar", "hyperon", allow_zero=True)
    _num(hyp, "Delta_Lambda_coefficient", "hyperon", allow_zero=True)
    return xs


def threshold(xs: dict) -> float:
    """Projectile kinetic energy per nucleon at threshold, T_th = (k_th - 1) m_p, in GeV."""
    return (float(xs["threshold_total_energy_mp"]) - 1.0) * M_P_GEV


def flux_segments(spec: dict, where: str) -> list[tuple[float, float, float, float]]:
    """A primary flux as power-law segments (T_lo, T_hi, C, gamma) with phi = C T^-gamma on [T_lo, T_hi) (T in GeV/n).

    'power-law': phi = K (T/T0)^-gamma for T >= T_min (default 0). 'broken-power-law' (sharp): index gamma1 below T_b
    and gamma2 above, continuous at T_b."""
    form = spec.get("form")
    t0 = _num(spec, "T0_gev", where)
    k = _num(spec, "K", where)
    t_min = float(spec.get("T_min_gev", 0.0))
    if form == "power-law":
        g = _num(spec, "gamma", where)
        return [(t_min, math.inf, k * t0 ** g, g)]
    if form == "broken-power-law":
        g1, g2, tb = _num(spec, "gamma1", where), _num(spec, "gamma2", where), _num(spec, "T_break_gev", where)
        if tb <= t_min:
            raise InputError(f"{where}: T_break_gev must exceed T_min_gev")
        c1 = k * t0 ** g1
        c2 = c1 * tb ** (g2 - g1)  # continuity at T_b
        return [(t_min, tb, c1, g1), (tb, math.inf, c2, g2)]
    raise InputError(f"{where}: form must be 'power-law' or 'broken-power-law', got {form!r}")


def flux(spec: dict, t_n: float, where: str = "flux") -> float:
    for lo, hi, c, g in flux_segments(spec, where):
        if lo <= t_n < hi:
            return c * t_n ** (-g)
    return 0.0


def densities(cfg: dict) -> dict:
    ism = cfg.get("ism") or {}
    n_h = _num(ism, "n_H_cm3", "ism")
    return {"H": n_h, "He": n_h * _num(ism, "He_to_H", "ism", allow_zero=True)}


def factor_parts(cfg: dict, xs: dict) -> dict:
    """Antineutron and hyperon bookkeeping: total = prompt pbar x (pbar_part + nbar_part)."""
    sw = {k: cfg.get(k, "included") for k in ("antineutrons", "hyperons")}
    for k, v in sw.items():
        if v not in SWITCHES:
            raise InputError(f"{k} must be one of {SWITCHES}, got {v!r}")
    d_is = float(xs["antineutron"]["Delta_IS"])
    hyp = xs["hyperon"]
    d_lam = float(hyp["Delta_Lambda_coefficient"]) * float(hyp["Lambdabar_over_pbar"])
    h = d_lam if sw["hyperons"] == "included" else 0.0
    pbar = 1.0 + h
    nbar = (1.0 + d_is + h) if sw["antineutrons"] == "included" else 0.0
    return {"antineutrons": sw["antineutrons"], "hyperons": sw["hyperons"], "Delta_IS": d_is, "Delta_Lambda": d_lam,
            "pbar_part": pbar, "nbar_part": nbar, "factor": pbar + nbar}


# ---------------------------------------------------------------- cross section (TOY, ILLUSTRATIVE)

def dsigma_dt_pp(xs: dict, t_n: float, t: float) -> float:
    """Toy prompt pp -> pbar X differential cross section dsigma/dT in cm^2/GeV (ILLUSTRATIVE)."""
    if t_n < threshold(xs) or not 0 < t < t_n:
        return 0.0
    pp = xs["pp_prompt"]
    return float(pp["sigma0_mb"]) * MB_CM2 / t_n * (1.0 - t / t_n) ** float(pp["n"])


def dsigma_dt(xs: dict, channel: str, t_n: float, t: float) -> float:
    return float(xs["channel_factors"][channel]) * dsigma_dt_pp(xs, t_n, t)


# ---------------------------------------------------------------- source term

def channel_numerical(cfg: dict, xs: dict, channel: str, t: float, epsrel: float = 1e-12) -> float:
    """Prompt q_ij(T) by quadrature in ln T_i from max(T_th, T) upward (split at flux breaks); cm^-3 s^-1 GeV^-1."""
    from scipy.integrate import quad
    _, proj, targ = next(c for c in CHANNELS if c[0] == channel)
    spec = cfg["primaries"][proj]
    n_j = densities(cfg)[targ]
    lower = max(threshold(xs), t)
    segs = flux_segments(spec, f"primaries.{proj}")
    cuts = sorted({lower} | {lo for lo, _, _, _ in segs if lo > lower})
    u_max = math.log(lower) + 80.0  # e^80: the power-law tail beyond is below double precision
    total = 0.0
    edges = [math.log(c) for c in cuts] + [u_max]
    for a, b in zip(edges, edges[1:]):
        val, _ = quad(lambda u: flux(spec, math.exp(u)) * dsigma_dt(xs, channel, math.exp(u), t) * math.exp(u),
                      a, b, epsabs=0.0, epsrel=epsrel, limit=500)
        total += val
    return 4.0 * math.pi * n_j * total


def closed_form_channel(cfg: dict, xs: dict, channel: str, t: float) -> float:
    """Closed form of the same integral for piecewise power-law fluxes and the toy cross section.

    With x = T / T_i: int phi dsigma/dT dT_i over a segment C T_i^-gamma on [a, b] equals
    f sigma0 C T^-gamma [B(x_hi; gamma, n + 1) - B(x_lo; gamma, n + 1)], x_lo = T / b, x_hi = T / max(a, T_th, T),
    B(x; a, b) the incomplete beta function (derivation record, checked by derive.py)."""
    from scipy.special import beta as beta_fn
    from scipy.special import betainc
    _, proj, targ = next(c for c in CHANNELS if c[0] == channel)
    n_j = densities(cfg)[targ]
    pp = xs["pp_prompt"]
    s0, n_exp, f = float(pp["sigma0_mb"]) * MB_CM2, float(pp["n"]), float(xs["channel_factors"][channel])
    total = 0.0
    for lo, hi, c, g in flux_segments(cfg["primaries"][proj], f"primaries.{proj}"):
        a = max(lo, threshold(xs), t)
        if a >= hi:
            continue
        x_hi, x_lo = t / a, (t / hi if math.isfinite(hi) else 0.0)
        inc = (betainc(g, n_exp + 1.0, x_hi) - betainc(g, n_exp + 1.0, x_lo)) * beta_fn(g, n_exp + 1.0)
        total += f * s0 * c * t ** (-g) * float(inc)
    return 4.0 * math.pi * n_j * total


def source_term(cfg: dict, energies: list[float] | None = None, xs_set: str | None = None,
                method: str = "numerical") -> dict:
    """q(T) per channel (prompt antiprotons), their sum, the antineutron/hyperon factor, the total and the channel
    fractions at `energies` (default cfg["energies_gev"])."""
    xs = load_cross_sections(cfg, xs_set)
    fac = factor_parts(cfg, xs)
    energies = list(cfg["energies_gev"] if energies is None else energies)
    fn = channel_numerical if method == "numerical" else closed_form_channel
    per = {c: [] for c, _, _ in CHANNELS}
    for t in energies:
        if not t > 0:
            raise InputError(f"antiproton kinetic energies must be > 0 GeV, got {t}")
        for c, _, _ in CHANNELS:
            per[c].append(fn(cfg, xs, c, t))
    prompt = [sum(per[c][k] for c in per) for k in range(len(energies))]
    total = [p * fac["factor"] for p in prompt]
    frac = {c: [v / p if p > 0 else None for v, p in zip(per[c], prompt)] for c in per}
    return {"method": method, "cross_section_set": xs_set or cfg["cross_section_set"], "energies_gev": energies,
            "unit": "cm^-3 s^-1 GeV^-1", "prompt_by_channel": per, "prompt": prompt, "factor": fac, "total": total,
            "channel_fractions": frac, "threshold_gev_per_n": threshold(xs), "illustrative": True}


def bin_averaged(cfg: dict, edges: list[float], xs_set: str | None = None, n_nodes: int = 8) -> list[float]:
    """Total q averaged linearly in T over each bin, (1/Delta T) int q dT (Gauss-Legendre, n_nodes per piece; a bin
    containing the threshold T_th is split there, since q has a kink at T = T_th)."""
    import numpy as np
    if len(edges) < 2 or edges[0] <= 0 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise InputError("bin edges must be positive and strictly increasing")
    t_th = threshold(load_cross_sections(cfg, xs_set))
    x, w = np.polynomial.legendre.leggauss(n_nodes)
    nodes, weights, owner = [], [], []
    for i, (lo, hi) in enumerate(zip(edges, edges[1:])):
        pieces = [(lo, t_th), (t_th, hi)] if lo < t_th < hi else [(lo, hi)]
        for a, b in pieces:
            nodes += [0.5 * (b - a) * xi + 0.5 * (a + b) for xi in x]
            weights += [0.5 * (b - a) * wi / (hi - lo) for wi in w]
            owner += [i] * n_nodes
    vals = source_term(cfg, nodes, xs_set)["total"]
    out = [0.0] * (len(edges) - 1)
    for i, wt, v in zip(owner, weights, vals):
        out[i] += wt * v
    return out


# ---------------------------------------------------------------- benchmark

def benchmark(cfg: dict) -> dict:
    """Numerical quadrature against the closed form (power-law and broken power-law primaries, energies on both
    sides of the threshold), a hand-computed point and the factor bookkeeping."""
    xs = load_cross_sections(cfg)
    checks, rows = {}, []
    variants = {"configured": cfg,
                "broken-power-law": dict(cfg, primaries={
                    "p": {"form": "broken-power-law", "K": cfg["primaries"]["p"]["K"], "T0_gev": 1.0, "gamma1": 2.8,
                          "gamma2": 2.6, "T_break_gev": 200.0},
                    "He": {"form": "broken-power-law", "K": cfg["primaries"]["He"]["K"], "T0_gev": 1.0, "gamma1": 2.7,
                           "gamma2": 2.5, "T_break_gev": 100.0}})}
    dev = 0.0
    for name, c in variants.items():
        for t in cfg["energies_gev"]:
            for ch, _, _ in CHANNELS:
                num, closed = channel_numerical(c, xs, ch, t), closed_form_channel(c, xs, ch, t)
                d = abs(num / closed - 1.0)
                dev = max(dev, d)
                rows.append({"variant": name, "T_gev": t, "channel": ch, "numerical": float(num),
                             "closed_form": float(closed), "rel_dev": float(d)})
    checks["numerical_equals_closed_form_1e-8"] = dev < 1e-8
    t_th = threshold(xs)
    checks["energies_on_both_sides_of_threshold"] = min(cfg["energies_gev"]) < t_th < max(cfg["energies_gev"])
    # hand-computed point: n = 0 and a pure power law, T >= T_th: q_pp = 4 pi n_H sigma0 C T^-gamma / gamma
    hand_xs = dict(xs, pp_prompt={"form": "x-scaling-beta", "sigma0_mb": 10.0, "n": 0.0})
    pl = {"form": "power-law", "K": 2.0, "T0_gev": 1.0, "gamma": 2.5}
    hand_cfg = dict(cfg, primaries={"p": pl, "He": pl})
    t = 20.0
    expect = 4.0 * math.pi * densities(cfg)["H"] * 10.0 * MB_CM2 * 2.0 * t ** -2.5 / 2.5
    hand = channel_numerical(hand_cfg, hand_xs, "pp", t)
    checks["hand_computed_point_1e-10"] = abs(hand / expect - 1.0) < 1e-10
    # factor bookkeeping: both included gives 2 + Delta_IS + 2 Delta_Lambda
    fac = factor_parts(cfg, xs)
    both = factor_parts(dict(cfg, antineutrons="included", hyperons="included"), xs)
    checks["factor_equals_2_plus_DeltaIS_plus_2_DeltaLambda"] = abs(
        both["factor"] - (2.0 + both["Delta_IS"] + 2.0 * both["Delta_Lambda"])) < 1e-15
    # channel sum: the total is the prompt channel sum times the factor
    st = source_term(cfg)
    checks["total_equals_factor_times_channel_sum"] = all(
        abs(tot - fac["factor"] * sum(st["prompt_by_channel"][c][k] for c, _, _ in CHANNELS)) <= 1e-12 * tot
        for k, tot in enumerate(st["total"]))
    checks["total_positive_at_every_energy"] = all(v > 0 for v in st["total"])
    checks = {k: bool(v) for k, v in checks.items()}
    return {"rows": rows, "max_rel_dev": float(dev), "threshold_gev_per_n": t_th, "hand_point": {"T_gev": t, "q": hand,
            "expected": expect}, "factor": fac, "checks": checks, "illustrative": True}


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--xs", help="cross-section set (path relative to the profile) instead of the config's nominal")
    ap.add_argument("--method", choices=("numerical", "closed-form"), default="numerical")
    ap.add_argument("--benchmark", action="store_true", help="run the numerical vs closed-form benchmark")
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
        out = benchmark(cfg) if opts.benchmark else source_term(cfg, None, opts.xs, opts.method)
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
