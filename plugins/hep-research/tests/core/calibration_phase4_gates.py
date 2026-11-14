"""Simulator calibration phase 4: the gate harness (Part B section 17, phase 4 gate: "Negative tests of the contribution
decomposition and the g4sim binding (section 15.3); specialization does not require modifying the generic layer").

Three items, each from the registered card (`simcal-tasks/phase-4.md`, gate designs):
- `contrib_negatives`: the section 15.3.18 contribution-decomposition tests (negatives caught, positive controls pass);
- `g4sim_binding`: every case of section 15.3.19 and the A21 cases, each mapped to its test(s) (CASES); the case
  "scintillation log_density switched to the normal density -> P0 fails" is recorded, not judged (A23: P0 does not
  distinguish it on the toy detector; the g4sim path re-digitizes);
- `generic_layer`: the eight node-binding examples pass the existing contract checker, P4 and candidate methods, and
  the commit that added the specialization documents touches no file under the generic layer (GENERIC_PATHS).

Usage (from a clean worktree at the registering commit): `python -I tests/core/calibration_phase4_gates.py --run --out
FILE`; every result `synthetic` where it uses fixtures."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase3_gates as P3G  # noqa: E402  (run_tests: the same unit-test runner as phase 3)

from core.calibration import io  # noqa: E402

LABEL = "synthetic"
UNIT_RULE = ("every listed test passes (a negative test passing means its negative case is caught and its positive "
             "control passes); any skip, failure or error fails the item")
SPECIALIZATION_COMMIT = "e661b3fd"            # WP-P: the commit that added simulation-calibration/ (card, A21)
GENERIC_PATHS = ("plugins/hep-research/core/", "plugins/hep-research/contracts/schemas/",
                 "plugins/hep-research/skills/hep-statistics/scripts/")
M = "test_calibration_"

CONTRIB = {
    "part": "negative tests of the contribution decomposition (section 15.3.18)",
    "tests": {M + "contrib.Decomposition.test_negative_some_subset_below_the_ess_threshold": "negative",
              M + "contrib.Decomposition.test_negative_exactly_one_subset_fails": "negative",
              M + "contrib.Decomposition.test_missing_support_fails": "negative",
              M + "contrib.Sampling.test_sampling_negative": "negative",
              M + "contrib.Declarations.test_object_is_required": "negative",
              M + "contrib.Declarations.test_effect_declarations": "negative",
              M + "contrib.Declarations.test_evaluator_that_cannot_remove_effects_is_incomplete": "negative",
              M + "contrib.Decomposition.test_positive_control_outputs_the_decomposition": "positive",
              M + "contrib.Decomposition.test_terms_sum_to_the_total_on_every_permutation": "positive",
              M + "contrib.Decomposition.test_bootstrap_covariance": "positive",
              M + "contrib.Sampling.test_permutation_sampling": "positive",
              M + "contrib.Declarations.test_variance_and_resolution_objects": "positive",
              M + "contrib.EffectsOffHook": "positive",
              M + "g4sim_eval.Redigitization.test_effects_off_sets_the_removal_values_last": "positive"}}

# section 15.3.19 (Part B lines 3467-3487) and the A21 cases: case -> tests (each negative with its positive control)
CASES = [
    ("node 0 uses an `external` source -> rejected", [M + "contract.OtherClauses.test_g4sim_source",
                                                      M + "g4sim_eval.NodeZero.test_external_source_is_rejected",
                                                      M + "design_g4sim.Support.test_external_source_has_no_density"]),
    ("a model lacks one of the five identity items -> rejected", [M + "model_identity.ContractClause1Item2"]),
    ("two physics lists without a confirmation record -> rejected",
     [M + "contract.OtherClauses.test_physics_list_confirmation",
      M + "specialization.Engine.test_two_physics_lists_need_their_confirmation_record"]),
    ("a node to be reweighted recorded only as `moments` -> infeasible",
     [M + "design_g4sim.Support.test_moments_recording_is_infeasible",
      M + "g4sim_binding.Table2.test_15_3_19_moments_only_is_infeasible"]),
    ("kill_policy minimum kinetic energy below an observable's dependence -> missing support",
     [M + "design_g4sim.Support.test_kill_policy_minimum_energy_is_missing_support"]),
    ("G8 declared while the pseudo-data fit MC only changes the Philox replica -> rejected; G8 not run -> "
     "closure-not-tested", [M + "design_g4sim.Intervals.test_g8_fit_mc_changing_only_the_response"]),
    ("the two MC sets of P7 share Geant4 events -> rejected", [M + "design_g4sim.Intervals.test_p7_sets_sharing_events"]),
    ("known photon count between light collection and PDE on the efficiency-map path -> rejected",
     [M + "g4sim_binding.Refusals.test_15_3_19_known_photon_count_between_light_collection_and_pde"]),
    ("PDE split declaration errors -> rejected", [M + "pde_split.ContractRules", M + "pde_split.SplitCheck",
                                                  M + "pde_split.DesignRules",
                                                  M + "g4sim_binding.Refusals.test_pde_split_parameter_needs_its_declaration"]),
    ("map varies with theta: wrong replica coupling or surrogate -> rejected; fixed-map linear construction for a "
     "non-linear observable -> rejected", [M + "map.TestMapPlan"]),
    ("shared seed whose mapping runs' primaries.csv disagree -> rejected",
     [M + "map.TestMapPlan.test_shared_seed_and_interval", "test_calibration_map_patterns"]),
    ("g4sim-digi-job/1 with changed run_seed, replica != 0, keys and conditions, or fields differing from the "
     "documents -> rejected", [M + "design_g4sim.DigiJobs", M + "model_identity.DigiJob"]),
    ("exported condition-snapshot/1 or alignment-overlay/1 without the result's hash in source_of_facts -> rejected "
     "(A21 19-g6)", [M + "export.CheckExport", M + "export.Export"]),
    ("after build_hash changes -> the result needs a redo", [M + "model_identity.IdentityChangeRedo"]),
    ("g4sim output as the calibration release -> projection; only the validation release -> calibrated-unvalidated",
     [M + "use.SimulatedReleases"]),
    ("A21 19-g7: T2 carry-over (a passing pre-registered record keeps the result flagged; failing, missing or late "
     "records redo)", [M + "deps.IdentityChange", M + "use.IdentityCarriedOver"]),
    ("section 10.3: upstream revision or downgrade -> downstream redo; same-kappa re-judgment -> no redo",
     [M + "deps.UpstreamInvalidation"]),
    ("discrete run-card fields (physics lists, PAI, XTR, optical, decay) bound as theta -> refused",
     [M + "g4sim_binding.Refusals.test_discrete_model_seeds_and_run_block"]),
]
RECORDED = [("scintillation log_density switched to the normal density -> P0 fails (Part B); A23: recorded, not judged",
             [M + "kernel_check.NormalDensityRecord"])]

GENERIC = {"part": "specialization does not require modifying the generic layer (section 12, section 17)",
           "tests": {M + "specialization.Engine": "positive", M + "specialization.Scripts": "positive",
                     M + "specialization.Pages": "positive"}}


def _run(ids: list) -> dict:
    return P3G.run_tests(ids)


def judge_tests(name: str, part: str, kinds: dict, outcomes: dict) -> dict:
    rows, ok = [], True
    for tid, out in sorted(outcomes.items()):
        kind = next((k for n, k in kinds.items() if tid == n or tid.startswith(n + ".")), "positive")
        o = out["outcome"]
        status = ("caught" if kind == "negative" else "passed") if o == "passed" else o
        ok = ok and o == "passed"
        rows.append({"test": tid, "kind": kind, "status": status})
    not_run = [n for n in kinds if not any(t == n or t.startswith(n + ".") for t in outcomes)]
    return {"item": name, "part": part, "rule": UNIT_RULE, "tests": rows, "not_run": not_run,
            "passed": bool(ok and outcomes and not not_run)}


def contrib_item() -> dict:
    return judge_tests("contrib_negatives", CONTRIB["part"], CONTRIB["tests"], _run(list(CONTRIB["tests"])))


def binding_item() -> dict:
    cases, ok = [], True
    for label, ids in CASES:
        outs = _run(ids)
        missing = [n for n in ids if not any(t == n or t.startswith(n + ".") for t in outs)]
        passed = bool(outs) and all(o["outcome"] == "passed" for o in outs.values()) and not missing
        ok = ok and passed
        cases.append({"case": label, "tests": {t: o["outcome"] for t, o in sorted(outs.items())}, "not_run": missing,
                      "passed": passed})
    recorded = []
    for label, ids in RECORDED:
        outs = _run(ids)
        recorded.append({"case": label, "tests": {t: o["outcome"] for t, o in sorted(outs.items())}, "judged": False})
    return {"item": "g4sim_binding", "part": "negative tests of the g4sim binding (section 15.3.19) and the A21 cases",
            "rule": "every case's tests pass (each negative caught, each control passing); the A23 case recorded",
            "cases": cases, "recorded_not_judged": recorded, "passed": ok}


def generic_item() -> dict:
    j = judge_tests("generic_layer", GENERIC["part"], GENERIC["tests"], _run(list(GENERIC["tests"])))
    try:
        files = subprocess.run(["git", "diff", "--name-only", f"{SPECIALIZATION_COMMIT}^", SPECIALIZATION_COMMIT],
                               cwd=ROOT, capture_output=True, text=True, check=True, timeout=60).stdout.split()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return dict(j, diff={"error": str(exc)}, passed=False)
    touched = sorted(f for f in files if f.startswith(GENERIC_PATHS))
    j["diff"] = {"commit": SPECIALIZATION_COMMIT, "files": len(files), "generic_layer_files": touched}
    j["rule"] = UNIT_RULE + "; and the specialization commit touches no file under " + ", ".join(GENERIC_PATHS)
    j["passed"] = bool(j["passed"] and files and not touched)
    return j


def provenance() -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                            timeout=60).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True,
                                timeout=60).stdout.strip())
    return {"commit": commit, "dirty": dirty, "python": sys.version.split()[0]}


def run_gate() -> dict:
    t0 = time.time()
    items = {"contrib_negatives": contrib_item(), "g4sim_binding": binding_item(), "generic_layer": generic_item()}
    prov = provenance()
    ok = all(v["passed"] for v in items.values()) and not prov["dirty"]
    return {"gate": "phase 4 (section 17): negative tests of the contribution decomposition and the g4sim binding "
                    "(section 15.3); specialization does not require modifying the generic layer",
            "gate_status": "passed" if ok else "failed", "passed": {k: v["passed"] for k, v in items.items()},
            "items": items, "provenance": prov, "seconds": time.time() - t0, "label": LABEL}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.list:
        print(json.dumps({"contrib": list(CONTRIB["tests"]), "cases": [c for c, _ in CASES],
                          "recorded": [c for c, _ in RECORDED], "generic": list(GENERIC["tests"])}, indent=1))
        return 0
    if a.run:
        if not a.out:
            ap.error("--out is required with --run")
        r = run_gate()
        io.write_json(a.out, io.jsonable(r))
        print(json.dumps({"gate_status": r["gate_status"], "passed": r["passed"]}))
        return 0 if r["gate_status"] == "passed" else 1
    ap.error("one of --run, --list")
    return 2


if __name__ == "__main__":
    sys.exit(main())
