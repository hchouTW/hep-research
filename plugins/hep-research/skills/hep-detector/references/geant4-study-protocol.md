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
- **Agreement with the official examples** (B1, TestEm3, TestEm5, and B4a as a smoke test only; `geant4_examples.py`) and with a mirror of an
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
| `observable` | name, kind (for example `most-probable-value`, `stopping-power`, `energy-deposit`), domain (`em` or `hadronic`), exact definition, unit, whether weights apply, and for leakage `leakage_faces` |
| `particle` | species and kinetic energy |
| `geometry_source`, `materials` | where the geometry and materials come from; for each reference material: density, its source, and `reference_origin` (`independent`, never the Geant4 material dump); Z/A, mean excitation energy I and the Sternheimer parameters when a benchmark uses them (stopping power, thin-layer MPV and width) |
| `physics` | the layered_sim spec, the order of UI commands, and a justification per choice with its source |
| `convergence_plan` | the cut or step-limit scan, the observables checked (any declared in `observables`) and their tolerances (relative, or absolute per observable declaration) |
| `statistical_target` | the observable and the relative standard error required |
| `validation_plan` | the benchmarks and the declared scope (particle, energy range, material, thickness range, observable) |
| `variation_plan` | the model variations and whether their model assignment was checked |
| `downstream_use` | response matrix, comparison with published data, report; who receives it (the fields below are also part of the spec) |
| `observables`, `blocks` | the declared observables (`simulation-observables/1`) and K |
| `stopping_rule` | how the event count was fixed before the first evidence run (trial events, target SE, events) and what happens to a point that misses its target |
| `citations`, `reproducibility`, `geant4` | the sources cited, the reproducibility record and the Geant4 version and datasets |

Ask the user for the observable, the particle and energy, the source of the geometry and materials, and the precision
target or downstream use when any is missing. Never choose an experiment or a detector for the user.

## 3. Physics settings: when to take care and what to read

The rule table [`../assets/geant4-physics-rules.json`](../assets/geant4-physics-rules.json) holds each item below as
a machine-checkable condition with its source and severity; `check_geant4_study.py spec` applies it and reports its
coverage. The items say when to look and where, not which list to use.

