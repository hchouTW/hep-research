# Statistics domain card (owner: hep-statistics)

Questions: is the estimand clear; does the likelihood or estimator match the stated model; are nuisance parameters and
correlations treated as stated; are degrees of freedom, intervals, significance and goodness of fit computed
correctly; is anything assumed that the inputs do not supply?

| Field | Content |
|---|---|
| Typical required material | the model or method description, data definitions, covariance or uncertainty breakdown with correlations, fitted parameters and their count, stated results |
| Methods | assumption and convention check; numerical recomputation (decimal tolerances with a stated rounding rule); counterexample |
| Evidence | the recomputation (inputs, formula, values), the element named (field, number, formula, step) |
| Do not confuse | optimizer convergence with model correctness; Asimov with observed data; a value quoted to fewer digits than the tolerance needs with a wrong method (it is a computing finding) |
| decision_required | usually true for the main statistical treatment |

## Positive case (supported)

Two measurements combined with BLUE; the systematic correlation 0.5 is stated and the covariance used carries the
off-diagonal 0.5·σ₁·σ₂; weights, combined value and uncertainty recompute within the tolerance. Expected: `supported`,
no finding. A reviewer may add a missing input ("the source of the correlation is not given") without a finding.

## Negative case (violated)

Two measurements share a fully correlated calibration systematic, but the covariance used has a zero off-diagonal.
Expected: `violated` with a finding naming the off-diagonal element and the recomputed uncertainty with the
correlation; the computing obligation may still be `supported` because the stated numbers follow the stated (wrong)
method.

## Missing input

The text says "partially correlated" but no coefficient is given. Expected: `undetermined` with the missing
coefficient named, unless the stated numbers are inconsistent for every admissible value (then a finding is
justified; record both).
