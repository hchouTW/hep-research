#!/usr/bin/env python3
"""J16 (Geant4 program C3): automated candidate generation on Examples A and B, offline replay.

SYNTHETIC. The search of evaluate_design.py (D2 candidate generator) runs on the design-specs and candidates of
examples/design-space-spectrometer (Example A, an AMS-like space spectrometer) and examples/design-collider-tracker
(Example B, a collider tracker and ECAL); it proposes finalists, which are expanded and evaluated like any candidate,
and contracts/design.py derives every verdict, the screening, the comparison basis and the ranking or its refusal.
The search demonstrates the process: its finalists are not new detector designs.

  Example A: base cand-S; free: the number of planes (4 to 9) and their positions over 0 to 3 m, and the field
    (0.1 to 0.5 T); an optional TOF slot; objectives REQ-TRK-001 (1 TV protons) and CON-MASS-001, constraint
    REQ-CC-001; the designer's three seed proposals. One finalist (the first) has an F4 confirmation study, run live
    by live.py and replayed here from recorded/ (label --upgrade, f4), on seeds the search never used (CV-C2).
  Example B: base cand-B; free: the plane count (8 to 13) and positions, the field (1 to 2 T, the role rule's upper limit) and the ECAL
    stochastic term; objectives REQ-TRK-001, REQ-ECAL-001 and CON-MASS-001; the four capability.unavailable
    requirements are evaluated as unavailable for the finalists and carried through the report.

Every step goes through skills/hep-detector/scripts/evaluate_design.py (search, expand --search, run, budget, report,
search --diagnose) and check_geant4_study.py label. The two searches are replayed from recorded/search/ (run
live with --live-search). Usage (from the plugin root):
  python3 examples/design-search-j16/run.py [--out DIR] [--live-search]
Exit 0 when every pre-declared criterion passes."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
EVAL = PLUGIN / "skills" / "hep-detector" / "scripts" / "evaluate_design.py"
CHECK = PLUGIN / "skills" / "hep-detector" / "scripts" / "check_geant4_study.py"
RECORDED = HERE / "recorded"
# Examples A and B as of their 0.38.0 outputs, snapshotted: the recorded searches name the design-spec by sha256,
# and the sibling examples' outputs carry the plugin version, so they change at every release.
SRC_A = RECORDED / "sources" / "A"  # from examples/design-space-spectrometer/output
SRC_B = RECORDED / "sources" / "B"  # from examples/design-collider-tracker/output
NS_A, NS_B = "ams-like-v1", "collider-tracker-v1"
CREATED = "2026-10-25"
EPOCH = "1792886400"  # 2026-10-25T00:00:00Z
UNAVAILABLE_B = ("REQ-HCAL-001", "REQ-TRG-001", "REQ-PU-001", "REQ-CONT-001")
CONFIRM_A = {"figure_of_merit": "momentum-resolution-core", "denominator": {"rigidity_GV": 1000, "species": "proton"},
             "requirement": "REQ-TRK-001"}
NOTE = ("SYNTHETIC: the search proposes candidates; verdicts, screening, comparison basis and ranking come only from "
        "contracts/design.py; search values are not evaluations and no optimum is claimed")


def env() -> dict:
    return dict(os.environ, SOURCE_DATE_EPOCH=EPOCH)


def ev(art: Path, *args, ok=(0,)) -> tuple[int, dict]:
    p = subprocess.run([sys.executable, "-B", str(EVAL), *map(str, args), "--artifacts", str(art)],
                       capture_output=True, text=True, timeout=7200, env=env())
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = {"raw": p.stdout[-2000:], "stderr": p.stderr[-2000:]}
    if p.returncode not in ok:
        raise RuntimeError(f"evaluate_design {args[0]} exit {p.returncode}: {json.dumps(out)[:2500]}")
    return p.returncode, out


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(src: Path, dst: Path) -> Path:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("reports", "results.json"))
    return dst / "artifacts"


def spec_a(art: Path) -> dict:
    return {"search_spec_version": 1,
            "description": "J16 Example A: plane count, positions and field of an AMS-like spectrometer (SYNTHETIC)",
            "design_spec": {"path": "design-spec.v1.json", "sha256": sha(art / "design-spec.v1.json")},
            "base_candidate": f"{NS_A}:cand-S",
            "objectives": [{"requirement": "REQ-TRK-001"}, {"requirement": "CON-MASS-001"}],
            "constraints": [{"requirement": "REQ-CC-001"}],
            "free_parameters": [
                {"ref": "DES-TRK-001.parameters.layer_positions_m", "kind": "positions", "n": [4, 9],
                 "range": [0.0, 3.0], "min_spacing_m": 0.05},
                {"ref": "DES-MAG-001.parameters.field_T", "range": [0.1, 0.5]}],
            "slots": {"tof": [0, 1]}, "regenerate_budgets": ["DES-TRK-001", "DES-MAG-001"],
            "rules_version": "1.0.0", "materials_version": "1.0.0", "budget": {"evaluations": 1200, "geant4": 0},
            "optimizer": {"name": "nsga2", "population": 40, "generations": 30, "seed": 1601},
            "stopping": {"hypervolume_window": 10, "min_improvement": 0.001, "reference_point": "auto"},
            "finalists": {"max": 3, "distinct_topologies": True},
            "proposals": [
                {"id": "P-long", "reason": "the longest lever arm with five planes: the measurement term falls as L^2",
                 "parameters": {"DES-TRK-001.parameters.layer_positions_m": [0.0, 0.75, 1.5, 2.25, 3.0]}},
                {"id": "P-ends", "reason": "planes clustered at the two ends and the centre raise the MDR "
                                           "(section C Appendix A)",
                 "parameters": {"DES-TRK-001.parameters.layer_positions_m": [0.0, 0.05, 1.5, 2.95, 3.0]}},
                {"id": "P-base", "reason": "the base layout as a seed", "parameters": {}}],
            "consistency_samples": 3}


def spec_b(art: Path) -> dict:
    return {"search_spec_version": 1,
            "description": "J16 Example B: tracker planes, field and ECAL stochastic term of a collider detector "
                           "(SYNTHETIC)",
            "design_spec": {"path": "design-spec.v1.json", "sha256": sha(art / "design-spec.v1.json")},
            "base_candidate": f"{NS_B}:cand-B",
            "objectives": [{"requirement": "REQ-TRK-001"}, {"requirement": "REQ-ECAL-001"},
                           {"requirement": "CON-MASS-001"}],
            "free_parameters": [
                {"ref": "DES-TRK-001.parameters.layer_positions_m", "kind": "positions", "n": [8, 13],
                 "range": [0.1, 1.1], "min_spacing_m": 0.03},
                {"ref": "DES-MAG-001.parameters.field_T", "range": [1.0, 2.0]},
                {"ref": "DES-ECAL-001.parameters.stochastic_term", "range": [0.02, 0.08]}],
            "regenerate_budgets": ["DES-TRK-001", "DES-MAG-001"],
            "rules_version": "1.0.0", "materials_version": "1.0.0", "budget": {"evaluations": 1200, "geant4": 0},
            "optimizer": {"name": "nsga2", "population": 40, "generations": 30, "seed": 1602},
            "stopping": {"hypervolume_window": 10, "min_improvement": 0.001, "reference_point": "auto"},
            "finalists": {"max": 3, "distinct_topologies": True},
            "proposals": [{"id": "P-base", "reason": "the base layout as a seed", "parameters": {}}],
            "consistency_samples": 3}


def search(art: Path, sid: str, spec: dict, live: bool = False) -> dict:
    """The search: run live (--live-search, or when nothing is recorded) and recorded to recorded/search/<sid>.run.json.gz,
    else unpacked from that record. NSGA-II draws its variation with libm functions (pow), whose last bits differ
    between platforms, so a rerun elsewhere may take another trajectory; the recorded search keeps the finalists, and
    with them the confirmation's candidate, identical everywhere (decoding a recorded genome is exact arithmetic)."""
    (art / "search").mkdir(exist_ok=True)
    (art / "search" / f"{sid}.spec.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    rec = RECORDED / "search" / f"{sid}.run.json.gz"
    run = art / "runs" / f"{sid}.computational-run.json"
    if live or not rec.is_file():
        _, out = ev(art, "search", "--spec", f"search/{sid}.spec.json", "--id", sid, "--status", "synthetic")
        rec.parent.mkdir(parents=True, exist_ok=True)
        with open(rec, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0,
                                                   filename="") as fh:
            fh.write(run.read_bytes())
        return out
    run.parent.mkdir(exist_ok=True)
    run.write_bytes(gzip.decompress(rec.read_bytes()))
    summ = json.loads(run.read_text(encoding="utf-8"))["extension"]["search_summary"]
    return {"status": "ok", "stopped": summ["optimizer"].get("stopped"), "recorded": True}


def evaluate_finalists(art: Path, ns: str, sid: str, requirements: list[str], upstream: dict | None = None,
                       unavailable: tuple = ()) -> list[dict]:
    run_rel = f"runs/{sid}.computational-run.json"
    summ = json.loads((art / run_rel).read_text(encoding="utf-8"))["extension"]["search_summary"]
    rows = []
    for f in summ["finalists"]:
        k = f["index"]
        name = f"cand-F{k}"
        ev(art, "expand", "--search", run_rel, "--point", k, "--candidate-id", name)
        cid = f"{ns}:{name}"
        got = {}
        for req in requirements:
            eid = f"CALC-{req.split('-')[1]}-F{k}"
            extra = ["--upstream", got[upstream[req]]["evaluation"]] if upstream and req in upstream else []
            _, r = ev(art, "run", "--candidate", cid, "--requirement", req, "--id", eid, "--status", "synthetic",
                      *extra)
            got[req] = r
        _, m = ev(art, "budget", "--candidate", cid, "--quantity", "mass", "--id", f"CALC-MASS-F{k}", "--status",
                  "synthetic")
        for req in unavailable:
            ev(art, "run", "--candidate", cid, "--requirement", req, "--id", f"EST-{req[4:-4]}-F{k}", "--status",
               "synthetic")
        rows.append({"candidate": cid, "index": k, "topology": f["topology"],
                     "values": {req: r.get("value") for req, r in got.items()}, "mass_kg": m.get("value")})
    return rows


def replay_confirmation(art: Path) -> dict | None:
    """The Example A confirmation from recorded/ (live.py): run records (gzip), specs, the study inputs and checks
    unpacked into the artifacts_dir, check_geant4_study.py label --upgrade, then evaluate_design.py f4."""
    meta_path = RECORDED / "confirmation.json"
    if not meta_path.is_file():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    (art / "runs").mkdir(exist_ok=True)
    for p in sorted((RECORDED / "runs").glob("*.json.gz")):
        (art / "runs" / p.name[:-3]).write_bytes(gzip.decompress(p.read_bytes()))
    for sub in ("specs", "studies", "checks"):
        if (RECORDED / "artifacts" / sub).is_dir():
            shutil.copytree(RECORDED / "artifacts" / sub, art / sub, dirs_exist_ok=True)
    study, sdir = meta["study"], art / "studies" / meta["study"]
    live = json.loads((sdir / "study.computational-run.json").read_text(encoding="utf-8"))
    refs = [r["ref"] for r in (live.get("extension") or {}).get("evidence_records") or []]
    refs += [i["ref"] for i in live.get("inputs") or [] if i.get("artifact_type") == "computational-run"]
    var = ["--variations", str(sdir / "variations.json")] if (sdir / "variations.json").is_file() else []
    p = subprocess.run([sys.executable, "-B", str(CHECK), "label", "--spec", str(sdir / "study.json"), "--benchmarks",
                        str(sdir / "bench.results.json"), "--convergence", str(sdir / "convergence.json"), *var,
                        *[a for r in dict.fromkeys(refs) for a in ("--run-record", str(art / r))],
                        "--project-root", str(art), "--results", str(sdir / "f4-results.json"), "--geometry",
                        str(art / "studies" / f"G-{study}.geometry.json"), "--upgrade", "--write",
                        str(sdir / "study.computational-run.json"), "--created", CREATED],
                       capture_output=True, text=True, timeout=1200, env=env())
    lab = json.loads(p.stdout)
    code, f4 = ev(art, "f4", "--candidate", meta["candidate"], "--requirement", CONFIRM_A["requirement"], "--study",
                  f"studies/{study}/study.computational-run.json", "--id", f"SIM-{study}", ok=(0, 3))
    return {"study": study, "candidate": meta["candidate"], "upgrade": lab.get("upgrade"), "gaps": lab.get("gaps"),
            "f4_exit": code, "value": f4.get("value"), "fidelity": f4.get("fidelity")}


def matrix_rows(full: dict, prefix: str) -> dict:
    rows = {}
    for item in full["requirements"] + full["constraints"]:
        for m in item["matrix"]:
            for c in m["candidates"]:
                if f":{prefix}" in c:
                    rows[f"{item['id'].split(':')[1]} {c.split(':')[1]}"] = {"result": m["result"],
                                                                             "codes": m["codes"]}
    return rows


def run_example(name: str, src: Path, out: Path, spec_fn, ns: str, sid: str, requirements, upstream=None,
                unavailable=(), confirm=False, live=False) -> dict:
    art = prepare(src, out / name)
    dec = out / name / "decisions"
    s = search(art, sid, spec_fn(art), live)
    rows = evaluate_finalists(art, ns, sid, requirements, upstream, unavailable)
    conf = replay_confirmation(art) if confirm else None
    rep_args = ["report", "--name", f"j16-{name.lower()}"] + (["--decisions", str(dec)] if dec.is_dir() else [])
    _, rep = ev(art, *rep_args, ok=(0, 1, 3))
    _, diag = ev(art, "search", "--diagnose", f"runs/{sid}.computational-run.json")
    sys.path.insert(0, str(PLUGIN))
    from contracts import design
    full = design.derive(art, dec if dec.is_dir() else None)
    summ = json.loads((art / f"runs/{sid}.computational-run.json").read_text(encoding="utf-8"))["extension"][
        "search_summary"]
    return {"search": {"evaluations": summ["evaluated"]["F1"], "distinct_designs": summ["evaluated"]["distinct_designs"],
                       "topologies": summ["evaluated"]["topologies"], "front": len(summ["front"]),
                       "finalists": [f["index"] for f in summ["finalists"]],
                       "proposals": [p["id"] for p in summ["proposals"]], "stopped": s.get("stopped"),
                       "consistency_max_relative_difference": summ["consistency"]["max_relative_difference"]},
            "finalists": rows, "confirmation": conf, "rows": matrix_rows(full, "cand-F"),
            "screening": {k: v for k, v in (full.get("screening") or {}).items()} if isinstance(
                full.get("screening"), dict) else full.get("screening"),
            "comparison_basis": {k: full["comparison_basis"].get(k) for k in ("declared", "holds", "reason")},
            "ranking": {"status": full["ranking"]["status"], "reasons": full["ranking"].get("reasons", [])},
            "gate_flags": full["gate_flags"], "errors": [(e["code"], e["path"]) for e in full["errors"]],
            "diagnostic": [{k: r[k] for k in ("candidate", "search_level", "fidelity", "search_minus_official",
                                              "f4_qualified") if k in r} for r in diag["rows"]],
            "report": rep.get("report")}


def criteria(a: dict, b: dict) -> dict:
    fa = [r for r in a["rows"] if r.startswith("REQ-TRK-001")]
    unavailable_b = [r for k, r in b["rows"].items() if k.split()[0] in UNAVAILABLE_B]
    conf = a.get("confirmation") or {}
    return {
        "a_search_ran": a["search"]["evaluations"] > 0 and bool(a["search"]["finalists"]),
        "a_proposals_recorded": a["search"]["proposals"] == ["P-long", "P-ends", "P-base"],
        "a_consistency": (a["search"]["consistency_max_relative_difference"] or 0.0) <= 1e-12,
        "a_finalists_reported": len(fa) == len(a["search"]["finalists"]),
        "a_ranking_refused_without_expected_precision": a["ranking"]["status"] == "refused" and any(
            "expected-precision" in r for r in a["ranking"]["reasons"]),
        # the confirmation is shown as it came out: upgraded with a qualified F4 evaluation, or refused with its
        # gaps (the F4 evaluation is then unqualified and decides nothing) and never rerun after the miss
        "a_confirmation_recorded_as_is": bool(conf) and (
            (conf.get("upgrade") == "re-issued as validated-in-scope" and conf.get("fidelity") == "F4")
            or (isinstance(conf.get("upgrade"), dict) and bool(conf.get("gaps")))),
        "a_no_errors": not a["errors"],
        "b_search_ran": b["search"]["evaluations"] > 0 and bool(b["search"]["finalists"]),
        "b_unavailable_carried": len(unavailable_b) == 4 * len(b["search"]["finalists"]) and all(
            r["result"] == "inconclusive" and "capability.unavailable" in r["codes"] for r in unavailable_b),
        "b_ranking_refused": b["ranking"]["status"] == "refused",
        "b_no_errors": not b["errors"],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE / "output")
    ap.add_argument("--live-search", action="store_true", help="rerun both searches and rewrite recorded/search/")
    args = ap.parse_args(argv)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    a = run_example("A", SRC_A, out, spec_a, NS_A, "SEARCH-J16A", ["REQ-TRK-001", "REQ-CC-001"],
                    upstream={"REQ-CC-001": "REQ-TRK-001"}, confirm=True, live=args.live_search)
    b = run_example("B", SRC_B, out, spec_b, NS_B, "SEARCH-J16B", ["REQ-TRK-001", "REQ-ECAL-001"],
                    unavailable=UNAVAILABLE_B, live=args.live_search)
    passed = criteria(a, b)
    results = {"note": NOTE, "A": a, "B": b, "pass": passed}
    (out / "results.json").write_text(json.dumps(results, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pass": passed, "out": str(out)}, indent=1))
    return 0 if all(passed.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
