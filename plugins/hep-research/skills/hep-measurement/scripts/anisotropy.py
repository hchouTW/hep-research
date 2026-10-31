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
            a = (2/W) sum w cos(alpha), b = (2/W) sum w sin(alpha), r = sqrt(a^2 + b^2), phase atan2(b, a). Under
            isotropy (v = (a, b), null covariance V) the Rayleigh probability is P(chi^2 >= v^T V^-1 v) =
            exp(-chi^2 / 2), which is exp(-N r^2 / 4) for V = (2/N) I (no map, or a uniform one). With
            --exposure-map, V is exact for the binned map (rho_j constant per bin) and N events, to leading order in
            1/N: Var(a) = (4/N) (int cos^2 / rho) (int rho) / (2 pi)^2, Var(b) likewise with sin^2, Cov(a, b) with
            sin cos (harmonic_covariance; a non-uniform exposure makes the variances unequal, and W^2 / sum w^2,
            reported as n_effective, does not give them). With declinations, the equatorial dipole projection
            d_perp = r / <cos(delta)>. The amplitude upper limit is the Neyman limit, power-constrained at the
            expected limit (the limit for the median isotropic amplitude) so it is never empty: from the Rice
            distribution of r (sigma^2 = 2/N per component; the CDF as a Poisson mixture of chi-square CDFs) when V
            is isotropic, otherwise from P(r <= x | s, phi, V) (the bivariate normal over the disk: a closed-form
            radial integral, a periodic trapezoid in the polar angle), a true amplitude s being excluded only if it
            is excluded for every dipole phase phi on a 72-point grid aligned with V's eigen-axes. --cl must lie in
            [0.5, 1): below 0.5 the expected limit is empty and the power constraint undefined (rejected). With
            --time-column, the first harmonic of event times at the solar (86400 s), sidereal and anti-sidereal
            (2/86400 - 1/86164.0905 per s) frequencies (unweighted, V = (2/N) I): an anti-sidereal amplitude with
            Rayleigh probability below --spurious-alpha means a seasonal modulation leaks into the sidereal frequency,
            and the run status is failed (exit 1).
Assumptions and validity: a top-hat field of view in right ascension (a planning model of the exposure; a real one
comes from the acceptance per direction and is supplied as the map, with exposure in every right-ascension bin); large
N for the Gaussian law of (a, b) behind the Rayleigh probability and the limits; the full three-dimensional dipole
needs whole-sky exposure (not computed here).
Input: exposure: --config JSON {"key", "start_column", "duration_column", "live_fraction_column", "lst_at_t0_deg",
"fov_half_width_deg", "ra_bins", "steps_per_sidereal_day" (optional)} and period tables (CSV); harmonic: --events CSV
with a right-ascension column in degrees (default ra_deg), optional declination and time columns, optional
--exposure-map (the JSON exposure prints).
Output JSON: status (ok, failed, rejected), status_label, inputs, defaults_used, and the result. harmonic reports
covariance_ab (the null V), rayleigh_probability (exp(-chi^2 / 2)), chi2_ab (when V is not isotropic),
sigma_per_component (the root-mean-square null standard deviation of a and b, sqrt(trace(V) / 2); the per-component
values are in covariance_ab) and n_effective (W^2 / sum w^2, informational).
Exit codes: 0 ok; 1 a spurious-modulation check failed; 2 bad input.
Run: python3 <plugin root>/skills/hep-measurement/scripts/anisotropy.py exposure --config exp.json periods.csv
     python3 <plugin root>/skills/hep-measurement/scripts/anisotropy.py harmonic --events events.csv --exposure-map map.json
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

ISOTROPY_RTOL = 1e-12  # equal variances and zero covariance within this relative tolerance: the isotropic (Rice) case
PHASE_STEP_DEG = 5.0  # the dipole-phase grid of the anisotropic limit: 72 points on the circle, aligned with V's axes


