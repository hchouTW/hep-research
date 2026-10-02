# PROGRESS — hep-research plugin

- Current milestone: **M1 complete, waiting at GATE G1** (G0 passed 2026-10-02: D1–D5 confirmed, network approved, branch pushed to origin)
- Repository: `hchouTW/hep-research-plugin`, branch `feat/hep-research-plugin` (no PR). Legacy source: read-only `agentic-ai-skills@3e995a4` via `tasks/hep-research/scripts/fetch_legacy.sh`
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

Latest check run: `check-runs/check-run-2026-10-02T134449Z.json` (6 pass, 0 fail, 0 skip; 47 tests).

## Blockers / needs user

1. G1 review: approve the architecture, journeys, contracts and skill descriptions.
2. None other. Work moved to hep-research-plugin (DECISIONS M1-09).

## Resume checklist

1. `tasks/hep-research/scripts/fetch_legacy.sh`
2. `python3 -m venv .venv-hep && .venv-hep/bin/pip install -r tasks/hep-research/baseline/pip-freeze-d5.txt`
3. `.venv-hep/bin/python plugins/hep-research/tools/run_all_checks.py`

## Next step

After G1: M2.1 migrate shared numerical code into `core/` with stewards, porting original tests.
