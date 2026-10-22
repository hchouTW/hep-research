# hep-research Geant4 study architecture, task B: J15 minimal spectrometer

> Status: proposal, awaiting the maintainer's approval; **starts only after task A is complete and merged**
> Prerequisite: phase 1 (contracts C1) and phase 2 (adapter 0.2.0: spec/2, probe, column map, `simcore`, `simroot`, per-event ROOT files) of task A ([`task-a-core.en.md`](task-a-core.en.md)) are both merged
> Baseline: when written, the same as task A (hep-research `main` at `9f08796`, contracts 3.5.0, Geant4 11.4.3); before starting, re-check with the method of task A's section 13 and update this document
> Contract versions: **C2** = the next unused minor when task B is merged (after task A's C1)
> Section references: "A4.5" means section 4.5 of the task A document; "B8" or "section 8" means section 8 of this document
> Origin: this document is section 6 (phase 3) of the original proposal plus the J15-only parts of its other sections (split on 2026-10-22), with nothing left out
> Language: English translation of [`task-b-j15.md`](task-b-j15.md) (Traditional Chinese original); the two have the same content
> Example: the J15 minimal spectrometer is a **synthetic geometry**, a vehicle for verification, not the detector of any experiment

---

## 0. Summary

Task B demonstrates a magnetic field, several subsystems and a reconstruction chain with a minimal spectrometer (J15): a field region, a plane-crossing scorer, digitization and reconstruction in `simreco`, the `verification` grade, and reconstruction records as inputs of simulated tables.

| Content | Version | J14 |
|---|---|---|
| J15 minimal spectrometer: field region, plane-crossing scorer and the `crossings` level of the ROOT file, digitization and reconstruction in `simcore`'s `simreco` (mixtures already exist in 0.21.0); `verification` grade; a reconstruction record as input of simulated tables | **adapter 0.3.0**, **contracts C2** (minor) | not re-recorded |

**The four most important decisions:**

1. **The validation grade follows the nature of the reference.** A reference that is an exact consequence of the
   inputs gives verification; only a reference that is a physics model Geant4 approximates can give validation (task A's principle 9).
2. **Field accuracy is checked deterministically.** A charged geantino is compared with the analytic helix; no
   statistics are needed (section 8).
3. **J15 is a vehicle for verification.** Every result in the full detector is `unvalidated`; only the optional benchmark run in an isolated slab shows the upgrade path for a new material (sections 7 and 10).
4. **No new hep-detector script.** Reconstruction is in the C++ `simreco`, with the interface in the adapter; quick load and description are unchanged (section 12).

---

## 1. Prerequisites and the interface with task A

| Task A provides | Task B uses it for |
|---|---|
| C1: benchmark table, scope compares kind, configuration and the isolation rule (A4.1–A4.3) | every J15 benchmark is `embedded` and not counted for upgrades; C2 adds `verification` to the table (section 10) |
| statistical rules: IUT gate, two-stage event count, seeds `H(study_id, role, point_id, k)`, sub-runs (A4.5) | event counts and decisions of the convergence scans and benchmarks (sections 7 and 8) |
| the `field` block reserved in spec/2 (A5.2); adapter 0.2.0 rejects a non-empty `field` | implements `field` (section 4) and lifts the rejection |
| when `G4StepLimiterPhysics` is added (A5.3) | also when a field is present; this changes the `sources_sha256` of later live J14 reruns (expected; the committed J14 records are not re-recorded) |
| the spec/2 gun field `energy_MeV` (A5.4) | adds `ekin_per_nucleon_MeV` |
| probe and column map `layered_sim.output/2` (A5.6) | the probe also records the field parameters (section 4); the column map gains the `crossings` columns |
| `simcore` (A5.8) and its required CI job | the new executable `simreco` (section 6), built and tested in the same CI job |
| per-event ROOT files and `simroot` (A5.9) | adds the `crossings` level and ntuple (section 5); `simreco` reads through `simroot dump` |

Task B does not change task A's interfaces. If implementation shows that a change is needed, it is first made within task A's scope as an adapter patch release, and task B then continues.

---

## 2. Geometry

Coordinates: centred on the world, stack axis x, in mm.

**Magnetic field: B = (0, 0, +0.5 T).** The bending plane is x–y; the non-bending direction is z. A positive charge
moving along +x bends toward −y; a μ⁻ bends toward +y.

```
x:  −1000   −810 … −780   −520 −500        …         300  320    490 … 520   550           900   ±1200
     gun    TOF1 (2 layers) │ Si1  Si2  Si3  Si4  Si5  Si6  │     TOF2 (2 layers) calorimeter    world edge
            10 + 10 mm      │◄──── uniform field 0.5 T ẑ (−520 … 320) ────►│  10 + 10 mm  50 × Pb 2 / PVT 5 mm
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

**TOF stations.** TOF1 and TOF2 each have two layers; all four layers are the same material (`G4_PLASTIC_SC_VINYLTOLUENE`) and thickness (10 mm), with a 10 mm vacuum gap between the two layers of a station. Each layer is a whole slab, unsegmented and with no paddle direction (a deliberate simplification); the two layers give two independent time measurements and dE/dx samples, and their agreement within a station is a check (section 7).

Checks (the script in Appendix A):
- Lever arm L = 0.800 m; the front of Si1 and the back of Si6 are 19.85 mm from the mother's faces.
- The field extends 20 mm beyond the measured region at each end.
- The distance between the TOF station centres (midpoints of the two layers: −795 and 505 mm) is D = 1.300 m, as in the single-layer design.
- The back face of TOF2's second layer (520) is 30 mm from the calorimeter front (550); TOF1's first layer (−810) is downstream of the gun (−1000).
- The world contains the gun and the back of the calorimeter.

Materials (11.4.3 NIST definitions against PDG): `G4_PLASTIC_SC_VINYLTOLUENE` is 1.032 g/cm³ with I = 64.7 eV, as in
PDG; `G4_Si` is 2.33 g/cm³ (PDG 2.329).

---

## 3. Parameters and acceptance

| Parameter | Value | Reason |
|---|---|---|
| B | 0.5 T | The rigidity where the scattering and measurement terms are equal is about 16–22 GV (μ), independent of B. 0.5 T gives one decade each in 1–10 GV and 100–1000 GV |
| Si layers | 6 | N = 4 leaves one degree of freedom in the bending plane; N = 8 improves the MDR by only about 8 % |
| MDR | about 1172 GV | σ_R/R = 1 from the measurement term alone. The reference is the exact least-squares fit of `tracker_resolution.py` (constant 0.2998). `mdr_intrinsic_only_gv` of `multiple_scattering.py` has the same definition but is still computed with the Gluckstern approximation (about 1131 GV at N = 6); since 0.21.0 it also reports `intrinsic_coefficient` (including the exact coefficient used here) and warns below N = 10 |
| TOF | two layers per station; σβ/β ≈ 2.3 % (100 ps per layer, independent layers, β = 1; 3.3 % with one layer per station) | D = 1.3 m; the station time is the mean of its two layers, σ_station = σ_layer / √2 |
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
| Reaches TOF2's first layer (x = 490, \|y\| ≤ 200 mm) | 0.385 GV |
| Crosses both TOF2 layers (x = 520, \|y\| ≤ 200 mm) | 0.404 GV |
| Calorimeter front, shower axis within 250 − 2 R_M,eff | 0.490 GV |
| Calorimeter back, same | 0.745 GV |

The overall threshold is 0.75 GV; 0.51 GV if only tracking and TOF are required. Below 0.364 GV a track leaves the
side of the field region and continues straight in the field-free world.

Electrons: the shower axis is 82 mm and 127 mm off axis at the calorimeter front and back at 1 GeV, 16 mm and 25 mm at
5 GeV. Bremsstrahlung photons from the 11.3 % X₀ upstream (83 % of it in the four TOF layers) are not bent, so the shower axis is not the straight-line extrapolation; the 79 mm margin is a geometric estimate, and with twice the upstream material of the single-layer design the shower checks must confirm it with the actual transverse energy distribution. Electron shower checks start at 1 GeV.

**Upstream energy loss** (integrated Bethe, TOF1's two layers, 2 cm PVT in total):

| Proton rigidity | Kinetic energy | TOF1 loss (two layers) | Δp/p | Change of β between the TOF station centres |
|---|---|---|---|---|
| 0.6 GV | 175 MeV | 10.23 MeV | 3.20 % | 2.87 % |
| 1 GV | 433 MeV | 6.00 MeV | 0.82 % | 0.46 % |
| 2 GV | 1271 MeV | 4.34 MeV | 0.24 % | 0.05 % |

At 0.6 GV, β changes by 2.87 % between the stations, more than the TOF resolution (2.3 %): TOF measures the mean β along the path, so β comparisons at low rigidity need a β model with energy loss, or are restricted to 2 GV and above. TOF1 is upstream of the first Si plane and changes only the incoming direction and momentum, not the curvature resolution; the true rigidity comes from the Si plane crossings and is not affected by the thicker TOF1.

**J14 cannot be reused.** J15's Si planes differ from J14 in material (`G4_Si` against `Si_study`), physics settings
and cuts, and J15 records only the entry point, so J14's observable E_in − E_exit cannot be formed.

---

## 4. Field implementation

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

---

## 5. Other new features

| Feature | Rule |
|---|---|
| Mixtures | already supported in 0.21.0 (`materials[].components`); nothing to add for J15, where PVT and Pb are NIST materials |
| Plane-crossing scorer | on the primary's (track ID 1) **first** entry into a tracker or TOF plane (pre-step status `fGeomBoundary` and the volume is the plane), record the pre-step position, direction, kinetic energy, global time and PDG code; one "recorded" flag per plane. A gun inside a plane never shows `fGeomBoundary`; that plane gets no row |
| Output | per-event ROOT file (A5.9; the `crossings` level below): event truth, crossing records for 10 planes (6 Si, 4 TOF layers), per-volume deposits (calorimeter layers included); the per-event CSV keeps only summary columns (primary truth, total deposit per subsystem); the column map describes both and is generated automatically |

**The `crossings` level of the ROOT file.** `output.event_file.level` gains `crossings` (which includes every ntuple of `summary`), `event_file_version` is incremented, and the ntuple layout becomes `layered_sim.events/2` (additions only; no existing ntuple changes):

| Ntuple | Level | One row per | Columns |
|---|---|---|---|
| `crossings` | from `crossings` (also in `hits`) | event × crossed plane | `event_id`, `plane_id`, `track_id`, PDG code, pre-step position, direction, kinetic energy, global time (the plane-crossing scorer above); planes not crossed get no row |

`simroot`'s round-trip and content-hash tests gain the `crossings` level (section 13).

**Deliberate simplifications:** uniform field with sharp edges, no magnet material, silicon as whole planes (no
strips, no charge sharing, no δ-ray centroid shifts), unsegmented TOF layers (no paddles, no direction), no optical photons, no trigger or readout
electronics. The J15 README lists each one.

---

## 6. Digitization and reconstruction

Digitization and reconstruction run in the C++ `simreco`, called by the Python interface `geant4_run.py reco`; the parameters (ε, σ_t, nominal B, calibration sample) are in a reco spec owned by hep-detector. hep-detector gets no new script. The inputs are `crossings` and `deposits` taken from the ROOT file by `simroot dump` (sorted by key) and the summary CSV.

| Step | Content |
|---|---|
| Silicon | Gaussian smearing of the crossing points: ε = 10 µm in the bending direction (y), 30 µm in the non-bending direction (z); the fit uses the same x as the scorer (the entry face) |
| TOF | independent Gaussian time smearing σ_t = 100 ps per layer; station time = mean of the two layers (each first moved to the station centre along the fitted track); the per-layer dE/dx and the time difference of the two layers of a station are also reported |
| Track | circle fit in x–y with a multiple-scattering covariance (without it χ²/dof is in the thousands at 1 GV); straight-line fit in x–z; outputs R, χ², degrees of freedom; nominal B |
| True rigidity | the mean of C·B / p_T,i over the six plane-crossing records (C = 0.2998), with the transverse momentum |
| β | path length between the station centres, including the straight segments TOF1→Si1 and Si6→TOF2 and the 3D dip angle; at low β, the change of β between the stations is reported |
| Calorimeter | total active deposit divided by the **electron** sampling fraction, obtained from a 10 GeV electron sample with the `calibration` role; e/mip is also reported |
| Random numbers | counter hash, separate from Geant4's stream |

Each execution of `geant4_run.py reco` writes a computational-run record (with `**trace.provenance()` and `simreco`'s program hash) whose inputs are the adapter's run records (with hashes and the ROOT file's `content_sha256`). Changing digitization parameters does not require rerunning the simulation. The exit codes of `simreco` and `geant4_run.py reco` follow `core/status.py`: 0 ok, 1 a negative verdict, 2 `rejected` (unreadable input, a missing file included), 3 incomplete; `reco` is registered in `MISSING_FILE_ARGS` of `tests/skills/test_cli_robustness.py`.

Reconstructed result tables (for example rigidity resolution against rigidity) are published as **simulated dataset-records**, written by `geant4_run.py table` (with `trace.provenance()`). Today `dependencies.py` requires every input of a simulated table to be a computational-run with `extension.simulation` or `extension.study`, and the reconstruction record has neither; listing only the raw run records would leave the step that changes the numbers out of the input chain. So C2 adds a marker (for example `extension.derived_from_simulation`) that accepts a computational-run whose inputs are all simulation runs as input of a simulated table. J15's study record is `unvalidated`, so the tables stay `unvalidated`; a communication that uses them gets the
`communication.simulated_source` warning, and figures are labelled "Simulation".

---

## 7. Validation ladder

| Check | Grade | Reference | Specification | Negative control |
|---|---|---|---|---|
| overlap | implementation | — | — | shift one Si plane to create an overlap |
| per-event energy balance (J15 geometry) | implementation | energy conservation | — | omit 2 mₑc²; double counting |
| material budget (geantino) | implementation | sum of PDG X₀ | tolerance about 2 % (Geant4's X₀ formula differs from PDG by about 1 %); catches geometry and material-assignment errors | Pb density ± δ |
| `field-propagation` | **verification** | charged geantino against the analytic helix (tests the numerical integration) | see section 8 | Geant4-side B × (1 ± δ) |
| `field-propagation-muon` | **sanity** | plane-averaged true 1/R (section 6) | μ⁻ at 1, 10, 100 GV; tolerance = t·SE + 0.05 %; N ≈ 400 (1 GV), ≈ 7400 (100 GV) | Geant4-side B × (1 ± 1 %) |
| fitter unit test | test (not a benchmark) | toy truth (R ≥ 300 GV): `simreco`'s C++ fit against the Python `tracker_resolution.py` (an independent implementation) | — | — |
| one-off scattering comparison | sanity | the analytic term of `multiple_scattering.py` (no log, by its convention); optionally `toy_spectrometer.py` (needs NumPy) | μ and p, 1–10 GV, with β | — |
| `tof-beta` | **verification** (bookkeeping) | kinematics along the true track | — | a scorer test flag injects a time offset; there is no Geant4-side physical control, and the documentation says so |
| `tof-layer-consistency` | **verification** (bookkeeping) | time difference of the two layers of a station against the inter-layer path length / βc (66.7 ps at β = 1 and normal incidence) | residual mean 0; width √2 σ_t (141 ps at 100 ps) | a test flag injects a time offset into one layer's scorer |
| `sampling-fraction` | sanity | ratio of ionization dE/dx from the PDG muon energy-loss tables (Groom et al., obtained through hep-citations) at the run momentum | μ⁻ at 1 GeV; statistic Σ PVT deposit / Σ (PVT + Pb) deposit; plausibility band ±10 % (a reviewer's Bethe estimate is about 0.271); seeds distinct from the `calibration` sample | PVT density ± δ |
| shower containment | sanity | PDG gamma profile with the mixture's effective critical energy of about 10.2 MeV | electrons 1–100 GeV | — |
| `longitudinal-profile` (0.21.0) | not applicable | its reference is the published ALICE FoCal-E measurement and holds only for that stack; J15's calorimeter differs and is embedded | — | — |
| optional: stopping power in an isolated PVT slab | reference (`configuration: isolated`) | Bethe (RPP 2024 eq. 34.5) | p at T = 200–600 MeV (βγ ≈ 0.67–1.37, below PVT's 10^x₀ ≈ 1.40, so the density correction is zero), 1 cm slab, nuclear interactions excluded (about 1 %); Sternheimer parameters must come from Sternheimer, Berger & Seltzer (1984), checked through hep-citations | PVT density ± δ |

The optional last item runs in an isolated slab, not as part of the J15 detector, and shows the upgrade path for a new
material.

---

## 8. Convergence scans

**Field accuracy and maximum step (deterministic, no statistics):**
- Tracks: charged geantinos (massless, β = 1) at 0.6, 1, 10, 100 and 1000 GV.
- Directions: normal incidence; **50 mrad in the bending plane, opposite to the bend** (+y for a positive charge);
  ±50 mrad in the non-bending plane.
- Checked in Appendix A: with these directions every track reaches every Si plane and both TOF2 layers and stays inside the field
  mother. With the bend instead, 0.6 GV and 1 GV miss Si6.
- Reference: the analytic helix; if a track leaves the field region, the reference becomes piecewise straight and only
  the planes the analytic track reaches are compared.

| Scan | Grid | Criterion |
|---|---|---|
| delta intersection | 1e-3, 1e-4, 1e-5, 1e-6 mm | at the nominal value (1e-5), in-plane distance √(Δy² + Δz²) ≤ 0.5 µm (ε/20) at every plane; the finest two settings differ by ≤ 0.2 µm; 1e-3 mm is expected to fail |
| maximum step | 100, 30, 10, 3 mm | same |
| delta one step and epsilon | nominal and 1/10 | no change expected; checked once |
| TOF2 path time (both layers) | — | \|Δt\| ≤ 1 ps (about 0.3 mm of path); tests the path length only |

**Calorimeter production cut:**
- Grid: 0.1, 0.3, 0.7, 1.0 mm.
- Sample: 10 GeV e⁻; a trial run first, then N per A4.5.
- Observables: total deposit (relative tolerance 1 %, about 400 showers per point) and the rear leakage fraction
  (from the existing `leak_rear_MeV`, rear face only; **absolute** tolerance 0.002, about 5000 showers per point).
- Events per point: the larger of the two.
- Decision per A4.5.

The Si production cut is not part of J15's convergence: it affects only the Si deposit, and J15's Si results are not evidence. The study spec's `convergence_plan.observables` enum holds only the four thin-layer observables today; task B adds the total deposit and the rear leakage fraction. The parameter groups each benchmark depends on are declared in the study spec in advance and checked
against the probe's effective settings.

---

## 9. Variations

| Variation | Scope | Rule |
|---|---|---|
| EM option4 against option3 | calorimeter profile, sampling fraction | `G4R-PRECISION-EM` |
| FTFP_BERT_EMZ against **QGSP_BIC_EMZ** | interaction probability and first-interaction depth in the calorimeter only; nucleons below 1.5 GeV | `G4R-BIC-RANGE`; π below 3 GeV and hadrons at 6–12 GeV use the same models in both, so they must not be used as a variation |
| vacuum against air | multiple scattering, rigidity resolution | — |

---

## 10. Labels and contracts C2

- The contracts benchmark table gains the J15 checks with grade `verification` or `sanity`; only reference
  benchmarks are counted by `_study_upgrade`.
- The isolation rule is already in force from task A's phase 1 (C1; A4.3); every J15 benchmark is `embedded` and is not counted.
- C2 also holds the marker that makes a reconstruction record an input of simulated tables (section 6).
- **J15's role:** a verification vehicle. Every result in the full detector is `unvalidated`; the README and the study
  record say so.
- `GRADES` in `geant4_benchmarks.py` and the study spec's grade enum gain `verification`.

---

## 11. Recorded-data budget

- `check_packaging.py` limits each file to 2 MiB; J14's `recorded/` is 2,447,979 bytes (2.45 MB).
- ROOT files are not committed (binary; sizes in A5.9). The run record keeps only their path, file sha256, `content_sha256`, the row count of each ntuple and the file size; ROOT files needed by tests are produced in live tests.
- J15's per-event CSV has only summary columns; per-layer and crossing data are in the ROOT file.
- J15's ROOT file (`crossings` level) takes at most about 4 kB per event before compression: `crossings` 10 rows × 80 B, `deposits` at most 110 rows × 28 B, `events` about 120 B; 10⁵ events are at most about 400 MB before compression.
- J15 commits only: summary-CSV replay files with reduced columns (as J14's `REDUCED`), reduced crossing and deposit records taken with `simroot dump --events` (for offline replay of `simreco`; the event subset is set by the budget), the digitization and reconstruction outputs, the probe output and the column map.
- Acceptance: every file ≤ 2 MiB; J15's `recorded/` ≤ 3 MB in total.

---

## 12. Registration and documentation

| Item | Content |
|---|---|
| Script count | hep-detector gets no new script (reconstruction in `simreco`, interface in the adapter); `DetectorScriptCount` stays 21 and line 47 of `docs/capability-matrix.md` is unchanged |
| CLI registration | `geant4_run.py reco` and `table` registered in `tests/skills/test_cli_robustness.py` and the adapter tests; `simcore`'s sources listed in the `assets` of `adapter.json` |
| Routing table | no change to `skills/hep-detector/SKILL.md` (no new script), so quick load is unchanged; J15 and `simcore` are described in `geant4-study-protocol.md` and the adapter documentation |
| Journey | J15; `docs/researcher-journeys.md`, the example table in `docs/maintenance.md`; `tests/examples/test_geant4_minimal_spectrometer.py` (replay compared with the committed outputs) |
| Capability | `docs/capability-map` (new items under `full-detector-simulation`, then `capability_map.py --write`), `docs/capability-matrix.md` |
| Routing | a J15 routing case; since 0.21.0 `check_routing_static.py` reads the journey list from `docs/researcher-journeys.md`, so once J15 is listed a routing case is **required**. Rerun the live Geant4 cases, including the existing Traditional Chinese under-specified case `g4-underspec-2` |
| Description length | the hep-detector description is at 1,018 / 1,024 characters (`measure_entrypoints.py` measures folded descriptions in full); the J15 routing case must reuse trigger terms already in it, with no change to the description |
| Experiment names | `check_layering.py` forbids experiment names (ALICE included) in `skills/` and `contracts/`; the contracts table and the protocol cite `longitudinal-profile`'s reference by citation key |
| Independent review | task B's Markdown (protocol changes, the J15 README, this document) is reviewed with 0.22.0's `review.py` (`--lens-model design=<strongest model>`, `--filter-model`); its record is advisory and, per O04/O14, does not replace the human G5 confirmation |
| Shared stanza | text **unchanged** (point 5 says "3.1.0 upgrade rule"; changing it touches every SKILL.md and requires a live routing rerun) |
| Other | `reference_inventory.py --check`, CHANGELOG, release manifest, adapter 0.3.0, `FieldSetup.*` in `SIM_SOURCES`, `simreco`'s sources in `SIMCORE_SOURCES` |

---

## 13. Acceptance

- [ ] The J15 geometry passes overlaps, material budget and per-event energy balance; the checked numbers in sections 2 and 3 are recomputed by tests.
- [ ] The MT test command reports distinct field-manager pointers per thread; the field parameters recorded by the
  probe match the spec.
- [ ] The deterministic field checks of section 8 pass at the nominal settings; delta intersection 1e-3 mm fails as
  expected.
- [ ] `field-propagation`, `field-propagation-muon`, `tof-beta`, `tof-layer-consistency` and `sampling-fraction` run; each negative control is
  caught per section 7, or the absence of a control is stated.
- [ ] `simroot`'s round-trip and content-hash tests pass at the `crossings` level; two MT runs with the same seed and different thread counts give the same `content_sha256`.
- [ ] `simreco`'s fitter unit test passes against the Python `tracker_resolution.py`; `simreco` is built and tested in the `simcore` CI job.
- [ ] Contract tests of the isolation rule: a missing configuration, `embedded`, and a grade that disagrees with the
  contracts table are all refused; J14 still passes under `--strict`.
- [ ] Recorded-data budget, registrations and documentation complete; VALIDATION entry GEANT4-J15.
- [ ] An independent agent, using only the documentation and tools, completes "rigidity resolution of 1 GV protons in
  J15": the result record passes `validate.py --strict`, carries `unvalidated`, and the resolution lies within the
  ranges of the table in section 3, with no help from the maintainer.

---

## 14. Dropped and deferred (J15 items)

| Item | Decision | Reason / trigger |
|---|---|---|
| σ(1/R) in the measurement-dominated regime as a benchmark | dropped | a fitter unit test instead |
| ion source and Birks visible energy (future J16) | deferred | trigger: a cosmic-ray nuclei study and a literature record for PVT's Birks constant. Per 11.4.3: get the ion with `GetIon(Z, A)` in `GeneratePrimaries`; set kB in `Construct`, `SetBirksActive(true)` in PreInit, then obtain it with `G4LossTableManager::Instance()->EmSaturation()` |
| GDML, field maps, fringe fields | deferred | trigger: a study that needs real geometry or field shape |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | dropped | replaced by the C++ `simreco`, with `geant4_run.py reco` and `table` as interface |

Other dropped and deferred items (including `physics_config_comparison`, RNTuple and Python bindings) are in A7.

---

## 15. Decisions for the maintainer and residual risks

**To decide:**
1. The C2 "derived simulation" marker (`extension.derived_from_simulation`, section 6): hep-computing, the owner of the computational-run schema, must agree.
2. The version class of C2: minor, following the convention of gates at x.y.0.

**Residual risks:**
1. The sampling-fraction reference needs the PDG muon energy-loss tables; the optional PVT benchmark needs Sternheimer
   parameters. Both must come through hep-citations literature records before use.
2. Calorimeter showers dominate the CPU time; rear-leakage convergence needs about 5000 showers per point, and the
   event count is set by a trial run and recorded.
3. The field region and plane crossings change the `sources_sha256` of later live J14 reruns; this is expected, and the committed J14 records are not re-recorded.
4. Only 931 bytes of quick-load budget remain and hep-detector's description is at 1,018 / 1,024 characters: task B must not change `skills/hep-detector/SKILL.md` or the description (section 12).
5. Effort is not yet estimated; estimate it from the actual `simcore` and `simroot` once task A is complete.
6. Task A's residual risks (the probe assumes workers match the master, the reading ability of `G4RootAnalysisReader`, disk and memory use of ROOT files) apply to J15 as well; see A11.

---

## Appendix A: numbers

Script: `j15_design_estimates.py` (in this folder; standard library, scipy optional; A_N checked against the closed
form by an exact rational least-squares computation).

**Geometry**
- Si centres: −500, −340, −180, −20, 140, 300 mm; L = 0.800 m.
- Field region: −520 … 320 mm; margins of 19.85 mm at both ends.
- TOF1 layers −810 … −800 and −790 … −780; TOF2 layers 490 … 500 and 510 … 520; station-centre distance D = 1.300 m; world ±1200 mm.

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

| Rigidity | Max \|y\| in the field | y at Si1 … Si6 (mm) | y at the two TOF2 layers |
|---|---|---|---|
| 0.6 GV | 29.0 | 25.0, 29.0, 26.6, 17.8, 2.5, −19.3 | −50.0, −53.2 |
| 1 GV | 32.4 | 25.0, 30.6, 32.4, 30.3, 24.4, 14.6 | 0.2, −1.4 |
| 10 GV | 60.7 | 25.0 … 60.0 | 67.1, 67.9 |
| 1000 GV | 66.0 | 25.0 … 65.0 | 74.5, 75.5 |

With the bend (−50 mrad): at 0.6 GV y = −151 mm at Si6, at 1 GV −116 mm; both miss Si6.

**TOF**: with two independent layers per station, σ_station = σ_layer / √2 and σβ/β = √2 σ_station c / D = σ_layer c / D; 1.8 %, 2.3 % and 3.5 % for 80, 100 and 150 ps per layer (2.6 %, 3.3 % and 4.9 % with one layer per station). The flight time between the two layers of a station is 66.7 ps at β = 1, and the layer-pair time difference has resolution √2 σ_layer (141 ps at 100 ps).

**Calorimeter**: 18.41 X₀, 0.886 λ_I, 35 cm; effective Molière radius 3.95 cm; the minimum-ionization loss ratio 0.284
is only a ratio of dE/dx_min, **not** a reference value.

**Material in front of the calorimeter**: 11.32 % X₀ (four TOF layers 9.40 %, i.e. 83 %; Si 1.92 %), 5.46 % λ_I; TOF1, upstream of the tracker, holds 4.70 % X₀.

**Statistics** (the attainment probabilities and t quantiles are in appendix A of task A)
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

The history before the split is in appendix C of task A.

| Version | Main content | Reviews and main corrections |
|---|---|---|
| detector note | single-axis stacked magnetic spectrometer | Gluckstern small-N formula corrected |
| v5 | field direction, field-check grid | two reviews (see task A, appendix C) |
| J15 revision (2026-10-22) | TOF1 and TOF2 become two layers each, all four of the same material; TOF resolution, upstream energy loss, material budget, acceptance and the field-check grid recomputed; new `tof-layer-consistency` | numbers recomputed with `j15_design_estimates.py` |
| language split (2026-10-22) | digitization and reconstruction move to the C++ `simreco`; no new hep-detector script | user decision |
| per-event ROOT files (2026-10-22) | J15's crossings and per-layer deposits go to the ROOT file; summary CSV | user decision |
| **Task split (2026-10-22)** | **split out of the original proposal as task B, done after task A; new section 1 (interface), sections 14 and 15; the definition of the ROOT file's `crossings` level moved to section 5** | user decision |
