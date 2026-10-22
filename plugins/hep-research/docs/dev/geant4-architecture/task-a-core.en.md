# Task A: correctness fixes and boundary artifacts

> Document type: implementation spec (for the implementing agent and reviewers). Status: awaiting the maintainer's approval
> Basis: [`architecture.en.md`](architecture.en.md) (design rationale and reference experiments). This document is the executable spec; where the two disagree, this document wins and the disagreement is reported
> Order: **task A comes first**; task B ([`task-b-j15.en.md`](task-b-j15.en.md)) starts only after task A is merged
> Baseline: hep-research `main` at `9f08796` (0.23.0 plus unreleased changes), contracts 3.5.0, adapter geant4 0.1.0, Geant4 11.4.3
> Date: 2026-10-22
> Language: English translation of the Traditional Chinese original [`task-a-core.md`](task-a-core.md), with the same content. If they disagree, the Chinese wins and the English is corrected at the same time

---

## 0. Task card

**Goal.** Fix the defects (D1–D10) that let a simulation study be wrongly labelled `validated-in-scope`, and make the study layer know a simulation backend only through three boundary artifacts (run summary, column map, effective config).

**Two stages (in order, each merged separately):**

| Stage | Content | Version | Language |
|---|---|---|---|
| **A1** Correctness fixes | Contracts (benchmark table, scope, configuration and isolation), statistical rules (block batch means, exact intervals, MPV, IUT gate, detection limit, two-stage event count), first run summary (produced by Python from the per-event CSV); J14 regenerated | contracts **C1** (minor, sci-fix) | Python |
| **A2** Shared library and boundary artifacts | `g4sim` (per-event seeds, summary, probe); `layered_sim` writes the three boundary artifacts and supports per-event seeding; the study layer reads only the boundary artifacts | adapter **0.2.0**; contracts unchanged | C++ (`g4sim`, `layered_sim`) and Python |

**Out of scope:** `element_sim`, fields, plane crossings, ROOT files, `simroot`, `simreco`, J15, contracts C2 (all in task B). The `layered_sim` spec format (spec/1) is not restructured; only optional fields are added.

**Deliverables:** code and test changes; regenerated J14 records; sci-fix ledger entries and advisories; VALIDATION entries GEANT4-CORRECTNESS (A1) and GEANT4-SUMMARY (A2); CHANGELOG; release manifest.

**Definition of done:** every box in the acceptance lists A1.15 and A2.10 is ticked; every check in §9 passes.

**Before starting:**
1. Check whether `main` has moved past `9f08796`. If so, read the new CHANGELOG, redo the checks of appendix B (defect locations, `CONTRACTS_VERSION`, `GRADES`, advisory numbers, quick load, description length, journey list), and update this document (both languages).
2. Read §0 and §2 (principles) of [`architecture.en.md`](architecture.en.md); read the sci-fix process, the adapter-change process and the release steps in `docs/maintenance.md`.
3. Start A1 from `prototype/phase1-core.patch`: it implements A1.1, A1.2, the first half of A1.3 and the enum fix of A1.12, but predates this spec (it lacks `target_slabs`, the validation classes, per-benchmark scope dimensions, `hash_scheme`, the `dependencies.py` re-derivation and C1 gating; it gates at a hard-coded 3.6.0).

---

## 1. Terms and notation

| Term | Meaning |
|---|---|
| J14 | The existing journey `examples/geant4-thin-silicon/`: a thin-silicon study, the only Geant4 example with `validated-in-scope` records |
| study record | A computational-run record carrying `extension.study`; its `label` sets the artifact label |
| `validated-in-scope` | The label allowed only after validation by an upgrading benchmark with the declared scope inside the benchmark's scope; enforced by `_study_upgrade` in `contracts/validate.py` |
| validation class | The nature of a benchmark's reference: verification, reference, setup-matched, regression, surrogate, sanity, interface (§4.3). Task A uses reference, setup-matched, sanity and interface |
| observable kind | The controlled kind of observable (enum) in the study spec, e.g. `most-probable-value` |
| configuration | How the target is placed: `isolated` or `embedded` (A1.3) |
| logical run | N events, numbered 0 … N−1, fixed by the spec, the backend and the logical-run seed S; may be executed as several jobs |
| block | One of K segments of a logical run by event number, each with B events (N = K·B); the unit of batch means |
| three boundary artifacts | run summary (`simulation-summary/1`), column map (`simulation-columns/1`), effective config (engine-independent envelope plus the actual geometry tree) |
| `seeding` | `stream` (old behaviour: a continuous random stream in serial) or `per-event` (each event reseeds with H(S, event number); available from A2) |
| `hash_scheme` | How the target hash is derived: `spec-v1` (A1, from spec/1) or `tree-v1` (from A2, from the geometry tree) |
| C1, C2 | The next unused contracts minor at merge time (C1 belongs to task A; C2 to task B); version numbers are fixed only at merge |
| E2 | An environment with a Geant4 11.4.3 build |
| IUT | intersection-union test: passes only if every observable is equivalent |
| DL | detection limit of a negative control |
| sci-fix | The process in `docs/maintenance.md` for fixing scientific-correctness defects |
| Notation | "A1.6" is a work item of this document; "§7" is a section of this document; "B1.3" is a work item of task B; "architecture §5" is a section of `architecture.en.md` |

**Main files (relative to `plugins/hep-research/`):**

| Purpose | Path |
|---|---|
| Contracts | `contracts/validate.py`, `contracts/dependencies.py`, `contracts/schema.py`, `contracts/schemas/ext_computational_run.json` |
| Study layer | `skills/hep-detector/scripts/check_geant4_study.py` (`convergence()` line 335, relative difference line 357, decision line 359, `scope_within()` line 482), `geant4_benchmarks.py` (`bootstrap()` line 197, `mpv()` line 204, detection limit line 274, `at_limit` line 678), `tracker_resolution.py`, `multiple_scattering.py`; `skills/hep-detector/assets/geant4-study-spec.schema.json`; `skills/hep-detector/references/geant4-study-protocol.md` |
| Adapter | `adapters/geant4/adapter.json`; `adapters/geant4/assets/geant4_run.py` (`SIM_SOURCES` line 63, `validate_spec()` line 103, `cmd_scan` line 435, `cmd_chunk` line 491, `cmd_summarize` line 525), `geant4_build.py` (`GEANT4_USE_GDML: OFF` line 53), `geant4_verify.py`; `adapters/geant4/assets/layered_sim/` (`Detector.cc`, `Spec.cc`, `Actions.cc` (CSV format `%.10g` line 23; deposit multiplied by track weight line 113), `Physics.cc`, `layered_sim.cc` (seeds and run manager lines 150–154), `MiniJson.hh`, `spec.schema.json`, `output.schema.json`) |
| Core | `core/status.py`, `core/trace.py`, `core/OWNERS.json`, `core/partition/engine.py` (`NON_ADDITIVE_TOKENS` line 381) |
| J14 | `examples/geant4-thin-silicon/run.py`, `recorded/` (`events/` with 5 reduced CSVs, `runs/`, `summaries/`, `specs/`), `output/` |
| Tests | `tests/contracts/test_geant4_upgrade.py`, `test_simulated_dataset.py`, `test_schema_keywords.py`; `tests/adapters/test_geant4.py`; `tests/examples/test_geant4_thin_silicon.py`; `tests/skills/test_cli_robustness.py` |
| Tools | `tools/run_all_checks.py`, `check_layering.py`, `check_relocation.py`, `check_ownership.py`, `check_packaging.py`, `measure_entrypoints.py`, `reference_inventory.py`, `capability_map.py`, `check_routing_static.py`, `scifix_advisories.py` |

