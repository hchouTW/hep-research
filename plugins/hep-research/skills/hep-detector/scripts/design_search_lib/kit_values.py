"""Geant4 search values of a new geometry kind (g4sim plan, Section 18, point 7): one design and one objective -> a design geometry (evaluate_design.py geometry, in a scratch copy of the artifacts_dir), a detector-spec
and a derivation record (g4kit.py), and a run from those files by path and hash (geant4_run.py run-spec). The layered-spectrometer keeps Geant4Values, unchanged.

The value is read from the run's per-event scorer rows, in equal blocks of events, for paired comparison: `relative_width` is the RMS over the mean of a scorer's total in each block, and `mean_fraction` its mean over the
beam energy. Search values are for selection only. hep-detector never imports the adapter: both programs run as subprocesses.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[4]
RUN = PLUGIN / "adapters" / "geant4" / "assets" / "geant4_run.py"
KIT = PLUGIN / "skills" / "hep-detector" / "scripts" / "g4kit.py"
ADAPTER = PLUGIN / "adapters" / "geant4" / "adapter.json"


class KitSearchError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def block_values(totals: list, energy_mev: float, measure: str, blocks: int) -> list:
    """One value of the measure per block of events; `totals` holds a scorer's total for every event, in event order."""
    size = len(totals) // blocks
    values = []
    for at in range(blocks):
        block = totals[at * size:(at + 1) * size]
        mean = statistics.fmean(block)
        if measure == "mean_fraction":
            values.append(mean / energy_mev)
        elif measure == "relative_width":
            values.append(statistics.stdev(block) / mean if mean > 0 else math.inf)
        else:
            raise KitSearchError(f"unknown measure {measure!r}")
    return values


class KitValues:
    """The Geant4 search values of one search of a new kind: scratch artifacts, runs and cache in `work`."""

    def __init__(self, cfg: dict, work: Path, artifacts: Path, search_id: str, g4: dict, created: str):
        self.program = Path(os.path.expanduser(str(cfg.get("g4sim_run", ""))))
        if not self.program.is_file():
            raise KitSearchError(f"HEP_GEANT4_CONFIG: g4sim_run {cfg.get('g4sim_run')!r} is not a file")
        self.work, self.search_id, self.g4, self.created = work, search_id, g4, created
        self.art = work / "artifacts"
        if not self.art.exists():
            shutil.copytree(artifacts, self.art, ignore=shutil.ignore_patterns("reports", "*.jsonl", ".search"))
        self.cache = work / "cache"
        for folder in (self.cache, self.art / "specs" / "search", work / "runs", work / "sim"):
            folder.mkdir(parents=True, exist_ok=True)
        self.events, self.blocks = int(g4["events"]), int(g4.get("blocks", 16))
        if self.events % self.blocks:
            raise KitSearchError(f"geant4.events {self.events} is not a multiple of blocks {self.blocks}")
        self.versions = {"adapter": json.loads(ADAPTER.read_text(encoding="utf-8"))["version"], "g4sim_run_sha256": _sha(self.program)}
        self.runs = 0
        self.cache_hits = 0
        self.evidence: list = []

    def _go(self, args: list) -> dict:
        done = subprocess.run([sys.executable, "-B", *map(str, args)], capture_output=True, text=True, check=False, timeout=7200)
        try:
            result = json.loads(done.stdout[done.stdout.rindex("\n{") + 1 if "\n{" in done.stdout else 0:])
        except ValueError:
            result = {"status": "failed", "error": done.stdout[-300:] + done.stderr[-300:]}
        if done.returncode != 0 or result.get("status") != "ok":
            raise KitSearchError(f"{Path(str(args[0])).name} {args[1]}: {json.dumps(result)[:400]}")
        return result

    def value(self, evaluate_design: Path, candidate_doc: dict, cid: str, short: str, digest: str, label: str, target: dict, seed: int, seed_group: str | None, point: int) -> dict:
        """The search value of one design for one objective: {value, se, dof, blocks, bound, seed, seed_group, run, cached}."""
        key = hashlib.sha256(json.dumps([digest, label, seed, self.events, self.blocks, self.versions], sort_keys=True).encode("utf-8")).hexdigest()
        hit = self.cache / f"{key}.json"
        if hit.is_file():
            self.cache_hits += 1
            return dict(json.loads(hit.read_text(encoding="utf-8")), cached=True)
        wanted = self.g4["targets"][label]
        (self.art / "candidates" / f"{short}.json").write_text(json.dumps(candidate_doc, indent=1) + "\n", encoding="utf-8")
        geometry_id = f"G-{short}-{hashlib.sha256(label.encode('utf-8')).hexdigest()[:8]}"
        self._go([evaluate_design, "geometry", "--artifacts", self.art, "--candidate", cid, "--figure-of-merit", target["figure_of_merit"], *[word for name, value in target["denominator"].items() for word in ("--denominator", f"{name}={value}")], "--id", geometry_id])
        geometry = self.art / "studies" / f"{geometry_id}.geometry.json"
        folder = self.art / "specs" / "search"
        detector, derivation = folder / f"{geometry_id}.detector.json", folder / f"{geometry_id}.derivation.json"
        self._go([KIT, "derive", "--geometry", geometry, "--out-detector", detector, "--out-derivation", derivation])
        energy_mev = float(wanted["energy_MeV"])
        request = json.loads((self.art / self.g4["kit"]["request"]).read_text(encoding="utf-8"))
        request["source"].update(particle=wanted["particle"], energy={"mono": {"energy_MeV": str(energy_mev)}})
        card = json.loads((self.art / self.g4["kit"]["run"]).read_text(encoding="utf-8"))
        card["run"].update(events=self.events, first_event=0, logical_run_seed=seed)
        run_id = f"{self.search_id}-{seed_group or 'ind'}-p{point}-{geometry_id[-8:]}"
        request_path, card_path = folder / f"{run_id}.request.json", folder / f"{run_id}.run.json"
        request_path.write_text(json.dumps(request, indent=1) + "\n", encoding="utf-8")
        card_path.write_text(json.dumps(card, indent=1) + "\n", encoding="utf-8")
        record = self.work / "runs" / f"{run_id}.computational-run.json"
        sim = self.work / "sim" / run_id
        self._go([RUN, "run-spec", "--detector", detector, "--detector-sha256", _sha(detector), "--request", request_path, "--request-sha256", _sha(request_path), "--run", card_path, "--run-sha256", _sha(card_path),
                  "--exe", self.program, "--work", sim, "--run-id", run_id, "--record", record, "--created", self.created, "--input", geometry])
        self.runs += 1
        self.evidence.append({"point": point, "label": label, "run": run_id, "derivation": str(derivation.relative_to(self.art)), "detector_sha256": _sha(detector), "request_sha256": _sha(request_path), "run_card_sha256": _sha(card_path), "record": str(record)})
        totals = [0.0] * self.events
        with (sim / "cells.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.reader(handle):
                if row[1] == wanted["scorer"] and row[2] != "-1":
                    totals[int(row[0])] += float(row[4])
        thetas = block_values(totals, energy_mev, wanted["measure"], self.blocks)
        mean = statistics.fmean(thetas)
        result = {"value": mean, "se": statistics.stdev(thetas) / math.sqrt(self.blocks), "dof": self.blocks - 1, "blocks": thetas, "bound": "optimistic", "seed": seed, "seed_group": seed_group, "run": run_id, "events": self.events}
        hit.write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
        return dict(result, cached=False)
