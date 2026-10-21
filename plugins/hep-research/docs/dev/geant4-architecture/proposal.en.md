# hep-research Geant4 study architecture: final version

> Status: final proposal, awaiting the maintainer's approval
> Basis: three rounds of independent review (v2, v4, v5; seven review reports) and a re-check against 0.21.0 (section 12); every fact and number the reviews raised has been checked
> Baseline: hep-research **0.21.0** (`main` at `c4f7954`, tag `hep-research--v0.21.0`), contracts **3.2.0**, adapter geant4 0.1.0, Geant4 11.4.3 (commit `2ee379e6`)
> Date: 2026-10-21 (re-checked against 0.21.0; see section 12)
> Language: English translation of [`proposal.md`](proposal.md) (Traditional Chinese original); the two have the same content
> Example: the J15 minimal spectrometer is a **synthetic geometry**, a vehicle for verification, not the detector of any experiment

---

## 0. Summary

This proposal has three phases. It fixes correctness defects in the Geant4 part of hep-research 0.21.0, removes the
coupling of the study workflow to a single simulation backend, and adds a minimal magnetic spectrometer (J15) that
demonstrates a magnetic field, several subsystems and a reconstruction chain.

| Phase | Content | Version | J14 |
|---|---|---|---|
| 1 | Fix label and statistics defects (sci-fix): scope compares the observable kind; benchmark grades and configuration come from a contracts table; negative controls judged by the shift in the observable; convergence gate as an intersection-union test; MPV SE from a partition into sub-runs | **contracts 3.3.0** (minor) | re-recorded once |
| 2 | layered_sim core refactor: spec/2, scorer components, probe, column map; hep-detector reads both formats | **adapter 0.2.0**; no contracts version change | re-recorded once, after bit-identical output on the same host |
| 3 | J15 minimal spectrometer: field region, plane-crossing scorer, digitization and reconstruction (mixtures already exist in 0.21.0); `verification` grade and isolation rule | **adapter 0.3.0**, **contracts 3.4.0** (minor) | not re-recorded |

**The eight most important decisions:**

1. **The current `validated-in-scope` has holes and must be fixed first.** The scope check skips the observable, and
   the grade of a benchmark is declared by the record itself.
2. **The validation grade follows the nature of the reference.** A reference that is an exact consequence of the
   inputs gives verification; only a reference that is a physics model Geant4 approximates can give validation.
3. **The contract enforces upgrade eligibility.** The contracts carry their own table of benchmark → grade and kinds;
   `configuration` is derived by the tool from the geometry and never taken from user input.
4. **One geometry path in C++.** spec/1 is converted to spec/2 in Python; bit-identical output on the same host proves
   the conversion.
5. **Reuse existing tools.** `contracts/schema.py`, `tracker_resolution.py` and `multiple_scattering.py`; no second
   implementation.
6. **Field accuracy is checked deterministically.** A charged geantino is compared with the analytic helix; no
   statistics are needed.
7. **The statistical rules must be executable.** The convergence gate is an intersection-union test; t quantiles
   whenever the SE is estimated; the two-stage event-count factor is F₀.₉₀(15,15) ≈ 1.97.
8. **Drop or defer what is not needed.** `uses-validated-physics`, `physics_config_comparison`, ions and Birks, a
   content-addressed cache, contracts 4.0 and more (section 7).

---

## 1. Background: confirmed defects

Each item was checked against the 0.21.0 source (line numbers are 0.21.0).

| # | Defect | Location | Consequence |
|---|---|---|---|
| D1 | The scope check does not compare the observable | `validate.py` `_scope_inside()` (from line 327); `check_geant4_study.py` `scope_within()` (lines 481–492: the loop explicitly skips observable and ignores scalars) | A study passed by an MPV benchmark can label another observable `validated-in-scope` |
| D2 | The grade of a benchmark is declared by the record | `_study_upgrade` (line 373; filter at line 397) reads `grade` from the record | Any producer that writes `"grade": "reference"` can upgrade |
| D3 | Negative controls compare quantities in different units and test one sign | `at_limit` at `geant4_benchmarks.py` line 678 | "At the detection limit" is not shown in the observable |
| D4 | The convergence gate has no equivalence test | `check_geant4_study.py` `convergence()` (verdict at line 358) | About 50 % pass when the true difference equals the tolerance |
| D5 | The MPV SE comes from a bootstrap | `geant4_benchmarks.py` line 369 bootstraps the argmax-type `mpv()` | Inconsistent variance estimate; J14's detection limit rests on it |
| D6 | The stopping rule does not forbid extra runs decided by results | protocol section 4 | Optional-stopping bias |
| D7 | Correlation between pieces of evidence is not disclosed | J14's nominal run feeds the gate, the statistical target, the benchmark and the variations | Treated as independent evidence |
| D8 | The study-spec benchmark enum lacks `shower-containment` and 0.21.0's `longitudinal-profile` | `geant4-study-spec.schema.json`; `GRADES` has 9 names, the enum 7 | Inconsistency; `longitudinal-profile` is a reference benchmark that a study spec cannot declare |
| D9 | The study layer is tied to layered_sim's data format | `derived()` reads `geometry.layers`; `summarize` and the benchmarks read fixed column names | No other backend can use the gate or the benchmarks |

---

## 2. Design principles

1. **Correctness before extension.** No new feature is merged before phase 1 is complete.
2. **The study core reads only data.** Rules, gates and benchmarks read through the column map and the probe output,
   never backend-specific column names or UI command strings.
3. **Trust the effective state; declarations are only a fallback.**
4. **Stopping rules and grids for evidence are declared in advance.** Extra runs, refinements and repeated controls
   are never decided by gate or benchmark outcomes.
5. **Look for an existing implementation first.** Methods the plugin already has are reused; an oracle never imports
   the module under test.
6. **Minimal change.**
7. **Follow the existing rules.** Layering (skill scripts and adapters import only `core` and `contracts`), the
   quick-load limit (hep-detector is at 24,669 / 25,600 bytes), the G5 licence boundary, the adapter-change process and
   the sci-fix process. The Geant4 scripts use only the Python standard library; this is a design choice, not a
   plugin-wide rule.
8. **Backends describe themselves.** layered_sim writes its own column map and its effective settings at run time.
9. **The validation grade follows the nature of the reference.** If the reference is an **exact consequence** of the
   inputs (analytic helix, kinematics, least-squares algebra), the check is verification and cannot upgrade; only if
   the reference is a **physics model that Geant4 approximates** (Bethe, Landau–Vavilov, Highland, shower profile)
   can it be reference or sanity.
10. **The contract decides what can upgrade.** Grade, kind and configuration are never self-declared by a record.

---

## 3. Architecture overview

```
hep-detector (physics decisions)
  check_geant4_study.py     spec / summarize / run / variations / label
                            + dual-format geometry accessor (spec/1, spec/2)
  geant4_benchmarks.py      emits observable kind and configuration (derived from the geometry)
  digitize_reconstruct.py   (phase 3) digitization, circle fit, beta
  tracker_resolution.py, multiple_scattering.py (existing; used as references)
        │  reads files only; imports only core and contracts
        ▼
contracts
  validate.py               (phase 1, 3.3.0) scope compares observable kind; benchmark table (name → grade, kinds)
                            (phase 3, 3.4.0) table gains verification; isolation rule
                            (existing in 0.21.0) simulated dataset-record (3.2.0)
  schema.py                 (phase 2) adds maxItems, maximum, exclusiveMaximum (no version change)
  computational-run (existing; extension.study and extension.simulation are free-form blocks)
        ▲
        │  writes files
adapters/geant4 (execution layer; every record unvalidated)
  geant4_build.py   build / check
  geant4_run.py     spec/1 → spec/2 conversion, cross_field_checks, run / scan / chunk / summarize / reduce / oracle
  geant4_verify.py  overlaps / budget / balance / mirror / datapaths (reads both formats)
  layered_sim       spec/2 only; scorer components; probe; column map (layered_sim.output/2)
                    (existing in 0.21.0) mixtures (components)
                    (phase 3) field region, plane crossings
        │
        ▼
hep-computing (run_workflow.py, local_partition.py)
```

