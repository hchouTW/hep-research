#!/usr/bin/env python3
"""Three-flavour neutrino oscillation probabilities in vacuum and in matter of constant density (Th4).

Purpose: P(nu_alpha -> nu_beta) for every flavour pair, with the conventions stated next to the numbers. See
<plugin root>/skills/hep-theory/references/neutrino-oscillations.md.

Method (Review of Particle Physics 2026, "Neutrino Masses, Mixing, and Oscillations", read 2026-10-17):
- PMNS in the PDG parametrization, Eq. (14.34): U = R23 x U13(delta_CP) x R12, angles in [0, 90] degrees,
  delta_CP in [0, 360); Majorana phases (Eq. 14.33) do not enter oscillations and are not taken;
- the flavour-basis Hamiltonian H = [U diag(0, dm21, dm31) U^dagger + diag(A, 0, 0)] / 2E with A = 2 E V_e and
  V_e = +sqrt(2) G_F n_e (Eqs. 14.53, 14.56-14.58); for antineutrinos U -> U* and V_e -> -V_e. The neutral-current
  potential is flavour-diagonal and drops out. The amplitude is exp(-i H L), from the exact eigen-decomposition of the
  Hermitian 3 x 3 matrix, so vacuum (n_e = 0) and constant density use the same path;
- dm^2 L / 4E = k dm^2[eV^2] L[km] / E[GeV] with k = 10^3 / (4 10^9 hbar c[eV m]) = 1.267 (Eq. 14.40), from the exact
  hbar c; n_e = Y_e rho N_A; G_F, N_A and hbar c from core/constants (CODATA 2022).
Assumptions and validity: three active flavours, ultra-relativistic neutrinos, plane waves (no decoherence), constant
density along the baseline (no Earth profile), no non-standard interactions. The mass ordering is the sign of dm31.
There are no built-in parameter values: every angle, phase, splitting, the baseline, the energy and the matter
(--vacuum, or --density-g-cm3 with --ye) are inputs.
Usage: neutrino_oscillation.py --theta12 DEG --theta13 DEG --theta23 DEG --delta-cp DEG --dm21 EV2 --dm31 EV2
         --baseline-km L --energy-gev E (--vacuum | --density-g-cm3 RHO --ye YE) [--antineutrino] [--angle-unit rad]
         [--status LABEL]
Output JSON: status, status_label (default unvalidated), inputs, defaults_used, conventions, probabilities
{from: {to: P}}, unitarity (largest deviation of a row or column sum from 1), label [General method].
Exit codes: 0 ok; 2 bad input; 3 NumPy missing.
"""
from __future__ import annotations

import argparse
import cmath
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core import constants  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

FLAVOURS = ("e", "mu", "tau")
LABEL = "[General method]"
PMNS = ("PDG parametrization, Review of Particle Physics 2026, Eq. (14.34): U = R23 U13(delta_CP) R12, "
        "U_e3 = s13 exp(-i delta_CP); Majorana phases do not enter")


class OscillationError(ValueError):
    """An input outside the domain of the calculation."""


def phase_factor() -> float:
    """k in dm^2 L / (4E) = k dm^2[eV^2] L[km] / E[GeV], from the exact hbar c."""
    return 1e3 / (4e9 * constants.hbar_c("eV m").value)


def matter_potential_ev(density_g_cm3: float, ye: float) -> float:
    """V_e = sqrt(2) G_F n_e, n_e = Y_e rho N_A (cm^-3), in eV."""
    gf = constants.constant("fermi_coupling_constant").value * 1e-18  # GeV^-2 -> eV^-2
    na = constants.constant("avogadro_constant").value
    hbar_c_ev_cm = constants.hbar_c("eV m").value * 100.0
    return math.sqrt(2.0) * gf * ye * density_g_cm3 * na * hbar_c_ev_cm ** 3


def pmns(theta12: float, theta13: float, theta23: float, delta_cp: float) -> list[list[complex]]:
    """U of Eq. (14.34); angles and phase in radians."""
    s12, c12, s13, c13 = math.sin(theta12), math.cos(theta12), math.sin(theta13), math.cos(theta13)
    s23, c23 = math.sin(theta23), math.cos(theta23)
    e = cmath.exp(1j * delta_cp)
    return [[c12 * c13, s12 * c13, s13 / e],
            [-s12 * c23 - c12 * s13 * s23 * e, c12 * c23 - s12 * s13 * s23 * e, c13 * s23],
            [s12 * s23 - c12 * s13 * c23 * e, -c12 * s23 - s12 * s13 * c23 * e, c13 * c23]]