def harmonic_covariance(edges, rel, n) -> dict:
    """Null covariance of the weighted harmonic components (a, b) for n events under isotropy, exact for a binned
    relative exposure rho_j (constant in each right-ascension bin) and weights w = 1 / rho: with R = int rho dalpha,
    Var(a) = (4/n) (int cos^2 / rho dalpha) R / (2 pi)^2, Var(b) likewise with sin^2 and Cov(a, b) with sin cos
    (W -> n E[w] = 2 pi n / R to leading order in 1/n; the integrals are closed-form per bin). Uniform exposure gives
    2/n, 2/n and 0 exactly. Returns covariance_ab, isotropic (equal variances and zero covariance within
    ISOTROPY_RTOL) and n_isotropic (the count with covariance (2/n_isotropic) I, None if not isotropic)."""
    if len(edges) != len(rel) + 1 or len(rel) < 1:
        raise ValueError("the exposure map needs len(ra_edges_deg) = len(relative_exposure) + 1")
    if any(not math.isfinite(x) for x in (*edges, *rel)) or any(b <= a for a, b in zip(edges, edges[1:])):
        raise ValueError("the exposure map edges must be finite and increasing, the exposures finite")
    if abs(edges[-1] - edges[0] - 360.0) > 1e-9:
        raise ValueError("the exposure map must cover the full circle of right ascension (360 deg)")
    if any(x <= 0.0 for x in rel):
        raise ValueError("the exposure map has a bin without exposure: the weighted harmonic and its null covariance "
                         "need exposure in every right-ascension bin")
    if n <= 0:
        raise ValueError("no events")
    if all(x == rel[0] for x in rel):  # constant exposure cancels: exactly the unweighted case
        m_aa, m_bb, m_ab = 2.0, 2.0, 0.0
    else:
        icc, iss, isc, big_r = [], [], [], []
        for lo, hi, rho in zip(edges, edges[1:], rel):
            x0, x1 = math.radians(lo), math.radians(hi)
            half = 0.5 * (x1 - x0)
            dsin2 = 0.25 * (math.sin(2.0 * x1) - math.sin(2.0 * x0))
            icc.append((half + dsin2) / rho)  # int cos^2 = x/2 + sin(2x)/4
            iss.append((half - dsin2) / rho)  # int sin^2 = x/2 - sin(2x)/4
            isc.append(0.5 * (math.sin(x1) ** 2 - math.sin(x0) ** 2) / rho)  # int sin cos = sin^2(x)/2
            big_r.append(rho * (x1 - x0))
        scale = 4.0 * math.fsum(big_r) / (2.0 * math.pi) ** 2
        m_aa, m_bb, m_ab = scale * math.fsum(icc), scale * math.fsum(iss), scale * math.fsum(isc)
    cov = [[m_aa / n, m_ab / n], [m_ab / n, m_bb / n]]
    mean = 0.5 * (m_aa + m_bb)
    iso = abs(m_aa - m_bb) <= ISOTROPY_RTOL * mean and abs(m_ab) <= ISOTROPY_RTOL * mean
    return {"covariance_ab": cov, "isotropic": iso, "n_isotropic": 2.0 * n / mean if iso else None}


