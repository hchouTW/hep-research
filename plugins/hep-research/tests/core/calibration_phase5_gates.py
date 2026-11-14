"""Simulator calibration phase 5: the gate harness (task card `simcal-tasks/phase-5.md`, "Gate designs" items 1-4; WP-U).
Not a unit test module.

Items:
1. `negatives`: units items G4L, POOLING, VMODEL_INFERRED (lists of test identifiers), judged like phases 3 and 4: every
   listed test passes (a negative passing means its negative is caught and its positive control passes); any skip,
   failure or error fails; every listed name must load. An empty list fails (the lists are filled by the main session
   after WP-Q, WP-R and WP-S merge).
2. `prior_gates_static`: `git diff --name-only <phase-5 base> HEAD` names none of PROTECTED (pathspecs from the
   repository root), and the phase-0..4 entries of `simcal-task-registry.json` equal those at the base.
3. `prior_gates_rerun`: `--dispatch DIR` writes the Slurm scripts and the login commands that rerun each earlier gate as
   its card registered it, driving the earlier harnesses unchanged (nothing is submitted); `--merge-rerun DIR` judges
   each earlier item by its own registered rule. Numerical differences from the recorded evidence are reported, not
   judged.
4. `default_off_identity`: the outputs of the engine and of `calib_*.py` on a fixed set of phase-0..4 inputs, captured
   as golden JSON at the phase-5 base (`--capture-golden`, run once, before any WP merges), are byte-identical at the
   gate commit except the fields listed in MASKED_KEYS.

Usage (from a clean worktree at the gate commit):
  python -I tests/core/calibration_phase5_gates.py --run --out FILE                items 1, 2, 4 (login host, minutes)
  python -I tests/core/calibration_phase5_gates.py --dispatch DIR --commit SHA --worktree WT     item 3: write scripts
  python -I tests/core/calibration_phase5_gates.py --merge-rerun DIR --out FILE                  item 3: judge
  python -I tests/core/calibration_phase5_gates.py --units KEY --out FILE    an earlier unit-test item (Slurm task)
  python -I tests/core/calibration_phase5_gates.py --capture-golden          item 4: golden capture (phase-5 base only)
  python -I tests/core/calibration_phase5_gates.py --list
Every result `synthetic` where it uses fixtures."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]            # plugin root
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

from core.calibration import io  # noqa: E402

# calibration_phase3_gates is imported only where its merge is needed: its imports register the g4sim evaluator kind,
# which changes what an earlier unit test expects (test_calibration_toy: an unknown kind "g4sim" is unavailable).

LABEL = "synthetic"
PHASE_BASE = "c7e5a610"            # the phase-5 base (card): origin/main at release 0.67.0
UNIT_RULE = ("every listed test passes (a negative test passing means its negative case is caught and its positive "
             "control passes); any skip, failure or error fails the item; every listed name must load; an empty "
             "list fails")
M = "test_calibration_"
SCRIPTS = "tests.skills.test_calib_scripts."
PLUGIN = "plugins/hep-research/"     # repository-relative prefix of the plugin
SIMCAL_DOCS = "docs/dev/simulator-calibration/"

# ------------------------------------------------------------------ item 1: negatives (placeholders, filled later)
# TODO(main session, after WP-Q, WP-R and WP-S merge): fill each list with {test id: "negative" | "positive"}; the
# card registers the lists before the gate run. While a list is empty the item fails (status `lists-not-filled`).
G4L: dict = {}               # TODO section 15.3.1 G4-L and section 15.3.16 (WP-R)
POOLING: dict = {}           # TODO section 15.3.18 partial pooling (WP-Q)
VMODEL_INFERRED: dict = {}   # TODO inferred V_model tests (a)-(d), as accepted per V6 (WP-S)
NEGATIVES = {"G4L": ("section 15.3.1 G4-L and section 15.3.16", G4L),
             "POOLING": ("section 15.3.18 partial pooling", POOLING),
             "VMODEL_INFERRED": ("inferred V_model tests (a)-(d) (V6)", VMODEL_INFERRED)}


def judge_tests(name: str, part: str, kinds: dict, outcomes: dict) -> dict:
    """UNIT_RULE on recorded outcomes ({test id: {"outcome": ...}}); kinds {listed name: negative|positive}."""
    if not kinds:
        return {"item": name, "part": part, "rule": UNIT_RULE, "tests": [], "not_run": [], "passed": False,
                "status": "lists-not-filled"}
    rows, ok = [], True
    for tid, out in sorted(outcomes.items()):
        kind = next((k for n, k in kinds.items() if tid == n or tid.startswith(n + ".")), "positive")
        o = out["outcome"]
        status = ("caught" if kind == "negative" else "passed") if o == "passed" else o
        ok = ok and o == "passed"
        rows.append({"test": tid, "kind": kind, "status": status,
                     **{k: v for k, v in out.items() if k != "outcome"}})
    not_run = [n for n in kinds if not any(t == n or t.startswith(n + ".") for t in outcomes)]
    return {"item": name, "part": part, "rule": UNIT_RULE, "tests": rows, "not_run": not_run,
            "passed": bool(ok and outcomes and not not_run)}


def _ids(suite) -> list:
    out = []
    for t in suite:
        out += _ids(t) if isinstance(t, unittest.TestSuite) else [t.id()]
    return out


def run_tests(ids: list) -> dict:
    """{test id: outcome} of the given names, in this process; the same runner as calibration_phase3_gates.run_tests
    (phases 3 and 4), kept here so that running tests does not import that harness (see above)."""
    loader = unittest.TestLoader()
    outcomes: dict = {}
    for name in ids:
        try:
            suite = loader.loadTestsFromName(name)
        except Exception as exc:                          # noqa: BLE001 (a missing test is a failed gate item)
            outcomes[name] = {"outcome": "error", "detail": f"not loadable: {exc}"}
            continue
        names = _ids(suite)
        res = unittest.TestResult()
        suite.run(res)
        got = {t: {"outcome": "passed"} for t in names}
        for kind, rows in (("failed", res.failures), ("error", res.errors)):
            for tc, tb in rows:
                got[tc.id()] = {"outcome": kind, "detail": tb[-2000:]}
        for tc, reason in res.skipped:
            got[tc.id()] = {"outcome": "skipped", "reason": reason}
        for tc in [x for x, _ in res.expectedFailures] + list(res.unexpectedSuccesses):
            got[tc.id()] = {"outcome": "failed", "detail": "an expected-failure marker"}
        for t in [t for t in got if t.startswith("unittest.loader._FailedTest")]:
            got[name] = {**got.pop(t), "outcome": "error"}
        outcomes.update(got or {name: {"outcome": "error", "detail": "no test ran"}})
    return outcomes


def negatives_item() -> dict:
    parts = {}
    for key, (part, kinds) in NEGATIVES.items():
        parts[key] = judge_tests(key, part, kinds, run_tests_by_module(list(kinds)) if kinds else {})
    return {"item": "negatives", "rule": UNIT_RULE, "lists": parts, "passed": all(v["passed"] for v in parts.values())}


# ------------------------------------------------------------------ item 2: prior_gates_static
PROTECTED = tuple([PLUGIN + f"tests/core/calibration_phase{k}_gates.py" for k in (1, 2, 3, 4)]
                  + [PLUGIN + "tests/core/calibration_exhaustive.py"]
                  + [PLUGIN + SIMCAL_DOCS + f"simcal-tasks/phase-{k}.md" for k in range(5)]
                  + [PLUGIN + SIMCAL_DOCS + f"simcal-gates/phase-{k}.md" for k in range(5)])
REGISTRY = PLUGIN + SIMCAL_DOCS + "simcal-task-registry.json"
PRIOR_CARDS = tuple(f"simcal-tasks/phase-{k}.md" for k in range(5))


def _git(*args, check=True) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=check, timeout=120).stdout


def prior_registry_entries(registry: dict) -> list:
    """The phase-0..4 registrations, in order, each a JSON object (compared as canonical JSON)."""
    return [e for e in registry.get("registrations", []) if e.get("card") in PRIOR_CARDS]


def judge_static(changed: list, base_entries: list, head_entries: list) -> dict:
    touched = sorted(f for f in changed if f in PROTECTED)
    canon = [json.dumps(e, sort_keys=True) for e in base_entries], [json.dumps(e, sort_keys=True) for e in head_entries]
    reg_ok = bool(base_entries) and canon[0] == canon[1]
    diff = [i for i in range(max(len(canon[0]), len(canon[1])))
            if i >= len(canon[0]) or i >= len(canon[1]) or canon[0][i] != canon[1][i]]
    return {"protected_files_changed": touched, "registry_entries_base": len(base_entries),
            "registry_entries_head": len(head_entries), "registry_entries_differing": diff,
            "passed": not touched and reg_ok}


def static_item(base: str = PHASE_BASE) -> dict:
    rule = (f"git diff --name-only {base} HEAD (pathspecs from the repository root) names none of the protected files, "
            "and the phase-0..4 entries of simcal-task-registry.json equal those at the base (canonical JSON)")
    try:
        changed = _git("diff", "--name-only", base, "HEAD", "--", *(":(top)" + p for p in PROTECTED)).split()
        changed_all = _git("diff", "--name-only", base, "HEAD").split()
        base_reg = json.loads(_git("show", f"{base}:{REGISTRY}"))
        top = Path(_git("rev-parse", "--show-toplevel").strip())
        head_reg = json.loads((top / REGISTRY).read_text())
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return {"item": "prior_gates_static", "rule": rule, "error": str(exc), "passed": False}
    j = judge_static(sorted(set(changed) | {f for f in changed_all if f in PROTECTED}),
                     prior_registry_entries(base_reg), prior_registry_entries(head_reg))
    return {"item": "prior_gates_static", "rule": rule, "base": base, "protected": list(PROTECTED), **j}


# ------------------------------------------------------------------ item 3: prior_gates_rerun
# earlier unit-test items that the earlier harnesses do not run themselves (phase 0 card item 2 and 3; phase 1 gate 1,
# the tests of its gate record); module `test_calibration_<x>` written M + x
P0_NAMED = {M + "chain.ReferenceCoverage.test_15_3_1_p4_subgraph": "negative",
            M + "contract.OtherClauses.test_15_3_1_p7_parameter_shift_alternative": "negative",
            **{M + "contract.ContractRulesSection15dot3dot2." + t: "negative" for t in (
                "test_contains_data_values", "test_roles_overlap", "test_dependency_cycle", "test_stage_graph_cycle",
                "test_simulation_bins_by_true_value", "test_model_enumerated_and_absorbed",
                "test_inferred_form_without_holdout", "test_kernel_not_positive_definite", "test_block_rule",
                "test_injection_without_node_split", "test_link_range_mismatch", "test_shape_bins_as_scalars_or_k_minus_1",
                "test_merging_rule", "test_conversion_relation_missing",
                "test_redundant_measurement_without_comparison_node", "test_upstream_usage_and_role")},
            M + "data.IngestionAndSealing.test_ingestion_requires_declarations": "negative",
            M + "data.IngestionAndSealing.test_sealed_components": "negative",
            M + "contract.DataReleaseAndSharing.test_15_3_3_observed_only_statistical": "negative",
            **{M + "data.OpeningPreconditions." + t: "negative" for t in (
                "test_lineage_unconfirmed_not_opened", "test_p7_incomplete_not_opened", "test_toy_replicas_not_generated",
                "test_k0_zero_no_read", "test_pre_opening_ratio_test", "test_holdout_sharing_rechecked_before_opening")},
            M + "use.NamedCases.test_outcome_already_determined_cases": "negative",
            M + "use.OutcomeAlreadyDetermined": "positive",
            M + "data.ReadsAndEligibility.test_version_2_after_version_1": "negative",
            M + "data.ReadsAndEligibility.test_role_swap": "negative",
            M + "data.ReadsAndEligibility.test_cross_validation_fit_reads_do_not_cap": "negative",
            **{M + "contract.DataReleaseAndSharing." + t: "negative" for t in (
                "test_15_3_13_holdout_shares_events", "test_15_3_13_combined_efficiency", "test_15_3_13_mixed_sample",
                "test_15_3_13_1000_800_300_second_half")},
            M + "data.FailureRecords": "negative",
            M + "use.IncompleteAggregation": "negative",
            M + "use.NamedCases.test_grade_rule_cases": "negative",
            M + "deps.Roles.test_15_3_17_numbers_instead_of_hashes": "negative",
            M + "use.NamedCases.test_use_rule_cases": "negative",
            M + "chain.Fixtures.test_15_3_18_p4_both_modules": "positive",
            M + "data.Lineage.test_15_3a_reformatting_does_not_reset_reads": "positive",
            M + "deps.Versions.test_15_3a_rebuild_in_acyclic_order": "positive",
            "tests.contracts.test_calibration_schemas": "positive"}
P0_FIXTURES = {M + "chain.Fixtures": "positive", SCRIPTS + "Scripts.test_calib_chain": "positive"}
P1_GATE1 = {M + "preflight.A0.test_linearity_example": "negative",
            SCRIPTS + "Phase1Scripts.test_calib_contract_preflight": "negative",
            M + "kernel_check.ToyDetector.test_declared_poisson_with_enf_in_the_implementation": "negative",
            M + "kernel_check.MissingSupport": "negative",
            M + "design.Support.test_single_support_is_missing": "negative",
            M + "design.P2.test_insufficient_observables": "negative",
            M + "design.P5": "negative",
            M + "reweight.Formula.test_w_is_one_without_proposal_at_theta0": "negative",
            M + "reweight.AgainstRerun": "positive",
            M + "design.Applicability": "positive",
            "test_calibration_toy": "positive",
            M + "preflight.D37": "negative",
            M + "design.ReviewFixes": "positive", M + "kernel_check.ReviewFixes": "positive",
            "test_calibration_linear": "positive", "test_calibration_reweight": "positive",
            SCRIPTS + "Phase1Scripts": "positive"}
UNIT_LISTS = {"p0_named": ("phase 0 card item 2: the named cases of section 15.3 and the P4 negative test", P0_NAMED),
              "p0_fixtures": ("phase 0 card item 3: the three fixtures derive candidate methods and reachability",
                              P0_FIXTURES),
              "p1_gate1": ("phase 1 gate 1: the negative tests of A0, P0, P2, P5 (card items 1-9; gate record tests)",
                           P1_GATE1)}

CAMPAIGNS = "/ceph/work/AMS/hsinyichou/hep-research-simcal-private/campaigns/"
PRIVATE = "/ceph/work/AMS/hsinyichou/hep-research-simcal-private/"
NODE_PY = "/ceph/work/AMS/hsinyichou/hep-detector-reco/env/py313/bin/python3.13"
G4_PRODUCTS = "/ceph/sharedfs/work/AMS/hsinyichou/simcal-p3"
G4_TELL_SHA256_PREFIX = "cefc811d"         # the p3-g4 tell.json of the phase-3 gate record
RECORDED = {"p0_appendix_c": CAMPAIGNS + "phase0-appendix-c-2/gate-summary.json",
            "p1_gate2": PRIVATE + "hep-research-simcal-phase-1/.simcal-work/gates/agreement-2.json",
            "p2_gate1": CAMPAIGNS + "p2-gate1-toy/gate1-toy-merged.json",
            "p2_gate2": PRIVATE + "hep-research-simcal-phase-2/.simcal-work/gates/gate2-segmented-r4.json",
            "p2_gate3": PRIVATE + "hep-research-simcal-phase-2/.simcal-work/gates/gate3-shift-r4.json",
            "p3_gate_e": CAMPAIGNS + "p3-gates-e/merged-E.json",
            "p4_gate": CAMPAIGNS + "p4-gates/gate-3.json"}
# the small Slurm array "misc": index -> (key, command relative to the plugin root; {out} the output file)
MISC = [("p0_named", "tests/core/calibration_phase5_gates.py --units p0_named --out {out}"),
        ("p0_fixtures", "tests/core/calibration_phase5_gates.py --units p0_fixtures --out {out}"),
        ("p1_gate1", "tests/core/calibration_phase5_gates.py --units p1_gate1 --out {out}"),
        ("p1_gate2", "tests/core/calibration_phase1_gates.py --gate agreement --out {out}"),
        ("p2_gate2", "tests/core/calibration_phase2_gates.py --gate segmented --out {out}"),
        ("p2_gate3", "tests/core/calibration_phase2_gates.py --gate shift --out {out}")]
P0_ITEMS = 69                  # calibration_exhaustive.GATE_SHARDS
P2_GATE1_TASKS = 33            # calibration_phase2_gates.GATE1T_TASKS
P3_ARRAYS = [("0-15,123", "8000M", 0), ("16-122", "4000M", 0), ("0-9", "8000M", 27164)]   # part E (card, record)

SBATCH = """#!/bin/bash
#SBATCH -J {name}
#SBATCH -p edr1-al9_short_serial
#SBATCH -A ams
#SBATCH -n 1
#SBATCH -c 1
#SBATCH --mem={mem}
#SBATCH -t {time}
#SBATCH --array={array}
#SBATCH -o {log}/task_%A_%a.log
#SBATCH --export=NONE
# simcal phase 5, gate item 3 (prior_gates_rerun): {what}. Written by calibration_phase5_gates.py --dispatch; run from
# the clean worktree at the phase-5 gate commit; the earlier harness unchanged.
set -euo pipefail
TASK=$((SLURM_ARRAY_TASK_ID + ${{1:-0}}))
WT={wt}
COMMIT={commit}
PY={py}
export TMPDIR={tmpdir}
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1{extra_env}
[ "$(git -C "$WT" rev-parse HEAD)" = "$COMMIT" ] || {{ echo "worktree moved from $COMMIT"; exit 9; }}
[ -z "$(git -C "$WT" status --porcelain)" ] || {{ echo "worktree dirty"; exit 9; }}
cd "$WT/plugins/hep-research"
echo "host $(hostname) commit ${{COMMIT:0:8}} task $TASK start $(date -Is)"
{body}
echo "end $(date -Is)"
"""


def dispatch(out: Path, commit: str, worktree: str, python: str = NODE_PY,
             tmpdir: str = PRIVATE + "tmp", g4_products: str = G4_PRODUCTS) -> dict:
    """Write the Slurm scripts, submit.sh (the sbatch lines, NOT run) and login.sh (phase 4 and the merge)."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("--commit must be the full 40-character SHA of the phase-5 gate commit")
    out = out.resolve()
    for d in ("p0/out", "p0/logs", "misc/out", "misc/logs", "p2g1/out", "p2g1/logs", "p3/out", "p3/logs", "p4"):
        (out / d).mkdir(parents=True, exist_ok=True)
    common = {"wt": worktree, "commit": commit, "py": python, "tmpdir": tmpdir, "extra_env": ""}
    scripts = {
        "p0.sbatch": dict(common, name="p5-rerun-p0", mem="1000M", time="00:20:00", array=f"0-{P0_ITEMS - 1}",
                          log=out / "p0/logs", what="phase 0 Appendix C campaign (69 items, card test design item 1)",
                          body=f'"$PY" -I tests/core/calibration_exhaustive.py --item "$TASK" '
                               f'--out {out}/p0/out/item-"$TASK".json'),
        "misc.sbatch": dict(common, name="p5-rerun-misc", mem="6000M", time="03:55:00", array=f"0-{len(MISC) - 1}",
                            log=out / "misc/logs",
                            what="phase 0 named cases and fixtures, phase 1 gates 1 and 2, phase 2 gates 2 and 3",
                            body="case $TASK in\n" + "".join(
                                f'  {i}) "$PY" -I {cmd.format(out=f"{out}/misc/out/{key}.json")} ;;\n'
                                for i, (key, cmd) in enumerate(MISC)) + '  *) echo "no task $TASK"; exit 2 ;;\nesac'),
        "p2g1.sbatch": dict(common, name="p5-rerun-p2g1", mem="6000M", time="03:55:00",
                            array=f"0-{P2_GATE1_TASKS - 1}", log=out / "p2g1/logs",
                            what="phase 2 gate 1 on the toy detector (33 tasks)",
                            body=f'"$PY" -I tests/core/calibration_phase2_gates.py --gate1-toy-task "$TASK" '
                                 f'--out {out}/p2g1/out'),
        "p3.sbatch": dict(common, name="p5-rerun-p3", mem="4000M", time="03:55:00", array="16-122",
                          log=out / "p3/logs", what="phase 3 gate part E (tasks 0-123 and 27164-27173)",
                          extra_env=f"\nexport SIMCAL_G4_PRODUCTS={g4_products}",
                          body=f'"$PY" -I tests/core/calibration_phase3_gates.py --task "$TASK" --out {out}/p3/out'),
    }
    for name, kw in scripts.items():
        (out / name).write_text(SBATCH.format(**kw))
    submit = ["#!/bin/bash", "# item 3: the sbatch lines (NOT run by the harness; the main session registers and submits)",
              "set -euo pipefail", f"cd {out}", "sbatch p0.sbatch", "sbatch misc.sbatch", "sbatch p2g1.sbatch"]
    submit += [f"sbatch --array={a} --mem={m} p3.sbatch" + (f" {off}" if off else "") for a, m, off in P3_ARRAYS]
    (out / "submit.sh").write_text("\n".join(submit) + "\n")
    me = "tests/core/calibration_phase5_gates.py"
    login = ["#!/bin/bash", "# item 3 on the login host: phase 4 (card: about 1 minute), then the merge after every array",
             "set -euo pipefail", f'WT={worktree}', f'COMMIT={commit}',
             '[ "$(git -C "$WT" rev-parse HEAD)" = "$COMMIT" ] || { echo "worktree moved"; exit 9; }',
             '[ -z "$(git -C "$WT" status --porcelain)" ] || { echo "worktree dirty"; exit 9; }',
             'cd "$WT/plugins/hep-research"', "export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1",
             f'"${{HEP_RESEARCH_PYTHON:-python3}}" -I tests/core/calibration_phase4_gates.py --run --out {out}/p4/gate.json'
             ' || true',
             f'SIMCAL_G4_PRODUCTS={g4_products} "${{HEP_RESEARCH_PYTHON:-python3}}" -I {me} --merge-rerun {out} '
             f'--out {out}/rerun-merged.json']
    (out / "login.sh").write_text("\n".join(login) + "\n")
    manifest = {"commit": commit, "worktree": worktree, "python": python, "g4_products": g4_products,
                "scripts": sorted(scripts), "misc": [k for k, _ in MISC], "p3_arrays": P3_ARRAYS,
                "tasks": {"p0": P0_ITEMS, "misc": len(MISC), "p2g1": P2_GATE1_TASKS, "p3": 124 + 10},
                "recorded_core_hours": {"p0": 0.44, "p2g1": 23.9, "p2_gate2": 0.7, "p3": 20.0},
                "submitted": False}
    io.write_json(str(out / "dispatch.json"), manifest)
    return manifest


