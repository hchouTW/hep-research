#!/usr/bin/env python3
"""cr-provider/1 entrypoint of DRAGON2: one DRAGON2 run per parameter point, read into ratios of bin integrals.

It wraps this adapter's translator and reader (dragon2_run.py spec_from_transport and prepare, dragon2_to_prediction.py
ratio_of_bin_integrals; no second implementation) behind the provider protocol of core/provider: a request names
parameter points in the canonical names and bins of B/C or 10Be/9Be on the axis ekn (GeV/n) or rigidity (GV); each
point is one DRAGON2 run and gets one prediction per observable.

Transport: the request's 'transport' block (contracts ext_theory_spec.transport, r3 5.4) if given, else the
built-in DEFAULT_TRANSPORT (equal to harmonized-v1-isotopic, tests/adapters/fixtures/cr_propagation/specs/, checked by
the adapter tests). A point overrides D0_cm2_s and delta (diffusion), L_kpc (geometry), V_c_kms (convection) and
V_A_kms (reacceleration, in the transport's zone). Production cross sections: only the ILLUSTRATIVE isotopic set
(ILLUSTRATIVE_CHANNELS_MB, equal to theory:cr-secondary-ratio models/xs-illustrative-decay.json for 12C and 16O,
checked by the tests); a transport naming another production set is refused (provider-error), never replaced. What
DRAGON2 cannot express is listed under the prediction's parameter_point.transport_substitutes (dragon2_run.py):
among them, V_A converted to DRAGON2's Ptuskin94 whole-halo convention by hep-theory's transport_conventions.py, and
Galprop gas instead of BronfFerr when losses are on (DRAGON2 cd588707's nuclear Coulomb loss diverges where the HII
density is 0).
Grid: the translator's (radial step 0.5 kpc, vertical step about 0.02 kpc, energy factor 1.2), charges from the
lightest observed isotope to Z = 8 (network top O-16), E/n from 0.8 times the lowest to 1.25 times the highest E/n the
bins need (at least 0.01 GeV/n). The DRAGON2 run is located through HEP_DRAGON2_BIN and HEP_DRAGON2_DATA; without
them a point fails with provider-error (R4), nothing falls back.

Values: the ratio of the bin-integrated summed numerator and denominator (r3 P2), isotopes summed at equal rigidity
on the axis rigidity and at equal E/n on the axis ekn (P3); fluxes per E/n are DRAGON2's columns times A (P11).
bin_semantics bin-averaged (the ratio of the two bin averages). Unmodulated local interstellar ratios; never
modulates. Not decomposable (a channel decomposition would need one run per channel). Labels synthetic and
unvalidated (ILLUSTRATIVE cross sections). numerical_tolerance NUMERICAL_TOLERANCE (0.01): a rounded-up bound on the
largest relative change of B/C bins (2.2e-3 on E-crprop, ekn 10-100 GeV/n and rigidity 2-1000 GV) when the vertical
step is halved and the energy factor goes from 1.2 to 1.1 (VALIDATION CRPROP-D1); not a physics uncertainty.
Runs: each run directory (XML, source.param, data links, output, computational-run record) is kept under
HEP_DRAGON2_RUN_DIR/<run name> when that folder is set, and its record id is the evaluation's computational_run_ref;
otherwise the run lives in a temporary folder removed after reading and the reference is null. The run name is
'p' plus the first 16 hex digits of the point hash, so equal requests give equal responses.

Usage:
  python3 dragon2_provider.py --request REQUEST.json --response RESPONSE.json [--allow-outside-validated-range]
  python3 dragon2_provider.py --serve [--allow-outside-validated-range]
Exit codes: 0 ok, 1 refused or every point failed, 3 some points failed, 2 unreadable request or unwritable response.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import time
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

import dragon2_run  # noqa: E402
import dragon2_to_prediction as reader  # noqa: E402

NUMERICAL_TOLERANCE = 0.01
RUN_TIMEOUT_S = 3600.0
NETWORK_TOP_Z = 8
ILLUSTRATIVE_SET = "xs-illustrative-decay"
# 12C and 16O to the propagated secondaries, sigma on hydrogen in mb (ILLUSTRATIVE placeholders, not data)
ILLUSTRATIVE_CHANNELS_MB = {
    "6012->4007": 10.0, "6012->4009": 6.0, "6012->4010": 4.0, "6012->5010": 20.0, "6012->5011": 50.0,
    "8016->4007": 10.0, "8016->4009": 5.0, "8016->4010": 2.0, "8016->5010": 10.0, "8016->5011": 25.0,
}
# observable -> (numerator columns, denominator columns, species names)
OBSERVABLES = {
    "B/C": (["NUC_5010", "NUC_5011"], ["NUC_6012", "NUC_6013", "NUC_6014"], ["boron", "carbon"]),
    "10Be/9Be": (["NUC_4010"], ["NUC_4009"], ["beryllium-10", "beryllium-9"]),
}
VARIABLE = {"ekn": ("kinetic_energy_per_nucleon", "GeV/n"), "rigidity": ("rigidity", "GV")}
POINT_TARGETS = {"D0_cm2_s": ("diffusion", "D0_cm2_s"), "delta": ("diffusion", "delta"),
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
    decl = dict(next(d for d in decls if d["id"] == "dragon2"))
    decl.setdefault("version", adapter["version"])
    return decl


def transport_for(request: dict, point: dict) -> dict:
    """The request's transport (or DEFAULT_TRANSPORT) with the point's values written into their blocks."""
    transport = copy.deepcopy(request.get("transport") or DEFAULT_TRANSPORT)
    xs = (transport.get("cross_sections") or {}).get("production_set", "")
    if ILLUSTRATIVE_SET not in str(xs):
        raise ValueError(f"production_set {xs!r}: this provider runs only the ILLUSTRATIVE isotopic set "
                         f"({ILLUSTRATIVE_SET}); no other set is substituted")
    for name, value in point.items():
        block, key = POINT_TARGETS[name]
        transport.setdefault(block, {})[key] = float(value)
    return transport


def run_ranges(observables: list[dict]) -> tuple[tuple[int, int], tuple[float, float]]:
    """(Zmin, Zmax) and (Ekmin, Ekmax in GeV/n) that cover every requested bin of every isotope involved."""
    z_min, e_lo, e_hi = NETWORK_TOP_Z, float("inf"), 0.0
    for obs in observables:
        num, den, _ = OBSERVABLES[obs["id"]]
        edges = [float(obs["bins"][0][0])] + [float(hi) for _, hi in obs["bins"]]
        for col in num + den:
            z, a = reader.charge_and_mass(col)
            z_min = min(z_min, z)
            lims = edges if obs["axis"] == "ekn" else [reader.ekn_from_rigidity(r, z, a) for r in edges]
            e_lo, e_hi = min(e_lo, lims[0]), max(e_hi, lims[-1])
    return (z_min, NETWORK_TOP_Z), (max(0.01, 0.8 * e_lo), 1.25 * e_hi)


def run_dragon2(spec: dict, run_dir: Path) -> tuple[Path, dict | None]:
    """Prepare and run one DRAGON2 run in run_dir; the output file and the computational-run record (or raise)."""
    binary, data_path = os.environ.get("HEP_DRAGON2_BIN"), os.environ.get("HEP_DRAGON2_DATA")
    if not (binary and Path(binary).is_file() and os.access(binary, os.X_OK)):
        raise RuntimeError("DRAGON2 executable not found: set HEP_DRAGON2_BIN (missing tool, R4)")
    if not (data_path and Path(data_path).is_dir()):
        raise RuntimeError("DRAGON2 data directory not found: set HEP_DRAGON2_DATA (missing tool, R4)")
    data_dir = Path(data_path)
    source_param = data_dir.parent / "examples" / "BaseModel_DRAGONxsec.source.param"
    checked = dragon2_run.check_spec(spec)
    inputs = dragon2_run.prepare(checked, run_dir, data_dir, source_param)
    command = [str(Path(binary).resolve()), f"{spec['name']}.xml"]
    started = time.monotonic()
    with open(run_dir / "dragon.log", "w", encoding="utf-8") as log:
        code = subprocess.run(command, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT,
                              timeout=RUN_TIMEOUT_S).returncode
    seconds = time.monotonic() - started
    txt = run_dir / "output" / f"{spec['name']}.txt"
    if code != 0 or not txt.is_file():
        tail = (run_dir / "dragon.log").read_text(encoding="utf-8", errors="replace")[-600:]
        raise RuntimeError(f"DRAGON2 exit {code}, output {'present' if txt.is_file() else 'missing'}: {tail}")
    args = type("RunArgs", (), {"dragon": Path(binary).resolve(),
                                "program_version": os.environ.get("HEP_DRAGON2_VERSION", "unknown")})
    rec = dragon2_run.record(args, checked, run_dir, inputs, command, code,
                             {f"output/{txt.name}": dragon2_run.sha256(txt)}, None, seconds)
    return txt, rec


def prediction(obs: dict, edges: list[float], values: list[float], point: dict, spec: dict) -> dict:
    var_name, unit = VARIABLE[obs["axis"]]
    num, den, species = OBSERVABLES[obs["id"]]
    return {
        "observable": {
            "quantity": "ratio",
            "process": f"unmodulated local interstellar {obs['id']} from a DRAGON2 run: ratio of bin integrals of "
                       f"{'+'.join(num)} over {'+'.join(den)} (columns times A)",
            "species": [{"name": s} for s in species],
            "variables": [{"name": var_name, "unit": unit, "edges": edges}],
            "phase_space": {"definition": "DRAGON2 local spectrum at the observer position (8.3, 0, 0) kpc, before "
                                          "solar modulation", "fiducial": False},
            "level": "crsr:local-interstellar",
            "normalization": {"kind": "exposure", "value": "not-applicable",
                              "convention": "ratio of two bin-integrated fluxes; the normalization cancels"},
            "bin_semantics": "bin-averaged",
            "unit": "1",
            "conventions": {
                "energy_variable": f"{var_name} in {unit}: the ratio of the bin-integrated fluxes (r3 P2), isotopes "
                                   "summed at equal " + ("rigidity" if obs["axis"] == "rigidity" else "E/n") + " (P3)",
                "frame": "Galactic rest frame (interstellar gas at rest)",
                "mass_approximation": "DRAGON2 per-nucleon kinematics with the nucleon mass 0.938 GeV; rigidity "
                                      "(A/|Z|) times the momentum per nucleon",
            },
            "validity_range": {"variable": var_name, "min": edges[0], "max": edges[-1], "unit": unit},
        },
        "derivation_status": "numerical-evidence",
        "parameter_point": {**{k: float(v) for k, v in point.items()}, "dragon2_run": spec["name"],
                            "transport_substitutes": list(spec.get("substitutes", []))},
        "representation": "numerical",
        "values": {"edges": edges, "values": values, "unit": "1"},
        "uncertainties": [],
        "allowed_transformations": ["solar modulation per isotope (outside this provider)",
                                    "rebin (recompute the bin integrals from the run output; never merge ratios)"],
    }


def evaluate_point(request: dict, point: dict, context: dict) -> dict:
    transport = transport_for(request, point)
    z_range, ekn_range = run_ranges(request["observables"])
    name = "p" + point_hash(request.get("transport"), request["provider"], request["provider_version"], point)[:16]
    spec = dragon2_run.spec_from_transport(transport, name, ILLUSTRATIVE_CHANNELS_MB, z_range=z_range,
                                           ekn_range_gev=ekn_range)
    keep = os.environ.get("HEP_DRAGON2_RUN_DIR")
    with tempfile.TemporaryDirectory(prefix="dragon2-provider-") as scratch:
        run_dir = Path(keep) / name if keep else Path(scratch) / name
        txt, rec = run_dragon2(spec, run_dir)
        if keep:
            (run_dir / f"{name}.computational-run.json").write_text(json.dumps(rec, indent=1) + "\n",
                                                                     encoding="utf-8")
            (run_dir / f"{name}.spec.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
        energies, cols = reader.read_output(txt)
        predictions = []
        for obs in request["observables"]:
            num, den, _ = OBSERVABLES[obs["id"]]
            edges = [float(obs["bins"][0][0])] + [float(hi) for _, hi in obs["bins"]]
            values = reader.ratio_of_bin_integrals(energies, cols, num, den, edges, obs["axis"])
            predictions.append(prediction(obs, edges, values, point, spec))
    out = {"labels": ["synthetic", "unvalidated"], "numerical_tolerance": NUMERICAL_TOLERANCE,
           "computational_run_ref": rec["artifact_id"] if keep else None}
    if "lis" in context["want"]:
        out["predictions"] = predictions
    return out


def main(argv=None) -> int:
    return provider_main(declaration(), evaluate_point, argv, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    sys.exit(main())
