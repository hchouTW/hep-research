"""Geant4 search values of evaluate_design.py search (Geant4 program C2.2): one design and one objective -> a design
geometry (evaluate_design.py geometry, in a scratch copy of the artifacts_dir), an element_sim spec (geant4_run.py
from-geometry with the search's realization profile, the beam from the objective's denominator), a short element_sim
run with S and the seed_group the caller gives (evidence role search), and a simreco reconstruction with every tail
source off; the value is core.simulation.estimates.estimate of the declared observable, with its block estimates for
paired comparison. Search values are for selection only: they are never written as evaluations, they are optimistic
(no tail source), and their run records stay in the work folder, outside the artifacts_dir.

The hep-detector side never imports the adapter: geant4_run.py runs as a subprocess. A cache keyed by the design's
effective digest, the objective, S, N, K, B, the adapter version and the hashes of the two executables returns a
result once per key."""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[4]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))
from core.constants import physical as K  # noqa: E402
from core.simulation import estimates as E, summary as S  # noqa: E402
from core.simulation.seeds import job_seeds  # noqa: E402

RUN = PLUGIN / "adapters" / "geant4" / "assets" / "geant4_run.py"
ADAPTER = PLUGIN / "adapters" / "geant4" / "adapter.json"
MASS_KEY = {"proton": "proton_mass_energy", "e-": "electron_mass_energy", "e+": "electron_mass_energy",
            "mu-": "muon_mass_energy", "mu+": "muon_mass_energy"}


class Geant4SearchError(RuntimeError):
    """A Geant4 search value could not be made."""


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def kinetic_mev(particle: str, denominator: dict) -> float:
    """The beam kinetic energy (MeV) from the objective's denominator: rigidity_GV (|z| = 1 for these particles) or
    momentum_GeV."""
    m = K.constant(MASS_KEY[particle], unit="GeV").value
    if "rigidity_GV" in denominator:
        p = float(denominator["rigidity_GV"])
    elif "momentum_GeV" in denominator:
        p = float(denominator["momentum_GeV"])
    else:
        raise Geant4SearchError(f"denominator {sorted(denominator)}: a Geant4 search value needs rigidity_GV or "
                                "momentum_GeV for the beam")
    return (math.hypot(p, m) - m) * 1000.0