def _load(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


SKIP_KEYS = {"provenance", "seconds", "task_seconds", "commits", "commits_by_family", "sha256"}


def numeric_diff(old, current, path="") -> list:
    """Numeric leaves present in both that differ: [(path, old, current)] (reported, not judged)."""
    out: list = []
    if isinstance(old, dict) and isinstance(current, dict):
        for k in sorted(set(old) & set(current)):
            if k not in SKIP_KEYS:
                out += numeric_diff(old[k], current[k], f"{path}/{k}")
    elif isinstance(old, list) and isinstance(current, list) and len(old) == len(current):
        for i, (a, b) in enumerate(zip(old, current)):
            out += numeric_diff(a, b, f"{path}/{i}")
    elif (isinstance(old, (int, float)) and isinstance(current, (int, float)) and not isinstance(old, bool)
          and not isinstance(current, bool) and old != current):
        out.append((path, old, current))
    return out


def _reported(key: str, current) -> dict:
    rec = RECORDED.get(key)
    old = _load(Path(rec)) if rec else None
    if old is None or current is None:
        return {"recorded": rec, "available": False}
    d = numeric_diff(old, current)
    return {"recorded": rec, "available": True, "numeric_leaves_differing": len(d), "first": d[:10],
            "judged": False}


def _commit_of(rec) -> tuple:
    p = (rec or {}).get("provenance") or {}
    return p.get("commit"), p.get("dirty")


def judge_rerun(items: dict, commit: str | None) -> dict:
    """Each earlier item passes by its own rule (`ok`) and ran at the dispatch commit from a clean tree."""
    out = {}
    for k, v in items.items():
        commits = v.get("commits") or []
        same = commit is None or (bool(commits) and all(c == commit for c in commits))
        clean = not v.get("dirty")
        out[k] = dict(v, commit_ok=same, clean=clean, passed=bool(v.get("ok") and same and clean))
    return {"items": out, "passed": bool(out) and all(v["passed"] for v in out.values())}


def merge_rerun(d: Path, out_file: Path | None = None) -> dict:
    """Judge each earlier item from the outputs in d (layout of `dispatch`), by its own registered rule."""
    import calibration_exhaustive as EX
    import calibration_phase2_gates as P2G
    import calibration_phase3_gates as P3G
    man = _load(d / "dispatch.json") or {}
    commit = man.get("commit")
    items: dict = {}
    s = EX.summarize(d / "p0/out")
    prov = s.get("provenance") or {}
    items["p0_appendix_c"] = {"rule": "calibration_exhaustive --summarize status ok (phase 0 card test design item 1)",
                              "status": s["status"], "ok": s["status"] == "ok",
                              "commits": [prov.get("commit")] if prov else [], "dirty": False,
                              "reported": _reported("p0_appendix_c", s)}
    for key, (part, kinds) in UNIT_LISTS.items():
        rec = _load(d / "misc/out" / f"{key}.json")
        if rec is None:
            items[key] = {"rule": UNIT_RULE, "status": "missing", "ok": False}
            continue
        j = judge_tests(key, part, kinds, rec["outcomes"])
        c, dirty = _commit_of(rec)
        items[key] = {"rule": UNIT_RULE, "status": "passed" if j["passed"] else "failed", "ok": j["passed"],
                      "not_run": j["not_run"], "failed": [r["test"] for r in j["tests"] if r["status"] not in
                                                          ("caught", "passed")], "commits": [c], "dirty": dirty}
    for key, rule in (("p1_gate2", "phase 1 gate 2: calibration_phase1_gates --gate agreement status passed"),
                      ("p2_gate2", "phase 2 gate 2: calibration_phase2_gates --gate segmented status passed"),
                      ("p2_gate3", "phase 2 gate 3: calibration_phase2_gates --gate shift status passed")):
        rec = _load(d / "misc/out" / f"{key}.json")
        c, dirty = _commit_of(rec)
        items[key] = {"rule": rule, "status": (rec or {}).get("status", "missing"),
                      "ok": bool(rec) and rec.get("status") == "passed" and not rec.get("smoke"),
                      "commits": [c] if rec else [], "dirty": dirty, "reported": _reported(key, rec)}
    work_dir = Path(tempfile.mkdtemp(prefix="p5-merge-"))
    g1 = P2G.gate1_toy_merge(d / "p2g1/out", work_dir / "p2g1.json")
    items["p2_gate1"] = {"rule": "phase 2 gate 1: calibration_phase2_gates --gate1-toy-merge status passed (18 items, "
                                 "every task, one clean commit)", "status": g1["status"], "ok": g1["status"] == "passed",
                         "missing_tasks": g1["missing_tasks"], "commits": g1["commits"], "dirty": g1["dirty"],
                         "reported": _reported("p2_gate1", g1)}
    saved = os.environ.get("SIMCAL_G4_PRODUCTS")
    os.environ["SIMCAL_G4_PRODUCTS"] = saved or man.get("g4_products") or G4_PRODUCTS   # restored below
    try:
        m3 = P3G.merge(d / "p3/out", work_dir / "p3.json")
    finally:
        if saved is None:
            os.environ.pop("SIMCAL_G4_PRODUCTS", None)
    tell = (m3.get("products") or {}).get("tell_sha256") or ""
    items["p3_gate_e"] = {"rule": "phase 3 gate part E: calibration_phase3_gates --merge gate_status passed, with "
                                  f"SIMCAL_G4_PRODUCTS at the recorded products (tell.json {G4_TELL_SHA256_PREFIX}...)",
                          "status": m3["gate_status"], "ok": m3["gate_status"] == "passed"
                          and tell.startswith(G4_TELL_SHA256_PREFIX), "products": m3.get("products"),
                          "missing_gate_families": {k: v for k, v in m3["missing_tasks_by_family"].items()
                                                    if not k.startswith("toy_g8")},
                          "commits": sorted({c for f in ("units", "zdc_fit", "zdc_fit_g4", "phi_resim", "g8_3m",
                                                         "g8_3m_spot") for c in m3["commits_by_family"].get(f, [])}),
                          "dirty": m3["dirty"], "reported": _reported("p3_gate_e", m3)}
    p4 = _load(d / "p4/gate.json")
    c, dirty = _commit_of(p4)
    items["p4_gate"] = {"rule": "phase 4: calibration_phase4_gates --run gate_status passed",
                        "status": (p4 or {}).get("gate_status", "missing"),
                        "ok": bool(p4) and p4.get("gate_status") == "passed", "commits": [c] if p4 else [],
                        "dirty": dirty, "reported": _reported("p4_gate", p4)}
    j = judge_rerun(items, commit)
    rep = {"item": "prior_gates_rerun", "rule": "each earlier item passes by its own registered rule, at the dispatch "
           "commit from a clean worktree; numerical differences from the recorded evidence are reported, not judged",
           "commit": commit, **j, "provenance": provenance(), "label": LABEL}
    if out_file:
        io.write_json(str(out_file), io.jsonable(rep))
    return rep


def _module(name: str) -> str:
    return ".".join(name.split(".")[:3]) if name.startswith("tests.") else name.split(".")[0]


def run_tests_by_module(names: list) -> dict:
    """run_tests with each test module in its own interpreter, as the earlier gates ran their modules: one
    process for all would leak state between modules (an evaluator kind registered by one module's import changes
    another module's expectation)."""
    groups: dict = {}
    for n in names:
        groups.setdefault(_module(n), []).append(n)
    outcomes: dict = {}
    for ids in groups.values():
        with tempfile.TemporaryDirectory(prefix="p5-units-") as work_dir:
            out = Path(work_dir) / "o.json"
            res = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--run-names", *ids, "--out",
                                  str(out)], capture_output=True, text=True, timeout=3600)
            got = _load(out)
        if got is None:
            outcomes.update({n: {"outcome": "error", "detail": (res.stderr or "")[-2000:]} for n in ids})
        else:
            outcomes.update(got)
    return outcomes


