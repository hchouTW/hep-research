# Resolution Shape Models

Parametric line shapes for a detector response or residual distribution, and when to use each: single- and
double-sided Crystal Ball (with the correlation of their tail parameters), Gaussian plus pedestal, core-plus-tail
time PDF, hadronic or partially contained response, and effective sigma. Width estimators (RMS, `sigma_68`, MAD,
RMS90, double Gaussian), residuals and pulls are in
[performance metrics and residual diagnostics](performance-metrics-and-residual-diagnostics.md), whose `sigma_68`
is the central or the smallest form and whose resolution-models section links here for `sigma_eff`.
Unbinned fitting and goodness of fit are hep-statistics'
([likelihood fitting](../../hep-statistics/references/likelihood-fitting.md)); a response that no shape describes
is quoted as an effective sigma or FWHM (Methods, row 7) and, for folding or unfolding, goes into a response
matrix ([response and forward folding](response-and-forward-folding.md)).

Environment codes: COL collider; FXT fixed-target and test beam; SPC space and balloon; UGD underground,
neutrino and rare-event; GND ground-based cosmic-ray and gamma-ray arrays; NUC nuclear and low-energy.

## Relations

`t = (x - xbar) / sigma` is the standardized variable, with `xbar` (`mu` in the DSCB, the pedestal model and
the examples) and `sigma` the Gaussian core's mean and width.

- **Crystal Ball (CB), low-side tail** (exact, a definition; Das, arXiv:1603.08591, eq. 1; an early form is
  Gaiser, App. F.1, eq. F-1; Das p. 1 credits the Crystal Ball Collaboration, refs.
  6 and 8 there): `f = exp(-t^2/2)` for `t > -alpha`;
  `f = A (B - t)^(-n)` for `t <= -alpha`, with `A = (n/|alpha|)^n exp(-|alpha|^2/2)` and
  `B = n/|alpha| - |alpha|`, for `alpha > 0` and `n > 1` (normalizable, next item). `A` and `B` make the function
  and its first derivative continuous at the join (Gaiser, printed p. 179). A high-side tail is the mirror image
  `t -> -t`, not a negative `alpha` (this form is then discontinuous at the join); some implementations encode the
  side by the sign of `alpha`, so state the convention.
- **Moments of the CB** (exact, from eq. 1): the tail falls as `|t|^(-n)`, so the function is
  normalizable only for `n > 1`, with a finite mean only for `n > 2` and a finite variance only for `n > 3`.
- **Large-`n` limit** (exact limit of eq. 1 at fixed `alpha`): `A (B - t)^(-n) -> exp(alpha^2/2 + alpha t)` as
  `n -> infinity`, which is the exponential tail of the GaussExp function with `k = alpha` (Das, eq. 2). A
  near-exponential tail leaves `n` free; at finite `n` the best `alpha` shifts with `n` and tends to `k` as `n`
  grows, which is the `alpha`-`n` correlation (Methods, row 3; Das, Fig. 1).
- **Double-sided Crystal Ball (DSCB)** (exact, a definition; arXiv:2012.06888, sec. 6.1, eq. 4): a
  Gaussian core for `-alpha_L <= t <= alpha_R` with independent power-law tails `(alpha_L, n_L)` below and
  `(alpha_R, n_R)` above, each joined as in eq. 1; six shape parameters `(mu, sigma, alpha_L, n_L, alpha_R, n_R)`
  plus the normalization.
- **ExpGaussExp** (exact, a definition; Das, eq. 3): exponential tails on both sides, joined at `-k_L` and
  `+k_H`; two parameters fewer than the DSCB (Das, abstract).
- **Gaussian plus pedestal** (a model, approximate: the floor is assumed flat over the fit range;
  arXiv:2001.01540, sec. 5.8, Fig. 12; arXiv:1912.08739, sec. 9.2, Fig. 9):
  `f(x) = N_s G(x; mu, sigma) + c`, with `c` the density of entries unrelated to the signal.
- **Core-plus-tail time PDF** (a model, approximate; arXiv:astro-ph/0407044, secs. 3.1.1 and 3.2.2): a Gaussian of
  width `sigma_g` for early and prompt residuals, joined smoothly to a one-sided late tail (there a gamma
  distribution, eq. 17), plus a flat term for random noise hits. `sigma_g` is a free parameter (example below)
  and includes all timing uncertainties, not only the photodetector jitter (sec. 3.2.2). As a tool model
  (`gauss_late_tail_const`): core width `sigma_g`, join time `t_1`, a late-tail density `g_late(t; theta)` from
  the caller, and a flat random-hit density `c_r`.
