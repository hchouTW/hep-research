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
              With --effective-config (geant4 adapter 0.2.0) the thin-layer rule takes the minimum slab thickness
              from the effective config's geometry tree (derived.min_thickness_basis), else from spec/1.
  run         run summaries (simulation-summary/1, written by adapters/geant4/assets/summary_from_csv.py, or legacy
              geant4-run-summary/1 for records made before contracts CV-A1) against the spec (physics, gun, spec
              hash, data paths and dataset hashes, the observable declarations and block count), the statistical
              target (batch-means SE over the run's K blocks; a missed target is incomplete, exit 3, and is not topped
              up), and the convergence gate (hard): every declared value of each cut or step-limit scan needs a run
              summary (a missing one makes the gate incomplete), and between the two finest declared settings every
              declared observable is equivalent within its tolerance (intersection-union test: pass when |diff| +
              t_0.95 se <= tol and both points meet the se target tol/(4 sqrt 2); fail, exit 1, when |diff| -
              t_(1-0.05/m) se > tol; otherwise incomplete, exit 3; core/stats/decisions.py). This is the only place a
              too-coarse cut is caught. Each observable is estimated by core/simulation/estimates.py (mean,
              proportion, mode or quantile per the study spec's observables; exact intervals at low counts).
  variations  a variation table: each variation's model assignment for the particle and energy (EM constructor and
              fluctuation model for EM observables; the hadronic model in use for hadronic ones); a variation that
              keeps the model is excluded, never listed as a systematic; the spread is a model envelope, not a sigma.
  label       the highest usable label (phase 1: `unvalidated`, plus every propagating label of the inputs), the gaps,
              and the scopes that phase 2 could upgrade (contracts CV-B2: a tracking-resolution or charge-confusion
              study qualifies only through every condition of its qualification path, contracts.validate.
              qualification_missing: material-definition, field-propagation, reco-closure and the kind's reference
              benchmark, each matched by its own declared-scope keys); with --results and --geometry (Geant4 program
              B2.6) the record keeps the F4 results, the tail sources and the geometry file; --write writes the study record, a computational-run whose
              inputs are the run records and reference dataset-records (statuses declared, sha256), with the
              benchmarks, convergence, variations and scope embedded. Insufficient evidence still writes the record,
              listing the gaps; only invalid input is refused (exit 2). Run records from geant4 adapter 0.6.0 name
              their installation's origin: label lists them (geant4_installations) and, for a registered
              installation (geant4_build.py register: no source commit, build options or dataset MD5s), adds a
              provenance note; the origin is reported, not a gap.
Usage (paths relative to the current folder):
  check_geant4_study.py spec --spec STUDY.json [--rules RULES.json] [--effective-config EFFECTIVE_CONFIG.json]
  check_geant4_study.py run --spec STUDY.json --summary SUMMARY.json [...] [--out CONVERGENCE.json]
  check_geant4_study.py variations --spec STUDY.json --nominal SUMMARY.json --variation NAME=SUMMARY.json [...] --out VARIATIONS.json
  check_geant4_study.py label --spec STUDY.json --benchmarks BENCH.json --convergence CONV.json [--variations VAR.json]
                        --project-root ROOT [--reference-record DATASET.json ...] [--write STUDY_RECORD.json] [--created DATE]
Output JSON: status, status_label, inputs, defaults_used and the subcommand's result.
Exit codes: 0 ok (label: the record was written or evaluated); 1 a negative verdict (missing required fields, an
error rule, a record that disagrees with the spec, a resolved convergence failure); 2 bad input; 3 incomplete (a
missing scan value, an unresolved difference, a missed se or statistical target).
Standard library only.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geant4_benchmarks as B  # noqa: E402  (sibling: one MPV estimator, CSV reader and bootstrap for both scripts)
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts import trace  # noqa: E402
from contracts.schema import validate as schema_validate  # noqa: E402
from contracts.validate import (geant4_tree_thickness_mm, qualification_missing, qualification_reference,  # noqa: E402
                                qualified_uncertainty, scope_outside)
from core.simulation import estimates as E  # noqa: E402
from core.simulation.summary import SUMMARY_VERSION  # noqa: E402
from core.stats import batch_means as M, decisions as D  # noqa: E402
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
# the EM constructor a reference list builds without a suffix, where it is not G4EmStandardPhysics (Geant4 11.4.3:
# QGSP_BIC_HP.cc, QGSP_BIC_HPT.cc, QGSP_BIC_AllHP.cc register option 4; FTFP_BERT_TRV.cc registers GS); LBE builds its
# own EM processes and G4PhysListFactory ignores an EM suffix on it (G4PhysListFactory.cc, had_name != "LBE")
EM_BASE = {"QGSP_BIC_HP": "G4EmStandardPhysics_option4", "QGSP_BIC_HPT": "G4EmStandardPhysics_option4",
           "QGSP_BIC_AllHP": "G4EmStandardPhysics_option4", "QGSP_BIC_AllHPT": "G4EmStandardPhysics_option4",
           "FTFP_BERT_TRV": "G4EmStandardPhysicsGS", "LBE": "LBE (its own EM processes)"}


def split_reference_list(ref: str) -> tuple[str, str]:
    """(hadronic list, EM suffix) of a G4PhysListFactory name: the suffix is the last four characters when they are one
    of the factory's EM options (G4PhysListFactory::GetReferencePhysList), else empty."""
    suf = ref[-4:] if len(ref) > 4 and ref[-4:] in EM_SUFFIX and ref[-4:] else ""
    return (ref[: -len(suf)] if suf else ref), suf


