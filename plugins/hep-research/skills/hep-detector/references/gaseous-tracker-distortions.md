# Gaseous Tracker Distortions

How the drift field biases reconstructed drift coordinates, and how the bias is measured and corrected: space
charge in gas TPCs; in liquid-argon TPCs, apart, as gas ions come mainly from multiplication, liquid ones from
primary ionization (arXiv:2008.10472, sec. 1, fn. 1, p. 3); static field and `E x B` distortions; reference sources
for drift velocity, `t0` and maps; and the drift-chamber `r(t)`. Environments: COL, FXT, UGD; SPC, GND and NUC are
gaps (no source read).

Principles: [gaseous and specialized tracking technologies](gaseous-and-specialized-tracking-technologies.md);
transport and Lorentz angle: [signal formation](signal-formation-and-readout.md#charge-drift-diffusion-gain-losses);
LArTPC `dQ/dx` and recombination: [noble liquid
detectors](noble-liquid-neutrino-and-rare-event-detectors.md#imaging-reconstruction-in-single-phase-lartpcs);
residual solvers: [in-situ calibration methods](in-situ-calibration-methods.md); `t0` versus alignment: [case
studies](detector-case-studies-and-checklists.md) (Case 3); conditions: [calibration and
alignment](calibration-and-alignment.md#time-dependence-and-conditions-data); drift-velocity tables: [gas transport
tools](sensor-and-gas-transport-tools.md). Simulator parameter fits:
simcal ([hep-statistics](../../hep-statistics/references/core-stats-guide.md#skill-scripts)).

## Relations

| # | Relation | Label | Validity and source |
|---|---|---|---|
| 1 | `v_d = (e tau / m_e) / (1 + w^2 tau^2) * (E + (w tau / B) E x B + (w^2 tau^2 / B^2) (E . B) B)`, `w = eB/m_e`; for `E` perpendicular to `B`, `tan theta_B = w tau` | approximate (friction-force model) | moderate fields, `tau` from the `B = 0` drift velocity; Magboltz for precision; PDG RPP 2025, Particle detectors at accelerators, sec. 35.6.1, Eq. 35.14, pp. 26-27 |
| 2 | the `E x B` term vanishes for `E` parallel to `B`; for `w tau > 1` electrons follow `B`, so `E` non-uniformity matters less | approximate | PDG sec. 35.6.4, pp. 42-43; near amplification wires `E` and `B` are not parallel, much less so with MPGDs (p. 44) |
| 3 | `rho_SC` proportional to (rate x ion drift time) x primary ionization x `(1 + eps)`; `IB = (1 + eps) / G_eff`, so `eps` (ions fed back per primary electron) is about `gain x IBF` | definition exact; proportionality approximate (shape ignored) | arXiv:2109.12000, sec. 2, p. 2; arXiv:1209.0482, sec. 2, Eq. 5, p. 5 |
| 4 | backflow ions enter at the readout plane each time step and drift through: `N_ijn = N_ij^I + N_(i,j-1,n-1)`; equilibrium after `z_max / u+` | approximate (azimuthal symmetry, instantaneous electron drift) | arXiv:1209.0482, sec. 3, Eqs. 12-13, p. 6 |
| 5 | `sigma_SC / mu_SC = N_pile^(-1/2) sqrt(1 + (sigma_N/mu_N)^2 + (1 + (sigma_Q/mu_Q)^2) / F_mu)`: ion pile-up events, multiplicity spread, per-track charge spread, `F_mu` the tracks in the volume fraction | approximate (independent events) | arXiv:2109.12000, sec. 2, Eq. 1, p. 3; larger for small volume elements |
| 6 | LAr, one-dimensional: `alpha = (L/E_0) sqrt(K / (eps mu+))`, `E_x(x) = E_0 sqrt((E_a/E_0)^2 + alpha^2 (x/L)^2)`; the anode field vanishes for `alpha >= 2` | exact for uniform injection `K` and field-independent yield | arXiv:2008.10472, sec. 2.1, Eqs. 5-6, p. 4; recombination raises the threshold (sec. 2.3, p. 6) |
| 7 | `delta x_max = gamma L^3 K / (9 sqrt(3) E_0^2 eps mu+)` at `x = L/sqrt(3)` from the anode, `gamma = (dv_e/v_e)/(dE/E)` | approximate (first order in `alpha^2`) | sec. 2.2, Eqs. 9-11, p. 6; the ion-mobility uncertainty enters `alpha^2` directly (p. 5) |
| 8 | `t_meas = t0_channel + t_TOF + t_prop + t_L1 + t_drift = t0_channel + t_trig + t_drift`, pedestal `t_trig = t_TOF + t_prop + t_L1` (`t_L1`: Level-1 latency) | exact (decomposition) | arXiv:0911.4895, sec. 6.1, Eqs. 1-2, p. 10 |
| 9 | `v_eff = L_half-cell / <T_max>`, `T_max` from the mean-timer over three adjacent layers | approximate (linear `r(t)`) | sec. 7, Eq. 4, p. 13 |
| 10 | map as a tensor-product spline `s(z, r) = sum_ij gamma_ij M_i(z) N_j(r)`, solved from `A^T W A gamma = A^T W f` (Eq. 23 with `A' = wA`, `w^2 = W`) | exact (linear least squares, fixed knots) | arXiv:1209.0482, sec. 5.2, Eqs. 19-23, pp. 9-10 |

## Space charge in gas TPCs

- **Origin.** Ions drift slowly, so ions of many events coexist; the larger share comes from the amplification stage.
  A gating grid stops them but limits the rate to a few kHz; MPGD stacks reduce the backflow instead (PDG sec. 35.6.4,
  p. 44).
- **From density to distortion.** Poisson's equation gives the field, the Langevin equation the drift
  (arXiv:2109.12000, sec. 2, p. 2; arXiv:1209.0482, secs. 4.1-4.2, pp. 7-8). With the drift field parallel to `B`
  and a symmetric charge, the radial space-charge field still produces azimuthal shifts through the `E x B` term (p. 8).
- **Geometry is a parameter.** With a fixed target the forward boost makes the ionization asymmetric in `z` about
  the interaction point (FXT; p. 7).
- **Two time scales.** An average map collected over minutes, and fluctuations from the number of piled-up events
  (relation 5) corrected on a much shorter scale from integrated pad currents (COL; arXiv:2109.12000, sec. 3,
  pp. 4-5; arXiv:2003.03174, sec. 2, p. 3).
- **Data-driven map from external trackers** (COL; arXiv:2003.03174, sec. 2, p. 2): match with relaxed tolerances, refit
  with the inner and outer trackers only (keeping the cluster association), take cluster-minus-refit residuals per
  sub-volume, one vector each, then a kernel smoother that keeps real discontinuities; the minimum number of matched
  tracks sets the update interval (p. 3).
- **Laser grid and spline fit** (FXT, a simulation study; arXiv:1209.0482, secs. 5-6, pp. 8-12): straight tracks at
  known positions, hits within a tube around each beam, residuals perpendicular to the track, a spline surface
  (relation 10). Without symmetry or an optimal grid, large hit errors along each laser track limit residual-projection
  bias (sec. 5.2, p. 10; p. 12).

<!-- example: experiment-specific illustration (ALICE TPC, Pb-Pb at 50 kHz, Run 3 design; arXiv:2109.12000, arXiv:2003.03174) -->
GEM readout with IBF below 1%; an ion drift time near 200 ms piles up about 10000 events; relative density
fluctuations of about 2% give distortion fluctuations of several mm, corrected every 10 ms or so (arXiv:2109.12000,
secs. 1-2, pp. 2-3); Distortions of 10-15 cm are expected;
one map needs at least 450k matched tracks (arXiv:2003.03174, pp. 2-3).
<!-- /example -->

<!-- example: experiment-specific illustration (PANDA GEM-TPC design study, fixed target, simulation; arXiv:1209.0482) -->
IB = 0.25% with G_eff = 2000 gives eps = 4 (sec. 2, p. 5); drift
distortions up to 10 mm (abstract), spline map precision better than 100 um for azimuthally symmetric distortions on an
optimized laser grid, not counting mechanical distortions of the laser system (secs. 5.3 and 6, pp. 10, 12).
<!-- /example -->

## Space charge in liquid-argon TPCs

- **Origin and scaling.** Primary-ionization ions from the cosmic flux; `K` scales with the flux, so overburden is a
  parameter: the same detector underground showed no appreciable distortion (arXiv:2001.08934, abstract, p. 2).
- **Effects.** Ionization is reconstructed displaced, pulled toward the centre and more for longer drift
  (arXiv:2008.09765, sec. 1, pp. 5-6); the local field changes recombination, so `dQ/dx` to `dE/dx` needs a field
  map (p. 6; arXiv:2007.06722, sec. 6.1, p. 73).
- **Liquid flow.** Convection moves ions at a speed similar to their drift, so the distribution follows the flow;
  asymmetries appear and the simulation did not reproduce the data (FXT; sec. 6.1, pp. 73-74).
- **Cosmic-muon calibration** (UGD; arXiv:2008.09765, sec. 4, Fig. 6, pp. 12-13): `t0`-tagged tracks crossing the
  faces (anode-piercing tracks need no correction at the anode), then the cathode, then the bulk from nearly
  intersecting track pairs, which fix the offset in three dimensions; a nominal drift velocity from anode-to-cathode
  tracks comes first (sec. 4.1, p. 13). The spatial maps give the field map. Data-driven spatial and
  field maps are inverted for data and simulation alike (FXT; arXiv:2007.06722, sec. 6.1,
  p. 74).
- **Laser in a LArTPC** (UGD): true positions known (arXiv:1910.01430, sec. 2.2, pp. 8-9); coverage limited by the
  mirror motion (arXiv:2008.09765, sec. 4, p. 12), and beams miss the regions blocked by the field-cage rings and the
  anode region (arXiv:1910.01430, sec. 2.1, p. 8; p. 16). The anode gap takes a null-displacement boundary condition,
  and it and the ring shadows are filled by interpolation, which enlarges the effective map region (secs. 5.2 and 5.3,
  p. 16): mark such voxels (anode gap and ring shadows) interpolated, not covered.

<!-- example: experiment-specific illustration (MicroBooNE, ProtoDUNE-SP; arXiv:2008.09765, arXiv:1910.01430, arXiv:2007.06722) -->
MicroBooNE (surface): nominal drift
velocity to 0.4%, including a simulated 0.5 cm space-charge term given 100% uncertainty (sec. 4.1, p. 13); laser anode
gap about 50 cm, interpolation enlarging the effective map region by about 20% (arXiv:1910.01430, sec. 5.2, p. 16).
ProtoDUNE-SP: offsets up to 40 cm, data
up to twice the simulation in places, an asymmetry about the cathode absent from simulation (pp. 73-74).
<!-- /example -->

<!-- example: worked example (a 4 m LArTPC at the surface; arXiv:2008.10472) -->
K = 2 x 10^-10 C m^-3 s^-1, L = 4 m, E_0 = 500 V/cm, mu+ = 1.6 x 10^-7 m^2/(V s) and eps = 1.504 eps_0 give alpha =
0.78 (alpha grows as L, reaching 1 near 5.2 m; pp. 4-5) and, with gamma = 0.5, first-order delta x_max = 7.7 cm at
alpha^2 = 0.6, as the source applies it (p. 6); reported Ar+ mobilities span 0.8-2.0 x 10^-7 m^2/(V s) (p. 5), so
alpha^2 = 1.2 at the low end. Solving relation 6 numerically (v_e proportional to E^gamma, this page) gives 8.1 cm:
first order is 5% low here, 22% low at alpha = 1.5.
<!-- /example -->

## Static field distortions and E x B

- **Sources:** field-cage and readout imperfections, temperature variations, `E`-`B` misalignment, and moving
  charges (COL; arXiv:1001.1950, sec. 7, p. 32).
- **Tracks in all orientations** (UGD; arXiv:1012.0865, sec. 6.1, p. 26): a displaced line image
  has no unique set of displacements; a displaced point gives direction and magnitude. Field-off data give the
  electric distortions; field-on minus field-off the magnetic ones (sec. 6.3, p. 28).
- **Inhomogeneous drift field** (FXT, radial drift; arXiv:0801.4920, sec. 14, p. 24): the whole mobility curve is
  needed. Field-correction factors, a mobility curve and a time offset are fitted together to laser tracks without
  `B`; the fitted mobility differed significantly from Garfield/Magboltz.

<!-- example: experiment-specific illustration (T2K ND280 TPCs, ALICE TPC, CERES TPC; arXiv:1012.0865, arXiv:1001.1950, arXiv:0801.4920) -->
T2K ND280: a design requirement of construction distortions of about 0.2 mm or less against 0.7 mm point resolution
(sec. 2.1, p. 4); magnetic displacements normally below 1 mm, up to 5 mm in the most downstream TPC
(Fig. 19, p. 29). ALICE: a field-cage goal of 400 V/cm with relative field distortions (Delta E/E) in the 10^-4 range
(p. 3).
<!-- /example -->

## Reference sources for drift velocity, t0 and maps

- **UV laser tracks:** straight, at known positions, interspersed with physics events to follow the drift velocity;
  photoelectrons from the central electrode mark the maximum drift time (COL; arXiv:1001.1950, secs. 7-7.1, p. 32).
- **Photoelectron dots on the cathode:** drift velocity from laser trigger to arrival, distortions from dot
  displacements (UGD; arXiv:1012.0865, secs. 6-6.3, pp. 26-28).
- **Electrode photoelectrons and the drift-time edge** (FXT; arXiv:0801.4920, sec. 15, pp. 25-26): laser events
  monitor the drift velocity per event; the edge of the drift-time distribution of physics hits, with more events, was
  used in the end, as laser rate and upkeep were limiting.
- **Electrode-crossing tracks:** full drift time from anode-to-cathode tracks (UGD; arXiv:2008.09765, sec. 4.1, p. 13);
  cathode crossing tags `t0` (FXT; arXiv:2007.06722, sec. 6.1, p. 74).

<!-- example: experiment-specific illustration (CERES TPC, ALICE TPC; arXiv:0801.4920, arXiv:1001.1950) -->
CERES: laser 0.2 time bin per pad per event, an expected 0.003 bins or so combining 5120 pads, against 0.9 bins for
the edge method (pp. 25-26). ALICE: positions required to 800 um (r phi) and 1000 um (z) (p. 32).
<!-- /example -->

## Drift-chamber time-to-distance calibration

The drift time gives a distance only with the interaction time; field shaping makes `r(t)` more linear; resolution
degrades near the wire from primary-cluster statistics (PDG sec. 35.6.2.2, p. 31).

- **Pieces:** channel offsets from test pulses, then the time pedestal, then the drift velocity (COL; arXiv:0911.4895,
  secs. 3-7, pp. 5-13); per-cell `t0`, time walk (time versus amplitude per layer) and `r(t)` per layer, before the
  resolution is quoted with alignment (arXiv:1405.3397, sec. 1, p. 1; sec. 6, pp. 4-5).
  The pedestal is the turn-on of the drift-time distribution (time box), fitted with an integrated Gaussian; with
  cosmic rays, flat in arrival time within the clock cycle, that spread limits its precision (arXiv:0911.4895, secs. 3
  and 6.1, pp. 5, 10-11). Alternatively `t0` and `v_d` are free parameters of each track fit (sec. 3, p. 6).
- **Iterative `r(t)` from residuals:** start from Garfield++, calibrate per layer, fit piecewise cubic polynomials over
  drift-time regions; separate relations
  per voltage and threshold (FXT; arXiv:2106.02316, sec. 3.2, p. 9). The residual `d - d_fit` excludes the tested
  layer from the fit (sec. 3.1, p. 8).
- **Dependences:** per layer (cell size, field), left versus right, entrance angle (COL; arXiv:1405.3397, secs. 1, 7,
  pp. 1, 5); non-linear `r(t)` where the radial magnetic-field component is strongest (arXiv:0911.4895, sec. 3, p. 6);
  a field-free beam test leaves `B` and angle untested (arXiv:2106.02316, sec. 5, pp. 17-18).
- **Dead neighbours** change a cell's field: the `r(t)` bias grows with drift time and biases
  momenta; calibrate those cells separately (arXiv:1405.3397, pp. 4-5, Figs. 8-10).

**Diagnostics.** Residual versus drift distance (the standard plot): state the residual convention
([glossary](detector-glossary.md): signed track coordinate). In the signed coordinate a `t0` offset gives
opposite-sign residuals for left and right passages, a drift-velocity error a residual growing with distance, and a
wire offset the same sign on both sides; in the unsigned drift radius the `t0` and wire-offset patterns swap. Residual
versus angle and versus amplitude reveal time walk and crossing-angle effects.

<!-- example: experiment-specific illustration (BESIII drift chamber, CMS barrel drift tubes; arXiv:1405.3397, arXiv:0911.4895) -->
BESIII: 123 um averaged over cells for Bhabha tracks, below 65 um mid-cell in layer 25 (pp. 1,
5, Figs 11-12). CMS drift tubes (cosmic rays): 54.3 um/ns with a 10 ns pedestal uncertainty,
about 2.5% on the velocity (p. 13).
<!-- /example -->

## Methods (decision table)

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| gas TPC between undistorted trackers | residual map from refits without the TPC | trackers free of space charge; relaxed matching; tracks per interval | interval longer than the fluctuation time; smoothing over real steps | COL |
| fluctuations faster than the map interval | correction from integrated pad currents and the map's derivative | an average map | not yet demonstrated (design) | COL |
| laser grid | spline fit of residuals | known beam positions; grid covering the distortion directions | residual projection along the track; coverage holes | COL, FXT (simulation) |
| tracks in all orientations | point pattern, field on versus off | surveyed points | line patterns are ambiguous | UGD |
| inhomogeneous drift field | joint fit of field factors, mobility and `t0` | tracks at known positions, `B` off | simulated mobility used unchecked | FXT |
| LArTPC at the surface | `t0`-tagged faces, track pairs in the bulk, field map from offsets | electrode-crossing tracks; nominal `v_d` first | simulated ion distribution (flow); a reference that both corrects and validates the map | UGD, FXT |
| drift-velocity monitoring | laser or photoelectron timing; drift-time edge | stable optics; event rate | low laser rate | COL, FXT, UGD |
| drift chamber | pedestal from the time box; iterative `r(t)` per layer, side, angle, voltage and threshold | unbiased residuals; both sides populated; `t0` first, or `t0` and `v_d` fitted per track | dead neighbours; `B` and angle; `t0` absorbed in alignment | COL, FXT |

Sourced in one environment only (no other source read): the external-tracker residual map (COL), the fluctuation
correction (COL, a design), the point pattern (UGD) and the inhomogeneous-field fit (FXT).

## Distinctive but generalizable features

- **Topology:** a 3D displacement field, smooth in the bulk but with real discontinuities (gaps between readout
  planes) that smoothing must keep; in gas TPCs it follows the ion backflow per unit time, not rate alone: localized
  with triggered wire-chamber readout, over the whole volume with continuous GEM readout at higher rate
  (arXiv:2003.03174, pp. 1-2); in LArTPCs transverse offsets measured at the faces grow away from the anode, the
  interior extrapolated from them (arXiv:2007.06722, pp. 73, 77), the drift-coordinate distortion peaking near
  `L/sqrt(3)` from the anode to first order for uniform `K` in one dimension (relation 7); for drift cells, one
  `r(t)` per cell class.
- **Inverse problem:** displacement and field from residuals against references; `t0`, drift velocity and alignment
  can be degenerate along the drift coordinate (drift cells: when one side dominates the track population or the
  geometry is fixed; TPCs: unless a reference of known time or position fixes `t0`, such as crossing tracks, electrode
  photoelectrons, the drift-time edge, lasers, external trackers, a trigger or a bunch crossing).
- **Natural objects:** voxel residual vectors, laser or point images, time boxes, `r(t)` curves.
- **Informative residual:** versus drift distance, radius, `phi` and side; field on versus off; per period.
- **Scaling:** relations 3, 5, 6 and 7 (7 is first order in `alpha^2`: with `gamma` = 0.5, 5% low at `alpha` = 0.8, 22% at 1.5, so
  solve 6 numerically there; the anode field vanishes for `alpha >= 2`, about 2.5 with recombination): rate, ion drift
  time, primary ionization, backflow, pile-up and its spreads, `F_mu`, `K`, ion mobility, permittivity, `gamma`, drift
  length and field.
- **Conventions:** drift coordinate from the anode or readout; the sign of residuals (reconstructed minus true or
  reference).
- **Tails:** out-of-time tracks, mismatched references, cells beside dead channels.
- **Dependence:** rate, gas or liquid mobility, temperature and pressure, flow, `B`, time.
- **Data sample:** external trackers (COL), cosmic muons crossing electrodes (UGD, FXT), lasers and photoelectrons
  (all three).
- **Transfers:** residual mapping, spline smoothing and the `t0`-`v_d`-alignment degeneracy (drift cells: one side
  dominating or fixed geometry; TPCs: no reference of known time or position for `t0`) transfer to any drift detector;
  gas backflow numerology does not transfer to liquids, nor surface cosmic rates to underground.

## Common misconceptions and failure modes

- **A simulated space-charge map used as the correction.** Mobility (arXiv:2008.10472,
  p. 5) and flow (sec. 8, p. 21; arXiv:2007.06722, sec. 6.1, pp. 73-74) are uncertain; the correction comes from data; a
  map rescaled to face data keeps its simulated bulk, and the face-to-centre extrapolation drives the field-map
  uncertainty (pp. 74-77): check the interior independently.
- **A reference used to correct the map counted as its validation.** Keep a sample apart.
- **An average map used where fluctuations are faster than its interval.**
- **A transport simulation taken as the calibration.** Garfield/Magboltz is a start value; fit mobility and `r(t)`
  to data (simcal if simulator parameters are fitted).
- **Residuals that include the hit under test**, which pull `r(t)` toward the start value.

## Deliverables

- The distortion sources, the Scaling parameters and which dominate.
- The reference per map region, its coverage mask, and the sample kept apart for validation.
- The map: binning, smoothing, entries per voxel, interval, and the fluctuation treatment; for LArTPCs the field map.
- For drift chambers: calibration order, `r(t)` classes, separately treated cells, residual-versus-distance plots.

## Tool hooks

No script yet. A tool takes residual vectors (reconstructed minus reference, in cm, with uncertainties), their
coordinates (`r, phi, z` or `x, y, z`, drift coordinate from the readout), sample ids with reference type and region,
the time interval, the fluctuation time with its origin (measured or sourced), any fluctuation correction (method,
interval), the validation-sample ids, the binning, the smoothing kernel and the minimum entries per voxel, fixed
before the fit; it returns the map with per-voxel uncertainty, entries and a coverage mask with states covered,
interpolated, extrapolated (each with its boundary condition or method) and empty. For drift cells it takes hit times
and amplitudes (time walk), fitted distances excluding the hit, class keys (layer, side, angle bin, voltage,
threshold, dead-neighbour flag), the minimum entries per class, dead channels and the residual convention (signed or
unsigned), fixed before the fit, and returns `t0`, the time-walk correction per layer, `r(t)` per class and the
residual-versus-distance table. **Negative controls:** (a) inject a smooth field plus one step into pseudo-residuals:
the map recovers both within uncertainty or emits `smoothed-discontinuity` (voxels named); (b) zero distortion gives
pulls whose mean and width lie within three standard errors of 0 and 1 in each region and in all but the chance
fraction of voxels with the minimum entries, which must cover a declared fraction of the map (excluded fraction
reported); (c) in the signed track coordinate, a pure `t0` shift gives opposite-sign left and right residuals and is
assigned to `t0`, not to a wire offset; (d) with one side only, one side above a declared fraction of the tracks
(reported), or a fixed geometry, the same shift gives `t0-alignment-degenerate`. Statuses: `map-ok`,
`insufficient-entries` (voxels named), `interpolated` and `extrapolated` (voxels named), `no-coverage`, `stale-map`
(interval longer than the fluctuation time with no shorter fluctuation correction, or a fluctuation time neither
measured nor sourced), `reference-reused` (validation sample also built the map, or shares its reference type and
region, as a random split of the same tracks does), `smoothed-discontinuity`, and for drift cells `class-missing` (a
class of those keys without its own `r(t)` or below the minimum entries per class), `time-walk-missing` (amplitudes
given, no time-walk correction fitted), `t0-alignment-degenerate` and `convention-undeclared`.

## Environment coverage

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| gas-TPC space charge | pdg_2025_particle-detectors-at-accelerators, arxiv_2109.12000, arxiv_2003.03174 | arxiv_1209.0482 (simulation) | gap | gap | gap | gap |
| LArTPC space charge | n/a (no collider LArTPC) | arxiv_2007.06722 (test beam) | gap | arxiv_2008.10472, arxiv_2008.09765, arxiv_2001.08934; [noble liquid](noble-liquid-neutrino-and-rare-event-detectors.md) | gap | gap |
| static field, `E x B` | pdg_2025_particle-detectors-at-accelerators, arxiv_1001.1950 | arxiv_0801.4920 | gap | arxiv_1012.0865 | gap | gap |
| reference sources | arxiv_1001.1950, arxiv_2003.03174 | arxiv_0801.4920, arxiv_2007.06722 | gap | arxiv_1012.0865, arxiv_1910.01430, arxiv_2008.09765 | gap | gap |
| drift-chamber `r(t)` | pdg_2025_particle-detectors-at-accelerators, arxiv_1405.3397, arxiv_0911.4895 | arxiv_2106.02316 (test beam) | gap | gap | gap | gap |

## Citations

Entries: [calibration bibliography](detector-principles-bibliography-calibration.md); PDG RPP 2025 (1 December 2025
web update): main [bibliography](detector-principles-bibliography.md). Pages are PDF indices of the arXiv versions
(arXiv:1405.3397: pp. 2-3 not read).
