# Changelog — hep-research

Release notes for the plugin. Each entry says what changed in behavior; evidence is in [VALIDATION.md](VALIDATION.md).
Software checks establish contract consistency only, not physical validity.

## Unreleased

- **Two-POI contours (T22).** `likelihood_limits.py contour` fits two signal strengths (bins with `s1` and `s2`, the
  shape-limit nuisances and `mc_stat`) and traces the profile-likelihood contours at the chi-square 2-dof levels along
  rays from the best fit, with the Hessian covariance. Toys at the true point confirm the Wilks coverage.
- **Toy CLs for shape-limit (T22).** `likelihood_limits.py shape-limit --cls-toys N` computes CLs from seeded toys on
  a grid of signal strengths (common random numbers across the grid; nuisances profiled on the data at each μ for
  CLs+b and at μ = 0 for CLb, auxiliary measurements redrawn) and gives the observed and the expected median and
  1/2-sigma limits from the same toys. It reproduces the exact Poisson CLs limit for one bin.
- **MC statistics in limits (T22).** A bin of `likelihood_limits.py multibin-limit` or `shape-limit` may give
  `mc_stat`, the MC-statistics uncertainty of its background. It enters as a Barlow-Beeston-lite factor (as
  HistFactory `staterror`): a Gaussian-constrained multiplier per bin, profiled in closed form, redrawn in toys. In a
  coverage study with 20% MC uncertainty per bin it brings the coverage back to nominal, where ignoring it under-covers.
- **Smooth nuisance interpolation (T22).** `shape-limit` shape nuisances accept `"interpolation": "code4p"` (polynomial
  inside |θ| < 1, linear outside, no kink at 0), and normalization nuisances accept asymmetric `hi`/`lo` factors with
  code4 (default), code1 or code0 interpolation, as in HistFactory and pyhf. The default shape interpolation stays the
  piecewise-linear code0, so existing inputs give the same results. Checked against pyhf 0.7.6.
- **Expected-limit bands (T22).** `likelihood_limits.py multibin-limit` and `shape-limit` now give the asymptotic CLs
  limit and the median and 1/2-sigma expected limits under background only, for CLs and for CLs+b, from the Asimov data
  set (Cowan, Cranmer, Gross and Vitells 2011), with σ taken at each band's own signal strength and the q̃ form of the
  CLs+b bands below the median. Checked against the closed form for one bin and against background-only toys.
