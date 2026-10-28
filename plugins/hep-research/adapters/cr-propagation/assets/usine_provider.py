#!/usr/bin/env python3
"""cr-provider/1 entrypoint of USINE: one USINE V3.5 run per parameter point, read into ratios of bin integrals.

It wraps this adapter's translator and reader (usine_translate.py translate and run_usine, usine_to_prediction.py
ratio_of_bin_integrals; no second implementation) behind the provider protocol of core/provider: a request names
parameter points in the canonical names and bins of B/C, 10Be/9Be or Be/B on the axis ekn (GeV/n) or rigidity (GV);
each point is one USINE run and gets one prediction per observable.

Transport: the request's 'transport' block (contracts ext_theory_spec.transport, r3 5.4) if given, else the built-in
DEFAULT_TRANSPORT (harmonized-v1 with the isotopic network and the isotopic ILLUSTRATIVE cross sections, equal to the
fixture tests/adapters/fixtures/cr_propagation/usine/specs/d1-isotopic.json, checked by the adapter tests). A point
overrides D0_cm2_s, delta and eta (diffusion), L_kpc (geometry), V_c_kms (convection) and V_A_kms (reacceleration, in
the transport's zone). Cross sections: the ILLUSTRATIVE sets of theory:cr-secondary-ratio
(usine_translate.ILLUSTRATIVE_SETS), or USINE's own cross-section files with data-normalised source abundances
('usine:<file>' names, read in place from HEP_USINE_DATA, never copied; work package B1X); a transport naming another
set fails the point with provider-error, never replaced. What USINE cannot express exactly is listed in each prediction's parameter_point.transport_substitutes;
what it cannot express at all fails the point. An observable whose isotopes are not in the network (Be/B or 10Be/9Be
with the element-level set) fails the point.
Grid: the translator's (20 E_k/n nodes per decade from below 0.8 times the lowest to above 1.25 times the highest E_k/n
the bins need; 100 Fourier-Bessel terms in the 2D model). The run is located through HEP_USINE_BIN and
HEP_USINE_DATA; without them a point fails with provider-error (R4), nothing falls back.

Values: the ratio of the bin-integrated summed numerator and denominator (r3 P2), isotopes summed at equal rigidity
on the axis rigidity and at equal E/n on the axis ekn (P3); fluxes per E_k/n from USINE's tables (P11). Never
modulated (phi = 0). Not decomposable. Labels: synthetic and unvalidated with the ILLUSTRATIVE cross sections,
unvalidated with USINE's own inputs.
numerical_tolerance NUMERICAL_TOLERANCE (0.005): a rounded-up bound on the largest relative change of B/C (2-1000 GV)
and 10Be/9Be (0.05-10 GeV/n) bins between this grid and one with 80 nodes per decade and 200 Bessel terms (2.0e-3,
with reacceleration; VALIDATION CRPROP-B1); not a physics uncertainty.
Runs: each run directory (initialisation file, cross-section tables, outputs, computational-run record) is kept under
HEP_USINE_RUN_DIR/<run name> when that folder is set, and its record id is the evaluation's computational_run_ref;
otherwise the run lives in a temporary folder removed after reading and the reference is null. The run name is 'p'
plus the first 16 hex digits of the point hash, so equal requests give equal responses.

Usage:
  python3 usine_provider.py --request REQUEST.json --response RESPONSE.json [--allow-outside-validated-range]
  python3 usine_provider.py --serve [--allow-outside-validated-range]
Exit codes: 0 ok, 1 refused or every point failed, 3 some points failed, 2 unreadable request or unwritable response.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADAPTER = HERE.parent
PLUGIN_ROOT = ADAPTER.parents[1]
sys.dont_write_bytecode = True
for entry in (str(PLUGIN_ROOT), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)
from core.provider.entrypoint import provider_main  # noqa: E402
from core.provider.hashing import point_hash  # noqa: E402

import usine_to_prediction as reader  # noqa: E402
import usine_translate as translator  # noqa: E402

PROVIDER_ID = "usine"
NUMERICAL_TOLERANCE = 0.005
RUN_TIMEOUT_S = 3600.0
POINT_TARGETS = {"D0_cm2_s": ("diffusion", "D0_cm2_s"), "delta": ("diffusion", "delta"), "eta": ("diffusion", "eta"),
                 "L_kpc": ("geometry", "L_kpc"), "V_c_kms": ("convection", "V_c_kms"),
                 "V_A_kms": ("reacceleration", "V_A_kms")}
DEFAULT_TRANSPORT = {
    "geometry": {"kind": "cylinder-2d", "L_kpc": 4.0, "radius_kpc": 20.0, "disc_halfwidth_pc": 100},
    "diffusion": {"form": "beta^eta (R/R0)^delta with smooth breaks", "D0_cm2_s": 3.0e28, "R0_gv": 1.0, "eta": 1.0,
                  "delta": 0.5, "breaks": []},
    "reacceleration": {"V_A_kms": 0.0, "zone": "thin-disc", "relation": "Seo-Ptuskin 1994", "w": 1.0},
    "convection": {"V_c_kms": 0.0, "dVc_dz_kms_per_kpc": 0.0},
    "losses": [],
    "decay": {"enabled": False, "lorentz_dilation": True, "ec_treatment": "fully-stripped"},
    "gas": {"model": "uniform, n_H = 1 cm^-3", "He_to_H_number": 0.1},
    "sources": {"spatial": "not fixed by harmonized-v1; each code records its choice",
                "injection": [{"species_group": "all primaries", "gamma": 2.3, "breaks": []}],
                "abundances": "fixed by the parent list of theory:cr-secondary-ratio"},
    "cross_sections": {
        "production_set": "theory:cr-secondary-ratio models/xs-illustrative-decay.json (ILLUSTRATIVE, isotopic)",
        "inelastic_set": "theory:cr-secondary-ratio models/xs-illustrative-decay.json (ILLUSTRATIVE, isotopic)",
        "ghost_threshold": "off: ghost nuclei and tertiary chains off on both sides"},
    "species": {"network_top": "O-16", "isotopic": True},
    "family": "SLIM",
    "free": [],
}


def declaration() -> dict:
    adapter = json.loads((ADAPTER / "adapter.json").read_text(encoding="utf-8"))
    decls = adapter["provider"] if isinstance(adapter["provider"], list) else [adapter["provider"]]
    decl = dict(next(d for d in decls if d["id"] == PROVIDER_ID))
    decl.setdefault("version", adapter["version"])
    return decl


def transport_for(request: dict, point: dict) -> dict:
    """The request's transport (or DEFAULT_TRANSPORT) with the point's values written into their blocks."""
    transport = copy.deepcopy(request.get("transport") or DEFAULT_TRANSPORT)
    for name, value in point.items():
        block, key = POINT_TARGETS[name]
        transport.setdefault(block, {})[key] = float(value)
    return transport


def ekn_range(observables: list[dict], species) -> tuple[float, float]:
    """(lowest, highest) E_k/n in GeV/n that every requested bin of every isotope involved needs."""
    lo, hi = float("inf"), 0.0
    for obs in observables:
        num, den = reader.present(obs["id"], species)
        edges = [float(obs["bins"][0][0])] + [float(b) for _, b in obs["bins"]]
        for nuclide in num + den:
            z, a = reader.charge_and_mass(nuclide)
            lims = edges if obs["axis"] == "ekn" else [reader.ekn_from_rigidity(r, z, a) for r in edges]
            lo, hi = min(lo, lims[0]), max(hi, lims[-1])
    return lo, hi


def run_point(transport: dict, name: str, observables: list[dict], run_dir: Path) -> tuple[dict, dict, dict]:
    """Translate and run one point; (spec, run result, isotope tables). Raises on any failure (R4)."""
    binary, data_path = os.environ.get("HEP_USINE_BIN"), os.environ.get("HEP_USINE_DATA")
    if not (binary and Path(binary).is_file() and os.access(binary, os.X_OK)):
        raise RuntimeError("USINE executable not found: set HEP_USINE_BIN (missing tool, R4)")
    if not (data_path and Path(data_path).is_dir()):
        raise RuntimeError("USINE inputs folder not found: set HEP_USINE_DATA (missing tool, R4)")
    probe = translator.translate(transport, name, (1.0, 10.0))
    spec = translator.translate(transport, name, ekn_range(observables, probe["species"]))
    result = translator.run_usine(spec, run_dir, Path(binary), Path(data_path), RUN_TIMEOUT_S)
    if not result["ok"]:
        raise RuntimeError(f"USINE run failed (exit {result['exit_status']}): {result['log_tail'][-400:]}")
    return spec, result, reader.read_run(Path(run_dir) / "out", spec["model"], spec["species"])


def evaluate_point(request: dict, point: dict, context: dict) -> dict:
    transport = transport_for(request, point)
    name = "p" + point_hash(request.get("transport"), request["provider"], request["provider_version"], point)[:16]
    keep = os.environ.get("HEP_USINE_RUN_DIR")
    with tempfile.TemporaryDirectory(prefix="usine-provider-") as scratch:
        run_dir = Path(keep) / name if keep else Path(scratch) / name
        spec, result, tables = run_point(transport, name, request["observables"], run_dir)
        rec = translator.record(spec, result, Path(os.environ["HEP_USINE_BIN"]))
        if keep:
            (run_dir / f"{name}.computational-run.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
            (run_dir / "translation.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
        predictions = []
        for obs in request["observables"]:
            edges = [float(obs["bins"][0][0])] + [float(b) for _, b in obs["bins"]]
            values = reader.ratio_of_bin_integrals(tables, obs["id"], edges, obs["axis"])
            predictions.append(reader.prediction(obs["id"], obs["axis"], edges, values, point, spec))
    labels = ["unvalidated"] if spec.get("mode") == "usine-inputs" else ["synthetic", "unvalidated"]
    out = {"labels": labels, "numerical_tolerance": NUMERICAL_TOLERANCE,
           "computational_run_ref": rec["artifact_id"] if keep else None}
    if "lis" in context["want"]:
        out["predictions"] = predictions
    return out


def main(argv=None) -> int:
    return provider_main(declaration(), evaluate_point, argv, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    sys.exit(main())
