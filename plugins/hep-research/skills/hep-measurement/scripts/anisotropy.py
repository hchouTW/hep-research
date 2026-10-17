#!/usr/bin/env python3
"""Large-scale anisotropy in right ascension: directional exposure, first harmonic, dipole projection, amplitude upper
limit and spurious-modulation checks (M9).

Purpose: the tools behind <plugin root>/skills/hep-measurement/references/cosmic-ray-measurements.md, "Anisotropy",
which states the estimand, the estimators and the checks this script implements.

Subcommands:
  exposure  relative exposure in right ascension from data-taking periods (the period conventions of
            collection_time.py: key, start, duration, live fraction, in seconds of one clock). The instrument sees the
            right ascensions within +- fov_half_width_deg of its zenith right ascension, which advances by 360 deg per
            sidereal day (86164.0905 s) from lst_at_t0_deg at t = 0 (the local sidereal time at the clock's zero; no
            default: the user's ephemeris gives it). Exposure per bin = sum over periods of live fraction x time x the
            fraction of the bin in view, integrated in steps of 1/steps_per_sidereal_day of a sidereal day.
  harmonic  first harmonic of the right ascensions (Linsley 1975): with weights w_i = 1 / relative exposure,
            a = (2/W) sum w cos(alpha), b = (2/W) sum w sin(alpha), r = sqrt(a^2 + b^2), phase atan2(b, a); under
            isotropy P(>= r) = exp(-N r^2 / 4) with N the effective count (W^2 / sum w^2). With declinations, the
            equatorial dipole projection d_perp = r / <cos(delta)>. The amplitude upper limit is the Neyman limit from
            the Rice distribution of r (sigma^2 = 2/N per component; the CDF as a Poisson mixture of chi-square
            CDFs), power-constrained at the expected limit (the limit for the median isotropic amplitude) so it is
            never empty. With --time-column, the first harmonic of event times at the solar (86400 s), sidereal and
            anti-sidereal (2/86400 - 1/86164.0905 per s) frequencies: an anti-sidereal amplitude with Rayleigh
            probability below --spurious-alpha means a seasonal modulation leaks into the sidereal frequency, and the
            run status is failed (exit 1).
Assumptions and validity: a top-hat field of view in right ascension (a planning model of the exposure; a real one
comes from the acceptance per direction and is supplied as the map); large N for the Rayleigh and Rice laws; the
full three-dimensional dipole needs whole-sky exposure (not computed here).
Input: exposure: --config JSON {"key", "start_column", "duration_column", "live_fraction_column", "lst_at_t0_deg",
"fov_half_width_deg", "ra_bins", "steps_per_sidereal_day" (optional)} and period tables (CSV); harmonic: --events CSV
with a right-ascension column in degrees (default ra_deg), optional declination and time columns, optional
--exposure-map (the JSON exposure prints).
Output JSON: status (ok, failed, rejected), status_label, inputs, defaults_used, and the result.
Exit codes: 0 ok; 1 a spurious-modulation check failed; 2 bad input.
Run: python3 <plugin root>/skills/hep-measurement/scripts/anisotropy.py exposure --config exp.json periods.csv
     python3 <plugin root>/skills/hep-measurement/scripts/anisotropy.py harmonic --events events.csv --exposure-map map.json
Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

SIDEREAL_DAY_S = 86164.0905
SOLAR_DAY_S = 86400.0
FREQUENCIES_HZ = {"solar": 1.0 / SOLAR_DAY_S, "sidereal": 1.0 / SIDEREAL_DAY_S,
                  "anti-sidereal": 2.0 / SOLAR_DAY_S - 1.0 / SIDEREAL_DAY_S}
DEFAULT_STEPS = 1440
DEFAULT_CL = 0.95
DEFAULT_SPURIOUS_ALPHA = 0.01
LABEL = "[General method]"


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _num(x, name: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError(f"{name} must be a finite number")
    return float(x)


# ---------------------------------------------------------------- statistics

def first_harmonic(ras, weights=None, decs=None) -> dict:
    """Weighted first harmonic of right ascensions in degrees (Linsley 1975)."""
    if not ras:
        raise ValueError("no events")
    w = [1.0] * len(ras) if weights is None else list(weights)
    big_w = math.fsum(w)
    sw2 = math.fsum(x * x for x in w)
    a = 2.0 / big_w * math.fsum(wi * math.cos(math.radians(r)) for wi, r in zip(w, ras))
    b = 2.0 / big_w * math.fsum(wi * math.sin(math.radians(r)) for wi, r in zip(w, ras))
    r = math.hypot(a, b)
    n_eff = big_w * big_w / sw2
    out = {"a": a, "b": b, "amplitude": r, "phase_deg": math.degrees(math.atan2(b, a)) % 360.0,
           "n_events": len(ras), "n_effective": n_eff, "sigma_per_component": math.sqrt(2.0 / n_eff),
           "rayleigh_probability": math.exp(-n_eff * r * r / 4.0)}
    if decs is not None:
        mean_cos = math.fsum(wi * math.cos(math.radians(d)) for wi, d in zip(w, decs)) / big_w
        out["mean_cos_dec"] = mean_cos
        out["d_perp"] = r / mean_cos
    return out


def rice_cdf(x: float, s: float, n: float) -> float:
    """P(r <= x) for the first-harmonic amplitude with true amplitude s and n (effective) events: r^2 / sigma^2 is a
    non-central chi-square with 2 degrees of freedom and non-centrality s^2 / sigma^2, sigma^2 = 2 / n, written as a
    Poisson(j; lambda/2) mixture of central chi-square CDFs with 2(j + 1) degrees of freedom."""
    if x <= 0.0:
        return 0.0
    sig2 = 2.0 / n
    hy, hl = x * x / sig2 / 2.0, s * s / sig2 / 2.0
    if hy > 500.0 or hl > 500.0:
        # far from the noise (r or s above ~30 sigma) the Rice law is Gaussian about s with width sigma
        from statistics import NormalDist
        return NormalDist(s, math.sqrt(sig2)).cdf(x)
    j_max = int(hl + 12.0 * math.sqrt(hl + 1.0) + 20)
    total, term, partial = 0.0, math.exp(-hy), 0.0
    for j in range(j_max + 1):
        if j > 0:
            term *= hy / j
        partial += term  # exp(-hy) sum_{m <= j} hy^m / m!, so 1 - partial is the chi-square CDF with 2(j + 1) dof
        if hl == 0.0:
            return min(max(1.0 - partial, 0.0), 1.0)
        weight = math.exp(-hl + j * math.log(hl) - math.lgamma(j + 1))
        total += weight * (1.0 - partial)
    return min(max(total, 0.0), 1.0)


def _neyman(r_obs: float, n: float, cl: float) -> float | None:
    """Largest s with P(r <= r_obs | s) >= 1 - cl; None when even s = 0 gives less (an empty limit)."""
    target = 1.0 - cl
    if rice_cdf(r_obs, 0.0, n) < target:
        return None
    lo, hi = 0.0, r_obs + 10.0 * math.sqrt(2.0 / n)
    while rice_cdf(r_obs, hi, n) >= target:
        hi *= 2.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if rice_cdf(r_obs, mid, n) >= target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def amplitude_upper_limit(r_obs, n: float, cl: float = DEFAULT_CL) -> dict:
    """Neyman upper limit on the amplitude from the Rice distribution, power-constrained at the expected limit."""
    median_iso = math.sqrt(4.0 * math.log(2.0) / n)
    expected = _neyman(median_iso, n, cl)
    out = {"confidence_level": cl, "expected_limit": expected, "median_isotropic_amplitude": median_iso,
           "construction": "Neyman upper limit from the Rice distribution of r, power-constrained at the expected limit"}
    if r_obs is not None:
        ney = _neyman(r_obs, n, cl)
        out["neyman_limit"] = ney
        out["upper_limit"] = max(ney if ney is not None else 0.0, expected)
        out["power_constrained"] = ney is None or ney < expected
    return out


# ---------------------------------------------------------------- exposure

def _overlap(lo: float, hi: float, blo: float, bhi: float) -> float:
    """Length of [lo, hi] (may wrap past 360 or below 0) inside [blo, bhi) on the circle."""
    total = 0.0
    for shift in (-360.0, 0.0, 360.0):
        total += max(0.0, min(hi + shift, bhi) - max(lo + shift, blo))
    return total


def exposure_map(cfg: dict, periods: list[dict]) -> dict:
    for k in ("key", "start_column", "duration_column", "live_fraction_column", "lst_at_t0_deg",
              "fov_half_width_deg", "ra_bins"):
        if k not in cfg:
            raise ValueError(f"config.{k} is required (no defaults)")
    lst0 = _num(cfg["lst_at_t0_deg"], "lst_at_t0_deg")
    half = _num(cfg["fov_half_width_deg"], "fov_half_width_deg")
    if not 0.0 < half <= 180.0:
        raise ValueError("fov_half_width_deg must lie in (0, 180]")
    nb = cfg["ra_bins"]
    if isinstance(nb, bool) or not isinstance(nb, int) or not 1 <= nb <= 3600:
        raise ValueError("ra_bins must be an integer in [1, 3600]")
    steps = cfg.get("steps_per_sidereal_day", DEFAULT_STEPS)
    if isinstance(steps, bool) or not isinstance(steps, int) or not 24 <= steps <= 864000:
        raise ValueError("steps_per_sidereal_day must be an integer in [24, 864000]")
    dt = SIDEREAL_DAY_S / steps
    width = 360.0 / nb
    edges = [i * width for i in range(nb + 1)]
    expo = [0.0] * nb
    seen = set()
    live_total = 0.0
    for row in periods:
        key = row[cfg["key"]]
        if key in seen:
            raise ValueError(f"period {key!r} appears twice")
        seen.add(key)
        t0 = _num(float(row[cfg["start_column"]]), "start")
        dur = _num(float(row[cfg["duration_column"]]), "duration")
        live = _num(float(row[cfg["live_fraction_column"]]), "live fraction")
        if dur <= 0 or not 0.0 <= live <= 1.0:
            raise ValueError(f"period {key!r}: duration must be > 0 and the live fraction in [0, 1]")
        live_total += live * dur
        k0 = math.floor(t0 / dt)
        k1 = math.ceil((t0 + dur) / dt)
        for k in range(k0, k1):
            a, b = max(k * dt, t0), min((k + 1) * dt, t0 + dur)
            if b <= a:
                continue
            tm = 0.5 * (a + b)
            zen = (lst0 + 360.0 * tm / SIDEREAL_DAY_S) % 360.0
            for i in range(nb):
                ov = _overlap(zen - half, zen + half, edges[i], edges[i + 1])
                if ov:
                    expo[i] += live * (b - a) * ov / width
    mean = math.fsum(expo) / nb
    if mean <= 0:
        raise ValueError("no exposure: every period has zero live time")
    return {"ra_edges_deg": edges, "exposure_s": expo, "relative_exposure": [e / mean for e in expo],
            "live_time_s": live_total, "fov_half_width_deg": half, "lst_at_t0_deg": lst0,
            "steps_per_sidereal_day": steps,
            "definition": "per right-ascension bin: sum of live fraction x time x fraction of the bin within the "
                          "field of view; the mean over bins is live time x (2 x half width / 360) for full coverage"}


# ---------------------------------------------------------------- I/O

def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def column(rows, name, path, lo=None, hi=None) -> list[float]:
    if name not in rows[0]:
        raise ValueError(f"{path}: no column {name!r}")
    out = []
    for r in rows:
        v = float(r[name])
        if not math.isfinite(v) or (lo is not None and v < lo) or (hi is not None and v >= hi):
            raise ValueError(f"{path}: {name} value {v} outside [{lo}, {hi})")
        out.append(v)
    return out


def harmonic_run(args) -> tuple[str, dict]:
    rows = read_csv(args.events)
    ras = column(rows, args.ra_column, args.events, 0.0, 360.0)
    decs = column(rows, args.dec_column, args.events, -90.0, 90.0000001) if args.dec_column else None
    warnings, weights = [], None
    if args.exposure_map:
        emap = json.loads(args.exposure_map.read_text(encoding="utf-8"))
        edges, rel = emap["ra_edges_deg"], emap["relative_exposure"]
        weights = []
        for a in ras:
            i = min(int((a - edges[0]) / (edges[1] - edges[0])), len(rel) - 1)
            if rel[i] <= 0:
                raise ValueError(f"an event at right ascension {a} falls where the exposure is zero")
            weights.append(1.0 / rel[i])
    else:
        warnings.append("no --exposure-map: uniform exposure assumed in right ascension; an exposure modulation would "
                        "appear as an anisotropy")
    h = first_harmonic(ras, weights, decs)
    out = {"harmonic": h, "upper_limit": amplitude_upper_limit(h["amplitude"], h["n_effective"], args.cl),
           "label": LABEL, "warnings": warnings}
    status = "ok"
    if args.time_column:
        times = column(rows, args.time_column, args.events)
        freqs, failed = {}, []
        for name, f in FREQUENCIES_HZ.items():
            phases = [(360.0 * f * t) % 360.0 for t in times]
            hf = first_harmonic(phases)
            freqs[name] = {"frequency_hz": f, "amplitude": hf["amplitude"], "phase_deg": hf["phase_deg"],
                           "rayleigh_probability": hf["rayleigh_probability"]}
        p_anti = freqs["anti-sidereal"]["rayleigh_probability"]
        if p_anti < args.spurious_alpha:
            failed.append(f"anti-sidereal amplitude significant (Rayleigh p = {p_anti:.3g} < {args.spurious_alpha}): a "
                          "seasonal modulation of the solar-frequency response leaks into the sidereal frequency")
            status = "failed"
        out["checks"] = {"frequencies": freqs, "spurious_alpha": args.spurious_alpha, "failed": failed,
                         "note": "the solar-frequency amplitude is a check of the method (the Compton-Getting dipole); "
                                 "for an instrument in orbit also check the orbital and attitude periods"}
    else:
        out["checks"] = {"not_run": "no --time-column: the solar, sidereal and anti-sidereal checks need event times"}
        warnings.append("spurious-modulation checks not run (no --time-column)")
    return status, out


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("exposure", help="relative exposure in right ascension from periods")
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("periods", nargs="+", type=Path)
    p = sub.add_parser("harmonic", help="first harmonic, upper limit and spurious-modulation checks")
    p.add_argument("--events", required=True, type=Path)
    p.add_argument("--ra-column", default="ra_deg", dest="ra_column")
    p.add_argument("--dec-column", dest="dec_column")
    p.add_argument("--time-column", dest="time_column")
    p.add_argument("--exposure-map", type=Path, dest="exposure_map")
    p.add_argument("--cl", type=float, default=DEFAULT_CL)
    p.add_argument("--spurious-alpha", type=float, default=DEFAULT_SPURIOUS_ALPHA, dest="spurious_alpha")
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("ra_column", "cl", "spurious_alpha", "status") if k in vars(args)
                and f"--{k.replace('_', '-')}" not in given]
    inputs = {k: (str(v) if isinstance(v, Path) else [str(x) for x in v] if isinstance(v, list) else v)
              for k, v in vars(args).items() if k != "status"}
    try:
        if args.command == "exposure":
            cfg = json.loads(args.config.read_text(encoding="utf-8"))
            if "steps_per_sidereal_day" not in cfg:
                defaults.append("steps_per_sidereal_day")
            rows = [r for p in args.periods for r in read_csv(p)]
            status, out = "ok", exposure_map(cfg, rows)
        else:
            if not 0 < args.cl < 1 or not 0 < args.spurious_alpha < 1:
                raise ValueError("--cl and --spurious-alpha must lie in (0, 1)")
            status, out = harmonic_run(args)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        status, out = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **out}, indent=1))
    if status == "rejected":
        print(f"{ap.prog}: error (rejected): {out['error']}", file=sys.stderr)
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
