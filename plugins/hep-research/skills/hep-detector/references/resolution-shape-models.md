# Resolution Shape Models

Parametric line shapes for a response or residual, and when to use each. Width estimators (RMS, `sigma_68`, MAD, RMS90,
double Gaussian), residuals and pulls are in [performance metrics and residual
diagnostics](performance-metrics-and-residual-diagnostics.md), whose `sigma_68` forms (central, smallest) are two of the
three `sigma_eff` conventions here (Relations), each value naming its own (that page's former `sigma_eff`, the smallest
interval only, now points here). Fitting and goodness of fit: [likelihood
fitting](../../hep-statistics/references/likelihood-fitting.md); response matrices: [response and forward
folding](response-and-forward-folding.md).

Environment codes: COL collider; FXT fixed target and test beam; SPC space and balloon; UGD underground,
neutrino, rare event; GND ground-based arrays; NUC nuclear and low energy.

## Relations

`t = (x - xbar) / sigma`, with `xbar` (`mu` elsewhere) and `sigma` the Gaussian core's
mean and width.

- **Crystal Ball (CB), low-side tail** (exact, a definition; Das, arXiv:1603.08591, eq. 1; an early form is
  Gaiser, App. F.1, eq. F-1; Das p. 1 credits its development to refs.
  6 and 8 there): `f = exp(-t^2/2)` for `t > -alpha`;
  `f = A (B - t)^(-n)` for `t <= -alpha`, with `A = (n/|alpha|)^n exp(-|alpha|^2/2)` and
  `B = n/|alpha| - |alpha|`, for `alpha > 0` and `n > 1`. `A` and `B` make the function
  and its first derivative continuous at the join (Gaiser, printed p. 179). A high-side tail is the mirror image
  `t -> -t`, not a negative `alpha` (discontinuous at the join); state how the side is encoded.
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
  arXiv:2001.01540, sec. 5.8, Fig. 12):
  `f(x) = N_s G(x; mu, sigma) + c`, with `c` the density of entries unrelated to the signal.
- **Core-plus-tail time PDF** (a model, approximate; arXiv:astro-ph/0407044, secs. 3.1.1 and 3.2.2): a half Gaussian of
  width `sigma_g` for negative residuals, joined smoothly (a cubic spline up to `r_1`) to a one-sided late tail, plus a
  flat term for random noise hits. `sigma_g` is free and includes all timing uncertainties, not only photodetector
  jitter (sec. 3.2.2). As a tool model (`gauss_late_tail_const`) of the time residual `r`: a Gaussian core of width
  `sigma_g` for `r < 0`, a cubic join over `0 <= r < r_1`, smooth and leaving the tail's normalization unchanged, with
  `r_1 = sqrt(2 pi) sigma_g` or a fixed input (never free), a late-tail density `g_late(r; theta)` from the caller for
  `r >= r_1`, and a flat random-hit density `c_r`.
- **Effective sigma** (exact, a definition with three conventions): the half-width of an interval holding 68.27% of
  the entries (68% in the sources): the smallest such interval (arXiv:1703.02821, sec. IV), the interval symmetric
  about the most probable value (mode estimator stated; arXiv:1306.2016, sec. 4.5, says "the interval"; placement and
  half-width are this page's reading), or the central interval, `(q84 - q16)/2` (the central `sigma_68`, as in
  `build_response.py`). All three equal `sigma` for a Gaussian; they differ for an asymmetric shape.

## Methods