- **Effective sigma** (exact, a definition with three conventions): the half-width of an interval holding 68.27% of
  the entries (the sources round it to 68%): the smallest such interval (arXiv:1703.02821, sec. IV), the interval
  around the most probable value (arXiv:1306.2016, sec. 4.5), or the central interval between the 15.87% and 84.13%
  quantiles, `(q84 - q16)/2` (the central `sigma_68` of
  [performance metrics](performance-metrics-and-residual-diagnostics.md) and `build_response.py`). All three equal
  `sigma` for a Gaussian; they differ for an asymmetric shape.

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| One-sided losses: shower leakage or radiation, incomplete charge collection | Single-sided CB on the loss side | Loss on one side only; enough entries in the tail to see the join | `n` unconstrained (row 3); a tail on the other side ignored; the RMS quoted as the resolution | COL, FXT, UGD |
| Losses on both sides, or a regression of the per-object resolution | DSCB; quote the core `sigma` as the resolution and the four tail parameters | Both tails populated | Six correlated parameters; the core `sigma` read as the full width | COL, FXT |
| Tail looks exponential, or `n` runs to its bound | Fix `n` (state the value) and fit `alpha`, or use GaussExp / ExpGaussExp | Tail shape checked against the fixed choice | `alpha` quoted without the fixed `n`; results compared across different fixed `n` | COL only (see below) |
| Entries unrelated to the signal (wrong matches, noise maxima, accidentals) | Gaussian plus pedestal; floor fixed, or constrained within the control's own uncertainty, from a signal-free control sample outside the fitted distribution (shifted timing, other channels, an off-time window) | Flat floor over the fit range and that control; or a floor flat by construction (argument recorded), fixed from a sideband chosen before the fit and excluded from the core fit, flagged `floor_from_tails` | Floor floated with the core, or constrained more loosely, so it trades against the core width; a non-flat floor | FXT (UGD: location fit only) |
| Times entering a likelihood (time residuals) | Core-plus-tail time PDF: Gaussian core, one-sided late tail, flat part | Tail mechanism known (slow shower components, scattering, late light); random hits rate | Tail cut instead of modelled, biasing the likelihood; `sigma_g` read as the photodetector jitter | UGD (COL: shape observed only) |
| Hadronic or partially contained shower response | A single-sided CB on the observed tail side (row 1, mirrored for a high-side tail), or a DSCB (row 2) if both sides have tails, while the fit in every energy bin passes (none of `fit_failed`, `shape_mismatch`, `insufficient_entries`, `tail_unconstrained` set); otherwise a simulated response matrix with deconvolution | Tail side checked for the observable | Assuming a low-side tail where the mechanism gives a high-side one (E/p with neutral overlap); one shape across energies | COL, FXT, SPC |
| Shape unknown or not described by any of the above | Effective sigma or FWHM with a tail fraction, stated with its convention | Enough entries for the quantile; bootstrap uncertainty | Conventions mixed in a comparison; a Gaussian formula used for its uncertainty | COL, FXT, SPC |
| Any quoted resolution | Name the line shape; vary it (Gaussian versus CB, fit range) and take the change as a systematic | The nominal and at least one alternative (Gaussian, CB, DSCB) pass the goodness of fit; if none does, list those tried and quote an effective sigma or FWHM (row 7) | A single Gaussian fitted over the full range; the fit range not stated | FXT (COL: efficiency fits only) |

**The `alpha`-`n` correlation is derived here** (Relations), a property of the function wherever the CB is
used. Gaiser (Table 20 caption: power term fixed) and Das (p. 1: `n` makes the CB fit unstable) report only that
`n` is unconstrained; the FXT and UGD uses do not discuss it.

<!-- example: the Crystal Ball NaI(Tl) detector at SPEAR (Gaiser, SLAC-R-255, App. F) -->
Introduced for monoenergetic Bhabha electrons in a NaI(Tl) calorimeter: `sigma_E/E = 2.2%` at 1.547 GeV with
`alpha = 1.5`, `n = 5.0` (printed p. 179). For inclusive photon spectra the fits were "very insensitive to the
power term in the range of 15.0-27.0, so it was fixed at 15.0" (Table 20, printed p. 181).
<!-- /example -->

