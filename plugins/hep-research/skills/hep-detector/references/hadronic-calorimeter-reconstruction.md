# Hadronic Calorimeter Reconstruction

How the energy, depth and quality of a hadronic shower are reconstructed: software compensation and dual readout,
the hadronic calibration chain, leakage, dead material and punch-through, and high-granularity (imaging) hadronic
calorimeters. Shower timing and the observables that validate hadronic physics lists are in the companion
[hadronic calorimeter timing and model validation](hadronic-calorimeter-timing-and-model-validation.md). The principles
(non-compensation, `e/h`, `pi/e`, the routes to compensation, containment) are in
[calorimetry](calorimetry-ecal-hcal.md#hadronic-showers-and-non-compensation) and its
[containment section](calorimetry-ecal-hcal.md#leakage-dead-material-and-containment) and are not repeated here; cell clustering
is in [event reconstruction](event-reconstruction.md#clustering) and particle flow in
[particle-flow reconstruction](event-reconstruction.md#track-cluster-association-and-particle-flow-reconstruction);
physics settings and list variations are in
[detector simulation](detector-simulation.md#physics-lists-and-their-validity) and the
[Geant4 study protocol](geant4-study-protocol.md) (secs. 3, 5 and 6; sec. 6 for which list pairs are a model
variation). Fitting simulator parameters to hadronic data is
simcal, owned by hep-statistics; its HCAL specialization is [simulation-calibration/hcal](simulation-calibration/hcal.md).
Jet energy scale corrections are in
[physics objects](physics-objects-jets-btagging-met.md#jet-energy-scale-and-resolution); their use as
systematics belongs to hep-measurement ([systematics](../../hep-measurement/references/systematics.md)).

Environment codes (R1): COL collider; FXT fixed-target and test beam; SPC space and balloon; UGD underground,
neutrino and rare-event; GND ground-based arrays; NUC nuclear and low-energy.

## Relations

Each relation gives its status, its validity (for a fitted relation, the training range and the energy that selects
the weights) and its source.

| # | Relation | Status and validity | Source |
|---|---|---|---|
| HC1 | `C = [f_em + (h/e)_C (1 - f_em)] E`, `S = [f_em + (h/e)_S (1 - f_em)] E`; `E = (xi S - C) / (xi - 1)`, `xi = [1 - (h/e)_C] / [1 - (h/e)_S]` | exact algebra of a linear two-component model; approximate as physics, since `(h/e)_C,S` are averages and leakage is ignored; useless as `xi -> 1` | PDG RPP 2025 sec. 35.10.3, eqs. 35.51-35.53 |
| HC2 | `f_em = [C/E - (h/e)_C] / [1 - (h/e)_C]` with `E` from HC1 | exact algebra of eq. 35.51 | same |
| HC3 | `E_LC = E_ECAL^track + (e/pi) [sum_i w(rho_i, E_raw) E_HCAL,i + E_TCMT]` (local software compensation, eq. 3.1): weights on the hadronic-section hits only; the electromagnetic track energy and the tail catcher unweighted; the sum scaled by `e/pi`; `rho_i = E_HCAL,i / V_i`, `V_i` the cell volume (sec. 3.1; the Fig. 5 caption calls it the absorber volume); weights lower for dense (electromagnetic) cells when `e/h > 1`, fitted on a sample of known energy by minimizing `sum_events (E_LC - E_beam)^2` | approximate (empirical); valid inside the training energy range and configuration; in application the uncorrected reconstructed energy `E_raw`, not the beam energy, selects the weight set | arXiv:1207.4210, sec. 3.1, eq. 3.1, Fig. 5, PDF pp. 13-14 |
| HC4 | `w_cell = P_EM w_em + (1 - P_EM) w_had` for every calibration step of a cluster | exact as a definition; `P_EM` and the weights come from single-pion (charged and neutral) simulation, so they are only as good as its modelling of the moments used | arXiv:1603.02934, sec. 5.1, eq. 29, PDF p. 30 |
| HC5 | `<E/p> = <E/p>_raw - k <E/p>_BG`, `k = R2^2 / (R2^2 - R1^2)` when the neutral background is measured in an annulus `R1 < Delta R < R2` | exact geometric factor if the background density is uniform in the cone; the uniformity is an assumption to validate | arXiv:1203.1302, sec. 3.5, eqs. 2-3, PDF p. 6 |
| HC6 | `N_dep,i = sum_j M_ij N_inc,j`, `M_ij` the probability that an event of incident-energy bin `j` deposits in bin `i` | exact definition of the response; `M` from simulation carries the hadronic-model dependence | arXiv:1909.12860, Materials and Methods eq. 2, PDF p. 11; see [response and forward folding](response-and-forward-folding.md) |
| HC7 | fractional leakage per event `(E_total - E_contained) / E_total`, with `E_total` including a rear tail catcher | exact definition; a lower bound on the true leakage if the catcher itself leaks | arXiv:1201.1653, sec. 5, PDF p. 21 |
| HC9 (HC8 is in the [companion](hadronic-calorimeter-timing-and-model-validation.md#relations)) | `R_i = sum_(l=i)^(i+2) E_l(r < r_core) / sum_(l=i)^(i+2) E_l(r < r_halo)`: near 1 along a minimum-ionizing track, smaller after the first hadronic interaction | exact as a definition; the shower start is the first layer passing multiplicity, energy and `R_i` thresholds tuned on simulation | arXiv:2211.04740, sec. 4, eq. 4.1 |

The mean shower depth from the front face is the shower-start distribution convolved with the profile measured from
the shower start, so detecting the start allows a per-event leakage estimate and a sharper model test (PDG RPP 2025
sec. 35.10.3, PDF p. 98).

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Non-compensating HCAL with longitudinal segmentation | offline (longitudinal or amplitude) weighting | segmentation that separates early dense deposits; a sample of known energy | weights tuned on simulation inherit its `f_em` modelling | COL, FXT |
| Highly granular HCAL | local (per-cell density bins) or global (per-event, from the hit-energy spectrum) software compensation; machine-learned variants | cell-level density; training and test samples statistically independent; a weight set per energy range | bins with too few hits; weights extrapolated outside the training range; train/test overlap | FXT (COL in construction) |
| Collider clusters in a non-compensating system | EM/HAD classification, then cell weights, out-of-cluster and dead-material corrections, each as blended weights (HC4) | single-pion simulation that models the cluster moments used, checked in data (isolated-track `E/p`, HC5) | misclassified small clusters; corrections that hide data/MC differences | COL |
| Two optical signals per cell | dual readout (HC1-HC2) | known `(h/e)_C`, `(h/e)_S`; the S and C fluctuations, amplified by `xi/(xi - 1)` and `1/(xi - 1)` (HC1), shown smaller than the `f_em` fluctuation they remove; a steep `xi` needs a nearly compensating scintillator readout, which leaves less to gain (PDG RPP 2025 sec. 35.10.3, PDF p. 103) | lateral leakage in small modules; `xi` near 1 amplifies the S and C fluctuations beyond the `f_em` term removed | FXT (prototypes) |
| Setting the hadronic scale | EM scale; MIP or muon equalization of cells; test-beam hadron response; in-situ isolated-track `E/p` (HC5); transfer of test-beam constants to the installed detector | the same electronics or a measured transfer; a tracker momentum scale independent of the calorimeter | `E/p` reach limited to low momenta; beyond the test-beam range only extrapolation is left; `E/p` shifts that are tracker effects | COL, FXT, UGD, SPC |
| Calorimeter much shallower than the shower | unfolding the deposited energy with a simulated response (HC6) | a response validated on beam tests and on-orbit or in-situ profiles over the unfolded range; above the highest validated energy, only a two-model envelope | model dependence dominates the systematic; the prior spectrum biases the unfolding | SPC only (GND fluorescence detectors integrate the profile and correct for invisible energy instead; see the coverage table) |
| Rear leakage and punch-through | tail catcher or extra instrumented depth; leakage corrections binned in energy, direction and cluster depth; shower-start-based correction | depth beyond the absorber instrumented, or simulation of the leakage tail | low-side tail not described by a Gaussian; punch-through mistaken for muons | COL, FXT, SPC |

Time per cell or cluster and validating the hadronic model are in the
[timing and model validation](hadronic-calorimeter-timing-and-model-validation.md#methods) methods.

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
- **Tails**: low-side tails from leakage and late showers; high-side from overlapping or out-of-time deposits and,
  without compensation, from `f_em` fluctuations (high side for `e/h > 1`).
  The resolution-shape models are in
  [performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md#resolution-models-and-widths).
- **Dependence**: integration time, absorber (neutron yield), active medium (hydrogen content), radiation damage of
  the sensors ([calibration and alignment](calibration-and-alignment.md#time-dependence-and-conditions-data),
  [photosensors](cherenkov-imaging-variants-and-photosensors.md#photosensors-and-light-transport)).
- **Data sample**: tagged test beams (FXT) for the absolute response; isolated tracks and muons in situ (COL);
  cosmic-ray muons for cell and detector equalization (UGD, COL); MIP signals on orbit (SPC).
- **Transfers**: the density-weighting idea, the shower-start convolution and the response-matrix treatment transfer
  between environments; specific weights (they depend on energy and configuration), thresholds and physics-list rankings do not.

## Common misconceptions and failure modes

- **One hadronic scale for every particle.** Pions, protons and neutral hadrons respond differently; an `E/p`
  measured for charged pions does not cover neutrons.
- **Validation on the training sample.** Weights, `P_EM` maps or a learned regression evaluated on the events that
  fitted them overstate the gain.
- **Leakage absorbed into the constant term.** Leakage grows with energy and gives a low-side tail; correct or model
  it per event.
- **Punch-through counted as muons.** Hadronic remnants behind the absorber fake muon hits
  ([muon systems](muon-systems.md), [particle identification](particle-identification.md)).
- **Test-beam constants carried over unchanged.** Electronics, integration time and magnetic field differ in the
  installed detector; measure the transfer.

## Deliverables

- Calorimeter depth in `lambda_I`, tail-catcher depth, granularity, absorber and active medium, readout integration time.
- The calibration chain in order, with each step's reference sample and energy range, and what is extrapolated.
- The compensation method (none, offline weighting, local or global, dual readout, learned), the training sample, and
  the energy range where it was validated.
- Leakage and dead-material corrections with their binning, and the leakage tail in the resolution model.
- Time reconstruction and model validation: as in
  [timing and model validation](hadronic-calorimeter-timing-and-model-validation.md#deliverables).

## Tool hooks

**Software-compensation weight fit and validation** (a planned tool), on a per-event cell CSV with cell volumes;
cluster products need the geometry added first:

- Inputs: per-event cell energies (GeV, EM scale) of the hadronic section and their volumes (cm^3) with the volume
  definition, optional true per-cell deposits (for the negative control), the other sections' energies and the `e/pi`
  scale as in HC3, a reference energy per event independent of the calorimeter (beam energy or a stated proxy such as
  the track momentum; a proxy from calorimeter energies is refused), the density-bin edges (GeV/cm^3), energy ranges
  for the weight sets, a split key that separates training from test events.
- Outputs: weights per (density bin, energy range) with uncertainties; resolution and linearity before and after on
  the test split; a three-term resolution fit through `calorimeter_resolution.py`.
- Conventions: weights multiply EM-scale cell energies of the hadronic section; density is cell energy per cell
  volume `V_i`, the volume definition (active, absorber or whole sampling cell) stated and the same in training and
  application, as in HC3; letters of the resolution terms as in [calorimetry](calorimetry-ecal-hcal.md#the-resolution-decomposition).
- Negative control: a fully contained sample (no rear or lateral leakage) generated with a single electromagnetic
  and hadronic response (`e/h = 1`) and no cell-level sampling fluctuations (or binned on true deposits) must give
  weights flat in density within their errors and no resolution gain; a train/test overlap must be refused.
- Statuses: `synthetic` on generated input; `validated-in-scope` when the test split is data of known energy
  independent of the training events; `unvalidated` otherwise; `failed` when a bin is empty or a weight is
  unconstrained; `outside-validated-range` when the raw (weight-selecting) or the reference energy leaves the trained
  range (the test split covers the same range). A train/test overlap is an error, not a status.

The hadronic benchmark for `geant4_benchmarks.py` (planned; only `reference` and `setup-matched` grades are
validation evidence, line 208) is specified in
[timing and model validation](hadronic-calorimeter-timing-and-model-validation.md#tool-hooks).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Software compensation, dual readout | arxiv_1603.02934; pdg_2025_particle-detectors-at-accelerators | arxiv_1207.4210 | gap | gap | gap | gap |
| Hadronic calibration chain | arxiv_1203.1302 | arxiv_hep-ex_0007045 | arxiv_1909.12860 | arxiv_0805.3170; arxiv_1501.06431 | gap (air-fluorescence calorimetry, which integrates the dE/dX profile and adds a simulation-based invisible-energy correction, is in [fluorescence detectors](ground-based-detection-arrays.md#fluorescence-detectors)) | gap |
| Leakage, dead material, punch-through | arxiv_1603.02934; arxiv_1806.02129 | arxiv_hep-ex_0007045; arxiv_1201.1653; doi_10.1007_BF01650426 | arxiv_1909.12860 | gap | gap (invisible energy, in [fluorescence detectors](ground-based-detection-arrays.md#fluorescence-detectors), is not leakage) | gap |
| High-granularity HCAL | pdg_2025_particle-detectors-at-accelerators (in construction, none operated) | arxiv_1702.08082; arxiv_2211.04740; arxiv_1412.2653 | gap | gap | gap | gap |

Every technique except high-granularity HCAL has at least two environments with operated detectors; shower timing and
physics-list validation points (where a list swap is a model variation, not a negative control) are covered in
[timing and model validation](hadronic-calorimeter-timing-and-model-validation.md#environment-coverage).
High-granularity hadronic calorimetry has been operated only in test beams; the collider entry is a detector under
construction and does not count as an environment.

## Worked examples

<!-- example: software compensation in the CALICE scintillator-steel AHCAL (arXiv:1207.4210) -->
CALICE AHCAL, 38 layers of 5 mm scintillator tiles separated by 21 mm of steel, 5.3 `lambda_I`, CERN SPS H6, charged
pions 10-80 GeV (sec. 2.1, PDF pp. 5-6; 2007 data).
Weights per energy-density bin follow `w = p0 + p1 exp(p2 rho)` (eq. 3.2, PDF p. 13), fitted on one half of the data and
tested on the statistically independent other half (PDF pp. 12-13). Stochastic term (fits of eq. 2.2): uncorrected (57.6 ± 0.4)%, global compensation
(45.8 ± 0.3)%, local compensation (44.3 ± 0.3)%; constant terms 1.6-1.8% (Fig. 4 caption, PDF p. 11). PDG RPP 2025
sec. 35.10.3 (PDF pp. 102-103) reports earlier offline weighting for CDHS (10% at 10 GeV to 30% at 140 GeV
improvement), H1 (51%/sqrt(E)) and the ATLAS endcap (84%/sqrt(E)), and dual readout in DREAM/RD52 with `xi` about 3
(so HC1 amplifies the S and C fluctuations by 1.5 and 0.5) and 70%/sqrt(E) for single hadrons, including lateral
leakage.
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
simulation, tuned with these data, agrees better than 4% for the calorimetric response, though some features are
not precisely modelled (1501.06431 abstract, PDF p. 2). DAMPE (SPC): a BGO
calorimeter of about 1.6 `lambda_I`; on-orbit calibration with MIP signals per crystal, energy by Bayesian unfolding
with a simulated response matrix (Materials and Methods, PDF p. 11); the hadronic-model systematic on the proton flux
is about 7% below 400 GeV, from the 400 GeV test beam against FTFP_BERT, and 7-10% above, from FTFP_BERT against
FLUKA (PDF p. 13).
<!-- /example -->

<!-- example: leakage and punch-through (arXiv:hep-ex/0007045, arXiv:1201.1653, arXiv:1806.02129, RD5, DOI 10.1007/BF01650426) -->
CMS HCAL prototype (H4 1995, about 8 `lambda_I`): pion response rises about 9% from 15 to 375 GeV/c; the estimated
leakage correction is 1.5% at 120 GeV/c and 3.5% at 375 GeV/c (sec. 6, PDF p. 27 of hep-ex/0007045). In the 27-layer H2 1996 module (11 `lambda_I`), profiles extend beyond
7 `lambda_I`; at the 9.5 `lambda_I` of HCAL, ECAL and the outer tail catcher HO behind the coil, fewer than 2% of
300 GeV/c pions are catastrophically mismeasured (sec. 7.3, PDF pp. 33-34). CALICE TCMT, October 2006 run with a
partial AHCAL (23 instrumented cassettes, sec. 3, PDF pp. 11-12; not the complete 5.3 `lambda_I` AHCAL of arXiv:1207.4210), the
system defined as ECAL, partial AHCAL and the first seven TCMT layers, 5.9 `lambda_n` as the text states (PDF p. 21, with Table 3; its Table 4,
PDF p. 23, lists 4.8 `lambda_n` without TCMT layers and 5.8 with seven), and the last nine TCMT layers measuring
the leakage: mean leakage 0.032 ± 0.002 (10 GeV) and 0.076 ± 0.001 (80 GeV); fraction of events above 10% leakage
0.030 and 0.061
(Table 3, PDF p. 21). ATLAS TileCal: a drop of the TileCal energy fraction for jets above 1800 GeV in the barrel
signals rear leakage (1806.02129 sec. 6.2.2, PDF p. 44). RD5 measured the total punch-through probability of pion
showers at 30-300 GeV/c in iron up to 5.3 m equivalent (Z. Phys. C 60 (1993) 1, abstract only).
<!-- /example -->

<!-- example: high-granularity HCALs (arXiv:1702.08082, arXiv:2211.04740) -->
CALICE SDHCAL: track segments inside showers, found with a Hough transform, calibrate the active layers in situ,
improve the energy and separate hadronic from electromagnetic showers (abstract, PDF p. 3). CMS HGCAL prototype with
CALICE AHCAL, CERN SPS H2, pions 20-300 GeV: shower start from layer multiplicity, energy within 10 cm and
`R_i < 0.96` with 2 cm and 10 cm radii; energy within 10 cm above 12 MIPs at 20 GeV and 40 MIPs at 200 GeV (sec. 4).
<!-- /example -->

## Citations

The full entries are in this list, each with its DOI or arXiv id (the source IDs above are `arxiv_<id>`,
`doi_<doi>`, with '/' written as '_', and `pdg_2025_particle-detectors-at-accelerators`). Entries that name an apparatus sit in the example
block. All were read 2026-11-20.

- S. Navas et al. (Particle Data Group), "Particle detectors at accelerators", sec. 35.10.3 "Hadronic calorimeters" (revised August 2025 by F. Sefkow and F. Simon), in Review of Particle Physics, Phys. Rev. D 110 (2024) 030001 and 2025 update, DOI 10.1103/PhysRevD.110.030001, <https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-accel.pdf>.

<!-- example: apparatus sources -->
- V. V. Abramov et al. (CMS-HCAL Collaboration), "Studies of the response of the prototype CMS hadron calorimeter, including magnetic field effects, to pion, electron, and muon beams", Nucl. Instrum. Methods A 457 (2001) 75, DOI 10.1016/S0168-9002(00)00711-7, arXiv:hep-ex/0007045.
- MINOS Collaboration, "The magnetized steel and scintillator calorimeters of the MINOS experiment", Nucl. Instrum. Methods A 596 (2008) 190-228, DOI 10.1016/j.nima.2008.08.003, arXiv:0805.3170.
- C. Adloff et al., "Construction and performance of a silicon photomultiplier/extruded scintillator tail-catcher and muon-tracker", JINST 7 (2012) P04015, DOI 10.1088/1748-0221/7/04/P04015, arXiv:1201.1653.
- ATLAS Collaboration, "Single hadron response measurement and calorimeter jet energy scale uncertainty with the ATLAS detector at the LHC", Eur. Phys. J. C 73 (2013) 2305, DOI 10.1140/epjc/s10052-013-2305-1, arXiv:1203.1302.
- C. Adloff et al. (CALICE Collaboration), "Hadronic energy resolution of a highly granular scintillator-steel hadron calorimeter using software compensation techniques", JINST 7 (2012) P09017, DOI 10.1088/1748-0221/7/09/P09017, arXiv:1207.4210.
- B. Bilki et al. (CALICE Collaboration), "Pion and proton showers in the CALICE scintillator-steel analogue hadron calorimeter", JINST 10 (2015) P04014, DOI 10.1088/1748-0221/10/04/P04014, arXiv:1412.2653.
- L. Aliaga et al. (MINERvA Collaboration), "MINERvA neutrino detector response measured with test beam data", Nucl. Instrum. Methods A 789 (2015) 28, DOI 10.1016/j.nima.2015.04.003, arXiv:1501.06431.
- G. Aad et al. (ATLAS Collaboration), "Topological cell clustering in the ATLAS calorimeters and its performance in LHC Run 1", Eur. Phys. J. C 77 (2017) 490, DOI 10.1140/epjc/s10052-017-5004-5, arXiv:1603.02934.
- Z. Deng et al. (CALICE Collaboration), "Tracking within hadronic showers in the CALICE SDHCAL prototype using a Hough transform technique", JINST 12 (2017) P05009, DOI 10.1088/1748-0221/12/05/P05009, arXiv:1702.08082.
- ATLAS Collaboration, "Operation and performance of the ATLAS Tile Calorimeter in Run 1", Eur. Phys. J. C 78 (2018) 987, DOI 10.1140/epjc/s10052-018-6374-z, arXiv:1806.02129.
- Q. An et al. (DAMPE Collaboration), "Measurement of the cosmic-ray proton spectrum from 40 GeV to 100 TeV with the DAMPE satellite", Sci. Adv. 5 (2019) eaax3793, DOI 10.1126/sciadv.aax3793, arXiv:1909.12860.
- B. Acar et al. (CMS HGCAL and CALICE), "Performance of the CMS High Granularity Calorimeter prototype to charged pion beams of 20-300 GeV/c", JINST 18 (2023) P08014, DOI 10.1088/1748-0221/18/08/P08014, arXiv:2211.04740.
- M. Aalste et al. (RD5 Collaboration), "Measurement of hadron shower punchthrough in iron", Z. Phys. C 60 (1993) 1, DOI 10.1007/BF01650426 (abstract only; full text not retrieved). Cited only for what its abstract states: the measurement, its momentum range and its iron depth.
<!-- /example -->
