# Task B: `element_sim`, reconstruction and the J15 minimal spectrometer

> Document type: implementation spec (for the implementing agent and reviewers). Status: awaiting the user's and the maintainer's approval
> Plan: [`plan.en.md`](plan.en.md) (stage order, numbering, interface ownership, gates, open decisions). Rationale: [`architecture.en.md`](architecture.en.md). This document is the executable spec of B1, B2 and B3; where it disagrees with other documents, this document wins on content and acceptance, and the disagreement is reported
> Order: B1 after A2; B2 after B1; B3 after B2. Task C's C2 waits only for B2, C3 for B3
> Baseline: at writing, the same as task A (hep-research `main` at `9f08796`, contracts 3.5.0, Geant4 11.4.3); must be rechecked before starting (§0)
> Date: 2026-10-23
> Language: English translation of the Traditional Chinese original [`task-b-j15.md`](task-b-j15.md), with the same content. If they disagree, the Chinese wins and the English is corrected at the same time
> Nature of the example: J15 is a **synthetic geometry**, a carrier for verification, not any experiment's detector; the closest real instruments are PAMELA and AMS-02 (§4.3)

---

## 0. Task card

**Goal.** Add a general box-element Geant4 program `element_sim` as a second backend (field, plane crossings, calorimeter leakage, per-event ROOT files), add the reconstruction program `simreco` (not linked to Geant4) and new validation classes, then use them to complete the J15 minimal-spectrometer study.

**Three stages (in order, each merged separately):**

| Stage | Content | Version |
|---|---|---|
| **B1** `element_sim` and event files | `element_sim.spec/1` and `element_sim` (box elements, one level of nesting, field, plane crossings, calorimeter leakage); per-event ROOT files; `simroot`; `geant4_run.py check-spec`; interface consistency between the two backends; deterministic field check | geant4 adapter **0.3.0** |
| **B2** Reconstruction and contracts | `simreco` (digitization and reconstruction, portable random numbers); `geant4_run.py reco` and `table`; transitive processing chains; verification, regression and surrogate classes and table entries; the decision engine's `change`; the regression role | geant4 adapter **0.4.0**, contracts **CV2** (minor) |
| **B3** J15 study | Validation ladder, calorimeter cut convergence, variations, TOF σ_t sensitivity, recorded data, J15 journey and docs | example and docs (adapter not bumped) |

**Out of scope:** changes to task A's interfaces (if needed, first as an adapter patch release within task A); new geometry features in `layered_sim` (frozen); task C's design search; ion sources and Birks (J17); non-box geometry and field maps (§9).

**Deliverables:** `element_sim`, `simroot`, `simreco` and their tests; `geant4_run.py check-spec`, `reco`, `table`; the CV2 contract changes; the J15 example (a new folder under `examples/`, README, recorded data); J15 journey and routing case; VALIDATION entries GEANT4-ELEMENT (B1), GEANT4-RECO (B2), GEANT4-J15 (B3); CHANGELOG; release manifest.

**Definition of done:** every box in the acceptance lists B1.9, B2.6 and B3.8 is ticked; every check in task A §8 passes; gates G-B1a and G-B1b (plan §6) pass.

**Main decisions:**
1. **A new backend, not a change to `layered_sim`.** `element_sim` leaves J14's program untouched and validates the output-side interface with a real second backend (architecture §3.2).
2. **Field accuracy by deterministic checks.** Charged geantinos against an analytic helix, no statistics needed; completed in B1 (B1.7).
3. **Infrastructure separated from the physics study.** B2 does only `simreco` and the contracts, so task C's C2 does not wait for the J15 study (plan P3).
4. **J15 is a verification carrier.** Every result in the full detector is `unvalidated`; only an optional benchmark run in an isolated slab shows the upgrade path for a new material (B3.2).
5. **No new scripts in hep-detector.** Reconstruction is in C++ in `simreco`, its interface in the adapter; quick load and description unchanged.

**Before starting:**
1. Confirm that A2 is merged and that the interfaces listed in §2 exist.
2. Using the method of task A appendix C, recheck the facts this document quotes against the `main` of that time (quick load, description length, journey list, `DetectorScriptCount`, contracts version, structure of `MISSING_FILE_ARGS`), and update this document (both languages).
3. Read task A §1, §3, §4 and plan §4–§6; this document does not repeat them.

---

## 1. Terms and files

| Term | Meaning |
|---|---|
| J15 | The minimal spectrometer of this task (synthetic geometry) |
| `element_sim` | The Geant4 program added in B1; spec `element_sim.spec/1` |
| Bending plane | The x–y plane (B along z); the non-bending direction is z |
| Rigidity R | p/\|q\|, in GV; C = 0.2998 GV/(T·m) |
| MDR | Maximum detectable rigidity: the rigidity at which σ_R/R = 1 counting only the measurement term |
| TOF station | TOF1 or TOF2; two layers (a, b) per station |
| charged geantino | A Geant4 charged test particle that feels only the field, with no material interactions (mass 0, β = 1) |
| Processing chain | simulation → reduction → digitization and reconstruction → table, one computational-run record per step |
| Notation | "B1.3" is a work item of this document; "§4.2" a section of this document; "A1.6", "C2.1" work items of tasks A and C; "task A §3", "plan §4", "architecture §6" sections of other documents |

