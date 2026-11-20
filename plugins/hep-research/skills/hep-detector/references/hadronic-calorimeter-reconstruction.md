# Hadronic Calorimeter Reconstruction

How the energy, depth, time and quality of a hadronic shower are reconstructed: software compensation and dual
readout, the hadronic calibration chain, leakage, dead material and punch-through, shower timing, high-granularity
(imaging) hadronic calorimeters, and the observables that validate hadronic physics lists. The principles
(non-compensation, `e/h`, `pi/e`, the routes to compensation, containment) are in
[calorimetry](calorimetry-ecal-hcal.md#hadronic-showers-and-non-compensation) and are not repeated here; clustering
and particle flow are in [event reconstruction](event-reconstruction.md#clustering); physics-list choice is in
[detector simulation](detector-simulation.md#physics-lists-and-their-validity) and the
[Geant4 study protocol](geant4-study-protocol.md) (secs. 3 and 5). Fitting simulator parameters to hadronic data is
simcal, owned by hep-statistics; its HCAL specialization is [simulation-calibration/hcal](simulation-calibration/hcal.md).
Jet energy scale variations belong to hep-measurement
([systematics](../../hep-measurement/references/systematics.md)).

Environment codes (R1): COL collider; FXT fixed-target and test beam; SPC space and balloon; UGD underground,
neutrino and rare-event; GND ground-based arrays; NUC nuclear and low-energy. Content for one environment carries its
code. Named apparatus and every performance number sit in example blocks.

## Relations

Each relation gives its status, validity and source.

| # | Relation | Status and validity | Source |
|---|---|---|---|
| HC1 | `C = [f_em + (h/e)_C (1 - f_em)] E`, `S = [f_em + (h/e)_S (1 - f_em)] E`; `E = (xi S - C) / (xi - 1)`, `xi = [1 - (h/e)_C] / [1 - (h/e)_S]` | exact algebra of a linear two-component model; approximate as physics, since `(h/e)_C,S` are averages and leakage is ignored; useless as `xi -> 1` | PDG RPP 2025 sec. 35.10.3, eqs. 35.51-35.53 |
| HC2 | `f_em = [C/E - (h/e)_C] / [1 - (h/e)_C]` with `E` from HC1 | exact algebra of eq. 35.51 | same |
| HC3 | `E_corr = sum_i w(rho_i, E_raw) E_i` (local software compensation): a weight per cell from its energy density `rho_i = E_i / V_i`, lower for dense (electromagnetic) cells when `e/h > 1`; weights fitted on a sample of known energy by minimizing `sum_events (E_corr - E_beam)^2` | approximate (empirical); valid inside the training energy range and configuration; the raw energy selects the weight set | arXiv:1207.4210, sec. 3.1 and eq. 3.1, PDF pp. 13-14 |
| HC4 | `w_cell = P_EM w_em + (1 - P_EM) w_had` for every calibration step of a cluster | exact as a definition; `P_EM` and the weights come from single-particle simulation, so they are only as good as its modelling of the moments used | arXiv:1603.02934, sec. 5.1, eq. 29, PDF p. 30 |
| HC5 | `<E/p> = <E/p>_raw - k <E/p>_BG`, `k = R2^2 / (R2^2 - R1^2)` when the neutral background is measured in an annulus `R1 < Delta R < R2` | exact geometric factor if the background density is uniform in the cone; the uniformity is an assumption to validate | arXiv:1203.1302, sec. 3.5, eqs. 2-3, PDF p. 6 |
| HC6 | `N_dep,i = sum_j M_ij N_inc,j`, `M_ij` the probability that an event of incident-energy bin `j` deposits in bin `i` | exact definition of the response; `M` from simulation carries the hadronic-model dependence | arXiv:1909.12860, Materials and Methods eq. 2, PDF p. 11; see [response and forward folding](response-and-forward-folding.md) |
| HC7 | fractional leakage per event `(E_total - E_contained) / E_total`, with `E_total` including a rear tail catcher | exact definition; a lower bound on the true leakage if the catcher itself leaks | arXiv:1201.1653, sec. 5, PDF p. 21 |
| HC8 | first-order pulse time `t ~= C [(p-1) A_(p-1) + p A_p + (p+1) A_(p+1)] / (A_(p-1) + A_p + A_(p+1))` from the three samples around the peak `p`, then a pulse-asymmetry correction and an amplitude-dependent slewing term | approximate; for a pulse spread over three or four samples, not for overlapping pulses from neighbouring readout windows | arXiv:0911.4877, sec. 3, eqs. 1-2, PDF pp. 5-6 |
| HC9 | `R_i = sum_(l=i)^(i+2) E_l(r < r_core) / sum_(l=i)^(i+2) E_l(r < r_halo)`: near 1 along a minimum-ionizing track, smaller after the first hadronic interaction | exact as a definition; the shower start is the first layer passing multiplicity, energy and `R_i` thresholds tuned on simulation | arXiv:2211.04740, sec. 4, eq. 4.1 |

The mean shower depth from the front face is the shower-start distribution convolved with the profile measured from
the shower start, so detecting the start allows a per-event leakage estimate and a sharper model test (PDG RPP 2025
sec. 35.10.3, PDF p. 98). The hadronic response depends on the electronics integration time through the delayed
neutron component (same section, PDF p. 101).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Non-compensating HCAL with longitudinal segmentation | offline (longitudinal or amplitude) weighting | segmentation that separates early dense deposits; a sample of known energy | weights tuned on simulation inherit its `f_em` modelling | COL, FXT |
| Highly granular HCAL | local (per-cell density bins) or global (per-event, from the hit-energy spectrum) software compensation; machine-learned variants | cell-level density; training and test samples statistically independent; a weight set per energy range | bins with too few hits; weights extrapolated outside the training range; train/test overlap | FXT (COL in construction) |
| Collider clusters in a non-compensating system | EM/HAD classification, then cell weights, out-of-cluster and dead-material corrections, each as blended weights (HC4) | single-pion simulation that models the cluster moments used | misclassified small clusters; corrections that hide data/MC differences | COL |
| Two optical signals per cell | dual readout (HC1-HC2) | known `(h/e)_C`, `(h/e)_S`, with `xi` well away from 1 | lateral leakage in small modules; `xi` near 1 amplifies noise | FXT (prototypes) |
| Setting the hadronic scale | EM scale; MIP or muon equalization of cells; test-beam hadron response; in-situ isolated-track `E/p` (HC5); transfer of test-beam constants to the installed detector | the same electronics or a measured transfer; a tracker momentum scale | `E/p` reach limited to low momenta; beyond the test-beam range only extrapolation is left; `E/p` shifts that are tracker effects | COL, FXT, UGD, SPC |
| Calorimeter much shallower than the shower | unfolding the deposited energy with a simulated response (HC6) | a response validated on beam tests and on-orbit or in-situ shower profiles | model dependence dominates the systematic; the prior spectrum biases the unfolding | SPC; GND via [fluorescence detectors](ground-based-detection-arrays.md#fluorescence-detectors) |
| Rear leakage and punch-through | tail catcher or extra instrumented depth; leakage corrections binned in energy, direction and cluster depth; shower-start-based correction | depth beyond the absorber instrumented, or simulation of the leakage tail | low-side tail not described by a Gaussian; punch-through mistaken for muons | COL, FXT, SPC |
| Time per cell or cluster | sample-centroid time (HC8), pulse-shape and slewing corrections, per-channel offsets, out-of-time windows | known pulse shape; offsets from beam, cosmic or calibration data | late neutron energy outside the window changes the response; overlapping pulses | COL, FXT |
| Validating the hadronic model | compare data and several lists on the observables of the ten-item block | a model-independent observable and stated configuration | tuning on the same observable used for validation | FXT, COL, UGD, SPC |

## Distinctive but generalizable features (hadronic calorimeter)

- **Topology**: lumpy showers with dense electromagnetic cores from `pi0` and `eta` decays and sparse hadronic
  activity with minimum-ionizing tracks (PDG RPP 2025 sec. 35.10.3, PDF p. 98).
- **Inverse problem**: incident energy from visible energy when invisible energy and `f_em` fluctuate event to event;
  degenerate with leakage and dead material.
- **Natural objects**: cells, topological clusters, shower start, track segments inside showers, tail-catcher sums.
- **Informative residual**: `E/p` of isolated tracks against momentum and direction; reconstructed minus beam energy
  in test beams; the depth fraction of the energy at the highest energies (rear leakage).
- **Scaling**: `f_em` rises with energy, so the response is non-linear unless compensated; leakage grows with energy.
- **Conventions**: the EM scale is the reference; the resolution parametrization letters differ between sources
  ([calorimetry](calorimetry-ecal-hcal.md#the-resolution-decomposition)); incident protons have a larger mean
  hadronic fraction than pions (leading particle), so their responses differ (PDG RPP 2025 sec. 35.10.3, PDF p. 99).
- **Tails**: low-side tails from leakage and late showers; high-side from overlapping or out-of-time deposits.
  The resolution-shape models are in
  [performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md#resolution-models-and-widths).
- **Dependence**: integration time, absorber (neutron yield), active medium (hydrogen content), radiation damage of
  photosensors and scintillator ([calibration and alignment](calibration-and-alignment.md#time-dependence-and-conditions-data),
  [photosensors](cherenkov-imaging-variants-and-photosensors.md)).
- **Data sample**: tagged test beams (FXT) for the absolute response; isolated tracks and muons in situ (COL);
  cosmic-ray muons for cell and detector equalization (UGD, COL); MIP signals on orbit (SPC).
- **Transfers**: the density-weighting idea, the shower-start convolution and the response-matrix treatment transfer
  between environments; specific weights, thresholds and physics-list rankings do not.

## Common misconceptions and failure modes

- **One hadronic scale for every particle.** Pions, protons and neutral hadrons respond differently; an `E/p`
  measured for charged pions does not cover neutrons.
- **Software compensation weights as constants.** They depend on energy and configuration; a weight set trained in a
  test beam is a starting point in another detector, not a calibration.
- **Validation on the training sample.** Weights, `P_EM` maps or a learned regression evaluated on the events that
  fitted them overstate the gain.
- **Leakage absorbed into the constant term.** Leakage grows with energy and gives a low-side tail; correct or model
  it per event.
- **Punch-through counted as muons.** Hadronic remnants behind the absorber fake muon hits
  ([muon systems](muon-systems.md), [particle identification](particle-identification.md)).
- **Test-beam constants carried over unchanged.** Electronics, integration time and magnetic field differ in the
  installed detector; measure the transfer.
- **One physics list called "validated".** Lists that agree on the mean response can differ on radial width, time
  structure or shower start; state which observable was tested.
- **Timing windows set from the electromagnetic pulse.** The delayed neutron component carries part of the
  hadronic signal; the window changes the response.

## Deliverables

- Calorimeter depth in `lambda_I`, tail-catcher depth, granularity, absorber and active medium, readout integration time.
- The calibration chain in order, with each step's reference sample and energy range, and what is extrapolated.
- The compensation method (none, offline weighting, local or global, dual readout, learned), the training sample, and
  the energy range where it was validated.
- Leakage and dead-material corrections with their binning, and the leakage tail in the resolution model.
- Time reconstruction: estimator, slewing and offset constants, window, and the simulation smearing that matches data.
- Validation: the observables, data sets and lists compared, and the model spread carried as a systematic.

## Tool hooks

**Software-compensation weight fit and validation** (a planned tool), on cell-level products of the `calo-cluster`
adapter or equivalent CSV:

- Inputs: per-event cell energies (GeV, EM scale) and volumes (cm^3), a reference energy per event (beam energy or a
  stated proxy), the density-bin edges (GeV/cm^3), energy ranges for the weight sets, a split key that separates
  training from test events.
- Outputs: weights per (density bin, energy range) with uncertainties; resolution and linearity before and after on
  the test split; a three-term resolution fit through `calorimeter_resolution.py`.
- Conventions: weights multiply EM-scale cell energies; density is energy per absorber volume; letters of the
  resolution terms as in [calorimetry](calorimetry-ecal-hcal.md#the-resolution-decomposition).
- Negative control: a sample generated with a single electromagnetic and hadronic response (`e/h = 1`) must give weights
  flat in density within their errors and no resolution gain; a train/test overlap must be refused.
- Statuses: `synthetic` on generated input, `unvalidated` on data without a qualifying benchmark, `failed` when a bin is
  empty or a weight is unconstrained, `outside-validated-range` when the reference energy leaves the trained range.

**Hadronic benchmark in `geant4_benchmarks.py`** (planned):

- Inputs: per-layer mean deposits and per-event sums from a Geant4 run of a stated configuration; a published test-beam
  data set with its uncertainties, apparatus description and configuration hash.
- Outputs: mean response, resolution, longitudinal profile from the shower start, mean shower radius, each against the
  published value, as `setup-matched` only when the configuration hash matches, otherwise `published-data`
  (interface).
- Negative control: a run with a deliberately different absorber thickness or physics list must be detected at the
  stated detection limit.
- Statuses: the script's `STATUSES`; `validated-in-scope` only with a matching configuration and a caught negative
  control, otherwise `unvalidated`.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Software compensation, dual readout | arxiv_1603.02934; pdg_2025_particle-detectors-at-accelerators | arxiv_1207.4210 | gap | gap | gap | gap |
| Hadronic calibration chain | arxiv_1203.1302 | arxiv_hep-ex_0007045 | arxiv_1909.12860 | arxiv_0805.3170; arxiv_1501.06431 | [fluorescence detectors](ground-based-detection-arrays.md#fluorescence-detectors) | gap |
| Leakage, dead material, punch-through | arxiv_1603.02934; arxiv_1806.02129 | arxiv_hep-ex_0007045; arxiv_1201.1653; doi_10.1007_BF01650426 | arxiv_1909.12860 | gap | [fluorescence detectors](ground-based-detection-arrays.md#fluorescence-detectors) (invisible energy) | gap |
| Shower timing | arxiv_0911.4877; pdg_2025_particle-detectors-at-accelerators | arxiv_1404.6454 | gap | gap | gap | gap |
| High-granularity HCAL | pdg_2025_particle-detectors-at-accelerators (in construction, none operated) | arxiv_1702.08082; arxiv_2211.04740; arxiv_1412.2653 | gap | gap | gap | gap |
| Physics-list validation points | arxiv_1203.1302 | arxiv_1412.2653; arxiv_1404.6454 | arxiv_1909.12860 | arxiv_1501.06431 | [extensive air showers](extensive-air-showers.md) (hadronic-model dependence) | gap |

Every technique has at least two environments. High-granularity hadronic calorimetry has been operated only in test
beams; the collider entry is a detector under construction.

## Worked examples

<!-- example: software compensation in the CALICE scintillator-steel AHCAL (arXiv:1207.4210) -->
CALICE AHCAL, 38 layers of 5 mm scintillator tiles separated by 21 mm of steel, 5.3 `lambda_I`, CERN SPS H6, charged
pions 10-80 GeV (sec. 2.1, PDF pp. 5-6).
Weights per energy-density bin follow `w = p0 + p1 exp(p2 rho)` (eq. 3.2, PDF p. 13), fitted on half the data and
tested on the other half (PDF pp. 12-13). Stochastic term: uncorrected (57.6 ± 0.4)%, global compensation
(45.8 ± 0.3)%, local compensation (44.3 ± 0.3)%; constant terms 1.6-1.8% (Fig. 4 caption, PDF p. 11). PDG RPP 2025
sec. 35.10.3 (PDF pp. 102-103) reports earlier offline weighting for CDHS (10% at 10 GeV to 30% at 140 GeV
improvement), H1 (51%/sqrt(E)) and the ATLAS endcap (84%/sqrt(E)), and dual readout in DREAM/RD52 with `xi` about 3
and 70%/sqrt(E) for single hadrons, including lateral leakage.
<!-- /example -->

<!-- example: hadronic calibration chain of the ATLAS calorimeters (arXiv:1203.1302, arXiv:1603.02934) -->
ATLAS LCW: EM/HAD classification, cell weighting, out-of-cluster and dead-material corrections derived from
single-pion simulation (1603.02934 sec. 5.1, PDF pp. 29-30); the longitudinal-leakage correction applies to clusters
reaching the last hadronic layer, binned in cluster `eta`, `log10(E)` and depth (sec. 5.5, eq. 39, PDF p. 41).
Isolated-track `E/p` at `sqrt(s)` = 0.9 and 7 TeV reaches about 30 GeV; data and simulation agree within about 2%
for 1-10 GeV and about 5% for 10-30 GeV (1203.1302 sec. 3.6, PDF p. 6). Above that, combined test-beam pions of
20-350 GeV are used, and above 400 GeV a 10% uncertainty is added because no test-beam or in-situ measurement
exists (sec. 5.2.1, PDF pp. 16-17). The TileCal scale comes from minimum-ionizing muons (sec. 5.2.2, PDF p. 17).
<!-- /example -->

<!-- example: calibration chains outside colliders (arXiv:0805.3170, arXiv:1501.06431, arXiv:1909.12860) -->
MINOS (UGD): a 60-plane calibration detector measured responses in CERN PS beams with both readout electronics; the
three detectors were normalized to each other with cosmic-ray muons (0805.3170 sec. 1, PDF p. 9). MINERvA (UGD): a
scaled replica in a 0.35-2.0 GeV/c test beam measured proton, pion and electron response and the Birks parameter;
simulation agrees better than 4% for the calorimetric response (1501.06431 abstract, PDF p. 2). DAMPE (SPC): a BGO
calorimeter of about 1.6 `lambda_I`; on-orbit calibration with MIP signals per crystal, energy by Bayesian unfolding
with a simulated response matrix (Materials and Methods, PDF p. 11); the hadronic-model systematic on the proton flux
is about 7% below 400 GeV and 7-10% above, from FTFP_BERT against FLUKA (PDF p. 13).
<!-- /example -->

<!-- example: leakage and punch-through (arXiv:hep-ex/0007045, arXiv:1201.1653, arXiv:1806.02129, RD5) -->
CMS HCAL prototype (H4 1995, about 8 `lambda_I`): pion response rises about 9% from 15 to 375 GeV/c; the estimated
leakage correction is 1.5% at 120 GeV/c and 3.5% at 375 GeV/c (sec. 7, PDF p. 27). Profiles extend beyond
7 `lambda_I`; with the outer tail catcher HO behind the coil the barrel reaches 9.5 `lambda_I` and fewer than 2% of
300 GeV/c pions are catastrophically mismeasured (sec. 7.3, PDF p. 34). CALICE TCMT, with the system defined as the first
5.9 `lambda_I` (ECAL, AHCAL, seven TCMT layers) and the last nine TCMT layers measuring the leakage: mean leakage 0.032 ± 0.002 (10 GeV) and 0.076 ± 0.001 (80 GeV); fraction of events above 10% leakage 0.030 and 0.061
(Table 3, PDF p. 21). ATLAS TileCal: a drop of the TileCal energy fraction for jets above 1800 GeV in the barrel
signals rear leakage (1806.02129 sec. 6.2.2, PDF p. 44). RD5 measured the total punch-through probability of pion
showers at 30-300 GeV/c in iron up to 5.3 m equivalent (Z. Phys. C 60 (1993) 1, abstract only).
<!-- /example -->

<!-- example: shower timing (arXiv:0911.4877, arXiv:1404.6454, PDG RPP 2025) -->
CMS HCAL: time resolution about 1.2 ns for showers above 100 GeV in test beams; optical summing of layers limits
hadron timing to about 1 ns; the slewing correction is `(3.59 ns) log10(1 TeV / E)`, at most 10 ns; channels
synchronized within ±2 ns with cosmic and beam-splash data; simulation smeared to match the measured time resolution
(abstract and secs. 2.1, 3, 4.1, PDF pp. 1, 5-6, 8). CALICE T3B (15 SiPM tiles, 2.4 µs window): late energy is more
pronounced in tungsten than in steel; QGSP_BERT overestimates late deposits in tungsten (mean time of first hit too
large by 2.0 ns at 9.2 cm and 7.8 ns at 40.2 cm), while lists with high-precision neutron treatment agree (sec. 6.4
and sec. 7, PDF pp. 21-22). PDG RPP 2025 sec. 35.10.3 (PDF p. 102): an HGCAL prototype reached 60 ps per channel and
better than 20 ps for full showers at the highest energies.
<!-- /example -->

<!-- example: high-granularity HCALs and validation points (arXiv:1702.08082, arXiv:2211.04740, arXiv:1412.2653) -->
CALICE SDHCAL: track segments inside showers, found with a Hough transform, calibrate the active layers in situ,
improve the energy and separate hadronic from electromagnetic showers (abstract, PDF p. 3). CMS HGCAL prototype with
CALICE AHCAL, CERN SPS H2, pions 20-300 GeV: shower start from layer multiplicity, energy within 10 cm and
`R_i < 0.96` with 2 cm and 10 cm radii; energy within 10 cm above 12 MIPs at 20 GeV and 40 MIPs at 200 GeV (sec. 4).
CALICE Fe-AHCAL, 10-80 GeV: FTFP_BERT predicts the proton mean radius within uncertainties and underestimates the pion
radius by about 5-7%; QGSP_BERT underestimates the width by about 10% above 10 GeV (sec. 3, PDF p. 20).
<!-- /example -->

## Citations

Full entries are in the [annotated bibliography](detector-principles-bibliography.md) (calorimetry sources). Source
IDs used above: `pdg_2025_particle-detectors-at-accelerators` (DOI 10.1103/PhysRevD.110.030001, 2025 update),
arXiv:1207.4210, 1603.02934, 1203.1302, hep-ex/0007045, 0805.3170, 1501.06431, 1909.12860, 1201.1653, 1806.02129,
1404.6454, 0911.4877, 1702.08082, 2211.04740, 1412.2653, and DOI 10.1007/BF01650426 (abstract only, cited for the
existence of the measurement).