- **Low-energy neutrons** (below 20 MeV): the data-driven ParticleHP models and the G4NDL data (`G4NEUTRONHPDATA`)
  are only in the `_HP` lists (with their `_HPT` and `_AllHP` variants) and in the Shielding family (`Shielding`,
  `ShieldingM`, `ShieldingLIQMD`, built with HP without the suffix)
  (`geant4:source/physics_lists/constructors/hadron_inelastic/src/G4HadronPhysicsQGSP_BIC_HP.cc`,
  `SetMaxEnergy(20*CLHEP::MeV)`; `geant4:source/physics_lists/lists/src/G4PhysListFactory.cc`;
  `geant4:cmake/Modules/G4DatasetDefinitions.cmake`). Rule `G4R-HP-NEUTRON`.
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
- **Hadronic model ranges**: the list named exactly QGSP_BIC uses the Binary cascade only for protons and neutrons up to 1.5 GeV
  (`geant4:source/physics_lists/constructors/hadron_inelastic/src/G4HadronPhysicsQGSP_BIC.cc`,
  `maxBIC_proton = maxBIC_neutron = 1.5 GeV`, Bertini from 1 GeV, otherwise as
  `geant4:source/physics_lists/constructors/hadron_inelastic/src/G4HadronPhysicsQGSP_BERT.cc`; FTFP_BERT has no
  Binary range); the model table holds for the lists named exactly QGSP_BIC and FTFP_BERT: variants such as FTFP_BERT_ATL (transition moved) or the _HP lists
  (ParticleHP below 20 MeV) use other models, and `check_geant4_study.py` treats their model as unknown; the FTF-cascade
  transition is 3 to 6 GeV and the QGS-FTF transition 12 to 25 GeV
  (`geant4:source/processes/hadronic/util/src/G4HadronicParameters.cc`). Rule `G4R-BIC-RANGE` (it requires only the declaration
  `variation_plan.model_assignment_checked`; the comparison itself is `check_geant4_study.py variations`, run with each
  variation's effective config).
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

- **Statistics** (contracts CV-A1). Each evidence point is one logical run with seed S = H(study_id, role, point_id)
  (`core/simulation/seeds.py`; under per-event seeding `geant4_run.py scan` writes it for each point too, from
  `--study-id`, which defaults to the grid name: pass the study's study_id), split by event number into K >= 16 blocks declared in the spec (`blocks.K`); its run
  summary (`simulation-summary/1`; from geant4 adapter 0.2.0 written by `layered_sim` itself from `output.observables`
  and `output.blocks`, merged across threads, with `adapters/geant4/assets/summary_from_csv.py` as its test oracle and
  the producer for older runs) holds per-block accumulators of the spec's `observables` (estimator mean, proportion,
  mode or quantile). New studies seed per event (`run.seeding: per-event`, the default of `geant4_run.py scan`, which gives
  point k its own S = H(study_id, role, point id) from `--study-id` and `--role`): event
  i starts from (H(S, i, 0), H(S, i, 1)), so a logical run gives the same events for any split into jobs and threads;
  reproduce such an event from (S, i), not from Geant4's stored random status. Values and SEs are batch means over the blocks
  (SE on K - 1 degrees of freedom; a proportion with an empty block or fewer than 100 counts uses exact intervals);
  the most probable value is the mean of three-point parabola modes of the block histograms. Choose the bin width
  and the events per block with bias toys before the first evidence run (95 % upper bound of the bias <= tol/10).
  Events must not share state (biasing breaks it); weights other than 1 are refused (`layered_sim` exits 2 when a
  weighted event meets a declared observable), so a biased run cannot give a summary; rule `G4R-BIASED-BALANCE` applies to every
  spec with secondary biasing and requires `observable.weighted` (the per-event CSV checks), and `summary_from_csv.py`
  checks only the vertex weight, so keep biased runs out of the evidence by hand.
- **Boundary artifacts** (A2.6, D9). The study scripts read only what a run hands over: the run summary, the column
  map (`column_map.json`, `simulation-columns/1`: per column a semantic name, unit and definition) and the effective
  config (what Geant4 resolved: geometry tree, materials, EM parameters, cuts per couple, hadronic models with their
  energy ranges, run manager; stored once per content hash). They name semantic columns only (`primary.energy_loss`,
  `energy_deposit.<slab>`); runs before adapter 0.2.0 resolve them through
  `assets/geant4-columns-legacy.json`. The thin-layer rule takes the minimum thickness from the effective config when
  one is given (`check_geant4_study.py spec --effective-config`), else from spec/1.
- **Convergence (hard gate).** Scan the production cut (and the step limit when one is used). `check_geant4_study.py
  run` requires a run summary for every declared value (otherwise `incomplete`, reason `missing-scan-value`) and
  compares the two finest *declared* values with an equivalence test for every declared observable (tolerance
  `relative` from `tolerance_relative`, or `absolute` from the observable's `tolerance`): pass when |diff| +
  t_0.95(nu) se <= tol and both points meet the se target tol / (4 sqrt 2); fail when |diff| - t_(1-0.05/m)(nu) se >
  tol (m = parameters x observables); anything else is `incomplete` (exit 3). Expect it: about 19 % of point pairs
  miss a target under the two-stage design below, and at a true difference equal to the tolerance about 90 % are
  unresolved; given that both points met the target, the pass rate there is 0.054, slightly above 0.05. It is the
  only check that catches a cut that is too coarse (no reference benchmark sees it), and only as far as the declared
  scan reaches: the finest declared cut must be fine for the observable and the tolerance tight enough to matter.
- **Event count and stopping rule** (D6). Decide the stopping rule, scan grid, K, the event counts and how an
  unresolved result is handled in the study spec before the first evidence run. Each point gets a trial run (role
  `trial`, K_trial = 16, N_trial declared); its evidence run then has N = N_trial (SE_trial / target)^2 F_0.95(K - 1,
  K_trial - 1) events, rounded up to a multiple of K. A point that still misses its target is `incomplete`: never add
  events, rerun with another seed or refine the scan because of a result (optional stopping biases the evidence; a
  procedural rule: no tool can tell a rerun under a new study or point id from a new study, so list every run in
  the study record).
  With n points that need a target all meet it with probability about 0.9^n.
- **Shared evidence** (D7). One run often serves several decisions (the nominal feeds the gate, the statistical
  target, the benchmark and the variations); `label` lists such runs in `extension.study.evidence_overlap`, and they
  are not independent evidence.
- **Observables for the gate.** Declare in `observables` what the study measures (thin layers: mean deposit, most
  probable deposit and loss, tail fraction; thick absorbers: leakage fractions from the leakage-by-face columns); any declared observable can be a gate
  observable in `convergence_plan.observables`.
  `geant4_run.py scan` gives every point its own seeds (its own S under per-event seeding, also when the base spec
  declares it, unless the grid scans `run.logical_run_seed`), so the SE of a difference is that of independent
  samples.

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
  precision each example's run class sets per field (`Run.cc`, B1's `RunAction.cc`; TestEm3 track lengths have
  3 digits).
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
| `longitudinal-profile` | setup-matched | the shower maximum t_max = (alpha - 1)/beta of a Gamma fit to per-layer mean deposits against the same fit to published test-beam data (config `published`: alpha, beta with uncertainties and source; their correlation is not used, which is conservative only for a non-negative correlation, the usual case for a Gamma fit; a negative one understates the t_max uncertainty); `systematic_relative` covers stated differences between the planar model and the measurement (readout window, beam spot, upstream material). First reference: a W/Si forward-calorimeter prototype test beam, JINST 19 (2024) P07006 (arXiv:2311.07413), Table 3 |
| `published-data` | interface | handed to hep-statistics |
| `field-propagation` | verification | charged geantinos of an `element_sim` run against the analytic helix (`core/simulation/helix.py`); scope the field-configuration hash |
| `material-definition` | verification | every material of the realized geometry from an independent source (density within 1e-3 of Geant4's resolved one) and a geantino scan reproducing the candidate's `layer_x_over_x0` within the declared tolerance; scope the geometry and realization-profile hashes |
| `reco-closure` | verification | `simreco` on charged geantinos at high rigidity, every tail source off: pull width 1 +- 3 sigma_MC and no bias; scope the reco-spec hash (tail sources, replicas and outputs excluded) |
| `tof-beta`, `tof-layer-consistency` | verification | bookkeeping of `simreco`'s beta and two-layer time differences (no physics control) |
| `field-propagation-muon`, `sampling-fraction` | sanity | mean inverse-rigidity residual of muons; sampling fraction against a declared value |
| `multiple-scattering-reference` | reference (`tracking-resolution`, core only) | core width of the projected exit angle after an isolated slab: the sigma of a Gaussian fitted (maximum likelihood) to the central 98 %, against Lynch and Dahl's F = 98 % formula (NIM B 58 (1991) 6) with the slab's independent Z, A and density; tolerance the formula's published accuracy (2 % from the paper's abstract: full text not yet read) + k SE; scope particle, material, thickness in X0, rigidity |
| `ms-tail-reference` | reference (`charge-confusion`) | not implemented (D0-b): needs a published tail reference; charge-confusion studies cannot be upgraded until then |
| `regression-comparison` | regression | one scalar observable of two versions decided by `core.stats.decisions.change` (changed, unchanged, unresolved); never affects a label |

The grade is the benchmark's validation class in the contracts table (`contracts.validate.GEANT4_BENCHMARKS`, contracts
CV-A1): a study record that declares another grade, or names a benchmark not in the table, is refused. Only reference
and setup-matched benchmarks can upgrade a study: reference against a physics model or thin-target measurement on an
isolated target, setup-matched against a published measurement of the same configuration (isolated, target hash
equal to the measured one).

