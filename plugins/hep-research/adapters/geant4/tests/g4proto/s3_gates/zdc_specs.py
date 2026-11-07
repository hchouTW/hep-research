#!/usr/bin/env python3
"""Express a ZDC prototype of the user's flat YAML as detector-spec/1, simulation-request/1 and g4sim-run/1 (g4sim plan, Section 19.2 S3; the YAML governs over Section 6.6).

Usage: zdc_specs.py GEOMETRY.yaml SAMPLE.yaml FOLDER [--events N] [--seed S] [--no-spread]   Prints JSON with a status key. Exit 0 ok, 2 bad input.
Decimal arithmetic throughout, so a position here is exactly what zdcsim computes before it rounds to a double.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 34
WORLD_SIZE_MM = ["3000", "3000", "9000"]
BEAM_MONITOR_NAMES = ("bm3_z_mm", "bm4_z_mm", "bm5_z_mm")
BEAM_MONITOR_DEFAULTS = ("-3000", "-2000", "-1000")
# FR4 of zdcsim, by mass: 60% G4_SILICON_DIOXIDE and 40% epoxy C21 H25 Cl O5; mass fractions as Geant4 reads them, written by volume_tree.py's material check
EPOXY_ATOMS = {"C": 21, "H": 25, "Cl": 1, "O": 5}


def text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def read_flat(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0]
        if ":" in line:
            key, value = line.split(":", 1)
            if key.strip() and value.strip():
                out[key.strip()] = value.strip().strip("\"'")
    return out


def spec_of(config: dict, fr4_fractions: dict) -> dict:
    def number(key: str, default: str) -> Decimal:
        return Decimal(config.get(key, default))
    count = int(number("n_crystals", "8"))
    size_x, size_y, length = number("crystal_x_mm", "20"), number("crystal_y_mm", "20"), number("crystal_z_mm", "53")
    wrap = number("wrap_um", "65") / 1000
    gap = number("gap_mm", "0.2")
    pitch_x, pitch_y = size_x + 2 * wrap + gap, size_y + 2 * wrap + gap
    world = []
    templates = {"crystal": {"solid": {"box": {"size_mm": [text(size_x), text(size_y), text(length)]}}, "material": "G4_PbWO4", "tags": ["active", "crystal"], "region": "CrystalRegion",
                             "modifiers": [{"shell": {"material": "G4_MYLAR", "thickness_mm": text(wrap), "faces": ["sides", "front"]}}]}}
    world.append({"template": "crystal", "placement": {"grid": {"n": [count, count], "pitch_mm": [text(pitch_x), text(pitch_y)], "centre_mm": ["0", "0", text((length - wrap) / 2)], "index": ["ix", "iy"]}}})
    columns, rows = int(number("sipm_nx", "0")), int(number("sipm_ny", "0"))
    materials = {}
    if columns > 0 and rows > 0:
        side, thick = number("sipm_size_mm", "3"), number("sipm_thick_mm", "0.5")
        step_x, step_y = number("sipm_pitch_x_mm", "5"), number("sipm_pitch_y_mm", "5")
        board = number("pcb_mm", "1.6")
        templates["sipm"] = {"solid": {"box": {"size_mm": [text(side), text(side), text(thick)]}}, "material": "G4_Si", "tags": ["readout"]}
        first_x, first_y = -(Decimal(count) - 1) / 2 * pitch_x, -(Decimal(count) - 1) / 2 * pitch_y
        positions = []
        for iy in range(count):
            for ix in range(count):
                for sy in range(rows):
                    for sx in range(columns):
                        positions.append([text(first_x + ix * pitch_x + (sx - (Decimal(columns) - 1) / 2) * step_x), text(first_y + iy * pitch_y + (sy - (Decimal(rows) - 1) / 2) * step_y), text(length + thick / 2)])
        world.append({"template": "sipm", "placement": {"explicit": {"positions_mm": positions}}})
        templates["pcb"] = {"solid": {"box": {"size_mm": [text(count * pitch_x), text(count * pitch_y), text(board)]}}, "material": "FR4", "tags": ["passive"]}
        world.append({"template": "pcb", "placement": {"single": {"centre_mm": ["0", "0", text(length + thick + board / 2)]}}})
        materials["FR4"] = {"composition": fr4_fractions, "density_g_cm3": "1.85", "facts": "assumed"}
    if config.get("upstream_enable", "0") not in ("0", ""):
        side, thick = number("bm_size_mm", "50"), number("bm_plane_thick_mm", "1")
        templates["beam_monitor"] = {"solid": {"box": {"size_mm": [text(side), text(side), text(thick)]}}, "material": "G4_PLASTIC_SC_VINYLTOLUENE", "tags": ["passive"]}
        planes = [["0", "0", text(number(name, default) + plane * thick)] for name, default in zip(BEAM_MONITOR_NAMES, BEAM_MONITOR_DEFAULTS) for plane in range(2)]
        world.append({"template": "beam_monitor", "placement": {"explicit": {"positions_mm": planes}}})
        if config.get("window_enable", "1") not in ("0", ""):
            foil = number("window_um", "100") / 1000
            templates["window"] = {"solid": {"box": {"size_mm": [text(side), text(side), text(foil)]}}, "material": "G4_MYLAR", "tags": ["passive"]}
            world.append({"template": "window", "placement": {"single": {"centre_mm": ["0", "0", text(number("window_z_mm", "-500"))]}}})
    gun = number("gun_z_mm", "-4000")
    return {"schema": "detector-spec/1", "params": {}, "materials": materials, "templates": templates, "world": {"material": "G4_AIR", "size_mm": WORLD_SIZE_MM, "children": world},
            "frames": {"gun": {"in": "world", "origin_mm": ["0", "0", text(gun)]}}, "readout": {"ecal": {"fields": {"ix": 3, "iy": 3}}}}


def request_of(config: dict, spread: bool) -> dict:
    count = int(Decimal(config.get("n_crystals", "8")))
    wrap = Decimal(config.get("wrap_um", "65")) / 1000
    gap = Decimal(config.get("gap_mm", "0.2"))
    pitch_x = Decimal(config.get("crystal_x_mm", "20")) + 2 * wrap + gap
    pitch_y = Decimal(config.get("crystal_y_mm", "20")) + 2 * wrap + gap
    aim_x = (Decimal(config.get("target_ix", "0")) - (Decimal(count) - 1) / 2) * pitch_x if "target_ix" in config else Decimal(0)
    aim_y = (Decimal(config.get("target_iy", "0")) - (Decimal(count) - 1) / 2) * pitch_y if "target_iy" in config else Decimal(0)
    energy = config.get("energy_mev", "500")
    if spread and Decimal(config.get("momentum_spread", "0")) != 0:
        raise ValueError("zdcsim spreads momentum; run with --no-spread, which the same setting in zdcsim's sample makes equal")
    sigma = config.get("spot_sigma_mm", "0")
    position = {"gaussian_spot": {"frame": "gun", "centre_mm": [text(aim_x), text(aim_y), "0"], "sigma_mm": [sigma, sigma]}} if Decimal(sigma) > 0 else {"point": {"frame": "gun", "centre_mm": [text(aim_x), text(aim_y), "0"]}}
    return {"schema": "simulation-request/1",
            "source": {"density": "analytic", "particle": config.get("particle", "e+"), "energy": {"mono": {"energy_MeV": energy}}, "position": position, "direction": {"fixed": {"frame": "gun", "vector": [0, 0, 1]}}},
            "scorers": [{"name": "crystal_edep", "readout": "ecal", "select": {"tags": ["crystal"]}, "quantity": "edep"}]}


def run_of(config: dict, events: int, seed: int, threads: int) -> dict:
    return {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT_EMZ", "cuts_mm": {"default": config.get("global_cut_mm", "0.7")}}, "accounting": "separated",
            "run": {"events": events, "first_event": 0, "logical_run_seed": seed, "mode": "mt", "seeding": "per-event", "threads": threads}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("geometry", type=Path)
    parser.add_argument("sample", type=Path)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--events", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--no-spread", action="store_true")
    parser.add_argument("--board-fractions", type=Path, help="a JSON file of FR4's mass fractions by element")
    args = parser.parse_args()
    config = {**read_flat(args.geometry), **read_flat(args.sample)}
    if args.no_spread:
        config["momentum_spread"] = "0"
    fractions = json.loads(args.board_fractions.read_text(encoding="utf-8")) if args.board_fractions else {"H": "0.5", "O": "0.5"}
    args.folder.mkdir(parents=True, exist_ok=True)
    for name, block in (("detector", spec_of(config, fractions)), ("request", request_of(config, True)), ("run", run_of(config, args.events, args.seed, args.threads))):
        (args.folder / f"{name}.json").write_text(json.dumps(block, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "folder": str(args.folder)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
