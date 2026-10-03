# Changelog — hep-research

Release notes for the plugin. Each entry says what changed in behavior; evidence is in [VALIDATION.md](VALIDATION.md).
Software checks establish contract consistency only, not physical validity.

## Unreleased (routing follow-ups, 2026-10-04)

Evidence in VALIDATION "FULLTEST-E2-ROUTING follow-ups". No change to skill text.

- **Routing cases**: `out-of-v1-2` (SMEFT global fit) now expects `hep-theory`, which its description claims;
  `st-impacts-1` gets a synthetic pyhf workspace and fit result, so a live run has the fit the prompt refers to.

## Unreleased (FULLTEST-E2 follow-ups, 2026-10-04)

Evidence in VALIDATION FULLTEST-E2-FOLLOWUPS.

- **physics-ml**: the DDP asset and the distributed-training reference advise
  `torchrun --standalone --local-addr=127.0.0.1` on a single machine, where an unresolvable host name otherwise
  makes the rendezvous hang. The smoke test uses it.
- **research-communication**: the Mermaid reference and the diagram checker say that `mmdc` needs its headless
  Chrome, and how to install it.
- **Tests and tools**: `ams-flux-ratio` output is now compared with the committed output (toy summary at Monte
  Carlo precision); `tools/check_relocation.py` copies only git-listed files.

## Unreleased (full test on E2, 2026-10-04)

Work order `tasks/hep-research/isolated-full-test/TASK.md` (r1); evidence in VALIDATION FULLTEST-E2. No change to
plugin behavior.

- **Tested on macOS arm64 (E2)** with pyhf, uproot/awkward, ROOT 6.38.04, PyTorch (CPU), Graphviz, PlantUML and
  Mermaid: legacy traceability, example reruns, relocation and an isolated Claude Code install pass.
- **Known on E2** (follow-ups, not fixed): the 2-process DDP smoke test hangs when the host name does not resolve;
  `ams-flux-ratio` toy-closure numbers differ from the committed output across platforms; relocation copies ignored
  local files such as a venv inside the plugin tree.

## Unreleased (E2 follow-ups, 2026-10-03)

Evidence in VALIDATION E2-FOLLOWUPS.

- **`examples/theory-comparison`**: the Path B response check now uses a stated relative tolerance of 1e-12
  (new criterion `response_vs_path_b_max_rel_dev`) instead of exact equality, which failed on macOS arm64 by one
  rounding unit. Committed output regenerated; its test compares reruns byte for byte and the committed output
  numerically.
- **`qed-benchmark` profile**: `conventions.json` states `scales` (not applicable at fixed-alpha tree level).
- **Tests**: the batch, privacy and ROOT C++ asset tests now pass or skip correctly on macOS (temporary-path
  symlinks, ignored local files, a ROOT build for another Python).

## Unreleased (installed on a macOS workstation, 2026-10-03)

Work order `tasks/hep-research/full-plugin-test/TASK.md` (r2); evidence in VALIDATION INSTALL. No change to plugin
behavior.

- **Installed** at user scope into a day-to-day Claude Code 2.1.288 configuration on macOS (E2) from the GitHub
  marketplace `hchouTW/hep-research` at `3aa942c`: seven `hep-research:*` skills discovered, namespaced invocation
  and profile reads from the installed cache path pass; existing plugins and settings unchanged.
- **Known on E2** (follow-ups, not fixed): five unit failures and one error from macOS path symlinks, a venv inside
  the plugin tree, a mismatched Homebrew ROOT/Python pair, and an exact float comparison in `theory-comparison`.

## Unreleased (Slurm and HTCondor batch execution, 2026-10-03)

Work order `tasks/hep-research/batch-schedulers/TASK.md` (r2); evidence in VALIDATION BATCH-RUN.

- **`core/partition`** (new, steward hep-computing): the T21 engine moved unchanged from `local_partition.py`
  (still its CLI; `examples/local-partition` output byte-identical), plus an executor interface
  (prepare / submit / poll / cancel / version), a local executor, an asynchronous campaign (submit, poll, collect,
  resubmit, reset, cancel, merge, watch) and a worker-side runner. Collection ingests the first valid output per
  chunk and records every other one as a duplicate, never summed; invalid outputs are quarantined with a reason.
  Resubmission is explicit, within `max_attempts`, with resource changes for timeouts and out-of-memory and a reset
  for failed, held, cancelled or unknown chunks; two identical failures stop a chunk.