**Configuration and isolation** (CV-A1). `geant4_benchmarks.py` derives each benchmark's geometry, materials and target hash
from the run record its setting names (`run_record`), never from user input. The slab list, and the particle, energy,
material and thickness that set the reference value and the benchmark scope, come from the benchmark config and are
not compared with the run record: check them against it by hand. The target is `target_slabs` (absorbers included; by
default the measured slab; `longitudinal-profile` lists its whole sampling stack). For records before geant4 adapter
0.2.0 the target hash (`hash_scheme: spec-v1`) is the sha256 of the target's placements in order with thickness,
transverse size, material and declared composition from spec/1 (numbers as `float.hex()`); records from 0.2.0 use
`tree-v1`, the same idea over the effective config's geometry tree (solid, resolved composition and density,
transform, field; names and copy numbers excluded and hashed separately in `naming_sha256`; daughters in canonical
order; transforms relative to the first target placement), so the same target built by two programs has one hash.
Hashes compare only within one scheme. The target is `isolated` when the world is vacuum (`G4_Galactic` or density
below 1e-20 g/cm3), no field is attached and every other placement belongs to it, otherwise `embedded`;
`geant4_run.py` refuses a run whose spec-v1 and tree-v1 decisions differ, and a run whose probe recorded nothing
(`recorded: false`) cannot upgrade. A counted
benchmark must be isolated; `contracts/dependencies.py` re-derives the configuration from the run record and refuses a
mismatch. Limits: J14's recorded CSVs are reduced, so their hashes are not the run records' `output_hashes`; the
configuration describes the run record the setting names; the geometry of negative-control runs is not checked
separately.

