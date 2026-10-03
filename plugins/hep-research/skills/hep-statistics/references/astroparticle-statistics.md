# Astroparticle Statistics: Significance, Trials, and Exposure

Covers the statistical methods specific to astroparticle searches - ON/OFF counting
significance, the look-elsewhere problem in its astroparticle forms (blind sky scans,
source catalogs, time windows), and exposure/effective-area weighting for a
steeply falling flux. General likelihood, interval, and combination machinery
(profile likelihoods, CLs, Asimov data, RooFit/pyhf) is unchanged from
[likelihood-fitting.md](likelihood-fitting.md) through
[statistical-tools.md](statistical-tools.md) and
[inference-recipes.md](inference-recipes.md) and applies here without
modification; this file covers what is different about the astroparticle setting,
not a restatement of general HEP statistics.

For the flux and interval of a few-count spectral bin (why `sqrt(N)` is wrong, units,
resolution spillover, background), read
[low-count, high-rigidity bins](../../detector-response/references/space-based-direct-detection.md#low-count-high-rigidity-bins).

## The ON/OFF counting problem and Li & Ma significance

The canonical astroparticle measurement is a Poisson counting experiment with signal
region counts `N_on` (source direction/energy/time window) and a background estimate
`N_off` drawn from a region with no expected signal but `alpha` times less (or more)
exposure/normalization than the ON region - used throughout
[imaging Cherenkov](../../detector-response/references/imaging-atmospheric-cherenkov.md) and
[neutrino astronomy](../../detector-response/references/neutrino-astronomy.md) alike. The **Li & Ma (1983)**
significance, derived from the likelihood ratio between the signal-plus-background and
background-only hypotheses under this model, is

    S = sqrt(2) * sqrt(
          N_on * ln[ ((1+alpha)/alpha) * (N_on / (N_on + N_off)) ]
        + N_off * ln[ (1+alpha) * (N_off / (N_on + N_off)) ]
        )

signed positive for an excess (`N_on > alpha * N_off`) and negative for a deficit.
`${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/scripts/li_ma_significance.py` computes this statistic, including the boundary
cases `N_on = 0` and `N_off = 0` where one logarithm's argument vanishes. Two points
recur in review of this statistic:

- It is the likelihood-ratio statistic itself, `S = sqrt(-2 ln lambda)` with the sign of
  the excess (Li & Ma 1983, eq. 17); the `sqrt(2)` above sits in front of the log sum, not
  outside `sqrt(-2 ln lambda)`. Reading `S` as a standard-normal deviate is asymptotic
  (Wilks' theorem), and its accuracy degrades for small `N_on` and `N_off`. It is still
  preferred to the naive Gaussian formula `(N_on - alpha*N_off)/sqrt(N_on + alpha^2*N_off)`,
  which fails much sooner, but it is not exact at low counts. At `N_on = 4`, `N_off = 2`,
  `alpha = 0.25` the asymptotic p-value is 6.65e-3, the toy-calibrated value (plug-in
  background, 200,000 toys, seed 1) about 9.0e-3, and the exact conditional (binomial)
  value 1.70e-2 (`tests/skills/hep_statistics/test_li_ma_significance.py`). For a few
  counts, quote a calibrated p-value: `--toys N --seed S` (background fitted under the
  null and plugged in, not a supremum over the background) or `--exact-conditional`
  (`N_on` given `N_on + N_off` is binomial with `alpha/(1+alpha)`; free of the background
  nuisance and conservative for discrete data). Name the method next to the number.
- `alpha` must be measured or modeled correctly for the exposure/acceptance actually
  achieved by each region (see the background-estimation discussion in
  [imaging Cherenkov](../../detector-response/references/imaging-atmospheric-cherenkov.md) and
  [neutrino astronomy](../../detector-response/references/neutrino-astronomy.md)); an `alpha` that silently drifts
  with time, zenith angle, or camera radius while being treated as constant biases
  every significance computed from it.

## The look-elsewhere effect in its astroparticle forms

The trials-factor correction (see
[inference-recipes.md](inference-recipes.md) for the general treatment) takes
specific, recurring forms in this domain that are easy to under-count:

- **Blind all-sky or source-catalog scans**: testing a significance map at many
  independent trial positions (an all-sky scan) or against many candidate source
  positions (a catalog search) requires the number of statistically independent
  trials, which for a scan is *not* simply the number of pixels - adjacent pixels are
  correlated by the point-spread function, so the effective trials count is roughly
  `N_eff ~ min(N_positions, scanned area / PSF solid angle)` - never *more* than the
  number of positions actually tested (a grid finer than the PSF gives the area term; a
  coarser grid gives `N_positions`). For a quick bound, `p_global = 1 - (1 -
  p_local)^N_eff`; e.g. a 3.0 sigma local hotspot (one-sided p = 1.35e-3) from a 1000-position scan
  has `p_global` about 0.74 for `N_eff = 1000` and about 0.13 even for `N_eff = 100` -
  not a detection either way. Estimating the correct global
  p-value from pixel-level local p-values is standard practice done via simulated
  background-only sky maps (scrambled data, per
  [neutrino astronomy](../../detector-response/references/neutrino-astronomy.md)'s RA-scrambling) rather than an
  analytic pixel-count correction, precisely because of this correlation.
- **Multiple energy bins, time windows, or source catalogs tested and not fully
  reported**: an analysis that quotes the single most significant bin/window/catalog
  entry out of several examined must correct for all of them, not only the one
  presented - the same "if you don't report the trials, state why none were needed"
  discipline as general HEP look-elsewhere practice.
- **Stacking/catalog analyses** (combining many known, weaker candidate sources into
  one joint test statistic, e.g. a joint likelihood over a full source catalog) trade
  per-source trials for a single, pre-defined joint hypothesis test and do *not*
  themselves require a trials correction across the stacked sources - but do require
  that the catalog and weighting scheme were fixed before looking at the data, or the
  choice of which sources to stack becomes its own hidden trial.

## Exposure, effective area, and forward-folding

Because every flux in this domain is measured against a steeply falling spectrum, the
exposure (effective area/volume times live time times solid angle, integrated over
the relevant energy-dependent acceptance) must be evaluated **differentially in
energy**, not as a single flat number, and combined with the instrument's energy
migration matrix by forward-folding an assumed spectral model rather than dividing
counts by a single acceptance and unfolding bin-by-bin - the same steep-spectrum
argument stated in
[cosmic-ray spectrum and composition](../../detector-response/references/cosmic-ray-spectrum-and-composition.md),
[imaging Cherenkov](../../detector-response/references/imaging-atmospheric-cherenkov.md), and
[measurements-and-unfolding.md](../../hep-analysis/references/measurements-and-unfolding.md). A quoted
upper limit or best-fit flux that does not state the assumed spectral shape used in
the exposure weighting is not reproducible, because a harder or softer assumed
spectrum shifts the effective exposure (and hence the limit) systematically.

## Deliverables

- The counting method (Li & Ma or an equivalent likelihood-based statistic, not a
  Gaussian approximation) and the exact `N_on`, `N_off`, and `alpha` used.
- The computed local significance and p-value (run `${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/scripts/li_ma_significance.py`;
  do not estimate it by eye), with the p-value method named (asymptotic, toys with seed
  and count, or exact conditional; at low counts not the asymptotic one alone), and, for a scan, the post-trials p-value with a plain
  verdict (e.g. "not a detection").
- The number of independent trials (positions, energy bins, time windows, source
  catalogs) and the method used to estimate it (analytic count, or scrambled/
  simulated background maps for spatially correlated trials), or a stated reason none
  were needed.
- Whether a stacking/catalog analysis's source list and weighting were fixed before
  looking at the data.
- The spectral shape assumed for exposure weighting/forward-folding in any flux, limit,
  or significance result, and confirmation that unfolding (if used at all) was
  checked against the forward-folded alternative for a steep-spectrum bias.
- The energy- and (where relevant) zenith-angle-dependent effective area/volume used,
  from full detector simulation rather than a single flat acceptance number.
