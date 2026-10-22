# Geant4 study architecture: re-evaluation and a new architecture

> Status: proposal, for the user and the maintainer to decide. Once approved, `task-a-core.md` and `task-b-j15.md` are rewritten (both languages)
> Date: 2026-10-22
> Basis: the current task A and task B specs (`0d815d6`) and the code facts checked at `9f08796` (§1.2)
> Language: English translation of [`architecture-revision.md`](architecture-revision.md) (Traditional Chinese original)

---

## 0. Conclusion

The **contracts and statistical rules** of the current architecture (task A, phase 1) are right and should stay. What needs redoing is **where computation happens and through which interface it is exchanged**.

The new architecture splits the system into two planes with one small, versioned artifact between them:

- **Data plane (C++):** all per-event processing: simulation, scorers, per-event output (CSV, ROOT), and accumulating the data into **mergeable sufficient statistics** where the events happen.
- **Control plane (Python):** specs, workflow, inference on the sufficient statistics (MPV, SE, gates, negative controls), reference formulas, decisions, records, contracts.
- **Boundary artifact:** one `run summary` per run (per chunk), schema `layered_sim.summary/1`. It holds only counts, integer-accumulated sums and sums of squares, minima and maxima, and histograms; it is a few kB and can be committed, hashed and replayed.

This split gives four benefits:

1. J14's offline replay stays **pure Python and bit-identical**, with no compiler needed.
2. Accumulation is done in integers, so results do not depend on thread count, chunk order or compiler.
3. A backend reaches the study layer by delivering a summary, a column map and an effective config, which is more general than the "fake backend that only renames columns".
4. Task A no longer needs a Geant4-free C++ project or a new required CI job.

Two changes of method:
- Every SE is estimated with **batch means over K = 16 chunks**, replacing the bootstrap. The MPV needs K = 16 anyway, so no events are added, and a whole counter-hash bootstrap goes away.
- The MPV is found from the histogram by **three-point parabolic interpolation**, with a **bias limit**: a toy shows |bias| ≤ tol/10.

Section 10 tests generality against five kinds of use case: the boundary artifact itself is engine-independent, but ten places would lock generality in (source of geometry, scope dimensions, the field definition of isolation, weights, one-dimensional observables and more); eight of them are recommended for a cheap fix now.

These changes reinterpret the user's decision "core code in C++": **per-event computation is in C++; only inference on tens to hundreds of numbers is in Python.** The user is asked to confirm (§7).

---

## 1. Re-evaluation

### 1.1 Goals and the real constraints

| Goal | Guaranteed by |
|---|---|
| `validated-in-scope` cannot be obtained wrongly | facts the contract can re-derive from evidence (grade, kind, configuration, scope) |
| Numbers are reproducible and reviewable | small hashed intermediate artifacts; replay independent of the machine |
| The study layer is not tied to one backend | an explicit backend interface |
| Demonstrate a field, several subsystems and reconstruction | J15 (task B) |

Real constraints: Python uses only the standard library; the G5 boundary (separate executables exchanging JSON/CSV); files ≤ 2 MiB; J14's offline replay currently reproduces the committed output bit for bit (`tests/examples/test_geant4_thin_silicon.py`) without Geant4 or a compiler.

### 1.2 Checked facts

| Fact | Source |
|---|---|
| `mpv()` and `bootstrap()` are about 7 lines each; `check_geant4_study.py` and `geant4_benchmarks.py` total 1,465 lines | `geant4_benchmarks.py` lines 197, 204 |
| J14's recorded data is 2.45 MB; Python handles it in milliseconds | `examples/geant4-thin-silicon/recorded/` |
| J14's offline replay is pure Python and reproduces the committed `output/` bit for bit | docstring of `examples/geant4-thin-silicon/run.py` |
| `layered_sim` runs MT with `G4RunManagerType::MTOnly`, seeds set on the master | `layered_sim.cc` lines 150–154 |
| hep-computing's partition merge decides additivity by name tokens (`NON_ADDITIVE_TOKENS`) | `core/partition/engine.py` line 381 |

### 1.3 Problems of the current architecture