---

## 4. Phase 1: fix the current defects (contracts 3.3.0, sci-fix)

### 4.1 A benchmark table in the contracts (D2)

Add a constant table to `contracts/validate.py`. `_study_upgrade` takes grades and kinds from this table, not from the
record:

| Benchmark | Grade | Supported observable kinds |
|---|---|---|
| `stopping-power` | reference | `stopping-power` |
| `range` | reference | `range` |
| `thin-layer-mpv` | reference | `most-probable-value` |
| `thin-layer-width` | sanity | `thin-layer-width` |
| `multiple-scattering` | sanity | — |
| `em-shower-shape` | sanity | — |
| `shower-containment` | sanity | — |
| `longitudinal-profile` | reference | `shower-shape` |
| `published-data` | interface | — |

- The grades equal 0.21.0's `GRADES` (including `longitudinal-profile`), so J14 is unaffected.
- A record whose `grade` disagrees with the table is an error.
- `GRADES` in `geant4_benchmarks.py` stays for the tool; a test keeps it equal to the contracts table.

### 4.2 Scope check (D1)

- Compare the controlled `observable.kind` (the study spec's existing enum), not free text; the free text stays for
  human readers.
- The declared kind must be among the kinds supported by the counted benchmark.
- Dimensions compared: observable kind, particle, material, energy, thickness; a scalar is treated as `[v, v]`.
- One implementation in `validate.py`, exported; `check_geant4_study.py` imports it and `scope_within()` is removed.
- Gated like every other rule family: `strict or _at_least(contract_version, "3.3.0")`, with no warning branch.
- The scope of `longitudinal-profile` holds only particle and energy (no material, no thickness), so only those two
  dimensions and the kind are compared; its "material" is the whole sampling stack, handled by the configuration rule
  (4.3).

### 4.3 configuration is emitted from phase 1

- `geant4_benchmarks.py` emits `configuration` for each benchmark result, derived from the run's geometry: `isolated`
  when there is no field and every placement other than the world belongs to the benchmark's **target**; otherwise
  `embedded`. The target is the measured slab for single-slab benchmarks (stopping-power, range, thin-layer-*) and the
  whole sampling stack listed in its configuration for `longitudinal-profile`.
- It also emits a hash of the target geometry (`target_geometry_sha256`), so that a reviewer can confirm that the
  `longitudinal-profile` stack is the published measured configuration; the contract cannot decide this, and the
  protocol says so.
- The field is never taken from user input.
- Phase 1 emits it **without** a contract rule; the rule arrives in phase 3 (3.4.0; 6.9).
- J14 is re-recorded in phases 1 and 2 with `configuration: isolated`, so the 3.4.0 rule can require the field.

### 4.4 Negative controls (D3)

- The decision quantity is the realized shift in the observable: `shift = (control − nominal) / reference`, with the
  SE combined from both runs.
- At the detection limit: `caught` and `|shift| ≤ 1.1 × DL`.
- Inject both signs; otherwise restrict the claim to one sign and record it in `scope.detection_limit_sign`.

### 4.5 Statistical rules

**Convergence gate (D4).** "Pass only if every observable is equivalent" is an intersection-union test:

```
pass:        |diff| + q_pass · se ≤ tol
fail:        |diff| − q_fail · se > tol
otherwise:   unresolved
```

| Item | Rule |
|---|---|
| se | the SE of the **difference** |
| q_pass | se from sub-runs: t₀.₉₅(ν); se from a large-sample bootstrap: z₀.₉₅ = 1.645 |
| q_fail | the same, at quantile 1 − α/m, with m the number of (parameter × observable) pairs |
| ν | difference of two estimates, each from K = 16 sub-runs: about 30 by Welch (t₀.₉₅(30) = 1.697); a single estimate: 15 |
| Event count | set in advance so that the se of the difference ≤ tol/4 |

Operating characteristics (se = tol/4 taken as known, α = 0.05):

| True difference | Pass | Fail (m = 1) | Fail (m = 6) | Fail (m = 30) |
|---|---|---|---|---|
| 0 | 0.981 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.639 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.050 | 0.008 | 0.002 |
| 2 tol | 0.000 | 0.991 | 0.946 | 0.857 |

At a true difference of tol/2 the gate passes only about 64 % of the time; this is the price of se ≤ tol/4 and is
stated in the documentation.

**MPV estimator and its SE (D5).**
- The nominal N events are **partitioned** into K = 16 sub-runs with `geant4_run.py chunk`. This splits the same
  events, adds none, and gives each sub-run its own seed.
- The reported value becomes **the mean of the 16 sub-run MPVs**, with a fixed bin width written in the spec;
  SE = sd(sub-run MPVs) / √16; quantiles from t₁₅.
- The full-sample MPV is a diagnostic only; its difference from the mean is recorded. The histogram-mode estimator does
  not scale as 1/√N, and sd/√K is valid only for the mean of the sub-run MPVs. A reviewer's toy showed that applying
  it to the full-sample MPV underestimates the SE by a factor of 1.1 to 2.3, depending on the bin width.
- The bootstrap is no longer used for the MPV.

**Two-stage event count.**
- `N = ceil(N_trial · (SE_trial / target)² · f)`.
- "Target missed" is judged on the **estimated** SE of the evidence run. When both the trial and the evidence SE come
  from K = 16 sub-runs, the probability of meeting the target is P(F₁₅,₁₅ ≤ f): only 0.636 at f = 1.2, so
  **f = F₀.₉₀(15,15) ≈ 1.97**, which gives 90 %.
- When the SE comes from a large-sample bootstrap, f = 1.2.
- An evidence run that misses the target is unresolved and **is not topped up**.

**Seeds.** `seed = H(study_id, role, point_id, k)`, mapped to two positive integers as `run.seeds` requires. Roles:
trial, nominal, scan, control, variation, calibration; k is the sub-run or chunk index; the two signs of a control use
different point_ids. No seed repeats within a study.

**Bootstrap** (for means, quantiles and fractions).
- Poisson(1) weights from a 64-bit counter hash of (study_seed, run_id, chunk_id, event_id, replica_id), mapped by the
  inverse CDF.
- R ≥ 400.
- `summarize` checks the event keys for duplicates.

**Correlated evidence (D7).** `extension.study.evidence_overlap` lists runs shared by several decisions, with
`evidence_overlap_version`.

### 4.6 Other fixes

- Add `shower-containment` and `longitudinal-profile` to the study-spec benchmark enum (D8).
- Protocol section 4 (D6): the stopping rule, the scan grid and the handling of unresolved results are written into
  the study spec before the first evidence run.

### 4.7 Version and sci-fix process

- **Version: contracts 3.3.0 (minor).** 0.21.0 already uses 3.2.0 (simulated dataset-record). Every existing gate is
  at an x.y.0 version; new gated rule families have been minor versions (2.4.0, 2.6.0, 2.8.0, 3.1.0, 3.2.0).
- **sci-fix** (per `docs/maintenance.md`):
  - class S2 (changes verdicts); commit prefix `sci-fix:`; a parent record (evidence level D2 of
    `docs/maintenance.md`, not defect D2 of this document).
  - oracle evidence at least C2; an assistant-written oracle must meet one of the four independence bases.
  - a new entry in `docs/evidence/sci-fixes.json`.
  - 0.20.0 and 0.21.0 released the affected verdict path, so an advisory is needed (as of 0.21.0 the next number is
    SFA-2026-036).
- Study records produced by 0.20.0 and 0.21.0 lack kind and configuration and fail under `--strict`; the advisory
  explains what to do (regenerate with the new version).
- 0.21.0's simulated dataset-record lets a table drop `unvalidated` when an input study record carries
  `validated-in-scope`. The scope fix tightens this path too; the advisory covers it.

### 4.8 Phase 1 acceptance

- [ ] Records with a kind mismatch, or a grade that disagrees with the contracts table, are refused under `--strict`
  and 3.3.0; scalar scopes are compared correctly.
- [ ] The regenerated J14 study records (with kind and configuration) pass `validate.py --strict` and
  `dependencies.py`.
- [ ] Negative controls are judged by the shift in the observable, with tests for both signs.
- [ ] Gate toy test (10⁴ toys per cell): pass rate ≤ 0.05 + 3σ_MC at a true difference of tol; ≥ 0.97 at 0; the
  fail-side correction matches the table in 4.5 within 3σ_MC.
- [ ] MPV: at J14's N, compare the sub-run mean with the full-sample MPV, and the sub-run SE with the bootstrap SE;
  record the results in VALIDATION.
- [ ] After J14 is re-recorded on E2, every reference benchmark's control is still caught within
  `|shift| ≤ 1.1 × DL`; if not, redesign the controls for the new detection limit and record why.
- [ ] sci-fix ledger, advisory and parent record complete; VALIDATION entry GEANT4-CORRECTNESS; CHANGELOG; release
  manifest.

---

## 5. Phase 2: layered_sim core refactor (adapter 0.2.0)

### 5.1 Scope

All C++ work that affects J14 happens in this phase: reading spec/2, scorer components, the probe, the column map. The
field region and plane crossings arrive in phase 3 (mixtures already exist in 0.21.0); they change the
`sources_sha256` of later live J14 reruns, which is expected, and the committed J14 records are not re-recorded.

### 5.2 spec/2 coordinates and format

- Coordinates are centred on the world; the stack axis is x.
- `at_mm` is the x coordinate of an element's **front face** in world coordinates. A daughter's `at_mm` is also in
  world coordinates and must lie inside its mother.
- One level of nesting only.
- The schema uses only keywords supported by `contracts/schema.py` (including the three added in this phase).

### 5.3 spec/1 → spec/2 conversion and bit-identical output

| Factor | Effect | Conversion rule |
|---|---|---|
| Material creation | **yes** (0.21.0 mixtures add components in order with `G4Material::AddMaterial`; the order affects the floating-point accumulation of mass fractions) | keep the order of `materials[]` and `components[]`; write numbers with `repr` |
| Placement positions | **yes**: one ulp changes the step lengths | the converter reproduces the C++ operation order in IEEE doubles: `stack = Σ repeat × Σt`, `world = world_scale × stack` (or `world.size_mm`), `x = −stack/2`, `center = x + t/2`, `x += t`; output with `repr`; the new C++ computes the centre as `at + t/2` |
| `shift_mm ≠ 0` | **yes** | `(x + t/2) + shift` and `(x + shift) + t/2` are not guaranteed bit-identical; guaranteed only for `shift = 0` (J14 and the mirrors), statistical comparison otherwise |
| Gun position | **yes** | `gun_world_fraction × world length`, computed in the same order and written out |
| Physics list composition | **yes** | `G4StepLimiterPhysics` only when `step_limit_mm > 0`, `min_ekin_MeV > 0` or (phase 3) a field is present |
| Daughter placement order | low | keep the order |
| Material and region creation order | low (only couple indices) | keep the order |
| Volume names, copy numbers | **none** (only output column names) | keep unchanged |
| Overlap checks | **none** (they use the separate `G4QuickRand`) | — |
| Output column set and order | affects comparison | specs converted from spec/1 enable the legacy scorer set, in `CsvColumns` order |

**Acceptance:** on the same host and Geant4 build, the 0.21.0 layered_sim and the new one produce bit-identical CSVs
for the TestEm3 and TestEm5 mirrors and the J14 specs (same seeds, serial), and identical hex-float dumps of every
placement (name, copy number, translation, mother). Across hosts, only statistical comparison; the committed J14 CSVs
are not a bit-identical reference.

### 5.4 Dual-format support in hep-detector

J14's recorded records must replay forever, so the Python side supports spec/1 and spec/2 permanently; only the C++
has a single path.

| Place | Change |
|---|---|
| run record | records `spec_sha256` (the spec as given) and `effective_spec_sha256` (the spec/2 the C++ ran) |
| `check_records` | compares the study's spec with the run's `spec_sha256` |
| Geometry accessor (new function) | element list, minimum thickness and materials from `layers` or `elements`; tested on the J14 records |
| `derived()` | `min_thickness_mm` through the accessor; a test keeps `G4R-THIN-FLUCT` and `G4R-THIN-CUT-SCAN` firing for both formats |
| `cmd_summarize` | gun energy from the run record's `extension.simulation.gun`; spec/2 gun fields defined (`energy_MeV`, plus `ekin_per_nucleon_MeV` from phase 3) |
| `geant4_verify.py` | volume count (overlaps) and material budget (budget) through the accessor |
| study-spec schema | `$comment` accepts `layered_sim.spec/1` or `/2` |

### 5.5 Schema validation

- Extend `contracts/schema.py` with `maxItems`, `maximum` and `exclusiveMaximum` (0.21.0's `SUPPORTED_KEYWORDS` still
  lacks all three, while the layered_sim schema already uses `maxItems` and `exclusiveMaximum`). Update
  `SUPPORTED_KEYWORDS` and extend `tests/contracts/test_schema_keywords.py` to scan the adapter schema too (it scans
  only `contracts/schemas/*.json` today).
- `geant4_run.py` switches to `contracts.schema.validate()`. The cross-field rules of the old `validate_spec()`
  (0.21.0 line 103) that the schema cannot express stay as `cross_field_checks()`: for mixtures, components versus
  z/a_g_mole (exactly one), at least two components, mass fractions summing to 1, components referring only to NIST or
  earlier materials; a reused slab name keeps its material and thickness; exactly one of world scale and size; exactly
  one of `reference_list` and `em_constructor`; region slab names exist; banned UI commands; the gun position range.
- The C++ checks only what it needs to run.
- No contracts version change: no contract schema uses the new keywords.

### 5.6 Probe and column map

**Probe (`Probe.hh`):**

| Item | Rule |
|---|---|
| Timing | the master's `BeginOfRunAction`; state `G4State_GeomClosed` and more than zero couples, otherwise refuse and record why. Per the 11.4.3 source, the physics tables exist at this point; a fake run (`/run/beamOn 0`) returns before `BeginOfRunAction`, so the probe does not run |
| Frequency | once per run |
| Threads | master only; the output says "workers assumed identical" |
| EM parameters | full text of `G4EmParameters::StreamInfo(os)` plus parsed fields; not `Dump()` (in 11.4.3 it prints only once per process) |
| Cuts | per material-cuts couple: material, region, range cut, energy threshold per particle |
| Hadronic models | per process and model, energy ranges queried per material and element; overlap regions marked as random choice |
| Run manager | type, `seedOncePerCommunication`, `G4RUN_MANAGER_TYPE`; SubEvt or a non-zero seeding mode is reported as a gap |
| Other | `G4UserLimits`, biasing, dataset paths and content hashes |
| Version | 11.4.x; `probe_version` |
| Output | `extension.simulation.effective_config` |

Rules and the model assignment of variations read the probe first and fall back to declarations, writing
`source: probe | declared`; when both exist and disagree, it is an error.

**Test trigger:** a UI command present only in test builds calls the probe after `/run/initialize` and before the first
`BeamOn`; the probe must refuse.

**Column map:**
- File `column_map.json`, schema `layered_sim.output/2`, kept in the adapter next to `output.schema.json`.
- layered_sim writes it for every run; its hash goes into the run record.
- Each column has a semantic name, the actual column name, a unit and an operational definition; `column_map_version`.
- A user's own application can write a map of the same format by hand; only declarative operations (rename, unit,
  sum, filter) are allowed. A conversion that computes something must be a separate recorded step.

