# Resolution Shape Models

Parametric line shapes for a detector response or residual distribution, and when to use each: the
single-sided and double-sided Crystal Ball (and the correlation of their tail parameters), the Gaussian
plus pedestal, the core-plus-tail time PDF, the low-side hadronic tail, and the effective sigma. A
resolution is a model or an estimator; this page says which model fits which loss mechanism, what to quote
from it, and how to vary it. Width estimators (RMS, `sigma_68`, MAD, RMS90, double Gaussian), residuals and
pulls are in [performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md);
unbinned fitting, parameter correlations and goodness of fit are hep-statistics'
([likelihood fitting](../../hep-statistics/references/likelihood-fitting.md)); a response that no
parametric shape describes goes into a response matrix ([response and forward folding](response-and-forward-folding.md)).

Environments (R1 codes): COL collider; FXT fixed-target and test beam; SPC space and balloon; UGD
underground, neutrino and rare-event; GND ground-based cosmic-ray and gamma-ray arrays; NUC nuclear and
low-energy. The shapes are generic; the coverage table (part 8) says where each use was sourced.

## Relations

Write `t = (x - xbar) / sigma` for the standardized variable, `xbar` and `sigma` the Gaussian core's mean
and width.

- **Crystal Ball (CB), low-side tail** (exact, a definition; Das, arXiv:1603.08591, eq. 1; the original form
  is Gaiser, SLAC-R-255, Appendix F.1, eq. F-1):
  `f = exp(-t^2/2)` for `t > -alpha`;
  `f = A (B - t)^(-n)` for `t <= -alpha`, with `A = (n/|alpha|)^n exp(-|alpha|^2/2)` and
  `B = n/|alpha| - |alpha|`. Four shape parameters `xbar, sigma, alpha, n` (Das, p. 1); `A` and `B` are fixed by
  requiring the function and its first derivative to be continuous at the join (Gaiser, p. 179). A high-side
  tail is the mirror image (`t -> -t`).
- **Moments of the CB** (exact, follows from eq. 1): the power-law tail falls as `|t|^(-n)`, so the
  function is normalizable only for `n > 1`, has a finite mean only for `n > 2` and a finite variance only for
  `n > 3`. For `n <= 3` the RMS of the model does not exist and the sample RMS grows with the fit range.
- **Large-`n` limit** (exact limit of eq. 1 at fixed `alpha`): `A (B - t)^(-n) -> exp(alpha^2/2 + alpha t)` as
  `n -> infinity`, which is the exponential tail of the GaussExp function with `k = alpha` (Das, eq. 2). A
  data set whose tail is close to exponential therefore constrains `alpha` and leaves `n` free: this is the
  origin of the `alpha`-`n` correlation (Methods, row 3).
- **Double-sided Crystal Ball (DSCB)** (exact, a definition; arXiv:2012.06888, sec. 6.1, eq. 4): a
  Gaussian core for `-alpha_L <= t <= alpha_R` with independent power-law tails `(alpha_L, n_L)` below and
  `(alpha_R, n_R)` above, each joined as in eq. 1; six shape parameters `(mu, sigma, alpha_L, n_L, alpha_R, n_R)`
  plus the normalization.
- **ExpGaussExp** (exact, a definition; Das, eq. 3): exponential tails on both sides, joined at `-k_L` and
  `+k_H`; two parameters fewer than the DSCB (Das, abstract).
- **Gaussian plus pedestal** (a model, approximate: the floor is assumed flat over the fit range;
  arXiv:2001.01540, sec. 5.8, Fig. 12; arXiv:1912.08739, sec. 9.2, Fig. 9):
  `f(x) = N_s G(x; mu, sigma) + c`, with `c` the density of entries unrelated to the signal.
- **Core-plus-tail time PDF** (a model, approximate; arXiv:astro-ph/0407044, secs. 3.1.1 and 3.2.2): a
  Gaussian of width `sigma_g` for early and prompt residuals, joined smoothly to a one-sided late-time
  distribution (in that source a gamma distribution, eq. 17, for photon scattering), plus a flat term for
  random noise hits. The fitted `sigma_g` absorbs all timing uncertainties, not only the photodetector jitter
  (sec. 3.2.2).
