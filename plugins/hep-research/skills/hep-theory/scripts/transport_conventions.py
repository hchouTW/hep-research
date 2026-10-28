#!/usr/bin/env python3
"""Convert cosmic-ray transport parameters between the conventions of the public propagation codes (cr-propagation A1).

Purpose: before two codes' transport parameters are compared, put them in one convention and say whether the
conversion is exact. See <plugin root>/skills/hep-theory/references/cosmic-ray-phenomenology.md, "Propagation codes
and transport parameters" (the convention table this module implements; its tests parse that table row by row).
Conventions (the reference page's table):
- galprop:   D = D0 beta (rho/rho0)^delta, rho0 = 4 GV, D0 in 1e28 cm^2/s (eta fixed at 1);
- usine-k0:  K = beta^eta K0 (R/R0)^delta with smooth breaks, R0 = 1 GV, K0 in kpc^2/Myr;
- usine-k10: the same with the normalization K10 = K0 10^delta at 10 GV, in kpc^2/Myr;
- dragon2:   D = D0 (p/p0)^delta, D0 at 1 GV in cm^2/s (eta = 0; a momentum reference p0 is refused, below);
- canonical: the plugin's names (D0_cm2_s, R0_gv, delta, eta, breaks), any R0, D0 in cm^2/s.
Every result is marked exact, approximate (with a relative-error bound) or not-convertible (r3 P1):
- exact: a pure power law in rigidity with the same eta on both sides; only the reference rigidity
  (D0' = D0 (R0'/R0)^delta) and the unit change.
- approximate: a power law with smooth breaks of one smoothness convention. The break terms are carried over
  unchanged and D0' = D0 (R0'/R0)^delta (how K10 = K0 10^delta is defined). Whether a code normalizes its break
  factor f(R) at its reference rigidity is a convention this module cannot see, so the bound is the largest of
  |f(R0) - 1|, |f(R0') - 1| and |f(R0')/f(R0) - 1|, the spread between the two readings. Never exact (A1-4).
- not-convertible: a different eta (beta^eta is a different function of energy and species), different or unknown
  smoothness conventions, a break kind this module does not evaluate, or a momentum reference p0 (rigidity per
  momentum depends on the species). Compare predictions instead of parameters.
The low break evaluated here (convention label "usine"): f(R) = (1 + (R_break/R)^((delta - delta_below)/s))^s, slope
delta_below well below R_break and delta well above. The form is this module's reading of the label; it was not
re-read from Weinrich et al. 2020a, Eq. 1 in work package A1.
Reacceleration zone: USINE reaccelerates only in the thin disc of half-thickness h, GALPROP and DRAGON2 in the whole
halo; equal energy gain needs V_A,disc^2 h = V_A,halo^2 L, so V_A,disc = V_A,halo sqrt(L/h). The status is only
approximate (r3 P1 "about sqrt(L/h)"); no bound is derived (relative_error_bound null, with the reason).
Energy variables: E_k,total = A E_k/n (exact); a flux per total kinetic energy times A is the flux per E_k/n (r3 P11).
Legacy names map to the canonical table (r3, Canonical parameter names): D0 (with D0_unit) -> D0_cm2_s, L (with
L_unit) -> L_kpc, and the DRAGON2 specification keys D0_1e28 -> D0_cm2_s, DiffRefRig_GV -> R0_gv, etaT -> eta,
Rmax_kpc -> radius_kpc.
Units: 1 pc = 648000/pi au (IAU 2012, au = 149 597 870 700 m), 1 Myr = 1e6 Julian years of 365.25 d, so
1 kpc^2/Myr = 3.0172e29 cm^2/s.
Usage: transport_conventions.py units
       transport_conventions.py diffusion --input SPEC.json   (SPEC: {"from": C, "to": C, "diffusion": {...},
                                                               optional "target_s_convention"})
       transport_conventions.py reacceleration --alfven-speed-km-s V --from-zone {thin-disc,whole-halo}
                                                --to-zone {thin-disc,whole-halo} --l-kpc L --disc-halfwidth-pc H
       transport_conventions.py energy --mass-number A --from-variable {ekn,ek-total} --values X [X ...]
                                       [--flux-values F [F ...]]
       transport_conventions.py names --input PARAMETERS.json
       (every subcommand takes --status LABEL, default unvalidated)
Output JSON: status, status_label, inputs, label [General method], and per subcommand: units (kpc_cm, myr_s,
kpc2_per_myr_cm2_s); conversion (conversion_status exact|approximate|not-convertible, relative_error_bound, reason,
result, canonical); rows; names (canonical, mapped, unmapped).
Exit codes: 0 ok (exact or approximate); 1 not-convertible (status refused); 2 bad or missing input (status rejected).
Standard library and core only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
AU_M = 149597870700.0  # IAU 2012 Resolution B2, exact
PARSEC_CM = 648000.0 / math.pi * AU_M * 100.0  # IAU 2015 Resolution B2 definition of the parsec
KPC_CM = 1e3 * PARSEC_CM
JULIAN_YEAR_S = 365.25 * 86400.0
MYR_S = 1e6 * JULIAN_YEAR_S
KPC2_PER_MYR_CM2_S = KPC_CM ** 2 / MYR_S

EXACT, APPROXIMATE, NOT_CONVERTIBLE = "exact", "approximate", "not-convertible"

# Unit of D0 per convention: the factor that turns the convention's number into cm^2/s.
D0_UNIT_CM2_S = {"cm^2/s": 1.0, "cm^2 s^-1": 1.0, "1e28 cm^2/s": 1e28, "10^28 cm^2/s": 1e28,
                 "kpc^2/Myr": KPC2_PER_MYR_CM2_S}

# The convention table of cosmic-ray-phenomenology.md. eta None: free (given with the parameters).
CODE_CONVENTIONS = {
    "galprop": {"form": "D0 beta (rho/rho0)^delta", "eta": 1.0, "reference_gv": 4.0, "d0_unit": "1e28 cm^2/s",
                "normalization_name": "D0", "source": "GALPROP v57 (Tables 1-2)"},
    "usine-k0": {"form": "beta^eta K0 (R/R0)^delta with smooth breaks", "eta": None, "reference_gv": 1.0,
                 "d0_unit": "kpc^2/Myr", "normalization_name": "K0", "source": "Weinrich et al. 2020a, Eq. 1"},
    "usine-k10": {"form": "beta^eta K10 (R/10 GV)^delta with smooth breaks, K10 = K0 10^delta", "eta": None,
                  "reference_gv": 10.0, "d0_unit": "kpc^2/Myr", "normalization_name": "K10",
                  "source": "Weinrich et al. 2020a, Eq. 1"},
    "dragon2": {"form": "D0 (p/p0)^delta", "eta": 0.0, "reference_gv": 1.0, "d0_unit": "cm^2/s",
                "normalization_name": "D0", "source": "Evoli et al. 2017, Sec. 5"},
    "canonical": {"form": "D0_cm2_s beta^eta (R/R0_gv)^delta with smooth breaks", "eta": None, "reference_gv": None,
                  "d0_unit": "cm^2/s", "normalization_name": "D0_cm2_s", "source": "r3 canonical parameter names"},
}
BREAK_CONVENTIONS = ("usine",)
ZONES = ("thin-disc", "whole-halo")

# Legacy key -> (canonical name, factor to the canonical unit, unit key read from the same mapping or None).
LEGACY_NAMES = {
    "D0": ("D0_cm2_s", None, "D0_unit"),
    "L": ("L_kpc", None, "L_unit"),
    "D0_1e28": ("D0_cm2_s", 1e28, None),
    "DiffRefRig_GV": ("R0_gv", 1.0, None),
    "etaT": ("eta", 1.0, None),
    "Rmax_kpc": ("radius_kpc", 1.0, None),
}
LENGTH_UNIT_KPC = {"kpc": 1.0, "pc": 1e-3}
CANONICAL_NAMES = ("D0_cm2_s", "R0_gv", "delta", "eta", "L_kpc", "radius_kpc", "disc_halfwidth_pc", "R_break_gv",
                   "delta_below", "s", "V_A_kms", "V_c_kms", "dVc_dz_kms_per_kpc", "He_to_H_number")


class ConventionError(ValueError):
    """An input this module cannot read."""


def unit_table() -> dict:
    """The derived length, time and diffusion units."""
    return {"au_m": AU_M, "parsec_cm": PARSEC_CM, "kpc_cm": KPC_CM, "julian_year_s": JULIAN_YEAR_S, "myr_s": MYR_S,
            "kpc2_per_myr_cm2_s": KPC2_PER_MYR_CM2_S}


def _number(value, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConventionError(f"{what} must be a finite number, got {value!r}")
    return float(value)


def _log_softplus(t: float) -> float:
    """ln(1 + e^t) without overflow."""
    return t + math.log1p(math.exp(-t)) if t > 0 else math.log1p(math.exp(t))


def break_factor(rigidity_gv: float, delta: float, breaks: list[dict]) -> float:
    """The product of the low-break factors f(R) of the "usine" smoothness convention."""
    log_f = 0.0
    for item in breaks:
        s = item["s"]
        t = (delta - item["delta_below"]) / s * math.log(item["R_break_gv"] / rigidity_gv)
        log_f += s * _log_softplus(t)
    return math.exp(log_f)


def _read_breaks(raw) -> list[dict]:
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        raise ConventionError("breaks must be a list")
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ConventionError(f"breaks[{i}] must be an object")
        brk = {"kind": item.get("kind"), "s_convention": item.get("s_convention")}
        for key in ("R_break_gv", "delta_below", "s"):
            if key in item:
                brk[key] = _number(item[key], f"breaks[{i}].{key}")
        if brk.get("R_break_gv", 1.0) <= 0 or brk.get("s", 1.0) <= 0:
            raise ConventionError(f"breaks[{i}]: R_break_gv and s must be positive")
        out.append(brk)
    return out


def to_canonical(params: dict, convention: str) -> dict:
    """Read a diffusion block written in `convention` into canonical names and units (cm^2/s, GV)."""
    if convention not in CODE_CONVENTIONS:
        raise ConventionError(f"unknown convention {convention!r}; known: {', '.join(CODE_CONVENTIONS)}")
    if not isinstance(params, dict):
        raise ConventionError("diffusion must be an object")
    conv = CODE_CONVENTIONS[convention]
    raw = dict(params)
    name = conv["normalization_name"]
    # The code's own normalization (GALPROP D0 in 1e28 cm^2/s, USINE K0 or K10 in kpc^2/Myr) is read in that code's
    # unit before the legacy-name mapping, which reads a bare D0 in cm^2/s (or its D0_unit).
    d0 = _number(raw.pop(name), name) * D0_UNIT_CM2_S[conv["d0_unit"]] if name in raw and name != "D0_cm2_s" else None
    params = map_legacy_names(raw)["canonical"]
    if params.get("reference") == "momentum":
        return {"refused": "the reference is a momentum p0: the rigidity of a given momentum depends on Z/A, so the "
                           "normalization is species dependent; give the reference as a rigidity"}
    if d0 is not None and "D0_cm2_s" in params:
        raise ConventionError(f"both {name} and D0_cm2_s are given")
    if d0 is None:
        if "D0_cm2_s" not in params:
            raise ConventionError(f"missing the normalization ({name} or D0_cm2_s)")
        d0 = _number(params["D0_cm2_s"], "D0_cm2_s")
    if d0 <= 0:
        raise ConventionError("the diffusion normalization must be positive")
    delta = _number(params.get("delta"), "delta")
    r0 = params.get("R0_gv", conv["reference_gv"])
    r0 = _number(r0, "R0_gv")
    if conv["reference_gv"] is not None and not math.isclose(r0, conv["reference_gv"], rel_tol=1e-12):
        raise ConventionError(f"{convention} has its reference at {conv['reference_gv']} GV, got R0_gv = {r0}")
    if r0 <= 0:
        raise ConventionError("R0_gv must be positive")
    eta = params.get("eta", conv["eta"])
    eta = _number(eta, "eta")
    if conv["eta"] is not None and eta != conv["eta"]:
        return {"refused": f"{convention} fixes eta = {conv['eta']}, got eta = {eta}"}
    return {"D0_cm2_s": d0, "R0_gv": r0, "delta": delta, "eta": eta, "breaks": _read_breaks(params.get("breaks"))}


def convert_diffusion(params: dict, source: str, target: str, target_s_convention: str | None = None) -> dict:
    """Convert a diffusion block from one convention to another; the result carries conversion_status."""
    canon = to_canonical(params, source)
    if "refused" in canon:
        return {"conversion_status": NOT_CONVERTIBLE, "relative_error_bound": None, "reason": canon["refused"]}
    if target not in CODE_CONVENTIONS:
        raise ConventionError(f"unknown convention {target!r}; known: {', '.join(CODE_CONVENTIONS)}")
    conv = CODE_CONVENTIONS[target]
    if conv["eta"] is not None and canon["eta"] != conv["eta"]:
        return {"conversion_status": NOT_CONVERTIBLE, "relative_error_bound": None, "canonical": canon,
                "reason": f"{target} fixes eta = {conv['eta']} and the input has eta = {canon['eta']}: beta^eta is a "
                          "different function of energy for each species; compare predictions, not parameters"}
    r0_new = conv["reference_gv"] if conv["reference_gv"] is not None else canon["R0_gv"]
    d0_new = canon["D0_cm2_s"] * (r0_new / canon["R0_gv"]) ** canon["delta"]
    breaks = canon["breaks"]
    status, bound, reason = EXACT, 0.0, "pure power law in rigidity: reference rigidity and unit change only"
    if breaks:
        conventions_in = {b["s_convention"] for b in breaks}
        conventions_out = {target_s_convention} if target_s_convention else conventions_in
        unknown = [b for b in breaks if b["kind"] != "low" or not {"R_break_gv", "delta_below", "s"} <= set(b)]
        if unknown:
            return {"conversion_status": NOT_CONVERTIBLE, "relative_error_bound": None, "canonical": canon,
                    "reason": "a break that is not a low break with R_break_gv, delta_below and s is not evaluated "
                              "here; compare predictions"}
        if conventions_in != conventions_out or not conventions_in <= set(BREAK_CONVENTIONS):
            return {"conversion_status": NOT_CONVERTIBLE, "relative_error_bound": None, "canonical": canon,
                    "reason": f"smoothness conventions differ or are unknown (input {sorted(map(str, conventions_in))}, "
                              f"target {sorted(map(str, conventions_out))}; known: {list(BREAK_CONVENTIONS)})"}
        f_old = break_factor(canon["R0_gv"], canon["delta"], breaks)
        f_new = break_factor(r0_new, canon["delta"], breaks)
        bound = max(abs(f_old - 1.0), abs(f_new - 1.0), abs(f_new / f_old - 1.0))
        status = APPROXIMATE
        reason = ("smooth breaks carried over unchanged; whether a code normalizes the break factor at its reference "
                  "rigidity is not visible in the parameters; the bound is the spread between the two readings")
    value = d0_new / D0_UNIT_CM2_S[conv["d0_unit"]]
    result = {conv["normalization_name"]: value, "d0_unit": conv["d0_unit"], "R0_gv": r0_new,
              "delta": canon["delta"], "eta": canon["eta"], "breaks": breaks}
    return {"conversion_status": status, "relative_error_bound": bound, "reason": reason, "result": result,
            "canonical": dict(canon, D0_cm2_s=d0_new, R0_gv=r0_new)}


def convert_alfven_speed(va_kms: float, from_zone: str, to_zone: str, l_kpc: float, disc_halfwidth_pc: float) -> dict:
    """V_A between thin-disc and whole-halo reacceleration: only approximate (equal V_A^2 x zone thickness)."""
    for value, what in ((va_kms, "--alfven-speed-km-s"), (l_kpc, "--l-kpc"), (disc_halfwidth_pc, "--disc-halfwidth-pc")):
        _number(value, what)
    if va_kms < 0 or l_kpc <= 0 or disc_halfwidth_pc <= 0:
        raise ConventionError("V_A must be >= 0 and L, h positive")
    if from_zone not in ZONES or to_zone not in ZONES:
        raise ConventionError(f"zones are {ZONES}")
    h_kpc = disc_halfwidth_pc * 1e-3
    if h_kpc >= l_kpc:
        raise ConventionError("the disc half-thickness must be below the halo half-height")
    scale = math.sqrt(l_kpc / h_kpc)
    factor = 1.0 if from_zone == to_zone else (scale if to_zone == "thin-disc" else 1.0 / scale)
    status = EXACT if from_zone == to_zone else APPROXIMATE
    return {"conversion_status": status, "relative_error_bound": 0.0 if status == EXACT else None,
            "reason": "same zone" if status == EXACT else
            "equal energy gain V_A,disc^2 h = V_A,halo^2 L (r3 P1, 'about sqrt(L/h)'); the gain also depends on where "
            "the particles spend their time, so no bound is derived: compare predictions",
            "result": {"V_A_kms": va_kms * factor, "zone": to_zone, "factor": factor},
            "canonical": {"V_A_kms": va_kms, "zone": from_zone, "L_kpc": l_kpc, "disc_halfwidth_pc": disc_halfwidth_pc}}


def convert_energy(mass_number: int, from_variable: str, values: list[float],
                   flux_values: list[float] | None = None) -> list[dict]:
    """E_k/n <-> E_k,total = A E_k/n and the matching flux densities (dN/dE_k/n = A dN/dE_k,total); exact."""
    if isinstance(mass_number, bool) or not isinstance(mass_number, int) or mass_number < 1:
        raise ConventionError("--mass-number must be a positive integer")
    if from_variable not in ("ekn", "ek-total"):
        raise ConventionError("--from-variable is ekn or ek-total")
    if flux_values is not None and len(flux_values) != len(values):
        raise ConventionError("--flux-values needs one value per energy")
    rows = []
    for i, x in enumerate(values):
        x = _number(x, "--values")
        ekn = x if from_variable == "ekn" else x / mass_number
        row = {"ekn_gev": ekn, "ek_total_gev": ekn * mass_number, "conversion_status": EXACT}
        if flux_values is not None:
            f = _number(flux_values[i], "--flux-values")
            per_ekn = f if from_variable == "ekn" else f * mass_number
            row.update(flux_per_ekn=per_ekn, flux_per_ek_total=per_ekn / mass_number)
        rows.append(row)
    return rows


def map_legacy_names(params: dict) -> dict:
    """Map legacy keys (D0, L, the DRAGON2 specification keys) to canonical names; unknown keys pass through."""
    if not isinstance(params, dict):
        raise ConventionError("parameters must be an object")
    unit_keys = {spec[2] for spec in LEGACY_NAMES.values() if spec[2]}
    canonical, mapped, unmapped = {}, {}, []
    for key, value in params.items():
        if key in unit_keys:
            continue
        if key not in LEGACY_NAMES:
            canonical[key] = value
            if key not in CANONICAL_NAMES:
                unmapped.append(key)
            continue
        name, factor, unit_key = LEGACY_NAMES[key]
        if factor is None:
            unit = params.get(unit_key, "cm^2/s" if name == "D0_cm2_s" else "kpc")
            table = D0_UNIT_CM2_S if name == "D0_cm2_s" else LENGTH_UNIT_KPC
            if unit not in table:
                raise ConventionError(f"{unit_key} {unit!r} unknown; known: {', '.join(table)}")
            factor = table[unit]
        if name in canonical:
            raise ConventionError(f"{key} and another key both give {name}")
        canonical[name] = _number(value, key) * factor
        mapped[key] = name
    return {"canonical": canonical, "mapped": mapped, "unmapped": unmapped}


def _load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        raise ConventionError(f"input file not found: {path}") from None
    except (OSError, json.JSONDecodeError) as exc:
        raise ConventionError(f"cannot read {path}: {exc}") from None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("units", help="the derived kpc, Myr and kpc^2/Myr in cgs")
    add_status_argument(p)
    p = sub.add_parser("diffusion", help="convert a diffusion block between conventions")
    p.add_argument("--input", required=True, help='JSON: {"from": C, "to": C, "diffusion": {...}}')
    add_status_argument(p)
    p = sub.add_parser("reacceleration", help="V_A between thin-disc and whole-halo reacceleration (approximate)")
    p.add_argument("--alfven-speed-km-s", type=float, required=True)
    p.add_argument("--from-zone", choices=ZONES, required=True)
    p.add_argument("--to-zone", choices=ZONES, required=True)
    p.add_argument("--l-kpc", type=float, required=True)
    p.add_argument("--disc-halfwidth-pc", type=float, required=True)
    add_status_argument(p)
    p = sub.add_parser("energy", help="kinetic energy per nucleon <-> total, with flux densities")
    p.add_argument("--mass-number", type=int, required=True)
    p.add_argument("--from-variable", choices=("ekn", "ek-total"), required=True)
    p.add_argument("--values", type=float, nargs="+", required=True)
    p.add_argument("--flux-values", type=float, nargs="+")
    add_status_argument(p)
    p = sub.add_parser("names", help="map legacy parameter names to the canonical table")
    p.add_argument("--input", required=True, help="JSON object of parameters")
    add_status_argument(p)
    a = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs, "label": LABEL}
    try:
        if a.command == "units":
            out = {"units": unit_table()}
        elif a.command == "diffusion":
            spec = _load_json(a.input)
            if not isinstance(spec, dict) or not {"from", "to", "diffusion"} <= set(spec):
                raise ConventionError('the input needs "from", "to" and "diffusion"')
            out = {"conversion": convert_diffusion(spec["diffusion"], spec["from"], spec["to"],
                                                   spec.get("target_s_convention"))}
        elif a.command == "reacceleration":
            out = {"conversion": convert_alfven_speed(a.alfven_speed_km_s, a.from_zone, a.to_zone, a.l_kpc,
                                                      a.disc_halfwidth_pc)}
        elif a.command == "energy":
            out = {"rows": convert_energy(a.mass_number, a.from_variable, a.values, a.flux_values)}
        else:
            out = {"names": map_legacy_names(_load_json(a.input))}
    except ConventionError as exc:
        print(json.dumps({"status": "rejected", **base, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    status = "refused" if out.get("conversion", {}).get("conversion_status") == NOT_CONVERTIBLE else "ok"
    print(json.dumps({"status": status, **base, **out}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
