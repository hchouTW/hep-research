# Calorimeter Cluster Reconstruction

What is estimated from the cells of a shower calorimeter after the cell chain: clusters and their splitting
and merging, cluster position and direction, shower shapes for electron, photon, neutral-pion and hadron
separation, converted photons, cluster energy corrections, preshower layers, dual readout, and imaging and
high-granularity calorimeters. Shower physics, the resolution terms, leakage and identification by `E/p` are in
[calorimetry](calorimetry-ecal-hcal.md); generic clustering choices (windows versus topological growth, seed and
growth thresholds, the merged-cluster failure) are in [event reconstruction](event-reconstruction.md#clustering)
and are not repeated here. Hadronic cluster calibration is outside this page. Calibration constants and their
in-situ derivation are in [calibration and alignment](calibration-and-alignment.md); resolution and pull
conventions in [performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md);
fitting simulator parameters to shower shapes is simcal, owned by hep-statistics
([ECAL simcal](simulation-calibration/ecal.md)). Training a classifier on shape variables belongs to hep-ml
([multivariate analysis](../../hep-ml/references/multivariate-analysis-bdt-nn.md),
[fast-simulation validation](../../hep-ml/references/fast-simulation-validation.md)). An optional development
binding of a cell chain and clustering for a homogeneous analog grid is `<plugin root>/adapters/calo-cluster/`
(status demonstrated-on-synthetic-data, no calorimetry quality claim); example
`<plugin root>/examples/reconstruction-calorimetry/`.

Environment codes: COL collider; FXT fixed-target and test beam; SPC space and balloon; UGD underground, neutrino
and rare-event; GND ground-based arrays; NUC nuclear and low-energy. Geometry (projective or not), field, occupancy,
noise and the material in front are parameters of every method below. The coverage table names sources by ID
(`arxiv_<id>` is arXiv:<id>, with `/` written `_`; `pdg_2025_<review>` is that PDG RPP 2025 review); their
entries are in the calorimetry split file of the [annotated bibliography](detector-principles-bibliography.md).

## Relations

- **Cell significance and three thresholds** (exact, a definition; arXiv:1603.02934 sec. 3.1, eqs. 2-5):
  `zeta_i = E_i / sigma_noise,i`; a seed needs `|zeta| > S`, a cell that continues the growth `|zeta| > N`, a
  boundary cell `|zeta| > P`, with `S > N >= P`. The absolute value lets negative noise fluctuations in, which
  partly cancels the positive bias of a one-sided cut (same sec., p. 17). `sigma_noise` adds the expected
  overlap (pileup) noise to the electronic noise in quadrature where overlap exists (eq. 1); it is a conditions
  quantity, not a constant.
- **Shared-cell weights after splitting** (exact, a definition; arXiv:1603.02934 sec. 3.1.3, eqs. 6-8): a cell
  next to two maxima gets `w_1 = E_1 / (E_1 + r E_2)`, `w_2 = 1 - w_1`, `r = exp(d_1 - d_2)`, with `d_k` its
  distance to cluster `k`'s centre of gravity in units of a shower-size scale (the Molière radius in that
  source). A cell is shared by at most two clusters.
- **Centroid** (exact as an estimator, biased; arXiv:hep-ex/0209055 sec. 8, eq. 2):
  `x_c = sum_i w_i x_i / sum_i w_i`. With `w_i = E_i` it is pulled toward the centre of the hit cell (the
  S-curve), because the lateral profile falls steeply.
- **Logarithmic weights** (approximate, empirical; arXiv:1812.11426 sec. 7.1, eq. 5; arXiv:physics/0505127
  sec. 3.1, eqs. 2-3): `w_i = max(0, W0 + ln(E_i / E))`. `W0` sets the smallest energy fraction, `exp(-W0)`,
  that still counts, so it also removes noise cells. `W0` is tuned per geometry and per longitudinal
  compartment; it is not a constant (the per-apparatus values are in the examples below). `E` is the cluster
  or window energy the source names (whole cluster, one compartment, or a fixed cell array).
- **Position resolution** (approximate; PDG RPP 2025, Particle detectors at accelerators, sec. 35.10.2, p. 97):
  `sigma_x = a / sqrt(E) (+) b`, set by the effective Molière radius and the transverse granularity; quote it
  with the impact-point distribution inside the cell, since it varies across the cell (arXiv:hep-ex/0209055
  sec. 8, Fig. 16).
