# hep-research Geant4 study architecture (consolidated)

> Status: architecture proposal consolidating all discussion from 2026-10-21 to 2026-10-22; awaiting the user's confirmation of the proposals in section 11.2 and the maintainer's decisions in section 11.3
> Supersedes: `architecture-revision.md` (re-evaluation and generality assessment, now merged here). `task-a-core.md` and `task-b-j15.md` are the implementation specs of the previous architecture and are rewritten per section 12 once this document is approved
> Baseline: hep-research `main` at `9f08796` (0.23.0 plus unreleased changes), contracts 3.5.0, adapter geant4 0.1.0, Geant4 11.4.3
> Date: 2026-10-22
> Language: English translation of [`architecture.md`](architecture.md) (Traditional Chinese original), same content

---

## 0. Summary

**The problem.** hep-research's Geant4 study workflow has two kinds of problem. The first is correctness: results can be wrongly labelled `validated-in-scope`, because the scope check skips the observable, the record declares its own benchmark grade, and the statistical rules have holes (D1–D10, §1). The second is structure: the study layer is tied to `layered_sim`'s column names and slab geometry, and cannot take other backends, other geometries or other kinds of study.

**The core of the architecture (five sentences):**
1. **Two planes.** Per-event processing is in C++ (the data plane); inference on tens to hundreds of numbers per run, decisions, records and contracts are in Python (the control plane).
2. **One boundary artifact.** The data plane accumulates observables into mergeable sufficient statistics where the events happen and writes them as a `run summary` (integer accumulation, weighted, with its own merge rules; a few kB per chunk). Python reads only summaries.
3. **The backend describes itself.** Any backend that delivers a run summary, an observable map (the column map) and its actual settings (the effective config, including the actual geometry tree) reaches the gates, benchmarks and labels.
4. **Upgrade-relevant facts are re-derived by the contract from evidence.** Grade, kind, scope dimensions, configuration and target hash are never self-declared.
5. **One variance method.** Every evidence run is split into K ≥ 16 independent chunks and every SE is estimated by batch means; for small counts, exact intervals.

**Stages:**

| Stage | Content | Version |
|---|---|---|
| A1 | correctness fixes (sci-fix), staying in Python: contracts, statistical rules, generalized definitions of scope and isolation | contracts C1 |
| A2a | spec/2, `layered_sim convert`, probe (engine-independent envelope, actual geometry tree), dual-format accessor | adapter 0.2.0 |
| A2b | run summary and backend interface: weighted integer accumulators, Python reads summaries, J14 replays from summaries | adapter 0.3.0 |
| B0 | per-event ROOT files and `simroot` | adapter 0.4.0 |
| B1 | J15 minimal spectrometer: field, plane crossings, `simreco`, `verification`, C2 | adapter 0.5.0, contracts C2 |

A1, A2a and A2b are "task A"; B0 and B1 are "task B", which starts after task A is merged. Each stage merges on its own.

---

## 1. Background

### 1.1 Confirmed defects (`9f08796`)

| # | Defect | Location | Consequence |
|---|---|---|---|
| D1 | the scope check does not compare the observable; a dimension missing from the declared scope is unconstrained | `validate.py` `_scope_inside()` (from line 349); `check_geant4_study.py` `scope_within()` (lines 482–493) | a study that passed an MPV benchmark can label other observables `validated-in-scope` |
| D2 | the record declares its own benchmark grade | `_study_upgrade` (line 395; filter at line 419) | writing `"grade": "reference"` upgrades |
| D3 | negative controls compare different units and test one sign only | `geant4_benchmarks.py` line 678 | the detection limit is not shown on the observable |
| D4 | the convergence gate has no equivalence test | `check_geant4_study.py` line 359 | passes about 50 % of the time when the true difference equals the tolerance |
| D5 | MPV SE from the bootstrap | `geant4_benchmarks.py` line 369 | inconsistent variance estimate |
| D6 | the stopping rule does not forbid topping up after results | protocol section 4 | optional-stopping bias |
| D7 | evidence correlation not disclosed | J14's nominal run is shared by several decisions | treated as independent evidence |
| D8 | the study-spec benchmark enum lacks two entries | `geant4-study-spec.schema.json` | consistency gap (no runtime effect) |
| D9 | the study layer is tied to layered_sim's data format | `derived()`, `summarize` and benchmarks read fixed column names | no other backend can reach it |
| D10 | test-order dependence | `tests/contracts` run as a whole has 5 errors | errors depend on execution order |

### 1.2 How this architecture came about

| When | Event | Effect on the architecture |
|---|---|---|
| before 2026-10-21 | three rounds of independent review (7 reports), checks against 0.21.0 and `9f08796`, a phase-1 prototype | the contracts and statistical rules took shape (kept in §6 and §5) |
| 2026-10-22 | user decision: core code in C++, Python only as the interface; separate executables exchanging JSON/CSV | the first version also moved run-level statistics to C++ (`simstat`) |
| 2026-10-22 | user decision: detailed per-event information stored in ROOT files | ROOT files and `simroot` added |
| 2026-10-22 | user decision: J15 split from the rest into a second task, done later | task A and task B |
| 2026-10-22 | soundness assessment | the boundary is in the wrong place (P1–P7 in §1.3) |
| 2026-10-22 | generality assessment | ten places that lock generality in (G1–G10 in §1.3) |

