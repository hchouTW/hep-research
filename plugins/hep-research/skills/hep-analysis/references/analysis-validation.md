# Validation, Debugging, and Reproducible Delivery

## Validation layers

1. **Schema:** expected files, branches, edges, units, corrections, and POI/nuisance names exist.
2. **Numerics:** weights and rates are finite, variances nonnegative, parameter bounds appropriate, and sumw2 complete.
3. **Physics:** validate cutflows, normalization, region overlap, closure, variation propagation, and selection migration.
4. **Statistics:** assess convergence, identifiability, profiles, bias/injection, and the need for toys or coverage studies.
5. **Reproducibility:** compare chunks/threads, repeated seeds, alternative backends, or small analytic references as relevant.

Match tests to the task. A prose edit does not require full production reprocessing; a weight-convention change requires yield and variance comparisons. Record tolerances and their rationale. Parallel floating-point reductions need not be bitwise identical without a specific reason.

## Histogram bundle schema

See `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/assets/histograms.example.json` for a complete minimal example.

- `schema_version`: integer 1.
- `kind`: `mc` or `poisson_expectation`. Negative MC bins produce warnings; negative Poisson expectations produce errors.
- `histograms`: a nonempty mapping. Each histogram has `edges` of length N+1 and `sumw`/`sumw2` of length N. Values must be finite numbers, edges strictly increasing, and sumw2 nonnegative.
- Optional `expected_variations`: a list of required names. Optional `variations`: a mapping whose entries contain full edges/sumw/sumw2 arrays with matching nominal edges. Names such as JESUp are labels; the tool does not infer physical direction.

This format represents one-dimensional bins without flow bins. Export upstream using a documented flow policy. It does not encode cross-bin covariance; passing the audit does not justify ignoring covariance. The tool does not modify or clip input.

Exit codes: 0 means no hard errors, possibly with warnings; 1 means invalid content/structure; 2 means CLI usage error. Warnings include negative signed MC bins, nonzero sumw with zero sumw2, cancellation bins, and variations identical to nominal. They are investigation cues rather than automatic proof of a defect.

## Symptoms and first checks

| Symptom | Inspect first |
|---|---|
| Yield differs by a factor of 1000 | Luminosity/cross-section units |
| Refactor changes yields | Mask axes, sorting, flow, duplicate weights, missing files |
| Large multithreading differences | Shared state, seeding, duplicate merges, ordering |
| NaN or infinity | Zero denominators, empty collections, correction range |
| Boundary fits or singular covariance | Degeneracy, bounds, invalid expectations |
| Limit equals maximum scan value | Threshold bracketing and failed fits |
| Identical Up/Down templates | Payload selection, sensitivity, generation chain |
| Excessive postfit constraint | Reused data, wrong correlation, overly restrictive constraints |

## Regression outputs

Compare N, sumw, sumw2, edges, and maximum absolute/relative bin differences by sample and region. Use absolute tolerances near zero. Compare selection membership using stable event keys for important event-level changes.

Preserve fit status, EDM or equivalent optimizer messages, covariance quality, parameters/bounds, NLL, expected rates, and profile curves. Do not log a failed fit and still emit a formal limit as valid.

## Preservation

Use `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/assets/report-template.md`. Include commit/diff, environment lock or container digest, input/configuration/payload checksums, seeds, commands, blinding state, model, and validation. Label synthetic, Asimov, and observed outputs separately. For unexecuted checks, give the reason and a concrete follow-up command or procedure.