Each reference or setup-matched benchmark has a tolerance (reference accuracy + k SE + binning, SE by batch means)
and a detection limit DL = tolerance + |observed offset| + t_0.977(nu) SE of the shift, and reruns on negative
controls: Geant4 runs with an error of that size injected on the Geant4 side (for example the density raised and
lowered by the detection limit while the reference keeps the spec density). A control is judged on the observable:
shift = (control - nominal) / reference; it is caught when its benchmark verdict fails and at the claimed limit when
|shift| <= 1.1 DL. Controls in both directions are needed for a two-sided claim; one direction narrows it
(`detection_limit_sign`). A single miss is recorded, never rerun with another seed; gross controls (multiple
scattering off) do not count. A benchmark whose control is not caught is not evidence for its scope.

New studies of the multiple-scattering reference declare `control_rule: "declared-size/1"` (decided 2026-10-25; the
factors are provisional). The window above is narrow compared with the scatter of a measured shift, so a correctly
sized control is refused often; the declared rule fixes the size before the runs instead. Run the nominal, then
`geant4_benchmarks.py plan-controls --config C`: it prints the planned DL (from the nominal alone) and the +- areal-
density changes whose expected shift, through Lynch and Dahl's formula, is 1.25 x that DL (the width scales about as
the square root of the density, so a density change of DL would move it only about DL/2). Write those
`injected_relative` values and the rule into the config, then make the control runs. A control counts when it is
caught and its expected shift is at most 1.5 x the planned DL (by construction for planned controls; a gross control
fails it), and the benchmark claims the largest detection limit a caught control demonstrated, max(DL, |shift|): never
less than a control showed. The rule applies to studies run under it; a study recorded under the window rule keeps
that rule and its outcome (J15 at 100 GV and J16 at 1 TV stay refused).

**The multiple-scattering core estimator.** Lynch and Dahl's theta0 is the width of a Gaussian fitted to the central
98 % of the angles, which is what `multiple-scattering-reference` computes (truncated-normal maximum likelihood in the
symmetric window holding 98 %). RMS(central 98 %) / 0.8673, the estimator of the `multiple-scattering` sanity
benchmark, assumes the inner 98 % is itself Gaussian; the single-scattering tail inside the window widens it by about
10 % (0.3 mm of silicon, protons at 1 and 10 GeV/c, option 4: +11 % against -1.5 % with the fit; VALIDATION
GEANT4-F4). Point resolution is a declared input that no benchmark validates; at high rigidity it dominates the core.

**Detector-level studies: the F4 qualification path** (CV-B2, decided D0 2026-10-24). A study of kind
`tracking-resolution` is upgradable only when all four conditions hold, each matched to the study by its own key in
`validation_plan.scope`: (1) `material-definition` passed for the same geometry and realization-profile hashes;
(2) `field-propagation` passed for the same field-configuration hash; (3) `reco-closure` passed for the same reco-spec
hash; (4) `multiple-scattering-reference` passed with its controls caught, covering the declared particle, material,
thickness in X0 and rigidity. `geant4_benchmarks.py scope-keys --element-spec --reco-spec --geometry --realization`
prints the hash keys to declare; `label` derives the same keys from the study's own inputs (`--geometry`, the derived
`element_sim` spec and its provenance, the reconstruction record the results file names) and refuses an upgrade whose
declared keys differ, so verifications of another configuration cannot be borrowed. The counted reference keeps
A1.3's isolation check, and its negative controls count only when their run records carry the stated injection
(the slab's areal density from each run's effective config). Verification benchmarks never upgrade a study on their own, and the convergence gate,
no remaining gap and a variation table apply as before. A `charge-confusion` study needs `ms-tail-reference` instead
(D0-b, not yet available); `shower-containment` and the other calorimeter figures of merit have no reference here and
their F4 studies stay unqualified. Every other kind keeps the CV-A1 rule (any covering reference or setup-matched
benchmark). Every run a qualification benchmark reads is an evidence record of the study (`label --run-record`):
`dependencies.py` re-derives the reference benchmark's configuration from its run record.