class Geant4Values:
    """The Geant4 search values of one search: scratch artifacts, runs and cache in `work`."""

    def __init__(self, cfg: dict, work: Path, artifacts: Path, search_id: str, g4: dict, created: str):
        self.cfg = {k: str(Path(os.path.expanduser(str(v)))) for k, v in cfg.items()}
        for key in ("element_sim", "simreco", "build_record"):
            if not Path(self.cfg.get(key, "")).is_file():
                raise Geant4SearchError(f"HEP_GEANT4_CONFIG: {key} {self.cfg.get(key)!r} is not a file")
        self.work, self.search_id, self.g4, self.created = work, search_id, g4, created
        self.art = work / "artifacts"
        if not self.art.exists():
            shutil.copytree(artifacts, self.art, ignore=shutil.ignore_patterns("reports", "*.jsonl", ".search"))
        self.sim = work / "sim"
        self.cache = work / "cache"
        for d in (self.sim, self.cache, self.art / "specs" / "search"):
            d.mkdir(parents=True, exist_ok=True)
        self.events = int(g4["events"])
        self.blocks = int(g4.get("blocks", 16))
        if self.events % self.blocks:
            raise Geant4SearchError(f"geant4.events {self.events} is not a multiple of blocks {self.blocks}")
        self.versions = {"adapter": json.loads(ADAPTER.read_text(encoding="utf-8"))["version"],
                         "element_sim_sha256": _sha(Path(self.cfg["element_sim"])),
                         "simreco_sha256": _sha(Path(self.cfg["simreco"]))}
        self.runs = 0
        self.cache_hits = 0

    def _go(self, args: list) -> dict:
        p = subprocess.run([sys.executable, "-B", *map(str, args)], capture_output=True, text=True, timeout=36000)
        try:
            out = json.loads(p.stdout)
        except ValueError:
            out = {"raw": p.stdout[-1500:], "stderr": p.stderr[-1500:]}
        if p.returncode != 0:
            raise Geant4SearchError(f"{Path(str(args[0])).name} {args[1] if len(args) > 1 else ''} exited "
                                    f"{p.returncode}: {json.dumps(out)[:1500]}")
        return out

    def key(self, digest: str, label: str, seed: int) -> str:
        return hashlib.sha256(json.dumps({"effective_digest": digest, "level": "geant4", "objective": label,
                                          "S": seed, "N": self.events, "K": self.blocks,
                                          "B": self.events // self.blocks, "target": self.g4["targets"][label],
                                          "reco": self.g4["reco"], "versions": self.versions},
                                         sort_keys=True).encode()).hexdigest()

    def value(self, evaluate_design: Path, candidate_doc: dict, cid: str, short: str, digest: str, label: str,
              target: dict, seed: int, seed_group: str | None, point: int) -> dict:
        """The Geant4 search value of one design (written as candidates/<short>.json in the scratch artifacts) for one
        objective: {value, se, dof, blocks, bound, seed, seed_group, run, cached}."""
        ck = self.key(digest, label, seed)
        hit = self.cache / f"{ck}.json"
        if hit.is_file():
            self.cache_hits += 1
            return dict(json.loads(hit.read_text(encoding="utf-8")), cached=True)
        tspec = self.g4["targets"][label]
        (self.art / "candidates" / f"{short}.json").write_text(json.dumps(candidate_doc, indent=1) + "\n",
                                                                encoding="utf-8")
        gid = f"G-{short}-{_slug(label)}"
        self._go([evaluate_design, "geometry", "--artifacts", self.art, "--candidate", cid, "--figure-of-merit",
                  target["figure_of_merit"], *[a for k, v in target["denominator"].items()
                                               for a in ("--denominator", f"{k}={v}")], "--id", gid])
        spec_path = self.art / "specs" / "search" / f"{gid}.element_sim.json"
        self._go([RUN, "from-geometry", "--geometry", self.art / "studies" / f"{gid}.geometry.json", "--profile",
                  self.art / self.g4["realization"], "--out", spec_path])
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec["source"].update(particle=tspec["particle"],
                              energy_MeV=kinetic_mev(tspec["particle"], target["denominator"]))
        spec["run"].update(events=self.events, logical_run_seed=seed, seeds=list(job_seeds(seed, 0)), first_event=0)
        if self.g4.get("threads"):
            spec["run"].update(run_manager="mt", threads=int(self.g4["threads"]))
        run_id = f"{self.search_id}-{seed_group or 'ind'}-p{point}-{_slug(label)}"
        spec_path.write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
        rec = self.work / "runs" / f"{run_id}.computational-run.json"
        rec.parent.mkdir(exist_ok=True)
        args = [RUN, "run", "--spec", spec_path, "--exe", self.cfg["element_sim"], "--build-record",
                self.cfg["build_record"], "--work", self.sim, "--run-id", run_id, "--record", rec, "--evidence-role",
                "search", "--point-id", f"point-{point}", "--logical-run-seed", seed, "--created", self.created]
        if seed_group:
            args += ["--seed-group", seed_group]
        self._go(args)
        decl = dict(tspec["observable"], name="value")
        reco_spec = dict(self.g4["reco"], schema="simreco.spec/1",
                         output={"observables": [decl], "blocks": {"blocks": self.blocks,
                                                                   "block_size": self.events // self.blocks}})
        reco_path = self.art / "specs" / "search" / f"{run_id}.reco.json"
        reco_path.write_text(json.dumps(reco_spec, indent=1) + "\n", encoding="utf-8")
        reco_rec = self.work / "runs" / f"{run_id}-reco.computational-run.json"
        self._go([RUN, "reco", "--run-record", rec, "--reco-spec", reco_path, "--simreco", self.cfg["simreco"],
                  "--work-out", self.sim, "--reco-id", f"{run_id}-reco", "--record", reco_rec, "--project-root",
                  self.art, "--created", self.created, "--geometry", self.art / "studies" / f"{gid}.geometry.json"])
        self.runs += 1
        summ = S.load(self.sim / f"{run_id}-reco" / "summary_r000.json")
        est = E.estimate(summ, decl)
        blocks = E.block_estimates(summ, decl)
        if est.get("status") != "ok" or blocks.get("status") != "ok":
            out = {"value": None, "error": est.get("reason") or blocks.get("reason"), "seed": seed,
                   "seed_group": seed_group, "run": run_id}
        else:
            out = {"value": est["value"], "se": est["se"], "dof": est["dof"], "blocks": blocks["thetas"],
                   "bound": "optimistic", "seed": seed, "seed_group": seed_group, "run": run_id,
                   "events": summ["run"]["events_in_blocks"]}
        hit.write_text(json.dumps(out, sort_keys=True), encoding="utf-8")
        return dict(out, cached=False)


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-." else "-" for c in text)[:48]
