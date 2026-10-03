---
name: hep-statistics
description: "Use when the deliverable is a statistical inference or its diagnostics in physics: likelihoods, binned and unbinned fits, template fits, fits of model parameters to published data points with their covariance, frequentist intervals and limits (Neyman, Feldman-Cousins, CLs, profile likelihood, asymptotics), Bayesian posteriors (priors, samplers, convergence), significance and look-elsewhere effects, low or zero counts, nuisance parameters, covariance assembly and validation, unfolding and forward folding with regularization and coverage, toys and Asimov datasets, goodness of fit, model comparison, and combinations across datasets or experiments. Load it first even for a quick interval, limit or fit, and for inference outside v1 (for example cosmic-ray propagation fits), where it says what it cannot cover. Not for supplying physics assumptions or correlations that were not provided (hep-analysis, detector-response, hep-theory), designing selections (hep-analysis), or deriving predictions (hep-theory)."
---

# hep-statistics: inference

**Owns:** likelihoods, frequentist and Bayesian inference, intervals and limits, covariance assembly, model comparison, unfolding and forward-folding algorithms, toys, coverage, combinations; stewardship of `core/stats`.
**Typical artifacts:** `statistical-result`, `comparison-spec` (inference part), diagnostics.
**Never:** invent a correlation, a prior or a physics assumption; turn a theory envelope into a Gaussian without the hep-theory prescription; report a fit that did not converge as a result.

## Invariants

- Declare the paradigm. Frequentist results state the test statistic, the construction, and coverage checks. Bayesian results state priors, the sampler, and convergence diagnostics. Neither is labeled as the other.
- Approximations are named and validated: Gaussian, Wilks, asymptotic, exact Poisson, toys. Low or zero counts, parameters on a boundary, and non-Gaussian tails get exact or toy-based treatment.
- Missing covariance stays missing; never assume a diagonal matrix silently. Correlations across bins, species, periods or experiments need evidence or a scoped, stated assumption.
- Overlapping datasets or shared auxiliary measurements are never combined by multiplying likelihoods as if independent.
- Before any mixed inference, the comparison gate must report the inputs comparable (same quantity, units, binning, phase space, level, normalization, conventions) or list the declared transformations.
- Injection tests and closure on Asimov and toy data precede any claim about observed data; Asimov, synthetic and observed results keep their labels.
- Failed or not-run fits propagate as `failed` / `not-run`; downstream artifacts keep that status.

## Workflow

1. Resolve context (stanza below). Collect inputs as artifacts: measurement spec, response, prediction, dataset records.
2. Run the compatibility gate when inputs come from different producers: `python3 ${CLAUDE_PLUGIN_ROOT}/contracts/comparison/gate.py PREDICTION.json MEASUREMENT.json --plan PLAN.json` (declared transformations, mappings and measurement conditions; exit 1 lists each mismatch and what would resolve it).
3. Build the statistical model: observables, parameters of interest, nuisances and constraints, correlations with their evidence.
4. Validate on Asimov and toys (bias, pull widths, coverage), then fit.
5. Write the `statistical-result` with paradigm-specific fields and validate it.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

1. Use the profiles the user names explicitly. Otherwise read `hep-research.project.json` in the project root, if it exists. Never infer an experiment or a model from vague wording. If the task needs a profile and none can be determined, ask which one.
2. Only when a profile is needed, read `${CLAUDE_PLUGIN_ROOT}/profiles/registry.json` (a short index), then that profile's `index.md`, then only the modules or dataset records the task needs. Experiment and theory profiles are independent: load neither unless the task needs it, and never load an unrelated experiment.
3. Local profiles named in the project config live in the project and are checked with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/project.py" <project-dir>`; never copy them into the plugin.
4. No profile needed: proceed with general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so explicitly, then apply the general discipline of this skill.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never inside the plugin. Check them with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the language the user writes in (for example English or Traditional Chinese); keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

References: [core/stats guide](references/core-stats-guide.md) for choosing and reading the executable checks, [nuisance modeling](references/nuisance-modeling.md) (constraints, interpolation, pruning, correlation schemes), [likelihood fitting](references/likelihood-fitting.md) (including sWeights and weighted unbinned fits), [inference recipes](references/inference-recipes.md), [statistical tools including pyhf and Combine](references/statistical-tools.md), [astroparticle statistics](references/astroparticle-statistics.md), [ML-assisted inference](references/ml-assisted-inference.md) when a trained model enters a likelihood or posterior, and [inference reasoning](references/statistical-inference-for-physics.md) for checking a likelihood, test, interval or limit.

Executable checks live in `${CLAUDE_PLUGIN_ROOT}/core/stats/` (likelihood limits, template fits, unfolding diagnostics, Poisson diagnostics, toys, covariance and response validation); run each with `--help` first. `${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/scripts/li_ma_significance.py` gives the ON/OFF significance (with toy or exact conditional p-values at low counts); in the same folder, `look_elsewhere.py` gives the global significance of a 1D scan, `sensitivity_and_gof.py` the Asimov discovery sensitivity and a toy-calibrated goodness of fit, and `bayes_diagnostics.py` R-hat, ESS and MCSE for supplied chains and prior reweighting; the Poisson counting reference is `${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/counting_reference.py`; `combine_measurements.py` (needs NumPy) combines measurements of one observable by generalized least squares only after the combination plan accepts them (declared cross-dataset blocks, shared auxiliary measurements, no Gaussianized envelopes). pyhf and Combine starting points are in `${CLAUDE_PLUGIN_ROOT}/adapters/pyhf-combine/assets/`, with `${CLAUDE_PLUGIN_ROOT}/adapters/pyhf-combine/assets/pyhf_nuisance_diagnostics.py` for pulls, constraints, impacts and grouped breakdowns.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Missing physical systematic or correlation evidence | hep-analysis / detector-response | request in `unresolved_inputs` |
| Theory-uncertainty prescription | hep-theory | `prediction` |
| Large toy campaigns, batch partitioning | hep-computing | `computational-run` |
| Reporting the result | research-communication | `statistical-result` |
