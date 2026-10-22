# Task B: `element_sim`, event files and the J15 minimal spectrometer

> Document type: implementation spec (for the implementing agent and reviewers). Status: awaiting the maintainer's approval
> Basis: [`architecture.en.md`](architecture.en.md) (design rationale and reference experiments). This document is the executable spec; where the two disagree, this document wins and the disagreement is reported
> Order: **starts only after A1 and A2 of task A ([`task-a-core.en.md`](task-a-core.en.md)) are both merged**
> Baseline: at writing, the same as task A (hep-research `main` at `9f08796`, contracts 3.5.0, Geant4 11.4.3); must be rechecked before starting (§0)
> Date: 2026-10-22
> Language: English translation of the Traditional Chinese original [`task-b-j15.md`](task-b-j15.md), with the same content. If they disagree, the Chinese wins and the English is corrected at the same time
> Nature of the example: J15 is a **synthetic geometry**, a carrier for verification, not any experiment's detector; the closest real instruments are PAMELA and AMS-02 (§4.3)

---

## 0. Task card

**Goal.** Add a general box-element Geant4 program `element_sim` as a second backend, with fields, plane crossings and per-event ROOT files; then use it and the reconstruction program `simreco` to complete the J15 minimal-spectrometer study, and add three validation classes (verification, regression, surrogate) and transitive processing chains to the contracts (C2).

**Two stages (in order, each merged separately):**

| Stage | Content | Version |
|---|---|---|
| **B1** `element_sim` and event files | `element_sim` (box elements, one level of nesting, field, plane crossings); per-event ROOT files; `simroot`; interface consistency between the two backends | adapter **0.3.0** |
| **B2** Reconstruction, J15 and C2 | `simreco`; the J15 study (validation ladder, convergence, variations, TOF sensitivity); C2 (verification, regression, surrogate, transitive processing chains); J15 journey | adapter **0.4.0**, contracts **C2** (minor) |

**Out of scope:** any change to task A's interfaces (if needed, handle it first as an adapter patch release within task A); new geometry features in `layered_sim` (it is frozen in maintenance mode); ion sources and Birks (future J16); real geometries and field maps (§8).

**Deliverables:** `element_sim`, `simroot`, `simreco` and their tests; `geant4_run.py reco` and `table`; the J15 example (a new folder under `examples/`, README, recorded data); C2 contract changes; J15 journey and routing case; VALIDATION entries GEANT4-ELEMENT (B1) and GEANT4-J15 (B2); CHANGELOG; release manifest.

**Definition of done:** every box in the acceptance lists B1.8 and B2.11 is ticked; every check in task A §9 passes.

**Main decisions:**
1. **A new backend, not a change to `layered_sim`.** `element_sim` leaves J14's program untouched and validates the output-side interface with a real second backend (architecture §3.2).
2. **Field accuracy by deterministic checks.** Charged geantinos against an analytic helix, no statistics needed (B2.5).
3. **J15 is a verification carrier.** Every result in the full detector is `unvalidated`; only an optional benchmark run in an isolated slab shows the upgrade path for a new material (B2.4).
4. **No new scripts in hep-detector.** Reconstruction is in C++ in `simreco`, its interface in the adapter; quick load and description unchanged (B2.10).

**Before starting:**
1. Confirm that task A's A1 (C1) and A2 (adapter 0.2.0) are both merged, and that the interfaces listed in §2 exist.
2. Using the method of task A appendix B, recheck the facts this document quotes against the `main` of that time (quick load, description length, journey list, `DetectorScriptCount`, contracts version), and update this document (both languages).
3. Read task A §1 (terms), §2 (hard rules) and §4 (design summary); this document does not repeat them.

---

## 1. Terms and notation

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
| Notation | "B1.3" is a work item of this document; "§4.2" a section of this document; "A1.6", "A2.4" work items of task A; "task A §2" a section of task A; "architecture §6" a section of `architecture.en.md` |

**Main files (relative to `plugins/hep-research/`):** `adapters/geant4/assets/g4common/` (created by task A, extended here); `adapters/geant4/assets/element_sim/` (new); `adapters/geant4/assets/simroot/` (new); `adapters/geant4/assets/simreco/` (new, not linked to Geant4); `adapters/geant4/assets/geant4_run.py` (new `reco`, `table`); `contracts/validate.py`, `contracts/dependencies.py` (C2); `skills/hep-detector/scripts/geant4_benchmarks.py` (`GRADES`); `skills/hep-detector/assets/geant4-study-spec.schema.json`; `skills/hep-detector/references/geant4-study-protocol.md`; `docs/researcher-journeys.md`, `docs/maintenance.md`, `docs/capability-matrix.md`, `docs/capability-map`; `tests/examples/test_geant4_minimal_spectrometer.py` (new).

---

