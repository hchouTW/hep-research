# hep-research simulation study architecture (redesigned with reference to real experiments)

> Status: architecture proposal, awaiting the user's confirmation of §12.2 and the maintainer's decisions in §12.3. Supersedes the previous version of this document (`2d32342`, "consolidated"); whatever still applies from it and from the three checks has been merged here, and the superseded designs are listed in §13
> Baseline: hep-research `main` at `9f08796` (0.23.0 plus unreleased changes), contracts 3.5.0, adapter geant4 0.1.0, Geant4 11.4.3
> Date: 2026-10-22
> Language: English translation of [`architecture.md`](architecture.md) (Traditional Chinese original), same content
> How to read: §0 is a one-page summary; §1 the design basis taken from real experiments; §2–§9 the architecture; §10–§13 stages, risks, decisions and history

---

## 0. Summary

**Purpose.** Make simulation studies in hep-research (Geant4 today) achieve three things: results cannot be wrongly labelled `validated-in-scope`; numbers and decisions are reproducible and traceable; the study layer is not tied to one simulation program, one geometry or one kind of study.

**Starting point.** Large experiments have solved the same problems at a much larger scale. This architecture takes only practices that have stood the test of time and are feasible under the plugin's constraints (standard-library Python, separate executables exchanging JSON/CSV, minimal change):

| Problem | What real experiments do | This architecture |
|---|---|---|
| reproducibility under parallel execution | ATLAS reseeds each event from the event and run numbers; Allpix² seeds by event number, "reproducible even when the number of workers is different" | each event reseeded with H(logical-run seed, event number); job splitting and thread count do not affect event content (§5) |
| merging results of many parallel jobs | CMS DQM: jobs fill histograms independently; the harvesting step merges them and only then runs quality tests | simulation programs write mergeable run summaries; Python infers and decides only after merging (§4) |
| tracing configuration and processing chains | CMS identifies configurations by parameter-set hashes and records each processing step in a process history | each step records hashes of its configuration, inputs and code; multi-level chains are traced transitively (§7) |
| supporting several simulation engines | ALICE's Virtual MC puts an insulation layer between user code and the engine, but separating geometry took years | no abstraction at the API level; abstraction at the **output**: any backend that delivers three boundary artifacts (§3) |
| sharing data between components | Key4hep uses EDM4hep as the common data model between components; legacy tools join by converting | the boundary artifacts are the common data model; other frameworks join through a reducer (§3.4) |
| whether a simulation can be trusted | Geant4's geant-val compares with experimental data across releases; CMS selects the physics list with test-beam data, then checks with collision data; ATLAS validates fast simulation against Geant4 | five validation classes, each with its own reference, statistics and rule on upgrading (§6) |
| whether a software change alters results | Belle II runs validation scripts nightly, compares across versions and can bisect the commit that caused a degradation; geant-val runs monthly | a regression class: compares with the previous version, detects change, never upgrades (§6.4) |
| data volume tiers | ATLAS: HITS → RDO → AOD; only the tiers needed downstream are kept | four data tiers: event detail (not committed) → per-event summary → run summary → decision records (§4.1) |

**The core of the architecture (six sentences):**
1. **Two planes.** Per-event processing is in C++ (the data plane: simulation, digitization, reconstruction); inference after merging, decisions, records and contracts are in Python (the control plane).
2. **A backend interface at the output.** Any backend that delivers a run summary, a column map and an effective config (including the actual geometry tree) reaches the gates, benchmarks and labels.
3. **Event determinism.** Event content depends only on the logical-run seed and the event number; job splitting, thread count and processing order do not matter.
4. **Reproducibility means "same decisions".** On replay, decisions and labels must be identical and numbers within a relative difference of 1e-9; decisions close to a threshold are flagged. Source files are traced by hash.
5. **One variance method.** The run summary splits events into K blocks by event number; every SE is estimated by batch means over the blocks, with exact intervals for small counts.
6. **Five validation classes.** Verification, physics reference, setup-matched measurement, regression, model-to-model; only physics reference and setup-matched measurement can upgrade, under conditions the contract re-derives from evidence.

**Stages:**

| Stage | Content | Version |
|---|---|---|
| A1 | correctness fixes (sci-fix): contracts and statistical rules; J14 recomputed offline from existing per-event data, re-recording only runs without per-event data | contracts C1 |
| A2 | shared Geant4 helper library; `layered_sim` writes the three boundary artifacts and gains a per-event seeding option; the study layer reads only boundary artifacts | adapter 0.2.0 |
| B1 | `element_sim`: box elements, nesting, field, plane crossings, per-event ROOT files and `simroot` | adapter 0.3.0 |
| B2 | `simreco`; the J15 study; verification, regression and model-to-model classes and transitive processing chains (C2) | adapter 0.4.0, contracts C2 |

A1 and A2 are "task A"; B1 and B2 are "task B", which starts after task A is merged. Each stage merges on its own.

---

## 1. Design basis: what real experiments teach

Each point has a source (§14). "Taken" is what this architecture adopts; "not taken" is what it deliberately leaves out, and why.

### 1.1 Random numbers and reproducibility

- **ATLAS (AthenaMT):** random streams for different purposes are distinguished by the name of the algorithm using them; generator states are reseeded for each event from the event and run numbers; the goal is that "the sequence of random numbers must be independent of the order in which events are processed".
- **Allpix²:** the main thread seeds each event from a central seed generator as events are created; a worker seeds its engine just before running the event; the design aims at "reproducibility of simulation results from the same inputs even when the number of workers is different". Modules that need ordered output wait in a buffer queue, saving the random-engine state.
- **CMS:** a different approach: one engine per module and per stream, whose state can be saved into the event and restored later for exact replay.
- **Taken:** the per-event reseeding of ATLAS and Allpix². It is the simplest, and it makes "one logical run split into several jobs" produce exactly the same events as a single job. **Not taken:** CMS's state saving (saving engine states per event is unnecessary at our scale).

### 1.2 Merging results and where decisions are made

- **CMS DQM:** data is split into any number of jobs, processed out of order and massively parallel; each job fills MonitorElements (mostly histograms); the harvesting step merges matching histograms across files and only then runs quality tests and derived quantities, single-threaded and in order.
- **Taken:** simulation programs fill only "mergeable accumulators" (counts, sums, histograms); all decisions are made after merging, in Python. This is exactly the split between the run summary and the control plane.

### 1.3 Traceability

- **CMS:** configurations are identified by parameter-set hashes, and a process history records every processing step the data went through.
- **Taken:** every step (simulation, digitization, reconstruction, table) writes a record with the hashes of its configuration, inputs and code; the input chain of a simulated table can be any depth, checked transitively by the contract (§7.4).

### 1.4 Several engines