## 6. Variations

Vary only what changes the model used for this particle and energy, and state the model assignment
(`check_geant4_study.py variations`). For thin-layer EM observables vary the EM constructor and the fluctuation model
(Urban against PAI). For hadronic observables first check that the two lists use different models at that energy:
QGSP_BIC and FTFP_BERT use the same inelastic models for pions below 12 GeV and for nucleons between 1.5 and 12
GeV (Bertini, the shared 3-6 GeV Bertini-FTF transition, then FTFP, in both), so their difference there is not a
model variation (what remains comes from ion elastic physics and cross-section data); they differ for nucleons below 1.5 GeV (Binary cascade) and for pions and nucleons above 12 GeV (QGSP). A reference list that builds the
same EM constructor as the nominal keeps the EM model and is excluded from the EM variations: the constructor
comes from the EM suffix, or without one from the list itself (option 4 in the QGSP_BIC_HP family, GS in
FTFP_BERT_TRV, G4EmStandardPhysics otherwise; LBE ignores suffixes), so `FTFP_BERT_EMZ` against
`QGSP_BIC_HP` is no EM variation. Report the spread as a model envelope, not a sigma, with each variation's standard error (a difference
below about 2 SE is not resolved), and hand it to hep-statistics as an envelope.

## 7. Labels and handoffs

- Every Geant4 run record is `unvalidated` (or also `failed`) and stays so: a run is never validated.
- The study record is a `computational-run`: its `inputs` are the run records (status declared, sha256) and any
  reference `dataset-record`; it carries every propagating label they bring; `extension.study` holds the benchmarks,
  convergence, variations, declared scope and gaps. Check it with `python3 <plugin root>/contracts/validate.py
  <record> --strict` and `python3 <plugin root>/contracts/dependencies.py <record> --root <project>`.
- Phase 2 (contracts 3.1.0): `check_geant4_study.py label --upgrade` re-issues the study record as
  `validated-in-scope` only when a scope is eligible and no gap remains. The run records then move from `inputs` to
  `extension.evidence_records` (path and sha256; `dependencies.py` checks the hash, exit status 0, no `failed`, and
  that output hashes are recorded (present and well formed, not compared with the output files), without inheriting
  their labels) and the record requires `core:evidence-records`. The contract
  rule (`geant4.upgrade_*`) refuses a record without a passed reference or setup-matched benchmark whose negative control was
  caught,
  without a passed convergence gate, or with a declared particle, material, energy or thickness outside the benchmark
  scope; a run record is never re-issued. From contracts 3.13.0 (CV-A1) the rule compares the controlled
  observable kind and every scope dimension of the benchmark, thickness included; records before 3.13.0 are checked
  this way only under `validate.py --strict` (which this section asks for); otherwise declare every dimension and
  check them by hand. This is the one exception to keeping labels on everything derived from them (shared stanza, point 5).
  Validated means only: within this particle, energy, material, thickness and observable (for records before contracts
  3.13.0 the observable and an omitted thickness are checked by hand as above), the run agreed with an
  independent reference to the stated tolerance, with the detection limit stated. Never relabel by hand.
- A table from the runs (resolution, containment, leakage by face): a `dataset-record` with status `simulated`
  (contracts 3.2.0), the run records (or the study record) as `inputs` with their labels, level `detector` or
  `particle-fiducial`; it keeps `unvalidated` unless its input study record carries `validated-in-scope`, and the
  table must stay inside that study's benchmarked scope: the contract does not check this (it checks only that an
  input study record carries `validated-in-scope`), so state the scope in the table's record and check it by hand.
- A processing chain (CV-B2): a table's inputs may be reconstruction records (`geant4_run.py reco`, a
  `computational-run` with `extension.reconstruction`) as long as every level is a recorded `computational-run` and
  every root a simulation or study record; `dependencies.py` follows the chain. While the study is `unvalidated` the
  table stays `unvalidated`.