| Situation | Method | Preconditions | Failure modes | Environments |
|---|---|---|---|---|
| One-sided losses: shower leakage or radiation, incomplete charge collection | Single-sided CB on the loss side | Loss on one side only; enough entries in the tail to see the join | `n` unconstrained (row 3); a tail on the other side ignored; the RMS quoted as the resolution | COL, FXT, UGD |
| Losses on both sides, or a regression of the per-object resolution | DSCB; quote the core `sigma` as the resolution and the four tail parameters | Both tails populated | Six correlated parameters; the core `sigma` read as the full width | COL, FXT |
| Tail looks exponential, or `n` runs to its bound | Fix `n` (state the value) and fit `alpha`, or use GaussExp / ExpGaussExp (large-`n` limit, same scan as systematic) | The fit passes (Statuses; `shape_mismatch` includes the bins beyond each join); `alpha` and `sigma` varied as a systematic over fixed `n` on a grid stated before the fit (at least 2, 3, 5, 10, 20, 50 and the nominal), from the smallest grid value passing with that `n` fixed to 50, range stated (zero span only if 50 alone passes: not evaluated; no grid value passes: row 7) | `alpha` quoted without the fixed `n`; results compared across different fixed `n` | COL only |
| Entries unrelated to the signal (wrong matches, noise maxima, accidentals) | Gaussian plus pedestal; floor fixed, or constrained no more loosely than the scaled control's uncertainty, from a signal-free control outside the fitted distribution (shifted timing, other channels, an off-time window), scaled to the fit sample by a recorded factor | Control: at least `min_entries` effective entries, slope passing the slope test, other channels only at an equal noise rate; or a sideband meeting `floor_from_sideband` (Statuses); else `floor_from_tails` (and `insufficient_entries` below `min_entries`) | Floor floated with the core, or constrained more loosely, so it trades against the core width (`floor_from_tails`); a non-flat floor | FXT (source fitted the floor; fixing it is guidance here) |
| Times entering a likelihood (time residuals) | Core-plus-tail time PDF: Gaussian core, one-sided late tail, flat part | Tail mechanism known (slow shower components, scattering, late light); random hits rate | Tail cut instead of modelled, biasing the likelihood; `sigma_g` read as the photodetector jitter | UGD only |
| Hadronic or partially contained shower response | Row 1 on the observed tail side (mirrored for a high side), or row 2 if both sides have tails, while each energy bin's own fit passes (Statuses); otherwise a simulated response matrix, validated in data, smearing variations as systematics (Transfers), before deconvolution or folding | Tail side checked for the observable | Assuming a low-side tail where the mechanism gives a high-side one (E/p with neutral overlap); one shape across energies | SPC (COL, FXT: tail side observed only) |
| Shape unknown or not described by any of the above | Effective sigma or FWHM with a tail fraction, stated with its convention | Enough entries for the quantile; bootstrap uncertainty | Conventions mixed in a comparison; a Gaussian formula used for its uncertainty | COL, FXT |
| Any quoted resolution | Name the line shape; vary it (Gaussian versus CB, fit range) and take the change as a systematic | Fewer than `min_entries` in the fit range: no resolution for that bin (merge bins); nominal with `tail_unconstrained` from a fitted power: row 3 first; with `floor_from_tails` or a floor's `insufficient_entries`: row 4 first; nominal still not passing (any status that stops it passing, Statuses, or row 3 with no passing grid value): quote row 7 instead; nominal passes: try at least Gaussian, CB, DSCB, take the systematic from those that pass (Statuses), if none passes from the difference to the central effective sigma (said so), keep the fit-range variation and add an effective sigma | A single Gaussian fitted over the full range; the fit range not stated | FXT only |

<!-- example: the Crystal Ball NaI(Tl) detector at SPEAR (Gaiser, SLAC-R-255, App. F) -->
Bhabha electrons (App. F.1, printed pp. 178-179):
`sigma_E/E = 2.2%` at 1.547 GeV with `alpha = 1.5`, `n = 5.0` (printed p. 179). For inclusive photon spectra the
fits were "very insensitive" to the power term over 15.0-27.0, so it was "fixed at 15.0" (Table 20, printed p. 181).
<!-- /example -->

<!-- example: GridPix quad in a test-beam telescope (arXiv:2001.01540, sec. 5.8, Fig. 12) -->
Tails partly from wrongly matched background tracks, estimated by shifting the telescope timing by 1000
frames, for comparison; fit: a Gaussian with a free constant offset.
<!-- /example -->