- **Effective sigma** (exact, a definition with two conventions): the half-width of the interval containing
  68% of the entries, either the smallest such interval (arXiv:1703.02821, sec. IV) or the interval around
  the most probable value (arXiv:1306.2016, sec. 4.5). Both equal `sigma` for a Gaussian; they differ for an
  asymmetric shape.

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| One-sided losses: shower leakage or radiation, incomplete charge collection | Single-sided CB on the loss side | Loss on one side only; enough entries in the tail to see the join | `n` unconstrained (row 3); a tail on the other side ignored; RMS quoted for `n <= 3` | COL, FXT, UGD |
| Losses on both sides, or a regression of the per-object resolution | DSCB; quote the core `sigma` as the resolution and the four tail parameters | Both tails populated | Six correlated parameters; the core `sigma` read as the full width | COL, FXT |
| Tail looks exponential, or `n` runs to its bound | Fix `n` (state the value) and fit `alpha`, or use GaussExp / ExpGaussExp | Tail shape checked against the fixed choice | `alpha` quoted without the fixed `n`; results compared across different fixed `n` | COL (single environment, see row text below) |
| Entries unrelated to the signal (wrong matches, noise maxima, accidentals) | Gaussian plus pedestal; estimate the floor from a signal-free control (shifted timing or an off-signal region) | Flat floor over the fit range; control sample free of signal | Floor fitted only from the tails, so it trades against the core width; a non-flat floor | FXT, UGD |
| Times entering a likelihood (time residuals) | Core-plus-tail time PDF: Gaussian core, one-sided late tail, flat part | Tail mechanism known (slow shower components, scattering, late light); random hits rate | Tail cut instead of modelled, biasing the likelihood; `sigma_g` read as the photodetector jitter | COL, UGD |
| Hadronic or partially contained shower response | Low-side tail model if mild; a simulated response matrix with deconvolution if the containment is poor | Tail side checked for the observable (it is not universal) | Assuming a low-side tail where the mechanism gives a high-side one (E/p with neutral overlap); one shape across energies | COL, FXT, SPC |
| Shape unknown or not described by any of the above | Effective sigma or FWHM, stated with its convention | Enough entries for the quantile; bootstrap uncertainty | Conventions mixed in a comparison; a Gaussian formula used for its uncertainty | COL, SPC |
| Any quoted resolution | Name the line shape; vary it (Gaussian versus CB, fit range) and take the change as a systematic | An alternative shape that also describes the data | A single Gaussian fitted over the full range; the fit range not stated | COL, FXT |

**`alpha`-`n` correlation in one environment.** The two sources found that state it are COL or COL-derived
(Gaiser, Table 20 caption; Das, p. 1 and sec. 1). It is a property of the parametrization (the large-`n`
limit in Relations), so it applies wherever the CB is used; the FXT and UGD users in part 8 did not discuss
it, and no source from another environment stating it was found.

<!-- example: the Crystal Ball NaI(Tl) detector at SPEAR (Gaiser, SLAC-R-255, Appendix F) -->
The function was introduced for monoenergetic Bhabha electrons in a NaI(Tl) calorimeter; the fit gave
`sigma_E/E = 2.2%` at 1.547 GeV with `alpha = 1.5` and `n = 5.0` (printed p. 179). For the inclusive photon
spectra the fits "were found to be very insensitive to the power term in the range of 15.0-27.0, so it was
fixed at 15.0", and only the join parameter was fitted, at 0.744 to 0.919 (Table 20, printed p. 181).
<!-- /example -->

<!-- example: synthetic fits in Das, arXiv:1603.08591, Fig. 1 (page 3) -->
On random samples drawn from a GaussExp distribution, a CB fit gave `alpha = 0.7 +- 0.1`, `n = 10 +- 6`
(1000 points) and `alpha = 0.53 +- 0.02`, `n = 70 +- 60` (10000 points), and failed to converge for
100000 and 1000000 points, while the GaussExp fits gave `k = 0.51 +- 0.04` and `0.52 +- 0.01` (Fig. 1 and its
caption): as the sample grows `alpha` approaches `k` and `n` stays unconstrained, as the large-`n` limit
predicts.
<!-- /example -->

<!-- example: CMS electron and photon energy regression (arXiv:2012.06888, sec. 6.1, eqs. 4-5) -->
The regression predicts all six DSCB parameters per object; "the width of the Gaussian core sigma is the
estimate of the per-object energy resolution", and the most probable value `mu` is the energy correction.
<!-- /example -->

