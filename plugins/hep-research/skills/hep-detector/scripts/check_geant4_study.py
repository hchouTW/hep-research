#!/usr/bin/env python3
"""Check a Geant4 study: spec completeness and physics rules, run records against the spec, the convergence gate,
model variations, and the study record (phase 1: always `unvalidated`).

Purpose: the hep-detector side of a Geant4 study (protocol: <plugin root>/skills/hep-detector/references/
geant4-study-protocol.md). A completed run is not a validated result; agreement with official examples is only
verification. This script never runs Geant4 and never imports the adapter: it reads the files adapters/geant4 writes.
Subcommands:
  spec        completeness of the study spec (assets/geant4-study-spec.schema.json) and the sourced rule table
              (assets/geant4-physics-rules.json; a rule without a source is refused); reports the rule coverage.
              Exit 1 when the observable, statistical target or validation scope is missing or an error rule fires.
  summarize   per-run observables from a layered_sim CSV (mean deposit, tail fraction, most probable deposit and
              energy loss, with seeded-bootstrap standard errors), tied to the run record by hash.
  run         run records against the spec (physics, gun, geometry, spec hash, data paths and dataset hashes), the
              statistical target (bootstrap SE, not only rms/sqrt(N); too few events gives the N needed), and the
              convergence gate (hard): across each declared cut or step-limit scan, every declared observable changes
              by no more than its tolerance between the two finest settings, with the difference resolved (SE of the
              difference <= tolerance / 2). This is the only place a too-coarse cut is caught.
  variations  a variation table: each variation's model assignment for the particle and energy (EM constructor and
              fluctuation model for EM observables; the hadronic model in use for hadronic ones); a variation that
              keeps the model is excluded, never listed as a systematic; the spread is a model envelope, not a sigma.
  label       the highest usable label (phase 1: `unvalidated`, plus every propagating label of the inputs), the gaps,
              and the scopes that phase 2 could upgrade; --write writes the study record, a computational-run whose
              inputs are the run records and reference dataset-records (statuses declared, sha256), with the
              benchmarks, convergence, variations and scope embedded. Insufficient evidence still writes the record,
              listing the gaps; only invalid input is refused (exit 2).
Usage (paths relative to the current folder):
  check_geant4_study.py spec --spec STUDY.json [--rules RULES.json]
  check_geant4_study.py summarize --record RUN.json --csv EVENTS.csv[.gz] --slab NAME --out SUMMARY.json [--bootstrap 200 --seed 1]
  check_geant4_study.py run --spec STUDY.json --summary SUMMARY.json [...] [--out CONVERGENCE.json]
  check_geant4_study.py variations --spec STUDY.json --nominal SUMMARY.json --variation NAME=SUMMARY.json [...] --out VARIATIONS.json
  check_geant4_study.py label --spec STUDY.json --benchmarks BENCH.json --convergence CONV.json [--variations VAR.json]
                        --project-root ROOT [--reference-record DATASET.json ...] [--write STUDY_RECORD.json] [--created DATE]
Output JSON: status, status_label, inputs, defaults_used and the subcommand's result.
Exit codes: 0 ok (label: the record was written or evaluated); 1 a negative verdict (missing required fields, an
error rule, a record that disagrees with the spec, too few events, an unconverged scan); 2 bad input; 3 incomplete.
Standard library only.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geant4_benchmarks as B  # noqa: E402  (sibling: one MPV estimator, CSV reader and bootstrap for both scripts)
from contracts import CONTRACTS_VERSION  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

STATUSES = ("failed", "unvalidated", "preliminary", "synthetic", "asimov", "observed", "user-supplied",
            "validated-in-scope", "projection", "outside-validated-range")
PROPAGATING = ("failed", "unvalidated", "preliminary", "synthetic", "asimov", "user-supplied")
RULES = PLUGIN / "skills" / "hep-detector" / "assets" / "geant4-physics-rules.json"
REQUIRED = ("observable", "particle", "geometry_source", "physics", "convergence_plan", "statistical_target",
            "validation_plan", "variation_plan", "downstream_use")
VERDICT_FIELDS = ("observable", "statistical_target", "validation_plan.scope")
EM_SUFFIX = {"": "G4EmStandardPhysics", "_EMV": "G4EmStandardPhysics_option1", "_EMX": "G4EmStandardPhysics_option2",
             "_EMY": "G4EmStandardPhysics_option3", "_EMZ": "G4EmStandardPhysics_option4", "_LIV": "G4EmLivermorePhysics",
             "_PEN": "G4EmPenelopePhysics", "_EM0": "G4EmStandardPhysics", "_WVI": "G4EmStandardPhysicsWVI",
             "__GS": "G4EmStandardPhysicsGS", "__SS": "G4EmStandardPhysicsSS", "__LE": "G4EmLowEPPhysics"}
# hadronic inelastic model by list, particle class and kinetic energy (MeV), Geant4 11.4.3: G4HadronPhysicsQGSP_BIC.cc
# (maxBIC_proton = maxBIC_neutron = 1.5 GeV, minBERT 1 GeV; otherwise as G4HadronPhysicsQGSP_BERT.cc) and
# G4HadronicParameters.cc (FTF-cascade transition 3-6 GeV, QGS-FTF transition 12-25 GeV); "A/B" is a transition region
HADRONIC = {"QGSP_BIC": {"nucleon": [(1000.0, "BIC"), (1500.0, "BIC/BERT"), (3000.0, "BERT"), (6000.0, "BERT/FTFP"),
                                     (12000.0, "FTFP"), (25000.0, "FTFP/QGSP"), (math.inf, "QGSP")],
                         "pion": [(3000.0, "BERT"), (6000.0, "BERT/FTFP"), (12000.0, "FTFP"), (25000.0, "FTFP/QGSP"),
                                  (math.inf, "QGSP")]},
            "FTFP_BERT": {"nucleon": [(3000.0, "BERT"), (6000.0, "BERT/FTFP"), (math.inf, "FTFP")],
                          "pion": [(3000.0, "BERT"), (6000.0, "BERT/FTFP"), (math.inf, "FTFP")]}}
NUCLEONS, PIONS = ("proton", "neutron"), ("pi+", "pi-")


class StudyError(ValueError):
    """Input the script refuses (exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_json(doc) -> str:
    return hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()


def write_json(path, doc) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except ValueError as exc:
        raise StudyError(f"{path}: not JSON ({exc})") from exc


def get(doc, dotted: str):
    cur = doc
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def load_study(path: Path) -> dict:
    study = load_json(path)
    if study.get("schema") != "geant4-study-spec/1":
        raise StudyError("the study spec schema must be geant4-study-spec/1")
    ls = get(study, "physics.layered_sim_spec")
    if isinstance(ls, str):
        study.setdefault("physics", {})["layered_sim"] = load_json(path.parent / ls)
    return study


def derived(study: dict) -> dict:
    ls = get(study, "physics.layered_sim") or {}
    phys = ls.get("physics", {})
    ui = ls.get("ui_commands", [])
    slabs = [s for layer in get(ls, "geometry.layers") or [] for s in layer.get("slabs", [])]
    ref = phys.get("reference_list")
    had = None
    if ref:
        had = ref
        for suf in sorted(EM_SUFFIX, key=len, reverse=True):
            if suf and ref.endswith(suf):
                had = ref[: -len(suf)]
                break
    scans = [p.get("values") for p in get(study, "convergence_plan.parameters") or [] if isinstance(p, dict)]
    return {"em_only": "em_constructor" in phys, "min_thickness_mm": min((s["thickness_mm"] for s in slabs),
                                                                        default=None),
            "pai_requested": any(c.startswith("/process/em/AddPAIRegion") for c in ui),
            "step_limits": bool(phys.get("step_limit_mm") or phys.get("min_ekin_MeV")),
            "cut_scan_values": scans, "hadronic_list": had,
            "secondary_biasing": any(c.startswith("/process/em/setSecBiasing") for c in ui)}


def holds(cond: dict, doc: dict) -> bool:
    if "all" in cond:
        return all(holds(c, doc) for c in cond["all"])
    if "any" in cond:
        return any(holds(c, doc) for c in cond["any"])
    v, op, ref = get(doc, cond["field"]), cond["op"], cond.get("value")
    if op == "exists":
        return v not in (None, [], {}, "")
    if op == "missing":
        return v in (None, [], {}, "")
    if v is None:
        return False
    try:
        return {"eq": lambda: v == ref, "ne": lambda: v != ref, "in": lambda: v in ref, "not_in": lambda: v not in ref,
                "lt": lambda: v < ref, "le": lambda: v <= ref, "gt": lambda: v > ref, "ge": lambda: v >= ref}[op]()
    except TypeError:
        return False


def load_rules(path: Path) -> list[dict]:
    doc = load_json(path)
    rules = doc.get("rules")
    if not isinstance(rules, list) or not rules:
        raise StudyError(f"{path}: no rules")
    for r in rules:
        src = r.get("source") or {}
        if not all(isinstance(src.get(k), str) and src[k].strip() for k in ("document", "version", "section")):
            raise StudyError(f"rule {r.get('id')}: a rule without a source (document, version, section) is refused")
        for k in ("id", "condition", "concern", "requires", "severity"):
            if k not in r:
                raise StudyError(f"rule {r.get('id')}: '{k}' is required")
        if r["severity"] not in ("error", "warning"):
            raise StudyError(f"rule {r['id']}: severity must be error or warning")
    return rules


def cmd_spec(args) -> tuple[str, dict]:
    study = load_study(Path(args.spec))
    rules = load_rules(Path(args.rules) if args.rules else RULES)
    missing = [k for k in REQUIRED if get(study, k) in (None, [], {}, "")]
    for k in ("observable.kind", "particle.name", "particle.energy_MeV", "validation_plan.scope"):
        if get(study, k) in (None, [], {}, "") and k.split(".")[0] not in missing:
            missing.append(k)
    doc = dict(study, derived=derived(study))
    findings, applicable = [], []
    for r in rules:
        if holds(r["condition"], doc):
            applicable.append(r["id"])
            if not holds(r["requires"], doc):
                findings.append({"rule": r["id"], "severity": r["severity"], "concern": r["concern"],
                                 "read": r.get("read"), "source": r["source"], "requires": r["requires"]})
    blocking = [m for m in missing if m.split(".")[0] in ("observable", "statistical_target") or
                m == "validation_plan.scope" or m == "validation_plan"]
    errors = [f for f in findings if f["severity"] == "error"]
    status = "failed" if blocking or errors else "ok"
    return status, {"missing": missing, "blocking_missing": blocking, "findings": findings,
                    "rule_coverage": {"rules": len(rules), "applicable": len(applicable), "applicable_ids": applicable,
                                      "fired": len(findings), "observable_kind": get(study, "observable.kind"),
                                      "kinds_with_a_rule": sorted({k for r in rules for k in _kinds(r["condition"])})},
                    "derived": doc["derived"]}


def _kinds(cond) -> list[str]:
    if "all" in cond or "any" in cond:
        return [k for c in cond.get("all", cond.get("any", [])) for k in _kinds(c)]
    if cond.get("field") == "observable.kind":
        v = cond.get("value")
        return v if isinstance(v, list) else [v]
    return []


def read_csv(path: Path) -> list[dict]:
    try:
        return B.read_csv(path)
    except B.BenchmarkError as exc:
        raise StudyError(str(exc)) from exc


def _mpv(values, width):
    return B.mpv(values, width)


def boot(values, stat, n_boot, seed) -> float:
    return B.bootstrap(values, stat, n_boot, seed)


def cmd_summarize(args) -> tuple[str, dict]:
    rec = load_json(args.record)
    sim = get(rec, "extension.simulation")
    if not sim:
        raise StudyError("--record is not a Geant4 run record (no extension.simulation)")
    csv = Path(args.csv)
    rows = read_csv(csv)
    col = f"edep_{args.slab}_MeV"
    if col not in rows[0]:
        raise StudyError(f"{csv.name} has no column {col}")
    dep = [r[col] for r in rows]
    width = args.mpv_bin_mev
    tail_thr = args.tail_threshold_mev
    mean = statistics.fmean(dep)
    obs = {"mean_deposit_MeV": {"value": mean, "se": boot(dep, statistics.fmean, args.bootstrap, args.seed)},
           "mpv_deposit_MeV": {"value": _mpv(dep, width), "se": boot(dep, lambda v: _mpv(v, width), args.bootstrap,
                                                                     args.seed)}}
    p = sum(d > tail_thr for d in dep) / len(dep)
    obs["tail_fraction"] = {"value": p, "se": math.sqrt(max(p * (1 - p), 1 / len(dep) ** 2) / len(dep)),
                            "threshold_MeV": tail_thr}
    if "primary_eloss_MeV" in rows[0]:
        loss = [r["primary_eloss_MeV"] for r in rows if r.get("primary_fate") == 1]
        if len(loss) > 1:
            obs["mpv_loss_MeV"] = {"value": _mpv(loss, width), "se": boot(loss, lambda v: _mpv(v, width),
                                                                          args.bootstrap, args.seed)}
    doc = {"schema": "geant4-run-summary/1", "run_record": {"artifact_id": rec["artifact_id"],
                                                            "sha256": sha256_file(Path(args.record))},
           "csv": {"name": csv.name, "sha256": sha256_file(csv)}, "events": len(rows),
           "settings": {"default_cut_mm": sim["physics"].get("default_cut_mm"),
                        "step_limit_mm": sim["physics"].get("step_limit_mm", 0.0),
                        "em_constructor": sim["physics"].get("em_constructor"),
                        "reference_list": sim["physics"].get("reference_list"),
                        "ui_commands": sim.get("ui_commands", []), "particle": sim["gun"]["particle"],
                        "energy_MeV": sim["gun"]["energy_MeV"]},
           "spec_sha256": sim.get("spec_sha256"), "data_path_problems": sim.get("data_path_problems", []),
           "datasets_content_match": all(d.get("content_match") for d in sim.get("datasets", [])),
           "bootstrap": {"resamples": args.bootstrap, "seed": args.seed}, "mpv_bin_MeV": width, "observables": obs}
    write_json(args.out, doc)
    return "ok", {"summary": args.out, "events": len(rows), "observables": obs}


def check_records(study: dict, sums: list[dict]) -> list[str]:
    ls = get(study, "physics.layered_sim") or {}
    problems = []
    scanned = {p["name"].split(".")[-1] for p in get(study, "convergence_plan.parameters") or []}
    for s in sums:
        st = s["settings"]
        rid = s["run_record"]["artifact_id"]
        if st["particle"] != ls.get("gun", {}).get("particle") or st["energy_MeV"] != ls.get("gun", {}).get("energy_MeV"):
            problems.append(f"{rid}: gun {st['particle']} {st['energy_MeV']} MeV differs from the spec")
        for k in ("em_constructor", "reference_list"):
            if st.get(k) != ls.get("physics", {}).get(k) and s.get("role") != "variation":
                problems.append(f"{rid}: physics {k} {st.get(k)} differs from the spec {ls.get('physics', {}).get(k)}")
        if "default_cut_mm" not in scanned and st["default_cut_mm"] != ls.get("physics", {}).get("default_cut_mm"):
            problems.append(f"{rid}: cut {st['default_cut_mm']} mm differs from the spec and is not a scanned parameter")
        if s.get("data_path_problems"):
            problems.append(f"{rid}: data paths {s['data_path_problems']}")
        if not s.get("datasets_content_match", False):
            problems.append(f"{rid}: a dataset content hash differs from the build record")
        if s.get("role") == "nominal" and s.get("spec_sha256") != sha256_json(ls):
            problems.append(f"{rid}: the run's spec hash differs from the study's layered_sim spec")
    return problems


def convergence(study: dict, sums: list[dict]) -> dict:
    plan = get(study, "convergence_plan") or {}
    tol = plan.get("tolerance_relative") or {}
    out, ok = [], True
    for p in plan.get("parameters", []):
        key = p["name"].split(".")[-1]
        pts = sorted((s for s in sums if s["settings"].get(key) is not None and s.get("role") in ("scan", "nominal")
                      and s["settings"].get(key) in p["values"]), key=lambda s: s["settings"][key])
        vals = sorted({s["settings"][key] for s in pts})
        if len(vals) < 2:
            out.append({"parameter": p["name"], "verdict": "not-run", "reason": "fewer than two scanned values"})
            ok = False
            continue
        finest = [next(s for s in pts if s["settings"][key] == v) for v in vals[:2]]
        rows = []
        for o in plan.get("observables", []):
            a, b = finest[0]["observables"].get(o), finest[1]["observables"].get(o)
            t = tol.get(o)
            if a is None or b is None or t is None:
                rows.append({"observable": o, "verdict": "missing"})
                ok = False
                continue
            diff = (a["value"] - b["value"]) / b["value"] if b["value"] else a["value"] - b["value"]
            se = math.hypot(a["se"], b["se"]) / abs(b["value"]) if b["value"] else math.hypot(a["se"], b["se"])
            v = "pass" if abs(diff) <= t and se <= t / 2 else ("unresolved" if abs(diff) <= t else "fail")
            ok = ok and v == "pass"
            rows.append({"observable": o, "finest": vals[0], "next": vals[1], "relative_change": diff,
                         "se_of_change": se, "tolerance": t, "verdict": v})
        out.append({"parameter": p["name"], "values": vals, "two_finest": vals[:2], "observables": rows,
                    "verdict": "pass" if all(r["verdict"] == "pass" for r in rows) else "fail"})
    return {"gate": "pass" if ok and out else "fail", "parameters": out,
            "rule": "between the two finest settings of each declared scan, every declared observable changes by at "
                    "most its relative tolerance and the SE of the change is at most half the tolerance"}


def stat_target(study: dict, nominal: dict | None) -> dict:
    t = get(study, "statistical_target") or {}
    q, target = t.get("observable"), t.get("relative_se")
    if not nominal or not q or not isinstance(target, (int, float)):
        return {"verdict": "not-checked", "reason": "no nominal summary or no statistical_target.observable/relative_se"}
    o = nominal["observables"].get(q)
    if not o:
        return {"verdict": "not-checked", "reason": f"observable {q} not in the nominal summary"}
    rel = o["se"] / abs(o["value"]) if o["value"] else math.inf
    n = nominal["events"]
    need = math.ceil(n * (rel / target) ** 2)
    return {"observable": q, "relative_se": rel, "target": target, "events": n, "verdict": "pass" if rel <= target
            else "fail", "events_needed": need if rel > target else None,
            "estimate": f"seeded bootstrap of this run ({nominal['bootstrap']['resamples']} resamples); N_needed = "
                        "N (SE/target)^2, assuming SE ~ 1/sqrt(N); the delta-ray tail makes means converge slowly"}


def cmd_run(args) -> tuple[str, dict]:
    study = load_study(Path(args.spec))
    sums = []
    for item in args.summary:
        role, _, path = item.rpartition("=")
        s = load_json(path)
        if s.get("schema") != "geant4-run-summary/1":
            raise StudyError(f"{path}: not a geant4-run-summary/1")
        s["role"] = role or "scan"
        s["path"] = path
        sums.append(s)
    nominal = next((s for s in sums if s["role"] == "nominal"), None)
    problems = check_records(study, sums)
    stat = stat_target(study, nominal)
    conv = convergence(study, sums)
    doc = {"record_problems": problems, "statistical_target": stat, "convergence": conv,
           "summaries": [{"role": s["role"], "path": s["path"], "sha256": sha256_file(Path(s["path"])),
                          "run_record": s["run_record"]} for s in sums]}
    if args.out:
        write_json(args.out, doc)
    ok = not problems and stat["verdict"] in ("pass", "not-checked") and conv["gate"] == "pass"
    return ("ok" if ok else "failed"), doc


def model_assignment(settings: dict, domain: str) -> dict:
    ui = settings.get("ui_commands", [])
    fluct = "PAI" if any(c.startswith("/process/em/AddPAIRegion") for c in ui) else "Urban"
    if domain == "hadronic":
        ref = settings.get("reference_list") or ""
        base = next((b for b in HADRONIC if ref.startswith(b)), None)
        part, e = settings["particle"], settings["energy_MeV"]
        cls = "nucleon" if part in NUCLEONS else "pion" if part in PIONS else None
        if not base or not cls:
            return {"domain": "hadronic", "model": None, "known": False}
        model = next(m for lim, m in HADRONIC[base][cls] if e <= lim)
        return {"domain": "hadronic", "list": base, "particle_class": cls, "model": model, "known": True}
    em = settings.get("em_constructor")
    if not em:
        ref = settings.get("reference_list") or ""
        suf = next((s for s in sorted(EM_SUFFIX, key=len, reverse=True) if s and ref.endswith(s)), "")
        em = EM_SUFFIX[suf]
    return {"domain": "em", "em_constructor": em, "fluctuation_model": fluct, "known": True}


def cmd_variations(args) -> tuple[str, dict]:
    study = load_study(Path(args.spec))
    domain = get(study, "observable.domain") or "em"
    obs = get(study, "variation_plan.observable") or get(study, "statistical_target.observable")
    nominal = load_json(args.nominal)
    nm = model_assignment(nominal["settings"], domain)
    if obs not in nominal["observables"]:
        raise StudyError(f"observable {obs} not in the nominal summary")
    rows, included = [], [nominal["observables"][obs]["value"]]
    for item in args.variation:
        name, _, path = item.partition("=")
        s = load_json(path)
        ma = model_assignment(s["settings"], domain)
        keys = ("domain", "particle_class", "model") if domain == "hadronic" else ("domain", "em_constructor",
                                                                                  "fluctuation_model")
        changed = ma.get("known") and nm.get("known") and any(ma.get(k) != nm.get(k) for k in keys)
        val = s["observables"].get(obs, {}).get("value")
        se = s["observables"].get(obs, {}).get("se")
        nse = nominal["observables"][obs].get("se")
        diff_se = math.hypot(se, nse) / abs(included[0]) if se is not None and nse is not None else None
        rel = (val - included[0]) / included[0] if val is not None else None
        row = {"variation": name, "summary": path, "model_assignment": ma, "nominal_model_assignment": nm,
               "value": val, "se": se, "relative_to_nominal": rel, "se_of_relative_difference": diff_se,
               "resolved": None if rel is None or diff_se is None else abs(rel) > 2 * diff_se}
        if changed and val is not None:
            row["listed"] = True
            included.append(val)
        else:
            row["listed"] = False
            row["reason"] = ("same model for this particle and energy: a false zero difference, not a systematic"
                             if ma.get("known") else "model assignment unknown for this list, particle or energy")
        rows.append(row)
    env = (max(included) - min(included)) / abs(included[0]) if len(included) > 1 else None
    doc = {"observable": obs, "domain": domain, "nominal": {"summary": args.nominal, "model_assignment": nm,
                                                            "value": included[0]},
           "variations": rows, "envelope_relative": env,
           "note": "model envelope (max - min over the listed variations and the nominal), not a standard deviation; "
                   "it includes each run's MC statistical spread (see se_of_relative_difference: a difference below "
                   "about 2 SE is not resolved); hand it to hep-statistics as a model envelope"}
    if args.out:
        write_json(args.out, doc)
    return "ok", doc


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise StudyError(f"{path} is outside the project root {root}") from exc


def scope_within(declared: dict, bench: dict) -> list[str]:
    out = []
    for k in ("particle", "material", "observable"):
        if declared.get(k) is not None and bench.get(k) is not None and k != "observable" and declared[k] != bench[k]:
            out.append(f"declared {k} {declared[k]} is not the benchmark's {bench[k]}")
    for k, bk in (("energy_MeV", "energy_MeV"), ("thickness_mm", "thickness_mm")):
        d, b = declared.get(k), bench.get(bk)
        if isinstance(d, list) and b is not None:
            lo, hi = d
            if lo < b * (1 - 1e-9) or hi > b * (1 + 1e-9):
                out.append(f"declared {k} {d} is larger than the benchmarked {b}")
    return out


def cmd_label(args) -> tuple[str, dict]:
    spec_path = Path(args.spec)
    study = load_study(spec_path)
    root = Path(args.project_root)
    bench = load_json(args.benchmarks)
    conv = load_json(args.convergence)
    var = load_json(args.variations) if args.variations else None
    gaps = list(bench.get("gaps", []))
    for b in bench.get("benchmarks", []):
        if b.get("grade") == "reference" and b.get("verdict") == "fail":
            gaps.append(f"{b['benchmark']} failed: relative difference {b['relative_difference']:+.4g} beyond the "
                        f"tolerance {b['tolerance']['total']:.4g} ({b['reference']['source'][:60]}...)")
    if conv.get("convergence", {}).get("gate") != "pass":
        gaps.append("convergence gate not passed: " + "; ".join(
            f"{p['parameter']} {p['verdict']}" for p in conv.get("convergence", {}).get("parameters", [])))
    if conv.get("record_problems"):
        gaps += [f"record: {p}" for p in conv["record_problems"]]
    if conv.get("statistical_target", {}).get("verdict") == "fail":
        st = conv["statistical_target"]
        gaps.append(f"statistical target not met: {st['observable']} relative SE {st['relative_se']:.3g} > "
                    f"{st['target']} (needs about {st['events_needed']} events)")
    for m in study.get("materials", []):
        origin = m.get("reference_origin")
        if origin != "independent":
            gaps.append(f"material {m.get('name')}: reference inputs taken from the Geant4 material dump or of "
                        f"undeclared origin (reference_origin {origin!r}; {m.get('reference_source')}): an error in "
                        "the spec would enter the reference too and cancel")
    if var is None:
        gaps.append("no variation table")
    gaps.append("build_response.py writes empty inputs and one --status: a response built from these runs cannot link "
                "the run records (phase 2 requirement 5)")
    if not any(b.get("validation_evidence") for b in bench.get("benchmarks", [])):
        gaps.append("no reference benchmark is validation evidence for this study (R5 not met)")
    declared = get(study, "validation_plan.scope") or {}
    eligible = []
    for b in bench.get("benchmarks", []):
        if b.get("validation_evidence"):
            outside = scope_within(declared, b["scope"])
            if outside:
                gaps += [f"{b['benchmark']}: {o}" for o in outside]
            elif conv.get("convergence", {}).get("gate") == "pass":
                eligible.append({"benchmark": b["benchmark"], "scope": b["scope"]})
    run_refs = []
    for path in args.run_record or []:
        rec = load_json(path)
        if rec.get("artifact_type") != "computational-run":
            raise StudyError(f"{path}: not a computational-run")
        run_refs.append({"ref": _rel(Path(path), root), "artifact_type": "computational-run",
                         "artifact_id": rec["artifact_id"], "version": rec["contract_version"],
                         "sha256": sha256_file(Path(path)), "status": rec["status"]})
    for path in args.reference_record or []:
        rec = load_json(path)
        run_refs.append({"ref": _rel(Path(path), root), "artifact_type": rec.get("artifact_type"),
                         "artifact_id": rec.get("artifact_id"), "version": rec.get("contract_version"),
                         "sha256": sha256_file(Path(path)), "status": rec.get("status", [])})
    labels = ["unvalidated"] + [s for r in run_refs for s in r["status"] if s in PROPAGATING]
    labels = list(dict.fromkeys(labels))
    doc = {"highest_usable_label": "unvalidated", "labels": labels, "gaps": gaps,
           "phase2_upgrade_eligible_scopes": eligible,
           "note": "phase 1: every Geant4-derived artifact stays unvalidated with its evidence and scope embedded; "
                   "the eligible scopes say only what phase 2 could re-issue as validated-in-scope"}
    if args.write:
        out = Path(args.write)
        created = args.created or datetime.date.today().isoformat()
        plugin_version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        manifest = [{"path": _rel(spec_path, root), "sha256": sha256_file(spec_path)}]
        for extra in (args.benchmarks, args.convergence, args.variations):
            if extra:
                manifest.append({"path": _rel(Path(extra), root), "sha256": sha256_file(Path(extra))})
        ls = get(study, "physics.layered_sim_spec")
        if isinstance(ls, str):
            manifest.append({"path": _rel(spec_path.parent / ls, root), "sha256": sha256_file(spec_path.parent / ls)})
        record = {
            "contract_version": CONTRACTS_VERSION, "artifact_id": study.get("study_id", "geant4-study") + "-study",
            "artifact_type": "computational-run",
            "objective": f"Geant4 study record: {get(study, 'observable.name')} for {get(study, 'particle.name')} "
                         f"{get(study, 'particle.energy_MeV')} MeV; benchmarks, convergence and scope embedded "
                         "(unvalidated in phase 1)",
            "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": plugin_version, "contracts": CONTRACTS_VERSION, "profiles": {}},
            "provenance": {"producer_skill": "hep-detector", "created": created, "evidence_ids": []},
            "inputs": run_refs, "outputs": [], "unresolved_inputs": [], "status": labels,
            "extension": {"input_manifest": manifest,
                          "tools": [{"name": "check_geant4_study.py", "version": sha256_file(Path(__file__))[:16]},
                                    {"name": "geant4_benchmarks.py", "version": sha256_file(
                                        Path(__file__).with_name("geant4_benchmarks.py"))[:16]}],
                          "commands": ["check_geant4_study.py label --write"], "environment": {},
                          "seeds": {}, "tolerances": {"convergence": get(study, "convergence_plan.tolerance_relative")
                                                      or {}},
                          "exit_status": 0, "output_hashes": {},
                          "study": {"benchmarks": bench.get("benchmarks", []), "convergence": conv.get("convergence"),
                                    "statistical_target": conv.get("statistical_target"),
                                    "variations": var, "declared_scope": declared, "gaps": gaps,
                                    "phase2_upgrade_eligible_scopes": eligible,
                                    "highest_usable_label": "unvalidated"}}}
        write_json(out, record)
        doc["record"] = str(out)
    return "ok", doc


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("spec", help="completeness and physics rules of a study spec")
    p.add_argument("--spec", required=True)
    p.add_argument("--rules")
    p = sub.add_parser("summarize", help="observables of one run")
    p.add_argument("--record", required=True)
    p.add_argument("--csv", required=True)
    p.add_argument("--slab", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--bootstrap", type=int, default=200)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mpv-bin-mev", type=float, default=0.002)
    p.add_argument("--tail-threshold-mev", type=float, default=0.25)
    p = sub.add_parser("run", help="records against the spec, statistical target, convergence gate")
    p.add_argument("--spec", required=True)
    p.add_argument("--summary", action="append", required=True, help="[ROLE=]SUMMARY.json; ROLE nominal or scan")
    p.add_argument("--out")
    p = sub.add_parser("variations", help="variation table with model assignments")
    p.add_argument("--spec", required=True)
    p.add_argument("--nominal", required=True)
    p.add_argument("--variation", action="append", required=True, help="NAME=SUMMARY.json")
    p.add_argument("--out")
    p = sub.add_parser("label", help="highest usable label, gaps, and the study record")
    p.add_argument("--spec", required=True)
    p.add_argument("--benchmarks", required=True)
    p.add_argument("--convergence", required=True)
    p.add_argument("--variations")
    p.add_argument("--run-record", action="append")
    p.add_argument("--reference-record", action="append")
    p.add_argument("--project-root", required=True)
    p.add_argument("--write")
    p.add_argument("--created")
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("rules", "bootstrap", "seed", "mpv_bin_mev", "tail_threshold_mev", "created", "status")
                if hasattr(args, k) and f"--{k.replace('_', '-')}" not in given]
    handlers = {"spec": cmd_spec, "summarize": cmd_summarize, "run": cmd_run, "variations": cmd_variations,
                "label": cmd_label}
    try:
        status, doc = handlers[args.command](args)
    except (StudyError, FileNotFoundError, KeyError, TypeError, OSError, ValueError, ArithmeticError) as exc:
        status, doc = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **doc}, indent=1, default=str))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