| # | Problem | Consequence |
|---|---|---|
| P1 | run-level statistics (MPV, bootstrap, differences) moved to C++ (`simstat`) | little code and little data, so no speed gain from C++; J14 replay then needs a compiler; across compilers and architectures (FMA contraction on aarch64, say) bit-identical replay may fail; the Python oracle still has to be maintained, so there are really two implementations |
| P2 | phase 2 bundles spec/2, conversion, scorer refactor, probe, column map, the statistics port, the accessor, schema, ROOT and `simroot` | if any item stalls (most likely bit identity) all of it waits; ROOT has no consumer in task A and is designed blind |
| P3 | the sub-run MPV is the mean of 16 mode estimates, whose finite-sample bias does not average away with K | only recorded, no limit; the bias may eat part of the benchmark tolerance |
| P4 | two SE methods (sub-runs and a counter-hash bootstrap) and two two-stage factors (1.97 and 1.2) | rules and code more complex than needed; the bootstrap needs globally unique event keys and duplicate checks |
| P5 | the "backend interface" is really a column map plus a per-event CSV | a new backend must still produce a per-event table with the right column semantics; per-event data grows with the event count |
| P6 | chunk values are merged by the partition through name tokens | a new column name can be silently summed (`mpv` is one case already) |
| P7 | task A needs a new Geant4-free C++ project and a required CI job | one of the maintainer's open decisions; the adapter has no required CI job today |

P1, P4, P5 and P6 share one root cause: **the boundary is in the wrong place.** Today Python receives per-event data, so the statistics are either computed in Python over many events or moved wholesale to C++. Moving the boundary to "mergeable sufficient statistics" removes all four together.

---

## 2. New architecture

### 2.1 Two planes

```
Control plane (Python, standard library)
  hep-detector   rules, reference formulas, inference (MPV, batch-means SE, IUT, negative controls), decisions, labels
  adapter        spec validation, build, run, chunk, records (trace.provenance())
  contracts      grade table, scope, configuration, isolation rule (C1); verification, derived-simulation marker (C2)
        ▲
        │  run summary (layered_sim.summary/1) + column map + effective_config (JSON; small, committable, hashable)
        │
Data plane (C++)
  layered_sim    Geant4 simulation, scorers, probe; at the end of each event, observables accumulated into integer
                 accumulators; per-event CSV (summary) and ROOT file (detail, task B); `convert` subcommand (spec/1 → spec/2)
  simroot        (task B) reads ROOT files: info / dump / hash
  simreco        (task B) per-event digitization and reconstruction; writes another summary and per-event results
```

**Dividing rule (replacing the wording of principle 11):** code that processes per-event data is in C++; code that processes run summaries (at most a few hundred numbers per run) is in Python. One production implementation per quantity.

### 2.2 Boundary artifact: the run summary

One JSON per run (per chunk), schema `layered_sim.summary/1`:

| Field | Content |
|---|---|
| `run` | sha256 of spec and effective spec, seeds, chunk index, event count, `summary_version`, quantization units |
| `observables[]` | one entry per declared observable: semantic name (matching the column map), unit, quantization step q, accumulators |
| Accumulators | `n` (count), `sum` (Σ round(x/q), int64), `sum2` (Σ round(x/q)², int128, written as a decimal string), `min`, `max`, `hist` (declared fixed bins; overflow and underflow counted separately), `count_if[]` (counts above declared thresholds, for tail and leakage fractions) |
| `merge` | each accumulator's merge rule: `sum`, `min`, `max`, `hist`; nothing guessed from names |

Properties:
- **Exact and order-independent.** Integer addition is commutative and associative, so results do not depend on thread count, worker merge order, compiler or architecture. Under MT, a custom `G4VAccumulable` merges through `G4AccumulableManager::Merge()`.
- **Small, bounded quantization error.** At most q/2 per event; q is declared in the spec, for example 1 eV for energies.
- **Small.** A J14 run is a few kB (mostly histograms) and can be committed directly.
- **Recomputable.** Observable definitions (which scorer column, bins, thresholds) are declared in spec/2's `output.observables`; Python can recompute a summary from a committed per-event CSV, as the oracle in tests.

### 2.3 Backend interface

A backend reaches the gates, benchmarks and labels by delivering three things for a spec/2:

1. a `run summary` (`layered_sim.summary/1`);
2. `column_map.json` (`layered_sim.output/2`): semantics, units and operational definitions of the observables;
3. `effective_config`: probe output, or declarations marked `source: declared`.

A user's own Geant4 application can include a standard-library-only header (accumulators plus JSON writer, shared with `layered_sim`) to produce the summary. This replaces the "fake backend that only renames columns" acceptance and gives the deferred "embeddable probe" a natural shape.

---

## 3. Methods

