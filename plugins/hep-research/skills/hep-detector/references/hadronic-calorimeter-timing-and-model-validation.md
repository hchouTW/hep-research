# Hadronic Calorimeter Timing and Model Validation

How the time of a hadronic shower is reconstructed, and which observables validate the hadronic physics lists of a
calorimeter simulation. Energy reconstruction, compensation, the calibration chain and leakage are in
[hadronic calorimeter reconstruction](hadronic-calorimeter-reconstruction.md), whose relation numbers (HC1-HC9) this
page shares; physics-list choice is in [detector simulation](detector-simulation.md#physics-lists-and-their-validity)
and the [Geant4 study protocol](geant4-study-protocol.md) (secs. 3, 5 and 6; sec. 6 for which list pairs are a model
variation). Fitting simulator parameters to data is simcal, owned by hep-statistics
([simulation-calibration/hcal](simulation-calibration/hcal.md)).

Environment codes (R1): COL collider; FXT fixed-target and test beam; SPC space and balloon; UGD underground,
neutrino and rare-event; GND ground-based arrays; NUC nuclear and low-energy. Content for one environment carries its
code. Named apparatus and every performance number sit in example blocks.

## Relations

| # | Relation | Status and validity | Source |
|---|---|---|---|
| HC8 | first-order pulse time `t ~= C [(p-1) A_(p-1) + p A_p + (p+1) A_(p+1)] / (A_(p-1) + A_p + A_(p+1))` from the three samples around the peak `p` (the largest sample, the earliest on ties), then a pulse-asymmetry correction and an amplitude-dependent slewing term | approximate; for a pulse spread over three or four samples, not when consecutive bunch crossings give similar amplitudes in the same cell (anomalous pulse shape) | arXiv:0911.4877, sec. 3, eqs. 1-2, PDF pp. 5-6 |

The time structure has a prompt component (relativistic hadrons, electromagnetic subshowers from `pi0` and `eta`) and
a delayed one reaching microsecond scales, mainly from neutrons; the absorber sets the neutron yield and the hydrogen
content of the active medium the sensitivity to MeV neutrons (arXiv:1404.6454, sec. 1, PDF p. 5). The hadronic
response therefore depends on the electronics integration time (PDG RPP 2025 sec. 35.10.3, PDF p. 101).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Time per cell or cluster | sample-centroid time (HC8), pulse-shape and slewing corrections, per-channel offsets, out-of-time windows; simulation smeared to the measured time resolution | known pulse shape spread over three or four samples (HC8); offsets from beam, cosmic or calibration data; a measured time resolution for the smearing | late neutron energy outside the window changes the response; overlapping pulses | COL, FXT |
| Validating the hadronic model | compare data with at least two lists that differ in the model producing the observable, each list's model assignment stated at its Geant4 version: the inelastic model at the primary particle and energy for response, resolution, profiles and radial width ([Geant4 study protocol](geant4-study-protocol.md) sec. 6; `check_geant4_study.py variations` states only this model, from its table for QGSP_BIC and FTFP_BERT at Geant4 11.4.3 or from the run's probe, and gives other lists, an `_HP` variant included, as model unknown or as the same model); the neutron transport below 20 MeV for the time structure and late energy (for example an `_HP` variant; protocol sec. 3, rule `G4R-HP-NEUTRON`; arXiv:1404.6454, sec. 5.1, PDF p. 12), its assignment, like any for another list or Geant4 version, stated by hand from the list's constructors at that version; observables: response, resolution, the longitudinal profile from the shower start (per-event start, HC9 in the [main page](hadronic-calorimeter-reconstruction.md#relations); no benchmark yet, see Tool hooks), the radial width and the time structure | a model-independent observable and stated configuration; data not used in any tuning of the simulation | data or observables used to tune the simulation reused as validation; lists that differ only in EM, elastic or cross-section data, or share the model producing the observable | FXT, COL only (SPC: list selection and model systematic, UGD: tuning data, neither a validation point; GND, NUC: gap; coverage table) |

## Distinctive but generalizable features (timing and model validation)

- **Topology**: a prompt signal followed by sparse late hits from neutron scattering and capture.
- **Inverse problem**: the shower time from a few sampled amplitudes whose shape and size vary; for validation, which
  model component causes a data/simulation difference.
- **Natural objects**: pulse samples, cell times, cluster times, per-layer and radial profiles from the shower start.
- **Informative residual**: cell time minus a reference time against energy (slewing); data minus simulation per
  observable and energy.
- **Scaling**: the slewing correction grows as the pulse energy falls, up to the cap the source sets (HC8;
  arXiv:0911.4877, eq. 2 and the text after it); the delayed
  fraction grows with the absorber's neutron yield.
- **Conventions**: the time zero (bunch crossing in COL, beam counter in FXT, a cosmic or calibration reference) and
  the window; a physics list is named with its Geant4 version.
