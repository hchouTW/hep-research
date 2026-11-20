# In-Situ Alignment and Momentum Scale

Positions and orientations of tracking elements and chambers, and the momentum (rigidity) scale, solved from data:
track-based global fits (Millepede-II with General Broken Lines), iterative `chi2` methods, non-track positioning,
and scale references. Environments (R1 codes): COL, FXT, SPC, UGD; GND n/a (no tracker in the arrays read, beyond
the sensor positioning of large volumes); NUC is a gap.

The general formulation (unknowns, reference sample, residual), the solvers, unconstrained modes and convergence
are in [in-situ calibration methods](in-situ-calibration-methods.md); this page applies them. Curvature weak modes,
their charge-antisymmetric bias and the constraints against them are in
[calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes); the track model in
[tracking and vertexing](tracking-and-vertexing.md); muon chambers in [muon systems](muon-systems.md).

## Relations

| # | Relation | Label | Validity and source |
|---|---|---|---|
| 1 | `chi2(p, q) = sum_tracks sum_meas ((m_ij - f_ij(p, q_j)) / sigma_ij)^2`, then `C' dp = b'` | exact objective; linearised solve, iterated if corrections are large | arXiv:1403.2286, sec. 4, Eqs. 1-2, pp. 9-10 |
| 2 | rigid-body hit correction `x_a = x + dX - y theta_Z`, `y_a = y + dY + x theta_Z`, `z_a = z + dZ - x theta_Y + y theta_X` | approximate (first order in the rotations) | arXiv:1712.02739, sec. 5.2, Eqs. 2-4, p. 6 |
| 3 | residual in a plane `= dx + dz tan(theta)` for a horizontal shift `dx` and a vertical shift `dz` | approximate (small deviations) | arXiv:0904.2226, sec. 10.1, Fig. 27, p. 42 |
| 4 | General Broken Lines: kinks at scatterers give linear equations whose matrix solves in time linear in the number of measurements, with the full covariance along the track | exact for the linearised track model | arXiv:1201.4320, abstract and sec. 1, p. 1 |
| 5 | momentum scale double ratio `(P_range / P_fit)_data / (P_range / P_fit)_MC` | approximate (range scale known to its own systematic) | arXiv:0805.3170, sec. 2.4.1, p. 18 |
| 6 | expansion of a mechanical part `L = L_0 + k_T (T - T_0) + k_H (H - H_0)` | approximate (linear) | arXiv:1712.02739, Table 5, p. 18 |

## Track-based alignment

- **Global fit.** Millepede-II solves all alignment parameters with all track parameters eliminated (relation 1);
  the track model needs multiple scattering, which General Broken Lines provide (COL: arXiv:1403.2286, sec. 4,
  pp. 9-10; arXiv:1201.4320, sec. 1, p. 1). FXT telescopes prealign by correlating each plane with a reference
  plane, track with loose cuts, then run an iterative `chi2` minimisation or Millepede-II, with straight-line,
  kinked or GBL tracks (arXiv:2011.12730, secs. 3.3 and 3.5, pp. 8-9).
- **Iterative global minimisation** (SPC): the total `chi2` of straight tracks over rigid sensors (relation 2) by
  gradient descent, all parameters at once; per-sensor track counts weight the sum (arXiv:1712.02739, sec. 5.2,
  pp. 6-7).
- **Hierarchy** (SPC): planes within a module from hit residuals, then modules from track segments crossing module
  boundaries, then the instrument to the spacecraft frame (arXiv:0904.2226, secs. 10.1-10.2, pp. 41-44).
- **Data sets together.** Align all tracking components simultaneously and use several data sets at once
  (collision tracks with cosmic tracks that link distant parts), because independent internal alignments need not
  give a good overall result (arXiv:hep-ex/0208021, sec. 3, p. 7).