def units_task(key: str, out: Path) -> dict:
    part, kinds = UNIT_LISTS[key]
    rec = {"key": key, "part": part, "outcomes": run_tests_by_module(list(kinds)), "provenance": provenance(),
           "label": LABEL}
    io.write_json(str(out), io.jsonable(rec))
    return rec


# ------------------------------------------------------------------ item 4: default_off_identity
GOLDEN = ROOT / "tests" / "core" / "data" / "simcal_p5_identity.json"
# fields that legitimately differ between the base and the gate commit (commit, time, environment), masked in both
# texts before the byte comparison. None of the captured outputs records any: two captures at the base were
# byte-identical, and no output carries a commit, a time, a host, an interpreter or a plugin/CORE version (a later
# case through map_basis would carry CORE_VERSION under "sampler" and would need it here). The environment itself is
# compared separately: a different interpreter or NumPy/SciPy makes the item incomplete, not judged.
MASKED_KEYS: tuple = ()


def mask(text: str, keys: tuple | None = None) -> str:
    """The text with the scalar value of each listed key replaced by "<masked>"; everything else byte for byte."""
    keys = MASKED_KEYS if keys is None else keys
    if not keys:
        return text
    names = "|".join(map(re.escape, keys))
    rx = re.compile(r'("(?:' + names + r')"\s*:\s*)("(?:[^"\\]|\\.)*"|-?[0-9][0-9.eE+-]*|null|true|false)')
    return rx.sub(lambda m: m.group(1) + '"<masked>"', text)


