# v6.3 M0 — baseline, facts and gap runs (D01)

Status: record of work package D01 of the v6.3 analysis-check programme (Phase M0), 2026-10-16. Labels:
**Confirmed** (checked in this checkout, with the evidence named), **Inferred** (a conclusion from confirmed facts),
**Unresolved**. Paths are relative to the plugin root `plugins/hep-research/` of the repository.

## 1. Checkout identity

| Item | Value |
| --- | --- |
| Precondition | git development checkout of the hep-research repository (plugin root `plugins/hep-research`), not an installed plugin copy. **Confirmed** |
| Base commit | `982af5202c4635ded0cec50b3cc223b92d83da62` on `main` (merge of PR #115), working tree clean |
| Work branches | `v63/d01-baseline`, `v63/d02-evidence-query`, `v63/d12a-rule-registry`, stacked in that order |
| `.claude-plugin/plugin.json` version | `0.11.0` |
| Python | 3.13.2 (miniconda), macOS 26.5 arm64 |
| Hosts seen by the gate | Claude Code 2.1.301, codex-cli 0.160.0 |

**Digest alignment** (`python3 tools/release_manifest.py verify --manifest release-manifests/0.11.0.json`, exit 1):
`status: different`; recorded digest `35a45863…68ea4e0` (the 0.11.0 release, tag `hep-research--v0.11.0` on
6572020), digest of this tree `a597cc41…30bcd`. **Confirmed:** 30 files changed, 70 added, 0 missing. The brief
reported 71 added on its synced tree; this checkout has 70 (**Unresolved** which file differs; it does not touch any
file this programme reads).

Changed against the release: `CHANGELOG.md`, `VALIDATION.md`, `contracts/lineage.py`, `contracts/registry.py`,
`docs/adapter-authoring.md`, `docs/agentic-architecture.md`, `docs/capability-matrix.md`,
`docs/reference-inventory.json`, `docs/reference-inventory.md`, `examples/eic-profile-routing/output/report.md`,
`examples/eic-profile-routing/output/results.json`, `profiles/experiments/eic/tests/test_profile_metadata.py`,
`profiles/registry.json`, `skills/hep-communication/SKILL.md`, `skills/hep-computing/README.md`,
`skills/hep-computing/SKILL.md`, `skills/hep-ml/references/ml-analysis.md`,
`skills/hep-statistics/scripts/covariance_fit.py`, `skills/hep-theory/README.md`,
`skills/hep-theory/references/cosmic-ray-propagation.md`, `tests/contracts/test_companion_validation_cli.py`,
`tests/contracts/test_contracts.py`, `tests/contracts/test_lineage.py`, `tests/routing/cases.json`,
`tests/routing/inputs.py`, `tests/skills/hep_communication/test_review_fixes2.py`,
`tests/skills/hep_ml/test_pretraining_freeze.py`, `tests/skills/hep_statistics/test_grid_fit.py`,
`tests/skills/test_cli_robustness.py`, `tools/measure_entrypoints.py`. Added: the `adapters/cr-propagation` adapter,
the `theory:heliospheric-modulation` profile and their tests and fixtures (the CHANGELOG *Unreleased* entries of
PRs #110–#115).

**File digests named by the brief** (SHA-256 in this checkout): all 16 equal the values the brief lists, including
the two that differ from the release (`contracts/registry.py` `0ce034d4…`, `docs/agentic-architecture.md`
`81f6063d…`). **Confirmed** (`shasum -a 256`). This checkout is the brief's synced tree for every file the programme
reads.

**O01 recommendation (Inferred; the maintainer decides).** Implement on `main` at 982af52 (this synced tree), not on
the 0.11.0 release: the two differing files (`registry.py`, `agentic-architecture.md`) differ only in argument checking,
a budget constant and one unrelated line, the cited clauses and behaviours are identical (section 2), and every later
change lands on `main` anyway. Statements about the release bind only to its manifest.

**Gate baseline** (`python3 tools/run_all_checks.py --out <dir>` on a clean worktree of 982af52): 24 checks pass,
0 fail, 0 skip; unittest 3366 run, 0 failures, 0 errors, 107 skipped, 248 modules. Pre-existing failures: none.
An earlier baseline run started in the main checkout while the D01 test was being written reported `ams_optional`
as failing: the AMS-optional copy had picked up the new, unfinished test, which then needed the AMS example. That
test now skips the AMS-dependent cases in that copy; the clean-worktree run above is the baseline.

## 2. Facts table

| Fact (brief, Repository Context) | State | Evidence |
| --- | --- | --- |
| `MEASUREMENT_KEYS["corrections"]` lacks `target_scope`, `calibration_digest`, `variation_id`, `stage` | still true | `contracts/validate.py:1111-1113`; gap run 1 |
| `_key_checks` warns `measurement.unknown_key` | still true | `contracts/validate.py:1131-1150` (codes `<kind>.unknown_key`, `<kind>.misspelled_key` for near misses) |
| `IMPLIED_CORRECTIONS = {"exposure": {"acceptance","livetime"}}` | still true | `contracts/validate.py:294` |
| blinding rule `measurement.blinded_observed` | still true | `contracts/validate.py:1313` |
| `STICKY_STATUSES`, `NOT_OBSERVED_STATUSES = ("synthetic","asimov")` | still true | `contracts/validate.py:74,76` |
| `validate.py` SHA-256 `8d7861a8…1fa0d`, release-identical | still true | digest check; not in the manifest's changed list |
| `recipe_semantics.upstream_instances` reads the four R4 fields | still true | `contracts/recipe_semantics.py:85-110` (`KEY_FIELDS`) |
| `_same_application`: different scope → False; same scope and variation, other calibration → True; missing key → None | still true, plus: both keys absent → True (the unkeyed effect-name rule) | `contracts/recipe_semantics.py:130-138` |
| codes `repeated_correction`, `repeat_undetermined`, `repeat_distinct_instance`, `upstream_unmapped` | still true (with `semantics.` prefix) | `contracts/recipe_semantics.py:188,194,199,227` |
| `flux_from_counts.json`, `differential_flux.json` exist; the table lists forward folding as out of scope | still true | table `scope`: "Forward-folding, ratios, cross sections with luminosity and multi-bin fits are outside this table" |
| bundle `ROLES`, `EXACTLY_ONE`, at least one recipe, duplicate paths rejected, `item_digest` canonical JSON for `.json` | still true | `contracts/analysis_bundle.py:39-40,84-111` (`bundle.duplicate_ref`); SHA-256 `b8d80ec8…` |
| `dependencies.py` is reference resolution | still true | module docstring |
| `verify_run.py` statuses error / unresolved / ok, exits 0/1/3/2 | still true | `contracts/verify_run.py:10-15,74` |
| `lineage.py` is exposure and decision lineage | still true | module docstring |
| `project.py` `BLINDING_KEYS = {blinded, allowed_outputs, regions}` | still true | `contracts/project.py:127` |
| `registry.py` differs from the release | still true | `git diff hep-research--v0.11.0 -- contracts/registry.py`: `check_arguments`, `REGISTRY_BUDGET` 2048→3072, `--help`; loading logic identical |
| Registry adds an error for an incompatible profile and still returns it as loaded | still true, in this checkout **and** in the release (the loading code did not change) | `contracts/registry.py:83-85,174`; gap run 3 |
| `review_measurement_spec.py:96` builds the vocabulary from `load_project(...).profiles` without checking the report | still true | `skills/hep-measurement/scripts/review_measurement_spec.py:96`; gap run 2 |
| `communication_project._load_project` turns load errors into warnings and still uses `proj.profiles` | still true (lines 137-147 and 217; also 353-357 for the vocabulary) | gap run 3 |
| `vocab/core.json`, `vocab.py` base vocabulary | still true | files present |
| `evidence.py` namespacing rule; `ledger.py` CLI under `@protected_main("core.evidence.ledger")`, listed in the protected entry-point suite | still true | `contracts/evidence.py:3-5`; `core/evidence/ledger.py:316`; `tests/contracts/test_protected_entry_points.py:137,196` |
| attestation review entries require `reviewer, role, date, bundle_sha256, scope_sha256, evidence, conclusion, record_ref`; future reviews not counted | still true | schema `properties.review.properties.reviews.items.required`; `contracts/attestation.py:106` (`attestation.review_future`); SHA-256 `a74359cb…` |
| permit subject requires `analysis_bundle_sha256, analysis_bundle_ref, artifacts`; `execution_bundle_sha256` optional and enforced for s3-execution | still true | `contracts/schemas/permit.json`; `contracts/permit.py:225-229` |
| `permit.py` `_review` runs only for formal-use, requires `accepted-as-recorded` for `required_roles`, output advisory (`formal_use_allowed: false`) | still true; evidence re-hashing happens inside `attestation.evaluate` (`_evidence_ok`) | `contracts/permit.py:94-140,230-231,262`; `contracts/attestation.py:77-125` |
| `core/partition` attempt identity `<campaign_uid>:<attempt_id>` | still true | `core/partition/campaign.py:36` |
| first valid output collected in attempt order; others duplicates; scheduler success without output is `lost` | still true | `core/partition/campaign.py:17-21,729` |
| `state.json` has no format-version field | still true | `core/partition/campaign.py:132-133` (keys at creation) |
| campaign without `collected` → `merge.provenance_unrecorded` warning only; orphan outputs → `merge.orphan_output` | still true | `core/partition/campaign.py:776,792`; gap run 5 |
| `merge` docstring: catches forged chunk files, not a forged `state.json` | still true | `core/partition/campaign.py:759-760` |
| merge result not stored by `core/partition` | still true | `campaign.merge` returns `engine.merge(...)`; no write in either |
| execution bundle freezes code, worker, interpreter, environment lock, digest-pinned image, carries an approval request; `submissions[].bundle_digest` may be None | still true | `core/partition/bundle.py:156-170,296-306`; gap run 5 (null digests) |
| `bundle.verify()`, `digest_of()`, `check_campaign()` exist | still true | `core/partition/bundle.py:150,260,326` |
| batch adapter computational-run: `campaign_uid`, attempts, duplicates, `bundles` per submission, `output_hashes.merged` | still true; these sit under `extension.environment.execution` (not top-level `execution`) | `adapters/batch-schedulers/batch_campaign.py:120-140` |
| merged hash is `sha256(json.dumps(merged, sort_keys=True))`, not `canonical_sha256` | still true | `adapters/batch-schedulers/batch_campaign.py:104` |
| backends slurm and htcondor only | still true | `adapters/batch-schedulers/batch_config.py:5` |
| `examples/batch-partition` does not freeze a bundle; submissions carry null digests | still true | gap run 5 |
| `examples/local-partition`: synchronous engine, no campaign; duplicates `merge.duplicate_chunk` | still true | `core/partition/engine.py:434` |
| `tests/core/test_partition.py` drives `campaign` with `LocalExecutor` | still true | `tests/core/test_partition.py:56-68` |
| `examples/ams-flux-ratio` artifacts as listed, no recipe file | still true | `examples/ams-flux-ratio/output/artifacts/` |
| `adapters/pyhf-combine` exists | still true | folder present |
| `comparison/composition.py` has `namespace_collision` | still true: `compose()` reports `compose.namespace_collision` when two loaded profiles declare one namespace | `contracts/comparison/composition.py:20-27` |
| `level-identification` lives in `contracts/comparison/gate.py` | still true | `contracts/comparison/gate.py:30,62,228` |
| HC-05, HC-13, HC-16 wording | still true; the one-line difference from the release copy is at line 434, outside the HC table | `docs/agentic-architecture.md:94,102,105` |
| run from the plugin root; Python ≥ 3.13; `unittest` | still true | `pyproject.toml`; gate run |

No fact was found changed or missing. Two refinements are recorded above (unkeyed R4 rule; location of the adapter's
execution block).

## 3. Gap runs

Committed as `tests/contracts/test_v63_baseline_gaps.py` (14 tests; run with
`python3 -m unittest tests.contracts.test_v63_baseline_gaps -v`). Each asserts today's behaviour and names the work
package that flips it. The AMS-example cases skip in the AMS-optional copy.

| Run | Result | Flipped by |
| --- | --- | --- |
| 1. Spec correction with the four R4 fields | reproduces: four `measurement.unknown_key` warnings (strict validation with the public ams-02 vocabulary); `recipe_semantics.KEY_FIELDS` reads exactly these fields | D05a (V36) |
| 2. `review_measurement_spec.py --profiles-from` a project binding an incompatible profile | reproduces: `load_project` reports `profile.incompatible_version`, the review still runs (exit 1 on the spec's own findings, never 2) and its output never mentions the incompatibility | D03a |
| 3. Incompatible profile kept | reproduces: `validate_registry` returns it as loaded; `load_project` binds it; `communication_project.resolve_context` lists it with only the warning `resolution.project_config_invalid` | D03a |
| 4. Cross-artifact error that every existing check passes | reproduces (below) | D06 (V34) |
| 4b. Same effect on one path under two calibrations, split over two recipe instances | reproduces: two keyed recipes checked together both pass; L2 catches it only when the first application is recorded as an upstream artifact | D06 (V21) |
| 5. Execution facts | reproduces: a synthetic campaign without `collected` merges `complete` with only `merge.provenance_unrecorded`; the batch example's Slurm campaign records `bundles` all null and a non-null `campaign_uid` | D05d (V62, V63) |

**Gap 4 in detail (Confirmed).** Inputs: the `examples/ams-flux-ratio` spec, four responses and two datasets, with the
spec's `rigidity_migration` correction stated as `applied_in: "unfolding"`; the recipe `flux_from_counts.json` and its
table. The relation is contradictory: the spec says migration is corrected by unfolding with the response, each
response has `intended_use: "unfolding"` and `includes: ["migration"]`, but the recipe has no `unfold` step and lists
`migration` under `not_applied` ("compared with a model by forward-folding"). Existing checks:

| Check | Result |
| --- | --- |
| `python3 contracts/validate.py <artifact> --profiles-from <project binding experiment:ams-02>`, each of the 7 artifacts | exit 0, no error or warning |
| `python3 contracts/recipe_semantics.py recipe.json --table table.json` | exit 0, `pass` |
| `python3 contracts/analysis_bundle.py verify bundle.json --root DIR` (spec, recipe, table, a synthetic lock) | exit 0, `identical` |

Why no single L2 patch catches it (**Inferred**): L2 sees a recipe, its table and upstream artifacts that record
*applied* corrections; the spec's plan and the response's intended use are neither. The bundle has no response role
(`analysis_bundle.ROLES`), so the response cannot be a typed member of the frozen analysis at all. Detecting the
contradiction needs a typed binding between the spec's description, the recipe step and the response
(`response_used_by`), which is cross-artifact by construction (R-RESP, R-REAL).

**Observation on the shipped example (Inferred, not a defect claim).** Unmodified, the example already pairs
responses whose `intended_use` is `unfolding` with a recipe that forward-folds and a spec that places migration in
`response_matrix`. Whether that is a contradiction depends on the response-use binding the plan introduces; today
nothing checks it either way.

**Not built: V37** (a scope-less correction against four recipe instances). Recipe instances do not exist as a
concept today (one recipe file, no instance bindings), so the case cannot be expressed in current artifacts. This is
itself evidence that instance identity (D05a) is new structure, not an L2 patch.

## 4. Consumer inventory (profile loading results)

Search: `load_project(`, `validate_registry(`, `Vocabulary.with_profiles`, `.profiles` outside tests.

| Consumer | What it reads | Respects the load report? |
| --- | --- | --- |
| `contracts/project.py:49-109` `load_project` | `validate_registry` → binds profiles | **No**: copies registry findings into its report but binds an incompatible profile in `profiles` (gap 3) |
| `contracts/registry.py:151-181` `validate_registry` | profile folders | **No**: returns incompatible profiles in `loaded` (gap 3) |
| `contracts/registry.py:209-221` CLI | `validate_registry` | yes: prints the report, exit 1 on errors |
| `contracts/project.py:178-183` `load_blinding` | `load_project` | yes: raises on an invalid report |
| `contracts/project.py:186-200` `resolve_context` | a `Project` | **No check of its own**: returns the configured profile IDs whatever the report (callers pass a project) |
| `contracts/project.py:205-217` CLI | `load_project` | yes: exit 1 on errors |
| `contracts/validate.py:2063-2077` `--profiles-from` | `load_project(...).profiles` | yes: the project's findings join the report, so the run fails (checked: exit 1 with `profile.incompatible_version`) |
| `contracts/communication_project.py:137-147,217,353-357` | `load_project`, `proj.profiles` | **Downgrades**: errors become warnings, profiles still used for ledgers and vocabulary (gap 3) |
| `skills/hep-communication/scripts/track_revision_impact.py:50`, `communication_lib/report.py:167` | `communication_project.resolve_context` | inherit the downgrade above |
| `skills/hep-measurement/scripts/review_measurement_spec.py:96` | `load_project(...).profiles` | **No** (gap 2) |
| `examples/eic-profile-routing/run.py:94-107` | `load_project` | yes: reports `report.ok` of the good and bad project |
| `examples/{ams-flux-ratio,collider-angular,detector-resolution,ml-classifier-to-inference,qed-prediction,theory-comparison}/run.py` | `Vocabulary.with_profiles([profile.json])` read directly | bypass loading (no report exists); fixed public profiles, examples only |
| `core/blinding/blinding.py:676` `load_project_blinding` | the config's `blinding` block | not a profile consumer (unvalidated by design; `contracts.project.load_blinding` is the validated read) |

D03a must fix the four rows marked **No** or **Downgrades** (and their inheritors), each with a failing-profile test.

## 5. What this record does not establish

- Physical validity of any example or fixture; the checks are software consistency only.
- Anything about the `ams02-research` companion: none of its files were opened.
- Whether the 70-versus-71 added-file difference matters for the brief's synced tree (Unresolved, see section 1).
