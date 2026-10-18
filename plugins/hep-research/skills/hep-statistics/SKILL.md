---
name: hep-statistics
description: "Use when the deliverable is a statistical inference or its diagnostics in physics: likelihoods, binned and unbinned fits, template fits, fits of model parameters to published data points with their covariance (saying if no shipped tool covers it), frequentist intervals and limits (Feldman-Cousins, CLs, profile likelihood, asymptotics), Bayesian posteriors (priors, samplers, convergence), significance and look-elsewhere effects, low or zero counts, nuisance parameters, covariance assembly and validation, unfolding with regularization and coverage, fits that use a folded prediction, toys and Asimov datasets, goodness of fit, model comparison, and combinations across datasets or experiments; also RooFit/RooStats, pyhf. Load it first even for a quick interval, limit or fit, and for inference outside v1 (e.g. global propagation fits), where it says what it cannot cover. Not for: producing missing physics inputs or selections (hep-measurement, hep-detector), predictions (hep-theory); code (hep-computing)."
---

# hep-statistics: inference

**Owns:** likelihoods, frequentist and Bayesian inference, intervals and limits, covariance assembly, model comparison, unfolding algorithms and regularization, fits that use a response, toys, coverage, combinations; stewardship of `core/stats`.
**Typical artifacts:** `statistical-result`, `comparison-spec`, diagnostics.
**Never:** invent a correlation, a prior or a physics assumption; turn a theory envelope into a Gaussian without the hep-theory prescription; report a fit that did not converge as a result.

## Invariants

- Declare the paradigm: frequentist results state the test statistic, construction and coverage checks; Bayesian results state priors, sampler and convergence diagnostics; neither is labeled as the other.
- Approximations are named and validated: Gaussian, Wilks, asymptotic, exact Poisson, toys. Low or zero counts, parameters on a boundary, and non-Gaussian tails get exact or toy-based treatment.
- Missing covariance stays missing; never assume a diagonal matrix silently. Correlations across bins, species, periods or experiments need evidence or a scoped, stated assumption.
- Overlapping datasets or shared auxiliary measurements are never combined by multiplying likelihoods as if independent.
- Before any mixed inference, the comparison gate must report the inputs comparable (units, binning, level, normalization, conventions) or list the declared transformations.
- Injection tests and closure on Asimov and toy data precede any claim about observed data from a new model; a validated core tool's own tests count as closure only for the model they test. Asimov, synthetic and observed results keep their labels.
- Failed or not-run fits propagate as `failed` / `not-run`; downstream artifacts keep it.

## Step 0: quick question, and task to tool

One number: when a shell is available, run its row's tool, state the construction and approximation, and label a value worked by hand as such; the workflow is for new models. `cs/` = `<plugin root>/core/stats/`, `sc/` = `<plugin root>/skills/hep-statistics/scripts/`; read `--help` first; caps and more rows in the guide.

| Request | Default | Fallback |
|---|---|---|
| Counting limit, known b | `cs/poisson_diagnostics.py cls-limit`, `fc-interval` | classical: `upper-limit` |
| Counting limit, uncertain b | `cs/likelihood_limits.py profile-cls --expected-toys N` | `profile-limit`; Berger-Boos `neyman-limit` |
| Discovery | `cs/likelihood_limits.py profile-significance`; bins: `shape-significance` | ON/OFF: `sc/li_ma_significance.py` |
| Multi-bin limit, nuisances; two POIs | `cs/likelihood_limits.py shape-limit`; `contour` | beyond the caps: pyhf adapter |
| Scan look-elsewhere | `sc/look_elsewhere.py brute`, `gross-vitells` | `sc/global_significance.py run` |
| Do split samples agree (eras, halves) | `sc/split_consistency.py --input` (chi2 of d = x1 - x2, shared blocks subtracted) | toy p-values: `--toys N --seed S` |
| Uncertainty or reach at k times the exposure | `sc/project_uncertainty.py budget.json --k 2,4` (M5 scaling classes; label `projection`) | Asimov Z: `counting` in the input |
| Background tail from a control region | `sc/tail_extrapolation.py --input` (validated; envelope kept apart) | then `cls-limit`, `profile-cls` |
| Combination | `sc/combine_measurements.py` | asymmetric errors: `sc/combine_asymmetric.py` |
| D'Agostini iterations | `cs/statistical_toys.py unfold-scan`, then `cs/unfolding_diagnostics.py closure` | unfold data with covariance: `dagostini-unfold` |
| MCMC posterior | user's sampler, `sc/bayes_diagnostics.py diagnose`, then `result_artifact.py --paradigm bayesian` | SBC: `sc/bayes_calibration.py sbc` |
| Fit to published points, covariance | `sc/covariance_fit.py fit` (line, exponential, broken power law, plug-in with `--allow-plugin`) | break position: `break-scan` |
| Ratio with covariance | `cs/statistical_toys.py ratio-cov` (counts <= 1e5) | counts >= 1e4: `ratio-cov-analytic` |
| Write the result | `sc/result_artifact.py` | then `contracts/validate.py --gate publication` |