<!-- example: synthetic fits in Das, arXiv:1603.08591, Fig. 1 (page 3) -->
On random samples drawn from a GaussExp distribution, a CB fit gave `alpha = 0.7 +- 0.1`, `n = 10 +- 6`
(1000 points) and `alpha = 0.53 +- 0.02`, `n = 70 +- 60` (10000 points), and did not converge for
larger samples, while the GaussExp fits gave `k = 0.51 +- 0.04` and `0.52 +- 0.01` (Fig. 1,
caption): `alpha` approaches `k` as the sample grows and `n` stays unconstrained.
<!-- /example -->

<!-- example: CMS electron and photon energy regression (arXiv:2012.06888, sec. 6.1, eqs. 4-5) -->
The regression predicts all six DSCB parameters per object; "the width of the Gaussian core sigma is the
estimate of the per-object energy resolution", and the most probable value `mu` is the energy correction.
<!-- /example -->

<!-- example: GridPix quad in a test-beam telescope (arXiv:2001.01540, sec. 5.8, Fig. 12) -->
Residual tails partly from wrongly matched background tracks, estimated by shifting the telescope timing by
1000 frames and shown for comparison; fit: a Gaussian with a free constant offset. The 35-ton LArTPC prototype
(arXiv:1912.08739, sec. 9.2, Fig. 9) fitted Gaussians plus constant offsets to the per-tick z of the wire with the
largest standardized ADC value, for the counters' central z (a location fit, not a resolution); noise-only entries
are equally likely on every wire, so the floor is flat.
<!-- /example -->

<!-- example: ATLAS Tile Calorimeter cell times and AMANDA photon arrival times -->
Tile Calorimeter channel times (arXiv:1806.02129, sec. 3.1, Fig. 5): a Gaussian core, a late tail from
the slow hadronic component, and symmetric out-of-time pileup tails (COL). AMANDA
(arXiv:astro-ph/0407044, secs. 3.1.1-3.2.2) models the photon time residual with the Pandel gamma distribution
(eq. 17) for scattering in ice, extended to negative residuals by a half Gaussian of width `sigma_g` joined by a
spline at `t_1 = sqrt(2 pi) sigma_g`, plus noise hits (Fig. 4); `10 ns <= sigma_g <= 20 ns` reconstructed well
(sec. 3.2.2).
<!-- /example -->

<!-- example: hadronic and partially contained response (ACCESS prototype, DAMPE, ATLAS E/p) -->
A thin dual-readout prototype in a 375 GeV pion beam: scintillation signal skewed low, from leakage
(arXiv:1712.05494, sec. IV, Fig. 6). DAMPE's BGO calorimeter biases the proton
energy, so a simulated response with spectral deconvolution is used (arXiv:1909.12860, Materials and
Methods). ATLAS E/p of isolated hadrons: long high-side tail from neutral background, small negative tail from
noise (arXiv:1203.1302, sec. 4.4).
<!-- /example -->

<!-- example: line-shape systematics (ALICE FoCal-H prototype, CMS muon tag-and-probe) -->
FoCal-H varied the right-tail limit of a CB fit (1, 1.5, 2, 2.5 sigma) and compared Gaussian with CB fits; the
line-shape choice gave `Delta sigma_stoch = 0.10`, larger than the fit-range variation, 0.02 (arXiv:2311.07413,
sec. 6.3, PDF p. 49); with non-Gaussian tails the resolution was then quantified with the FWHM (sec. 7). CMS
recomputed tag-and-probe efficiencies with a Gaussian instead of a CB as the resonance signal model
(arXiv:1206.4071, sec. 5.1.3): a shape systematic of an efficiency, not of a resolution.
<!-- /example -->

## Distinctive but generalizable features (resolution shapes)

- **Topology**: a 1D response (`x_reco / x_true`, `x_reco - x_true`) or residual per conditioning bin.
- **Inverse problem**: core, scale and tail parameters; degeneracies `alpha`-`n`, pedestal-core width, core
  width-fit range.
- **Natural objects**: a monoenergetic line (beam, source, resonance), a matched track residual, a hit time.
- **Informative residual**: data minus the fitted shape, at the join points and in the tails.
- **Scaling**: the core width follows the detector's resolution terms; tails change with energy and
  containment, so fit them per bin.
