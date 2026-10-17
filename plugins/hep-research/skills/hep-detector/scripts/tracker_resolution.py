#!/usr/bin/env python3
"""Tracker momentum and impact-parameter resolution for a stated layout, and the layouts that meet a requirement (D14).

Purpose: the design-level numbers of a tracking system from its layer positions, point resolution, field and
material, with the approximation each one uses stated. See "Detector design principles" in
<plugin root>/skills/hep-detector/references/detector-design-principles.md and the formulas in
<plugin root>/skills/hep-detector/references/tracking-and-vertexing.md.

Method:
- momentum, intrinsic term: the exact weighted least-squares fit of a parabola y = a + b x + c x^2 to the given
  layer positions (curvature k = 2c, var(k) = 4 (X^T W X)^-1_cc, W = 1/sigma_i^2); sigma(p_T)/p_T = sigma_k p_T /
  (0.299792458 z B) with p_T in GeV/c, B in T, lengths in m. The Gluckstern approximation sigma_k = (sigma_x/L^2)
  sqrt(720/(N+4)) (N equally spaced points over L) is reported for comparison, with the variance ratio exact/
  Gluckstern; for N = 3 the exact coefficient is 8 sqrt(3/2);
- momentum, scattering term: the PDG fit form 0.016 GeV/c / (0.299792458 beta B L) sqrt(x/X0), independent of z
  (PDG RPP, "Passage of particles through matter" / "Particle detectors at accelerators", as quoted in
  tracking-and-vertexing.md). multiple_scattering.py and toy_spectrometer.py use the Highland constant 0.0136 GeV
  without its log factor; the two terms differ by the factor 0.016 / 0.0136;
- MDR: the p_T where the intrinsic term reaches 100% (0.299792458 z B / sigma_k), and where the total does;
- impact: sigma_d0 = a (+) b / (p sin^(3/2) theta) in the transverse plane;
- scan: N equally spaced layers over each lever arm L, every combination of --n-layers and --lever-arm-m, the total
  sigma(p_T)/p_T at --pt with x/X0 = N x (per layer), against --max-relative-resolution.
Assumptions and validity: uniform field over the lever arm, track at lambda = 0 (p = p_T), Gaussian point errors,
material spread uniformly along the track; a design estimate, not a track fit. No experiment defaults: every
physical input is required (beta from --beta or --mass-gev; the lever arm defaults to the span of the positions,
and the default is reported).

Usage:
  tracker_resolution.py momentum --positions-m Z ... --point-resolution-um S [S ...] --field-tesla B
      --x-over-x0 X --charge Z (--beta B | --mass-gev M) --pt P [P ...] [--lever-arm-m L]
  tracker_resolution.py impact --a-um A --b-um-gev B --p-gev P [P ...] --theta-deg T
  tracker_resolution.py scan --n-layers N ... --lever-arm-m L ... --point-resolution-um S --field-tesla B
      --x-over-x0-per-layer X --charge Z (--beta B | --mass-gev M) --pt P --max-relative-resolution R
  every subcommand takes --status LABEL (default unvalidated), echoed as status_label.
Output JSON: status (ok, rejected), status_label, inputs, defaults_used, label "[General method]" and the results.
Exit codes: 0 ok; 2 invalid input or a missing required input (status rejected). Standard library only.
"""
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
K_FIELD = constants.constant("speed_of_light").value * 1e-9  # GeV/c per (T m): p_T = K z B R
PDG_MS = 0.016  # GeV/c, the PDG coefficient of the scattering term of a curvature fit
HIGHLAND = 0.0136  # GeV, the Highland constant without its log factor (multiple_scattering.py)