- **Tails**: late neutron hits, out-of-time overlaps; lists can agree on means and differ on widths and late energy (examples below).
- **Dependence**: integration time, absorber, active-medium hydrogen content, neutron transport precision.
- **Data sample**: tagged test beams (FXT); cosmic muons and beam data for synchronization (COL); data not used to
  tune the simulation for validation.
- **Transfers**: the estimator, the slewing form and the validation observables transfer; constants and list
  rankings do not.

## Common misconceptions and failure modes

- **One physics list called "validated".** Lists that agree on the mean response can differ on radial width, time
  structure or shower start; state which observable was tested.
- **Timing windows set from the electromagnetic pulse.** The delayed neutron component carries part of the
  hadronic signal; the window changes the response.
- **A tuned comparison read as validation.** Agreement on the data that tuned the simulation is not a validation
  point (the SPC and UGD entries of the coverage table below).

## Deliverables

- Time reconstruction: estimator, slewing and offset constants, window, and the simulation smearing that matches data.
- Validation: the observables, data sets and lists compared, and the model spread carried as a systematic.

## Tool hooks

**Hadronic benchmark in `geant4_benchmarks.py`** (planned):

- Inputs: per-layer mean deposits, per-event sums and per-hit deposits with transverse position (for the radius) from a
  Geant4 run of a stated configuration, plus per-hit times only if the planned tool adds the time structure, which
  stays outside it until then;
  a published test-beam data set with its uncertainties and apparatus description, and a measured configuration hash
  computed from a geometry built from that description.
- Outputs: the front-referenced longitudinal profile through the existing `longitudinal-profile` benchmark (`t_max`,
  the batch mean of Gamma-function fits to the per-layer mean deposits of each block, at fixed depths from the front),
  today the script's only `setup-matched` grade and evidence only against published data defined and fitted the same
  way, which the script does not check (it reads only the published alpha, beta, their uncertainties and a source):
  record the published fit's depth origin, depth unit, fit function (Gamma plus Q0) and range with their source pages,
  check them by hand against the run's fit, and justify `systematic_relative`, which the script does not cap, while a
  profile from the shower start needs per-event start alignment (HC9) and the published parametrisation, which the
  planned benchmark must add, recording the reference convention so that a start-referenced published fit is
  refused, before it is setup-matched evidence;
  mean response, resolution and mean shower radius as `published-data` comparisons (grade
  `interface`, handed to hep-statistics, never validation evidence) unless the planned tool adds setup-matched
  benchmarks for them.
- Negative control: a Geant4 run with an absorber thickness or density change of declared size (`injected_relative`,
  which the script checks in the control's run record only under `declared-size/1`, so until the planned benchmark
  adds that rule, check by hand that the control run differs from the nominal only by the declared absorber
  change), its expected shift fixed before the runs as under `declared-size/1` (today implemented, with
  `plan-controls`, only for three non-hadronic benchmarks, so the planned benchmark must add its expected-shift model),
  caught (its verdict fails) and at the claimed detection limit (|shift| <= 1.1 DL, DL =
  tolerance + |relative difference| + t SE of the shift, or under `declared-size/1` an expected shift within 1.5 x the
  planned limit), a control off the limit being a gap that blocks the upgrade. A physics-list swap is a model
  variation only when the two lists differ in the model producing the observable, the inelastic model at that
  particle and energy or the neutron transport below 20 MeV for the time structure and late energy (Methods row,
  [Geant4 study protocol](geant4-study-protocol.md) secs. 3 and 6), not a negative control.
  Controls run only for reference and setup-matched benchmarks.
- Statuses: labels from the script's `STATUSES`; `validated-in-scope` only from
  `check_geant4_study.py label --upgrade` (Geant4 study protocol section 7), never from
  `geant4_benchmarks.py run --status`, which echoes the label it is given: the upgrade needs a setup-matched
  benchmark with `validation_evidence` (a pass on an isolated target whose hash matches the measured configuration
  hash, every negative control caught, and the script only compares the two hashes, so a measured hash copied from
  the run proves nothing) plus a passed convergence gate, the declared scope inside the
  benchmark scope (whose particle and energy the script copies from the benchmark config, not from the run record,
  so check them against the run's gun by hand), a variation table (the script checks only that one is given: check
  by hand that at least one row is listed as a change of the model producing the observable), material inputs
  declared independent (`reference_origin`, a declaration the script does not verify) and no remaining gap;
  `failed` when its verdict fails or a control is not caught; otherwise `unvalidated`.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Shower timing | arxiv_0911.4877 | arxiv_1404.6454; pdg_2025_particle-detectors-at-accelerators | gap | gap | gap | gap |
