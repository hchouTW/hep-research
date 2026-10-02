# M2 migration equivalence records

Environment: Python 3.11.15, `.venv-hep` (numpy 2.4.6, scipy 1.17.1). Legacy source `agentic-ai-skills@3e995a4`.

## core/stats (move, 2026-10-02)

| Legacy | Plugin | Change | Evidence |
|---|---|---|---|
| ams-analysis/scripts/{statistical_toys, unfolding_diagnostics, likelihood_limits, template_fit, poisson_diagnostics, validate_covariance, validate_response}.py | core/stats/<same name>.py | Imports packaged (`core.stats.*`), script-mode bootstrap, usage paths, docstrings no longer name AMS. **No numerical code changed.** | Ported tests: 207 run / 207 pass (legacy: 207 tests in these 7 files). Seeds and tolerances are those of the legacy tests, unchanged. CLI `statistical_toys.py boundary --n 12 --b 8 --toys 2000 --seed 1` output byte-identical to legacy (md5). |

## core/kinematics (move, 2026-10-02)

| Legacy | Plugin | Change | Evidence |
|---|---|---|---|
| ams-analysis/scripts/ams_kinematics.py | core/kinematics/relativistic.py | Moved whole: every conversion (rigidity, momentum, energies, kinetic energy per nucleon, bin edges, Jacobians, mass propagation) is generic charged-particle kinematics; it embeds no constants (|Z|, A and mass are caller-supplied, no defaults). Interface change: output note now says "not measured detector performance" instead of naming AMS; one test assertion updated accordingly. No numerical change. | 25/25 ported tests pass (legacy 25). |

AMS-specific interpretation (which variable a given AMS publication reports, isotope mass assumptions) belongs in the `experiment:ams-02` profile modules, not in code.

## core/evidence (move, 2026-10-02)

| Legacy | Plugin | Change | Evidence |
|---|---|---|---|
| ams-analysis/scripts/validate_evidence_ledger.py | core/evidence/ledger.py | `--sources`/`--claims` required (no built-in paths); optional `--namespace` requires `<ns>:S01`/`<ns>:C01` IDs; reads `verification_date`, falling back to legacy `access_date`; accepts the date markers `unknown`/`not-provided`; messages say "experiment-practice claim" instead of naming AMS. No rule removed or loosened. | On the legacy ledger (`--today 2026-10-02`): same status (pass), counts (60/183) and the same findings by code and location (0 errors, 0 warnings, 8 notes) as the legacy script. Legacy tests ported: 40 run / 40 pass in `profiles/experiments/ams-02/tests/test_evidence_ledger.py` (39 legacy + 1 namespace test); 7 generic tests in `tests/core/test_evidence_ledger.py`. |
| ams-analysis/scripts/render_source_index.py | core/evidence/render_index.py | `--sources`/`--claims`/`--index` required; ID-run compression handles qualified IDs. | `--print` on the legacy ledger is byte-identical to the legacy script (md5 6a7b43d8...); the legacy `source-index.md` checks as in sync. |

## AMS ledger (move, 2026-10-02)

`tasks/hep-research/scripts/migrate_ams_ledger.py` writes `profiles/experiments/ams-02/evidence/`. Record-level changes (declared in `legacy_id_map.json`): IDs `S01` → `ams02:S01` (and every reference), `access_date` → `verification_date` (null → `unknown`), added `legacy_id`, `formal_status` (from tier) and `evidence_status` (from support kind). `tools/check_ams_ledger_preservation.py` passes: every other field identical for 60/60 sources and 183/183 claims; 7 negative tests.

## AMS profile scripts and modules (move, 2026-10-02)

| Legacy | Plugin | Change | Evidence |
|---|---|---|---|
| ams-analysis/scripts/yaml_subset.py | contracts/legacy/yaml_subset.py | Unchanged. | YAML fixture conversion byte-identical. |
| ams-analysis/scripts/audit_analysis_spec.py | profiles/experiments/ams-02/scripts/ | Imports `contracts.legacy.yaml_subset`; default ledger `evidence/claims.json`; a bare claim ID (`C31`) resolves as the short form of `ams02:C31`. | Output on both spec fixtures byte-identical to legacy in default, `--markdown`, `--no-claims` and `--strict` modes. Ported tests pass (+2 namespace tests). |
| ams-analysis/scripts/{fetch_papers,crdb_query}.py | profiles/experiments/ams-02/scripts/ | Data paths `evidence/`; usage text. Networked subcommands unchanged and opt-in. | Ported tests pass; one assertion now expects qualified source IDs in the manifest. `check-manifest` passes (50 papers). |
| ams-analysis/references/*.md (except source-index, tests-and-examples) | profiles/experiments/ams-02/modules/{species,subsystems,methods,periods,sources}/ | Verbatim except link and path rewrites (`tasks/hep-research/scripts/migrate_ams_modules.py`). | All profile-internal links resolve; every short S/C ID cited in a module exists in the ams02 ledger (test). |
| ams-analysis/references/tests-and-examples.md | modules/methods/worked-examples.md | Worked examples only. Scoring rules, test suite, results record and the test-suite failure modes/questions are grading material and are not shipped. | — |
| ams-analysis/references/source-index.md | evidence/index.md | Prose kept, paths updated; tables regenerated from the migrated ledger. | Index in sync (test). |
| ams-analysis/SKILL.md body | modules/working-rules.md | Routing, invariants, labels, source rule and script list kept; skill wording changed to profile wording. Frontmatter becomes `profile.json` scope. | — |
| hep-analysis/references/38-ams02-case-study.md | modules/subsystems/instrument-overview.md | Links to hep-analysis references point to their new skill folders; "use the ams-analysis skill" now points to this profile. | — |
