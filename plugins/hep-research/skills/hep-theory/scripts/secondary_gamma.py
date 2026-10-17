#!/usr/bin/env python3
"""Astroparticle secondaries: gamma rays from neutral-pion decay, neutrino flavour ratios after averaged oscillations,
and head-on reaction thresholds on a target photon (Th11).

Purpose: the exact kinematics behind three standard astroparticle numbers. See <plugin root>/skills/hep-theory/
references/astroparticle-essentials.md.
Method:
- pi0: each pi0 -> gamma gamma decays isotropically in its rest frame, so a pion of energy E_pi gives a flat photon
  spectrum between E+- = (E_pi +- p_pi) / 2 with height 2 / p_pi (two photons per pion). For a user pion spectrum
  dN/dE_pi, dN_gamma/dE_gamma = 2 integral from E_pi,min of (dN/dE_pi) / p_pi dE_pi with
  E_pi,min = E_gamma + m_pi^2 / (4 E_gamma); with E_pi = m_pi cosh u the integrand becomes (dN/dE_pi) du, free of the
  1/p_pi end point, and is integrated by Simpson's rule. The tabulated spectrum is interpolated linearly in log-log and
  is zero outside its range. m_pi0 from core/constants (PDG 2026);
- flavour: averaged over many oscillation lengths, P(alpha -> beta) = sum_i |U_alpha i|^2 |U_beta i|^2 with U in the
  PDG parametrization (Review of Particle Physics 2026, Eq. 14.34; the CP phase enters through the moduli). The Earth
  fractions are sum_alpha f_alpha P(alpha -> beta) for a source ratio f;
- threshold: for a projectile of mass m meeting a photon of energy eps head on, s = m^2 + 2 eps (E + p); the threshold
  is s = (sum of final masses)^2, so E + p = K = (M^2 - m^2) / (2 eps) and E = (K^2 + m^2) / (2 K). The output checks
  the invariant mass at threshold: with core/kinematics/fourvector.py for moderate boosts, and from s = m^2 + 2 eps (E + p)
  where the four-vector sum loses precision (E above 1e4 times the larger of m and eps). Processes: pair (gamma gamma -> e+ e-),
  photopion (p gamma -> p pi0), or --final masses with --projectile-gev.
Assumptions and validity: isotropic pi0 decay, no other photon sources; three-flavour averaged oscillation (no matter
effects, no decoherence beyond averaging); a head-on collision gives the lowest threshold (other angles need more).
Usage:
  secondary_gamma.py pi0 (--spectrum PI.json | --monoenergetic-gev E) --e-gamma-gev E [E ...]
  secondary_gamma.py flavour --theta12 DEG --theta13 DEG --theta23 DEG --delta-cp DEG --source A:B:C
  secondary_gamma.py threshold --target-photon-ev EPS (--process {pair,photopion} | --projectile-gev M --final M [M ...])
  every subcommand takes --status LABEL (default unvalidated)
Input: PI.json {"e_gev": [...], "dn_de": [...]} (pion total energy and dN/dE, any normalization, values > 0).
Output JSON: status, status_label, inputs, defaults_used, conventions and the result; label [General method].
Exit codes: 0 ok; 2 bad input. Standard library only.
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
from core.kinematics import fourvector  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
FLAVOURS = ("e", "mu", "tau")


class SecondaryError(ValueError):
    """An input outside the domain of the calculation."""


def _interp_loglog(spec, e):
    xs, ys = spec["e_gev"], spec["dn_de"]
    if e < xs[0] or e > xs[-1]:
        return 0.0
    for i in range(len(xs) - 1):
        if xs[i] <= e <= xs[i + 1]:
            t = (math.log(e) - math.log(xs[i])) / (math.log(xs[i + 1]) - math.log(xs[i]))
            return math.exp(math.log(ys[i]) + t * (math.log(ys[i + 1]) - math.log(ys[i])))
    return 0.0


def check_spectrum(spec):
    try:
        xs, ys = [float(x) for x in spec["e_gev"]], [float(y) for y in spec["dn_de"]]
    except (KeyError, TypeError, ValueError) as exc:
        raise SecondaryError("the spectrum needs e_gev and dn_de lists of numbers") from exc
    if len(xs) < 2 or len(xs) != len(ys) or any(b <= a for a, b in zip(xs, xs[1:])):
        raise SecondaryError("e_gev must be increasing with at least two points, as long as dn_de")
    if any(not math.isfinite(v) or v <= 0 for v in xs + ys):
        raise SecondaryError("energies and dN/dE must be finite and > 0 (log-log interpolation)")
    return {"e_gev": xs, "dn_de": ys}


def gamma_spectrum(spec, e_gamma, m_pi, n=2000):
    """dN_gamma/dE_gamma = 2 integral of (dN/dE_pi) du from u_min, E_pi = m_pi cosh u."""
    if e_gamma <= 0:
        raise SecondaryError("E_gamma must be > 0")
    e_min = max(e_gamma + m_pi * m_pi / (4.0 * e_gamma), spec["e_gev"][0], m_pi)
    e_max = spec["e_gev"][-1]
    if e_min >= e_max:
        return 0.0
    u_lo, u_hi = math.acosh(e_min / m_pi), math.acosh(e_max / m_pi)
    h = (u_hi - u_lo) / n
    total = 0.0
    for i in range(n + 1):
        w = 1 if i in (0, n) else (4 if i % 2 else 2)
        total += w * _interp_loglog(spec, m_pi * math.cosh(u_lo + i * h))
    return 2.0 * total * h / 3.0


def pmns_moduli(t12, t13, t23, dcp):
    s12, c12, s13, c13 = math.sin(t12), math.cos(t12), math.sin(t13), math.cos(t13)
    s23, c23 = math.sin(t23), math.cos(t23)
    e = cmath.exp(1j * dcp)
    u = [[c12 * c13, s12 * c13, s13 * cmath.exp(-1j * dcp)],
         [-s12 * c23 - c12 * s23 * s13 * e, c12 * c23 - s12 * s23 * s13 * e, s23 * c13],
         [s12 * s23 - c12 * c23 * s13 * e, -c12 * s23 - s12 * c23 * s13 * e, c23 * c13]]
    return [[abs(x) ** 2 for x in row] for row in u]


def averaged_ratio(source, angles_deg):
    if len(source) != 3 or any(not math.isfinite(x) or x < 0 for x in source) or sum(source) <= 0:
        raise SecondaryError("--source is three non-negative numbers A:B:C (nu_e : nu_mu : nu_tau), not all zero")
    u2 = pmns_moduli(*(math.radians(a) for a in angles_deg))
    p = [[sum(u2[a][i] * u2[b][i] for i in range(3)) for b in range(3)] for a in range(3)]
    f = [x / sum(source) for x in source]
    return [sum(f[a] * p[a][b] for a in range(3)) for b in range(3)], p


def head_on_threshold(m_projectile, final_masses, eps_gev):
    if not math.isfinite(eps_gev) or eps_gev <= 0:
        raise SecondaryError("--target-photon-ev must be > 0")
    big_m = sum(final_masses)
    if big_m <= m_projectile:
        raise SecondaryError("the final state must be heavier than the projectile")
    k = (big_m * big_m - m_projectile * m_projectile) / (2.0 * eps_gev)
    e = (k * k + m_projectile * m_projectile) / (2.0 * k)
    p = math.sqrt(max(e * e - m_projectile * m_projectile, 0.0))
    if e < 1e4 * max(m_projectile, eps_gev, 1e-12):
        # moderate boosts: the four-vector sum (core/kinematics/fourvector.py) is precise
        check = fourvector.invariant_mass((e, 0.0, 0.0, p), (eps_gev, 0.0, 0.0, -eps_gev))
    else:
        # at astrophysical thresholds E^2 - p^2 cancels catastrophically: use s = m^2 + 2 eps (E + p)
        check = math.sqrt(m_projectile * m_projectile + 2.0 * eps_gev * (e + p))
    return e, check, big_m


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("pi0", help="gamma rays from a pi0 spectrum")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--spectrum")
    g.add_argument("--monoenergetic-gev", type=float)
    p.add_argument("--e-gamma-gev", type=float, nargs="+", required=True)
    p = sub.add_parser("flavour", help="neutrino flavour fractions after averaged oscillations")
    for n in ("--theta12", "--theta13", "--theta23", "--delta-cp"):
        p.add_argument(n, type=float, required=True, help="degrees")
    p.add_argument("--source", required=True, help="nu_e:nu_mu:nu_tau at the source, e.g. 1:2:0")
    p = sub.add_parser("threshold", help="head-on threshold on a target photon")
    p.add_argument("--target-photon-ev", type=float, required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--process", choices=("pair", "photopion"))
    g.add_argument("--projectile-gev", type=float)
    p.add_argument("--final", type=float, nargs="+", help="final-state masses in GeV (with --projectile-gev)")
    for sp in sub.choices.values():
        add_status_argument(sp)
    a = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs, "defaults_used": [k for k in ("status",) if f"--{k}" not in given]}
    try:
        if a.command == "pi0":
            mq = constants.particle("pi0", "mass", unit="GeV")
            m_pi = mq.value
            if a.monoenergetic_gev is not None:
                e = a.monoenergetic_gev
                if not math.isfinite(e) or e <= m_pi:
                    raise SecondaryError("--monoenergetic-gev must exceed the pi0 mass")
                p_pi = math.sqrt(e * e - m_pi * m_pi)
                lo, hi = (e - p_pi) / 2.0, (e + p_pi) / 2.0
                rows = [{"e_gamma_gev": x, "dn_de_gamma": 2.0 / p_pi if lo <= x <= hi else 0.0} for x in a.e_gamma_gev]
                out = {"rows": rows, "box": {"e_minus_gev": lo, "e_plus_gev": hi, "height": 2.0 / p_pi}}
            else:
                try:
                    spec = check_spectrum(json.loads(Path(a.spectrum).read_text(encoding="utf-8")))
                except (OSError, ValueError) as exc:
                    raise SecondaryError(f"cannot read {a.spectrum}: {exc}") from exc
                rows = [{"e_gamma_gev": x, "dn_de_gamma": gamma_spectrum(spec, x, m_pi)} for x in a.e_gamma_gev]
                out = {"rows": rows}
            out["pi0_mass"] = mq.to_dict()
            conv = {"pi0": "dN_gamma/dE = 2 integral (dN/dE_pi)/p_pi dE_pi from E_gamma + m_pi^2/(4 E_gamma); isotropic decay",
                    "units": "energies in GeV; dN/dE_gamma in the pion spectrum's normalization per GeV"}
        elif a.command == "flavour":
            try:
                source = [float(x) for x in a.source.split(":")]
            except ValueError as exc:
                raise SecondaryError("--source is A:B:C") from exc
            ratio, pmat = averaged_ratio(source, (a.theta12, a.theta13, a.theta23, a.delta_cp))
            out = {"earth_fractions": ratio, "flavours": list(FLAVOURS), "averaged_probabilities": pmat}
            conv = {"pmns": "PDG parametrization (Review of Particle Physics 2026, Eq. 14.34)",
                    "averaging": "P(a -> b) = sum_i |U_ai|^2 |U_bi|^2 (oscillation phases averaged out)"}
        else:
            eps = a.target_photon_ev * 1e-9
            if a.process == "pair":
                me = constants.particle("electron", "mass", unit="GeV").value
                m_proj, finals = 0.0, [me, me]
            elif a.process == "photopion":
                mp = constants.particle("proton", "mass", unit="GeV").value
                m_proj, finals = mp, [mp, constants.particle("pi0", "mass", unit="GeV").value]
            else:
                if not a.final:
                    raise SecondaryError("--projectile-gev needs --final masses")
                m_proj, finals = a.projectile_gev, a.final
                if not math.isfinite(m_proj) or m_proj < 0 or any(not math.isfinite(x) or x < 0 for x in finals):
                    raise SecondaryError("masses must be finite and >= 0")
            e, check, big_m = head_on_threshold(m_proj, finals, eps)
            out = {"threshold_gev": e, "masses_gev": {"projectile": m_proj, "final": finals, "final_sum": big_m},
                   "invariant_mass_check_gev": check}
            conv = {"threshold": "head on: E = (K^2 + m^2)/(2K), K = (M^2 - m^2)/(2 eps); masses from core/constants (PDG 2026)",
                    "units": "eps in eV, energies in GeV"}
    except (SecondaryError, constants.ConstantsError) as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": "ok", **base, "label": LABEL, "conventions": conv, **out}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
