# Geant4 Study Protocol

How to design, run, check and label a Geant4 study so that its result can be reviewed. The general methodology of
full simulation (geometry, physics lists, cuts, digitization, data/MC agreement) is in
[detector simulation](detector-simulation.md) and is not restated here; this file adds the study discipline and the
tools that enforce it.

**Versions.** Statements about Geant4 cite the upstream source at tag `v11.4.3` (commit
`2ee379e6843e55b9c6bbb835d2a2b03cc998fef0`), written `geant4:<path>`. No build of the Physics List Guide or the Book
for Application Developers matched to 11.4 was found (only development builds), so the source at the tag is the
authority here; a statement in a development guide may differ from what 11.4.3 does. For another Geant4 version, read
the same files at that version's tag before relying on any statement below. Formulas cite the Review of Particle
Physics 2024, chapter "Passage of particles through matter" (RPP 2024).

## 1. Verification is not validation

- **A run that completes** says only that the program ran. A simulation with an unsuitable physics list runs to the end
  without any error.
- **Agreement with the official examples** (B1, B4a, TestEm3, TestEm5; `geant4_examples.py`) and with a mirror of an
  example (`geant4_verify.py mirror`) is **verification**: the installation and the application reproduce Geant4's own
  numbers.
- **Validation** is agreement with an independent reference whose inputs do not come from Geant4, within a stated
  scope, by a benchmark whose negative control proved it can detect an error of the claimed size
  (`geant4_benchmarks.py`). It holds only in the range compared.

## 2. The study spec

Write the study as a spec (schema: [`../assets/geant4-study-spec.schema.json`](../assets/geant4-study-spec.schema.json);
synthetic example: [`../assets/geant4-study-spec.example.json`](../assets/geant4-study-spec.example.json)) before any
run. Its fields:

| Field | What it fixes |
|---|---|
| `observable` | name, kind (for example `most-probable-value`, `stopping-power`, `energy-deposit`), domain (`em` or `hadronic`), exact definition, unit, whether weights apply |
| `particle` | species and kinetic energy |
| `geometry_source`, `materials` | where the geometry and materials come from; for each reference material: density, its source, and `reference_origin` (`independent`, never the Geant4 material dump); Z/A, mean excitation energy I and the Sternheimer parameters when a benchmark uses them (stopping power, thin-layer MPV and width) |
| `physics` | the layered_sim spec, the order of UI commands, and a justification per choice with its source |
| `convergence_plan` | the cut or step-limit scan, the observables checked and their relative tolerances |
| `statistical_target` | the observable and the relative standard error required |
| `validation_plan` | the benchmarks and the declared scope (particle, energy range, material, thickness range, observable) |
| `variation_plan` | the model variations and whether their model assignment was checked |
| `downstream_use` | response matrix, comparison with published data, report; who receives it |

Ask the user for the observable, the particle and energy, the source of the geometry and materials, and the precision
target or downstream use when any is missing. Never choose an experiment or a detector for the user.

## 3. Physics settings: when to take care and what to read

The rule table [`../assets/geant4-physics-rules.json`](../assets/geant4-physics-rules.json) holds each item below as
a machine-checkable condition with its source and severity; `check_geant4_study.py spec` applies it and reports its
coverage. The items say when to look and where, not which list to use.

- **Low-energy neutrons** (below 20 MeV): the data-driven ParticleHP models and the G4NDL data (`G4NEUTRONHPDATA`)
  are only in the `_HP` lists (`geant4:source/physics_lists/constructors/hadron_inelastic/src/G4HadronPhysicsQGSP_BIC_HP.cc`,
  `SetMaxEnergy(20*CLHEP::MeV)`; `geant4:cmake/Modules/G4DatasetDefinitions.cmake`). Rule `G4R-HP-NEUTRON`.
- **Thin layers**: the energy-loss fluctuation model shapes the distribution. The standard EM constructors set Urban
  (`geant4:source/physics_lists/constructors/electromagnetic/src/G4EmStandardPhysics_option4.cc`,
  `SetFluctuationType(fUrbanFluctuation)`; the same call in `G4EmStandardPhysics.cc` and `_option3.cc`), while
  `G4EmParameters` itself defaults to the Universal model (`geant4:source/processes/electromagnetic/utils/src/G4EmParameters.cc`).
  PAI is requested per region with `/process/em/AddPAIRegion` (particle, region, `PAI` or `PAIphoton`;
  `geant4:source/processes/electromagnetic/utils/src/G4EmExtraParametersMessenger.cc`). Vary it. Rule `G4R-THIN-FLUCT`.