---

## 2. Hard rules

Breaking any of these blocks the merge.

1. **Layering.** Skill scripts and adapters import only `core` and `contracts`. New shared Python modules go in `core/`, with a steward named in `core/OWNERS.json`.
2. **Experiment names.** No experiment names (ALICE included) in `skills/` or `contracts/` (`check_layering.py`); use citation keys where needed.
3. **Python uses only the standard library**; no Python bindings. The t and F quantiles (non-integer degrees of freedom) and Garwood intervals needed by the statistics are implemented on the existing `beta_ppf` of `core/stats/` as `t_ppf`, `f_ppf` and `garwood`, placed in `core/stats/` with a steward named in `core/OWNERS.json` (shared numerical functions, not the "new core validators" of §10).
4. **C++ dependencies.** `g4sim/SimSummary.hh`, `SimHash.hh` and `MiniJson.hh` use only the C++17 standard library; `SimProbe.hh`, `SimSeed.hh` and `layered_sim` link Geant4. No third-party libraries.
5. **G5 licence boundary.** Python exchanges only JSON and CSV with separate executables; code is written from the Geant4 API, without copying or adapting Geant4 example code.
6. **Status and exit codes** (`core/status.py`): 0 ok, 1 negative verdict (`refused`/`failed`), 2 unusable input (`rejected`), 3 `incomplete`. Unresolved and target-missed are always 3.
7. **Execution trace.** New record writers call `trace.provenance()`; new shared functions call `trace.tag()`; calls to C++ executables record the sha256 of the executable and its sources, the version and the subcommand.
8. **Size and paths.** Each file ≤ 2 MiB, and `check_packaging.py` scans all text files; written paths go through `tilde()`; size claims in the plugin README must be within 10 % of the actual value.
9. **Entry budget.** hep-detector quick load ≤ 25,600 bytes (now 24,669), description ≤ 1,024 characters (`measure_entrypoints.py` reports 1,016; the raw length with quotes is 1,018). This task does not change `skills/hep-detector/SKILL.md` or the description.
10. **Process.** A1 follows the sci-fix process; A2 the adapter-change process; both follow the release steps. Work only on branch `worktree-geant4-architecture`; do not push to `main` or open a pull request without the maintainer's approval.
11. **Contract versions.** New rules are gated with `strict or _at_least(contract_version, C1)`, with no warning branch.
12. **The offline replay of J14** always runs, without Geant4 or a compiler.
13. **No change to existing outputs.** A2 only adds files and optional fields; J14's existing specs must produce a CSV bit-identical to the pre-A2 one (same host).
14. **Not done:** integer quantization, 128-bit integers, bit-identical statistics, spec-format conversion, `simstat`, a `simcore` not linked to Geant4 (reasons in architecture §13).

---

## 3. Background: confirmed defects (`9f08796`)

| # | Defect | Location | Consequence | Work item |
|---|---|---|---|---|
| D1 | Scope check does not compare the observable; dimensions missing from the declaration are unconstrained | `validate.py` `_scope_inside()` (from line 349); `check_geant4_study.py` `scope_within()` (lines 482–493, the loop skips observable and ignores scalars) | A study that passed an MPV benchmark can label other observables `validated-in-scope` | A1.2 |
| D2 | A benchmark's grade is declared by the record itself | `_study_upgrade` (line 395; filter line 419) | Writing `"grade": "reference"` is enough to upgrade | A1.1 |
| D3 | Negative control compared across units, tested in one direction only | `geant4_benchmarks.py` line 678 | Detection limit not demonstrated on the observable | A1.10 |
| D4 | Convergence gate has no equivalence test | `check_geant4_study.py` line 359 | Passes about 50 % of the time when the true difference equals the tolerance | A1.8 |
| D5 | MPV SE from bootstrap | `geant4_benchmarks.py` line 369 | Inconsistent variance estimate; J14's detection limit is built on it | A1.6, A1.7 |
| D6 | Stopping rule does not forbid adding events based on results | protocol section 4 | Optional-stopping bias | A1.11 |
| D7 | Evidence correlation not disclosed | J14's nominal run shared by gate, statistics target, benchmark and variation | Treated as independent evidence | A1.11 |
| D8 | Study-spec benchmark enum lacks `shower-containment` and `longitudinal-profile` | `geant4-study-spec.schema.json`; `GRADES` has 9, the enum 7 | Consistency gap (no runtime effect) | A1.12 |
| D9 | Study layer bound to layered_sim's data format | `derived()` reads `geometry.layers`; `summarize` and benchmarks read fixed column names | Other backends cannot enter | A2.6 |
| D10 | Test-order dependence | `tearDownModule` of `test_geant4_upgrade` deletes the shared J14 replay directory; 5 tests of `test_simulated_dataset` error | Errors depend on execution order | A1.12 |

---

## 4. Design summary (what the implementation needs to know)

### 4.1 Two planes

Per-event processing is in C++ (the simulation programs; from A2 also the summary accumulation); inference after merging, decisions, records and contracts are in Python. Each quantity has one production implementation; an implementation in the other language may exist only in tests as an oracle. In A1 the summary is produced by Python from the per-event CSV; from A2 it is produced by `layered_sim`, and the Python producer stays only in tests.

### 4.2 What reproducibility means

| Level | Requirement |
|---|---|
| Traceability | Every record keeps the spec, effective config, code (`sources_sha256`), seeds, and hashes of input and output files |
| Re-execution | Same build and platform, same logical run: identical event content; summary integer accumulators identical, floating-point relative difference ≤ 1e-12 |
| Replay (from committed summaries and records) | Decisions and labels identical; numbers within relative 1e-9; decisions with a margin < 1e-9 (relative) flagged "near threshold" in the record |
| Regression check (A2) | J14's existing specs (`seeding: stream`) produce a CSV bit-identical to the pre-A2 one on the same host |

### 4.3 Validation classes

| Class | Reference | Upgrades | Introduced |
|---|---|---|---|
| verification | Exact consequence of the inputs (analytic helix, kinematics) | No | C2 |
| reference | The physics model Geant4 approximates, or thin-target measurements, on an isolated target | Yes (in scope) | C1 |
| setup-matched | A published measurement, target hash equal to the measured configuration, and isolated | Yes (in scope) | C1 |
| regression | The same study at a previous version | No | C2 |
| surrogate | A fast simulation or surrogate model referenced to a full simulation | No physics-label upgrade | C2 |
| sanity, interface | Plausible range, interface checks | No | existing |

---

## 5. Stage A1: correctness fixes (contracts C1, sci-fix)

A1 changes only Python. Statistics are computed by Python from the per-event CSV; from A2 they read the summary written by `layered_sim`.

### A1.1 Benchmark table (D2)

