#!/usr/bin/env python3
"""The AMS-02 RICH replica of the g4sim task package (examples/ams02-rich-replica, synthetic) as detector-spec/1, simulation-request/1
and g4sim-run/1 (g4sim plan, Section E12; S7). Every number is the replica's own, from config/rich_params.cfg (SHA-256 a96efa38...),
and the tables follow sim/rich_sim.cc (SHA-256 128ecf26...): 5 nm steps from 650 to 300 nm, (n - 1) scaled with fused-silica dispersion
from the index quoted at 400 nm, Rayleigh length lambda^4 / C, the foil absorbing below 350 nm. The tile positions follow its BuildTiles:
the 60 aerogel tiles wholly inside the 600 mm aperture and the 16 NaF tiles; the 32 tiles it clips to the aperture with a boolean
intersection are left out (arbitrary CSG is outside g4sim's shape list, Section 2.2: a core-module requirement, Section 13.2).
Usage: python3 make_replica.py PARAMS.cfg OUT_FOLDER   writes detector-spec.json, request.json and run.json."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

PHOTON_EV_NM = 1239.84198
CFG = "user-supplied:g4sim-task/examples/ams02-rich-replica/config/rich_params.cfg"


def params(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        words = line.split("#", 1)[0].split()
        if len(words) == 2:
            out[words[0]] = float(words[1])
    return out


def silica_minus_one(lam_nm: float) -> float:  # Malitson's Sellmeier, the replica's dispersion shape
    l2 = (lam_nm * 1e-3) ** 2
    n2 = 1 + 0.6961663 * l2 / (l2 - 0.0684043 ** 2) + 0.4079426 * l2 / (l2 - 0.1162414 ** 2) + 0.8974794 * l2 / (l2 - 9.896161 ** 2)
    return math.sqrt(n2) - 1


def scaled(n0: float, lam: float, ref: float) -> float:
    return 1 + (n0 - 1) * silica_minus_one(lam) / silica_minus_one(ref)


def number(value: float) -> str:
    return repr(float(value))


def naf_side(p: dict) -> float:
    """The replica's NaF square (4 x 85 = 340 mm) is 1 mm wider than the hole its aerogel lattice leaves (3 x 113 = 339 mm), so in
    rich_sim.cc, which places its volumes without an overlap check, NaF and aerogel overlap in a 0.5 mm strip: g4sim's gap rule refuses
    that. The smallest change that removes it: NaF tiles of 339 / 4 mm at that pitch, filling the hole exactly (a recorded deviation)."""
    return 3 * p["aero_tile_side_mm"] / p["naf_n_per_side"]


def tiles(p: dict) -> tuple[list, list]:
    """BuildTiles of rich_sim.cc: NaF on a 4 x 4 lattice; aerogel cells of a 17 x 17 lattice outside the central 3 x 3, wholly inside the aperture."""
    s, r0, nn = p["aero_tile_side_mm"], p["radiator_aperture_r_mm"], int(p["naf_n_per_side"])
    pn = naf_side(p)
    naf = [[(i - (nn - 1) / 2) * pn, (j - (nn - 1) / 2) * pn] for i in range(nn) for j in range(nn)]
    full = []
    for j in range(-8, 9):
        for i in range(-8, 9):
            if abs(i) <= 1 and abs(j) <= 1:
                continue
            n = 24
            inside = sum(1 for a in range(n) for b in range(n)
                         if ((i - .5) * s + (a + .5) * s / n) ** 2 + ((j - .5) * s + (b + .5) * s / n) ** 2 < r0 * r0)
            if inside == n * n:
                full.append([i * s, j * s])
    return naf, full


def main(argv: list) -> int:
    p = params(Path(argv[1]))
    out = Path(argv[2])
    lam = [p["lambda_max_nm"] - 5 * k for k in range(int((p["lambda_max_nm"] - p["lambda_min_nm"]) / 5) + 1)]
    energies = [number(PHOTON_EV_NM / l) for l in lam]
    table = lambda values: {"energy_eV": energies, "value": [number(v) for v in values]}
    aero_rindex = table([scaled(p["aero_n"], l, p["aero_n_ref_nm"]) for l in lam])
    naf_rindex = table([scaled(p["naf_n"], l, p["aero_n_ref_nm"]) for l in lam])
    rayleigh = table([(l * 1e-3) ** 4 / p["aero_clarity_um4_per_cm"] * 10 for l in lam])  # cm to mm
    naf_tiles, aero_tiles = tiles(p)
    height, foil, ta, tn = p["expansion_height_mm"], p["foil_thickness_mm"], p["aero_thickness_mm"], p["naf_thickness_mm"]
    flat = lambda value: table([value] * len(lam))
    surface_e = [number(PHOTON_EV_NM / 700), number(PHOTON_EV_NM / 250)]
    spec = {"schema": "detector-spec/1",
            "params": {"height_mm": number(height), "mirror_bottom_mm": number(p["mirror_r_bottom_mm"]), "mirror_top_mm": number(p["mirror_r_top_mm"]),
                       "mirror_thickness_mm": number(p["mirror_thickness_mm"]), "aperture_mm": number(p["radiator_aperture_r_mm"]), "foil_mm": number(foil),
                       "aero_side_mm": number(p["aero_tile_side_mm"]), "aero_mm": number(ta), "naf_side_mm": number(naf_side(p)), "naf_mm": number(tn),
                       "mirror_z_mm": "height_mm / 2", "foil_z_mm": "height_mm + foil_mm / 2", "aero_z_mm": "height_mm + foil_mm + aero_mm / 2",
                       "naf_z_mm": "height_mm + foil_mm + naf_mm / 2"},
            "materials": {
                "vacuum_optical": {"base": "G4_Galactic", "optical": {"rindex": flat(1.0)}},
                "aerogel": {"composition": {"Si": "0.4674", "O": "0.5326"}, "density_g_cm3": number(p["aero_density_g_cm3"]),
                            "optical": {"rindex": aero_rindex, "rayleigh_length_mm": rayleigh, "absorption_length_mm": flat(p["aero_abs_len_cm"] * 10)}},
                "naf": {"composition": {"Na": "0.5477", "F": "0.4523"}, "density_g_cm3": number(p["naf_density_g_cm3"]),
                        "optical": {"rindex": naf_rindex, "absorption_length_mm": flat(p["naf_abs_len_cm"] * 10)}},
                "foil_pmma": {"base": "G4_PLEXIGLASS", "optical": {"rindex": flat(p["foil_n"]),
                              "absorption_length_mm": table([0.5 if l < p["foil_cut_nm"] else 10000.0 for l in lam])}},
                "cfrp": {"composition": {"C": "1"}, "density_g_cm3": "1.6"}},
            "templates": {
                "aero_tile": {"solid": {"box": {"size_mm": ["aero_side_mm", "aero_side_mm", "aero_mm"]}}, "material": "aerogel", "tags": ["optical", "aerogel_tile"]},
                "naf_tile": {"solid": {"box": {"size_mm": ["naf_side_mm", "naf_side_mm", "naf_mm"]}}, "material": "naf", "tags": ["optical", "naf_tile"]},
                "foil": {"solid": {"tube": {"rmin_mm": "0", "rmax_mm": "aperture_mm", "length_mm": "foil_mm"}}, "material": "foil_pmma", "tags": ["optical"]},
                "mirror": {"solid": {"cone": {"rmin1_mm": "mirror_bottom_mm", "rmax1_mm": "mirror_bottom_mm + mirror_thickness_mm", "rmin2_mm": "mirror_top_mm",
                                              "rmax2_mm": "mirror_top_mm + mirror_thickness_mm", "length_mm": "height_mm"}}, "material": "cfrp", "tags": ["optical", "mirror"]},
                "plane": {"solid": {"box": {"size_mm": ["1500", "1500", "1"]}}, "material": "vacuum_optical", "tags": ["optical", "plane"]},
                "rich": {"solid": {"box": {"size_mm": ["2000", "2000", "1800"]}}, "material": "vacuum_optical", "tags": ["optical"], "children": [
                    {"template": "plane", "placement": {"single": {"centre_mm": ["0", "0", "-0.5"]}}},
                    {"template": "mirror", "placement": {"single": {"centre_mm": ["0", "0", "mirror_z_mm"]}}},
                    {"template": "foil", "placement": {"single": {"centre_mm": ["0", "0", "foil_z_mm"]}}},
                    {"template": "aero_tile", "placement": {"explicit": {"positions_mm": [[number(x), number(y), "aero_z_mm"] for x, y in aero_tiles]}}},
                    {"template": "naf_tile", "placement": {"explicit": {"positions_mm": [[number(x), number(y), "naf_z_mm"] for x, y in naf_tiles]}}}]}},
            "world": {"material": "G4_Galactic", "size_mm": ["4000", "4000", "4000"], "children": [{"template": "rich", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]},
            "physics_requirements": [{"need": "optical_scope", "select": {"tags": ["optical"]}}],
            "optical_surfaces": {
                "mirror_skin": {"skin": "mirror", "model": "unified", "finish": "polished", "type": "dielectric_metal",
                                "reflectivity": {"energy_eV": surface_e, "value": [number(p["mirror_reflectivity"])] * 2}, "efficiency": {"energy_eV": surface_e, "value": ["0", "0"]}},
                "plane_skin": {"skin": "plane", "model": "unified", "finish": "polished", "type": "dielectric_metal",
                               "reflectivity": {"energy_eV": surface_e, "value": ["0", "0"]}, "efficiency": {"energy_eV": surface_e, "value": ["1", "1"]}}},
            "source_of_facts": {"/params/aero_side_mm": "claim:ams02:C70", "/params/aero_mm": "claim:ams02:C70", "/params/naf_side_mm": CFG + "#naf_tile_side_mm 85 (spec), reduced to 3 x aero_tile_side_mm / 4 to remove the replica's 0.5 mm overlap",
                                "/params/naf_mm": "claim:ams02:C70", "/params/height_mm": CFG + "#expansion_height_mm (spec)",
                                "/params/mirror_bottom_mm": CFG + "#mirror_r_bottom_mm (spec)", "/params/mirror_top_mm": CFG + "#mirror_r_top_mm (spec)",
                                "/params/mirror_thickness_mm": CFG + "#mirror_thickness_mm (spec)", "/params/aperture_mm": CFG + "#radiator_aperture_r_mm (assumed)",
                                "/params/foil_mm": CFG + "#foil_thickness_mm (spec)", "/materials/aerogel/density_g_cm3": CFG + "#aero_density_g_cm3 (assumed)",
                                "/materials/naf/density_g_cm3": CFG + "#naf_density_g_cm3 (assumed)",
                                "/materials/aerogel/optical/rindex": "claim:ams02:C205 (n = 1.050 at 400 nm, the replica's dispersion shape: rich_sim.cc)",
                                "/materials/naf/optical/rindex": "claim:ams02:C205 (n = 1.334, the replica's dispersion shape: rich_sim.cc)"}}
    # the two optical-index pointers name a claim and a note: keep the claim id alone where the checker resolves it
    spec["source_of_facts"]["/materials/aerogel/optical/rindex"] = "claim:ams02:C205"
    spec["source_of_facts"]["/materials/naf/optical/rindex"] = "claim:ams02:C205"
    request = {"schema": "simulation-request/1", "source": {"density": "analytic", "particle": "proton", "energy": {"mono": {"energy_MeV": "100000"}},
               "position": {"box_uniform": {"frame": "world", "centre_mm": ["226", "0", "530"], "size_mm": ["0", "0", "0"]}},
               "direction": {"fixed": {"frame": "world", "vector": ["0", "0", "-1"]}}},
               "scorers": [{"name": "plane", "readout": "none", "select": {"tags": ["plane"]}, "quantity": "photon_detected"}]}
    card = {"schema": "g4sim-run/1", "physics": {"reference_list": "FTFP_BERT", "cuts_mm": {"default": "0.7"}, "extra_constructors": ["G4OpticalPhysics"],
            "optical": {"wls": False}}, "accounting": "separated",
            "run": {"events": 300, "first_event": 0, "logical_run_seed": 20261112, "mode": "mt", "seeding": "per-event", "threads": 4}}
    out.mkdir(parents=True, exist_ok=True)
    for name, document in (("detector-spec.json", spec), ("request.json", request), ("run.json", card)):
        (out / name).write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "aerogel_tiles": len(aero_tiles), "naf_tiles": len(naf_tiles), "wavelengths": len(lam)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
