# Systematic Uncertainties and Nuisance Correlations

This file covers the physical sources, their payloads and correlations. How each source then enters the likelihood (constraint form, interpolation code, one-sided and two-point variations, MC-statistics modifiers, pruning criteria) and the post-fit pulls, impacts and breakdowns are owned by hep-statistics: [nuisance modeling](../../hep-statistics/references/nuisance-modeling.md).

## Source inventory

Use `<plugin root>/skills/hep-analysis/assets/systematics.csv` to record source, type, affected processes/eras/regions, correlation key, rate/shape behavior, payload, and validation. Nuisance names have statistical meaning: sharing a name often shares a parameter. Do not reuse names solely for convenience. For a paper or note, `<plugin root>/skills/hep-analysis/scripts/systematics_table_tex.py` renders the registry as a booktabs LaTeX table and refuses one without a status label (synthetic, observed, ...).

Correlations follow shared physical sources, measurement procedures, and documented prescriptions. Neither "all uncertainties in one year are correlated" nor "different years are independent" is a valid blanket rule. Decompose luminosity, JES, or object scale factors into justified components when prescribed. Represent partial Gaussian correlations with a covariance matrix or latent standard-normal variables; verify positive semidefiniteness and compatibility of pairwise correlations.

## Types and propagation

- **Rate-only:** change normalization with a parameterization valid over the relevant parameter domain. Log-normal factors are common for positive multiplicative effects, not mandatory for every source.
- **Shape:** preserve nominal/up/down templates, including bin and region migration. Renormalize only for a defined shape-only source and specified domain. Avoid adding the same rate effect again if templates already contain it.
- **Detector:** propagate affected four-momenta, sorting, selection, missing transverse momentum, categories, and related weights. Pairing variations on the same events helps control comparison noise.
- **Theory:** document scale combinations/envelopes, exclusions, PDF replica/Hessian confidence conventions, alpha-s, shower/hadronization, and generator alternatives according to the production prescription.
- **MC statistics:** model finite simulation precision independently of observed-data counting fluctuations. Check the applicability of Barlow–Beeston-type approximations to weighted or signed samples.

## Variation registry and implementation pattern

Keep a central registry (`<plugin root>/skills/hep-analysis/assets/systematics.csv` or equivalent) recording, per
source: variation name and downstream suffix; type (weight, shape,
normalization-only, one-sided, envelope, theory set); samples affected; the data
exclusion rule; the correlation model across eras/channels/bins/processes; the
nominal branch or weight the variation replaces; and the validation tolerance with
known exceptions.

When implementing variations in code: build nominal histograms first; iterate over a
configured variation list rather than hand-writing each one; for weight systematics
replace only the weight expression; for shape systematics replace only the affected
kinematic columns and recompute any dependent selections (recomputing selections for a
weight-only variation, or failing to recompute them for a shape variation that moves
objects across thresholds, are both common bugs); write output objects using the exact
naming the downstream datacard or plotting tool expects; and record skipped variations
with a reason instead of silently dropping them.

## Is a variation's shift significant?

A varied selection shares most events with the nominal one, so the statistical spread of the shift is the
uncorrelated part only. For the data, Barlow's subset/superset approximation `sigma_diff^2 ~ |sigma_var^2 -
sigma_nom^2|` is a common estimate. The simulation is overlapping too: rebuild nominal and varied corrections on the
same bootstrap replicas of the simulated sample (paired bootstrap) and take the spread of their difference. Leaving the
simulation part out can make a stable variation look significant: in a synthetic test where simulation and data
statistics were comparable, a data-only test flagged 8 of 22 bins of one variation, and the paired test 3 of 99 bins
over all variations, the rate expected by chance at 2 sigma. A shift beyond these statistics is an effect to explain
before it is quoted; one within them is not evidence that the source is absent.

## Template validation

Check edges, flow handling, finite values, variance bookkeeping, required sources, and units. Identical variations are an investigation flag, not proof of a bug. Migration may lower a bin for an Up variation; integral ordering cannot establish whether labels are reversed. Inspect payloads and generation code to establish direction.

A zero nominal with a nonzero variation needs explicit treatment; do not define ratios with arbitrary epsilons. Negative sample templates require a backend-compatible model. Investigate additional MC, justified rebinning, or a model supporting signed contributions. If smoothing or regularization is used, preserve raw templates and quantify closure, bias, and result changes.

## Model validation

Evaluate nuisance values at -1, 0, +1 and relevant extrapolation points. Check finite, valid expected rates and continuity within the designed parameter domain. Unbounded scanning of every nuisance is not required.

Quantify sensitivity, shape, correlation, and POI consequences before pruning sources. A small postfit impact alone does not justify removal. Freezing groups is a diagnostic; uncertainty decompositions can depend on method and order. Correlated impacts are not independent errors to add in quadrature.