### 5.7 Adapter-change process

| Item | Content |
|---|---|
| Version | 0.1.0 → 0.2.0 |
| `adapter.json` | add the new files to `assets`; update `purpose`; `status` stays `demonstrated-on-synthetic-data` |
| `SIM_SOURCES` | add `Scorers.*` and `Probe.hh` (otherwise `sources_sha256` leaves out the new sources) |
| G5 | the statement "written from the Geant4 API; no example code copied or adapted", confirmed by a reviewer in the VALIDATION entry |
| Tests | the assets check in `tests/adapters/test_geant4.py`; offline tests; live tests with `HEP_GEANT4_LIVE_TEST=1` |
| Documentation | the Geant4 row of `docs/capability-matrix.md` |

### 5.8 Phase 2 acceptance

- [ ] Bit-identical output and identical placement dumps on the same host, per 5.3.
- [ ] J14 read through the accessor gives the same result for spec/1 and spec/2; both thin-layer rules fire for both
  formats.
- [ ] The probe refuses at the wrong time triggered by the test command; every J14 run has `effective_config`; it
  agrees with the declarations, and a deliberate disagreement is caught.
- [ ] A fake backend that only renames columns, with a hand-written column map, passes J14's summarize, gate and
  benchmarks.
- [ ] `contracts.schema.validate()` plus `cross_field_checks()` reach the same verdicts as the old `validate_spec()` and
  the C++ on a set of valid and invalid specs.
