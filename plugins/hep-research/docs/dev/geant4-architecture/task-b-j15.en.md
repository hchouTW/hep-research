# Task B: J15 minimal spectrometer

> Document type: implementation spec (for the implementing agent and reviewers). Status: proposal, awaiting the maintainer's approval
> Order: **starts only after both phases of task A ([`task-a-core.en.md`](task-a-core.en.md)) are merged**
> Baseline: when written, the same as task A (hep-research `main` at `9f08796`, contracts 3.5.0, Geant4 11.4.3); must be re-checked before starting (§0)
> Date: 2026-10-22
> Language: English translation of [`task-b-j15.md`](task-b-j15.md) (Traditional Chinese original), same content. If they disagree, the Chinese wins and the English is corrected
> Example: J15 is a **synthetic geometry**, a vehicle for verification, not the detector of any experiment

---

## 0. Task card

**Goal.** Demonstrate a magnetic field, several subsystems and a reconstruction chain with a minimal spectrometer (J15), and establish the `verification` grade: a field region, a plane-crossing scorer, digitization and reconstruction in the C++ `simreco`, and reconstruction records as inputs of simulated tables.

| Content | Version | Effect on J14 |
|---|---|---|
| field region (`field`), plane-crossing scorer and the `crossings` level of the ROOT file, `simreco` (digitization and reconstruction; mixtures already exist in 0.21.0), the `verification` grade, a reconstruction record as input of simulated tables | adapter **0.3.0**, contracts **C2** (minor) | not re-recorded; `sources_sha256` of later live reruns changes (expected) |

**Out of scope:** any change to task A's interfaces (if one is needed, make it first within task A as an adapter patch release); ion sources and Birks (future J16); real geometry and field maps (§11).

**Deliverables:** field and plane crossings in layered_sim, `simreco`, `geant4_run.py reco` and `table`, the J15 example (a new folder under `examples/`, README, recorded data), the C2 contract change, the J15 journey and routing case, VALIDATION entry GEANT4-J15, CHANGELOG, release manifest.

**Definition of done:** every box in §10 is ticked and every check of task A §10 passes.

**Main decisions:**
1. **The validation grade follows the nature of the reference** (task A, principle 9). A reference that is an exact consequence of the inputs (analytic helix, kinematics) gives verification, which cannot upgrade.
2. **Field accuracy is checked deterministically.** A charged geantino is compared with the analytic helix; no statistics are needed (B2.2).
3. **J15 is a vehicle for verification.** Every result in the full detector is `unvalidated`; only the optional benchmark run in an isolated slab shows the upgrade path for a new material (B2.1, B1.5).
4. **No new hep-detector script.** Reconstruction is in the C++ `simreco`, with the interface in the adapter; quick load and description are unchanged (§9).

**Before starting:**
1. Confirm that task A's phase 1 (C1) and phase 2 (adapter 0.2.0) are both merged and that every interface listed in §2 exists.
2. With the method of task A appendix B.2, re-check against the `main` of that time the facts this document cites (quick load, description length, journey list, `DetectorScriptCount`, contracts version), and update this document (both languages).
3. Read task A §2 (hard rules) and §1 (terms); this document does not repeat them.

---

## 1. Terms and notation

| Term | Meaning |
|---|---|
| J15 | this task's minimal spectrometer (a synthetic geometry) |
| bending plane | the x–y plane (B along z); the non-bending direction is z |
| rigidity R | p/|q|, in GV; C = 0.2998 GV/(T·m) |
| MDR | maximum detectable rigidity: the rigidity where σ_R/R = 1 from the measurement term alone |
| TOF station | TOF1 or TOF2; two layers (a, b) per station |
| charged geantino | a Geant4 charged test particle that feels only the field and has no material interactions (mass 0, β = 1) |
| verification | the grade of a check whose reference is an exact consequence of the inputs; never counted for upgrades (C2 adds it to the contracts table) |
| C2 | the next unused contracts minor when task B is merged (after C1) |
| references | "B1.3" is a work item of this document; "§4.2" a section of this document; "A1.6", "A2.9" are work items of task A; "task A §2" is a section of task A |

**Main files (relative to `plugins/hep-research/`):** `adapters/geant4/assets/layered_sim/` (new `FieldSetup.*`; extended scorers and `EventFile.*`); `adapters/geant4/assets/simcore/` (new `simreco`); `adapters/geant4/assets/geant4_run.py` (new `reco`, `table`); `contracts/validate.py`, `contracts/dependencies.py` (C2); `skills/hep-detector/scripts/geant4_benchmarks.py` (`GRADES`); `skills/hep-detector/assets/geant4-study-spec.schema.json`; `skills/hep-detector/references/geant4-study-protocol.md`; `docs/researcher-journeys.md`, `docs/maintenance.md`, `docs/capability-matrix.md`, `docs/capability-map`; `tests/examples/test_geant4_minimal_spectrometer.py` (new).

---

## 2. Prerequisites: interfaces from task A

