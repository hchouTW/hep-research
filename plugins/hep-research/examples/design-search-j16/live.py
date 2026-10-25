#!/usr/bin/env python3
"""J16 live part: the F4 confirmation study of one Example A finalist (Geant4 program C3.1), recorded for run.py.

The search of run.py is repeated in the work folder (deterministic, so the finalists and their effective digests are
the replay's), the first finalist's geometry is generated (evaluate_design.py geometry, 1 TV protons), and one F4
study runs with J15's campaign code (examples/design-minimal-spectrometer/live.py: trial, A1.9 event count,
nominal, cut scan, two physics-list variations, tail sources off and on, the four conditions of the qualification
path with the multiple-scattering reference on a silicon slab of the plane's thickness), with this example's
realization profile (space.realization.json) and the aluminium support's independent material entry. The study's
own runs (trial, nominal, cut scan, variations) are seeded S = H(study_id, role, point_id) with study_id =
confirmation_study_id(search id, digest, figure of merit, denominator) (core/simulation/seeds.py), so no seed of the
search serves them (CV-C2); the shared verification and reference runs use J15's fixed ids with the j16a prefix.

export writes recorded/: run records gzip-compressed, the specs, the study folder and its geometry file, home paths
written as ~ with every sha256 citation rewritten (J15's scrub_home), and confirmation.json. Usage:
  HEP_GEANT4_CONFIG=cfg.json python3 examples/design-search-j16/live.py --work DIR [--recorded DIR]"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
J15 = PLUGIN / "examples" / "design-minimal-spectrometer"
sys.path[:0] = [str(PLUGIN), str(J15), str(HERE)]
import live as L  # noqa: E402  (J15's campaign)
import run as R15  # noqa: E402  (J15's run module: STUDIES, CREATED)
from core.simulation.seeds import confirmation_study_id  # noqa: E402

sys.path.remove(str(J15))
sys.modules.pop("run", None)
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("j16_run", HERE / "run.py")
J = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J)

AL = {"name": "G4_Al", "z": 13, "a_g_mole": 26.9815385, "density_g_cm3": 2.699, "radiation_length_mm": 88.97,
      "reference_source": "PDG Atomic and Nuclear Properties 2024 (https://pdg.lbl.gov/2024/AtomicNuclearProperties/), "
                          "aluminum_Al: density 2.699 g/cm3, A 26.9815385(7), X0 8.897 cm, read 2026-10-25",
      "reference_origin": "independent"}
SEARCH_ID = "SEARCH-J16A"


class Confirm(L.Campaign3):
    prefix = "j16a"
    profile_name = "space.realization.json"
    slab_mm = 0.01 * L.X0_SI  # the planes' x/X0 0.01 of silicon
    materials = L.MATERIALS + [AL]

    def __init__(self, work: Path, cfg: dict, art: Path, digest: str):
        super().__init__(work, cfg)
        self.art, self.proj, self.runs = art, art.parent, art / "runs"
        self.digest = digest

    def study_id(self, sid: str) -> str:
        _, fom, den, _ = R15.STUDIES[sid]
        return confirmation_study_id(SEARCH_ID, self.digest, fom, den)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--recorded", type=Path, default=HERE / "recorded")
    ap.add_argument("--export-only", action="store_true", help="re-export a finished confirmation (no simulation)")
    args = ap.parse_args(argv)
    work = args.work.expanduser().resolve()
    cfg = json.loads(Path(os.environ["HEP_GEANT4_CONFIG"]).expanduser().read_text())
    art = work / "A" / "artifacts"
    if not (art / f"runs/{SEARCH_ID}.computational-run.json").is_file():
        J.prepare(J.SRC_A, work / "A")
        J.search(art, SEARCH_ID, J.spec_a(art))
        J.evaluate_finalists(art, J.NS_A, SEARCH_ID, ["REQ-TRK-001", "REQ-CC-001"],
                             upstream={"REQ-CC-001": "REQ-TRK-001"})
    shutil.copy(HERE / "space.realization.json", art / "space.realization.json")
    summ = json.loads((art / f"runs/{SEARCH_ID}.computational-run.json").read_text())["extension"]["search_summary"]
    k = summ["finalists"][0]["index"]
    point = next(p for p in summ["points"] if p["index"] == k)
    cand, study = f"cand-F{k}", f"F{k}-TRK1000"
    den = J.CONFIRM_A["denominator"]
    R15.STUDIES[study] = (cand, J.CONFIRM_A["figure_of_merit"], den, J.CONFIRM_A["requirement"])
    if not (art / "studies" / f"G-{study}.geometry.json").is_file():
        J.ev(art, "geometry", "--candidate", f"{J.NS_A}:{cand}", "--figure-of-merit", J.CONFIRM_A["figure_of_merit"],
             *[a for kk, v in den.items() for a in ("--denominator", f"{kk}={v}")], "--id", f"G-{study}")
    before = {p.name for p in (art / "specs").glob("*")}  # the specs the confirmation writes are exported
    if args.export_only:
        meta = json.loads((args.recorded / "confirmation.json").read_text())
        spec_names = {p.name for p in (args.recorded / "artifacts" / "specs").glob("*")}
        export(art, args.recorded, study, f"{J.NS_A}:{cand}", before - spec_names, meta["events"])
        return 0
    c = Confirm(work / "confirm", cfg, art, point["effective_digest"])
    sh = c.shared(cand)
    t = c.tracking(study)
    out = c.finish_tracking(t, sh)
    print(json.dumps({"study": study, "events": t["events"], "record": str(out["study"]), "log": c.log}, default=str))
    export(art, args.recorded, study, f"{J.NS_A}:{cand}", before, t["events"])
    return 0


def export(art: Path, recorded: Path, study: str, candidate: str, before: set, events: int) -> None:
    if recorded.exists():
        shutil.rmtree(recorded)
    (recorded / "runs").mkdir(parents=True)
    rec = json.loads((art / "studies" / study / "study.computational-run.json").read_text())
    # the study's run records: evidence_records when upgraded, inputs either way (a refused study lists them there)
    refs = [r["ref"] for r in rec["extension"].get("evidence_records") or []]
    refs += [i["ref"] for i in rec.get("inputs") or [] if i.get("artifact_type") == "computational-run"]
    for ref in dict.fromkeys(refs):
        p = art / ref
        with open(recorded / "runs" / (p.name + ".gz"), "wb") as raw, gzip.GzipFile(
                fileobj=raw, mode="wb", compresslevel=9, mtime=0, filename="") as fh:
            fh.write(p.read_bytes())
    (recorded / "artifacts" / "specs").mkdir(parents=True)
    for p in sorted((art / "specs").glob("*")):
        if p.name not in before and p.is_file():
            shutil.copy(p, recorded / "artifacts" / "specs" / p.name)
    (recorded / "artifacts" / "studies").mkdir(parents=True)
    shutil.copytree(art / "studies" / study, recorded / "artifacts" / "studies" / study,
                    ignore=shutil.ignore_patterns("derived.element_sim.json"))
    shutil.copy(art / "studies" / f"G-{study}.geometry.json", recorded / "artifacts" / "studies")
    (recorded / "confirmation.json").write_text(json.dumps({"study": study, "candidate": candidate,
                                                            "search": SEARCH_ID, "events": events}, indent=1) + "\n")
    L.scrub_home(recorded)
    total = sum(p.stat().st_size for p in recorded.rglob("*") if p.is_file())
    print(json.dumps({"recorded": str(recorded), "bytes": total}))


if __name__ == "__main__":
    sys.exit(main())
