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

- **Statistics** (contracts CV-A1). Each evidence point is one logical run with seed S = H(study_id, role, point_id)
  (`core/simulation/seeds.py`), split by event number into K >= 16 blocks declared in the spec (`blocks.K`); its run
  summary (`simulation-summary/1`, `adapters/geant4/assets/summary_from_csv.py`) holds per-block accumulators of the
  spec's `observables` (estimator mean, proportion, mode or quantile). Values and SEs are batch means over the blocks
  (SE on K - 1 degrees of freedom; a proportion with an empty block or fewer than 100 counts uses exact intervals);
  the most probable value is the mean of three-point parabola modes of the block histograms. Choose the bin width
  and the events per block with bias toys before the first evidence run (95 % upper bound of the bias <= tol/10).
  Events must not share state (biasing breaks it); weights other than 1 are refused.
- **Convergence (hard gate).** Scan the production cut (and the step limit when one is used). `check_geant4_study.py
  run` requires a run summary for every declared value (otherwise `incomplete`, reason `missing-scan-value`) and
  compares the two finest *declared* values with an equivalence test for every declared observable (tolerance
  `relative` from `tolerance_relative`, or `absolute` from the observable's `tolerance`): pass when |diff| +
  t_0.95(nu) se <= tol and both points meet the se target tol / (4 sqrt 2); fail when |diff| - t_(1-0.05/m)(nu) se >
  tol (m = parameters x observables); anything else is `incomplete` (exit 3). Expect it: about 19 % of point pairs
  miss a target under the two-stage design below, and at a true difference equal to the tolerance about 90 % are
  unresolved; given that both points met the target, the pass rate there is 0.054, slightly above 0.05. It is the
  only check that catches a cut that is too coarse: no reference benchmark sees it.
- **Event count and stopping rule** (D6). Decide the stopping rule, scan grid, K, the event counts and how an
  unresolved result is handled in the study spec before the first evidence run. Each point gets a trial run (role
  `trial`, K_trial = 16, N_trial declared); its evidence run then has N = N_trial (SE_trial / target)^2 F_0.95(K - 1,
  K_trial - 1) events, rounded up to a multiple of K. A point that still misses its target is `incomplete`: never add
  events, rerun with another seed or refine the scan because of a result (optional stopping biases the evidence).
  With n points that need a target all meet it with probability about 0.9^n.
- **Shared evidence** (D7). One run often serves several decisions (the nominal feeds the gate, the statistical
  target, the benchmark and the variations); `label` lists such runs in `extension.study.evidence_overlap`, and they
  are not independent evidence.
- **Observables for the gate.** Declare in `observables` what the study measures (thin layers: mean deposit, most
  probable deposit and loss, tail fraction; thick absorbers: leakage fractions from the leakage-by-face columns).
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
| `longitudinal-profile` | setup-matched | the shower maximum t_max = (alpha - 1)/beta of a Gamma fit to per-layer mean deposits against the same fit to published test-beam data (config `published`: alpha, beta with uncertainties and source; their correlation is not used, which is conservative only for a non-negative correlation, the usual case for a Gamma fit; a negative one understates the t_max uncertainty); `systematic_relative` covers stated differences between the planar model and the measurement (readout window, beam spot, upstream material). First reference: a W/Si forward-calorimeter prototype test beam, JINST 19 (2024) P07006 (arXiv:2311.07413), Table 3 |
| `published-data` | interface | handed to hep-statistics |

The grade is the benchmark's validation class in the contracts table (`contracts.validate.GEANT4_BENCHMARKS`, contracts
CV-A1): a study record that declares another grade, or names a benchmark not in the table, is refused. Only reference
and setup-matched benchmarks can upgrade a study: reference against a physics model or thin-target measurement on an
isolated target, setup-matched against a published measurement of the same configuration (isolated, target hash
equal to the measured one).

**Configuration and isolation** (CV-A1). `geant4_benchmarks.py` derives each benchmark's configuration from the
spec/1 of the run record its setting names (`run_record`), never from user input: the target is `target_slabs`
(absorbers included; by default the measured slab; `longitudinal-profile` lists its whole sampling stack), the target
hash (`hash_scheme: spec-v1`) is the sha256 of the target's placements in order with thickness, transverse size,
material and declared composition (numbers as `float.hex()`), and the target is `isolated` when the world is vacuum
(`G4_Galactic` or density below 1e-20 g/cm3) and every other placement belongs to it, otherwise `embedded`. A counted
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