def first_harmonic(ras, weights=None, decs=None, null=None) -> dict:
    """Weighted first harmonic of right ascensions in degrees (Linsley 1975). null is the harmonic_covariance result
    for the weights (required with non-uniform weights). Without it (unweighted events) the null covariance of (a, b)
    is (2/N) I. rayleigh_probability is P(chi^2 >= v^T V^-1 v) = exp(-chi^2 / 2) for v = (a, b) and the null
    covariance V (exact for a bivariate normal; exp(-N r^2 / 4) when V = (2/N) I); sigma_per_component is the
    root-mean-square null standard deviation of a and b, sqrt(trace(V) / 2); n_effective = W^2 / sum w^2 is
    informational only."""
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
           "n_events": len(ras), "n_effective": n_eff}
    if null is None:
        if weights is not None and any(x != w[0] for x in w):
            raise ValueError("non-uniform weights need the null covariance (harmonic_covariance of the exposure map)")
        n_iso, cov = n_eff, None
        source = "unweighted (or uniform) events: (2/N) I"
    else:
        n_iso, cov = null["n_isotropic"], null["covariance_ab"]
        source = ("exposure map: exact for the binned relative exposure under isotropy"
                  + ("; isotropic within 1e-12, so (2/n_isotropic) I" if null["isotropic"] else ""))
    if n_iso is not None:
        var = 2.0 / n_iso
        out.update({"sigma_per_component": math.sqrt(2.0 / n_iso),
                    "rayleigh_probability": math.exp(-n_iso * r * r / 4.0),
                    "covariance_ab": cov if cov is not None else [[var, 0.0], [0.0, var]]})
    else:
        (vaa, vab), (_, vbb) = cov
        det = vaa * vbb - vab * vab
        chi2 = (vbb * a * a - 2.0 * vab * a * b + vaa * b * b) / det
        out.update({"sigma_per_component": math.sqrt(0.5 * (vaa + vbb)), "rayleigh_probability": math.exp(-0.5 * chi2),
                    "covariance_ab": cov, "chi2_ab": chi2})
    out["covariance_source"] = source
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