### 3.1 One variance method: batch means

- Every evidence run is K = 16 independent chunks (seeds `H(study_id, role, point_id, k)`), with one summary per chunk.
- For any observable θ (mean, fraction, quantile, MPV): compute θ_k per chunk, report θ̄ = the mean, SE = sd(θ_k)/√16, t₁₅ quantiles; the difference of two estimates uses Welch's approximation (about ν = 30).
- Means and fractions can also be computed for the full sample from the merged accumulators; the difference goes into the record as a diagnostic.
- Quantiles come from the histogram by linear interpolation within a bin, with resolution limited by the bin width; the bin width is declared in the spec and must be below 1/10 of the observable's tolerance.
- **Dropped:** the counter-hash bootstrap, globally unique event keys and their duplicate checks, and the second two-stage factor (1.2). Only f = F₀.₉₀(15,15) ≈ 1.97 remains.
- Cost: t₁₅ is about 6.6 % wider than z; every scan point and control needs 16 processes (extra Geant4 initialization time; no extra events).

### 3.2 MPV

- In each chunk's histogram (declared fixed bins), take the highest bin and find the mode by **three-point parabolic interpolation** with its two neighbours. This removes most of the discretization bias of taking the bin centre.
- Report the mean of the 16 chunk modes and its SE (3.1).
- **Bias limit (new):** at the declared N/K and bin width, a Landau–Vavilov toy shows |E[θ̄] − true mode| ≤ tol/10; if not, increase the events per chunk or change the bin width and re-declare (before the first evidence run).

### 3.3 Spec conversion inside `layered_sim`

