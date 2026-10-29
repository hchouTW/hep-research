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
the transport's zone), and (work package F1):
- R_break_gv and delta_below: the transport's one low break (its s and s_convention stay); a point naming them with no
  low break, or with more than one, fails (provider-error). A point that sets delta keeps each high break's slope
  change Deltabreak = delta - delta_above of the transport block (USINE's shipped K formula and the initialisation
  files of Génolini et al. 2019 parameterize the high break by Deltabreak), so the run's delta_above is the point's
  delta minus that change; recorded in transport_substitutes.
- phi_<period>_gv: the force-field modulation potential of the observable's data period; USINE modulates each isotope
  (SolMod0DFF, Phi = |Z| phi / A, before the reader forms ratios, r3 P4) and the predictions are top-of-atmosphere
  values. At most one phi per point (one period per request); without it the values are unmodulated. This is the
  declared exception to the protocol's "providers never modulate" (contracts 3.15.0: the declaration's modulation
  block in adapter.json, contracts/schemas/cr_provider.json): the per-isotope modulation is USINE's own, the code of
  the reproduced analysis, and passed the conformance gate (tools/provider_registry.py --conformance usine, through
  isotope_tables below: USINE's SolMod0DFF output equals the plugin's force-field tool applied to USINE's own isotopic
  LIS within the declared tolerance); recorded in every modulated prediction.
- xs_norm_<proj>_<target>_<frag>, xs_slope_<proj>_<target>_<frag>, xs_threshold_<proj>_<target>_<frag>_gev (for
  example xs_norm_12C_H_11B): one production channel of USINE's own cross sections times norm, and below the threshold
  (E_k/n in GeV/n) times (E_k/n / threshold)^slope (USINE's fit-mode Norm, SlopeLE and EThresh; usine_translate.py
  production modifiers); the three are given together or not at all. Cross sections: the ILLUSTRATIVE sets of theory:cr-secondary-ratio
(usine_translate.ILLUSTRATIVE_SETS), or USINE's own cross-section files with data-normalised source abundances
('usine:<file>' names, read in place from HEP_USINE_DATA, never copied; work package B1X); a transport naming another
set fails the point with provider-error, never replaced. What USINE cannot express exactly is listed in each prediction's parameter_point.transport_substitutes;
what it cannot express at all fails the point. An observable whose isotopes are not in the network (Be/B or 10Be/9Be
with the element-level set) fails the point.
Grid: the translator's (20 E_k/n nodes per decade from below 0.8 times the lowest to above 1.25 times the highest E_k/n
the bins need; 100 Fourier-Bessel terms in the 2D model). The run is located through HEP_USINE_BIN and
HEP_USINE_DATA; without them a point fails with provider-error (R4), nothing falls back.

Values: the ratio of the bin-integrated summed numerator and denominator (r3 P2), isotopes summed at equal rigidity
on the axis rigidity and at equal E/n on the axis ekn (P3); fluxes per E_k/n from USINE's tables (P11). Unmodulated
unless the point carries phi_<period>_gv (above). Not decomposable. Labels: synthetic and unvalidated with the ILLUSTRATIVE cross sections,
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
import re
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
                "injection": [{"species_group": "all primaries", "gamma": 2.3, "breaks": [],
                               "spectrum_variable": "kinetic_energy_per_nucleon"}],
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


LOW_BREAK_TARGETS = ("R_break_gv", "delta_below")
PHI_NAME = re.compile(r"phi_([A-Za-z0-9]+(?:_[A-Za-z0-9]+)*)_gv")
XS_NAME = re.compile(r"xs_(norm|slope|threshold)_(\d+[A-Z][a-z]?)_(H|He)_(\d+[A-Z][a-z]?)(_gev)?")
XS_KEYS = {"norm": "norm", "slope": "slope_le", "threshold": "threshold_ekn_gev"}


class PointError(ValueError):
    """A point the provider cannot turn into one USINE run (provider-error)."""


def run_options(point: dict) -> tuple[float, list[dict]]:
    """(phi in GV, production modifiers) carried by the point's phi_<period>_gv and xs_* parameters."""
    phis = [name for name in point if PHI_NAME.fullmatch(name)]
    if len(phis) > 1:
        raise PointError(f"one modulation period per request, the point carries {sorted(phis)}")
    channels: dict = {}
    for name, value in point.items():
        m = XS_NAME.fullmatch(name)
        if not m:
            continue
        if (m.group(1) == "threshold") != bool(m.group(5)):
            raise PointError(f"{name}: the threshold is xs_threshold_<channel>_gev, norm and slope have no unit suffix")
        channel = f"{m.group(2)}+{m.group(3)}->{m.group(4)}"
        channels.setdefault(channel, {"channel": channel})[XS_KEYS[m.group(1)]] = float(value)
    mods = []
    for channel, mod in sorted(channels.items()):
        missing = [k for k in XS_KEYS.values() if k not in mod]
        if missing:
            raise PointError(f"production channel {channel}: give xs_norm, xs_slope and xs_threshold together "
                             f"(missing {missing}); nothing is defaulted")
        mods.append(mod)
    return (float(point[phis[0]]) if phis else 0.0), mods