class AnisotropicNull:
    """The amplitude r = |mu + eps| of the harmonic for a true dipole mu = s (cos phi, sin phi) and Gaussian noise
    eps ~ N(0, V) with an anisotropic null covariance V (unequal variances or a covariance of a and b)."""

    def __init__(self, cov):
        (vaa, vab), (vba, vbb) = cov
        if not all(math.isfinite(x) for x in (vaa, vab, vba, vbb)) or vab != vba:
            raise ValueError("the covariance of (a, b) must be a finite symmetric 2 x 2 matrix")
        det = vaa * vbb - vab * vab
        if vaa <= 0.0 or vbb <= 0.0 or det <= 0.0:
            raise ValueError("the covariance of (a, b) must be positive definite")
        self.lam1 = 0.5 * (vaa + vbb) + math.hypot(0.5 * (vaa - vbb), vab)  # the larger eigenvalue
        self.lam2 = det / self.lam1
        self.axis = 0.5 * math.atan2(2.0 * vab, vaa - vbb)  # direction of the lam1 eigenvector
        self.sqrt_det = math.sqrt(det)
        self._grids: dict = {}

    def _n_theta(self, s: float) -> int:
        """Points of the periodic trapezoid in the polar angle: the integrand is analytic and periodic, so the error
        falls exponentially with the number of points; its angular scale is set by sqrt(lam2 / lam1) and, for a true
        amplitude s, by sqrt(lam2) / s."""
        n = max(64, math.ceil(40.0 * math.sqrt(self.lam1 / self.lam2)), math.ceil(12.0 * s / math.sqrt(self.lam2)))
        return min(8192, 8 * math.ceil(n / 8))

    def _grid(self, n: int):
        if n not in self._grids:
            pts = []
            for k in range(n):
                t = 2.0 * math.pi * k / n
                ct, st = math.cos(t), math.sin(t)
                g = ct * ct / self.lam1 + st * st / self.lam2
                pts.append((ct / self.lam1, st / self.lam2, g, math.sqrt(0.5 * g), math.sqrt(0.5 * math.pi / g)))
            self._grids[n] = pts
        return self._grids[n]

    def cdf_eigen(self, x: float, s: float, phi: float) -> float:
        """P(r <= x) for the dipole phase phi measured from the lam1 eigen-axis: the bivariate normal integrated over
        the disk of radius x in polar coordinates, the radial integral in closed form (the exponent is quadratic in
        the radius: an exponential and an erf term), the polar angle by the periodic trapezoid rule."""
        if x <= 0.0:
            return 0.0
        cp, sp = math.cos(phi), math.sin(phi)
        if s > 40.0 * math.sqrt(self.lam1):
            # far from the noise (s above 40 sigma) r = s + eps_par + eps_perp^2 / (2 s) to second order: Gaussian about
            # the shifted mean (it differs from the trapezoid by up to about 6e-4 in the CDF at 40 sigma)
            from statistics import NormalDist
            v_par = cp * cp * self.lam1 + sp * sp * self.lam2
            v_perp = sp * sp * self.lam1 + cp * cp * self.lam2
            return NormalDist(s + 0.5 * v_perp / s, math.sqrt(v_par)).cdf(x)
        n = self._n_theta(s)
        terms = []
        if s == 0.0:
            for _, _, g, _, _ in self._grid(n):
                terms.append(-math.expm1(-0.5 * g * x * x) / g)
        else:
            c = s * s * (cp * cp / self.lam1 + sp * sp / self.lam2)
            e_c = math.exp(-0.5 * c)
            for pa, pb, g, k, pref in self._grid(n):
                h = s * (pa * cp + pb * sp)  # u^T V^-1 mu
                m = h / g
                q = max(c - h * m, 0.0)  # c - h^2 / g >= 0 (Cauchy-Schwarz)
                lo_arg, hi_arg = k * m, k * (x - m)
                if lo_arg * hi_arg >= 0.0:
                    erf_sum = math.erf(hi_arg) + math.erf(lo_arg)
                elif hi_arg < 0.0:
                    erf_sum = math.erfc(-hi_arg) - math.erfc(lo_arg)
                else:
                    erf_sum = math.erfc(-lo_arg) - math.erfc(hi_arg)
                terms.append((e_c - math.exp(-0.5 * q - 0.5 * g * (x - m) ** 2)) / g
                             + math.exp(-0.5 * q) * m * pref * erf_sum)
        return min(max(math.fsum(terms) / (n * self.sqrt_det), 0.0), 1.0)

    def cdf(self, x: float, s: float, phase_deg: float) -> float:
        """P(r <= x | s, phase) with the phase in degrees in the frame of (a, b)."""
        return self.cdf_eigen(x, s, math.radians(phase_deg) - self.axis)

    def median_null(self) -> float:
        """Median of r under isotropy: P(r <= x) = (1 / (2 pi sqrt(det V))) int (1 - exp(-x^2 g / 2)) / g dtheta,
        g = u^T V^-1 u, solved for 1/2 by bisection."""
        lo, hi = 0.0, 2.0 * math.sqrt(self.lam1)
        while self.cdf_eigen(hi, 0.0, 0.0) < 0.5:
            hi *= 2.0
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            if self.cdf_eigen(mid, 0.0, 0.0) < 0.5:
                lo = mid
            else:
                hi = mid
            if hi - lo <= 1e-15 * hi:
                break
        return 0.5 * (lo + hi)

    def allowed(self, r_obs: float, s: float, target: float) -> bool:
        """True when s is not excluded: P(r <= r_obs | s, phi) >= target for some dipole phase phi on the grid. The
        72-point phase grid (steps of PHASE_STEP_DEG) is aligned with the eigen-axes of V; r has the same law for phi,
        -phi and phi + pi (eps and its reflections about the axes have the same law), so the 19 phases from one axis
        to the other cover it."""
        steps = round(90.0 / PHASE_STEP_DEG)
        return any(self.cdf_eigen(r_obs, s, math.radians(j * PHASE_STEP_DEG)) >= target for j in range(steps + 1))

    def neyman(self, r_obs: float, cl: float) -> float | None:
        """Largest s not excluded for any dipole phase (P(r <= r_obs | s, phi) is nonincreasing in s for each phase,
        Anderson's theorem for a centrally symmetric unimodal density and a disk); None when s = 0 is excluded."""
        target = 1.0 - cl
        if not self.allowed(r_obs, 0.0, target):
            return None
        lo, hi = 0.0, r_obs + 10.0 * math.sqrt(self.lam1)
        while self.allowed(r_obs, hi, target):
            hi *= 2.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if self.allowed(r_obs, mid, target):
                lo = mid
            else:
                hi = mid
            if hi - lo <= 1e-13 * hi:
                break
        return 0.5 * (lo + hi)