- **Conventions**: model, tail sides, fit range, fixed `n`, effective-sigma convention (Deliverables).
- **Tails**: leakage, radiation, incomplete charge collection, slow components, scattering, wrong matches,
  noise, and (COL) out-of-time pileup.
- **Dependence**: energy, angle, position (containment), rate, and the sample's selection.
- **Data sample**: test beams, calibration lines, narrow resonances, tracks matched to a telescope, signal-free
  controls for the floor.
- **Transfers** (guidance of this page): a shape fitted in simulation transfers to data only re-fitted in data
  with core and tail parameters free (any kept from simulation listed and checked against data), or scaled and
  accepted only if its goodness of fit in data passes in the same bin, core and tails (`shape_mismatch`,
  `insufficient_entries`, `fit_failed` not set), otherwise re-fitted or replaced by a response matrix;
  comparisons and smearing variations are in
  [data mc validation and detector systematics](data-mc-validation-and-detector-systematics.md).

## Common misconceptions and failure modes

- **The RMS of a CB is the resolution.** It is not: it mixes core and tail, has no finite RMS for `n <= 3`
  (infinite variance for `2 < n <= 3`, no mean if `n <= 2`, unnormalizable if `n <= 1`);
  for larger `n` it depends on `alpha` and `n`, diverging as `n -> 3` (from eq. 1: RMS/`sigma` 1.46, 1.29, 1.14
  at `alpha = 1.5` for `n = 4`, 5, 10; 1.03 at `alpha = 2.5`, `n = 4`), and the sample RMS depends on the fit range.
  Quote the core `sigma` with the
  tail parameters, or an effective sigma with a tail fraction.
- **A fitted `n` is a measurement.** It is usually unconstrained; fix it or use an exponential tail.
- **Comparing `alpha` across fits with different fixed `n`.** The definition is the same, but the fitted
  `alpha` depends on the fixed `n` (the `alpha`-`n` correlation), so the values are not comparable.
- **Tails are always on the low side.** The side follows the mechanism (E/p with neutral overlap or
  annihilation gives a high-side tail).
- **A pedestal floated with the core.** Fix or constrain it from a signal-free control; a floor flat by
  construction is fixed from a sideband chosen before the fit (argument recorded, flagged).
- **Cutting the late tail of a time distribution that enters a likelihood.** Model it.
- **One line shape, no systematic.** Vary the shape and the fit range.

## Deliverables

- The named line shape with its formula, all fitted and fixed parameters (fixed ones marked), the fit
  range, and the fit quality ([likelihood fitting](../../hep-statistics/references/likelihood-fitting.md)).
- A width and a tail measure, never one number for both: the core width with its tail parameters, or an
  effective sigma or FWHM with a tail fraction, its `k` and the `sigma_68` convention it multiplies.
- For a pedestal: the control sample (or the flatness argument and the sideband), the floor it gave, and the
  fitted floor.
- For quantile widths: the convention and a bootstrap uncertainty.
- The line-shape and fit-range systematics, and the shape used for each energy or angle bin.

## Tool hooks

A shape-fit tool (none yet; `build_response.py` gives `sigma68`, MAD and a tail fraction, no parametric
shape) would take:

- **Inputs**: a weighted sample or histogram of the residual or response, its unit, the model (`gauss`, `cb_low`,
  `cb_high`, `dscb`, `gaussexp`, `expgaussexp`, `gauss_plus_const`, and
  `gauss_late_tail_const` with its `g_late`), fixed parameters, parameter bounds, the fit range, the alternative
  models and fit ranges for the systematic, the named goodness-of-fit statistic, and the thresholds, all fixed
  before the fit: `gof_p_min` (default 0.05, from 0.05 to below 1), `tail_rel_unc_max` (default 0.5, at most 0.5),
  `n_max` (default 50, at most 50; Das, p. 4, rejects an `n` of 113 or 127), `min_entries` (default 100, at least
  100) and `min_tail_entries` (default 10, at least 10), counted as effective entries `(sum w)^2 / sum w^2`, and the
  tail-fraction threshold `k` (default 3, at most 3, as in `build_response.py`). Defaults and limits are this page's
  convention, not sourced; a non-default value is reported. For a flat term: a signal-free control sample, or for
  `gauss_late_tail_const` a measured random-hit rate.