- **Production cuts in thin layers**: the official 20 um silicon run sets a 7 um cut
  (`geant4:examples/extended/electromagnetic/TestEm5/TestEm5.in`). Scan the cut. Rule `G4R-THIN-CUT-SCAN`.
- **EM constructor choice**: option 4 is described by its author as the best standard and low-energy models with the
  most advanced options for precise simulation at low and intermediate energies
  (`geant4:source/physics_lists/constructors/electromagnetic/include/G4EmStandardPhysics_option4.hh`). Justify the choice.
  Rule `G4R-PRECISION-EM`.
- **Hadronic model ranges**: QGSP_BIC uses the Binary cascade only for protons and neutrons up to 1.5 GeV
  (`geant4:source/physics_lists/constructors/hadron_inelastic/src/G4HadronPhysicsQGSP_BIC.cc`,
  `maxBIC_proton = maxBIC_neutron = 1.5 GeV`, Bertini from 1 GeV, otherwise as
  `geant4:source/physics_lists/constructors/hadron_inelastic/src/G4HadronPhysicsQGSP_BERT.cc`); the FTF-cascade
  transition is 3 to 6 GeV and the QGS-FTF transition 12 to 25 GeV
  (`geant4:source/processes/hadronic/util/src/G4HadronicParameters.cc`). Rule `G4R-BIC-RANGE`.
- **Stopping power**: the Bethe mean rate (RPP 2024 Eq. 34.5) is accurate to a few percent only for 0.1 <~ beta gamma
  <~ 1000. Rule `G4R-BETHE-RANGE`.
- **Datasets, UI timing, replicas, step limiters, biasing**: rules `G4R-DATASETS`, `G4R-UI-TIMING`,
  `G4R-REPLICA-OVERLAP`, `G4R-SPECIALCUTS`, `G4R-BIASED-BALANCE` (section 5).
- **Shower and leakage observables**: cut and EM constructor matter; leakage is energy leaving the world, so state
  which faces count (`observable.leakage_faces`: layered_sim splits it into `leak_rear_MeV`, `leak_front_MeV`, the
  albedo, and `leak_lateral_MeV`; an escaping e+ carries its 2 m_e c^2 as in
  `geant4:examples/extended/electromagnetic/TestEm3/src/TrackingAction.cc`). Rule `G4R-SHOWER`.
- **Written results**: name the literature record in `citations.literature_record` (the 11.4.3 run banner,
  `geant4:source/run/src/G4RunManagerKernel.cc`, lists the three papers to cite). Rule `G4R-CITATION`.

## 4. The convergence gate and the event count

- **Convergence (hard gate).** Scan the production cut (and the step limit when one is used). Between the two finest
  settings of each declared scan, every declared observable (mean deposit, tail fraction, most probable value) must
  change by no more than its relative tolerance, and the standard error of the change must be at most half of it.
  `check_geant4_study.py run` enforces this. It is the only check that catches a cut that is too coarse: no reference
  benchmark sees it, because the reference does not depend on the cut.
- **Event count.** Estimate it from a trial run. `check_geant4_study.py summarize` gives seeded-bootstrap standard
  errors, and `run` reports the events needed as N (SE/target)^2. The delta-ray tail makes means converge slowly: in
  the official TestEm5 run 0 (5 GeV pi+, 20 um Si, 1e5 events) the error on the primary's leakage is about 8 % of the
  mean energy loss. Do not take rms/sqrt(N) of a mean energy loss at face value.
- **Observables for the gate.** `summarize` computes the thin-layer set by default (mean deposit, most probable
  deposit and loss, tail fraction); for thick absorbers ask for what the study measures with `--observables`
  (`leakage_fraction`, `rear_leakage_fraction`, `albedo_fraction`, `lateral_leakage_fraction`) and `--slab all`.
  `geant4_run.py scan` gives every point its own seeds, so the SE of a difference is that of independent samples.

## 5. The validation ladder and verified pitfalls

Go up the ladder in order: implementation checks (`geant4_verify.py`: overlaps, material budget, energy balance,
mirror), then convergence, then independent-reference benchmarks.

- **Deposit is not energy loss.** In TestEm5 run 0 the mean deposit corresponds to 1.363 MeV cm2/g against a full
  dE/dx of 2.028 (`geant4:examples/extended/electromagnetic/TestEm5/TestEm5.out`): delta rays leave the layer.
  `stopping-power` uses E_in - E_exit of transmitted primaries, never the deposit.
- **Histogram means count in-range entries only.** B4a's printed means are over entries inside the histogram range,
  and its deposits can overflow (`geant4:examples/basic/B4/B4a/exampleB4a.out`). The benchmarks read per-event CSV
  values, never histogram summaries.