- **Time dependence.** Alignment moves with temperature and humidity (relation 6); repeat it per period and check
  whether a finer period improves resolution (SPC: arXiv:1712.02739, sec. 7, pp. 17-18). Per-period stability:
  [calibration and alignment](calibration-and-alignment.md#monitoring-stability-over-time).

## Chambers and large structures

- **Material between chambers** (COL): multiple scattering moves the track by more than the chamber resolution, so
  procedures must be insensitive to it: align nearby structures relative to one another (no extrapolation through
  material, but no link between distant frames), or align chambers to tracks from the inner tracker
  (arXiv:0911.4022, sec. 1, p. 3).
- **Non-track positioning.** Photogrammetry and in-situ sensors monitor movements and measure the degrees of
  freedom tracks barely constrain (COL; arXiv:0911.4022, sec. 1, p. 3); photogrammetry also cross-checks the
  track-based result (sec. 3.2, p. 8). In large-volume detectors (UGD) light travel times between optical modules or
  acoustic transducers position the sensors, and the shadow of the Moon checks the absolute pointing (PDG RPP 2025,
  Particle detectors for non-accelerator physics, sec. 36.3.2, p. 20); see [neutrino astronomy](neutrino-astronomy.md).

<!-- example: experiment-specific illustration (CMS muon system, 3.8 T solenoid; arXiv:0911.4022, sec. 1, p. 3) -->
Steel layers of 20-60 cm between the muon chambers deflect muons by 3-8 mm, large next to the 100-300 um intrinsic
resolution of the chambers; hence the two track-based approaches above.
<!-- /example -->

## Momentum scale

- **Resonances** (COL): the dimuon masses of the J/psi and the Z, in bins of the kinematics; the low-mass resonance
  anchors low momenta, the Z higher ones (arXiv:1206.4071, abstract, p. 1; arXiv:1603.05598, abstract, p. 1). The
  extrapolation between and beyond them is part of the uncertainty
  ([calibration standards](calibration-and-alignment.md#calibration-standards-and-their-pitfalls)).
- **Range versus curvature** (UGD, magnetized iron): stopping muons have a momentum from range and one from
  curvature; the data-to-simulation double ratio (relation 5) tests the field map and the curvature scale, limited
  by the range systematic (detector mass, geometry, energy-loss model) (arXiv:0805.3170, sec. 2.4.1, pp. 17-18).
- **SPC rigidity scale:** a dedicated source exists but was not retrieved; no SPC method is stated here (gap).

<!-- example: experiment-specific illustration (momentum-scale precision) -->
CMS, pp at 7 TeV, 40 pb^-1: the overall muon momentum scale is measured to 0.2% with muons from Z decays
(arXiv:1206.4071, abstract). ATLAS, pp at 13 TeV, 3.2 fb^-1: the momentum scale in the central region is known to
0.05%, and to about 0.2% for low-pT muons from J/psi at |eta| > 2.2 (arXiv:1603.05598, abstract). MINOS near
detector: the range-to-curvature double ratio is about 1.01, with a 2% systematic on the range momentum
(arXiv:0805.3170, sec. 2.4.1, p. 18).
<!-- /example -->

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| many elements, tracks with scattering | Millepede-II with GBL | track model with material; constraints on global modes | weak modes left free; linearisation with large corrections | COL, FXT |
| few elements, straight tracks | iterative global `chi2` (gradient descent) or residual iteration | reference element fixed | step-size control; bias of residual iteration | SPC, FXT |
| chambers behind absorbers | local relative alignment, or alignment to inner-tracker tracks | scattering-insensitive residuals | distant frames unlinked | COL |
| degrees of freedom tracks barely see | photogrammetry, optical or acoustic positioning | sensors installed | survey frame versus track frame | COL, UGD |
| momentum scale with a resonance | mass versus kinematics | resonance rate | extrapolation beyond the anchor | COL |
| momentum scale without a resonance | range versus curvature | stopping tracks; known mass and energy loss | range systematic | UGD |

One environment only: resonance scales are COL; range versus curvature is UGD in the sources read.

## Distinctive but generalizable features

- **Topology:** layered planes or chambers; tracks link them, absorbers or gaps weaken the links.
- **Inverse problem:** global parameters from track residuals; degenerate along gauges and weak modes.
- **Natural objects:** hit residuals, segment mismatches, track-segment angles across module boundaries.
- **Informative residual:** residual means versus position, angle, charge sign and period.
- **Scaling:** precision per element improves with tracks through it until scattering or modes limit it.
- **Conventions:** one reference element or zero mean shift and rotation fixes the global frame.
- **Tails:** wrong hit association, scattering tails, interacting particles in the sample.
- **Dependence:** temperature, humidity, magnet state, time since installation.
- **Data sample:** collision, beam and cosmic tracks; field-off tracks; stopping muons (UGD); orbit tracks (SPC).
- **Transfers:** the solvers and mode reasoning transfer to any tracker; collider resonance samples do not.

## Common misconceptions and failure modes

- **Good residuals taken as a correct geometry.** Weak modes leave them unchanged.
- **Subsystems aligned one by one.** The overall result can be wrong; align together with linking data sets.
- **A momentum scale extrapolated without an uncertainty** beyond its resonance anchors.
- **Survey positions mixed with track-based ones** without relating the two frames.

## Deliverables

- The alignment parameters per element, the solver, the track model and the data sets used.
- The global gauges fixed and the weak modes constrained, with the constraint used for each.
- Per-period alignment with its stability check, and the momentum-scale anchors with the extrapolated range.

## Tool hooks

No hep-detector script solves alignment. A tool built on this page takes per-hit residuals with track and element
identifiers and uncertainties; it returns per-element corrections (um, urad) with uncertainties and the eigenvalue
spectrum of the reduced matrix. **Negative control:** a simulated geometry with an injected weak mode (a twist)
must come back with the mode reported as unconstrained, not as aligned. Statuses: `converged`, `not-converged`,
`unconstrained-mode`. A scale or curvature-offset residual goes to `propagate_scale_distortion.py`
([calibration residual propagation](calibration-residual-propagation.md)).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| global track fit (Millepede-II, GBL) | arxiv_1403.2286, arxiv_1201.4320 | arxiv_2011.12730 | gap | gap | n/a: no tracker | gap |
| iterative `chi2` alignment | arxiv_hep-ex_0208021 | arxiv_2011.12730 | arxiv_1712.02739, arxiv_0904.2226 | gap | n/a: no tracker | gap |
| chamber and large-structure alignment | arxiv_0911.4022 | gap | gap | pdg_2025_particle-detectors-for-non-accelerator-physics | gap | gap |
| momentum scale | arxiv_1206.4071, arxiv_1603.05598 | gap | gap (source not retrieved) | arxiv_0805.3170 | n/a: no magnetic spectrometer | gap |

## Citations

Full entries are in the hep-detector [bibliography](detector-principles-bibliography.md) and its split files
(section "In-situ calibration and alignment"). Sources (the arXiv
version was read): arXiv:1403.2286, arXiv:1201.4320, arXiv:2011.12730, arXiv:1712.02739, arXiv:0904.2226,
arXiv:hep-ex/0208021 (preprint), arXiv:0911.4022, arXiv:1206.4071, arXiv:1603.05598, arXiv:0805.3170; PDG RPP 2025,
Particle detectors for non-accelerator physics.