S_DIR = ROOT / "skills" / "hep-statistics" / "scripts"
FIXTURE_DIR = ROOT / "core" / "calibration" / "data"


def _cli(script: str, args: list, files: dict, outputs=()) -> dict:
    return {"kind": "cli", "script": script, "args": [str(a) for a in args], "files": files, "outputs": list(outputs)}


def golden_inputs() -> dict:
    """The fixed set of phase-0..4 inputs (built once, at the capture, from the earlier phases' fixtures; stored in
    GOLDEN so the comparison does not depend on fixture code that a later commit may change)."""
    import calibration_fixtures as F
    import calibration_g4sim_fixtures as G4
    import calibration_phase1 as H
    import test_calibration_contrib as TC
    import test_calibration_export as EXT
    from core.calibration import data_release as observed
    fx = {n: json.loads((FIXTURE_DIR / f"{n}.json").read_text()) for n in ("ecal", "rich", "tracker",
                                                                             "toy_detector_design",
                                                                             "toy_detector_subgraph")}
    rels = F.releases()
    good = F.contract()
    good["data"] = {"calibration_releases": [observed.release_hash(rels[F.CAL])],
                    "validation_releases": [observed.release_hash(rels[F.VAL])]}
    bad = dict(good, models={"enumerated": [{"id": "nominal"}], "absorbed": [{"id": "nominal"}]})
    sub = json.loads(json.dumps(fx["toy_detector_subgraph"]))
    sub["contract"]["references"] = [dict(r, enabled=r["id"] == "single_photoelectron")
                                     for r in sub["contract"]["references"]]
    gc, gp = H.gaussian_chain()
    pc, pp = H.poisson_chain()
    uc, up = H.uniform_chain()
    mc, mp = H.uniform_chain({"nodes": ["x"], "components": [{"theta": {"theta": v}} for v in (0.0, 0.5, 1.0)]})
    lc, lp = H.gaussian_chain(proposal={"nodes": ["x"], "components": [{"theta": {"sigma": 2.5}}]})
    pts = [{"theta": 0.5}, {"theta": 0.25}, {"theta": 0.4}]
    toy_c, toy_p, toy_v = _toy_fit_inputs()
    cc2, cp2 = TC.chain(2)[:2]
    rc2, rp2 = TC.chain(2, method="analytic-reweighting", removal=0.4, n_data=320)[:2]
    J, W = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]
    zero = [[[0.0] * 3] * 3] * 2
    use_in = dict(incomplete=False, mandatory_gate_failed=False, real_data=True, vmode="holdout", design_only=False,
                  p7_failed=False, v_pass=True, power_ok=True, testable_ok=True, validation_data_reuse="none",
                  validation_data_simulated=False, earlier_failure_record="none", own_flags=[])
    g8 = {"errors": [[0.1], [-0.2], [0.05], [0.0]], "cover68": [[True], [True], [False], [True]]}
    exp_res, exp_con = EXT.result(), EXT.contract()
    cases = {
        # contract check (phase 0)
        "contract_check_accepted": _cli("calib_contract.py", ["check", "--contract", "c.json", "--release", "cal.json",
                                                              "--release", "val.json"],
                                        {"c.json": good, "cal.json": rels[F.CAL], "val.json": rels[F.VAL]}),
        "contract_check_rejected": _cli("calib_contract.py", ["check", "--contract", "c.json", "--release", "cal.json",
                                                              "--release", "val.json"],
                                        {"c.json": bad, "cal.json": rels[F.CAL], "val.json": rels[F.VAL]}),
        # chain, P4 (phase 0)
        **{f"chain_{n}_{s}": _cli("calib_chain.py", [s, "--contract", f"{n}.json"], {f"{n}.json": fx[n]})
           for n in ("ecal", "rich", "tracker") for s in ("candidates", "p4")},
        "chain_subgraph_p4_failed": _cli("calib_chain.py", ["p4", "--contract", "sub.json"], {"sub.json": sub}),
        # design, P2, P5, support, methods (phase 1 and 2)
        "design_p2": _cli("calib_design.py", ["p2", "--contract", "fx.json"], {"fx.json": fx["toy_detector_design"]}),
        "design_points": _cli("calib_design.py", ["points", "--contract", "fx.json", "--n", 8, "--seed", 1,
                                                  "--held-back", 2], {"fx.json": fx["toy_detector_design"]}),
        "design_applicability": _cli("calib_design.py", ["applicability", "--plan", "m.json"],
                                     {"m.json": {"methods": {"a": "rerun"}}}),
        "design_p5_declared_failed": _cli("calib_design.py", ["p5", "--contract", "c.json", "--plan", "p.json",
                                                              "--items", "ess", "--declared-methods"],
                                          {"c.json": gc, "p.json": gp}),
        "design_p5_final_method": _cli("calib_design.py", ["p5", "--contract", "c.json", "--plan", "p.json", "--items",
                                                           "ess"], {"c.json": gc, "p.json": gp}),
        "design_methods_poisson": _cli("calib_design.py", ["methods", "--contract", "c.json", "--plan", "p.json"],
                                       {"c.json": pc, "p.json": pp}),
        "design_support_missing": _cli("calib_design.py", ["support", "--contract", "c.json", "--plan", "p.json"],
                                       {"c.json": uc, "p.json": up}),
        "design_linearize": _cli("calib_design.py", ["linearize", "--contract", "c.json", "--plan", "p.json"],
                                 {"c.json": lc, "p.json": lp}),
        "design_bj": _cli("calib_design.py", ["bj", "--points", "pts.json"],
                          {"pts.json": [{"J": J, "W": W, "K": zero, "sigma_tot": [1.0, 1.0]}]}),
        "design_p7": _cli("calib_design.py", ["p7", "--input", "p7.json"],
                          {"p7.json": {"mode": "none", "k0": 3, "path": "analytic"}}),
        "design_practices": _cli("calib_design.py", ["practices", "--plan", "plan.json"],
                                 {"plan.json": {"toys": {"construction": "philox-only"}}}),
        # P0, weights (phase 1)
        "kernel_p0_failed": _cli("calib_kernel_check.py", ["p0", "--contract", "c.json", "--plan", "p.json", "--points",
                                                           "pts.json", "--seed", 11],
                                 {"c.json": uc, "p.json": up, "pts.json": pts}),
        "kernel_p0_passed": _cli("calib_kernel_check.py", ["p0", "--contract", "c.json", "--plan", "p.json", "--points",
                                                           "pts.json", "--seed", 11],
                                 {"c.json": mc, "p.json": mp, "pts.json": pts}),
        "reweight_weights": _cli("calib_reweight.py", ["weights", "--contract", "c.json", "--plan", "p.json", "--theta",
                                                       "t.json"], {"c.json": gc, "p.json": gp, "t.json": {"mu": 0.5}}),
        # P6 on arrays (phase 3)
        "emulator_p6_failed": _cli("calib_emulator.py", ["p6", "--input", "a.json"],
                                   {"a.json": {"v_data": [1.0], "points": [{"delta_m": [5.0], "cov_delta": [[1.0]]}]}}),
        "emulator_p6_passed": _cli("calib_emulator.py", ["p6", "--input", "a.json"],
                                   {"a.json": {"v_data": [1.0], "points": [{"delta_m": [0.5], "cov_delta": [[1.0]]}]}}),
        # the fit with G1 on the toy detector, G3, G5, G7, k* (phase 2); G2, G4, G6 at engine level below
        "fit_toy": _cli("calib_fit.py", ["fit", "--contract", "c.json", "--plan", "p.json", "--values", "v.json"],
                        {"c.json": toy_c, "p.json": toy_p, "v.json": toy_v}),
        "identify_g5_toy": _cli("calib_identify.py", ["g5", "--contract", "c.json", "--plan", "p.json", "--values",
                                                      "v.json"], {"c.json": toy_c, "p.json": toy_p, "v.json": toy_v}),
        "fit_g7": _cli("calib_fit.py", ["g7", "--theta-hats", "th.json", "--sigma-mc", "s.json"],
                       {"th.json": [[0.0, 0.0], [0.1, -0.1], [-0.1, 0.05]], "s.json": [[0.01, 0.0], [0.0, 0.01]]}),
        "fit_g3": _cli("calib_fit.py", ["g3", "--region", "r.json", "--limits", "l.json"],
                       {"r.json": {"t": [0.7, 1.3]}, "l.json": {"feasible": {"t": [0.0, 1.0]}}}),
        "fit_kstar": _cli("calib_fit.py", ["kstar", "--n", 60], {}),
        # closure: G8 (phase 2, 3)
        "closure_nc": _cli("calib_closure.py", ["nc", "--d", 3, "--level", "standard"], {}),
        "closure_decide_standard": _cli("calib_closure.py", ["decide", "--results", "g.json"],
                                        {"g.json": {"level": "standard", "names": ["a"], "sigma_design": [1.0],
                                                    "interior": g8, "boundary": g8,
                                                    "pseudo_data_source": {"status": "ok", "sample": "lo"}}}),
        "closure_not_executed": _cli("calib_closure.py", ["not-executed", "--reason", "costly"], {}),
        # validation (phase 2)
        "validate_statistic": _cli("calib_validate.py", ["statistic", "--input", "x.json"],
                                   {"x.json": {"r": [1.0, 0.0], "C_r": [[1.0, 0.0], [0.0, 0.0]], "sigma0": [1.0, 1.0],
                                               "constraints": [[0.0, 1.0]]}}),
        "validate_required_lambda": _cli("calib_validate.py", ["required-lambda", "--k", 1], {}),
        # propagation, likelihood, interval (phase 2)
        "propagate_export": _cli("calib_propagate.py", ["export", "--input", "e.json"],
                                 {"e.json": {"theta_hat": [0.1], "zeta_hat": [0.0], "Sigma": [[1.0, 0.5], [0.5, 1.0]],
                                             "i_theta": [0], "i_zeta": [1]}}),
        "likelihood_layout": _cli("calib_likelihood.py", ["layout", "--contract", "fx.json"],
                                  {"fx.json": fx["toy_detector_design"]}),
        "likelihood_binomial": _cli("calib_likelihood.py", ["binomial", "--moments", "m.json"],
                                    {"m.json": {"W_P": 30.0, "S_P": 30.0, "W_F": 70.0, "S_F": 70.0}}),
        "interval_total": _cli("calib_interval.py", ["total", "--sigma-q", 1, "--shift", "0.3", "--sigma-boot", 0.02,
                                                     "--w", 0.891], {}),
        # use, deps (phase 0, 4)
        "use_judge": _cli("calib_use.py", ["judge", "--inputs", "a.json"], {"a.json": {"inputs": use_in,
                                                                                         "upstreams": []}}),
        "use_lookup": _cli("calib_use.py", ["lookup", "--undecided", "mandatory-gate", "--inputs", "c.json"],
                           {"c.json": {"inputs": dict(use_in, incomplete=True), "upstreams": [
                               {"usages": ["phi-center"], "effective_grade": "failed", "flags": []}]}}),
        "deps_roles": _cli("calib_deps.py", ["roles", "--contract", "c.json"], {"c.json": {"upstream": [
            {"result_sha256": F.h("u"), "usages": ["envelope", "xi"], "role": "variation"}]}}),
        "deps_version": _cli("calib_deps.py", ["version", "--payload", "p.json"], {"p.json": {
            "contract_sha256": F.h("c"), "data_sha256": F.h("d"), "plan_sha256": F.h("p"), "engine_version": "0.1.0",
            "parent_versions": [], "values": {}}}),
        "deps_packages": _cli("calib_deps.py", ["packages", "--input", "x.json"], {"x.json": {"packages": [
            {"id": "p1", "upstream": "a" * 64, "zeta": {"eta": "v1"}},
            {"id": "p2", "upstream": "b" * 64, "zeta": {"eta": "v2"}}], "upstreams": {}}}),
        # contrib (phase 4)
        "contrib_variance": _cli("calib_contrib.py", ["decompose", "--contract", "c.json", "--plan", "p.json", "--theta",
                                                      "th.json", "--observable", "res", "--bootstrap", 50, "--object",
                                                      "variance"], {"c.json": cc2, "p.json": cp2, "th.json": {}}),
        "contrib_resolution_ess": _cli("calib_contrib.py", ["decompose", "--contract", "c.json", "--plan", "p.json",
                                                            "--theta", "th.json", "--observable", "res", "--object",
                                                            "resolution", "--bootstrap", 50],
                                       {"c.json": rc2, "p.json": rp2, "th.json": {}}),
        # export (phase 4)
        "propagate_g4sim_snapshot": _cli("calib_propagate.py", ["g4sim", "--template", "s.json", "--result", "r.json",
                                                                "--contract", "c.json", "--use", "production",
                                                                "--out", "out.json"],
                                         {"s.json": G4.snapshot(), "r.json": exp_res, "c.json": exp_con},
                                         outputs=["out.json"]),
    }
    for name in ("linear_fit_g1_g6_g7", "linear_g2_boundary", "g4_weights"):
        cases["engine_" + name] = {"kind": "engine", "function": name}
    return cases


