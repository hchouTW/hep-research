#!/usr/bin/env python3
"""cr-provider/1 entrypoint of theory:cr-secondary-ratio: the closed-form B/C of the 1D thin-disc diffusion model.

It wraps the closed form of predict.py (thin_disc_ratio, no second implementation of the physics) behind the provider
protocol of core/provider: a request names parameter points in the canonical names and B/C bins in kinetic energy per
nucleon (axis ekn, GeV/n); each point gets one prediction per observable and, when wanted, its components.

Parameters (the profile.json 'provider' domain; canonical names, mapped to predict.py's keys): D0_cm2_s (D0, cm^2/s),
L_kpc (L, kpc), delta, R0_gv (predict.py R0_GV, GV), disc_halfwidth_pc (predict.py h_kpc = disc_halfwidth_pc / 1000).
A parameter a point omits keeps its value in benchmarks/bc-benchmark.json; the gas density n_H, the parents C and O with
their observed ratios and the nominal cross-section set (models/xs-illustrative-A.json) are fixed by that file. The
declared domain is the range the closed form is offered for, not a validated range of physics.

Values: the ratio averaged uniformly in ln(E/n) over each bin (predict.py bin_averaged, Gauss-Legendre, 8 nodes),
bin_semantics bin-averaged, convention crsr:bin_average. This is the profile's own binning convention, not the ratio
of bin-integrated fluxes (r3 P2): the profile has no primary spectra. A caller that needs P2 binning must not use it.
Components (decomposable): the ratio is a sum over production channels j -> B, sigma_jB r_j / (sigma_B + D/(h n_H v L)),
so each channel is one component of kind channel in the same bins, and the components add up to the prediction. A
norm-type change of a production cross section multiplies its component; an inelastic change needs a new evaluation.
Labels: synthetic and unvalidated (ILLUSTRATIVE inputs). numerical_tolerance 1e-6: the 8-node quadrature against a
32-node one (profile test). No external program; computational_run_ref is null. Never modulates.

Usage:
  python3 provider.py --request REQUEST.json --response RESPONSE.json [--allow-outside-validated-range]
  python3 provider.py --serve [--allow-outside-validated-range]
Exit codes: 0 ok, 1 refused or every point failed, 3 some points failed, 2 unreadable request or unwritable response.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent
PLUGIN_ROOT = PROFILE.parents[2]
sys.dont_write_bytecode = True
for entry in (str(PLUGIN_ROOT), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)
from core.provider.entrypoint import provider_main  # noqa: E402

import predict  # noqa: E402

CONFIG = PROFILE / "benchmarks" / "bc-benchmark.json"
NUMERICAL_TOLERANCE = 1e-6
QUADRATURE_NODES = 8
# canonical parameter name -> (predict.py key, factor from the canonical unit to predict.py's unit)
PARAMETER_MAP = {"D0_cm2_s": ("D0_cm2_s", 1.0), "L_kpc": ("L_kpc", 1.0), "delta": ("delta", 1.0),
                 "R0_gv": ("R0_GV", 1.0), "disc_halfwidth_pc": ("h_kpc", 1e-3)}


def declaration() -> dict:
    profile = json.loads((PROFILE / "profile.json").read_text(encoding="utf-8"))
    decl = dict(profile["provider"])
    decl.setdefault("version", profile["version"])
    return decl


def model_overrides(point: dict) -> dict:
    return {PARAMETER_MAP[name][0]: float(value) * PARAMETER_MAP[name][1] for name, value in point.items()}


def channel_terms(params: dict, e_n: float, cfg: dict, xs: dict) -> dict:
    """Per production channel 'j->B': sigma_jB r_j / (sigma_B + D/(h n_H v L)) at one E/n; their sum is
    predict.thin_disc_ratio."""
    rig, b = predict.kinematics(e_n, cfg["secondary"])
    sec = cfg["secondary"]["name"]
    sig_s = predict._sigma(xs, "inelastic_mb", sec)
    h = predict._positive(params, "h_kpc") * predict.KPC_CM
    big_l = predict._positive(params, "L_kpc") * predict.KPC_CM
    escape = predict.diffusion_coefficient(params, rig, b) / (
        h * predict._positive(params, "n_H_cm3") * b * predict.C_CM_S * big_l)
    return {f"{p['name']}->{sec}": s_js * r / (sig_s + escape) for p, s_js, r in predict._production(cfg, xs)}


def bin_averaged_channels(params: dict, edges: list[float], cfg: dict, xs: dict,
                          nodes: int = QUADRATURE_NODES) -> dict:
    """Each channel averaged uniformly in ln(E/n) over each bin, with predict.bin_averaged's quadrature."""
    import numpy as np
    x, w = np.polynomial.legendre.leggauss(nodes)
    out: dict[str, list[float]] = {}
    for lo, hi in zip(edges, edges[1:]):
        a, b = math.log(lo), math.log(hi)
        sums: dict[str, float] = {}
        for t, wt in zip(x, w):
            for key, val in channel_terms(params, math.exp(0.5 * (b - a) * t + 0.5 * (a + b)), cfg, xs).items():
                sums[key] = sums.get(key, 0.0) + 0.5 * float(wt) * val
        for key, val in sums.items():
            out.setdefault(key, []).append(val)
    return out


