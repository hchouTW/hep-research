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
| HC8 | first-order pulse time `t ~= C [(p-1) A_(p-1) + p A_p + (p+1) A_(p+1)] / (A_(p-1) + A_p + A_(p+1))` from the three samples around the peak `p`, then a pulse-asymmetry correction and an amplitude-dependent slewing term | approximate; for a pulse spread over three or four samples, not when consecutive bunch crossings give similar amplitudes in the same cell (anomalous pulse shape) | arXiv:0911.4877, sec. 3, eqs. 1-2, PDF pp. 5-6 |

The time structure has a prompt component (relativistic hadrons, electromagnetic subshowers from `pi0` and `eta`) and
a delayed one reaching microsecond scales, mainly from neutrons; the absorber sets the neutron yield and the hydrogen
content of the active medium the sensitivity to MeV neutrons (arXiv:1404.6454, sec. 1, PDF p. 5). The hadronic
response therefore depends on the electronics integration time (PDG RPP 2025 sec. 35.10.3, PDF p. 101).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Time per cell or cluster | sample-centroid time (HC8), pulse-shape and slewing corrections, per-channel offsets, out-of-time windows; simulation smeared to the measured time resolution | known pulse shape spread over three or four samples (HC8); offsets from beam, cosmic or calibration data; a measured time resolution for the smearing | late neutron energy outside the window changes the response; overlapping pulses | COL, FXT |
| Validating the hadronic model | compare data with several lists that differ in the model at the particle and energy concerned ([Geant4 study protocol](geant4-study-protocol.md) sec. 6) on response, resolution, the longitudinal profile from the shower start, the radial width and the time structure | a model-independent observable and stated configuration; data not used to tune the simulation | tuning on the same observable used for validation; lists that share the model at that energy | FXT, COL, UGD (tuning data only), SPC |

## Distinctive but generalizable features (timing and model validation)

- **Topology**: a prompt signal followed by sparse late hits from neutron scattering and capture.
- **Inverse problem**: the shower time from a few sampled amplitudes whose shape and size vary; for validation, which
  model component causes a data/simulation difference.
- **Natural objects**: pulse samples, cell times, cluster times, per-layer and radial profiles from the shower start.
- **Informative residual**: cell time minus a reference time against energy (slewing); data minus simulation per
  observable and energy.
- **Scaling**: the slewing correction grows as the pulse energy falls (HC8; arXiv:0911.4877, eq. 2); the delayed
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
  point (the UGD entry of the coverage table below).

## Deliverables

- Time reconstruction: estimator, slewing and offset constants, window, and the simulation smearing that matches data.
- Validation: the observables, data sets and lists compared, and the model spread carried as a systematic.

## Tool hooks

**Hadronic benchmark in `geant4_benchmarks.py`** (planned):

- Inputs: per-layer mean deposits and per-event sums from a Geant4 run of a stated configuration; a published test-beam
  data set with its uncertainties, apparatus description and configuration hash.
- Outputs: the longitudinal profile through the existing `longitudinal-profile` benchmark, today the script's only
  `setup-matched` grade; mean response, resolution and mean shower radius as `published-data` comparisons (grade
  `interface`, handed to hep-statistics, never validation evidence) unless the planned tool adds setup-matched
  benchmarks for them.
- Negative control: a Geant4 run with an absorber thickness or density change of declared size (`injected_relative`,
  checked in the control's run record), its expected shift fixed before the runs as under `declared-size/1` (today
  implemented, with `plan-controls`, only for three non-hadronic benchmarks, so the planned benchmark must add its
  expected-shift model), caught at the detection limit the script computes (tolerance + |relative difference| +
  t SE of the shift). A physics-list swap is a model variation ([Geant4 study protocol](geant4-study-protocol.md)
  sec. 6), not a negative control. Controls run only for reference and setup-matched benchmarks.
- Statuses: labels from the script's `STATUSES`; `validated-in-scope` only when a setup-matched benchmark passes on an
  isolated target with a matching configuration hash and every negative control is caught (the script's
  `validation_evidence`); `failed` when its verdict fails or a control is not caught; otherwise `unvalidated`.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Shower timing | arxiv_0911.4877 | arxiv_1404.6454; pdg_2025_particle-detectors-at-accelerators | gap | gap | gap | gap |
| Physics-list validation points | arxiv_1203.1302 | arxiv_1412.2653; arxiv_1404.6454 | arxiv_1909.12860 | tuning data (arxiv_1501.06431), not an independent validation | [extensive air showers](extensive-air-showers.md) (hadronic-model dependence) | gap |

Both techniques have at least two environments.

## Worked examples

<!-- example: shower timing (arXiv:0911.4877, arXiv:1404.6454, PDG RPP 2025) -->
CMS HCAL: time resolution about 1.2 ns for showers above 100 GeV in test beams; optical summing of layers limits
hadron timing to about 1 ns; the slewing correction is `(3.59 ns) log10(1 TeV / E)`, at most 10 ns; channels
synchronized within ±2 ns with cosmic and beam-splash data; simulation smeared to match the measured time resolution
(abstract and secs. 2.1, 3, 4.1, PDF pp. 1, 5-6, 8). CALICE T3B (15 SiPM tiles, 2.4 µs window): late energy is more
pronounced in tungsten than in steel; QGSP_BERT overestimates late deposits in tungsten (mean time of first hit too
large by 2.0 ns at 9.2 cm and 7.8 ns at 40.2 cm), while lists with high-precision neutron treatment agree (sec. 6.4
and sec. 7, PDF pp. 21-22). PDG RPP 2025 sec. 35.10.3 (PDF p. 102): in beam tests of a combined HGCAL prototype,
timing reached 60 ps per channel and better than 20 ps for full showers at the highest energies.
<!-- /example -->

<!-- example: physics-list validation points (arXiv:1412.2653) -->
CALICE Fe-AHCAL, 10-80 GeV: FTFP_BERT predicts the proton mean radius within uncertainties and underestimates the pion
radius by about 5-7%; QGSP_BERT underestimates the width by about 10% above 10 GeV (sec. 3, PDF p. 20).
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