- **"+-" means different things.** B1 prints the standard deviation of the run total, which grows as sqrt(N)
  (`geant4:examples/basic/B1/src/RunAction.cc`); TestEm3 prints the single-event RMS, and its "+- x %" is the
  resolution over sqrt(N) (`geant4:examples/extended/electromagnetic/TestEm3/src/Run.cc`); TestEm5 prints the error on
  the mean (`geant4:examples/extended/electromagnetic/TestEm5/src/Run.cc`). Printed values are rounded at the
  precision each `Run.cc` sets per field (TestEm3 track lengths have 3 digits).
- **Biased runs do not balance.** With secondary biasing TestEm3 weights the deposit but not the leakage, so run 1 does
  not close its energy balance (`geant4:examples/extended/electromagnetic/TestEm3/TestEm3.in`).
- **Killed tracks are booked as deposits.** `G4StepLimiterPhysics` attaches `G4UserSpecialCuts`, which books a killed
  track's kinetic energy as a local deposit and kills it; a killed e+ does not annihilate
  (`geant4:source/physics_lists/constructors/limiters/src/G4UserSpecialCuts.cc`). Do not subtract that energy again,
  and add 2 m_e c^2 per killed e+ to the balance.
- **Automatic data search.** An unset dataset variable does not necessarily fail: Geant4 searches `GEANT4_DATA_DIR`,
  the install data folder, `/usr/local`, `/usr` and `/cvmfs/geant4.cern.ch` and may use another copy
  (`geant4:source/global/management/src/G4FindDataDir.cc`). `geant4-config --check-datasets` checks only that the
  compiled-in folders exist (`geant4:cmake/Templates/geant4-config.in`). Record the resolved paths and their content
  hashes.
- **UI command timing.** The EM constructors call `G4EmParameters::SetDefaults()`
  (`geant4:source/physics_lists/constructors/electromagnetic/src/G4EmStandardPhysics.cc`), so `/process/em`,
  `/process/msc` and `/process/eLoss` commands work only after the physics list is built and before `/run/initialize`.
- **Replicas are not overlap-checked.** `G4PVReplica` does not declare `CheckOverlaps`
  (`geant4:source/geometry/volumes/include/G4PVReplica.hh`; compare `G4PVPlacement.hh`), and `/geometry/test/run`
  samples points, so a pass is not a proof.

**Benchmarks** (`geant4_benchmarks.py`). Reference inputs come from the study spec (PDG or NIST), never from the
material dump; constants from `core/constants`.

| Benchmark | Grade | Reference |
|---|---|---|
| `stopping-power` | reference | Bethe, RPP 2024 Eq. 34.5, at the mean energy in the slab; density effect Eq. 34.7 |
| `range` | reference | user-supplied PSTAR/ASTAR projected range (no nuclear interactions) |
| `thin-layer-mpv` | reference | Delta_p, RPP 2024 Eq. 34.12 (j = 0.200), only for kappa < 0.05; thickness of validity and accuracy declared in the spec, as RPP states neither |
| `thin-layer-width` | sanity | Landau width 4 xi; thin-layer distributions are significantly wider (RPP 2024) |
| `multiple-scattering` | sanity | Highland, RPP 2024 Eq. 34.16, through `multiple_scattering.py`; RPP gives no numerical accuracy |
| `em-shower-shape` | sanity | t_max, RPP 2024 Eq. 34.36 (not applicable when the stack does not contain t_max) |
| `shower-containment` | sanity | rear leakage against the gamma-function profile, RPP 2024 Eqs. 34.34-34.36 (a fit to EGS4 showers, 1-100 GeV; b = 0.5 by default): never validation; a reference for leakage needs published data (`published-data`) |
| `published-data` | interface | handed to hep-statistics |

Each reference benchmark has a tolerance (reference accuracy + k SE + binning) and a detection limit (tolerance +
|observed offset| + 2 SE), and reruns on a negative control: a Geant4 run with an error of that size injected on the
Geant4 side (for example the density raised by the detection limit while the reference keeps the spec density). The
control must fail; gross controls (multiple scattering off) do not count. A benchmark whose control is not caught is
not evidence for its scope.

## 6. Variations

Vary only what changes the model used for this particle and energy, and state the model assignment
(`check_geant4_study.py variations`). For thin-layer EM observables vary the EM constructor and the fluctuation model
(Urban against PAI). For hadronic observables first check that the two lists use different models at that energy:
QGSP_BIC and FTFP_BERT give a false zero difference for pions below 3 GeV and for any hadron between 6 and 12 GeV
(Bertini, then FTFP, in both); they differ for nucleons below 1.5 GeV (Binary cascade) and above 12 GeV (QGSP). A reference list with an EM
suffix that maps to the same constructor (for example `FTFP_BERT_EMZ` against option 4) keeps the EM model and is
excluded. Report the spread as a model envelope, not a sigma, with each variation's standard error (a difference
below about 2 SE is not resolved), and hand it to hep-statistics as an envelope.