def _toy_fit_inputs():
    """The small toy-detector problem of tests/skills/test_calib_scripts (holdout decision): 2 theta, 4000 events."""
    import numpy as np
    from core.calibration import toy
    from core.calibration import toy_problem as TP
    cal = ["beam1_e_mean", "beam2_e_mean", "beam4_e_mean", "light_e_mean", "light_e_width", "spe_e_mean"]
    val = ["beam2_e_width", "beam4_e_width"]
    obs = [{"name": n, "role": "calibration", "block": "gaussian", "link": "log"} for n in cal] + \
          [{"name": n, "role": "validation", "block": "gaussian", "link": "log"} for n in val]
    contract = {"observables": obs, "exposure": {"all": 400},
                "parameters": [{"name": "pde", "role": "theta", "sampling_bounds": [0.2, 0.3],
                                "physical_bounds": [0.01, 0.99]},
                               {"name": "gain", "role": "theta", "sampling_bounds": [8, 12],
                                "physical_bounds": [1, 100]}]}
    plan = {"evaluator": {"kind": "toy-detector-subgraph", "events": 4000}}
    p = TP.ToyProblem(lambda n: toy.build_toy(n, "subgraph"), cal, {"pde": {"bounds": (0.01, 0.99), "prior": (0.2, 0.3)},
                      "gain": {"bounds": (1, 100), "prior": (8, 12)}}, 400, 4000, val_names=val)
    y = np.exp(p.simulate(np.array([0.25, 10.0]), np.random.default_rng(3), nominal=False).y_gauss)
    return contract, plan, dict(zip(cal, y.tolist()))