| Physics-list validation points | arxiv_1203.1302 | arxiv_1412.2653; arxiv_1404.6454 | list selection and model systematic (arxiv_1909.12860), not an independent validation | tuning data (arxiv_1501.06431), not an independent validation | gap for Geant4 physics-list validation (air-shower hadronic interaction models, such as those behind the muon puzzle, are a different model family with no validation data set here: [extensive air showers](extensive-air-showers.md#the-muon-puzzle)) | gap |

Both techniques have at least two environments.

## Worked examples

<!-- example: shower timing (arXiv:0911.4877, arXiv:1404.6454, PDG RPP 2025) -->
CMS HCAL: time resolution about 1.2 ns for showers above 100 GeV in test beams; optical summing of layers limits
hadron timing to about 1 ns; the slewing correction is `(3.59 ns) log10(1 TeV / E)`, at most 10 ns; channels
synchronized within ±2 ns with cosmic and beam-splash data; simulation smeared to match the measured time resolution
(abstract and secs. 2.1, 3, 4.1, 4.2, PDF pp. 1, 5-6, 8-9).
CALICE T3B (15 SiPM tiles, 2.4 µs window): late energy is more
pronounced in tungsten than in steel; QGSP_BERT (Geant4 9.4p03, section 5, PDF page 12) overestimates late deposits
in tungsten for 60 GeV hadrons (section 4, PDF page 10), with the mean time of first hit too large by 2.0 ns at
9.2 cm and 7.8 ns at 40.2 cm, while QGSP_BERT_HP (high-precision neutrons below 20 MeV, otherwise identical to
QGSP_BERT) and QBBC (another slow-neutron treatment, and other inelastic models below 25 GeV: FTF, and the Binary
cascade for nucleons below 1.5 GeV, where QGSP_BERT uses LEP and Bertini, section 5.1, PDF page 12) agree,
overestimating it by only 1-2 ns beyond 10 cm (sec. 6.4
and sec. 7, PDF pp. 21-22). PDG RPP 2025 sec. 35.10.3 (PDF p. 102): in beam tests of a combined HGCAL prototype,
timing reached 60 ps per channel and better than 20 ps for full showers at the highest energies.
<!-- /example -->

<!-- example: physics-list validation points (arXiv:1412.2653) -->
CALICE Fe-AHCAL, 10-80 GeV: FTFP_BERT (Geant4 9.6.p01, section 2.2, PDF page 6) predicts the proton mean radius within
uncertainties and underestimates the pion radius by about 5-7%; QGSP_BERT (Geant4 9.6.p01) underestimates the width by
about 10% above 10 GeV (sec. 3, PDF p. 20).
<!-- /example -->

## Citations

The full entries are in this list, each with its DOI or arXiv id (the source IDs above are `arxiv_<id>` and
`pdg_2025_particle-detectors-at-accelerators`). Entries that name an apparatus sit in the example block.

- S. Navas et al. (Particle Data Group), "Particle detectors at accelerators", sec. 35.10.3 "Hadronic calorimeters" (revised August 2025 by F. Sefkow and F. Simon), in Review of Particle Physics, Phys. Rev. D 110 (2024) 030001 and 2025 update, DOI 10.1103/PhysRevD.110.030001, <https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-accel.pdf> (read 2026-11-20).

<!-- example: apparatus sources -->
- S. Chatrchyan et al. (CMS Collaboration), "Performance of CMS hadron calorimeter timing and synchronization using test beam, cosmic ray, and LHC beam data", JINST 5 (2010) T03013, DOI 10.1088/1748-0221/5/03/T03013, arXiv:0911.4877 (read 2026-11-20).
- ATLAS Collaboration, "Single hadron response measurement and calorimeter jet energy scale uncertainty with the ATLAS detector at the LHC", Eur. Phys. J. C 73 (2013) 2305, DOI 10.1140/epjc/s10052-013-2305-1, arXiv:1203.1302 (read 2026-11-20).
- C. Adloff et al. (CALICE Collaboration), "The time structure of hadronic showers in highly granular calorimeters with tungsten and steel absorbers", JINST 9 (2014) P07022, DOI 10.1088/1748-0221/9/07/P07022, arXiv:1404.6454 (read 2026-11-20).
- B. Bilki et al. (CALICE Collaboration), "Pion and proton showers in the CALICE scintillator-steel analogue hadron calorimeter", JINST 10 (2015) P04014, DOI 10.1088/1748-0221/10/04/P04014, arXiv:1412.2653 (read 2026-11-20).
- L. Aliaga et al. (MINERvA Collaboration), "MINERvA neutrino detector response measured with test beam data", Nucl. Instrum. Methods A 789 (2015) 28, DOI 10.1016/j.nima.2015.04.003, arXiv:1501.06431 (read 2026-11-20).
- Q. An et al. (DAMPE Collaboration), "Measurement of the cosmic-ray proton spectrum from 40 GeV to 100 TeV with the DAMPE satellite", Sci. Adv. 5 (2019) eaax3793, DOI 10.1126/sciadv.aax3793, arXiv:1909.12860 (read 2026-11-20).
<!-- /example -->
