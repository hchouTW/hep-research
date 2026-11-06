#!/usr/bin/env python3
"""GB11 to GB14 (g4sim plan, Section 23): judge the runs of s3_em against check-spec's prediction, by the criteria of the S3 task card.

GB11 and GB12 are run three ways: as Part B describes (`pai`), with the activator run again after the EM constructor (`pai-late`), and with models
added for the region only (`pai-region`): the last two are the evidence the addendum needs, because the first does nothing in Geant4 11.4.3.

Usage: judge.py PROGRAM FOLDER   In an activated Geant4 environment. Prints JSON with a status key; exit 0 all confirmed, 1 a GB not confirmed, 2 bad input.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[3] / "assets"
sys.path.insert(0, str(ASSETS))

import g4sim_physics_check as check  # noqa: E402

VISIBLE_TOLERANCE = 1e-12
LISTS = ("FTFP_BERT", "FTFP_BERT_EMZ")
REQUESTS = {"electron": ["tracker:e-:PAI"], "positron_photon": ["tracker:e+:PAIphoton"], "proton": ["tracker:proton:PAI"], "muon": ["tracker:mu-:PAI"], "ion": ["tracker:GenericIon:PAI"],
            "everything": ["tracker:all:PAI"], "alpha": ["tracker:alpha:PAI"], "twice": ["tracker:e-:PAI", "tracker:e+:PAI"]}
MATERIALS = ("G4_POLYSTYRENE", "G4_PbWO4")
PAI_MODEL_NAMES = ("PAIModel", "PAIPhotModel")
WANTED_STEP_REPORT = ("(0.1, 0.5 mm)", "(0.1, 0.05 mm)", "(0.1, 0.05 mm)", "(0.1, 0.05 mm)")
DEFAULT_STEP_REPORT = ("(0.2, 1 mm)", "(0.2, 0.1 mm)", "(0.2, 0.1 mm)", "(0.2, 0.1 mm)")
NEEDED_BIRKS_PARTICLES = ("e-", "mu-", "proton", "alpha", "direct_neutron", "gamma")


def run(program: str, folder: Path, name: str, *arguments: str) -> dict:
    target = folder / f"{name}.json"
    with (folder / f"{name}.log").open("w", encoding="utf-8") as log:
        subprocess.run([program, arguments[0], arguments[1], str(target), *arguments[2:]], check=True, stdout=log, stderr=subprocess.STDOUT, cwd=folder)
    return json.loads(target.read_text(encoding="utf-8"))


def model_names(rows: list) -> list:
    return sorted({row[1] for row in rows})


def has_pai(record: dict, particle: str, region: str) -> bool:
    return any(name in PAI_MODEL_NAMES for name in model_names(record["particles"][particle]["regions"][region]))


def carrying(record: dict) -> dict:
    return {name: item["name"] for name, item in record["particles"].items()}


def predicted(requests: list, ionisation: dict) -> set:
    """Who check-spec says gets PAI in the tracker: everyone carrying the mapped process name."""
    parsed = [dict(zip(("region", "particle", "model"), text.split(":"))) for text in requests]
    return {particle for row in check.effective_pai(parsed, ionisation) for particle in row["particles"]}


def judge_pai(program: str, folder: Path, listing: str, mode: str) -> dict:
    plain = run(program, folder, f"plain-{listing}", "pai", listing)
    ionisation = carrying(plain)
    rows = {}
    for label, requests in REQUESTS.items():
        record = run(program, folder, f"{mode}-{listing}-{label}", mode, listing, *requests)
        wanted = predicted(requests, ionisation)
        found = {name for name in record["particles"] if has_pai(record, name, "tracker")}
        outside_changed = sorted(name for name, item in record["particles"].items() for region in ("calorimeter", "DefaultRegionForTheWorld")
                                 if model_names(item["regions"][region]) != model_names(plain["particles"][name]["regions"][region]))
        rows[label] = {"predicted": len(wanted), "found": len(found), "missing": sorted(wanted - found)[:6], "unexpected": sorted(found - wanted)[:6],
                       "outside_changed": outside_changed[:6], "electron_models": record["particles"]["e-"]["model_count"], "alpha_has_pai": "alpha" in found}
    return {"rows": rows, "agrees": all(not row["missing"] and not row["unexpected"] for row in rows.values()),
            "nothing_applied": all(row["found"] == 0 for row in rows.values())}


def judge_birks(program: str, folder: Path, listing: str) -> dict:
    results, seen, control = {}, set(), 0.0
    for material in MATERIALS:
        record = run(program, folder, f"birks-{material}", "birks", listing, material)
        largest = max(float.fromhex(row["largest"]) for row in record["rows"].values())
        seen |= {key.split("/")[0] for key in record["rows"]}
        control = max([control, *(float.fromhex(row["control"]) for key, row in record["rows"].items() if "nonionizing" in key or "neutral" in key)])
        results[material] = {"largest": largest, "before": float.fromhex(record["birks_before"]), "after": float.fromhex(record["birks_after"]),
                             "steps": sum(row["steps"] for row in record["rows"].values())}
    silent = all(item["before"] == 0 and item["after"] != 0 for item in results.values())
    within = all(item["largest"] <= VISIBLE_TOLERANCE for item in results.values())
    return {"materials": results, "control_largest": control, "confirmed": within and silent and control > VISIBLE_TOLERANCE and set(NEEDED_BIRKS_PARTICLES) <= seen,
            "missing_particles": sorted(set(NEEDED_BIRKS_PARTICLES) - seen)}


def judge_steps(program: str, folder: Path) -> dict:
    records = {when: run(program, folder, f"steps-{when}", "steps", "FTFP_BERT", when) for when in ("none", "before", "after")}

    def reads(record: dict, wanted: tuple) -> bool:
        return len(record["report"]) == 4 and all(line.endswith(item) for line, item in zip(record["report"], wanted))
    defaults = (float.fromhex(records["none"]["msc_range_factor"]), float.fromhex(records["none"]["msc_muhad_range_factor"]))
    after = (float.fromhex(records["after"]["msc_range_factor"]), float.fromhex(records["after"]["msc_muhad_range_factor"]))
    before = (float.fromhex(records["before"]["msc_range_factor"]), float.fromhex(records["before"]["msc_muhad_range_factor"]))
    return {"defaults": defaults, "after": after, "before": before,
            "confirmed": reads(records["none"], DEFAULT_STEP_REPORT) and reads(records["before"], DEFAULT_STEP_REPORT) and reads(records["after"], WANTED_STEP_REPORT)
            and before == defaults and after == (defaults[0] / 2, defaults[1] / 2)}


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"status": "rejected", "message": "usage: judge.py PROGRAM FOLDER"}))
        return 2
    program, folder = str(Path(sys.argv[1]).resolve()), Path(sys.argv[2]).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    described = {listing: judge_pai(program, folder, listing, "pai") for listing in LISTS}
    late = {listing: judge_pai(program, folder, listing, "pai-late") for listing in LISTS}
    region_only = {listing: judge_pai(program, folder, listing, "pai-region") for listing in LISTS}
    verdicts = {"as_described": described, "activator_run_again": late, "region_only": region_only, "GB13": judge_birks(program, folder, "FTFP_BERT_EMZ"), "GB14": judge_steps(program, folder)}
    verdicts["GB11"] = "confirmed" if all(item["agrees"] for item in described.values()) else "falsified"
    confirmed = verdicts["GB11"] == "confirmed" and verdicts["GB13"]["confirmed"] and verdicts["GB14"]["confirmed"]
    print(json.dumps({"status": "ok" if confirmed else "failed", **verdicts}, indent=1))
    return 0 if confirmed else 1


if __name__ == "__main__":
    sys.exit(main())