| Task A provides | Task B uses it for |
|---|---|
| C1: benchmark table, scope compares kind, configuration and the isolation rule (A1.1–A1.3) | every J15 benchmark is `embedded` and not counted for upgrades; C2 adds `verification` to the table (B1.5) |
| statistical rules: IUT gate, two-stage event count, seeds `H(study_id, role, point_id, k)`, sub-runs (A1.5–A1.8) | event counts and decisions of the convergence scans and benchmarks (B2.1, B2.2) |
| the `field` block reserved in spec/2 (A2.2); adapter 0.2.0 rejects a non-empty `field` | implements `field` (B1.1) and lifts the rejection |
| when `G4StepLimiterPhysics` is added (A2.3) | also when a field is present |
| the spec/2 gun field `energy_MeV` (A2.2) | adds `ekin_per_nucleon_MeV` |
| probe (A2.6) and column map `layered_sim.output/2` (A2.7) | the probe also records the field parameters (B1.1); the column map gains the `crossings` columns |
| `simcore` (A2.8) and its required CI job | the new executable `simreco` (B1.3), built and tested in the same CI job |
| per-event ROOT files (A2.9) and `simroot` (A2.10) | adds the `crossings` level and ntuple (B1.2); `simreco` reads through `simroot dump` |

---

## 3. Hard rules

All of task A §2 applies. In addition:

1. Do not change `skills/hep-detector/SKILL.md` or hep-detector's description (only 931 bytes of quick-load budget left; description at 1,018 / 1,024 characters). J15's routing case must use trigger words already in the description.
2. No experiment names in `skills/` or `contracts/` (ALICE included); the contracts table and protocol cite the `longitudinal-profile` reference by citation key.
3. The field code is written from the Geant4 API; no code from the B5 example is copied or adapted (G5).
4. The shared stanza text is not changed (point 5 says "3.1.0 upgrade rule"; changing it touches every SKILL.md and needs live routing reruns).
5. J15's `recorded/`: each file ≤ 2 MiB, ≤ 3 MB in total; ROOT files are not committed (§7).
6. Every J15 result is `unvalidated`; no J15 benchmark may count toward an upgrade.

---

## 4. J15 design

### 4.1 Geometry

Coordinates: world centre as origin, stacking axis x, units mm.

**Field: B = (0, 0, +0.5 T).** The bending plane is x–y; the non-bending direction is z. A positive charge moving along +x bends toward −y; a μ⁻ toward +y.

```
x:  −1000   −810 … −780   −520 −500        …         300  320    490 … 520   550          900   ±1200
     gun    TOF1 (2 layers) │ Si1  Si2  Si3  Si4  Si5  Si6  │     TOF2 (2 layers) calorimeter 50 layers  world edge
            10 + 10 mm    │◄────── uniform field 0.5 T ẑ (−520 … 320) ─────►│     10 + 10 mm   Pb 2 / PVT 5 mm
```

| Element | Material | Front face `at_mm` | Thickness | Extent | Transverse (y × z) |
|---|---|---|---|---|---|
| World | `G4_Galactic` | — | 2400 | −1200 … 1200 | 1200 × 1200 |
| Gun | — | x = −1000, y = z = 0 | — | — | — |
| TOF1a, TOF1b | `G4_PLASTIC_SC_VINYLTOLUENE` | −810, −790 | 10 each | −810 … −800, −790 … −780 | 300 × 300 |
| Field mother | `G4_Galactic` | −520 | 840 | −520 … 320 | 300 × 300 |
| Si1–Si6 (daughters) | `G4_Si` | −500.15 + 160k | 0.3 | centres −500, −340, −180, −20, 140, 300 | 200 × 200 |
| TOF2a, TOF2b | `G4_PLASTIC_SC_VINYLTOLUENE` (same as TOF1) | 490, 510 | 10 each | 490 … 500, 510 … 520 | 400 × 400 |
| Calorimeter | 50 × (`G4_Pb` 2 + PVT 5) | 550 | 350 | 550 … 900 | 500 × 500 |

**TOF stations.** TOF1 and TOF2 each have two layers; all four are the same material (`G4_PLASTIC_SC_VINYLTOLUENE`) and thickness (10 mm), with a 10 mm vacuum gap between the two layers of a station. Each layer is a whole slab, unsegmented and with no paddle direction (a deliberate simplification); the two layers give two independent time measurements and dE/dx samples, and their agreement within a station is a check (B2.1).

**Checks** (the script of appendix A; recomputed in tests):
- Lever arm L = 0.800 m; the front of Si1 and the back of Si6 are 19.85 mm from the mother's edges.
- The field extends 20 mm beyond the measurement region at each end.
- The distance between the TOF station centres (layer midpoints: −795 and 505 mm) is D = 1.300 m.
- The back face of TOF2's rear layer (520) is 30 mm from the calorimeter's front face (550); TOF1's front layer (−810) is downstream of the gun (−1000).
- The world contains the gun and the back of the calorimeter.

Materials (11.4.3 NIST definitions against PDG): `G4_PLASTIC_SC_VINYLTOLUENE` is 1.032 g/cm³ with I = 64.7 eV, as in PDG; `G4_Si` is 2.33 g/cm³ (PDG 2.329).

**Deliberate simplifications** (the J15 README lists each): uniform field with sharp edges, no magnet material, silicon as whole planes (no strips, no charge sharing, no δ-ray centroid shifts), unsegmented TOF layers (no paddles, no direction), no optical photons, no trigger or readout electronics.

### 4.2 Parameters and acceptance