def engine_case(name: str) -> dict:
    """Engine outputs on the linear toys of phase 2 (G1, G2, G6, G7) and G4 on fixed weights."""
    import numpy as np
    from scipy import stats

    from core.calibration import fit as F
    from core.calibration import reweight as R
    from core.calibration import toys_linear as T
    if name == "linear_fit_g1_g6_g7":
        cfg = T.linear_config(n=20, d=3, mc_ratio=0.1)
        p = T.make(cfg, [0.5, -0.3, 1.0], data_seed=3, mc_seed=4)
        f = F.find_extremum(p, 20261130, T.initial_beta(p))
        th = [F.iterate(T.LinearProblem(cfg, mc_seed=k + 7, observed=p.observed), T.initial_beta(p),
                        lndet=False).beta[:3] for k in range(10)]
        return {"fit": f.record(), "G1": F.g1(f, p), "G6": F.g6(p, f, F.null_toys(p, f, 500, 99)),
                "G7": F.g7(np.array(th), F.sigma_mc(p, f, cfg.V_MC))}
    if name == "linear_g2_boundary":
        cfg = T.linear_config(n=20, d=2, bounds=[(0.0, 10.0), (-10, 10)], prior=[(0, 3), (-3, 3)])
        p = T.make(cfg, [0.0, 0.3], data_seed=11, mc_seed=12)
        f = F.iterate(p, T.initial_beta(p, [1.0, 0.0]))
        return {"fit": f.record(), "G2": F.g2(p, f, F.null_toys(p, f, 500, 5))}
    if name == "g4_weights":
        s = np.random.default_rng(3).normal(0, 1, 20000)
        return {"G4": R.g4({"mean": stats.norm.pdf(s, 0.3, 1.2) / stats.norm.pdf(s)}, {"mean": 1000}),
                "G4_ess": R.g4({"a": np.ones(500)}, {"a": 1000})}
    raise KeyError(name)