<!-- example: GridPix quad in a test-beam telescope (arXiv:2001.01540, sec. 5.8, Fig. 12) -->
The residual to the telescope track has long tails, partly from erroneously matched background tracks; their
number was estimated by shifting the telescope timing by 1000 frames, and the fit used a Gaussian with a
constant offset. The 35-ton LArTPC prototype (arXiv:1912.08739, sec. 9.2, Fig. 9) fitted Gaussians plus
constant offsets to the wire position of the largest standardized ADC value, where noise-only entries are
equally likely on every wire, which is why the floor is flat.
<!-- /example -->

<!-- example: ATLAS Tile Calorimeter cell times and AMANDA photon arrival times -->
Tile Calorimeter channel times (arXiv:1806.02129, sec. 3.1, Fig. 5) show a Gaussian core, a late tail more
evident at low energy from the slow hadronic shower component, and symmetric tails from out-of-time pileup
(COL), absent in data without pileup. AMANDA (arXiv:astro-ph/0407044, secs. 3.1.1, 3.2.1, 3.2.2) models the
photon time residual with the Pandel gamma distribution (eq. 17) for scattering in ice, extended to negative
residuals with a half Gaussian of width `sigma_g` joined by a spline at `t_1 = sqrt(2 pi) sigma_g`, plus random
noise hits (Fig. 4).
<!-- /example -->

<!-- example: hadronic and partially contained response (ACCESS prototype, DAMPE, ATLAS E/p) -->
A thin dual-readout prototype in a 375 GeV pion beam gave a scintillation signal skewed to low energy, as
expected from leakage (arXiv:1712.05494, sec. IV, Fig. 6). DAMPE's BGO calorimeter (about 1.6 nuclear
interaction lengths) gives a biased proton energy, so a simulated response with spectral deconvolution is used
(arXiv:1909.12860, Materials and Methods). In ATLAS E/p of isolated hadrons the long tail is on the high side,
from neutral background, with a small negative tail from noise (arXiv:1203.1302, sec. 4.4).
<!-- /example -->

<!-- example: line-shape systematics (ALICE FoCal-H prototype, CMS muon tag-and-probe) -->
The FoCal-H test-beam analysis varied the right-tail limit of a CB fit over 1, 1.5, 2 and 2.5 sigma and
compared Gaussian with CB fits; the line-shape choice gave `Delta sigma_stoch = 0.10`, larger than the
fit-range variation, 0.02 (arXiv:2311.07413, sec. 6.3, PDF p. 49); with non-Gaussian tails the resolution was
then quantified with the FWHM (sec. 7). CMS recomputed tag-and-probe efficiencies with a Gaussian instead of a
CB for the resonance (arXiv:1206.4071, sec. 5.1.3).
<!-- /example -->

## Distinctive but generalizable features (resolution shapes)

- **Topology**: a one-dimensional distribution of a response (`x_reco / x_true`, `x_reco - x_true`) or a
  residual, in a bin of the conditioning variables.
- **Inverse problem**: infer core, scale and tail parameters from that distribution; degeneracies are
  `alpha` against `n`, the pedestal level against the core width, and the core width against the fit range.
- **Natural objects**: a monoenergetic line (beam, source, resonance), a matched track residual, a hit time.
- **Informative residual**: data minus the fitted shape, especially at the join points and in the tails.
- **Scaling**: the core width follows the resolution terms of the detector; tail parameters change with energy
  and containment, so fit them per bin.
- **Conventions**: name the model and its parameters, the side of each tail, the fit range, whether `n` was
  fixed, and the effective-sigma convention (smallest interval or around the most probable value).
- **Tails**: leakage, radiation, incomplete charge collection, slow components, scattering, wrong matches,
  noise, and (COL) out-of-time pileup.
- **Dependence**: energy, angle and position (containment), rate, and the selection that defines the sample.
- **Data sample**: test beams of known energy, calibration lines, narrow resonances, matched tracks against a
  reference telescope, signal-free control samples for the floor.
- **Transfers**: a shape fitted in simulation transfers to data only with its parameters re-fitted or scaled
  ([data mc validation and detector systematics](data-mc-validation-and-detector-systematics.md)); a parametric
  shape becomes a response matrix when it no longer describes the data.

