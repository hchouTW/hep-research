# Changelog — hep-research

Release notes for the plugin. Each entry says what changed in behavior; evidence is in [VALIDATION.md](VALIDATION.md).
Software checks establish contract consistency only, not physical validity.

## Unreleased

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