<!-- example: AMANDA photon arrival times -->
AMANDA (arXiv:astro-ph/0407044, secs. 3.1.1-3.2.2): Pandel gamma distribution (eq. 17) for scattering in ice from
`r_1 = sqrt(2 pi) sigma_g` on (`t_1` there), joined to the half Gaussian as above plus noise hits (Fig. 4).
<!-- /example -->

<!-- example: hadronic and partially contained response (ACCESS prototype, DAMPE, ATLAS E/p) -->
Dual-readout prototype, 375 GeV pions: skewed low by leakage (arXiv:1712.05494, sec. IV, Fig. 6). DAMPE BGO:
simulated response, deconvolution (arXiv:1909.12860, Materials and Methods). ATLAS E/p: high-side tail from neutral
background (arXiv:1203.1302, sec. 4.4).
<!-- /example -->

<!-- example: line-shape systematics (ALICE FoCal-H prototype) -->
FoCal-H quoted FWHM/2.355 of a Gaussian or CB fit (Fig. 36) and took on it the line-shape (Gaussian versus CB,
`Delta sigma_stoch = 0.10`) and fit-range (CB right-tail limit 1 to 2.5 sigma, 0.02) systematics (arXiv:2311.07413,
sec. 6.3, PDF pp. 48-49).
<!-- /example -->

## Distinctive but generalizable features (resolution shapes)

- **Topology**: a 1D response (`x_reco / x_true`, `x_reco - x_true`) or residual per conditioning bin, or a line
  about a known value, its natural width negligible or folded in (stated).
- **Inverse problem**: core and tail parameters; degeneracies `alpha`-`n`, floor-core width, width-fit range.
- **Natural objects**: a monoenergetic line (beam, source, resonance), a matched track residual, a hit time.
- **Informative residual**: data minus the fitted shape at the joins and in the tails.
- **Scaling**: the core width follows the resolution terms; tails change with energy (fit per bin).
- **Conventions**: model, tail sides and `alpha` sign, fit range, fixed parameters, goodness-of-fit statistic and
  binning, thresholds, effective-sigma and tail-fraction conventions.
- **Tails**: leakage, radiation, charge loss, slow components, scattering, wrong matches, noise, (COL) pileup.
- **Dependence**: energy, angle, position, rate, selection.
- **Data sample**: test beams, calibration lines, resonances, matched tracks, floor controls.
-  **Transfers** (guidance of this page): a shape fitted in simulation transfers to data only re-fitted in data so that
  it passes (Statuses, beyond each join too), core and tail parameters free except at most one kept from simulation
  (listed), which moves, freed, by less than its data-fit uncertainty, itself below `tail_rel_unc_max` of the value; or
  scaled (only a width scale on `sigma`, the position and the normalization fitted in data, factor reported), if in data
  in the same bin it passes (Statuses), its tail values fixed from simulation and at most one of them sourced, after the
  test above. Only a value kept by either test counts as sourced. Otherwise it does not transfer: the data shape is
  fitted under Methods (row 3 for a fixed `n`) or replaced by a response matrix validated in data, smearing variations
  as systematics ([data/MC validation](data-mc-validation-and-detector-systematics.md)).

## Common misconceptions and failure modes

- **The RMS of a CB is the resolution.** It is not: it mixes core and tail, has no finite RMS for `n <= 3`
  (Relations); for larger `n` it depends
  on `alpha`, `n` and the fit range.
- **Tails are always on the low side.** The side follows the mechanism (E/p with neutral overlap or
  annihilation gives a high-side tail).

## Deliverables

- The named line shape with its formula, all fitted and fixed parameters (fixed ones marked), the fit
  range, and the fit quality.
- A width and a tail measure, never one number for both: the core width with its tail parameters (and a tail
  fraction if `tail_unconstrained` is set or all tail parameters are fixed), or, for a model without them (`gauss`,
  `gauss_plus_const`) or an effective sigma or FWHM, a tail fraction with its `k_tail` (central `sigma_68`).
