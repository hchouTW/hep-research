# hep-research Geant4 study architecture (consolidated)

> Status: architecture proposal consolidating all discussion from 2026-10-21 to 2026-10-22, corrected after the third deep check (§13); awaiting the user's confirmation of the proposals in §11.2 and the maintainer's decisions in §11.3
> Supersedes: `architecture-revision.md` (re-evaluation and generality assessment, now merged here). `task-a-core.md` and `task-b-j15.md` are the implementation specs of the previous architecture and are rewritten per §12 once this document is approved
> Baseline: hep-research `main` at `9f08796` (0.23.0 plus unreleased changes), contracts 3.5.0, adapter geant4 0.1.0, Geant4 11.4.3
> Date: 2026-10-22
> Language: English translation of [`architecture.md`](architecture.md) (Traditional Chinese original), same content

---

## 0. Summary

**The problem.** hep-research's Geant4 study workflow has two kinds of problem. The first is correctness: results can be wrongly labelled `validated-in-scope`, because the scope check skips the observable, the record declares its own benchmark grade, and the statistical rules have holes (D1–D10, §1). The second is structure: the study layer is tied to `layered_sim`'s column names and slab geometry, and cannot take other backends, other geometries or other kinds of study.

**The core of the architecture (five sentences):**
1. **Two planes.** Per-event processing is in C++ (the data plane); inference on tens to hundreds of numbers per run, decisions, records and contracts are in Python (the control plane).
2. **One boundary artifact.** Observables are quantized to integers where the events happen and accumulated into mergeable sufficient statistics, written as `simulation-summary/1` (one per chunk, a few kB, with its own merge rules). Python reads only summaries.
3. **The backend describes itself.** Any backend that delivers a summary, an observable map (the column map) and its actual settings (the effective config, including the actual geometry tree) reaches the gates, benchmarks and labels.
4. **Upgrade-relevant facts are re-derived by the contract from evidence.** Grade, kind, scope dimensions, configuration and target hash are never self-declared.
5. **One variance method.** Every evidence run is split into K ≥ 16 independent chunks and every SE is estimated by batch means; for small counts, exact intervals, with the gate deciding on interval endpoints.

**Stages:**

