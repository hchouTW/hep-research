#!/usr/bin/env python3
"""Closed forms of theory:cr-secondary-ratio's 1D thin-disc model with constant convection and radioactive decay.

Model (derivation in ../derivations/convection-decay-record.md, checked by derive_convection_decay.py): halo |z| < L
with free escape, thin gas disc 2 h delta(z) of density n_H, convective speed V_c sign(z) in conservative form,
D(R) = D0 beta (R/R0)^delta, decay rate 1/(gamma tau_0) of an unstable secondary in the whole halo, and the decay
gain of its daughter (10Be -> 10B). At the mid-plane, for a secondary s fed by parents j with mid-plane ratios r_j:

    N_s(0) = 2 h q_s / (K_s + 2 h n_H v sigma_s),   q_s = n_H v sum_j sigma_js r_j,
    K = V_c + D S coth(S L/2),   S = sqrt(V_c^2/D^2 + 4 Gamma/D),   Gamma = 1/(gamma tau_0) (0 if stable),

which is the pure-diffusion thin-disc form of predict.py (K = 2 D/L) for V_c -> 0 and Gamma -> 0. The daughter of a
radioactive species gets the halo gain Gamma N_R(z) on top of its direct disc source (decay_gain_mid_plane).
Half-lives come from core.constants.physical (NUBASE2020); tau_0 = t_1/2 / ln 2. Fully stripped 7Be is treated as
stable (no electron to capture), and every species with a finite NUBASE half-life must either carry a "decay" entry
or record such a "stable_assumption" in the config. Not included: reacceleration (no closed form), energy losses and
the adiabatic energy change of the wind, a convective gradient, secondary-to-secondary feeding other than decay.

Numerical cross-check (no external program): boundary_value_mid_plane solves the same boundary-value problem with
scipy.integrate.solve_bvp; benchmark() compares it with the closed forms and checks the limits to pure diffusion and
number conservation in decay. Every input set shipped with this profile is ILLUSTRATIVE.

Usage:
  python3 convection_decay.py [--config ../benchmarks/convection-decay-benchmark.json] [--set V_c_kms=20] [--out P.json]
  python3 convection_decay.py --benchmark   # closed forms against solve_bvp, limits, conservation; exit 1 on a failure
Exit codes: 0 ok, 1 a check failed, 2 bad input (JSON "error" on stdout), 3 a required package (numpy/scipy) missing.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import predict  # noqa: E402  (sibling module: constants, kinematics, diffusion coefficient, inputs)
from predict import C_CM_S, KPC_CM, InputError, kinematics  # noqa: E402

from core.constants.physical import half_life_seconds  # noqa: E402  (predict.py put the plugin root on sys.path)
from core.kinematics.relativistic import Species, to_momentum, total_energy  # noqa: E402

PROFILE = HERE.parent
DEFAULT_CONFIG = PROFILE / "benchmarks" / "convection-decay-benchmark.json"
KM_S_IN_CM_S = 1e5  # 1 km/s in cm/s
TRANSPORT_KEYS = (*predict.TRANSPORT_KEYS, "V_c_kms")


# ---------------------------------------------------------------- inputs

def model_parameters(cfg: dict, overrides: dict | None = None) -> dict:
    """The config's transport block updated by `overrides` (unknown keys refused); V_c_kms >= 0."""
    params = dict(cfg["transport"])
    for key, val in (overrides or {}).items():
        if key not in TRANSPORT_KEYS:
            raise InputError(f"unknown parameter {key!r}; allowed: {list(TRANSPORT_KEYS)}")
        params[key] = float(val)
    v_c = float(params.get("V_c_kms", 0.0))
    if not (v_c >= 0 and math.isfinite(v_c)):
        raise InputError(f"V_c_kms must be finite and >= 0, got {v_c}")
    params["V_c_kms"] = v_c
    return params


def lorentz_gamma(e_n: float, entry: dict) -> float:
    """gamma at kinetic energy per nucleon e_n (GeV/n), mass A x atomic mass unit (predict.py's convention)."""
    spec = Species(Z=int(entry["Z"]), A=int(entry["A"]), mass=int(entry["A"]) * predict.M_U_GEV)
    mom = to_momentum(e_n, "kinetic_energy_per_nucleon", spec)
    return total_energy(mom, spec.need_mass()) / spec.need_mass()