class InputError(ValueError):
    """Invalid or missing input (status rejected, exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(exit_code("rejected"), f"{self.prog}: error: {message}\n")


def _pos(x, name):
    if not math.isfinite(x) or x <= 0:
        raise InputError(f"{name} must be a finite number > 0")
    return x


def _solve3(m, v):
    """Solve a 3x3 linear system (Cramer's rule; the normal matrix is small and well defined here)."""
    def det(a):
        return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    d = det(m)
    if abs(d) < 1e-300:
        raise InputError("the layer positions do not constrain a curvature (need three distinct positions)")
    out = []
    for i in range(3):
        mi = [row[:] for row in m]
        for r in range(3):
            mi[r][i] = v[r]
        out.append(det(mi) / d)
    return out


def curvature_sigma(positions, sigmas_m):
    """sigma of k = 2c from the weighted least-squares parabola fit."""
    if len(positions) < 3 or len(set(positions)) < 3:
        raise InputError("give at least three distinct layer positions")
    s = [[0.0] * 3 for _ in range(3)]
    for x, sg in zip(positions, sigmas_m):
        w, f = 1.0 / (sg * sg), (1.0, x, x * x)
        for i in range(3):
            for j in range(3):
                s[i][j] += w * f[i] * f[j]
    col = _solve3(s, [0.0, 0.0, 1.0])  # third column of the inverse
    return 2.0 * math.sqrt(col[2])


def _beta(args, p):
    if args.beta is not None:
        if not 0 < args.beta <= 1:
            raise InputError("--beta must be in (0, 1]")
        return args.beta
    m = _pos(args.mass_gev, "--mass-gev")
    return p / math.hypot(p, m)


def _need_beta(args):
    if (args.beta is None) == (args.mass_gev is None):
        raise InputError("give exactly one of --beta or --mass-gev")


def momentum(args, defaults):
    _need_beta(args)
    z = sorted(args.positions_m)
    if len(args.point_resolution_um) not in (1, len(z)):
        raise InputError("--point-resolution-um takes one value or one per position")
    sig = [_pos(s, "--point-resolution-um") * 1e-6 for s in args.point_resolution_um] * (len(z) if len(args.point_resolution_um) == 1 else 1)
    b, x0, q = _pos(args.field_tesla, "--field-tesla"), args.x_over_x0, abs(args.charge)
    if x0 < 0 or q == 0:
        raise InputError("--x-over-x0 must be >= 0 and --charge nonzero")
    span = z[-1] - z[0]
    if args.lever_arm_m is None:
        defaults.append("lever_arm_m: the span of the positions")
    lever = _pos(args.lever_arm_m if args.lever_arm_m is not None else span, "lever arm")
    sk = curvature_sigma(z, sig)
    n = len(z)
    sig_eff = (sum(1 / s ** 2 for s in sig) / n) ** -0.5
    g_coef = math.sqrt(720.0 / (n + 4))
    sk_g = sig_eff * g_coef / lever ** 2
    intrinsic = {"sigma_curvature_per_m": sk, "exact_coefficient": sk * lever ** 2 / sig_eff,
                 "gluckstern_coefficient": g_coef, "gluckstern_sigma_curvature_per_m": sk_g,
                 "exact_over_gluckstern_variance": (sk / sk_g) ** 2,
                 "slope_per_gev": sk / (K_FIELD * q * b), "gluckstern_slope_per_gev": sk_g / (K_FIELD * q * b),
                 "note": "Gluckstern assumes N equally spaced points over the lever arm; the exact fit uses the given positions"}
    points = []
    for p in args.pt:
        p = _pos(p, "--pt")
        beta = _beta(args, p)
        intr = sk * p / (K_FIELD * q * b)
        ms = PDG_MS * math.sqrt(x0) / (K_FIELD * beta * b * lever)
        points.append({"pt_gev": p, "beta": beta, "intrinsic_relative": intr, "scattering_relative": ms,
                       "scattering_relative_highland": ms * HIGHLAND / PDG_MS, "total_relative": math.hypot(intr, ms)})
    mdr = K_FIELD * q * b / sk
    ms1 = PDG_MS * math.sqrt(x0) / (K_FIELD * b * lever)  # at beta = 1
    return {"n_layers": n, "lever_arm_m": lever, "intrinsic": intrinsic, "points": points,
            "mdr_intrinsic_gev": mdr, "mdr_total_gev_beta1": (math.sqrt(1 - ms1 ** 2) * mdr if ms1 < 1 else None),
            "scattering_convention": "PDG 0.016 GeV/c; the Highland form (0.0136 GeV) is scattering_relative_highland"}


def impact(args, defaults):
    a, b = args.a_um, args.b_um_gev
    if a is None or b is None or args.theta_deg is None:
        raise InputError("--a-um, --b-um-gev and --theta-deg are required")
    th = math.radians(args.theta_deg)
    if not 0 < th < math.pi:
        raise InputError("--theta-deg must be in (0, 180)")
    rows = [{"p_gev": p, "sigma_d0_um": math.hypot(a, b / (_pos(p, "--p-gev") * math.sin(th) ** 1.5))} for p in args.p_gev]
    return {"form": "sigma_d0 = a (+) b / (p sin^(3/2) theta)", "points": rows}


def scan(args, defaults):
    _need_beta(args)
    b, req, p = _pos(args.field_tesla, "--field-tesla"), _pos(args.max_relative_resolution, "--max-relative-resolution"), _pos(args.pt, "--pt")
    sig = _pos(args.point_resolution_um, "--point-resolution-um") * 1e-6
    beta, q = _beta(args, p), abs(args.charge)
    if q == 0 or args.x_over_x0_per_layer < 0:
        raise InputError("--charge nonzero and --x-over-x0-per-layer >= 0")
    grid, best = [], {}
    for n in args.n_layers:
        if n < 3:
            raise InputError("--n-layers values must be >= 3")
        for lever in args.lever_arm_m:
            lever = _pos(lever, "--lever-arm-m")
            z = [lever * i / (n - 1) for i in range(n)]
            sk = curvature_sigma(z, [sig] * n)
            intr = sk * p / (K_FIELD * q * b)
            ms = PDG_MS * math.sqrt(n * args.x_over_x0_per_layer) / (K_FIELD * beta * b * lever)
            tot = math.hypot(intr, ms)
            grid.append({"n_layers": n, "lever_arm_m": lever, "intrinsic_relative": intr, "scattering_relative": ms,
                         "total_relative": tot, "meets": tot <= req})
            if tot <= req and (str(n) not in best or lever < best[str(n)]):
                best[str(n)] = lever
    return {"requirement": f"sigma(p_T)/p_T <= {req} at p_T = {p} GeV/c", "grid": grid,
            "minimal_lever_arm_m": {str(n): best.get(str(n)) for n in args.n_layers}}


def main(argv=None):
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    m = sub.add_parser("momentum", help="momentum resolution of a given layout")
    m.add_argument("--positions-m", type=float, nargs="+", required=True)
    m.add_argument("--point-resolution-um", type=float, nargs="+", required=True)
    m.add_argument("--field-tesla", type=float, required=True)
    m.add_argument("--x-over-x0", type=float, required=True, help="total material along the track, x/X0")
    m.add_argument("--charge", type=float, required=True)
    m.add_argument("--beta", type=float)
    m.add_argument("--mass-gev", type=float)
    m.add_argument("--pt", type=float, nargs="+", required=True)
    m.add_argument("--lever-arm-m", type=float, help="default: the span of the positions (reported)")
    i = sub.add_parser("impact", help="impact-parameter resolution a (+) b/(p sin^1.5 theta)")
    i.add_argument("--a-um", type=float, required=True)
    i.add_argument("--b-um-gev", type=float, required=True)
    i.add_argument("--p-gev", type=float, nargs="+", required=True)
    i.add_argument("--theta-deg", type=float, required=True)
    s = sub.add_parser("scan", help="layouts that meet a momentum-resolution requirement")
    s.add_argument("--n-layers", type=int, nargs="+", required=True)
    s.add_argument("--lever-arm-m", type=float, nargs="+", required=True)
    s.add_argument("--point-resolution-um", type=float, required=True)
    s.add_argument("--field-tesla", type=float, required=True)
    s.add_argument("--x-over-x0-per-layer", type=float, required=True)
    s.add_argument("--charge", type=float, required=True)
    s.add_argument("--beta", type=float)
    s.add_argument("--mass-gev", type=float)
    s.add_argument("--pt", type=float, required=True)
    s.add_argument("--max-relative-resolution", type=float, required=True)
    for sp in (m, i, s):
        add_status_argument(sp)
    args = ap.parse_args(argv)
    given = {a.split("=")[0] for a in (sys.argv[1:] if argv is None else argv) if a.startswith("--")}
    defaults = ["status"] if "--status" not in given else []
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    try:
        res = {"momentum": momentum, "impact": impact, "scan": scan}[args.command](args, defaults)
        out = {"status": "ok", "status_label": args.status, "label": LABEL, "inputs": inputs,
               "defaults_used": defaults, **res}
    except InputError as exc:
        out = {"status": "rejected", "status_label": args.status, "inputs": inputs, "error": str(exc)}
    try:
        text = json.dumps(out, indent=2, allow_nan=False)
    except ValueError:
        out = {"status": "rejected", "status_label": args.status, "error": "a result is not finite"}
        text = json.dumps(out, indent=2)
    print(text)
    return exit_code(out["status"])


if __name__ == "__main__":
    raise SystemExit(main())