def transport_for(request: dict, point: dict) -> tuple[dict, list[str]]:
    """The request's transport (or DEFAULT_TRANSPORT) with the point's transport values written into their blocks,
    and the notes of what the point changed beyond a plain value (for transport_substitutes)."""
    transport = copy.deepcopy(request.get("transport") or DEFAULT_TRANSPORT)
    notes: list[str] = []
    breaks = transport.get("diffusion", {}).get("breaks") or []
    if "delta" in point:
        for brk in breaks:
            if isinstance(brk, dict) and brk.get("kind") == "high" and "delta_above" in brk:
                change = float(transport["diffusion"]["delta"]) - float(brk["delta_above"])
                brk["delta_above"] = float(point["delta"]) - change
                notes.append(f"high break at {brk.get('R_break_gv')} GV: slope change Deltabreak = {change:.10g} of the "
                             f"transport block kept, delta_above = point delta - Deltabreak = {brk['delta_above']:.10g}")
    for name, value in point.items():
        if name in POINT_TARGETS:
            block, key = POINT_TARGETS[name]
            transport.setdefault(block, {})[key] = float(value)
        elif name in LOW_BREAK_TARGETS:
            lows = [b for b in breaks if isinstance(b, dict) and b.get("kind") == "low"]
            if len(lows) != 1:
                raise PointError(f"{name}: the transport block has {len(lows)} low breaks, the point can set only one")
            lows[0][name] = float(value)
        elif not (PHI_NAME.fullmatch(name) or XS_NAME.fullmatch(name)):
            raise PointError(f"parameter {name!r} is not read by this provider")
    return transport, notes


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


def run_point(transport: dict, name: str, observables: list[dict], run_dir: Path, phi_gv: float = 0.0,
              modifiers: list | None = None) -> tuple[dict, dict, dict]:
    """Translate and run one point; (spec, run result, isotope tables, modulated at phi_gv). Raises on any failure
    (R4)."""
    binary, data_path = os.environ.get("HEP_USINE_BIN"), os.environ.get("HEP_USINE_DATA")
    if not (binary and Path(binary).is_file() and os.access(binary, os.X_OK)):
        raise RuntimeError("USINE executable not found: set HEP_USINE_BIN (missing tool, R4)")
    if not (data_path and Path(data_path).is_dir()):
        raise RuntimeError("USINE inputs folder not found: set HEP_USINE_DATA (missing tool, R4)")
    probe = translator.translate(transport, name, (1.0, 10.0))
    lo, hi = ekn_range(observables, probe["species"])
    if phi_gv:   # the force field reads the LIS at E_k/n + |Z| phi / A (at most phi per nucleon): cover it
        hi += phi_gv
    spec = translator.translate(transport, name, (lo, hi), phi_gv=phi_gv, production_modifiers=modifiers)
    result = translator.run_usine(spec, run_dir, Path(binary), Path(data_path), RUN_TIMEOUT_S)
    if not result["ok"]:
        raise RuntimeError(f"USINE run failed (exit {result['exit_status']}): {result['log_tail'][-400:]}")
    return spec, result, reader.read_run(Path(run_dir) / "out", spec["model"], spec["species"], phi_gv)


def evaluate_point(request: dict, point: dict, context: dict) -> dict:
    transport, notes = transport_for(request, point)
    phi_gv, modifiers = run_options(point)
    name = "p" + point_hash(request.get("transport"), request["provider"], request["provider_version"], point)[:16]
    keep = os.environ.get("HEP_USINE_RUN_DIR")
    with tempfile.TemporaryDirectory(prefix="usine-provider-") as scratch:
        run_dir = Path(keep) / name if keep else Path(scratch) / name
        spec, result, tables = run_point(transport, name, request["observables"], run_dir, phi_gv, modifiers)
        spec["substitutes"] = notes + spec["substitutes"]
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


def isotope_tables(request: dict, point: dict) -> dict:
    """Conformance hook of the declared modulation (contracts 3.15.0; tools/provider_registry.py --conformance): one
    USINE run at the point, as evaluate_point makes it, and the per-isotope tables of the requested observables:
    {"phi_gv": phi (0 without a phi_<period>_gv), "isotopes": {nuclide: {"charge", "mass_number", "ekn", "flux"}},
    "substitutes": [...]}. With a phi the tables are USINE's SolMod0DFF output (first column the top-of-atmosphere
    E_k/n), without one the local interstellar fluxes. The run lives in a temporary folder."""
    transport, notes = transport_for(request, point)
    phi_gv, modifiers = run_options(point)
    name = "c" + point_hash(request.get("transport"), request["provider"], request["provider_version"], point)[:16]
    with tempfile.TemporaryDirectory(prefix="usine-conformance-") as scratch:
        spec, _, tables = run_point(transport, name, request["observables"], Path(scratch) / name, phi_gv, modifiers)
    isotopes = {}
    for obs in request["observables"]:
        num, den = reader.present(obs["id"], spec["species"])
        for nuclide in num + den:
            z, a = reader.charge_and_mass(nuclide)
            isotopes[nuclide] = {"charge": z, "mass_number": a, "ekn": list(tables[nuclide][0]),
                                 "flux": list(tables[nuclide][1])}
    return {"phi_gv": phi_gv, "isotopes": isotopes, "substitutes": notes + list(spec["substitutes"])}


def main(argv=None) -> int:
    return provider_main(declaration(), evaluate_point, argv, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    sys.exit(main())