def _dump(value) -> str:
    return json.dumps(io.jsonable(value), indent=1, sort_keys=True, default=sorted) + "\n"


def run_case(case: dict, python: str | None = None) -> dict:
    """{returncode, stdout, outputs} of a CLI case (inputs written as the tests write them, relative paths, its own
    temporary folder as the working directory), or {output} of an engine case."""
    if case["kind"] == "engine":
        return {"output": _dump(engine_case(case["function"]))}
    with tempfile.TemporaryDirectory(prefix="p5-identity-") as work_dir:
        for name, text in case["files"].items():          # the exact bytes written at the capture
            (Path(work_dir) / name).write_text(text if isinstance(text, str) else json.dumps(text))
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH",)}
        res = subprocess.run([python or sys.executable, "-I", str(S_DIR / case["script"]), *case["args"]],
                             cwd=work_dir, capture_output=True, text=True, timeout=900, env=env)
        outs = {n: (Path(work_dir) / n).read_text() if (Path(work_dir) / n).is_file() else None for n in case["outputs"]}
    return {"returncode": res.returncode, "stdout": res.stdout, "outputs": outs}


def environment() -> dict:
    import numpy as np
    import scipy
    return {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__}


def capture_golden(path: Path = GOLDEN) -> dict:
    cases = golden_inputs()
    for case in cases.values():
        if case["kind"] == "cli":                          # stored as text: key order and bytes kept exactly
            case["files"] = {n: json.dumps(v) for n, v in case["files"].items()}
        case["golden"] = run_case(case)
    head = _git("rev-parse", "HEAD").strip()
    doc = {"schema": "simcal-p5-identity/1", "phase_base": PHASE_BASE, "captured_at_commit": head,
           "note": "captured at the phase-5 base content (the base plus only the phase-5 card), before any WP merged",
           "environment": environment(), "masked_fields": list(MASKED_KEYS), "label": LABEL, "cases": cases}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return doc


