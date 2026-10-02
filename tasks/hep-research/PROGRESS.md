# PROGRESS — hep-research plugin

- Current milestone: **M5 work done, waiting at GATE G5** (native install test needs the user's choice). G0 and G1 passed 2026-10-02
- Repository: `hchouTW/hep-research`, branch `feat/hep-research-plugin` (no PR). Legacy source: read-only `agentic-ai-skills@3e995a4` via `tasks/hep-research/scripts/fetch_legacy.sh`
- Base commit: `3e995a49a89fad8e0e9d52130ee1fd93a3a0f4f9`
- Last session: 2026-10-02, Claude Code cloud container (CLI 2.1.287), Python 3.11.15

## M0 steps

- [x] 1. Branch + `tasks/hep-research/` with PROGRESS/DECISIONS
- [x] 2. Environment recorded; `.venv-hep` created (empty) and gitignored
- [x] 3. Network-use grep (no test makes real calls; see baseline/summary.md)
- [x] 4. Baseline run: 1027 tests, 985 pass, 0 fail, 42 skip; 7/7 bundle validators exit 0
- [x] 5. Section 4 facts re-verified (all match; extra files recorded below)
- [x] 6. `plugins/hep-research/docs/integration-inventory.json` (949 files, 100% of 942 in the seven skills) and draft `migration-map.csv` (948 rows)
- [x] 7. Section 5.1: 4 verified locally, 1 partial, 3 unverified (need docs access) — see `plugins/hep-research/docs/architecture.md`
- [x] 8. D3 reference candidates listed (no formulas written)
- [x] 9. `lint_task.py` run: 4 structural errors, adapted (DECISIONS M0-05)

## Section 4 re-verification

| Fact | Result |
|---|---|
| Seven source skills | Confirmed |
| AMS ledger 60 sources / 183 claims | Confirmed (IDs S01–S60, C01–C183, all unique) |
| ams-analysis/SKILL.md 95 lines / 16,281 B | Confirmed |
| hep-analysis/SKILL.md 218 lines / 38,172 B | Confirmed |
| No root plugin manifest, no root LICENSE | Confirmed |
| Differences vs 4.1 map | `ams-analysis/scripts/{crdb_query,fetch_papers,poisson_diagnostics,statistical_toys,yaml_subset}.py` and `docs/detector-principles/` are not in the 4.1 map; added to migration-map.csv |

## M1 steps

- [x] 1. `docs/researcher-journeys.md` (J1–J12; 3 gaps fixed, 2 limitations)
- [x] 2. `docs/architecture.md`, `core/OWNERS.json`
- [x] 3. `docs/routing-contract.md`
- [x] 4. Vocabulary (`contracts/vocab/core.json`, `contracts/vocab.py`) and common schemas
- [x] 5. Envelope + 10 typed extensions + validator; 16 valid / 18 invalid fixtures
- [x] 6. Two-tier registry, templates, validator; 11 registry packages
- [x] 7. Project config, resolution order, local profiles; 16 configs
- [x] 8. Evidence schema and namespacing (`contracts/evidence.py`)
- [x] 9. Skeleton: manifest, seven SKILL.md, generated stanza, dev marketplace; `claude plugin validate --strict` passes
- [x] 10. `tools/run_all_checks.py`, `check_layering.py`, `measure_entrypoints.py`, `build_stanzas.py`
- [x] 11. `docs/architecture-review.md` (10/10 items met; item 2 at file level)

M1 check run: `check-runs/check-run-2026-10-02T134449Z.json` (6 pass, 0 fail, 0 skip; 47 tests).

## M2 steps

- [x] 1. Shared code in `core/` with stewards (`core/stats`, `core/kinematics`, `core/evidence`); original tests ported (`m2/equivalence.md`)
- [x] 2. `profiles/experiments/ams-02`: 60 sources / 183 claims as `ams02:` IDs with legacy map; `check_ams_ledger_preservation.py` passes
- [x] 3. AMS distinctions kept in modules and conventions (rigidity definition and sign, charge-sign source, mass-number assumption; species/period restrictions stay per source)
- [x] 4. Seven metadata-only dataset records (no values: none exist in the legacy repo with provenance)
- [x] 5. Legacy spec converter (`profiles/experiments/ams-02/scripts/convert_legacy_spec.py`, 20 tests)
- [x] 6. All five Section 12 corrections as `sci-fix:` commits with regressions
- [x] 7. Path A: `examples/ams-flux-ratio/run_path_a.py` (all pre-declared criteria pass; `tests/examples/test_path_a.py`)
- [x] Skill redistribution: 394 legacy files recorded (`m2/redistribution/*.csv`), moved in one `move:` commit, then legacy-name routes, example-block marking and SKILL.md resource routes as separate commits; `docs/migration-map.csv` updated from the records

M2 exit checks: ledger preservation pass; migrated-helper regressions pass (816 pass, 35 skip for missing optional tools: PyTorch, PyROOT, awkward/uproot, Combine, Graphviz, Mermaid, PlantUML, tectonic); Path A pass; AMS tasks read `profiles/registry.json` then the profile `index.md` (2.4 KB) and only the modules they need; layering pass.

M2 check run: `check-runs/check-run-2026-10-02T150623Z.json`.

M3 check run: `check-runs/check-run-2026-10-02T153532Z.json`.

Latest check run (M4): `check-runs/check-run-2026-10-02T160613Z.json` (11 pass, 0 fail, 0 skip; 952 unit tests, 913 pass, 39 skip; profile suites 257 + 9 + 16 pass). The Path D low-count test was added while this run was in progress and passed on its own.

## M3 steps

- [x] 1. `profiles/theory/qed-benchmark`: PDG review eqs. 51.2/51.3 read at page level (DECISIONS M3-04/05), SymPy trace derivation with 8 checks (`analytic-derivation`, not proof), prediction with convergence study, 16 tests (incl. T13 convention mismatch)
- [x] 2. Path C (`examples/qed-benchmark/run_path_c.py`): zero experiment-profile files read (audit hook), no detector/data/blinding fields, no GPU or commercial CAS; theory_spec and prediction artifacts
- [x] 3. `profiles/experiments/synthetic-collider` (illustrative) via profile resources and registry only; AC10 diff in `m3/ac10-diff.txt`; generator imports no theory code
- [x] 4. Path B (`examples/collider-angular/run_path_b.py`): unfolded dσ/dcosθ, fiducial σ 745.65 ± 6.63 (stat) ± 14.9 (lumi) pb vs 745.81 expected, χ² 10.4/10, reproducible
- [x] 5. AMS optionality: `tools/check_ams_optional.py` (copy without the AMS profile, path with spaces) passes; part of `run_all_checks.py`
- [x] Carry-over T18: `core/blinding` with two consumer scripts and synthetic leak tests

M3 exit checks: Paths B and C pass; AMS-absent run passes; AC10 diff touches no core, contracts or skill files.

## M4 steps

- [x] 1. Comparison gate (`contracts/compat/gate.py`, CLI) and composition diagnostics (`compose.py`); combination plan (`combine.py`) with `hep-statistics/scripts/combine_measurements.py`; competing-model set (`models.py`)
- [x] 2. Path D (`examples/theory-comparison/run_path_d.py`): gate, forward folding, mu fit, Asimov injection at 1 and 1.25, 200 toys at mu = 1 and 0.8, 9 rejected variants, one documented conversion; T24 (`examples/published-comparison/`)
- [x] 3. Handoffs exercised by Section 11 tests (`tests/integration/test_handoffs.py`): detector -> statistics (T07), ML (T16, new `check_surrogate_domain.py`, AUC-only rule), analysis changes (T19, new `review_analysis_change.py`), failure propagation and communication (T20), private local profile (T27), paradigms (T28)
- [x] 4. Local partition/merge/recovery (`skills/hep-computing/scripts/local_partition.py`, `examples/local-partition/`, T21)
- [x] 5. Section 11 tests mapped to M4 run: T03–T09, T16, T19–T21, T24, T27, T28 pass
- [x] Carry-over: legacy end-to-end sample analysis moved to `examples/end-to-end-sample/` (skipped without pyhf)

M4 exit checks: Path D and T24 pass; every negative composition/compatibility fixture fails with an actionable message (field, reason, resolution); failure statuses propagate downstream (T20).

## M5 steps

- [x] 1. Relocation (`tools/check_relocation.py`): path with spaces, unrelated cwd, no symlinks or source-path references; all checks pass
- [x] 2. Budgets measured (`tasks/hep-research/m5/budgets.json`); all within budget (M5-02)
- [x] 3. Routing: 48 cases (`tests/routing/cases.json`) and `tools/check_routing_static.py` pass; live routing pending approval
- [x] 4. Packaging scan (`tools/check_packaging.py`) clean
- [x] 5. `README.md`, `requirements-core.txt`, `docs/capability-matrix.md`; host notes rewritten; bundle validator fixed
- [ ] 6. GATE G5: native install, discovery, namespaced invocation, profile-resource access, legacy coexistence, removal; host and version recorded

## Blockers / needs user

1. GATE G5: the user runs the native install test, or approves an isolated run here (and, separately, paid live routing/loading traces).
2. Open from M1: the old branch in agentic-ai-skills (M1-12) is for the user to delete.

## Resume checklist

1. `tasks/hep-research/scripts/fetch_legacy.sh`
2. `python3 -m venv .venv-hep && .venv-hep/bin/pip install -r tasks/hep-research/baseline/pip-freeze-d5.txt`
3. `.venv-hep/bin/python plugins/hep-research/tools/run_all_checks.py`

## Next step

G5 per the user's choice, then record it in VALIDATION (AC02, AC04 traces, AC20 live, AC24, AC25, T22) and start M6. Carry-overs: dedupe generic content in AMS modules (M2-04); pyhf example unverified until pyhf is approved.