- **ALICE Virtual MC:** an insulation layer between user code and the transport engine, so that geometry and hit-generation code is written once; at the time Geant3 was used in production, Geant4 only for physics validation, FLUKA was not yet finished, and separating geometry from transport was still ongoing.
- **ATLAS AtlFast3:** work is routed by particle type and energy to Geant4, FastCaloSim V2 and FastCaloGAN; fast simulation is validated by showing "no sizeable differences from the Geant4 simulation" after reconstruction.
- **Taken:** abstraction at the **output**, not at the stepping API: a backend may simulate however it likes, as long as it delivers the same boundary artifacts. A backend that mixes simulators describes its routing in the effective config. Fast simulation and ML surrogates validated against Geant4 are "model-to-model" validation (§6.5). **Not taken:** a VMC-style engine abstraction layer (ALICE's experience shows high cost and a long time scale).

### 1.5 A common data model and geometry

- **Key4hep:** Gaudi as the processing framework, DD4hep for geometry, EDM4hep (built with podio) as the data model; EDM4hep is the exchange format between components in memory and on file; legacy iLCSoft processors convert to and from EDM4hep on entry and exit instead of being rewritten.
- **Taken:** the boundary artifacts are our common data model; external frameworks join through a "reducer" (for example reducing an EDM4hep file to a run summary). Geometry is taken from the backend's actual (as-built) geometry. **Not taken:** Gaudi or DD4hep as dependencies (plugin constraints).
- **GDML:** Geant4 can write the actual geometry as GDML, but only when built with GDML; this plugin's build has `GEANT4_USE_GDML: OFF` (`geant4_build.py` line 53). So the probe walks the actual geometry itself (§3.3); a user's build with GDML may attach a GDML file as well.

### 1.6 Validation

- **geant-val (Geant4 collaboration):** community validation tests run monthly with development releases; results are stored in a database, compared across releases, with χ² and KS tests on distributions.
- **CMS:** first tunes and selects the physics list with test-beam data, then checks calorimeter response and resolution with isolated charged particles in collision data; compares several Geant4 versions before adopting one, trading speed against accuracy.
- **Belle II:** every software package has validation scripts producing histograms; they run centrally every night, are compared across versions, and a tool bisects the commit that introduced a degradation.
- **Taken:** "validation" split into five classes of different nature (§6): verification as an exact consequence; a physics reference on an isolated target (geant-val's thin-target tests belong here); comparison with a measurement on the same configuration (CMS test beams); regression across versions (Belle II, geant-val's monthly comparison); model-to-model (ATLAS fast simulation).

### 1.7 Data tiers

- **ATLAS:** simulation writes a HITS file; digitization writes RDO (conceptually similar to raw detector data); reconstruction writes AOD.
- **Taken:** four data tiers, each with its own retention rule (§4.1).

### 1.8 Real instruments (comparison for J15)

- **PAMELA:** a 0.43 T permanent magnet; 6 planes of double-sided silicon microstrip sensors, resolution better than 4 µm; MDR above 1 TV; three TOF planes (S1–S3, segmented into paddles); a tungsten/silicon imaging calorimeter of 16.3 X₀ and 0.6 λ; plus anticoincidence, S4 and a neutron detector.
- **AMS-02:** four TOF planes (8, 8, 10 and 8 counters); about 140 ps for protons for the system.
- **Taken:** J15 (0.5 T, 6 Si planes, MDR about 1.17 TV, two TOF layers per station, an 18.4 X₀ calorimeter) is almost the same type as PAMELA and serves as a plausibility comparison; 100 ps per TOF layer is optimistic against AMS-02, so J15 scans σ_t at 100 and 150 ps (§10 B2). J15 remains a synthetic geometry and represents no experiment.

---

## 2. Goals, constraints and principles

### 2.1 Goals

| Goal | Guaranteed by |
|---|---|
| `validated-in-scope` cannot be obtained wrongly | facts the contract re-derives from evidence (§7) |
| reproducible decisions, traceable numbers | event determinism (§5.1), inference after merging (§4), the same-decision definition of reproducibility (§5.6), hashes of every step (§7.4) |
| the study layer is not tied to one backend, geometry or kind of study | a backend interface at the output (§3) |
| demonstrate a field, several subsystems and reconstruction | J15 (B1, B2) |

### 2.2 Constraints

- Python uses only the standard library.
- G5 licence boundary: Python exchanges only JSON and CSV with separate executables; no Geant4 example code is copied.
- Layering: skill scripts and adapters import only `core` and `contracts`; no experiment names in `skills/` or `contracts/` (experiment names may appear in `docs/` and `examples/`).
- Statuses and exit codes (`core/status.py`): 0 ok, 1 a negative verdict, 2 `rejected`, 3 `incomplete`.
- Files ≤ 2 MiB; hep-detector quick load ≤ 25,600 bytes (24,669 now), description ≤ 1,024 characters (`measure_entrypoints.py` reports 1,016).
- J14's offline replay must always run, with no Geant4 and no compiler.

### 2.3 Principles

1. **Correctness before extension.** Nothing new is merged before A1.
2. **Per-event in C++, after merging in Python.** Code that processes per-event data is in the data plane; code that processes merged accumulators is in the control plane. One production implementation per quantity; one in the other language may exist only in tests, as an oracle.
3. **Abstract at the output.** The study layer knows only the boundary artifacts, never a backend's column names, spec format or UI commands.
4. **Trust the actual state; declarations are only the fallback.** Geometry, field and physics settings come from the probe; declarations alone are marked `source: declared` and cannot upgrade.
5. **Upgrade-relevant facts are decided by the contract.** Grade, kind, scope dimensions, configuration and target hash are never self-declared by a record.
6. **The validation class follows the nature of the reference** (§6).
7. **Event determinism.** Event content depends only on the logical-run seed and the event number.
8. **What is reproduced is the decision.** Numbers are compared within tolerances, decisions must be identical, sources are traced by hash.
9. **Stopping rules, grids and block counts of evidence are declared in advance.** Topping up, refining and redoing controls are never decided from results.
10. **Extensible interfaces, implementation only as needed.** No general expression language, no plug-in system, no engine abstraction layer.
11. **Look for an existing implementation first; minimal change.**

---

## 3. Architecture overview

### 3.1 Two planes and the components

```
Control plane (Python, standard library)
  hep-detector      rules, reference formulas, inference (batch means, exact intervals, MPV, IUT, negative controls, distribution comparison), decisions, labels
  adapters/geant4   spec validation, build, run, job splitting, records (trace.provenance()), simulated tables;
                    produces run summaries from per-event CSVs in A1 (only as the oracle in tests from A2)
  core              trace, status
  contracts         validation-class and grade table, scope, configuration and isolation (C1); new classes, transitive processing chains (C2)
        ▲
        │  three boundary artifacts (JSON; small, committable, hashable)
        │    run summary        simulation-summary/1    (§4)
        │    column map         simulation-columns/1    (§3.5)
        │    effective config   engine-independent envelope + actual geometry tree (§3.3)
        │
Data plane (C++)
  g4sim/         shared Geant4 helper library (headers):
                      SimSeed.hh     per-event seed H(logical-run seed, event number)
                      SimSummary.hh  block accumulators, merging, JSON writer (standard library only)
                      SimProbe.hh    the probe: settings and actual geometry tree (depends on Geant4)
                      materials, physics-list selection, CSV writer
  layered_sim       the existing slab program; spec/1 unchanged; gains g4sim
  element_sim       (B1) a general box-element program: nesting, field, plane crossings, per-event ROOT files
  simroot           (B1) links only Geant4's analysis library: info / dump / hash of ROOT files
  simreco           (B2) no Geant4: digitization and reconstruction, writes run summaries and per-event results
  other backends    a user's Geant4 application (including g4sim), other engines or frameworks (converted by a reducer)
```

| Component | Language | Stage | Depends on |
|---|---|---|---|
| contracts | Python | A1 (C1), B2 (C2) | — |
| inference and decisions | Python | A1 | — |
| Python run-summary producer (from per-event CSVs) | Python | A1; only the oracle from A2 | — |
| `g4sim` (`SimSeed.hh`, `SimSummary.hh`, `SimProbe.hh`, helpers) | C++ | A2 | Geant4 (`SimSummary.hh` standard library only) |
| `layered_sim` | C++ | existing; gains `g4sim` in A2 | Geant4 |
| `element_sim` | C++ | B1 | Geant4, `g4sim` |
| `simroot` | C++ | B1 | Geant4 analysis (g4tools) |
| `simreco` | C++ | B2 | standard library, `SimSummary.hh`, `MiniJson.hh` |

### 3.2 Backends

| Backend | Purpose | Geometry | Status |
|---|---|---|---|
| `layered_sim` | material-level slab studies (J14) | spec/1: a stack of slabs along x | existing; after A2 only maintenance and `g4sim` integration, no new geometry features |
| `element_sim` | detector-level studies (from J15) | box elements, one level of nesting, field regions | new in B1; future geometry features go here |
| a user's Geant4 application | an experiment group's own geometry | anything (GDML included) | delivers the boundary artifacts by including `g4sim` |
| other engines or frameworks | FLUKA, fast simulation, ML surrogates, Key4hep and others | anything | a reducer converts their output into boundary artifacts; with probe content declared only (`source: declared`) they cannot upgrade |

**Why a new `element_sim` rather than reworking `layered_sim`.** Moving `layered_sim` to a new geometry format needs a spec conversion with a same-host bit-identical check, plus a dual-format accessor maintained forever; it was the most costly and least valuable step of the previous version (§13). A new program leaves J14's program untouched and gives two real backends to test the output interface from day one. Both share `g4sim`, avoiding duplication.

### 3.3 Effective config

```
{ "engine": "geant4", "engine_version": "11.4.3", "probe_version": "...",
  "backend": {"name": "element_sim", "version": "...", "sources_sha256": "..."},
  "source": "probe" | "declared", "recorded": true, "config_sha256": "...",
  "seeding": {"mode": "per-event" | "stream", "logical_run_seed": ...},
  "geometry": { "tree": [...], "tree_sha256": "...", "hash_scheme": "tree-v1", "gdml_sha256": null },
  "environment_ref": "<hash of the build record>",
  "sections": { "geant4": { ... } } }
```

| Part | Content |
|---|---|
| envelope | engine-independent; rules are chosen as a rule pack by `engine` (only Geant4's `G4R-*` today) |
| `geometry.tree` | rebuilt from `G4PhysicalVolumeStore` (a flat list in creation order) and each volume's mother logical volume; each placement records name, copy number, solid type and parameters, material (composition and density as resolved by Geant4), transform, mother, attached field manager and its parameters; numbers in Python's `float.hex()` format. Replica and parameterised volumes record their parameterization |
| GDML | when a user's build enables GDML, a file written by `G4GDMLParser` and its hash may be attached; not required |
| `sections.geant4` | the full text of `G4EmParameters::StreamInfo` plus parsed fields; per-couple cuts and energy thresholds; energy ranges per process and model; run-manager type; `G4UserLimits`, biasing |
| datasets | paths and content hashes computed once in the build record; the probe refers to it by `environment_ref` |
| timing | master `BeginOfRunAction` (after `RunInitialization`), in `G4State_GeomClosed` with more than 0 couples; otherwise `recorded: false`, and the run cannot upgrade |
| field | field managers are per thread; the master also calls `ConstructSDandField`, so backends using `g4sim` see the field on the master; a declared field the master cannot see marks the config `source: declared` |
| mixed simulators | a backend that routes particles or regions to different simulators describes the routing in `sections` |

### 3.4 Reducers (where external backends join)

A backend that cannot include `g4sim` (other engines, Key4hep's EDM4hep files, ML surrogates) joins through a recorded reduction step: it reads that backend's per-event output and writes a run summary and a column map as declared in `output.observables`; its effective config is declared only. The step is itself a computational-run record in the processing chain (§7.4). The first reducer, `simreduce`, reads the output of `simroot dump` (implemented after B1, at the first need).

### 3.5 Column map (`simulation-columns/1`)

For each observable and output column: semantic name, actual column name, unit, operational definition, and the file it lives in (`csv`, which ntuple of `root`, or `summary`); with `column_map_version`. Only declarative operations (rename, unit, sum, filter) are allowed; a conversion that computes something is a separate recorded step.

---

## 4. Data tiers and the run summary

### 4.1 Four data tiers

| Tier | Content | Analogue | Retention |
|---|---|---|---|
| T1 event detail | ROOT files: per-volume deposits, plane crossings, per-step hits | ATLAS HITS | not committed; records keep the path, file hash, content hash and row count per ntuple |
| T2 per-event summary | CSV: primary truth, total deposit per subsystem, declared observables | a reduced event table | benchmark runs commit a reduced-column version; others are not committed |
| T3 run summary | `simulation-summary/1`: mergeable accumulators per event block | CMS DQM MonitorElements | all committed (a few kB per run) |
| T4 decision records | study records, benchmark results, labels | — | all committed |

J14's offline replay needs only T3 and T4; T2 is used only for optional oracle tests and the high-statistics MPV check.

### 4.2 Run summary (`simulation-summary/1`)

One JSON per job.

| Field | Content |
|---|---|
| `run` | identity and seed of the logical run, the event-number range this job covers, `seeding`, block size B and block count K, hashes of the spec and effective config, the producer (`layered_sim`, `element_sim`, `simreco`, `python-csv`, a reducer) and its version |
| `observables[]` | per declared observable: semantic name (matching the column map), unit, accumulators |
| blocks | events go into blocks by number: block b covers events [b·B, (b+1)·B); each block has its own set of accumulators |
| accumulators | integers: `n`, the count per histogram bin (declared fixed bins; overflow and underflow separate), `count_if[]` (counts above declared thresholds); floating point: Σx, Σx², `min`, `max`, with Neumaier compensated summation; from B2 `profile` and 2D histograms may appear (§9) |
| `merge` | each accumulator's merge rule (`sum`, `min`, `max`, `hist`); several jobs of one logical run merge by block number |

**Event weights.** `layered_sim`'s deposits are already multiplied by the track weight, while the CSV's `weight` column is only the primary vertex weight. To avoid double weighting, the event weight must be 1 for now (otherwise exit 2); the meaning of weighted accumulation and rules for biasing are deferred (§9.3).

**Numerical precision.** Integer accumulators (counts, histograms, `count_if`) are exact. Floating-point sums use compensated summation; different job splits or thread counts change only the merge order, giving relative differences of about 1e-15, far below the reproducibility tolerance (§5.6).

---

## 5. Execution, seeds, blocks and reproducibility

### 5.1 Logical runs and event determinism

- A **logical run** is fixed by the spec, the backend and the logical-run seed S, and has N events numbered 0 … N−1.
- `seeding: per-event` (the default for new specs): event i reseeds at its start with H(S, i). Therefore:
  - splitting a logical run into any number of jobs (each covering a range of event numbers) gives exactly the same events as a single job;
  - serial and MT with any thread count give the same event content.
- `seeding: stream`: the old behaviour (serial: one continuous stream; MT: the master draws per-event seeds in batches). Used only for J14's existing specs, so that A2's regression check can require bit-identical CSVs.
- Seeds: S = H(study_id, role, point_id), mapped to [1, 2³¹); roles are trial, nominal, scan, control, variation, calibration, regression; positive and negative controls use different point_ids. No S repeats within a study.

### 5.2 Blocks and batch means

- Block size B and block count K (K ≥ 16) are declared before the first evidence run; N = K·B.
- From the summary, each block b gives an estimate θ_b (mean, fraction, ratio, quantile, mode); report θ̄ = the mean; SE = sd(θ_b)/√K, with K − 1 degrees of freedom.
- Blocks are non-overlapping event ranges of the same run. Events are independent (guaranteed by the seeds with `per-event`; the standard Monte Carlo assumption with `stream`), so block estimates are independent.
- One run is enough to estimate the SE; there is no need for several processes for statistics, and job splitting is only for parallelism.
- Precondition: no state carried between events (adaptive biasing, cross-event caches and the like). The probe records biasing and related settings; when in doubt, use several independent logical runs instead.

### 5.3 Estimators

- **Several observables:** the vector of per-block estimates is kept together; covariances between observables are estimated from these vectors.
- **Full-sample values:** means and fractions also from the merged accumulators; the difference from θ̄ goes into the record as a diagnostic.
- **Quantiles:** linear interpolation within a histogram bin; the bin width must be below 1/10 of the tolerance; a quantile in the overflow or underflow bin makes the estimate incomplete.
- **MPV:** per block, take the highest histogram bin and interpolate the mode with a three-point parabola through it and its neighbours; report the mean of the K modes. At design time a toy shows the bias's 95 % upper bound ≤ tol/10 (the toy uses Landau–Vavilov, checked against the shape from one high-statistics Geant4 run); at every run, the difference between θ̄ and the mode of the merged histogram must be ≤ tol/5 + 2·SE, otherwise the benchmark is incomplete.

### 5.4 Small counts

- When a counting estimator has a block at 0, or a merged total < 100 (the threshold can be declared), exact intervals on the merged accumulators are used instead: Clopper–Pearson for fractions, Garwood for counts; comparing two runs uses the exact conditional binomial interval for the ratio of the rates, with relative difference = ratio − 1.
- There is no SE in these cases; the gate decides on interval endpoints (§6.6), and event planning uses the Poisson variance of the trial run.

### 5.5 Two-stage event count

N = ceil(N_trial·(SE_trial/target)²·f), with f = F₀.₉₀(K − 1, K_trial − 1) (≈ 1.97 when both are 16). About 10 % of evidence runs miss their target and are incomplete, with no top-up; F₀.₉₅ (≈ 2.40) brings this to about 5 % at about 22 % more events.

### 5.6 What reproducibility means

| Level | Requirement |
|---|---|
| traceability | every record keeps hashes of the spec, effective config, code (`sources_sha256`), seeds, and input and output files |
| re-execution | same build and platform, same logical run: identical event content; integer accumulators identical, floating-point accumulators within a relative difference of 1e-12 |
| replay (from committed T3 and T4) | decisions and labels identical; numbers within a relative difference of 1e-9; any decision whose margin is < 1e-9 (relative) is flagged "close to threshold" in the record |
| regression check (A2) | J14's existing specs (`seeding: stream`) produce, on the same host, CSVs bit-identical to those from before A2; files are only added, existing output is unchanged |

---

## 6. Validation classes and decisions

### 6.1 Five classes

| Class | Reference | Examples | Statistics | Can upgrade |
|---|---|---|---|---|
| verification | an exact consequence of the inputs | charged geantino against the analytic helix, kinematics, least-squares algebra | deterministic comparison or IUT | no |
| physics reference (reference) | a physics model Geant4 approximates, or a published thin-target measurement, on an isolated target | Bethe stopping power, Landau–Vavilov MPV, geant-val-style thin-target tests | IUT (scalars); χ² (distributions, §9.2) | yes (in scope) |
| setup-matched measurement (setup-matched) | a published measurement whose configuration has the same target hash | a test-beam longitudinal profile, a module's response and resolution | as above, plus the measurement uncertainties | yes (in scope) |
| regression | the same study's result with the previous software or Geant4 version | MPV, histogram shapes before and after a change | difference and SE for scalars; χ² p-value for histograms | no; only flags "changed" and may trigger an advisory |
| model-to-model (surrogate) | a full simulation such as Geant4, as the reference for fast simulation or an ML surrogate | a parametrized calorimeter against Geant4 | IUT or χ² | cannot upgrade physics labels; the surrogate itself may get a "consistent with the reference simulation in scope" mark |

There are also `sanity` (a rough plausibility check) and `interface` (an interface check); neither can upgrade.

### 6.2 Benchmark table (C1, extended in C2)

`contracts/validate.py` carries its own table; `_study_upgrade` takes class, grade, kinds and scope dimensions only from it.

| Benchmark | Class | Supported kinds | Scope dimensions |
|---|---|---|---|
| `stopping-power` | reference | `stopping-power` | particle, material, energy, thickness |
| `range` | reference | `range` | particle, material, energy, thickness |
| `thin-layer-mpv` | reference | `most-probable-value` | particle, material, energy, thickness |
| `thin-layer-width` | sanity | `thin-layer-width` | particle, material, energy, thickness |
| `multiple-scattering` | sanity | — | — |
| `em-shower-shape` | sanity | — | — |
| `shower-containment` | sanity | — | — |
| `longitudinal-profile` | setup-matched | `shower-maximum` | particle, energy, target hash |
| `published-data` | interface | — | — |
| added in C2: J15's checks (`field-propagation` and others) | verification or sanity | — | — |
| added in C2: generic entries for the `regression` and `surrogate` classes | regression, surrogate | any | the same as the study compared |

A record whose class or grade disagrees with the table, or whose name is not in it, is an error. `GRADES` in `geant4_benchmarks.py` stays for the tool, with a consistency test.

### 6.3 Scope (C1)

- Compare the controlled `observable.kind`; `label` writes it into `declared_scope.observable_kind`.
- The dimension list is declared per benchmark (fourth column of 6.2), each dimension typed: categorical or a numeric range; a scalar is [v, v]. A new use case adds dimensions by changing the table only.
- A declared scope missing a dimension the benchmark has is outside.
- With a target-hash dimension, the declared scope must carry the same `target_geometry_sha256` and `hash_scheme`.
- Gating: `strict or _at_least(contract_version, C1)`, no warning branch.

### 6.4 Configuration and isolation (C1)

- **Target:** the benchmark config declares `target_slabs` (A1, `layered_sim`) or a list of target volumes (from A2, matching placements in the geometry tree).
- **Vacuum:** the world material is `G4_Galactic`, or its density is < 1e-20 g/cm³.
- **Isolated:** the world is vacuum and every placement other than the world belongs to the target; a field attached only inside the target is part of the target and enters the hash; a field extending beyond the target makes it embedded.
- **Derivation and hash versions:**

| Stage | Derived from | `hash_scheme` |
|---|---|---|
| A1 | `layered_sim`'s spec/1 (for `layered_sim` the spec is the actual geometry; A2 checks it against the geometry tree) | `spec-v1` |
| from A2 | the geometry tree of the effective config (any backend) | `tree-v1` |

- Comparisons happen only within the same `hash_scheme`; `dependencies.py` re-derives with the record's `hash_scheme`. J14 uses no target-hash dimension and is unaffected by the switch.
- A backend with declarations only can run and be published but cannot upgrade.
- **Contract rule:** every counted benchmark must be isolated (reference) or match the target hash (setup-matched); `dependencies.py` must re-derive from the run records in `evidence_records` and compare.

### 6.5 Regression and model-to-model (C2)

- **Regression:** the same study with the same settings runs once on each of two versions (plugin, backend or Geant4) (point_id is the version tag, so the samples are independent), and every scalar observable is compared. Three outcomes: `changed` (|diff| − t_{1−α/m}·se_diff > tol), `unchanged` (the pass rule of §6.6), `unresolved`; "not significant" does not mean "unchanged". Histogram comparison is deferred to distribution-level benchmarks. Labels are not affected; a reference observable marked `changed` can trigger a sci-fix check.
- **Model-to-model:** a surrogate never changes the physics label. A surrogate's study declares its reference study (a study record) and scope; decided by IUT (χ² only as a diagnostic). On pass, `extension.study.surrogate` is recorded (reference study's reference and hash, scope the intersection of the two).

### 6.6 Convergence gate (IUT)

- **Difference:** a is the finest setting, b the second-finest; in `relative` mode diff = (a − b)/b and se_diff = √(se_a² + se_b²)/|b|, in `absolute` mode diff = a − b and se_diff = √(se_a² + se_b²) (the two points are independent logical runs); ν by Welch's formula for each pair.
- **Event-count target:** each point's se target is tol/(4√2), so that se_diff ≤ tol/4.
- **Decision:** pass: |diff| + t₀.₉₅(ν)·se_diff ≤ tol, and both points meet their se target; fail (possible even with a missed target): |diff| − t_{1−α/m}(ν)·se_diff > tol, with m the number of (parameter × observable) pairs; otherwise unresolved. For small counts, interval endpoints: pass = the 90 % interval lies within [−tol, tol]; fail = the one-sided 1 − α/m interval lies entirely outside.
- **Reporting:** unresolved and missed targets are `incomplete` (exit 3) and the label stays `unvalidated`; only fail is `failed` (exit 1).

**Operating characteristics** (α = 0.05, 2×10⁶ simulated trials; recompute with `gate_operating_characteristics.py` in this folder; model in task A's A1.8):

| True difference | Pass (se = target) | Pass (two-stage) | Pass (two-stage, given both points met the target) | Fail m = 1 (se = target) | Fail m = 30 (se = target) | Fail m = 30 (two-stage) |
|---|---|---|---|---|---|---|
| 0 | 0.976 | 0.809 | 0.999 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.621 | 0.696 | 0.860 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.044 | 0.054 | 0.050 | 0.002 | 0.002 |
| 2 tol | 0.000 | 0.000 | 0.000 | 0.988 | 0.780 | 0.952 |

At a true difference of tol about 90 % of results are unresolved, which is inherent to an equivalence test. Under the two-stage design about 19 % of point pairs are incomplete because one point missed its target. The independent review of 2026-10-23 found that the old two-stage columns double-counted the trial χ²; they have been recomputed.

### 6.7 Negative controls and the detection limit

- Decision quantity: shift = (control − nominal)/reference, with the SE combined from both runs.
- Detection limit: DL = tol + |rel| + t_{0.977}(ν)·se_rel.
- Caught: the control's benchmark verdict is fail (|rel_c| > tol).
- Design requirement: a toy shows that an injection at the DL is caught with probability ≥ 0.977; the true power is near 0.977, so the acceptance threshold is 0.977 − 3σ_MC (an A1 acceptance condition).
- Realization: inject both signs (otherwise restrict the claim to one sign); at the detection limit = caught and |shift| ≤ 1.1 × DL. A single miss is recorded and explained, does not fail automatically, and the control is never rerun with another seed.

### 6.8 Stopping rule and evidence correlation

- The stopping rule, scan grid, K and B, and the handling of unresolved results are written into the study spec before the first evidence run.
- `extension.study.evidence_overlap` lists runs shared by several decisions.

---

## 7. Contracts, traceability and sci-fix

### 7.1 C1 (A1)

The table, scope and isolation rules of §6.2–6.4; `dependencies.py`'s re-derivation; an optional `simulation` property in `ext_computational_run.json` (needs hep-computing's agreement).

### 7.2 C2 (B2)

The new entries of §6.2 (verification, regression, surrogate); the rules of §6.5; the transitive processing chain of §7.4. Gated like C1.

### 7.3 sci-fix and advisories (A1)

| Defect | Ledger entry | Severity |
|---|---|---|
| D1 (including per-benchmark scope dimensions) | scope-kind | S2 |
| D2 | grade-table | S2 |
| D3 (including the t-based detection limit) | control-shift | S2 |
| D4 (including the definitions of the difference and its se) | gate-IUT | S2 |
| D5 (including block batch means replacing the bootstrap, exact counting intervals, MPV interpolation) | variance-method | **S1** |
| isolation definition (including field and vacuum) | isolation | S2 |
| D6 | stopping-rule | S3 |

One advisory each for S1 and S2 (keys `artifact_types: [computational-run]`, `extension_keys: ["study", "evidence_records"]`; introduced 0.20.0). simulated dataset-records cannot be keyed; the remedy asks holders to run `contracts/dependencies.py` on each simulated table.

### 7.4 Tracing processing chains

- Every processing step (simulation, reduction, digitization and reconstruction, table) writes a computational-run record with `**trace.provenance()`, the configuration hash, hashes of input records and files, and the code hash.
- The input chain of a simulated table can be any depth, as long as every level is a recorded computational-run and every root of the chain is a simulation run (C2; previously only one level).
- When calling a C++ executable, Python records the sha256 of the executable and its sources, the version and the subcommand, and tags the call with `trace.tag()`.

---

## 8. Code and CI

| Location | Change |
|---|---|
| `contracts/validate.py`, `dependencies.py` | §6, §7 |
| `contracts/schema.py` | `maxItems`, `maximum`, `exclusiveMaximum` (needed by `element_sim`'s schema; no contracts version change) |
| `core/stats/`, `core/simulation/` | Block estimators, the decision engine (equivalence, threshold, change, order), distribution functions, summary reading and schemas. They are in `core/` because both hep-detector's scripts and adapters (`geant4`, task C's `detector-design`) need them, and the layering rules let adapters import only `core` and `contracts` (task A §4.4) |
| `skills/hep-detector/scripts/` | inference and decisions read only boundary artifacts; geometry facts (minimum thickness, configuration) come from the effective config, records from before A2 still from spec/1; no new script, `SKILL.md` and description unchanged |
| `adapters/geant4/assets/` | `g4sim/`; `layered_sim/` gains `g4sim`; `geant4_run.py` (logical runs and job splitting, the A1 Python summary producer, B2's `reco` and `table`); B1 `element_sim/` and `simroot`; B2 `simreco` |
| `SIM_SOURCES` | covers `g4sim` and the sources of each program |
| CI | task A needs no new required CI job; a ctest of `SimSummary.hh` can be an optional job. B2's `simreco` needs a required C++17 CI job |

---

## 9. Generality

### 9.1 Use cases covered

| Use case | Supported by | Status |
|---|---|---|
| material-level references (J14-like) | the reference class, isolated slabs | A1 |
| spectrometers with a field (J15, compared with PAMELA and AMS-02) | `element_sim`, the field counted in the target, verification, the reconstruction chain | B1, B2 |
| test beams and modules (compared with data) | the setup-matched class, target hashes from the geometry tree, per-benchmark scope dimensions | contracts in A1 and A2; geometry from a user application or `element_sim` |
| rare events | exact counting intervals | A1 |
| software or Geant4 changes | the regression class | B2 |
| fast simulation, ML surrogates | the surrogate class, reducers | B2 (contracts); reducers at the first need |
| other engines or frameworks (FLUKA, Key4hep) | the output interface, reducers | interface ready; converters deferred |

### 9.2 Interfaces defined now, implemented later

| Interface | Content | First use case |
|---|---|---|
| distribution-level comparison | χ² on summary histograms (statistical uncertainties on both sides; measurement uncertainties when the reference is a measurement) | the first benchmark with a shape as its observable, or the first regression check |
| observable combinations and selections | a linear combination of columns, the ratio of two columns; AND of column-against-constant comparisons | the first study that needs an event selection |
| profiles and 2D histograms | n, Σy, Σy² in bins of x; 2D counts | the first study with a spectrum source; J15 runs at fixed rigidities and does not need it |
| sources | `gps` (declarative settings only), `event-file`; the summary records the source area and solid angle for flux normalization | the first spectrum or flux study |
| `simreduce` | reads event files (through `simroot`) or external formats and writes summaries as declared | the first observable decided after the fact, or the first external backend |

### 9.3 Deferred (with triggers)

| Item | Trigger |
|---|---|
| weighted accumulation and biasing rules | the first study with biasing |
| non-box solids, rotations and GDML input in `element_sim` | the first study that needs them and cannot use a user application |
| rule packs and probes for other engines | the first non-Geant4 backend |
| a reducer for EDM4hep | the first Key4hep backend |
| optical photons, long time windows, decay chains | the first scintillator or rare-event study |
| ion sources and Birks (J17) | a cosmic-ray nuclei study and a literature record for PVT's Birks constant |
| probes for several Geant4 versions | the first application on a version other than 11.4 (the regression class will need it first) |
| `physics_config_comparison` | a study that needs to compare physics settings |
| RNTuple, vector columns | ROOT file size or read speed becomes a bottleneck |

### 9.4 Deliberately not done

- An engine abstraction layer (VMC-style): abstraction at the output is enough, and ALICE's experience shows API-level abstraction is costly.
- A processing framework (Gaudi-style), a validation database and website (geant-val-style): they solve the scale problems of large collaborations and break the plugin's constraints.
- A general expression language, a plug-in system for estimators, one probe content for all engines.
- Integer quantization and bit-identical statistics (§13).
- Topping up, refining or reseeding controls based on results.
- The `uses-validated-physics` label, contracts 4.0, Python bindings, a content-addressed cache, `simstat`, a Geant4-free `simcore`.

---

## 10. Stages and acceptance

### 10.0 What J14 records

| Stage | Recorded content | Replay |
|---|---|---|
| today | reduced CSVs for 5 runs (with an `event` column); the 13 scan and variation runs keep only `geant4-run-summary/1` (one value plus a bootstrap SE); 2.6 MB | pure Python |
| A1 | runs with per-event CSVs: blocks cut offline from the existing CSV, producing and committing `simulation-summary/1` (no re-record); scan and variation runs with single-value summaries only: live re-recorded with `seeding: stream`, committing summaries; new negative controls | from summaries, pure Python |
| A2 | an effective config per run; the regression-check record | as above |

### A1 Correctness fixes (contracts C1, sci-fix)

**Content:** §6.2–6.4, §6.6–6.8, §7.1, §7.3; the statistics of §5.2–5.5; the Python summary producer (from per-event CSVs, blocks by the `event` column); the D8 enums, the D10 tests, protocol section 4.

**Acceptance:**
- [ ] Records with a kind mismatch, a missing declared dimension, a class or grade that disagrees with the table, a missing or embedded configuration, or a mismatched target hash or `hash_scheme` are refused under `--strict` and C1; a mismatch found by `dependencies.py`'s re-derivation is refused.
- [ ] The regenerated J14 study records pass `validate.py --strict` and `dependencies.py`; any change of verdict is recorded with its reason.
- [ ] The gate toy (10⁴ trials per cell) matches the table of §6.6 within ±3σ_MC; the interval-based decision for small counts is tested.
- [ ] Block batch-means coverage toy: for each kind of J14 estimator (mean, fraction, quantile, mode), the actual coverage of a nominal 90 % interval satisfies |coverage − 0.90| ≤ 0.02 + 3σ_MC, reported per kind.
- [ ] The MPV bias toy's 95 % upper bound ≤ tol/10; the per-run empirical check is in force.
- [ ] Detection-limit toy: an injection at the DL is caught with probability ≥ 0.977; J14's realized control results are recorded in VALIDATION.
- [ ] J14's offline replay runs from the committed summaries, its decisions meet §5.6, and it needs neither Geant4 nor a compiler.
- [ ] `python3 -m unittest discover -s tests/contracts -t .` has no errors.
- [ ] Ledger entries and two advisories pass `scifix_advisories.py check`; VALIDATION GEANT4-CORRECTNESS; CHANGELOG; release manifest.

### A2 Shared library and boundary artifacts (adapter 0.2.0)

**Content:** `g4sim` (`SimSeed.hh`, `SimSummary.hh`, `SimProbe.hh`, helpers); `layered_sim` writes the summary, effective config and column map, and supports `seeding: per-event`; the study layer reads only boundary artifacts, with geometry facts from the effective config; `hash_scheme: tree-v1`.

**Acceptance:**
- [ ] Regression check: J14's existing specs produce, on the same host, CSVs bit-identical to those from before A2.
- [ ] With `seeding: per-event`, one logical run executed as 1, 2 and 4 jobs and with 1, 2 and 4 threads gives the same event content; integer accumulators of the summary identical, floating point within a relative difference of 1e-12.
- [ ] The summary written by `layered_sim` agrees with the one Python produces from the same run's observable dump (integers identical, floating point within 1e-12 relative). The dump is a side file switched on only in tests (`%.17g`); the CSV itself is unchanged.
- [ ] The J14 specs rerun for the regression check all have an effective config; the configuration derived with `tree-v1` gives the same verdicts as `spec-v1`; a deliberate disagreement is caught; a run with `recorded: false` cannot upgrade.
- [ ] The thin-layer rules take the minimum thickness from the effective config, reaching the same conclusions for J14 as in A1.
- [ ] An event weight ≠ 1 exits 2.
- [ ] VALIDATION GEANT4-SUMMARY; CHANGELOG; release manifest.

### B1 `element_sim` and event files (adapter 0.3.0)

**Content:** `element_sim` (spec `element_sim.spec/1`: box elements, one level of nesting, `field`, `source.type = gun`, `output.observables`, `output.event_file`); the field (`ConstructSDandField`, thread-local, `delta_intersection` 1e-5 mm, DormandPrince745); the plane-crossing scorer; per-event ROOT files (`G4AnalysisManager`, g4tools, flat ntuples, MT merging, `content_sha256`); `simroot` (starting with one day confirming what `G4RootAnalysisReader` can do).

**Acceptance:**
- [ ] The three boundary artifacts from `element_sim` pass the same interface tests as `layered_sim`'s; on a slab configuration identical to J14's, the observables both backends produce (mean and mode of the silicon deposit, rear-leakage fraction) agree statistically.
- [ ] MT test: each thread's field-manager pointer differs; the field parameters recorded by the probe match the spec.
- [ ] The deterministic field checks (J15's design is in `task-b-j15.md` §4 and B2.5) pass at the nominal settings; the result of every grid point is reported; the B × (1 ± δ) negative control is caught.
- [ ] `simroot` round trip: values of every level and I, D, S columns are identical; with `seeding: per-event`, serial and different thread counts give the same `content_sha256`; the per-event sum of `deposits` equals the CSV's total deposit per subsystem.

### B2 Reconstruction, J15 and C2 (adapter 0.4.0, contracts C2)

**Content:** `simreco` (writing summaries and per-event results); the J15 study (geometry and parameters in `task-b-j15.md` §4: B = 0.5 T, six Si planes, two TOF layers per station, 50 Pb/PVT layers); the validation ladder, calorimeter cut convergence, variations; TOF σ_t sensitivity at 100 and 150 ps; C2 (verification, regression, surrogate, transitive processing chains); the J15 journey and routing case; the J15 README names PAMELA and AMS-02 as the closest real instruments and stresses that J15 is a synthetic geometry.

**Acceptance:** as in `task-b-j15.md` B2.11, plus:
- [ ] `simreco`'s summaries pass the same consistency tests as A2.
- [ ] A processing chain of three or more levels (simulation → reconstruction → table) is accepted by `dependencies.py`; one whose root is not a simulation run is refused.
- [ ] A regression check (J14 on two plugin versions, say) produces a `changed`, `unchanged` or `unresolved` record without affecting labels.
- [ ] Contract tests of the surrogate rule: a record carrying `extension.study.surrogate` that declares `validated-in-scope` is refused.

### C Automated detector design search (proposal; C1 after task A, C2 after task B)

**Content:** the user writes down physics requirements; Claude freely chooses and combines structures from a component catalogue (magnet region, tracker planes, TOF layers, sampling and homogeneous calorimeters, passive layers) and proposes physically motivated seed designs; a standard-library NSGA-II (optional MOBO) searches at three fidelities: F0 analytic formulas, F1 Geant4 with few events, F2 full statistics; reported performance comes only from confirmation runs with independent seeds; contracts C3. Spec in [`task-c-design-search.en.md`](task-c-design-search.en.md).

**Acceptance:** as in `task-c-design-search.en.md` C1.9 and C2.9.

---

## 11. Residual risks

1. J14's detection limits may change with block batch means, t quantiles and controls in observable units, and the controls may need redesigning.
2. Block batch means has an O(1/B) bias for ratios, quantiles and modes of skewed distributions that K does not reduce; the coverage toy allows ±0.02, and B is raised if needed.
3. Block independence fails when state is carried between events; the probe records the relevant settings, and several independent logical runs are used when in doubt.
4. Under the two-stage design about 10 % of evidence runs miss their target (§5.5).
5. With tolerance comparisons, decisions close to a threshold may differ across platforms; handled by margin flags and "the CI platform decides".
6. Two Geant4 programs: `layered_sim` is frozen in maintenance mode, and `g4sim` keeps duplication down.
7. The probe assumes workers match the master; if a thread-local difference appears, dump per thread.
8. When a target hash is matched to a published measurement, the contract can only compare hashes, not decide that the target is the configuration in the paper; a reviewer still checks.
9. The reading ability of `G4RootAnalysisReader` is unverified (the B1 trial).
10. Only 931 bytes of quick-load budget remain; this architecture does not change `SKILL.md` or the description.
11. Effort: the prototype estimates A1's contract part at about 8–12 engineer-days plus Geant4 time; the rest is not estimated.

---

## 12. Decision record

### 12.1 Decided by the user

| Date | Decision | Where |
|---|---|---|
| 2026-10-22 | core code in C++, Python as the interface; compute core in C++, reference values stay in Python; separate executables exchanging JSON/CSV, no Python bindings | principle 2 (as interpreted by item 1 of 12.2) |
| 2026-10-22 | J15's TOF1 and TOF2 two layers each, all four of the same material | B2 |
| 2026-10-22 | detailed per-event information stored in ROOT files | §4.1 T1, B1 |
| 2026-10-22 | J15 split from the rest into a second task, done later | task A (A1, A2), task B (B1, B2) |

### 12.2 Proposals of this document (need the user's confirmation)

1. **Interpreting the language split:** per-event computation (simulation, digitization, reconstruction, accumulation) in C++; inference after merging in Python.
2. **A backend interface at the output** (three boundary artifacts), no engine abstraction layer.
3. **Event determinism:** `seeding: per-event` by default for new specs; job splitting and thread count do not affect events.
4. **Reproducibility means "same decisions"**, with numbers compared within tolerances; no integer quantization and no bit-identical statistics.
5. **Block batch means:** K ≥ 16 blocks by event number within one run; J14 runs with per-event data are recomputed offline without re-recording.
6. **A new `element_sim`**, with `layered_sim`'s spec format unchanged; both share `g4sim`.
7. **Five validation classes**, with regression and surrogate added in C2.
8. **Four stages** (A1, A2, B1, B2), with ROOT files and `simroot` in B1.
9. The two-stage factor F₀.₉₀ or F₀.₉₅; the threshold for exact intervals (any block at 0 or a total < 100).

### 12.3 For the maintainer to decide

1. The version class of C1 (proposed: minor plus a sci-fix).
2. How to confirm the G5 statement that no example code was copied.
3. hep-computing's agreement to the `simulation` property and the transitive processing chains of C2.
4. A required C++17 CI job for B2's `simreco`.
5. Where ROOT files are stored and for how long.
6. A1's live re-record of J14's scan and variation runs, and a limit on the recorded size.
7. Ownership of `element_sim` as a second Geant4 program (hep-detector).

---

## 13. History: superseded designs

| Previous design | Replaced by | Basis |
|---|---|---|
| `simstat` and a Geant4-free `simcore`: moving run-level statistics to C++ | inference stays in Python, reading merged summaries | little code and data, no gain from C++, and replay would need a compiler (soundness assessment P1); CMS DQM also decides only after merging |
| spec/2, `layered_sim convert`, a dual-format accessor, a same-host bit-identical gate | `layered_sim`'s format unchanged; a new `element_sim` | the most costly, least valuable step; a new program leaves J14 untouched and gives a real second backend |
| integer quantization, a two-word 128-bit integer, round half to even, `%.17g` needed for recomputation | compensated floating-point sums; integers only for counts and histograms; reproducibility defined as same decisions | bit identity is not a scientific need; real experiments aim at reproducible events and traceable sources |
| 16 independent processes per evidence run | blocks by event number within one run | batch means is batching within a run; per-event seeds make job splitting irrelevant to statistics |
| per-event seeding forced only for bit identity | per-event seeding as the default for new specs, for event determinism | the practice of ATLAS and Allpix² |
| an interface-only synthetic backend | `element_sim` as a real second backend | third check R19 |
| validation as grades only (reference, sanity, verification, interface) | five validation classes, adding regression and surrogate | geant-val, Belle II, ATLAS AtlFast3 |

Still valid from the previous version (merged here): the fixes of D1–D10, the contracts grade table and per-benchmark scope dimensions, the isolation and field definitions, versioned target hashes, the IUT gate and its t-based operating characteristics, exact counting intervals, MPV interpolation with two bias checks, the t-based detection limit, the two-stage event count, the event-weight restriction, the probe's content and timing, the ROOT file design, J15's design. Of the 25 findings of the third deep check, R11, R12, R16 and R18 no longer apply because the design changed, R19 is resolved by `element_sim`, and the rest are merged.

---

## 14. Sources

- ATLAS Collaboration, *Software and computing for Run 3 of the ATLAS experiment at the LHC*, [arXiv:2404.06335](https://arxiv.org/pdf/2404.06335) (random numbers: §3.1; data formats: §2.3)
- ATLAS Collaboration, *AtlFast3: the next generation of fast simulation in ATLAS*, [arXiv:2109.02551](https://ar5iv.labs.arxiv.org/html/2109.02551)
- CMSSW `RandomNumberGenerator.h` ([LXR](https://cmssdt.cern.ch/lxr/source/FWCore/Utilities/interface/RandomNumberGenerator.h)); DQM `README.md` ([LXR](https://cmssdt.cern.ch/lxr/source/DQMServices/Core/README.md)); `ProcessHistory` ([doxygen](https://cmsdoxygen.web.cern.ch/cmsdoxygen/CMSSW_12_3_2/doc/html/d8/d42/ProcessHistory_8cc_source.html))
- S. Banerjee, V. Ivanchenko (CMS), *Validation of physics models of Geant4 using data from the CMS experiment*, [EPJ Web Conf. CHEP 2021](https://www.epj-conferences.org/articles/epjconf/abs/2021/05/epjconf_chep2021_03010/epjconf_chep2021_03010.html)
- *Simulation in ALICE* (Virtual MC), [physics/0306092](https://ar5iv.labs.arxiv.org/html/physics/0306092)
- Key4hep, *Progress Report on Integrations*, [arXiv:2312.08152](https://arxiv.org/html/2312.08152v1)
- Allpix², [multithreading documentation](https://allpix-squared.docs.cern.ch/docs/04_framework/10_multithreading); [arXiv:1806.05813](https://arxiv.org/pdf/1806.05813)
- *Geant-val: a web application for validation of detector simulations*, [EPJ Web Conf. CHEP 2018](https://www.epj-conferences.org/articles/epjconf/abs/2019/19/epjconf_chep2018_05002/epjconf_chep2018_05002.html)
- Belle II, *Tools for Physics Validation of the Software* ([basf2 documentation](https://software.belle2.org/release-09-00-15/sphinx/_sources/validation/doc/index.rst))
- *The PAMELA Space Experiment*, [arXiv:0905.2551](https://ar5iv.arxiv.org/html/0905.2551)
- *The AMS-02 Time of Flight System*, [astro-ph/0206021](https://ar5iv.labs.arxiv.org/html/astro-ph/0206021)
- hep-research `9f08796`: `adapters/geant4/assets/geant4_build.py` (line 53, `GEANT4_USE_GDML: OFF`), `layered_sim/Actions.cc` (lines 23, 113), `examples/geant4-thin-silicon/recorded/`, `check_geant4_study.py` (line 357), `geant4_benchmarks.py` (line 274)