- **New adapter `adapters/batch-schedulers`** (`documented`): Slurm job arrays (`--no-requeue`, accounting with a
  queue fallback) and HTCondor clusters (item-data queues, job event log, shared file system or file transfer), a
  campaign CLI `batch_campaign.py` whose state-changing commands are dry runs without `--submit` /
  `--approve-cancel`, a config validator that takes site facts only from the user, a bounded `watch`, and a
  `computational-run` report (incomplete campaigns are `failed`). Tested only against fake schedulers; no real
  Slurm or HTCondor has run it; its tool facts were checked on 2026-10-03 against the Slurm 26.05 and HTCondor 25.13 documentation (a few formats are not stated there and stay to be confirmed on a real run).
- **Fixed** after the documentation check: the Slurm state map now covers RESV_DEL_HOLD (held), SIGNALING
  (running), DEADLINE (failed), REVOKED (cancelled), and SUSPENDED/STOPPED (unknown, as HTCondor's suspend); before,
  all of these already fell to `unknown`.
- **New reference** `skills/hep-computing/references/batch-scheduling.md` and example `examples/batch-partition/`
  (the T21 job on both fake schedulers with injected faults; byte-reproducible).
- **Blinding scan** (`core/blinding`): `.out`, `.err`, `.sh`, `.sbatch` and `.sub` files are now read as text, so
  scanning a campaign directory is no longer `incomplete` because of job logs and job descriptions.
- **Packaging check**: `--root`, and the `batch-site-fact` rule for shipped batch configs.
- **Routing**: six new cases (two in Traditional Chinese); the `hep-computing` description now names Slurm and
  HTCondor job arrays, held or evicted jobs and pilot sizing.

## Unreleased (hep-statistics reinforcement, 2026-10-03)

Work order `tasks/hep-research/stats-reinforcement/TASK.md` (r2); evidence in VALIDATION STATS-REINFORCEMENT-RUN.

- **Li & Ma significance** (`skills/hep-statistics/scripts/li_ma_significance.py`, scientific fix): the docstring
  and references now call the statistic `sqrt(-2 ln lambda)` and its normal reading asymptotic. New `--toys N --seed S`
  (plug-in background toys) and `--exact-conditional` (binomial test) report p-values under `p_values`; default output
  keys are unchanged. The astroparticle reference quotes the low-count p-values from the committed command.
- **New scripts** in `skills/hep-statistics/scripts/`: `look_elsewhere.py` (local scan, brute-force toys,
  Gross-Vitells bound; one-dimensional scans), `sensitivity_and_gof.py` (Asimov discovery significance with and
  without a background uncertainty; toy-calibrated saturated-deviance goodness of fit that withholds chi2 at low
  counts), `bayes_diagnostics.py` (rank-normalized split R-hat, bulk and tail ESS, quantile MCSE; prior reweighting
  that asks for a rerun when the weights degenerate; a demonstration Metropolis sampler). Exit codes fail closed.
- **New pyhf asset** `adapters/pyhf-combine/assets/pyhf_nuisance_diagnostics.py`: pulls, constraints, pre- and
  post-fit impacts, grouped breakdowns (freeze-one and sequential, with closure) and correlations; adapter 0.6.0.
- **New references**: `core-stats-guide.md` (every core/stats subcommand, exit codes, choosing table),
  `nuisance-modeling.md` (constraints, interpolation codes with a verified pyhf walkthrough, pruning, correlation
  schemes), `ml-assisted-inference.md` (classifier observables, NSBI calibration and coverage, SBC; physics-ml keeps
  training). New sections: look-elsewhere, expected sensitivity, goodness of fit, model comparison and Bayesian
  convergence in `inference-recipes.md`; sWeights and weighted unbinned fits in `likelihood-fitting.md`; publishing
  likelihoods in `statistical-tools.md`. Every number in them comes from a committed test or command.
- **Routing**: eight new cases (three in Traditional Chinese) for impacts, global significance, sensitivity, goodness
  of fit, Bayesian convergence, sWeights, NSBI validity and likelihood publication; the skill description is unchanged.
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