### 1.3 Problems of the previous architecture

**Soundness (P):**

| # | Problem |
|---|---|
| P1 | moving run-level statistics (`mpv()` and `bootstrap()` about 7 lines each; 2.45 MB of data) to C++ gains no speed but makes J14's offline replay need a compiler; across compilers and architectures (FMA contraction on aarch64, say) bit-identical replay may fail; the Python oracle still has to be maintained |
| P2 | phase 2 bundles spec/2, conversion, scorers, probe, column map, the statistics port, ROOT and `simroot`; ROOT has no consumer in task A |
| P3 | the finite-sample bias of the sub-run MPV has no limit |
| P4 | two SE methods (sub-runs and a counter-hash bootstrap) and two two-stage factors |
| P5 | the backend interface is a column map plus a per-event CSV, so a new backend must still produce a per-event table |
| P6 | chunk values are merged by the partition through column-name tokens (`mpv` was once silently summed) |
| P7 | task A needs a Geant4-free C++ project and a new required CI job |

**Generality (G):**

| # | What locks generality in |
|---|---|
| G1 | configuration and the target hash can only be derived from the spec's slab list |
| G2 | scope dimensions hard-wired as particle, material, energy, thickness (`validate.py` lines 350–355) |
| G3 | a field makes isolated impossible |
| G4 | no weights in accumulation (the CSV has a `weight` column, unused downstream) |
| G5 | one dimension per observable; no per-event combinations or event selection |
| G6 | only one SE method; it fails for rare counts |
| G7 | only a `gun` source |
| G8 | `effective_config` is a Geant4-specific format |
| G9 | the derived-simulation marker has one level |
| G10 | the number of chunks is fixed at 16 |

P1, P4, P5 and P6 share one root cause: **the boundary is in the wrong place**, since Python receives per-event data. G1–G10 share another: **the interfaces follow the first use case (slabs, a gun, Geant4)**. This architecture answers them by "moving the boundary to sufficient statistics" and "extensible interfaces from the start, implementing only what is needed now".

---

## 2. Goals, constraints and principles

### 2.1 Goals

| Goal | Guaranteed by |
|---|---|
| `validated-in-scope` cannot be obtained wrongly | facts the contract re-derives from evidence (§6) |
| Numbers are reproducible and reviewable | small, hashed, integer-exact intermediate artifacts; replay independent of the machine (§4.2) |
| The study layer is not tied to one backend, geometry or kind of study | a backend interface made of three boundary artifacts (§4.6) |
| Demonstrate a field, several subsystems and reconstruction | J15 (B1) |

### 2.2 Constraints

- Python uses only the standard library.
- G5 licence boundary: Python exchanges only JSON and CSV with separate executables; no Geant4 example code is copied.
- Layering: skill scripts and adapters import only `core` and `contracts`; no experiment names in `skills/` or `contracts/`.
- Statuses and exit codes (`core/status.py`): 0 ok, 1 a negative verdict, 2 `rejected`, 3 `incomplete`.
- Files ≤ 2 MiB; hep-detector quick load ≤ 25,600 bytes (24,669 now), description ≤ 1,024 characters (1,018 now).
- J14's offline replay must always run and reproduce the committed output bit for bit.

### 2.3 Principles

1. **Correctness before extension.** Nothing new is merged before A1.
2. **The boundary is at sufficient statistics.** Code that processes per-event data is in the data plane (C++); code that processes run summaries is in the control plane (Python). One production implementation per quantity; one in the other language may exist only in tests, as an oracle.
3. **Trust the actual state; declarations are only the fallback.** Geometry, field and physics settings are taken from the probe; declarations alone are marked `source: declared` and cannot be used to upgrade.
4. **Upgrade-relevant facts are decided by the contract.** Grade, kind, scope dimensions, configuration and target hash are never self-declared by a record.
5. **The validation grade follows the nature of the reference.** A reference that is an exact consequence of the inputs gives verification (no upgrade); only a physics model Geant4 approximates, or a published measurement, can be reference or sanity.
6. **Stopping rules, grids and chunk counts of evidence are declared in advance.** Topping up, refining and redoing controls are never decided from results.
7. **Exact and order-independent.** Values merged across threads, chunks or machines are always accumulated as integers.
8. **Extensible interfaces, implementation only as needed.** No general expression language, no plug-in system.
9. **Look for an existing implementation first.** Reuse `contracts/schema.py`, `tracker_resolution.py`, `multiple_scattering.py`; an oracle never imports the module it tests.
10. **Minimal change.**

---

## 3. Architecture overview