def compare_case(golden: dict, now: dict) -> dict:
    diffs = []
    for k in ("returncode", "stdout", "output"):
        if k in golden:
            a, b = golden[k], now.get(k)
            if (mask(a) if isinstance(a, str) else a) != (mask(b) if isinstance(b, str) else b):
                diffs.append(k)
    for n, a in (golden.get("outputs") or {}).items():
        b = (now.get("outputs") or {}).get(n)
        if (mask(a) if isinstance(a, str) else a) != (mask(b) if isinstance(b, str) else b):
            diffs.append(f"outputs/{n}")
    return {"identical": not diffs, "differs": diffs}


def identity_item(path: Path = GOLDEN, cases: list | None = None) -> dict:
    rule = ("the outputs (exit code, stdout, written files) of every golden case are byte-identical to the capture at "
            "the phase-5 base, after masking the fields in masked_fields")
    doc = _load(path)
    if doc is None:
        return {"item": "default_off_identity", "rule": rule, "status": "missing-golden", "passed": False}
    env = environment()
    if env != doc["environment"]:
        return {"item": "default_off_identity", "rule": rule, "status": "incomplete", "passed": False,
                "reason": "the interpreter or library versions differ from the capture", "environment": env,
                "capture_environment": doc["environment"]}
    rows = {}
    for cid, case in sorted(doc["cases"].items()):
        if cases is not None and cid not in cases:
            continue
        try:
            rows[cid] = compare_case(case["golden"], run_case(case))
        except Exception as exc:                          # noqa: BLE001 (a crash is a difference)
            rows[cid] = {"identical": False, "differs": [f"error: {exc}"]}
    bad = sorted(k for k, v in rows.items() if not v["identical"])
    rel = str(path.resolve().relative_to(ROOT)) if path.resolve().is_relative_to(ROOT) else str(path)
    return {"item": "default_off_identity", "rule": rule, "golden": rel,
            "golden_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "captured_at_commit": doc["captured_at_commit"], "masked_fields": doc["masked_fields"],
            "cases": rows, "differing": bad, "passed": bool(rows) and not bad}


# ------------------------------------------------------------------ the gate
def provenance() -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                            timeout=60).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True,
                                timeout=60).stdout.strip())
    return {"commit": commit, "dirty": dirty, "python": sys.version.split()[0]}


def run_gate(rerun: Path | None = None) -> dict:
    """Items 1, 2 and 4 here; item 3 from its merged file (`--rerun-merged FILE`), else `not-run` (the gate fails)."""
    t0 = time.time()
    items = {"negatives": negatives_item(), "prior_gates_static": static_item(),
             "default_off_identity": identity_item()}
    r3 = _load(rerun) if rerun else None
    items["prior_gates_rerun"] = (dict(r3, item="prior_gates_rerun") if r3 else
                                  {"item": "prior_gates_rerun", "status": "not-run", "passed": False})
    prov = provenance()
    if r3 and r3.get("commit") != prov["commit"]:
        items["prior_gates_rerun"] = dict(items["prior_gates_rerun"], passed=False, status="rerun-at-another-commit")
    ok = all(v.get("passed") for v in items.values()) and not prov["dirty"]
    return {"gate": "phase 5: G4-L, partial pooling and inferred V_model negatives; the gates of phases 0-4 unchanged "
                    "and still passing; the extensions change nothing when unused",
            "gate_status": "passed" if ok else "failed", "passed": {k: v.get("passed") for k, v in items.items()},
            "items": items, "provenance": prov, "seconds": time.time() - t0, "label": LABEL}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--rerun-merged", help="item 3's merged file (from --merge-rerun) for --run")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dispatch", metavar="DIR")
    ap.add_argument("--commit")
    ap.add_argument("--worktree")
    ap.add_argument("--merge-rerun", metavar="DIR")
    ap.add_argument("--units", choices=sorted(UNIT_LISTS))
    ap.add_argument("--capture-golden", action="store_true")
    ap.add_argument("--run-names", nargs="+", help=argparse.SUPPRESS)      # one module's tests (run_tests_by_module)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.list:
        print(json.dumps({"negatives": {k: list(v) for k, (_, v) in NEGATIVES.items()}, "protected": list(PROTECTED),
                          "units": {k: list(v) for k, (_, v) in UNIT_LISTS.items()}, "misc": [k for k, _ in MISC],
                          "identity_cases": sorted((_load(GOLDEN) or {}).get("cases", {}))}, indent=1))
        return 0
    if a.capture_golden:
        doc = capture_golden()
        print(json.dumps({"cases": len(doc["cases"]), "captured_at_commit": doc["captured_at_commit"]}))
        return 0
    if a.dispatch:
        if not (a.commit and a.worktree):
            ap.error("--dispatch needs --commit and --worktree")
        print(json.dumps(dispatch(Path(a.dispatch), a.commit, a.worktree)))
        return 0
    if not a.out:
        ap.error("--out is required")
    if a.run_names:
        io.write_json(a.out, io.jsonable(run_tests(a.run_names)))
        return 0
    if a.units:
        r = units_task(a.units, Path(a.out))
        print(json.dumps({"key": a.units, "tests": len(r["outcomes"])}))
        return 0
    if a.merge_rerun:
        r = merge_rerun(Path(a.merge_rerun), Path(a.out))
        print(json.dumps({"passed": r["passed"], "items": {k: v["passed"] for k, v in r["items"].items()}}))
        return 0 if r["passed"] else 1
    if a.run:
        r = run_gate(Path(a.rerun_merged) if a.rerun_merged else None)
        io.write_json(a.out, io.jsonable(r))
        print(json.dumps({"gate_status": r["gate_status"], "passed": r["passed"]}))
        return 0 if r["gate_status"] == "passed" else 1
    ap.error("one of --run, --list, --dispatch, --merge-rerun, --units, --capture-golden")
    return 2


if __name__ == "__main__":
    sys.exit(main())
