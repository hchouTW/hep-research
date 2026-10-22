#!/usr/bin/env python3
"""Value gate of the cross-artifact analysis check (Phase 1, DR-13; plugin record
docs/dev/cross-artifact-check/decision-value-gate.md). Scores planted errors and legitimate refactors layer by layer.

Subject: examples/ams-flux-ratio/run.py (the code; it also writes the spec, responses and dataset records) plus the
hand-written descriptions in subject/ (recipe.json, context.json). A case is a folder under --cases holding key.json
and any of run.py, recipe.json, context.json; a missing file means the baseline one. Per case:

  layer 1  closure: the case's run.py, run from a shadow plugin root (symlinks to the plugin, the case's run.py in
           examples/ams-flux-ratio/); flagged when it crashes or exits non-zero (a pre-declared criterion failed)
  layer 2  contracts/validate.py --strict on the produced artifacts (experiment:ams-02 bound) and
           contracts/recipe_semantics.py on the recipe (L2); flagged when either is not ok
  layer 3  the checker: freeze (contracts.analysis_check.freeze) and check (CLI, suites counting-chain and
           ratio-subset 1.0.0) against the baseline report. Flagged when freeze refuses, the check reports invalid
           input, an obligation becomes violated, or an obligation becomes unverified or unsupported (from satisfied,
           not_applicable or absent) and its obligation_id names an id of key.json 'affected'

An error is an incremental detection when layer 3 flags it and layers 1 and 2 do not. A refactor counts towards F
when layer 3 reports a new violated obligation. Definition-induced results are in the baseline and never count.
--sensitivity repeats layer 3 with a bundle-supplied coverage contract whose correct_efficiency covers both
efficiency members (flagged by A3); it is reported separately and never decides the gate.

Usage: python3 evals/cross-artifact-value-gate/measure.py --cases DIR --out DIR [--only ID ...] [--sensitivity]
Exit 0 measured, 2 bad input. Output: <out>/results.json and <out>/results.md; work files in <out>/work/.
The checker's outputs are advisory diagnostics (HC-05); this script measures them and authorizes nothing.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins" / "hep-research"
SUBJECT = HERE / "subject"
EXAMPLE = PLUGIN / "examples" / "ams-flux-ratio" / "run.py"
TABLE = PLUGIN / "contracts" / "semantics" / "tables" / "differential_flux.json"
SPECIES, PERIODS = ("proton", "helium"), ("synthetic-period-1", "synthetic-period-2")
SHORT = {"synthetic-period-1": "p1", "synthetic-period-2": "p2"}
TIMEOUT = 600
THRESHOLDS = "Pass I >= 0.25 N and F <= 1; Shrink 0.10 N <= I < 0.25 N, or I >= 0.25 N with F = 2; Stop I < 0.10 N or F >= 3"

sys.path.insert(0, str(PLUGIN))


def load(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {TIMEOUT}s"


def case_file(case: Path | None, name: str) -> Path:
    return case / name if case is not None and (case / name).is_file() else (EXAMPLE if name == "run.py" else SUBJECT / name)


def shadow_root(work: Path, run_py: Path) -> Path:
    """A plugin root of symlinks whose examples/ams-flux-ratio/run.py is the case's copy (run.py finds the plugin as
    the parents[2] of its own path)."""
    root = work / "plugin"
    root.mkdir(parents=True)
    for entry in PLUGIN.iterdir():
        if entry.name not in ("examples", ".in_use"):
            (root / entry.name).symlink_to(entry)
    ex = root / "examples" / "ams-flux-ratio"
    ex.mkdir(parents=True)
    shutil.copy2(run_py, ex / "run.py")
    return root


def layer1(case, work: Path) -> dict:
    root = shadow_root(work, case_file(case, "run.py"))
    out = work / "run-out"
    code, log = run([sys.executable, str(root / "examples" / "ams-flux-ratio" / "run.py"), "--out", str(out)])
    (work / "run.log").write_text(log, encoding="utf-8")
    res = out / "results.json"
    failed = sorted(k for k, v in (load(res).get("pass") or {}).items() if not v) if res.is_file() else []
    crashed = not (out / "artifacts" / "measurement_spec.json").is_file()
    return {"flag": code != 0, "exit": code, "failed_criteria": failed, "crashed": crashed, "artifacts": str(out / "artifacts")}


def project_config(work: Path) -> Path:
    version = load(PLUGIN / "profiles" / "experiments" / "ams-02" / "profile.json")["version"]
    p = work / "project" / "hep-research.project.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0",
                             "experiments": [{"profile": "experiment:ams-02", "version": version}]}), encoding="utf-8")
    return p


def layer2(case, work: Path, artifacts: Path) -> dict:
    out = {}
    if artifacts.is_dir():
        code, log = run([sys.executable, str(PLUGIN / "contracts" / "validate.py"), str(artifacts),
                         "--profiles-from", str(project_config(work)), "--strict"])
        out["validate"] = {"exit": code, "codes": sorted(set(re.findall(r'"code": "([^"]+)"', log)))}
    else:
        out["validate"] = {"exit": None, "codes": ["no artifacts (layer 1 crashed)"]}
    code, log = run([sys.executable, str(PLUGIN / "contracts" / "recipe_semantics.py"), str(case_file(case, "recipe.json")),
                     "--table", str(TABLE)])
    out["l2"] = {"exit": code, "codes": sorted(set(re.findall(r'"code": "([^"]+)"', log)))}
    out["flag"] = out["validate"]["exit"] not in (0, None) or out["l2"]["exit"] != 0
    return out


def efficiency_coverage(items: list, context: dict, recipe: dict, project: Path) -> None:
    """Sensitivity variant: a bundle-supplied table copy and coverage contract in which correct_efficiency covers both
    efficiency members (the A3 flag applies)."""
    from contracts.effect_catalog import load_coverage
    from contracts.recipe_semantics import canonical_sha256
    table = load(TABLE)
    table["table_id"] = "differential-flux-vg"
    (project / "tables" / "differential_flux_vg.json").write_text(json.dumps(table, indent=1), encoding="utf-8")
    recipe["semantics"] = {"table_id": "differential-flux-vg", "sha256": canonical_sha256(table)}
    cov = copy.deepcopy(load_coverage("differential-flux"))
    cov.update(table_id="differential-flux-vg", table_sha256=canonical_sha256(table))
    for op in cov["operators"]:
        if op["operator_id"] == "correct_efficiency":
            op.setdefault("class_coverage", {})["efficiency"] = {
                "members": ["trigger_efficiency", "selection_efficiency"],
                "basis": "sensitivity run: run.py divides by the trigger and the selection efficiency in one step"}
    (project / "tables" / "differential_flux_vg.coverage.json").write_text(json.dumps(cov, indent=1), encoding="utf-8")
    items[:] = [i for i in items if i["role"] != "semantics-table"]
    items += [{"role": "semantics-table", "id": "differential-flux-vg", "ref": "tables/differential_flux_vg.json"},
              {"role": "coverage-contract", "id": "differential-flux-vg-coverage", "ref": "tables/differential_flux_vg.coverage.json"}]


def layer3(case, work: Path, artifacts: Path, sensitivity: bool) -> dict:
    from contracts import analysis_check as ac
    from contracts.analysis_bundle import BundleRefused
    name = "checker-sens" if sensitivity else "checker"
    project = work / name
    if not artifacts.is_dir():
        return {"status": "no-artifacts", "report": None}
    shutil.copytree(artifacts, project / "artifacts")
    (project / "recipes").mkdir()
    (project / "tables").mkdir()
    recipe = load(case_file(case, "recipe.json"))
    context = load(case_file(case, "context.json"))
    shutil.copy2(TABLE, project / "tables" / "differential_flux.json")
    (project / "environment.lock").write_text("synthetic environment lock for the value-gate subject\n", encoding="utf-8")
    items = [{"role": "measurement-spec", "id": "spec", "ref": "artifacts/measurement_spec.json"},
             {"role": "recipe", "id": recipe.get("recipe_id", "recipe"), "ref": "recipes/recipe.json"},
             {"role": "semantics-table", "id": "differential-flux", "ref": "tables/differential_flux.json"},
             {"role": "environment-lock", "id": "env", "ref": "environment.lock"}]
    items += [{"role": "response", "id": f"response-{s}-{SHORT[p]}", "ref": f"artifacts/response_{s}_{p}.json"}
              for s in SPECIES for p in PERIODS if (project / "artifacts" / f"response_{s}_{p}.json").is_file()]
    items += [{"role": "dataset-record", "id": f"dataset-{SHORT[p]}", "ref": f"artifacts/dataset_{p}.json"}
              for p in PERIODS if (project / "artifacts" / f"dataset_{p}.json").is_file()]
    if sensitivity:
        efficiency_coverage(items, context, recipe, project)
    (project / "recipes" / "recipe.json").write_text(json.dumps(recipe, indent=1), encoding="utf-8")
    try:
        bundle = ac.freeze(project, "value-gate", items, context)
    except BundleRefused as exc:
        return {"status": "refused", "refusal": str(exc), "report": None}
    except Exception as exc:  # a malformed draft the freeze cannot read is a refusal too
        return {"status": "refused", "refusal": f"{type(exc).__name__}: {exc}", "report": None}
    (project / "bundle.json").write_text(json.dumps(bundle, indent=1), encoding="utf-8")
    code, log = run([sys.executable, str(PLUGIN / "contracts" / "analysis_check.py"), "check", str(project / "bundle.json"),
                     "--root", str(project), "--out", str(project / "report.json")])
    rep = project / "report.json"
    if not rep.is_file():
        return {"status": "no-report", "exit": code, "log": log[-2000:], "report": None}
    r = load(rep)
    return {"status": r.get("status"), "exit": code, "input_validity": r.get("input_validity"), "counts": r.get("counts"),
            "report": str(rep), "obligations": {o["obligation_id"]: o["state"] for o in r.get("obligations", [])},
            "reasons": {o["obligation_id"]: o.get("reason") for o in r.get("obligations", [])}}


def changes(base: dict, now: dict) -> list[dict]:
    b, n = base.get("obligations") or {}, now.get("obligations") or {}
    out = []
    for oid, st in sorted(n.items()):
        old = b.get(oid)
        if st == "violated" and old != "violated":
            out.append({"obligation_id": oid, "from": old, "to": st, "reason": now["reasons"].get(oid)})
        elif st in ("unverified", "unsupported") and old in (None, "satisfied", "not_applicable"):
            out.append({"obligation_id": oid, "from": old, "to": st, "reason": now["reasons"].get(oid)})
    return out


def names_affected(oid: str, affected: list[str]) -> bool:
    return any(re.search(rf"(?<![A-Za-z0-9_]){re.escape(a)}(?![A-Za-z0-9_])", oid) for a in affected if a)


def judge(l3: dict, base: dict, key: dict) -> dict:
    if l3["status"] in ("refused", "no-report"):
        return {"flag": True, "why": l3["status"], "changes": []}
    if l3["status"] == "no-artifacts":
        return {"flag": False, "why": "no-artifacts", "changes": []}
    if l3.get("input_validity") not in (None, "valid"):
        return {"flag": True, "why": f"input {l3.get('input_validity')}", "changes": []}
    ch = changes(base, l3)
    violated = [c for c in ch if c["to"] == "violated"]
    named = [c for c in ch if c["to"] != "violated" and names_affected(c["obligation_id"], key.get("affected", []))]
    why = "new violated" if violated else ("new unverified naming the defect" if named else "")
    return {"flag": bool(violated or named), "why": why, "changes": ch, "new_violated": len(violated)}


def measure(case: Path | None, cid: str, out: Path, base3: dict | None, base3s: dict | None, sens: bool) -> dict:
    work = out / "work" / cid
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    key = load(case / "key.json") if case is not None else {"kind": "baseline", "affected": []}
    l1 = layer1(case, work)
    art = Path(l1["artifacts"])
    l2 = layer2(case, work, art)
    l3 = layer3(case, work, art, False)
    row = {"id": cid, "kind": key.get("kind"), "category": key.get("category"), "layer1": l1, "layer2": l2,
           "layer3": {k: v for k, v in l3.items() if k not in ("obligations", "reasons")}}
    if base3 is not None:
        row["layer3"]["judgement"] = judge(l3, base3, key)
    if sens:
        l3s = layer3(case, work, art, True)
        row["sensitivity"] = {k: v for k, v in l3s.items() if k not in ("obligations", "reasons")}
        if base3s is not None:
            row["sensitivity"]["judgement"] = judge(l3s, base3s, key)
    row["_l3"], row["_l3s"] = l3, (l3s if sens else None)
    return row


def outcome(n: int, i: int, f: int, human: int) -> str:
    if i < 0.10 * n or f >= 3:
        res = "Stop"
    elif i >= 0.25 * n and f <= 1:
        res = "Pass"
    else:
        res = "Shrink"
    if res == "Pass" and human < 10:
        return "Shrink (AI-planted cap; the uncapped condition is Pass)"
    return res


def summarise(rows: list[dict], sens: bool) -> dict:
    def tally(arm: str) -> dict:
        errs = [r for r in rows if r["kind"] == "error"]
        refs = [r for r in rows if r["kind"] == "refactor"]
        j = (lambda r: r[arm]["judgement"]) if arm == "sensitivity" else (lambda r: r["layer3"]["judgement"])
        inc = [r["id"] for r in errs if j(r)["flag"] and not r["layer1"]["flag"] and not r["layer2"]["flag"]]
        fpos = [r["id"] for r in refs if j(r).get("new_violated", 0) > 0 or j(r)["why"] in ("refused", "no-report")]
        n, i, f = len(errs), len(inc), len(fpos)
        human = sum(1 for r in errs if r.get("planter") == "human")
        return {"N": n, "R": len(refs), "I": i, "F": f, "incremental": inc, "false_positive_refactors": fpos,
                "layer1": sum(r["layer1"]["flag"] for r in errs), "layer2_only": sum(r["layer2"]["flag"] and not r["layer1"]["flag"] for r in errs),
                "checker_any": sum(j(r)["flag"] for r in errs), "missed_by_all": [r["id"] for r in errs if not (
                    r["layer1"]["flag"] or r["layer2"]["flag"] or j(r)["flag"])],
                "refactor_layer1_alarms": [r["id"] for r in refs if r["layer1"]["flag"]],
                "refactor_layer2_alarms": [r["id"] for r in refs if r["layer2"]["flag"]],
                "outcome": outcome(n, i, f, human) if n else "no errors measured"}
    out = {"main": tally("layer3"), "thresholds": THRESHOLDS, "planter": "AI-planted"}
    if sens:
        out["sensitivity"] = tally("sensitivity")
    return out


def write_md(path: Path, res: dict) -> None:
    m = res["summary"]["main"]
    lines = ["# Value-gate measurement", "", f"Planter: {res['summary']['planter']}. Thresholds: {res['summary']['thresholds']}.", "",
             "| Arm | N | R | I | F | layer 1 | layer 2 only | checker (any) | outcome |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for arm in ("main", "sensitivity"):
        if arm in res["summary"]:
            a = res["summary"][arm]
            lines.append(f"| {arm} | {a['N']} | {a['R']} | {a['I']} | {a['F']} | {a['layer1']} | {a['layer2_only']} | {a['checker_any']} | {a['outcome']} |")
    lines += ["", f"Incremental detections: {', '.join(m['incremental']) or 'none'}.",
              f"False-positive refactors: {', '.join(m['false_positive_refactors']) or 'none'}.",
              f"Missed by every layer: {', '.join(m['missed_by_all']) or 'none'}.", "",
              "| Case | Kind | Category | L1 | L2 | Checker | Checker why | Sens. |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in res["cases"]:
        j = r["layer3"].get("judgement", {})
        s = r.get("sensitivity", {}).get("judgement", {})
        lines.append(f"| {r['id']} | {r['kind']} | {r.get('category') or ''} | {'x' if r['layer1']['flag'] else ''} | "
                     f"{'x' if r['layer2']['flag'] else ''} | {'x' if j.get('flag') else ''} | {j.get('why', '')} | "
                     f"{'x' if s.get('flag') else ''} |")
    lines += ["", "Checker outcomes are advisory diagnostics (HC-05); a flag is a measurement, not a verdict on the analysis."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--sensitivity", action="store_true")
    a = ap.parse_args(argv)
    if not a.cases.is_dir():
        print(json.dumps({"status": "usage", "error": f"no cases folder {a.cases}"}))
        return 2
    cases = sorted(p for p in a.cases.iterdir() if (p / "key.json").is_file() and (not a.only or p.name in a.only))
    a.out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    base = measure(None, "baseline", a.out, None, None, a.sensitivity)
    if base["layer1"]["flag"] or base["layer2"]["flag"]:
        print(json.dumps({"status": "error", "error": "the baseline fails layer 1 or 2", "baseline": base["layer1"] | base["layer2"]}, default=str))
        return 2
    rows = []
    for c in cases:
        row = measure(c, c.name, a.out, base["_l3"], base["_l3s"], a.sensitivity)
        row["planter"] = load(c / "key.json").get("planter", "ai")
        rows.append(row)
    for r in [base] + rows:
        r.pop("_l3"), r.pop("_l3s")
    res = {"status": "ok", "baseline": base, "cases": rows, "summary": summarise(rows, a.sensitivity)}
    (a.out / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    write_md(a.out / "results.md", res)
    print(json.dumps({"status": "ok", "summary": res["summary"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
