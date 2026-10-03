# Final Report — hep-research validation-gap audit (T01–T08)

Work order: `hep-research-audit-task.r2.md` (this folder; also `tasks/hep-research/audit/TASK.md` in the repo).
Branch `claude/validation-gaps-1799v5`, PR https://github.com/hchouTW/hep-research/pull/12 (not merged).
Base `main` at `8f2b3da` (merge of PR #11). Plugin version 0.1.0.

## 0. Changes to the work order (r1 → r2)

Every path, function and fixture named in r1 exists on `main`, and every finding still reproduces, so the tasks themselves are unchanged. The r2 edits are:
- The audited commit is now known: `8f2b3da`.
- The reference table gains the cloud baseline. SciPy is a core dependency, so the main suite has 0 errors (not 1).
- "Release notes" is defined. The plugin had no changelog, so `plugins/hep-research/CHANGELOG.md` is created.
- T06 fixes its status vocabulary (`passed` / `failed` / `incomplete`, `--strict`). It also notes that the existing unit test `test_group_check_is_skipped_without_a_mapping` tests a helper only and stays.
- T07 names the second auxiliary-truncation site (`_toy_p1`, profile-limit). That site is left as an open item.
- C03 carries the recorded routing count: 43/48 in VALIDATION, 44/48 after the scorer fix.

## 1. Environment

- Claude Code cloud container: Linux 6.18 x86_64, Python 3.11.15.
- Core stack (`requirements-core.txt`, installed in `.venv-hep`): numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.2, sympy 1.14.0.
- Optional tools not installed: PyTorch, uproot/awkward, ROOT, pyhf, Combine, Graphviz/PlantUML/Mermaid, tectonic, and the legacy checkout.

## 2. Phase 0 reproduction table (on `8f2b3da`)

| ID | Reproduces | Classification |
|---|---|---|
| T01 (a) process, (b) species, (c) phase space, (d) second axis | yes, all four `comparable: true` | reproduced defect |
| T02 (a) edges, (b) unit, (c) no values, (d) NaN | yes, all four valid | reproduced defect |
| T03 `{"data":[10,10],"templates":{"sig":[10,0]}}` | yes: exit 0, `status: ok`, yield 20, error null | reproduced defect |
| T04 (A) `.npy` | yes: `TypeError` | reproduced defect |
| T04 (B) `.root` only | yes: `ok: true` with nothing scanned | reproduced (weak success semantics) |
| T05 dangling ref with bad sha256 | yes: validates, and no project-level layer exists | product capability gap |
| T06 no groups, partial groups | yes: both `passed`, and partial gives `groups_checked: true` | reproduced defect |
| T07 "guaranteed coverage" label | yes, and the auxiliary draw is truncated at 0 | method-claim gap. Undercoverage was **not** demonstrated |
| T08 `\cite` with no bibliography | yes: exit 0, "No issues found" | reproduced defect |

Script: `tasks/hep-research/audit/phase0_repro.py`. After the fixes it prints `reproduces: false` for all 18 checks.

## 3. Per-task summary

**T01 comparison gate.** Changed `contracts/comparison/gate.py` and `contracts/schemas/common.json` (adds `phase_space.cuts`).
- Behavior: process, species and phase space are compared. Free text is normalized for case and whitespace. Text that still differs is `unresolved` until a mapping `{"field","action":"equivalent","justification"}` is declared; a mapping without a justification is rejected.
- Structured `cuts` are compared exactly. Every axis is compared by name, unit and edges or points.
- Axis transformations on multi-dimensional observables are rejected explicitly.
- The result gains `status` (comparable / not-comparable / unresolved) and each mismatch a `kind`.
- Tests: `tests/contracts/test_comparison.py::GateDefinitionAuditT01` (10 tests).
- Knock-on: the `theory-comparison` and `published-comparison` examples compare a theory prediction worded "one photon, tree level" with "synthetic generator". They now declare justified process and phase-space mappings. `theory-comparison` gains a negative variant for "process without mapping". The committed outputs of `theory-comparison` and `recasting` were regenerated; only the added fields changed.
- Rule 9 decisions: definition mappings are distinguished from convention mappings by `field` vs `key`. After a `fiducial-restriction`, only structured cuts describe the prediction's phase space. Forward-folding keeps the definition.

**T02 artifact validation.** Changed `contracts/validate.py` and `common.json`.
- Payload edges must equal the observable's edges. A unit other than the observable's needs `unit_conversion {from,to,factor,justification}`.
- `numerical` and `grid` predictions need `values`; `symbolic` predictions need `expression`.
- Non-finite numbers are rejected anywhere in the artifact.
- Multi-dimensional payloads declare `axes` in observable order and are flattened row-major (last axis fastest). `edges` repeats the first axis (Rule 9). Metadata-only records stay valid.
- Tests: `tests/contracts/test_contracts.py::ArtifactConsistencyAuditT02` (10 tests).

**T03 template fit.** Changed `core/stats/template_fit.py` and the AMS statistical-diagnostics module text.
- The minimizers report convergence and the termination reason (through an optional `info` dict, so the existing call signatures are unchanged).
- Each fit carries `diagnostics` with an outcome: converged, converged-at-boundary, covariance-warning, not-converged or infeasible.
- A failed fit sets `status: failed`, exit code 1, `artifact_fit_status: failed` and `artifact_status_labels: ["failed"]`. Toys count failed fits and drop them.
- BFGS can stop on a failed line search at the kink of the shape interpolation. It is accepted as converged only if no coordinate step lowers the objective. Feasible fits are byte-identical before and after.
- Tests: `FitStatusAuditT03` (6 tests). `test_solver_failure_recorded` runs with SciPy and passes.

**T04 blinding.** Changed `core/blinding/blinding.py` and `skills/hep-computing/scripts/audit_blinded_outputs.py`.
- `.npy` and `.npz` files are loaded on separate paths.
- Scan status is `pass`, `fail` or `incomplete`, and `ok` is true only for `pass`.
- Strict mode adds three rules. An incomplete scan fails. Every exemption needs a reason. Every output in a manifest needs a scan record or an exemption.
- An exemption never skips a readable file. Every report states the transformed-value limitation.
- CLI exit codes: 0 pass, 1 fail, 3 incomplete, 2 usage.
- Tests: `ScanCompletenessAuditT04` (7 tests).

**T05 project-level dependencies.** Adds `contracts/dependencies.py`; `envelope.json` documents the `artifact_id`, `version` and `external` input fields.
- For each input it checks the ref, existence, type, ID, contract version and sha256, and the sticky statuses derived from the source. The check recurses through the sources' inputs.
- Refs outside the project root are refused before any read: absolute paths, `..` escapes and symlinks.
- External refs are `unresolved`. A missing hash is also `unresolved`.
- `formal_use_allowed` is false on any error, any unresolved finding or a failed upstream. CLI exit codes: 0, 1, 3, 2.
- Tests: `tests/contracts/test_dependencies.py` (11 tests).

**T06 split integrity.** Changed `skills/physics-ml/scripts/check_split_integrity.py`.
- Reports `group_coverage` and `timestamp_coverage` with the missing IDs, plus `status` and `failure_kind` (leakage and/or missing-metadata).
- `groups_checked` is true only with full coverage. `--strict` turns `incomplete` into `failed`. Exit codes: 0, 1, 3.
- Tests: `SplitGroupingCompletenessAuditT06` (7 tests).

**T08 manuscript.** Changed `check_manuscript.py` and `academic-papers-guide.md`.
- Keys resolve against `.bib` files, inline `\bibitem`s and `.bbl` files.
- Citations with no bibliography are reported as missing (`[NO BIBLIOGRAPHY]`, exit 1).
- `--external-bib` reports keys as unresolved (exit 3).
- Tests: `TestCitationsWithoutBibliographyAuditT08` (5 tests).

**T07 Berger–Boos.** Changed `core/stats/likelihood_limits.py` and the AMS module wording.
- The method is labeled an approximation of the construction. Output adds `coverage_claim`, `toy_p_value_error_at_threshold`, `inner_toy_p_value_error_at_threshold`, `within_validated_range` and `BB_VALIDATED_RANGE`. There is a new `neyman_coverage_scan`.
- The auxiliary measurement is drawn from the untruncated Gaussian used in the likelihood. `q̃` uses the constrained maximum (s, b ≥ 0) when the draw is negative. The grid handles a confidence set that lies below 0.
- Tests: `BergerBoosApproximationAuditT07` has 5 fast tests and 2 slow ones (`HEP_SLOW_TESTS=1`). The slow tests cover grid refinement (9 vs 33 points), toy precision (2000 vs 8000 toys) and a 36-point coverage scan.
- Coverage scan: s ∈ {0, 2, 5}, b ∈ {1, 3, 8}, σ_b ∈ {0.5, 2}, cl ∈ {0.90, 0.95}, 600 outer × 300 inner toys, seed 7. Every point is ≥ cl − 3σ_MC. The lowest is 0.8967 ± 0.0124. The results are in `tasks/hep-research/audit/bb-coverage-scan.json`.
- The plug-in profile went as low as 0.8717 ± 0.0137 (cl 0.90, s=2, b=8, σ_b=0.5).

## 4. Test results (after the fixes)

| Suite | Run | Pass | Fail | Error | Skip |
|---|---|---|---|---|---|
| Main unittest (`run_all_checks.py`) | 1094 | 1035 | 0 | 0 | 59 |
| Contracts (included above) | 114 | 114 | 0 | 0 | 0 |
| AMS-02 profile | 258 | 258 | 0 | 0 | 0 |
| synthetic-collider / qed-benchmark | 9 / 16 | all | 0 | 0 | 0 |
| Slow T07 tests (`HEP_SLOW_TESTS=1`) | 7 | 7 | 0 | 0 | 0 |

Tool checks: 13 pass, 0 fail, 1 skip. They cover layering, stanzas, registry, ams_optional, routing_static (48), packaging, traceability, measure_entrypoints and the plugin validator.

The outcomes fall into three separate groups:
- **Tool skips (57):** PyTorch 17, uproot/awkward 11, ROOT 12, pyhf 10, Graphviz/PlantUML/Mermaid 4, Combine 1, tectonic 1, legacy checkout 1. Skips are not evidence of success.
- **Deliberate skips (2):** the slow T07 tests, which were run separately and pass. The check run also skips the AMS ledger-preservation check because there is no legacy checkout.
- **Environment failures and product defects:** none.

The run is recorded in `tasks/hep-research/check-runs/check-run-2026-10-03T022907Z.json`.

## 5. Documentation updates

- `VALIDATION.md` has a new AUDIT-RUN section with per-task evidence and the coverage scan. It also gains two rows in the limitations table: blinding cannot see transformed values, and Berger–Boos coverage is validated only in range.
- `docs/capability-matrix.md`:
  - New rows: payload consistency, project-level dependencies, template-fit status, Berger–Boos (approximation, validated in range only) and manuscript check.
  - Updated rows: comparison gate, blinding and split integrity.
- `CHANGELOG.md` (new): an "Unreleased" entry lists every behavior change.
- `docs/provenance-new.csv` registers the three new files.

No text presents schema validity, program exit, a single-point coverage check or static routing as physical validity.

## 6. Open items

- **Behavior changes users will notice:** several checks now fail closed. Gate plans that compared differently worded processes need a justified mapping. Blinding scans that include figures need `--exempt` with a reason. Split manifests without groups are now `incomplete` (exit 3).
- **Out of T07's scope:** the profile-limit toys (`_toy_p1`) still truncate the auxiliary observation at 0. Changing it would change other commands' outputs.
- **Validated range:** Berger–Boos coverage is validated only at the 36 scanned points. It covers a single-bin background nuisance only.
- **Requested ID not verified:** the T05 `version` field is checked against the source's `contract_version`. Artifacts carry no separate artifact version.
- **Not done, as the work order says:** C01–C04 were not done because they were not requested.
- **Human decision:** C05 (license choice and reuse compatibility) is the owner's decision. No legal conclusions are given here.