- **Outputs**: parameters with uncertainties, their correlation matrix and the bounds, the core `sigma`, the three
  effective-sigma conventions and the FWHM with bootstrap uncertainties, the tail fraction
  `|r - median| > k sigma_68` (central `sigma_68`), the fit quality, the status set, the model RMS if its variance
  is finite (`moments_undefined` not set, for `g_late` as stated by the caller), all thresholds used, the floor's
  source with the control and the fitted floor, and the change in core `sigma` for each alternative model and
  fit range.
- **Units and conventions**: `sigma`, `sigma_g`, `t_1` in the input's unit; `c`, `c_r` in entries per input
  unit; `theta` in the units `g_late` defines; `alpha` (and `alpha_L`, `alpha_R`, `k`, `k_L`,
  `k_H`) in units of `sigma`; `n`, `n_L`, `n_R` dimensionless; tail sides stated.
- **Negative control** (fixed seeds stated with the test; a value matches when its pull is below 3, or over toys
  the pulls have mean 0 and width 1): a pure Gaussian sample fitted with `cb_low` and with `dscb` must return the
  generated width as core `sigma` and a status set containing `tail_unconstrained` (`moments_undefined` also
  allowed); `gauss_plus_const` without a control, or constrained more loosely than the control's uncertainty, must
  return `floor_from_tails`, and with the floor fixed from a signal-free control must not;
  an unconverged fit must return `fit_failed`, not `ok`, at any threshold. Positive control: a CB
  sample generated with known `alpha` and `n > 3`, fitted with that `n` fixed, at default thresholds and entries
  well above the minima, must return `alpha` with status `ok` for a seed recorded before the first run (over toys,
  `shape_mismatch` at a rate consistent with `gof_p_min` for calibrated p-values, `tail_unconstrained` and
  `fit_failed` below stated rates, and a DSCB sample fitted with `gauss` sets `shape_mismatch`; with a fixed
  `n <= 3` the set contains `moments_undefined`).
