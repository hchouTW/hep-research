#!/usr/bin/env python3
"""G2 pilot driver (T04): each trial runs the full R2 path in its own review context. Development tool; never
imported by product code. The coordinator (Claude) dispatches the reviewers with the host's Agent tool between
`prepare` and `assign`; this script never runs a model.

  prepare --instances DIR --run DIR --store DIR --trials N   contexts, snapshots, plans, packets (predicted ids)
  assign  --run DIR --store DIR --dispatch FILE              commit assignments with the host invocation ids
  ingest  --run DIR --store DIR --declared FILE              read drop files by bytes, commit, report, export-check
  score   --run DIR --expected DIR [--grades FILE]           pre-registered scoring (frozen-protocol.md section 4)

FILE formats: --dispatch / --declared are text files of "trial_id value" lines (agent id / reported SHA-256).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-review" / "scripts"))
sys.dont_write_bytecode = True

from contracts import hep_review as H  # noqa: E402
from hep_review_support import continuity as C  # noqa: E402
from hep_review_support import coordinator as K  # noqa: E402
from hep_review_support import export as X  # noqa: E402
from hep_review_support import materials as M  # noqa: E402
from hep_review_support import store as S  # noqa: E402

AUTHOR = "pilot-generator"
CONTEXT_PREFIX = "g2"  # a later suite in its own store sets its own
STAT_Q = "Is the statistical treatment in analysis.md appropriate for the model and inputs stated there?"
COMP_Q = ("Can every number in data.json 'stated_results' be recomputed from the inputs in data.json with the method "
          "described in analysis.md, within 0.1% relative?")
ADOPT = {"second_method_required": False, "verification_required": False, "qualifications": []}


def obligations() -> list[dict]:
    common = {"targets": ["analysis.md", "data.json"], "assumptions": [], "adoption_policy": ADOPT,
              "independence_requirements": [], "required": True, "origin_requirement_ids": ["REQ-1"]}
    return [
        common | {"id": "O-stat", "question": STAT_Q, "domain_refs": ["hep-statistics"],
                  "criterion": "The uncertainty model (estimator, weights, correlations, degrees of freedom, "
                               "propagation) matches the stated model and inputs; a missing input needed to decide is "
                               "named rather than assumed.",
                  "tolerances": [], "required_methods": ["assumption-check"], "evidence_requirements": ["reasoning"],
                  "decision_required": True},
        common | {"id": "O-compute", "question": COMP_Q, "domain_refs": ["hep-computing"],
                  "criterion": "Recomputed values agree with the stated values within 0.1% relative; a disagreement "
                               "or a missing input is reported.",
                  "tolerances": [{"quantity": "stated_results", "value": "0.001", "kind": "relative"}],
                  "required_methods": ["recompute"], "evidence_requirements": ["recomputation"],
                  "decision_required": False},
    ]


def header(kind: str, oid: str, ctx: str) -> dict:
    return {"protocol": H.PROTOCOL, "schema_version": H.SCHEMA_VERSION, "record_kind": kind, "id": oid,
            "context_id": ctx}


def read_pairs(path: str) -> dict:
    out = {}
    for line in Path(path).read_text().split("\n"):
        if line.strip():
            k, v = line.split()
            out[k] = v
    return out


def state_path(run: Path, ctx: str) -> Path:
    return run / "state" / f"{ctx}.json"


def cmd_prepare(a) -> dict:
    inst, run = Path(a.instances), Path(a.run)
    store = S.Store(a.store)
    trials = []
    try:
        for d in sorted(p for p in inst.iterdir() if p.is_dir()):
            intent_src = json.loads((d / "intent.json").read_text())
            snap = M.snapshot(d / "material", ["analysis.md", "data.json"], store.dir / "blobs")
            if snap["coverage_gaps"]:
                raise RuntimeError(f"{d.name}: {snap['coverage_gaps']}")
            for t in range(1, a.trials + 1):
                ctx = f"{CONTEXT_PREFIX}-{d.name}-t{t}"
                tid = f"{d.name}-t{t}"
                st = C.start_session(store, ctx, f"pilot-{tid}")
                intent = header("intent", "intent-1", ctx) | {
                    "revision": 1, "target_tier": "R2", "minimum_requirements": intent_src["minimum_requirements"],
                    "material_scope": ["analysis.md", "data.json"],
                    "authorized_by": {"actor": "user", "basis": "declared"}}
                for m in snap["materials"]:
                    store.conn.execute("INSERT OR IGNORE INTO blobs(digest, size) VALUES(?, ?)",
                                       (m["raw_ref"]["digest"], m["capture"]["size"]))
                mats = [{k: v for k, v in m.items() if k in ("material_id", "raw_ref", "view_version",
                                                             "source_category", "capture", "limitations")}
                        | {"authors": [AUTHOR], "authors_basis": "declared"} for m in snap["materials"]]
                manifest = header("manifest", "manifest-1", ctx) | {"materials": mats}
                plan = header("plan", "plan-1", ctx) | {
                    "revision": 1, "parent_revision": None, "intent_id": "intent-1", "intent_revision": 1,
                    "manifest_id": "manifest-1", "obligations": obligations(),
                    "independence_requirements": [{"condition": c, "required": True} for c in H.FLOOR],
                    "assignment_specs": [{"id": "spec-1", "obligation_ids": ["O-stat", "O-compute"],
                                          "role": "reviewer"}],
                    "scope_scan": "performed-no-known-gaps", "judgments": [],
                    "environment_observations": [{"executor": K.load_host_profile()["reviewer_executor"],
                                                  "tools": ["python3"], "environment_refs": []}]}
                for i, o in enumerate(([intent], [manifest], [plan]), 1):
                    C.append(store, st, o, f"op-{ctx}-{i}")
                state_path(run, ctx).parent.mkdir(parents=True, exist_ok=True)
                state_path(run, ctx).write_text(st.to_json())
                aid = "asg-1"  # predicted: the first assignment of this context (checked at assign)
                text = K.packet_text({"assignment_id": aid, "obligations": obligations(),
                                      "materials": [f"{m['material_id']}: {store.dir / 'blobs' / m['raw_ref']['digest']}"
                                                    for m in mats],
                                      "drop": str(K.drop_path(run / "drops" / ctx, aid))})
                (run / "packets").mkdir(parents=True, exist_ok=True)
                (run / "packets" / f"{tid}.md").write_text(text)
                trials.append({"trial_id": tid, "instance": d.name, "trial": t, "context": ctx, "assignment": aid})
    finally:
        store.close()
    (run / "trials.json").write_text(json.dumps(trials, indent=1))
    return {"status": "ok", "trials": len(trials)}


def cmd_assign(a) -> dict:
    run = Path(a.run)
    trials = json.loads((run / "trials.json").read_text())
    ids = read_pairs(a.dispatch)
    store = S.Store(a.store)
    done = []
    try:
        for tr in trials:
            if tr["trial_id"] not in ids:
                continue
            st = C.CoordinatorState.from_json(state_path(run, tr["context"]).read_text())
            asg = K.make_assignment(store, tr["context"], K.load_host_profile(),
                                    {"via": "agent-tool", "actor": f"reviewer-{tr['trial_id']}",
                                     "authors_declared": True, "invocation_id": ids[tr["trial_id"]]},
                                    spec_id="spec-1", plan_revision=1)
            if asg["id"] != tr["assignment"]:
                raise RuntimeError(f"{tr['trial_id']}: predicted {tr['assignment']}, got {asg['id']}")
            C.append(store, st, [asg], f"op-{tr['context']}-asg")
            state_path(run, tr["context"]).write_text(st.to_json())
            done.append(tr["trial_id"])
    finally:
        store.close()
    return {"status": "ok", "assigned": len(done)}


def cmd_ingest(a) -> dict:
    run = Path(a.run)
    trials = json.loads((run / "trials.json").read_text())
    declared = read_pairs(a.declared) if a.declared else {}
    store = S.Store(a.store)
    results = {}
    try:
        for tr in trials:
            ctx, tid = tr["context"], tr["trial_id"]
            st = C.CoordinatorState.from_json(state_path(run, ctx).read_text())
            objs = [o for c in store.load_bundle(ctx)["commits"] for o in c["objects"]]
            asg = next((o for o in objs if o["record_kind"] == "assignment"), None)
            row = {"trial_id": tid, "instance": tr["instance"]}
            if asg is None:
                results[tid] = row | {"state": "not-started"}
                continue
            try:
                rec = K.ingest(store, ctx, asg, run / "drops" / ctx, declared.get(tid))
            except (M.ReadRefused, OSError) as e:
                results[tid] = row | {"state": "no-submission", "error": str(e)}
                continue
            if not rec["answers"]:
                row["state"] = "invalid-submission"
            C.append(store, st, [rec], f"op-{ctx}-rec")
            state_path(run, ctx).write_text(st.to_json())
            rep = K.report(store, st, ctx)
            (run / "exports").mkdir(exist_ok=True)
            X.export(store, ctx, run / "exports" / f"{ctx}.json")  # a third party recomputes layer 1 from this
            again = H.encode(H.project(H.validate(X.bundle_from_export(run / "exports" / f"{ctx}.json"),
                                                  H.LATEST_VALIDATOR), H.LATEST_VALIDATOR))
            l1 = rep["layer1"]
            obs = {o["id"]: o for o in l1["obligations"]}
            findings = {f["obligation_id"]: f for f in rec["findings"]}
            row |= {"state": row.get("state", "completed"), "fidelity": rec["submission_fidelity"],
                    "tier": l1["achieved_tier"], "continuity": rep["attestation"]["head_continuity"]["status"],
                    "export_recomputes": again == H.encode(l1),
                    "quarantined": l1["quarantined"],
                    "outcomes": {k: v["outcome"] for k, v in obs.items()},
                    "flags": l1["flags"], "planning_gaps": [g.get("requirement_id") for g in l1["planning_gaps"]],
                    "missing_inputs": {n["obligation_id"]: n["missing_inputs"] for n in rec["answers"]},
                    "stat_findings": [{"claim": f["claim"], "element": f["element"],
                                       "evidence_text": f.get("evidence_text", "")}
                                      for f in rec["findings"] if f["obligation_id"] == "O-stat"],
                    "any_findings": bool(findings), "summary": rep["attestation"]["output_summary"],
                    "limitations": rec["limitations"]}
            results[tid] = row
    finally:
        store.close()
    (run / "results.json").write_text(json.dumps(results, indent=1, sort_keys=True))
    return {"status": "ok", "trials": len(results),
            "states": {s: sum(r["state"] == s for r in results.values()) for s in
                       ("completed", "invalid-submission", "no-submission", "not-started")}}


C03_TERMS = ("sigma", "uncertaint", "measurement 3", "third")


def cmd_score(a) -> dict:
    run, exp_dir = Path(a.run), Path(a.expected)
    results = json.loads((run / "results.json").read_text())
    grades = json.loads(Path(a.grades).read_text()) if a.grades else {}
    rows = {}
    for tid, r in sorted(results.items()):
        exp = json.loads((exp_dir / f"{r['instance']}.json").read_text())
        typ = exp["type"]
        row = {"type": typ, "instance": r["instance"], "state": r["state"]}
        ok = None
        if r["state"] == "completed":
            out = r["outcomes"]
            if typ == "C01":
                located = out.get("O-stat") == "violated" and bool(r["stat_findings"])
                row["located"] = located
                row["evidence_grade"] = grades.get(tid)
                ok = located and grades.get(tid) == "accept"
            elif typ == "C02":
                row["false_alarm"] = r["any_findings"] or "violated" in out.values()
                ok = out.get("O-stat") == "supported" and out.get("O-compute") == "supported" and not r["any_findings"]
            elif typ == "C03":
                named = " ".join(r["missing_inputs"].get("O-stat", [])).lower()
                ok = out.get("O-stat") in ("undetermined", "not-examined") and any(t in named for t in C03_TERMS)
            elif typ == "C04":
                ok = r["flags"]["plan_requirements_met"] is False and "REQ-2" in r["planning_gaps"]
        row["success"] = bool(ok)
        rows[tid] = row
    by = {t: [x for x in rows.values() if x["type"] == t] for t in ("C01", "C02", "C03", "C04")}

    def per_instance(t):
        inst = {}
        for x in by[t]:
            inst.setdefault(x["instance"], []).append(x["success"])
        return {"instances": len(inst), "first_attempt": sum(v[0] for v in inst.values()),
                "at_least_once": sum(any(v) for v in inst.values()), "all_scheduled": sum(all(v) for v in inst.values())}
    c01_inst = per_instance("C01")
    sci = {"C01_trials_ok": sum(x["success"] for x in by["C01"]), "C01_instances_ok_at_least_once":
           c01_inst["at_least_once"], "C02_false_alarms": sum(bool(x.get("false_alarm")) or x["state"] != "completed"
                                                             for x in by["C02"]),
           "C03_trials_ok": sum(x["success"] for x in by["C03"]), "C04_trials_ok": sum(x["success"] for x in by["C04"])}
    sci["pass"] = (sci["C01_trials_ok"] >= 10 and c01_inst["at_least_once"] >= 3 and sci["C02_false_alarms"] <= 2
                   and sci["C03_trials_ok"] >= 10 and sci["C04_trials_ok"] == 12)
    completed = [r for r in results.values() if r["state"] == "completed"]
    eng = {"trials": len(results), "completed": len(completed),
           "fidelity_ok": sum(r["fidelity"] in ("digest-bound", "file-transfer") for r in completed),
           "export_recomputes": sum(r["export_recomputes"] for r in completed),
           "continuity_verified": sum(r["continuity"] == "verified" for r in completed),
           "unplanned_quarantine": sum(bool(r["quarantined"]) for r in completed)}
    eng["pass"] = (eng["completed"] == eng["trials"] == eng["fidelity_ok"] == eng["export_recomputes"]
                   == eng["continuity_verified"] and eng["unplanned_quarantine"] == 0)
    task = {"cases": len({r["instance"] for r in results.values()}), "planned": len(results),
            "states": {s: sum(r["state"] == s for r in results.values()) for s in
                       ("completed", "invalid-submission", "no-submission", "not-started")},
            "successful": sum(x["success"] for x in rows.values())}
    known = {"defect_trials": len(by["C01"]), "identified_with_valid_reason": sci["C01_trials_ok"]}
    graded = [g for g in grades.values()]
    predicted = {"C01_findings_graded": len(graded), "verified_correct": graded.count("accept"),
                 "verified_wrong": graded.count("reject"), "unadjudicated": graded.count("unsure")}
    return {"status": "ok", "task_level": task, "known_defect_level": known, "predicted_finding_level": predicted,
            "per_type_instances": {t: per_instance(t) for t in by}, "engineering_gate": eng, "scientific_gate": sci,
            "rows": rows}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prepare")
    pr.add_argument("--instances", required=True)
    pr.add_argument("--run", required=True)
    pr.add_argument("--store", required=True)
    pr.add_argument("--trials", type=int, default=3)
    asg = sub.add_parser("assign")
    asg.add_argument("--run", required=True)
    asg.add_argument("--store", required=True)
    asg.add_argument("--dispatch", required=True)
    ig = sub.add_parser("ingest")
    ig.add_argument("--run", required=True)
    ig.add_argument("--store", required=True)
    ig.add_argument("--declared")
    sc = sub.add_parser("score")
    sc.add_argument("--run", required=True)
    sc.add_argument("--expected", required=True)
    sc.add_argument("--grades")
    a = p.parse_args(argv)
    out = {"prepare": cmd_prepare, "assign": cmd_assign, "ingest": cmd_ingest, "score": cmd_score}[a.cmd](a)
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
