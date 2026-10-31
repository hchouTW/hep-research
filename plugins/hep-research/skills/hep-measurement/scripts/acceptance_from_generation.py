#!/usr/bin/env python3
"""Acceptance A(x) from generation records: the generation factor times the fraction of generated events selected.

Purpose: an instrument's acceptance (geometric factor times selection efficiency, m^2 sr) per bin of a variable, from a
simulation whose generation is declared: the generation surface, its angular law, the spectrum and the number of
events generated. See <plugin root>/skills/hep-measurement/references/correction-chain.md.

Method: events are generated with the cosine law (an isotropic flux crossing the surface) on
  plane:  one side of a flat surface of area S, optionally within theta_max: G_gen = pi sin^2(theta_max) S;
  sphere: inward through a sphere of radius R: G_gen = pi (4 pi R^2).
In bin j of the variable, N_gen,j = N_generated P_j with P_j the declared generation spectrum's probability in the
bin (power law with index != 1, or log-uniform, between x_min and x_max), and A_j = G_gen k_j / N_gen,j for k_j selected
events; the interval is the Clopper-Pearson interval on k_j / N_gen,j (core/stats/tail_estimation.py) times G_gen.
With a target spectrum t(x) the selected events are weighted by t/g (g the normalized generation density) and
A_j = G_gen sum_i w_i / (N_generated int_j t dx); the interval then uses Kish's effective count (approximate, labelled).
sullivan_two_disc(R1, R2, L) gives the closed form for two coaxial discs, (pi^2/2) [R1^2 + R2^2 + L^2 -
sqrt((R1^2 + R2^2 + L^2)^2 - 4 R1^2 R2^2)], used as a test oracle (the attribution to Sullivan, Nucl. Instrum. Methods
95 (1971) 5, is to-verify: the paper was not opened; the formula is checked against a Monte Carlo).

Assumptions and validity: straight-line generation and a selection independent of how the generated count is
binned; the generated count is the full count thrown, including events that miss the instrument. A target spectrum
taken from this measurement's own result makes the acceptance depend on the answer (circularity): a warning.

Input: --config JSON {"generation": {"surface": "plane"|"sphere", "area_m2" (plane) | "radius_m" (sphere),
"angular": "cosine", "theta_max_deg" (optional, plane), "n_generated": N, "spectrum": {"kind": "power-law",
"index": G, "x_min", "x_max"} | {"kind": "log-uniform", "x_min", "x_max"}}, "x": {"variable", "unit", "edges": [...]},
"target_spectrum": optional spectrum (+ "from_measurement": true|false, "source": text), "interval_cl": optional};
--events CSV with a header and a column (default "x") of the true value of each selected event.
Output JSON: status (ok, rejected, incomplete), status_label, inputs, defaults_used, generation_factor_m2_sr, bins
(edges, n_selected, n_generated, acceptance, acceptance_lower, acceptance_upper), warnings.
Exit codes: 0 ok; 2 bad input; 3 incomplete (the generated count is missing).
Run: python3 <plugin root>/skills/hep-measurement/scripts/acceptance_from_generation.py --config gen.json --events selected.csv
Standard library only.
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
import csv
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.stats.tail_estimation import clopper_pearson  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
DEFAULT_CL = 0.6827


class Incomplete(ValueError):
    """A required count is missing: exit 3."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def sullivan_two_disc(r1: float, r2: float, sep: float) -> float:
    """Geometric factor (m^2 sr) of two coaxial discs of radii r1, r2 a distance sep apart, isotropic flux."""
    s = r1 * r1 + r2 * r2 + sep * sep
    p = r1 * r1 * r2 * r2
    # (pi^2/2)(s - sqrt(s^2 - 4p)) written without the cancellation that loses precision when sep >> r
    return 2.0 * math.pi ** 2 * p / (s + math.sqrt(max(s * s - 4.0 * p, 0.0)))