- An F4 study (B2.6): `geant4_run.py table --f4-results` writes `f4-results/1` (value, the coverage-0.90 uncertainty
  object = statistical (t_0.95(K-1) x batch-means SE) (+) replica spread, the model envelope from `--variation` reco
  records, the tail sources simulated, the geometry file's sha256); `check_geant4_study.py label --results FILE
  --geometry GEOMETRY` keeps them in `extension.study` and adds the results, geometry, derived spec and realization
  profile to `input_manifest` (a geometry sha256 that differs from the results file's exits 2). Then either run
  `evaluate_design.py f4 --study RECORD`, or `f4 --label-spec ... --label-results ... --label-geometry ...` in one
  step; both give the same evaluation, whose `geometry_ref` names the geometry its study used. An F4 resolution is an
  `estimate` only with all four tail sources simulated, else `optimistic` (a tail source switched on must act:
  `simreco_spec.check` refuses one with zero widths). The results file must come from a reconstruction record among
  the study's `--run-record`s, with the same tail sources, its observable must read the figure of merit's column and
  select the fitted tracks, and its denominator must be the simulated gun's (rigidity, species).
- The F4 uncertainty and floor (D0-c, decided 2026-10-24): on a qualification path `label` adds the qualifying
  reference's total tolerance T (published accuracy + k SE) times |value| in quadrature to each side of the
  coverage-0.90 interval (`uncertainty_components.qualification`): an upgraded value is no more accurate than what the
  upgrade certifies. `design.py` then uses the path's floor (adequacy table `f4_qualified_min_relative_uncertainty`,
  0.02 for `momentum-resolution-core`: Lynch and Dahl's published accuracy) instead of `min_relative_uncertainty`
  (0.2, which describes the F1 formula's 20-50 % bias), and only when the evaluation's uncertainty holds the term.
  Both values are provisional until the adequacy table's physics review (OQ-05). Point resolution is a declared input
  that no benchmark validates: above the crossover rigidity (about 20-30 GV for protons in J15) the verdict is
  conditional on the declared point resolution, and the README says so.
- A response from the runs: `build_response.py build ... --status unvalidated --input-record <run record>` links the
  run records as inputs with their labels. Inference goes to hep-statistics; plots of simulation alone are labelled
  "Simulation" (hep-authoring).

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
  `skills/hep-computing/scripts/run_workflow.py`; a step estimated above 3600 s is refused, and each step runs with
  `--timeout 3540`; specs it writes seed per event by default), `chunk` (a `local_partition.py` worker writing
  additive sums, `{"csv": [...]}` for `--rule csv=concat` and, with observables, `{"summaries": [...]}` for
  `--rule summaries=concat`), `summarize` (from the chunks' summaries when they have them, reading no CSV; for older
  partitions means after the merge, duplicate check, agreement with a single run), `reduce` (a gzip copy of chosen
  columns for replay) and `oracle` (runs `geant4_benchmarks.py` through a subprocess); `run --evidence-role
  --point-id --logical-run-seed` records what the run is for and its seed scheme. From adapter 0.2.0 every run record
  also carries the summary, column map and effective config (hash and reference), `argv`, `script_sha256` and
  `versions.plugin_release`.
- `assets/summary_from_csv.py`: the run summary (`simulation-summary/1`, K blocks) of a logical run from its CSVs and
  the study spec's observables, validated before it is written (the test oracle of `layered_sim`'s own summary).
- `assets/g4sim/`: the headers shared by the adapter's programs (seed hash, per-event seeding, summary accumulators,
  the effective-config probe, materials, physics lists, CSV helpers); `g4sim/selftest.cc` checks the Geant4-free ones
  against their Python references (`tests/adapters/test_g4sim.py`).
- `assets/geant4_verify.py overlaps|budget|balance|mirror|datapaths|field`: the implementation checks, each able to
  write a record that lists the checked run as an input.
- From adapter 0.3.0, `element_sim` (box elements, uniform field regions, plane crossings of every charged track, a
  per-event ROOT event file read by `simroot info|dump|hash`); `geant4_run.py check-spec` and `from-geometry`
  (a `design-geometry/1` file plus an `element_sim.realization/1` profile to an `element_sim.spec/1`; mapping 1.1.0's
  optional fields (tracker material and size, field extent, TOF layers, calorimeter front face, depth and sampling)
  need a profile that declares 1.1.0).
- From adapter 0.4.0, `simreco` (C++17, no Geant4; `build-sim --program simreco`): point errors or a strip
  digitization, a circle-arc fit with the multiple-scattering covariance, TOF beta, calorimeter energy, and four tail
  sources, each switched in the reco spec: `alignment` and `calibration-non-uniformity` as M >= 20 reconstruction
  replicas (seeded by H(S, "align", m) and H(S, "fieldnu", m)), `noise-digitization` and `pattern-recognition`; a
  global field scale is not a tail source. `geant4_run.py reco` dumps the crossings, runs `simreco` per replica and
  writes a record with the input hashes (changing digitization or tail sources needs no new simulation); `table`
  writes the simulated dataset-record and, with `--f4-results`, the F4 results file. The summary's
  `tail_sources_simulated` lists only the stages that ran.
- From adapter 0.4.1: `field.max_track_time_ns` kills tracks older than that in a field element (a looper in a
  vacuum field region never meets the looper killer under a step limit); the strip digitization draws a random strip
  phase per plane and event and gives hits sigma = sqrt((p - w)^3 / 12 p) (pitch p, sharing width w), and
  `simreco_spec.check` refuses a digitization finer than the declared point resolution (tails on would then measure
  better than tails off); shower containment is the calorimeter deposit over the incident energy. A design project
  taken from F1 to F4 with these programs:
  [examples/design-minimal-spectrometer](../../../examples/design-minimal-spectrometer/README.md) (J15).
  The detector benchmarks' config keys are listed in `geant4_benchmarks.py --help`. A reference's negative
  control is declared with the injection Geant4 realized (a NIST material resolves to Geant4's own density, so
  derive the control from it), before the runs; a control declared otherwise is not counted, and correcting the
  declaration after the result is a rerun after a miss. Single scattering (`__SS`) in a design with a thick
  calorimeter can cost far more per event than option 4 even at 1 GV (protons stopping in lead; J15's acceptance
  run measured about 2000 events in 16 min on 8 threads); plan its event count from a trial. Validate the whole artifacts_dir (`contracts/validate.py --strict <artifacts_dir>`), with
  derived specs and dumps kept outside it: paths in records are relative to that root.
- From adapter 0.5.0 (Geant4 program C2): an observable declared with `values: true` keeps each block's raw values
  (at most `values_max` per block, else `values_omitted`), so the quantile estimator is empirical (Hyndman-Fan type
  7); `run --seed-group NAME` records the seed_group whose runs share S. Runs of one seed_group (Geant4 search values,
  evidence role `search`) are compared in paired mode (`core/stats/decisions.py`: per-block differences); they are
  never study evidence (`label` refuses them), and a confirmation study's runs use S = H(study_id, role, point_id)
  with study_id from `core/simulation/seeds.py` `confirmation_study_id`, so no evaluation shares a search seed
  (`design.contract_mismatch`); S repeats only within one declared seed_group (`design.seed_reuse`).

The hep-detector side never imports the adapter: `scripts/check_geant4_study.py` (`spec`, `run`, `variations`,
`label`) and `scripts/geant4_benchmarks.py` (`run`, `reference`, `scope-keys`) read the files it writes. A worked
journey with real runs, negative-control scenarios and an offline replay is
[examples/geant4-thin-silicon](../../../examples/geant4-thin-silicon/run.py).

## 9. Reporting and citation

State the Geant4 version and commit, the physics constructor and options, the cuts, the documentation version relied
on, the reference sources and their editions, the benchmarks with scope and detection limit, and the label. Cite the
Geant4 papers and the documents from a hep-citations literature-record, never from memory, following
[primary sources and version checks](../../hep-citations/references/primary-sources-and-version-checks.md); check the
draft with hep-authoring's `check_citations.py`.

**Done when:** the study spec passes `check_geant4_study.py spec`, the convergence gate passes, every reference
or setup-matched benchmark's negative control is caught at its claimed detection limit, the statistical target is met
(with no such benchmark the control clause holds vacuously and `label` records the R5 gap: the study is then not
validation evidence), the study record carries the label `label` issued (`unvalidated`, or `validated-in-scope` after
`--upgrade` when a reference or setup-matched benchmark qualifies; with none the study is verification only) with its
evidence and scope embedded and passes `validate.py --strict` and `dependencies.py`, and every citation is in a
literature-record.
