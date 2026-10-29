# hep-statistics

Statistical inference and its diagnostics for physics: likelihoods, fits, intervals and limits, significance, covariance, unfolding, toys, model comparison and combinations, with the construction and approximation stated and checked.

## Core capabilities

- Likelihoods: binned and unbinned fits, template fits, sWeights and weighted unbinned fits, fits that use a folded prediction or a response.
- Fits of model parameters to published data points with their covariance, including the `tabulated-grid` model (parameters tabulated on a grid of predictions) and joint fits of several datasets with a scale nuisance on a dataset's abscissa.
- Frequentist intervals and limits: Neyman, Feldman-Cousins, CLs, profile likelihood, asymptotics; low or zero counts with exact or toy-based treatment.
- Bayesian posteriors: priors, samplers, convergence diagnostics (R-hat, ESS, MCSE), prior reweighting, simulation-based calibration.
- Significance and look-elsewhere effects (brute-force toys, Gross-Vitells upcrossings), ON/OFF significance (Li-Ma, exact conditional p-values), Asimov sensitivity, toy-calibrated goodness of fit.
- Nuisance parameters, constraints and interpolation; degeneracy diagnostics (a Fisher screen, then profile-likelihood scans).
- Covariance assembly and validation, including a `[Proposal]` covariance from declared correlation models (none, full, log-length, antisymmetric, AR(1), exponential in time, a user matrix).
- Unfolding with regularization and coverage (closure, stress tests, toy coverage).
- Toys and Asimov datasets, injection tests, bias, pulls, coverage.
- Model comparison and combinations across datasets or experiments (generalized least squares, BLUE, asymmetric errors, likelihood-level).
- PDF, nPDF and FF fit statistics: chi2 forms, t0, tolerances, reweighting and Hessian profiling of published PDF sets.
- Time series: periodicity scans, change points, lags, split-sample consistency, time-bin covariance.
- Uncertainty and reach projections to k times the exposure (labelled `projection`), control-region tail extrapolation.
- RooFit/RooStats fit checks; pyhf, HistFactory and Combine starting points.
- Stewardship of `core/stats`.

## Triggering conditions

Use when:

- the deliverable is a statistical inference or its diagnostics in physics;
- a quick interval, limit or fit is asked for;
- a fit, limit, significance, posterior, covariance, unfolding, combination or PDF reweighting/profiling question arises, including RooFit/RooStats and pyhf;
- the inference is outside v1 (for example global propagation fits): the skill says what it cannot cover.

Not for:

| Need | Hand to |
|---|---|
| Missing systematic or correlation evidence | hep-measurement or hep-detector |
| Theory-uncertainty prescription, predictions | hep-theory |
| Large toy campaigns, batch partitioning, code | hep-computing |
| Reporting the result | hep-authoring |
| SBI, neural likelihoods | hep-ml |

## Workspace directory architecture

```text
hep-statistics/
├── SKILL.md
├── README.md
├── assets/
│   └── combine.example.json
├── references/
│   ├── core-stats-guide.md
│   ├── core-stats-commands.md
│   ├── statistical-inference-for-physics.md
│   ├── inference-recipes.md
│   ├── likelihood-fitting.md
│   ├── unfolding.md
│   └── ...
└── scripts/
    ├── covariance_fit.py
    ├── combine_measurements.py
    ├── result_artifact.py
    └── ...
```

| Path | Content |
|---|---|
| `SKILL.md` | entry point: invariants, Step 0 for a quick question and the task-to-tool table (default tool, fallback, or "no shipped tool"), workflow, context resolution |
| `references/` | fourteen references: PDF, nPDF and FF fit statistics (chi2 forms, t0, tolerances, reweighting, profiling), the `core/stats` decision guide and its command reference, combinations (BLUE, Peelle, likelihood-level), nuisance modeling, likelihood fitting (including sWeights and weighted unbinned fits), unfolding, inference recipes, statistical tools (pyhf, Combine), astroparticle statistics, binned time series (documented; its time-bin covariance recipe demonstrated on synthetic data by `test_time_series_covariance.py`), ML-assisted inference, RooFit and RooStats methods, inference reasoning |
| `assets/` | `combine.example.json`: SYNTHETIC input for `combine_measurements.py` (two experiments, shared luminosity) |
| `scripts/` | twenty-seven helpers (listed below); the executable checks themselves (limits, template fits, unfolding diagnostics, Poisson diagnostics, toys, covariance and response validation) live in `core/stats/` |