| Stage | Content | Version |
|---|---|---|
| A1 | correctness fixes (sci-fix), staying in Python: contracts, statistical rules, generalized definitions of scope and isolation; first version of the summary schema, produced by Python from chunk CSVs | contracts C1 |
| A2a | spec/2, `layered_sim convert`, probe (engine-independent envelope, actual geometry tree), dual-format accessor | adapter 0.2.0 |
| A2b | summaries accumulated by C++ during events; per-event reseeding; backend interface; full-precision CSV | adapter 0.3.0 |
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
| before 2026-10-21 | three rounds of independent review (7 reports), checks against 0.21.0 and `9f08796`, a phase-1 prototype | the contracts and statistical rules took shape (§6, §5) |
| 2026-10-22 | user decision: core code in C++, Python only as the interface; separate executables exchanging JSON/CSV | the first version also moved run-level statistics to C++ (`simstat`) |
| 2026-10-22 | user decision: detailed per-event information stored in ROOT files | ROOT files and `simroot` added |
| 2026-10-22 | user decision: J15 split from the rest into a second task, done later | task A and task B |
| 2026-10-22 | soundness assessment | the boundary is in the wrong place (P1–P7 in §1.3) |
| 2026-10-22 | generality assessment | ten places that lock generality in (G1–G10 in §1.3) |
| 2026-10-22 | third deep check (two independent reviewers plus the author's checks) | 25 corrections to statistics, quantization, seeding, replay records, hash versions and more (§13) |

### 1.3 Problems of the previous architecture

**Soundness (P):**

| # | Problem |
|---|---|
| P1 | moving run-level statistics (`mpv()` and `bootstrap()` about 7 lines each; 2.6 MB of data) to C++ gains no speed but makes J14's offline replay need a compiler; across compilers and architectures (FMA contraction on aarch64, say) bit-identical replay may fail; the Python oracle still has to be maintained |
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
| Numbers are reproducible and reviewable | small, hashed, integer-exact intermediate artifacts (§4.2); bit-identical replay on the CI platform, comparison within a relative difference of 1e-12 across platforms (§5.8) |
| The study layer is not tied to one backend, geometry or kind of study | a backend interface made of three boundary artifacts (§4.6) |
| Demonstrate a field, several subsystems and reconstruction | J15 (B1) |

### 2.2 Constraints

- Python uses only the standard library.
- G5 licence boundary: Python exchanges only JSON and CSV with separate executables; no Geant4 example code is copied.
- Layering: skill scripts and adapters import only `core` and `contracts`; no experiment names in `skills/` or `contracts/`.
- Statuses and exit codes (`core/status.py`): 0 ok, 1 a negative verdict, 2 `rejected`, 3 `incomplete`.
- Files ≤ 2 MiB; hep-detector quick load ≤ 25,600 bytes (24,669 now), description ≤ 1,024 characters (1,018 now).
- J14's offline replay must always run and reproduce the committed output bit for bit on the CI platform.

### 2.3 Principles

1. **Correctness before extension.** Nothing new is merged before A1.
2. **The boundary is at sufficient statistics.** Code that processes per-event data is in the data plane (C++); code that processes summaries is in the control plane (Python). One production implementation per quantity; one in the other language may exist only in tests, as an oracle.
3. **Trust the actual state; declarations are only the fallback.** Geometry, field and physics settings are taken from the probe; declarations alone are marked `source: declared` and cannot be used to upgrade.
4. **Upgrade-relevant facts are decided by the contract.** Grade, kind, scope dimensions, configuration and target hash are never self-declared by a record.
5. **The validation grade follows the nature of the reference.** A reference that is an exact consequence of the inputs gives verification (no upgrade); only a physics model Geant4 approximates, or a published measurement, can be reference or sanity.
6. **Stopping rules, grids and chunk counts of evidence are declared in advance.** Topping up, refining and redoing controls are never decided from results.
7. **Exact and order-independent.** Values merged across threads, chunks or machines are first quantized to integers, then accumulated.
8. **Extensible interfaces, implementation only as needed.** No general expression language, no plug-in system.
9. **Look for an existing implementation first.** Reuse `contracts/schema.py`, `tracker_resolution.py`, `multiple_scattering.py`; an oracle never imports the module it tests.
10. **Minimal change.**

---

## 3. Architecture overview

```
Control plane (Python, standard library)
  hep-detector      rules, reference formulas, inference (MPV, batch means, exact intervals, IUT, negative controls), decisions, labels
  adapters/geant4   spec validation, build, run, chunk, records (trace.provenance()), simulated tables;
                    produces summaries from chunk CSVs from A1 (only as the oracle from A2b)
  core              dual-format geometry accessor, trace, status
  contracts         grade and dimension table, scope, configuration and isolation (C1); verification, transitive derived-simulation marker (C2)
        ▲
        │  boundary artifacts (JSON; small, committable, hashable)
        │    summary              simulation-summary/1     (§4.2)
        │    column map           layered_sim.output/2     (§4.4)
        │    effective config     engine-independent envelope + geometry tree (§4.3)
        │
Data plane (C++)
  SimSummary.hh     standard library only: quantization, two-word 128-bit integer accumulators, merging, JSON writer
  SimProbe.hh       depends on Geant4: the probe (settings and geometry tree); shared by layered_sim and users' Geant4 applications
  layered_sim       links Geant4: simulation, scorers, accumulation of observables at the end of each event; per-event CSV;
                    `convert` subcommand (spec/1 → spec/2); (B0) per-event ROOT files; (B1) field and plane crossings
  simroot           (B0) links only Geant4's analysis library: info / dump / hash of ROOT files
  simreco           (B1) no Geant4: per-event digitization and reconstruction, writes summaries and per-event results
  other backends    a user's Geant4 application (including SimSummary.hh and SimProbe.hh) or another engine, delivering the same three boundary artifacts
```

| Component | Language | Stage | Depends on |
|---|---|---|---|
| contract changes | Python | A1 (C1), B1 (C2) | — |
| hep-detector inference and decisions | Python | A1 | — |
| Python summary producer (from chunk CSVs) | Python | A1; from A2b only in tests, as the oracle | — |
| `core/geometry/layered.py` | Python | A2a | — |
| `layered_sim` (with `convert`) | C++ | A2a | Geant4 |
| `SimProbe.hh` | C++ | A2a | Geant4 |
| `SimSummary.hh` | C++ | A2b | standard library only |
| `simroot` | C++ | B0 | Geant4 analysis (g4tools) |
| `simreco` | C++ | B1 | standard library, `SimSummary.hh`, `MiniJson.hh` |

Terms: the **effective spec** is the spec/2 that `layered_sim` actually runs (converted from spec/1 or given directly); the **effective config** is the actual settings read by the probe (§4.3).

---

## 4. Interfaces

### 4.1 spec/2

| Block | Content | Stage |
|---|---|---|
| coordinates | world centre as origin, stacking axis x, mm; `at_mm` is an element's **unshifted** front face in world coordinates, with the shift kept separately in `shift_mm` (centre = (`at_mm` + t/2) + `shift_mm`, the operation order of the old `Detector.cc`); one level of nesting | A2a |
| `elements`, `materials` | elements and materials (mixtures included, order kept) | A2a |
| `field` | reserved in A2a (a non-empty block is rejected with exit 2); B1 implements a uniform field and the accuracy parameters | A2a / B1 |
| `source` | distinguished by `type`: `gun` (A2a); `gps` and `event-file` defined as interfaces only (§9) | A2a |
| `output.observables` | declared observables: source column, quantization step q, bin edges and thresholds as integer multiples of q; used by Python from A1 and by C++ from A2b; combinations and selections are interfaces only (§9) | A1 / A2b |
| `output.event_file` | `level`: `none` (default), `summary`, `hits`, `crossings` | B0 / B1 |
| `run` | threads, seeds, event count; `seeding`: `stream` (the old behaviour, default for specs converted from spec/1) or `per-event` (from A2b, default for new specs; §4.2) | A2a / A2b |

spec/1 is converted to spec/2 by `layered_sim convert`: the same translation unit keeps the floating-point operation order of the old `Detector.cc`, written as `%.17g`. On the same host, old and new must be bit-identical for TestEm3, the TestEm5 mirror and J14 (CSV and hex-float dumps of every placement); because the shift is kept separately, `shift_mm ≠ 0` is bit-identical too. The schema uses only keywords supported by `contracts/schema.py` (A2a adds `maxItems`, `maximum`, `exclusiveMaximum`, with no contracts version change); cross-field rules stay in Python's `cross_field_checks()`.

### 4.2 Summary (`simulation-summary/1`)

One JSON per run (per chunk). The schema name is engine-independent; it differs from the existing `geant4-run-summary/1` written by `summarize` (which after A2b serves only the replay of old records).

| Field | Content |
|---|---|
| `run` | sha256 of spec and effective spec, seeds and `seeding`, chunk index, event count, `summary_version`, the quantization steps, the producer (`python-csv`, `layered_sim`, ...) and its version |
| `observables[]` | per declared observable: semantic name (matching the column map), unit, q, accumulators |
| Quantization | each event is quantized first: X = round(x/q), W = round(w/q_w), with round **half to even** (C++ `std::nearbyint` under `FE_TONEAREST`, Python `round()`); only integer arithmetic afterwards |
| Accumulators | `n`, `ΣW`, `ΣW²`, `ΣW·X`, `ΣW·X²`, `min X`, `max X`, `hist` (edges at integer multiples of q, binned on X; ΣW and count per bin; overflow and underflow separate), `count_if[]` (thresholds at integer multiples of q; ΣW and count); from B1 `profile` and 2D `hist` may appear (§9) |
| Number form | every sum accumulated as a **two-word 128-bit integer** (implemented in `SimSummary.hh` with the standard library only, no compiler extension), written as a decimal string |
| `merge` | each accumulator's merge rule: `sum`, `min`, `max`, `hist` |
| `overflow` | true if any accumulator overflowed; the run is then incomplete (exit 3), with the reason recorded |

**Weights.** `layered_sim`'s deposits are already multiplied by the track weight (`Actions.cc` line 113), while the CSV's `weight` column is only the primary vertex weight. To avoid double weighting, A2b requires the event weight w = 1 (exit 2 otherwise), and the accumulators keep the W fields as an interface; biasing studies (including what an event weight means) are deferred (§9.3).

**Event seeds (A2b).** With `seeding: per-event`, each event reseeds at its start from `H(chunk seed, global event number)`. Serial and MT runs with any thread count then produce the same events, and their summaries are bit-identical. `seeding: stream` keeps the old behaviour (serial: one continuous stream; MT: the master draws per-event seeds in batches) and is used only for specs converted from spec/1 and for the bit-identical comparison.

**Exactness and error.**
- Integer addition is commutative and associative, so results do not depend on thread count, worker merge order, compiler or architecture. Under MT, a custom `G4VAccumulable` merges: each worker calls `G4AccumulableManager::Merge()` in its own `EndOfRunAction`, the master writes in its own `EndOfRunAction`, and master and workers register in the same order.
- Quantization error is propagated to each statistic before comparison with that statistic's tolerance: the error of a mean is ≤ q/2; fractions and `count_if` have none (thresholds are integer multiples of q); quantiles and modes have at most half a bin width plus q/2. Python checks this during inference.
- Default steps: energy 1 eV, length 1 nm, time 1 fs, weight 2⁻²⁰.

**Recomputation and the oracle.** In A1 the Python producer computes summaries from chunk CSVs under the same declarations. From A2b `layered_sim` writes the CSV as `%.17g` (the version of `layered_sim.output/2` is incremented; the old `%.10g` cannot reproduce the quantization); in tests, a summary recomputed by Python from these CSVs must be bit-identical to the one `layered_sim` wrote. CSVs recorded before A2b are not used for this comparison.

### 4.3 Effective config

```
{ "engine": "geant4", "engine_version": "11.4.3", "probe_version": "...",
  "source": "probe" | "declared", "recorded": true, "config_sha256": "...",
  "geometry": { "tree": [...], "tree_sha256": "...", "hash_scheme": "tree-v1" },
  "environment_ref": "<hash of the build record>",
  "sections": { "geant4": { ... } } }
```

| Part | Content |
|---|---|
| envelope | engine-independent; rules are chosen as a rule pack by `engine` (only Geant4's `G4R-*` today) |
| `geometry.tree` | `G4PhysicalVolumeStore` is a flat list in creation order, so the tree is rebuilt from each volume's mother logical volume; each placement records name, copy number, solid type and parameters, material (composition and density), transform, mother, attached field manager and its parameters; numbers in Python's `float.hex()` format. Replica and parameterised volumes record their parameterization rather than expanding copies |
| `sections.geant4` | the full text of `G4EmParameters::StreamInfo` plus parsed fields; per-couple cuts and energy thresholds; energy ranges per process and model; run-manager type and seed mode; `G4UserLimits`, biasing |
| datasets | dataset paths and content hashes are computed once, in the build or environment record; the probe refers to it by `environment_ref` instead of recomputing per chunk |
| timing | master `BeginOfRunAction` (after `RunInitialization`), in `G4State_GeomClosed` with more than 0 couples; otherwise `recorded: false` (layered_sim still exits 0), and the run counts as declarations only and cannot upgrade |
| field | field managers are per thread; the master also calls `ConstructSDandField`, so `layered_sim`'s master sees the field. If the spec declares a field the master cannot see (a user application setting it only on workers, say), the config is marked `source: declared` |
| paths | written through `tilde()` |

Rule and variation model assignments read the probe first; declarations alone are written with `source: declared`; if both exist and disagree, it is an error.

### 4.4 Column map (`layered_sim.output/2`)

For each observable and output column: semantic name, actual column name, unit, operational definition, and the file it lives in (`csv`, which ntuple of `root`, or `summary`); with `column_map_version`. Only declarative operations (rename, unit, sum, filter) are allowed; a conversion that computes something must be a separate recorded step.

### 4.5 Per-event files (B0)

| Item | Rule |
|---|---|
| per-event CSV | the summary table (primary truth, total deposit per subsystem); full precision from A2b |
| ROOT file | written by `layered_sim` through `G4AnalysisManager` (g4tools, no ROOT installation); under MT `SetNtupleMerging(true)` merges into one file; flat ntuples, scalar columns only, every row keyed; layout `layered_sim.events/1` with ntuples `run`, `events`, `deposits`, `hits`; B1 adds `crossings` (`events/2`) |
| row order | not fixed after merging; readers always sort by key |
| hashes | file bytes include the write time and are not bit-identical; the run record keeps the file sha256 (integrity) and the `content_sha256` from `simroot hash` (comparison and provenance); with `seeding: per-event`, serial and any thread count give the same `content_sha256` |
| `simroot` | `info`, `dump` (CSV after sorting by key, `%.17g`), `hash`; links only Geant4's analysis library (`G4RootAnalysisReader`), no run manager |
| readers | Python and `simreco` never parse ROOT; they go through `simroot dump`; researchers may use ROOT or uproot themselves |
| size | not committed; the run record keeps the path, hashes, row count per ntuple and size; `hits` has an event-count limit (`max_events_hits`, default 100) |
| trial | B0 starts with one day confirming that `G4RootAnalysisReader` reads MT-merged, compressed files and string columns; if not, `simroot` reads only flat scalar columns and the strings move to a JSON side file |

### 4.6 Backend interface

To reach the gates, benchmarks and labels, a backend delivers, for a spec/2 (or its own input, with a hash):

1. one summary per chunk (§4.2);
2. a column map (§4.4);
3. an effective config (§4.3). With declarations only (`source: declared` or `recorded: false`), the study can still run and be published but cannot upgrade.

A user's own Geant4 application meets this by including `SimSummary.hh` and `SimProbe.hh`. A2b's acceptance uses an **interface-only synthetic backend** instead: a test fixture that produces the three boundary artifacts from J14's committed data (renamed columns, a different producer name) and must pass J14's gates and benchmarks; it needs no Geant4, so it runs in ordinary CI. Validating with a real user Geant4 application is an optional item of the live tests.

---

## 5. Statistical methods

### 5.1 Chunks and seeds

Every evidence run is K independent chunks, K declared in advance with a minimum of 16. Chunk seeds are `H(study_id, role, point_id, k)` mapped to an integer in [1, 2³¹); with `seeding: stream`, layered_sim's second seed is `start + 1`; no seed pair repeats across a study's run records.

### 5.2 Estimators and SE

- θ_k from each chunk's summary (mean, fraction, ratio, quantile, mode); report θ̄ = the mean.
- **Default SE:** batch means, SE = sd(θ_k)/√K, with K − 1 degrees of freedom.
- **Several observables:** the vector of per-chunk estimates is kept together; covariances between observables are estimated from these vectors.
- **Full-sample values:** means and fractions also from the merged accumulators; the difference from θ̄ goes into the record as a diagnostic.
- **Quantiles:** linear interpolation within a bin of the X histogram; the bin width must be below 1/10 of the observable's tolerance; a quantile that falls in the overflow or underflow bin makes that estimate incomplete.

### 5.3 Small counts

- When: a counting estimator (fraction, `count_if`) has a chunk at 0, or a merged total < 100 (the threshold can be declared).
- All weights 1: Clopper–Pearson for fractions, Garwood for counts, from the merged accumulators; comparing two runs uses the exact conditional binomial interval for the ratio of the two rates, with relative difference = ratio − 1.
- Weights not all 1: a Poisson interval scaled by n_eff, marked approximate in the record.
- There is no SE in these cases; the gate decides on interval endpoints (§5.5), and event planning uses the Poisson variance of the trial run.

### 5.4 MPV

- Per chunk, take the highest bin of the histogram and interpolate the mode with a three-point parabola through it and its neighbours; report the mean of the K modes.
- **Bias limit (at design time):** estimate the bias with a toy at the declared N/K and bin width; the toy's 95 % upper bound must be ≤ tol/10. The toy uses a Landau–Vavilov distribution, checked against the histogram shape of one high-statistics Geant4 run.
- **Empirical check (every time):** the difference between θ̄ and the three-point mode of the merged histogram must be ≤ tol/5 + 2·SE; otherwise that benchmark is incomplete.

### 5.5 Convergence gate

- **The difference:** relative, diff = (a − b)/b, with b the finer setting (the convention of `check_geant4_study.py` line 357); se_diff = √(se_a² + se_b²)/|b| (the two points are independent runs); ν by Welch's formula for each pair (30 for equal variances at K = 16, about 22 at a variance ratio of 4).
- **Event-count target:** each point's se target is tol/(4√2), so that se_diff ≤ tol/4.
- **Decision (intersection-union test):** pass: |diff| + t₀.₉₅(ν)·se_diff ≤ tol; fail: |diff| − t_{1−α/m}(ν)·se_diff > tol, with m the number of (parameter × observable) pairs; otherwise unresolved. For small counts (§5.3), interval endpoints instead: pass = the 90 % interval lies within [−tol, tol]; fail = the one-sided 1 − α/m interval lies entirely outside.
- **Reporting:** unresolved and missed targets are `incomplete` (exit 3) and the label stays `unvalidated`; only fail is `failed` (exit 1).

**Operating characteristics** (α = 0.05, t(30) with an estimated se, 2×10⁶ simulated trials; recompute with `gate_operating_characteristics.py` in this folder):

| True difference | Pass (se = target, worst case) | Pass (se distribution of the two-stage design) | Fail m = 1 (se = target) | Fail m = 30 (se = target) | Fail m = 30 (two-stage design) |
|---|---|---|---|---|---|
| 0 | 0.976 | 0.989 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.621 | 0.830 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.050 | 0.050 | 0.002 | 0.002 |
| 2 tol | 0.000 | 0.000 | 0.988 | 0.780 | 0.933 |

At a true difference of tol about 90 % of results are unresolved; this is inherent to an equivalence test, and the documentation states the expected rate of incomplete results. A1's gate toy uses this table, within ±3σ_MC.

### 5.6 Two-stage event count

N = ceil(N_trial·(SE_trial/target)²·f), with f = F₀.₉₀(K − 1, K_trial − 1) (≈ 1.97 when both are 16). Under this design about 10 % of evidence runs miss their target; a missed target is incomplete and is not topped up. To lower that rate, use F₀.₉₅ instead (≈ 2.40 at 16 and 16; §11.2 item 8).

### 5.7 Negative controls and the detection limit

- The decision quantity is the shift in the observable, shift = (control − nominal)/reference, with the SE combined from both runs.
- **Detection limit:** DL = tol + |rel| + t_{0.977}(ν)·se_rel, the smallest injected error caught with 97.7 % power given the offset already observed.
- **Design requirement:** a toy shows that an injection at the DL is caught with probability ≥ 0.977; this is an A1 acceptance condition.
- **Realized controls:** inject both signs (otherwise restrict the claim to one sign); at the detection limit means caught and |shift| ≤ 1.1 × DL. A single realization that is not caught is recorded as a finding and explained; it does not fail A1 automatically, and the control is never rerun with another seed.

### 5.8 Stopping rule, evidence correlation and platforms

- The stopping rule, scan grid, K and the handling of unresolved results are written into the study spec before the first evidence run.
- `extension.study.evidence_overlap` lists runs shared by several decisions.
- Python's `math` functions depend on the platform's maths library, so t, F and exact-interval quantiles may differ in the last digit across platforms. Bit-identical replay is required only on the CI platform; across platforms the comparison is within a relative difference of 1e-12.

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
- For benchmarks with a target-hash dimension, the declared scope must carry the same `target_geometry_sha256` **and the same `hash_scheme`**.
- Gating: `strict or _at_least(contract_version, C1)`, no warning branch; records at 3.5.0 or below are bound only under `--strict`.

### 6.3 Configuration and isolation (C1)

- **Target:** the benchmark config declares `target_slabs` (A1) or a list of target volumes (from A2a, matching placements in the geometry tree).
- **Vacuum:** the world material is `G4_Galactic`, or its density is < 1e-20 g/cm³.
- **Isolated:** the world is vacuum and every placement other than the world belongs to the target; a field attached only to volumes inside the target is part of the target and enters the target hash; a field extending beyond the target makes it embedded.
- **Source of the derivation and hash versions:**

| Stage | Derived from | `hash_scheme` | Normal form |
|---|---|---|---|
| A1 | `layered_sim`'s spec (for `layered_sim` the spec is the actual geometry, which A2a proves with the placement dump) | `spec-v1` | ordered slabs, thicknesses, transverse sizes, material names and declared compositions; numbers in `float.hex()` |
| from A2a | the geometry tree of the effective config | `tree-v1` | ordered placements, solid parameters, material composition and density as resolved by Geant4, transforms, attached field; numbers in `float.hex()` |

- Comparisons happen only within the same `hash_scheme`; `dependencies.py` re-derives with the record's `hash_scheme`. From A2a new records use `tree-v1`; `spec-v1` records stay valid but cannot be compared with `tree-v1` benchmarks (J14 uses no target-hash dimension and is unaffected).
- Another backend with declarations only can run and be published but cannot upgrade.
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
| D3 (including the new detection-limit definition) | control-shift | S2 |
| D4 (including the definitions of the difference and its se) | gate-IUT | S2 |
| D5 (including batch means replacing the bootstrap, exact counting intervals, a declared K, MPV interpolation) | variance-method | **S1** |
| isolation definition (including the field rule and the definition of vacuum) | isolation | S2 |
| D6 | stopping-rule | S3 |

One advisory each for S1 and S2 (keys `artifact_types: [computational-run]`, `extension_keys: ["study", "evidence_records"]`; introduced 0.20.0). simulated dataset-records cannot be keyed; the remedy asks holders to run `contracts/dependencies.py` on each simulated table.

---

## 7. Code and CI

| Location | Change |
|---|---|
| `contracts/validate.py`, `dependencies.py` | 6.1–6.4 |
| `contracts/schema.py` | `maxItems`, `maximum`, `exclusiveMaximum`; `test_schema_keywords.py` also scans the adapter schemas |
| `contracts/schemas/ext_computational_run.json` | optional free-form property `simulation` (needs hep-computing's agreement) |
| `skills/hep-detector/scripts/` | inference and decisions (§5), reading only summaries; no new script, `SKILL.md` and description unchanged |
| `core/geometry/layered.py` | dual-format geometry accessor (steward hep-detector) |
| `adapters/geant4/assets/` | `geant4_run.py` (`chunk` with the seeds of §5.1, summaries produced from chunk CSVs from A1, B1 adds `reco` and `table`), `layered_sim/` (`convert`, `seeding`, accumulation, full-precision CSV, B0 event files, B1 field and crossings), `SimSummary.hh`, `SimProbe.hh`, B0 `simroot`, B1 `simreco` |
| `SIM_SOURCES` | updated with the new sources so that `sources_sha256` covers them all |
| CI | task A needs no new required CI job; a ctest of `SimSummary.hh` can be an optional job. B1's `simreco` needs a required C++17 CI job |
| trace | new record writers call `trace.provenance()`; new shared functions call `trace.tag()`; calls to C++ executables record the sha256 of executable and sources, the version and the subcommand |

---

## 8. Stages and acceptance

### 8.0 What J14 records at each stage

| Stage | Recorded content added or changed | Replay |
|---|---|---|
| today | one reduced CSV each for 5 runs (`events/`, 5 columns); the 13 scan and variation runs keep only `geant4-run-summary/1` (one value plus a bootstrap SE); 2.6 MB in total | pure Python |
| A1 | every evidence run (scans, variations, nominal, controls) live re-recorded as K = 16 chunks; each chunk commits a Python-produced `simulation-summary/1` (a few kB); benchmark runs also keep reduced CSVs. Expected total still a few MB; measured in A1 and bounded by `check_packaging.py` | from summaries, pure Python |
| A2a | an effective config per run; the record of the same-host bit-identical comparison | as above |
| A2b | live re-record: `seeding: per-event`, C++-produced summaries, full-precision CSVs (for the oracle test) | from summaries, pure Python |

### A1 Correctness fixes (contracts C1, sci-fix)

**Content:** §6.1–6.3 (derived from the spec in A1, `hash_scheme: spec-v1`), §6.5; all statistical rules of §5; the first version of the summary schema and the Python producer (from chunk CSVs); the D8 enums, the D10 tests, protocol section 4; the `simulation` property.

**Acceptance:**
- [ ] Records with a kind mismatch, a missing declared dimension, a grade that disagrees with the table, a missing or embedded configuration, or a mismatched target hash or `hash_scheme` are refused under `--strict` and C1; a mismatch found by `dependencies.py`'s re-derivation is refused.
- [ ] The regenerated J14 study records pass `validate.py --strict` and `dependencies.py`; any change of verdict is recorded with its reason.
- [ ] The gate toy (10⁴ trials per cell) matches the table of §5.5 within ±3σ_MC; unresolved is reported with exit 3; the interval-based decision for small counts is tested.
- [ ] Batch-means coverage toy: for each kind of J14 estimator (mean, fraction, quantile, mode), the actual coverage of a nominal 90 % interval satisfies |coverage − 0.90| ≤ 0.02 + 3σ_MC, reported per kind.
- [ ] MPV: the bias toy's 95 % upper bound ≤ tol/10; the per-run empirical check (§5.4) is in force.
- [ ] Detection limit: a toy shows an injection at the DL is caught with probability ≥ 0.977; J14's realized control results are recorded in VALIDATION.
- [ ] `python3 -m unittest discover -s tests/contracts -t .` has no errors.
- [ ] Ledger entries and two advisories pass `scifix_advisories.py check`; VALIDATION GEANT4-CORRECTNESS; CHANGELOG; release manifest.

### A2a spec/2 and probe (adapter 0.2.0)

**Content:** §4.1 (reserved `field`, `source.type = gun`, `shift_mm` kept separately), `layered_sim convert`, the §4.3 probe (`SimProbe.hh`), the dual-format accessor, schema keywords and `cross_field_checks()`.

**Acceptance:**
- [ ] Bit-identical on the same host (CSV, placement dumps), including specs with `shift_mm ≠ 0`.
- [ ] A non-empty `field` is rejected with exit 2.
- [ ] Every J14 run has an effective config; the configuration derived with `tree-v1` agrees with the one derived with `spec-v1` (different hashes, same verdict); a deliberate disagreement is caught.
- [ ] The probe writes `recorded: false` at the wrong time (test command), and that run cannot upgrade.
- [ ] The accessor gives the same result for spec/1 and spec/2; both thin-layer rules fire for both formats.
- [ ] `contracts.schema.validate()` plus `cross_field_checks()` reach the same verdicts as the old `validate_spec()`.
- [ ] J14 re-recorded on E2; VALIDATION GEANT4-SPEC2.

### A2b Summaries from C++ and the backend interface (adapter 0.3.0)

**Content:** `SimSummary.hh`, accumulation during events and MT merging, `seeding: per-event`, full-precision CSV, column map; a live re-record of J14; the synthetic-backend test.

**Acceptance:**
- [ ] With `seeding: per-event` and the same seed, serial runs and MT runs with 1, 2 and 4 threads give bit-identical summaries.
- [ ] Merging chunk summaries in any order gives the same result, equal to Python's accumulation from those chunks' full-precision CSVs.
- [ ] A summary recomputed by Python from the full-precision CSV is bit-identical to the one `layered_sim` wrote (the conventions for quantization, rounding, bins and thresholds are all tested).
- [ ] Overflow is detected and the run is incomplete; an event weight ≠ 1 exits 2; the per-statistic quantization-error check works.
- [ ] J14's offline replay reproduces the committed output bit for bit on the CI platform and runs where no compiler is installed.
- [ ] The synthetic backend (delivering only the three boundary artifacts) passes J14's gates and benchmarks.
- [ ] In production code summaries are produced only by C++; the Python producer is used only in tests, as the oracle.
- [ ] VALIDATION GEANT4-SUMMARY; CHANGELOG; release manifest.

### B0 Per-event ROOT files (adapter 0.4.0)

**Content:** §4.5; the `G4RootAnalysisReader` trial first.

**Acceptance:**
- [ ] With `level = none` the output is bit-identical to A2b's; switching on `summary` changes neither the CSV nor the summary.
- [ ] `simroot` round trip: values of every level and I, D, S columns are bit-identical; with `seeding: per-event`, serial and different thread counts give the same `content_sha256`.
- [ ] The per-event sum of `deposits` in the ROOT file equals the CSV's total deposit per subsystem; `hits` above the limit exits 2; an interrupted run is incomplete.

### B1 J15 minimal spectrometer (adapter 0.5.0, contracts C2)

**Content:** J15's design is in `task-b-j15.md` §4 (geometry, parameters, acceptance: B = 0.5 T, six Si planes, two TOF layers per station, a 50-layer Pb/PVT calorimeter); the field (`ConstructSDandField`, thread-local, `delta_intersection` 1e-5 mm, DormandPrince745); the plane-crossing scorer and the `crossings` ntuple; `simreco` (writing summaries and per-event results); the validation ladder (`field-propagation` and others), deterministic field checks, calorimeter cut convergence, variations; `verification` and the transitive marker (C2); the J15 journey and routing case.

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
| rare events | exact counting intervals | A1 |
| biasing, event weights | the W fields of the accumulators (interface) | interface in A2b; A2b requires w = 1, the meaning of weights and the rules deferred |
| other engines, fast simulation, ML surrogates | the three boundary artifacts, the engine-independent effective-config envelope | interfaces in A2a and A2b; rule packs deferred |

### 9.2 Interfaces defined now, implemented later

| Interface | Content | First use case |
|---|---|---|
| observable combinations and selections | a linear combination of columns, the ratio of two columns; AND of column-against-constant comparisons. Anything more is a recorded program step | the first study that needs an event selection |
| profiles and 2D histograms | n, ΣW·Y, ΣW·Y² in bins of x; 2D ΣW | the first study with a spectrum source (resolution against continuous rigidity, say); J15 runs at fixed rigidities and does not need it |
| sources | `gps` (`G4GeneralParticleSource`, declarative settings only), `event-file` (HepMC and others); the summary records the source area and solid angle for flux normalization | the first spectrum or flux study |
| `simreduce` | reads ROOT event files and writes summaries as declared, so observables decided later need no rerun | the first need after B0 |

### 9.3 Deferred (with triggers)

| Item | Trigger |
|---|---|
| non-slab geometry in `layered_sim` (GDML, cylinders, rotations) | the first study that needs non-slab geometry and cannot use a user application |
| rule packs and probes for other engines | the first non-Geant4 backend |
| biasing and event weights (meaning of weights, minimum n_eff, related rules) | the first study with biasing |
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
- Stopping adaptively on the SE, refined scans as evidence, or rerunning an uncaught control with another seed (optional stopping).
- The `uses-validated-physics` label, contracts 4.0, Python bindings, a content-addressed cache.
- Moving statistics to C++ (`simstat`) and a Geant4-free `simcore` project (task A does not need them).

---

## 10. Residual risks

1. J14's detection limits may change with batch means, t quantiles and controls in observable units, and the controls may need redesigning.
2. Batch means has an O(1/events per chunk) bias for ratios, quantiles and modes of skewed distributions that K does not reduce; the coverage toy allows ±0.02, and the events per chunk are raised if needed.
3. Under the two-stage design about 10 % of evidence runs miss their target and are incomplete (§5.6).
4. The MPV bias toy uses a model distribution; the empirical check (§5.4) is the second line of defence.
5. The interface of a custom `G4VAccumulable` with MT merging is confirmed from the 11.4.3 source; its behaviour still needs an MT test.
6. A1 needs a live re-record of every J14 evidence run as 16 chunks; Geant4 initialization time and recorded size are measured in A1.
7. The probe assumes workers match the master; if a thread-local difference appears, dump per thread.
8. When a target hash is matched to a published measurement, the contract can only compare hashes, not decide that the target is the configuration in the paper; a reviewer still checks.
9. The reading ability of `G4RootAnalysisReader` is unverified (B0 trial).
10. Only 931 bytes of quick-load budget remain; J15 does not change `SKILL.md` or the description.
11. Effort: the prototype estimates A1's contract part at about 8–12 engineer-days plus Geant4 time; the changes of statistical method and the summary producer, A2a, A2b, B0 and B1 are not estimated.

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

1. **Interpreting the language split:** the "core" is per-event computation, in C++; inference on summaries is in Python. No `simstat` and no `simcore` project.
2. **The boundary artifact becomes `simulation-summary/1`** (quantized during events, 128-bit integer accumulation, with its own merge rules); produced by Python from chunk CSVs in A1 and by C++ from A2b; J14 replays from summaries.
3. **Every SE uses batch means** (K ≥ 16, declarable), dropping the bootstrap; exact intervals for small counts; MPV by three-point interpolation with a bias limit and an empirical check; the detection limit uses t quantiles. This widens the D5 sci-fix (S1).
4. **ROOT files and `simroot` move to B0**, together with their first consumer, `simreco`.
5. **Five stages** (A1, A2a, A2b, B0, B1), each merged on its own.
6. **Generalization in C1:** per-benchmark scope dimensions, the isolation definition with the field counted in the target, versioned target hashes; configuration from the geometry tree from A2a; an engine-independent effective-config envelope; the derived-simulation marker made transitive in C2.
7. **`seeding: per-event` in A2b** (each event reseeded from H(chunk seed, event number)), so serial and MT give the same results; the old `stream` mode stays only for spec/1 conversion and the bit-identical comparison.
8. The two-stage factor F₀.₉₀ (about 10 % miss their target) or F₀.₉₅ (about 5 %, with about 22 % more events).
9. Default quantization steps (1 eV, 1 nm, 1 fs, weight 2⁻²⁰) and the threshold for exact intervals (any chunk at 0 or a total < 100).

### 11.3 For the maintainer to decide

1. The version class of C1 (proposed: minor plus a sci-fix).
2. Whether a statistical comparison is acceptable if bit identity fails even on the same host.
3. How to confirm the G5 statement that no example code was copied.
4. hep-computing's agreement to the `simulation` property and the transitive derived-simulation marker of C2.
5. A required C++17 CI job for B1's `simreco`.
6. Where ROOT files are stored and for how long.
7. The size of A1's live re-record of J14 (every evidence run as 16 chunks) and a limit on the recorded size.

---

## 12. Mapping to the current task specs, and next steps

| Current spec | This architecture |
|---|---|
| `task-a-core.md` A1.1–A1.3 (contracts) | A1, plus per-benchmark scope dimensions, the field and vacuum definitions of isolation, `hash_scheme` |
| A1.4–A1.10 (statistics and other fixes) | A1, with batch means replacing the bootstrap, the definitions of the difference and its se, exact intervals, MPV interpolation with two bias checks, a t-based detection limit, declarable K; the summary schema and the Python producer |
| A1.11 (sci-fix) | §6.5 (D5 widened into variance-method; a new isolation entry) |
| A2.2–A2.7 (spec/2, conversion, accessor, schema, probe, column map) | A2a (conversion becomes `layered_sim convert`; `shift_mm` kept separately; the probe gains the envelope and the geometry tree) |
| A2.8 (`simcore`, `simstat`) | dropped; inference stays in Python; summaries produced by C++ from A2b |
| A2.9–A2.10 (ROOT files, `simroot`) | B0 |
| all of `task-b-j15.md` | B1 (`crossings` defined as an interface in B0, implemented in B1; `simreco` writes summaries; the C2 marker becomes transitive) |

**Steps after approval:**
1. Rewrite `task-a-core.md` (A1, A2a, A2b) and `task-b-j15.md` (B0, B1) from this document, both languages together, in the current implementation-spec format (task card, terms, hard rules, work items, acceptance, order of work).
2. Update `README.md`.
3. Review the rewritten specs independently once more.

---

## 13. Third deep check (2026-10-22)

### 13.1 Method

Two reviewers who did not write the document checked, separately, the statistical design (including recomputing the operating characteristics with 2×10⁶ simulated trials) and Geant4 and implementation feasibility (including reading Geant4 11.4.3 source and this repository's code). The author listed findings independently and checked the reviewers' main claims against the code: the CSV is written as `%.10g` (`Actions.cc` line 23); deposits are already multiplied by the track weight (line 113); the contents of `recorded/` (5 reduced CSVs, single-value summaries for the rest, 2.6 MB); the gate's relative difference (`check_geant4_study.py` line 357); the detection-limit formula (`geant4_benchmarks.py` line 274); the order of operations for shifts (`Detector.cc` line 89).

### 13.2 Findings and handling

| # | Finding | Source | Handling |
|---|---|---|---|
| R1 | the operating-characteristics table was computed with z and a known se, not the rule (t, estimated se); A1's gate-toy acceptance could therefore never pass (the m = 30 cell is off by about 16σ) | statistics review (CONFIRMED) | §5.5 table replaced by t and estimated-se values, plus values under the two-stage design |
| R2 | the table assumes se = target, while the two-stage design misses the target about 10 % of the time and has a mean se of about 0.18 tol | statistics review | §5.5 table gains a column; §5.6 states the miss rate; §11.2 item 8 |
| R3 | exact intervals give no se, so the gate and the event-count formula are undefined for small counts; no exact method for a difference of two counts | author, statistics review | §5.3 and §5.5 decide on interval endpoints; comparisons use the conditional binomial method |
| R4 | exact intervals do not apply to weighted counts | statistics review | §5.3 uses them only when all weights are 1 |
| R5 | the quantization bound n·q/2 compared the error of a sum with the tolerance of a mean; products, rounding mode and whether bins are quantized were undefined | statistics and feasibility reviews | §4.2: quantize first, then integer arithmetic; round half to even; bin edges and thresholds at integer multiples of q; error propagated per statistic |
| R6 | the gate's difference (absolute or relative), its se and the per-point target were undefined | statistics review | §5.5 defines the relative difference, se_diff and the per-point target tol/(4√2) |
| R7 | the detection limit was not redefined for the new method; a single control realization misses with 3–5 % probability | statistics review | §5.7 uses t_{0.977}; power verified by a toy; a single miss is recorded, not a failure, with no reseeding |
| R8 | the coverage criterion tested exactly 0.90, which O(1/n) bias of skewed estimators makes fail with enough toys | statistics review | §8 A1 uses ±0.02 + 3σ_MC, reported per kind |
| R9 | the MPV bias toy uses a model distribution, not Geant4; no rule for the toy's own uncertainty | statistics review | §5.4 uses the 95 % upper bound, checked against high-statistics Geant4; a per-run empirical check added |
| R10 | quantiles in overflow bins, a trial K different from K, Welch ν not always 30 | statistics review | §5.2, §5.6, §5.5 |
| R11 | serial and MT cannot be bit-identical (serial does not reseed per event); "merging chunks equals a single run" does not hold | author, feasibility review (CONFIRMED) | new `seeding: per-event` (§4.1, §4.2); A2b acceptance rewritten |
| R12 | a `%.10g` CSV cannot reproduce quantized summaries bit for bit | feasibility review (CONFIRMED) | CSV as `%.17g` from A2b; the oracle uses only CSVs recorded afterwards |
| R13 | deposits already carry the track weight, so ΣW·X would weight twice | feasibility review (CONFIRMED) | A2b requires event weight = 1; the meaning of weights deferred |
| R14 | J14's `recorded/` cannot support batch means in A1; A2b needs a live re-record; "J14's verdicts do not change" contradicts a possible control redesign | author, feasibility review (CONFIRMED) | new §8.0, recorded content per stage; summaries produced by Python and committed from A1; acceptance now "changes recorded and explained" |
| R15 | target hashes derived from the spec and from the geometry tree must differ; "vacuum" and the hex-float spelling undefined | author, feasibility review | §6.3 adds `hash_scheme` (`spec-v1`, `tree-v1`), a definition of vacuum and the `float.hex()` format |
| R16 | int128 is a compiler extension, not standard C++17; Python and C++ round differently by default | statistics and feasibility reviews | §4.2: a two-word 128-bit integer implemented in place; half to even on both sides |
| R17 | Python's maths functions depend on the platform, so replay is not bit-identical across machines | feasibility review | §2.1, §5.8: bit identity only on the CI platform; relative difference ≤ 1e-12 across platforms |
| R18 | with `shift_mm ≠ 0`, the new centre formula changes the operation order | feasibility review (CONFIRMED) | §4.1 keeps the shift separately, with the same operation order |
| R19 | the "probe header" was missing from the component table; a "second backend" passing physics benchmarks must be a Geant4 application, which needs Geant4 in CI | feasibility review | §3 adds `SimProbe.hh`; §4.6 uses an interface-only synthetic backend |
| R20 | hashing GB of datasets in every chunk is too costly; field managers are per thread, so the master may not see the field | feasibility review | §4.3: datasets hashed once in the build record; an unseen field marks the config declared |
| R21 | `G4PhysicalVolumeStore` is a flat list; copy numbers of replica and parameterised volumes are ambiguous | feasibility review | §4.3 rebuilds the tree from mother logical volumes; parameterised volumes record their description |
| R22 | `G4AccumulableManager::Merge()` acts only on workers, in the order they finish | feasibility review (CONFIRMED) | §4.2 states where it is called and the registration order; integer accumulation makes order irrelevant |
| R23 | MT per-event seeds are drawn in batches, not all "in advance" | feasibility review (CONFIRMED) | §4.2 wording corrected |
| R24 | terms: effective spec and effective config mixed; `layered_sim.summary/1` tied to one backend and clashing with `geant4-run-summary/1`; the effect of `recorded: false` undefined | feasibility review | §3 defines the terms; renamed `simulation-summary/1`; `recorded: false` cannot upgrade |
| R25 | correlations between observables are "handled automatically" only if the per-chunk estimate vectors are kept | statistics review | §5.2 says so |

### 13.3 Not yet done

- The corrected text has not been independently reviewed again; it will be, together with the rewritten task specs (§12 step 3).
- The reviewer's simulation script is now in this folder (`gate_operating_characteristics.py`, needs numpy and scipy, a design aid only); when the task specs are rewritten, the operating-characteristics toy is rewritten with the standard library and added to A1's tests.
