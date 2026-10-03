# Changelog — hep-research

Release notes for the plugin. Each entry says what changed in behavior; evidence is in [VALIDATION.md](VALIDATION.md).
Software checks establish contract consistency only, not physical validity.

## Unreleased (hep-statistics reinforcement, 2026-10-03)

Work order `tasks/hep-research/stats-reinforcement/TASK.md` (r2); evidence in VALIDATION STATS-REINFORCEMENT-RUN.

- **Contracts 1.1.0** (minor; every new field optional). `statistical-result` gains `significance` (`local_p`,
  `local_z`, `global_p`, `global_z`, `trials_method` in none-needed / toys / gross-vitells / analytic-bound, `scan`
  with `parameters` and `ranges`), `expected` (`median`, `band_1sigma`, `band_2sigma`, `method`),
  `uncertainty_breakdown` (`method` in group-freeze / impacts / other, `order`, `groups`, `closure`) and
  `goodness_of_fit` (`statistic`, `p_value`, `calibration` asymptotic / toys, `n_toys`); `construction` gains
  `berger-boos`, `cousins-highland` and `toy-calibrated-profile`. New rules: a result with `significance.scan` and
  no `global_p` is `unresolved` (`stats.lee_missing`); a Bayesian result declaring an R-hat above 1.01 with
  `fit_status: converged` is an error (`stats.convergence_mismatch`) for artifacts written under 1.1.0 and a warning
  for 1.0.0 artifacts, which therefore validate as before. Example artifacts now record contract 1.1.0; nothing else
  in them changed.

## Unreleased (validation-gap audit, 2026-10-03)

Fixes from the validation-gap audit (work order `tasks/hep-research/audit/TASK.md`, evidence VALIDATION AUDIT-RUN).
Each has a regression test that failed on the previous code. Several checks now fail closed, so results that used to
pass can now be `unresolved`, `incomplete` or `failed`:

- **Comparison gate** (`contracts/comparison/gate.py`): compares process, species and phase space (structured `cuts`
  exactly; free text only when equal after normalization) and every variable axis, not only the first. Unequal free
  text is `unresolved` until the plan declares a mapping `{"field", "action": "equivalent", "justification"}`. Axis
  transformations on multi-dimensional observables are rejected. The result gains `status` (comparable /
  not-comparable / unresolved) and each mismatch a `kind`.
- **Artifact validation** (`contracts/validate.py`): binned payloads must match the observable's edges and unit (or
  record a `unit_conversion`); multi-dimensional payloads declare `axes`; numerical and grid predictions need
  `values`, symbolic ones `expression`; NaN and Infinity are rejected anywhere. Metadata-only dataset records stay valid.
- **Project-level dependency validation** (new `contracts/dependencies.py`): resolves input refs inside a project
  root and checks existence, type, ID, contract version, sha256 and the statuses the sources really carry; external
  refs are `unresolved`; paths outside the root are refused and never read.
- **Template fit** (`core/stats/template_fit.py`): fits report diagnostics and an outcome; infeasible (a bin with data
  and no template support) or unconverged fits are `failed` with exit code 1 and the artifact fit status `failed`.
- **Blinding scans** (`core/blinding/blinding.py`, `audit_blinded_outputs.py`): `.npy` caches are read; scans report
  `pass` / `fail` / `incomplete` (only `pass` is ok; exit 3 for incomplete); strict publication mode with named
  exemptions and an output manifest.
- **Split integrity** (`skills/physics-ml/scripts/check_split_integrity.py`): reports group and timestamp coverage;
  missing metadata is `incomplete` (exit 3), `--strict` makes it a failure; `groups_checked` needs full coverage.
- **Manuscript check** (`check_manuscript.py`): citations with no bibliography are missing; inline
  `thebibliography` and `.bbl` files resolve keys; `--external-bib` reports keys as unresolved (exit 3).
- **Berger-Boos limit** (`core/stats/likelihood_limits.py`): labeled an approximation of the construction (finite
  nuisance grid, seeded toys), with toy errors, a `coverage_claim` and the range validated by seeded coverage scans;
  the auxiliary measurement in its toys is drawn from the likelihood's untruncated Gaussian, and the statistic uses the
  constrained maximum when that draw is negative; new `neyman_coverage_scan`.

## 0.1.0 (2026-10-02)

First release of the plugin: seven core skills, contracts, core methods, profiles and examples (see README).