def _pos(x, name: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x <= 0:
        raise ValueError(f"{name} must be a finite number > 0")
    return float(x)


def generation_factor(gen: dict) -> float:
    if gen.get("angular") != "cosine":
        raise ValueError("generation.angular must be 'cosine' (an isotropic flux crossing the surface)")
    surface = gen.get("surface")
    if surface == "plane":
        area = _pos(gen.get("area_m2"), "generation.area_m2")
        tmax = gen.get("theta_max_deg", 90.0)
        tmax = _pos(tmax, "generation.theta_max_deg")
        if tmax > 90.0:
            raise ValueError("generation.theta_max_deg must be <= 90")
        return math.pi * math.sin(math.radians(tmax)) ** 2 * area
    if surface == "sphere":
        r = _pos(gen.get("radius_m"), "generation.radius_m")
        return math.pi * 4.0 * math.pi * r * r
    raise ValueError("generation.surface must be 'plane' or 'sphere'")


class Spectrum:
    """A density on [x_min, x_max]: power law x^-index (index != 1) or log-uniform; integrals in closed form."""

    def __init__(self, spec: dict, name: str):
        self.kind = spec.get("kind")
        self.lo, self.hi = _pos(spec.get("x_min"), f"{name}.x_min"), _pos(spec.get("x_max"), f"{name}.x_max")
        if self.hi <= self.lo:
            raise ValueError(f"{name}: x_max must exceed x_min")
        if self.kind == "power-law":
            idx = spec.get("index")
            if isinstance(idx, bool) or not isinstance(idx, (int, float)) or not math.isfinite(idx) or idx == 1:
                raise ValueError(f"{name}.index must be a finite number other than 1 (use log-uniform for 1)")
            self.index = float(idx)
        elif self.kind != "log-uniform":
            raise ValueError(f"{name}.kind must be 'power-law' or 'log-uniform'")

    def antiderivative(self, x: float) -> float:
        if self.kind == "log-uniform":
            return math.log(x)
        a = 1.0 - self.index
        return x ** a / a

    def integral(self, a: float, b: float) -> float:
        a, b = max(a, self.lo), min(b, self.hi)
        return 0.0 if b <= a else self.antiderivative(b) - self.antiderivative(a)

    def density(self, x: float) -> float:
        return 1.0 / x if self.kind == "log-uniform" else x ** -self.index

    def total(self) -> float:
        return self.integral(self.lo, self.hi)


def compute(cfg: dict, xs: list[float]) -> dict:
    gen = cfg.get("generation")
    if not isinstance(gen, dict):
        raise ValueError("config.generation is required")
    g_gen = generation_factor(gen)
    if gen.get("n_generated") is None:
        raise Incomplete("generation.n_generated is missing: the acceptance needs the number of events thrown")
    n_gen = gen["n_generated"]
    if isinstance(n_gen, bool) or not isinstance(n_gen, int) or n_gen <= 0:
        raise ValueError("generation.n_generated must be a positive integer")
    gspec = Spectrum(gen.get("spectrum") or {}, "generation.spectrum")
    xcfg = cfg.get("x") or {}
    edges = xcfg.get("edges")
    if not isinstance(edges, list) or len(edges) < 2 or any(_pos(e, "x.edges") <= 0 for e in edges) or \
            any(b <= a for a, b in zip(edges, edges[1:])):
        raise ValueError("x.edges must be at least two increasing positive numbers")
    cl = cfg.get("interval_cl", DEFAULT_CL)
    if isinstance(cl, bool) or not isinstance(cl, (int, float)) or not 0 < cl < 1:
        raise ValueError("interval_cl must lie strictly between 0 and 1")
    warnings = []
    target = cfg.get("target_spectrum")
    tspec = Spectrum(target, "target_spectrum") if target else None
    if target and (target.get("from_measurement") is True or target == cfg.get("measured_spectrum")):
        warnings.append("circularity: the target spectrum comes from this measurement's own result, so the "
                        "acceptance depends on the answer; iterate to convergence and report the dependence")
    if edges[0] < gspec.lo or edges[-1] > gspec.hi:
        warnings.append("the binning extends beyond the generated range; bins there have no generated events")
    gtot = gspec.total()
    bins = []
    for lo, hi in zip(edges, edges[1:]):
        sel = [x for x in xs if lo <= x < hi]
        k = len(sel)
        row = {"edges": [lo, hi], "n_selected": k}
        if tspec is None:
            expected = n_gen * gspec.integral(lo, hi) / gtot
            row["n_generated"] = expected
            if expected <= 0:
                row.update(acceptance=None, note="no generated events in this bin")
            else:
                n_bin = int(round(expected))
                frac = k / expected
                lo_p, hi_p = clopper_pearson(min(k, n_bin), max(n_bin, k), cl) if n_bin > 0 else (0.0, 1.0)
                row.update(acceptance=g_gen * frac, acceptance_lower=g_gen * lo_p, acceptance_upper=g_gen * hi_p)
        else:
            w = [tspec.density(x) / (gspec.density(x) / gtot) for x in sel]
            denom = n_gen * tspec.integral(lo, hi)
            if denom <= 0:
                row.update(acceptance=None, note="the target spectrum is zero in this bin")
            else:
                sw, sw2 = math.fsum(w), math.fsum(v * v for v in w)
                acc = g_gen * sw / denom
                n_eff = (sw * sw / sw2) if sw2 > 0 else 0.0
                scale = acc / (n_eff if n_eff > 0 else 1.0)
                k_eff = int(round(n_eff))
                lo_e, hi_e = _poisson_like(k_eff, cl)
                row.update(n_generated_weighted=denom, n_effective=n_eff, acceptance=acc,
                           acceptance_lower=scale * lo_e, acceptance_upper=scale * hi_e,
                           interval_note="Kish effective count with a Garwood interval: approximate")
        bins.append(row)
    return {"generation_factor_m2_sr": g_gen, "variable": xcfg.get("variable"), "unit": xcfg.get("unit"),
            "acceptance_unit": "m^2 sr", "interval_cl": cl, "bins": bins, "warnings": warnings, "label": LABEL,
            "target_spectrum": target}


def _poisson_like(k: int, cl: float) -> tuple[float, float]:
    from core.stats.poisson_diagnostics import central_interval
    iv = central_interval(k, cl)
    return iv["lower"], iv["upper"]


def read_events(path: Path, column: str) -> list[float]:
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))
    if not rows or column not in rows[0]:
        raise ValueError(f"{path}: needs a header with the column {column!r}")
    out = []
    for r in rows:
        v = float(r[column])
        if not math.isfinite(v):
            raise ValueError(f"{path}: non-finite value in {column}")
        out.append(v)
    return out


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--events", required=True, type=Path)
    ap.add_argument("--x-column", default="x", dest="x_column")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("x_column", "status") if f"--{k.replace('_', '-')}" not in given]
    inputs = {"config": str(args.config), "events": str(args.events), "x_column": args.x_column}
    try:
        cfg = json.loads(args.config.read_text(encoding="utf-8"))
        if "interval_cl" not in cfg:
            defaults.append("interval_cl")
        out = compute(cfg, read_events(args.events, args.x_column))
        status = "ok"
    except Incomplete as exc:
        status, out = "incomplete", {"error": str(exc)}
    except (OSError, ValueError, KeyError) as exc:
        status, out = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **out}, indent=1))
    if status != "ok":
        print(f"{ap.prog}: error ({status}): {out['error']}", file=sys.stderr)
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