## 2. Prerequisites: interfaces provided by task A

| Provided by task A | Use in task B |
|---|---|
| C1: benchmark table (class, grade, kind, scope dimensions), scope comparison, configuration and isolation (A1.1–A1.3) | J15's benchmarks are all embedded and do not count for upgrade; C2 adds verification, regression, surrogate to the table (B2.3) |
| Statistical spec: block batch means, exact intervals, MPV, IUT gate, two-stage event count, detection limit (A1.6–A1.10) | Decisions for J15's benchmarks, convergence scans and variations |
| Seeds S = H(study_id, role, point_id) and `seeding: per-event` (A1.4, A2.2) | `element_sim` supports only `per-event` |
| `g4common`: `SimSeed.hh`, `SimSummary.hh`, `SimProbe.hh`, material and physics-list helpers (A2.1) | Used directly by `element_sim` and `simreco` |
| The three boundary artifacts, and the study layer reading only them (A2.3–A2.6) | `element_sim` and `simreco` deliver the same three artifacts; the study layer needs no change |
| `tree-v1` target hash (A2.4) | A field attached to a volume inside the target counts in the hash |
| Schema keywords `maxItems`, `maximum`, `exclusiveMaximum` (A2.7) | Used by the `element_sim.spec/1` schema |

---

## 3. Hard rules

All of task A §2 applies. In addition:

1. Do not change `skills/hep-detector/SKILL.md` or hep-detector's description (quick load has only 931 bytes left; description 1,018 / 1,024 characters). J15's routing case must reuse trigger words already in the description.
2. No experiment names in `skills/` or `contracts/`; the contract table and the protocol refer to `longitudinal-profile`'s reference by citation key. Experiment names (PAMELA, AMS-02) may appear only in `docs/` and in J15's `examples/` README.
3. Field code is written from the Geant4 API, without copying or adapting the B5 example's code (G5).
4. The text of the shared stanza is not changed (point 5 says "3.1.0 upgrade rule"; changing it would touch every SKILL.md and rerun the live routing).
5. J15's `recorded/`: each file ≤ 2 MiB, total ≤ 3 MB; ROOT files are not committed (B2.9).
6. All J15 results are `unvalidated`; no J15 benchmark may count for upgrade.
7. No geometry features are added to `layered_sim`; new geometry features go only into `element_sim`.
8. Neither Python nor `simreco` parses ROOT directly; always through `simroot`.

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
| Calorimeter | 50 × (`G4_Pb` 2 + PVT 5) | 550 | 350 | 550 … 900 | 500 × 500 |

**TOF stations.** TOF1 and TOF2 have two layers each; all four layers have the same material and thickness (10 mm), with a 10 mm vacuum gap between the two layers of a station. Each layer is a whole slab, not segmented, with no paddle direction (a deliberate simplification); the two layers give two independent time measurements and dE/dx samples, and make the consistency of a station's two layers a check (B2.4).

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
| AMS-02 | Four TOF planes (8, 8, 10, 8 counters); system about 140 ps for protons | J15's 100 ps per layer is more optimistic, hence the 100 and 150 ps sensitivity (B2.7) |

J15's README uses this table to show that J15 is reasonable, and stresses that J15 is a synthetic geometry that represents no experiment.

---

## 5. Stage B1: `element_sim` and event files (adapter 0.3.0)

### B1.1 `element_sim` and its spec

**Location:** `adapters/geant4/assets/element_sim/` (CMake project linking Geant4 and `g4common`).

**Spec `element_sim.spec/1`** (schema in the same directory, using only keywords supported by `contracts/schema.py`):