def rest_lifetime_s(entry: dict) -> float | None:
    """tau_0 = t_1/2 / ln 2 in s from NUBASE2020 (core.constants.physical), or None for a species propagated as
    stable. A species with a finite half-life needs a "decay" entry or a recorded "stable_assumption"."""
    nuclide = entry.get("nuclide", entry["name"])
    half = half_life_seconds(nuclide)
    if entry.get("decay"):
        if half["value"] is None:
            raise InputError(f"{nuclide} has a decay entry but NUBASE2020 lists it as stable")
        return half["value"] / math.log(2.0)
    if half["value"] is not None and not entry.get("stable_assumption"):
        raise InputError(f"{nuclide} has a finite half-life ({half['value']:.4g} s); give a 'decay' entry or record "
                         "a 'stable_assumption'")
    return None


def decay_rate(e_n: float, entry: dict) -> float:
    """1/(gamma tau_0) in 1/s at E/n = e_n; 0 for a species propagated as stable."""
    tau0 = rest_lifetime_s(entry)
    return 0.0 if tau0 is None else 1.0 / (lorentz_gamma(e_n, entry) * tau0)


# ---------------------------------------------------------------- closed forms

def x_coth(x: float) -> float:
    """x coth(x), equal to 1 at x = 0 (series below 1e-4)."""
    return 1.0 + x * x / 3.0 if abs(x) < 1e-4 else x / math.tanh(x)


def escape_speed(diff: float, v_c: float, big_l: float, rate: float) -> float:
    """K = V_c + D S coth(S L/2), S = sqrt(V_c^2/D^2 + 4 rate/D) (cm/s); K = 2D/L for V_c = rate = 0."""
    s_root = math.sqrt((v_c / diff) ** 2 + 4.0 * rate / diff)
    return v_c + (2.0 * diff / big_l) * x_coth(0.5 * s_root * big_l)


def mid_plane_density(source: float, diff: float, v_c: float, big_l: float, rate: float, h: float,
                      loss: float) -> float:
    """N(0) = 2 h q / (K + 2 h loss), with q the disc source and loss = n_H v sigma_inel (1/s)."""
    return 2.0 * h * source / (escape_speed(diff, v_c, big_l, rate) + 2.0 * h * loss)


def decay_gain_mid_plane(n_r0: float, diff_r: float, rate: float, diff_d: float, v_c: float, big_l: float, h: float,
                         loss_d: float) -> float:
    """Mid-plane density of a stable daughter fed only by the decay (rate) of a parent R of mid-plane density n_r0.

    Parent profile: N_R = sum_pm a_pm e^{k_pm z}, k_pm = V_c/(2 D_R) +- S_R/2, a_- = N_R0/(1 - e^{-S_R L}),
    a_+ = -N_R0 e^{-S_R L}/(1 - e^{-S_R L}). Particular daughter solution sum c_pm e^{k_pm z},
    c = rate a / (V_c k - D_d k^2); homogeneous alpha + beta g(z), g = (e^{V_c z/D_d} - 1) D_d / V_c; N(L) = 0 and
    the disc jump -2 D_d N'(0) + (2 V_c + 2 h loss_d) N(0) = 0 fix alpha, beta. k_- is computed as
    -2 rate/(V_c + D_R S_R) so the Gamma -> 0 limit has no cancellation in c_-."""
    if rate == 0.0:
        return 0.0
    s_r = math.sqrt((v_c / diff_r) ** 2 + 4.0 * rate / diff_r)
    k_m = -2.0 * rate / (v_c + diff_r * s_r)
    k_p = v_c / (2.0 * diff_r) + 0.5 * s_r
    norm = n_r0 / -math.expm1(-s_r * big_l)
    c_m = norm * (-(v_c + diff_r * s_r) / 2.0) / (v_c - diff_d * k_m)  # rate / k_m = -(V_c + D_R S_R)/2
    denom_p = k_p * (v_c - diff_d * k_p)
    if abs(v_c - diff_d * k_p) < 1e-9 * max(v_c, diff_d * k_p):
        raise InputError("V_c = D_d k_+: resonant particular solution (choose other transport values)")
    c_p_unit = -rate * norm / denom_p  # c_+ e^{k_+ z} = c_p_unit * e^{k_+ z - S_R L}
    p0 = c_m + c_p_unit * math.exp(-s_r * big_l)
    p_l = c_m * math.exp(k_m * big_l) + c_p_unit * math.exp((k_p - s_r) * big_l)
    dp0 = c_m * k_m + c_p_unit * k_p * math.exp(-s_r * big_l)
    peclet = v_c * big_l / diff_d
    g_l = big_l if peclet == 0.0 else math.expm1(peclet) * diff_d / v_c
    wall = 2.0 * v_c + 2.0 * h * loss_d
    beta_h = (wall * (p0 - p_l) - 2.0 * diff_d * dp0) / (2.0 * diff_d + wall * g_l)
    return -beta_h * g_l - p_l + p0