## 6. Variations

Vary only what changes the model used for this particle and energy, and state the model assignment
(`check_geant4_study.py variations`). For thin-layer EM observables vary the EM constructor and the fluctuation model
(Urban against PAI). For hadronic observables first check that the two lists use different models at that energy:
QGSP_BIC and FTFP_BERT give a false zero difference for pions below 12 GeV and for nucleons between 1.5 and 12 GeV
(Bertini, the shared 3-6 GeV Bertini-FTF transition, then FTFP, in both); they differ for nucleons below 1.5 GeV (Binary cascade) and above 12 GeV (QGSP). A reference list with an EM
suffix that maps to the same constructor (for example `FTFP_BERT_EMZ` against option 4) keeps the EM model and is
excluded. Report the spread as a model envelope, not a sigma, with each variation's standard error (a difference
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
  rule (`geant4.upgrade_*`) refuses a record without a passed reference benchmark whose negative control was caught,
  without a passed convergence gate, or with a declared particle, material, energy or thickness outside the benchmark
  scope; a run record is never re-issued. Neither the rule nor `label` compares the observable, and a declared scope
  that omits the thickness is not checked against the benchmark's thickness: declare both and check them by hand. This is the one exception to keeping labels on everything derived from them (shared stanza, point 5).
  Validated means only: within this particle, energy, material, thickness and observable (the observable, and an
  omitted thickness, checked by hand as above), the run agreed with an
  independent reference to the stated tolerance, with the detection limit stated. Never relabel by hand.
- A table from the runs (resolution, containment, leakage by face): a `dataset-record` with status `simulated`
  (contracts 3.2.0), the run records (or the study record) as `inputs` with their labels, level `detector` or
  `particle-fiducial`; it keeps `unvalidated` unless its input study record carries `validated-in-scope`, and the
  table must stay inside that study's benchmarked scope (not checked by the contract: state it).
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
  `--timeout 3540`), `chunk` (a `local_partition.py` worker writing
  additive sums and `{"csv": [...]}` for `--rule csv=concat`), `summarize` (means after the merge, duplicate check,
  agreement with a single run), `reduce` (a gzip copy of chosen columns for replay) and `oracle` (runs
  `geant4_benchmarks.py` through a subprocess); `run --evidence-role --point-id --logical-run-seed` records what the
  run is for and its seed scheme.
- `assets/summary_from_csv.py`: the run summary (`simulation-summary/1`, K blocks) of a logical run from its CSVs and
  the study spec's observables, validated before it is written.
- `assets/geant4_verify.py overlaps|budget|balance|mirror|datapaths`: the implementation checks, each able to write a
  record that lists the checked run as an input.

The hep-detector side never imports the adapter: `scripts/check_geant4_study.py` (`spec`, `run`, `variations`,
`label`) and `scripts/geant4_benchmarks.py` (`run`, `reference`) read the files it writes. A worked
journey with real runs, negative-control scenarios and an offline replay is
[examples/geant4-thin-silicon](../../../examples/geant4-thin-silicon/run.py).

## 9. Reporting and citation

State the Geant4 version and commit, the physics constructor and options, the cuts, the documentation version relied
on, the reference sources and their editions, the benchmarks with scope and detection limit, and the label. Cite the
Geant4 papers and the documents from a hep-citations literature-record, never from memory, following
[primary sources and version checks](../../hep-citations/references/primary-sources-and-version-checks.md); check the
draft with hep-authoring's `check_citations.py`.

**Done when:** the study spec passes `check_geant4_study.py spec`, the convergence gate passes, every reference
benchmark's negative control is caught at its claimed detection limit (with no reference benchmark this holds
vacuously and `label` records the R5 gap: the study is then not validation evidence), the study record is `unvalidated` with its
evidence and scope embedded and passes `validate.py --strict` and `dependencies.py`, and every citation is in a
literature-record.
