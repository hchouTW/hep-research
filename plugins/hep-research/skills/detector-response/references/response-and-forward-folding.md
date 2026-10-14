# Response objects and forward folding

This is the one place for the response object, folding a prediction through it, and the double-counting checks
(ownership table in `docs/routing-contract.md`). Unfolding algorithms, regularization, coverage and every fit that
uses the response belong to hep-statistics ([unfolding](../../hep-statistics/references/unfolding.md)).

## The response object

Define `nu = D_reco * R * D_truth * x + b` (written out under forward folding below). Specify axis orientation,
efficiency treatment, missed truth events, out-of-fiducial contributions/reconstruction fakes, and luminosity. Truth-bin
sums normalized to unity (columns for `rows_reco_cols_truth`) no longer encode efficiency loss; do not mix that convention with one that includes
losses.

Check folding with a small hand-calculable matrix. Document purity and stability with their denominators (orientation `rows_reco_cols_truth`): purity `p_i = N_ii / sum_j N_ij`, the fraction of reco-bin-i events generated in truth bin i (state whether fakes are in the denominator); stability `s_j = N_jj / N_sel,j` (or `/ N_gen,j`; say which), the fraction of truth-bin-j events reconstructed in bin j. Bin purity is not the object purity of [performance metrics](performance-metrics-and-residual-diagnostics.md).
Assess conditioning, rank, and identifiable truth bins. Signed MC contributions are not literal transition
probabilities and need suitable response-estimation and uncertainty treatment.

**Finite-MC uncertainty of the response.** The matrix is estimated from a finite simulated sample, so it is itself
uncertain. Per truth bin `j`, the reco entries plus a "lost" class (not selected, or reconstructed outside the axes)
are multinomial with `N_j` generated events, so `Cov(R_ij, R_kj) = (delta_ik R_ij - R_ij R_kj)/N_j`, and different
truth bins are independent. With weights, use `sum w` and `sum w^2` per cell (effective counts). Propagate it with
`core/stats/unfolding_diagnostics.py response-covariance` or `response-stat` (hep-statistics,
[core statistics commands](../../hep-statistics/references/core-stats-commands.md)), and record the counts in the
artifact's `mc_stat` (`kind: generated_counts` with `events_per_truth_bin`, or `sumw2`): from contracts 2.8.0 a
response for unfolding without it is unresolved.

**Fakes.** Reconstructed events with no truth match under the matching criterion of
[reconstruction performance and truth matching](reconstruction-performance-and-truth-matching.md) form a reco-space
vector `b_fake`, estimated from simulation with that criterion and validated in a control region; they belong in `b`,
not in `R`. Keeping them as an extra truth column is possible if declared; the validator warns
(`response.fakes_inside`) when `fakes` is listed in `includes`.

**Time-dependent responses.** Conditions change, so a response built for one period does not describe another. Build
one matrix per period with stable conditions and combine them with exposure (or luminosity) weights,
`R_eff = sum_t w_t R_t / sum_t w_t`, or fold each period separately; record them in the artifact's `periods`
(`id`, `exposure_weight`, `matrix` or `matrix_ref`) rather than in the free `conditions` string
([calibration and alignment](calibration-and-alignment.md)).

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
  declared. From a counts table, `R_ij = N_ij / N_gen,j` when the inefficiency is inside (`conditional_on_generated`), and `R_ij = N_ij / N_sel,j` when it is outside (`conditional_on_selected`), where `N_sel,j` counts the selected events of truth bin j including those reconstructed outside the reco axes (declare them as explicit underflow/overflow).
- `D_reco`: diagonal corrections in reco space, applied after migration: a trigger or selection efficiency measured in
  the reconstructed variable, and data/MC scale factors binned in reco.
- `b`: additive reco-space terms: fakes, out-of-fiducial truth that is reconstructed, and backgrounds.

Diagonal corrections in different spaces do not commute with `R`: a reco-binned efficiency moved into truth space, or
the reverse, changes the result wherever migration is large. State for each correction its space, its position in the
product, and whether it is inside `R`; the artifact records this in `correction_space` (term ->
`{space: truth | reco | global, binned_in, order}`; `global` for scalars such as luminosity, exposure or live time,
`truth` or `reco` binned in a variable otherwise, never `reco` for acceptance or a fiducial correction). Every correction is applied exactly once: one that sits inside the matrix is never
applied again outside it, and a detector-level prediction is never folded a second time.

Declare the response's intended use (`intended_use`): `forward_folding`, `unfolding` or `parametric_fit`. Fewer reco
than truth bins, a rank-deficient matrix and a truth bin with zero efficiency (for example below threshold) defeat
unfolding but are legitimate for forward folding, which only loses information there; for a parametric fit what must be
identifiable is the model parameters, not every truth bin. The folded prediction is a `prediction` in reco space with
the response reference and its status; the fit that uses it is a hep-statistics deliverable.

## Worked example: a 2x2 response checked by hand

The fixture `contracts/fixtures/artifacts/valid/response_v28.json` (SYNTHETIC) declares a `cos_theta` response with
the inefficiency inside (`conditional_on_generated`), the acceptance and the luminosity outside:

```json
{"orientation": "rows_reco_cols_truth", "normalization": "conditional_on_generated",
 "inefficiency": "inside_matrix", "acceptance": "outside_matrix", "includes": ["migration", "efficiency"],
 "applied_separately": ["acceptance", "luminosity"], "underflow_overflow": "not_represented",
 "intended_use": "unfolding", "matrix": [[0.7, 0.1], [0.1, 0.6]],
 "mc_stat": {"kind": "generated_counts", "events_per_truth_bin": [10000, 10000]},
 "correction_space": {"acceptance": {"space": "truth", "binned_in": "cos_theta"}, "luminosity": {"space": "global"}}}
```

The truth-bin sums 0.8 and 0.7 are the efficiencies inside the matrix. Folding `x = (1000, 500)` (already corrected
for acceptance and luminosity) with `b = (5, 5)`: `nu_1 = 0.7*1000 + 0.1*500 + 5 = 755`,
`nu_2 = 0.1*1000 + 0.6*500 + 5 = 405`. `contracts.response_adapter.fold` gives the same numbers
(`tests/contracts/test_response_contract.py`). With `N_j = 10000`, `sigma(R_11) = sqrt(0.7*0.3/10000) = 0.0046`.

## Double-counting checks

Write the `response` artifact, then run `python3 "<plugin root>/contracts/validate.py" <artifact>` and
`python3 "<plugin root>/contracts/response_adapter.py" <artifact> --validate`; both must pass before another skill
consumes it.

| Tool | Checks | Does not check |
|---|---|---|
| `contracts/validate.py` (native from contracts 2.8.0, older artifacts with `--strict`) | declarations: vocabulary, misspelled keys, `intended_use` and `underflow_overflow` declared, placement against `includes` and normalization, exposure not listed with the acceptance or live time it contains, flow vectors with `explicit_bins`, `correction_space`, `mc_stat`, variation shapes, and the numbers of an *inline* matrix through the two tools below | the numbers behind a `matrix_ref` (it opens no other file: unresolved `response.numeric_unchecked`) |
| `contracts/response_adapter.py ART --validate` | the numbers: orientation, sums against the normalization, signs, shape against the edges, rank and conditioning, lost probability with the flow vectors, closure when given; reads `matrix_ref` (`file.json` or `file.json#key` inside the artifact folder, an object with `matrix`, `underflow`, `overflow`) | physical validity |

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
