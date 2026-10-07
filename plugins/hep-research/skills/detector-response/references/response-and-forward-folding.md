# Response objects and forward folding

This is the one place for the response object, folding a prediction through it, and the double-counting checks
(ownership table in `docs/routing-contract.md`). Unfolding algorithms, regularization, coverage and every fit that
uses the response belong to hep-statistics ([unfolding](../../hep-statistics/references/unfolding.md)).

## The response object

Define `y_reco=R*x_truth+b`. Specify axis orientation, efficiency treatment, missed truth events, out-of-fiducial
contributions/reconstruction fakes, and luminosity. Columns normalized to unity generally no longer encode efficiency
loss; do not mix that convention with one that includes losses.

Check folding with a small hand-calculable matrix. Document purity/stability denominators and assess conditioning,
rank, and identifiable truth bins. Signed MC contributions are not literal transition probabilities and need suitable
response-estimation and uncertainty treatment.

Truth and reco variables are named with units; if they differ (for example rigidity and its inverse), state the
conversion and the Jacobian. Record the conditions (period, geometry, calibration version) the response was built
with; a response is time-dependent until shown otherwise.

## Forward folding a prediction

Fold a truth-level prediction as `nu_reco = R * x_truth * (corrections outside R) + b`, with every correction applied
exactly once: a correction that sits inside the matrix is never applied again outside it, and a detector-level
prediction is never folded a second time. The folded prediction is a `prediction` in reco space with the response
reference and its status; the fit that uses it is a hep-statistics deliverable.

## Double-counting checks

`<plugin root>/core/stats/validate_response.py` checks orientation, normalization against the declared convention,
efficiency or acceptance counted twice or not at all, probability lost outside the axes, empty bins and phase-space
holes, and folds `closure` spectra when given. The artifact validator rejects a `response` whose metadata places an
efficiency inside the matrix and also applies it separately (`response.double_counted`), and the comparison gate
rejects folding a detector-level prediction. A clean report says `"physical_validity": "not_assessed"`: consistency
with the declared conventions is not evidence that the response is physically right.
