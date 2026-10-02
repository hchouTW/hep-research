# PROGRESS — hep-research plugin

- Current milestone: **M2 complete** (exit checks pass); next M3. G0 and G1 passed 2026-10-02
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

Latest check run: `check-runs/check-run-2026-10-02T150623Z.json` (8 pass, 0 fail, 0 skip; 851 tests, 816 pass, 35 skip).

## Blockers / needs user

1. None at M2. Next gate needing the user is G5 (native install test).
2. Open from M1: the old branch in agentic-ai-skills (M1-12) is for the user to delete.

## Resume checklist

1. `tasks/hep-research/scripts/fetch_legacy.sh`
2. `python3 -m venv .venv-hep && .venv-hep/bin/pip install -r tasks/hep-research/baseline/pip-freeze-d5.txt`
3. `.venv-hep/bin/python plugins/hep-research/tools/run_all_checks.py`

## Next step

M3: theory capability (`theory:qed-benchmark`, Path C) and the extension proof (`experiment:synthetic-collider`, Path B). Carry-overs: T18 blinding checks across plots/logs/caches/reports (not yet implemented); port `end_to_end_sample_analysis.py`; rewrite the obsolete host-install notes in `hep-computing/references/{claude-code,antigravity,codex}.md`; dedupe generic content in AMS modules against core skills (M2-04).