- **Inclined incidence** (approximate, a fit form; arXiv:hep-ex/0209055 sec. 8, eq. 5):
  `sigma_theta / sigma_0 = 1 (+) A sin(theta)`; the added term is the depth fluctuation of shower maximum
  projected on the cell plane.
- **Pointing from two depths** (exact geometry, given the two barycentres; arXiv:physics/0505127 sec. 3.2,
  eqs. 7-8): with barycentres `(Z_1, R_1)`, `(Z_2, R_2)` in two compartments,
  `Z_vertex = (Z_1 R_2 - Z_2 R_1) / (R_2 - R_1)` and the direction is the line through the two points.
- **Lateral second moment** (exact, a definition; arXiv:2012.06888 sec. 7.1, eq. 7):
  `sigma_uu = sqrt(sum_i w_i (u_i - u_bar)^2 / sum_i w_i)` over a fixed cell array with logarithmic `w_i`, in
  cell units. Per-layer energy-weighted RMS with `w_i = E_i` (arXiv:1711.10981 Methods, eq. 1) is the same
  quantity with linear weights.
- **Longitudinal profile** (approximate; a gamma-function description of one shower; arXiv:1703.02821 sec. III.B,
  eqs. 2-3): `dE/dt = E_0 beta (beta t)^(alpha-1) exp(-beta t) / Gamma(alpha)`, `t` in `X0`,
  `t_max = (alpha - 1) / beta`. A late `t_max` relative to the depth traversed flags rear leakage.
- **Preshower energy** (exact, a definition; arXiv:1306.2016 sec. 4.3, eq. 4): `E_PS = G (E_1 + alpha E_2)`, plane
  energies in MIP units, `G` in GeV per MIP from a fit to the calorimeter cluster energy, `alpha` the relative
  weight of the second plane from test beam.