**Change:** `contracts/validate.py` (new constant table; `_study_upgrade` takes class, grade, kind and scope dimensions only from the table); `geant4_benchmarks.py` (`GRADES` kept for the tool, its values changed to the table's class, plus a consistency test).

**Grade is class.** The table's second column is also the value the record's `grade` field must have; there is no separate grade column.

| benchmark | Class | Supported kind | Scope dimensions (type) |
|---|---|---|---|
| `stopping-power` | reference | `stopping-power` | particle (categorical), material (categorical), energy (interval), thickness (interval) |
| `range` | reference | `range` | same |
| `thin-layer-mpv` | reference | `most-probable-value` | same |
| `thin-layer-width` | sanity | `thin-layer-width` | same |
| `multiple-scattering` | sanity | — | — |
| `em-shower-shape` | sanity | — | — |
| `shower-containment` | sanity | — | — |
| `longitudinal-profile` | setup-matched | `shower-maximum` (new kind, t_max only) | particle (categorical), energy (interval), target hash |
| `published-data` | interface | — | — |

**Rules:**
- A class or grade in the record that differs from the table, or a benchmark name not in the table: error. Applies to every record with a Geant4 study block.
- Only reference and setup-matched are counted by `_study_upgrade`.
- A benchmark's supported kinds and scope dimensions come only from the table; values output by the tool are for reading only.
- The table's 9 benchmark names equal the current `GRADES`; the values of `GRADES` become the table's class, the only change being `longitudinal-profile`: reference → setup-matched (`geant4_benchmarks.py` lines 92–94). The study spec's grade enum gains `setup-matched` (A1.12); the prototype patch's `("reference", ("shower-shape",))` is corrected along with it.
- J14's decisions are unchanged, but the content of study and benchmark files changes (new fields; `code_paths` gains `contracts/validate.py`).

### A1.2 Scope check (D1)

**Change:** `contracts/validate.py` (the single implementation, exported); `check_geant4_study.py` (imports it, deletes `scope_within()`; `label` writes `declared_scope.observable_kind`); study-spec schema (`validation_plan.scope` is `additionalProperties: false`; add `observable_kind`).

**Rules:**
- Compare the controlled `observable.kind`, not free text.
- The declared kind must be among the kinds supported by the counted benchmarks.
- The dimension list is per benchmark (fourth column of A1.1); categorical dimensions compare by set inclusion, interval dimensions by interval inclusion; a scalar is treated as [v, v].
- Every dimension the benchmark has must be in the declared scope; a missing one counts as out of scope.
- When the target hash is a dimension, the declared scope must carry the same `target_geometry_sha256` and `hash_scheme`.
- Gating: `strict or _at_least(contract_version, C1)`, no warning branch; records at 3.5.0 or below are constrained only under `--strict`, and only records with `validated-in-scope` fail.

### A1.3 Configuration and isolation

**Change:** `geant4_benchmarks.py` (output); `contracts/validate.py` (rule); `contracts/dependencies.py` (re-derivation).

- `geant4_benchmarks.py` outputs, for each benchmark result, `configuration`, `target_geometry_sha256`, `hash_scheme: spec-v1` and `configuration_basis`, derived from the spec/1 of the run record named by the benchmark setting's `run_record`, never from user input. A benchmark that is counted for upgrade must have a `run_record`.
- **Target:** the benchmark setting declares `target_slabs` (the names of the slabs in the target, absorbers included). A single-layer benchmark defaults to the measured slab; `longitudinal-profile` must list the whole sampling stack (its `layers` lists only the readout columns).
- **Vacuum:** the world material is `G4_Galactic`, or density < 1e-20 g/cm³.
- **isolated:** the world is vacuum and every placement other than the world belongs to the target; spec/1 has no field and is treated as field-free (the field rule takes effect in task B: only a field attached inside the target belongs to the target and counts in the hash). Otherwise embedded.
- **`spec-v1` normal form:** the ordered slabs, thicknesses, transverse sizes, material names and declared compositions; repeated placements listed one by one; numbers as Python `float.hex()`; sha256 of the JSON of this list (sorted keys, no whitespace).
- **Contract rule (C1):** a counted reference benchmark must be isolated; a counted setup-matched benchmark must be isolated and its target hash and `hash_scheme` must equal those of the benchmark's measured configuration. Missing or embedded are errors. `dependencies.py` **must** re-derive from the run records in `evidence_records` and compare.
- Residual limits (written into the protocol): J14's recorded CSVs are reduced, so their hashes do not match the run records' `output_hashes`; configuration describes the run record the setting names. The geometry of negative-control runs is not checked separately.

### A1.4 Logical runs and seeds

- Each evidence point (trial, nominal, scan, control, variation, calibration, regression) is one logical run, with seed S = H(study_id, role, point_id); the two directions of a control use different point_ids.
- **Definition of H** (Python and C++ must agree; the C++ one is in `SimHash.hh` of A2.1): H(x₁, …, x_n) = int.from_bytes(sha256("\x1f".join(str(x) for x in (x₁, …, x_n)).encode("utf-8"))[:8], "big") % (2³¹ − 1) + 1, with values in [1, 2³¹ − 1]. Integers are written as decimal strings without leading zeros.
- New recordings in A1 always use `seeding: stream` (`layered_sim`'s current behaviour). A single job's seed pair is (H(S, 0, 0), H(S, 0, 1)). Do not use `make_manifest`'s `seed × 100003 + k`, nor `cmd_scan`'s `[s0, s1 + k]` or `cmd_chunk`'s `start + 1` any more.
- A logical run may be split into several jobs (`geant4_run.py chunk` with a hand-made manifest, each job covering a range of event numbers): the job starting at event e has seed pair (H(S, e, 0), H(S, e, 1)); S is recorded separately in the run record. Seeds within one manifest then differ, and `validate_manifest`'s `partition.duplicate_seed` check needs no change. Under `stream`, different splits give different events, but statistically equivalent ones.
- `check_geant4_study.py` checks that S is not repeated across all run records of a study. The 5 J14 runs not re-recorded in A1 (A1.13) have no S: they are registered with their original seed pairs (first seed 1401 or 1402) as `seed_scheme: legacy`, and only their full seed pairs are checked for repetition.

### A1.5 First run summary and the Python producer

**Change:** new `adapters/geant4/assets/summary_from_csv.py` (or a `summarize-blocks` subcommand of `geant4_run.py`); the `simulation-summary/1` schema goes in `adapters/geant4/assets/`.

- **Input:** per-event CSVs of one or more jobs, the observable declarations (the new top-level `observables` of the study spec, defined in A1.12), block size B and block count K.
- **Selection:** each observable accumulates only events that satisfy its `selection` (e.g. MPV and `tail_fraction` need `primary_fate == 1` and `primary_end_process == "Transportation"`; see `geant4_benchmarks.py` lines 232–236 and `check_geant4_study.py` line 284); `n` is the number of selected events, and the total number of events per block is recorded as well.
- **Blocks:** event i (the `event` column minus the logical run's first event number) belongs to block ⌊i/B⌋; events with i ≥ K·B are ignored and their number noted in the record.
- **Accumulators per block and observable:** integers `n`, per-bin histogram counts (fixed binning; overflow and underflow separate), `count_if[]`; floating point Σx, Σx², `min`, `max` (Neumaier compensated summation).
- **Output fields:** `run` (logical-run identity and seed, event range, `seeding`, B, K, spec hash, producer `python-csv` and version), `observables[]`, a `merge` rule for each accumulator (`sum`, `min`, `max`, `hist`). Multiple jobs merge by block number.
- **Event weights:** if the CSV has a `weight` column it must be all 1, otherwise exit 2 (deposits are already multiplied by the track weight; see `Actions.cc` line 113). Without a `weight` column (J14's 5 reduced CSVs have none), the summary records `weight_column: absent`, justified by the absence of biasing commands in the run record's spec; with biasing commands in the spec, exit 2.
- From A2, `layered_sim` writes the summary with the same schema; this Python producer then stays only in tests as an oracle.

### A1.6 Estimators and SE

**Change:** `check_geant4_study.py`, `geant4_benchmarks.py` (read only the summary; drop production use of `bootstrap()`, keep it in tests for comparison).

- For each block b compute θ_b; report θ̄ = mean, SE = sd(θ_b)/√K with K − 1 degrees of freedom. K ≥ 16, declared before the first evidence run.
- Several observables: the per-block vector of estimates is kept together, and covariances are estimated from these vectors.
- Full-sample values: means and proportions are also computed from the merged accumulators, and their difference from θ̄ is recorded as a diagnostic.
- Quantiles: linear interpolation within the histogram; bin width divided by the estimate must be below 1/10 of the relative tolerance; landing in the overflow or underflow bin makes it incomplete.
- The t and F quantiles and Garwood intervals of this section and of A1.7–A1.10 use `t_ppf`, `f_ppf` and `garwood` in `core/stats/` (§2 rule 3); Clopper–Pearson uses the existing `clopper_pearson` (`core/stats/tail_estimation.py`).
- **Low counts:** when any block of a count estimator is 0, or the merged total is < 100 (threshold can be declared), use exact intervals on the merged accumulators instead: Clopper–Pearson for proportions, Garwood for counts; comparing two runs uses the exact conditional-binomial interval for the ratio of rates, relative difference = ratio − 1. There is then no SE, and the gate decides on interval endpoints (A1.8).
- Assumption: no state between events. The probe (A2) records biasing and similar settings; in A1, J14 satisfies the assumption.

### A1.7 MPV (D5)

- In each block's histogram take the maximum bin and interpolate the mode with a three-point parabola through it and its two neighbours; report the mean of the K modes and its SE (A1.6). This replaces the five-point least-squares fit of the current `mpv()`, noted in the S1 ledger entry.
- **Edge cases:** bin origin and width come from `observables[].bins`; ties for the maximum bin take the lowest index; when the maximum bin is the first or last valid bin, or the denominator y₋ − 2y₀ + y₊ = 0, that block's mode is the centre of the maximum bin, and such blocks are counted and recorded; if they exceed K/4 the benchmark is incomplete.
- **At design time:** estimate the bias with toys at the declared B and bin width; the toys' 95 % upper bound must be ≤ tol/10. The toys use a Landau–Vavilov distribution, checked against the histogram shape of one high-statistics Geant4 run.
- **Every execution:** with m the three-point interpolated mode of the merged histogram, |θ̄ − m|/|m| ≤ tol/5 + 2·SE/|m| (tol is the relative tolerance); otherwise that benchmark is incomplete.
- Block MPVs must not go through the partition merge rules (`mpv` is not in `NON_ADDITIVE_TOKENS`); they are computed only from the summary histograms.

### A1.8 Convergence gate and reporting (D4)

**Change:** `convergence()` and `cmd_run` in `check_geant4_study.py`.

- **Difference:** keeps the convention of line 357: a is the finest setting and b the second-finest (`vals` sorted ascending, a = `finest[0]`, b = `finest[1]`). Each observable's tolerance declares a `tolerance_mode`: with `relative` (default) diff = (a − b)/b and se_diff = √(se_a² + se_b²)/|b|; with `absolute` diff = a − b and se_diff = √(se_a² + se_b²). ν from the Welch formula per pair (30 for equal variances and K = 16).
- **Event-count target:** the se target per point is tol/(4√2) (a relative se under `relative`).
- **Decision:** pass |diff| + t₀.₉₅(ν)·se_diff ≤ tol, **and both points meet their se target**; fail |diff| − t_{1−α/m}(ν)·se_diff > tol (α = 0.05, m the number of (parameter × observable) pairs; a point that missed its se target can still give fail, since a larger se only makes fail harder); otherwise unresolved. Low counts: pass = the 90 % interval lies inside [−tol, tol]; fail = the one-sided 1 − α/m interval lies entirely outside.
- **Reporting:** unresolved and target-missed are reported as `incomplete` (exit 3), and the label stays `unvalidated`; only fail is `failed` (exit 1). Today every non-pass is treated as `failed`; this must change.

**Operating characteristics** (recomputed by `gate_operating_characteristics.py`, 2×10⁶ toys per cell. "se = target": se_diff equal to the target, estimated with ν = 30; "two-stage": each of the two points designed per A1.9, K = K_trial = 16, ν from the Welch formula on the estimated se):

| True difference | Pass (se = target) | Pass (two-stage) | Pass (two-stage, given both points met the target) | Fail m = 1 (se = target) | Fail m = 30 (se = target) | Fail m = 30 (two-stage) |
|---|---|---|---|---|---|---|
| 0 | 0.976 | 0.809 | 0.999 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.621 | 0.696 | 0.860 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.044 | 0.054 | 0.050 | 0.002 | 0.002 |
| 2 tol | 0.000 | 0.000 | 0.000 | 0.988 | 0.780 | 0.952 |

- Under the two-stage design about 19 % of point pairs have at least one point that missed its target, which is why the pass rate at a true difference of 0 is only 0.809.
- At a true difference of tol the unconditional pass rate is 0.044 ≤ 0.05, but given that both points met the target it is 0.054, slightly above the nominal 0.05 (points that meet the target have a smaller se); the protocol discloses this.
- At a true difference of tol about 90 % are unresolved; the protocol states the expected incomplete rate.

### A1.9 Two-stage event count

- N = ceil(N_trial·(SE_trial/target)²·f), f = F₀.₉₀(K − 1, K_trial − 1) (≈ 1.97 when both are 16).
- About 10 % of evidence runs miss their target and are incomplete; **no top-up is allowed** (if the maintainer chooses F₀.₉₅ ≈ 2.40, about 5 %, with about 22 % more events; §11).
- Misses are independent per run: about 19 % of the point pairs of a convergence gate are incomplete; a study needing n runs with an se target has all of them meet it with probability about 0.9ⁿ (about 0.53 at n = 6). The protocol states this; regenerated J14 may lose `validated-in-scope` by chance, and how to handle that is the maintainer's decision (§11).
- The 5 J14 runs not re-recorded in A1 have fixed event counts not planned by this design; their se is still compared with the target, and a miss is likewise incomplete.
- With low counts, plan with the trial run's Poisson variance.

### A1.10 Negative controls and detection limit (D3)

**Change:** `geant4_benchmarks.py`.

- Test quantity: shift = (control − nominal)/reference, SE combined from the two runs.
- **Definition of caught:** the control's benchmark verdict is fail, i.e. |rel_c| > tol (rel_c is the control's deviation from the reference); consistent with the current code, which uses the control's benchmark verdict (`geant4_benchmarks.py` around line 672).
- Detection limit: DL = tol + |rel| + t_{0.977}(ν)·se_rel (replacing `2 * se_rel` at line 274); rel is the nominal's deviation from the reference, se_rel the combined SE of the shift, ν its Welch degrees of freedom.
- Design requirement: toys show the probability of catching an injection at DL is ≥ 0.977. With the definition above the true power is near 0.977 (the reviewer's calculation: about 0.9785 at ν = 15 and 30; it varies slightly with the ratio of the control's SE to the shift's SE), so the toy acceptance threshold is 0.977 − 3σ_MC (A1.15).
- Inject in both directions; otherwise narrow the claim to one direction, recorded in `scope.detection_limit_sign`. At the detection limit = caught and |shift| ≤ 1.1 × DL.
- A single miss is recorded and explained, not an automatic failure; rerunning with another seed is not allowed.
- J14's existing controls inject only +density; until negative controls are recorded, J14's two claims are narrowed to `detection_limit_sign: "+"`.

### A1.11 Stopping rule, evidence correlation and trace (D6, D7)

- Protocol section 4: the stopping rule, scan grid, K and B, and the handling of unresolved results are written into the study spec before the first evidence run.
- `extension.study.evidence_overlap` lists runs shared by several decisions, with `evidence_overlap_version`.
- Trace tags (lowercase, hyphenated): `geant4-scope-kind`, `geant4-configuration`, `geant4-convergence-iut`, `geant4-batch-means`, `geant4-mpv-block`, `geant4-seed-hash`. Once `check_geant4_study.py` imports `contracts.validate`, `code_paths` gains `contracts/validate.py`; this change is expected.

### A1.12 Other fixes (D8, D10)

- The study-spec benchmark enum gains `shower-containment` and `longitudinal-profile`; the grade enum (now reference, sanity, interface) gains `setup-matched`; the observable-kind enum gains `shower-maximum`; `validation_plan.scope` gains `observable_kind`.
- The study spec (top-level `additionalProperties: false`) gains top-level properties:
  - `observables`: an array, each item `{name, source_column, selection, bins: {lo, hi, width}, thresholds, tolerance_mode}`. `name` must equal the names used in `convergence_plan.observables` (e.g. `mpv_deposit_MeV`); `selection` is a declarative filter on CSV columns (column name, comparator `==`, `!=`, `<`, `<=`, `>`, `>=`, value; several conditions are ANDed); `thresholds` feed `count_if`; `tolerance_mode` see A1.8.
  - `blocks: {K, B}`.
  - The existing singular `observable` is unchanged and remains the study's main observable.
- `ext_computational_run.json` declares the existing `simulation` property in the schema (J14's run records already carry `extension.simulation` and `_study_upgrade` already tests it; the schema does not declare it yet; needs hep-computing's agreement).
- D10: `test_geant4_upgrade` and `test_simulated_dataset` no longer share a temporary directory that gets deleted (each builds its own replay, or a package-level fixture is used).

### A1.13 Regenerating and recording J14

| Run type | Today | What A1 does |
|---|---|---|
| The 5 runs with per-event CSV (`events/`, with an `event` column) | A single reduced CSV | No re-recording: cut blocks offline with the A1.5 producer, produce and commit `simulation-summary/1` |
| 13 scan, variation and scenario runs (e.g. `mpv-cut-0.1`, `sp-em-option3`, `mpv-density-10`) | Only `geant4-run-summary/1` (one value plus a bootstrap SE) | Re-record live in E2 with `seeding: stream`; produce and commit the summary; CSV not committed |
| Negative-direction (−density) controls | Do not exist (the existing `mpv-control` and `sp-control` inject only +density) | Record new ones in E2; commit the summary |

- Replay: `examples/geant4-thin-silicon/run.py` computes from the committed summaries instead, meeting the replay requirement of §4.2; no Geant4 or compiler needed.
- Old `geant4-run-summary/1` files are kept, only for replaying old records.
- The size of `recorded/` is measured in A1 and limited by `check_packaging.py`; the cap is the maintainer's decision (§11).

### A1.14 Version and sci-fix process

- **Version:** contracts C1 (minor). Precedents for new gated rule families (2.4.0, 2.6.0, 2.8.0, 3.1.0, 3.2.0) were all minor.
- **Ledger:** one entry per defect, `changelog` as a structured object (`{"kind": "unreleased", ...}`).

| Defect | Ledger entry | Severity | Reason |
|---|---|---|---|
| D1 (incl. per-benchmark scope dimensions) | scope-kind | S2 | Changes decisions |
| D2 (incl. validation classes) | grade-table | S2 | Changes decisions |
| D3 (incl. detection limit with t quantile) | control-shift | S2 | Changes decisions |
| D4 (incl. definition of diff and se) | gate-IUT | S2 | Changes decisions |
| D5 (incl. block batch means instead of bootstrap, exact count intervals, MPV interpolation) | variance-method | **S1** | Changes reported numbers |
| Isolation definition (incl. vacuum) | isolation | S2 | Changes decisions |
| D6 | stopping-rule | S3 | Guidance only |

- **Evidence:** S2 needs levels C2 and D2; S1 needs levels C3 and D2 (evidence levels from `docs/maintenance.md`, not this document's defect D2). Evidence tests run through the command lines of `validate.py` and `check_geant4_study.py` so that they can run on the parent commit; what cannot run goes in `gaps`.
- **Advisories:** one for S1 and one for S2 (`scifix_advisories.py check` requires an advisory's severity to equal that of every ledger entry it lists); numbers are the next unused at merge (now SFA-2026-038 and -039).
  - Keys: `artifact_types: [computational-run]`, `extension_keys: ["study", "evidence_records"]`.
  - Range: introduced 0.20.0, with `database_specific.introduced_basis`; affected versions 0.20.0–0.23.x and unreleased.
  - Simulated dataset-records cannot be distinguished by keys; the remedy asks holders to run `contracts/dependencies.py` on every simulated table.
- Study records produced from 0.20.0 on with `validated-in-scope` fail under `--strict`; the advisory says what to do (regenerate with the new version).

### A1.15 A1 acceptance

- [ ] Records with a kind mismatch, a declaration missing a dimension, a class or grade differing from the table, a missing or embedded configuration, or a mismatched target hash or `hash_scheme` are rejected under `--strict` and C1; a `dependencies.py` re-derivation mismatch is rejected; scalar scopes compare correctly.
- [ ] Regenerated J14 study records pass `validate.py --strict` and `dependencies.py`; any change in decisions is recorded with its reason.
- [ ] Gate toys (10⁴ per cell, with the model stated in the A1.8 table header) agree with the A1.8 table to ±3σ_MC; the `absolute` mode and the interval decisions for low counts are tested.
- [ ] Coverage toys for block batch means: for each class of J14 estimator (mean, proportion, quantile, mode), the actual coverage of a nominal 90 % interval satisfies |coverage − 0.90| ≤ 0.02 + 3σ_MC, reported per class.
- [ ] MPV bias toys: 95 % upper bound ≤ tol/10; the per-execution check is in effect.
- [ ] Detection-limit toys (the caught definition of A1.10): probability of catching an injection at DL ≥ 0.977 − 3σ_MC; the outcome of J14's realised controls recorded in VALIDATION.
- [ ] J14's offline replay runs from the committed summaries, decisions meet §4.2, without Geant4 or a compiler.
- [ ] Unit tests of the Python producer: block division, merging, exit 2 when `weight ≠ 1`, overflow bins.
- [ ] `python3 -m unittest discover -s tests/contracts -t .` has no errors.
- [ ] Seven ledger entries, two advisories passing `scifix_advisories.py check`, parent records complete; live Geant4 evidence recorded with release-gate; VALIDATION GEANT4-CORRECTNESS; CHANGELOG; release manifest.

---

## 6. Stage A2: shared library and boundary artifacts (adapter 0.2.0)

A2 does not change `layered_sim`'s spec format or existing outputs; it only adds optional fields and files.

### A2.1 `g4sim`

**Location:** `adapters/geant4/assets/g4sim/` (headers; shared by `layered_sim` and task B's `element_sim` and `simreco`; owner hep-detector). The directory is not named `g4common`, to avoid confusion with the existing Python module `assets/g4common.py` (imported by four scripts, listed in `adapter.json`).

| File | Content | Dependency |
|---|---|---|
| `SimHash.hh` | SHA-256 (written in the plugin) and H(x₁, …, x_n) as defined in A1.4, checked against the Python implementation with test vectors; also a SplitMix64 generator and Box–Muller normal deviates (for programs not linked to Geant4, identical across platforms) | C++17 standard library only |
| `SimSeed.hh` | The two seeds of event i, (H(S, i, 0), H(S, i, 1)); calls `G4Random::setTheSeeds` | Geant4, `SimHash.hh` |
| `SimSummary.hh` | Block accumulators (the fields of A1.5), Neumaier summation, merging, JSON writing of `simulation-summary/1` | C++17 standard library only |
| `MiniJson.hh` | Moved from `layered_sim/` (content unchanged; `layered_sim` includes this copy instead) | C++17 standard library only |
| `SimProbe.hh` | The probe (A2.4) | Geant4 |
| Helpers | Material construction (including the order of mixtures), physics-list selection, CSV writing | Geant4 |

- For `layered_sim`, moving code with the same function into `g4sim` must not change its behaviour (guaranteed by the regression check).
- `SimSummary.hh` is tested in an environment without Geant4 by an optional ctest (optional CI job).

### A2.2 Per-event seeding

- `layered_sim` spec/1 gains an optional `run.seeding`: `stream` (default, existing behaviour) or `per-event`.
- `per-event`: event i reseeds with `SimSeed.hh` at the **start** of `GeneratePrimaries` (before any random draw), i being the global event number. Geant4 calls `GeneratePrimaries` before `BeginOfEventAction`, so reseeding cannot happen in `BeginOfEventAction`; `BeginOfEventAction` must not draw random numbers. The same logical run gives identical events for any split into jobs and any thread count.
- J14's existing specs are not changed and stay `stream`. Specs of new studies get `per-event` written by the adapter by default.

### A2.3 `layered_sim` writes the run summary

- spec/1 gains optional `output.observables` (source column, binning, thresholds) and `output.blocks` (K, B, the logical run's first event number). `geant4_run.py` writes them into the execution spec from the study spec's observable declarations.
- At the end of each event, the declared observables are accumulated into their block; under MT they merge through a custom `G4VAccumulable`: `G4AccumulableManager::Reset()` is called at the start of every run (`BeginOfRunAction`); workers call `G4AccumulableManager::Merge()` in their own `EndOfRunAction`, the master writes in its own `EndOfRunAction`; master and workers register in the same order.
- Output `summary.json` (`simulation-summary/1`, producer `layered_sim`), its hash written into the run record.
- Event weight ≠ 1: exit 2.
- **Test dump:** with `output.debug_observable_dump: true` in the spec, a side file lists the declared observables per event as `%.17g`; used only in tests, and the CSV itself is unchanged.

### A2.4 Effective config and the probe (`SimProbe.hh`)

```
{ "engine": "geant4", "engine_version": "11.4.3", "probe_version": "...",
  "backend": {"name": "layered_sim", "version": "...", "sources_sha256": "..."},
  "source": "probe" | "declared", "recorded": true, "config_sha256": "...",
  "seeding": {"mode": "per-event" | "stream", "logical_run_seed": ...},
  "geometry": { "tree": [...], "tree_sha256": "...", "hash_scheme": "tree-v1", "gdml_sha256": null },
  "environment_ref": "<hash of the build record>",
  "sections": { "geant4": { ... } } }
```

| Item | Spec |
|---|---|
| When | The master's `BeginOfRunAction` (called inside `G4RunManager::RunInitialization`, after the kernel closes the geometry); state `G4State_GeomClosed` and more than 0 couples; otherwise `recorded: false` (layered_sim still exits 0), and that run cannot upgrade. A fake run (`/run/beamOn 0`) returns before `BeginOfRunAction`, so the probe does not run |
| Frequency and threads | Once per run; master only; noted as "workers assumed identical" |
| Geometry tree | Rebuilt from `G4PhysicalVolumeStore` (a flat list in creation order) and each volume's mother logical volume; per placement: name, copy number, solid type and parameters, material (composition and density as resolved by Geant4), transform, mother, attached field manager and parameters; numbers written in the format of Python `float.hex()` (e.g. `0x1.0000000000000p+0`): C's `%a` output differs (`0x1p+0`), so `SimProbe.hh` carries its own formatter, checked against Python with test vectors; replica and parameterised volumes record their parameterisation |
| `tree-v1` target hash | sha256 of the JSON (sorted keys, no whitespace) of the target placement's subtree (ordered placements, solid parameters, material composition and density, transforms, attached fields) |
| GDML | The plugin's build has GDML off; when a user build has GDML, `gdml_sha256` may be attached, but is not required |
| EM parameters | Full text of `G4EmParameters::StreamInfo(os)` plus parsed fields; not `Dump()` |
| Cuts | Per material-cuts couple: material, region, range cut, energy threshold per particle |
| Hadronic models | Per process and model, energy ranges queried with `GetHadronicInteractionList()` and `GetMinEnergy(mat, elm)`, `GetMaxEnergy(mat, elm)`; overlapping ranges marked as random selection. **Must not** call `G4EnergyRangeManager::GetHadronicInteraction` or `ChooseHadronicInteraction`: with overlapping ranges they call `G4UniformRand`, which shifts the serial random stream |
| Random numbers | The probe must draw no random numbers (otherwise it breaks the bit-identity of §2 rule 13); a test confirms the random-engine state is the same before and after the probe |
| Run manager | The actual run-manager type (with `MTOnly`/`SerialOnly`, as `layered_sim` uses, the environment variable `G4RUN_MANAGER_TYPE` is ignored, so the actual type is recorded rather than the variable), `seedOncePerCommunication`; SubEvt or a non-zero seed mode reports a gap |
| Other | `G4UserLimits`, biasing (with biasing, flag "events may share state") |
| Datasets | Paths and content hashes computed once in the build record; the probe refers to it via `environment_ref` |
| Field | Field managers are per thread; a declared field the master cannot see is marked `source: declared` (`layered_sim` has no field) |
| Paths | Written through `tilde()` |
| Output location | `effective_config.json`, hash written into the run record; content also placed in `extension.simulation.effective_config` |

- Rules and the model assignment of variations read the probe first and fall back to the declaration only when the probe cannot be read, outputting `source: probe | declared`; when both exist and disagree, it is an error.
- Test trigger: a UI command that exists only in the test build calls the probe after `/run/initialize` and before the first `BeamOn`; it must write `recorded: false`.

### A2.5 Column map (`simulation-columns/1`)

- `layered_sim` writes `column_map.json` for each run, its hash written into the run record.
- Per column: semantic name, actual column name, unit, operational definition, file it lives in (`csv` or `summary`); with `column_map_version`.
- Only declarative operations are allowed (rename, unit conversion, sum, filter); a transformation that needs computation is a separate, recorded step.

### A2.6 The study layer reads only boundary artifacts (D9)

| Location | Change |
|---|---|
| `cmd_summarize`, benchmarks | Read only the summary (and the column map's semantic names); no CSV column names |
| `derived()` and the thin-layer rule | Minimum thickness from the effective config's geometry tree; records from before A2 (no effective config) still use spec/1's `geometry.layers` |
| Configuration and target hash | Records from A2 use `tree-v1`; A1 records keep `spec-v1`; comparison only between the same `hash_scheme`; `dependencies.py` re-derives by the record's `hash_scheme` |
| Consistency check | `geant4_run.py` (not `layered_sim`, to avoid a second implementation of `spec-v1` in C++) checks after every `layered_sim` run that the configuration derived via `spec-v1` and the one derived via `tree-v1` give the same decision; exit 2 if not |
| `geant4_verify.py` | Volume counts and material budget from the geometry tree |

### A2.7 Schema keywords

- Extend `contracts/schema.py` with `maxItems`, `maximum`, `exclusiveMaximum` (already used by `layered_sim`'s schemas; also needed by task B's `element_sim`). Update `SUPPORTED_KEYWORDS`, and make `tests/contracts/test_schema_keywords.py` also scan the adapter's schemas.
- Contracts not bumped (no contract schema uses the new keywords).
- `validate_spec()` in `geant4_run.py` stays unchanged (out of scope).

### A2.8 Adapter-change process

| Item | Content |
|---|---|
| Version | 0.1.0 → 0.2.0 |
| `adapter.json` | `assets` gains `g4sim/`, the summary and column-map schemas, `summary_from_csv.py`; update `purpose`; `status` stays `demonstrated-on-synthetic-data` |
| `SIM_SOURCES` | Add the `g4sim/` files so that `sources_sha256` covers everything |
| G5 | Statement "written from the Geant4 API; no example code copied or adapted", confirmed by the reviewer in the VALIDATION entry |
| Tests | The assets check in `tests/adapters/test_geant4.py`; offline tests; live tests with `HEP_GEANT4_LIVE_TEST=1`; ctest of `SimSummary.hh` (optional) |
| Docs | The Geant4 row of `docs/capability-matrix.md`; `geant4-study-protocol.md` (boundary artifacts, blocks, validation classes) |

### A2.9 Tests and oracle

- From the A2.3 test dump, recompute the summary with the A1.5 Python producer and compare with the one written by `layered_sim`: integers identical, floating-point relative difference ≤ 1e-12.
- Under `per-event`, the same logical run with 1, 2, 4 jobs and 1, 2, 4 threads: identical event content (dumps bit-identical), summary integers identical, floating-point relative difference ≤ 1e-12.

### A2.10 A2 acceptance

- [ ] Regression check: J14's existing specs produce a CSV bit-identical to the pre-A2 one on the same host; the random-engine state is the same before and after the probe.
- [ ] H in `SimHash.hh` equals Python's H on the test vectors; the hex format of `SimProbe.hh` equals Python's `float.hex()`.
- [ ] Under `per-event`, if `GeneratePrimaries` draws random numbers (a random gun in a test), event content still does not depend on how the run is split into jobs.
- [ ] Both tests of A2.9 pass.
- [ ] The J14 specs rerun in E2 for the regression check (all 18, still `stream`) have new run records that all carry an effective config, and `tree-v1` and `spec-v1` give the same decisions on them; a deliberate inconsistency is caught; a run with `recorded: false` cannot upgrade. The committed J14 records stay at their A1 version (`spec-v1`) and are not regenerated in A2.
- [ ] The thin-layer rule takes the minimum thickness from the effective config, with the same conclusion for J14 as in A1.
- [ ] The study layer's production code reads no CSV column names (confirmed by a test).
- [ ] Event weight ≠ 1 gives exit 2.
- [ ] J14's offline replay still meets §4.2.
- [ ] VALIDATION GEANT4-SUMMARY; CHANGELOG; release manifest.

---

## 7. Statistics summary

| Item | Spec | Work item |
|---|---|---|
| Blocks | K ≥ 16 blocks by event number, B events each; declared in advance | A1.5, A1.6 |
| SE | Batch means, sd(θ_b)/√K, t_{K−1} | A1.6 |
| Low counts | Any block 0 or total < 100: Clopper–Pearson, Garwood, conditional binomial; the gate decides on interval endpoints | A1.6, A1.8 |
| MPV | Mean of three-point interpolations of block histograms; bias toy 95 % upper bound ≤ tol/10; per-execution check ≤ tol/5 + 2·SE | A1.7 |
| Quantiles | Linear interpolation within the histogram; bin < tol/10; incomplete on overflow | A1.6 |
| Convergence gate | IUT; relative or absolute difference (`tolerance_mode`); se_diff; Welch ν; per-point se target tol/(4√2); pass needs both points to meet the target | A1.8 |
| Two-stage | f = F₀.₉₀(K−1, K_trial−1); target missed → incomplete, no top-up; about 19 % of point pairs incomplete, all n runs meet the target with probability about 0.9ⁿ | A1.9 |
| Negative control | Shift in the observable; DL = tol + \|rel\| + t_{0.977}(ν)·se_rel; both directions | A1.10 |
| Seeds | S = H(study_id, role, point_id); job seeds H(S, e, 0/1); event seeds H(S, i, 0/1); A1 `stream`, new studies `per-event` from A2 | A1.4, A2.2 |
| Evidence correlation | `evidence_overlap` | A1.11 |
| Reproducibility | Same decisions, numbers within relative 1e-9, near-threshold flag | §4.2 |
| New block versions | `probe_version`, `column_map_version`, `evidence_overlap_version`, `summary_version` | A1.5, A1.11, A2.4, A2.5 |

---

## 8. Contracts and versions

| Object | Location | Version |
|---|---|---|
| Benchmark table (class, grade, kind, scope dimensions), scope comparison, configuration and isolation, `hash_scheme`, `extension.simulation` | `contracts/validate.py`, `contracts/dependencies.py`, `ext_computational_run.json` | C1 (minor, gated, sci-fix) |
| Schema-keyword extension | `contracts/schema.py` | not bumped |
| `simulation-summary/1`, `simulation-columns/1`, effective config | adapter | adapter 0.2.0 (the first summary schema is added in A1 with the Python producer) |
| `g4sim`, the `seeding` option | adapter (C++) | adapter 0.2.0 |
| `GRADES`, kind and configuration output | hep-detector | with the plugin version |

The owner of the computational-run schema is hep-computing; this task only adds the optional `simulation` property (needs its agreement). C2 belongs to task B.

---

## 9. Checks at the end of every stage

- `run_all_checks.py` (including the CI lock environment)
- `check_layering.py`, `check_relocation.py`, `check_ownership.py`, `check_packaging.py`
- `measure_entrypoints.py` (quick load ≤ 25,600 bytes)
- `reference_inventory.py --check`, `capability_map.py --check`, `check_routing_static.py`
- Every study record passes `validate.py --strict` and `dependencies.py`
- `tests.adapters.test_geant4` offline and live (`HEP_GEANT4_LIVE_TEST=1`)
- `tests/examples/test_geant4_thin_silicon.py` (replay decisions meet §4.2)
- `python3 -m unittest discover -s tests/contracts -t .` (run as a whole)
- `tools/scifix_advisories.py check` (A1)
- A new problem run by an agent that did not take part in writing, with pass conditions
- The Markdown of each stage reviewed with 0.22.0's `review.py` (`--lens-model design=<strongest model>`, `--filter-model`); its record is advisory only and, per O04/O14, does not replace the human G5 confirmation
- VALIDATION entries, CHANGELOG, release manifest

---

## 10. Not done and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| spec/2, spec conversion, dual-format accessor, bit-identical comparison gate | Not done | `layered_sim` keeps its format; new features go into task B's `element_sim` |
| Integer quantization, 128-bit integers, bit-identical statistics | Not done | Reproducibility means same decisions |
| `simstat`, a `simcore` not linked to Geant4 | Not done | Inference stays in Python |
| Several independent processes per evidence run | Not done | Blocks are within the run |
| `uses-validated-physics` label | Not done | The hash is both too strict and too loose; it would bypass the scope check |
| Adaptive stopping on SE, refined scans as evidence, rerunning controls with another seed | Not done | Optional stopping |
| New core validators, rewriting the tracking and multiple-scattering formulas | Not done | Reuse existing tools |
| Contracts 4.0 | Not done | New optional blocks and gated rules are minor |
| Python bindings | Not done | The user chose separate executables exchanging JSON/CSV |
| Replacing `validate_spec()` | Not done | Out of scope |
| Weighted accumulation and biasing rules | Deferred | The first study that uses biasing |
| `physics_config_comparison` | Deferred | A study that compares physics settings; then differences must obtain `effective_config` through `evidence_records`, and always fail when it is missing |
| Rule version ranges, probes for several Geant4 versions | Deferred | Supporting a second Geant4 version (task B's regression class uses it first) |
| Benchmark registry | Deferred | Replaced by the contract table and the enum consistency test |
| `inspect` and Linux environments | Deferred | Needed to run on CVMFS or LCG |
| ReferenceMaterial contract | Deferred | The first reference benchmark on non-slab geometry |
| Generalized `scoped_upgrade` | Deferred | A second study type needs upgrades |
| J15-related items | In task B | See task B §8 |

---

## 11. Decisions for the maintainer and residual risks

**To decide:**
1. Classification of C1 (proposed: minor plus sci-fix).
2. How to confirm the G5 statement "no example code copied".
3. hep-computing's agreement to the `simulation` property.
4. Two-stage factor F₀.₉₀ (about 10 % miss) or F₀.₉₅ (about 5 %, about 22 % more events); and what to do if regenerated J14 loses `validated-in-scope` by chance through a missed target (A1.9).
5. Live re-recording of J14's scan and variation runs in A1, and the cap on `recorded/` size.
6. The switch threshold for exact intervals (default: any block 0 or total < 100).

**Residual risks:**
1. J14's detection limits may change because of block batch means, t quantiles and controls in observable units; the controls need redesign.
2. Block batch means have O(1/B) bias for ratios, quantiles and modes of skewed distributions, which does not shrink with K; the coverage toys allow ±0.02, and B is increased if needed.
3. Block independence fails when events share state; the probe flags biasing, and in doubt use several independent logical runs.
4. With tolerance comparisons, near-threshold decisions may differ between platforms; handled by the margin flag and "the CI platform rules".
5. MT merging of a custom `G4VAccumulable` must be confirmed by tests.
6. The probe assumes workers and master have the same settings; if thread-local differences appear, switch to per-thread dumps.
7. A setup-matched target hash only proves the configuration is the same, not that it is the one in the paper; a reviewer must still check.
8. Quick load has only 931 bytes left.
9. Effort: the prototype estimated about 8–12 working days for the contract part of A1, plus Geant4 run time; the statistics part and A2 are not estimated.

---

## 12. Suggested order of work

**A1**
1. Pre-start checks (§0); apply `prototype/phase1-core.patch` and complete what A1.1–A1.3 lack.
2. Fix D10 first (A1.12); from then on always run `python3 -m unittest discover -s tests/contracts -t .` as a whole.
3. A1.1 → A1.2 → A1.3 (contracts and `dependencies.py`), with contract tests.
4. The A1.5 Python producer and schema; produce summaries offline from J14's 5 per-event CSVs.
5. Statistics of A1.6–A1.10 (now reading summaries), with toy tests (gate, coverage, MPV bias, detection limit).
6. Seeds of A1.4 and the rest of A1.11 and A1.12 (protocol, enums, `simulation` property).
7. Re-record J14's scans, variations and negative controls live in E2 (A1.13); regenerate J14 records and run `--strict`.
8. A1.14: ledger, advisories, parent records, VALIDATION, CHANGELOG, release manifest; run the checks of §9.

**A2 (after A1 is merged)**
1. `g4sim/SimSummary.hh` and its ctest (no Geant4), with the A1.5 Python producer as oracle.
2. `SimSeed.hh` and `run.seeding`; `SimProbe.hh` and the geometry tree.
3. `layered_sim` integration: summary, effective config, column map, test dump; confirm J14's CSV is bit-unchanged.
4. Study layer reads boundary artifacts (A2.6); schema keywords (A2.7).
5. Adapter-change items of A2.8; run live tests in E2; tick all of A2.10; run the checks of §9.

---

## Appendix A: Numbers

Computed by `gate_operating_characteristics.py` (needs numpy and scipy; a design aid only).

- F₀.₉₀(15,15) = 1.972; F₀.₉₅(15,15) = 2.403; F₀.₉₀(31,31) = 1.594.
- t₀.₉₅(30) = 1.697, t₀.₉₅(15) = 1.753, t₀.₉₇₅(15) = 2.131; fail quantile for m = 30, t_{1−0.05/30}(30) = 3.189.
- Welch ν (K = 16): 30 at variance ratio 1, 27 at 2, 22.1 at 4, 18.0 at 10.
- Mean se_diff under the two-stage design ≈ 0.189 tol (target 0.25 tol); probability that at least one point of a pair misses its target 0.190.
- Detection-limit power (the caught definition of A1.10) is near 0.977 (the reviewer's calculation about 0.9785), so acceptance uses 0.977 − 3σ_MC.

## Appendix B: Baseline values (`9f08796`)

| Item | Value |
|---|---|
| `CONTRACTS_VERSION` | 3.5.0 |
| `GEANT4_UPGRADE_FROM` | 3.1.0 (line 346) |
| J14 study record | contract 3.5.0, with `code_paths`, `code_tags` |
| J14 world material | `G4_Galactic` |
| J14 `recorded/` | 2.6 MB; `events/` 5 reduced CSVs (`event`, `primary_eloss_MeV`, `edep_Si_MeV`, `primary_fate`, `primary_end_process`); `runs/` 18 run records (5 with per-event CSV; 13 scan, variation and scenario runs with only single-value summaries in `summaries/`) |
| Advisory | latest SFA-2026-037 |
| hep-detector | quick load 24,669 / 25,600 bytes; description 1,016 / 1,024 characters (`measure_entrypoints.py`); `DetectorScriptCount` 21 |
| `GRADES` | `longitudinal-profile: "reference"` (lines 92–94); the study spec's grade enum is reference, sanity, interface |
| `ext_computational_run.json` | Does not declare `simulation`; J14's run records already carry `extension.simulation` |
| J14 seeds | The first seed of the 5 non-re-recorded runs is 1401 or 1402 |
| `SUPPORTED_KEYWORDS` | no maxItems, maximum, exclusiveMaximum |
| `check_packaging.py` MAX_BYTES | 2 MiB |
| Geant4 build | `GEANT4_USE_GDML: OFF`; `layered_sim` MT uses `G4RunManagerType::MTOnly` |
| Shared stanza point 5 | says "3.1.0 upgrade rule" (unchanged) |
| Journey table | J1–J14 |
| Stage 1 prototype | 55 tests pass; J14's 7 study records pass `--strict`; D10 reproduced on clean main (5 errors) |

## Appendix C: Sources

The experiments and frameworks the design refers to (ATLAS, CMS, ALICE, Key4hep, Allpix², geant-val, Belle II) are in [`architecture.en.md`](architecture.en.md) §14. Relevant Geant4 11.4.3 source files: `G4RunManager.cc`, `G4MTRunManager.cc`, `G4WorkerRunManager.cc`, `G4EmParameters.cc`, `G4ProductionCutsTable`, `G4HadronicProcess.hh`, `G4AccumulableManager`, `G4VAccumulable`, `G4PhysicalVolumeStore`, `G4LogicalVolume`, `G4NistMaterialBuilder.cc`, `G4PVPlacement`.

## Appendix D: Version history

| Version | Content |
|---|---|
| Before 2026-10-21 | Three rounds of independent review, two checks against 0.21.0 and `9f08796`, stage 1 prototype |
| 2026-10-22 | Language split, per-event ROOT files, task split, organized as an implementation spec; soundness and generality reviews; third deep check (25 items); redesign referencing real experiments (`architecture.md`) |
| 2026-10-22 | Rewritten for the redesigned architecture: A1 (contracts and statistics, block batch means, Python summary producer, offline recomputation of J14), A2 (`g4common`, per-event seeds, three boundary artifacts); spec/2, `simcore` and quantization removed |
| **2026-10-23 (this version)** | **Fixes after independent review: two-stage operating characteristics recomputed (the old script double-counted the trial χ²); pass needs both points to meet the target; `tolerance_mode`; grade is class, `longitudinal-profile` becomes setup-matched; top-level `observables` declaration and selection; `weight` column may be absent; byte-level definition of H, job seeds and legacy runs; caught definition and toy threshold; reseeding at the start of `GeneratePrimaries`; the probe draws no random numbers; `SimHash.hh` and `MiniJson.hh` in the shared directory; shared directory renamed `g4sim` (formerly `g4common`); other small fixes** |