- **Barlow-Beeston fits with empty MC bins (T22).** A bin where a template has no MC count no longer makes the
  Barlow-Beeston likelihood infinite: the template's true content there stays a nuisance, observed as zero, and takes a
  share of the data when the Barlow and Beeston (1993) special case applies (unweighted and weighted fits; an empty bin
  of a weighted template uses the template's mean weight scale). Only the naive fit can now be infeasible; the result's
  status follows the Barlow-Beeston fit and a failed naive comparison is reported in `naive_fit_failed`. The toy
  studies score each fit on its own successful toys instead of dropping a toy when either fit fails.
- **Environments and reproducibility (T23).** `skills/hep-computing/scripts/environment_manifest.py` records the
  environment of a run as the `environment` object and `tools` list of a `computational-run` artifact (Python,
  platform, whether it comes from an LCG view, a container, conda or a venv, package versions, a fixed list of
  variables such as `LCG_VERSION` and `BINARY_TAG`, never other variables, and the git commit and dirty state), and
  `check` lists every drift against a saved manifest. A new `adapters/environments` (status `documented`) holds an LCG
  view setup template and an Apptainer definition built on `requirements-ci.lock`; the new reference
  `environments-and-containers.md` says which route pins what and what to record.
- **Recasting toolchain templates (T20).** A new `adapters/recasting` (status `documented`: none of the tools is
  installed where it was written) holds starting templates for a MadGraph5_aMC@NLO process and launch card, a Rivet
  analysis with its metadata, a Delphes efficiency-module override, a SModelS parameters file and a MadAnalysis 5 recast
  script. `skills/hep-theory/references/recasting-toolchain.md` says which route fits which search, what every recast
  records, and the cutflow and limit checks a template must pass before its status is raised. The packaging scan now
  reads every shipped text format, including these.
- **Columnar analysis starting points (T24).** `adapters/root-uproot/assets/coffea_dijet_processor.py` is a coffea
  processor template (jet selection, signed generator weights, leading-pair mass and its weighted histogram) and
  `root_to_parquet.py` converts a TTree to Parquet in bounded steps, keeping jagged branches, with a manifest of
  checksums and entry counts that must add up. Both are tested on the synthetic NanoAOD-like file from
  `make_synthetic_nanoaod.py`: the processor reproduces the generator's independently computed answers for any chunk
  size, and every entry is written once. A `columnar` extra and an optional CI job cover them.
- **HEPData export (T21).** `adapters/hepdata/assets/hepdata_export.py` writes a dataset-record or a binned prediction
  as a HEPData submission: `submission.yaml`, the table (bins, values, qualifiers from the observable, each uncertainty
  component as a labelled symmetric or asymmetric error) and, when the artifact has one, its covariance table. The
  status label is kept in the submission comment, each description and a `phrases` keyword. A plain standard-library
  writer is the default; `--engine hepdata_lib` uses hepdata_lib. hepdata-validator 0.3.6 accepts both, and
  `hepdata_record.py` reads the export back with the same values and covariance. A new `hepdata` extra and an optional
  CI job run the validator.
- **Systematics table for papers (T26).** `skills/hep-analysis/scripts/systematics_table_tex.py` renders the
  systematics registry (the `assets/systematics.csv` format, plus any impact columns) as a booktabs LaTeX table. It
  refuses a table without a status (`--status` or a per-row `status` column), names synthetic, asimov, preliminary or
  unvalidated content in the caption, records every status in a comment, and escapes LaTeX; tested by compiling the
  output with pdflatex.
- **Missing skill handoffs (T25).** The Handoffs tables gain hep-statistics → physics-ml (simulation-based
  inference, neural likelihoods), physics-ml → detector-response (fast-simulation validation) and → research-
  communication, research-communication → hep-analysis, detector-response and hep-computing, and detector-response and
  hep-computing → research-communication. To stay within the 8,192-byte budget, a few words of existing handoff rows and
  one routing example in `detector-response` and `hep-statistics` were shortened; routing (static), ownership and
  entry-point checks pass.
- **Documentation brought up to date (T27).** The capability matrix header names 0.3.0; `VALIDATION.md` no longer
  points at the removed `DECISIONS.md` as a current file; `docs/maintenance.md` no longer lists the traceability check
  removed in 0.3.0; the entry-point sizes in `docs/architecture.md` and `docs/architecture-review.md` are remeasured
  (5,602–8,185 bytes, descriptions 765–990 characters, about 2,205 always-on tokens); routing results name the case
  set they used (48, 62, or the current 118 cases); the README says `ams02-research` is listed, access-restricted, in
  both marketplace manifests. The AMS example artifacts now record profile `experiment:ams-02` 2.0.0, as shipped in
  0.3.0 (they still said 1.0.0).
- **Feldman-Cousins upper ends now follow the published construction (sci-fix).** `poisson_diagnostics.py
  fc-interval` forces the upper end to be non-increasing in the background, as Feldman and Cousins (1998, Sec. IV.B)
  did for their tables. It now reproduces every `n0 = 0..10`, `b = 0..5` entry of their Tables IV (90%) and VI (95%)
  within 0.01; before, it returned the plain construction, for example 1.08 instead of 1.26 at `n0 = 0`, `b = 2`, 90%,
  and the unit test's reference value was the plain one. `--plain-construction` (`monotone=False`) keeps the old
  interval; the output records `construction`, `upper_plain` and the searched background range. The
  `--sigma-b` (marginalized) interval is unchanged and labelled plain.
- **Exact Poisson p-values no longer underflow (sci-fix).** `likelihood_limits.py profile-significance` and
  `statistical_toys.py boundary` computed `P(N >= n | b)` as `1 - P(N <= n - 1 | b)`, which returned 0 below about
  1e-16 (n = 60, b = 5 gave 0 instead of 7.65e-43). The tail is now summed directly (`poisson_sf`,
  `log_poisson_sf` in `poisson_diagnostics.py`), and both outputs add `log_p_value_exact_poisson` and
  `significance_exact_poisson_z`, computed from the log p-value so they stay finite beyond the smallest double.
  The Garwood lower end uses the same tail.
- **Covariance matrices are no longer repaired silently (sci-fix).** A new private `core/stats/_linalg.py` holds the
  one Cholesky factorization used by `statistical_toys.py`, `unfolding_diagnostics.py` and `likelihood_limits.py`.
  It works on the matrix scaled to a unit diagonal, so its verdict does not depend on units, and it never adds jitter
  quietly. Before, `ratio-measured`, `ratio-cov` and the constant-ratio fit added an absolute jitter of 1e-10 up to
  1.0 until the factorization succeeded: a covariance with correlation 2 gave chi2 = 9e13 and no error, and
  `response-measured` added 1e-14 to every variance. Now a matrix with a pivot below -1e-10 (relative) raises an
  error that names it; a fit refuses a singular matrix; and sampling accepts a semi-definite matrix and reports the
  shift in `regularization` (`response_covariance_check` for `response-measured`, which only checks). The unit test
  of a correlated ratio covariance used an indefinite matrix (smallest correlation eigenvalue -0.05) and now uses a
  valid one.
- **Poisson limits and intervals are no longer clipped at 500 (sci-fix).** `upper-limit` and `interval` searched for
  their root in [0, 500] and returned 500 when it lay beyond (`central_interval(490)` gave an upper end of 500.0
  instead of 513.15, `upper_limit(495, 0)` 500 instead of 533.19). The search range now follows the count, and a root
  that cannot be bracketed below the mean limit is reported `failed` (exit 1), never as the range end. One mean
  limit, 1e5, now holds in `poisson_diagnostics.py`, `likelihood_limits.py` and `statistical_toys.py` (it was 500,
  500 and 1e5), from a new private `core/stats/_poisson.py` whose distribution, tail and quantile are summed in log
  space and stay accurate to that limit (checked against SciPy and decimal arithmetic). `fc-interval` keeps a
  separate, stated limit of 500 on the total mean, since it scans a fine grid.
- **Malformed input gives findings, not tracebacks (sci-fix).** The comparison gate sorted structured cuts with
  `null` (open) bounds by comparing `None` with numbers, and read an explicit `"phase_space": null` or
  `"normalization": null` as an object; both raised on schema-valid input. `validate_artifact` raised "unhashable
  type" when `artifact_type` was a list or an object. The evidence ledger raised on a non-object record, a string
  `year`, a string `data_taking_period`, list-valued ids and a dated source without an `id`. Now the gate CLI goes
  through a new `check()` that refuses an artifact whose fields have the wrong JSON type, or a plan that is not an
  object (`"status": "refused"`, exit 2, findings with a field path and a code), and a malformed plan entry is a
  mismatch of kind `malformed` that is never applied. The ledger reports `source.bad_field_type` and
  `claim.bad_field_type` at `<id>.<field>` and checks the rest of the record. A seeded mutation fuzz (30,000
  mutations of the valid artifact fixtures, gate plans and the shipped ledgers) raises nothing. The ledger's
  `claim.no_limitations` warning is removed: it could fire only when `scope.text` was missing, which is already an
  error. The shipped ledgers give the same findings as before.
- **Blinding scanner: fewer false alarms, no silent passes (sci-fix).** A sealed low count such as 0 or 3 matched
  every "0" or "3" in a log, including `run_3`, `v3.0.1`, `3rd` and dates (8 hits on one unrelated line); a sealed
  value with fewer than 3 significant digits now matches only a standalone number, and such hits are marked
  `weak`. Logs were read as UTF-8 with replacement characters, so a UTF-16 log containing a sealed value passed;
  text is now decoded from its byte-order mark, a UTF-16 byte pattern, UTF-8 or Latin-1, and a file that cannot be
  decoded is `incomplete`. `check_figure` also inspects `fill_between` and other filled areas, `hist2d` and
  `pcolormesh` meshes and `imshow` images, and, given the sealed numbers (`check_figure(fig, region, sealed)`), text
  artists, titles and figure texts; a "blinded" label inside the region is not a leak. What it still cannot see
  (tick labels, legends, colorbars, values carried only by colors, transformed values) is stated in the module.
- **Dependencies, lint and type checks (T18).** A `pyproject.toml` declares the Python dependencies as extras (`core`,
  `pyhf`, `root-uproot`, `torch`, `diagrams`, `test`, `lint`; the plugin itself is not an installable package) and
  configures ruff and mypy for `core/` and `contracts/`, which both pass. `requirements-ci.lock` pins the `core` and
  `test` extras at the newest versions that still install on Python 3.11 (`requirements-ci-constraints.txt` says
  why), checked to install on 3.11, 3.12 and 3.13. `.pre-commit-config.yaml` runs the path allowlist and ruff on
  commit and the fast test tier on push; the repository's git hooks call it when `pre-commit` is installed.
  `docs/maintenance.md` records the plan to trim `detector-response` and `hep-statistics` (8,185 and 8,138 of 8,192
  bytes) by at least 10%.
- **Continuous integration for the tests (T13).** A new workflow `tests.yml` runs the unit tests, profile suites and
  static checks on Python 3.11, 3.12 and 3.13 with the pinned set, and ruff and mypy, on every push and pull request.
  Optional jobs repeat the unit tests with pyhf, uproot and awkward, PyTorch (CPU) or ROOT (container) installed and
  do not block a merge yet; a weekly run uses the latest releases and the slow tier. Actions are pinned to commit SHAs.
- **Faster covariance and response validation (T17).** The validators' eigenvalue step used pure-Python Jacobi
  rotations, cubic in the matrix size (1.6 s at n = 120 here, 6.9 s in the review's container). They now use
  `numpy.linalg.eigh` when NumPy is installed (0.011 s at n = 120) and keep the rotations otherwise, so the checks stay
  standard-library only; `HEP_STATS_PURE_PYTHON=1` forces the rotations, and the report records `eigen_solver`. The
  two solvers agree to 1e-12 relative; a slow-tier benchmark (`tests/core/test_benchmarks.py`) holds the time budgets.
- **One owner for each numerical helper (T16).** Two Jacobi eigensolvers, the Gauss-Jordan solve, the Cholesky solve,
  bisection, the golden-section minimizers and the matrix products now live once in `core/stats/_linalg.py`; the
  number, seed and toy-count checks in a new `core/stats/_validate.py` (each takes the caller's error class); the
  chunked Poisson sampler joins the others in `_poisson.py`. The modules keep thin aliases, numbers are unchanged
  (the examples reproduce bit for bit), and the helpers now say when they did not do their job: the eigensolver
  reports non-convergence (a warning in the covariance and response validators, an error in TSVD unfolding), a
  bisection whose interval does not bracket the limit is refused instead of returning the interval's end, and a
  singular matrix in a profile fit raises `LikelihoodError` (it raised the unfolding module's `ToyError`, which the
  `likelihood_limits.py` command line did not catch).
- **Batch campaigns survive interruptions and concurrent commands (sci-fix, T15).** `campaign.submit` called the
  scheduler before saving its attempts, so a kill in between left jobs running that the campaign did not know about,
  and a second submit could send them again; submission IDs came from a count with no lock. Now every command that
  changes a campaign holds a lock on `<campaign_dir>/.lock` (a second one is refused with `campaign.locked`), and
  `submit` saves its attempts as `submitting` before the scheduler call and confirms them after. An interrupted
  submission blocks further submits until a person runs `batch_campaign.py confirm` with the job IDs the scheduler
  lists or `abandon` with a reason; a refused submission is recorded as `not-submitted`. The default merge no longer
  concatenates string results (it reports `merge.combine_failed`; pass a combine function), and `engine.merge`
  refuses non-finite chunk results and a non-finite merged value (`merge.non_finite`).
- **The test suite is bounded and tiered (T14).** Every subprocess call in the tests and tools has a timeout
  (`tests/tools/test_subprocess_timeouts.py` keeps it so). `check_diagram_sources.py` fails a block whose
  renderer does not finish within `HEP_RENDER_TIMEOUT` (default 60 s) and stops calling Mermaid's `mmdc` after one
  timeout, so a host where Chromium cannot start no longer hangs the suite. `run_all_checks.py` runs each test
  module in its own process with a time limit (`--module-timeout`, default 600 s; `--jobs` for parallel modules) and
  records every module's duration and the modules over 60 s. The full theory-comparison example test (70 to 350 s)
  moved to the slow tier (`HEP_SLOW_TESTS=1`).
- **Every script behaves as a command-line tool (T12).** `tests/skills/test_cli_robustness.py` runs all 64 scripts
  under `skills/*/scripts/` and `adapters/*/assets/` with `python3 -I`: `--help` must exit 0 without a traceback, and
  a missing input file must give a short error (or a JSON error report) with a non-zero exit. A table names each
  script's input arguments or why it reads none, so a new script must be added. Fixed: tracebacks on a missing file
  in 15 scripts (`eft_truncation.py`, `event_weights.py`, `pdf_uncertainty.py`, `check_example_diversity.py`,
  `check_diagram_sources.py`, the four ROOT-file helpers, `check_systematic_variations.py`, `inspect_checkpoint.py`,
  `unbinned_fit.py`, `uproot_awkward_analysis.py`, `reproduce_published_likelihood.py`, `hepdata_record.py`); sibling
  imports that failed under `-I` in `cosmic_ray_flux.py` and `orbit_averaged_geomagnetic_cutoff.py`; and module-level
  imports of pyhf (`reproduce_published_likelihood.py`) and uproot/awkward/PyYAML (`uproot_awkward_analysis.py`)
  that broke `--help`; they now name the package to install when the script runs.
- **Tests for public functions no test reached (T11).** Direct tests for `scan_file`, `load_project_blinding`,
  `clip_demo`, `campaign.chunk_status`, `load_ledger`, `render_tables`, the contract helpers (`check_conventions`,
  `check_finite`, `check_binned`, `check_observable`, `load_schema`, `side_from_artifact`, `find_cycles`,
  `check_profile_dir`, `declared_namespaces`, `namespace_of`) and round trips of every kinematic conversion. New CLI
  tests for `check_surrogate_domain.py`, which printed a traceback for a non-list `features` field and now reports
  it as a JSON error with exit 2. `counting_reference.py` has its own test file (its flat-prior bound at b = 0 checked
  against PDG Table 40.3, its tail against `core/stats`); the `audit_histograms.py` tests moved to hep-computing;
  `examples/published-comparison/make_record.py` is checked to reproduce its committed record.
- **Edge cases in every public `core/stats` entry point (T10).** `tests/core/test_stats_edge_cases.py` feeds NaN,
  +inf and -inf to each numeric argument of 20 scalar entry points and to numeric leaves of 9 document entry points,
  plus empty lists and empty documents; each must raise its module's named error (the two validators must fail
  instead), from a baseline that is checked to be valid. It also covers p-values far below 1e-10, the mean limit and
  zero or low counts in blinded bins. Defects it found, now fixed: `chi2_sf` returned 1.0 for a NaN or infinite
  chi2 or ndf (an infinite chi2 now gives 0, the rest raise); a bin count of inf or NaN in `multibin-limit` and
  `shape-limit` raised `OverflowError` or a bare `ValueError`; `z_from_log_p(nan)` returned NaN.
- **Schema mutation fuzzing and a keyword meta-test (T09).** `tests/contracts/test_robustness.py` mutates every node
  of every valid artifact fixture, a full gate plan and a ledger record four ways (null, type swap, list wrap,
  deletion) in the fast tier, and runs 10,000 seeded random multi-mutations through the validator, the gate and the
  ledger in the slow tier; none raises. `tests/contracts/test_schema_keywords.py` checks that every keyword in
  `contracts/schemas/` is one `contracts/schema.py` implements (`SUPPORTED_KEYWORDS`) or reads as an annotation, so a
  schema cannot promise a check (for example `oneOf` or `maxItems`) that never runs, and that every `$ref` resolves.
- **Property-based tests (T08).** `tests/core/test_properties.py` (with `hypothesis`, a test-only dependency in the
  new `requirements-test.txt`; skipped without it) checks that upper limits are non-decreasing in n and
  non-increasing in b, that intervals are nested in the confidence level, that covariance tools give the same
  verdict at 1e-12 and 1e12 scale, that a GLS fit does not depend on input order, that a partitioned merge does not
  depend on chunking or finish order, and that validators never raise on arbitrary JSON. That last property found
  that `validate_covariance` and `validate_response` raised on a document that was not an object, a non-list
  `labels` or `closure`, and non-numeric `tolerances`; they now report `document.malformed`,
  `tolerances.malformed` and the existing shape codes.
- **Published-table tests (T07).** `tests/core/test_published_tables.py` checks Feldman-Cousins Tables IV and VI,
  PDG 2024 Tables 40.3 (one-sided Poisson limits, the Garwood ends) and 40.4 (unified intervals), each transcribed by
  script with its source, and Li & Ma eq. 17 against an independent transcription (the paper prints no table).

## 0.3.0 (2026-10-07): first public release

The plugin is published under the Apache License 2.0 (`LICENSE` at the repository root and inside the plugin folder,
`license` in both host manifests). This release restructures what the plugin ships; the seven skills, `core/`,
`contracts/` and the adapters are otherwise unchanged in behavior.

- **Access-controlled AMS-02 content moved to a companion plugin.** `experiment:ams-02` (now 2.0.0) keeps the public
  evidence ledger (60 sources, 184 claims), the domain modules, the analysis-spec audit and the paper-manifest and
  CRDB helpers. The user-supplied Offline software modules, the EOS production catalogue, the ntuple-producer kit, the
  generated catalogs and their index, the environment checker and their tests are no longer in this plugin or its
  repository. They are provided to authorized members by the separate, access-restricted plugin `ams02-research`
  (profile `experiment:ams-02-private` 1.0.0, which depends on `experiment:ams-02`), listed in the same marketplace
  `hep-research-dev` for Claude Code and Codex. The public profile's `index.md`, `README.md`, working rules and
  `profile.json` describe only what they hold and name the companion plugin for the rest.
- **Companion-plugin mechanism.** The shared context-resolution stanza (item 3) says how a bound profile that is in
  neither the registry nor `local_profile_paths` is found: load the installed `<plugin>:profile` skill that names it
  and use the folder it gives as a local profile; with no such plugin installed, say the profile is unavailable and
  never answer its topics from memory. The stanza was rewritten to stay within the 8 KiB SKILL.md budget.
  `contracts/project.py` gains `--local DIR` to validate such a profile with the project; `docs/profile-authoring.md`
  gains a "Companion plugin" section; `tools/check_host_manifests.py` also requires the two marketplace files to list
  the same plugins.
- **Contracts 2.0.0.** The optional old-ledger identifier field is removed from `evidence_source.json` and
  `evidence_claim.json`; the ams02 ledger no longer carries it. Shipped profiles declare `contracts >=2.0,<3.0`; example outputs record the new
  versions.
- **Pre-release development records removed.** Migration guides and maps, the traceability, ledger-preservation and
  principles-coverage checks with their fixtures, the legacy analysis-spec converter and four task examples whose
  subject was the earlier development repository are gone; the remaining references, examples and tests cite this
  plugin's own files. `docs/reference-inventory.*` is regenerated. Nothing in the plugin refers to work orders or run
  logs outside it.
- **Packaging guard extended.** `tools/check_packaging.py` also rejects restricted-site facts (EOS, AFS and AMS CVMFS
  paths, lxplus node names, home folders, local hostnames, AMS Offline identifiers) and traces of the earlier
  development repository. The repository adds `.githooks/` (path allowlist on commit and push), the `guard`
  workflow (allowlist over the whole history plus a gitleaks scan) and `.gitleaks.toml` with the known false
  positives (DOIs, checksum tables, article keys).
- **Documentation.** `CHANGELOG.md` and `VALIDATION.md` restart at this release; `README.md` (plugin and repository)
  carry the install commands, the companion-plugin section, the license and the post-split package size;
  `docs/capability-matrix.md` describes the public profile only.

Earlier versions (0.1.0 to 0.2.6, 2026-10-02 to 2026-10-07) were development releases distributed from a private
repository; their notes are not part of the public record.
