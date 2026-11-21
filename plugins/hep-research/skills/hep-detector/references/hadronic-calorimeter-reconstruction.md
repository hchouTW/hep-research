# Hadronic Calorimeter Reconstruction

How the energy, depth and quality of a hadronic shower are reconstructed: software compensation and dual readout,
the hadronic calibration chain, leakage, dead material and punch-through, and high-granularity (imaging) HCALs.
Timing and physics-list validation are in the [companion](hadronic-calorimeter-timing-and-model-validation.md).
Not repeated here: the principles in
[calorimetry](calorimetry-ecal-hcal.md#hadronic-showers-and-non-compensation) and its
[containment section](calorimetry-ecal-hcal.md#leakage-dead-material-and-containment); clustering and particle flow
in [event reconstruction](event-reconstruction.md#clustering);
physics lists in [detector simulation](detector-simulation.md#physics-lists-and-their-validity) and the
[Geant4 study protocol](geant4-study-protocol.md) (secs. 3, 5, 6). Fitting simulator parameters to data is
simcal (hep-statistics; HCAL: [simulation-calibration/hcal](simulation-calibration/hcal.md)).

Environment codes ([comparison tables](detector-comparison-tables.md)): COL collider; FXT fixed target and test beam;
SPC space and balloon; UGD underground, neutrino and rare-event; GND ground-based arrays; NUC nuclear and low-energy.

## Relations

Each relation gives its status, validity and source.

| # | Relation | Status and validity | Source |
|---|---|---|---|
| HC1 | `C = [f_em + (h/e)_C (1 - f_em)] E`, `S = [f_em + (h/e)_S (1 - f_em)] E`; `E = (xi S - C) / (xi - 1)`, `xi = [1 - (h/e)_C] / [1 - (h/e)_S]` | exact algebra of a linear two-component model; approximate as physics, since `(h/e)_C,S` are averages and leakage is ignored; useless as `xi -> 1` | PDG RPP 2025 sec. 35.10.3, eqs. 35.51-35.53 |
| HC2 | `f_em = [C/E - (h/e)_C] / [1 - (h/e)_C]` with `E` from HC1 | exact algebra of eq. 35.51 | same |
| HC3 | `E_LC = E_ECAL^track + (e/pi) [sum_i w(rho_i, E_raw) E_HCAL,i + E_TCMT]` (local software compensation, eq. 3.1): weights on the hadronic-section hits only; the ECAL energy of the incoming track (eq. 2.1, PDF p. 8) and the tail catcher unweighted; `rho_i = E_HCAL,i / V_i`, `V_i` the cell volume (sec. 3.1; the Fig. 5 caption calls it the absorber volume); weights lower for dense (electromagnetic) cells when `e/h > 1`, fitted on a sample of known energy by minimizing `sum_events (E_LC - E_beam)^2` | approximate (empirical); valid inside the training energy range and configuration, for events selected as in training (shower start in the first hadronic layers, so the ECAL holds only the incoming track; example below); in application the uncorrected reconstructed energy `E_raw`, not the beam energy, selects the weight set | arXiv:1207.4210, secs. 2.2, 3.1, eq. 3.1, Fig. 5, PDF pp. 8, 13-14 |
| HC4 | `w_cell = P_EM w_em + (1 - P_EM) w_had` for every calibration step of a cluster | exact as a definition; `P_EM` and the weights come from single-pion (charged and neutral) simulation over a stated energy and `eta` range (example below), so they are only as good as its modelling of the moments used; lookup tables binned in the cluster EM-scale energy with other moments give them (`P_EM`: cluster `eta`, density, depth, sec. 5.2, eq. 30, PDF p. 33; hadronic weights: sampling layer, cell `eta`, cell density, sec. 5.3, eq. 34, PDF p. 36) | arXiv:1603.02934, secs. 5.1-5.3, eqs. 29 (PDF p. 30), 30, 34 |
| HC5 | `<E/p> = <E/p>_raw - k <E/p>_BG`, `k = R2^2 / (R2^2 - R1^2)` when the neutral background is measured in an annulus `R1 < Delta R < R2` and `E` is summed in a cone of radius `R2` | exact geometric factor if the background density is uniform in the cone and independent of the track's deposit (both to validate); `<E/p>_BG` is measured in the EM section only, on late-showering tracks (minimum-ionizing there, so the annulus holds no track shower; cuts below), once the hadronic-section neutral background is shown negligible, and subtracted from `<E/p>_raw` of all isolated tracks | arXiv:1203.1302, secs. 3.3, 3.5, eqs. 1-3, PDF pp. 4-6 |
| HC6 | `N_dep,i = sum_j M_ij N_inc,j`, `M_ij` the probability that an event of incident-energy bin `j` deposits in bin `i` | exact definition of the response; `M` from simulation carries the hadronic-model dependence | arXiv:1909.12860, Materials and Methods eq. 2, PDF p. 11; see [response and forward folding](response-and-forward-folding.md) |
| HC7 | fractional leakage per event `(E_total - E_contained) / E_total`, with `E_total` including a rear tail catcher | exact definition; a lower bound on the true leakage if the catcher itself leaks | arXiv:1201.1653, sec. 5, PDF p. 21 |
| HC9 ([HC8](hadronic-calorimeter-timing-and-model-validation.md#relations): companion) | `R_i = sum_(l=i)^(i+2) E_l(r < r_core) / sum_(l=i)^(i+2) E_l(r < r_halo)`: near 1 along a minimum-ionizing track, smaller after the first hadronic interaction | exact as a definition; the shower start is the first layer passing multiplicity, energy and `R_i` thresholds tuned on simulation; the energy threshold rises with beam energy, tuned for one prototype's pion beam range (example below); without a beam energy, an estimate independent of the start decision (such as `E_raw`, HC3) selects it inside the tuned range; between tuned energies the threshold follows a stated interpolation, and the start efficiency (events found within a stated number of layers of the true start) meets a stated requirement in simulation | arXiv:2211.04740, sec. 4, eq. 4.1, PDF pp. 17-18 |

The mean longitudinal profile from the front face is the shower-start distribution convolved with the profile from the
start, so finding the start allows a per-event leakage estimate and a sharper model test (PDG RPP 2025
sec. 35.10.3, PDF p. 98).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Non-compensating HCAL with longitudinal segmentation | offline (longitudinal or amplitude) weighting | segmentation that separates early dense deposits; a sample of known energy | weights tuned on simulation inherit its `f_em` modelling | COL, FXT |
| Highly granular HCAL | local (per-cell density bins) or global (per-event, from the hit-energy spectrum) software compensation; machine-learned variants | cell-level density; training and test samples statistically independent; a weight set per energy range | bins with too few hits; weights extrapolated outside the training range; train/test overlap | FXT (COL in construction) |
| Collider clusters in a non-compensating system | EM/HAD classification, then cell weights, out-of-cluster and dead-material corrections, each as blended weights (HC4) | single-pion simulation whose cluster moments match data within a stated criterion (data/MC moment distributions), checked in data over the cluster energies, directions and hadron species calibrated (isolated-track `E/p` for charged hadrons, HC5; test beams above); beyond, and for neutral hadrons, an extrapolation uncertainty sized by a stated method that covers at least the alternative-model spread (example below) | misclassified small clusters; corrections that hide data/MC differences | COL |
| Two optical signals per cell | dual readout (HC1-HC2) | known `(h/e)_C`, `(h/e)_S`; the S and C fluctuations, amplified by `xi/(xi - 1)` and `1/(xi - 1)` (HC1), shown smaller than the `f_em` fluctuation they remove; a steep `xi` needs a nearly compensating scintillator readout, which leaves less to gain (PDG RPP 2025 sec. 35.10.3, PDF p. 103) | lateral leakage in small modules; `xi` near 1 | FXT (prototypes) |
| Setting the hadronic scale | EM scale; MIP or muon equalization of cells; test-beam hadron response; in-situ isolated-track `E/p` (HC5); transfer of test-beam constants to the installed detector | the same electronics or a measured transfer; a tracker momentum scale independent of the calorimeter; reference samples of the species calibrated, or a measured species difference | `E/p` reach limited to low momenta; `E/p` shifts that are tracker effects | COL, FXT, UGD, SPC |
| Calorimeter much shallower than the shower | unfolding the deposited energy with a simulated response (HC6) | a response checked against beam tests and on-orbit or in-situ profiles at listed energies, each with its agreement criterion (companion example); below, between and above them, only an envelope of two hadronic models (physics lists, or another transport code with a stated model assignment) that differ at each of those energies for the particle family (`check_geant4_study.py variations` with `observable.domain` `hadronic`, [protocol](geant4-study-protocol.md) sec. 6), stated as such | model dependence dominates the systematic; the prior spectrum biases the unfolding | SPC only (GND: see the coverage table) |
| Rear leakage and punch-through | tail catcher or extra instrumented depth; leakage corrections binned in energy, direction and cluster depth; shower-start-based correction | depth beyond the absorber instrumented, simulation of the leakage tail, or containment-versus-depth data of a comparable absorber; the correction's uncertainty stated | low-side tail not described by a Gaussian; punch-through mistaken for muons | COL, FXT, SPC |

## Distinctive but generalizable features (hadronic calorimeter)

- **Topology**: lumpy showers with dense electromagnetic cores from `pi0` and `eta` decays and sparse hadronic
  activity with minimum-ionizing tracks (PDG RPP 2025 sec. 35.10.3, PDF p. 98).
- **Inverse problem**: incident from visible energy when invisible energy and `f_em` fluctuate per event; degenerate
  with leakage and dead material.
- **Natural objects**: cells, clusters, shower start, track segments in showers, tail-catcher sums.
- **Informative residual**: `E/p` of isolated tracks against momentum and direction; reconstructed minus beam energy
  in test beams; the energy's depth fraction at the highest energies (rear leakage).
- **Scaling**: `f_em` rises with energy, so the response is non-linear unless compensated; leakage grows with energy.
- **Conventions**: the EM scale is the reference; protons have a larger mean
  hadronic fraction than pions (leading particle) and respond differently (PDG RPP 2025 sec. 35.10.3, PDF p. 99).
- **Tails**: low-side from leakage and late showers; high-side from overlapping or out-of-time deposits and, for
  `e/h > 1` without compensation, `f_em` fluctuations.
- **Dependence**: integration time, absorber (neutron yield), active medium (hydrogen content), radiation damage of
  the sensors ([calibration and alignment](calibration-and-alignment.md#time-dependence-and-conditions-data)).
- **Data sample**: tagged test beams (FXT) for the absolute response; isolated tracks and muons in situ (COL);
  cosmic-ray muons for cell and detector equalization (UGD, COL); MIP signals on orbit (SPC).
- **Transfers**: the density-weighting idea, the shower-start convolution and the response-matrix treatment transfer
  between environments; specific weights, thresholds and physics-list rankings do not.

## Common misconceptions and failure modes

- **One hadronic scale for every particle.** Pions, protons and neutral hadrons respond differently; an `E/p`
  measured for charged pions does not cover neutrons.
- **Validation on the training sample.** Weights or `P_EM` maps tested on the events that fitted them overstate the
  gain.
- **Punch-through counted as muons.** Hadronic remnants behind the absorber fake muon hits
  ([muon systems](muon-systems.md), [particle identification](particle-identification.md)).

## Deliverables

- Calorimeter depth in `lambda_I`, tail-catcher depth, granularity, absorber and active medium, readout integration time.
- The calibration chain in order, with each step's reference sample and energy range, and what is extrapolated.
- The compensation method (none, offline weighting, local or global, dual readout, learned), the training sample, and
  the energy range where it was validated.
- Leakage and dead-material corrections with their binning, and the leakage tail in the resolution model.
- Time reconstruction and model validation:
  [companion](hadronic-calorimeter-timing-and-model-validation.md#deliverables).

## Tool hooks

**Software-compensation weight fit and validation** (planned), on a per-event cell CSV (cluster products need the geometry
added first):

- Inputs: per-event cell energies (GeV, EM scale) of the hadronic section and their volumes (cm^3), optional true per-cell deposits (for the negative control), the other sections' energies and the `e/pi`
  scale as in HC3, a reference energy per event independent of the calorimeter (beam energy or a stated non-calorimetric proxy such as
  the track momentum), the density-bin edges (GeV/cm^3), energy ranges
  for the weight sets, a split key that separates training from test events, the training event selection (HC3), applied alike.
- Outputs: weights per (density bin, energy range) with uncertainties; resolution and linearity before and after on
  the test split; a three-term resolution fit through `calorimeter_resolution.py`.
- Conventions: weights multiply EM-scale cell energies of the hadronic section; density as in HC3, its volume
  definition (active, absorber or whole sampling cell) the same in training and application; letters of the resolution terms as in [calorimetry](calorimetry-ecal-hcal.md#the-resolution-decomposition).
- Negative control: a fully contained sample generated with a single electromagnetic
  and hadronic response (`e/h = 1`) and no cell-level sampling fluctuations (or binned on true deposits) must give
  weights flat in density within their errors and no resolution gain, with errors no larger than in a positive control
  (same size and binning, `e/h` at the detector's measured or claimed value or the smallest non-compensation
  claimed corrected, never a gross one) whose non-flat weights are detected at the stated significance.
- Statuses: `synthetic` on generated input; `validated-in-scope` when the test split is data of known energy
  independent of the training events and both controls passed; `unvalidated` otherwise; `failed` when a control fails, a bin is empty, a weight is
  unconstrained, or the raw (weight-selecting) or reference energy leaves the trained range (out of domain; the test
  split covers the same range); `outside-validated-range` only when forced with
  `--allow-outside-validated-range`. A train/test overlap is an error, not a status.

The hadronic benchmark for `geant4_benchmarks.py` (planned; validation evidence only from `reference` or `setup-matched`
benchmarks covering the study's particle, energy, material and observable (isolated target, the setup-matched one with the measured hash), negative controls caught at the claimed detection limit in both directions for a two-sided claim, gross
controls excluded; none is hadronic today (the one setup-matched calorimeter benchmark, `longitudinal-profile`, has only an EM
reference), so a hadronic study is verification only until a published hadronic profile of the same configuration
is given to that benchmark and its controls are caught:
[protocol](geant4-study-protocol.md) secs. 5, 9) is specified in
[timing and model validation](hadronic-calorimeter-timing-and-model-validation.md#tool-hooks).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Software compensation | arxiv_1603.02934; pdg_2025_particle-detectors-at-accelerators | arxiv_1207.4210 | gap | gap | gap | gap |
| Dual readout | gap | pdg_2025_particle-detectors-at-accelerators | gap | gap | gap | gap |
| Hadronic calibration chain | arxiv_1203.1302 | arxiv_hep-ex_0007045 | arxiv_1909.12860 | arxiv_0805.3170; arxiv_1501.06431 | gap (air-fluorescence calorimetry: [fluorescence detectors](ground-based-detection-arrays.md#fluorescence-detectors)) | gap |
| Leakage, dead material, punch-through | arxiv_1603.02934; arxiv_1806.02129 | arxiv_hep-ex_0007045; arxiv_1201.1653; doi_10.1007_BF01650426 | arxiv_1909.12860 | gap | gap (invisible energy there is not leakage) | gap |
| High-granularity HCAL | pdg_2025_particle-detectors-at-accelerators (in construction, none operated) | arxiv_1702.08082; arxiv_2211.04740; arxiv_1412.2653 | gap | gap | gap | gap |

Every technique but high-granularity HCAL and dual readout (operated only in test beams, FXT) has two environments
with operated detectors; timing and validation points: companion.

## Worked examples

<!-- example: CALICE AHCAL software compensation -->
CALICE AHCAL, 38 layers of 5 mm scintillator tiles separated by 21 mm of steel, 5.3 `lambda_I`, CERN SPS H6, charged
pions 10-80 GeV (sec. 2.1, PDF pp. 5-6; 2007 data), shower start in the first five AHCAL layers (sec. 2.2, PDF p. 8).
Weights per energy-density bin follow `w = p0 + p1 exp(p2 rho)` (eq. 3.2, PDF p. 13), fitted on one half of the data and
tested on the statistically independent other half (PDF pp. 12-13). Stochastic term (fits of eq. 2.2): uncorrected (57.6 ± 0.4)%, global compensation
(45.8 ± 0.3)%, local compensation (44.3 ± 0.3)%; constant terms 1.6-1.8% (Fig. 4 caption, PDF p. 11). PDG RPP 2025
sec. 35.10.3 (PDF pp. 102-103) reports offline weighting (CDHS, H1, ATLAS endcap) and DREAM/RD52 dual readout (`xi` about 3, 70%/sqrt(E) for
single hadrons with lateral leakage).
<!-- /example -->

<!-- example: ATLAS calorimeters -->
ATLAS LCW: EM/HAD classification, cell weighting, out-of-cluster and dead-material corrections derived from
single-pion simulation, log-uniform in E from 200 MeV to 2 TeV at various `eta` (1603.02934 sec. 5.1, PDF pp. 29-31); the longitudinal-leakage correction applies to clusters
reaching the last hadronic layer, binned in cluster `eta`, `log10(E)` and depth (sec. 5.5, eq. 39, PDF p. 41).
Isolated-track `E/p` at `sqrt(s)` = 0.9 and 7 TeV reaches about 30 GeV, with the neutral background measured on late-showering tracks (`E_EM^0.1` < 1.1 GeV, `E_HAD^0.1/p` > 0.4 in `Delta R < 0.1`) and subtracted with `k` = 4/3 (R1 = 0.1, R2 = `R_coll` = 0.2) from the mean `E/p` of all isolated tracks (sec. 3.5, PDF pp. 5-6); data and simulation agree within about 2%
for 1-10 GeV and about 5% for 10-30 GeV (1203.1302 sec. 3.6, PDF p. 6). Above that, combined test-beam pions of
20-350 GeV at `eta` 0.20-0.65 are used (no neutral-hadron beam: from alternative lists, the n/p response ratio to 10% below 3 GeV and 5% above, and for `K_L` 20%, more conservative than the ~10% list spread, sec. 5.2.3), the 350 GeV measurement uncertainty is used up to 400 GeV, and above 400 GeV, where no test-beam or in-situ measurement
exists, 10% is added in quadrature for calorimeter non-linearities at high energy density and longitudinal leakage (sec. 5.2.1, PDF pp. 16-17; neutral hadrons PDF pp. 17-18).
<!-- /example -->

<!-- example: MINOS, MINERvA, DAMPE -->
MINOS (UGD): a 60-plane calibration detector measured responses in CERN PS beams with both readout electronics; the
three detectors were normalized to each other with cosmic-ray muons (0805.3170 sec. 1, PDF p. 9). MINERvA (UGD): a
scaled replica in a 0.35-2.0 GeV/c test beam measured proton, pion and electron response and the Birks parameter (1501.06431 abstract, PDF p. 2). DAMPE (SPC): a BGO
calorimeter of about 1.6 `lambda_I`; on-orbit calibration with MIP signals per crystal, energy by Bayesian unfolding
with a simulated response matrix (Materials and Methods, PDF p. 11). Their model comparisons:
[companion](hadronic-calorimeter-timing-and-model-validation.md#worked-examples).
<!-- /example -->

<!-- example: CMS HCAL, CALICE TCMT, ATLAS TileCal, RD5 -->
CMS HCAL prototype (H4 1995, about 8 `lambda_I` after the three MIP-tagged layers, 8.5 in total, ECAL removed): pion response rises about 9% from 15 to 375 GeV/c; the
longitudinal-leakage correction, from CCFR and NuTeV containment-versus-depth data (its reference 22) with a 30% systematic (Fig. 28 caption, PDF page 76), is 1.5% at 120 GeV/c and 3.5% at 375 GeV/c (hep-ex/0007045 sec. 6, PDF p. 27). In the 27-layer H2 1996 module (11 `lambda_I`, sec. 7.3; 10.1, and 8.5 for H4 1995, in sec. 2, PDF p. 9), profiles extend beyond
7 `lambda_I`; at the 9.5 `lambda_I` of HCAL, ECAL and the outer tail catcher HO behind the coil, fewer than 2% of
300 GeV/c pions are catastrophically mismeasured (sec. 7.3, PDF pp. 33-34). CALICE TCMT, October 2006, partial AHCAL
(23 cassettes, sec. 3, PDF pp. 11-12; not the AHCAL of arXiv:1207.4210): ECAL, partial AHCAL and the first seven TCMT
layers, 5.9 `lambda_n` (= `lambda_I`, PDF p. 7) in the text (PDF p. 21; 5.8 in Table 4, PDF p. 23), with the last nine TCMT layers measuring the leakage: mean 0.032 ± 0.002 (10 GeV) and 0.076 ± 0.001
(80 GeV); events above 10% leakage 0.030 and 0.061
(Table 3, PDF p. 21). ATLAS TileCal: a drop of the TileCal energy fraction for jets with pT above 1800 GeV in the barrel
signals rear leakage (1806.02129 sec. 6.2.2, PDF p. 44). RD5 measured the total punch-through probability of pion
showers at 30-300 GeV/c in iron up to 5.3 m equivalent (abstract only).
<!-- /example -->

<!-- example: CALICE SDHCAL, CMS HGCAL -->
CALICE SDHCAL: track segments inside showers, found with a Hough transform, calibrate the active layers in situ (sec. 5, PDF p. 18),
improve the energy and separate hadronic from EM showers (abstract, PDF p. 3). CMS HGCAL prototype with
CALICE AHCAL, CERN SPS H2, pions 20-300 GeV: shower start from layer multiplicity, energy within 10 cm and
`R_i < 0.96` with 2 cm and 10 cm radii; energy within 10 cm above 12 MIPs at 20 GeV and 40 MIPs at 200 GeV (no other energy given), tuned on Geant4 simulation, and the start is found within 2 layers (CE-E) or 1 (CE-H) of the true one for almost 95% of pions (sec. 4, PDF pp. 17-18).
<!-- /example -->

## Citations

Source IDs above are `arxiv_<id>`, `doi_<doi>` ('/' as '_' in both) and `pdg_2025_particle-detectors-at-accelerators`.
All were read 2026-11-20.

- S. Navas et al. (Particle Data Group), "Particle detectors at accelerators", sec. 35.10.3 "Hadronic calorimeters" (revised August 2025 by F. Sefkow and F. Simon), in Review of Particle Physics, Phys. Rev. D 110 (2024) 030001 and 2025 update, DOI 10.1103/PhysRevD.110.030001.

<!-- example: apparatus sources -->
- V. V. Abramov et al. (CMS-HCAL Collaboration), "Studies of the response of the prototype CMS hadron calorimeter, including magnetic field effects, to pion, electron, and muon beams", Nucl. Instrum. Methods A 457 (2001) 75, arXiv:hep-ex/0007045.
- D. G. Michael et al. (MINOS Collaboration), "The magnetized steel and scintillator calorimeters of the MINOS experiment", Nucl. Instrum. Methods A 596 (2008) 190, arXiv:0805.3170.
- C. Adloff et al., "Construction and performance of a silicon photomultiplier/extruded scintillator tail-catcher and muon-tracker", JINST 7 (2012) P04015, arXiv:1201.1653.
- ATLAS Collaboration, "Single hadron response measurement and calorimeter jet energy scale uncertainty with the ATLAS detector at the LHC", Eur. Phys. J. C 73 (2013) 2305, arXiv:1203.1302.
- C. Adloff et al. (CALICE Collaboration), "Hadronic energy resolution of a highly granular scintillator-steel hadron calorimeter using software compensation techniques", JINST 7 (2012) P09017, arXiv:1207.4210.
- B. Bilki et al. (CALICE Collaboration), "Pion and proton showers in the CALICE scintillator-steel analogue hadron calorimeter", JINST 10 (2015) P04014, arXiv:1412.2653.
- L. Aliaga et al. (MINERvA Collaboration), "MINERvA neutrino detector response measured with test beam data", Nucl. Instrum. Methods A 789 (2015) 28, arXiv:1501.06431.
- G. Aad et al. (ATLAS Collaboration), "Topological cell clustering in the ATLAS calorimeters and its performance in LHC Run 1", Eur. Phys. J. C 77 (2017) 490, arXiv:1603.02934.
- Z. Deng et al. (CALICE Collaboration), "Tracking within hadronic showers in the CALICE SDHCAL prototype using a Hough transform technique", JINST 12 (2017) P05009, arXiv:1702.08082.
- ATLAS Collaboration, "Operation and performance of the ATLAS Tile Calorimeter in Run 1", Eur. Phys. J. C 78 (2018) 987, arXiv:1806.02129.
- Q. An et al. (DAMPE Collaboration), "Measurement of the cosmic-ray proton spectrum from 40 GeV to 100 TeV with the DAMPE satellite", Sci. Adv. 5 (2019) eaax3793, arXiv:1909.12860.
- B. Acar et al. (CMS HGCAL and CALICE), "Performance of the CMS High Granularity Calorimeter prototype to charged pion beams of 20–300 GeV/c", JINST 18 (2023) P08014, arXiv:2211.04740.
- M. Aalste et al. (RD5 Collaboration), "Measurement of hadron shower punchthrough in iron", Z. Phys. C 60 (1993) 1, DOI 10.1007/BF01650426 (abstract only).
<!-- /example -->