def _species_inputs(params: dict, e_n: float, cfg: dict, xs: dict) -> dict:
    """Per secondary at E/n = e_n: D (cm^2/s), loss = n_H v sigma_inel (1/s), disc source q = n_H v sum sigma r,
    decay rate (1/s); also the shared h, L (cm) and V_c (cm/s)."""
    n_h = predict._positive(params, "n_H_cm3")
    out = {"h": predict._positive(params, "h_kpc") * KPC_CM, "L": predict._positive(params, "L_kpc") * KPC_CM,
           "V_c": params["V_c_kms"] * KM_S_IN_CM_S, "species": {}}
    for sec in cfg["secondaries"]:
        rig, b = kinematics(e_n, sec)
        vel = b * C_CM_S
        prod = sum(predict._sigma(xs, "production_mb", f"{p['name']}->{sec['name']}")
                   * float(p["observed_ratio_to_reference"]) for p in cfg["parents"])
        out["species"][sec["name"]] = {
            "D": predict.diffusion_coefficient(params, rig, b),
            "loss": n_h * vel * predict._sigma(xs, "inelastic_mb", sec["name"]),
            "q": n_h * vel * prod, "rate": decay_rate(e_n, sec), "entry": sec}
    return out


def network_mid_plane(params: dict, e_n: float, cfg: dict, xs: dict) -> dict:
    """Mid-plane densities relative to the reference parent: parents (their given ratios) and every secondary; a
    daughter's value includes its decay gain, also reported separately under 'decay_gain'."""
    inp = _species_inputs(params, e_n, cfg, xs)
    h, big_l, v_c = inp["h"], inp["L"], inp["V_c"]
    dens = {p["name"]: float(p["observed_ratio_to_reference"]) for p in cfg["parents"]}
    gain = {}
    for name, sp_in in inp["species"].items():
        dens[name] = mid_plane_density(sp_in["q"], sp_in["D"], v_c, big_l, sp_in["rate"], h, sp_in["loss"])
    for name, sp_in in inp["species"].items():
        decay = sp_in["entry"].get("decay")
        if not decay:
            continue
        child = decay["daughter"]
        if child not in inp["species"]:
            raise InputError(f"decay daughter {child!r} of {name} is not a secondary in the config")
        if inp["species"][child]["rate"] != 0.0:
            raise InputError(f"decay daughter {child!r} must be propagated as stable")
        dch = inp["species"][child]
        gain[child] = gain.get(child, 0.0) + decay_gain_mid_plane(dens[name], sp_in["D"], sp_in["rate"], dch["D"],
                                                                  v_c, big_l, h, dch["loss"])
    for child, val in gain.items():
        dens[child] += val
    return {"density": dens, "decay_gain": gain}


def evaluate(cfg: dict, overrides: dict | None = None, xs_set: str | None = None) -> dict:
    """Observables (sums of species at equal E/n) at cfg["energies_gev_per_n"] for one parameter point."""
    params = model_parameters(cfg, overrides)
    xs = predict.load_cross_sections(cfg, xs_set)
    obs = {k: [] for k in cfg["observables"]}
    gain_frac: dict[str, list] = {}
    for e_n in cfg["energies_gev_per_n"]:
        if not e_n > 0:
            raise InputError(f"energies must be > 0 GeV/n, got {e_n}")
        net = network_mid_plane(params, e_n, cfg, xs)
        for key, spec in cfg["observables"].items():
            num = sum(net["density"][s] for s in spec["numerator"])
            den = sum(net["density"][s] for s in spec["denominator"])
            obs[key].append(num / den)
        for child, val in net["decay_gain"].items():
            gain_frac.setdefault(child, []).append(val / net["density"][child])
    return {"model": "diffusion-1d-convection-decay", "parameter_point": params,
            "cross_section_set": xs_set or cfg["cross_section_set"],
            "energies_gev_per_n": list(cfg["energies_gev_per_n"]), "observables": obs,
            "decay_gain_fraction": gain_frac, "illustrative": True}


# ---------------------------------------------------------------- numerical cross-check