- [ ] J14 re-recorded once on E2; VALIDATION entry GEANT4-CORE; CHANGELOG; release manifest.

---

## 6. Phase 3: J15 minimal spectrometer (adapter 0.3.0, contracts 3.4.0)

### 6.1 Geometry

Coordinates: centred on the world, stack axis x, in mm.

**Magnetic field: B = (0, 0, +0.5 T).** The bending plane is x–y; the non-bending direction is z. A positive charge
moving along +x bends toward −y; a μ⁻ bends toward +y.

```
x:  −1000   −800      −520 −500        …         300  320    500    550           900   ±1200
     gun    TOF1       │ Si1  Si2  Si3  Si4  Si5  Si6  │     TOF2   calorimeter     world edge
            10 mm      │◄──── uniform field 0.5 T ẑ (−520 … 320) ────►│  10 mm  50 × Pb 2 / PVT 5 mm
```

| Element | Material | Front face `at_mm` | Thickness | Extent | Transverse (y × z) |
|---|---|---|---|---|---|
| World | `G4_Galactic` | — | 2400 | −1200 … 1200 | 1200 × 1200 |
| Gun | — | x = −1000, y = z = 0 | — | — | — |
| TOF1 | `G4_PLASTIC_SC_VINYLTOLUENE` | −800 | 10 | −800 … −790 | 300 × 300 |
| Field mother | `G4_Galactic` | −520 | 840 | −520 … 320 | 300 × 300 |
| Si1–Si6 (daughters) | `G4_Si` | −500.15 + 160k | 0.3 | centres −500, −340, −180, −20, 140, 300 | 200 × 200 |
| TOF2 | PVT | 500 | 10 | 500 … 510 | 400 × 400 |
| Calorimeter | 50 × (`G4_Pb` 2 + PVT 5) | 550 | 350 | 550 … 900 | 500 × 500 |

Checks (the script in Appendix A):
- Lever arm L = 0.800 m; the front of Si1 and the back of Si6 are 19.85 mm from the mother's faces.
- The field extends 20 mm beyond the measured region at each end.
- TOF centre distance D = 1.300 m.
- The world contains the gun and the back of the calorimeter.

Materials (11.4.3 NIST definitions against PDG): `G4_PLASTIC_SC_VINYLTOLUENE` is 1.032 g/cm³ with I = 64.7 eV, as in
PDG; `G4_Si` is 2.33 g/cm³ (PDG 2.329).

### 6.2 Parameters and acceptance

| Parameter | Value | Reason |
|---|---|---|
| B | 0.5 T | The rigidity where the scattering and measurement terms are equal is about 16–22 GV (μ), independent of B. 0.5 T gives one decade each in 1–10 GV and 100–1000 GV |
| Si layers | 6 | N = 4 leaves one degree of freedom in the bending plane; N = 8 improves the MDR by only about 8 % |
| MDR | about 1172 GV | σ_R/R = 1 from the measurement term alone. The reference is the exact least-squares fit of `tracker_resolution.py` (constant 0.2998). `mdr_intrinsic_only_gv` of `multiple_scattering.py` has the same definition but is still computed with the Gluckstern approximation (about 1131 GV at N = 6); since 0.21.0 it also reports `intrinsic_coefficient` (including the exact coefficient used here) and warns below N = 10 |
| TOF | σβ/β ≈ 3.3 % (100 ps, β = 1) | D = 1.3 m |
| Calorimeter | 18.4 X₀, 0.886 λ_I, 50 cm wide | 0.89 λ_I suffices for e/p separation by shower shape, not for hadron energy |

**Multiple-scattering term.** The design estimate here uses the Highland formula with the log term on the total
thickness and a coefficient of 1.0–1.4. A reviewer's exact least-squares calculation with discrete scattering planes
gives 1.02 (weighted fit) to 1.06 (unweighted). The plugin's `multiple_scattering.py` leaves out the log term by its
convention; comparisons must state the difference.

| Particle | Rigidity | β | Scattering term | Rigidity where the terms are equal |
|---|---|---|---|---|
| μ | 1 GV | 0.994 | 1.3–1.9 % | 16–22 GV |
| p | 0.6 GV | 0.539 | 2.5–3.5 % | 29–41 GV |
| p | 1 GV | 0.729 | 1.8–2.6 % | 21–30 GV |
| p | 2 GV | 0.905 | 1.5–2.1 % | 17–24 GV |

**Acceptance** (unit charge, normal incidence on axis, uniform field with sharp edges):

| Condition | Minimum rigidity |
|---|---|
| Does not leave the side of the field mother before x = 320 (\|y\| ≤ 150 mm) | 0.364 GV |
| Reaches Si6 (\|y\| ≤ 100 mm) | 0.511 GV |
| Reaches TOF2 (\|y\| ≤ 200 mm) | 0.391 GV |
| Calorimeter front, shower axis within 250 − 2 R_M,eff | 0.490 GV |
| Calorimeter back, same | 0.745 GV |

The overall threshold is 0.75 GV; 0.51 GV if only tracking and TOF are required. Below 0.364 GV a track leaves the
side of the field region and continues straight in the field-free world.

Electrons: the shower axis is 82 mm and 127 mm off axis at the calorimeter front and back at 1 GeV, 16 mm and 25 mm at
5 GeV. Bremsstrahlung photons from the 6.6 % X₀ upstream are not bent, so the shower axis is not the straight-line
extrapolation; the 79 mm margin covers this. Electron shower checks start at 1 GeV.

**Upstream energy loss** (integrated Bethe, 1 cm PVT):

| Proton rigidity | Kinetic energy | TOF1 loss | Δp/p | Change of β between the TOF mid-planes |
|---|---|---|---|---|
| 0.6 GV | 175 MeV | 5.06 MeV | 1.58 % | 1.55 % |
| 1 GV | 433 MeV | 2.99 MeV | 0.41 % | 0.26 % |
| 2 GV | 1271 MeV | 2.17 MeV | 0.12 % | 0.03 % |

**J14 cannot be reused.** J15's Si planes differ from J14 in material (`G4_Si` against `Si_study`), physics settings
and cuts, and J15 records only the entry point, so J14's observable E_in − E_exit cannot be formed.