Scripts:

- `li_ma_significance.py`: ON/OFF significance, exact conditional p-values at low counts.
- `look_elsewhere.py`: global significance of a 1D scan; `global_significance.py`: toy-calibrated global significance for a recorded scan.
- `sensitivity_and_gof.py`: Asimov discovery sensitivity, toy-calibrated goodness of fit.
- `bayes_diagnostics.py` (R-hat, ESS, MCSE, prior reweighting), `bayes_calibration.py` (SBC).
- `combine_measurements.py` (generalized least squares once a combination plan accepts the inputs), `combine_asymmetric.py` (Barlow's asymmetric errors).
- `tail_extrapolation.py`: a control-region tail extrapolated into the signal region, validated on a cut of the control region, the envelope between models kept apart.
- `project_uncertainty.py`: an uncertainty budget and Asimov significance projected to k times the exposure with the M5 scaling classes, and the reach; every output labelled `projection`.
- `split_consistency.py`: agreement of split samples such as eras (chi2 of the difference with the declared shared covariance subtracted, a generalized chi2 for K splits, Sidak or toy correction of the pairwise tests).
- `covariance_fit.py`: fits to published points with covariance (line, exponential, broken power law, plug-in with `--allow-plugin`; `break-scan`); its `tabulated-grid` model fits parameters tabulated on a grid of predictions, one gated `prediction` per node, reports degenerate directions, and with a `degeneracy_scan` block runs profile-likelihood scans through `degeneracy.py`; demonstrated on synthetic data, end to end in `examples/bc-propagation-fit/`.
- `degeneracy.py`: two-level degeneracy diagnostics (a Fisher screen, then profile-likelihood scans that record the range where a degeneracy holds).
- `propagation_fit.py`: multi-dataset propagation fits through a registered provider.
- `build_covariance.py`: a `[Proposal]` covariance from declared correlation models, each block checked for positive semi-definiteness, with a scan of the length.
- `periodicity_scan.py`: weighted generalized Lomb-Scargle on unevenly sampled series; band-maximum global p-value from white, AR(1) or Ornstein-Uhlenbeck surrogates, the red-noise null refitted on every surrogate by default; caps on points, frequencies and surrogates.
- `time_structure.py`: `changepoint` (binary segmentation or PELT, threshold or penalty calibrated by toys to a declared false-alarm rate) and `lag` (cross-correlation with phase-randomized surrogates and a look-elsewhere correction over lags, hysteresis between rising and falling branches).
- `pdf_reweighting.py`, `hessian_profiling.py`: updating published PDF sets.
- `roofit_fit_check.py`: RooFit status, pulls, cross-checks with core.
- `extract_names.py`: the naming extractor for nuisances, channels and processes.
- `discrete_profile.py`, `eft_scan.py`, `pcl_efficiency_ratio.py`, `ratio_estimation.py`, `sweighted_fit.py`.
- `result_artifact.py`: writes a `statistical-result` from a tool's output; `--paradigm bayesian` from `bayes_diagnostics.py diagnose` output with priors and sampler.

Outside this folder: `core/stats/` (executable checks), `adapters/pyhf-combine/assets/` (pyhf and Combine starting points), `adapters/unbinned-fit/assets/` (unbinned fits), `adapters/unfolding/assets/unfold.py` (iterative unfolding through pyunfold or RooUnfold, validated by closure, stress tests and toy coverage).

## Input and output specifications

Inputs:

- Request: the inference wanted, with its paradigm, construction and confidence level where known.
- Profiles and context: only through the context-resolution steps in `SKILL.md`; no experiment facts are embedded.
- Files read: handed-over artifacts (measurement spec, response, prediction, dataset records), each first checked with `contracts/validate.py <file>`; a response also with `response_adapter.py --validate`. Inputs from different producers pass `contracts/comparison/gate.py` (exit 1 lists each mismatch) before any mixed inference.

Outputs:

- `statistical-result` artifacts (written with `scripts/result_artifact.py`), the inference part of `comparison-spec`, and diagnostics, as JSON in the project's `artifacts_dir`, never inside the plugin.
- Status labels (`synthetic`, `asimov`, `observed`, `failed`, `not-run`, `projection`) stay on everything derived from them.

Script CLI contract:

```text
python3 <plugin root>/skills/hep-statistics/scripts/<script>.py --help
python3 <plugin root>/core/stats/<module>.py <subcommand> --help
```

- Every script prints `--help`; outputs are JSON.
- Exit codes: 0 ok; 1 a negative verdict (a refused fit or input, a fit that did not converge: `failed`); 2 an input the tool cannot use (JSON message on stdout), also a missing NumPy or SciPy; 3 `incomplete` (for example a missing data covariance or uncertainty correlation in `covariance_fit.py` or `propagation_fit.py`, only toy fits failed in `likelihood_limits.py`, an undeclared weight treatment in `roofit_fit_check.py`). Per-module codes: [core/stats guide](references/core-stats-guide.md).
- Every toy-based subcommand requires `--seed` and echoes it with the toy count and configuration.

## Setup requirements

- Python 3.13 or newer.
- Standard library first: unmarked scripts use the standard library only.
- NumPy (and SciPy for some scripts) for the marked scripts, which refuse to run without them with exit 2 and a JSON message.
- PyROOT (a Python that can `import ROOT`) for `roofit_fit_check.py`.
- pyhf, ArviZ and Combine for the corresponding backends and adapters; pyunfold or RooUnfold for `adapters/unfolding/assets/unfold.py`.
- No environment variables.

## Operational constraints

- Never invents a correlation, a prior or a physics assumption.
- Never turns a theory envelope into a Gaussian without the hep-theory prescription.
- Never reports a fit that did not converge as a result; failed or not-run fits propagate as `failed` / `not-run`.
- Declares the paradigm; frequentist and Bayesian results are never labelled as each other.
- Approximations (Gaussian, Wilks, asymptotic, exact Poisson, toys) are named and validated.
- Missing covariance stays missing; never assumes a diagonal matrix silently.
- Never combines overlapping datasets or shared auxiliary measurements by multiplying likelihoods as if independent.
- Injection tests and closure on Asimov and toy data precede any claim about observed data from a new model.
- Runs the matching check when a shell is available; a value worked by hand is labelled as such.
- A successful script run is a software check, not scientific validity.
- The authoritative statement of these rules is [SKILL.md](SKILL.md).

## Validation

- `tests/skills/hep_statistics/`: thirty-six test modules, including `test_grid_fit.py` for the `tabulated-grid` model and `test_time_series_covariance.py`.
- `core/stats` tests under `tests/core/`.
- Statistics benchmarks under `examples/stats-benchmarks/`, the `unfolding-coverage` example, the `bc-propagation-fit` example (`tests/examples/test_bc_propagation_fit.py`).
- GitHub `stats-backends` and `statistics-validation` jobs (pyhf, ArviZ, Combine), recorded in `VALIDATION.md`.
- What is and is not validated: `docs/capability-matrix.md`; the evidence: `VALIDATION.md`.

## Example requests

Request kinds from the Step 0 table in [SKILL.md](SKILL.md):

- A counting limit with known or uncertain background.
- A discovery significance, or ON/OFF significance.
- The look-elsewhere effect of a scan.
- Whether split samples (eras, halves) agree.
- An uncertainty or reach at k times the exposure.
- A combination of measurements, including asymmetric errors.
- An MCMC posterior with convergence diagnostics.
- A fit to published points with their covariance.
- Writing the result (also unfolded) as a `statistical-result`.