## 7. Labels and handoffs (phase 1)

- Every Geant4-derived artifact is `unvalidated` (or also `failed`), with its evidence embedded. Nothing is upgraded
  to `validated-in-scope` in phase 1; `check_geant4_study.py label` lists only the scopes a later phase could upgrade.
- The study record is a `computational-run`: its `inputs` are the run records (status declared, sha256) and any
  reference `dataset-record`; it carries every propagating label they bring; `extension.study` holds the benchmarks,
  convergence, variations, declared scope and gaps. Check it with `python3 <plugin root>/contracts/validate.py
  <record> --strict` and `python3 <plugin root>/contracts/dependencies.py <record> --root <project>`.
- A response from the runs: `build_response.py build ... --status unvalidated` (it writes empty `inputs`, a
  provenance gap listed in the study record). Inference goes to hep-statistics; plots of simulation alone are labelled
  "Simulation" (hep-authoring).
- Phase 2 (re-issuing an eligible scope as `validated-in-scope`) is deferred by maintainer decision (2026-10-21). It
  would need all of: an explicit exception in point 5 of the shared context-resolution stanza (regenerating every
  SKILL.md and a live routing rerun); a contract rule after 3.0.1 requiring a `study` block with a passed reference
  benchmark whose negative control held, a passed convergence gate and a declared scope inside the benchmark scope;
  a field that references the provisional run records by path and hash without inheriting their labels, resolved by
  `dependencies.py`; the study spec kept in `extension.input_manifest`; `build_response.py` able to link run records
  and carry several labels; and recorded fixtures not tied to the current contract version. Until then never relabel a
  study record: `dependencies.py` reports `dependency.status_undeclared` for exactly that.

## 8. The Geant4 adapter

The optional adapter `<plugin root>/adapters/geant4/` (Geant4 is distributed under the Geant4 Software License 1.0;
nothing of it is bundled: the source is cloned and built in the user's work folder with the user's approval) runs the
execution layer. Its records are always `unvalidated`.

- `assets/geant4_build.py build --spec BUILD_SPEC.json --work DIR --record OUT.json`: clone the tag, check the commit,
  build, install, fetch the datasets the spec names (tarball MD5 checked), hash every dataset folder; `check` compares
  an installation with its record.
- `assets/geant4_examples.py build|run|extract|compare|smoke`: the four official examples, run unchanged through a
  wrapper macro in serial mode and compared with the reference outputs, each quantity with its own standard error and
  a Bonferroni threshold; reruns are pooled, never substituted. B4a is a smoke test only.
- `assets/geant4_run.py`: `build-sim` (layered_sim against the installation), `run` (one JSON spec: per-event CSV,
  log, material dump, data-path record and a record with a `simulation` block; a data path or content hash that
  differs from the build record makes the run `failed`), `scan` (a parameter grid as a `workflow.json` for
  `skills/hep-computing/scripts/run_workflow.py`, steps under 3600 s), `chunk` (a `local_partition.py` worker writing
  additive sums and `{"csv": [...]}` for `--rule csv=concat`), `summarize` (means after the merge, duplicate check,
  agreement with a single run), `reduce` (a gzip copy of chosen columns for replay) and `oracle` (runs
  `geant4_benchmarks.py` through a subprocess).
- `assets/geant4_verify.py overlaps|budget|balance|mirror|datapaths`: the implementation checks, each able to write a
  record that lists the checked run as an input.

The hep-detector side never imports the adapter: `scripts/check_geant4_study.py` (`spec`, `summarize`, `run`,
`variations`, `label`) and `scripts/geant4_benchmarks.py` (`run`, `reference`) read the files it writes. A worked
journey with real runs, negative-control scenarios and an offline replay is
[examples/geant4-thin-silicon](../../../examples/geant4-thin-silicon/run.py).

## 9. Reporting and citation

State the Geant4 version and commit, the physics constructor and options, the cuts, the documentation version relied
on, the reference sources and their editions, the benchmarks with scope and detection limit, and the label. Cite the
Geant4 papers and the documents from a hep-citations literature-record, never from memory, following
[primary sources and version checks](../../hep-citations/references/primary-sources-and-version-checks.md); check the
draft with hep-authoring's `check_citations.py`.

**Done when:** the study spec passes `check_geant4_study.py spec`, the convergence gate passes, every reference
benchmark's negative control is caught at its claimed detection limit, the study record is `unvalidated` with its
evidence and scope embedded and passes `validate.py --strict` and `dependencies.py`, and every citation is in a
literature-record.