def em_constructor_of(ref: str) -> str:
    """The EM constructor a reference list builds: the suffix's, else the list's own (EM_BASE), else
    G4EmStandardPhysics; LBE keeps its own EM whatever the suffix; _EM0 is the factory's default (no replacement)."""
    had, suf = split_reference_list(ref)
    if had == "LBE":
        return EM_BASE["LBE"]
    if suf and suf != "_EM0":
        return EM_SUFFIX[suf]
    return EM_BASE.get(had, "G4EmStandardPhysics")
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
    es = get(study, "physics.element_sim_spec")  # Geant4 program B2: an element_sim study (geant4 adapter 0.3.0)
    if isinstance(es, str):
        study.setdefault("physics", {})["element_sim"] = load_json(path.parent / es)
    return study


def sim_spec(study: dict) -> tuple[str, dict]:
    """(program, spec) of the study: element_sim when it names an element_sim spec, else layered_sim."""
    es = get(study, "physics.element_sim")
    if isinstance(es, dict):
        return "element_sim", es
    return "layered_sim", get(study, "physics.layered_sim") or {}


def spec_hash(program: str, spec: dict) -> str:
    """The spec hash a run record carries: layered_sim's sha256_json, element_sim's sha256 of the spec file the program
    read (geant4_run.py writes it with sorted keys, one-space indent and a final newline)."""
    if program == "element_sim":
        return hashlib.sha256((json.dumps(spec, indent=1, sort_keys=True) + "\n").encode("utf-8")).hexdigest()
    return sha256_json(spec)