- For a pedestal: the floor items of the Outputs (Tool hooks).
- For quantile widths: the convention and a bootstrap uncertainty.
- The line-shape and fit-range systematics, and the shape used for each energy or angle bin.

## Tool hooks

A shape-fit tool (none yet; `build_response.py` fits no parametric shape) would take:

-  **Inputs**: a weighted sample or histogram of the residual or response, its unit, the model (`gauss`, `cb_low`,
  `cb_high`, `dscb`, `gaussexp`, `expgaussexp`, `gauss_plus_const`, and `gauss_late_tail_const` with its `g_late`),
  fixed parameters, parameter bounds, the fit range, the alternative models and fit ranges for the systematic, the
  goodness-of-fit statistic (default the saturated-model likelihood ratio on bins fixed before the fit, at most half the
  sample's central `sigma_68` wide, merged to at least 5 entries keeping a bin beyond each join of the nominal model's
  pre-fit estimate, stated with the binning (none beyond a fitted join: `insufficient_entries`), or one at least as
  powerful at equal size against a subtle tail: CB fits to DSCB toys of the same entries with `alpha_R = 2`, `n_R = 5`),
  the minimizer settings (strategy, edm tolerance, call limit; defaults or tighter), row 3's `n` grid, the slope test
  (default: a linear fit's slope against zero, two-sided p-value at least `gof_p_min`, not the line's goodness of fit,
  another only if at least as powerful at equal size), and the thresholds, all fixed before the fit: `gof_p_min`
  (default 0.05, from 0.05 to below 1), `tail_rel_unc_max` (default 0.5, at most 0.5), `n_max` (default 50, at most 50,
  tightening `tail_unconstrained` only, as row 3's scan runs to 50; Das, p. 4, rejects an `n` of 113 or 127),
  `min_entries` (default 100, at least 100) and `min_tail_entries` (default 10, at least 10), counted as effective
  entries `(sum w)^2 / sum w^2`, and the tail-fraction threshold `k_tail` in units of the central `sigma_68` (default 3,
  at most 3, as in `build_response.py`). Defaults and limits are this page's unsourced convention; a non-default value
  is reported. For a flat term: a signal-free control with its scale factor, its uncertainty and, for other channels,
  the noise rates of control and fit channels, a sideband (range, flatness argument, signal-tail estimate and its
  source), or a random-hit rate (uncertainty, entries, sample, factor to `c_r`).
-  **Outputs**: parameters with uncertainties, correlation matrix and bounds, tail sides, core `sigma`, the three
  effective-sigma conventions (mode estimator named) and the FWHM with bootstrap uncertainties, the tail fraction
  `|x - median| > k_tail sigma_68` (central `sigma_68`), p-values over the fit range and beyond each join, edm and
  covariance status, the status set, statistic and binning, the model standard deviation if finite
  (`moments_undefined` not set, never with a flat term: it depends on the fit range), all thresholds and settings,
  the floor's source, control or sideband with scale factor (or flatness argument and signal-tail contribution) and
  fitted slope, the floor it gave, the fitted floor, the change in core `sigma` from the floor's uncertainty and per
  alternative model and fit range.
-  **Units and conventions**: `x` (the input value), `mu`, `sigma`, `sigma_g`, `r`, `r_1` and every reported width in
  the input's unit, the tail fraction dimensionless; `c`, `c_r` in sum of weights per input unit, `N_s` in sum of
  weights; `theta` as `g_late` defines; `alpha`, `alpha_L`, `alpha_R`, `k`, `k_L`, `k_H` in units of `sigma`; powers
  dimensionless.
-  **Negative control** (fixed seeds stated with the test; a value matches when its pull is below 3, or over toys the
  pulls have mean 0 and width 1): a pure Gaussian sample fitted with `cb_low` and with `dscb` must return the generated
  width as core `sigma` and a status set containing `tail_unconstrained` (`moments_undefined` also allowed);
  `gauss_plus_const` without a control, or constrained more loosely than the control's uncertainty, and
  `gauss_late_tail_const` with a free flat term must return `floor_from_tails`, a floor fixed from a sideband meeting
  row 4 `floor_from_sideband` without `floor_from_tails` (range changed after the fit, sloped, or a signal tail above
  the floor's statistical uncertainty: `floor_from_tails`), a sloped control, other channels at an unequal noise rate, a
  signal-tail estimate fitted to the same sample, or a rate from the fitted sample or used more loosely than its
  uncertainty, `floor_from_tails`, a 10-entry control, sideband or rate `insufficient_entries` and `floor_from_tails`,
  and a floor fixed from a signal-free control meeting row 4 none of `floor_from_tails`, `floor_from_sideband`,
  `insufficient_entries`; an unconverged fit (made with a one-call limit) and a converged fit with a covariance not
  positive definite (two fully correlated free parameters) must each return `fit_failed`, not `ok`, at any allowed
  threshold and minimizer setting (defaults or tighter). Positive control: a CB sample of 10,000 entries generated with
  `alpha = 1.5`, `n = 5` and fitted with `n` fixed at 5, at default thresholds, must return `alpha` with status `ok` for
  a seed fixed and recorded before the first run (over 1000 toys, `shape_mismatch` (the combined test of Statuses) in a
  fraction at most `gof_p_min` plus binomial 3 sigma (0.071 at 0.05), `tail_unconstrained` and `fit_failed` each below
  1%, and a DSCB sample of that size with `alpha_L = alpha_R = 1`, `n_L = n_R = 5` fitted with `gauss` sets
  `shape_mismatch` in at least 99% of toys; with a fixed `n <= 3` the set contains `moments_undefined`).
-  **Statuses** (a set, all that apply are reported; `ok` only when no other is set, `floor_from_sideband` aside): `ok`;
  `tail_unconstrained` (a fitted tail parameter at its input bound, or with relative uncertainty above
  `tail_rel_unc_max` or undefined, or a fitted power above `n_max`, or a tail parameter fixed neither at a stated,
  sourced value (a control's generated value, the one kept under Transfers) with its variation over the source's stated
  uncertainty reported as a systematic, nor, for a power, at a point of row 3's grid whose fit sets none of
  `shape_mismatch`, `insufficient_entries`, `fit_failed` nor the fitted-parameter tests above); `moments_undefined` (any
  power `p` of `n`, `n_L`, `n_R` with `p <= 3` when fixed, or `p - sigma_p <= 3` or `sigma_p` undefined when fitted, or
  a `g_late` without finite variance; no standard deviation reported); `shape_mismatch` (a p-value of the named
  statistic undefined (degrees of freedom not positive) or below its level, over the fit range (degrees of freedom: bins
  less free parameters) or over the bins wholly beyond a fitted join (their number), each test at `gof_p_min` over the
  number of tests, or one combined statistic calibrated by toys at size `gof_p_min`); `floor_from_tails` (a flat term,
  in `gauss_plus_const` or `gauss_late_tail_const`, neither fixed from, nor constrained no more loosely than the scaled
  control's uncertainty by, a scaled signal-free control outside the fitted distribution meeting row 4 (at least
  `min_entries`, slope passing the slope test, other channels only at an equal noise rate), nor by a random-hit rate
  from a signal-free sample outside the fitted distribution with at least `min_entries` effective entries
  (`gauss_late_tail_const`, no more loosely than its uncertainty), nor fixed from a sideband meeting
  `floor_from_sideband`); `floor_from_sideband` (a floor flat by construction, argument recorded, its fitted slope
  passing the slope test, from a sideband with an input range fixed before the fit, outside the core fit, with at least
  `min_entries` effective entries and a signal-tail contribution (from simulation, or from a fit to an independent
  sample, recorded) below the floor's statistical uncertainty, `ok` still allowed); `insufficient_entries` (fewer
  effective entries than `min_entries` in the fit range, for a quantile width, or in a floor control, sideband or
  random-hit-rate measurement, or than `min_tail_entries` beyond a join); `fit_failed` (minimizer not converged or
  covariance not positive definite; no parameter reported as measured). A fit *passes* when none of `shape_mismatch`,
  `insufficient_entries`, `fit_failed`, `tail_unconstrained` and, with a flat term, `floor_from_tails` is set.

## Environment coverage

Cells: a source ID, `n/a` with a reason, `gap`, or a link to an environment-specific reference; a related use or a
link alone is a `gap` here, and a cell follows the measurement's environment (a beam test is FXT).

| Technique | COL | FXT | SPC | UGD | GND | NUC |
|---|---|---|---|---|---|---|
| Single-sided CB | inspire_183554 | arxiv_2311.07413 | gap | arxiv_2604.25748 | gap | gap |
| DSCB | arxiv_2012.06888 | arxiv_2607.28477 | gap | gap | gap | gap |
| Fixed `n`, GaussExp (`alpha`-`n` correlation) | Fixed `n`: inspire_183554 (fixed at 15.0, no scan); GaussExp: gap (related: arxiv_1603.08591, synthetic) | gap | gap | gap | gap | gap |
| Gaussian plus pedestal | gap | arxiv_2001.01540 (control for comparison; floor fitted) | gap | gap | gap | gap |
| Core-plus-tail time PDF | gap | gap | gap | arxiv_astro-ph_0407044; [photon likelihood reconstruction](photon-likelihood-reconstruction.md) (time term) | gap | gap |
| Hadronic or partially contained response | gap (related, no shape fitted: arxiv_1203.1302, high-side tail; pdg_2025_particle-detectors-at-accelerators, sec. 35.10.1.1, non-Gaussian) | gap (related: arxiv_1712.05494, low-side skew, no fit) | arxiv_1909.12860 (response-matrix branch); [space based direct detection](space-based-direct-detection.md) | gap | gap | gap |
| Effective sigma | arxiv_1306.2016 | arxiv_1703.02821 (beam test, sec. IV) | gap | gap (related: R68, [neutrino astronomy](neutrino-astronomy.md)) | gap (related: R68, [imaging atmospheric cherenkov](imaging-atmospheric-cherenkov.md), [ground based detection arrays](ground-based-detection-arrays.md)) | gap |
| Model choice as a systematic | gap | arxiv_2311.07413 | gap | gap | gap | gap |

R68 (68% containment radius of a point-spread function) is a related 2D measure those references own. Five uses were
sourced in one environment only: `n` unconstrained in CB fits (COL), the pedestal under a resolution (FXT), the time
PDF in a likelihood (UGD), the hadronic response matrix (SPC) and the line-shape systematic (FXT);
their other cells naming a source are related uses.

## Citations

Read 2026-11-19, in the format of the [detector principles bibliography](detector-principles-bibliography.md):

- J. E. Gaiser, "Charmonium spectroscopy from radiative decays of the J/psi and psi-prime", PhD thesis, Stanford
  University (1982), SLAC-R-255, https://www.slac.stanford.edu/pubs/slacreports/reports02/slac-r-255.pdf
  (INSPIRE 183554), Appendix F.1 (eq. F-1, printed pp. 178-179) and Table 20.
- S. Das, "A simple alternative to the Crystal Ball function", arXiv:1603.08591 (2016),
  https://arxiv.org/abs/1603.08591, eqs. 1-3, Fig. 1, abstract and pages 1 and 4.
- Particle Data Group, S. Navas et al., Phys. Rev. D 110 (2024) 030001, and 2025 update, *Particle detectors at
  accelerators*, https://pdg.lbl.gov/2025/reviews/rpp2025-rev-particle-detectors-accel.pdf, sec. 35.10.1.1 (p. 92).
  Non-Gaussian hadronic response.

<!-- example: apparatus papers cited by ID outside example blocks, with no full entry or example block of their own -->
- Read 2026-11-19: CRILIN arXiv:2607.28477v1, sec. 7.5.3; CONUS+ 2604.25748v1, sec. 4, Fig. 7; DAMPE beam test
  1703.02821v2, sec. IV; CMS 1306.2016v2, sec. 4.5.
<!-- /example -->
