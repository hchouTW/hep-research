# Path D report: QED prediction vs synthetic reconstructed data (SYNTHETIC)

**Status: synthetic.** The data come from the illustrative `experiment:synthetic-collider` generator with sigma_gen = mu x sigma_pred and mu = 1 injected; the harness passes sigma_pred from the Path C artifact to the generator. The fit therefore tests the comparison chain, not physics. No statement about new physics is made or possible.

Reproduce: `python3 examples/theory-comparison/run.py --toys 200 --seed 20261004` (from the plugin root, after Paths B and C; D5 environment). Profiles loaded: `experiment:synthetic-collider`, `theory:qed-benchmark`.

## Contract trace

Path C `prediction` → comparison gate (`comparison_spec.json`) → `folded_expectation.json` → `result.json` (mu fit). Every Path D artifact carries the `synthetic` status inherited from the data and the response.

Gate transformations, in order: bin-integrate (owner hep-theory); multiply-by-normalization (owner hep-statistics); forward-fold (owner hep-statistics). Declared convention mapping: angle definitions equivalent (wording differs). Core convention keys stated only by the prediction (spin treatment, mass approximation) are reported as notes.

## Pre-declared criteria and outcome

| Check | Criterion | Result |
|---|---|---|
| Composition of both profiles | namespaces disjoint, ids qualified | pass |
| Comparison gate | comparable after declared transformations | pass |
| Response | identical to the Path B response matrix | pass |
| Folded expectation vs independent quadrature | max relative deviation < 1e-06 | pass (5.6e-08) |
| Asimov injection at mu = 1 and 1.25 | abs(mu_hat - mu) < 1e-08 | pass |
| Identifiability | without the luminosity constraint q(1.15) ≈ 0 (mu x L is what the counts fix) | pass |
| Synthetic sample at mu = 1 | abs(pull) < 3.0 | pass |
| Toys at mu = 1 and 0.8 | mean pull abs < 0.2, width in (0.85, 1.15) | pass |
| 68% interval coverage | within 3 binomial sigma (0.099) of 0.683 | pass |
| Mismatched variants | each rejected, naming the field | pass |
| Documented conversion (T08) | fiducial restriction + level identification accepted | pass |
| Contract artifacts | all valid with both profile vocabularies | pass |

## Result on the synthetic sample

sigma_pred = 868.0 pb (Path C). 17521 events generated; measured luminosity 19.726 pb^-1 (synthetic auxiliary measurement). mu_hat = 1.0233, 68% interval [1.0010, 1.0464], pull against the injected value 1.04. The bounded rounding nuisance makes mu_hat a plateau [1.0227, 1.0238].

| Injected mu | toys | mean pull | pull width | 68% coverage |
|---|---|---|---|---|
| 1 | 200 | -0.0195 | 0.9671 | 0.71 |
| 0.8 | 200 | -0.0405 | 1.015 | 0.655 |

## Rejected variants

| Variant | Rejected | Reported field and reason |
|---|---|---|
| prediction at a different sqrt(s) | yes | `parameter_point.sqrt_s_gev`: prediction computed at a different parameter point |
| prediction in nb without a unit conversion | yes | `transformations[1]`: the normalization value expects a different unit for the cross section |
| prediction bins differ from the response truth bins | yes | `transformations[2]`: prediction bins differ from the response truth bins |
| point values compared with bins without a mapping | yes | `transformations[0]`: point values cannot be compared with bins without a defined mapping |
| efficiency applied before folding with a response that includes it | yes | `transformations[3]`: 'efficiency' already applied before folding; the response includes it too |
| angle definitions without a declared mapping | yes | `conventions.angle_definition`: values differ; declare a transform mapping or use a variant |
| process definitions without a declared mapping | yes | `process`: process differs and free-text equality cannot be established |
| measurement normalized to exposure | yes | `normalization.kind`: normalization kinds differ |
| folded prediction against the unfolded (Path B) result | yes | `level`: levels differ after the declared transformations |
| inclusive prediction against the fiducial unfolded result | yes | `phase_space.fiducial`: fiducial and inclusive phase spaces are not equivalent |

## Limitations

- Truncation (higher orders, Z exchange) is not quantified, so mu is conditional on the tree-level prediction.
- The response uses the predicted shape inside each bin; a different shape hypothesis needs its own response.
- The data are synthetic and generated from the same shape, so agreement is expected by construction.

Figure: `folded_comparison.png`. Artifacts: `artifacts/*.json`.