## Common misconceptions and failure modes

- **The RMS of a CB is the resolution.** For `n <= 3` the model's variance is infinite; quote the core
  `sigma` and the tail parameters, or an effective sigma.
- **A fitted `n` is a measurement.** It is usually unconstrained; fix it or use an exponential tail.
- **Comparing `alpha` across fits with different fixed `n`.** They are not the same quantity.
- **Tails are always on the low side.** The side follows the mechanism (E/p with neutral overlap or
  annihilation gives a high-side tail).
- **A pedestal fitted from the tails alone.** Constrain it from a signal-free control sample.
- **Cutting the late tail of a time distribution that enters a likelihood.** Model it.
- **`sigma_g` of a time PDF is the photodetector jitter.** It includes every timing uncertainty.
- **One effective sigma convention assumed.** Smallest interval and around the most probable value differ.
- **One line shape, no systematic.** Vary the shape and the fit range.

## Deliverables

- The named line shape with its formula, all fitted and fixed parameters (fixed ones marked), the fit
  range, and the fit quality ([likelihood fitting](../../hep-statistics/references/likelihood-fitting.md)).
- The core width and a tail measure (tail parameters or a tail fraction), never one number for both.
- For a pedestal: the control sample and the floor it gave.
- For quantile widths: the convention and a bootstrap uncertainty.
- The line-shape and fit-range systematics, and the shape used for each energy or angle bin.

## Tool hooks

A shape-fit tool (none exists yet; `build_response.py` gives the central `sigma68 = (q84 - q16)/2`, MAD and a
tail fraction, not a parametric shape) would take:

- **Inputs**: a weighted sample or histogram of the residual or response, its unit, the model (`gauss`,
  `cb_low`, `cb_high`, `dscb`, `gaussexp`, `expgaussexp`, `gauss_plus_const`), fixed parameters, the fit range,
  and optionally a signal-free control sample for the floor.
- **Outputs**: parameters with uncertainties and their correlation matrix, the core `sigma`, both
  effective-sigma conventions with bootstrap uncertainties, the tail fraction, the fit quality, and the change
  in core `sigma` against an alternative shape and fit range.
- **Units and conventions**: `sigma` in the unit of the input; `alpha` in units of `sigma`; tail sides stated.
- **Negative control**: a pure Gaussian sample must return a core `sigma` equal to the generated width within
  its uncertainty and a flagged unconstrained `n`; a CB sample with known `alpha` and fixed `n` must return them.
- **Statuses**: `ok`, `tail_unconstrained` (a tail parameter at its bound or with uncertainty comparable to its
  value), `moments_undefined` (`n <= 3`, no RMS reported), `shape_mismatch` (fit quality below threshold),
  `insufficient_entries`.

## Environment coverage

Cells: a source ID, `n/a` with a reason, `gap`, or a link to an environment-specific reference.

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Single-sided CB | inspire_183554, arxiv_1603.08591 | arxiv_2311.07413 | gap | arxiv_2604.25748 | gap | gap |
| DSCB | arxiv_2012.06888 | arxiv_2607.28477 | gap | gap | gap | gap |
| `alpha`-`n` correlation | inspire_183554, arxiv_1603.08591 | n/a: property of the function; users there did not discuss it | n/a: as FXT | n/a: as FXT | n/a: as FXT | n/a: as FXT |
| Gaussian plus pedestal | gap | arxiv_2001.01540 | gap | arxiv_1912.08739 | gap | gap |
| Core-plus-tail time PDF | arxiv_1806.02129 | gap | gap | arxiv_astro-ph_0407044; [neutrino astronomy](neutrino-astronomy.md) | gap | gap |
| Low-side hadronic tail | pdg_2025_particle-detectors-at-accelerators, arxiv_1203.1302 (high-side counterexample) | arxiv_1712.05494 | arxiv_1909.12860; [space based direct detection](space-based-direct-detection.md) | gap | gap | gap |
| Effective sigma | arxiv_1306.2016 | gap | arxiv_1703.02821 | [neutrino astronomy](neutrino-astronomy.md) (68% containment radius) | [imaging atmospheric cherenkov](imaging-atmospheric-cherenkov.md), [ground based detection arrays](ground-based-detection-arrays.md) (68% containment radius) | gap |
| Model choice as a systematic | arxiv_1206.4071, pdg_2025_particle-detectors-at-accelerators | arxiv_2311.07413 | gap | gap | gap | gap |

