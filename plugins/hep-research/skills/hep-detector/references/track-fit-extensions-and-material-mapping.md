# Track-Fit Extensions and Material Mapping

What the plain Kalman fit leaves out, and how to measure what the fit assumes: the Gaussian-sum filter for
radiating electrons, the deterministic annealing filter for outliers and left-right ambiguities, the broken-lines
global fit, propagation in non-uniform fields (including permanent magnets), the material model of the fit and its
measurement, and track resolution measured in data. Environments (R1 codes): COL, FXT, SPC; UGD only for sensor
positions (linked below); GND and NUC are gaps (no source read).

The Kalman fit, track finding, the Gluckstern terms and vertexing are in [tracking and
vertexing](tracking-and-vertexing.md); alignment, weak modes and the momentum scale in [calibration and
alignment](calibration-and-alignment.md#alignment-and-weak-modes) and [in-situ alignment and momentum
scale](in-situ-alignment-and-momentum-scale.md), solvers in [in-situ calibration methods](in-situ-calibration-methods.md);
pulls and widths in [performance metrics](performance-metrics-and-residual-diagnostics.md); the simulation geometry in
[detector simulation](detector-simulation.md#geometry-and-materials); nuclei lost in material in [nuclear interactions in
detector material](nuclear-interactions-in-detector-material.md). Sparse optical-module arrays (UGD), whose sensor
positions come from acoustic or light-travel-time systems: [neutrino astronomy](neutrino-astronomy.md#sensor-positions-and-orientations).

## Relations

| # | Relation | Label | Validity and source |
|---|---|---|---|
| 1 | Bethe-Heitler: `f(z) = (-ln z)^(c-1) / Gamma(c)`, `c = t / ln 2`, `z` the energy fraction kept, `t` the thickness in `X0` | approximate (model; fractional loss independent of energy) | arXiv:physics/0306087, sec. 1, Eq. 1, p. 1 |
| 2 | mixture for relation 1 from minimising `D_CDF = int abs(F - G) dz` or the Kullback-Leibler distance `D_KL = int ln(f/g) f dz` | approximate (fitted per thickness, parameters as polynomials in `t` within the fitted range) | sec. 2, Eqs. 2-3, p. 2 |
| 3 | annealed weight `w_i = exp(-chi2_i/2T) / (exp(-chi2_i/2T) + exp(-chi2_c/2T))`: `w = 1/2` at `chi2_c`; `T -> 0` is a hard cut | exact (definition) | inspire_753449 (preprint note, 2007), sec. 2, Eq. 4, p. 2 |
| 4 | vertex `ndof = -3 + 2 sum_i w_i` | exact (definition) | arXiv:1405.6569, sec. 6.1, Eq. 8, p. 50 |
| 5 | Highland: `theta_0 = 13.6 MeV/(beta c p) z sqrt(x/X0) (1 + 0.038 ln(x/X0))`, inverted for `x/X0` with the Lambert `W_0` function | approximate (Gaussian core of the projected angle; the Lynch-Dahl form with `ln(x/X0)` equals the `ln(x z^2/(X0 beta^2))` form of [E4](core-detector-equations.md) only for `z = 1`, `beta ~ 1`, as for the source's positron beam) | arXiv:2407.13721, sec. 1.1, Eqs. 1.1-1.2, p. 4 |
| 6 | split track: `R = (k_up - k_low)/(sqrt(2) k_low)`, pull `P = (k_up - k_low)/sqrt(sigma_up^2 + sigma_low^2)`, `k = q/p_T` | exact (definitions); the `sqrt(2)` holds for two independent halves of equal resolution | arXiv:1206.4071, sec. 6.2.1, Eqs. 7-8, p. 36 |
| 7 | unequal halves: `sigma_diff^2 = sigma_1^2 + sigma_2^2`, so `sigma_diff/sqrt(2)` is neither half | approximate (independent Gaussian halves; this page); the source corrects with simulation | arXiv:2310.12865, sec. 11.1, p. 23 |
| 8 | split vertex: `sigma_v = sigma_G(v_1 - v_2) / sqrt(2)`, `sigma_G` the width of a single Gaussian fitted within twice the RMS of the distribution | approximate (halves of equal kinematics) | arXiv:1405.6569, sec. 6.1.1, p. 50 |
| 9 | deflection `eta = 1/R`: `Delta eta_ms ∝ 1/R` (`beta ~ 1`) and `Delta eta_res = K`; the MDR is where `Delta R = R`, about `1/K` (this page) | approximate | arXiv:astro-ph/0608697, sec. 2.4, Fig. 12 and footnote, p. 17 |
| 10 | unbiased residual (hit excluded from the fit): `sigma_res^2 ≈ sigma_hit^2 + sigma_proj^2`, larger in outer layers | approximate (independence; this page) | arXiv:1712.02739, sec. 6, p. 9; sec. 8, p. 23 |

## Gaussian-sum filter

- **State as a mixture.** Every state is a weighted sum of Gaussians, each propagated by its own Kalman filter
  (arXiv:physics/0306087, sec. 1, pp. 1-2). At each layer every component splits into one per mixture component of
  relation 1, with the product of the weights (COL; arXiv:1405.6569, sec. 4.5.1, pp. 25-26); the mixture follows the
  effective thickness from the incidence angle (arXiv:physics/0306087, sec. 2, p. 2).
- **Component reduction** is the tunable approximation. Keeping the largest weights is inferior, with even the first
  two moments wrong; merging the heaviest component with its nearest (Kullback-Leibler distance) works (sec. 3,
  p. 2). The quality depends mainly on the maximum number kept (sec. 5, p. 5).
- **Mean or mode.** The `q/p` estimate is skewed, with tails from hard radiation in the innermost layers (p. 4); a
  vertex constraint reduces the skew and moves the mode toward zero (p. 5). State which summary is used.
- **Error quality.** In simulation, the estimated distribution integrated up to the true value should be flat; its
  `chi2` against flat measures the error model (sec. 4, p. 3).
- **Finding and quality.** Electron finding relaxes the hit compatibility and the missing-hit penalties (COL;
  arXiv:1405.6569, sec. 4.5.1, p. 25). A single fit-quality criterion is hard to define for a GSF; reject large residuals in any layer and large
  differences between the momenta in the first and last layers (FXT, simulation; arXiv:2410.10956, sec. 3.3.1,
  p. 19).

<!-- example: experiment-specific illustration (CMS tracker; Lohengrin proposal at ELSA, simulation; arXiv:1405.6569, arXiv:2410.10956) -->
CMS keeps at most 12 trajectory components (sec. 4.5.1, p. 26). Lohengrin (100 um silicon plus 1000 um
polyethylene per plane), in simulation of single electrons from a particle gun with truth-estimated seeding, removes
the outliers to a negligible level while keeping more than 97% of tracks; they come from bremsstrahlung in the first
layers that impairs the seeding (pp. 18-19).
<!-- /example -->

## Deterministic annealing filter

- **Weights from residuals.** A Kalman fit iterated with residual-based weights over an annealing scheme; competing
  measurements on one surface, including both sides of a wire, enter as their weighted average (arXiv:1410.3698,
  secs. 5-5.3, pp. 3-4). It ends when all weights change by less than a threshold (default `1e-3`), iterating at the last
  temperature, or at a maximum number of iterations, in which case it has not converged: record whether the weight
  criterion was met (p. 5).
- **Initialisation bias.** Starting both sides of a wire at weight 0.5 uses the wire positions with one common
  covariance and biases the fit; give smaller weights to larger drift radii (sec. 5.3, p. 4).
- **Drift chambers** (FXT; arXiv:2310.12865, sec. 8.2, p. 14): the filter rejects hits not from the particle and
  resolves left-right ambiguities; a longitudinal coordinate from the hit itself, weak as information, improves the
  bad-hit rejection.
- The same annealed weighting applied to tracks is the adaptive vertex fit (relations 3-4); it is sourced for COL
  only (inspire_753449; arXiv:1405.6569, sec. 6.1). Space pair-conversion vertices:
  [gamma-ray imaging](gamma-ray-imaging-and-polarimetry-reconstruction.md#pair-conversion-gamma-ray-telescopes).

<!-- example: software defaults (GENFIT in the Belle II framework; arXiv:1410.3698) -->
Kalman fits run 2 to 4 iterations by default, continuing while `chi2` changes by more than 20%; the DAF default
uses 5 temperatures and needed 6 iterations on average for 0.9 GeV tracks (secs. 5, 7, pp. 4-5).
<!-- /example -->

## Broken-lines global fit

Kinks at every thin scatterer, solved for the whole track at once: equivalent to a Kalman fit with thin scatterers
and the natural input to Millepede-II alignment (COL toolkit; arXiv:1410.3698, sec. 5.4, p. 5). Test-beam telescopes
use it with kinks at every plane and in the air between them; a two-tracklet model with one kink at the device under
test gives an unbiased material estimate there (FXT; arXiv:2011.12730, sec. 3.3, p. 8). The linear-time solve and
alignment use: [in-situ alignment](in-situ-alignment-and-momentum-scale.md) (relation 4).

## Propagation in non-uniform fields

- **Integration.** A fourth-order Runge-Kutta method with the step chosen from the agreement of fourth- and
  fifth-order predictions (COL; arXiv:1405.6569, sec. 4.3, pp. 21-22); Runge-Kutta-Nystroem steppers take the field
  as input and reproduce a helix in a constant field (arXiv:2106.13593, sec. 3.7, p. 12). Steps also stop at
  material boundaries and limit the momentum loss per step (arXiv:1410.3698, sec. 4, p. 3).
- **Analytic propagators bias** the fit where the field is least uniform; the Runge-Kutta propagator nearly removes
  the bias (arXiv:1405.6569, p. 22).
- **The field map is a measured condition.** Map the field before operation (COL); a permanent-magnet spectrometer
  maps its cavity and the surroundings with a Hall probe before flight (SPC; arXiv:astro-ph/0608697, sec. 2.4,
  p. 15). Record the map version, source and alignment with the conditions.
- **Field-to-tracker alignment and scale** (FXT; arXiv:2310.12865, sec. 10.3, pp. 21-22). In a gradient field a
  tracker misaligned to the field gives a momentum scale that varies with emission angle; align the map by
  minimising that variation, then calibrate the overall field scale on a kinematic edge.
- **Lever arm and tolerance.** Resolution follows the bending power along the actual path
  ([tracking](tracking-and-vertexing.md#propagation-in-a-non-uniform-field)); check the step tolerance against a
  fine-step reference and with track-parameter pulls against truth in simulation (their mean shifts), since a loose
  one can bias rigidity with little change in `chi2` or residual pulls.

<!-- example: experiment-specific illustration (CMS tracker, PAMELA, MEG II; arXiv:1405.6569, arXiv:astro-ph/0608697, arXiv:2310.12865) -->
CMS: the simple propagator biases `p_T = 10 GeV` tracks by up to 1% at `|eta| > 1`; the map was measured to
< 0.01% before collisions (sec. 4.3, p. 22). PAMELA: Nd-Fe-B blocks, a 0.43 T mean field and 0.48 T at the centre of
the cavity, with ferromagnetic shielding against the stray field (p. 15). MEG II: the computed field shifted by
100, 700 and 300 um in x, y and z, and its scale set to 0.9991 with 0.01% precision from the Michel edge (p. 22).
<!-- /example -->

## Material model of the fit, and its measurement

- **Simplified for reconstruction.** Average mixtures with an effective radiation length for scattering and
  bremsstrahlung and an effective ionization loss; small structures merged into nearby slabs; accuracy traded against
  speed per setup; effects applied as deterministic changes or added covariance (COL; arXiv:2106.13593, sec. 3.6.2,
  p. 11).
- **Mapping.** Project the detailed simulation material onto chosen surfaces or into volumes, homogeneous or
  binned (p. 11); compare the mapped and full material along tracks, and refine the binning where they differ
  (sec. 4.1, p. 16; FXT, simulation: arXiv:2410.10956, sec. 3.3.1, Fig. 18, p. 18).
- **Discrete scatterers.** Small elements that a track crosses or misses make the material budget unstable under
  small trajectory changes; smearing them over the volume can also degrade the fit, so validate the choice on data
  (FXT; arXiv:2310.12865, sec. 8.2, p. 14).
- **Measuring material in data.** Nuclear-interaction and conversion vertices image the material and validate its
  amount (COL; arXiv:1405.6569, sec. 2, p. 6; arXiv:1807.03289, abstract). A telescope at a low-energy beam measures
  `x/X0` maps from scattering-angle widths through the inverse of relation 5 (FXT; arXiv:2407.13721, abstract and
  secs. 4.4-4.5, pp. 18-19); scattering in the air between planes enters the uncertainty.
- **SPC:** no source read states a material map for a space instrument; a permanent-magnet spectrometer takes its
  spatial resolution and deflection error from beam tests before flight (arXiv:astro-ph/0608697, sec. 2.4, p. 17;
  flight-model ladders: [silicon hit reconstruction](silicon-hit-reconstruction.md)). Gap.

<!-- example: experiment-specific illustration (CMS tracker, Open Data Detector with ACTS, CMS Phase-2 pixel module at PSI; arXiv:1405.6569, arXiv:2106.13593, arXiv:2407.13721) -->
CMS: simulated material accurate to better than 10% (sec. 2, p. 6). Open Data Detector: mapped and Geant4 material
agree within a few percent (p. 16). Phase-2 module with a 40-65 MeV positron beam: x/X0 = (0.72 ± 0.05)% and
(0.95 ± 0.09)% in two regions against estimates of 0.753% and 0.892% (abstract); air scattering over 75% of the
uncertainty where x/X0 ≲ 1% (p. 19).
<!-- /example -->

## Track resolution measured in data

- **Split tracks.** Fit two halves of a cosmic track independently (relation 6), choosing tracks that resemble the
  physics sample; the pull width tests the fit errors; compare a core fit with the truncated RMS, as tails are
  non-Gaussian (COL; arXiv:1206.4071, sec. 6.2.1, p. 36). Pulls grow where hit errors omit the alignment uncertainty
  (p. 37).
- **Two turns of a looping track** are two tracks, but the halves differ in hit count; correct with the same analysis
  on simulation (relation 7; FXT; arXiv:2310.12865, sec. 11.1, pp. 22-23).
- **Split vertex.** Pair tracks by `p_T`, assign one of each pair to each half at random, fit both, divide by
  `sqrt(2)` (relation 8); an asymmetric split gives the vertex efficiency (COL; arXiv:1405.6569, secs. 6.1.1-6.1.2,
  pp. 50-51).
- **Unbiased residuals** exclude the hit; select high energy (in space, from the calorimeter) to suppress scattering
  (SPC; arXiv:1712.02739, secs. 6-6.1, p. 9); the width is an effective resolution including projection errors
  (relation 10); strip residuals are double Gaussian ([silicon hits](silicon-hit-reconstruction.md)).
- **Beam test** (SPC instrument before flight; arXiv:astro-ph/0608697, sec. 2.4, p. 17): deflection error versus
  rigidity with proton beams, fitted with a scattering and a constant spatial term, gives the MDR (relation 9); in
  flight the deflection was to be cross-checked with calorimeter energies of high-energy electrons (planned).
- Resonance widths, balance and source lines: [performance
  metrics](performance-metrics-and-residual-diagnostics.md#resolution-measured-in-data).

<!-- example: experiment-specific illustration (CMS muon system, MEG II, DAMPE, PAMELA; arXiv:1206.4071, arXiv:2310.12865, arXiv:1712.02739, arXiv:astro-ph/0608697) -->
CMS: tracker-only pull widths within ±10% of unity (p. 36). MEG II: about 15% of positron tracks cross the chamber in two turns (sec. 11.1, p. 22);
the double-turn core resolution in data and the simulated (reconstructed minus generated) Michel resolution differ by
0.02 mm in y_e and 0.43 mrad in phi_e; the same double-turn analysis on simulation is 0.10 mm and 0.55 mrad narrower
than data, and correction factors convert double-turn widths into resolutions (Tables 3-4, pp. 23-24). DAMPE: after
`E > 50 GeV` in the calorimeter, 47 ± 2 um for protons at normal incidence, outer layers 12 um worse on average (pp. 9, 23).
PAMELA: (3.0 ± 0.1) um in the bending view and an MDR of about 1 TV (p. 17).
<!-- /example -->

## Methods (decision table)

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| electrons in material | Gaussian-sum filter | mixture for the thickness range; component cap | summary (mean, mode) unstated; seeds lost after early radiation | COL, FXT (simulation) |
| outliers, wire ambiguity | deterministic annealing filter | annealing scheme; weight start | 0.5/0.5 start bias; weights never converge | COL, FXT |
| alignment, telescopes | broken-lines global fit | thin scatterers; material per plane | air or a device omitted from the kinks | COL, FXT |
| non-uniform field | adaptive Runge-Kutta with a measured map | map version and alignment | analytic propagator; loose tolerance | COL, SPC, FXT |
| gradient field | map alignment from angle-dependent scale, scale from an edge | kinematic edge or line | rotations not fitted | FXT |
| fit material | mapped surfaces or volumes | detailed material; binning | coarse bins; smeared discrete scatterers | COL, FXT |
| material in data | interaction vertices; scattering-angle `x/X0` | vertex sample; low-energy beam and telescope; fit-quality cut | air term; beam-energy error; the Highland model itself (no stated accuracy; `ln(x/X0)` form only for `z = 1`, `beta ~ 1`; [E4](core-detector-equations.md)) | COL, FXT |
| resolution in data | split track, two turns, split vertex | independent halves | unequal halves; correlated hits | COL, FXT |
| resolution in data | unbiased residuals with scattering suppressed; beam-test decomposition | energy selection; beams of known rigidity | projection error read as hit error | SPC |

Sourced in one environment only: the adaptive vertex fit (COL), field alignment from the angle-dependent scale
(FXT), unbiased residuals with a calorimeter selection and the beam-test decomposition (SPC; both are general methods,
but no second source was read).

## Distinctive but generalizable features

- **Topology:** a state per surface, transported through field and material; mixtures (electrons), weighted hit
  sets (annealing) or kinks (broken lines).
- **Inverse problem:** track parameters given hits, field map and material model; material and field are themselves
  measured (interaction vertices, scattering widths, Hall-probe maps, kinematic edges).
- **Natural objects:** mixture components, hit weights, kinks, field-map voxels, material bins, split halves.
- **Informative residual:** pulls and split-half differences; scale against emission angle; mapped minus full
  material along tracks.
- **Scaling:** relations 5, 6, 9 and 10; the GSF cost grows with the components kept.
- **Conventions:** `q/p` or `q/p_T`, deflection `1/R`; the MDR as 100% rigidity uncertainty; weight 1/2 at
  `chi2_c`.
- **Tails:** hard bremsstrahlung early on the track; mis-assigned hits; tracks through weak bending power.
- **Dependence:** field map and its alignment, material model and binning, hit-error model, momentum.
- **Data sample:** cosmic tracks, looping tracks, vertices, beam tests, high-energy selections.
- **Transfers:** the methods are geometry-free; mixture parameters, temperatures, component caps and map binning are
  tuned per detector.

## Common misconceptions and failure modes

- **A GSF momentum quoted without saying mean or mode.**
- **Splitting halves that are correlated or of unequal resolution and dividing by `sqrt(2)`.** Use disjoint hits
  and no shared seed or constraint: a correlation `rho` between equal halves biases `sigma_diff/sqrt(2)` low by
  `sqrt(1 - rho)` (this page). Relation 7 alone cannot separate unequal halves; correct with the ratio of the true
  resolution to the split-half width found on simulated pairs, per variable, and with a ratio to the physics sample if
  it differs (arXiv:2310.12865, sec. 11.1, Table 4, p. 24).
- **Unbiased residual width read as the hit resolution.** It includes the projection error (relation 10).
- **Material model judged by the simulation alone.** Measure it (interaction vertices, `x/X0` maps).
- **Field map taken as exact.** Its alignment and scale are calibration constants with uncertainties.
- **Pull widths at high momentum near 1 assumed.** Omitted alignment uncertainties widen them.

## Deliverables

- Fitter per particle type: GSF mixture, component cap and summary; annealing scheme and weight start.
- Propagator, step tolerance and its validation; field-map version, source, alignment and scale.
- Material model (mapping, binning, discrete-element treatment) and its validation in data.
- Resolution in data: method, half definitions and corrections, pull widths, simulation comparison.

## Tool hooks

No script yet. A tool takes paired estimates of one quantity from two halves (`q/p` in c/GeV or positions in mm),
their fit errors, shared hits per pair, shared-seed and common-constraint flags, and the hit counts, lever arm, field
region and material of each half, for data pairs and for simulation pairs with truth; the binning variable; and, fixed
before the fit, the core-fit range, truncation level, declared fraction and split-width tolerance (relative to the
smaller; at most 0.1, 0.2), correlation bound (at most 0.1), pull band (within 1 ± 0.1), tails ratio (at most 1.5) and
minimum numbers of data and of simulation pairs (at least 200 each: a 5% error on a width); bounds are tool
conventions. Under every status it returns per bin, as diagnostics, `sigma_diff/sqrt(2)`, the pull width with its
uncertainty, the truncated RMS and, given simulation pairs, the factor `sigma_truth/sigma_split` per variable
(`sigma_truth` from reconstructed minus generated values of the full simulated track), the corrected resolution of
that sample, both split widths and, given simulated physics-sample tracks, the ratio to that sample (relation 7;
arXiv:2310.12865, sec. 11.1, Eq. 7, Tables 3-4, pp. 23-24). **Negative controls** (fit errors equal to each half's
`sigma`): (a) equal halves drawn with known `sigma`, with simulation pairs of the same halves and truth width `sigma`,
must return `ok` with `sigma` within the statistical error; (b) halves with `sigma_2 = 1.5 sigma_1` and equal hit
counts, simulation pairs of the same inequality and both bounds at their maximum, must return `ok-corrected` with the
simulated truth width within the statistical error; (c) (a) or (b) without simulation pairs must return
`unequal-halves-untested`; (d) equal halves with shared hits, with only a shared seed, or with only a common
constraint must each return `correlated-halves`; (e) (b), and (b) with `sigma_2 = 1.3 sigma_1`, with simulation pairs
of two `sigma_1` halves must return `sim-data-mismatch`; (f) equal halves with no shared hits or flags whose simulated
half errors correlate at 0.3 must return `correlated-halves`. Statuses, first match wins: `insufficient-pairs` (data,
or simulation pairs when given, below the minimum); `correlated-halves` (a shared hit, seed or constraint, or
simulated half errors `v_i - v_true` correlated beyond the bound); `unequal-halves-untested` (no simulation pairs:
equal hit counts do not establish equal halves); `unequal-halves` (simulated halves do not match the data ones in hit
counts, lever arm, field region or material: no correction applies); `sim-data-mismatch` (split widths, or the ratio
of the halves' mean fit errors, differ between data and simulation beyond the tolerance; an inequality neither shows
passes, so `ok` trusts the simulated halves); `pull-width-off` (outside the band); `tails-dominate` (truncated RMS and
core width differ beyond the ratio); `ok-corrected` (halves differ in those attributes, or in simulated width beyond
the fraction, or the factor differs from 1 beyond its error); `ok` (equal halves, factor consistent with 1). Only the
last two deliver a resolution, the corrected one; under other statuses the numbers are diagnostics, marked not a
resolution.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Gaussian-sum filter | arxiv_physics_0306087, arxiv_1405.6569 | arxiv_2410.10956 (simulation) | gap | gap | gap | gap |
| deterministic annealing filter | arxiv_1410.3698 | arxiv_2310.12865 | gap | gap | gap | gap |
| broken-lines fit | arxiv_1410.3698 | arxiv_2011.12730 | gap | gap | gap | gap |
| combinatorial Kalman finding | arxiv_2106.13593 | gap | arxiv_1206.1896, arxiv_1712.02739 ([tracking](tracking-and-vertexing.md#track-finding-strategies)) | gap | gap | gap |
| Hough or Legendre finding | arxiv_2412.14687 (simulation, proposed collider) | arxiv_1702.08082 (hadron calorimeter, test beam; [tracking](tracking-and-vertexing.md#track-finding-strategies)) | gap | gap | gap | gap |
| adaptive vertex fit | inspire_753449, arxiv_1405.6569 | gap | [gamma-ray imaging](gamma-ray-imaging-and-polarimetry-reconstruction.md) (two-track vertex, not adaptive) | gap | gap | gap |
| non-uniform field propagation | arxiv_1405.6569, arxiv_1410.3698, arxiv_2106.13593 | arxiv_2310.12865 | arxiv_astro-ph_0608697 | gap | gap | gap |
| fit material model | arxiv_2106.13593 | arxiv_2310.12865, arxiv_2410.10956 (simulation) | gap | gap | gap | gap |
| material measured in data | arxiv_1405.6569, arxiv_1807.03289 | arxiv_2407.13721; arxiv_2011.12730 (method only, no measurement) | gap | gap | gap | gap |
| split-track, two-turn, split-vertex resolution | arxiv_1206.4071, arxiv_1405.6569 | arxiv_2310.12865 | gap | gap | gap | gap |
| unbiased residuals, beam-test decomposition | gap | gap | arxiv_1712.02739, arxiv_astro-ph_0608697 | gap | gap | gap |
| sensor positions without tracks | gap | gap | gap | pdg_2025_particle-detectors-for-non-accelerator-physics, arxiv_1202.3894 ([neutrino astronomy](neutrino-astronomy.md)) | gap | gap |

## Citations

New entries: [calibration bibliography](detector-principles-bibliography-calibration.md). The main
[bibliography](detector-principles-bibliography.md) already lists the Gaussian-sum filter, adaptive vertex fit and
common tracking software papers and two tracker papers (arXiv:1405.6569, arXiv:1712.02739); the sections read for this
page are its locators. Pages are PDF indices of the versions read.

<!-- example: source citation (read versions) -->
The Gaussian-sum filter paper was read as its CHEP03 proceedings (arXiv:physics/0306087v1, eConf C0303241), not
the J. Phys. G 31 (2005) N9 version; the adaptive vertex fit as CMS NOTE 2007/008 from INSPIRE (the J. Phys. G 34
(2007) N343 version is paywalled).
<!-- /example -->
