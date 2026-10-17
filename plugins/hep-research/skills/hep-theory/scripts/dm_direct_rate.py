#!/usr/bin/env python3
"""Dark-matter conventions as checked arithmetic: the spin-independent recoil rate in the standard halo model, the
Helm form factor, J and D factors of a halo, and indirect-detection flux prefactors (Th5).

Purpose: put the conventions next to the number. See <plugin root>/skills/hep-theory/references/
dark-matter-phenomenology.md. Every halo, cross-section and particle input comes from the user; nothing is defaulted.
Method (sources read 2026-10-17):
- rate: dR/dE_R = rho0 sigma_N |F(q)|^2 eta(v_min) / (2 m_chi mu_N^2) per unit target mass (PDG Review 2026, "Dark
  Matter", Eqs. 27.10-27.12; Duda, Kemper and Gondolo 2007, Eq. 5), v_min = sqrt(m_N E_R / 2 mu_N^2), and for
  isospin-conserving couplings sigma_N = sigma_n A^2 (mu_N / mu_n)^2 (Duda et al., Eq. 2), mu_n with the proton mass
  (CODATA 2022, core/constants);
- eta(v_min) = integral of f(v + v_E) / v over v > v_min, for the standard halo model: an isotropic Maxwellian
  exp(-v^2 / v0^2) in the galactic frame truncated at v_esc (Baxter et al. 2021, arXiv:2105.00599, Eq. 10; PDG
  Sec. 27.4.1), boosted by the Earth speed v_E. The angular integral is done analytically and the speed integral by
  Simpson's rule (relative precision about 1e-8);
- Helm form factor |F|^2 = (3 j1(q R1) / (q R1))^2 exp(-q^2 s^2), R1^2 = c^2 + (7/3) pi^2 a^2 - 5 s^2,
  c = 1.23 A^(1/3) - 0.60 fm, a = 0.52 fm, s = 0.9 fm (the Lewin-Smith values as given by Duda et al. 2007, Eqs. 9-12),
  q = sqrt(2 m_N E_R) / hbar;
- J = integral over the cone of half-angle theta around the halo centre of the line-of-sight integral of rho^2 (PDG
  Eq. 27.21), D the same with rho; uniform, NFW, Einasto or Burkert profiles with user parameters and a truncation
  radius;
- flux: annihilation Phi = c <sigma v> N J / (4 pi m^2) with c = 1/2 for a self-conjugate particle and 1/4 for a
  particle-antiparticle pair without asymmetry; decay Phi = N D / (4 pi m tau) (PDG Eqs. 27.18-27.20).
Assumptions and validity: elastic, spin-independent, isospin-conserving scattering; the SHM only (no streams, no
anisotropy); a time-independent v_E (annual modulation is the user's v_E per date); spherical halos; prompt yields
only (no propagation of charged products: hand those to the propagation reference). Relic-density conventions are in
the reference; no Boltzmann solver. A published reference rate to compare against: to-verify (no source read gives
one).
Usage:
  dm_direct_rate.py rate --mass-gev M --sigma-n-cm2 S --mass-number A (--nucleus-mass-gev MN | --nuclide 4He)
      --rho-gev-cm3 R --v0-km-s V0 --vesc-km-s VESC --vearth-km-s VE --er-kev E [E ...] --form-factor {helm,none}
  dm_direct_rate.py jfactor --profile {uniform,nfw,einasto,burkert} [--rho-gev-cm3 | --rho-s-gev-cm3] [--radius-kpc |
      --r-s-kpc --r-max-kpc] [--alpha A] --distance-kpc D --cone-deg THETA
  dm_direct_rate.py flux (--annihilation --sigmav-cm3-s SV --j-gev2-cm5 J --particle {self-conjugate,dirac} |
      --decay --lifetime-s T --d-gev-cm2 D) --mass-gev M --yield N
  every subcommand takes --status LABEL (default unvalidated)
Output JSON: status, status_label, inputs, defaults_used, conventions, and the result rows or values; label
[General method]. Exit codes: 0 ok; 2 bad input. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core import constants  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
HELM_A_FM, HELM_S_FM = 0.52, 0.9  # Lewin-Smith values as given by Duda, Kemper, Gondolo 2007, Eqs. 11-12
HELM_C1_FM, HELM_C0_FM = 1.23, 0.60
PARSEC_CM = 648000.0 / math.pi * 149597870700.0 * 100.0  # IAU 2012 definition
DAY_S = 86400.0
REFERENCE_RATE = "to-verify: no source read on 2026-10-17 gives a published reference rate for this configuration"


class DmError(ValueError):
    """An input outside the domain of the calculation."""


def _positive(value, name):
    if value is None or not math.isfinite(value) or value <= 0:
        raise DmError(f"{name} must be a finite number > 0")
    return float(value)


def _simpson(f, a, b, n):
    if b <= a:
        return 0.0
    n += n % 2
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += (4 if i % 2 else 2) * f(a + i * h)
    return total * h / 3.0


def eta_shm(vmin, v0, vesc, ve, n=4000):
    """eta(v_min) in s/km for the truncated Maxwellian exp(-v^2/v0^2), |v_gal| < v_esc, seen from speed v_E (km/s)."""
    for x, name in ((v0, "v0"), (vesc, "vesc"), (ve, "vearth")):
        _positive(x, name)
    if vmin < 0:
        raise DmError("v_min must be >= 0")
    z = vesc / v0
    norm = math.pi ** 1.5 * v0 ** 3 * (math.erf(z) - 2 * z / math.sqrt(math.pi) * math.exp(-z * z))
    top = min(vesc + ve, ve + 40.0 * v0)  # beyond 40 v0 the integrand is below exp(-1600)
    if vmin >= top:
        return 0.0

    def integrand(v):
        lo = abs(v - ve)
        if lo >= vesc:
            return 0.0
        hi = min(v + ve, vesc)
        return math.exp(-(lo / v0) ** 2) - math.exp(-(hi / v0) ** 2)

    kinks = sorted(k for k in (vesc - ve, ve + vesc, ve) if vmin < k < top)
    edges = [vmin, *kinks, top]
    total = sum(_simpson(integrand, a, b, max(200, int(n * (b - a) / (top - vmin)))) for a, b in zip(edges, edges[1:]))
    return math.pi * v0 ** 2 / (norm * ve) * total


def helm_radius_fm(mass_number):
    c = HELM_C1_FM * mass_number ** (1.0 / 3.0) - HELM_C0_FM
    return math.sqrt(c * c + 7.0 / 3.0 * math.pi ** 2 * HELM_A_FM ** 2 - 5.0 * HELM_S_FM ** 2)


def helm_f2(q_fm, mass_number):
    """|F(q)|^2 of the Helm form factor; q in fm^-1."""
    x = q_fm * helm_radius_fm(mass_number)
    if x < 1e-6:
        return math.exp(-(q_fm * HELM_S_FM) ** 2)
    j1 = math.sin(x) / (x * x) - math.cos(x) / x
    return (3.0 * j1 / x) ** 2 * math.exp(-(q_fm * HELM_S_FM) ** 2)


def recoil_rate(mass_gev, sigma_n_cm2, mass_number, nucleus_mass_gev, rho_gev_cm3, v0, vesc, ve, er_kev, form_factor):
    m_chi, m_n_gev = _positive(mass_gev, "--mass-gev"), _positive(nucleus_mass_gev, "nucleus mass")
    _positive(sigma_n_cm2, "--sigma-n-cm2")
    _positive(rho_gev_cm3, "--rho-gev-cm3")
    if not isinstance(mass_number, int) or mass_number < 1:
        raise DmError("--mass-number must be a positive integer")
    kg = constants.convert(1.0, "GeV/c2", "kg")
    e_j = constants.constant("elementary_charge").value
    hbar = constants.hbar("J s").value
    m_p_gev = constants.constant("proton_mass_energy", unit="GeV").value
    mu_n = m_chi * m_n_gev / (m_chi + m_n_gev)
    mu_p = m_chi * m_p_gev / (m_chi + m_p_gev)
    sigma_nucleus = sigma_n_cm2 * mass_number ** 2 * (mu_n / mu_p) ** 2  # cm^2
    rho_kg_m3 = rho_gev_cm3 * kg * 1e6
    m_chi_kg, m_nuc_kg, mu_kg = m_chi * kg, m_n_gev * kg, mu_n * kg
    rows = []
    for er in er_kev:
        _positive(er, "--er-kev")
        e_r = er * 1e3 * e_j
        vmin_km_s = math.sqrt(m_nuc_kg * e_r / (2.0 * mu_kg ** 2)) / 1e3
        q_fm = math.sqrt(2.0 * m_nuc_kg * e_r) / hbar * 1e-15
        f2 = helm_f2(q_fm, mass_number) if form_factor == "helm" else 1.0
        eta_s_m = eta_shm(vmin_km_s, v0, vesc, ve) * 1e-3
        rate_si = rho_kg_m3 * sigma_nucleus * 1e-4 * f2 * eta_s_m / (2.0 * m_chi_kg * mu_kg ** 2)  # 1/(kg s J)
        rows.append({"er_kev": er, "vmin_km_s": vmin_km_s, "q_fm": q_fm, "form_factor_sq": f2,
                     "eta_s_km": eta_s_m * 1e3, "dR_dE_per_kg_day_kev": rate_si * DAY_S * 1e3 * e_j})
    total = None
    if len(rows) > 1:
        total = sum(0.5 * (a["dR_dE_per_kg_day_kev"] + b["dR_dE_per_kg_day_kev"]) * (b["er_kev"] - a["er_kev"])
                    for a, b in zip(rows, rows[1:]))
    return {"rows": rows, "sigma_nucleus_cm2": sigma_nucleus, "mu_N_gev": mu_n,
            "rate_trapezoid_per_kg_day": total}


def density(halo, r_kpc):
    p = halo["profile"]
    if p == "uniform":
        return halo["rho"] if r_kpc <= halo["radius_kpc"] else 0.0
    if r_kpc > halo["r_max_kpc"]:
        return 0.0
    x = max(r_kpc, 1e-12) / halo["r_s_kpc"]
    if p == "nfw":
        return halo["rho_s"] / (x * (1 + x) ** 2)
    if p == "einasto":
        return halo["rho_s"] * math.exp(-2.0 / halo["alpha"] * (x ** halo["alpha"] - 1.0))
    if p == "burkert":
        return halo["rho_s"] / ((1 + x) * (1 + x * x))
    raise DmError(f"unknown profile {p}")


def j_factor(halo, distance_kpc, cone_deg, n=400):
    """J (GeV^2 cm^-5) and D (GeV cm^-2) over a cone of half-angle cone_deg around the direction to the halo centre."""
    d = _positive(distance_kpc, "--distance-kpc")
    theta = math.radians(_positive(cone_deg, "--cone-deg"))
    if theta >= math.pi / 2:
        raise DmError("--cone-deg must be below 90")
    r_out = halo["radius_kpc"] if halo["profile"] == "uniform" else halo["r_max_kpc"]

    def los(psi):
        b = d * math.sin(psi)  # impact parameter
        if b >= r_out:
            return 0.0, 0.0
        half = math.sqrt(r_out * r_out - b * b)
        lo, hi = d * math.cos(psi) - half, d * math.cos(psi) + half
        lo = max(lo, 0.0)
        t_lo, t_hi = lo - d * math.cos(psi), hi - d * math.cos(psi)  # t along the line, r = sqrt(t^2 + b^2)
        bb = max(b, 1e-9 * r_out)
        u_lo, u_hi = math.asinh(t_lo / bb), math.asinh(t_hi / bb)

        def f2(u):
            r = min(bb * math.cosh(u), r_out)  # the end points sit on the boundary; rounding must not drop them
            return density(halo, r) ** 2 * bb * math.cosh(u)

        def f1(u):
            r = min(bb * math.cosh(u), r_out)
            return density(halo, r) * bb * math.cosh(u)

        return _simpson(f2, u_lo, u_hi, n), _simpson(f1, u_lo, u_hi, n)

    # the line of sight leaves the halo at psi_edge (a square-root edge): integrate up to it in u = sqrt(edge - psi)
    psi_edge = math.asin(r_out / d) if r_out < d else math.pi / 2
    top = min(theta, psi_edge)

    def cone(k):
        if top < psi_edge:
            return _simpson(lambda s: math.sin(s) * los(s)[k], 0.0, top, n)
        w = math.sqrt(top)
        return _simpson(lambda v: 2 * v * math.sin(top - v * v) * los(top - v * v)[k], 0.0, w, n)

    j = cone(0) * 2 * math.pi
    dd = cone(1) * 2 * math.pi
    kpc_cm = 1e3 * PARSEC_CM
    return {"J_gev2_cm5": j * kpc_cm, "D_gev_cm2": dd * kpc_cm, "solid_angle_sr": 2 * math.pi * (1 - math.cos(theta))}


def flux(args):
    m = _positive(args.mass_gev, "--mass-gev")
    n = _positive(args.yield_, "--yield")
    if args.annihilation:
        c = {"self-conjugate": 0.5, "dirac": 0.25}[args.particle]
        sv, j = _positive(args.sigmav_cm3_s, "--sigmav-cm3-s"), _positive(args.j_gev2_cm5, "--j-gev2-cm5")
        return {"flux_cm2_s": c * sv * n * j / (4 * math.pi * m * m), "c": c,
                "formula": "Phi = c <sigma v> N J / (4 pi m^2) (PDG Eqs. 27.18, 27.20, 27.21)"}
    tau, dfac = _positive(args.lifetime_s, "--lifetime-s"), _positive(args.d_gev_cm2, "--d-gev-cm2")
    return {"flux_cm2_s": n * dfac / (4 * math.pi * m * tau), "formula": "Phi = N D / (4 pi m tau) (PDG Eqs. 27.19, 27.20)"}


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("rate", help="spin-independent recoil rate in the standard halo model")
    p.add_argument("--mass-gev", type=float, required=True)
    p.add_argument("--sigma-n-cm2", type=float, required=True, help="per-nucleon SI cross section")
    p.add_argument("--mass-number", type=int, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--nucleus-mass-gev", type=float)
    g.add_argument("--nuclide", help="a nuclide of core/constants (e.g. 4He) for the bare-nucleus mass")
    p.add_argument("--rho-gev-cm3", type=float, required=True)
    p.add_argument("--v0-km-s", type=float, required=True)
    p.add_argument("--vesc-km-s", type=float, required=True)
    p.add_argument("--vearth-km-s", type=float, required=True)
    p.add_argument("--er-kev", type=float, nargs="+", required=True)
    p.add_argument("--form-factor", choices=("helm", "none"), required=True)
    p = sub.add_parser("jfactor", help="J and D factors of a spherical halo over a cone")
    p.add_argument("--profile", choices=("uniform", "nfw", "einasto", "burkert"), required=True)
    p.add_argument("--rho-gev-cm3", type=float, help="uniform density")
    p.add_argument("--radius-kpc", type=float, help="uniform radius")
    p.add_argument("--rho-s-gev-cm3", type=float)
    p.add_argument("--r-s-kpc", type=float)
    p.add_argument("--r-max-kpc", type=float)
    p.add_argument("--alpha", type=float, help="Einasto shape")
    p.add_argument("--distance-kpc", type=float, required=True)
    p.add_argument("--cone-deg", type=float, required=True)
    p = sub.add_parser("flux", help="indirect-detection flux from J or D")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--annihilation", action="store_true")
    g.add_argument("--decay", action="store_true")
    p.add_argument("--sigmav-cm3-s", type=float)
    p.add_argument("--j-gev2-cm5", type=float)
    p.add_argument("--particle", choices=("self-conjugate", "dirac"))
    p.add_argument("--lifetime-s", type=float)
    p.add_argument("--d-gev-cm2", type=float)
    p.add_argument("--mass-gev", type=float, required=True)
    p.add_argument("--yield", dest="yield_", type=float, required=True, help="particles per annihilation or decay")
    for sp in sub.choices.values():
        add_status_argument(sp)
    a = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs, "defaults_used": [k for k in ("status",) if f"--{k}" not in given]}
    try:
        if a.command == "rate":
            if a.nuclide:
                rec = constants.nuclide(a.nuclide)
                mn = constants.nuclear_mass_gev(rec["Z"], rec["A"])
            else:
                mn = a.nucleus_mass_gev
            out = recoil_rate(a.mass_gev, a.sigma_n_cm2, a.mass_number, mn, a.rho_gev_cm3, a.v0_km_s, a.vesc_km_s,
                              a.vearth_km_s, a.er_kev, a.form_factor)
            conv = {"rate": "dR/dE = rho0 sigma_N F^2 eta / (2 m_chi mu_N^2), sigma_N = sigma_n A^2 (mu_N/mu_n)^2",
                    "halo": "SHM: Maxwellian exp(-v^2/v0^2) truncated at v_esc, boosted by v_E (user values)",
                    "form_factor": "Helm, Lewin-Smith parameters (c = 1.23 A^1/3 - 0.60 fm, a = 0.52 fm, s = 0.9 fm)"
                    if a.form_factor == "helm" else "none (point-like nucleus)",
                    "units": "dR/dE in events / (kg day keV); eta in s/km",
                    "reference_rate": REFERENCE_RATE}
        elif a.command == "jfactor":
            if a.profile == "uniform":
                halo = {"profile": "uniform", "rho": _positive(a.rho_gev_cm3, "--rho-gev-cm3"),
                        "radius_kpc": _positive(a.radius_kpc, "--radius-kpc")}
            else:
                halo = {"profile": a.profile, "rho_s": _positive(a.rho_s_gev_cm3, "--rho-s-gev-cm3"),
                        "r_s_kpc": _positive(a.r_s_kpc, "--r-s-kpc"), "r_max_kpc": _positive(a.r_max_kpc, "--r-max-kpc")}
                if a.profile == "einasto":
                    halo["alpha"] = _positive(a.alpha, "--alpha")
            out = j_factor(halo, a.distance_kpc, a.cone_deg)
            conv = {"J": "J = integral over the cone of the line-of-sight integral of rho^2 (PDG Eq. 27.21)",
                    "units": "J in GeV^2 cm^-5, D in GeV cm^-2 (cone-integrated); distances in kpc (IAU parsec)"}
        else:
            if a.annihilation and (a.sigmav_cm3_s is None or a.j_gev2_cm5 is None or a.particle is None):
                raise DmError("--annihilation needs --sigmav-cm3-s, --j-gev2-cm5 and --particle")
            if a.decay and (a.lifetime_s is None or a.d_gev_cm2 is None):
                raise DmError("--decay needs --lifetime-s and --d-gev-cm2")
            out = flux(a)
            conv = {"units": "flux in cm^-2 s^-1 (integrated over the J or D region); prompt yield only"}
    except (DmError, constants.ConstantsError) as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": "ok", **base, "label": LABEL, "conventions": conv, **out}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