| Parameter | Value | Basis |
|---|---|---|
| B | 0.5 T | the rigidity where the scattering term equals the measurement term is about 16–22 GV (μ), independent of B. 0.5 T gives one decade at 1–10 GV and one at 100–1000 GV |
| Si layers | 6 | N = 4 leaves one degree of freedom in the bending plane; N = 8 improves the MDR by only about 8 % |
| MDR | about 1172 GV | σ_R/R = 1 from the measurement term alone. Reference from the exact least squares of `tracker_resolution.py` (constant 0.2998). `mdr_intrinsic_only_gv` of `multiple_scattering.py` has the same definition but uses the Gluckstern approximation (about 1131 GV at N = 6); since 0.21.0 it also reports `intrinsic_coefficient` (including the exact coefficient used here) and warns below N = 10 |
| TOF | two layers per station; σβ/β ≈ 2.3 % (100 ps per layer, independent layers, β = 1; 3.3 % with one layer per station) | D = 1.3 m; station time is the mean of the two layers, σ_station = σ_layer / √2 |
| Calorimeter | 18.4 X₀, 0.886 λ_I, 50 cm wide | 0.89 λ_I suffices for e/p separation by shower shape, not for hadron energy |

**Scattering term.** The design estimate uses the Highland formula with the log term on the total thickness, times a factor of 1.0–1.4. A reviewer's exact least squares with discrete scattering planes gives 1.02 (weighted fit) to 1.06 (unweighted). By its convention `multiple_scattering.py` has **no** log term; state the difference between the conventions when comparing.

| Particle | Rigidity | β | Scattering term | Rigidity where the terms are equal |
|---|---|---|---|---|
| μ | 1 GV | 0.994 | 1.3–1.9 % | 16–22 GV |
| p | 0.6 GV | 0.539 | 2.5–3.5 % | 29–41 GV |
| p | 1 GV | 0.729 | 1.8–2.6 % | 21–30 GV |
| p | 2 GV | 0.905 | 1.5–2.1 % | 17–24 GV |

**Acceptance** (unit charge, on-axis normal incidence, uniform field, sharp edges):

| Condition | Minimum rigidity |
|---|---|
| does not leave the field mother sideways before x = 320 (\|y\| ≤ 150 mm) | 0.364 GV |
| reaches Si6 (\|y\| ≤ 100 mm) | 0.511 GV |
| reaches TOF2's front layer (x = 490, \|y\| ≤ 200 mm) | 0.385 GV |
| crosses both TOF2 layers (x = 520, \|y\| ≤ 200 mm) | 0.404 GV |
| calorimeter front face, shower axis within 250 − 2 R_M,eff | 0.490 GV |
| calorimeter back face, same | 0.745 GV |

Overall threshold 0.75 GV; 0.51 GV for tracking plus TOF only. Below 0.364 GV a track leaves the field region sideways and then goes straight in the field-free world.

Electrons: the shower axis is off by 82 mm and 127 mm at the calorimeter's front and back faces at 1 GeV, 16 mm and 25 mm at 5 GeV. Bremsstrahlung photons from the upstream 11.3 % X₀ (83 % of it in the four TOF layers) are not bent, so the shower axis is not a straight extrapolation; the 79 mm margin is a geometric estimate, the upstream material is twice that of a single-layer design, and shower checks must use the actual lateral energy distribution. Electron shower checks start at 1 GeV.