### 6.3 Field implementation

- Build `G4UniformMagField`, `G4FieldManager` and `G4ChordFinder` in `ConstructSDandField`, stored as
  `G4ThreadLocal`, one set for the master and each worker. Building them in `Construct()` would make the workers share
  a chord finder that is not thread-safe.
- Attach with `SetFieldManager(fm, true)` to the field mother, which propagates to all daughters.
- Written from the API; no code copied or adapted from example B5 (G5).
- The stepper class is set in the spec and recorded by the probe (a helix stepper would make the field-transport check
  meaningless).

| Parameter | Nominal | Note |
|---|---|---|
| `delta_chord_mm` | 0.25 | inert while the maximum step is below about 80 mm; recorded, not scanned |
| `delta_one_step_mm` | 0.01 | in a uniform field the Runge–Kutta truncation error is far below the intersection error, so a scan is expected to show nothing; checked once |
| `delta_intersection_mm` | **1e-5** (0.01 µm) | sets the accuracy of crossing points |
| `min_epsilon_step` | 5e-5 | |
| `max_epsilon_step` | 1e-3 | epsilon = delta one step / step length is clamped to this ceiling |
| `max_step_mm` | 10 | needs `G4StepLimiterPhysics`; `G4UserLimits` must be set per volume and does not propagate to daughters |
| `stepper` | DormandPrince745 | the default of 11.4.3 `G4FieldParameters` |

Probe: iterate `G4LogicalVolumeStore`, read B, the chord finder and the precision parameters back through
`GetFieldManager()`; deduplicate by pointer and record the volume the manager was attached to; state that the master
sees only its own copy.

**MT test:** a UI command present only in test builds reports each thread's field-manager pointer; they must differ.

### 6.4 Other new features

| Feature | Rule |
|---|---|
| Mixtures | already supported in 0.21.0 (`materials[].components`); nothing to add for J15, where PVT and Pb are NIST materials |
| Plane-crossing scorer | on the primary's (track ID 1) **first** entry into a tracker or TOF plane (pre-step status `fGeomBoundary` and the volume is the plane), record the pre-step position, direction, kinetic energy, global time and PDG code; one "recorded" flag per plane. A gun inside a plane never shows `fGeomBoundary`; the fields are left missing |
| Output | per-event CSV; per-layer calorimeter columns can be switched off; the column map is generated automatically |

**Deliberate simplifications:** uniform field with sharp edges, no magnet material, silicon as whole planes (no
strips, no charge sharing, no δ-ray centroid shifts), unsegmented TOF, no optical photons, no trigger or readout
electronics. The J15 README lists each one.

### 6.5 Digitization and reconstruction

A new script `skills/hep-detector/scripts/digitize_reconstruct.py`, standard library only, does digitization, the
circle fit and β, and nothing else.

| Step | Content |
|---|---|
| Silicon | Gaussian smearing of the crossing points: ε = 10 µm in the bending direction (y), 30 µm in the non-bending direction (z); the fit uses the same x as the scorer (the entry face) |
| TOF | Gaussian time smearing σ_t = 100 ps |
| Track | circle fit in x–y with a multiple-scattering covariance (without it χ²/dof is in the thousands at 1 GV); straight-line fit in x–z; outputs R, χ², degrees of freedom; nominal B |
| True rigidity | the mean of C·B / p_T,i over the six plane-crossing records (C = 0.2998), with the transverse momentum |
| β | path length includes the straight segments TOF1→Si1 and Si6→TOF2 and the 3D dip angle; at low β, the change of β between the TOF planes is reported |
| Calorimeter | total active deposit divided by the **electron** sampling fraction, obtained from a 10 GeV electron sample with the `calibration` role; e/mip is also reported |
| Random numbers | counter hash, separate from Geant4's stream |

Each execution writes a computational-run record whose inputs are the adapter's run records (with hashes); the code
hash goes into the provenance. Changing digitization parameters does not require rerunning the simulation.

Reconstructed result tables (for example rigidity resolution against rigidity) are published as 0.21.0 **simulated
dataset-records**: `extension.status: simulated`, inputs the run records or study record, level `detector`. J15's
study record is `unvalidated`, so the tables stay `unvalidated`; a communication that uses them gets the
`communication.simulated_source` warning, and figures are labelled "Simulation".

### 6.6 Validation ladder