- **Dual readout** (approximate: a two-component model with constant `h/e` per channel; arXiv:1712.05494 sec. V,
  eq. 6; arXiv:1703.09120 sec. 3.1, eq. 2): with both channels calibrated on electrons,
  `S = E [f_em + (h/e)_S (1 - f_em)]`, `C = E [f_em + (h/e)_C (1 - f_em)]`, so
  `E = (S - chi C) / (1 - chi)`, `chi = (1 - (h/e)_S) / (1 - (h/e)_C)`. It needs `(h/e)_S != (h/e)_C`; `S/C` is
  independent of `E` and fixes `f_em` per event.

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| Isolated electromagnetic showers, stable noise | Fixed-size window around a seed | Projective cells; known shower size | Lost brem or conversion energy; window crosses a crack | COL (arXiv:1908.00005 sec. 4); FXT, fixed crystal arrays (arXiv:hep-ex/0209055 sec. 8, eq. 2) |
| Variable shower extent, noise to suppress | Seeded growth on noise significance (`S`, `N`, `P`) | Per-cell noise known for the run conditions | Noise or overlap clusters; tails cut at low energy | COL (arXiv:1603.02934 sec. 3.1); single deposit in low occupancy, SPC (arXiv:1303.3514 sec. 2.2.1) |
| Non-projective calorimeter, wide field of view, stray deposits | Graph clustering (minimum spanning tree on 3D hits) | 3D readout | Unrelated deposits merged into the shower bias energy, centroid and axis | SPC only in the sources read (arXiv:1303.3514 sec. 2.2.1) |
| Two particles in one deposit | Split at local maxima, share boundary cells | Granularity finer than the separation | Merged pair reads as one object with summed energy | COL (arXiv:1603.02934 sec. 3.1.3); FXT (arXiv:1802.00672 sec. III) |
| Radiation spread by a field before the calorimeter | Supercluster: seed cluster plus clusters in a field-shaped window; tracker-assisted refinement | Field map; track or conversion-vertex input | Spurious clusters added; brem lost at low momentum | COL only (field geometry; arXiv:2012.06888 secs. 4.2, 4.4) |
| Position of an electromagnetic cluster | Logarithmic weights, or a linear centroid with an S-curve correction | Shower contained laterally; `W0` or S-curve tuned for that geometry | `W0` taken from another geometry; correction applied at the wrong angle or energy | FXT, COL (arXiv:1812.11426; arXiv:physics/0505127; arXiv:2012.06888) |
| Deriving the S-curve | Centroid versus an independently known impact point | Beam telescope or chambers | Telescope resolution not unfolded | FXT only: the reference point exists in test beams; COL and SPC apply corrections from simulation or test beam (arXiv:hep-ex/0209055 sec. 8; arXiv:physics/0505127 sec. 3.1) |
| Direction without a track | Barycentres at two or more depths, or a principal-axis fit | Longitudinal segmentation, a preshower, or 3D imaging | Early fluctuations and backsplash pull the axis | FXT, COL, SPC (arXiv:physics/0505127 sec. 3.2; PDG sec. 35.10.2; arXiv:1206.1896 sec. 3.2.1) |
| Electron or photon versus hadron | Lateral moments, core ratios, longitudinal fractions, combined in cuts or a classifier | Shape variables validated on data control samples | Hadronic tails mismodelled; variables used beyond their validated range | COL (arXiv:2012.06888 sec. 7.1); SPC without magnet (arXiv:1711.10981 Methods) |
| Photon versus two collimated photons | Fine first-layer strips, splitting on strips, two-shower separation | Strip pitch small compared with the opening | Separation lost at high energy | COL (arXiv:1908.00005 sec. 7.1; arXiv:1603.02934 sec. 3.1.3); FXT (arXiv:1802.00672) |
| Photon converted before the calorimeter | Cluster matched to a conversion vertex; recover the legs into the supercluster | Tracker, conversion finding | Single-leg conversions missed; converted photons as electrons | COL (arXiv:1908.00005 sec. 4; arXiv:2012.06888 sec. 4.4) |
| Energy in a converter-tracker before the calorimeter | Treat the converter-tracker as a sampling calorimeter; add its energy | Known converter thickness | Low-energy bias if omitted | SPC ([gamma-ray imaging](gamma-ray-imaging-and-polarimetry-reconstruction.md#pair-conversion-gamma-ray-telescopes); arXiv:1206.1896 sec. 3.2.1) |
| Energy lost in gaps, upstream material, laterally or at the rear | Parametric correction in shape variables, profile fit, likelihood, or a regression with a per-object resolution | Simulation validated on data; inputs inside the training range | Correction extrapolated in energy or angle; resolution estimate taken as truth | COL (arXiv:2012.06888 sec. 6.1); SPC (arXiv:1703.02821 sec. III; arXiv:1206.1896 sec. 3.2.1) |
| Homogeneous calorimeter without longitudinal segmentation | Preshower in front: added energy, pointing, a lateral-spread variable | MIP calibration of the preshower planes | Plane weights from another geometry | COL (arXiv:1306.2016 sec. 4.3; arXiv:2012.06888 sec. 7.1); FXT (arXiv:physics/0104033 p. 13, footnote 3) |
| Hadron energy with fluctuating electromagnetic fraction | Dual readout, `E = (S - chi C)/(1 - chi)` | Two signals with different `h/e`; enough Cherenkov light | Cherenkov photostatistics; leakage not corrected | FXT data only; SPC and COL are design contexts (arXiv:1703.09120; arXiv:1712.05494 secs. I, IV) |
| Overlapping showers, particle flow | Imaging or high-granularity calorimeter with pattern recognition | Cell size near or below the Molière radius | Confusion between overlapping showers | FXT (arXiv:0811.2354 sec. 1; arXiv:1802.00672); SPC imaging (arXiv:1901.00734 sec. III.A; arXiv:1206.1896 sec. 2.1.2) |

Rules that hold across the rows:

- **Fixed versus dynamic clusters.** A fixed-size cluster gives a linear, overlap-stable response; a dynamic one
  recovers brem and conversion energy and needs its own calibration to reach the same linearity
  (arXiv:1908.00005 sec. 4). State which one an energy scale belongs to.
- **Noise thresholds are run-condition parameters.** Seeds and growth are set in units of the per-run noise,
  including overlapping-event noise where present (arXiv:1603.02934 sec. 3.1); a cut in energy units changes
  meaning when the noise changes.
- **Longitudinal separation scales with `lambda_int / X0`.** Hadronic showers start later than electromagnetic
  ones, strongly so in a high-`Z` absorber where that ratio is large (arXiv:1802.00672 sec. II, p. 2).
- **The ambiguity is an output.** When a cluster can be an electron or a photon, both objects can be kept and
  flagged ambiguous for the analysis to resolve (arXiv:1908.00005 sec. 4.4).
- **Two-shower separation is measured, not assumed.** Overlay two single-shower test-beam events with a known
  displacement and record the probability that both are found with the right energy and position, as a
  function of distance (event mixing; arXiv:1802.00672 sec. III).

<!-- example: named apparatus and their numbers (collider, test beam and space instances of the rows above) -->
- ATLAS topological clusters: defaults `S = 4`, `N = 2`, `P = 0`, from pion test-beam optimisation; local maxima
  need `E > 500 MeV`, at least four neighbours and no larger neighbour; the shower-size scale for shared cells is
  5 cm for all calorimeters (arXiv:1603.02934 sec. 3.1, p. 15; sec. 3.1.3, p. 18, footnote 6). Converted-photon
  fraction: about 20% at low `|eta|` and up to about 65% near `|eta| = 2.3` (arXiv:1908.00005 sec. 4, p. 7).
- CMS ECAL: clusters seeded at local maxima above 1 GeV, energy shared by a Gaussian profile; mustache
  superclusters spread in `phi` by the solenoid (arXiv:2012.06888 sec. 4.2, p. 9). `sigma_ieta_ieta` uses
  `W0 = 4.7` over the 5x5 array, so a crystal counts above 0.9% of `E_5x5` (sec. 7.1, eq. 7, p. 36); R9 is the
  3x3 energy over the supercluster energy, and converted photons have lower R9 (sec. 6.1, p. 26; sec. 7.1,
  p. 36). Preshower: `alpha = 0.7` (best range 0.6 to 0.8 in test beam), `G = 0.023 +- 0.002 (stat) +- 0.001
  (syst) GeV/MIP`, 6 to 8% of the shower energy in the preshower (arXiv:1306.2016 sec. 4.3, p. 19-20).
- ATLAS EM barrel module in test beam: best `w0` 2.0 in the front and 4.4 in the middle compartment, 2.2 in the
  end-cap front (arXiv:physics/0505127 sec. 3.1, p. 9).
- ILC LumiCal prototype: best radial resolution at `W0 = 3.4` for that configuration, from simulation
  (arXiv:1812.11426 sec. 7.1, p. 9).
- BTeV PbWO4 prototype: `sigma_x = (0.16 +- 0.06) (+) (2.80 +- 0.08)/sqrt(E)` mm (E in GeV), 3x3 crystals;
  at 15 degrees the resolution is 1.5 (10 GeV) and 2.5 (27 GeV) times worse than at normal incidence
  (arXiv:hep-ex/0209055 sec. 8, eqs. 3, 5, pp. 16, 19).
- Fermi-LAT CsI calorimeter: before Pass 8 the deposit was one cluster; Pass 8's minimum-spanning-tree
  clustering separates ghost signals, with a reported 5 to 10% gain in effective area above about 1 GeV
  (arXiv:1303.3514 sec. 2.2.1, p. 3). Energy by a parametric correction, a profile fit or a likelihood, each
  valid in part of the energy and angle space; tracker energy added (arXiv:1206.1896 sec. 3.2.1, p. 41).
- DAMPE BGO: `zeta = F_last (sum_i RMS_i / mm)^4 / (8 x 10^6)` for electron-proton separation
  (arXiv:1711.10981 Methods, eq. 2, p. 11); gap correction with a core-energy ratio, rear leakage from the fitted
  `t_max` (arXiv:1703.02821 secs. III.A-B, pp. 3-4).
- HERMES: electrons identified by calorimeter, preshower and TRD together, about 99% efficiency with hadron
  contamination below 1% (arXiv:physics/0104033 p. 13, footnote 3).
- DREAM copper-fibre calorimeter: `h/e` of 0.21 (Cherenkov) and 0.77 (scintillation), `chi` about 0.3
  (arXiv:1703.09120 sec. 3.1, eqs. 1-2, p. 10). ACCESS, a proposed space-station instrument under 2 interaction
  lengths deep, was the first dual-readout prototype (arXiv:1712.05494 sec. IV, p. 7).
- CALICE SiW ECAL physics prototype: 1x1 cm2 cells, 30 layers, 24 `X0`; two-shower success needs both energies
  within 20% and barycentres within 5 mm (arXiv:1802.00672 secs. II-III, pp. 2-3).
<!-- /example -->

## Distinctive but generalizable features (calorimeter clusters)

- **Topology**: a sparse 2D or 3D image of cell energies, projective or not, with longitudinal layers or an
  unsegmented block.
- **Inverse problem**: number, energy, position and direction of the particles that made the deposit;
  degeneracy between one broad shower, two close showers and a shower plus noise or an unrelated deposit.
- **Natural objects**: cell, cluster, split cluster, supercluster, preshower cluster. **Informative residual**:
  centroid minus an independent impact point versus position in the cell (the S-curve), and cluster energy over
  a reference (`E/p`, a mass constraint, or the beam energy) versus shape variables.
- **Scaling**: position resolution `a/sqrt(E) (+) b`; the logarithmic cut-off at `exp(-W0)` of the cluster
  energy; two-shower separation set by the Molière radius relative to the cell size.
- **Conventions**: the depth at which a position is quoted; cell units or length units for moments; the energy
  that normalises a log weight (cluster, compartment or fixed array).
- **Tails**: merged showers, lost brem or conversion legs, leakage through cracks and the rear, saturated cells.
- **Dependence**: noise and overlap level, upstream material, incidence angle, field, occupancy.
- **Data sample**: test beams with a telescope (FXT); electrons from a dilepton resonance and photons from a
  radiative decay (COL); flight electrons and protons with independent charge or track tags (SPC).
- **Transfers**: the significance-threshold logic, log weighting, shape moments and event mixing to any
  segmented calorimeter. **Does not transfer**: supercluster window shapes (field-specific), `W0` values, and
  preshower plane weights between geometries.

## Common misconceptions and failure modes

- **A single `W0` treated as universal.** It depends on cell size relative to the Molière radius and on the
  compartment; tune it per geometry.
- **S-curve corrections applied at another angle or energy.** The curve depends on both (arXiv:hep-ex/0209055
  sec. 8).
- **Thresholds in energy units carried across run conditions.** They must follow the noise.
- **Unrelated deposits accepted into a low-occupancy cluster.** In a wide-field instrument they bias energy,
  centroid and axis (arXiv:1303.3514 sec. 2.2.1).
- **Regression resolution taken as measured.** A per-object resolution from a regression is a prediction to
  check with pulls on data.
- **Dual readout assumed operational in COL or SPC.** Its data are from test beams.
- **Converted photons scored as electrons** (or the reverse) without an ambiguity flag.

## Deliverables

- Clustering method (window, seeded growth, graph), thresholds in noise units, splitting rule and shared-cell
  weighting, with the run conditions they were set for.
- Position method (linear plus S-curve, or log weights with `W0`), the depth at which it is quoted, and the
  resolution versus energy, angle and position in the cell.
- Direction method (barycentres at depths, principal axis, preshower) and its resolution.
- Shape variables used for identification, their definitions (weights, cell array, units) and data/MC
  agreement on control samples.
- Energy corrections applied (gaps, upstream, lateral, rear) with their domain in energy and angle.
- For preshower, dual-readout and imaging calorimeters: plane weights and MIP calibration, `chi` and how it was
  measured, and the two-shower separation curve.

## Tool hooks

- **Inputs**: cell energies (GeV) after the cell chain, cell positions and sizes (mm) with layer index, per-cell
  noise (GeV) for the run conditions, optional tracks or conversion vertices.
- **Outputs**: clusters with energy, centroid at a stated depth, direction, second moments in cell units, core
  fractions, number of local maxima, and per-cell sharing fractions.
- **Conventions**: thresholds in units of the cell noise; the log-weight normalisation stated; deposited energy
  kept apart from corrected energy.
- **Negative control**: a scan of impact points across one cell; a linear centroid must show the S-curve bias
  and log weights must reduce it. Noise-only events must give the seed rate expected from the threshold.
- **Statuses**: `ok`, `split` (more than one maximum), `ambiguous` (electron or photon), `edge` (near a crack or
  border), `saturated`, `insufficient-cells`, `out-of-range` (correction asked outside its domain).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Seeded and graph clustering | arxiv_1603.02934 | n/a: one shower per event in a beam | arxiv_1303.3514 | [LArTPC imaging](noble-liquid-neutrino-and-rare-event-detectors.md#imaging-reconstruction-in-single-phase-lartpcs) | [two-level image cleaning](imaging-atmospheric-cherenkov.md#image-cleaning-and-reconstruction-choices) | gap |
| Splitting and two-shower separation | arxiv_1603.02934 | arxiv_1802.00672 | gap | gap | n/a: no cell calorimeter | gap |
| Superclustering in a field | arxiv_2012.06888 | n/a: no field-spread radiation | n/a: no magnet in front of calorimetric instruments | n/a | n/a | n/a |
| Logarithmic weights | arxiv_2012.06888 | arxiv_1812.11426, arxiv_physics_0505127 | gap | gap | n/a | gap |
| S-curve derivation | n/a: no independent impact point in situ | arxiv_hep-ex_0209055, arxiv_physics_0505127 | n/a: as COL | n/a | n/a | gap |
| Depth and direction | pdg_2025_particle-detectors-at-accelerators | arxiv_physics_0505127, arxiv_hep-ex_0209055 | arxiv_1206.1896 | gap | [air showers](extensive-air-showers.md) | n/a |
| Shower shapes for identification | arxiv_2012.06888, arxiv_1908.00005 | gap | arxiv_1711.10981 | [electron versus photon showers](noble-liquid-neutrino-and-rare-event-detectors.md#imaging-reconstruction-in-single-phase-lartpcs) | n/a | gap |
| Photon versus neutral pion | arxiv_1908.00005, arxiv_1603.02934 | arxiv_1802.00672 | gap | gap | n/a | gap |
| Converted photons | arxiv_1908.00005, arxiv_2012.06888 | gap | arxiv_1206.1896, [pair-conversion telescopes](gamma-ray-imaging-and-polarimetry-reconstruction.md#pair-conversion-gamma-ray-telescopes) | n/a | n/a | n/a |
| Energy corrections | arxiv_2012.06888 | gap | arxiv_1703.02821, arxiv_1206.1896 | gap | [fluorescence energy](ground-based-detection-arrays.md#fluorescence-detectors) | gap |
| Preshower | arxiv_1306.2016, arxiv_2012.06888 | arxiv_physics_0104033 | gap | n/a | n/a | gap |
| Dual readout | n/a: proposed only (arxiv_1712.05494) | arxiv_1703.09120, arxiv_1712.05494 | test-beam prototype for a proposed instrument (arxiv_1712.05494) | n/a | n/a | n/a |
| Imaging and high granularity | gap | arxiv_0811.2354, arxiv_1802.00672 | arxiv_1901.00734, arxiv_1206.1896 | [LArTPC imaging](noble-liquid-neutrino-and-rare-event-detectors.md#imaging-reconstruction-in-single-phase-lartpcs) | n/a | gap |

`gap` marks content not found in the sources read; `n/a` gives the reason. NUC photon calorimeters were not
surveyed (a gap for every NUC cell marked so).

## Citations

Each source was read in its arXiv e-print (PDG: the 2025 review PDF) on 2026-11-17 to 2026-11-20; page numbers
are PDF pages. Full entries, with DOIs, are in the calorimetry split file of the
[annotated bibliography](detector-principles-bibliography.md). General sources:
PDG RPP 2025, Particle detectors at accelerators (sec. 35.10.2); S. Lee, M. Livan, R. Wigmans, Dual-readout
calorimetry, Rev. Mod. Phys. 90 (2018) 025002, arXiv:1712.05494 (secs. I, IV, V).

<!-- example: source citations (experiments and apparatus named as the source of a method or number) -->
arXiv:1603.02934 (ATLAS topological clustering, secs. 3.1, 3.1.3); arXiv:1908.00005 (ATLAS electrons and
photons, secs. 4, 4.4, 7.1); arXiv:2012.06888 (CMS electrons and photons, secs. 4.2, 4.4, 6.1, 7.1);
arXiv:1306.2016 (CMS ECAL calibration, sec. 4.3); arXiv:physics/0505127 (ATLAS EM module position, secs. 3.1,
3.2); arXiv:hep-ex/0209055 (BTeV prototype, sec. 8); arXiv:1812.11426 (LumiCal prototype, sec. 7.1);
arXiv:1303.3514 (Fermi-LAT Pass 8, sec. 2.2.1); arXiv:1206.1896 (Fermi-LAT on orbit, secs. 2.1.2, 3.2.1);
arXiv:1711.10981 (DAMPE electrons, Methods); arXiv:1703.02821 (DAMPE energy correction, sec. III);
arXiv:1901.00734 (DAMPE imaging calorimeter, sec. III.A); arXiv:0811.2354 (CALICE SiW ECAL, sec. 1);
arXiv:1802.00672 (CALICE two-shower separation, secs. II-III); arXiv:1703.09120 (dual-readout fibre calorimeter,
sec. 3.1); arXiv:physics/0104033 (HERMES RICH, p. 13, footnote 3).
<!-- /example -->
