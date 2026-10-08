---
name: hep-statistics
description: "Use when the deliverable is a statistical inference or its diagnostics in physics: likelihoods, binned and unbinned fits, template fits, fits of model parameters to published data points with their covariance, frequentist intervals and limits (Neyman, Feldman-Cousins, CLs, profile likelihood, asymptotics), Bayesian posteriors (priors, samplers, convergence), significance and look-elsewhere effects, low or zero counts, nuisance parameters, covariance assembly and validation, unfolding with regularization and coverage, fits that use a folded prediction, toys and Asimov datasets, goodness of fit, model comparison, and combinations across datasets or experiments. Load it first even for a quick interval, limit or fit, and for inference outside v1 (for example cosmic-ray propagation fits), where it says what it cannot cover. Not for: physics inputs not provided (hep-analysis, detector-response, hep-theory); selections (hep-analysis); predictions (hep-theory)."
---

# hep-statistics: inference

**Owns:** likelihoods, frequentist and Bayesian inference, intervals and limits, covariance assembly, model comparison, unfolding algorithms and regularization, fits that use a response, toys, coverage, combinations; stewardship of `core/stats`.
**Typical artifacts:** `statistical-result`, `comparison-spec` (inference part), diagnostics.
**Never:** invent a correlation, a prior or a physics assumption; turn a theory envelope into a Gaussian without the hep-theory prescription; report a fit that did not converge as a result.

## Invariants

- Declare the paradigm. Frequentist results state the test statistic, the construction, and coverage checks. Bayesian results state priors, the sampler, and convergence diagnostics. Neither is labeled as the other.
- Approximations are named and validated: Gaussian, Wilks, asymptotic, exact Poisson, toys. Low or zero counts, parameters on a boundary, and non-Gaussian tails get exact or toy-based treatment.
- Missing covariance stays missing; never assume a diagonal matrix silently. Correlations across bins, species, periods or experiments need evidence or a scoped, stated assumption.
- Overlapping datasets or shared auxiliary measurements are never combined by multiplying likelihoods as if independent.
- Before any mixed inference, the comparison gate must report the inputs comparable (same quantity, units, binning, phase space, level, normalization, conventions) or list the declared transformations.
- Injection tests and closure on Asimov and toy data precede any claim about observed data; Asimov, synthetic and observed results keep their labels.
- Failed or not-run fits propagate as `failed` / `not-run`; downstream artifacts keep it.

## Workflow

1. Resolve context (stanza below). Collect inputs as artifacts: measurement spec, response, prediction, dataset records.
2. Run the compatibility gate when inputs come from different producers: `python3 <plugin root>/contracts/comparison/gate.py PREDICTION.json MEASUREMENT.json --plan PLAN.json` (declared transformations, mappings and measurement conditions; exit 1 lists each mismatch and what would resolve it).
3. Build the statistical model: observables, parameters of interest, nuisances and constraints, correlations with their evidence.
4. Validate on Asimov and toys (bias, pull widths, coverage), then fit.
5. Write the `statistical-result` with paradigm-specific fields and validate it.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

`<plugin root>` is the folder two levels above this `SKILL.md`; `<plugin root>/...` paths are relative to it.

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; read a bound profile before answering about its experiment. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; check them with `python3 "<plugin root>/contracts/project.py" <project-dir>`. A bound profile found in neither place may come from a companion plugin: load the installed `<plugin>:profile` skill that names it and use the folder it gives as a local profile. If none is installed, or a non-public local or companion profile lacks `agent_policy` approval for this host (none has it yet), say the profile is unavailable; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never in the plugin; check them with `python3 "<plugin root>/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

References: [core/stats guide](references/core-stats-guide.md) for choosing and reading the executable checks, [nuisance modeling](references/nuisance-modeling.md) (constraints, interpolation, pruning, correlation schemes), [likelihood fitting](references/likelihood-fitting.md) (including sWeights and weighted unbinned fits), [unfolding](references/unfolding.md), [inference recipes](references/inference-recipes.md), [statistical tools including pyhf and Combine](references/statistical-tools.md), [astroparticle statistics](references/astroparticle-statistics.md), [ML-assisted inference](references/ml-assisted-inference.md) when a trained model enters a likelihood or posterior, and [inference reasoning](references/statistical-inference-for-physics.md) for checking a likelihood, test, interval or limit.

Executable checks live in `<plugin root>/core/stats/` (likelihood limits, template fits, unfolding diagnostics, Poisson diagnostics, toys, covariance and response validation); read `--help` first. When a shell is available, run the matching script for exact limits and intervals and report its output; label a value worked by hand as such. `<plugin root>/skills/hep-statistics/scripts/li_ma_significance.py` gives the ON/OFF significance (toy or exact conditional p-values at low counts); in that folder, `look_elsewhere.py` the global significance of a 1D scan, `sensitivity_and_gof.py` Asimov discovery sensitivity and toy-calibrated goodness of fit, and `bayes_diagnostics.py` R-hat, ESS and MCSE of supplied chains and prior reweighting; the Poisson counting reference: `<plugin root>/skills/hep-analysis/scripts/counting_reference.py`; `combine_measurements.py` (needs NumPy) combines measurements of one observable by generalized least squares once the combination plan accepts them (declared cross-dataset blocks, shared auxiliary measurements, no Gaussianized envelope); `combine_asymmetric.py`: Barlow's asymmetric errors. pyhf and Combine starting points: `<plugin root>/adapters/pyhf-combine/assets/`, with `<plugin root>/adapters/pyhf-combine/assets/pyhf_nuisance_diagnostics.py` for pulls, constraints, impacts and grouped impacts; unbinned fits: `<plugin root>/adapters/unbinned-fit/assets/unbinned_fit.py`.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Missing systematic or correlation evidence | hep-analysis / detector-response | request in `unresolved_inputs` |
| Theory-uncertainty prescription | hep-theory | `prediction` |
| Large toy campaigns, batch partitioning | hep-computing | `computational-run` |
| Reporting the result | research-communication | `statistical-result` |
| SBI, neural likelihoods | physics-ml | `ml-artifact` |
