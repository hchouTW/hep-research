# Time-Series Inference for Binned Series

Inference on a **binned** time series: a flux, rate or ratio estimated in consecutive time bins (and often in several
energy or rigidity bins at once), each with its own uncertainty. It covers the covariance between time bins, tests for
periodicity against a red-noise null, the trials of a search over periods and energy bins, and joint fits of several
periods. Event-level methods (arrival-time phases, the Rayleigh, `Z_m^2` and H tests, Bayesian blocks on event times)
are in [astroparticle statistics](astroparticle-statistics.md#point-sources-test-statistics-periodicity-and-variability)
and are not repeated here. General fitting, covariance and combination rules are in
[likelihood fitting](likelihood-fitting.md), [nuisance modeling](nuisance-modeling.md) and
[combinations](combinations.md).

Status: **documented** (guidance; `periodicity_scan.py` runs a periodogram search against simpler nulls, see
[Test](#periodicity-in-a-binned-series), and `time_structure.py` finds change points and lags; no shipped tool fits
the red-noise null with `C` below). The time-bin covariance
construction below is **demonstrated-on-synthetic-data** by `tests/skills/hep_statistics/test_time_series_covariance.py`
(synthetic series only; it shows the recipe is internally consistent, not that any experiment's systematics are
modeled correctly). Which systematic sources are time-independent, and their correlation times, are physics inputs
from hep-measurement and hep-detector; this file never supplies them.

## Contents

1. [Time-bin covariance](#time-bin-covariance)
2. [Periodicity in a binned series](#periodicity-in-a-binned-series)
3. [Trials across periods and energy bins](#trials-across-periods-and-energy-bins)
4. [Joint fits of several periods](#joint-fits-of-several-periods)
5. [Multi-era joint fits](#multi-era-joint-fits)
6. [Deliverables](#deliverables)
7. [Sources](#sources)

## Time-bin covariance

For one series `F_t` in `T` time bins, write the covariance as a sum of blocks, each built from its own evidence:

    C = C_stat + C_tind + C_tdep

- **`C_stat`**: statistical, diagonal when the time bins hold disjoint events (`diag(sigma_stat,t^2)`). Overlapping or
  sliding windows are not disjoint: their statistical covariance has off-diagonal terms from the shared events.
- **`C_tind`**: time-independent systematics (an acceptance or normalization factor, a cross section used in a
  correction, any source that is the same for every time bin). A source with relative size `delta_k` is fully
  correlated in time: `C_tind = sum_k a_k a_k^T`, `a_k = delta_k F` (elementwise; `delta_k` may vary with `t` when the
  same source enters with a time-varying weight). Each source is rank one; sources that are constant fractions of the
  same `F` add in quadrature into a single rank-one term.
- **`C_tdep`**: time-dependent systematics (detector conditions, calibration drifts, an environment correction). For
  each source, `C_tdep = D R D` with `D = diag(eps_j F)` and a valid time correlation `R`. Two common, valid choices:
  `R[t, t'] = exp(-|t - t'| / tau)` (an exponential correlation with correlation time `tau`; on equally spaced bins it
  is the correlation of an AR(1) process with `phi = exp(-Delta t / tau)`, whose inverse is tridiagonal), or a block
  structure (fully correlated within one calibration epoch, independent between epochs). `tau` or the epoch boundaries
  are a stated assumption with evidence; vary them and report the effect.

Checks before the matrix is used:

- **Positive definiteness.** Each block must be positive semi-definite, and the total positive definite for a `chi2`
  (`C_stat` usually provides that). An ad hoc correlation is the usual failure: correlating only neighbouring bins with
  `rho` gives a tridiagonal matrix with eigenvalues `1 + 2 rho cos(k pi / (T + 1))`, negative once
  `rho > 1 / (2 cos(pi / (T + 1)))` (just above 0.5 for many bins). Build `R` from a valid correlation function
  instead; never clip eigenvalues to repair a construction error.
- **Limits.** `tau -> 0` must give a diagonal `C_tdep`; `tau -> infinity` must make it rank one (it then belongs in
  `C_tind`). The variance of the time average, `w^T C w` with `w = 1/T`, keeps the full time-independent part
  (`(sum_k delta_k^2) mean(F)^2` for constant fractions) while the statistical part falls as `1/T`: compare it with the
  uncertainty quoted for the time-integrated measurement, when one exists. In a ratio `F_t / F_t'` a constant-fraction
  time-independent part cancels to first order; a ratio uncertainty that still contains it is a construction error.
- **Validate.** Run `<plugin root>/core/stats/validate_covariance.py` with the blocks given (`"blocks": {...}`) so
  their sum, symmetry and positive semi-definiteness are checked. A fully correlated block is rank deficient on its
  own, and the validator warns about it (`block.<name>.rank_deficient`); that warning is expected for `C_tind`, an
  error on the total is not.
- **Energy and time together.** For a series in several rigidity bins the covariance is over (rigidity, time) pairs.
  A source whose rigidity correlation `R_E` and time correlation `R_T` factorize contributes `D (R_E kron R_T) D`, which
  is positive semi-definite when both factors are (the Kronecker product of two positive semi-definite matrices is).
  Whether a source factorizes is an assumption to state.
- **Normalization in a fit.** A time-independent fraction built from the measured values biases a fit low (Peelle's
  pertinent puzzle, [combinations](combinations.md#multiplicative-uncertainties-peelles-pertinent-puzzle)); in a fit,
  carry it as a nuisance parameter (a covariance built from the model is not equivalent; see
  [joint fits](#joint-fits-of-several-periods)).

A missing time correlation stays missing: when only per-bin totals are published, the time correlation is unknown, not
zero, and a result that depends on it says so.

## Periodicity in a binned series

**Why the event-level tests do not apply.** The Rayleigh and `Z_m^2` tests use the phases of individual events and
assume, under the null, independent events with uniformly distributed phases (a constant rate after exposure
correction), so the statistic follows `chi2` with `2m` degrees of freedom. A binned series has no event phases, its
bins are correlated through `C_tind` and `C_tdep`, and the physical series itself varies stochastically with more power
at low frequencies. Under such a red-noise null a white-noise test (or a `chi2` with independent bins) finds spurious
"periods" at long time scales, especially when the series spans only a few cycles (Vaughan et al. 2016).

**Red-noise null.** Model the series under the null as a smooth trend plus a stationary red-noise process plus the
measurement error:

    y_t = mu_t + x_t + e_t,   x_t = phi x_{t-1} + eta_t (AR(1)),   e ~ N(0, C)

The AR(1) process has variance `sigma_eta^2 / (1 - phi^2)`, autocorrelation `phi^k` at lag `k`, and spectral density
`S(f) = sigma_eta^2 / (1 + phi^2 - 2 phi cos(2 pi f Delta t))` (Gilman, Fuglister and Mitchell 1963; Torrence and Compo
1998). For uneven spacing (gaps, bins of different length) use `phi_i = exp(-(t_i - t_{i-1}) / tau)` and estimate `tau`
from the data (Mudelsee 2002, TAUEST; Schulz and Mudelsee 2002, REDFIT, with the Lomb-Scargle periodogram of
Lomb 1976 and Scargle 1982). A power-law spectrum is the other common red-noise model (Vaughan 2005, 2010); the choice
is part of the null hypothesis and is stated.

**Known or unknown period.** A period with a physical reason to test (the ~27-day solar rotation and its harmonics, an
orbital or attitude period of the instrument) is tested alone, for example by folding the series at that period
(epoch folding) against the same red-noise null: one trial, no search penalty, provided the period is fixed before the
series is examined (a period read off the same series is a search and pays the trials). A periodogram search
(Lomb-Scargle for uneven sampling and gaps) is for a genuinely unknown or approximate period and pays the trials
below. Comparing the amplitude and phase of the same candidate period between species of opposite charge sign (a
particle and its antiparticle, protons and electrons) separates a drift-related heliospheric effect from an
instrumental or environmental artefact, which affects both signs alike; the comparison is a joint fit with the shared
normalization and its covariance, not two separate significances.

**Test.** At the Fourier frequencies `f_j` of a Gaussian stationary series, the periodogram ordinates are approximately
independent and distributed as `S(f_j) chi2_2 / 2` (Brockwell and Davis 1991, Ch. 10). The local test compares each
ordinate with the fitted red-noise spectrum: `2 I(f_j) / S_hat(f_j)` against `chi2_2`. Then:

- Fit the null (trend, `phi` or `tau`, `sigma_eta`) with the measurement covariance `C` included (total covariance
  `Sigma_AR + C`), not with `C` ignored: a measurement error with its own time correlation is otherwise mistaken for
  physical red noise, or the reverse.
- The fitted null parameters are uncertain, and fitting them on data that may contain the signal biases the test;
  Vaughan (2005) includes the uncertainty of the fitted power-law parameters in the test, Vaughan (2010) uses
  posterior predictive p-values; in general, simulate from the fitted null and refit the null in every simulation.
- Report the significance only after the trials (next section). A peak that is significant against white noise and not
  against the fitted red noise is not a detection.
- A common time-independent normalization (constant fraction) scales the whole series: it changes an absolute
  modulation amplitude but, to first order, not the relative amplitude or its significance.
- Fewer than a few cycles in the span cannot establish a period against red noise; say so instead of quoting a
  significance (Vaughan et al. 2016). The longest period searched and the minimum number of cycles are fixed in
  advance.
- **Shipped tool.** `<plugin root>/skills/hep-statistics/scripts/periodicity_scan.py` runs a weighted generalized
  Lomb-Scargle periodogram of one series with a band-maximum global p from surrogates under a declared white, AR(1)
  or OU null. Its red-noise surrogates are a constant mean plus a red process with `phi` (or `tau`) from the lag-1
  autocorrelation (for AR(1), with the first-order small-sample correction) and the series' total variance. By
  default (`--null-fit refit`, since the fix PERIODICITY-REFIT) the null is refitted on every surrogate and the p is
  a double parametric bootstrap; on no-signal toys (400 per configuration, AR(1) and OU, n = 50 and 100) every
  rejection fraction at alpha = 0.01, 0.05 and 0.1 lies within two binomial sigma of alpha or below it. With
  `--null-fit once` (the only method of releases 0.14.0 to 0.23.0) the null is estimated once: on short red series
  that p is anti-conservative (AR(1), n = 50, phi = 0.9: 0.147 rejected at alpha = 0.05, 0.253 at 0.1). The
  surrogates have no trend, no measurement term `e ~ N(0, C)` (only the white null adds `N(0, sigma_i^2)`) and no
  cross-rigidity correlation, so the p-value is not the one against the full null above; report it as such, or run
  the full toys yourself.

## Trials across periods and energy bins

The global p-value of a search over trial periods (and, often, over several rigidity or energy bins) counts every
period and bin tried.

- **Periods.** An evenly sampled series of `N` bins has about `N/2` independent Fourier frequencies; an oversampled
  frequency grid makes neighbouring trials correlated, so its number of grid points is not the number of trials. For
  uneven sampling the effective number of independent frequencies is estimated by simulation (Horne and Baliunas 1986,
  for a white-noise null; under the red-noise null the toys below count the trials).
- **Energy bins.** Series in neighbouring rigidity bins share the physical variability and the systematics, so they
  are strongly correlated. A Bonferroni factor (the number of bins) is conservative; treating each bin as a separate
  search with no correction is not acceptable.
- **Toys of the complete procedure.** The reliable global p-value repeats the whole search on simulated null series:
  draw all rigidity bins jointly from the fitted red-noise null with their cross-rigidity correlation plus `C`, rerun
  the null fit, the periodogram over every trial period and every bin, and take the largest local statistic; the
  global p is the fraction of toys that reach the observed maximum, with its binomial uncertainty (a bound when none
  do). This is the principle that `<plugin root>/skills/hep-statistics/scripts/global_significance.py` (labelled
  EXPERIMENTAL) implements for Poisson-count scans (the best variant chosen inside every toy) and that
  `<plugin root>/skills/hep-statistics/scripts/look_elsewhere.py brute` implements for a 1D scan. Neither script takes
  a periodogram of a correlated series: use them as the pattern and for their tail and binomial conventions
  (`core/stats/tail_estimation.py`), not as the tool. The Gross-Vitells bound in `look_elsewhere.py gross-vitells` is
  implemented for one degree of freedom; a periodogram ordinate has two (amplitude and phase), so the shipped bound
  does not apply to it directly. Record the seed and the toy count.

## Joint fits of several periods

When a time-dependent parameter (for example a modulation potential) is fitted in several periods, fit the periods
together rather than one at a time:

- **Parameters.** One modulation parameter per period, `phi_p` (p = 1..P); shared parameters `theta` (the
  quantities that do not change with time, such as an unmodulated spectrum's shape); one nuisance `nu_k ~ N(0, 1)` per
  time-independent systematic source, shared by every period.
- **Likelihood.** With the residual `r = y - m(theta, phi_p) (1 + sum_k delta_k nu_k)` over all (period, rigidity)
  bins, `chi2 = r^T (C_stat + C_tdep)^-1 r + sum_k nu_k^2`. `C_tdep` keeps its cross-period blocks when `tau` is not
  short compared with the gap between periods. Putting `C_tind` into the covariance instead is not equivalent: built
  from the measured values it biases the fit low (Peelle's pertinent puzzle), and built from the model (`C(theta)`
  with `ln det`) it was also biased low on the Peelle setup of `covariance_fit.py`, while the explicit nuisance was not.
- **Why jointly.** Fits of single periods each absorb the same time-independent systematic, so their `phi_p` are
  correlated; fitting a trend to them as if independent mis-states its uncertainty. The joint fit returns the full
  covariance of `(phi_1 .. phi_P, theta)`: differences `phi_p - phi_q` are usually much better constrained than each
  `phi_p`. Report that correlation matrix, and the profile in any parameter that is strongly correlated with `theta`
  or with a nuisance.
- **Tool.** `<plugin root>/skills/hep-statistics/scripts/covariance_fit.py fit` with a plug-in model
  (`{"plugin": {"path", "function", "n_params"}}`, `n_params` = the shared parameters plus `P`; `x` can be a running
  bin index that the function maps to period and rigidity; the plug-in file runs with your permissions, so only with
  `--allow-plugin`). Its `multiplicative` mode `nuisance` fits one common normalization and needs a rank-one relative
  covariance (constant fractions add into one); several sources with different time or rigidity shapes need explicit
  nuisances in the plug-in (the `model` mode is biased low for a normalization, see the likelihood above). A
  force-field modulation model is in
  `<plugin root>/skills/hep-measurement/scripts/solar_modulation_force_field.py`; the physics of the model and its
  validity range belong to hep-measurement and hep-theory.
- **Closure first.** Generate synthetic series from known `phi_p` and `theta` with the full covariance, fit them, and
  check bias and pull widths before any fit to data (the skill's injection-and-closure invariant).

## Multi-era joint fits

When the detector changes during data taking (an added layer, a new readout, a recalibration), the eras have different
responses, acceptances and collection times, and one spectrum is fitted to all of them:

- **Model.** For era e and reconstructed bin i, `mu^e_i = sum_j (R^e A^e T^e)_ij Phi_j Delta_j + b^e_i`, with `R^e`
  the era's response (migration from truth bin j), `A^e` its acceptance, `T^e` its collection time, `Phi_j` the
  common flux in truth bin j of width `Delta_j` and `b^e_i` the era's background. The flux parameters are shared;
  responses, acceptances and backgrounds are per era.
- **Era nuisances.** Each systematic enters with the correlation across eras that the measurement spec declares
  (`systematics[].era_correlation`, M3 in hep-measurement's analysis design): one shared nuisance when correlated,
  one per era when uncorrelated, and a stated scheme when partial. Per-era corrections (`eras[].corrections`) give
  per-era nuisances.
- **Check consistency first.** Before the joint fit, test that the eras agree where no physical change is expected:
  `<plugin root>/skills/hep-statistics/scripts/split_consistency.py` on the per-era results, with the shared blocks
  declared. A failed test is a finding about the eras (a correction or response that differs), not a reason to inflate
  uncertainties until the joint fit passes.
- **Size.** The core tools stop at their caps (template fits: 60 bins, 6 templates; see the core/stats guide). Above
  them, use parametrized forward folding: fold `Phi(theta)` through each era's response
  (hep-detector, response and forward folding) and fit `theta` with `covariance_fit.py fit --allow-plugin` and a
  plug-in model, or with the pyhf adapter (one channel per era).
- **Model-card diagnostic (opt-in).** When the joint fit is described by model cards, freeze them with
  `python3 <plugin root>/contracts/analysis_check.py freeze ... --mode model` and run `check`: the model-card suite
  reports whether each auxiliary measurement is used once (`r-aux.use`) and whether parameters shared across eras are
  declared as shared (`r-share.parameters`). The rules run in shadow mode: the report is a diagnostic and never
  changes a fit's status.
- **Report.** The per-era and joint results, the split-consistency p-values, the era-nuisance scheme, and the joint
  fit's parameter covariance; closure on synthetic eras before data.

## Deliverables

- The covariance blocks, the evidence or assumption behind each (time-independent sources, correlation times or epoch
  boundaries, rigidity correlation), the validator output, and the limit checks above.
- For a periodicity claim: the null model (trend, AR(1) or power law) and how it was fitted with `C`, the trial periods
  and bins, the local and global p-values with the toy count and seed, and the number of cycles in the span.
- For a joint fit: the parameter list (per period and shared), how the time-independent part entered (nuisance or
  model-built covariance), the full parameter covariance, and the closure result on synthetic series.

## Sources

- Brockwell, P. J. and Davis, R. A., *Time Series: Theory and Methods*, 2nd ed., Springer (1991), Ch. 10 (periodogram
  distribution).
- D'Agostini, G., NIM A346 (1994) 306 (normalization uncertainties in fits; Peelle's pertinent puzzle).
- Gilman, D. L., Fuglister, F. J. and Mitchell, J. M., J. Atmos. Sci. 20 (1963) 182 (the power spectrum of red noise).
- Horne, J. H. and Baliunas, S. L., ApJ 302 (1986) 757 (independent frequencies of an unevenly sampled periodogram).
- Lomb, N. R., Astrophys. Space Sci. 39 (1976) 447; Scargle, J. D., ApJ 263 (1982) 835 (periodogram for uneven
  sampling).
- Mudelsee, M., Computers & Geosciences 28 (2002) 69 (TAUEST: AR(1) persistence for uneven spacing).
- Schulz, M. and Mudelsee, M., Computers & Geosciences 28 (2002) 421 (REDFIT: red-noise spectra of unevenly spaced
  series).
- Torrence, C. and Compo, G. P., Bull. Am. Meteorol. Soc. 79 (1998) 61 (AR(1) red-noise background spectrum).
- Vaughan, S., A&A 431 (2005) 391 (periodic signals in red noise, with uncertain noise parameters); Vaughan, S.,
  MNRAS 402 (2010) 307 (Bayesian test, posterior predictive p-values).
- Vaughan, S. et al., MNRAS 461 (2016) 3145 (false periodicities from red noise with few cycles).
- Gross, E. and Vitells, O., Eur. Phys. J. C 70 (2010) 525 (upcrossing bound used by `look_elsewhere.py`).

Standard linear algebra, not cited to a source here: the Kronecker product of positive semi-definite matrices is
positive semi-definite, and the eigenvalues of a tridiagonal Toeplitz matrix (the negative eigenvalue at `rho = 0.7` is
checked by the test).
