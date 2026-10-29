#!/usr/bin/env python3
"""Codex-authored held-out suite driver ("g2x", g2x/frozen-protocol.md). The R2 path and criterion are those of
g2h (`run_g2h.py`); grading is cross-family (two Claude graders in swapped order plus one Codex grader) and the
scoring handles several defects per instance. Development tool; never imported by product code; never runs a model.

  prepare | assign | ingest                       as in run_pilot.py (contexts g2x-<instance>-t<k>)
  items   --run DIR --gold DIR --calibration DIR --out DIR   grader items, after the gold is restored
  combine --out DIR                               merge the three graders' files in OUT/grades/
  score   --run DIR --gold DIR --combined FILE
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "g2h"))
import run_g2h  # noqa: E402,F401  (installs the uncued criterion)
import run_pilot as P  # noqa: E402

P.CONTEXT_PREFIX = "g2x"
TYPES = ("C01", "C02", "C03", "C04")
UNDECIDED = ("undetermined", "not-examined")
GRADERS = ("claude-forward", "claude-reverse", "codex")


def gold_of(gold_dir: Path, iid: str) -> dict:
    return json.loads((gold_dir / f"{iid}.json").read_text())


def finding_view(f: dict) -> dict:
    return {"obligation": f["obligation_id"], "claim": f["claim"], "element": f["element"],
            "evidence_text": f["evidence_text"]}


def cmd_items(a) -> dict:
    results = json.loads((Path(a.run) / "results.json").read_text())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    items, key = [], {}
    for tid, r in sorted(results.items()):
        g = gold_of(Path(a.gold), r["instance"])
        if g["type"] != "C01" or r["state"] != "completed":
            continue
        for d in g["defects"]:
            iid = f"D{len(key) + 1:03d}"
            key[iid] = {"kind": "defect", "trial": tid, "defect_id": d["defect_id"]}
            items.append({"item": iid, "kind": "defect", "defect": d["statement"],
                          "findings": [finding_view(f) for f in r["findings"]]})
        for k, f in enumerate(r["findings"]):
            iid = f"F{len(key) + 1:03d}"
            key[iid] = {"kind": "finding", "trial": tid, "finding_index": k}
            items.append({"item": iid, "kind": "finding", "finding": finding_view(f),
                          "defects": {d["defect_id"]: d["statement"] for d in g["defects"]}})
    random.Random("g2x-grader-order").shuffle(items)  # fixed, pre-registered order
    cal = json.loads((Path(a.calibration) / "items.json").read_text())
    cal_items = [{"item": c["item"], "kind": "defect", "defect": c["defect"], "findings": [c["finding"]]} for c in cal]
    (out / "items-forward.json").write_text(json.dumps(items, indent=1))
    (out / "items-reverse.json").write_text(json.dumps(list(reversed(items)), indent=1))
    (out / "items-key.json").write_text(json.dumps(key, indent=1, sort_keys=True))
    (out / "calibration-items.json").write_text(json.dumps(cal_items, indent=1))
    (out / "grades").mkdir(exist_ok=True)
    return {"status": "ok", "items": len(items), "calibration_items": len(cal_items)}


def cmd_combine(a) -> dict:
    out = Path(a.out)
    key = json.loads((out / "items-key.json").read_text())
    labels = json.loads((Path(a.calibration) / "labels.json").read_text())
    calibrated = {}
    for g in GRADERS:
        cal = json.loads((out / "grades" / f"calibration-{g}.json").read_text())
        wrong = [k for k, v in labels.items() if not k.startswith("_") and cal.get(k, {}).get("grade") != v]
        calibrated[g] = {"pass": not wrong, "mismatched": wrong}
    grades = {g: json.loads((out / "grades" / f"scoring-{g}.json").read_text()) for g in GRADERS}
    combined, disagreements = {}, 0
    for iid in key:
        votes = [grades[g].get(iid, {}).get("grade") for g in GRADERS]
        if len(set(votes)) == 1 and votes[0] not in (None, "unsure"):
            combined[iid] = votes[0]
        else:
            combined[iid] = "unadjudicated"
            disagreements += len(set(votes)) > 1
    record = {"calibration": calibrated, "all_calibrated": all(c["pass"] for c in calibrated.values()),
              "items": combined, "disagreements": disagreements}
    (out / "combined.json").write_text(json.dumps(record, indent=1, sort_keys=True))
    return {"status": "ok", "all_calibrated": record["all_calibrated"], "disagreements": disagreements,
            "unadjudicated": sum(v == "unadjudicated" for v in combined.values())}


def cmd_score(a) -> dict:
    results = json.loads((Path(a.run) / "results.json").read_text())
    comb = json.loads(Path(a.combined).read_text())
    key = json.loads((Path(a.combined).parent / "items-key.json").read_text())
    verdict = {(k["trial"], k["defect_id"]): comb["items"][iid] for iid, k in key.items() if k["kind"] == "defect"}
    fverdict = [(k["trial"], comb["items"][iid]) for iid, k in key.items() if k["kind"] == "finding"]
    rows, defect_rows = {}, []
    for tid, r in sorted(results.items()):
        g = gold_of(Path(a.gold), r["instance"])
        typ = g["type"]
        row = {"type": typ, "instance": r["instance"], "state": r["state"], "success": False}
        if r["state"] == "completed":
            out = r["outcomes"]
            if typ == "C01":
                flagged = "violated" in out.values() and bool(r["findings"])
                hits = {d["defect_id"]: flagged and comb["all_calibrated"] and verdict.get((tid, d["defect_id"])) == "accept"
                        for d in g["defects"]}
                for d in g["defects"]:
                    defect_rows.append({"trial": tid, "instance": r["instance"], "defect_id": d["defect_id"],
                                        "detected": hits[d["defect_id"]],
                                        "unadjudicated": verdict.get((tid, d["defect_id"])) == "unadjudicated"})
                row |= {"defects": len(hits), "detected": sum(hits.values()), "success": all(hits.values())}
            elif typ in ("C02",):
                row["false_alarm"] = bool(r["findings"]) or "violated" in out.values()
                row["success"] = not row["false_alarm"] and out.get("O-stat") == out.get("O-compute") == "supported"
            elif typ == "C03":
                named = " ".join(m for v in r["missing_inputs"].values() for m in v).lower()
                kept = out.get("O-compute") != "supported" and any(out.get(o) in UNDECIDED for o in ("O-stat", "O-compute"))
                row |= {"gap_kept": kept, "success": kept and any(k in named for k in g["keywords"])}
            else:
                row["success"] = r["flags"]["plan_requirements_met"] is False and "REQ-2" in r["planning_gaps"]
        elif typ == "C02":
            row["false_alarm"] = True
        rows[tid] = row
    by = {t: [x for x in rows.values() if x["type"] == t] for t in TYPES}

    def per_instance(xs):
        inst: dict = {}
        for x in xs:
            inst.setdefault(x["instance"], []).append(x["success"])
        return {"instances": len(inst), "first_attempt": sum(v[0] for v in inst.values()),
                "at_least_once": sum(any(v) for v in inst.values()), "all_scheduled": sum(all(v) for v in inst.values())}
    detected = sum(d["detected"] for d in defect_rows)
    sci = {"defect_trials": len(defect_rows), "defect_trials_detected": detected,
           "defect_trials_unadjudicated": sum(d["unadjudicated"] for d in defect_rows),
           "C01_instances_all_defects_at_least_once": per_instance(by["C01"])["at_least_once"],
           "C02_false_alarms": sum(bool(x.get("false_alarm")) for x in by["C02"]),
           "C03_trials_ok": sum(x["success"] for x in by["C03"]), "C04_trials_ok": sum(x["success"] for x in by["C04"]),
           "graders_calibrated": comb["all_calibrated"]}
    sci["pass"] = (comb["all_calibrated"] and detected >= 0.8 * len(defect_rows)
                   and sci["C01_instances_all_defects_at_least_once"] >= 6 and sci["C02_false_alarms"] <= 2
                   and sci["C03_trials_ok"] >= 5 and sci["C04_trials_ok"] == len(by["C04"]))
    completed = [r for r in results.values() if r["state"] == "completed"]
    eng = {"trials": len(results), "completed": len(completed),
           "fidelity_ok": sum(r["fidelity"] in ("digest-bound", "file-transfer") for r in completed),
           "export_recomputes": sum(r["export_recomputes"] for r in completed),
           "continuity_verified": sum(r["continuity"] == "verified" for r in completed),
           "unplanned_quarantine": sum(bool(r["quarantined"]) for r in completed)}
    eng["pass"] = (eng["completed"] == eng["trials"] == eng["fidelity_ok"] == eng["export_recomputes"]
                   == eng["continuity_verified"] and eng["unplanned_quarantine"] == 0)
    fv = [v for _, v in fverdict]
    return {"status": "ok",
            "task_level": {"cases": len({r["instance"] for r in results.values()}), "planned": len(results),
                           "states": {s: sum(r["state"] == s for r in results.values()) for s in
                                      ("completed", "invalid-submission", "no-submission", "not-started")},
                           "successful": sum(x["success"] for x in rows.values())},
            "known_defect_level": {"defect_trials": len(defect_rows), "identified_with_valid_reason": detected,
                                   "unadjudicated": sci["defect_trials_unadjudicated"]},
            "predicted_finding_level": {"C01_findings": len(fv),
                                        "matched_a_gold_defect": sum(v.startswith("D") for v in fv),
                                        "outside_gold_unadjudicated": fv.count("none"),
                                        "grader_disagreement_unadjudicated": fv.count("unadjudicated")},
            "per_type_instances": {t: per_instance(by[t]) for t in TYPES},
            "engineering_gate": eng, "scientific_gate": sci, "defect_rows": defect_rows, "rows": rows}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ("items", "combine", "score"):
        return P.main(argv)
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("cmd")
    p.add_argument("--run")
    p.add_argument("--gold")
    p.add_argument("--calibration")
    p.add_argument("--out")
    p.add_argument("--combined")
    a = p.parse_args(argv)
    print(json.dumps({"items": cmd_items, "combine": cmd_combine, "score": cmd_score}[a.cmd](a), indent=1,
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