**Main files (relative to `plugins/hep-research/`):** `adapters/geant4/assets/g4sim/` (created in A2, extended here); `adapters/geant4/assets/element_sim/` (new); `adapters/geant4/assets/simroot/` (new); `adapters/geant4/assets/simreco/` (new, not linked to Geant4); `adapters/geant4/assets/geant4_run.py` (new `check-spec`, `reco`, `table`; `SIM_SOURCES` lines 63, 327); `core/stats/decisions.py` (B2 adds `change`); `contracts/validate.py`, `contracts/dependencies.py` (CV2); `skills/hep-detector/scripts/geant4_benchmarks.py` (`GRADES`, new benchmark functions); `skills/hep-detector/assets/geant4-study-spec.schema.json`; `skills/hep-detector/references/geant4-study-protocol.md`; `tests/skills/test_cli_robustness.py` (`MISSING_FILE_ARGS`, `geant4_run.py`'s entry at line 130); `docs/researcher-journeys.md`, `docs/maintenance.md`, `docs/capability-matrix.md` (`DetectorScriptCount` line 47), `docs/capability-map`; `tests/examples/test_geant4_minimal_spectrometer.py` (new).

---

## 2. Prerequisites and provided interfaces

**Prerequisites (provided by task A):**

| Interface | Use in task B |
|---|---|
| Benchmark table, validation classes, scope comparison, isolation rule (A1.1–A1.3) | B2 adds verification, regression, surrogate and J15 entries; J15's benchmarks are all embedded and do not count for upgrade |
| Evidence roles and uniqueness of S (A1.4) | B2 adds the regression role |
| Block estimators, exact intervals, MPV, the decision engine's `equivalence`, two-stage event count (A1.6–A1.10) | Decisions in B3; B2 adds `change` through the same interface |
| `simulation-summary/1`, `simulation-observables/1` (A1.5) | `element_sim` and `simreco` write summaries with the same schema |
| `g4sim`: `SimHash.hh`, `SimSeed.hh`, `SimSummary.hh`, `MiniJson.hh`, `SimProbe.hh`, material and physics-list helpers (A2.1) | `element_sim` uses all of them; `simreco` only the Geant4-free `SimHash.hh`, `SimSummary.hh`, `MiniJson.hh` |
| `per-event` seeding (reseeded at the start of `GeneratePrimaries`, A2.2) | `element_sim` supports only `per-event` |
| Three boundary artifacts, name-free `tree-v1`, effective-config storage (A2.3–A2.6) | `element_sim` and `simreco` deliver the same boundary artifacts; the study layer needs no change; a field attached inside the target counts in the `tree-v1` target hash |
| Schema keywords `maxItems`, `maximum`, `exclusiveMaximum` (A2.7) | The `element_sim.spec/1` schema |

**Interfaces provided to task C:**

| Interface | Work item | Use in task C |
|---|---|---|
| `element_sim.spec/1` and `geant4_run.py check-spec` | B1.1, B1.6 | C1 validates realizations through a subprocess; F1/F2 evaluation in C2 |
| Calorimeter mother and `leak_*_MeV` | B1.3 | Objectives of calorimeter components |
| `simreco` (rigidity, β, calorimeter energy) | B2.1 | Reconstruction at F1/F2 |
| Decision engine `change`, surrogate class | B2.4 | C2 positions F0 and F1 as surrogates; C2 adds `threshold` and `order` |

---

## 3. Hard rules

All of task A §3 applies. In addition:

1. Do not change `skills/hep-detector/SKILL.md` or hep-detector's description (quick load has only 931 bytes left; description 1,016 / 1,024 characters). J15's routing case must reuse trigger words already in the description.
2. No experiment names in `skills/`, `contracts/` or `core/`; the contract table and the protocol refer to `longitudinal-profile`'s reference by citation key. Experiment names (PAMELA, AMS-02) may appear only in `docs/` and in J15's `examples/` README.
3. Field code is written from the Geant4 API, without copying or adapting the B5 example's code (G5).
4. The text of the shared stanza is not changed (point 5 says "3.1.0 upgrade rule"; changing it would touch every SKILL.md and rerun the live routing).
5. J15's `recorded/`: each file ≤ 2 MiB, total ≤ 3 MB; ROOT files are not committed (B3.6).
6. All J15 results are `unvalidated`; no J15 benchmark may count for upgrade.
7. No geometry features are added to `layered_sim`; new geometry features go only into `element_sim`.
8. Neither Python nor `simreco` parses ROOT directly; always through `simroot`.
9. Contract rules are gated with `strict or _at_least(contract_version, CV2)`.

---

## 4. J15 design

### 4.1 Geometry

Coordinates: origin at the world centre, stacking axis x, unit mm.

**Magnetic field: B = (0, 0, +0.5 T).** The bending plane is x–y, the non-bending direction z. A positive charge moving along +x bends towards −y; μ⁻ bends towards +y.

```
x:  −1000   −810 … −780   −520 −500        …         300  320    490 … 520   550          900   ±1200
     gun    TOF1 (2 layers)│ Si1  Si2  Si3  Si4  Si5  Si6  │     TOF2 (2 layers) calorimeter 50 layers  world edge
            10 + 10 mm    │◄────── uniform field 0.5 T ẑ (−520 … 320) ─────►│  10 + 10 mm   Pb 2 / PVT 5 mm
```

| Element | Material | Front face x | Thickness | Extent | Transverse (y × z) |
|---|---|---|---|---|---|
| World | `G4_Galactic` | — | 2400 | −1200 … 1200 | 1200 × 1200 |
| Particle source | — | x = −1000, y = z = 0 | — | — | — |
| TOF1a, TOF1b | `G4_PLASTIC_SC_VINYLTOLUENE` | −810, −790 | 10 each | −810 … −800, −790 … −780 | 300 × 300 |
| Field-region mother | `G4_Galactic` | −520 | 840 | −520 … 320 | 300 × 300 |
| Si1–Si6 (daughters) | `G4_Si` | −500.15 + 160k | 0.3 | centres −500, −340, −180, −20, 140, 300 | 200 × 200 |
| TOF2a, TOF2b | `G4_PLASTIC_SC_VINYLTOLUENE` (same as TOF1) | 490, 510 | 10 each | 490 … 500, 510 … 520 | 400 × 400 |
| Calorimeter mother | `G4_Galactic` | 550 | 350 | 550 … 900 | 500 × 500 |
| Calorimeter sampling layers (daughters) | 50 × (`G4_Pb` 2 + PVT 5) | 550 | 350 | 550 … 900 | 500 × 500 |

**TOF stations.** TOF1 and TOF2 have two layers each; all four layers have the same material and thickness (10 mm), with a 10 mm vacuum gap between the two layers of a station. Each layer is a whole slab, not segmented, with no paddle direction (a deliberate simplification); the two layers give two independent time measurements and dE/dx samples, and make the consistency of a station's two layers a check (B3.2).

**Checks** (the program of appendix A, recomputed in tests):
- Measurement lever arm L = 0.800 m; the front edge of Si1 and the back edge of Si6 are each 19.85 mm from the mother's boundary.
- The field extends 20 mm beyond each end of the measurement region.
- Distance between the TOF station centres (the midpoint of the two layers: −795, 505 mm) D = 1.300 m.
- The back face of TOF2's rear layer (520) is 30 mm from the calorimeter's front face (550); TOF1's front layer (−810) is behind the source (−1000).
- The world contains the source and the back of the calorimeter.

Materials (NIST definitions in 11.4.3 against PDG): `G4_PLASTIC_SC_VINYLTOLUENE` 1.032 g/cm³, I = 64.7 eV; `G4_Si` 2.33 g/cm³ (PDG 2.329).

**Deliberate simplifications** (listed one by one in J15's README): uniform field with sharp edges, no magnet material, silicon as whole planes (no strips, no charge sharing, the centroid shift from δ rays not simulated), TOF layers not segmented, no optical photons, no trigger or readout electronics, no anticoincidence.

### 4.2 Parameters and acceptance

| Parameter | Value | Basis |
|---|---|---|
| B | 0.5 T | The rigidity at which the multiple-scattering term equals the measurement term is about 16–22 GV (μ), independent of B; 0.5 T gives one decade each at 1–10 GV and 100–1000 GV |
| Si planes | 6 | N = 4 leaves only 1 degree of freedom in the bending plane; N = 8 improves the MDR by only about 8 % |
| MDR | about 1172 GV | Measurement term only. Reference value from the exact least squares of `tracker_resolution.py` (C = 0.2998). `mdr_intrinsic_only_gv` of `multiple_scattering.py` has the same definition but uses the Gluckstern approximation (about 1131 GV for N = 6); from 0.21.0 it also outputs `intrinsic_coefficient` and warns for N < 10 |
| TOF | Two layers per station; σβ/β ≈ 2.3 % (100 ps per layer, two independent layers, β = 1; 3.3 % with one layer per station); 3.5 % at 150 ps | D = 1.3 m; the station time is the mean of the two layers, σ_station = σ_layer/√2 |
| Calorimeter | 18.4 X₀, 0.886 λ_I, 50 cm wide | Enough to separate e/p by shower shape, not enough to measure hadron energy |

**Multiple-scattering term.** Highland formula, with the log term taken over the total thickness, times a factor 1.0–1.4. The review did an exact least-squares fit with discrete scattering planes, giving a factor of 1.02 (weighted) to 1.06 (unweighted). `multiple_scattering.py` by its convention **excludes** the log term; state the difference when comparing.

| Particle | Rigidity | β | Multiple-scattering term | Rigidity where the two terms are equal |
|---|---|---|---|---|
| μ | 1 GV | 0.994 | 1.3–1.9 % | 16–22 GV |
| p | 0.6 GV | 0.539 | 2.5–3.5 % | 29–41 GV |
| p | 1 GV | 0.729 | 1.8–2.6 % | 21–30 GV |
| p | 2 GV | 0.905 | 1.5–2.1 % | 17–24 GV |

**Acceptance** (unit charge, on-axis normal incidence, uniform field, sharp edges):

| Condition | Minimum rigidity |
|---|---|
| Does not leave the side of the field-region mother before x = 320 (\|y\| ≤ 150 mm) | 0.364 GV |
| Reaches Si6 (\|y\| ≤ 100 mm) | 0.511 GV |
| Reaches TOF2's front layer (x = 490, \|y\| ≤ 200 mm) | 0.385 GV |
| Passes both TOF2 layers (x = 520, \|y\| ≤ 200 mm) | 0.404 GV |
| Calorimeter front face, shower axis within 250 − 2 R_M,eff | 0.490 GV |
| Calorimeter back face, same | 0.745 GV |

Overall threshold 0.75 GV; 0.51 GV when only the track plus TOF is required. Below 0.364 GV the track leaves the side of the field region and then travels in a straight line in the field-free world.

Electrons: the shower axis is displaced 82 mm and 127 mm at the calorimeter's front and back faces at 1 GeV, 16 mm and 25 mm at 5 GeV. Bremsstrahlung photons from the upstream 11.3 % X₀ (83 % of it in the four TOF layers) are not bent, so the shower axis is not a straight extrapolation; the 79 mm margin is a geometric estimate, and the shower checks must be checked against the actual transverse energy distribution. Electron shower checks are limited to 1 GeV and above.

**Upstream energy loss** (Bethe integral, 2 cm of PVT in TOF1's two layers):

| Proton rigidity | Kinetic energy | TOF1 energy loss | Δp/p | Change in β between the station centres |
|---|---|---|---|---|
| 0.6 GV | 175 MeV | 10.23 MeV | 3.20 % | 2.87 % |
| 1 GV | 433 MeV | 6.00 MeV | 0.82 % | 0.46 % |
| 2 GV | 1271 MeV | 4.34 MeV | 0.24 % | 0.05 % |

At 0.6 GV, β changes by 2.87 % between the stations, more than the TOF resolution (2.3 %): β comparisons at low rigidity need a β model with energy loss, or are limited to 2 GV and above. TOF1 is before the first Si plane and does not affect curvature resolution; the true rigidity is taken from the crossing records of the Si planes.

**J14 cannot be reused.** J15's Si differs from J14's in material (`G4_Si` vs `Si_study`), physics settings and cuts, and J15 records only entry, so it cannot form J14's E_in − E_exit observable.

### 4.3 Comparison with real instruments

| Instrument | Configuration (sources in architecture §14) | Compared with J15 |
|---|---|---|
| PAMELA | 0.43 T permanent magnet; 6 double-sided silicon microstrip planes, resolution better than 4 µm; MDR above 1 TV; three TOF planes (S1–S3, segmented into paddles); W/Si imaging calorimeter 16.3 X₀, 0.6 λ; also anticoincidence, S4, neutron detector | Almost the same type; J15 assumes 10 µm Si resolution (more conservative), unsegmented TOF and no anticoincidence |
| AMS-02 | Four TOF planes (8, 8, 10, 8 counters); system about 140 ps for protons | J15's 100 ps per layer is more optimistic, hence the 100 and 150 ps sensitivity (B3.5) |

J15's README uses this table to show that J15 is reasonable, and stresses that J15 is a synthetic geometry that represents no experiment.

---

## 5. Stage B1: `element_sim` and event files (geant4 adapter 0.3.0)

### B1.1 `element_sim` and its spec

**Location:** `adapters/geant4/assets/element_sim/` (CMake project linking Geant4 and `g4sim`).

**Spec `element_sim.spec/1`** (schema in the same directory, using only keywords supported by `contracts/schema.py`):

| Block | Content |
|---|---|
| Coordinates | Origin at the world centre, mm; elements given by centre and half-lengths (boxes). **All centres are world coordinates** (daughters included); `element_sim` converts them to mother coordinates when placing (e.g. the field-region mother's centre is at x = −100, so Si1's world centre x = −500 becomes −400 in the mother) |
| `materials` | NIST names or mixtures (component order kept; `g4sim`'s material helper) |
| `elements` | Box elements: name, material, centre, half-lengths, mother (the world or one element; only one level of nesting), role (`passive`, `tracker-plane`, `tof-layer`, `calorimeter` (the mother), `calorimeter-active`, `calorimeter-passive`), repetition (for calorimeter sampling layers) |
| `field` | Uniform magnetic field: element it is attached to, B vector, accuracy parameters (B1.2) |
| `physics` | Physics list and EM option, cuts, regions (same semantics as `layered_sim`, through `g4sim`) |
| `source` | `type: gun`: particle, energy (`energy_MeV` or `ekin_per_nucleon_MeV`), position, direction; `gps` and `event-file` only have their interface defined (architecture §9.2) and exit 2 when met |
| `run` | Number of events, threads, logical-run seed; `seeding` allows only `per-event` |
| `output.observables`, `output.blocks` | As in A2.3 (referencing `simulation-observables/1`) |
| `output.event_file` | `level`: `none` (default), `summary`, `crossings`, `hits`; `compression` (default 1); `max_events_hits` (default 100) |

- Cross-field rules (elements do not overlap, daughters inside their mother, unique names, role compatible with material) are checked in the Python adapter (`check-spec` of B1.6); C++ checks only the minimum needed to run.
- Every run delivers the three boundary artifacts (summary, column map, effective config), the same as `layered_sim`.

### B1.2 Field

- Build `G4UniformMagField`, `G4FieldManager` and `G4ChordFinder` in `ConstructSDandField`, stored as `G4ThreadLocal`; the master and each worker have their own. Building them in `Construct()` would make workers share a non-thread-safe chord finder.
- Attach to the field-region mother with `SetFieldManager(fm, true)`, propagating to all daughters.
- With a field, add `G4StepLimiterPhysics`.
- Stepper and driver are **built explicitly**: a `G4DormandPrince745` on a `G4Mag_UsualEqRhs`, passed to `G4ChordFinder`; not the stepper chosen by `G4ChordFinder`'s default constructor (which `G4FieldParameters` does not control). The stepper class is written into the spec, and the probe records the actual stepper and driver class names via RTTI (a helix stepper would make the field-propagation check meaningless). Check the constructor signatures against the 11.4.3 source before implementing.
- Written from the API, without copying or adapting the B5 example's code (G5).

| Parameter | Nominal | Note |
|---|---|---|
| `delta_chord_mm` | 0.25 | Has no effect when the maximum step is below about 80 mm; recorded, not scanned |
| `delta_one_step_mm` | 0.01 | In a uniform field the Runge–Kutta truncation error is far below the intersection error; the scan is expected to show no effect; confirmed once |
| `delta_intersection_mm` | **1e-5** (0.01 µm) | Sets the accuracy of crossing points |
| `min_epsilon_step` | 5e-5 | |
| `max_epsilon_step` | 1e-3 | epsilon = delta one step / step length, clamped at this upper bound |
| `max_step_mm` | 10 | Needs `G4StepLimiterPhysics`; `G4UserLimits` must be set per volume and does not propagate to daughters |
| `stepper` | DormandPrince745 | Built explicitly (see above) |

- **Probe:** `SimProbe.hh` walks `G4LogicalVolumeStore`, reads back B, the chord finder and each accuracy parameter via `GetFieldManager()`; deduplicates by pointer, records the volume of the original attachment; notes that the master sees only the master's copy. A field attached to a volume inside the target counts in the `tree-v1` target hash.
- **MT test:** a UI command that exists only in the test build reports each thread's field-manager pointer; they must all differ.

### B1.3 Plane crossings and calorimeter leakage

- **Crossings:** when the primary (track ID 1) **first** enters a `tracker-plane` or `tof-layer` element (pre-step point status `fGeomBoundary` and its volume is that plane), record the pre-step point's position, direction, kinetic energy, global time and PDG code; one "recorded" flag per plane. If the source lies inside a plane there is no `fGeomBoundary`, and no row is written for that plane.
- **Calorimeter leakage:** for the mother element with role `calorimeter`, each event records the energy carried out of the mother by particles leaving it from inside (steps whose `post` point leaves that mother; a positron adds 2 mₑc²; multiplied by the track weight), split by the face crossed into `leak_rear_MeV` (+x face), `leak_front_MeV` (−x face) and `leak_lateral_MeV` (y and z faces), with the same semantics as `layered_sim`'s columns of the same names (`layered_sim` uses the world boundary as the faces, `element_sim` the calorimeter mother). The three columns go into the CSV, the `events` ntuple and the column map, for shower-containment (`geant4_benchmarks.py` line 487) and the rear-leakage fraction of B3.3.
- The per-event CSV keeps only summary columns (primary truth, total deposit per subsystem, calorimeter leakage); crossings and per-layer deposits go into the ROOT file (B1.4).

### B1.4 Per-event ROOT files

| Item | Spec |
|---|---|
| Writing | Through `G4AnalysisManager` (ROOT output type); underneath is g4tools, bundled with Geant4, so no ROOT installation and no new build dependency |
| Files | One file per job; under MT, `SetNtupleMerging(true)` has the master merge into one file (in 11.4.3 only ROOT output supports ntuple merging); path written into the run record through `tilde()` |
| Structure | Flat ntuples with scalar columns only (I, D, S), each row keyed (`event_id` plus the ntuple's own secondary key); no vector columns |
| Row order | Not fixed after MT merging; readers always sort by key |
| When written | Rows filled in `EndOfEventAction`; the file written and closed at end of run. If the run is interrupted the file is incomplete and the run is incomplete (exit 3) |
| Version | Structure `element_sim.events/1`, `event_file_version` in the file |
| Hashes | File bytes include the write time and are not bit-identical; the run record keeps both the file sha256 (integrity) and the `content_sha256` from `simroot hash` (comparison and provenance). When a logical run has several job files, `content_sha256` is computed over the union of all files sorted by key (except the `run` ntuple, which differs per file), so it does not depend on the split |
| Size | Not committed; the run record keeps path, hashes, row counts and size per ntuple |

| ntuple | Level | One row per | Columns |
|---|---|---|---|
| `run` | from `summary` | file | sha256 of spec and column map, program version and source hash, Geant4 version, logical-run seed, event range, `event_file_version` |
| `processes` | from `summary` | process | `process_id`, `name` (the process-number table for `hits`) |
| `events` | from `summary` | event | `event_id`, primary PDG code, kinetic energy, origin, direction; total deposit per subsystem; `leak_rear_MeV`, `leak_front_MeV`, `leak_lateral_MeV`; energy leaving the world; flags |
| `deposits` | from `summary` | event × volume with a deposit | `event_id`, `volume_id`, `copy`, total deposit, deposit by charged particles |
| `crossings` | from `crossings` (also in `hits`) | event × crossed plane | `event_id`, `plane_id`, `track_id`, PDG code, pre-step position, direction, kinetic energy, global time |
| `hits` | `hits` only | step with a deposit | `event_id`, `track_id`, `step_index` (the track's step number; with `event_id` and `track_id` a unique key), `parent_id`, PDG code, `volume_id`, `copy`, pre- and post-step positions, time, deposit, step length, `process_id` |

- If the number of events with `hits` exceeds `max_events_hits`, spec validation rejects it as `rejected` (exit 2).
- Estimate (J15, `crossings` level): at most about 4 kB per event uncompressed (`crossings` 10 rows × 80 B, `deposits` up to 110 rows × 28 B, `events` about 120 B); at most about 400 MB uncompressed for 10⁵ events.

### B1.5 `simroot`

**Location:** `adapters/geant4/assets/simroot/` (same CMake project as `element_sim`; links only Geant4's analysis library, no run manager).

- **Gate G-B1a (the first day):** confirm that `G4RootAnalysisReader` can read MT-merged, compressed files and string columns; if it cannot, `simroot` reads only flat scalar columns, and the strings of `run` go into a JSON side file.

| Subcommand | Content |
|---|---|
| `info` | Row counts and columns per ntuple, content of the `run` row; JSON output |
| `dump` | After sorting by key, writes the chosen ntuple and columns as CSV (stdout or `--out`), floating point as `%.17g`; can read several files at once; `--events` selects a subset |
| `hash` | Content hash: each ntuple sorted by key, numbers normalized as hex floats, then sha256; outputs `content_sha256` |

- Exit codes per `core/status.py`. Researchers may analyse the ROOT files directly with ROOT or uproot, but neither is a dependency of the pipeline or of the required tests.

### B1.6 `check-spec` and interface consistency between the two backends

- **`geant4_run.py check-spec --spec <file>`:** validates `element_sim.spec/1` against the schema and cross-field rules (no Geant4 needed); outputs JSON `{ok, problems[]}`, exit code 0 or 2. Task C's `detector-design` calls it as a subprocess (adapters do not import each other).
- The three boundary artifacts from `element_sim` pass the same interface tests as `layered_sim`'s (schema, hashes, semantic names in the column map).
- **Statistical agreement compares only observables both backends produce.** J14's `stopping-power` and `thin-layer-mpv` need `primary_eloss_MeV`, `primary_fate` and `primary_end_process` (`geant4_benchmarks.py` lines 233, 284, 325, 365), which `element_sim` does not produce, so J14's benchmark decisions are not compared.
- Method: a slab identical to J14's nominal (`Si_study` declared as a mixture with the same composition and density, same physics settings and cuts), one logical run on each backend (`layered_sim` with `stream`, `element_sim` with `per-event`; the events differ); compare the mean and mode (A1.7) of the silicon deposit `edep_Si_MeV`, and the `leak_rear_MeV` fraction of a calorimeter-like configuration. Each observable's difference within 3·se_diff.

### B1.7 Deterministic field check (`field-propagation`)

No statistics needed; only `element_sim`.

- Tracks: charged geantinos (mass 0, β = 1) at rigidities 0.6, 1, 10, 100, 1000 GV.
- Directions: normal incidence; 50 mrad in the bending plane **opposite to the bending direction** (+y for positive charge); ±50 mrad in the non-bending plane.
- Appendix A checks that with these directions every track reaches every Si plane and both TOF2 layers and does not leave the field-region mother. With the bending direction instead, 0.6 GV and 1 GV miss Si6.
- Reference: the analytic helix; after the track leaves the field region, piecewise straight lines; only planes the analytic track actually reaches are compared.

| Scan | Grid | Decision |
|---|---|---|
| delta intersection | 1e-3, 1e-4, 1e-5, 1e-6 mm | At nominal (1e-5), the in-plane distance √(Δy² + Δz²) ≤ 0.5 µm (ε/20) on all planes, the analytic track evaluated at the plane's x; the two finest differ by ≤ 0.2 µm; \|x − x_plane\| of Geant4's crossing point is also recorded. The result of every grid point is reported; 1e-3 mm is not assumed to fail (Geant4's intersection error is mainly along x, and in the plane it becomes only about slope × δ ≤ 0.25 µm) |
| Maximum step | 100, 30, 10, 3 mm | Same |
| delta one step and epsilon | nominal and 1/10 | Expected no change; confirmed once |
| TOF2 path time (both layers) | — | \|Δt\| ≤ 1 ps (about 0.3 mm of path), checks path length only |

- Negative control: B × (1 ± δ) on the Geant4 side, δ chosen by a trial run so that the deviation exceeds the criterion.
- The result is recorded as the `field-propagation` benchmark (verification, added to the table in B2.4); in B1 it is first recorded by tests and the VALIDATION entry.

### B1.8 Adapter-change process

| Item | Content |
|---|---|
| Version | 0.2.0 → 0.3.0 |
| `adapter.json` | `assets` gains `element_sim/`, `simroot/`, the `element_sim.spec/1` schema; update `purpose` |
| `SIM_SOURCES` | Today a flat tuple of file names, hashed only under `ASSETS/"layered_sim"` (`geant4_run.py` lines 63, 327). Change it to a table grouped by program, `{"layered_sim": [...], "element_sim": [...], "simroot": [...], "g4sim": [...]}`; each run record records the program used and the hashes of the `g4sim` files; field code in `element_sim/Field.hh`, `Field.cc`; `layered_sim`'s hash keys are unchanged, so old records still compare |
| G5 | Statement "written from the Geant4 API; no example code (B5 included) copied or adapted", confirmed by the reviewer in the VALIDATION entry; the same entry notes the ROOT file type and `simroot` |
| Tests | Offline tests (spec validation, cross-field rules, `check-spec`); live tests (`HEP_GEANT4_LIVE_TEST=1`): geometry, field, event files, `simroot` round trip |
| Docs | The Geant4 row of `docs/capability-matrix.md`; adapter docs |

### B1.9 B1 acceptance

- [ ] `element_sim`'s J15 geometry passes overlap, material-budget and per-event energy-balance checks; the check values of §4.1 and §4.2 are recomputed by tests.
- [ ] `check-spec` returns exit 2 with the reason for every kind of cross-field error, and exit 0 for a valid spec.
- [ ] Interface consistency of B1.6 and statistical agreement of the two backends (gate G-B1b).
- [ ] Under `per-event`, the same logical run with 1, 2, 4 jobs and 1, 2, 4 threads: summary integers identical, floating-point relative difference ≤ 1e-12.
- [ ] The field-manager pointers reported by the MT test command differ between threads; the field parameters recorded by the probe agree with the spec; the field counts in the target hash.
- [ ] The deterministic field check of B1.7 passes at nominal values, the result of every grid point is reported, and the negative control is caught (gate G-B1b).
- [ ] Calorimeter leakage: in a simple configuration (electrons on a thin calorimeter), `leak_*_MeV` plus deposits and energy leaving the world satisfy per-event energy balance.
- [ ] `simroot` round trip: values of I, D, S columns identical at each level; `content_sha256` identical between serial and different thread counts; `deposits` summed per event equals the subsystem totals in the CSV; `hits` above the cap gives exit 2; an interrupted run is incomplete.
- [ ] VALIDATION GEANT4-ELEMENT; CHANGELOG; release manifest.

---

## 6. Stage B2: reconstruction and contracts (geant4 adapter 0.4.0, contracts CV2)

### B2.1 `simreco` (digitization and reconstruction)

**Location:** `adapters/geant4/assets/simreco/` (CMake project; uses only the C++17 standard library and the Geant4-free `SimHash.hh`, `SimSummary.hh` and `MiniJson.hh` of `g4sim`; not linked to Geant4). Parameters (ε, σ_t, nominal B, calibration sample) are in a reco spec owned by hep-detector.

**Input:** `crossings` and `deposits` taken from the ROOT file by `simroot dump` (sorted by key, passed through a pipe, not stored), and the summary CSV.

| Step | Content |
|---|---|
| Silicon | Gaussian smearing of crossing points: bending direction (y) ε = 10 µm, non-bending direction (z) 30 µm; the fit uses the same x as the scorer (entry face) |
| TOF | Independent Gaussian smearing σ_t of each layer's time (100 ps; 150 ps separately for sensitivity); station time = mean of the two layers' times (after converting both to the station centre with the fitted track); also outputs each layer's dE/dx and the time difference of a station's two layers |
| Track | Circle fit in the x–y plane with multiple-scattering covariance (without it, χ²/dof is in the thousands at 1 GV), giving the curvature κ; straight-line fit in the x–z plane, giving the dip angle λ; R_reco = C·B/(κ cos λ) with the nominal B (total momentum, C = 0.2998 GV/(T·m)); outputs R, χ², degrees of freedom |
| True rigidity | 1/R_true = mean of \|q\|/p_i from the crossing records of the six planes (**total momentum** p_i; for unit charge 1/R = 1/p); R_true and R_reco both use total momentum, avoiding the p vs p_T difference (about 0.125 % at 50 mrad, more than the 0.05 % tolerance of the muon field check) |
| β | Path length with the two station centres as end points, including the straight segments TOF1→Si1 and Si6→TOF2 and the 3D inclination; at low β reports the change in β between the stations |
| Calorimeter | Total deposit in active layers divided by the **electron** sampling fraction; the sampling fraction is obtained from a 10 GeV electron sample of role `calibration`; also outputs e/mip |
| Random numbers | Each event's digitization random stream comes from the SplitMix64 of `SimHash.hh`, seeded with H(S, i, "digi") (H of A1.4; S the logical-run seed, i the event number); normal deviates from the Box–Muller of `SimHash.hh`; not `std::normal_distribution` (libstdc++ and libc++ give different output). Separate from Geant4's random stream, identical across platforms |

**Output:** a per-event result CSV (R, χ², β, calorimeter energy, etc.) and a run summary (`simulation-summary/1`, producer `simreco`; block accumulators of observables such as (1/R_reco − 1/R_true)·R_true and β − β_true).

- **Fitter unit tests:** `tracker_resolution.py` does not fit; it only computes the curvature resolution from a parabola least-squares fit (`curvature_sigma`, line 89). The test therefore compares, on toys without multiple scattering (R ≥ 300 GV), the σ(1/R) and pull width of the C++ fit with the measurement-term resolution from `tracker_resolution.py momentum` (`mdr_intrinsic_gev`), within the toys' MC error; pull width within 1 ± 3σ_MC.

### B2.2 `geant4_run.py reco` and `table`

- `reco`: runs `simroot dump` and `simreco`; each execution writes one computational-run record (with `**trace.provenance()`, `simreco`'s program hash, the hashes of the input run records and the ROOT file's `content_sha256`, and the list of dumped ntuples and columns). Changing digitization parameters does not require rerunning the simulation.
- `table`: writes reconstructed results (e.g. rigidity resolution vs rigidity) as a simulated dataset-record (with `trace.provenance()`).
- Exit codes per `core/status.py`: 0 ok, 1 negative verdict, 2 `rejected` (unreadable input, including missing files), 3 incomplete.
- **CLI registration:** `MISSING_FILE_ARGS` in `tests/skills/test_cli_robustness.py` maps each script to a single argv list today, and `geant4_run.py`'s entry is taken by `run` (line 130). Extend it so that a script may map to one or more argv lists, then add `check-spec`, `reco` and `table`.

### B2.3 Result tables and transitive processing chains

- **Transitive processing chain:** today `dependencies.py` requires every input of a simulated table to be a computational-run with `extension.simulation` or `extension.study`; reconstruction records have neither. CV2 changes this: the input chain may be arbitrarily deep, as long as every level is a recorded computational-run and every root of the chain is a simulation run (needs hep-computing's agreement; plan §7 item 8).
- When the study is `unvalidated`, the table stays `unvalidated`; a communication using it gets the `communication.simulated_source` warning, and figures are marked "Simulation".

### B2.4 Validation classes, table entries and `change`

**New benchmark table entries** (A1.1 format; grade is class; `GRADES` and the study spec's benchmark and grade enums gain them as well; the functions go in `geant4_benchmarks.py` and read only summaries or `simroot dump`):

| benchmark | Class | Supported kind | Scope dimensions | Computed in |
|---|---|---|---|---|
| `field-propagation` | verification | — | — | `field_propagation()`, reading `crossings` from `simroot dump` and the analytic helix (B1.7) |
| `field-propagation-muon` | sanity | — | — | `field_propagation_muon()`, reading `simreco`'s summary |
| `tof-beta` | verification | — | — | `tof_beta()`, reading `simreco`'s summary |
| `tof-layer-consistency` | verification | — | — | `tof_layer_consistency()`, reading `simreco`'s summary |
| `sampling-fraction` | sanity | — | — | `sampling_fraction()`, reading `element_sim`'s summary |
| `regression-comparison` | regression | — | — | `regression_comparison()`, reading the summaries of two versions |
| `surrogate-comparison` | surrogate | — | — | `surrogate_comparison()`, reading the summaries of the surrogate and the reference simulation |

- **verification:** does not count for upgrade.
- **regression:** the role enum gains `regression`. The same study with the same settings runs once at each of two versions (plugin, backend or Geant4); the point_id of each is the version tag, so S differs and the samples are independent (no clash with A1.4's uniqueness). Only scalar observables are compared (histogram comparison belongs to the distribution-level benchmarks deferred in §9). The decision is made by the decision engine's new `change(diff, se, ν, tol, m)`: `changed` = |diff| − t_{1−α/m}·se_diff > tol; `unchanged` = pass of `equivalence`; otherwise `unresolved`. Tolerance and α are declared in advance. The record does not affect the label; a reference observable marked `changed` may trigger a sci-fix check.
- **surrogate:** a surrogate model **never changes the physics label**. A surrogate study declares its reference study (a study record, not a run record; run records carry no upgrade) and scope; decided by `equivalence` (χ² only as a diagnostic). On pass it records `extension.study.surrogate = {reference_study_ref, reference_sha256, scope}`, the scope being the intersection of the declared scope and the reference study's scope. Task C's F0 and F1 evaluations architecturally belong to this class.
- Gating: `strict or _at_least(contract_version, CV2)`, no warning branch.

### B2.5 Adapter-change process and CI

| Item | Content |
|---|---|
| Version | 0.3.0 → 0.4.0 |
| `adapter.json` | `assets` gains `simreco/` and the reco-spec schema; update `purpose` |
| `SIM_SOURCES` | Add a `simreco` group |
| CI | A C++17 CI job builds and tests `simreco` (required or optional is the maintainer's decision, plan §7 item 9) |
| Docs | Adapter docs, `geant4-study-protocol.md` (validation classes, processing chains, `reco` and `table`) |

### B2.6 B2 acceptance

- [ ] `simreco`'s fitter unit tests pass per B2.1; `simreco` is built and tested in a CI job (a required job; or, if the maintainer decides it is optional, an optional job plus a local build-and-test record).
- [ ] `simreco`'s digitization output is bit-identical on Linux (libstdc++) and macOS (libc++).
- [ ] `simreco`'s summary passes the same consistency test as A2.9 (Python recomputes from the per-event result CSV).
- [ ] `check-spec`, `reco` and `table` are registered in the extended `MISSING_FILE_ARGS` and pass the missing-file tests.
- [ ] A processing chain of three or more levels (simulation → reconstruction → table) is accepted by `dependencies.py`; it is rejected when a root is not a simulation run.
- [ ] The new table entries agree with `GRADES` and the study spec's enums (consistency test); the verification class does not count for upgrade.
- [ ] Toys of `change`: probability of changed when the true difference is 0 ≤ α/m + 3σ_MC; a regression check (e.g. J14 on two plugin versions) produces a `changed`, `unchanged` or `unresolved` record without affecting the label.
- [ ] Contract tests of surrogate: a record carrying `extension.study.surrogate` that declares `validated-in-scope` is rejected; a reference that is not a study record is rejected.
- [ ] J14 still passes under `--strict`.
- [ ] VALIDATION GEANT4-RECO; CHANGELOG; release manifest.

---

## 7. Stage B3: J15 study

### B3.1 J15's study spec

- Declares: observables (rigidity resolution, β resolution, sampling fraction, total deposit, rear leakage fraction; referencing `simulation-observables/1`), K and B, benchmarks, convergence plan, variations, stopping rule.
- All results `unvalidated`; the README and the study record state its role as a "verification carrier".

### B3.2 Validation ladder

| Check | Class | Reference | Spec | Negative control |
|---|---|---|---|---|
| overlap | implementation | — | — | Shift one Si plane to create an overlap |
| Per-event energy balance (J15 geometry) | implementation | Energy conservation | — | Omit 2 mₑc², double counting |
| Material budget (geantino) | implementation | PDG X₀ sum | Tolerance about 2 % (Geant4's X₀ formula differs from PDG by about 1 %) | Pb density ± δ |
| `field-propagation` | **verification** | Charged geantino against the analytic helix | B1.7 | B × (1 ± δ) on the Geant4 side |
| `field-propagation-muon` | **sanity** | Plane-averaged true 1/R (B2.1) | μ⁻ 1, 10, 100 GV; observable: mean of (1/R_reco − 1/R_true)·R_true; tolerance = t_{K−1}·SE + 0.05 %; relative SE target 0.1 %, N from the trial run per A1.9 (estimates: about 400 at 1 GV, about 7400 at 100 GV, for SE of about 0.07 % and 0.10 %) | B × (1 ± 1 %) on the Geant4 side |
| Fitter unit test | test (not a benchmark) | B2.1 | — | — |
| One-off multiple-scattering comparison | sanity | The analytic term of `multiple_scattering.py` (no log); optionally `toy_spectrometer.py` (needs NumPy) | μ and p, 1–10 GV, with β | — |
| `tof-beta` | **verification** (bookkeeping) | Kinematics along the true trajectory | — | Scorer test flag injects a time offset; there is no physics control on the Geant4 side, noted in the docs |
| `tof-layer-consistency` | **verification** (bookkeeping) | Time difference between a station's two layers against "inter-layer path length / βc" (66.7 ps at β = 1, normal incidence) | Mean residual 0; width √2 σ_t (141 ps at 100 ps) | Test flag injects an offset into one layer's scorer time |
| `sampling-fraction` | sanity | Ratio of ionization dE/dx at the run momentum from the PDG muon energy-loss tables (Groom et al., obtained via hep-citations) | μ⁻ 1 GeV; statistic Σ PVT deposit / Σ (PVT + Pb) deposit; plausible range ±10 % (the reviewer's Bethe estimate is about 0.271); different seed from the `calibration` sample | PVT density ± δ |
| Shower containment | sanity | PDG gamma profile, effective critical energy of the mixture about 10.2 MeV | Electrons 1–100 GeV; `leak_*_MeV` (B1.3) | — |
| `longitudinal-profile` (0.21.0) | not applicable | Its reference is the published ALICE FoCal-E measurement, valid only for that stack; J15's calorimeter differs, and is embedded | — | — |
| Optional: stopping power in an isolated PVT slab | reference (`configuration: isolated`) | Bethe (RPP 2024 eq. 34.5) | p, T = 200–600 MeV (βγ ≈ 0.69–1.30, below PVT's 10^x₀ ≈ 1.40, so the density correction is 0), 1 cm slab, nuclear interactions excluded (about 1 %); Sternheimer parameters from Sternheimer, Berger & Seltzer (1984), checked via hep-citations | PVT density ± δ |

The optional last item runs in an isolated slab (a single element of `element_sim`), not as part of the J15 detector, to show the upgrade path for a new material. Event counts and decisions follow A1.6–A1.10.

### B3.3 Calorimeter production-cut convergence

- Grid: 0.1, 0.3, 0.7, 1.0 mm.
- Sample: 10 GeV e⁻; trial first, then N per A1.9.
- Observables: total deposit (relative tolerance 1 %, about 400 showers per point), rear leakage fraction (`leak_rear_MeV` divided by the incident kinetic energy, back face of the calorimeter mother only; **absolute** tolerance 0.002, `tolerance_mode: absolute`, about 5000 showers per point).
- Events per point: the larger of the two; decision per A1.8 (`equivalence`).
- The Si production cut is not converged in J15: it affects only the Si deposit, and J15's Si results are not used as evidence. The study spec's `convergence_plan.observables` gains total deposit and rear leakage fraction. The parameter sets each benchmark depends on are declared in advance and checked against the probe's actual settings.

### B3.4 Variations

| Variation | Scope | Rule |
|---|---|---|
| EM option4 vs option3 | Calorimeter profile, sampling fraction | `G4R-PRECISION-EM` |
| FTFP_BERT_EMZ vs **QGSP_BIC_EMZ** | Nucleons below 1.5 GeV; final-state observables: deposit in the 5 layers after the first interaction, energy of charged secondaries after the interaction. Interaction probability and first-interaction depth are reported only when the probe confirms the two inelastic cross sections differ (the two physics lists may share nucleon cross sections, and then the difference is 0 by construction, the false zero warned about at protocol line 161) | `G4R-BIC-RANGE`; below 3 GeV for π and at 6–12 GeV for hadrons both use the same model and must not be used as a variation |
| Vacuum vs air | Multiple scattering, rigidity resolution | — |

### B3.5 TOF time-resolution sensitivity

- `simreco` reconstructs once with σ_t = 100 ps and once with 150 ps (same simulation, no rerun).
- Report σβ/β for both (expected about 2.3 % and 3.5 %) and the effect of β resolution vs rigidity; the README says that 100 ps is more optimistic than AMS-02's system resolution (about 140 ps).

### B3.6 Recorded-data budget

- `check_packaging.py` caps each file at 2 MiB; J14's `recorded/` is 2.6 MB (for reference).
- ROOT files are not committed; run records keep only the path, file sha256, `content_sha256`, row counts and size per ntuple; ROOT files needed by tests are produced in live tests.
- J15 commits only: run summaries (simulation and reconstruction), effective configs (stored by content hash), column maps, summary CSVs with reduced columns (benchmark runs), reduced crossing and deposit records extracted with `simroot dump --events` (for offline replay tests of `simreco`; the event subset set by the budget), reconstructed result tables.
- Each file ≤ 2 MiB, J15's `recorded/` total ≤ 3 MB.

### B3.7 Registration, journey and docs

| Item | Content |
|---|---|
| Script count | No new scripts in hep-detector; `DetectorScriptCount` stays 21, line 47 of `docs/capability-matrix.md` unchanged |
| Routing table | `skills/hep-detector/SKILL.md` not changed; descriptions of J15, `element_sim` and `simreco` go into `geant4-study-protocol.md` and the adapter docs |
| Journey | J15; `docs/researcher-journeys.md`, the examples table of `docs/maintenance.md`; `tests/examples/test_geant4_minimal_spectrometer.py` (replay and compare decisions) |
| Capability | `docs/capability-map` (new entry under `full-detector-simulation`, run `capability_map.py --write`), `docs/capability-matrix.md` |
| Routing | New routing case for J15; `check_routing_static.py` reads the journey list from `docs/researcher-journeys.md`, so once J15 is in the table it **must** have a routing case. Rerun the live Geant4 cases, including the existing Traditional Chinese underspecified case `g4-underspec-2` |
| Description length | Description 1,016 / 1,024 characters; routing cases reuse existing trigger words, the description is not changed |
| README | J15's list of simplifications (§4.1), comparison with PAMELA and AMS-02 (§4.3), its role as a "synthetic geometry, verification carrier" |
| Independent review | This task's Markdown (protocol changes, J15 README, this document) is reviewed with 0.22.0's `review.py`; its record is advisory only and, per O04/O14, does not replace the human G5 confirmation |
| Other | `reference_inventory.py --check`, CHANGELOG, release manifest |

### B3.8 B3 acceptance

- [ ] `field-propagation-muon`, `tof-beta`, `tof-layer-consistency`, `sampling-fraction` and shower containment are complete; each negative control is caught per B3.2, or the absence of a control is noted.
- [ ] Calorimeter cut convergence (B3.3) and variations (B3.4) are complete, with decisions and the incomplete rate recorded in the study record.
- [ ] The TOF σ_t sensitivity at 100 and 150 ps is reported.
- [ ] Recorded budget, registration items and docs all done; J15's offline replay test passes.
- [ ] An independent agent, using only the docs and tools, completes "rigidity resolution of a 1 GV proton in J15": the result record passes `validate.py --strict`, the label is `unvalidated`, the resolution (central 68 % half-width of the distribution of (1/R_reco − 1/R_true)·R_true) lies within the range of the 1 GV proton row of the §4.2 multiple-scattering table (1.8–2.6 %; the measurement term is negligible at 1 GV), and no maintainer help is needed.
- [ ] VALIDATION GEANT4-J15; CHANGELOG; release manifest.

---

## 8. Contracts and versions

| Object | Location | Version |
|---|---|---|
| `element_sim`, `element_sim.spec/1`, `element_sim.events/1`, `simroot`, `check-spec` | geant4 adapter | 0.3.0 (B1) |
| `simreco`, reco spec, `reco`, `table` | geant4 adapter (C++, not linked to Geant4) | 0.4.0 (B2) |
| verification, regression, surrogate classes and table entries; regression role; transitive processing chains | `contracts/validate.py`, `contracts/dependencies.py` | CV2 (minor, gated) |
| Decision engine `change` | `core/stats/decisions.py` | with the plugin version |
| `GRADES` and the study spec's enums; total deposit and rear leakage fraction in `convergence_plan.observables` | hep-detector | with the plugin version |

---

## 9. Not done and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| σ(1/R) in the measurement-dominated region as a benchmark | Not done | Replaced by the fitter unit test |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | Not done | Replaced by `simreco` in C++ |
| New geometry features in `layered_sim` | Not done | New features only in `element_sim` |
| Reading ROOT directly from Python (uproot) in the pipeline | Not done | Through `simroot` |
| Ion sources and Birks visible energy (J17) | Deferred | Cosmic-ray nuclide studies, and a documented Birks constant for PVT. Implementation per 11.4.3: get the ion with `GetIon(Z, A)` in `GeneratePrimaries`; set kB in `Construct` (`GetIonisation()->SetBirksConstant`), call `G4EmParameters::Instance()->SetBirks(true)` at PreInit, then get it via `G4LossTableManager::Instance()->EmSaturation()` (check the API names against the 11.4.3 source when implementing) |
| Non-box solids, rotations, GDML input, field maps, fringe fields in `element_sim` | Deferred | The first study that needs them and cannot use a user application (also the trigger for task C's cylindrical geometry) |
| Primary exit records in `element_sim` (J14's observables) | Deferred | When J14 is migrated to `element_sim` and `layered_sim` retired (plan §8) |
| Distribution-level benchmarks (including histogram comparison for regression), combination of observables, profiles, `gps` and `event-file` sources, `simreduce` | Deferred (interfaces defined in architecture §9.2) | Each one's first use case |
| RNTuple, vector columns | Deferred | ROOT file size or read speed becomes a bottleneck |

For other items not done or deferred, see task A §9.

---

## 10. Open decisions and residual risks

**Open decisions** (numbers from plan §7): item 7 (how to confirm G5), item 8 (transitive processing chains and the classification of CV2), item 9 (the CI job for `simreco`), item 10 (where ROOT files are stored), item 11 (maintenance ownership of `element_sim`).

**Residual risks:**
1. The sampling-fraction reference needs the PDG muon energy-loss tables; the optional PVT benchmark needs Sternheimer parameters. Both need literature records via hep-citations before use.
2. Calorimeter showers dominate CPU time; convergence of rear leakage needs about 5000 showers per point; event counts are set by trial runs and recorded.
3. The read capability of `G4RootAnalysisReader` is unverified (gate G-B1a).
4. ROOT files of large samples can reach hundreds of MB; under MT merging, worker baskets stay in memory until end of run; `hits` has an event cap; size and memory confirmed in trial runs.
5. Maintenance cost of two Geant4 programs; duplication controlled through `g4sim` (plan §8).
6. Hadronic variation: if the two physics lists share nucleon inelastic cross sections, the interaction probability does not change; only final-state observables are reported (B3.4).
7. Some Geant4 behaviour (stepper construction, the Birks API, the direction of the intersection error) rests on the reviewer's experience and was not checked line by line against the 11.4.3 source; check it first when implementing.
8. Effort is estimated at the start of B1 based on the actual `g4sim`.
9. Task A's residual risks (the block-independence assumption, near-threshold decisions, the probe assuming worker and master settings are the same) also apply; see task A §10.

---

## 11. Suggested order of work

**B1**
1. Pre-start checks (§0); the one-day `G4RootAnalysisReader` trial (gate G-B1a).
2. `element_sim`'s spec, schema, `check-spec` and geometry (B1.1, B1.6); two-backend consistency with a slab configuration identical to J14.
3. Field (B1.2) and MT test; deterministic field check (B1.7).
4. Build the J15 geometry (§4.1); pass overlap, material budget, energy balance; recompute the check values of §4.1 and §4.2 in tests.
5. Plane crossings and calorimeter leakage (B1.3), ROOT files (B1.4), `simroot` (B1.5).
6. Adapter-change items of B1.8; tick all of B1.9; run the checks of task A §8.

**B2**
1. `simreco`'s fitter unit tests first, then the `simroot dump` input (B2.1); CI job.
2. `reco` and `table`, extension of `MISSING_FILE_ARGS` (B2.2); transitive processing chains (B2.3).
3. Validation classes, table entries, `change`, regression role and contract tests (B2.4).
4. Adapter-change items of B2.5; tick all of B2.6; run the checks of task A §8.

**B3**
1. J15's study spec (B3.1); run the validation ladder in E2 (B3.2).
2. Calorimeter cut convergence, variations, TOF sensitivity (B3.3–B3.5).
3. Recorded data, registration, journey, docs, the independent-agent acceptance problem (B3.6–B3.7); tick all of B3.8; run the checks of task A §8.

---

## Appendix A: Numbers

Computed by `j15_design_estimates.py` (this folder; standard library only, scipy optional; A_N checked against the closed form by exact rational least squares).

**Geometry**
- Si centres: −500, −340, −180, −20, 140, 300 mm; L = 0.800 m.
- Field region: −520 … 320 mm; margins 19.85 mm at each end.
- TOF1 layers −810 … −800, −790 … −780; TOF2 layers 490 … 500, 510 … 520; station-centre distance D = 1.300 m; world ±1200 mm.

**Tracking**
- A_N = 720 (N−1)³ / [(N−2) N (N+1)(N+2)]: A₄ = 81.0, A₆ = 66.96, A₈ = 57.17 (N equally spaced points including both ends, equal weights).
- MDR (measurement term only) = C B L² / (ε √A_N): 1172 GV for C = 0.2998 (1173 GV for C = 0.3).
- Multiple-scattering term (β = 1, with log): 1.34 %, bracketed with a factor of 1.0–1.4.

| B (T) | N | MDR (GV) | Multiple-scattering term (β = 1) | Rigidity where the two terms are equal |
|---|---|---|---|---|
| 0.15 | 6 | 352 | 4.5–6.2 % | 16–22 GV |
| **0.5** | **6** | **1172** | **1.3–1.9 %** | **16–22 GV** |
| 1.0 | 6 | 2345 | 0.7–0.9 % | 16–22 GV |
| 0.5 | 4 | 1066 | 1.1–1.5 % | 11–16 GV |
| 0.5 | 8 | 1269 | 1.6–2.2 % | 20–28 GV |

**Field-check grid** (50 mrad, opposite to the bending direction, positive charge):

| Rigidity | Max \|y\| in field | y at Si1 … Si6 (mm) | y at the two TOF2 layers |
|---|---|---|---|
| 0.6 GV | 29.0 | 25.0, 29.0, 26.6, 17.8, 2.5, −19.3 | −50.0, −53.2 |
| 1 GV | 32.4 | 25.0, 30.6, 32.4, 30.3, 24.4, 14.6 | 0.2, −1.4 |
| 10 GV | 60.7 | 25.0 … 60.0 | 67.1, 67.9 |
| 1000 GV | 66.0 | 25.0 … 65.0 | 74.5, 75.5 |

If the direction is the same as the bending (−50 mrad): y at Si6 is −151 mm for 0.6 GV and −116 mm for 1 GV, both missing Si6.

**TOF**: σ_station = σ_layer/√2, σβ/β = σ_layer c / D; 80, 100, 150 ps per layer give 1.8 %, 2.3 %, 3.5 % (with one layer per station 2.6 %, 3.3 %, 4.9 %). Time of flight at β = 1 between a station's two layers 66.7 ps; resolution of the two layers' time difference √2 σ_layer (141 ps at 100 ps).

**Calorimeter**: 18.41 X₀, 0.886 λ_I, 35 cm; effective Molière radius 3.95 cm; the mip energy-loss ratio 0.284 is only a ratio of dE/dx_min, **not** a reference value.

**Material before the calorimeter**: 11.32 % X₀ (four TOF layers 9.40 %, 83 %; Si 1.92 %), 5.46 % λ_I; TOF1, before the tracker, is 4.70 % X₀ of it.

**Event counts** (difference se ≤ tol/4): 10 GeV electron total deposit (tolerance 1 %) about 392; rear leakage (absolute tolerance 0.002) about 5000.

## Appendix B: Sources

- PDG Atomic and Nuclear Properties (retrieved 2026-10-21): [Silicon](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/silicon_Si.html), [Lead](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/lead_Pb.html), [Polyvinyltoluene](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/polyvinyltoluene.html)
- PDG Review of Particle Physics 2024, chapter 34: eqs. 34.5, 34.12, 34.16, 34.34–34.36 (equation numbers per the plugin's VALIDATION GEANT4-STUDY)
- Geant4 v11.4.3 sources relevant to fields and event files: `G4FieldManager.hh`, `G4ChordFinder.hh`, `G4PropagatorInField.cc`, `G4FieldParameters`, `G4LogicalVolume`, `G4ChargedGeantino.cc`, `G4VAnalysisManager.hh`, `G4EmSaturation`, `G4LossTableManager`, `G4IonTable`, `G4NistMaterialBuilder.cc`
- Geant4 Book for Application Developers, [Basic Examples](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html) (B4, B5)
- Sources for PAMELA and AMS-02 are in architecture §14
- To obtain: PDG muon energy-loss tables (Groom, Mokhov & Striganov); Sternheimer, Berger & Seltzer (1984), *Atomic Data and Nuclear Data Tables* 30, 261

## Appendix C: Version history

| Version | Content |
|---|---|
| Detector document and v5 | Single-axis stacked spectrometer; Gluckstern small-N formula corrected; field direction and field-check grid |
| 2026-10-22 | TOF1 and TOF2 with two layers each; digitization and reconstruction moved to C++; per-event ROOT files; split out as task B; rewritten for the new architecture (`element_sim` replacing spec/2; B1, B2; PAMELA and AMS-02 comparison and TOF sensitivity) |
| 2026-10-23 | Fixes after independent review (B1.6 compares only shared observables, calorimeter leakage, table entries, surrogate and regression rules, total-momentum rigidity, CLI and `SIM_SOURCES`, portable random numbers, explicit stepper construction, etc.) |
| **2026-10-23 (this version)** | **Reorganized per the plan (`plan.md`): B2 split into B2 (reconstruction and contracts) and B3 (J15 study), so that task C's C2 waits only for B2; deterministic field check moved to B1.7; new `geant4_run.py check-spec` (B1.6, for task C to use as a subprocess); the decision engine's `change` and the regression role added in B2; contract version written CV2; section numbering aligned with tasks A and C** |