def boundary_value_mid_plane(params: dict, e_n: float, cfg: dict, xs: dict, tol: float = 1e-10) -> dict:
    """Solve the 1D problem on u = z/L in [0, 1] with scipy.integrate.solve_bvp, species by species (a radioactive
    species together with its daughter), and return the mid-plane densities like network_mid_plane.

    Per species, with M = L dN/dz: dN/du = M, dM/du = Pe M + lam N - (L^2/D) G(z) (Pe = V_c L/D, lam = Gamma L^2/D,
    G the halo source from a decaying parent); at u = 0: -M + (Pe + h L loss/D) N = h L q/D; at u = 1: N = 0."""
    import numpy as np
    from scipy.integrate import solve_bvp
    inp = _species_inputs(params, e_n, cfg, xs)
    h, big_l, v_c = inp["h"], inp["L"], inp["V_c"]
    dens = {p["name"]: float(p["observed_ratio_to_reference"]) for p in cfg["parents"]}
    mesh = np.linspace(0.0, 1.0, 2001)

    def coeffs(sp_in):
        diff = sp_in["D"]
        return (v_c * big_l / diff, sp_in["rate"] * big_l ** 2 / diff,
                v_c * big_l / diff + h * big_l * sp_in["loss"] / diff, h * big_l * sp_in["q"] / diff)

    daughters = {s["decay"]["daughter"]: s["name"] for s in cfg["secondaries"] if s.get("decay")}
    for name, sp_in in inp["species"].items():
        if name in daughters:
            continue
        pe, lam, wall, src = coeffs(sp_in)
        decay = sp_in["entry"].get("decay")
        if not decay:
            sol = solve_bvp(lambda u, y, pe=pe, lam=lam: np.vstack([y[1], pe * y[1] + lam * y[0]]),
                            lambda ya, yb, wall=wall, src=src: np.array([-ya[1] + wall * ya[0] - src, yb[0]]),
                            mesh, np.vstack([1.0 - mesh, -np.ones_like(mesh)]), tol=tol, max_nodes=200000)
            if not sol.success:
                raise RuntimeError(f"solve_bvp failed for {name}: {sol.message}")
            dens[name] = float(sol.sol(0.0)[0])
            continue
        child = inp["species"][decay["daughter"]]
        pe_d, _, wall_d, src_d = coeffs(child)
        feed = sp_in["rate"] * big_l ** 2 / child["D"]

        def rhs(u, y, pe=pe, lam=lam, pe_d=pe_d, feed=feed):
            return np.vstack([y[1], pe * y[1] + lam * y[0], y[3], pe_d * y[3] - feed * y[0]])

        def bc(ya, yb, wall=wall, src=src, wall_d=wall_d, src_d=src_d):
            return np.array([-ya[1] + wall * ya[0] - src, yb[0], -ya[3] + wall_d * ya[2] - src_d, yb[2]])

        guess = np.vstack([1.0 - mesh, -np.ones_like(mesh), 1.0 - mesh, -np.ones_like(mesh)])
        sol = solve_bvp(rhs, bc, mesh, guess, tol=tol, max_nodes=200000)
        if not sol.success:
            raise RuntimeError(f"solve_bvp failed for {name} and its daughter: {sol.message}")
        dens[name], dens[decay["daughter"]] = float(sol.sol(0.0)[0]), float(sol.sol(0.0)[2])
    return {"density": dens}


