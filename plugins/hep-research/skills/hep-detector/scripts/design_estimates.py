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
Output JSON: status (ok, rejected), status_label, inputs, label, warnings and the operation's numbers.
Exit codes: 0 ok; 2 invalid input (status rejected). Standard library only.
Usage:
  design_estimates.py budget-sum --estimates E ... --uncertainties U ... [--rule linear|quadrature] [--status LABEL]
  design_estimates.py straight-line-acceptance --z-m Z ... --radius-m R ... --lateral-offset-m O ... [--status LABEL]
  design_estimates.py pid-rejection --separation S --efficiency EPS --convention single|quadrature [--status LABEL]
"""
from __future__ import annotations

import argparse
import json
import math
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
    args = ap.parse_args(argv)
    inputs = _clean(vars(args))
    warnings: list[str] = []
    try:
        if args.command == "budget-sum":
            result = budget_sum(args.estimates, args.uncertainties, args.rule)
        elif args.command == "straight-line-acceptance":
            result, warnings = straight_line_acceptance(args.z_m, args.radius_m, args.lateral_offset_m)
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
