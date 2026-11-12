"""An analytic Cherenkov STAND-IN for the RICH-replica items of Part B section 15.2 (P3 with one and with several beta)
and section 8.7 note 6 (the section 7.4 basin classification on the "refractive index and geometric scale"
degeneracy of section 3.5); phase 3, labelled `analytic-stand-in`, never Geant4 and never evidence for the replica.

The real items run on the g4sim replica case with full optical tracking (resimulation, a theta on the radiator height
and on the refractive-index spectrum); this module replaces the transport by the Cherenkov relation so that the
design-stage path runs in unit tests:

- emission at the middle of a flat radiator of thickness t (index n), cos theta_c = 1 / (n beta);
- refraction at the radiator's lower face into vacuum, sin theta_out = n sin theta_c (the foil neglected);
- the ring radius at the detection plane, a height H below the radiator: R = (t/2) tan theta_c + H tan theta_out;
- per event the ring radius is measured with a per-event resolution sigma_R (photon count and per-photon spread
  folded in); the observable of a sample at one beta is the mean ring radius of its events.

Parameters: `height_mm` (H) and `index_scale` (s, n = s n_ref: a theta on the spectrum rescales the whole spectrum).
With one beta the radius is one function of (H, n): H and n are not identifiable; a second beta (another momentum or
particle species) separates them, because d ln R / d n depends on beta while d ln R / d ln H = 1 (approximately).
"""
from __future__ import annotations

import math

import numpy as np

LABEL = "analytic-stand-in"
MODE = {"mode": "refractive index and geometric scale",
        "parameters": ["height_mm", "index_scale"],
        "signal": "multiple beta: several momenta or particle species (section 3.5)"}


def beta_of(kinetic_per_nucleon_gev: float, mass_per_nucleon_gev: float = 0.938272) -> float:
    gamma = 1.0 + kinetic_per_nucleon_gev / mass_per_nucleon_gev
    return math.sqrt(1.0 - 1.0 / gamma ** 2)


def ring_radius(n: float, beta: float, height_mm: float, thickness_mm: float) -> float:
    """The ring radius at the detection plane (mm); NaN below threshold or under total internal reflection."""
    c = 1.0 / (n * beta)
    if c >= 1.0:
        return math.nan
    tc = math.acos(c)
    so = n * math.sin(tc)
    if so >= 1.0:
        return math.nan
    return 0.5 * thickness_mm * math.tan(tc) + height_mm * math.tan(math.asin(so))


class CherenkovStandIn:
    """The section 7.1 `evaluate` of the stand-in over samples [{name, beta}] (one observable per sample, run label =
    sample name): pred = ring radius, V_MC = 0 (analytic), s2 = sigma_R^2 per event (independent samples)."""

    parameters = ["height_mm", "index_scale"]

    def __init__(self, samples: list, n_ref: float = 1.05, thickness_mm: float = 25.0, sigma_event_mm: float = 1.5,
                 nominal: dict | None = None):
        self.samples = [dict(s) for s in samples]
        self.n_ref, self.thickness, self.sigma = float(n_ref), float(thickness_mm), float(sigma_event_mm)
        self.nominal = {"height_mm": 470.0, "index_scale": 1.0, **(nominal or {})}
        self.observables = [s["name"] for s in self.samples]

    def default_method(self, par: str) -> str:
        return "resimulation"                    # on the replica: a theta on a detector-spec field (section 11.4)

    def evaluate(self, theta: dict, phi=None, psi=None, model: str = "nominal", effects_off=(), seeds=None,
                 names=None) -> dict:
        v = {**self.nominal, **(theta or {})}
        n = float(v["index_scale"]) * self.n_ref
        smp = [s for s in self.samples if names is None or s["name"] in names]
        pred = np.array([ring_radius(n, float(s["beta"]), float(v["height_mm"]), self.thickness) for s in smp])
        k = len(smp)
        return {"names": [s["name"] for s in smp], "pred": pred, "V_MC": np.zeros((k, k)),
                "s2": np.eye(k) * self.sigma ** 2, "runs": [s["name"] for s in smp], "n_eff": np.full(k, np.inf),
                "missing_support_runs": [], "flags": [LABEL], "V_emu": None, "V_learn": None, "theta": v}


def contract(samples: list, exposure: int = 2000, height=(450.0, 490.0), scale=(0.998, 1.002)) -> dict:
    """A calibration contract of the stand-in: theta (height_mm, index_scale) with their sampling bounds, one Gaussian
    ring-radius observable per sample (identity link), the exposure per sample."""
    pars = [{"name": "height_mm", "role": "theta", "sampling_bounds": list(height), "physical_bounds": [1.0, 2000.0]},
            {"name": "index_scale", "role": "theta", "sampling_bounds": list(scale), "physical_bounds": [0.9, 1.1]}]
    obs = [{"name": s["name"], "role": "calibration", "block": "gaussian", "link": "identity", "functional": "location"}
           for s in samples]
    return {"schema": "calibration-contract/1", "simulator": LABEL, "parameters": pars, "observables": obs,
            "exposure": {s["name"]: exposure for s in samples}, "validation": {"mode": "holdout", "N_dc": []}}


def classification(fit, box, digits: int = 2) -> tuple:
    """The section 7.4 classification of one `fit.find_extremum` result (section 8.7 note 6): the admitted basins
    matched by position (in units of the prior box, rounded), whether theta-hat is a tie, whether no endpoint was
    admitted, and whether a non-identified stationary point lies below the lowest basin."""
    lo = np.array([a for a, _ in box], float)
    w = np.array([b - a for a, b in box], float)
    basins = tuple(sorted(tuple(np.round((np.asarray(b["theta"], float) - lo) / w, digits).tolist())
                          for b in (fit.basins or [])))
    return (basins, "tie" in fit.flags, "no-admitted-endpoint" in fit.flags, "nonidentified-below" in fit.flags)


def reseeding_stability(problem_of_toy, n_toys: int, n_reseed: int, beta0_of, seed, digits: int = 2,
                        n_start: int | None = None) -> dict:
    """The fraction of toys whose classification is unchanged under `n_reseed` reseedings of the section 7.4 starts
    (section 8.7 note 6; the calibration needs >= 10^3 toys and 10 reseedings, rule >= 99%).
    problem_of_toy(j) -> a problem with its pseudo-data; beta0_of(problem) -> the nominal beta."""
    from . import fit as F
    same, per = 0, []
    kinds: dict[str, int] = {}
    for j in range(n_toys):
        p = problem_of_toy(j)
        b0 = beta0_of(p)
        cls = {classification(F.find_extremum(p, (seed, j, r), b0, n_start=n_start), p.prior_box(), digits)
               for r in range(n_reseed)}
        same += len(cls) == 1
        per.append(len(cls))
        for c in cls:
            key = f"basins={len(c[0])} tie={c[1]} no-admitted={c[2]} nonidentified-below={c[3]}"
            kinds[key] = kinds.get(key, 0) + 1
    return {"toys": n_toys, "reseedings": n_reseed, "unchanged": same, "fraction": same / n_toys if n_toys else None,
            "classes_per_toy": per, "kinds": kinds, "label": LABEL,
            "rule": ">= 0.99 of >= 1000 toys under 10 reseedings (section 8.7 note 6)"}