**Upstream energy loss** (Bethe integral, 2 cm of PVT in TOF1's two layers):

| Proton rigidity | Kinetic energy | TOF1 loss (two layers) | Δp/p | Change of β between the TOF station centres |
|---|---|---|---|---|
| 0.6 GV | 175 MeV | 10.23 MeV | 3.20 % | 2.87 % |
| 1 GV | 433 MeV | 6.00 MeV | 0.82 % | 0.46 % |
| 2 GV | 1271 MeV | 4.34 MeV | 0.24 % | 0.05 % |

At 0.6 GV β changes by 2.87 % between the stations, more than the TOF resolution (2.3 %): TOF measures the path-averaged β, so a low-rigidity β comparison needs a β model with energy loss, or is restricted to 2 GV and above. TOF1 is upstream of the first Si plane and changes only the incoming direction and momentum, not the curvature resolution; the true rigidity comes from the Si crossing records and is unaffected by TOF1.

**J14 cannot be reused.** J15's Si planes differ from J14's in material (`G4_Si` against `Si_study`), physics settings and cuts, and J15 records only the entry, so J14's E_in − E_exit observable cannot be formed.

---

## 5. Implementation work items

### B1.1 Field implementation

**Change:** `layered_sim` (new `FieldSetup.*`; lift the rejection of the spec/2 `field` block); probe; `SIM_SOURCES` gains `FieldSetup.*`.

- Build `G4UniformMagField`, `G4FieldManager` and `G4ChordFinder` in `ConstructSDandField`, stored as `G4ThreadLocal`; the master and every worker have their own. Building them in `Construct()` would make workers share a chord finder that is not thread-safe.
- Attach with `SetFieldManager(fm, true)` to the field mother, which propagates to all daughters.
- Add `G4StepLimiterPhysics` when a field is present (the composition rule of A2.3).
- The stepper class is written in the spec and recorded by the probe (a helix stepper would make the field-transport check meaningless).
- Written from the API; no B5 example code copied or adapted (G5).

| Parameter | Nominal | Note |
|---|---|---|
| `delta_chord_mm` | 0.25 | inactive below a maximum step of about 80 mm; recorded, not scanned |
| `delta_one_step_mm` | 0.01 | in a uniform field the Runge–Kutta truncation error is far below the intersection error, so no effect is expected; confirmed once |
| `delta_intersection_mm` | **1e-5** (0.01 µm) | sets the precision of crossing points |
| `min_epsilon_step` | 5e-5 | |
| `max_epsilon_step` | 1e-3 | epsilon = delta one step / step length, clamped at this ceiling |
| `max_step_mm` | 10 | needs `G4StepLimiterPhysics`; `G4UserLimits` must be set per volume and does not propagate to daughters |
| `stepper` | DormandPrince745 | the default of 11.4.3 `G4FieldParameters` |

- **Probe:** walk `G4LogicalVolumeStore` and read back B, the chord finder and the accuracy parameters through `GetFieldManager()`; de-duplicate by pointer, record the volume the manager was attached to; state that the master sees only its own copy.
- **MT test:** a UI command that exists only in test builds reports each thread's field-manager pointer; they must all differ.
- The gun gains `ekin_per_nucleon_MeV`.

### B1.2 Plane-crossing scorer and the `crossings` level of the ROOT file

**Change:** `layered_sim`'s scorers and `EventFile.*`; the column map; `simroot` tests.

| Item | Rule |
|---|---|
| Plane-crossing scorer | on the primary's (track ID 1) **first** entry into a tracker or TOF plane (pre-step status `fGeomBoundary` and the volume is the plane), record the pre-step position, direction, kinetic energy, global time and PDG code; one "recorded" flag per plane. A gun inside a plane never shows `fGeomBoundary`; that plane gets no row |
| Mixtures | already supported in 0.21.0 (`materials[].components`); nothing to add for J15, where PVT and Pb are NIST materials |
| Output | per-event ROOT file (A2.9, `crossings` level): event truth, crossing records for 10 planes (6 Si, 4 TOF layers), per-volume deposits (calorimeter layers included); the per-event CSV keeps only summary columns (primary truth, total deposit per subsystem); the column map describes both and is generated automatically |

**The `crossings` level.** `output.event_file.level` gains `crossings` (which includes every ntuple of `summary`), `event_file_version` is incremented, and the ntuple layout becomes `layered_sim.events/2` (additions only; no existing ntuple changes):

| Ntuple | Level | One row per | Columns |
|---|---|---|---|
| `crossings` | from `crossings` (also in `hits`) | event × crossed plane | `event_id`, `plane_id`, `track_id`, PDG code, pre-step position, direction, kinetic energy, global time (the plane-crossing scorer above); planes not crossed get no row |

`simroot`'s round-trip and content-hash tests gain the `crossings` level (§10).

### B1.3 Digitization and reconstruction (`simreco`)

**Change:** `adapters/geant4/assets/simcore/` (new `simreco`; `SIMCORE_SOURCES` gains its sources); `geant4_run.py` (new `reco`); a reco spec owned by hep-detector (parameters ε, σ_t, nominal B, calibration sample). hep-detector gets no new script.

Inputs: `crossings` and `deposits` taken from the ROOT file by `simroot dump` (sorted by key, passed through a pipe, not stored) and the summary CSV.

| Step | Content |
|---|---|
| Silicon | Gaussian smearing of the crossing points: ε = 10 µm in the bending direction (y), 30 µm in the non-bending direction (z); the fit uses the same x as the scorer (the entry face) |
| TOF | independent Gaussian time smearing σ_t = 100 ps per layer; station time = mean of the two layers (each first moved to the station centre along the fitted track); the per-layer dE/dx and the time difference of the two layers of a station are also reported |
| Track | circle fit in x–y with a multiple-scattering covariance (without it χ²/dof is in the thousands at 1 GV); straight-line fit in x–z; outputs R, χ², degrees of freedom; nominal B |
| True rigidity | the mean of C·B / p_T,i over the six plane-crossing records (C = 0.2998), with the transverse momentum |
| β | path length between the station centres, including the straight segments TOF1→Si1 and Si6→TOF2 and the 3D dip angle; at low β, the change of β between the stations is reported |
| Calorimeter | total active deposit divided by the **electron** sampling fraction, obtained from a 10 GeV electron sample with the `calibration` role; e/mip is also reported |
| Random numbers | counter hash, separate from Geant4's stream |

- Each execution of `geant4_run.py reco` writes a computational-run record (with `**trace.provenance()` and `simreco`'s program hash) whose inputs are the adapter's run records (with hashes and the ROOT file's `content_sha256`), and records the dumped ntuples and columns. Changing digitization parameters does not require rerunning the simulation.
- Exit codes of `simreco` and `geant4_run.py reco` follow `core/status.py`: 0 ok, 1 a negative verdict, 2 `rejected` (unreadable input, a missing file included), 3 incomplete; `reco` is registered in `MISSING_FILE_ARGS` of `tests/skills/test_cli_robustness.py`.
- The fitter's unit tests use the Python `tracker_resolution.py` (an independent implementation) as reference (B2.1).

### B1.4 Reconstructed result tables (simulated dataset-records) and the C2 marker

- Reconstructed result tables (for example rigidity resolution against rigidity) are published as **simulated dataset-records**, written by `geant4_run.py table` (with `trace.provenance()`).
- Today `dependencies.py` requires every input of a simulated table to be a computational-run with `extension.simulation` or `extension.study`, and the reconstruction record has neither; listing only the raw run records would leave the step that changes the numbers out of the input chain. So C2 adds a marker (for example `extension.derived_from_simulation`) that accepts a computational-run whose inputs are all simulation runs as input of a simulated table (needs hep-computing's agreement, §12).
- J15's study record is `unvalidated`, so the tables stay `unvalidated`; a communication that uses them gets the `communication.simulated_source` warning, and figures are labelled "Simulation".

### B1.5 Labels and contracts C2

- The contracts benchmark table (A1.1) gains J15's checks with grade `verification` or `sanity`; only reference is counted by `_study_upgrade`.
- The isolation rule is already in force from task A's C1 (A1.3); every J15 benchmark is `embedded` and is not counted.
- C2 also holds the marker of B1.4.
- **What J15 is:** a vehicle for verification. Every result in the full detector is `unvalidated`, as the README and the study record state.
- `GRADES` in `geant4_benchmarks.py` and the study-spec grade enum gain `verification`.

---

## 6. Validation work items

### B2.1 Validation ladder

| Check | Grade | Reference | Rule | Negative control |
|---|---|---|---|---|
| overlaps | implementation | — | — | shift one Si plane into an overlap |
| per-event energy balance (J15 geometry) | implementation | energy conservation | — | drop 2 mₑc², double counting |
| material budget (geantino) | implementation | sum of PDG X₀ | tolerance about 2 % (Geant4's X₀ formula and PDG differ by about 1 %); catches geometry and material errors | Pb density ± δ |
| `field-propagation` | **verification** | charged geantino against the analytic helix (tests the numerical integration) | see B2.2 | Geant4-side B × (1 ± δ) |
| `field-propagation-muon` | **sanity** | plane-averaged true 1/R (B1.3) | μ⁻ at 1, 10, 100 GV; tolerance = t·SE + 0.05 %; N ≈ 400 (1 GV), ≈ 7400 (100 GV) | Geant4-side B × (1 ± 1 %) |
| fitter unit test | test (not a benchmark) | toy truth (R ≥ 300 GV): `simreco`'s C++ fit against the Python `tracker_resolution.py` (an independent implementation) | — | — |
| one-off scattering comparison | sanity | the analytic term of `multiple_scattering.py` (no log, by its convention); optionally `toy_spectrometer.py` (needs NumPy) | μ and p, 1–10 GV, with β | — |
| `tof-beta` | **verification** (bookkeeping) | kinematics along the true track | — | a scorer test flag injects a time offset; no Geant4-side physics control, stated in the documentation |
| `tof-layer-consistency` | **verification** (bookkeeping) | time difference of the two layers of a station against the inter-layer path length / βc (66.7 ps at β = 1 and normal incidence) | residual mean 0; width √2 σ_t (141 ps at 100 ps) | a test flag injects a time offset into one layer's scorer |
| `sampling-fraction` | sanity | ratio of ionization dE/dx at the run momentum from the PDG muon tables (Groom et al., through hep-citations) | μ⁻ at 1 GeV; statistic Σ PVT deposit / Σ (PVT + Pb) deposit; plausible range ±10 % (a reviewer's Bethe estimate is about 0.271); seeds different from the `calibration` sample | PVT density ± δ |
| shower containment | sanity | PDG gamma profile, mixture effective critical energy about 10.2 MeV | electrons 1–100 GeV | — |
| `longitudinal-profile` (0.21.0) | not applicable | its reference is the published ALICE FoCal-E measurement, valid only for that stack; J15's calorimeter differs and is embedded | — | — |
| optional: stopping power in an isolated PVT slab | reference (`configuration: isolated`) | Bethe (RPP 2024 eq. 34.5) | p at T = 200–600 MeV (βγ ≈ 0.67–1.37, below PVT's 10^x₀ ≈ 1.40, so the density correction is zero), 1 cm slab, nuclear interactions excluded (about 1 %); Sternheimer parameters must come from Sternheimer, Berger & Seltzer (1984), checked through hep-citations | PVT density ± δ |

The optional last item runs in an isolated slab, not as part of the J15 detector, to show the upgrade path for a new material. Event counts and decisions follow A1.5–A1.8.

### B2.2 Convergence scans

**Field accuracy and maximum step (deterministic, no statistics):**
- Tracks: charged geantino (mass 0, β = 1) at rigidities 0.6, 1, 10, 100 and 1000 GV.
- Directions: normal incidence; **50 mrad in the bending plane, opposite to the bend** (+y for positive charge); ±50 mrad in the non-bending plane.
- Checked in appendix A: with these directions every track reaches every Si plane and both TOF2 layers without leaving the field mother. With the bend instead, 0.6 GV and 1 GV miss Si6.
- Reference: the analytic helix; if a track leaves the field region, piecewise straight lines, comparing only the planes the analytic track actually reaches.

| Scan | Grid | Decision |
|---|---|---|
| delta intersection | 1e-3, 1e-4, 1e-5, 1e-6 mm | at the nominal value (1e-5) the in-plane distance √(Δy² + Δz²) ≤ 0.5 µm (ε/20) on every plane; the two finest settings differ by ≤ 0.2 µm; 1e-3 mm is expected to fail |
| maximum step | 100, 30, 10, 3 mm | same |
| delta one step and epsilon | nominal and 1/10 | no change expected; confirmed once |
| TOF2 path time (both layers) | — | \|Δt\| ≤ 1 ps (about 0.3 mm of path), checks only the path length |

**Calorimeter production cut:**
- Grid: 0.1, 0.3, 0.7, 1.0 mm.
- Sample: 10 GeV e⁻; a trial run first, then N per A1.7.
- Observables: total deposit (relative tolerance 1 %, about 400 showers per point) and rear leakage fraction (from the existing `leak_rear_MeV`, back face only; **absolute** tolerance 0.002, about 5000 showers per point).
- Events per point: the larger of the two.
- Decision per A1.5 (IUT gate).

The Si production cut is not part of J15's convergence: it affects only the Si deposit, and J15's Si results are not evidence. The study spec's `convergence_plan.observables` enum holds only the four thin-layer observables today; this task adds the total deposit and the rear leakage fraction. The parameter groups each benchmark depends on are declared in the study spec in advance and checked against the probe's actual settings.

### B2.3 Variations

| Variation | Scope | Rule |
|---|---|---|
| EM option4 against option3 | calorimeter profile, sampling fraction | `G4R-PRECISION-EM` |
| FTFP_BERT_EMZ against **QGSP_BIC_EMZ** | only the interaction probability and first-interaction depth in the calorimeter; nucleons below 1.5 GeV | `G4R-BIC-RANGE`; π below 3 GeV and hadrons at 6–12 GeV use the same models in both and must not be used as variations |
| vacuum against air | multiple scattering, rigidity resolution | — |

---

## 7. Recorded-data budget

- `check_packaging.py` limits each file to 2 MiB; J14's `recorded/` is 2,447,979 bytes (2.45 MB).
- ROOT files are not committed (binary). The run record keeps only their path, file sha256, `content_sha256`, the row count of each ntuple and the file size; ROOT files needed by tests are produced in live tests.
- J15's ROOT file (`crossings` level) takes at most about 4 kB per event before compression: `crossings` 10 rows × 80 B, `deposits` at most 110 rows × 28 B, `events` about 120 B; 10⁵ events are at most about 400 MB before compression.
- J15's per-event CSV has only summary columns; per-layer and crossing data are in the ROOT file.
- J15 commits only: summary-CSV replay files with reduced columns (as J14's `REDUCED`), reduced crossing and deposit records taken with `simroot dump --events` (for offline replay of `simreco`; the event subset is set by the budget), the digitization and reconstruction outputs, the probe output and the column map.
- Acceptance: every file ≤ 2 MiB; J15's `recorded/` ≤ 3 MB in total.

---

## 8. Contracts and versions

| Object | Location | Version |
|---|---|---|
| the table gains `verification` and J15's checks; the marker for reconstruction records as input of simulated tables | `contracts/validate.py`, `contracts/dependencies.py` | C2 (minor, gated) |
| `field` block, `ekin_per_nucleon_MeV`, `layered_sim.events/2` (`crossings`), new column-map columns | adapter | adapter 0.3.0 |
| `simreco` | adapter (C++, `simcore`) | adapter 0.3.0 |
| `GRADES` and the study-spec grade enum gain `verification`; `convergence_plan.observables` gains the total deposit and rear leakage fraction | hep-detector | with the plugin version |

C2 is gated like C1: `strict or _at_least(contract_version, C2)`, with no warning branch.

---

## 9. Registration and documentation

| Item | Content |
|---|---|
| Script count | no new hep-detector script (reconstruction in `simreco`, interface in the adapter); `DetectorScriptCount` stays 21; line 47 of `docs/capability-matrix.md` unchanged |
| CLI registration | `geant4_run.py reco` and `table` registered in `tests/skills/test_cli_robustness.py` and the adapter tests; `simcore`'s sources listed in `assets` of `adapter.json` |
| Routing table | `skills/hep-detector/SKILL.md` unchanged, quick load unchanged; J15 and `simreco` documented in `geant4-study-protocol.md` and the adapter documentation |
| Journey | J15; `docs/researcher-journeys.md`, the example table in `docs/maintenance.md`; `tests/examples/test_geant4_minimal_spectrometer.py` (replay and compare with the committed outputs) |
| Capability | `docs/capability-map` (a new entry under `full-detector-simulation`, then `capability_map.py --write`), `docs/capability-matrix.md` |
| Routing | a new routing case for J15; `check_routing_static.py` reads the journey list from `docs/researcher-journeys.md`, so once J15 is listed a routing case is **required**. Rerun the live Geant4 cases, including the existing Traditional Chinese under-specified case `g4-underspec-2` |
| Description length | hep-detector's description is at 1,018 / 1,024 characters (`measure_entrypoints.py` measures the folded description in full); J15's routing case uses trigger words already in the description, which is not changed |
| Experiment names | none in `skills/` or `contracts/`; the `longitudinal-profile` reference is cited by citation key |
| Independent review | this task's Markdown (protocol changes, the J15 README, this document) reviewed with 0.22.0's `review.py` (`--lens-model design=<strongest model>`, `--filter-model`); the record is advisory only and, per O04/O14, does not replace the human G5 confirmation |
| Shared stanza | text unchanged |
| Other | `reference_inventory.py --check`, CHANGELOG, release manifest, adapter 0.3.0, `SIM_SOURCES` gains `FieldSetup.*`, `SIMCORE_SOURCES` gains `simreco`'s sources |

---

## 10. Acceptance

- [ ] The J15 geometry passes overlaps, material budget and per-event energy balance; the checked numbers of §4.1 and §4.2 are recomputed by tests.
- [ ] The MT test command reports distinct field-manager pointers per thread; the field parameters recorded by the probe match the spec.
- [ ] The deterministic field checks of B2.2 pass at the nominal settings; delta intersection 1e-3 mm fails as expected.
- [ ] `field-propagation`, `field-propagation-muon`, `tof-beta`, `tof-layer-consistency` and `sampling-fraction` run; each negative control is caught per B2.1, or the absence of a control is stated.
- [ ] `simroot`'s round-trip and content-hash tests pass at the `crossings` level; two MT runs with the same seed and different thread counts give the same `content_sha256`.
- [ ] `simreco`'s fitter unit test passes against the Python `tracker_resolution.py`; `simreco` is built and tested in the `simcore` CI job.
- [ ] Contract tests of the isolation rule: a missing configuration, `embedded`, and a grade that disagrees with the contracts table are all refused; J14 still passes under `--strict`.
- [ ] C2: the `verification` grade is not counted for upgrades; `dependencies.py` accepts a reconstruction record as input of a simulated table through the marker of B1.4; J15's tables stay `unvalidated`.
- [ ] Recorded-data budget, registrations and documentation complete; VALIDATION entry GEANT4-J15.
- [ ] An independent agent, using only the documentation and tools, completes "rigidity resolution of 1 GV protons in J15": the result record passes `validate.py --strict`, carries `unvalidated`, and the resolution lies within the ranges of the table in §4.2, with no help from the maintainer.

---

## 11. Not done and deferred

| Item | Decision | Reason / trigger |
|---|---|---|
| σ(1/R) in the measurement-dominated regime as a benchmark | not done | a fitter unit test instead |
| ion source and Birks visible energy (future J16) | deferred | trigger: a cosmic-ray nuclei study and a literature record for PVT's Birks constant. Per 11.4.3: get the ion with `GetIon(Z, A)` in `GeneratePrimaries`; set kB in `Construct`, `SetBirksActive(true)` in PreInit, then obtain it with `G4LossTableManager::Instance()->EmSaturation()` |
| GDML, field maps, fringe fields | deferred | trigger: a study that needs real geometry or field shape |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | not done | replaced by the C++ `simreco`, with `geant4_run.py reco` and `table` as interface |

Other items not done or deferred (including `physics_config_comparison`, RNTuple and Python bindings) are in task A §11.

---

## 12. Decisions for the maintainer and residual risks

**To decide:**
1. The C2 "derived simulation" marker (`extension.derived_from_simulation`, B1.4): hep-computing, the owner of the computational-run schema, must agree.
2. The version class of C2: minor, following the convention of gates at x.y.0.

**Residual risks:**
1. The sampling-fraction reference needs the PDG muon energy-loss tables; the optional PVT benchmark needs Sternheimer parameters. Both must come through hep-citations literature records before use.
2. Calorimeter showers dominate the CPU time; rear-leakage convergence needs about 5000 showers per point, and the event count is set by a trial run and recorded.
3. The field region and plane crossings change the `sources_sha256` of later live J14 reruns; this is expected, and the committed J14 records are not re-recorded.
4. Only 931 bytes of quick-load budget remain and the description is at 1,018 / 1,024 characters: this task must not change `skills/hep-detector/SKILL.md` or the description (§9).
5. Effort is not yet estimated; estimate it from the actual `simcore` and `simroot` once task A is complete.
6. Task A's residual risks (the probe assumes workers match the master, the reading ability of `G4RootAnalysisReader`, disk and memory use of ROOT files) apply as well; see task A §12.

---

## 13. Suggested order of work

1. The checks before starting (§0); confirm that every interface of §2 exists.
2. B1.1: field (`FieldSetup.*`, lifting the `field` rejection, step limiter, probe) and the MT test; then the deterministic field checks of B2.2 (no statistics, so they can be verified first).
3. Build J15's spec/2 geometry (§4.1); pass overlaps, material budget and energy balance, and recompute the checked numbers of §4.1 and §4.2 in tests.
4. B1.2: plane-crossing scorer and the `crossings` level; add `crossings` to the `simroot` tests.
5. B1.3: `simreco` and `geant4_run.py reco`, fitter unit tests first, then the input from `simroot dump`.
6. B1.4, B1.5: `geant4_run.py table`, the C2 contract change and tests, `GRADES` and the enums.
7. B2.1, B2.2 (calorimeter cut), B2.3: run the benchmarks, convergence scans and variations on E2.
8. The recorded data of §7, the registrations and documentation of §9, the independent-agent acceptance question; tick every box of §10 and run the checks of task A §10.

---

## Appendix A: numbers

Script: `j15_design_estimates.py` (this folder; standard library, scipy optional; A_N checked against the closed form by an exact rational least-squares computation). The attainment probabilities and t quantiles are in task A, appendix A.

**Geometry**
- Si centres: −500, −340, −180, −20, 140, 300 mm; L = 0.800 m.
- Field region: −520 … 320 mm; 19.85 mm margins at both ends.
- TOF1 layers −810 … −800 and −790 … −780; TOF2 layers 490 … 500 and 510 … 520; station-centre distance D = 1.300 m; world ±1200 mm.

**Tracking**
- A_N = 720 (N−1)³ / [(N−2) N (N+1)(N+2)]: A₄ = 81.0, A₆ = 66.96, A₈ = 57.17 (N equally spaced points including both ends, equal weights).
- MDR (measurement term only) = C B L² / (ε √A_N): 1172 GV at C = 0.2998 (1173 GV at C = 0.3).
- Scattering term (β = 1, with the log): 1.34 %, bracketed by a factor of 1.0–1.4.

| B (T) | N | MDR (GV) | Scattering term (β = 1) | Rigidity where the terms are equal |
|---|---|---|---|---|
| 0.15 | 6 | 352 | 4.5–6.2 % | 16–22 GV |
| **0.5** | **6** | **1172** | **1.3–1.9 %** | **16–22 GV** |
| 1.0 | 6 | 2345 | 0.7–0.9 % | 16–22 GV |
| 0.5 | 4 | 1066 | 1.1–1.5 % | 11–16 GV |
| 0.5 | 8 | 1269 | 1.6–2.2 % | 20–28 GV |

**Field-check grid** (50 mrad opposite to the bend, positive charge):

| Rigidity | Max \|y\| in the field | y at Si1 … Si6 (mm) | y at the two TOF2 layers |
|---|---|---|---|
| 0.6 GV | 29.0 | 25.0, 29.0, 26.6, 17.8, 2.5, −19.3 | −50.0, −53.2 |
| 1 GV | 32.4 | 25.0, 30.6, 32.4, 30.3, 24.4, 14.6 | 0.2, −1.4 |
| 10 GV | 60.7 | 25.0 … 60.0 | 67.1, 67.9 |
| 1000 GV | 66.0 | 25.0 … 65.0 | 74.5, 75.5 |

With the bend instead (−50 mrad): 0.6 GV is at y = −151 mm at Si6 and 1 GV at −116 mm; both miss Si6.

**TOF**: with two independent layers per station, σ_station = σ_layer / √2 and σβ/β = √2 σ_station c / D = σ_layer c / D; 1.8 %, 2.3 % and 3.5 % for 80, 100 and 150 ps per layer (2.6 %, 3.3 % and 4.9 % with one layer per station). The flight time between the two layers of a station is 66.7 ps at β = 1, and the layer-pair time difference has resolution √2 σ_layer (141 ps at 100 ps).

**Calorimeter**: 18.41 X₀, 0.886 λ_I, 35 cm; effective Molière radius 3.95 cm; the minimum-ionization loss ratio 0.284 is only a ratio of dE/dx_min, **not** a reference value.

**Material in front of the calorimeter**: 11.32 % X₀ (four TOF layers 9.40 %, i.e. 83 %; Si 1.92 %), 5.46 % λ_I; TOF1, upstream of the tracker, holds 4.70 % X₀.

**Event counts** (se of the difference ≤ tol/4): total deposit of 10 GeV electrons (tolerance 1 %) about 392; rear leakage (absolute tolerance 0.002) about 5000.

---

## Appendix B: sources

- PDG Atomic and Nuclear Properties (retrieved 2026-10-21): [Silicon](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/silicon_Si.html), [Lead](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/lead_Pb.html), [Polyvinyltoluene](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/polyvinyltoluene.html)
- PDG Review of Particle Physics 2024, chapter 34: eqs. 34.5, 34.12, 34.16, 34.34–34.36 (equation numbers as in the plugin's VALIDATION GEANT4-STUDY)
- Geant4 v11.4.3 source (tag `v11.4.3`), field-related: `G4FieldManager.hh`, `G4ChordFinder.hh`, `G4PropagatorInField.cc`, `G4FieldBuilder`, `G4FieldParameters`, `G4LogicalVolume`, `G4ChargedGeantino.cc`, `G4EmSaturation`, `G4LossTableManager`, `G4IonTable`, `G4NistMaterialBuilder.cc`; the full list is in task A appendix C
- Geant4 Book for Application Developers, [Basic Examples](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html) (B4, B5; development documentation)
- hep-research: `skills/hep-detector/scripts/tracker_resolution.py`, `multiple_scattering.py`, `toy_spectrometer.py`
- Still to obtain: the PDG muon energy-loss tables (Groom, Mokhov & Striganov); Sternheimer, Berger & Seltzer (1984), *Atomic Data and Nuclear Data Tables* 30, 261

---

## Appendix C: version history

The full history before the split is in task A, appendix D.

| Version | Main content | Reviews and main corrections |
|---|---|---|
| detector note | single-axis stacked magnetic spectrometer | Gluckstern small-N formula corrected |
| v5 | field direction, field-check grid | two reviews (see task A, appendix D) |
| J15 revision (2026-10-22) | TOF1 and TOF2 become two layers each, all four of the same material; TOF resolution, upstream energy loss, material budget, acceptance and the field-check grid recomputed; new `tof-layer-consistency` | numbers recomputed with `j15_design_estimates.py` |
| language split (2026-10-22) | digitization and reconstruction move to the C++ `simreco`; no new hep-detector script | user decision |
| per-event ROOT files (2026-10-22) | J15's crossings and per-layer deposits go to the ROOT file; summary CSV | user decision |
| task split (2026-10-22) | split out of the original proposal as task B, done after task A; the `crossings` level defined in this task | user decision |
| **Restructured as an implementation spec (2026-10-22)** | **task card, glossary, prerequisite interfaces, hard rules, numbered work items (B1.x, B2.x), contracts and versions, suggested order of work; sections renumbered; no content removed** | user request |
