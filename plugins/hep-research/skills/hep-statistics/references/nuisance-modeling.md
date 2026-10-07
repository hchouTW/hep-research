# Nuisance Parameters in the Likelihood

How systematic effects enter a likelihood: constraint terms, interpolation between variations, two-point and
one-sided variations, alternative models, MC statistics, smoothing and pruning, the correlation scheme, and the
post-fit diagnostics that check all of it. The physical inventory of sources (what varies, by how much, from which
evidence) belongs to hep-analysis ([systematics](../../hep-analysis/references/systematics.md)) and detector-response;
theory prescriptions belong to hep-theory. This file starts once those are provided, and never invents a variation,
a correlation or a constraint width.

## Contents

1. [Constraint terms](#constraint-terms)
2. [Interpolation between variations](#interpolation-between-variations)
3. [Two-point and one-sided systematics](#two-point-and-one-sided-systematics)
4. [Envelopes and alternative models](#envelopes-and-alternative-models)
5. [MC statistics](#mc-statistics)
6. [Smoothing, symmetrization and pruning](#smoothing-symmetrization-and-pruning)
7. [Correlation scheme](#correlation-scheme)
8. [Post-fit nuisance diagnostics](#post-fit-nuisance-diagnostics)

## Constraint terms

A nuisance `theta` with an auxiliary measurement `a` enters as `L(mu, theta) = L_main(mu, theta) x p(a | theta)`. In a
frequentist analysis `p(a | theta)` is the likelihood of an auxiliary measurement (a calibration, a control region),
not a prior; a Bayesian analysis states priors separately and does not reuse the same information
([likelihood fitting](likelihood-fitting.md)). Choose the form from the origin of the uncertainty:

- **Gaussian** `a ~ N(theta, 1)` with an additive or linear effect `1 + sigma theta`: natural for a calibration
  measured with Gaussian error. A linear rate factor can go negative for large `sigma theta`; protect or choose
  another form.
- **Log-normal** (rate factor `kappa^theta`, Gaussian constraint on `theta`): positive by construction, natural for a
  multiplicative uncertainty quoted as a ratio. It is skewed: `kappa^-1` is not `2 - kappa`, which matters once
  `kappa - 1` is no longer small.
- **Gamma / Poisson auxiliary**: a yield measured in a control sample of `m` events, `m ~ Pois(tau b)`; the effective
  relative width is `1/sqrt(tau b)`. Use it for a control-region or MC-count origin; it is positive and its asymmetry
  follows the count.
- `core/stats/likelihood_limits.py shape-limit` implements all three for normalization nuisances (`gaussian`,
  `lognormal`, `gamma` with `tau = 1/sigma^2`); for small widths they agree, for wide ones they differ, which is the
  point of choosing ([core/stats guide](core-stats-guide.md)).
- Correlated constraints: a multivariate Gaussian with a correlation matrix supplied with evidence, or decomposed
  into independent components (below). An auxiliary measurement shared by two datasets enters the joint likelihood
  once.

## Interpolation between variations

A variation is usually given at `theta = -1, 0, +1` only. The tool interpolates between them and extrapolates beyond;
the choice changes the likelihood away from the three points.

pyhf 0.7.6 (read from the installed source, `pyhf/interpolators/`, 2026-10-03):

| Modifier | Code | Inside `|theta| < 1` | Outside |
|---|---|---|---|
| `normsys` | `code1` | exponential: `(hi)^theta` for `theta >= 0`, `(lo)^(-theta)` below | same |
| `normsys` | `code4` (Model default) | 6th-order polynomial matching value, first and second derivative at `+-1` | exponential, as `code1` |
| `histosys` | `code0` | piecewise linear: `theta (hi - nom)` above 0, `theta (nom - lo)` below (kink at 0) | linear |
| `histosys` | `code4p` (Model default) | `theta S + theta^2 (3 theta^4 - 10 theta^2 + 15) A` with `S = (d+ + d-)/2`, `A = (d+ - d-)/16` | linear |

`pyhf.Model` uses `code4`/`code4p` unless `modifier_settings` says otherwise; the modifier classes alone default to
`code1`/`code0`. `core/stats/likelihood_limits.py shape-limit` implements the same codes (`hi`/`lo` normalization
factors with `code4` by default; shapes `code0` by default, `code4p` on request) and matches pyhf 0.7.6 on a grid
(`tests/core/test_stats_interpolation.py`). A cross-check against another implementation must use the same code,
or it compares different likelihoods: an independent HistFactory reference with exponential normsys first disagreed with pyhf for exactly
this reason (repository history of the pyhf shape cross-check).

Combine (documentation for the recommended tag v11.1.0, read 2026-10-03; not executed in this plugin):

- `lnN` with one value `kappa` multiplies the yield by `kappa^theta`. The asymmetric form `kappa_down/kappa_up` gives
  the yield ratios at `-1` and `+1`; the effective `kappa` equals `kappa_up` for `theta >= 0.5`, `1/kappa_down` for
  `theta <= -0.5`, and a smooth polynomial blend in between
  ([model and likelihood](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/what_combine_does/model_and_likelihood/)).
- `shape` interpolates bin **fractions** vertically: polynomial inside `|theta| < 1`, linear outside; `shapeN`
  interpolates the logarithm of the fractions. The normalization effect of a shape nuisance is a separate asymmetric
  log-normal ([setting up the analysis](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/part2/settinguptheanalysis/)).
  So a pyhf `histosys` (absolute yields) and a Combine `shape` (fractions plus a log-normal norm) are different models
  of the same variation; compare yields at several `theta` before comparing limits.

### Verified walkthrough: code 1 against code 4 (2026-10-03)

`tests/adapters/test_nuisance_interpolation.py` (needs pyhf; skips otherwise) on
`<plugin root>/adapters/pyhf-combine/assets/pyhf-counting.json` (synthetic: s = 5, b = 20, n = 20, normsys
hi/lo = 1.1/0.9):

| Case | `theta = -0.5` | `+0.5` | 95% CLs limit on `mu` |
|---|---|---|---|
| symmetric 1.1/0.9, `code4` | 18.9843 | 20.9863 | 2.1529 |
| symmetric 1.1/0.9, `code1` | 18.9737 | 20.9762 | 2.1541 |
| asymmetric 1.3/0.95, `code4` | 19.2665 | 22.5944 | 2.1145 |
| asymmetric 1.3/0.95, `code1` | 19.4936 | 22.8035 | 2.0525 |

At `theta = +-1` and beyond the two codes agree exactly. For a nearly symmetric variation the limit moves by 0.05%;
for an asymmetric one by 3%. The difference grows with the asymmetry and with how far the fit pulls the nuisance.

## Two-point and one-sided systematics

- **Two-point variations** (two generators, two tunes): there is no `-1` side. Options are a one-sided nuisance (the
  alternative at `theta = 1`, nominal at 0, mirrored or not) or treating it as a discrete choice (next section).
  Mirroring (`down = 2 nom - up`) asserts a symmetric effect that nobody measured: state it as an assumption.
- **One-sided variations** (both up and down move the same way, or only one exists): a symmetric Gaussian nuisance
  built from `max(|up|, |down|)` fits a direction the data cannot reach and can double-count when the same physics
  appears elsewhere. Keep the sign information; if both shifts go the same way, the variation is not a `+-1 sigma`
  pair and needs a source-level explanation from hep-analysis.
- **Symmetrization** (`(up - down)/2` around the nominal, or the larger shift both ways) changes the curvature and the
  center of the nuisance. It is a modeling choice: quantify its effect on the POI (fit with and without) and record it.
- "Max of up and down" applied per bin mixes directions bin by bin and destroys the correlation across bins: never.
- **Quoting a total with asymmetric errors** outside a likelihood (several asymmetric sources on one number, or
  several results with asymmetric errors): adding the up and down shifts in quadrature separately has no justification.
  `<plugin root>/skills/hep-statistics/scripts/combine_asymmetric.py` follows Barlow: `sources` adds cumulants under a
  stated model (quadratic or piecewise) and moves the central value so the mean is kept; `measurements` combines
  results through the linear-variance or linear-sigma approximate likelihood. State the model; a fit with the sources
  as nuisances is better when the likelihood is available.

## Envelopes and alternative models

- An envelope from hep-theory (scale variations, PDF sets) enters only through its prescription. Never turn it into a
  Gaussian nuisance on your own; `contracts/comparison/combination.py` refuses Gaussianized envelopes, and
  `contracts/validate.py` reports `uncertainty.auto_gaussian` for a prediction that does so.
- **Discrete alternatives** (several background functional forms, several generators): profile over the discrete
  choice (discrete profiling, with a penalty per extra parameter stated in advance) or keep the alternatives as
  separate results. A single Gaussian nuisance interpolating between two non-nested functions is not a model of
  either and is not acceptable when the alternatives differ in shape.
- A spurious-signal test (fit a signal on a background-only model of each alternative) measures the bias a choice
  induces; its size and the criterion for accepting a function are fixed before looking at the data.

## MC statistics

- `staterror` (pyhf): one Gaussian nuisance per bin shared by all samples that carry it, width from the summed
  `sum w^2`; the Barlow-Beeston-lite approximation ([Conway 2011](https://doi.org/10.5170/CERN-2011-006.115)). `shapesys`: one Poisson-constrained nuisance per bin
  with a supplied absolute uncertainty. The full Barlow-Beeston likelihood ([Barlow & Beeston 1993](https://doi.org/10.1016/0010-4655(93)90005-W)) has one nuisance
  per bin and template.
- The trade-off is tested in `core/stats`: `statistical_toys.py template-bb` (per-bin lite against true templates) and
  `template_fit.py bb-fit`/`bb-toys` (full per-template; a template with no MC in a bin keeps its true content there as
  a nuisance) ([core/stats guide](core-stats-guide.md)). In `likelihood_limits.py` a bin's `mc_stat` adds the lite
  factor to `multibin-limit`, `shape-limit` and `contour`. Use the lite form
  when one template dominates each bin; when several small-statistics templates share a bin, check the full form.
- One statistical source gets one treatment: never `staterror` and `shapesys` (or a Barlow-Beeston term) on the same
  MC sample. Bins with zero nominal yield and non-zero MC uncertainty need an explicit convention (pyhf does not
  supply one: check the tool's behavior and state the choice).

## Smoothing, symmetrization and pruning

- Keep the raw templates. Smoothing (rebinning the variation, a fit, a kernel) is a modeling step: record the method
  and compare the POI with the raw and the smoothed variation.
- Decide pruning by criteria stated before unblinding, for example: the variation is below a stated fraction of the
  statistical error in every bin **and** removing it changes the expected POI uncertainty by less than a stated
  amount. A small post-fit impact alone does not justify removal ([systematics](../../hep-analysis/references/systematics.md)):
  a nuisance can matter through its correlation with others.
- After pruning, smoothing or symmetrization, rerun the post-fit diagnostics below and report the POI shift of each
  step.

## Correlation scheme

- In pyhf and Combine a nuisance **name** is a correlation: the same name across channels, samples or datasets is
  100% correlated, different names are independent. The naming table is part of the model and must match the
  correlation inventory from hep-analysis.
- A source with partial correlation is decomposed: a shared component plus independent components (`theta_common`,
  `theta_A`, `theta_B`), with the split taken from evidence. A latent-variable form with a stated correlation is
  equivalent when the constraint is multivariate Gaussian.
- Decomposed sources (a calibration split into eigenvector components) stay decomposed; recombining them in quadrature
  loses the shape correlations.
- Correlations across experiments or datasets need evidence; without it, results may be compared but not combined
  (combination plan, hep-statistics `combine_measurements.py`).

## Post-fit nuisance diagnostics

Run after every fit that is used for a result, and after each pruning, smoothing or symmetrization step.

- **Pulls and constraints.** Pull `(theta_hat - theta_0)/sigma_prefit`; constraint `sigma_postfit/sigma_prefit`. A
  pull far from 0 is a tension between the data and the auxiliary measurement; a constraint well below 1 means the
  data measure the nuisance better than its auxiliary measurement did, which needs a physical explanation (and often
  a finer decomposition), not acceptance. The Gaussian pull scale is only an approximation for Poisson- or
  gamma-constrained nuisances.
- **Impacts.** Fix one nuisance at `theta_hat +- sigma` and refit everything else; the POI shift, with its sign, is the
  impact. Pre-fit impacts use `sigma_prefit` (what the nuisance could do), post-fit impacts `sigma_postfit` (what it
  does after the fit). Correlated impacts are not independent errors: never add them in quadrature into a total.
- **Ranking** by post-fit impact shows what drives the result; it is not a pruning criterion on its own.
- **Grouped breakdown.** Freeze a group at its best-fit values and quote `sqrt(sigma_total^2 - sigma_frozen^2)`. The
  result depends on the method (freeze one group, or freeze sequentially) and on the order; report the method, the
  order and the closure of the quadrature sum against the total.
- **Correlations.** List nuisance pairs with large `|rho|` (a stated threshold); `|rho|` near 1 means two nuisances
  describe the same direction and only their combination is measured.
- A refit that fails is a `failed` entry, never a silently missing row.

`<plugin root>/adapters/pyhf-combine/assets/pyhf_nuisance_diagnostics.py` does all of this for a pyhf
workspace (needs pyhf; exit 1 when the nominal fit or a refit fails, 2 for rejected input or no pyhf). Its impacts
agree with independent refits of a HistFactory likelihood written without pyhf to 1e-3 relative or 1e-4 absolute
(`tests/adapters/test_pyhf_nuisance_diagnostics.py`).

### Verified walkthrough: the synthetic shape workspace (2026-10-03, pyhf 0.7.6)

```bash
python3 <plugin root>/adapters/pyhf-combine/assets/pyhf_nuisance_diagnostics.py \
    <plugin root>/adapters/pyhf-combine/assets/pyhf-shape-synthetic.json --groups groups.json --json diag.json
# groups.json: {"theory_like": ["bkg_xsec"], "detector": ["jes"], "mc_stat": ["staterror_synthetic_sr", "cr_shape"]}
```

`mu = 0.795 +- 0.865` (Hessian). `bkg_xsec` ranks first (post-fit impact `-0.210/+0.210`, pre-fit `-0.329/+0.318`)
with a constraint of 0.65: the control region measures the background normalization better than its 1-sigma
auxiliary term, which is why its pre- and post-fit impacts differ. The breakdown gives, freezing one group at a time,
0.208 (theory-like), 0.198 (detector) and 0.285 (MC statistics), with 0.753 statistical (all nuisances frozen); in
quadrature 0.854 against the total 0.865 (closure 0.987). Sequentially, the detector group gives 0.259 in the given
order and 0.194 in the reversed one: the same group, two numbers, which is why the order is part of the result.
These are synthetic numbers for checking the tool, not a physics result.

Combine equivalents (documentation for v11.1.0, read 2026-10-03; not run in this plugin):
`combine -M FitDiagnostics` writes `fit_b`, `fit_s` and `nuisances_prefit` (with `--plots` the covariance matrices,
with `--saveShapes` the pre- and post-fit shapes), and `diffNuisances.py` prints pulls. Impacts come from
`combineTool.py -M Impacts` (`--doInitialFit --robustFit 1`, then `--doFits`, then `-o impacts.json`) and
`plotImpacts.py`; Combine defines the impact with the nuisance at its **post-fit** `+-1 sigma` and plots
the post-fit minus pre-fit value over the uncertainty, `(theta - theta_0)/Delta theta`, with the post-fit/pre-fit width ratio
([non-standard usage](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/part3/nonstandard/)).