```
Control plane (Python, standard library)
  hep-detector      rules, reference formulas, inference (MPV, batch means, exact intervals, IUT, negative controls), decisions, labels
  adapters/geant4   spec validation, build, run, chunk, records (trace.provenance()), simulated tables
  core              dual-format geometry accessor, trace, status
  contracts         grade and dimension table, scope, configuration and isolation (C1); verification, transitive derived-simulation marker (C2)
        ▲
        │  boundary artifacts (JSON; small, committable, hashable)
        │    run summary          layered_sim.summary/1    (§4.2)
        │    column map           layered_sim.output/2     (§4.4)
        │    effective config     engine-independent envelope + geometry tree (§4.3)
        │
Data plane (C++)
  SimSummary.hh     standard-library-only header: weighted integer accumulators, merging, JSON writer (shared by layered_sim, simreco, user applications)
  layered_sim       links Geant4: simulation, scorers, probe, accumulates observables at the end of each event; per-event CSV (summary);
                    `convert` subcommand (spec/1 → spec/2); (B0) per-event ROOT files; (B1) field and plane crossings
  simroot           (B0) links only Geant4's analysis library: info / dump / hash of ROOT files
  simreco           (B1) no Geant4: per-event digitization and reconstruction, writes run summaries and per-event results
  other backends    a user's Geant4 application (including SimSummary.hh) or another engine, delivering the same three boundary artifacts
```

| Component | Language | Stage | Depends on |
|---|---|---|---|
| contract changes | Python | A1 (C1), B1 (C2) | — |
| hep-detector inference and decisions | Python | A1; reads summaries from A2b | — |
| `core/geometry/layered.py` | Python | A2a | — |
| `layered_sim` (with `convert` and the probe) | C++ | A2a | Geant4 |
| `SimSummary.hh` | C++ | A2b | standard library only |
| `simroot` | C++ | B0 | Geant4 analysis (g4tools) |
| `simreco` | C++ | B1 | standard library, `SimSummary.hh`, `MiniJson.hh` |

---

## 4. Interfaces

### 4.1 spec/2

| Block | Content | Stage |
|---|---|---|
| coordinates | world centre as origin, stacking axis x, mm; `at_mm` is an element's front face in world coordinates; one level of nesting | A2a |
| `elements`, `materials` | elements and materials (mixtures included, order kept) | A2a |
| `field` | reserved in A2a (a non-empty block is rejected with exit 2); B1 implements a uniform field and the accuracy parameters | A2a / B1 |
| `source` | distinguished by `type`: `gun` (A2a); `gps` and `event-file` defined as interfaces only (§9) | A2a |
| `output.observables` | declared observables: source column, quantization step q, bins, thresholds; A2b implements single columns, combinations and selections are interfaces only (§9) | A2b |
| `output.event_file` | `level`: `none` (default), `summary`, `hits`, `crossings` | B0 / B1 |
| `run` | threads, seeds, event count | A2a |

spec/1 is converted to spec/2 by `layered_sim convert`: the same translation unit keeps the floating-point operation order of the old `Detector.cc`, written as `%.17g`. On the same host, old and new must be bit-identical for TestEm3, the TestEm5 mirror and J14 (CSV and hex-float dumps of every placement). The schema uses only keywords supported by `contracts/schema.py` (A2a adds `maxItems`, `maximum`, `exclusiveMaximum`, with no contracts version change); cross-field rules stay in Python's `cross_field_checks()`.

### 4.2 Run summary (`layered_sim.summary/1`)

One JSON per run (per chunk).

| Field | Content |
|---|---|
| `run` | sha256 of spec and effective spec, seeds, chunk index, event count, `summary_version`, the quantization steps |
| `observables[]` | per declared observable: semantic name (matching the column map), unit, q, accumulators |
| Accumulators | `n`, `Σw`, `Σw²`, `Σw·x`, `Σw·x²`, `min`, `max`, `hist` (declared fixed bins, Σw and count per bin; overflow and underflow separate), `count_if[]` (Σw and count above declared thresholds); from B1 `profile` and 2D `hist` may appear (§9) |
| Number form | every sum accumulated as int128 of round(value / quantization step), written as a decimal string; `n_eff = (Σw)²/Σw²` is computed by Python |
| `merge` | each accumulator's merge rule: `sum`, `min`, `max`, `hist`; nothing guessed from names |
| `overflow` | true if any accumulator overflowed; the run is then incomplete (exit 3), with the reason recorded |

**Properties:**
- **Exact and order-independent.** Integer addition is commutative and associative, so results do not depend on thread count, worker merge order, compiler or architecture. Under MT, a custom `G4VAccumulable` merges through `G4AccumulableManager::Merge()`.
- **Bounded quantization error.** At most q/2 per event; Python checks that the bound n·q/2 is far below every tolerance. Default steps: energy 1 eV, length 1 nm, time 1 fs, weight 2⁻²⁰.
- **Small.** A J14 chunk is a few kB and can be committed; J14's offline replay runs on the committed summaries, staying pure Python and bit-identical.
- **Recomputable.** Python can recompute a summary from a committed per-event CSV under the same declarations (bit-identical after quantization), as the oracle in tests.