The 68% containment radius of a point-spread function is the two-dimensional analogue of the effective
sigma; those references own it. The single-sided CB in UGD is a germanium line with incomplete charge
collection, a use that also exists in NUC spectroscopy but was not sourced here (a gap).

## Citations

Read for this page (2026-11-19), in the format of
[detector principles bibliography](detector-principles-bibliography.md):

- J. E. Gaiser, "Charmonium spectroscopy from radiative decays of the J/psi and psi-prime", PhD thesis,
  Stanford University (1982), report SLAC-R-255, Appendix F.1 (eq. F-1, printed pp. 178-179) and Table 20.
  Origin of the Crystal Ball function.
- S. Das, "A simple alternative to the Crystal Ball function", arXiv:1603.08591 (2016), eqs. 1-3 and Fig. 1.
  CB closed form, GaussExp and ExpGaussExp, instability from `n`.
- Particle Data Group, S. Navas et al., Phys. Rev. D 110 (2024) 030001 and 2025 update, *Particle detectors at
  accelerators*, sec. 35.10.1.1 (p. 92). Hadronic response is non-Gaussian; state the line shape and the
  resolution definition.

<!-- example: apparatus papers read for this page (2026-11-19) -->
- CMS, JINST 16 (2021) P05014, DOI 10.1088/1748-0221/16/05/P05014, arXiv:2012.06888, sec. 6.1 (DSCB regression).
- CMS, JINST 8 (2013) P09009, DOI 10.1088/1748-0221/8/09/P09009, arXiv:1306.2016, sec. 4.5 (effective sigma).
- CMS, JINST 7 (2012) P10002, DOI 10.1088/1748-0221/7/10/P10002, arXiv:1206.4071, sec. 5.1.3 (shape systematic).
- ATLAS, Eur. Phys. J. C 78 (2018) 987, DOI 10.1140/epjc/s10052-018-6374-z, arXiv:1806.02129, sec. 3.1 (cell times).
- ATLAS, Eur. Phys. J. C 73 (2013) 2305, DOI 10.1140/epjc/s10052-013-2305-1, arXiv:1203.1302, sec. 4.4 (E/p tails).
- ALICE FoCal, M. Aehle et al., JINST 19 (2024) P07006, DOI 10.1088/1748-0221/19/07/P07006, arXiv:2311.07413,
  secs. 6.3 and 7.
- S. Ceravolo et al. (CRILIN), JINST 21 (2026) P09015, DOI 10.1088/1748-0221/21/09/P09015, arXiv:2607.28477,
  sec. 7.5.3.
- E. Sánchez García et al. (CONUS+), arXiv:2604.25748 (2026), sec. 4, Fig. 7.
- C. Ligtenberg et al. (GridPix quad), Nucl. Instrum. Meth. A 956 (2020) 163331, DOI 10.1016/j.nima.2019.163331,
  arXiv:2001.01540, sec. 5.8.
- D. L. Adams et al. (35-ton LArTPC), JINST 15 (2020) P03035, DOI 10.1088/1748-0221/15/03/P03035, arXiv:1912.08739,
  sec. 9.2.
- J. Ahrens et al. (AMANDA), Nucl. Instrum. Meth. A 524 (2004) 169-194, DOI 10.1016/j.nima.2004.01.065,
  arXiv:astro-ph/0407044, secs. 3.1.1-3.2.2.
- S. Lee, M. Livan and R. Wigmans, Rev. Mod. Phys. 90 (2018) 025002, DOI 10.1103/RevModPhys.90.025002,
  arXiv:1712.05494, sec. IV (ACCESS prototype).
- DAMPE, Q. An et al., Sci. Adv. 5 (2019) eaax3793, DOI 10.1126/sciadv.aax3793, arXiv:1909.12860, Materials and
  Methods.
- C. Yue et al. (DAMPE), Nucl. Instrum. Meth. A 856 (2017) 11-16, DOI 10.1016/j.nima.2017.03.013, arXiv:1703.02821
  (arXiv version read), sec. IV.
<!-- /example -->
