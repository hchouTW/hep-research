#!/usr/bin/env python3
"""Write the run summary (simulation-summary/1) of a layered_sim logical run from its per-event CSV (Geant4 program
A1.5): per-block accumulators of the declared observables, the input of the batch-means statistics of hep-detector's
study scripts. From adapter 0.2.0 layered_sim writes the summary itself and this producer stays as a test oracle.

Method: the CSVs of one or more jobs of one logical run (CSV or .csv.gz, first line '# SIMULATION') are read; event i
(the event column minus --first-event) belongs to block floor(i / B), events with i >= K B are ignored and counted;
each observable of the declaration (simulation-observables/1: a JSON array, or an object with an 'observables' array,
such as a study spec) accumulates only the events its selection keeps (core/simulation/summary.py). Event weights: a
'weight' column must be all 1 (deposits are already multiplied by the track weight); without one the summary records
weight_column absent, which needs a run record whose spec has no biasing command. The summary is validated with
contracts/schemas/simulation_summary.json before it is written.
Usage (paths relative to the current folder):
  summary_from_csv.py --csv EVENTS.csv[.gz] [--csv ...] --observables DECL.json --block-size B --blocks K
                      --run-record RUN.json --out SUMMARY.json [--first-event E] [--evidence-role ROLE]
                      [--logical-run-seed S] [--seed-scheme hash-v1|legacy]
Output JSON: status, status_label, inputs, defaults_used, summary, events_in_blocks, events_ignored.
Exit codes: 0 written; 2 bad input (unreadable CSV, unknown column, a weight other than 1, biasing without weights,
an invalid summary). Standard library only."""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4common import JsonArgumentParser, sha256_file, tilde, write_json  # noqa: E402
from contracts import trace  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.simulation import summary as S  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

VERSION = "1.0.0"
BIASING_PREFIXES = ("/process/em/setSecBiasing", "/process/em/setDirectionalSplitting", "/biasing/",
                    "/process/em/setElectronBremSplitting", "/run/setCut biasing")


class InputError(ValueError):
    """Input the producer refuses (exit 2)."""


def read_rows(path: Path) -> list[dict]:
    raw = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    if len(lines) < 2 or lines[0] != "# SIMULATION":
        raise InputError(f"{path.name}: not a layered_sim CSV (first line must be '# SIMULATION')")
    cols = lines[1].split(",")
    rows = []
    for ln in lines[2:]:
        if ln:
            row = {}
            for c, v in zip(cols, ln.split(",")):
                try:
                    row[c] = float(v)
                except ValueError:
                    row[c] = v
            rows.append(row)
    return rows


def declarations(path: Path) -> list[dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    obs = doc.get("observables") if isinstance(doc, dict) else doc
    rep = validate(obs, "simulation_observables.json")
    if not rep.ok:
        raise InputError(f"{path.name}: not a simulation-observables/1 declaration: "
                         + "; ".join(f.message for f in rep.errors)[:400])
    return obs


def biasing(sim: dict) -> list[str]:
    return [c for c in sim.get("ui_commands") or [] if c.startswith(BIASING_PREFIXES)]


def cmd(args) -> tuple[str, dict]:
    obs = declarations(Path(args.observables))
    rec = json.loads(Path(args.run_record).read_text(encoding="utf-8"))
    sim = (rec.get("extension") or {}).get("simulation")
    if not isinstance(sim, dict):
        raise InputError("--run-record is not a Geant4 run record (no extension.simulation)")
    rows = []
    for c in args.csv:
        rows += read_rows(Path(c))
    if not rows:
        raise InputError("the CSVs hold no events")
    cols = set(rows[0])
    for o in obs:
        needed = {o["source_column"], *(c["column"] for c in o.get("selection") or [])}
        if needed - cols:
            raise InputError(f"observable {o['name']}: columns {sorted(needed - cols)} are not in the CSV")
    if "weight" in cols:
        bad = sum(1 for r in rows if r.get("weight") != 1.0)
        if bad:
            raise InputError(f"{bad} events have a weight other than 1: weighted accumulation is not supported (A1.5)")
        weight = "unit"
    else:
        if biasing(sim):
            raise InputError(f"the run used biasing commands {biasing(sim)} but the CSV has no weight column")
        weight = "absent"
    phys, gun = sim.get("physics") or {}, sim.get("gun") or {}
    settings = {"default_cut_mm": phys.get("default_cut_mm"), "step_limit_mm": phys.get("step_limit_mm", 0.0),
                "em_constructor": phys.get("em_constructor"), "reference_list": phys.get("reference_list"),
                "ui_commands": sim.get("ui_commands", []), "particle": gun.get("particle"),
                "energy_MeV": gun.get("energy_MeV")}
    run = {"run_id": rec.get("artifact_id"), "evidence_role": args.evidence_role, "seeding": "stream",
           "spec_sha256": sim.get("spec_sha256"), "weight_column": weight, "settings": settings,
           "data_path_problems": sim.get("data_path_problems", []),
           "datasets_content_match": all(d.get("content_match") for d in sim.get("datasets", [])),
           "run_record": {"ref": tilde(Path(args.run_record).resolve()), "sha256": sha256_file(Path(args.run_record))},
           "csv": [{"name": Path(c).name, "sha256": sha256_file(Path(c))} for c in args.csv]}
    if args.logical_run_seed is not None:
        run["logical_run_seed"] = args.logical_run_seed
    if args.seed_scheme:
        run["seed_scheme"] = args.seed_scheme
    run = {k: v for k, v in run.items() if v is not None}
    run["run_record"]["artifact_id"] = rec.get("artifact_id")
    try:
        doc = S.build(rows, obs, args.block_size, args.blocks, args.first_event, run,
                      {"name": "python-csv", "version": VERSION, **trace.provenance()})
    except S.SummaryError as exc:
        raise InputError(str(exc)) from exc
    rep = validate(doc, "simulation_summary.json")
    if not rep.ok:
        raise InputError("the summary does not validate: " + "; ".join(f.message for f in rep.errors)[:400])
    write_json(Path(args.out), doc)
    return "ok", {"summary": tilde(Path(args.out).resolve()), "events_in_blocks": doc["run"]["events_in_blocks"],
                  "events_ignored": doc["run"]["events_ignored"]}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", action="append", required=True)
    ap.add_argument("--observables", required=True)
    ap.add_argument("--block-size", type=int, required=True)
    ap.add_argument("--blocks", type=int, required=True)
    ap.add_argument("--run-record", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--first-event", type=int, default=0)
    ap.add_argument("--evidence-role")
    ap.add_argument("--logical-run-seed", type=int)
    ap.add_argument("--seed-scheme", choices=("hash-v1", "legacy"))
    add_status_argument(ap)
    args = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("first_event", "status") if f"--{k.replace('_', '-')}" not in given]
    try:
        status, doc = cmd(args)
    except (InputError, OSError, ValueError, KeyError) as exc:
        status, doc = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **doc}, indent=1, default=str))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