| Block | Content |
|---|---|
| Coordinates | Origin at the world centre, mm; elements given by centre and half-lengths (boxes) |
| `materials` | NIST names or mixtures (component order kept; `g4common`'s material helper) |
| `elements` | Box elements: name, material, centre, half-lengths, mother (the world or one element; only one level of nesting), role (`passive`, `tracker-plane`, `tof-layer`, `calorimeter-active`, `calorimeter-passive`), repetition (for calorimeter sampling layers) |
| `field` | Uniform magnetic field: element it is attached to, B vector, accuracy parameters (B1.2) |
| `physics` | Physics list and EM option, cuts, regions (same semantics as `layered_sim`, through `g4common`) |
| `source` | `type: gun`: particle, energy (`energy_MeV` or `ekin_per_nucleon_MeV`), position, direction; `gps` and `event-file` only have their interface defined (architecture §9.2) and exit 2 when met |
| `run` | Number of events, threads, logical-run seed; `seeding` allows only `per-event` |
| `output.observables`, `output.blocks` | Same as task A's A2.3 |
| `output.event_file` | `level`: `none` (default), `summary`, `crossings`, `hits`; `compression` (default 1); `max_events_hits` (default 100) |

- Cross-field rules (elements do not overlap, daughters inside their mother, unique names, role compatible with material) are checked in the Python adapter; C++ checks only the minimum needed to run.
- Every run delivers the three boundary artifacts (summary, column map, effective config), the same as `layered_sim`.

### B1.2 Field

- Build `G4UniformMagField`, `G4FieldManager` and `G4ChordFinder` in `ConstructSDandField`, stored as `G4ThreadLocal`; the master and each worker have their own. Building them in `Construct()` would make workers share a non-thread-safe chord finder.
- Attach to the field-region mother with `SetFieldManager(fm, true)`, propagating to all daughters.
- With a field, add `G4StepLimiterPhysics`.
- The stepper class is written into the spec and recorded by the probe (a helix stepper would make the field-propagation check meaningless).
- Written from the API, without copying or adapting the B5 example's code (G5).

| Parameter | Nominal | Note |
|---|---|---|
| `delta_chord_mm` | 0.25 | Has no effect when the maximum step is below about 80 mm; recorded, not scanned |
| `delta_one_step_mm` | 0.01 | In a uniform field the Runge–Kutta truncation error is far below the intersection error; the scan is expected to show no effect; confirmed once |
| `delta_intersection_mm` | **1e-5** (0.01 µm) | Sets the accuracy of crossing points |
| `min_epsilon_step` | 5e-5 | |
| `max_epsilon_step` | 1e-3 | epsilon = delta one step / step length, clamped at this upper bound |
| `max_step_mm` | 10 | Needs `G4StepLimiterPhysics`; `G4UserLimits` must be set per volume and does not propagate to daughters |
| `stepper` | DormandPrince745 | Default of `G4FieldParameters` in 11.4.3 |

- **Probe:** `SimProbe.hh` walks `G4LogicalVolumeStore`, reads back B, the chord finder and each accuracy parameter via `GetFieldManager()`; deduplicates by pointer, records the volume of the original attachment; notes that the master sees only the master's copy. A field attached to a volume inside the target counts in the `tree-v1` target hash.
- **MT test:** a UI command that exists only in the test build reports each thread's field-manager pointer; they must all differ.

### B1.3 Plane-crossing scorer

- When the primary (track ID 1) **first** enters a `tracker-plane` or `tof-layer` element (pre-step point status `fGeomBoundary` and its volume is that plane), record the pre-step point's position, direction, kinetic energy, global time and PDG code; one "recorded" flag per plane.
- If the source lies inside a plane there is no `fGeomBoundary`, and no row is written for that plane.
- The per-event CSV keeps only summary columns (primary truth, total deposit per subsystem); crossings and per-layer deposits go into the ROOT file (B1.4).

### B1.4 Per-event ROOT files

| Item | Spec |
|---|---|
| Writing | Through `G4AnalysisManager` (ROOT output type); underneath is g4tools, bundled with Geant4, so no ROOT installation and no new build dependency |
| Files | One file per job; under MT, `SetNtupleMerging(true)` has the master merge into one file (in 11.4.3 only ROOT output supports ntuple merging); path written into the run record through `tilde()` |
| Structure | Flat ntuples with scalar columns only (I, D, S), each row keyed (`event_id` plus the ntuple's own secondary key); no vector columns |
| Row order | Not fixed after MT merging; readers always sort by key |
| When written | Rows filled in `EndOfEventAction`; the file written and closed at end of run. If the run is interrupted the file is incomplete and the run is incomplete (exit 3) |
| Version | Structure `element_sim.events/1`, `event_file_version` in the file |
| Hashes | File bytes include the write time and are not bit-identical; the run record keeps both the file sha256 (integrity) and the `content_sha256` from `simroot hash` (comparison and provenance) |
| Size | Not committed; the run record keeps path, hashes, row counts and size per ntuple |

| ntuple | Level | One row per | Columns |
|---|---|---|---|
| `run` | from `summary` | file | sha256 of spec and column map, program version and source hash, Geant4 version, logical-run seed, event range, `event_file_version`, process-number table |
| `events` | from `summary` | event | `event_id`, primary PDG code, kinetic energy, origin, direction; total deposit per subsystem; energy leaving the world; flags |
| `deposits` | from `summary` | event × volume with a deposit | `event_id`, `volume_id`, `copy`, total deposit, deposit by charged particles |
| `crossings` | from `crossings` (also in `hits`) | event × crossed plane | `event_id`, `plane_id`, `track_id`, PDG code, pre-step position, direction, kinetic energy, global time |
| `hits` | `hits` only | step with a deposit | `event_id`, `track_id`, `parent_id`, PDG code, `volume_id`, `copy`, pre- and post-step positions, time, deposit, step length, process number |

- If the number of events with `hits` exceeds `max_events_hits`, spec validation rejects it as `rejected` (exit 2).
- Estimate (J15, `crossings` level): at most about 4 kB per event uncompressed (`crossings` 10 rows × 80 B, `deposits` up to 110 rows × 28 B, `events` about 120 B); at most about 400 MB uncompressed for 10⁵ events.

### B1.5 `simroot`

**Location:** `adapters/geant4/assets/simroot/` (same CMake project as `element_sim`; links only Geant4's analysis library, no run manager).

- **First, a one-day trial:** confirm that `G4RootAnalysisReader` can read MT-merged, compressed files and string columns; if it cannot, `simroot` reads only flat scalar columns, and the strings of `run` go into a JSON side file.

| Subcommand | Content |
|---|---|
| `info` | Row counts and columns per ntuple, content of the `run` row; JSON output |
| `dump` | After sorting by key, writes the chosen ntuple and columns as CSV (stdout or `--out`), floating point as `%.17g`; can read several files at once; `--events` selects a subset |
| `hash` | Content hash: each ntuple sorted by key, numbers normalized as hex floats, then sha256; outputs `content_sha256` |

- Exit codes per `core/status.py`. Researchers may analyse the ROOT files directly with ROOT or uproot, but neither is a dependency of the pipeline or of the required tests.

### B1.6 Interface consistency between the two backends

- The three boundary artifacts from `element_sim` pass the same interface tests as `layered_sim`'s (schema, hashes, semantic names in the column map).
- A slab configuration identical to J14 gives the same benchmark decisions on `layered_sim` and `element_sim` (their events differ, so only statistical agreement is required: each observable's difference within 3·se_diff).

### B1.7 Adapter-change process

| Item | Content |
|---|---|
| Version | 0.2.0 → 0.3.0 |
| `adapter.json` | `assets` gains `element_sim/`, `simroot/`, the `element_sim.spec/1` schema; update `purpose` |
| `SIM_SOURCES` | Add the sources of `element_sim` and `simroot` (including `FieldSetup.*`) |
| G5 | Statement "written from the Geant4 API; no example code (B5 included) copied or adapted", confirmed by the reviewer in the VALIDATION entry; the same entry notes the ROOT file type and `simroot` |
| Tests | Offline tests (spec validation, cross-field rules); live tests (`HEP_GEANT4_LIVE_TEST=1`): geometry, field, event files, `simroot` round trip |
| Docs | The Geant4 row of `docs/capability-matrix.md`; adapter docs |

### B1.8 B1 acceptance

- [ ] `element_sim`'s J15 geometry passes overlap, material-budget and per-event energy-balance checks; the check values of §4.1 and §4.2 are recomputed by tests.
- [ ] Interface consistency of B1.6 and statistical agreement of the two backends.
- [ ] Under `per-event`, the same logical run with 1, 2, 4 jobs and 1, 2, 4 threads: summary integers identical, floating-point relative difference ≤ 1e-12.
- [ ] The field-manager pointers reported by the MT test command differ between threads; the field parameters recorded by the probe agree with the spec; the field counts in the target hash.
- [ ] The deterministic field check of B2.5 passes at nominal values; delta intersection 1e-3 mm fails as expected (field verification is completed in B1 because it needs only `element_sim`).
- [ ] `simroot` round trip: values of I, D, S columns identical at each level; `content_sha256` identical between serial and different thread counts; `deposits` summed per event equals the subsystem totals in the CSV; `hits` above the cap gives exit 2; an interrupted run is incomplete.
- [ ] VALIDATION GEANT4-ELEMENT; CHANGELOG; release manifest.

---

## 6. Stage B2: reconstruction, J15 and C2 (adapter 0.4.0, contracts C2)

### B2.1 `simreco` (digitization and reconstruction)

**Location:** `adapters/geant4/assets/simreco/` (CMake project; uses only the C++17 standard library, `SimSummary.hh` and `MiniJson.hh`; not linked to Geant4). Interface: `geant4_run.py reco`. Parameters (ε, σ_t, nominal B, calibration sample) are in a reco spec owned by hep-detector. No new scripts in hep-detector.

**Input:** `crossings` and `deposits` taken from the ROOT file by `simroot dump` (sorted by key, passed through a pipe, not stored), and the summary CSV.

| Step | Content |
|---|---|
| Silicon | Gaussian smearing of crossing points: bending direction (y) ε = 10 µm, non-bending direction (z) 30 µm; the fit uses the same x as the scorer (entry face) |
| TOF | Independent Gaussian smearing σ_t of each layer's time (100 ps; 150 ps separately for sensitivity); station time = mean of the two layers' times (after converting both to the station centre with the fitted track); also outputs each layer's dE/dx and the time difference of a station's two layers |
| Track | Circle fit in the x–y plane with multiple-scattering covariance (without it, χ²/dof is in the thousands at 1 GV); straight-line fit in the x–z plane; outputs R, χ², degrees of freedom; uses the nominal B |
| True rigidity | Mean of C·B / p_T,i from the crossing records of the six planes (C = 0.2998), using transverse momentum |
| β | Path length with the two station centres as end points, including the straight segments TOF1→Si1 and Si6→TOF2 and the 3D inclination; at low β reports the change in β between the stations |
| Calorimeter | Total deposit in active layers divided by the **electron** sampling fraction; the sampling fraction is obtained from a 10 GeV electron sample of role `calibration`; also outputs e/mip |
| Random numbers | Digitization random numbers from H(logical-run seed, event number, "digi") (the same hash as `SimSeed.hh`), separate from Geant4's random stream |

**Output:** a per-event result CSV (R, χ², β, calorimeter energy, etc.) and a run summary (`simulation-summary/1`, producer `simreco`; block accumulators of observables such as 1/R_reco − 1/R_true and β − β_true).

- Each `geant4_run.py reco` execution writes one computational-run record (with `**trace.provenance()`, `simreco`'s program hash, the hashes of the input run records and the ROOT file's `content_sha256`, and the list of dumped ntuples and columns). Changing digitization parameters does not require rerunning the simulation.
- Exit codes per `core/status.py`: 0 ok, 1 negative verdict, 2 `rejected` (unreadable input, including missing files), 3 incomplete; `reco` is registered in `MISSING_FILE_ARGS` of `tests/skills/test_cli_robustness.py`.
- The fitter's unit tests use Python's `tracker_resolution.py` (an independent implementation) as reference.

### B2.2 Result tables and transitive processing chains (C2)

- The reconstructed result table (e.g. rigidity resolution vs rigidity) is published as a **simulated dataset-record**, written by `geant4_run.py table` (with `trace.provenance()`).
- **Transitive processing chain:** today `dependencies.py` requires every input of a simulated table to be a computational-run with `extension.simulation` or `extension.study`; reconstruction records have neither. C2 changes this: the input chain may be arbitrarily deep, as long as every level is a recorded computational-run and every root of the chain is a simulation run (needs hep-computing's agreement; §9).
- J15's study record is `unvalidated`, so the table stays `unvalidated`; a communication using it gets the `communication.simulated_source` warning, and figures are marked "Simulation".

### B2.3 C2 validation classes

- **verification:** the table gains J15's checks (`field-propagation`, `tof-beta`, `tof-layer-consistency`); they do not count for upgrade. `GRADES` and the study spec's grade enum gain `verification`.
- **regression:** a general entry. The same study with the same settings runs once at each of two versions (plugin, backend or Geant4); scalars use the difference and SE of A1.8 with a two-sided test (α declared in advance) for a significant change; histograms use the χ² p-value (statistical uncertainty on both sides). The record is marked `changed` or `unchanged` and does not affect the label; a significant change in a reference observable may trigger a sci-fix check.
- **surrogate:** a general entry. A study of a surrogate model declares its reference simulation (a recorded full-simulation run) and scope; decided by IUT or χ². On pass it gets `consistent-with-reference-simulation` (with the reference run's hash and scope); the physics label can only inherit upgrades the reference simulation already has, with the scope being the intersection of the two.
- Gated as in C1: `strict or _at_least(contract_version, C2)`, no warning branch.

### B2.4 J15 validation ladder

| Check | Class | Reference | Spec | Negative control |
|---|---|---|---|---|
| overlap | implementation | — | — | Shift one Si plane to create an overlap |
| Per-event energy balance (J15 geometry) | implementation | Energy conservation | — | Omit 2 mₑc², double counting |
| Material budget (geantino) | implementation | PDG X₀ sum | Tolerance about 2 % (Geant4's X₀ formula differs from PDG by about 1 %) | Pb density ± δ |
| `field-propagation` | **verification** | Charged geantino against the analytic helix | See B2.5 | B × (1 ± δ) on the Geant4 side |
| `field-propagation-muon` | **sanity** | Plane-averaged true 1/R (B2.1) | μ⁻ 1, 10, 100 GV; tolerance = t·SE + 0.05 %; N ≈ 400 (1 GV), ≈ 7400 (100 GV) | B × (1 ± 1 %) on the Geant4 side |
| Fitter unit test | test (not a benchmark) | Toy truth (R ≥ 300 GV): `simreco`'s C++ fit against `tracker_resolution.py` | — | — |
| One-off multiple-scattering comparison | sanity | The analytic term of `multiple_scattering.py` (no log); optionally `toy_spectrometer.py` (needs NumPy) | μ and p, 1–10 GV, with β | — |
| `tof-beta` | **verification** (bookkeeping) | Kinematics along the true trajectory | — | Scorer test flag injects a time offset; there is no physics control on the Geant4 side, noted in the docs |
| `tof-layer-consistency` | **verification** (bookkeeping) | Time difference between a station's two layers against "inter-layer path length / βc" (66.7 ps at β = 1, normal incidence) | Mean residual 0; width √2 σ_t (141 ps at 100 ps) | Test flag injects an offset into one layer's scorer time |
| `sampling-fraction` | sanity | Ratio of ionization dE/dx at the run momentum from the PDG muon energy-loss tables (Groom et al., obtained via hep-citations) | μ⁻ 1 GeV; statistic Σ PVT deposit / Σ (PVT + Pb) deposit; plausible range ±10 % (the reviewer's Bethe estimate is about 0.271); different seed from the `calibration` sample | PVT density ± δ |
| Shower containment | sanity | PDG gamma profile, effective critical energy of the mixture about 10.2 MeV | Electrons 1–100 GeV | — |
| `longitudinal-profile` (0.21.0) | not applicable | Its reference is the published ALICE FoCal-E measurement, valid only for that stack; J15's calorimeter differs, and is embedded | — | — |
| Optional: stopping power in an isolated PVT slab | reference (`configuration: isolated`) | Bethe (RPP 2024 eq. 34.5) | p, T = 200–600 MeV (βγ ≈ 0.67–1.37, below PVT's 10^x₀ ≈ 1.40, so the density correction is 0), 1 cm slab, nuclear interactions excluded (about 1 %); Sternheimer parameters from Sternheimer, Berger & Seltzer (1984), checked via hep-citations | PVT density ± δ |

The optional last item runs in an isolated slab (a single element of `element_sim`), not as part of the J15 detector, to show the upgrade path for a new material. Event counts and decisions follow A1.6–A1.10.

### B2.5 Convergence scans

**Field accuracy and maximum step (deterministic, no statistics; completed in B1):**
- Tracks: charged geantinos (mass 0, β = 1) at rigidities 0.6, 1, 10, 100, 1000 GV.
- Directions: normal incidence; 50 mrad in the bending plane **opposite to the bending direction** (+y for positive charge); ±50 mrad in the non-bending plane.
- Appendix A checks that with these directions every track reaches every Si plane and both TOF2 layers and does not leave the field-region mother. With the bending direction instead, 0.6 GV and 1 GV miss Si6.
- Reference: the analytic helix; after the track leaves the field region, piecewise straight lines; only planes the analytic track actually reaches are compared.

| Scan | Grid | Decision |
|---|---|---|
| delta intersection | 1e-3, 1e-4, 1e-5, 1e-6 mm | At nominal (1e-5), the in-plane distance √(Δy² + Δz²) ≤ 0.5 µm (ε/20) on all planes; the two finest differ by ≤ 0.2 µm; 1e-3 mm is expected to fail |
| Maximum step | 100, 30, 10, 3 mm | Same |
| delta one step and epsilon | nominal and 1/10 | Expected no change; confirmed once |
| TOF2 path time (both layers) | — | \|Δt\| ≤ 1 ps (about 0.3 mm of path), checks path length only |

**Calorimeter production cut:**
- Grid: 0.1, 0.3, 0.7, 1.0 mm.
- Sample: 10 GeV e⁻; trial first, then N per A1.9.
- Observables: total deposit (relative tolerance 1 %, about 400 showers per point), rear leakage fraction (computed from the existing `leak_rear_MeV`, back face only; **absolute** tolerance 0.002, about 5000 showers per point).
- Events per point: the larger of the two; decision per A1.8 (IUT).

The Si production cut is not converged in J15: it affects only the Si deposit, and J15's Si results are not used as evidence. The study spec's `convergence_plan.observables` enum gains total deposit and rear leakage fraction. The parameter sets each benchmark depends on are declared in advance and checked against the probe's actual settings.

### B2.6 Variations

| Variation | Scope | Rule |
|---|---|---|
| EM option4 vs option3 | Calorimeter profile, sampling fraction | `G4R-PRECISION-EM` |
| FTFP_BERT_EMZ vs **QGSP_BIC_EMZ** | Only interaction probability and first-interaction depth in the calorimeter; nucleons below 1.5 GeV | `G4R-BIC-RANGE`; below 3 GeV for π and at 6–12 GeV for hadrons both use the same model and must not be used as a variation |
| Vacuum vs air | Multiple scattering, rigidity resolution | — |

### B2.7 TOF time-resolution sensitivity

- `simreco` reconstructs once with σ_t = 100 ps and once with 150 ps (same simulation, no rerun).
- Report σβ/β for both (expected about 2.3 % and 3.5 %) and the effect of β resolution vs rigidity; the README says that 100 ps is more optimistic than AMS-02's system resolution (about 140 ps).

### B2.8 J15 study and journey

- J15's study spec declares: observables (rigidity resolution, β resolution, sampling fraction, total deposit, rear leakage fraction), K and B, benchmarks, convergence plan, variations, stopping rule.
- All results `unvalidated`; the README and the study record state its role as a "verification carrier".

### B2.9 Recorded-data budget

- `check_packaging.py` caps each file at 2 MiB; J14's `recorded/` is 2.6 MB (for reference).
- ROOT files are not committed; run records keep only the path, file sha256, `content_sha256`, row counts and size per ntuple; ROOT files needed by tests are produced in live tests.
- J15 commits only: run summaries (simulation and reconstruction), effective configs, column maps, summary CSVs with reduced columns (benchmark runs), reduced crossing and deposit records extracted with `simroot dump --events` (for offline replay tests of `simreco`; the event subset set by the budget), reconstructed result tables.
- Acceptance: each file ≤ 2 MiB, J15's `recorded/` total ≤ 3 MB.

### B2.10 Registration and docs

| Item | Content |
|---|---|
| Script count | No new scripts in hep-detector; `DetectorScriptCount` stays 21, line 47 of `docs/capability-matrix.md` unchanged |
| CLI registration | `geant4_run.py reco` and `table` registered in `tests/skills/test_cli_robustness.py` and the adapter tests; `simreco` sources listed in `assets` of `adapter.json` |
| Routing table | `skills/hep-detector/SKILL.md` not changed; descriptions of J15, `element_sim` and `simreco` go into `geant4-study-protocol.md` and the adapter docs |
| Journey | J15; `docs/researcher-journeys.md`, the examples table of `docs/maintenance.md`; `tests/examples/test_geant4_minimal_spectrometer.py` (replay and compare decisions) |
| Capability | `docs/capability-map` (new entry under `full-detector-simulation`, run `capability_map.py --write`), `docs/capability-matrix.md` |
| Routing | New routing case for J15; `check_routing_static.py` reads the journey list from `docs/researcher-journeys.md`, so once J15 is in the table it **must** have a routing case. Rerun the live Geant4 cases, including the existing Traditional Chinese underspecified case `g4-underspec-2` |
| Description length | Description 1,018 / 1,024 characters; routing cases reuse existing trigger words, the description is not changed |
| Independent review | This task's Markdown (protocol changes, J15 README, this document) is reviewed with 0.22.0's `review.py`; its record is advisory only and, per O04/O14, does not replace the human G5 confirmation |
| Other | `reference_inventory.py --check`, CHANGELOG, release manifest, adapter 0.4.0, `SIM_SOURCES` gains `simreco`'s sources; a required C++17 CI job builds and tests `simreco` |

### B2.11 B2 acceptance

- [ ] `field-propagation-muon`, `tof-beta`, `tof-layer-consistency` and `sampling-fraction` are complete; each negative control is caught per B2.4, or the absence of a control is noted.
- [ ] `simreco`'s fitter unit tests pass with `tracker_resolution.py` as reference; `simreco` is built and tested in a required CI job.
- [ ] `simreco`'s summary passes the same consistency test as task A's A2.9 (Python recomputes from the per-event result CSV).
- [ ] A processing chain of three or more levels (simulation → reconstruction → table) is accepted by `dependencies.py`; it is rejected when a root is not a simulation run.
- [ ] The verification class does not count for upgrade; a regression check (e.g. J14 on two plugin versions) produces a `changed` or `unchanged` record without affecting the label; a contract test of the surrogate rule (a surrogate cannot get an upgrade the reference simulation lacks).
- [ ] Contract tests of the isolation rule: missing configuration, embedded, and class differing from the table are all rejected; J14 still passes under `--strict`.
- [ ] The TOF σ_t sensitivity at 100 and 150 ps is reported.
- [ ] Recorded budget, registration items and docs all done; VALIDATION GEANT4-J15.
- [ ] An independent agent, using only the docs and tools, completes "rigidity resolution of a 1 GV proton in J15": the result record passes `validate.py --strict`, the label is `unvalidated`, the resolution lies within the range of the §4.2 table, and no maintainer help is needed.

---

## 7. Contracts and versions

| Object | Location | Version |
|---|---|---|
| verification, regression, surrogate classes; J15 checks; transitive processing chains | `contracts/validate.py`, `contracts/dependencies.py` | C2 (minor, gated) |
| `element_sim`, `element_sim.spec/1`, `element_sim.events/1`, `simroot` | adapter | adapter 0.3.0 |
| `simreco`, reco spec | adapter (C++, not linked to Geant4) | adapter 0.4.0 |
| `verification` in `GRADES` and the study spec's grade enum; total deposit and rear leakage fraction in `convergence_plan.observables` | hep-detector | with the plugin version |

---

## 8. Not done and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| σ(1/R) in the measurement-dominated region as a benchmark | Not done | Replaced by the fitter unit test |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | Not done | Replaced by `simreco` in C++ |
| New geometry features in `layered_sim` | Not done | New features only in `element_sim` |
| Reading ROOT directly from Python (uproot) in the pipeline | Not done | Through `simroot` |
| Ion sources and Birks visible energy (future J16) | Deferred | Cosmic-ray nuclide studies, and a documented Birks constant for PVT. Implementation per 11.4.3: get the ion with `GetIon(Z, A)` in `GeneratePrimaries`; set kB in `Construct` and `SetBirksActive(true)` at PreInit, then get it via `G4LossTableManager::Instance()->EmSaturation()` |
| Non-box solids, rotations, GDML input, field maps, fringe fields in `element_sim` | Deferred | The first study that needs them and cannot use a user application |
| Distribution-level benchmarks, combination and selection of observables, profiles, `gps` and `event-file` sources, `simreduce` | Deferred (interfaces defined in architecture §9.2) | Each one's first use case |
| RNTuple, vector columns | Deferred | ROOT file size or read speed becomes a bottleneck |

For other items not done or deferred, see task A §10.

---

## 9. Decisions for the maintainer and residual risks

**To decide:**
1. The transitive processing chain of C2: needs agreement from hep-computing, owner of the computational-run schema.
2. Classification of C2 (proposed minor).
3. `simreco` needs a required C++17 CI job.
4. Where ROOT files are stored and for how long (not committed to the repo).
5. Maintenance ownership of `element_sim` as the second Geant4 program (proposed hep-detector).

**Residual risks:**
1. The sampling-fraction reference needs the PDG muon energy-loss tables; the optional PVT benchmark needs Sternheimer parameters. Both need literature records via hep-citations before use.
2. Calorimeter showers dominate CPU time; convergence of rear leakage needs about 5000 showers per point; event counts are set by trial runs and recorded.
3. The read capability of `G4RootAnalysisReader` is unverified (the B1.5 trial).
4. ROOT files of large samples can reach hundreds of MB; under MT merging, worker baskets stay in memory until end of run; `hits` has an event cap; size and memory confirmed in trial runs.
5. Maintenance cost of two Geant4 programs; duplication controlled through `g4common`.
6. Quick load has only 931 bytes left, description 1,018 / 1,024 characters: this task must not change `SKILL.md` or the description.
7. Effort not yet estimated; re-estimate after task A based on the actual `g4common`.
8. Task A's residual risks (the block-independence assumption, near-threshold decisions, the probe assuming worker and master settings are the same) also apply; see task A §11.

---

## 10. Suggested order of work

**B1**
1. Pre-start checks (§0); confirm the interfaces of §2 exist.
2. `element_sim`'s spec, schema, cross-field rules and geometry (B1.1); two-backend consistency with a slab configuration identical to J14 (B1.6).
3. Field (B1.2) and MT test; the deterministic field check of B2.5 (no statistics, can be verified earliest).
4. Build the J15 geometry (§4.1); pass overlap, material budget, energy balance; recompute the check values of §4.1 and §4.2 in tests.
5. Plane-crossing scorer (B1.3) and ROOT files (B1.4); `simroot` after a one-day trial (B1.5).
6. Adapter-change items of B1.7; tick all of B1.8.

**B2**
1. `simreco`'s fitter unit tests first, then the `simroot dump` input (B2.1); set up the required CI job.
2. `geant4_run.py reco` and `table`; C2's transitive processing chain and validation classes (B2.2, B2.3) with contract tests.
3. Run the validation ladder, calorimeter cut convergence, variations and TOF sensitivity in E2 (B2.4–B2.7).
4. J15 study, recorded data, registration and docs, the independent-agent acceptance problem (B2.8–B2.10); tick all of B2.11; run the checks of task A §9.

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
- Sources for PAMELA and AMS-02 are in [`architecture.en.md`](architecture.en.md) §14
- To obtain: PDG muon energy-loss tables (Groom, Mokhov & Striganov); Sternheimer, Berger & Seltzer (1984), *Atomic Data and Nuclear Data Tables* 30, 261

## Appendix C: Version history

| Version | Content |
|---|---|
| Detector document and v5 | Single-axis stacked spectrometer; Gluckstern small-N formula corrected; field direction and field-check grid |
| 2026-10-22 | TOF1 and TOF2 with two layers each; digitization and reconstruction moved to C++; per-event ROOT files; split out as task B |
| **2026-10-22 (this version)** | **Rewritten for the architecture redesigned with reference to real experiments: new `element_sim` as a second backend (replacing spec/2 and the rework of `layered_sim`); B1 (`element_sim`, field, crossings, ROOT files, `simroot`), B2 (`simreco`, J15, C2's verification, regression, surrogate and transitive chains); PAMELA and AMS-02 comparison and TOF sensitivity added** |