| Check | Grade | Reference | Specification | Negative control |
|---|---|---|---|---|
| overlap | implementation | — | — | shift one Si plane to create an overlap |
| per-event energy balance (J15 geometry) | implementation | energy conservation | — | omit 2 mₑc²; double counting |
| material budget (geantino) | implementation | sum of PDG X₀ | tolerance about 2 % (Geant4's X₀ formula differs from PDG by about 1 %); catches geometry and material-assignment errors | Pb density ± δ |
| `field-propagation` | **verification** | charged geantino against the analytic helix (tests the numerical integration) | see 6.7 | Geant4-side B × (1 ± δ) |
| `field-propagation-muon` | **sanity** | plane-averaged true 1/R (6.5) | μ⁻ at 1, 10, 100 GV; tolerance = t·SE + 0.05 %; N ≈ 400 (1 GV), ≈ 7400 (100 GV) | Geant4-side B × (1 ± 1 %) |
| fitter unit test | test (not a benchmark) | toy truth (R ≥ 300 GV) against `tracker_resolution.py` | — | — |
| one-off scattering comparison | sanity | the analytic term of `multiple_scattering.py` (no log, by its convention); optionally `toy_spectrometer.py` (needs NumPy) | μ and p, 1–10 GV, with β | — |
| `tof-beta` | **verification** (bookkeeping) | kinematics along the true track | — | a scorer test flag injects a time offset; there is no Geant4-side physical control, and the documentation says so |
| `sampling-fraction` | sanity | ratio of ionization dE/dx from the PDG muon energy-loss tables (Groom et al., obtained through hep-citations) at the run momentum | μ⁻ at 1 GeV; statistic Σ PVT deposit / Σ (PVT + Pb) deposit; plausibility band ±10 % (a reviewer's Bethe estimate is about 0.271); seeds distinct from the `calibration` sample | PVT density ± δ |
| shower containment | sanity | PDG gamma profile with the mixture's effective critical energy of about 10.2 MeV | electrons 1–100 GeV | — |
| `longitudinal-profile` (0.21.0) | not applicable | its reference is the published ALICE FoCal-E measurement and holds only for that stack; J15's calorimeter differs and is embedded | — | — |
| optional: stopping power in an isolated PVT slab | reference (`configuration: isolated`) | Bethe (RPP 2024 eq. 34.5) | p at T = 200–600 MeV (βγ ≈ 0.67–1.37, below PVT's 10^x₀ ≈ 1.40, so the density correction is zero), 1 cm slab, nuclear interactions excluded (about 1 %); Sternheimer parameters from Sternheimer, Berger & Seltzer (1984), checked through hep-citations | PVT density ± δ |

The optional last item runs in an isolated slab, not as part of the J15 detector, and shows the upgrade path for a new
material.

### 6.7 Convergence scans

**Field accuracy and maximum step (deterministic, no statistics):**
- Tracks: charged geantinos (massless, β = 1) at 0.6, 1, 10, 100 and 1000 GV.
- Directions: normal incidence; **50 mrad in the bending plane, opposite to the bend** (+y for a positive charge);
  ±50 mrad in the non-bending plane.
- Checked in Appendix A: with these directions every track reaches every Si plane and TOF2 and stays inside the field
  mother. With the bend instead, 0.6 GV and 1 GV miss Si6.
- Reference: the analytic helix; if a track leaves the field region, the reference becomes piecewise straight and only
  the planes the analytic track reaches are compared.

| Scan | Grid | Criterion |
|---|---|---|
| delta intersection | 1e-3, 1e-4, 1e-5, 1e-6 mm | at the nominal value (1e-5), in-plane distance √(Δy² + Δz²) ≤ 0.5 µm (ε/20) at every plane; the finest two settings differ by ≤ 0.2 µm; 1e-3 mm is expected to fail |
| maximum step | 100, 30, 10, 3 mm | same |
| delta one step and epsilon | nominal and 1/10 | no change expected; checked once |
| TOF2 path time | — | \|Δt\| ≤ 1 ps (about 0.3 mm of path); tests the path length only |

**Calorimeter production cut:**
- Grid: 0.1, 0.3, 0.7, 1.0 mm.
- Sample: 10 GeV e⁻; a trial run first, then N per 4.5.
- Observables: total deposit (relative tolerance 1 %, about 400 showers per point) and the rear leakage fraction
  (from the existing `leak_rear_MeV`, rear face only; **absolute** tolerance 0.002, about 5000 showers per point).
- Events per point: the larger of the two.
- Decision per 4.5.

The Si production cut is not part of J15's convergence: it affects only the Si deposit, and J15's Si results are not
evidence. The parameter groups each benchmark depends on are declared in the study spec in advance and checked
against the probe's effective settings.

### 6.8 Variations

| Variation | Scope | Rule |
|---|---|---|
| EM option4 against option3 | calorimeter profile, sampling fraction | `G4R-PRECISION-EM` |
| FTFP_BERT_EMZ against **QGSP_BIC_EMZ** | interaction probability and first-interaction depth in the calorimeter only; nucleons below 1.5 GeV | `G4R-BIC-RANGE`; π below 3 GeV and hadrons at 6–12 GeV use the same models in both, so they are not a variation |
| vacuum against air | multiple scattering, rigidity resolution | — |

### 6.9 Labels and contracts 3.4.0

- The contracts benchmark table gains the J15 checks with grade `verification` or `sanity`; only reference
  benchmarks are counted by `_study_upgrade`.
- **Isolation rule:** under `strict or _at_least(version, "3.4.0")`, every counted benchmark must have
  `configuration == "isolated"`; **missing or `embedded` is an error**. J14 carries the field after its phase 1 and 2
  re-records and passes; older 0.20.0 and 0.21.0 records already fail in phase 1 for the missing kind, covered by the
  advisory.
- `configuration` is derived by the tool from the run geometry; a declared value in a record is not accepted.
  Optionally, `dependencies.py` cross-checks the placement count in the evidence run records.
- **J15's role:** a verification vehicle. Every result in the full detector is `unvalidated`; the README and the study
  record say so.
- `GRADES` in `geant4_benchmarks.py` and the study spec's grade enum gain `verification`.

### 6.10 Recorded-data budget

- `check_packaging.py` limits each file to 2 MiB; J14's `recorded/` is 2,447,979 bytes (2.45 MB).
- J15's CSV of about 200 columns is about 2 kB per event, about 20 MB for 10⁴ events, and cannot be committed as is.
- J15 commits only: replay files with reduced columns (as J14's `REDUCED`), the digitization and reconstruction
  outputs, the probe output and the column map.
- Acceptance: every file ≤ 2 MiB; J15's `recorded/` ≤ 3 MB in total.

### 6.11 Registration and documentation

| Item | Content |
|---|---|
| Script count | `DetectorScriptCount` in `tests/skills/test_documented_output_claims.py` from 21 to 22; the strings checked at lines 74–78 of the same file and "twenty-one scripts" at line 47 of `docs/capability-matrix.md` become "twenty-two" |
| Script lists | `skills/hep-detector/README.md` (line 21), `tests/skills/test_cli_robustness.py`, `tests/skills/hep_detector/test_script_guards.py`, `tests/skills/hep_detector/test_hep_detector_audit.py` |
| Routing table | one line (≤ 150 bytes) in the routing table of `skills/hep-detector/SKILL.md`, which counts toward quick load; confirm ≤ 25,600 bytes with `measure_entrypoints.py`; details go in `geant4-study-protocol.md` |
| Journey | J15; `docs/researcher-journeys.md`, the example table in `docs/maintenance.md`; `tests/examples/test_geant4_minimal_spectrometer.py` (replay compared with the committed outputs) |
| Capability | `docs/capability-map` (new items under `full-detector-simulation`, then `capability_map.py --write`), `docs/capability-matrix.md` |
| Routing | a J15 routing case; since 0.21.0 `check_routing_static.py` reads the journey list from `docs/researcher-journeys.md`, so once J15 is listed a routing case is **required**. Rerun the live Geant4 cases, including the existing Traditional Chinese under-specified case `g4-underspec-2` |
| Shared stanza | text **unchanged** (point 5 says "3.1.0 upgrade rule"; changing it touches every SKILL.md and requires a live routing rerun) |
| Other | `reference_inventory.py --check`, CHANGELOG, release manifest, adapter 0.3.0, `FieldSetup.*` in `SIM_SOURCES` |

### 6.12 Phase 3 acceptance

- [ ] The J15 geometry passes overlaps, material budget and per-event energy balance; the checked numbers in 6.1 and
  6.2 are recomputed by tests.
- [ ] The MT test command reports distinct field-manager pointers per thread; the field parameters recorded by the
  probe match the spec.
- [ ] The deterministic field checks of 6.7 pass at the nominal settings; delta intersection 1e-3 mm fails as
  expected.
- [ ] `field-propagation`, `field-propagation-muon`, `tof-beta` and `sampling-fraction` run; each negative control is
  caught per 6.6, or the absence of a control is stated.
- [ ] The fitter unit test passes against `tracker_resolution.py`.
- [ ] Contract tests of the isolation rule: a missing configuration, `embedded`, and a grade that disagrees with the
  contracts table are all refused; J14 still passes under `--strict`.
- [ ] Recorded-data budget, registrations and documentation complete; VALIDATION entry GEANT4-J15.
- [ ] An independent agent, using only the documentation and tools, completes "rigidity resolution of 1 GV protons in
  J15": the result record passes `validate.py --strict`, carries `unvalidated`, and the resolution lies within the
  ranges of the 6.2 table, with no help from the maintainer.

---

## 7. Dropped and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| `uses-validated-physics` label | dropped | the hash is both too strict and too loose, and bypasses the scope check |
| `physics_config_comparison` annotation | deferred | no consumer today; J15 cannot reuse J14. Trigger: a study that needs to compare physics settings; then the diff must take run records' `effective_config` through `evidence_records`, handle `probe_version` differences, and fail closed when `effective_config` is missing |
| stopping adaptively on the SE; refined scans as evidence | dropped | optional-stopping bias |
| σ(1/R) in the measurement-dominated regime as a benchmark | dropped | a fitter unit test instead |
| two geometry formats in C++ | dropped | conversion in Python instead |
| a new core validator; rewriting the tracking and scattering formulas | dropped | reuse `contracts/schema.py`, `tracker_resolution.py`, `multiple_scattering.py` |
| column map in the contracts | dropped | stays in the adapter (`layered_sim.output/2`) |
| contracts 4.0 | dropped | new optional blocks and gated rules are minor |
| ion source and Birks visible energy (future J16) | deferred | trigger: a cosmic-ray nuclei study and a literature record for PVT's Birks constant. Per 11.4.3: get the ion with `GetIon(Z, A)` in `GeneratePrimaries`; set kB in `Construct`, `SetBirksActive(true)` in PreInit, then obtain it with `G4LossTableManager::Instance()->EmSaturation()` |
| rule version ranges; moving physics knowledge out of Python | deferred | trigger: support for a second Geant4 version |
| benchmark registry | deferred | replaced by the contracts table and enum-consistency tests; trigger: the number of benchmarks outgrows the tests |
| `inspect` and a Linux environment | deferred | trigger: a user who needs to run on CVMFS or LCG; needs a new environment number |
| GDML, field maps, fringe fields | deferred | trigger: a study that needs real geometry or field shape |
| user-application backend, embeddable probe | deferred | trigger: the first experiment application; needs G5 re-approval |
| ReferenceMaterial contract | deferred | trigger: the first reference benchmark in a non-slab geometry |
| columnar output | deferred | trigger: per-hit data is needed and the root-uproot adapter is available |
| in-simulation bootstrap, content-addressed cache, new executors, replay backend | dropped or deferred | not needed at the current scale; a complete cache key is hard |
| generalized `scoped_upgrade` | deferred | trigger: a second kind of study needs upgrades (today only Geant4 study records) |
| Geant4 10.x probe | deferred | trigger: the first application on 10.x; APIs such as `StreamInfo` (from 10.2) and `FluctuationType()` (from 11.x) need version-conditional compilation |

---

## 8. Statistical rules at a glance

| Item | Rule | Section |
|---|---|---|
| Stopping | only at the N declared in advance; a missed target is unresolved, no top-up | 4.5 |
| Two-stage factor | SE from K = 16 sub-runs: f = F₀.₉₀(15,15) ≈ 1.97; from a large-sample bootstrap: 1.2 | 4.5 |
| Convergence gate | IUT: pass with q₀.₉₅, fail with q₁₋α/m; t when the SE is estimated (difference ν ≈ 30), z otherwise; se of the difference; se ≤ tol/4 set in advance | 4.5 |
| Deterministic gate | charged geantino for field accuracy and maximum step | 6.7 |
| MPV | mean of the MPVs of 16 partition sub-runs; fixed bin width; SE = sd/√16; t₁₅; the full-sample MPV is a diagnostic | 4.5 |
| Bootstrap | 64-bit counter hash, inverse CDF, globally unique event keys, R ≥ 400; not for the MPV | 4.5 |
| Seeds | `H(study_id, role, point_id, k)` → two positive integers | 4.5 |
| Negative controls | shift in the observable, both signs | 4.4 |
| Correlated evidence | `evidence_overlap` | 4.5 |
| Versions of new blocks | `probe_version`, `column_map_version`, `evidence_overlap_version` | 4.5, 5.6 |

---

## 9. Contracts and versions

| Object | Location | Version |
|---|---|---|
| simulated dataset-record | `contracts/validate.py` | 3.2.0 (existing in 0.21.0) |
| scope compares observable kind; benchmark table; grades not self-declared | `contracts/validate.py` | 3.3.0 (minor, gated, sci-fix) |
| schema keyword extension | `contracts/schema.py` | no version change |
| table gains verification; isolation rule | `contracts/validate.py` | 3.4.0 (minor, gated) |
| `effective_config`, `evidence_overlap` | free-form blocks of computational-run | no contract change |
| `layered_sim.spec/2`, `layered_sim.output/2`, `column_map` | adapter | adapter 0.2.0, 0.3.0 |
| `GRADES`; emitting kind and configuration | hep-detector | with the plugin version |

hep-computing owns the computational-run schema; this proposal does not change it.

---

## 10. Checks at the end of every phase

- `run_all_checks.py` (including the CI lock environment)
- `check_layering.py`, `check_relocation.py`, `check_ownership.py`, `check_packaging.py`
- `measure_entrypoints.py` (hep-detector quick load ≤ 25,600 bytes)
- `reference_inventory.py --check`, `capability_map.py --check`, `check_routing_static.py`
- `validate.py --strict` and `dependencies.py` on every study record
- `tests.adapters.test_geant4` offline and live (`HEP_GEANT4_LIVE_TEST=1`)
- an agent that did not write the code runs a new question, with a pass criterion
- VALIDATION entry, CHANGELOG, release manifest

---

## 11. Decisions for the maintainer and residual risks

**To decide:**
1. The version class of phase 1. This proposal follows the convention of gates at x.y.0 and makes it 3.3.0 (minor)
   plus a sci-fix; if the maintainer prefers a patch, the first patch-level gate (3.2.1) sets a new precedent.
2. Whether a statistical comparison is acceptable if bit-identical output cannot be reached even on the same host
   (with the reason recorded in VALIDATION).
3. How to confirm the G5 statement that no example code was copied.

**Residual risks:**
1. J14's detection limits may change with the sub-run estimator, t quantiles and controls in observable units; the
   controls may need to be redesigned.
2. The mean of sub-run MPVs and the full-sample MPV differ slightly (about 0.25 % in a reviewer's toy); the sci-fix
   record explains this.
3. Only 931 bytes of quick-load budget remain.
4. The sampling-fraction reference needs the PDG muon energy-loss tables; the optional PVT benchmark needs Sternheimer
   parameters. Both must come through hep-citations literature records before use.
5. Calorimeter showers dominate the CPU time; rear-leakage convergence needs about 5000 showers per point, and the
   event count is set by a trial run and recorded.
6. The probe assumes that workers have the master's settings; if a thread-local difference appears, dump per thread.
7. For `longitudinal-profile`, `isolated` guarantees only that the geometry holds nothing but the target; whether the
   target stack is the published measured configuration cannot be decided by the contract and is checked by a reviewer
   with `target_geometry_sha256`.

---

## 12. Re-check against 0.21.0 (2026-10-21)

This document was first written against 0.20.0. After 0.21.0 (`main` at `c4f7954`) was merged, every item was
re-checked in an isolated worktree (branch `worktree-geant4-architecture`).

**0.21.0 changes and their effect**

| 0.21.0 change | Effect on this proposal | Handling |
|---|---|---|
| contracts 3.2.0: simulated dataset-record | the 3.2.0 planned here is taken | phase 1 becomes 3.3.0, phase 3 becomes 3.4.0 |
| simulated dataset-record: a table may drop `unvalidated` when an input study record is `validated-in-scope` | the scope holes (D1, D2) reach tables through this path | covered by the advisory (4.7); J15's reconstructed tables use this format (6.5) |
| new reference benchmark `longitudinal-profile` (ALICE FoCal-E) | must enter the contracts table; its target is a whole sampling stack, which the original "a single slab" definition of isolated would misjudge | added to the table (4.1); configuration defined by the benchmark target, with a target-geometry hash (4.3) |
| the study-spec benchmark enum still lacks `shower-containment`, and also `longitudinal-profile` | D8 grows | both added in 4.6 |
| layered_sim supports mixtures (`components`) | nothing to do in phase 3; the spec/1 → spec/2 conversion and bit identity must keep the material order | 5.3, 5.5, 6.4 |
| `multiple_scattering.py` reports `intrinsic_coefficient` and warns below N = 10; the reported values still use Gluckstern | the text of 6.2 needed updating | 6.2 |
| `check_routing_static.py` reads journeys from `docs/researcher-journeys.md` | once J15 is listed, a routing case is required | 6.11 |
| `geant4.def` pins the base image by digest | none | — |

**Defects still present (0.21.0 line numbers)**

| # | Location | Status |
|---|---|---|
| D1 | `validate.py` `_scope_inside()` line 327; `check_geant4_study.py` `scope_within()` line 481 | not fixed |
| D2 | `validate.py` `_study_upgrade()` line 373, filter at line 397 | not fixed |
| D3 | `geant4_benchmarks.py` line 678 | not fixed |
| D4 | `check_geant4_study.py` line 358 | not fixed |
| D5 | `geant4_benchmarks.py` line 369 | not fixed |
| D8 | study-spec enum 7 names, `GRADES` 9 | grown |

**Other checked values**

| Item | 0.21.0 value |
|---|---|
| `CONTRACTS_VERSION` | 3.2.0 |
| `GEANT4_UPGRADE_FROM` | 3.1.0 (line 324) |
| `SUPPORTED_KEYWORDS` | still no maxItems, maximum, exclusiveMaximum |
| `SIM_SOURCES` | 11 files, unchanged |
| `validate_spec()` | still at `geant4_run.py` line 103, now with mixture checks |
| `DetectorScriptCount` | 21; line 47 of `docs/capability-matrix.md` still says "twenty-one scripts" |
| adapter geant4 | 0.1.0, `demonstrated-on-synthetic-data` |
| shared stanza point 5 | still says "3.1.0 upgrade rule" |
| J14 `recorded/` | 2,447,979 bytes |
| hep-detector quick load | 24,669 / 25,600 bytes |
| `check_packaging.py` MAX_BYTES | 2 MiB |
| advisories | latest SFA-2026-035 |
| journey table | J1–J14 |

---

## Appendix A: numbers

Script: `j15_design_estimates.py` (in this folder; standard library, scipy optional; A_N checked against the closed
form by an exact rational least-squares computation).

**Geometry**
- Si centres: −500, −340, −180, −20, 140, 300 mm; L = 0.800 m.
- Field region: −520 … 320 mm; margins of 19.85 mm at both ends.
- TOF centre distance D = 1.300 m; world ±1200 mm.

**Tracking**
- A_N = 720 (N−1)³ / [(N−2) N (N+1)(N+2)]: A₄ = 81.0, A₆ = 66.96, A₈ = 57.17 (N equally spaced points including both
  ends, equal weights).
- MDR (measurement term alone) = C B L² / (ε √A_N): 1172 GV with C = 0.2998 (1173 GV with C = 0.3).
- Scattering term (β = 1, with the log): 1.34 %, bracketed by the 1.0–1.4 coefficient.

| B (T) | N | MDR (GV) | Scattering term (β = 1) | Rigidity where the terms are equal |
|---|---|---|---|---|
| 0.15 | 6 | 352 | 4.5–6.2 % | 16–22 GV |
| **0.5** | **6** | **1172** | **1.3–1.9 %** | **16–22 GV** |
| 1.0 | 6 | 2345 | 0.7–0.9 % | 16–22 GV |
| 0.5 | 4 | 1066 | 1.1–1.5 % | 11–16 GV |
| 0.5 | 8 | 1269 | 1.6–2.2 % | 20–28 GV |

**Field-check grid** (50 mrad opposite to the bend, positive charge):

| Rigidity | Max \|y\| in the field | y at Si1 … Si6 (mm) | y at TOF2 |
|---|---|---|---|
| 0.6 GV | 29.0 | 25.0, 29.0, 26.6, 17.8, 2.5, −19.3 | −51.6 |
| 1 GV | 32.4 | 25.0, 30.6, 32.4, 30.3, 24.4, 14.6 | −0.6 |
| 10 GV | 60.7 | 25.0 … 60.0 | 67.5 |
| 1000 GV | 66.0 | 25.0 … 65.0 | 75.0 |

With the bend (−50 mrad): at 0.6 GV y = −151 mm at Si6, at 1 GV −116 mm; both miss Si6.

**TOF**: σβ/β = √2 σ_t c / D; 2.6 %, 3.3 % and 4.9 % for 80, 100 and 150 ps.

**Calorimeter**: 18.41 X₀, 0.886 λ_I, 35 cm; effective Molière radius 3.95 cm; the minimum-ionization loss ratio 0.284
is only a ratio of dE/dx_min, **not** a reference value.

**Material in front of the calorimeter**: 6.62 % X₀ (71 % from TOF), 2.93 % λ_I.

**Statistics**
- Probability of meeting the target: judged on the true SE, P(χ²₁₅ ≥ 15/f): 0.641 at f = 1.2, 0.90 at f = 1.755.
  Judged on the estimated SE, P(F₁₅,₁₅ ≤ f): 0.636 at f = 1.2, 0.856 at f = 1.755, **0.90 at f = 1.972**.
- t₀.₉₅(30) = 1.697, t₀.₉₅(15) = 1.753, t₀.₉₇₅(15) = 2.131.
- Event counts (se of the difference ≤ tol/4): total deposit of 10 GeV electrons (tolerance 1 %) about 392; rear
  leakage (absolute tolerance 0.002) about 5000.

## Appendix B: sources

- PDG Atomic and Nuclear Properties (retrieved 2026-10-21):
  [Silicon](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/silicon_Si.html),
  [Lead](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/lead_Pb.html),
  [Polyvinyltoluene](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/polyvinyltoluene.html)
- PDG Review of Particle Physics 2024, chapter 34: eqs. 34.5, 34.12, 34.16, 34.34–34.36 (equation numbers as in the
  plugin's VALIDATION GEANT4-STUDY)
- Geant4 v11.4.3 source (`github.com/Geant4/geant4`, tag `v11.4.3`); files read during the reviews include
  `G4RunManager.cc`, `G4RunManagerKernel.cc`, `G4MTRunManager.cc`, `G4TaskRunManager.cc`, `G4WorkerRunManager.cc`,
  `G4EmParameters.cc`, `G4EmParametersMessenger.cc`, `G4EmExtraParametersMessenger.cc`, `G4ProductionCutsTable`,
  `G4HadronicInteraction.hh`, `G4HadronicProcess.hh`, `source/analysis/`, `G4FieldManager.hh`, `G4ChordFinder.hh`,
  `G4PropagatorInField.cc`, `G4FieldBuilder`, `G4FieldParameters`, `G4LogicalVolume`, `G4ChargedGeantino.cc`,
  `G4EmBuilder`, `G4EmSaturation`, `G4LossTableManager`, `G4IonisParamMat`, `G4IonTable`, `FTFP_BERT.cc`,
  `G4PhysListFactory`, `G4NistMaterialBuilder.cc`, `G4PVPlacement`, `G4QuickRand.hh`, `G4GeomTestVolume.cc`
- Geant4 Book for Application Developers,
  [Basic Examples](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html)
  (B4, B5; development documentation)
- hep-research 0.21.0 (`c4f7954`): `contracts/validate.py`, `contracts/schema.py`,
  `contracts/stanzas/context-resolution.md`, `skills/hep-detector/` (`SKILL.md`, `README.md`, `check_geant4_study.py`,
  `geant4_benchmarks.py`, `tracker_resolution.py`, `multiple_scattering.py`, `toy_spectrometer.py`),
  `adapters/geant4/`, `examples/geant4-thin-silicon/`, `docs/maintenance.md`, `docs/capability-matrix.md`,
  `tools/measure_entrypoints.py`, `tools/check_packaging.py`, `tests/skills/test_documented_output_claims.py`,
  `CHANGELOG.md`, `VALIDATION.md`
- Still to obtain: the PDG muon energy-loss tables (Groom, Mokhov & Striganov); Sternheimer, Berger & Seltzer (1984),
  *Atomic Data and Nuclear Data Tables* 30, 261

## Appendix C: version history

| Version | Main content | Reviews and main corrections |
|---|---|---|
| v2 | four layers, four contracts, three backends | two reviews: probe timing, EM parameters locked, SE-stopping bias, `uses-validated-physics`; found the current scope defect |
| v3 | reduced to three batches | — |
| detector note | single-axis stacked magnetic spectrometer | Gluckstern small-N formula corrected |
| v4 | merged into five phases | three reviews: inconsistent geometry, J14 would fail, infeasible convergence, upgrade limits not enforced by the contract, duplicated implementations |
| v5 | three phases | two reviews: field direction, field-check grid, MPV estimator, F-distribution factor (0.74 corrected to 0.64), self-declared grades, isolation loophole, seed index, several plugin facts |
| final | three phases; every review finding handled | — |
| **final (0.21.0 baseline)** | **re-checked against 0.21.0: contract versions shifted, `longitudinal-profile`, mixtures, simulated dataset-record, journey check** | see section 12 |