### 4.3 Effective config

```
{ "engine": "geant4", "engine_version": "11.4.3", "probe_version": "...",
  "source": "probe" | "declared", "config_sha256": "...",
  "geometry": { "tree": [...], "tree_sha256": "..." },
  "sections": { "geant4": { ... } } }
```

| Part | Content |
|---|---|
| envelope | engine-independent; rules are chosen as a rule pack by `engine` (only Geant4's `G4R-*` today) |
| `geometry.tree` | a walk of `G4PhysicalVolumeStore`: each placement's name, copy number, solid type and parameters, material (composition and density), transform, mother, attached field manager and its parameters; numbers as hex floats |
| `sections.geant4` | the full text of `G4EmParameters::StreamInfo` plus parsed fields; per-couple cuts and energy thresholds; energy ranges per process and model; run-manager type and seed mode; `G4UserLimits`, biasing, dataset paths and content hashes |
| timing | master `BeginOfRunAction`, in `G4State_GeomClosed` with more than 0 couples; otherwise `recorded: false` (layered_sim still exits 0); master only, stating "workers assumed identical" |
| paths | written through `tilde()` |

Rule and variation model assignments read the probe first; declarations alone are written with `source: declared`; if both exist and disagree, it is an error.

### 4.4 Column map (`layered_sim.output/2`)

For each observable and output column: semantic name, actual column name, unit, operational definition, and the file it lives in (`csv`, which ntuple of `root`, or `summary`); with `column_map_version`. Only declarative operations (rename, unit, sum, filter) are allowed; a conversion that computes something must be a separate recorded step.

### 4.5 Per-event files (B0)

| Item | Rule |
|---|---|
| per-event CSV | the summary table (primary truth, total deposit per subsystem); unchanged from A2a; J14's bit-identical comparison is on it |
| ROOT file | written by `layered_sim` through `G4AnalysisManager` (g4tools, no ROOT installation); under MT `SetNtupleMerging(true)` merges into one file; flat ntuples, scalar columns only, every row keyed; layout `layered_sim.events/1` with ntuples `run`, `events`, `deposits`, `hits`; B1 adds `crossings` (`events/2`) |
| row order | not fixed after merging; readers always sort by key |
| hashes | file bytes include the write time and are not bit-identical; the run record keeps the file sha256 (integrity) and the `content_sha256` from `simroot hash` (comparison and provenance); under MT the master draws every event's seeds in advance, so different thread counts should give the same `content_sha256` |
| `simroot` | `info`, `dump` (CSV after sorting by key), `hash`; links only Geant4's analysis library (`G4RootAnalysisReader`), no run manager |
| readers | Python and `simreco` never parse ROOT; they go through `simroot dump`; researchers may use ROOT or uproot themselves |
| size | not committed; the run record keeps the path, hashes, row count per ntuple and size; `hits` has an event-count limit (`max_events_hits`, default 100) |
| trial | B0 starts with one day confirming that `G4RootAnalysisReader` reads MT-merged, compressed files and string columns; if not, `simroot` reads only flat scalar columns and the strings move to a JSON side file |

### 4.6 Backend interface

To reach the gates, benchmarks and labels, a backend delivers, for a spec/2 (or its own input, with a hash):

1. one run summary per chunk (§4.2);
2. a column map (§4.4);
3. an effective config (§4.3). With declarations only (`source: declared`), the study can still run and be published but cannot upgrade.

A user's own Geant4 application meets this by including `SimSummary.hh` and the probe header. A2b's acceptance includes a "second backend": not `layered_sim`, delivering only these three things, and it must pass J14's gates and benchmarks.

---

## 5. Statistical methods

| Item | Rule |
|---|---|
| chunks | every evidence run is K independent chunks, K declared in advance with a minimum of 16; seeds `H(study_id, role, point_id, k)` mapped to an integer in [1, 2³¹); layered_sim's second seed is `start + 1`; no seed pair repeats across a study's run records |
| estimators | θ_k from each chunk's summary (mean, fraction, ratio, quantile, mode); report θ̄ = the mean |
| SE (default) | batch means: SE = sd(θ_k)/√K, quantiles t_{K−1}; Welch's approximation for a difference of two estimates (about ν = 30 at K = 16). Correlations between observables are handled automatically |
| SE (small counts) | counting estimators switch to exact intervals on the merged accumulators (Garwood for Poisson, Clopper–Pearson for binomial) when any chunk is 0 or the total is < 100; the threshold can be declared |
| MPV | per chunk, take the highest bin of the histogram and interpolate the mode with a three-point parabola through it and its neighbours; report the mean of the K modes |
| MPV bias limit | at the declared N/K and bin width, a Landau–Vavilov toy shows \|E[θ̄] − true mode\| ≤ tol/10; otherwise increase the events per chunk or change the bins before the first evidence run |
| quantiles | linear interpolation within a histogram bin; the bin width must be below 1/10 of the observable's tolerance |
| full-sample values | means and fractions also from the merged accumulators; the difference from θ̄ goes into the record as a diagnostic |
| convergence gate | intersection-union test: pass \|diff\| + q_pass·se ≤ tol, fail \|diff\| − q_fail·se > tol, otherwise unresolved; q_pass = t₀.₉₅(ν), q_fail = t_{1−α/m}(ν), with m the number of (parameter × observable) pairs; event counts set in advance so that the se of the difference ≤ tol/4 |
| reporting | unresolved and missed targets are `incomplete` (exit 3) and the label stays `unvalidated`; only fail is `failed` (exit 1) |
| two-stage event count | N = ceil(N_trial·(SE_trial/target)²·f), f = F₀.₉₀(K−1, K−1) (≈ 1.97 at K = 16); an evidence run that misses its target is not topped up |
| negative controls | the decision quantity is the shift in the observable, (control − nominal)/reference; at the detection limit: caught and \|shift\| ≤ 1.1 × DL; inject both signs, otherwise restrict the claim to one sign |
| stopping rule | stopping rule, scan grid, K and the handling of unresolved results written into the study spec before the first evidence run |
| evidence correlation | `extension.study.evidence_overlap` lists runs shared by several decisions |

Operating characteristics (se = tol/4, α = 0.05): at a true difference of 0, pass 0.981; at tol/2, 0.639; at tol, 0.050; at 2 tol, fail 0.991 (m = 1), 0.857 (m = 30). At tol/2 only about 64 % pass, and the documentation states the expected rate of incomplete results.

Dropped: the counter-hash bootstrap, globally unique event keys and their duplicate checks, the second two-stage factor (1.2).

---

## 6. Contracts

### 6.1 Benchmark table (C1)

`contracts/validate.py` carries its own table, and `_study_upgrade` takes grade, kinds and scope dimensions only from it:

| Benchmark | Grade | Supported kinds | Scope dimensions |
|---|---|---|---|
| `stopping-power` | reference | `stopping-power` | particle, material, energy, thickness |
| `range` | reference | `range` | particle, material, energy, thickness |
| `thin-layer-mpv` | reference | `most-probable-value` | particle, material, energy, thickness |
| `thin-layer-width` | sanity | `thin-layer-width` | particle, material, energy, thickness |
| `multiple-scattering` | sanity | — | — |
| `em-shower-shape` | sanity | — | — |
| `shower-containment` | sanity | — | — |
| `longitudinal-profile` | reference | `shower-maximum` | particle, energy, target hash |
| `published-data` | interface | — | — |

A record whose `grade` disagrees with the table, or whose name is not in it, is an error (for every record with a Geant4 study block). `GRADES` in `geant4_benchmarks.py` stays for the tool, with a consistency test.

### 6.2 Scope (C1)

- Compare the controlled `observable.kind`; `label` writes it into `declared_scope.observable_kind`.
- The dimension list is **declared per benchmark** (fourth column of 6.1), each dimension typed: categorical (particle, say) or a numeric range (energy, say); a scalar is [v, v]. A new use case adds dimensions by changing the table (data), not the comparison logic.
- A declared scope missing a dimension the benchmark has is outside.
- For benchmarks with a target-hash dimension (such as `longitudinal-profile`), the declared scope must carry the same `target_geometry_sha256`.
- Gating: `strict or _at_least(contract_version, C1)`, no warning branch; records at 3.5.0 or below are bound only under `--strict`.

### 6.3 Configuration and isolation (C1)

- **Target:** the benchmark config declares `target_slabs` (A1) or a list of target volumes (from A2a, matching placements in the geometry tree).
- **Isolated:** the world is vacuum and every placement other than the world belongs to the target; a field attached only to volumes inside the target is part of the target and enters the target hash; a field extending beyond the target makes it embedded.
- **Source of the derivation:**
  - A1: derived from `layered_sim`'s spec. For `layered_sim` the spec is the actual geometry (A2a proves it with the placement dump), so it can upgrade.
  - From A2a: derived from the geometry tree in the effective config; `layered_sim` runs also check "spec-derived = tree-derived".
  - Another backend with declarations only (`source: declared`) can run and be published but cannot upgrade.
- **`target_geometry_sha256`:** the sha256 of the target's normalized list (ordered placements, solid parameters, material composition and density, transforms, attached field; numbers as hex floats).
- **Contract rule:** every counted benchmark must be `isolated`; `dependencies.py` must re-derive configuration and hash from the run records in `evidence_records` and compare.

### 6.4 C2 (B1)

- The table gains the `verification` grade and J15's checks; only reference is counted.
- **Transitive derived-simulation marker:** the input chain of a simulated table may have any depth (simulation → digitization → reconstruction → analysis), as long as every level is a recorded computational-run and every root of the chain is a simulation run.
- Gated like C1.

### 6.5 sci-fix and advisories (A1)

| Defect | Ledger entry | Severity |
|---|---|---|
| D1 (including per-benchmark scope dimensions) | scope-kind | S2 |
| D2 | grade-table | S2 |
| D3 | control-shift | S2 |
| D4 | gate-IUT | S2 |
| D5 (including batch means replacing the bootstrap, exact counting intervals, a declared K) | variance-method | **S1** |
| isolation definition (including the field rule) | isolation | S2 |
| D6 | stopping-rule | S3 |

One advisory each for S1 and S2 (keys `artifact_types: [computational-run]`, `extension_keys: ["study", "evidence_records"]`; introduced 0.20.0). simulated dataset-records cannot be keyed; the remedy asks holders to run `contracts/dependencies.py` on each simulated table.

---

## 7. Code and CI

| Location | Change |
|---|---|
| `contracts/validate.py`, `dependencies.py` | 6.1–6.4 |
| `contracts/schema.py` | `maxItems`, `maximum`, `exclusiveMaximum`; `test_schema_keywords.py` also scans the adapter schemas |
| `contracts/schemas/ext_computational_run.json` | optional free-form property `simulation` (needs hep-computing's agreement) |
| `skills/hep-detector/scripts/` | inference and decisions (§5); reads chunk CSVs in A1, summaries from A2b; no new script, `SKILL.md` and description unchanged |
| `core/geometry/layered.py` | dual-format geometry accessor (steward hep-detector) |
| `adapters/geant4/assets/` | `geant4_run.py` (`chunk` with the seeds of §5, `summarize` reading summaries, B1 adds `reco` and `table`), `layered_sim/` (`convert`, probe, accumulation, B0 event files, B1 field and crossings), `SimSummary.hh`, B0 `simroot`, B1 `simreco` |
| `SIM_SOURCES` | updated with the new sources so that `sources_sha256` covers them all |
| CI | task A needs no new required CI job; a ctest of `SimSummary.hh` can be an optional job. B1's `simreco` needs a required C++17 CI job |
| trace | new record writers call `trace.provenance()`; new shared functions call `trace.tag()`; calls to C++ executables record the sha256 of executable and sources, the version and the subcommand |

---

## 8. Stages and acceptance

### A1 Correctness fixes (contracts C1, sci-fix)

**Content:** §6.1–6.3 (derived from the spec in A1), §6.5; all statistical rules of §5, computed in Python from chunk CSVs; the D8 enums, the D10 tests, protocol section 4; the `simulation` property.

**Acceptance:**
- [ ] Records with a kind mismatch, a missing declared dimension, a grade that disagrees with the table, a missing or embedded configuration, or a mismatched target hash are refused under `--strict` and C1; a mismatch found by `dependencies.py`'s re-derivation is refused.
- [ ] The regenerated J14 study records pass `validate.py --strict` and `dependencies.py`; J14's verdicts do not change.
- [ ] The gate toy (10⁴ trials per cell) matches the operating characteristics of §5; unresolved is reported with exit 3.
- [ ] Batch-means coverage toy: the actual coverage of a nominal 90 % interval for J14's observables is within 0.90 ± 3σ_MC; exact intervals switch in correctly for rare counts.
- [ ] MPV bias toy: |bias| ≤ tol/10.
- [ ] Negative controls in both signs; after the live re-record of J14 on E2 with K = 16 chunks, the controls are still caught within \|shift\| ≤ 1.1 × DL, or they are redesigned and the reason recorded.
- [ ] `python3 -m unittest discover -s tests/contracts -t .` has no errors.
- [ ] Ledger entries and two advisories pass `scifix_advisories.py check`; VALIDATION GEANT4-CORRECTNESS; CHANGELOG; release manifest.

### A2a spec/2 and probe (adapter 0.2.0)

**Content:** §4.1 (reserved `field`, `source.type = gun`), `layered_sim convert`, the §4.3 probe (envelope, geometry tree), the dual-format accessor, schema keywords and `cross_field_checks()`.

**Acceptance:**
- [ ] Bit-identical on the same host (CSV, placement dumps).
- [ ] A non-empty `field` is rejected with exit 2.
- [ ] Every J14 run has an effective config; configuration and target hash derived from the geometry tree agree with those derived from the spec; a deliberate disagreement is caught.
- [ ] The probe writes `recorded: false` at the wrong time (test command).
- [ ] The accessor gives the same result for spec/1 and spec/2; both thin-layer rules fire for both formats.
- [ ] `contracts.schema.validate()` plus `cross_field_checks()` reach the same verdicts as the old `validate_spec()`.
- [ ] J14 re-recorded on E2; VALIDATION GEANT4-SPEC2.

### A2b Run summary and backend interface (adapter 0.3.0)

**Content:** `output.observables` (single columns), `SimSummary.hh`, MT merging, `layered_sim.summary/1`, column map; Python inference reads summaries; J14 replays from the committed summaries.

**Acceptance:**
- [ ] With the same seed, serial and MT runs with different thread counts give bit-identical summaries; merging chunks equals a single run's accumulation.
- [ ] A summary recomputed in Python from a committed CSV is bit-identical to the one `layered_sim` wrote.
- [ ] Overflow is detected and the run is incomplete; the quantization-error bound check works.
- [ ] J14's offline replay reproduces the committed output bit for bit and runs where no compiler is installed.
- [ ] A second backend (delivering only the three boundary artifacts) passes J14's gates and benchmarks.
- [ ] Production Python no longer computes statistics from per-event CSVs (only the oracle tests do).
- [ ] VALIDATION GEANT4-SUMMARY; CHANGELOG; release manifest.

### B0 Per-event ROOT files (adapter 0.4.0)

**Content:** §4.5; the `G4RootAnalysisReader` trial first.

**Acceptance:**
- [ ] With `level = none` the output is bit-identical to A2b's; switching on `summary` changes neither the CSV nor the run summary.
- [ ] `simroot` round trip: values of every level and I, D, S columns are bit-identical; different thread counts give the same `content_sha256`.
- [ ] The per-event sum of `deposits` in the ROOT file equals the CSV's total deposit per subsystem; `hits` above the limit exits 2; an interrupted run is incomplete.

### B1 J15 minimal spectrometer (adapter 0.5.0, contracts C2)

**Content:** J15's design is in `task-b-j15.md` §4 (geometry, parameters, acceptance: B = 0.5 T, six Si planes, two TOF layers per station, a 50-layer Pb/PVT calorimeter); the field (`ConstructSDandField`, thread-local, `delta_intersection` 1e-5 mm, DormandPrince745); the plane-crossing scorer and the `crossings` ntuple; `simreco` (writing run summaries and per-event results); the validation ladder (`field-propagation` and others), deterministic field checks, calorimeter cut convergence, variations; `verification` and the transitive marker (C2); the J15 journey and routing case.

**Acceptance:** as in `task-b-j15.md` §10, plus:
- [ ] `simreco`'s summaries pass the same bit-identity and recomputation tests as A2b.
- [ ] An input chain of three or more levels (simulation → reconstruction → table) is accepted by `dependencies.py`; one whose root is not a simulation run is refused.

---

## 9. Generality

### 9.1 Use cases covered

| Use case | Supported by | Status |
|---|---|---|
| material-level references (J14-like) | the §6.1 table, isolated slabs | A1 |
| spectrometers with a field (J15, space and cosmic-ray detectors) | field counted in the target (§6.3), `verification`, the reconstruction chain | B1 |
| test-beam or collider modules (non-slab, compared with data) | configuration from the geometry tree; per-benchmark scope dimensions; target hash matched to the configuration of a published measurement | contracts ready from A1 and A2a; `layered_sim` itself stays slab-only (user applications can be used) |
| rare events, biasing | weighted accumulators, exact counting intervals | accumulators in A2b; biasing-specific rules deferred |
| other engines, fast simulation, ML surrogates | the three boundary artifacts, the engine-independent effective-config envelope | interfaces in A2a and A2b; rule packs deferred |

### 9.2 Interfaces defined now, implemented later

| Interface | Content | First use case |
|---|---|---|
| observable combinations and selections | a linear combination of columns, the ratio of two columns; AND of column-against-constant comparisons. Anything more is a recorded program step | the first study that needs an event selection |
| profiles and 2D histograms | n, Σw·y, Σw·y² in bins of x; 2D Σw | the first study with a spectrum source (resolution against continuous rigidity, say); J15 runs at fixed rigidities and does not need it |
| sources | `gps` (`G4GeneralParticleSource`, declarative settings only), `event-file` (HepMC and others); the summary records the source area and solid angle for flux normalization | the first spectrum or flux study |
| `simreduce` | reads ROOT event files and writes summaries as declared, so observables decided later need no rerun | the first need after B0 |

### 9.3 Deferred (with triggers)

| Item | Trigger |
|---|---|
| non-slab geometry in `layered_sim` (GDML, cylinders, rotations) | the first study that needs non-slab geometry and cannot use a user application |
| rule packs and probes for other engines | the first non-Geant4 backend |
| biasing-specific rules (weight distribution, minimum n_eff) | the first study with biasing |
| optical photons, long time windows, decay chains | the first scintillator or rare-event study |
| ion sources and Birks (J16) | a cosmic-ray nuclei study and a literature record for PVT's Birks constant |
| probes for several Geant4 versions | the first application on a version other than 11.4 |
| `physics_config_comparison` | a study that needs to compare physics settings |
| RNTuple, vector columns | ROOT file size or read speed becomes a bottleneck |
| generalized `scoped_upgrade` | a second kind of study needs upgrades |

### 9.4 Deliberately not done

- A general expression language (it would become a second programming language to validate).
- A plug-in system for estimators (estimators are a small set of tested Python functions).
- One probe content for all engines (only the envelope is unified).
- Adaptive binning or approximate quantile sketches (merged results depend on order, breaking exactness).
- Stopping adaptively on the SE, or refined scans as evidence (optional stopping).
- The `uses-validated-physics` label, contracts 4.0, Python bindings, a content-addressed cache.
- Moving statistics to C++ (`simstat`) and a Geant4-free `simcore` project (task A does not need them).

---

## 10. Residual risks

1. J14's detection limits may change with batch means, t quantiles and controls in observable units, and the controls may need redesigning.
2. For very skewed observables the t approximation with K = 16 may be optimistic; the coverage toy shows it, and K is raised if needed (declared in advance).
3. Quantization means a summary is not the exact floating-point sum; the error bound n·q/2 must be far below the tolerances.
4. The MT behaviour of a custom `G4VAccumulable` and `G4AccumulableManager::Merge()` must be confirmed by a test on 11.4.3.
5. Geant4 initialization time for 16 or more processes: a few seconds per point for J14; calorimeter studies estimate it with a trial run.
6. The probe assumes workers match the master; if a thread-local difference appears, dump per thread.
7. When a target hash is matched to a published measurement, the contract can only compare hashes, not decide that the target is the configuration in the paper; a reviewer still checks.
8. The reading ability of `G4RootAnalysisReader` is unverified (B0 trial).
9. Only 931 bytes of quick-load budget remain; J15 does not change `SKILL.md` or the description.
10. Effort: the prototype estimates A1 at about 8–12 engineer-days plus Geant4 time; A2a, A2b, B0 and B1 are not estimated.

---

## 11. Decision record

### 11.1 Decided by the user

| Date | Decision | Where in this architecture |
|---|---|---|
| 2026-10-22 | core code in C++, Python as the interface; compute core in C++, reference values stay in Python; separate executables exchanging JSON/CSV, no Python bindings | §2.3 principle 2 (as interpreted by item 1 of 11.2) |
| 2026-10-22 | J15's TOF1 and TOF2 two layers each, all four of the same material | B1 |
| 2026-10-22 | detailed per-event information stored in ROOT files | §4.5, B0 |
| 2026-10-22 | J15 split from the rest into a second task, done later | task A (A1, A2a, A2b), task B (B0, B1) |

### 11.2 Proposals of this document (need the user's confirmation)

1. **Interpreting the language split:** the "core" is per-event computation, in C++; inference on run summaries is in Python. No `simstat` and no `simcore` project.
2. **The boundary artifact becomes the run summary** (weighted, int128 integer accumulation, with its own merge rules); J14 replays from summaries.
3. **Every SE uses batch means** (K ≥ 16, declarable), dropping the bootstrap; exact intervals for small counts; MPV by three-point interpolation with a bias limit. This widens the D5 sci-fix (S1).
4. **ROOT files and `simroot` move to B0**, together with their first consumer, `simreco`.
5. **Five stages** (A1, A2a, A2b, B0, B1), each merged on its own.
6. **Generalization in C1:** per-benchmark scope dimensions, the isolation definition with the field counted in the target; configuration from the geometry tree from A2a; an engine-independent effective-config envelope; the derived-simulation marker made transitive in C2.
7. Default quantization steps (1 eV, 1 nm, 1 fs, weight 2⁻²⁰) and the threshold for exact intervals (any chunk at 0 or a total < 100).

### 11.3 For the maintainer to decide

1. The version class of C1 (proposed: minor plus a sci-fix).
2. Whether a statistical comparison is acceptable if bit identity fails even on the same host.
3. How to confirm the G5 statement that no example code was copied.
4. hep-computing's agreement to the `simulation` property and the transitive derived-simulation marker of C2.
5. A required C++17 CI job for B1's `simreco`.
6. Where ROOT files are stored and for how long.

---

## 12. Mapping to the current task specs, and next steps

| Current spec | This architecture |
|---|---|
| `task-a-core.md` A1.1–A1.3 (contracts) | A1, plus per-benchmark scope dimensions and the field definition of isolation |
| A1.4–A1.10 (statistics and other fixes) | A1, with batch means replacing the bootstrap, MPV interpolation and bias limit, declarable K, exact intervals |
| A1.11 (sci-fix) | §6.5 (D5 widened into variance-method; a new isolation entry) |
| A2.2–A2.7 (spec/2, conversion, accessor, schema, probe, column map) | A2a (conversion becomes `layered_sim convert`; the probe gains the envelope and the geometry tree) |
| A2.8 (`simcore`, `simstat`) | dropped; inference stays in Python and reads summaries from A2b |
| A2.9–A2.10 (ROOT files, `simroot`) | B0 |
| all of `task-b-j15.md` | B1 (`crossings` defined as an interface in B0, implemented in B1; `simreco` writes summaries; the C2 marker becomes transitive) |

**Steps after approval:**
1. Rewrite `task-a-core.md` (A1, A2a, A2b) and `task-b-j15.md` (B0, B1) from this document, both languages together, in the current implementation-spec format (task card, terms, hard rules, work items, acceptance, order of work).
2. Update `README.md`.
3. Have an agent that did not write them review the specs independently, focusing on summary accumulation, quantization and merging; the switch between batch means and exact intervals; configuration derived from the geometry tree; the interfaces between stages.