def derived(study: dict, effective_config: dict | None = None) -> dict:
    """Facts the rule table reads. The minimum slab thickness comes from the effective config's geometry tree when
    one is given (records from geant4 adapter 0.2.0, A2.6), else from spec/1's geometry.layers."""
    program, ls = sim_spec(study)
    phys = ls.get("physics", {})
    ui = ls.get("ui_commands", [])
    slabs = [s for layer in get(ls, "geometry.layers") or [] for s in layer.get("slabs", [])]
    if program == "element_sim":  # every element that is not a mother of another one, thickness along x
        mothers = {e.get("mother") for e in ls.get("elements", [])}
        slabs = [{"thickness_mm": 2 * e["half_mm"][0]} for e in ls.get("elements", []) if e["name"] not in mothers]
    ref = phys.get("reference_list")
    had = None
    if ref:
        had = ref
        for suf in sorted(EM_SUFFIX, key=len, reverse=True):
            if suf and ref.endswith(suf):
                had = ref[: -len(suf)]
                break
    scans = [p.get("values") for p in get(study, "convergence_plan.parameters") or [] if isinstance(p, dict)]
    thick, basis = min((s["thickness_mm"] for s in slabs), default=None), None
    if effective_config is not None:
        if not effective_config.get("recorded"):
            raise StudyError("--effective-config: the probe recorded nothing (recorded: false); give none to use spec/1")
        try:
            thick, basis = min(geant4_tree_thickness_mm(effective_config).values(), default=None), "effective config"
        except ValueError as exc:
            raise StudyError(f"--effective-config: {exc}") from exc
    return {"em_only": "em_constructor" in phys, "min_thickness_mm": thick,
            **({"min_thickness_basis": basis} if basis else {}),
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
    ec = load_json(Path(args.effective_config)) if getattr(args, "effective_config", None) else None
    doc = dict(study, derived=derived(study, ec))
    if study.get("observables") is not None:  # CV-A1 (A1.12): the declarations and the names that must be declared
        rep = schema_validate(study["observables"], "simulation_observables.json")
        if not rep.ok:
            raise StudyError("observables: " + "; ".join(f.message for f in rep.errors)[:300])
        names = {o["name"] for o in study["observables"]}
        need = set(get(study, "convergence_plan.observables") or []) | {get(study, "statistical_target.observable")}
        missing += [f"observables.{n}" for n in sorted(need - names - {None})]
    findings, applicable = [], []
    for r in rules:
        if holds(r["condition"], doc):
            applicable.append(r["id"])
            if not holds(r["requires"], doc):
                findings.append({"rule": r["id"], "severity": r["severity"], "concern": r["concern"],
                                 "read": r.get("read"), "source": r["source"], "requires": r["requires"]})
    blocking = [m for m in missing if m.split(".")[0] in ("observable", "statistical_target", "observables") or
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


LEGACY_DOF = 1e6  # a geant4-run-summary/1 (bootstrap SE, before CV-A1) is read with a normal approximation
SE_TARGET_DIVISOR = 4 * math.sqrt(2)  # per-point se target tol / (4 sqrt 2) of the convergence gate (A1.8)
TWO_STAGE_FACTOR = (0.95, "F_0.95(K - 1, K_trial - 1)")  # A1.9 safety factor (maintainer decision: F_0.95)


def _decls(study: dict) -> dict:
    return {o["name"]: o for o in study.get("observables") or [] if isinstance(o, dict) and "name" in o}


def load_summary(path: str, study: dict) -> dict:
    """A run summary read for the study: simulation-summary/1 (validated with contracts/schemas, every observable
    estimated through core.simulation.estimates with the study's declaration, which the summary must match), or a
    legacy geant4-run-summary/1 (value and bootstrap SE; replay of records made before CV-A1)."""
    doc = load_json(path)
    if doc.get("schema") == "geant4-run-summary/1":
        obs = {k: {"value": v["value"], "se": v["se"], "dof": LEGACY_DOF, "status": "ok",
                   "method": "legacy single-run summary (bootstrap SE)"} for k, v in doc["observables"].items()}
        return {"legacy": True, "settings": doc["settings"], "events": doc["events"], "observables": obs,
                "spec_sha256": doc.get("spec_sha256"), "data_path_problems": doc.get("data_path_problems", []),
                "datasets_content_match": doc.get("datasets_content_match", False), "run_record": doc["run_record"],
                "estimate_note": doc.get("bootstrap")}
    if doc.get("summary_version") != SUMMARY_VERSION:
        raise StudyError(f"{path}: neither a {SUMMARY_VERSION} nor a legacy geant4-run-summary/1")
    rep = schema_validate(doc, "simulation_summary.json")
    if not rep.ok:
        raise StudyError(f"{path}: invalid {SUMMARY_VERSION}: " + "; ".join(f.message for f in rep.errors)[:300])
    run, decls = doc["run"], _decls(study)
    k = get(study, "blocks.K")
    if isinstance(k, int) and run["blocks"] != k:
        raise StudyError(f"{path}: {run['blocks']} blocks, the study spec declares K = {k}")
    tol = get(study, "convergence_plan.tolerance_relative") or {}
    obs = {}
    for o in doc["observables"]:
        d = decls.get(o["name"])
        if d is None:
            continue
        for key, default in (("source_column", None), ("selection", []), ("bins", None), ("thresholds", [])):
            if o.get(key, default) != d.get(key, default):
                raise StudyError(f"{path}: observable {o['name']} {key} {o.get(key)!r} differs from the study's "
                                 f"declaration {d.get(key, default)!r}")
        try:
            obs[o["name"]] = E.estimate(doc, d, tol.get(o["name"]))
        except (ValueError, ArithmeticError) as exc:
            obs[o["name"]] = {"value": None, "status": "incomplete", "reason": str(exc)}
    return {"legacy": False, "settings": run.get("settings") or {}, "events": run["events_in_blocks"],
            "observables": obs, "spec_sha256": run.get("spec_sha256"),
            "data_path_problems": run.get("data_path_problems", []),
            "datasets_content_match": run.get("datasets_content_match", False),
            "run_record": run.get("run_record") or {}, "evidence_role": run.get("evidence_role"),
            "blocks": run["blocks"], "block_size": run["block_size"]}


def check_records(study: dict, sums: list[dict]) -> list[str]:
    program, ls = sim_spec(study)
    gun = ls.get("gun") or ls.get("source") or {}
    problems = []
    scanned = {p["name"].split(".")[-1] for p in get(study, "convergence_plan.parameters") or []}
    for s in sums:
        st = s["settings"]
        rid = s["run_record"].get("artifact_id")
        if st.get("particle") != gun.get("particle") or st.get("energy_MeV") != gun.get("energy_MeV"):
            problems.append(f"{rid}: gun {st.get('particle')} {st.get('energy_MeV')} MeV differs from the spec")
        for k in ("em_constructor", "reference_list"):
            if st.get(k) != ls.get("physics", {}).get(k) and s.get("role") != "variation":
                problems.append(f"{rid}: physics {k} {st.get(k)} differs from the spec {ls.get('physics', {}).get(k)}")
        if "default_cut_mm" not in scanned and st.get("default_cut_mm") != ls.get("physics", {}).get("default_cut_mm"):
            problems.append(f"{rid}: cut {st.get('default_cut_mm')} mm differs from the spec and is not a scanned "
                            "parameter")
        if s.get("data_path_problems"):
            problems.append(f"{rid}: data paths {s['data_path_problems']}")
        if not s.get("datasets_content_match", False):
            problems.append(f"{rid}: a dataset content hash differs from the build record")
        if s.get("role") == "nominal" and s.get("spec_sha256") != spec_hash(program, ls):
            problems.append(f"{rid}: the run's spec hash differs from the study's {program} spec")
        if s.get("evidence_role") and s.get("role") and s["evidence_role"] != s["role"] and not (
                s["role"] == "scan" and s["evidence_role"] == "nominal"):
            problems.append(f"{rid}: summary evidence_role {s['evidence_role']} but supplied as {s['role']}")
    return problems


def _se_target_met(e: dict, t: float, mode: str) -> bool:
    """A1.8: a point meets its se target when se (relative under 'relative') <= tol / (4 sqrt 2); the exact
    low-count branch has no se and is judged on its interval instead (True here)."""
    if e.get("se") is None:
        return True
    se = e["se"] / abs(e["value"]) if mode == "relative" else e["se"]
    return se <= t / SE_TARGET_DIVISOR


def _compare(ea: dict, eb: dict, t: float, mode: str, m: int) -> dict:
    """One observable between the finest (a) and second-finest (b) declared settings (A1.8)."""
    if ea.get("status") != "ok" or eb.get("status") != "ok" or ea.get("value") is None or eb.get("value") is None:
        return {"verdict": "unresolved", "reason": "estimate-incomplete",
                "detail": ea.get("reason") or eb.get("reason")}
    met = _se_target_met(ea, t, mode) and _se_target_met(eb, t, mode)
    targets = {"finest": _se_target_met(ea, t, mode), "next": _se_target_met(eb, t, mode)}
    if ea.get("low_count") or eb.get("low_count"):
        if mode != "relative":
            return {"verdict": "unresolved", "reason": "low-count-absolute-unsupported"}
        r90 = M.rate_ratio_interval(ea["k"], eb["k"], 0.90, ea["n"], eb["n"])
        rm = M.rate_ratio_interval(ea["k"], eb["k"], 1 - 2 * D.ALPHA / m, ea["n"], eb["n"])
        r = D.equivalence(None, None, None, t, m, interval90=(r90[0] - 1, r90[1] - 1), interval_m=(rm[0] - 1, rm[1] - 1))
        return {**r, "relative_change": ea["value"] / eb["value"] - 1 if eb["value"] else None,
                "interval90": [r90[0] - 1, r90[1] - 1], "method": "conditional binomial (exact, low count)",
                "se_targets_met": targets}
    diff, se = D.difference(ea["value"], ea["se"], eb["value"], eb["se"], mode)
    nu = D.welch_dof(ea["se"], ea["dof"], eb["se"], eb["dof"])
    r = D.equivalence(diff, se, nu, t, m, targets_met=met)
    return {**r, ("relative_change" if mode == "relative" else "change"): diff, "se_of_change": se, "dof": nu,
            "se_targets_met": targets}


def convergence(study: dict, sums: list[dict]) -> dict:
    """The convergence gate (A1.8, A1.16): every declared value of each scan needs a summary; between the two finest
    declared settings every declared observable must be equivalent within its tolerance (intersection-union test,
    core.stats.decisions.equivalence with m = parameters x observables; unresolved or a missed se target is
    incomplete, a resolved excess is fail)."""
    plan = get(study, "convergence_plan") or {}
    tol = plan.get("tolerance_relative") or {}
    decls = _decls(study)
    params = plan.get("parameters", [])
    m = max(1, len(params) * len(plan.get("observables", [])))
    out = []
    trace.tag("geant4-convergence-complete")
    for p in params:
        key = p["name"].split(".")[-1]
        pts = sorted((s for s in sums if s["settings"].get(key) is not None and s.get("role") in ("scan", "nominal")
                      and s["settings"].get(key) in p["values"]), key=lambda s: s["settings"][key])
        vals = sorted({s["settings"][key] for s in pts})
        declared = sorted(p["values"])
        missing = [v for v in declared if v not in vals]
        if missing:  # D11: every declared value needs a scan or nominal summary (A1.16)
            out.append({"parameter": p["name"], "verdict": "incomplete", "reason": "missing-scan-value",
                        "missing_values": missing, "values": vals, "declared_values": declared})
            continue
        if len(declared) < 2:
            out.append({"parameter": p["name"], "verdict": "not-run", "reason": "fewer than two declared values"})
            continue
        finest = [next(s for s in pts if s["settings"][key] == v) for v in declared[:2]]  # the two finest declared
        rows = []
        for o in plan.get("observables", []):
            d = decls.get(o) or {}
            mode = d.get("tolerance_mode", "relative")
            t = d.get("tolerance") if mode == "absolute" else tol.get(o)
            ea, eb = finest[0]["observables"].get(o), finest[1]["observables"].get(o)
            if ea is None or eb is None or not isinstance(t, (int, float)):
                rows.append({"observable": o, "verdict": "unresolved", "reason": "missing"})
                continue
            rows.append({"observable": o, "finest": declared[0], "next": declared[1], "tolerance": t,
                         "tolerance_mode": mode, **_compare(ea, eb, t, mode, m)})
        vs = {r["verdict"] for r in rows}
        verdict = "fail" if "fail" in vs else ("incomplete" if vs - {"pass"} else "pass")
        out.append({"parameter": p["name"], "values": vals, "two_finest": declared[:2], "observables": rows,
                    "verdict": verdict})
    vs = {p["verdict"] for p in out}
    gate = "fail" if "fail" in vs or "not-run" in vs or not out else ("incomplete" if vs - {"pass"} else "pass")
    return {"gate": gate, "parameters": out, "multiplicity": m,
            "rule": "every declared value of each scan has a run summary (else incomplete, missing-scan-value); "
                    "between the two finest declared settings every declared observable is equivalent within its "
                    "tolerance: pass when |diff| + t_0.95(nu) se <= tol and both points meet the se target "
                    "tol/(4 sqrt 2), fail when |diff| - t_(1-0.05/m)(nu) se > tol, otherwise incomplete; low counts "
                    "decide on exact interval endpoints (A1.8)"}


def stat_target(study: dict, nominal: dict | None) -> dict:
    t = get(study, "statistical_target") or {}
    q, target = t.get("observable"), t.get("relative_se")
    if not nominal or not q or not isinstance(target, (int, float)):
        return {"verdict": "not-checked", "reason": "no nominal summary or no statistical_target.observable/relative_se"}
    o = nominal["observables"].get(q)
    if not o or o.get("status") != "ok" or o.get("value") is None:
        return {"verdict": "not-checked", "reason": f"observable {q} not estimated in the nominal summary"}
    if o.get("se") is None:  # exact low-count branch: the 68.27 % interval half-width stands in for the se
        lo, hi = M.exact_proportion(o["k"], o["n"], 0.6827)
        rel = (hi - lo) / 2 / abs(o["value"]) if o["value"] else math.inf
    else:
        rel = o["se"] / abs(o["value"]) if o["value"] else math.inf
    n = nominal["events"]
    need = math.ceil(n * (rel / target) ** 2)
    return {"observable": q, "relative_se": rel, "target": target, "events": n,
            "verdict": "pass" if rel <= target else "target-missed",
            "events_needed": need if rel > target else None,
            "estimate": "batch means over the run's blocks (legacy summaries: their bootstrap SE); N_needed = "
                        "N (SE/target)^2; a missed target is incomplete and is not topped up (A1.9)"}


def cmd_run(args) -> tuple[str, dict]:
    study = load_study(Path(args.spec))
    sums = []
    for item in args.summary:
        role, _, path = item.rpartition("=")
        s = load_summary(path, study)
        s["role"] = role or s.get("evidence_role") or "scan"
        s["path"] = path
        sums.append(s)
    nominal = next((s for s in sums if s["role"] == "nominal"), None)
    problems = check_records(study, sums)
    stat = stat_target(study, nominal)
    conv = convergence(study, sums)
    doc = {"record_problems": problems, "statistical_target": stat, "convergence": conv,
           "summaries": [{"role": s["role"], "path": s["path"], "sha256": sha256_file(Path(s["path"])),
                          "run_record": s["run_record"], "legacy": s["legacy"],
                          "observables": s["observables"]} for s in sums]}
    if args.out:
        write_json(args.out, doc)
    if problems or conv["gate"] == "fail":
        return "failed", doc
    if conv["gate"] == "incomplete" or stat["verdict"] == "target-missed":
        return "incomplete", doc
    return "ok", doc


PROBE_MODEL_NAMES = {"BertiniCascade": "BERT", "Binary Cascade": "BIC", "FTFP": "FTFP", "QGSP": "QGSP"}


def probe_hadronic_model(effective_config: dict, particle: str, energy_mev: float) -> str | None:
    """The inelastic model(s) the probe recorded for a particle at an energy (A2.4): models whose closed range contains
    the energy, a model whose range only starts at that energy left out unless it is the only one (the convention of
    HADRONIC, whose rows end at e <= lim), ordered by their lower edge and joined by '/', in the short names of
    HADRONIC; None if the probe has no inelastic process for the particle."""
    procs = [h for h in (effective_config.get("sections") or {}).get("geant4", {}).get("hadronic") or []
             if h.get("particle") == particle and "nelastic" in h.get("process", "")]
    if not procs:
        return None
    ranges = [(float.fromhex(m["min_MeV"]), float.fromhex(m["max_MeV"]), m["name"]) for m in procs[0]["models"]]
    inside = [r for r in ranges if r[0] <= energy_mev <= r[1]]
    interior = [r for r in inside if r[0] < energy_mev or len(inside) == 1]
    return "/".join(PROBE_MODEL_NAMES.get(n, n) for _, _, n in sorted(interior or inside))


def model_assignment(settings: dict, domain: str, effective_config: dict | None = None) -> dict:
    """The model a variation uses for the study's particle and energy. Hadronic: from the run's effective config when
    one is given (source probe; the declared table, source declared, otherwise; both present and different is an
    error, A2.4). EM: from the declared settings (the probe records the EM parameters, not the constructor)."""
    ma = _declared_assignment(settings, domain)
    if domain == "hadronic" and effective_config is not None and effective_config.get("recorded"):
        got = probe_hadronic_model(effective_config, settings["particle"], settings["energy_MeV"])
        if got is not None:
            if ma.get("known") and ma["model"] != got:
                raise StudyError(f"the effective config gives the hadronic model {got} for {settings['particle']} at "
                                 f"{settings['energy_MeV']} MeV, the declared table {ma['model']} (A2.4)")
            cls = "nucleon" if settings["particle"] in NUCLEONS else "pion" if settings["particle"] in PIONS else None
            return {**ma, "domain": "hadronic", "particle_class": ma.get("particle_class", cls), "model": got,
                    "known": True, "source": "probe"}
    return ma  # source declared (the key is written only when the probe is read, so older outputs are unchanged)


def _declared_assignment(settings: dict, domain: str) -> dict:
    ui = settings.get("ui_commands", [])
    fluct = "PAI" if any(c.startswith("/process/em/AddPAIRegion") for c in ui) else "Urban"
    if domain == "hadronic":
        ref = settings.get("reference_list") or ""
        base = split_reference_list(ref)[0]  # the exact list name: a variant (_ATL, _HP, ...) has other models
        base = base if base in HADRONIC else None
        part, e = settings["particle"], settings["energy_MeV"]
        cls = "nucleon" if part in NUCLEONS else "pion" if part in PIONS else None
        if not base or not cls:
            return {"domain": "hadronic", "model": None, "known": False}
        model = next(m for lim, m in HADRONIC[base][cls] if e <= lim)
        return {"domain": "hadronic", "list": base, "particle_class": cls, "model": model, "known": True}
    em = settings.get("em_constructor") or em_constructor_of(settings.get("reference_list") or "")
    return {"domain": "em", "em_constructor": em, "fluctuation_model": fluct, "known": True}


def cmd_variations(args) -> tuple[str, dict]:
    study = load_study(Path(args.spec))
    domain = get(study, "observable.domain") or "em"
    obs = get(study, "variation_plan.observable") or get(study, "statistical_target.observable")
    nominal = load_summary(args.nominal, study)
    configs = {}
    for item in args.effective_config or []:
        name, _, path = item.partition("=")
        configs[name] = load_json(Path(path))
    nm = model_assignment(nominal["settings"], domain, configs.get("nominal"))
    if obs not in nominal["observables"]:
        raise StudyError(f"observable {obs} not in the nominal summary")
    rows, included = [], [nominal["observables"][obs]["value"]]
    for item in args.variation:
        name, _, path = item.partition("=")
        s = load_summary(path, study)
        ma = model_assignment(s["settings"], domain, configs.get(name))
        keys = ("domain", "particle_class", "model") if domain == "hadronic" else ("domain", "em_constructor",
                                                                                  "fluctuation_model")
        changed = ma.get("known") and nm.get("known") and any(ma.get(k) != nm.get(k) for k in keys)
        val = s["observables"].get(obs, {}).get("value")
        se = s["observables"].get(obs, {}).get("se")
        nse = nominal["observables"][obs].get("se")
        diff_se = math.hypot(se, nse) / abs(included[0]) if se is not None and nse is not None else None
        rel = (val - included[0]) / included[0] if val is not None else None
        row = {"variation": name, "summary": path, "run_record_id": s["run_record"].get("artifact_id"),
               "model_assignment": ma, "nominal_model_assignment": nm,
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
                                                            "run_record_id": nominal["run_record"].get("artifact_id"),
                                                            "value": included[0]},
           "variations": rows, "envelope_relative": env,
           "note": "model envelope (max - min over the listed variations and the nominal), not a standard deviation; "
                   "it includes each run's MC statistical spread (see se_of_relative_difference: a difference below "
                   "about 2 SE is not resolved); hand it to hep-statistics as a model envelope"}
    if args.out:
        write_json(args.out, doc)
    return "ok", doc


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise StudyError(f"{path} is outside the project root {root}") from exc


def realization_entry(realization: dict, esp: Path, root: Path) -> dict | None:
    """Input-manifest entry for the realization profile an element_sim spec's provenance names, or None.

    The recorded path is used when it exists on this machine. A recorded path from another machine (a live campaign
    replayed elsewhere) is replaced by a file of the same name next to the spec or in a folder above it inside root,
    accepted only when its sha256 equals the recorded one; the entry then keeps the recorded path, so the record is
    the same on every machine."""
    rp = realization.get("path")
    if not isinstance(rp, str):
        return None
    rpath = Path(rp.replace("<plugin root>", str(PLUGIN))).expanduser()
    if not rpath.is_absolute():
        rpath = esp.parent / rpath
    if rpath.is_file():
        return {"path": _rel(rpath, root) if _inside(rpath, root) else rp, "sha256": sha256_file(rpath)}
    recorded = realization.get("sha256")
    if not isinstance(recorded, str):
        return None
    for folder in (esp.parent, *esp.parent.parents):
        if not _inside(folder, root):
            break
        copy = folder / rpath.name
        if copy.is_file() and sha256_file(copy) == recorded:
            return {"path": rp, "sha256": recorded}
    return None


def evidence_overlap(conv: dict, bench: dict, var: dict | None) -> list[dict]:
    """A1.11 (D7): the runs that serve more than one decision of the study (convergence gate, statistical target,
    each benchmark and its controls, the variation table), so that they are not read as independent evidence."""
    uses: dict[str, set] = {}

    def use(run, decision):
        if run:
            uses.setdefault(str(run), set()).add(decision)
    for s in conv.get("summaries", []):
        rid = (s.get("run_record") or {}).get("artifact_id")
        use(rid, "convergence")
        if s.get("role") == "nominal":
            use(rid, "statistical-target")
    for b in bench.get("benchmarks", []):
        use((b.get("configuration_basis") or {}).get("artifact_id") or (b.get("inputs") or {}).get("run_record"),
            f"benchmark:{b.get('benchmark')}")
        for c in (b.get("negative_control") or {}).get("controls", []):
            use(c.get("run_record"), f"benchmark:{b.get('benchmark')}")
    if var:
        use((var.get("nominal") or {}).get("run_record_id") or (var.get("nominal") or {}).get("summary"), "variations")
        for v in var.get("variations", []):
            use(v.get("run_record_id") or v.get("summary"), "variations")
    return [{"run": r, "decisions": sorted(d)} for r, d in sorted(uses.items()) if len(d) > 1]


def bound_inputs(study: dict, declared: dict, qualifying: bool, results: dict | None, args) -> list[str]:
    """CV-B2: gaps unless the declared hash keys and the results file describe this study's own inputs. The results
    file must come from a reconstruction record that is one of --run-record (same id and sha256), with the same tail
    sources; on a qualification path the declared geometry, realization, field-configuration and reco-spec hashes
    must equal the ones derived from --geometry, the element_sim spec (and its provenance) and that reco record, so
    verifications of another configuration cannot be borrowed by copying their hashes."""
    gaps: list[str] = []
    reco = None
    if results is not None:
        want = results.get("reco_record") or {}
        for path in args.run_record or []:
            if sha256_file(Path(path)) == want.get("sha256") and load_json(path).get("artifact_id") == want.get("artifact_id"):
                reco = load_json(path)
        if reco is None:
            gaps.append(f"the results file's reco record {want.get('artifact_id')!r} is not one of the study's run "
                        "records (--run-record, same sha256)")
        else:
            rx = get(reco, "extension.reconstruction") or {}
            if list(rx.get("tail_sources_simulated") or []) != list(results.get("tail_sources_simulated") or []):
                gaps.append(f"the results file lists tail sources {results.get('tail_sources_simulated')}, its reco "
                            f"record {rx.get('tail_sources_simulated')}")
    if not qualifying:
        return gaps
    program, es = sim_spec(study)
    actual: dict = {}
    if args.geometry:
        actual["geometry_sha256"] = sha256_file(Path(args.geometry))
    if program == "element_sim":
        actual["field_configuration_sha256"] = B.field_configuration_sha256(es)
        prov = es.get("provenance") or {}
        if isinstance((prov.get("realization") or {}).get("sha256"), str):
            actual["realization_sha256"] = prov["realization"]["sha256"]
        g = (prov.get("geometry") or {}).get("sha256")
        if g and actual.get("geometry_sha256") and g != actual["geometry_sha256"]:
            gaps.append(f"the element_sim spec was derived from geometry sha256 {g}, --geometry has "
                        f"{actual['geometry_sha256']}")
    if reco is not None:
        actual["reco_spec_sha256"] = B.reco_spec_sha256(get(reco, "extension.reconstruction.reco_spec") or {})
    for key in ("geometry_sha256", "realization_sha256", "field_configuration_sha256", "reco_spec_sha256"):
        if key not in actual:
            gaps.append(f"qualification: {key} cannot be derived from the study's own inputs (--geometry, the "
                        "derived element_sim spec, the results file's reco record)")
        elif declared.get(key) != actual[key]:
            gaps.append(f"qualification: the declared {key} {declared.get(key)} is not the study's own {actual[key]}")
    return gaps


def cmd_label(args) -> tuple[str, dict]:
    spec_path = Path(args.spec)
    study = load_study(spec_path)
    root = Path(args.project_root)
    bench = load_json(args.benchmarks)
    conv = load_json(args.convergence)
    var = load_json(args.variations) if args.variations else None
    results = load_json(args.results) if args.results else None
    if results is not None:  # B2.6: the F4 results file and the geometry file it was computed for
        if results.get("schema") != "f4-results/1" or not isinstance(results.get("results"), dict):
            raise StudyError(f"{args.results} is not an f4-results/1 file (geant4_run.py table --f4-results)")
        if args.geometry:
            gsha = sha256_file(Path(args.geometry))
            if (results.get("geometry") or {}).get("sha256") != gsha:
                raise StudyError(f"the results file names geometry sha256 {(results.get('geometry') or {}).get('sha256')}"
                                 f", --geometry {args.geometry} has {gsha}")
    elif args.geometry:
        raise StudyError("--geometry goes with --results")
    gaps = list(bench.get("gaps", []))
    for b in bench.get("benchmarks", []):
        if b.get("grade") in B.UPGRADING and b.get("verdict") == "fail":
            gaps.append(f"{b['benchmark']} failed: relative difference {b['relative_difference']:+.4g} beyond the "
                        f"tolerance {b['tolerance']['total']:.4g} ({b['reference']['source'][:60]}...)")
    if conv.get("convergence", {}).get("gate") != "pass":
        gaps.append("convergence gate not passed: " + "; ".join(
            f"{p['parameter']} {p['verdict']}" for p in conv.get("convergence", {}).get("parameters", [])))
    if conv.get("record_problems"):
        gaps += [f"record: {p}" for p in conv["record_problems"]]
    if conv.get("statistical_target", {}).get("verdict") in ("fail", "target-missed"):
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
    if get(study, "downstream_use.kind") in ("report", "paper", "talk", "thesis", "proposal"):
        lit = get(study, "citations.literature_record")
        lit_doc = None
        if isinstance(lit, str) and (spec_path.parent / lit).is_file():
            lit_doc = load_json(spec_path.parent / lit)
        if not lit_doc or lit_doc.get("artifact_type") != "literature-record":
            gaps.append("written downstream use without a literature record (citations.literature_record): cite the "
                        "Geant4 papers, version and documents from one, never from memory (R8)")
    if not any(b.get("validation_evidence") for b in bench.get("benchmarks", [])):
        gaps.append("no reference benchmark is validation evidence for this study (R5 not met)")
    declared = dict(get(study, "validation_plan.scope") or {})
    if get(study, "observable.kind") is not None:  # CV-A1: the controlled kind is part of the declared scope
        declared["observable_kind"] = get(study, "observable.kind")
    eligible = []
    qmissing = qualification_missing(declared, bench.get("benchmarks", []))
    if qmissing is not None:  # CV-B2 (B2.8): a detector-level kind qualifies through every condition of its path
        gaps += [f"qualification ({declared['observable_kind']}): {q}" for q in qmissing]
        if not qmissing and conv.get("convergence", {}).get("gate") == "pass":
            eligible.append({"qualification": declared["observable_kind"],
                             "benchmarks": [b["benchmark"] for b in bench.get("benchmarks", [])
                                            if b.get("grade") in ("verification", "reference")]})
    gaps += bound_inputs(study, declared, qmissing is not None, results, args)
    for b in bench.get("benchmarks", []) if qmissing is None else []:
        if b.get("validation_evidence"):
            outside = scope_outside(declared, b["scope"], b["benchmark"])
            if outside:
                gaps += [f"{b['benchmark']}: {o}" for o in outside]
            elif conv.get("convergence", {}).get("gate") == "pass":
                eligible.append({"benchmark": b["benchmark"], "scope": b["scope"]})
    run_refs, seen, installations = [], {}, []
    for path in args.run_record or []:
        rec = load_json(path)
        if rec.get("artifact_type") != "computational-run":
            raise StudyError(f"{path}: not a computational-run")
        sim = get(rec, "extension.simulation") or {}
        if sim.get("evidence_role") == "search":  # CV-C2 (C2.6): search values select designs, they are no evidence
            raise StudyError(f"{path}: a Geant4 search run (evidence_role search) cannot be evidence of a study; a "
                             "confirmation study runs on its own seeds")
        key = (("S", sim["logical_run_seed"]) if sim.get("seed_scheme") == "hash-v1" else
               ("legacy", tuple(get(rec, "extension.seeds.layered_sim") or sim.get("random", {}).get("seeds") or [])))
        if key in seen and key[1]:  # A1.4: S (or a legacy run's full seed pair) is not repeated within a study
            raise StudyError(f"{path}: {'logical-run seed' if key[0] == 'S' else 'legacy seed pair'} {key[1]} repeats "
                             f"{seen[key]}")
        seen[key] = path
        run_refs.append({"ref": _rel(Path(path), root), "artifact_type": "computational-run",
                         "artifact_id": rec["artifact_id"], "version": rec["contract_version"],
                         "sha256": sha256_file(Path(path)), "status": rec["status"]})
        inst = B.geant4_installation(rec)  # None for records from before adapter 0.6.0 (source builds)
        if inst:
            installations.append({"artifact_id": rec["artifact_id"], **inst})
    for path in args.reference_record or []:
        rec = load_json(path)
        run_refs.append({"ref": _rel(Path(path), root), "artifact_type": rec.get("artifact_type"),
                         "artifact_id": rec.get("artifact_id"), "version": rec.get("contract_version"),
                         "sha256": sha256_file(Path(path)), "status": rec.get("status", [])})
    overlap = evidence_overlap(conv, bench, var)
    labels = ["unvalidated"] + [s for r in run_refs for s in r["status"] if s in PROPAGATING]
    labels = list(dict.fromkeys(labels))
    upgrade, refused = False, []
    if args.upgrade:
        if not eligible and qmissing is not None:
            refused.append(f"the {declared['observable_kind']} qualification path does not hold (B2.8: every "
                           "condition passed and matched by its own scope keys, and a passed convergence gate)")
        elif not eligible:
            refused.append("no scope is eligible (a passed reference benchmark with its control caught, a passed "
                           "convergence gate, the declared scope inside the benchmark scope)")
        if gaps:
            refused.append(f"{len(gaps)} gap(s) remain")
        n_ref = len(args.reference_record or [])
        evidence = run_refs[:len(run_refs) - n_ref] if n_ref else run_refs
        if not evidence:
            refused.append("no run record to reference as evidence")
        upgrade = not refused
    if upgrade:  # phase 2 (contracts 3.1.0): the run records become evidence records, their labels not inherited
        refs = run_refs[len(evidence):]
        labels = ["validated-in-scope"] + [s for r in refs for s in r["status"] if s in PROPAGATING and
                                           s != "unvalidated"]
        labels = list(dict.fromkeys(labels))
    doc = {"highest_usable_label": "validated-in-scope" if upgrade else "unvalidated", "labels": labels, "gaps": gaps,
           "upgrade": ("re-issued as validated-in-scope" if upgrade else
                       {"refused": refused} if args.upgrade else "not requested"),
           "phase2_upgrade_eligible_scopes": eligible,
           "note": "without --upgrade the record stays unvalidated with its evidence and scope embedded; --upgrade "
                   "re-issues it as validated-in-scope only when a scope is eligible and no gap remains (contracts "
                   "3.1.0 rule geant4.upgrade_*)"}
    if installations:  # adapter 0.6.0 run records: how Geant4 was installed; a registered one is weaker provenance
        doc["geant4_installations"] = installations
        weaker = [i["artifact_id"] for i in installations if i["origin"] == "registered"]
        if weaker:
            doc["provenance_notes"] = [f"{len(weaker)} run record(s) ran on a registered Geant4 installation (no "
                                       "source commit, build options or dataset MD5s; datasets content-hashed only): "
                                       "state the installation and its origin when reporting (protocol section 9)"]
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
        geometry_block = None
        if results is not None:
            manifest.append({"path": _rel(Path(args.results), root), "sha256": sha256_file(Path(args.results))})
        if args.geometry:
            gp = Path(args.geometry)
            geometry_block = {"path": _rel(gp, root), "sha256": sha256_file(gp)}
            manifest.append(dict(geometry_block))
        es = get(study, "physics.element_sim_spec")
        if isinstance(es, str):  # the derived element_sim spec and the realization profile its provenance names
            esp = spec_path.parent / es
            manifest.append({"path": _rel(esp, root), "sha256": sha256_file(esp)})
            prov = load_json(esp).get("provenance") or {}
            entry = realization_entry(prov.get("realization") or {}, esp, root)
            if entry:
                manifest.append(entry)
        record = {
            "contract_version": CONTRACTS_VERSION, "artifact_id": study.get("study_id", "geant4-study") + "-study",
            "artifact_type": "computational-run",
            "objective": f"Geant4 study record: {get(study, 'observable.name')} for {get(study, 'particle.name')} "
                         f"{get(study, 'particle.energy_MeV')} MeV; benchmarks, convergence and scope embedded "
                         "(unvalidated in phase 1)",
            "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": plugin_version, "contracts": CONTRACTS_VERSION, "profiles": {}},
            "provenance": {"producer_skill": "hep-detector", **trace.provenance(), "created": created, "evidence_ids": []},
            "inputs": run_refs[len(evidence):] if upgrade else run_refs, "outputs": [], "unresolved_inputs": [],
            "status": labels,
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
                                    "evidence_overlap": overlap, "evidence_overlap_version": 1,
                                    "highest_usable_label": doc["highest_usable_label"]}}}
        if installations:
            record["extension"]["study"]["geant4_installations"] = installations
            if doc.get("provenance_notes"):
                record["extension"]["study"]["provenance_notes"] = doc["provenance_notes"]
        if args.upgrade and not upgrade:  # kept in the record, so evaluate_design.py f4 refuses it later too
            record["extension"]["study"]["upgrade_refused"] = refused
        if results is not None:  # B2.6: kept across the re-issue (label rebuilds the record from scratch)
            kept = results["results"]
            ref = qualification_reference(declared.get("observable_kind"), bench.get("benchmarks", [])) \
                if qmissing == [] else None
            if ref is not None:  # D0-c: the value is no more accurate than what the qualification certifies
                kept = {fom: qualified_uncertainty(r, ref) if isinstance(r, dict) else r for fom, r in kept.items()}
            record["extension"]["study"]["results"] = kept
            record["extension"]["study"]["tail_sources_simulated"] = list(results.get("tail_sources_simulated", []))
            if geometry_block:
                record["extension"]["study"]["geometry"] = geometry_block
        if upgrade:
            record["artifact_id"] = record["artifact_id"].removesuffix("-study") + "-study-validated"
            record["required_capabilities"] = ["core:evidence-records"]
            record["extension"]["evidence_records"] = [
                {"ref": r["ref"], "sha256": r["sha256"], "artifact_id": r["artifact_id"],
                 "artifact_type": "computational-run", "role": "Geant4 run"} for r in evidence]
            record["objective"] = record["objective"].replace("(unvalidated in phase 1)",
                                                              "(validated-in-scope: phase 2, contracts 3.1.0)")
        write_json(out, record)
        doc["record"] = str(out)
    return "ok", doc


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("spec", help="completeness and physics rules of a study spec")
    p.add_argument("--spec", required=True)
    p.add_argument("--rules")
    p.add_argument("--effective-config", help="an effective config (geant4 adapter 0.2.0): the thin-layer rule reads "
                                              "the minimum thickness from its geometry tree")
    p = sub.add_parser("run", help="records against the spec, statistical target, convergence gate")
    p.add_argument("--spec", required=True)
    p.add_argument("--summary", action="append", required=True,
                   help="[ROLE=]SUMMARY.json (simulation-summary/1, or a legacy geant4-run-summary/1); ROLE nominal or "
                        "scan (default the summary's evidence_role)")
    p.add_argument("--out")
    p = sub.add_parser("variations", help="variation table with model assignments")
    p.add_argument("--spec", required=True)
    p.add_argument("--nominal", required=True)
    p.add_argument("--variation", action="append", required=True, help="NAME=SUMMARY.json")
    p.add_argument("--effective-config", action="append",
                   help="NAME=EFFECTIVE_CONFIG.json (NAME nominal or a variation; geant4 adapter 0.2.0): the hadronic "
                        "model assignment reads the probe first (source probe), else the declared table")
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
    p.add_argument("--results", help="the f4-results/1 file of geant4_run.py table: written into the study block "
                                     "(results, tail_sources_simulated) and the input manifest (Geant4 program B2.6)")
    p.add_argument("--geometry", help="the design-geometry/1 file the study used (its sha256 must equal the results "
                                      "file's); listed in the input manifest with the realization profile and the "
                                      "derived element_sim spec")
    p.add_argument("--upgrade", action="store_true",
                   help="phase 2: re-issue an eligible study with no gaps as validated-in-scope (run records become "
                        "evidence records); otherwise the record stays unvalidated and the refusal is reported")
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(args).items() if k != "status" and not (k == "effective_config" and v is None)}
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("rules", "bootstrap", "seed", "mpv_bin_mev", "tail_threshold_mev", "created", "status")
                if hasattr(args, k) and f"--{k.replace('_', '-')}" not in given]
    handlers = {"spec": cmd_spec, "run": cmd_run, "variations": cmd_variations,
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
