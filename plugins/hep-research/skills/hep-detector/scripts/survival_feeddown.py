#!/usr/bin/env python3
"""Survival probability of nuclei crossing detector material, and first-order fragmentation feed-down (D4).

Purpose: the two nuclear-interaction corrections of a nuclei measurement in a detector (see
<plugin root>/skills/hep-detector/references/nuclear-interactions-in-detector-material.md): a species loses the
fraction 1 - P that interacts in the material above the measuring layers, and a heavier species that fragments there
can be reconstructed as a lighter one (feed-down).

Method:
- interaction length per layer: 1/lambda = sum_i w_i N_A sigma_i / A_i (mass fractions w_i, target mass numbers A_i
  in g/mol, inelastic cross sections sigma_i per nucleus; N_A from core/constants, CODATA 2022), so a pure layer has
  lambda = A / (N_A sigma);
- survival over the layers: P = exp(-sum_k x_k / lambda_k) (grammage x_k in g/cm2); the flux correction is 1/P;
- cross-section scale: with every sigma of a species scaled by (1 + s), dP/ds = P ln P at s = 0; --scale-nuisance S
  reports P at s = -S and +S;
- first-order feed-down into a lighter species: N_feed = N_heavy (1 - P_heavy) f(heavy -> light), with the
  fragmentation fraction f from the table and N_heavy the number arriving above the material (no re-interaction of
  the fragment, no second-step fragmentation); dN_feed/ds_heavy = -N_heavy f P_heavy ln P_heavy.
Assumptions: straight-through crossing (the grammage is along the track), first-order feed-down, one energy point
(the cross sections are those at the energy of interest). There are no built-in cross sections; the table must name
its source, or the output is labelled unvalidated whatever --status says.

Input (JSON):
  --layers   {"layers": [{"name", "grammage_g_cm2", "composition": [{"target", "A", "mass_fraction"}]}]}
  --species  {"species": [{"name", "arriving"?}]}   (arriving: count above the material, for feed-down)
  --xs       {"source": TEXT, "unit": "mb"|"b"|"cm2", "inelastic": {SPECIES: {TARGET: sigma}},
              "fragmentation_fraction"?: {HEAVY: {LIGHT: f}}}
Output JSON: status (ok, rejected), status_label, inputs, defaults_used, warnings, species (per layer lambda,
survival_probability, correction_factor, dP_dscale, scale_variation), feeddown (from, to, fraction, events,
dN_dscale), and recipe_steps: the corrections as recipe steps with the correction keys of
measurement:correction-keys-v1 (effects survival and fragmentation_feeddown of contracts/vocab/effects.json).
Exit codes: 0 ok; 2 bad input (missing file, species or cross section; mass fractions that do not sum to 1;
non-finite or negative numbers). Standard library only.
Usage: survival_feeddown.py compute --layers L.json --species S.json --xs XS.json [--scale-nuisance S]
       [--stage top-of-instrument] [--status LABEL]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(PLUGIN))
from core import constants  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
UNITS = {"mb": "mb", "b": "b", "cm2": "cm2"}
FRACTION_TOL = 1e-9


class InputError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _num(x, where: str, positive: bool = False) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise InputError(f"{where}: {x!r} is not a finite number")
    if x < 0 or (positive and x == 0):
        raise InputError(f"{where}: must be {'> 0' if positive else '>= 0'}")
    return float(x)


def _load(path: Path, key: str) -> tuple[dict, str]:
    try:
        raw = Path(path).read_bytes()
        doc = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read {path}: {exc}") from None
    if not isinstance(doc, dict) or key not in doc:
        raise InputError(f"{path}: expected a JSON object with '{key}'")
    return doc, hashlib.sha256(raw).hexdigest()


def inverse_lengths(layers: list, sigma_cm2: dict, species: str) -> list[float]:
    """1/lambda (cm2/g) per layer for one species."""
    na = constants.constant("avogadro_constant").value
    out = []
    for k, layer in enumerate(layers):
        where = f"layers[{k}]"
        comp = layer.get("composition")
        if not isinstance(comp, list) or not comp:
            raise InputError(f"{where}: composition must be a non-empty list")
        total = sum(_num(c.get("mass_fraction"), f"{where}.mass_fraction") for c in comp)
        if abs(total - 1.0) > FRACTION_TOL:
            raise InputError(f"{where}: mass fractions sum to {total}, not 1")
        inv = 0.0
        for c in comp:
            target = c.get("target")
            if target not in sigma_cm2:
                raise InputError(f"no inelastic cross section for {species} on {target!r}")
            inv += c["mass_fraction"] * na * sigma_cm2[target] / _num(c.get("A"), f"{where}.A", positive=True)
        out.append(inv)
    return out


def compute(layers_doc: dict, species_doc: dict, xs_doc: dict, scale: float | None) -> tuple[dict, list[str]]:
    warnings = []
    unit = xs_doc.get("unit")
    if unit not in UNITS:
        raise InputError(f"xs.unit must be one of {sorted(UNITS)}")
    to_cm2 = constants.convert(1.0, unit, "cm2")
    layers = layers_doc["layers"]
    if not isinstance(layers, list) or not layers:
        raise InputError("layers must be a non-empty list")
    grammage = [_num(layer.get("grammage_g_cm2"), f"layers[{k}].grammage_g_cm2") for k, layer in enumerate(layers)]
    inel = xs_doc.get("inelastic")
    if not isinstance(inel, dict):
        raise InputError("xs.inelastic must be an object {species: {target: sigma}}")
    rows, prob = [], {}
    for s in species_doc["species"]:
        name = s.get("name") if isinstance(s, dict) else None
        if name not in inel:
            raise InputError(f"no inelastic cross sections for species {name!r}")
        sig = {t: _num(v, f"xs.inelastic.{name}.{t}") * to_cm2 for t, v in inel[name].items()}
        inv = inverse_lengths(layers, sig, name)
        tau = math.fsum(x * i for x, i in zip(grammage, inv))
        if not math.isfinite(tau) or tau > 700:
            raise InputError(f"{name}: sum x/lambda = {tau} makes the survival probability underflow; check the units")
        if tau == 0:
            raise InputError(f"{name}: zero material or zero cross sections: nothing to correct")
        p = math.exp(-tau)
        prob[name] = p
        row = {"species": name, "layers": [{"name": layer.get("name"), "grammage_g_cm2": x,
                                             "interaction_length_g_cm2": (1.0 / i if i > 0 else None)}
                                            for layer, x, i in zip(layers, grammage, inv)],
               "survival_probability": p, "correction_factor": 1.0 / p, "dP_dscale": p * math.log(p)}
        if scale is not None:
            row["scale_variation"] = {"s": scale, "down": math.exp(-tau * (1 - scale)), "up": math.exp(-tau * (1 + scale))}
        rows.append(row)
    feed = []
    arriving = {s["name"]: s.get("arriving") for s in species_doc["species"]}
    for heavy, targets in (xs_doc.get("fragmentation_fraction") or {}).items():
        for light, f in targets.items():
            f = _num(f, f"xs.fragmentation_fraction.{heavy}.{light}")
            if f > 1:
                raise InputError(f"fragmentation fraction {heavy} -> {light} is above 1")
            if heavy not in prob or light not in prob:
                warnings.append(f"fragmentation {heavy} -> {light} skipped: both species must be listed")
                continue
            n = arriving.get(heavy)
            if n is None:
                warnings.append(f"feed-down {heavy} -> {light}: no 'arriving' count for {heavy}; only the probability")
            p = prob[heavy]
            entry = {"from": heavy, "to": light, "fraction": f, "probability_per_arriving": (1 - p) * f,
                     "events": None if n is None else _num(n, f"species.{heavy}.arriving") * (1 - p) * f,
                     "dN_dscale": None if n is None else -n * f * p * math.log(p)}
            feed.append(entry)
    return {"species": rows, "feeddown": feed}, warnings


def recipe_steps(result: dict, digest: str, stage: str) -> list[dict]:
    steps = []
    for fd in result["feeddown"]:
        steps.append({"step_id": f"feeddown-{fd['from']}-to-{fd['to']}".lower(), "operator": "subtract_background",
                      "effect_keys": {"fragmentation_feeddown": {"target_scope": f"species:{fd['to']}",
                                                                 "calibration_digest": digest, "variation_id": "nominal",
                                                                 "stage": stage}}})
    for row in result["species"]:
        steps.append({"step_id": f"survival-{row['species']}".lower(), "operator": "divide_effective_exposure",
                      "effect_keys": {"survival": {"target_scope": f"species:{row['species']}",
                                                   "calibration_digest": digest, "variation_id": "nominal",
                                                   "stage": stage}}})
    return steps


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("compute", help="survival probabilities and feed-down")
    p.add_argument("--layers", type=Path, required=True)
    p.add_argument("--species", type=Path, required=True)
    p.add_argument("--xs", type=Path, required=True)
    p.add_argument("--scale-nuisance", type=float, dest="scale_nuisance")
    p.add_argument("--stage", default="top-of-instrument", help="correction-key stage (default top-of-instrument)")
    add_status_argument(p)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    defaults = [k for k in ("stage", "status") if f"--{k}" not in given]
    try:
        layers, _ = _load(args.layers, "layers")
        species, _ = _load(args.species, "species")
        xs, digest = _load(args.xs, "inelastic")
        scale = None if args.scale_nuisance is None else _num(args.scale_nuisance, "--scale-nuisance")
        if scale is not None and scale >= 1:
            raise InputError("--scale-nuisance must be below 1")
        result, warnings = compute(layers, species, xs, scale)
    except InputError as exc:
        print(json.dumps({"status": "rejected", "status_label": args.status, "inputs": inputs, "error": str(exc)},
                         indent=1))
        return exit_code("rejected")
    label = args.status
    source = xs.get("source")
    if not (isinstance(source, str) and source.strip()):
        warnings.append("the cross-section table names no source: output labelled unvalidated")
        label = "unvalidated"
    out = {"status": "ok", "status_label": label, "inputs": inputs, "defaults_used": defaults, "warnings": warnings,
           "label": LABEL, "xs_source": source, "xs_sha256": digest,
           "method": "P = exp(-sum x_k / lambda_k), 1/lambda = sum_i w_i N_A sigma_i / A_i; first-order feed-down "
                     "N_heavy (1 - P_heavy) f", **result,
           "recipe_steps": recipe_steps(result, digest, args.stage),
           "effects": {"survival": "contracts/vocab/effects.json survival",
                       "fragmentation_feeddown": "contracts/vocab/effects.json fragmentation_feeddown"}}
    print(json.dumps(out, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())
