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