def amplitude_upper_limit(r_obs, n: float | None, cl: float = DEFAULT_CL, covariance=None) -> dict:
    """Neyman upper limit on the amplitude, power-constrained at the expected limit (the limit for the median isotropic
    amplitude). Without a covariance (or n given for an isotropic null covariance (2/n) I) the limit comes from the
    Rice distribution of r. With an anisotropic null covariance of (a, b) a true amplitude s is excluded only when
    P(r <= r_obs | s, phi) < 1 - cl for every dipole phase phi on the grid (AnisotropicNull.allowed), so the limit
    holds whatever the phase.

    cl must lie in [0.5, 1) (ValueError otherwise): below 1/2 the expected limit is empty (even s = 0 is excluded at
    the median isotropic amplitude), so the power constraint is undefined. At cl = 1/2 the expected limit is 0
    analytically (P(r <= median | s = 0) = 1/2); a rounding-level empty result there is reported as 0."""
    if not 0.5 <= cl < 1.0:
        raise ValueError(f"the confidence level must lie in [0.5, 1), got {cl} (below 0.5 the expected limit, the "
                         "Neyman limit at the median isotropic amplitude, is empty and the power constraint undefined)")
    if covariance is None:
        median_iso = math.sqrt(4.0 * math.log(2.0) / n)
        expected = _neyman(median_iso, n, cl)
        out = {"confidence_level": cl, "expected_limit": expected, "median_isotropic_amplitude": median_iso,
               "construction": "Neyman upper limit from the Rice distribution of r, power-constrained at the expected "
                               "limit"}
        if r_obs is not None:
            ney = _neyman(r_obs, n, cl)
    else:
        model = AnisotropicNull(covariance)
        median_iso = model.median_null()
        expected = model.neyman(median_iso, cl)
        out = {"confidence_level": cl, "expected_limit": expected, "median_isotropic_amplitude": median_iso,
               "construction": "Neyman upper limit for the anisotropic null covariance of (a, b): s is excluded only "
                               "if excluded for every dipole phase on a 72-point grid (steps of 5 deg aligned with "
                               "the covariance's eigen-axes); power-constrained at the expected limit",
               "phase_grid_deg": PHASE_STEP_DEG}
        if r_obs is not None:
            ney = model.neyman(r_obs, cl)
    if expected is None:  # only at (or within rounding of) cl = 1/2: s = 0 is allowed at the median (docstring)
        out["expected_limit"] = expected = 0.0
    if r_obs is not None:
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
    warnings, weights, null = [], None, None
    if args.exposure_map:
        emap = json.loads(args.exposure_map.read_text(encoding="utf-8"))
        edges, rel = emap["ra_edges_deg"], emap["relative_exposure"]
        weights = []
        for a in ras:
            i = min(int((a - edges[0]) / (edges[1] - edges[0])), len(rel) - 1)
            if rel[i] <= 0:
                raise ValueError(f"an event at right ascension {a} falls where the exposure is zero")
            weights.append(1.0 / rel[i])
        null = harmonic_covariance(edges, rel, len(ras))
    else:
        warnings.append("no --exposure-map: uniform exposure assumed in right ascension; an exposure modulation would "
                        "appear as an anisotropy")
    h = first_harmonic(ras, weights, decs, null)
    if null is None or null["isotropic"]:
        n_iso = h["n_effective"] if null is None else null["n_isotropic"]
        limit = amplitude_upper_limit(h["amplitude"], n_iso, args.cl)
    else:
        limit = amplitude_upper_limit(h["amplitude"], None, args.cl, covariance=null["covariance_ab"])
    out = {"harmonic": h, "upper_limit": limit,
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
            if not 0.5 <= args.cl < 1:
                raise ValueError(f"--cl must lie in [0.5, 1), got {args.cl} (an upper limit below CL 0.5 is not "
                                 "supported: the expected limit is empty and the power constraint undefined)")
            if not 0 < args.spurious_alpha < 1:
                raise ValueError("--spurious-alpha must lie in (0, 1)")
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