def benchmark(cfg: dict) -> dict:
    """B2 checks with their tolerances (fixed in VALIDATION.md before the run)."""
    params = model_parameters(cfg)
    xs = predict.load_cross_sections(cfg)
    checks, rows = {}, []
    # 1. closed forms vs solve_bvp at every energy (relative 1e-6)
    bvp_dev = 0.0
    for e_n in cfg["energies_gev_per_n"]:
        closed = network_mid_plane(params, e_n, cfg, xs)["density"]
        numeric = boundary_value_mid_plane(params, e_n, cfg, xs)["density"]
        dev = max(abs(numeric[k] / closed[k] - 1) for k in closed)
        bvp_dev = max(bvp_dev, dev)
        rows.append({"e_n_gev": e_n, "closed": closed, "bvp": numeric, "max_rel_dev": dev})
    checks["closed_forms_equal_solve_bvp_1e-6"] = bvp_dev < 1e-6
    # 2. pure-diffusion reduction (B2-1): V_c = 0 and no decay give predict.thin_disc_ratio (1e-12)
    bc_cfg = predict.load_json(PROFILE / cfg["pure_diffusion_reference"]["config"])
    bc_xs = predict.load_cross_sections(bc_cfg)
    sec = dict(bc_cfg["secondary"], nuclide=cfg["pure_diffusion_reference"]["secondary_nuclide"])
    stable_cfg = dict(bc_cfg, transport=dict(bc_cfg["transport"], V_c_kms=0.0), secondaries=[sec])
    ref_dev = 0.0
    for e_n in bc_cfg["energies_gev_per_n"]:
        rig, b = kinematics(e_n, sec)
        ref = predict.thin_disc_ratio(bc_cfg["transport"], rig, b, bc_cfg, bc_xs)
        ours = network_mid_plane(model_parameters(stable_cfg), e_n, stable_cfg, bc_xs)["density"][sec["name"]]
        ref_dev = max(ref_dev, abs(ours / ref - 1))
    checks["V_c_0_no_decay_equals_pure_diffusion_1e-12"] = ref_dev < 1e-12
    # 3. approach: V_c -> 0 and tau_0 -> infinity (decay rate scaled down), deviation monotonic and < 1e-4
    e_mid = cfg["energies_gev_per_n"][len(cfg["energies_gev_per_n"]) // 2]
    approach = []
    for step in range(5):
        v_c, rate_scale = 10.0 ** -step, 10.0 ** (-2 * step)
        p = dict(params, V_c_kms=v_c)
        inp = _species_inputs(p, e_mid, cfg, xs)
        dev = 0.0
        for name, sp_in in inp["species"].items():
            with_terms = mid_plane_density(sp_in["q"], sp_in["D"], inp["V_c"], inp["L"], sp_in["rate"] * rate_scale,
                                           inp["h"], sp_in["loss"])
            pure = mid_plane_density(sp_in["q"], sp_in["D"], 0.0, inp["L"], 0.0, inp["h"], sp_in["loss"])
            dev = max(dev, abs(with_terms / pure - 1))
        approach.append({"V_c_kms": v_c, "decay_rate_scale": rate_scale, "max_rel_dev": dev})
    devs = [a["max_rel_dev"] for a in approach]
    checks["approach_to_pure_diffusion_monotonic"] = all(b2 < a2 for a2, b2 in zip(devs, devs[1:]))
    checks["approach_to_pure_diffusion_below_1e-4"] = devs[-1] < 1e-4
    # 4. decay conserves number: parent and daughter with the same D and loss; N_R + N_d independent of tau_0
    inp = _species_inputs(params, e_mid, cfg, xs)
    radio = next(s for s in cfg["secondaries"] if s.get("decay"))
    sp_r = inp["species"][radio["name"]]
    cons = []
    for scale in (0.0, 0.3, 1.0, 3.0, 30.0):
        n_r = mid_plane_density(sp_r["q"], sp_r["D"], inp["V_c"], inp["L"], sp_r["rate"] * scale, inp["h"],
                                sp_r["loss"])
        n_d = decay_gain_mid_plane(n_r, sp_r["D"], sp_r["rate"] * scale, sp_r["D"], inp["V_c"], inp["L"], inp["h"],
                                   sp_r["loss"])
        cons.append(n_r + n_d)
    checks["decay_conserves_number_1e-10"] = max(abs(c / cons[0] - 1) for c in cons) < 1e-10
    # 5. units: 10Be decay length sqrt(D gamma tau_0) and the convective length D/V_c, in kpc, are finite and > 0
    e_lo = cfg["energies_gev_per_n"][0]
    lengths = {"decay_length_kpc": math.sqrt(sp_r["D"] / sp_r["rate"]) / KPC_CM if sp_r["rate"] else None,
               "convective_length_kpc": (sp_r["D"] / inp["V_c"]) / KPC_CM if inp["V_c"] else None,
               "at_e_n_gev": e_mid, "lowest_e_n_gev": e_lo}
    tau0 = rest_lifetime_s(radio)
    rig, b = kinematics(e_mid, radio)
    checks["unit_conversions_consistent"] = (
        abs(tau0 * math.log(2.0) / half_life_seconds(radio.get("nuclide", radio["name"]))["value"] - 1) < 1e-12
        and abs(lorentz_gamma(e_mid, radio) * math.sqrt(1.0 - b * b) - 1) < 1e-9
        and abs(sp_r["rate"] * lorentz_gamma(e_mid, radio) * tau0 - 1) < 1e-12)
    return {"rows": rows, "approach": approach, "conservation_totals": cons, "lengths": lengths,
            "max_rel_dev": {"closed_vs_bvp": bvp_dev, "pure_diffusion_reference": ref_dev}, "checks": checks,
            "illustrative": True}


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override one model parameter")
    ap.add_argument("--xs", help="cross-section set (path relative to the profile) instead of the config's nominal")
    ap.add_argument("--benchmark", action="store_true", help="closed forms vs solve_bvp, limits and conservation")
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
        cfg = predict.load_json(opts.config)
        out = benchmark(cfg) if opts.benchmark else evaluate(cfg, predict._parse_assign(opts.set, many=False), opts.xs)
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