## Workflow

1. Resolve context (stanza below); collect inputs as artifacts (measurement spec, response, prediction, dataset records) and validate each (`contracts/validate.py`; a response also `response_adapter.py --validate`); stop on a contract error.
2. Inputs from different producers: run `<plugin root>/contracts/comparison/gate.py` (exit 1 lists each mismatch).
3. Build the model: observables, POIs, nuisances and constraints, correlations with their evidence.
4. Validate on Asimov and toys (bias, pulls, coverage); fit; write the `statistical-result` with `scripts/result_artifact.py`; validate `artifacts_dir`. A report: load hep-communication.

## Resources

| Request | Read or run |
|---|---|
| Which core/stats tool, conventions, caps, exit codes | [core/stats guide](references/core-stats-guide.md); per module: [command reference](references/core-stats-commands.md) |
| Hypotheses, p-values, intervals, what a result means | [inference recipes](references/inference-recipes.md), [inference reasoning](references/statistical-inference-for-physics.md) |
| Likelihood construction, template and weighted fits | [likelihood fitting](references/likelihood-fitting.md); `covariance_fit.py`, `sweighted_fit.py` |
| Systematics in the likelihood: constraints, interpolation | [nuisance modeling](references/nuisance-modeling.md) |
| pyhf, HistFactory, Combine | [statistical tools](references/statistical-tools.md); `<plugin root>/adapters/pyhf-combine/` |
| Unfolding, regularization, coverage | [unfolding](references/unfolding.md); `<plugin root>/adapters/unfolding/` |
| Combining measurements or experiments | [combinations](references/combinations.md); `combine_measurements.py`, `combine_asymmetric.py` |
| Covariance from declared correlation models (length, AR(1), time), with a scan | `build_covariance.py` (labeled [Proposal]) |
| ON/OFF counting, trials, exposure | [astroparticle statistics](references/astroparticle-statistics.md); `li_ma_significance.py`, `look_elsewhere.py` |
| Time series: periodicity, change points, lags, split consistency | [time-series inference](references/time-series-inference.md); `split_consistency.py`, `periodicity_scan.py`, `time_structure.py` |
| ML-assisted inference, SBC | [ML-assisted inference](references/ml-assisted-inference.md); `bayes_calibration.py` |
| MCMC convergence, prior reweighting | `bayes_diagnostics.py` |
| RooFit/RooStats: status, weights, pulls, calculators | [RooFit and RooStats](references/roofit-and-roostats-methods.md); `roofit_fit_check.py` |
| Write the statistical-result artifact | `result_artifact.py` |
| Unbinned fits | `<plugin root>/adapters/unbinned-fit/` |
| Outside v1 (global propagation fits, EFT global fits) | say so; general discipline; full list: `<plugin root>/docs/routing-contract.md`, Scope of v1 |

Scripts in `<plugin root>/skills/hep-statistics/scripts/`, modules in `<plugin root>/core/stats/` (read `--help` first). Folder guide: [README.md](README.md).

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

`<plugin root>` is the folder two levels above this `SKILL.md`.

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; if present, run `python3 "<plugin root>/contracts/project.py" <project-dir> --preflight` and read the indexes it prints. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; `--preflight` checks them. A bound profile in neither place, or at a local path known to be a companion's, is used only via the installed `<plugin>:profile` skill that names it, after its preflight, from its folder; never scan for companions. If none is installed, the preflight fails, or a non-public profile lacks `agent_policy` approval for this host (none has it yet), say it is unavailable, do other work; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, global cosmic-ray propagation fits): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default ./hep-research-artifacts/), never the plugin, and pass `python3 "<plugin root>/contracts/validate.py" <artifacts_dir>`; no scratch. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Handoffs

Missing systematic or correlation evidence: hep-measurement, hep-detector (`unresolved_inputs`); theory-uncertainty prescriptions: hep-theory; toy campaigns, batch jobs: hep-computing; reporting: hep-communication; SBI, neural likelihoods: hep-ml.
