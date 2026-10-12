# Response objects and forward folding

This is the one place for the response object, folding a prediction through it, and the double-counting checks
(ownership table in `docs/routing-contract.md`). Unfolding algorithms, regularization, coverage and every fit that
uses the response belong to hep-statistics ([unfolding](../../hep-statistics/references/unfolding.md)).

## The response object

Define `nu = D_reco * R * D_truth * x + b` (written out under forward folding below). Specify axis orientation,
efficiency treatment, missed truth events, out-of-fiducial contributions/reconstruction fakes, and luminosity. Columns
normalized to unity generally no longer encode efficiency loss; do not mix that convention with one that includes
losses.

Check folding with a small hand-calculable matrix. Document purity/stability denominators and assess conditioning,
rank, and identifiable truth bins. Signed MC contributions are not literal transition probabilities and need suitable
response-estimation and uncertainty treatment.

Truth and reco variables are named with units; if they differ (for example rigidity and its inverse), state the
conversion. A binned response is a conditional distribution `p(reco bin | truth bin)` and needs no Jacobian; a Jacobian
applies only when a continuous density is transformed from one variable to the other. Record the conditions (period,
geometry, calibration version) the response was built with; a response is time-dependent until shown otherwise.

## Forward folding a prediction

Fold a truth-level prediction as

```
nu = D_reco * R * D_truth * x + b
```

- `x`: the truth-level prediction per truth bin (events, or a rate times exposure or luminosity).
- `D_truth`: diagonal corrections in truth space, applied first: acceptance and fiducial fraction, and an efficiency
  that depends only on the truth variable, when they sit outside `R`.
- `R`: the migration matrix, `R_ij = P(reco bin i | truth bin j)`, with or without the inefficiency inside it as
  declared. From a counts table, `R_ij = N_ij / N_gen,j`.
- `D_reco`: diagonal corrections in reco space, applied after migration: a trigger or selection efficiency measured in
  the reconstructed variable, and data/MC scale factors binned in reco.
- `b`: additive reco-space terms: fakes, out-of-fiducial truth that is reconstructed, and backgrounds.

Diagonal corrections in different spaces do not commute with `R`: a reco-binned efficiency moved into truth space, or
the reverse, changes the result wherever migration is large. State for each correction its space, its position in the
product, and whether it is inside `R`. Every correction is applied exactly once: one that sits inside the matrix is never
applied again outside it, and a detector-level prediction is never folded a second time.

Declare the response's intended use (`intended_use`): `forward_folding`, `unfolding` or `parametric_fit`. Fewer reco
than truth bins, a rank-deficient matrix and a truth bin with zero efficiency (for example below threshold) defeat
unfolding but are legitimate for forward folding, which only loses information there; for a parametric fit what must be
identifiable is the model parameters, not every truth bin. The folded prediction is a `prediction` in reco space with
the response reference and its status; the fit that uses it is a hep-statistics deliverable.

## Double-counting checks

`<plugin root>/core/stats/validate_response.py` checks orientation, normalization against the declared convention,
efficiency or acceptance counted twice or not at all, probability lost outside the axes, empty bins and phase-space
holes, and folds `closure` spectra when given (under `counts` it divides by `generated_per_truth_bin`, and without it
reports the closure as `not_assessable`). Its `metadata.intended_use` sets the identifiability verdict: errors for
`unfolding` (and, with a warning to declare the use, when it is absent), warnings for `forward_folding` and
`parametric_fit`. `<plugin root>/contracts/response_adapter.py` converts a `response` artifact into that validator's
input (it maps `name`, `conditional_on_generated`, `joint_counts` and the `applied_separately` list, and refuses values
it cannot map) and folds through the result; use it instead of declaring the metadata a second time.

The artifact validator rejects a `response` whose metadata places an efficiency inside the matrix and also applies it
separately (`response.double_counted`). From contracts 2.4.0 (older artifacts with `--strict`) it also reads
`includes` and `applied_separately` against the `response_corrections` vocabulary, where every `<x>_efficiency` term
counts as an efficiency, and requires `matrix` or `matrix_ref` for a matrix, normalization consistent with what sits
inside the matrix (`conditional_on_selected` keeps inefficiency and acceptance outside; `joint_counts` cannot hold the
inefficiency) and one unit per variable. The comparison gate rejects folding a detector-level prediction. A clean
report says `"physical_validity": "not_assessed"`: consistency with the declared conventions is not evidence that the
response is physically right.
