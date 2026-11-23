# Calorimeter Cluster Reconstruction

Estimates from the cells of a shower calorimeter after the cell chain: clusters and splitting, position and
direction, shower shapes (electron, photon, neutral pion, hadron), converted photons, energy corrections,
preshower, dual readout and imaging. Shower physics, resolution terms,
leakage physics (not its corrections), `E/p` identification and a
[summary of this page](calorimetry-ecal-hcal.md#shower-position-direction-and-shape):
[calorimetry](calorimetry-ecal-hcal.md); windows versus topological growth and the merged-cluster failure:
[event reconstruction](event-reconstruction.md#clustering). Hadronic cluster calibration is outside this page.
Calibration constants:
[calibration and alignment](calibration-and-alignment.md); resolution and pull conventions:
[performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md). Fitting
simulator parameters to shower shapes is simcal, owned by hep-statistics
([ECAL simcal](simulation-calibration/ecal.md)); training a classifier on shape variables belongs to hep-ml
([multivariate analysis](../../hep-ml/references/multivariate-analysis-bdt-nn.md),
[fast-simulation validation](../../hep-ml/references/fast-simulation-validation.md)). A development adapter
(cell chain and clustering on a homogeneous analog grid; synthetic and labelled simulated-unvalidated data only) is
`<plugin root>/adapters/calo-cluster/`, example `<plugin root>/examples/reconstruction-calorimetry/`.

Environment codes: COL collider; FXT fixed-target and test beam; SPC space and balloon; UGD underground, neutrino
and rare-event; GND ground-based arrays; NUC nuclear and low-energy. Geometry (projective or not), field, occupancy,
noise and the material in front are parameters of every method below. Coverage cells name sources by ID or link
a page whose sources carry the evidence (`arxiv_<id>` is arXiv:<id>, `/` written `_`;
`pdg_2025_<review>` the PDG RPP 2025 review of that hyphenated title); every ID
has an entry in the split file shipped with this page,
[detector-principles-bibliography-calorimetry.md](detector-principles-bibliography-calorimetry.md).

## Relations

- **Cell significance and three thresholds** (exact, a definition; arXiv:1603.02934 sec. 3.1, eqs. 2-5):
  `zeta_i = E_i / sigma_noise,i`; a seed needs `|zeta| > S`, a cell that continues the growth `|zeta| > N`, a
  boundary cell `|zeta| > P`, with `S > N >= P`. `sigma_noise` adds overlap
  (pileup) noise to the electronic noise in quadrature where overlap exists (eq. 1): a conditions quantity,
  fixed in advance for a run period's expected mean overlap (sec. 2.2.2, p. 12).
- **Shared-cell weights after splitting** (exact, a definition; arXiv:1603.02934 sec. 3.1.3 with footnote 6,
  eqs. 6-8): a cell next to two maxima gets `w_1 = E_1 / (E_1 + r E_2)`, `w_2 = 1 - w_1`, `r = exp(d_1 - d_2)`,
  with `d_k` its distance to cluster `k`'s centre of gravity in units of a shower-size scale (in that source a
  typical scale motivated by the Molière radius but fixed for all calorimeters, value in the examples).
  A cell is shared by at most two clusters.
- **Centroid** (exact as an estimator, biased; arXiv:hep-ex/0209055 sec. 8, eq. 2):
  `x_c = sum_i w_i x_i / sum_i w_i`. With `w_i = E_i` it is pulled toward the centre of the hit cell (the
  S-curve), because the lateral profile falls steeply.
- **Logarithmic weights** (approximate, empirical; arXiv:1812.11426 sec. 7.1, eq. 5; arXiv:physics/0505127
  sec. 3.1, eqs. 2-3): `w_i = max(0, W0 + ln(E_i / E))`. `W0` sets the smallest energy fraction, `exp(-W0)`,
  that still counts, so it also removes noise cells. `W0` is tuned per geometry and per longitudinal
  compartment (values in the examples). `E` is the normalising energy: the whole cluster, one
  compartment or a fixed cell array.
- **Position resolution** (approximate; PDG sec. 35.10.2, p. 97):
  `sigma_x = a / sqrt(E) (+) b`, set by the effective Molière radius and the transverse granularity; it varies
  across the cell, so quote it with the impact-point distribution (arXiv:hep-ex/0209055 sec. 8, Fig. 16).
- **Inclined incidence** (approximate, a fit form; arXiv:hep-ex/0209055 sec. 8, eq. 5):
  `sigma_theta / sigma_0 = 1 (+) A sin(theta)`; the added term is the depth fluctuation of shower maximum
  projected on the cell plane.
- **Pointing from two depths** (exact geometry, given the two barycentres; arXiv:physics/0505127 sec. 3.2,
  eqs. 7-8): with barycentres `(Z_1, R_1)`, `(Z_2, R_2)` in two compartments,
  `Z_vertex = (Z_1 R_2 - Z_2 R_1) / (R_2 - R_1)` and the direction is the line through the two points.
- **Lateral second moment** (exact, a definition; arXiv:2012.06888 sec. 7.1, eq. 7):
  `sigma_uu = sqrt(sum_i w_i (u_i - u_bar)^2 / sum_i w_i)` over a fixed cell array with logarithmic `w_i`, in
  cell units, not lengths. Per-layer energy-weighted RMS with `w_i = E_i` (arXiv:1711.10981 Methods, eq. 1) has
  the same form with linear weights, but per layer and in mm, not cell units.
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
| Variable shower extent, noise to suppress | Seeded growth on noise significance (`S`, `N`, `P`) | Per-cell noise known for the run conditions | Noise or overlap clusters; tails cut at low energy | COL (arXiv:1603.02934 sec. 3.1); FXT: default thresholds optimised on pion test beams, cited second-hand (same sec., p. 15) |
| Non-projective calorimeter, wide field of view, stray deposits | Graph clustering (minimum spanning tree on 3D hits) | 3D readout | Unrelated deposits merged into the shower bias energy, centroid and axis | SPC only in the sources read (arXiv:1303.3514 sec. 2.2.1) |
| Two particles in one deposit | Split at local maxima, share boundary cells | Granularity finer than the separation | Merged pair reads as one object with summed energy | COL (arXiv:1603.02934 sec. 3.1.3); FXT (arXiv:1802.00672 sec. III) |
| Radiation spread by a field before the calorimeter | Supercluster: seed cluster plus clusters in a field-shaped window; tracker-assisted refinement | Field map; track or conversion-vertex input | Spurious clusters added; brem outside the window (an inference; the window widens at low `E_T`, sec. 4.2) | COL only in the sources read (arXiv:2012.06888 secs. 4.2, 4.4); FXT and SPC magnet spectrometers not read |
| Position of an electromagnetic cluster | Logarithmic weights, or a linear centroid with an S-curve correction | Shower contained laterally; `W0` or S-curve tuned for that geometry | `W0` taken from another geometry; correction applied at the wrong angle or energy | FXT (arXiv:1812.11426; arXiv:physics/0505127); COL: log weights only in a moment (arXiv:2012.06888 sec. 7.1) |
| Deriving the S-curve | Centroid versus an independently known impact point | Beam telescope or chambers | Telescope resolution not unfolded | FXT in the sources read (arXiv:hep-ex/0209055 sec. 8; arXiv:physics/0505127 sec. 3.1); COL, SPC: a track gives the impact point (no in-situ derivation read) |
| Direction without a track | Barycentres at two or more depths, or a principal-axis fit | Longitudinal segmentation, a preshower, or 3D imaging | Early fluctuations and backsplash pull the axis | FXT, COL, SPC (arXiv:physics/0505127 sec. 3.2; PDG sec. 35.10.2; arXiv:1206.1896 sec. 3.2.1) |
| Electron or photon versus hadron | Lateral moments, core ratios, longitudinal fractions, combined in cuts or a classifier | Shape variables validated on data control samples | Hadronic tails mismodelled; variables used beyond their validated range | COL (arXiv:2012.06888 sec. 7.1); SPC without magnet (arXiv:1711.10981 Methods) |
| Photon versus two collimated photons | Fine first-layer strips, splitting on strips, two-shower separation | Strip pitch small compared with the opening | Separation lost at high energy | COL (arXiv:1908.00005 sec. 7.1; arXiv:1603.02934 sec. 3.1.3); FXT (arXiv:1802.00672) |
| Photon converted before the calorimeter | Cluster matched to a conversion vertex; recover the legs into the supercluster | Tracker, conversion finding | Single-leg conversions missed; converted photons as electrons | COL (arXiv:1908.00005 sec. 4; arXiv:2012.06888 sec. 4.4) |
| Energy in a converter-tracker before the calorimeter | Treat the converter-tracker as a sampling calorimeter; add its energy | Known converter thickness | Low-energy bias if omitted | SPC ([gamma-ray imaging](gamma-ray-imaging-and-polarimetry-reconstruction.md#pair-conversion-gamma-ray-telescopes); arXiv:1206.1896 sec. 3.2.1) |
| Energy lost in gaps, upstream material, laterally or at the rear | Parametric correction in shape variables, profile fit, likelihood, or a regression with a per-object resolution | Simulation validated on data; inputs inside the training range | Correction extrapolated in energy or angle; resolution estimate taken as truth | COL (arXiv:2012.06888 sec. 6.1); SPC (arXiv:1703.02821 sec. III; arXiv:1206.1896 sec. 3.2.1); FXT not read |
| Homogeneous calorimeter without longitudinal segmentation | Preshower in front: added energy, a lateral-spread variable, pointing | MIP calibration of the preshower planes | Plane weights from another geometry | COL (energy: arXiv:1306.2016 sec. 4.3; spread: arXiv:2012.06888 sec. 7.1.2; pointing: PDG sec. 35.10.2); FXT, preshower used in electron identification only (arXiv:physics/0104033 p. 13, footnote 3) |
| Hadron energy with fluctuating electromagnetic fraction | Dual readout: two signals combined with `chi` | Two signals with different `h/e`; enough Cherenkov light | Cherenkov photostatistics; leakage not corrected | FXT data only; SPC and COL are design contexts (arXiv:1703.09120; arXiv:1712.05494 secs. I, IV) |
| Overlapping showers, particle flow | Imaging or high-granularity calorimeter with pattern recognition | Cell size near or below the Molière radius | Confusion between overlapping showers | FXT (arXiv:0811.2354 sec. 1; arXiv:1802.00672); SPC: 3D imaging for shape and leakage, no overlapping-shower separation read (arXiv:1901.00734 sec. III.A; arXiv:1206.1896 sec. 2.1.2; stray deposits: arXiv:1303.3514 sec. 2.2.1) |

Rules that hold across the rows:

- **Fixed versus dynamic clusters.** A fixed-size cluster gives a linear, overlap-stable response; a dynamic one
  recovers brem and conversion energy and needs its own calibration to reach the same linearity
  (arXiv:1908.00005 sec. 4). State which cluster type an energy scale belongs to.
- **Noise thresholds are run-condition parameters.** Seed, growth and boundary thresholds are in units of the noise
  expected for the run conditions (per run period in one source), overlap noise
  included (arXiv:1603.02934 secs. 2.2.2, 3.1); a cut in energy units changes meaning when the noise changes.
- **Longitudinal separation is helped by a large `lambda_int / X0`.** Hadronic showers start later than
  electromagnetic ones, the more so in a high-`Z` absorber with a large ratio, about 28 for tungsten
  (arXiv:1802.00672, sec. I, PDF p. 2, top).
- **The ambiguity is an output.** When a resolution step (track quality, conversion vertex, `E/p`) cannot
  settle whether a cluster is an electron or a photon, both objects are kept, flagged ambiguous
  (arXiv:1908.00005 sec. 4.4, Fig. 4, p. 13); an analysis picks one per cluster before counting or summing.
- **Two-shower separation is measured, not assumed.** Overlay two single-shower test-beam events at known
  displacements and record the probability of recovering both versus distance (event mixing;
  arXiv:1802.00672 sec. III).

<!-- example: named apparatus and their numbers (collider, test beam and space instances of the rows above) -->
- ATLAS topological clusters: defaults `S = 4`, `N = 2`, `P = 0`, from pion test-beam optimisation; local maxima
  need `E > 500 MeV`, at least four neighbours and no larger neighbour; the shower-size scale for shared cells is
  5 cm for all calorimeters (arXiv:1603.02934 sec. 3.1, p. 15; sec. 3.1.3, p. 18, footnote 6).
- CMS ECAL: clusters seeded at local maxima above 1 GeV share cells by a Gaussian profile (arXiv:2012.06888
  sec. 4.2, PDF p. 8, opening paragraph);
  mustache superclusters, spread in `phi` by the solenoid field (same sec., PDF p. 9). `sigma_ieta_ieta` uses
  `W0 = 4.7` over the 5x5 array, so a crystal counts above 0.9% of `E_5x5` (sec. 7.1, eq. 7, p. 36).
  Preshower: `alpha = 0.7`, `G = 0.023 +- 0.002 (stat) +- 0.001
  (syst) GeV/MIP`, 6 to 8% of the shower energy in the preshower (arXiv:1306.2016 sec. 4.3, p. 19-20).
- ATLAS EM barrel module in test beam: best `w0` 2.0 in the front and 4.4 in the middle compartment, 2.2 in the
  end-cap front (arXiv:physics/0505127 sec. 3.1, p. 9).
- ILC LumiCal prototype: best radial resolution at `W0 = 3.4` for that configuration, from simulation
  (arXiv:1812.11426 sec. 7.1, p. 9).
- BTeV PbWO4 prototype: `sigma_x = (0.16 +- 0.06) (+) (2.80 +- 0.08)/sqrt(E)` mm (E in GeV), 3x3 crystals
  (arXiv:hep-ex/0209055 sec. 8, eq. 3, p. 16; mm and 3x3 crystals: Fig. 15, p. 18).
- Fermi-LAT CsI calorimeter: Pass 8's minimum-spanning-tree
  clustering separates ghost signals, with a 5 to 10% gain in effective area above about 1 GeV
  (arXiv:1303.3514 sec. 2.2.1, p. 3). Tracker energy added (arXiv:1206.1896 sec. 3.2.1, p. 41).
- DAMPE BGO: `zeta_DAMPE = F_last (sum_i RMS_i / mm)^4 / (8 x 10^6)` (equation 2, unrelated to `zeta_i`) separates
  electrons from protons (arXiv:1711.10981 Methods, p. 11); gap correction with a core-energy ratio,
  rear leakage from the fitted `t_max` (arXiv:1703.02821 secs. III.A-B, pp. 3-4).
- DREAM copper-fibre calorimeter: `h/e` of 0.21 (Cherenkov) and 0.77 (scintillation), `chi` about 0.3
  (arXiv:1703.09120 sec. 3.1, eqs. 1-2, p. 10).
- CALICE SiW ECAL physics prototype: 1x1 cm2 cells, 30 layers, 24 `X0`; two-shower success needs both energies
  within 20% and barycentres within 5 mm (arXiv:1802.00672 secs. II-III, pp. 2-3).
<!-- /example -->

## Distinctive but generalizable features (calorimeter clusters)

- **Topology**: a sparse 2D or 3D image of cell energies, projective or not, layered or unsegmented in depth.
- **Inverse problem**: number, energy, position and direction of the particles in the deposit; one broad
  shower, two close showers and a shower plus noise or a stray deposit are degenerate.
- **Natural objects**: cell, cluster, split cluster, supercluster, preshower cluster. **Informative residual**:
  centroid minus an independent impact point versus position in the cell (the S-curve), and cluster energy over
  a reference (`E/p`, a mass constraint, or the beam energy) versus shape variables.
- **Scaling**: position resolution `sigma_x = a/sqrt(E) (+) b`; the logarithmic cut-off at `exp(-W0)` of the
  normalising energy `E` (cluster, compartment or fixed array); two-shower separation set by the Molière radius over
  the cell size.
- **Conventions**: the depth at which a position is quoted; cell or length units for moments; the log-weight
  normalising energy.
- **Tails**: merged showers, lost brem or conversion legs, leakage through cracks and the rear, saturated cells.
- **Dependence**: noise and overlap, upstream material, incidence angle, field, occupancy.
- **Data sample**: test beams with a telescope (FXT); electrons from a dilepton resonance and photons from a
  radiative decay (COL); flight electrons and protons with independent charge or track tags (SPC).
- **Transfers**: significance thresholds, log weighting, shape moments and event mixing, to any segmented
  calorimeter. **Does not transfer**: supercluster window shapes (field-specific), `W0` values, and
  preshower plane weights between geometries.

## Common misconceptions and failure modes

- **A single `W0` treated as universal.** It depends on cell size relative to the Molière radius and on the
  compartment; tune it per geometry and compartment.
- **S-curve corrections applied at another angle or energy.** The curve depends on the incidence angle
  (0-15 deg, arXiv:hep-ex/0209055 sec. 8, PDF pp. 15, 19) and on energy and (eta, phi) direction (arXiv:physics/0505127 sec. 3.1,
  p. 9); one prototype found it almost energy independent at normal incidence (arXiv:hep-ex/0209055 p. 15).
- **Noise-suppression thresholds in energy units carried across run conditions.** Seed, growth and boundary
  thresholds follow the noise; energy thresholds by design (local maxima, seed clusters) are stated with their
  run conditions and re-validated when those change.

## Deliverables to report

- Clustering method (window, seeded growth, graph), noise-suppression thresholds in noise units, energy-unit
  thresholds (local maxima, seed clusters), splitting rule and shared-cell weighting, with the run conditions
  they were set for; where showers are split or their separation is relied on (photon versus neutral pion), the
  separation curve (event mixing) with its angles and energies; without splitting, the merged-pair rate.
- Position method (linear plus S-curve, with the angle and energy domain the curve was derived in; or log
  weights with `W0`, its normalising energy, and the geometry, compartment, energy and angle of its tuning), the
  depth at which it is quoted, and the resolution versus energy, angle and position in the cell.
- Direction method (barycentres at depths, principal axis, preshower) and its resolution.
- Shape variables used for identification, their definitions (weights, cell array, units) and data/MC
  agreement on control samples.
- Energy corrections applied (gaps, upstream, lateral, rear) with their domain in energy and angle.
- For preshower and dual-readout calorimeters: plane weights and MIP calibration, and `chi` with how and on which
  sample it was measured.

## Tool hooks and checks

- **Inputs**: cell energies (GeV) after the cell chain, cell positions and sizes (mm) with layer index, per-cell
  noise (GeV) for the run conditions, optional tracks or conversion vertices.
- **Outputs**: clusters with energy, centroid at a stated depth, direction, second moments in cell units, core
  fractions, number of local maxima, and per-cell sharing fractions.
- **Conventions**: noise-suppression thresholds in cell-noise units; the log-weight normalising energy stated;
  deposited energy kept apart from corrected energy in the outputs.
- **Closure test and negative control**: scan impact points across one cell, with `W0` tuned for that geometry
  on a sample separate from the scan, its normalising energy stated; after log weighting (or an S-curve derived
  on an independent scan) the largest `|mean residual|` over impact-point bins, at each incidence angle and
  energy where the correction is used, must stay below a stated fraction of a
  resolution fixed in advance (the distortion "practically disappears", arXiv:physics/0505127 sec. 3.1, p. 9,
  its Fig. 5 on page 10, one test-beam module). The uncorrected linear centroid, the negative control, must fail it at
  one energy or more; where it passes, the closure there is inconclusive. Random-trigger events at the run
  conditions must give, per region, a per-cell RMS within a stated tolerance of the conditions `sigma_noise`
  (this catches a stale `sigma_noise`), and rates of `|zeta|` above `S`, `N` and `P` inside a binomial interval,
  at a stated confidence level and minimum expected count, of those from the noise of a disjoint random-trigger
  sample (`2 [1 - Phi(S)]` only if Gaussian; overlap noise is not, and `sigma_noise` holds for a nominal overlap,
  arXiv:1603.02934 sec. 2.2.2, pp. 11-12).
- **Statuses**: per cluster `ok`, `split` (more than one maximum), `ambiguous` (electron or photon), `edge`
  (near a crack or border), `saturated`, `insufficient-cells`, `out-of-range` (correction asked outside its domain),
  and per check (closure, noise) `passed`, `failed` or `inconclusive` (negative control passed).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Seeded and graph clustering | arxiv_1603.02934 (seeded; graph: gap) | gap: seeded test-beam tuning cited second-hand (arxiv_1603.02934) | arxiv_1303.3514 (graph; seeded: gap) | gap: per-view 2D clustering only ([LArTPC imaging](noble-liquid-neutrino-and-rare-event-detectors.md#imaging-reconstruction-in-single-phase-lartpcs)) | [image cleaning](imaging-atmospheric-cherenkov.md#image-cleaning-and-reconstruction-choices) (seeded) | gap: unsurveyed |
| Splitting and two-shower separation | arxiv_1603.02934 | arxiv_1802.00672 | gap | gap | gap: no image splitting read | gap: unsurveyed |
| Superclustering in a field | arxiv_2012.06888 | gap | gap: magnet spectrometers not read | gap | gap: geomagnetic spreading not read | gap: unsurveyed |
| Logarithmic weights | arxiv_2012.06888 (moment only; position: gap) | arxiv_1812.11426, arxiv_physics_0505127 | gap | gap | gap | gap: unsurveyed |
| S-curve derivation | gap: no track-based in-situ derivation read | arxiv_hep-ex_0209055, arxiv_physics_0505127 | gap | gap | gap | gap: unsurveyed |
| Direction (pointing from depths or principal axis) | pdg_2025_particle-detectors-at-accelerators | arxiv_physics_0505127 | arxiv_1206.1896 | gap | [fluorescence geometry](ground-based-detection-arrays.md#fluorescence-geometry-and-profile-reconstruction) | gap: unsurveyed |
| Shower shapes for identification | arxiv_2012.06888, arxiv_1908.00005 | gap | arxiv_1711.10981 | [e/γ showers](noble-liquid-neutrino-and-rare-event-detectors.md#imaging-reconstruction-in-single-phase-lartpcs) (start `dE/dx`, vertex gap) | [Hillas parameters](imaging-atmospheric-cherenkov.md#the-technique) | gap: unsurveyed |
| Photon versus neutral pion | arxiv_1908.00005, arxiv_1603.02934 | arxiv_1802.00672 | gap | gap | n/a: no single photons resolved | gap: unsurveyed |
| Converted photons | arxiv_1908.00005, arxiv_2012.06888 | gap | arxiv_1206.1896, [pair-conversion telescopes](gamma-ray-imaging-and-polarimetry-reconstruction.md#pair-conversion-gamma-ray-telescopes) | n/a: conversion inside the active volume | gap: geomagnetic conversion not read | gap: unsurveyed |
| Energy corrections | arxiv_2012.06888 | gap | arxiv_1703.02821, arxiv_1206.1896 | gap | [fluorescence energy](ground-based-detection-arrays.md#fluorescence-detectors) | gap: unsurveyed |
| Preshower | arxiv_1306.2016, arxiv_2012.06888 | arxiv_physics_0104033 (identification use only) | gap | gap | n/a: the atmosphere is the absorber | gap: unsurveyed |
| Dual readout | gap: proposed only (arxiv_1712.05494) | arxiv_1703.09120, arxiv_1712.05494 | gap: proposed only (arxiv_1712.05494) | gap | gap | gap: unsurveyed |
| Imaging and high granularity | gap | arxiv_0811.2354, arxiv_1802.00672 | arxiv_1901.00734, arxiv_1206.1896 | [LArTPC imaging](noble-liquid-neutrino-and-rare-event-detectors.md#imaging-reconstruction-in-single-phase-lartpcs) | gap | gap: unsurveyed |

`gap` marks content not found in the sources read; `n/a` gives the reason. NUC photon calorimeters were not
surveyed.

## Citations

Each source was read in its arXiv e-print (PDG: the 2025 review PDF) on 2026-11-17 to 2026-11-20; page numbers
are PDF pages. Full entries, with a DOI for all but two proceedings and the sections read, are in the split file
[detector-principles-bibliography-calorimetry.md](detector-principles-bibliography-calorimetry.md).