def prediction(obs: dict, edges: list[float], values: list[float], point: dict, params: dict, cfg: dict) -> dict:
    """The prediction extension (contracts ext_prediction.json) of one observable at one point."""
    return {
        "observable": {
            "quantity": "ratio",
            "process": "secondary-to-primary ratio B/C from spallation of C and O on interstellar hydrogen",
            "species": [{"name": "boron"}, {"name": "carbon"}],
            "variables": [{"name": "kinetic_energy_per_nucleon", "unit": "GeV/n", "edges": edges}],
            "phase_space": {"definition": "local interstellar ratio at the Galactic mid-plane (z = 0), before solar "
                                          "modulation", "fiducial": False},
            "level": "crsr:local-interstellar",
            "normalization": {"kind": "exposure", "value": "not-applicable",
                              "convention": "ratio of two fluxes at the same E/n; the normalization cancels"},
            "bin_semantics": "bin-averaged",
            "unit": "1",
            "conventions": {"crsr:bin_average": "a binned value is the ratio averaged uniformly in ln(E/n) over the "
                                                "bin (Gauss-Legendre, 8 nodes), not the ratio of bin-averaged fluxes",
                            "crsr:transport_model": "diffusion-1d thin disc, D(R) = D0 beta (R/R0)^delta, no "
                                                    "convection, reacceleration, losses or decay"},
            "validity_range": {"variable": "kinetic_energy_per_nucleon", "min": 1.0, "max": 1000.0, "unit": "GeV/n"},
        },
        "theory_spec_ref": "derivations/theory-spec.json",
        "derivation_status": "analytic-derivation",
        "parameter_point": {**{k: float(v) for k, v in point.items()},
                            "model_parameters": params, "cross_section_set": cfg["cross_section_set"]},
        "representation": "numerical",
        "values": {"edges": edges, "values": values, "unit": "1"},
        "uncertainties": [],
        "allowed_transformations": ["solar modulation per isotope (outside this provider; force field in "
                                    "hep-measurement)", "rebin (recompute the ln(E/n) average; never merge averaged "
                                    "values)"],
    }


def evaluate_point(request: dict, point: dict, context: dict) -> dict:
    cfg = dict(predict.load_json(CONFIG), model="diffusion-1d")
    params = predict.model_parameters(cfg, model_overrides(point))
    xs = predict.load_cross_sections(cfg)
    predictions, components = [], []
    for obs in request["observables"]:
        edges = [float(obs["bins"][0][0])] + [float(hi) for _, hi in obs["bins"]]
        channels = bin_averaged_channels(params, edges, cfg, xs)
        totals = predict.bin_averaged(cfg, edges, model_overrides(point), n_nodes=QUADRATURE_NODES)
        predictions.append(prediction(obs, edges, totals, point, params, cfg))
        for key, vals in sorted(channels.items()):
            parent, daughter = key.split("->")
            components.append({"observable": obs["id"], "id": key, "kind": "channel", "parent": parent,
                               "daughter": daughter, "values": vals, "unit": "1"})
    out = {"labels": ["synthetic", "unvalidated"], "numerical_tolerance": NUMERICAL_TOLERANCE,
           "computational_run_ref": None}
    if "lis" in context["want"]:
        out["predictions"] = predictions
    if "components" in context["want"]:
        out["components"] = components
    return out


def main(argv=None) -> int:
    return provider_main(declaration(), evaluate_point, argv, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    sys.exit(main())