- **Statuses** (a set, all that apply are reported; `ok` only when no other is set): `ok`; `tail_unconstrained` (a
  tail parameter at its input bound, or with relative uncertainty above `tail_rel_unc_max` or undefined, or a
  fitted power above `n_max`); `moments_undefined` (any power `p` of `n`, `n_L`, `n_R` with `p <= 3` when
  fixed, or `p - sigma_p <= 3` when fitted; no RMS reported);
  `shape_mismatch` (the named statistic's p-value below `gof_p_min`); `floor_from_tails`
  (a flat term, in `gauss_plus_const` or `gauss_late_tail_const`, not fixed, or constrained within the
  control's own uncertainty, from a signal-free control outside the fitted distribution or, for
  `gauss_late_tail_const`, a measured random-hit rate);
  `insufficient_entries` (fewer effective entries than `min_entries` in the fit range or for a quantile width, or
  than `min_tail_entries` beyond a join);
  `fit_failed` (minimizer not converged or covariance not positive definite; no parameter reported as measured).

## Environment coverage

Cells: a source ID, `n/a` with a reason, `gap`, or a link to an environment-specific reference; a related use or a
link alone is a `gap` here.

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Single-sided CB | inspire_183554, arxiv_1603.08591 | arxiv_2311.07413 | gap | arxiv_2604.25748 | gap | gap |
| DSCB | arxiv_2012.06888 | arxiv_2607.28477 | gap | gap | gap | gap |
| Fixed `n`, GaussExp (`alpha`-`n` correlation) | inspire_183554 (`n` fixed); arxiv_1603.08591 (synthetic); correlation derived in Relations | gap (not discussed) | gap | gap (not discussed) | gap | gap |
| Gaussian plus pedestal | gap | arxiv_2001.01540 (control for comparison; floor fitted) | gap | gap (related: arxiv_1912.08739, location fit; floor flat by construction, fitted) | gap | gap |
| Core-plus-tail time PDF | gap (related: arxiv_1806.02129, shape observed; not used as a likelihood PDF) | gap | gap | arxiv_astro-ph_0407044; [photon likelihood reconstruction](photon-likelihood-reconstruction.md) (time term) | gap | gap |
| Hadronic or partially contained response | arxiv_1203.1302 (high-side tail); low-side: gap (pdg_2025_particle-detectors-at-accelerators, sec. 35.10.1.1: non-Gaussian only) | arxiv_1712.05494 (low-side tail) | arxiv_1909.12860 (response-matrix branch); [space based direct detection](space-based-direct-detection.md) | gap | gap | gap |
| Effective sigma | arxiv_1306.2016 | arxiv_1703.02821 (beam test of the same instrument, sec. IV) | arxiv_1703.02821 | gap (related: R68, [neutrino astronomy](neutrino-astronomy.md)) | gap (related: R68, [imaging atmospheric cherenkov](imaging-atmospheric-cherenkov.md), [ground based detection arrays](ground-based-detection-arrays.md)) | gap |
| Model choice as a systematic | gap (related: arxiv_1206.4071, signal model of an efficiency fit) | arxiv_2311.07413 | gap | gap | gap | gap |

R68, the 68% containment radius of a point-spread function, is a related 2D measure, not an
effective sigma: for a circular Gaussian `1 - exp(-R68^2 / (2 sigma^2)) = 0.6827` gives `R68 = 1.515 sigma`;
those references own it. The UGD single-sided CB is a germanium line with incomplete charge collection, a use
NUC spectroscopy shares, not sourced here (a gap). Four uses were sourced in one environment
only: `n` unconstrained in CB fits (COL), the pedestal under a resolution (FXT), the time PDF in a likelihood
(UGD) and the line-shape systematic of a resolution (FXT); their other cells naming a source are related uses.

## Citations

Read 2026-11-19; format of the [detector principles bibliography](detector-principles-bibliography.md),
apparatus papers abbreviated:

- J. E. Gaiser, "Charmonium spectroscopy from radiative decays of the J/psi and psi-prime", PhD thesis, Stanford
  University (1982), report SLAC-R-255, https://www.slac.stanford.edu/pubs/slacreports/reports02/slac-r-255.pdf
  (INSPIRE 183554), Appendix F.1 (eq. F-1, printed pp. 178-179) and Table 20. Early CB line shape.
- S. Das, "A simple alternative to the Crystal Ball function", arXiv:1603.08591 (2016),
  https://arxiv.org/abs/1603.08591, eqs. 1-3 and Fig. 1.
  CB closed form, GaussExp and ExpGaussExp, instability from `n`.
- Particle Data Group, S. Navas et al., Phys. Rev. D 110 (2024) 030001, DOI 10.1103/PhysRevD.110.030001, and
  2025 update, *Particle detectors at accelerators*,
  https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-accel.pdf, sec. 35.10.1.1 (p. 92).
  Non-Gaussian hadronic response.

<!-- example: apparatus papers read for this page (2026-11-19) -->
- CMS, JINST 16 (2021) P05014, arXiv:2012.06888, sec. 6.1 (DSCB regression).
- CMS, JINST 8 (2013) P09009, arXiv:1306.2016, sec. 4.5 (effective sigma).
- CMS, JINST 7 (2012) P10002, arXiv:1206.4071, sec. 5.1.3 (shape systematic).
- ATLAS, Eur. Phys. J. C 78 (2018) 987, arXiv:1806.02129, sec. 3.1 (cell times).
- ATLAS, Eur. Phys. J. C 73 (2013) 2305, arXiv:1203.1302, sec. 4.4 (E/p tails).
- ALICE FoCal, M. Aehle et al., JINST 19 (2024) P07006, arXiv:2311.07413, secs. 6.3 and 7.
- S. Ceravolo et al. (CRILIN), JINST 21 (2026) P09015, arXiv:2607.28477, sec. 7.5.3.
- E. Sánchez García et al. (CONUS+), arXiv:2604.25748 (2026), sec. 4, Fig. 7.
- C. Ligtenberg et al. (GridPix quad), Nucl. Instrum. Meth. A 956 (2020) 163331, arXiv:2001.01540, sec. 5.8.
- D. L. Adams et al. (35-ton LArTPC), JINST 15 (2020) P03035, arXiv:1912.08739, sec. 9.2.
- J. Ahrens et al. (AMANDA), Nucl. Instrum. Meth. A 524 (2004) 169-194, arXiv:astro-ph/0407044,
  secs. 3.1.1-3.2.2.
- S. Lee, M. Livan and R. Wigmans, Rev. Mod. Phys. 90 (2018) 025002, arXiv:1712.05494, sec. IV (ACCESS prototype).
- DAMPE, Q. An et al., Sci. Adv. 5 (2019) eaax3793, arXiv:1909.12860, Materials and Methods.
- C. Yue et al. (DAMPE), Nucl. Instrum. Meth. A 856 (2017) 11-16, arXiv:1703.02821 (arXiv version read), sec. IV.
<!-- /example -->