- A `layered_sim convert` subcommand converts spec/1 to spec/2 with the same code as the old `Detector.cc` (same translation unit, same floating-point operations), written as `%.17g`.
- This keeps the reason for the original `simspec` (the same double arithmetic) without another C++ project; the conversion test and the bit-identical comparison need Geant4 anyway, so both are live tests.
- The dual-format geometry accessor in Python is unchanged (J14's records always replay).

### 3.4 ROOT files and `simroot`

- The decision stands: detailed per-event information goes to ROOT files (g4tools, no ROOT installation), flat ntuples keyed by `event_id`, content hash `content_sha256`.
- The timing changes: ROOT files and `simroot` move to **the first stage of task B (B0)**, designed and accepted together with their first consumer, `simreco`. Task A does not need them (J14's `level` is `none`).
- B0 starts with a one-day trial of `G4RootAnalysisReader` (MT merging, compression, string columns) before the `simroot` interface is fixed.

### 3.5 C++ projects and CI

- Task A has only `layered_sim` (links Geant4). The accumulators and the JSON writer are a standard-library-only header that a small ctest can check in CI without Geant4 (an optional CI job).
- The Geant4-free C++ project (`simreco`) and its required CI job appear only in task B.

---

## 4. New stages

| Stage | Content | Version | Replay |
|---|---|---|---|
| **A1** correctness fixes (sci-fix) | contracts: grade table, scope by kind, configuration and the isolation rule (C1); IUT gate and incomplete; negative controls by shift, both signs; stopping rule declared in advance; seeds H; D8, D10. Statistics: batch means over K = 16 chunks for every SE (replacing the bootstrap), MPV by parabolic interpolation with the bias limit; computed in Python from the chunk CSVs | contracts C1 | pure Python |
| **A2a** spec/2 and conversion | reading spec/2, `layered_sim convert`, bit-identical comparison, dual-format accessor, schema keywords, the reserved `field`, probe (`effective_config`) | adapter 0.2.0 | pure Python |
| **A2b** run summary and backend interface | `output.observables`, integer accumulators and MT merging, `layered_sim.summary/1`, column map; Python inference reads summaries; J14 replay uses committed summaries; a second-backend test (delivering only summary, column map and effective config) | adapter 0.3.0 | pure Python |
| **B0** per-event ROOT files | `G4RootAnalysisReader` trial; `EventFile.*`, `simroot`; the `summary`, `hits` and `crossings` levels | adapter 0.4.0 | no ROOT needed |
| **B1** J15 | field, plane crossings, `simreco` (C++, Geant4-free) and its required CI job, `verification`, the derived-simulation marker (C2), the J15 journey | adapter 0.5.0, contracts C2 | pure Python (reconstruction outputs committed as summaries) |

Each stage merges on its own; if A2a's bit-identical comparison stalls, A1 is not held up.

---

## 5. Differences from the current specs

| Item | Current specs | New architecture |
|---|---|---|
| Contracts C1 (grade table, scope, configuration, isolation) | A1.1–A1.3 | **kept** |
| IUT gate, incomplete, stopping rule, seeds H, negative controls | A1.4, A1.5, A1.7, A1.8, A1.10 | **kept** (only the 1.97 two-stage factor remains) |
| MPV | mean of sub-run modes; bias only recorded | histogram three-point interpolation + bias limit |
| Other SEs | counter-hash bootstrap (R ≥ 400) | batch means (K = 16); bootstrap dropped |
| `simstat`, the `simcore` project, a required CI job | phase 2 | **dropped**; inference stays in Python, reading summaries |
| `simspec` | a separate C++ executable | the `layered_sim convert` subcommand |
| Backend interface | column map + per-event CSV | run summary + column map + effective config |
| Chunk merging | partition, by name tokens | each summary accumulator carries its merge rule |
| ROOT files, `simroot` | task A, phase 2 | task B, B0, with `simreco` |
| `simreco` | part of `simcore` | the only Geant4-free C++ project, in task B |
| J14 replay | needs a compiled `simstat` after phase 2 | always pure Python |
| Scope of bit identity | CSV, `simspec` placements, `simstat` within 1e-12 relative | CSV, `convert` placements, summaries (integers, bit-identical across threads and compilers) |
| J15 design (geometry, parameters, validation ladder, convergence, variations) | task B | **kept** |

---

## 6. Acceptance points of the new methods

- [ ] Integer accumulation in summaries: with the same seed, serial and MT runs with different thread counts give bit-identical summaries; merging chunks gives the same accumulators as a single run.
- [ ] A summary recomputed in Python from a committed per-event CSV equals the one `layered_sim` wrote (bit for bit after quantization), as the oracle.
- [ ] Batch-means SE coverage toy: under the distributions of J14's observables, the actual coverage of a nominal 90 % interval is within 0.90 ± 3σ_MC.
- [ ] MPV bias toy: |bias| ≤ tol/10 at the declared N/K and bin width.
- [ ] J14's offline replay still reproduces the committed output bit for bit, and runs where no compiler is installed.
- [ ] A second backend (delivering only summary, column map and effective config) passes J14's gates and benchmarks.

---

## 7. Decisions needed

1. **Reinterpreting the language split (needs the user's confirmation):** per-event computation in C++, inference on run summaries in Python; no `simstat` and no `simcore` project.
2. Batch means for every SE, dropping the bootstrap: this widens the D5 sci-fix (reported SEs change, S1), to be explained in the ledger.
3. ROOT files and `simroot` move to task B's B0.
4. The stages become A1, A2a, A2b, B0, B1, each merged on its own (so two more adapter versions).
5. Default quantization steps (energy 1 eV, length 1 nm, time 1 fs) and `sum2` written as an int128 decimal string.

Of the earlier open decisions, "a new required CI job that builds `simcore`" moves to task B (`simreco`); the rest stand (version class of C1, the fallback for bit identity, G5 confirmation, hep-computing's agreement to the `simulation` property and the derived-simulation marker, where ROOT files are stored).

## 8. Residual risks

1. Quantization means a summary is no longer the exact floating-point sum; the error bound n·q/2 must be far below any tolerance, checked against the declared q and event count.
2. For very skewed observables (a small tail fraction, say), the t approximation with K = 16 may be optimistic; the coverage toy shows this, and K is raised if needed (declared before the first evidence run).
3. Geant4 initialization time for 16 processes: a few seconds per point for J14, acceptable overall; calorimeter studies estimate it with a trial run.
4. The behaviour of a custom `G4VAccumulable` and of `G4AccumulableManager::Merge()` must be confirmed on 11.4.3 with an MT test.
5. After A2b the recorded J14 replays from summaries; the old CSV replay path stays in tests as the oracle until J14 is re-recorded.

## 9. Steps after approval

1. Rewrite `task-a-core.md` (A1, A2a, A2b) and `task-b-j15.md` (B0, B1) per §4 and §5, both languages together.
2. Update the file table, decisions and order of work in `README.md`.
3. Have an agent that did not write the specs review them independently, focusing on summary accumulation and merging, batch-means coverage, and the interfaces between stages.

---

## 10. Generality assessment

### 10.1 Method

Test the architecture of §2 against five kinds of real use case, layer by layer, looking for places where a different use case would force a change to the core:

| Use case | Typical needs |
|---|---|
| material-level references (J14-like) | isolated slabs, analytic or PDG references |
| a spectrometer with a field (J15, space or cosmic-ray detectors) | field, several subsystems, reconstruction, rigidity and β resolution |
| a collider or test-beam detector module | non-slab geometry (cylinders, rotations, GDML), comparison with test-beam data |
| rare events (dark matter, 0νββ, background studies) | radioactive sources and decay chains, time windows, event weights (biasing), very small counts |
| other simulation engines or fast simulation (FLUKA, parametrizations, ML surrogates) | no Geant4 probe; per-event processing not in C++ |

### 10.2 What is already general

- **The run-summary boundary itself is engine-independent.** Any producer (`layered_sim`, `simreco`, a user's Geant4 application, another engine, an offline reducer) that writes the same schema reaches inference and decisions. This is the main source of generality in §2.
- **Batch means does not depend on the form of the observable.** Any estimator computable per chunk from a summary (mean, fraction, ratio, quantile, mode) gets its SE the same way, and correlations between observables are handled automatically, with no Σxy needed.
- **The contract's upgrade logic does not depend on geometric shape.** "Grade from the contracts table, scope compared by kind, target compared by hash" holds for any geometry; `longitudinal-profile` already shows a reference measurement tied to a specific configuration.
- **The number of chunks and where they run are unconstrained.** A chunk can be a local process or a cluster job; accumulators carry their merge rules, independent of the partition's naming rules.

### 10.3 What would lock generality in

| # | Where | Today | Problem with another use case |
|---|---|---|---|
| G1 | source of configuration and the target hash | derived from the spec's slab list (A1.3) | non-slab geometry, GDML and user applications cannot be derived, so they can never upgrade |
| G2 | scope dimensions | hard-wired particle, material, energy, thickness (`validate.py` lines 350–355) | a detector-level scope needs incidence angle, position, rigidity, field strength and so on; slab "thickness" means nothing for a module |
| G3 | the isolation rule's field requirement | isolated only with no field | a test-beam measurement in a field (a spectrometer module) is always embedded, even when the reference was measured in the same field |
| G4 | accumulators without weights | `n`, `sum`, `sum2` | events from biasing or importance sampling carry weights (the CSV already has a `weight` column, unused downstream); unweighted accumulation gives wrong means and SEs |
| G5 | one dimension per observable | single-column accumulators and 1D histograms | "y in bins of x" quantities such as resolution against energy or efficiency against position are impossible; per-event combinations (ratios, differences) and event selections have nowhere to be defined |
| G6 | only one SE method | batch means | for rare counts (many chunks at 0) the t approximation fails; exact Poisson or binomial intervals are needed |
| G7 | only a `gun` source | point, direction, single energy | spectra, isotropic fluxes, radioactive sources and decay chains, external event files (HepMC) cannot be expressed; flux normalization (geometric factor) has nowhere to be recorded |
| G8 | `effective_config` is Geant4-specific | EM parameters, cuts, hadronic models | other engines cannot provide it; the rules (`G4R-*`) are tied to Geant4 |
| G9 | the derived-simulation marker has one level | a reconstruction record's inputs must be simulation runs (C2) | multi-stage chains (simulation → digitization → reconstruction → analysis) break after the second level |
| G10 | the number of chunks is fixed at 16 | K = 16 | wastes information with hundreds of cluster chunks; skewed distributions may need a larger K |

### 10.4 Recommendations

Three tiers, by whether not doing it now would force a change to a core interface later. The rule: **define interfaces to be extensible now, implement only what the use case at hand needs; no general expression language, no plug-in system.**

**Tier 1: do now (cheap; avoids changing interfaces later)**

| # | Change | Where |
|---|---|---|
| G1 | configuration and the target hash are derived from **the actual geometry tree dumped by the probe**: walk `G4PhysicalVolumeStore` and record each placement's solid type and parameters, material, transform, mother and attached field. Deriving from the spec is only the fallback without a probe, marked `source: declared`, and then cannot upgrade. This also follows principle 3 (trust the actual state) | A2a probe; A1.3 derives from the spec first, the probe takes over from A2a |
| G2 | scope becomes **a list of dimensions declared per kind**: each benchmark in the contracts table lists its dimensions and their types (categorical or numeric range); the comparison rule is unchanged (a missing dimension is outside). The current four dimensions become the default list for material-level kinds | A1.1, A1.2 (done within C1, so C2 need not change the comparison logic again) |
| G3 | isolation becomes "nothing outside the target": a field attached to volumes inside the target is part of the target and enters the target hash; only a field extending beyond the target makes it embedded. J14's verdicts do not change | A1.3 |
| G4 | accumulators carry weights from the start: `n`, `Σw`, `Σw²`, `Σw·x`, `Σw·x²`, weighted histograms; unweighted is the special case w = 1. Weights are quantized to integers too, keeping the result exact and order-independent; the effective event count n_eff = (Σw)²/Σw² goes into the summary | A2b (in the first version of `layered_sim.summary/1`) |
| G6 | each estimator declares its SE method: batch means by default; counting estimators switch to exact intervals (Garwood for Poisson, Clopper–Pearson for binomial) from the merged accumulators when the total count is below a threshold (for example any chunk at 0, or a total < 100) | A1 (Python inference) |
| G8 | `effective_config` gets an engine-independent envelope: `{engine, engine_version, config_sha256, sections{...}}`, with the Geant4 content in `sections.geant4`; rules are chosen as a rule pack by `engine` | A2a |
| G9 | the derived-simulation marker becomes transitive: the input chain of a simulated table may have any depth, as long as every level is a recorded computational-run and every root of the chain is a simulation run | B1 (C2) |
| G10 | K becomes a declared value, at least 16; the two-stage factor follows from K (F₀.₉₀(K−1, K−1)) | A1 |

**Tier 2: define the interface now, implement with the first use case**

| # | Interface | First use case |
|---|---|---|
| G5 | `output.observables` allows three declarations: a single column; limited per-event combinations (a linear combination of columns, the ratio of two columns); event selection (AND of column-against-constant comparisons). Accumulators gain profiles (n, Σw·y, Σw·y² in bins of x) and 2D histograms. Any computation beyond these is a separate recorded step (a C++ reducer that reads the event file and writes a summary of the same schema) | J15's resolution against rigidity (B1) |
| G7 | spec/2's `source` block is distinguished by `type`: `gun` (existing), `gps` (`G4GeneralParticleSource`, declarative settings only), `event-file` (HepMC and other external events); the summary records the source area and solid angle needed for flux normalization | the first spectrum or flux study |
| — | a reducer `simreduce`: reads ROOT event files (with `simroot`'s reading code) and writes summaries as declared, so observables decided after the fact need no rerun of the simulation | the first need after B0 |

**Tier 3: defer (with triggers)**

| Item | Trigger |
|---|---|
| non-slab geometry in `layered_sim` (GDML input, cylinders, rotations) | the first study that needs non-slab geometry and cannot use a user application with the header; G1 already lets user applications upgrade, so `layered_sim` itself is not urgent |
| rule packs and probes for other engines | the first non-Geant4 backend |
| biasing-specific rules (weight distribution, minimum n_eff) | the first study with biasing; G4 already makes the accumulators correct |
| optical photons, long time windows and decay chains | the first scintillator or rare-event study |
| probes for several Geant4 versions | the first application on a version other than 11.4 |

### 10.5 Generalizations deliberately not made

- **A general expression language.** Declarative combinations stop at linear combinations, ratios and AND selections; anything more is a recorded program step. An expression language would become a second programming language to validate.
- **A plug-in system for estimators.** Estimators are a small set of tested Python functions in the control plane; adding one is an ordinary code change with review.
- **One probe for all engines.** Only the envelope is unified (G8); each engine describes its own content. Forcing one schema would lose engine-specific information that matters for decisions.
- **Adaptive binning or approximate quantile sketches (t-digest, say).** Their merged results depend on order, which breaks the exactness of summaries; bins are always declared in advance.

### 10.6 Effect on the stages and open decisions

- A1 (C1) gains two items: scope dimensions declared per kind (G2) and the field definition of isolation (G3). It also gains exact counting intervals (G6) and a declared K (G10). All change verdicts and go into the S2 sci-fix entries.
- A2a gains two items: the probe's geometry-tree dump (G1) and the engine-independent `effective_config` envelope (G8).
- A2b's first summary version carries weights (G4) and reserves the fields for profiles and 2D histograms (the interface of G5).
- B1's C2 marker becomes transitive (G9); J15's resolution against rigidity is the first user of profiles.
- New open decisions: whether per-kind scope dimensions go into C1 (recommended, or C2 has to change the comparison logic again); the threshold for switching to exact counting intervals.
