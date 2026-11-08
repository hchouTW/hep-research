#!/usr/bin/env python3
"""Light-collection efficiency maps from Geant4 (g4sim plan, Section 10.4, S7): plan a mapping run, then build the map from it.

Usage: g4sim_efficiency_map.py plan --detector D.json --template NAME --material M --component K --scorer NAME --photons N --out REQUEST.json
       g4sim_efficiency_map.py build --work RUN_DIR --template NAME --material M --component K --segmentation SEG.json --out MAP.json

plan writes the simulation request of a mapping run: one optical photon per event, of the component's emission spectrum (64 energies,
weighted by the interpolated spectrum), uniform over the template's volume and isotropic, with a photon_detected scorer of the given name
on the templates its select names (the run card turns G4OpticalPhysics on). Run it with g4sim_run.py simulate and as many events as photons.
build reads that run's ir.json, primaries.csv and photons.csv, bins every emitted photon by the production segmentation, and writes an
efficiency-map/1 with the materials' and surfaces' hashes and, for along_axis, the transverse-uniformity check. The template must be placed
once, with no rotation along its chain, so its volume is a box of the world. Prints JSON with a status key. Exit 0 ok, 1 the map fails its
check, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import g4sim_simulate as simulate_new  # noqa: E402
from core.canonical import canonical_sha256  # noqa: E402
from core.simulation import efficiency_map  # noqa: E402

SPECTRUM_POINTS = 64
EV_TO_MEV = 1e-6


class InputError(ValueError):
    pass


def component_spectrum(material: dict, component: int) -> dict:
    components = material.get("scintillation", {}).get("components") or []
    if not 1 <= component <= len(components):
        raise InputError(f"the material has {len(components)} scintillation components, not a component {component}")
    return components[component - 1]["spectrum"]


def spectrum_energies(spectrum: dict) -> tuple[list, list]:
    """64 energies across the spectrum, each weighted by the linearly interpolated spectrum: the discrete source the request can hold."""
    energies = [float(value) for value in spectrum["energy_eV"]]
    values = [float(value) for value in spectrum["value"]]
    points = [energies[0] + (energies[-1] - energies[0]) * (i + 0.5) / SPECTRUM_POINTS for i in range(SPECTRUM_POINTS)]

    def at(energy):
        for (e0, v0), (e1, v1) in zip(zip(energies, values), zip(energies[1:], values[1:])):
            if e0 <= energy <= e1:
                return v0 + (v1 - v0) * (energy - e0) / (e1 - e0)
        return 0.0

    weights = [at(point) for point in points]
    total = sum(weights)
    if total <= 0:
        raise InputError("the emission spectrum is zero everywhere")
    return points, [weight / total for weight in weights]


def template_box(ir: dict, template: str) -> tuple[list, list]:
    """The world centre and half sizes of a template placed once with no rotation on its chain."""
    chain = simulate_new._chain(ir, template)
    if any(placement["rotation"] for placement in chain):
        raise InputError(f"template {template} is rotated on its way to the world; a mapping run needs it as a box of the world")
    node = ir["physical"]["templates"][template]
    if node["shape"] != "box":
        raise InputError(f"template {template} is a {node['shape']}; a mapping run maps a box")
    centre = simulate_new._to_world(ir, template, [0.0, 0.0, 0.0])
    return centre, [float(value) for value in node["half_mm"]]


def plan(args) -> dict:
    from contracts import geometry
    checked = geometry.check_file(args.detector)
    if checked["status"] != "ok":
        return {"status": "rejected", "findings": checked["findings"]}
    ir = checked["ir"]
    material = ir["physical"]["materials"].get(args.material)
    if material is None:
        raise InputError(f"{args.material} is not a declared material")
    spectrum = component_spectrum(material, args.component)
    energies, weights = spectrum_energies(spectrum)
    centre, half = template_box(ir, args.template)
    request = {"schema": "simulation-request/1",
               "source": {"density": "analytic", "particle": "opticalphoton",
                          "energy": {"list": {"energies_MeV": [repr(energy * EV_TO_MEV) for energy in energies], "probabilities": [repr(weight) for weight in weights]}},
                          "position": {"box_uniform": {"frame": "world", "centre_mm": [repr(value) for value in centre], "size_mm": [repr(2 * value) for value in half]}},
                          "direction": {"isotropic": {}}},
               "scorers": [{"name": args.scorer, "readout": "none", "select": json.loads(args.select), "quantity": "photon_detected"}]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(request, indent=1) + "\n", encoding="utf-8")
    return {"status": "ok", "request": str(args.out), "events": args.photons, "note": f"run g4sim_run.py simulate with run.events = {args.photons}"}


def _csv(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.reader(handle) if row and row[0] != "event" and not row[0].startswith("#")]


def build(args) -> dict:
    work = args.work
    ir = json.loads((work / "ir.json").read_text(encoding="utf-8"))
    summary = json.loads((work / "summary.json").read_text(encoding="utf-8"))
    material = ir["physical"]["materials"].get(args.material)
    if material is None:
        raise InputError(f"{args.material} is not a material of the run's IR")
    spectrum = component_spectrum(material, args.component)
    centre, half = template_box(ir, args.template)
    emitted = {}
    for row in _csv(work / "primaries.csv"):
        point = [float(value) for value in row[2:5]]
        emitted[int(row[0])] = simulate_new.to_local(ir, args.template, point)
    detected = [(int(row[0]), f"{row[1]}/{row[2]}", float(row[4])) for row in _csv(work / "photons.csv")]
    channels = sorted({channel for _, channel, _ in detected})
    used = {node["material"] for node in ir["physical"]["templates"].values()}
    hashes = {"materials_sha256": canonical_sha256({name: value for name, value in ir["physical"]["materials"].items() if name in used}),
              "surfaces_sha256": canonical_sha256(ir["physical"].get("optical_surfaces", {})),
              "mapping_run_id": summary.get("request_id", "")}
    segmentation = json.loads(args.segmentation.read_text(encoding="utf-8"))
    document = efficiency_map.build(template=args.template, component=args.component, spectrum=spectrum, segmentation=segmentation, half_mm=half,
                                    channels=channels, emitted=emitted, detected=detected, hashes=hashes)
    document["source_of_facts"] = f"mapping run {hashes['mapping_run_id']}"
    uniformity = efficiency_map.transverse_uniformity(document)
    document["form"]["uniformity"] = uniformity
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    status = "failed" if uniformity["status"] in ("failed", "insufficient") else "ok"
    return {"status": status, "map": str(args.out), "bins": len(document["form"]["bins"]), "channels": channels, "uniformity": uniformity["status"],
            "emitted": len(emitted), "detected": len(detected), "map_sha256": efficiency_map.map_sha256(document)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    first = commands.add_parser("plan")
    first.add_argument("--detector", type=Path, required=True)
    first.add_argument("--select", default='{"tags": ["sensor"]}', help="the photon_detected scorer's select, as JSON")
    second = commands.add_parser("build")
    second.add_argument("--work", type=Path, required=True)
    second.add_argument("--segmentation", type=Path, required=True, help="the production scorer's segmentation, as JSON")
    for command in (first, second):
        command.add_argument("--template", required=True)
        command.add_argument("--material", required=True)
        command.add_argument("--component", type=int, default=1)
        command.add_argument("--out", type=Path, required=True)
    first.add_argument("--scorer", default="detected")
    first.add_argument("--photons", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        result = plan(args) if args.command == "plan" else build(args)
    except (InputError, efficiency_map.MapError, OSError, json.JSONDecodeError, KeyError, ValueError) as err:
        result = {"status": "rejected", "message": str(err)}
    print(json.dumps(result))
    return {"ok": 0, "failed": 1}.get(result["status"], 2)


if __name__ == "__main__":
    sys.exit(main())
