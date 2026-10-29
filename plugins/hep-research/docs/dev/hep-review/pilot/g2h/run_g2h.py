#!/usr/bin/env python3
"""Held-out G2 follow-up driver ("g2h", g2h/frozen-protocol.md). Reuses the G2 driver's R2 path (`run_pilot.py`
prepare / assign / ingest) with a criterion text that names no defect class, and scores with this suite's
pre-registered rules. Development tool; never imported by product code; never runs a model.

  prepare | assign | ingest   as in run_pilot.py (contexts are g2h-<instance>-t<k>)
  score --run DIR --expected DIR [--grades FILE]   only after the seed holder has revealed the gold
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_pilot as P  # noqa: E402

STAT_CRITERION = ("The statistical treatment is appropriate for the stated model and inputs and the stated results "
                  "follow from it; a missing input needed to decide is named rather than assumed.")
TYPES = ("C01", "C02", "C03", "C04")
UNDECIDED = ("undetermined", "not-examined")


def obligations() -> list[dict]:
    rows = P.G2_OBLIGATIONS()
    for o in rows:
        if o["id"] == "O-stat":
            o["criterion"] = STAT_CRITERION
    return rows


P.G2_OBLIGATIONS, P.obligations, P.CONTEXT_PREFIX = P.obligations, obligations, "g2h"


def trial_success(typ: str, exp: dict, r: dict, grade: str | None) -> tuple[bool, dict]:
    out = r["outcomes"]
    if typ == "C01":
        located = out.get("O-stat") == "violated" and bool(r["stat_findings"])
        return located and grade == "accept", {"located": located, "evidence_grade": grade}
    if typ == "C02":
        alarm = r["any_findings"] or "violated" in out.values()
        return (out.get("O-stat") == "supported" and out.get("O-compute") == "supported" and not r["any_findings"],
                {"false_alarm": alarm, "variant": exp["variant"]})
    if typ == "C03":
        named = " ".join(m for v in r["missing_inputs"].values() for m in v).lower()
        named_ok = any(k in named for k in exp["keywords"])
        kept = out.get("O-compute") != "supported" and any(out.get(o) in UNDECIDED for o in ("O-stat", "O-compute"))
        return kept and named_ok, {"gap_kept": kept, "input_named": named_ok, "outcomes": out}
    return (r["flags"]["plan_requirements_met"] is False and "REQ-2" in r["planning_gaps"]), {}


def cmd_score(a) -> dict:
    run, exp_dir = Path(a.run), Path(a.expected)
    results = json.loads((run / "results.json").read_text())
    grades = json.loads(Path(a.grades).read_text()) if a.grades else {}
    rows = {}
    for tid, r in sorted(results.items()):
        exp = json.loads((exp_dir / f"{r['instance']}.json").read_text())
        row = {"type": exp["type"], "family": exp["family"], "instance": r["instance"], "state": r["state"]}
        ok = False
        if r["state"] == "completed":
            ok, extra = trial_success(exp["type"], exp, r, grades.get(tid))
            row |= extra
        elif exp["type"] == "C02":
            row["false_alarm"] = True  # a control without a usable record is not a well-founded supported
        row["success"] = bool(ok)
        rows[tid] = row
    by = {t: [x for x in rows.values() if x["type"] == t] for t in TYPES}

    def per_instance(xs):
        inst: dict = {}
        for x in xs:
            inst.setdefault(x["instance"], []).append(x["success"])
        return {"instances": len(inst), "first_attempt": sum(v[0] for v in inst.values()),
                "at_least_once": sum(any(v) for v in inst.values()), "all_scheduled": sum(all(v) for v in inst.values())}
    families = sorted({x["family"] for x in rows.values()})
    sci = {"C01_trials_ok": sum(x["success"] for x in by["C01"]),
           "C01_instances_ok_at_least_once": per_instance(by["C01"])["at_least_once"],
           "C02_false_alarms": sum(bool(x.get("false_alarm")) for x in by["C02"]),
           "C02_false_alarms_alternative_method": sum(bool(x.get("false_alarm")) for x in by["C02"]
                                                      if x.get("variant") == "alternative"),
           "C03_trials_ok": sum(x["success"] for x in by["C03"]), "C04_trials_ok": sum(x["success"] for x in by["C04"])}
    sci["pass"] = (sci["C01_trials_ok"] >= 12 and sci["C01_instances_ok_at_least_once"] >= 4
                   and sci["C02_false_alarms"] <= 3 and sci["C03_trials_ok"] >= 7 and sci["C04_trials_ok"] == 6)
    completed = [r for r in results.values() if r["state"] == "completed"]
    eng = {"trials": len(results), "completed": len(completed),
           "fidelity_ok": sum(r["fidelity"] in ("digest-bound", "file-transfer") for r in completed),
           "export_recomputes": sum(r["export_recomputes"] for r in completed),
           "continuity_verified": sum(r["continuity"] == "verified" for r in completed),
           "unplanned_quarantine": sum(bool(r["quarantined"]) for r in completed)}
    eng["pass"] = (eng["completed"] == eng["trials"] == eng["fidelity_ok"] == eng["export_recomputes"]
                   == eng["continuity_verified"] and eng["unplanned_quarantine"] == 0)
    graded = list(grades.values())
    return {"status": "ok",
            "task_level": {"cases": len({r["instance"] for r in results.values()}), "planned": len(results),
                           "states": {s: sum(r["state"] == s for r in results.values()) for s in
                                      ("completed", "invalid-submission", "no-submission", "not-started")},
                           "successful": sum(x["success"] for x in rows.values())},
            "known_defect_level": {"defect_trials": len(by["C01"]), "identified_with_valid_reason": sci["C01_trials_ok"]},
            "predicted_finding_level": {"C01_findings_graded": len(graded), "verified_correct": graded.count("accept"),
                                        "verified_wrong": graded.count("reject"),
                                        "unadjudicated": graded.count("unsure") + graded.count("unstable")},
            "per_type_instances": {t: per_instance(by[t]) for t in TYPES},
            "per_family": {f: {t: [x["success"] for x in by[t] if x["family"] == f] for t in TYPES} for f in families},
            "engineering_gate": eng, "scientific_gate": sci, "rows": rows}


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "score":
        p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
        p.add_argument("cmd")
        p.add_argument("--run", required=True)
        p.add_argument("--expected", required=True)
        p.add_argument("--grades")
        print(json.dumps(cmd_score(p.parse_args(argv)), indent=1, sort_keys=True))
        return 0
    return P.main(argv)


if __name__ == "__main__":
    sys.exit(main())
