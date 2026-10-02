# PROGRESS — hep-research plugin

- Current milestone: **M0 complete, waiting at GATE G0**
- Branch: `feat/hep-research-plugin` (local; nothing pushed)
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

## Blockers / needs user

1. Confirm D1–D5 (G0).
2. Approve network for: (a) reading official Claude Code plugin docs (5.1 items 2, 3, 4, 8); (b) `pip install` of D5 packages into `.venv-hep`.
3. The repository is read-only from this cloud session; commits are local only. A patch/bundle is exported to the project folder.

## Next step

After G0: M1.1 `docs/researcher-journeys.md`.
