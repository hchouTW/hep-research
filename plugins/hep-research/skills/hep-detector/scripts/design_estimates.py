#!/usr/bin/env python3
"""Design-level F1 estimates for detector system design: budget sums, straight-line acceptance, PID rejection.

Purpose: the three analytic operations the detector system design loop needs besides the existing resolution and PID
tools (see <plugin root>/skills/hep-detector/references/system-design-workflow.md); each has a tool contract with a
design block (contracts/tool_contracts/design_estimates.json) so contracts/design.py can recompute its inputs.

Operations:
- budget-sum: the sum of per-subsystem budget items (mass, power, channel count, data rate) and its uncertainty: the
  linear sum of the item uncertainties (default; conservative for correlated items), or the quadrature sum when the
  items are declared independent (--rule quadrature). An arithmetic sum, not a physics prediction.
- straight-line-acceptance: the geometric acceptance (m^2 sr) of coaxial circular apertures for an isotropic flux in
  the straight-line limit, A = 2 pi integral sin(theta) cos(theta) S(theta) dtheta, with S the area of the overlap of
  the apertures projected along the direction (theta) onto the first plane; for two apertures it reproduces Sullivan's
  closed form (Nucl. Instrum. Meth. 95 (1971) 5). The straight-line limit ignores bending, nuclear interactions and
  detection efficiency, so it is an upper bound only for apertures on one straight axis: lateral offsets are echoed
  and must be zero for that (with an offset, bending can raise one charge sign's acceptance).
- pid-rejection: the background rejection 1/P(misidentified) of a Gaussian discriminant at a signal working-point
  efficiency eps: cut at t = Phi^-1(eps) on the signal side of unit-width responses whose means differ by the
  single-convention separation S (S = sqrt(2) times the quadrature-convention value for equal widths), misidentification
  Phi(t - S). Real responses have heavier tails, and multiplying rejections of several subsystems as if independent
  overstates them, so the value is an upper bound of the rejection.
- infield-acceptance (F2): a seeded Monte Carlo of the same apertures in a uniform field B along y: tracks start
  uniformly on the first aperture with a cos(theta)-weighted isotropic direction and follow the exact helix (radius
  R / (0.299792458 B) for the momentum component perpendicular to B, bending sense from the charge sign) to each
  aperture plane, which they must reach and cross inside the (laterally offset) circle; A = pi x area(first aperture) x
  the fraction accepted. Its uncertainty adds the binomial statistical error and the effect of the declared aperture
  radius tolerance (dA/A = 2 dr/r of the smallest aperture) in quadrature. Geometry only: no material, nuclear
  interactions or detection efficiency.
- response-assembly (F3): a parametrized rigidity response at the denominator rigidity from a core resolution (an
  upstream evaluation), an alignment curvature term a (1/GV) and a declared tail: effective core
  s = sqrt(core^2 + (a R)^2), a tail of fraction f and width w s, and the RMS sqrt((1 - f) s^2 + f (w s)^2), all in
  sigma(1/R) x R (relative). The tail is an assumption the candidate declares, never fitted here.
- material-sum (F1, CHN-14): the material along the track, x/X0 = sum of the given contributions (measuring layers,
  passive material, the services each subsystem adds), with a declared relative uncertainty; an arithmetic sum.
- precision-from-result (F3): the expected relative precision written back from a hep-statistics statistical-result
  on an Asimov dataset (status asimov; extension.results.expected_relative_uncertainty); the result is read, never
  computed here.
Output JSON: status (ok, rejected), status_label, inputs, label, warnings and the operation's numbers.
Exit codes: 0 ok; 2 invalid input (status rejected). Standard library only.
Usage:
  design_estimates.py budget-sum --estimates E ... --uncertainties U ... [--rule linear|quadrature] [--status LABEL]
  design_estimates.py straight-line-acceptance --z-m Z ... --radius-m R ... --lateral-offset-m O ... [--status LABEL]
  design_estimates.py pid-rejection --separation S --efficiency EPS --convention single|quadrature [--status LABEL]
  design_estimates.py infield-acceptance --z-m Z ... --radius-m R ... --lateral-offset-m O ... --field-tesla B
      --rigidity R --charge-sign positive|negative --radius-tolerance-m T [--samples N] [--seed S] [--status LABEL]
  design_estimates.py response-assembly --core C --rigidity R --alignment-per-gv A --tail-fraction F
      --tail-width-factor W [--status LABEL]
  design_estimates.py precision-from-result --result FILE [--status LABEL]
  design_estimates.py material-sum --x-over-x0 X ... [--relative-uncertainty U] [--status LABEL]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from statistics import NormalDist

PLUGIN = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(PLUGIN))
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
_N = NormalDist()
N_THETA = 1200
N_X = 400


class InputError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _clean(obj):
    """JSON-safe echo of the inputs: a non-finite number becomes its string."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return str(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, list):
        return [_clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    return obj


def _finite(values, where: str, positive: bool = False) -> list[float]:
    out = []
    for v in values:
        if not math.isfinite(v) or v < 0 or (positive and v == 0):
            raise InputError(f"{where}: {v!r} must be finite and {'> 0' if positive else '>= 0'}")
        out.append(float(v))
    return out


def budget_sum(estimates: list[float], uncertainties: list[float], rule: str) -> dict:
    if len(estimates) != len(uncertainties) or not estimates:
        raise InputError("--estimates and --uncertainties need one value per item, at least one item")
    est, unc = _finite(estimates, "--estimates"), _finite(uncertainties, "--uncertainties")
    total = math.fsum(est)
    sigma = math.fsum(unc) if rule == "linear" else math.sqrt(math.fsum(u * u for u in unc))
    return {"n_items": len(est), "total": total, "uncertainty": sigma, "rule": rule,
            "uncertainty_meaning": "one standard deviation; linear sum of the item uncertainties" if rule == "linear"
            else "one standard deviation; quadrature sum (items declared independent)"}


def _simpson(f, a: float, b: float, n: int) -> float:
    if b <= a:
        return 0.0
    n += n % 2
    h = (b - a) / n
    s = f(a) + f(b) + sum((4 if k % 2 else 2) * f(a + k * h) for k in range(1, n))
    return s * h / 3


def overlap_area(radii: list[float], shifts: list[float]) -> float:
    """Area of the intersection of disks of the given radii centred at (shift_i, 0)."""
    lo = max(s - r for s, r in zip(shifts, radii))
    hi = min(s + r for s, r in zip(shifts, radii))
    if hi <= lo:
        return 0.0

    def width(x: float) -> float:
        return 2 * min(math.sqrt(max(0.0, r * r - (x - s) ** 2)) for s, r in zip(shifts, radii))
    return _simpson(width, lo, hi, N_X)


def straight_line_acceptance(z: list[float], radii: list[float], offsets: list[float]) -> tuple[dict, list[str]]:
    if not (len(z) == len(radii) == len(offsets)) or len(z) < 2:
        raise InputError("--z-m, --radius-m and --lateral-offset-m need one value per aperture, at least two")
    radii = _finite(radii, "--radius-m", positive=True)
    if any(not math.isfinite(v) for v in z + offsets):
        raise InputError("positions and offsets must be finite")
    order = sorted(range(len(z)), key=lambda i: z[i])
    zs, rs = [z[i] for i in order], [radii[i] for i in order]
    if len(set(zs)) != len(zs):
        raise InputError("--z-m: two apertures at the same position")
    warnings = []
    if any(o != 0 for o in offsets):
        warnings.append("lateral offsets are not zero: the coaxial straight-line value is not an upper bound "
                        "(the apertures are not on one straight axis); offsets are not used in the computation")
    z0 = zs[0]
    theta_max = math.atan((rs[0] + rs[-1]) / (zs[-1] - z0))

    def integrand(th: float) -> float:
        t = math.tan(th)
        return math.sin(th) * math.cos(th) * overlap_area(rs, [(zi - z0) * t for zi in zs])
    acc = 2 * math.pi * _simpson(integrand, 0.0, theta_max, N_THETA)
    out = {"acceptance_m2sr": acc, "n_apertures": len(zs), "theta_max_rad": theta_max,
           "coaxial": all(o == 0 for o in offsets), "lateral_offsets_m": offsets}
    if len(zs) == 2:
        r1, r2, d = rs[0], rs[-1], zs[-1] - zs[0]
        q = r1 * r1 + r2 * r2 + d * d
        out["sullivan_two_aperture_m2sr"] = 0.5 * math.pi ** 2 * (q - math.sqrt(q * q - 4 * r1 * r1 * r2 * r2))
    return out, warnings


def _crossing(p0, d, s, rho, z):
    """(x, y, path) where a track from p0 = (x, y, z0) with unit direction d, charge sign s and bending radius rho (for
    the full momentum; B along y) first reaches the plane z ahead of it, or None."""
    x0, y0, z0 = p0
    ux, uy, uz = d
    t = math.hypot(ux, uz)
    if t == 0:
        return None
    ax, az = ux / t, uz / t
    r = rho * t  # radius of the projection on the bending (x, z) plane
    if r > 1e9:  # straight line
        if az <= 0:
            return None
        lxz = (z - z0) / az
        return x0 + ax * lxz, y0 + uy / t * lxz, lxz
    cx, cz = x0 - s * r * az, z0 + s * r * ax          # the centre lies to the left (s > 0) of the motion
    th0 = math.atan2(z0 - cz, x0 - cx)
    v = (z - cz) / r
    if abs(v) > 1:
        return None
    best = None
    for th in (math.asin(v), math.pi - math.asin(v)):
        delta = (s * (th - th0)) % (2 * math.pi)
        if delta > 1e-15 and (best is None or delta < best[0]):
            best = (delta, th)
    if best is None or best[0] > math.pi:
        return None  # the track turns back before the plane
    lxz = best[0] * r
    return cx + r * math.cos(best[1]), y0 + uy / t * lxz, lxz


def infield_acceptance(z: list[float], radii: list[float], offsets: list[float], field: float, rigidity: float,
                       sign: str, tolerance: float, samples: int, seed: int) -> dict:
    if not (len(z) == len(radii) == len(offsets)) or len(z) < 2:
        raise InputError("--z-m, --radius-m and --lateral-offset-m need one value per aperture, at least two")
    radii = _finite(radii, "--radius-m", positive=True)
    field, rigidity = _finite([field], "--field-tesla", positive=True)[0], _finite([rigidity], "--rigidity", positive=True)[0]
    tolerance = _finite([tolerance], "--radius-tolerance-m")[0]
    if samples < 1000:
        raise InputError("--samples must be at least 1000")
    if any(not math.isfinite(v) for v in z + offsets):
        raise InputError("positions and offsets must be finite")
    order = sorted(range(len(z)), key=lambda i: z[i])
    zs, rs, os_ = [z[i] for i in order], [radii[i] for i in order], [offsets[i] for i in order]
    if len(set(zs)) != len(zs):
        raise InputError("--z-m: two apertures at the same position")
    s = 1 if sign == "positive" else -1
    rho = rigidity / (0.299792458 * field)
    rng = random.Random(seed)
    passed = 0
    for _ in range(samples):
        rr, ph = rs[0] * math.sqrt(rng.random()), 2 * math.pi * rng.random()
        p0 = (os_[0] + rr * math.cos(ph), rr * math.sin(ph), zs[0])
        ct = math.sqrt(rng.random())
        st, phi = math.sqrt(max(0.0, 1 - ct * ct)), 2 * math.pi * rng.random()
        d = (st * math.cos(phi), st * math.sin(phi), ct)
        ok = True
        for zi, ri, oi in zip(zs[1:], rs[1:], os_[1:]):
            c = _crossing(p0, d, s, rho, zi)
            if c is None or (c[0] - oi) ** 2 + c[1] ** 2 > ri * ri:
                ok = False
                break
        passed += ok
    frac = passed / samples
    total = math.pi * math.pi * rs[0] ** 2
    acc = total * frac
    stat = total * math.sqrt(frac * (1 - frac) / samples)
    syst = acc * 2 * tolerance / min(rs)
    return {"acceptance_m2sr": acc, "acceptance_uncertainty_m2sr": math.hypot(stat, syst), "statistical_m2sr": stat,
            "tolerance_term_m2sr": syst, "accepted": passed, "samples": samples, "seed": seed,
            "bending_radius_m": rho, "uncertainty_meaning": "one standard deviation: binomial statistics and the "
            "aperture-radius tolerance (2 dr / r of the smallest aperture) in quadrature"}


def response_assembly(core: float, rigidity: float, align: float, frac: float, width: float) -> dict:
    core, rigidity, align = (_finite([core], "--core", positive=True)[0], _finite([rigidity], "--rigidity", positive=True)[0],
                             _finite([align], "--alignment-per-gv")[0])
    if not 0 <= frac < 1:
        raise InputError("--tail-fraction must be in [0, 1)")
    width = _finite([width], "--tail-width-factor", positive=True)[0]
    if width < 1:
        raise InputError("--tail-width-factor must be at least 1 (a tail is wider than the core)")
    eff = math.hypot(core, align * rigidity)
    rms = math.sqrt((1 - frac) * eff * eff + frac * (width * eff) ** 2)
    return {"rigidity_gv": rigidity, "core_relative": core, "alignment_relative": align * rigidity,
            "effective_core_relative": eff, "tail_fraction": frac, "tail_width_relative": width * eff,
            "rms_relative": rms,
            "function": "sigma(1/R) R ~ (1 - f) N(0, s) + f N(0, w s): Gaussian core and Gaussian tail (declared)"}


def precision_from_result(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise InputError(f"--result {path}: not readable JSON ({exc})") from exc
    if not isinstance(doc, dict) or doc.get("artifact_type") != "statistical-result":
        raise InputError("--result is not a statistical-result artifact")
    if "asimov" not in (doc.get("status") or []):
        raise InputError("--result is not on an Asimov dataset (status asimov; CHN-03)")
    v = ((doc.get("extension") or {}).get("results") or {}).get("expected_relative_uncertainty")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
        raise InputError("--result has no positive extension.results.expected_relative_uncertainty")
    return {"expected_relative_uncertainty": float(v), "result_artifact_id": doc.get("artifact_id"),
            "note": "the median expected uncertainty of an Asimov fit (Wald approximation), not a guarantee for one "
                    "measurement (LIM-06)"}


def material_sum(parts: list[float], rel: float) -> dict:
    parts = _finite(parts, "--x-over-x0")
    rel = _finite([rel], "--relative-uncertainty")[0]
    total = math.fsum(parts)
    return {"x_over_x0": total, "uncertainty": rel * total, "n_contributions": len(parts),
            "uncertainty_meaning": "one standard deviation, the declared relative uncertainty of the material description"}


def pid_rejection(separation: float, efficiency: float, convention: str) -> dict:
    if not math.isfinite(separation) or separation < 0:
        raise InputError("--separation must be finite and >= 0")
    if not 0 < efficiency < 1:
        raise InputError("--efficiency must be in (0, 1)")
    s_single = separation * (math.sqrt(2) if convention == "quadrature" else 1.0)
    t = _N.inv_cdf(efficiency)
    misid = _N.cdf(t - s_single)
    return {"separation_single_sigma": s_single, "working_point_efficiency": efficiency, "cut_sigma": t,
            "misidentification": misid, "rejection": (1 / misid) if misid > 0 else None,
            "note": "Gaussian responses of unit width: an upper bound of the rejection (tails are heavier)"}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("budget-sum", help="sum of budget items with their uncertainty")
    p.add_argument("--estimates", type=float, nargs="+", required=True)
    p.add_argument("--uncertainties", type=float, nargs="+", required=True)
    p.add_argument("--rule", choices=("linear", "quadrature"), default="linear")
    add_status_argument(p)
    p = sub.add_parser("straight-line-acceptance", help="coaxial-aperture acceptance in the straight-line limit")
    p.add_argument("--z-m", dest="z_m", type=float, nargs="+", required=True)
    p.add_argument("--radius-m", dest="radius_m", type=float, nargs="+", required=True)
    p.add_argument("--lateral-offset-m", dest="lateral_offset_m", type=float, nargs="+", required=True)
    add_status_argument(p)
    p = sub.add_parser("pid-rejection", help="rejection from separation power and working-point efficiency")
    p.add_argument("--separation", type=float, required=True)
    p.add_argument("--efficiency", type=float, required=True)
    p.add_argument("--convention", choices=("single", "quadrature"), required=True)
    add_status_argument(p)
    p = sub.add_parser("infield-acceptance", help="acceptance of offset apertures in a uniform field (seeded toy)")
    p.add_argument("--z-m", dest="z_m", type=float, nargs="+", required=True)
    p.add_argument("--radius-m", dest="radius_m", type=float, nargs="+", required=True)
    p.add_argument("--lateral-offset-m", dest="lateral_offset_m", type=float, nargs="+", required=True)
    p.add_argument("--field-tesla", dest="field_tesla", type=float, required=True)
    p.add_argument("--rigidity", type=float, required=True)
    p.add_argument("--charge-sign", dest="charge_sign", choices=("positive", "negative"), required=True)
    p.add_argument("--radius-tolerance-m", dest="radius_tolerance_m", type=float, required=True)
    p.add_argument("--samples", type=int, default=50000)
    p.add_argument("--seed", type=int, default=1)
    add_status_argument(p)
    p = sub.add_parser("response-assembly", help="parametrized response: core, alignment and declared tail")
    p.add_argument("--core", type=float, required=True)
    p.add_argument("--rigidity", type=float, required=True)
    p.add_argument("--alignment-per-gv", dest="alignment_per_gv", type=float, required=True)
    p.add_argument("--tail-fraction", dest="tail_fraction", type=float, required=True)
    p.add_argument("--tail-width-factor", dest="tail_width_factor", type=float, required=True)
    add_status_argument(p)
    p = sub.add_parser("material-sum", help="material along the track from all contributions (CHN-14)")
    p.add_argument("--x-over-x0", dest="x_over_x0", type=float, nargs="+", required=True)
    p.add_argument("--relative-uncertainty", dest="relative_uncertainty", type=float, default=0.1)
    add_status_argument(p)
    p = sub.add_parser("precision-from-result", help="expected precision from an Asimov statistical-result")
    p.add_argument("--result", type=Path, required=True)
    add_status_argument(p)
    args = ap.parse_args(argv)
    inputs = _clean(vars(args))
    warnings: list[str] = []
    try:
        if args.command == "budget-sum":
            result = budget_sum(args.estimates, args.uncertainties, args.rule)
        elif args.command == "straight-line-acceptance":
            result, warnings = straight_line_acceptance(args.z_m, args.radius_m, args.lateral_offset_m)
        elif args.command == "infield-acceptance":
            result = infield_acceptance(args.z_m, args.radius_m, args.lateral_offset_m, args.field_tesla, args.rigidity,
                                        args.charge_sign, args.radius_tolerance_m, args.samples, args.seed)
        elif args.command == "response-assembly":
            result = response_assembly(args.core, args.rigidity, args.alignment_per_gv, args.tail_fraction,
                                       args.tail_width_factor)
        elif args.command == "material-sum":
            result = material_sum(args.x_over_x0, args.relative_uncertainty)
        elif args.command == "precision-from-result":
            result = precision_from_result(args.result)
        else:
            result = pid_rejection(args.separation, args.efficiency, args.convention)
        if any(isinstance(v, float) and not math.isfinite(v) for v in result.values()):
            raise InputError("the result is not representable (non-finite)")
    except (OverflowError, ZeroDivisionError) as exc:
        result = None
        err = f"the result is not representable: {exc}"
    except InputError as exc:
        result = None
        err = str(exc)
    if result is None:
        print(json.dumps({"status": "rejected", "status_label": args.status, "inputs": inputs, "error": err},
                         indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": "ok", "status_label": args.status, "inputs": inputs, "label": LABEL,
                      "warnings": warnings, **result}, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())
