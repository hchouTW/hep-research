# In-Situ Alignment and Momentum Scale

Positions and orientations of tracking elements and chambers, and the momentum scale (COL, UGD; the FXT momentum
scale and the SPC rigidity scale are gaps), solved from data: track-based global fits (Millepede-II with General
Broken Lines), iterative `chi2` methods, non-track positioning, and scale references. Environments (R1 codes): COL,
FXT, SPC, UGD; GND: no tracker alignment in the arrays read, and the rigidity scale of ground arrays (geomagnetic
methods such as the Moon-shadow shift) is a gap (no source read); NUC is a gap.

The general formulation (unknowns, reference sample, residual), the solvers, unconstrained modes and convergence
are in [in-situ calibration methods](in-situ-calibration-methods.md); this page applies them. Curvature weak modes,
their charge-antisymmetric bias and the constraints against them are in
[calibration and alignment](calibration-and-alignment.md#alignment-and-weak-modes); the track model in
[tracking and vertexing](tracking-and-vertexing.md); muon chambers in [muon systems](muon-systems.md).

## Relations

| # | Relation | Label | Validity and source |
|---|---|---|---|
| 1 | `chi2(p, q) = sum_tracks sum_meas ((m_ij - f_ij(p, q_j)) / sigma_ij)^2`, then `C' dp = b'` | exact objective; linearised solve, iterated if corrections are large | arXiv:1403.2286, sec. 4, Eqs. 1-2, PDF p. 9 |
| 2 | rigid-body hit correction `x_a = x + dX - y theta_Z`, `y_a = y + dY + x theta_Z`, `z_a = z + dZ - x theta_Y + y theta_X` | approximate (first order in the rotations; rotations about the origin of the xy frame in the plane where the sensor nominally sits, `x`, `y` global hit coordinates; for a pivot off that plane add `+ z theta_Y` to `x_a` and `- z theta_X` to `y_a`) | arXiv:1712.02739, sec. 5.2, Eqs. 2-4, p. 6 |
| 3 | residual in a plane `= dx + dz tan(theta)` for a horizontal shift `dx` and a vertical shift `dz` | approximate (small deviations) | arXiv:0904.2226, sec. 10.1, Fig. 27, p. 42 |
| 4 | General Broken Lines: kinks at scatterers give linear equations whose matrix solves in time linear in the number of measurements, with the full covariance along the track | exact for the linearised track model | arXiv:1201.4320, abstract and sec. 1, p. 1 |
| 5 | momentum scale double ratio `(P_range / P_fit)_data / (P_range / P_fit)_MC` | approximate (range scale known to its own systematic) | arXiv:0805.3170, sec. 2.4.1, p. 18 |
| 6 | expansion of a mechanical part `L = L_0 + k_T (T - T_0) + k_H (H - H_0)` | approximate (linear) | arXiv:1712.02739, Table 5, p. 18 |
| 7 | step halving when `chi2_next >= chi2_this - eps * abs(grad chi2) * abs(d)` | approximate (heuristic) | fixed track sample only; `eps` in [0, 1], reference 0.5, `eps = 1` never converges; arXiv:1712.02739, sec. 5.2.1, Eq. 7, pp. 7-8 |
| 8 | step halving when successive gradients give `cos(alpha) < eps`, `eps = 0.5` | approximate (heuristic) | tracks re-selected each iteration, where `chi2` cannot set the step; the source's baseline; sec. 5.2.2, Eq. 8, p. 8 |

## Track-based alignment

- **Global fit.** Millepede-II solves all alignment parameters with all track parameters eliminated (relation 1); the
  track model needs multiple scattering, which General Broken Lines provide (COL: arXiv:1403.2286, sec. 4.1,
  PDF pp. 10-11; arXiv:1201.4320, sec. 1, p. 1). FXT telescopes prealign by correlating each plane with a reference
  plane, track with loose cuts, then run an iterative `chi2` minimisation or Millepede-II, with
  straight-line, kinked or GBL tracks (arXiv:2011.12730, secs. 3.3 and 3.5, pp. 8-9).
- **Iterative global minimisation** (SPC, no explicit frame fixing): the total `chi2` of straight tracks over rigid
  sensors (relation 2) by gradient descent, all parameters at once; each sensor term is divided by the number of
  tracks crossing that sensor (arXiv:1712.02739, sec. 5.2, Eq. 5, pp. 6-7). With a fixed sample relation 7 halves the
  step: `eps = 0` oscillates and converges more slowly than the reference `eps = 0.5`, and with `eps = 1` the step
  collapses and it does not converge (sec. 5.2.1, pp. 7-8). With tracks re-selected each iteration `chi2` cannot set
  the step, and relation 8 is the source's baseline (sec. 5.2.2, p. 8). The source fixes no frame explicitly. Started
  from zero, gradient descent never moves along exact gauge directions (the gradient is orthogonal to them) and moves
  along weak modes slowly, so a converged `chi2` does not show the modes fixed: compute the Hessian eigenvalue
  spectrum at the solution (Tool hooks; this page's reasoning). Shifting elements by their mean residuals and
  iterating instead biases the parameters, more so with each iteration (arXiv:hep-ex/0208021, sec. 1, p. 1); FXT
  telescopes use residual centring only as a prealignment (arXiv:2011.12730, sec. 3.5, p. 9).
- **Hierarchy** (SPC): planes within a module from hit residuals, then modules from track segments crossing module
  boundaries, then the instrument to the spacecraft frame (arXiv:0904.2226, secs. 10.1-10.3, pp. 41-49).
- **Data sets together.** Align all tracking components simultaneously and use several data sets at once
  (collision tracks with cosmic tracks that link distant parts), because independent internal alignments need not
  give a good overall result (arXiv:hep-ex/0208021, sec. 3, p. 7).
- **Time dependence.** Alignment moves with temperature and humidity (relation 6); repeat it per period and check
  whether a finer period improves resolution (SPC: arXiv:1712.02739, sec. 7, pp. 17-18). Per-period stability:
  [calibration and alignment](calibration-and-alignment.md#monitoring-stability-over-time).

<!-- example: experiment-specific illustration (Fermi LAT tracker, on orbit; arXiv:0904.2226, sec. 10.1, p. 44) -->
Intra-tower alignment of 576 planes stops when no parameter moves by more than 0.01 um (1 urad) between successive
iterations, typically after 100 iterations.
<!-- /example -->

## Chambers and large structures

- **Material between chambers** (COL): multiple scattering moves the track by more than the chamber resolution, so
  procedures must be insensitive to it: align nearby structures relative to one another (no extrapolation through
  material, but no link between distant frames), or align chambers to tracks from the inner tracker
  (arXiv:0911.4022, sec. 1, p. 3).
- **Non-track positioning.** Photogrammetry and in-situ sensors monitor movements and measure the degrees of
  freedom tracks barely constrain (COL; arXiv:0911.4022, sec. 1, p. 3); photogrammetry also cross-checks the
  track-based result (sec. 3.2, p. 8). In large-volume detectors (UGD) light travel times between optical modules or
  acoustic transducers position the sensors, and the shadow of the Moon checks the absolute pointing (PDG RPP 2025,
  Particle detectors for non-accelerator physics, sec. 36.3.2, p. 20); [neutrino astronomy](neutrino-astronomy.md)
  gives the detector context, not these methods.

<!-- example: experiment-specific illustration (CMS muon system, 3.8 T solenoid; arXiv:0911.4022, sec. 1, p. 3) -->
Steel layers of 20-60 cm between the muon chambers deflect muons by 3-8 mm, large next to the 100-300 um intrinsic
resolution of the chambers; hence the two track-based approaches above.
<!-- /example -->

## Momentum scale

- **Resonances and cosmic muons** (COL): the dimuon mass constraints of the J/psi and the Z, in kinematic bins,
  calibrate the scale at low and intermediate `pT`; at high momentum cosmic-ray muons give the scale
  bias from the position of the minimum of the `q/pT` spectrum against simulation with injected biases (cosmics
  endpoint method) (arXiv:1206.4071, sec. 6, PDF p. 27, and sec. 6.2.2, PDF pp. 38-39;
  arXiv:1603.05598, abstract, p. 1). The extrapolation between the resonances is part of the uncertainty
  ([calibration standards](calibration-and-alignment.md#calibration-standards-and-their-pitfalls)); so is any
  extrapolation beyond the anchors used.
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
| straight tracks, scattering negligible, any number of elements | iterative global `chi2` (gradient descent); residual iteration only as prealignment | global frame fixed (reference element or zero-mean constraints); shear and `z` scale fixed too (a second reference element, a survey, or zero-mean-shear and zero-mean-`z`-scale constraints) | global, shear, `z`-scale and weak modes left free; step-size control (relations 7, 8); bias of residual iteration | SPC, FXT |
| chambers behind absorbers | local relative alignment, or alignment to inner-tracker tracks | scattering-insensitive residuals | distant frames unlinked | COL |
| degrees of freedom tracks barely see | photogrammetry, optical or acoustic positioning | sensors installed | survey frame versus track frame | COL, UGD |
| momentum scale with a resonance | mass versus kinematics | resonance rate | extrapolation beyond the anchor | COL |
| momentum scale at high momentum | cosmics endpoint: `q/pT` minimum against simulation with injected biases | cosmic muons through the tracker | charge-ratio differences between data and simulation (normalise each charge sign separately) | COL |
| momentum scale without a resonance | range versus curvature | stopping tracks; known mass and energy loss | range systematic | UGD |

One environment only: resonance scales and the cosmics endpoint are COL; range versus curvature is UGD in the
sources read.

## Distinctive but generalizable features

- **Topology:** layered planes or chambers; tracks link them, absorbers or gaps weaken the links.
- **Inverse problem:** global parameters from track residuals; degenerate along gauges and weak modes.
- **Natural objects:** hit residuals, segment mismatches, track-segment angles across module boundaries.
- **Informative residual:** residual means versus position, angle, charge sign and period.
- **Scaling:** precision per element improves as `1/sqrt(N)` with the tracks through it (scattering raises the
  per-track error) until weak modes or systematics (track model, material, time variation) limit it.
- **Conventions:** one reference element or zero mean shift and rotation fixes the global frame. With straight
  tracks a shear `dx = s z` and a `z` scale `z -> (1 + e) z` are absorbed by the slope `b` of `x = a + b z`, so they
  need a second reference element, a survey, or zero-mean-shear and zero-mean-`z`-scale constraints; a
  zero-mean-shear constraint alone leaves the `z` scale free.
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
identifiers and uncertainties, and optional constraint inputs (resonance-mass track pairs with the known mass and a
common vertex, vertex constraints, field-off or cosmic track sets); it returns per-element corrections (um, urad)
with uncertainties and the eigenvalue spectrum of the reduced matrix, or of the Hessian at the solution for solvers
that do not form one. A mode is unconstrained when its eigenvalue is below a fraction of the largest, declared
before the controls run and used unchanged in all of them. **Negative control:** a simulated barrel geometry with
the global gauges fixed and an injected twist (`dphi=tau*z`), fitted from track residuals alone with no constraint
input, must return `unconstrained-mode` naming the twist eigenvector, not corrections that absorb it; no constrained
mode may be flagged. **Positive controls:** (1) on the same input, an injected rigid misalignment of the constrained
degrees of freedom (all per-element parameters except the fixed gauges and the named weak modes) must return
`converged`, flagged `unconstrained-mode` for the twist (and any other named weak mode) only, with the injected
values recovered within their uncertainties; (2) with Z-mass track pairs sharing a vertex added, the same twist must
be recovered within its uncertainty, with its eigenvalue above the threshold, status `converged` without the twist
flag, and the constraint used reported. Statuses: `converged` or `not-converged`, with `unconstrained-mode` as a
flag on either; `converged` alone is not allowed while a mode is free. A scale or
curvature-offset residual goes to `propagate_scale_distortion.py` ([calibration residual
propagation](calibration-residual-propagation.md)).

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| global track fit (Millepede-II, GBL) | arxiv_1403.2286, arxiv_1201.4320, arxiv_hep-ex_0208021 | arxiv_2011.12730 (test beam) | gap | gap | gap: no tracker alignment in the arrays read | gap |
| iterative `chi2` alignment | gap | arxiv_2011.12730 (test beam) | arxiv_1712.02739, arxiv_0904.2226 | gap | gap: no tracker alignment in the arrays read | gap |
| chamber and large-structure alignment | arxiv_0911.4022 | gap | gap | pdg_2025_particle-detectors-for-non-accelerator-physics | gap | gap |
| momentum scale | arxiv_1206.4071, arxiv_1603.05598 | gap | gap (source not retrieved) | arxiv_0805.3170 | gap (geomagnetic methods such as the Moon-shadow shift; no source read) | gap |

## Citations

Full entries are in the hep-detector [bibliography](detector-principles-bibliography.md) and its split files (section
"In-situ calibration and alignment"). Page numbers are PDF page indices of the version read (printed folios can
differ). Sources: arXiv:1403.2286v2, arXiv:1201.4320v1, arXiv:2011.12730v2, arXiv:1712.02739v2, arXiv:0904.2226v1,
arXiv:hep-ex/0208021v1 (preprint), arXiv:0911.4022v2, arXiv:1206.4071v2, arXiv:1603.05598v2, arXiv:0805.3170v2; PDG
RPP 2025, Particle detectors for non-accelerator physics (rev. October 2025,
<https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-non-accel.pdf>; PDF pages equal its folios).
