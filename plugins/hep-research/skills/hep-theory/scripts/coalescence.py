#!/usr/bin/env python3
"""Coalescence of light (anti)nuclei: B_A and p0, the coalesced invariant yield, and the factors of the Wigner-function
model (Th6).

Purpose: keep the coalescence convention explicit when an (anti)deuteron or (anti)helium yield is built from an
(anti)nucleon yield. See <plugin root>/skills/hep-theory/references/light-nuclei-coalescence.md.
Method (sources read 2026-10-17):
- the standard model: E_A d^3N_A/dp_A^3 = B_A (E_p d^3N_p/dp_p^3)^A at p_A = A p_p, with equal proton and neutron
  yields (Duperray et al. 2005, Eqs. 1-4), and B_A = A (4 pi p0^3 / (3 m_N))^(A-1) (Kachelriess, Ostapchenko and
  Tjemsland 2019, Eq. 2), equal to Duperray et al.'s Eq. 5, (4 pi p0^3 / 3)^(A-1) m_A / m_p^A, when m_A = A m_N.
  The output gives both, with m_A the bare-nucleus mass from core/constants when --nuclide is given;
- the Wigner-function model for the deuteron (Kachelriess et al. 2019, Eqs. 10-16): with a Gaussian deuteron wave
  function of size d and nucleons spread in space with width sigma, the coalescence weight of a pair with relative
  momentum q (half the momentum difference) is 3 zeta exp(-q^2 d^2), zeta = (d^2 / (d^2 + 4 sigma^2))^(3/2) <= 1,
  where 3 = 8 S with the spin-isospin factor S = 3/8 (S = 1/12 for three nucleons, their Eq. 41). q d is made
  dimensionless with hbar c (exact, core/constants).
Assumptions and validity: equal neutron and proton yields and uncorrelated nucleons for `yield`; an event generator
that supplies nucleon pairs for the Wigner weights. No p0, d or sigma is built in: the values fitted in the literature
depend on the reaction and energy (the reference lists the ones read).
Usage:
  coalescence.py ba (--p0-gev P0 | --b-a B) --mass-number A --nucleon-mass {proton,neutron,GEV} [--nuclide 2H]
  coalescence.py yield --spectrum SPEC.json --mass-number A --b-a B
  coalescence.py wigner --d-fm D --sigma-fm S --q-gev Q [Q ...]
  every subcommand takes --status LABEL (default unvalidated)
Input: SPEC.json {"p_gev": [...], "invariant_yield_gev_minus2": [...]} (E d^3N/dp^3 per nucleon, c = 1).
Output JSON: status, status_label, inputs, defaults_used, conventions and the result; label [General method].
Exit codes: 0 ok; 2 bad input. Standard library only.
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
SPIN_ISOSPIN = {2: 3.0 / 8.0, 3: 1.0 / 12.0}  # Kachelriess et al. 2019, Sec. 2.1 and Eq. 41


class CoalescenceError(ValueError):
    """An input outside the domain of the calculation."""


def _positive(x, name):
    if x is None or not math.isfinite(x) or x <= 0:
        raise CoalescenceError(f"{name} must be a finite number > 0")
    return float(x)


def _mass_number(a):
    if not isinstance(a, int) or a < 2:
        raise CoalescenceError("--mass-number must be an integer >= 2")
    return a


def b_from_p0(p0_gev, a, m_n_gev):
    """B_A = A (4 pi p0^3 / (3 m_N))^(A-1), in GeV^(2(A-1))."""
    return a * (4.0 * math.pi * _positive(p0_gev, "p0") ** 3 / (3.0 * _positive(m_n_gev, "m_N"))) ** (_mass_number(a) - 1)


def p0_from_b(b_a, a, m_n_gev):
    _positive(b_a, "B_A")
    return (3.0 * m_n_gev / (4.0 * math.pi) * (b_a / a) ** (1.0 / (_mass_number(a) - 1))) ** (1.0 / 3.0)


def zeta(d_fm, sigma_fm):
    d, s = _positive(d_fm, "--d-fm"), _positive(sigma_fm, "--sigma-fm")
    return (d * d / (d * d + 4.0 * s * s)) ** 1.5


def nucleon_mass(spec):
    if spec in ("proton", "neutron"):
        q = constants.particle(spec, "mass", unit="GeV")
        return q.value, f"{spec} mass, {q.edition}"
    try:
        return _positive(float(spec), "--nucleon-mass"), "user-supplied (GeV)"
    except ValueError as exc:
        raise CoalescenceError("--nucleon-mass is proton, neutron or a mass in GeV") from exc


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("ba", help="B_A from p0, or p0 from B_A")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--p0-gev", type=float)
    g.add_argument("--b-a", type=float)
    p.add_argument("--mass-number", type=int, required=True)
    p.add_argument("--nucleon-mass", required=True, help="proton, neutron or a mass in GeV")
    p.add_argument("--nuclide", help="a nuclide of core/constants for m_A in Duperray et al.'s form (e.g. 2H, 3He)")
    p = sub.add_parser("yield", help="coalesced invariant yield from a nucleon yield")
    p.add_argument("--spectrum", required=True)
    p.add_argument("--mass-number", type=int, required=True)
    p.add_argument("--b-a", type=float, required=True)
    p = sub.add_parser("wigner", help="Wigner-function model factors for the deuteron")
    p.add_argument("--d-fm", type=float, required=True)
    p.add_argument("--sigma-fm", type=float, required=True)
    p.add_argument("--q-gev", type=float, nargs="+", required=True)
    for sp in sub.choices.values():
        add_status_argument(sp)
    a = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs, "defaults_used": [k for k in ("status",) if f"--{k}" not in given]}
    try:
        if a.command == "ba":
            m_n, src = nucleon_mass(a.nucleon_mass)
            mass_a = _mass_number(a.mass_number)
            b = b_from_p0(a.p0_gev, mass_a, m_n) if a.p0_gev is not None else _positive(a.b_a, "--b-a")
            p0 = a.p0_gev if a.p0_gev is not None else p0_from_b(b, mass_a, m_n)
            out = {"B_A": b, "B_A_unit": f"GeV^{2 * (mass_a - 1)}", "p0_gev": p0, "nucleon_mass_gev": m_n,
                   "nucleon_mass_source": src}
            if a.nuclide:
                rec = constants.nuclide(a.nuclide)
                if rec["A"] != mass_a:
                    raise CoalescenceError(f"--nuclide {a.nuclide} has A = {rec['A']}, not {mass_a}")
                m_a = constants.nuclear_mass_gev(rec["Z"], rec["A"])
                b_d = (4.0 * math.pi * p0 ** 3 / 3.0) ** (mass_a - 1) * m_a / m_n ** mass_a
                out.update(B_A_duperray_form=b_d, m_A_gev=m_a, ratio_duperray_to_standard=b_d / b,
                           note="the two forms differ by m_A / (A m_N): the binding energy and the n-p mass difference")
            conv = {"B_A": "A (4 pi p0^3 / (3 m_N))^(A-1) (Kachelriess et al. 2019, Eq. 2)",
                    "duperray": "(4 pi p0^3 / 3)^(A-1) m_A / m_p^A (Duperray et al. 2005, Eq. 5)",
                    "spin_isospin": "not in B_A; the Wigner model carries S = 3/8 (A = 2) or 1/12 (A = 3)"}
        elif a.command == "yield":
            b = _positive(a.b_a, "--b-a")
            mass_a = _mass_number(a.mass_number)
            try:
                spec = json.loads(Path(a.spectrum).read_text(encoding="utf-8"))
                ps, ys = spec["p_gev"], spec["invariant_yield_gev_minus2"]
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise CoalescenceError(f"cannot read {a.spectrum}: {exc}") from exc
            if len(ps) != len(ys) or not ps:
                raise CoalescenceError("p_gev and invariant_yield_gev_minus2 must be non-empty and of equal length")
            rows = [{"p_nucleon_gev": _positive(p_, "p"), "p_A_gev": mass_a * p_,
                     "invariant_yield_A": b * _positive(y, "yield") ** mass_a} for p_, y in zip(ps, ys)]
            out = {"rows": rows}
            conv = {"yield": "E_A d^3N_A/dp_A^3 = B_A (E d^3N/dp^3)^A at p_A = A p (equal n and p yields; Duperray et al. "
                             "2005, Eqs. 1-4)", "units": "invariant yields in GeV^-2 (c = 1)"}
        else:
            z = zeta(a.d_fm, a.sigma_fm)
            hbar_c = constants.hbar_c("GeV fm").value
            rows = []
            for q in a.q_gev:
                if not math.isfinite(q) or q < 0:
                    raise CoalescenceError("--q-gev must be >= 0")
                x = q * a.d_fm / hbar_c
                rows.append({"q_gev": q, "q_d": x, "weight": 3.0 * z * math.exp(-x * x)})
            out = {"zeta": z, "spin_isospin_factor": SPIN_ISOSPIN[2], "rows": rows}
            conv = {"weight": "3 zeta exp(-q^2 d^2), zeta = (d^2 / (d^2 + 4 sigma^2))^(3/2) (Kachelriess et al. 2019, "
                              "Eqs. 15-16); 3 = 8 S, S = 3/8", "units": "d and sigma in fm, q in GeV, hbar c exact"}
    except (CoalescenceError, constants.ConstantsError) as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": "ok", **base, "label": LABEL, "conventions": conv, **out}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