def _check(theta12, theta13, theta23, delta_cp, dm21, dm31, L_km, E_gev, density, ye, angle_unit="deg"):
    for name, v in (("theta12", theta12), ("theta13", theta13), ("theta23", theta23), ("delta_cp", delta_cp),
                    ("dm21", dm21), ("dm31", dm31), ("baseline_km", L_km), ("energy_gev", E_gev),
                    ("density", density), ("ye", ye)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise OscillationError(f"{name} must be a finite number")
    top = 90.0 if angle_unit == "deg" else math.pi / 2
    for name, v in (("theta12", theta12), ("theta13", theta13), ("theta23", theta23)):
        if not 0.0 <= v <= top:
            raise OscillationError(f"{name} must lie in [0, {top}] ({angle_unit}): the PDG convention takes the first quadrant")
    if E_gev <= 0 or L_km < 0:
        raise OscillationError("energy must be > 0 and baseline >= 0")
    if density < 0 or not 0.0 <= ye <= 1.0:
        raise OscillationError("density must be >= 0 and the electron fraction Y_e in [0, 1]")
    if dm21 < 0:
        raise OscillationError("dm21 must be >= 0 (m2 > m1 by convention); the ordering is the sign of dm31")


def probabilities(theta12, theta13, theta23, delta_cp, dm21, dm31, L_km, E_gev, density, ye, anti=False,
                  angle_unit="deg") -> dict:
    """{'matrix': {from: {to: P}}, 'unitarity': max |sum - 1|, 'potential_ev': V_e}."""
    _check(theta12, theta13, theta23, delta_cp, dm21, dm31, L_km, E_gev, density, ye, angle_unit)
    import numpy as np  # needed only to evaluate

    to_rad = math.radians if angle_unit == "deg" else float
    U = np.array(pmns(to_rad(theta12), to_rad(theta13), to_rad(theta23), to_rad(delta_cp)), dtype=complex)
    V = matter_potential_ev(density, ye)
    if anti:
        U, V = U.conj(), -V
    A = 2.0 * E_gev * 1e9 * V  # eV^2
    H2E = U @ np.diag([0.0, dm21, dm31]).astype(complex) @ U.conj().T + np.diag([A, 0.0, 0.0])  # 2 E H, eV^2
    H2E = 0.5 * (H2E + H2E.conj().T)
    w, Z = np.linalg.eigh(H2E)
    # exp(-i H L) = Z exp(-i w L / 2E) Z^dagger; w L / 2E = 2 k w L / E
    S = Z @ np.diag(np.exp(-1j * 2.0 * phase_factor() * w * L_km / E_gev)) @ Z.conj().T
    P = np.abs(S) ** 2  # P[beta, alpha] = |<beta| S |alpha>|^2
    matrix = {a: {b: float(P[j, i]) for j, b in enumerate(FLAVOURS)} for i, a in enumerate(FLAVOURS)}
    dev = float(max(np.max(np.abs(P.sum(axis=0) - 1)), np.max(np.abs(P.sum(axis=1) - 1))))
    return {"matrix": matrix, "unitarity": dev, "potential_ev": V}


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    for name in ("--theta12", "--theta13", "--theta23", "--delta-cp"):
        ap.add_argument(name, type=float, required=True, help="degrees (or --angle-unit rad)")
    ap.add_argument("--dm21", type=float, required=True, help="m2^2 - m1^2 in eV^2 (>= 0)")
    ap.add_argument("--dm31", type=float, required=True, help="m3^2 - m1^2 in eV^2 (sign = mass ordering)")
    ap.add_argument("--baseline-km", type=float, required=True)
    ap.add_argument("--energy-gev", type=float, required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--vacuum", action="store_true")
    g.add_argument("--density-g-cm3", type=float, help="constant matter density along the baseline")
    ap.add_argument("--ye", type=float, help="electron fraction Y_e (required with --density-g-cm3)")
    ap.add_argument("--antineutrino", action="store_true")
    ap.add_argument("--angle-unit", choices=("deg", "rad"), default="deg")
    add_status_argument(ap)
    a = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    defaults = [k for k in ("angle_unit", "status") if "--" + k.replace("_", "-") not in given]
    base = {"status_label": a.status, "inputs": inputs, "defaults_used": defaults}
    if a.density_g_cm3 is not None and a.ye is None:
        print(json.dumps({"status": "rejected", **base, "error": "--ye is required with --density-g-cm3 (no default)"}, indent=1))
        return exit_code("rejected")
    density, ye = (0.0, 0.0) if a.vacuum else (a.density_g_cm3, a.ye)
    try:
        r = probabilities(a.theta12, a.theta13, a.theta23, a.delta_cp, a.dm21, a.dm31, a.baseline_km, a.energy_gev,
                          density, ye, anti=a.antineutrino, angle_unit=a.angle_unit)
    except OscillationError as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    except ImportError:
        print(json.dumps({"status": "missing-dependency", **base, "error": "NumPy is needed to evaluate",
                          "install": "pip install numpy"}, indent=1))
        return exit_code("missing-dependency")
    conventions = {
        "pmns": PMNS,
        "units": "angles in " + ("degrees" if a.angle_unit == "deg" else "radians") + "; dm^2 in eV^2; L in km; E in GeV",
        "L_over_E": a.baseline_km / a.energy_gev, "phase_factor": phase_factor(),
        "neutrino": "antineutrino" if a.antineutrino else "neutrino",
        "density": "vacuum" if a.vacuum else {"rho_g_cm3": density, "ye": ye, "profile": "constant",
                                              "V_e_ev": r["potential_ev"]},
        "mass_ordering": "normal (dm31 > 0)" if a.dm31 > 0 else "inverted (dm31 < 0)" if a.dm31 < 0 else "degenerate",
        "constants": "G_F, N_A and hbar c from core/constants (CODATA 2022)",
    }
    print(json.dumps({"status": "ok", **base, "label": LABEL, "conventions": conventions,
                      "probabilities": r["matrix"], "unitarity": r["unitarity"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
