#!/usr/bin/env python3
"""Synchrotron and inverse-Compton energy losses of relativistic electrons and positrons, the loss time and the
diffusion distance (Th2).

Purpose: the loss rate b(E) = b_sync + b_IC that sets how far a cosmic-ray electron travels before it loses its energy.
See <plugin root>/skills/hep-theory/references/cosmic-ray-propagation.md, "Electron and positron energy losses".
Method (Moderski, Sikora, Coppi and Aharonian 2005, MNRAS 363, 954, arXiv:astro-ph/0504388, read 2026-10-17 and
2026-10-22; their Eqs. 1 and 7 write gamma^2, the ultra-relativistic limit of the exact gamma^2 - 1 = beta^2 gamma^2
used here):
- isotropic electrons: b_sync = (4/3) sigma_T c (gamma^2 - 1) U_B with U_B = B^2 / 8 pi (Gaussian; Eq. 7);
- inverse Compton on each declared photon field: b_IC = (4/3) sigma_T c (gamma^2 - 1) U_rad F_KN (Eq. 1). A field
  given as U:thomson is in the Thomson limit (F_KN = 1). A field given as U:T (temperature in K) is a Planck field
  treated as mono-energetic at eps0 = 2.8 k T (Section 2.1), with b~ = 4 gamma eps0 / (m_e c^2) and, by --kn:
  thomson (F_KN = 1), approx (F_KN = (1 + b~)^-1.5, Eq. 3; against the exact function it is within 3% for
  b~ <= 1, within 40% up to b~ = 1e3 and a factor 3 off at 1e4, measured here) or exact (F_KN = 9 g(b~) / b~^3,
  Eqs. A10 and A12, isotropic photons on isotropic electrons);
- tau = E / b; with --diffusion-cm2-s D (at this energy) the distance sqrt(4 D tau).
Assumptions and validity: gamma >> 1 (E >= 0.01 GeV is required), continuous losses (no catastrophic IC steps), a
tangled field, isotropic photon fields; ionization, bremsstrahlung and adiabatic losses are not included. The exact
F_KN is evaluated for b~ >= 1e-3; below that the code uses Eq. (3), whose difference from the exact function there is
below 2e-3 (tested). sigma_T, m_e c^2, k_B, c and e come from core/constants (CODATA 2022). Years are Julian
(365.25 d); 1 pc = 648000 / pi au (IAU 2012 definition, au = 149 597 870 700 m).
Usage: lepton_energy_losses.py --energy-gev E [E ...] --b-microgauss B --field U:T|U:thomson [--field ...]
         --kn {thomson,approx,exact} [--diffusion-cm2-s D] [--status LABEL]
       (U in eV/cm^3, T in K)
Output JSON: status, status_label (default unvalidated), inputs, defaults_used, conventions, rows (per energy: gamma,
u_b_ev_cm3, b_sync_gev_s, b_ic_gev_s per field, b_tilde per field, f_kn per field, b_total_gev_s, tau_s, tau_yr,
distance_cm, distance_kpc), label [General method].
Exit codes: 0 ok; 2 bad input. Standard library only.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

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
EXACT_MIN_B = 1e-3
PLANCK_MONO_FACTOR = 2.8  # eps0 = 2.8 kT for a Planckian treated as mono-energetic (Moderski et al. 2005, Sec. 2.1)
JULIAN_YEAR_S = 365.25 * 86400.0
PARSEC_M = 648000.0 / math.pi * 149597870700.0


class LossError(ValueError):
    """An input outside the domain of the calculation."""


def _li2_pos(y: float) -> float:
    """Li2(y) for 0 <= y <= 0.5 by its power series."""
    total, term, k = 0.0, y, 1
    while k < 200:
        total += term / (k * k)
        k += 1
        term *= y
        if term < 1e-18:
            break
    return total


def li2_neg(x: float) -> float:
    """The dilogarithm Li2(-x) for x >= 0 (Landen identity for x <= 1, inversion for x > 1)."""
    if x < 0:
        raise LossError("li2_neg takes x >= 0")
    if x == 0:
        return 0.0
    if x > 1:
        return -math.pi ** 2 / 6 - 0.5 * math.log(x) ** 2 - li2_neg(1.0 / x)
    # Landen: Li2(z) = -Li2(z / (z - 1)) - (1/2) ln^2(1 - z), z = -x, z / (z - 1) = x / (1 + x) in (0, 1/2]
    return -_li2_pos(x / (1.0 + x)) - 0.5 * math.log1p(x) ** 2


def g_function(b: float) -> float:
    """Moderski et al. 2005, Eq. (A10): g = (b/2 + 6 + 6/b) ln(1 + b) - (11/12 b^3 + 6 b^2 + 9 b + 4) / (1 + b)^2
    - 2 + 2 Li2(-b). Its small-b expansion starts at b^3 / 9, so F_KN -> 1 (tested)."""
    return ((0.5 * b + 6.0 + 6.0 / b) * math.log1p(b)
            - (11.0 / 12.0 * b ** 3 + 6.0 * b ** 2 + 9.0 * b + 4.0) / (1.0 + b) ** 2
            - 2.0 + 2.0 * li2_neg(b))


def f_kn_exact(b: float) -> float:
    """F_KN = 9 g(b) / b^3 (Eq. A12); for b < 1e-3 the Eq. (3) approximation (see the module docstring)."""
    if b < EXACT_MIN_B:
        return f_kn_approx(b)
    return 9.0 * g_function(b) / b ** 3


def f_kn_approx(b: float) -> float:
    """F_KN = (1 + b)^-1.5 (Eq. 3)."""
    return (1.0 + b) ** -1.5


def parse_field(text: str) -> tuple[float, float | None]:
    try:
        u, t = text.split(":")
        u_val = float(u)
        t_val = None if t.strip().lower() == "thomson" else float(t)
    except ValueError as exc:
        raise LossError(f"--field is U:T (eV/cm^3 : kelvin) or U:thomson, got {text!r}") from exc
    if not (math.isfinite(u_val) and u_val >= 0):
        raise LossError("a field energy density must be >= 0")
    if t_val is not None and not (math.isfinite(t_val) and t_val > 0):
        raise LossError("a field temperature must be > 0 K")
    return u_val, t_val


def losses(energies_gev, b_microgauss, fields, kn, diffusion_cm2_s=None) -> list[dict]:
    if not math.isfinite(b_microgauss) or b_microgauss < 0:
        raise LossError("--b-microgauss must be >= 0")
    if diffusion_cm2_s is not None and not (math.isfinite(diffusion_cm2_s) and diffusion_cm2_s > 0):
        raise LossError("--diffusion-cm2-s must be > 0")
    me_gev = constants.constant("electron_mass_energy", unit="GeV").value
    sigma_t = constants.constant("thomson_cross_section").value  # m^2
    c = constants.constant("speed_of_light").value
    e = constants.constant("elementary_charge").value  # J per eV
    k_ev = constants.constant("boltzmann_constant").value / e  # eV/K
    gev_j = 1e9 * e
    b_gauss = b_microgauss * 1e-6
    u_b_ev_cm3 = b_gauss ** 2 / (8.0 * math.pi) * 1e-7 / e  # erg/cm^3 -> J/cm^3 -> eV/cm^3
    rows = []
    for energy in energies_gev:
        if not math.isfinite(energy) or energy < 0.01:
            raise LossError("energies must be >= 0.01 GeV (gamma >> 1)")
        gamma = energy / me_gev
        pref = 4.0 / 3.0 * sigma_t * c * (gamma * gamma - 1.0) / gev_j  # GeV/s per (J/m^3)
        b_sync = pref * u_b_ev_cm3 * 1e6 * e
        b_ic, b_tilde, f_kn = [], [], []
        for u, temp in fields:
            if temp is None or kn == "thomson":
                f, bt = 1.0, None if temp is None else 4.0 * gamma * PLANCK_MONO_FACTOR * k_ev * temp / (me_gev * 1e9)
            else:
                bt = 4.0 * gamma * PLANCK_MONO_FACTOR * k_ev * temp / (me_gev * 1e9)
                f = f_kn_exact(bt) if kn == "exact" else f_kn_approx(bt)
            b_ic.append(pref * u * 1e6 * e * f)
            b_tilde.append(bt)
            f_kn.append(f)
        total = b_sync + sum(b_ic)
        if total <= 0:
            raise LossError("no losses: give a field or a magnetic field")
        tau = energy / total
        row = {"energy_gev": energy, "gamma": gamma, "u_b_ev_cm3": u_b_ev_cm3, "b_sync_gev_s": b_sync,
               "b_ic_gev_s": b_ic, "b_tilde": b_tilde, "f_kn": f_kn, "b_total_gev_s": total, "tau_s": tau,
               "tau_yr": tau / JULIAN_YEAR_S}
        if diffusion_cm2_s is not None:
            dist = math.sqrt(4.0 * diffusion_cm2_s * tau)
            row.update(distance_cm=dist, distance_kpc=dist / (1e3 * PARSEC_M * 100.0))
        rows.append(row)
    return rows


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--energy-gev", type=float, nargs="+", required=True)
    ap.add_argument("--b-microgauss", type=float, required=True)
    ap.add_argument("--field", action="append", default=[], help="U:T (eV/cm^3 : K) or U:thomson; repeat per field")
    ap.add_argument("--kn", choices=("thomson", "approx", "exact"), required=True)
    ap.add_argument("--diffusion-cm2-s", type=float)
    add_status_argument(ap)
    a = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    defaults = [k for k in ("status",) if f"--{k}" not in given]
    base = {"status_label": a.status, "inputs": inputs, "defaults_used": defaults}
    try:
        fields = [parse_field(f) for f in a.field]
        if a.kn != "thomson" and any(t is None for _, t in fields):
            raise LossError("--kn approx or exact needs a temperature for every field (U:T); U:thomson only with --kn thomson")
        rows = losses(a.energy_gev, a.b_microgauss, fields, a.kn, a.diffusion_cm2_s)
    except LossError as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    conventions = {
        "synchrotron": "b = (4/3) sigma_T c (gamma^2 - 1) U_B, U_B = B^2 / 8 pi (Gaussian), isotropic pitch angles",
        "inverse_compton": "b = (4/3) sigma_T c (gamma^2 - 1) U F_KN; Planck field as mono-energetic at 2.8 kT",
        "klein_nishina": {"thomson": "F_KN = 1", "approx": "F_KN = (1 + b~)^-1.5 (Moderski et al. 2005 Eq. 3)",
                          "exact": "F_KN = 9 g(b~)/b~^3 (Eqs. A10, A12); Eq. 3 below b~ = 1e-3"}[a.kn],
        "source": "Moderski, Sikora, Coppi, Aharonian 2005 (arXiv:astro-ph/0504388); constants: core/constants (CODATA 2022)",
        "units": "E in GeV; b in GeV/s; tau in s and Julian years; distance in cm and kpc",
    }
    print(json.dumps({"status": "ok", **base, "label": LABEL, "conventions": conventions, "rows": rows}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
